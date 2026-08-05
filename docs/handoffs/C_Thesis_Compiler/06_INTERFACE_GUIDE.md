# Role C Interface Guide

## Compile phases

```text
1. Schema validation
2. Definition and scope checks
3. Evidence requirement derivation
4. Initial compile issues
5. Validation plan
6. ToolRequest generation
7. EvidenceBundle ingestion
8. Diagnostic and coverage checks
9. Language policy
10. Conclusion state
11. Immutable version persistence
12. Diff
```

## Language ceiling

| EvidenceBundle type | Maximum product wording |
|---|---|
| DESCRIPTIVE | data show / report states |
| PREDICTIVE | model predicts |
| ASSOCIATIONAL | conditionally associated |
| DYNAMIC_ASSOCIATION | dynamic association |
| STRUCTURAL_PROXY | consistent with mechanism |
| CAUSAL_IDENTIFIED | estimated causal effect under registered assumptions |

A lower level can never satisfy a higher requested level.

## Multiple bundles

When bundles disagree:

- retain all evidence;
- do not average incomparable estimands;
- surface `EVIDENCE_CONFLICT`;
- record which claim path each bundle supports or weakens.

## Compile state ordering

```text
Blocking schema/rule error → COMPILE_FAILED
No blocking error but required coverage absent → EVIDENCE_INSUFFICIENT
Triggered falsifier / complete weakening path → WEAKENED
Complete support and weakening paths → EVIDENCE_CONFLICT
Complete support path, no triggered falsifier → SUPPORTED
```
