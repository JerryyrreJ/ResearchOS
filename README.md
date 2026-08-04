# ResearchOS Web

ResearchOS turns versioned research objects into evidence-bounded theses. This repository currently contains Role D's fixture-first product shell and the frozen v1 contracts used by the four implementation roles.

## Run locally

Requires Node.js 22.13 or newer.

```bash
npm ci
npm run dev
```

Open `http://localhost:3000`. The interface is explicitly labeled **FIXTURE MODE** until A/B/C APIs replace the frozen samples.

## Validate

```bash
npm run build
npm test
npm run lint
```

## Product boundaries

- Frontend displays backend-owned states; it does not invent conclusion semantics.
- `contracts/v1` and `fixtures/contracts` are frozen shared inputs.
- Associational evidence must never be presented as causal evidence.
- Failed, partial, unsupported, stale, and offline states must remain visible.

See `docs/product/PRODUCT_CONSTITUTION.md`, `docs/architecture/ARCHITECTURE.md`, and `docs/handoffs/D_Frontend_Integration/` for the binding product and role rules.
