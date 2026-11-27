# /preprocess-source — Execution Specification

---

## Phase 1 — Workspace Resolution

Identical to all CSR commands: W1 → W5, R4a → R4e.

Build WORKSPACE_ROOT = workspaces/<workspace_id>/

---

## Phase 2 — Source File Location

Search for the source file in:

```text
WORKSPACE_ROOT/input/documents/
```

If not found: report STATUS: BLOCKED — Source file not found. Stop.

---

## Phase 3 — Source Classification and Routing

### Step 3a — Read format_category from sources.md

Read the source row from `WORKSPACE_ROOT/runtime/sources.md`. Retrieve:
- `format_category` (A / A+ / B / C / D)
- `eligibility_status` (for Category C: PENDING / ELIGIBLE / ELIGIBLE_WITH_WARNING / INELIGIBLE / OVERRIDE)

If the source has no row in sources.md (source not previously ingested), classify by extension — Step 3b.

### Step 3b — Extension-based classification (fallback)

| Extension | format_category | Processing Route |
|-----------|-----------------|-----------------|
| `.pdf` | A | PDF Profile |
| `.md` `.txt` | A | Plain Text Pass-through |
| `.png` `.jpg` `.jpeg` `.gif` `.webp` | A | Image Profile |
| `.docx` | A+ | DOCX Pandoc Profile |
| `.doc` `.rtf` `.ppt` `.pptx` | B | Category B — RT-02 pending |
| `.xlsx` `.csv` `.json` `.yaml` `.yml` `.xml` `.sql` | C | Phase 0 Eligibility required |
| (other) | D | Immediate rejection |

### Step 3c — Category D: immediate rejection

If `format_category = D`:

```
STATUS: BLOCKED — Format not supported.
Source: <source_file>
Extension: <ext>
Category D: no preprocessing path available in the current environment.
Recommended alternative: see ADR-005 Category D table.
  VSDX → Export to PDF or PNG/SVG from Visio
  ODT/ODP → Export to PDF from LibreOffice or Word/PowerPoint
  HTML → Export to PDF via browser
  URL → Export to PDF via browser
  ZIP → Extract files individually and ingest each file
  Audio/Video → Provide a transcript as TXT or MD
```

Stop. No further processing. No event emitted beyond FORMAT_CLASSIFIED (emitted at ingestion).

### Step 3d — Category B: Office COM Conversion

If `format_category = B`:
- Verify Office 365 availability before proceeding — see Phase 5e Step 5e-0.
- Emit CONVERSION_STARTED event.
- Route to Phase 5e — Office COM Conversion Profile.

If Office 365 is unavailable:

```
STATUS: BLOCKED — Office 365 not available.
Source: <source_file>
Extension: <ext>
Category B preprocessing requires Office 365 v16.0 (Word COM for DOC/RTF, PowerPoint COM for PPT/PPTX).
Workaround: export the document manually to PDF, then ingest and preprocess the PDF file.
```

Emit CONVERSION_FAILED event with reason `Office 365 not available`. Stop.

### Step 3e — Category C: route to Phase 0

If `format_category = C`:
- If `eligibility_status = INELIGIBLE`: stop immediately.

```
STATUS: BLOCKED — Source previously rejected.
Source: <source_file>
eligibility_status: INELIGIBLE
Reason: <eligibility_reason from sources.md>
To override: provide explicit written justification and re-run with OVERRIDE mode.
```

- If `eligibility_status = ELIGIBLE` or `ELIGIBLE_WITH_WARNING` or `OVERRIDE`: skip Phase 0, proceed to Phase 4.
- If `eligibility_status = PENDING` (default after /ingest-source for Category C): proceed to Phase 0 (Eligibility Gate).

### Step 3f — Category A and A+: report and route

If `format_category = A`:
- `.pdf` → PDF Profile (Phase 5a)
- `.md` `.txt` → Plain Text Pass-through (Phase 5b)
- `.png` `.jpg` `.jpeg` `.gif` `.webp` → Image Profile (Phase 5c)

If `format_category = A+`:
- `.docx` → DOCX Pandoc Profile (Phase 5d)
- Verify Pandoc: run `pandoc --version`. If not found or exits non-zero, stop:

```
STATUS: BLOCKED — Pandoc not installed.
DOCX preprocessing requires Pandoc.
Install: winget install pandoc   (Windows)
         pandoc.org               (all platforms)
```

Report and proceed:

```
Source: <filename>
Category: <A | A+>
Detected type: <PDF | TXT | IMAGE | DOCX>
Profile to apply: <profile name>
Processing...
```

---

## Phase 0 — Eligibility Gate (Category C only)

Phase 0 applies exclusively to Category C sources with `eligibility_status = PENDING`. It is a mandatory gate — no Category C source enters preprocessing without an eligibility decision.

### Step 0a — Read source for eligibility analysis

Read the source file partially (first 200 rows for tabular formats, first 3,000 characters for others) to evaluate content nature.

Inputs available:
- Source filename and extension
- User context provided at ingestion (from `knowledge_base/raw/<source_name>_registration.md`)
- First 200 rows / 3,000 characters of source content

### Step 0b — Apply signal evaluation hierarchy (ADR-005)

```
Level 1 — Contextual signals (determinant if clear)
    Filename / declared source / requester context
    → Strong OD signal → REJECT immediate
    → Strong KO signal → ACCEPT immediate
    → Ambiguous → Level 2

Level 2 — Structural signals (discriminating)
    Statement types (DDL vs DML), JSON schema structure, CSV headers
    → KO dominant → ACCEPT
    → OD dominant → REJECT
    → Mix or uncertain → ACCEPT_WITH_WARNING

Level 3 — Volume signals (confirmatory, not determinant alone)
    → High volume + OD headers: reinforces REJECT
    → Moderate volume + KO headers: confirms ACCEPT
    → High volume + KO headers: confirms ACCEPT
```

**KO signals (Knowledge-Oriented — accept):**
- Normative text fields: `Description`, `Rule`, `Definition`, `Purpose`, `Condition`, `Action`
- Encoded constraints: conditional formulas, `CHECK CONSTRAINT`, `required`, `enum`, `pattern`, `minLength`
- Normative metadata: `data_type`, `is_required`, `valid_states`, `foreign_key`
- DDL SQL: `CREATE TABLE`, `ALTER TABLE`, `CREATE VIEW`, `FOREIGN KEY`, `CHECK`
- API/schema structure: JSON Schema, YAML config with business parameters

**OD signals (Operational Data — reject):**
- Columns dominated by dates, amounts, quantities, instance identifiers
- Row homogeneity (all structurally identical — transactional signature)
- Volume > 5,000 rows with transactional headers
- Filename containing: `export_`, `orders_`, `sales_`, `log_`, `history_`, `backup_`, date suffix
- Dominant DML SQL: `INSERT INTO`, `UPDATE`, `DELETE` without associated DDL
- Total absence of descriptive or normative fields

### Step 0c — Produce decision

Produce one of three decisions:

**ACCEPT (KO dominant):**
- Proceed without restriction
- `eligibility_status = ELIGIBLE`

**ACCEPT_WITH_WARNING (mixed or ambiguous signals):**
- Present human confirmation request:

```
PHASE 0 — ELIGIBILITY CHECK

Source: <source_file>
Category: C
Decision: ACCEPT_WITH_WARNING

Signals detected:
  KO: <list of KO signals found>
  OD: <list of OD signals found>
  Ambiguity: <description>

Options:
  1. CONFIRM FULL — process the entire file (annotation CAVEAT added to output)
  2. DEFINE SCOPE — restrict processing to a subset:
       XLSX: specify sheet names (e.g., scope=Rules,Config)
       SQL: specify DDL-ONLY to exclude INSERT/UPDATE/DELETE
       JSON/YAML: specify top-level keys (e.g., scope=business_rules,schemas)
       XML: specify element types (e.g., scope=BusinessRules,Entities)
  3. REJECT — do not process this source

Your choice? (CONFIRM FULL / DEFINE SCOPE <scope_value> / REJECT)
```

Wait for user response before proceeding.
- If CONFIRM FULL: `eligibility_status = ELIGIBLE_WITH_WARNING`, `scope = ALL`, `eligibility_human_confirmed = true`
- If DEFINE SCOPE: `eligibility_status = ELIGIBLE_WITH_WARNING`, `scope = <user_value>`, `eligibility_human_confirmed = true`
- If REJECT: `eligibility_status = INELIGIBLE`, `eligibility_human_confirmed = true`

**REJECT (OD dominant):**
- `eligibility_status = INELIGIBLE`
- `eligibility_human_confirmed = false`

### Step 0d — Emit eligibility events

Append to `WORKSPACE_ROOT/runtime/events.md`:

**Always — ELIGIBILITY_EVALUATED:**
```
| <timestamp> | ELIGIBILITY_EVALUATED | source: <source_file>; category: C; signals_ko: <count>; signals_od: <count>; decision: <ACCEPT|ACCEPT_WITH_WARNING|REJECT> |
```

**Then, one of:**
```
| <timestamp> | ELIGIBILITY_ACCEPTED | source: <source_file>; scope: ALL; reason: <summary> |
```
```
| <timestamp> | ELIGIBILITY_ACCEPTED_WITH_WARNING | source: <source_file>; scope: <scope>; human_confirmed: true; reason: <summary> |
```
```
| <timestamp> | ELIGIBILITY_REJECTED | source: <source_file>; reason: <summary>; human_confirmed: <true|false> |
```

**If ACCEPT or ACCEPT_WITH_WARNING — PHASE0_COMPLETED:**
```
| <timestamp> | PHASE0_COMPLETED | source: <source_file>; eligibility_status: <ELIGIBLE|ELIGIBLE_WITH_WARNING>; scope: <scope> |
```

### Step 0e — Update sources.md eligibility fields

Write the following fields to the source's row in `WORKSPACE_ROOT/runtime/sources.md`:

| Field | Value |
|-------|-------|
| `eligibility_status` | `ELIGIBLE` / `ELIGIBLE_WITH_WARNING` / `INELIGIBLE` |
| `eligibility_reason` | Synthetic summary of triggering signals |
| `eligibility_date` | Current timestamp (ISO 8601) |
| `eligibility_human_confirmed` | `true` / `false` |
| `scope` | Scope value or `ALL` |

### Step 0f — Routing after Phase 0

- `ELIGIBLE` or `ELIGIBLE_WITH_WARNING`: proceed to Phase 4.
- `INELIGIBLE`: stop. Report:

```
STATUS: BLOCKED — Source rejected by Phase 0 Eligibility Check.
Source: <source_file>
Decision: INELIGIBLE
Reason: <eligibility_reason>
eligibility_status written to sources.md.
ELIGIBILITY_REJECTED event recorded in runtime/events.md.
```

---

## Phase 4 — Preprocessed Directory

Verify or create:

```text
WORKSPACE_ROOT/knowledge_base/preprocessed/
```

---

## Phase 5 — Apply Profile

### Phase 5a — PDF Profile

1. Read the PDF file using multimodal capability.
2. Process each page in sequence.
3. For each page:
   a. Extract text content as Markdown.
   b. Identify all visual elements (images, diagrams, charts, tables rendered as images).
   c. For each visual element: produce a [VISUAL:] block (see format below).
4. Assemble the full Enriched Markdown document.

**[VISUAL:] block format for PDF:**

For ERD / Data Model diagrams — use `[SCHEMA:]` block:

```
[SCHEMA: <model-name>]
**Diagram Type:** Data Model / Entity Relationship Diagram
**Entities:**
| Entity | Key Field | Notable Fields |
|--------|-----------|----------------|
| <name> | <pk> | <field1>, <field2>, ... |

**Relationships:**
| Source | Field | Type | Target |
|--------|-------|------|--------|
| <entity> | <field> | N:1 / 1:N / N:N | <entity> |
[/SCHEMA]
```

For Workflow / Process Flow / State Machine diagrams — use `[FLOW:]` block:

```
[FLOW: <workflow-name>]
**Diagram Type:** Workflow / Process Flow / State Machine
**Steps:**
1. [Actor] Action — Condition: <condition> — State: <from> → <to>
2. [Actor] Action — State: <from> → <to>
...
**Decision points:**
- <condition>: → <branch A> | → <branch B>
[/FLOW]
```

For Screenshots / UI captures:

```
[VISUAL: screenshot]
**Content:** <description of UI elements, data visible, state depicted>
[/VISUAL]
```

For other visual elements:

```
[VISUAL: <type>]
**Description:** <structured description>
[/VISUAL]
```

### Phase 5b — Plain Text Pass-through Profile

For `.md` and `.txt` sources (Category A).

1. Read the file content.
2. If the file is already Markdown (`.md`): write it as-is to the preprocessed artifact — no transformation needed.
3. If the file is plain text (`.txt`): wrap in minimal Markdown:

```markdown
# <source_name> — Preprocessed Text

<file content verbatim>
```

4. No visual element extraction — plain text sources contain no embedded images.

---

### Phase 5c — Image Profile

1. Read the image file using multimodal capability.
2. Identify image type: data model / ERD, workflow / process / state machine, screenshot, other.
3. Produce the appropriate block:
   - Data model / ERD → `[SCHEMA:]` block
   - Workflow / process / state machine → `[FLOW:]` block
   - Screenshot / UI / other → `[VISUAL:]` block
4. Wrap in minimal Markdown:

```markdown
# <source_name> — Preprocessed Image

[SCHEMA: <model-name>]   OR   [FLOW: <workflow-name>]   OR   [VISUAL: <type>]
...description...
[/SCHEMA]                OR   [/FLOW]                   OR   [/VISUAL]
```

---

### Phase 5d — DOCX Pandoc Profile

**Precondition:** Pandoc available (verified in Phase 3).

**Step 1 — Create media extraction directory:**

```text
WORKSPACE_ROOT/knowledge_base/preprocessed/<source_name>_media/
```

**Step 2 — Run Pandoc conversion:**

```bash
pandoc "WORKSPACE_ROOT/input/documents/<source_name>.docx" \
  -f docx \
  -t markdown \
  --extract-media="WORKSPACE_ROOT/knowledge_base/preprocessed/<source_name>_media" \
  -o "WORKSPACE_ROOT/knowledge_base/preprocessed/<source_name>_converted.md"
```

If Pandoc exits non-zero: stop with `STATUS: BLOCKED — DOCX conversion failed. Pandoc stderr: <stderr>`.

**Step 3 — Read converted Markdown:**

Read `<source_name>_converted.md`. This file contains the document text in Markdown and `![alt](<source_name>_media/<image>)` references for each embedded image.

**Step 4 — Diagram extraction (per embedded image):**

List all files in `<source_name>_media/`. For each image file found:

a. Read the image using multimodal capability.
b. Identify diagram type:
   - Data model / ER / tables / relationships → `[SCHEMA:]`
   - Workflow / process / swimlane / state machine → `[FLOW:]`
   - Screenshot / UI / chart / other → `[VISUAL:]`
c. Produce the appropriate block (same formats as PDF and IMAGE profiles above).
d. In the converted Markdown: replace the `![...](<source_name>_media/<filename>)` reference for this image with the produced block.

**Step 5 — Assemble final Enriched Markdown:**

The result is the converted Markdown text with all `![...]` image references replaced by structured blocks.

---

### Phase 5e — Office COM Conversion Profile (Category B)

**Applicable to:** `.doc`, `.rtf` (Word COM) and `.ppt`, `.pptx` (PowerPoint COM).

**Step 5e-0 — Office availability check:**

Verify Office 365 v16.0 is installed and the required COM application is accessible:

- For DOC/RTF: test Word COM instantiation:
  ```powershell
  $word = New-Object -ComObject Word.Application
  ```
- For PPT/PPTX: test PowerPoint COM instantiation:
  ```powershell
  $ppt = New-Object -ComObject PowerPoint.Application
  ```

If COM instantiation fails (Office not installed, COM registration broken, application not found):

```
STATUS: BLOCKED — Office COM not available.
Source: <source_file>
COM application: <Word.Application | PowerPoint.Application>
Error: <error message>
Workaround: export manually to PDF, then ingest and preprocess the PDF.
```

Emit `CONVERSION_FAILED` event with reason `COM_NOT_AVAILABLE: <error>`. Stop.

**Step 5e-1 — Prepare output path:**

Conversion target:

```text
WORKSPACE_ROOT/knowledge_base/preprocessed/<source_name>_converted.pdf
```

**Step 5e-2 — Emit CONVERSION_STARTED event:**

```
| <timestamp> | CONVERSION_STARTED | source: <source_file>; category: B; method: <WORD_COM|PPTX_COM>; target: knowledge_base/preprocessed/<source_name>_converted.pdf |
```

**Step 5e-3 — Run Office COM conversion:**

For DOC / RTF (Word COM):

```powershell
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$doc = $word.Documents.Open("<WORKSPACE_ROOT>\input\documents\<source_name>.<ext>")
$pdfPath = "<WORKSPACE_ROOT>\knowledge_base\preprocessed\<source_name>_converted.pdf"
$doc.ExportAsFixedFormat($pdfPath, 17)  # 17 = wdExportFormatPDF
$doc.Close($false)
$word.Quit()
```

For PPT / PPTX (PowerPoint COM):

```powershell
$ppt = New-Object -ComObject PowerPoint.Application
$ppt.Visible = [Microsoft.Office.Core.MsoTriState]::msoTrue
$presentation = $ppt.Presentations.Open("<WORKSPACE_ROOT>\input\documents\<source_name>.<ext>")
$pdfPath = "<WORKSPACE_ROOT>\knowledge_base\preprocessed\<source_name>_converted.pdf"
$presentation.ExportAsFixedFormat($pdfPath, [Microsoft.Office.Interop.PowerPoint.PpFixedFormatType]::ppFixedFormatTypePDF)
$presentation.Close()
$ppt.Quit()
```

**Step 5e-4 — Validate conversion output:**

Check all four conditions:

1. **PDF file exists:** `Test-Path $pdfPath` returns true.
2. **PDF file non-empty:** file size > 1,024 bytes.
3. **PDF file readable:** file can be opened for reading.
4. **PDF exploitability:** basic structure check (file starts with `%PDF-`).

If any check fails:

```
STATUS: BLOCKED — Office COM conversion failed.
Source: <source_file>
Check failed: <which check failed>
Error: <error detail>
Workaround: open the document in Word/PowerPoint and export to PDF manually.
```

Emit `CONVERSION_FAILED` event with reason `<check>: <detail>`. Stop.

**Step 5e-5 — Emit CONVERSION_COMPLETED event and update sources.md:**

```
| <timestamp> | CONVERSION_COMPLETED | source: <source_file>; category: B; output: knowledge_base/preprocessed/<source_name>_converted.pdf; method: <WORD_COM|PPTX_COM> |
```

Write to sources.md:

| Column | Value |
|--------|-------|
| `conversion_status` | `COMPLETED` |
| `conversion_date` | Current timestamp (ISO 8601) |
| `conversion_output` | `knowledge_base/preprocessed/<source_name>_converted.pdf` |
| `conversion_reason` | _(empty)_ |

**Step 5e-6 — Apply PDF Profile to converted output:**

Read the generated PDF and apply Phase 5a (PDF Profile) to it. The preprocessed artifact is the Enriched Markdown produced from the converted PDF.

```
Source: <source_name>.<ext>
Category: B
Conversion: <WORD_COM|PPTX_COM> → PDF (COMPLETED)
Profile applied: PDF (Phase 5a) on converted output
```

---

### Phase 5f — Partial Scope Application (Category C with scope ≠ ALL)

**Applicable to:** Category C sources where `scope != ALL` (set during Phase 0 DEFINE SCOPE response).

**Trigger:** Check sources.md `scope` field after Phase 0. If `scope = ALL` or `scope` is empty: skip Phase 5f entirely — emit `PARTIAL_SCOPE_SKIPPED` and proceed directly to preprocessing.

**Step 5f-0 — Emit PARTIAL_SCOPE_SELECTED event:**

```
| <timestamp> | PARTIAL_SCOPE_SELECTED | source: <source_file>; category: C; scope: <scope_value>; format: <CSV|SQL|XLSX|JSON|YAML|XML> |
```

**Step 5f-1 — Apply scope by format:**

**SQL — scope filter:**

Supported scope values:
- `DDL-ONLY`: extract only `CREATE TABLE`, `ALTER TABLE`, `CREATE VIEW`, `FOREIGN KEY`, `CHECK`, `CREATE INDEX` statements. Discard all `INSERT INTO`, `UPDATE`, `DELETE`, `SELECT`.
- `DDL+INSERT`: extract DDL statements + `INSERT INTO` statements (reference data). Discard `UPDATE`, `DELETE`, `SELECT`.
- `DDL+DATA`: extract all DDL + all DML (full content, structurally filtered).

Parse SQL line by line. Include a statement if its first keyword matches the scope filter. Comments (`--`, `/* */`) are preserved.

**XLSX — scope filter:**

`scope=SheetA,SheetB` — process only sheets named in the scope list. All other sheets are excluded.

Read the XLSX ZIP structure:
```powershell
$zip = [System.IO.Compression.ZipFile]::OpenRead("<source_path>")
$sharedStrings = $zip.GetEntry("xl/sharedStrings.xml")
$worksheets = $zip.Entries | Where-Object { $_.FullName -match "xl/worksheets/sheet\d+\.xml" }
```

For each worksheet entry: resolve sheet name via `xl/workbook.xml` `<sheet name="...">` elements. Include only sheets matching the scope list.

**JSON — scope filter:**

`scope=key1,key2` — parse top-level keys of the JSON object. Include only the listed keys and their values. Exclude all other top-level keys.

**XML — scope filter:**

`scope=ElementA,ElementB` — extract only top-level child elements whose tag name matches the scope list.

**Step 5f-2 — Write scoped intermediate content:**

Write the scoped content to:

```text
WORKSPACE_ROOT/knowledge_base/preprocessed/<source_name>_scoped.<ext>
```

This file contains only the scoped portion of the source.

**Step 5f-3 — Emit PARTIAL_SCOPE_APPLIED event:**

```
| <timestamp> | PARTIAL_SCOPE_APPLIED | source: <source_file>; scope: <scope_value>; scoped_artifact: knowledge_base/preprocessed/<source_name>_scoped.<ext>; lines_included: <N>; lines_excluded: <N> |
```

**Step 5f-4 — Use scoped artifact for preprocessing:**

The subsequent preprocessing profile (Phase 5b plain text) reads from the scoped artifact instead of the original source file. The preprocessed artifact is annotated:

```
<!-- Scope applied: <scope_value> -->
<!-- Lines included: <N> / Lines total: <M> -->
```

**Step 5f-5 — Invalid scope handling:**

If the specified scope value does not match any content in the source (empty result):

```
PHASE 5f — PARTIAL SCOPE WARNING

Source: <source_file>
Scope requested: <scope_value>
Result: EMPTY — no content matched the scope.

Options:
  1. PROCESS FULL — process the entire file with CAVEAT annotation
  2. CANCEL — stop without processing

Your choice? (PROCESS FULL / CANCEL)
```

Wait for user response. If CANCEL: emit `PARTIAL_SCOPE_APPLIED` with `lines_included=0`, stop. If PROCESS FULL: treat as `scope=ALL`, emit `PARTIAL_SCOPE_SKIPPED`.

---

## Phase 6 — Write Preprocessed Artifact

Output path:

```text
WORKSPACE_ROOT/knowledge_base/preprocessed/<source_name>_preprocessed.md
```

Where `<source_name>` is the filename without extension.

Write the Enriched Markdown document.

Verify: file exists and is non-empty.

---

## Phase 7 — Update Source Registry

In `WORKSPACE_ROOT/runtime/sources.md`:

If the source already has a registry row: add or update the columns below.
If no row exists: add a new row with all available columns.

### Step 7a — Write preprocessing columns

| Column | Value |
|--------|-------|
| `source_type` | Detected source type (PDF / TXT / IMAGE / DOCX / DOC / RTF / PPT / PPTX / CSV / SQL / JSON / YAML / XML / XLSX) |
| `preprocessed_artifact` | Relative path to preprocessed artifact |

**Category B — additional conversion columns:**

| Column | Value |
|--------|-------|
| `conversion_status` | `COMPLETED` / `FAILED` |
| `conversion_date` | Conversion timestamp (ISO 8601) |
| `conversion_output` | Relative path to generated PDF (e.g. `knowledge_base/preprocessed/<name>_converted.pdf`) |
| `conversion_reason` | Error detail if FAILED; empty if COMPLETED |

**Category C with scope — additional scope column:**

The `scope` column is set during Phase 0 and does not change in Phase 7. Phase 5f produces a `scoped_artifact` path which is recorded in the `preprocessed_artifact` column.

### Step 7b — Write ADR-005 eligibility columns (Category C only)

For Category C sources, write the eligibility decision produced in Phase 0:

| Column | Value |
|--------|-------|
| `eligibility_status` | `ELIGIBLE` / `ELIGIBLE_WITH_WARNING` / `INELIGIBLE` |
| `eligibility_reason` | Synthetic summary of triggering signals |
| `eligibility_date` | Phase 0 decision timestamp (ISO 8601) |
| `eligibility_human_confirmed` | `true` / `false` |
| `scope` | Applied scope value or `ALL` |

For Category A/A+/B sources: these columns are not populated (eligibility is implicit for A/A+/B).

### Step 7c — Compute source_fingerprint

From the preprocessed artifact content, compute:

- For PDF (Category A and Category B post-conversion): count `[PAGE:` markers → pages; count `[VISUAL:` + `[SCHEMA:` + `[FLOW:` blocks → visuals; count total characters → chars (round to nearest 100)
- For IMAGE (Category A): visuals=1; count total characters of preprocessed artifact → chars (round to nearest 100)
- For DOCX (Category A+): count `[VISUAL:` + `[SCHEMA:` + `[FLOW:` blocks → visuals; count total characters of preprocessed artifact → chars (round to nearest 100)
- For MD/TXT/Category C plain text: count lines → lines; count total characters → chars (round to nearest 100)

Format:

```
pdf:pages=<N>,visuals=<N>,chars=<N>
img:visuals=1,chars=<N>
docx:visuals=<N>,chars=<N>
txt:lines=<N>,chars=<N>
```

**Category B note:** The fingerprint is computed from the preprocessed Markdown artifact (output of PDF Profile applied to the converted PDF), not from the intermediate `.pdf` file. Format: `pdf:pages=<N>,visuals=<N>,chars=<N>` — same as Category A PDF.

### Step 7d — Write source_fingerprint to registry

Write the computed fingerprint to the `source_fingerprint` column of the source's row in `runtime/sources.md`.

If the row already has a `source_fingerprint` value (reprocessing case): overwrite it with the new value.

---

## Phase 8 — Report

```text
STATUS: PREPROCESS COMPLETE
Source: <source_name>
Category: <A | A+ | B | C>
Type: <source_type>
Profile applied: <profile>
Output: knowledge_base/preprocessed/<source_name>_preprocessed.md
Visual elements captured: <N>
[Category B only] Conversion: <WORD_COM|PPTX_COM> → PDF — COMPLETED
[Category B only] Conversion output: knowledge_base/preprocessed/<source_name>_converted.pdf
[Category C only] Eligibility: <ELIGIBLE | ELIGIBLE_WITH_WARNING>
[Category C only] Scope applied: <scope_value | ALL>
```
