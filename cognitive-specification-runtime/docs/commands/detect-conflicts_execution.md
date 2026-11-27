# Detect Conflicts Execution Specification

## Purpose

Define the runtime execution process for the `/detect-conflicts` command.

The objective is to scan extracted knowledge artifacts and produce a structured, traceable conflict report.

---

## Execution Flow

```text
Discover Artifacts
→ Two-Pass Source Selection (N > 5 only)
→ Parse Artifacts
→ Detect Ambiguity
→ Detect Contradiction
→ Detect Gap
→ Assemble Conflict Records
→ Generate Report
→ Persist
```

---

## Phase 0.5 — Two-Pass Source Selection

### Objective

Determine which full knowledge artifacts to load for conflict analysis.

### Condition

This phase runs when N > 5 knowledge sources are available. When N ≤ 5, skip this phase and load all full artifacts (single-pass mode).

### Actions (Two-Pass Mode)

**Pass 1 — Index Scan:**
1. Locate all knowledge index files: `knowledge_base/extracted/<base>_knowledge_index.md`
2. Load all index files (compact — one table per source, bounded context).
3. Build ID Map: for each source, collect its set of BR/TR/C identifiers and their topics.
4. Compare ID Maps across all source pairs:
   - Sources sharing identical ID numbers (e.g., both have BR-003) are candidate conflict pairs.
   - Sources with topics that are semantically related (same domain term in topic column) are candidate conflict pairs.
5. Build Candidate Set: the union of all sources that appear in at least one candidate pair.
6. Any source not in any candidate pair is excluded from Pass 2.

**Pass 2 — Targeted Load:**
1. Load full knowledge artifacts ONLY for sources in the Candidate Set.
2. Proceed to existing conflict detection logic on the loaded artifacts.

### Output

```text
Candidate Set — list of source names whose full artifacts will be loaded.
```

---

## Phase 1 — Artifact Discovery

### Objective

Identify all extracted knowledge artifacts available for analysis.

### Inputs

```text
knowledge_base/extracted/
```

### Actions

* Discover all files matching `*_knowledge.md` in `knowledge_base/extracted/`.
* Verify each file is accessible and readable.
* Build artifact inventory.

### Failure Conditions

* No `*_knowledge.md` files exist in `knowledge_base/extracted/`.
* An artifact file cannot be read.

### Output

```text
Artifact Inventory
```

---

## Phase 2 — Artifact Parsing

### Objective

Extract structured content from each artifact for analysis.

### Actions

For each artifact in the inventory:

* Read the full content.
* Identify sections by header (`# Facts`, `# Decisions`, `# Assumptions`, `# Constraints`, `# Terminology`, `# Business Rules`, `# Technical Rules`).
* Extract individual items from each section as a list.
* Record which sections are present and which are absent.
* Record the source reference from the `# Source` section.

### Output

```text
Parsed Artifact Set
```

---

## Phase 3 — Ambiguity Detection

### Objective

Identify items that are insufficiently specific for downstream use.

### Scope

Applied per artifact, per item across all sections.

### Detection Signals

An item is ambiguous when it contains:

* **Vague quantifiers** — "fast", "slow", "large", "small", "many", "few", "sufficient", "appropriate", "adequate", "reasonable", "significant"
* **Undefined references** — a term used in an item that is not defined in the `# Terminology` section of any analyzed artifact
* **Relative terms without reference** — "better", "improved", "more efficient", "higher quality"
* **Underspecified conditions** — "when necessary", "if applicable", "as needed"
* **Unqualified bounds `[E5, 2026-11-01]`** — a numeric or temporal bound stated without saying whether it is included: `de X à Y`, `entre X et Y`, `jusqu'à X`, `au moins X`, `au plus X`, `X maximum`, `J-7`, `before X`, `up to X`. A reader cannot tell whether the endpoint satisfies the rule, and two implementers will not choose the same answer.

### Rules

Do not flag items that use precise, measurable language.

**On unqualified bounds — detect, never resolve.** Flag the bound; do not write `inclus` into the item. Choosing a reading of an ambiguity is forbidden by the generation contract (`templates/prompts/generate_specification_prompt.md`: *"Interpret ambiguous content and choose a reading to include"*), and an endpoint read the wrong way is a defect that survives into code.

**Severity ADVISORY, by exception to the default below.** An unqualified bound is almost always resolvable in one sentence by the person who wrote it, and raising it BLOCKING would stall a project on a point that a question answers. The purpose is to put the question in front of someone, not to stop the pipeline.

Do not flag a bound whose inclusivity is already stated — `inclus`, `inclusive`, `compris`, `exclu`, `strictement`, `≤`, `≥`, `<`, `>` — nor a single value that is not a bound (`durée : 30 minutes` is a value, `jusqu'à 30 minutes` is a bound).

Do not flag items that use terms defined in any artifact's `# Terminology` section.

Assign severity BLOCKING by default. Downgrade to ADVISORY only when the ambiguous item is in the `# Terminology` section itself (a terminology definition that is slightly imprecise is less critical than an ambiguous constraint).

### Output

```text
Ambiguity Candidate List
```

---

## Phase 4 — Contradiction Detection

### Objective

Identify pairs of items across artifacts that make logically incompatible claims.

### Scope

Applied cross-artifact, within the same knowledge category. Intra-document contradiction (a single source contradicting itself) is **not** this phase's concern — see the correction below.

### Detection Patterns

| Pattern | Example |
| ------- | ------- |
| Direct opposition | A: "X is required" — B: "X is not required" |
| Incompatible numeric claims | A: "timeout is 30 seconds" — B: "timeout is 60 seconds" |
| Incompatible requirements | A: "system must be offline-capable" — B: "all operations require server confirmation" |
| Conflicting decisions | A: "adopt approach X" — B: "adopt approach Y" (where X and Y are mutually exclusive) |

### Rules

Only flag contradictions supported by evidence in the item text.

Do not infer contradictions from context not present in the items themselves.

A single-artifact run has no cross-artifact contradictions to find, and this phase does not look for intra-artifact ones either.

**Corrected 2026-11-01.** This paragraph previously read: "Intra-artifact contradictions (within the same source) are still detectable and must be flagged" — with no detection pattern, no exclusion rule, nothing this phase's own Scope and worked examples (all cross-artifact, all of the form "A: ... — B: ...") could execute. It directly contradicted the Scope line one paragraph above, and the L1 contract's own Execution Rules, which already say CONTRADICTION is detected "across artifacts." It was never implemented and could not have been.

The real need it gestured at is covered: `/extract-knowledge` Phase 5.5 (Bloc 5) checks every extracted BR-NNN/TR-NNN/C-NNN pair for intra-document contradiction, with an actual algorithm (a contradiction test plus three exclusions — conditional branches, different actors, sequential steps) and a mandatory report, `<source>_intra_contradictions.md`, written before this command ever runs. By the time Phase 4 executes, that check is already done.

All contradictions are severity BLOCKING.

### Output

```text
Contradiction Candidate List
```

---

## Phase 5 — Gap Detection

### Objective

Identify knowledge categories present in some artifacts but absent from others.

### Scope

Applied cross-artifact, comparing category presence.

### Detection Rule

For each knowledge category (`# Facts`, `# Decisions`, `# Assumptions`, `# Constraints`, `# Terminology`, `# Business Rules`, `# Technical Rules`):

* If the category is present in at least one artifact but absent from at least one other: flag as GAP.
* The absent artifact(s) are listed as "Absent from".
* The present artifact(s) are listed as "Present in".

### Single-Artifact Behavior

With a single artifact, cross-artifact gap detection is not applicable.

Check for empty sections: if a section header is present but contains no items, flag as structural GAP (ADVISORY).

### Severity

* Default: ADVISORY — absence of a category may be intentional.
* Upgrade to BLOCKING when the absent category is `# Business Rules` or `# Constraints` and at least one other artifact has it populated.

### Output

```text
Gap Candidate List
```

---

## Phase 6 — Conflict Record Assembly

### Objective

Convert all detected candidates into numbered conflict records.

### Actions

* Assign sequential IDs (C001, C002, ...) in this order: CONTRADICTION first, AMBIGUITY second, GAP third.
* For each conflict, populate: ID, type, severity, status (`open`), description, affected items with full traceability.
* If zero conflicts were detected, prepare an explicit empty report.

### Output

```text
Conflict Record Set
```

---

## Phase 7 — Report Generation

### Objective

Assemble the final structured conflict report.

### Report Structure

```markdown
# Conflicts Report

## Metadata
- Generated: <ISO 8601 timestamp>
- Sources analyzed: [list of artifact filenames]
- Total conflicts: N
- Blocking: N
- Advisory: N

---

## Summary

| ID   | Type          | Severity | Status | Description          |
| ---- | ------------- | -------- | ------ | -------------------- |
| C001 | CONTRADICTION | BLOCKING | open   | [one line]           |
| ...  |               |          |        |                      |

---

## Conflicts

### C001
[conflict record]

### C002
[conflict record]
```

If no conflicts were detected:

```markdown
## Conflicts

No conflicts detected across the analyzed artifacts.
```

### Output

```text
Conflict Report Document
```

---

## Phase 8 — Persistence

### Objective

Write the conflict report to the repository.

### Output Location

```text
knowledge_base/conflicts/conflicts_report.md
```

If the file already exists, overwrite it.

### Output

```text
Persisted Conflict Report
```

---

## Traceability Rules

Every conflict record must reference the source artifact filename, section name, and exact item content.

Traceability must be preserved for downstream stages.

---

## Completion Criteria

Execution is complete when:

* all artifacts in `knowledge_base/extracted/` have been analyzed through all detection phases;
* all conflict records have been assembled;
* `knowledge_base/conflicts/conflicts_report.md` has been written;
* every record is traceable to a source artifact and section.
