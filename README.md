# ResearchOS：确定性资产基座与浏览器工作台

ResearchOS converts uploaded research materials into version-pinned, auditable assets and provides a browser workspace for exploring them. The current integration slice connects the Role D web shell to the Role A M1 API for real file ingestion, asset listing, version history and structural graph data.

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

Open http://localhost:3000. The workspace upload, asset and version surfaces use the real API. Thesis Build, MacroTrace and Recompile remain explicitly labeled Fixture or Offline Replay surfaces until their producer APIs are available.

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
