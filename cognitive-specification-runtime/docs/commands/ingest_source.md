# Command Contract — /ingest-source

## Purpose

Import a source document into the Cognitive Specification Runtime.

This command is the entry point of the MVP workflow.

---

## Inputs

A source file provided by the user.

### Supported Format Taxonomy (ADR-005 — ACCEPTED 2026-07-04)

**Category A — Canonical Formats** (native processing, no conversion required)

| Format | Processing |
|--------|-----------|
| PDF (.pdf) | PDF Profile — text + multimodal visual description |
| Markdown (.md) | Pass-through |
| Text (.txt) | Pass-through |
| Images (.png, .jpg, .jpeg, .gif, .webp) | Image Profile — multimodal |

**Category B — Convertible Formats** (automatic Office COM conversion → PDF, then PDF preprocessing)

| Format | Conversion | Prerequisite |
|--------|-----------|-------------|
| DOCX | Word COM → PDF | Office 365 v16.0 |
| DOC | Word COM → PDF | Office 365 v16.0 |
| RTF | Word COM → PDF | Office 365 v16.0 |
| PPTX | PowerPoint COM → PDF | Office 365 v16.0 |
| PPT | PowerPoint COM → PDF | Office 365 v16.0 |

**Environment prerequisite for Category B:** Office 365 v16.0 must be installed locally. If absent, Category B formats are rejected with an explicit message and a manual conversion alternative is suggested.

**Category C — Structured Formats** (Eligibility Check required before preprocessing)

| Format | Eligibility Check | ADR-002 Profile |
|--------|-------------------|-----------------|
| XLSX (.xlsx) | Required — Phase 0 | XLSX Profile (designed, not yet implemented) |
| CSV (.csv) | Required — Phase 0 | CSV Profile (designed, not yet implemented) |
| JSON (.json) | Required — Phase 0 | JSON/YAML Profile (designed, not yet implemented) |
| YAML (.yaml, .yml) | Required — Phase 0 | JSON/YAML Profile (designed, not yet implemented) |
| XML (.xml) | Required — Phase 0 | XML Profile (designed, not yet implemented) |
| SQL (.sql) | Required — Phase 0 | SQL Profile (designed, not yet implemented) |

**Eligibility Check behavior:** For Category C sources, an eligibility decision is made before preprocessing begins. The decision is based on content nature (normative knowledge vs operational data), not format.
- `ACCEPT`: source enters preprocessing without restriction
- `ACCEPT_WITH_WARNING`: source is mixed or ambiguous — human confirmation and optional scope definition required
- `REJECT`: source contains operational data — no preprocessing, decision traced in sources.md and events.md

**Category D — Unsupported Formats** (immediate rejection with alternative suggested)

| Format | Alternative |
|--------|------------|
| VSDX | Export to PDF from Visio, or to PNG/SVG |
| ODT | Export to PDF from LibreOffice or Word |
| ODP | Export to PDF from LibreOffice or PowerPoint |
| HTML | Export page to PDF via browser |
| URL | Export page to PDF via browser |
| ZIP | Extract files individually and ingest each |
| Audio | Provide transcript as TXT or MD |
| Video | Provide transcript or slide deck |

---

## Preconditions

The repository structure must exist.

The source file must be accessible.

---

## Processing

The command must:

1. Identify the source file. Its path may be anywhere on disk; if it is not already in the project's `input/documents/`, the command copies it there (the original is never moved or modified, and an existing different file of the same name is never overwritten) `[issue #55]`.
2. Capture metadata.
3. Register the source.
4. Create an ingestion event.
5. Store traceability information.

The command does not perform extraction.

---

## Outputs

### Source Registration

workspaces/\<workspace_id\>/knowledge_base/raw/

Registration records must include origin_path referencing the relative repository path of the source file as staged in `input/documents/`, and provided_path — the path the user gave.

### Runtime Event

workspaces/\<workspace_id\>/runtime/events.md

### Runtime State Update

workspaces/\<workspace_id\>/runtime/state.md

---

## Traceability

The following information must be recorded:

* source name
* source type
* source format category (A / B / C / D) — per ADR-005 taxonomy
* ingestion date
* ingestion status
* origin path
* eligibility_status — for Category C: `PENDING` at ingestion (Phase 0 runs at preprocessing time); for Category D: `UNSUPPORTED`

---

## Success Criteria

The source is registered.

An ingestion event exists.

The runtime state is updated.

---

## Failure Conditions

The source file cannot be accessed.

The repository structure is invalid.

The runtime cannot record the ingestion event.
