# Sterling AI multi-agent demo: sales playbook

For humans presenting or supporting the demo. Claude Code should not load this unless asked.

## What we are selling
Not software. Judgement about how AI should be put to work inside a business: separation of duties, a human gate, provenance for every number, and a system that knows when to stop. The demo is evidence. The prospect should leave believing two things: this pattern works on my problem, and these are the people to build it.

## The one-line pitch
"A team of AI agents, each with a job, working under a coordinator, producing a reviewed deliverable a human approves. Same engine, your workflow."

## The framing that works
Talk about it as an org chart, not a tech stack. The Orchestrator is the project manager. The specialists are the estimator and the buyer. The Writer is the proposal writer. The Reviewer is QA. The prospect is the approver. Use the agents' names. "Rosa rejected Willa's draft because Elias's estimate didn't match the panel schedule" lands. "The reviewer agent returned a fail verdict" does not.

## Before the meeting
- One week out: ask for one real RFP, redacted if needed. If refused, pick a public tender from their market and say so.
- Run Dry intake on their file. Not ready: go back to them for the missing pieces (this makes you look rigorous). Ready with assumptions: note which clarification will fire live and plan to have the prospect answer it.
- Run the full team on their file at least twice. Fix anything ugly. Record a clean run for Replay.
- Load the Planted inconsistency dataset as your backup if their file passes review cleanly on the first go. You need a rejection on screen.
- Set the brand.yaml for their dataset so the deliverable cover carries their name and logo.
- Day of: run the pre-flight page. All green or you switch to Replay mode before you walk in.
- Know which seat is on the local model and which is on Gemini so you can answer "what's running where" instantly.
- Decide whether you are comfortable with the prompt toggle being used in this room. It is always on. A technical prospect can read and photograph the prompts.

## The arc (20 minutes)
0 to 3, Introduction tab. Meet the team, one sentence per agent. Explain the loop with the diagram, spend the extra beat on the backward arrows and on "four ways it stops."

3 to 5, the villain. Switch to Single model, run their RFP. Say nothing while it generates. Ask them to read it. Let them find the invented price or the missed item. If they don't, point to one. Say: "That's what most AI demos are. Here's what we do instead."

5 to 14, the team run. Narrate lightly, let the screen do the work.
- Plan appears: "This is orchestration. A work breakdown before any work."
- Clarification fires: hand them the keyboard. They answer. "You're in the loop by design, not as an afterthought."
- Specialists run in parallel, Pricing waits for Estimator: "Dependencies are respected, not guessed."
- The trap fires, Reviewer rejects, arrow goes backward: "Rosa doesn't see how the team got there. She only sees the brief and the document. That's why she can catch it." When it passes: "Two cycles maximum. After that it comes to you with the open findings instead of pretending."
- Open a prompt toggle on the Reviewer's message: "Notice what's not in there. She never saw the estimate."
- Handoff: hover a number in the PDF, feed scrolls to the source. "Every figure has a paper trail."
- Ask them to click Approve.

14 to 16, model swap and the meter. Open Settings, move Pricing from local to Bedrock, or Reviewer onto Bedrock. Point at the grey text changing and the cost column. "Your compliance team picks the model. The architecture doesn't care." Pull up the Compare strip: Single vs Team cost and time.

16 to 18, "How this becomes real inside your AWS account." Same boxes, different badges. Give the timeline: weeks to a first gated workflow.

18 to 20, start a second run. The clarification doesn't fire. Point at the knowledge file. Stop the run there. Ask: "What's the workflow you'd want to run through this first?" Then stop talking.

## Moments that must land
The villain output. The prospect answering a question. The backward arrow. The prompt toggle showing what the Reviewer could not see. The provenance hover. The grey model text changing. The question not repeating. Get all seven and you get the second meeting.

## Objections and answers
- "Isn't this just prompt engineering?" Each seat is a separate call with its own tools and a restricted view. Open two prompt toggles side by side. Show Settings: six seats, six model choices. A prompt can't do that.
- "Why not one strong model?" It can't review itself, can't be denied tools, can't show provenance. Show the villain output again.
- "What if it hallucinates?" The Reviewer catches the class of error; the Handoff shows every assumption and source; nothing is sent without a human. Say the word "gate."
- "Our data can't leave the building." Point at the seat on the local model. Any seat can run in their AWS account.
- "What does it cost to run?" Point at the meter. Compare Single vs Team. Note the local seat costing nothing. Mention the cost ceiling setting.
- "How long to production?" Weeks for one gated workflow. The engine exists; the work is tools and criteria.
- "What happens when it goes wrong?" Load the Missing sheet dataset. Show the blocker exit. "It stops and tells you why. That's the feature."
- "What if our RFP is a mess?" Load the Not ready dataset. "It tells you in thirty seconds what's missing rather than answering the wrong question beautifully."

## What not to say
Don't say "autonomous." Say "supervised." Don't say "it learns." Say "it remembers what you told it." Don't say "AI employees." Don't promise their exact tools are connected; say "connectors through the gateway." Don't apologise for the planted trap; explain it as design for failure. Don't oversell the model swap as magic; it is a config change, and that's the point.

## If things break
Switch to Replay mode with the most recent clean recording of their file, or the Planted inconsistency scenario. Say: "I'll play back this morning's run so we're not waiting on the network." Nobody minds. Never restart a live run twice in front of them.

## After the meeting
Within one hour: run the leave-behind command and email the compiled PDF from their run, the run timeline, and the Introduction PDF. Two sentences, no pitch, one question about which workflow they'd run next. Log the objections you heard and add them to this file.

## Glossary for the team
Orchestrator: the coordinator that plans, assigns, and decides when to stop. Agentic loop: the six stages with backward arrows. Termination: the four narrative ways a run ends (reviewer pass, retry budget spent, blocker escalated, intake not ready) plus a cost ceiling safety stop. Provenance: the tag linking a number to the agent output that produced it. Renderer: any screen that displays the event stream; the web page today, Slack tomorrow. Gate: a human approval that nothing passes without. Knowledge file: per-client memory of answers given. Dry intake: running only the first stage to check a file before a meeting. Prompt toggle: the control under every agent message that shows exactly what that agent was told.
