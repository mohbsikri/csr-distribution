# /governance-resolve

## Command Purpose

M13 — Governance Outcome Resolution Runtime closes governance outcomes that M12 opened.

**M13 resolves governance outcomes. M13 does not:**

- create original Verdicts (exclusively M12)
- evaluate Policy Profiles (exclusively M12)
- coordinate pipeline execution (exclusively M11)
- invoke M11
- invoke M12
- authorize execution following resume (M12 determines execution authorization at re-invocation)

M13 receives terminal external governance decisions submitted by human actors, validates each resolution attempt for structural eligibility against the active Policy Profile, records all resolution activity with full traceability, and closes open governance outcomes through four closure paths: RESOLVED, SUPERSEDED, EXPIRED, INVALIDATED.

All outcome closures produce governance events that M11 reads to detect whether a Governance Pause has been lifted and resume conditions are met.

This command implements Stage 13 — Governance Outcome Resolution Runtime of the CSR pipeline.

---

## Specification Layers

Read and assimilate all three specification layers before executing:

```text
Layer 1 contract:       ${CLAUDE_PLUGIN_ROOT}/docs/commands/governance-resolve.md
Layer 2 execution spec: ${CLAUDE_PLUGIN_ROOT}/docs/commands/governance-resolve_execution.md
Layer 3 prompt:         ${CLAUDE_PLUGIN_ROOT}/templates/prompts/governance_resolve_prompt.md
```

Layer 1 defines what M13 does: invocation modes, outcome lifecycle model, four closure paths, closure path precedence, resolution model, validity model, runtime invariants (RI-01 through RI-10), failure model, and traceability requirements.

Layer 2 defines how M13 executes: the 12-phase sequence (Phase 0–11), reconstruction rules (RR-1 through RR-7), decision rules (RD-1 through RD-10), runtime actions (RA-01 through RA-07), execution invariants (EI-01 through EI-11), event formats, governance projection format, and session result codes.

Layer 3 defines behavioral intent: what M13 must always do, must never do, and how to reason at each phase.

The repository is the source of truth. Do not rely on prior conversational context. All behavioral rules and execution procedures are defined in L1, L2, and L3.

---

## Invocation Context

M13 is user-invoked. It is invoked directly by human actors with governance authority, not programmatically by M11 or M12.

```text
/governance-resolve                       → STATUS mode
/governance-resolve <outcome_id>          → INSPECT mode
/governance-resolve <outcome_id> APPROVED → RESOLVE mode
/governance-resolve <outcome_id> REJECTED → RESOLVE mode
/governance-resolve <outcome_id> DENIED   → RESOLVE mode
/governance-resolve --validate            → VALIDATE mode
```

| Mode | Purpose | User supplies |
|------|---------|---------------|
| STATUS | Present all open outcomes. Run validity evaluation. | No arguments |
| INSPECT | Present full detail for one outcome. Run validity evaluation. | `<outcome_id>` |
| RESOLVE | Submit a terminal decision for one open outcome. | `<outcome_id>` + `APPROVED`, `REJECTED`, or `DENIED` |
| VALIDATE | Run validity evaluation only. Close all invalid outcomes. | `--validate` |

RESOLVE mode is the only mode that appends RESOLUTION_RECEIVED, RESOLUTION_RECORDED, or RESOLUTION_REJECTED. VALIDATE mode closes outcomes through validity closure paths only (SUPERSEDED, EXPIRED, INVALIDATED) and does not accept terminal decisions.

If the invocation form is unrecognizable: BLOCKED. Stop. No event appended.

---

## Required Runtime Inputs

Before executing, verify all required inputs are accessible:

| Input | Path | Required |
|-------|------|----------|
| Governance event log | `WORKSPACE_ROOT/runtime/governance/events.md` | Required if exists; absent → initialize on first invocation |
| Active Policy Profile | `WORKSPACE_ROOT/governance/policy_profile.md` | REQUIRED — required in all modes |
| Workspace resolver | `runtime/current_workspace.md` | REQUIRED |
| Workspace registry | `runtime/workspaces.md` | REQUIRED |
| M13 Layer 1 | `${CLAUDE_PLUGIN_ROOT}/docs/commands/governance-resolve.md` | REQUIRED |
| M11 event log | `WORKSPACE_ROOT/runtime/pipeline/events.md` | Optional — flag `m11_events_readable`; INVALIDATED check skipped if absent |
| Target outcome_id | Invocation argument | REQUIRED for RESOLVE and INSPECT modes |
| Decision type | Invocation argument | REQUIRED for RESOLVE mode — must be APPROVED, REJECTED, or DENIED |

`governance_state.md` is a write target, not a required input. It is never used as a derivation authority. If absent: first invocation creates it at Phase 10. If present: overwritten at Phase 10. Its absence or corruption does not affect reconstruction.

If any REQUIRED input is absent or unreadable: BLOCKED. Stop. Do not proceed to execution.

---

## Runtime Loading Procedure

### Step 1 — Load Specification Layers

Read and assimilate in order:

1. `${CLAUDE_PLUGIN_ROOT}/docs/commands/governance-resolve.md` — Layer 1 Contract
2. `${CLAUDE_PLUGIN_ROOT}/docs/commands/governance-resolve_execution.md` — Layer 2 Execution Specification
3. `${CLAUDE_PLUGIN_ROOT}/templates/prompts/governance_resolve_prompt.md` — Layer 3 Behavioral Prompt

Layer 3 is the executable behavioral authority for this session. All phase execution, decision routing, event writing, and failure handling follow L3 behavioral intent as grounded in L1 and L2.

Do not proceed to Step 2 until all three layers are read and assimilated.

### Step 2 — Load Runtime Artifacts

1. Read `runtime/current_workspace.md`. Parse `workspace_id`.
2. Construct `WORKSPACE_ROOT = workspaces/<workspace_id>/`.
3. Verify `WORKSPACE_ROOT` exists.
4. Validate registry entry in `runtime/workspaces.md` (R4a–R4e per L2 Phase 1.4).
5. Read or initialize `WORKSPACE_ROOT/runtime/governance/events.md`.
6. Read active Policy Profile at `WORKSPACE_ROOT/governance/policy_profile.md`. Parse `current_policy_version`.
7. Attempt to read `WORKSPACE_ROOT/runtime/pipeline/events.md`. Record `m11_events_readable` flag.

Workspace resolution and artifact loading follow L2 Phase 1 and Phase 2 procedures.

---

## Workspace Isolation Enforcement

M13 owns exactly two artifacts and one directory:

```text
WORKSPACE_ROOT/runtime/governance/events.md             (append-only)
WORKSPACE_ROOT/runtime/governance/governance_state.md   (overwrite)
WORKSPACE_ROOT/runtime/governance/                      (created on first invocation if absent)
```

**`governance_state.md` is exclusively owned and written by M13.** This constraint is compatible with DMA-05: M12 must not write to `governance_state.md`. M12 records all governance evaluation state through the shared event log only. A write to `governance_state.md` by M12 constitutes a workspace contamination violation against M13's owned artifact.

**All other writes are prohibited. The following paths are explicitly prohibited:**

```text
WORKSPACE_ROOT/runtime/pipeline/events.md       ← NEVER WRITTEN BY M13 (M11 event log — read-only)
WORKSPACE_ROOT/runtime/pipeline/pipeline_state.md ← NEVER WRITTEN BY M13 (M11 artifact)
```

M13 must not write to any M11 artifact, any M12 artifact outside the shared governance event log, or any business artifact (knowledge_base, specifications, input, output).

If a write to any path outside the two owned artifacts and owned directory is about to occur: stop immediately. Report workspace contamination. Terminate with session result FAILED. Follow the Contamination Protocol defined in L3.

---

## Execution Procedure

Execute the runtime defined in `${CLAUDE_PLUGIN_ROOT}/templates/prompts/governance_resolve_prompt.md`.

All phase logic, decision trees, and behavioral constraints are defined in L1, L2, and L3. Do not reproduce them here. The high-level execution sequence is:

**Phase 0:** Parse invocation. Assign session_ref. Determine MODE. Extract target_outcome_id and decision_type if applicable. BLOCKED on unrecognized invocation.

**Phase 1:** Resolve workspace. Construct WORKSPACE_ROOT. Validate registry entry R4a–R4e.

**Phase 2:** Verify required artifacts. Initialize governance directory and event log on first invocation. Load active Policy Profile. Record `m11_events_readable` flag.

**Phase 3:** Confirm session context. Validate mode-specific preconditions.

**Phase 4:** Read all events from `WORKSPACE_ROOT/runtime/governance/events.md` into `event_log_chronology`. Identify M12-produced creation events (ESCALATION_RECORDED, DELEGATION_ASSIGNED) as candidate outcomes. Extract required fields. Apply DMA WARNING for any absent field. **Never read `governance_state.md` as input to this phase** (AD-001, RI-09, EI-09).

**Phase 5:** Classify each candidate outcome as OPEN or CLOSED by scanning `event_log_chronology` for terminal lifecycle events. Build OPEN_SET, CLOSED_SET, ALL_OUTCOMES.

**Phase 6:** Execute validity evaluation against all outcomes in OPEN_SET — mandatory in all modes, completes before Phase 7 (RI-05, EI-05). Apply SUPERSEDED check (Step 6a), EXPIRED check for DELEGATION_ASSIGNED outcomes (Step 6b), INVALIDATED check using M11 events.md if readable (Step 6c). Append OUTCOME_SUPERSEDED (RA-03), DELEGATION_EXPIRED (RA-04), or OUTCOME_INVALIDATED (RA-05) for each failing outcome, with EI-11 guard before each append.

**Phase 7:** Route by MODE. STATUS presents OPEN_SET. VALIDATE produces no table. INSPECT verifies target_outcome_id in ALL_OUTCOMES and presents full record. RESOLVE verifies target_outcome_id in OPEN_SET — BLOCKED if in CLOSED_SET, BLOCKED if not found. Proceed to Phase 8 only if OPEN.

**Phase 8 (RESOLVE only):** Append RESOLUTION_RECEIVED (RA-01) as unconditional first step. Validate authority eligibility (RD-7). Validate terminal decision type (RD-8 — defensive). Append RESOLUTION_REJECTED (RA-06) on failure. Proceed to Phase 9 on success.

**Phase 9 (RESOLVE, validation-passed only):** Append RESOLUTION_RECORDED (RA-02). Transition outcome to CLOSED in session context.

**Phase 10:** Refresh governance projection. Build governance_state.md from current OPEN_SET and CLOSED_SET per L2 Section 7 format. Execute RA-07 (overwrite). **All event appends for this session must complete before Phase 10 executes** (RI-10, EI-10).

**Phase 11:** Determine session result code (RD-10). Report result including session_ref, VALIDITY_CLOSURE_COUNT, mode-specific fields, and all WARNINGs issued.

---

## Event Persistence Requirements

All M13-produced events are appended to `WORKSPACE_ROOT/runtime/governance/events.md`. The event log is append-only. No existing event record is modified after it is written (RI-06, EI-06).

### Event Ordering Invariants

| Rule | Requirement | Source |
|------|-------------|--------|
| EI-04 | RESOLUTION_RECEIVED appended before RESOLUTION_RECORDED or RESOLUTION_REJECTED | RI-04 |
| EI-10 | All event appends complete before governance_state.md is written | RI-10 |
| EI-11 | EI-11 guard verified before each of RA-03, RA-04, RA-05 — no second terminal lifecycle event per outcome_id | EI-11 |
| EI-05 | Phase 6 (all validity closure event appends) completes before Phase 8 begins | RI-05 |
| EI-06 | events.md is append-only — no modification of existing records | RI-06 |

### Event Type Ownership

M13 owns and appends exactly the following event types. No other event types are appended by M13:

| Event Type | Trigger | Phase |
|-----------|---------|-------|
| `RESOLUTION_RECEIVED` | Every RESOLVE mode invocation reaching Phase 8 — before any validation result | Phase 8.2 (RA-01) |
| `RESOLUTION_RECORDED` | Valid terminal decision accepted | Phase 9.1 (RA-02) |
| `RESOLUTION_REJECTED` | Resolution attempt failed authority or decision type validation | Phase 8.3 or 8.4 (RA-06) |
| `OUTCOME_SUPERSEDED` | Open outcome policy version differs from current | Phase 6.2 (RA-03) |
| `DELEGATION_EXPIRED` | DELEGATION_ASSIGNED outcome elapsed time exceeds tier response interval | Phase 6.3 (RA-04) |
| `OUTCOME_INVALIDATED` | Open outcome meets ORIGINATING_SESSION_TERMINAL, NEWER_SESSION_EXISTS, or BASE_CLOSED condition | Phase 6.4 (RA-05) |

M13 must never append ESCALATION_RECORDED, DELEGATION_ASSIGNED, or any M11 or M12 event type (RI-02, EI-02). If any execution path would append these types: stop immediately.

### DMA Field Requirements

DMA-01 (policy_version), DMA-02 (session_id), and DMA-03 (tier) are APPLIED in M12 L2. M13 reads these fields from ESCALATION_RECORDED and DELEGATION_ASSIGNED events during Phase 4 reconstruction. If any DMA field is absent in an outcome creation event: emit WARNING identifying the missing field and affected outcome_id. Continue reconstruction with available fields. Do not stop.

---

## Projection Refresh Requirements

`governance_state.md` is exclusively owned and written by M13. It is refreshed at Phase 10 (RA-07) in all modes after all event appends for the session are complete.

**governance_state.md write rules (RA-07, L2 Section 7):**

- Written after all event appends are complete — never before (RI-10, EI-10)
- Content derived from OPEN_SET and CLOSED_SET derived from events.md — never from prior governance_state.md content (RI-09, EI-09)
- Overwrite semantics on every invocation
- If governance_state.md does not exist: created. If it exists: overwritten.
- If write fails (WRITE_FAILURE): event log is authoritative. Projection is reconstructable from events.md on next invocation. Session result = FAILED.

**governance_state.md is never a derivation authority** (RI-09, EI-09). It is a reconstructable projection. Its absence or corruption does not affect Phase 4, 5, 6, 8, or 9 execution.

**DMA-05 compatibility:** M12 must not write to `governance_state.md`. This constraint is enforced on the M12 side. M13 notes any write to `governance_state.md` by M12 as a cross-runtime workspace contamination violation.

---

## Output Contract

M13 returns one session result code per invocation. The output content varies by mode and result:

| Mode | Success Result | Always Returned | Returned on Success | Returned on Failure |
|------|---------------|-----------------|--------------------|--------------------|
| STATUS | `STATUS_COMPLETED` | session_ref, MODE, VALIDITY_CLOSURE_COUNT, WARNINGs | OPEN_SET presentation table | BLOCKED or FAILED message |
| INSPECT | `INSPECTION_COMPLETED` | session_ref, MODE, VALIDITY_CLOSURE_COUNT, WARNINGs | Full outcome record + M13 events for outcome_id | BLOCKED or FAILED message |
| RESOLVE (success) | `RESOLUTION_COMPLETED` | session_ref, MODE, VALIDITY_CLOSURE_COUNT, WARNINGs | outcome_id, decision_type, closure_path = RESOLVED | — |
| RESOLVE (rejection) | `VALIDATION_REJECTED` | session_ref, MODE, VALIDITY_CLOSURE_COUNT, WARNINGs | outcome_id, rejection_reason, submitter | — |
| VALIDATE | `VALIDITY_COMPLETED` | session_ref, MODE, VALIDITY_CLOSURE_COUNT, VALIDITY_CLOSURE_LIST, WARNINGs | — | BLOCKED or FAILED message |

**Session result codes (all modes):**

| Code | Condition |
|------|-----------|
| `RESOLUTION_COMPLETED` | RESOLVE mode — valid terminal decision accepted and recorded |
| `VALIDITY_COMPLETED` | VALIDATE mode — validity evaluation complete |
| `STATUS_COMPLETED` | STATUS mode — open outcomes presented |
| `INSPECTION_COMPLETED` | INSPECT mode — outcome detail presented |
| `VALIDATION_REJECTED` | RESOLVE mode — resolution attempt failed validation |
| `BLOCKED` | Precondition failure, invocation error, or outcome state violation |
| `FAILED` | Write failure on event log or governance projection |

No additional output artifacts are produced. M13 does not write M11 artifacts. M13 does not invoke M12.

Result code semantics and output formats are defined in L2 Section 10, L2 Phase 11.2, and L3 Output Format section.

---

## Failure Contract

All failure conditions, classifications, and result codes are defined in L2 Section 9 (Failure Handling) and L3 (Failure Handling section). Do not invent new failure classes.

| Class | Handling |
|-------|----------|
| `BLOCKED` | Stop session. No partial operation proceeds. RESOLUTION_RECEIVED is never appended for any BLOCKED condition. |
| `VALIDATION_FAILURE` | RESOLUTION_RECEIVED appended. RESOLUTION_REJECTED appended. Outcome remains OPEN. Session continues to Phase 10. |
| `WARNING` | Reduced capability. Session continues. All WARNINGs reported in Phase 11 and governance_state.md Warnings section. |
| `WRITE_FAILURE` | Stop event processing for the affected outcome. Varies by event type — see L2 Section 9 WRITE_FAILURE. |

BLOCKED conditions and their messages are enumerated in L2 Section 9 and L3 Failure Handling section.

WRITE_FAILURE on RESOLUTION_RECEIVED (RA-01): session result = FAILED. No subsequent event appended.

WRITE_FAILURE on validity closure events (RA-03 through RA-05): record failure for affected outcome. Continue remaining outcomes. Report at Phase 11.

WRITE_FAILURE on RESOLUTION_RECORDED (RA-02) or RESOLUTION_REJECTED (RA-06): session result = FAILED. Stop. Do not proceed to Phase 10.

WRITE_FAILURE on governance_state.md (RA-07): session result = FAILED. Event log is authoritative. Data integrity is not compromised.

---

## Validation

Before reporting session completion, verify all of the following gates:

| Gate | Requirement |
|------|-------------|
| VG-1 | `${CLAUDE_PLUGIN_ROOT}/docs/commands/governance-resolve.md` (L1) was read and assimilated before execution began |
| VG-2 | `${CLAUDE_PLUGIN_ROOT}/docs/commands/governance-resolve_execution.md` (L2) was read and assimilated before execution began |
| VG-3 | `${CLAUDE_PLUGIN_ROOT}/templates/prompts/governance_resolve_prompt.md` (L3) was read and assimilated before execution began |
| VG-4 | `governance_state.md` was never read as a derivation input during Phase 4, 5, 6, 8, or 9 (RI-09, EI-09 enforced) |
| VG-5 | `governance_state.md` was never used as a derivation authority — all outcome state derived from `events.md` only |
| VG-6 | All writes to `governance_state.md` executed after all event appends for this session (RI-10, EI-10 enforced) |
| VG-7 | M11 was not invoked at any point during this session (RI-07, EI-07 enforced) |
| VG-8 | M12 was not invoked at any point during this session (RI-07, EI-07 enforced) |
| VG-9 | No write occurred outside `WORKSPACE_ROOT/runtime/governance/events.md` and `governance_state.md` (workspace isolation enforced) |
| VG-10 | Output matches the session result code and mode-specific output defined in L1/L2 Output Contract — no additional outputs produced |
| VG-11 | No behavioral rule was applied that is not traceable to L1, L2, or L3 |

If any gate fails: report the failing gate and the violation. Terminate with session result FAILED.
