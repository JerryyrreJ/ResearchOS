# ResearchOS Web

ResearchOS turns versioned research objects into evidence-bounded theses. This repository currently contains Role D's fixture-first product shell and the frozen v1 contracts used by the four implementation roles.

## Run locally

Requires Node.js 22.13 or newer.

```bash
npm ci
npm run dev
```

Open `http://localhost:3000`. The interface is explicitly labeled **FIXTURE MODE** until A/B/C APIs replace the frozen samples.

The Settings → Demo & status panel provides deterministic delivery QA:

- switch between `FIXTURE MODE` and clearly labeled `OFFLINE REPLAY`;
- exercise queued, running, partial, failed, cancelled, permission, timeout, and unknown states;
- reset the golden project before each demonstration;
- scan the production QR code for the mobile entry.

`REAL API` remains visibly unavailable until the A/B/C producer handshakes are complete. The UI does not simulate a successful backend integration.

## Validate

```bash
npm run build
npm test
npm run lint
```

Web health probe:

```bash
curl http://localhost:3000/health
```

## Product boundaries

- Frontend displays backend-owned states; it does not invent conclusion semantics.
- `contracts/v1` and `fixtures/contracts` are frozen shared inputs.
- Associational evidence must never be presented as causal evidence.
- Failed, partial, unsupported, stale, and offline states must remain visible.

See `docs/product/PRODUCT_CONSTITUTION.md`, `docs/architecture/ARCHITECTURE.md`, and `docs/handoffs/D_Frontend_Integration/` for the binding product and role rules.
