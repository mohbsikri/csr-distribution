# /consolidate-knowledge

## Purpose

Consume VALIDATED question records and produce transformed consolidated knowledge artifacts.

This command is non-interactive. It reads validated answers already recorded by `/human-validation`, resolves the underlying conflicts in the extracted knowledge base, and writes consolidated artifacts, an updated consolidation authority record, and RESOLVED question status transitions.

This command implements Step 6 — Knowledge Consolidation of the CSR pipeline.

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

1. All specification artifacts must exist and be readable:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/consolidate-knowledge.md
${CLAUDE_PLUGIN_ROOT}/docs/commands/consolidate-knowledge_execution.md
${CLAUDE_PLUGIN_ROOT}/templates/prompts/consolidate_knowledge_prompt.md
```

2. The canonical question registry must exist and be readable:

```text
WORKSPACE_ROOT/knowledge_base/questions/questions_report.md
```

3. The conflict report must exist and be readable:

```text
WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md
```

4. At least one `*_knowledge.md` file must exist in:

```text
WORKSPACE_ROOT/knowledge_base/extracted/
```

5. The consolidated output directory must exist:

```text
WORKSPACE_ROOT/knowledge_base/consolidated/
```

6. At least one question with status `VALIDATED` or `SUPERSEDED` with a validated replacement must be present in the question registry. Status values are treated as case-insensitive.

If any precondition fails, report the failure explicitly and stop. Do not proceed to execution.

---

## Execution

### Step 1 — Load Specifications

Read and assimilate:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/consolidate-knowledge.md
${CLAUDE_PLUGIN_ROOT}/docs/commands/consolidate-knowledge_execution.md
${CLAUDE_PLUGIN_ROOT}/templates/prompts/consolidate_knowledge_prompt.md
```

The repository is the source of truth.

Ignore any prior conversational assumptions not present in the repository.

All execution procedures are defined in `${CLAUDE_PLUGIN_ROOT}/docs/commands/consolidate-knowledge_execution.md`.

All behavioral constraints, decision rules, and artifact format requirements are defined in `${CLAUDE_PLUGIN_ROOT}/templates/prompts/consolidate_knowledge_prompt.md`.

---

### Step 2 — Execute Knowledge Consolidation Runtime

Execute the runtime defined in:

```text
${CLAUDE_PLUGIN_ROOT}/templates/prompts/consolidate_knowledge_prompt.md
```

Execution is non-interactive. Conduct it in the following order as defined in the execution specification:

1. Discover eligible conflicts: identify all conflicts whose associated questions are at VALIDATED status or SUPERSEDED with a validated replacement.
2. Apply re-run resolution: identify already-consolidated conflicts from `consolidation_report.md` and exclude them from processing.
3. Group conflicts into Source Groups and build the Resolution Map for each: AMBIGUITY and GAP conflicts are grouped by source artifact into Standard Source Groups (one consolidated artifact per group); each CONTRADICTION conflict forms its own PAIRED Source Group with two source artifacts and two consolidated artifacts written as an atomic pair (Item A write → verify → Item B write → verify → CONSOLIDATED gate).
4. Transform each source extracted knowledge artifact into consolidated knowledge artifacts: Standard Source Groups produce one consolidated artifact; PAIRED Source Groups (CONTRADICTION) produce two consolidated artifacts atomically — if Item B write fails after Item A succeeds, append PARTIAL_WRITE NOTE to Item A and mark the conflict CONSOLIDATION_FAILED.
5. Write or update `consolidation_report.md` with CONSOLIDATED entries for all processed conflicts.
6. Transition all associated questions to RESOLVED status in `questions_report.md`.
7. Run post-execution validation rules CK1–CK14.

Do not introduce business logic beyond what is defined in the specification artifacts.

Do not modify `knowledge_base/conflicts/conflicts_report.md` or any `*_knowledge.md` file in `knowledge_base/extracted/`.

Do not transition any question to RESOLVED before its conflict's consolidated artifact and `consolidation_report.md` entry are written and verified.

---

## Validation

Before reporting the completion state, verify that:

* every conflict in the Processing Set has an entry in `WORKSPACE_ROOT/knowledge_base/consolidated/consolidation_report.md` with status CONSOLIDATED or CONSOLIDATION_FAILED;
* every conflict recorded as CONSOLIDATED has a corresponding consolidated artifact at the declared path that exists and is readable; for CONTRADICTION conflicts: both the primary and secondary consolidated artifact paths exist and are readable;
* every question transitioned to RESOLVED in `WORKSPACE_ROOT/knowledge_base/questions/questions_report.md` carries `**Resolved By:**`, `**Resolution Date:**`, and `**Consolidated Artifact:**` fields with non-empty values; for questions whose conflict is CONTRADICTION: `**Consolidated Artifact (Secondary):**` is also present with a non-empty value;
* every RESOLVED question maps to a CONSOLIDATED conflict via `conflict_id`;
* `WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md` is unmodified;
* all source extracted knowledge artifacts in `WORKSPACE_ROOT/knowledge_base/extracted/` are unmodified;
* all post-execution validation rules CK1–CK14 defined in the execution specification pass.

---

## Failure Handling

Stop execution and report an explicit error when:

* any specification artifact cannot be read;
* `WORKSPACE_ROOT/knowledge_base/questions/questions_report.md` does not exist or cannot be read;
* `WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md` does not exist or cannot be read;
* `WORKSPACE_ROOT/knowledge_base/extracted/` contains no `*_knowledge.md` files;
* `WORKSPACE_ROOT/knowledge_base/consolidated/` is inaccessible;
* a VALIDATED or eligible-SUPERSEDED question record's `Answer`, `Evidence`, or `Decision` field contains non-English text — report ADR-001 compliance failure and stop before proceeding to conflict loading;
* a CONTRADICTION conflict in the Already-Consolidated Set is missing `**Consolidated Artifact (Secondary):**` in consolidation_report.md — report PARTIAL RECORD DETECTED and stop; do not classify as SKIP;
* no eligible conflicts exist after eligibility discovery and re-run resolution;
* a consolidated artifact cannot be written;
* `consolidation_report.md` cannot be written after consolidated artifacts are produced;
* a question record update cannot be written after `consolidation_report.md` is updated;
* a workspace isolation violation occurs.

Do not silently continue after a blocking failure.

For write failures after earlier artifacts have been produced: append a RECOVERY NOTE to all affected question records as defined in the execution specification, report all affected question IDs, and stop.

For per-source-group failures: continue processing remaining Source Groups. Declare CONSOLIDATION PARTIAL at completion.

---

## Completion Criteria

Execution is complete when:

* at least one conflict was successfully consolidated;
* a consolidated artifact exists for each Source Group processed; for PAIRED Source Groups (CONTRADICTION): both the primary and secondary consolidated artifacts exist;
* `WORKSPACE_ROOT/knowledge_base/consolidated/consolidation_report.md` has been written or updated with CONSOLIDATED entries for each processed conflict; CONTRADICTION records include `**Source Artifact (Secondary):**` and `**Consolidated Artifact (Secondary):**` fields;
* all associated VALIDATED or eligible-SUPERSEDED questions have been updated to RESOLVED status in `WORKSPACE_ROOT/knowledge_base/questions/questions_report.md`; CONTRADICTION question resolution blocks include `**Consolidated Artifact (Secondary):**`;
* all original question fields (question_id, conflict_id, Conflict Type, Severity, question text, Context block, all existing answer and validation blocks) are unchanged;
* post-execution validation rules CK1–CK14 pass.

---

## Completion Reporting

Report one of three completion states:

```text
STATUS: CONSOLIDATION COMPLETE
```

```text
STATUS: CONSOLIDATION PARTIAL
```

```text
STATUS: CONSOLIDATION BLOCKED
```

---

## Expected Output

```text
WORKSPACE_ROOT/knowledge_base/consolidated/<base>_consolidated.md  ← new or updated per source group
WORKSPACE_ROOT/knowledge_base/consolidated/consolidation_report.md ← written or updated in-place
WORKSPACE_ROOT/knowledge_base/questions/questions_report.md        ← updated in-place (RESOLVED status + resolution blocks)
```

No other repository areas are modified by this command.

`WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md` is read as input and must not be modified.

`WORKSPACE_ROOT/knowledge_base/extracted/*_knowledge.md` files are read as input and must not be modified.
