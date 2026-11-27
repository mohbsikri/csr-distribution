# /generate-specification

## Purpose

Transform consolidated knowledge artifacts into structured draft specification artifacts.

This command implements Step 7 — Specification Generation of the CSR pipeline.

Specification generation is **non-interactive**. It derives content entirely from consolidated knowledge artifacts produced by `/consolidate-knowledge`. No new human decisions are collected during this stage.

This command operates as a **structural transformation runtime**. It applies a defined transformation procedure to consolidated knowledge artifacts to produce specification artifacts. The same consolidated input always produces the same specification output. This command does not change lifecycle state in any upstream artifact — no status field in any upstream artifact is modified by specification generation.

Draft specifications are the direct input to the Specification Stabilization stage. A draft specification is not stable until it has passed through Specification Stabilization review.

---

## STD v1 Template Mode

When the active workspace has `spec_template_version: v1` in `runtime/workspaces.md`, `/generate-specification` operates in **STD mode** (`template_mode = STD`). When the field is `legacy` or absent, **LEGACY mode** applies (`template_mode = LEGACY`).

**Mode routing is per-workspace.** Legacy workspaces are unaffected by STD-mode logic. STD workspaces never receive legacy 7-section output.

| Dimension | LEGACY mode | STD mode |
|---|---|---|
| Output format | Markdown bold header (7 fields) + 7 sections | YAML frontmatter (8 fields) + generation metadata block + S0–S15 + Annexes A/B |
| Section count | 7 (Terms, Context, Decisions, Assumptions, Constraints, BR, TR) | 15 sections (S0–S15) + 2 annexes |
| FR-NNN | Not generated | Derived from BR-NNN via DK projection |
| AC-NNN | Not generated | Derived from FR-NNN (Given/When/Then) |
| NFR-NNN | Not generated | Derived from C-NNN with category assignment |
| OP-NNN | Not generated | Generated from ADVISORY conflicts + US items |
| Traceability matrix | BR/TR/C columns | BR/TR/FR/AC/NFR/OP columns (STD extension) |
| SQF I1.1 count_traced | BR+TR+C rows in TM | FR+TR+NFR rows in STD TM |
| Inference Registry | `## Inference Registry` | `## Annexe A — Inference Registry` (same 4 subsections; S0 pre-populated) |
| Provenance section | `## Specification Provenance` (CONSOLIDATED) | `## Annexe B — Specification Provenance` (COND, multi-source ≥2) |

**KPM R4 cascade in STD mode:** FR-NNN inherits KPM type from BR-NNN source. AC-NNN inherits from FR-NNN. NFR-NNN inherits from C-NNN. A FR/AC/NFR derived from an ID-classified KB item enters the Inference Registry with the inherited ID classification. **No FR/AC/NFR item becomes ID:structural unless its source BR/C or derived FR meets S1–S4 criteria.**

**Content generation contract:** STD mode performs controlled traceable derivations: BR→FR (DK projection) and C→NFR (category mapping). These derivations are authorized by the ODQ-STD-02 resolution (Model D Hybrid Source-Aware). The verbatim constraint applies to all other sections (S1/S2/S4/S5/S14 reproduce source content verbatim). S0 is a deterministic synthesis of counts and cross-references only.

---

## Inputs

### Primary — Consolidated Knowledge Artifacts

```text
WORKSPACE_ROOT/knowledge_base/consolidated/*_consolidated.md
```

One specification is generated per consolidated artifact. Fields consumed:

| Field | Used For |
| ----- | -------- |
| `**Source Artifact:**` header field | Source traceability link |
| `**Consolidated Date:**` header field | Provenance |
| `**Conflicts Resolved:**` header field | Conflict incorporation tracking |
| All knowledge sections (Facts, Decisions, Assumptions, Constraints, Terminology, Business Rules, Technical Rules) | Specification content |
| `## Resolved Conflicts` table | Traceability (conflict_id, type, severity, question_id, resolution summary) |

This file is **read-only**. `/generate-specification` must not modify consolidated knowledge artifacts.

### Secondary — Consolidation Authority Record

```text
WORKSPACE_ROOT/knowledge_base/consolidated/consolidation_report.md
```

Read-only. Used to verify that all BLOCKING conflicts associated with a source are CONSOLIDATED before that source is eligible for specification generation.

Fields consumed:

| Field | Used For |
| ----- | -------- |
| Conflict ID | Eligibility cross-reference |
| Type | Conflict type dispatch — determines source group association for CONTRADICTION (dual-path) |
| Status (CONSOLIDATED) | BLOCKING conflict eligibility gate |
| Severity | BLOCKING vs ADVISORY distinction |
| Consolidated Artifact path | Primary source group binding (Item A for CONTRADICTION) |
| Consolidated Artifact (Secondary) path | Secondary source group binding for CONTRADICTION (Item B); absent for AMBIGUITY and GAP |

### Tertiary — Extracted Knowledge Artifacts (zero-conflict fallback)

```text
WORKSPACE_ROOT/knowledge_base/extracted/*_knowledge.md
```

Consumed **only** when no corresponding consolidated artifact exists for a given source — i.e., the source produced zero conflicts during `/detect-conflicts`. Such sources are internally consistent and conflict-free; their extracted artifact is spec-ready without consolidation.

This input is optional. When consumed, it is treated as a consolidated artifact with zero conflicts resolved.

These files are **read-only**.

### Quaternary — Conflicts Report (ADVISORY flag identification)

```text
WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md
```

Read-only. Used to identify ADVISORY conflicts associated with a source that have not yet been consolidated, enabling inline `[ADVISORY UNRESOLVED: <conflict_id> — awaiting consolidation]` flags to be inserted in the corresponding specification sections.

Fields consumed:

| Field | Used For |
| ----- | -------- |
| `**Conflict ID:**` | ADVISORY conflict identification |
| `**Type:**` | Conflict type dispatch for Conflicts Index construction (AMBIGUITY, GAP, or CONTRADICTION) |
| `**Severity:**` | ADVISORY vs BLOCKING discrimination |
| `**Section:**` | Target specification section — location is type-qualified: AMBIGUITY → `Section:` in `**Affected Item:**` block; GAP → annotation after ` — ` in `**Absent from:**` field; CONTRADICTION → `Item A Section:` and `Item B Section:` in `**Affected Items:**` block |
| `**Source:**` | Source artifact cross-reference (`<base>` extraction) — location is type-qualified: AMBIGUITY → `Source:` in `**Affected Item:**` block; GAP → path component of `**Absent from:**` field; CONTRADICTION → `Item A Source:` and `Item B Source:` in `**Affected Items:**` block |

This file is **read-only**. `/generate-specification` must not modify it.

If this file does not exist: ADVISORY unresolved conflict flags are omitted from all specifications in this execution. This is a WARNING condition only — it does not block specification generation.

### Optional — Generation Log (re-generation optimization)

```text
WORKSPACE_ROOT/specifications/draft/specifications_report.md
```

If this file exists, it may be consulted to identify previously generated specifications. Re-generation is subject to the lifecycle guard defined in the Eligibility section below — see the Re-generation paragraph.

---

## Outputs

### Draft Specification Artifacts

```text
WORKSPACE_ROOT/specifications/draft/<base>_specification.md
```

One file per processed source group. Named by replacing the source suffix:

```text
knowledge_base/consolidated/test_source_consolidated.md
→ specifications/draft/test_source_specification.md

knowledge_base/extracted/requirements_knowledge.md  (zero-conflict fallback)
→ specifications/draft/requirements_specification.md
```

This naming convention maintains the lineage established across prior stages:

```text
<base>_knowledge.md → <base>_consolidated.md → <base>_specification.md
```

### Traceability Matrix

```text
WORKSPACE_ROOT/specifications/draft/<base>_traceability.md
```

Maps every BR-NNN, TR-NNN, and C-NNN identifier in the specification back to its knowledge artifact section and source document. Generated alongside the specification draft. Contains zero data rows when no identifiers were found (file is still written).

### Generation Log

```text
WORKSPACE_ROOT/specifications/draft/specifications_report.md
```

A **generation audit log** recording which consolidated or extracted artifacts have been transformed into specifications, the output artifact path for each, and generation metadata. This record is informational — it does not gate whether a source group may be re-processed. Re-processing the same consolidated artifact produces an identical output (deterministic transformation).

### SQF Gate Report

```text
WORKSPACE_ROOT/specifications/draft/sqf_gate_report.md
```

A **quality gate report** produced by Phase 8.7 (Q-GATE-1) after specification and traceability matrix generation. It records the D1 (Complétude), D3 (Traçabilité), D5 (Testabilité), and D6 (Couverture Métier) indicator scores and a preliminary gate decision. D5 and D6 are informative only (PASS/WARN/NOT_APPLICABLE — never BLOCK). The D7 (Gouvernance des Inférences) section is added by the `/specification-lifecycle` E6 gate extension at BASELINE time.

The gate report is written for every execution regardless of gate outcome. If gate_status = BLOCK, the report documents blocking dimensions and required corrective actions. The report template is at `templates/sqf_gate_report_template.md`.

---

## Specification Model

**Model: One specification per source artifact.**

Each consolidated artifact produces exactly one draft specification. The naming lineage is preserved:

```text
<base>_knowledge.md → <base>_consolidated.md → <base>_specification.md
```

**Rationale:** Maintains per-source traceability, avoids requiring a cross-artifact domain classifier, and is consistent with the upstream artifact structure established in Milestones 2–6.

**Accepted trade-off:** Multiple specification files in the same workspace may contain related or overlapping content. A workspace-level aggregated specification is deferred to a future milestone.

**Zero-conflict sources:** A source that produced no conflicts has no consolidated artifact. Its extracted artifact is treated as spec-eligible. The resulting specification carries `Source Type: EXTRACTED` in its header block and contains no Specification Provenance section.

---

## Specification Conflict Model

Each conflict record in `conflicts_report.md` contributes specification entries as follows:

| Conflict Type | Specification Entries |
| ------------- | --------------------- |
| AMBIGUITY | One entry in the single source specification |
| GAP | One entry in the Absent From source specification |
| CONTRADICTION | One entry in the Item A specification AND one entry in the Item B specification |

A CONTRADICTION conflict produces entries in two distinct specifications — one per source artifact. This is the only conflict type that crosses specification boundaries.

---

## Conflict Ownership Model

Ownership determines which source group is responsible for processing a conflict and placing ADVISORY unresolved flags:

| Conflict Type | Owner |
| ------------- | ----- |
| AMBIGUITY | The single source group (`Source:` in `**Affected Item:**`) |
| GAP | The Absent From source group (path component of `**Absent from:**`) |
| CONTRADICTION | Both Item A source group AND Item B source group |

For ADVISORY unresolved conflict flags: each owning source group inserts `[ADVISORY UNRESOLVED: <conflict_id> — awaiting consolidation]` in the relevant section of its specification. A CONTRADICTION conflict produces one flag in the Item A specification and one flag in the Item B specification.

---

## Conflicts Index Contract

The Conflicts Index is a runtime structure mapping each `<base>` to the set of conflict entries relevant to its specification:

```text
Conflicts Index: <base> → [{conflict_id, conflict_type, severity, section}, ...]
```

Construction rules (type-dispatched):

| Conflict Type | Entries per Conflict | Section Source |
| ------------- | -------------------- | -------------- |
| AMBIGUITY | 1 (for the single source `<base>`) | `Section:` in `**Affected Item:**` block |
| GAP | 1 (for the Absent From source `<base>`) | annotation after ` — ` in `**Absent from:**` field (empty string if absent) |
| CONTRADICTION | 2 (one for Item A `<base>`, one for Item B `<base>`) | `Item A Section:` and `Item B Section:` from `**Affected Items:**` block |

---

## Provenance Contract

The `## Specification Provenance` section is present only in CONSOLIDATED-type specifications. It is populated verbatim from the source consolidated artifact's `## Resolved Conflicts` table.

For CONTRADICTION conflicts: the conflict appears in the Specification Provenance of both the Item A specification and the Item B specification. The `Specification Section` column references the section in each respective specification where the resolution applies.

EXTRACTED-type specifications carry no `## Specification Provenance` section.

---

## Eligibility

A source group is **eligible** for specification generation when ALL of the following hold:

1. A consolidated artifact exists for it in `knowledge_base/consolidated/` (preferred path), OR its extracted artifact exists in `knowledge_base/extracted/` with no associated conflicts (zero-conflict fallback).
2. Every BLOCKING conflict associated with this source is recorded as CONSOLIDATED in `consolidation_report.md`. A source with one or more BLOCKING conflicts that are not CONSOLIDATED is **ineligible** — no specification is generated for that source group. Source association is type-qualified: for AMBIGUITY and GAP, a conflict is associated with the source whose consolidated artifact path matches `Consolidated Artifact` in `consolidation_report.md`; for CONTRADICTION, a conflict is associated with the source when either the `Consolidated Artifact` path (Item A) or the `Consolidated Artifact (Secondary)` path (Item B) matches the source group's consolidated artifact path.

**Re-generation:** Re-generation is subject to the lifecycle guard. Before writing a draft specification, `/generate-specification` must check whether the lifecycle registry (`WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md`) exists. If it does, and the `spec_state_index` for this `<base>` records a status of BASELINED, SUPERSEDED, or ARCHIVED, generation is blocked and the human actor must use `/specification-lifecycle` to perform the appropriate lifecycle operation first. If the status is DRAFT (evolved) — identified by the presence of a `supersedes` field in the registry entry — generation proceeds and the `reserved_spec_id` from the registry is used as the Spec ID for this run. If the lifecycle registry does not exist, or no entry exists for `<base>`, generation proceeds normally. The full guard procedure is defined in `docs/commands/specification-lifecycle_execution.md` — Cross-Command Guard (A7) section.

**ADVISORY unresolved conflicts:** A source group with unresolved ADVISORY conflicts is eligible. The specification is generated from available consolidated content. Each unresolved ADVISORY item is flagged inline:

```text
[ADVISORY UNRESOLVED: <conflict_id> — awaiting consolidation]
```

---

## Specification Content Model

Each draft specification is a **structural reformatting** of its source consolidated artifact. No content invention, inference, paraphrase, summarization, or interpretation is permitted.

Content from the source artifact's knowledge sections is reorganized into the following specification sections, in this canonical order:

| Source Section | Specification Section | Order |
| -------------- | --------------------- | ----- |
| Terminology | 1. Terms and Definitions | 1st |
| Facts | 2. Context and Background | 2nd |
| Decisions | 3. Design Decisions | 3rd |
| Assumptions | 4. Assumptions | 4th |
| Constraints | 5. Constraints | 5th |
| Business Rules | 6. Business Rules | 6th |
| Technical Rules | 7. Technical Rules | 7th |

Sections absent from the source artifact are omitted from the specification. The section sequence above is canonical and must be preserved when present.

Resolution notes from the consolidated artifact are incorporated **verbatim** within their respective sections, attributed to the originating conflict ID.

### Spec-Level Design Sections

A draft specification may include sections beyond the seven knowledge-derived sections above — most commonly a **Data Model** section describing the information architecture derived from the functional requirements.

These sections contain design decisions made by CSR during specification generation. They are permitted additions to the specification structure. However, they must satisfy the following governance constraint (ADR-004 Engagement #6):

**Every element in a spec-level design section must carry an explicit provenance signal:**

- Each table in a spec-level section must include a `Source` column as the last column.
- `Source` values:
  - A knowledge base reference (BR-NNN, TR-NNN, C-NNN, or a validation ref such as `VAL-002 OP-001`) — the element is traceable to a KB item.
  - `—` — the element has no KB backing. It is a spec-level `INFERRED_DESIGN` decision and must appear in the Inference Registry (SG-18).
- Entire entities (tables/lists) introduced by the spec without any KB backing are declared by providing a header row with `Source = —` and are classified `INFERRED_DESIGN` with S1 (new entity) structural impact.

The presence of spec-level design decisions does not block specification generation. They are captured in the Inference Registry and governed by the BASELINE pre-condition (E6).

---

## Draft Specification Artifact Format

```markdown
# <Source Display Name> — Draft Specification

**Source Artifact:** knowledge_base/consolidated/<base>_consolidated.md
**Source Type:** CONSOLIDATED | EXTRACTED
**Generated:** <ISO 8601 date>
**Generation Command:** /generate-specification
**Conflicts Incorporated:** <comma-separated conflict_ids, or "none">
**Questions Incorporated:** <comma-separated question_ids, or "none">
**KPM Status:** PROVENANCE_INDEXED | NO_PROVENANCE_INDEX
**Status:** DRAFT

---

## 1. Terms and Definitions

<content from Terminology section>

## 2. Context and Background

<content from Facts section>

[... remaining sections in canonical order ...]

---

## Specification Provenance

| Specification Section | Conflict ID | Type | Severity | Question ID | Resolution Summary |
| --------------------- | ----------- | ---- | -------- | ----------- | ------------------ |
| Business Rules | C001 | AMBIGUITY | BLOCKING | Q001 | <one-line summary> |

---

## Inference Registry

### INFERRED_DESIGN — Impact Structurel

| ID | Rationale | Statut | Propagating |
|---|---|---|---|
| BR-015 | États non spécifiés ; alternatives valides | PENDING_VALIDATION | — |

### INFERRED_DESIGN — Détail d'Implémentation

| ID | Rationale | Statut |
|---|---|---|
| TR-003 | Valeur par défaut choisie parmi plusieurs options valides | REGISTERED |

### TECH_STANDARD

| ID | Standard | Statut |
|---|---|---|
| C-003 | ISO-3166-1 | ACKNOWLEDGED |

### UNDEFINED_IN_SOURCE

| ID | Statut |
|---|---|
| TR-012 | BLOCKED |
```

The `## Specification Provenance` section is included only for CONSOLIDATED-type specifications. It is omitted for EXTRACTED-type specifications.

**Spec-level design sections** (e.g., `## 5. Data Model`) appear before the `---` separator that precedes `## Specification Provenance`. Every table in a spec-level section includes a `Source` column:

```markdown
### 5.1 List: ExampleEntity

| Field | Type | Notes | Source |
|---|---|---|---|
| FieldA | Text | Derived from business rules | BR-001 |
| FieldB | Choice | Lifecycle states — spec-level decision | — |
```

Rows with `Source: —` are spec-level INFERRED_DESIGN decisions. They are detected by Step 6.5b (generate-specification_execution.md) and injected into the Inference Registry. See SG-18.

**Source Display Name:** The title from the source artifact's top-level `#` heading, with known pipeline suffixes stripped (` — Consolidated Knowledge`, ` — Source Knowledge`). If no title exists, use the base filename without extension.

---

## Traceability Rules

Every draft specification must be traceable to:

- Its source consolidated artifact (or extracted artifact for zero-conflict sources) via the `Source Artifact` header field.
- All conflicts incorporated via the `Conflicts Incorporated` header field and the `## Specification Provenance` table.
- All questions incorporated via the `Questions Incorporated` header field.

The full traceability chain is:

```text
specification artifact
  → consolidated artifact (Source Artifact header)
    → consolidation_report.md (conflict_id → question_id)
      → questions_report.md (question_id → Answer Source / session_id)
        → input/validations/<session_id>.md (validator, date, evidence)
          → source document (origin_path)
```

The specification carries enough anchors to make the chain navigable by following artifacts sequentially. It does not embed the full chain inline.

**CONTRADICTION forked traceability:** A CONTRADICTION conflict produces entries in two specifications. The chain forks at the consolidated artifact level:

```text
Item A specification  ←  Item A consolidated artifact ┐
                                                        ├─ conflict_id → question_id → validation → source
Item B specification  ←  Item B consolidated artifact ┘
```

Both specifications trace through the same conflict record in `consolidation_report.md`. The `Conflicts Incorporated` header field and `## Specification Provenance` table in each specification carry sufficient anchors to make both branches of the forked chain independently navigable.

---

## Traceability Matrix Rules

The traceability matrix artifact is generated for every processed source group, immediately after the specification draft is written.

**LEGACY mode:** The matrix maps BR-NNN, TR-NNN, and C-NNN identifiers to their origin: Provenance type (KPM classification), Knowledge section, Knowledge artifact path, Source document path. If no BR/TR/C identifiers are present, the matrix is generated with an empty table.

**STD mode:** The matrix maps all generated identifiers (BR-NNN, TR-NNN, FR-NNN, AC-NNN, NFR-NNN, OP-NNN) to their origin. FR-NNN and AC-NNN trace to the Knowledge Artifact via the Business Rules section (R4 chain from BR). NFR-NNN traces via the Constraints section (R4 chain from C). OP-NNN has no KB backing (Knowledge Artifact = `—`). Row order: BR ascending, TR ascending, FR ascending, AC ascending, NFR ascending, OP ascending.

The traceability matrix is a read-only derived artifact. It must never be edited directly.

---

## Language Policy

All draft specification artifacts must be written in English. This is guaranteed by the upstream pipeline under ADR-001 (CSR Language Policy): consolidated artifacts are in English, and specification generation is a structural reformatting operation on English content. No translation is performed at this stage.

If non-English content is detected in a source artifact, report an ADR-001 compliance failure for that source and do not generate a specification from it:

```text
STATUS: BLOCKED — ADR-001 Compliance Failure: non-English content detected in <artifact_path>. Upstream stage correction required.
```

---

## Preconditions

| ID | Precondition | Action on Failure |
| -- | ------------ | ----------------- |
| P1 | At least one `*_consolidated.md` file exists in `WORKSPACE_ROOT/knowledge_base/consolidated/`, OR at least one `*_knowledge.md` file exists in `WORKSPACE_ROOT/knowledge_base/extracted/` | Stop. Report no input artifacts. |
| P2 | `WORKSPACE_ROOT/knowledge_base/consolidated/consolidation_report.md` exists and is readable (required when any consolidated artifacts exist) | Stop. Report missing consolidation authority record. |
| P3 | `WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md` exists and is readable | WARNING only — ADVISORY unresolved conflict flags cannot be inserted if absent. Proceed without ADVISORY flags. |
| P4 | `WORKSPACE_ROOT/specifications/draft/` directory exists | Stop. Report missing output directory. |
| P5 | Workspace runtime resolves (R1–R6 pass) | Stop. Report workspace failure. |
| P6 | At least one eligible source group exists after eligibility determination | Stop. Report no eligible source groups. Report reasons for each ineligible group. |

---

## Failure Cases

The command must stop for the entire execution when:

- Workspace runtime fails to resolve.
- No input artifacts exist (no consolidated or extracted).
- `consolidation_report.md` does not exist when consolidated artifacts are present.
- `specifications/draft/` directory is inaccessible.
- No eligible source groups exist.
- A workspace isolation violation occurs.

The command continues (WARNING only) when:

- `knowledge_base/conflicts/conflicts_report.md` does not exist — ADVISORY unresolved conflict flags are omitted from all specifications in this execution.

Per-source-group failures: continue processing remaining eligible groups. Declare SPECIFICATION PARTIAL at completion.

Write failure after spec artifacts produced: append GENERATION FAILURE NOTE to affected spec files. Report all affected source groups.

---

## Constraints

- `knowledge_base/consolidated/*_consolidated.md` files must not be modified.
- `knowledge_base/extracted/*_knowledge.md` files must not be modified.
- `knowledge_base/consolidated/consolidation_report.md` must not be modified.
- `knowledge_base/conflicts/conflicts_report.md` must not be modified.
- No human decisions are collected during specification generation.
- No specification content is invented, inferred, paraphrased, summarized, or interpreted. All content is derived verbatim from the source artifact.
- All write operations must target `WORKSPACE_ROOT/specifications/draft/`.

---

## Completion States

| State | Condition |
| ----- | --------- |
| SPECIFICATION COMPLETE | All eligible source groups processed successfully |
| SPECIFICATION PARTIAL | At least one generated; at least one eligible group failed; or some groups are ineligible |
| SPECIFICATION BLOCKED | No eligible source groups exist, or all processing attempts failed |
| QUALITY BLOCKED | Specification generated; Q-GATE-1 Phase 7 produced gate_status = BLOCK on D1 or D3. The draft spec remains DRAFT. The sqf_gate_report.md documents the blocking dimensions and required actions. Pipeline does not advance to HITL-3 until corrective action is taken and /generate-specification is re-run. |

---

## Post-Execution Validation Rules

| Rule | Check |
| ---- | ----- |
| SG1 | Every specification in `specifications_report.md` with status GENERATED has a corresponding file at the declared path that exists and is readable. |
| SG2 | Every generated specification has a header block with `Source Artifact`, `Source Type`, `Generated`, `Generation Command`, `Conflicts Incorporated`, `Questions Incorporated`, `KPM Status`, and `Status: DRAFT` fields, all non-empty. |
| SG3 | `Conflicts Incorporated` in each CONSOLIDATED-type spec matches the `**Conflicts Resolved:**` header field of the source consolidated artifact. For EXTRACTED-type specs, `Conflicts Incorporated` is `none`. |
| SG4 | `Questions Incorporated` in each CONSOLIDATED-type spec matches the union of `question_id` values from the `## Resolved Conflicts` table of the source consolidated artifact. For EXTRACTED-type specs, `Questions Incorporated` is `none`. |
| SG5 | All write operations targeted paths within `WORKSPACE_ROOT/specifications/draft/`. |
| SG6 | `specifications_report.md` exists and is readable. |
| SG7 | All source consolidated artifacts are unmodified from their pre-execution state. |
| SG8 | All source extracted artifacts are unmodified from their pre-execution state. |
| SG9 | `consolidation_report.md` is unmodified from its pre-execution state. |
| SG10 | Every generated specification contains a `**Status:** DRAFT` field in its header block. |
| SG11 | Resolution notes in CONSOLIDATED-type specifications are preserved verbatim from the source consolidated artifact. No note was paraphrased, summarized, or removed. |
| SG12 | `specifications_report.md` `Last Updated` matches the ISO 8601 date of this execution. |
| SG13 | For each CONSOLIDATED-type specification generated when `conflicts_report.md` was available: every ADVISORY conflict whose ownership includes this source, that is NOT CONSOLIDATED in `consolidation_report.md`, is flagged inline as `[ADVISORY UNRESOLVED: <conflict_id> — awaiting consolidation]`. Ownership is type-qualified: AMBIGUITY → owned by the single source group; GAP → owned by the Absent From source group only; CONTRADICTION → owned by both Item A and Item B source groups (one flag appears in each). No such flag is present for any ADVISORY conflict that IS CONSOLIDATED. |
| SG14 | Traceability matrix file exists at `specifications/draft/<base>_traceability.md` for each GENERATED spec. | WARNING (non-blocking if write failed) |
| SG15 | Every generated `_specification.md` contains a `**KPM Status:**` field with value `PROVENANCE_INDEXED` or `NO_PROVENANCE_INDEX`. | BLOCKING |
| SG16 | Every generated `_specification.md` contains a `## Inference Registry` section with exactly 4 subsections in order: `INFERRED_DESIGN — Impact Structurel`, `INFERRED_DESIGN — Détail d'Implémentation`, `TECH_STANDARD`, `UNDEFINED_IN_SOURCE`. | BLOCKING |
| SG17 | The `Provenance` column is present in every generated `_traceability.md`, positioned after the `Type` column. | WARNING |
| SG18 | Every table in a spec-level design section present in the generated specification contains a `Source` column. Every row where `Source = —` has a corresponding entry in the Inference Registry under `INFERRED_DESIGN — Impact Structurel` or `INFERRED_DESIGN — Détail d'Implémentation`. An entire entity (table/list) declared without KB backing must appear as a structural entry (`impact_level: structural`). | BLOCKING |
| SG19 | `specifications/draft/sqf_gate_report.md` exists and contains a `gate_status` field with a valid value (`PENDING_D7`, `PASS`, `WARN`, or `BLOCK`). | BLOCKING |
| SG20 | `specifications_report.md` contains an SQF Gate entry for each processed source group with D1, D3, D5, and D6 statuses. If gate_status = BLOCK, the entry is annotated `QUALITY_BLOCKED`. | BLOCKING |

---

## Completion Criteria

The command is complete when:

- At least one draft specification was generated.
- A draft specification artifact exists at the declared path for each processed source group.
- `specifications_report.md` has been written or updated with GENERATED entries for each processed source group.
- Traceability matrix artifact written to `specifications/draft/<base>_traceability.md` for each processed source group.
- All SG1–SG14 validation rules pass.
- Every generated `_specification.md` contains a `**KPM Status:**` field (`PROVENANCE_INDEXED` or `NO_PROVENANCE_INDEX`).
- Every generated `_specification.md` contains a `## Inference Registry` section with exactly 4 subsections.
- Every generated `_traceability.md` contains a `Provenance` column after `Type`.
- In T-MODE (`NO_PROVENANCE_INDEX`) with no spec-level design decisions: all 4 Inference Registry subsections contain `*(aucun élément)*`. In T-MODE with spec-level design decisions detected by Step 6.5b: spec_design_map entries populate the appropriate subsections; extraction-level subsections remain `*(aucun élément)*`.
- All SG15–SG17 validation rules pass.
- SG18: every spec-level design section table has a `Source` column; every `Source = —` row has a corresponding Inference Registry entry.
- **Phase 8.7 — SQF Q-GATE-1:** `specifications/draft/sqf_gate_report.md` written with D1, D3, D5, and D6 scores (gate_status = PENDING_D7, PASS, WARN, or BLOCK). D5/D6 informative only — never BLOCK. SG19 and SG20 pass.
- If gate_status = BLOCK: `specifications_report.md` annotated QUALITY_BLOCKED; pipeline stops. Human must correct blocking items and re-run `/generate-specification`.
- If gate_status = PASS or WARN: pipeline continues to HITL-3 (human specification review) and then `/specification-lifecycle BASELINE`.
- The completion state (COMPLETE / PARTIAL / BLOCKED) has been reported.
