# Human Validation Execution Specification

## Purpose

Define the runtime execution procedure for the `/human-validation` command.

The objective is to consume eligible question records from the canonical question registry, collect human answers, evidence, and decisions across one or more validation sessions, and produce traceable validation session records and updated canonical question records.

This specification implements Step 5 — Human Validation of the CSR pipeline.

---

## Execution Flow

```text
Workspace Resolution
↓
Question Loading
↓
Session Registry Scan
↓
Session Registration (metadata collection)
↓
Question Matching (human selection)
↓
Human Confirmation (answer collection)
↓
Question State Update (canonical records written)
↓
Historical Preservation (SUPERSEDED handling)
↓
Session Record Output (session file written)
↓
Validation Rules Check
```

---

## Runtime Version Reference

The runtime version is referenced throughout this specification as `CURRENT_RUNTIME_VERSION`.

At execution time, `CURRENT_RUNTIME_VERSION` must be read from:

```text
docs/implementation_status.md
```

Locate the section `## Current Version` and extract the version value.

This value must never be hardcoded. Every reference to `CURRENT_RUNTIME_VERSION` is a runtime-resolved placeholder.

---

## Preconditions

Before execution begins, verify:

| ID | Precondition | Action on Failure |
| -- | ------------ | ----------------- |
| P1 | `docs/commands/human-validation.md` exists and is readable | Stop. Report missing contract. |
| P2 | Workspace runtime resolves (R1–R7 pass in Phase 1) | Stop. Report workspace failure. |
| P3 | `WORKSPACE_ROOT/knowledge_base/questions/questions_report.md` exists and is readable | Stop. Report missing question registry. |
| P4 | At least one question with status UNANSWERED, PARTIALLY_ANSWERED, or REJECTED exists in the registry | Stop. Report no eligible questions. Do not create a session record. |
| P5 | `WORKSPACE_ROOT/input/validations/` directory exists | Stop. Report missing validations directory. |

If any precondition fails, report the failure explicitly and stop. Do not proceed to execution.

---

## Phase 1 — Workspace Resolution

### Objective

Establish the active workspace root path and validate workspace integrity before any artifact operation.

### R1 — Read Current Workspace

Read:

```text
runtime/current_workspace.md
```

Parse the `workspace_id` value from:

```text
workspace_id: <value>
```

### R2 — Build Workspace Root

Construct:

```text
WORKSPACE_ROOT = workspaces/<workspace_id>/
```

All subsequent artifact paths are constructed as `WORKSPACE_ROOT + <relative path within workspace>`.

### R3 — Verify Workspace Root

Confirm the directory `WORKSPACE_ROOT` exists.

If not found:

```text
STATUS: BLOCKED — Workspace Root Not Found: workspaces/<workspace_id>/
```

Stop execution.

### R4 — Validate Registry Entry

Read `runtime/workspaces.md`. Locate the row where `workspace_id` matches the value from R1.

#### R4a — Workspace ID Present

If no matching row exists:

```text
STATUS: BLOCKED — Workspace Drift Detected: workspace_id '<value>' not found in runtime/workspaces.md
```

Stop execution.

#### R4b — Status Field

If the matching row `status` is `archived`:

```text
STATUS: BLOCKED — Workspace Archived: workspace_id '<value>' must not be used for active processing
```

Stop execution.

If the matching row `status` is `paused` or `completed`:

```text
STATUS: WARNING — Workspace Drift: registry status is '<status>' for workspace_id '<value>'
```

Document the discrepancy. Continue with caution.

#### R4c — runtime_version Field

If `runtime_version` is empty or missing:

```text
STATUS: WARNING — Registry Entry Incomplete: runtime_version missing for workspace_id '<value>'
```

Continue.

#### R4d — last_active Field

If `last_active` is empty or missing:

```text
STATUS: WARNING — Registry Entry Incomplete: last_active missing for workspace_id '<value>'
```

Continue.

#### R4e — Single Active Entry

If more than one registry row has `status: active`:

```text
STATUS: WARNING — Workspace Drift: multiple active entries in runtime/workspaces.md
```

Use `runtime/current_workspace.md` as the authority. Continue.

### R5 — Confirm Resolution

Report:

```text
Active workspace: <workspace_id>
WORKSPACE_ROOT: workspaces/<workspace_id>/
```

### R6 — Isolation Enforcement

All file operations must target paths prefixed with `WORKSPACE_ROOT`.

Shared exception paths (not workspace-scoped):
- `runtime/current_workspace.md`
- `runtime/workspaces.md`
- `docs/`
- `templates/`
- `.claude/`

Any operation targeting a path outside `WORKSPACE_ROOT` that is not on the exception list must be rejected immediately:

```text
STATUS: BLOCKED — Workspace Contamination: <path> is outside WORKSPACE_ROOT and not on the exception list
```

**STATUS: WORKSPACE RESOLVED**

---

## Phase 2 — Question Loading

### Objective

Load and parse the canonical question registry. Identify questions eligible for this validation session. Build the sorted Eligible Question Set for human review.

### Inputs

```text
WORKSPACE_ROOT/knowledge_base/questions/questions_report.md   ← primary input
WORKSPACE_ROOT/output/generated_questions/questions_for_review.md   ← human review context only, not modified
```

### Actions

**Step 2.1** — Verify `WORKSPACE_ROOT/knowledge_base/questions/questions_report.md` exists and is readable.

**Step 2.2** — Read the full file content.

**Step 2.3** — Parse all question records from the `## Questions` section. For each `### Q<NNN>` block, extract:

| Field | Location in record |
| ----- | ------------------ |
| `question_id` | `### Q<NNN>` section header |
| `conflict_id` | `**Conflict ID:**` field |
| `Conflict Type` | `**Conflict Type:**` field |
| `Severity` | `**Severity:**` field |
| `Status` | `**Status:**` field |
| `Question` | `**Question:**` field |
| Context block | Full `**Context:**` sub-block including Source, Section, Content, and Reason (if present) |

**Step 2.4** — Apply status normalization: treat all status values as case-insensitive during loading. Normalize to UPPERCASE internally. The upstream value `unanswered` is equivalent to `UNANSWERED`.

**Step 2.5** — Filter to eligible questions: retain only questions where normalized status is `UNANSWERED`, `PARTIALLY_ANSWERED`, or `REJECTED`. Discard all others.

**Step 2.6** — If zero eligible questions remain after filtering: report explicitly and stop without creating a session record:

```text
No eligible questions found (UNANSWERED, PARTIALLY_ANSWERED, or REJECTED).
No session created.
```

**Step 2.7** — Sort the Eligible Question Set for presentation:

1. BLOCKING severity first:
   - Sub-order within BLOCKING: REJECTED → UNANSWERED → PARTIALLY_ANSWERED
2. ADVISORY severity second:
   - Sub-order within ADVISORY: REJECTED → UNANSWERED → PARTIALLY_ANSWERED

### Failure Conditions

- `questions_report.md` does not exist → stop. Report: P3 failed.
- `questions_report.md` cannot be read → stop. Report read failure.
- A question record cannot be parsed to extract required fields → stop. Report the question_id and the missing field.
- Zero eligible questions after filtering → stop. Report. No session created.

### Output

```text
Eligible Question Set (sorted by severity and status)
Count: <N> eligible questions
```

**STATUS: QUESTIONS LOADED — \<N\> eligible questions**

---

## Phase 3 — Validation Artifact Discovery

### Objective

Determine the next valid session ID by inspecting the existing validation record inventory.

### Actions

**Step 3.1** — Confirm `WORKSPACE_ROOT/input/validations/` is accessible.

**Step 3.2** — List all files in the directory matching the pattern `VS<NNN>.md` where `<NNN>` is a zero-padded three-digit integer. Extract the numeric component from each matching filename. Record these as the **File-Based Session ID Set**.

**Step 3.3** — Scan `WORKSPACE_ROOT/knowledge_base/questions/questions_report.md` for all `**Answer Source:**` field values. Parse the numeric component from each `VS<NNN>` value found. Record these as the **Record-Referenced Session ID Set**.

This step is required to detect session IDs that were assigned and referenced in canonical records but for which no session file was written — for example, following a Phase 9.4 rollback. If an `Answer Source` value cannot be parsed as `VS<NNN>`, skip it and continue.

**Step 3.4** — Build the **Known Session ID Set** = File-Based Session ID Set ∪ Record-Referenced Session ID Set.

**Step 3.5** — Determine the next session ID:
- If the Known Session ID Set is empty: next session ID is `VS001`.
- Otherwise: next session ID is `VS<highest N in Known Set + 1>`, zero-padded to three digits.

**Step 3.6** — Confirm the computed session ID does not already exist as a file. If it does: stop and report a session ID collision.

### Session ID Convention

```text
VS001, VS002, VS003, ...
```

Session IDs are sequential integers zero-padded to three digits, prefixed with `VS`. They are assigned in order of session creation within a workspace. IDs do not reset across question report cycles or across `/generate-questions` runs.

### Failure Conditions

- `input/validations/` directory is inaccessible → stop. Report access failure.
- Computed next session ID already exists as a file → stop. Report collision. Do not proceed.

### Output

```text
File-based sessions: <list of VS<NNN>.md filenames, or 'None'>
Record-referenced sessions (no file): <list of VS<NNN> found in Answer Source fields but absent as files, or 'None'>
Next session ID: VS<NNN>
```

**STATUS: SESSION REGISTRY SCANNED — Next session ID: VS\<NNN\>**

---

## Phase 4 — Validation Session Registration

### Objective

Assign the session identifier and collect session metadata from the human actor. Build the session record header in context. Do not write to disk at this phase.

### Actions

**Step 4.1** — Assign `session_id` from Phase 3 output.

**Step 4.2** — Record `session_date` as the current ISO 8601 date (YYYY-MM-DD).

**Step 4.3** — Collect from the human actor:

| Field | Description |
| ----- | ----------- |
| `session_source` | Context or trigger for this session. Examples: "stakeholder review", "expert consultation", "document review", "requirements workshop". |
| `actors` | Named participants in this session. At least one actor must be named. |

**Step 4.4** — Build the session record header in context (not written to disk):

```markdown
# Validation Session <session_id>

**Session Date:** <ISO 8601 date>
**Session Source:** <context or trigger>
**Actors:** <participant names or roles>
```

### Output

```text
session_id: VS<NNN>
session_date: <YYYY-MM-DD>
session_source: <value>
actors: <value>
Session record header: in context, not yet written to disk
```

**STATUS: SESSION REGISTERED — session_id: VS\<NNN\>**

---

## Phase 5 — Question Matching

### Objective

Present eligible questions to the human actor. Collect the human actor's selection of which questions to address in this session. Record default resolutions for skipped ADVISORY questions if provided.

### Actions

**Step 5.1** — Present the Eligible Question Set to the human actor in the sorted order from Phase 2.

**Step 5.2** — For each question in the set, display:
- `question_id` and current `Status`
- `Severity` (BLOCKING or ADVISORY)
- Full question text
- Full Context block (Source, Section, Content, Reason if present)
- For PARTIALLY_ANSWERED questions: the existing partial answer block from the canonical record (Answer, Answer Source, Answer Date, Evidence, Decision fields as recorded in the prior session)
- For REJECTED questions: the rejected answer block and all rejection fields (Rejection Reason, Rejected By, Rejection Date) from the canonical record

**Step 5.3** — Ask the human actor which questions to address in this session. A session is not required to address all eligible questions.

**Step 5.4** — Record the selected subset as the **Addressed Question Set** for this session.

**Step 5.5** — If the human actor selects zero questions: stop. Do not create a session record.

**Step 5.6** — For each ADVISORY question the human actor explicitly skips: offer the option to record a default resolution.
- If a default resolution is provided: record it as a decision entry in the session record's Decisions section.
- A default resolution does not change the question's status. The question remains UNANSWERED (or its current eligible status) until a future session addresses it.

### Evidence Restriction

Evidence may be presented to the human actor to inform their review.

Evidence may support or suggest answers.

Evidence may never determine or automatically set the status of a question.

Status changes require explicit human input. The execution must not derive a status from evidence content.

### Failure Conditions

- Human actor selects zero questions → stop. Report. No session record created.

### Output

```text
Addressed Question Set: <list of question_ids>
Skipped ADVISORY default resolutions: <list, or 'None'>
```

**STATUS: QUESTIONS PRESENTED — \<N\> questions selected for this session**

---

## Phase 6 — Human Confirmation

### Objective

Collect complete answer data for each addressed question. Apply the Human Authority Principle at every step. Record all required traceability fields.

### For Each Question in the Addressed Question Set

#### Step 6.1 — Present Question

Display the full question record:
- `question_id`, `conflict_id`, current `Status`, `Severity`
- Full question text
- Full Context block
- All existing answer blocks present in the canonical record, in order: prior partial answers, prior rejected answer blocks with rejection fields, prior validated answer blocks. This provides full prior-session context for PARTIALLY_ANSWERED and REJECTED questions.

#### Step 6.2 — Determine Answer Path (REJECTED questions only)

This step applies only when the question's current status is REJECTED.

Before collecting answer data, ask the human actor to choose:

- **Re-open (UNANSWERED)**: the question will revert to UNANSWERED for answering in a future session. No answer is collected now. Skip Steps 6.3–6.5. Proceed to Step 6.6 with target status `UNANSWERED`. No answer block will be written.
- **Revise answer (ANSWERED)**: a corrected answer will be provided in this session. Continue to Step 6.3 to collect the revised answer text.

For questions with any other current status (UNANSWERED, PARTIALLY_ANSWERED), this step is skipped. Proceed to Step 6.3.

#### Step 6.3 — Collect Answer

Collect from the human actor:

- `answer_text`: the human-provided answer. May not be empty. Required for all target statuses except UNANSWERED (from REJECTED).

#### Step 6.4 — Collect Evidence

Collect from the human actor:

- `evidence`: a reference to supporting materials (document name, file path, section title) or the literal string `None`.

Evidence is recorded verbatim. No inference, interpretation, or status suggestion may be derived from evidence content.

#### Step 6.5 — Collect Decision

Collect from the human actor:

- `decision`: an explicit decision text associated with this answer, or the literal string `None`.

#### Step 6.6 — Determine Target Status

Ask the human actor to specify the target status for this question.

Valid initial transitions from eligible starting states:

| Current Status (normalized) | Valid Target Statuses |
| --------------------------- | -------------------- |
| UNANSWERED | PARTIALLY_ANSWERED, ANSWERED |
| PARTIALLY_ANSWERED | PARTIALLY_ANSWERED, ANSWERED |
| REJECTED | UNANSWERED, ANSWERED |

If the human actor requests a transition not in this table:

```text
STATUS: INVALID TRANSITION — <from> → <to> is not a valid lifecycle transition for <question_id>
```

Do not apply the transition. Ask the human actor to specify a valid target status. Do not stop the session.

#### Step 6.7 — VALIDATED Transition

This step applies when the question was just transitioned to ANSWERED in step 6.6 within the current session, and the human actor is also the designated validator and wishes to immediately confirm the answer.

Required when target status is VALIDATED (the question must have just reached ANSWERED status in step 6.6 of this session):

Collect:
- `validated_by`: the name or role of the designating validator. May not be empty or 'None'.
- `validation_date`: current ISO 8601 date.

#### Step 6.8 — REJECTED Transition

This step applies when the question was just transitioned to ANSWERED in step 6.6 within the current session, and a reviewer finds the recorded answer insufficient.

Required when target status is REJECTED (the question must have just reached ANSWERED status in step 6.6 of this session):

Collect:
- `rejection_reason`: the reason the answer was found insufficient. May not be empty.
- `rejected_by`: the name or role of the reviewing actor. May not be empty.
- `rejection_date`: current ISO 8601 date.

#### Step 6.9 — SUPERSEDED Transition

This step applies when the question was just transitioned to VALIDATED in step 6.7 within the current session, and the human actor determines the newly validated answer must be immediately replaced.

Required when target status is SUPERSEDED (the question must have just reached VALIDATED status in step 6.7 of this session):

A SUPERSEDED transition means a previously validated answer is replaced by a newer answer.

Collect:
- `superseded_on`: current ISO 8601 date.
- `superseded_by_session`: current `session_id`.
- Replacement answer using steps 6.3–6.5.
- Ask whether the replacement answer should be immediately VALIDATED in this session.
  - If yes: collect `validated_by` and `validation_date` per step 6.7.

#### Step 6.10 — Sequential Transitions Within a Session

A question may undergo sequential transitions within a single session.

Example: A question with status UNANSWERED may transition to ANSWERED (step 6.6) and then to VALIDATED (step 6.7) within the same session.

In such cases:
- Apply steps 6.3–6.6 for the first transition (skip step 6.2 for non-REJECTED questions).
- Apply the appropriate additional step (6.7 or 6.8) for the subsequent transition.
- The session record's `Status Before` column records the original status at session start.
- The session record's `Status After` column records the final status after all transitions.

### Human Authority Principle

At no point may a question status be set without explicit human confirmation.

Prohibited:
- Setting status based on evidence content alone.
- Inferring answer completeness from answer length or phrasing.
- Advancing a question through multiple lifecycle states in a single action without separate human confirmation for each transition.

### Output

```text
Answer Data Set — one record per addressed question:
  question_id, answer_text, evidence, decision, target_status
  + validated_by / validation_date (if VALIDATED)
  + rejection_reason / rejected_by / rejection_date (if REJECTED)
  + supersession metadata (if SUPERSEDED)
```

**STATUS: ANSWERS COLLECTED — \<N\> questions answered**

---

## Phase 7 — Question State Update

### Objective

Apply collected answer data to the canonical question records. Append answer blocks. Update status fields. Write changes to disk.

### Pre-Write Consistency Check

Before writing any question update, verify:

1. The target transition is valid per the lifecycle table in Phase 6.6.
2. All required answer fields are present:

| Target Status | Required Fields |
| ------------- | --------------- |
| PARTIALLY_ANSWERED | answer_text, Answer Source (session_id), Answer Date, Evidence, Decision |
| ANSWERED | answer_text, Answer Source (session_id), Answer Date, Evidence, Decision |
| VALIDATED | All ANSWERED fields + Validated By, Validation Date |
| REJECTED | All ANSWERED fields + Rejection Reason, Rejected By, Rejection Date |
| UNANSWERED (from REJECTED) | No answer block written — status reverts only |
| SUPERSEDED | Handled in Phase 8 |

If a required field is missing: do not write that question. Report the missing field. Ask the human actor to provide it before writing.

### Update Procedure

For each question in the Addressed Question Set, apply the following steps:

**Step 7.1** — Read the current state of the question record from `WORKSPACE_ROOT/knowledge_base/questions/questions_report.md`.

**Step 7.2** — Verify all original fields are intact and will not be modified:
- `question_id`
- `conflict_id`
- `Conflict Type`
- `Severity`
- Full question text
- Full Context block

**Step 7.3** — Append the answer block below the existing Context block:

```markdown
**Answer:** <human-provided answer text>
**Answer Source:** <session_id>
**Answer Date:** <ISO 8601 date>
**Evidence:** <reference or 'None'>
**Decision:** <decision text or 'None'>
```

**Step 7.4** — Append additional fields based on target status:

For VALIDATED:

```markdown
**Validated By:** <actor name or role>
**Validation Date:** <ISO 8601 date>
```

For REJECTED:

```markdown
**Rejection Reason:** <reason the answer was found insufficient>
**Rejected By:** <actor name or role>
**Rejection Date:** <ISO 8601 date>
```

For UNANSWERED (from REJECTED): do not append an answer block. Update the Status field only.

**Step 7.5** — Update the `**Status:**` field in the question record to the new UPPERCASE target status value.

**Step 7.6** — Verify the updated question record:
- All original fields unchanged
- Answer block present and complete (where applicable)
- Status field updated to UPPERCASE target status

### Write Target

```text
WORKSPACE_ROOT/knowledge_base/questions/questions_report.md
```

Updates are applied in-place. The file is not replaced in full. Only the affected question record sections are modified.

### Failure Conditions

- A required answer field is missing → do not write that question. Report the missing field. The session may continue for other questions.
- The transition is not valid per lifecycle table → do not write. Report. The session may continue for other questions.
- The file cannot be written → stop all remaining updates. Report. Initiate rollback procedure (see Phase 11).

**STATUS: QUESTION RECORDS UPDATED — \<N\> questions updated**

---

## Phase 8 — Historical Preservation

### Objective

Apply preservation rules for questions transitioning to SUPERSEDED status. Ensure original validated answer blocks are retained in full when replaced.

### When Phase 8 Applies

Phase 8 applies only when at least one question transitions to SUPERSEDED status.

For all other status transitions, Phase 8 is a pass-through with no action required.

### SUPERSEDED Procedure

For each question transitioning to SUPERSEDED:

**Step 8.1** — Confirm the original answer block (including Validated By and Validation Date) is present and complete in the question record. Do not remove or modify it.

**Step 8.2** — Append the supersession marker below the original answer block:

```markdown
**Superseded On:** <ISO 8601 date>
**Superseded By Session:** <session_id>
```

**Step 8.3** — Append the replacement answer block using the standard Answer Record Format:

```markdown
**Answer:** <replacement answer text>
**Answer Source:** <session_id>
**Answer Date:** <ISO 8601 date>
**Evidence:** <reference or 'None'>
**Decision:** <decision text or 'None'>
```

**Step 8.4** — If the replacement answer is immediately VALIDATED in this session, append:

```markdown
**Validated By:** <actor name or role>
**Validation Date:** <ISO 8601 date>
```

**Step 8.5** — Update the `**Status:**` field to `SUPERSEDED`.

### SUPERSEDED vs REJECTED

| Attribute | SUPERSEDED | REJECTED |
| --------- | ---------- | -------- |
| Prior required status | VALIDATED | ANSWERED |
| Original answer | Preserved in full (unmodified) | Preserved for reference |
| Replacement answer | Required — provided in the same session | Not required at rejection time |
| New lifecycle state | SUPERSEDED | REJECTED |
| Re-answering required | No — replacement provided in the same transition | Yes — question must be re-answered in a subsequent session |
| Meaning | Previously validated answer replaced by a newer validated answer | Answer found insufficient; requires revision |

### Output

Updated question records with preserved original blocks and supersession markers where applicable.

**STATUS: HISTORICAL PRESERVATION COMPLETE**

---

## Phase 9 — Output Generation

### Objective

Build and write the validation session record to disk. Verify all outputs. Confirm traceability between the session record and updated question records.

### Step 9.1 — Build Session Record

Assemble the complete session record from data collected in Phases 4–8:

```markdown
# Validation Session <session_id>

**Session Date:** <ISO 8601 date>
**Session Source:** <context or trigger>
**Actors:** <participant names or roles>

---

## Questions Addressed

| Question ID | Status Before | Status After | Answer Summary |
| ----------- | ------------- | ------------ | -------------- |
| Q<NNN>      | <UNANSWERED>  | <ANSWERED>   | <one-line summary of the answer> |

---

## Evidence

<list of supporting materials with source references, or 'None'>

---

## Decisions

<list of explicit decisions recorded during this session, or 'None'>
```

Rules for the Questions Addressed table:
- `Status Before`: the normalized status of the question at the start of this session (before any Phase 7 updates).
- `Status After`: the final status of the question after all transitions applied in this session.
- `Answer Summary`: one-line distillation of the answer text. Must be present for all transitions except UNANSWERED.

### Step 9.2 — Write Session Record

Write the session record to:

```text
WORKSPACE_ROOT/input/validations/<session_id>.md
```

If a file already exists at this path: stop. Report collision. Do not overwrite.

### Step 9.3 — Verify Session Record

After writing:
- Confirm the file exists and is readable.
- Confirm it lists all `question_id` values from the Addressed Question Set.
- Confirm the `Status Before` and `Status After` columns match the transitions applied in Phase 7.
- Confirm the `Evidence` section lists all evidence references cited across Phase 6 answer collection.
- Confirm the `Decisions` section lists all decisions recorded, including any ADVISORY default resolutions from Phase 5.

### Step 9.4 — Rollback on Session Write Failure

If Step 9.2 fails after Phase 7 has already written updates to the canonical question records:

1. Identify all question records that were updated in Phase 7.
2. The canonical records reference a `session_id` (`VS<NNN>`) for which no session file exists.
3. This constitutes an incomplete session. Append the following note to each affected question record in `questions_report.md`:

```markdown
**RECOVERY NOTE:** Session record <session_id> write failed. This question update is untraced. Manual resolution required before proceeding to the next session.
```

4. Report the failure and the list of affected `question_id` values explicitly.
5. Do not create a partial session record file.
6. Stop execution.

**STATUS: SESSION RECORD WRITTEN — \<session_id\>**

---

## Phase 10 — Validation Rules

### Objective

Verify post-execution consistency across all updated artifacts. Confirm all traceability requirements are satisfied.

### Rules

| Rule | Check |
| ---- | ----- |
| QR1 | Every updated question record has an `Answer Source` field referencing the current `session_id`. |
| QR2 | Every updated question record has an `Answer Date` field containing a valid ISO 8601 date. |
| QR3 | Every question record reaching VALIDATED status has a `Validated By` field containing a named actor (not empty, not 'None'). |
| QR4 | Every question record reaching REJECTED status has `Rejection Reason`, `Rejected By`, and `Rejection Date` fields. |
| QR5 | No original question field (question_id, conflict_id, Conflict Type, Severity, question text, Context block) was modified. |
| QR6 | Every status transition applied in this session is present in the lifecycle transition table. |
| QR7 | The session record lists every `question_id` updated during this session. |
| QR8 | The session record `Actors` field references the actors who participated and confirmed answers in this session. |
| QR9 | For every SUPERSEDED question: the original answer block is present and unmodified before the supersession marker. |
| QR10 | The session record `session_id` does not match any previously existing session file in `WORKSPACE_ROOT/input/validations/`. |
| QR11 | BLOCKING questions that reach VALIDATED status are flagged for downstream `/consolidate-knowledge` to proceed on the affected conflict. |
| QR12 | For ADVISORY questions with a recorded default resolution: the default resolution appears in the session record's Decisions section. |

### Verification Procedure

Check QR1–QR12 against the written artifacts after Phase 9 completes.

For each failed rule:
- Report the rule ID, the affected artifact path, and the specific violation.
- Classify: BLOCKING (prevents correct downstream consumption) or WARNING (traceability gap, does not block but must be documented).

**STATUS: VALIDATION RULES CHECKED**

---

## Phase 11 — Failure Handling

### Stop Conditions

| Condition | Response |
| --------- | -------- |
| `questions_report.md` does not exist | Stop. Report: P3 failed. |
| `questions_report.md` cannot be read | Stop. Report read failure and path. |
| A question record cannot be parsed | Stop. Report the question_id and the missing field. |
| Zero eligible questions after filtering | Stop. Report. No session created. |
| Human actor selects zero questions | Stop. No session created. |
| Invalid status transition requested | Reject the transition. Ask for a valid target. Do not stop the session. |
| Required answer field missing before write | Do not write that question. Report missing field. Session may continue for other questions. |
| `input/validations/` directory is inaccessible | Stop. Report access failure. |
| Session ID collision | Stop. Report the collision. Do not overwrite. |
| Session record write failure (after canonical updates) | Append RECOVERY NOTE to all affected question records. Report affected question IDs. Stop. |
| Workspace isolation violation | Stop immediately. Report the contaminating path. |
| R4a — workspace_id not in registry | Stop. Report workspace drift (BLOCKING). |
| R4b — workspace status is `archived` | Stop. Report workspace archived (BLOCKING). |
| R4b — workspace status is `paused` or `completed` | Warn. Continue with caution. Document discrepancy. |
| R4e — multiple active workspaces in registry | Warn. Use `runtime/current_workspace.md` as authority. Continue. |
| `questions_report.md` write fails during update | Stop all remaining updates. Report. Initiate rollback. |

### Rollback Procedure

If a write failure occurs after partial updates to `questions_report.md`:

1. Identify all question records that were successfully written before the failure.
2. Identify all question records that were not written.
3. Report the split explicitly: written question IDs and unwritten question IDs.
4. If the session record was not written: append a RECOVERY NOTE to all successfully written question records.
5. Do not create a partial session record file.
6. Report the execution state as INCOMPLETE. Require manual resolution before the next session.

### Recovery Note Format

```markdown
**RECOVERY NOTE:** Session record <session_id> write failed. This question update is untraced. Manual resolution required before proceeding to the next session.
```

---

## Phase 12 — Completion Criteria

Execution is complete when all of the following are true:

* [ ] At least one question was addressed in this session.
* [ ] All addressed questions have an updated `**Status:**` field in `WORKSPACE_ROOT/knowledge_base/questions/questions_report.md`.
* [ ] All addressed questions have a complete answer block appended to their question record (where applicable per target status).
* [ ] Every answer block carries `**Answer Source:**` referencing the current `session_id`.
* [ ] Every answer block carries `**Answer Date:**`.
* [ ] All VALIDATED records carry `**Validated By:**` and `**Validation Date:**`.
* [ ] All REJECTED records carry `**Rejection Reason:**`, `**Rejected By:**`, and `**Rejection Date:**`.
* [ ] All SUPERSEDED records preserve the original answer block unmodified, followed by the supersession marker, followed by the replacement answer block.
* [ ] All original question fields (question_id, conflict_id, Conflict Type, Severity, question text, Context block) are unchanged.
* [ ] The session record exists at `WORKSPACE_ROOT/input/validations/<session_id>.md`.
* [ ] The session record lists all `question_id` values addressed in this session with Status Before and Status After columns.
* [ ] Every applied transition is valid per the lifecycle transition table.
* [ ] No question status was changed without an explicit human action recorded in the session.
* [ ] Validation Rules QR1–QR12 pass.

**STATUS: HUMAN VALIDATION COMPLETE**

---

## Out of Scope — Milestone 5

The following capabilities are explicitly deferred and must not be implemented as part of this specification.

### MATCH_CANDIDATE Workflow

**Decision: B — Future Validation Assistance capability. Not part of Milestone 5.**

A MATCH_CANDIDATE workflow would allow the runtime to propose candidate answers derived from evidence in the knowledge base, with the human actor confirming or rejecting each proposal. This is architecturally distinct from answer collection (the current model) for the following reasons:

1. MATCH_CANDIDATE requires knowledge graph traversal and semantic matching against the extracted knowledge base — infrastructure not present in the current runtime.
2. The Layer 1 contract (`docs/commands/human-validation.md`) defines no MATCH_CANDIDATE state, no proposal lifecycle, and no candidate confirmation mechanism. Adding MATCH_CANDIDATE to Layer 2 without Layer 1 grounding violates the specification hierarchy.
3. Answer collection and answer suggestion are different interaction models requiring separate contract design and human authority scoping.

MATCH_CANDIDATE is deferred to a future `/validation-assistance` capability or a future revision of `/human-validation` that operates with full knowledge graph integration.

This specification implements answer collection only. The Human Authority Principle ("evidence may suggest answers; evidence may never automatically close questions") governs all evidence handling within this scope.
