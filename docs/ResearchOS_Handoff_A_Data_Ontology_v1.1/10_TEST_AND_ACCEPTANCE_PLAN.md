# Role A Test and Acceptance Plan

## Unit

- object ID and version ID generation;
- SHA-256 duplicate detection;
- immutable original storage;
- candidate to active version transition;
- permission filter;
- MD, DOCX, text PDF and XLSX canonicalization;
- manifest generation;
- relation state transition;
- Context Pack hash;
- exact Data Resolve version.

## Contract

- serialize DataObjectRef;
- serve DataResolveResponse;
- serialize OntologyRelation and ContextPack;
- reject unknown contract version;
- reject missing version_id;
- reject unauthorized object.

## Integration

- B resolves frozen dataset;
- C consumes fixed object refs;
- D renders object and relation fixtures;
- activation of new version returns affected refs.

## Acceptance Demo

Upload a mixed project set, show original and canonical representations, confirm one version relation, show one conflict, generate a Context Pack, then resolve one dataset version for B.
