# Command Execution — /ingest-source

## Objective

Register a source document in the Cognitive Specification Runtime.

The command must preserve traceability and prepare the document for downstream processing.

The command must not perform extraction.

---

## Execution Flow

### Step 1 — Validate Repository Structure

Verify that the following locations exist:

* input/documents/
* knowledge_base/raw/
* runtime/

If a required location is missing:

* stop execution;
* report the issue.

---

### Step 2 — Validate Source File and Classify Format

Verify that:

* the file exists;
* the file is readable.

Classify the source format per ADR-005 taxonomy:

| Category | Formats | Action |
|----------|---------|--------|
| A — Canonical | PDF, MD, TXT, PNG, JPG, JPEG, GIF, WEBP | Accept — record format_category=A |
| A+ — DOCX | DOCX | Accept — record format_category=A+ (Pandoc path per AMBIGUITY-INP-001/002) |
| B — Convertible | DOC, RTF, PPTX, PPT | Accept — record format_category=B |
| C — Structured | XLSX, CSV, JSON, YAML, YML, XML, SQL | Accept — record format_category=C, eligibility_status=PENDING |
| D — Unsupported | VSDX, ODT, ODP, HTML, URL, ZIP, Audio, Video | Reject — trace in sources.md + FORMAT_CLASSIFIED event, then stop |

If the extension is unknown: treat as Category D — report with message requesting format clarification.

If format is Category D:

* Create a minimal sources.md row (for traceability — ADR-005 Rejection Traceability):

```
| <source_file> | <extension> | D | rejected | UNSUPPORTED | <timestamp> | | | | Format not supported | <timestamp> | false | |
```

* Emit FORMAT_CLASSIFIED event:

```
| <timestamp> | FORMAT_CLASSIFIED | source: <source_file>; format_category: D; basis: extension (<ext>); eligibility_status: UNSUPPORTED |
```

* Stop execution;
* Report the failure with the recommended alternative (see ADR-005 Category D table).

No further steps execute for Category D.

---

### Step 2b — Stage the Source into the Project `[issue #55, 2026-11-09]`

The source path given to the command may be anywhere on disk — the user's Downloads folder, a share, the project folder itself. Downstream commands (`/preprocess-source`) read sources from `input/documents/`. Staging closes that gap inside the official command, so neither the user nor the Operating Agent has to know an internal folder or copy a file by hand.

1. If the source already lies under `WORKSPACE_ROOT/input/documents/`: use it as is. Nothing is copied.
2. Otherwise, **copy** it to `WORKSPACE_ROOT/input/documents/<source filename>`. Never move, rename or modify the original.
3. If a file with that name already exists in `input/documents/`:
   * same content (byte-identical) → reuse it, do not copy again;
   * different content → stop. Report that a different document with the same name is already in the project and ask the user how to proceed. Never overwrite.
4. Record:
   * `origin_path` = the staged path relative to the folder that holds `runtime/workspaces.md` (e.g. `workspaces/<workspace_id>/input/documents/<source filename>`);
   * `provided_path` = the path exactly as the user gave it.

The copy is the only write outside `knowledge_base/raw/` and `runtime/` that this command performs, and it stays inside `WORKSPACE_ROOT`. A copy into `input/documents/` alone is **not** an ingestion: Steps 3–7 still run.

---

### Step 3 — Collect Metadata

Collect:

* source name
* source extension
* ingestion timestamp

---

### Step 4 — Register Source

Create a source registration record in:

knowledge_base/raw/

The registration must reference:

* source name
* source type
* format_category (A / A+ / B / C / D) — per ADR-005
* ingestion timestamp
* origin path (the staged copy — Step 2b)
* provided path (where the user gave the file — Step 2b)
* eligibility_status — `PENDING` for Category C; `UNSUPPORTED` for Category D (already rejected in Step 2); not applicable for A/A+/B

origin_path is the relative repository path to the original source file.

Example:

```text
input/documents/test_source.md
```

---

### Step 4b — Update Source Registry (sources.md)

Create or update the source row in:

runtime/sources.md

The row must include at minimum:

| Column | Value |
|--------|-------|
| source_file | source filename (with extension) |
| extension | file extension (e.g. `.pdf`, `.docx`) |
| format_category | `A` / `A+` / `B` / `C` / `D` — per ADR-005 |
| status | `ingested` |
| eligibility_status | `PENDING` for Category C; `UNSUPPORTED` for Category D; leave blank for A/A+/B |
| ingested | ingestion timestamp (ISO 8601) |

Columns populated by subsequent commands (do not fill at ingestion):
`source_type`, `preprocessed_artifact`, `source_fingerprint`, `eligibility_reason`, `eligibility_date`, `eligibility_human_confirmed`, `scope`

**Backward compatibility:** Existing workspace sources.md rows without format_category or eligibility_status columns are not retroactively modified. The new columns apply to newly ingested sources only.

---

### Step 5 — Record Runtime Events

Append two events to:

runtime/events.md

**Event 1 — INGESTION_COMPLETED:**

```
| <timestamp> | INGESTION_COMPLETED | source: <source_filename>; format_category: <A|A+|B|C|D>; status: ingested |
```

**Event 2 — FORMAT_CLASSIFIED:**

```
| <timestamp> | FORMAT_CLASSIFIED | source: <source_filename>; format_category: <A|A+|B|C|D>; basis: extension (<ext>); eligibility_status: <PENDING|N/A|UNSUPPORTED> |
```

Use the same timestamp for both events.

---

### Step 6 — Update Runtime State

Update:

runtime/state.md

State must indicate:

* latest ingestion
* latest source

---

### Step 7 — Report Result

Provide a concise execution report.

Include:

* source name
* status
* timestamp
* the project (`workspace_id`) it was registered in

---

### Step 7b — Offer the Graphic Charter, Once `[A2, 2026-11-01]`

**Trigger condition — all three must hold:**

1. this ingestion succeeded;
2. it is the **first** source of the workspace (`sources.md` carries exactly one row after Step 4b);
3. `WORKSPACE_ROOT/runtime/workspace_config.md` has `**theme:** default` and no `theme_path`.

If any fails, skip silently. This is offered **once per workspace**, never repeated.

**Why here, and not at project creation.** `/configure-theme` has worked since it was written and nothing has ever proposed it, so it is used only by someone who already knows it exists. Project creation is the wrong moment: at that point there is no document to extract a charter from, and the user is being asked to name a project, not to make a design decision. The first ingested source is usually the client's own document — it carries the charter, it is already on disk, and its path is in hand.

**What to say.** One sentence, in the interaction language, offering and not insisting — this is optional and a specification is perfectly deliverable in the default theme:

> Vous pourrez aligner les documents produits sur votre charte graphique à partir de ce document : `/configure-theme EXTRACT <path>`. Le thème par défaut convient très bien si vous préférez voir le fond d'abord.

**Do not run it.** Report the possibility and continue. `/configure-theme EXTRACT` previews extracted values and asks for confirmation (Step 3.3); invoking it from inside an ingestion would bury an interactive decision inside a command the user ran for another purpose.

**Safety net.** `/export-views` is the second and last opportunity: the first export of a workspace still on the default theme may mention the same possibility, once. After that, silence — a runtime that keeps offering the same thing teaches the user to skip what it says.

---

## Forbidden Actions

The command must not:

* extract knowledge;
* detect conflicts;
* generate questions;
* modify specifications.

---

## Success Condition

The source is registered and traceability is preserved.

---

## Failure Condition

Any missing repository dependency or inaccessible source file prevents execution.
