# /generate-test-cases

## Purpose

Generate a bilingual test specification book (cahier de recette) from a BASELINED specification.

Each Business Rule, Technical Rule, and Constraint in the specification becomes a traceable test case with preconditions, test steps, expected result, and pass criterion. The output is the primary artifact for functional acceptance testing and stakeholder sign-off.

This command implements the M-TC milestone of the CSR pipeline.

---

## Inputs

### Required

```text
WORKSPACE_ROOT/specifications/stable/<base>_specification.md   ← Status: BASELINED
WORKSPACE_ROOT/specifications/stable/<base>_traceability.md
runtime/id_governance.md
docs/commands/generate-test-cases_execution.md
templates/commands/generate_test_cases_prompt.md
```

### Optional

```text
templates/word/csr_view_reference.docx   ← Word template for Phase 10 DOCX export
```

---

## Outputs

### Primary (Markdown — authoritative)

```text
WORKSPACE_ROOT/output/test-cases/<base>_test_cases_fr.md
WORKSPACE_ROOT/output/test-cases/<base>_test_cases_en.md
```

### Supplementary (Word — Phase 10, requires Pandoc)

```text
WORKSPACE_ROOT/output/test-cases/<base>_test_cases_fr.docx
WORKSPACE_ROOT/output/test-cases/<base>_test_cases_en.docx
```

### Traceability update (in-place)

```text
WORKSPACE_ROOT/specifications/stable/<base>_traceability.md   ← Test Cases column added
```

---

## Preconditions

1. Active workspace resolves correctly (standard W1–W5 resolution).
2. At least one specification with `Status: BASELINED` exists in `WORKSPACE_ROOT/specifications/stable/`.
3. The corresponding traceability matrix exists and is non-empty.
4. `runtime/id_governance.md` exists.
5. Pandoc is recommended for Word export (`pandoc --version`). If absent, Phase 10 is skipped — not blocking.

---

## Coverage Requirement

100% rule coverage is mandatory. Every row in the traceability matrix must produce exactly one test case. Execution is blocked if any rule has no corresponding test case.

---

## Status Assignment

| Status | When |
|--------|------|
| `OPEN` | Rule is fully specified — test is ready for execution |
| `PENDING_PO_INPUT` | Rule depends on an unresolved specification gap requiring stakeholder input |
| `PENDING_CLARIFICATION` | An ambiguity in the knowledge base requires clarification before expected results can be confirmed |

`PENDING` statuses must carry a justification note naming the open question and the contact responsible.

---

## Bilingual Output

Every execution produces two companion files per `docs/conventions/bilingual_output.md`.

For proj-test-01 (French source): `_fr.md` is primary; `_en.md` is the translated companion.

Technical identifiers (`BR-NNN`, `TC-NNN`, status codes, formulas, identifiers) appear identically in both files.

---

## Completion Criteria

Execution is complete when:

* all rules from the traceability matrix have exactly one test case;
* TC-NNN identifiers are sequential without gaps (starting at TC-001);
* all PENDING statuses carry a justification note;
* both bilingual Markdown files exist in `WORKSPACE_ROOT/output/test-cases/`;
* both bilingual DOCX files exist in `WORKSPACE_ROOT/output/test-cases/` (or Phase 10 SKIPPED if Pandoc absent);
* the traceability matrix `Test Cases` column is populated for all rows;
* the coverage summary in the document matches the traceability matrix.

---

## Failure Handling

Stop execution and report when:

* no BASELINED specification found;
* traceability matrix cannot be read or is empty;
* coverage falls below 100% (any rule without a TC).

---

## Pipeline Position

| Stage | Command | Output |
|-------|---------|--------|
| 8 | `/specification-lifecycle BASELINE` | Canonical spec (BASELINED) |
| 9 | `/generate-views` | 4 audience view artifacts |
| 10 | `/generate-test-cases` | Bilingual test case book (MD + DOCX) |

`/generate-test-cases` requires Stage 8 to be complete before it can run.

---

## Relationship to Versioning V2

When the workspace carries a `v2` lineage (`runtime/lineage.md` present), the test suite must distinguish:

* **Suite 1 — Régression v1:** test cases for rules with `version_introduced: v1`
* **Suite 2 — Nouvelles fonctionnalités:** test cases for rules with `version_introduced: v2`

See `docs/commands/workspace-lifecycle.md` V2 FORK operation for lineage context.
