# /workspace-runtime-refactor

## Purpose

Execute Milestone 4.5 — Workspace Runtime Refactor.

Transform the repository from a flat-path model to a workspace-scoped model where all artifacts reside under `workspaces/<workspace_id>/`.

This command follows the four-layer architecture:

1. `${CLAUDE_PLUGIN_ROOT}/docs/architecture/workspace_runtime.md` — Layer 1 Contract
2. `${CLAUDE_PLUGIN_ROOT}/docs/architecture/workspace_runtime_execution.md` — Layer 2 Execution Specification
3. `${CLAUDE_PLUGIN_ROOT}/templates/architecture/workspace_runtime_prompt.md` — Layer 3 Prompt Template
4. `.claude/commands/workspace-runtime-refactor.md` — Layer 4 Claude Command (this file)

---

## Preconditions

### Precondition 0 — Specification Layers on Disk

All four specification layer files must exist as files on disk before execution begins.

Conversation context is not a substitute for files on disk. If any layer file is missing, stop and report which file is absent.

### Precondition 1 — Runtime Version Resolvable

`${CLAUDE_PLUGIN_ROOT}/docs/implementation_status.md` must exist and section `## Current Version` must be readable.

Extract `CURRENT_RUNTIME_VERSION` from this file. Never hardcode a version value.

### Precondition 2 — Repository Structure Valid

The repository root must contain the expected top-level directories as defined in `CLAUDE.md`.

### Precondition 3 — Control Files Absent or Readable

If `runtime/current_workspace.md` exists, read and report its content before proceeding.

If `runtime/workspaces.md` exists, read and report its content before proceeding.

### Precondition 4 — Workspace Root State Known

Check whether `workspaces/default/` exists. Read and report its current state if it does.

### Precondition 5 — Source Artifacts Present

Read `${CLAUDE_PLUGIN_ROOT}/docs/architecture/workspace_runtime_execution.md` Phase 3 — Artifact Migration to obtain the complete artifact migration mapping.

Verify that each source artifact listed in Phase 3 exists at its source path.

Report any missing source artifact before proceeding.

---

## Step 1 — Load and Assimilate Specification Layers

Read the following files in order:

1. `${CLAUDE_PLUGIN_ROOT}/docs/architecture/workspace_runtime.md`
2. `${CLAUDE_PLUGIN_ROOT}/docs/architecture/workspace_runtime_execution.md`
3. `${CLAUDE_PLUGIN_ROOT}/templates/architecture/workspace_runtime_prompt.md`
4. `${CLAUDE_PLUGIN_ROOT}/docs/implementation_status.md` — extract `CURRENT_RUNTIME_VERSION`
5. `CLAUDE.md`
6. `${CLAUDE_PLUGIN_ROOT}/docs/runtime_engineering_method.md`

Do not proceed to Step 2 until all files are read and assimilated.

Report: `STATUS: SPECIFICATION LAYERS LOADED`

---

## Workspace Isolation

**Workspace isolation is active throughout the entire execution of this command.**

Before every file read or write operation:

1. Determine the target path.
2. Check if the path is prefixed with `WORKSPACE_ROOT`.
3. If not prefixed, check if the path is on the shared exception list below.
4. If neither condition is met: stop immediately. Report workspace contamination. Do not proceed with the operation.

**Shared exception paths (not workspace-scoped):**

- `runtime/current_workspace.md`
- `runtime/workspaces.md`
- `docs/`
- `templates/`
- `.claude/`

This rule has no other exceptions.

---

## Step 2 — Workspace Resolution

### R1 — Read Current Workspace

Read `runtime/current_workspace.md`.

Parse the `workspace_id` value from:

```text
workspace_id: <value>
```

### R2 — Build Workspace Root

Construct:

```text
WORKSPACE_ROOT = workspaces/<workspace_id>/
```

### R3 — Verify Workspace Root

Confirm `WORKSPACE_ROOT` directory exists.

If not found:

```text
STATUS: BLOCKED — Workspace Root Not Found: workspaces/<workspace_id>/
```

Stop execution.

### R4 — Validate Registry Entry

Read `runtime/workspaces.md`. Locate the row where `workspace_id` matches R1.

#### R4a — Workspace ID Present

If no matching row exists:

```text
STATUS: BLOCKED — Workspace Drift Detected: workspace_id '<value>' not found in runtime/workspaces.md
```

Stop execution.

#### R4b — Status Field

If matching row `status` is `archived`:

```text
STATUS: BLOCKED — Workspace Archived: workspace_id '<value>' has status 'archived' and must not be used for active processing
```

Stop execution.

If matching row `status` is `paused` or `completed`:

```text
STATUS: WARNING — Workspace Drift Detected: registry status is '<status>' for workspace_id '<value>', expected 'active'
```

Proceed with caution. Document the discrepancy.

#### R4c — runtime_version Field

If `runtime_version` is empty or missing:

```text
STATUS: WARNING — Registry Entry Incomplete: runtime_version missing for workspace_id '<value>'
```

#### R4d — last_active Field

If `last_active` is empty or missing:

```text
STATUS: WARNING — Registry Entry Incomplete: last_active missing for workspace_id '<value>'
```

#### R4e — Single Active Entry

If more than one registry row has `status: active`:

```text
STATUS: WARNING — Workspace Drift Detected: multiple rows with status 'active' in runtime/workspaces.md
```

Use `runtime/current_workspace.md` as the authority.

### R5 — Confirm Resolution

Report:

```text
Active workspace: <workspace_id>
WORKSPACE_ROOT: workspaces/<workspace_id>/
```

### R6 — Isolation Enforcement Active

Confirm workspace isolation is enforced from this point forward.

### R7 — Path Construction

All artifact paths are constructed as:

```text
WORKSPACE_ROOT + <relative path within workspace>
```

---

## Step 3 — Execute Phase 1: Workspace Runtime Infrastructure Creation

Follow `${CLAUDE_PLUGIN_ROOT}/docs/architecture/workspace_runtime_execution.md` Phase 1 exactly.

Create `runtime/current_workspace.md` if absent.

Create `runtime/workspaces.md` if absent. Populate `CURRENT_RUNTIME_VERSION` from `${CLAUDE_PLUGIN_ROOT}/docs/implementation_status.md`.

### Step 10.1 — Infrastructure Validation

After writing `runtime/workspaces.md`, read it back and verify:

- The `default` row exists.
- The `runtime_version` field contains the value read from `${CLAUDE_PLUGIN_ROOT}/docs/implementation_status.md ## Current Version`.
- The value is not a placeholder string `CURRENT_RUNTIME_VERSION` — it must be the resolved version number.

If the `runtime_version` field contains `CURRENT_RUNTIME_VERSION` as a literal string, or contains any value other than the resolved version:

```text
STATUS: BLOCKED — Workspace Registry Version Mismatch: runtime_version field was not resolved correctly
```

Stop execution.

Report: `STATUS: PHASE 1 COMPLETE`

---

## Step 4 — Execute Phase 2: Default Workspace Directory Creation

Follow `${CLAUDE_PLUGIN_ROOT}/docs/architecture/workspace_runtime_execution.md` Phase 2 exactly.

Create all 14 workspace subdirectories.

Create `.gitkeep` files in all empty directories listed in Phase 2.

Report: `STATUS: PHASE 2 COMPLETE`

---

## Step 5 — Execute Phase 3: Artifact Migration

Follow `${CLAUDE_PLUGIN_ROOT}/docs/architecture/workspace_runtime_execution.md` Phase 3 exactly.

For each artifact in the migration table, apply the M1–M5 procedure:

- M1: Verify source exists
- M2: Read source content
- M3: Write to destination
- M4: Verify destination content matches source
- M5: Confirm source is still present

After all artifacts are copied, verify every destination exists and is non-empty where source was non-empty.

Report: `STATUS: PHASE 3 COMPLETE`

---

## Step 6 — Execute Phase 4: Workspace Path Resolution Validation

Perform workspace resolution R1–R7 against the newly created workspace.

Validate R4a–R4e against the registry entry just created.

Report: `STATUS: PHASE 4 COMPLETE — INFRASTRUCTURE VALID`

---

## Step 7 — Execute Phase 5: Existing Command Refactor

Follow `${CLAUDE_PLUGIN_ROOT}/docs/architecture/workspace_runtime_execution.md` Phase 5 exactly.

Update each of the four commands:

- `.claude/commands/ingest-source.md`
- `.claude/commands/extract-knowledge.md`
- `.claude/commands/detect-conflicts.md`
- `.claude/commands/generate-questions.md`

For each command:

1. Add workspace resolution block (R1–R7) at the start.
2. Replace all flat-path references with workspace-scoped equivalents per Phase 5 path tables.
3. Add workspace isolation enforcement.
4. Read the updated command back and confirm no flat-path references remain.

Report: `STATUS: PHASE 5 COMPLETE`

---

## Step 8 — Execute Phase 6: Documentation Refactor

Follow `${CLAUDE_PLUGIN_ROOT}/docs/architecture/workspace_runtime_execution.md` Phase 6 exactly.

Apply all BLOCKING documentation updates.

Report: `STATUS: PHASE 6 COMPLETE`

---

## Step 9 — Execute Phase 7: Deprecation Of Old Root-Level Runtime Areas

Follow `${CLAUDE_PLUGIN_ROOT}/docs/architecture/workspace_runtime_execution.md` Phase 7 exactly.

Create `DEPRECATED.md` files in all deprecated flat-path directories using the content defined in Phase 7.

Report: `STATUS: PHASE 7 COMPLETE`

---

## Step 10 — Execute Phase 8: Validation Strategy

Execute all four validation checks from `${CLAUDE_PLUGIN_ROOT}/docs/architecture/workspace_runtime_execution.md` Phase 8:

- 8.1 Infrastructure Validation
- 8.2 Migration Validation
- 8.3 Command Validation
- 8.4 End-to-End Validation

Report: `STATUS: WORKSPACE RUNTIME E2E VALIDATED`

---

## Failure Handling

| Failure Condition | Response |
| ----------------- | -------- |
| Specification layer file missing (Precondition 0) | Stop. Report which layer file is absent. Do not proceed. |
| `CURRENT_RUNTIME_VERSION` unresolvable | Stop. Report `STATUS: BLOCKED — Cannot resolve CURRENT_RUNTIME_VERSION from ${CLAUDE_PLUGIN_ROOT}/docs/implementation_status.md`. |
| Registry version mismatch (Step 10.1) | Stop. Report `STATUS: BLOCKED — Workspace Registry Version Mismatch`. |
| Workspace root not found (R3) | Stop. Report `STATUS: BLOCKED — Workspace Root Not Found`. |
| Workspace drift — ID missing (R4a) | Stop. Report `STATUS: BLOCKED — Workspace Drift Detected: workspace_id not found in registry`. |
| Workspace archived (R4b — archived status) | Stop. Report `STATUS: BLOCKED — Workspace Archived`. |
| Workspace drift — status warning (R4b — paused or completed) | Warn. Proceed with caution. Document discrepancy. |
| Multiple active workspaces (R4e) | Warn. Use `runtime/current_workspace.md` as authority. Continue. |
| R11 — Workspace Drift | Stop if BLOCKING (R4a, R4b archived). Warn and continue if ADVISORY (R4b paused/completed, R4c, R4d, R4e). |
| Source artifact missing (M1) | Stop for that artifact. Report path. Do not migrate that artifact. |
| Content mismatch after copy (M4) | Stop. Retry M3–M4 once. If mismatch persists, stop and report. |
| Directory creation fails | Stop. Report the path that failed. |
| R13 — Workspace Contamination | Stop immediately. Report contaminating path. Do not write the file. Roll back any partial write if possible. |
| Phase gate not reached | Stop. Report which phase gate was not reached and why. |

---

## Completion Criteria

The command is complete when all of the following are true:

- [ ] All four specification layers read from disk and assimilated
- [ ] `CURRENT_RUNTIME_VERSION` resolved from `${CLAUDE_PLUGIN_ROOT}/docs/implementation_status.md`
- [ ] `runtime/current_workspace.md` exists with `workspace_id: default`
- [ ] `runtime/workspaces.md` exists with `default` registry entry; `runtime_version` contains resolved version value (not placeholder)
- [ ] All 14 workspace directories exist under `workspaces/default/`
- [ ] All `.gitkeep` files present in empty workspace directories
- [ ] All artifacts from Phase 3 migration table copied using M1–M5 procedure
- [ ] All source artifacts preserved at original flat paths (not deleted or modified)
- [ ] All four commands updated with workspace resolution, workspace-scoped paths, and isolation enforcement
- [ ] Blocking documentation updates applied
- [ ] `DEPRECATED.md` files created in all deprecated flat-path directories
- [ ] All Phase 8 validation checks passed
- [ ] `STATUS: WORKSPACE RUNTIME E2E VALIDATED` reached

---

## Post-Implementation Activities

After all completion criteria are met, perform the following activities:

1. Review `git status` to confirm all changed and new files are as expected.
2. Verify that no unintended files were modified or deleted.
3. Create a Git checkpoint with commit message:

```text
feat: milestone 4.5 workspace runtime refactor
```

Stage only the files that are part of this refactor. Do not stage unrelated files.

---

## Out of Scope

The following are explicitly out of scope for this command:

- Human Validation workflow changes
- Consolidation workflow changes
- Specification generation changes
- Multi-workspace orchestration (switching between workspaces)
- Workspace creation commands
- Workspace archival commands
- Any file operation outside the boundaries defined in this command
