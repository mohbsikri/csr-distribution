# Extract Knowledge Prompt Template

You are executing the Cognitive Specification Runtime extraction stage.

Your objective is to transform source material into structured and traceable knowledge artifacts.

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

Never invent information.

Never generate knowledge without supporting evidence.

---

# Objective

The command operates in two stages.

## Global Stage

1. Discover available sources.
2. Read the source registry.
3. Identify previously processed sources.
4. Request user guidance when required.

## Per Source Stage

For each source selected for processing:

1. Analyze source content.
2. Extract explicit knowledge.
3. Structure extracted knowledge.
4. Validate extracted knowledge.
5. Generate a knowledge artifact.
6. Update the source registry.

---

# V2 Context Detection

Before discovering sources, check for V2 workspace context.

1. Check if `runtime/lineage.md` exists in WORKSPACE_ROOT.
2. **If found:** you are in a **V2 workspace**. Record `extraction_mode = V2`.
   - Read `source_workspace_id` from lineage.md (the parent v1 workspace).
   - Locate `specifications/stable/*_traceability.md`. Read all BR-NNN, TR-NNN, and C-NNN IDs.
   - Record `max_br`, `max_tr`, `max_c` (highest numeric suffix per type, 0 if none).
   - New v2 IDs will start at max_br + 1, max_tr + 1, max_c + 1.
   - If no traceability matrix found: halt with `V2 ID BASE ERROR`.
3. **If not found:** `extraction_mode = V1`. Continue normally.

---

# Source Discovery

Discover ingested raw records located in:

```text
knowledge_base/raw/
```

For each raw record:

* read `origin_path`;
* identify the original source file;
* load the original source content using `origin_path`.

Read the source registry:

```text
runtime/sources.md
```

---

# Preprocessed Artifact Lookup

Before loading the original source content, check if a preprocessed artifact exists for the source.

For each source discovered in knowledge_base/raw/:

1. Determine the source_name (filename without extension from origin_path).
2. Check if the following path exists:
   ```text
   knowledge_base/preprocessed/<source_name>_preprocessed.md
   ```
3. If a preprocessed artifact exists: use it as the source content for extraction instead of the original file.
4. If no preprocessed artifact exists: use the original file content via origin_path as before.

This lookup is transparent to all downstream extraction logic. The Enriched Markdown blocks ([VISUAL:], [SCHEMA:], [FLOW:], [COMPONENT:], [SPEAKER:]) are treated as first-class text content during extraction.

---

# Source Registry Rules

For each discovered source:

* If the source is not present in the registry, process it normally.
* If the source already exists in the registry, request user guidance before continuing.

The command must never silently reprocess a registered source.

---

# User Decision Rules

When a source already exists in the registry, present the following prompt and wait for an explicit decision before continuing:

---

## Source Already Registered — Decision Required

**Source:** `<source_name>.<ext>`
**Registered status:** <current_status>
**Existing knowledge artifact:** `knowledge_base/extracted/<artifact>`
**Source fingerprint:** <stored_fingerprint or "not computed">
**Staleness check:** <CHANGED — source content differs from last processing | UNCHANGED — content matches | UNKNOWN — no fingerprint stored>

> **Warning: source content has changed since last processing. OVERWRITE or NEW VERSION recommended.**
> *(This warning is shown only when staleness check = CHANGED)*

**Choose one action:**

- **SKIP** — do not reprocess; keep the current knowledge artifact
- **OVERWRITE** — reprocess and replace the existing knowledge artifact in-place
- **NEW VERSION** — reprocess and create a new versioned artifact alongside the existing one

**Your choice? (SKIP / OVERWRITE / NEW VERSION)**

---

### SKIP

Do not process the source.

Update the source registry:

* set status to `skipped`;
* keep the current Knowledge Artifact reference.

Continue with the next available source.

### OVERWRITE

Reprocess the source.

Replace the existing knowledge artifact.

### NEW VERSION

Reprocess the source.

Create a new versioned knowledge artifact.

---

# Versioning Rules

For NEW VERSION:

Scan:

```text
knowledge_base/extracted/
```

for files matching:

```text
<source_name>_knowledge_v*.md
```

The next version number is the highest version number found plus one.

If no versioned artifact exists:

```text
<source_name>_knowledge.md
```

is considered version 1.

The first generated version must therefore be:

```text
<source_name>_knowledge_v2.md
```

Examples:

```text
requirements_knowledge.md
requirements_knowledge_v2.md
requirements_knowledge_v3.md
requirements_knowledge_v4.md
```

---

# Extraction Targets

Extract only supported information.

Identify:

* Facts
* Workflows
* Decisions
* Assumptions
* Constraints
* Terminology
* Business Rules
* Technical Rules

Do not infer undocumented decisions.

Do not generate speculative knowledge.

Do not generate unsupported statements.

---

## Identifier Assignment

Every extracted Business Rule, Technical Rule, and Constraint must carry a mandatory sequential identifier.

### V1 mode (extraction_mode = V1)

| Category | Format | Example |
|----------|--------|---------|
| Business Rules | **BR-NNN:** | `**BR-001:** Users must authenticate via Matricule scan before...` |
| Technical Rules | **TR-NNN:** | `**TR-001:** The validation sequence checks X, then Y, then...` |
| Constraints | **C-NNN:** | `**C-001:** Maximum lot age before expiry is 30 days.` |

Numbering starts at `001` and is strictly sequential. Assign identifiers in the order items are encountered in the source.

### V2 mode (extraction_mode = V2)

In V2 mode, each rule carries one of three annotation tags. Determine the annotation type **before** assigning an identifier.

**Annotation type determination:**

| Signal in v2 source | Annotation | ID assignment |
|---------------------|------------|--------------|
| No reference to any v1 rule | `[v2-added]` | New v2 ID (max+1) |
| Source explicitly modifies a v1 rule (e.g., "remplace BR-005", "updated: BR-005", "supersedes BR-005") | `[v2-modified]` | Retain v1 ID (e.g., BR-005) |
| Source explicitly retires a v1 rule without replacement (e.g., "supprime BR-013", "deprecated: BR-013", "BR-013 no longer applies") | `[DEPRECATED in v2]` | Retain v1 ID (e.g., BR-013) |

**Default when no explicit signal is found:** `[v2-added]` with new v2 ID.

For `[v2-modified]` and `[DEPRECATED in v2]`: verify the referenced v1 ID exists in the inherited traceability matrix. If not found:
- `[v2-modified]` → log `V2-MOD-WARN: ID not found — treated as v2-added`; assign new v2 ID
- `[DEPRECATED in v2]` → log `V2-DEP-WARN: ID not found — deprecation skipped`

**New v2 IDs (for `[v2-added]` only) start from v1 ceiling:**

| Category | Start | Example (if v1 had BR-015) |
|----------|-------|---------------------------|
| Business Rules | `max_br + 1` | BR-016, BR-017, … |
| Technical Rules | `max_tr + 1` | TR-017, TR-018, … |
| Constraints | `max_c + 1` | C-009, C-010, … |

Do not start from 001. Renumbering from 001 would collide with inherited v1 IDs.

**Format examples (all three annotation types):**

```markdown
**BR-005** `[v2-modified]` — <updated rule text replacing v1 BR-005>
**BR-013** `[DEPRECATED in v2]` — <reason for retirement, or "Rule retired in v2">
**BR-016** `[v2-added]` — <new rule>
**TR-017** `[v2-added]` — <new rule>
**C-009** `[v2-added]` — <new constraint>
```

No Business Rule, Technical Rule, or Constraint may appear in the knowledge artifact without an identifier and, in V2 mode, without an annotation tag. Facts, Decisions, Assumptions, Terminology, and Workflows do not receive identifiers or annotation tags.

---

# Provenance Classification (KPM)

After all BR-NNN, TR-NNN, and C-NNN identifiers have been assigned and the intra-document contradiction check (Phase 5.5) has completed, classify every extracted item using the Q1–Q6 algorithm below. You still have the full source document in context — use it.

## Q1–Q6 Algorithm

Apply in order. Stop at the first affirmative answer.

```
Q1. Is the element directly observable in the source document
    (verbatim text or direct reformulation without addition)?
    → YES → SF (SOURCE_FACT)

Q2. Was the element explicitly confirmed during a traceable
    validation session already recorded (VQ-NNN / VAL-NNN)?
    → YES → UV (USER_VALIDATED)

Q3. Does the element follow by logical necessity from SF/UV
    premises only — no alternative conclusion is possible —
    and are ALL premises SF or UV (none classified ID)?
    → YES → DK (DERIVED_KNOWLEDGE)

Q4. Is the need established by SF/UV, does exactly one
    industry-documented standard apply, and would any other
    value be a deliberate deviation from that standard?
    → YES → TS (TECH_STANDARD)

Q5. Did you (CSR) select this element from identifiable
    alternatives where other valid choices exist and none
    is mandated by source, validation, standard, or logical
    necessity?
    → YES → ID (INFERRED_DESIGN)

Q6. (Default — gap you cannot resolve)
    → US (UNDEFINED_IN_SOURCE)
```

**Cascade rule R4:** If any premise of a DK derivation is classified ID, the derived element inherits ID, not DK.

## Structural Impact (ID elements only)

For every ID element, determine `impact_level` using criteria S1–S4:

| Code | Condition → `structural` |
|---|---|
| S1 | Introduces a new entity (table, list, object) absent from all sources and validations |
| S2 | Defines new lifecycle or workflow states visible to end users |
| S3 | Modifies the solution boundary (new integrations, new external interfaces) |
| S4 | Affects permission assignments or access control |

If none of S1–S4 applies: `impact_level: implementation`.

## Governance Status

| Type | `governance_status` |
|---|---|
| SF, UV, DK | `—` (not tracked) |
| TS | `ACKNOWLEDGED` |
| ID structural | `PENDING_VALIDATION` |
| ID implementation | `REGISTERED` |
| US | `BLOCKED` |

## Provenance Record Fields

| Field | Rules |
|---|---|
| `ID` | The BR-NNN / TR-NNN / C-NNN identifier |
| `Type` | One of: `SF`, `UV`, `DK`, `TS`, `ID`, `US` |
| `Refs` | For SF: `<source_base_name>#<section-heading>` (e.g., `demo-retail-transcript#requirements`). For TS: the standard ID (e.g., `ISO-3166-1`). Otherwise: `—` |
| `Rationale` | **Required and non-empty for ID and TS.** One sentence. For others: `—` |
| `Impact` | For ID: `structural` or `implementation`. For others: `—` |
| `Statut` | For ID/US/TS: the governance status. For SF/UV/DK: `—` |

## Ambiguity rules

- **R1 Partial:** Element partly in source, partly added → most conservative classification wins.
- **R2 Enrichment:** Precision added to an SF element → base is SF; added precision is TS or ID per Q4/Q5.
- **R3 Platform:** Vendor-documented conventions (Microsoft Power Platform, Dataverse, SharePoint) → TS. Undocumented patterns → ID.

## Classification discipline

- Do not default to SF without verifying Q1. If the element is a synthesis, summary, or conclusion — even a reasonable one — it is not SF.
- Do not classify as DK if an alternative conclusion would be possible given a different design.
- Do not classify as TS if multiple standards could apply or if the *need itself* is inferred (not established by SF/UV).
- Every ID must have an explicit `rationale`. "Seems reasonable" is not a rationale. Name the alternatives that were not chosen.
- Every US must represent a gap — something the source genuinely does not resolve and where the alternatives domain is too wide to select without client input.

---

## Format and Type Variants

When a source mentions multiple variants of a format, type, or category (e.g., two lot number formats, two user types, two validation modes):

* Extract ALL variants explicitly.
* If a variant exists but its specification is not defined in the source, capture it with an explicit note:
  `[UNDEFINED IN SOURCE — requires stakeholder input]`
* Never capture only the first or most prominent variant and omit the others.

---

## Multi-Step Logic

When a source describes a multi-step process as a Technical Rule (e.g., "if X then check Y, then do Z"):

* Capture the complete sequence of steps.
* Include: pre-condition check, existence check (if any), state check (if any), each branch outcome, final action.
* Do not collapse multi-step logic into a single-step summary.
* Preserve the order and conditionality of each step.

---

## Terminology Completeness

Capture ALL domain-specific terms found in the source, including:

* Entity names (tables, objects, documents)
* State names (lifecycle states, statuses)
* Role names (user profiles, actor types)
* Metric names (KPIs, measured quantities)
* Location names (physical or logical locations specific to the domain)
* Process names (named operations or procedures)
* Any term a reader outside the domain would not immediately understand

Do not limit terminology to the most prominent terms — completeness is required.

If a term appears in the source without a definition, capture it with: `[Definition not provided in source]`

---

## Extraction Scope — Spec Level vs Implementation Detail

CSR captures specification-level information:

* What the system does
* The rules it enforces
* The constraints it operates under
* The decisions made about it

Implementation details are out of scope UNLESS they encode a business rule, a constraint, or a technical rule.

**Decision rule:** If removing the detail would prevent someone from implementing the system correctly → include it as a Technical Rule. Otherwise → exclude it.

When excluding: add a note `[Implementation detail — out of scope]` in the extraction artifact to make the exclusion explicit and traceable.

Examples:
* Email body template text → out of scope (unless it encodes a required content rule)
* Regex pattern for input validation → in scope (Technical Rule)
* Step-by-step UI click sequence → out of scope
* Multi-step validation logic → in scope (Technical Rule)

---

# Phase 5.5 — Intra-Document Contradiction Check (Bloc 5)

This phase runs after all BR/TR/C have been extracted (with identifiers assigned) and before the knowledge artifact is structured. You have the full document and complete rule set in context — use this window to check for internal contradictions.

## When to flag INTRA_CONTRADICTION

Flag a pair (Rule A, Rule B) as INTRA_CONTRADICTION only when ALL of the following hold:

1. **Same situation**: same actor AND same action AND same state or condition context
2. **Incompatible outcomes**: Rule A asserts X; Rule B asserts NOT-X, or an outcome incompatible with X
3. **No scope separation**: neither rule limits itself to conditions that would prevent overlap

## When NOT to flag (exclusion conditions)

Do NOT flag as INTRA_CONTRADICTION when ANY of the following applies:

| Condition | Reasoning |
|-----------|-----------|
| Different actor types | Rules apply to different users/roles — both can coexist |
| Different lifecycle states | Rules apply at different moments in the workflow — sequential, not conflicting |
| Different input types or variants | Rules apply to different subtypes of the same entity (e.g., Classique vs Spécifique lot) |
| General + specific case | One rule is the general case; the other is a recognized exception — the specific wins |
| Different triggers or time fields | Rules share a domain but fire on different conditions |
| Different recipients | Rules address different system actors even with similar triggers |

**Decision rule:** If you can articulate a scenario where BOTH rules apply simultaneously to the SAME situation and produce incompatible outcomes — flag it. If you cannot construct such a scenario, do not flag.

## Severity

All INTRA_CONTRADICTIONs are BLOCKING. A spec generated from contradictory knowledge will produce contradictory requirements.

## Output

Write `knowledge_base/conflicts/<source_name>_intra_contradictions.md`:
- If contradictions found: one IC-NNN entry per pair, with full quote of both rules and the contradiction reasoning
- If none found: clean confirmation (no contradictions detected)

Extraction proceeds to Phase 6 regardless of findings.

---

# Knowledge Structure

## V1 structure

```markdown
# Source

# Facts

# Workflows

# Decisions

# Assumptions

# Constraints

**C-001:** <constraint description>

**C-002:** <constraint description>

# Terminology

# Business Rules

**BR-001:** <rule description>

**BR-002:** <rule description>

# Technical Rules

**TR-001:** <rule description>

**TR-002:** <rule description>

## Provenance Index

| ID | Type | Refs | Rationale | Impact | Statut |
|---|---|---|---|---|---|
| BR-001 | SF | <source_name>#<section-heading> | — | — | — |
| BR-002 | ID | — | <one sentence — name alternatives not chosen> | structural | PENDING_VALIDATION |
| TR-001 | TS | <standard_id> | <one sentence> | — | ACKNOWLEDGED |
| TR-002 | DK | <source_name>#<section-heading> | — | — | — |
| C-001 | US | — | — | — | BLOCKED |
```

The `## Provenance Index` is always the **last section** of the full knowledge artifact. Every BR-NNN, TR-NNN, and C-NNN item in the artifact has exactly one row. Rows are ordered: all BR ascending, then TR ascending, then C ascending. Empty cells use `—`.

## V2 structure (when extraction_mode = V2)

```markdown
**workspace_version:** v2
**source_workspace:** <source_workspace_id>
**v2_id_base:** BR-<max_br+1> / TR-<max_tr+1> / C-<max_c+1>

---

# Source

# Facts

# Workflows

# Decisions

# Assumptions

# Constraints

**C-009** `[v2-added]` — <new constraint>

# Terminology

# Business Rules

**BR-005** `[v2-modified]` — <updated rule text replacing v1 BR-005>
**BR-013** `[DEPRECATED in v2]` — <reason for retirement, or "Rule retired in v2">
**BR-016** `[v2-added]` — <new rule>

# Technical Rules

**TR-017** `[v2-added]` — <new rule>

## Provenance Index

| ID | Type | Refs | Rationale | Impact | Statut |
|---|---|---|---|---|---|
| BR-005 | SF | <source_name>#<section-heading> | — | — | — |
| BR-013 | SF | <source_name>#<section-heading> | — | — | — |
| BR-016 | ID | — | <one sentence — name alternatives not chosen> | implementation | REGISTERED |
| TR-017 | TS | <standard_id> | <one sentence> | — | ACKNOWLEDGED |
| C-009 | SF | <source_name>#<section-heading> | — | — | — |
```

An annotation tag is mandatory on every BR/TR/C item in V2 mode. The `## Provenance Index` covers all items present in the V2 artifact — inherited (v2-modified, v2-deprecated) and new (v2-added). Modified and deprecated rules appear inline in the same section as their type, ordered by ascending ID alongside `[v2-added]` rules. These tags are the downstream signals consumed by `/generate-specification` (Phase 4.2a / Phase 6b.1), the traceability matrix (`version_introduced`, `version_updated`, `Status` columns), and `/generate-test-cases` (Suite 1 régression vs Suite 2 nouvelles fonctionnalités).

Only create sections containing information. Empty sections are omitted in both modes.

---

# Workflow Extraction Rules

A Workflow is a named, sequential process involving actors and state transitions.

For each workflow identified in the source, capture:

* Workflow name
* Each step in sequence: actor, action, trigger condition, state transition (from → to)
* Decision points (conditions that branch the flow)
* Terminal states

Do not summarize workflows. Capture each step explicitly.

---

# Traceability Rules

Every extracted item must preserve a source reference.

Every knowledge item must remain traceable to its originating source.

Traceability must remain available for downstream runtime stages.

---

# Validation Rules

Before generating output, verify that:

* every item is supported by source material;
* no unsupported assumptions were introduced;
* duplicate knowledge is avoided;
* extracted information is understandable;
* extracted information is unambiguous;
* technical identifiers (table names, column names, field names, formula strings, regex patterns, API endpoints, account names) are captured with exact spelling and casing as they appear in the source — no abbreviation, normalization, or inference is permitted.

Reject unsupported statements.

---

# Output Rules

Generate two artifacts per processed source:

1. **Full knowledge artifact** — complete structured knowledge.
2. **Knowledge index artifact** — compact BR/TR/C summary table.

### Standard Naming

```text
<source_name>_knowledge.md
<source_name>_knowledge_index.md
```

### Versioned Naming

```text
<source_name>_knowledge_v<n>.md
<source_name>_knowledge_index_v<n>.md
```

Store all generated artifacts inside:

```text
knowledge_base/extracted/
```

---

# Knowledge Index Generation

After writing the full knowledge artifact, generate the companion knowledge index.

## Index Purpose

The knowledge index is a compact single-table summary of all BR-NNN, TR-NNN, and C-NNN items. It enables downstream stages (Detect Conflicts, Consolidate Knowledge) to scan identifiers across multiple sources without loading full artifacts.

## Index Format — V1

```markdown
# Knowledge Index — <source_name>

**Source:** <source_name>
**Full Artifact:** knowledge_base/extracted/<source_name>_knowledge[_v<n>].md
**Generated:** <date>

| ID | Type | Topic | Excerpt |
|----|------|-------|---------|
| BR-001 | Business Rule | <1–5 word topic> | <first 80 chars of rule description> |
| BR-002 | Business Rule | <1–5 word topic> | <first 80 chars of rule description> |
| TR-001 | Technical Rule | <1–5 word topic> | <first 80 chars of rule description> |
| C-001 | Constraint | <1–5 word topic> | <first 80 chars of constraint description> |
```

## Index Format — V2 (when extraction_mode = V2)

```markdown
# Knowledge Index — <source_name>

**Source:** <source_name>
**Full Artifact:** knowledge_base/extracted/<source_name>_knowledge[_v<n>].md
**Generated:** <date>
**workspace_version:** v2

| ID | Type | Topic | Excerpt | Version |
|----|------|-------|---------|---------|
| BR-005 | Business Rule | <1–5 word topic> | <first 80 chars of new rule text> | v2-modified |
| BR-013 | Business Rule | <1–5 word topic> | <first 80 chars of deprecation reason> | v2-deprecated |
| BR-016 | Business Rule | <1–5 word topic> | <first 80 chars of rule description> | v2-added |
| TR-017 | Technical Rule | <1–5 word topic> | <first 80 chars of rule description> | v2-added |
| C-009 | Constraint | <1–5 word topic> | <first 80 chars of constraint description> | v2-added |
```

## Index Rules

- Row order: all BR-NNN rows ascending, then all TR-NNN rows ascending, then all C-NNN rows ascending.
- **Topic:** 1–5 words summarizing what the item governs (e.g., "User authentication", "Lot age limit").
- **Excerpt:** first 80 characters of the rule or constraint text (the part after the identifier prefix). Append `…` if truncated.
- If no BR, TR, or C items were extracted, the table has zero data rows. Write the index anyway.
- Do not include Facts, Decisions, Assumptions, Terminology, or Workflows in the index.
- V2 mode `Version` column values:
  - `v2-added` — new rule; new v2 ID assigned
  - `v2-modified` — modifies a v1 rule; v1 ID retained
  - `v2-deprecated` — v1 rule retired; v1 ID retained

---

# Registry Update Rules

After successful processing, update:

```text
runtime/sources.md
```

The registry contains one row per source file.

The registry row must contain:

* source filename;
* extension;
* status;
* generated knowledge artifact path;
* generated knowledge index artifact path.

### Status Mapping

| User Decision | Registry Status |
| ------------- | --------------- |
| OVERWRITE     | re-extracted    |
| NEW VERSION   | extracted       |
| FAILURE       | failed          |

### Registry Behavior

For OVERWRITE:

* update the existing registry row;
* set status to `re-extracted`;
* keep Knowledge Artifact pointing to the overwritten artifact.

For NEW VERSION:

* do not create a second registry row;
* update the existing registry row;
* set status to `extracted`;
* update the Knowledge Artifact field to reference the latest versioned artifact.

For FAILURE:

* update the registry row when possible;
* set status to `failed`;
* keep Knowledge Artifact pointing to the last successful artifact when one exists.

---

# Failure Handling

Stop execution if:

* source material is missing;
* source material cannot be read;
* source registry cannot be read;
* extracted information cannot be traced;
* repository structure is invalid.

Report failures explicitly.

---

# Completion Criteria

Execution is complete when:

* all available sources have been processed or skipped by user decision;
* knowledge artifacts have been generated for processed sources;
* knowledge index artifacts have been generated alongside all knowledge artifacts;
* all BR-NNN, TR-NNN, and C-NNN items carry sequential identifiers;
* a `## Provenance Index` section is present as the **last section** of each full knowledge artifact;
* every BR-NNN, TR-NNN, and C-NNN item has exactly one row in the Provenance Index;
* every `ID` row carries a non-empty `rationale` and a non-empty `impact_level`;
* every `TS` row carries a non-empty `rationale`;
* validation checks have passed;
* outputs have been written to the repository;
* the source registry has been updated with both artifact paths.
