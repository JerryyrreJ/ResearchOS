# MacroTrace v0.4 Frontend Design System

## 1. Design direction

MacroTrace is an institutional research operating system, not an AI chat landing page. The interface should make the research object, execution state, evidence graph and audit trail more visually important than the language model.

The selected direction is **Institutional Research OS**:

- dense but layered rather than spacious and promotional;
- cool white analytical surfaces on a light gray workspace;
- one blue action color, with teal/amber/red reserved for evidence state;
- compact sans-serif interface typography and monospaced IDs/parameters;
- serif typography only for final research claims and academic table titles;
- 1px borders, 3–4px radii and restrained shadows;
- no purple gradient, glassmorphism, glowing AI effects or oversized prompt hero.

## 2. Benchmarks and what was learned

### OpenBB Workspace

Source: <https://docs.openbb.co/workspace>

- Treat the application as an analyst workbench composed of inspectable data objects.
- Keep charts, tables, parameters and AI in one governed workspace.
- Use compact headers, linked parameters, small controls and modular analytical surfaces.
- MacroTrace adaptation: the query is one workbench control; the Research Graph and evidence objects are the product center.

### Palantir Workflow Lineage

Source: <https://www.palantir.com/docs/foundry/workflow-lineage/getting-started>

- Keep registered but unused nodes visible in a muted state.
- Highlight selected routes and linked dependencies.
- Use a graph canvas plus a detailed inspector rather than hiding provenance behind summary cards.
- MacroTrace adaptation: full Registry universe in gray, routed lanes in color, node click opens the seven-tab academic inspector.

### Observable Framework

Source: <https://observablehq.com/framework/>

- Let typography, grid and data graphics carry the interface.
- Use neutral surfaces and high-quality analytical hierarchy instead of decorative UI.
- MacroTrace adaptation: restrained report typography, tabular numerals, chart-first academic detail.
- License note: Observable Framework uses the permissive ISC license. No source was copied into MacroTrace in this redesign.

### Evidence

Source: <https://docs.evidence.dev/components/all-components>

- Use readable analytical tables, simple report sections and consistent component contracts.
- MacroTrace adaptation: three-line regression tables, compact export actions, diagnostics and robustness sections.
- License note: Evidence uses the MIT license. No source was copied into MacroTrace in this redesign.

## 3. Core tokens

| Role | Token | Value |
|---|---|---|
| Workspace | `--canvas` | `#eef0f3` |
| Primary surface | `--surface` | `#ffffff` |
| Secondary surface | `--surface-2` | `#f7f8fa` |
| Primary text | `--ink` | `#15191f` |
| Muted text | `--muted` | `#66707d` |
| Border | `--line` | `#d6dbe2` |
| Navigation | `--nav` | `#11161d` |
| Primary action / routed | `--blue` | `#1769d2` |
| Success | `--teal` | `#087b6c` |
| Warning | `--amber` | `#9a6100` |
| Failure | `--red` | `#b42318` |
| Supporting evidence | `--violet` | `#6555a6` |

Typography:

- UI and body: IBM Plex Sans + Noto Sans SC;
- IDs, states, parameters and small labels: IBM Plex Mono;
- final claims and academic table titles: Noto Serif SC.

## 4. Screen contract

1. The top navigation is a compact system bar, not a marketing header.
2. The research composer is visible at the top but becomes compact once a job is running or restored.
3. Job progress remains sticky below the system bar.
4. The synthesis card reports coverage, confidence, falsifiers and limitations before the graph.
5. The Research Graph occupies the main analytical canvas.
6. Registered but unrouted nodes remain visible with reduced opacity and dashed borders.
7. Node details open in a right-side inspector with Overview, Specification, Data & Variables, Results, Diagnostics, Robustness and Provenance.
8. Academic results use tabular numerals, three-line table rules and direct artifact exports.

## 5. Responsive behavior

- At tablet widths, top navigation collapses while system health remains visible.
- At phone widths, the research composer becomes a vertical stack and all controls use the full content width.
- The Research Graph remains a pannable canvas rather than shrinking node typography below legibility.
- The node inspector becomes full width on phones.

## 6. Implementation boundary

This redesign reuses MacroTrace's existing HTML, JavaScript graph renderer and FastAPI contracts. It does not copy proprietary OpenBB or Palantir source code, brand assets or trademarks. The benchmark products informed the information architecture and interaction principles; the implementation and visual tokens are original to MacroTrace.
