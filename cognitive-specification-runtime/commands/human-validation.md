# /human-validation

## Purpose

Conduct a Human Validation session against open question records.

This command is interactive. It presents eligible questions to the human actor, collects answers and evidence, records decisions, updates canonical question records, and writes a traceable validation session record.

This command implements Step 5 — Human Validation of the CSR pipeline.

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

2. All specification artifacts must exist and be readable:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/human-validation.md
${CLAUDE_PLUGIN_ROOT}/docs/commands/human-validation_execution.md
${CLAUDE_PLUGIN_ROOT}/templates/prompts/human_validation_prompt.md
```

3. The canonical question registry must exist and be readable:

```text
WORKSPACE_ROOT/knowledge_base/questions/questions_report.md
```

4. At least one question with status `UNANSWERED`, `PARTIALLY_ANSWERED`, or `REJECTED` must be present in the question registry. Status values are treated as case-insensitive.

5. The validations output directory must exist:

```text
WORKSPACE_ROOT/input/validations/
```

If any precondition fails, report the failure explicitly and stop. Do not proceed to execution.

---

## Execution

### Step 1 — Load Specifications

Read and assimilate:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/human-validation.md
${CLAUDE_PLUGIN_ROOT}/docs/commands/human-validation_execution.md
${CLAUDE_PLUGIN_ROOT}/templates/prompts/human_validation_prompt.md
```

The repository is the source of truth.

Ignore any prior conversational assumptions not present in the repository.

All execution procedures are defined in `${CLAUDE_PLUGIN_ROOT}/docs/commands/human-validation_execution.md`.

All behavioral constraints, decision rules, and artifact format requirements are defined in `${CLAUDE_PLUGIN_ROOT}/templates/prompts/human_validation_prompt.md`.

---

### Step 2 — Execute Human Validation Session

Execute the runtime defined in:

```text
${CLAUDE_PLUGIN_ROOT}/templates/prompts/human_validation_prompt.md
```

The session is interactive. Conduct it in the following order as defined in the execution specification:

1. Scan the validation artifact inventory and determine the next session ID.
2. Collect session metadata from the human actor (session source, actors).
3. Present eligible questions to the human actor and collect the selection of questions to address.
4. For each addressed question: collect answer data, evidence, decisions, and target status with explicit human confirmation.
5. Update canonical question records.
6. Handle SUPERSEDED transitions where applicable.
7. Write the validation session record.
8. Run post-execution validation rules QR1–QR12.

Do not introduce business logic beyond what is defined in the specification artifacts.

Do not close, validate, reject, or answer any question without explicit human authorization recorded in the current session.

---

## Validation

Before reporting completion, verify that:

* the session record exists at `WORKSPACE_ROOT/input/validations/<session_id>.md` and is readable;
* every `question_id` addressed in the session has an updated `**Status:**` field in `WORKSPACE_ROOT/knowledge_base/questions/questions_report.md`;
* every updated question record has an `**Answer Source:**` field referencing the current `session_id`;
* every updated question record has an `**Answer Date:**` field;
* all original question fields (question_id, conflict_id, Conflict Type, Severity, question text, Context block) are unchanged;
* all post-execution validation rules QR1–QR12 defined in the execution specification pass.

---

## Failure Handling

Stop execution and report an explicit error when:

* any specification artifact cannot be read;
* `WORKSPACE_ROOT/knowledge_base/questions/questions_report.md` does not exist or cannot be read;
* no eligible questions exist after filtering;
* `WORKSPACE_ROOT/input/validations/` is inaccessible;
* a session ID collision is detected;
* a write failure occurs on the canonical question registry or the session record.

Do not silently continue after a blocking failure.

For session record write failure after canonical records have been updated: append a RECOVERY NOTE to each affected question record as defined in the execution specification, report all affected question IDs, and stop.

---

## Completion Criteria

Execution is complete when:

* at least one question was addressed in the session;
* the session record has been written to `WORKSPACE_ROOT/input/validations/<session_id>.md`;
* all addressed questions have updated status and answer fields in `WORKSPACE_ROOT/knowledge_base/questions/questions_report.md`;
* every answer record is traceable to the current session record;
* post-execution validation rules QR1–QR12 pass.

---

## Expected Output

```text
WORKSPACE_ROOT/knowledge_base/questions/questions_report.md   ← updated in-place
WORKSPACE_ROOT/input/validations/<session_id>.md              ← new session record
```

No other repository areas are modified by this command.
