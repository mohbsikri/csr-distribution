# Pipeline Coordination Runtime

## 1. Purpose

Enable CSR to coordinate the full M1–M10 pipeline across one or more specification bases within the active workspace, track each base through its lifecycle from source ingestion to closure, and present actionable pipeline state to the user at any point in the workflow.

Before this runtime: each of the ten pipeline commands (M1–M10) operates independently. There is no shared record of which bases have been ingested, which are awaiting validation, which have been baselined, or which pipeline stages have been executed. The user must mentally track pipeline state across all bases and commands. There is no mechanism to resume a partially completed pipeline session, to detect when a base is ready for the next stage, or to prevent a stage from being invoked out of order.

After this runtime: every base in the active workspace holds an explicit coordination state derived from the current artifact state of the workspace. The `/pipeline-run` command computes and executes a coordination plan that advances one or more bases toward their next logical pipeline stage. The user can pause at any point, resume in a subsequent session, and receive an accurate, current view of pipeline progress across all bases.

This runtime implements Stage 11 — Workspace State Coordination Runtime of the CSR pipeline.

---

## 2. Scope

This contract governs:

- The coordination state model for specification bases within the active workspace.
- The event model that drives state transitions.
- The goal model: how coordination targets (goals) are declared, selected, and resolved.
- The coordination model: how the runtime computes and executes plans against M1–M10.
- The ownership model: which truth sources M11 reads from and which it must not modify.
- The persistence model: what M11 writes, where, and under what conditions.
- The resume and recovery model: how interrupted coordination sessions are continued.
- Validation rules PC0–PC18.
- Success conditions for M11 completion.
- Risks and non-goals.

This contract does not cover:

- Automated execution without user confirmation (M12 scope).
- Non-interactive pipeline chaining (M12 scope).
- Multi-workspace coordination (post-M12 scope).
- Conflict resolution logic, question presentation, or validation interaction (M4–M6 scope).
- Specification lifecycle operations BASELINE, REOPEN, EVOLVE, ARCHIVE (M8–M9 scope).

---

## 3. Core Concepts

### Base

A **base** is the coordination unit. A base corresponds to a named source artifact group identified by a shared stem name (e.g., `project_alpha`). All extracted knowledge, conflicts, questions, consolidated artifacts, and specifications for that source group share the base stem. The base is the natural unit of pipeline progress tracking.

A base is not a workspace. Multiple bases may exist within a single workspace. Each base is tracked independently.

A base comes into existence in one of two ways: (1) M11 detects an extracted knowledge artifact in `WORKSPACE_ROOT/knowledge_base/extracted/` — the base enters DISCOVERING state; or (2) M11 detects an ingested source in `WORKSPACE_ROOT/runtime/sources.md` with Status=ingested and no corresponding extracted knowledge artifact — the base enters INGESTED state. A base is closed when its specification has reached the CLOSED coordination state.

### Coordination State

Each base holds exactly one **coordination state** at any time. Coordination states are defined in Section 4. Coordination states are **derived** — M11 computes the state of a base by reading artifact state from the workspace. Coordination states are not stored as the source of truth; the workspace artifacts are.

`WORKSPACE_ROOT/runtime/pipeline/pipeline_state.md` is a **coordination projection** — a snapshot of the computed coordination states of all known bases, written by M11 for operational efficiency and resume support. It is reconstructable from the workspace at any time.

### Goal

A **goal** is a coordination target that the user specifies when invoking `/pipeline-run`. A goal names a base (or uses `ALL` to target all non-CLOSED bases) and optionally names a target state to advance to. M11 computes a plan to advance the base from its current coordination state to the goal state.

### Plan

A **plan** is a deterministic, ordered sequence of M1–M10 command invocations that M11 computes to advance a base from its current coordination state to its goal state. Plans are computed at coordination start and re-evaluated at each step after execution. A plan step is a single command invocation with defined inputs and expected outputs.

### Workspace State Projection

The coordination projection at `WORKSPACE_ROOT/runtime/pipeline/pipeline_state.md` represents M11's current view of all base coordination states. It is written by M11 and reconstructable from the workspace. It does not own lifecycle truth for specifications or workspaces.

### Session

A **session** is a single invocation of `/pipeline-run`. A session has a session_id, a goal declaration, a computed plan, and an execution record. Session records are written to `WORKSPACE_ROOT/runtime/pipeline/events.md`.

### Change Event

A **Change Event** is any event of the following types: `NEW_SOURCE`, `CHANGE_REQUEST`, or `DECISION_OVERRIDE`. When any Change Event is received against a BASELINED base, the Revision Rule in Section 4 applies unconditionally. The complete definition of each event type, including its trigger and effect, is in Section 5.

---

## 4. State Model

### Business States

Each base holds exactly one business state at any time. INGESTED is the pre-extraction state for sources registered in `runtime/sources.md` but not yet extracted. DISCOVERING is entered when the extracted knowledge artifact is first detected.

| State | Meaning |
|-------|---------|
| `INGESTED` | A source artifact has been ingested into the workspace (`runtime/sources.md` Status=ingested) but no extracted knowledge artifact exists yet for this base. |
| `DISCOVERING` | At least one extracted knowledge artifact exists for this base. Conflict detection and question generation may or may not have run yet. |
| `AWAITING_VALIDATION` | All conflicts have been detected and all questions generated. At least one question is in `UNANSWERED`, `PARTIALLY_ANSWERED`, or `REJECTED` status. Human validation is required before consolidation can proceed. |
| `KNOWLEDGE_READY` | All questions are in `VALIDATED` or `RESOLVED` status (or no questions exist). Consolidation can proceed. |
| `SPECIFICATION_READY` | At least one consolidated knowledge artifact exists and at least one draft specification has been generated. No baseline exists yet for any specification in this base. |
| `BASELINED` | A stable specification exists for this base. The specification lifecycle record confirms at least one BASELINE event. No subsequent REOPEN, EVOLVE, or ARCHIVE event has been recorded for any specification in this base. |
| `UNDER_REVISION` | A BASELINED specification for this base has received a Change Event (NEW_SOURCE, CHANGE_REQUEST, or DECISION_OVERRIDE). The base is being revised. A new draft or REOPEN/EVOLVE operation is in progress. |
| `CLOSED` | The specification for this base has been archived (M9 ARCHIVE operation completed). The base lifecycle is complete. CLOSED is a terminal state within M11. |

### State Transition Rules

**Nominal Flow:**

```text
INGESTED → DISCOVERING → AWAITING_VALIDATION → KNOWLEDGE_READY → SPECIFICATION_READY → BASELINED → CLOSED
```

**Discovery Shortcut:**

```text
DISCOVERING → KNOWLEDGE_READY
```

Applies when conflict detection and question generation complete with zero unresolved questions and zero open conflicts. No human validation step is required.

**Revision Rule:**

```text
BASELINED + any Change Event → UNDER_REVISION
```

This transition is **mandatory and has no exceptions**. Any Change Event (NEW_SOURCE, CHANGE_REQUEST, or DECISION_OVERRIDE) received against a BASELINED base transitions it to UNDER_REVISION regardless of the nature or source of the change. There is no direct path from BASELINED back to BASELINED without passing through UNDER_REVISION.

**Revision Resolution:**

```text
UNDER_REVISION → BASELINED   (new baseline established after revision)
UNDER_REVISION → CLOSED      (revision completes with archival)
```

**Complete Transition Table:**

| From | To | Trigger |
|------|----|---------|
| (none) | INGESTED | Source ingested via /ingest-source (M1); appears in `runtime/sources.md` with Status=ingested; no extracted knowledge artifact yet |
| INGESTED | DISCOVERING | Extracted knowledge artifact created for this base by /extract-knowledge (M2) |
| (none) | DISCOVERING | Extracted knowledge artifact first detected directly in `knowledge_base/extracted/` with no prior INGESTED state |
| DISCOVERING | AWAITING_VALIDATION | All questions generated; at least one UNANSWERED |
| DISCOVERING | KNOWLEDGE_READY | Discovery shortcut: zero unresolved questions after detection |
| AWAITING_VALIDATION | KNOWLEDGE_READY | All questions reach VALIDATED or RESOLVED status |
| KNOWLEDGE_READY | SPECIFICATION_READY | Draft specification generated |
| SPECIFICATION_READY | BASELINED | BASELINE_REQUEST event; BASELINE operation completes |
| BASELINED | UNDER_REVISION | Any Change Event received (NEW_SOURCE, CHANGE_REQUEST, or DECISION_OVERRIDE) |
| UNDER_REVISION | BASELINED | New BASELINE operation completes after revision |
| UNDER_REVISION | CLOSED | ARCHIVE_REQUEST event; ARCHIVE operation completes |
| BASELINED | CLOSED | ARCHIVE_REQUEST event; ARCHIVE operation completes |

### State Derivation

M11 **derives** the coordination state of each base by reading workspace artifacts. It does not trust a cached state value without verification. At the start of every session and at each plan step boundary, M11 re-derives coordination states from workspace artifacts.

State derivation is deterministic: given the same workspace artifact state, the derived coordination state is always the same.

If the coordination projection (`pipeline_state.md`) disagrees with the derived state, the derived state wins. The projection is updated to reflect the derived state and the disagreement is reported as a WARNING to the user before plan computation proceeds.

---

## 5. Event Model

### Events

Nineteen event types are defined in the tables below. Eight are externally triggered (user or pipeline); eleven are M11-internal operational events, including six added by the Governance Integration Amendment for Phase 8.G and two added by the BF-1 Amendment for Phase 9.5.

**Externally Triggered Events:**

| Event | Category | Trigger | Effect |
|-------|----------|---------|--------|
| `NEW_SOURCE` | Change Event | An extracted knowledge artifact is detected for this base — either first detection (new base) or additional extraction for an existing base | For a new base: creates base entry in DISCOVERING state. Against a BASELINED base: triggers Revision Rule (BASELINED → UNDER_REVISION). Against other states: re-evaluates current coordination state. |
| `VALIDATION_RECEIVED` | — | A human validation session (M5) produces at least one VALIDATED question | Re-evaluates AWAITING_VALIDATION → KNOWLEDGE_READY gate |
| `CHANGE_REQUEST` | Change Event | User declares a change request against a BASELINED base | Mandatory BASELINED → UNDER_REVISION transition |
| `DECISION_OVERRIDE` | Change Event | User overrides a conflict resolution or question answer during a session | Flagged for re-consolidation; resets consolidation state for affected artifacts. Against a BASELINED base: triggers Revision Rule (BASELINED → UNDER_REVISION). |
| `BASELINE_REQUEST` | — | User requests baseline for a SPECIFICATION_READY or UNDER_REVISION base | Triggers BASELINE operation (M8); transitions to BASELINED on success |
| `ARCHIVE_REQUEST` | — | User requests closure/archival of a BASELINED or UNDER_REVISION base | Triggers ARCHIVE operation (M9); transitions to CLOSED on success |
| `RESUME_REQUEST` | — | User requests resume of a paused coordination session | Reconstructs coordination state from workspace; presents prior partial plan and current state |
| `GOVERNANCE_RESOLVED` | — | M13 has closed an open governance outcome for base B; user signals M11 to resume from Governance Gate pause | Verifies the governance outcome referenced in the Governance Gate PAUSE event is no longer open in `WORKSPACE_ROOT/runtime/governance/events.md`. Routes to Governance Gate Resume Procedure (Phase 8.G, added by Governance Integration Amendment). M11 must not treat this signal as plan execution approval; M12 re-evaluation is required before execution continues. |

**M11 Internal Events:**

| Event | Trigger | Effect |
|-------|---------|--------|
| `PAUSE` | User pauses the active coordination session; or Phase 8.G emits a Governance Gate re-pause on GOVERNANCE_ESCALATED | Records the current session_id and last completed plan step; written before session_state is updated. When emitted by Phase 8.G on re-escalation, the payload also carries `event_signal: GOVERNANCE_GATE`, `outcome_id` (new), `prior_outcome_id`, and `repause_sequence`. |
| `STEP_FAILED` | A plan step fails during execution | Records the failing step, the error, and the coordination state at failure time; execution stops |
| `CHECKPOINT_RECONSTRUCTION` | M11 reconstructs `pipeline_state.md` from workspace artifacts | Records the reconstruction timestamp and the number of bases reconstructed |
| `GOVERNANCE_RESUME_STARTED` | Phase 8.G is entered for base B following a GOVERNANCE_RESOLVED signal | Records base_id, outcome_id, and resume_triggered_by; written as the first action in Phase 8.G before any reads or derivations |
| `GOVERNANCE_REEVALUATION_REQUESTED` | Phase 8.G is about to invoke M12 for governance re-evaluation | Records base_id, outcome_id, and plan_step_count; written before M12 is invoked (write-before-invoke invariant) |
| `GOVERNANCE_REEVALUATION_COMPLETED` | M12 has returned a Governance Verdict Set and Governance Cycle Result Code | Records base_id, outcome_id, governance_cycle_result, and verdict_count; written before Phase 8.G routes to any downstream phase |
| `GOVERNANCE_RESUME_DENIED` | m13_terminal_decision = REJECTED (human authority refused the action) in Phase 8.G Step 3; or M12 returns GOVERNANCE_DENIED (policy gap) in Phase 8.G Step 8 | Records base_id, outcome_id, and reason (M13_REJECTED_TERMINAL_DECISION or POLICY_GAP); plan steps for the affected base cannot proceed |
| `GOVERNANCE_RESUME_FAILED` | M12 returns GOVERNANCE_FAILED during Phase 8.G re-evaluation | Records base_id, outcome_id, and failure_reason |
| `GOVERNANCE_RESUME_BLOCKED` | M12 returns GOVERNANCE_BLOCKED, or an internal Phase 8.G blocking condition occurs | Records base_id, outcome_id, and blocked_reason |
| `GOVERNANCE_EVALUATION_REQUESTED` | Phase 9.5 is about to invoke M12 for initial governance evaluation | Records base_id and plan_step_count; written before M12 is invoked (write-before-invoke invariant I-9.5-01) |
| `GOVERNANCE_EVALUATION_COMPLETED` | M12 has returned a Verdict Set and Governance Cycle Result Code for initial evaluation | Records base_id, governance_cycle_result, and verdict_count; written before Phase 9.5 routes to any downstream phase or pause state |

### Event Record Format

All events are appended to `WORKSPACE_ROOT/runtime/pipeline/events.md`. Each event record contains:

- `event_id` — unique identifier (sequential within the workspace, prefixed `EV`)
- `session_id` — the session that generated this event
- `event_type` — one of the ten types above
- `base` — the base affected by this event; empty for workspace-level events (CHECKPOINT_RECONSTRUCTION)
- `timestamp` — ISO 8601
- `actor` — the user or M11 subsystem that generated this event
- `payload` — event-type-specific structured data (e.g., source path for NEW_SOURCE, question IDs for VALIDATION_RECEIVED, step index for PAUSE and STEP_FAILED)

Events are append-only. No event record may be modified after it is written.

---

## 6. Goal Model

### Goal Declaration

A goal is declared when the user invokes `/pipeline-run`. Goals take one of three forms:

| Form | Meaning |
|------|---------|
| `/pipeline-run` (no args) | Present pipeline status for all non-CLOSED bases in the active workspace. No plan is computed or executed. |
| `/pipeline-run <base>` | Advance the named base to its next logical state. M11 determines the next state and computes the minimal plan. |
| `/pipeline-run <base> <target_state>` | Advance the named base to the specified target state. M11 computes the full plan from the current state to the target. |

Using `ALL` in place of `<base>` targets all non-CLOSED bases in declaration order. CLOSED bases are excluded from status views, `ALL` goal targets, and plan computation.

### Goal Resolution

M11 resolves a goal by:

1. Deriving the current coordination state of the target base from workspace artifacts.
2. Identifying the target state (next logical state, or the user-specified target state).
3. Validating that the target state is reachable from the current state using the transition table.
4. Computing the plan: a deterministic, ordered sequence of M1–M10 command invocations that will advance the base to the target state.

If the target state is not reachable (e.g., target is CLOSED but current state is DISCOVERING), M11 reports the unreachable goal with the reason and stops. It does not modify any artifact.

### Plan Execution

Plans are presented to the user before execution. The user may:

- Approve the plan for execution.
- Modify the goal (change target state or base).
- Abort the session.

M11 never executes a plan step without user awareness. Plan steps that require human interaction (e.g., M5 Human Validation) are presented as interactive breakpoints. M11 suspends plan execution at each interactive step and waits for the user to complete the step and signal readiness to continue.

After user confirmation at the Confirmation Gate, M11 invokes M12 (Phase 9.5 — Initial Governance Evaluation Gate) with the confirmed plan before any plan step is executed. M12 evaluates the plan against the active Policy Profile and returns a Governance Cycle Result Code. M11 proceeds to plan execution only on GOVERNANCE_COMPLETE. On GOVERNANCE_ESCALATED, M11 enters a Governance Gate pause and waits for M13 to close the open outcome. On GOVERNANCE_DENIED, GOVERNANCE_FAILED, or GOVERNANCE_BLOCKED, plan execution is terminated. In ALL mode, M12 is invoked once per base and all evaluations complete before Phase 10 begins for any base (GD-8).

---

## 7. Coordination Model

### AD-001 — M11 is a Deterministic Orchestrator

M11 computes plans and executes them by invoking M1–M10 commands. It may invoke any M1–M10 command as a step in a coordination plan. It may not replicate or internalize the business logic of any M1–M10 command.

This constraint is absolute:

- M11 does not perform knowledge extraction. It invokes `/extract-knowledge` (M2).
- M11 does not perform conflict detection. It invokes `/detect-conflicts` (M3).
- M11 does not perform human validation. It invokes `/human-validation` (M5).
- M11 does not perform specification lifecycle operations. It invokes `/specification-lifecycle` (M8) with the appropriate operation argument.
- M11 does not create, switch, or archive workspaces. It invokes `/workspace-lifecycle` (M10).

M11's own business logic is limited to: deriving coordination states, computing plans, executing plans step-by-step, recording events, and maintaining the coordination projection.

### Plan Computation Rules

1. A plan is computed fresh at the start of every session. Plans are never cached across sessions.
2. After each plan step executes, M11 re-derives the coordination state of the affected base before computing the next step. Plans adapt to the actual postcondition of each step.
3. If a step fails, M11 stops plan execution, records a STEP_FAILED event, and presents the partial completion state and next-step recovery options to the user.
4. M11 does not retry failed steps automatically. Retry requires user direction.
5. Plans are deterministic: given the same coordination state and goal, M11 always computes the same plan.

### Coordination Boundaries

M11 operates within the active workspace. It does not coordinate bases across multiple workspaces. All plan steps target the active workspace.

The workspace resolver (`runtime/current_workspace.md`, `runtime/workspaces.md`) is read at session start to identify the active workspace. If workspace drift is detected (R4a–R4e), M11 reports it and does not proceed until drift is resolved.

---

## 8. Ownership Model

### AD-002 — M11 Derives State; It Does Not Own Lifecycle Truth

M11 owns:

- Coordination state projections: `WORKSPACE_ROOT/runtime/pipeline/pipeline_state.md`
- Session event records: `WORKSPACE_ROOT/runtime/pipeline/events.md`
- The session_id namespace within the workspace

M11 reads but does not own:

| Truth Source | Owner | What M11 reads |
|--------------|-------|----------------|
| `WORKSPACE_ROOT/runtime/sources.md` | M1 | Source registry: ingested sources without extracted artifacts (INGESTED state discovery) |
| `WORKSPACE_ROOT/knowledge_base/extracted/*_knowledge.md` | M2 | Existence and content (base discovery, DISCOVERING gate) |
| `WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md` | M3 | Conflict status (OPEN, CONSOLIDATED) |
| `WORKSPACE_ROOT/knowledge_base/questions/questions_report.md` | M4 | Question status (UNANSWERED, VALIDATED, RESOLVED) |
| `WORKSPACE_ROOT/knowledge_base/consolidated/*_consolidated.md` | M6 | Existence (KNOWLEDGE_READY gate) |
| `WORKSPACE_ROOT/specifications/draft/*_specification.md` | M7 | Existence (SPECIFICATION_READY gate) |
| `WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md` | M8/M9 | Lifecycle event log (BASELINE, REOPEN, EVOLVE, ARCHIVE event types) |
| `runtime/workspaces.md` | M10 | Active workspace identification |
| `runtime/current_workspace.md` | M10 | Active workspace resolver |

M11 must not modify any artifact owned by M1–M10. Modification of a truth source by M11 is workspace contamination.

### pipeline_state.md as Projection

`WORKSPACE_ROOT/runtime/pipeline/pipeline_state.md` is a coordination projection. It is reconstructable from the workspace at any time by re-deriving coordination states from all truth sources. If `pipeline_state.md` is absent or unreadable:

1. M11 reconstructs it from the workspace.
2. M11 records a CHECKPOINT_RECONSTRUCTION event.
3. M11 proceeds with the reconstructed projection.

Loss of `pipeline_state.md` does not cause data loss. It causes a one-time reconstruction overhead at the next session start.

---

## 9. Persistence Model

### M11 Initialization

Before session start rules are evaluated, M11 performs a one-time initialization check: if `WORKSPACE_ROOT/runtime/pipeline/` does not exist, M11 creates it. This ensures PC3 is satisfiable on the first invocation against any workspace, including workspaces created before M11 was deployed. If the directory cannot be created, M11 reports a BLOCKING initialization failure and stops.

### Files Owned by M11

| File | Role | Behavior |
|------|------|----------|
| `WORKSPACE_ROOT/runtime/pipeline/pipeline_state.md` | Coordination projection | Written at session start (reconstruction or update). Updated after each plan step. |
| `WORKSPACE_ROOT/runtime/pipeline/events.md` | Workspace event history | Append-only. One record per event. Never modified after write. |

### Pipeline State Format

`pipeline_state.md` contains one row per known base in the active workspace.

Required fields per row:
- `base` — base stem name
- `coordination_state` — current derived coordination state
- `last_event_id` — ID of the most recent event affecting this base
- `last_updated` — ISO 8601 timestamp of the last projection update
- `flags` — current business flags (see below)

### Business Flags

Flags are derived from workspace artifact state. They are stored in `pipeline_state.md` as a convenience but are always re-derived from the workspace at session start.

| Flag | Set when |
|------|----------|
| `specification_available` | A draft specification exists for this base |
| `baseline_available` | Draft specification exists AND all questions are in VALIDATED or RESOLVED status — BASELINE is immediately executable |
| `open_questions` | At least one question for this base is in UNANSWERED, PARTIALLY_ANSWERED, or REJECTED status |
| `human_action_required` | `open_questions` is set AND no plan step can proceed without human input |
| `change_pending` | A Change Event has been recorded for this base but has not yet been resolved through UNDER_REVISION → BASELINED or → CLOSED |
| `resume_available` | A prior session for this base was interrupted; a PAUSE event exists in the event log for a session that did not reach a terminal state |
| `quality_gated` | Derived from `sqf_gate_report.md` in `specifications/draft/` or `specifications/stable/`: `PASS` / `WARN` / `BLOCK` / `PENDING` (gate_status = PENDING_D7) / `NOT_RUN` (no report found — pre-SQF workspace or spec generated before WP-SQF-2). This flag is informational — M11 does not block on `quality_gated = BLOCK`; the blocking is enforced by `/specification-lifecycle` E7. |

### events.md Format

`events.md` contains one event block per event in append order. Events are not grouped by session. The complete workspace event history is visible in a single file.

### Write Ordering

M11 appends the step completion event before updating the coordination projection. If the `pipeline_state.md` update fails after an event has been appended, the event log is the authoritative record. M11 reconstructs `pipeline_state.md` from the workspace at the next session start.

---

## 10. Resume and Recovery

### Pause

A coordination session may be paused at any time by the user. Pausing is always valid — there is no coordination state from which pausing is prohibited. On pause:

1. M11 appends a PAUSE event to `events.md` with the current session_id and the last completed plan step.
2. M11 updates `pipeline_state.md` to reflect the current coordination state of all affected bases.
3. M11 reports the pause point and the remaining plan steps to the user.

### Resume

When the user invokes `/pipeline-run` against a base with `resume_available` flag set:

1. M11 reads the event log to identify the most recent partial session for the base.
2. M11 re-derives the current coordination state from workspace artifacts (not from the cached projection).
3. M11 presents the prior partial plan and the current derived state to the user.
4. If the workspace state has changed since the pause, M11 reports the change and recomputes the plan from the current derived state.
5. The user confirms or modifies the resumed plan before execution continues.

### Recovery

If a plan step fails mid-execution:

1. M11 appends a STEP_FAILED event to `events.md` with the failing step, the error, and the coordination state at failure time.
2. M11 does not roll back completed plan steps. Completed steps are durable.
3. M11 presents the failure with: the step that failed, the current coordination state of the affected base, and the remaining plan steps.
4. The user may retry the failed step, abort the session, or modify the goal.

If `pipeline_state.md` is absent or unreadable at session start, M11 executes the Checkpoint Reconstruction procedure as part of M11 initialization (Section 9), before session start rules are evaluated.

### Checkpoint Reconstruction

Checkpoint reconstruction rebuilds `pipeline_state.md` by:

1. Discovering all bases in the active workspace: (a) scanning `knowledge_base/extracted/` for `*_knowledge.md` files; (b) scanning `runtime/sources.md` for rows with Status=ingested where no corresponding `_knowledge.md` exists in `knowledge_base/extracted/`.
2. For each base, re-deriving its coordination state from all truth sources (conflicts_report.md, questions_report.md, specifications/lifecycle/specifications_lifecycle.md, and presence of consolidated and draft artifacts).
3. Setting `last_event_id` for each base by scanning `events.md` for the most recent event for that base.
4. Writing the reconstructed `pipeline_state.md`.
5. Appending a CHECKPOINT_RECONSTRUCTION event to `events.md`.

Checkpoint reconstruction does not modify any M1–M10 artifact. It is a read-then-write operation on M11-owned files only.

### Governance Gate Resume

When Phase 9.5 — Initial Governance Evaluation Gate invokes M12 and M12 returns GOVERNANCE_ESCALATED, M11 enters a Governance Gate pause. A PAUSE event with `payload.event_signal = GOVERNANCE_GATE` is appended to `events.md`. The base is not advanced. M11 waits. A Governance Gate pause is entered for both ESCALATION_RECORDED and DELEGATION_ASSIGNED outcomes. M13 manages the lifecycle of both. M11 treats GOVERNANCE_ESCALATED uniformly at the routing level regardless of the underlying outcome type.

When M13 has closed the open governance outcome, the user signals M11 to resume via `/pipeline-run <base> --event GOVERNANCE_RESOLVED`.

M11 must not treat this signal as execution authorization. Phase 8.G — Governance Gate Resume Procedure governs this path:

1. M11 verifies the governance outcome closure in `WORKSPACE_ROOT/runtime/governance/events.md`.
2. If M13's terminal decision was REJECTED: M11 appends GOVERNANCE_RESUME_DENIED and terminates the affected plan steps. M12 is not re-invoked.
3. If M13's terminal decision was APPROVED or DENIED, or if the outcome was closed by a governance lifecycle event (policy supersession via OUTCOME_SUPERSEDED, delegation expiry via DELEGATION_EXPIRED, or outcome invalidation via OUTCOME_INVALIDATED): M11 constructs a fresh resume plan from the verified remaining plan steps and invokes M12 for an independent re-evaluation under the current governance state. A lifecycle closure is not a human authority decision and does not bypass M12.
4. M12's new Governance Verdict Set is the sole authorization input. M11 routes by the new Governance Cycle Result Code.
5. On GOVERNANCE_COMPLETE: M11 re-enters the Confirmation Gate (Phase 9) for user confirmation before execution resumes.
6. On GOVERNANCE_ESCALATED: M11 emits a new PAUSE event with `event_signal: GOVERNANCE_GATE` and waits for a subsequent GOVERNANCE_RESOLVED signal. The new PAUSE event carries `prior_outcome_id` and `repause_sequence` to distinguish it from the original pause.

No Governance Verdict Set from a prior cycle is reused. The M13 terminal decision does not substitute for M12 evaluation.

---

## 11. Validation Rules

All validation rules are verified at the point noted. Rules marked BLOCKING stop execution and report an error. Rules marked WARNING are reported but do not stop execution.

### M11 Initialization Rules

| Rule | Condition | Classification |
|------|-----------|----------------|
| PC0 | If `WORKSPACE_ROOT/runtime/pipeline/` does not exist, M11 creates it before session start rules are evaluated. If creation fails, M11 stops and reports a BLOCKING initialization failure. | BLOCKING |

### Session Start Rules

| Rule | Condition | Classification |
|------|-----------|----------------|
| PC1 | Active workspace is resolvable from `runtime/current_workspace.md` and `runtime/workspaces.md` | BLOCKING |
| PC2 | Active workspace has `status: active` in the registry (R4b) | BLOCKING |
| PC3 | `WORKSPACE_ROOT/runtime/pipeline/` directory exists (ensured by PC0) | BLOCKING |
| PC4 | If `pipeline_state.md` exists, it is readable | BLOCKING |
| PC5 | If `events.md` exists, it is readable and append-only invariant is intact (no event_id gaps or modifications detected) | WARNING |
| PC6 | Workspace drift between `runtime/current_workspace.md` and `runtime/workspaces.md` is reported before any plan computation | WARNING |

### Base Discovery Rules

| Rule | Condition | Classification |
|------|-----------|----------------|
| PC7 | At least one base exists in the workspace: either a `*_knowledge.md` file in `knowledge_base/extracted/` or a source with Status=ingested in `runtime/sources.md` with no corresponding `_knowledge.md` | BLOCKING |
| PC8 | The named base in the goal declaration is present in `knowledge_base/extracted/` as a `*_knowledge.md` file OR present in `runtime/sources.md` with Status=ingested | BLOCKING |
| PC9 | Coordination state for each discovered base is derivable from workspace artifacts | BLOCKING |

### Plan Computation Rules

| Rule | Condition | Classification |
|------|-----------|----------------|
| PC10 | Target state for the goal is reachable from the current coordination state using the transition table | BLOCKING |
| PC11 | Each plan step maps to an existing M1–M10 command available in the workspace | BLOCKING |
| PC12 | Plan is presented to the user and acknowledged before execution begins | BLOCKING |
| PC12.5 | M12 is invoked via Phase 9.5 before any plan step executes. Phase 10 may not begin until GOVERNANCE_EVALUATION_COMPLETED is recorded with `governance_cycle_result = GOVERNANCE_COMPLETE` for the current session and base. In ALL mode, all Phase 9.5 evaluations complete before Phase 10 begins for any base (GD-8). | BLOCKING |

### Execution Rules

| Rule | Condition | Classification |
|------|-----------|----------------|
| PC13 | M11 does not modify any M1–M10-owned artifact during plan execution | BLOCKING |
| PC14 | After each plan step, the coordination state of the affected base is re-derived from workspace artifacts before the next step is computed | BLOCKING |
| PC15 | Each event record written to `events.md` contains non-empty values for: event_id, session_id, event_type, timestamp, actor; `base` is non-empty for base-scoped events | BLOCKING |

### Persistence Rules

| Rule | Condition | Classification |
|------|-----------|----------------|
| PC16 | `pipeline_state.md` is written before the session is reported as complete | BLOCKING |
| PC17 | `events.md` is append-only: no existing event record is modified by any M11 operation | BLOCKING |
| PC18 | `pipeline_state.md` derived state matches the workspace artifact state at the time of the last write | WARNING |

---

## 12. Success Conditions

M11 is complete when all of the following are true:

1. `/pipeline-run` (status view) produces an accurate, current coordination state view for all non-CLOSED bases in the active workspace, derived from workspace artifacts.

2. `/pipeline-run <base>` correctly advances a base from its current coordination state to the next logical state by computing and executing a deterministic plan of M1–M10 invocations.

3. The Revision Rule is enforced: a live invocation of `/pipeline-run` against a BASELINED base with a CHANGE_REQUEST event produces a transition to UNDER_REVISION. No direct path from BASELINED to BASELINED is available without passing through UNDER_REVISION.

4. The Discovery Shortcut is exercised: a base with zero unresolved questions after conflict detection transitions directly from DISCOVERING to KNOWLEDGE_READY without requiring an AWAITING_VALIDATION or VALIDATION_RECEIVED step.

5. Pause and Resume are validated: a session interrupted mid-plan is resumable in a subsequent session. The resumed session correctly identifies the last completed step, re-derives the current coordination state from the workspace, and continues the plan from the correct point.

6. Checkpoint Reconstruction is validated: `pipeline_state.md` is deleted, `/pipeline-run` is invoked, and the projection is correctly reconstructed from workspace artifacts without data loss or error.

7. Ownership boundary is enforced: no M1–M10-owned artifact is modified by any M11 operation during a full-lifecycle validation run. This is verified by computing checksums on all M1–M10 artifacts before and after the M11 session.

8. All validation rules PC0–PC18 pass for their respective operation phases during the E2E validation.

9. M11 initialization (PC0) is validated: `/pipeline-run` is invoked against a workspace where `runtime/pipeline/` does not yet exist; M11 creates the directory and proceeds without error.

---

## 13. Risks and Non-Goals

### BLOCKING Risks

| Risk | Description |
|------|-------------|
| R-B1: State derivation divergence | If M11's state derivation logic disagrees with the artifact state produced by M1–M10, the computed coordination state will be wrong and the plan will be incorrect. Mitigation: state derivation must reference the same artifact paths and status field semantics used by M1–M10 command contracts. The L2 execution specification must enumerate every artifact and field M11 reads per state gate, with references to the owning command's L1 contract. |
| R-B2: Revision Rule bypass | If a Change Event does not reliably trigger the BASELINED → UNDER_REVISION transition, a BASELINED specification could be silently overwritten. The Revision Rule must be enforced with no exception path. Any direct BASELINED → BASELINED transition in the L2 implementation is a contract violation. |
| R-B3: Plan execution modifies M1–M10 artifacts | If M11 writes to any M1–M10-owned artifact (e.g., by incorrectly scoping a write operation to the wrong path), it violates AD-002 and corrupts the workspace truth sources. Mitigation: PC13 must be verified by static path analysis in L2 and confirmed by artifact checksum comparison in E2E validation. |

### NON-BLOCKING Risks

| Risk | Description |
|------|-------------|
| R-NB1: events.md growth at scale | An append-only event log grows unboundedly over the lifetime of a workspace. For workspaces with many bases and many sessions, `events.md` may become large. No compaction mechanism is defined in M11. This is acceptable at current scale; compaction is a post-M12 concern. |
| R-NB2: Checkpoint reconstruction cost | If `pipeline_state.md` is absent, reconstruction requires reading all truth source artifacts for all bases. For large workspaces, this may be slow. Reconstruction is a rare recovery path, not a nominal operation. No optimization is required at M11. |
| R-NB3: Multi-base goal ordering | When `ALL` is used as the goal target, M11 must define a deterministic ordering for base processing. If ordering is not defined in L2, different sessions may process bases in different orders, producing non-reproducible event logs. The L2 execution specification must define the canonical base processing order (e.g., alphabetical by base stem). |

### OBSERVATIONS

| Observation | Description |
|-------------|-------------|
| OB1: CLOSED is terminal within M11 | CLOSED bases are excluded from status views, `ALL` goal targets, and plan computation. A CLOSED base may still be consulted (its artifacts are readable under the workspace isolation contract), but M11 will not generate plans for it. |
| OB2: pipeline_state.md is not a lock | `pipeline_state.md` does not prevent concurrent modification of workspace artifacts by other means (e.g., direct user edits). M11 re-derives state from workspace artifacts at session start precisely to detect such external changes. |
| OB3: Session IDs and event IDs are workspace-scoped | session_id and event_id values are unique within a workspace but not globally unique. If a workspace is copied or merged, ID collision may occur. This is a post-M12 concern. |
| OB4: Interactive breakpoints require L2 definition | Plan steps requiring human interaction (M5 Human Validation) suspend execution and hand control to the user. The exact protocol for interactive breakpoints — how M11 signals the user, how the user signals readiness to continue, and how M11 verifies the interactive step completed successfully — must be defined precisely in the L2 execution specification. |

### Non-Goals

The following capabilities are explicitly outside M11:

| Capability | Reason |
|------------|--------|
| Automated pipeline chaining without user confirmation | M12 scope |
| Non-interactive stage runner | M12 scope |
| Multi-workspace coordination | Post-M12 scope |
| Conflict resolution logic | M3–M6 scope |
| Question generation or presentation | M4 scope |
| Specification lifecycle operations (BASELINE, REOPEN, EVOLVE, ARCHIVE) | M8–M9 scope |
| Workspace CREATE, SWITCH, ARCHIVE | M10 scope |
| Parallel base processing | Not defined; single-base-at-a-time plan execution is the M11 model |
| events.md compaction or rotation | Post-M12 maintenance concern |
| Global (cross-workspace) pipeline visibility | Not defined at this milestone |
| Undo / rollback of completed plan steps | Not defined; completed steps are durable |

---

## Final Recommendation

This Layer 1 Contract is **APPROVED**.

**Architecture decisions integrated:**

AD-001 — M11 is a Deterministic Orchestrator: Integrated in Section 7 (Coordination Model). M11 computes and executes plans by invoking M1–M10. The business logic boundary is enforced at L1: M11 may not replicate the internal logic of any M1–M10 command.

AD-002 — M11 Derives State; It Does Not Own Lifecycle Truth: Integrated in Section 8 (Ownership Model). The ownership table enumerates every truth source, its owner, and what M11 reads. `pipeline_state.md` is explicitly defined as a reconstructable projection.

Base = Coordination Unit: Integrated in Section 3 (Core Concepts) and throughout the state model. All business states, flags, and events belong to bases, not workspaces.

CLOSED replacing ARCHIVED: Integrated in Section 4. CLOSED is the terminal coordination state within M11, disambiguated from M9's specification ARCHIVE operation.

Complete transition table including Discovery Shortcut and Revision Rule: Integrated in Section 4 with the full tabular transition specification.

**Open items delegated to L2:**

- Canonical base processing order for `ALL` goal targets (R-NB3).
- Interactive breakpoint protocol for M5 integration (OB4).
- Path enumeration for state derivation (R-B1 mitigation — each state gate's required artifact reads).
- Static path analysis confirming PC13 (M11 writes no M1–M10-owned artifact).
- E2E validation corpus specification.
