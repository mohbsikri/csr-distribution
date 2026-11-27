# /export-views — Execution Specification

---

## Phase 1 — Workspace Resolution

Standard W1–W5, R4a–R4e. Build `WORKSPACE_ROOT = workspaces/<workspace_id>/`.

---

## Phase 2 — Pandoc Availability Check

Run:

```bash
pandoc --version
```

- If command succeeds: record `pandoc_version` from output line 1. Continue.
- If command not found or exits non-zero: stop immediately with:

```text
STATUS: EXPORT-VIEWS BLOCKED
Reason: Pandoc not installed or not accessible in PATH.
Install: winget install pandoc   (Windows)
         pandoc.org               (all platforms)
```

---

## Phase 3 — Base and Lifecycle Resolution

### Step 3a — Determine target `<base>`

1. If a `<base>` argument was provided: use it.
2. If no argument: read `WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md`.
   - Use the base of the row with the highest-priority active status: `BASELINED` > `CANDIDATE` > `REOPEN` > `DRAFT`.
   - If multiple rows at the same priority: prompt user to specify the target base.
3. If the lifecycle registry is absent: scan `WORKSPACE_ROOT/specifications/views/` for any `<base>_*` view files. If exactly one base found: use it. If multiple: prompt user.
4. If no base can be determined: stop with `STATUS: EXPORT-VIEWS BLOCKED — Cannot determine target spec. Provide <base> as argument.`

### Step 3b — Determine `spec_status`

1. Read `WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md` (if present). Locate the row for `<base>` and extract the `Status:` field value.
2. Fallback (no lifecycle registry or no matching row): read YAML frontmatter `status:` field from `WORKSPACE_ROOT/specifications/<base>.md`.
3. If `spec_status` is `CANCELLED` or `ARCHIVED`: stop with:
   ```text
   STATUS: EXPORT-VIEWS BLOCKED
   Reason: Specification <base> is <CANCELLED|ARCHIVED>. Export not permitted.
   ```
4. If `spec_status` cannot be determined: default to `DRAFT` with WARNING.

### Step 3c — Build eight target source paths

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

---

## Phase 3.5 — Export Mode Resolution

Derive `export_mode`, `output_dir`, and `file_suffix` from spec state:

| Condition | export_mode | output_dir | file_suffix |
|-----------|-------------|------------|-------------|
| `--draft` flag provided | DRAFT | `output/drafts/` | `_draft.html` |
| `spec_status` = BASELINED, EVOLVE_BASELINED, or BASELINED_WITH_CAVEAT | BASELINED | `output/deliverables/` | `.html` |
| `spec_status` = DRAFT, CANDIDATE, REOPEN, or EVOLVE | DRAFT | `output/drafts/` | `_draft.html` |

Draft banner HTML template (injected when `export_mode = DRAFT`):

```html
<div class="draft-banner">⚠ DRAFT — Ce document n'est pas encore validé et n'a pas de valeur contractuelle. / This document is not yet baselined and has no contractual value. — Généré le {{GENERATED_DATE}}</div>
```

When `export_mode = BASELINED`: `banner_html = ""` (empty string — placeholder is removed).

---

## Phase 4 — View Inventory

For each of the eight source paths, plus the two cahier-de-recette paths (`output/test-cases/<base>_test_cases_fr.md`, `output/test-cases/<base>_test_cases_en.md`) `[C2c, 2026-11-01]`: check existence.

Record each path as `FOUND` or `BLOCKED_VIEW`. The two test-cases paths follow the identical FOUND/BLOCKED_VIEW accounting and feed the same Phase 8 conversion loop and Phase 9 report as the other eight — nothing about Phases 5 through 9 is specific to the three human-facing view types; they operate on whatever Markdown source paths Phase 4 found. `/generate-test-cases` not having run yet is not an error here, same as a view never having been generated: it is simply `BLOCKED_VIEW`, surfaced in Phase 9's report like any other.

If all ten paths are `BLOCKED_VIEW`: stop with:

```text
STATUS: EXPORT-VIEWS BLOCKED
Reason: No human-facing views found for base <base>.
Action: Run /generate-views to produce the view artifacts first.
```

---

## Phase 4.5 — Mermaid Pre-Scan (non-blocking)

For each `FOUND` source view file, scan all Mermaid code blocks (content between ` ```mermaid ` and ` ``` `) for known rendering anti-patterns. Emit a `MRM-WARN` event for each match. Continue the export regardless — warnings do not block conversion.

### Anti-patterns to detect

| Pattern ID | Regex / detection | Description | Fix |
|------------|-------------------|-------------|-----|
| MRM-001 | `^  participant .+ as [^"][^\n]*[()$]` | sequenceDiagram: participant alias with `(`, `)` or `$` — not quoted | Wrap alias in `"..."` |
| MRM-002 | `[→⟹⇒⟶]` inside a mermaid block | Unicode arrow character (non-ASCII) | Replace with ` - ` or ASCII `-->` |
| MRM-003 | `^  [A-Za-z0-9_]+ --> [A-Za-z0-9]*[éàèùâêîôûëïüœçÉÀÈÙÂÊÎÔÛËÏÜŒÇ]` inside `stateDiagram-v2` | Accented character used as state ID (not just label) | Use `state "Libellé" as AsciiId` + reference `AsciiId` |
| MRM-004 | `UpdateContext\(\{` or `\{[A-Za-z]+:` inside a message line (after `:`) | Object literal `{key: val}` in sequenceDiagram message | Replace with plain description |
| MRM-005 | `"[^"]*"` inside a sequenceDiagram message line (after `:`) | Double-quoted string in message text — may cause visual noise (quotes included in rendered output). Note: `participant X as "Label"` declarations are NOT in scope; this anti-pattern only applies to message lines. Partial-quote patterns (`Load "file.json"`) produce a low-severity false positive. | Replace with plain text; ignore if quotes are intentional |

### Warning format

```text
MRM-WARN [MRM-NNN] <view_file>:<line_number> — <description>
  Detected: <matched text excerpt (max 80 chars)>
  Fix: <correction guidance>
```

### Scan output

If no issues detected: emit `MRM-SCAN CLEAN — <N> Mermaid blocks scanned, 0 issues.`

If issues detected: emit all `MRM-WARN` lines, then:
```text
MRM-SCAN: <N> issue(s) found across <M> Mermaid block(s). Export continues — verify rendered output after conversion.
```

---

## Phase 5 — Output Directory

Create the target output directory determined in Phase 3.5:

```text
DRAFT mode:     WORKSPACE_ROOT/output/drafts/
BASELINED mode: WORKSPACE_ROOT/output/deliverables/
```

If creation fails: stop with `STATUS: EXPORT-VIEWS BLOCKED — Cannot create output directory.`

---

## Phase 5.5 — Draft Supersession Check (BASELINED mode only)

Runs only when `export_mode = BASELINED`.

1. Scan `WORKSPACE_ROOT/output/drafts/` for files matching `<base>_*_draft.html`.
2. If none found: skip. Continue.
3. If draft files found:
   - Determine `baseline_date`: read YAML frontmatter `baseline_date:` from `WORKSPACE_ROOT/specifications/<base>.md`, or use current date (ISO: `YYYY-MM-DD`).
   - Create archive directory: `WORKSPACE_ROOT/output/drafts/archive/<baseline_date>/`.
   - Move all matched `<base>_*_draft.html` files to the archive directory.
   - Emit: `SUPERSESSION: <N> draft file(s) archived to output/drafts/archive/<baseline_date>/`

---

## Phase 6 — Load HTML Template and CSS

### 6a — HTML template

Read `templates/html/base_template.html` into memory.

If absent: BLOCKED — stop. The HTML template is required.

### 6b — Base CSS

Read `templates/html/base.css` into memory.

If absent: BLOCKED — stop.

### 6c — Theme CSS resolution (priority order)

1. Check `workspaces/<workspace_id>/theme.css` — workspace-specific theme.
2. If absent: check `templates/html/themes/default.css`.
3. If both absent: BLOCKED — no CSS theme available.

Read the resolved theme file into memory. Record which path was used.

---

## Phase 7 — Mermaid.js Copy

Copy `templates/html/mermaid.min.js` to:

```text
DRAFT mode:     WORKSPACE_ROOT/output/drafts/mermaid.min.js
BASELINED mode: WORKSPACE_ROOT/output/deliverables/mermaid.min.js
```

- If source absent: emit `WARNING: mermaid.min.js not found in templates/html/ — diagram rendering will be broken.` Continue.
- If destination already exists and size matches source: skip (no-op). Continue.
- On copy failure: emit WARNING. Continue.

---

## Phase 8 — HTML Conversion Loop

For each `FOUND` source view:

### Step 8a — Pandoc: Markdown → HTML fragment

**Step 8a-0 — Strip view file header (pre-processing — QW-01):**

The mandatory view file header block (`---` … `---`) must be removed before pandoc conversion. Without stripping, Pandoc's `simple_table` extension interprets the `---…---` structure as a one-column table, rendering all metadata fields as a visible `<table>` before the cover page in every exported HTML document.

Algorithm:
1. Read source view file content as lines.
2. If `lines[0] != "---"`: header absent — skip stripping, use full file content as body.
3. Find index `j` = first line index `> 0` where `lines[j] == "---"` (closing delimiter).
4. Extract `body = lines[j+1:]` (everything after the closing delimiter).
5. Write `body` to a temporary file alongside the original: `WORKSPACE_ROOT/specifications/views/<source>_stripped.md`.
6. Use `<source>_stripped.md` as the pandoc input (step below).
7. After Step 8d completes, delete `<source>_stripped.md`.

If no closing `---` is found (malformed file): use the full file content (defensive fallback).

```bash
pandoc "WORKSPACE_ROOT/specifications/views/<source>_stripped.md" \
  -f "markdown+raw_html-yaml_metadata_block-tex_math_dollars" \
  -t html5 \
  --syntax-highlighting=none \
  -o "WORKSPACE_ROOT/output/<mode_dir>/<source>_body.html"
```

where `<mode_dir>` = `drafts` or `deliverables` per `export_mode`.

`-yaml_metadata_block`: disabled — view files use `**Field:** Value` inside `---` delimiters which is not valid YAML; disabling prevents pandoc YAML parse errors.

`-tex_math_dollars`: disabled — prevents pandoc from interpreting `$ControlName` and `$Variable` tokens in technical content as TeX math delimiters.

`--syntax-highlighting=none`: replaces deprecated `--no-highlight`; prevents pandoc code highlight styles from conflicting with the template CSS.

If pandoc exits non-zero: log `EV-FAIL: <view_name> — <stderr excerpt>`. Record as FAILED. Continue to next view.

### Step 8b — Extract document metadata from Markdown header

Parse the mandatory header block at the top of the source Markdown:

| Header field | Template placeholder |
|--------------|---------------------|
| `**Document type:**` value | `{{TITLE}}` |
| File suffix `_fr` or `_en` | `{{LANG}}` → `fr` or `en` |
| Internal view code (sf/dat/std/qa) | `{{DOCUMENT_TYPE_CODE}}` |

`{{WORKSPACE_ID}}` → active workspace ID.
`{{CSR_VERSION}}` → read from `docs/implementation_status.md ## Current Version`.
`{{GENERATED_DATE}}` → current date in ISO format (`YYYY-MM-DD`).

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

### Step 8c — Assemble HTML

Starting from the `base_template.html` content loaded in Phase 6a:

1. Replace `{{THEME_CSS}}` with theme CSS content (Phase 6c)
2. Replace `{{BASE_CSS}}` with base CSS content (Phase 6b)
3. Replace `{{LANG}}` with language code
4. Replace `{{TITLE}}` with document professional name
5. Replace `{{WORKSPACE_ID}}` with workspace ID
6. Replace `{{DOCUMENT_TYPE_CODE}}` with `sf`, `dat`, `std`, or `qa`
7. Replace `{{CSR_VERSION}}` with CSR version string
8. Replace `{{DRAFT_BANNER}}` with `banner_html` (populated or empty string per Phase 3.5); replace `{{GENERATED_DATE}}` within the banner HTML before injecting
9. Replace `{{SKIP_LINK_LABEL}}` with `Aller au contenu` when the language code is `fr`, `Skip to content` otherwise
10. Replace `{{SUITE_NAV}}` with the suite navigation landmark built in Step 8e, or with an empty string when only one document was written — a navigation bar listing one item is noise
11. Replace `{{CONTENT}}` with the pandoc HTML fragment content

**Every token must be substituted.** An unreplaced `{{…}}` reaches the reader as literal text in the delivered document. `{{SKIP_LINK_LABEL}}` is the one a reader sees first — it is the first focusable element on the page — so a missed substitution is immediately visible.

### Accessibility and theme contract (E1, 2026-11-01)

The exported HTML is a deliverable sent outside the team: it is read on a phone, printed, enlarged, and navigated by keyboard. The following are structural guarantees of `/export-views`, not theme choices, and `/configure-theme` must not be able to remove them:

| Guarantee | Carried by | Why it cannot live in the source Markdown |
|---|---|---|
| Light and dark palettes | `themes/<name>.css` — `prefers-color-scheme` + `[data-theme]` | a palette is a token set, and the tokens live in the theme |
| Print forces the light palette | `base.css` `@media print` | `print-color-adjust: exact` (OUT-RT-05) would otherwise print a dark page for a reader whose system is dark |
| Skip link, `<main id="contenu">` | `base_template.html` | pandoc emits a fragment with no landmarks |
| Tables scroll in an announced, focusable region | runtime DOM pass in `base_template.html` | pandoc emits a bare `<table>`; the wrapper cannot come from Markdown |
| `scope` on header cells | same DOM pass | same reason |
| Reduced motion respected | `base.css` | — |
| Table of contents rebuilt from the headings actually present | runtime DOM pass in `base_template.html` | the TOC in the source is a literal block copied from the L3 prompt — it lists the sections the contract expects, not the ones emitted |

**Table of contents (E2, 2026-11-01).** The exported document rebuilds its TOC from the `h2`/`h3` headings actually present inside `<main>`, replacing the contents of the `.toc` container while keeping its heading. A heading that arrives without an id is given one, so no entry in the rebuilt list can be a dead link.

The rebuild is a repair of the deliverable, **not an excuse for the source**. When the `.toc` container is absent entirely the export does not invent one, because inventing it would hide a generation defect behind a correct-looking document. `tools/csr-check` W7 reports the omission at the view file, where it can be fixed by regeneration.

Why the source TOC cannot be trusted: the L3 prompt tells the generator to emit a *literal* TOC block listing sections SF-03 through SF-13. That list describes what the contract expects, not what the generator actually produced — omit a conditional section such as SF-01b or SF-04b and its entry becomes a dead link; add one and it is missing. Rebuilding from the document makes the list correct by construction.

**A custom theme that redefines only the light tokens stays correct**: it inherits the dark palette shipped with `themes/default.css`. A custom theme that hardcodes a colour instead of a token breaks dark mode for that element — this is why `base.css` holds no hardcoded colour outside `@media print`.

### Step 8e — Write the Suite Index `[E9, 2026-11-01]`

Runs once, after every view has been written. Produces `index.html` in the same output directory.

**Why.** Until now `/export-views` wrote up to eight HTML files into a folder and stopped. There was no entry point: a recipient received a directory listing and had to guess which file to open, and nothing told them the other seven existed or how they related. The unit a reader receives is the **suite**, not a document — but nothing in the runtime represented a suite.

**Content.** Reuse `base_template.html` so the index inherits the theme, the dark palette, the print sheet and the accessibility layer without duplicating any of it. The body is:

1. the workspace description (`workspace_config.md`) as a subtitle, and the logo if `logo_path` is set;
2. one entry per document actually written — professional name, language, and one line saying who it is for, taken from the audience model (ADR-003): business reader, architect, developer, test lead;
3. the suite's state: `BASELINED` with its date, or `DRAFT` with the same warning the draft banner carries;
4. the generation date and the CSR version.

**List only what was written.** A view that was `BLOCKED_VIEW` in Phase 4 has no entry — not a dead link, and not an entry marked unavailable. An index is a map of what the reader has, not a statement about what they do not.

**Cross-navigation.** Each exported document receives the same list through `{{SUITE_NAV}}`, rendered as a navigation landmark at the top. A reader who opens the architecture dossier directly — which is what happens when a link is forwarded by email — can reach the functional specification without going back to a folder they may never have had.

**Both modes.** The index is written for `DRAFT` as for `BASELINED`, into whichever directory the mode selected. A draft suite needs an entry point exactly as much as a baselined one; it is the state that differs, not the need.

### Step 8c-bis — Graphic Charter Reminder, Once `[A2, 2026-11-01]`

If Phase 6c resolved the theme to `templates/html/themes/default.css` (no workspace `theme.css`) **and** this is the first export of this workspace, add one line to the completion report:

> Ces documents utilisent le thème CSR par défaut. Pour les aligner sur votre charte : `/configure-theme EXTRACT <document de référence>`.

Once only, and never when a workspace theme exists. This is the second and last opportunity — the first is Step 7b of `/ingest-source`. A runtime that repeats the same offer teaches the reader to skip what it says.

### Step 8d — Write output HTML

Write to:

```text
DRAFT mode:     WORKSPACE_ROOT/output/drafts/<output_name>_draft.html
BASELINED mode: WORKSPACE_ROOT/output/deliverables/<output_name>.html
```

Output filename base mapping:

| Source Markdown suffix | Output HTML base |
|------------------------|-----------------|
| `_specification_fonctionnelle_fr.md` | `<base>_specification_fonctionnelle_fr` |
| `_functional_specification_en.md` | `<base>_functional_specification_en` |
| `_dossier_architecture_fr.md` | `<base>_dossier_architecture_fr` |
| `_technical_architecture_en.md` | `<base>_technical_architecture_en` |
| `_specification_technique_fr.md` | `<base>_specification_technique_fr` |
| `_technical_specification_en.md` | `<base>_technical_specification_en` |
| `_plan_tests_fr.md` | `<base>_plan_tests_fr` |
| `_test_plan_en.md` | `<base>_test_plan_en` |

Final filename: `<output_html_base>_draft.html` (DRAFT) or `<output_html_base>.html` (BASELINED).

Delete the temporary body fragment (`_body.html`) after assembly.

Verify output HTML exists and is non-empty (> 0 bytes). If empty: log EV-FAIL and record as FAILED.

---

## Phase 9 — Report

Compute result status:

| Condition | Status |
|-----------|--------|
| All FOUND views converted successfully | EXPORT-VIEWS COMPLETE |
| At least 1 FOUND view failed OR at least 1 BLOCKED_VIEW | EXPORT-VIEWS PARTIAL |
| 0 FOUND views (all BLOCKED_VIEW or all FAILED) | EXPORT-VIEWS BLOCKED |

Report template:

```text
STATUS: EXPORT-VIEWS COMPLETE | PARTIAL | BLOCKED
Base: <base>
Workspace: <workspace_id>
Export mode: DRAFT | BASELINED
Spec status: <spec_status>
Pandoc: <version>
Theme: <workspace-specific (workspaces/<id>/theme.css) | default (templates/html/themes/default.css)>
Output format: HTML (self-contained folder)

Draft banner: ACTIVE | NONE
Supersession: <N draft file(s) archived to output/drafts/archive/<date>/> | NONE

Documents exported:
  ✓ <base>_specification_fonctionnelle_fr[_draft].html
  ✓ <base>_functional_specification_en[_draft].html
  ✓ <base>_dossier_architecture_fr[_draft].html
  ✓ <base>_technical_architecture_en[_draft].html
  ✓ <base>_specification_technique_fr[_draft].html
  ✓ <base>_technical_specification_en[_draft].html
  ✓ <base>_plan_tests_fr[_draft].html
  ✓ <base>_test_plan_en[_draft].html

Assets:
  ✓ output/<drafts|deliverables>/mermaid.min.js

Output folder: WORKSPACE_ROOT/output/<drafts|deliverables>/
```

---

## Validation Rules

| ID | Rule | Classification |
|----|------|----------------|
| EV-01 | Pandoc must be available before any conversion begins | BLOCKING |
| EV-02 | At least one source view must exist | BLOCKING |
| EV-03 | Agent IA views must never be included in the export scope | BLOCKING |
| EV-04 | Each output HTML must be non-empty after conversion | BLOCKING (per view) |
| EV-05 | Output path must be within `WORKSPACE_ROOT/output/drafts/` (DRAFT) or `WORKSPACE_ROOT/output/deliverables/` (BASELINED) | BLOCKING |
| EV-06 | HTML template must exist before conversion begins | BLOCKING |
| EV-07 | At least one CSS theme must be resolved before conversion begins | BLOCKING |
| EV-08 | mermaid.min.js copy failure does not block export | WARNING |
| EV-09 | Draft banner HTML must be present in all DRAFT mode outputs; must be absent (empty) in BASELINED mode outputs | BLOCKING (per view) |
| EV-10 | CANCELLED and ARCHIVED specs may not be exported | BLOCKING |
