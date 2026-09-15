# How this becomes real inside your AWS account

The demo runs on a laptop. The production version runs in your AWS account with the same agents, the same orchestrator, and the same event protocol. What changes is where each piece lives.

| Demo | Production |
|---|---|
| Agents run in a local Python process | Agents deploy to Amazon Bedrock AgentCore Runtime, unchanged |
| Tools are Python functions | Tools sit behind AgentCore Gateway with per-agent access policy |
| Client knowledge is a file | AgentCore Memory, scoped per client, with expiry |
| Run log is a JSON file | AgentCore Observability plus CloudWatch |
| Login is a shared password | Your identity provider through AgentCore Identity |
| Models: Bedrock plus external keys | Models: Bedrock first; external providers through Gateway where you allow them |
| Fixture price lists and CRM | Your supplier APIs and CRM through Gateway connectors |
| Human approval on the demo page | Human approval in Slack, email, or your existing tools, as another renderer |

Why this matters: the thing you saw in the demo is not a prototype that gets rewritten. The orchestrator and agents are built on Strands Agents, the same SDK AgentCore is designed around, so the migration is deployment work, not engineering work. Your data stays in your account. Your security team gets IAM, VPC, and audit logs they already understand.

Typical path: two weeks to stand up the runtime and gateway with your first real tool, then one workflow live with a human gate, then expand.

<!-- diagram: demo-vs-production. The architecture diagram drawn twice side by side, identical shapes. Left labelled "Demo" with laptop badges. Right labelled "Your AWS account" with AgentCore service badges on the corresponding boxes. -->
<!-- maintainer note: verify current AgentCore service names and that Strands Agents remains the recommended SDK before publishing. -->
