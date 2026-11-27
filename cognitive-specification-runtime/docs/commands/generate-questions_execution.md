# Generate Questions Execution Specification

## Purpose

Define the runtime execution process for the `/generate-questions` command.

The objective is to consume open conflict records and produce a canonical structured question artifact and a human-readable derived artifact for stakeholder review.

---

## Execution Flow

```text
Load Conflict Report
↓
Parse Conflict Records
↓
Filter Open Conflicts
↓
Generate Questions
↓
Assemble Question Records
↓
Generate Canonical Artifact
↓
Generate Derived Artifact
↓
Persist Outputs
```

---

## Phase 1 — Report Loading

### Objective

Verify that the input artifact exists and is readable. Load its content for downstream processing.

### Inputs

```text
knowledge_base/conflicts/conflicts_report.md
```

### Actions

* Verify the file exists at the declared path.
* Verify the file is accessible and readable.
* Read the full file content.

### Failure Conditions

* `knowledge_base/conflicts/conflicts_report.md` does not exist.
* The file cannot be read.

### Output

```text
Conflict Report Content
```

---

## Phase 2 — Conflict Parsing

### Objective

Extract all conflict records from the report into a structured inventory for processing.

### Actions

* Parse the `## Metadata` section: extract Generated date, Sources analyzed, Total conflicts, Blocking count, Advisory count.
* Parse the `## Summary` table: extract all rows — ID, Type, Severity, Status, Description.
* Parse each individual conflict record under `## Conflicts`:

  For every `### C<NNN>` section, extract:

  | Field | Location in record |
  | ----- | ------------------ |
  | `conflict_id` | Section header (`### C001`) |
  | `Type` | `**Type:**` field |
  | `Severity` | `**Severity:**` field |
  | `Status` | `**Status:**` field |
  | `Description` | `**Description:**` field |
  | `Source` | `- Source:` line within Affected Item(s) |
  | `Section` | `- Section:` line within Affected Item(s) |
  | `Content` | `- Content:` line within Affected Item(s) |
  | `Reason` | `- Reason:` line — AMBIGUITY records only |

  For CONTRADICTION records, extract Item A and Item B separately. Capture Source, Section, and Content for each.

  For GAP records, extract `Absent from` and `Present in` lists.

* Build the Conflict Record Inventory.

### Failure Conditions

* A record cannot be parsed to extract required fields.
* A record is present in the Summary table but absent from the Conflicts section.

### Output

```text
Conflict Record Inventory
```

---

## Phase 3 — Open Conflict Filtering

### Objective

Select only conflicts that are eligible for question generation.

### Actions

* Filter the Conflict Record Inventory to records where `Status: open`.
* Discard records with any other status (`answered`, `resolved`).
* Count the remaining open conflicts.

### Empty Set Behavior

If zero records remain after filtering:

* Prepare an explicit empty report for both output artifacts.
* Skip Phases 4 and 5.
* Proceed directly to Phase 6 with zero question records.

### Output

```text
Open Conflict Set
```

---

## Phase 4 — Question Generation

### Objective

Generate one targeted, grounded question per open conflict.

Apply the type-specific rule to each conflict in the Open Conflict Set.

---

### AMBIGUITY

**Source fields:** `Content`, `Reason`

**Rule:** Identify the undefined or insufficiently specified term or condition from the `Content` and `Reason` fields. Formulate a question that asks for a precise definition or for the criteria that would make the term unambiguous and usable in a downstream specification.

**Requirements:**

* The question must name the specific term or condition requiring clarification.
* The question must indicate what form of answer would resolve the ambiguity (a definition, a set of criteria, a measurable threshold).
* The question must not be generic. It must derive from the exact `Content` and `Reason` values of the conflict record.

**Example pattern:**

> The item `[Content]` uses the term `[undefined term from Reason]`. What is the precise definition of this term? What criteria determine whether this condition is satisfied for the purposes of downstream specification?

---

### CONTRADICTION

**Source fields:** Item A `Content`, Item B `Content`, `Description`

**Rule:** Identify the two opposing claims from Item A and Item B. Formulate a question that makes the conflict explicit and asks which claim is authoritative, or whether a reconciliation rule exists that allows both to apply under defined conditions.

**Requirements:**

* The question must quote or closely reference both opposing items.
* The question must ask for a resolution that can be directly applied — not a restatement of the conflict.
* The question must not be generic. It must derive from the exact content of both affected items.

**Example pattern:**

> Item A states: `[Content A]`. Item B states: `[Content B]`. Which claim is authoritative? If both apply, under what conditions does each take precedence?

---

### GAP

**Source fields:** `Absent from`, `Present in`, `Description`

**Rule:** Identify which artifact lacks the section and which has it populated. Formulate a question that asks whether the missing section is required for the absent source, and if so, what it should contain.

**Requirements:**

* The question must identify the missing section by name.
* The question must reference the source where the section is absent and the source where it is present.
* The question must ask both whether the section is required and what its content should be if required.

**Example pattern:**

> The section `[Section]` is present in `[present artifact]` but absent from `[absent artifact]`. Is this section required for `[absent artifact]`? If yes, what should it contain?

---

### Output

```text
Question Draft Set
```

---

## Phase 5 — Question Record Assembly

### Objective

Build fully populated canonical question records with complete traceability.

### Q-ID Assignment

Assign sequential question IDs in order of the originating conflict ID:

```text
Q001, Q002, Q003, ...
```

The first open conflict (lowest conflict ID) receives Q001. IDs reset on each run.

### Status Initialization

Set `Status: unanswered` on every question record.

This is the only status transition managed by `/generate-questions`. Subsequent transitions (`answered`, `resolved`) are managed by downstream stages.

### Traceability Population

For each question record, populate all traceability fields from the originating conflict record:

| Question record field | Source |
| --------------------- | ------ |
| `Conflict ID` | `conflict_id` from conflict record |
| `Conflict Type` | `Type` from conflict record |
| `Severity` | `Severity` from conflict record |
| `Context.Source` | `Source` from conflict Affected Item |
| `Context.Section` | `Section` from conflict Affected Item |
| `Context.Content` | `Content` from conflict Affected Item |
| `Context.Reason` | `Reason` from conflict Affected Item — AMBIGUITY only |

For CONTRADICTION records, `Context.Source`, `Context.Section`, and `Context.Content` are populated from Item A. Item B content is incorporated into the question text.

### Output

```text
Canonical Question Record Set
```

---

## Phase 6 — Canonical Artifact Generation

### Objective

Assemble the complete canonical questions report document.

### Report Structure

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

### Q002
[canonical question record]
```

If zero open conflicts:

```markdown
## Questions

No open conflicts found in the source conflicts report. No questions generated.
```

### Output

```text
Canonical Artifact Document
```

---

## Phase 7 — Derived Artifact Generation

### Objective

Render the human-readable review document from the Canonical Question Record Set.

### Source

Canonical Question Record Set from Phase 5.

### Field Mapping

| Derived field | Source |
| ------------- | ------ |
| `## Question <question_id>` | `question_id` |
| `**Priority:**` | `Severity` (BLOCKING → BLOCKING, ADVISORY → ADVISORY) |
| Question text | `Question` field |
| `- Section:` | `Context.Section` |
| `- Item:` | `Context.Content` |

Fields **not** included in the derived artifact: `Conflict ID`, `Conflict Type`, `Status`, `Context.Source` (filepath).

### Derived Report Structure

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
...
```

If zero open conflicts:

```markdown
# Questions for Review

No open conflicts found. No questions require review.
```

### Output

```text
Derived Artifact Document
```

---

## Phase 8 — Persistence

### Objective

Write both artifacts to the repository.

### Canonical Artifact

Write to:

```text
knowledge_base/questions/questions_report.md
```

If the file already exists, overwrite it.

### Derived Artifact

Write to:

```text
output/generated_questions/questions_for_review.md
```

If the file already exists, overwrite it.

### Verification

After writing, confirm:

* `knowledge_base/questions/questions_report.md` exists and is readable.
* `output/generated_questions/questions_for_review.md` exists and is readable.
* Both files contain the expected number of question records.

### Output

```text
Persisted Artifacts
```

---

## Traceability Rules

Every canonical question record must carry the following fields populated from the originating conflict record:

* `conflict_id` — links the question to its source conflict
* `Conflict Type` and `Severity` — preserved for downstream prioritisation
* `Context.Source` — source artifact filepath
* `Context.Section` — section name within the source artifact
* `Context.Content` — exact item text from the conflict record
* `Context.Reason` — AMBIGUITY records only

These fields must remain present and unmodified in the canonical artifact.

Traceability must be preserved for downstream stages:

* Human Validation (Step 5) reads the canonical artifact to understand what requires human input before proceeding.
* `/consolidate-knowledge` (Step 6) reads the canonical artifact to match validated answers back to their originating conflicts.

---

## Completion Criteria

Execution is complete when:

* all conflict records with `Status: open` in `knowledge_base/conflicts/conflicts_report.md` have been processed;
* one question record has been generated for each open conflict;
* `knowledge_base/questions/questions_report.md` has been written;
* `output/generated_questions/questions_for_review.md` has been written;
* every canonical question record carries all required traceability fields.
