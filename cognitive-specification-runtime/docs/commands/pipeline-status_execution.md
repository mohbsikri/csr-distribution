# /pipeline-status — Execution Specification

---

## Phase 1 — Workspace Resolution

Identical to all CSR commands: W1 → W5, R4a → R4e.

Build WORKSPACE_ROOT = workspaces/<workspace_id>/

On any blocking failure: report `STATUS: PIPELINE STATUS BLOCKED — <reason>`. Stop.

---

## Phase 2 — Stage Artifact Discovery

Attempt to read the completion indicators defined in the L1 contract for each stage (0–8). Build a `stage_status_map` in memory. Absent or unreadable artifacts are treated as `NOT_STARTED` — never as a failure.

### Stage PP (0) — Preprocess

Scan: `WORKSPACE_ROOT/knowledge_base/preprocessed/` for files matching `*_preprocessed.md`.

| Outcome | Status |
|---------|--------|
| One or more files found | COMPLETE |
| No files found / directory absent | NOT_STARTED |

Record: count of matching files.

---

### Stage EX (1) — Extract

Scan: `WORKSPACE_ROOT/knowledge_base/extracted/` for files matching `*_knowledge*.md`.

| Outcome | Status |
|---------|--------|
| One or more files found | COMPLETE |
| No files found / directory absent | NOT_STARTED |

Record: count of matching files.

---

### Stage DC (2) — Detect Conflicts

Check existence: `WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md`.

| Outcome | Status |
|---------|--------|
| File exists | COMPLETE |
| File absent | NOT_STARTED |

---

### Stage GQ (3) — Generate Questions

Check existence: `WORKSPACE_ROOT/knowledge_base/questions/questions_report.md`.

| Outcome | Status |
|---------|--------|
| File exists | COMPLETE |
| File absent | NOT_STARTED |

---

### Stage HV (4) — Human Validation

Precondition: `WORKSPACE_ROOT/knowledge_base/questions/questions_report.md` must exist.

If questions_report.md absent: `NOT_STARTED`.

If questions_report.md exists:
1. Read the file.
2. Count questions that satisfy both conditions: status is not `VALIDATED` AND status is not `RESOLVED` AND class is `BLOCKING`.
3. Apply:

| Outcome | Status | Detail |
|---------|--------|--------|
| 0 BLOCKING questions pending | COMPLETE | all resolved |
| N > 0 BLOCKING questions pending | IN_PROGRESS | N BLOCKING questions pending |

---

### Stage CK (5) — Consolidate Knowledge

Check existence: `WORKSPACE_ROOT/knowledge_base/consolidated/consolidation_report.md`.

| Outcome | Status |
|---------|--------|
| File exists | COMPLETE |
| File absent | NOT_STARTED |

---

### Stage GS (6) — Generate Specification

Scan:
- `WORKSPACE_ROOT/specifications/draft/` for files matching `*_specification.md` (exclude any file named `specifications_report.md`)
- `WORKSPACE_ROOT/specifications/stable/` for files matching `*_specification.md`

Combine both scans. Count distinct matching files.

| Outcome | Status |
|---------|--------|
| One or more files found | COMPLETE |
| No files found / directories absent | NOT_STARTED |

Record: count of matching files.

---

### Stage SL (7) — Specification Lifecycle

Check existence: `WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md`.

If absent: `NOT_STARTED`.

If present:
1. Read the file.
2. Locate the **Active State Index** section.
3. Count entries with status `BASELINED`.

| Outcome | Status | Detail |
|---------|--------|--------|
| At least one BASELINED entry | COMPLETE | N BASELINED |
| Registry exists, zero BASELINED entries | IN_PROGRESS | none BASELINED |

---

### Stage GV (8) — Generate Views

Scan: `WORKSPACE_ROOT/specifications/views/` for files matching `*_view_*.md`.

| Outcome | Status |
|---------|--------|
| One or more files found | COMPLETE |
| No files found / directory absent | NOT_STARTED |

Record: count of matching files.

---

## Phase 3 — Consistency Check

Apply rule PS5: a stage cannot be `COMPLETE` if a required prior stage is `NOT_STARTED`.

Pipeline dependency chain (each stage requires all prior stages):

```text
PP(0) → EX(1) → DC(2) → GQ(3) → HV(4) → CK(5) → GS(6) → SL(7) → GV(8)
```

For each stage with status `COMPLETE`, verify that no prior stage in the chain has status `NOT_STARTED`.

If inconsistency detected: emit a WARNING entry in the report. Do **not** change the computed statuses — report them as-is.

---

## Phase 4 — Next Recommended Action

Scan stages in order 0 → 8.

1. If a stage has status `IN_PROGRESS`: next action = the command for that stage. Report: `<command> — complete this stage before advancing`.
2. Else if a stage has status `NOT_STARTED` (and no IN_PROGRESS found): next action = the command for that stage. Report: `<command> — this stage has not been started`.
3. If all 9 stages are `COMPLETE`: next action = `—`. Report: `Pipeline is fully complete`.

Command mapping:

| Stage | Command |
|-------|---------|
| PP (0) | /preprocess-source |
| EX (1) | /extract-knowledge |
| DC (2) | /detect-conflicts |
| GQ (3) | /generate-questions |
| HV (4) | /human-validation |
| CK (5) | /consolidate-knowledge |
| GS (6) | /generate-specification |
| SL (7) | /specification-lifecycle |
| GV (8) | /generate-views |

---

## Phase 5 — Write Status Report

Create `WORKSPACE_ROOT/runtime/` if absent.

Write `WORKSPACE_ROOT/runtime/pipeline_status.md` with the following format:

```markdown
# Pipeline Status — <workspace_id>

**Generated:** <YYYY-MM-DD>
**Workspace:** <workspace_id>

---

## Stage Status

| Stage | ID | Command | Status | Details |
|-------|----|---------|--------|---------|
| Preprocess | PP | /preprocess-source | <STATUS> | <N> artifact(s) found / — |
| Extract | EX | /extract-knowledge | <STATUS> | <N> artifact(s) found / — |
| Detect Conflicts | DC | /detect-conflicts | <STATUS> | — |
| Generate Questions | GQ | /generate-questions | <STATUS> | — |
| Human Validation | HV | /human-validation | <STATUS> | <N> BLOCKING questions pending / all resolved |
| Consolidate | CK | /consolidate-knowledge | <STATUS> | — |
| Generate Spec | GS | /generate-specification | <STATUS> | <N> spec(s) found / — |
| Lifecycle | SL | /specification-lifecycle | <STATUS> | <N> BASELINED / none |
| Generate Views | GV | /generate-views | <STATUS> | <N> view(s) found / — |

---

## Next Recommended Action

**<command or —>** <one-line explanation>

---

## Warnings

<any PS5 consistency warnings, or "None">
```

Detail column rules:

| Stage | Detail when COMPLETE | Detail when NOT_STARTED | Detail when IN_PROGRESS |
|-------|----------------------|------------------------|------------------------|
| PP | `<N> artifact(s) found` | `—` | — |
| EX | `<N> artifact(s) found` | `—` | — |
| DC | `—` | `—` | — |
| GQ | `—` | `—` | — |
| HV | `all resolved` | `—` | `<N> BLOCKING questions pending` |
| CK | `—` | `—` | — |
| GS | `<N> spec(s) found` | `—` | — |
| SL | `<N> BASELINED` | `—` | `none BASELINED` |
| GV | `<N> view(s) found` | `—` | — |

On write failure: report `STATUS: PIPELINE STATUS BLOCKED — cannot write runtime/pipeline_status.md`. Stop.

---

## Phase 6 — Validation Rules PS1–PS6

Apply each rule after the report is written.

| Rule | Check | Class | On Failure |
|------|-------|-------|-----------|
| PS1 | All 9 stages have a non-empty status value in the report | BLOCKING | `STATUS: PIPELINE STATUS BLOCKED — PS1: missing status for stage <ID>` |
| PS2 | `WORKSPACE_ROOT/runtime/pipeline_status.md` exists and is readable after write | BLOCKING | `STATUS: PIPELINE STATUS BLOCKED — PS2: report not readable after write` |
| PS3 | No write operations targeted any path outside `WORKSPACE_ROOT/runtime/` | BLOCKING | `STATUS: PIPELINE STATUS BLOCKED — PS3: write operation outside WORKSPACE_ROOT/runtime/` |
| PS4 | Next Recommended Action field is present and non-empty, or explicitly `—` | BLOCKING | `STATUS: PIPELINE STATUS BLOCKED — PS4: Next Recommended Action is missing or empty` |
| PS5 | Stage statuses are internally consistent (a stage cannot be COMPLETE if a required prior stage is NOT_STARTED) | WARNING | Emit warning in report — do not stop |
| PS6 | Report timestamp matches current execution date | WARNING | Emit warning in report — do not stop |

On any BLOCKING rule failure: stop and report the specific failure. Do not proceed to Phase 7.

---

## Phase 7 — Completion Report

```text
STATUS: PIPELINE STATUS COMPLETE
Workspace: <workspace_id>
Report: WORKSPACE_ROOT/runtime/pipeline_status.md
Stages complete: <N>/9
Next action: <command or —>
```
