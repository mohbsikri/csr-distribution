# Generate Test Cases — Execution Specification

## Purpose

Define the runtime execution process used by the `/generate-test-cases` command.

The objective is to transform a BASELINED specification into a complete, traceable test specification book (cahier de recette) suitable for human-executed acceptance testing and stakeholder sign-off.

---

# Execution Flow

```text
Discover Baselined Spec
→ Load Traceability Matrix
→ Build Rule Inventory
→ Cluster by Domain
→ Generate Test Cases
→ Assign Statuses
→ Validate Coverage
→ Persist Output
```

---

## Phase 1 — Specification Discovery

### Objective

Locate the BASELINED specification in the active workspace.

### Actions

* Scan `WORKSPACE_ROOT/specifications/stable/` for files matching `*_specification*.md`.
* Read each candidate file and check the `Status:` field.
* Collect all files where `Status: BASELINED`.
* If exactly one: use it. If multiple: ask the user which to use. If none: BLOCKING.

### Blocking condition

```text
STATUS: BLOCKED — No BASELINED specification found in WORKSPACE_ROOT/specifications/stable/
```

### Output

```text
Identified specification file path and base name
```

---

## Phase 2 — Traceability Matrix Load

### Objective

Build the complete ordered rule inventory from the TM.

### Actions

* Load `WORKSPACE_ROOT/specifications/stable/<base>_traceability.md`.
* Parse all rows from the TM table (columns: ID, Type, Spec Section, Knowledge Section, Knowledge Artifact, Source Document).
* Build rule inventory: ordered list of (ID, Type, Spec Section).
* Verify that every ID follows a known prefix (BR-NNN, TR-NNN, C-NNN).

### Blocking conditions

* TM file not found → BLOCKING.
* TM table is empty → BLOCKING.

### Output

```text
Rule Inventory: ordered list of (ID, Type, Spec Section)
```

---

## Phase 3 — Rule Text Loading

### Objective

Load the text of each rule from the BASELINED specification to use in test case descriptions and expected results.

### Actions

* Read the BASELINED specification file.
* For each rule ID in the inventory, extract the full rule text (everything after `**ID:**` on that line).
* Store (ID → full rule text) map.

---

## Phase 4 — Domain Clustering

### Objective

Group rules by functional domain for structured test suite organisation.

### Domain Assignment Rules

Assign each rule to exactly one domain based on the following criteria:

| Domain | Trigger keywords / rule patterns |
|--------|----------------------------------|
| Authentification et contrôle d'accès | matricule, profil, accès, rôle, administrateur bypass, ri_utilisateurcc authority |
| Saisie d'un nouveau lot | new entry, lot scan, format, Classique, Spécifique, lot exists check |
| Cycle de vie du lot | Entrée, Conditionnement, Mis à disposition, Sortie, state transition, non-entry screen |
| Notifications email | email, notification, weekly flow, chimiste reminder, admin summary, qualifying lots |
| Gestion des utilisateurs | Matricule Calc, Business Rule copy, calculated field |
| Rapports et déploiement | Power BI, deployment, pipeline, MANAGED, service account, license, workstation |

Rules that do not fit a single domain: assign to the domain of their most prominent entity.

### Domain ordering in output

Present domains in the following order:
1. Authentification et contrôle d'accès
2. Saisie d'un nouveau lot
3. Cycle de vie du lot
4. Notifications email
5. Gestion des utilisateurs
6. Rapports et déploiement

---

## Phase 5 — Test Case Generation

### Objective

Generate one test case per rule in the inventory. TC identifiers are assigned sequentially (TC-001, TC-002, …) in domain order (Domain 1 first, then Domain 2, etc.), within each domain in ascending rule ID order.

### TC Format

Each test case must contain the following fields:

```markdown
### TC-NNN — [Short title (max 8 words)]

| Field | Value |
|-------|-------|
| Rule | <ID> |
| Type | <Business Rule / Technical Rule / Constraint> |
| Version introduced | v1 |
| Domain | <domain name> |
| Priority | <HIGH / MEDIUM / LOW> |
| Status | <OPEN / PENDING_PO_INPUT / PENDING_CLARIFICATION> |

**What it verifies:** <1–2 sentence description of what the test validates>

**Preconditions:**
- <list each prerequisite state or data setup>

**Test steps:**
| Step | Actor | Action | Expected result |
|------|-------|--------|-----------------|
| 1 | <actor> | <action> | <expected outcome> |

**Pass criterion:** <concise statement of what constitutes a PASS verdict>

**Notes:** <optional — clarification notes, open questions, dependencies>
```

### Priority Assignment Rules

| Priority | When to assign |
|----------|----------------|
| HIGH | Core business process: lifecycle state transitions, access control, lot entry/exit, data integrity |
| MEDIUM | Secondary automation: email notifications, format validation, scan logic, user management |
| LOW | Infrastructure and configuration: deployment prerequisites, PBI embedding, licensing |

### Status Assignment Rules

| Status | When to assign |
|--------|----------------|
| OPEN | Test case is complete and ready for execution |
| PENDING_PO_INPUT | The rule depends on a specification gap requiring stakeholder input before the test can be defined or executed |
| PENDING_CLARIFICATION | An ambiguity in the source knowledge base needs resolution before the expected result can be confirmed |

Rules currently requiring PENDING status (as of 2026-06-19):

| Rule | Status | Reason |
|------|--------|--------|
| BR-013 | PENDING_PO_INPUT | C-008 gap: Spécifique format not defined in source |
| TR-007 | PENDING_PO_INPUT | C-008 gap: Spécifique format not defined; test depends on PO decision |
| C-008 | PENDING_PO_INPUT | Format constraint for Spécifique lot type not defined in source |
| BR-006 | PENDING_CLARIFICATION | Observation IC-OBS-001: BR-006 says "availability date" but Flow 1 uses createdon; which date field? |
| TR-012 | PENDING_CLARIFICATION | Observation IC-OBS-001: both flows use GetDateOneWeekAgo but BR-006 implies a different date field than createdon |

### Test Step Actors

Use the following actor names in test steps:

| Actor | When to use |
|-------|-------------|
| Chimiste | Canvas App user with Chimiste profile |
| Conditionneur | Canvas App user with Conditionneur profile |
| Administrateur | Canvas App user with Administrateur profile |
| System | Automated action (formula, flow, business rule) |
| Tester | Human tester performing a configuration or verification check |
| Power Automate | Scheduled flow execution |

---

## Phase 6 — Coverage Validation

### Objective

Ensure every rule in the TM has exactly one test case.

### Validation rules

* Count of TCs must equal count of rules in the TM.
* Every rule ID from the TM must appear exactly once as a TC Rule field.
* No TC may reference an ID not present in the TM.
* All TC-NNN identifiers must be sequential with no gaps.

### Blocking condition

```text
STATUS: BLOCKED — Coverage gap: <N> rule(s) without a test case: <list of IDs>
```

---

## Phase 7 — Output Structure

### Objective

Assemble the complete test specification book document.

### Document Structure

```markdown
# Cahier de Recette — <Specification title>

## Header
(specification reference, version, date, scope, contact)

## Coverage Summary
(two tables: rules covered by suite, PENDING items)

## Test Suite 1 — Régression v1
### Domain A: ...
### Domain B: ...
(all TCs grouped by domain)

## Test Suite 2 — Nouvelles fonctionnalités
(empty for v1-only specifications; include section with explicit "no v2-added rules" note)

## Sign-off
(table for human tester sign-off per domain)
```

### Coverage Summary format

Table 1 — Rule coverage:

```markdown
| Rule ID | Type | Domain | TC | Priority | Status |
|---------|------|--------|-----|----------|--------|
| BR-001  | Business Rule | ... | TC-NNN | HIGH | OPEN |
```

Table 2 — PENDING items (if any):

```markdown
| Rule ID | TC | Status | Pending input |
|---------|----|--------|---------------|
| C-008 | TC-NNN | PENDING_PO_INPUT | Spécifique format — contact: ROBINAULT Jean-Luc |
```

---

## Phase 8 — Bilingual Generation

### Objective

Generate the test case book in both languages per `docs/conventions/bilingual_output.md`.

### Procedure

**Step 8.1 — Determine primary language**

Read the source document language from the workspace registry (`runtime/workspaces.md`, field `primary_language`). Default: `fr` if not set.

**Step 8.2 — Generate primary-language file**

Produce the full test case document in the primary language:
- All structural labels (field names, section titles, column headers) in the primary language
- All content (rule text, test steps, descriptions) in the primary language
- Technical identifiers unchanged (see `docs/conventions/bilingual_output.md`)

**Step 8.3 — Generate secondary-language file**

Produce the full test case document in the secondary language:
- All structural labels translated
- All narrative content translated
- System-displayed strings: copy verbatim; add translation in parentheses
- Technical identifiers unchanged

### Output location

```text
WORKSPACE_ROOT/output/test-cases/<base>_test_cases_fr.md
WORKSPACE_ROOT/output/test-cases/<base>_test_cases_en.md
```

### Naming

Standard: `<base>_test_cases_fr.md` / `<base>_test_cases_en.md`

For a v2 workspace: `<base>_test_cases_v2_fr.md` / `<base>_test_cases_v2_en.md`

---

## Phase 9 — Traceability Matrix Forward-Link Update

### Objective

Write the `Test Cases` forward-link column in the traceability matrix, establishing a bidirectional trace: `spec rule → test case`.

This resolves AUD-3-002 (absence de forward-link Test Cases dans la TM).

### Actions

**Step 9.1 — Check for existing Test Cases column**

Read the TM file header row. If a `Test Cases` column already exists, overwrite it. If absent, add it as the last column.

**Step 9.2 — Update TM header block**

Add or update the following fields in the TM header:
```text
**Updated:** <date> — ajout colonne Test Cases (<command>)
**Test Cases FR:** output/test-cases/<base>_test_cases_fr.md
**Test Cases EN:** output/test-cases/<base>_test_cases_en.md
```

**Step 9.3 — Populate Test Cases column**

For each TM row, write the TC-NNN identifier assigned to the corresponding rule in the coverage summary. One TC per row (1:1 mapping).

The TM is in `WORKSPACE_ROOT/specifications/stable/<base>_traceability.md`. It is in `stable/` (BASELINED state). Write the Test Cases column in-place — this is an additive, non-breaking update that does not alter the specification status.

**Step 9.4 — Verify**

Verify that every TM row has a `Test Cases` value and that no TC identifier appears twice in the column.

### Blocking condition

TM not writeable → WARNING only; report and continue. The test cases output is the authoritative artifact.

---

---

## Phase 10 — Word Export (pandoc)

### Objective

Convert the two bilingual test case Markdown files to Word (.docx) for stakeholder delivery.

### Pre-check

Run `pandoc --version`. If Pandoc exits non-zero: emit WARNING and skip Phase 10. The Markdown files are the authoritative output; DOCX is supplementary.

### Actions

For each of the two test case files:

```bash
pandoc "WORKSPACE_ROOT/output/test-cases/<base>_test_cases_<lang>.md" \
  -f markdown-tex_math_dollars \
  -t docx \
  --reference-doc="templates/word/csr_view_reference.docx" \
  -o "WORKSPACE_ROOT/output/test-cases/<base>_test_cases_<lang>.docx"
```

The `-f markdown-tex_math_dollars` flag disables the `tex_math_dollars` Pandoc extension, preventing `$ControlName` identifiers (Power Apps / Dataverse notation) from being misinterpreted as TeX math delimiters.

If `templates/word/csr_view_reference.docx` is absent: omit `--reference-doc` and emit WARNING.

### Validation

- Output DOCX must exist and be non-empty.
- If a conversion fails: emit WARNING for that file; continue with the other.

### Completion states

| Condition | Status |
|-----------|--------|
| Both DOCX generated | TC-DOCX COMPLETE |
| One DOCX generated | TC-DOCX PARTIAL |
| Pandoc absent | TC-DOCX SKIPPED |
| Both conversions failed | TC-DOCX FAILED |

---

## Completion Criteria

Execution is complete when:

* all rules from the TM are covered (one TC each);
* TC-NNN identifiers are sequential without gaps;
* all PENDING statuses are justified with a note;
* bilingual test case files written to `WORKSPACE_ROOT/output/test-cases/`;
* bilingual DOCX files written to `WORKSPACE_ROOT/output/test-cases/` (TC-DOCX COMPLETE or SKIPPED if Pandoc absent);
* the TM `Test Cases` column populated for all rows;
* coverage summary matches the TM.
