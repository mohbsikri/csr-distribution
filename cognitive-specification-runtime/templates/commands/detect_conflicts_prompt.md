# Detect Conflicts Prompt Template

You are executing the Cognitive Specification Runtime conflict detection stage.

Your objective is to analyze extracted knowledge artifacts and produce a structured, traceable conflict report.

You must follow repository rules and execution specifications.

---

# Context

The repository follows:

* Repository-first
* Markdown-first
* Claude Code-first
* Human-in-the-loop
* Traceability-first

The repository is the source of truth.

Never invent conflicts.

Every conflict must be supported by evidence present in the analyzed artifacts.

---

# Objective

The command operates in two stages.

## Global Stage

1. Discover all extracted knowledge artifacts.
2. Parse each artifact into sections and items.
3. Build the full item inventory for analysis.

## Detection and Reporting Stage

4. Detect AMBIGUITY across all items.
5. Detect CONTRADICTION across artifacts.
6. Detect GAP across artifacts.
7. Assemble conflict records.
8. Generate the conflict report.
9. Write the report to the repository.

---

# Artifact Discovery

Discover all files matching:

```text
*_knowledge.md
```

located in:

```text
knowledge_base/extracted/
```

Build the list of artifacts to analyze.

---

# Artifact Parsing

For each artifact:

* Read the `# Source` section to capture the source reference.
* Read each knowledge section: `# Facts`, `# Decisions`, `# Assumptions`, `# Constraints`, `# Terminology`, `# Business Rules`, `# Technical Rules`.
* Extract each bullet item as an individual knowledge item.
* Record which sections are present and which are absent.

---

# Detection Rules

## AMBIGUITY Detection

For every item in every artifact, determine whether it is sufficiently specific for downstream use.

Flag an item as AMBIGUOUS if it contains any of the following:

**Vague quantifiers:**

> "fast", "slow", "large", "small", "many", "few", "sufficient", "appropriate", "adequate", "reasonable", "significant", "quickly", "efficiently"

**Undefined references:**

> A term that appears in the item but is not defined in the `# Terminology` section of any analyzed artifact.

**Relative terms without reference:**

> "better", "improved", "more efficient", "higher quality", "enhanced"

**Underspecified conditions:**

> "when necessary", "if applicable", "as needed", "where relevant"

**Unqualified bounds `[E5, 2026-11-01]`:**

> A numeric or temporal bound stated without saying whether the endpoint is included: `de X à Y`, `entre X et Y`, `jusqu'à X`, `au moins X`, `au plus X`, `X maximum`, `J-7`, `before X`, `up to X`.
>
> **Flag it — never resolve it.** Do not write `inclus` into the item. Choosing a reading of an ambiguity is forbidden by the generation contract, and an endpoint read the wrong way becomes a defect in code.
>
> **Severity ADVISORY**, by exception to the default. An unqualified bound is almost always answered in one sentence by whoever wrote it; raising it BLOCKING would stall a project on a point a question settles. The purpose is to put the question in front of someone, not to stop the pipeline.
>
> Do not flag a bound whose inclusivity is already stated (`inclus`, `inclusive`, `compris`, `exclu`, `strictement`, `≤`, `≥`, `<`, `>`), nor a single value that is not a bound — `durée : 30 minutes` is a value, `jusqu'à 30 minutes` is a bound.

Do not flag items that use precise, measurable, or fully defined language.

**Severity:**

* Default: BLOCKING
* ADVISORY only when the ambiguous item is in the `# Terminology` section itself.

---

## CONTRADICTION Detection

Compare items within the same category across all artifacts.

Flag a pair of items as a CONTRADICTION when they make claims that cannot both be true.

Detection patterns:

* Item A asserts X is required; Item B asserts X is not required.
* Item A specifies a numeric value N; Item B specifies a different numeric value M for the same parameter.
* Item A requires capability X; Item B requires capability Y that is logically incompatible with X.
* Item A adopts approach P; Item B adopts an incompatible approach Q.

Do not infer contradictions from context not present in the item text.

If only one artifact is present, check for contradictions within the same artifact.

**Severity:** Always BLOCKING.

---

## GAP Detection

Compare the set of sections present across all artifacts.

Flag a GAP when a section is present in at least one artifact but absent from at least one other.

For a single artifact, flag a GAP if a section header is present but contains no items (structural gap).

**Severity:**

* Default: ADVISORY.
* BLOCKING when the absent section is `# Business Rules` or `# Constraints` and at least one other artifact has it populated.

---

# Conflict Record Assembly

Assign sequential IDs to all detected conflicts:

```text
C001, C002, C003, ...
```

Order: CONTRADICTION first, AMBIGUITY second, GAP third.

For each conflict, record:

* ID
* Type
* Severity
* Status: `open`
* Description (one sentence)
* Affected items with full traceability

### CONTRADICTION record format

```markdown
## C<NNN>

**Type:** CONTRADICTION
**Severity:** BLOCKING
**Status:** open

**Description:** [one sentence]

**Affected Items:**

Item A:
- Source: `knowledge_base/extracted/<file>.md`
- Section: `# <Section>`
- Content: `<exact item text>`

Item B:
- Source: `knowledge_base/extracted/<file>.md`
- Section: `# <Section>`
- Content: `<exact item text>`
```

### AMBIGUITY record format

```markdown
## C<NNN>

**Type:** AMBIGUITY
**Severity:** BLOCKING | ADVISORY
**Status:** open

**Description:** [one sentence]

**Affected Item:**
- Source: `knowledge_base/extracted/<file>.md`
- Section: `# <Section>`
- Content: `<exact item text>`
- Reason: `<specific reason for ambiguity>`
```

### GAP record format

```markdown
## C<NNN>

**Type:** GAP
**Severity:** BLOCKING | ADVISORY
**Status:** open

**Description:** [one sentence]

**Absent from:**
- `knowledge_base/extracted/<file>.md` — section `# <Section>` not present

**Present in:**
- `knowledge_base/extracted/<file>.md` — section `# <Section>` populated
```

---

# Report Generation

Generate the following structure:

```markdown
# Conflicts Report

## Metadata
- Generated: <ISO 8601 timestamp>
- Sources analyzed: [list]
- Total conflicts: N
- Blocking: N
- Advisory: N

---

## Summary

| ID | Type | Severity | Status | Description |
| -- | ---- | -------- | ------ | ----------- |
| C001 | ... | ... | open | ... |

---

## Conflicts

### C001
[record]
```

If no conflicts are detected:

```markdown
## Conflicts

No conflicts detected across the analyzed artifacts.
```

---

# Output Rules

Write the report to:

```text
knowledge_base/conflicts/conflicts_report.md
```

Overwrite if the file already exists.

---

# Traceability Rules

Every conflict record must preserve:

* the source artifact filename;
* the section name;
* the exact text of the affected item(s).

Traceability must remain available for downstream stages.

---

# Failure Handling

Stop execution if:

* no `*_knowledge.md` files exist in `knowledge_base/extracted/`;
* an artifact cannot be read;
* a conflict record cannot be traced to a source artifact;
* repository structure is invalid.

Report failures explicitly.

---

# Completion Criteria

Execution is complete when:

* all artifacts in `knowledge_base/extracted/` have been analyzed;
* all detected conflicts have been classified and recorded;
* the conflict report has been written to `knowledge_base/conflicts/conflicts_report.md`;
* every conflict record is traceable.
