# Consolidate Knowledge Execution Specification

## Purpose

Define the runtime execution procedure for the `/consolidate-knowledge` command.

The objective is to consume VALIDATED question records from the canonical question registry, resolve the underlying conflicts identified during `/detect-conflicts`, produce transformed consolidated knowledge artifacts, update the consolidation authority record, and transition all resolved question records to RESOLVED status.

This specification implements Step 6 — Knowledge Consolidation of the CSR pipeline.

---

## Execution Flow

```text
Workspace Resolution
↓
Artifact Loading
↓
Two-Pass Source Selection (N > 5 only)
↓
Eligibility Discovery
↓
Re-run Resolution
↓
Resolution Preparation
↓
Knowledge Transformation
↓
Consolidation Report Update
↓
Question Status Update
↓
Traceability Validation
↓
Post-Execution Validation
```

---

## Runtime Version Reference

The runtime version is referenced throughout this specification as `CURRENT_RUNTIME_VERSION`.

At execution time, `CURRENT_RUNTIME_VERSION` must be read from:

```text
docs/implementation_status.md
```

Locate the section `## Current Version` and extract the version value.

This value must never be hardcoded. Every reference to `CURRENT_RUNTIME_VERSION` is a runtime-resolved placeholder.

---

## Preconditions

Before execution begins, verify:

| ID | Precondition | Action on Failure |
| -- | ------------ | ----------------- |
| P1 | `docs/commands/consolidate-knowledge.md` exists and is readable | Stop. Report missing contract. |
| P2 | Workspace runtime resolves (R1–R7 pass in Phase 1) | Stop. Report workspace failure. |
| P3 | `WORKSPACE_ROOT/knowledge_base/questions/questions_report.md` exists and is readable | Stop. Report missing question registry. |
| P4 | `WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md` exists and is readable | Stop. Report missing conflict report. |
| P5 | `WORKSPACE_ROOT/knowledge_base/extracted/` contains at least one `*_knowledge.md` file | Stop. Report missing extracted knowledge. |
| P6 | `WORKSPACE_ROOT/knowledge_base/consolidated/` directory exists | Stop. Report missing consolidated directory. |
| P7 | At least one question with status VALIDATED (or SUPERSEDED with a validated replacement) exists in the question registry | Stop. Report no eligible questions. Do not produce output artifacts. |

If any precondition fails, report the failure explicitly and stop. Do not proceed to execution.

---

## Phase 1 — Workspace Resolution

### Objective

Establish the active workspace root path and validate workspace integrity before any artifact operation.

### R1 — Read Current Workspace

Read:

```text
runtime/current_workspace.md
```

Parse the `workspace_id` value from:

```text
workspace_id: <value>
```

### R2 — Build Workspace Root

Construct:

```text
WORKSPACE_ROOT = workspaces/<workspace_id>/
```

All subsequent artifact paths are constructed as `WORKSPACE_ROOT + <relative path within workspace>`.

### R3 — Verify Workspace Root

Confirm the directory `WORKSPACE_ROOT` exists.

If not found:

```text
STATUS: BLOCKED — Workspace Root Not Found: workspaces/<workspace_id>/
```

Stop execution.

### R4 — Validate Registry Entry

Read `runtime/workspaces.md`. Locate the row where `workspace_id` matches the value from R1.

#### R4a — Workspace ID Present

If no matching row exists:

```text
STATUS: BLOCKED — Workspace Drift Detected: workspace_id '<value>' not found in runtime/workspaces.md
```

Stop execution.

#### R4b — Status Field

If the matching row `status` is `archived`:

```text
STATUS: BLOCKED — Workspace Archived: workspace_id '<value>' must not be used for active processing
```

Stop execution.

If the matching row `status` is `paused` or `completed`:

```text
STATUS: WARNING — Workspace Drift: registry status is '<status>' for workspace_id '<value>'
```

Document the discrepancy. Continue with caution.

#### R4c — runtime_version Field

If `runtime_version` is empty or missing:

```text
STATUS: WARNING — Registry Entry Incomplete: runtime_version missing for workspace_id '<value>'
```

Continue.

#### R4d — last_active Field

If `last_active` is empty or missing:

```text
STATUS: WARNING — Registry Entry Incomplete: last_active missing for workspace_id '<value>'
```

Continue.

#### R4e — Single Active Entry

If more than one registry row has `status: active`:

```text
STATUS: WARNING — Workspace Drift: multiple active entries in runtime/workspaces.md
```

Use `runtime/current_workspace.md` as the authority. Continue.

### R5 — Confirm Resolution

Report:

```text
Active workspace: <workspace_id>
WORKSPACE_ROOT: workspaces/<workspace_id>/
```

### R6 — Isolation Enforcement

All file operations must target paths prefixed with `WORKSPACE_ROOT`.

Shared exception paths (not workspace-scoped):
- `runtime/current_workspace.md`
- `runtime/workspaces.md`
- `docs/`
- `templates/`
- `.claude/`

Any operation targeting a path outside `WORKSPACE_ROOT` that is not on the exception list must be rejected immediately:

```text
STATUS: BLOCKED — Workspace Contamination: <path> is outside WORKSPACE_ROOT and not on the exception list
```

**STATUS: WORKSPACE RESOLVED**

---

## Phase 2 — Artifact Loading

### Objective

Load all input artifacts required for knowledge consolidation. Verify artifact integrity. Build the data structures consumed in downstream phases.

### Inputs

```text
WORKSPACE_ROOT/knowledge_base/questions/questions_report.md          ← primary: question records
WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md          ← primary: conflict records
WORKSPACE_ROOT/knowledge_base/extracted/                             ← source knowledge artifacts
WORKSPACE_ROOT/knowledge_base/consolidated/consolidation_report.md  ← optional: re-run state
```

### Actions

**Step 2.1** — Read `WORKSPACE_ROOT/knowledge_base/questions/questions_report.md` in full.

Parse all question records from the `## Questions` section. For each `### Q<NNN>` block, extract:

| Field | Location in record |
| ----- | ------------------ |
| `question_id` | `### Q<NNN>` section header |
| `conflict_id` | `**Conflict ID:**` field |
| `conflict_type` | `**Conflict Type:**` field |
| `severity` | `**Severity:**` field |
| `status` | `**Status:**` field |
| `answer_text` | `**Answer:**` field in the primary answer block (if present) |
| `validated_by` | `**Validated By:**` field in the primary answer block (if present) |
| `validation_date` | `**Validation Date:**` field in the primary answer block (if present) |
| `decision` | `**Decision:**` field in the primary answer block (if present) |
| `evidence` | `**Evidence:**` field in the primary answer block (if present) |
| `superseded_on` | `**Superseded On:**` field (if present — indicates question is SUPERSEDED) |
| `replacement_answer_text` | `**Answer:**` field in the block immediately following `**Superseded On:**` (if present) |
| `replacement_validated_by` | `**Validated By:**` field in the replacement block (if present) |
| `replacement_validation_date` | `**Validation Date:**` field in the replacement block (if present) |
| `replacement_decision` | `**Decision:**` field in the replacement block (if present) |
| `replacement_evidence` | `**Evidence:**` field in the replacement block (if present) |

Apply status normalization: treat all status values as case-insensitive during loading. Normalize to UPPERCASE internally. The upstream value `validated` is equivalent to `VALIDATED`.

**Step 2.1a** — ADR-001 Language Compliance Check.

For each VALIDATED or eligible-SUPERSEDED question record: verify that the `answer_text`, `decision`, and `evidence` fields contain English text.

This command performs no translation. All canonical question records must contain English content, as required by ADR-001 (CSR Language Policy) and guaranteed by the `/human-validation` language normalization requirement.

If non-English content is detected in any of these fields for any eligible question:

```text
STATUS: BLOCKED — ADR-001 Compliance Failure: non-English content detected in <question_id> <field>. Human Validation normalization must be completed before consolidation can proceed.
```

Stop execution immediately. Do not proceed with conflict loading or any further execution steps. The affected conflict is not eligible for consolidation until the upstream compliance gap is resolved.

**Step 2.2** — Read `WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md` in full.

This file is a READ-ONLY input. It must not be modified at any point during execution.

Parse all conflict records from the `## Conflicts` section. For each `### C<NNN>` block, first extract the universal fields:

| Field | Location in record |
| ----- | ------------------ |
| `conflict_id` | `### C<NNN>` section header |
| `type` | `**Type:**` field |
| `severity` | `**Severity:**` field |
| `status` | `**Status:**` field (informational only — not managed by this command) |
| `description` | `**Description:**` field |

Then apply type-dispatched extraction for source artifact path(s) and section(s):

**AMBIGUITY conflicts** (`type == AMBIGUITY`): Locate the `**Affected Item:**` block. Extract:
- `source_artifact_path` — `Source:` line within the block
- `section` — `Section:` line within the block
- `content` — `Content:` line within the block
- `reason` — `Reason:` line within the block
- Set `source_artifact_path_B = null`

**CONTRADICTION conflicts** (`type == CONTRADICTION`): Locate the `**Affected Items:**` block. Extract from the `Item A:` sub-block:
- `source_artifact_path` — `Item A Source:` value (Item A; used as primary)
- `section` — `Item A Section:` value
- `content_A` — `Item A Content:` value

Extract from the `Item B:` sub-block:
- `source_artifact_path_B` — `Item B Source:` value (Item B; secondary)
- `section_B` — `Item B Section:` value
- `content_B` — `Item B Content:` value

**GAP conflicts** (`type == GAP`): Locate the `**Absent from:**` field. Parse:
- `absent_path` — path component before ` — ` (or full value if no ` — ` separator)
- `absent_section` — annotation after ` — ` (or null if no separator)
- `source_artifact_path` — equals `absent_path`
- `section` — equals `absent_section`
- `present_in_path` — value of the `**Present in:**` field (reference only; not a transformation target)
- Set `source_artifact_path_B = null`

**PARTIAL RECORD DETECTED check**: After loading consolidation_report.md (Step 2.4), for every CONTRADICTION conflict whose `conflict_id` is present in the Already-Consolidated Set: verify that its consolidation_report.md record contains a non-empty `**Consolidated Artifact (Secondary):**` field. If this field is absent or empty:

```text
STATUS: BLOCKED — PARTIAL RECORD DETECTED: conflict <conflict_id> has CONSOLIDATED status but is missing **Consolidated Artifact (Secondary):** in consolidation_report.md. Manual resolution required before re-run.
```

Stop execution. Do not classify this conflict as SKIP. Do not proceed.

**Step 2.3** — List all files matching `*_knowledge.md` in `WORKSPACE_ROOT/knowledge_base/extracted/`. Verify each file is accessible and readable. Build the **Extracted Knowledge Inventory**: a mapping of normalized filename → full file path and file content.

Normalize the `source_artifact_path` values from conflict records (strip any leading `knowledge_base/extracted/` prefix) to match against this inventory.

**Step 2.4** — Check whether `WORKSPACE_ROOT/knowledge_base/consolidated/consolidation_report.md` exists.

- If it exists: read it in full. Parse the `## Summary` table. Extract all rows where the `Status` column value is `CONSOLIDATED`. Record these `Conflict ID` values as the **Already-Consolidated Set**.
- If it does not exist: the Already-Consolidated Set is empty. This is the first consolidation run.

### Failure Conditions

- `questions_report.md` cannot be read → stop. Report read failure and path.
- A question record field required for eligibility determination (`question_id`, `conflict_id`, `status`) cannot be parsed → stop. Report the `question_id` and missing field.
- A VALIDATED or eligible-SUPERSEDED question record's `answer_text`, `decision`, or `evidence` field contains non-English text → stop. Report ADR-001 compliance failure for the affected `question_id` and field. Do not consolidate the associated conflict.
- `conflicts_report.md` cannot be read → stop. Report read failure and path.
- A conflict record's `source_artifact_path` is absent or empty after type-dispatched extraction → stop. Report the `conflict_id`. For CONTRADICTION: if either `source_artifact_path` (Item A) or `source_artifact_path_B` (Item B) is absent, stop and report the `conflict_id` and which path is missing.
- `knowledge_base/extracted/` is inaccessible or contains no `*_knowledge.md` files → stop. Report P5 failed.
- `knowledge_base/consolidated/` is inaccessible → stop. Report P6 failed.

### Output

```text
Question Record Set: <N> records parsed
Conflict Record Set: <N> records parsed
Extracted Knowledge Inventory: <N> artifacts
Already-Consolidated Set: <list of conflict_ids, or 'empty — first run'>
```

**STATUS: ARTIFACTS LOADED — \<N\> questions, \<N\> conflicts, \<N\> extracted artifacts**

---

## Phase 0.5 — Two-Pass Source Selection

### Objective

Determine which full knowledge artifacts to load for each open conflict being consolidated.

### Condition

Runs when N > 5 knowledge sources. When N ≤ 5, skip this phase and load all full artifacts (single-pass).

### Actions (Two-Pass Mode)

**Pass 1 — Index Scan:**
1. Load all knowledge index files: `WORKSPACE_ROOT/knowledge_base/extracted/<base>_knowledge_index.md`
2. For each open conflict record (from conflicts_report.md), read the conflict's source references (the knowledge artifacts named in the conflict record).
3. Identify which sources are directly referenced by the conflict.
4. For CONTRADICTION conflicts: both Item A and Item B sources are in the candidate set.
5. Build Candidate Set per conflict: the sources directly named in that conflict's record, plus any source whose index contains an ID mentioned in the conflict.

**Pass 2 — Targeted Load:**
1. For each conflict being consolidated: load only the full knowledge artifacts in its Candidate Set.
2. Proceed to existing consolidation logic.

### Output

```text
Per-conflict Candidate Sets — for each open conflict, the list of source names whose full artifacts will be loaded.
```

---

## Phase 3 — Eligibility Discovery

### Objective

Determine which conflicts are eligible for consolidation in this execution.

Build the Eligible Conflict Set and the Ineligible Conflict Set.

### Eligibility Definition

A conflict is **eligible** for consolidation when ALL of the following conditions are met:

1. At least one question record in the question registry maps to this `conflict_id` (matching by `conflict_id` field in the question record).
2. Every question record mapping to this `conflict_id` has a normalized status of VALIDATED, OR has normalized status SUPERSEDED with a validated replacement (see SUPERSEDED Eligibility Rule below).
3. For AMBIGUITY and GAP conflicts: the conflict's `source_artifact_path` resolves to an artifact present in the Extracted Knowledge Inventory. For CONTRADICTION conflicts: BOTH `source_artifact_path` (Item A) AND `source_artifact_path_B` (Item B) resolve to artifacts present in the Extracted Knowledge Inventory.

A conflict is **INELIGIBLE** when any of the following is true:

- No question records in the question registry map to this `conflict_id`.
- ANY question record mapping to this `conflict_id` has a normalized status that is NOT VALIDATED and NOT eligible-SUPERSEDED.
- For AMBIGUITY or GAP: the conflict's `source_artifact_path` cannot be resolved to an artifact in the Extracted Knowledge Inventory.
- For CONTRADICTION: either `source_artifact_path` (Item A) or `source_artifact_path_B` (Item B) cannot be resolved to an artifact in the Extracted Knowledge Inventory.

### SUPERSEDED Eligibility Rule

A question with normalized status SUPERSEDED is eligible for consolidation if AND ONLY IF:

- The replacement answer block (the block following `**Superseded On:**` in the question record) contains a non-empty `**Validated By:**` field (`replacement_validated_by`).
- The replacement answer block contains a non-empty `**Validation Date:**` field (`replacement_validation_date`).

If either field is absent or empty in the replacement block, the SUPERSEDED question is NOT eligible. The conflict associated with that question is INELIGIBLE.

When a SUPERSEDED question is eligible, the consolidation must use the replacement answer text, replacement decision, and replacement evidence — not the original superseded values.

### Actions

**Step 3.1** — For each conflict in the Conflict Record Set:

  a. Find all question records where `conflict_id` matches the conflict's ID.

  b. If no matching question records exist: classify the conflict as INELIGIBLE. Record reason: "No associated questions found in questions_report.md."

  c. For each matching question record, apply the eligibility conditions:
     - If normalized status is VALIDATED: eligible question.
     - If normalized status is SUPERSEDED and both `replacement_validated_by` and `replacement_validation_date` are non-empty: eligible question (replacement answer will be used).
     - Otherwise: ineligible question. Record the `question_id` and its status.

  d. If ALL matching questions are eligible: classify the conflict as ELIGIBLE.

  e. If ANY matching question is ineligible: classify the conflict as INELIGIBLE. Record reason: "Question `<question_id>` has status `<status>` — VALIDATED or eligible-SUPERSEDED required."

**Step 3.2** — Build:
  - **Eligible Conflict Set**: all conflicts classified as ELIGIBLE.
  - **Ineligible Conflict Set**: all conflicts classified as INELIGIBLE with their recorded reasons.

**Step 3.3** — If the Eligible Conflict Set is empty: report the Ineligible Conflict Set with reasons. Declare completion state CONSOLIDATION BLOCKED. Stop. Do not produce output artifacts.

**Step 3.4** — Report both sets.

### Output

```text
Eligible Conflict Set: <list of conflict_ids>
Ineligible Conflict Set: <list of conflict_ids with reasons>
```

**STATUS: ELIGIBILITY DISCOVERY COMPLETE — \<N\> eligible, \<M\> ineligible**

---

## Phase 4 — Re-run Resolution

### Objective

Apply the incremental and idempotent re-run strategy. Separate conflicts that have already been consolidated from those requiring processing in this execution.

### Actions

**Step 4.1** — If the Already-Consolidated Set is empty: all conflicts in the Eligible Conflict Set are NEW. Proceed to Phase 5 with the full Eligible Conflict Set as the Processing Set.

**Step 4.2** — If the Already-Consolidated Set is non-empty:

  a. For each conflict in the Eligible Conflict Set: check whether its `conflict_id` is present in the Already-Consolidated Set.

  b. If present: classify as SKIP (already consolidated — idempotent; do not reprocess).

  c. If not present: classify as NEW (requires processing in this execution).

**Step 4.3** — Build:
  - **Processing Set**: all conflicts classified as NEW.
  - **Skip Set**: all conflicts classified as SKIP.

**Step 4.4** — If the Processing Set is empty: all eligible conflicts are already consolidated. No new work to perform. Declare completion state CONSOLIDATION COMPLETE. Stop without modifying any artifact.

**Step 4.5** — Report the Processing Set and Skip Set.

### Idempotency Rule

An already-consolidated conflict (present in the Already-Consolidated Set) must NEVER be reprocessed. Its existing entry in consolidation_report.md must not be modified. Its existing consolidated artifact must not be overwritten. This rule holds even if source artifacts changed since the prior consolidation run.

### Output

```text
Processing Set: <list of conflict_ids to process>
Skip Set: <list of conflict_ids already consolidated — skipped>
```

**STATUS: RE-RUN RESOLUTION COMPLETE — \<N\> to process, \<M\> already consolidated**

---

## Phase 5 — Resolution Preparation

### Objective

Assemble the complete Resolution Context for each conflict in the Processing Set. The Resolution Context contains all data required to transform source extracted knowledge into consolidated knowledge.

### Source Group Model

Two Source Group types exist. The type is determined by the conflict's `type` field.

**Standard Source Group (AMBIGUITY and GAP):** Multiple AMBIGUITY or GAP conflicts may reference the same source extracted knowledge artifact. Group these by their `source_artifact_path`. Each unique source artifact path produces one Standard Source Group → one consolidated artifact.

**PAIRED Source Group (CONTRADICTION):** Each CONTRADICTION conflict forms its own PAIRED Source Group regardless of whether other conflicts share the same source artifact paths. A PAIRED Source Group has two source artifact paths (`source_artifact_path` for Item A and `source_artifact_path_B` for Item B) and produces two consolidated artifacts (one per source artifact) as an atomic pair.

**PAIRED Completeness Check:** Before proceeding for each PAIRED Source Group, verify that BOTH `source_artifact_path` and `source_artifact_path_B` resolve to readable artifacts in the Extracted Knowledge Inventory. If either is unresolvable: mark the conflict as CONSOLIDATION_FAILED. Report the missing path. Continue with remaining Source Groups.

### Actions

**Step 5.1** — For each Source Group:

  a. Identify the source extracted knowledge artifact: resolve `source_artifact_path` to its entry in the Extracted Knowledge Inventory. Read the full content into context.

  b. For each conflict in the Source Group:

     - Load the full conflict record (type, severity, description, section, content, reason).
     - Load all associated question records from the Question Record Set.
     - For each VALIDATED question: extract the answer text, decision, and evidence.
     - For each eligible-SUPERSEDED question: extract the replacement answer text, replacement decision, and replacement evidence (from the block following `**Superseded On:**`).

**Step 5.2** — Build the **Resolution Map** for each Source Group:

```text
Resolution Map (per Source Group):
  <conflict_id>:
    type: <AMBIGUITY | CONTRADICTION | GAP>
    severity: <BLOCKING | ADVISORY>
    section: <section header in source artifact where conflict occurs>
    content: <conflicting content as recorded in the conflict record>
    reason: <why it is a conflict>
    resolution_text: <validated answer text (or replacement answer text if SUPERSEDED)>
    decision: <validated decision text (or 'None')>
    evidence: <validated evidence reference (or 'None')>
    question_ids: <comma-separated list of all associated question_ids>
```

**Step 5.3** — Determine the consolidated artifact output path(s) for each Source Group:

```text
Consolidated Artifact Naming Rule:
  source_filename = basename of the source_artifact_path
  base = source_filename with '_knowledge.md' suffix removed
  consolidated_filename = base + '_consolidated.md'
  output_path = WORKSPACE_ROOT + 'knowledge_base/consolidated/' + consolidated_filename
```

Example:
```text
source_artifact_path: knowledge_base/extracted/test_source_knowledge.md
source_filename:       test_source_knowledge.md
base:                  test_source
consolidated_filename: test_source_consolidated.md
output_path:           WORKSPACE_ROOT/knowledge_base/consolidated/test_source_consolidated.md
```

For PAIRED Source Groups (CONTRADICTION): apply the naming rule independently to both `source_artifact_path` (Item A) and `source_artifact_path_B` (Item B), producing `output_path_A` and `output_path_B` respectively.

If the source artifact filename does not end with `_knowledge.md`, append `_consolidated` before the `.md` extension.

### Failure Conditions

- Source artifact content cannot be read from the Extracted Knowledge Inventory → stop for this Source Group. Report the source path. Mark all conflicts in this Source Group as CONSOLIDATION_FAILED. Continue with remaining Source Groups.
- A conflict record field required for the Resolution Map is absent → stop for that conflict. Report the `conflict_id` and missing field. Mark the conflict as CONSOLIDATION_FAILED. Continue with remaining conflicts in the Source Group.

### Output

```text
Source Groups:
  <source_artifact_path>:
    Conflicts: <list of conflict_ids>
    Output path: <consolidated artifact output path>
    Resolution Map: <built and ready>
```

**STATUS: RESOLUTION CONTEXT BUILT — \<N\> source groups, \<N\> conflicts prepared**

---

## Phase 6 — Knowledge Transformation

### Objective

Transform each source extracted knowledge artifact into a consolidated knowledge artifact by applying all resolutions in the Resolution Map. Write consolidated artifacts to disk. Do not modify source artifacts.

### Transformation Procedure

For each Source Group in the Resolution Context:

**Step 6.1** — Read the source extracted knowledge artifact content in full. Record its content as the base for transformation. Do not modify the source artifact at any point during or after this step.

**Step 6.2** — For each section in the source artifact (identified by `#` headers), determine whether any conflict in the Resolution Map targets that section (match by the `section` field in the Resolution Map).

**Step 6.3** — Apply resolutions:

For **AMBIGUITY** conflicts targeting a section:
- Locate the ambiguous term or statement identified in the conflict's `content` field within that section.
- If the ambiguity is an undefined term: add the validated definition immediately following or within the relevant section. Use the format: `- **<term>** — <validated definition>` in the `# Terminology` section, or a clearly labeled definition within the targeted section if Terminology is not the target.
- If the ambiguity is an underspecified rule or mechanism: append a resolution note to the relevant item within the section using the format: `  > Resolution (conflict_id): <resolution_text>`

For **CONTRADICTION** conflicts (PAIRED Source Group):

CONTRADICTION conflicts produce TWO consolidated artifacts as an atomic pair. Apply the following procedure:

- **Item A consolidated artifact**: Read Item A's source extracted artifact. Locate the section identified by `section` (Item A's section). Within that section, locate the contradicting statement identified by `content_A`. Preserve Item A's original statement and append a resolution note:
  ```
  > Conflict <conflict_id> resolved: <resolution_text>
  ```
- **Item B consolidated artifact**: Read Item B's source extracted artifact. Locate the section identified by `section_B` (Item B's section). Within that section, locate the contradicting statement identified by `content_B`. Preserve Item B's original statement and append the same resolution note.

Each consolidated artifact incorporates the authoritative position established by the validated answer. Neither artifact deletes the original contradicting statement; each preserves its own source statement alongside the resolution note.

**PAIRED atomic write sequence** (enforced in Step 6.5 and Step 6.6):

```
Step 6.P1: Write Item A consolidated artifact to output_path_A
Step 6.P2: Verify Item A artifact (file exists, readable, ## Resolved Conflicts present)
Step 6.P3: Write Item B consolidated artifact to output_path_B
Step 6.P4: Verify Item B artifact (file exists, readable, ## Resolved Conflicts present)
Step 6.P5: If Item B write or verification fails after Item A succeeded:
           → Append PARTIAL_WRITE NOTE to Item A artifact
           → Mark conflict as CONSOLIDATION_FAILED
           → Do not record as CONSOLIDATED in consolidation_report.md
           → Continue with remaining Source Groups
```

PARTIAL_WRITE NOTE format (appended to Item A artifact when Step 6.P5 triggers):

```markdown
> **PARTIAL_WRITE NOTE:** /consolidate-knowledge failed to complete the PAIRED write for conflict <conflict_id>. Item A consolidated artifact was written but Item B write failed. Manual resolution required. Do not use this artifact for specification generation until the PAIRED write is completed.
```

For **GAP** conflicts targeting a section:
- Locate the section with the missing content identified in the conflict's `content` field.
- Insert the validated content under a clearly labeled subsection: `### Gap Resolution (<conflict_id>)` followed by the `resolution_text`.

**Step 6.4** — Assemble the complete consolidated artifact using the following format:

```markdown
# <source display name> — Consolidated Knowledge

**Source Artifact:** knowledge_base/extracted/<source_filename>
**Consolidated Date:** <ISO 8601 date>
**Conflicts Resolved:** <comma-separated list of conflict_ids resolved in this artifact>

---

<all sections from the source artifact with resolutions applied per Step 6.3>

---

## Resolved Conflicts

| Conflict ID | Type | Severity | Question ID | Resolution Summary |
| ----------- | ---- | -------- | ----------- | ------------------ |
| C001        | AMBIGUITY | BLOCKING | Q001   | <one-line summary of the resolution applied> |
```

The `<source display name>` is derived from the source artifact's `# <title>` header. If no title header is present, use the base name of the source artifact file without extension.

**Step 6.5** — Write the assembled consolidated artifact to the output path determined in Phase 5.

- If the output path does not exist: write the new file.
- If the output path already exists and ALL conflict IDs in this Source Group are in the Already-Consolidated Set (Skip Set): this is an inconsistency between Phase 4 classification and the artifact state. Stop. Report the inconsistency. Do not overwrite.
- If the output path already exists and this Source Group includes NEW conflicts not previously consolidated: read the existing artifact. Append new resolution entries in the `## Resolved Conflicts` table and apply additional resolutions to the relevant sections. Update the `Conflicts Resolved` header to include the newly added conflict IDs. Report this as a PARTIAL_UPDATE.

**Step 6.6** — Verify the consolidated artifact after writing:

- Confirm the file exists and is readable.
- Confirm it contains a `## Resolved Conflicts` section with at least one row.
- Confirm the `Conflicts Resolved` header field lists all conflict IDs processed for this Source Group (including any from prior runs already in the file).

### Source Artifact Preservation

The source extracted knowledge artifact (`*_knowledge.md`) must not be modified under any circumstances. Transformation applies to the in-memory content assembled for the consolidated artifact. The source artifact file on disk must remain byte-for-byte identical before and after execution.

### Failure Conditions

- Consolidated artifact cannot be written → stop for this Source Group. Report the output path. Mark all conflicts in this Source Group as CONSOLIDATION_FAILED. Do not update consolidation_report.md for this Source Group.
- Conflict-artifact path inconsistency detected (Step 6.5, second condition) → stop. Report. Manual resolution required.

### Output

```text
Consolidated artifacts written:
  <consolidated_artifact_path> (source groups: <N> conflicts resolved)
```

**STATUS: KNOWLEDGE TRANSFORMATION COMPLETE — \<N\> artifacts produced**

---

## Phase 7 — Consolidation Report Update

### Objective

Write or update `WORKSPACE_ROOT/knowledge_base/consolidated/consolidation_report.md` to reflect the results of this execution. This file is the sole authority for conflict resolution status.

### Consolidated Conflict Record Format

Each processed conflict produces one conflict resolution record in consolidation_report.md.

For AMBIGUITY and GAP conflicts:

```markdown
### <conflict_id>

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

For CONTRADICTION conflicts (PAIRED Source Group), append secondary artifact fields:

```markdown
### <conflict_id>

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

For conflicts that failed transformation (CONSOLIDATION_FAILED):

```markdown
### <conflict_id>

**Conflict ID:** <conflict_id>
**Type:** <type>
**Severity:** <severity>
**Status:** CONSOLIDATION_FAILED
**Failure Reason:** <description of why transformation failed>
**Consolidation Date:** <ISO 8601 date>
```

### First Execution (consolidation_report.md does not exist)

Write the complete file:

```markdown
# Consolidation Report

## Metadata
- Last Updated: <ISO 8601 date>
- Total Conflicts Processed: <N>
- Consolidated: <N>
- Consolidation Failed: <N>
- Ineligible (not processed): <N>

---

## Summary

| Conflict ID | Type | Severity | Status | Consolidated Artifact | Consolidation Date |
| ----------- | ---- | -------- | ------ | --------------------- | ------------------ |
| <C<NNN>>    | <type> | <severity> | CONSOLIDATED | knowledge_base/consolidated/<filename> | <YYYY-MM-DD> |

---

## Conflict Resolution Records

<one ### C<NNN> block per conflict processed>
```

### Re-run Execution (consolidation_report.md exists)

Do NOT overwrite the existing file contents. Apply incremental updates:

1. Update `## Metadata`: update `Last Updated` date and update totals to include the new entries.
2. Append new rows to the `## Summary` table for each newly processed conflict.
3. Append new `### C<NNN>` conflict resolution records for each newly processed conflict.
4. Do NOT modify any existing conflict record entries. Existing rows and blocks are immutable.

### Actions

**Step 7.1** — For each conflict in the Processing Set that was successfully transformed in Phase 6: build the CONSOLIDATED conflict resolution record using the format above.

**Step 7.2** — For each conflict in the Processing Set that failed transformation in Phase 6: build the CONSOLIDATION_FAILED record using the format above.

**Step 7.3** — Write or update consolidation_report.md per the format rules above (first execution or re-run).

**Step 7.4** — Verify consolidation_report.md after writing:
  - Confirm it contains entries for every conflict in the Processing Set.
  - Confirm no existing entries (from the Skip Set or prior runs) were modified.
  - Confirm the `Last Updated` date is the current execution date.

### Constraint — conflicts_report.md Is Immutable

`WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md` must not be read during this phase for modification purposes and must not be written to under any circumstances. The `Status: open` field in conflicts_report.md is the snapshot state written by `/detect-conflicts`. It is not managed by `/consolidate-knowledge`.

### Failure Conditions

- consolidation_report.md cannot be written → stop. Append RECOVERY NOTE to all question records that would have been transitioned to RESOLVED. Report write failure and affected conflict IDs. Do not proceed to Phase 8.
- consolidation_report.md content after write does not match expected content → re-read and verify. If mismatch persists: stop. Report and stop.

**STATUS: CONSOLIDATION REPORT UPDATED — \<N\> conflicts recorded**

---

## Phase 8 — Question Status Update

### Objective

Transition all VALIDATED and eligible-SUPERSEDED questions associated with successfully consolidated conflicts to RESOLVED status in `WORKSPACE_ROOT/knowledge_base/questions/questions_report.md`.

### RESOLVED Transition Rule

The transition VALIDATED → RESOLVED is owned exclusively by `/consolidate-knowledge`. No other command may apply this transition.

RESOLVED is a terminal status. No further lifecycle transitions are defined from RESOLVED in the current version.

### Eligibility for RESOLVED Transition

A question is eligible for the RESOLVED transition in this execution if:
- Its normalized status is VALIDATED or eligible-SUPERSEDED.
- Its `conflict_id` maps to a conflict with status CONSOLIDATED in consolidation_report.md (successfully processed in Phase 6 and recorded in Phase 7).

Questions associated with CONSOLIDATION_FAILED conflicts must NOT be transitioned to RESOLVED.

### Write Ordering

Phase 8 must execute AFTER Phase 6 (consolidated artifacts written) and Phase 7 (consolidation_report.md updated). This write ordering guarantees that if a Phase 8 write fails, both the consolidated artifacts and the consolidation_report.md are already in a consistent state and can be used for recovery and re-run.

### Update Procedure

For each eligible question:

**Step 8.1** — Read the current state of the question record from `WORKSPACE_ROOT/knowledge_base/questions/questions_report.md`.

**Step 8.2** — Verify all original fields are intact and will not be modified:
- `question_id`
- `conflict_id`
- `Conflict Type`
- `Severity`
- Full question text
- Full Context block
- All existing answer blocks (Answer, Answer Source, Answer Date, Evidence, Decision, Validated By, Validation Date, Superseded On, Superseded By Session, and all replacement block fields)

**Step 8.3** — Append the resolution block below the existing validated answer block (or replacement block for SUPERSEDED questions):

```markdown
**Resolved By:** /consolidate-knowledge
**Resolution Date:** <ISO 8601 date>
**Consolidated Artifact:** knowledge_base/consolidated/<consolidated_filename>
```

For questions whose conflict is CONTRADICTION: append one additional field immediately after `**Consolidated Artifact:**`:

```markdown
**Consolidated Artifact (Secondary):** knowledge_base/consolidated/<Item B consolidated_filename>
```

This field is omitted for AMBIGUITY and GAP resolutions.

**Step 8.4** — Update the `**Status:**` field in the question record to `RESOLVED`.

**Step 8.5** — Update the `## Summary` table row for this question in questions_report.md: change the `Status` column value from `VALIDATED` (or `SUPERSEDED`) to `RESOLVED`.

**Step 8.6** — Verify the updated question record:
- All original fields unchanged.
- Resolution block present and complete (Resolved By, Resolution Date, Consolidated Artifact — all non-empty).
- `**Status:**` field is `RESOLVED`.

### Failure Conditions

- A question record cannot be read → stop. Report the `question_id`. Do not proceed with remaining questions. Report all successfully updated and not-yet-updated question IDs.
- A question record update cannot be written → stop. Append RECOVERY NOTE to all successfully updated question records. Report.
- Required resolution field is missing → stop for that question. Report the missing field.

**STATUS: QUESTION RECORDS UPDATED — \<N\> questions resolved**

---

## Phase 9 — Traceability Validation

### Objective

Verify cross-artifact consistency and traceability after all writes are complete. Confirm no workspace contamination occurred. Confirm all integrity constraints hold.

### Checks

**Step 9.1 — Question-to-Conflict Traceability**

For every question with status RESOLVED in questions_report.md after this execution:
- Confirm there is a corresponding entry in consolidation_report.md where `Conflict ID` matches the question's `conflict_id` and `Status` is `CONSOLIDATED`.

Violation type: TRACEABILITY VIOLATION — BLOCKING.

**Step 9.2 — Conflict-to-Artifact Traceability**

For every conflict with status CONSOLIDATED in consolidation_report.md (including prior runs):
- Confirm the `Consolidated Artifact` path exists as a readable file.
- Confirm the file contains a `## Resolved Conflicts` table with a row for this `conflict_id`.
- For CONTRADICTION conflicts: confirm the `Consolidated Artifact (Secondary)` field is non-empty, the path exists as a readable file, and the file contains a `## Resolved Conflicts` table with a row for this `conflict_id`.

Violation type: TRACEABILITY VIOLATION — BLOCKING.

**Step 9.3 — Source Artifact Integrity**

For each file in the Extracted Knowledge Inventory:
- Confirm no modifications were made to any `*_knowledge.md` file during this execution.

Violation type: INTEGRITY VIOLATION — BLOCKING.

**Step 9.4 — Conflict Report Integrity**

Confirm `WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md` is unmodified from its state loaded in Phase 2. The file must be byte-for-byte identical to its loaded content.

Violation type: INTEGRITY VIOLATION — BLOCKING.

**Step 9.5 — Skip Set Integrity**

For each conflict in the Skip Set:
- Confirm its entry in consolidation_report.md is unchanged.
- Confirm its consolidated artifact is unchanged.

Violation type: INTEGRITY VIOLATION — BLOCKING.

### Failure Response

Any BLOCKING violation → report the violation rule, the affected artifact path, and the specific violation. Do not declare a successful completion state. Require manual resolution.

### Output

```text
Step 9.1: <PASS | FAIL — list of violations>
Step 9.2: <PASS | FAIL — list of violations>
Step 9.3: <PASS | FAIL — list of violations>
Step 9.4: <PASS | FAIL — list of violations>
Step 9.5: <PASS | FAIL — list of violations>
```

**STATUS: TRACEABILITY VALIDATED**

---

## Phase 10 — Failure Handling

### Stop Conditions

| Condition | Response |
| --------- | -------- |
| `docs/commands/consolidate-knowledge.md` missing | Stop. Report P1 failed. |
| `questions_report.md` cannot be read | Stop. Report read failure and path. |
| `conflicts_report.md` cannot be read | Stop. Report read failure and path. |
| `knowledge_base/extracted/` has no `*_knowledge.md` files | Stop. Report P5 failed. |
| `knowledge_base/consolidated/` is inaccessible | Stop. Report P6 failed. |
| Question record field required for eligibility cannot be parsed | Stop. Report `question_id` and missing field. |
| Conflict record `source_artifact_path` is absent or unresolvable | Stop. Report `conflict_id`. |
| Zero eligible conflicts after eligibility discovery | Stop. Report ineligible set with reasons. Completion state: CONSOLIDATION BLOCKED. |
| Processing Set is empty (all already consolidated) | Stop without modification. Completion state: CONSOLIDATION COMPLETE. |
| Source artifact cannot be read for transformation | Stop for that Source Group. Mark conflicts CONSOLIDATION_FAILED. Continue other Source Groups. |
| Consolidated artifact cannot be written | Stop for that Source Group. Mark conflicts CONSOLIDATION_FAILED. Continue other Source Groups. |
| Conflict-artifact path inconsistency (Phase 6, Step 6.5) | Stop. Report. Manual resolution required. |
| consolidation_report.md cannot be written | Stop. Append RECOVERY NOTE to all would-be RESOLVED questions. Report. Do not proceed to Phase 8. |
| Question record cannot be read during Phase 8 | Stop. Report `question_id`. Report split: updated vs. not-yet-updated question IDs. |
| Question record update write fails during Phase 8 | Stop. Append RECOVERY NOTE to all successfully updated records. Report. |
| BLOCKING traceability violation (Phase 9) | Report violation. Do not declare successful completion. |
| BLOCKING integrity violation (Phase 9) | Report violation. Do not declare successful completion. |
| Workspace isolation violation | Stop immediately. Report contaminating path. |
| R4a — workspace_id not in registry | Stop. Report workspace drift (BLOCKING). |
| R4b — workspace status is `archived` | Stop. Report workspace archived (BLOCKING). |
| R4b — workspace status is `paused` or `completed` | Warn. Continue with caution. Document discrepancy. |
| R4e — multiple active workspaces in registry | Warn. Use `runtime/current_workspace.md` as authority. Continue. |

### Recovery Note Format

Append to affected question records in `questions_report.md` when consolidation_report.md or a question update write fails:

```markdown
**RECOVERY NOTE:** /consolidate-knowledge write failed during execution. This question's RESOLVED transition is incomplete. Manual resolution required before specification generation.
```

### Partial Failure Protocol

If transformation fails for one Source Group but succeeds for others:

1. Continue processing the remaining Source Groups.
2. Update consolidation_report.md for successfully processed conflicts only (including CONSOLIDATION_FAILED entries for failed conflicts).
3. Transition question statuses to RESOLVED for successfully consolidated conflicts only.
4. Report the failed Source Group, affected conflict IDs, and failure reason.
5. Declare completion state CONSOLIDATION PARTIAL.

---

## Phase 11 — Completion States

### Three Completion States

#### CONSOLIDATION COMPLETE

All conditions met:

- Eligible Conflict Set is non-empty.
- Every conflict in the Processing Set was successfully transformed and recorded as CONSOLIDATED.
- consolidation_report.md updated with CONSOLIDATED status for all processed conflicts.
- All associated VALIDATED or eligible-SUPERSEDED questions transitioned to RESOLVED.
- All Phase 9 traceability and integrity checks pass.

Also reported when the Processing Set is empty because all eligible conflicts were already consolidated on a prior run (re-run with no new work — idempotent success).

```text
STATUS: CONSOLIDATION COMPLETE
Conflicts consolidated this run: <N>
Conflicts already consolidated (skipped): <M>
Questions resolved this run: <P>
Consolidated artifacts: <list of paths>
```

#### CONSOLIDATION PARTIAL

At least one conflict was successfully consolidated AND at least one conflict in the Eligible Conflict Set failed transformation or could not be written.

```text
STATUS: CONSOLIDATION PARTIAL
Conflicts consolidated this run: <N>
Conflicts failed: <M>
  <conflict_id>: <failure reason>
Questions resolved this run: <P>
Consolidated artifacts: <list of paths>
Ineligible conflicts: <list with reasons>
```

#### CONSOLIDATION BLOCKED

No conflicts could be consolidated:

- Eligible Conflict Set is empty (no conflicts with all questions at VALIDATED or eligible-SUPERSEDED status), OR
- Processing Set is non-empty but all transformation attempts failed.

```text
STATUS: CONSOLIDATION BLOCKED
Reason: <primary blocking reason>
Ineligible conflicts:
  <conflict_id>: <reason>
```

---

## Phase 12 — Post-Execution Validation

### Objective

Run all CK rules against the written artifacts. Confirm all traceability, integrity, and format requirements are satisfied.

### Rules

| Rule | Check |
| ---- | ----- |
| CK1 | Every question with status RESOLVED has `**Resolved By:**`, `**Resolution Date:**`, and `**Consolidated Artifact:**` fields with non-empty values. For questions whose conflict is CONTRADICTION: `**Consolidated Artifact (Secondary):**` is also present with a non-empty value. |
| CK2 | Every conflict with status CONSOLIDATED in consolidation_report.md has a corresponding consolidated artifact at the declared path that exists and is readable. For CONTRADICTION conflicts: both the primary `**Consolidated Artifact:**` and the secondary `**Consolidated Artifact (Secondary):**` paths exist and are readable. |
| CK3 | `WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md` is unmodified from its pre-execution state. |
| CK4 | Every consolidated artifact contains a `## Resolved Conflicts` section with at least one row. |
| CK5 | Every question with status RESOLVED maps to a conflict with status CONSOLIDATED in consolidation_report.md (via `conflict_id`). |
| CK6 | Every conflict with status CONSOLIDATED in consolidation_report.md maps to at least one question with status RESOLVED in questions_report.md (via the `Question ID` field). |
| CK7 | Source extracted knowledge artifacts (`*_knowledge.md` files in `knowledge_base/extracted/`) are unchanged — no modifications occurred during execution. |
| CK8 | All conflicts in the Skip Set have unchanged entries in consolidation_report.md and unchanged consolidated artifact files. |
| CK9 | The declared completion state (COMPLETE / PARTIAL / BLOCKED) matches the actual counts: consolidated, failed, and ineligible. |
| CK10 | No artifact was written outside `WORKSPACE_ROOT` (workspace isolation). |
| CK11 | Every consolidated artifact filename follows the `<base>_consolidated.md` naming convention derived from the corresponding `<base>_knowledge.md` source artifact. |
| CK12 | The consolidation_report.md `Last Updated` date matches the ISO 8601 date of this execution. |
| CK13 | For every CONTRADICTION conflict with status CONSOLIDATED in consolidation_report.md: the `**Consolidated Artifact (Secondary):**` field is present, non-empty, and the file at that path exists and is readable. |
| CK14 | For every CONTRADICTION conflict with status CONSOLIDATED in consolidation_report.md: the secondary consolidated artifact file contains a `## Resolved Conflicts` section with a row for this `conflict_id`. |

### Verification Procedure

Check CK1–CK14 against the written artifacts after Phase 9 completes.

For each failed rule:
- Report the rule ID, the affected artifact path, and the specific violation.
- Classify: BLOCKING (prevents correct downstream consumption) or WARNING (traceability gap, does not block but must be documented).

Any BLOCKING CK failure requires resolution before the completion state CONSOLIDATION COMPLETE may be declared.

**STATUS: POST-EXECUTION VALIDATION COMPLETE**

---

## Expected Outputs

```text
WORKSPACE_ROOT/knowledge_base/consolidated/<base>_consolidated.md    ← new consolidated artifact per source
WORKSPACE_ROOT/knowledge_base/consolidated/consolidation_report.md  ← updated consolidation authority record
WORKSPACE_ROOT/knowledge_base/questions/questions_report.md         ← updated in-place (RESOLVED status + resolution blocks)
```

No other repository areas are modified by this command.

`WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md` is read as input and must not be modified.

---

## Out of Scope — Milestone 6

### Conflict Re-processing

Once a conflict is marked CONSOLIDATED in consolidation_report.md, it is immutable for the current version. Re-processing a consolidated conflict after source artifact changes is deferred to a future milestone.

### RESOLVED Re-entry

RESOLVED is a terminal status. Transitioning a RESOLVED question back to any earlier lifecycle state is deferred to a future milestone. This specification must not accept or apply a re-entry transition.

### Specification Generation

Specification generation consumes consolidated knowledge artifacts but is not part of this command. `/consolidate-knowledge` produces consolidated artifacts; it does not invoke or trigger the specification generation pipeline.

### Language Translation

This command performs no language translation. Translation of human validation responses is the exclusive responsibility of the `/human-validation` stage per ADR-001. If a canonical question record is found to contain non-English content, execution stops with an ADR-001 compliance failure. This command does not attempt to correct upstream compliance gaps.
