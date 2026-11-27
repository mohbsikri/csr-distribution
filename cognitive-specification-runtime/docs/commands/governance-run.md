# Governance Runtime — Layer 1 Contract

**Milestone:** M12
**Version:** 1.0
**Status:** VALIDATED
**Effective Date:** 2026-06-13
**File:** `docs/commands/governance-run.md`

---

## Purpose

The Governance Runtime determines whether coordination actions proposed by M11 are authorized to proceed under the active policy set.

M12 replaces mandatory per-action human authorization with deterministic policy-driven governance decisions.

M12 does not coordinate.

M12 does not plan.

M12 does not execute.

M12 governs.

---

## Responsibility

M12 is exclusively responsible for:

1. **Governance State Reconstruction**
2. **Governing Situation Derivation**
3. **Policy Evaluation**
4. **Verdict Persistence**
5. **Verdict Set Assembly**

M12 is not responsible for:

- Coordination decision-making (M11)
- Plan generation (M11)
- Capability assessment (M11)
- Plan execution (M11)
- User interaction of any kind
- Business artifact modification (M1—M10)
- M11 artifact modification (`pipeline_state.md`, `events.md`)
- Policy Profile authoring or modification (M13)
- Escalation resolution (human authority or M13)

---

## Inputs

### External Input

| Input | Source | Required |
|-------|--------|----------|
| M11 Plan | M11 Phase 8 — Plan Generation | REQUIRED |

The M11 Plan is an ordered sequence of plan steps. Each plan step carries:

| Field | Description |
|-------|-------------|
| `command` | M1 through M10 command to invoke |
| `base_id` | Coordination base the action applies to |
| `step_type` | AUTO or INTERACTIVE |
| `current_state` | Base coordination state at time of plan generation |
| `target_state` | Intended coordination state after the action completes |

If the M11 Plan is absent, unparseable, or contains zero steps, M12 reports GOVERNANCE_BLOCKED and stops.

### Internal Inputs — Reconstructed by M12

The following are never supplied by M11. M12 reconstructs all of them from governance artifacts.

| Input | Authoritative Source | Required |
|-------|---------------------|----------|
| Active Policy Profile | `WORKSPACE_ROOT/runtime/governance/policies/` | REQUIRED — at least one active profile must exist |
| Prior Verdicts | `WORKSPACE_ROOT/runtime/governance/events.md` | Required if log exists; absent log treated as empty history |
| Escalation History | `WORKSPACE_ROOT/runtime/governance/events.md` | Required if log exists |
| Delegation Assignments | `WORKSPACE_ROOT/runtime/governance/events.md` | Required if log exists |

---

## Outputs

### External Output

| Output | Description |
|--------|-------------|
| Governance Verdict Set | The complete set of Governance Verdicts produced for the M11 Plan |

The Governance Verdict Set contains one Governance Verdict per Governing Situation derived from the M11 Plan. M11 consumes this set to determine which plan steps are authorized to proceed.

### Persisted Outputs

| Artifact | Path | Write Mode |
|----------|------|------------|
| Governance event log | `WORKSPACE_ROOT/runtime/governance/events.md` | Append-only |

No other repository paths are written by M12.

### Governance Verdict Structure

Every Governance Verdict is a structured record:

| Field | Required | Description |
|-------|----------|-------------|
| `verdict_id` | REQUIRED | Unique identifier for this Verdict record |
| `situation_ref` | REQUIRED | Reference to the Governing Situation evaluated |
| `code` | REQUIRED | Authorization decision code — see Verdict Vocabulary |
| `policy_rule_ref` | REQUIRED | Identifier of the Policy Profile rule that produced this code |
| `scope` | REQUIRED | Authorization validity boundary — see Verdict Scope Values |
| `parameters` | CONDITIONAL | Empty for APPROVED, REJECTED, RECOVERY_ALLOWED, TERMINATION_ALLOWED, DENY. Required for ESCALATE (`authority`) and DELEGATE (`delegate_target`). |
| `produced_at` | REQUIRED | Timestamp of evaluation |

A Governance Verdict without `policy_rule_ref` is invalid. A Governance Verdict may not be modified after it is appended to `events.md`.

### Verdict Vocabulary

| Code | Meaning |
|------|---------|
| `APPROVED` | The proposed action is authorized to proceed without restriction under the active Policy Profile. |
| `REJECTED` | The proposed action is not authorized. M11 must not execute this plan step. |
| `RECOVERY_ALLOWED` | A recovery action is authorized following a classified RECOVERABLE failure. The recovery scope is declared in `parameters`. |
| `TERMINATION_ALLOWED` | Plan termination is authorized. |
| `ESCALATE` | The Governing Situation falls outside M12's policy scope. Human decision is required. `parameters.authority` must identify the escalation target. |
| `DELEGATE` | Authorization is assigned to a named authority. `parameters.delegate_target` must identify the delegation target. |
| `DENY` | No applicable policy rule covers this Governing Situation. Policy gap. M12 has no authorization position on this action. |

### Verdict Scope Values

| Value | Meaning |
|-------|---------|
| `INVOCATION_SCOPED` | Verdict applies only to the current M11 invocation. |
| `PERSISTENT` | Verdict remains active until explicitly superseded by a subsequent Verdict or policy change. |
| `UNTIL_STATE_CHANGE` | Verdict expires when the base transitions to a new coordination state. |

---

## Internal Runtime Dependencies

### Policy Profile

The Policy Profile is the transformation function applied internally to each Governing Situation:

```
Profile(Situation, Context) → Governance Verdict
```

A valid Policy Profile satisfies two properties:

- **Complete** — it covers every Governing Situation that may be derived from a valid M11 Plan. A Situation not covered by any rule produces a DENY Verdict, not an error.
- **Consistent** — it produces exactly one Verdict code per Governing Situation input.

Policy authoring is M13's responsibility. M12 reads and applies. M12 does not author, modify, or override Policy Profiles.

### Governing Situation

A Governing Situation is an internal projection produced from each M11 plan step. It is the input unit of Policy Profile evaluation. It is not persisted. It is not exposed externally.

A Governing Situation is composed of two layers.

**Situation** — observable properties derived from the M11 plan step:

| Field | Description |
|-------|-------------|
| `action_class` | The M1—M10 command being proposed |
| `base_id` | The coordination base the action applies to |
| `current_state` | The base's current coordination state |
| `target_state` | The intended coordination state after the action |

**Context** — governance classifications derived by M12:

| Field | Governance Dimension |
|-------|---------------------|
| `transition_type` | Lifecycle, Failure |
| `authority_context` | Authority |

The Context layer requires governance knowledge that belongs exclusively in M12. M11 does not classify `transition_type` or `authority_context`.

### Governance Dimensions

M12 evaluates Governing Situations across three governance dimensions. These dimensions are non-exclusive.

| Dimension | Character | Concern |
|-----------|-----------|---------|
| **Authority** | Enabling | What is within M12's authorization scope for this Governing Situation |
| **Failure** | Directing | What recovery or termination actions are sanctioned |
| **Lifecycle** | Directing + Consequential | What coordination lifecycle transitions are sanctioned, and what governance consequences they carry |

### Governance State

Governance State is the complete set of governance-relevant facts M12 reconstructs from its artifacts before each governance cycle. It contains:

- Active Policy Profile
- Prior Verdicts with PERSISTENT or UNTIL_STATE_CHANGE scope, still active
- Escalation History — unresolved escalations from prior cycles
- Delegation Assignments — active delegation records

`governance_state.md` is a reconstructable projection of Governance State. It is never used as authoritative input to Governance State reconstruction.

---

## Runtime Principles

**GP-01 — Reconstruction-First**
M12 never reads `governance_state.md` as authoritative input to Governance State reconstruction. `governance_state.md` is exclusively owned by M13. M12 reconstructs Governance State from `events.md` only.

**GP-02 — One Situation, One Verdict**
Each Governing Situation derived from the M11 Plan produces exactly one Governance Verdict. No Governing Situation is evaluated more than once per governance cycle. No Verdict is produced without a corresponding Governing Situation.

**GP-03 — Verdict Immutability**
Every Governance Verdict is immutable after it is appended to `events.md`. No existing Verdict record may be modified.

**GP-04 — Mandatory Traceability**
Every Governance Verdict must carry a `policy_rule_ref` identifying the Policy Profile rule that produced it. A Verdict without `policy_rule_ref` is invalid and must not be returned to M11.

**GP-05 — Policy-Gap Declaration**
When no applicable policy rule covers a Governing Situation, M12 produces a DENY Verdict. M12 never produces an authorization decision based on its own judgment outside the Policy Profile.

**GP-06 — Non-Execution**
M12 never invokes M1—M10 commands. M12 never modifies M1—M10 artifacts. M12 never modifies M11 artifacts.

**GP-07 — Write Ordering**
The VERDICT_PRODUCED event must be appended to `events.md` before any downstream state projection is updated. This ordering is unconditional and has no exceptions.

**GP-08 — Policy Profile Authority**
The active Policy Profile is the sole authority for Verdict production. No M11 state, no external input, and no prior Verdict may override a Policy Profile evaluation outcome.

**GP-09 — Scope Preservation**
A PERSISTENT Verdict remains active across governance cycles until explicitly superseded by a new Verdict on the same Governing Situation or by a policy change event.

**GP-10 — Execution Authorization Dependency**
M11 may not execute a plan step until the corresponding Governance Verdict has been obtained from M12. M12 never executes plan steps. M12 authorizes, denies, delegates, escalates, or sanctions execution through Governance Verdicts. Execution remains exclusively owned by M11.

---

## Runtime Boundaries

### M12 Owns

| Artifact | Path | Write Mode |
|----------|------|------------|
| Governance event log | `WORKSPACE_ROOT/runtime/governance/events.md` | Append-only |
| Policy records directory | `WORKSPACE_ROOT/runtime/governance/policies/` | Read-only (authored by M13) |

M12 writes exactly one file. Any write to a path outside `events.md` is a workspace contamination violation. If such a write is about to occur: stop immediately. Report the violating path. Terminate the governance cycle with GOVERNANCE_FAILED.

### M12 Does Not Own

| Artifact | Owner | M12 Access |
|----------|-------|------------|
| `WORKSPACE_ROOT/runtime/pipeline/pipeline_state.md` | M11 | Read-only |
| `WORKSPACE_ROOT/runtime/pipeline/events.md` | M11 | Not required |
| All `knowledge_base/`, `specifications/`, `input/` artifacts | M1—M10 | Not required |
| Policy authoring artifacts | M13 | Read-only |

---

## Governance Event Model

M12 appends all governance events to `events.md`. The log is append-only and immutable.

### Internal Events

| Event | Trigger |
|-------|---------|
| `GOVERNANCE_SESSION_START` | Governance cycle begins; M11 Plan received |
| `VERDICT_PRODUCED` | One Governance Verdict produced for one Governing Situation |
| `ESCALATION_RECORDED` | ESCALATE Verdict produced; human decision required |
| `GOVERNANCE_SESSION_END` | Governance cycle completes or aborts; `result_code` carries the outcome (`GOVERNANCE_COMPLETE`, `GOVERNANCE_ESCALATED`, `GOVERNANCE_DENIED`, `FAILED`, `BLOCKED`) |

**Corrected 2026-11-01 `[C4 finding]`.** This table previously named three events the execution specification has never written under those names, found by checking L1 against L2 rather than trusting the table: `ESCALATION_RAISED` (the real event is `ESCALATION_RECORDED` — written since this runtime's first governance cycle, and the name every real `events.md` in this repository actually carries), `POLICY_GAP_DETECTED` (a GAP Verdict is recorded as an ordinary `VERDICT_PRODUCED` event with `verdict_code: GAP`, not a distinct event type), and `GOVERNANCE_SESSION_FAILED` (failure is a `result_code` value — `FAILED` or `BLOCKED` — on the same `GOVERNANCE_SESSION_END` event every cycle writes, not a separate event type). A reader who searched a real event log for any of the three original names would have found nothing, because the mechanism never produced them.

### External Events

| Event | Producer | Meaning |
|-------|----------|---------|
| `POLICY_ACTIVATED` | M13 | A Policy Profile has been activated |
| `POLICY_SUPERSEDED` | M13 | A Policy Profile has been superseded |
| `ESCALATION_RESOLVED` | Human authority / M13 | A raised escalation has been resolved |
| `DELEGATION_ASSIGNED` | M13 | An authority delegation has been recorded and is active |

External events are written by their producers directly to `events.md`. M12 reads but does not author external events.

---

## Owned Concepts

| Concept | Definition |
|---------|------------|
| **Governance Verdict** | An authoritative, immutable, policy-derived authorization decision for one Governing Situation |
| **Governance Verdict Set** | The complete set of Governance Verdicts produced for one M11 Plan in one governance cycle |
| **Verdict Vocabulary** | The seven Verdict codes: APPROVED, REJECTED, RECOVERY_ALLOWED, TERMINATION_ALLOWED, ESCALATE, DELEGATE, DENY |
| **Verdict Scope** | The validity boundary of a Governance Verdict: INVOCATION_SCOPED, PERSISTENT, UNTIL_STATE_CHANGE |
| **Governing Situation** | The internal projection of an M11 plan step through M12's governance lens; not persisted; not exposed externally |
| **Situation** | The observable layer of a Governing Situation: action_class, base_id, current_state, target_state |
| **Context** | The classified layer of a Governing Situation: transition_type, authority_context |
| **Transition Type** | Governance classification of a proposed coordination action's character; values defined in Layer 2 |
| **Authority Context** | Governance classification of the authority conditions under which a proposed action occurs; values defined in Layer 2 |
| **Policy Profile** | The structured rule set defining the transformation Profile(Situation, Context) → Governance Verdict |
| **Governance State** | The complete reconstructed governance context: active Policy Profile, Prior Verdicts, Escalation History, Delegation Assignments |
| **Governance Cycle** | One complete evaluation sequence from M11 Plan receipt to Verdict Set return |
| **Governance Dimension** | A non-exclusive analytical lens for Policy Profile evaluation: Authority, Failure, Lifecycle |
| **Policy Gap** | The condition in which no applicable policy rule covers a Governing Situation |
| **Governance Cycle Result Code** | The terminal classification of a governance cycle: GOVERNANCE_COMPLETE, GOVERNANCE_ESCALATED, GOVERNANCE_DENIED, GOVERNANCE_FAILED, GOVERNANCE_BLOCKED |

---

## Non-Owned Concepts

| Concept | Owner | M12 Relationship |
|---------|-------|-----------------|
| **Plan** | M11 | External input to M12; read-only |
| **Plan Step** | M11 | Source of observable Situation fields; not modified |
| **Coordination State** | M11 | Read as `current_state` in Governing Situation derivation |
| **Capability Assessment** | M11 | Determines which steps enter the plan; not re-evaluated by M12 |
| **Coordination Goal** | M11 | Not referenced in M12 evaluation |
| **Change Event** | M11 | Read as input to Context classification; not authored by M12 |
| **Revision Rule** | M11 | M11 invariant; M12 may govern the resulting transition but may not cancel or bypass the rule |
| **Confirmation Gate** | M11 | M12 replaces its human authorization function; M12 does not own the gate |
| **Interactive Breakpoint** | M11 | Produces INTERACTIVE plan steps that M12 classifies as governance-relevant |
| **Business Artifacts** | M1—M10 | Not accessible to M12 |
| **Policy Authoring** | M13 | M13 creates, modifies, and supersedes Policy Profile records; M12 reads only |
| **Escalation Resolution** | Human authority / M13 | M12 raises escalations; resolution is external |

---

## Completion Criteria

A governance cycle is complete when all of the following are true:

1. The Governance Verdict Set has been returned to M11.
2. A GOVERNANCE_SESSION_END event has been appended to `events.md`.

### Governance Cycle Result Codes

| Code | Meaning |
|------|---------|
| `GOVERNANCE_COMPLETE` | All Verdicts produced and returned. No ESCALATE, DELEGATE, or DENY Verdicts present. All Verdicts are APPROVED, RECOVERY_ALLOWED, or TERMINATION_ALLOWED. M11 may proceed to plan execution. |
| `GOVERNANCE_ESCALATED` | All Verdicts produced. At least one ESCALATE or DELEGATE Verdict is present. M11 must pause at each affected plan step and await M13 resolution before proceeding. |
| `GOVERNANCE_DENIED` | All Verdicts produced. At least one DENY Verdict is present. Affected plan steps cannot proceed until policy coverage is established. |
| `GOVERNANCE_FAILED` | Governance cycle could not complete. Verdict Set not returned. M11 must not proceed. |
| `GOVERNANCE_BLOCKED` | Precondition failure prevented the governance cycle from starting. No Verdicts produced. M11 must not proceed. |

GOVERNANCE_COMPLETE, GOVERNANCE_ESCALATED, and GOVERNANCE_DENIED are valid cycle completions. The Verdict Set is returned in all three cases. GOVERNANCE_FAILED and GOVERNANCE_BLOCKED are non-completions. The Verdict Set is not returned.

---

## Failure Conditions

| Condition | Classification | Cycle Result |
|-----------|----------------|--------------|
| Governance event log present but unreadable | NON_RECOVERABLE | GOVERNANCE_BLOCKED |
| No active Policy Profile found | NON_RECOVERABLE | GOVERNANCE_BLOCKED |
| M11 Plan absent or unparseable | NON_RECOVERABLE | GOVERNANCE_BLOCKED |
| M11 Plan contains zero steps | NON_RECOVERABLE | GOVERNANCE_BLOCKED |
| Governing Situation derivation fails for one step | RECOVERABLE | GOVERNANCE_DENIED |
| Policy Profile incomplete — Situation not covered by any rule | RECOVERABLE | GOVERNANCE_DENIED |
| Policy Profile inconsistent — conflicting Verdicts for the same Governing Situation | RECOVERABLE | GOVERNANCE_ESCALATED |
| VERDICT_PRODUCED write failure | NON_RECOVERABLE | GOVERNANCE_FAILED |
| Workspace contamination violation | NON_RECOVERABLE | GOVERNANCE_FAILED |

No failure condition may be silently absorbed. Every failure must be named and reported.

---

## Non-Goals

M12 does not:

1. **Generate coordination plans.** Plan generation is M11's responsibility.
2. **Execute coordination actions.** Execution is M11's responsibility.
3. **Interact with users.** All user interaction is M11's responsibility.
4. **Author Policy Profiles.** Policy authoring is M13's responsibility.
5. **Modify business artifacts.** M1—M10 artifacts are not accessible to M12.
6. **Modify M11 artifacts.** `pipeline_state.md` and `events.md` are M11-owned and inaccessible to M12.
7. **Resolve policy conflicts.** Conflicting policy rules are an M13 concern. M12 produces ESCALATE when conflict resolution is outside its scope.
8. **Override the Revision Rule.** The Revision Rule is an M11 invariant. M12 may govern the resulting transition but may not cancel or bypass it.

---

## Irreducible Definition

M12 governs whether M11's coordination actions proceed, replacing per-action human authorization with policy-driven sanction.

---

## Applied Amendments

| Amendment | Description | Applied |
|-----------|-------------|---------|
| DMA-05 | M12 does not write to `governance_state.md`. M12 writes `events.md` only. `governance_state.md` is exclusively owned and written by M13. | Yes |
