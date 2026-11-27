# /specification-lifecycle

## Purpose

Govern the post-generation lifecycle of draft specification artifacts.

This command is **interactive**. All lifecycle transitions require explicit human authorization. The runtime surfaces the current specification state and the available transitions; the human actor makes the decision and provides the required metadata. The runtime records the decision; it does not make it.

This command implements Stage 8 — Specification Stabilization of the CSR pipeline.

This command implements four lifecycle operations: BASELINE, REOPEN, EVOLVE, and ARCHIVE.

---

## Architecture Dependency — A7

`/generate-specification` (M7) must be amended to consult the lifecycle registry before writing any draft specification. The required amendment is defined in:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/specification-lifecycle_execution.md — Cross-Command Guard (A7)
```

The clause to amend in `${CLAUDE_PLUGIN_ROOT}/docs/commands/generate-specification.md` is the Re-generation paragraph in the Eligibility section.

This amendment is part of M8 implementation. Until it is applied, M7 will not enforce the lifecycle guard. Apply the amendment before running M8 E2E validation.

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

All file operations must target paths within `WORKSPACE_ROOT/specifications/`.

Before every write: verify the target path is within `WORKSPACE_ROOT/specifications/`. If it is not: stop immediately. Report workspace contamination. Do not write the file.

Exceptions (not workspace-scoped): `runtime/current_workspace.md`, `runtime/workspaces.md`, `docs/`, `templates/`, `.claude/`

Any operation targeting a path outside `WORKSPACE_ROOT/specifications/` that is not on the exception list must be rejected and reported as workspace contamination.

---

## Preconditions

Before execution:

1. All specification artifacts must exist and be readable:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/specification-lifecycle.md
${CLAUDE_PLUGIN_ROOT}/docs/commands/specification-lifecycle_execution.md
${CLAUDE_PLUGIN_ROOT}/templates/prompts/specification_lifecycle_prompt.md
```

2. **BASELINE mode** — the following must exist and be readable:

```text
WORKSPACE_ROOT/specifications/draft/<base>_specification.md
WORKSPACE_ROOT/knowledge_base/consolidated/consolidation_report.md
WORKSPACE_ROOT/specifications/draft/specifications_report.md
WORKSPACE_ROOT/specifications/stable/                              (directory)
```

The lifecycle registry (`WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md`) need not exist for the first BASELINE. It is created during execution.

3. **REOPEN and EVOLVE modes** — the following must exist and be readable:

```text
WORKSPACE_ROOT/specifications/stable/<base>_specification.md
WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md
```

4. **BASELINE eligibility conditions E1–E5** must hold at execution time (verified during execution):

| ID | Condition |
|----|-----------|
| E1 | Target status is DRAFT — **legacy spec:** `**Status:** DRAFT`; **STD spec** (first line `---`): YAML `status: DRAFT` |
| E2 | Draft artifact exists and is readable |
| E3 | All BLOCKING conflicts in `**Conflicts Incorporated:**` are CONSOLIDATED |
| E4 | Named human authorization provided |
| E5 | No active BASELINED entry for this `<base>` in the lifecycle registry |

5. The `specifications/lifecycle/` directory is created by the runtime if it does not exist (first lifecycle operation).

6. **ARCHIVE mode** — the following must exist and be readable:

```text
WORKSPACE_ROOT/specifications/stable/<base>_specification.md
WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md
```

The `specifications/archive/` directory is created by the runtime if it does not exist (first ARCHIVE operation). No pre-existence required.

If any BLOCKING precondition fails, report the failure explicitly and stop. Do not proceed to execution.

---

## Execution

### Step 1 — Load Specifications

Read and assimilate:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/specification-lifecycle.md
${CLAUDE_PLUGIN_ROOT}/docs/commands/specification-lifecycle_execution.md
${CLAUDE_PLUGIN_ROOT}/templates/prompts/specification_lifecycle_prompt.md
```

The repository is the source of truth.

Ignore any prior conversational assumptions not present in the repository.

All execution procedures and write ordering rules are defined in `${CLAUDE_PLUGIN_ROOT}/docs/commands/specification-lifecycle_execution.md`.

All behavioral constraints, decision rules, invariants, and step-by-step instructions are defined in `${CLAUDE_PLUGIN_ROOT}/templates/prompts/specification_lifecycle_prompt.md`.

---

### Step 2 — Determine Operation

If the human specifies an operation argument (BASELINE, REOPEN, EVOLVE, ARCHIVE): use that operation.

If no operation is specified: present the four operations and their conditions, and ask which operation the human wants to perform.

If ARCHIVE is requested: execute the ARCHIVE sequence defined in Step 3.

---

### Step 3 — Execute Lifecycle Runtime

Execute the runtime defined in:

```text
${CLAUDE_PLUGIN_ROOT}/templates/prompts/specification_lifecycle_prompt.md
```

The session is **interactive**. Execute the operation selected in Step 2 in the following order as defined in the prompt:

**BASELINE:**

1. Load draft specification; detect `spec_mode` (STD if first line is `---`, LEGACY otherwise); record `body_checksum` from body content (STD: below YAML closing `---`; LEGACY: below first `---`).
2. Load consolidation report and lifecycle registry.
3. Verify E3 eligibility — all BLOCKING conflicts are CONSOLIDATED.
4. Verify E5 eligibility — no active BASELINED entry for `<base>`.
5. Present confirmation prompt; collect `baseline_actor`, `baseline_date`, `baseline_rationale`.
6. Write stable artifact (header-only update; body unchanged). **STD:** update YAML `status: BASELINED`, `baseline_date: <date>`; actor/rationale in lifecycle registry only. **LEGACY:** update `**Status:** BASELINED`, add `**Baseline Date:**`, `**Baselined By:**`, `**Baseline Rationale:**`. Verify; delete draft; verify deletion.
7. Update `**Superseded By:**` on SUPERSEDED artifact if this is an evolved spec (WARNING if fails).
8. Write or update lifecycle registry (Active State Index + BASELINE event record).
9. Update generation log (WARNING if fails).
10. Run validation rules BL1, BL2, BL3, BL5 (evolved only), BL9, BL10, BL11, BL12.
11. Report BASELINE COMPLETE.

**REOPEN:**

1. Load stable specification; record `body_checksum`.
2. Load lifecycle registry; verify `<base>` is BASELINED.
3. Present confirmation prompt; collect `reopen_actor`, `reopen_date`, `reopen_reason`.
4. Write draft artifact (header-only update; body unchanged). **STD:** update YAML `status: DRAFT`, `baseline_date: null`. **LEGACY:** update `**Status:** DRAFT`, remove `**Baseline Date:**`, `**Baselined By:**`, `**Baseline Rationale:**`. Verify; delete stable; verify deletion.
5. Update lifecycle registry (Active State Index + REOPEN event record); prior BASELINE event preserved.
6. Update generation log (WARNING if fails).
7. Run validation rules BL6, BL7, BL9, BL10, BL11, BL12.
8. Report REOPEN COMPLETE.

**EVOLVE:**

1. Load stable specification; record `body_checksum`.
2. Load lifecycle registry; read `version_sequence`; verify no DRAFT exists for `<base>`.
3. Determine versioned path: `specifications/stable/<base>_specification_v<version_sequence>.md`.
4. Present confirmation prompt; collect `evolve_actor`, `evolve_date`, `evolve_reason`.
5. Write versioned SUPERSEDED artifact; verify; delete unsuffixed stable; verify deletion.
6. Assign `reserved_spec_id` (next sequential SP ID).
7. Create DRAFT stub at `specifications/draft/<base>_specification.md` (PARTIAL if fails).
8. Update lifecycle registry (update existing Active State Index row for `<base>` to DRAFT with `supersedes` and `reserved_spec_id` fields + append EVOLVE event record; SUPERSEDED artifact details captured only in the Event Log).
9. Update generation log (WARNING if fails).
10. Run validation rules BL4, BL8, BL9, BL10, BL11.
11. Report EVOLVE COMPLETE.

**ARCHIVE:**

1. Load lifecycle registry; read `spec_state_index` entry for `<base>`.
2. Verify `current_status = BASELINED`. If status is DRAFT, SUPERSEDED, or ARCHIVED: report ARCHIVE_BLOCKED and stop. Do not proceed.
3. **Hybrid Discovery (AR1 — M9-D8) — executes before the confirmation summary:**
   - Active baseline: read `current_path` and `spec_id` from `spec_state_index`.
   - Superseded versions: scan all EVOLVE event records in the Event Log where `Base = <base>`; record `Superseded Artifact` path and `Superseded Spec ID` for each; order oldest first.
   - Filesystem check: confirm each path in `full_lineage` exists on disk. Missing paths carry forward to the Integrity Gate.
   - Result: `full_lineage = [active_baseline_path] + [superseded_artifact_paths]`.
4. **Integrity Gate (AR2 — M9-D9) — executes before the confirmation summary:**
   - Verify every path in `full_lineage` exists at its expected `specifications/stable/` location.
   - Verify no path in `full_lineage` already exists at its `specifications/archive/` destination.
   - On any mismatch: report ARCHIVE_BLOCKED. No files moved. Registry unchanged. Stop.
5. Present ARCHIVE confirmation summary using `full_lineage` (verified in steps 3–4). Display: base, active baseline path with BASELINED status, each superseded artifact path with its Spec ID (oldest first), total artifact count, archive destination, and an explicit warning that no artifacts will remain in `specifications/stable/` for this base after the operation. Collect `archive_actor`, `archive_date`, `archive_reason`. On cancellation or non-affirmative: BLOCKED. No file operations.
6. Create `specifications/archive/` if absent (first ARCHIVE operation).
7. For each artifact in `full_lineage` (AR3): load content; detect `spec_mode`. **STD:** update YAML `status: ARCHIVED`; archive metadata (actor/date/reason) in lifecycle registry only. **LEGACY:** update `**Status:** ARCHIVED`, add `**Archived Date:**`, `**Archived By:**`, `**Archive Reason:**`. Body content unchanged. Capture `body_checksum[path]` (STD: below YAML closing `---`; LEGACY: below first `---`).
8. For each artifact in `full_lineage` — MOVE execution (AR4–AR7):
   a. **Write** modified content to `specifications/archive/<filename>` (filename component unchanged from source path). On write failure: report ARCHIVE_FAILED. No stable/ files have been deleted. Registry unchanged. Stop.
   b. **Verify** archive copy: file exists, ARCHIVED status confirmed (STD: YAML `status: ARCHIVED`; LEGACY: `**Status:** ARCHIVED`), `body_checksum[path]` matches. On failure: report ARCHIVE_FAILED. No stable/ files deleted. Registry unchanged. Manual inspection required. Stop.
   c. **Delete** source from `specifications/stable/<filename>`. Apply retry policy on deletion failure (M9-D6): up to 5 total attempts; backoff of 1 s / 2 s / 4 s / 8 s between attempts; timing is best-effort. On retry exhaustion: report ARCHIVE_FAILED. Archive copy exists. Manual stable/ cleanup required. Stop.
   d. **Verify deletion**: source path must not exist in `specifications/stable/`. On presence: report ARCHIVE_FAILED. Archive copy exists. Manual cleanup required. Stop.
9. **Registry mutation — single atomic write (M9-D1, M9-D8):** In a single write operation: update `spec_state_index` row for `<base>` (`status → ARCHIVED`, `current_path → specifications/archive/<base>_specification.md`); append ARCHIVE event record (`event_id`, `event_type: ARCHIVE`, `spec_id`, `base`, `date`, `actor`, `reason`, `artifact` = archive path of active baseline, `lineage_moved` = total artifacts moved). State Index update and ARCHIVE Event Append must not be split into separate writes. On registry write failure: append LIFECYCLE FAILURE NOTE (ARCHIVE variant) to the archived artifact; report ARCHIVE_FAILED. Manual registry update required.
10. Validate registry write: `spec_state_index` row for `<base>` has `status = ARCHIVED` and `current_path` pointing to archive/; ARCHIVE event record exists in Event Log. On failure: report ARCHIVE_FAILED.
11. Update generation log: `Specification Artifact → specifications/archive/<base>_specification.md`; `Status → ARCHIVED` (WARNING if fails; non-blocking; lifecycle registry is authoritative).
12. **Completion Barrier (M9-D7):** Run validation rules BL9, BL10, BL11. On any BLOCKING rule failure: report ARCHIVE_FAILED with the rule ID, artifact path, and specific check that failed.
13. Report ARCHIVE COMPLETE with archive path, lineage moved summary, and confirmation that no artifacts remain in `specifications/stable/` for this base.

Do not introduce business logic beyond what is defined in the specification artifacts.

Do not modify any file outside `WORKSPACE_ROOT/specifications/`. Do not modify `knowledge_base/` or `input/` artifacts.

Do not begin file operations before explicit human confirmation is received.

---

## Invariants

These rules must never be violated, regardless of operation or failure state:

- Never alter body content. **STD:** body = below YAML closing `---` (second `---`). **LEGACY:** body = below first `---`. Verify with `body_checksum` before and after every write.
- SUPERSEDED artifacts must not be deleted except as part of a validated ARCHIVE MOVE operation. Within ARCHIVE, stable/ copies are deleted only after archive/ copies are written and verified (M9-D4, M9-D5).
- Never delete an ARCHIVED artifact.
- Never overwrite a lifecycle event record. The Event Log is append-only.
- Never proceed without explicit human confirmation.
- Write ordering: write the new artifact, verify it, then delete the prior artifact. Never delete before the successor is verified.
- Rollback on verification failure: delete the newly written artifact; preserve the prior artifact.
- Registry write is the last step. If it fails: append a FAILURE NOTE to the affected artifact; report BLOCKED.

---

## Validation

Before reporting the completion state, verify that all applicable BL rules pass:

| Rule | Check | Class | Operations |
|------|-------|-------|-----------|
| BL1 | BASELINE event in registry has `baseline_date` and `baselined_by` populated | BLOCKING | BASELINE |
| BL2 | `specifications/stable/<base>_specification.md` exists and is readable | BLOCKING | BASELINE |
| BL3 | The Active State Index row for `<base>` has status = BASELINED (one row per base) | BLOCKING | BASELINE |
| BL4 | Versioned SUPERSEDED artifact has SUPERSEDED status confirmed. **STD:** YAML `status: SUPERSEDED`. **LEGACY:** `**Superseded By:**` non-empty. | BLOCKING | EVOLVE |
| BL5 | If `spec_state_index` entry carries `supersedes`: referenced SUPERSEDED artifact exists and is readable | BLOCKING | BASELINE (evolved) |
| BL6 | REOPEN event in registry has `reopen_date`, `actor`, `reason` all non-empty | BLOCKING | REOPEN |
| BL7 | `specifications/draft/<base>_specification.md` exists with DRAFT status. **STD:** YAML `status: DRAFT`. **LEGACY:** `**Status:** DRAFT`. | BLOCKING | REOPEN |
| BL8 | EVOLVE event in registry has `evolution_date`, `actor`, `reason`, `superseded_artifact`, `new_spec_id` all non-empty | BLOCKING | EVOLVE |
| BL9 | Lifecycle registry exists and is readable | BLOCKING | All |
| BL10 | All writes targeted paths within `WORKSPACE_ROOT/specifications/` | BLOCKING | All |
| BL11 | Body content matches `body_checksum` for every written artifact. **STD:** body = below YAML closing `---` (second `---`). **LEGACY:** body = below first `---`. | BLOCKING | All |
| BL12 | Generation log reflects current path and status of affected specifications | WARNING | BASELINE, REOPEN, ARCHIVE |

If any BLOCKING rule fails: report the rule ID, the artifact path, and the specific check that failed. Stop.

---

## Failure Handling

Stop execution and report an explicit error when:

- any specification artifact (`docs/`, `templates/`) cannot be read;
- workspace resolution fails at any W step;
- target specification does not exist or is unreadable;
- target specification status is incompatible with the requested operation;
- any BASELINE eligibility condition (E1–E5) fails;
- a write failure occurs on a primary output artifact;
- a lifecycle registry write fails after file operations have been performed;
- a workspace isolation violation occurs;
- human cancels or does not provide an explicit affirmative.

Do not silently continue after any blocking failure. Every failure must be named and reported.

For the registry write failure specifically: append a LIFECYCLE FAILURE NOTE to the primary affected artifact before stopping. This provides a manual recovery path.

For EVOLVE stub write failure (Step EV8): report PARTIAL rather than BLOCKED. Core SUPERSEDED artifact was created; the missing stub must be created manually.

For ARCHIVE failures, use the following status codes:

**ARCHIVE_BLOCKED** (pre-MOVE; no file operations performed):
- Invalid lifecycle state (target is not BASELINED)
- Integrity Gate failure (lineage artifact missing from stable/ or already exists in archive/)
- Registry and filesystem lineage mismatch
- Human cancellation

**ARCHIVE_FAILED** (execution failure; MOVE may be partially or fully completed):
- archive/ write failure
- archive/ verification failure
- stable/ deletion failure after retry exhaustion
- Registry write failure after MOVE completed
- Completion Barrier BL rule failure

For ARCHIVE_FAILED: explicitly report the current state of the repository — which artifacts exist in archive/, which remain in stable/, and whether the registry has been updated. Do not leave the failure state ambiguous.

---

## Completion Criteria

**BASELINE** — complete when:

- `WORKSPACE_ROOT/specifications/stable/<base>_specification.md` exists with BASELINED status (STD: YAML `status: BASELINED`; LEGACY: `**Status:** BASELINED`);
- Draft artifact deleted from `specifications/draft/`;
- Lifecycle registry updated with BASELINE event and Active State Index entry;
- BL1, BL2, BL3, BL9, BL10, BL11 pass.

**REOPEN** — complete when:

- `WORKSPACE_ROOT/specifications/draft/<base>_specification.md` exists with DRAFT status (STD: YAML `status: DRAFT`; LEGACY: `**Status:** DRAFT`);
- Stable artifact deleted from `specifications/stable/`;
- Lifecycle registry updated with REOPEN event;
- BL6, BL7, BL9, BL10, BL11 pass.

**EVOLVE** — complete when:

- `WORKSPACE_ROOT/specifications/stable/<base>_specification_v<n>.md` exists with SUPERSEDED status (STD: YAML `status: SUPERSEDED`; LEGACY: `**Status:** SUPERSEDED`);
- Unsuffixed stable artifact deleted;
- `WORKSPACE_ROOT/specifications/draft/<base>_specification.md` exists as a DRAFT stub;
- Lifecycle registry updated with EVOLVE event and revised Active State Index;
- BL4, BL8, BL9, BL10, BL11 pass.

**ARCHIVE** — complete when:

- All artifacts in `full_lineage` exist in `WORKSPACE_ROOT/specifications/archive/` with ARCHIVED status (STD: YAML `status: ARCHIVED`; LEGACY: `**Status:** ARCHIVED`);
- All artifacts in `full_lineage` are absent from `WORKSPACE_ROOT/specifications/stable/`;
- Lifecycle registry `spec_state_index` row for `<base>` shows `status = ARCHIVED` with `current_path` pointing to the archive/ path;
- ARCHIVE event record appended to Event Log;
- BL9, BL10, BL11 pass.

---

## Completion Reporting

Report one of the following completion states:

```text
STATUS: BASELINE COMPLETE
```

```text
STATUS: REOPEN COMPLETE
```

```text
STATUS: EVOLVE COMPLETE
```

```text
STATUS: BLOCKED
```

```text
STATUS: PARTIAL — <specific condition>
```

```text
STATUS: ARCHIVE COMPLETE
```

```text
STATUS: ARCHIVE_BLOCKED
```

```text
STATUS: ARCHIVE_FAILED
```

Completion state definitions are specified in `${CLAUDE_PLUGIN_ROOT}/docs/commands/specification-lifecycle.md`.

Include in the report:

- the `<base>` identifier and Spec ID;
- the primary artifact path(s) affected;
- human actor name, date, and rationale/reason;
- validation rules passed;
- any WARNINGs issued (draft deletion failure, log update failure, superseded-by update failure);
- for BLOCKED: the operation, phase, reason, artifacts affected, and rollback status;
- for PARTIAL: what succeeded, what failed, and what manual action is required;
- for ARCHIVE COMPLETE: archive path, total artifacts moved, lineage summary, stable/ absent confirmation;
- for ARCHIVE_BLOCKED: the specific blocking condition (state mismatch or Integrity Gate failure), no file operations performed;
- for ARCHIVE_FAILED: the failing step, which artifacts exist in archive/, which remain in stable/, and whether the registry was updated.

---

## Expected Output

### BASELINE

```text
WORKSPACE_ROOT/specifications/stable/<base>_specification.md   ← promoted from draft; Status: BASELINED
WORKSPACE_ROOT/specifications/draft/<base>_specification.md    ← deleted (MOVE semantics)
WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md  ← written or updated
WORKSPACE_ROOT/specifications/draft/specifications_report.md   ← updated (path and status)
```

### REOPEN

```text
WORKSPACE_ROOT/specifications/draft/<base>_specification.md    ← returned from stable; Status: DRAFT
WORKSPACE_ROOT/specifications/stable/<base>_specification.md   ← deleted (MOVE semantics)
WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md  ← updated (REOPEN event)
WORKSPACE_ROOT/specifications/draft/specifications_report.md   ← updated (path and status)
```

### EVOLVE

```text
WORKSPACE_ROOT/specifications/stable/<base>_specification_v<n>.md   ← former baseline versioned; Status: SUPERSEDED
WORKSPACE_ROOT/specifications/stable/<base>_specification.md         ← deleted (vacated)
WORKSPACE_ROOT/specifications/draft/<base>_specification.md          ← DRAFT stub created
WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md  ← updated (EVOLVE event; reserved_spec_id)
WORKSPACE_ROOT/specifications/draft/specifications_report.md         ← updated (old entry SUPERSEDED; new stub row added)
```

### ARCHIVE

```text
WORKSPACE_ROOT/specifications/archive/<base>_specification.md         ← moved from stable/; Status: ARCHIVED
WORKSPACE_ROOT/specifications/archive/<base>_specification_v<n>.md    ← moved from stable/; one per SUPERSEDED version
WORKSPACE_ROOT/specifications/stable/<base>_specification.md          ← deleted (MOVE semantics)
WORKSPACE_ROOT/specifications/stable/<base>_specification_v<n>.md     ← deleted (MOVE semantics); one per SUPERSEDED version
WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md   ← updated (ARCHIVE event; Active State Index → ARCHIVED + archive path)
WORKSPACE_ROOT/specifications/draft/specifications_report.md          ← updated (archive path + ARCHIVED status) [WARNING if fails]
```

No other repository areas are modified by this command.

`WORKSPACE_ROOT/knowledge_base/` and `WORKSPACE_ROOT/input/` artifacts must not be modified.
