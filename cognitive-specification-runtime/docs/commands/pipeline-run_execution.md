# Pipeline Coordination Runtime — Execution Specification

## Purpose

Define the runtime execution procedure for the Pipeline Coordination Runtime.

The Layer 1 contract (`docs/commands/pipeline-run.md`) defines what the runtime does. This document defines how it executes: the phase sequence, state reconstruction algorithm, capability assessment model, plan generation procedure, confirmation gate, execution loop, interactive breakpoint protocol, failure handling, recovery model, projection update rules, validation procedures, idempotency rules, and session result determination.

This specification implements Stage 11 — Workspace State Coordination Runtime of the CSR pipeline.

---

## Execution Flow

```text
Phase 0  — Session Initialization
    ↓
Phase 1  — Workspace Validation
    ↓
Phase 2  — M11 Directory Initialization
    ↓
Phase 3  — Target Resolution
    ↓
Phase 4  — State Reconstruction
    ↓
Phase 5  — Event Resolution
    ↓
Phase 6  — Goal Decomposition
    ↓
Phase 7  — Capability Assessment
    ↓
Phase 8  — Plan Generation
    ↓
Phase 9  — Confirmation Gate
    ↓
Phase 9.5 — Initial Governance Evaluation Gate
    ↓
Phase 10 — Plan Execution Loop
    ↓
Phase 11 — Interactive Breakpoint Protocol (entered from Phase 10 as needed)
    ↓
Phase 12 — Session Result Determination
    ↓
Phase 13 — Failure Handling
    ↓
Phase 14 — Projection Update

[Branch Phases — Entered from Phase 5 Event Resolution]
Phase 8.G — Governance Gate Resume Procedure (entered from Phase 5.5 on GOVERNANCE_RESOLVED; exits to Phase 9 on GOVERNANCE_COMPLETE or terminates)

[Cross-Cutting Reference Phases]
Phase 15 — Validation Rules
Phase 16 — Idempotency Rules
Phase 17 — Failure Scenarios
Phase 18 — Success Conditions
```

Phases 0–14 are sequential per session. Phases 15–18 are cross-cutting references.

---

## Definitions

**Base Identifier (B):** The stem name shared by all artifacts belonging to one specification source group (e.g., `project_alpha`). Derived from the filename stem of the extracted knowledge artifact: `knowledge_base/extracted/<B>_knowledge.md`.

**Capability:** A binary condition that indicates whether a required artifact or artifact state exists for a given base B. Capabilities are assessed from workspace artifacts at runtime. They are not stored.

**Capability Gap:** The set of capabilities required to reach the goal state that are not currently satisfied for base B.

**Coordination Plan:** An ordered sequence of plan steps computed to close the capability gap for base B. Each plan step maps to one M1–M10 command invocation.

**Plan Step:** A single, atomic command invocation within a Coordination Plan. Each plan step has a defined type (AUTO or INTERACTIVE), a target command, an expected postcondition, and a failure classification.

**AUTO Step:** A plan step that M11 executes without human interaction. M11 invokes the command and evaluates the postcondition.

**INTERACTIVE Step:** A plan step that requires human action before M11 can proceed. M11 announces the required action, emits a PAUSE event, and suspends execution for the affected base.

**Session Identifier (session_id):** A workspace-scoped unique identifier for the current invocation of `/pipeline-run`. Format: `SES-NNN` where NNN is a zero-padded decimal counter, incrementing from the count of SESSION_START events previously recorded in `events.md`. First session in a workspace: `SES-001`.

**Projection Drift:** A condition where the derived coordination state of a base (computed from workspace artifacts) disagrees with the cached state in `pipeline_state.md`. Projection Drift is resolved in favour of the derived state. It is reported as a WARNING to the user. It is not a blocking failure.

**Targetable State:** A coordination state that may be specified as a goal target in a `/pipeline-run <base> <target_state>` invocation. Targetable states: KNOWLEDGE_READY, SPECIFICATION_READY, BASELINED, CLOSED. States DISCOVERING, AWAITING_VALIDATION, and UNDER_REVISION are non-targetable; they are entered automatically via the state transition table.

---

## Preconditions

Before Phase 0 begins, verify:

| ID | Precondition | Action on Failure |
|----|--------------|-------------------|
| PRE-01 | `docs/commands/pipeline-run.md` exists and is readable | Stop. Report: `BLOCKED — L1 contract not found: docs/commands/pipeline-run.md` |
| PRE-02 | `runtime/current_workspace.md` is readable or absent | Stop if unreadable-but-present. Absent triggers Phase 1 drift handling. |
| PRE-03 | `runtime/workspaces.md` is readable | Stop. Report: `BLOCKED — Workspace registry unavailable` |

---

## Phase 0 — Session Initialization

**0.1 Determine Session ID (Deferred)**

Session identifier (session_id) derivation requires `WORKSPACE_ROOT`, which is not yet known at this phase. Assignment is deferred to Phase 1 step R5.1, after workspace validation confirms the workspace root path. No file operations are performed in this step.

**0.2 Assign Session Timestamp**

Record `session_start_timestamp` as the current ISO 8601 timestamp.

**0.3 Determine Invocation Form**

Parse the invocation arguments to determine one of three forms (details in Phase 3):

| Form | Arguments | Mode |
|------|-----------|------|
| Status View | none | STATUS |
| Advance to Next | `<base>` or `ALL` | NEXT |
| Advance to Target | `<base> <target_state>` or `ALL <target_state>` | TARGET |
| Lifecycle Event Signal | `<base> --event BASELINE_REQUEST`, `<base> --event ARCHIVE_REQUEST`, or `<base> --event GOVERNANCE_RESOLVED` | EVENT |

Do not record the SESSION_START event until workspace validation (Phase 1) passes. If Phase 1 fails, no session record is created.

---

## Phase 1 — Workspace Validation

Execute the standard workspace resolution and registry validation.

**R1 — Read Resolver**

Read `runtime/current_workspace.md`. Parse `workspace_id` from:

```text
workspace_id: <value>
```

If absent or unparseable: workspace_id = UNRESOLVED. Proceed to R4 to check registry for a single `active` entry. If none found: report `BLOCKED — Active workspace cannot be resolved` and stop.

**R2 — Build WORKSPACE_ROOT**

Construct `WORKSPACE_ROOT = workspaces/<workspace_id>/`

**R3 — Verify Workspace Root**

Confirm `WORKSPACE_ROOT` directory exists.

If not found: report `BLOCKED — Workspace Root Not Found: workspaces/<workspace_id>/` and stop.

**R4 — Validate Registry Entry**

Read `runtime/workspaces.md`. Locate the row where `workspace_id` matches R1.

| Check | Condition | Action |
|-------|-----------|--------|
| R4a | workspace_id present in registry | If missing: `BLOCKED — Workspace ID not in registry`. Stop. |
| R4b | status is not `archived` | If archived: `BLOCKED — Workspace Archived`. Stop. |
| R4b-warn | status is `paused` or `completed` | `WARNING — Registry status is '<status>', expected 'active'`. Proceed. |
| R4c | runtime_version is present | `WARNING — Registry entry incomplete: runtime_version missing`. Proceed. |
| R4d | last_active is present | `WARNING — Registry entry incomplete: last_active missing`. Proceed. |
| R4e | exactly one `active` entry | `WARNING — Multiple active entries detected. Using runtime/workspaces.md as authority`. Use registry-designated active workspace. |

If workspace_id from resolver (R1) disagrees with the registry-designated active workspace: report Projection Drift as a WARNING. Proceed using the registry authority.

**R5 — Confirm Workspace**

Report:

```text
Active workspace: <workspace_id>
WORKSPACE_ROOT: workspaces/<workspace_id>/
```

**R5.1 — Assign Session ID**

Scan `WORKSPACE_ROOT/runtime/pipeline/events.md` for all records with `event_type: SESSION_START`. If the file does not exist, the count is zero. session_id = `SES-` + zero-padded (count+1) to 3 digits. First session in a workspace: `SES-001`.

If the file exists but is unreadable: report `BLOCKED — events.md unreadable. Cannot assign session_id.` Stop.

**R6 — SESSION_START Write (Deferred to Phase 2)**

The SESSION_START event is written after Phase 2.2 completes, ensuring the `runtime/pipeline/` directory and `events.md` file exist before the write is attempted. See Phase 2.3.

---

## Phase 2 — M11 Directory Initialization

This phase implements PC0 from the Layer 1 contract.

**2.1 Create runtime/pipeline/ Directory**

Check whether `WORKSPACE_ROOT/runtime/pipeline/` exists.

If it does not exist:
- Create `WORKSPACE_ROOT/runtime/pipeline/`
- If creation fails: report `BLOCKED — Cannot create runtime/pipeline/ directory: <path>`. Stop.

If it exists: proceed.

**2.2 Initialize events.md**

Check whether `WORKSPACE_ROOT/runtime/pipeline/events.md` exists.

If it does not exist: create an empty file at this path. The file is valid when empty.

If it exists and is readable: proceed.

If it exists and is unreadable: report `BLOCKED — events.md exists but is unreadable: <path>`. Stop.

**2.3 Write SESSION_START Event**

Append a SESSION_START event to `WORKSPACE_ROOT/runtime/pipeline/events.md`:

```text
event_id:    <session_id>
session_id:  <session_id>
event_type:  SESSION_START
base:        (empty — workspace-level event)
timestamp:   <session_start_timestamp>
actor:       M11
payload:     { invocation_form: <STATUS|NEXT|TARGET|EVENT>, raw_args: "<args>" }
```

If the append fails: report `BLOCKED — Cannot write SESSION_START to events.md: <path>`. Stop.

**2.4 Validate Append-Only Invariant**

Read `events.md`. Verify that event_id values are sequential with no gaps and no duplicate values. If gaps or duplicates are detected: report `WARNING — events.md append-only invariant may be violated (event_id sequence gap detected)`. Proceed.

**2.5 Initialize or Reconstruct pipeline_state.md**

Check whether `WORKSPACE_ROOT/runtime/pipeline/pipeline_state.md` exists.

- If it does not exist: execute Checkpoint Reconstruction (Phase 4, Section 4.7) after base discovery completes. Flag `reconstruction_required = TRUE`.
- If it exists and is readable: proceed. `reconstruction_required = FALSE`.
- If it exists and is unreadable: execute Checkpoint Reconstruction. Flag `reconstruction_required = TRUE`.

---

## Phase 3 — Target Resolution

This phase implements L2-008 (explicit target required) and L2-001 (ALL → alphabetical).

**3.1 Parse Target**

| Invocation Form | Target | Mode |
|-----------------|--------|------|
| `/pipeline-run` | — | STATUS |
| `/pipeline-run <base>` | single base | NEXT |
| `/pipeline-run ALL` | all non-CLOSED bases | NEXT (ALL) |
| `/pipeline-run <base> <target_state>` | single base with explicit target | TARGET |
| `/pipeline-run ALL <target_state>` | all non-CLOSED bases with explicit target | TARGET (ALL) |
| `/pipeline-run <base> --event BASELINE_REQUEST` | single base with lifecycle signal | EVENT |
| `/pipeline-run <base> --event ARCHIVE_REQUEST` | single base with lifecycle signal | EVENT |
| `/pipeline-run <base> --event GOVERNANCE_RESOLVED` | single base with governance resume signal | EVENT |

**3.2 Validate Target State (TARGET mode only)**

If mode is TARGET: verify that `<target_state>` is one of the Targetable States defined in Definitions. If not: report `BLOCKED — '<target_state>' is not a valid goal target. Valid targets: KNOWLEDGE_READY, SPECIFICATION_READY, BASELINED, CLOSED`. Stop.

**3.3 Discover Bases (ALL mode)**

When target is `ALL`:

1. Scan `WORKSPACE_ROOT/knowledge_base/extracted/` for files matching the pattern `*_knowledge.md`.
2. Extract base identifiers: strip the `_knowledge.md` suffix from each filename stem. The result is the base identifier B.
3. Record extracted_count = count of bases found. These are the extracted bases.

**3.3b — Discover INGESTED Bases (ALL Mode)**

Execute immediately after Phase 3.3 when target is `ALL`:

1. Read `WORKSPACE_ROOT/runtime/sources.md`. If the file does not exist or is empty: ingested_count = 0. Skip to step 4.
2. For each row with Status = `ingested`:
   a. Extract base identifier B from the "Source File" column (stem name, no extension).
   b. Verify `WORKSPACE_ROOT/knowledge_base/extracted/<B>_knowledge.md` does NOT exist.
   c. If not exists: add B to the processing list as an INGESTED candidate. Increment ingested_count.
   d. If exists: skip — this base is already covered by the Phase 3.3 extracted scan.
3. ingested_count = number of new INGESTED bases added.
4. If extracted_count = 0 AND ingested_count = 0: report `BLOCKED — No bases found in this workspace. Run /ingest-source to register a source, then /pipeline-run.` Stop.
5. Sort the combined processing list (extracted bases + ingested bases) in ascending alphabetical order of base identifier (L2-001).
6. Process bases in this order throughout Phases 5–12. CLOSED bases are filtered out in Phase 4.5 after state derivation completes.

**3.4 Validate Named Base (NEXT and TARGET modes)**

When a specific base B is named:

1. Check A: Verify `WORKSPACE_ROOT/knowledge_base/extracted/<B>_knowledge.md` exists.
2. If A satisfied: base B confirmed (extracted). Proceed.
3. If A not satisfied — Check B: Read `WORKSPACE_ROOT/runtime/sources.md`. Look for a row with "Source File" stem matching B and Status = `ingested`.
4. If B satisfied: base B is in INGESTED state. Mark for SD-0 derivation in Phase 4.1. Proceed.
5. If neither A nor B: report `BLOCKED — Base '<B>' not found. No extracted knowledge artifact at knowledge_base/extracted/<B>_knowledge.md and no ingested source for '<B>' in runtime/sources.md.` Stop.

**3.5 Open Governance Outcome Scan (NEXT, TARGET and ALL modes)**

Execute for every invocation that does **not** carry `--event GOVERNANCE_RESOLVED`. The EVENT-mode resume path performs its own, stricter verification at Phase 5.5 and is out of scope here.

1. Read `WORKSPACE_ROOT/runtime/governance/events.md`. If absent: the Open Outcome Set is empty; proceed to Phase 4.
2. Reconstruct open outcomes the same way M13 does (RR-1 / AD-001): an `ESCALATION_RECORDED` or `DELEGATION_ASSIGNED` is **open** unless a later event carrying the same `outcome_id` closes it — `RESOLUTION_RECORDED`, `OUTCOME_SUPERSEDED`, `DELEGATION_EXPIRED` or `OUTCOME_INVALIDATED`.
3. Keep those whose `base_id` is among the bases this invocation targets. This is the **Open Outcome Set**.
4. If the set is empty: proceed to Phase 4 with no further action.
5. If the set is non-empty, report — before any plan is generated:

```text
GOVERNANCE PAUSE OPEN — this invocation would proceed past an unresolved governance outcome.

  <base_id> — <outcome_id> (<outcome_type>, opened <timestamp>, tier <tier>)
  [one line per open outcome]

This invocation form does not consult governance pauses. Phase 5.5, which resumes a paused
base and verifies the outcome is closed, applies only to `--event GOVERNANCE_RESOLVED`.
Continuing re-derives coordination state from workspace artifacts alone and may execute the
very step the pause was recorded to hold.

Resolve the outcome with /governance-resolve and resume with
  /pipeline-run <base> --event GOVERNANCE_RESOLVED
or confirm explicitly that this invocation should proceed regardless.
```

Require explicit human confirmation. Without it: stop, write nothing, append no event.

6. On confirmation, append one event per bypassed outcome to `WORKSPACE_ROOT/runtime/pipeline/events.md` **before** continuing:

```text
event_type:  GOVERNANCE_PAUSE_BYPASSED
session_id:  <session_id>
base:        <base_id>
timestamp:   <ISO 8601>
actor:       M11
payload:
  outcome_id:      <outcome_id>
  outcome_type:    <ESCALATION_RECORDED | DELEGATION_ASSIGNED>
  invocation_form: <NEXT | TARGET | ALL>
  confirmed_by:    <human actor>
```

Then proceed to Phase 4.

> **Why this warns and confirms rather than blocking.** Refusing the invocation outright would be the stronger guarantee, and it is deliberately not chosen. The M12 evaluator does not implement rule-level preconditions (`docs/commands/governance-run_execution.md`, DT-2), so an unconditional ESCALATE rule reproduces its verdict on every re-evaluation and an M13 resolution carries no execution authority (PE-7, GP-08, I-8G-02). A base caught in such a loop has no convergent exit. Blocking the non-EVENT invocation forms would remove the last one and deadlock the workspace, leaving a by-name policy derogation as the only escape — which is worse, because it is permanent and invisible.
>
> What was actually wrong was never that the bypass existed; it was that it was **silent**. Phase 5.1 assigns a new session unconditionally and a plain TARGET invocation consults no prior PAUSE record at all, so on 2026-10-30 sessions SES-005 and SES-006 of workspace `demo-inventory-01` baselined two specifications while `VD-GS-20261030-093000-001` and `VD-GS-20261030-094000-001` were — and still are — open, with nothing in the pipeline log marking that a pause had been passed. This step makes the bypass deliberate and auditable without removing it. See finding F-05 of (internal review note).
>
> When the second half of R4 lands and conditions over governance history become expressible, the escape hatch stops being necessary and this step can be reconsidered as a hard block.

---

## Phase 4 — State Reconstruction

State reconstruction derives the authoritative coordination state for each target base from workspace artifacts. Reconstruction follows L2-004.

**Authority Order (L2-004):**

1. M8/M9 lifecycle artifacts (`specifications/lifecycle/specifications_lifecycle.md`)
2. M10 workspace lifecycle artifacts (`runtime/workspaces.md`)
3. Questions, validations, specifications
4. Event history (consulted last, for resume flag derivation only)
5. Rebuilt projection

`pipeline_state.md` is never used as a reconstruction authority. It is a write target, not a read source.

**4.1 State Derivation Decision Tree**

For each base B, evaluate the following steps in order. Apply the first matching condition and stop.

**SD-0 — INGESTED check:**

1. Verify `WORKSPACE_ROOT/knowledge_base/extracted/<B>_knowledge.md` does NOT exist.
2. Read `WORKSPACE_ROOT/runtime/sources.md`. Check for a row with "Source File" stem matching B and Status = `ingested`.
3. If both conditions hold: **state = INGESTED**. Stop evaluation.

SD-0 fires before all other rules. If the extracted knowledge artifact is absent and the source is registered as ingested, the base is pre-extraction. All subsequent SD rules (SD-1 through SD-7) assume the extracted artifact exists and will not match correctly without it.

**SD-1 — CLOSED check:**

1. Read `WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md`.
2. If the file exists: build the chronological event chain for base B (all BASELINE, REOPEN, EVOLVE, and ARCHIVE events where the specification path contains base stem B).
3. If an ARCHIVE event exists in the chain AND the ARCHIVE event is the most recent event in the chain for this base: **state = CLOSED**.

**SD-2 — BASELINED check:**

1. Using the lifecycle event chain from SD-1 (or an empty chain if the file does not exist):
2. If the chain contains at least one BASELINE event AND the most recent event in the chain is a BASELINE event (no REOPEN, EVOLVE, or ARCHIVE recorded after the most recent BASELINE): **state = BASELINED**.

**SD-3 — UNDER_REVISION check:**

1. If the lifecycle event chain contains at least one BASELINE event for base B:
2. AND `WORKSPACE_ROOT/specifications/draft/<B>_specification.md` currently exists:
3. **state = UNDER_REVISION**.

This condition is satisfied when REOPEN or EVOLVE has been performed (creating or returning a draft) after a prior baseline.

**SD-4 — SPECIFICATION_READY check:**

1. If `WORKSPACE_ROOT/specifications/draft/<B>_specification.md` exists:
2. AND (the lifecycle event chain contains no BASELINE event for base B OR the lifecycle file does not exist):
3. **state = SPECIFICATION_READY**.

**SD-5 — KNOWLEDGE_READY check:**

1. Read `WORKSPACE_ROOT/knowledge_base/questions/questions_report.md`.
2. If the file does not exist OR it contains no questions for base B: open_question_count = 0.
3. Else: count questions for base B with status `UNANSWERED`, `PARTIALLY_ANSWERED`, or `REJECTED`. Set open_question_count to this count.
4. Read `WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md`. If the file does not exist: unresolved_conflict_count = 0. Else: count conflicts for base B with status other than `CONSOLIDATED`. Set unresolved_conflict_count to this count.
5. If open_question_count = 0 AND unresolved_conflict_count = 0 AND no draft specification exists for B: **state = KNOWLEDGE_READY**.

Rationale: a base cannot become KNOWLEDGE_READY when unresolved conflict processing remains pending. If M3 detected conflicts but M4 has not yet generated questions for them, open_question_count is vacuously zero but the conflict pipeline is incomplete. Both conditions must be clear before KNOWLEDGE_READY is assigned.

**SD-6 — AWAITING_VALIDATION check:**

1. If `questions_report.md` exists AND contains at least one question for base B with status `UNANSWERED`, `PARTIALLY_ANSWERED`, or `REJECTED`:
2. **state = AWAITING_VALIDATION**.

**SD-7 — DISCOVERING (default):**

If none of SD-1 through SD-6 matched: **state = DISCOVERING**.

Note: SD-7 applies when `knowledge_base/extracted/<B>_knowledge.md` exists but no higher-state conditions are satisfied.

**4.2 Projection Drift Detection**

After deriving the coordination state for each base:

1. If `pipeline_state.md` exists and is readable: read the cached coordination state for each base.
2. If the derived state disagrees with the cached state: Projection Drift is detected.
3. Report a WARNING for each base with detected drift: `WARNING — Projection Drift: base '<B>' derived state is '<new>' but projection shows '<old>'. Derived state takes precedence.`
4. The derived state is used. The projection is updated in Phase 14.

**4.3 NEW_SOURCE Event Detection**

Projection Drift from BASELINED to UNDER_REVISION (or any non-advancing direction) that is not accounted for by a recorded Change Event may indicate a NEW_SOURCE condition.

If derived state for base B is UNDER_REVISION AND projection shows BASELINED AND no Change Event exists in events.md for base B since the most recent BASELINE event:

1. Record a NEW_SOURCE event for base B.
2. Transition B's derived state to UNDER_REVISION (already derived as such; record confirms it).

This handles the case where an additional extraction has been performed outside of an M11 session.

**4.4 Checkpoint Reconstruction**

Executed when `reconstruction_required = TRUE` (Phase 2.5).

1. Discover all bases:
   a. Scan `WORKSPACE_ROOT/knowledge_base/extracted/` for `*_knowledge.md` files and extract base identifiers (extracted bases).
   b. Read `WORKSPACE_ROOT/runtime/sources.md`. For each row with Status = `ingested`: extract the stem B from the "Source File" column. If `WORKSPACE_ROOT/knowledge_base/extracted/<B>_knowledge.md` does NOT exist: add B to the base list (ingested bases).
   c. Combine both lists. Remove duplicates (a base present in both is covered by the extracted scan). Apply SD-0 in Phase 4.1 for bases found only via the sources.md scan.
2. For each discovered base B: apply the State Derivation Decision Tree (Section 4.1).
3. For each base B: determine `last_event_id` by scanning `events.md` for the most recent event with `base = B`. If no events exist for B: last_event_id = none.
4. Derive all business flags for each base (per Phase 14 flag derivation rules).
5. Write the reconstructed `pipeline_state.md`.
6. Append a CHECKPOINT_RECONSTRUCTION internal event to `events.md`.

Checkpoint Reconstruction does not modify any M1–M10 artifact. It is a read-then-write operation on M11-owned files only.

**4.5 Filter CLOSED Bases (ALL mode)**

When mode is ALL: after state derivation is complete for all discovered bases, remove any base B where derived state = CLOSED from the processing list.

1. For each discovered base B: check the derived coordination state from Phase 4.1.
2. If state = CLOSED: remove B from the processing list. Report: `Base '<B>' is CLOSED — skipped.`
3. If all discovered bases are CLOSED: report `BLOCKED — All bases are CLOSED. No bases to process.` Stop.
4. Continue with the filtered processing list in Phase 5.

CLOSED bases are not counted in session result computations. They are excluded silently after the skip report.

---

## Phase 5 — Event Resolution

This phase processes incoming Change Events declared by the user at invocation time, and applies the Revision Rule (L1 Section 4).

**5.1 Identify Incoming Change Events**

Incoming Change Events are declared via invocation parameters:

| Event Type | Invocation Signal |
|------------|-------------------|
| `CHANGE_REQUEST` | User explicitly requests a change against a named base |
| `DECISION_OVERRIDE` | User declares a decision override for a named base |

`NEW_SOURCE` Change Events are detected automatically in Phase 4.3. They do not arrive via invocation parameters.

**5.2 Apply the Revision Rule**

For each incoming Change Event against base B:

1. Read the current derived coordination state of B (from Phase 4).
2. If state = BASELINED:
   a. Record the Change Event in `events.md`.
   b. Transition B's coordination state to UNDER_REVISION.
   c. Update `pipeline_state.md` immediately (before plan generation).
   d. Report to user: `Revision Rule applied: base '<B>' transitioned to UNDER_REVISION.`
3. If state ≠ BASELINED and the Change Event is CHANGE_REQUEST:
   a. Record the Change Event.
   b. Do not alter the coordination state (the Revision Rule applies only when BASELINED).
   c. Report: `CHANGE_REQUEST recorded for base '<B>' (current state: <state>).`
4. If state = CLOSED: report `WARNING — Change Event received against a CLOSED base '<B>'. No transition applied. CLOSED is terminal.`

**5.3 Revision Rule Invariant**

The Revision Rule is mandatory with no exceptions. Any Change Event received against a BASELINED base must produce the UNDER_REVISION transition. An implementation that processes a Change Event against a BASELINED base without transitioning to UNDER_REVISION violates this contract.

**5.4 Lifecycle Event Signal Routing (EVENT mode)**

When mode is EVENT (invocation includes `--event BASELINE_REQUEST` or `--event ARCHIVE_REQUEST`):

1. Verify base B was validated in Phase 3.4 (extracted knowledge artifact exists).
2. Verify base B has `resume_available = TRUE` in `pipeline_state.md` OR a PAUSE event exists in `events.md` for B in a session with no subsequent SESSION_END marking SUCCESS or ALREADY_SATISFIED for B.
   - If no resumable pause point exists: report `BLOCKED — Base '<B>' is not paused at a resumable step. Cannot process <EVENT_TYPE> signal.` Stop.
3. Route to Phase 11.3 (Resume Procedure). Pass the event signal (`BASELINE_REQUEST` or `ARCHIVE_REQUEST`) as context so Phase 11.3 step 1 records a RESUME_REQUEST event with `payload: { event_signal: <BASELINE_REQUEST|ARCHIVE_REQUEST> }`. In Phase 11.3 step 5–6, re-present the remaining steps and re-enter the Confirmation Gate before execution.

EVENT mode does not generate a new forward plan. It resumes an existing paused plan from the recorded resume point.

**5.5 Governance Resume Routing (EVENT mode — GOVERNANCE_RESOLVED)**

When mode is EVENT and invocation includes `--event GOVERNANCE_RESOLVED`:

1. Verify base B was validated in Phase 3.4.
2. Detect Governance Gate PAUSE state: scan `WORKSPACE_ROOT/runtime/pipeline/events.md` for PAUSE events for base B with `payload.event_signal = GOVERNANCE_GATE`. Apply the scan precision rule: select the **most recent** such PAUSE event that has **not** been followed by a `GOVERNANCE_RESUME_STARTED` event carrying the same `payload.outcome_id` in `pipeline/events.md`. Confirm no SESSION_END event marking SUCCESS or ALREADY_SATISFIED for B appears after the selected PAUSE event.
   - If no qualifying Governance Gate PAUSE event exists (all prior PAUSE events for B with `event_signal = GOVERNANCE_GATE` have a matching GOVERNANCE_RESUME_STARTED for the same outcome_id): report `BLOCKED — Base '<B>' is not paused at a Governance Gate. GOVERNANCE_RESOLVED signal not applicable.` Stop.
3. Extract `outcome_id` from the PAUSE event payload.
4. Verify the governance outcome is closed: read `WORKSPACE_ROOT/runtime/governance/events.md`. Scan for a closure event with matching `outcome_id` (event_type is one of: RESOLUTION_RECORDED, OUTCOME_SUPERSEDED, DELEGATION_EXPIRED, OUTCOME_INVALIDATED).
   - If no closure event is found: report `BLOCKED — Governance outcome <outcome_id> for base '<B>' has not been closed. Resolve via /governance-resolve before retrying.` Stop.
5. Extract closure type and set `m13_terminal_decision`:

   If closure event type = `RESOLUTION_RECORDED`: extract the terminal decision from the closure event's decision type field. Valid values: `APPROVED`, `REJECTED`, `DENIED`. Set `m13_terminal_decision = <extracted terminal decision>`. If the field is absent or its value is not one of APPROVED, REJECTED, DENIED: report `BLOCKED — Malformed RESOLUTION_RECORDED event: terminal decision field absent or invalid for outcome <outcome_id>.` Stop.

   If closure event type is `OUTCOME_SUPERSEDED`, `DELEGATION_EXPIRED`, or `OUTCOME_INVALIDATED`: set `m13_terminal_decision = LIFECYCLE_CLOSURE`. No terminal decision is extracted. These are governance lifecycle closure events, not human authority decisions.

6. M11 must not treat GOVERNANCE_RESOLVED as human plan-execution approval. No M1–M10 command is executed at this routing step.
7. M11 must not bypass M12 re-evaluation. Route to Phase 8.G — Governance Gate Resume Procedure. Pass: governance result type (passed to Phase 8.G as `m13_terminal_decision`; extracted from the closure event payload in Step 5 above as `governance_result_type`), `outcome_id`, and the remaining plan steps from the PAUSE event payload.

---

## Phase 8.G — Governance Gate Resume Procedure

This phase is entered from Phase 5.5 when the invocation is EVENT mode GOVERNANCE_RESOLVED. It is not part of the nominal sequential execution flow (Phases 0–14). On GOVERNANCE_COMPLETE, this phase routes to Phase 9 (Confirmation Gate) for user confirmation before plan execution resumes.

**Inputs (received from Phase 5.5):**

| Input | Description |
|-------|-------------|
| `base_id` | Coordination base being resumed (validated base B from Phase 3.4) |
| `outcome_id` | Governance outcome ID from the Governance Gate PAUSE event |
| `m13_terminal_decision` | M13's terminal decision or governance lifecycle closure type, derived in Phase 5.5 Step 5: APPROVED \| REJECTED \| DENIED \| LIFECYCLE_CLOSURE |
| `remaining_plan_steps` | Plan steps pending at the time of the Governance Gate pause, from the PAUSE event payload |

`m13_terminal_decision` is received from Phase 5.5 Step 5 as `governance_result_type` and renamed here for clarity. It governs the Step 3 branch. It is not used as execution authorization under any condition.

**Step 1 — Append GOVERNANCE_RESUME_STARTED**

Before any reads or derivations, append to `WORKSPACE_ROOT/runtime/pipeline/events.md`:

```text
event_type:  GOVERNANCE_RESUME_STARTED
session_id:  <session_id>
base:        <base_id>
timestamp:   <now>
actor:       M11
payload:     { outcome_id: <outcome_id>, resume_triggered_by: GOVERNANCE_RESOLVED }
```

If this write fails: report `BLOCKED — GOVERNANCE_RESUME_STARTED write failure.` Stop immediately.

**Step 2 — Reconstruct and Verify Execution State**

Apply the same scan precision rule as Phase 5.5 Step 2: read `WORKSPACE_ROOT/runtime/pipeline/events.md` and locate the most recent PAUSE event for base_id with `payload.event_signal = GOVERNANCE_GATE` that has not been followed by a GOVERNANCE_RESUME_STARTED event carrying the same outcome_id.

Verify all three conditions:

1. The PAUSE event exists and `payload.outcome_id` matches the outcome_id supplied by Phase 5.5.
2. `payload.remaining_plan_steps` in the PAUSE event matches the remaining_plan_steps supplied by Phase 5.5.
3. Read `WORKSPACE_ROOT/runtime/governance/events.md`. A closure event with matching `outcome_id` exists (event_type is one of: RESOLUTION_RECORDED, OUTCOME_SUPERSEDED, OUTCOME_INVALIDATED, DELEGATION_EXPIRED).

Failure responses:

- PAUSE event not found: report `BLOCKED — State Reconstruction Failure: no qualifying Governance Gate PAUSE event for base '<B>'.` Stop.
- outcome_id does not match: report `BLOCKED — Outcome ID Discrepancy: PAUSE record carries different outcome_id than Phase 5.5 input.` Stop.
- remaining_plan_steps do not match: report `BLOCKED — Plan State Discrepancy: PAUSE record carries different remaining steps than Phase 5.5 input.` Stop.
- No closure event in governance/events.md: report `BLOCKED — Outcome Not Closed: no closure event found for outcome_id <outcome_id>.` Stop.

After verification, use remaining_plan_steps from the pipeline/events.md PAUSE record as the authoritative plan source. Phase 5.5 inputs are initial references only.

**Step 3 — Branch on Closure Type and Terminal Decision**

If `m13_terminal_decision = REJECTED`:

The escalated action was reviewed by human authority and rejected. M12 must not be invoked.

Append to `WORKSPACE_ROOT/runtime/pipeline/events.md`:

```text
event_type:  GOVERNANCE_RESUME_DENIED
session_id:  <session_id>
base:        <base_id>
timestamp:   <now>
actor:       M11
payload:     { outcome_id: <outcome_id>, reason: M13_REJECTED_TERMINAL_DECISION }
```

If this write fails: stop. Report write failure. M11 is in indeterminate state.

Terminate plan for the affected plan steps. Proceed to Phase 12 (Session Result Determination) with result BLOCKED (reason: governance authorization precondition not met — M13 REJECTED terminal decision). Do not proceed to Step 4.

If `m13_terminal_decision = APPROVED`, `m13_terminal_decision = DENIED`, or `m13_terminal_decision = LIFECYCLE_CLOSURE`: proceed to Step 4.

For `LIFECYCLE_CLOSURE`: the outcome was closed by a governance lifecycle event (policy supersession, delegation expiry, or outcome invalidation), not by a human authority decision. A lifecycle closure does not constitute approval or rejection of the governed plan steps. The correct response is fresh M12 re-evaluation under the current governance state. Invariant I-8G-09 applies.

**Step 4 — Build Resume Plan**

Construct a fresh M11 Plan from the verified remaining_plan_steps using the PAUSE event payload as the authoritative source. Each plan step carries its original fields: `command`, `base_id`, `step_type`, `current_state`, `target_state`.

The prior Governance Verdict Set (from the cycle that produced the original ESCALATE Verdict) is not referenced, not forwarded, and not used at any point in this phase.

If the resume plan contains zero steps: report `BLOCKED — Empty Resume Plan: no remaining plan steps found for base '<B>'.` Stop.

**Step 5 — Append GOVERNANCE_REEVALUATION_REQUESTED**

Append to `WORKSPACE_ROOT/runtime/pipeline/events.md`:

```text
event_type:  GOVERNANCE_REEVALUATION_REQUESTED
session_id:  <session_id>
base:        <base_id>
timestamp:   <now>
actor:       M11
payload:     { outcome_id: <outcome_id>, plan_step_count: <count of steps in resume plan> }
```

If this write fails: report `BLOCKED — GOVERNANCE_REEVALUATION_REQUESTED write failure. M12 must not be invoked.` Stop.

**Step 6 — Invoke M12**

Invoke M12 with the resume plan. This is a complete, independent governance evaluation. M12 reconstructs Governance State from `WORKSPACE_ROOT/runtime/governance/events.md`, which now contains the M13 closure event. M12 returns a Governance Verdict Set and a Governance Cycle Result Code.

**Step 7 — Append GOVERNANCE_REEVALUATION_COMPLETED**

Append to `WORKSPACE_ROOT/runtime/pipeline/events.md`:

```text
event_type:  GOVERNANCE_REEVALUATION_COMPLETED
session_id:  <session_id>
base:        <base_id>
timestamp:   <now>
actor:       M11
payload:     { outcome_id: <outcome_id>, governance_cycle_result: <code>, verdict_count: <count> }
```

If this write fails: stop. Do not route. The unrecorded result cannot authorize or deny execution. Report write failure.

**Step 8 — Route by Governance Cycle Result Code**

| Result Code | Action |
|-------------|--------|
| `GOVERNANCE_COMPLETE` | Proceed to Phase 9 (Confirmation Gate). M12 Verdict Set is the authorization input for the resumed plan. User must confirm before execution resumes. |
| `GOVERNANCE_ESCALATED` | Execute Step 8.1. Enter new Governance Pause. |
| `GOVERNANCE_DENIED` | Append GOVERNANCE_RESUME_DENIED (reason: POLICY_GAP; include denied_step_refs). Terminate affected steps. Report DENY Verdicts to user. Proceed to Phase 12. |
| `GOVERNANCE_FAILED` | Append GOVERNANCE_RESUME_FAILED. Proceed to Phase 12 with result FAILED. |
| `GOVERNANCE_BLOCKED` | Append GOVERNANCE_RESUME_BLOCKED. Proceed to Phase 12 with result BLOCKED. |

**Step 8.1 — GOVERNANCE_ESCALATED Path (Re-Pause)**

Identify the new ESCALATE or DELEGATE Verdict(s) from M12's Verdict Set. Read `WORKSPACE_ROOT/runtime/governance/events.md`. Locate the ESCALATION_RECORDED or DELEGATION_ASSIGNED event written by the current M12 session (match on `m11_session_id` = current session_id). Extract `outcome_id` from that event's `verdict_id` field.

Determine repause_sequence: count all PAUSE events with `payload.event_signal = GOVERNANCE_GATE` for base_id present in `WORKSPACE_ROOT/runtime/pipeline/events.md` including this one. The original Governance Gate pause is sequence 1; the first re-pause is sequence 2.

Append to `WORKSPACE_ROOT/runtime/pipeline/events.md`:

```text
event_type:  PAUSE
session_id:  <session_id>
base:        <base_id>
timestamp:   <now>
actor:       M11
payload:     {
  event_signal:     GOVERNANCE_GATE,
  outcome_id:       <new_outcome_id from new ESCALATE Verdict>,
  prior_outcome_id: <resolved outcome_id>,
  repause_sequence: <integer>,
  remaining_steps:  <remaining_plan_steps>
}
```

Update `pipeline_state.md` for base B: set `resume_available = TRUE`.

Report: `STATUS: GOVERNANCE_REPAUSED — base '<B>' requires a new governance resolution for outcome <new_outcome_id>. Resolve via /governance-resolve, then resume with /pipeline-run <B> --event GOVERNANCE_RESOLVED.`

If this PAUSE write fails: stop. M11 is in indeterminate pause state. The GOVERNANCE_REEVALUATION_COMPLETED event already appended provides a reconstruction anchor. Report write failure.

**Phase 8.G Failure Conditions:**

| Condition | Classification | Result |
|-----------|----------------|--------|
| GOVERNANCE_RESUME_STARTED write failure | NON_RECOVERABLE | Stop immediately |
| PAUSE event not found in pipeline/events.md | NON_RECOVERABLE | BLOCKED — State Reconstruction Failure |
| outcome_id mismatch between Phase 5.5 input and PAUSE record | NON_RECOVERABLE | BLOCKED — Outcome ID Discrepancy |
| remaining_plan_steps mismatch between Phase 5.5 input and PAUSE record | NON_RECOVERABLE | BLOCKED — Plan State Discrepancy |
| Outcome closure event not found in governance/events.md | NON_RECOVERABLE | BLOCKED — Outcome Not Closed |
| Resume plan contains zero steps | NON_RECOVERABLE | BLOCKED — Empty Resume Plan |
| GOVERNANCE_RESUME_DENIED write failure (REJECTED path, Step 3) | NON_RECOVERABLE | Stop — indeterminate state |
| GOVERNANCE_REEVALUATION_REQUESTED write failure | NON_RECOVERABLE | BLOCKED — M12 must not be invoked |
| M12 → GOVERNANCE_BLOCKED | NON_RECOVERABLE | GOVERNANCE_RESUME_BLOCKED |
| M12 → GOVERNANCE_FAILED | NON_RECOVERABLE | GOVERNANCE_RESUME_FAILED |
| M12 → GOVERNANCE_DENIED | PLAN BLOCKED | GOVERNANCE_RESUME_DENIED (reason: POLICY_GAP) |
| GOVERNANCE_REEVALUATION_COMPLETED write failure | NON_RECOVERABLE | Stop — do not route |
| PAUSE re-escalation write failure (Step 8.1) | NON_RECOVERABLE | Stop — indeterminate pause state |

**Phase 8.G Runtime Invariants:**

**I-8G-01 — No Prior Verdict Set Reuse.** Phase 8.G must not pass, reference, or re-use the Governance Verdict Set from the prior cycle as input to M12 or as authorization for any plan step.

**I-8G-02 — Closed Outcome Is Not Authorization.** The M13 closure of outcome_id does not authorize any plan step for execution, regardless of M13's terminal decision. Authorization is derived exclusively from M12's new Governance Verdict Set.

**I-8G-03 — Write-Before-Invoke Ordering.** GOVERNANCE_REEVALUATION_REQUESTED must be appended before M12 is invoked. GOVERNANCE_REEVALUATION_COMPLETED must be appended before Phase 8.G routes to any downstream phase or pause state.

**I-8G-04 — Reconstruction Before Invocation.** Phase 8.G verifies the Governance Gate PAUSE state from pipeline/events.md and outcome closure from governance/events.md before constructing the resume plan or invoking M12. Phase 5.5 inputs are initial references only.

**I-8G-05 — Single Evaluation Per Resume.** Each Phase 8.G invocation produces exactly one M12 re-evaluation. If M12 returns GOVERNANCE_ESCALATED, Phase 8.G emits a re-escalation PAUSE event and stops. It does not loop or retry.

**I-8G-06 — Re-Escalation PAUSE Carries New Outcome ID.** The re-escalation PAUSE event records the new outcome_id as `payload.outcome_id` and the resolved outcome_id as `payload.prior_outcome_id`. The prior outcome_id is not reused as the active tracking identifier.

**I-8G-07 — Re-Escalation PAUSE Is Detectable by Phase 5.5 Scan.** The re-escalation PAUSE carries `payload.event_signal = GOVERNANCE_GATE`. Phase 5.5's scan, with the scan precision rule applied (select most recent qualifying PAUSE not followed by GOVERNANCE_RESUME_STARTED for the same outcome_id), produces a match on this event without modification to Phase 5.5.

**I-8G-08 — M13 REJECTED Bypasses M12 Unconditionally.** When `m13_terminal_decision = REJECTED`, Phase 8.G must not invoke M12 under any condition. The Step 3 termination path applies regardless of the active Policy Profile.

**I-8G-09 — LIFECYCLE_CLOSURE Does Not Bypass M12.** When `m13_terminal_decision = LIFECYCLE_CLOSURE` (closure event type is OUTCOME_SUPERSEDED, DELEGATION_EXPIRED, or OUTCOME_INVALIDATED), Phase 8.G must proceed to Step 4 and invoke M12 for a fresh governance evaluation. A lifecycle closure event is not a human authority decision and does not substitute for M12 policy evaluation. The current Governance State — which includes the M13 closure event and, for OUTCOME_SUPERSEDED, reflects the updated active Policy Profile — is the input to fresh M12 evaluation. I-8G-08 applies only when `m13_terminal_decision = REJECTED`; I-8G-09 applies only when `m13_terminal_decision = LIFECYCLE_CLOSURE`. These invariants are non-overlapping.

---

## Phase 6 — Goal Decomposition

This phase implements L2-006 (M11 derives Coordination Goals; may not invent Business Goals) and L2-007 (ALREADY_SATISFIED).

**6.1 Business Goal to Coordination Goal Mapping**

The Business Goal is the user's stated intent (expressed via invocation arguments). M11 derives the Coordination Goal (target coordination state) as follows:

| Mode | Business Goal | Coordination Goal |
|------|---------------|-------------------|
| STATUS | View current state | None (no plan) |
| NEXT | Advance to next logical state | Derived from current state — see next-state table below |
| TARGET | Advance to `<target_state>` | `<target_state>` directly |

**Next-State Derivation Table (NEXT mode):**

| Current State | Next Logical State |
|---------------|--------------------|
| DISCOVERING | KNOWLEDGE_READY |
| AWAITING_VALIDATION | KNOWLEDGE_READY |
| KNOWLEDGE_READY | SPECIFICATION_READY |
| SPECIFICATION_READY | BASELINED |
| BASELINED | CLOSED |
| UNDER_REVISION | BASELINED |
| CLOSED | (no next state — ALREADY_SATISFIED with message: base is CLOSED) |

**6.2 Reachability Check**

Verify that the Coordination Goal is reachable from the current state using the transition table (L1 Section 4). Valid forward paths are:

- DISCOVERING → {KNOWLEDGE_READY, SPECIFICATION_READY, BASELINED, CLOSED}
- AWAITING_VALIDATION → {KNOWLEDGE_READY, SPECIFICATION_READY, BASELINED, CLOSED}
- KNOWLEDGE_READY → {SPECIFICATION_READY, BASELINED, CLOSED}
- SPECIFICATION_READY → {BASELINED, CLOSED}
- BASELINED → {CLOSED}
- UNDER_REVISION → {BASELINED, CLOSED}
- CLOSED → {} (terminal — no reachable goal)

If the Coordination Goal is not reachable from the current state: report `BLOCKED — Goal '<target_state>' is not reachable from current state '<current_state>' for base '<B>'.` Stop for this base. If processing ALL, continue to next base (RECOVERABLE per base).

**6.3 ALREADY_SATISFIED Check (L2-007)**

If the current derived coordination state of base B is equal to or beyond the Coordination Goal: the goal is ALREADY_SATISFIED.

"Beyond" is defined by forward-only ordering: DISCOVERING < AWAITING_VALIDATION < KNOWLEDGE_READY < SPECIFICATION_READY < BASELINED < CLOSED. UNDER_REVISION does not fit this linear order; it is handled separately: UNDER_REVISION is not "beyond" BASELINED (it is a revision of BASELINED).

If ALREADY_SATISFIED:

1. Report: `STATUS: ALREADY_SATISFIED — base '<B>' is currently in state '<state>', which satisfies goal '<target_state>'.`
2. Do not generate a plan.
3. Do not invoke any M1–M10 command.
4. Do not emit a confirmation gate.
5. Session result for this base: ALREADY_SATISFIED.

**6.4 Status View (STATUS mode)**

If mode is STATUS:

1. For each base in the workspace: derive coordination state (Phase 4 already complete).
2. Present a summary table of all known bases, their coordination states, and active flags.
3. Do not generate a plan. Do not enter the confirmation gate. Do not invoke any M1–M10 command.
4. Emit SESSION_END event. Session result: SUCCESS (for status view, all views succeed unless workspace validation failed).

---

## Phase 7 — Capability Assessment

This phase implements L2-005 (capability-based planning). Plans are derived from missing capabilities, not from hardcoded state transitions.

**7.1 Capability Map**

| ID | Capability | Satisfied When | Producing Command |
|----|-----------|----------------|-------------------|
| CAP-01 | extracted_knowledge | `knowledge_base/extracted/<B>_knowledge.md` exists | /extract-knowledge (M2) |
| CAP-02 | conflicts_detected | `knowledge_base/conflicts/conflicts_report.md` exists | /detect-conflicts (M3) |
| CAP-03 | questions_processed | `questions_report.md` exists AND no question for B has status UNANSWERED, PARTIALLY_ANSWERED, or REJECTED AND `conflicts_report.md` has no conflict for B with status other than CONSOLIDATED | /generate-questions (M4) + /human-validation (M5) |
| CAP-04 | knowledge_consolidated | `knowledge_base/consolidated/<B>_consolidated.md` exists | /consolidate-knowledge (M6) |
| CAP-05 | specification_drafted | `specifications/draft/<B>_specification.md` exists | /generate-specification (M7) |
| CAP-06 | specification_baselined | Lifecycle record shows a BASELINE event as the most recent event for B's spec chain | /specification-lifecycle BASELINE (M8) |
| CAP-07 | specification_archived | Lifecycle record shows an ARCHIVE event as the most recent event for B's spec chain | /specification-lifecycle ARCHIVE (M9) |

Note: CAP-03 combines question generation and validation. It is satisfied when both the questions pipeline and the conflict pipeline are complete for base B: no open questions remain AND no unresolved conflicts remain. When M3 found zero conflicts for B and no questions were generated (zero-conflict base), CAP-03 is vacuously satisfied.

**7.2 Capability Requirements per Goal State**

| Goal State | Required Capabilities |
|------------|-----------------------|
| KNOWLEDGE_READY | CAP-01, CAP-02, CAP-03 |
| SPECIFICATION_READY | CAP-01, CAP-02, CAP-03, CAP-04, CAP-05 |
| BASELINED | CAP-01, CAP-02, CAP-03, CAP-04, CAP-05, CAP-06 |
| CLOSED | CAP-01, CAP-02, CAP-03, CAP-04, CAP-05, CAP-06, CAP-07 |

**7.3 Current Capability Assessment**

For base B, evaluate each capability condition against the current workspace artifact state:

1. CAP-01: `knowledge_base/extracted/<B>_knowledge.md` exists? → TRUE/FALSE
2. CAP-02: `knowledge_base/conflicts/conflicts_report.md` exists? → TRUE/FALSE
3. CAP-03: `questions_report.md` has no UNANSWERED/PARTIALLY_ANSWERED/REJECTED entries for B AND `conflicts_report.md` has no unresolved (non-CONSOLIDATED) conflict for B? → TRUE/FALSE
4. CAP-04: `knowledge_base/consolidated/<B>_consolidated.md` exists? → TRUE/FALSE
5. CAP-05: `specifications/draft/<B>_specification.md` exists? → TRUE/FALSE
6. CAP-06: Lifecycle event chain for B has BASELINE as most recent event? → TRUE/FALSE
7. CAP-07: Lifecycle event chain for B has ARCHIVE as most recent event? → TRUE/FALSE

**7.4 Compute Capability Gap**

```text
required_capabilities = capability_requirements[goal_state]
current_capabilities  = assess_capabilities(B, WORKSPACE_ROOT)
capability_gap        = required_capabilities − current_capabilities
```

If capability_gap is empty: the goal is ALREADY_SATISFIED (handled in Phase 6.3; if not already caught, apply ALREADY_SATISFIED here).

**7.5 Capability Dependency Order**

Capabilities must be acquired in dependency order. Violating this order causes downstream command failures.

```text
CAP-01 → CAP-02 → CAP-03 → CAP-04 → CAP-05 → CAP-06 → CAP-07
```

Each capability depends on all capabilities before it in this chain. When generating a plan, steps must be ordered so that each capability's producer runs after all prior capabilities in the chain are satisfied.

Special rule: CAP-03 has an internal dependency — question generation (M4) must run before human validation (M5) can run. If CAP-03 is in the gap, the plan includes two steps: M4 (AUTO) then M5 (INTERACTIVE).

---

## Phase 8 — Plan Generation

**8.1 Map Capability Gap to Plan Steps**

For each capability in the gap, in dependency order, map to plan steps:

| Missing Capability | Plan Step(s) | Type |
|--------------------|-------------|------|
| CAP-01 (INGESTED bases only) | PS-N: /extract-knowledge | AUTO |
| CAP-02 | PS-N: /detect-conflicts | AUTO |
| CAP-03 (partial: no questions file) | PS-N: /generate-questions, PS-N+1: /human-validation | AUTO, INTERACTIVE |
| CAP-03 (partial: open questions exist) | PS-N: /human-validation | INTERACTIVE |
| CAP-04 | PS-N: /consolidate-knowledge | AUTO |
| CAP-05 | PS-N: /generate-specification | AUTO |
| CAP-06 | PS-N: [user review] BASELINE_REQUEST → PS-N+1: /specification-lifecycle BASELINE | INTERACTIVE, AUTO |
| CAP-07 | PS-N: [user review] ARCHIVE_REQUEST → PS-N+1: /specification-lifecycle ARCHIVE | INTERACTIVE, AUTO |

CAP-01 is in the capability gap only for bases in INGESTED state (discovered via Phase 3.3b from `runtime/sources.md`). For bases discovered via Phase 3.3 (extracted `*_knowledge.md` scan), CAP-01 is always pre-satisfied and never appears in the gap.

**8.2 Plan Step Format**

Each plan step record contains:

| Field | Description |
|-------|-------------|
| `step_id` | PS-NNN, sequential within the session plan |
| `command` | The M1–M10 command to invoke (e.g., `/detect-conflicts`) |
| `operation` | Operation argument if applicable (e.g., `BASELINE` for /specification-lifecycle) |
| `type` | AUTO or INTERACTIVE |
| `capability_acquired` | The CAP-ID that this step satisfies |
| `postcondition` | Artifact existence or status check that confirms success |
| `failure_class` | RECOVERABLE or NON_RECOVERABLE (see Phase 13) |

**8.3 Plan Validation**

Before presenting the plan:

1. Verify every step's target command exists (PC11 — the corresponding `.claude/commands/` or `docs/commands/` entry is present).
2. Verify the step sequence satisfies capability dependency order.
3. Verify no step modifies an M1–M10-owned artifact directly (AD-002).

If any plan validation check fails: report `BLOCKED — Plan generation failed: <reason>`. Stop.

**8.4 Multi-Base Plan (ALL mode)**

When mode is ALL:

1. Generate a plan for each target base independently (Phases 7–8 per base).
2. Present plans for all bases before the confirmation gate (Phase 9).
3. Execute plans in base alphabetical order (L2-001).
4. A RECOVERABLE failure on one base does not prevent execution of the next base's plan.

---

## Phase 9 — Confirmation Gate

This phase implements L2-009 (plan execution requires explicit confirmation).

**9.1 Gate Exceptions**

The confirmation gate is skipped for the following cases (no user confirmation required):

| Condition | Reason |
|-----------|--------|
| STATUS mode | No plan generated |
| NEXT mode and ALREADY_SATISFIED | No plan generated |
| TARGET mode and ALREADY_SATISFIED | No plan generated |

All other cases require confirmation before any M1–M10 command is invoked.

**9.2 Plan Presentation**

Present the plan to the user. The presentation must include:

1. Base identifier and current coordination state.
2. Goal state (Coordination Goal).
3. Numbered list of plan steps in execution order.
4. For each step: command name, type (AUTO/INTERACTIVE), and expected outcome.
5. For INTERACTIVE steps: a description of the human action required.
6. For multi-base plans: a plan section per base, in execution order.

**9.3 User Response**

Await one of three user responses:

| Response | Action |
|----------|--------|
| Approve | Proceed to Phase 9.5. |
| Modify | User may change the goal state or base. Return to Phase 6. Do not enter Phase 9.5 until re-approved. |
| Abort | Emit SESSION_ABORTED event. Session result: FAILED. Stop. |

If the user modifies the goal: regenerate the plan from Phase 6 and re-present. Do not carry forward any artifacts from the cancelled plan.

---

## Phase 9.5 — Initial Governance Evaluation Gate

This phase executes after Phase 9 (Confirmation Gate) and before Phase 10 (Plan Execution Loop). It invokes M12 for the confirmed plan before any M1–M10 command is executed.

**Gate Exceptions**

Phase 9.5 is skipped in the same cases as Phase 9:

| Condition | Reason |
|-----------|--------|
| STATUS mode | No plan generated; Phase 9 was skipped |
| NEXT mode and ALREADY_SATISFIED | No plan generated; Phase 9 was skipped |
| TARGET mode and ALREADY_SATISFIED | No plan generated; Phase 9 was skipped |

If the user aborted at Phase 9.3, the session has already terminated. Phase 9.5 is not entered.

**Single-Base Procedure**

**Step 1 — Append GOVERNANCE_EVALUATION_REQUESTED**

Append to `WORKSPACE_ROOT/runtime/pipeline/events.md`:

```text
event_type:  GOVERNANCE_EVALUATION_REQUESTED
session_id:  <session_id>
base:        <base_id>
timestamp:   <now>
actor:       M11
payload:     { plan_step_count: <N> }
```

If this write fails: stop. Report write failure. Session result = FAILED. M12 must not be invoked.

Invariant I-9.5-01 applies: this write must complete before M12 is invoked.

**Step 2 — Invoke M12**

Invoke the Governance Runtime (M12) with the confirmed plan for base B.

**Step 3 — Receive Verdict Set**

Receive the Governance Verdict Set and Governance Cycle Result Code from M12.

**Step 4 — Append GOVERNANCE_EVALUATION_COMPLETED**

Append to `WORKSPACE_ROOT/runtime/pipeline/events.md`:

```text
event_type:  GOVERNANCE_EVALUATION_COMPLETED
session_id:  <session_id>
base:        <base_id>
timestamp:   <now>
actor:       M11
payload:     { governance_cycle_result: <RESULT_CODE>, verdict_count: <N> }
```

If this write fails: stop. Report write failure. Session result = FAILED. Do not route to any downstream phase.

Invariant I-9.5-02 applies: this write must complete before Phase 9.5 routes to any downstream phase or pause state.

**Step 4 Routing — Branch on Governance Cycle Result Code**

| Result Code | Action |
|-------------|--------|
| `GOVERNANCE_COMPLETE` | Proceed to Phase 10. |
| `GOVERNANCE_ESCALATED` | Execute Step 4.1. |
| `GOVERNANCE_DENIED` | Report DENY Verdicts to user. Session result = GOVERNANCE_DENIED. Proceed to Phase 12. |
| `GOVERNANCE_FAILED` | Report governance failure to user. Session result = FAILED. Proceed to Phase 12. |
| `GOVERNANCE_BLOCKED` | Report governance blockage to user. Session result = BLOCKED. Proceed to Phase 12. |

**Step 4.1 — GOVERNANCE_ESCALATED Path (Initial Governance Pause)**

Read `WORKSPACE_ROOT/runtime/governance/events.md`. Locate the ESCALATION_RECORDED or DELEGATION_ASSIGNED event written by the current M12 session (match on `m11_session_id` = current session_id). Extract `outcome_id` from that event's `verdict_id` field.

Append to `WORKSPACE_ROOT/runtime/pipeline/events.md`:

```text
event_type:  PAUSE
session_id:  <session_id>
base:        <base_id>
timestamp:   <now>
actor:       M11
payload:     {
  event_signal:     GOVERNANCE_GATE,
  outcome_id:       <outcome_id from ESCALATE or DELEGATE Verdict>,
  repause_sequence: 1,
  remaining_steps:  <all plan steps>
}
```

Update `pipeline_state.md` for base B: set `resume_available = TRUE`.

Report: `STATUS: GOVERNANCE_PAUSED — base '<B>' requires governance resolution for outcome <outcome_id>. Resolve via /governance-resolve, then resume with /pipeline-run <B> --event GOVERNANCE_RESOLVED.`

If the PAUSE write fails: stop. M11 is in indeterminate pause state. The GOVERNANCE_EVALUATION_COMPLETED event already appended provides a reconstruction anchor. Report write failure.

Session result = GOVERNANCE_PAUSED. Proceed to Phase 12.

**ALL Mode Procedure**

In ALL mode, all M12 evaluations complete before Phase 10 begins for any base (GD-8, I-9.5-04).

**Step 4.0 — Evaluate All Bases**

Initialize: executable set = ∅, paused set = ∅, denied set = ∅.

For each base B in the processing set, in ascending alphabetical order:

1. Execute Steps 1–4 for base B.
2. Classify base B by Governance Cycle Result Code:
   - `GOVERNANCE_COMPLETE` → add B to executable set.
   - `GOVERNANCE_ESCALATED` → add B to paused set (do not execute Step 4.1 yet — all evaluations complete first).
   - `GOVERNANCE_DENIED`, `GOVERNANCE_FAILED`, or `GOVERNANCE_BLOCKED` → add B to denied set.

Do not begin Phase 10 for any base during this step. All evaluations must complete before routing (I-9.5-04).

**Step 4.1 — Process Paused Set**

For each base B in the paused set: execute the single-base Step 4.1 (Initial Governance Pause) for base B.

**Step 4.2 — ALL Mode Routing**

| Condition | Action |
|-----------|--------|
| Executable set non-empty; paused set empty; denied set empty | Proceed to Phase 10 with all bases in the executable set. |
| Executable set non-empty; paused set or denied set non-empty | Proceed to Phase 10 with the executable set only. Paused bases are suspended at Governance Gate (PAUSE events written in Step 4.1). For each denied base: report DENY Verdicts to user. |
| Executable set empty; paused set non-empty; denied set empty | All bases suspended at Governance Gate (PAUSE events written in Step 4.1). Session result = GOVERNANCE_PAUSED. Proceed to Phase 12. |
| Executable set empty; paused set empty; denied set non-empty | All bases denied. Report DENY Verdicts. Session result = GOVERNANCE_DENIED. Proceed to Phase 12. |
| Executable set empty; paused set non-empty; denied set non-empty | Mixed: some bases suspended at Governance Gate (PAUSE events written in Step 4.1), some denied. Report DENY Verdicts for denied bases. Session result = PARTIAL_GOVERNANCE_PAUSED. Proceed to Phase 12. |

**Phase 9.5 Failure Conditions**

| Condition | Classification | Action |
|-----------|----------------|--------|
| GOVERNANCE_EVALUATION_REQUESTED write failure | NON_RECOVERABLE | Stop. Session result = FAILED. M12 must not be invoked. |
| M12 invocation error (I/O failure, runtime unavailable) | NON_RECOVERABLE | Stop. Session result = FAILED. |
| GOVERNANCE_EVALUATION_COMPLETED write failure | NON_RECOVERABLE | Stop. Session result = FAILED. Do not route. |
| PAUSE write failure (Step 4.1) | NON_RECOVERABLE | Stop. Indeterminate pause state. GOVERNANCE_EVALUATION_COMPLETED event provides reconstruction anchor. Report write failure. |

**Phase 9.5 Runtime Invariants**

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| I-9.5-01 | **Write-Before-Invoke Ordering.** GOVERNANCE_EVALUATION_REQUESTED must be appended to `events.md` before M12 is invoked. This write must succeed before the M12 call is made. | BLOCKING |
| I-9.5-02 | **Write-After-Return Ordering.** GOVERNANCE_EVALUATION_COMPLETED must be appended to `events.md` before Phase 9.5 routes to any downstream phase or pause state. | BLOCKING |
| I-9.5-03 | **No Phase 10 Until GOVERNANCE_COMPLETE.** Phase 10 may not begin for any base until GOVERNANCE_EVALUATION_COMPLETED is recorded with `governance_cycle_result = GOVERNANCE_COMPLETE` for that base and session. | BLOCKING |
| I-9.5-04 | **ALL Mode Batch Sequencing.** In ALL mode, all Phase 9.5 evaluations (Steps 1–4) complete for all bases before Phase 10 begins for any base. No base enters Phase 10 during the evaluation loop. (GD-8) | BLOCKING |
| I-9.5-05 | **M12 Non-Execution.** Phase 9.5 does not invoke M1–M10 commands, modify M1–M10 artifacts, or modify governance artifacts. Phase 9.5 appends exactly two event types to `pipeline/events.md` per base per evaluation: GOVERNANCE_EVALUATION_REQUESTED and GOVERNANCE_EVALUATION_COMPLETED (plus one PAUSE event per paused base in Step 4.1). | BLOCKING |
| I-9.5-06 | **Single Evaluation per Base.** Each base in the processing set is evaluated by M12 exactly once in Phase 9.5 per session. | BLOCKING |

---

## Phase 10 — Plan Execution Loop

**10.1 Execute Steps in Order**

For each plan step, in sequence:

**Step 10.1.1 — Announce**

Report: `Executing step <step_id>: <command> <operation> for base '<B>'...`

**Step 10.1.2 — Invoke**

For AUTO steps: invoke the target M1–M10 command. Pass the base identifier and WORKSPACE_ROOT context as inputs. Observe the command's completion report.

For INTERACTIVE steps: enter the Interactive Breakpoint Protocol (Phase 11).

**Step 10.1.3 — Evaluate Postcondition**

After each AUTO step completes:

1. Re-derive the coordination state of base B from workspace artifacts (abbreviated State Derivation Decision Tree, Phase 4.1).
2. Check the step's postcondition: verify the expected artifact exists or the expected status is set.
3. If postcondition satisfied: proceed to Step 10.1.4.
4. If postcondition not satisfied: classify as RECOVERABLE step failure. Invoke Failure Handling (Phase 13).

**Step 10.1.4 — Record Step Completion**

Append a STEP_COMPLETE event to `events.md`:

```text
event_type:  STEP_COMPLETE
base:        <B>
payload:     { step_id: <PS-NNN>, command: <command>, capability_acquired: <CAP-ID> }
```

**Step 10.1.5 — Update Projection**

Update `pipeline_state.md` for base B to reflect the new derived state and updated flags.

The write ordering invariant must be maintained: STEP_COMPLETE event appended **before** `pipeline_state.md` is updated.

**Step 10.1.6 — Advance to Next Step**

Re-derive the capability gap from the updated coordination state (Phase 7.3–7.4). If the gap is now empty: the goal is reached. Proceed to Phase 12. Otherwise: proceed to the next plan step.

**10.2 Re-evaluation at Each Step**

After each step, M11 re-derives the coordination state. If the derived state indicates the goal is already satisfied (e.g., a step had side effects that advanced the base further than expected): report the unexpected advancement, emit a STEP_COMPLETE event for the current step, and proceed to Phase 12.

**10.3 Plan Adaptation**

If the derived state after a step indicates that the originally planned next step is no longer needed (e.g., M3 ran and produced zero conflicts — M5 is no longer required): recompute the capability gap and omit unnecessary steps from the remaining plan. Report the adapted plan to the user before continuing.

---

## Phase 11 — Interactive Breakpoint Protocol

This phase implements L2-003. Interactive steps do not fail the pipeline — they pause the affected base.

**11.1 Interactive Step Types**

| Step | Required Human Action | Signal to Resume |
|------|-----------------------|------------------|
| /human-validation (M5) | User answers questions in an M5 session | User invokes `/pipeline-run` against this base (RESUME_REQUEST) |
| BASELINE_REQUEST gate | User reviews draft spec; declares readiness to baseline | User invokes `/pipeline-run <base>` with BASELINE_REQUEST signal |
| ARCHIVE_REQUEST gate | User reviews stable spec; declares readiness to archive | User invokes `/pipeline-run <base>` with ARCHIVE_REQUEST signal |

**11.2 Breakpoint Procedure**

When an INTERACTIVE step is reached:

1. Report the required human action to the user.
2. Record the resume point: the current step_id, the session_id, and the base B.
3. Append a PAUSE event:

```text
event_type:  PAUSE
session_id:  <session_id>
base:        <B>
payload:     { resume_step_id: <PS-NNN>, remaining_steps: [<PS-NNN+1>, ...] }
```

4. Update `pipeline_state.md` for base B: set `resume_available = TRUE`.
5. Report: `STATUS: PAUSED — base '<B>' is paused at step <PS-NNN>. Resume with /pipeline-run <B> when ready.`
6. Session result for this base: PAUSED.

**11.3 Resume Procedure**

When `/pipeline-run <B>` is invoked against a base with `resume_available = TRUE`:

1. Append a RESUME_REQUEST event.
2. Re-derive the coordination state of B from workspace artifacts (Phase 4.1).
3. Report the prior pause point and the current derived state to the user.
4. If the workspace state changed since the pause (projection drift): report the change and recompute the plan from current state (return to Phase 6).
5. If the workspace state is unchanged: present the remaining steps from the prior plan.
6. Re-enter the Confirmation Gate (Phase 9) for the resumed plan. User must confirm before execution continues.

**11.4 Interactive Step Completion Detection**

For M5 (/human-validation): after the user signals resume, re-derive CAP-03. If CAP-03 is now satisfied (all questions VALIDATED/RESOLVED): the step is complete. Proceed to the next plan step. If CAP-03 is not yet satisfied: re-enter the M5 interactive breakpoint (user must complete more validation).

For BASELINE_REQUEST gate: after the user signals resume, re-derive CAP-06. If CAP-06 is now satisfied: the step is complete. If not: BASELINE operation failed; classify as RECOVERABLE failure (Phase 13).

---

## Phase 12 — Session Result Determination

This phase implements L2-010.

**12.1 Result Codes**

| Result | Condition |
|--------|-----------|
| `SUCCESS` | All target bases reached their Coordination Goal. All plan steps completed. |
| `PARTIAL_SUCCESS` | Mode is ALL. At least one base reached its Coordination Goal. At least one base did not (RECOVERABLE failure or PAUSED). |
| `PAUSED` | At least one base is paused at an INTERACTIVE step. No base failed with NON_RECOVERABLE failure. |
| `FAILED` | Session aborted by user, or at least one NON_RECOVERABLE failure occurred. |
| `BLOCKED` | Workspace validation failed, or plan computation failed, or a critical precondition was not met. |
| `ALREADY_SATISFIED` | Goal was already satisfied for all target bases. No steps executed. |
| `GOVERNANCE_PAUSED` | At least one base is paused at a Governance Gate (Phase 9.5 returned GOVERNANCE_ESCALATED for the initial evaluation). No plan steps were executed. Session resumes via GOVERNANCE_RESOLVED event. |
| `GOVERNANCE_DENIED` | All target bases were denied by policy during Phase 9.5 governance evaluation. No plan steps executed. Affected plan steps cannot proceed until policy coverage is established. |
| `PARTIAL_GOVERNANCE_PAUSED` | Mode is ALL. Executable set is empty. At least one base is paused at a Governance Gate and at least one base was denied by policy during Phase 9.5 batch evaluation. No base entered Phase 10. |

**12.2 Multi-Base Result**

If the session result was pre-determined by Phase 9.5 governance evaluation (GOVERNANCE_PAUSED, GOVERNANCE_DENIED, or PARTIAL_GOVERNANCE_PAUSED), use that result directly. The computation below applies only when Phase 10 executed.

When mode is ALL and Phase 10 executed, compute the result as follows:

1. If any base has result NON_RECOVERABLE failure: overall result = FAILED.
2. Else if all bases are ALREADY_SATISFIED: overall result = ALREADY_SATISFIED.
3. Else if all bases reached their goal: overall result = SUCCESS.
4. Else if some bases reached their goal and others did not (PAUSED or RECOVERABLE failure): overall result = PARTIAL_SUCCESS.
5. Else if all bases are PAUSED: overall result = PAUSED.

**12.3 SESSION_END Event**

Append a SESSION_END event:

```text
event_type:  SESSION_END
base:        (empty)
payload:     { session_result: <RESULT_CODE>, bases_processed: [<B1>, <B2>, ...], goals_reached: [<B1>, ...], goals_not_reached: [<B2>, ...] }
```

**12.4 Result Report**

Present the session result to the user. Include:

1. Overall result code.
2. Per-base summary: base identifier, final coordination state, result.
3. For PAUSED bases: resume instructions.
4. For FAILED or PARTIAL_SUCCESS: failure details and recovery options.
5. For BLOCKED: the blocking condition and resolution guidance.

---

## Phase 13 — Failure Handling

This phase implements L2-002 (RECOVERABLE vs NON_RECOVERABLE classification).

**13.1 Failure Classification**

| Classification | Meaning | Action |
|----------------|---------|--------|
| RECOVERABLE | Failure affects only the current base. Execution of other bases (in ALL mode) may continue. | Record STEP_FAILED event. Report to user. Pause execution for this base. |
| NON_RECOVERABLE | Failure affects the workspace or session integrity. Execution cannot safely continue for any base. | Record SESSION_FAILED event. Report to user. Stop all execution. |

**13.2 RECOVERABLE Failure Procedure**

1. Append a STEP_FAILED event:

```text
event_type:  STEP_FAILED
base:        <B>
payload:     { step_id: <PS-NNN>, command: <command>, error: <error_message>, coordination_state_at_failure: <state> }
```

2. Update `pipeline_state.md` for base B: set coordination state to the last confirmed derived state.
3. Report to user: `STEP FAILED (RECOVERABLE): step <PS-NNN> (<command>) for base '<B>' failed. <error_message>. Remaining steps for '<B>' suspended.`
4. In ALL mode: continue processing remaining bases. Mark this base result as FAILED.
5. In single-base mode: session result = FAILED. Proceed to Phase 12.

**13.3 NON_RECOVERABLE Failure Procedure**

1. Append a SESSION_FAILED event:

```text
event_type:  SESSION_FAILED
base:        (empty or the base at point of failure)
payload:     { reason: <error_message>, step_id: <PS-NNN if applicable> }
```

2. Stop all plan execution immediately.
3. Report to user: `SESSION FAILED (NON_RECOVERABLE): <error_message>. Session terminated.`
4. Proceed to Phase 12 with result = FAILED.

**13.4 Failure Classification Table**

| Failure Condition | Classification |
|-------------------|----------------|
| Workspace validation failure (Phase 1: R4a, R4b) | NON_RECOVERABLE |
| M11 directory initialization failure (Phase 2: directory cannot be created) | NON_RECOVERABLE |
| events.md write failure | NON_RECOVERABLE |
| pipeline_state.md write failure after step completion event is written | RECOVERABLE (projection reconstructable at next session) |
| Named base not found (PC8) | NON_RECOVERABLE for single-base mode; RECOVERABLE (skip) in ALL mode |
| Plan validation failure (Phase 8.3) | NON_RECOVERABLE |
| M1–M10 command invocation failure | RECOVERABLE |
| M1–M10 command postcondition not satisfied | RECOVERABLE |
| M1–M10 artifact contamination detected (PC13 violation) | NON_RECOVERABLE |
| User aborts session | NON_RECOVERABLE (FAILED result) |
| Reachability check failure (Phase 6.2) | RECOVERABLE in ALL mode; NON_RECOVERABLE in single-base mode |

---

## Phase 14 — Projection Update

**14.1 Flag Derivation Rules**

After each plan step and at session end, derive and write business flags for each processed base B:

| Flag | Set When |
|------|----------|
| `specification_available` | `specifications/draft/<B>_specification.md` exists |
| `baseline_available` | CAP-05 is satisfied AND CAP-03 is satisfied (draft spec exists AND no open questions) |
| `open_questions` | At least one question for B in `questions_report.md` has status UNANSWERED, PARTIALLY_ANSWERED, or REJECTED |
| `human_action_required` | `open_questions` is TRUE AND no AUTO plan step can advance the base (only INTERACTIVE steps remain) |
| `change_pending` | A Change Event (NEW_SOURCE, CHANGE_REQUEST, or DECISION_OVERRIDE) has been recorded in events.md for B after the most recent BASELINE event for B, AND the base has not yet transitioned back to BASELINED or CLOSED |
| `resume_available` | A PAUSE event exists in events.md for B in a session that has no corresponding SESSION_END event marking SUCCESS or ALREADY_SATISFIED for B |
| `quality_gated` | (SD-8) If `specifications/draft/<B>_specification.md` does not exist: `NOT_APPLICABLE`. Else: read `specifications/draft/sqf_gate_report.md`. If absent: `NOT_RUN`. If present and readable: extract the `gate_status:` header field; map `PENDING_D7` → `PENDING`; pass through `PASS`, `WARN`, `BLOCK` unchanged. If present but unreadable: `NOT_RUN` (log WARNING). M11 does not block on this flag; blocking is enforced by /specification-lifecycle E7. [SQF Phase 1] |

**14.2 Projection Write Rules**

1. `pipeline_state.md` is written after every STEP_COMPLETE event and at SESSION_END.
2. The write ordering invariant: the event record is appended **before** `pipeline_state.md` is updated.
3. If the `pipeline_state.md` write fails: append a WARNING record to events.md noting the failed projection write. Do not stop execution. The event log remains authoritative; `pipeline_state.md` will be reconstructed at the next session start.
4. `pipeline_state.md` contains one record per known base. The record format is defined in L1 Section 9.

---

## Phase 15 — Validation Rules

All validation rules are evaluated at the points specified. Rules marked BLOCKING halt execution and report a structured error. Rules marked WARNING are logged and reported but do not halt execution.

**Initialization Rules:**

| Rule | Point | Condition | Classification |
|------|-------|-----------|----------------|
| EX-01 | Phase 1 (R5.1) | session_id is unique within the workspace (no prior SESSION_START event in events.md has the same session_id) | BLOCKING |
| EX-02 | Phase 2 | `WORKSPACE_ROOT/runtime/pipeline/` exists after Phase 2 | BLOCKING |
| EX-03 | Phase 2 | `events.md` is readable and all event_id values are sequential with no gaps | WARNING |

**State Derivation Rules:**

| Rule | Point | Condition | Classification |
|------|-------|-----------|----------------|
| EX-04 | Phase 4 | Every target base has exactly one derived coordination state (no ambiguous derivation) | BLOCKING |
| EX-05 | Phase 4 | Projection Drift is reported as a WARNING before plan computation | WARNING |
| EX-06 | Phase 5 | Every Change Event received against a BASELINED base triggers UNDER_REVISION transition before plan generation | BLOCKING |

**Plan Rules:**

| Rule | Point | Condition | Classification |
|------|-------|-----------|----------------|
| EX-07 | Phase 8 | Plan steps are ordered in capability dependency order (CAP-01 through CAP-07) | BLOCKING |
| EX-08 | Phase 8 | Every plan step's target command exists | BLOCKING |
| EX-09 | Phase 9 | Plan is presented to user and acknowledged before any AUTO step is executed (except for exempted modes) | BLOCKING |
| EX-09.5 | Phase 9.5 | M12 is invoked before any M1–M10 command executes. GOVERNANCE_EVALUATION_COMPLETED is appended with `governance_cycle_result = GOVERNANCE_COMPLETE` before Phase 10 begins for the current base. In ALL mode, all Phase 9.5 evaluations complete before Phase 10 begins for any base (GD-8). | BLOCKING |

**Execution Rules:**

| Rule | Point | Condition | Classification |
|------|-------|-----------|----------------|
| EX-10 | Phase 10 | M11 does not write to any artifact listed in the ownership table (Section 8 of L1) | BLOCKING |
| EX-11 | Phase 10 | After each plan step, coordination state is re-derived from workspace artifacts before the next step is computed | BLOCKING |
| EX-12 | Phase 10 | STEP_COMPLETE event is appended before `pipeline_state.md` is updated | BLOCKING |
| EX-13 | Phase 11 | When an INTERACTIVE step is reached, a PAUSE event is appended and `resume_available` is set before execution is suspended | BLOCKING |

**Persistence Rules:**

| Rule | Point | Condition | Classification |
|------|-------|-----------|----------------|
| EX-14 | Phase 10, 14 | Every event record written to `events.md` contains non-empty values for event_id, session_id, event_type, timestamp, and actor; `base` is non-empty for base-scoped events | BLOCKING |
| EX-15 | Phase 10 | No existing event record in `events.md` is modified after it is written | BLOCKING |
| EX-16 | Phase 12 | `pipeline_state.md` is updated before SESSION_END is reported | BLOCKING |
| EX-17 | Phase 14 | All business flags are re-derived from workspace artifacts at each projection write | WARNING |

**Session Result Rules:**

| Rule | Point | Condition | Classification |
|------|-------|-----------|----------------|
| EX-18 | Phase 12 | Session result code is one of: SUCCESS, PARTIAL_SUCCESS, PAUSED, GOVERNANCE_PAUSED, FAILED, BLOCKED, ALREADY_SATISFIED, GOVERNANCE_DENIED, PARTIAL_GOVERNANCE_PAUSED | BLOCKING |

---

## Phase 16 — Idempotency Rules

**ID-01 — State Derivation is Idempotent**

Given the same workspace artifact state, the State Derivation Decision Tree always produces the same coordination state for a given base. Running Phase 4 multiple times on an unchanged workspace produces the same result each time.

**ID-02 — ALREADY_SATISFIED Prevents Re-Execution**

If the goal is already satisfied (Phase 6.3), M11 reports ALREADY_SATISFIED and exits without invoking any M1–M10 command and without appending any event record (other than SESSION_START and SESSION_END). Re-invoking `/pipeline-run` on a base that has already reached its goal produces ALREADY_SATISFIED every time.

**ID-03 — Plan Generation is Idempotent**

Given the same coordination state and goal, M11 always generates the same plan (same steps in the same order). Plan generation has no side effects.

**ID-04 — Checkpoint Reconstruction is Idempotent**

Running Checkpoint Reconstruction (Phase 4.4) on an unchanged workspace produces the same `pipeline_state.md` content each time. A CHECKPOINT_RECONSTRUCTION event is appended each time reconstruction runs; this is the only side effect.

**ID-05 — Duplicate Session Protection**

If a SESSION_START event already exists for the current session_id in events.md (indicating a prior partial run), M11 detects this at Phase 1 (step R5.1, session_id counter). Since session_ids are sequential and auto-incremented, each invocation produces a new session_id. Prior sessions are not re-entered.

---

## Phase 17 — Failure Scenarios

**Scenario FS-01: Active Workspace Not Resolvable**
Phase: 1
Cause: `runtime/current_workspace.md` absent and `runtime/workspaces.md` has no `active` entry.
Classification: NON_RECOVERABLE.
Recovery: User must create a workspace via `/workspace-lifecycle CREATE` and SWITCH to it.

**Scenario FS-02: No Bases Found in Workspace**
Phase: 3
Cause: `knowledge_base/extracted/` is empty or contains no `*_knowledge.md` files.
Classification: NON_RECOVERABLE (STATUS and NEXT modes); mode-specific BLOCKED.
Recovery: User must run `/ingest-source` and `/extract-knowledge` to populate at least one base.

**Scenario FS-03: M3 (detect-conflicts) Fails**
Phase: 10
Cause: `/detect-conflicts` returns an error or does not produce `conflicts_report.md`.
Classification: RECOVERABLE.
Recovery: M11 records STEP_FAILED. User may retry with `/pipeline-run <B>` after resolving the M3 failure.

**Scenario FS-04: M5 (human-validation) Not Completed**
Phase: 11
Cause: User pauses during M5 interactive step.
Classification: Not a failure — PAUSED result.
Recovery: User completes M5 session outside M11, then resumes with `/pipeline-run <B>`.

**Scenario FS-05: M7 (generate-specification) Blocked by A7 Guard**
Phase: 10
Cause: `/generate-specification` returns STATUS: BLOCKED because the target specification is BASELINED (A7 guard active).
Classification: RECOVERABLE. This indicates the base is BASELINED or UNDER_REVISION; M7 should not have been included in the plan.
Recovery: M11 re-derives coordination state (Phase 4.1). If state is BASELINED or UNDER_REVISION, the plan was incorrect; M11 recomputes. This condition should be prevented by correct capability assessment (Phase 7.3 evaluates CAP-06 before including M7 as a step).

**Scenario FS-06: pipeline_state.md Write Failure After Event Append**
Phase: 14
Cause: `pipeline_state.md` cannot be written after a STEP_COMPLETE event was appended.
Classification: RECOVERABLE. Events are authoritative; projection is reconstructable.
Recovery: At next session start, Phase 2.5 detects `pipeline_state.md` is stale or absent. Checkpoint Reconstruction rebuilds the projection from workspace artifacts.

**Scenario FS-07: Revision Rule Bypass Attempted**
Phase: 5
Cause: A Change Event is received against a BASELINED base but no UNDER_REVISION transition is recorded.
Classification: NON_RECOVERABLE. This is a contract violation (EX-06).
Recovery: M11 must not proceed with plan execution when a Change Event against a BASELINED base is unhandled. The implementation must enforce EX-06 without exception.

**Scenario FS-08: Checkpoint Reconstruction Produces Inconsistent State**
Phase: 4.4
Cause: Lifecycle artifacts are partially written or inconsistent (e.g., ARCHIVE event exists but specification file is missing from archive/).
Classification: RECOVERABLE per base. Report each inconsistency as a WARNING. Assign the most conservative valid state (the state immediately preceding the inconsistent condition).
Recovery: User resolves the artifact inconsistency manually and re-invokes `/pipeline-run`.

---

## Phase 18 — Success Conditions

M11 execution is complete when all of the following are true for the current session:

**SC-01:** All target bases have been advanced to their Coordination Goal, OR have been correctly classified as ALREADY_SATISFIED, PAUSED, or FAILED with proper reporting.

**SC-02:** Every plan step that was executed has a corresponding STEP_COMPLETE event in `events.md` with non-empty required fields (EX-14).

**SC-03:** `pipeline_state.md` reflects the current derived coordination state of all processed bases at session end (EX-16).

**SC-04:** No M1–M10-owned artifact has been modified by M11 during the session (EX-10). If verification is performed by checksum: the pre-session and post-session checksums of all M1–M10 artifacts are identical.

**SC-05:** The Revision Rule (EX-06) was enforced: no Change Event against a BASELINED base was processed without a UNDER_REVISION transition.

**SC-06:** For sessions including INTERACTIVE steps: every INTERACTIVE step that was reached has a corresponding PAUSE event in `events.md` with a valid resume point (EX-13).

**SC-07:** For ALL-mode sessions: bases were processed in ascending alphabetical order of base identifier (L2-001).

**SC-08:** Session result code is one of the defined codes (EX-18) and accurately reflects the session outcome.

**SC-09:** All events recorded during the session are sufficient to reconstruct `pipeline_state.md` via Checkpoint Reconstruction (Phase 4.4) without relying on `pipeline_state.md` itself as input.
