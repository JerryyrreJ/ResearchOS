# ResearchOS D Demo Runbook

## Preflight

1. Run `npm ci`, `npm run lint`, and `npm test`.
2. Confirm `/health` returns `status: ok` and contract `0.1.0-frozen`.
3. Open Settings → Demo & status → Reset golden project.
4. Confirm the header says `FIXTURE MODE`. Never describe Fixture or Offline Replay as live execution.

## Golden path

1. Enter the Fiscal transmission workspace.
2. Open Workspace and point out versioned objects, relations, conflict count, and Context Packs.
3. Open Thesis Build and show the visible `BUILD FAILED` constraints.
4. Open Validation Plan and inspect the registered MacroTrace step.
5. Open MacroTrace and state that the fixture is associational and contains no empirical conclusion.
6. Open Recompile and explain the causal-to-associational semantic diff.
7. Open Version Diff and identify Changed, Recomputed, Reused, and Invalidated objects.

## Required fallback checks

Use Settings → Demo & status to verify:

- `OFFLINE REPLAY` remains visible throughout cached playback;
- `Partial` blocks a final conclusion;
- `Failed` does not substitute a successful result;
- `Permission blocked` provides an access action;
- `Model timeout` marks the previous result stale;
- `Unknown state` stops rendering safely and exposes a diagnostic action.

## Three-run evidence

| Run | Reset first | Golden path | Failure check | Mobile QR | Result |
|---|---|---|---|---|---|
| 1 | ☐ | ☐ | ☐ | ☐ | Pending |
| 2 | ☐ | ☐ | ☐ | ☐ | Pending |
| 3 / recording | ☐ | ☐ | ☐ | ☐ | Pending |

Record the third successful run only after all boxes are complete. The recording must show the same build and deployment being delivered.
