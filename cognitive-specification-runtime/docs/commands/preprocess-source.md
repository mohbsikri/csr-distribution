# /preprocess-source

## Purpose

Normalize source material into Enriched Markdown before knowledge extraction.

This command applies a type-specific preprocessing profile to a source file, producing an Enriched Markdown artifact that preserves non-textual content (visual elements, structured data, thread context) as structured text blocks consumable by /extract-knowledge.

This command implements ADR-002 — Source Type Aware Extraction.

---

## Inputs

* A source file located in `workspaces/<workspace_id>/input/documents/`
* Source type: auto-detected from file extension; confirmation required only for UNSUPPORTED types

---

## Outputs

Enriched Markdown artifact stored in:

```text
workspaces/<workspace_id>/knowledge_base/preprocessed/<source_name>_preprocessed.md
```

Updated source registry:

```text
workspaces/<workspace_id>/runtime/sources.md
```

---

## Supported Source Types

| Extension | Profile Applied | External Dependency |
|-----------|----------------|---------------------|
| .pdf | PDF Profile | None (multimodal) |
| .png .jpg .jpeg .gif .webp | Image Profile | None (multimodal) |
| .docx | DOCX Profile | Pandoc (BLOCKING if absent) |
| All others | UNSUPPORTED — reported to user | — |

---

## Enriched Markdown Blocks

The preprocessed artifact may contain the following block types:

* `[VISUAL: <type>]...[/VISUAL]` — structured description of a visual element (screenshot, unidentified)
* `[SCHEMA: <name>]...[/SCHEMA]` — structured description of a data model or ER diagram
* `[FLOW: <name>]...[/FLOW]` — structured description of a workflow, process, or state machine diagram
* `[PAGE: <n>]` — page separator for multi-page documents

---

## Preconditions

* Active workspace resolves correctly.
* Source file exists and is readable.
* `knowledge_base/preprocessed/` directory exists or can be created.

---

## Source Registry Schema

The source registry at `WORKSPACE_ROOT/runtime/sources.md` contains one row per processed source with the following fields:

| Field | Description |
|-------|-------------|
| `Source File` | Source filename without extension |
| `Extension` | File extension |
| `Status` | Processing status |
| `Knowledge Artifact` | Path to extracted knowledge artifact |
| `source_type` | Detected source type (PDF, IMAGE, PLAIN) |
| `preprocessed_artifact` | Path to preprocessed Enriched Markdown artifact |
| `source_fingerprint` | Content fingerprint computed at preprocessing time — used for staleness detection |

### Source Fingerprint

`source_fingerprint` is a compact content signature computed by `/preprocess-source` at preprocessing time and stored in the source registry. It is compared by `/extract-knowledge` at re-processing time to detect source changes.

Format by type:

| Source Type | Fingerprint Format |
|-------------|-------------------|
| PDF | `pdf:pages=<N>,visuals=<N>,chars=<N>` |
| IMAGE | `img:visuals=1,chars=<N>` |
| DOCX | `docx:visuals=<N>,chars=<N>` |
| PLAIN | `txt:lines=<N>,chars=<N>` |

Where `chars` is the total character count of the preprocessed artifact. Values are approximate to the nearest 100 for stability across minor whitespace variations.

If a previously registered source is reprocessed and the new fingerprint differs from the stored value, `/extract-knowledge` must emit a staleness warning before presenting the SKIP/OVERWRITE/NEW VERSION decision.

---

## Execution Rules

1. Resolve workspace.
2. Locate source file.
3. Detect source type from extension. For supported types (PDF, IMAGE): proceed automatically. For DOCX: verify Pandoc availability first (BLOCKING if absent); then proceed. For UNSUPPORTED: present choice to user (PLAIN TEXT or CANCEL).
4. Apply preprocessing profile.
5. Write Enriched Markdown artifact.
6. Compute `source_fingerprint` from preprocessed artifact content.
7. Update source registry with `source_type`, `preprocessed_artifact`, and `source_fingerprint` fields.
8. Report completion.

---

## Failure Cases

Stop and report when:

* Source file does not exist or cannot be read.
* Source type is UNSUPPORTED and user declines to continue.
* Output directory cannot be created.
* Write to preprocessed artifact fails.

---

## Completion Criteria

* Enriched Markdown artifact exists at declared path.
* Artifact is readable and non-empty.
* Source registry updated.
* All visual elements in the source have a corresponding [VISUAL:], [SCHEMA:], or [FLOW:] block in the output.
