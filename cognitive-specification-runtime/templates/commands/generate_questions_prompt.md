# Generate Questions Prompt Template

You are executing the Cognitive Specification Runtime question generation stage.

Your objective is to transform open conflict records into targeted clarification questions that enable Human Validation.

You must follow repository rules and execution specifications.

---

# Context

The repository follows:

* Repository-first — the repository is the source of truth
* Markdown-first — all artifacts are stored as Markdown files
* Claude Code-first — Claude Code is the primary runtime engine
* Human-in-the-loop — Human Validation is required before consolidation proceeds
* Traceability-first — every question must link back to its originating conflict

Never invent questions.

Every question must derive from an open conflict record present in the source conflicts report.

Every question must be grounded in the exact content of the originating conflict record.

---

# Objective

The command operates in two stages.

## Global Stage

1. Load and parse the conflict report.
2. Filter to open conflicts only.

## Question Generation Stage

3. Generate one targeted question per open conflict.
4. Assemble canonical question records with full traceability.
5. Generate the canonical artifact.
6. Generate the derived artifact.
7. Write both artifacts to the repository.

---

# Input Discovery

Locate the conflict report at:

    knowledge_base/conflicts/conflicts_report.md

Verify the file exists.

Verify the file is readable.

If the file does not exist or cannot be read, stop execution and report the failure explicitly.

Read the full file content before proceeding.

---

# Conflict Parsing

Parse the conflict report in full.

## Metadata

Extract from the `## Metadata` section:

* Generated date
* Sources analyzed
* Total conflicts
* Blocking count
* Advisory count

## Summary Table

Extract all rows from the `## Summary` table:

* ID, Type, Severity, Status, Description

## Individual Conflict Records

For each `### C<NNN>` section under `## Conflicts`, extract:

| Field | Location |
| ----- | -------- |
| `conflict_id` | Section header — `### C001` |
| `Type` | `**Type:**` line |
| `Severity` | `**Severity:**` line |
| `Status` | `**Status:**` line |
| `Description` | `**Description:**` line |
| `Source` | `- Source:` line within Affected Item |
| `Section` | `- Section:` line within Affected Item |
| `Content` | `- Content:` line within Affected Item |
| `Reason` | `- Reason:` line — AMBIGUITY records only |

## Special Handling: CONTRADICTION Records

CONTRADICTION records contain two affected items (Item A and Item B).

Extract them separately.

For each item, capture:

* Source
* Section
* Content

Label them Item A and Item B as they appear in the record.

## Special Handling: GAP Records

GAP records contain `Absent from` and `Present in` lists.

Extract all entries from both lists.

---

# Open Conflict Filtering

After parsing, filter the conflict record inventory.

Process only records where `Status: open`.

Discard any record where Status is `answered` or `resolved`.

## Empty Set Behavior

If zero open conflicts remain after filtering:

* Do not generate any question records.
* Write an explicit empty report to both output paths.
* Report completion with zero questions generated.
* Stop.

---

# Question Generation Rules

For each open conflict, apply the rule for its Type.

Generate exactly one question per conflict.

The question must be specific and grounded. It must not be generic.

---

## AMBIGUITY

**Source fields to use:** `Content`, `Reason`

### Procedure

1. Read the `Content` field — this is the item that contains the ambiguous term or condition.
2. Read the `Reason` field — this explains why the item is ambiguous.
3. Identify the specific term or condition that is undefined or insufficiently precise.
4. Formulate a question that asks:
   * What the precise definition of that term is, or
   * What criteria determine whether the condition is satisfied, or
   * What measurable threshold or rule applies.

### Requirements

* The question must name the specific term or condition from the `Content` and `Reason` fields.
* The question must indicate what form of answer would resolve the ambiguity.
* The question text must reference the exact item from `Content`.
* Do not generate a generic question such as "Please clarify this item." The question must be specific to the identified ambiguity.

### Example

If `Content` is:

> Only validated knowledge may be used for specification generation.

And `Reason` is:

> "validated knowledge" is not defined. The criteria, process, and authority required for knowledge to be considered "validated" are unspecified.

Then an acceptable question is:

> The rule "Only validated knowledge may be used for specification generation" uses the term "validated knowledge," which is not defined. What is the precise definition of "validated knowledge"? What criteria, process, or authority must be satisfied for a piece of knowledge to be considered validated for specification use?

---

## CONTRADICTION

**Source fields to use:** Item A (`Source`, `Section`, `Content`), Item B (`Source`, `Section`, `Content`), `Description`

### Procedure

1. Read Item A `Content` — the first opposing claim.
2. Read Item B `Content` — the second opposing claim.
3. Confirm that the two claims are logically incompatible as described in `Description`.
4. Formulate a question that:
   * Makes both opposing claims explicit by referencing their exact content.
   * Asks which claim is authoritative, or whether a reconciliation rule exists that allows both to apply under defined conditions.
   * Asks for a resolution that can be directly applied to the specification — not a restatement of the conflict.

### Requirements

* The question text must include both Item A `Content` and Item B `Content`, quoted or closely referenced.
* The question must not reference only one item.
* The question must request a specific, applicable resolution.
* Do not generate a generic question. The question must derive from the exact content of both items.

### Context field population

For the canonical record, populate Context fields from **Item A**:

* `Context.Source` ← Item A `Source`
* `Context.Section` ← Item A `Section`
* `Context.Content` ← Item A `Content`

Item B is traceable via the `conflict_id` link to the originating conflict record.

---

## GAP

**Source fields to use:** `Absent from` list, `Present in` list, `Description`

### Procedure

1. Identify the missing section name from `Description` or from the `Absent from` entries.
2. Identify the artifact where the section is absent (from `Absent from`).
3. Identify the artifact where the section is present (from `Present in`).
4. Formulate a question that asks:
   * Whether the missing section is required for the source where it is absent.
   * If required, what content it should contain.

### Requirements

* The question must name the missing section explicitly.
* The question must reference both the absent source and the present source.
* The question must have two parts: is it required, and if so, what should it contain.
* Do not generate a generic question. The question must identify the specific section and sources involved.

---

# Question Record Assembly

After generating all questions, assemble canonical question records.

## Q-ID Assignment

Assign sequential question IDs in order of the originating conflict ID:

```text
Q001, Q002, Q003, ...
```

The conflict with the lowest conflict ID number receives Q001.

IDs reset on each execution run.

## Status Initialization

Set `Status: unanswered` on every question record.

Do not set any other status. Subsequent transitions (`answered`, `resolved`) are managed by downstream stages.

## Canonical Record Format

Use the following exact structure for each question record:

```markdown
## <question_id>

**Conflict ID:** <conflict_id>
**Conflict Type:** CONTRADICTION | AMBIGUITY | GAP
**Severity:** BLOCKING | ADVISORY
**Status:** unanswered

**Question:** [specific question text grounded in the conflict content]

**Context:**
- Source: `knowledge_base/extracted/<file>.md`
- Section: `# <Section>`
- Content: `<exact item text from conflict record>`
```

For AMBIGUITY records, append to Context:

```markdown
- Reason: `<reason field from conflict record>`
```

For CONTRADICTION records, populate Context from Item A. Ensure both Item A and Item B content appear in the `**Question:**` field.

---

# Canonical Artifact Generation

Generate the full canonical artifact using the following exact structure:

```markdown
# Questions Report

## Metadata
- Generated: <ISO 8601 date>
- Source: `knowledge_base/conflicts/conflicts_report.md`
- Total questions: N
- Blocking: N
- Advisory: N

---

## Summary

| ID   | Conflict ID | Conflict Type | Severity | Status     | Question                    |
| ---- | ----------- | ------------- | -------- | ---------- | --------------------------- |
| Q001 | C001        | AMBIGUITY     | BLOCKING | unanswered | [one-line question summary] |

---

## Questions

### Q001

[canonical question record]

---

### Q002

[canonical question record]

---
```

If zero open conflicts:

```markdown
# Questions Report

## Metadata
- Generated: <ISO 8601 date>
- Source: `knowledge_base/conflicts/conflicts_report.md`
- Total questions: 0
- Blocking: 0
- Advisory: 0

---

## Questions

No open conflicts found in the source conflicts report. No questions generated.
```

---

# Derived Artifact Generation

Generate the derived human-readable artifact using the following exact structure:

```markdown
# Questions for Review

## About This Document

The following questions were generated from open conflicts detected in the knowledge base.

Please answer all BLOCKING questions before Human Validation can proceed.
ADVISORY questions are informational — you may provide answers or leave them for automatic resolution.

---

## Question Q001

**Priority:** BLOCKING | ADVISORY

[question text]

**Context:**
- Section: `# <Section>`
- Item: `<exact item text>`

**Answer:** _(please fill in)_

---

## Question Q002

[...]
```

If zero open conflicts:

```markdown
# Questions for Review

No open conflicts found. No questions require review.
```

## Field exclusion rules

Do not include the following in the derived artifact:

* `conflict_id` (e.g., C001)
* `Conflict Type` field label
* `Status` field
* `Context.Source` filepath

The derived artifact is for human review only. Internal pipeline identifiers must not appear in it.

---

# Output Rules

## Canonical Artifact

Write to:

```text
knowledge_base/questions/questions_report.md
```

If the file already exists, overwrite it.

## Derived Artifact

Write to:

```text
output/generated_questions/questions_for_review.md
```

If the file already exists, overwrite it.

Do not write any artifacts to any other location.

---

# Traceability Rules

Every canonical question record must preserve the following fields from the originating conflict record:

* `conflict_id` — direct link to the source conflict
* `Conflict Type` — preserved for downstream processing
* `Severity` — preserved for downstream prioritisation
* `Context.Source` — source artifact filepath
* `Context.Section` — section name
* `Context.Content` — exact item text

For AMBIGUITY records, also preserve:

* `Context.Reason` — exact reason text from the conflict record

These fields must remain present and unmodified in the canonical artifact.

Traceability must remain available for:

* **Human Validation (Step 5)** — reads canonical question records to understand what requires human input and to determine whether BLOCKING questions have been answered before proceeding.
* **`/consolidate-knowledge` (Step 6)** — reads canonical question records to match validated human answers back to their originating conflicts via `conflict_id`.

---

# Failure Handling

Stop execution and report an explicit failure when:

* `knowledge_base/conflicts/conflicts_report.md` does not exist.
* The conflicts report cannot be read.
* Repository structure is invalid.
* A question record cannot be linked to an originating conflict.

Do not silently continue after a blocking failure.

---

# Completion Criteria

Execution is complete when:

* all conflict records with `Status: open` in `knowledge_base/conflicts/conflicts_report.md` have been processed;
* one question record has been generated for each open conflict;
* `knowledge_base/questions/questions_report.md` has been written;
* `output/generated_questions/questions_for_review.md` has been written;
* every canonical question record is traceable to an originating conflict.
