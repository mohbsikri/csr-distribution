# /diff-specification — Execution Specification

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
STATUS: DIFF BLOCKED — Workspace resolution failed at W<N>: <reason>
```

---

## Phase 2 — Version Resolution

### Step 2.1 — Load Lifecycle Registry

Read:

```text
WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md
```

If the registry file does not exist:

```text
STATUS: DIFF BLOCKED — lifecycle registry not found
```

Stop.

### Step 2.2 — Locate Base in Active State Index

Parse the `## Active State Index` table. Locate the row where `Base = <base>`.

If no row matches:

```text
STATUS: DIFF BLOCKED — <base> not found in lifecycle registry
```

Stop.

### Step 2.3 — Resolve From/To Paths

**If both `--from` and `--to` are provided:**

Use `--from` and `--to` directly as the from-path and to-path. The values are Spec IDs (e.g., `SP001`). Resolve the corresponding file paths from the Event Log and Active State Index.

**If `--to` is not provided:**

`--to` = the `Current Path` of `<base>` where `Status = BASELINED` in the Active State Index.

If the Active State Index entry for `<base>` does not carry `Status = BASELINED`:

```text
STATUS: DIFF BLOCKED — <base> is not currently BASELINED; cannot resolve --to automatically.
Provide --to <spec_id> explicitly or run /specification-lifecycle BASELINE first.
```

Stop.

**If `--from` is not provided:**

Scan the `## Event Log` section for all `Event Type: EVOLVE` records where `Base = <base>`. Select the most recent EVOLVE event (highest Event ID).

Extract `Superseded Artifact` from that EVOLVE event record. This is the from-path.

If no EVOLVE event exists for `<base>`:

```text
STATUS: DIFF BLOCKED — no prior version available for <base>. Only one version exists.
```

Stop.

### Step 2.4 — Verify Artifact Paths Exist on Disk

Verify both resolved paths exist as readable files.

If either path is absent:

```text
STATUS: DIFF BLOCKED — artifact not found: <path>
```

Stop.

Record:
- `from_path`: workspace-relative path of the older version
- `from_spec_id`: Spec ID of the from artifact (from registry or provided)
- `from_status`: lifecycle status of the from artifact (typically SUPERSEDED)
- `to_path`: workspace-relative path of the newer version
- `to_spec_id`: Spec ID of the to artifact (from registry or provided)
- `to_status`: lifecycle status of the to artifact (typically BASELINED)

---

## Phase 3 — Load Specifications

Read both specification files fully.

For each file, partition content into two zones:

**Header section:** everything above (and not including) the first `---` separator line. This includes all `**Field:** value` lines.

**Body section:** everything below the first `---` separator line.

Parse the following header fields from each file:

| Field | Pattern |
|-------|---------|
| Status | `**Status:** <value>` |
| Spec ID | `**Spec ID:** <value>` (or `**Source Artifact:**` if Spec ID absent — use filename as fallback) |
| Baseline Date | `**Baseline Date:** <value>` |
| Baselined By | `**Baselined By:** <value>` |

Record parsed header fields for both `from` and `to` versions.

---

## Phase 4 — Dimension-by-dimension Comparison

Execute comparison across all seven dimensions. Build change sets for each.

### Dimension 1 — Header Fields

Compare the four header fields between from and to:

- Status
- Spec ID
- Baseline Date
- Baselined By

For each field: if the value differs between from and to, record as `changed`.

### Dimension 2 — Sections

Extract all level-2 headings (`## `) from the body of each specification.

Build two sets:
- `from_headings`: ordered list of `## <heading>` strings from the from body
- `to_headings`: ordered list of `## <heading>` strings from the to body

Classify:

- **Added:** heading present in `to_headings` but not in `from_headings`
- **Removed:** heading present in `from_headings` but not in `to_headings`
- **Present in both:** for each shared heading, extract the full content of that section (from the heading line to the next `## ` heading or end of file). Compare character counts. If the absolute character delta exceeds 50: classify as **Modified**. Otherwise: **Unchanged**.

### Dimension 3 — Business Rules

Scan both body sections for occurrences matching the pattern `BR-\d{3}` (e.g., `BR-001`, `BR-123`).

Build two sets:
- `from_br_ids`: set of all BR IDs found in the from body
- `to_br_ids`: set of all BR IDs found in the to body

Classify:

- **Added:** ID present in `to_br_ids` but not `from_br_ids`
- **Removed:** ID present in `from_br_ids` but not `to_br_ids`
- **Modified:** ID present in both sets; extract the full paragraph (or list item block) containing each ID; if the text differs between from and to, classify as modified. Record a short excerpt: first 80 characters of the from text and the to text.

### Dimension 4 — Technical Rules

Same logic as Business Rules, using pattern `TR-\d{3}`.

Build `from_tr_ids` and `to_tr_ids`. Classify added, removed, modified by the same paragraph-comparison approach.

### Dimension 5 — Constraints

Same logic, using pattern `C-\d{3}`.

Build `from_c_ids` and `to_c_ids`. Classify added, removed, modified.

### Dimension 6 — Terms

Scan both body sections for term definitions. A term definition matches either of:

- A bolded term on its own: `**<term>**` on a line, within a section whose heading contains "Term", "Glossaire", "Glossary", or "Définitions"
- A table row in such a section: `| <term> | ...`

Build two sets of term names:
- `from_terms`
- `to_terms`

Classify:

- **Added:** term present in `to_terms` but not `from_terms`. Include the definition text from the to body.
- **Removed:** term present in `from_terms` but not `to_terms`. Include the definition text from the from body.

No "modified" classification for terms: definition changes are captured under the enclosing section's character-delta (Dimension 2).

### Dimension 7 — Data Model

Scan both body sections for table names. A table name is identified by:

- Pattern A: a heading `### <TableName>` inside a section whose heading contains "Data", "Model", "Schema", "Tables", or "Données"
- Pattern B: a table row `| <TableName> | ...` where the row appears to be a table-of-tables listing

Build two sets of table names:
- `from_tables`
- `to_tables`

Classify:

- **Added:** table name present in `to_tables` but not `from_tables`
- **Removed:** table name present in `from_tables` but not `to_tables`

Field-level changes within a table are noted in narrative if detected (no structured field-diff is required; a note is sufficient).

---

## Phase 5 — Assemble Delta Report

Construct the delta report document conforming to the format defined in `docs/commands/diff-specification.md` (section "Delta Report Format").

### Summary Table

Compute totals across all dimensions:

| Dimension | Added | Removed | Modified | Unchanged |
|-----------|-------|---------|----------|-----------|

Note: Terms and Data Model do not produce a "Modified" count; use "—" for that cell.

### Per-Dimension Sections

Include one section per dimension with non-zero changes. Dimensions with all-zero changes still appear in the Summary table but may be omitted from the detailed sections, or shown with a note: `No changes detected.`

Format for each rules dimension (Business Rules, Technical Rules, Constraints):

```markdown
### Added
- BR-NNN: <rule statement (first 120 chars)>

### Removed
- BR-NNN: <rule statement (first 120 chars)>

### Modified
- BR-NNN: content changed
  From: <first 80 chars of from text>
  To:   <first 80 chars of to text>
```

### Report Filename

Construct the output filename:

```text
<base>_diff_<from_spec_id>_vs_<to_spec_id>_<date>.md
```

Where `<date>` = today's date in `YYYY-MM-DD` format.

### Output Directory

Verify `WORKSPACE_ROOT/output/diffs/` exists. If absent: create it.

If directory creation fails:

```text
STATUS: DIFF BLOCKED — output/diffs/ directory could not be created
```

Stop.

---

## Phase 6 — Write Report

Write the assembled delta report to:

```text
WORKSPACE_ROOT/output/diffs/<filename>
```

Verify: file exists at the declared path and is non-empty.

If write fails or the file does not exist after write:

```text
STATUS: DIFF BLOCKED — delta report write failed: output/diffs/<filename>
```

Stop.

Record `output_path = output/diffs/<filename>`.

---

## Phase 7 — Validation Rules DS1–DS6

Apply each validation rule. On any BLOCKING failure: report the rule ID and the specific check that failed. Stop completion reporting.

| Rule | Check | Class |
|------|-------|-------|
| DS1 | Delta report exists at `WORKSPACE_ROOT/output/diffs/<filename>` and is readable | BLOCKING |
| DS2 | Both `from_spec_id` and `to_spec_id` are present in the report header (`**From:**` and `**To:**` fields) | BLOCKING |
| DS3 | Summary table is present and includes all 5 dimensions: Sections, Business Rules, Technical Rules, Constraints, Terms | BLOCKING |
| DS4 | No write operation targeted any path outside `WORKSPACE_ROOT/output/diffs/` | BLOCKING |
| DS5 | The from-path and to-path specification files have the same content as when they were read in Phase 3 (no modification occurred) | BLOCKING |
| DS6 | `WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md` has the same content as when it was read in Phase 2 (no modification occurred) | BLOCKING |

For DS5: re-read both specification files and compare byte-for-byte with the content captured in Phase 3. Any difference is a BLOCKING violation.

For DS6: re-read the lifecycle registry and compare with the content captured in Phase 2. Any difference is a BLOCKING violation.

---

## Phase 8 — Completion Report

```text
STATUS: DIFF COMPLETE

From: <from_spec_id> (<from_path>)
To:   <to_spec_id> (<to_path>)
Output: output/diffs/<filename>

Summary: <N> added, <N> removed, <N> modified across all dimensions.

Validation: DS1 ✓  DS2 ✓  DS3 ✓  DS4 ✓  DS5 ✓  DS6 ✓
```
