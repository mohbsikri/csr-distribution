# /validate-specification

## Purpose

Cross-check a specification artifact against its source knowledge artifact to assess content coverage, producing a structured report identifying business rules, technical rules, terms, and workflows present in the knowledge base that are absent from the specification.

---

## Workspace Resolution

Before any file operation, resolve the active workspace:

```text
Step W1: Read runtime/current_workspace.md and parse workspace_id.
         If absent or empty: record resolver_workspace_id as null; skip W2–W3; proceed to W4.
Step W2: Build WORKSPACE_ROOT = workspaces/<workspace_id>/
Step W3: Verify WORKSPACE_ROOT exists. If not found, stop and report:
         STATUS: VALIDATE BLOCKED — Workspace Root Not Found: workspaces/<workspace_id>/
Step W4: Read runtime/workspaces.md. Validate registry (R4a–R4e):
         R4a: workspace_id must be present in registry — BLOCKING if missing.
         R4b: status must not be 'archived' — BLOCKING; warn if 'paused' or 'completed'.
         R4c: runtime_version must be present — WARNING if missing.
         R4d: last_active must be present — WARNING if missing.
         R4e (M10 revision): count entries with status:active in runtime/workspaces.md.
              Case A — Normal: exactly one active entry; its workspace_id = resolver_workspace_id → continue.
              Case B — Drift: exactly one active entry; its workspace_id ≠ resolver_workspace_id →
                       BLOCKING: STATUS: VALIDATE BLOCKED — WORKSPACE DRIFT DETECTED.
              Case C — Resolver absent: resolver_workspace_id is null; one active entry in registry →
                       BLOCKING: STATUS: VALIDATE BLOCKED — RESOLVER ABSENT.
              Case D — No active entry: zero status:active entries in registry →
                       BLOCKING: STATUS: VALIDATE BLOCKED — NO ACTIVE WORKSPACE.
              Case E — Multiple active entries: more than one status:active entry →
                       BLOCKING: STATUS: VALIDATE BLOCKED — REGISTRY INTEGRITY VIOLATION.
Step W5: All subsequent paths are prefixed with WORKSPACE_ROOT.
```

---

## Workspace Isolation

This command is **read-only** with one exception.

The only permitted write operation is:

```text
WORKSPACE_ROOT/output/validation/
```

No specification artifact, knowledge artifact, generation log, or lifecycle registry is created or modified. No path outside `output/validation/` is written.

Exceptions (not workspace-scoped, read-only): `runtime/current_workspace.md`, `runtime/workspaces.md`, `docs/`, `.claude/`

---

## Invocation

```text
/validate-specification [<base>]
```

* `<base>` — optional; the specification base name (without `_specification.md` suffix).
  If omitted: the single eligible specification in the active workspace is used automatically.
  If multiple candidates exist and `<base>` is omitted: `STATUS: VALIDATE BLOCKED — multiple candidates; specify <base>`.

---

## Preconditions

1. Active workspace resolves correctly (W1–W5, R4a–R4e).
2. Specification exists at `WORKSPACE_ROOT/specifications/draft/<base>_specification.md` (DRAFT) or `WORKSPACE_ROOT/specifications/stable/<base>_specification.md` (BASELINED).
3. Generation log `WORKSPACE_ROOT/specifications/draft/specifications_report.md` is present and readable.
4. The `Source Artifact` field for `<base>` in the generation log resolves to an existing knowledge artifact.

---

## Execution

### Step 1 — Load Specifications

Read and assimilate:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/validate-specification.md
${CLAUDE_PLUGIN_ROOT}/docs/commands/validate-specification_execution.md
```

The repository is the source of truth.

### Step 2 — Execute Validation Runtime

Execute the runtime defined in:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/validate-specification_execution.md
```

Phases: workspace resolution → specification location → knowledge artifact resolution → parse knowledge artifact → parse specification → compute coverage → assemble report → write report → validate SV1–SV6 → completion report.

---

## Expected Output

```text
WORKSPACE_ROOT/output/validation/<base>_spec_validation_<date>.md
```

The coverage report is also rendered to the conversation.

---

## Completion Reporting

```text
STATUS: VALIDATE COMPLETE
STATUS: VALIDATE BLOCKED
```
