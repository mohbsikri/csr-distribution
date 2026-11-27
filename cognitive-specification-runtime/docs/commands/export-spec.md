# /export-spec

## Purpose

Export a canonical BASELINED specification as a structured JSON or YAML document. The exported file is a machine-readable, system-agnostic representation of the specification that can feed downstream pipelines, diff tools, or external consumers.

This command is non-interactive, read-only with respect to the specification artifact, and writes only to `output/exports/`. It does not modify any specification, lifecycle registry, or knowledge artifact.

---

## Inputs

```text
/export-spec [<base>] [--format json|yaml]
```

* `<base>` — optional; the specification base name (without `_specification.md` suffix). If omitted: the single BASELINED specification in the active workspace is used automatically. If multiple BASELINED candidates exist and `<base>` is omitted: `STATUS: EXPORT BLOCKED — multiple candidates; specify <base>`.
* `--format` — optional; output format. Accepted values: `json`, `yaml`. Default: `json`.

---

## Target Specification

The command targets:

```text
WORKSPACE_ROOT/specifications/stable/<base>_specification.md
```

The specification must have `**Status:** BASELINED` in its header block. If the file is absent or its status is not BASELINED: `STATUS: EXPORT BLOCKED`.

---

## Outputs

Export file written to:

```text
WORKSPACE_ROOT/output/exports/<base>_export_<date>.json
```

or

```text
WORKSPACE_ROOT/output/exports/<base>_export_<date>.yaml
```

Where `<date>` = today's date in `YYYY-MM-DD` format.

The `output/exports/` directory is created if absent.

---

## Export Schema

The export document has the following top-level structure:

### `meta`

Header-level metadata extracted from the specification header block.

| Field | Source |
|-------|--------|
| `base` | The resolved `<base>` argument |
| `spec_id` | `**Spec ID:**` header field |
| `status` | Always `"BASELINED"` |
| `baseline_date` | `**Baseline Date:**` header field |
| `baselined_by` | `**Baselined By:**` header field |
| `generated` | Today's date in `YYYY-MM-DD` format |
| `format_version` | Always `"1.0"` |

### `sections`

Array of all `##` headings found in the specification body (below the header `---` separator), in document order.

Each entry:

```json
{"heading": "<## Section Title>", "content": "<section body text, trimmed>"}
```

Content is the text between this heading and the next `##` heading, trimmed of leading/trailing whitespace.

### `business_rules`

Array of business rule entries extracted from the Business Rules section.

Each entry:

```json
{"id": "BR-001", "description": "<rule text after **BR-001:** >"}
```

### `technical_rules`

Array of technical rule entries extracted from the Technical Rules section.

Each entry:

```json
{"id": "TR-001", "description": "<rule text after **TR-001:** >"}
```

### `constraints`

Array of constraint entries extracted from the Constraints section.

Each entry:

```json
{"id": "C-001", "description": "<constraint text after **C-001:** >"}
```

### `terms`

Array of term definition entries extracted from the Terms and Definitions section.

Each entry:

```json
{"term": "<term name>", "definition": "<definition text>"}
```

### `workflows`

Array of workflow entries extracted from the Workflows section.

Each entry:

```json
{"name": "<workflow name>", "description": "<workflow description or steps, trimmed>"}
```

---

## Full JSON Structure

```json
{
  "meta": {
    "base": "<base>",
    "spec_id": "<spec_id from **Spec ID:** header field>",
    "status": "BASELINED",
    "baseline_date": "<from **Baseline Date:** header field>",
    "baselined_by": "<from **Baselined By:** header field>",
    "generated": "<ISO date of this export>",
    "format_version": "1.0"
  },
  "sections": [
    {"heading": "<## Section Title>", "content": "<section body text, trimmed>"}
  ],
  "business_rules": [
    {"id": "BR-001", "description": "<rule text after **BR-001:** >"}
  ],
  "technical_rules": [
    {"id": "TR-001", "description": "<rule text after **TR-001:** >"}
  ],
  "constraints": [
    {"id": "C-001", "description": "<constraint text after **C-001:** >"}
  ],
  "terms": [
    {"term": "<term name>", "definition": "<definition text>"}
  ],
  "workflows": [
    {"name": "<workflow name>", "description": "<workflow description or steps, trimmed>"}
  ]
}
```

**YAML format:** same structure rendered as standard YAML. Numbers and strings formatted per standard YAML conventions.

---

## Parsing Rules

### sections

Every `##` heading in the specification body (below the first `---` separator) becomes one entry. Content is the text between this heading and the next `##` heading, trimmed. Sub-headings (`###`, `####`, etc.) are included as part of the section content, not as separate section entries.

### business_rules

Scan the Business Rules section (heading `## Business Rules` or `## N. Business Rules`) for lines matching `**BR-NNN:**`. For each match, extract the ID (`BR-NNN`) and the description (the text following `**BR-NNN:** ` on the same line, trimmed). If the section is absent or no patterns are found: use `[]`.

### technical_rules

Same pattern as business_rules but for `**TR-NNN:**` in the Technical Rules section (`## Technical Rules` or `## N. Technical Rules`). If absent or empty: use `[]`.

### constraints

Same pattern but for `**C-NNN:**` in the Constraints section (`## Constraints` or `## N. Constraints`). If absent or empty: use `[]`.

### terms

Locate the Terms and Definitions section (heading `## Terms and Definitions` or `## N. Terms and Definitions`). Accept any of these formats:

* `**<term>**: <definition>` — inline bold term with colon
* `- **<term>:** <definition>` — bulleted definition
* `**<term>**` on a line followed by `: <definition>` on the next line

Extract the term name (text inside `**...**`) and the definition text (trimmed). If the section is absent or no terms are found: use `[]`.

### workflows

Locate the Workflows section (heading `## Workflows` or `## N. Workflows`). Each named workflow is identified by:

* A `### <name>` sub-heading — name is the heading text; description is the body text of that sub-section, trimmed
* A numbered line of the form `N. <name>` — name is the text after the number; description is the subsequent indented or paragraph text, trimmed

Extract name and description for each workflow. If the section is absent or no workflows are found: use `[]`.

---

## Workspace Resolution

Standard R4a–R4e workspace resolution applies.

```text
W1: Read runtime/current_workspace.md → parse workspace_id
W2: WORKSPACE_ROOT = workspaces/<workspace_id>/
W3: Verify WORKSPACE_ROOT exists → BLOCKED if not found
W4: Validate registry entry in runtime/workspaces.md (R4a–R4e)
W5: All subsequent paths prefixed with WORKSPACE_ROOT
```

---

## Workspace Isolation

This command is **read-only** for all specification, knowledge, and registry artifacts.

The only permitted write operation is:

```text
WORKSPACE_ROOT/output/exports/
```

No specification artifact, lifecycle registry, or knowledge artifact is created or modified. No path outside `output/exports/` is written.

Exceptions (not workspace-scoped, read-only): `runtime/current_workspace.md`, `runtime/workspaces.md`, `docs/`, `.claude/`

---

## Preconditions

1. Active workspace resolves correctly (W1–W5, R4a–R4e).
2. Target specification exists at `WORKSPACE_ROOT/specifications/stable/<base>_specification.md`.
3. Specification header contains `**Status:** BASELINED`.
4. `docs/commands/export-spec.md` and `docs/commands/export-spec_execution.md` exist and are readable.

---

## Validation Rules

| Rule | Check | Class |
|------|-------|-------|
| ES1 | Output file exists at the declared path after execution and is non-empty | BLOCKING |
| ES2 | `meta.base` matches the requested `<base>` | BLOCKING |
| ES3 | `meta.status` equals `"BASELINED"` | BLOCKING |
| ES4 | `sections` array is non-empty (spec must have at least one `##` section) | BLOCKING |
| ES5 | All write operations targeted `output/exports/` only; spec file unmodified; registry unmodified | BLOCKING |
| ES6 | `meta.format_version` equals `"1.0"` | BLOCKING |

---

## Failure Cases

Stop and report `STATUS: EXPORT BLOCKED` when:

* Workspace resolution fails (any of W1–W5, R4a–R4e).
* `<base>` is omitted and multiple BASELINED specifications are found.
* `<base>` is omitted and no BASELINED specification is found.
* Target specification file does not exist at the stable path.
* Specification status is not BASELINED.
* `output/exports/` cannot be created.
* Export file write fails or file is absent after write.
* Any ES1–ES6 BLOCKING rule fails.

---

## Completion Criteria

The command is complete when:

1. The export file exists at the declared output path.
2. The file is non-empty and valid JSON or YAML.
3. All ES1–ES6 validation rules pass.
4. The completion report is emitted.

---

## Completion Reporting

```text
STATUS: EXPORT COMPLETE
Base: <base>
Format: json|yaml
Output: output/exports/<base>_export_<date>.json
Sections exported: N
Business Rules exported: N
Technical Rules exported: N
Constraints exported: N
Terms exported: N
Workflows exported: N
```

```text
STATUS: EXPORT BLOCKED
```
