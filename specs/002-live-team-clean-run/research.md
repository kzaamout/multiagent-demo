# Research: Live team on the clean run (S2)

Date of verification: 2026-09-14. Every fact below was read from an official source or from the installed package on that date. Nothing is pinned from memory.

## Installed and pinned

| Package | Version | Source |
|---|---|---|
| strands-agents with `litellm` and `ollama` extras | 1.55.1 | PyPI; wheel source read and exercised with a scripted model |
| litellm | 1.96.0 (latest 1.101.0; Strands 1.55.1 requires 1.96.0 or lower) | PyPI, strands-agents wheel METADATA |
| ollama (Python client) | 0.6.2 | resolved by uv |
| boto3 | 1.43.94 | PyPI |
| openai (LiteLLM dependency) | 2.54.0 | resolved by uv |
| pypdfium2 | 5.13.0, BSD-3-Clause and Apache-2.0 | PyPI |

The repository sits in OneDrive, which refuses hardlinks from the uv cache; `[tool.uv] link-mode = "copy"` is set in `pyproject.toml`.

## Strands Agents 1.55.1 facts used by the design

Source: the 1.55.1 wheel, byte-identical to tag `python/v1.55.1` in `strands-agents/harness-sdk` (the old `sdk-python` repository redirects there).

- `Agent(model=..., system_prompt=..., tools=[...], hooks=[...], callback_handler=None, name=...)`. Invoke with `await agent.invoke_async(prompt)` or `agent.stream_async(prompt)`; the default callback handler prints, so it is disabled.
- One Agent instance serves one invocation at a time; concurrent calls raise `ConcurrencyException`. The design builds one Agent per seat call.
- Per model call usage: `AfterModelCallEvent.stop_response.message["metadata"]["usage"]` with `inputTokens`, `outputTokens`, `totalTokens`, and `metrics.latencyMs`.
- Tool calls: `BeforeToolCallEvent` and `AfterToolCallEvent` carry `tool_use` (`name`, `input`, `toolUseId`), `result` (`status`, `content`), and `duration` in seconds. The default executor runs a turn's tools concurrently; the design uses `SequentialToolExecutor` so thread replies appear in call order.
- Streaming text arrives as `{"data": chunk}`; the design splits completed lines into progress events.
- Tools: `@tool` from `strands`, typed parameters with docstring `Args:`. A tool may return `{"status": "success", "content": [{"text": ...}, {"image": {"format": "png", "source": {"bytes": ...}}}]}` to give a vision model a page image.
- Structured output: `structured_output_model=` per call registers an output tool; it works alongside other tools. The design does not use it: seat files already specify JSON replies, and the reply is validated by `app/live/replies.py` with one retry, which works the same on every provider including the local model.
- A custom model subclasses `strands.models.Model` and implements `update_config`, `get_config`, `structured_output`, and `stream`, yielding `messageStart`, `contentBlockStart`, `contentBlockDelta`, `contentBlockStop`, `messageStop`, and `metadata` events. The scripted test model uses this.
- Providers: `BedrockModel(region_name=..., model_id=..., temperature=...)` uses the boto3 credential chain; `OllamaModel(host, model_id=...)`; `LiteLLMModel(client_args=..., model_id="gemini/<id>", params={...})`.
- Tool names must match provider limits; dotted names are not portable, so tools are named with underscores (`price_list_lookup`).

## Model facts (official pages fetched 2026-09-14)

Sources: AWS Bedrock model cards (docs.aws.amazon.com/bedrock/latest/userguide/model-cards.html), the Bedrock pricing data behind aws.amazon.com/bedrock/pricing, platform.claude.com model and pricing pages, ai.google.dev Gemini models, pricing, and deprecations pages, docs.litellm.ai provider pages, ollama.com library tag pages.

| Seat need | Candidate | Model id | Price per million tokens, in and out (USD) | Notes |
|---|---|---|---|---|
| Claude via Bedrock | Claude Sonnet 5 | `us.anthropic.claude-sonnet-5` (US and Canada geo profile) | 2.20 and 11.00 geo; 2.00 and 10.00 global | Image input. Rejects any non-default `temperature`. Bedrock marks native structured outputs unsupported; tool use works. |
| Claude via Bedrock, low temperature | Claude Sonnet 4.6 | `us.anthropic.claude-sonnet-4-6` | 3.30 and 16.50 geo | Accepts temperature. Legacy at Anthropic, active on Bedrock. |
| Claude via Bedrock, low cost | Claude Haiku 4.5 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | 1.10 and 5.50 geo | Accepts temperature. End of life no sooner than October 2026. |
| Gemini with vision | Gemini 2.5 Pro | `gemini/gemini-2.5-pro` via LiteLLM, key `GEMINI_API_KEY` | 1.25 and 10.00 up to 200k tokens | Stable, no shutdown date; its successor is only in preview. |
| Gemini with vision | Gemini 3.8 Flash | `gemini/gemini-3.8-flash` | 0.75 and 3.75 until 2026-12-31, then 1.50 and 7.50 | Stable, released 2026-09-02. |
| Gemini with vision | Gemini 3.1 Pro preview | `gemini/gemini-3.1-pro-preview` | 2.00 and 12.00 | Preview. |
| Local via Ollama | Llama 3.1 8B | `llama3.1:8b` | 0 | Text only, tools badge, the export's label. |
| Local via Ollama | Granite 4.1 8B, Qwen3 8B | `granite4.1:8b`, `qwen3:8b` | 0 | Tools badge; newer. |
| Grok via LiteLLM | Grok 4.6 | `xai/grok-4.6`, key `XAI_API_KEY` | 2.00 and 6.00 | Listed only; not a default seat model. |

No Claude 4.5 or later model runs in-region in ca-central-1; the `us.` profile keeps data in US and Canada regions and routes from ca-central-1 to ca-central-1, us-east-1, us-east-2, and us-west-2. Ollama's latest release is v0.34.0 (2026-09-05).

## Decisions

### D1. Strands runs one seat call; the Orchestrator stays hand-written
- Decision: each seat call builds a fresh Strands `Agent` with the seat's instructions, tools, hooks, and model, invokes it once, and returns the reply text, progress lines, tool calls, and usage to the Orchestrator, which converts them to events.
- Rationale: constitution XV. Strands multi-agent features are not used.

### D2. One agent source interface for stub and live runs
- Decision: the Orchestrator consumes an agent source with the same shape for both modes: intake, work task, rework, assemble, review, and plan. The S1 stub scenario becomes one implementation; the live source is the other. Stage rules, gates, recording, and replay are unchanged.
- Rationale: FR-014, and S1's tests keep guarding the engine.

### D3. JSON replies validated in the application, not provider structured output
- Decision: seat replies are extracted and validated by `app/live/replies.py`, with one retry carrying the validation error (FR-016).
- Rationale: identical behaviour on Bedrock, Gemini through LiteLLM, and the local model; Bedrock marks native structured outputs unsupported on Sonnet 5.

### D4. Live timestamps are wall time
- Decision: in live mode the clock never sleeps; event offsets are elapsed wall time. Replay scales these gaps as in S1.

### D5. Tools are thin wrappers over tested deterministic functions
- Decision: Strands tool functions are closures bound per run over the dataset and run folder, calling the tested functions in `app/tools/`. Their names use underscores. Each call is observed by hooks and becomes one `tool.called` event with a short argument and result summary and the duration.
- Consequence: the seat instruction files name tools with underscores (mechanical rename of the approved text).

### D6. PDF parsing and page images with pypdfium2
- Decision: `document_parse_pdf` returns text per page and a legibility confidence; `vision_read_drawing` renders one page to PNG at 150 DPI and returns it as an image content block with the page's text layer.
- Legibility heuristic (no official standard exists): confidence is the share of extracted characters that are letters, digits, whitespace, or common punctuation, capped at 1.0; a page with fewer than 20 extracted characters scores 0.3, meaning "probably a drawing with no text layer, read it visually". The heuristic is documented in the tool and flagged for review on the curated dataset.

### D7. Orchestrator model use in S2
- Decision: in S2 the Orchestrator's model proposes the plan (with its reason) and the termination headline. The run engine validates the plan against seat scopes and dependency rules and falls back to the rule-based plan with a stated reason when invalid. Other reasons use the engine's templates until S3 routing needs model wording.
- Rationale: stays inside the owner-approved scope (decision 3 of 2026-09-14) while keeping S2's cost and latency small.

### D8. Model configuration lives in `config/models.yaml`
- Decision: providers, models (id, provider, model id, label, image input, temperature support, prices and their source date), and each seat's default model live in one YAML file. Labels name the exact model, for example "claude-sonnet-5 via Bedrock", so the grey text stays truthful.
- Defaults pending the owner's confirmation are marked in the file (see the plan's open questions).

### D9. Provider availability checks never read secret values into the app's state
- Decision: Bedrock is available when boto3 resolves credentials and a region; Gemini when `GEMINI_API_KEY` is set; xAI when `XAI_API_KEY` is set; Ollama when `GET {OLLAMA_HOST}/api/tags` answers and lists the configured model. Only booleans and reasons leave the registry.

### D10. Estimated cost
- Decision: `est_cost = tokens_in / 1e6 * price_in + tokens_out / 1e6 * price_out`, rounded to 6 decimals, from `config/models.yaml`. Local models cost 0.

### D11. Scripted model for Part A proof
- Decision: `tests/support/scripted_model.py` subclasses the Strands `Model` and replays, per seat, a sequence of text and tool-use turns. The end-to-end test runs the live source on a small synthetic dataset under `tests/fixtures/s2/` (a two-page request PDF, one drawing page PDF, a short price fixture) and matches the Clean run golden stage sequence and exit.
