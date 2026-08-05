# Role C Dependency Handshakes

## Needs from A

Fixed DataObjectRef and ContextPack. Permission or missing version becomes CompileIssue.

## Sends to B

ToolRequest only. No direct model invocation.

## Receives from B

EvidenceBundle only. MacroTrace internal Final Claim becomes engine_claim.

## Sends to D

OpenAPI, ThesisBuild, CompileResult, JobEvent, Validation Plan and VersionDiff fixtures before real endpoints.

## Contract Steward

Record every proposal in ICR. C can merge L1 only with consumer approval. L2/L3 require all roles.
