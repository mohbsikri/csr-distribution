# /pipeline-status

## Purpose

Query the current pipeline state of the active workspace. Non-interactive and read-only.

Produces a stage-by-stage status report showing what has been completed, what is in progress, what is blocked, and the next recommended action.

This command implements no pipeline stage. It is a diagnostic query that can be invoked at any point in the CSR workflow.

---

## Inputs

No inputs beyond active workspace resolution.

---

## Outputs

Status report rendered to conversation and written to:

```text
WORKSPACE_ROOT/runtime/pipeline_status.md
```

---

## Pipeline Stage Model

| Stage | ID | Command | Completion Indicator |
|-------|----|---------|---------------------|
| 0 | PP | /preprocess-source | Preprocessed artifact exists in `knowledge_base/preprocessed/` |
| 1 | EX | /extract-knowledge | Extracted knowledge artifact exists in `knowledge_base/extracted/` |
| 2 | DC | /detect-conflicts | `knowledge_base/conflicts/conflicts_report.md` exists |
| 3 | GQ | /generate-questions | `knowledge_base/questions/questions_report.md` exists |
| 4 | HV | /human-validation | All BLOCKING questions have status VALIDATED or RESOLVED |
| 5 | CK | /consolidate-knowledge | `knowledge_base/consolidated/consolidation_report.md` exists |
| 6 | GS | /generate-specification | Specification exists in `specifications/draft/` or `specifications/stable/` |
| 7 | SL | /specification-lifecycle | At least one specification is BASELINED |
| 8 | GV | /generate-views | Views exist in `specifications/views/` |

---

## Stage Status Values

| Status | Meaning |
|--------|---------|
| `COMPLETE` | Stage artifacts exist and are in the expected terminal state |
| `IN_PROGRESS` | Stage artifacts exist but work is not finished (e.g., unanswered questions) |
| `NOT_STARTED` | No artifacts detected for this stage |
| `BLOCKED` | A required prior stage is not COMPLETE |

---

## Next Action

The status report always includes a **Next Recommended Action** — the command to run to advance the pipeline, stated in business language. If the pipeline is fully complete, the next action is `/generate-views` if views are absent or `—` if views are current.

---

## Workspace Resolution

Standard R4a–R4e workspace resolution applies. If workspace resolution fails, report `STATUS: PIPELINE STATUS BLOCKED` with the specific failure.

---

## Execution Rules

1. Resolve workspace (W1–W5, R4a–R4e).
2. Read all stage indicator artifacts.
3. Compute status for each stage.
4. Compute next recommended action.
5. Write status report to `WORKSPACE_ROOT/runtime/pipeline_status.md`.
6. Render status report to conversation.

---

## Failure Cases

Stop and report `STATUS: PIPELINE STATUS BLOCKED` when:

* Workspace resolution fails at any W step.
* `runtime/pipeline_status.md` cannot be written.

Unreadable or absent stage indicators are treated as `NOT_STARTED` for that stage — never as a failure.

---

## Completion Reporting

```text
STATUS: PIPELINE STATUS COMPLETE
STATUS: PIPELINE STATUS BLOCKED
```

---

## Validation Rules

| Rule | Check | Class |
|------|-------|-------|
| PS1 | All 9 stages reported with a non-empty status value | BLOCKING |
| PS2 | `WORKSPACE_ROOT/runtime/pipeline_status.md` exists and is readable after write | BLOCKING |
| PS3 | No write operations targeted any path outside `WORKSPACE_ROOT/runtime/` | BLOCKING |
| PS4 | Next Recommended Action is present and non-empty, or explicitly `—` if pipeline is complete | BLOCKING |
| PS5 | Stage statuses are internally consistent: a stage cannot be `COMPLETE` if a required prior stage is `NOT_STARTED` | WARNING |
| PS6 | Report timestamp matches current execution date | WARNING |
