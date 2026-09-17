# One request in. One reviewed deliverable out. A team of AI agents in between.

This is a working demonstration of a multi-agent system: several AI agents, each with a defined job, working together under a coordinator to take a real business request from intake to a finished, quality-checked deliverable that a human approves before anything leaves the building.

It is not a chatbot. No single model writes the answer. A coordinator breaks the work down, hands pieces to specialists, has a writer assemble the result, sends it to an independent reviewer, and only calls it done when the reviewer passes it or when it has decided it needs a human.

Two workflows run on the same engine: responding to an electrical bid request, and producing an appraisal report from an intake order. Same agents in the same seats, different trade knowledge. That is the point: the pattern is reusable, the domain is a configuration.

Everything you see in the demo is driven by the system's actual state. The diagram lights up because the coordinator changed stage, not because a video is playing.
