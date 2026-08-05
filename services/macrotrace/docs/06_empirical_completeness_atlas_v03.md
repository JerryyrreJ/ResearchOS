# MacroTrace v0.3 Empirical Completeness Atlas

## 1. Why this exists

MacroTrace must not confuse a valid model run with a complete answer. A large US
macro question is a research programme: it requires multiple economic mechanisms,
multiple measurements of each mechanism, competing model families, benchmarks,
falsifiers, diagnostics and an explicit aggregation rule. The compiler therefore
uses the evidence budgets below as hard coverage gates.

The budget counts pre-registered research roles, not significant coefficients.
Changing a window until a p-value becomes small, repeating the same regression
under cosmetic parameter changes, or duplicating one factor under several labels
does not increase research depth.

## 2. Question-complexity classes

| Class | Typical request | Required interpretation |
|---|---|---|
| `SIMPLE_MEASUREMENT` | “What is the latest unemployment rate?” | One official series can answer the measurement, with vintage and release lineage. |
| `STANDARD_FORECAST` | “What will next month’s CPI be?” | A target-specific forecast contest with benchmarks and rolling out-of-sample evaluation. |
| `SYSTEM_FORECAST` | “Is the US economy weakening or reaccelerating, and what is three-month recession risk?” | A multi-lane system view with mechanism-specific nodes, tail-risk evidence and cross-lane synthesis. |
| `CAUSAL_ATTRIBUTION` | “Has AI significantly increased US unemployment?” | Association evidence is insufficient. At least one defensible identification design must pass its own diagnostics before a causal final claim is allowed. |
| `STRUCTURAL_SCENARIO` | “What happens after a persistent tariff or oil shock?” | A registered structural or semi-structural transmission system with explicit shock definition and regime assumptions. |

## 3. Hard evidence budgets

### 3.1 System forecast

A `SYSTEM_FORECAST` may receive `FULL` coverage only when all of the following
are satisfied:

- at least 4 routed lanes;
- at least 4 routed mechanisms in every core lane;
- at least 12 distinct registered factors in every core lane;
- at least 10 pre-registered model specifications in every core lane;
- at least 3 genuinely different method families across the workflow;
- at least 2 benchmark specifications;
- rolling or expanding-origin out-of-sample evaluation for every predictive claim;
- at least 1 falsification node per core lane;
- at least 1 pre-registered alternative transform or sample-window robustness check;
- a visible aggregation specification with contribution and equal-weight sensitivity.

Failure of any hard item reduces coverage to `PARTIAL`; absence of executable
evidence for a central claim reduces it to `UNSUPPORTED`.

### 3.2 Causal attribution

A `CAUSAL_ATTRIBUTION` workflow must show at least 4 lanes, at least 5 mechanisms
in the central exposure/outcome lanes, at least 12 factors per core lane and at
least 10 planned specifications per core lane. Active and blocked specifications
are both visible, but blocked specifications do not count as executed evidence.

A causal conclusion additionally requires at least one registered identification
design with all required inputs and diagnostics. For a panel event-study or DID,
this includes:

- a pre-specified treatment/exposure measure and treatment timing;
- a comparison group and overlap/common-support assessment;
- fixed effects and covariance choices selected only from the recipe allow-list;
- event-time estimates and a joint pre-trend test;
- placebo or negative-control evidence;
- cluster-count and inference adequacy;
- robustness to the pre-registered alternative window/specification;
- no use of post-treatment variables as ordinary controls.

If these conditions are not available, the final status is
`UNSUPPORTED_CAUSAL`. MacroTrace may still report descriptive, predictive and
associational evidence, but it must not translate that evidence into a causal
claim or a probability.

## 4. Research-role taxonomy

Every model specification has one immutable role:

- `CORE`: primary pre-registered specification for a distinct mechanism/estimand;
- `BENCHMARK`: deliberately simple comparator such as an autoregression or equal-weight baseline;
- `ROBUSTNESS`: a pre-registered alternative sample, transform, lag or covariance choice;
- `FALSIFICATION`: placebo, negative control, pre-trend or other attempt to overturn a claim;
- `BLOCKED`: a scientifically required specification whose data or identification prerequisites are not met.

Robustness and falsification runs are not additional votes in aggregation. They
modify the credibility tier of the associated core estimate. Multiple model
specifications targeting the same estimand are first combined or retained as a
model set; they do not buy extra cross-lane weight.

## 5. Activity/recession mechanism atlas

The question “Is the US economy weakening or reaccelerating, and what is the
three-month recession risk?” is routed through, at minimum:

1. Production and output: industrial production, hours, manufacturing demand and
   broad activity indicators.
2. Household demand and real income: real consumption, retail control, disposable
   income and saving.
3. Labor demand and flows: payrolls, unemployment, vacancies, hires, quits,
   layoffs and claims.
4. Housing and interest-sensitive demand: permits, starts, sales and financing
   conditions.
5. Financial conditions and credit: NFCI, spreads, curve slope and real rates.
6. Inflation-real-income interaction: headline/core inflation and real purchasing
   power.
7. Downside/tail risk: recession indicators and conditional lower-tail growth.

The workflow must include target-specific univariate benchmarks, multivariate
bridge/DFM forecasts, a system model, a recession classification/tail-risk model,
and out-of-sample comparison. A single DFM or VAR cannot represent the entire
workflow.

## 6. AI–US labor mechanism atlas

The question “Has AI significantly increased US unemployment?” is decomposed into:

1. Firm adoption and exposure: Census BTOS adoption by sector/state/size and a
   separately reviewed occupational exposure crosswalk.
2. Vacancy demand: total and industry job openings, hires, vacancy rates and the
   AI content of job postings when a licensed source is available.
3. Displacement and layoffs: JOLTS layoffs/discharges, WARN or other reviewed
   displacement data and UI claims.
4. Unemployment flows: unemployment level/rate, claims, duration and labor-force
   transitions where available.
5. Wage adjustment: aggregate and industry wages, wage growth and deceleration.
6. Cohort and education incidence: youth unemployment/employment-population ratios
   and education-group outcomes.
7. Complementarity/productivity: employment expansion and productivity channels
   that can offset displacement.

The Deutsche Bank report `R11` supports this route as a descriptive and
correlational research map (firm adoption, vacancies, layoffs, wages and young
workers). It does not by itself supply causal identification. BTOS, BLS/CPS and
JOLTS can activate measurement and association nodes; DID/DDD/event-study nodes
remain visible but blocked until exposure, timing, comparison and pre-trend
requirements are met.

## 7. Graph contract

The Research Graph represents the full registered research universe:

- every lane appears, even when not routed;
- unrouted lanes, mechanisms, factors and specifications are grey and labelled
  `NOT_ROUTED`;
- routed but unavailable specifications remain visible as `BLOCKED` with the
  exact missing prerequisite;
- routed nodes are highlighted and can expand from lane → mechanism → research
  node → factor/data/transform → model specification → model run → diagnostic →
  evidence → lane signal → aggregation → final claim;
- every node has a detail endpoint. Non-model nodes expose definitions,
  assumptions, registry/report provenance and downstream effect; model runs add
  formula, variables, academic tables, diagnostics, robustness and artifacts;
- the header reports planned, executable, successful, blocked and not-routed
  counts separately. A folded “+N” never implies hidden model runs.

## 8. Data feasibility boundary (2026-07-14)

- BLS CPS provides monthly youth and education-group labor outcomes.
- BLS JOLTS provides monthly openings, hires, quits and layoffs/discharges,
  including industry detail.
- Census BTOS provides biweekly AI-use estimates by national, sector, state and
  firm-size strata. Time series require joining collection periods; some
  cross-strata and supplemental content require the official Excel files.
- O*NET provides downloadable occupation/task data, but MacroTrace will not invent
  an AI-exposure score from those tasks. An exposure score needs a reviewed,
  externally defined method and crosswalk before activation.

This boundary allows a much deeper real-data research graph immediately, but it
does not permit an identified causal verdict on AI and unemployment yet.
