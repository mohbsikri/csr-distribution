# /export-spec

## Purpose

Export a canonical BASELINED specification as a structured JSON or YAML document. The exported file is a machine-readable, system-agnostic representation of the specification for downstream pipeline consumption.

---

## Workspace Resolution

Before any file operation, resolve the active workspace:

```text
Step W1: Read runtime/current_workspace.md and parse workspace_id.
         If absent or empty: record resolver_workspace_id as null; skip W2–W3; proceed to W4.
Step W2: Build WORKSPACE_ROOT = workspaces/<workspace_id>/
Step W3: Verify WORKSPACE_ROOT exists. If not found, stop and report:
         STATUS: EXPORT BLOCKED — Workspace Root Not Found: workspaces/<workspace_id>/
Step W4: Read runtime/workspaces.md. Validate registry (R4a–R4e):
         R4a: workspace_id must be present in registry — BLOCKING if missing.
         R4b: status must not be 'archived' — BLOCKING; warn if 'paused' or 'completed'.
         R4c: runtime_version must be present — WARNING if missing.
         R4d: last_active must be present — WARNING if missing.
         R4e (M10 revision): count entries with status:active in runtime/workspaces.md.
              Case A — Normal: exactly one active entry; its workspace_id = resolver_workspace_id → continue.
              Case B — Drift: exactly one active entry; its workspace_id ≠ resolver_workspace_id →
                       BLOCKING: STATUS: EXPORT BLOCKED — WORKSPACE DRIFT DETECTED.
              Case C — Resolver absent: resolver_workspace_id is null; one active entry in registry →
                       BLOCKING: STATUS: EXPORT BLOCKED — RESOLVER ABSENT.
              Case D — No active entry: zero status:active entries in registry →
                       BLOCKING: STATUS: EXPORT BLOCKED — NO ACTIVE WORKSPACE.
              Case E — Multiple active entries: more than one status:active entry →
                       BLOCKING: STATUS: EXPORT BLOCKED — REGISTRY INTEGRITY VIOLATION.
Step W5: All subsequent paths are prefixed with WORKSPACE_ROOT.
```

---

## Workspace Isolation

This command is **read-only** with one exception.

The only permitted write operation is:

```text
WORKSPACE_ROOT/output/exports/
```

No specification artifact, knowledge artifact, generation log, or lifecycle registry is created or modified. No path outside `output/exports/` is written.

Exceptions (not workspace-scoped, read-only): `runtime/current_workspace.md`, `runtime/workspaces.md`, `docs/`, `.claude/`

---

## Invocation

```text
/export-spec [<base>] [--format json|yaml]
```

* `<base>` — optional; the specification base name (without `_specification.md` suffix).
  If omitted: the single BASELINED specification in the active workspace is used automatically.
  If multiple BASELINED candidates exist and `<base>` is omitted: `STATUS: EXPORT BLOCKED — multiple candidates; specify <base>`.
* `--format` — optional; output format. Accepted values: `json`, `yaml`. Default: `json`.

---

## Preconditions

1. Active workspace resolves correctly (W1–W5, R4a–R4e).
2. Target specification exists at `WORKSPACE_ROOT/specifications/stable/<base>_specification.md`.
3. Specification header contains `**Status:** BASELINED`.
4. `${CLAUDE_PLUGIN_ROOT}/docs/commands/export-spec.md` and `${CLAUDE_PLUGIN_ROOT}/docs/commands/export-spec_execution.md` exist and are readable.

---

## Step 1 — Load Specifications

Read and assimilate:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/export-spec.md
${CLAUDE_PLUGIN_ROOT}/docs/commands/export-spec_execution.md
```

The repository is the source of truth.

---

## Step 2 — Execute Export Runtime

Execute the runtime defined in:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/export-spec_execution.md
```

Phases: workspace resolution → specification location → parse specification header → parse specification body → assemble export document → write output → validate ES1–ES6 → completion report.

---

## Expected Output

```text
WORKSPACE_ROOT/output/exports/<base>_export_<date>.json
```

or

```text
WORKSPACE_ROOT/output/exports/<base>_export_<date>.yaml
```

The export file is also summarized in the conversation completion report.

---

## Completion Reporting

```text
STATUS: EXPORT COMPLETE
Base: <base>
Format: json|yaml
Output: output/exports/<base>_export_<date>.json
Sections exported: N
Business Rules exported: N
Technical Rules exported: N
Constraints exported: N
Terms exported: N
Workflows exported: N
```

```text
STATUS: EXPORT BLOCKED
```
