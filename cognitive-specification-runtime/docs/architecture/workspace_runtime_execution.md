# Workspace Runtime Execution Specification

## Purpose

This document is the Layer 2 Execution Specification for Milestone 4.5 — Workspace Runtime Refactor.

It provides the concrete, step-by-step execution procedure for transforming the repository from a flat-path model to a workspace-scoped model.

---

## Runtime Version Reference

The runtime version used throughout this specification is referred to as `CURRENT_RUNTIME_VERSION`.

At execution time, `CURRENT_RUNTIME_VERSION` must be read from:

```text
docs/implementation_status.md
```

Locate the section `## Current Version` and extract the version value.

This value must never be hardcoded. Every reference to `CURRENT_RUNTIME_VERSION` in this specification is a runtime-resolved placeholder.

---

## Preconditions

Before execution begins, verify:

| Precondition | Check |
| ------------ | ----- |
| P1 | `docs/architecture/workspace_runtime.md` exists and is readable |
| P2 | `docs/architecture/workspace_runtime_execution.md` exists and is readable |
| P3 | `templates/architecture/workspace_runtime_prompt.md` exists and is readable |
| P4 | `docs/implementation_status.md` exists and `## Current Version` is readable |
| P5 | All artifacts listed in Phase 3 — Artifact Migration exist at their source paths |

If any precondition fails, stop and report the failure explicitly.

---

## Phase 1 — Workspace Runtime Infrastructure Creation

Create the runtime control files that establish workspace identity.

### 1.1 Create `runtime/current_workspace.md`

If the file does not exist, create it with the following content:

```markdown
# Current Workspace

workspace_id: default
```

If the file already exists, do not overwrite it. Read and report its current content.

### 1.2 Create `runtime/workspaces.md`

If the file does not exist, create it with the following content:

```markdown
# Workspace Registry

| workspace_id | created | status | description | last_active | runtime_version |
| ------------ | ------- | ------ | ----------- | ----------- | --------------- |
| default | <ISO 8601 timestamp> | active | Default workspace — migrated from flat-path model | <ISO 8601 timestamp> | CURRENT_RUNTIME_VERSION |
```

Replace `CURRENT_RUNTIME_VERSION` with the value read from `docs/implementation_status.md ## Current Version`.

Replace `<ISO 8601 timestamp>` with the current UTC timestamp.

If the file already exists, do not overwrite it. Read and report its current content.

**STATUS: PHASE 1 COMPLETE**

---

## Phase 2 — Default Workspace Directory Creation

Create all workspace subdirectories for `workspaces/default/`.

Create the following directories:

```text
workspaces/default/input/documents/
workspaces/default/input/decisions/
workspaces/default/input/validations/
workspaces/default/knowledge_base/raw/
workspaces/default/knowledge_base/extracted/
workspaces/default/knowledge_base/conflicts/
workspaces/default/knowledge_base/questions/
workspaces/default/knowledge_base/consolidated/
workspaces/default/knowledge_base/decisions/
workspaces/default/knowledge_base/graph/
workspaces/default/specifications/draft/
workspaces/default/specifications/stable/
workspaces/default/output/generated_questions/
workspaces/default/runtime/
```

For directories that will remain empty after migration, create a `.gitkeep` file to ensure Git tracks them:

```text
workspaces/default/knowledge_base/consolidated/.gitkeep
workspaces/default/knowledge_base/decisions/.gitkeep
workspaces/default/specifications/draft/.gitkeep
workspaces/default/specifications/stable/.gitkeep
workspaces/default/input/decisions/.gitkeep
workspaces/default/input/validations/.gitkeep
```

**STATUS: PHASE 2 COMPLETE**

---

## Phase 3 — Artifact Migration

Copy all existing artifacts from flat-path locations to workspace-scoped locations.

### Migration Procedure

For each artifact:

**M1** — Verify the source file exists at the source path.

**M2** — Read the full content of the source file.

**M3** — Write the content to the destination path.

**M4** — Verify the destination file exists and its content matches the source.

**M5** — Do not delete or modify the source file.

### Artifact Migration Mapping

| Source Path | Destination Path |
| ----------- | ---------------- |
| `input/documents/test_source.md` | `workspaces/default/input/documents/test_source.md` |
| `knowledge_base/raw/test_source.md` | `workspaces/default/knowledge_base/raw/test_source.md` |
| `knowledge_base/extracted/test_source_knowledge.md` | `workspaces/default/knowledge_base/extracted/test_source_knowledge.md` |
| `knowledge_base/conflicts/conflicts_report.md` | `workspaces/default/knowledge_base/conflicts/conflicts_report.md` |
| `knowledge_base/questions/questions_report.md` | `workspaces/default/knowledge_base/questions/questions_report.md` |
| `knowledge_base/graph/entities.md` | `workspaces/default/knowledge_base/graph/entities.md` |
| `knowledge_base/graph/relations.md` | `workspaces/default/knowledge_base/graph/relations.md` |
| `knowledge_base/graph/impacts.md` | `workspaces/default/knowledge_base/graph/impacts.md` |
| `output/generated_questions/questions_for_review.md` | `workspaces/default/output/generated_questions/questions_for_review.md` |
| `runtime/sources.md` | `workspaces/default/runtime/sources.md` |
| `runtime/state.md` | `workspaces/default/runtime/state.md` |
| `runtime/events.md` | `workspaces/default/runtime/events.md` |

After all artifacts are copied, verify that each destination file exists and is non-empty where the source was non-empty.

**STATUS: PHASE 3 COMPLETE**

---

## Phase 4 — Workspace Path Resolution

Establish and validate workspace path resolution.

### R1 — Read Current Workspace

Read `runtime/current_workspace.md`.

Parse the `workspace_id` value.

### R2 — Build Workspace Root

Construct:

```text
WORKSPACE_ROOT = workspaces/<workspace_id>/
```

### R3 — Verify Workspace Root Exists

Confirm `WORKSPACE_ROOT` directory exists in the repository.

If it does not exist, stop and report `STATUS: BLOCKED — Workspace Root Not Found`.

### R4 — Validate Registry Entry

Read `runtime/workspaces.md`.

Locate the row where `workspace_id` matches the value from R1.

#### R4a — Workspace ID Present

If no matching row exists, report:

```text
STATUS: BLOCKED — Workspace Drift Detected: workspace_id not found in registry
```

Stop execution.

#### R4b — Status Consistency

If the registry row `status` is `archived`, stop execution and report:

```text
STATUS: BLOCKED — Workspace Archived: workspace must not be used for active processing
```

If the registry row `status` is `paused` or `completed`, report:

```text
STATUS: WARNING — Workspace Drift Detected: registry status is <status>, expected active
```

Proceed with caution.

#### R4c — Registry runtime_version Present

If the `runtime_version` field is empty or missing, report:

```text
STATUS: WARNING — Registry Entry Incomplete: runtime_version is missing
```

#### R4d — Last Active Timestamp Present

If the `last_active` field is empty or missing, report:

```text
STATUS: WARNING — Registry Entry Incomplete: last_active is missing
```

#### R4e — Single Active Entry

If more than one registry row has `status: active`, report:

```text
STATUS: WARNING — Workspace Drift Detected: multiple active workspaces in registry
```

### R5 — Confirm Workspace Path Resolution

Report the resolved workspace root path and workspace ID.

### R6 — Workspace Isolation Check

All file operations must use paths prefixed with `WORKSPACE_ROOT`.

Exceptions (shared paths, not workspace-scoped):
- `runtime/current_workspace.md`
- `runtime/workspaces.md`
- `docs/`
- `templates/`
- `.claude/`

### R7 — Path Construction

All artifact paths used in subsequent phases are constructed as:

```text
WORKSPACE_ROOT + <relative path within workspace>
```

**STATUS: PHASE 4 COMPLETE — INFRASTRUCTURE VALID**

---

## Phase 5 — Existing Command Refactor

Update all runtime commands to resolve paths relative to the active workspace.

### Commands to Refactor

#### `/ingest-source` (`.claude/commands/ingest-source.md`)

| Path Type | Before | After |
| --------- | ------ | ----- |
| Input document destination | `input/documents/` | `WORKSPACE_ROOT/input/documents/` |
| Raw knowledge output | `knowledge_base/raw/` | `WORKSPACE_ROOT/knowledge_base/raw/` |

#### `/extract-knowledge` (`.claude/commands/extract-knowledge.md`)

| Path Type | Before | After |
| --------- | ------ | ----- |
| Raw knowledge input | `knowledge_base/raw/` | `WORKSPACE_ROOT/knowledge_base/raw/` |
| Extracted knowledge output | `knowledge_base/extracted/` | `WORKSPACE_ROOT/knowledge_base/extracted/` |
| Source registry | `runtime/sources.md` | `WORKSPACE_ROOT/runtime/sources.md` |

#### `/detect-conflicts` (`.claude/commands/detect-conflicts.md`)

| Path Type | Before | After |
| --------- | ------ | ----- |
| Extracted knowledge input | `knowledge_base/extracted/` | `WORKSPACE_ROOT/knowledge_base/extracted/` |
| Conflicts report output | `knowledge_base/conflicts/conflicts_report.md` | `WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md` |

#### `/generate-questions` (`.claude/commands/generate-questions.md`)

| Path Type | Before | After |
| --------- | ------ | ----- |
| Conflicts report input | `knowledge_base/conflicts/conflicts_report.md` | `WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md` |
| Questions canonical output | `knowledge_base/questions/questions_report.md` | `WORKSPACE_ROOT/knowledge_base/questions/questions_report.md` |
| Questions derived output | `output/generated_questions/questions_for_review.md` | `WORKSPACE_ROOT/output/generated_questions/questions_for_review.md` |

All four commands must:

1. Read `runtime/current_workspace.md` to resolve `WORKSPACE_ROOT`.
2. Validate the workspace registry entry (R4a–R4e).
3. Prefix all artifact paths with `WORKSPACE_ROOT`.
4. Enforce workspace isolation — reject any path outside `WORKSPACE_ROOT` that is not on the shared exceptions list.

**STATUS: PHASE 5 COMPLETE**

---

## Phase 6 — Documentation Refactor

Update documentation and templates to reflect workspace-scoped paths.

### BLOCKING

Documents that must be updated before the refactor is considered complete:

| Document | Required Change |
| -------- | --------------- |
| `docs/mvp_workflow.md` | Update all path references to workspace-scoped format |
| `docs/mvp_commands.md` | Update all command output path references |
| `docs/commands/ingest_source.md` | Update path references |
| `docs/commands/extract-knowledge.md` | Update path references |
| `docs/commands/detect-conflicts.md` | Update path references |
| `docs/commands/generate-questions.md` | Update path references |

### DOCUMENTATION (informational)

Documents that should be updated to reflect the new model:

| Document | Required Change |
| -------- | --------------- |
| `docs/glossary.md` | Add Workspace, Workspace Registry, Active Workspace entries |
| `README.md` | Update repository structure section |

### NON-BLOCKING

Documents that may be updated in a follow-up:

| Document | Note |
| -------- | ---- |
| `templates/commands/` | Update prompt templates to reference workspace-scoped paths |

**STATUS: PHASE 6 COMPLETE**

---

## Phase 7 — Deprecation Of Old Root-Level Runtime Areas

Mark deprecated flat-path directories with `DEPRECATED.md` files.

### Deprecation Target Directories

```text
input/documents/
input/decisions/
input/validations/
knowledge_base/raw/
knowledge_base/extracted/
knowledge_base/conflicts/
knowledge_base/questions/
knowledge_base/graph/
output/generated_questions/
```

### DEPRECATED.md Content

Create a `DEPRECATED.md` file in each target directory with the following content:

```markdown
# DEPRECATED

This directory has been superseded by the workspace-scoped model introduced in Milestone 4.5.

Artifacts in this directory are preserved for reference.

Active artifacts are now located at:

```text
workspaces/default/<relative path>/
```

Physical deletion of this directory is deferred to a future milestone.
```

### Header Format for Source Files

For each source file that has been migrated, prepend a deprecation notice to the file header:

```markdown
> **DEPRECATED** — This artifact has been migrated to `workspaces/default/<relative path>/<filename>`. This copy is preserved for reference only.
```

Do not modify the body of the source files.

**STATUS: PHASE 7 COMPLETE**

---

## Phase 8 — Validation Strategy

### 8.1 Infrastructure Validation

Verify:

- `runtime/current_workspace.md` exists and contains `workspace_id: default`
- `runtime/workspaces.md` exists and contains a row for `default` with `status: active` and `runtime_version: CURRENT_RUNTIME_VERSION`
- All 14 workspace directories exist under `workspaces/default/`

**STATUS: INFRASTRUCTURE VALID**

### 8.2 Migration Validation

For each artifact in the Phase 3 migration table:

- Verify destination file exists
- Verify destination file content is non-empty where source was non-empty
- Verify source file is still present (not deleted)

**STATUS: MIGRATION VALID**

### 8.3 Command Validation

For each refactored command:

- Verify workspace resolution steps are present
- Verify all path references use `WORKSPACE_ROOT` prefix
- Verify shared exception paths are not prefixed with `WORKSPACE_ROOT`

**STATUS: COMMANDS VALID**

### 8.4 End-to-End Validation

Execute a simulated run of each command against the workspace-scoped paths and verify expected outputs resolve correctly.

**STATUS: WORKSPACE RUNTIME E2E VALIDATED**

---

## Phase 9 — Failure Handling

| Failure | Action |
| ------- | ------ |
| Precondition file missing | Stop. Report which precondition failed. Do not proceed. |
| `docs/implementation_status.md` unreadable | Stop. Report `STATUS: BLOCKED — Cannot resolve CURRENT_RUNTIME_VERSION`. |
| Directory creation fails | Stop. Report the path that failed. |
| Source artifact missing (M1 check fails) | Stop. Report the missing source path. Do not proceed with that artifact. |
| Content mismatch after copy (M4 check fails) | Stop. Report the destination path and mismatch. Retry M3–M4 once. If mismatch persists, stop. |
| Workspace root not found (R3) | Stop. Report `STATUS: BLOCKED — Workspace Root Not Found`. |
| Workspace drift detected (R4a) | Stop. Report `STATUS: BLOCKED — Workspace Drift Detected`. |
| Workspace archived (R4b) | Stop. Report `STATUS: BLOCKED — Workspace Archived: workspace must not be used for active processing`. |
| Multiple active workspaces (R4e) | Report warning. Proceed using `runtime/current_workspace.md` as authority. |
| Registry version mismatch | Stop. Report `STATUS: BLOCKED — Workspace Registry Version Mismatch`. |
| R13 — Workspace Contamination | Stop immediately. Report the contaminating path. Do not write the file. Roll back any partial write. |

### R13 — Workspace Contamination

Workspace contamination occurs when an operation attempts to read from or write to a path that is:

- Outside `WORKSPACE_ROOT`, and
- Not on the shared exception list (`runtime/current_workspace.md`, `runtime/workspaces.md`, `docs/`, `templates/`, `.claude/`)

This is a hard stop condition. No exception applies beyond the shared exception list.

---

## Phase 10 — Completion Criteria

The execution is complete when all of the following are true:

- [ ] `runtime/current_workspace.md` created with `workspace_id: default`
- [ ] `runtime/workspaces.md` created with `default` registry entry containing correct `CURRENT_RUNTIME_VERSION`
- [ ] All 14 workspace directories exist under `workspaces/default/`
- [ ] All `.gitkeep` files created in empty directories
- [ ] All 12 artifacts copied from flat paths to workspace-scoped paths
- [ ] All source artifacts preserved at their original paths
- [ ] All four commands updated to resolve paths relative to `WORKSPACE_ROOT`
- [ ] Workspace registry validation (R4a–R4e) integrated into all four commands
- [ ] Workspace isolation enforcement integrated into all four commands
- [ ] Blocking documentation updates applied
- [ ] `DEPRECATED.md` files created in all deprecated flat-path directories
- [ ] `STATUS: WORKSPACE RUNTIME E2E VALIDATED` reached

---

## Risk Assessment

| ID | Risk | Severity | Mitigation |
| -- | ---- | -------- | ---------- |
| R1 | `runtime/current_workspace.md` missing | BLOCKING | Phase 1 creates it if absent; Preconditions verify that infrastructure layer files exist |
| R2 | `runtime/workspaces.md` missing | BLOCKING | Phase 1 creates it if absent |
| R3 | Workspace directory not found | BLOCKING | Phase 4 R3 check stops execution |
| R4 | Workspace registry entry missing | BLOCKING | Phase 4 R4a check stops execution |
| R5 | Source artifact missing before copy | BLOCKING | M1 check stops execution for that artifact |
| R6 | Content mismatch after copy | BLOCKING | M4 check stops execution; one retry permitted |
| R7 | Command path reference missed in refactor | ADVISORY | Phase 8.3 command validation catches omissions |
| R8 | Documentation update incomplete | ADVISORY | Phase 6 blocking list; Phase 8 validation |
| R9 | `.gitkeep` file missing in empty directory | ADVISORY | Phase 2 explicitly lists all `.gitkeep` targets |
| R10 | `CURRENT_RUNTIME_VERSION` unresolvable | BLOCKING | Phase 9 failure handler; stop before registry write |
| R11 | Workspace Drift | ADVISORY | R4a–R4e detect inconsistency between `current_workspace.md` and registry; report and stop or warn per severity |
| R12 | Multiple active workspaces in registry | ADVISORY | R4e detects; `current_workspace.md` is authority |
| R13 | Workspace Contamination — path written outside WORKSPACE_ROOT | BLOCKING | Prefix check before every file operation; hard stop on violation |
