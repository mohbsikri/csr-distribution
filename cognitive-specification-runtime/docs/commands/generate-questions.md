# /generate-questions

## Purpose

Transform open conflict records into targeted clarification questions that enable Human Validation.

The command consumes the conflict report produced by `/detect-conflicts` and produces two artifacts: a canonical structured question record for pipeline consumption, and a human-readable derived artifact for stakeholder review and answer entry.

---

## Inputs

The command reads:

```text
workspaces/<workspace_id>/knowledge_base/conflicts/conflicts_report.md
```

Fields consumed from each conflict record:

| Field | Used for |
| ----- | -------- |
| `conflict_id` | Question-to-conflict traceability link |
| `Type` | Question generation rule selection |
| `Severity` | Question priority assignment |
| `Status` | Processing filter — only `open` conflicts are processed |
| `Description` | Question context and derived artifact summary |
| `Source` | Traceability in canonical question record |
| `Section` | Traceability in canonical question record; context in derived artifact |
| `Content` | Question grounding — exact item text |
| `Reason` | AMBIGUITY records only — question specificity |

---

## Outputs

### Canonical Artifact

```text
workspaces/<workspace_id>/knowledge_base/questions/questions_report.md
```

Structured question records for pipeline consumption.

Contains full traceability fields. This is the authoritative question artifact consumed by downstream stages.

### Derived Artifact

```text
workspaces/<workspace_id>/output/generated_questions/questions_for_review.md
```

Human-readable version rendered from the canonical artifact.

Formatted for stakeholder review and answer entry. Does not contain internal pipeline fields (`conflict_id`, `Status`, `Source` filepath).

An empty report (zero open conflicts) is a valid output for both artifacts.

---

## Question Generation Rules

Each open conflict generates exactly one question.

Questions must be specific, grounded in the content of the originating conflict, and directly actionable. Generic or invented questions are not permitted.

### AMBIGUITY

Ask for a precise definition or clarification of the undefined or insufficiently specified term or condition.

The question must identify the exact term or condition requiring clarification and what criteria would make it unambiguous for downstream specification use.

### CONTRADICTION

Ask which of the opposing claims is authoritative, or whether a reconciliation rule exists that allows both to apply under defined conditions.

The question must make the conflict between the two items explicit and ask for a resolution that can be applied to the specification.

### GAP

Ask whether the missing knowledge category is required for the source where it is absent, and if so, what its content should be.

The question must identify which source lacks the section and reference the source where it is present.

---

## Question Priority

| Severity | Handling |
| -------- | -------- |
| BLOCKING | Question is mandatory. Human Validation must not proceed on the affected conflict until the question is answered and a resolution is recorded. |
| ADVISORY | Question is informational. Human Validation may proceed with a documented default resolution if the question is not answered. |

---

## Question Status

Questions carry a status field that tracks their lifecycle from generation through resolution.

| Status | Description |
| ------ | ----------- |
| `unanswered` | Question has been generated. No human answer has been recorded. Initial state set by `/generate-questions`. |
| `answered` | A human answer has been recorded in `workspaces/<workspace_id>/input/validations/`. Transition managed by Human Validation (Step 5). |
| `resolved` | The answer has been validated and incorporated by `/consolidate-knowledge`. Transition managed by Step 6. |

`/generate-questions` sets the initial status only. It does not manage subsequent transitions.

---

## Question Record Format

Each question in the canonical artifact must follow this structure:

```markdown
## <question_id>

**Conflict ID:** <conflict_id>
**Conflict Type:** CONTRADICTION | AMBIGUITY | GAP
**Severity:** BLOCKING | ADVISORY
**Status:** unanswered

**Question:** [specific, targeted question text grounded in the conflict content]

**Context:**
- Source: `workspaces/<workspace_id>/knowledge_base/extracted/<file>.md`
- Section: `# <Section>`
- Content: `<exact item text from conflict record>`
```

For AMBIGUITY records, append to Context:

```markdown
- Reason: `<reason field from conflict record>`
```

---

## Derived Artifact Format

Each question in the derived artifact must follow this structure:

```markdown
## Question <question_id>

**Priority:** BLOCKING | ADVISORY

<question text>

**Context:**
- Section: `# <Section>`
- Item: `<exact item text>`

**Answer:** _(please fill in)_

---
```

Internal pipeline fields (`conflict_id`, `Status`, `Source` filepath) are not included in the derived artifact.

---

## Question ID Convention

Question IDs are sequential integers zero-padded to three digits, prefixed with `Q`:

```text
Q001, Q002, Q003, ...
```

IDs are assigned in order of the originating conflict ID. They reset on each new report generation.

---

## Preconditions

`workspaces/<workspace_id>/knowledge_base/conflicts/conflicts_report.md` must exist and be readable.

Repository structure must be valid.

---

## Execution Rules

The command shall:

1. Read `workspaces/<workspace_id>/knowledge_base/conflicts/conflicts_report.md`.
2. Parse all conflict records.
3. Filter to records with `Status: open`.
4. For each open conflict, apply the type-specific question generation rule.
5. Assign question IDs (Q001, Q002, ...) in order of conflict ID.
6. Assemble canonical question records with full traceability.
7. Write the canonical artifact to `workspaces/<workspace_id>/knowledge_base/questions/questions_report.md`.
8. Render and write the derived artifact to `workspaces/<workspace_id>/output/generated_questions/questions_for_review.md`.

If zero open conflicts remain after filtering, write an explicit empty report to both output paths and stop.

---

## Validation Rules

Each question record must be:

* linked to a `conflict_id` that exists in the source conflicts report;
* grounded in the content of the originating conflict — the question text must reference or derive from the `Content` field of the conflict record;
* assigned `Status: unanswered`;
* traceable to a source artifact and section via the originating conflict record.

A question must not be invented. Every question must derive from an open conflict record.

---

## Language Policy

Generated question text must be written in English.

The Context block in each question record reproduces content from upstream conflict records. Conflict records inherit English content from extracted knowledge artifacts per the `/detect-conflicts` language policy. Question context is therefore English.

If upstream conflict records contain non-English content, this indicates an upstream ADR-001 compliance gap. Report it explicitly. Do not generate questions from non-English conflict content.

---

## Failure Cases

The command must stop when:

* `workspaces/<workspace_id>/knowledge_base/conflicts/conflicts_report.md` does not exist;
* the conflicts report cannot be read;
* repository structure is invalid;
* a question record cannot be linked to an originating conflict.

Failures must be reported explicitly.

---

## Traceability Rules

Every canonical question record must reference:

* the originating `conflict_id`;
* the conflict type and severity;
* the source artifact filename;
* the section name;
* the exact content of the affected item.

Traceability must remain available for downstream stages: Human Validation (Step 5) reads question records to determine what requires human input; `/consolidate-knowledge` reads question records to match validated answers back to their originating conflicts.

---

## Completion Criteria

The command is complete when:

* all open conflicts in `workspaces/<workspace_id>/knowledge_base/conflicts/conflicts_report.md` have been processed;
* one question has been generated per open conflict;
* `workspaces/<workspace_id>/knowledge_base/questions/questions_report.md` has been written;
* `workspaces/<workspace_id>/output/generated_questions/questions_for_review.md` has been written;
* every canonical question record is traceable to an originating conflict.
