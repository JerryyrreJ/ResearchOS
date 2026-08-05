# MacroTrace × ResearchOS：让宏观观点真正开始跑实证

MacroTrace is now the product entry point. A user supplies a macro claim or question; the
system first lights up the data and document nodes used for that question, then expands the
registered mechanisms, lanes, factors, models and diagnostics, and finally produces an
evidence-bounded research report.

`Question → Part A evidence space → Part B empirical compiler → confidence and report`

Part A remains the immutable data/asset layer. Part B is the primary research experience.
Part C preserves claim language and evidence boundaries, while Part D provides the integrated
browser experience.

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
uv sync --dev --extra data-plugins
uv run alembic upgrade head
uv run uvicorn researchos.api.main:app --reload
```

API documentation: http://127.0.0.1:8000/docs

```bash
uv run pytest
uv run ruff check .
```

## Product entry

On Windows, one command creates the environment, installs the optional data providers, runs
the local migrations and opens the MacroTrace product:

```powershell
.\start.ps1
```

Open http://127.0.0.1:8000. The default page is the mature MacroTrace research workspace:

1. enter a question or paste a report claim;
2. inspect the zoomable Part A evidence space (grey = available, highlighted = used);
3. inspect Part B lanes, factors, model runs, diagnostics and lineage;
4. read the direct answer and full research report.

The earlier ResearchOS workspace shell remains available as an optional supporting view:

```powershell
.\start.ps1 -WorkspaceShell
```

## Optional ResearchOS workspace shell

Requires Node.js 22.13 or newer.

```bash
cd apps/web
npm ci
npm run dev
```

Open http://localhost:3000. This supporting shell exposes file intake, immutable versions,
Thesis compilation and the frozen Tool Adapter. It is no longer the product's primary entry.

The browser client defaults to `http://127.0.0.1:8000/api/v1`. To point it at another backend, set `NEXT_PUBLIC_RESEARCHOS_API_BASE_URL` before starting the web app. The backend accepts the documented local development ports by default; override them with `RESEARCHOS_CORS_ORIGINS`.

## Data plugins

The integrated Python backend exposes selectable AKShare and FRED plugins. They appear in the
main Part A evidence-space toolbar. Every fetched table is stored through Role A as an
immutable, content-hashed AssetVersion before Role B can resolve it.

- AKShare accepts a public AKShare function name and structured JSON arguments. It never
  evaluates Python or SQL supplied by the browser.
- FRED accepts a validated series ID and a small whitelist of observation/vintage options.
  Its API key remains server-side and is never returned to the browser.
- B resolves a dataset only by its pinned object ID, version ID and SHA-256 through
  `POST /api/v1/data/resolve`; it never silently switches to a newer version.

Create a local `.env.local` (already ignored by Git) when FRED is needed:

```dotenv
FRED_API_KEY=your-local-key
```

An existing private environment file can instead be referenced without copying credentials:

```dotenv
RESEARCHOS_ENV_FILE=C:\path\to\your\private\.env.local
```

The integration work is on `role/b-data-plugins` and intentionally reuses the existing A, B,
C and D implementations instead of creating another product copy.

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
