# /diff-specification

## Purpose

Compare two versions of a specification and produce a structured delta report showing what changed between them.

---

## Workspace Resolution

Before any file operation, resolve the active workspace:

```text
Step W1: Read runtime/current_workspace.md and parse workspace_id.
         If absent or empty: record resolver_workspace_id as null; skip W2–W3; proceed to W4.
Step W2: Build WORKSPACE_ROOT = workspaces/<workspace_id>/
Step W3: Verify WORKSPACE_ROOT exists. If not found, stop and report:
         STATUS: DIFF BLOCKED — Workspace Root Not Found: workspaces/<workspace_id>/
Step W4: Read runtime/workspaces.md. Validate registry (R4a–R4e):
         R4a: workspace_id must be present in registry — BLOCKING if missing.
         R4b: status must not be 'archived' — BLOCKING; warn if 'paused' or 'completed'.
         R4c: runtime_version must be present — WARNING if missing.
         R4d: last_active must be present — WARNING if missing.
         R4e (M10 revision): count entries with status:active in runtime/workspaces.md.
              Case A — Normal: exactly one active entry; its workspace_id = resolver_workspace_id → continue.
              Case B — Drift: exactly one active entry; its workspace_id ≠ resolver_workspace_id →
                       BLOCKING: STATUS: DIFF BLOCKED — WORKSPACE DRIFT DETECTED.
              Case C — Resolver absent: resolver_workspace_id is null; one active entry in registry →
                       BLOCKING: STATUS: DIFF BLOCKED — RESOLVER ABSENT.
              Case D — No active entry: zero status:active entries in registry →
                       BLOCKING: STATUS: DIFF BLOCKED — NO ACTIVE WORKSPACE.
              Case E — Multiple active entries: more than one status:active entry →
                       BLOCKING: STATUS: DIFF BLOCKED — REGISTRY INTEGRITY VIOLATION.
Step W5: All subsequent paths are prefixed with WORKSPACE_ROOT.
```

---

## Workspace Isolation

This command is **read-only** on all specification artifacts and the lifecycle registry.

Write operations are restricted exclusively to:

```text
WORKSPACE_ROOT/output/diffs/
```

The following paths must never be written to or modified:

- `WORKSPACE_ROOT/specifications/` (all subdirectories)
- `WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md`
- Any other artifact outside `output/diffs/`

---

## Invocation

```text
/diff-specification <base> [--from <spec_id>] [--to <spec_id>]
```

- `<base>` — required; the specification base name (e.g., `ri-condi-colo-technical-documentation-v1`)
- `--from <spec_id>` — optional; the older version Spec ID to compare from (default: most recent SUPERSEDED, resolved from the Event Log)
- `--to <spec_id>` — optional; the newer version Spec ID to compare to (default: current BASELINED)

---

## Preconditions

1. Active workspace resolves correctly (W1–W5).
2. Lifecycle registry exists at `WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md`.
3. `<base>` is present in the Active State Index of the lifecycle registry.
4. At least two versions of `<base>` exist: one currently BASELINED and at least one prior SUPERSEDED version (recorded in the Event Log via an EVOLVE event). If only one version exists, diff is blocked.

---

## Execution

### Step 1 — Load Specifications

Read and assimilate:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/diff-specification.md
${CLAUDE_PLUGIN_ROOT}/docs/commands/diff-specification_execution.md
```

The repository is the source of truth.

### Step 2 — Execute Diff Runtime

Execute the runtime defined in:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/diff-specification_execution.md
```

Phases:
1. Workspace Resolution
2. Version Resolution (lifecycle registry → from/to paths)
3. Load Specifications (header + body partition)
4. Dimension-by-dimension Comparison (7 dimensions)
5. Assemble Delta Report
6. Write Report to `output/diffs/`
7. Validation Rules DS1–DS6
8. Completion Report

---

## Expected Output

```text
WORKSPACE_ROOT/output/diffs/<base>_diff_<from_spec_id>_vs_<to_spec_id>_<date>.md
```

The `output/diffs/` directory is created if absent.

---

## Completion Reporting

```text
STATUS: DIFF COMPLETE
STATUS: DIFF BLOCKED
```

On `DIFF COMPLETE`:

```text
STATUS: DIFF COMPLETE

From: <from_spec_id> (<from_path>)
To:   <to_spec_id> (<to_path>)
Output: output/diffs/<filename>

Summary: <N> added, <N> removed, <N> modified across all dimensions.

Validation: DS1 ✓  DS2 ✓  DS3 ✓  DS4 ✓  DS5 ✓  DS6 ✓
```

On `DIFF BLOCKED`:

```text
STATUS: DIFF BLOCKED — <reason>
```
