# Workspace Runtime Refactor — Prompt Template

## Section 1 — Mission

You are executing Milestone 4.5 — Workspace Runtime Refactor for the Cognitive Specification Runtime.

Your objective is to transform the repository from a flat-path model (where all artifacts share root-level directories) to a workspace-scoped model (where each workspace owns a dedicated directory subtree under `workspaces/<workspace_id>/`).

You must follow the four-layer architecture precisely:

1. **Layer 1 Contract:** `${CLAUDE_PLUGIN_ROOT}/docs/architecture/workspace_runtime.md`
2. **Layer 2 Execution Specification:** `${CLAUDE_PLUGIN_ROOT}/docs/architecture/workspace_runtime_execution.md`
3. **Layer 3 Prompt Template (this document):** `${CLAUDE_PLUGIN_ROOT}/templates/architecture/workspace_runtime_prompt.md`
4. **Layer 4 Claude Command:** `.claude/commands/workspace-runtime-refactor.md`

The repository is the source of truth. All decisions must be grounded in files on disk, not in conversation context.

---

## Section 2 — Preconditions

Verify all preconditions before taking any action.

### Precondition 0 — Specification Layers on Disk

All four specification layers must exist as files on disk.

Conversation context is not a substitute for files on disk.

Read each file and confirm it is present and readable before proceeding.

### Precondition 1 — Runtime Version Resolvable

`${CLAUDE_PLUGIN_ROOT}/docs/implementation_status.md` must exist and the section `## Current Version` must be readable.

Extract `CURRENT_RUNTIME_VERSION` from this file. Never hardcode a version value.

### Precondition 2 — Repository Structure Valid

The repository root must contain the expected top-level directories as defined in `CLAUDE.md`.

### Precondition 3 — Control Files Absent or Valid

If `runtime/current_workspace.md` exists, read and report its content before proceeding.

If `runtime/workspaces.md` exists, read and report its content before proceeding.

### Precondition 4 — Artifacts Available for Migration

Read `${CLAUDE_PLUGIN_ROOT}/docs/architecture/workspace_runtime_execution.md` Phase 3 — Artifact Migration to obtain the complete artifact migration mapping.

Verify that each source artifact listed in Phase 3 exists at its source path.

### Precondition 5 — Workspace Root Absent

Verify that `workspaces/default/` does not already exist, or, if it does, read and report its current state before proceeding.

---

## Section 3 — Mandatory Inputs

Before execution, read and assimilate the following files:

| File | Purpose |
| ---- | ------- |
| `${CLAUDE_PLUGIN_ROOT}/docs/architecture/workspace_runtime.md` | Layer 1 Contract — workspace model and principles |
| `${CLAUDE_PLUGIN_ROOT}/docs/architecture/workspace_runtime_execution.md` | Layer 2 Execution Specification — step-by-step procedure |
| `${CLAUDE_PLUGIN_ROOT}/docs/implementation_status.md` | Runtime version source |
| `CLAUDE.md` | Repository rules and area definitions |
| `${CLAUDE_PLUGIN_ROOT}/docs/runtime_engineering_method.md` | Four-layer methodology and STATUS protocol |
| `runtime/current_workspace.md` | Current workspace selector (if it exists) |
| `runtime/workspaces.md` | Workspace registry (if it exists) |

Do not proceed past Section 3 until all readable inputs have been assimilated.

---

## Section 4 — Workspace Resolution

Resolve the active workspace before any file operation.

### R1 — Read Current Workspace File

Read `runtime/current_workspace.md`.

Parse the `workspace_id` value from the line:

```text
workspace_id: <value>
```

### R2 — Build Workspace Root

Construct:

```text
WORKSPACE_ROOT = workspaces/<workspace_id>/
```

This is the root path for all workspace-scoped file operations.

### R3 — Verify Workspace Root Exists

Confirm the `WORKSPACE_ROOT` directory exists.

If it does not exist, stop and report:

```text
STATUS: BLOCKED — Workspace Root Not Found: workspaces/<workspace_id>/
```

### R4 — Validate Registry Entry

Read `runtime/workspaces.md` and locate the row where `workspace_id` matches the value from R1.

#### R4a — Workspace ID Present in Registry

If no matching row is found:

```text
STATUS: BLOCKED — Workspace Drift Detected: workspace_id '<value>' not found in runtime/workspaces.md
```

Stop execution.

#### R4b — Status Field is Active

If the matching row `status` is `archived`:

```text
STATUS: BLOCKED — Workspace Archived: workspace_id '<value>' has status 'archived' and must not be used for active processing
```

Stop execution.

If the matching row `status` is `paused` or `completed`:

```text
STATUS: WARNING — Workspace Drift Detected: registry status is '<status>' for workspace_id '<value>', expected 'active'
```

Proceed with caution and document the discrepancy.

#### R4c — runtime_version Field Present

If the `runtime_version` field is empty or absent in the matching row:

```text
STATUS: WARNING — Registry Entry Incomplete: runtime_version missing for workspace_id '<value>'
```

#### R4d — last_active Field Present

If the `last_active` field is empty or absent in the matching row:

```text
STATUS: WARNING — Registry Entry Incomplete: last_active missing for workspace_id '<value>'
```

#### R4e — Single Active Entry

If more than one row in the registry has `status: active`:

```text
STATUS: WARNING — Workspace Drift Detected: multiple rows with status 'active' in runtime/workspaces.md
```

Use `runtime/current_workspace.md` as the authority. Continue with the workspace_id from R1.

### R5 — Confirm Resolution

Report:

```text
Active workspace: <workspace_id>
WORKSPACE_ROOT: workspaces/<workspace_id>/
```

### R6 — Workspace Isolation Enforcement

Every file operation must use a path prefixed with `WORKSPACE_ROOT`.

Shared exception paths (not workspace-scoped):

- `runtime/current_workspace.md`
- `runtime/workspaces.md`
- `docs/`
- `templates/`
- `.claude/`

Before every file operation, check that the target path is either prefixed with `WORKSPACE_ROOT` or is on the exception list. If neither condition is met, stop and report a workspace contamination violation (see Section 10).

### R7 — Path Construction

Construct all artifact paths as:

```text
WORKSPACE_ROOT + <relative path within workspace>
```

Example:

```text
workspaces/default/knowledge_base/extracted/test_source_knowledge.md
```

### Architectural Limitation (MVP)

The MVP maintains two mechanisms for tracking the active workspace:

1. `runtime/current_workspace.md` — the authority for workspace resolution
2. `runtime/workspaces.md` — the registry with `status` field

These can drift. The checks R4a–R4e detect drift and report it. They do not auto-correct it. Drift is a human-resolvable condition. The runtime uses `runtime/current_workspace.md` as the authority in all cases.

---

## Section 5 — Workspace Isolation

**Workspace isolation is a hard rule, active throughout the entire execution.**

No file operation may target a path outside `WORKSPACE_ROOT` unless that path is on the shared exception list defined in R6.

Before every file read or write operation:

1. Determine the target path.
2. Check if it is prefixed with `WORKSPACE_ROOT`.
3. If not prefixed, check if it is on the shared exception list.
4. If neither: stop immediately, report workspace contamination, and do not proceed with the operation.

This check applies to every operation in every phase without exception.

---

## Section 6 — Migration Rules

Migration copies artifacts from flat-path locations to workspace-scoped locations.

### Requirements

- Migration is COPY ONLY. Source files are never deleted or modified.
- Content integrity must be verified after each copy.
- Each copy is verified individually before proceeding to the next.
- A failed copy stops execution for that artifact. Failures are reported explicitly.

### Migration Procedure

**M1** — Verify the source file exists.

**M2** — Read the full content of the source file.

**M3** — Write the content to the destination path.

**M4** — Verify the destination file exists and content matches the source.

**M5** — Confirm the source file is still present and unmodified.

Read the complete artifact migration mapping from `${CLAUDE_PLUGIN_ROOT}/docs/architecture/workspace_runtime_execution.md` Phase 3 — Artifact Migration before executing any copy operation.

---

## Section 7 — Implementation Sequence

Execute the following phases in order. Do not proceed to the next phase until the current phase STATUS gate is reached.

### Phase 1 — Workspace Runtime Infrastructure Creation

Create `runtime/current_workspace.md` if it does not exist.

Create `runtime/workspaces.md` if it does not exist. Populate the `default` registry entry with `CURRENT_RUNTIME_VERSION` (read from `${CLAUDE_PLUGIN_ROOT}/docs/implementation_status.md`).

Use the exact file content specified in `${CLAUDE_PLUGIN_ROOT}/docs/architecture/workspace_runtime_execution.md` Phase 1.

**Gate:** `STATUS: PHASE 1 COMPLETE`

### Phase 2 — Default Workspace Directory Creation

Create all workspace subdirectories under `workspaces/default/`.

Create `.gitkeep` files in all directories that will be empty after migration.

Use the directory list from `${CLAUDE_PLUGIN_ROOT}/docs/architecture/workspace_runtime_execution.md` Phase 2.

**Gate:** `STATUS: PHASE 2 COMPLETE`

### Phase 3 — Artifact Migration

Copy each artifact using the M1–M5 procedure.

Use the migration mapping table from `${CLAUDE_PLUGIN_ROOT}/docs/architecture/workspace_runtime_execution.md` Phase 3.

**Gate:** `STATUS: PHASE 3 COMPLETE`

### Phase 4 — Workspace Path Resolution

Perform workspace resolution steps R1–R7 against the newly created workspace.

Validate all R4a–R4e registry checks pass.

**Gate:** `STATUS: PHASE 4 COMPLETE — INFRASTRUCTURE VALID`

### Phase 5 — Existing Command Refactor

Update all four runtime commands to resolve paths relative to `WORKSPACE_ROOT`.

Add workspace resolution (R1–R7) at the start of each command.

Add workspace isolation enforcement (R6) to each command.

Use the per-command path tables from `${CLAUDE_PLUGIN_ROOT}/docs/architecture/workspace_runtime_execution.md` Phase 5.

**Gate:** `STATUS: PHASE 5 COMPLETE`

### Phase 6 — Documentation Refactor

Apply all BLOCKING documentation updates listed in `${CLAUDE_PLUGIN_ROOT}/docs/architecture/workspace_runtime_execution.md` Phase 6.

**Gate:** `STATUS: PHASE 6 COMPLETE`

### Phase 7 — Deprecation Of Old Root-Level Runtime Areas

Create `DEPRECATED.md` files in all deprecated flat-path directories.

Use the deprecation content from `${CLAUDE_PLUGIN_ROOT}/docs/architecture/workspace_runtime_execution.md` Phase 7.

**Gate:** `STATUS: PHASE 7 COMPLETE`

### Phase 8 — Validation Strategy

Execute all validation checks from `${CLAUDE_PLUGIN_ROOT}/docs/architecture/workspace_runtime_execution.md` Phase 8:

- 8.1 Infrastructure Validation
- 8.2 Migration Validation
- 8.3 Command Validation
- 8.4 End-to-End Validation

**Final Gate:** `STATUS: WORKSPACE RUNTIME E2E VALIDATED`

---

## Section 8 — Command Refactor Rules

When updating each command file, apply the following rules:

### Workspace Resolution Block

Insert the following block at the start of each command, before any artifact path is referenced:

```text
Step W1: Read runtime/current_workspace.md and parse workspace_id.
Step W2: Build WORKSPACE_ROOT = workspaces/<workspace_id>/
Step W3: Verify WORKSPACE_ROOT exists.
Step W4: Validate registry entry in runtime/workspaces.md (R4a–R4e).
Step W5: All subsequent paths are prefixed with WORKSPACE_ROOT.
```

### Path Update Rule

For each flat path reference in the command, replace with the workspace-scoped equivalent from the Phase 5 path table.

### Workspace Isolation Rule

Add the following to each command's validation section:

```text
All file operations must target paths prefixed with WORKSPACE_ROOT.
Exceptions: runtime/current_workspace.md, runtime/workspaces.md, docs/, templates/, .claude/
Any operation targeting a path outside WORKSPACE_ROOT that is not on the exception list must be rejected.
```

### Assimilation Check

After updating each command, read it back and verify:

- Workspace resolution block is present
- All path references are workspace-scoped
- Workspace isolation rule is present
- No flat-path references remain (except shared exception paths)

---

## Section 9 — Validation Rules

### 9.1 Precondition Validation

All preconditions (Section 2) must be satisfied before any phase begins. A precondition failure stops execution immediately.

### 9.2 Phase Gate Validation

Each phase must reach its STATUS gate before the next phase begins. A missing STATUS gate indicates incomplete execution.

### 9.3 Artifact Integrity Validation

After Phase 3, every migrated artifact must exist at its destination path with content matching the source.

### 9.4 Engineering Method Compliance

Execution must follow the STATUS protocol defined in `${CLAUDE_PLUGIN_ROOT}/docs/runtime_engineering_method.md`. Every phase gate must be explicitly stated in output before proceeding.

### 9.5 Workspace Isolation Validation

After Phase 5, verify that no command contains a flat-path reference that should have been workspace-scoped.

### 9.6 Registry Consistency Validation

After Phase 8, verify that `runtime/workspaces.md` contains exactly one row with `status: active` and that this row matches the `workspace_id` in `runtime/current_workspace.md`.

---

## Section 10 — Failure Handling

| Failure Condition | Response |
| ----------------- | -------- |
| Specification layer file missing | Stop. Report which layer is missing. Workspace resolution cannot proceed without all layers on disk. |
| `CURRENT_RUNTIME_VERSION` unresolvable | Stop. Report `STATUS: BLOCKED — Cannot resolve CURRENT_RUNTIME_VERSION from ${CLAUDE_PLUGIN_ROOT}/docs/implementation_status.md`. |
| Workspace root not found | Stop. Report `STATUS: BLOCKED — Workspace Root Not Found`. |
| R4a — workspace_id not in registry | Stop. Report `STATUS: BLOCKED — Workspace Drift Detected: workspace_id not found in registry`. |
| R4b — registry status archived | Stop. Report `STATUS: BLOCKED — Workspace Archived`. |
| R4b — registry status paused or completed | Report warning. Proceed with caution. Document discrepancy. |
| R4e — multiple active workspaces | Report warning. Use `runtime/current_workspace.md` as authority. |
| R11 — Workspace Drift (current_workspace.md and registry inconsistent) | Report drift. Stop if BLOCKING (R4a, R4b archived). Warn and continue if ADVISORY (R4b paused/completed, R4c, R4d, R4e). |
| Source artifact missing (M1) | Stop for that artifact. Report path. Do not proceed with migration of that artifact. |
| Content mismatch after copy (M4) | Stop. Report destination path and mismatch. Retry M3–M4 once. If mismatch persists, stop and report. |
| Directory creation fails | Stop. Report the path that failed. |
| R13 — Workspace Contamination | Stop immediately. Report the contaminating path. Do not write the file. Roll back any partial write if possible. |
| Phase gate not reached | Stop. Report which phase gate was not reached and why. |

---

## Section 11 — Completion Criteria

The refactor is complete when all of the following are true:

- [ ] All four specification layers read and assimilated from disk
- [ ] `CURRENT_RUNTIME_VERSION` resolved from `${CLAUDE_PLUGIN_ROOT}/docs/implementation_status.md`
- [ ] `runtime/current_workspace.md` exists with `workspace_id: default`
- [ ] `runtime/workspaces.md` exists with `default` registry entry containing `CURRENT_RUNTIME_VERSION`
- [ ] All workspace directories exist under `workspaces/default/`
- [ ] All `.gitkeep` files present in empty directories
- [ ] All artifacts copied using M1–M5 procedure; all verified at destination
- [ ] All source artifacts preserved at original flat paths
- [ ] All four commands updated with workspace resolution, workspace-scoped paths, and isolation enforcement
- [ ] Blocking documentation updates applied
- [ ] `DEPRECATED.md` files created in all deprecated flat-path directories
- [ ] All validation checks in Section 9 passed
- [ ] `${CLAUDE_PLUGIN_ROOT}/docs/runtime_engineering_method.md` STATUS protocol followed throughout
- [ ] `STATUS: WORKSPACE RUNTIME E2E VALIDATED` reached
