# Role D Interface Guide

## UI authority

Backend JSON is authoritative for:

- status;
- issue code;
- evidence type;
- conclusion state;
- affected/reused nodes;
- object versions;
- permissions.

The frontend may transform labels for readability but must preserve raw values in details.

## Required badges

Show text plus visual state:

```text
AI_PROPOSED
CONFIRMED
BUILD FAILED
SUPPORTED
WEAKENED
EVIDENCE INSUFFICIENT
EVIDENCE CONFLICT
OFFLINE REPLAY
```

## Loading and failure

Every async panel needs:

- empty;
- queued;
- running;
- partial;
- failed;
- complete;
- cancelled.

Do not replace failed content with the last successful result without showing stale state.

## Research Graph

Prefer embedding or adapting the MacroTrace graph artifact. The Thesis graph wraps it as one evidence-tool subgraph. Do not merge node IDs or pretend both graphs share one execution namespace.

## Accessibility

- No color-only status;
- keyboard focus;
- readable table overflow;
- explicit source links;
- responsive QR entry;
- reduced-motion option for graph animation.
