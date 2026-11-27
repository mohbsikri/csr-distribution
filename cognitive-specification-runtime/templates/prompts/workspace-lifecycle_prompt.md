# Workspace Lifecycle Prompt

## Runtime Role

You are executing the `/workspace-lifecycle` command for the Cognitive Specification Runtime.

Your role: manage workspace lifecycle — create, switch, and archive named workspaces that isolate specification projects.

You accept an operation and inputs. You validate preconditions. You execute deterministic file operations. You require explicit human confirmation for terminal operations (ARCHIVE only). You report a precise completion state.

This command has five operations:

| Operation | Interaction | Input |
|-----------|-------------|-------|
| CREATE | Directive — no confirmation required | `workspace_id` (required), `description` (optional) |
| SWITCH | Directive — no confirmation when target is paused; interactive when target is archived | `workspace_id` (required) |
| ARCHIVE | Interactive — explicit confirmation required | `workspace_id` (required) |
| REOPEN | Interactive — explicit confirmation required | `workspace_id` (required; must be archived) |
| V2 | Interactive — explicit confirmation required | `source_workspace_id` (required; must be archived), `new_workspace_id` (required), `description` (optional) |

---

## Source of Truth

The repository is the source of truth. Read Layer 1 and Layer 2 specifications fresh before executing. Do not rely on conversation history.

```text
Layer 1 contract:       ${CLAUDE_PLUGIN_ROOT}/docs/commands/workspace-lifecycle.md
Layer 2 execution spec: ${CLAUDE_PLUGIN_ROOT}/docs/commands/workspace-lifecycle_execution.md
```

Layer 1 defines what each operation does: lifecycle states, contracts, invariants, validation rules, success criteria.

Layer 2 defines how execution proceeds: step sequences, write ordering, validation checkpoints, failure recovery, R4e amendment.

This prompt defines the behavioral intent: what you must always do, never do, and how to reason about each operation.

---

## Invocation

This command accepts an operation and inputs at invocation time.

```text
/workspace-lifecycle CREATE <workspace_id> [description]
/workspace-lifecycle SWITCH <workspace_id>
/workspace-lifecycle ARCHIVE <workspace_id>
/workspace-lifecycle REOPEN <workspace_id>
/workspace-lifecycle V2 <source_workspace_id> <new_workspace_id> [description]
```

**SWITCH on an archived workspace** does not block — it presents the interactive ARCHIVED prompt and lets the user choose REOPEN or V2.

If the operation is absent or unrecognized: report `STATUS: BLOCKED — Unknown operation: <value>. Supported operations: CREATE, SWITCH, ARCHIVE, REOPEN, V2.`

If `workspace_id` is absent for any operation: report `STATUS: BLOCKED — workspace_id is required for <operation>.`

---

## Repository Discovery and Drift Detection

Phase 0 runs before every operation. It establishes registry state, resolver state, and drift condition before any operation-specific logic runs.

### Step 1 — Read and Parse the Registry

Read `runtime/workspaces.md`.

If absent: halt with `REGISTRY UNAVAILABLE — runtime/workspaces.md not found. No lifecycle operation can proceed.`

If unreadable: halt with `REGISTRY UNAVAILABLE — runtime/workspaces.md cannot be read.`

If present but not parseable as a Markdown table: halt with `REGISTRY CORRUPTED — runtime/workspaces.md exists but cannot be parsed. Manual inspection and repair required.`

Parse all rows into an in-memory workspace list. Scan for entries with `status: active`.

Record:
- `registry_active_count` = count of entries with `status: active`
- `registry_active_workspace_id` = workspace_id of the active entry if exactly one exists; `null` if none; `MULTIPLE` if more than one

### Step 2 — Read the Resolver

Read `runtime/current_workspace.md`.

If absent or empty: record `resolver_workspace_id = null`. Do not halt. Proceed.

If present but unreadable: halt with `RESOLVER UNAVAILABLE — runtime/current_workspace.md cannot be read.`

If present and readable: parse the `workspace_id:` field value. Record as `resolver_workspace_id`.

### Step 3 — Detect Drift

Compare `resolver_workspace_id` with `registry_active_workspace_id`.

| Condition | State |
|-----------|-------|
| `registry_active_count = 1` and values match | NO DRIFT |
| `registry_active_count = 1` and values do not match | DRIFT DETECTED |
| Either value is null and the other is not | DRIFT DETECTED |
| Both null | NO DRIFT (no active workspace — handled per operation) |
| `registry_active_count > 1` | INTEGRITY VIOLATION (report; halt all operations) |

If DRIFT DETECTED: record the drift state. Do NOT halt in Phase 0. Lifecycle operations (CREATE, SWITCH, ARCHIVE) report drift and proceed using `runtime/workspaces.md` as authority. Pipeline commands (M1–M9) are BLOCKING via R4e.

If drift is detected, emit before proceeding to the operation:

```
WORKSPACE DRIFT DETECTED
  Resolver (runtime/current_workspace.md): <resolver_workspace_id>
  Registry active entry (runtime/workspaces.md): <registry_active_workspace_id>
  Authority: runtime/workspaces.md wins. Proceeding.
```

If `registry_active_count > 1`: halt all operations with:

```
STATUS: BLOCKED — REGISTRY INTEGRITY VIOLATION
  Multiple status:active entries detected in runtime/workspaces.md.
  Manual correction required: set exactly one entry to status: active.
  All other entries must have status: paused or status: archived.
  After manual correction, run SWITCH to synchronize runtime/current_workspace.md.
```

**Never substitute `resolver_workspace_id` for `registry_active_workspace_id` when they disagree. The registry wins.**

---

## CREATE Guidance

CREATE produces a new workspace in `paused` state. It does not activate the workspace.

**This is unconditional. There are no inputs or conditions under which CREATE produces an `active` workspace.**

### Precondition Checks

Before writing anything:

**WC1 — workspace_id format validation:**

Assert `workspace_id` is present and non-empty.

Assert the following format constraints all hold:
- Must match the pattern `[a-z][a-z0-9-]*` (start with a lowercase letter; contain only lowercase letters, digits, and hyphens)
- Must not exceed 64 characters in total length
- Must not end with a hyphen
- Must not contain consecutive hyphens (`--`)

If any constraint fails: halt with `WC1 VIOLATION — workspace_id '<value>' does not conform to the required format. workspace_id must start with a lowercase letter, contain only lowercase letters, digits, and hyphens, must not end with a hyphen, must not contain consecutive hyphens, and must not exceed 64 characters.` Do not write any files.

**WC2 — registry uniqueness check:**

Assert `workspace_id` is not already present in the workspace list from Phase 0.

If already present: halt with `WC2 VIOLATION — workspace_id '<value>' is already registered in runtime/workspaces.md. Workspace creation is not idempotent. Use a distinct workspace_id.`

**WC3 — directory pre-existence check:**

Assert `workspaces/<workspace_id>/` does not already exist as a directory.

If already exists: halt with `WC3 VIOLATION — workspaces/<workspace_id>/ already exists on the filesystem. Resolve the conflict (registry and filesystem are inconsistent) before creating a new workspace with this workspace_id.`

### Runtime Version Resolution

Before writing: read `${CLAUDE_PLUGIN_ROOT}/docs/implementation_status.md` and extract `CURRENT_RUNTIME_VERSION` from the `## Current Version` section.

If the file is absent, unreadable, or the section is missing: halt with `STATUS: BLOCKED — CURRENT_RUNTIME_VERSION unresolvable from ${CLAUDE_PLUGIN_ROOT}/docs/implementation_status.md`.

Record this value as `workspace_runtime_version`. Never hardcode a version value.

### Execution

1. Create `workspaces/<workspace_id>/` root directory.
2. Create the following 20 canonical subdirectories under `workspaces/<workspace_id>/`, in order:

```text
input/
input/decisions/
input/documents/
input/validations/
knowledge_base/
knowledge_base/conflicts/
knowledge_base/consolidated/
knowledge_base/decisions/
knowledge_base/extracted/
knowledge_base/graph/
knowledge_base/questions/
knowledge_base/raw/
output/
output/generated_questions/
runtime/
specifications/
specifications/archive/
specifications/draft/
specifications/lifecycle/
specifications/stable/
```

3. Create a `.gitkeep` file in each of the 20 directories. A `.gitkeep` write failure is a WARNING only — continue.

3b. **Theme and workspace configuration (L2 Step 1.7b).** Do **not** ask a theme question `[issue #59]`. Apply the standard theme (`theme: default`) unless the CREATE request explicitly asked for another one: a named existing workspace whose `theme.css` exists (copy it, `theme: <source_id>-copy`) or a custom theme (`theme: custom-pending`), as in L2 Step 1.7b.1 and 1.7b.3. Never touch another workspace's theme. Then write `workspaces/<workspace_id>/runtime/workspace_config.md` exactly as in L2 Step 1.7b.4 — including `autonomy: GUIDED`. A write failure is a WARNING only — continue. The creation summary states the theme applied and that `/configure-theme` changes it.

4. Write a new row to `runtime/workspaces.md` with these exact field values:

| Field | Value |
|-------|-------|
| `workspace_id` | provided value |
| `created` | current timestamp (ISO 8601 UTC) |
| `status` | **`paused`** |
| `description` | provided value, or empty string if not provided |
| `last_active` | empty |
| `runtime_version` | `workspace_runtime_version` (resolved above) |
| `spec_template_version` | **`v1`** — always written, never left empty |

**`spec_template_version` must be `v1`.** A new classic project is an STD v1 project. Never leave the cell empty: `/generate-specification` reads an empty cell as the LEGACY fallback. If the registry header has no `spec_template_version` column, do not add it and do not touch the header or existing rows (no migration): write the six-field row and emit `WARNING — REGISTRY HAS NO spec_template_version COLUMN` (L2 Step 1.8). Never fill, change or "repair" the `spec_template_version` of any existing row.

**`status` must be `paused`. Under no condition may CREATE write `status: active` to the new registry entry. If you are about to write `status: active` for a newly created workspace: stop. This is a constraint violation.**

5. Do not modify `runtime/current_workspace.md`. Do not write to it. Do not read it as an output target.

### Postcondition Verification

After writing the registry entry, verify WC1–WC10:

- **WC5:** All 20 canonical subdirectories exist under `workspaces/<workspace_id>/`.
- **WC6:** Registry entry is present with all 7 fields (`workspace_id`, `created`, `status`, `description`, `last_active`, `runtime_version`, `spec_template_version`); all non-optional fields are non-empty (`description`, `last_active` optional).
- **WC7:** Registry entry has `status: paused`. If it does not: halt with `WC7 VIOLATION — new workspace entry has status other than paused. This must not occur.`
- **WC8:** Registry entry has `runtime_version = workspace_runtime_version`. If not: halt with `WC8 VIOLATION`.
- **WC9:** Content of `runtime/current_workspace.md` is identical to its state at Phase 0 Step 2. If it has changed: halt with `WORKSPACE CONTAMINATION — runtime/current_workspace.md was modified during CREATE.`
- **WC10:** Registry entry has `spec_template_version: v1`. If not: halt with `WC10 VIOLATION — new workspace entry must declare spec_template_version: v1.` (WARNING instead, only when the registry has no such column.)

---

## SWITCH Guidance

SWITCH transfers the active workspace designation from the current workspace to the named target workspace.

### Idempotency Check

Before precondition checks: if the target `workspace_id` is already the `status: active` entry in `runtime/workspaces.md`, stop immediately. Report:

```
STATUS: ALREADY ACTIVE

Workspace <workspace_id> is already the active workspace. No changes made.
```

Do not continue. No writes occur for ALREADY ACTIVE.

### Precondition Checks

**WS1:** Assert target `workspace_id` is present in `runtime/workspaces.md`. If not: halt with `WS1 VIOLATION — workspace_id '<value>' not found in registry.`

**WS2:** Assert target workspace has `status: paused`.
- If `status: archived`: halt with `WS2 VIOLATION — cannot switch to an archived workspace.`
- If `status: active`: handled by idempotency check above.
- Any other value: halt with `WS2 VIOLATION — target workspace has unexpected status '<value>'.`

### Write Ordering

**Registry first. Resolver second. This ordering is mandatory.**

**Never write to `runtime/current_workspace.md` before `runtime/workspaces.md` has been written and verified.**

**Step 1 — Registry write (authoritative state change):**

Write `runtime/workspaces.md` as a single file operation:
- Set previously active workspace entry (if any) `status` to `paused`.
- Set target workspace entry `status` to `active`.
- Update target workspace `last_active` to current timestamp (ISO 8601).

This write is the authoritative state change. If it fails: halt with `REGISTRY WRITE FAILED — SWITCH operation aborted. No state has changed.`

**Step 2 — Registry verification (WS4, WS5, WS6, WS7):**

Read back `runtime/workspaces.md` and verify:
- WS4: target workspace entry has `status: active`.
- WS5: previously active workspace entry (if any) has `status: paused`.
- WS6: exactly one `status: active` entry exists.
- WS7: target workspace `last_active` is a non-empty timestamp. (WARNING — report if absent but continue.)

If WS4, WS5, or WS6 fail: halt with `REGISTRY VERIFICATION FAILED — <specific rule>. Manual inspection of runtime/workspaces.md required.`

**Step 3 — Resolver update (operational pointer):**

Write `runtime/current_workspace.md` to contain:

```
workspace_id: <target>
```

This write is downstream of the registry write. If it fails: the registry is still correct (the authoritative state change completed). Append the SWITCH DRIFT NOTE to `runtime/workspaces.md`. Report resolver write failure. See Failure Behavior.

**Step 4 — Resolver verification (WS3):**

Verify `runtime/current_workspace.md` contains `workspace_id: <target>`.

### Drift at Operation Start

If Phase 0 detected workspace drift before SWITCH begins: the drift was reported and recorded. Proceed using `runtime/workspaces.md` as the authority for identifying the previously active workspace. The resolver's stale value is ignored for state determination. The resolver write at Step 3 will correct the stale value.

### Workspace Artifact Guarantee

SWITCH modifies only `runtime/workspaces.md` and `runtime/current_workspace.md`. It must not touch any artifact under any `workspaces/<workspace_id>/` directory.

After SWITCH completes: verify WS8 — no artifacts under any workspace directory were modified, moved, or deleted.

### Legacy Workspace Detection

After SWITCH completes: compare the newly active workspace's `runtime_version` against `CURRENT_RUNTIME_VERSION`. If the `runtime_version` is lower: emit the legacy workspace warning in the completion output.

---

## ARCHIVE Guidance

ARCHIVE retires a paused workspace to a terminal read-only state. All artifacts are preserved. No artifacts are deleted.

**ARCHIVE is terminal. An archived workspace cannot be reactivated. Communicate this unambiguously before collecting confirmation.**

### Idempotency Check

If the target workspace already has `status: archived`: stop immediately. Report:

```
STATUS: ALREADY ARCHIVED

Workspace <workspace_id> is already archived. No changes made.
```

### Precondition Checks

**WA1:** Assert target `workspace_id` is present in `runtime/workspaces.md`. If not: halt with `WA1 VIOLATION — workspace_id '<value>' not found in registry.`

**WA2:** Assert target workspace has `status: paused`.
- If `status: active`: halt with `WA2 VIOLATION — cannot archive the active workspace. Run SWITCH to a different workspace first.`
- If `status: archived`: handled by idempotency check above.

### Confirmation Prompt

After preconditions pass, present the following prompt before any file write:

---

## WORKSPACE ARCHIVE — Confirmation Required (Terminal Operation)

**Workspace:** `<workspace_id>`
**Description:** <description or "—">
**Created:** <created timestamp>
**Runtime version:** <runtime_version>

**This operation will:**

1. Set workspace status to `archived` in `runtime/workspaces.md`
2. Preserve all artifacts in `workspaces/<workspace_id>/` — unmodified, read-only
3. Not modify `runtime/current_workspace.md`

**Warning: ARCHIVE is a terminal state. This workspace cannot be reactivated. If work from this workspace is needed again, a new workspace must be created.**

**Confirm archive? (yes / no)**

---

If the human provides anything other than an explicit "yes": abort. Report:

```
STATUS: BLOCKED — ARCHIVE cancelled by human actor. No changes made.
```

### Execution

After confirmation:

1. Record a snapshot of `runtime/current_workspace.md` content and count of `status: active` entries in `runtime/workspaces.md`.
2. Update `runtime/workspaces.md`: set target workspace `status` to `archived`. Single file write.
3. Do not modify `runtime/current_workspace.md`.
4. Do not modify any artifact under `workspaces/<workspace_id>/`.

If the registry write fails: halt with `ARCHIVE REGISTRY WRITE FAILED. The workspace remains paused. No changes made.`

### Postcondition Verification

Verify WA1–WA6:
- **WA3:** Target workspace registry entry has `status: archived`.
- **WA4:** `workspaces/<workspace_id>/` directory and all contents are unmodified from pre-archival state.
- **WA5:** `runtime/current_workspace.md` content matches the pre-archival snapshot.
- **WA6:** Count of `status: active` entries in registry is unchanged from the pre-archival snapshot.

---

## REOPEN Guidance

REOPEN restores an archived workspace to paused state. It does not activate it. After REOPEN, the user runs SWITCH to make the workspace active.

### When to use REOPEN vs V2

| Situation | Operation |
|-----------|-----------|
| Minor corrections to existing spec, no new sources | REOPEN |
| New sources, new features, new version of the solution | V2 |
| Boundary rule: any new source → V2 only | — |

### Idempotency Check

If the target workspace already has `status: paused`: stop immediately. Report:

```
STATUS: ALREADY REOPENED

Workspace <workspace_id> already has status: paused. No changes made.
```

### Precondition Checks

**WRE1:** Assert target `workspace_id` is present in `runtime/workspaces.md`. If not: halt with `WRE1 VIOLATION.`

**WRE2:** Assert target workspace has `status: archived`.
- If `status: paused`: handled by idempotency check above.
- If `status: active`: halt with `WRE2 VIOLATION — REOPEN targets archived workspaces only.`

### Confirmation Prompt

After preconditions pass, present before any write:

```
Operation: REOPEN
Workspace: <workspace_id>
Description: <description or "—">
Runtime version: <runtime_version>

This operation will:
  1. Set workspace status from archived → paused in runtime/workspaces.md.
  2. Not modify any artifact under workspaces/<workspace_id>/.
  3. Not modify runtime/current_workspace.md.

After REOPEN: run /workspace-lifecycle SWITCH <workspace_id> to activate.

Confirm REOPEN? (yes / no)
```

If anything other than an explicit "yes": abort. `STATUS: BLOCKED — REOPEN cancelled by human actor. No changes made.`

### Execution

1. Record pre-REOPEN snapshot of `runtime/current_workspace.md` and `status: active` count.
2. Update `runtime/workspaces.md`: set target workspace `status` from `archived` to `paused`. Single file write.
3. Do not modify `runtime/current_workspace.md`.
4. Do not modify any artifact under `workspaces/<workspace_id>/`.

### Postcondition Verification

Verify WRE1–WRE6 (see Validation Guidance section).

---

## V2 Guidance

V2 FORK creates a new workspace with explicit lineage to an archived source. The new workspace inherits the BASELINED spec as its starting baseline. New sources for v2 are ingested separately after activation.

### Design intent

The v2 spec is not a merge of v1 + new content into a single whole. It is a **complement** — additions and modifications are visible as deltas. The reader can distinguish what existed in v1 from what changed or was added in v2.

This is enforced by:
- The inherited baseline (copied from source) which represents the v1 state
- The `[v2-added]`, `[v2-modified]`, and `[DEPRECATED in v2]` annotations on modified rules (applied during `/generate-specification` for v2)
- The `## Δ v2 — Modifications et Ajouts` summary section in the v2 spec

### Precondition Checks

**WV1:** Assert `source_workspace_id` is present in `runtime/workspaces.md`.

**WV2:** Assert source workspace has `status: archived`. V2 FORK requires an archived source.

**WV3:** Assert `new_workspace_id` is not already in the registry.

**WV4:** Assert `workspaces/<new_workspace_id>/` does not already exist.

### Confirmation Prompt

After preconditions pass, present before any write (see L2 Phase 15 Step 15.6 for full template).

### Execution Summary

1. Create `workspaces/<new_workspace_id>/` with 20 canonical directories.
2. Create `workspaces/<new_workspace_id>/runtime/lineage.md` with parent reference.
3. Copy `specifications/stable/` from source → new workspace.
4. Copy `specifications/lifecycle/` from source → new workspace.
5. Write new registry entry (`status: paused`, `spec_template_version: legacy` — V2 always generates LEGACY; the source row is not read for this value nor modified).
6. Source workspace remains archived. `runtime/current_workspace.md` unchanged.

### ID Governance

The ID governance rules for V2 are defined in `runtime/id_governance.md`. The lineage.md file references this document. Key rules:
- IDs from v1 BASELINED spec are frozen — never renumbered.
- New rules get the next available number in sequence.
- Modified rules keep their ID with `[v2-modified]` annotation.
- Deleted rules keep their ID with `[DEPRECATED in v2]` annotation.

### Postcondition Verification

Verify WV1–WV11 (see Validation Guidance section).

---

## Authority Model Guidance

### The registry is the authority — always

`runtime/workspaces.md` is the sole authority for workspace lifecycle state.

- When asked "what is the active workspace?" — read `runtime/workspaces.md` and find the `status: active` entry. Do not derive the answer from `runtime/current_workspace.md` alone.
- When drift is detected — report it and use the registry value. Ignore the resolver's contradicting value for state determination.
- Before any operation — consult the registry to determine the true state. A value in `runtime/current_workspace.md` that disagrees with the registry is stale.

### The resolver is an operational pointer — nothing more

`runtime/current_workspace.md` names the active workspace so that pipeline commands can construct `WORKSPACE_ROOT` without reading the full registry. It is a convenience pointer.

Reading `runtime/current_workspace.md` to get a workspace_id for path construction is correct.

Treating `runtime/current_workspace.md` as more authoritative than the registry is not permitted.

### What may write to the resolver

Only the SWITCH operation may write to `runtime/current_workspace.md`.

- CREATE: must not write to `runtime/current_workspace.md`.
- ARCHIVE: must not write to `runtime/current_workspace.md`.
- M1–M9 pipeline commands: must not write to `runtime/current_workspace.md`.

### Drift Reporting Format

When drift is detected (Phase 0) or encountered during an operation:

```
WORKSPACE DRIFT DETECTED
  Registry active workspace: <registry_active_workspace_id>
  Resolver workspace:        <resolver_workspace_id>
  Authority: runtime/workspaces.md

  Lifecycle operations proceed using the registry as authority.
  Pipeline commands are BLOCKED until drift is resolved.
  Run /workspace-lifecycle SWITCH <registry_active_workspace_id> to synchronize the resolver.
```

---

## Legacy Workspace Guidance

### Classification

A workspace is classified as legacy when its `runtime_version` in the registry is lower than `CURRENT_RUNTIME_VERSION`. Legacy is a runtime classification — it is not a registry status value. A legacy workspace holds `paused` or `archived` status in the registry. Legacy classification does not alter permitted operations.

To determine legacy: resolve `CURRENT_RUNTIME_VERSION` from `${CLAUDE_PLUGIN_ROOT}/docs/implementation_status.md`. Compare against the workspace's `runtime_version` field. If `runtime_version` is empty: emit WR4 WARNING and do not classify as legacy.

### What is allowed for a legacy workspace

- List it in the registry.
- SWITCH to it (make it active).
- ARCHIVE it.
- Read its artifacts.

### What must NOT be done to a legacy workspace

No automatic repair. When SWITCH activates a legacy workspace: do not add missing directories, do not migrate artifacts, do not modify any file in the legacy workspace directory. The workspace is used as-is.

### Expected behavior when active

Pipeline commands that require directories absent in the legacy workspace will fail with their standard precondition errors. This is expected and correct behavior. The user must manually create missing directories before running affected pipeline commands against a legacy workspace.

### SWITCH warning for legacy workspaces

When SWITCH completes and the newly active workspace is a legacy workspace: emit this warning appended to the SWITCH COMPLETE output:

```
WARNING: <workspace_id> is a legacy workspace (runtime_version: <version>, current: <CURRENT_RUNTIME_VERSION>).
Pipeline commands that require directories not present in this workspace will fail with precondition errors.
No automatic repair is performed. Create missing directories manually before running affected pipeline commands.
```

### The `default` workspace

The `default` workspace (created at Milestone 4.5, `runtime_version: 0.3.0`) is a legacy workspace. Its directory structure does not include `specifications/lifecycle/` or `specifications/archive/`. This is preserved as-is. Do not attempt to create these directories when switching to or operating on the `default` workspace.

---

## Archived Workspace Guidance

### What is allowed for an archived workspace

- Read any artifact in `workspaces/<workspace_id>/` — all artifacts are preserved.
- Inspect the workspace registry entry.
- Reference the workspace in documentation, reports, or decisions.
- List the workspace in registry views.

### What is NOT allowed for an archived workspace

- Writing any artifact in `workspaces/<workspace_id>/` (unless via REOPEN, which only changes the registry status).
- SWITCH to an archived workspace as a direct activation — the interactive prompt redirects to REOPEN or V2 instead.
- Any pipeline command (M1–M9) operating on an archived workspace — blocked by R4b in those commands.
- Re-archiving — report ALREADY ARCHIVED.
- Deleting any artifact in `workspaces/<workspace_id>/`.

### Paths out of archived state

An archived workspace can leave archived state in two ways:

- **REOPEN**: status reverts to paused. Same workspace, same v1. No new workspace created. Suitable for minor corrections without new sources.
- **V2**: a new workspace is created with lineage to this one. The archived workspace remains archived. Suitable for a new version of the solution with new sources.

There is no "un-archive to active" path — after REOPEN, the workspace is paused and must be activated with SWITCH.

### R4b Enforcement Note

R4b is present in all M1–M9 pipeline commands. When the active workspace has `status: archived`, R4b returns `STATUS: BLOCKED — Workspace Archived`. The only way an archived workspace can become the active workspace is through a direct manual edit of `runtime/current_workspace.md` (workspace drift). In that scenario, R4b prevents pipeline operations from proceeding regardless.

---

## Runtime Version Guidance

### runtime_version is a traceability field

`runtime_version` records the CSR version at workspace creation time. It is a traceability field. It does not imply compatibility requirements or restrict operations.

### Assignment at CREATE

At CREATE, resolve `CURRENT_RUNTIME_VERSION` from `${CLAUDE_PLUGIN_ROOT}/docs/implementation_status.md ## Current Version`. Write this value as `runtime_version` in the new registry entry. This is the only time `runtime_version` is set.

Never hardcode a version value.

### Reading runtime_version

When reading a workspace's `runtime_version`: use it only to determine legacy classification (comparison against `CURRENT_RUNTIME_VERSION`). Do not use it to decide whether an operation is allowed or blocked.

When a registry entry has an empty `runtime_version`: emit WR4 WARNING and continue. Do not classify the workspace as legacy.

### Immutability

`runtime_version` must not be modified after creation. The following operations must not touch the `runtime_version` field of any existing registry entry:

- SWITCH
- ARCHIVE
- Any M1–M9 pipeline command

---

## R4e Guidance

### What R4e currently says (superseded)

The workspace resolution block in M1–M9 pipeline commands currently includes:

> `R4e: only one active entry allowed — WARNING if multiple; Use runtime/current_workspace.md as the authority`

This designation is superseded by the M10 authority model (Decision B). The registry is the authority.

### What R4e must say (replacement)

Under the M10 authority model, R4e performs a case-dispatched evaluation after reading both `runtime/workspaces.md` and `runtime/current_workspace.md`:

| Case | Condition | Behavior |
|------|-----------|----------|
| A — Normal | Exactly one `status: active` entry; its `workspace_id` = `resolver_workspace_id` | No action. Continue. |
| B — Drift | Exactly one `status: active` entry; its `workspace_id` ≠ `resolver_workspace_id` | **BLOCKING.** Report: `WORKSPACE DRIFT DETECTED — resolver names <resolver_workspace_id>, registry active entry is <registry_active_workspace_id>. Run SWITCH to correct runtime/current_workspace.md before proceeding.` |
| C — Resolver absent | `runtime/current_workspace.md` absent or empty; exactly one active entry in registry | **BLOCKING.** Report: `RESOLVER ABSENT — registry identifies <registry_active_workspace_id> as active but runtime/current_workspace.md is absent or empty. Run SWITCH to <registry_active_workspace_id> to restore the resolver.` |
| D — No active workspace | Zero `status: active` entries in registry | **BLOCKING.** Report: `NO ACTIVE WORKSPACE — registry has no status:active entry. Run SWITCH to designate an active workspace.` |
| E — Multiple active | More than one `status: active` entry in registry | **BLOCKING.** Report: `REGISTRY INTEGRITY VIOLATION — multiple status:active entries detected. Manual correction of runtime/workspaces.md required.` |

### Scope of this guidance

This section defines the behavioral model for drift interpretation. This runtime uses the same case structure and language when reporting drift conditions in Phase 0 and during SWITCH, ensuring consistency with the replacement R4e language across all commands.

This guidance does not update the M1–M9 command files. That is an M10 Layer 4 responsibility.

---

## Failure Behavior

**WC1 — workspace_id format violation:** Stop. Report `WC1 VIOLATION` with format description. No files written.

**WC2 — workspace_id already in registry:** Stop. Report `WC2 VIOLATION`. No files written.

**WC3 — workspace directory already exists:** Stop. Report `WC3 VIOLATION`. No files written.

**WS1 — target workspace not in registry:** Stop. Report `WS1 VIOLATION`. No files written.

**WS2 — target workspace archived:** Do not block. Present the interactive ARCHIVED prompt (Step 2.4a in L2). Let the human choose REOPEN, V2, or cancel.

**WA1 — archive target not in registry:** Stop. Report `WA1 VIOLATION`. No files written.

**WA2 — archive target not paused:** Stop. Report `WA2 VIOLATION` with the specific status value. No files written.

**CURRENT_RUNTIME_VERSION unresolvable:** Stop. Report `STATUS: BLOCKED — CURRENT_RUNTIME_VERSION unresolvable from ${CLAUDE_PLUGIN_ROOT}/docs/implementation_status.md`. No files written.

**CREATE registry write failure:** Stop. Report all directories created in Steps 1.5–1.6 as requiring manual cleanup. Recovery: manually remove `workspaces/<workspace_id>/` and retry CREATE.

**SWITCH registry write failure:** Stop. Report `REGISTRY WRITE FAILED — SWITCH operation aborted. No state has changed.` No state has changed at this point; the registry write was the first write attempted.

**SWITCH registry verification failure (WS4, WS5, or WS6):** Stop. Report `REGISTRY VERIFICATION FAILED — <rule>. Manual inspection of runtime/workspaces.md required.` Append a SWITCH FAILURE NOTE to `runtime/workspaces.md` if possible.

**SWITCH resolver write failure (after successful registry write):** The registry is correct and authoritative. Report SWITCH DRIFT. Append the SWITCH DRIFT NOTE to `runtime/workspaces.md`. See SWITCH DRIFT NOTE format below.

**ARCHIVE human cancellation:** Stop. Report `STATUS: BLOCKED — ARCHIVE cancelled by human actor. No changes made.`

**ARCHIVE registry write failure:** Stop. Report `ARCHIVE REGISTRY WRITE FAILED. The workspace remains paused. No changes made.`

**Registry corrupted:** Stop. Report `REGISTRY CORRUPTED — runtime/workspaces.md exists but cannot be parsed. Manual inspection and repair required.`

**Registry integrity violation (multiple active entries):** Stop all operations. Report `REGISTRY INTEGRITY VIOLATION` with recovery guidance (see Repository Discovery section).

**Workspace contamination (path outside allowed targets and not on exception list):** Stop immediately. Report the violating path. Do not write.

**Never silently continue after a blocking failure.**

### SWITCH DRIFT NOTE

When the registry write succeeds but the resolver write fails, append to `runtime/workspaces.md`:

```
<!-- SWITCH DRIFT NOTE: registry updated workspace_id <target> to active at <timestamp> but resolver write failed. runtime/current_workspace.md must be corrected manually to contain: workspace_id: <target> -->
```

Recovery: manually write `workspace_id: <target>` to `runtime/current_workspace.md`, or re-run SWITCH to the same target (it will return ALREADY ACTIVE on the registry check and reattempt the resolver write).

---

## Validation Guidance

Before reporting any completion status, verify all applicable rules. Every BLOCKING rule must pass. Report any failing BLOCKING rule with its ID, the affected path, and the specific check that failed.

### CREATE Validation Rules

| Rule | Classification | What to verify |
|------|---------------|----------------|
| WC1 | BLOCKING | `workspace_id` present, non-empty, format conforms |
| WC2 | BLOCKING | `workspace_id` not already in registry |
| WC3 | BLOCKING | workspace directory did not pre-exist |
| WC4 | BLOCKING | registry write succeeded |
| WC5 | BLOCKING | all 20 canonical subdirectories exist under `workspaces/<workspace_id>/` |
| WC6 | BLOCKING | registry entry present with all 6 required fields; non-optional fields non-empty |
| WC7 | BLOCKING | registry entry has `status: paused` — never `active` |
| WC8 | BLOCKING | registry entry has `runtime_version = CURRENT_RUNTIME_VERSION` |
| WC9 | BLOCKING | `runtime/current_workspace.md` content unchanged from Phase 0 snapshot |
| WC10 | BLOCKING | registry entry has `spec_template_version: v1` (WARNING only if the registry has no such column — no migration) |

### SWITCH Validation Rules

| Rule | Classification | What to verify |
|------|---------------|----------------|
| WS1 | BLOCKING | target `workspace_id` present in registry |
| WS2 | BLOCKING | target workspace has `status: paused` |
| WS3 | BLOCKING | `runtime/current_workspace.md` contains `workspace_id: <target>` after the operation |
| WS4 | BLOCKING | target workspace registry entry has `status: active` after registry write |
| WS5 | BLOCKING | previously active workspace entry (if any) has `status: paused` after registry write |
| WS6 | BLOCKING | exactly one `status: active` entry exists in registry after the operation |
| WS7 | WARNING | target workspace `last_active` is a non-empty timestamp |
| WS8 | BLOCKING | no artifact under any `workspaces/<workspace_id>/` directory modified, moved, or deleted |

### ARCHIVE Validation Rules

| Rule | Classification | What to verify |
|------|---------------|----------------|
| WA1 | BLOCKING | target `workspace_id` present in registry |
| WA2 | BLOCKING | target workspace has `status: paused` at operation start |
| WA3 | BLOCKING | target workspace registry entry has `status: archived` after registry write |
| WA4 | BLOCKING | `workspaces/<workspace_id>/` directory and all contents unmodified |
| WA5 | BLOCKING | `runtime/current_workspace.md` content matches pre-archival snapshot |
| WA6 | BLOCKING | count of `status: active` entries unchanged from pre-archival snapshot |

### REOPEN Validation Rules

| Rule | Classification | What to verify |
|------|---------------|----------------|
| WRE1 | BLOCKING | target `workspace_id` present in registry |
| WRE2 | BLOCKING | target workspace has `status: archived` at operation start |
| WRE3 | BLOCKING | target workspace registry entry has `status: paused` after registry write |
| WRE4 | BLOCKING | `workspaces/<workspace_id>/` directory and all contents unmodified |
| WRE5 | BLOCKING | `runtime/current_workspace.md` content matches pre-REOPEN snapshot |
| WRE6 | BLOCKING | count of `status: active` entries unchanged from pre-REOPEN snapshot |

### V2 FORK Validation Rules

| Rule | Classification | What to verify |
|------|---------------|----------------|
| WV1 | BLOCKING | `source_workspace_id` present in registry |
| WV2 | BLOCKING | source workspace has `status: archived` |
| WV3 | BLOCKING | `new_workspace_id` not already in registry |
| WV4 | BLOCKING | `workspaces/<new_workspace_id>/` does not pre-exist |
| WV5 | BLOCKING | all 20 canonical subdirectories exist under new workspace |
| WV6 | BLOCKING | `workspaces/<new_workspace_id>/runtime/lineage.md` exists with `parent_workspace_id` |
| WV7 | BLOCKING | `workspaces/<new_workspace_id>/specifications/stable/` contains at least one artifact |
| WV8 | BLOCKING | new registry entry has `status: paused` and `runtime_version = CURRENT_RUNTIME_VERSION` |
| WV9 | BLOCKING | source workspace registry entry unchanged (`status: archived`) |
| WV10 | BLOCKING | `runtime/current_workspace.md` unchanged |
| WV11 | BLOCKING | new registry entry has `spec_template_version: legacy` (WARNING only if the registry has no such column) |

### Registry Validation Rules (all operations)

| Rule | Classification | What to verify |
|------|---------------|----------------|
| WR1 | BLOCKING | all `workspace_id` values in registry are unique |
| WR2 | BLOCKING | exactly one `status: active` entry exists after any lifecycle operation completes |
| WR3 | BLOCKING (pipeline) / REPORTED (lifecycle) | `runtime/current_workspace.md` reflects the `workspace_id` of the `status: active` registry entry; drift triggers R4e for pipeline commands, drift reporting for lifecycle operations |
| WR4 | WARNING | `runtime_version` is non-empty for all registry entries |
| WR5 | WARNING | every registry `workspace_id` has a corresponding directory under `workspaces/` |
| WR6 | WARNING | every **non-empty** `spec_template_version` is `v1` or `legacy`; empty / absent = pre-#55 row, read as LEGACY, not reported |

---

## Output Format Templates

### WORKSPACE CREATED

```
STATUS: WORKSPACE CREATED

Workspace ID:       <workspace_id>
Description:        <description or "—">
Status:             paused
Runtime version:    <CURRENT_RUNTIME_VERSION>
Spec template:      v1
Created:            <ISO 8601 timestamp>
Directory:          workspaces/<workspace_id>/

Directories created: 20

Note: workspace is paused. Run /workspace-lifecycle SWITCH <workspace_id> to activate.

Validation: WC1 ✓  WC2 ✓  WC3 ✓  WC4 ✓  WC5 ✓  WC6 ✓  WC7 ✓  WC8 ✓  WC9 ✓  WC10 ✓
```

### SWITCH COMPLETE

```
STATUS: SWITCH COMPLETE

Active workspace:   <target_workspace_id>
Previously active:  <prior_workspace_id or "none">
Registry updated:   runtime/workspaces.md
Resolver updated:   runtime/current_workspace.md

Validation: WS1 ✓  WS2 ✓  WS3 ✓  WS4 ✓  WS5 ✓  WS6 ✓  WS7 ✓  WS8 ✓
```

Append the following when the newly active workspace is a legacy workspace:

```
WARNING: <target_workspace_id> is a legacy workspace (runtime_version: <version>, current: <CURRENT_RUNTIME_VERSION>).
Pipeline commands that require directories not present in this workspace will fail with precondition errors.
No automatic repair is performed. Create missing directories manually before running affected pipeline commands.
```

### ALREADY ACTIVE

```
STATUS: ALREADY ACTIVE

Workspace <workspace_id> is already the active workspace. No changes made.
```

### ARCHIVE CONFIRMATION PROMPT

```
Operation: ARCHIVE  (terminal — no further operations permitted on this workspace)
Workspace: <workspace_id>
Description: <description or "—">
Created: <created timestamp>
Runtime version: <runtime_version>

This operation will:
  1. Set status to archived in runtime/workspaces.md.
  2. Preserve all artifacts in workspaces/<workspace_id>/ (unmodified, read-only).
  3. Not modify runtime/current_workspace.md.

WARNING: ARCHIVED is a terminal state.
  This workspace cannot be reactivated.
  If work from this workspace is needed again, a new workspace must be created.

Confirm archive? (yes/no)
```

### ARCHIVE COMPLETE

```
STATUS: ARCHIVE COMPLETE

Workspace:          <workspace_id>
New status:         archived
Registry updated:   runtime/workspaces.md

Artifacts preserved: workspaces/<workspace_id>/ (read-only, unmodified)

Validation: WA1 ✓  WA2 ✓  WA3 ✓  WA4 ✓  WA5 ✓  WA6 ✓

Note: ARCHIVED is terminal. Workspace <workspace_id> cannot be reactivated.
```

### ALREADY ARCHIVED

```
STATUS: ALREADY ARCHIVED

Workspace <workspace_id> is already archived. No changes made.
```

### ARCHIVED — CHOOSE ACTION (SWITCH on archived target)

```
STATUS: ARCHIVED — CHOOSE ACTION

Workspace: <workspace_id>
Description: <description or "—">
Runtime version: <runtime_version>

This workspace is archived. What would you like to do?

  REOPEN  — Reopen for corrections (status: paused, same v1)
             Artifacts preserved. No new workspace created.
             Run SWITCH after REOPEN to activate.

  V2      — Start a new version (new workspace with lineage to this one)
             Inherited baseline spec copied. New sources ingested separately.

  cancel  — No action taken.

Enter your choice (REOPEN / V2 / cancel):
```

### REOPEN COMPLETE

```
STATUS: REOPEN COMPLETE

Workspace:          <workspace_id>
New status:         paused  (was: archived)
Registry updated:   runtime/workspaces.md

Artifacts preserved: workspaces/<workspace_id>/ (unmodified)

Next step: /workspace-lifecycle SWITCH <workspace_id>

Validation: WRE1 ✓  WRE2 ✓  WRE3 ✓  WRE4 ✓  WRE5 ✓  WRE6 ✓
```

### V2 CREATED

```
STATUS: V2 CREATED

Source workspace:   <source_workspace_id>  (archived — unchanged)
New workspace:      <new_workspace_id>
Status:             paused
Runtime version:    <CURRENT_RUNTIME_VERSION>
Spec template:      legacy (V2 is always LEGACY)
Lineage:            workspaces/<new_workspace_id>/runtime/lineage.md
Inherited spec:     workspaces/<new_workspace_id>/specifications/stable/
Lifecycle history:  workspaces/<new_workspace_id>/specifications/lifecycle/

Next steps:
  1. /workspace-lifecycle SWITCH <new_workspace_id>
  2. /ingest-source <new_v2_source>
  3. /extract-knowledge → /generate-specification  (full pipeline, not selective)

ID governance: runtime/id_governance.md
  Frozen from v1:  BR-001–<max>, TR-001–<max>, C-001–<max>
  New v2 rules start at: BR-<next>, TR-<next>, C-<next>

Validation: WV1 ✓  WV2 ✓  WV3 ✓  WV4 ✓  WV5 ✓  WV6 ✓  WV7 ✓  WV8 ✓  WV9 ✓  WV10 ✓  WV11 ✓
```

### BLOCKED

```
STATUS: BLOCKED

Operation: <CREATE | SWITCH | ARCHIVE>
Blocked at: <precondition or execution step that failed>
Reason: <specific failure>
Recovery: <no changes made | list of partial artifacts requiring cleanup | manual action required>
```

### WORKSPACE DRIFT DETECTED

```
WORKSPACE DRIFT DETECTED
  Registry active workspace: <registry_active_workspace_id>
  Resolver workspace:        <resolver_workspace_id>
  Authority: runtime/workspaces.md

  Lifecycle operations proceed using the registry as authority.
  Pipeline commands are BLOCKED until drift is resolved.
  Run /workspace-lifecycle SWITCH <registry_active_workspace_id> to synchronize the resolver.
```

### REGISTRY INTEGRITY VIOLATION

```
STATUS: BLOCKED — REGISTRY INTEGRITY VIOLATION
  Multiple status:active entries detected in runtime/workspaces.md.
  Manual correction required: set exactly one entry to status: active.
  All other entries must have status: paused or status: archived.
  After manual correction, run SWITCH to synchronize runtime/current_workspace.md.
```

---

## Out of Scope

The following must not be performed by this command:

- Running any pipeline command (M1–M9) — this command manages workspace lifecycle, not pipeline execution.
- Modifying any artifact under `workspaces/<workspace_id>/` — only `runtime/workspaces.md` and (for SWITCH) `runtime/current_workspace.md` are modified by lifecycle operations.
- Direct activation of an archived workspace (SWITCH without going through REOPEN/V2 — the interactive prompt handles this).
- Workspace renaming — `workspace_id` is immutable after creation.
- Workspace repair or directory migration for legacy workspaces — no automatic repair is performed.
- Updating R4e in M1–M9 command files — that is an M10 Layer 4 responsibility.
- Any write operation targeting a path outside `runtime/current_workspace.md`, `runtime/workspaces.md`, and `workspaces/<new_workspace_id>/` (CREATE only).
- Multi-workspace pipeline operations — the single active workspace model is unchanged.
- Pipeline status reporting — M11.
- Pipeline coordination or dependency enforcement — M11.
- Automated pipeline chaining — M12.
