# /generate-questions

## Purpose

Generate targeted clarification questions from open conflict records.

This command consumes `WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md` and produces
a canonical question artifact for pipeline consumption and a human-readable artifact
for stakeholder review.

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

2. The conflict report must exist and be readable:

```text
WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md
```

3. The following specification artifacts must be available:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/generate-questions.md
${CLAUDE_PLUGIN_ROOT}/docs/commands/generate-questions_execution.md
${CLAUDE_PLUGIN_ROOT}/templates/commands/generate_questions_prompt.md
```

---

## Execution

### Step 1 — Load Specifications

Read and understand:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/generate-questions.md
${CLAUDE_PLUGIN_ROOT}/docs/commands/generate-questions_execution.md
${CLAUDE_PLUGIN_ROOT}/templates/commands/generate_questions_prompt.md
```

The repository is the source of truth.

Ignore any prior conversational assumptions not present in the repository.

---

### Step 2 — Execute Prompt Template

Execute the runtime instructions defined in:

```text
${CLAUDE_PLUGIN_ROOT}/templates/commands/generate_questions_prompt.md
```

All question generation rules, conflict parsing rules, record assembly rules,
artifact generation rules, and output rules are defined in the prompt template and
execution specification.

Do not introduce business logic beyond what is defined in the specification artifacts.

---

## Validation

Before completing, verify that:

* `WORKSPACE_ROOT/knowledge_base/questions/questions_report.md` exists and is readable;
* `WORKSPACE_ROOT/output/generated_questions/questions_for_review.md` exists and is readable;
* `WORKSPACE_ROOT/knowledge_base/questions/questions_report.md` is not empty;
* `WORKSPACE_ROOT/output/generated_questions/questions_for_review.md` is not empty;
* every canonical question record references a valid `conflict_id` from the source
  conflicts report.

Exception: if the source conflict report contained zero open conflicts, both output
files may contain the approved explicit empty-report content as defined in the prompt
template. This outcome is valid and considered a successful execution.

---

## Failure Handling

Stop execution and report an explicit error when:

* `WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md` does not exist;
* any specification artifact cannot be read;
* output artifacts were not generated.

Do not silently continue after a blocking failure.

---

## Completion Criteria

Execution is complete when:

* `WORKSPACE_ROOT/knowledge_base/questions/questions_report.md` has been written;
* `WORKSPACE_ROOT/output/generated_questions/questions_for_review.md` has been written;
* every canonical question record is traceable to an originating conflict.

---

## Expected Output

```text
WORKSPACE_ROOT/knowledge_base/questions/questions_report.md
WORKSPACE_ROOT/output/generated_questions/questions_for_review.md
```

No other repository areas are modified by this command.
