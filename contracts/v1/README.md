# Frozen Contracts v1

Contract version: `0.1.0-frozen`

## Rules

1. Copy these files into the repository once through the contracts bootstrap PR.
2. Every producer and consumer validates the same Schema.
3. Do not duplicate contract fields in module-specific files.
4. L1 changes require Producer and Consumer review.
5. L2 and L3 changes require A/B/C/D approval and a new version directory.
6. Recompute `CONTRACT_HASHES.sha256` only after an approved contract PR.

## Producer and Consumer

| Schema | Producer | Consumer |
|---|---|---|
| data_object_ref | A | B, C, D |
| data_resolve | A | B |
| ontology_relation | A | C, D |
| context_pack | A | C, D |
| thesis_build | C | D |
| compile_issue | C | D |
| tool_request | C | B |
| evidence_bundle | B | C, D through C |
| compile_result | C | D |
| version_diff | C with A/B inputs | D |
| job_event | C | D |
| api_error | A/B/C | D and peer services |
