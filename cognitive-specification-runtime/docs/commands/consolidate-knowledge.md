# /consolidate-knowledge

## Purpose

Consume VALIDATED question records and resolved conflict data to produce transformed consolidated knowledge artifacts.

This command implements Step 6 — Knowledge Consolidation of the CSR pipeline.

It operates as the **Conflict Resolution Authority**: the only command authorized to transition questions from VALIDATED to RESOLVED and the only command that may write to `knowledge_base/consolidated/consolidation_report.md`.

Consolidation is non-interactive. It derives resolution content entirely from validated answers already recorded by `/human-validation`. No new human decisions are collected during consolidation.

---

## Inputs

The command reads:

### Canonical Question Records

```text
workspaces/<workspace_id>/knowledge_base/questions/questions_report.md
```

Fields consumed from each question record:

| Field | Used for |
| ----- | -------- |
| `question_id` | Traceability — links consolidated knowledge back to the originating question |
| `conflict_id` | Conflict mapping — associates the validated answer with its originating conflict |
| `Status` | Eligibility filter — only VALIDATED and eligible SUPERSEDED questions are consumed |
| `Answer` | Resolution content — the validated answer text used to resolve the conflict |
| `Decision` | Resolution content — the explicit decision appended to consolidated artifacts |
| `Evidence` | Traceability — evidence references preserved in consolidated artifacts |
| `Validated By` | Validation provenance — preserved in consolidated artifacts |
| `Validation Date` | Validation provenance — preserved in consolidated artifacts |

### Conflict Records

```text
workspaces/<workspace_id>/knowledge_base/conflicts/conflicts_report.md
```

This file is **read-only**. `/consolidate-knowledge` must not modify this file under any circumstances.

Fields consumed from each conflict record:

| Field | Used for |
| ----- | -------- |
| `conflict_id` | Conflict identity — links to associated question records |
| `Type` | Resolution strategy — AMBIGUITY, CONTRADICTION, or GAP determine how the consolidated artifact is transformed |
| `Severity` | Eligibility priority — BLOCKING conflicts require all questions VALIDATED before consolidation |
| `Source Artifact(s)` | Source artifact path(s) — identifies the extracted knowledge file(s) to transform; location is type-qualified: AMBIGUITY → `Source:` in `**Affected Item:**` block; GAP → path component of `**Absent from:**` field; CONTRADICTION → `Item A Source:` and `Item B Source:` in `**Affected Items:**` block |
| `Section(s)` | Transformation target(s) — section(s) where the conflict occurs; location is type-qualified: AMBIGUITY → `Section:` in `**Affected Item:**` block; GAP → annotation after ` — ` in `**Absent from:**` field; CONTRADICTION → `Item A Section:` and `Item B Section:` in `**Affected Items:**` block |
| `Content` | Transformation target — the specific conflicting content; applicable for AMBIGUITY (from `**Affected Item:**`) and CONTRADICTION (from `**Affected Items:**`); not applicable for GAP |

### Extracted Knowledge Artifacts

```text
workspaces/<workspace_id>/knowledge_base/extracted/*_knowledge.md
```

Source artifacts for transformation. These files are **read-only**. `/consolidate-knowledge` must not modify extracted knowledge artifacts under any circumstances.

### Knowledge Index Artifacts (optional — two-pass mode)

```text
workspaces/<workspace_id>/knowledge_base/extracted/*_knowledge_index.md
```

Compact index artifacts produced by `/extract-knowledge`. Used in two-pass mode when N > 5 knowledge sources are present to bound context load before targeted full-artifact loading.

### Consolidation Report (optional — re-run detection)

```text
workspaces/<workspace_id>/knowledge_base/consolidated/consolidation_report.md
```

If this file exists, it is read to identify already-consolidated conflicts and prevent reprocessing (idempotency). If it does not exist, this is the first consolidation run.

---

## Two-Pass Scalability Mode

When the workspace contains more than 5 knowledge sources, /consolidate-knowledge operates in two-pass mode:

**Pass 1 — Index Scan (bounded context):**
Load all knowledge index artifacts. For each open conflict being consolidated, identify which sources contain the relevant BR/TR/C items by matching IDs in the index.

**Pass 2 — Targeted Consolidation:**
Load only the full knowledge artifacts for sources identified as relevant in Pass 1. Execute consolidation on the targeted artifacts.

When N ≤ 5 sources, single-pass mode loads all full artifacts directly (existing behavior).

The two-pass mode does not change consolidation outputs, validation rules, or artifact formats.

---

## Outputs

### Consolidated Knowledge Artifacts

```text
workspaces/<workspace_id>/knowledge_base/consolidated/<base>_consolidated.md
```

**Standard Source Group (AMBIGUITY and GAP):** One consolidated artifact per unique source extracted knowledge artifact. Named by replacing the `_knowledge.md` suffix with `_consolidated.md`:

```text
knowledge_base/extracted/test_source_knowledge.md
→ knowledge_base/consolidated/test_source_consolidated.md
```

**PAIRED Source Group (CONTRADICTION):** A CONTRADICTION conflict spans two source extracted artifacts (Item A and Item B). It produces two consolidated artifacts — one per source artifact — written as an atomic pair. Both artifacts must be written and verified before the conflict is recorded as CONSOLIDATED. If the second write fails after the first succeeds, a PARTIAL_WRITE NOTE is appended to the first artifact and the conflict is recorded as CONSOLIDATION_FAILED. The naming convention applies to each source artifact independently.

Each consolidated artifact is a **transformed canonical artifact** — a restructured version of its source extracted knowledge with the conflict resolved using validated answers. It is not an annotation of the original. All source extracted artifacts remain unchanged.

### Consolidation Authority Record

```text
workspaces/<workspace_id>/knowledge_base/consolidated/consolidation_report.md
```

The single source of truth for conflict resolution status. This file records which conflicts have been consolidated, the consolidated artifact path for each, and the resolution summary for each conflict. No other artifact is authoritative for conflict resolution status.

### Updated Canonical Question Records

```text
workspaces/<workspace_id>/knowledge_base/questions/questions_report.md
```

For each question whose conflict was successfully consolidated, the canonical record is updated in place:

- `Status` field is updated to `RESOLVED`.
- Resolution fields are appended to the existing record.
- All original question fields and all answer and validation fields are preserved unchanged.

---

## Question Lifecycle

`/consolidate-knowledge` manages the final transition in the question lifecycle.

| Transition | Managed By | Condition |
| ---------- | ---------- | --------- |
| `VALIDATED → RESOLVED` | `/consolidate-knowledge` | The conflict associated with the question was successfully consolidated |

No other status transitions are applied by this command.

### RESOLVED Status

RESOLVED is a **terminal status** in the current pipeline version. A RESOLVED question may not be transitioned to any other status. Re-entry from RESOLVED is explicitly out of scope for the current version.

---

## SUPERSEDED Question Eligibility

A question with status SUPERSEDED is eligible for consolidation only if the replacement answer block (the answer appended after `**Superseded On:**`) contains:

- `**Validated By:**` — non-empty
- `**Validation Date:**` — non-empty

When a SUPERSEDED question is eligible, the replacement answer is used for consolidation. The original superseded answer is not used.

A SUPERSEDED question without a validated replacement is **not eligible**. The conflict associated with that question is not eligible for consolidation.

---

## Eligibility Rules

A conflict is **eligible** for consolidation when ALL of the following hold:

1. At least one question record in `questions_report.md` maps to this conflict via `conflict_id`.
2. Every question mapped to this conflict is at VALIDATED status, or is SUPERSEDED with a validated replacement.
3. The conflict's source artifact path(s) resolve to artifact(s) in `knowledge_base/extracted/`. For AMBIGUITY and GAP conflicts: the single source artifact path must resolve. For CONTRADICTION conflicts: BOTH the Item A source artifact path AND the Item B source artifact path must resolve to artifacts in `knowledge_base/extracted/`.

A conflict is **ineligible** when any of the following holds:

- No question records map to this conflict.
- Any question mapped to this conflict is at a status other than VALIDATED or eligible-SUPERSEDED.
- For AMBIGUITY or GAP: the conflict's source artifact path cannot be resolved. For CONTRADICTION: either the Item A or the Item B source artifact path cannot be resolved.

---

## Re-run Strategy

Consolidation is **incremental** and **idempotent**.

An already-consolidated conflict (recorded as CONSOLIDATED in `consolidation_report.md`) must never be reprocessed. Its `consolidation_report.md` entry must not be modified. Its consolidated artifact must not be overwritten.

When no new eligible conflicts exist (all eligible conflicts were consolidated on a prior run), the command reports CONSOLIDATION COMPLETE without modifying any artifact.

---

## Conflict Resolution Strategies

Resolution behavior is determined by conflict type:

| Conflict Type | Resolution Strategy |
| ------------- | ------------------- |
| AMBIGUITY | The validated answer defines or clarifies the ambiguous term or mechanism within the relevant section of the consolidated artifact |
| CONTRADICTION | The validated answer identifies the authoritative position; each source artifact (Item A and Item B) is transformed into its own consolidated artifact as an atomic PAIRED write; each consolidated artifact incorporates the resolution note identifying the authoritative position; both original statements are preserved in their respective artifacts |
| GAP | The validated answer fills the missing content in the relevant section of the consolidated artifact |

---

## Consolidated Artifact Format

Each consolidated artifact must include:

- A header block with the following required fields:
  - `**Source Artifact:**` — path to the source extracted knowledge file (relative to `WORKSPACE_ROOT`)
  - `**Consolidated Date:**` — ISO 8601 date of consolidation
  - `**Conflicts Resolved:**` — comma-separated list of `conflict_id` values resolved in this artifact
- All sections from the source extracted artifact, with resolutions applied per conflict type.
- A `## Resolved Conflicts` table listing each resolved conflict ID, type, severity, associated question ID, and a one-line resolution summary.

---

## Resolution Record Format

When a question is resolved, the following fields are appended to the canonical question record in `questions_report.md`, below the existing validated answer block:

```markdown
**Resolved By:** /consolidate-knowledge
**Resolution Date:** <ISO 8601 date>
**Consolidated Artifact:** knowledge_base/consolidated/<consolidated_filename>
**Consolidated Artifact (Secondary):** knowledge_base/consolidated/<Item B consolidated_filename>
```

The `**Consolidated Artifact (Secondary):**` field is present only when the question resolved a CONTRADICTION conflict. It is omitted for AMBIGUITY and GAP resolutions.

The `**Status:**` field is updated to `RESOLVED`.

---

## Conflict Resolution Record Format

Each processed conflict produces one record in `consolidation_report.md`. For AMBIGUITY and GAP conflicts (Standard Source Group):

```markdown
**Conflict ID:** <conflict_id>
**Type:** <AMBIGUITY | GAP>
**Severity:** <BLOCKING | ADVISORY>
**Status:** CONSOLIDATED
**Source Artifact:** knowledge_base/extracted/<source_filename>
**Consolidated Artifact:** knowledge_base/consolidated/<consolidated_filename>
**Question ID:** <comma-separated list of question_ids>
**Resolution Summary:** <one-line summary of the resolution applied>
**Consolidation Date:** <ISO 8601 date>
```

For CONTRADICTION conflicts (PAIRED Source Group), two additional fields are appended:

```markdown
**Conflict ID:** <conflict_id>
**Type:** CONTRADICTION
**Severity:** <BLOCKING | ADVISORY>
**Status:** CONSOLIDATED
**Source Artifact:** knowledge_base/extracted/<Item A source_filename>
**Consolidated Artifact:** knowledge_base/consolidated/<Item A consolidated_filename>
**Source Artifact (Secondary):** knowledge_base/extracted/<Item B source_filename>
**Consolidated Artifact (Secondary):** knowledge_base/consolidated/<Item B consolidated_filename>
**Question ID:** <comma-separated list of question_ids>
**Resolution Summary:** <one-line summary of the resolution applied>
**Consolidation Date:** <ISO 8601 date>
```

---

## Completion States

Three completion states are defined:

| State | Condition |
| ----- | --------- |
| CONSOLIDATION COMPLETE | All eligible conflicts were consolidated (including the case where all were already consolidated on a prior run) |
| CONSOLIDATION PARTIAL | At least one conflict consolidated; at least one eligible conflict failed transformation or write |
| CONSOLIDATION BLOCKED | No conflicts could be consolidated (no eligible conflicts, or all transformation attempts failed) |

---

## Preconditions

Before execution:

1. The repository structure must be valid.
2. The canonical question records must exist and be readable.
3. The conflict report must exist and be readable.
4. At least one `*_knowledge.md` file must exist in `knowledge_base/extracted/`.
5. The `knowledge_base/consolidated/` directory must exist.
6. At least one question with status VALIDATED or eligible-SUPERSEDED must exist.

---

## Failure Cases

The command must stop when:

- The canonical question records do not exist or cannot be read.
- The conflict report does not exist or cannot be read.
- No extracted knowledge artifacts exist.
- A consolidated artifact cannot be written.
- `consolidation_report.md` cannot be written after consolidated artifacts are produced.
- A question record cannot be updated after consolidation is recorded.
- A traceability violation is detected: a RESOLVED question has no corresponding CONSOLIDATED entry in `consolidation_report.md`.
- A workspace isolation violation occurs.

Failures must be reported explicitly. Partial writes must be flagged with RECOVERY NOTE entries in the canonical question records.

---

## Traceability Rules

Every consolidated artifact must be traceable to:

- The originating conflict (`conflict_id`) via the `## Resolved Conflicts` table.
- The originating question (`question_id`) via the `## Resolved Conflicts` table.
- The validation session (`Answer Source` / `session_id`) via the question record's answer block.
- The validator (`Validated By`, `Validation Date`) via the question record's validation block.

Every RESOLVED question record must reference:

- The command that resolved it (`Resolved By: /consolidate-knowledge`).
- The resolution date.
- The consolidated artifact path (`Consolidated Artifact`).
- For CONTRADICTION resolutions: the secondary consolidated artifact path (`Consolidated Artifact (Secondary)`).

**CONTRADICTION forked traceability:** A CONTRADICTION conflict's resolution produces two consolidated artifacts. The traceability chain forks: `consolidation_report.md` records both the primary path (Item A) and the secondary path (Item B). Both resolved question records trace through `consolidation_report.md` to the same `conflict_id` but diverge to separate consolidated artifacts. The chains converge at the conflict record.

`conflicts_report.md` is never modified. Conflict resolution status is tracked solely through `consolidation_report.md`.

---

## Constraints

- `knowledge_base/conflicts/conflicts_report.md` must not be modified.
- `knowledge_base/extracted/*_knowledge.md` files must not be modified.
- The VALIDATED → RESOLVED transition is owned exclusively by this command.
- RESOLVED is a terminal status. No further transitions are permitted.
- Already-consolidated conflicts must not be reprocessed.
- No human decisions are collected during consolidation. All resolution content is derived from validated answers in question records.

---

## Language Policy

Knowledge Consolidation performs no translation.

All canonical question records consumed by this command must contain English text in the `Answer`, `Evidence`, and `Decision` fields. This is guaranteed by the `/human-validation` language policy, which requires normalization and human confirmation before any response is written to a canonical record.

**Answer fidelity:** The rule "record the answer as provided" applies to the English-confirmed version produced during Human Validation. The English-normalized answer is the authoritative version. Consolidation applies it without modification or paraphrase.

**ADR-001 compliance check:** If non-English text is detected in the `Answer`, `Evidence`, or `Decision` fields of a canonical question record, this command must stop, report an ADR-001 compliance failure for that question record, and not proceed with consolidation of the affected conflict. Report:

```text
STATUS: BLOCKED — ADR-001 Compliance Failure: non-English content detected in <question_id> <field>. Human Validation normalization must be completed before consolidation can proceed.
```

---

## Completion Criteria

The command is complete when:

- At least one conflict was successfully consolidated.
- A consolidated artifact exists for each source group processed.
- `consolidation_report.md` has been written or updated with CONSOLIDATED entries for each processed conflict.
- All associated VALIDATED or eligible-SUPERSEDED questions have been updated to RESOLVED status in `questions_report.md`.
- All CK traceability and integrity checks pass.
- The completion state (COMPLETE / PARTIAL / BLOCKED) has been reported.
