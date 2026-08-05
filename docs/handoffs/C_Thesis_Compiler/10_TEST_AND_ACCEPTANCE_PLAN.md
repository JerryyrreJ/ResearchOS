# Role C Test and Acceptance Plan

## Rules

Each P0 error code has one positive and one negative case. Initial golden claim triggers definition, horizon, language, variable and falsifier issues.

## Language Policy

Test every evidence level against every requested language level. CAUSAL input with ASSOCIATIONAL evidence must not pass as causal.

## Tool Orchestration

- valid ToolRequest;
- unsupported route;
- timeout;
- partial evidence;
- blocking diagnostic;
- evidence with lower language level;
- duplicate EvidenceBundle idempotency.

## Versioning

- changed definition affects downstream plan and claim;
- unchanged EvidenceBundle reused;
- new EvidenceBundle creates new build;
- VersionDiff sets changed and reused refs correctly.

## Consumers

D renders all states and unknown-state error. A/B producer tests pass.
