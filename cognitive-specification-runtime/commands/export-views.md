# /export-views

## Purpose

Convert human-facing specification views from Markdown to self-contained HTML for stakeholder delivery.

Output is a self-contained folder with up to eight HTML files and `mermaid.min.js` — works offline, renders diagrams in browser, printable to PDF.

Export mode is determined automatically from the spec lifecycle state:

- **DRAFT mode** (spec status: DRAFT, CANDIDATE, REOPEN, or `--draft` flag): writes to `output/drafts/` with `_draft.html` suffix and an orange draft banner.
- **BASELINED mode** (spec status: BASELINED/EVOLVE_BASELINED): writes to `output/deliverables/` with no suffix and no banner. Archives any existing draft files to `output/drafts/archive/<date>/`.

Requires Pandoc. Install: `winget install pandoc` (Windows) or pandoc.org.

---

## Workspace Resolution

```text
Step W1: Read runtime/current_workspace.md and parse workspace_id.
Step W2: Build WORKSPACE_ROOT = workspaces/<workspace_id>/
Step W3: Verify WORKSPACE_ROOT exists. If not found, stop and report:
         STATUS: BLOCKED — Workspace Root Not Found: workspaces/<workspace_id>/
Step W4: Read runtime/workspaces.md. Validate registry (R4a–R4e).
Step W5: All subsequent paths are prefixed with WORKSPACE_ROOT.
```

---

## Workspace Isolation

All write operations must target one of:

- `WORKSPACE_ROOT/output/drafts/` — DRAFT mode exports
- `WORKSPACE_ROOT/output/deliverables/` — BASELINED mode exports
- `WORKSPACE_ROOT/output/drafts/archive/<date>/` — superseded draft files

Source Markdown files in `WORKSPACE_ROOT/specifications/views/` are read-only.

---

## Flags

| Flag | Effect |
|------|--------|
| `--draft` | Force DRAFT mode regardless of spec lifecycle status |

---

## Preconditions

1. Active workspace resolves correctly (W1–W5, R4a–R4e).
2. Pandoc installed (`pandoc --version` exits 0) — BLOCKING if absent.
3. `${CLAUDE_PLUGIN_ROOT}/templates/html/base_template.html` exists — BLOCKING if absent.
4. `${CLAUDE_PLUGIN_ROOT}/templates/html/base.css` exists — BLOCKING if absent.
5. At least one CSS theme file exists (workspace or default) — BLOCKING if both absent.
6. At least one source view file exists — BLOCKING if none.
7. Spec status is not CANCELLED or ARCHIVED — BLOCKING if either.

---

## Execution

### Step 1 — Load Specification Layers

Read and assimilate:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/export-views.md                   ← L1 contract
${CLAUDE_PLUGIN_ROOT}/docs/commands/export-views_execution.md         ← L2 execution spec
${CLAUDE_PLUGIN_ROOT}/templates/prompts/export_views_prompt.md        ← L3 prompt
```

### Step 2 — Execute Export Runtime

Execute the runtime defined in `${CLAUDE_PLUGIN_ROOT}/docs/commands/export-views_execution.md`:

1. Pandoc availability check (Phase 2) — BLOCKING if absent
2. Base and lifecycle resolution (Phase 3) — determines `<base>` and `spec_status`
3. Export mode resolution (Phase 3.5) — sets `export_mode`, `output_dir`, `file_suffix`, `banner_html`
4. View inventory — eight human-facing views (Phase 4)
5. Mermaid pre-scan (Phase 4.5)
6. Output directory creation (Phase 5)
7. Draft supersession check — BASELINED mode only (Phase 5.5)
8. HTML template + CSS loading (Phase 6)
9. mermaid.min.js copy (Phase 7)
10. HTML conversion loop — pandoc + template assembly per view (Phase 8)
11. Completion report (Phase 9)

---

## Expected Output

**DRAFT mode:**

```text
WORKSPACE_ROOT/output/drafts/<base>_specification_fonctionnelle_fr_draft.html
WORKSPACE_ROOT/output/drafts/<base>_functional_specification_en_draft.html
WORKSPACE_ROOT/output/drafts/<base>_dossier_architecture_fr_draft.html
WORKSPACE_ROOT/output/drafts/<base>_technical_architecture_en_draft.html
WORKSPACE_ROOT/output/drafts/<base>_specification_technique_fr_draft.html
WORKSPACE_ROOT/output/drafts/<base>_technical_specification_en_draft.html
WORKSPACE_ROOT/output/drafts/<base>_plan_tests_fr_draft.html
WORKSPACE_ROOT/output/drafts/<base>_test_plan_en_draft.html
WORKSPACE_ROOT/output/drafts/mermaid.min.js
```

**BASELINED mode:**

```text
WORKSPACE_ROOT/output/deliverables/<base>_specification_fonctionnelle_fr.html
WORKSPACE_ROOT/output/deliverables/<base>_functional_specification_en.html
WORKSPACE_ROOT/output/deliverables/<base>_dossier_architecture_fr.html
WORKSPACE_ROOT/output/deliverables/<base>_technical_architecture_en.html
WORKSPACE_ROOT/output/deliverables/<base>_specification_technique_fr.html
WORKSPACE_ROOT/output/deliverables/<base>_technical_specification_en.html
WORKSPACE_ROOT/output/deliverables/<base>_plan_tests_fr.html
WORKSPACE_ROOT/output/deliverables/<base>_test_plan_en.html
WORKSPACE_ROOT/output/deliverables/mermaid.min.js
```

Only views whose Markdown source exists are exported.

---

## Completion Reporting

```text
STATUS: EXPORT-VIEWS COMPLETE | PARTIAL | BLOCKED
Export mode: DRAFT | BASELINED
Draft banner: ACTIVE | NONE
```
