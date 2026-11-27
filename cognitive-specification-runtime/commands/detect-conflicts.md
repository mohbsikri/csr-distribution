# /detect-conflicts

## Purpose

Analyze extracted knowledge artifacts and produce a structured conflict report.

This command identifies contradictions, ambiguities, and gaps across the knowledge base and makes them visible for downstream resolution.

---

## Workspace Resolution

Before any file operation, resolve the active workspace:

```text
Step W1: Read runtime/current_workspace.md and parse workspace_id.
         If absent or empty: record resolver_workspace_id as null; skip W2–W3; proceed to W4.
Step W2: Build WORKSPACE_ROOT = workspaces/<workspace_id>/
Step W3: Verify WORKSPACE_ROOT exists. If not found, stop and report:
         STATUS: BLOCKED — Workspace Root Not Found: workspaces/<workspace_id>/
Step W4: Read runtime/workspaces.md. Validate registry (R4a–R4e):
         R4a: workspace_id must be present in registry — BLOCKING if missing.
         R4b: status must not be 'archived' — BLOCKING; warn if 'paused' or 'completed'.
         R4c: runtime_version must be present — WARNING if missing.
         R4d: last_active must be present — WARNING if missing.
         R4e (M10 revision): count entries with status:active in runtime/workspaces.md.
              Case A — Normal: exactly one active entry; its workspace_id = resolver_workspace_id → continue.
              Case B — Drift: exactly one active entry; its workspace_id ≠ resolver_workspace_id →
                       BLOCKING: STATUS: BLOCKED — WORKSPACE DRIFT DETECTED. Resolver names
                       <resolver_workspace_id>; registry active entry is <registry_active_workspace_id>.
                       Run /workspace-lifecycle SWITCH to synchronize runtime/current_workspace.md.
              Case C — Resolver absent: resolver_workspace_id is null; one active entry in registry →
                       BLOCKING: STATUS: BLOCKED — RESOLVER ABSENT. Registry identifies
                       <registry_active_workspace_id> as active but runtime/current_workspace.md is
                       absent or empty. Run /workspace-lifecycle SWITCH <registry_active_workspace_id>.
              Case D — No active entry: zero status:active entries in registry →
                       BLOCKING: STATUS: BLOCKED — NO ACTIVE WORKSPACE. Registry has no status:active
                       entry. Run /workspace-lifecycle SWITCH to designate an active workspace.
              Case E — Multiple active entries: more than one status:active entry in registry →
                       BLOCKING: STATUS: BLOCKED — REGISTRY INTEGRITY VIOLATION. Multiple status:active
                       entries in runtime/workspaces.md. Manual correction required.
Step W5: All subsequent paths are prefixed with WORKSPACE_ROOT.
```

## Workspace Isolation

All file operations must target paths prefixed with `WORKSPACE_ROOT`.

Exceptions (not workspace-scoped): `runtime/current_workspace.md`, `runtime/workspaces.md`, `docs/`, `templates/`, `.claude/`

Any operation targeting a path outside `WORKSPACE_ROOT` that is not on the exception list must be rejected and reported as workspace contamination.

---

## Preconditions

Before execution:

1. The repository structure must be valid.
2. At least one extracted knowledge artifact must exist in:

```text
WORKSPACE_ROOT/knowledge_base/extracted/
```

3. The following artifacts must be available:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/detect-conflicts.md
${CLAUDE_PLUGIN_ROOT}/docs/commands/detect-conflicts_execution.md
${CLAUDE_PLUGIN_ROOT}/templates/commands/detect_conflicts_prompt.md
```

---

## Execution

### Step 1 — Load Specifications

Read and understand:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/detect-conflicts.md
${CLAUDE_PLUGIN_ROOT}/docs/commands/detect-conflicts_execution.md
${CLAUDE_PLUGIN_ROOT}/templates/commands/detect_conflicts_prompt.md
```

The repository is the source of truth.

Ignore any prior conversational assumptions not present in the repository.

---

### Step 2 — Discover Artifacts

Inspect:

```text
WORKSPACE_ROOT/knowledge_base/extracted/
```

Build the list of all `*_knowledge.md` files.

---

### Step 3 — Parse Artifacts

For each artifact:

* Read sections and items.
* Record which sections are present and which are absent.
* Record the source reference.

---

### Step 4 — Detect Conflicts

Apply all three detection phases in sequence:

1. AMBIGUITY — per artifact, per item.
2. CONTRADICTION — cross-artifact, per category.
3. GAP — cross-artifact category comparison.

Follow all detection rules defined in:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/detect-conflicts_execution.md
```

---

### Step 5 — Assemble Conflict Records

For each detected conflict:

* Assign conflict ID (C001, C002, ...).
* Set type, severity, status.
* Record full traceability.

If zero conflicts are detected, prepare an explicit empty report.

---

### Step 6 — Generate and Persist Report

Write the conflict report to:

```text
WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md
```

Overwrite if the file already exists.

---

## Validation

Before completing, verify that:

* all artifacts in `WORKSPACE_ROOT/knowledge_base/extracted/` have been analyzed;
* every conflict record has a type, severity, status, and traceable source reference;
* the report has been written to the correct location.

---

## Failure Handling

Stop execution and report an explicit error when:

* no `*_knowledge.md` files exist in `WORKSPACE_ROOT/knowledge_base/extracted/`;
* an artifact cannot be read;
* repository structure is invalid;
* a conflict record cannot be traced to a source artifact.

Do not silently continue after a blocking failure.

---

## Completion Criteria

Execution is complete when:

* all artifacts have been analyzed;
* the conflict report has been generated;
* `WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md` has been written;
* every conflict record is traceable.

---

## Expected Output

```text
WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md
```

No other repository areas are modified by this command.
