# /export-spec — Execution Specification

---

## Phase 1 — Workspace Resolution

Identical to all CSR commands: W1 → W5, R4a → R4e.

```text
W1: Read runtime/current_workspace.md → parse workspace_id
W2: WORKSPACE_ROOT = workspaces/<workspace_id>/
W3: Verify WORKSPACE_ROOT exists → BLOCKED if not found
W4: Validate registry entry in runtime/workspaces.md (R4a–R4e)
W5: All subsequent paths prefixed with WORKSPACE_ROOT
```

If workspace resolution fails at any step: stop immediately. Report:

```text
STATUS: EXPORT BLOCKED — <reason>
```

---

## Phase 2 — Specification Location

### Step 2.1 — Resolve `<base>`

If `<base>` was provided as an argument: use it directly. Proceed to Step 2.2.

If `<base>` was not provided:

1. Scan `WORKSPACE_ROOT/specifications/stable/` for files matching `*_specification.md`.
2. For each file found, read its header and check for `**Status:** BASELINED`.
3. Collect all files that are BASELINED.
4. Apply:

| Outcome | Action |
|---------|--------|
| Exactly 1 BASELINED file found | Extract `<base>` from the filename (strip `_specification.md` suffix). Proceed to Step 2.2. |
| 0 BASELINED files found | `STATUS: EXPORT BLOCKED — no BASELINED specification found` |
| More than 1 BASELINED file found | `STATUS: EXPORT BLOCKED — multiple candidates; specify <base>` |

### Step 2.2 — Locate Specification File

Check path:

```text
WORKSPACE_ROOT/specifications/stable/<base>_specification.md
```

If not found:

```text
STATUS: EXPORT BLOCKED — specification not found: specifications/stable/<base>_specification.md
```

Stop.

### Step 2.3 — Verify BASELINED Status

Read the specification file header block (everything above the first `---` separator line).

Locate the line matching `**Status:** BASELINED`.

If absent or the value is not `BASELINED`:

```text
STATUS: EXPORT BLOCKED — specification is not BASELINED: specifications/stable/<base>_specification.md
```

Stop.

Record `spec_path = specifications/stable/<base>_specification.md`.

---

## Phase 3 — Parse Specification Header

Read the full content of `spec_path`.

Partition the content into two zones:

* **Header block:** everything above (and not including) the first `---` separator line.
* **Body:** everything below (and not including) the first `---` separator line.

From the **header block**, extract the following fields by scanning for `**<Field>:** <value>` patterns:

| Field | Pattern | Variable |
|-------|---------|----------|
| Spec ID | `**Spec ID:** <value>` | `meta_spec_id` |
| Status | `**Status:** <value>` | Always `"BASELINED"` (confirmed in Phase 2) |
| Baseline Date | `**Baseline Date:** <value>` | `meta_baseline_date` |
| Baselined By | `**Baselined By:** <value>` | `meta_baselined_by` |

For any field not found in the header: use an empty string `""` as the value. Do not stop.

Set `meta_generated` = today's date in `YYYY-MM-DD` format.
Set `meta_format_version` = `"1.0"`.

---

## Phase 4 — Parse Specification Body

All parsing in this phase operates on the **body** only (below the first `---` separator).

### Step 4.1 — Extract Sections

Scan the body line by line. A section boundary is any line that begins with exactly `## ` (two hash characters followed by a space).

For each `##` heading found:

* Record `heading` as the full heading line text (e.g., `## Business Rules`).
* Record `content` as all lines between this heading line and the next `##` heading (or end of body), joined and trimmed of leading/trailing whitespace.

Build array `parsed_sections`: list of `{heading, content}` objects in document order.

### Step 4.2 — Extract Business Rules

Locate the section whose heading matches `## Business Rules` or `## N. Business Rules` (where N is any number).

Within that section's content, scan every line for the pattern `\*\*BR-\d{3}:\*\*` or `\*\*BR-\d{3}\*\*:`.

For each match:
* Extract `id` = `BR-NNN` (the three-digit identifier).
* Extract `description` = the text following the `**BR-NNN:** ` marker on the same line, trimmed.

Build array `parsed_br`: list of `{id, description}` objects in document order.

If the section is absent or no patterns are found: `parsed_br = []`.

### Step 4.3 — Extract Technical Rules

Same logic as Step 4.2 but for pattern `\*\*TR-\d{3}:\*\*` or `\*\*TR-\d{3}\*\*:` in the Technical Rules section (`## Technical Rules` or `## N. Technical Rules`).

Build array `parsed_tr`: list of `{id, description}` objects in document order.

If absent or empty: `parsed_tr = []`.

### Step 4.4 — Extract Constraints

Same logic but for pattern `\*\*C-\d{3}:\*\*` or `\*\*C-\d{3}\*\*:` in the Constraints section (`## Constraints` or `## N. Constraints`).

Build array `parsed_constraints`: list of `{id, description}` objects in document order.

If absent or empty: `parsed_constraints = []`.

### Step 4.5 — Extract Terms

Locate the section whose heading matches `## Terms and Definitions` or `## N. Terms and Definitions`.

Within that section's content, scan for term entries. Accept any of these formats:

* `**<term>**: <definition>` — bold term with inline definition
* `- **<term>:** <definition>` — bulleted bold term with colon
* `**<term>**` alone on a line followed by the definition (possibly on the next line)

For each match:
* Extract `term` = the text inside `**...**`, stripped of trailing punctuation.
* Extract `definition` = the definition text, trimmed.

Build array `parsed_terms`: list of `{term, definition}` objects in document order.

If the section is absent or no terms are found: `parsed_terms = []`.

### Step 4.6 — Extract Workflows

Locate the section whose heading matches `## Workflows` or `## N. Workflows`.

Within that section's content, scan for workflow entries. Accept any of these formats:

* `### <name>` sub-heading — name is the heading text (without `### `); description is the text of that sub-section until the next `###` or `##` heading, trimmed.
* A numbered line of the form `N. <name>` or `**N. <name>**` — name is the text after the number and period; description is the subsequent paragraph or indented text, trimmed.

Build array `parsed_workflows`: list of `{name, description}` objects in document order.

If the section is absent or no workflows are found: `parsed_workflows = []`.

---

## Phase 5 — Assemble Export Document

Construct the export document using the parsed data from Phases 3 and 4.

### JSON format (default)

Assemble a JSON object with the following structure:

```json
{
  "meta": {
    "base": "<base>",
    "spec_id": "<meta_spec_id>",
    "status": "BASELINED",
    "baseline_date": "<meta_baseline_date>",
    "baselined_by": "<meta_baselined_by>",
    "generated": "<meta_generated>",
    "format_version": "1.0"
  },
  "sections": <parsed_sections>,
  "business_rules": <parsed_br>,
  "technical_rules": <parsed_tr>,
  "constraints": <parsed_constraints>,
  "terms": <parsed_terms>,
  "workflows": <parsed_workflows>
}
```

Format with 2-space indentation. All string values are UTF-8. Arrays that are empty remain as `[]`.

### YAML format (if `--format yaml`)

Render the same structure as standard YAML. Use 2-space indentation. Multi-line string values (e.g., section content) use the literal block scalar style (`|`). Empty arrays render as `[]`.

Store the assembled document as `export_document`.

---

## Phase 6 — Write Output

### Step 6.1 — Create Output Directory

Verify `WORKSPACE_ROOT/output/exports/` exists. If absent: create it.

If directory creation fails:

```text
STATUS: EXPORT BLOCKED — output/exports/ directory could not be created
```

Stop.

### Step 6.2 — Determine Output Filename

```text
<base>_export_<date>.<ext>
```

Where:
* `<date>` = today's date in `YYYY-MM-DD` format.
* `<ext>` = `json` if `--format json` (or default); `yaml` if `--format yaml`.

### Step 6.3 — Write Export File

Write `export_document` to:

```text
WORKSPACE_ROOT/output/exports/<base>_export_<date>.<ext>
```

Verify the file exists at the declared path and is non-empty after write.

If write fails or file is absent after write:

```text
STATUS: EXPORT BLOCKED — export write failed: output/exports/<filename>
```

Stop.

Record `output_path = output/exports/<filename>`.

---

## Phase 7 — Validation Rules ES1–ES6

Apply each validation rule after the export file is written.

| Rule | Check | Class | On Failure |
|------|-------|-------|-----------|
| ES1 | Export file exists at `WORKSPACE_ROOT/output/exports/<filename>` and is non-empty | BLOCKING | `STATUS: EXPORT BLOCKED — ES1: output file not readable after write` |
| ES2 | `meta.base` in the export document equals the resolved `<base>` | BLOCKING | `STATUS: EXPORT BLOCKED — ES2: meta.base mismatch` |
| ES3 | `meta.status` in the export document equals `"BASELINED"` | BLOCKING | `STATUS: EXPORT BLOCKED — ES3: meta.status is not BASELINED` |
| ES4 | `sections` array in the export document is non-empty (at least one entry) | BLOCKING | `STATUS: EXPORT BLOCKED — ES4: sections array is empty` |
| ES5 | All write operations targeted `output/exports/` only; spec file at `spec_path` was not modified; `runtime/workspaces.md` was not modified | BLOCKING | `STATUS: EXPORT BLOCKED — ES5: write isolation violated` |
| ES6 | `meta.format_version` in the export document equals `"1.0"` | BLOCKING | `STATUS: EXPORT BLOCKED — ES6: format_version mismatch` |

On any BLOCKING rule failure: stop immediately. Do not proceed to Phase 8.

---

## Phase 8 — Completion Report

```text
STATUS: EXPORT COMPLETE
Base: <base>
Format: json|yaml
Output: output/exports/<filename>
Sections exported: <count of parsed_sections>
Business Rules exported: <count of parsed_br>
Technical Rules exported: <count of parsed_tr>
Constraints exported: <count of parsed_constraints>
Terms exported: <count of parsed_terms>
Workflows exported: <count of parsed_workflows>
```
