# Architecture

Three layers.

**Renderers.** What you look at. The demo web page is one renderer. A Slack channel could be another. Renderers subscribe to an event stream and draw it; they never decide anything.

**Orchestrator.** A state machine with six stages and a review limit. It owns the plan, the assignments, every stage transition, all contact with the human, and the decision to stop. It emits a typed event for everything it does, each with a one-sentence reason. It is the only component that changes state.

**Agents and tools.** Each agent is a model plus instructions plus a tool set plus a visibility scope. Agents receive a task and a slice of context, return a structured result, and have no idea what stage the system is in. Tools are deliberately narrow: a drawing reader, a price list, a template, a document compiler.

Models are interchangeable per seat. Any agent can run on a cloud model (Amazon Bedrock, Anthropic, Google Gemini, xAI Grok) or a model running locally on a laptop. The agent's name and role stay fixed; the model under the hood is shown in grey and can be swapped from a settings page.

<!-- diagram: architecture. Three horizontal bands top to bottom: Renderers (Web UI card, Slack card greyed with a "future" tag); Event Stream drawn as a horizontal bus; Orchestrator as a single box containing the six-stage strip and a retry counter; Agents as a row of six agent cards; Tools as small boxes only beneath specialists and Writer; Model providers along the bottom (Bedrock, Anthropic, Gemini, Grok, Local) with dotted lines up to agent cards. A human figure to the right of the Orchestrator with one arrow labelled "one door". -->
