"""Replay the figure checks over recorded live runs, at no model cost (spec 010, phase 1.7).

    uv run python scripts/replay_figures.py

Runs recorded before tool results were kept hold only a summary of each call, so the Pricing tool is run
again here on the reply's own lines: it is deterministic, and the fixture has not changed. The rates passed
to it were not recorded, so markup and labour are taken from the reply and only the material total and the
grand total are really tested. The Estimator's calculator cannot be replayed at all, because the counts it
was given were never recorded. The Writer rule replays exactly: each committed draft is on disk beside the
context its seat was given.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.live.figures import (  # noqa: E402
    amounts_not_in_context,
    number,
    pricing_disagreements,
    quantity_handover_disagreements,
)
from app.live.materials import supplier_order_from  # noqa: E402
from app.tools.price_list import LookupRequest, PriceList  # noqa: E402
from app.tools.template import MONEY, TAG, untagged_money, with_dollars_inside  # noqa: E402

RUNS = Path("runs")
DATASETS = Path("datasets")


def events_of(folder: Path) -> list[dict[str, Any]]:
    try:
        lines = (folder / "events.jsonl").read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]
    except (OSError, ValueError):
        return []


def lookup_again(folder: Path, dataset: str, reply: dict[str, Any]) -> dict[str, Any] | None:
    fixture = DATASETS / dataset / "fixtures" / "supplier-prices.csv"
    if not fixture.exists():
        return None
    knowledge = folder / "knowledge.md"
    order = supplier_order_from(knowledge.read_text(encoding="utf-8") if knowledge.exists() else "")
    requests = []
    for line in reply["priced_bom"]:
        quantity = number(line.get("quantity"))
        if quantity is None:
            continue
        requests.append(
            LookupRequest(
                line_ref=str(line.get("line_ref")),
                description=str(line.get("description")),
                quantity=quantity,
                unit=str(line.get("unit", "")),
                item_code=str(line["item_code"]) if line.get("item_code") else None,
            )
        )
    lines = PriceList.from_csv(fixture).lookup(requests, supplier_order=order, long_lead_days=28)
    material = sum((line.extended for line in lines if line.extended is not None), Decimal("0"))
    summary = reply.get("cost_summary") or {}
    markup, labour = number(summary.get("markup")), number(summary.get("labour"))
    total = None if markup is None or labour is None else material + markup + labour
    return {
        "lines": [
            {
                "line_ref": line.line_ref,
                "description": line.description,
                "status": line.status,
                "unit_price": None if line.unit_price is None else str(line.unit_price),
                "extended": None if line.extended is None else str(line.extended),
            }
            for line in lines
        ],
        "totals": {"material": material, "markup": markup, "labour": labour, "total": total},
    }


def main() -> None:
    count: Counter[str] = Counter()
    by_model: Counter[str] = Counter()
    shown: list[str] = []
    for folder in sorted(RUNS.iterdir()):
        events = events_of(folder)
        if not events or events[0].get("payload", {}).get("mode") != "team":
            continue
        if not any(e["type"] == "tool.called" for e in events):
            continue
        dataset = events[0]["payload"].get("dataset_id", "")
        estimator_bom: list[dict[str, Any]] = []
        for event in events:
            payload = event.get("payload") or {}
            result = payload.get("result") or {}
            if event["type"] == "task.completed" and payload.get("agent_id") == "estimator":
                estimator_bom = result.get("bom") or estimator_bom
            if event["type"] == "task.completed" and payload.get("agent_id") == "pricing":
                if not result.get("priced_bom"):
                    continue
                count["pricing replies accepted at the time"] += 1
                model = event["actor"]["model"]["model_id"]
                again = lookup_again(folder, dataset, result)
                if again is not None:
                    problems = pricing_disagreements(
                        result["priced_bom"], result.get("cost_summary") or {}, [("price_list_lookup", again)]
                    )
                    if problems:
                        count["  would now be refused: differs from the lookup"] += 1
                        by_model[f"pricing differs from lookup, {model}"] += 1
                        if len(shown) < 4:
                            shown.append(f"{folder.name[:8]} {model}: {problems[0]}")
                handover = quantity_handover_disagreements(result["priced_bom"], estimator_bom)
                if handover:
                    count["  would now be refused: quantity or line is not the Estimator's"] += 1
                    by_model[f"handover, {model}"] += 1
                    if len(shown) < 8:
                        shown.append(f"{folder.name[:8]} {model}: {handover[0]}")
            if event["type"] == "draft.committed":
                prompt = folder / "prompts" / f"{event.get('prompt_ref')}.json"
                draft = folder / str(payload.get("markdown_path", ""))
                if not draft.is_file():
                    draft = folder / "drafts" / f"draft-v{payload.get('version')}.md"
                if not prompt.is_file() or not draft.is_file():
                    continue
                context = json.loads(prompt.read_text(encoding="utf-8")).get("context_slice", "")
                markdown = draft.read_text(encoding="utf-8")
                body = with_dollars_inside(markdown).split("\n## Provenance", 1)[0]
                count["drafts committed"] += 1
                count["  dollar amounts in those drafts"] += len(
                    MONEY.findall(TAG.sub(lambda m: m.group(0), body))
                )
                absent = amounts_not_in_context(MONEY.findall(body), context)
                if absent:
                    count["  drafts holding an amount found nowhere in the Writer's context"] += 1
                    count["    such amounts"] += len(absent)
                    if len(shown) < 12:
                        shown.append(
                            f"{folder.name[:8]} draft v{payload.get('version')}: {', '.join(absent[:5])}"
                        )
        # What the old rule refused, judged by the new one.
        for rejected in sorted((folder / "rejected").glob("*.txt")) if (folder / "rejected").is_dir() else []:
            text = rejected.read_text(encoding="utf-8", errors="ignore")
            if "have no provenance tag" not in text.split("\n", 1)[0]:
                continue
            count["writer replies the old rule refused for untagged amounts"] += 1
            prompt = folder / "prompts" / f"{rejected.stem.rsplit('-', 1)[0]}.json"
            if not prompt.is_file():
                continue
            context = json.loads(prompt.read_text(encoding="utf-8")).get("context_slice", "")
            body = text.split("\n", 1)[1].replace("\\n", "\n").split("## Provenance", 1)[0]
            if amounts_not_in_context(untagged_money(body), context):
                count["  of those, the new rule would still refuse"] += 1
    for label, value in count.items():
        print(f"{value:6d}  {label}")
    print()
    for label, value in sorted(by_model.items()):
        print(f"{value:6d}  {label}")
    print()
    for line in shown:
        print("  e.g.", line)


if __name__ == "__main__":
    main()
