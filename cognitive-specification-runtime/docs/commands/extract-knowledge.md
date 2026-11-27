# /extract-knowledge

## Purpose

Extract actionable knowledge from source material and store it in a structured and traceable format.

The command transforms raw source content into knowledge artifacts that can be used by downstream runtime stages.

**This command also checks a single source for contradictions within itself** (Bloc 5 — intra-document contradiction detection, corrected 2026-11-01: this capability existed and ran in production since 2026-07-05 but was never stated in this L1 contract). `/detect-conflicts` checks contradictions *between* sources; it has no visibility into a single document. A document whose section 3 asserts X and section 12 asserts not-X, with no second source involved, would otherwise pass extraction silently. See Outputs and Execution Rules below.

---

## Inputs

Accepted inputs:

* One or more ingested raw records located in `workspaces/<workspace_id>/knowledge_base/raw/`

Sources must have been processed by `/ingest-source` before extraction can proceed.

Input sources must already exist inside the repository.

---

## Outputs

Generated knowledge artifacts stored in:

```text
workspaces/<workspace_id>/knowledge_base/extracted/
```

Outputs may include:

* facts
* decisions
* assumptions
* constraints
* terminology
* business rules
* technical rules

All generated knowledge must preserve traceability to the originating source.

For each processed source, three artifacts are generated:

1. **Full knowledge artifact** — complete structured knowledge in all sections, followed by a `## Provenance Index` section classifying the provenance of every BR-NNN, TR-NNN, and C-NNN item per ADR-004 / KPM-001 taxonomy.
2. **Knowledge index artifact** — compact single-table summary of all BR-NNN, TR-NNN, and C-NNN items; one row per identifier; enables context-efficient multi-source reasoning in downstream stages (DC, CK). The knowledge index does not include provenance data.
3. **Intra-document contradiction report** (Bloc 5) — written to `knowledge_base/conflicts/<source_name>_intra_contradictions.md`, always produced, whether or not a contradiction was found. A clean result is reported explicitly, not by the file's absence — the same reasoning Section 13's "no open point" convention already applies elsewhere in this runtime. See `docs/commands/extract-knowledge_execution.md` Phase 5.5 for the detection algorithm (INTRA_CONTRADICTION: a pair of BR-NNN/TR-NNN/C-NNN items that conflict and for which no conditional-branch, different-actor, or sequential-step exclusion applies).

---

## Knowledge Identifier Convention

Every extracted Business Rule must carry a `BR-NNN` identifier.
Every extracted Technical Rule must carry a `TR-NNN` identifier.
Every extracted Constraint must carry a `C-NNN` identifier.

Identifiers are sequential within a single knowledge artifact, starting at `001`.

| Prefix | Category |
|--------|----------|
| BR-NNN | Business Rule |
| TR-NNN | Technical Rule |
| C-NNN  | Constraint |

Identifiers are assigned in the order items appear in the source. On OVERWRITE: identifiers are reassigned from `001`. On NEW VERSION: identifiers are reassigned from `001` in the new artifact (identifiers are artifact-scoped, not cross-artifact).

No Business Rule, Technical Rule, or Constraint may appear in a knowledge artifact without an identifier.

---

## Naming Convention

Standard artifact naming:

```text
<source_name>_knowledge.md
<source_name>_knowledge_index.md
```

Examples:

```text
requirements_knowledge.md
requirements_knowledge_index.md
architecture_knowledge.md
architecture_knowledge_index.md
```

Versioned artifact naming:

```text
<source_name>_knowledge_v<n>.md
<source_name>_knowledge_index_v<n>.md
```

Examples:

```text
requirements_knowledge_v2.md
requirements_knowledge_index_v2.md
```

The knowledge index version always matches the corresponding full artifact version.

The version number is determined by scanning:

```text
workspaces/<workspace_id>/knowledge_base/extracted/
```

for existing files matching:

```text
<source_name>_knowledge_v*.md
```

The next version number is the highest existing version number plus one.

If no versioned artifact exists, the first versioned artifact must be:

```text
<source_name>_knowledge_v2.md
<source_name>_knowledge_index_v2.md
```

The unversioned artifact:

```text
<source_name>_knowledge.md
```

is treated as version 1.

---

## Preconditions

The repository must contain at least one ingested raw record in `workspaces/<workspace_id>/knowledge_base/raw/`.

The source material referenced by `origin_path` must be accessible and readable.

The command must not execute on empty input.

The source registry must be available:

```text
workspaces/<workspace_id>/runtime/sources.md
```

---

## Execution Rules

The command shall:

1. Discover available ingested raw records.
2. Check the source registry.
3. Determine whether a source has already been processed.
4. Ask the user for guidance when a source has already been processed.
5. Read source material.
6. Identify relevant knowledge.
7. Extract explicit information.
8. Preserve source traceability.
9. Avoid interpretation beyond available evidence.
10. Assign sequential BR-NNN, TR-NNN, and C-NNN identifiers to all extracted items in those categories.
11. Classify every extracted BR-NNN, TR-NNN, and C-NNN item using the Q1–Q6 algorithm (ADR-004 / KPM-001) to determine its provenance type.
12. Generate the `## Provenance Index` section as the final section of the full knowledge artifact, with one entry per BR-NNN, TR-NNN, and C-NNN item.
13. Check all extracted BR-NNN, TR-NNN, and C-NNN items for intra-document contradictions (Bloc 5) and write the report; proceed to artifact generation regardless of the result (non-blocking).
14. Produce structured Markdown artifacts.
15. Generate a knowledge index artifact alongside the full knowledge artifact.
16. Update the source registry.

---

## Validation Rules

Extracted knowledge must be:

* traceable;
* source-backed;
* understandable;
* unambiguous;
* non-duplicated.

Knowledge without supporting evidence must not be generated.

Provenance classifications must be:

* complete — every BR-NNN, TR-NNN, and C-NNN item has exactly one entry in the `## Provenance Index`;
* justified — every `ID` and `TS` classification carries a non-empty `rationale`;
* correctly typed — types must be one of: `SF`, `UV`, `DK`, `TS`, `ID`, `US`.

---

## Language Policy

Source material may be written in any language.

Extracted knowledge artifacts must be written in English regardless of the source language.

When source content is non-English, knowledge is extracted and rendered in English. The original-language content is not reproduced inside extracted knowledge artifacts.

Traceability to the original source material is preserved through the `origin_path` field in the ingestion registration record. The original-language source document remains accessible via that path.

---

## Source Reprocessing Rules

If a source already exists in the source registry, the command must ask the user whether to:

* SKIP;
* OVERWRITE;
* NEW VERSION.

The command must not silently reprocess a previously registered source.

---

## Source Registry Rules

The registry contains one row per source file.

A source file is uniquely identified by:

* filename;
* extension.

The registry must always reference the currently active knowledge artifact for the source.

For NEW VERSION:

* the existing registry row must be updated;
* the Knowledge Artifact field must reference the latest versioned artifact.

---

## Failure Cases

The command must stop when:

* no ingested raw records exist in `workspaces/<workspace_id>/knowledge_base/raw/`;
* source material cannot be read;
* source registry cannot be read;
* repository structure is invalid;
* extracted content cannot be traced to a source.

Failures must be reported explicitly.

---

## Traceability Rules

Every extracted knowledge item must maintain a reference to its originating source.

Traceability must remain available throughout the runtime lifecycle.

---

## Completion Criteria

The command is considered complete when:

* all available sources have been processed or skipped by user decision;
* knowledge artifacts have been generated for processed sources;
* knowledge index artifacts have been generated alongside all knowledge artifacts;
* an intra-document contradiction report (Bloc 5) has been generated alongside all knowledge artifacts, whether clean or flagged;
* all BR-NNN, TR-NNN, and C-NNN items in knowledge artifacts carry sequential identifiers;
* a `## Provenance Index` section is present and complete in each full knowledge artifact;
* every BR-NNN, TR-NNN, and C-NNN item has exactly one corresponding entry in the Provenance Index;
* every `ID` and `TS` entry in the Provenance Index carries a non-empty `rationale`;
* traceability is preserved;
* outputs have been written to the repository;
* the source registry has been updated;
* validation rules are satisfied.
