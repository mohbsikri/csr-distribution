# Specification Generation Execution Specification

## Purpose

Define the runtime execution procedure for the `/generate-specification` command.

The objective is to consume consolidated knowledge artifacts from the canonical consolidated knowledge store, apply a deterministic structural transformation to produce draft specification artifacts, record generation metadata in the specification generation log, and report completion state.

This specification implements Step 7 — Specification Generation of the CSR pipeline.

---

## Execution Flow

```text
Workspace Resolution
↓
Artifact Discovery
↓
Eligibility Verification
↓
Source Loading
↓
Specification Model Resolution
↓
Specification Transformation
↓
Specification Writing
↓
Generation Log Update
↓
Traceability Matrix Generation
↓
SQF Q-GATE-1 (D1 + D3)     ← Phase 8.7 [SQF Phase 1]
↓
Post-Execution Validation (SG1–SG20)
↓
Completion Reporting
```

---

## Runtime Version Reference

The runtime version is referenced throughout this specification as `CURRENT_RUNTIME_VERSION`.

At execution time, `CURRENT_RUNTIME_VERSION` must be read from:

```text
docs/implementation_status.md
```

Locate the section `## Current Version` and extract the version value.

This value must never be hardcoded.

---

## Preconditions

Before execution begins, verify:

| ID | Precondition | Action on Failure |
| -- | ------------ | ----------------- |
| P1 | `docs/commands/generate-specification.md` exists and is readable | Stop. Report missing contract. |
| P2 | Workspace runtime resolves (R1–R6 pass in Phase 1) | Stop. Report workspace failure. |
| P3 | `WORKSPACE_ROOT/knowledge_base/consolidated/` contains at least one `*_consolidated.md` file, OR `WORKSPACE_ROOT/knowledge_base/extracted/` contains at least one `*_knowledge.md` file | Stop. Report no source artifacts found. |
| P4 | `WORKSPACE_ROOT/knowledge_base/consolidated/consolidation_report.md` exists and is readable (required when P3 is satisfied via consolidated path) | Stop. Report missing consolidation authority record. |
| P5 | `WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md` exists and is readable | WARNING only — ADVISORY unresolved conflict flags cannot be inserted if absent. Proceed without ADVISORY flags. |
| P6 | `WORKSPACE_ROOT/specifications/draft/` directory exists | Stop. Report missing output directory. Enforced at R7 in Phase 1. |
| P7 | At least one eligible source group exists after Phase 3 eligibility verification | Stop. Report no eligible source groups with reasons. |

If any precondition fails, report the failure explicitly and stop. Do not proceed to execution.

---

## Phase 0 — V2 Context Detection

### Objective

Determine whether specification generation is running inside a V2 workspace. V2 mode triggers a different assembly path: merge of inherited v1 BASELINED spec + v2 knowledge delta → V2 spec with Section Δ.

This phase runs once, before workspace resolution, using the global repository root.

### Step 0.1 — Detect lineage file

After resolving WORKSPACE_ROOT (from Phase 1 R1–R2), check:

```text
WORKSPACE_ROOT/runtime/lineage.md
```

If **found**: set `spec_mode = V2`. Read `source_workspace_id` from lineage. Proceed to Step 0.2.
If **not found**: set `spec_mode = V1`. Skip to Phase 1 normal execution.

> Note: Phase 0 reads WORKSPACE_ROOT which is established in Phase 1. In practice, run Phase 1 R1–R2 first to build WORKSPACE_ROOT, then execute Phase 0 before Phase 2.

### Step 0.2 — Load inherited v1 BASELINED spec (V2 mode only)

Locate the inherited BASELINED spec in:

```text
WORKSPACE_ROOT/specifications/stable/
```

Find any file matching `*_specification.md` in that directory. Exactly one file is expected (the v1 spec inherited via V2 FORK).

- If zero files found: halt with:
  ```
  V2 SPEC ERROR — No inherited BASELINED spec found at WORKSPACE_ROOT/specifications/stable/.
  The V2 FORK must copy the v1 BASELINED spec before /generate-specification is run.
  ```
- If more than one file found: halt with:
  ```
  V2 SPEC ERROR — Multiple files in WORKSPACE_ROOT/specifications/stable/. Ambiguous inherited spec.
  Expected exactly one *_specification.md file.
  ```

Record:
- `inherited_spec_path` = path to the found spec file
- `inherited_base` = filename minus `_specification.md` suffix

### Step 0.3 — Parse v1 rule map

Read the inherited spec. Parse all rule entries per section:

- `## 5. Constraints` → `C-NNN` entries
- `## 6. Business Rules` → `BR-NNN` entries
- `## 7. Technical Rules` → `TR-NNN` entries

Build `v1_rule_map`:

```text
v1_rule_map = {
  "BR-001": { section: "Business Rules", text: "<full rule text>", annotation: null },
  "TR-001": { section: "Technical Rules", text: "<full rule text>", annotation: null },
  "C-001": { section: "Constraints", text: "<full rule text>", annotation: null },
  ...
}
```

Also record:
- `v1_sections` = map of all other sections (Terms and Definitions, Context and Background, Design Decisions, Assumptions) with their verbatim v1 content

These will form the inherited base in Phase 6b.

### Output

```text
spec_mode = V1 | V2
[V2 only] inherited_spec_path
[V2 only] inherited_base
[V2 only] v1_rule_map (keyed by rule ID)
[V2 only] v1_sections (keyed by section name)
```

---

## Phase 1 — Workspace Resolution

### Objective

Establish the active workspace root path, validate workspace integrity, and verify the output directory exists before any artifact operation.

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

### R7 — Output Directory Verification

Verify that the output directory exists:

```text
WORKSPACE_ROOT/specifications/draft/
```

If the directory does not exist:

```text
STATUS: BLOCKED — Precondition P4 Failure: WORKSPACE_ROOT/specifications/draft/ directory not found. Create this directory before running /generate-specification.
```

Stop execution.

**STATUS: WORKSPACE RESOLVED**

---

## Phase 1.5 — Template Mode Detection

### Objective

Detect whether the active workspace is configured for STD v1 template generation or legacy template generation. Set `template_mode`. This governs Phase 6 routing for all candidates in this execution.

### Step 1.5.1 — Read spec_template_version

From `runtime/workspaces.md`, locate the row matching `workspace_id` (already loaded in Phase 1).

Extract the `spec_template_version` column value:

| Value | `template_mode` | Note |
|---|---|---|
| `v1` | `STD` | STD canonical v1 generation |
| `legacy` | `LEGACY` | Legacy 7-section generation (unchanged) |
| absent / empty | `LEGACY` | Issue WARNING: `spec_template_version non défini pour workspace <workspace_id>; routage LEGACY par défaut.` |

**Who writes this value `[issue #55, 2026-11-09]`.** `/workspace-lifecycle` writes it explicitly on every row it creates: CREATE writes `v1`, V2 FORK writes `legacy` (canonical schema: `docs/commands/workspace-lifecycle_execution.md` Step 1.8). The absent / empty row of the table above therefore only concerns workspaces registered before that rule; it is kept unchanged as their documented fallback — those rows are never migrated, and this step never writes to the registry.

### Step 1.5.2 — V2 Override

When `spec_mode = V2` (set in Phase 0): V2 mode always uses LEGACY template assembly. Regardless of `spec_template_version`:

```text
template_mode = LEGACY
```

Log: `V2 mode detected — template_mode forced to LEGACY. STD v1 template not supported in V2 mode.`

### Step 1.5.3 — Report

```text
Template mode: <template_mode> (workspace spec_template_version: <value>)
```

**STATUS: TEMPLATE MODE DETECTED**

---

## Phase 2 — Artifact Discovery

### Objective

Identify all source artifacts that are candidates for specification generation. Build the Candidate Source Set.

### Path Representation Convention

All internal path representations within Phase 2 data structures (Consolidated Candidate Set, Consolidation Index, Zero-Conflict Candidate Set, Conflicts Index) use **workspace-relative format**: paths relative to `WORKSPACE_ROOT` (e.g., `knowledge_base/consolidated/test_consolidated.md`).

Paths obtained from directory scans are WORKSPACE_ROOT-prefixed. Strip the `WORKSPACE_ROOT` prefix before storing any path in an internal data structure. All cross-references between data structures — Phase 3 Consolidation Index lookups, Phase 6 Conflicts Index lookups — must use workspace-relative paths consistently to prevent silent key mismatches.

### Step 2.1 — Consolidated Path Scan

Scan the directory:

```text
WORKSPACE_ROOT/knowledge_base/consolidated/
```

Collect all files matching the pattern `*_consolidated.md`.

For each file found: extract `<base>` by stripping the `_consolidated.md` suffix from the filename.

Build the **Consolidated Candidate Set**: a mapping of `<base>` → consolidated artifact path.

If the directory does not exist: record zero consolidated candidates (not a stop condition on its own — the zero-conflict fallback path may provide candidates).

### Step 2.2 — Consolidation Report Load

If the Consolidated Candidate Set is non-empty:

Read:

```text
WORKSPACE_ROOT/knowledge_base/consolidated/consolidation_report.md
```

This file is a **READ-ONLY** input. It must not be modified at any point during execution.

Parse the `## Conflict Resolution Records` section. For each `### C<NNN>` block, extract:

| Field | Location in record |
| ----- | ------------------ |
| `conflict_id` | `**Conflict ID:**` field |
| `conflict_type` | `**Type:**` field |
| `severity` | `**Severity:**` field |
| `status` | `**Status:**` field |
| `consolidated_artifact` | `**Consolidated Artifact:**` field |
| `consolidated_artifact_secondary` | `**Consolidated Artifact (Secondary):**` field — present only for CONTRADICTION records; null if absent |

Apply status normalization: treat all status values as case-insensitive. Normalize to UPPERCASE internally.

**PARTIAL RECORD DETECTED check:** For any record where `status == CONSOLIDATED` and `conflict_type == CONTRADICTION`:

If `consolidated_artifact_secondary` is null or empty:

```text
STATUS: BLOCKED — PARTIAL RECORD DETECTED: CONTRADICTION conflict <conflict_id> has status CONSOLIDATED in consolidation_report.md but is missing **Consolidated Artifact (Secondary):**. Manual resolution required. Do not classify as SKIP.
```

Stop execution.

Build the **Consolidation Index**: a mapping from consolidated artifact path → list of `{ conflict_id, conflict_type, severity, status }` records.

For CONTRADICTION records: register the conflict record under **both** `consolidated_artifact` (Item A path) **and** `consolidated_artifact_secondary` (Item B path). Both paths map to the same conflict record.

For AMBIGUITY and GAP records: register under `consolidated_artifact` only.

Also derive the **Consolidated Conflict Set**: the flat set of all `conflict_id` values where `status == CONSOLIDATED` across all Consolidation Index entries, regardless of which consolidated artifact path they appear under. This flat set enables O(1) conflict resolution status lookup in Phase 6 Step 6.4 without requiring a path-keyed lookup.

Then parse the `## Ineligible Conflicts` section of the same file, if present. It is a two-column table:

```markdown
| Conflict ID | Reason |
| ----------- | ------ |
| C006 | Question Q006 has status PARTIALLY_ANSWERED — VALIDATED or eligible-SUPERSEDED required. |
```

Build the **Ineligible Conflict Set**: a mapping from `conflict_id` → `reason`. If the section is absent or has no data rows, the set is empty.

> **Why this section must be read.** `/consolidate-knowledge` records a conflict it declined to process here, and **only** here — it produces no `### C<NNN>` resolution record for it. A conflict parked in this table is therefore absent from the Consolidation Index entirely, including a conflict of `severity: BLOCKING`. Before this section was parsed, the Step 3.1 eligibility check could not see such a conflict at all: it inspected only records the Consolidation Index contained, so the one category of conflict it most needed to catch was the one category structurally invisible to it. Conflict C006 of workspace `demo-inventory-01` reached a BASELINED specification through this gap on 2026-10-30. See finding F-01 of (internal review note).
>
> The Ineligible Conflict Set carries no severity of its own — the table has no severity column. Severity comes from the Conflicts Index built in Step 2.6, which is the authority for it. This set supplies the *reason* text, so that an eligibility failure can tell the operator why consolidation declined the conflict rather than merely that it did.

If `consolidation_report.md` does not exist when the Consolidated Candidate Set is non-empty:

```text
STATUS: BLOCKED — Missing Consolidation Authority Record: consolidation_report.md not found. Cannot verify BLOCKING conflict eligibility.
```

Stop execution.

### Step 2.3 — Zero-Conflict Fallback Scan

Scan the directory:

```text
WORKSPACE_ROOT/knowledge_base/extracted/
```

Collect all files matching the pattern `*_knowledge.md`.

For each file found: extract `<base>` by stripping the `_knowledge.md` suffix.

Cross-reference against the Consolidated Candidate Set (Step 2.1): a `<base>` that already has a consolidated artifact is **excluded** from the zero-conflict fallback path. The consolidated artifact takes precedence.

Build the **Zero-Conflict Candidate Set**: the set of `<base>` values present in the extracted scan but absent from the Consolidated Candidate Set. Source type for these candidates: EXTRACTED.

### Step 2.4 — Build Candidate Source Set

Merge the two candidate sets:

```text
Candidate Source Set = Consolidated Candidate Set (type: CONSOLIDATED)
                     ∪ Zero-Conflict Candidate Set (type: EXTRACTED)
```

No `<base>` value appears in both sets (Step 2.3 guarantees exclusion).

If the Candidate Source Set is empty after merging:

```text
STATUS: BLOCKED — No source artifacts found: no *_consolidated.md files in knowledge_base/consolidated/ and no *_knowledge.md files in knowledge_base/extracted/
```

Stop execution.

### Step 2.5 — Generation Log Consultation (Optimization)

Read `WORKSPACE_ROOT/specifications/draft/specifications_report.md` if it exists.

Build the **Already-Generated Set**: the set of `<base>` values with status GENERATED in the report.

This set is used as a performance optimization only. A candidate in the Already-Generated Set is **not excluded** from the Processing Set — re-generation from an unchanged source produces identical output and is semantically safe. The decision to skip or re-generate is an optimization choice, not a correctness constraint.

If `specifications_report.md` does not exist: the Already-Generated Set is empty. This is the first generation run.

### Step 2.6 — Conflicts Report Load (ADVISORY Flag Identification)

Read:

```text
WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md
```

This file is a **READ-ONLY** input. It must not be modified at any point during execution.

Parse all conflict records. For each conflict record, first extract the common fields:

| Internal field | Location in record |
| -------------- | ------------------ |
| `conflict_id` | `**Conflict ID:**` field |
| `conflict_type` | `**Type:**` field |
| `severity` | `**Severity:**` field |

Then apply type-dispatched extraction to obtain `source_base` and `section`:

**AMBIGUITY:**
- `section` = value of `Section:` field within the `**Affected Item:**` block
- `source_base` = `<base>` extracted from the `Source:` field in the `**Affected Item:**` block (strip `knowledge_base/extracted/` prefix and `_knowledge.md` suffix)
- Produces 1 Conflicts Index entry under `source_base`

**GAP:**
- `section` = annotation after ` — ` in the `**Absent from:**` field (the part after the path separator; empty string if no ` — ` separator is present)
- `source_base` = `<base>` extracted from the path component of the `**Absent from:**` field (strip `knowledge_base/extracted/` prefix and `_knowledge.md` suffix)
- Produces 1 Conflicts Index entry under `source_base`

**CONTRADICTION:**
- Item A: `section_a` = `Item A Section:` value from the `**Affected Items:**` block; `source_base_a` = `<base>` extracted from `Item A Source:` (strip `knowledge_base/extracted/` prefix and `_knowledge.md` suffix)
- Item B: `section_b` = `Item B Section:` value from the `**Affected Items:**` block; `source_base_b` = `<base>` extracted from `Item B Source:` (strip `knowledge_base/extracted/` prefix and `_knowledge.md` suffix)
- Produces 2 Conflicts Index entries: one under `source_base_a` with `section_a`; one under `source_base_b` with `section_b`

Build the **Conflicts Index**: a mapping from `<base>` → list of `{ conflict_id, conflict_type, severity, section }` records.

Include all conflicts regardless of severity. Phase 6 Step 6.4 filters to ADVISORY severity.

If `conflicts_report.md` does not exist:

```text
STATUS: WARNING — WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md not found. ADVISORY unresolved conflict flags cannot be inserted in this execution. Proceeding without ADVISORY flag generation.
```

Set the Conflicts Index to empty. Continue execution. Do not stop.

**STATUS: ARTIFACT DISCOVERY COMPLETE**

---

## Phase 3 — Eligibility Verification

### Objective

Determine which candidates in the Candidate Source Set are eligible for specification generation. Build the Processing Set.

### Step 3.1 — BLOCKING Conflict Check (all candidates)

No specification may be generated from a source group that still carries an unresolved BLOCKING conflict. This step enforces that through two sub-checks with different authorities. Both run; neither replaces the other.

| Sub-check | Authority | Applies to | Catches |
| --------- | --------- | ---------- | ------- |
| 3.1a | Consolidation Index (`consolidation_report.md`, `## Conflict Resolution Records`) | CONSOLIDATED candidates | A conflict the consolidation report registered but did not resolve, and a consolidated artifact the report never registered at all |
| 3.1b | Conflicts Index (`conflicts_report.md`, Step 2.6) | **All** candidates | A BLOCKING conflict the consolidation report never resolved, wherever it was parked — including one it declined to process, and one belonging to a base that has no consolidated artifact |

#### Step 3.1a — Consolidation Record Check (CONSOLIDATED candidates only)

For each candidate with source type CONSOLIDATED:

Using the Consolidation Index from Step 2.2: retrieve all conflict records associated with this candidate's consolidated artifact path.

**CONTRADICTION dual-path note:** For CONTRADICTION conflicts, the Consolidation Index registers the conflict record under both the Item A path and the Item B path. A candidate whose consolidated artifact appears as either the primary or secondary path of a CONTRADICTION conflict will therefore find that conflict in its lookup. Each source group in a CONTRADICTION pair independently satisfies the BLOCKING eligibility check.

If any conflict record has `severity: BLOCKING` and `status ≠ CONSOLIDATED`:

Mark this candidate as **INELIGIBLE**.

Record:

```text
INELIGIBLE — <base>_consolidated.md: unresolved BLOCKING conflict(s): <comma-separated conflict_id list>. All BLOCKING conflicts must be CONSOLIDATED before specification generation can proceed.
```

If the Consolidation Index contains no records for this consolidated artifact path (consolidated artifact exists but was not registered in consolidation_report.md):

Mark this candidate as **INELIGIBLE**.

Record:

```text
INELIGIBLE — <base>_consolidated.md: no consolidation records found in consolidation_report.md. Consolidated artifact may have been created outside the pipeline.
```

#### Step 3.1b — Conflicts Report Authority Check (all candidates)

This sub-check applies to **every** candidate in the Candidate Source Set, CONSOLIDATED and EXTRACTED alike.

For each candidate, retrieve the Conflicts Index entries recorded under this candidate's `<base>` (Step 2.6). The Conflicts Index is keyed by base, carries `severity` for every conflict regardless of what consolidation did with it, and registers a CONTRADICTION under both of its source bases — so a candidate sees every conflict that concerns it.

Build `unresolved_blocking` for this candidate:

```text
unresolved_blocking = [
  entry.conflict_id
  for entry in ConflictsIndex[<base>]
  if entry.severity == BLOCKING and entry.conflict_id not in ConsolidatedConflictSet
]
```

If `unresolved_blocking` is non-empty:

Mark this candidate as **INELIGIBLE**.

For each listed conflict, look up its `reason` in the Ineligible Conflict Set (Step 2.2). Record:

```text
INELIGIBLE — <base>: unresolved BLOCKING conflict(s) per conflicts_report.md: <comma-separated conflict_id list>.
  <conflict_id>: <reason from the Ineligible Conflict Set, or "not registered in consolidation_report.md">
All BLOCKING conflicts affecting a source group must be CONSOLIDATED before a specification can be generated from it.
```

**Why the Consolidated Conflict Set is the right comparator.** It is the flat set of every `conflict_id` that reached `status: CONSOLIDATED`, independent of which artifact path the record sits under. A BLOCKING conflict is therefore cleared only by an actual resolution record — never by the absence of evidence, and never by the section of `consolidation_report.md` it happens to be filed in.

**If `conflicts_report.md` does not exist:** Step 2.6 has already emitted its WARNING and set the Conflicts Index empty. In that state this sub-check cannot be performed. Record it as skipped rather than passed, and carry the fact into the completion report of Phase 10:

```text
WARNING — Step 3.1b skipped: conflicts_report.md not found. BLOCKING conflict verification for this execution rests on consolidation_report.md alone (Step 3.1a), which covers CONSOLIDATED candidates only. EXTRACTED candidates were not verified.
```

Do not stop execution. A workspace that never ran `/detect-conflicts` has no conflicts report and is a legitimate state; what is not legitimate is reporting an unverified candidate as verified.

#### EXTRACTED candidates

An EXTRACTED candidate is **not** exempt from Step 3.1b, and the Zero-Conflict Fallback path (Step 2.3) must not be read as proof that a base has no conflicts.

A base is routed to EXTRACTED when it has no `*_consolidated.md` artifact. The usual reason is that `/detect-conflicts` found nothing for it. But a base whose conflicts were *all declined by consolidation* also has no consolidated artifact, and lands on the identical path. The two are indistinguishable at Step 2.3, and only `conflicts_report.md` can tell them apart.

> **Correction recorded 2026-10-30.** This step previously marked every EXTRACTED candidate ELIGIBLE unconditionally, justified by the inference "zero-conflict sources produced no conflict records, therefore they have no BLOCKING conflicts". The premise does not hold: in workspace `demo-inventory-01`, base `demo-inventory-mockup_transcript` was processed as a zero-conflict EXTRACTED candidate while carrying conflicts C008, C009 and C010. Those three were ADVISORY, so no harm followed — but nothing in the rule made that outcome anything other than luck. Had any been BLOCKING, the candidate would have been generated and baselined with the eligibility check reporting success. This was found while implementing recommendation R1 of the run review, not by the review itself.

Therefore, for each candidate with source type EXTRACTED: do not mark ELIGIBLE by inference. Apply Step 3.1b. A candidate with no Conflicts Index entries produces an empty `unresolved_blocking` and passes on evidence rather than on assumption; "no entry found in the Consolidation Index" remains the expected state for a genuinely zero-conflict source and is still **not** an eligibility failure.

### Step 3.2 — Mappable Content Check

For each candidate not yet marked INELIGIBLE:

Inspect the source artifact to determine whether it contains at least one section from the canonical mapping set:

```text
Terminology | Facts | Decisions | Assumptions | Constraints | Business Rules | Technical Rules
```

Section identification is case-insensitive.

If none of these sections are present: mark this candidate as **INELIGIBLE**.

Record:

```text
INELIGIBLE — <base>_<type>.md: no mappable knowledge sections found. The artifact contains no content that can be transformed into a specification section.
```

### Step 3.3 — Build Processing Set

After Steps 3.1 and 3.2: the Processing Set contains all candidates not marked INELIGIBLE.

If the Processing Set is empty:

```text
STATUS: SPECIFICATION BLOCKED — All candidates are ineligible.
```

Report each candidate's ineligibility reason. Stop execution.

If the Processing Set is non-empty but some candidates were excluded: continue with the Processing Set. SPECIFICATION PARTIAL will be declared at completion.

**STATUS: ELIGIBILITY VERIFICATION COMPLETE — <N> candidates eligible, <M> ineligible**

---

## Phase 4 — Source Loading

### Objective

Load the source artifact for each candidate in the Processing Set. Build the Source Data Model for each candidate.

Process candidates one at a time. A loading failure for one candidate does not stop processing of remaining candidates.

### Step 4.1 — Load Consolidated Artifact (CONSOLIDATED candidates)

Read the consolidated artifact at:

```text
WORKSPACE_ROOT/knowledge_base/consolidated/<base>_consolidated.md
```

This file is a READ-ONLY input. It must not be modified.

**Parse header block fields:**

Locate the header block at the start of the file (before the first `---` separator). Extract:

| Internal field | Source field name | Required |
| -------------- | ----------------- | -------- |
| `origin_extracted_path` | `**Source Artifact:**` | Yes — STOP for this candidate if missing |
| `consolidated_date` | `**Consolidated Date:**` | Yes — STOP for this candidate if missing |
| `conflicts_resolved_raw` | `**Conflicts Resolved:**` | Yes — STOP for this candidate if missing |

After extracting the above fields, set:

```text
source_artifact_path = "knowledge_base/consolidated/<base>_consolidated.md"
```

Where `<base>` is the base name derived during Phase 2 discovery. This is the workspace-relative path to the consolidated artifact being loaded in this step — it is not read from the artifact's internal header. The internal `**Source Artifact:**` field of the consolidated artifact (`origin_extracted_path`) holds the path to the extracted knowledge artifact from which the consolidated artifact was derived; it is retained for SG7 verification only and must not be used as `source_artifact_path`.

Parse `conflicts_resolved_raw` as a comma-separated list of `conflict_id` values. Trim whitespace from each value.

**Parse `## Resolved Conflicts` table:**

Locate the `## Resolved Conflicts` section. Parse each table row:

| Internal field | Table column |
| -------------- | ------------ |
| `conflict_id` | Conflict ID |
| `conflict_type` | Type |
| `conflict_severity` | Severity |
| `question_id` | Question ID |
| `resolution_summary` | Resolution Summary |

If the `## Resolved Conflicts` section is absent: record an empty resolved conflicts list.

**Parse knowledge sections:**

Scan for all Markdown headings (`#` or `##`) in the artifact. For each heading:

- Apply the canonical section identification rules defined in Phase 5.
- Extract the full content block beneath each identified section (up to the next heading of equal or higher level, or end of document).
- Exclude the following sections from content extraction: `# Source` (traceability use only), `## Resolved Conflicts` (consumed separately above).

If a parsing failure prevents reading required header fields: mark this candidate as a **per-candidate failure**. Record the failure reason. Continue with remaining candidates.

### Step 4.2 — Load Extracted Artifact (EXTRACTED candidates)

Read the extracted artifact at:

```text
WORKSPACE_ROOT/knowledge_base/extracted/<base>_knowledge.md
```

This file is a READ-ONLY input. It must not be modified.

Set internal fields:

```text
source_artifact_path = "knowledge_base/extracted/<base>_knowledge.md"
consolidated_date = null
conflicts_resolved_raw = "none"
resolved_conflicts_table = []
```

**Parse knowledge sections:**

Apply the same section scanning procedure as Step 4.1. Exclude the `# Source` section from content extraction (use for traceability reference only).

### Step 4.2a — V2 Delta Extraction (V2 mode only)

When `spec_mode = V2`:

After parsing knowledge sections, scan all BR-NNN, TR-NNN, and C-NNN entries for v2 annotation tags.

Build the **v2 delta**:

```text
v2_delta = {
  added:      [ { id, section, text } ],   ← rules with `[v2-added]` tag
  modified:   [ { id, section, text } ],   ← rules with `[v2-modified]` tag
  deprecated: [ { id } ]                   ← rules with `[DEPRECATED in v2]` tag
}
```

**Tag detection rules:**

- `[v2-added]`: rule text contains the literal string `[v2-added]` (inserted by `/extract-knowledge` in V2 mode)
- `[v2-modified]`: rule text contains `[v2-modified]` — this rule replaces or modifies a v1 rule with the same ID
- `[DEPRECATED in v2]`: rule text contains `[DEPRECATED in v2]` — the corresponding v1 rule ID is being retired

For `[v2-modified]` rules: verify that the rule ID exists in `v1_rule_map` (from Phase 0). If not found in v1_rule_map: treat as `[v2-added]` and log a WARNING.

For `[DEPRECATED in v2]` rules: verify that the rule ID exists in `v1_rule_map`. If not found: log a WARNING. Ignore the deprecation entry.

If no v2 annotation tags are found in any extracted rule: log a WARNING and continue. The V2 spec will contain only v1-inherited content plus the un-annotated new rules (treated as v2-added implicitly).

### Step 4.2b — Parse Provenance Index (KPM — ALL candidates)

For every candidate after Steps 4.1/4.2 loading:

**Locate the knowledge artifact:**

- For EXTRACTED candidates: the knowledge artifact is the source artifact already loaded in Step 4.2. Use `source_artifact_path`.
- For CONSOLIDATED candidates: the knowledge artifact is at `WORKSPACE_ROOT/<origin_extracted_path>` (the `**Source Artifact:**` field extracted in Step 4.1). Read this file. If it cannot be read or does not exist: set `kpm_status = NO_PROVENANCE_INDEX`, set `provenance_map = {}`, log a WARNING, and proceed (T-MODE active for this candidate).

**Scan for `## Provenance Index` section:**

After reading the knowledge artifact, locate a section heading that matches `## Provenance Index` (case-insensitive). If found: parse the table rows beneath it (up to the next heading or end of file).

If the section is absent, or the table contains zero data rows: set `kpm_status = NO_PROVENANCE_INDEX`, `provenance_map = {}`.

**Parse each table row:**

Table columns: `| ID | Type | Refs | Rationale | Impact | Statut |`

For each row:
```text
provenance_map[ID] = {
  type:              SF | UV | DK | TS | ID | US
  refs:              <string | null>
  rationale:         <string | null>
  impact_level:      structural | implementation | null   (present only when type = ID)
  governance_status: PENDING_VALIDATION | REGISTERED | ACKNOWLEDGED | BLOCKED | null
}
```

Normalize cell values: trim whitespace; treat `—` as null.

If parsing succeeds and at least one row was parsed: set `kpm_status = PROVENANCE_INDEXED`.

**T-MODE activation:** `kpm_status = NO_PROVENANCE_INDEX` is T-MODE. In T-MODE:
- The Inference Registry is generated with all 4 subsections containing `*(aucun élément)*`.
- The Provenance column in the traceability matrix contains `—` for all rows.
- No WARNING is required unless the knowledge artifact itself could not be read.

This step is non-blocking. A failure to parse the Provenance Index activates T-MODE; it does not stop specification generation.

### Step 4.3 — ADR-001 Language Compliance Check

For each successfully loaded candidate:

Scan the extracted section content (all text extracted in Steps 4.1 or 4.2) for non-English content.

This command performs no translation. All canonical artifacts consumed by this command must contain English content, as required by ADR-001 (CSR Language Policy) and guaranteed by the upstream pipeline.

If non-English content is detected:

```text
STATUS: BLOCKED — ADR-001 Compliance Failure: non-English content detected in <artifact_path>. Upstream stage correction required before specification generation can proceed for this source.
```

Mark this candidate as a **per-candidate failure**. Record the failure. Continue with remaining candidates.

If ALL candidates fail ADR-001: declare SPECIFICATION BLOCKED at completion.

### Step 4.4 — Build Source Data Model

For each candidate that passed Steps 4.1–4.3, construct the Source Data Model:

```text
SourceDataModel {
  base:                    <base name>
  source_type:             CONSOLIDATED | EXTRACTED
  source_artifact_path:    <path to consolidated or extracted artifact>
  origin_extracted_path:   <path to extracted artifact — CONSOLIDATED only; null for EXTRACTED>
  display_name:            <derived — see Step 4.6>
  consolidated_date:       <date string | null>
  conflicts_resolved:      [<conflict_id>, ...]  (empty list if EXTRACTED)
  resolved_conflicts:      [{ conflict_id, conflict_type, severity, question_id, resolution_summary }, ...]
  questions_incorporated:  [<question_id>, ...]  (derived from resolved_conflicts)
  conflict_section_map:    { conflict_id: specification_section_name }  (derived — see Step 4.5; empty for EXTRACTED)
  kpm_status:              PROVENANCE_INDEXED | NO_PROVENANCE_INDEX   (set in Step 4.2b)
  provenance_map:          { ID → { type, refs, rationale, impact_level, governance_status } }   (set in Step 4.2b; empty map in T-MODE)
  spec_design_map:         { element_name → { type, rationale, impact_level, governance_status } }   (populated in Step 6.5b; empty map initially)
  sections: {
    Terminology:    <content string | null>
    Facts:          <content string | null>
    Decisions:      <content string | null>
    Assumptions:    <content string | null>
    Constraints:    <content string | null>
    BusinessRules:  <content string | null>
    TechnicalRules: <content string | null>
  }
}
```

Derive `questions_incorporated` by collecting all unique `question_id` values from `resolved_conflicts`.

### Step 4.5 — Build Conflict-Section Map (CONSOLIDATED candidates only)

For each CONSOLIDATED candidate, determine which specification section each resolved conflict affected.

**Method:** Scan the extracted section content for inline resolution note markers.

For each section key in `{ Terminology, Facts, Decisions, Assumptions, Constraints, BusinessRules, TechnicalRules }`:

If `sections.<key>` is non-null:

Scan the section content for inline markers matching the pattern:

```text
> Resolution (<conflict_id>):
```

Case-insensitive match on the word `Resolution`. Exact match on the `conflict_id` value (e.g., `C001`).

For each `conflict_id` found within this section's content:

```text
conflict_section_map[conflict_id] = <specification_section_name>
```

Where `<specification_section_name>` is the canonical specification section name from the Phase 5 mapping table (e.g., if the marker appears in the `BusinessRules` section content, record `"6. Business Rules"`).

A `conflict_id` found in multiple sections: record only the first occurrence (earlier sections have higher canonical order priority).

A `conflict_id` present in `conflicts_resolved` but not found via scanning: record `conflict_section_map[conflict_id] = null`. This means the conflict was consolidated but no inline resolution marker was located — the Provenance table row will omit the Specification Section value for this conflict.

For EXTRACTED candidates: set `conflict_section_map = {}`.

### Step 4.6 — Derive Display Name

The display name is used as the specification document title.

**Rule:** Take the text of the top-level `#` heading from the source artifact. Strip the following known pipeline suffixes (case-insensitive):

- ` — Consolidated Knowledge`
- ` — Source Knowledge`
- ` — Extracted Knowledge`

If no top-level `#` heading exists: use the `<base>` filename as the display name (replacing underscores with spaces, title-cased).

**STATUS: SOURCE LOADING COMPLETE**

---

## Phase 5 — Specification Model Resolution

### Objective

Define the canonical specification structure for each candidate in the Processing Set.

### Section Identification Rules

When scanning source artifact sections, apply the following identification rules. Section matching is case-insensitive and uses substring matching where noted:

| Source heading (case-insensitive) | Maps to | Specification Section |
| --------------------------------- | ------- | --------------------- |
| `Terminology` | Terminology | 1. Terms and Definitions |
| `Facts` | Facts | 2. Context and Background |
| `Decisions` | Decisions | 3. Design Decisions |
| `Assumptions` | Assumptions | 4. Assumptions |
| `Constraints` | Constraints | 5. Constraints |
| `Business Rules` | BusinessRules | 6. Business Rules |
| `Technical Rules` | TechnicalRules | 7. Technical Rules |

**Excluded sections (not mapped to any specification section):**

| Source heading | Reason |
| -------------- | ------ |
| `Source` | Pipeline provenance — used for traceability; not included in specification content |
| `Resolved Conflicts` | Conflict traceability table — consumed separately for Specification Provenance; not reproduced as a specification section |

**Section order:** The canonical specification section order is fixed (1–7 as listed above), regardless of the order sections appear in the source artifact.

**Absent sections:** A section not present in the source artifact is omitted from the specification. No placeholder or empty section is inserted.

**Mandatory minimum:** At least one mappable section must be present (enforced in Phase 3, Step 3.2). If this check was not applied or was bypassed, re-apply it here: if no sections map to a specification section, this candidate is a per-candidate failure.

---

## Phase 6 — Specification Transformation

### Phase 6 Routing — template_mode

Before Step 6.1, apply the following routing based on `template_mode` (set in Phase 1.5):

**When `template_mode = STD`:** Skip Phase 6 Steps 6.1–6.7. Proceed directly to **Phase 6-STD** (below Phase 6.7). All STD candidates use Phase 6-STD.

**When `template_mode = LEGACY`:** Execute Phase 6 Steps 6.1–6.7 as defined below. This is unchanged from pre-STD behavior.

Note: `spec_mode = V2` implies `template_mode = LEGACY` (enforced in Phase 1.5). Phase 6b (V2 assembly) is entered from Phase 6.7 when `spec_mode = V2`.

### Objective

Assemble the complete draft specification document for each candidate in the Processing Set using the Source Data Model from Phase 4.

This phase is a **structural transformation only**. Content is reproduced verbatim from the source artifact. No content is invented, inferred, paraphrased, summarized, or reinterpreted.

Process candidates one at a time.

### Step 6.1 — Assemble Specification Header Block

Construct the header block:

```markdown
**Source Artifact:** <source_artifact_path>
**Source Type:** <CONSOLIDATED | EXTRACTED>
**Generated:** <ISO 8601 date of this execution>
**Generation Command:** /generate-specification
**Conflicts Incorporated:** <comma-separated conflict_id list, or "none" if empty>
**Questions Incorporated:** <comma-separated question_id list, or "none" if empty>
**KPM Status:** <kpm_status from Step 4.2b — PROVENANCE_INDEXED | NO_PROVENANCE_INDEX>
**Status:** DRAFT
```

All seven fields are required. No field may be empty. If `conflicts_resolved` is an empty list: write `none`. If `questions_incorporated` is an empty list: write `none`.

### Step 6.2 — Transform Knowledge Sections

Iterate through the canonical specification section order:

```
1. Terms and Definitions  (← Terminology)
2. Context and Background (← Facts)
3. Design Decisions       (← Decisions)
4. Assumptions            (← Assumptions)
5. Constraints            (← Constraints)
6. Business Rules         (← Business Rules)
7. Technical Rules        (← Technical Rules)
```

For each section:

**If the section is present** in the Source Data Model (`sections.<key>` is non-null):

- Write the canonical section heading (e.g., `## 1. Terms and Definitions`).
- Reproduce the section content **verbatim** from the Source Data Model.
- Preserve all formatting: bullet points, sub-bullets, indentation, bold markers, and inline resolution notes.

**If the section is absent** in the Source Data Model (`sections.<key>` is null):

- Omit the section entirely. Do not write the heading or any placeholder content.

### Step 6.3 — Reproduce Resolution Notes Verbatim

Resolution notes in consolidated artifacts appear inline as:

```
> Resolution (<conflict_id>): <resolution text>
```

These are part of the section content extracted in Phase 4. They are reproduced verbatim by Step 6.2's content copy. Do not reformat, relocate, summarize, or remove any resolution note.

### Step 6.4 — Insert ADVISORY UNRESOLVED Flags

**If the Conflicts Index is empty** (Step 2.6: `conflicts_report.md` was not found): skip this step for all candidates. Proceed to Step 6.5.

**Identify unresolved ADVISORY conflicts for this source:**

Look up this candidate's `<base>` in the Conflicts Index. Retrieve all records where `severity == ADVISORY`.

For each retrieved ADVISORY conflict record: check whether `conflict_id` is in the Consolidated Conflict Set (Step 2.2).

- If `conflict_id` IS in the Consolidated Conflict Set (Step 2.2): the conflict is resolved. Skip this conflict.
- If `conflict_id` is NOT in the Consolidated Conflict Set (Step 2.2): the conflict is **unresolved ADVISORY**.

**For each unresolved ADVISORY conflict:**

Determine the target specification section:

1. Take the `section` field from the Conflicts Index record.
2. Apply Phase 5 section identification rules to map to the canonical specification section name (e.g., `Business Rules` → `6. Business Rules`).
3. If no mapping exists (section value not in the canonical mapping set): skip this conflict. Do not insert a flag for an unmappable section.

Append the following flag at the end of that specification section's content — after all verbatim content from Step 6.2:

```markdown
> [ADVISORY UNRESOLVED: <conflict_id> — awaiting consolidation]
```

**Constraint:** This is the only content `/generate-specification` may insert that does not derive verbatim from the source artifact. Any content inserted here must use exactly the format above with no variation.

**Intra-source CONTRADICTION deduplication:** A CONTRADICTION conflict where Item A and Item B map to the same `<base>` produces two entries for the same `conflict_id` in the Conflicts Index for that `<base>`. Insert the flag only once per `conflict_id`, using the first entry in the Conflicts Index entry list. Do not insert duplicate flags.

**If no unresolved ADVISORY conflicts exist for this candidate:** proceed to Step 6.5 without modification.

### Step 6.5 — Assemble Specification Provenance Section (CONSOLIDATED only)

For CONSOLIDATED-type candidates:

Build the `## Specification Provenance` table from the `resolved_conflicts` list in the Source Data Model.

For each conflict record in `resolved_conflicts`:

- Look up `specification_section = conflict_section_map[conflict_id]`.
- If `specification_section` is null (conflict resolved but no inline marker found): write `—` in the Specification Section column.
- Write one table row:

```markdown
| <specification_section or —> | <conflict_id> | <conflict_type> | <conflict_severity> | <question_id> | <resolution_summary> |
```

If the `resolved_conflicts` list is empty: omit the Provenance section entirely.

For EXTRACTED-type candidates: omit the `## Specification Provenance` section.

### Step 6.5b — Spec-Level Design Decision Detection (KPM — ALL candidates)

#### Objective

After assembling spec sections in Steps 6.1–6.5, scan all spec-level design sections for elements with no knowledge base backing. Build the `spec_design_map` in the Source Data Model. This step runs for every candidate regardless of `kpm_status`.

#### Definition: Spec-Level Design Section

A section is a **spec-level design section** if it is present in the assembled spec content AND its heading does not match any of the seven canonical knowledge-derived sections:

```
1. Terms and Definitions | 2. Context and Background | 3. Design Decisions
4. Assumptions | 5. Constraints | 6. Business Rules | 7. Technical Rules
```

Common examples: `## 5. Data Model`, `## 8. Architecture Overview`.

#### Step 6.5b.1 — Scan for Spec-Level Sections

Scan the assembled spec content (all sections from Steps 6.1–6.5 plus any spec-level sections added by the spec author or agent).

Identify all section headings that do NOT match the canonical seven sections.

For each identified spec-level section: proceed to Step 6.5b.2.

If no spec-level sections are present: set `spec_design_map = {}`. Skip to Step 6.6.

#### Step 6.5b.2 — Detect Source = — Elements

For each spec-level section, scan all Markdown tables within that section.

For each table:
- If the table contains a `Source` column (case-insensitive match): read the `Source` cell value for each row.
  - `Source = —` (dash) → element has no KB backing → proceed to Step 6.5b.3.
  - `Source = <KB reference>` → element is traceable; skip.
- If the table has **no** `Source` column: the entire table is in violation of SG-18. All rows are treated as `Source = —`. Log a SG-18 WARNING.

For narrative paragraphs (non-table content) in spec-level sections that introduce named entities — e.g., `"defined in a separate **QuestionnaireConfig** list"` — extract the entity name and treat it as `Source = —` (S1 structural, new entity).

#### Step 6.5b.3 — Classify and Build spec_design_map

For each element detected in Step 6.5b.2 (Source = — table rows and narrative entities):

**Classification (always ID or US):**

Since `Source = —` guarantees Q1=NO, Q2=NO, Q3=NO (no source, no validation, no logical derivation):

- Evaluate Q4 (TECH_STANDARD): apply only if the need is established by SF/UV and a single industry standard mandates this specific implementation. In spec-level elements this is exceptional.
- Evaluate Q5 (INFERRED_DESIGN): YES if the spec author could have made a different valid choice → **ID**.
- Q6 (UNDEFINED_IN_SOURCE): fallback if alternatives are too wide to justify any selection.
- Default: **ID** (Q5 fires for virtually all spec-level design decisions).

**Impact level determination (S1–S4):**

| Code | Condition | Result |
|---|---|---|
| S1 | Element is an entire new entity (list/table) absent from all sources and validations | `structural` |
| S2 | Element defines new lifecycle or workflow states visible to users | `structural` |
| S3 | Element modifies the solution boundary (new integration, new interface) | `structural` |
| S4 | Element affects permissions or access control | `structural` |
| — | None of S1–S4 apply | `implementation` |

**Governance status:**

- `structural` → `PENDING_VALIDATION`
- `implementation` → `REGISTERED`

**Rationale generation:**

Produce a one-sentence rationale of the form: `"<element> not specified in source or validations; selected from identifiable alternatives."` Spec-level context may enrich this if the assembly context makes it clear.

**Add to spec_design_map:**

```text
spec_design_map[element_name] = {
  type:              ID
  rationale:         "<one-sentence rationale>"
  impact_level:      structural | implementation
  governance_status: PENDING_VALIDATION | REGISTERED
}
```

`element_name` is the display label used in the Inference Registry — e.g., `"QuestionnaireConfig (liste)"`, `"Status : Draft / Active / Completed"`, `"AddedBy"`, `"Method : QRCode / ManualTrainer"`.

#### Step 6.5b.4 — Store result

Assign `spec_design_map` to the Source Data Model for this candidate. It is consumed by Step 6.7.

If Step 6.5b fails to parse any section: log a WARNING, set `spec_design_map = {}`, and continue. Non-blocking.

---

### Step 6.6 — Assemble Complete Specification Document

Assemble the complete specification in this exact structure:

**For CONSOLIDATED-type specifications:**

```markdown
# <display_name> — Draft Specification

<header block from Step 6.1>

---

<knowledge sections from Step 6.2, in canonical order>

---

## Specification Provenance

<provenance table from Step 6.5>

---

## Inference Registry

<Inference Registry from Step 6.7>
```

**For EXTRACTED-type specifications (no Specification Provenance):**

```markdown
# <display_name> — Draft Specification

<header block from Step 6.1>

---

<knowledge sections from Step 6.2, in canonical order>

---

## Inference Registry

<Inference Registry from Step 6.7>
```

The `---` separators are mandatory structural elements:
- First `---`: between header block and first knowledge section.
- Second `---` (CONSOLIDATED): between last knowledge section and Specification Provenance.
- Third `---` (CONSOLIDATED) / Second `---` (EXTRACTED): before `## Inference Registry`.

The `## Inference Registry` section is **always** present, including in T-MODE (where all 4 subsections contain `*(aucun élément)*`).

**STATUS: SPECIFICATION TRANSFORMATION COMPLETE**

---

### Step 6.7 — Inference Registry Generation

#### Objective

Build the `## Inference Registry` section content from **both** the `provenance_map` (extraction-level, from Step 4.2b) and the `spec_design_map` (spec-generation-level, from Step 6.5b) in the Source Data Model. This step runs for every candidate.

The Inference Registry aggregates from two input maps:

```
provenance_map   (extraction-level: elements classified during /extract-knowledge)
spec_design_map  (spec-generation-level: elements detected by Step 6.5b)
```

Both maps use the same 4-subsection structure and the same governance rules. Entries are indistinguishable in the final IR — their origin (extraction vs. spec-generation) is not surfaced to readers.

#### Step 6.7.0 — Reconcile governance_status with resolved conflicts

Run this reconciliation on the merged `provenance_map ∪ spec_design_map` **before** distributing entries into subsections.

For each entry where `impact_level == structural` and `governance_status == PENDING_VALIDATION`:

1. Determine whether the specification body attaches a conflict resolution to **this element**. It does when the element's own row or paragraph carries a `**Resolution (<conflict_id>):**` marker. An element is never matched by proximity, by section, or by sharing a conflict with a neighbour — only by carrying the marker itself.
2. If no marker is attached: leave `governance_status` unchanged. A genuinely unvalidated structural inference is a legitimate state, and this step must never invent validation for one.
3. If a marker is attached, verify **all three** of the following:
   - `<conflict_id>` is in the Consolidated Conflict Set (Step 2.2);
   - the `Question ID` recorded for that conflict in `consolidation_report.md` resolves to a question whose status in `questions_report.md` is `VALIDATED`;
   - that question's record carries `Validated By` and `Validation Date`.
4. If all three hold, set `governance_status = USER_VALIDATED` and record the evidence triple `<conflict_id> / <question_id> / <Answer Source session>`.
5. If a marker is attached but any of the three fails, leave `governance_status = PENDING_VALIDATION` and record the element in the Phase 10 completion report as an unreconciled contradiction. Do not silently resolve it either way.

Render promoted entries with `USER_VALIDATED` in the `Statut` column — the column keeps a single bare token, because the E6 BASELINE gate (`/specification-lifecycle`) and `tools/csr-check` W3 both read it as one. Append the evidence **below** the subsection table:

```markdown
> **Reconciled at generation (Step 6.7.0).** The following structural inferences moved from
> `PENDING_VALIDATION` to `USER_VALIDATED` because a human validation recorded in this project
> decided the exact element they describe:
>
> | Élément | Conflit | Question | Session |
> |---|---|---|---|
> | TR-001 | C001 | Q001 | VS001 |
```

**Scope boundary.** This reconciliation promotes only an element the resolution is explicitly attached to. It does not promote a sibling in the same table, an element of the same domain, or any other structural inference of the same specification. ADR-004 Engagement #6 is satisfied here because the human decision on record is a decision about that element, taken under `/human-validation`, which itself requires explicit human confirmation before any canonical record is written (ADR-001 § Normalization Point).

> **Why this step exists.** Nothing previously connected the two paths. `/human-validation` wrote its decision into the question record, `/consolidate-knowledge` carried it into the consolidated artifact, and `/generate-specification` reproduced it in the specification body as a `**Resolution (...)**` note — while the Inference Registry of the *same file* kept the element at `PENDING_VALIDATION`, because the registry was built from the Provenance Index alone. The result was a single artifact asserting both that an element was "Validated and implemented" and that it was awaiting validation. In workspace `demo-inventory-01`, 2 of the 7 structural inferences blocking the BASELINE of SP002 were in this state, and the block they produced was spurious. See finding F-10 of (internal review note); the automated check is `W3` in `tools/csr-check`.

#### T-MODE with no spec-level decisions (kpm_status = NO_PROVENANCE_INDEX AND spec_design_map = {})

Both maps are empty. All 4 subsections contain `*(aucun élément)*`.

```markdown
## Inference Registry

### INFERRED_DESIGN — Impact Structurel

*(aucun élément)*

### INFERRED_DESIGN — Détail d'Implémentation

*(aucun élément)*

### TECH_STANDARD

*(aucun élément)*

### UNDEFINED_IN_SOURCE

*(aucun élément)*
```

#### T-MODE with spec-level decisions (kpm_status = NO_PROVENANCE_INDEX AND spec_design_map ≠ {})

`provenance_map` is empty. Distribute entries from `spec_design_map` only. Extraction-level subsections that have no entries contain `*(aucun élément)*`.

Use the same distribution logic as PROVENANCE_INDEXED mode below, applied to `spec_design_map` entries.

#### PROVENANCE_INDEXED mode (and all modes with non-empty spec_design_map)

Distribute entries from `provenance_map ∪ spec_design_map` into 4 subsections by type:

| Subsection | Filter | Table columns |
|---|---|---|
| INFERRED_DESIGN — Impact Structurel | `type == ID` AND `impact_level == structural` | Élément, Rationale, Statut, Propagating |
| INFERRED_DESIGN — Détail d'Implémentation | `type == ID` AND `impact_level == implementation` | Élément, Rationale, Statut |
| TECH_STANDARD | `type == TS` | Élément, Standard (= refs field), Statut |
| UNDEFINED_IN_SOURCE | `type == US` | Élément, Statut |

The column header is `Élément` (renamed from `ID` to accommodate both KB item IDs and spec-level element names). Values come from either `provenance_map[ID]` (using the KB item ID as the element identifier) or `spec_design_map[element_name]` (using the declared element name).

**Table formats:**

INFERRED_DESIGN — Impact Structurel:
```markdown
| Élément | Rationale | Statut | Propagating |
|---|---|---|---|
| <id or element_name> | <rationale> | <governance_status> | — |
```

INFERRED_DESIGN — Détail d'Implémentation:
```markdown
| Élément | Rationale | Statut |
|---|---|---|
| <id or element_name> | <rationale> | <governance_status> |
```

TECH_STANDARD:
```markdown
| Élément | Standard | Statut |
|---|---|---|
| <id or element_name> | <refs> | ACKNOWLEDGED |
```

UNDEFINED_IN_SOURCE:
```markdown
| Élément | Statut |
|---|---|
| <id or element_name> | BLOCKED |
```

**Empty subsection rule:** If a subsection has zero qualifying entries from both maps: write `*(aucun élément)*` instead of an empty table. All 4 subsection headings are **always** present.

**Row order within each subsection:** `provenance_map` entries first (BR-NNN ascending, then TR-NNN ascending, then C-NNN ascending), followed by `spec_design_map` entries in the order they were detected in the spec (section order, then table row order).

**Rationale field:** Use the `rationale` value from the source map entry. If null or empty and type is ID: write `[rationale not provided]` as a signal of a classification defect.

**Propagating field (INFERRED_DESIGN — Impact Structurel only):** Always `—` unless the `provenance_map` entry explicitly carries `propagating: true`. `spec_design_map` entries always use `—` for this field.

---

## Phase 6-STD — STD Specification Generation (template_mode = STD only)

This phase is active when `template_mode = STD`. It replaces Phase 6 Steps 6.1–6.7 for STD workspaces (`spec_template_version: v1`). Legacy behavior (Steps 6.1–6.7) is untouched.

Process candidates one at a time.

---

### Step 6-STD.0 — Source Section Parsing

Use the SourceDataModel already built in Phase 4. Extract and label sections:

| Source Section Key | Internal Label | Primary STD Target |
|---|---|---|
| `sections.Terminology` | `kn_Terminology` | Section 14 — Glossaire |
| `sections.Facts` | `kn_Facts` | Section 1 — Contexte + Section 2 — Périmètre |
| `sections.Decisions` | `kn_Decisions` | Section 4 — Décisions de Design |
| `sections.Assumptions` | `kn_Assumptions` | Section 2.2 — Limites (supplemental) |
| `sections.Constraints` | `kn_Constraints` | NFR-NNN → Section 11 |
| `sections.BusinessRules` | `kn_BusinessRules` | Section 5.1 (verbatim BR) + FR-NNN → Section 6 |
| `sections.TechnicalRules` | `kn_TechnicalRules` | Section 5.2 (verbatim TR) |

**BR-NNN Item Extraction:** Scan `kn_BusinessRules` for bold ID patterns `**BR-\d+**:` (with optional list prefix `- ` or `* `). For each match, record:

```text
br_items[BR-NNN] = {
  text:       <full rule text after the colon>
  kpm_type:   provenance_map[BR-NNN].type         (null in T-MODE)
  kpm_impact: provenance_map[BR-NNN].impact_level (null if type ≠ ID)
}
```

**TR-NNN Item Extraction:** Same pattern from `kn_TechnicalRules`. Build `tr_items[TR-NNN]` with same fields.

**C-NNN Item Extraction:** Same pattern from `kn_Constraints`. Build `c_items[C-NNN]` with same fields.

**D-NNN Item Extraction:** Scan `kn_Decisions` for `**D-\d+**:` patterns. Build `d_items[D-NNN] = { text, kpm_type }`.

---

### Step 6-STD.1 — YAML Frontmatter

Generate the 8-field YAML frontmatter. `spec_id` uses `SP-TBD` as placeholder — replaced with the actual SP<NNN> assignment in Phase 8.2 before final write.

If this base has a prior generation entry in the existing records map (Step 8.1): retain the existing `spec_id` value and `version` value.

```yaml
---
spec_id: SP-TBD
title: "<display_name>"
workspace_id: "<workspace_id>"
version: "1.0"
status: DRAFT
baseline_date: null
language: fr
template_version: "v1"
---
```

`display_name`: from Phase 4.6.
`workspace_id`: active workspace from Phase 1.
`language`: read from workspace registry if a `language` column exists; default `fr`.

---

### Step 6-STD.2 — Generation Metadata Block

Immediately after the YAML closing `---`, write the generation metadata block. This block enables SG2 and SG15 verification and replaces the legacy Markdown bold header.

```markdown
**Source Artifact:** <source_artifact_path>
**Source Type:** <CONSOLIDATED | EXTRACTED>
**Generated:** <ISO 8601 date>
**Generation Command:** /generate-specification
**Conflicts Incorporated:** <comma-separated conflict_ids, or "none">
**Questions Incorporated:** <comma-separated question_ids, or "none">
**KPM Status:** <kpm_status>
```

All seven metadata fields are required. Values are identical to those used in the legacy header block (Steps 6.1 field definitions apply).

---

### Step 6-STD.3 — FR-NNN Generation (Section 6 — DK Mode)

For each BR-NNN in `br_items`, in ascending BR-NNN order:

**DK Projection Rule:** Transform the BR text into an FR-form system capability statement:

```text
"Le système [verbe actif : empêche / réserve / valide / affiche / calcule / enregistre / ...] [objet / comportement] [condition si pertinente]."
```

Identify the system behavior implied by the BR text and reformulate it as a system capability. This is a deterministic semantic projection: for a given BR text, one canonical FR form is derivable.

**R4 Cascade — FR KPM type:**

| BR KPM Type | FR KPM Type |
|---|---|
| SF | DK |
| UV | DK |
| DK | DK |
| TS | DK |
| ID:structural | ID:structural |
| ID:implementation | ID:implementation |
| US | US |
| null (T-MODE) | DK |

Assign sequential IDs: FR-001, FR-002, ... (one per BR-NNN, in ascending BR-NNN order).

Build `fr_items`:

```text
fr_items[FR-NNN] = {
  br_source:  BR-NNN
  text:       <DK projection text in "Le système..." form>
  domain:     <domain from BR if determinable; "—" otherwise>
  priority:   <priority from BR if available; "HAUTE" otherwise>
  kpm_type:   <FR KPM type per R4 above>
  kpm_impact: <impact_level if kpm_type = ID; null otherwise>
  status:     ACTIF
}
```

**US FR rule:** If a BR-NNN is US-classified, the derived FR is also US. Add to `op_pending` list: `{ fr_id: FR-NNN, br_id: BR-NNN, reason: "FR trop vague — source US" }`.

---

### Step 6-STD.4 — AC-NNN Generation (Section 7)

For each FR-NNN in `fr_items`, in ascending FR-NNN order:

**AC Derivation:**

- If `fr_items[FR-NNN].kpm_type ∈ { DK, SF, UV, TS, ID:implementation, ID:structural }`: derive AC in Given/When/Then from the FR text. Status = `DK`.
- If `fr_items[FR-NNN].kpm_type = US`: AC is a placeholder. Status = `US`. Add to `op_pending`.

Given/When/Then extraction rule:

```text
Given: <initial system or user state implied by the FR precondition>
When:  <triggering action or event implied by the FR>
Then:  <expected system response stated in the FR>
```

Assign sequential IDs: AC-001, AC-002, ... (one per FR-NNN, in ascending FR-NNN order).

**R4 cascade for AC:** AC inherits the FR's KPM type.

Build `ac_items`:

```text
ac_items[AC-NNN] = {
  fr_source: FR-NNN
  given:     <given text>
  when:      <when text>
  then:      <then text>
  kpm_type:  <same as FR source, per R4>
  status:    DK | US
}
```

---

### Step 6-STD.5 — NFR-NNN Generation (Section 11)

For each C-NNN in `c_items`, in ascending C-NNN order:

**Category Assignment:** Infer the NFR category from the C-NNN text content (case-insensitive keyword matching):

| Category | Detection Keywords |
|---|---|
| Performance | response time, latency, throughput, temps de réponse, délai |
| Disponibilité | uptime, SLA, availability, disponibilité, continuité |
| Capacité | volume, concurrent users, capacity, capacité, charge, utilisateurs simultanés |
| Sécurité | authentication, authorization, encryption, sécurité, chiffrement, accès |
| Contrainte | (default — all other measurable constraints) |

**Seuil (threshold):** Extract the measurable threshold from the C-NNN text (e.g., `≤ 2s`, `99.9%`, `1000 utilisateurs simultanés`). If no measurable threshold is present: write `—`.

**R4 Cascade — NFR KPM type:**

| C-NNN KPM Type | NFR KPM Type |
|---|---|
| SF | DK |
| UV | DK |
| DK | DK |
| ID:implementation | ID:implementation |
| ID:structural | ID:structural |
| US | US |
| null (T-MODE) | DK |

Assign sequential IDs: NFR-001, NFR-002, ... (ascending C-NNN order).

Build `nfr_items`:

```text
nfr_items[NFR-NNN] = {
  c_source:     C-NNN
  category:     Performance | Disponibilité | Capacité | Sécurité | Contrainte
  description:  <C-NNN text reformulated as NFR statement>
  seuil:        <extracted threshold or "—">
  kpm_type:     <NFR KPM type per R4>
  source_label: "C-NNN (kpm_type)"
  status:       ACTIF
}
```

**US NFR rule:** If C-NNN is US-classified: add to `op_pending`.

**S11 minimum check:** If `nfr_items` contains no entry with `category = Performance` AND no entry with `category = Disponibilité`: issue WARNING `S11 minimum requis non satisfait: au moins 1 NFR Performance + 1 NFR Disponibilité requis pour une spec BASELINABLE.` S11 is still generated with all available NFR entries (non-blocking for generation).

---

### Step 6-STD.6 — OP-NNN Generation (Section 13)

Build `op_items` from three sources in order:

**Source 1 — ADVISORY UNRESOLVED conflicts** (same unresolved ADVISORY conflicts identified in the Phase 6.4 logic for this candidate):

For each unresolved ADVISORY conflict `{ conflict_id, conflict_type, section }`:

```text
op_items[OP-NNN] = {
  description: "Conflit non résolu : <conflict_id> (<conflict_type>) — section KB : <section>"
  source:      "ADVISORY"
  priority:    HAUTE
  status:      OPEN
  resolution:  "Consolidation requise via /consolidate-knowledge"
}
```

**Source 2 — US FR items** (from `op_pending` where reason = "FR trop vague"):

```text
op_items[OP-NNN] = {
  description: "<FR-NNN> : Exigence fonctionnelle indéterminée (source BR US)"
  source:      "US"
  priority:    HAUTE
  status:      OPEN
  resolution:  "HITL-3 — définir le comportement système attendu"
}
```

**Source 3 — US AC and NFR items** (from `op_pending` where reason involves US AC or US NFR):

```text
op_items[OP-NNN] = {
  description: "<AC-NNN or NFR-NNN> : Critère ou exigence indéterminé(e)"
  source:      "US"
  priority:    HAUTE
  status:      OPEN
  resolution:  "HITL-3 — définir le contenu"
}
```

Assign sequential IDs: OP-001, OP-002, ... (Source 1 first, then Source 2, then Source 3).

If `op_items` is empty: `op_table_content = "*(aucun point ouvert)*"`.

---

### Step 6-STD.7 — Section Assembly

Assemble each STD section from the prepared data:

#### Section 1 — Contexte et Objectifs [OBL]

Source: `kn_Facts` verbatim content. Place under subsections `### 1.1 Contexte` and `### 1.2 Objectifs`. If `kn_Facts` is null: placeholder `*[Contexte à compléter — section Facts absente du knowledge artifact.]*`.

#### Section 2 — Périmètre [OBL]

Source: scope-related content from `kn_Facts` + scope-limiting content from `kn_Assumptions`. Extract "inclus" (in-scope) and "limites" (boundary) elements. If content not clearly separable: reproduce `kn_Facts` content under `### 2.1 Inclus` and use `kn_Assumptions` content (if non-null) under `### 2.2 Limites`. Include the cross-reference link to Section 12 for excluded items.

#### Section 3 — Profils Utilisateurs [COND]

COND: include if `kn_Facts` content contains user/role/actor keywords (case-insensitive: `utilisateur`, `user`, `rôle`, `role`, `acteur`, `actor`, `profil`). Format as a table with columns: `Rôle | Description | Droits principaux | Volume estimé`. If COND not met: omit Section 3 entirely.

#### Section 4 — Décisions de Design [OBL]

Source: `d_items` from `kn_Decisions`. Format as table:

```markdown
| ID | Décision | Statut | Source | Justification | Autorité |
|---|---|---|---|---|---|
| D-NNN | <text> | APPROUVÉE | <kpm_type> | <justification> | SF / UV / ADR-NNN |
```

If `kn_Decisions` null or `d_items` empty: single row `| *(aucune décision documentée)* | — | — | — | — | — |`.

#### Section 5 — Règles de Gestion [OBL]

**5.1 Règles Métier (BR-NNN):** For each BR-NNN in `br_items` (ascending order):

```markdown
| ID | Domaine | Description | Priorité | Source | Statut |
|---|---|---|---|---|---|
| BR-NNN | <domain or —> | <text> | HAUTE / MOYENNE / BASSE | <kpm_type> | ACTIF |
```

If `br_items` empty: single data row `| *(aucune règle métier)* | — | — | — | — | — |`

**5.2 Règles Techniques (TR-NNN):** For each TR-NNN in `tr_items` (ascending order):

```markdown
| ID | Domaine | Description | Priorité | Source | Statut |
|---|---|---|---|---|---|
| TR-NNN | <domain or —> | <text> | HAUTE | <kpm_type> | ACTIF |
```

If `tr_items` empty: single data row `| *(aucune règle technique)* | — | — | — | — | — |`

#### Section 6 — Exigences Fonctionnelles [OBL]

From `fr_items` (ascending FR-NNN):

```markdown
| ID | Priorité | Description | Domaine | BR Source | Source | Statut |
|---|---|---|---|---|---|---|
| FR-NNN | <priority> | <FR text> | <domain or —> | <BR-NNN> | <kpm_type as label> | ACTIF |
```

`Source` column label for each FR:
- DK → `DK`
- SF → `SF`
- ID:structural → `ID:structural`
- ID:implementation → `ID:implementation`
- US → `US`

#### Section 7 — Acceptance Criteria [OBL]

From `ac_items` (ascending AC-NNN):

```markdown
| ID | FR Couvert | Given | When | Then | Source | Preuve | Démontré en |
|---|---|---|---|---|---|---|---|
| AC-NNN | <FR-NNN> | <given> | <when> | <then> | DK / US | NON_DÉMONTRÉ | — |
```

**`Preuve` and `Démontré en` are emitted with their default values and are never computed at generation time (ADR-007).** An acceptance criterion is, by construction, a claim that only an execution event can settle — a UAT, a production release, a manual test. At generation time no such event has occurred, so `NON_DÉMONTRÉ` and `—` are the only correct values. Do not attempt to infer a proof state from the sources: a source describing a system that works is not a demonstration that this criterion passes.

The two columns exist so that the user has somewhere to record the result later. Filling them is optional and is **not** a precondition of any gate — see `specification-lifecycle.md` and ADR-007 §5.1.

#### Sections 8, 9, 10 — COND Sections

**Section 8 — Flux Métier [COND]:** Include if workflow/process content detected in `kn_Facts` (keywords: `processus`, `workflow`, `étape`, `flux`, `sequence`, case-insensitive). Otherwise omit.

**Section 9 — Interfaces Utilisateur [COND]:** Include if UI/interface content detected in `kn_Facts` (keywords: `écran`, `interface`, `formulaire`, `view`, `screen`, `UI`). Otherwise omit.

**Section 10 — Modèle de Données [COND]:** Include if data model content detected in `kn_Facts` (keywords: `entité`, `table`, `entity`, `champ`, `field`, `modèle de données`, `data model`). Otherwise omit.

When a COND section is included: reproduce relevant source content verbatim in the appropriate subsection format from `templates/spec_canonical_v1.md`.

#### Section 11 — Exigences Non-Fonctionnelles [OBL]

From `nfr_items` (ascending NFR-NNN):

```markdown
| ID | Catégorie | Description | Seuil | Source | Statut | Preuve | Mesuré | Démontré en |
|---|---|---|---|---|---|---|---|---|
| NFR-NNN | <category> | <description> | <seuil or —> | <source_label> | ACTIF | NON_DÉMONTRÉ | — | — |
```

**Same rule as Section 7 (ADR-007):** `Preuve`, `Mesuré` and `Démontré en` are emitted at their defaults and never computed. A threshold is a measurable claim; only a measurement establishes it. A source stating a target value states the target, not the measurement.

If `nfr_items` empty: single data row `| *(aucune exigence non-fonctionnelle identifiée)* | — | — | — | — | — | — | — | — |`.

#### Section 12 — Hors Périmètre [OBL]

Source: items explicitly out-of-scope identified in `kn_Facts`, `kn_Assumptions`, or `kn_Constraints` that do not appear in FR/NFR lists (scan for "hors-périmètre", "out of scope", "exclu", "excluded", "not in scope" keywords, case-insensitive).

Format:
```markdown
| # | Élément exclu | Justification |
|---|---|---|
| 1 | <excluded item> | <justification> |
```

If no out-of-scope items identified: single row `| 1 | *(à compléter — éléments hors-périmètre non documentés dans les sources)* | [Justification requise] |`.

#### Section 13 — Points Ouverts [OBL]

From `op_items`:
```markdown
| ID | Description | Source | Priorité | Statut | Responsable | Résolution attendue |
|---|---|---|---|---|---|---|
| OP-NNN | <description> | <source> | <priority> | OPEN | — | <resolution> |
```

**`Responsable` is emitted empty and never inferred (E4).** No source names the owner of a gap it does not know it has, and guessing one would be inventing content. The column exists so the assignment has somewhere to land once it happens — the same reservation of place as `Preuve` under ADR-007. An empty owner blocks no gate.

If `op_items` empty: `*(aucun point ouvert)*`.

#### Section 14 — Glossaire [OBL]

Source: `kn_Terminology` verbatim content formatted as table:
```markdown
| Terme | Définition | Source |
|---|---|---|
| <term> | <definition> | <kpm_type or "—"> |
```

If `kn_Terminology` null: single data row `| *(terminologie à compléter)* | — | — |`.

#### Section 15 — Validation et Signatures [OBL pour BASELINE]

Always present as placeholder:
```markdown
| Rôle | Prénom Nom | Verdict | Date | Commentaire |
|---|---|---|---|---|
| *(à compléter)* | *(à compléter)* | APPROUVÉ / RÉSERVÉ / REFUSÉ | *(YYYY-MM-DD)* | *(Optionnel)* |
```

---

### Step 6-STD.8 — Annexe A — Inference Registry [OBL]

Build the Inference Registry using the same 4-subsection structure as Phase 6.7, with the following STD-specific rules:

**Mandatory S0 entry:** Always add to `INFERRED_DESIGN — Détail d'Implémentation`:

```markdown
| S0 — Résumé Exécutif | Synthèse spec-level des sections S1–S15. Chaque affirmation référence une section du corps de la spec. Vérification lors de HITL-3. |
```

**FR/AC/NFR entries with ID classification:** Apply same distribution logic as Phase 6.7 but applied to `fr_items`, `ac_items`, and `nfr_items`:

- `fr_items[FR-NNN].kpm_type = ID:structural` → add to `INFERRED_DESIGN — Impact Structurel` with `Critère Sx` column (evaluate S1-S4 criteria from FR text).
- `fr_items[FR-NNN].kpm_type = ID:implementation` → add to `INFERRED_DESIGN — Détail d'Implémentation`.
- Same for `nfr_items[NFR-NNN]`.
- `ac_items[AC-NNN].kpm_type = ID:structural` (rare, via R4 from FR:ID:structural) → add to `INFERRED_DESIGN — Impact Structurel`.

**Standard KB-level entries** from `provenance_map ∪ spec_design_map`: same as Phase 6.7. `provenance_map` entries ordered first (BR-NNN ascending, TR-NNN ascending, C-NNN ascending), then FR/AC/NFR ID entries ascending, then `spec_design_map` entries in section detection order.

**Output format:** Identical to Phase 6.7 structure. The heading is `## Annexe A — Inference Registry` instead of `## Inference Registry` to match the STD template.

---

### Step 6-STD.9 — Annexe B — Specification Provenance [COND multi-source]

**Condition:** Present when the workspace has ≥2 INGESTED sources. Detection: read `WORKSPACE_ROOT/runtime/sources.md`; count rows with status `INGESTED`. If count ≥ 2: include Annexe B. Otherwise: omit.

If present:

**Sources table:** List all INGESTED sources from `sources.md` (columns: ID Source, Nom du Document, Date Ingestion, Type, Statut).

**Carte de Provenance:** For each BR-NNN, TR-NNN, D-NNN in the spec, map to contributing source(s):

```markdown
| Élément | S1 | S2 | ... | Note |
|---|---|---|---|---|
| BR-001 | ✅ | — | | Source primaire S1 |
```

Cross-reference with the `## Source` section of the source artifact (if available) or the Consolidation Index (Step 2.2) for multi-source attribution.

Note: For CONSOLIDATED candidates, the Consolidated Conflict Provenance (which conflicts were resolved into this spec) is available in the generation metadata `**Conflicts Incorporated:**` field and the existing `consolidation_report.md`. Annexe B focuses on source-document attribution, not conflict traceability.

---

### Step 6-STD.10 — Section 0 Generation (S0 — deferred, requires S1–S15 counts)

After all sections S1–S15 and Annexes A/B are assembled:

Compute from assembled data:
- `count_fr` = count of ACTIF FR-NNN entries in Section 6
- `count_br` = count of BR-NNN entries in Section 5.1
- `count_tr` = count of TR-NNN entries in Section 5.2
- `count_d` = count of D-NNN entries in Section 4
- `count_op` = count of OP-NNN entries in Section 13
- `count_op_blocking` = count of OP-NNN with `priority = HAUTE`

Generate S0 content:

```markdown
## Section 0 — Résumé Exécutif

> **Généré automatiquement par /generate-specification.** Chaque affirmation est vérifiable
> par référence croisée à une section S1–S15. Aucun fait nouveau n'est introduit ici.

Ce document spécifie le comportement attendu du système <system name from S1 context>.

**Portée fonctionnelle :** <count_fr> exigences fonctionnelles actives (→ Section 6).
**Règles de gestion :** <count_br> règles métier + <count_tr> règles techniques (→ Section 5).
**Décisions de conception :** <count_d> décisions documentées (→ Section 4).
**Points d'attention :** <count_op> points ouverts (<count_op_blocking> de priorité HAUTE) (→ Section 13).
**Statut :** DRAFT. BASELINE possible après résolution des points ouverts de priorité HAUTE (→ Section 13, Section 15).
```

If the system name cannot be determined from S1 content: write `du système spécifié`.

S0 entry in Annexe A is pre-populated (Step 6-STD.8) and classifies S0 as `ID:implementation` (non-blocking).

---

### Step 6-STD.11 — STD Document Assembly

Assemble the complete STD specification in this exact structure:

```markdown
---
spec_id: SP-TBD
title: "<display_name>"
workspace_id: "<workspace_id>"
version: "1.0"
status: DRAFT
baseline_date: null
language: fr
template_version: "v1"
---

**Source Artifact:** <source_artifact_path>
**Source Type:** <CONSOLIDATED | EXTRACTED>
**Generated:** <ISO 8601 date>
**Generation Command:** /generate-specification
**Conflicts Incorporated:** <conflict_ids or "none">
**Questions Incorporated:** <question_ids or "none">
**KPM Status:** <kpm_status>

# <display_name> — Spécification Canonique v1

> **Template :** spec_canonical_v1 — CSR CURRENT_RUNTIME_VERSION

---

## Section 0 — Résumé Exécutif

<S0 content from Step 6-STD.10>

---

## Section 1 — Contexte et Objectifs

<S1 content>

---

## Section 2 — Périmètre

<S2 content>

---

[## Section 3 — Profils Utilisateurs  ← included only if COND met]

---

## Section 4 — Décisions de Design

<S4 table>

---

## Section 5 — Règles de Gestion

### 5.1 Règles Métier (BR-NNN)

<BR table>

### 5.2 Règles Techniques (TR-NNN)

<TR table>

---

## Section 6 — Exigences Fonctionnelles

<FR-NNN table>

---

## Section 7 — Acceptance Criteria

<AC-NNN table>

---

[## Section 8 — Flux Métier  ← if COND met]
[## Section 9 — Interfaces Utilisateur  ← if COND met]
[## Section 10 — Modèle de Données  ← if COND met]

---

## Section 11 — Exigences Non-Fonctionnelles

<NFR-NNN table>

---

## Section 12 — Hors Périmètre

<S12 table>

---

## Section 13 — Points Ouverts

<OP-NNN table or *(aucun point ouvert)*>

---

## Section 14 — Glossaire

<Terminology table>

---

## Section 15 — Validation et Signatures

<S15 placeholder table>

---

## Annexe A — Inference Registry

<4 subsections — always present>

---

[## Annexe B — Specification Provenance  ← if multi-source (≥2 INGESTED sources)]
```

`---` separators between sections are mandatory structural elements.

`SP-TBD` in YAML is replaced with the actual SP<NNN> value after Phase 8.2 ID assignment, before the file is written in Phase 7.

**STATUS: STD SPECIFICATION TRANSFORMATION COMPLETE**

---

## Phase 6b — V2 Specification Assembly (V2 mode only)

This phase replaces Phase 6 Step 6.6 when `spec_mode = V2`. Phases 6.1–6.5 are skipped in V2 mode. The V2 assembly constructs a merged specification from the inherited v1 content and the v2 delta.

### Step 6b.1 — Apply v2 delta to v1 rule map

Start from `v1_rule_map` (Phase 0). Apply mutations from `v2_delta` (Phase 4.2a):

1. **Deprecated rules** (`v2_delta.deprecated`):
   - Find the rule ID in `v1_rule_map`.
   - Set `annotation = "[DEPRECATED in v2]"` on that entry.

2. **Modified rules** (`v2_delta.modified`):
   - Find the rule ID in `v1_rule_map`.
   - Replace `text` with the new v2 text.
   - Set `annotation = "[v2-modified]"` on that entry.

3. **Added rules** (`v2_delta.added`):
   - These are new IDs not in `v1_rule_map`.
   - Add them to the map with `annotation = "[v2-added]"`.

Result: a **merged rule map** containing all v1 rules (with mutations applied) + all v2-added rules.

### Step 6b.2 — Assemble per-section content

For each canonical section (5. Constraints, 6. Business Rules, 7. Technical Rules):

1. Write all rules from the merged rule map that belong to this section, in ascending ID order.
2. Rules with `annotation = "[v2-modified]"` are rendered as: `**BR-005** [v2-modified] — <new text>`
3. Rules with `annotation = "[DEPRECATED in v2]"` are rendered as: `**BR-013** [DEPRECATED in v2] — <original text>`
4. Rules with `annotation = "[v2-added]"` are rendered as: `**BR-016** [v2-added] — <text>`
5. Rules with `annotation = null` (unchanged v1 rules) are rendered verbatim from v1: `**BR-001** — <v1 text>`

### Step 6b.3 — Assemble Section Δ v2

Build the Section Δ v2 as defined in `templates/spec_v2_template.md`:

```markdown
## Δ v2 — Modifications et Ajouts

### Nouvelles règles (v2-added)

| ID | Type | Description courte |
|----|------|-------------------|
| <ID> | <Type> | <first 80 chars of rule text> |

### Règles modifiées (v2-modified)

| ID | Type | Changement |
|----|------|-----------|
| <ID> | <Type> | <nature of change vs v1> |

### Règles supprimées (DEPRECATED in v2)

| ID | Type | Raison |
|----|------|--------|
| <ID> | <Type> | [Reason from rule text or "Superseded in v2"] |

### Résumé statistique

| Catégorie | v1 | v2-added | v2-modified | DEPRECATED | Total v2 actif |
|-----------|-----|----------|-------------|------------|----------------|
| BR | <count> | <count> | <count> | <count> | <v1+added-deprecated> |
| TR | <count> | <count> | <count> | <count> | <v1+added-deprecated> |
| C  | <count> | <count> | <count> | <count> | <v1+added-deprecated> |
| **Total** | ... | ... | ... | ... | ... |
```

If any delta category (added/modified/deprecated) is empty: include the subsection heading but write "None for this version." instead of the table.

### Step 6b.4 — Assemble V2 Header Block

```markdown
**Source Artifact:** <v2 knowledge artifact path>
**Source Type:** EXTRACTED-V2
**Generated:** <ISO 8601 date>
**Generation Command:** /generate-specification
**Workspace:** <workspace_id>
**Lineage:** <source_workspace_id> (v1 BASELINED <date from inherited spec>)
**ID Governance:** runtime/id_governance.md
**Status:** DRAFT
```

### Step 6b.5 — Assemble Guide de lecture callout

```markdown
> **Guide de lecture v2**
>
> Ce document est le complément de la spécification v1 (BASELINED [date]).
>
> - Règles **sans annotation** : héritées de v1, inchangées.
> - Règles annotées `[v2-added]` : nouvelles en v2.
> - Règles annotées `[v2-modified]` : existaient en v1, modifiées en v2.
> - Règles annotées `[DEPRECATED in v2]` : existaient en v1, supprimées ou remplacées en v2.
>
> La section **Δ v2** en fin de document récapitule toutes les modifications.
```

### Step 6b.6 — Assemble Complete V2 Specification Document

```markdown
# <display_name> — Specification v2

<header block from Step 6b.4>

---

<guide de lecture callout from Step 6b.5>

---

## 1. Terms and Definitions

<v1 inherited content + v2-added terms if any>

## 2. Context and Background

<v1 inherited content + v2 modifications if any>

## 3. Design Decisions

<v1 inherited content + v2-added decisions if any>

## 4. Assumptions

<v1 inherited content or "No assumptions documented.">

## 5. Constraints

<merged rule content from Step 6b.2>

## 6. Business Rules

<merged rule content from Step 6b.2>

## 7. Technical Rules

<merged rule content from Step 6b.2>

---

## Δ v2 — Modifications et Ajouts

<Section Δ from Step 6b.3>

---

## Traceability Note

La traceability matrix v2 (`specifications/draft/<inherited_base>_traceability_v2.md`) couvre :
- Toutes les règles héritées de v1 (version_introduced: v1)
- Toutes les règles v2-added (version_introduced: v2)
- Les règles modifiées (version_introduced: v1, version_updated: v2)
```

**STATUS: V2 SPECIFICATION ASSEMBLY COMPLETE**

---

## Phase 7 — Specification Writing

### Objective

Write the assembled specification document to the output path and verify the write.

### Step 7.1 — Determine Output Path

**V1 mode:**

```text
output_path = WORKSPACE_ROOT/specifications/draft/<base>_specification.md
```

Where `<base>` is derived from the source artifact filename:
- From CONSOLIDATED: strip `_consolidated.md` from the consolidated artifact filename.
- From EXTRACTED: strip `_knowledge.md` from the extracted artifact filename.

**V2 mode:**

```text
output_path = WORKSPACE_ROOT/specifications/draft/<inherited_base>_specification_v2.md
```

Where `inherited_base` is the base name of the inherited BASELINED spec from Phase 0.

In both modes, verify that `output_path` is within `WORKSPACE_ROOT/specifications/draft/`. If not: workspace contamination — stop for this candidate. Record the violation.

### Step 7.2 — Check for Existing File

If a file already exists at `output_path`:

Since `/generate-specification` is a structural transformation runtime, re-writing a previously generated specification from the same source is semantically safe (deterministic transformation). Overwrite the existing file.

Do not preserve or merge previous content. Write the fully assembled specification document.

### Step 7.3 — Write Specification File

Write the assembled document from Step 6.6 to `output_path`.

Verify the file exists and is readable after write. If the write fails or the file is unreadable after write:

Mark this candidate as a **per-candidate write failure**. Record:

```text
WRITE FAILURE — specifications/draft/<base>_specification.md: <reason>
```

Continue with remaining candidates. Declare SPECIFICATION PARTIAL at completion.

### Write Ordering

Write all specification files before updating the generation log:

```
Step 1: Write draft specification artifacts (*_specification.md)  [this phase]
Step 2: Write generation log (specifications_report.md)           [Phase 8]
```

Never reverse this order. Never update the generation log before all specification files have been written and verified.

**STATUS: SPECIFICATION WRITING COMPLETE**

---

## Phase 8 — Specification Registry Update

### Objective

Write or update the generation log to record the outcome of this execution.

The generation log is an informational audit record. It does not gate re-processing. It is written after all specification files have been verified.

### Step 8.1 — Read Existing Log

Read `WORKSPACE_ROOT/specifications/draft/specifications_report.md` if it exists.

If it exists: parse the `## Specification Records` section to build the existing records map: `<base>` → existing record (Spec ID, Source Type, Source Artifact, Specification Artifact, Conflicts Incorporated, Questions Incorporated, Generation Date, Status).

If it does not exist: the existing records map is empty. This is the first generation run.

### Step 8.2 — Assign Spec IDs

For each successfully generated specification (candidates that reached Phase 7 Step 7.3 without failure):

- If a record for this `<base>` already exists in the existing records map: **retain the existing Spec ID**. Update in place.
- If no record exists: **assign a new Spec ID**.

New Spec ID assignment:

```
next_id = highest existing SP<NNN> value + 1
```

If no existing records: next_id = 1.

Format: `SP<NNN>` where NNN is zero-padded to three digits (SP001, SP002, ...).

### Step 8.3 — Build Updated Log Content

Assemble the complete `specifications_report.md` content.

**Metadata block:**

```markdown
## Metadata
- Last Updated: <ISO 8601 date of this execution>
- Total Specifications Generated: <count of GENERATED records in updated log>
- Generated from consolidated: <count of CONSOLIDATED-type GENERATED records>
- Generated from extracted (zero-conflict): <count of EXTRACTED-type GENERATED records>
- Generation Failed: <count of candidates that failed in this execution>
```

**Summary table:** Rebuild from all records (existing + new/updated). Include one row per `<base>`.

**Specification Records:** Rebuild all `### SP<NNN>` blocks. For updated records: replace with new content (updated Generation Date). For unchanged records: reproduce as-is.

**Format for each Specification Record:**

```markdown
### <spec_id>

**Spec ID:** <spec_id>
**Source Type:** <CONSOLIDATED | EXTRACTED>
**Source Artifact:** <source_artifact_path>
**Specification Artifact:** specifications/draft/<base>_specification.md
**Conflicts Incorporated:** <comma-separated conflict_ids, or "none">
**Questions Incorporated:** <comma-separated question_ids, or "none">
**Generation Date:** <ISO 8601 date of this execution>
**Status:** GENERATED

---
```

### Step 8.4 — Write Generation Log

Write the assembled content to:

```text
WORKSPACE_ROOT/specifications/draft/specifications_report.md
```

If the write fails after specification files have been produced:

Stop. Do not retry. Append the following GENERATION FAILURE NOTE to each affected specification file (those successfully written but not yet recorded):

```markdown
> **GENERATION FAILURE NOTE:** /generate-specification failed to update specifications_report.md after writing this specification artifact. Manual registry update required before this specification can be considered fully recorded.
```

Report all affected base names. Stop execution.

**STATUS: GENERATION LOG UPDATED**

---

## Phase 8.5 — Traceability Matrix Generation

### Objective

Generate a traceability matrix mapping all BR-NNN, TR-NNN, and C-NNN identifiers in the knowledge artifact to their knowledge section and source document.

### Inputs

- Knowledge artifact for this source group (already loaded in Phase 4/5)
- Source registry (`WORKSPACE_ROOT/runtime/sources.md`) — for `origin_path` lookup
- Generation log (`specifications_report.md`) — for source artifact path

### Actions

For each processed source group:

1. **Parse identifiers from knowledge artifact:**
   - Scan `# Business Rules` section for `**BR-NNN:**` patterns → collect (ID, section=`# Business Rules`)
   - Scan `# Technical Rules` section for `**TR-NNN:**` patterns → collect (ID, section=`# Technical Rules`)
   - Scan `# Constraints` section for `**C-NNN:**` patterns → collect (ID, section=`# Constraints`)

2. **Resolve source document path:**
   - Read `origin_path` from the raw registration record in `knowledge_base/raw/` for this source.
   - If not resolvable: use `[origin_path not found]`.

3. **Assemble matrix rows:**
   - One row per identifier.
   - Row order: BR-NNN ascending, then TR-NNN ascending, then C-NNN ascending.

4. **Write traceability matrix:**
   - Path: `WORKSPACE_ROOT/specifications/draft/<base>_traceability.md`
   - Use the format defined in the contract (`docs/commands/generate-specification.md`).
   - Write even if zero rows.

   **Matrix format:**

   ```markdown
   # Traceability Matrix — <base>

   **Base:** <base>
   **Specification:** specifications/draft/<base>_specification.md
   **Knowledge Artifact:** knowledge_base/extracted/<base>_knowledge.md
   **Generated:** <ISO 8601 date>
   **Generated by:** /generate-specification
   **KPM Status:** <kpm_status from SourceDataModel>

   | ID | Type | Provenance | Knowledge Section | Knowledge Artifact | Source Document |
   |----|------|-----------|------------------|--------------------|-----------------|
   | BR-001 | Business Rule | SF | # Business Rules | knowledge_base/extracted/<base>_knowledge.md | input/documents/<source_file> |
   | BR-015 | Business Rule | ID:structural | # Business Rules | knowledge_base/extracted/<base>_knowledge.md | input/documents/<source_file> |
   ```

   **Provenance column values:** Read from `provenance_map[ID].type`. Format:
   - `SF` / `UV` / `DK` / `TS` / `US` → write the type code directly.
   - `ID` with `impact_level == structural` → write `ID:structural`.
   - `ID` with `impact_level == implementation` → write `ID:implementation`.
   - ID not found in `provenance_map` → write `—`.
   - T-MODE (`kpm_status = NO_PROVENANCE_INDEX`) → write `—` for all rows.

   Type mapping:
   - `BR-NNN` → `Business Rule`
   - `TR-NNN` → `Technical Rule`
   - `C-NNN` → `Constraint`

5. **On write failure:**
   - Append a WARNING to the generation log.
   - Do not block specification generation. This is non-blocking.

### STD Traceability Matrix (template_mode = STD only)

When `template_mode = STD`, the traceability matrix covers all STD identifiers generated in Phase 6-STD.

**Parse identifiers from the assembled STD specification** (already in memory from Phase 6-STD):

| Section scanned | Identifier pattern | Type label |
|---|---|---|
| Section 5.1 Règles Métier | `BR-\d+` in table ID column | Business Rule |
| Section 5.2 Règles Techniques | `TR-\d+` in table ID column | Technical Rule |
| Section 6 Exigences Fonctionnelles | `FR-\d+` in table ID column | Functional Requirement |
| Section 7 Acceptance Criteria | `AC-\d+` in table ID column | Acceptance Criteria |
| Section 11 NFR | `NFR-\d+` in table ID column | Non-Functional Requirement |
| Section 13 Points Ouverts | `OP-\d+` in table ID column | Open Point |

**Knowledge Artifact resolution per identifier type:**

| ID Type | Knowledge Artifact | Knowledge Section |
|---|---|---|
| BR-NNN | source_artifact_path (KB) | `# Business Rules` |
| TR-NNN | source_artifact_path (KB) | `# Technical Rules` |
| FR-NNN | source_artifact_path (KB) | `# Business Rules` (via BR source in R4 chain) |
| AC-NNN | source_artifact_path (KB) | `# Business Rules` (via FR→BR chain) |
| NFR-NNN | source_artifact_path (KB) | `# Constraints` (via C source in R4 chain) |
| OP-NNN | `—` | `—` (open point; no KB backing) |

**Provenance column for STD identifiers:**

| ID Type | Provenance value |
|---|---|
| BR-NNN | From `provenance_map[BR-NNN].type` (same as LEGACY) |
| TR-NNN | From `provenance_map[TR-NNN].type` |
| FR-NNN | From `fr_items[FR-NNN].kpm_type` (R4-derived) |
| AC-NNN | From `ac_items[AC-NNN].kpm_type` (R4-derived) |
| NFR-NNN | From `nfr_items[NFR-NNN].kpm_type` (R4-derived) |
| OP-NNN | `—` |

**Row order:** BR-NNN ascending, TR-NNN ascending, FR-NNN ascending, AC-NNN ascending, NFR-NNN ascending, OP-NNN ascending.

**Output path:** `WORKSPACE_ROOT/specifications/draft/<base>_traceability.md` (same as LEGACY).

**Header block:**

```markdown
# Traceability Matrix — <base>

**Base:** <base>
**Specification:** specifications/draft/<base>_specification.md
**Knowledge Artifact:** knowledge_base/extracted/<base>_knowledge.md
**Generated:** <ISO 8601 date>
**Generated by:** /generate-specification
**KPM Status:** <kpm_status>
**Template:** STD v1
```

Remaining columns (`ID`, `Type`, `Provenance`, `Knowledge Section`, `Knowledge Artifact`, `Source Document`) use the same column format as the LEGACY matrix.

---

### V2 Traceability Matrix (V2 mode only)

When `spec_mode = V2`, the traceability matrix covers both inherited v1 rules and new v2 rules.

**Output path:**

```text
WORKSPACE_ROOT/specifications/draft/<inherited_base>_traceability_v2.md
```

**V2 matrix format:**

```markdown
# Traceability Matrix v2 — <inherited_base>

**Base:** <inherited_base>
**Specification v1 (inherited):** specifications/stable/<inherited_base>_specification.md
**Specification v2 (draft):** specifications/draft/<inherited_base>_specification_v2.md
**Knowledge Artifact (v2):** knowledge_base/extracted/<v2_base>_knowledge.md
**Generated:** <ISO 8601 date>
**Generated by:** /generate-specification

| ID | Type | version_introduced | version_updated | Knowledge Section | Source Document | Status |
|----|------|--------------------|-----------------|-------------------|-----------------|--------|
| BR-001 | Business Rule | v1 | — | # Business Rules | input/... | active |
| BR-005 | Business Rule | v1 | v2 | # Business Rules | input/... | v2-modified |
| BR-013 | Business Rule | v1 | — | # Business Rules | input/... | DEPRECATED |
| BR-016 | Business Rule | v2 | — | # Business Rules | input/... | active |
```

Column `version_updated`:
- `—` for unchanged v1 rules and v2-added rules
- `v2` for v2-modified rules

Column `Status`:
- `active` for all rules not deprecated
- `DEPRECATED` for rules with `[DEPRECATED in v2]`
- `v2-modified` for rules with `[v2-modified]`

### Output

```text
V1 mode: WORKSPACE_ROOT/specifications/draft/<base>_traceability.md
V2 mode: WORKSPACE_ROOT/specifications/draft/<inherited_base>_traceability_v2.md
```

**STATUS: TRACEABILITY MATRIX GENERATION COMPLETE**

---

## Phase 8.7 — SQF Q-GATE-1 (D1 + D3 + D5 + D6)

### Objective

Evaluate quality dimensions D1 (Complétude), D3 (Traçabilité), D5 (Testabilité), and D6 (Couverture Métier) for each candidate that reached Phase 7 successfully. Write `sqf_gate_report.md`. If any candidate produces a BLOCK result on D1 or D3, stop before Phase 9 and declare QUALITY BLOCKED. D5 and D6 are informative only — they produce PASS, WARN, or NOT_APPLICABLE, but never BLOCK.

This phase runs after Phase 8.5 (traceability matrix written). D7 (Gouvernance des Inférences) is **evaluated** by the `/specification-lifecycle` E6 extension at BASELINE time; since 2026-11-01 this phase additionally produces a non-binding **advisory reading** of D7 (Step 8.7.9, R11) so that a specification which stays in draft is not left without any D7 signal at all.

**Inputs required (already available in memory or on disk):**
- Knowledge artifact section data (from SourceDataModel, Phase 4)
- Draft specification (written in Phase 7)
- Traceability matrix (written in Phase 8.5)

### Step 8.7.0 — Scope

Phase 8.7 runs per-candidate, for every candidate that completed Phase 7 (Step 7.3) without a write failure. Candidates that failed in Phase 7 are excluded.

When multiple candidates are processed in a single run, Phase 8.7 runs sequentially for each. The `sqf_gate_report.md` workspace file is written once per candidate (overwritten). The final file on disk reflects the last processed candidate. The gate decision is made across all candidates after all have been evaluated.

### Step 8.7.1 — Precondition Check (SQF PQ1–PQ4)

For each candidate, verify before computing indicators:

| ID | Condition | On Failure |
|----|-----------|------------|
| PQ1 | `specifications/draft/<base>_specification.md` exists and is readable | ABORT for this candidate — record `SQF PQ1 FAIL`; mark QUALITY_BLOCKED in specifications_report.md |
| PQ2 | `specifications/draft/<base>_traceability.md` exists and is readable | D3 = L0 BLOCK (I3.1 = `MATRIX_ABSENT`, forced BLOCK); D1 can still be computed |
| PQ3 | Knowledge artifact readable (from SourceDataModel — availability of BR/TR/C count) | I1.1 = `N/A` (WARN, non-blocking for D1); I1.2 and I1.3 unaffected |
| PQ4 | `specifications/draft/` is writeable (verified by Phase 7 success — assume writeable) | ABORT — gate report cannot be written; stop for this candidate |

### Step 8.7.2 — D1 Indicator I1.1 — Taux KB→Spec

**Source:** SourceDataModel (Phase 4) already holds the knowledge artifact sections. Re-use the in-memory data; do not re-read from disk.

**count_kb computation:**

Scan the knowledge artifact's section content for identifier patterns:
- In `# Business Rules` section: count lines matching `**BR-\d+**:` (bold ID with colon). Each match = 1 item.
- In `# Technical Rules` section: count lines matching `**TR-\d+**:`. Each match = 1 item.
- In `# Constraints` section: count lines matching `**C-\d+**:`. Each match = 1 item.
- `count_kb = sum of the three counts`

If any section is absent from the knowledge artifact: its count is 0 (does not fail the check).

**count_traced computation — LEGACY mode (`template_mode = LEGACY`):**

Read the traceability matrix at `WORKSPACE_ROOT/specifications/draft/<base>_traceability.md` (already written in Phase 8.5):
- Locate the `Knowledge Artifact` column header (case-insensitive match).
- Count data rows where the `Knowledge Artifact` cell value is non-empty AND the value is not `—`.
- `count_traced = count of qualifying rows`

If the `Knowledge Artifact` column is absent: set `count_traced = 0`.

**count_traced computation — STD mode (`template_mode = STD`):**

Read the STD traceability matrix at `WORKSPACE_ROOT/specifications/draft/<base>_traceability.md`:
- Locate the `Type` column and `Knowledge Artifact` column (case-insensitive matches).
- Count data rows where BOTH: `Type ∈ { Business Rule, Technical Rule, Functional Requirement, Non-Functional Requirement }` AND `Knowledge Artifact` cell is non-empty AND not `—`.
- `count_traced = count of qualifying rows`

Rationale: FR-NNN represents BR-NNN items (derived via DK), NFR-NNN represents C-NNN items. TR-NNN appears directly. AC-NNN and OP-NNN are excluded from count_traced (AC is derived from FR, OP has no KB backing). This ensures count_traced / count_kb reaches 100% when all KB items are represented in the STD spec.

If the `Knowledge Artifact` column is absent: set `count_traced = 0`.

**I1.1 computation:**

```
if PQ3 failed:
  I1.1_value = "N/A"
  I1.1_status = "WARN"
  I1.1_level  = L2
elif count_kb == 0:
  I1.1_value = "N/A (0 KB items found)"
  I1.1_status = "WARN"
  I1.1_level  = L2
else:
  pct = count_traced / count_kb
  I1.1_value = f"{count_traced}/{count_kb} = {pct:.0%}"

  if pct >= 0.90:
    I1.1_status = "PASS"
    I1.1_level  = L3
  elif pct >= 0.75:
    I1.1_status = "WARN"
    I1.1_level  = L2
  elif pct >= 0.60:
    I1.1_status = "BLOCK"
    I1.1_level  = L1
  else:
    I1.1_status = "BLOCK"
    I1.1_level  = L0
```

### Step 8.7.3 — D1 Indicator I1.2 — Table hors-périmètre

Read the draft specification from disk at `WORKSPACE_ROOT/specifications/draft/<base>_specification.md`.

For STD mode (`template_mode = STD`), the hors-périmètre section is `## Section 12 — Hors Périmètre`. For LEGACY mode, it matches heading patterns. Both modes use the same search-and-count logic below (the heading pattern list covers both).

```
headings_found = search_headings(spec_content,
  patterns=["Section 12", "Out of scope", "Hors-périmètre", "Hors périmètre", "Hors Périmètre"],
  case_insensitive=True)

if not headings_found:
  I1.2_value  = "ABSENT"
  I1.2_status = "BLOCK"
  I1.2_level  = L1
  note: "Section hors-périmètre absente — ajouter une section 'Out of scope' ou 'Hors-périmètre' avec au moins un élément justifié."
else:
  heading_pos = headings_found[0]
  section_content = extract_until_next_heading(spec_content, heading_pos)

  // Count entries: table data rows OR list items
  table_data_rows = count_markdown_table_data_rows(section_content)
  list_items      = count_list_items(section_content)
  has_entries     = (table_data_rows + list_items) > 0

  if has_entries:
    I1.2_value  = "PRESENT_WITH_ENTRIES"
    I1.2_status = "PASS"
    I1.2_level  = L3
  else:
    I1.2_value  = "PRESENT_EMPTY"
    I1.2_status = "WARN"
    I1.2_level  = L2
    note: "Section hors-périmètre présente mais vide — ajouter au moins un élément justifié."
```

**count_markdown_table_data_rows:** count lines matching `| ... |` that are NOT the header separator (`|---|`).
**count_list_items:** count lines starting with `- ` or `* ` or matching `^\d+\. `.

### Step 8.7.4 — D1 Indicator I1.3 — Points ouverts résolus

Search the draft specification (already read in Step 8.7.3):

For STD mode (`template_mode = STD`), the open points section is `## Section 13 — Points Ouverts` with OP-NNN table rows. For LEGACY mode, heading pattern matching applies. Both modes use the same heading search and unresolved-row detection logic; the STD `Section 13` heading is included in the pattern list.

```
op_heading = find_heading(spec_content,
  patterns=["Section 13", "Open points", "Points ouverts", "Points Ouverts"],
  case_insensitive=True)

if not op_heading:
  I1.3_value  = "NO_SECTION"
  I1.3_status = "PASS"
  I1.3_level  = L3
else:
  section_content = extract_until_next_heading(spec_content, op_heading)
  data_rows       = open_point_rows(section_content)

  if count(data_rows) == 0:
    // Section present but carrying no point. Only here may a closure statement
    // be consulted, and only to confirm what the absence of rows already says.
    I1.3_value  = "ALL_RESOLVED"
    I1.3_status = "PASS"
    I1.3_level  = L3
  else:
    open_rows     = [r for r in data_rows if status_of(r) in OPEN_STATUS]
    deferred_rows = [r for r in data_rows if status_of(r) in DEFERRED_STATUS]

    if count(open_rows) == 0 and count(deferred_rows) == 0:
      I1.3_value  = "ALL_RESOLVED"
      I1.3_status = "PASS"
      I1.3_level  = L3
    elif count(open_rows) == 0:
      I1.3_value  = "DEFERRED"
      I1.3_status = "WARN"
      I1.3_level  = L2
      note: f"{count(deferred_rows)} point(s) explicitement déféré(s) — BASELINE possible mais réserve enregistrée."
    else:
      justified = [r for r in open_rows if has_deferral_justification(r)]
      if count(justified) == count(open_rows):
        I1.3_value  = "DEFERRED"
        I1.3_status = "WARN"
        I1.3_level  = L2
        note: f"{count(open_rows)} point(s) ouvert(s) avec justification de report — réserve enregistrée."
      else:
        unresolved_count = count(open_rows) - count(justified)
        I1.3_value  = "UNRESOLVED"
        I1.3_status = "BLOCK"
        I1.3_level  = L1
        note: f"{unresolved_count} point(s) ouvert(s) ni résolu(s) ni déféré(s) — résoudre ou déférer explicitement avant BASELINE."
```

**`open_point_rows(section)`** returns the table data rows whose first cell matches `OP-<NNN>` — never the header row, never the separator, never surrounding prose.

**`status_of(row)`** reads the cell under the column headed `Status` or `Statut`. **If the table has no such column, I1.3 is `UNRESOLVED → BLOCK`**: a table of open points with no status column is not evaluable, and the non-evaluable does not pass a quality gate.

**Status vocabulary** — identical to `docs/implementation/SQF-Implementation-Contract.md` § 3.3, which is the authority:

```
OPEN_STATUS     = OPEN, OUVERT, PENDING, PENDING_VALIDATION, UNRESOLVED, NON_RESOLU, IN_PROGRESS, EN_COURS
CLOSED_STATUS   = RESOLVED, RESOLU, CLOSED, CLOS, INTEGRATED, INTEGRE
DEFERRED_STATUS = DEFERRED, DIFFERE, REPORTE
```

A status value outside all three lists is treated as **open**, and the unrecognised value is named in the gate report. A status the contract does not know cannot be presumed favourable.

**`has_deferral_justification(row)`** is true only when the row carries an explicit postponement — `deferred to`, `différé à`, `reporté à`, `postponed to` — naming a milestone, a version or a date.

**What does not count as resolution.** The `Expected Resolution` / `Résolution attendue` column describes *how the point is to be resolved*: it is a plan, not an outcome. A row at `Status = OPEN` carrying a detailed resolution plan is open. A closure sentence in the section body is consulted only when the table holds no rows; where rows exist, the table is authoritative and a contradicting sentence is simply false.

If the Open Points section uses a flat list rather than a table: treat any item without an explicit closed or deferred status marker as open.

> **Correction recorded 2026-10-30.** The previous algorithm tested the closure sentence **before** reading any row, and its `find_unresolved_rows` helper excluded every row that "contains a concrete decision text (a non-trivial sentence in the decision column)". A correctly filled Section 13 has prose in every row, so a table of entirely open points produced `count(pending_rows) == 0` and therefore `ALL_RESOLVED → PASS`. Both paths reached PASS on a section holding three `OPEN` rows, one of them BLOCKING, and SP001 and SP003 of `demo-inventory-01` were baselined on that verdict. The term *decision text* is removed; the `Status` column is now the sole authority. See finding F-02 of (internal review note), validation rule SG21 of Phase 9, and check `W2` of `tools/csr-check`.
>
> This block duplicated the algorithm of `SQF-Implementation-Contract.md` § 3.3 rather than referencing it, which is why the defect had to be fixed in two places. Keep the two in step, or collapse one into a reference to the other.

### Step 8.7.5 — D1 Composite Score

```
// Severity ranking: BLOCK > WARN > PASS
statuses = [I1.1_status, I1.2_status, I1.3_status]
levels   = [I1.1_level,  I1.2_level,  I1.3_level ]

if "BLOCK" in statuses:
  D1_status = "BLOCK"
elif "WARN" in statuses:
  D1_status = "WARN"
else:
  D1_status = "PASS"

D1_score = min(levels)  // min(Ln) = worst level
```

### Step 8.7.6 — D3 Indicator I3.1 — Taux traçabilité table

Read the traceability matrix (already read in Step 8.7.2; re-use in-memory representation).

```
if PQ2 failed:
  I3.1_value  = "MATRIX_ABSENT"
  I3.1_status = "BLOCK"
  I3.1_level  = L0
  // D3 already BLOCK — still compute I3.3 for documentation
else:
  col_ka = find_column_header(matrix, "Knowledge Artifact", case_insensitive=True)

  if col_ka not found:
    I3.1_value  = "0% (column absent)"
    I3.1_status = "BLOCK"
    I3.1_level  = L0
  else:
    total_rows  = count_data_rows(matrix)
    if total_rows == 0:
      I3.1_value  = "EMPTY_MATRIX (0 rows)"
      I3.1_status = "BLOCK"
      I3.1_level  = L0
    else:
      // R8: an OP-NNN row has no Knowledge Artifact by construction — that is
      // what makes it an open point. Excluding it from the denominator stops the
      // indicator from penalising the honest reporting of a gap.
      op_rows      = count_rows_where_id_matches(matrix, "^OP-\d+$")
      scored_rows  = total_rows - op_rows
      if scored_rows == 0:
        I3.1_value  = f"NO_SCORABLE_ROW ({op_rows} open point(s) only)"
        I3.1_status = "WARN"
        I3.1_level  = L2
        skip to I3.3
      traced_rows = count_rows_where_cell_non_empty_and_not_dash(matrix, col_ka)
                    excluding OP-NNN rows
      pct = traced_rows / scored_rows
      I3.1_value  = f"{traced_rows}/{scored_rows} = {pct:.0%} ({op_rows} OP-NNN excluded)"

      if pct >= 0.95:
        I3.1_status = "PASS"
        I3.1_level  = (L4 if pct == 1.0 else L3)
      elif pct >= 0.80:
        I3.1_status = "WARN"
        I3.1_level  = L2
      else:
        I3.1_status = "BLOCK"
        I3.1_level  = (L1 if traced_rows > 0 else L0)
```

**OP-NNN rows are excluded from both D3 denominators (R8, 2026-11-01).**

An `OP-NNN` row exists *because* something is unresolved, undefined or awaiting a decision. By construction it has no Knowledge Artifact and no Provenance entry — there is no settled knowledge to point at; that is what makes it an open point. Counting it as an untraced row makes I3.1 and I3.3 penalise the honest reporting of a gap, and rewards a specification that stays silent about what it does not know.

This was not theoretical. On `demo-inventory-01`, the OP-NNN rows **alone** produced the WARN recorded in lifecycle events EV001 and EV002:

| Base | With OP rows | Without |
|---|---|---|
| `cdc_demo-inventory` | 51/54 = 94% → **WARN** | 51/51 = 100% → PASS |
| `demo-inventory-mockup_transcript` | 21/24 = 88% → **WARN** | 21/21 = 100% → PASS |

Every other untraced row in the repository is a genuine traceability gap and still counts.

**Excluded, not hidden.** The count is reported alongside the indicator so an open point never becomes invisible by being discounted — Section 13 remains the place where it is answered for, and `csr-check` W4 still blocks a BLOCKING open point in a baselined spec.

### Step 8.7.7 — D3 Indicator I3.3 — Couverture Provenance Index

```
// kpm_status from SourceDataModel (Phase 4.2b) — no re-read required
kpm_status = source_data_model.kpm_status

col_prov = find_column_header(matrix, "Provenance", case_insensitive=True)

if kpm_status == "NO_PROVENANCE_INDEX" OR col_prov not found:
  // T-MODE: always WARN, never BLOCK
  I3.3_value  = "T_MODE"
  I3.3_status = "WARN"
  I3.3_level  = L2
else:
  // PROVENANCE_INDEXED mode
  // R8: same exclusion as I3.1 — an open point has no provenance to index.
  total_rows   = count_data_rows(matrix) - count_rows_where_id_matches(matrix, "^OP-\d+$")
  indexed_rows = count_rows_where_cell_non_empty_and_not_dash(matrix, col_prov)
  pct = indexed_rows / total_rows if total_rows > 0 else 0

  I3.3_value = f"{indexed_rows}/{total_rows} = {pct:.0%}"

  if pct >= 0.90:
    I3.3_status = "PASS"
    I3.3_level  = L3
  elif pct >= 0.75:
    I3.3_status = "WARN"
    I3.3_level  = L2
  else:
    I3.3_status = "BLOCK"
    I3.3_level  = L1
```

**T-MODE cap rule:** I3.3 in T-MODE (`kpm_status = NO_PROVENANCE_INDEX` or `Provenance` column absent) is always WARN. It must never produce BLOCK, regardless of coverage percentage.

### Step 8.7.8 — D3 Composite Score

```
statuses = [I3.1_status, I3.3_status]
levels   = [I3.1_level,  I3.3_level ]

// I3.3 in T-MODE is WARN, which is already captured above.
// I3.3 can never cause BLOCK (T-MODE cap enforced in Step 8.7.7).

if "BLOCK" in statuses:
  D3_status = "BLOCK"
elif "WARN" in statuses:
  D3_status = "WARN"
else:
  D3_status = "PASS"

D3_score = min(levels)
```

### Step 8.7.8b — D5 Indicator I5.1 — Taux FR couverts par AC (Testabilité)

**INFORMATIVE ONLY — statuts autorisés : PASS, WARN, NOT_APPLICABLE. BLOCK interdit.**

```
if template_mode == "LEGACY":
  I5.1_value  = "NOT_APPLICABLE (LEGACY mode — Section 7 AC absent)"
  I5.1_status = "NOT_APPLICABLE"
  D5_status   = "NOT_APPLICABLE"
else:
  // STD mode: read Section 6 and Section 7 from spec already in memory (Phase 6-STD)
  fr_ids = collect(FR-NNN from Section 6 table, ID column)
  fr_total = count(fr_ids)

  section_7_present = spec contains heading "## Section 7" or "Section 7 — Acceptance Criteria"
  ac_fr_covered = collect(distinct FR-NNN values from "FR Couvert" column of Section 7 AC table)

  // ADR-007: the "Preuve" column is NOT an input to D5 and must never become one.
  // D5 measures testability — whether each FR has a criterion able to settle it.
  // Whether that criterion has yet been executed is a fact about the project's
  // progress, not about the specification's quality. Penalising NON_DEMONTRE would
  // make every freshly generated specification score badly for being new, and would
  // reward deleting criteria over writing them.
  // Read the column by NAME, never by position: Section 7 now carries 8 columns.

  if fr_total == 0 OR NOT section_7_present:
    I5.1_value  = "NOT_APPLICABLE (0 FR or Section 7 absent)"
    I5.1_status = "NOT_APPLICABLE"
    D5_status   = "NOT_APPLICABLE"
  else:
    fr_covered_count = count(fr_id for fr_id in fr_ids if fr_id IN ac_fr_covered)
    pct = fr_covered_count / fr_total
    I5.1_value = f"{fr_covered_count}/{fr_total} = {pct:.0%}"

    if pct >= 0.80:
      I5.1_status = "PASS"
      D5_status   = "PASS"
    else:
      I5.1_status = "WARN"
      D5_status   = "WARN"
      D5_uncovered = [fr_id for fr_id in fr_ids if fr_id NOT IN ac_fr_covered]
      D5_note = f"{fr_total - fr_covered_count} FR sans AC : {D5_uncovered}"

// Threshold rationale: PASS ≥ 80%, WARN < 80%. Bootstrapped at N=2 gate reports.
// Recalibration required at B8-v2 (N ≥ 5 gate reports).
// D5 = NOT_APPLICABLE is neutral — excluded from gate_status computation.
```

### Step 8.7.8c — D6 Indicator I6.1 — Taux BR couverts par FR (Couverture Métier)

**INFORMATIVE ONLY — statuts autorisés : PASS, WARN, NOT_APPLICABLE. BLOCK interdit.**
**Scope : BR-NNN uniquement. TR-NNN exclus du numérateur ET du dénominateur.**

```
if template_mode == "LEGACY":
  I6.1_value  = "NOT_APPLICABLE (LEGACY mode — BR Source column absent)"
  I6.1_status = "NOT_APPLICABLE"
  D6_status   = "NOT_APPLICABLE"
else:
  // STD mode: read Section 5.1 and Section 6 from spec in memory (Phase 6-STD)
  br_ids = collect(BR-NNN from Section 5.1 table, ID column)  // TR-NNN excluded
  br_total = count(br_ids)

  br_source_col_present = Section 6 FR table contains column header "BR Source"
  fr_br_sources = collect(distinct BR-NNN values from "BR Source" column of Section 6 FR table)

  if br_total == 0 OR NOT br_source_col_present:
    I6.1_value  = "NOT_APPLICABLE (0 BR or BR Source column absent)"
    I6.1_status = "NOT_APPLICABLE"
    D6_status   = "NOT_APPLICABLE"
  else:
    br_covered_count = count(br_id for br_id in br_ids if br_id IN fr_br_sources)
    pct = br_covered_count / br_total
    I6.1_value = f"{br_covered_count}/{br_total} = {pct:.0%}"

    if pct >= 0.70:
      I6.1_status = "PASS"
      D6_status   = "PASS"
    else:
      I6.1_status = "WARN"
      D6_status   = "WARN"
      D6_uncovered = [br_id for br_id in br_ids if br_id NOT IN fr_br_sources]
      D6_note = f"{br_total - br_covered_count} BR sans FR : {D6_uncovered}"

// Threshold rationale: PASS ≥ 70%, WARN < 70%. Bootstrapped at N=2 gate reports.
// Recalibration required at B8-v2 (N ≥ 5 gate reports).
// PENDING_VALIDATION BRs with no FR projection count as uncovered — intentional coverage signal.
// D6 = NOT_APPLICABLE is neutral — excluded from gate_status computation.
```


### Step 8.7.9 — D7 Advisory Reading `[R11, 2026-11-01]`

**D7 is evaluated at BASELINE by the E6 extension, and that remains the authoritative evaluation.** This step adds an *advisory* reading at generation time. It changes no gate and blocks nothing.

**Why it is needed.** Both D7 indicators read the Inference Registry, which `/generate-specification` itself writes in Step 6.5b. The data has always been available here; only the decision to evaluate at BASELINE made D7 absent. The consequence is an observability blind spot: a specification that stays in draft — which is the normal state of most specifications, most of the time — never receives a D7 verdict at all, **even when that verdict would be BLOCK**. The report says `PENDING_D7`, which a reader takes to mean *not yet assessed* rather than *would not pass*.

```
// Same inputs as the E6 extension — see templates/sqf_gate_report_template.md
if kpm_status == "NO_PROVENANCE_INDEX":
  D7_advisory = "T_MODE (WARN)"
else:
  structural_pending = count(rows in "### INFERRED_DESIGN — Impact Structurel"
                             where Statut == "PENDING_VALIDATION")
  D7_advisory = "BLOCK" if structural_pending > 0 else "PASS"

I7.3_advisory = validated_ir_entries / total_ir_entries   // 100% if total = 0
```

**It must not block, and must not be mistaken for the gate.**

- A draft holding unvalidated structural inferences is **correct**, not defective. That is what a draft is for, and `PENDING_VALIDATION` is the state ADR-004 created to hold them. Blocking generation on it would make it impossible to produce the very artifact in which those inferences are recorded for validation.
- The global `gate_status` stays `PENDING_D7`. The advisory value is reported *beside* it, never substituted for it: `PENDING_D7 (D7 advisory: BLOCK — 7 structural element(s) PENDING_VALIDATION)`.
- E6 recomputes from scratch at BASELINE. An advisory reading taken days earlier is evidence of nothing: elements get validated, and a `BLOCK` advisory routinely becomes a `PASS` gate without anything being wrong.

**What it buys.** A reader of a draft gate report can see, without running a BASELINE, exactly what would stop one — and which elements to take to a validation session.

### Step 8.7.9 — Determine Initial Gate Status

```
// D5 and D6 are informative. NOT_APPLICABLE is neutral (excluded from gate_status computation).
// D5/D6 can contribute WARN but never BLOCK.
informative_warn = ("WARN" in [D5_status, D6_status])

if D1_status == "BLOCK" OR D3_status == "BLOCK":
  initial_gate_status = "BLOCK"
elif D1_status == "WARN" OR D3_status == "WARN" OR informative_warn:
  initial_gate_status = "WARN"
else:
  // D1 = PASS, D3 = PASS, D5/D6 = PASS or NOT_APPLICABLE — D7 not yet evaluated
  initial_gate_status = "PENDING_D7"
```

`PENDING_D7` is the correct status when D1 and D3 both PASS and D5/D6 are PASS or NOT_APPLICABLE: the global gate cannot be PASS until D7 is evaluated at BASELINE time by the E6 extension.

### Step 8.7.10 — Write sqf_gate_report.md

Write `WORKSPACE_ROOT/specifications/draft/sqf_gate_report.md` using the template at `templates/sqf_gate_report_template.md` as the structural reference.

**Canonical content:**

```markdown
# SQF Gate Report

**workspace_id:** <workspace_id>
**spec_base:** <base>
**spec_draft:** specifications/draft/<base>_specification.md
**generated:** <ISO 8601 date of this execution>
**sqf_phase:** Q-GATE-1
**sqf_version:** 1.0
**gate_status:** <initial_gate_status>

---

## D1 — Complétude

| Indicateur | Valeur | Seuil | Statut |
|---|---|---|---|
| I1.1 Taux KB→Spec | <I1.1_value> | ≥ 90% PASS / 75–89% WARN / < 75% BLOCK | <I1.1_status> |
| I1.2 Table hors-périmètre | <I1.2_value> | PRESENT_WITH_ENTRIES=PASS | <I1.2_status> |
| I1.3 Points ouverts | <I1.3_value> | ALL_RESOLVED=PASS | <I1.3_status> |

**Score D1 :** L<D1_score>
**D1 Gate Status :** <D1_status>

<If D1_status = WARN or BLOCK: write each indicator's note from Steps 8.7.2–8.7.4>

---

## D3 — Traçabilité

| Indicateur | Valeur | Seuil | Statut |
|---|---|---|---|
| I3.1 Taux traçabilité table | <I3.1_value> | ≥ 95% PASS / 80–94% WARN / < 80% BLOCK | <I3.1_status> |
| I3.3 Couverture Provenance Index | <I3.3_value> | ≥ 90% PASS / 75–89% WARN / < 75% BLOCK | <I3.3_status> |
| KPM Status | <kpm_status> | — | — |

**Score D3 :** L<D3_score>
**D3 Gate Status :** <D3_status>

<If D3_status = WARN or BLOCK: write issue details>

---

## D5 — Testabilité

*[Informatif uniquement — BLOCK interdit. NOT_APPLICABLE si LEGACY mode.]*

| Indicateur | Valeur | Seuil | Statut |
|---|---|---|---|
| I5.1 Taux FR couverts par AC | <I5.1_value> | ≥ 80% PASS / < 80% WARN / STD absent NOT_APPLICABLE | <I5.1_status> |

**D5 Gate Status :** <D5_status>

<If D5_status = WARN: list FR IDs from D5_uncovered without AC coverage>

---

## D6 — Couverture Métier

*[Informatif uniquement — BLOCK interdit. NOT_APPLICABLE si LEGACY mode. Scope : BR-NNN uniquement.]*

| Indicateur | Valeur | Seuil | Statut |
|---|---|---|---|
| I6.1 Taux BR couverts par FR | <I6.1_value> | ≥ 70% PASS / < 70% WARN / STD absent NOT_APPLICABLE | <I6.1_status> |

**D6 Gate Status :** <D6_status>

<If D6_status = WARN: list BR IDs from D6_uncovered without FR coverage>

---

## D7 — Gouvernance des Inférences

*[Section ajoutée par E6 gate étendu lors du BASELINE check — /specification-lifecycle]*

---

## Verdict Global

**D1 :** <D1_status>  **D3 :** <D3_status>  **D5 :** <D5_status>  **D6 :** <D6_status>  **D7 :** PENDING — lecture indicative : <D7_advisory> (R11)

**Gate Status Global :** <initial_gate_status>
**Décision BASELINE :** <decision>

<decision mapping:>
  PENDING_D7 → EN ATTENTE D7 (exécuter /specification-lifecycle BASELINE) — afficher la lecture indicative à côté : PENDING_D7 (D7 advisory: <value>)
  WARN       → AUTORISÉ AVEC RÉSERVES (réserves : <list WARN dimensions — D1/D3/D5/D6>)
  BLOCK      → REFUSÉ (D1 ou D3 seulement — D5/D6 ne peuvent pas BLOCK)

<If BLOCK: write action list — one item per blocking indicator>
```

**Action list format (BLOCK only):**

For each indicator that produced BLOCK:

```
Actions requises :
1. <D1 or D3 indicator> BLOCK : <specific corrective action from the indicator's note>
2. ...
Relancer /generate-specification après correction pour régénérer le rapport.
```

**Write ordering:** Write sqf_gate_report.md before updating specifications_report.md.

**On write failure:** Record `SQF GATE REPORT WRITE FAILURE` for this candidate. Mark the candidate as QUALITY_BLOCKED in specifications_report.md (cannot confirm quality; conservatively block). Continue with remaining candidates.

### Step 8.7.11 — Update specifications_report.md

Open `WORKSPACE_ROOT/specifications/draft/specifications_report.md` (already written in Phase 8). Locate the `### SP<NNN>` block for this `<base>`. Append the SQF Gate line:

```markdown
**SQF Gate:** <initial_gate_status> — D1=<D1_status> D3=<D3_status> D5=<D5_status> D6=<D6_status> D7=PENDING(advisory=<D7_advisory>)
```

If `initial_gate_status = BLOCK`, additionally update the `**Status:**` field in this record:

```markdown
**Status:** QUALITY_BLOCKED
```

The `**Status:**` field previously read `GENERATED`. After Phase 8.7, a BLOCK candidate's status is `QUALITY_BLOCKED`.

**Write ordering:** Update specifications_report.md after writing sqf_gate_report.md.

### Step 8.7.12 — Gate Decision (Post All-Candidate Processing)

After Phase 8.7 has run for every candidate:

```
blocked_candidates = [c for c in processed_candidates where initial_gate_status[c] == "BLOCK"]

if blocked_candidates:
  // QUALITY BLOCKED path
  for each c in blocked_candidates:
    report:
      "──────────────────────────────────────────"
      "SQF Q-GATE-1 BLOCK — <c.base>"
      "  D1: <D1_status[c]>  D3: <D3_status[c]>  D5: <D5_status[c]>  D6: <D6_status[c]>"
      "  Gate report: specifications/draft/sqf_gate_report.md"
      "  See sqf_gate_report.md Verdict section for required actions."
      "──────────────────────────────────────────"

  // Do NOT proceed to Phase 9 (Post-Execution Validation SG1–SG18)
  goto Phase 11 → QUALITY BLOCKED completion state

else:
  // PASS or WARN — proceed normally
  for each c in processed_candidates:
    if initial_gate_status[c] == "WARN":
      report: "SQF Q-GATE-1 WARN — <c.base> — D1=<D1_status> D3=<D3_status> D5=<D5_status> D6=<D6_status> — BASELINE authorized with reservations"
    else:
      report: "SQF Q-GATE-1 PENDING_D7 — <c.base> — D1=PASS D3=PASS D5=<D5_status> D6=<D6_status> — awaiting D7 at BASELINE"

  proceed to Phase 9 (Post-Execution Validation SG1–SG20)
```

**STATUS: SQF Q-GATE-1 COMPLETE**

---

## Phase 9 — Post-Execution Validation

### Objective

Verify that all generated artifacts meet correctness and traceability requirements before reporting the completion state.

### Validation Rules

Evaluate all rules SG1–SG20. For each failed rule: record the rule ID, the affected artifact path, and the specific violation. Classify as BLOCKING or WARNING.

**Phase 9 entry condition:** Phase 9 is reached only when Phase 8.7.12 determined that no candidate produced a BLOCK gate status. If Phase 8.7.12 redirected to QUALITY BLOCKED, Phase 9 does not run.

BLOCKING failures prevent declaring SPECIFICATION COMPLETE.

| Rule | Description | Classification |
| ---- | ----------- | -------------- |
| SG1 | Every specification in `specifications_report.md` with status GENERATED has a corresponding file at the declared Specification Artifact path that exists and is readable. | BLOCKING |
| SG2 | **LEGACY mode:** Every generated specification file has a Markdown bold header block containing all seven required fields (`Source Artifact`, `Source Type`, `Generated`, `Generation Command`, `Conflicts Incorporated`, `Questions Incorporated`, `KPM Status`) with non-empty values. **STD mode (`template_mode = STD`):** Every generated STD specification file has (a) a YAML frontmatter block with all 8 required fields (`spec_id`, `title`, `workspace_id`, `version`, `status`, `baseline_date`, `language`, `template_version`) and (b) a generation metadata block (immediately after YAML `---`) with all seven metadata fields (`Source Artifact`, `Source Type`, `Generated`, `Generation Command`, `Conflicts Incorporated`, `Questions Incorporated`, `KPM Status`) with non-empty values. | BLOCKING |
| SG3 | `Conflicts Incorporated` in each CONSOLIDATED-type spec matches the `**Conflicts Resolved:**` header field of the source consolidated artifact. For EXTRACTED-type specs, `Conflicts Incorporated` is `none`. | BLOCKING |
| SG4 | `Questions Incorporated` in each CONSOLIDATED-type spec matches the union of `question_id` values from the `## Resolved Conflicts` table of the source consolidated artifact. For EXTRACTED-type specs, `Questions Incorporated` is `none`. | BLOCKING |
| SG5 | All write operations targeted paths within `WORKSPACE_ROOT/specifications/draft/`. No artifact was written outside this path. | BLOCKING |
| SG6 | `specifications_report.md` exists and is readable at `WORKSPACE_ROOT/specifications/draft/specifications_report.md`. | BLOCKING |
| SG7 | All source consolidated artifacts read during this execution are readable and contain the same `**Source Artifact:**`, `**Consolidated Date:**`, and `**Conflicts Resolved:**` header field values as recorded at load time in Phase 4. | WARNING |
| SG8 | All source extracted artifacts read during this execution are readable and contain the same section structure as recorded at load time in Phase 4. | WARNING |
| SG9 | `consolidation_report.md` is readable and its `## Metadata` section is unchanged from the state recorded at load time in Phase 2. | WARNING |
| SG10 | **LEGACY mode:** Every generated specification file has `**Status:** DRAFT` in its Markdown header block. **STD mode:** Every generated STD specification file has `status: DRAFT` in its YAML frontmatter. | BLOCKING |
| SG11 | Resolution notes in CONSOLIDATED-type specifications are present and match the inline resolution notes from the corresponding section of the source consolidated artifact. No note is missing, paraphrased, or summarized. | BLOCKING |
| SG12 | `specifications_report.md` `Last Updated` field matches the ISO 8601 date of this execution. | BLOCKING |
| SG13 | For each CONSOLIDATED-type specification generated when the Conflicts Index was non-empty: every ADVISORY conflict whose ownership includes this source, that is NOT CONSOLIDATED in `consolidation_report.md`, has an inline `[ADVISORY UNRESOLVED: <conflict_id> — awaiting consolidation]` flag in the appropriate specification section. Ownership is type-qualified: AMBIGUITY → owned by the single source group; GAP → owned by the Absent From source group only; CONTRADICTION → owned by both Item A and Item B source groups (one flag per owned specification). No such flag is present for any ADVISORY conflict that IS CONSOLIDATED. If the Conflicts Index was empty, this rule is skipped. | BLOCKING |
| SG14 | Traceability matrix file exists at `specifications/draft/<base>_traceability.md` for each GENERATED spec. | WARNING (non-blocking if write failed) |
| SG15 | Every generated `_specification.md` contains a `**KPM Status:**` field with value `PROVENANCE_INDEXED` or `NO_PROVENANCE_INDEX`. | BLOCKING |
| SG16 | **LEGACY mode:** Every generated `_specification.md` contains a `## Inference Registry` section with exactly 4 subsections. **STD mode:** Every generated STD `_specification.md` contains `## Annexe A — Inference Registry` with exactly 4 subsections in order: `### INFERRED_DESIGN — Impact Structurel`, `### INFERRED_DESIGN — Détail d'Implémentation`, `### TECH_STANDARD`, `### UNDEFINED_IN_SOURCE`. Each empty subsection contains `*(aucun élément)*`. The `INFERRED_DESIGN — Détail d'Implémentation` subsection must contain the S0 entry. | BLOCKING |
| SG17 | Every generated `_traceability.md` contains a `Provenance` column positioned after `Type`. In T-MODE: all Provenance values are `—`. In PROVENANCE_INDEXED mode: values are one of `SF`, `UV`, `DK`, `TS`, `ID:structural`, `ID:implementation`, `US`, `—`. | WARNING |
| SG18 | For each generated `_specification.md` that contains spec-level design sections: (a) every table in those sections has a `Source` column; (b) every row where `Source = —` has a corresponding entry in the Inference Registry under `INFERRED_DESIGN — Impact Structurel` or `INFERRED_DESIGN — Détail d'Implémentation`; (c) every entire entity (table/list) declared without KB backing appears as a structural entry. A spec with no spec-level design sections satisfies SG-18 trivially. | BLOCKING |
| SG19 | `specifications/draft/sqf_gate_report.md` exists and is readable. Its `gate_status` field contains one of the valid values: `PENDING_D7`, `PASS`, `WARN`, or `BLOCK`. **Note:** SG19 is only evaluated when Phase 8.7.12 did not stop execution (i.e., no candidate produced BLOCK — if BLOCK, Phase 9 is bypassed entirely). | BLOCKING |
| SG20 | For each candidate in the Processing Set, `specifications_report.md` contains an SQF Gate entry (line `**SQF Gate:**`) in its `### SP<NNN>` record with valid D1, D3, D5, and D6 statuses. If `initial_gate_status = BLOCK`, the record `**Status:**` field reads `QUALITY_BLOCKED`. | BLOCKING |
| SG21 | **I1.3 agrees with the open points it describes.** For each candidate, count the Open Points rows (Section 13 / `## Section 13 — Open Points` / `Points Ouverts`) whose `Status` cell holds an open value per the SQF status vocabulary (`docs/implementation/SQF-Implementation-Contract.md` § 3.3). If that count is greater than zero, the I1.3 value recorded in `sqf_gate_report.md` must **not** be `ALL_RESOLVED`. It must be `DEFERRED` when every open row carries an explicit deferral justification, and `UNRESOLVED` otherwise. A gate verdict the contract cannot produce from the artifact it describes is a defect in the verdict, never in the artifact. | BLOCKING |
| SG22 | **The Inference Registry does not contradict the specification body.** For each element listed in `### INFERRED_DESIGN — Impact Structurel` with `Statut = PENDING_VALIDATION`, the element's own row or paragraph in the specification body must not carry a `**Resolution (<conflict_id>):**` marker. If it does, Step 6.7.0 either promoted it to `USER_VALIDATED` or recorded it as an unreconciled contradiction; reaching Phase 9 still contradicting itself means neither happened. | BLOCKING |

> **SG21 and SG22 exist because their absence was not theoretical.** Both conditions were true of artifacts committed on 2026-10-30, and both passed every validation rule then in force. SG21 corresponds to finding F-02 and to check `W2` of `tools/csr-check`; SG22 corresponds to finding F-10 and to check `W3`. The two mechanisms are deliberately redundant: `tools/csr-check` catches the condition in artifacts already on disk, including those produced before these rules existed, while SG21 and SG22 prevent a new one from being written at all.

### Handling Validation Failures

For each BLOCKING failure: do not declare SPECIFICATION COMPLETE. Report the failure rule, affected artifact, and violation detail. Require manual resolution.

For each WARNING failure: report the failure. Continue to completion reporting. The completion state may still be SPECIFICATION COMPLETE if no BLOCKING failures exist.

**STATUS: POST-EXECUTION VALIDATION COMPLETE**

---

## Phase 10 — Failure Handling

### Hard Stop Conditions (entire execution halts)

| Condition | Phase | Reported Status |
| --------- | ----- | --------------- |
| Workspace root not found (R3) | Phase 1 | BLOCKED — Workspace Root Not Found |
| Workspace archived (R4b) | Phase 1 | BLOCKED — Workspace Archived |
| Workspace ID not in registry (R4a) | Phase 1 | BLOCKED — Workspace Drift Detected |
| Workspace contamination detected (R6) | Phase 1 | BLOCKED — Workspace Contamination |
| No source artifacts found (Step 2.4) | Phase 2 | BLOCKED — No source artifacts found |
| `consolidation_report.md` missing when consolidated candidates exist (Step 2.2) | Phase 2 | BLOCKED — Missing Consolidation Authority Record |
| Processing Set empty after Phase 3 | Phase 3 | SPECIFICATION BLOCKED |
| `specifications/draft/` directory not found (R7) | Phase 1 | BLOCKED — Precondition P4 Failure |
| Generation log write failure after specs produced (Step 8.4) | Phase 8 | Stop + GENERATION FAILURE NOTE |
| SQF Q-GATE-1 BLOCK on D1 or D3 for any candidate (Step 8.7.12) | Phase 8.7 | QUALITY BLOCKED — see sqf_gate_report.md; Phase 9 bypassed |
| BLOCKING validation rule failure (Phase 9) | Phase 9 | SPECIFICATION BLOCKED or requires manual resolution |

### Per-Candidate Failure Conditions (execution continues with remaining candidates)

| Condition | Phase | Effect |
| --------- | ----- | ------ |
| Source artifact unreadable | Phase 4 | Candidate fails; continue |
| Required header field missing from consolidated artifact | Phase 4 | Candidate fails; continue |
| ADR-001 compliance failure (non-English content detected) | Phase 4 (Step 4.3) | Candidate fails; continue |
| No mappable sections found | Phase 3 or Phase 5 | Candidate fails; continue |
| Specification file write failure | Phase 7 (Step 7.3) | Candidate fails; continue |

When at least one candidate succeeds and at least one fails: declare SPECIFICATION PARTIAL at completion.

### Recovery Note Format

Appended to affected specification files when the generation log write fails:

```markdown
> **GENERATION FAILURE NOTE:** /generate-specification failed to update specifications_report.md after writing this specification artifact. Manual registry update required before this specification can be considered fully recorded.
```

### Rollback Expectations

This command does not roll back written specification files on failure. Specification files produced before a failure remain on disk. This is intentional: the transformation is deterministic, and the files are correct. The generation log is updated last and is the only artifact that may be incomplete after a partial failure.

---

## Phase 11 — Completion States

### SPECIFICATION COMPLETE

**Criteria:**

- Every candidate in the Processing Set was successfully transformed and written to disk.
- `specifications_report.md` has been written or updated with GENERATED status for all processed candidates.
- All SG1–SG14 validation rules pass.

**Report format:**

```text
STATUS: SPECIFICATION COMPLETE
Specifications generated: <N>
  Generated from consolidated: <M>
  Generated from extracted (zero-conflict): <K>
Ineligible source groups: <J> (if any — list with reasons)
Specification artifacts:
  - specifications/draft/<base1>_specification.md
  - specifications/draft/<base2>_specification.md
  [...]
```

### SPECIFICATION PARTIAL

**Criteria:**

- At least one specification was generated.
- At least one candidate failed (ineligibility, ADR-001 failure, source load failure, write failure).

**Report format:**

```text
STATUS: SPECIFICATION PARTIAL
Specifications generated: <N>
Failed candidates: <M>
  - <base>: <failure reason>
  [...]
Ineligible candidates: <J>
  - <base>: <ineligibility reason>
  [...]
```

### SPECIFICATION BLOCKED

**Criteria:**

- No specifications were generated.
- All candidates were ineligible, or the Processing Set was empty, or all write attempts failed, or a hard stop was reached before any specification was produced.

**Report format:**

```text
STATUS: SPECIFICATION BLOCKED
Reason: <primary blocking reason>
Candidates evaluated: <N>
  - <base>: <reason>
  [...]
```

### QUALITY BLOCKED

**Criteria:**

- At least one candidate was written to disk (Phase 7 succeeded).
- Phase 8.7 (SQF Q-GATE-1) produced `gate_status = BLOCK` for one or more candidates (D1 or D3 blocking).
- Phase 9 (Post-Execution Validation SG1–SG20) was NOT executed.

**Effect on specifications:**
- Draft specifications remain on disk at `specifications/draft/<base>_specification.md` with `**Status:** DRAFT`.
- `specifications_report.md` records the affected candidates with `**Status:** QUALITY_BLOCKED`.
- `specifications/draft/sqf_gate_report.md` contains the blocking indicator details and required corrective actions.
- No candidate is promoted or eligible for BASELINE until the blocking conditions are corrected and `/generate-specification` is re-run.

**Report format:**

```text
STATUS: QUALITY BLOCKED
SQF Q-GATE-1 blocked <N> candidate(s). Phase 9 validation not executed.

Blocked candidates:
  - <base>: D1=<status> D3=<status>
    Blocking indicator(s):
      - <indicator>: <reason>
      [...]
    Required action(s):
      1. <action>
      [...]
    Gate report: specifications/draft/sqf_gate_report.md

To resolve:
  1. Apply the required actions listed above.
  2. Re-run /generate-specification to recompute the SQF gate.
  3. A PASS or WARN result will allow pipeline progression.
```

---

## Phase 12 — E2E Validation Requirements

### Scope

E2E validation confirms that the full runtime chain from consolidated knowledge to draft specification works correctly end-to-end.

### Required Preconditions for E2E

Before executing E2E validation, the following must be true:

1. A workspace exists with at least one fully consolidated source group:
   - `*_consolidated.md` artifact exists at `WORKSPACE_ROOT/knowledge_base/consolidated/`
   - `consolidation_report.md` exists with at least one CONSOLIDATED entry
   - All BLOCKING conflicts for the test source are CONSOLIDATED
   - At least one `*_knowledge.md` artifact exists in `WORKSPACE_ROOT/knowledge_base/extracted/` with no associated conflicts (to test the zero-conflict path, if available)

2. The upstream chain is complete and validated:
   - Source document ingested via `/ingest-source`
   - Knowledge extracted via `/extract-knowledge`
   - Conflicts detected via `/detect-conflicts`
   - Questions generated via `/generate-questions`
   - Answers validated via `/human-validation` (at least one RESOLVED question)
   - Knowledge consolidated via `/consolidate-knowledge` (at least one CONSOLIDATED conflict)

### E2E Execution Checklist

After executing `/generate-specification`:

| Check | Pass Criteria |
| ----- | ------------- |
| E1 | `WORKSPACE_ROOT/specifications/draft/<base>_specification.md` exists and is readable. |
| E2 | `WORKSPACE_ROOT/specifications/draft/specifications_report.md` exists, is readable, and contains a GENERATED entry for the test source. |
| E3 | The specification header block contains all six required fields with non-empty values. |
| E4 | `**Status:** DRAFT` is present in the header block. |
| E5 | `Conflicts Incorporated` matches the `**Conflicts Resolved:**` field from the source consolidated artifact. |
| E6 | `Questions Incorporated` matches the union of question_ids from the `## Resolved Conflicts` table in the source consolidated artifact. |
| E7 | The specification contains at least one knowledge section derived from the source artifact. |
| E8 | Resolution notes from the source consolidated artifact are present verbatim in the corresponding specification sections. |
| E9 | The `## Specification Provenance` table is present for CONSOLIDATED-type specs and contains one row per resolved conflict. |
| E10 | Source consolidated artifact is unmodified (verified by re-reading and comparing header block). |
| E11 | `consolidation_report.md` is unmodified. |
| E12 | All SG1–SG13 rules pass. |
| E13 | Full traceability chain is navigable: `specification → consolidated artifact → consolidation_report.md → questions_report.md → validation session record`. |
| E14 | If zero-conflict fallback path was tested: extracted artifact produces a specification with `Source Type: EXTRACTED`, `Conflicts Incorporated: none`, `Questions Incorporated: none`, and no `## Specification Provenance` section. |
| E15 | If `conflicts_report.md` was available and ADVISORY unresolved conflicts exist for the test source: the generated specification contains inline `[ADVISORY UNRESOLVED: <conflict_id> — awaiting consolidation]` flags in the appropriate specification sections. No such flag is present for any ADVISORY conflict that is already CONSOLIDATED. If `conflicts_report.md` was absent: no ADVISORY flags are present and a WARNING was reported in the execution output. |

### Required E2E Gate

```text
STATUS: E2E VALIDATED — Specification Generation Runtime
```

This gate must be reached before implementation is considered complete.

---

## Out of Scope

### Content Generation

This command does not generate, infer, propose, or summarize specification content beyond what is present in the source artifact. Any content not present verbatim in the source artifact must not appear in the specification.

### Specification Stabilization

`/generate-specification` produces draft specifications only. Review, approval, and promotion to stable status are managed by a separate future command.

### Cross-Artifact Aggregation

This command does not merge multiple specifications into a workspace-level document. Each specification is derived from one source artifact.

### Language Translation

This command generates the specification in **English**, consistent with ADR-001 and the extraction pipeline convention (knowledge artifacts are in English regardless of source document language).

Per `docs/conventions/bilingual_output.md`, Specification artifacts use English as the primary language. The generated file is `<base>_specification_en.md`. A French companion (`<base>_specification_fr.md`) may be produced as a separate step (manual translation or a future `/translate-specification` skill) and is not required for BASELINE.

If non-English content is detected in the knowledge source artifact, this command logs a WARNING and continues — the knowledge artifact language does not block specification generation.

### Conflict Lifecycle Management

This command does not modify `conflicts_report.md`, `consolidation_report.md`, or `questions_report.md`. It does not change the status of any conflict, question, or consolidation record.
