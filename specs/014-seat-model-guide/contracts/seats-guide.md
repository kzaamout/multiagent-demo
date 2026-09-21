# Contract: seat model guide

Additive to `specs/006-seats-single-chat/contracts/http-api-s5.md`. No event, payload or schema version changes (FR-017).

## 1. Registry field (`config/models.yaml`)

Each model entry gains one key:

```yaml
  qwen3-5-9b:
    provider: ollama
    ...
    weights: open          # open: published weights; proprietary: served only by its vendor
```

- Allowed values: `open`, `proprietary`. Any other value makes `ModelConfig.load` raise `ValueError("model <key>: weights must be open or proprietary")`.
- Absent: the model is not classified; it is never a pick and the report names it.

## 2. `GET /api/seats` additions

Every existing key is unchanged. Each row gains `guide`; the table gains `guide`.

```json
{
  "seats": [
    {
      "seat": "writer",
      "card": { "agent_id": "writer", "name": "...", "role": "Writer", "model": { "label": "qwen3.5 9b, local", "...": "..." } },
      "model_key": "qwen3-5-9b",
      "dependency": "...",
      "warning": "",
      "guide": {
        "current": { "model": "qwen3.5 9b, local", "runs": 173, "replies": 248, "first_time": 100, "percent": 40 },
        "open": { "status": "pick", "model_key": "qwen3-5-9b", "model": "qwen3.5 9b, local", "runs": 173, "replies": 248, "first_time": 100, "percent": 40 },
        "proprietary": { "status": "no_runs" }
      }
    }
  ],
  "models": [ "..." ],
  "note": "Changes apply at the next stage.",
  "guide": { "runs": 385, "min_runs": 5 }
}
```

- `guide` is `null` on the rows of seats outside the six (the appraisal seats `case` and `market`, whose workflow is not built); the page shows no guide lines and no button figure for them.
- `guide.current`: the seat's effective model (after any swap) at this seat, whatever its runs, or `null` when that model has no replies at this seat.
- `guide.open`, `guide.proprietary`: `{"status": "pick", ...record}`, `{"status": "too_few_runs"}` or `{"status": "no_runs"}` (data-model.md, Seat pick).
- `percent` is a whole number worked out by the server with the report's rounding; the page never divides.
- `guide.runs` is the number of counted runs in which some seat made a model call or a reply (the report's "called a model" count), leaving out the run this app is running now.

## 3. Settings page elements

The page renders what the table says; it never computes a figure. `data-part` names are the test hooks.

| Element | `data-part` | Text |
|---|---|---|
| Line under the title, after `#settings-note` | `guide-note` | `Instruction accuracy is the share of a seat's replies the Orchestrator accepted the first time it checked them against the seat's instructions. Figures from {runs} recorded runs.` (`1 recorded run` when there is one) |
| Figure inside each model button, after the model's name | `select-fig` | `{percent}% ({first_time} of {replies})`, or `no runs yet` when `current` is `null` |
| Block under each seat's button and dependency note | `seat-guide` | two `.guide-line` children, `data-kind="open"` then `data-kind="proprietary"` |
| Kind label in a guide line | `guide-kind` | `Top open model` or `Top proprietary model` |
| Value in a guide line | `guide-value` | pick: `{model} · {percent}% ({first_time} of {replies} replies)`; `no_runs`: `no runs yet`; `too_few_runs`: `none with 5 runs on this seat yet` |
| Note at the foot, after the status line | `guide-foot` | the paragraph in section 4 |

The picks are not buttons. The model menu's options carry no figures.

## 4. Foot note text

> Instruction accuracy is the share of a seat's replies the Orchestrator accepted the first time it checked them against the seat's instructions: a well-formed reply in the right shape, tools called rather than figures typed, figures that match what the tool returned, concerns carried forward. Behaviour accuracy, in the model performance report, is whether the seat did what its scenario expects, such as raising the planted blocker or passing a clean draft. Neither measure looks at whether the price is right; the report checks prices separately. A top model has at least 5 runs on the seat, and is ranked so that a long record counts for more than a short perfect one.

## 5. Report section (`docs/model-performance.md`)

Placed after "What the columns mean" and before "Best local model per seat".

```markdown
## Top models per seat

<one paragraph: same code and runs as the Settings page, the definition of instruction accuracy in the page's words, the 5 run threshold, the Wilson ranking, and where the kind comes from>

| Seat | Top open model | Instruction accuracy | Runs | Top proprietary model | Instruction accuracy | Runs |
|---|---|---|---|---|---|---|
| orchestrator | qwen3.5 9b, local | 98% (390 of 397) | 288 | no runs yet | | |
| estimator | qwen3.5 9b, local | 44% (155 of 349) | 273 | claude-sonnet-5 via Bedrock | 94% (29 of 31) | 26 |

Models not classified as open or proprietary: none.
```

Rows follow the Settings order: orchestrator, intake, estimator, pricing, writer, reviewer. A slot with no pick gives the page's wording in the model cell and leaves its two figures empty.

## 6. Report label changes

- Display label `First time` becomes `Instruction accuracy` in every table, heading and sentence; its definition reads: "share of the seat's replies the Orchestrator accepted on the first attempt, where a reply the run stopped on counts as not accepted; the figure the Settings page shows".
- Display label `Accuracy` becomes `Behaviour accuracy` everywhere, with its definition unchanged in meaning.
- `docs/model-performance-runs.csv` column names are unchanged (`accepted_first_time`, `replies`, `checks_met`, `checks_total`, ...).
