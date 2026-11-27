# /preprocess-source

## Purpose

Normalize source material into Enriched Markdown before knowledge extraction.

This command applies a type-specific preprocessing profile to a source file, producing an Enriched Markdown artifact that preserves non-textual content as structured text blocks consumable by /extract-knowledge.

Implements ADR-002 — Source Type Aware Extraction.

---

## Workspace Resolution

Before any file operation, resolve the active workspace:

```text
Step W1: Read runtime/current_workspace.md and parse workspace_id.
Step W2: Build WORKSPACE_ROOT = workspaces/<workspace_id>/
Step W3: Verify WORKSPACE_ROOT exists.
Step W4: Read runtime/workspaces.md. Validate registry (R4a–R4e).
Step W5: All subsequent paths are prefixed with WORKSPACE_ROOT.
```

---

## Workspace Isolation

All file write operations must target paths within `WORKSPACE_ROOT/knowledge_base/preprocessed/`.

Exceptions: runtime/current_workspace.md, runtime/workspaces.md, docs/, templates/, .claude/

---

## Preconditions

1. Active workspace resolves correctly.
2. Source file exists in WORKSPACE_ROOT/input/documents/ or at specified path.
3. The following specification artifacts must exist and be readable:
   - ${CLAUDE_PLUGIN_ROOT}/docs/commands/preprocess-source.md
   - ${CLAUDE_PLUGIN_ROOT}/docs/commands/preprocess-source_execution.md
   - ${CLAUDE_PLUGIN_ROOT}/templates/commands/preprocess_source_prompt.md

---

## Execution

### Step 1 — Load Specifications

Read and assimilate:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/preprocess-source.md
${CLAUDE_PLUGIN_ROOT}/docs/commands/preprocess-source_execution.md
${CLAUDE_PLUGIN_ROOT}/templates/commands/preprocess_source_prompt.md
```

The repository is the source of truth.

### Step 2 — Execute Preprocessing Runtime

Execute the runtime defined in ${CLAUDE_PLUGIN_ROOT}/templates/commands/preprocess_source_prompt.md following the phases in ${CLAUDE_PLUGIN_ROOT}/docs/commands/preprocess-source_execution.md:

1. Workspace resolution
2. Source file location
3. Source classification and routing (ADR-005 categories A / A+ / B / C / D)
4. Phase 0 — Eligibility Gate (Category C only: ACCEPT / ACCEPT_WITH_WARNING / REJECT)
5. Preprocessed directory creation
6. Apply profile:
   - Phase 5a: PDF (Category A)
   - Phase 5b: Plain Text pass-through (Category A — .md/.txt)
   - Phase 5c: Image (Category A)
   - Phase 5d: DOCX Pandoc (Category A+)
   - Phase 5e: Office COM → PDF (Category B: DOC/RTF via Word COM, PPT/PPTX via PowerPoint COM)
   - Phase 5f: Partial Scope filter (Category C with scope ≠ ALL, then plain text profile)
7. Write preprocessed artifact
8. Update source registry (source_type, preprocessed_artifact, source_fingerprint, eligibility fields, conversion fields)
9. Report completion

---

## Supported Types (ADR-005)

| Category | Extension | Profile | External Dependency |
|----------|-----------|---------|---------------------|
| A | `.pdf` | PDF — multimodal extraction, [SCHEMA:]/[FLOW:]/[VISUAL:] blocks | None |
| A | `.md` `.txt` | Plain Text — pass-through, no transformation | None |
| A | `.png` `.jpg` `.jpeg` `.gif` `.webp` | Image — multimodal description, one block per image | None |
| A+ | `.docx` | DOCX — Pandoc → Markdown + diagram extraction from embedded images | Pandoc (BLOCKING if absent) |
| B | `.doc` `.rtf` `.ppt` `.pptx` | Office COM → PDF → PDF Profile | Office 365 v16.0 |
| C | `.xlsx` `.csv` `.json` `.yaml` `.yml` `.xml` `.sql` | Phase 0 Eligibility Check + optional Partial Scope (RT-06) | None |
| D | all others | Immediate rejection — unsupported format | — |

**Category A+ — DOCX uses Pandoc (not COM):**
DOCX was excluded from Category B (Office COM → PDF path) per AMBIGUITY-INP-001/002 PO decision. Pandoc produces 0 structural defects vs 4 defects on the COM path. Install: `winget install pandoc`.

**Category B — Office COM Conversion (RT-02):**
DOC/RTF → Word COM → PDF. PPT/PPTX → PowerPoint COM → PDF. Pre-checks: COM available, conversion successful, PDF exploitable. CONVERSION_STARTED + CONVERSION_COMPLETED/FAILED events emitted. If Office 365 unavailable: explicit block with manual export workaround.

**Category C — Phase 0 (Eligibility Gate) + RT-06 (Partial Scope):**
Phase 0 evaluates content nature (KO vs OD signals). ACCEPT_WITH_WARNING + DEFINE SCOPE triggers RT-06: scope filter applied before preprocessing (SQL DDL-ONLY/DDL+INSERT/DDL+DATA; XLSX sheet selection; JSON/XML key/element selection). Scope persisted and traceable.

---

## Expected Output

```text
WORKSPACE_ROOT/knowledge_base/preprocessed/<source_name>_preprocessed.md
```

Updated:

```text
WORKSPACE_ROOT/runtime/sources.md
```

---

## Failure Handling

Stop and report when:
- Source file not found.
- Source type UNSUPPORTED and user cancels.
- Write failure on preprocessed artifact.

---

## Completion Reporting

```text
STATUS: PREPROCESS COMPLETE
Source: <source_name>
Type: <source_type>
Profile applied: <profile>
Output: knowledge_base/preprocessed/<source_name>_preprocessed.md
Visual elements captured: <N>
```
