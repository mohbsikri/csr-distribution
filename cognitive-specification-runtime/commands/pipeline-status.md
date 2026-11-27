# /pipeline-status

## Purpose

Query the current pipeline state of the active workspace and produce a stage-by-stage status report showing completion, progress, and the next recommended action.

---

## Workspace Resolution

Before any file operation, resolve the active workspace:

```text
Step W1: Read runtime/current_workspace.md and parse workspace_id.
         If absent or empty: record resolver_workspace_id as null; skip W2–W3; proceed to W4.
Step W2: Build WORKSPACE_ROOT = workspaces/<workspace_id>/
Step W3: Verify WORKSPACE_ROOT exists. If not found, stop and report:
         STATUS: PIPELINE STATUS BLOCKED — Workspace Root Not Found: workspaces/<workspace_id>/
Step W4: Read runtime/workspaces.md. Validate registry (R4a–R4e):
         R4a: workspace_id must be present in registry — BLOCKING if missing.
         R4b: status must not be 'archived' — BLOCKING; warn if 'paused' or 'completed'.
         R4c: runtime_version must be present — WARNING if missing.
         R4d: last_active must be present — WARNING if missing.
         R4e (M10 revision): count entries with status:active in runtime/workspaces.md.
              Case A — Normal: exactly one active entry; its workspace_id = resolver_workspace_id → continue.
              Case B — Drift: exactly one active entry; its workspace_id ≠ resolver_workspace_id →
                       BLOCKING: STATUS: PIPELINE STATUS BLOCKED — WORKSPACE DRIFT DETECTED.
              Case C — Resolver absent: resolver_workspace_id is null; one active entry in registry →
                       BLOCKING: STATUS: PIPELINE STATUS BLOCKED — RESOLVER ABSENT.
              Case D — No active entry: zero status:active entries in registry →
                       BLOCKING: STATUS: PIPELINE STATUS BLOCKED — NO ACTIVE WORKSPACE.
              Case E — Multiple active entries: more than one status:active entry →
                       BLOCKING: STATUS: PIPELINE STATUS BLOCKED — REGISTRY INTEGRITY VIOLATION.
Step W5: All subsequent paths are prefixed with WORKSPACE_ROOT.
```

---

## Workspace Isolation

This command is **read-only** with one exception.

The only permitted write operation is:

```text
WORKSPACE_ROOT/runtime/pipeline_status.md
```

No other files are created or modified. No specification, knowledge base, or source artifact is touched.

Exceptions (not workspace-scoped, read-only): `runtime/current_workspace.md`, `runtime/workspaces.md`, `docs/`, `.claude/`

---

## Preconditions

1. Active workspace resolves correctly (W1–W5).

No pipeline stage artifacts are required to be present. Absent stage indicators are treated as `NOT_STARTED`.

---

## Execution

### Step 1 — Load Specifications

Read and assimilate:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/pipeline-status.md
${CLAUDE_PLUGIN_ROOT}/docs/commands/pipeline-status_execution.md
```

The repository is the source of truth.

### Step 2 — Execute Pipeline Status Runtime

Execute the runtime defined in:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/pipeline-status_execution.md
```

Phases: workspace resolution → stage artifact discovery → consistency check → next recommended action → write status report → validate PS1–PS6 → completion report.

---

## Expected Output

```text
WORKSPACE_ROOT/runtime/pipeline_status.md
```

The report is also rendered to the conversation.

---

## Completion Reporting

```text
STATUS: PIPELINE STATUS COMPLETE
STATUS: PIPELINE STATUS BLOCKED
```
