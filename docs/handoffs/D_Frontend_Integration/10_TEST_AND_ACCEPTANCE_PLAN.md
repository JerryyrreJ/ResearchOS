# Role D Test and Acceptance Plan

## Component

- every contract enum renders;
- unknown enum fails visibly;
- errors and warnings remain readable;
- Fixture, Offline Replay and Real modes are distinct;
- permission and timeout errors have user actions.

## E2E

```text
Workspace
→ Thesis Build Failed
→ Validation Plan
→ Tool Run or Replay
→ Evidence Drawer
→ Recompile
→ Version Diff
```

## Deployment

- `/health` for both APIs;
- Nginx routing;
- HTTPS;
- environment variables;
- QR access;
- demo reset;
- log location;
- restart commands.

## Demo

Run three times from reset. Record the third successful run. Test network loss and graph fallback.
