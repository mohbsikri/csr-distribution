# Export Views Prompt Template — HTML output

You are executing the Cognitive Specification Runtime view export stage.

Your objective is to convert human-facing Markdown view artifacts into self-contained HTML files using Pandoc, then assemble them using the CSR HTML template with the workspace theme. Output is routed to `output/drafts/` (DRAFT mode) or `output/deliverables/` (BASELINED mode) based on the specification lifecycle state.

---

## Core principles

- Partial is acceptable: if some views are missing, export those that exist and report the rest as BLOCKED_VIEW.
- Agent IA is always excluded: never export `_view_agent_*.md`. It remains Markdown.
- Markdown is never modified: `.md` source files are read-only.
- Per-view independence: a failure on one view does not stop the others.
- Self-contained output folder: copy `mermaid.min.js` to the output directory so every HTML file's `<script src="mermaid.min.js">` resolves offline.
- Draft banner: all DRAFT mode files receive the orange banner; BASELINED files receive none.

---

## Phase 1 — Base, lifecycle state, and source resolution

### Step 1a — Determine `<base>` and `spec_status`

Read `WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md` (if present). Select the target base and extract the spec lifecycle status.

Fallback: read YAML frontmatter `status:` from the canonical spec file.

If `spec_status` is CANCELLED or ARCHIVED: stop — export not permitted.

### Step 1b — Determine export mode

| Condition | export_mode | output_dir | file_suffix |
|-----------|-------------|------------|-------------|
| `--draft` flag | DRAFT | `output/drafts/` | `_draft.html` |
| `spec_status` = BASELINED, EVOLVE_BASELINED, or BASELINED_WITH_CAVEAT | BASELINED | `output/deliverables/` | `.html` |
| `spec_status` = DRAFT, CANDIDATE, REOPEN, or EVOLVE | DRAFT | `output/drafts/` | `_draft.html` |

Draft banner HTML (DRAFT mode only):

```html
<div class="draft-banner">⚠ DRAFT — Ce document n'est pas encore validé et n'a pas de valeur contractuelle. / This document is not yet baselined and has no contractual value. — Généré le {{GENERATED_DATE}}</div>
```

When BASELINED: `banner_html = ""`.

### Step 1c — Build eight source paths

```text
WORKSPACE_ROOT/specifications/views/<base>_specification_fonctionnelle_fr.md
WORKSPACE_ROOT/specifications/views/<base>_functional_specification_en.md
WORKSPACE_ROOT/specifications/views/<base>_dossier_architecture_fr.md
WORKSPACE_ROOT/specifications/views/<base>_technical_architecture_en.md
WORKSPACE_ROOT/specifications/views/<base>_specification_technique_fr.md
WORKSPACE_ROOT/specifications/views/<base>_technical_specification_en.md
WORKSPACE_ROOT/specifications/views/<base>_plan_tests_fr.md
WORKSPACE_ROOT/specifications/views/<base>_test_plan_en.md
```

Check each for existence. Record FOUND or BLOCKED_VIEW.

---

## Phase 2 — Pandoc availability

Run `pandoc --version`. If not found: BLOCKED — stop.

The pandoc conversion parses Markdown tables, lists, and paragraphs into HTML. Mermaid code blocks are handled by the post-processing init script in the template; pandoc does not need any Lua filter.

---

## Phase 3 — Template and theme loading

### 3a — HTML template

Read `${CLAUDE_PLUGIN_ROOT}/templates/html/base_template.html`. This is the HTML shell. It contains these placeholders:

```text
{{THEME_CSS}}           ← replaced with theme CSS content
{{BASE_CSS}}            ← replaced with base.css content
{{LANG}}                ← fr or en
{{TITLE}}               ← document professional name
{{WORKSPACE_ID}}        ← active workspace ID
{{DOCUMENT_TYPE_CODE}}  ← sf, dat, std, or qa
{{CSR_VERSION}}         ← CSR version string
{{DRAFT_BANNER}}        ← banner HTML (DRAFT mode) or empty string (BASELINED)
{{CONTENT}}             ← pandoc HTML fragment
```

### 3b — Base CSS

Read `${CLAUDE_PLUGIN_ROOT}/templates/html/base.css`. This is the structural stylesheet content (includes `.draft-banner` styles).

### 3c — Theme CSS

Look for the workspace theme in this order:

1. `workspaces/<workspace_id>/theme.css` — workspace-specific theme (created by /configure-theme)
2. `${CLAUDE_PLUGIN_ROOT}/templates/html/themes/default.css` — CSR default theme

Read whichever is found first. Record which was used in the export report.

If neither exists: BLOCKED — cannot export without CSS theme.

---

## Phase 4 — Setup

### 4a — Output directory

Create:

```text
DRAFT mode:     WORKSPACE_ROOT/output/drafts/
BASELINED mode: WORKSPACE_ROOT/output/deliverables/
```

### 4b — Draft supersession (BASELINED mode only)

Scan `WORKSPACE_ROOT/output/drafts/` for `<base>_*_draft.html` files. If found: move them to `WORKSPACE_ROOT/output/drafts/archive/<baseline_date>/`. Emit `SUPERSESSION:` event.

### 4c — Mermaid.js copy

Copy `${CLAUDE_PLUGIN_ROOT}/templates/html/mermaid.min.js` to the output directory.

If source absent: emit WARNING and proceed.

Skip copy if target already exists and has the same size (no-op).

---

## Phase 5 — HTML conversion loop

For each FOUND source view:

### Step 5a — Pandoc Markdown → HTML body

Run pandoc to convert the Markdown to an HTML fragment:

```bash
pandoc "<source.md>" \
  -f "markdown+raw_html-yaml_metadata_block-tex_math_dollars" \
  -t html5 \
  --syntax-highlighting=none \
  -o "<output_dir>/<source>_body.html"
```

The `-f markdown+raw_html` flag ensures raw HTML blocks in the Markdown (cover pages, [GAP] blocks) are passed through unchanged.

`-yaml_metadata_block` disabled: prevents YAML parse errors on view file headers.

`-tex_math_dollars` disabled: prevents `$Variable` tokens from being interpreted as TeX math.

`--syntax-highlighting=none`: prevents pandoc highlight CSS from conflicting with template styles.

### Step 5b — Determine document metadata

| Placeholder | Source |
|-------------|--------|
| `{{LANG}}` | `fr` if filename ends `_fr.md`, else `en` |
| `{{TITLE}}` | Value of `**Document type:**` field in header |
| `{{DOCUMENT_TYPE_CODE}}` | View code per table below |
| `{{WORKSPACE_ID}}` | Active workspace ID |
| `{{CSR_VERSION}}` | From `${CLAUDE_PLUGIN_ROOT}/docs/implementation_status.md ## Current Version` |
| `{{GENERATED_DATE}}` | Current date in ISO format (YYYY-MM-DD) |

View code mapping:

| Filename suffix | DOCUMENT_TYPE_CODE |
|----------------|-------------------|
| `_specification_fonctionnelle_fr` | sf |
| `_functional_specification_en` | sf |
| `_dossier_architecture_fr` | dat |
| `_technical_architecture_en` | dat |
| `_specification_technique_fr` | std |
| `_technical_specification_en` | std |
| `_plan_tests_fr` | qa |
| `_test_plan_en` | qa |

### Step 5c — Assemble HTML

Build the final HTML by replacing template placeholders in order:

1. Replace `{{THEME_CSS}}` with theme CSS content
2. Replace `{{BASE_CSS}}` with base CSS content
3. Replace `{{LANG}}` with language code
4. Replace `{{TITLE}}` with document professional name
5. Replace `{{WORKSPACE_ID}}` with workspace ID
6. Replace `{{DOCUMENT_TYPE_CODE}}` with view code
7. Replace `{{CSR_VERSION}}` with CSR version
8. Replace `{{GENERATED_DATE}}` within `banner_html`, then replace `{{DRAFT_BANNER}}` with the populated `banner_html` (or empty string)
9. Replace `{{CONTENT}}` with the pandoc HTML fragment

### Step 5d — Write output file

**DRAFT mode:**

```text
WORKSPACE_ROOT/output/drafts/<output_base>_draft.html
```

**BASELINED mode:**

```text
WORKSPACE_ROOT/output/deliverables/<output_base>.html
```

Output base mapping:

| Source suffix | Output base |
|--------------|-------------|
| `_specification_fonctionnelle_fr.md` | `<base>_specification_fonctionnelle_fr` |
| `_functional_specification_en.md` | `<base>_functional_specification_en` |
| `_dossier_architecture_fr.md` | `<base>_dossier_architecture_fr` |
| `_technical_architecture_en.md` | `<base>_technical_architecture_en` |
| `_specification_technique_fr.md` | `<base>_specification_technique_fr` |
| `_technical_specification_en.md` | `<base>_technical_specification_en` |
| `_plan_tests_fr.md` | `<base>_plan_tests_fr` |
| `_test_plan_en.md` | `<base>_test_plan_en` |

Delete the temporary `_body.html` fragment after assembly.

Verify the output HTML exists and is non-empty.

---

## Phase 6 — Completion report

```text
STATUS: EXPORT-VIEWS COMPLETE | PARTIAL | BLOCKED
Base: <base>
Workspace: <workspace_id>
Export mode: DRAFT | BASELINED
Spec status: <spec_status>
Draft banner: ACTIVE | NONE
Supersession: <N files archived> | NONE
Theme: <workspace-specific | default>
Pandoc: <version>

HTML files generated:
  ✓ <base>_specification_fonctionnelle_fr[_draft].html
  ✓ <base>_functional_specification_en[_draft].html
  ✓ <base>_dossier_architecture_fr[_draft].html
  ✓ <base>_technical_architecture_en[_draft].html
  ✓ <base>_specification_technique_fr[_draft].html
  ✓ <base>_technical_specification_en[_draft].html
  ✓ <base>_plan_tests_fr[_draft].html
  ✓ <base>_test_plan_en[_draft].html

  ✗ <base>_plan_tests_fr.md   — source not found (BLOCKED_VIEW)

Assets:
  ✓ output/<drafts|deliverables>/mermaid.min.js

Output folder: WORKSPACE_ROOT/output/<drafts|deliverables>/
Note: Folder is self-contained — open any .html file in a browser. Mermaid diagrams render offline.
```

---

## Status computation

| Condition | Status |
|-----------|--------|
| All FOUND views converted successfully | EXPORT-VIEWS COMPLETE |
| At least 1 FOUND view failed OR at least 1 BLOCKED_VIEW | EXPORT-VIEWS PARTIAL |
| Pandoc absent OR no views found at all | EXPORT-VIEWS BLOCKED |
