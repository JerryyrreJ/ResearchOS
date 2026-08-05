# ResearchOS：确定性资产基座与浏览器工作台

ResearchOS converts uploaded research materials into version-pinned, auditable assets and provides a browser workspace for exploring them. The integrated API now combines Role A assets, the Role B MacroTrace adapter, and the Role C Thesis Compiler behind one browser-facing `/api/v1` surface.

## Backend

The M1 backend provides deterministic:

- file format and metadata detection;
- streaming SHA-256 and content-addressed Blob storage;
- immutable Asset and AssetVersion records;
- whole-file deduplication;
- Representation and exact Fragment records;
- Markdown, DOCX, XLSX, CSV and text PDF parsing;
- ingest batches, failure isolation and audit events;
- object, version and structural graph query projections.

AI classification, semantic relations, Context Packs, Impact Sets and selective rebuilds remain later milestones.

```bash
uv sync --dev
uv run alembic upgrade head
uv run uvicorn researchos.api.main:app --reload
```

API documentation: http://127.0.0.1:8000/docs

```bash
uv run pytest
uv run ruff check .
```

## Web application

Requires Node.js 22.13 or newer.

```bash
cd apps/web
npm ci
npm run dev
```

Open http://localhost:3000. Real API mode connects workspace upload and versioning with Thesis creation, compile, MacroTrace execution, evidence verification, semantic recompile, and version diff. The MacroTrace producer currently identifies its execution as `FIXTURE`; the UI preserves that boundary while still exercising real REST calls end to end.

The browser client defaults to `http://127.0.0.1:8000/api/v1`. To point it at another backend, set `NEXT_PUBLIC_RESEARCHOS_API_BASE_URL` before starting the web app. The backend accepts the documented local development ports by default; override them with `RESEARCHOS_CORS_ORIGINS`.

The integration work is on `role/d-frontend` and preserves the producer-owned A, B, and C implementations as merge history.

```bash
cd apps/web
npm run build
npm test
npm run lint
```

## Product boundaries

- The frontend displays backend-owned states and does not invent conclusion semantics.
- `contracts/v1` and `fixtures/contracts` are frozen shared inputs.
- Associational evidence must never be presented as causal evidence.
- Fixture, Offline Replay and Real API modes are distinguishable.
- A deterministic file fact, hash, version decision or parse result is never delegated to AI.
