# Role B Interface Guide

## ToolRequest input

Validate before invoking MacroTrace:

- contract version;
- tool exactly `MACROTRACE`;
- as-of date;
- requested evidence type;
- fixed input object versions;
- timeout.

Do not accept arbitrary Python, SQL, formulas or Registry mutations from the request.

## EvidenceBundle output

### Status mapping

```text
MacroTrace COMPLETE → COMPLETE
MacroTrace PARTIAL → PARTIAL
MacroTrace FAILED → FAILED
Cancellation → CANCELLED
```

### Coverage mapping

Preserve `FULL`, `PARTIAL`, `UNSUPPORTED`, `OUT_OF_SCOPE`.

### Diagnostic blocking

A diagnostic must expose `blocking: true` only when the registered Recipe or Specification defines it as a failure condition. Do not infer blocking from a low p-value alone.

### Engine claim

`engine_claim` may summarize evidence but must not contain a product conclusion status.

Forbidden output fields:

```text
conclusion_state
supported_probability
investment_rating
buy_sell_signal
```

## Artifact handling

Return artifact IDs, URIs and hashes. Do not inline huge tables into the contract unless the existing API already requires it.
