# How the agents differ

They are built the same way. They differ on three axes, and the differences are what make the roles real.

**Instructions.** The Orchestrator manages. The Analyst understands. Specialists produce facts. The Writer assembles. The Reviewer finds fault. Writer and Reviewer are given opposing success criteria so that a pass means something.

**Tools.** Each specialist gets exactly the tools its trade needs. The Writer gets a template. The Orchestrator and the Reviewer get nothing, so one cannot do the work and the other cannot redo it.

**Visibility.** The Orchestrator sees everything. The Writer sees all outputs but no raw sources. Each specialist sees its own slice. The Reviewer sees only the brief and the finished document. The Analyst sees only the request and the client knowledge file. Less context per agent means less cost, fewer hallucinations, and a cleaner audit trail.

You can check this yourself during the demo. Under every agent message is a small toggle that shows exactly what that agent was told, what context it was given, and which tools it had. Open the Reviewer's and notice what is not there.

Two rules hold across all of them: only the Orchestrator talks to the human, and only the Orchestrator changes state.
