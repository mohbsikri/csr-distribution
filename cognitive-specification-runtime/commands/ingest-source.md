---
description: Ingest Source — register a source document (PDF, Word, text, image…) into the active CSR project
argument-hint: <path to the source file>
---

# Ingest Source

Register a source document in the Cognitive Specification Runtime.

## Specification Layers

```text
Layer 1 contract:       ${CLAUDE_PLUGIN_ROOT}/docs/commands/ingest_source.md
Layer 2 execution spec: ${CLAUDE_PLUGIN_ROOT}/docs/commands/ingest_source_execution.md
```

Read the Layer 2 execution specification before executing. It is authoritative for the step sequence; this file summarises it. Where they differ, Layer 2 wins — in particular Step 2b (staging the source into the project) and Step 4b (the `runtime/sources.md` row) `[issue #55]`.

The source path is the command argument. It may be anywhere on disk: the user never has to place it in an internal folder first.

## Workspace Resolution

Before any file operation, resolve the active workspace:

```text
Step W1: Read runtime/current_workspace.md and parse workspace_id.
         If absent or empty: record resolver_workspace_id as null; skip W2–W3; proceed to W4.
Step W2: Build WORKSPACE_ROOT = workspaces/<workspace_id>/
Step W3: Verify WORKSPACE_ROOT exists. If not found, stop and report:
         STATUS: BLOCKED — Workspace Root Not Found: workspaces/<workspace_id>/
Step W4: Read runtime/workspaces.md. Validate registry (R4a–R4e):
         R4a: workspace_id must be present in registry — BLOCKING if missing.
         R4b: status must not be 'archived' — BLOCKING; warn if 'paused' or 'completed'.
         R4c: runtime_version must be present — WARNING if missing.
         R4d: last_active must be present — WARNING if missing.
         R4e (M10 revision): count entries with status:active in runtime/workspaces.md.
              Case A — Normal: exactly one active entry; its workspace_id = resolver_workspace_id → continue.
              Case B — Drift: exactly one active entry; its workspace_id ≠ resolver_workspace_id →
                       BLOCKING: STATUS: BLOCKED — WORKSPACE DRIFT DETECTED. Resolver names
                       <resolver_workspace_id>; registry active entry is <registry_active_workspace_id>.
                       Run /workspace-lifecycle SWITCH to synchronize runtime/current_workspace.md.
              Case C — Resolver absent: resolver_workspace_id is null; one active entry in registry →
                       BLOCKING: STATUS: BLOCKED — RESOLVER ABSENT. Registry identifies
                       <registry_active_workspace_id> as active but runtime/current_workspace.md is
                       absent or empty. Run /workspace-lifecycle SWITCH <registry_active_workspace_id>.
              Case D — No active entry: zero status:active entries in registry →
                       BLOCKING: STATUS: BLOCKED — NO ACTIVE WORKSPACE. Registry has no status:active
                       entry. Run /workspace-lifecycle SWITCH to designate an active workspace.
              Case E — Multiple active entries: more than one status:active entry in registry →
                       BLOCKING: STATUS: BLOCKED — REGISTRY INTEGRITY VIOLATION. Multiple status:active
                       entries in runtime/workspaces.md. Manual correction required.
Step W5: All subsequent paths are prefixed with WORKSPACE_ROOT.
```

## Workspace Isolation

All file operations must target paths prefixed with `WORKSPACE_ROOT`.

Exceptions (not workspace-scoped): `runtime/current_workspace.md`, `runtime/workspaces.md`, `docs/`, `templates/`, `.claude/`

Any operation targeting a path outside `WORKSPACE_ROOT` that is not on the exception list must be rejected and reported as workspace contamination.

## Instructions

Execute the following sequence.

### 1. Validate Repository Structure

Verify that the following locations exist:

* `WORKSPACE_ROOT/input/documents/`
* `WORKSPACE_ROOT/knowledge_base/raw/`
* `WORKSPACE_ROOT/runtime/`

If any location is missing:

* stop execution;
* report the missing element.

---

### 2. Validate Source and Classify Format

Verify:

* source exists;
* source is readable.

Classify the source format per ADR-005 Input Taxonomy (ACCEPTED 2026-07-04):

**Category A — Canonical (accept, no conversion):** PDF, MD, TXT, PNG, JPG, JPEG, GIF, WEBP

**Category B — Convertible (accept, Office COM conversion at preprocessing time):** DOCX, DOC, RTF, PPTX, PPT
— Requires Office 365 v16.0. If absent at preprocessing time: explicit rejection with manual conversion alternative.

**Category C — Structured (accept, Eligibility Check required at preprocessing time):** XLSX, CSV, JSON, YAML, YML, XML, SQL
— Record `eligibility_status: PENDING` at ingestion. Phase 0 runs during `/preprocess-source`.

**Category D — Unsupported (reject immediately):** VSDX, ODT, ODP, HTML, URL, ZIP, Audio, Video, and unknown extensions.
— Stop execution. Report the format category and suggest the appropriate alternative (export to PDF, extract files, provide transcript).

If validation fails:

* stop execution;
* explain the reason and provide the recommended alternative.

---

### 2b. Stage the Source into the Project `[issue #55]`

Per Layer 2 Step 2b: if the source is not already under `WORKSPACE_ROOT/input/documents/`, **copy** it there (never move, rename or modify the original). If a file with the same name already exists there: identical content → reuse it; different content → stop and ask the user, never overwrite. The staged copy is the `origin_path`; the path the user gave is recorded as `provided_path`.

---

### 3. Collect Metadata

Capture:

* source name
* source type
* format_category (A / B / C / D) — per ADR-005
* ingestion timestamp
* origin path
* eligibility_status — `PENDING` for Category C; `UNSUPPORTED` for Category D (already rejected)

origin_path is the relative repository path to the original source file.

Example:

```text
WORKSPACE_ROOT/input/documents/test_source.md
```

---

### 4. Register Source

Create a registration record in:

`WORKSPACE_ROOT/knowledge_base/raw/`

Include:

* source name
* source type
* format_category
* ingestion timestamp
* origin path
* eligibility_status

---

### 5. Record Runtime Event

Append an ingestion event to:

`WORKSPACE_ROOT/runtime/events.md`

Event type:

INGESTION_COMPLETED

---

### 6. Update Runtime State

Update:

`WORKSPACE_ROOT/runtime/state.md`

Include:

* latest source
* latest ingestion timestamp

---

### 7. Produce Report

Return a concise report including:

* source name
* status
* timestamp

---

## Constraints

Do NOT:

* extract knowledge;
* detect conflicts;
* generate questions;
* modify specifications.

## Success Criteria

* source registered
* event recorded
* runtime state updated
