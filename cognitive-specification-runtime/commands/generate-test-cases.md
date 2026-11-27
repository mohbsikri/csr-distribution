# /generate-test-cases

## Purpose

Generate a test specification book (cahier de recette) from a BASELINED specification.

Each Business Rule, Technical Rule, and Constraint in the specification becomes a traceable test case with preconditions, test steps, expected result, and status.

The output is the primary artifact for functional acceptance testing and sign-off.

---

## Workspace Resolution

Before any file operation, resolve the active workspace:

```text
Step W1: Read runtime/current_workspace.md and parse workspace_id.
         If absent or empty: record resolver_workspace_id as null; skip W2–W3; proceed to W4.
Step W2: Build WORKSPACE_ROOT = workspaces/<workspace_id>/
Step W3: Verify WORKSPACE_ROOT exists. If not found, stop and report:
         STATUS: BLOCKED — Workspace Root Not Found: workspaces/<workspace_id>/
Step W4: Read runtime/workspaces.md. Validate registry (R4a–R4e):
         R4a: workspace_id must be present in registry — BLOCKING if missing.
         R4b: status must not be 'archived' — BLOCKING.
         R4c: runtime_version must be present — WARNING if missing.
         R4d: last_active must be present — WARNING if missing.
         R4e: count status:active entries.
              Case A — Normal: exactly one active entry; its workspace_id = resolver_workspace_id → continue.
              Case B–E: BLOCKING per standard resolver rules.
Step W5: All subsequent paths are prefixed with WORKSPACE_ROOT.
```

## Workspace Isolation

All file operations must target paths prefixed with `WORKSPACE_ROOT`.

Exceptions (not workspace-scoped): `runtime/current_workspace.md`, `runtime/workspaces.md`, `docs/`, `templates/`, `.claude/`, `runtime/id_governance.md`

---

## Preconditions

Before execution:

1. At least one specification with `Status: BASELINED` must exist in:
   ```text
   WORKSPACE_ROOT/specifications/stable/
   ```

2. The traceability matrix must exist:
   ```text
   WORKSPACE_ROOT/specifications/stable/<base>_traceability.md
   ```

3. The ID governance registry must exist:
   ```text
   runtime/id_governance.md
   ```

4. The following artifacts must be available:
   ```text
   ${CLAUDE_PLUGIN_ROOT}/docs/commands/generate-test-cases_execution.md
   ${CLAUDE_PLUGIN_ROOT}/templates/commands/generate_test_cases_prompt.md
   ```

5. Pandoc is recommended for Word export (`pandoc --version`). If absent, Phase 10 is skipped with a WARNING — not blocking.

---

## Execution

### Step 1 — Load Specifications

Read and understand:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/generate-test-cases_execution.md
${CLAUDE_PLUGIN_ROOT}/templates/commands/generate_test_cases_prompt.md
runtime/id_governance.md
```

The repository is the source of truth.

---

### Step 2 — Discover Baselined Specification

Scan `WORKSPACE_ROOT/specifications/stable/` for `*_specification*.md` files with `Status: BASELINED`.

If multiple BASELINED specifications exist, ask the user which one to use.

---

### Step 3 — Load Traceability Matrix

Load the corresponding `*_traceability.md` file to build the complete rule inventory (all BR/TR/C IDs with types and spec sections).

---

### Step 4 — Generate Test Cases

For each rule in the inventory, generate one test case following the format and rules defined in:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/generate-test-cases_execution.md
${CLAUDE_PLUGIN_ROOT}/templates/commands/generate_test_cases_prompt.md
```

---

### Step 5 — Generate Bilingual Output

Generate two language versions following `${CLAUDE_PLUGIN_ROOT}/docs/conventions/bilingual_output.md`:

1. **Primary language** (source document language) → `<base>_test_cases_<lang>.md`
2. **Secondary language** (translated) → `<base>_test_cases_<lang>.md`

For proj-test-01 (French source): FR first, then EN.

Write both files to:

```text
WORKSPACE_ROOT/output/test-cases/<base>_test_cases_fr.md
WORKSPACE_ROOT/output/test-cases/<base>_test_cases_en.md
```

---

## Validation

Before completion verify that:

* every BR/TR/C in the traceability matrix has exactly one test case;
* all TCs carry a TC-NNN identifier (sequential, starting at TC-001);
* all TCs reference the rule ID they cover;
* coverage is 100% (no rule without a TC);
* PENDING_PO_INPUT and PENDING_CLARIFICATION statuses are justified with a note.

---

## Failure Handling

Stop execution and report when:

* no BASELINED specification found;
* traceability matrix cannot be read;
* rule inventory is empty;
* generated coverage is below 100%.

---

## Completion Criteria

Execution is complete when:

* all rules have a corresponding test case;
* both bilingual test case files written to the repository;
* the coverage summary is included in the output document;
* the traceability matrix `Test Cases` column is populated for all rows.

---

## Expected Outputs

```text
WORKSPACE_ROOT/output/test-cases/<base>_test_cases_fr.md
WORKSPACE_ROOT/output/test-cases/<base>_test_cases_en.md
WORKSPACE_ROOT/output/test-cases/<base>_test_cases_fr.docx   ← Phase 10 (pandoc, if available)
WORKSPACE_ROOT/output/test-cases/<base>_test_cases_en.docx   ← Phase 10 (pandoc, if available)
WORKSPACE_ROOT/specifications/stable/<base>_traceability.md   ← Test Cases column added/updated in-place
```

Markdown files are authoritative. DOCX files are supplementary stakeholder deliverables generated by Phase 10. See `${CLAUDE_PLUGIN_ROOT}/docs/conventions/bilingual_output.md`.

The traceability matrix `Test Cases` column is populated as the final step (Phase 9) to establish the forward-link `spec rule → test case`.
