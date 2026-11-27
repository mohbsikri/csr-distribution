# Workspace Lifecycle Runtime

## Purpose

Enable CSR to manage multiple specification projects natively through controlled lifecycle management of named workspaces.

Before this runtime: workspace infrastructure existed (Milestone 4.5) but workspace creation, switching, and archival were not supported as runtime operations. All projects required manual workspace configuration. A single workspace limited CSR to one active project context.

After this runtime: a named workspace can be created for any new specification project, the active workspace can be switched between projects, and completed workspaces can be archived. The full CSR pipeline (M1–M9) operates identically in any workspace created by this runtime.

This runtime implements Stage 10 — Workspace Lifecycle Management of the CSR pipeline.

---

## Definitions

**workspace** — A named, isolated environment under `workspaces/<workspace_id>/` containing all artifacts for a single specification project.

**workspace_id** — A unique identifier that is both the workspace's registry key and its directory name under `workspaces/`. Must be a non-empty string forming a valid directory name on the host filesystem. Must not contain path separators.

**active workspace** — The workspace whose registry entry in `runtime/workspaces.md` holds `status: active`. `runtime/current_workspace.md` reflects this designation for pipeline command consumption. The registry is the authority; the resolver is the pointer.

**WORKSPACE_ROOT** — The path `workspaces/<workspace_id>/` for the active workspace. Constructed by all pipeline commands from the active workspace resolver.

**workspace registry** — `runtime/workspaces.md` — the authoritative source of truth for all workspace lifecycle states, existence, and creation metadata.

**active workspace resolver** — `runtime/current_workspace.md` — an operational pointer that reflects the `status: active` workspace from `runtime/workspaces.md`. Consumed by pipeline commands to resolve `WORKSPACE_ROOT`. Not an authority source for workspace lifecycle state.

**legacy workspace** — A workspace whose `runtime_version` field is lower than the current CSR runtime version. Classification only; does not alter registry status. No automatic structural repair is performed on legacy workspaces.

---

## Supported Operations

| Operation | Precondition State | Description |
|-----------|-------------------|-------------|
| CREATE | (none — new workspace) | Create a named workspace with complete pipeline-ready directory structure |
| SWITCH | Target workspace is `paused` | Transition the active workspace; all subsequent pipeline commands operate on the new workspace |
| ARCHIVE | Target workspace is `paused` | Retire a workspace to terminal read-only state; artifacts preserved |

---

## Workspace Lifecycle Model

A workspace holds one of four formal lifecycle states at any time.

---

### active

**Meaning:** The workspace is currently active. All pipeline commands operate on this workspace. The active workspace resolver (`runtime/current_workspace.md`) must name this workspace_id.

**Entry:**
- Explicit SWITCH operation targeting this workspace.

**Allowed transitions:**

| Transition | Operation |
|------------|-----------|
| `active` → `paused` | SWITCH to a different workspace (this workspace becomes paused) |

**Invariants:**
- Exactly one workspace registry entry may hold `status: active` at any time after the first workspace has been activated.
- `runtime/current_workspace.md` must reflect the `workspace_id` of the `status: active` registry entry. When they disagree, `runtime/workspaces.md` is authoritative and `runtime/current_workspace.md` is stale. Any disagreement is workspace drift.
- A workspace enters `active` state only via an explicit SWITCH operation. No other operation — including CREATE — may produce or imply `active` status.
- An active workspace cannot be directly archived. The workspace must be paused first (via SWITCH to another workspace).

---

### paused

**Meaning:** The workspace is registered and structurally intact but not currently active. Pipeline commands do not operate on a paused workspace unless it is first made active.

**Entry:**
- CREATE operation. All new workspaces are always created as `paused`. CREATE is the only operation that produces a new workspace entry; it never produces an `active` entry.
- SWITCH away from this workspace (the previously active workspace becomes `paused`).

**Allowed transitions:**

| Transition | Operation |
|------------|-----------|
| `paused` → `active` | SWITCH targeting this workspace |
| `paused` → `archived` | ARCHIVE targeting this workspace |

**Invariants:**
- A paused workspace is fully preserved. No artifacts are modified, moved, or deleted when a workspace transitions to `paused`.
- A legacy workspace (runtime_version lower than current CSR version) holds `paused` or `archived` status. It may be switched to (made active), but pipeline commands may fail if the workspace directory structure is incomplete relative to current CSR requirements. No automatic repair is performed.

---

### archived

**Meaning:** The workspace has been retired. It is preserved, consultable, and read-only. No pipeline commands may operate on it. Archival is terminal within this runtime.

**Entry:**
- Explicit ARCHIVE operation targeting a `paused` workspace.

**Allowed transitions:**

None. `archived` is a terminal state.

**Invariants:**
- An archived workspace must not be modified by any pipeline command or lifecycle operation.
- An archived workspace cannot be made active. The SWITCH operation must reject an archived workspace as the target.
- All artifacts in an archived workspace remain readable.
- Archived workspaces are not deleted and are not hidden from the workspace registry.

---

### relocated

**Meaning:** `[C1-era addition, 2026-11-01]` The workspace is a CSR engineering fixture — a certification campaign, an E2E milestone test, a synthetic or replay workspace — never a client project, and its directory no longer resides under `workspaces/<id>/`. It has moved to `tests/fixtures/<id>/`, outside the path every workspace operation in this contract assumes.

**Entry:**
- No operation in this contract produces `relocated`. The first 20 entries carrying it were set by a one-time manual repository reorganization on 2026-11-01, separating engineering fixtures from genuine project material ahead of eventual plugin packaging (D2). This is not a repeatable runtime capability today — there is no RELOCATE operation.

**Allowed transitions:**

None observed. If a future need arises to formalize moving a workspace out of `workspaces/`, it should be specified as a proper operation rather than left as an undocumented manual edit — this entry exists precisely so that does not happen silently a second time.

**Invariants:**
- A relocated workspace's registry row is preserved, not deleted — `created`, `last_active`, `runtime_version`, and the original `description` remain exactly as recorded, with only `status` and an appended relocation note changed. Same principle as `archived`: a workspace leaving active service marks its row, it does not erase it.
- A relocated workspace is not addressable by any operation in this contract. `SWITCH`, `ARCHIVE`, and pipeline commands all assume `workspaces/<id>/`; a relocated entry's data is not there.
- `runtime/current_workspace.md` must never name a relocated workspace. If it does, this is workspace drift of a kind this contract did not anticipate before 2026-11-01: not a stale pointer to a workspace that moved status, but a pointer to a workspace that moved *location*.

---

### Lifecycle Transition Diagram

```text
[CREATE] ─────────────────────────────────────→ paused
                                                   │
                          ┌──────────────────────→ │
                          │                        ↓
                          │        ←─[SWITCH to]── paused
                       active                      │
                          │─[SWITCH away]──────────┘
                                                   │
                                       [ARCHIVE] ──┘
                                                   ↓
                                               archived
                                           (terminal state)
```

---

## Workspace Creation Contract

### Purpose

Produce a new workspace with a complete pipeline-ready directory structure, registered in the workspace registry with `status: paused`.

### Inputs

| Input | Required | Description |
|-------|----------|-------------|
| `workspace_id` | Required | Unique identifier for the new workspace; forms the directory name under `workspaces/` |
| `description` | Optional | Human-readable description recorded in the workspace registry |

### Preconditions

1. `workspace_id` is non-empty and forms a valid directory name on the host filesystem.
2. `workspace_id` is not already present in `runtime/workspaces.md`.
3. `workspaces/<workspace_id>/` does not already exist as a directory.
4. `runtime/workspaces.md` is readable and writable.
5. `runtime/current_workspace.md` is readable.

### Activation Principle

CREATE produces a workspace in `paused` state. It does not activate the workspace. It does not modify `runtime/current_workspace.md`. Activation always requires a separate, explicit SWITCH operation. This is unconditional — there are no inputs or conditions under which CREATE produces an `active` workspace.

### Behavior

1. Create the workspace root directory `workspaces/<workspace_id>/`.
2. Create all required pipeline subdirectories under the workspace root. The canonical directory structure is defined in the execution specification.
3. Create `.gitkeep` files in all empty pipeline subdirectories as defined in the execution specification.
4. Register the new workspace in `runtime/workspaces.md` with the following fields:
   - `workspace_id` = provided value
   - `created` = current timestamp (ISO 8601)
   - `status` = `paused`
   - `description` = provided value, or empty string if not provided
   - `last_active` = empty (not yet activated)
   - `runtime_version` = current CSR version (traceability field — see Workspace Registry Contract)
   - `spec_template_version` = `v1` — written explicitly; a new classic project is an STD v1 project (see Workspace Registry Contract)
5. Do not modify `runtime/current_workspace.md`.
6. Do not set `status` to any value other than `paused` in the new registry entry.

### Postconditions

1. `workspaces/<workspace_id>/` exists with the complete required directory structure.
2. A registry entry for the new workspace exists in `runtime/workspaces.md`.
3. The registry entry has `status: paused`.
4. The registry entry has `runtime_version` set to the current CSR version.
5. The registry entry has `spec_template_version: v1`.
6. `runtime/current_workspace.md` is unchanged.
7. No existing workspace changes state as a result of workspace creation.

### Traceability Requirements

The workspace registry entry is the permanent creation record for the workspace. The `created` and `runtime_version` fields are set at creation time and must not be modified by any subsequent operation.

### Ownership

The workspace creation operation owns:
- `workspaces/<workspace_id>/` (newly created directory tree)
- The new registry entry in `runtime/workspaces.md`

The workspace creation operation must not touch:
- `runtime/current_workspace.md`
- Any existing workspace directory
- Any existing registry entry

---

## Workspace Switching Contract

### Purpose

Transfer the active workspace designation from the current workspace to a named paused workspace.

### Inputs

| Input | Required | Description |
|-------|----------|-------------|
| `workspace_id` | Required | The target workspace to make active |

### Preconditions

1. `workspace_id` is present in `runtime/workspaces.md`.
2. Target workspace has `status: paused` in the registry. An archived workspace may not be switched to. The currently active workspace may not be switched to (no-op; report STATUS: ALREADY ACTIVE).
3. `runtime/current_workspace.md` is readable and writable.
4. `runtime/workspaces.md` is readable and writable.

### Write Ordering

`runtime/workspaces.md` is updated before `runtime/current_workspace.md`. Registry writes are the authoritative state change. The resolver update is a downstream reflection of the completed registry write.

### Behavior

1. Identify the currently active workspace from `runtime/workspaces.md` — the `status: active` registry entry, if any. If `runtime/current_workspace.md` names a different workspace than the `status: active` registry entry, this is workspace drift at operation start. Report the drift and proceed using `runtime/workspaces.md` as the authority.
2. Update `runtime/workspaces.md`: set the previously `active` workspace entry (if any) to `status: paused`; set the target workspace entry to `status: active`; update `last_active` on the target entry to the current timestamp (ISO 8601).
3. Write `runtime/current_workspace.md` to contain `workspace_id: <target>`, reflecting the completed registry state.
4. Verify consistency: `runtime/current_workspace.md` names the target workspace; exactly one `status: active` entry exists in the registry and it matches `runtime/current_workspace.md`.

### Postconditions

1. `runtime/current_workspace.md` contains `workspace_id: <target>`.
2. Target workspace registry entry has `status: active`.
3. Target workspace registry entry has `last_active` updated to the current timestamp.
4. Previously active workspace registry entry (if any) has `status: paused`.
5. Exactly one registry entry has `status: active`.
6. No artifacts in any workspace are modified, moved, or deleted.

### Workspace Isolation Guarantees

The SWITCH operation modifies only `runtime/current_workspace.md` and `runtime/workspaces.md`. It does not touch any artifact under any `workspaces/<workspace_id>/` directory. After switching, the pipeline's `WORKSPACE_ROOT` resolves to the new workspace. Artifacts from the prior workspace are not visible or accessible through the pipeline unless the workspace is explicitly switched back.

---

## Workspace Archival Contract

### Purpose

Retire a paused workspace to a terminal read-only state. All artifacts are preserved. The workspace is removed from active use.

### Inputs

| Input | Required | Description |
|-------|----------|-------------|
| `workspace_id` | Required | The target workspace to archive |

### Preconditions

1. `workspace_id` is present in `runtime/workspaces.md`.
2. Target workspace has `status: paused`. The active workspace cannot be archived; the user must SWITCH to another workspace first. An already-archived workspace cannot be re-archived.
3. `runtime/workspaces.md` is readable and writable.

### Behavior

1. Set target workspace `status` to `archived` in `runtime/workspaces.md`.
2. Do not modify any artifact under `workspaces/<workspace_id>/`.
3. Do not modify `runtime/current_workspace.md`.

### Postconditions

1. Target workspace registry entry has `status: archived`.
2. `workspaces/<workspace_id>/` directory and all its contents are unmodified.
3. `runtime/current_workspace.md` is unchanged.
4. The count of `status: active` entries in the registry is unchanged.

### Archived Workspace Guarantees

See Read-Only Archive Contract.

---

## Workspace Registry Contract

### Responsibility

`runtime/workspaces.md` is the authoritative source of truth for all workspace lifecycle states, existence, and creation metadata. The `status` field in the registry defines the true state of each workspace. No other source overrides it.

`runtime/current_workspace.md` is an operational pointer maintained in sync with the registry by workspace lifecycle operations. It names the workspace identified as `status: active` in the registry and is consumed by pipeline commands to resolve `WORKSPACE_ROOT`. It is not an authority source for workspace status.

### Registry Fields

| Field | Semantics | Mutability |
|-------|-----------|------------|
| `workspace_id` | Unique workspace identifier; matches directory name under `workspaces/` | Immutable after creation |
| `created` | ISO 8601 timestamp of workspace creation | Immutable after creation |
| `status` | Lifecycle state: `active`, `paused`, `archived`, or `relocated` `[2026-11-01]` | Updated by SWITCH and ARCHIVE operations only; `relocated` is not produced by any operation — see Workspace Lifecycle Model |
| `description` | Human-readable description | Mutable |
| `last_active` | ISO 8601 timestamp of last activation; updated when workspace transitions to `active` | Updated by SWITCH only |
| `runtime_version` | CSR version at workspace creation time | Immutable after creation |
| `spec_template_version` | Specification template the workspace generates with: `v1` (STD canonical) or `legacy` | Written at creation — `v1` by CREATE, `legacy` by V2 FORK. Never modified by a lifecycle operation; changing it is an explicit human decision outside the lifecycle |

### spec_template_version Semantics `[issue #55, 2026-11-09]`

`spec_template_version` is read by `/generate-specification` (Step 1.5.1) to choose the template: `v1` → STD, `legacy` → LEGACY. Every lifecycle operation that creates a registry row writes it explicitly — CREATE writes `v1` (STD v1 is mandatory for new workspaces, `docs/architecture/STD-Specification-Template-Design.md` §9.4), V2 FORK writes `legacy` (V2 always generates LEGACY). The admitted values are exactly `v1` and `legacy`.

Rows written before this rule — empty value, or a registry with no such column — are not migrated, rewritten or invalidated: an empty or absent value keeps reading as LEGACY with a WARNING at generation time, as documented before. The creation-time rules (WC10, WV11) apply only to the row the operation writes; the registry-wide rule (WR6) reports only a non-empty value outside `v1`/`legacy`.

### runtime_version Semantics

`runtime_version` records the CSR runtime version at the time the workspace was created. It is a traceability field, not a compatibility field. It does not imply that the workspace is only compatible with that version. It does not require that pipeline commands verify version compatibility before operating on the workspace. Its value is set once at creation and must not be modified by any subsequent operation.

### Registry Invariants

1. `workspace_id` values must be unique across all registry entries.
2. Exactly one registry entry may hold `status: active` at any time after the first workspace has been activated.
3. `runtime/current_workspace.md` must reflect the `workspace_id` of the `status: active` registry entry. When they disagree, `runtime/workspaces.md` is authoritative and `runtime/current_workspace.md` must be corrected. The drift is detected and reported; workspace lifecycle operations do not silently ignore it.
4. The `created` and `runtime_version` fields for any entry must not be modified after creation.
5. `last_active` must not be modified except by the SWITCH operation.

### Authority Model

`runtime/workspaces.md` is the authority for workspace lifecycle state. When `runtime/current_workspace.md` and `runtime/workspaces.md` disagree, `runtime/workspaces.md` wins. `runtime/current_workspace.md` is considered stale and must be corrected to reflect the active workspace as declared in the registry.

No pipeline command or lifecycle operation may treat `runtime/current_workspace.md` as the authority over `runtime/workspaces.md`. Reading `runtime/current_workspace.md` to obtain the target workspace_id for path construction is permitted; accepting its value as overriding the registry is not.

---

## Active Workspace Resolver Contract

### Role

`runtime/current_workspace.md` is an operational pointer. Its sole purpose is to name the active workspace for pipeline command consumption, so that commands can construct `WORKSPACE_ROOT` without reading and parsing the full workspace registry.

It is not a lifecycle state store. It does not define which workspace is active. It reflects which workspace `runtime/workspaces.md` has declared as `status: active`.

### Content

`runtime/current_workspace.md` contains exactly one field:

```text
workspace_id: <value>
```

### Maintenance

`runtime/current_workspace.md` is written by workspace lifecycle operations only:

| Operation | Effect on resolver |
|-----------|-------------------|
| SWITCH | Updated to `workspace_id: <target>` after the registry write completes |
| CREATE | Not modified |
| ARCHIVE | Not modified |

No pipeline command (M1–M9) may write to `runtime/current_workspace.md`.

### Drift Handling

If `runtime/current_workspace.md` and `runtime/workspaces.md` disagree at the time a pipeline command or lifecycle operation reads them, the following applies:

1. The disagreement is workspace drift.
2. `runtime/workspaces.md` is authoritative.
3. The operation reports the drift condition explicitly.
4. `runtime/current_workspace.md` must be corrected to match `runtime/workspaces.md` before normal pipeline operations resume.
5. Workspace lifecycle operations (SWITCH, ARCHIVE) that detect drift at operation start report it and proceed using the registry as authority.
6. Pipeline commands (M1–M9) that detect drift report it and do not proceed until drift is resolved. This is enforced through the existing R4a–R4e workspace validation chain.

### Cross-Command Impact

The existing R4e workspace drift rule in pipeline commands (M1–M9) designates `runtime/current_workspace.md` as the authority when multiple `status: active` entries exist. This designation is superseded by the M10 authority model: `runtime/workspaces.md` is authoritative in all drift conditions. The execution specification (L2) must update R4e accordingly across all affected commands.

---

## Legacy Workspace Contract

### Classification

A workspace is classified as legacy when its `runtime_version` in the registry is lower than the current CSR runtime version. Legacy is a classification derived from these two values; it is not a registry status value. A legacy workspace holds `paused` or `archived` status in the registry.

### Allowed Operations

A legacy workspace may be:
- Listed in the workspace registry.
- Switched to (made active) via the SWITCH operation.
- Archived via the ARCHIVE operation.
- Consulted — its artifacts may be read by any means.

### Restricted Operations

No automatic structural repair is performed on a legacy workspace. This runtime does not add missing directories, upgrade directory structure, or migrate artifacts when a legacy workspace is created or activated.

### Expected Behavior When Active

When a legacy workspace is made active, all pipeline commands operate on it normally. A pipeline command that requires a directory that does not exist in the legacy workspace (for example, `specifications/lifecycle/` introduced in M8) will fail with its standard precondition error for that missing directory. This is the expected behavior. The user must create the missing directory manually before running affected pipeline commands against a legacy workspace.

The `default` workspace created during Milestone 4.5 is a legacy workspace (`runtime_version: 0.3.0`). Its directory structure does not include `specifications/lifecycle/` or `specifications/archive/`. This is preserved as-is.

---

## Workspace Isolation Contract

### Existing Model (Established in Milestone 4.5)

All pipeline command file operations must target paths prefixed with `WORKSPACE_ROOT`.

Shared exception paths that pipeline commands may also access (not workspace-scoped):
- `runtime/current_workspace.md`
- `runtime/workspaces.md`
- `docs/`
- `templates/`
- `.claude/`

Any pipeline command operation targeting a path outside `WORKSPACE_ROOT` that is not on the exception list is workspace contamination — a hard stop.

### M10 Additions

The workspace lifecycle operations (CREATE, SWITCH, ARCHIVE) are the only operations that intentionally modify `runtime/current_workspace.md` and `runtime/workspaces.md`. These files are on the shared exception list precisely because lifecycle operations must be able to write to them.

The workspace isolation model must not be weakened by M10. The following invariants must remain true after M10 is implemented:

1. Pipeline commands (M1–M9) continue to enforce the `WORKSPACE_ROOT` prefix requirement on all artifact operations.
2. A pipeline command invoked in workspace A cannot read or write artifacts in workspace B, even if both workspaces exist under `workspaces/`.
3. The SWITCH, ARCHIVE, and CREATE operations must not write to any path under any `workspaces/<workspace_id>/` directory that is not the target of the current operation.

---

## Read-Only Archive Contract

### What Remains Allowed for Archived Workspaces

- Reading any artifact in `workspaces/<workspace_id>/` by any actor.
- Inspecting the workspace registry entry.
- Referencing the workspace in documentation, reports, or decisions.
- Listing the workspace in registry views.

### What is Prohibited for Archived Workspaces

- Writing any artifact in `workspaces/<workspace_id>/`.
- Making the workspace active (SWITCH to an archived workspace is BLOCKING).
- Running any pipeline command (M1–M9) on an archived workspace. R4b already enforces `status: archived → STATUS: BLOCKED`.
- Re-archiving (the workspace is already archived).
- Deleting any artifact in `workspaces/<workspace_id>/`.

### Enforcement

The primary enforcement mechanism is R4b — present in all M1–M9 commands since Milestone 4.5. When an archived workspace is the active workspace (possible only through direct manual edit of `current_workspace.md`), R4b returns STATUS: BLOCKED — Workspace Archived. M10 adds the constraint that the SWITCH operation explicitly rejects archived workspaces as targets, preventing the archived workspace from becoming active through normal operation.

---

## Runtime Boundaries

### What belongs to M10

- Workspace CREATE operation
- Workspace SWITCH operation
- Workspace ARCHIVE operation
- Workspace registry (CREATE, SWITCH, ARCHIVE write semantics)
- Legacy workspace classification and contract
- Workspace isolation contract (preservation of existing model, M10 additions)
- Read-only archive contract
- Validation rules WC1–WC10, WS1–WS8, WA1–WA6, WR1–WR6

### What belongs to CSR System Certification (post-M10, pre-M11)

CSR System Certification is a transverse validation gate executed after M10 completion and before M11 begins. It is not a component of M10 and must not be included in M10's scope or success criteria. This gate verifies the complete M1–M10 pipeline as an integrated system. Its definition, scope, and execution procedure are outside this contract.

### What belongs to M11

- Pipeline status reporting
- Pipeline ordering contract
- Pipeline dependency enforcement
- Precondition gates at pipeline boundaries

### What belongs to M12

- Automated pipeline chaining
- Non-interactive stage runner
- Session continuity across pipeline steps

---

## Out of Scope

The following capabilities are explicitly outside M10:

| Capability | Reason |
|------------|--------|
| Pipeline status reporting | M11 |
| Pipeline coordination | M11 |
| Dependency enforcement between pipeline stages | M11 |
| Automated pipeline chaining | M12 |
| Guided pipeline runner | M12 |
| CSR operating agent | Post-M12 |
| CSR System Certification | Post-M10 transverse gate |
| Flat-path deprecated artifact deletion | Deferred maintenance; requires per-file audit |
| Un-archiving a workspace | Not defined; archival is terminal within M10 |
| Workspace repair or migration | No automatic repair for legacy workspaces |
| Workspace renaming | Not defined; workspace_id is immutable |
| Multi-workspace pipeline operations | Single active workspace model is not changed |

---

## Validation Rules

All validation rules are verified after the operation completes. Rules marked BLOCKING cause the operation to stop and report an explicit error when they fail. Rules marked WARNING are reported but do not stop execution.

### Workspace Creation Rules

| Rule | Condition | Classification |
|------|-----------|----------------|
| WC1 | `workspace_id` is non-empty | BLOCKING |
| WC2 | `workspace_id` is not already present in `runtime/workspaces.md` | BLOCKING |
| WC3 | `workspaces/<workspace_id>/` did not already exist before the operation | BLOCKING |
| WC4 | `runtime/workspaces.md` is writable | BLOCKING |
| WC5 | All required pipeline subdirectories exist under `workspaces/<workspace_id>/` after creation | BLOCKING |
| WC6 | Registry entry for the new workspace is present in `runtime/workspaces.md` with all required fields populated and non-empty | BLOCKING |
| WC7 | New workspace registry entry has `status: paused` — never `active` | BLOCKING |
| WC8 | New workspace registry entry has `runtime_version` equal to the current CSR version | BLOCKING |
| WC9 | `runtime/current_workspace.md` is unmodified after the operation | BLOCKING |
| WC10 | New workspace registry entry has `spec_template_version: v1` | BLOCKING (WARNING if the registry has no `spec_template_version` column — no header migration) |

### Workspace Switching Rules

| Rule | Condition | Classification |
|------|-----------|----------------|
| WS1 | Target `workspace_id` is present in `runtime/workspaces.md` | BLOCKING |
| WS2 | Target workspace has `status: paused` in the registry | BLOCKING |
| WS3 | `runtime/current_workspace.md` contains `workspace_id: <target>` after the operation | BLOCKING |
| WS4 | Target workspace registry entry has `status: active` after the operation | BLOCKING |
| WS5 | Previously active workspace registry entry (if any) has `status: paused` after the operation | BLOCKING |
| WS6 | Exactly one registry entry has `status: active` after the operation | BLOCKING |
| WS7 | Target workspace registry entry `last_active` is updated to a current timestamp | WARNING |
| WS8 | No artifact under any `workspaces/<workspace_id>/` directory is modified, moved, or deleted | BLOCKING |

### Workspace Archival Rules

| Rule | Condition | Classification |
|------|-----------|----------------|
| WA1 | Target `workspace_id` is present in `runtime/workspaces.md` | BLOCKING |
| WA2 | Target workspace has `status: paused` at operation start | BLOCKING |
| WA3 | Target workspace registry entry has `status: archived` after the operation | BLOCKING |
| WA4 | `workspaces/<workspace_id>/` directory and all its contents are unmodified | BLOCKING |
| WA5 | `runtime/current_workspace.md` is unmodified after the operation | BLOCKING |
| WA6 | The count of `status: active` entries in the registry is unchanged after the operation | BLOCKING |

### Workspace Registry Rules

| Rule | Condition | Classification |
|------|-----------|----------------|
| WR1 | All `workspace_id` values in the registry are unique | BLOCKING |
| WR2 | Exactly one registry entry has `status: active` at the completion of any lifecycle operation | BLOCKING |
| WR3 | `runtime/current_workspace.md` reflects the `workspace_id` of the `status: active` registry entry. When they disagree, `runtime/workspaces.md` is authoritative; `runtime/current_workspace.md` is stale and must be corrected before pipeline operations may proceed. | BLOCKING |
| WR4 | `runtime_version` is non-empty for all registry entries | WARNING |
| WR6 | Every non-empty `spec_template_version` value is `v1` or `legacy` (empty / absent = pre-#55 row, not a finding) | WARNING |
| WR5 | Every `workspace_id` in the registry **not** marked `relocated` has a corresponding directory under `workspaces/` | WARNING |

---

## Success Criteria

M10 is complete when all of the following are true:

1. The CREATE operation produces a workspace with the complete M9-era pipeline directory structure, registered with `status: paused` and `runtime_version` set to the current CSR version.

2. The SWITCH operation correctly transitions workspace states: `runtime/workspaces.md` reflects the target workspace as `active` and the previously active workspace as `paused`; `runtime/current_workspace.md` is updated as a downstream reflection of the completed registry write; and no artifacts are modified.

3. The ARCHIVE operation correctly transitions a paused workspace to `archived`, with no modification to workspace artifacts or the active workspace resolver.

4. All WC1–WC10, WS1–WS8, WA1–WA6, and WR1–WR6 validation rules pass for their respective operations.

5. An archived workspace blocks all pipeline commands (M1–M9) via the existing R4b enforcement. A live invocation of at least one pipeline command against an archived workspace returns STATUS: BLOCKED — Workspace Archived.

6. The A7 cross-command guard is validated live: a live invocation of `/generate-specification` against a workspace where the target specification base is BASELINED returns STATUS: BLOCKED. This confirms that the cross-command lifecycle guard is active and correct.

7. A workspace created by the CREATE operation is taken through the full nine-stage pipeline (M1 → M9) using a multi-type conflict corpus (at minimum one AMBIGUITY conflict, one GAP conflict, and one CONTRADICTION conflict present simultaneously) and completes successfully through ARCHIVE. This is the definitive end-to-end validation of M10.

8. All existing pipeline commands (M1–M9) and lifecycle operations (BASELINE, REOPEN, EVOLVE, ARCHIVE) continue to function correctly in the active workspace after each M10 lifecycle operation is executed.

9. Validation rules WC1–WC10, WS1–WS8, WA1–WA6, and WR1–WR6 are enumerated in the execution specification and verified in the E2E validation.

---

## Risks

### BLOCKING Risks

| Risk | Description |
|------|-------------|
| R-B1: workspace_id collision | If workspace creation does not atomically check and create the directory and registry entry, a race condition or partial failure could leave the registry and filesystem in disagreement. Mitigation: WC2 and WC3 must be checked before any write operation; if WC5 or WC6 fail, partial creation must be reported explicitly with recovery guidance. |
| R-B2: A7 guard failure | The A7 guard has been specified across M7 L1–L4 but has never been triggered by a live `/generate-specification` invocation. If the guard is not active, a pipeline command could silently overwrite a BASELINED specification draft file without triggering STATUS: BLOCKED. Discovery of this failure during M10 E2E validation requires immediate remediation before M10 can be declared complete. |
| R-B3: SWITCH partial write | If `runtime/workspaces.md` is updated (old workspace set to `paused`) but `runtime/current_workspace.md` write fails, the system enters workspace drift: the registry shows no active workspace, but the resolver still points to the old workspace. Mitigation: WS3, WS4, WS6 must all pass before SWITCH is declared complete; if any fail, the operation must report the drift and the recovery steps. |

### NON-BLOCKING Risks

| Risk | Description |
|------|-------------|
| R-NB1: Legacy workspace activation failures | Switching to the `default` workspace will succeed at the SWITCH level but will cause pipeline command failures because `specifications/lifecycle/` and `specifications/archive/` do not exist in the `default` workspace. This is expected behavior per the legacy workspace contract. Documentation of this behavior in L2 and L4 prevents user confusion. |
| R-NB2: runtime_version field interpretation drift | Future contributors may interpret `runtime_version` as a compatibility gate rather than a traceability field. The semantics must be documented clearly in L1 (this document), L2, and L4 to prevent incorrect compatibility checks from being introduced. |
| R-NB3: E2E corpus design underspecification | The multi-type conflict corpus for M10 E2E validation must produce AMBIGUITY, GAP, and CONTRADICTION conflicts simultaneously. If the corpus is designed with only one conflict type, the validation will not exercise the ADR-X1 code paths. The corpus design is an L2 responsibility and must be explicitly specified. |

### OBSERVATIONS

| Observation | Description |
|-------------|-------------|
| OB1: Zero active entries at initialization | Before any SWITCH operation (e.g., immediately after repository initialization), no workspace may hold `status: active`. WR2 applies after any lifecycle operation completes; it does not apply to the empty-registry initial state. |
| OB2: Workspace_id format is not constrained at L1 | This contract requires only that workspace_id is non-empty and forms a valid directory name. The execution specification (L2) must define a more precise character set constraint (e.g., lowercase alphanumeric and hyphens only) to ensure cross-platform compatibility and avoid user-facing errors. |
| OB3: last_active for workspaces never switched to | A workspace created by CREATE but never activated will have an empty `last_active` field. This is a valid registry state. WR4 does not require `last_active` to be non-empty, only `runtime_version`. |
| OB4: R4e cross-command update required | The existing R4e drift rule in all M1–M9 pipeline commands designates `runtime/current_workspace.md` as the authority when multiple `status: active` entries are detected. This designation is superseded by the M10 authority model. The M10 execution specification (L2) must document the required R4e update; the M10 command update (L4) must propagate it to all affected commands. Until this update is applied, the existing commands partially contradict the authority model defined here. |

---

## Final Recommendation

This Layer 1 Contract is **ready for approval**.

**Approved decisions integrated:**

Decision 1 — CREATE → paused: The contract unconditionally specifies that CREATE produces a `paused` workspace. This is enforced by the Activation Principle in the Workspace Creation Contract, the `paused` state Entry definition, the `active` state Invariants, WC7, and WC9. No code path or input condition results in CREATE producing an `active` workspace.

Decision 2 — workspaces.md as authority: The contract redefines `runtime/workspaces.md` as the source of truth and `runtime/current_workspace.md` as an operational pointer. This is reflected in Definitions, the `active` state Invariants, the Workspace Switching Contract write ordering, the Workspace Registry Contract Responsibility and Authority Model, the Active Workspace Resolver Contract (new section), Registry Invariant 3, WR3, and Success Criterion 2. All prior references to `current_workspace.md` as authority have been removed.

**Open items delegated to L2:**

- The canonical workspace directory structure (enumeration of required subdirectories).
- The workspace_id character set constraint (OB2).
- The E2E corpus specification (multi-type conflict corpus design).
- The R4e cross-command update procedure (OB4 — supersedes current `current_workspace.md`-as-authority designation in M1–M9 commands).

**No new scope introduced.** The contract implements exactly the three lifecycle operations (CREATE, SWITCH, ARCHIVE) approved for M10. All five open design questions from the M10 architecture review are resolved in this contract.
