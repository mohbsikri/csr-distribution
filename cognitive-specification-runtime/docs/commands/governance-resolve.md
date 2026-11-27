# Governance Outcome Resolution Runtime

**Version:** 1.0
**Status:** VALIDATED
**Milestone:** M13
**Command:** `/governance-resolve`
**Layer:** Layer 1 Contract

---

## Purpose

Close governance outcomes that M12 opened but cannot close.

M13 receives terminal external governance decisions, validates each resolution attempt against the active Policy Profile, records all resolution activity, and closes open governance outcomes through four closure paths. All outcome closures produce governance events that M11 reads to detect whether a Governance Pause has been lifted and resume conditions are met.

This command implements Stage 13 — Governance Outcome Resolution Runtime of the CSR pipeline.

---

## Scope

M13 governs the complete lifecycle of all open governance outcomes from creation to closure. An outcome enters M13 scope at the moment M12 appends an ESCALATION_RECORDED or DELEGATION_ASSIGNED event. An outcome exits M13 scope at the moment M13 appends a terminal lifecycle event closing it.

M13 acts on governance outcomes only. M13 does not govern M11 coordination state, M12 policy evaluation logic, Policy Profile definitions, workspace artifact lifecycle, or any plan execution behavior.

---

## Invocation

```text
/governance-resolve
/governance-resolve <outcome_id>
/governance-resolve <outcome_id> APPROVED
/governance-resolve <outcome_id> REJECTED
/governance-resolve <outcome_id> DENIED
/governance-resolve --validate
```

| Form | Mode | Behavior |
|------|------|----------|
| No arguments | STATUS | Present all open governance outcomes. Run validity evaluation. No resolution processed. |
| `<outcome_id>` | INSPECT | Present full detail for one outcome. Run validity evaluation. No resolution processed. |
| `<outcome_id> APPROVED` | RESOLVE | Submit APPROVED terminal decision for the named outcome. |
| `<outcome_id> REJECTED` | RESOLVE | Submit REJECTED terminal decision for the named outcome. |
| `<outcome_id> DENIED` | RESOLVE | Submit DENIED terminal decision for the named outcome. |
| `--validate` | VALIDATE | Run validity evaluation only. Close expired, superseded, and invalidated outcomes. No resolution processed. |

If the invocation form is unrecognizable: report `BLOCKED — Unrecognized invocation form. See usage above.` Stop.

If `<outcome_id>` does not identify a known governance outcome: report `BLOCKED — Outcome not found: <outcome_id>`. Stop.

If `<outcome_id>` in RESOLVE mode identifies an already-closed outcome: report `BLOCKED — Outcome already closed: <outcome_id>. Closure path: <closure_path>. Terminal decisions may not be submitted against a closed outcome.` Stop.

---

## Workspace Resolution

Before any file operation, resolve the active workspace:

```text
W1: Read runtime/current_workspace.md and parse workspace_id.
W2: Build WORKSPACE_ROOT = workspaces/<workspace_id>/
W3: Verify WORKSPACE_ROOT exists. If not found, stop:
    BLOCKED — Workspace Root Not Found: workspaces/<workspace_id>/
W4: Validate registry entry in runtime/workspaces.md (R4a—R4e).
W5: All subsequent paths are prefixed with WORKSPACE_ROOT.
```

---

## Workspace Isolation

M13 owns exactly two artifacts and one directory:

```text
WORKSPACE_ROOT/runtime/governance/governance_state.md  — governance outcome projection (write)
WORKSPACE_ROOT/runtime/governance/events.md            — governance event log (append-only, shared with M12)
WORKSPACE_ROOT/runtime/governance/                     — created on first invocation if absent (PC0)
```

All write operations must target paths within these three targets. Any write to a path outside these targets is a workspace contamination violation. If such a write is about to occur: stop immediately. Report:

```text
WORKSPACE CONTAMINATION DETECTED
Violating path: <path>
M13 must not write to this path.
Session terminated.
```

M13 reads the following paths as read-only inputs. These paths are not owned by M13 and must never be written:

```text
WORKSPACE_ROOT/runtime/pipeline/events.md              — M11 event log (session invalidation detection and base CLOSED coordination state detection)
WORKSPACE_ROOT/governance/policy_profile.md            — active Policy Profile (authority validation, expiration intervals, supersession detection)
WORKSPACE_ROOT/runtime/workspaces.md                   — workspace registry
```

The path to the active Policy Profile follows the Policy Profile architecture. The reference path above is subject to amendment when the Policy Profile architecture (M14 future) is defined.

---

## Preconditions

| ID | Condition | Action on Failure |
|----|-----------|-------------------|
| PC0 | `WORKSPACE_ROOT/runtime/governance/` directory exists or is created on first invocation | Create on first invocation. If creation fails, stop: `BLOCKED — Cannot initialize M13 directory` |
| PC1 | `docs/commands/governance-resolve.md` is readable | Stop: `BLOCKED — L1 contract not found: docs/commands/governance-resolve.md` |
| PC2 | `runtime/current_workspace.md` is readable | Stop: `BLOCKED — Workspace control file unavailable` |
| PC3 | `runtime/workspaces.md` is readable | Stop: `BLOCKED — Workspace registry unavailable` |
| PC4 | Active Policy Profile is readable | Stop: `BLOCKED — Active Policy Profile unavailable. M13 cannot validate resolution authority without the Policy Profile.` |
| PC5 | `WORKSPACE_ROOT/runtime/governance/events.md` exists and is readable, or does not exist (first invocation) | Stop if present but unreadable: `BLOCKED — Governance event log present but unreadable` |

PC4 is required for all modes. Validity evaluation and resolution validation both depend on the active Policy Profile.

PC5: On first invocation, `events.md` is initialized in PC0 directory creation. If `events.md` exists but is unreadable, M13 cannot reconstruct outcome state and must stop.

---

## Responsibilities

M13 is responsible for:

- Receiving external governance decisions submitted by human actors with terminal authority
- Validating each resolution attempt for authority eligibility and decision type against the active Policy Profile
- Recording all resolution attempts, valid and invalid, with full traceability
- Evaluating open outcome validity at every invocation before processing any incoming resolution
- Closing open outcomes that fail validity through the appropriate validity termination path
- Closing open outcomes for which a valid terminal decision is received through the RESOLVED path
- Maintaining the governance outcome projection as a reconstructable artifact
- Producing governance events that M11 reads to detect Governance Pause lift and resume eligibility

---

## Non-Responsibilities

M13 is not responsible for:

- Producing Verdicts (exclusively M12)
- Creating governance outcomes (exclusively M12 via ESCALATION_RECORDED and DELEGATION_ASSIGNED events)
- Policy Profile lifecycle — defining, versioning, activating, or superseding Policy Profiles (M14 future)
- Invoking M11, M12, or any other runtime
- Routing governance decisions to external authorities
- Re-escalating or re-delegating on outcome expiration, supersession, or invalidation
- Evaluating the substantive correctness of an authority's decision — only structural eligibility and decision type
- Making planning decisions about what M11 should do after an outcome closes
- Enforcing M11 execution behavior following resume

---

## Inputs

| Artifact | Source | Usage |
|----------|--------|-------|
| `WORKSPACE_ROOT/runtime/governance/events.md` | Shared governance event log (M12 and M13) | Outcome reconstruction — M13 reads all events to derive current open outcomes |
| Active Policy Profile | Governance Policy Profile (path follows M14 architecture) | Authority eligibility validation, terminal authority tier definitions, delegation response intervals, supersession detection |
| `WORKSPACE_ROOT/runtime/pipeline/events.md` | M11 event log | Session invalidation detection — M13 reads to determine whether originating M11 sessions are in terminal state or whether a newer session for the same base exists; base CLOSED coordination state detection |
| Resolution submission | Invocation argument | Outcome ID, decision type, submitter context |

All inputs are read-only. M13 never modifies input artifacts.

---

## Outputs

| Artifact | Path | Write Mode |
|----------|------|------------|
| Governance event log entries | `WORKSPACE_ROOT/runtime/governance/events.md` | Append-only |
| Governance outcome projection | `WORKSPACE_ROOT/runtime/governance/governance_state.md` | Overwrite |

M13 appends the following event types to the governance event log:

| Event | Trigger |
|-------|---------|
| `RESOLUTION_RECEIVED` | Every resolution attempt submitted, valid or invalid |
| `RESOLUTION_REJECTED` | Submitted resolution fails authority eligibility or decision type validation |
| `RESOLUTION_RECORDED` | Valid terminal decision accepted; outcome transitions to RESOLVED |
| `OUTCOME_SUPERSEDED` | Open outcome closed due to Policy Profile version change |
| `DELEGATION_EXPIRED` | Open DELEGATION_ASSIGNED outcome closed due to response interval exceeded |
| `OUTCOME_INVALIDATED` | Open outcome closed due to session terminal state, base CLOSED coordination state, or superseding M11 session |

No other event types are appended by M13. M13 never appends ESCALATION_RECORDED, DELEGATION_ASSIGNED, or any M11 or M12 event type.

---

## Outcome Lifecycle Model

A governance outcome has two states:

**OPEN**
The outcome is active. M11 is in Governance Pause for the associated base. No terminal decision has been received or applied. No validity failure condition applies.

**CLOSED**
The outcome is permanently closed through one of four closure paths. No further resolution activity is possible against a closed outcome. Closed outcomes are not reopened.

The transition from OPEN to CLOSED is one-directional and irreversible. CLOSED is a terminal state.

An outcome in OPEN state carries:

| Field | Description |
|-------|-------------|
| `outcome_id` | Unique identifier assigned at creation by M12 |
| `outcome_type` | `ESCALATION_RECORDED` or `DELEGATION_ASSIGNED` |
| `base` | The base name the outcome is associated with |
| `session_id` | The M11 session that generated the M12 evaluation producing this outcome |
| `policy_version` | The Policy Profile version active at M12 evaluation time (DMA-01 dependency) |
| `created_at` | Timestamp of the M12 creation event |
| `tier` | The escalation or delegation tier defined in the Policy Profile |

These fields are derived from the ESCALATION_RECORDED or DELEGATION_ASSIGNED event in the governance event log. M13 never stores state independently of the event log.

---

## Closure Paths

### RESOLVED

Triggered by: a valid terminal decision received from an eligible authority.

The submitter is validated as a terminal authority for the outcome's tier per the active Policy Profile. The decision type is APPROVED, REJECTED, or DENIED.

M13 appends: RESOLUTION_RECEIVED, then RESOLUTION_RECORDED.

The RESOLUTION_RECORDED event carries the decision type, submitter identity, outcome_id, and timestamp. M11 and M12 read this event at resume time.

**Terminal decision types:**

| Type | Governance Meaning |
|------|--------------------|
| `APPROVED` | The external authority authorizes the governed plan step(s) to proceed |
| `REJECTED` | The external authority prohibits the governed plan step(s) |
| `DENIED` | The external authority denies the governed base overall |

M13 records the decision type. M13 does not prescribe M11 execution behavior following resume. Execution implications are resolved by M12 at re-invocation time.

### SUPERSEDED

Triggered by: the Policy Profile version recorded in the outcome creation event differs from the currently active Policy Profile version at M13 invocation time.

M13 appends: OUTCOME_SUPERSEDED.

The OUTCOME_SUPERSEDED event carries the outcome_id, the creating policy_version, the current active policy_version, and the timestamp.

This closure path is not a governance decision. The outcome is closed because the governance framework that produced it is no longer active. M11 resume detection reads this event as an outcome closure, allowing M12 re-evaluation under the current Policy Profile.

### EXPIRED

Triggered by: a DELEGATION_ASSIGNED outcome has exceeded the response interval defined for its tier in the active Policy Profile, evaluated at M13 invocation time.

Applies only to outcomes of type DELEGATION_ASSIGNED.

M13 appends: DELEGATION_EXPIRED.

The DELEGATION_EXPIRED event carries the outcome_id, the delegation assignment timestamp, the policy-defined response interval, and the computed elapsed time.

M13 does not re-delegate. M13 does not re-escalate. Post-expiration governance evaluation is M12's responsibility at next M11 invocation.

### INVALIDATED

Triggered by any of the following conditions, evaluated at M13 invocation time:

| Condition | Detection Source |
|-----------|-----------------|
| The originating M11 session has a terminal state (FAILED or BLOCKED) | M11 events.md |
| A newer M11 session for the same base was started after this outcome was created | M11 events.md |
| The base has reached CLOSED coordination state | M11 events.md |

M13 appends: OUTCOME_INVALIDATED.

The OUTCOME_INVALIDATED event carries the outcome_id, the invalidation condition, and the timestamp.

Invalidation is a lifecycle termination, not a governance decision. M11 resume detection reads this event as an outcome closure; whether and how M11 proceeds for the base is M11's determination.

### Closure Path Precedence Rule

An outcome may simultaneously satisfy more than one validity failure condition. Simultaneous conditions are not anomalies — they occur in normal operation when, for example, a policy change and a delegation timeout coincide, or when a session termination and a policy supersession occur within the same interval.

The closure path is determined by the first validity failure condition that applies in the defined evaluation order:

```
1. SUPERSEDED
2. EXPIRED
3. INVALIDATED
```

This ordering is a declared contract rule, not an implementation artifact. An outcome is closed under exactly one closure path — the one corresponding to the first condition in the evaluation order that holds at M13 invocation time. The evaluation order in the Validity Model implements this rule.

The RESOLVED path applies only when no validity failure condition is detected. An incoming terminal decision is processed only against outcomes that pass all three validity checks and remain OPEN at the time resolution processing begins.

**Rationale for ordering:**

SUPERSEDED ranks first because it reflects a deliberate organizational governance decision — a change to the governance framework itself. When the governing policy is no longer active, no time-based or operational condition is more authoritative than the explicit supersession of the policy that created the outcome.

EXPIRED ranks second because it is a policy-defined temporal mechanism operating within the original governance framework. The delegating authority and the response interval were defined by the same policy that created the outcome. Expiration is the policy's own enforcement of its authority model.

INVALIDATED ranks third because it reflects an operational lifecycle event external to the governance framework — a session terminal state, a newer session for the same base, or a base reaching CLOSED coordination state. These are CSR pipeline events, not governance policy decisions.

---

## Validity Model

Validity evaluation is mandatory at every M13 invocation. It executes before resolution processing in all modes.

M13 evaluates all open outcomes for the three validity failure conditions. Any outcome that fails a condition is closed through the corresponding closure path before any incoming resolution is processed. When an outcome simultaneously satisfies more than one validity failure condition, the closure path is determined by the Closure Path Precedence Rule defined in the Closure Paths section.

**Validity evaluation order:**

1. SUPERSEDED check: for each open outcome, compare policy_version in creation event to current active Policy Profile version. If versions differ: close as SUPERSEDED.
2. EXPIRED check: for each open DELEGATION_ASSIGNED outcome not already closed by step 1, compute elapsed time. If elapsed time exceeds the policy-defined interval for the outcome's tier: close as EXPIRED.
3. INVALIDATED check: for each open outcome not already closed by steps 1 or 2, check originating session state, newer session existence for the same base, and base CLOSED coordination state. If any invalidation condition holds: close as INVALIDATED.

If M11 events.md is unreadable: skip all three INVALIDATED conditions — session state detection, newer session detection, and base CLOSED state detection all depend on M11 events.md. Report:

```text
WARNING — M11 event log unreadable: session invalidation detection and base CLOSED state detection unavailable.
The following outcomes may be incorrectly held OPEN: <list of open outcome_ids by base>.
Proceed with reduced validity coverage.
```

Continue. Validity warnings are not BLOCKED conditions. M13 proceeds with the validity checks it can perform.

---

## Runtime State Model

M13 maintains no independent runtime state. All state is derived from the governance event log at invocation time.

At every invocation, M13 derives:

- The set of all outcomes (OPEN and CLOSED) from ESCALATION_RECORDED and DELEGATION_ASSIGNED events
- The closure state of each outcome from RESOLUTION_RECORDED, OUTCOME_SUPERSEDED, DELEGATION_EXPIRED, and OUTCOME_INVALIDATED events
- The active Policy Profile version for supersession comparison
- The elapsed time since each DELEGATION_ASSIGNED event for expiration comparison
- The M11 session states for each base with open outcomes, from M11 events.md
- The base CLOSED coordination state for each base with open outcomes, from M11 events.md

The governance outcome projection (`governance_state.md`) is a reconstructable artifact. It is updated after each closure operation. It is never read as input to outcome derivation.

**The projection is refreshed only by M13, and is stale between an M12 cycle and the next M13 invocation.** M12 produces governance outcomes without writing it (AD-002, DMA-05), so after any M12 evaluation that escalates or delegates, the projection understates the open set until M13 next runs. The file is correct as of its own watermark and wrong about the present.

Every version of the projection from 1.1 onward therefore carries two watermark fields — `Source Event Count` and `Source Last Event` — recording the state of `runtime/governance/events.md` at write time. **Any consumer must compare them against that log before presenting the projection's contents.** If either differs, the projection is STALE: reconstruct the open set from the event log (RR-1 / AD-001), or state that the figures predate the current state and name the watermark. Stale figures must never be reported as current. The event log is authoritative at all times; the projection is a convenience that must prove its own age. See `governance-resolve_execution.md` § Staleness Detection.

---

## Resolution Model

Resolution processing applies in RESOLVE mode only. Validity evaluation always precedes resolution processing.

**Resolution validation sequence:**

1. Record RESOLUTION_RECEIVED with full submission metadata.
2. Confirm the outcome exists and is in OPEN state.
3. Validate authority eligibility: the submitter must be designated as a terminal authority for the outcome's tier in the active Policy Profile.
4. Validate decision type: the submitted decision must be APPROVED, REJECTED, or DENIED.
5. If either validation fails: record RESOLUTION_REJECTED with rejection reason. Outcome remains OPEN. Stop.
6. If both validations pass: record RESOLUTION_RECORDED. Outcome transitions to CLOSED with closure path RESOLVED.
7. Update governance_state.md.

Resolution validation is structural. M13 validates that the submitter has the authority to make a terminal decision for this outcome's tier, and that the decision type chosen is terminal. M13 does not evaluate whether the decision is substantively correct, policy-compliant, or appropriate for the situation.

**RESOLUTION_REJECTED reasons:**

| Code | Condition |
|------|-----------|
| `INELIGIBLE_AUTHORITY` | Submitter is not designated as a terminal authority for this outcome's tier in the active Policy Profile |
| `NON_TERMINAL_DECISION_TYPE` | Decision type submitted is not APPROVED, REJECTED, or DENIED (e.g., re-escalation, deferral, abstention) |
| `OUTCOME_ALREADY_CLOSED` | Outcome is in CLOSED state; no further resolution is possible |

An invalid resolution attempt does not reset or extend the expiration timer of the outcome.

---

## Runtime Invariants

These invariants are unconditional. No input, mode, or condition may override them.

**RI-01 — Outcome Closure Finality**
A closed governance outcome is permanently closed. M13 never reopens a closed outcome. No operation applied to a closed outcome changes its state.

**RI-02 — No Outcome Creation**
M13 never appends ESCALATION_RECORDED or DELEGATION_ASSIGNED events. Outcome creation belongs exclusively to M12. This invariant has no exceptions.

**RI-03 — Terminal Decisions Only**
M13 accepts only APPROVED, REJECTED, and DENIED as valid terminal decision types. Any other decision type submitted produces RESOLUTION_REJECTED with reason NON_TERMINAL_DECISION_TYPE. This invariant has no exceptions.

**RI-04 — RESOLUTION_RECEIVED Before RESOLUTION_REJECTED or RESOLUTION_RECORDED**
For every resolution attempt, RESOLUTION_RECEIVED must be appended before RESOLUTION_REJECTED or RESOLUTION_RECORDED. The audit trail of the submission precedes any outcome determination.

**RI-05 — Validity Evaluation Before Resolution Processing**
At every invocation, validity evaluation (RI-01 through step 3 of the Validity Model) executes before any incoming resolution is processed. This ordering is mandatory in all modes including RESOLVE mode.

**RI-06 — Append-Only Event Log**
The governance event log is append-only. No existing event record is modified after it is written. `governance_state.md` may be overwritten; `events.md` may not.

**RI-07 — No M11 or M12 Invocation**
M13 never invokes M11, M12, or any other CSR runtime. M13 produces closure events. M11 detects them independently.

**RI-08 — Expiration Timer Not Reset by Invalid Submission**
An invalid resolution attempt (RESOLUTION_REJECTED) does not reset or extend the expiration timer of the outcome. The timer runs from the DELEGATION_ASSIGNED event timestamp regardless of invalid submission history.

**RI-09 — Governance Projection Is Not a Derivation Input**
`governance_state.md` is a write target. M13 never reads it as input to outcome reconstruction, validity evaluation, or resolution processing. The governance event log is the sole derivation input.

**RI-10 — Write Ordering: Events Before Projection**
Governance event log entries must be appended before `governance_state.md` is updated. The event record of a closure precedes the projection update that reflects it.

**Correspondence with the execution specification `[S5-narrow finding, 2026-11-01]`.** RI-01 through RI-10 above each have a counterpart in `docs/commands/governance-resolve_execution.md`, declared there as EI-01 through EI-10 in the same order and restated with execution-level detail (file paths, exact field names, enforcement points). This correspondence was never stated anywhere before this note — a reader of either file alone could not discover it, and nothing enforced that adding an RI here implies adding an EI there, or that the two texts for the "same" invariant had not quietly diverged. `EI-11` extends the set with no RI counterpart; it is a pure execution-layer enforcement detail (a guard inside RA-03/04/05) that does not belong at contract level.

---

## Failure Model

**BLOCKED — Session terminates, no partial operation proceeds**

| Condition | Report |
|-----------|--------|
| Governance event log present but unreadable | `BLOCKED — Governance event log unreadable: runtime/governance/events.md` |
| Active Policy Profile unavailable | `BLOCKED — Active Policy Profile unavailable. Resolution validation and supersession detection require the Policy Profile.` |
| M13 specification layers unreadable | `BLOCKED — L1 contract not found: docs/commands/governance-resolve.md` |
| Workspace resolution fails | `BLOCKED — <workspace resolution failure message>` |
| Invocation form unrecognizable | `BLOCKED — Unrecognized invocation form. See usage above.` |
| Outcome not found | `BLOCKED — Outcome not found: <outcome_id>` |
| Outcome already closed in RESOLVE mode | `BLOCKED — Outcome already closed: <outcome_id>. Closure path: <closure_path>. Terminal decisions may not be submitted against a closed outcome.` |

**VALIDATION_FAILURE — Resolution attempt rejected, outcome remains open, session continues**

| Condition | Event |
|-----------|-------|
| Submitter not eligible terminal authority | RESOLUTION_REJECTED with reason INELIGIBLE_AUTHORITY |
| Decision type not terminal | RESOLUTION_REJECTED with reason NON_TERMINAL_DECISION_TYPE |

**WARNING — Reduced capability, session continues**

| Condition | Impact |
|-----------|--------|
| M11 events.md unreadable | All three INVALIDATED conditions skipped: session state detection, newer session detection, and base CLOSED state detection. Affected outcome_ids reported in WARNING message. |

**WRITE_FAILURE — Event record could not be appended**

If a governance event log append fails after a prior append in the same session has succeeded: stop immediately. Report the failure with the outcome_id, the event type that failed to write, and all event types successfully written in the same session. Do not proceed with projection update if the event log append failed.

---

## Traceability Requirements

Every event M13 appends to the governance event log must carry:

| Field | Required on |
|-------|-------------|
| `event_type` | All events |
| `outcome_id` | All events except RESOLUTION_RECEIVED where outcome not yet confirmed |
| `timestamp` | All events |
| `session_ref` | All events — the M13 invocation identifier |
| `submitter` | RESOLUTION_RECEIVED, RESOLUTION_REJECTED, RESOLUTION_RECORDED |
| `decision_type` | RESOLUTION_RECEIVED, RESOLUTION_REJECTED, RESOLUTION_RECORDED |
| `rejection_reason` | RESOLUTION_REJECTED |
| `policy_version_at_creation` | OUTCOME_SUPERSEDED |
| `policy_version_current` | OUTCOME_SUPERSEDED |
| `delegation_assigned_at` | DELEGATION_EXPIRED |
| `response_interval` | DELEGATION_EXPIRED |
| `elapsed_time` | DELEGATION_EXPIRED |
| `invalidation_condition` | OUTCOME_INVALIDATED |
| `closure_path` | RESOLUTION_RECORDED, OUTCOME_SUPERSEDED, DELEGATION_EXPIRED, OUTCOME_INVALIDATED |

All resolution attempts — including rejected attempts — carry submitter identity and decision type. Traceability of invalid attempts is as important as traceability of valid ones.

---

## Cross-Runtime Dependencies

### M13 reads from

| Runtime | Artifact | Purpose |
|---------|----------|---------|
| M12 | `runtime/governance/events.md` (M12-appended events) | Outcome reconstruction — identifies ESCALATION_RECORDED and DELEGATION_ASSIGNED events as candidate outcomes |
| M11 | `runtime/pipeline/events.md` | Session invalidation detection — determines terminal state of originating M11 sessions; detects newer sessions for the same base; detects base CLOSED coordination state |
| Policy administration (M14 future) | Active Policy Profile | Authority eligibility validation, delegation response intervals, supersession detection |

### M13 writes to

| Runtime | Artifact | Purpose |
|---------|----------|---------|
| M11 (indirect) | `runtime/governance/events.md` (M13-appended events) | M11 reads closure events to detect Governance Pause lift |

### M13 never invokes

M12, M11, M10, or any other CSR runtime. All cross-runtime communication is through shared event log reads and writes.

### Shared governance event log ownership

`WORKSPACE_ROOT/runtime/governance/events.md` is shared between M12 and M13. Event type ownership defines the boundary:

- M12 owns: GOVERNANCE_SESSION_START, GOVERNANCE_SESSION_END, ESCALATION_RECORDED, DELEGATION_ASSIGNED, and all M12 evaluation events.
- M13 owns: RESOLUTION_RECEIVED, RESOLUTION_REJECTED, RESOLUTION_RECORDED, OUTCOME_SUPERSEDED, DELEGATION_EXPIRED, OUTCOME_INVALIDATED.

Neither runtime modifies event records written by the other.

---

## Success Criteria

A successful M13 invocation satisfies all of the following:

- Validity evaluation completed before any resolution was processed
- All open outcomes evaluated against supersession, expiration, and invalidation conditions
- All outcomes failing validity conditions closed through the correct closure path with correct events appended
- All incoming resolution attempts recorded with RESOLUTION_RECEIVED regardless of validity outcome
- Invalid resolution attempts recorded with RESOLUTION_REJECTED and rejection reason; originating outcome remains OPEN
- Valid terminal decisions recorded with RESOLUTION_RECORDED; outcome transitioned to CLOSED with closure path RESOLVED
- `governance_state.md` updated to reflect all closures in the current invocation
- Governance event log updated before `governance_state.md` updated (RI-10)
- No closed outcome reopened
- No governance outcome created
- No M11 or M12 invocation

---

## Boundary Statement

M13 — Governance Outcome Resolution Runtime owns the complete lifecycle of all open governance outcomes from the moment M12 creates them to the moment M13 closes them. M13 accepts terminal external governance decisions, validates each resolution attempt for structural eligibility (authority tier and decision type) against the active Policy Profile, records all resolution activity with full traceability including invalid attempts, and closes outcomes through four closure paths: RESOLVED (terminal decision received), SUPERSEDED (Policy Profile changed), EXPIRED (delegation timeout), and INVALIDATED (session, base, or plan no longer valid). All outcome closures produce governance events that M11 reads to detect Governance Pause lift conditions.

M13 does not produce Verdicts. M13 does not create governance outcomes. M13 does not own Policy Profile lifecycle. M13 does not invoke M11, M12, or any other runtime. M13 does not re-escalate or re-delegate. M13 validates structural eligibility of resolutions; it does not evaluate the substantive correctness of decisions. M13 derives all runtime state from the governance event log; it never reads the governance outcome projection as a derivation input.

---

## Deferred Cross-Milestone Amendments

### DMA-01

**Source:** M13 Boundary Refinement

**Description:** M12 outcome creation events (ESCALATION_RECORDED and DELEGATION_ASSIGNED) must include the Policy Profile version active at outcome creation time.

**Status:** APPLIED

**Application Target:** M12 Layer 2 Amendment

**Reason:** Required for M13 policy supersession detection (Validity Model, SUPERSEDED condition).

This item has been applied to the M12 Layer 2 Execution Specification in this materialization.

---

### DMA-02

**Source:** M13 Layer 1 Contract Challenge — BF-1

**Description:** M12 outcome creation events (ESCALATION_RECORDED and DELEGATION_ASSIGNED) must include the M11 session_id that triggered the M12 evaluation. M13 requires this field to correlate open outcomes with their originating M11 sessions for session state detection (Validity Model, INVALIDATED condition, first and second rows).

**Status:** APPLIED

**Application Target:** M12 Layer 2 Amendment

**Reason:** Required for M13 INVALIDATED closure path. Session state correlation via M11 events.md depends on matching outcome events to M11 sessions by session_id. Without this field, M13 cannot determine whether the session that produced a given outcome has reached a terminal state or whether a newer session for the same base has started.

This item has been applied to the M12 Layer 2 Execution Specification in this materialization.

---

### DMA-03

**Source:** M13 Layer 1 Contract Challenge — BF-1

**Description:** M12 outcome creation events (ESCALATION_RECORDED and DELEGATION_ASSIGNED) must include the escalation or delegation tier, matching the tier label defined in the active Policy Profile. M13 requires this field to identify which tier's terminal authorities are eligible to resolve the outcome.

**Status:** APPLIED

**Application Target:** M12 Layer 2 Amendment

**Reason:** Required for M13 RESOLVED closure path. Terminal authority validation in the Resolution Model (INELIGIBLE_AUTHORITY check) compares the submitter against the eligible terminal authorities for the outcome's tier as defined in the active Policy Profile. Without the tier field in the outcome creation event, M13 cannot execute this check.

This item has been applied to the M12 Layer 2 Execution Specification in this materialization. The `base` field is present in M12 Layer 2 ESCALATION_RECORDED and DELEGATION_ASSIGNED events, confirming DMA-04 is not required.

---

## References

```text
docs/commands/governance-resolve.md          — Layer 1 Contract (this document)
docs/commands/governance-run.md              — M12 Layer 1 Contract (Verdict production, outcome creation events)
docs/commands/pipeline-run.md               — M11 Layer 1 Contract (Governance Pause state, resume detection)
docs/governance/csr_certification_framework.md — CSR Certification Framework
docs/decisions/ADR-001-csr-language-policy.md  — language policy (canonical artifacts English; interaction surface in the user's language)
```
