"""Numbers checked where they are born (spec 010, phase 1.7).

A specialist's figures are copies of what its tool returned, so they can be compared with the original by
equality. Asking only whether the tool was called let five runs through in which price_list_lookup failed,
the model wrote every price itself, and three of the documents passed review with a valid tag on an
invented total. A tag says which output a number was copied from, never that the output is true.

Three links, each an exact lookup and none a judgment: a specialist's reply against its tool's result,
Pricing's quantities against the Estimator's, and the draft's dollar amounts against what the Writer was
given. What none of them can check is a count read from a drawing, which is what confidence flags, the
Reviewer and the human at Handoff are for.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

ToolResults = Sequence[tuple[str, Mapping[str, Any]]]
"""Each successful tool call of one seat turn, in order: the tool's name and the data it returned."""

CENT = Decimal("0.005")
THOUSANDTH = Decimal("0.001")
HUNDREDTH = Decimal("0.01")
NUMBER = re.compile(r"(?<![\d.,])\d{1,3}(?:,\d{3})+(?:\.\d+)?(?![\d])|(?<![\d.])\d+(?:\.\d+)?(?![\d])")


def number(value: Any) -> Decimal | None:
    """A figure as a number, however it was written: 6450, "6450.00", "$6,450.00". None when it is not one."""
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip().lstrip("$").replace(",", "").strip()
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _same(a: Decimal | None, b: Decimal | None, within: Decimal = CENT) -> bool:
    return a is not None and b is not None and abs(a - b) < within


def _agrees(mine: Any, theirs: Any, within: Decimal = CENT) -> bool:
    """A field the reply leaves out is not an invented number, so only a field it carries is compared."""
    return mine is None or _same(number(mine), number(theirs), within)


def _key(text: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()


def _candidates(line: Mapping[str, Any], tool_lines: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """The tool lines a reply line could be a copy of.

    Neither a line reference nor a description is unique in practice: seats reuse a drawing reference for
    every line read from that sheet, and the same material appears once per group. So a reply line is held
    against every tool line sharing its reference and description, or failing that its description alone,
    and it stands when it equals any one of them.
    """
    pool = list(tool_lines)
    ref, description = _key(line.get("line_ref")), _key(line.get("description"))
    return (
        [t for t in pool if _key(t.get("line_ref")) == ref and _key(t.get("description")) == description]
        or _described(description, pool)
        or _only(t for t in pool if ref and _key(t.get("line_ref")) == ref)
    )


def _only(lines: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """A reference finds a line only when one line carries it. Shared by several, it says nothing."""
    found = list(lines)
    return found if len(found) == 1 else []


def _described(description: str, pool: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Lines with this description, or failing that lines whose description contains it or is contained
    in it, because a seat shortens "Duplex receptacle 15A with box and device" to "Duplex receptacle".
    Loose wording is safe here: the wording only finds the candidates, and the figures must still be equal."""
    lines = list(pool)
    exact = [t for t in lines if _key(t.get("description")) == description]
    if exact or not description:
        return exact
    return [
        t
        for t in lines
        if _key(t.get("description"))
        and (description in _key(t.get("description")) or _key(t.get("description")) in description)
    ]


def _calls(results: ToolResults, tool: str) -> list[Mapping[str, Any]]:
    return [data for name, data in results if name == tool]


NO_LOOKUP = (
    "price_list_lookup returned no result in this turn, so no price in this reply came from the fixture. If "
    "the call failed, read its error, correct the arguments and call it again: items is a list of lines each "
    "with line_ref, description, quantity and unit, and markup_rate, labour_hours and labour_rate are "
    "numbers. Then copy its prices, extensions and totals"
)
NO_CALCULATOR = (
    "quantity_calculate returned no result in this turn, so no quantity in this reply came from it. If the "
    "call failed, read its error, correct the arguments and call it again: each item has description, unit, "
    "category, counts as a list of numbers, group, and unit_hours as a number. Then copy its quantities "
    "with waste and its labour hours"
)


def pricing_disagreements(
    priced_bom: Iterable[Mapping[str, Any]], cost_summary: Mapping[str, Any], results: ToolResults
) -> list[str]:
    """Where a Pricing reply differs from what price_list_lookup returned in the same turn.

    Lines are matched by line reference across every successful call, the latest call winning. The totals
    must be those of one call that priced every line in the reply, because totals added up across calls
    would be the model's arithmetic. A failed call returns nothing, so it supports nothing.
    """
    calls = _calls(results, "price_list_lookup")
    if not calls:
        return [NO_LOOKUP]
    tool_lines = [line for data in calls for line in data.get("lines", [])]
    problems: list[str] = []
    priced: list[Mapping[str, Any]] = []
    for line in priced_bom:
        if number(line.get("unit_price")) is None and number(line.get("extended")) is None:
            continue
        priced.append(line)
        name = f"{line.get('line_ref')} {line.get('description', '')}".strip()
        candidates = _candidates(line, tool_lines)
        if not candidates:
            problems.append(f"{name} carries a price and was never sent to price_list_lookup")
            continue
        if any(
            c.get("status") == "priced"
            and _agrees(line.get("unit_price"), c.get("unit_price"))
            and _agrees(line.get("extended"), c.get("extended"))
            for c in candidates
        ):
            continue
        source = candidates[-1]
        if source.get("status") != "priced":
            problems.append(
                f"{name} carries a price and the lookup returned it {source.get('status')}. Report it in "
                "exceptions with no price"
            )
            continue
        for field in ("unit_price", "extended"):
            if not _agrees(line.get(field), source.get(field)):
                problems.append(
                    f"{name}: your {field} is {line.get(field)}, the lookup returned {source.get(field)}"
                )
    covering = [
        data
        for data in calls
        if data.get("totals")
        and all(_described(_key(line.get("description")), data.get("lines", [])) for line in priced)
    ]
    if not covering:
        problems.append(
            "no single price_list_lookup call priced every line in this reply and returned totals. Call it "
            "once with every line, markup_rate, labour_hours and labour_rate, and copy its totals"
        )
        return problems
    totals = covering[-1]["totals"]
    for field in ("material", "markup", "labour", "total"):
        if not _same(number(cost_summary.get(field)), number(totals.get(field))):
            problems.append(
                f"cost_summary {field} is {cost_summary.get(field)}, the lookup returned {totals.get(field)}"
            )
    return problems


def quantity_handover_disagreements(
    priced_bom: Iterable[Mapping[str, Any]], estimator_bom: Iterable[Mapping[str, Any]]
) -> list[str]:
    """Priced lines whose quantity is not the Estimator's, or that the Estimator never produced."""
    taken = list(estimator_bom)
    if not taken:
        return []
    problems: list[str] = []
    for line in priced_bom:
        if number(line.get("quantity")) is None:
            continue
        same = _described(_key(line.get("description")), taken)
        source = same[-1] if same else None
        if any(_same(number(line.get("quantity")), number(t.get("quantity")), THOUSANDTH) for t in same):
            continue
        if source is None:
            problems.append(
                f"{line.get('description')} is not a line of the Estimator's bill of materials. Price the "
                "Estimator's lines, with their descriptions as written"
            )
        elif number(source.get("quantity")) is not None and not _same(
            number(line.get("quantity")), number(source.get("quantity")), THOUSANDTH
        ):
            problems.append(
                f"{line.get('description')}: your quantity is {line.get('quantity')}, the Estimator's is "
                f"{source.get('quantity')}"
            )
    return problems


def estimator_disagreements(
    bom: Iterable[Mapping[str, Any]], labour: Mapping[str, Any], results: ToolResults
) -> list[str]:
    """Where a takeoff differs from what quantity_calculate returned in the same turn.

    A line is matched by its description. A seat often rewords a description between the call and the
    reply, so a line that matches none is still accepted when its quantity and unit are ones the tool
    produced: the rule is that the number came from the tool, not that the wording did. This proves the
    arithmetic and the waste factors. It cannot prove the counts read from the drawings.
    """
    calls = _calls(results, "quantity_calculate")
    if not calls:
        return [NO_CALCULATOR]
    tool_lines = [line for data in calls for line in data.get("lines", [])]
    produced = [(_key(t.get("unit")), number(t.get("quantity_with_waste"))) for t in tool_lines]
    problems: list[str] = []
    hours = Decimal("0")
    for line in bom:
        quantity = number(line.get("quantity"))
        same = _described(_key(line.get("description")), tool_lines)
        exact = [t for t in same if _same(quantity, number(t.get("quantity_with_waste")), THOUSANDTH)]
        source = exact[-1] if exact else same[-1] if same else None
        if source is not None:
            hours += number(source.get("hours")) or Decimal("0")
            if not exact:
                problems.append(
                    f"{line.get('description')}: your quantity is {line.get('quantity')}, quantity_calculate "
                    f"returned {source.get('quantity_with_waste')} with waste"
                )
        elif not any(u == _key(line.get("unit")) and _same(quantity, q, THOUSANDTH) for u, q in produced):
            problems.append(
                f"{line.get('description')}: quantity {line.get('quantity')} {line.get('unit')} is not a "
                "figure quantity_calculate returned. Send the line to quantity_calculate and copy its result"
            )
    total = number(labour.get("total_hours"))
    latest = number(calls[-1].get("total_hours"))
    if not (_same(total, latest, HUNDREDTH) or _same(total, hours, HUNDREDTH)):
        problems.append(
            f"labour total_hours is {labour.get('total_hours')}, quantity_calculate returned "
            f"{calls[-1].get('total_hours')}"
        )
    groups = {_key(k): number(v) for data in calls for k, v in (data.get("hours_by_group") or {}).items()}
    for group, value in (labour.get("by_group") or {}).items():
        mine = number(value)
        if mine is None:
            continue
        named = _same(mine, groups.get(_key(group)), HUNDREDTH)
        if not named and not any(_same(mine, v, HUNDREDTH) for v in groups.values()):
            problems.append(
                f"labour by_group {group} is {value}, which is not a figure quantity_calculate returned"
            )
    return problems


def numbers_in(text: str) -> set[Decimal]:
    """Every number a piece of context carries, with 31,338.31 and 31338.31 read as the same number."""
    found: set[Decimal] = set()
    for match in NUMBER.findall(text):
        # "120,208" is one amount in a sentence and two numbers in a JSON list, and the text alone cannot
        # say which. Both readings are held: this set only ever answers whether a figure exists upstream.
        for part in {match, *match.split(",")}:
            value = number(part)
            if value is not None:
                found.add(value)
    return found


def amounts_not_in_context(amounts: Iterable[str], offered_context: str) -> list[str]:
    """Dollar amounts a draft carries that appear nowhere in what the Writer was given.

    This replaces the rule that every dollar amount must carry a tag. That rule had to decide what counts
    as a figure needing a tag, which is a judgment, and it refused zeros, the labour rate and line
    extensions. Whether a number exists upstream is a lookup. It catches an invented amount whether or not
    it is tagged, and it lets through any amount the specialists really produced.
    """
    held = numbers_in(offered_context)
    return [a for a in dict.fromkeys(amounts) if number(a.rstrip(".")) not in held]


def summarise(problems: list[str], limit: int = 6) -> str | None:
    """One refusal from many disagreements: the first few in full, and a count of the rest."""
    if not problems:
        return None
    more = len(problems) - limit
    return "; ".join(problems[:limit]) + (f"; and {more} more of the same kind" if more > 0 else "")
