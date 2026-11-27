# Generate Test Cases Prompt Template

You are executing the Cognitive Specification Runtime test case generation stage.

Your objective is to transform a BASELINED specification into a complete, traceable test specification book (cahier de recette).

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

Never invent test steps not derivable from the specification.

Never generate speculative expected results.

---

# Objective

For each Business Rule, Technical Rule, and Constraint in the BASELINED specification, produce one test case that:

1. Uniquely identifies the rule being tested (TC-NNN → Rule ID)
2. Describes what the test verifies
3. Specifies preconditions
4. Lists concrete test steps (actor, action, expected result)
5. States the pass criterion
6. Carries the correct status (OPEN / PENDING_PO_INPUT / PENDING_CLARIFICATION)

---

# Source Inputs

## Required inputs

```text
WORKSPACE_ROOT/specifications/stable/<base>_specification*.md   ← BASELINED
WORKSPACE_ROOT/specifications/stable/<base>_traceability.md
runtime/id_governance.md
```

## How to use the traceability matrix

The TM is the authoritative rule inventory. Every row in the TM must produce exactly one TC. Do not add TCs for rules not in the TM. Do not skip rows.

## How to use the specification

Extract rule text from the BASELINED specification for use in TC descriptions and expected results. The exact wording of the spec is the expected result — do not paraphrase rule conditions.

---

# Test Case Format

```markdown
### TC-NNN — [Short title (max 8 words)]

| Field | Value |
|-------|-------|
| Rule | BR/TR/C-NNN |
| Type | Business Rule / Technical Rule / Constraint |
| Version introduced | v1 |
| Domain | <domain name> |
| Priority | HIGH / MEDIUM / LOW |
| Status | OPEN / PENDING_PO_INPUT / PENDING_CLARIFICATION |

**What it verifies:** <1–2 sentences>

**Preconditions:**
- <prerequisite 1>
- <prerequisite 2>

**Test steps:**
| Step | Actor | Action | Expected result |
|------|-------|--------|-----------------|
| 1 | <actor> | <action> | <expected outcome> |

**Pass criterion:** <what PASS means for this TC>

**Notes:** <optional>
```

---

# Test Step Writing Rules

## Be concrete

Each test step must name:
- **Who** does the action (use canonical actor names: Chimiste, Conditionneur, Administrateur, Tester, System, Power Automate)
- **What** they do (action at spec level — not UI click level)
- **What should happen** (expected result for that step)

## Match the rule's logic

For Business Rules: test steps must exercise the rule's trigger condition and verify the outcome.

For Technical Rules: test steps must verify the technical mechanism described in the rule (formula, switch logic, deduplication, etc.). Where the rule describes a formula or algorithm, the test step must reference it.

For Constraints: test steps must verify that the constraint is met in the configured environment (verify configuration, not execution flow).

## Cover negative paths

For rules that describe blocking conditions (access denied, state mismatch, format invalid), include at least one negative step that verifies the error is shown and navigation is blocked.

---

# Domain Assignment

Assign each rule to one of these domains in this order:

1. **Authentification et contrôle d'accès** — matricule scan, profile matching, role bypass, ri_utilisateurcc authority
2. **Saisie d'un nouveau lot** — new lot entry, lot scan, Classique/Spécifique types, format validation
3. **Cycle de vie du lot** — state transitions (Entrée→Cond.→MàD→Sortie), state validation on all screens
4. **Notifications email** — immediate email on MàD, weekly flows (Chimiste + Admin), no-email condition
5. **Gestion des utilisateurs** — Matricule Calc formula, Business Rule copy trigger
6. **Rapports et déploiement** — PBI embedding, pipeline, MANAGED mode, service accounts, licensing, workstation

---

# Priority Rules

| Priority | Criteria |
|----------|----------|
| HIGH | Core lot lifecycle state transition; access control; data integrity |
| MEDIUM | Secondary automation (email, flow logic); format validation; scan routing |
| LOW | Infrastructure; configuration; deployment prerequisites; reporting embedding |

When in doubt between two priorities, assign the lower one.

---

# Status Rules

## OPEN

The rule is fully specified. The test can be designed and executed without additional stakeholder input.

Assign OPEN to all rules unless a PENDING condition applies.

## PENDING_PO_INPUT

The rule contains a specification gap explicitly marked `[UNDEFINED IN SOURCE]` or depends on a constraint that has not been defined in the source. The test cannot be designed or executed until the PO (ROBINAULT Jean-Luc) provides the missing information.

Current PENDING_PO_INPUT rules: BR-013, TR-007, C-008 (all depend on the undefined Spécifique lot format).

In the TC Notes field, write: "Pending PO input: [describe exactly what information is needed]. Contact: ROBINAULT Jean-Luc."

## PENDING_CLARIFICATION

An observation in the knowledge base conflict artifacts raises an ambiguity that could affect the expected result. The test case can be partially designed, but the expected result or scope needs clarification before sign-off.

Current PENDING_CLARIFICATION rules: BR-006, TR-012 (date field ambiguity — "availability date" in BR-006 vs createdon in Flow 1).

In the TC Notes field, write: "Pending clarification: [describe the ambiguity]. Reference: IC-OBS-001 in conflicts/ri-condi-colo-technical-documentation-v1_intra_contradictions.md."

---

# Coverage Requirement

100% coverage is mandatory. Every row in the TM must have exactly one TC. The coverage summary table must list all 39 rows (for SP003 v1) and their TC mapping.

---

# Suite Structure

## Suite 1 — Régression v1

Contains all TCs for rules with `version_introduced: v1`. For SP003, this is all 39 rules.

## Suite 2 — Nouvelles fonctionnalités

Contains TCs for rules with `version_introduced: v2`. For a v1-only specification, this suite exists but contains zero TCs. Include the section heading with the explicit note: "No v2-added rules — this suite will be populated when a V2 workspace is created."

---

# Sign-off Section

End the document with a sign-off table, one row per domain:

```markdown
## Sign-off

| Domain | TCs | Tester | Date | Verdict | Notes |
|--------|-----|--------|------|---------|-------|
| Authentification et contrôle d'accès | N | | | | |
| Saisie d'un nouveau lot | N | | | | |
| Cycle de vie du lot | N | | | | |
| Notifications email | N | | | | |
| Gestion des utilisateurs | N | | | | |
| Rapports et déploiement | N | | | | |
| **Total** | **39** | | | | |
```

Verdict values: PASS / FAIL / PARTIAL

---

# Bilingual Output

Every execution of `/generate-test-cases` produces two companion files per `${CLAUDE_PLUGIN_ROOT}/docs/conventions/bilingual_output.md`.

## File pair

```text
<base>_test_cases_fr.md   ← French version
<base>_test_cases_en.md   ← English version
```

## What to translate

Between the two files, translate:
- All section headings, field labels, column headers
- All narrative text (What it verifies / Ce que le test vérifie, Preconditions / Prérequis, Pass criterion / Critère de réussite, Notes)
- Rule descriptions and test step content
- Domain names

## What NOT to translate

Keep identical in both files: rule IDs (BR/TR/C/TC-NNN), status codes (OPEN, PENDING_*), priority codes (HIGH/MEDIUM/LOW), Dataverse table names, formulas, regex, file paths, proper nouns, CSR command names.

System-displayed strings (Canvas App error messages in French): copy verbatim in both files; in the EN file, add the English translation in parentheses after the French string.

## Field label reference (FR ↔ EN)

| FR | EN |
|----|-----|
| Règle | Rule |
| Type | Type |
| Version introduite | Version introduced |
| Domaine | Domain |
| Priorité | Priority |
| Statut | Status |
| Ce que le test vérifie | What it verifies |
| Prérequis | Preconditions |
| Étapes de test | Test steps |
| Étape | Step |
| Acteur | Actor |
| Action | Action |
| Résultat attendu | Expected result |
| Critère de réussite | Pass criterion |
| Notes | Notes |
| Règle métier | Business Rule |
| Règle technique | Technical Rule |
| Contrainte | Constraint |
| Suite de tests | Test Suite |
| Tableau de couverture | Coverage Summary |
| Validation | Sign-off |

---

# Word Export (Phase 10)

After writing both Markdown files (Phase 8) and updating the TM (Phase 9), convert the test case files to Word format using Pandoc.

## Pre-check

Run:

```bash
pandoc --version
```

If Pandoc is not available: emit `WARNING: Pandoc not found — skipping Word export` and skip to completion. Markdown files are the authoritative output.

## Conversion

```bash
pandoc "WORKSPACE_ROOT/output/test-cases/<base>_test_cases_fr.md" \
  -f markdown-tex_math_dollars -t docx \
  --reference-doc="${CLAUDE_PLUGIN_ROOT}/templates/word/csr_view_reference.docx" \
  -o "WORKSPACE_ROOT/output/test-cases/<base>_test_cases_fr.docx"

pandoc "WORKSPACE_ROOT/output/test-cases/<base>_test_cases_en.md" \
  -f markdown-tex_math_dollars -t docx \
  --reference-doc="${CLAUDE_PLUGIN_ROOT}/templates/word/csr_view_reference.docx" \
  -o "WORKSPACE_ROOT/output/test-cases/<base>_test_cases_en.docx"
```

Use `-f markdown-tex_math_dollars` to prevent `$ControlName` Power Apps identifiers from triggering TeX math parsing.

If `${CLAUDE_PLUGIN_ROOT}/templates/word/csr_view_reference.docx` is absent: omit `--reference-doc` and emit `WARNING: template not found — using Pandoc defaults`.

## Report

Include in completion output:

```text
TC-DOCX FR: output/test-cases/<base>_test_cases_fr.docx — OK / FAILED
TC-DOCX EN: output/test-cases/<base>_test_cases_en.docx — OK / FAILED
```

---

# Validation Before Writing Output

Before writing the output file, verify:

* TC count = TM row count (no missing, no extra)
* All TC-NNN are sequential from TC-001 with no gaps
* All rule IDs appear exactly once
* All PENDING statuses have a Notes entry with a specific pending question
* Coverage summary table matches TC list

Report any discrepancy before writing.
