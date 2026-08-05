# ResearchOS：版本化数据、金融研究与实证验证工作台

The integrated product uses Role D's financial-research workspace as the browser entry and
Role B's Python application as the backend foundation. Files and plugin datasets first enter
Role A's immutable asset/version layer; Role C compiles claims; MacroTrace executes registered
empirical validation without weakening evidence boundaries.

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

## Start the integrated product

On Windows, one command creates both environments, installs the optional data providers, runs
the migrations, starts the Python API and opens the integrated Role D workspace:

```powershell
.\start.ps1
```

Open http://127.0.0.1:3000. The default product supports:

1. drag files into the ResearchOS workspace and inspect immutable version history;
2. select a registered FRED or AKShare dataset and persist it as a versioned Asset;
3. generate a report data sheet from exact dataset versions and SHA-256 references;
4. open B's original MacroTrace workbench inside the D shell, with the current research
   question prefilled; run the registered empirical workflow, diagnostics and research graph there.

The `MacroTrace` navigation item is intentionally B's original interface, not a visual rewrite:
the D shell embeds the workbench served at `NEXT_PUBLIC_MACROTRACE_UI_URL` (default
`http://127.0.0.1:8000`). It passes the research question into B and receives terminal run
status back through a same-origin-checked browser message. The original B console remains
available directly at http://127.0.0.1:8000. To start only the backend and that console:

```powershell
.\start.ps1 -BackendOnly
```

## Manual frontend start

Requires Node.js 22.13 or newer.

```bash
cd apps/web
npm ci
npm run dev
```

Open http://localhost:3000. The workspace exposes file intake, immutable versions, backend
data plugins, report production, Thesis compilation and the frozen Tool Adapter.

The browser client defaults to `http://127.0.0.1:8000/api/v1`; the original MacroTrace frame
defaults to `http://127.0.0.1:8000`. To point either surface elsewhere, set
`NEXT_PUBLIC_RESEARCHOS_API_BASE_URL` or `NEXT_PUBLIC_MACROTRACE_UI_URL` before starting the web app.
The backend accepts the documented local development ports by default; override them with
`RESEARCHOS_CORS_ORIGINS`.

## Data plugins

The integrated Python backend exposes selectable AKShare and FRED plugins. They appear in the
Role D data-source settings and the research-output studio. Every fetched table is stored
through Role A as an immutable, content-hashed AssetVersion before the report studio or Role B
can resolve it.

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

The integration work is on `integration-v2` and intentionally reuses the existing A, B, C and
D implementations instead of creating another product copy.

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
