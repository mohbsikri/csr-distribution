# Workspace Lifecycle Runtime — Execution Specification

## Purpose

Define the runtime execution procedure for the Workspace Lifecycle Runtime.

The Layer 1 contract (`docs/commands/workspace-lifecycle.md`) defines what the runtime does. This document defines how it executes: the phase sequence, file operations, write ordering, validation procedures, idempotency behavior, failure recovery, and the R4e amendment required across all M1–M9 pipeline commands.

This specification implements Stage 10 — Workspace Lifecycle Management of the CSR pipeline.

---

## Execution Flow

```text
Phase 0  — Repository Discovery
    ↓
Phase 1  — Workspace Creation (CREATE operation)
Phase 2  — Workspace Switching (SWITCH operation)
Phase 3  — Workspace Archival (ARCHIVE operation)
    ↓
Phase 4  — Registry Resolution Model
Phase 5  — Active Workspace Resolution
Phase 6  — Legacy Workspace Handling
Phase 7  — Archived Workspace Handling
Phase 8  — Runtime Version Handling
    ↓
Phase 9  — R4e Amendment
Phase 10 — Validation Rules
Phase 11 — Idempotency
Phase 12 — Failure Scenarios
Phase 13 — Success Conditions
```

Phases 1, 2, and 3 are operation-specific. Phases 4–8 are shared resolution models consumed by all three operations. Phases 9–13 are cross-cutting concerns.

---

## Runtime Version Reference

`CURRENT_RUNTIME_VERSION` is used throughout this specification as a placeholder.

At execution time, read `docs/implementation_status.md` and extract the value from the `## Current Version` section. This value must never be hardcoded. If the file is absent, unreadable, or the section is missing, halt with:

```text
STATUS: BLOCKED — CURRENT_RUNTIME_VERSION unresolvable from docs/implementation_status.md
```

---

## Preconditions

Before any lifecycle operation begins:

| ID | Precondition | Action on Failure |
|----|--------------|-------------------|
| P1 | `docs/commands/workspace-lifecycle.md` exists and is readable | Stop. Report missing L1 contract. |
| P2 | `runtime/workspaces.md` exists and is parseable as a Markdown table | On CREATE: if absent, initialize an empty registry (see Phase 0 Step 0.1a). On other operations: Stop. Report REGISTRY UNAVAILABLE or REGISTRY CORRUPTED. See Phase 0. |
| P3 | `runtime/current_workspace.md` is readable, or absent (absent is handled as null resolver — see Phase 0) | Stop only if unreadable-but-present. Absent is tolerated. |
| P4 | `CURRENT_RUNTIME_VERSION` is resolvable (required for CREATE only) | Stop CREATE. Report BLOCKED per runtime version reference above. |

---

## Phase 0 — Repository Discovery

Phase 0 is executed at the start of every lifecycle operation. It establishes the registry state, resolver state, and drift condition before any operation-specific logic runs.

### Step 0.1 — Locate and Read the Workspace Registry

Read `runtime/workspaces.md`.

If absent AND operation is **CREATE**: proceed to Step 0.1a — Registry Initialization, then continue.

If absent AND operation is NOT CREATE: halt with `REGISTRY UNAVAILABLE — runtime/workspaces.md not found. No lifecycle operation can proceed.`

If unreadable: halt with `REGISTRY UNAVAILABLE — runtime/workspaces.md cannot be read.`

#### Step 0.1a — Registry Initialization (CREATE only, absent registry)

This step runs only when `runtime/workspaces.md` is absent and the operation is CREATE.

1. Create the `runtime/` directory if it does not exist.
2. Write `runtime/workspaces.md` with the following content exactly:

```markdown
# Workspace Registry

| workspace_id | created | status | description | last_active | runtime_version | spec_template_version |
| ------------ | ------- | ------ | ----------- | ----------- | --------------- | --------------------- |
```

3. Emit: `REGISTRY INITIALIZED — runtime/workspaces.md created.`
4. Treat the in-memory workspace list as empty. Continue to Step 0.2.

**Idempotency:** if `runtime/workspaces.md` exists after a failed partial write, do not overwrite it. Read it and continue; Step 0.2 will catch any corruption.

**Safety:** this step creates no project, sets no active workspace, and writes only the registry header. No other file is created by this step.

### Step 0.2 — Parse the Workspace Registry

Parse `runtime/workspaces.md` as a Markdown table. Extract all rows into an in-memory workspace list. Each entry contains:

| Field | Type |
|-------|------|
| `workspace_id` | string |
| `created` | ISO 8601 timestamp string |
| `status` | string: `active`, `paused`, `archived`, or `relocated` |
| `description` | string (may be empty) |
| `last_active` | ISO 8601 timestamp string (may be empty) |
| `runtime_version` | string (may be empty — WR4 WARNING) |
| `spec_template_version` | string: `v1` or `legacy`; may be empty, or the column may be absent, for rows written before issue #55 (see *spec_template_version* below) |

If the file exists but cannot be parsed as a valid Markdown table: halt with `REGISTRY CORRUPTED — runtime/workspaces.md exists but cannot be parsed. Manual inspection and repair required.`

### Step 0.3 — Identify the Registry Active Workspace

Scan the workspace list for entries with `status: active`.

Record:
- `registry_active_count` = number of entries with `status: active`
- `registry_active_workspace_id` = workspace_id of the active entry if exactly one exists; `null` if none; `MULTIPLE` if more than one

### Step 0.4 — Locate and Read the Active Workspace Resolver

Read `runtime/current_workspace.md`.

If absent or empty: record `resolver_workspace_id = null`. Do NOT halt. Proceed to Step 0.5.

If present but unreadable: halt with `RESOLVER UNAVAILABLE — runtime/current_workspace.md cannot be read.`

If present and readable: parse the `workspace_id:` field value. Record as `resolver_workspace_id`.

### Step 0.5 — Drift Detection

Compare `resolver_workspace_id` with `registry_active_workspace_id`.

| Condition | Drift State |
|-----------|-------------|
| `resolver_workspace_id` = `registry_active_workspace_id` (both non-null, matching) | NO DRIFT |
| `resolver_workspace_id` ≠ `registry_active_workspace_id` | DRIFT DETECTED |
| Either value is null and the other is not | DRIFT DETECTED |
| Both are null | NO DRIFT (no active workspace — handled per operation) |
| `registry_active_count` > 1 | INTEGRITY VIOLATION (handled at Phase 4.4) |

If DRIFT DETECTED: record the drift state. Do NOT halt in Phase 0. Individual operations handle drift as follows:

- **SWITCH, CREATE, ARCHIVE**: report drift, continue using `runtime/workspaces.md` as authority.
- **Pipeline commands (M1–M9)**: BLOCKING via R4e (see Phase 9).

### Step 0.6 — Report Drift if Detected

If DRIFT DETECTED: emit before proceeding to the operation phase:

```text
WORKSPACE DRIFT DETECTED
  Resolver (runtime/current_workspace.md): <resolver_workspace_id>
  Registry active entry (runtime/workspaces.md): <registry_active_workspace_id>
  Authority: runtime/workspaces.md wins. Proceeding.
```

---

## Phase 1 — Workspace Creation Execution

### Step 1.1 — workspace_id Format Validation

Assert the provided `workspace_id` input is present and non-empty.

Assert `workspace_id` conforms to the following format:

- Must match the pattern: `[a-z][a-z0-9-]*`
- Must not end with a hyphen.
- Must not contain consecutive hyphens (`--`).
- Must not exceed 64 characters in total length.

If any format constraint fails: halt with `WC1 VIOLATION — workspace_id '<value>' does not conform to the required format. workspace_id must start with a lowercase letter, contain only lowercase letters, digits, and hyphens, must not end with a hyphen, must not contain consecutive hyphens, and must not exceed 64 characters.`

### Step 1.2 — Registry Uniqueness Check

Assert `workspace_id` is not already present in the workspace list from Phase 0.

If already present: halt with `WC2 VIOLATION — workspace_id '<value>' is already registered in runtime/workspaces.md. Workspace creation is not idempotent. Use a distinct workspace_id.`

### Step 1.3 — Directory Pre-existence Check

Assert the path `workspaces/<workspace_id>/` does not already exist as a directory.

If already exists: halt with `WC3 VIOLATION — workspaces/<workspace_id>/ already exists on the filesystem. Resolve the conflict (registry and filesystem are inconsistent) before creating a new workspace with this workspace_id.`

### Step 1.4 — Runtime Version Resolution

Read `docs/implementation_status.md`. Extract `CURRENT_RUNTIME_VERSION` as defined in the Runtime Version Reference.

Record as `workspace_runtime_version`. This value is written to the registry entry at Step 1.8 and must not be hardcoded.

### Step 1.5 — Workspace Root Creation

Create directory `workspaces/<workspace_id>/`.

If creation fails: halt with `DIRECTORY CREATION FAILED — workspaces/<workspace_id>/. No workspace created. No registry entry written.`

### Step 1.6 — Canonical Directory Creation

Create the following 20 directories under `workspaces/<workspace_id>/`, in the order listed. Parent directories must be created before their children.

```text
input/
input/decisions/
input/documents/
input/validations/
knowledge_base/
knowledge_base/conflicts/
knowledge_base/consolidated/
knowledge_base/decisions/
knowledge_base/extracted/
knowledge_base/graph/
knowledge_base/questions/
knowledge_base/raw/
output/
output/generated_questions/
runtime/
specifications/
specifications/archive/
specifications/draft/
specifications/lifecycle/
specifications/stable/
```

For each directory: if creation fails, halt with `DIRECTORY CREATION FAILED — workspaces/<workspace_id>/<path>. Workspace is partially created. Manual cleanup of workspaces/<workspace_id>/ is required before retrying.`

### Step 1.7 — .gitkeep File Creation

Create a `.gitkeep` file in each of the 20 directories listed in Step 1.6.

If any `.gitkeep` write fails: emit `WARNING — GITKEEP WRITE FAILED: workspaces/<workspace_id>/<path>/.gitkeep`. Continue. This is non-blocking.

### Step 1.7b — Theme Selection

Select the CSS theme used by `/export-views` for this workspace's HTML documents. **CREATE applies the standard theme without asking** `[issue #59, 2026-11-10]`: the answer cannot block anything and the theme is changed at any time with `/configure-theme`, so a question here is friction, not safety (Autonomy criterion, `CLAUDE.md`). This holds at every `autonomy` level.

**Step 1.7b.1 — Determine the theme (no prompt)**

| Situation | Selection |
|-----------|-----------|
| Default — the CREATE request says nothing about a theme | `Default` (CSR Professional Blue, `templates/html/themes/default.css`) |
| The CREATE request **explicitly** names an existing workspace whose theme to reuse (e.g. "same theme as `<source_id>`") and `workspaces/<source_id>/theme.css` exists | `Existing workspace theme` from `<source_id>` |
| The CREATE request **explicitly** asks for a custom theme | `Custom` |
| The explicit request cannot be honoured (named workspace has no `theme.css`) | `Default`, and say so in the CREATE summary |

Never ask a theme question during CREATE, and never infer a theme from anything other than an explicit request in the CREATE invocation or the conversation that led to it. Existing workspaces and their `theme.css` / `workspace_config.md` are never read for rewriting, migrated or overwritten by CREATE.

**Step 1.7b.2 — (removed)** The former interactive selection prompt is retired `[issue #59]`. `/configure-theme` is the place to choose or change a theme.

**Step 1.7b.3 — Apply selection**

| Selection | Action |
|-----------|--------|
| Default | Record `theme: default` in workspace_config.md. No theme.css copy needed (export-views falls back to `templates/html/themes/default.css`). |
| Existing workspace theme | Copy `workspaces/<source_id>/theme.css` to `workspaces/<workspace_id>/theme.css`. Record `theme: <source_id>-copy` in workspace_config.md. |
| Custom | Record `theme: custom-pending` in workspace_config.md. No action. Instruct user to run `/configure-theme` to apply a custom theme. |

**Step 1.7b.4 — Write workspace_config.md**

Write `workspaces/<workspace_id>/runtime/workspace_config.md`:

```markdown
# Workspace Configuration

**workspace_id:** <workspace_id>
**primary_language:** (set at first /ingest-source execution)
**theme:** <default | <source_id>-copy | custom-pending>
**theme_path:** (workspaces/<workspace_id>/theme.css if custom/copy; empty if default)
**logo_path:** (empty — set with /configure-theme if needed)
**workspace_description:** <description from CREATE argument, or empty>
**autonomy:** GUIDED
**created:** <ISO 8601 UTC timestamp>
```

If write fails: emit `WARNING — WORKSPACE CONFIG WRITE FAILED: workspaces/<workspace_id>/runtime/workspace_config.md`. Continue. Non-blocking. Export-views will fall back to default theme.

**`autonomy` semantics `[C1, 2026-11-01]`.** Governs how much a session running against this workspace confirms with the human before proceeding, as a *style*, not a safety setting — the invariant below holds at every level, including UNATTENDED.

| Level | Behaviour |
|---|---|
| `GUIDED` (default; written at CREATE) | Current behaviour, unchanged. Confirms routinely. |
| `STANDARD` | Confirms a decision or a destructive action; **announces** everything else rather than asking. |
| `UNATTENDED` | Announces throughout; confirms only what the invariant below never waives. |

**Criterion** (applies at `STANDARD` and `UNATTENDED` to decide what still needs to be asked): *ask only when the answer could be "no", and a "no" would change what gets written.* A question whose answer cannot alter the outcome is not a safety measure — it is friction, and friction wears out: a runtime that asks when nothing is at stake trains the user to approve without reading, which is worse than not asking at all.

**Invariant — unconditional at every level, including `UNATTENDED`:** human validation sessions, governance escalation, and BASELINE always ask. These are precisely the cases the criterion above already selects — a validation decision, a governance verdict, and a baseline commitment are each exactly a point where the answer could be "no" and a "no" changes what gets written — so the invariant is the criterion applied, not an exception carved out of it.

`autonomy` is read, never silently escalated or downgraded by the runtime. Changing it is an explicit edit to `workspace_config.md`, the same way `theme` is changed by `/configure-theme`.

**Backward compatibility.** Every workspace created before this field existed has no `autonomy` line in its `workspace_config.md`. Its absence is read as `GUIDED`, never as an error and never auto-populated by any command other than `/workspace-lifecycle CREATE` — the same precedent `ADR-007` set for a specification baselined before its `Preuve` columns existed: an absent field is not rewritten into an existing artifact, it reads as the conservative default.

### Step 1.8 — Registry Entry Write

Append a new row to `runtime/workspaces.md` with the following field values:

| Field | Value |
|-------|-------|
| `workspace_id` | input workspace_id |
| `created` | current timestamp (ISO 8601 UTC, format: `YYYY-MM-DDTHH:MM:SSZ`) |
| `status` | `paused` |
| `description` | input description, or empty string if not provided |
| `last_active` | empty |
| `runtime_version` | workspace_runtime_version (from Step 1.4) |
| `spec_template_version` | `v1` — always, written explicitly (see *spec_template_version* below) |

`status` must be `paused`. Under no condition may CREATE write `status: active` to the new registry entry.

`spec_template_version` must be `v1`: a new classic project is an STD v1 project (`docs/architecture/STD-Specification-Template-Design.md` §9.4 — *Nouveaux workspaces → STD v1 natif → Obligatoire*). It is written, never left empty: an empty cell is read by `/generate-specification` Step 1.5.1 as the LEGACY fallback, which is exactly how every project created before issue #55 silently ended up LEGACY.

**Registry without the column.** If the registry header has no `spec_template_version` column (a registry written before STD existed), do **not** add the column and do not rewrite the header or any existing row — that would be a migration, and lifecycle operations perform none. Write the six-field row and emit:

```text
WARNING — REGISTRY HAS NO spec_template_version COLUMN
  runtime/workspaces.md predates STD; '<workspace_id>' could not be recorded as v1.
  /generate-specification will route it LEGACY (documented fallback). No header migration performed.
```

WC10 is then reported as this WARNING instead of blocking.

#### spec_template_version — canonical schema `[issue #55, 2026-11-09]`

| Aspect | Rule |
|---|---|
| Admitted values | `v1` (STD canonical template) and `legacy` (7-section legacy template). Nothing else is written by any lifecycle operation. |
| Written by | CREATE (`v1`, Step 1.8) and V2 FORK (`legacy`, Step 15.10). No other lifecycle operation writes or modifies it. |
| Read by | `/generate-specification` Step 1.5.1 — the only consumer. `v1` → STD; `legacy` → LEGACY; empty or column absent → LEGACY with a WARNING. |
| Existing rows | Never migrated, rewritten or re-validated by a lifecycle operation. An empty value or an absent column on a row written before issue #55 is a valid state and keeps the documented LEGACY fallback. WC10 / WV11 apply to the row the operation itself writes, never to pre-existing rows. |
| Changing it | An explicit human decision outside the lifecycle (the optional STD migration documented in `docs/implementation/STD-Implementation-Contract.md`), never a side effect of CREATE, SWITCH, ARCHIVE, REOPEN or V2. |

If write fails: halt with `REGISTRY WRITE FAILED — new workspace entry for '<workspace_id>' could not be written to runtime/workspaces.md. All directories created in Steps 1.5–1.6 require manual cleanup: workspaces/<workspace_id>/`

### Step 1.9 — Post-Creation Validation

Run all WC1–WC10 rules as defined in Phase 10. All must pass (WC10 is a WARNING only in the registry-without-column case of Step 1.8).

WC9 specifically: compare current content of `runtime/current_workspace.md` against its state recorded at Phase 0 Step 0.4. If the content has changed: halt with `WORKSPACE CONTAMINATION — runtime/current_workspace.md was modified during CREATE. This is a prohibited operation. Manual inspection required.`

### Step 1.10 — Completion Reporting

```text
STATUS: WORKSPACE CREATED
  workspace_id:      <value>
  status:            paused
  runtime_version:   <workspace_runtime_version>
  spec_template:     v1
  directory:         workspaces/<workspace_id>/
  theme:             <default | <source_id>-copy | custom-pending>
  config:            workspaces/<workspace_id>/runtime/workspace_config.md
  Activation requires an explicit SWITCH operation.
  To change the theme: /configure-theme
```

---

## Phase 2 — Workspace Switching Execution

### Step 2.1 — Drift at Operation Start

If DRIFT DETECTED in Phase 0: the drift report from Step 0.6 was already emitted. Record `previously_active_workspace_id = registry_active_workspace_id` (from Phase 0 Step 0.3 — the registry authority, not the resolver value).

If NO DRIFT: record `previously_active_workspace_id = registry_active_workspace_id`.

If `registry_active_count` > 1: halt with `REGISTRY INTEGRITY VIOLATION — multiple status:active entries detected in runtime/workspaces.md. Manual correction required before SWITCH can proceed. See Phase 4 Step 4.4.`

### Step 2.2 — Input Validation

Assert target `workspace_id` is present in the operation input. If not: halt with `SWITCH INPUT ERROR — target workspace_id not provided.`

### Step 2.3 — Target Registry Lookup (WS1)

Assert target `workspace_id` is present in the workspace list from Phase 0.

If not found: halt with `WS1 VIOLATION — target workspace_id '<value>' not found in runtime/workspaces.md.`

### Step 2.4 — Target Status Check (WS2)

Read target workspace status from the Phase 0 workspace list.

| Target status | Response |
|---------------|----------|
| `archived` | Present the ARCHIVED interactive prompt (Step 2.4a). Do not block. |
| `active` | Halt with: `STATUS: ALREADY ACTIVE — workspace_id '<value>' is already the active workspace. No state changed.` (This is not a failure — it is a no-op completion.) |
| `paused` | Proceed to Step 2.5. |

### Step 2.4a — ARCHIVED Interactive Detection

When the SWITCH target has `status: archived`, do not block. Present the following interactive prompt:

```text
STATUS: ARCHIVED — CHOOSE ACTION

Workspace: <workspace_id>
Description: <description or "—">
Archived since: <last_active or "—">
Runtime version: <runtime_version>

This workspace is archived. What would you like to do?

  REOPEN  — Reopen for corrections (status: paused, same v1)
             Artifacts are preserved. No new workspace created.
             Run SWITCH after REOPEN to activate.

  V2      — Start a new version (new workspace with lineage to this one)
             Inherited baseline spec copied to the new workspace.
             New sources will be ingested separately.

  cancel  — No action taken.

Enter your choice (REOPEN / V2 / cancel):
```

If the human responds `REOPEN`: execute Phase 14 (REOPEN) on the target `workspace_id`. SWITCH does not proceed.

If the human responds `V2`: prompt for the new workspace ID:
```text
Enter the new workspace_id for the v2 workspace: <new_workspace_id>
Enter a description (optional): <description>
```
Then execute Phase 15 (V2 FORK) with source = target `workspace_id`. SWITCH does not proceed.

If the human responds `cancel` or anything else: report:
```text
STATUS: BLOCKED — Action cancelled by human actor. No changes made.
```
SWITCH does not proceed.

### Step 2.5 — Registry Write (Authoritative State Change)

**This write is the authoritative state transition. It must complete before the resolver is updated.**

Write a single, complete updated `runtime/workspaces.md` containing all existing entries with the following modifications:

- If `previously_active_workspace_id` is non-null: the row for that workspace_id has `status` changed to `paused`. All other fields on that row are unchanged.
- The row for the target workspace_id has `status` changed to `active` and `last_active` updated to the current timestamp (ISO 8601 UTC).

The entire file must be written in a single write operation. Do NOT write partial rows or issue separate writes for each change.

If the write fails: halt with:

```text
SWITCH REGISTRY WRITE FAILED — runtime/workspaces.md could not be updated.
  State before operation: active workspace was <previously_active_workspace_id>.
  No state change has occurred. The operation may be retried safely.
```

### Step 2.6 — Registry Write Verification

Read `runtime/workspaces.md` immediately after Step 2.5.

Verify against the following rules. Any failure halts with `REGISTRY VERIFICATION FAILED — <rule_id>`:

- WS4: target workspace entry has `status: active`.
- WS5: previously active workspace entry (if any) has `status: paused`.
- WS6: exactly one registry entry has `status: active`.
- WS7 (WARNING only): target workspace entry `last_active` is a non-empty timestamp.

### Step 2.7 — Resolver Update (Operational Pointer Update)

Write `runtime/current_workspace.md` with the following content:

```text
workspace_id: <target>
```

If the write fails:

```text
SWITCH RESOLVER WRITE FAILED — runtime/current_workspace.md could not be updated.
  Registry state is correct (authoritative write succeeded at Step 2.5).
  runtime/current_workspace.md is stale and must be corrected.
```

Append the following SWITCH DRIFT NOTE to `runtime/workspaces.md`:

```text
<!-- SWITCH DRIFT NOTE: registry updated workspace_id <target> to active at <timestamp> but resolver write failed. runtime/current_workspace.md must be corrected manually to contain: workspace_id: <target> -->
```

Then halt.

### Step 2.8 — Resolver Write Verification (WS3)

Read `runtime/current_workspace.md`. Assert the content is `workspace_id: <target>`.

If WS3 fails: halt with `RESOLVER VERIFICATION FAILED — WS3. runtime/current_workspace.md does not reflect the expected target workspace after write.`

### Step 2.9 — Artifact Isolation Verification (WS8)

Assert no artifact under any `workspaces/<workspace_id>/` directory has been modified, moved, or deleted during this operation.

If any workspace artifact was modified: halt with `WS8 VIOLATION — workspace artifacts were modified during SWITCH. SWITCH must not touch workspace artifact directories.`

### Step 2.10 — Post-Switch Validation

Run WS1–WS8 as defined in Phase 10. All must pass.

### Step 2.11 — Completion Reporting

```text
STATUS: SWITCH COMPLETE
  Active workspace:   <target>
  Previous workspace: <previously_active_workspace_id> (now paused)
```

If `previously_active_workspace_id` was null (no prior active workspace):

```text
STATUS: SWITCH COMPLETE
  Active workspace:   <target>
  Previous workspace: (none)
```

---

## Phase 3 — Workspace Archival Execution

### Step 3.1 — Input Validation

Assert target `workspace_id` is present in the operation input. If not: halt with `ARCHIVE INPUT ERROR — target workspace_id not provided.`

### Step 3.2 — Target Registry Lookup (WA1)

Assert target `workspace_id` is present in the workspace list from Phase 0.

If not found: halt with `WA1 VIOLATION — target workspace_id '<value>' not found in runtime/workspaces.md.`

### Step 3.3 — Status Check (WA2)

Read target workspace status from the Phase 0 workspace list.

| Target status | Response |
|---------------|----------|
| `active` | Halt with: `WA2 VIOLATION — cannot archive the active workspace. Switch to another workspace first (SWITCH), then archive this workspace.` |
| `archived` | Halt with: `ALREADY ARCHIVED — workspace_id '<value>' is already archived. No operation performed.` (Not a failure.) |
| `paused` | Proceed to Step 3.4. |

### Step 3.4 — Pre-Archival State Snapshot

Record the following before writing:
- `snapshot_resolver_content` = current content of `runtime/current_workspace.md`.
- `snapshot_active_count` = `registry_active_count` from Phase 0.

### Step 3.5 — Registry Write

Write a complete updated `runtime/workspaces.md` containing all existing entries with the following modification:

- The row for the target `workspace_id` has `status` changed to `archived`. All other fields on that row are unchanged. `last_active` is not modified.

If the write fails: halt with `ARCHIVE REGISTRY WRITE FAILED — status:archived could not be written for workspace_id '<value>'. No state change has occurred. The operation may be retried safely.`

### Step 3.6 — Registry Write Verification (WA3)

Read `runtime/workspaces.md` immediately after Step 3.5. Assert target workspace entry has `status: archived`.

If WA3 fails: halt with `REGISTRY VERIFICATION FAILED — WA3.`

### Step 3.7 — Post-Archival Verification

Assert all of the following:

- **WA4**: `workspaces/<workspace_id>/` directory exists and is structurally intact. Verify the workspace root and at least one subdirectory are present. No files may have been removed.
- **WA5**: `runtime/current_workspace.md` content matches `snapshot_resolver_content` from Step 3.4.
- **WA6**: `registry_active_count` in the current registry matches `snapshot_active_count` from Step 3.4.

If any rule fails: halt with `ARCHIVAL VERIFICATION FAILED — <rule_id>.`

### Step 3.8 — Completion Reporting

```text
STATUS: ARCHIVE COMPLETE
  workspace_id: <value>
  status:       archived
  Artifacts preserved at: workspaces/<value>/
  Pipeline commands may not operate on this workspace.
```

---

## Phase 14 — Workspace REOPEN Execution

REOPEN restores an archived workspace to paused state. It is the inverse of ARCHIVE. After REOPEN, the workspace can be activated with SWITCH and processed with pipeline commands.

### Step 14.1 — Input Validation

Assert target `workspace_id` is present. If not: halt with `REOPEN INPUT ERROR — target workspace_id not provided.`

### Step 14.2 — Target Registry Lookup (WRE1)

Assert target `workspace_id` is present in the workspace list from Phase 0.

If not found: halt with `WRE1 VIOLATION — target workspace_id '<value>' not found in runtime/workspaces.md.`

### Step 14.3 — Status Check (WRE2)

Read target workspace status from the Phase 0 workspace list.

| Target status | Response |
|---------------|----------|
| `paused` | Halt with: `STATUS: ALREADY REOPENED — workspace_id '<value>' already has status: paused. No changes made.` |
| `active` | Halt with: `WRE2 VIOLATION — cannot reopen the active workspace. REOPEN targets archived workspaces only.` |
| `archived` | Proceed to Step 14.4. |

### Step 14.4 — Pre-REOPEN State Snapshot

Record before writing:
- `snapshot_resolver_content` = current content of `runtime/current_workspace.md`.
- `snapshot_active_count` = `registry_active_count` from Phase 0.

### Step 14.5 — Confirmation Prompt

Present the following before any write:

```text
Operation: REOPEN
Workspace: <workspace_id>
Description: <description or "—">
Runtime version: <runtime_version>

This operation will:
  1. Set workspace status from archived → paused in runtime/workspaces.md.
  2. Not modify any artifact under workspaces/<workspace_id>/.
  3. Not modify runtime/current_workspace.md.

After REOPEN: run /workspace-lifecycle SWITCH <workspace_id> to activate.

Confirm REOPEN? (yes / no)
```

If the human provides anything other than an explicit "yes": abort. Report:
```text
STATUS: BLOCKED — REOPEN cancelled by human actor. No changes made.
```

### Step 14.6 — Registry Write

Write a complete updated `runtime/workspaces.md` containing all existing entries with the following modification:

- The row for the target `workspace_id` has `status` changed from `archived` to `paused`. All other fields on that row are unchanged.

If the write fails: halt with `REOPEN REGISTRY WRITE FAILED — status:paused could not be written for workspace_id '<value>'. No state change has occurred.`

### Step 14.7 — Registry Write Verification (WRE3)

Read `runtime/workspaces.md` immediately after Step 14.6. Assert target workspace entry has `status: paused`.

If WRE3 fails: halt with `REGISTRY VERIFICATION FAILED — WRE3.`

### Step 14.8 — Post-REOPEN Verification

Assert all of the following:

- **WRE4**: `workspaces/<workspace_id>/` directory exists and is structurally intact. No files may have been removed or modified.
- **WRE5**: `runtime/current_workspace.md` content matches `snapshot_resolver_content` from Step 14.4.
- **WRE6**: Count of `status: active` entries in registry matches `snapshot_active_count` from Step 14.4.

If any rule fails: halt with `REOPEN VERIFICATION FAILED — <rule_id>.`

### Step 14.9 — Completion Reporting

```text
STATUS: REOPEN COMPLETE
  workspace_id: <value>
  status:       paused
  Artifacts preserved at: workspaces/<value>/
  Run /workspace-lifecycle SWITCH <value> to activate.

Validation: WRE1 ✓  WRE2 ✓  WRE3 ✓  WRE4 ✓  WRE5 ✓  WRE6 ✓
```

---

## Phase 15 — V2 FORK Execution

V2 FORK creates a new v2 workspace with explicit lineage to an archived source workspace. The new workspace inherits the BASELINED spec artifacts from the source as its starting baseline. New sources for v2 are ingested separately after the V2 workspace is activated.

### Step 15.1 — Input Validation

Assert `source_workspace_id` and `new_workspace_id` are both present.

If either is absent: halt with `V2 INPUT ERROR — both source_workspace_id and new_workspace_id are required.`

Assert `new_workspace_id` conforms to the workspace_id format (same rules as WC1). If not: halt with `WC1 VIOLATION — new_workspace_id '<value>' does not conform to the required format.`

### Step 15.2 — Source Workspace Validation (WV1)

Assert `source_workspace_id` is present in the workspace list from Phase 0.

If not found: halt with `WV1 VIOLATION — source_workspace_id '<value>' not found in runtime/workspaces.md.`

Read source workspace status.

If not `archived`: halt with `WV2 VIOLATION — V2 FORK requires an archived source workspace. workspace_id '<value>' has status: <status>. Archive the workspace before forking.`

### Step 15.3 — New Workspace Uniqueness Check (WV3)

Assert `new_workspace_id` is not already present in the workspace list from Phase 0.

If already present: halt with `WV3 VIOLATION — new_workspace_id '<value>' is already registered. Use a distinct workspace_id for the v2 workspace.`

### Step 15.4 — New Workspace Directory Check (WV4)

Assert `workspaces/<new_workspace_id>/` does not already exist as a directory.

If already exists: halt with `WV4 VIOLATION — workspaces/<new_workspace_id>/ already exists on the filesystem.`

### Step 15.5 — Runtime Version Resolution

Read `docs/implementation_status.md`. Extract `CURRENT_RUNTIME_VERSION`. Record as `workspace_runtime_version`.

If unresolvable: halt with `STATUS: BLOCKED — CURRENT_RUNTIME_VERSION unresolvable from docs/implementation_status.md`.

### Step 15.6 — Confirmation Prompt

Present the following before any write:

```text
Operation: V2 FORK
Source workspace: <source_workspace_id>  (status: archived)
New workspace:    <new_workspace_id>
Description:      <description or "—">

This operation will:
  1. Create workspaces/<new_workspace_id>/ with the 20 canonical directories.
  2. Create workspaces/<new_workspace_id>/runtime/lineage.md (lineage to source).
  3. Copy specifications/stable/ from source → new workspace (inherited baseline).
  4. Copy specifications/lifecycle/ from source → new workspace (lifecycle history).
  5. Register the new workspace in runtime/workspaces.md with status: paused.
  6. Not modify the source workspace or runtime/current_workspace.md.

The source workspace remains archived. New sources for v2 will be ingested
separately after activating the new workspace with SWITCH.

Confirm V2 FORK? (yes / no)
```

If the human provides anything other than an explicit "yes": abort. Report:
```text
STATUS: BLOCKED — V2 FORK cancelled by human actor. No changes made.
```

### Step 15.7 — New Workspace Directory Creation

Create directory `workspaces/<new_workspace_id>/`.

Create the 20 canonical subdirectories (identical to Phase 1 Step 1.6).

Create `.gitkeep` in each (WARNING only on failure — non-blocking).

### Step 15.8 — Lineage File Creation

Create `workspaces/<new_workspace_id>/runtime/lineage.md` with the following content:

```markdown
# Workspace Lineage

| Field | Value |
|-------|-------|
| workspace_id | <new_workspace_id> |
| version | v2 |
| parent_workspace_id | <source_workspace_id> |
| parent_status | archived |
| fork_date | <current ISO 8601 date> |
| fork_rationale | V2 FORK — new sources will be ingested; inherited baseline spec from parent |
| id_governance | runtime/id_governance.md — IDs BR-NNN/TR-NNN/C-NNN frozen from parent BASELINED spec; new IDs start from next available number |
```

### Step 15.9 — Inherited Baseline Copy

Copy `workspaces/<source_workspace_id>/specifications/stable/` to `workspaces/<new_workspace_id>/specifications/stable/`.

Copy `workspaces/<source_workspace_id>/specifications/lifecycle/` to `workspaces/<new_workspace_id>/specifications/lifecycle/`.

If any copy fails: halt with `V2 COPY FAILED — <source_path> could not be copied to <dest_path>. Partial workspace created at workspaces/<new_workspace_id>/. Manual cleanup required.`

### Step 15.10 — Registry Entry Write

Append a new row to `runtime/workspaces.md`:

| Field | Value |
|-------|-------|
| `workspace_id` | `new_workspace_id` |
| `created` | current timestamp (ISO 8601 UTC) |
| `status` | `paused` |
| `description` | input description, or empty string if not provided |
| `last_active` | empty |
| `runtime_version` | `workspace_runtime_version` (from Step 15.5) |
| `spec_template_version` | `legacy` — always, written explicitly |

`status` must be `paused`. Under no condition may V2 write `status: active`.

`spec_template_version` must be `legacy`. V2 mode is LEGACY by construction — `/generate-specification` Step 1.5.2 forces `template_mode = LEGACY` whenever `runtime/lineage.md` is present — so the registry states what the runtime will actually do instead of leaving it to the empty-value fallback. Writing `legacy` changes no generation behaviour. The source workspace's own value is not read, copied or modified. If the registry has no `spec_template_version` column, apply the same rule as Step 1.8 (six-field row, WARNING, no header migration).

### Step 15.11 — Post-V2 Validation

Verify:
- **WV5**: all 20 canonical subdirectories exist under `workspaces/<new_workspace_id>/`.
- **WV6**: `workspaces/<new_workspace_id>/runtime/lineage.md` exists and contains `parent_workspace_id`.
- **WV7**: `workspaces/<new_workspace_id>/specifications/stable/` contains at least one artifact copied from source.
- **WV8**: new registry entry has `status: paused` and `runtime_version = CURRENT_RUNTIME_VERSION`.
- **WV9**: source workspace registry entry is unchanged (still `status: archived`).
- **WV10**: `runtime/current_workspace.md` is unchanged.
- **WV11**: new registry entry has `spec_template_version: legacy` (WARNING only if the registry has no such column).

### Step 15.12 — Completion Reporting

```text
STATUS: V2 CREATED

Source workspace:  <source_workspace_id>  (archived — unchanged)
New workspace:     <new_workspace_id>
Status:            paused
Runtime version:   <workspace_runtime_version>
Spec template:     legacy (V2 is always LEGACY)
Lineage file:      workspaces/<new_workspace_id>/runtime/lineage.md
Inherited spec:    workspaces/<new_workspace_id>/specifications/stable/

Next steps:
  1. /workspace-lifecycle SWITCH <new_workspace_id>  ← activate v2 workspace
  2. /ingest-source <new_source>                     ← ingest v2 sources
  3. /extract-knowledge → /generate-specification    ← pipeline (full, not selective)

ID governance: runtime/id_governance.md
  Inherited IDs (frozen): <list from lineage>
  New rules start at:     BR-<next>, TR-<next>, C-<next>

Validation: WV1 ✓  WV2 ✓  WV3 ✓  WV4 ✓  WV5 ✓  WV6 ✓  WV7 ✓  WV8 ✓  WV9 ✓  WV10 ✓  WV11 ✓
```

---

## Phase 4 — Workspace Registry Resolution

This phase defines how `runtime/workspaces.md` is parsed and how conflicting registry states are handled. This phase is consumed by Phase 0 and by individual operation phases.

### Step 4.1 — Normal Resolution

Parse `runtime/workspaces.md` as a Markdown table. Extract all rows into the workspace list. Identify the active workspace as the single row where `status = active`.

### Step 4.2 — Single Active Entry (Normal Path)

If exactly one active entry exists: `registry_active_workspace_id` = that workspace_id. Proceed normally.

### Step 4.3 — Zero Active Entries

If no active entry exists: `registry_active_workspace_id = null`.

| Operation | Response |
|-----------|----------|
| CREATE | Allowed. No active workspace required. |
| SWITCH | Allowed. SWITCH establishes the active workspace. |
| ARCHIVE | Allowed. Target must be paused. |
| Pipeline commands (M1–M9) | BLOCKING via R4e Case D. Report: `NO ACTIVE WORKSPACE — registry has no status:active entry. Run SWITCH to designate an active workspace.` |

### Step 4.4 — Multiple Active Entries

If more than one active entry exists: `registry_active_workspace_id = MULTIPLE`.

```text
REGISTRY INTEGRITY VIOLATION
  Multiple entries with status:active detected in runtime/workspaces.md.
  Active workspace_ids: <list all active workspace_ids>
  All lifecycle operations and pipeline commands are blocked until resolved.
```

Recovery: manually edit `runtime/workspaces.md` to ensure exactly one entry has `status: active`. Then run SWITCH to the desired workspace to re-synchronize `runtime/current_workspace.md`.

### Step 4.5 — Workspace Not Found

If a `workspace_id` referenced by an operation (or by `runtime/current_workspace.md`) is not present in the registry: WR5 produces a WARNING; R4a BLOCKING for pipeline commands.

---

## Phase 5 — Active Workspace Resolution

This phase defines all resolution paths when determining which workspace is active. It is consumed by all operations and pipeline commands.

### Step 5.1 — Normal Path

Conditions: `resolver_workspace_id` is non-null; `registry_active_workspace_id` is non-null; they are equal; exactly one active registry entry exists.

Result: `active_workspace_id = resolver_workspace_id = registry_active_workspace_id`. No drift. `WORKSPACE_ROOT = workspaces/<active_workspace_id>/`.

### Step 5.2 — Drift Path

Conditions: `resolver_workspace_id` ≠ `registry_active_workspace_id`; exactly one active registry entry exists.

Authority: `registry_active_workspace_id` is the true active workspace.

| Caller | Response |
|--------|----------|
| SWITCH | Report drift (already done at Step 0.6). Proceed using `registry_active_workspace_id` as authority. |
| CREATE | Report drift. Proceed (CREATE does not require an active workspace). |
| ARCHIVE | Report drift. Proceed. |
| Pipeline commands (M1–M9) | BLOCKING. Report drift via R4e Case B. Do not proceed. Instruct user: `Run SWITCH to correct runtime/current_workspace.md to point to <registry_active_workspace_id>, or SWITCH to a different desired workspace.` |

### Step 5.3 — Missing Resolver Path

Conditions: `runtime/current_workspace.md` is absent or empty; `registry_active_workspace_id` is non-null.

Authority: `registry_active_workspace_id` is the active workspace.

| Caller | Response |
|--------|----------|
| Lifecycle operations | Report: `RESOLVER ABSENT — using registry active workspace: <registry_active_workspace_id>.` Proceed. |
| Pipeline commands | BLOCKING via R4e Case C. Report: `RESOLVER ABSENT — registry identifies <registry_active_workspace_id> as active but runtime/current_workspace.md is absent. Run SWITCH to <registry_active_workspace_id> to restore the resolver.` |

### Step 5.4 — No Active Workspace Path

Conditions: `registry_active_workspace_id = null` (zero active registry entries); `resolver_workspace_id` may be null or non-null.

Response: as defined in Phase 4 Step 4.3.

### Step 5.5 — Missing Registry Path

Conditions: `runtime/workspaces.md` is absent.

Response: `REGISTRY UNAVAILABLE`. Halt all operations. Recovery: restore or reconstruct `runtime/workspaces.md` from workspace directory state.

### Step 5.6 — Corrupted Registry Path

Conditions: `runtime/workspaces.md` exists but cannot be parsed.

Response: `REGISTRY CORRUPTED`. Halt all operations. Recovery: manually inspect and repair the Markdown table structure of `runtime/workspaces.md`.

---

## Phase 6 — Legacy Workspace Handling

### Step 6.1 — Legacy Classification

A workspace is classified as legacy when its `runtime_version` field value in the registry is lower than `CURRENT_RUNTIME_VERSION`.

This classification is computed at read time by version string comparison. It is never written to the registry. A legacy workspace holds `status: paused` or `status: archived`.

If `runtime_version` is empty for a registry entry: emit WR4 WARNING. Classify as non-legacy (the version is unknown; do not assume it is older).

### Step 6.2 — Allowed Operations on Legacy Workspaces

| Operation | Allowed |
|-----------|---------|
| SWITCH (to legacy) | Yes |
| ARCHIVE (legacy) | Yes |
| Artifact reading | Yes |
| Registry inspection | Yes |
| Pipeline command execution (after SWITCH to legacy) | Yes — but pipeline commands may fail if required directories are absent |

### Step 6.3 — Legacy Warning at SWITCH

When SWITCH completes successfully to a legacy workspace (`registry_active_workspace_id.runtime_version < CURRENT_RUNTIME_VERSION`), append the following to the SWITCH COMPLETE report:

```text
WARNING — LEGACY WORKSPACE
  workspace_id '<value>' was created at CSR runtime version <runtime_version>.
  Current CSR runtime version is <CURRENT_RUNTIME_VERSION>.
  This workspace may be missing pipeline directories introduced after its creation version.
  Pipeline commands will fail with standard precondition errors if required directories are absent.
  No automatic directory repair is performed.
  Affected known directories for upgrades from v0.3.0 to current:
    specifications/lifecycle/   (introduced in Milestone 8)
    specifications/archive/     (introduced in Milestone 9)
  Create any missing directories manually before running affected pipeline commands.
```

### Step 6.4 — No Automatic Repair

No lifecycle operation or pipeline command may create, delete, or modify workspace directories in a legacy workspace for the purpose of structural repair or upgrade. Any such operation is a workspace contamination violation.

### Step 6.5 — The `default` Workspace

The `default` workspace (`runtime_version: 0.3.0`, `status: paused`) is a known legacy workspace. Its directory structure predates Milestone 8. It is missing `specifications/lifecycle/` and `specifications/archive/`. It is preserved as-is per Decision D. If switched to, the legacy warning at Step 6.3 lists the missing directories.

---

## Phase 7 — Archived Workspace Handling

### Step 7.1 — Pipeline Command Behavior

All M1–M9 pipeline commands enforce R4b: if the active workspace has `status: archived` in `runtime/workspaces.md`, return:

```text
STATUS: BLOCKED — Workspace Archived: workspace_id '<value>' has status 'archived' and must not be used for active processing.
```

With the M10 authority model, R4b reads `status` from `runtime/workspaces.md`. The `status: archived` value in the registry is the determination; `runtime/current_workspace.md` is used only to resolve the workspace_id.

### Step 7.2 — SWITCH to Archived Workspace

SWITCH targeting an archived workspace no longer blocks with WS2 VIOLATION. Instead, it triggers the interactive ARCHIVED detection at Phase 2 Step 2.4a, offering REOPEN or V2.

Direct operations are also available:
- `REOPEN <workspace_id>` — directly reopens the archived workspace without going through SWITCH.
- `V2 <source_workspace_id> <new_workspace_id>` — directly creates a v2 fork without going through SWITCH.

The only path to an archived workspace appearing as "active" is a direct manual edit of `runtime/current_workspace.md`. This produces R4b BLOCKING on the next pipeline command execution.

### Step 7.3 — Artifact Access

All artifacts in `workspaces/<workspace_id>/` remain readable. No write operation is performed on archived workspace artifacts by any lifecycle operation or pipeline command.

### Step 7.4 — Registry Visibility

The `status: archived` registry entry is permanent within M10. It is not removed, flagged, or hidden. It appears in all registry views.

---

## Phase 8 — Runtime Version Handling

### Step 8.1 — Version Resolution Source

`CURRENT_RUNTIME_VERSION` is always resolved from `docs/implementation_status.md ## Current Version`. No hardcoded version strings are used.

### Step 8.2 — Version Assignment at CREATE

At Step 1.4, `CURRENT_RUNTIME_VERSION` is resolved and recorded as `workspace_runtime_version`. At Step 1.8, this value is written to the `runtime_version` field of the new registry entry.

The `runtime_version` field is set exactly once at creation. No subsequent operation may modify it.

### Step 8.3 — Version Read Behavior

When `runtime_version` is read from a registry entry during any phase:

- It is used for legacy classification in Phase 6 Step 6.1 (comparison against `CURRENT_RUNTIME_VERSION`).
- It is not used to gate, block, or restrict any operation.
- If empty: emit WR4 WARNING and continue. Do not classify as legacy.

### Step 8.4 — No Upgrade Logic

The following operations must not modify the `runtime_version` field on any registry entry under any condition:

- SWITCH
- ARCHIVE
- Any M1–M9 pipeline command

---

## Phase 9 — R4e Amendment

### Step 9.1 — Superseded Behavior

All M1–M9 pipeline commands contain a workspace resolution block implementing R4a–R4e. The current R4e rule reads:

> `only one active entry allowed — WARNING if multiple; Use runtime/current_workspace.md as the authority`

This designation is superseded by the M10 authority model (Decision B). The M10 execution specification defines the replacement behavior below.

### Step 9.2 — Replacement R4e Behavior

R4e must be replaced across all impacted commands with the following case-dispatched logic:

**R4e (M10 revision):**

After reading `runtime/workspaces.md` and `runtime/current_workspace.md`, evaluate:

| Case | Condition | Response |
|------|-----------|----------|
| A — Normal | Exactly one `status:active` entry in registry; its `workspace_id` = `resolver_workspace_id` | No action. Continue. |
| B — Drift | Exactly one `status:active` entry in registry; its `workspace_id` ≠ `resolver_workspace_id` | BLOCKING. `runtime/workspaces.md` is authoritative. Report: `WORKSPACE DRIFT DETECTED — resolver names <resolver_workspace_id>, registry active entry is <registry_active_workspace_id>. Run SWITCH to correct runtime/current_workspace.md before proceeding.` |
| C — Resolver absent | `runtime/current_workspace.md` absent or empty; exactly one `status:active` entry in registry | BLOCKING. Report: `RESOLVER ABSENT — registry identifies <registry_active_workspace_id> as active but runtime/current_workspace.md is absent or empty. Run SWITCH to <registry_active_workspace_id> to restore the resolver.` |
| D — No active workspace | Zero `status:active` entries in registry | BLOCKING. Report: `NO ACTIVE WORKSPACE — registry has no status:active entry. Run SWITCH to designate an active workspace.` |
| E — Multiple active | More than one `status:active` entry in registry | BLOCKING. Report: `REGISTRY INTEGRITY VIOLATION — multiple status:active entries detected. Manual correction of runtime/workspaces.md required.` |

### Step 9.3 — Impacted Commands

The R4e amendment must be applied to the workspace resolution block in each of the following command files:

| Command | File path |
|---------|-----------|
| `/ingest-source` | `.claude/commands/ingest-source.md` |
| `/extract-knowledge` | `.claude/commands/extract-knowledge.md` |
| `/detect-conflicts` | `.claude/commands/detect-conflicts.md` |
| `/generate-questions` | `.claude/commands/generate-questions.md` |
| `/human-validation` | `.claude/commands/human-validation.md` |
| `/consolidate-knowledge` | `.claude/commands/consolidate-knowledge.md` |
| `/generate-specification` | `.claude/commands/generate-specification.md` |
| `/specification-lifecycle` | `.claude/commands/specification-lifecycle.md` |

Additionally, `docs/architecture/workspace_runtime.md` (M4.5 L1 contract) documents the original R4e behavior and must be updated to reference the M10 authority model amendment.

### Step 9.4 — Behavioral Impact Summary

The change from WARNING to BLOCKING for drift conditions (Cases B and C) is intentional. Previously, a pipeline command with a stale resolver could silently operate on the wrong workspace. Under the M10 model, any disagreement between the resolver and the registry halts the pipeline command and surfaces the inconsistency. The user runs a SWITCH to resolve it.

### Step 9.5 — Migration Behavior

The current repository state is consistent: `runtime/current_workspace.md` names `test-e2e`; `runtime/workspaces.md` has `test-e2e` as the single `status: active` entry. No drift exists. The R4e update will be exercised for the first time at M10 E2E validation.

---

## Phase 10 — Validation Rules

All rules are verified as postcondition checks after their respective phase step completes. BLOCKING rules halt the operation with an explicit error report on failure. WARNING rules emit a message and continue.

### Workspace Creation Rules

| Rule | Step | Condition | Classification |
|------|------|-----------|----------------|
| WC1 | 1.1 | `workspace_id` is present, non-empty, and conforms to format `[a-z][a-z0-9-]*`, ≤ 64 chars, no trailing hyphen, no consecutive hyphens | BLOCKING |
| WC2 | 1.2 | `workspace_id` is not already present in `runtime/workspaces.md` | BLOCKING |
| WC3 | 1.3 | `workspaces/<workspace_id>/` did not already exist before the operation | BLOCKING |
| WC4 | 1.8 | `runtime/workspaces.md` write succeeds | BLOCKING |
| WC5 | 1.9 | All 20 canonical subdirectories from Step 1.6 exist under `workspaces/<workspace_id>/` | BLOCKING |
| WC6 | 1.9 | New registry entry is present with all 7 fields (`workspace_id`, `created`, `status`, `description`, `last_active`, `runtime_version`, `spec_template_version`) and all non-optional fields are non-empty (`description` and `last_active` are optional; `spec_template_version` is absent only in the registry-without-column case of Step 1.8) | BLOCKING |
| WC7 | 1.9 | New registry entry has `status: paused` — never `active` | BLOCKING |
| WC8 | 1.9 | New registry entry has `runtime_version` equal to `CURRENT_RUNTIME_VERSION` | BLOCKING |
| WC9 | 1.9 | `runtime/current_workspace.md` content is identical to its state at Phase 0 Step 0.4 | BLOCKING |
| WC10 | 1.9 | New registry entry has `spec_template_version: v1` | BLOCKING (WARNING if the registry has no `spec_template_version` column — Step 1.8) |

### Workspace Switching Rules

| Rule | Step | Condition | Classification |
|------|------|-----------|----------------|
| WS1 | 2.3 | Target `workspace_id` is present in `runtime/workspaces.md` | BLOCKING |
| WS2 | 2.4 | Target workspace has `status: paused` (not archived, not already active) | BLOCKING |
| WS3 | 2.8 | `runtime/current_workspace.md` contains `workspace_id: <target>` after the operation | BLOCKING |
| WS4 | 2.6 | Target workspace registry entry has `status: active` after the registry write | BLOCKING |
| WS5 | 2.6 | Previously active workspace registry entry (if any) has `status: paused` after the registry write | BLOCKING |
| WS6 | 2.6 | Exactly one registry entry has `status: active` after the operation | BLOCKING |
| WS7 | 2.6 | Target workspace `last_active` field is a non-empty timestamp after the registry write | WARNING |
| WS8 | 2.9 | No artifact under any `workspaces/<workspace_id>/` directory was modified, moved, or deleted | BLOCKING |

### Workspace Archival Rules

| Rule | Step | Condition | Classification |
|------|------|-----------|----------------|
| WA1 | 3.2 | Target `workspace_id` is present in `runtime/workspaces.md` | BLOCKING |
| WA2 | 3.3 | Target workspace has `status: paused` at operation start | BLOCKING |
| WA3 | 3.6 | Target workspace registry entry has `status: archived` after the registry write | BLOCKING |
| WA4 | 3.7 | `workspaces/<workspace_id>/` directory and at least one subdirectory are structurally intact; no files removed | BLOCKING |
| WA5 | 3.7 | `runtime/current_workspace.md` content matches pre-archival snapshot | BLOCKING |
| WA6 | 3.7 | Count of `status: active` entries in registry is unchanged from pre-archival snapshot | BLOCKING |

### Workspace REOPEN Rules

| Rule | Step | Condition | Classification |
|------|------|-----------|----------------|
| WRE1 | 14.2 | Target `workspace_id` is present in `runtime/workspaces.md` | BLOCKING |
| WRE2 | 14.3 | Target workspace has `status: archived` at operation start | BLOCKING |
| WRE3 | 14.7 | Target workspace registry entry has `status: paused` after registry write | BLOCKING |
| WRE4 | 14.8 | `workspaces/<workspace_id>/` directory and all contents unmodified | BLOCKING |
| WRE5 | 14.8 | `runtime/current_workspace.md` content matches pre-REOPEN snapshot | BLOCKING |
| WRE6 | 14.8 | Count of `status: active` entries unchanged from pre-REOPEN snapshot | BLOCKING |

### Workspace V2 FORK Rules

| Rule | Step | Condition | Classification |
|------|------|-----------|----------------|
| WV1 | 15.2 | `source_workspace_id` is present in `runtime/workspaces.md` | BLOCKING |
| WV2 | 15.2 | Source workspace has `status: archived` | BLOCKING |
| WV3 | 15.3 | `new_workspace_id` is not already in `runtime/workspaces.md` | BLOCKING |
| WV4 | 15.4 | `workspaces/<new_workspace_id>/` does not already exist | BLOCKING |
| WV5 | 15.11 | All 20 canonical subdirectories exist under `workspaces/<new_workspace_id>/` | BLOCKING |
| WV6 | 15.11 | `workspaces/<new_workspace_id>/runtime/lineage.md` exists with `parent_workspace_id` | BLOCKING |
| WV7 | 15.11 | `workspaces/<new_workspace_id>/specifications/stable/` contains at least one copied artifact | BLOCKING |
| WV8 | 15.11 | New registry entry has `status: paused` and `runtime_version = CURRENT_RUNTIME_VERSION` | BLOCKING |
| WV9 | 15.11 | Source workspace registry entry still has `status: archived` (unchanged) | BLOCKING |
| WV10 | 15.11 | `runtime/current_workspace.md` is unchanged | BLOCKING |
| WV11 | 15.11 | New registry entry has `spec_template_version: legacy` | BLOCKING (WARNING if the registry has no `spec_template_version` column) |

### Workspace Registry Rules

| Rule | Phase | Condition | Classification |
|------|-------|-----------|----------------|
| WR1 | 0.2 | All `workspace_id` values in the workspace list are unique | BLOCKING |
| WR2 | 0.3 | After any lifecycle operation completes: exactly one registry entry has `status: active` | BLOCKING |
| WR3 | 0.5 | `runtime/current_workspace.md` reflects the `workspace_id` of the `status: active` registry entry; drift triggers R4e for pipeline commands, reporting for lifecycle operations | BLOCKING (pipeline) / REPORTED (lifecycle) |
| WR4 | Phase 8 | `runtime_version` is non-empty for all registry entries | WARNING |
| WR5 | Phase 4 | Every `workspace_id` in the registry not marked `relocated` has a corresponding directory under `workspaces/` | WARNING |
| WR6 | 0.2 | Every **non-empty** `spec_template_version` value is `v1` or `legacy`. An empty value or an absent column is **not** a finding: it is the documented pre-#55 state and reads as LEGACY. | WARNING |

---

## Phase 11 — Idempotency

### CREATE

NOT idempotent. Re-invoking CREATE with the same `workspace_id` fails at Step 1.2 (WC2 VIOLATION) because the workspace_id is already in the registry. Re-invoking CREATE with the same `workspace_id` when only the directory exists (but no registry entry) fails at Step 1.3 (WC3 VIOLATION).

Workspace creation is not a "create if not exists" operation. This is by contract design: each CREATE is a distinct, traceable act recorded in the registry with its own `created` timestamp. To recreate a workspace with the same `workspace_id`, the prior registry entry and directory must be removed manually.

### SWITCH

Effectively idempotent when the target workspace is already active. Invoking SWITCH with the `workspace_id` of the current active workspace halts at Step 2.4 with `STATUS: ALREADY ACTIVE`. No state change occurs, no write operations are performed.

After a SWITCH completes, invoking SWITCH again to the same target workspace produces `STATUS: ALREADY ACTIVE` — same no-op behavior.

### ARCHIVE

Effectively idempotent when the target workspace is already archived. Invoking ARCHIVE on an already-archived workspace halts at Step 3.3 with `ALREADY ARCHIVED`. No state change occurs, no write operations are performed.

---

## Phase 12 — Failure Scenarios

### F1 — Registry Drift (resolver and registry disagree)

Detection: Phase 0 Step 0.5.

For lifecycle operations: drift is reported at Step 0.6; operation proceeds with registry as authority.

For pipeline commands: BLOCKING via R4e Case B or Case C.

Recovery: run SWITCH to the desired active workspace. SWITCH detects drift (Step 2.1), reports it, proceeds using the registry, and writes the correct `workspace_id` to `runtime/current_workspace.md`.

### F2 — Missing Workspace Directory

Detection: WR5 WARNING during Phase 0 Step 0.2, or pipeline command precondition failure.

Cause: registry entry exists but `workspaces/<workspace_id>/` directory is absent (e.g., was deleted outside the runtime).

Impact: pipeline commands will fail with standard directory-not-found precondition errors.

Recovery: manually recreate the workspace directory structure. Alternatively, archive the workspace registry entry and create a new workspace.

### F3 — Duplicate Active Workspaces (Multiple `status: active` Entries)

Detection: Phase 4 Step 4.4.

Response: `REGISTRY INTEGRITY VIOLATION`. All operations halt.

Recovery: manually edit `runtime/workspaces.md` to set exactly one entry to `status: active` and all others to `status: paused` or `status: archived` as appropriate. Then run SWITCH to re-synchronize `runtime/current_workspace.md` with the registry.

### F4 — Archived Workspace Encountered via SWITCH

Detection: Step 2.4 — SWITCH target has `status: archived`.

Response: interactive ARCHIVED prompt at Step 2.4a (no longer a violation). User chooses REOPEN or V2.

Recovery: no recovery needed — this is a normal interactive path, not a failure.

### F5 — CREATE Partial Failure (Directories Created, Registry Write Fails)

Detection: registry write failure at Step 1.8.

Response: halt. Report all directories created in Steps 1.5–1.6 as requiring manual cleanup.

Recovery: manually remove `workspaces/<workspace_id>/`. Retry CREATE.

### F6 — SWITCH Registry Write Succeeds, Resolver Write Fails

Detection: Step 2.7 resolver write failure.

State after failure: registry is correct (authoritative); `runtime/current_workspace.md` is stale; SWITCH DRIFT NOTE appended to `runtime/workspaces.md`.

Recovery path A: manually write `workspace_id: <target>` to `runtime/current_workspace.md`.

Recovery path B: re-run SWITCH to the same target. Phase 0 will detect drift (resolver still stale), Step 0.6 will report it, Step 2.1 will record previously active as the registry-authoritative active, Step 2.4 will find `status: active` → STATUS: ALREADY ACTIVE — no write needed except the resolver. The resolver write will be attempted again.

Note on Path B: because WS2 halts on `status: active`, a second SWITCH to the same target returns ALREADY ACTIVE without re-attempting writes. Recovery Path A is the direct resolution.

### F7 — SWITCH Partial Registry Write (Registry File Write Not Complete)

Detection: WS4, WS5, or WS6 failures at Step 2.6.

Response: halt with `REGISTRY VERIFICATION FAILED`. Append SWITCH FAILURE NOTE to `runtime/workspaces.md` if possible.

Recovery: manually inspect `runtime/workspaces.md`. Restore the correct single-active-entry state. Run SWITCH to re-synchronize.

### F8 — Legacy Workspace Pipeline Failures

Detection: standard pipeline command precondition errors after SWITCH to a legacy workspace.

Cause: required directories missing from legacy workspace (e.g., `specifications/lifecycle/`).

Recovery: manually create the missing directory in the legacy workspace. No structural repair is performed by the runtime.

### F9 — Corrupted Registry

Detection: Phase 0 Step 0.2 parse failure.

Response: `REGISTRY CORRUPTED`. All operations halt.

Recovery: manually inspect and repair the Markdown table structure of `runtime/workspaces.md`. Verify each row has exactly 6 pipe-delimited fields.

### F10 — workspace_id Format Violation

Detection: Step 1.1.

Response: `WC1 VIOLATION` with format description.

Recovery: retry CREATE with a conforming `workspace_id` (lowercase letter start, lowercase alphanumeric and hyphens only, no trailing hyphen, no consecutive hyphens, ≤ 64 characters).

---

## Phase 13 — Success Conditions

CREATE is complete when:
- WC1–WC10 all pass.
- `workspaces/<workspace_id>/` exists with all 20 canonical subdirectories from Step 1.6.
- Registry entry has `status: paused` and `runtime_version = CURRENT_RUNTIME_VERSION`.
- `runtime/current_workspace.md` is unchanged.
- `STATUS: WORKSPACE CREATED` is reported.

SWITCH is complete when:
- WS1–WS8 all pass (WS7 as WARNING is acceptable).
- Registry reflects `status: active` for target, `status: paused` for previously active.
- `runtime/current_workspace.md` contains `workspace_id: <target>`.
- No workspace artifacts modified.
- `STATUS: SWITCH COMPLETE` is reported. (Or `STATUS: ALREADY ACTIVE` for the no-op case.)

ARCHIVE is complete when:
- WA1–WA6 all pass.
- Registry reflects `status: archived` for target.
- `workspaces/<workspace_id>/` is structurally intact.
- `runtime/current_workspace.md` is unchanged.
- `STATUS: ARCHIVE COMPLETE` is reported.

REOPEN is complete when:
- WRE1–WRE6 all pass.
- Registry reflects `status: paused` for target (was `archived`).
- `workspaces/<workspace_id>/` is structurally intact and unmodified.
- `runtime/current_workspace.md` is unchanged.
- `STATUS: REOPEN COMPLETE` is reported.

V2 FORK is complete when:
- WV1–WV11 all pass.
- `workspaces/<new_workspace_id>/` exists with all 20 canonical directories.
- `workspaces/<new_workspace_id>/runtime/lineage.md` present with parent reference.
- `workspaces/<new_workspace_id>/specifications/stable/` contains inherited baseline.
- New registry entry has `status: paused`.
- Source workspace registry entry unchanged (`status: archived`).
- `runtime/current_workspace.md` is unchanged.
- `STATUS: V2 CREATED` is reported.

---

## Layer Consistency Audit

Verification that every L1 contract section is correctly implemented in this L2 specification.

| L1 Section | L2 Coverage | Status |
|------------|-------------|--------|
| Workspace Lifecycle Model — 3 states and transitions | Phases 1, 2, 3 implement all transitions. Phase 11 covers idempotent re-invocation. | ✓ |
| Activation Principle — CREATE never activates | Step 1.8 prescribes `status: paused` only. WC7 verifies. STATUS: ALREADY ACTIVE at Step 2.4 prevents no-op re-activation. | ✓ |
| SWITCH write ordering — registry before resolver | Phase 2 explicitly sequences Step 2.5 (registry) before Step 2.7 (resolver). F6 defines behavior when resolver write fails after registry write succeeds. | ✓ |
| Authority model — workspaces.md wins | Phase 0 Step 0.5, Phase 5 Steps 5.1–5.3, Phase 9 R4e revision. Registry is always consulted before resolver in all resolution paths. | ✓ |
| Registry Invariants WR1–WR6 | Phase 10 maps each rule to its detection step and classification. | ✓ |
| Workspace Creation Contract — all postconditions | WC1–WC10 in Phase 10 cover all postconditions. | ✓ |
| Workspace Switching Contract — all postconditions | WS1–WS8 in Phase 10 cover all postconditions. | ✓ |
| Workspace Archival Contract — all postconditions | WA1–WA6 in Phase 10 cover all postconditions. | ✓ |
| Legacy Workspace Contract | Phase 6, including the `default` workspace specific note at Step 6.5. | ✓ |
| Read-Only Archive Contract | Phase 7 — R4b enforcement, SWITCH rejection, artifact read access, registry visibility. | ✓ |
| runtime_version semantics | Phase 8 — traceability assignment at CREATE, no modification thereafter, no compatibility gate. | ✓ |
| Active Workspace Resolver Contract | Phase 0 (discovery), Phase 5 (all resolution paths), Phase 9 R4e (cross-command enforcement). | ✓ |
| R4e Cross-command update (OB4) | Phase 9 — superseded behavior defined, replacement defined, impacted command list enumerated, behavioral impact summarized, migration behavior noted. | ✓ |
| L1 Success Criteria SC1–SC4, SC8–SC9 | Phase 13 covers operation-level success conditions. SC1 (CREATE), SC2 (SWITCH), SC3 (ARCHIVE), SC4 (all validation rules pass), SC8 (existing commands remain functional — addressed by R4e migration), SC9 (validation rules enumerated in Phase 10). | ✓ |
| L1 Success Criteria SC5 (archived workspace blocks pipeline) | Phase 7 Step 7.1 defines R4b enforcement behavior. | ✓ |
| L1 Success Criteria SC6 (A7 guard live validation) | The A7 guard is in the M7 command, not the workspace lifecycle runtime. It is a success criterion for M10 E2E validation, not for this specification. Noted below under Findings. | OBSERVATION |
| L1 Success Criteria SC7 (fresh workspace E2E) | E2E validation is a test procedure, not an execution behavior. Delegated to the M10 E2E validation procedure. Noted below. | OBSERVATION |
| L1 Risks R-B1 (workspace_id collision) | Phase 12 F5 — partial failure handling with recovery guidance. Step 1.2 and 1.3 are pre-creation blockers. | ✓ |
| L1 Risks R-B3 (SWITCH partial write) | Phase 12 F6 and F7 — resolver and registry partial write scenarios both handled. | ✓ |

---

## Findings

### BLOCKING

None. No L1–L2 inconsistencies that block approval.

### NON-BLOCKING

| ID | Finding |
|----|---------|
| NB1: Single-file write atomicity | Step 2.5 specifies that the registry update must be a "single write operation." On most file systems, file writes are not transactional. A crash mid-write can produce a partially written file. This specification defines the intent (single atomic write); L4 must acknowledge that true atomicity requires write-to-temp-then-rename semantics if the underlying platform demands it. This is an implementation-level concern and does not affect the contract. |
| NB2: WS7 (WARNING) is uncheckable in some recovery paths | Step 2.6 verifies WS7 (last_active updated) immediately after the registry write. In F6 (resolver write failure), a second SWITCH attempt returns ALREADY ACTIVE and does not re-verify WS7. The last_active value from the first successful registry write is already correct; the WARNING is irrelevant in the recovery path. No action needed. |

### OBSERVATIONS

| ID | Observation |
|----|-------------|
| OB1: SC6 (A7 guard) is outside this specification's scope | SC6 requires a live invocation of `/generate-specification` against a BASELINED workspace to confirm STATUS: BLOCKED. This tests M7's cross-command guard, not the workspace lifecycle runtime. It is a required E2E validation activity, not an execution behavior defined here. |
| OB2: SC7 (fresh workspace E2E) corpus design is delegated | The E2E corpus requires at minimum one AMBIGUITY, one GAP, and one CONTRADICTION conflict. The corpus construction procedure is an E2E test procedure concern, not an execution specification concern. |
| OB3: `docs/architecture/workspace_runtime.md` update | Phase 9.3 includes this file as requiring an R4e amendment update. This is a documentation update to the M4.5 L1 contract, not a behavioral change to any command. |
| OB4: WR5 (WARNING) depends on filesystem access | WR5 checks that every registry `workspace_id` not marked `relocated` has a corresponding directory. A `relocated` entry is skipped by design (2026-11-01) -- its directory living outside `workspaces/` is the point, not a drift. This check requires filesystem access for every registered workspace, which may be slow for large registries. The WARNING classification is appropriate — this is a consistency advisory, not a blocking gate. |

---

## Final Recommendation

The M10 Layer 2 Execution Specification is **ready for approval**.

**Coverage is complete:**

- All three operations (CREATE, SWITCH, ARCHIVE) have fully specified execution phases with step-level precision, write ordering, verification steps, and failure handling.
- All L1 postconditions are mapped to numbered validation rules with execution step references.
- The authority model (Decision B) is implemented at every applicable resolution path (Phase 0, Phase 5, Phase 9).
- The activation principle (Decision A) is enforced at Step 1.8 (prescriptive `status: paused`), WC7 (verification), and Step 2.4 (ALREADY ACTIVE no-op).
- The R4e amendment is fully defined: superseded behavior documented, replacement behavior specified for all five cases, impacted command list enumerated.
- Idempotency behavior is defined for all three operations.
- Twelve failure scenarios are specified with detection, response, and recovery paths.

**Two NON-BLOCKING findings** (NB1 and NB2) are implementation-level concerns delegated to L4.

**Four OBSERVATIONS** are noted; none require changes to this specification.

L3 (prompt template) may proceed once this specification is approved.
