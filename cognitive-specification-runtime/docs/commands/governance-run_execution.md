## M12 Layer 2 Execution Specification — Final Validation Candidate

---

**Command:** `/governance-run`
**Version:** 1.0
**Status:** VALIDATED
**Milestone:** M12 — Governance Evaluation Runtime
**Governance Layer position:** Evaluation half. Resolution half is M13 — Governance Outcome Resolution Runtime.
**Depends on:** `docs/commands/governance-run.md` (Layer 1 Contract)

---

## 1. Runtime Overview

The Governance Runtime evaluates whether an M11 Plan is sanctioned for execution under the active Policy Profile. It operates as a pure evaluation runtime: it reads the M11 Plan and reconstructed Governance State, applies the active Policy Profile against each plan step, and produces a Verdict Set.

**M12 evaluates. M12 does not execute. M12 does not resolve.**

### Scope Boundary

M12 is responsible for exactly the following:

- Deriving one Governing Situation per M11 plan step
- Reconstructing Governance State from the governance event log
- Applying the active Policy Profile to produce one Verdict per Governing Situation
- Recording governance events (VERDICT_PRODUCED, ESCALATION_RECORDED, DELEGATION_ASSIGNED)
- Returning a Verdict Set and a Governance Cycle Result Code to the caller

M12 is not responsible for the following:

- Resolving ESCALATE outcomes — M12 records ESCALATION_RECORDED and the governance cycle ends. Resolution is M13's responsibility.
- Resolving DELEGATE outcomes — M12 records DELEGATION_ASSIGNED and the governance cycle ends. Resolution is M13's responsibility.
- Executing pipeline actions — M12 does not invoke M1—M10 commands under any condition.
- Coordinating the pipeline — that is M11's responsibility.
- Amending M11 — M11 integration with M12's Verdict Set is defined in the M11 Governance Integration Amendment, which is outside the scope of this specification.
- Determining what M11 does with each Verdict code — that is M11's responsibility.

### Owned Paths

```
WORKSPACE_ROOT/runtime/governance/events.md
```

### Session Input

```
M11 Plan (from /pipeline-run confirmation gate output)
```

### Session Output

```
Verdict Set (one Verdict per plan step)
Governance Cycle Result Code
```

---

## 2. Phase Structure

```
Phase 0 — Session Initialization
    │
    ▼
Phase 1 — Workspace Validation
    │
    ▼
Phase 2 — Infrastructure Initialization
    │
    ▼
Phase 3 — Governance State Reconstruction
    │
    ▼
Phase 4 — Governing Situation Derivation
    │
    ▼
Phase 5 — Policy Profile Evaluation
    │
    ▼
Phase 6 — Verdict Set Assembly
    │
    ▼
Phase 7 — Cycle Completion
    │
    ▼
Phase 8 — Failure Handling         (cross-cutting)
Phase 9 — Projection Update        (cross-cutting)
```

Phases 0—7 execute sequentially within a governance cycle. Phases 8 and 9 are cross-cutting: Phase 8 is invoked on any failure condition; Phase 9 is invoked after each write operation and at cycle completion.

---

## 3. Phase Definitions

### Phase 0 — Session Initialization

**Purpose:** Parse the invocation and establish session identity.

**Steps:**

0.1. Parse invocation arguments:
- Extract `plan_source` (path to M11 Plan artifact, or inline plan reference).
- Extract `mode` if specified (default: EVALUATE).
- Record `session_start_timestamp`.

0.2. Assign `session_id`:
- Format: `GS-<YYYYMMDD>-<HHMMSS>`.
- `session_id` is assigned at Phase 0 and does not change during the cycle.

0.3. Validate invocation form:
- If invocation form is unrecognizable: emit `GOVERNANCE_BLOCKED`. Stop.

**Output:** `session_id`, `session_start_timestamp`, `plan_source`, `mode`

---

### Phase 1 — Workspace Validation

**Purpose:** Resolve the active workspace and verify the governance runtime directory.

**Steps:**

1.1. Read `runtime/current_workspace.md`. Parse `workspace_id`.
- If file is absent or unreadable: emit `GOVERNANCE_BLOCKED`. Stop.
- If `workspace_id` is absent or empty: emit `GOVERNANCE_BLOCKED`. Stop.

1.2. Construct `WORKSPACE_ROOT`:
```
WORKSPACE_ROOT = workspaces/<workspace_id>/
```

1.3. Verify `WORKSPACE_ROOT` exists:
- If directory is absent: emit `GOVERNANCE_BLOCKED — Workspace root not found: workspaces/<workspace_id>/`. Stop.

1.4. Confirm `WORKSPACE_ROOT` is used for all subsequent path resolution.

**Output:** `workspace_id`, `WORKSPACE_ROOT`

**Note:** No workspace registry validation is performed in Phase 1. Workspace registry authority rests with M10 and M11. M12 reads `runtime/current_workspace.md` as its sole authoritative workspace context.

---

### Phase 2 — Infrastructure Initialization

**Purpose:** Ensure M12 governance directory and owned files exist before reconstruction.

**Steps:**

2.1. Check `WORKSPACE_ROOT/runtime/governance/` exists.
- If absent: create it. Record creation in session log.

2.2. Check `WORKSPACE_ROOT/runtime/governance/events.md` exists.
- If absent: initialize with header:
  ```
  # Governance Event Log
  workspace_id: <workspace_id>
  initialized: <session_start_timestamp>
  ```
- If present: verify it is readable.

2.3. Write `GOVERNANCE_SESSION_START` event to `events.md`:
```
event_type:   GOVERNANCE_SESSION_START
session_id:   <session_id>
timestamp:    <session_start_timestamp>
plan_source:  <plan_source>
mode:         <mode>
```

2.4. Check `WORKSPACE_ROOT/runtime/governance/governance_state.md` exists.
- If absent: it will be created at first Projection Update (Phase 9).
- If present: it is used as a consistency reference only. It is never used as a state derivation input.

**Output:** `governance_dir_confirmed`, `events_md_initialized`, `SESSION_START_written`

**Invariant (RI-07):** `events.md` is append-only. No event record written in 2.3 or any prior session may be modified.

---

### Phase 3 — Governance State Reconstruction

**Purpose:** Reconstruct the current Governance State from authoritative artifacts — the event log and the active Policy Profile.

Governance State is never read from `governance_state.md`. `governance_state.md` is a projection artifact; it is never the reconstruction source.

**Steps:**

3.1. Load active Policy Profile:
- Read the Policy Profile artifact at the path registered in the governance configuration, or at the default path `WORKSPACE_ROOT/runtime/governance/policy_profile.md`.
- If absent: emit `GOVERNANCE_BLOCKED — No active Policy Profile found`. Stop.
- Apply PA-1 through PA-4.

3.2. Reconstruct Prior Verdicts (PERSISTENT scope):
- Scan `events.md` for all `VERDICT_PRODUCED` events with `verdict_scope: PERSISTENT`.
- For each: apply RA-4 then RA-4.1.
- Survivors form the Prior Verdict Register (PERSISTENT partition).

3.3. Reconstruct Prior Verdicts (UNTIL_STATE_CHANGE scope):
- Scan `events.md` for all `VERDICT_PRODUCED` events with `verdict_scope: UNTIL_STATE_CHANGE`.
- For each: apply RA-5 then RA-5.1.
- Survivors form the Prior Verdict Register (UNTIL_STATE_CHANGE partition).

3.4. Reconstruct Escalation History:
- Scan `events.md` for `ESCALATION_RECORDED` events.
- Apply RA-6.

3.5. Reconstruct Delegation Assignments:
- Scan `events.md` for `DELEGATION_ASSIGNED` events.
- Apply RA-7.

3.6. Reconstruct Policy Supersession History:
- Scan `events.md` for all `POLICY_SUPERSEDED` events.
- Build the Supersession Set: the set of all `policy_id` values that appear in any `POLICY_SUPERSEDED` event.
- Apply RA-8.
- The Supersession Set must be fully built (OR-1) before any Prior Verdict retention check is applied.

3.7. Validate Prior Verdict Register completeness:
- Apply RA-9 through RA-12.

**Output:** `active_policy_profile`, `prior_verdict_register`, `escalation_history`, `delegation_assignments`, `supersession_set`

---

### Phase 4 — Governing Situation Derivation

**Purpose:** Parse the M11 Plan and derive one Governing Situation per plan step.

**Steps:**

4.1. Read the M11 Plan artifact at `plan_source`.
- If absent or unreadable: emit `GOVERNANCE_BLOCKED`. Stop.

4.2. Parse the plan step list. For each step:
- Apply GSD-1 through GSD-6.
- Derive: `action_class`, `base_id`, `current_state`, `target_state`, `transition_type`, `authority_context`.

4.3. Validate each derived Governing Situation:
- Apply GX-01 through GX-06.

4.4. Build the Situation Set: ordered list of Governing Situations, one per plan step, preserving plan order.

**Output:** `situation_set`

---

### Phase 5 — Policy Profile Evaluation

**Purpose:** Evaluate the active Policy Profile against each Governing Situation and derive a preliminary Verdict for each.

**Steps:**

5.1. For each Governing Situation in the Situation Set (in order):

5.1.1. Check for applicable Prior Verdict:
- Apply RA-1 through RA-3 to determine whether a Prior Verdict is applicable.
- If an applicable Prior Verdict is found: it has already passed RA-4.1 / RA-5.1 in Phase 3. Apply VP-4 to carry it forward.

5.1.2. If no applicable Prior Verdict: apply PE-1 through PE-8.
- Locate applicable policy rule(s) for this Governing Situation.
- Apply GP-05 for policy gaps.
- Produce a preliminary Verdict.

5.1.3. Record the preliminary Verdict with its source: `PRIOR_REUSE`, `POLICY_MATCH`, or `GAP_DECLARATION`.

5.2. Validate all preliminary Verdicts:
- Apply GX-07 through GX-12.

**Output:** `preliminary_verdict_map` (Situation → Verdict, one per step)

---

### Phase 6 — Verdict Set Assembly

**Purpose:** Assemble the final Verdict Set from the preliminary Verdict Map and validate completeness.

**Steps:**

6.1. For each plan step (in order):
- Retrieve the preliminary Verdict from the preliminary Verdict Map.
- Assign `verdict_id` (format: `VD-<session_id>-<sequence_number>`).
- Assign `produced_at` timestamp.
- Finalize all Verdict fields per VP-1 through VP-8.

6.2. Validate the Verdict Set:
- Apply GX-13 through GX-18.
- Confirm: one Verdict per plan step, no duplicates, all required fields populated.

6.3. Write each Verdict as a `VERDICT_PRODUCED` event to `events.md`.
- Apply PR-1 through PR-3.
- Append-only. No modification to prior events.

**Output:** `verdict_set`

---

### Phase 7 — Cycle Completion

**Purpose:** Determine and record the Governance Cycle Result and finalize the session.

**Steps:**

7.1. Apply RD-1 through RD-5 to determine the Governance Cycle Result Code.

7.2. If optional `VERDICT_INVALIDATED` events are to be written (IV-6): write them before proceeding to 7.3 (OR-4).

7.3. Write `GOVERNANCE_SESSION_END` event to `events.md`:
```
event_type:        GOVERNANCE_SESSION_END
session_id:        <session_id>
timestamp:         <session_end_timestamp>
result_code:       <result_code>
verdicts_produced: <count>
```

7.4. Invoke Phase 9 — Projection Update.

7.5. Return the Governance Cycle Result Code and Verdict Set to the caller.

**Note:** When the result code is GOVERNANCE_ESCALATED — which covers both ESCALATE and DELEGATE verdicts per DT-4 — M12's responsibility ends with this return. M12 does not resolve escalation or delegation outcomes. M12 records ESCALATION_RECORDED for ESCALATE verdicts and DELEGATION_ASSIGNED for DELEGATE verdicts; these are terminal M12 events. Resolution of ESCALATION_RECORDED and DELEGATION_ASSIGNED outcomes is M13's responsibility. M11 acts on GOVERNANCE_ESCALATED uniformly by entering a Governance Gate pause, regardless of whether the underlying outcome is an escalation or a delegation.

**Output:** `result_code`, `verdict_set` (returned to caller)

---

### Phase 8 — Failure Handling (Cross-Cutting)

**Purpose:** Classify and handle all failure conditions encountered during the governance cycle.

See Section 14: Failure Handling.

---

### Phase 9 — Projection Update (Cross-Cutting)

**Purpose:** Maintain `governance_state.md` as a current-state projection after each write operation.

**Note (DMA-05):** `governance_state.md` is exclusively owned and written by M13 — Governance Outcome Resolution Runtime. M12 does not write to `governance_state.md`. This phase is a no-op for M12. The projection is maintained by M13 at its own invocation boundaries.

**Steps:**

9.1. No write action. Phase 9 is retained as a structural marker for L2 consistency. M12's projection write responsibility has been transferred to M13 per DMA-05.

9.2. `governance_state.md` write ordering (OR-3) continues to apply to M13's write of this artifact. M12 enforces its own write ordering: `events.md` must be updated before any downstream state projection is updated (RI-05).

---

## 4. Phase I/O Summary

| Phase | Inputs | Outputs |
|-------|--------|---------|
| 0 | Invocation arguments | session_id, session_start_timestamp, plan_source, mode |
| 1 | runtime/current_workspace.md | workspace_id, WORKSPACE_ROOT |
| 2 | WORKSPACE_ROOT | governance_dir, events.md initialized, SESSION_START written |
| 3 | events.md, policy_profile.md | active_policy_profile, prior_verdict_register, supersession_set |
| 4 | M11 Plan artifact | situation_set |
| 5 | situation_set, active_policy_profile, prior_verdict_register | preliminary_verdict_map |
| 6 | preliminary_verdict_map | verdict_set, VERDICT_PRODUCED events written |
| 7 | verdict_set | result_code, SESSION_END written |
| 8 | failure condition | failure record, appropriate result code |
| 9 | — (no-op per DMA-05) | — |

---

## 5. Decision Trees

### DT-1 — Prior Verdict Applicability

```
Given: Governing Situation S, Prior Verdict Register
  │
  ├── Is there a Prior Verdict with matching (action_class, base_id)?
  │     │
  │     ├── NO → Proceed to Policy Profile Evaluation (PE-1)
  │     │
  │     └── YES → Retrieve Verdict V
  │                 │
  │                 ├── Is V scope = INVOCATION_SCOPED?
  │                 │     └── YES → Discard (not retained across sessions)
  │                 │
  │                 ├── Is V scope = PERSISTENT?
  │                 │     └── Already filtered by RA-4.1 in Phase 3
  │                 │           → Apply RA-4 state match check
  │                 │
  │                 └── Is V scope = UNTIL_STATE_CHANGE?
  │                       └── Already filtered by RA-5.1 in Phase 3
  │                             → Apply RA-5 state change check
```

### DT-2 — Policy Rule Match

```
Given: Governing Situation S, Active Policy Profile P
  │
  ├── Does P contain a rule matching (action_class, authority_context)?
  │     │
  │     ├── YES → Apply matched rule → Produce Verdict
  │     │
  │     └── NO → Does P contain a rule matching (action_class) alone?
  │                 │
  │                 ├── YES → Apply matched rule → Produce Verdict
  │                 │
  │                 └── NO → Policy Gap Detected
  │                           → Apply GP-05 → Produce GAP Verdict
```

**Rule preconditions act as a guard on a matched rule, never as a selector.**

Field matching is unchanged: PE-1 through PE-8 select a candidate rule over `action_class`, `base_id`, `current_state`, `target_state`, `transition_type`, `authority_context`, specificity and document order. A `precondition`, where present, is then evaluated against the candidate (PE-9). If it holds, the rule applies. If it does not, **the rule does not match** and evaluation continues with the next candidate exactly as though that rule were absent.

A precondition can therefore only ever make a rule *less* applicable, never more, and never reorders anything. Adding one to an existing policy can only push matching further down the profile.

### Rule Preconditions

**Closed vocabulary.** A precondition is one of the following named predicates and nothing else. There is no expression language, no operators, no composition. An unrecognised predicate is rejected at PUBLISH time (PP-V14) and, should one reach evaluation, is treated as **not satisfied**.

| Predicate | Holds when |
|---|---|
| `prior_outcome_resolved` | The Escalation History contains, for **this same Governing Situation**, at least one entry with `closure_status = CLOSED`, `closure_path = RESOLVED` and `decision_type = APPROVED` |
| `prior_outcome_open` | The Escalation History contains at least one entry for this same Governing Situation with `closure_status = OPEN` |
| `no_prior_outcome` | The Escalation History contains no entry at all for this same Governing Situation |

**"Same Governing Situation"** means an exact match on `base_id`, `action_class` and `target_state`. A resolution recorded for one base never satisfies a precondition evaluated for another, and an approval to baseline never satisfies a precondition guarding a different target state. This is the single most important constraint in this section: a precondition that matched loosely would convert one human decision into standing authorisation for a class of transitions nobody approved.

**Policy version scope.** `prior_outcome_resolved` accepts an optional qualifier:

```text
precondition: prior_outcome_resolved                  # default — current_policy
precondition: prior_outcome_resolved(current_policy)  # explicit
precondition: prior_outcome_resolved(any_policy)
```

Under `current_policy` the prior outcome must carry the `policy_version` of the active Policy Profile. Under `any_policy` an outcome created under a superseded version also counts. The default is the conservative one, because a decision taken under one set of rules did not anticipate the next. `any_policy` is legitimate — it is exactly what is needed when a policy is amended *in order to* honour decisions already taken — but it must be written out, so that the choice is visible in the policy file rather than inherited silently.

An outcome closed by `OUTCOME_SUPERSEDED`, `DELEGATION_EXPIRED` or `OUTCOME_INVALIDATED` never satisfies `prior_outcome_resolved`. Only a terminal human decision of `APPROVED` does.

**Scope constraint.** A rule carrying a precondition must declare `verdict_scope: INVOCATION_SCOPED` (enforced by PP-V14). A conditional rule producing a retained Verdict is incoherent: the Verdict would outlive the condition that justified it, and a later invocation would be authorised by a precondition that no longer holds.

**Why this does not weaken PE-7, GP-08 or I-8G-02.**

These three invariants say that no external input may override a Policy Profile evaluation, and that M13's closure of an outcome does not itself authorise any plan step — authorisation derives exclusively from M12's Verdict Set. All three continue to hold, exactly:

- Nothing external overrides anything. The Policy Profile remains the sole authority for Verdict production. A precondition is **the policy choosing to consult recorded history**, because a human author wrote a rule saying so. Remove the rule and the history is ignored again.
- M13's closure still authorises nothing. It is evidence, not authority. The authorisation remains the APPROVED Verdict that M12 produces — the chain `M12 Verdict → plan step execution` is untouched, and I-8G-02 is satisfied on its own terms.
- An unconditional rule behaves exactly as before. A profile containing no precondition evaluates identically to how it evaluated before this capability existed.

The distinction that matters: **M13 does not reach past M12. M12 reads what M13 recorded, because the policy told it to.**

> **Implemented 2026-10-31** (recommendation R4, (internal review note)). Before this, an unconditional ESCALATE rule had no terminating path inside the governance layer: the rule re-matched identically on every re-evaluation and reproduced ESCALATE indefinitely, and the only exits were to narrow the rule by `base_id` — a permanent by-name derogation — or to decide the transition by hand forever. The enabling change is the amendment to RA-6: escalation closure status was previously declared opaque to M12.

### DT-3 — Verdict Scope Assignment

```
Given: Policy rule match result
  │
  ├── Rule specifies INVOCATION_SCOPED   → Assign INVOCATION_SCOPED
  ├── Rule specifies PERSISTENT          → Assign PERSISTENT
  ├── Rule specifies UNTIL_STATE_CHANGE  → Assign UNTIL_STATE_CHANGE
  └── Rule specifies no scope            → Default: INVOCATION_SCOPED
```

### DT-4 — Governance Cycle Result Determination

```
Given: Verdict Set
  │
  ├── Any GOVERNANCE_BLOCKED condition?                                  → GOVERNANCE_BLOCKED
  ├── Any DENY Verdict?                                                  → GOVERNANCE_DENIED
  ├── Any ESCALATE or DELEGATE Verdict?                                  → GOVERNANCE_ESCALATED
  ├── All Verdicts APPROVED / RECOVERY_ALLOWED / TERMINATION_ALLOWED?
  │     └── YES                                                          → GOVERNANCE_COMPLETE
  └── NON_RECOVERABLE failure during evaluation?                        → GOVERNANCE_FAILED
```

Precedence order: GOVERNANCE_BLOCKED > GOVERNANCE_FAILED > GOVERNANCE_DENIED > GOVERNANCE_ESCALATED > GOVERNANCE_COMPLETE.

**Note:** DELEGATE and ESCALATE verdicts both produce GOVERNANCE_ESCALATED because both create open governance outcomes (DELEGATION_ASSIGNED and ESCALATION_RECORDED respectively) requiring external resolution before M11 can proceed to execution. The semantic distinction between ESCALATE and DELEGATE is preserved at the Verdict vocabulary level and the governance event level. At the Governance Cycle Result Code level, both require M11 to enter a Governance Gate pause.

### DT-5 — Policy Supersession Handling

```
Given: POLICY_SUPERSEDED event in events.md
  │
  ├── Extract superseded policy_id from event
  │
  ├── Add policy_id to Supersession Set (Phase 3.6)
  │
  ├── For each Prior Verdict in PERSISTENT partition (Phase 3.2):
  │     └── Does verdict.policy_id == superseded policy_id?
  │           ├── YES → Discard from register (RA-4.1)
  │           └── NO  → Apply RA-4 retention check
  │
  ├── For each Prior Verdict in UNTIL_STATE_CHANGE partition (Phase 3.3):
  │     └── Does verdict.policy_id == superseded policy_id?
  │           ├── YES → Discard from register (RA-5.1)
  │           └── NO  → Apply RA-5 retention check
  │
  └── (Optional) Write VERDICT_INVALIDATED event per IV-6
```

---

## 6. Governance Event Model

### Internal Events (written to events.md by M12)

| Event | Trigger | Required Fields |
|-------|---------|-----------------|
| `GOVERNANCE_SESSION_START` | Phase 2.3 — session begins | session_id, timestamp, plan_source, mode |
| `VERDICT_PRODUCED` | Phase 6.3 — verdict finalized | verdict_id, session_id, action_class, base_id, verdict_code, verdict_scope, policy_rule_ref, policy_id, reused_from_verdict_id (if reuse), produced_at |
| `ESCALATION_RECORDED` | Phase 6.3 — ESCALATE verdict produced | verdict_id, session_id, m11_session_id, action_class, base_id, escalation_reason, policy_version, tier, timestamp |
| `DELEGATION_ASSIGNED` | Phase 6.3 — DELEGATE verdict produced | verdict_id, session_id, m11_session_id, action_class, base_id, delegate_target, policy_version, tier, timestamp |
| `GOVERNANCE_SESSION_END` | Phase 7.3 — session completes | session_id, timestamp, result_code, verdicts_produced |
| `VERDICT_INVALIDATED` | Phase 3.6 / IV-6 — supersession detected | verdict_id, invalidated_session_id, policy_id, superseded_by, invalidation_timestamp *(OPTIONAL — see IV-6)* |

**Scope note — ESCALATION_RECORDED and DELEGATION_ASSIGNED:** These are terminal M12 events for their respective outcome types. M12 records them and the governance cycle ends. M12 does not write resolution events for escalation or delegation outcomes. Resolution events for these outcomes are the responsibility of M13 — Governance Outcome Resolution Runtime. Both ESCALATION_RECORDED and DELEGATION_ASSIGNED outcomes produce GOVERNANCE_ESCALATED as the Governance Cycle Result Code per DT-4. The event type distinguishes the outcome nature (escalation vs. delegation); M13 handles them differently (EXPIRED closure path applies only to DELEGATION_ASSIGNED). At the M11 routing level, the result code is uniform.

**Field definitions for DMA-added fields:**

| Field | Applies To | Description |
|-------|------------|-------------|
| `policy_version` | ESCALATION_RECORDED, DELEGATION_ASSIGNED | The `policy_version` of the active Policy Profile at M12 evaluation time. Required by M13 for supersession detection (SUPERSEDED closure path). |
| `m11_session_id` | ESCALATION_RECORDED, DELEGATION_ASSIGNED | The M11 session identifier (SES-NNN format) from the M11 Plan that triggered this M12 evaluation. Distinct from `session_id` which is the M12 session (GS-YYYYMMDD-HHMMSS format). Required by M13 for originating session state correlation (INVALIDATED closure path). |
| `tier` | ESCALATION_RECORDED, DELEGATION_ASSIGNED | The escalation or delegation tier label as defined in the active Policy Profile rule that produced this outcome. Required by M13 for terminal authority eligibility validation (RESOLVED closure path). |

### External Events (read from events.md, produced by other components)

| Event | Source | Consumed in Phase |
|-------|--------|-------------------|
| `POLICY_SUPERSEDED` | Policy administration | Phase 3.6 — Supersession Set construction |
| `BASELINE_REQUEST` | M8/M9 lifecycle runtime | Phase 4 — authority_context derivation |
| `ARCHIVE_REQUEST` | M8/M9 lifecycle runtime | Phase 4 — authority_context derivation |
| `WORKSPACE_LIFECYCLE_EVENT` | M10 workspace runtime | Phase 3 — Governance State context |

### POLICY_SUPERSEDED Event Field Structure

When a `POLICY_SUPERSEDED` event is written by a policy administration process, it must contain:

```
event_type:    POLICY_SUPERSEDED
policy_id:     <id of the policy profile being superseded>
superseded_by: <id of the new policy profile that supersedes it>
effective_at:  <timestamp at which the supersession takes effect>
recorded_at:   <timestamp at which this event was appended to events.md>
recorded_by:   <identity of the actor or process that recorded this event>
```

M12 reads but does not write `POLICY_SUPERSEDED` events. It consumes them in Phase 3.6 to build the Supersession Set. A `POLICY_SUPERSEDED` event missing any required field is treated as malformed: M12 emits a WARNING, skips it during Supersession Set construction, and continues. A malformed supersession event does not halt the cycle.

---

## 7. Validation Rules

| Rule | Phase | Condition | Classification |
|------|-------|-----------|----------------|
| GX-01 | 4 | Every plan step must yield exactly one Governing Situation | BLOCKING |
| GX-02 | 4 | `action_class` must be a valid M11 action class value | BLOCKING |
| GX-03 | 4 | `base_id` must match a base known to the active workspace | BLOCKING |
| GX-04 | 4 | `current_state` must be a valid M11 coordination state | BLOCKING |
| GX-05 | 4 | `target_state` must be a valid M11 coordination state | BLOCKING |
| GX-06 | 4 | `transition_type` must be STANDARD, REVISION, or LIFECYCLE | BLOCKING |
| GX-07 | 5 | Each Governing Situation must produce exactly one preliminary Verdict | BLOCKING |
| GX-08 | 5 | A GAP Verdict must reference the policy gap condition (GP-05) | BLOCKING |
| GX-09 | 5 | A reused Prior Verdict must not carry a `policy_id` in the Supersession Set | BLOCKING |
| GX-10 | 5 | An INVOCATION_SCOPED Prior Verdict must not be reused across sessions | BLOCKING |
| GX-11 | 5 | A Policy Profile evaluation must not produce two Verdicts for the same Situation | BLOCKING |
| GX-12 | 5 | `authority_context` used in rule matching must match the Governing Situation value | BLOCKING |
| GX-13 | 6 | Verdict Set must contain exactly one Verdict per plan step | BLOCKING |
| GX-14 | 6 | Each Verdict must have a non-empty `verdict_id` | BLOCKING |
| GX-15 | 6 | Each Verdict must have a non-empty `policy_rule_ref` | BLOCKING |
| GX-16 | 6 | Each Verdict must have a non-empty `verdict_scope` with a valid value | BLOCKING |
| GX-17 | 6 | No Verdict in the Verdict Set may carry a `policy_id` in the Supersession Set | BLOCKING |
| GX-18 | 6 | `produced_at` timestamp must be present on every Verdict | BLOCKING |

---

## 8. Reconstruction Rules

**RA-1 — Prior Verdict Register Scope**
The Prior Verdict Register contains only Verdicts with `verdict_scope` of PERSISTENT or UNTIL_STATE_CHANGE. INVOCATION_SCOPED Verdicts are not retained across sessions.

**RA-2 — Prior Verdict Match Criteria**
A Prior Verdict is applicable to a Governing Situation S if and only if: `verdict.action_class == S.action_class` AND `verdict.base_id == S.base_id`.

**RA-3 — Prior Verdict Recency**
When multiple Prior Verdicts match the same Governing Situation, the most recently produced Verdict by `produced_at` timestamp takes precedence.

**RA-4 — PERSISTENT Verdict Retention**
A PERSISTENT Prior Verdict is carried forward if and only if it has not been invalidated by policy supersession. Apply RA-4.1 before carrying forward any PERSISTENT Verdict.

**RA-4.1 — PERSISTENT Verdict Supersession Check**
Before carrying forward a PERSISTENT Prior Verdict V: check whether `V.policy_id` appears in the Supersession Set. If `V.policy_id` is in the Supersession Set, discard V. V must not be included in the Prior Verdict Register for this cycle. V is not reusable.

**RA-5 — UNTIL_STATE_CHANGE Verdict Retention**
A UNTIL_STATE_CHANGE Prior Verdict V is carried forward if and only if: (a) `V.base_id` has not undergone a state change since `V.produced_at`; AND (b) V has not been invalidated by policy supersession. Apply RA-5.1 before applying condition (a).

**RA-5.1 — UNTIL_STATE_CHANGE Verdict Supersession Check**
Before carrying forward a UNTIL_STATE_CHANGE Prior Verdict V: check whether `V.policy_id` appears in the Supersession Set. If `V.policy_id` is in the Supersession Set, discard V. V must not be included in the Prior Verdict Register for this cycle. V is not reusable.

**RA-6 — Escalation History Reconstruction**
All `ESCALATION_RECORDED` events in `events.md` are included in the Escalation History. Escalations are never discarded during reconstruction.

Each entry additionally carries its **closure status**, derived from the same log: an escalation is `OPEN` unless a later event bearing the same `outcome_id` closes it — `RESOLUTION_RECORDED` (closure_path `RESOLVED`, carrying `decision_type` and `submitter`), `OUTCOME_SUPERSEDED`, `DELEGATION_EXPIRED` or `OUTCOME_INVALIDATED`. The entry records `closure_status`, `closure_path`, `decision_type`, `closed_at` and the `policy_version` the escalation was created under.

> **Amended 2026-10-31.** This rule previously ended "Their resolution status is managed by M13 and is opaque to M12." That opacity — not the absence of a grammar — is what made an escalation loop unclosable: M12 could not distinguish a transition nobody had decided from one the owner had approved twice. Closure status is now reconstructed. It is **read-only input to precondition evaluation** (PE-9) and is never a Verdict in itself; see "Rule Preconditions" for why this does not weaken PE-7, GP-08 or I-8G-02.
>
> Reading closure status does not make M13's decision authoritative over M12. M13 continues to own closure; M12 continues to own Verdicts. What changes is only that a human-authored policy rule may now *consult* a decision already recorded, instead of being structurally unable to see it.

**RA-7 — Delegation Assignment Reconstruction**
All active `DELEGATION_ASSIGNED` events are included. An assignment is active if no corresponding `DELEGATION_REVOKED` event has been recorded with the same `delegate_target` and `action_class`. Delegation resolution is managed by M13 and is opaque to M12.

**RA-8 — Policy Supersession Set Construction**
The Supersession Set is the set of all `policy_id` values that appear in any `POLICY_SUPERSEDED` event in `events.md`. This set is constructed during Phase 3.6 and is applied in RA-4.1, RA-5.1, and IV-1 through IV-7. The Supersession Set must be fully constructed before any retention check is performed (OR-1).

**RA-9 — Prior Verdict Register Post-Supersession Integrity**
After applying RA-1 through RA-8, the Prior Verdict Register must not contain any Verdict whose `policy_id` is in the Supersession Set.

**RA-10 — Reconstruction Source Authority**
`events.md` is the sole reconstruction source for Prior Verdicts, Escalation History, Delegation Assignments, and the Supersession Set. `governance_state.md` is never used as a reconstruction input.

**RA-11 — Reconstruction Determinism**
Given the same `events.md` content and the same Supersession Set, reconstruction must produce the same Prior Verdict Register and Escalation History on every invocation.

**RA-12 — Malformed Event Handling**
If any `VERDICT_PRODUCED` event record in `events.md` is malformed (missing required fields, unparseable timestamp), skip that record and emit a WARNING. Do not halt reconstruction. Record the skipped event IDs in the session log.

---

## 9. Invalidation Rules

**IV-1 — Invalidation Trigger**
A Prior Verdict is subject to invalidation when its `policy_id` is present in the Supersession Set (RA-8).

**IV-2 — Invalidation Scope**
Invalidation applies to all Prior Verdicts — both PERSISTENT and UNTIL_STATE_CHANGE — whose `policy_id` matches a superseded policy. INVOCATION_SCOPED Verdicts are never retained across sessions and are therefore not subject to invalidation.

**IV-3 — Invalidation Timing**
Invalidation is applied during Phase 3 — Governance State Reconstruction, at RA-4.1 (PERSISTENT partition) and RA-5.1 (UNTIL_STATE_CHANGE partition). Invalidation is not deferred to Phase 5 (OR-5).

**IV-4 — Invalidation Irreversibility**
A Verdict invalidated due to policy supersession may not be reinstated in the same or any future cycle. Erroneous supersession events are an operational concern outside the scope of this specification.

**IV-5 — Invalidation Does Not Modify the Event Log**
Invalidation removes a Verdict from the active Prior Verdict Register. It does not modify or delete the original `VERDICT_PRODUCED` event record in `events.md`. The event log remains immutable (RI-07, GP-03).

**IV-6 — VERDICT_INVALIDATED Event (Optional)**
When one or more Verdicts are invalidated during Phase 3, M12 MAY append a `VERDICT_INVALIDATED` event to `events.md` for each invalidated Verdict. This event is OPTIONAL but RECOMMENDED for observability. If written, it must appear before `GOVERNANCE_SESSION_END` (OR-4). Format:

```
event_type:             VERDICT_INVALIDATED
verdict_id:             <original verdict_id>
invalidated_session_id: <session_id in which the verdict was originally produced>
policy_id:              <policy_id of the superseded policy>
superseded_by:          <superseded_by value from the POLICY_SUPERSEDED event>
invalidation_timestamp: <timestamp of this invalidation record>
```

**IV-7 — Invalidation Does Not Constitute a Policy Gap**
Invalidation of a Prior Verdict does not itself trigger a GP-05 gap declaration. The active Policy Profile must be evaluated to produce a new Verdict for the affected Governing Situation. GP-05 applies only if no matching policy rule is found during that evaluation.

---

## 10. Ordering Rules

**OR-1 — Supersession Set Before Reconstruction**
The Supersession Set (RA-8) must be fully constructed from `events.md` before any Prior Verdict retention check (RA-4, RA-4.1, RA-5, RA-5.1) is performed. Phase 3.6 precedes Phase 3.2 and 3.3 in execution.

**OR-2 — Reconstruction Before Evaluation**
Phase 3 must complete before Phase 5 begins. No policy rule evaluation may use a Prior Verdict Register that has not been filtered by RA-4.1 and RA-5.1.

**OR-3 — Verdict Event Write Before Projection Update**
Each `VERDICT_PRODUCED` event must be appended to `events.md` before `governance_state.md` is updated (RI-05).

**OR-4 — VERDICT_INVALIDATED Before Session End**
If the optional `VERDICT_INVALIDATED` event is written (IV-6), it must be appended to `events.md` before `GOVERNANCE_SESSION_END` is written.

**OR-5 — Invalidation Filter Before Evaluation**
No Verdict from a superseded policy may be presented to Phase 5 as a candidate for Prior Verdict Reuse. The invalidation filter (RA-4.1, RA-5.1) is applied in Phase 3. Phase 5 receives only the filtered Prior Verdict Register.

---

## 11. Policy Evaluation Rules

### Policy Artifact Rules (PA-1 through PA-4)

**PA-1 — Active Policy Profile Required**
The active Policy Profile must be loaded before any Verdict is produced. If no Policy Profile is loadable, the session must emit `GOVERNANCE_BLOCKED`.

**PA-2 — Policy Profile Identity**
The active Policy Profile carries a `profile_id` and a `policy_version`. These values are recorded in every `VERDICT_PRODUCED` event as `policy_id`.

**PA-3 — Policy Profile Immutability During Cycle**
The active Policy Profile does not change during a governance cycle. If a `POLICY_SUPERSEDED` event is appended to `events.md` during cycle execution by an external process, it takes effect in the next cycle's Phase 3. It does not retroactively affect the current cycle's evaluation.

**PA-4 — Policy Profile Structure**
The Policy Profile maps Governing Situation patterns to Verdict specifications. Each rule specifies at minimum: `action_class`, optionally `authority_context`, `verdict_code`, `verdict_scope`, and `rule_id`.

### Policy Evaluation Rules (PE-1 through PE-8)

**PE-1 — Evaluation Order**
Policy rules are evaluated in the order defined in the Policy Profile. The first matching rule wins.

**PE-2 — Match Specificity**
A rule specifying both `action_class` and `authority_context` is more specific than a rule specifying `action_class` alone. More specific rules are evaluated before less specific rules, regardless of their order in the Policy Profile.

**PE-3 — Wildcard Support**
A rule may specify `action_class: ANY` to match all action classes. Wildcard rules have the lowest specificity.

**PE-4 — Gap Declaration**
If no rule matches a Governing Situation, apply GP-05: produce a GAP Verdict. The GAP Verdict code is defined by the Policy Profile's `gap_default` field. If `gap_default` is absent, the default GAP Verdict code is `ESCALATE`.

**PE-5 — Rule Reference Format**
Each Verdict produced by direct policy rule match carries `policy_rule_ref = <profile_id>/<rule_id>`.

**PE-6 — GAP Verdict Reference**
A GAP Verdict carries `policy_rule_ref = <profile_id>/GAP_DEFAULT`.

**PE-7 — No External Verdict Authority**
The active Policy Profile is the sole authority for Verdict production during Phase 5. No external system, prior conversation, or external instruction may override the Verdict produced by PE-1 through PE-4.

A rule precondition (PE-9) is not an exception to this rule and must not be read as one. A precondition is a clause of the Policy Profile itself; when it consults recorded governance history, the Policy Profile is exercising its own authority over its own matching, not deferring to an external one. No input from outside the profile can produce, change or suppress a Verdict.

**PE-8 — Scope Default**
If a matching policy rule does not specify `verdict_scope`, the Verdict scope defaults to `INVOCATION_SCOPED`.

**PE-9 — Precondition Guard**
A rule carrying a `precondition` applies only if that precondition is satisfied for the Governing Situation under evaluation. A precondition is evaluated **after** field matching and specificity resolution (PE-1 through PE-3), never as part of them: it cannot change which rule is considered first, only whether a considered rule applies.

If the precondition is not satisfied, the rule does not match and evaluation continues with the next candidate, exactly as if the rule were absent from the profile. If no further rule matches, PE-4 applies and a GAP Verdict is produced.

The recognised predicates, their evaluation semantics, the "same Governing Situation" constraint and the mandatory `INVOCATION_SCOPED` scope are defined in "Rule Preconditions" above. An unrecognised predicate is rejected at PUBLISH time (PP-V14); should one nonetheless reach evaluation, it is treated as **not satisfied** — a precondition that cannot be understood is never presumed to hold.

---

## 12. Governing Situation Derivation Rules

**GSD-1 — Plan Step is the Unit**
One Governing Situation is derived per M11 plan step. Two plan steps that are syntactically identical but occupy different positions in the plan are distinct Governing Situations.

**GSD-2 — action_class Derivation**
`action_class` is derived from the M11 plan step command. The mapping is defined in the M12 L1 Contract (Owned Concepts: action_class vocabulary).

**GSD-3 — base_id Derivation**
`base_id` is taken directly from the M11 plan step.

**GSD-4 — current_state and target_state Derivation**
`current_state` and `target_state` are taken from the M11 plan step's declared state transition.

**GSD-5 — transition_type Classification**
`transition_type` is classified as:
- STANDARD: Normal forward pipeline progression.
- REVISION: Transition involving a base in UNDER_REVISION state or a Change Event.
- LIFECYCLE: Transition involving a BASELINE_REQUEST or ARCHIVE_REQUEST event signal.

**GSD-6 — authority_context Derivation**
`authority_context` is derived from the presence or absence of lifecycle event signals in the plan step:
- If plan step carries `--event BASELINE_REQUEST`: `authority_context = BASELINE_AUTHORITY`
- If plan step carries `--event ARCHIVE_REQUEST`: `authority_context = ARCHIVE_AUTHORITY`
- Otherwise: `authority_context = STANDARD`

---

## 13. Verdict Production Rules

**VP-1 — Verdict Atomicity**
Each Verdict is an atomic, self-contained authorization decision. It carries exactly the fields defined in the L1 Verdict Structure. It is not a summary and not a conditional.

**VP-2 — One Verdict Per Situation**
Exactly one Verdict is produced per Governing Situation. No Governing Situation may receive zero Verdicts or more than one Verdict.

**VP-3 — Verdict Immutability**
Once a Verdict is written as a `VERDICT_PRODUCED` event to `events.md`, it is immutable. It may not be modified, retracted, or overwritten. This is GP-03.

**VP-4 — Prior Verdict Reuse**
When a Prior Verdict is applicable and not invalidated (per RA-4, RA-4.1, RA-5, RA-5.1), it may be reused as the Verdict for the current Governing Situation. The reused Verdict is recorded as a new `VERDICT_PRODUCED` event with:
- `verdict_id`: new identifier for this session's verdict record.
- `verdict_code`: identical to the prior verdict's `verdict_code`.
- `verdict_scope`: identical to the prior verdict's `verdict_scope` (GP-09).
- `policy_rule_ref`: the original policy rule reference from the prior verdict — format `<original_profile_id>/<original_rule_id>`. Not `PRIOR/<prior_verdict_id>`.
- `reused_from_verdict_id`: the `verdict_id` of the original Prior Verdict being reused. Required when VP-4 applies.
- `produced_at`: current session timestamp.
- `policy_id`: the `policy_id` of the original Prior Verdict. Must not be in the Supersession Set; enforced by RA-4.1 / RA-5.1 and GX-09.

**VP-5 — GAP Verdict Fields**
A GAP Verdict carries: `verdict_code` from `gap_default` (or ESCALATE if absent), `verdict_scope = INVOCATION_SCOPED`, `policy_rule_ref = <profile_id>/GAP_DEFAULT`, `policy_id = <active_profile_id>`.

**VP-6 — Verdict Code Validity**
`verdict_code` must be one of: APPROVED, REJECTED, RECOVERY_ALLOWED, TERMINATION_ALLOWED, ESCALATE, DELEGATE, DENY.

**VP-7 — Verdict Scope Validity**
`verdict_scope` must be one of: INVOCATION_SCOPED, PERSISTENT, UNTIL_STATE_CHANGE.

**VP-8 — Verdict Traceability**
Every Verdict must carry: `verdict_id`, `session_id`, `action_class`, `base_id`, `verdict_code`, `verdict_scope`, `policy_rule_ref`, `policy_id`, `produced_at`. `reused_from_verdict_id` is required when VP-4 applies; omitted otherwise.

---

## 14. Failure Handling (Phase 8)

### Failure Classification

| Classification | Description | Handling |
|----------------|-------------|----------|
| NON_RECOVERABLE | Failure prevents correct governance evaluation | Stop cycle. Emit result code. Append SESSION_END with FAILED or BLOCKED. |
| RECOVERABLE | Failure affects one step but does not prevent evaluation of remaining steps | Record failure. Continue with remaining steps. Report at completion. |

### NON_RECOVERABLE Conditions

| Condition | Result Code |
|-----------|-------------|
| `runtime/current_workspace.md` unreadable | GOVERNANCE_BLOCKED |
| `WORKSPACE_ROOT` not found | GOVERNANCE_BLOCKED |
| No active Policy Profile | GOVERNANCE_BLOCKED |
| M11 Plan artifact unreadable | GOVERNANCE_BLOCKED |
| `events.md` write failure | GOVERNANCE_FAILED |
| Workspace contamination detected | GOVERNANCE_BLOCKED |
| Invocation form unrecognizable | GOVERNANCE_BLOCKED |

### RECOVERABLE Conditions

| Condition | Handling |
|-----------|----------|
| Malformed `VERDICT_PRODUCED` event record in `events.md` | Skip record (RA-12). Warn. Continue reconstruction. |
| Single plan step Governing Situation derivation failure | Record failure for that step. Continue with remaining steps. |
| `governance_state.md` write failure | Warn. Session result not affected. Record in session log. |
| Malformed `POLICY_SUPERSEDED` event record | Skip record. Warn. Continue Supersession Set construction. |

### Failure Reporting

Every failure must be named, classified, and reported. Silent continuation after a NON_RECOVERABLE failure is prohibited (GP-06, RI-06).

---

## 15. Persistence Rules

**PR-1 — Verdict Event Write**
Each Verdict in the Verdict Set must be written as an individual `VERDICT_PRODUCED` event record to `events.md` before `GOVERNANCE_SESSION_END` is appended.

**PR-2 — Append-Only Event Log**
`events.md` is append-only. No event record may be modified or deleted after it is written. This is RI-07.

**PR-3 — Verdict Event Completeness**
A `VERDICT_PRODUCED` event record is complete only if all fields required by VP-8 are present with non-empty values.

**PR-4 — Projection Overwrite**
`governance_state.md` is a projection artifact. It is overwritten (not appended) on each Phase 9 invocation.

**PR-5 — Projection Content**
`governance_state.md` must reflect the post-update state: active Policy Profile identity, Prior Verdict Register summary (counts and scope breakdown, post-invalidation), Supersession Set summary, Escalation History summary (open and unresolved, from M12's perspective), last session result.

**PR-6 — Projection Not Authoritative**
`governance_state.md` is never used as a reconstruction input (RA-10). Its content is derived, not authoritative.

---

## 16. Completion Rules

**RD-1 — GOVERNANCE_COMPLETE**
All plan steps have received a Verdict. No Verdict is ESCALATE, DELEGATE, DENY, or REJECTED. No NON_RECOVERABLE failure occurred.

**RD-2 — GOVERNANCE_ESCALATED**
At least one Verdict is ESCALATE or DELEGATE. No NON_RECOVERABLE failure occurred. Remaining Verdicts may be any code other than DENY.

**RD-3 — GOVERNANCE_DENIED**
At least one Verdict is DENY. No NON_RECOVERABLE failure. DENIED result takes precedence over ESCALATED when both are present.

**RD-4 — GOVERNANCE_FAILED**
At least one NON_RECOVERABLE failure occurred during evaluation. No GOVERNANCE_BLOCKED condition applies.

**RD-5 — GOVERNANCE_BLOCKED**
A precondition failure or infrastructure failure prevented the governance cycle from producing any Verdicts.

### Outcome Precedence

```
GOVERNANCE_BLOCKED > GOVERNANCE_FAILED > GOVERNANCE_DENIED > GOVERNANCE_ESCALATED > GOVERNANCE_COMPLETE
```

---

## 17. Session Result Codes

**Note:** The descriptions below state the meaning of each result code as produced by M12. How the caller acts on these codes is outside the scope of this specification and is defined in the M11 Governance Integration Amendment.

| Code | Meaning as produced by M12 |
|------|----------------------------|
| `GOVERNANCE_COMPLETE` | All plan steps evaluated. No ESCALATE, DELEGATE, DENY, or REJECTED Verdicts produced. Verdict Set is fully authorized. |
| `GOVERNANCE_ESCALATED` | At least one plan step received an ESCALATE or DELEGATE Verdict. M12 has recorded ESCALATION_RECORDED or DELEGATION_ASSIGNED for each affected step. M12 does not resolve escalations or delegations. Resolution is M13's responsibility. |
| `GOVERNANCE_DENIED` | At least one plan step received a DENY Verdict. Verdict Set contains at least one DENY. |
| `GOVERNANCE_FAILED` | Governance evaluation failed due to a NON_RECOVERABLE error during evaluation. Verdict Set may be incomplete. |
| `GOVERNANCE_BLOCKED` | Governance cycle could not start or complete due to a precondition or infrastructure failure. No Verdicts produced. |

---

## 18. Runtime Invariants

**RI-01 — Reconstruction-First**
Phase 3 must complete before any Verdict is produced. No Verdict may be produced from a non-reconstructed state. GP-01.

**RI-02 — One Verdict Per Situation**
Exactly one Verdict per Governing Situation. GP-02.

**RI-03 — Verdict Immutability**
No Verdict event record may be modified after it is written. GP-03.

**RI-04 — Mandatory Traceability**
Every Verdict must carry `policy_rule_ref` and `policy_id`. No Verdict without traceability may be included in the Verdict Set. GP-04.

**RI-05 — Write Ordering**
`events.md` must be updated before `governance_state.md` is overwritten. GP-07, OR-3.

**RI-06 — Non-Execution**
M12 does not invoke M1—M10 commands. M12 does not execute pipeline actions. M12 does not invoke M11. M12 evaluates and produces Verdicts only. GP-06.

**RI-07 — Append-Only Event Log**
`events.md` is append-only. No existing event record may be modified or deleted.

**RI-08 — Evaluation-Only Scope**
M12 produces Verdicts. M12 does not resolve ESCALATE or DELEGATE outcomes. When M12 produces an ESCALATE Verdict, it records ESCALATION_RECORDED and the governance cycle ends at that verdict. When M12 produces a DELEGATE Verdict, it records DELEGATION_ASSIGNED and the governance cycle ends at that verdict. Resolution of these outcomes is the responsibility of M13 — Governance Outcome Resolution Runtime, which is outside the scope of this specification.

---

## 19. Traceability Requirements

**TR-1 — Verdict-to-Policy Traceability**
Every Verdict must be traceable to a specific policy rule via `policy_rule_ref` (format: `<profile_id>/<rule_id>`).

**TR-2 — Verdict-to-Session Traceability**
Every Verdict must carry `session_id` linking it to the governance cycle that produced it.

**TR-3 — Verdict-to-Situation Traceability**
Every Verdict must carry `action_class` and `base_id` identifying the Governing Situation it addresses.

**TR-4 — Session-to-Plan Traceability**
Every `GOVERNANCE_SESSION_START` event must carry `plan_source` identifying the M11 Plan that triggered the governance cycle.

**TR-5 — Prior Verdict Reuse Traceability**
When a Prior Verdict is reused (VP-4), the new `VERDICT_PRODUCED` event must carry `reused_from_verdict_id` referencing the original Verdict, enabling full lineage reconstruction.

**TR-SUPERS-1 — Supersession Event Traceability**
Every `POLICY_SUPERSEDED` event must carry `policy_id`, `superseded_by`, `effective_at`, `recorded_at`, and `recorded_by`. A `POLICY_SUPERSEDED` event missing any required field is treated as malformed and is skipped with a WARNING during Supersession Set construction.

**TR-SUPERS-2 — Invalidation Traceability**
For each Verdict invalidated during Phase 3, a record of the invalidation must be retained in the session log, whether or not the optional `VERDICT_INVALIDATED` event (IV-6) is written. The session log must identify: `verdict_id`, `policy_id` of the superseded policy, and the session in which invalidation occurred.

**TR-SUPERS-3 — Prior Verdict Register Auditability**
The Prior Verdict Register as used in Phase 5 must be fully derivable from `events.md` by applying RA-1 through RA-12 and IV-1 through IV-7. No Verdict in the Register may carry a `policy_id` in the Supersession Set (RA-9). An independent reconstruction from `events.md` must yield an identical Register.

**TR-SUPERS-4 — Supersession Set Completeness**
The Supersession Set used across Phases 3 through 5 must reflect all valid `POLICY_SUPERSEDED` events recorded in `events.md` at the time of Phase 3 execution. No superseded `policy_id` may be absent from the Supersession Set due to a skipped well-formed event.

**TR-SUPERS-5 — GP-08 Reconciliation: Reuse Policy Lineage**
Any Verdict reused via VP-4 must carry the `policy_id` of the original producing policy. If that `policy_id` is found in the Supersession Set during Phase 5 (e.g., due to a concurrent `POLICY_SUPERSEDED` event recorded between Phase 3 and Phase 5 of the same cycle), the reuse is invalidated and the Governing Situation must be re-evaluated via Policy Profile Evaluation before Phase 6 proceeds. This rule ensures GP-08 holds throughout the full cycle.

---

## 20. GP-08 Reconciliation

### Formal Reconciliation: Prior Verdict Reuse and GP-08

**GP-08 Statement (from L1 Contract):**
*The active Policy Profile is the sole authority for Verdict production. No Verdict is authoritative unless it is produced or sanctioned by the current active Policy Profile.*

**Apparent Tension:**
Prior Verdict Reuse (VP-4) permits a Verdict produced in a prior session, under a prior Policy Profile, to be carried forward as the current cycle's Verdict. This appears to allow a non-current Policy Profile to exercise Verdict authority in the current cycle.

**Resolution:**

Prior Verdict Reuse is not a bypass of GP-08. It is a persistence mechanism whose validity is conditioned on the continued authority of the producing policy. The active Policy Profile sanctions reuse implicitly through its structural design: rules that specify PERSISTENT or UNTIL_STATE_CHANGE scope authorize authorization continuity across session boundaries.

This sanction is bounded by policy continuity. The active Policy Profile does not sanction Verdicts produced under a superseded policy. A superseded policy is no longer the active policy. Its authorizations have lapsed. Verdicts it produced remain in `events.md` as immutable historical records — they are not deleted (IV-5, GP-03) — but they are not active authorizations under the current governance regime.

**GP-08 Reconciliation Statement:**

*A Prior Verdict is an active authorization only while the policy that produced it remains the active policy. When a policy is superseded, its authorizations lapse. Superseded-policy Verdicts retained in `events.md` are historical records, not active authorizations. They are excluded from the Prior Verdict Register by RA-4.1 and RA-5.1. This exclusion is not a violation of GP-03 (Verdict Immutability) — the event record is preserved unchanged. It is an application of GP-08: the active Policy Profile governs, and a superseded policy no longer governs.*

*The active Policy Profile exercises its GP-08 authority in two modes: direct evaluation (producing new Verdicts via PE-1 through PE-8) and sanction of continuity (permitting Prior Verdict Reuse for Verdicts produced under still-active policies). Both modes are expressions of GP-08. Superseded-policy Verdicts fall outside both modes: they were not produced under the active Policy Profile, and the active Policy Profile does not sanction their reuse. They must not appear in the Verdict Set.*

---

## References

```
docs/commands/governance-run.md              — Layer 1 Contract (GP-01—GP-10, Verdict vocabulary, event model)
docs/runtime_engineering_method.md           — CSR engineering method and four-layer architecture
docs/implementation_status.md               — current runtime version and milestone completion status
docs/decisions/ADR-001-csr-language-policy.md — language policy (canonical artifacts English; interaction surface in the user's language)
```

---

## Applied Amendments

| Amendment | Description | Applied |
|-----------|-------------|---------|
| DMA-01 | Added `policy_version` field to ESCALATION_RECORDED and DELEGATION_ASSIGNED events. Required for M13 supersession detection. | Yes |
| DMA-02 | Added `m11_session_id` field to ESCALATION_RECORDED and DELEGATION_ASSIGNED events. Required for M13 session invalidation detection. | Yes |
| DMA-03 | Added `tier` field to ESCALATION_RECORDED and DELEGATION_ASSIGNED events. Required for M13 terminal authority validation. | Yes |
| DMA-05 | M12 does not write to `governance_state.md`. Phase 9 amended to no-op. `governance_state.md` exclusively owned by M13. | Yes |
