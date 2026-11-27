# /generate-views

## Purpose

Generate audience-derived view artifacts from a BASELINED canonical specification.

This command implements ADR-003 — Specification Audience Model. It produces four audience-specific views derived from a BASELINED canonical specification. Views are generated artifacts; they are never governed by the specification lifecycle and must never be edited directly.

This command implements Step 9 — Audience View Generation of the CSR pipeline.

---

## Inputs

### Primary — BASELINED Canonical Specification

```text
WORKSPACE_ROOT/specifications/stable/<base>_specification.md
```

The canonical specification must carry BASELINED status:
- **STD specs** (first line is `---`): `status: BASELINED` in YAML frontmatter
- **LEGACY specs**: `**Status:** BASELINED` in Markdown bold header

Views are not generated from DRAFT specifications regardless of format.

---

## Outputs

Five view artifacts stored in:

```text
WORKSPACE_ROOT/specifications/views/<base>_view_metier.md
WORKSPACE_ROOT/specifications/views/<base>_view_archi.md
WORKSPACE_ROOT/specifications/views/<base>_view_dev.md
WORKSPACE_ROOT/specifications/views/<base>_view_qa.md
WORKSPACE_ROOT/specifications/views/<base>_view_agent.md
```

Updated generation log:

```text
WORKSPACE_ROOT/specifications/draft/specifications_report.md
```

After view generation, the `Views Status` column in the View Generation Records table of `specifications_report.md` is set to `CURRENT` for all VW rows generated in this run.

---

## Audience Profiles

| View suffix | Audience | Primary need |
|---|---|---|
| `_view_metier` | Product Owner, business stakeholders, end users | Functional understanding — what the system does, for whom, and why |
| `_view_archi` | Solution architect, technical lead, LCNC manager | Architecture, decisions, constraints, deployment |
| `_view_dev` | Power Platform developer, technical implementer | Implementation precision — schemas, formulas, identifiers, screen names |
| `_view_qa` | QA lead, test engineer | Testability — business rules as test conditions, edge cases, governance uncertainties as test risks |
| `_view_agent` | AI agents (Claude Code, pipeline agents) | Machine-readable structured content with stable typed identifiers |

Content scope for each profile is defined in ADR-003 — Specification Audience Model (`docs/decisions/ADR-003-specification-audience-model.md`).

---

## View Header

Every generated view carries the following header block:

```
STATUS: VIEW — DO NOT EDIT DIRECTLY
Canonical Source: specifications/stable/<base>_specification.md
Canonical Spec ID: <spec_id>
Canonical Status: BASELINED
Audience: <audience label>
Generated: <ISO date>
Generation Source: /generate-views
```

---

## AI Agent View Format

The `_view_agent` artifact uses Structured Markdown with explicit typed identifiers per ADR-003:

* YAML front-matter for machine-readable metadata
* `ENTITY[]`, `STATE_MACHINE[]`, `WORKFLOW[]`, `RULE[]`, `TERM[]`, `ACTOR[]` typed bracket notation
* Stable rule IDs: `BR-001`, `TR-001`, `C-001`
* No narrative prose — every line is a fact, rule, or structural element
* Explicit cross-references only — no pronouns, no implicit references

---

## Preconditions

1. Active workspace resolves correctly (standard W1–W5 resolution).
2. The canonical specification exists and is readable:
   ```text
   WORKSPACE_ROOT/specifications/stable/<base>_specification.md
   ```
3. The canonical specification carries BASELINED status:
   - STD spec (first non-empty line = `---`): `status: BASELINED` in YAML frontmatter
   - LEGACY spec: `**Status:** BASELINED` in Markdown bold header
   If status ≠ BASELINED in either format: BLOCKED.
4. The `specifications/views/` directory exists or can be created.
5. The generation log exists or can be created:
   ```text
   WORKSPACE_ROOT/specifications/draft/specifications_report.md
   ```

---

## Completion Criteria

Execution is complete when:

* All five view artifacts exist at their declared paths and are readable.
* Every view artifact carries the required header with `STATUS: VIEW — DO NOT EDIT DIRECTLY` and the correct canonical reference.
* The generation log has been updated with a View Generation Records table entry for each generated view.
* Generation log Views Status updated to CURRENT for all generated view rows.

---

## Failure Handling

Stop and report when:

* Workspace resolution fails at any W step.
* The canonical specification does not exist or is not in BASELINED status.
* Any view artifact write fails.

Continue with remaining views when a single view write fails; declare GENERATE-VIEWS PARTIAL at completion.

---

## KPM / Inference Governance Filtering (ADR-004 WP-4)

View artifacts apply audience-aware filtering of KPM (Knowledge Provenance Model) data and Inference Governance information present in the canonical specification. Filtering rules by view are defined in `templates/commands/generate_views_prompt.md` — KPM Filtering Policy section.

**Principle:** The canonical specification remains complete and unfiltered. Views surface only the KPM/governance information relevant to their audience. Omission is intentional and audience-aware in human-facing views. The `_view_agent` artifact always includes the complete Inference Registry verbatim — no filtering applies.

**PENDING_VALIDATION alert:** Views `_view_metier` and `_view_qa` surface INFERRED_DESIGN structural PENDING_VALIDATION elements as explicit human-readable alerts. These alerts are not a failure condition; they inform the stakeholder or QA lead that design decisions require validation before development or testing begins.

---

## STD Spec Support (spec_template_version: v1)

When the canonical specification is a STD spec (YAML frontmatter, generated by /generate-specification in STD mode), /generate-views adapts its parsing and content sourcing without changing the five output view types or the view file format.

**Format detection:** First non-empty line `---` → STD; anything else → LEGACY.

**Key differences in STD parsing vs LEGACY:**

| Aspect | LEGACY | STD |
|---|---|---|
| Status field | `**Status:** BASELINED` | `status: BASELINED` in YAML |
| Spec ID | `**Spec ID:** SP-NNN` | `spec_id: SP-NNN` in YAML |
| Baseline Date | `**Baseline Date:** date` | `baseline_date: date` in YAML |
| KPM Status | `**KPM Status:**` in header | `**KPM Status:**` in generation metadata block (body) |
| Inference Registry | `## Inference Registry` | `## Annexe A — Inference Registry` |
| Business Rules | `## 6. Business Rules` | Section 5.1 BR table (Section 5) |
| Constraints/NFR | `## 5. Constraints` (C-NNN) | Section 11 NFR table (NFR-NNN) |
| Open Points | ADVISORY UNRESOLVED flags | Section 13 OP-NNN table |
| Actor Profiles | Derived from BR section | Section 3 Profils Utilisateurs |
| Out of Scope | Inferred from Facts | Section 12 Hors Périmètre |

**YAML body exclusion rule:** The YAML frontmatter block (content between the two `---` delimiters at the start of the file) must never appear as rendered content in any view. Only the spec body (content after the YAML closing `---`) is used for section parsing.

**View output unchanged:** All five views are generated with identical file names, header structure, and format for both LEGACY and STD canonical specs.

---

## Lifecycle Governance

Views are **not** governed by `/specification-lifecycle`. They:

* Are never BASELINED, REOPENED, EVOLVED, or ARCHIVED.
* Are regenerated automatically when the canonical spec transitions to a new BASELINED version.
* Stale views (from a prior baseline) are overwritten without lifecycle ceremony.
* Any correction goes to the canonical specification first; views are then regenerated via `/generate-views`.

---

## Relationship to Pipeline

| Stage | Command | Output |
|---|---|---|
| 7 | `/generate-specification` | Canonical spec (DRAFT) |
| 8 | `/specification-lifecycle BASELINE` | Canonical spec (BASELINED) |
| 9 | `/generate-views` | 5 audience view artifacts |

`/generate-views` requires Stage 8 to be complete before it can run.

---

## Expected Output Summary

```text
WORKSPACE_ROOT/specifications/views/<base>_view_metier.md   ← new or overwritten
WORKSPACE_ROOT/specifications/views/<base>_view_archi.md    ← new or overwritten
WORKSPACE_ROOT/specifications/views/<base>_view_dev.md      ← new or overwritten
WORKSPACE_ROOT/specifications/views/<base>_view_qa.md       ← new or overwritten
WORKSPACE_ROOT/specifications/views/<base>_view_agent.md    ← new or overwritten
WORKSPACE_ROOT/specifications/draft/specifications_report.md ← updated in-place
```

No other repository areas are modified by this command.
