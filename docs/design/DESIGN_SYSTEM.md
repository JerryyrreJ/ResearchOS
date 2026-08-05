# ResearchOS Design System v0.2

## Product character

ResearchOS is an evidence-driven research instrument. It should feel editorial where researchers read and write claims, and technical where they inspect contracts, runs, diagnostics, hashes, and versions. Decoration never substitutes for provenance.

## Design principles

1. **Evidence becomes structure.** Relationships appear through alignment, rails, dependency lines, source markers, and semantic diffs.
2. **The thesis is primary.** Claims receive editorial typography and space; controls and metadata remain subordinate.
3. **Failure stays visible.** Error, warning, partial, stale, offline, and unsupported states use text plus shape, never color alone.
4. **Density follows task.** Reading surfaces are spacious. Tables, inspectors, and execution details are compact but stay above the minimum readable text size.
5. **Localization is structural.** UI strings are separated from research content. Research content preserves its original language and provenance.

## Localization

Supported interface locales:

- `zh-CN` — Simplified Chinese
- `zh-TW` — Traditional Chinese
- `en` — English

Research objects, source quotations, thesis claims, contract enums, IDs, hashes, and model output are not automatically translated. Translating those values could alter meaning or provenance. Locale switching changes navigation, system actions, explanations, and interface metadata.

Font stacks:

- Simplified Chinese: Geist → PingFang SC → Microsoft YaHei
- Traditional Chinese: Geist → PingFang TC → Noto Sans TC → Microsoft JhengHei
- English: Geist → system UI
- Claims and editorial display: Georgia / Songti fallback
- IDs, hashes, versions, and enum values: Geist Mono

## Geometry

Control heights:

- Compact: 28 px — table filters and dense inspector actions
- Default: 36 px — navigation, buttons, language controls
- Prominent: 44 px — authentication and primary entry actions

Radius:

- 3 px — buttons, inputs, language selector, badges
- 5 px — tables, execution panels, grouped sections
- 8 px — only large editorial containers

Pills are reserved for true tags or states. Containers never use fully rounded geometry.

## Responsive model

ResearchOS is device-agnostic; breakpoints respond to available width rather than browser user-agent strings.

| Mode | Width | Product structure |
|---|---:|---|
| Phone | `< 720 px` | Single-column reading surface, six-item bottom navigation, safe-area padding, Inspector as a bottom sheet |
| Tablet / iPad | `720–1180 px` | Persistent compact sidebar, one main workspace column, Inspector as a right-side drawer |
| Laptop / Desktop | `> 1180 px` | Persistent sidebar, central workspace, persistent contextual Inspector |

Tailwind CSS v4 owns the named `phone`, `tablet`, `laptop`, and `desktop` breakpoints plus container-query capability. Radix Dialog owns the accessible tablet/mobile Inspector overlay, focus trap, Escape behavior, and semantic title. Layout changes remain CSS-driven; JavaScript never detects device names.

Touch targets are at least 44 px for primary mobile actions. Fixed bottom navigation and drawers include `env(safe-area-inset-bottom)` for modern phones and tablets.

## Spacing

The spacing system uses a 4 px base: `4, 8, 12, 16, 24, 32`. Page-level reading margins may use 40–60 px on desktop. Alignment takes priority over introducing new spacing values.

## Color

- Ink `#17191b`: primary text and strong actions
- Research green `#245e54`: selection, confirmed evidence, active relationships
- Neutral surfaces `#ffffff / #f7f7f5 / #eeefec`: hierarchy without glass effects
- Error `#aa403c`: blocking failures
- Warning `#8d611c`: non-blocking attention
- Blue `#315f99`: running/recomputed technical state
- Purple `#675398`: proposed or semantic-change state

Color is never the sole status signal. Every status includes a text label or icon shape.

### Appearance modes

- `Light` is the neutral editorial default.
- `Dark` uses separate semantic surface and foreground tokens; it is not a mechanical inversion.
- `System` follows `prefers-color-scheme` and reacts when the operating-system setting changes.
- `High contrast` uses black, white, and a single yellow focus/accent token with explicit three-pixel focus rings.

Reduced motion is a first-class device preference. It suppresses non-essential transitions and status pulses without removing state feedback.

## Product identity

The ResearchOS sigil is the **Evidence Fold**: two observations converge through a third highlighted node and a short structural spine. It represents evidence becoming a bounded claim without falling back to a generic atom, brain, sparkle, or network-cloud symbol. The single-color silhouette remains legible from a 16 px favicon to the larger identity panel. It appears in the favicon, authentication threshold, sidebar, settings identity, and compact product marks. Object identity remains separate: Thesis, Evidence, Source, Validation, Model Run, and Version use their own typed markers and never borrow third-party logos.

## Extension center

The Extension Center follows the mature IDE convention of separating active, available, and restricted capabilities. A catalog entry is not proof of integration.

- `ENABLED` means the capability is registered in the current frozen contract.
- `AVAILABLE` is descriptive only and requires a reviewed integration contract before activation.
- `RESTRICTED` requires workspace or institutional policy approval.

The fixture may name recognized research services such as Zotero and OpenAlex, but must never imply authentication, data access, installation, or successful execution when none exists. Extension capability cannot bypass provenance, version pinning, evidence policy, or contract boundaries.

## References

- Apple Human Interface Guidelines: typography, color, layout, accessibility, and localization
- Apple Design Awards: interaction quality, inclusivity, visual craft, and understandable complex capability
- Linear Method: purpose-built tools, clarity, and simple-first progression
- Elicit: structured research tables, evidence traceability, and multi-step research workflows
- Hex: technical run state, parameters, results, and diagnostics

These references define quality criteria, not a visual collage. ResearchOS retains its own evidence, contract, and thesis hierarchy.
