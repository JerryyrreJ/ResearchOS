# Role B Test and Acceptance Plan

## Upstream

- record upstream commit and license;
- run original tests before local changes;
- preserve startup and API behavior.

## Adapter

- validate ToolRequest;
- map COMPLETE, PARTIAL, UNSUPPORTED and FAILED;
- map evidence type conservatively;
- preserve failed model runs;
- exclude conclusion_state;
- include registry version and result hash.

## Ontology Adapter

- resolve exact version;
- verify content hash;
- reject schema mismatch;
- reject permission error;
- record lineage.

## Golden Route

- three identical runs for identical inputs;
- one main model view;
- one diagnostic;
- one robustness or challenge;
- Offline Replay with explicit mode.

## Consumer

C compiles both Fixture and real EvidenceBundle. Any mapping disagreement blocks merge.
