# The agentic loop

Six stages. Work moves forward through them and, when something is wrong, moves backward with a reason and a target. Forward is what you expect. Backward is what makes it agentic.

1. **Intake.** The Intake Analyst reads the raw request, grades it against a readiness checklist, and produces a structured brief. Gaps become questions. Blocking questions pause the run and go to you in one batch. Non-blocking gaps proceed on a stated default that is flagged and carried through to the end. A request that is not ready stops here, with a list of what is missing.
2. **Plan.** The Orchestrator decomposes the brief into sub-tasks, assigns specialists, and decides what each may see. You watch the work breakdown appear before any work happens.
3. **Work.** Specialists execute. Independent tasks run in parallel; dependent ones wait. A specialist that hits something the brief can't answer raises a blocker, which goes to you through the Orchestrator.
4. **Assemble.** The Writer builds the deliverable from specialist outputs, tagging every fact with where it came from. The document compiles and refreshes on screen as it is written.
5. **Review.** An independent Reviewer, on a different model family from the Writer, judges the finished document against the brief and a criteria file. Pass or fail, with findings by severity and a routing recommendation for each. A fail sends work back to the specific stage that caused it.
6. **Handoff.** You receive the deliverable, the reviewer's verdict, every assumption made on your behalf, every question asked and answered, and the full log. Nothing is sent externally by the system.

**Knowing when to stop.** Termination is the hardest problem in multi-agent systems. This system has exactly four exits, and the Orchestrator alone decides: the Reviewer passed; review stopped, because a review cycle made no progress or a ceiling was reached, and the unresolved findings go to you; a blocker needs a human decision; or the request was not ready to begin with. Every run ends with a card saying which exit fired and why.

**Memory.** Answers you give are written to a per-client knowledge file the Intake Analyst reads at the start of every run. Ask once.

<!-- diagram: loop. Six nodes in a horizontal strip; forward arrows between them; curved backward arrows Review to Work, Review to Assemble, Work to Intake, each labelled; a human icon attached to Intake, Work, and Handoff; a retry counter badge on Review; a terminal card off Handoff listing the four exits, with Not ready also branching off Intake. -->
