# Workspace Runtime Contract

## Purpose

This document is the Layer 1 Contract for Milestone 4.5 — Workspace Runtime Refactor.

It defines the workspace model, workspace structure, lifecycle, registry, path refactoring strategy, migration approach, and validation gates required to transition the Cognitive Specification Runtime from a single-workspace flat-path model to a multi-workspace model.

---

## Workspace Definition

A workspace is an isolated, self-contained processing context within the runtime.

Each workspace owns a dedicated directory subtree under `workspaces/<workspace_id>/` and contains all artifacts produced during its processing lifecycle: inputs, extracted knowledge, conflicts, questions, consolidations, specifications, and outputs.

Workspaces do not share artifact directories. Runtime-level files (`runtime/current_workspace.md`, `runtime/workspaces.md`) are shared across workspaces and are the only exceptions to workspace isolation.

---

## Workspace Structure

Each workspace follows this directory structure:

```text
workspaces/<workspace_id>/
  input/
    documents/
    decisions/
    validations/
  knowledge_base/
    raw/
    extracted/
    conflicts/
    questions/
    consolidated/
    decisions/
    graph/
  specifications/
    draft/
    stable/
  output/
    generated_questions/
  runtime/
    sources.md
    state.md
    events.md
```

---

## Active Workspace Resolution

The active workspace is resolved through a two-file lookup:

1. **`runtime/workspaces.md`** (authority) — the entry with `status: active` defines the active workspace.
2. **`runtime/current_workspace.md`** (operational pointer) — names the active workspace for pipeline command consumption, enabling path construction without reading the full registry.

The runtime reads the `workspace_id` value from `runtime/current_workspace.md` and constructs the workspace root path:

```text
workspaces/<workspace_id>/
```

All command operations resolve paths relative to this workspace root.

### Authority Model (M10)

`runtime/workspaces.md` is the authoritative source of truth for workspace lifecycle state. The `status: active` entry in the registry defines the active workspace.

`runtime/current_workspace.md` is an operational pointer. It reflects the active workspace from the registry and is consumed by pipeline commands to construct `WORKSPACE_ROOT`. It is not an authority source.

When `runtime/workspaces.md` and `runtime/current_workspace.md` disagree, `runtime/workspaces.md` wins. `runtime/current_workspace.md` is considered stale and must be corrected.

### Drift Handling (M10)

Drift occurs when the `workspace_id` in `runtime/current_workspace.md` does not match the `workspace_id` of the `status: active` entry in `runtime/workspaces.md`.

Pipeline commands must not silently proceed when drift is detected. The R4e workspace validation rule (M10 revision) defines five cases — Normal, Drift, Resolver Absent, No Active Workspace, and Registry Integrity Violation — all non-Normal cases are BLOCKING.

To resolve drift: run `/workspace-lifecycle SWITCH` to synchronize `runtime/current_workspace.md` with the registry.

Only the `/workspace-lifecycle` command may write to `runtime/current_workspace.md`.

---

## Default Workspace

The default workspace is:

```text
workspaces/default/
```

`runtime/current_workspace.md` initially contains:

```text
workspace_id: default
```

All existing artifacts are migrated to the default workspace during Milestone 4.5.

---

## Workspace Lifecycle

A workspace passes through the following states:

| State | Description |
| ----- | ----------- |
| `pending` | Workspace created but not yet activated |
| `active` | Workspace currently in use |
| `paused` | Workspace temporarily suspended |
| `completed` | Workspace processing finished |
| `archived` | Workspace preserved for reference, no longer active |

### Lifecycle Transitions

| From | To | Trigger |
| ---- | -- | ------- |
| — | `pending` | Workspace created |
| `pending` | `active` | Workspace activated |
| `active` | `paused` | Processing suspended |
| `paused` | `active` | Processing resumed |
| `active` | `completed` | Processing finished |
| `completed` | `archived` | Workspace archived |
| `paused` | `archived` | Workspace archived without completing |

---

## Workspace Registry

All workspaces are registered in:

```text
runtime/workspaces.md
```

Each registry entry contains:

| Field | Description |
| ----- | ----------- |
| `workspace_id` | Unique identifier for the workspace |
| `created` | ISO 8601 timestamp of workspace creation |
| `status` | Current lifecycle state |
| `description` | Human-readable description of the workspace purpose |
| `last_active` | ISO 8601 timestamp of last activity |
| `runtime_version` | Runtime version at time of workspace creation |

---

## Command Path Refactor

All runtime commands must be updated to resolve paths relative to the active workspace root.

### Workspace-Scoped Paths

| Path Type | Before (flat) | After (workspace-scoped) |
| --------- | ------------- | ------------------------- |
| Input documents | `input/documents/` | `workspaces/<id>/input/documents/` |
| Input decisions | `input/decisions/` | `workspaces/<id>/input/decisions/` |
| Input validations | `input/validations/` | `workspaces/<id>/input/validations/` |
| Raw knowledge | `knowledge_base/raw/` | `workspaces/<id>/knowledge_base/raw/` |
| Extracted knowledge | `knowledge_base/extracted/` | `workspaces/<id>/knowledge_base/extracted/` |
| Conflicts | `knowledge_base/conflicts/` | `workspaces/<id>/knowledge_base/conflicts/` |
| Questions | `knowledge_base/questions/` | `workspaces/<id>/knowledge_base/questions/` |
| Generated questions output | `output/generated_questions/` | `workspaces/<id>/output/generated_questions/` |
| Workspace runtime files | `runtime/sources.md`, `runtime/state.md`, `runtime/events.md` | `workspaces/<id>/runtime/sources.md`, etc. |

### Shared Paths (not workspace-scoped)

| Path | Reason |
| ---- | ------ |
| `runtime/current_workspace.md` | Operational pointer to the active workspace — shared across all workspaces; authority is `runtime/workspaces.md` (M10) |
| `runtime/workspaces.md` | Workspace registry — shared across all workspaces |
| `docs/` | Documentation — shared |
| `templates/` | Templates — shared |
| `.claude/` | Commands, agents, skills, hooks — shared |

---

## Backward Compatibility

Existing flat-path artifacts are not deleted during Milestone 4.5.

Deprecated paths are marked with `DEPRECATED.md` files at the root of each deprecated directory. Physical deletion is deferred to a future milestone.

No command, documentation, or runtime file is deleted during Milestone 4.5 without explicit instruction.

---

## Migration Strategy

Artifact migration proceeds in six phases:

| Phase | Description |
| ----- | ----------- |
| Phase 1 | Workspace Runtime Infrastructure Creation — create runtime control files and workspace directories |
| Phase 2 | Default Workspace Directory Creation — create all workspace subdirectories |
| Phase 3 | Artifact Migration — copy existing artifacts to workspace-scoped paths |
| Phase 4 | Workspace Path Resolution — establish and validate workspace path resolution |
| Phase 5 | Existing Command Refactor — update all command path references to workspace-scoped paths |
| Phase 6 | Documentation Refactor — update documentation and templates |

---

## Validation Strategy

Each phase concludes with a STATUS gate before the next phase begins.

The final validation gate is:

```text
STATUS: WORKSPACE RUNTIME E2E VALIDATED
```

This gate is reached when all commands execute correctly against workspace-scoped paths and all artifacts are traceable to the active workspace.

---

## Out of Scope

The following are explicitly out of scope for Milestone 4.5:

- Human Validation workflow changes
- Consolidation workflow changes
- Specification generation changes
- Multi-workspace orchestration (switching between workspaces during execution)
- Workspace creation commands
- Workspace archival commands
