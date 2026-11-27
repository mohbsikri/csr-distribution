# /specification-lifecycle — Execution Specification

## Purpose

This document defines the execution behavior of the `/specification-lifecycle` command for each supported lifecycle operation: BASELINE, REOPEN, EVOLVE, and ARCHIVE.

The Layer 1 contract (`docs/commands/specification-lifecycle.md`) defines what the command does. This document defines how it executes: the phase sequence, file operations, write ordering, validation procedures, failure recovery, and the cross-command guard required by Architecture Dependency A7.

---

## M9 Integration Model

Milestone 9 extends this execution specification to implement the ARCHIVE operation. The following sections are **replaced** by M9. All other sections (BASELINE, REOPEN, EVOLVE, Phase 0, Phase 1, Phase 8 BL rules, A7 Guard, Lifecycle Registry Format) are **unchanged**.

| Section | M8 content (replaced) | M9 replacement |
|---------|-----------------------|----------------|
| Phase 2 ARCHIVE row | `DRAFT or BASELINED or SUPERSEDED` | `BASELINED` only — M9-D3 |
| Phase 3 ARCHIVE Eligibility | ARCHIVED → ARCHIVED check only | Full M9-D3 forbidden-state enforcement |
| Phase 4 ARCHIVE Confirmation Prompt | Single artifact display | Full lineage display — M9-D10 |
| Phase 5 ARCHIVE Execution | AR1–AR4 (in-place, no MOVE) | AR1–AR7 (Hybrid Discovery, Integrity Gate, Controlled MOVE, Move Validation) — M9-D4/D5/D6/D8/D9 |
| Phase 6 ARCHIVE Registry Update | Two separate writes | Single atomic write (State Index + Event Append) — M9 B3 fix |
| Phase 7 ARCHIVE Generation Log | Status only | Status + archive path |
| Phase 9 ARCHIVE COMPLETE report | In-place path | Archive path + lineage summary |
| Completion States ARCHIVE COMPLETE | AR1–AR4 reference | AR1–AR7 reference |
| Failure Handling ARCHIVE rows | AR3, AR4 | AR2, AR5–AR7 |

---

## Phase Structure

All lifecycle operations share the following phase sequence. Operation-specific behavior is defined in the execution sections below.

```text
Phase 0 — Workspace Resolution
Phase 1 — Lifecycle Registry Load
Phase 2 — Target Artifact Discovery
Phase 3 — Eligibility Validation
Phase 4 — Human Confirmation
Phase 5 — Operation Execution         ← mode-specific
Phase 6 — Lifecycle Registry Update   ← mode-specific
Phase 7 — Generation Log Update
Phase 8 — Post-Operation Validation
Phase 9 — Completion Reporting
```

---

## Phase 0 — Workspace Resolution

Apply standard workspace resolution (W1–W5):

```text
W1: Read runtime/current_workspace.md → parse workspace_id
W2: WORKSPACE_ROOT = workspaces/<workspace_id>/
W3: Verify WORKSPACE_ROOT exists → BLOCKED if not found
W4: Validate registry entry in runtime/workspaces.md (R4a–R4e)
W5: All subsequent paths prefixed with WORKSPACE_ROOT
```

If workspace resolution fails at any step: stop immediately. Report:

```text
STATUS: BLOCKED — Workspace resolution failed at W<N>: <reason>
```

---

## Phase 1 — Lifecycle Registry Load

### Step 1.1 — Locate Registry

Registry path:

```text
WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md
```

If the registry does not exist:

- **BASELINE (first ever):** Proceed. The registry will be created in Phase 6.
- **REOPEN, EVOLVE, ARCHIVE:** BLOCKED — these operations require a registry to read lifecycle state.

```text
STATUS: BLOCKED — Lifecycle registry not found. BASELINE must be run before REOPEN, EVOLVE, or ARCHIVE.
```

If the `specifications/lifecycle/` directory does not exist: create it before proceeding (first lifecycle operation).

### Step 1.2 — Parse Registry

Read the registry and build the following internal index:

**spec_state_index:**

```text
{ base → { spec_id, status, current_path, version_sequence, supersedes?, reserved_spec_id? } }
```

Fields:
- `base`: the `<base>` identifier (e.g., `test_source`)
- `spec_id`: current Spec ID for this base
- `status`: current lifecycle status (DRAFT / BASELINED / SUPERSEDED / ARCHIVED)
- `current_path`: workspace-relative path to the artifact
- `version_sequence`: integer counter; 0 for new specs; incremented by each BASELINE operation
- `supersedes`: (evolved specs only) path to the SUPERSEDED artifact this was derived from
- `reserved_spec_id`: (evolved specs only) Spec ID reserved for the next generation run

**event_log:**

Ordered list of all lifecycle event records in the registry.

### Step 1.3 — Resolve Target Base

Parse `<base>` from human input or the target specification path.

Look up `<base>` in `spec_state_index`. Record `current_status`, `current_path`, and `version_sequence` (null/0 if not found).

### Step 1.4 — EVOLVE_PENDING Detection [EVOLVE Runtime Integration]

Scan `event_log` (built in Step 1.2) for an active EVOLVE_PENDING event for `<base>`:

```text
evolve_pending_mode = FALSE

For each event in event_log (reverse chronological order):
  If event.Base ≠ <base>: continue

  If event.Event_Type = "EVOLVE_PENDING"
     AND event.evolve_status ∈ {APPROVED, PARTIAL_DENY}:
    evolve_pending_mode  = TRUE
    evolve_pending_event = this event record
    evolve_id            = event.evolve_id
    candidate_v2_path    = WORKSPACE_ROOT + "/" + event.Candidate_V2_Path
    change_set_path      = WORKSPACE_ROOT + "/" + event.Change_Set_Path
    break

  If event.Event_Type ∈ {BASELINE, EVOLVE_CANCELLED}:
    break   (EVOLVE_PENDING resolved — none active for this base)
```

If `evolve_pending_mode = TRUE`:

- **BASELINE:** Switch to BASELINE V2 mode. All subsequent phases use BASELINE V2 logic (see BASELINE V2 — EVOLVE_PENDING Mode section). Standard BASELINE eligibility (E1–E7) is replaced by E6 V2 and E7 V2 for this operation.
- **REOPEN, EVOLVE, ARCHIVE:** BLOCKED.

```text
STATUS: BLOCKED — EVOLVE_PENDING active for <base>.
evolve_id: <evolve_id>
Candidate V2 registered: <candidate_v2_path>
An EVOLVE operation is awaiting BASELINE V2 via /specification-lifecycle BASELINE.
REOPEN, EVOLVE, and ARCHIVE are not permitted while EVOLVE_PENDING is active.
Run /specification-lifecycle BASELINE to process the Candidate V2,
or respond "cancel" at the BASELINE V2 confirmation prompt to cancel this EVOLVE operation.
```

---

## Phase 2 — Target Artifact Discovery

Locate and verify the target artifact for the requested operation:

| Operation | Expected Status | Expected Location |
|-----------|----------------|-------------------|
| BASELINE | DRAFT | `WORKSPACE_ROOT/specifications/draft/<base>_specification.md` |
| REOPEN | BASELINED | `WORKSPACE_ROOT/specifications/stable/<base>_specification.md` |
| EVOLVE | BASELINED | `WORKSPACE_ROOT/specifications/stable/<base>_specification.md` |
| ARCHIVE | BASELINED | `WORKSPACE_ROOT/specifications/stable/<base>_specification.md` |

Read the target artifact.

**STD Detection:** Inspect the first line of the artifact. Set `spec_mode`:
- If first line is exactly `---`: `spec_mode = STD`. Status is in YAML `status:` field; body begins after the YAML closing `---` (second `---`).
- Otherwise: `spec_mode = LEGACY`. Status is in `**Status:**` Markdown bold header; body begins after the first `---`.

`spec_mode` governs all status field reads, writes, and body boundary detection for the remainder of this execution.

Verify:

1. File exists at the expected path.
2. Status field matches the expected status for this operation: for `spec_mode = STD`, check YAML `status:`; for `spec_mode = LEGACY`, check `**Status:**`.
3. Required header fields are present: for `spec_mode = STD`, the 8 YAML frontmatter fields (`spec_id`, `title`, `workspace_id`, `version`, `status`, `baseline_date`, `language`, `template_version`) must be present; for `spec_mode = LEGACY`, all seven required Markdown bold header fields must be present and non-empty.

If the file is absent or the status does not match:

```text
STATUS: BLOCKED — Target artifact not found or status mismatch.
  Expected status: <expected>
  Actual status:   <actual>
  Path: <path>
```

Also verify for BASELINE and EVOLVE: `WORKSPACE_ROOT/specifications/stable/` directory exists. If not:

```text
STATUS: BLOCKED — specifications/stable/ directory does not exist.
```

---

## Phase 3 — Eligibility Validation

### BASELINE Eligibility

Verify conditions E1–E5 from the Layer 1 contract:

**E1 — Status is DRAFT**

Confirmed in Phase 2.

**E2 — Artifact exists and is readable**

Confirmed in Phase 2.

**E3 — All BLOCKING conflicts are CONSOLIDATED**

Read `WORKSPACE_ROOT/knowledge_base/consolidated/consolidation_report.md`.

Parse the `**Conflicts Incorporated:**` field from the draft specification header. For each `conflict_id` listed:

1. Locate the conflict record in `consolidation_report.md`.
2. Verify `status` is `CONSOLIDATED`.
3. Verify `Severity` is `BLOCKING` (ADVISORY conflicts are excluded from this check).

If any BLOCKING `conflict_id` is absent from the consolidation report or has status other than CONSOLIDATED:

```text
STATUS: BLOCKED — E3 Eligibility Failure:
  Conflict <conflict_id> is not CONSOLIDATED.
  Rerun /consolidate-knowledge after all BLOCKING conflicts are resolved.
```

**E4 — Named human authorization**

Deferred to Phase 4.

**E5 — No active BASELINED entry for this `<base>`**

Check `spec_state_index`. If an entry exists with `status = BASELINED` for this `<base>`:

```text
STATUS: BLOCKED — E5 Eligibility Failure:
  A BASELINED specification already exists for <base>.
  Run REOPEN or EVOLVE on the existing baseline before creating a new one.
```

**E6 — Inference Registry contains no INFERRED_DESIGN structural PENDING_VALIDATION element**

Read the `## Inference Registry` section from the draft specification artifact (already loaded in Phase 2).

Locate the subsection `### INFERRED_DESIGN — Impact Structurel`. If the subsection is absent or contains only `*(aucun élément)*`: E6 passes trivially. Set `e6_result = PASS`, `e6_structural_pending_count = 0`. Skip to REOPEN Eligibility.

Parse all table rows in `### INFERRED_DESIGN — Impact Structurel`. Build `blocking_elements[]`:

```text
For each row in the subsection table:
  if row["Statut"] = "PENDING_VALIDATION":
    blocking_elements[] ← { element: row["Élément"], rationale: row["Rationale"] }
```

If `blocking_elements` is non-empty:

```text
STATUS: BLOCKED — E6 Eligibility Failure: BASELINE REFUSED — INFERENCE GOVERNANCE PENDING

The specification contains unvalidated structural design decisions (ADR-004 Engagement #6).

Blocking elements:
  - <Élément> — INFERRED_DESIGN structural — <Rationale>
  [one line per element in blocking_elements[]]

Resolution paths:
  1. Obtain stakeholder validation and update governance_status to USER_VALIDATED in the Inference Registry.
  2. If the decision is accepted retroactively: update governance_status to USER_VALIDATED directly in the spec.
  3. Remove or modify the element and regenerate the specification via /generate-specification.
  4. Reclassify the element under a non-blocking provenance type per ADR-004 mechanisms.

No file operations performed. Draft artifact preserved.
```

Stop. Do not proceed to Phase 4.

If `blocking_elements` is empty: E6 passes. Set `e6_result = PASS`, `e6_structural_pending_count = 0`.

The E6 gate applies exclusively to `### INFERRED_DESIGN — Impact Structurel`. Elements in `### INFERRED_DESIGN — Détail d'Implémentation` are not checked by E6 regardless of their `governance_status`.

**E6 Extension — Write D7 scores to sqf_gate_report.md [SQF Phase 1]**

This extension executes only when `e6_result = PASS`. It does not alter the E6 blocking logic above.

Check `WORKSPACE_ROOT/specifications/draft/sqf_gate_report.md`:

**If absent:** Set `e6_ext_result = SKIPPED`. Proceed directly to E7.

**If present but unreadable or structurally inconsistent (cannot parse `gate_status` header field or `## D7` section):**

```text
STATUS: BLOCKED — E6 Extension: sqf_gate_report.md is present but unreadable or has inconsistent structure.
  Path: specifications/draft/sqf_gate_report.md
  Manual inspection required before BASELINE can proceed.
  Draft artifact preserved.
```

Stop. Do not proceed to Phase 4.

**If present and readable:** Compute I7.1 and I7.3 from inputs already available in this session:

```text
Compute I7.1 — KPM Status:
  Read **KPM Status:** header field from the draft spec artifact (Phase 2 load).
  If the field is absent or its value is "NO_PROVENANCE_INDEX":
    i7_1_value  = "T_MODE"
    i7_1_status = WARN
  Else:
    i7_1_value  = "PROVENANCE_INDEXED"
    i7_1_status = PASS

Compute I7.3 — Structural PENDING_VALIDATION count:
  i7_3_count  = e6_structural_pending_count  (0, since E6 passed)
  i7_3_status = PASS

Compute D7 Gate Status:
  d7_gate_status = worst-of(i7_1_status, i7_3_status)
  Resolution order (highest severity first): BLOCK > WARN > PASS
```

Update `sqf_gate_report.md` in-place with the following three changes:

1. Replace the `## D7 — Gouvernance des Inférences` section content (preserving the heading) with:

```
## D7 — Gouvernance des Inférences

| Indicateur | Valeur | Seuil | Statut |
|---|---|---|---|
| I7.1 — KPM Status | <i7_1_value> | PROVENANCE_INDEXED = PASS ; T_MODE = WARN | <i7_1_status> |
| I7.3 — Structural PENDING_VALIDATION | <i7_3_count> éléments | 0 = PASS ; ≥1 = BLOCK | <i7_3_status> |

**Score D7 :** I7.1 = <i7_1_status> / I7.3 = <i7_3_status>
**D7 Gate Status :** <d7_gate_status>
```

2. In the `## Verdict Global` section: update the D7 dimension row status to `<d7_gate_status>`.

3. Update the `gate_status:` header metadata field. Compute `final_gate_status`:

```text
Read current_gate_status from the file header (BLOCK, WARN, or PENDING_D7).
Map PENDING_D7 → PASS for the worst-of computation.
final_gate_status = worst-of(current_gate_status_mapped, d7_gate_status)
  where: BLOCK > WARN > PASS
Update gate_status: field to final_gate_status.
Update Gate Status Global and Décision BASELINE in ## Verdict Global:
  PASS  → Gate Status Global: PASS    — Décision BASELINE: AUTORISÉ
  WARN  → Gate Status Global: WARN    — Décision BASELINE: AUTORISÉ AVEC RÉSERVES
  BLOCK → Gate Status Global: BLOCK   — Décision BASELINE: REFUSÉ
```

If write fails: WARNING only. Non-blocking. Set `e6_ext_result = WRITE_FAILED`. Proceed to E7 using the in-memory `final_gate_status` value.

Set `e6_ext_result = WRITTEN` on success.

---

**E7 — SQF Gate Report: gate_status is not BLOCK [SQF Phase 1]**

**If `e6_ext_result = SKIPPED` (sqf_gate_report.md was absent):**

Set `e7_result = WARN_LEGACY`, `sqf_legacy = TRUE`. Record:

```text
WARNING — E7 SQF Gate: sqf_gate_report.md absent (legacy workspace — pre-SQF Phase 1 run).
BASELINE proceeds in legacy mode. Quality gate not enforced for this baseline.
Recommendation: re-run /generate-specification to produce the SQF gate report before the next BASELINE.
```

Continue to Phase 4.

**If `e6_ext_result = WRITTEN`:** Use `final_gate_status` read from the updated `sqf_gate_report.md` header.

**If `e6_ext_result = WRITE_FAILED`:** Use in-memory `final_gate_status` computed by E6 Extension.

Evaluate `final_gate_status`:

| gate_status | E7 Outcome | Action |
|-------------|------------|--------|
| `PASS` | E7 PASS | Set `sqf_pass = TRUE`. Continue to Phase 4. |
| `WARN` | E7 WARN | Set `sqf_warn = TRUE`. Continue to Phase 4 with warning recorded. |
| `BLOCK` | E7 BLOCK | BASELINE REFUSED — stop. |
| `PENDING_D7` | E7 BLOCK | BASELINE REFUSED — D7 was not evaluated (E6 Extension did not run). Stop. |
| any unrecognized value | E7 BLOCK | BASELINE REFUSED — gate_status unrecognized. Stop. |

**If E7 BLOCK:**

```text
STATUS: BLOCKED — E7 SQF Gate Failure: BASELINE REFUSED

SQF Q-GATE-1 gate_status: <final_gate_status>
The specification did not pass the SQF quality gate.

Review sqf_gate_report.md for blocking dimensions:
  Path: specifications/draft/sqf_gate_report.md

Resolution:
  1. Identify and address the blocking indicators (D1 / D3 / D7 as shown in sqf_gate_report.md).
  2. Re-run /generate-specification to regenerate the specification and the SQF gate report.
  3. Retry /specification-lifecycle BASELINE.

No file operations performed. Draft artifact preserved.
```

Stop. Do not proceed to Phase 4.

**If E7 WARN:** `sqf_warn = TRUE`. Continue to Phase 4.

**If E7 PASS:** `sqf_pass = TRUE`. Continue to Phase 4.

### REOPEN Eligibility

Target status must be BASELINED. Confirmed in Phase 2. No additional conditions.

### EVOLVE Eligibility

Target status must be BASELINED. Confirmed in Phase 2.

Additionally: verify `WORKSPACE_ROOT/specifications/draft/<base>_specification.md` does NOT exist. If it does, a DRAFT version is already active for this `<base>`:

```text
STATUS: BLOCKED — EVOLVE rejected: a DRAFT specification already exists for <base>.
  Path: specifications/draft/<base>_specification.md
  Resolve or archive the existing DRAFT before running EVOLVE.
```

### ARCHIVE Eligibility

ARCHIVE is only permitted when `current_status = BASELINED` (M9-D3). All other states are forbidden:

**DRAFT:**

```text
STATUS: BLOCKED — ARCHIVE rejected: <base> is in DRAFT state.
Only a BASELINED specification may be archived.
Required action: complete the specification lifecycle (run /specification-lifecycle BASELINE) before archiving,
or discard the draft if no longer needed.
```

**SUPERSEDED:**

```text
STATUS: BLOCKED — ARCHIVE rejected: <base> has status SUPERSEDED.
SUPERSEDED artifacts are archived automatically as part of the ARCHIVE operation applied to the active BASELINED base.
No direct ARCHIVE on a SUPERSEDED artifact is permitted.
```

**ARCHIVED:**

```text
STATUS: BLOCKED — <base> is already ARCHIVED. No further lifecycle operations are permitted.
```

No additional conditions. If `current_status = BASELINED`, the specification is eligible.

---

## Phase 4 — Human Confirmation

Present the operation summary and collect required input.

All human input fields must be confirmed before any file operation begins. If the human responds with anything other than an explicit affirmative (yes or equivalent): abort immediately. Report:

```text
STATUS: BLOCKED — Operation cancelled by human actor. No changes made.
```

### BASELINE Confirmation Prompt

```
Operation: BASELINE
Target: specifications/draft/<base>_specification.md
Current Status: DRAFT
Eligibility: VERIFIED (E1–E7 passed)

Conflicts Incorporated: <conflict_ids>
Consolidation verified: <date>
Inference Registry E6: 0 INFERRED_DESIGN structural PENDING_VALIDATION — PASS
SQF Q-GATE-1 E7: <gate_status> — <PASS | WARN (see sqf_gate_report.md for dimensions) | legacy (sqf_gate_report.md absent)>

Required:
  Validator name:      [____]
  Baseline date:       [____] (default: <today>)
  Rationale (optional): [____]

Confirm baseline? (yes/no)
```

Collect: `baseline_actor`, `baseline_date`, `baseline_rationale` (default "—" if blank).

### REOPEN Confirmation Prompt

```
Operation: REOPEN
Target: specifications/stable/<base>_specification.md
Current Status: BASELINED
Baseline Date: <date>
Baselined By: <actor>

WARNING: Downstream consumers of this baseline will lose their stable reference.
The specification will return to DRAFT. Content is unchanged.

Required:
  Actor name:   [____]
  Reopen date:  [____] (default: <today>)
  Reason:       [____]

Confirm reopen? (yes/no)
```

Collect: `reopen_actor`, `reopen_date`, `reopen_reason`.

### EVOLVE Confirmation Prompt

```
Operation: EVOLVE
Target: specifications/stable/<base>_specification.md
Current Status: BASELINED

This operation will:
  1. Preserve current baseline as: specifications/stable/<base>_specification_v<version_sequence>.md
  2. Create new DRAFT stub at: specifications/draft/<base>_specification.md

The new version requires content generation:
  After EVOLVE: process new source material → run /generate-specification → run /specification-lifecycle BASELINE

Required:
  Actor name:     [____]
  Evolution date: [____] (default: <today>)
  Reason:         [____]

Confirm evolve? (yes/no)
```

Collect: `evolve_actor`, `evolve_date`, `evolve_reason`.

### ARCHIVE Confirmation Prompt

The full lineage for `<base>` is resolved before presenting the confirmation prompt (see Phase 5 AR1 Hybrid Discovery). Present all artifacts that will be moved:

```
Operation: ARCHIVE (terminal — no further lifecycle operations allowed)
Specification: <base>

Artifacts to be moved to specifications/archive/:
  Active baseline:  specifications/stable/<base>_specification.md  (Status: BASELINED)
  Superseded v1:    specifications/stable/<base>_specification_v1.md  (Status: SUPERSEDED)
  [additional superseded artifacts, one line each]

All <n> artifacts above will be moved from stable/ to archive/.
No artifacts will remain in specifications/stable/ for this base after this operation.

Required:
  Actor name:    [____]
  Archive date:  [____] (default: <today>)
  Reason:        [____]

Confirm archive? (yes/no)
```

If no superseded artifacts exist for this base, omit the superseded lines and show only the active baseline row.

Collect: `archive_actor`, `archive_date`, `archive_reason`.

### Language Normalization

If any collected text field (rationale, reason) appears to be in a language other than English: produce an English-normalized version and present it to the human actor for confirmation before proceeding. Do not persist non-English text in any lifecycle record.

---

## Phase 5 — Operation Execution

### BASELINE Execution

**Write ordering is mandatory. Steps execute in sequence. On any blocking failure: stop and report.**

#### Step BA1 — Prepare stable artifact content

Load draft artifact content (from Phase 2 read). Apply in-memory modifications based on `spec_mode`.

**For STD specs (`spec_mode = STD`):**

- Update YAML field: `status: BASELINED`
- Update YAML field: `baseline_date: <baseline_date>`
- Do not write Markdown bold fields; `baseline_actor` and `baseline_rationale` are recorded in the lifecycle registry Event Log only.
- Content below the YAML closing `---` (second `---`) must not be altered.
- Store content below the YAML closing `---` as `body_checksum` for BL11 verification.

**For legacy specs (`spec_mode = LEGACY`):**

- Update: `**Status:** BASELINED`
- Add: `**Baseline Date:** <baseline_date>`
- Add: `**Baselined By:** <baseline_actor>`
- Add: `**Baseline Rationale:** <baseline_rationale>`
- Content below the first `---` separator must not be altered.
- Store original content below `---` as `body_checksum` for BL11 verification.

#### Step BA2 — Write stable artifact

Write the modified content to:

```text
WORKSPACE_ROOT/specifications/stable/<base>_specification.md
```

If write fails:

```text
STATUS: BLOCKED — Write failure: specifications/stable/<base>_specification.md
Draft artifact preserved. No changes made.
```

#### Step BA3 — Verify stable artifact

Read back `WORKSPACE_ROOT/specifications/stable/<base>_specification.md`. Verify based on `spec_mode`:

**For STD specs (`spec_mode = STD`):**
- File exists and is readable
- YAML `status:` is `BASELINED`
- YAML `baseline_date:` is present and non-null
- Content below YAML closing `---` matches `body_checksum` exactly

**For legacy specs (`spec_mode = LEGACY`):**
- File exists and is readable
- `**Status:** BASELINED`
- `**Baseline Date:**` is present and non-empty
- `**Baselined By:**` is present and non-empty
- Content below `---` matches `body_checksum` exactly

If any verification check fails: delete the stable artifact (rollback). Abort. Preserve draft:

```text
STATUS: BLOCKED — Verification failure after writing stable artifact.
Rollback performed. Draft artifact preserved.
Reason: <specific check that failed>
```

#### Step BA4 — Delete draft artifact

Delete `WORKSPACE_ROOT/specifications/draft/<base>_specification.md`.

If deletion fails: WARNING only. Both stable and draft exist. The lifecycle registry (updated in Phase 6) records BASELINED status; the stable artifact is authoritative. Log:

```text
WARNING: Draft artifact deletion failed. Manual cleanup required:
  specifications/draft/<base>_specification.md
```

Continue to BA5.

#### Step BA5 — Verify draft deletion

Confirm `WORKSPACE_ROOT/specifications/draft/<base>_specification.md` no longer exists.

If draft still exists: WARNING. Record for manual cleanup. Continue.

#### Step BA5b — Update SUPERSEDED artifacts (evolved specifications only)

If the lifecycle registry `spec_state_index` entry for `<base>` contains a `supersedes` field (indicating this BASELINE is for an evolved version), update the SUPERSEDED artifact's `**Superseded By:**` field:

1. Identify the SUPERSEDED artifact path from `supersedes`.
2. Read the SUPERSEDED artifact.
3. Update `**Superseded By:**` from `specifications/draft/<base>_specification.md` to `specifications/stable/<base>_specification.md`.
4. Write back to the versioned path. Verify.

If this update fails: WARNING only. The lifecycle registry provides the authoritative lineage. Record:

```text
WARNING: Could not update **Superseded By** in <versioned_path>.
Lifecycle registry is authoritative for lineage.
```

Continue.

#### Step BASELINE-TM — Traceability Matrix Co-movement (non-blocking)

1. Check if `specifications/draft/<base>_traceability.md` exists.
2. If absent: note "Traceability matrix not found — skipping co-movement." Continue.
3. If present: MOVE to `specifications/stable/<base>_traceability.md` (write → verify → delete → verify absent).
4. On MOVE failure: log WARNING. Do not block BASELINE completion.

#### Step BASELINE-SQF — SQF Gate Report Snapshot [SQF Phase 1]

1. Check if `specifications/draft/sqf_gate_report.md` exists.
2. If absent: note "SQF gate report not found — skipping snapshot (legacy workspace or pre-SQF run)." Continue.
3. If present: COPY to `specifications/stable/sqf_gate_report.md`:
   a. Read content from `specifications/draft/sqf_gate_report.md`.
   b. Write to `specifications/stable/sqf_gate_report.md`.
   c. Verify: read back stable/ copy and confirm it is non-empty and contains the `gate_status:` header field.
   d. The draft/ copy is preserved (not deleted); the stable/ copy is the BASELINED quality gate snapshot.
4. On COPY failure: log WARNING. Do not block BASELINE completion.

---

### REOPEN Execution

**Write ordering is mandatory.**

#### Step RO1 — Prepare draft artifact content

Load stable artifact content (from Phase 2 read). Apply in-memory modifications based on `spec_mode`.

**For STD specs (`spec_mode = STD`):**

- Update YAML field: `status: DRAFT`
- Update YAML field: `baseline_date: null`
- No Markdown bold fields to remove (STD artifacts do not carry `**Baseline Date:**`, `**Baselined By:**`, or `**Baseline Rationale:**` in the body).
- Do not alter content below the YAML closing `---`. Store original body as `body_checksum`.

**For legacy specs (`spec_mode = LEGACY`):**

- Update: `**Status:** DRAFT`
- Remove: `**Baseline Date:**`
- Remove: `**Baselined By:**`
- Remove: `**Baseline Rationale:**`
- Do not alter content below `---`. Store original body as `body_checksum`.

#### Step RO2 — Write draft artifact

Write the modified content to:

```text
WORKSPACE_ROOT/specifications/draft/<base>_specification.md
```

If write fails:

```text
STATUS: BLOCKED — Write failure: specifications/draft/<base>_specification.md
Stable artifact preserved. No changes made.
```

#### Step RO3 — Verify draft artifact

Read back. Verify based on `spec_mode`:

**For STD specs (`spec_mode = STD`):**
- YAML `status:` is `DRAFT`
- YAML `baseline_date:` is `null`
- Content below YAML closing `---` matches `body_checksum` exactly

**For legacy specs (`spec_mode = LEGACY`):**
- `**Status:** DRAFT`
- `**Baseline Date:**` is absent
- `**Baselined By:**` is absent
- Content below `---` matches `body_checksum` exactly

If any check fails: delete draft (rollback). Abort. Preserve stable:

```text
STATUS: BLOCKED — Verification failure after writing draft artifact.
Rollback performed. Stable artifact preserved.
```

#### Step RO4 — Delete stable artifact

Delete `WORKSPACE_ROOT/specifications/stable/<base>_specification.md`.

If deletion fails: WARNING. Both paths exist. Draft is authoritative (registry update in Phase 6 records DRAFT status). Log warning. Continue.

#### Step RO5 — Verify stable deletion

Confirm stable artifact no longer exists. If still present: WARNING. Record for manual cleanup. Continue.

#### Step REOPEN-VS: View Staleness — Update generation log.

Read WORKSPACE_ROOT/specifications/draft/specifications_report.md.
If the file exists and contains View Generation Records rows matching this <base>:
  Set Views Status → STALE for all matching VW rows.
  Write the updated file.
If the file is absent or no matching rows exist: skip (WARNING only — non-blocking).

#### Step REOPEN-TCS: Test Cases Staleness — Update generation log. `[C2b, 2026-11-01]`

Read WORKSPACE_ROOT/specifications/draft/specifications_report.md.
If the file exists and contains a Test Case Generation Records row matching this <base>:
  Set Test Cases Status → STALE for the matching TC row.
  Write the updated file.
If the file is absent or no matching row exists: skip (WARNING only — non-blocking). Same mechanism as Step REOPEN-VS immediately above, applied to the test specification book instead of views.

#### Step REOPEN-TM — Traceability Matrix Co-movement (non-blocking)

1. Check if `specifications/stable/<base>_traceability.md` exists.
2. If absent: note "Traceability matrix not found — skipping co-movement." Continue.
3. If present: MOVE to `specifications/draft/<base>_traceability.md` (write → verify → delete → verify absent).
4. On MOVE failure: log WARNING. Do not block REOPEN completion.

---

### EVOLVE Execution

**Write ordering is mandatory.**

#### Step EV1 — Determine version number

Read `version_sequence` from `spec_state_index` for `<base>`. This is the version number to assign to the SUPERSEDED artifact.

If `version_sequence = 0`: this is the first EVOLVE for this `<base>`. The current BASELINED spec was baseline version 1; it is assigned `_v1` suffix.

Versioned path:

```text
WORKSPACE_ROOT/specifications/stable/<base>_specification_v<version_sequence>.md
```

#### Step EV2 — Prepare versioned (SUPERSEDED) artifact content

Load current stable artifact content (from Phase 2 read). Apply in-memory modifications based on `spec_mode`.

**For STD specs (`spec_mode = STD`):**

- Update YAML field: `status: SUPERSEDED`
- Do not add `**Superseded Date:**` or `**Superseded By:**` to the artifact body; this information is captured exclusively in the lifecycle registry EVOLVE event record.
- Do not alter content below the YAML closing `---`. Store original body as `body_checksum`.

**For legacy specs (`spec_mode = LEGACY`):**

- Update: `**Status:** SUPERSEDED`
- Add: `**Superseded Date:** <evolve_date>`
- Add: `**Superseded By:** specifications/draft/<base>_specification.md`
- Do not alter content below `---`. Store original body as `body_checksum`.

#### Step EV3 — Write versioned artifact

Write to:

```text
WORKSPACE_ROOT/specifications/stable/<base>_specification_v<version_sequence>.md
```

If write fails:

```text
STATUS: BLOCKED — Write failure: versioned SUPERSEDED artifact.
Unsuffixed stable artifact preserved. No changes made.
```

#### Step EV4 — Verify versioned artifact

Read back. Verify based on `spec_mode`:

**For STD specs (`spec_mode = STD`):**
- YAML `status:` is `SUPERSEDED`
- Content below YAML closing `---` matches `body_checksum` exactly

**For legacy specs (`spec_mode = LEGACY`):**
- `**Status:** SUPERSEDED`
- `**Superseded Date:**` non-empty
- `**Superseded By:**` non-empty
- Content below `---` matches `body_checksum` exactly

If any check fails: delete versioned artifact (rollback). Abort. Preserve unsuffixed stable:

```text
STATUS: BLOCKED — Verification failure: versioned artifact content mismatch.
Rollback performed. Unsuffixed stable artifact preserved.
```

#### Step EV5 — Delete unsuffixed stable artifact

Delete `WORKSPACE_ROOT/specifications/stable/<base>_specification.md`.

If deletion fails: WARNING. Both unsuffixed and versioned exist. The versioned artifact at `_v<n>` is the SUPERSEDED record; the unsuffixed should be deleted. Log warning. Continue.

#### Step EV6 — Verify unsuffixed stable deletion

Confirm `specifications/stable/<base>_specification.md` no longer exists. If still present: WARNING. Record for manual cleanup. Continue.

#### Step EV7 — Assign reserved Spec ID

Read `spec_state_index` and the generation log to find the highest existing Spec ID (format: `SP<NNN>`).

Assign `reserved_spec_id = SP<(max + 1)>`, zero-padded to 3 digits.

#### Step EV8 — Create DRAFT stub

Determine display name: read from the SUPERSEDED artifact's top-level `#` heading. Strip known pipeline suffixes (` — Draft Specification`, ` — Specification`, etc.) if present.

Create the stub file at:

```text
WORKSPACE_ROOT/specifications/draft/<base>_specification.md
```

Stub content:

```markdown
# <display_name> — Draft Specification

**Source Artifact:** —
**Source Type:** —
**Generated:** —
**Generation Command:** /generate-specification
**Conflicts Incorporated:** —
**Questions Incorporated:** —
**Status:** DRAFT
**Supersedes:** specifications/stable/<base>_specification_v<version_sequence>.md

---

*Evolved version pending content generation. Process new source material through the pipeline, then run /generate-specification.*
```

If write fails: PARTIAL state. The SUPERSEDED versioned artifact was created; the new DRAFT stub was not. Record. Proceed to Phase 6 (registry update records the PARTIAL state). Report at Phase 9.

#### Step EV9 — Verify DRAFT stub

Read back stub. Verify:

- File exists
- `**Status:** DRAFT`
- `**Supersedes:**` field is present and points to `specifications/stable/<base>_specification_v<version_sequence>.md`

If verification fails: WARNING. Record. Continue.

#### Step EVOLVE-VS: View Staleness — Update generation log.

Read WORKSPACE_ROOT/specifications/draft/specifications_report.md.
If the file exists and contains View Generation Records rows matching this <base>:
  Set Views Status → STALE for all matching VW rows.
  Write the updated file.
If the file is absent or no matching rows exist: skip (WARNING only — non-blocking).

#### Step EVOLVE-TCS: Test Cases Staleness — Update generation log. `[C2b, 2026-11-01]`

Read WORKSPACE_ROOT/specifications/draft/specifications_report.md.
If the file exists and contains a Test Case Generation Records row matching this <base>:
  Set Test Cases Status → STALE for the matching TC row.
  Write the updated file.
If the file is absent or no matching row exists: skip (WARNING only — non-blocking). Same mechanism as Step EVOLVE-VS immediately above, applied to the test specification book instead of views. This is what actually answers the staleness question for M-TC: unlike the withdrawn CAP-08 (M11 pipeline orchestration, reverted — views are not M11 capabilities either, so neither should test cases be), the cahier de recette now goes stale on EVOLVE through the exact same mechanism as every other derived artifact in this contract.

#### Step EVOLVE-TM — Traceability Matrix Co-movement (non-blocking)

1. Check if `specifications/stable/<base>_traceability.md` exists.
2. If absent: note "Traceability matrix not found — skipping." Continue.
3. If present: MOVE to `specifications/stable/<base>_traceability_v<version_sequence>.md` (versioned alongside the superseded spec; write → verify → delete → verify absent).
4. On MOVE failure: log WARNING. Do not block EVOLVE completion.

---

### ARCHIVE Execution

**Write ordering is mandatory. Steps execute in sequence. On any blocking failure: stop and report. No partial registry update.**

#### Step AR1 — Hybrid Discovery (M9-D8)

Build the full lineage for `<base>` using two sources:

1. **Registry First:** Read `spec_state_index`. Record the active baseline: `active_path = current_path`, `active_spec_id = spec_id`.

2. **Event Log Scan:** Scan all EVOLVE event records in the Event Log for records where `Base = <base>`. For each EVOLVE event found, record the `Superseded Artifact` path and `Superseded Spec ID`. Build `superseded_artifacts[]` ordered by event sequence (oldest first).

3. **Filesystem Verification:** For each path in `active_path` + `superseded_artifacts[]`, verify the file exists on disk.

4. **Result:** `full_lineage = [active_path] + superseded_artifacts[]` — the complete ordered list of artifacts to be moved.

5. **Traceability Co-artifacts:** Also check if `specifications/stable/<base>_traceability.md` exists; if so, include it in `full_lineage` as a co-artifact. If versioned traceability files exist (e.g., `specifications/stable/<base>_traceability_v<n>.md`, from prior EVOLVE operations), include them as well. Traceability co-artifacts use the same MOVE semantics as spec files (write to archive/ → verify → delete from stable/ → verify absent). Absence of any traceability co-artifact is non-blocking; record a note and continue.

If any path in `full_lineage` does not exist on disk: record as missing but continue building the lineage. Missing paths are reported in the Integrity Gate (AR2). Missing traceability co-artifacts are non-blocking (log note only — do not treat as Integrity Gate failures).

#### Step AR2 — Integrity Gate (M9-D9)

Compare the expected lineage (from AR1) against the actual filesystem state before any write or move begins.

For each artifact in `full_lineage`:

- Verify the file exists at the expected stable/ path.
- Verify no file already exists at the corresponding archive/ destination path (`specifications/archive/<filename>`).

If any file is missing from stable/:

```text
STATUS: BLOCKED — ARCHIVE_BLOCKED: Integrity Gate failure.
Missing artifact: <path>
Expected in specifications/stable/ but not found.
No files moved. Registry unchanged.
```

If any destination path in archive/ already exists:

```text
STATUS: BLOCKED — ARCHIVE_BLOCKED: Integrity Gate failure.
Destination conflict: <archive_path> already exists.
No files moved. Registry unchanged.
```

Do not proceed to AR3 if the Integrity Gate fails. The `specifications/archive/` directory is created now if it does not exist (first ARCHIVE operation).

#### Step AR3 — Prepare archived content (all artifacts)

For each artifact in `full_lineage`, load its content, determine `spec_mode` (STD if first line is `---`, LEGACY otherwise), and apply in-memory modifications:

**For STD specs (`spec_mode = STD`):**
- Update YAML field: `status: ARCHIVED`
- Do not add `**Archived Date:**`, `**Archived By:**`, or `**Archive Reason:**` to the body; this information is captured exclusively in the lifecycle registry ARCHIVE event record.
- Do not alter content below the YAML closing `---`. Store as `body_checksum[path]`.

**For legacy specs (`spec_mode = LEGACY`):**
- Update: `**Status:** ARCHIVED`
- Add: `**Archived Date:** <archive_date>`
- Add: `**Archived By:** <archive_actor>`
- Add: `**Archive Reason:** <archive_reason>`
- Do not alter content below `---`. Store original body content as `body_checksum[path]`.

#### Step AR4 — Write to archive/ (MOVE step 1: write)

For each artifact in `full_lineage`, write the modified content to the archive destination:

```text
WORKSPACE_ROOT/specifications/archive/<filename>
```

where `<filename>` is the filename component of the source path (unchanged).

If write fails for any artifact:

```text
STATUS: BLOCKED — Write failure: archive/ write failed for <filename>.
No stable/ files deleted. No registry update performed.
```

Do not proceed to AR5 if any archive/ write fails.

#### Step AR5 — Verify archive/ writes

For each artifact written in AR4, read back the archive/ destination. Verify based on `spec_mode`:

**For STD specs (`spec_mode = STD`):**
- File exists and is readable
- YAML `status:` is `ARCHIVED`
- Content below YAML closing `---` matches `body_checksum[path]` exactly

**For legacy specs (`spec_mode = LEGACY`):**
- File exists and is readable
- `**Status:** ARCHIVED`
- `**Archived Date:**` is present and non-empty
- `**Archived By:**` is present and non-empty
- Content below `---` matches `body_checksum[path]` exactly

If verification fails for any artifact:

```text
STATUS: BLOCKED — CRITICAL: archive/ verification failed for <filename>.
Manual inspection required: specifications/archive/<filename>
No stable/ files deleted. Registry update NOT performed.
```

Do not proceed to AR6 if any AR5 verification fails.

#### Step AR6 — Delete from stable/ (MOVE step 2: delete) with Retry Policy (M9-D6)

For each artifact in `full_lineage`, delete the source file from `specifications/stable/`.

Apply the Retry Policy (M9-D6) on deletion failure:

- Attempt 1: immediate
- Attempt 2: after 1 second
- Attempt 3: after 2 seconds
- Attempt 4: after 4 seconds
- Attempt 5: after 8 seconds

If deletion fails after all 5 attempts for any artifact:

```text
STATUS: BLOCKED — CRITICAL: stable/ deletion failed for <filename> after 5 attempts.
Archive copy exists at: specifications/archive/<filename>
Manual deletion required: specifications/stable/<filename>
Registry update NOT performed.
```

Do not proceed to Phase 6 (registry update) if any deletion fails after exhausting retries.

#### Step AR7 — Verify deletion

For each artifact in `full_lineage`, verify the source path in `specifications/stable/` no longer exists.

If any source file still exists after AR6:

```text
STATUS: BLOCKED — CRITICAL: stable/ file still present after deletion: <path>
Archive copy exists. Manual cleanup required.
Registry update NOT performed.
```

Do not proceed to Phase 6 if AR7 verification fails.

---

## Phase 6 — Lifecycle Registry Update

All event records are appended. Prior event records must never be overwritten or deleted.

If the registry does not exist (first BASELINE only): create it with the header and section structure defined in the Lifecycle Registry Format section below.

### BASELINE Registry Update

1. **Update the Active State Index row for `<base>`:**
   - `spec_id`: from generation log
   - `status`: BASELINED
   - `current_path`: `specifications/stable/<base>_specification.md`
   - `version_sequence`: prior value + 1
   - `Last Event`: `<baseline_date>`

   If the row carried `supersedes` and `reserved_spec_id` fields (evolved spec): clear both fields. These fields are only valid during the EVOLVE→M7→BASELINE window.

2. **Append BASELINE event record** (format defined in Lifecycle Registry Format section). Include the following SQF quality gate fields [SQF Phase 1]:
   - **SQF Gate:** `PASS` / `WARN` / `BLOCK` / `NOT_RUN` (use NOT_RUN when `sqf_legacy = TRUE`)
   - **SQF Flags:** one of `sqf_pass=true` / `sqf_warn=true` / `sqf_legacy=true`; use `—` if none apply

If registry write fails: CRITICAL.

Append a BASELINE FAILURE NOTE to the stable artifact:

```markdown
> LIFECYCLE FAILURE NOTE: BASELINE file operations completed but registry write failed.
> Date: <baseline_date>
> Manual registry update required.
```

Report:

```text
STATUS: BLOCKED — CRITICAL: lifecycle registry write failed after file operations completed.
File state: specifications/stable/<base>_specification.md exists with Status: BASELINED.
Registry state: NOT updated.
Manual recovery required.
```

### REOPEN Registry Update

1. **Update spec_state_index entry** for `<base>`:
   - `status`: DRAFT
   - `current_path`: `specifications/draft/<base>_specification.md`
   - `Last Event`: `<reopen_date>`

2. **Append REOPEN event record.**

Prior BASELINE event records for this `<base>` must not be modified.

If registry write fails: CRITICAL. The draft artifact exists but the registry still shows BASELINED. Append a REOPEN FAILURE NOTE to the draft artifact. Report BLOCKED.

### EVOLVE Registry Update

1. **Update the existing Active State Index row for `<base>`** (in-place; one row per base):
   - `spec_id`: `reserved_spec_id` from Step EV7
   - `status`: DRAFT
   - `current_path`: `specifications/draft/<base>_specification.md`
   - `version_sequence`: carry forward current value (unchanged; incremented at next BASELINE)
   - `supersedes`: `specifications/stable/<base>_specification_v<version_sequence>.md`
   - `reserved_spec_id`: `reserved_spec_id` (retained for M7 A7 guard use)
   - `Last Event`: `<evolve_date>`

   The SUPERSEDED artifact's original spec_id and versioned path are not separately indexed. They are captured in the EVOLVE event record (step 2). The Event Log is the authority for historical versions.

   If EV8 failed (stub not created): `status` is still `DRAFT`. The PARTIAL completion state communicates the stub failure. No additional status value is used.

2. **Append EVOLVE event record** with: `Event ID`, `Event Type: EVOLVE`, `Spec ID` (reserved_spec_id), `Base`, `Date`, `Actor`, `Reason`, `Artifact` (draft stub path or `—` if EV8 failed), `Superseded Artifact` (versioned_path), `Superseded Spec ID` (original spec_id), `New Spec ID` (reserved_spec_id).

If registry write fails: CRITICAL. Versioned SUPERSEDED artifact exists but registry is not updated. Append EVOLVE FAILURE NOTE to the versioned artifact. Report BLOCKED.

### ARCHIVE Registry Update

The State Index update and ARCHIVE Event Append must be performed as a **single atomic write** to prevent a state where the Active State Index shows ARCHIVED but no ARCHIVE event record exists.

In a single write operation:

1. **Update spec_state_index entry** for `<base>`:
   - `status`: ARCHIVED
   - `current_path`: `specifications/archive/<base>_specification.md`
   - `Last Event`: `<archive_date>`

2. **Append ARCHIVE event record** with all lineage moved. Include: `Event ID`, `Event Type: ARCHIVE`, `Spec ID`, `Base`, `Date`, `Actor`, `Reason`, `Artifact` (archive path of active baseline), `Lineage Moved` (count of superseded artifacts moved).

If registry write fails: CRITICAL. All stable/ artifacts have been deleted and archive/ copies exist, but the registry does not reflect the ARCHIVED state.

```text
STATUS: BLOCKED — CRITICAL: lifecycle registry write failed after MOVE operations completed.
Archive artifacts exist: specifications/archive/<base>_specification.md [+ versioned artifacts]
Stable artifacts removed.
Registry state: NOT updated.
Manual registry update required.
```

---

## Phase 7 — Generation Log Update

Read `WORKSPACE_ROOT/specifications/draft/specifications_report.md`.

Apply the following update based on operation:

| Operation | Entry to update | Change |
|-----------|----------------|--------|
| BASELINE | Entry for `spec_id` | `Specification Artifact`: change to stable path; `Status`: BASELINED |
| BASELINE (evolved) | Entry for old `spec_id` | `Status`: SUPERSEDED |
| REOPEN | Entry for `spec_id` | `Specification Artifact`: change to draft path; `Status`: DRAFT |
| EVOLVE | Entry for old `spec_id` | `Status`: SUPERSEDED |
| EVOLVE | New row | `spec_id`: reserved_spec_id; `Source Artifact`: —; `Specification Artifact`: draft stub path; `Status`: DRAFT |
| ARCHIVE | Entry for `spec_id` | `Specification Artifact`: change to archive path; `Status`: ARCHIVED |

Write the updated generation log.

If the generation log update fails: WARNING only. Non-blocking. The lifecycle registry is authoritative.

```text
WARNING: Generation log update failed. Lifecycle registry is authoritative for current status.
Path: specifications/draft/specifications_report.md
```

Continue to Phase 8.

---

## Phase 8 — Post-Operation Validation

Execute the applicable BL rules. For each failing BLOCKING rule: report the rule ID, the artifact path, and the specific check that failed. Stop completion reporting.

### Validation Procedure

**BL1 (BASELINE):** Read lifecycle registry. Find BASELINE event for `spec_id`. Verify `baseline_date` and `baselined_by` are non-empty. **BLOCKING.**

**BL2 (BASELINE):** Confirm `specifications/stable/<base>_specification.md` exists and is readable. **BLOCKING.**

**BL3 (BASELINE):** The Active State Index row for `<base>` has `status = BASELINED`. (One row per base — the single row must show BASELINED after this operation.) **BLOCKING.**

**BL4 (EVOLVE):** Read versioned artifact `<base>_specification_v<n>.md`. Verify SUPERSEDED status: **STD spec** (`spec_mode = STD`): YAML `status:` must be `SUPERSEDED`; **legacy spec**: `**Superseded By:**` field must be present and non-empty. For both types, lineage is authoritative in the lifecycle registry EVOLVE event record. **BLOCKING.**

**BL5 (BASELINE for evolved spec):** Read the lifecycle registry `spec_state_index` entry for `<base>`. If a `supersedes` field is present (indicating this is an evolved version): verify the referenced SUPERSEDED artifact exists at the declared path and is readable. The registry `supersedes` field is authoritative for this check; the artifact's `**Supersedes:**` header field is informational only and is not used for BL5 enforcement. **BLOCKING.**

**BL6 (REOPEN):** Read lifecycle registry. Find REOPEN event for `spec_id`. Verify `reopen_date`, `actor`, `reason` are all non-empty. **BLOCKING.**

**BL7 (REOPEN):** Confirm `specifications/draft/<base>_specification.md` exists and has DRAFT status: **STD spec** (`spec_mode = STD`): YAML `status:` must be `DRAFT`; **legacy spec**: `**Status:**` must be `DRAFT`. **BLOCKING.**

**BL8 (EVOLVE):** Read lifecycle registry. Find EVOLVE event. Verify `evolution_date`, `actor`, `reason`, `superseded_artifact`, `new_spec_id` are all non-empty. **BLOCKING.**

**BL9 (All):** Confirm `specifications/lifecycle/specifications_lifecycle.md` exists and is readable. **BLOCKING.**

**BL10 (All):** Confirm every file written in Phase 5 has a path starting with `WORKSPACE_ROOT/specifications/`. **BLOCKING.**

**BL11 (All):** For each artifact written: re-read body content and compare with `body_checksum` captured in Phase 5. Must be byte-identical. **Body boundary:** STD spec (`spec_mode = STD`) — body begins after the YAML closing `---` (second `---` from top of file); legacy spec — body begins after the first `---` separator. **BLOCKING.**

**BL12 (BASELINE, REOPEN):** Read the generation log. Verify `Specification Artifact` column for `spec_id` reflects the current post-operation path. **WARNING.**

**BL13 (BASELINE):** Step BASELINE-BL13 — View Staleness Check.
Read WORKSPACE_ROOT/specifications/draft/specifications_report.md.
If the file contains View Generation Records rows matching this <base> with Views Status = STALE:
  Emit WARNING: "BL13 — Views for <base> are stale. Run /generate-views after this BASELINE to regenerate."

**BL14 (BASELINE):** `[C2b, 2026-11-01]` Step BASELINE-BL14 — Test Cases Staleness Check.
Read WORKSPACE_ROOT/specifications/draft/specifications_report.md.
If the file contains no Test Case Generation Records row for this <base>, OR contains one with Test Cases Status = STALE:
  Emit WARNING: "BL14 — Test cases for <base> are stale. Run /generate-test-cases after this BASELINE to regenerate."
Identical mechanism to BL13, applied to the test specification book. Unlike BL13, a missing row also warns — views may legitimately never have been generated without that being notable on a first BASELINE, but a cahier de recette is the acceptance-testing artifact the client-requested deliverable exists for, so its absence is worth surfacing even on the very first BASELINE.
  Record this warning in the BASELINE COMPLETE report.
This step is non-blocking. BASELINE proceeds regardless of the staleness state.

---

## Phase 9 — Completion Reporting

### BASELINE COMPLETE

```
STATUS: BASELINE COMPLETE

Specification: <base>
Spec ID: <spec_id>
Stable path: specifications/stable/<base>_specification.md
Baseline Date: <date>
Baselined By: <actor>
E3 verified: <conflict_ids> — all CONSOLIDATED
E6 verified: Inference Registry — 0 INFERRED_DESIGN structural PENDING_VALIDATION
E7 SQF Gate: <gate_status> — <PASS | WARN (see sqf_gate_report.md) | legacy (sqf_gate_report.md absent)>

Validation: E6 ✓  E7 ✓  BL1 ✓  BL2 ✓  BL3 ✓  BL9 ✓  BL10 ✓  BL11 ✓
Generation log: updated
```

### REOPEN COMPLETE

```
STATUS: REOPEN COMPLETE

Specification: <base>
Spec ID: <spec_id>
Draft path: specifications/draft/<base>_specification.md
Reopen Date: <date>
Reopened By: <actor>
Reason: <reason>

Prior baseline (date / actor) preserved in lifecycle registry.

Validation: BL6 ✓  BL7 ✓  BL9 ✓  BL10 ✓  BL11 ✓
Next step: run /generate-specification to update content if needed.
```

### EVOLVE COMPLETE

```
STATUS: EVOLVE COMPLETE

Specification: <base>
Superseded: specifications/stable/<base>_specification_v<n>.md (Spec ID: <old_spec_id>)
New DRAFT: specifications/draft/<base>_specification.md (Spec ID: <reserved_spec_id>)
Evolution Date: <date>
Evolved By: <actor>
Reason: <reason>

Validation: BL4 ✓  BL8 ✓  BL9 ✓  BL10 ✓  BL11 ✓

Next steps:
  1. Process new source material through the pipeline (ingest → extract → conflicts → questions → validation → consolidation)
  2. Run /generate-specification
  3. Run /specification-lifecycle BASELINE
```

### ARCHIVE COMPLETE

```
STATUS: ARCHIVE COMPLETE

Specification: <base>
Spec ID: <spec_id>
Archive path: specifications/archive/<base>_specification.md
Archive Date: <date>
Archived By: <actor>
Reason: <reason>

Lineage moved:
  Active baseline: specifications/archive/<base>_specification.md
  Superseded:      specifications/archive/<base>_specification_v<n>.md  [repeat per version]
  Total artifacts moved: <n>

Stable path removed: specifications/stable/<base>_specification.md  — absent ✓
[Superseded stable paths removed: specifications/stable/<base>_specification_v<n>.md  — absent ✓]

Validation: BL9 ✓  BL10 ✓  BL11 ✓
Note: ARCHIVED is terminal. No further lifecycle operations permitted for this specification.
```

If no superseded artifacts existed, omit the superseded lineage rows and show `Total artifacts moved: 1`.

### BLOCKED

```
STATUS: BLOCKED

Operation: <BASELINE | REOPEN | EVOLVE | ARCHIVE>
Blocked at: Phase <N>, Step <XX> (if applicable)
Reason: <explicit failure description>
Rollback: <performed | not required | manual action required>
Artifacts affected: <list>
```

### PARTIAL

```
STATUS: PARTIAL — <specific partial condition>

Succeeded: <list of completed steps>
Failed: <failed step and reason>
Manual action required: <description>
```

---

## Cross-Command Guard (A7)

### Overview

`/generate-specification` (M7) currently allows re-generation of any existing specification. After M8, M7 must consult the lifecycle registry before writing to `WORKSPACE_ROOT/specifications/draft/<base>_specification.md` to prevent overwriting specifications whose lifecycle state prohibits it.

This section defines the guard behavior. It does not redesign M7; it defines the dependency and the required outcome.

### Guard Procedure

At the point in M7's execution where it is about to write `WORKSPACE_ROOT/specifications/draft/<base>_specification.md`, M7 must execute the following:

**Step AG1 — Check lifecycle registry presence**

Check whether `WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md` exists.

If it does not exist: no lifecycle management is active. Proceed with normal M7 generation (no guard applied).

**Step AG2 — Lookup `<base>` in lifecycle registry**

If the registry exists: parse `spec_state_index`. Lookup entry for `<base>`.

If no entry found for `<base>`: no prior lifecycle history. Proceed normally.

**Step AG3 — Evaluate lifecycle status**

If an entry is found:

| `status` in registry | M7 Action |
|---------------------|-----------|
| DRAFT | Proceed — re-generation of a DRAFT is allowed |
| DRAFT (with `supersedes` field) | Proceed — evolved DRAFT awaiting content; use `reserved_spec_id` as the Spec ID for this run |
| BASELINED | BLOCKED |
| SUPERSEDED | BLOCKED |
| ARCHIVED | BLOCKED |

**Blocked status messages from M7:**

For BASELINED:

```
STATUS: BLOCKED — Lifecycle Guard (A7): specification for <base> is BASELINED.
Generation is not permitted while the specification is at a committed baseline.
Required action: run /specification-lifecycle REOPEN to return the specification to DRAFT, then re-run /generate-specification.
```

For SUPERSEDED:

```
STATUS: BLOCKED — Lifecycle Guard (A7): specification for <base> is SUPERSEDED.
This version cannot be re-generated.
Required action: run /specification-lifecycle EVOLVE on the active baseline to begin a new version, or run /generate-specification for the new DRAFT version.
```

For ARCHIVED:

```
STATUS: BLOCKED — Lifecycle Guard (A7): specification for <base> is ARCHIVED.
This version is retired and cannot be re-generated.
Required action: if new content is needed, ingest new source material under a different base name, or consult a human operator.
```

### M7 Contract Clause Requiring Amendment

The following clause in `docs/commands/generate-specification.md` must be updated as part of M8 implementation:

**Current (Re-generation section, Eligibility):**

> Re-generation of an existing specification is permitted — `/generate-specification` is a structural transformation runtime and re-processing from an unchanged source produces identical output.

**Required amendment:**

> Re-generation is subject to the lifecycle guard. Before writing a draft specification, `/generate-specification` must check whether the lifecycle registry (`WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md`) exists. If it does, and the `spec_state_index` for this `<base>` records a status of BASELINED, SUPERSEDED, or ARCHIVED, generation is blocked and the human actor must use `/specification-lifecycle` to perform the appropriate lifecycle operation first. If the status is DRAFT (evolved) — identified by the presence of a `supersedes` field — generation proceeds and the `reserved_spec_id` from the registry is used as the Spec ID for this run.

**Location:** `docs/commands/generate-specification.md`, Eligibility section (Re-generation paragraph).

---

## BASELINE V2 — EVOLVE_PENDING Mode

This section defines BASELINE operation behavior when `evolve_pending_mode = TRUE` (Step 1.4 detected an active EVOLVE_PENDING for `<base>`).

In BASELINE V2 mode, the target artifact is a **Candidate V2** (not a regular DRAFT). Standard BASELINE eligibility (E1–E7) is replaced by E6 V2 and E7 V2. BASELINE V2 promotes the Candidate V2 to the new active baseline and versions Baseline V1 as SUPERSEDED.

**Source:** EVOLVE Runtime v1 — WP-EVOLVE-1G implementation.

---

### Phase 2 V2 — Candidate V2 Discovery (EV-FR-076, EV-FR-077)

Expected artifact path (from EVOLVE_PENDING event record, Step 1.4):

```text
candidate_v2_path = WORKSPACE_ROOT/specifications/draft/<base>_specification_candidate_v2.md
```

Read the Candidate V2 file. Verify:

1. File exists and is readable at `candidate_v2_path`.
2. First line is exactly `---` (YAML front matter opener).
3. Parse YAML front matter. Verify: `document_type = "CANDIDATE_V2"` and `assembly_status = "CANDIDATE"`.

Also read Baseline V1 from `specifications/stable/<base>_specification.md`. Detect `spec_mode_v1` (STD / LEGACY) using the standard first-line check.

If Candidate V2 absent or unreadable:

```text
STATUS: BLOCKED — Candidate V2 not found at registered path.
Path: <candidate_v2_path>
EVOLVE_PENDING event: <evolve_pending_event.Event_ID>
Manual investigation required: Candidate V2 may have been moved or deleted.
EVOLVE_PENDING remains active.
```

If YAML `document_type ≠ CANDIDATE_V2` or `assembly_status ≠ CANDIDATE`:

```text
STATUS: BLOCKED — Candidate V2 has unexpected front matter.
document_type: <actual>   (expected: CANDIDATE_V2)
assembly_status: <actual> (expected: CANDIDATE)
EVOLVE_PENDING remains active.
```

---

### E6 V2 — Impact-Aware Inference Validation (EV-FR-078 to EV-FR-083)

**Activation:** BASELINE V2 mode only. Replaces the standard E6 gate for this operation. (EV-FR-078)

**Premise (EV-FR-079):** Baseline V1 passed E6 at its own BASELINE time — this is an invariant enforced by the standard E6 gate. Therefore Baseline V1 has zero `INFERRED_DESIGN — Impact Structurel` entries with `Statut = PENDING_VALIDATION`. Preserved sections in Candidate V2 are verbatim copies from Baseline V1 (Phase P5 guarantee — ADR-EVOLVE-003). Therefore no new `PENDING_VALIDATION` entries can exist in preserved sections. **Conclusion:** any `PENDING_VALIDATION` found in Candidate V2 must originate from reconstructed (impacted) sections. Impact-aware property is satisfied by this invariant — no element-level correlation is required.

**Algorithm (EV-FR-080):**

```text
Locate `## Inference Registry` section in Candidate V2.
Locate `### INFERRED_DESIGN — Impact Structurel` subsection.

If absent or contains only `*(aucun élément)*`:
  e6v2_result = PASS   (trivially — no structural design inferences to validate)

Else:
  blocking_elements_v2 = []
  For each row in the subsection table:
    If row["Statut"] = "PENDING_VALIDATION":
      blocking_elements_v2 += { element: row["Élément"], rationale: row["Rationale"] }

  If blocking_elements_v2 non-empty:
    e6v2_result = BLOCK
  Else:
    e6v2_result = PASS
```

**If E6 V2 PASS (EV-FR-081):** proceed to E7 V2.

**If E6 V2 BLOCK (EV-FR-082, EV-FR-083):**

```text
STATUS: BLOCKED — E6 V2: BASELINE V2 REFUSED — INFERENCE GOVERNANCE PENDING

The Candidate V2 contains unvalidated structural design decisions.
(These PENDING_VALIDATION entries originate from EVOLVE-impacted / reconstructed sections.)

Blocking elements:
  - <Élément> — INFERRED_DESIGN structural — <Rationale>
  [one line per element in blocking_elements_v2]

Resolution: validate the decision (set governance_status to USER_VALIDATED in Candidate V2),
or remove the impacted element from the Candidate V2, then re-run /specification-lifecycle BASELINE.
No file operations performed. EVOLVE_PENDING remains active (event: <evolve_pending_event.Event_ID>).
```

Stop. Do not proceed to E7 V2.

---

### E7 V2 — Candidate Validation Review (EV-FR-084 to EV-FR-090)

**Activation:** BASELINE V2 mode only, after E6 V2 PASS. (EV-FR-084)

**Check 1 — YAML front matter completeness (EV-FR-086):**

```text
Required Candidate V2 front matter fields (all must be present and non-empty):
  document_type        : "CANDIDATE_V2"    — already verified in Phase 2 V2
  spec_base            : non-empty
  candidate_version    : non-empty
  source_baseline      : non-empty
  source_baseline_path : non-empty
  evolve_id            : non-empty
  generation_timestamp : non-empty
  assembly_status      : "CANDIDATE"       — already verified in Phase 2 V2
  excluded_elements    : present (value "none" or comma-separated IDs)

If any field absent or empty: check_1_fail = TRUE
```

**Check 2 — Excluded elements absent from body (EV-FR-087):**

```text
Read `excluded_elements` from Candidate V2 YAML front matter.
If excluded_elements = "none": check_2_fail = FALSE (skip)

Else:
  Parse excluded_element_ids (comma-separated list)
  Read Candidate V2 body (content below the second "---")
  For each id in excluded_element_ids:
    If id appears as a standalone row identifier in the Candidate V2 body:
      check_2_fail = TRUE
      integrity_violation = "<id> found in Candidate V2 body (should be absent — DENY/Human-DENIED)"
```

**Check 3 — Body non-empty (EV-FR-088):**

```text
Candidate V2 body = content below the second "---" (YAML closing marker).
If body absent or contains only whitespace: check_3_fail = TRUE
```

**SQF note (EV-FR-102):** SQF re-computation on Candidate V2 is out of scope. Change Set Section 6.2 (SQF Delta V1 → V2) remains as placeholder. E7 V2 focuses on structural validation only.

**E7 V2 result (EV-FR-089, EV-FR-090):**

```text
If check_1_fail OR check_2_fail OR check_3_fail: e7v2_result = BLOCK
Else: e7v2_result = PASS
```

**If E7 V2 BLOCK (EV-FR-090):**

```text
STATUS: BLOCKED — E7 V2: BASELINE V2 REFUSED — CANDIDATE COHERENCE FAILURE

Candidate V2 failed structural coherence validation.

  Check 1 (front matter completeness): <FAIL — missing fields: <list> | PASS>
  Check 2 (excluded elements absent): <FAIL — <integrity_violation> | PASS | SKIP>
  Check 3 (body non-empty):           <FAIL | PASS>

Review and correct Candidate V2 at: <candidate_v2_path>
No file operations performed. EVOLVE_PENDING remains active (event: <evolve_pending_event.Event_ID>).
```

Stop. Do not proceed to Phase 4 V2.

---

### Phase 4 V2 — BASELINE V2 Confirmation (EV-FR-091)

Present the BASELINE V2 confirmation prompt:

```text
═══════════════════════════════════════════════════════════════════
BASELINE V2 — EVOLVE_PENDING Mode

Specification   : <base>
evolve_id       : <evolve_id>

Candidate V2    : <candidate_v2_path>
  aggregate_verdict  : <APPROVED | PARTIAL_DENY>
  candidate_version  : <candidate_version from Candidate V2 YAML>
  source_baseline    : <source_baseline from Candidate V2 YAML>

Current Baseline V1 will be SUPERSEDED:
  specifications/stable/<base>_specification.md
  → specifications/stable/<base>_specification_v<version_sequence>.md

E6 V2 — Impact-Aware Inference Validation : PASS (0 blocking elements)
E7 V2 — Candidate Validation Review       : PASS (all coherence checks passed)

This operation will:
  1. Write SUPERSEDED Baseline V1 to: specifications/stable/<base>_specification_v<version_sequence>.md
  2. Promote Candidate V2 to:         specifications/stable/<base>_specification.md (BASELINED)
  3. Delete Candidate V2 from:        specifications/draft/<base>_specification_candidate_v2.md
  4. Set Change Set evolve_status →   COMPLETE (terminal)

Required input:
  Validator name : [____]
  Baseline date  : [____] (default: <today YYYY-MM-DD>)
  Rationale      : [____] (optional)

Confirm? (yes / cancel / no)
  yes    → proceed with BASELINE V2
  cancel → cancel this EVOLVE operation (evolve_status → CANCELLED — terminal)
  no     → abort; EVOLVE_PENDING remains active; can retry later
═══════════════════════════════════════════════════════════════════
```

Collect `baseline_actor_v2`, `baseline_date_v2` (default today), `baseline_rationale_v2`.

If `no`:

```text
STATUS: BLOCKED — BASELINE V2 aborted by human actor. No changes made.
EVOLVE_PENDING remains active. Re-run /specification-lifecycle BASELINE to retry.
```

If `cancel`: proceed to EVOLVE Cancellation.

If `yes`: proceed to Phase 5 V2.

---

### EVOLVE Cancellation (EV-FR-085, EV-FR-100, EV-FR-101)

Triggered when the operator responds `cancel` at Phase 4 V2 confirmation.

**Step CANCEL-1 — Update Change Set evolve_status → CANCELLED (EV-FR-100):**

Update Section 1 Metadata in Change Set at `<change_set_path>`:

```text
evolve_status: CANCELLED
```

Transition: `<APPROVED | PARTIAL_DENY>` → [operator cancellation during EVOLVE_PENDING] → `CANCELLED` (terminal)

If Change Set update fails: WARNING only. Proceed to CANCEL-2.

**Step CANCEL-2 — Append EVOLVE_CANCELLED event to Lifecycle Registry (EV-FR-101):**

Derive `next_event_id`: scan Event Log for highest EV`<NNN>`; `next_event_id = EV<max+1, zero-padded 3 digits>`.

Append to `## Event Log`:

```markdown
### <next_event_id> — EVOLVE_CANCELLED

**Event ID:** <next_event_id>
**Event Type:** EVOLVE_CANCELLED
**evolve_id:** <evolve_id>
**Base:** <base>
**Date:** <YYYY-MM-DD UTC>
**Actor:** <cancel_actor>
**Reason:** Operator cancellation during EVOLVE_PENDING confirmation.
**EVOLVE_PENDING Event:** <evolve_pending_event.Event_ID>

---
```

Update `## Metadata`: Last Updated = today. Update `## Active State Index`: Last Event = today (Status remains BASELINED).

If registry write fails: CRITICAL — report; stop.

**Step CANCEL-3 — EVOLVE CANCELLED report:**

```text
STATUS: EVOLVE CANCELLED

evolve_id     : <evolve_id>
spec_base     : <base>
evolve_status : CANCELLED (terminal)

Specification <base> remains BASELINED at Baseline V1.
No Baseline V2 was created.
Candidate V2 preserved: <candidate_v2_path>
Change Set: <change_set_path>  (evolve_status: CANCELLED)

Note: EVOLVE_CANCELLED detection in Phase P0.2 of /evolve-specification is not yet implemented.
      To run a new EVOLVE on <base>, manual registry cleanup may be required.
      This is a known gap to be addressed in a future update.
```

---

### Phase 5 V2 — BASELINE V2 Execution (EV-FR-092)

Execute the following steps in sequence. On any blocking failure: stop and report. Do not attempt to rollback completed prior steps.

**BA1v2 — Prepare SUPERSEDED content for Baseline V1 (EV-FR-097):**

Read Baseline V1 (loaded in Phase 2 V2). Apply SUPERSEDED modifications in memory:

```text
For STD (spec_mode_v1 = STD):
  Update YAML field: status → "SUPERSEDED"
  Preserve all content below YAML closing "---" verbatim. Record body_checksum_v1.

For LEGACY (spec_mode_v1 = LEGACY):
  Update: **Status:** SUPERSEDED
  Add:    **Superseded Date:** <baseline_date_v2>
  Add:    **Superseded By:** specifications/stable/<base>_specification.md
  Preserve all content below first "---" verbatim. Record body_checksum_v1.
```

`version_sequence` = current value from `spec_state_index` (Step 1.3).

Write SUPERSEDED content to:

```text
WORKSPACE_ROOT/specifications/stable/<base>_specification_v<version_sequence>.md
```

Verify: file exists; status field = SUPERSEDED; body content matches `body_checksum_v1`.

If write or verify fails:

```text
STATUS: BLOCKED — BA1v2: Cannot write SUPERSEDED Baseline V1.
Path: specifications/stable/<base>_specification_v<version_sequence>.md
Baseline V1 at unsuffixed stable path preserved. No further changes made.
EVOLVE_PENDING remains active.
```

Stop.

**BA2v2 — Delete Baseline V1 from unsuffixed stable path (EV-FR-098):**

Delete `WORKSPACE_ROOT/specifications/stable/<base>_specification.md`.

If deletion fails: WARNING only. Proceed — the BA3v2 write will overwrite it.

**BA3v2 — Prepare and write Baseline V2 content (EV-FR-098):**

```text
From Baseline V1 (already loaded): extract spec_id, title, workspace_id, language, template_version.
version_v2 = "v" + str(version_sequence + 1) + ".0.0"

Build Baseline V2 YAML front matter:
  ---
  spec_id: <spec_id from Baseline V1>
  title: <title from Baseline V1>
  workspace_id: <workspace_id>
  version: <version_v2>
  status: BASELINED
  baseline_date: <baseline_date_v2>
  language: <language from Baseline V1>
  template_version: <template_version from Baseline V1>
  source_baseline: <source_baseline from Candidate V2 YAML>
  evolve_id: <evolve_id>
  ---

Extract Candidate V2 body = content below Candidate V2 YAML closing "---".
Record body_checksum_v2 = identity of this body content.
baseline_v2_content = Baseline V2 YAML header + Candidate V2 body
```

Write `baseline_v2_content` to `WORKSPACE_ROOT/specifications/stable/<base>_specification.md`.

If write fails:

```text
STATUS: BLOCKED — BA3v2: Cannot write Baseline V2.
Path: specifications/stable/<base>_specification.md
State: Baseline V1 SUPERSEDED at _v<version_sequence>.md — manual recovery or restore required.
```

Stop.

**BA4v2 — Verify Baseline V2 (EV-FR-098):**

Read back `WORKSPACE_ROOT/specifications/stable/<base>_specification.md`. Verify:

```text
1. File exists and is readable
2. YAML status: = "BASELINED"
3. YAML baseline_date: = <baseline_date_v2> (non-empty)
4. YAML evolve_id: = <evolve_id> (non-empty)
5. Content below YAML closing "---" matches body_checksum_v2
```

If any check fails:

```text
STATUS: BLOCKED — BA4v2: Baseline V2 verification failed.
Failing check: <specific check>
Manual inspection required: specifications/stable/<base>_specification.md
```

Stop.

**BA5v2 — Delete Candidate V2 from draft/ (EV-FR-096):**

Delete `WORKSPACE_ROOT/specifications/draft/<base>_specification_candidate_v2.md`.

If deletion fails: WARNING only. Baseline V2 in stable/ is authoritative.

```text
WARNING: Candidate V2 deletion failed. Manual cleanup required:
  specifications/draft/<base>_specification_candidate_v2.md
Baseline V2 at specifications/stable/<base>_specification.md is the authoritative active baseline.
```

**BA6v2 — Update Change Set evolve_status → COMPLETE (EV-FR-094):**

Update Change Set Section 1 at `<change_set_path>`:

```text
evolve_status: COMPLETE
```

Transition: `<APPROVED | PARTIAL_DENY>` → [BASELINE V2 confirmed by Lifecycle Runtime] → `COMPLETE` (terminal)

This is the exclusive responsibility of `/specification-lifecycle BASELINE`. (ADR-EVOLVE-004)

If Change Set update fails: WARNING only. Lifecycle Registry BASELINE V2 event is authoritative.

---

### Phase 6 V2 — BASELINE V2 Registry Update (EV-FR-093, EV-FR-099)

All three registry sections are written in a single operation.

Derive `next_event_id`: scan Event Log for highest EV`<NNN>`; `next_event_id = EV<max+1, zero-padded 3 digits>`.

**1. Update `## Metadata`:**

```text
Last Updated    : <baseline_date_v2>
Total Baselines : +1
Active Baselines: (unchanged — 1 before; 1 after; V2 replaces V1)
Superseded      : +1
```

**2. Update `## Active State Index` row for `<base>`:**

```text
Status           : BASELINED
Current Path     : specifications/stable/<base>_specification.md
Version Sequence : <version_sequence + 1>
Last Event       : <baseline_date_v2>
```

Remove optional fields `Supersedes` and `Reserved Spec ID` if present.

**3. Append to `## Event Log`:**

```markdown
### <next_event_id> — BASELINE

**Event ID:** <next_event_id>
**Event Type:** BASELINE
**Spec ID:** <spec_id>
**Base:** <base>
**Date:** <baseline_date_v2>
**Actor:** <baseline_actor_v2>
**Artifact:** specifications/stable/<base>_specification.md
**Rationale:** <baseline_rationale_v2 or —>
**Superseded Artifact:** specifications/stable/<base>_specification_v<version_sequence>.md
**evolve_id:** <evolve_id>
**EVOLVE_PENDING Resolved:** <evolve_pending_event.Event_ID>
**SQF Gate:** NOT_RUN
**SQF Flags:** —

---
```

Note: `SQF Gate: NOT_RUN` — SQF re-computation is out of scope for BASELINE V2 (EV-FR-102). The prior Baseline V1 SQF assessment remains in the Event Log.

If registry write fails:

```text
STATUS: BLOCKED — CRITICAL: BASELINE V2 registry write failed after file operations completed.
File state: specifications/stable/<base>_specification.md — exists (BASELINED)
Registry: NOT updated — manual update required before system state is consistent.
```

---

### Phase 8 V2 — Post-Operation Validation (EV-FR-103)

| Rule | Check | Class |
|------|-------|-------|
| BL2v2 | `specifications/stable/<base>_specification.md` exists, is readable, YAML `status: BASELINED` | BLOCKING |
| BL4v2 | `specifications/stable/<base>_specification_v<version_sequence>.md` exists, status = SUPERSEDED | BLOCKING |
| BL9 | Lifecycle registry exists and is readable | BLOCKING |
| BL11v2 | Baseline V2 body content matches `body_checksum_v2` | BLOCKING |
| BLv2-CS | Change Set `evolve_status = COMPLETE` | WARNING |

If any BLOCKING rule fails: report rule ID and artifact path; stop.

---

### Phase 9 V2 — Completion Reporting (EV-FR-095)

```text
STATUS: BASELINE V2 COMPLETE

Specification  : <base>
Spec ID        : <spec_id>
Version        : <version_v2>
Stable path    : specifications/stable/<base>_specification.md
Baseline Date  : <baseline_date_v2>
Baselined By   : <baseline_actor_v2>
evolve_id      : <evolve_id>

Change Set     : <change_set_path>  (evolve_status: COMPLETE)
Baseline V1 SUPERSEDED : specifications/stable/<base>_specification_v<version_sequence>.md
Candidate V2 DELETED   : specifications/draft/<base>_specification_candidate_v2.md

Quality gates:
  E6 V2 — Impact-Aware Inference Validation : PASS (0 blocking elements)
  E7 V2 — Candidate Validation Review       : PASS (all coherence checks passed)

Post-validation:
  BL2v2 : PASS    BL4v2 : PASS    BL9 : PASS    BL11v2 : PASS

ADR-EVOLVE-004 satisfied: BASELINE V2 created exclusively by /specification-lifecycle BASELINE.
```

---

## Lifecycle Registry Format

### Location

```text
WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md
```

### File Structure

```markdown
# Specification Lifecycle Registry

## Metadata
- Last Updated: <ISO 8601 date>
- Total Baselines: <n>
- Active Baselines: <n>
- Superseded: <n>
- Archived: <n>

---

## Active State Index

| Base | Spec ID | Status | Current Path | Version Sequence | Last Event |
| ---- | ------- | ------ | ------------ | ---------------- | ---------- |
| <base> | <spec_id> | <status> | <path> | <n> | <date> |

---

## Event Log

### EV001 — BASELINE

**Event ID:** EV001
**Event Type:** BASELINE
**Spec ID:** SP001
**Base:** <base>
**Date:** <ISO 8601 date>
**Actor:** <name>
**Artifact:** specifications/stable/<base>_specification.md
**Rationale:** <rationale or —>
**SQF Gate:** <PASS | WARN | BLOCK | NOT_RUN>
**SQF Flags:** <sqf_pass=true | sqf_warn=true | sqf_legacy=true | —>

---
```

### Field Definitions

**Active State Index fields:**

| Field | Description |
|-------|-------------|
| Base | The `<base>` identifier derived from the specification filename |
| Spec ID | The Spec ID assigned at generation time (or reserved at EVOLVE time) |
| Status | Current lifecycle status: DRAFT / BASELINED / SUPERSEDED / ARCHIVED |
| Current Path | Workspace-relative path to the current artifact |
| Version Sequence | Integer counter incremented by each BASELINE; used to assign versioned filename on EVOLVE |
| Last Event | ISO 8601 date of the most recent lifecycle event for this `<base>` |

**Optional Active State Index fields (evolved specs):**

| Field | Description |
|-------|-------------|
| Supersedes | Path to the SUPERSEDED artifact this evolved version was derived from |
| Reserved Spec ID | Spec ID reserved for the next `/generate-specification` run |

**Event Log fields:**

| Field | Required by |
|-------|------------|
| Event ID | All events — format: EV<NNN>, sequential, never reassigned |
| Event Type | All — BASELINE / REOPEN / EVOLVE / ARCHIVE / EVOLVE_PENDING / EVOLVE_CANCELLED |
| Spec ID | All except EVOLVE_PENDING and EVOLVE_CANCELLED |
| Base | All |
| Date | All |
| Actor | All |
| Artifact | All except EVOLVE_PENDING and EVOLVE_CANCELLED — path of the primary affected artifact |
| Rationale | BASELINE — optional |
| Reason | REOPEN, EVOLVE, ARCHIVE, EVOLVE_CANCELLED — required |
| Superseded Artifact | EVOLVE, BASELINE V2 — path of the versioned SUPERSEDED artifact |
| New Spec ID | EVOLVE — reserved_spec_id |
| SQF Gate | BASELINE — optional; PASS / WARN / BLOCK / NOT_RUN [SQF Phase 1] |
| SQF Flags | BASELINE — optional; one of: sqf_pass=true / sqf_warn=true / sqf_legacy=true [SQF Phase 1] |
| evolve_id | EVOLVE_PENDING, EVOLVE_CANCELLED, BASELINE V2 — EVOLVE Runtime identifier |
| Candidate V2 Path | EVOLVE_PENDING — path to Candidate V2 in draft/ |
| Change Set Path | EVOLVE_PENDING — path to Change Set in specifications/evolve/ |
| evolve_status | EVOLVE_PENDING — APPROVED or PARTIAL_DENY at time of event writing |
| aggregate_verdict | EVOLVE_PENDING — APPROVED or PARTIAL_DENY |
| EVOLVE_PENDING Event | EVOLVE_CANCELLED — Event ID of the EVOLVE_PENDING event being cancelled |
| EVOLVE_PENDING Resolved | BASELINE V2 — Event ID of the EVOLVE_PENDING event this BASELINE resolves |

### Write Rules

1. The `## Metadata` section is updated on every write (Last Updated, counts).
2. The `## Active State Index` table is updated in-place (one row per `<base>`; existing row is modified, not appended).
3. The `## Event Log` section is append-only. New event records are added after the last existing record. No prior record is modified.

---

## Failure Handling Summary

| Phase | Step | Failure | Class | Recovery |
|-------|------|---------|-------|----------|
| 0 | Workspace resolution | BLOCKING | BLOCKED — stop; no file ops |
| 1 | Registry absent (REOPEN/EVOLVE/ARCHIVE) | BLOCKING | BLOCKED — stop |
| 2 | Target artifact absent or wrong status | BLOCKING | BLOCKED — stop |
| 2 | `specifications/stable/` absent (BASELINE/EVOLVE) | BLOCKING | BLOCKED — stop |
| 3 | E3 — conflict not CONSOLIDATED | BLOCKING | BLOCKED — stop |
| 3 | E5 — existing BASELINED entry | BLOCKING | BLOCKED — stop |
| 3 | E6 — INFERRED_DESIGN structural PENDING_VALIDATION found | BLOCKING | BLOCKED — list blocking elements; no file ops; draft preserved |
| 3 | E6 Extension — sqf_gate_report.md present but unreadable or inconsistent | BLOCKING | BLOCKED — manual inspection required; draft preserved |
| 3 | E7 — gate_status = BLOCK or PENDING_D7 | BLOCKING | BLOCKED — BASELINE REFUSED; re-run /generate-specification to remediate |
| BASELINE-SQF | sqf_gate_report.md COPY to stable/ fails | WARNING | Non-blocking; BASELINE proceeds; stable/ copy absent |
| 3 | EVOLVE — draft exists for `<base>` | BLOCKING | BLOCKED — stop |
| 3 | ARCHIVE — already ARCHIVED | BLOCKING | BLOCKED — stop |
| 4 | Human cancels | BLOCKING | BLOCKED — no ops; stop |
| BA2 | Write stable fails | BLOCKING | BLOCKED — draft preserved; rollback not needed |
| BA3 | Verify stable fails | BLOCKING | Delete stable (rollback); draft preserved |
| BA4 | Delete draft fails | WARNING | Stable is authoritative; log; continue |
| RO2 | Write draft fails | BLOCKING | BLOCKED — stable preserved |
| RO3 | Verify draft fails | BLOCKING | Delete draft (rollback); stable preserved |
| RO4 | Delete stable fails | WARNING | Draft is authoritative; log; continue |
| EV3 | Write versioned fails | BLOCKING | BLOCKED — unsuffixed stable preserved |
| EV4 | Verify versioned fails | BLOCKING | Delete versioned (rollback); unsuffixed stable preserved |
| EV5 | Delete unsuffixed fails | WARNING | Versioned is SUPERSEDED record; log; continue |
| EV8 | Create DRAFT stub fails | PARTIAL | Record; continue to Phase 6; report PARTIAL |
| 3 | ARCHIVE — target is DRAFT or SUPERSEDED | BLOCKING | BLOCKED — M9-D3; stop; no file ops |
| AR2 | Integrity Gate — missing or conflicting artifact | BLOCKING | BLOCKED — no files moved; registry unchanged |
| AR4 | archive/ write fails | BLOCKING | BLOCKED — no stable/ files deleted; registry unchanged |
| AR5 | archive/ verification fails | CRITICAL | BLOCKED — no stable/ files deleted; registry unchanged; manual inspection |
| AR6 | stable/ deletion fails after 5 retries | CRITICAL | BLOCKED — archive copy exists; manual deletion required; registry unchanged |
| AR7 | stable/ file still present after AR6 | CRITICAL | BLOCKED — archive copy exists; manual cleanup required; registry unchanged |
| 6 | Registry write fails | CRITICAL | Append FAILURE NOTE to artifact; BLOCKED |
| 7 | Generation log write fails | WARNING | Non-blocking; registry is authoritative; continue |
| 8 | BL BLOCKING rule fails | BLOCKING | Report rule ID and artifact; stop |
| 1.4 | EVOLVE_PENDING active + REOPEN / EVOLVE / ARCHIVE attempted | BLOCKING | BLOCKED — run /specification-lifecycle BASELINE to process Candidate V2 |
| 2 V2 | Candidate V2 absent at registered path | BLOCKING | BLOCKED — EVOLVE_PENDING remains active; manual investigation required |
| 2 V2 | Candidate V2 wrong document_type or assembly_status | BLOCKING | BLOCKED — EVOLVE_PENDING remains active; correct Candidate V2 front matter |
| E6 V2 | INFERRED_DESIGN structural PENDING_VALIDATION found in Candidate V2 | BLOCKING | BLOCKED — correct Candidate V2; retry /specification-lifecycle BASELINE |
| E7 V2 | Check 1 — front matter field missing or empty | BLOCKING | BLOCKED — correct Candidate V2 YAML; retry |
| E7 V2 | Check 2 — excluded element found in Candidate V2 body | BLOCKING | BLOCKED — integrity violation; remove excluded element from Candidate V2 |
| E7 V2 | Check 3 — body empty | BLOCKING | BLOCKED — Candidate V2 body absent; regenerate or restore Candidate V2 |
| 4 V2 | Human responds "no" | BLOCKING | BLOCKED — EVOLVE_PENDING remains active; operator can retry later |
| 4 V2 | Human responds "cancel" | CANCELLED | EVOLVE CANCELLED — Change Set CANCELLED; EVOLVE_CANCELLED event written |
| BA1v2 | Write SUPERSEDED Baseline V1 fails | BLOCKING | BLOCKED — unsuffixed Baseline V1 preserved; no changes made |
| BA3v2 | Write Baseline V2 fails | BLOCKING | BLOCKED — Baseline V1 versioned as SUPERSEDED; stable/ unsuffixed may be absent; manual recovery |
| BA4v2 | Baseline V2 verification fails | BLOCKING | BLOCKED — manual inspection of stable/<base>_specification.md required |
| BA5v2 | Candidate V2 deletion from draft/ fails | WARNING | Non-blocking — Baseline V2 at stable/ is authoritative; manual cleanup required |
| BA6v2 | Change Set COMPLETE update fails | WARNING | Non-blocking — Lifecycle Registry BASELINE V2 event is authoritative |
| 6 V2 | Registry write fails after Phase 5 V2 file operations | CRITICAL | BLOCKED — Baseline V2 file OK; registry NOT updated; manual registry update required |
| 8 V2 | BL2v2 / BL4v2 / BL9 / BL11v2 fails | BLOCKING | Report rule ID and path; stop |
| CANCEL-2 | Registry write fails during EVOLVE Cancellation | CRITICAL | BLOCKED — CANCELLED state not recorded in registry; manual recovery required |

---

## Completion States

| State | Condition |
|-------|-----------|
| BASELINE COMPLETE | E6 passed; BA1–BA5 succeeded; BL1, BL2, BL3, BL9, BL10, BL11 passed; registry updated |
| REOPEN COMPLETE | RO1–RO5 succeeded; BL6, BL7, BL9, BL10, BL11 passed; registry updated |
| EVOLVE COMPLETE | EV1–EV9 succeeded; BL4, BL8, BL9, BL10, BL11 passed; registry updated |
| ARCHIVE COMPLETE | AR1–AR7 succeeded; BL9, BL10, BL11 passed; registry updated; all stable/ artifacts absent |
| PARTIAL | Core file operations succeeded; non-critical step (EV8 stub, Phase 7 log) failed |
| BASELINE V2 COMPLETE | E6 V2 PASS; E7 V2 PASS; BA1v2–BA6v2 succeeded; BL2v2, BL4v2, BL9, BL11v2 passed; registry updated; evolve_status = COMPLETE |
| EVOLVE CANCELLED | Operator cancelled at Phase 4 V2; evolve_status = CANCELLED; EVOLVE_CANCELLED event written; no Baseline V2 created; Baseline V1 remains active |
| BLOCKED | Any BLOCKING precondition or CRITICAL failure; rollback attempted where defined |
