# /extract-knowledge

## Purpose

Extract structured and traceable knowledge from source material stored in the repository.

This command transforms source documents into knowledge artifacts that can be consumed by downstream CSR stages.

---

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

---

## Preconditions

Before execution:

1. The repository structure must be valid.
2. At least one ingested raw record must exist in:

```text
WORKSPACE_ROOT/knowledge_base/raw/
```

3. The source registry must exist:

```text
WORKSPACE_ROOT/runtime/sources.md
```

4. The following artifacts must be available:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/extract-knowledge.md
${CLAUDE_PLUGIN_ROOT}/docs/commands/extract-knowledge_execution.md
${CLAUDE_PLUGIN_ROOT}/templates/commands/extract_knowledge_prompt.md
```

---

## Execution

### Step 1 — Load Specifications

Read and understand:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/extract-knowledge.md
${CLAUDE_PLUGIN_ROOT}/docs/commands/extract-knowledge_execution.md
${CLAUDE_PLUGIN_ROOT}/templates/commands/extract_knowledge_prompt.md
WORKSPACE_ROOT/runtime/sources.md
```

The repository is the source of truth.

Ignore any prior conversational assumptions that are not present in the repository.

---

### Step 1.5 — V2 Context Detection

Before discovering sources, check whether `WORKSPACE_ROOT/runtime/lineage.md` exists.

- **Found:** V2 workspace. Read `source_workspace_id` and v1 ID ceiling (max_br / max_tr / max_c) from the inherited traceability matrix. Set `extraction_mode = V2`.
- **Not found:** V1 workspace. `extraction_mode = V1`. Standard behavior.

Full procedure in `${CLAUDE_PLUGIN_ROOT}/docs/commands/extract-knowledge_execution.md` Phase 0.

---

### Step 2 — Discover Sources

Inspect:

```text
WORKSPACE_ROOT/knowledge_base/raw/
```

Build the list of available ingested sources.

For each raw record:

* read `origin_path`;
* identify the original source file;
* load source content through `origin_path`.

---

### Step 3 — Check Source Registry

Inspect:

```text
WORKSPACE_ROOT/runtime/sources.md
```

For each source:

* determine whether it is new;
* determine whether it has already been processed.

---

### Step 4 — Request User Decisions

For previously processed sources, ask the user to choose:

```text
SKIP
OVERWRITE
NEW VERSION
```

Apply the behavior defined in:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/extract-knowledge_execution.md
```

---

### Step 5 — Process Approved Sources

For each source selected for processing:

1. Analyze source content.
2. Extract supported knowledge (Phase 4 → Phase 5 in execution spec). If `extraction_mode = V2`: assign new IDs from v1 ceiling for rules with no v1 reference (tagged `[v2-added]`); retain v1 IDs for rules that explicitly modify a v1 rule (tagged `[v2-modified]`) or retire one (tagged `[DEPRECATED in v2]`). See execution spec Phase 5 for annotation type determination rules.
3. **Run intra-document contradiction check** (Phase 5.5 — Bloc 5): scan all extracted BR/TR/C pairs for INTRA_CONTRADICTIONs; write conflict artifact to `knowledge_base/conflicts/`; proceed regardless of findings.
4. Structure extracted knowledge. If V2 mode: include v2 header block and `[v2-added]` annotations on all BR/TR/C items.
5. Validate extracted knowledge.
6. Persist knowledge artifacts.
7. Update the source registry.

Follow all extraction, validation, traceability, versioning and persistence rules defined by the specifications.

---

### Step 6 — Generate Results

Create knowledge artifacts in:

```text
WORKSPACE_ROOT/knowledge_base/extracted/
```

Naming must follow:

```text
<source_name>_knowledge.md
```

or

```text
<source_name>_knowledge_v<n>.md
```

according to the versioning rules.

---

### Step 7 — Update Registry

Update:

```text
WORKSPACE_ROOT/runtime/sources.md
```

using the registry update rules defined in the execution specification.

---

## Validation

Before completion verify that:

* all processed sources produced valid knowledge artifacts;
* traceability is preserved;
* validation rules succeeded;
* source registry updates are consistent;
* generated artifacts respect naming conventions.

---

## Failure Handling

Stop execution and report an explicit error when:

* source material is missing;
* source material cannot be read;
* source registry cannot be read;
* repository structure is invalid;
* extracted information cannot be traced.

Do not silently continue after a blocking failure.

---

## Completion Criteria

Execution is complete when:

* all available sources have been processed or skipped by user decision;
* knowledge artifacts have been generated for processed sources;
* outputs have been written to the repository;
* the source registry has been updated;
* validation checks have passed.

---

## Expected Outputs

Repository updates may include:

```text
WORKSPACE_ROOT/knowledge_base/extracted/*_knowledge.md          ← V1 format
WORKSPACE_ROOT/knowledge_base/extracted/*_knowledge_v<n>.md
WORKSPACE_ROOT/knowledge_base/extracted/*_knowledge_index.md    ← V1 format
WORKSPACE_ROOT/knowledge_base/extracted/*_knowledge_index_v<n>.md
WORKSPACE_ROOT/knowledge_base/conflicts/*_intra_contradictions.md  ← Bloc 5 (clean or flagged)
WORKSPACE_ROOT/runtime/sources.md
```

In V2 mode, the knowledge artifact and index include the v2 header and one of three annotation types per rule: `[v2-added]` (new rule, new v2 ID), `[v2-modified]` (modifies a v1 rule, v1 ID retained), or `[DEPRECATED in v2]` (retires a v1 rule, v1 ID retained). The index includes an additional `Version` column. Paths are identical — V2 mode is a format variant, not a separate file location.

No other repository areas should be modified unless explicitly required by future specifications.
