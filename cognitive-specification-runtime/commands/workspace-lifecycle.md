---
description: Workspace lifecycle — CREATE, SWITCH, ARCHIVE, REOPEN or V2 a CSR project workspace (CREATE registers it paused)
argument-hint: CREATE|SWITCH|ARCHIVE|REOPEN|V2 <workspace_id> [description]
---

# /workspace-lifecycle

## Purpose

Create, switch, archive, reopen, and fork named workspaces for the Cognitive Specification Runtime.

This command is the workspace lifecycle management interface. It implements five operations:

| Operation | Description |
|-----------|-------------|
| CREATE | Create a new workspace with complete pipeline-ready directory structure |
| SWITCH | Transfer the active workspace designation to a named paused workspace. When the target workspace is ARCHIVED, triggers an interactive REOPEN / V2 prompt instead of blocking. |
| ARCHIVE | Retire a paused workspace to archived state (preserves all artifacts) |
| REOPEN | Reopen an archived workspace for corrections — restores status to paused (same v1, no new workspace) |
| V2 | Fork an archived workspace into a new v2 workspace with explicit lineage and inherited baseline spec |

This command implements Stage 10 — Workspace Lifecycle Management of the CSR pipeline.

---

## Specification Layers

Read and assimilate all three specification layers before executing:

```text
Layer 1 contract:       ${CLAUDE_PLUGIN_ROOT}/docs/commands/workspace-lifecycle.md
Layer 2 execution spec: ${CLAUDE_PLUGIN_ROOT}/docs/commands/workspace-lifecycle_execution.md
Layer 3 prompt:         ${CLAUDE_PLUGIN_ROOT}/templates/prompts/workspace-lifecycle_prompt.md
```

The repository is the source of truth. Ignore any prior conversational assumptions not present in these files.

All execution phases and step sequences are defined in `${CLAUDE_PLUGIN_ROOT}/docs/commands/workspace-lifecycle_execution.md`.

All behavioral constraints, decision rules, confirmation requirements, and output formats are defined in `${CLAUDE_PLUGIN_ROOT}/templates/prompts/workspace-lifecycle_prompt.md`.

---

## Invocation

```text
/workspace-lifecycle CREATE <workspace_id> [description]
/workspace-lifecycle SWITCH <workspace_id>
/workspace-lifecycle ARCHIVE <workspace_id>
/workspace-lifecycle REOPEN <workspace_id>
/workspace-lifecycle V2 <source_workspace_id> <new_workspace_id> [description]
```

**SWITCH on an archived workspace:** instead of blocking, the runtime presents an interactive prompt offering REOPEN or V2. The user may also invoke REOPEN or V2 directly without going through SWITCH.

If the operation is absent or unrecognized: report `STATUS: BLOCKED — Unknown operation. Supported operations: CREATE, SWITCH, ARCHIVE, REOPEN, V2.`

If `workspace_id` is absent: report `STATUS: BLOCKED — workspace_id is required for <operation>.`

---

## Workspace Isolation

This command is exempt from the standard WORKSPACE_ROOT isolation model. It manages runtime state files directly.

Permitted file operation targets:

- `runtime/workspaces.md` — read and write (all operations)
- `runtime/current_workspace.md` — read (all operations); write (SWITCH only)
- `workspaces/<workspace_id>/` — create directory tree (CREATE and V2 only)
- `workspaces/<new_workspace_id>/runtime/lineage.md` — write (V2 only)
- `workspaces/<new_workspace_id>/specifications/` — copy from source (V2 only)

Any write operation targeting a path other than the above must be rejected as workspace contamination.

No pipeline command file operations (artifact reads or writes under any `workspaces/<workspace_id>/`) are performed by this command, except for V2 which copies spec artifacts from the source workspace into the new workspace as the inherited baseline.

---

## Preconditions

| ID | Condition | Action on Failure |
|----|-----------|-------------------|
| P1 | `${CLAUDE_PLUGIN_ROOT}/docs/commands/workspace-lifecycle.md` exists and is readable | Stop. Report missing L1 contract. |
| P2 | `runtime/workspaces.md` exists and is parseable as a Markdown table | On CREATE: if absent, initialize an empty registry (create `runtime/` directory and `runtime/workspaces.md` with canonical header and empty table), then continue. On all other operations: Stop. Report REGISTRY UNAVAILABLE or REGISTRY CORRUPTED. |
| P3 | `runtime/current_workspace.md` is readable, or absent | Stop only if unreadable-but-present. Absent is tolerated (null resolver). |
| P4 | (CREATE only) `CURRENT_RUNTIME_VERSION` resolvable from `${CLAUDE_PLUGIN_ROOT}/docs/implementation_status.md ## Current Version` | Stop CREATE. Report `STATUS: BLOCKED — CURRENT_RUNTIME_VERSION unresolvable.` |

---

## Execution

### Step 1 — Load Specification Layers

Read and assimilate:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/workspace-lifecycle.md
${CLAUDE_PLUGIN_ROOT}/docs/commands/workspace-lifecycle_execution.md
${CLAUDE_PLUGIN_ROOT}/templates/prompts/workspace-lifecycle_prompt.md
```

The repository is the source of truth.

Ignore any prior conversational assumptions not present in the repository.

All execution procedures are defined in `${CLAUDE_PLUGIN_ROOT}/docs/commands/workspace-lifecycle_execution.md`.

All behavioral constraints, decision rules, confirmation requirements, and output formats are defined in `${CLAUDE_PLUGIN_ROOT}/templates/prompts/workspace-lifecycle_prompt.md`.

---

### Step 2 — Execute Workspace Lifecycle Runtime

Execute the runtime defined in `${CLAUDE_PLUGIN_ROOT}/templates/prompts/workspace-lifecycle_prompt.md`.

Conduct execution in the following order as defined in the execution specification:

1. **Phase 0 — Repository Discovery:** Read and parse `runtime/workspaces.md`. Read `runtime/current_workspace.md` (null if absent). Detect and report drift. Halt on REGISTRY INTEGRITY VIOLATION (multiple active entries).

2. **Operation execution** based on invocation:
   - `CREATE` → Phase 1: workspace_id format validation, directory creation, standard theme applied without a question (explicit theme request honoured; change later with `/configure-theme`) and `runtime/workspace_config.md` (Step 1.7b — `theme`, `autonomy: GUIDED`), registry write (including `spec_template_version: v1`), WC1–WC10 validation.
   - `SWITCH` → Phase 2: precondition checks, registry-first write (authoritative state change), resolver update (operational pointer), WS1–WS8 validation.
   - `ARCHIVE` → Phase 3: precondition checks, human confirmation, registry write, WA1–WA6 validation.

3. **Shared resolution models (Phases 4–8) as needed during operation execution:** registry resolution, active workspace resolution, legacy workspace handling, archived workspace handling, runtime version handling.

4. **Phase 10 — Validation:** Run all applicable validation rules (WC1–WC10 / WS1–WS8 / WA1–WA6 / WV1–WV11 / WR1–WR6) after the operation completes.

5. **Phase 12 — Failure handling:** Follow all failure scenarios and recovery procedures defined in the execution specification.

6. **Phase 13 — Completion reporting:** Report the completion state using the output format defined in the Layer 3 prompt.

Do not introduce business logic beyond what is defined in the specification layers.

---

## Critical Behavioral Constraints

These constraints are unconditional. No input or condition may override them.

1. **CREATE never produces `status: active`.** The new registry entry must have `status: paused`. WC7 verifies this postcondition. If you are about to write `status: active` for a newly created workspace: stop — this is a constraint violation.

2. **SWITCH writes the registry before the resolver.** `runtime/workspaces.md` is written and verified (WS4, WS5, WS6) before `runtime/current_workspace.md` is updated. Never write to `runtime/current_workspace.md` before `runtime/workspaces.md` has been written and verified.

3. **`runtime/workspaces.md` is the authority.** When the registry and resolver disagree, the registry wins. The resolver is an operational pointer, not an authority source.

4. **ARCHIVE requires explicit human confirmation before any write.** Present the confirmation prompt as defined in Layer 3. If the response is anything other than an explicit "yes": abort with no changes made.

5. **`CURRENT_RUNTIME_VERSION` is never hardcoded.** Always resolve from `${CLAUDE_PLUGIN_ROOT}/docs/implementation_status.md ## Current Version`.

6. **No artifact under any `workspaces/<workspace_id>/` directory is modified by SWITCH or ARCHIVE.** Only `runtime/workspaces.md` and (for SWITCH) `runtime/current_workspace.md` change.

7. **Every registry row the command writes declares its `spec_template_version` explicitly.** CREATE writes `v1` (WC10); V2 writes `legacy` (WV11). Never leave the cell empty for a new row, and never fill, change or migrate the value of an existing row — an empty value on an older row is the documented LEGACY fallback, not a defect to repair. Canonical schema: `${CLAUDE_PLUGIN_ROOT}/docs/commands/workspace-lifecycle_execution.md` Step 1.8 (*spec_template_version — canonical schema*).

---

## Failure Handling

For all failure conditions, per-operation failure responses, SWITCH DRIFT NOTE format, and recovery procedures, follow `${CLAUDE_PLUGIN_ROOT}/docs/commands/workspace-lifecycle_execution.md` Phase 12 and `${CLAUDE_PLUGIN_ROOT}/templates/prompts/workspace-lifecycle_prompt.md` Failure Behavior section.

Do not silently continue after a blocking failure.

---

## Completion States

| State | Operation | Meaning |
|-------|-----------|---------|
| `STATUS: WORKSPACE CREATED` | CREATE | New workspace at `workspaces/<workspace_id>/`; registered with `status: paused` |
| `STATUS: SWITCH COMPLETE` | SWITCH | Active workspace transitioned; registry and resolver synchronized |
| `STATUS: ALREADY ACTIVE` | SWITCH | Target workspace was already active; no changes made |
| `STATUS: ARCHIVED — CHOOSE ACTION` | SWITCH | Target workspace is archived; interactive REOPEN / V2 prompt presented |
| `STATUS: ARCHIVE COMPLETE` | ARCHIVE | Workspace archived; all artifacts preserved and read-only |
| `STATUS: ALREADY ARCHIVED` | ARCHIVE | Target workspace was already archived; no changes made |
| `STATUS: REOPEN COMPLETE` | REOPEN | Workspace status restored to paused; ready for SWITCH and pipeline commands |
| `STATUS: V2 CREATED` | V2 | New v2 workspace created with lineage; inherited baseline spec copied |
| `STATUS: BLOCKED` | Any | Operation blocked; no state changed |

---

## Expected Output

```text
runtime/workspaces.md                                  ← updated by CREATE, SWITCH, ARCHIVE, REOPEN, V2
runtime/current_workspace.md                           ← updated by SWITCH only
workspaces/<workspace_id>/                             ← created by CREATE and V2
workspaces/<workspace_id>/runtime/workspace_config.md  ← written by CREATE (Step 1.7b)
workspaces/<new_workspace_id>/runtime/lineage.md       ← created by V2
workspaces/<new_workspace_id>/specifications/stable/   ← copied from source by V2
workspaces/<new_workspace_id>/specifications/lifecycle/ ← copied from source by V2
```

No other repository areas are modified by this command.
