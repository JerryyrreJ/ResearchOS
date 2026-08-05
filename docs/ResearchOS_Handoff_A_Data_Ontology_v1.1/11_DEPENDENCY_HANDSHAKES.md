# Role A Dependency Handshakes

## A to B

Deliver Data Resolve endpoint, success fixture, permission failure and schema mismatch failure.

## A to C

Deliver DataObjectRef, ContextPack and confirmed relation APIs. C must never rely on A internal database IDs beyond public refs.

## A to D

Deliver object summary, versions, relation graph, conflicts and project-state fixtures. D owns layout only.

## Needs from C

Contract version and any optional write-back metadata. Breaking changes require ICR.
