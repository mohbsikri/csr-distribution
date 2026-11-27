# /validate-specification — Execution Specification

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
STATUS: VALIDATE BLOCKED — <reason>
```

---

## Phase 2 — Specification Location

### Step 2.1 — Resolve `<base>`

If `<base>` was provided as an argument: use it directly. Proceed to Step 2.2.

If `<base>` was not provided:

1. Scan `WORKSPACE_ROOT/specifications/draft/` for files matching `*_specification.md`.
2. Scan `WORKSPACE_ROOT/specifications/stable/` for files matching `*_specification.md`.
3. Combine both result sets (exclude `specifications_report.md` if present).
4. Apply:

| Outcome | Action |
|---------|--------|
| Exactly 1 file found | Extract `<base>` from the filename (strip `_specification.md` suffix). Proceed to Step 2.2. |
| 0 files found | `STATUS: VALIDATE BLOCKED — no specification found` |
| More than 1 file found | `STATUS: VALIDATE BLOCKED — multiple candidates; specify <base>` |

### Step 2.2 — Locate Specification File

Check paths in priority order:

1. `WORKSPACE_ROOT/specifications/draft/<base>_specification.md` → if found: `spec_status = DRAFT`
2. `WORKSPACE_ROOT/specifications/stable/<base>_specification.md` → if found: `spec_status = BASELINED`

If neither path exists:

```text
STATUS: VALIDATE BLOCKED — no specification found for <base>
```

Stop.

Record `spec_path` (the workspace-relative path of the found file) and `spec_status`.

---

## Phase 3 — Knowledge Artifact Resolution

### Step 3.1 — Read Generation Log

Read:

```text
WORKSPACE_ROOT/specifications/draft/specifications_report.md
```

If absent:

```text
STATUS: VALIDATE BLOCKED — generation log not found
```

Stop.

### Step 3.2 — Locate `<base>` Row

Parse the Generation Records table. Locate the row where the base name matches `<base>`.

If no matching row is found:

```text
STATUS: VALIDATE BLOCKED — <base> not found in generation log
```

Stop.

### Step 3.3 — Read Source Artifact Field

Extract the `Source Artifact` field value from the `<base>` row. This is a workspace-relative path.

### Step 3.4 — Verify Artifact Exists

Verify that `WORKSPACE_ROOT/<source_artifact>` exists as a readable file.

If absent:

```text
STATUS: VALIDATE BLOCKED — knowledge artifact not found: <path>
```

Stop.

Record `knowledge_path` (the workspace-relative path of the knowledge artifact).

---

## Phase 4 — Parse Knowledge Artifact

Read the full content of `knowledge_path`.

### Business Rules

Scan every line for pattern `\*\*BR-\d{3}[:\*]`. Extract each unique BR ID of the form `BR-NNN`. For each matched BR ID, extract the first 80 characters of the rule text (the text following the BR-NNN marker on the same line) as the excerpt.

Build set `knowledge_br`: map of `{ BR-NNN → excerpt }`.

### Technical Rules

Same logic with pattern `\*\*TR-\d{3}[:\*]`. Extract unique TR-NNN IDs and 80-character excerpts.

Build set `knowledge_tr`: map of `{ TR-NNN → excerpt }`.

### Terms

Locate the section whose heading is `# Terminology` or `# Terms`. Extract all term names within that section until the next `#`-level heading.

Accept any of these formats:

- `**<term>**` on its own line (or at the start of a definition line)
- `- **<term>**:` (bulleted definition)
- `| <term> |` (table row — first cell)

Extract the term name (the text between the bold markers or in the first table cell), stripped of leading/trailing whitespace.

Build set `knowledge_terms`: list of term name strings.

### Workflows

Locate the section whose heading is `# Workflows`. Extract all named workflow entries within that section until the next `#`-level heading.

Accept any of these formats:

- `## <name>` or `### <name>` sub-headings
- Lines of the form `**<name>**` where the name contains an action verb or the word "Workflow"

Extract the name only.

Build set `knowledge_workflows`: list of workflow name strings.

---

## Phase 5 — Parse Specification

Read the full content of `spec_path`.

Partition content into two zones:

- **Header:** everything above (and not including) the first `---` separator line.
- **Body:** everything below the first `---` separator line.

All parsing in this phase operates on the **body** only.

### `spec_br`

Scan body for pattern `BR-\d{3}`. Extract each unique BR ID string found.

Build set `spec_br`: set of BR-NNN strings.

### `spec_tr`

Scan body for pattern `TR-\d{3}`. Extract each unique TR-NNN string found.

Build set `spec_tr`: set of TR-NNN strings.

### `spec_text`

Convert the full body to lowercase. Store as `spec_text`.

### `spec_terms`

Tokenise `spec_text` into individual words (split on whitespace and punctuation). Build set of unique tokens with length > 3.

Build set `spec_terms`: set of lowercase word tokens.

---

## Phase 6 — Compute Coverage

### Business Rules Coverage

If `|knowledge_br| == 0`:
- `coverage_br = 100%`
- `missing_br = []`

Else:
- `missing_br` = IDs present in `knowledge_br` but absent from `spec_br`
- `found_br = |knowledge_br| - |missing_br|`
- `coverage_br = found_br / |knowledge_br| * 100` (rounded to 1 decimal place)

### Technical Rules Coverage

Same logic using `knowledge_tr` and `spec_tr`.

- `missing_tr` = IDs in `knowledge_tr` absent from `spec_tr`
- `coverage_tr` computed identically.

### Terms Coverage

If `|knowledge_terms| == 0`:
- `coverage_terms = 100%`
- `missing_terms = []`

Else: for each term in `knowledge_terms`:
- Normalise term to lowercase.
- Check if the lowercase term appears as a substring in `spec_text`.
- If found: counted as present. If not found: add to `missing_terms`.
- `coverage_terms = (found_terms / |knowledge_terms|) * 100` (rounded to 1 decimal place).

### Workflows Coverage

If `|knowledge_workflows| == 0`:
- `coverage_workflows = 100%`
- `missing_workflows = []`

Else: for each workflow name in `knowledge_workflows`:
- Normalise name to lowercase.
- Check if the lowercase name appears as a substring in `spec_text`.
- If found: counted as present. If not found: add to `missing_workflows`.
- `coverage_workflows = (found_workflows / |knowledge_workflows|) * 100` (rounded to 1 decimal place).

### Overall Coverage

```text
overall_coverage = (coverage_br + coverage_tr + coverage_terms + coverage_workflows) / 4
```

Rounded to 1 decimal place.

---

## Phase 7 — Assemble Report

Construct the coverage report following the format defined in `docs/commands/validate-specification.md` (section "Coverage Report Format").

### Summary Table

For each dimension where `|knowledge_<dim>| == 0`: output `N/A` in the Coverage cell and `—` in the Missing cell.

For dimensions with at least one knowledge item: output computed values.

### Missing Items Section

If `overall_coverage == 100%` and all `missing_*` lists are empty:

- Omit the `## Missing Items` section entirely.
- In its place: write the line `All items covered.`

Otherwise: include `## Missing Items` with one sub-section per dimension that has missing items.

- Business Rules: list each missing BR-ID with its knowledge excerpt: `- BR-NNN: <excerpt>`
- Technical Rules: list each missing TR-NNN with its knowledge excerpt: `- TR-NNN: <excerpt>`
- Terms: list each missing term name: `- <term>`
- Workflows: list each missing workflow name: `- <workflow name>`

Omit any sub-section for a dimension with no missing items.

### Notes Section

Record any of the following if they occurred during parsing:

- A knowledge section (`# Terminology`, `# Terms`, `# Workflows`) was absent — note which section was not found.
- No BR or TR patterns were found in the knowledge artifact.
- Ambiguous term matches (e.g., short term names that match many words) — note the terms affected.

If no notable parsing issues: write `None`.

---

## Phase 8 — Write Report

### Step 8.1 — Create Output Directory

Verify `WORKSPACE_ROOT/output/validation/` exists. If absent: create it.

If directory creation fails:

```text
STATUS: VALIDATE BLOCKED — output/validation/ directory could not be created
```

Stop.

### Step 8.2 — Write Report File

Filename:

```text
<base>_spec_validation_<date>.md
```

Where `<date>` = today's date in `YYYY-MM-DD` format.

Write the assembled report to:

```text
WORKSPACE_ROOT/output/validation/<base>_spec_validation_<date>.md
```

Verify the file exists at the declared path and is non-empty after write.

If write fails or file is absent after write:

```text
STATUS: VALIDATE BLOCKED — coverage report write failed: output/validation/<filename>
```

Stop.

Record `output_path = output/validation/<filename>`.

---

## Phase 9 — Validation Rules SV1–SV6

Apply each validation rule after the report is written.

| Rule | Check | Class | On Failure |
|------|-------|-------|-----------|
| SV1 | Coverage report exists at `WORKSPACE_ROOT/output/validation/<filename>` and is readable | BLOCKING | `STATUS: VALIDATE BLOCKED — SV1: report not readable after write` |
| SV2 | All four dimensions (Business Rules, Technical Rules, Terms, Workflows) are present in the Summary table | BLOCKING | `STATUS: VALIDATE BLOCKED — SV2: dimension missing from Summary table` |
| SV3 | No write operation targeted any path outside `WORKSPACE_ROOT/output/validation/` | BLOCKING | `STATUS: VALIDATE BLOCKED — SV3: write operation outside WORKSPACE_ROOT/output/validation/` |
| SV4 | Specification artifact at `spec_path` was not modified during execution | BLOCKING | `STATUS: VALIDATE BLOCKED — SV4: specification artifact was modified` |
| SV5 | Knowledge artifact at `knowledge_path` was not modified during execution | BLOCKING | `STATUS: VALIDATE BLOCKED — SV5: knowledge artifact was modified` |
| SV6 | Report `<base>` field and `<spec_path>` field match the actual files read in Phases 2–3 | WARNING | Emit warning in Notes section of report — do not stop |

On any BLOCKING rule failure: stop immediately. Do not proceed to Phase 10.

---

## Phase 10 — Completion Report

```text
STATUS: VALIDATE COMPLETE

Specification: <spec_path> (<spec_status>)
Knowledge: <knowledge_path>
Output: output/validation/<filename>

Coverage summary:
  Business Rules:  N%  (<found> / <total> — <missing> missing)
  Technical Rules: N%  (<found> / <total> — <missing> missing)
  Terms:           N%  (<found> / <total> — <missing> missing)
  Workflows:       N%  (<found> / <total> — <missing> missing)
  Overall:         N%
```

Where:
- For dimensions with `|knowledge_<dim>| == 0`: show `N/A  (0 / 0 — 0 missing)`.
- `<found>` = count of knowledge items matched in the specification.
- `<total>` = count of knowledge items extracted from the knowledge artifact.
- `<missing>` = count of knowledge items not matched.
