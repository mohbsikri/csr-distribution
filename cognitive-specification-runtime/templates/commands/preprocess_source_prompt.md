# Preprocess Source Prompt Template

You are executing the Cognitive Specification Runtime preprocessing stage.

Your objective is to normalize source material into Enriched Markdown that preserves non-textual content as structured text blocks, enabling /extract-knowledge to capture information that would otherwise be lost.

You must follow repository rules and execution specifications defined in:

* ${CLAUDE_PLUGIN_ROOT}/docs/commands/preprocess-source.md
* ${CLAUDE_PLUGIN_ROOT}/docs/commands/preprocess-source_execution.md

---

# Core Principles

* Repository-first: all output goes to files, not conversation.
* Fidelity: describe visual content accurately and completely. Never invent content.
* Completeness: every visual element in the source must have a corresponding [VISUAL:] block.
* Structure: use the prescribed block formats exactly.
* Traceability: the preprocessed artifact must be traceable to its source file.

---

# Workspace Resolution

Resolve the active workspace from runtime/current_workspace.md.
Build WORKSPACE_ROOT = workspaces/<workspace_id>/
Apply R4a–R4e registry validation.

---

# Source Classification and Routing (ADR-005)

Determine the source's format category from `runtime/sources.md` (preferred) or from file extension (fallback).

**ADR-005 format_category routing table:**

| Category | Extension | Route |
|----------|-----------|-------|
| A | `.pdf` | PDF Profile |
| A | `.md` `.txt` | Plain Text Pass-through |
| A | `.png` `.jpg` `.jpeg` `.gif` `.webp` | Image Profile |
| A+ | `.docx` | DOCX Pandoc Profile |
| B | `.doc` `.rtf` `.ppt` `.pptx` | BLOCKED — RT-02 pending. Suggest manual PDF export. |
| C | `.xlsx` `.csv` `.json` `.yaml` `.yml` `.xml` `.sql` | Phase 0 Eligibility Gate required |
| D | other | BLOCKED — immediate rejection with alternative suggested |

**Category D:** Report rejection immediately. No preprocessing. Include format-specific alternative from ADR-005 Category D table.

**Category B — Office COM Conversion:**

DOC/RTF: Word COM → PDF. PPT/PPTX: PowerPoint COM → PDF. Pre-checks before conversion:
1. Test COM instantiation (`New-Object -ComObject Word.Application` / `PowerPoint.Application`). If fails: emit CONVERSION_FAILED, stop with manual export workaround.
2. Run export (`ExportAsFixedFormat($pdfPath, 17)` for Word; `ExportAsFixedFormat(... ppFixedFormatTypePDF)` for PowerPoint).
3. Validate PDF: exists + size > 1024 bytes + starts with `%PDF-`. If fails: emit CONVERSION_FAILED, stop.
4. Emit CONVERSION_COMPLETED. Update sources.md (conversion_status, conversion_date, conversion_output).
5. Apply Phase 5a (PDF Profile) to the converted PDF output.

**Category C — Phase 0 Eligibility Gate:**

For Category C sources with `eligibility_status = PENDING`:
1. Read source file partially (first 200 rows / 3,000 chars).
2. Evaluate KO signals (normative: rules, definitions, constraints, DDL, schemas) vs OD signals (operational: dates, amounts, instance rows, transactional data).
3. Produce decision: ACCEPT / ACCEPT_WITH_WARNING / REJECT — per ADR-005 signal hierarchy.
4. For ACCEPT_WITH_WARNING: request human confirmation and optional scope.
5. Write decision to `runtime/sources.md` (eligibility_status, eligibility_reason, eligibility_date, eligibility_human_confirmed, scope).
6. Emit events to `runtime/events.md`: ELIGIBILITY_EVALUATED + ELIGIBILITY_ACCEPTED / ELIGIBILITY_ACCEPTED_WITH_WARNING / ELIGIBILITY_REJECTED + PHASE0_COMPLETED (if not rejected).
7. If REJECT: stop. If ACCEPT or ACCEPT_WITH_WARNING: proceed.
8. **RT-06 Partial Scope (if scope ≠ ALL):** Emit PARTIAL_SCOPE_SELECTED. Apply scope filter to source:
   - SQL `DDL-ONLY`: keep CREATE/ALTER/FOREIGN KEY/CHECK only.
   - SQL `DDL+INSERT`: keep DDL + INSERT INTO.
   - XLSX `scope=Sheet1,Sheet2`: include only named sheets.
   - JSON `scope=key1,key2`: include only listed top-level keys.
   - XML `scope=ElemA,ElemB`: include only listed root child elements.
   Write scoped artifact to `<source_name>_scoped.<ext>`. Emit PARTIAL_SCOPE_APPLIED. If scope yields empty result: ask user PROCESS FULL or CANCEL.
9. If scope = ALL: emit PARTIAL_SCOPE_SKIPPED.

**Category A/A+ confirmation:**
```text
Source: <source_name>.<ext>
Category: <A | A+>
Detected type: <PDF | TXT | IMAGE | DOCX>
Profile to apply: <profile>
Processing...
```

For A+ (DOCX): run `pandoc --version` first. If not found: stop with BLOCKED message including `winget install pandoc`.

---

# Diagram Block Formats

Use the correct block type based on the diagram identified:

**Data Model / ERD → `[SCHEMA:]`:**

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

**Workflow / Process / State Machine → `[FLOW:]`:**

```
[FLOW: <workflow-name>]
**Diagram Type:** Workflow / Process Flow / State Machine
**Steps:**
1. [Actor] Action — Condition: <condition> — State: <from> → <to>
...
**Decision points:**
- <condition>: → <branch A> | → <branch B>
[/FLOW]
```

**Screenshot / UI / other → `[VISUAL:]`:**

```
[VISUAL: <type>]
**Content:** <structured description>
[/VISUAL]
```

**Decision rule for diagram type:**
- Entities, tables, fields, foreign keys, relationships → `[SCHEMA:]`
- Steps, actors, transitions, conditions, branches, swimlanes → `[FLOW:]`
- UI elements, screen captures, charts, unidentified → `[VISUAL:]`

When in doubt between [SCHEMA:] and [FLOW:], choose [FLOW:] — it is more general.

---

# Plain Text Pass-through Profile (Category A — .md / .txt)

For `.md` files: write the file content as-is to the preprocessed artifact — no transformation.

For `.txt` files: wrap in minimal Markdown header:
```markdown
# <source_name> — Preprocessed Text

<file content verbatim>
```

No visual element extraction. Source fingerprint: `txt:lines=<N>,chars=<N>`.

---

# PDF Profile (Category A — .pdf)

Read the PDF using multimodal capability.

For each page:
1. Extract text content as Markdown.
2. Identify all visual elements (images, diagrams, charts, tables rendered as images).
3. For each visual element: determine type and produce the appropriate block ([SCHEMA:], [FLOW:], or [VISUAL:]) using the formats above.

---

# Image Profile (Category A — .png / .jpg / .jpeg / .gif / .webp)

Read the image using multimodal capability.
Identify image type (data model, workflow, screenshot, other).
Produce a single block using the appropriate format ([SCHEMA:], [FLOW:], or [VISUAL:]).

---

# DOCX Pandoc Profile (Category A+)

**Pandoc must be available** (verified in Phase 3 — do not re-verify here).

1. Run Pandoc to convert DOCX to Markdown and extract embedded images:

```bash
pandoc "<WORKSPACE_ROOT>/input/documents/<source_name>.docx" \
  -f docx -t markdown \
  --extract-media="<WORKSPACE_ROOT>/knowledge_base/preprocessed/<source_name>_media" \
  -o "<WORKSPACE_ROOT>/knowledge_base/preprocessed/<source_name>_converted.md"
```

2. If Pandoc fails: stop with `STATUS: BLOCKED — DOCX conversion failed`.

3. Read the converted Markdown.

4. For each embedded image (`![...](<source_name>_media/<file>)` reference):
   - Read the image using multimodal capability.
   - Identify diagram type.
   - Produce the appropriate block ([SCHEMA:], [FLOW:], or [VISUAL:]).
   - Replace the `![...]` reference in the Markdown with the produced block.

5. The final preprocessed artifact is the converted Markdown with all image references replaced by structured blocks.

---

# Output Rules

Write enriched Markdown to:

```
WORKSPACE_ROOT/knowledge_base/preprocessed/<source_name>_preprocessed.md
```

Verify file exists and is non-empty after writing.

Update WORKSPACE_ROOT/runtime/sources.md with: source_type, preprocessed_artifact, source_fingerprint.
For Category C: also write eligibility_status, eligibility_reason, eligibility_date, eligibility_human_confirmed, scope (from Phase 0 decision).

---

# Source Fingerprint Computation

After writing the preprocessed artifact, compute the source_fingerprint:

For PDF artifacts:
- Count `[PAGE:` occurrences → pages
- Count `[VISUAL:` + `[SCHEMA:` + `[FLOW:` occurrences → visuals
- Count total character length of artifact → chars (round to nearest 100)
- Fingerprint: `pdf:pages=<N>,visuals=<N>,chars=<N>`

For IMAGE artifacts:
- visuals = 1
- Count total character length of artifact → chars (round to nearest 100)
- Fingerprint: `img:visuals=1,chars=<N>`

For DOCX artifacts:
- Count `[VISUAL:` + `[SCHEMA:` + `[FLOW:` occurrences → visuals
- Count total character length of preprocessed artifact → chars (round to nearest 100)
- Fingerprint: `docx:visuals=<N>,chars=<N>`

For PLAIN TEXT artifacts:
- Count newline characters → lines
- Count total character length → chars (round to nearest 100)
- Fingerprint: `txt:lines=<N>,chars=<N>`

Write this fingerprint to the `source_fingerprint` field in `WORKSPACE_ROOT/runtime/sources.md`.

---

# Completion

Report:

```
STATUS: PREPROCESS COMPLETE
Source: <source_name>
Type: <source_type>
Profile applied: <profile>
Output: knowledge_base/preprocessed/<source_name>_preprocessed.md
Visual elements captured: <N>
```
