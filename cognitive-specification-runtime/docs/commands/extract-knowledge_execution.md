# Extract Knowledge Execution Specification

## Purpose

Define the runtime execution process used by the `/extract-knowledge` command.

The objective is to transform source material into structured and traceable knowledge artifacts.

---

# Execution Flow

```text
[V2 Context Detection]
→ Discover Sources
→ Check Source Registry
→ Request User Decision
→ Analyze
→ Extract  (+ intra-doc contradiction check Phase 5.5)
→ Structure (+ v2 annotations if V2 mode)
→ Validate
→ Persist
```

---

## Phase 0 — V2 Context Detection

### Objective

Determine whether extraction is running inside a V2 workspace. V2 context affects identifier numbering and rule annotation. This phase runs once, before any source is touched.

### Actions

1. Check if `WORKSPACE_ROOT/runtime/lineage.md` exists.
2. **If found:** set `extraction_mode = V2`. Read `source_workspace_id` from the lineage file. Proceed to ID Base Determination (Step 0.3).
3. **If not found:** set `extraction_mode = V1`. All downstream behavior is unchanged from standard execution. Skip to Phase 1.

### Step 0.3 — V2 ID Base Determination

Purpose: establish the ceiling of v1 identifiers so new v2 IDs continue sequentially without collision.

1. Locate the inherited traceability matrix in `WORKSPACE_ROOT/specifications/stable/`. Match any file ending in `_traceability.md`.
2. Read all BR-NNN, TR-NNN, and C-NNN identifiers present in the matrix.
3. Record:
   - `max_br` = highest BR numeric suffix found (e.g., BR-015 → `max_br = 15`). If no BR rows: `max_br = 0`.
   - `max_tr` = highest TR numeric suffix found. If none: `max_tr = 0`.
   - `max_c` = highest C numeric suffix found. If none: `max_c = 0`.
4. New v2 identifiers will start at `max_br + 1`, `max_tr + 1`, `max_c + 1` respectively.
5. If no traceability matrix is found in `specifications/stable/`: halt with:
   ```
   V2 ID BASE ERROR — Cannot determine v1 ID ceiling.
   Expected: WORKSPACE_ROOT/specifications/stable/*_traceability.md
   Archive the parent workspace first, then run V2 FORK to inherit the BASELINED spec.
   ```

### Output

```text
extraction_mode = V1 | V2
[V2 only] source_workspace_id (from lineage.md)
[V2 only] max_br, max_tr, max_c  (v1 ID ceiling values)
```

---

## Phase 1 — Source Discovery

### Objective

Identify source material available for extraction.

### Inputs

```text
knowledge_base/raw/
runtime/sources.md
```

### Actions

* Discover ingested raw records in `knowledge_base/raw/`.
* For each raw record, identify the original source file via `origin_path`.
* Verify original source accessibility.
* Verify original source readability.
* Read the source registry from `runtime/sources.md`.
* Build source inventory.

### Failure Conditions

* no ingested raw records exist in `knowledge_base/raw/`;
* source material cannot be read;
* source registry cannot be read.

### Output

```text
Source Inventory
```

---

## Phase 2 — Source Registry Check

### Objective

Determine whether discovered sources have already been processed.

### Actions

For each discovered source:

* Compare filename and extension against the registry.
* Classify the source as:

  * New
  * Previously Processed

### Fingerprint Staleness Check

For each source that already exists in the registry:

1. Read stored `source_fingerprint` from the registry row.
2. If `source_fingerprint` is absent or empty in the registry: skip staleness check (fingerprint not yet computed — older registry entry).
3. If `source_fingerprint` is present: compute the current fingerprint from the preprocessed artifact (same formula as `/preprocess-source` Phase 7c). If no preprocessed artifact exists: skip staleness check.
4. Compare current fingerprint with stored value.
5. If they differ: set `staleness_flag = TRUE` for this source.
6. If they match: set `staleness_flag = FALSE`.

The staleness flag is displayed in the user decision prompt (see Phase 3 — User Decision).

### Output

```text
Classified Source Inventory
```

---

## Phase 3 — User Decision

### Objective

Request human guidance for previously processed sources.

### Actions

For each previously processed source, ask the user whether to:

* SKIP
* OVERWRITE
* NEW VERSION

### Rules

#### SKIP

* Do not process the source.
* Update the source registry.
* Set status to `skipped`.
* Keep the current Knowledge Artifact reference.
* Continue with the next available source.

#### OVERWRITE

* Reprocess the source.
* Replace the existing knowledge artifact.

#### NEW VERSION

* Reprocess the source.
* Create a new versioned knowledge artifact.

### Output

```text
Extraction Plan
```

---

## Phase 4 — Source Analysis

### Objective

Understand source content before extraction.

### Actions

* Read source content.
* Identify major topics.
* Identify knowledge-rich sections.
* Identify explicit information.
* Ignore formatting noise.

### Output

```text
Analyzed Source
```

---

## Phase 5 — Knowledge Extraction

### Objective

Extract relevant knowledge and assign structured identifiers.

### Extraction Targets

* Facts
* Decisions
* Assumptions
* Constraints
* Terminology
* Business Rules
* Technical Rules

### Rules

Only extract information supported by evidence.

Do not invent knowledge.

Do not infer undocumented decisions.

Do not generate speculative knowledge.

### Identifier Assignment

#### V1 Mode (extraction_mode = V1)

Assign sequential identifiers starting at `001` for each processed source:

| Category | Format | Sequence |
|----------|--------|---------|
| Business Rules | BR-NNN | BR-001, BR-002, … |
| Technical Rules | TR-NNN | TR-001, TR-002, … |
| Constraints | C-NNN | C-001, C-002, … |

Identifiers are artifact-scoped. On OVERWRITE: renumber from `001`. On NEW VERSION: renumber from `001` in the new artifact.

#### V2 Mode (extraction_mode = V2)

IDs must be globally unique across v1 and v2. Per `runtime/id_governance.md` (Rule IG-002): new v2 IDs are a strict sequential continuation of v1 IDs.

Start numbering from the v1 ceiling computed in Phase 0:

| Category | Start |
|----------|-------|
| Business Rules | `max_br + 1` (e.g., if max_br = 15 → start at BR-016) |
| Technical Rules | `max_tr + 1` |
| Constraints | `max_c + 1` |

Do NOT renumber from 001 in V2 mode. Renumbering from 001 would collide with inherited v1 IDs.

On OVERWRITE or NEW VERSION in V2 mode: re-apply the same v2 ceiling start (re-read Phase 0 ceiling values).

No Business Rule, Technical Rule, or Constraint may be written to the output artifact without an identifier.

#### V2 — Annotation Type Determination

Before assigning an identifier in V2 mode, determine the annotation type for each extracted rule. The v2 source document must provide an explicit signal to trigger `[v2-modified]` or `[DEPRECATED in v2]`. In the absence of a signal, default to `[v2-added]`.

**`[v2-added]`** — Rule has no reference to any v1 rule. It is new in v2.
- Assign a new v2 ID starting from the v1 ceiling (max_br+1, max_tr+1, max_c+1 as appropriate).
- Format: `**BR-016** \`[v2-added]\` — <rule text>`

**`[v2-modified]`** — Source explicitly signals that this rule replaces or modifies a specific v1 rule.
Recognized signals: "remplace BR-005", "modifie BR-005", "updated from BR-005", "supersedes BR-005", "BR-005 est désormais", "see also: BR-005 (v1)".
- Use the referenced v1 ID (e.g., BR-005). Do NOT assign a new v2 ID.
- Format: `**BR-005** \`[v2-modified]\` — <new rule text>`
- Verify the v1 ID exists in the inherited traceability matrix (Phase 0 ceiling). If not found: treat as `[v2-added]` with a new ID; log `V2-MOD-WARN: referenced v1 ID <ID> not found in traceability matrix — treated as v2-added`.

**`[DEPRECATED in v2]`** — Source explicitly retires a specific v1 rule without providing a replacement.
Recognized signals: "supprime BR-013", "BR-013 is no longer applicable", "BR-013 retired", "deprecated: BR-013", "removed: BR-013".
- Use the referenced v1 ID (e.g., BR-013). Do NOT assign a new v2 ID.
- Format: `**BR-013** \`[DEPRECATED in v2]\` — <reason from source, or "Rule retired in v2">`
- Verify the v1 ID exists in the inherited traceability matrix. If not found: log `V2-DEP-WARN: referenced v1 ID <ID> not found in traceability matrix — deprecation skipped`.

### Output

```text
Raw Knowledge Set (with identifiers assigned)
```

---

## Phase 5.5 — Intra-Document Contradiction Check (Bloc 5)

### Objective

Detect logical contradictions between rules extracted from the same source document. This phase runs while the LLM has the full document and the complete extracted rule set in context — the optimal window for intra-source analysis.

This phase is non-blocking: contradictions are flagged and persisted as conflict artifacts, but extraction proceeds to Phase 6 regardless of findings.

### Input

Raw Knowledge Set from Phase 5 — all BR-NNN, TR-NNN, and C-NNN items with assigned identifiers.

### Detection Procedure

For each pair of rules (BR/TR/C) within the extracted set:

**Step 5.5.1 — Domain clustering**

Group rules by domain: same entity (ex: ri_lot, user), same actor (ex: Chimiste, Conditionneur), same action (ex: scan, validate), same lifecycle state (ex: Entrée, Mise à disposition). Only pairs within the same domain cluster are candidates for contradiction.

**Step 5.5.2 — Contradiction test**

A pair (Rule A, Rule B) constitutes an INTRA_CONTRADICTION when ALL of the following hold:

1. Both rules address the **same situation**: same actor AND same action AND same state/condition.
2. Rule A asserts an outcome X.
3. Rule B asserts an outcome that is incompatible with X (opposite, exclusive, or numerically irreconcilable).
4. Neither rule limits its scope to conditions that would make the two rules non-overlapping.

**Step 5.5.3 — Conditional exclusion test**

A pair is NOT a contradiction when ANY of the following hold:

| Exclusion condition | Example from this source |
|---------------------|--------------------------|
| Different actors | BR-012 (Chimiste / Classique) vs BR-013 (Chimiste / Spécifique) — different lot type |
| Different lifecycle states | BR-002 (Entrée→Conditionnement) vs BR-003 (Conditionnement→MàD) — different states |
| General case vs specific exception | Rule B is a specialization of Rule A; the specific case prevails |
| Different time horizons or triggers | BR-006 (availability date) vs BR-007 (creation date) — different date fields |
| Different recipients or channels | Rules address different actors even if they share the same trigger |

If a pair passes Step 5.5.2 AND fails Step 5.5.3 (no exclusion applies): flag as INTRA_CONTRADICTION.

### Conflict Artifact

If one or more INTRA_CONTRADICTIONs are detected, write:

```text
knowledge_base/conflicts/<source_name>_intra_contradictions.md
```

**Format:**

```markdown
# Intra-Document Contradiction Report

**Source:** <source_name>
**Knowledge Artifact:** knowledge_base/extracted/<artifact_path>
**Generated:** <date>
**Generated by:** /extract-knowledge Phase 5.5 (Bloc 5)

## Summary

| ID | Type | Rules Involved | Severity | Status |
|----|------|----------------|----------|--------|
| IC-001 | INTRA_CONTRADICTION | BR-XXX, BR-YYY | BLOCKING | open |

## Conflicts

### IC-001

**Type:** INTRA_CONTRADICTION
**Severity:** BLOCKING
**Status:** open

**Rule A (BR-XXX):** <full text of rule A>
**Rule B (BR-YYY):** <full text of rule B>

**Contradiction:** <Why these two rules are logically incompatible in the same context>

**Conditional exclusion test:** <Why neither exclusion condition from Step 5.5.3 applies>

**Resolution path:** /human-validation → /consolidate-knowledge
```

If no INTRA_CONTRADICTIONs are detected, write a clean confirmation:

```text
knowledge_base/conflicts/<source_name>_intra_contradictions.md
```

```markdown
# Intra-Document Contradiction Report

**Source:** <source_name>
**Knowledge Artifact:** knowledge_base/extracted/<artifact_path>
**Generated:** <date>
**Generated by:** /extract-knowledge Phase 5.5 (Bloc 5)

## Result

No intra-document contradictions detected.

All BR-NNN, TR-NNN, and C-NNN rule pairs were analyzed. No pair passed both
the contradiction test (Step 5.5.2) and failed the conditional exclusion test (Step 5.5.3).

The extracted knowledge base is internally consistent for this source.
```

### ID Space

Intra-contradiction IDs use the prefix `IC-NNN` (e.g., IC-001, IC-002) to distinguish from detect-conflicts' `C-NNN` space. Both spaces may coexist in `knowledge_base/conflicts/` without collision.

### Non-Blocking Behavior

Phase 5.5 findings do not halt extraction. Phase 6 proceeds regardless of results.

If INTRA_CONTRADICTIONs are detected: include a summary note at the end of the Phase 5.5 output before proceeding to Phase 6:

```text
INTRA_CONTRADICTION: <N> contradiction(s) detected. Conflict artifact written to
knowledge_base/conflicts/<source_name>_intra_contradictions.md.
Extraction continues. Submit to /human-validation before /generate-specification.
```

### Output

```text
INTRA_CONTRADICTION report at knowledge_base/conflicts/<source_name>_intra_contradictions.md
(clean or flagged)
```

---

## Phase 5.7 — Provenance Classification (KPM)

### Objective

Classify the provenance of every extracted BR-NNN, TR-NNN, and C-NNN item using the Q1–Q6 algorithm defined in ADR-004 / KPM-001. This phase runs after all identifiers have been assigned and intra-document contradictions have been checked, while the full source document is still in context.

### Input

Complete extracted rule set from Phase 5 (all BR-NNN, TR-NNN, C-NNN items with identifiers assigned) and the source document content.

### Q1–Q6 Classification Algorithm

Apply in order. First affirmative answer determines the provenance type.

```
Q1. Is the element directly observable in the source document
    (verbatim text or direct reformulation without addition)?
    → YES → SOURCE_FACT (SF)

Q2. Was the element explicitly confirmed during a traceable
    validation session (VQ-NNN, VAL-NNN) already recorded?
    → YES → USER_VALIDATED (UV)

Q3. Does the element follow by logical necessity from SF/UV
    premises only (no alternative conclusion possible),
    with ALL premises classified SF or UV (not ID)?
    → YES → DERIVED_KNOWLEDGE (DK)

Q4. Is the need for this element established by SF/UV,
    AND does exactly one industry-documented standard apply,
    AND would any other value be a deliberate deviation
    from that standard?
    → YES → TECH_STANDARD (TS)

Q5. Did CSR select this element from identifiable alternatives
    (other valid choices exist that are not mandated by source,
    validation, standard, or logical necessity)?
    → YES → INFERRED_DESIGN (ID)

Q6. (Default — gap CSR cannot resolve)
    → UNDEFINED_IN_SOURCE (US)
```

### Cascade Rule R4

Before finalizing the classification of DK elements: if any premise of a DK derivation is itself classified ID, the derived element inherits ID, not DK. Re-classify accordingly.

### Structural Impact Criteria (for ID elements only)

An INFERRED_DESIGN element has `impact_level: structural` if it satisfies at least one of:

| Code | Condition |
|---|---|
| S1 | Introduces a new entity (table, list, object) absent from source and validations |
| S2 | Defines new lifecycle or workflow states visible to end users |
| S3 | Modifies the solution boundary (new integrations, new external interfaces) |
| S4 | Affects permission assignments or access control |

An ID element satisfying none of S1–S4 has `impact_level: implementation`.

### Governance Status Assignment

| Type | `governance_status` |
|---|---|
| SF, UV, DK | not tracked (columns left as `—`) |
| TS | `ACKNOWLEDGED` |
| ID with `impact_level: structural` | `PENDING_VALIDATION` |
| ID with `impact_level: implementation` | `REGISTERED` |
| US | `BLOCKED` |

### Provenance Record Format

For each classified item, build a provenance record with these fields:

| Field | Meaning | Required for |
|---|---|---|
| `ID` | BR-NNN / TR-NNN / C-NNN | All |
| `Type` | SF \| UV \| DK \| TS \| ID \| US | All |
| `Refs` | Source reference for SF (format: `<source_name>#<section-heading>`) or standard identifier for TS (e.g., `ISO-3166-1`); `—` otherwise | SF (required), TS (standard ref), DK (recommended) |
| `Rationale` | One sentence justifying the classification | ID (required), TS (required), DK (optional); `—` for SF/UV/US |
| `Impact` | `structural` or `implementation` | ID only; `—` for all others |
| `Statut` | governance_status value or `—` | ID (required), US (required), TS (required); `—` for SF/UV/DK |

**source_refs format (I-1 decision):** `<source_base_name>#<section-heading>` where `section-heading` is the normalized `#` heading of the section containing the item (lowercase, hyphens for spaces). If the item spans multiple sections or no heading applies: use `<source_base_name>` without a fragment. Examples: `demo-retail-teams-transcript#requirements`, `condicolo-technical-doc#business-rules`.

### Ambiguity Resolution Rules

**R1 — Partial:** Element partly in source, partly added → classify each part independently; the element receives the most conservative classification.

**R2 — Enrichment:** Precision added to an SF element → the added precision is TS or ID per Q4/Q5; the base element remains SF.

**R3 — Platform conventions:** Vendor-documented conventions (Microsoft Dataverse, Power Platform, SharePoint) → TS. Undocumented common patterns → ID.

### Output

```text
Classified provenance record set: one record per BR-NNN / TR-NNN / C-NNN item.
Ready for inclusion in ## Provenance Index (Phase 6).
```

---

## Phase 6 — Knowledge Structuring

### Objective

Convert extracted knowledge into a standardized format with mandatory identifiers on BR, TR, and Constraint items.

### V1 Output Structure

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
| BR-002 | DK | <source_name>#<section-heading> | — | — | — |
| TR-001 | TS | <standard_identifier> | <one sentence> | — | ACKNOWLEDGED |
| TR-002 | ID | — | <one sentence justifying the design choice> | structural | PENDING_VALIDATION |
| C-001 | SF | <source_name>#<section-heading> | — | — | — |
| C-002 | US | — | — | — | BLOCKED |
```

Every BR-NNN, TR-NNN, and C-NNN item in the knowledge artifact must have exactly one row in the Provenance Index. Rows are ordered: all BR-NNN ascending, then TR-NNN ascending, then C-NNN ascending. Sections containing no extracted items are omitted from the artifact — but every item that IS present must appear in the Provenance Index.

### V2 Output Structure

When `extraction_mode = V2`, the artifact includes a V2 header block and all extracted rules carry an annotation tag (`[v2-added]`, `[v2-modified]`, or `[DEPRECATED in v2]`). Modified and deprecated rules use their original v1 IDs; only added rules receive new v2 IDs.

```markdown
**workspace_version:** v2
**source_workspace:** <source_workspace_id> (v1 parent)
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
| BR-016 | ID | — | <one sentence justifying the design choice> | implementation | REGISTERED |
| TR-017 | TS | <standard_identifier> | <one sentence> | — | ACKNOWLEDGED |
| C-009 | SF | <source_name>#<section-heading> | — | — | — |
```

The Provenance Index in V2 mode covers all BR/TR/C items present in the artifact — both inherited (v2-modified, v2-deprecated) and new (v2-added). Modified and deprecated rules appear inline in the same section as their type, ordered by ascending ID alongside `[v2-added]` rules.

Three annotation tags are recognized by downstream stages:

| Tag | Meaning | ID used |
|-----|---------|---------|
| `[v2-added]` | New rule in v2 | New v2 ID (from ceiling) |
| `[v2-modified]` | Modifies a v1 rule | v1 ID retained |
| `[DEPRECATED in v2]` | Retires a v1 rule | v1 ID retained |

These tags are the downstream signals consumed by:
- `/generate-specification` → Phase 4.2a tag detection; Phase 6b.1 mutation (modified replaces v1 text, deprecated marks retired, added inserts new)
- `/generate-traceability` → `version_introduced`, `version_updated`, `Status` columns
- `/generate-test-cases` → Suite 1 (régression, rules modified/deprecated from v1) vs Suite 2 (nouvelles fonctionnalités, `[v2-added]` rules)

Sections containing no extracted items are omitted in both modes.

### Output

```text
Structured Knowledge Artifact (V1 or V2 format)
```

---

## Phase 7 — Validation

### Objective

Validate extracted knowledge.

### Validation Rules

Each knowledge item must:

* be traceable;
* be source-backed;
* be understandable;
* be unambiguous;
* be non-duplicated.

### Step 7.1 — ADR-001 Language Compliance Check (Early Checkpoint)

The knowledge artifact is the **first canonical runtime artifact** a project produces. Under ADR-001 it must be English, whatever the language of the source document.

Before the artifact is persisted, verify that every item of the assembled knowledge content is written in English. This covers all extracted sections (Facts, Workflows, Constraints, Terminology, Business Rules, Technical Rules, Decisions, Assumptions) and the `rationale` field of every Provenance Index entry.

Two values are explicitly **out of scope** of this check and must not be flagged:

* the `refs` column of the Provenance Index, which carries source-document anchors and legitimately reproduces original-language headings;
* quoted source wording deliberately preserved inside an item, where the quotation is marked as such.

If non-English content is detected:

```text
STATUS: BLOCKED — ADR-001 Compliance Failure: non-English content detected in the knowledge artifact for <base> (<section> / <item_id>). Extraction must normalize canonical content into English. The source document is not modified.
```

Stop. Do not proceed to Phase 8. No artifact is persisted.

This command performs normalization as part of extraction — it is not a translation stage bolted on afterwards. The check exists to catch the case where extraction mirrored the source language instead of normalizing it.

**Why this checkpoint is here.** `/consolidate-knowledge` Step 2.1a already enforces ADR-001, but it runs four commands later. A failure detected there means extraction, conflict detection, question generation and human validation have all already produced artifacts in the wrong language, and the whole chain must be retranslated. Catching the drift at the first artifact that can carry it keeps the correction to a single file. See ADR-001 § Compliance Checkpoints.

### Failure Conditions

* missing source reference;
* unsupported statement;
* ambiguous extracted item;
* duplicated knowledge item;
* unreadable artifact;
* non-English content in canonical knowledge content or in a Provenance Index `rationale` (Step 7.1, ADR-001);
* BR-NNN / TR-NNN / C-NNN item present in artifact without a corresponding Provenance Index entry;
* ID or TS entry in Provenance Index with empty `rationale`;
* ID entry in Provenance Index without `impact_level`;
* type value not in the recognized set: `SF`, `UV`, `DK`, `TS`, `ID`, `US`.

### Output

```text
Validated Knowledge Artifact (including Provenance Index)
```

---

## Phase 8 — Persistence

### Objective

Store generated knowledge artifacts and knowledge index artifacts; update the source registry.

### Output Location

```text
knowledge_base/extracted/
```

### Step 8a — Write Full Knowledge Artifact

**Standard naming:**

```text
<source_name>_knowledge.md
```

**Versioned naming (NEW VERSION):**

```text
<source_name>_knowledge_v<n>.md
```

The version number is the highest existing `_knowledge_v*.md` version plus one. If no versioned artifact exists, `<source_name>_knowledge.md` is version 1 and the first new version is `<source_name>_knowledge_v2.md`.

### Step 8b — Write Knowledge Index Artifact

After writing the full artifact, generate and write the knowledge index.

**Naming:**

```text
<source_name>_knowledge_index.md         ← paired with <source_name>_knowledge.md
<source_name>_knowledge_index_v<n>.md    ← paired with <source_name>_knowledge_v<n>.md
```

**V1 index format:**

```markdown
# Knowledge Index — <source_name>

**Source:** <source_name>
**Full Artifact:** knowledge_base/extracted/<source_name>_knowledge[_v<n>].md
**Generated:** <date>

| ID | Type | Topic | Excerpt |
|----|------|-------|---------|
| BR-001 | Business Rule | <1–5 word topic> | <first 80 chars of rule> |
| TR-001 | Technical Rule | <1–5 word topic> | <first 80 chars of rule> |
| C-001 | Constraint | <1–5 word topic> | <first 80 chars of constraint> |
```

**V2 index format** (when `extraction_mode = V2`):

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
| BR-016 | Business Rule | <1–5 word topic> | <first 80 chars of rule> | v2-added |
| TR-017 | Technical Rule | <1–5 word topic> | <first 80 chars of rule> | v2-added |
| C-009 | Constraint | <1–5 word topic> | <first 80 chars of constraint> | v2-added |
```

**Index rules (both modes):**
- Rows are ordered: all BR-NNN rows ascending, then all TR-NNN rows ascending, then all C-NNN rows ascending.
- Topic: 1–5 words summarizing what the item governs.
- Excerpt: first 80 characters of the item description (text after the identifier prefix); truncate with `…` if longer.
- If no BR, TR, or C items were extracted, the table has zero data rows. The index is still generated.
- V2 mode `Version` column values:
  - `v2-added` — new rule; new v2 ID assigned
  - `v2-modified` — modifies a v1 rule; v1 ID retained
  - `v2-deprecated` — v1 rule retired; v1 ID retained

---

## Registry Update

Update:

```text
runtime/sources.md
```

The registry must contain one row per source file.

The registry row must include:

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
* update Knowledge Artifact and Knowledge Index to the overwritten paths.

For NEW VERSION:

* do not create a second registry row;
* update the existing registry row;
* set status to `extracted`;
* update Knowledge Artifact to the latest versioned artifact path;
* update Knowledge Index to the matching versioned index path.

For FAILURE:

* update the registry row when possible;
* set status to `failed`;
* keep Knowledge Artifact and Knowledge Index pointing to the last successful artifacts when they exist.

### Output

```text
Persisted Knowledge Artifact
Persisted Knowledge Index Artifact
Updated Source Registry
```

---

## Traceability Rules

Every extracted item must preserve a source reference.

Traceability information must remain available for downstream runtime stages.

---

## Completion Criteria

Execution is complete when:

* all available sources have been processed or skipped by user decision;
* knowledge artifacts have been generated for processed sources;
* knowledge index artifacts have been generated alongside all knowledge artifacts;
* all BR-NNN, TR-NNN, and C-NNN items carry sequential identifiers starting at 001;
* a `## Provenance Index` section is present as the final section of each full knowledge artifact;
* every BR-NNN, TR-NNN, and C-NNN item in the artifact has exactly one row in the Provenance Index;
* every `ID` and `TS` row in the Provenance Index carries a non-empty `rationale`;
* every `ID` row carries a non-empty `impact_level` (`structural` or `implementation`);
* validation has succeeded;
* artifacts have been written to the repository;
* runtime/sources.md has been updated with both knowledge artifact and knowledge index paths.
