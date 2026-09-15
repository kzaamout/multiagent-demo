# FAQ

**Is this one model pretending to be six?** No. Each seat is a separate call with its own instructions, tools, and context. You can put a different model in every seat and watch the grey text change. Open the prompt toggle under any two messages and compare.

**Why not one very good model with a long prompt?** A single model cannot review its own work with a straight face, cannot be denied the tools it should not have, and cannot show you where a number came from. Roles give you separation of duties, which is what your auditors will ask about.

**What stops it from looping forever?** A retry budget owned by the Orchestrator. Two review cycles, then it escalates to a human with the open findings. There is also a hard cost ceiling per run. Stopping is a designed behaviour, not a hope.

**What if it gets something wrong?** The Reviewer is designed to catch it, and the Handoff package shows every assumption and source so the human can catch what the Reviewer missed. Nothing is sent externally without a person approving it.

**What if my request is incomplete or messy?** The Intake Analyst grades it against a readiness checklist before any work starts. If it is not ready, the run stops in seconds with a list of what is missing.

**Does it learn?** It remembers. Answers you give go into a per-client knowledge file and are not asked again. It does not retrain on your data.

**Can it run on our data without sending it to a model vendor?** Yes. Any seat can run on a local model or on Amazon Bedrock inside your account. The demo shows one seat running on a laptop-hosted model.

**Can this live in Slack, Teams, or our ticketing system?** Yes. Those are renderers. The orchestrator does not know or care what is displaying it.

**How long from demo to something real?** Weeks, not quarters, for a first workflow with a human gate. The engine exists; the work is connecting your tools and encoding your criteria.

**Why Sterling AI?** Because the person who designed this also led data and AI delivery for a Big Four practice and has shipped this pattern for insurers, banks, and payment networks. The demo is small on purpose. The judgement behind it is not.
