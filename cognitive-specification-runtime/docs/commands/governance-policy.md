# Governance Policy Administration — Layer 1 Contract

**Milestone:** M14
**Version:** 1.0
**Status:** VALIDATED
**Effective Date:** 2026-06-19
**File:** `docs/commands/governance-policy.md`

---

## Purpose

The Governance Policy Administration Runtime manages the lifecycle of Policy Profiles that govern the M12 Governance Evaluation Runtime.

M14 is the authoritative source for creating, versioning, activating, and superseding Policy Profiles. It produces the governance events (`POLICY_ACTIVATED`, `POLICY_SUPERSEDED`) that M12 consumes to reconstruct governance state and apply policy supersession invalidation rules (RA-4.1, RA-5.1).

M14 administers policies. M12 evaluates against them. M13 resolves escalation outcomes produced by M12.

---

## Responsibility

M14 is exclusively responsible for:

1. **Policy Profile Authoring** — accepting and validating a Policy Profile definition
2. **Policy File Persistence** — writing validated profiles to `WORKSPACE_ROOT/runtime/governance/policies/`
3. **Policy Activation** — writing `POLICY_ACTIVATED` events and updating the active policy registration
4. **Policy Supersession** — writing `POLICY_SUPERSEDED` events when an active policy is replaced
5. **Policy Inspection** — read-only views of active and historical policies

M14 is not responsible for:

- Governance evaluation against plan steps (M12)
- Verdict production (M12)
- Escalation resolution (M13)
- Delegation assignment handling (M13)
- Pipeline coordination (M11)
- Workspace artifact modification (M1–M10)

---

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Policy Profile definition | Human actor (inline or file reference) | REQUIRED for PUBLISH |
| `authored_by` identity | Human actor | REQUIRED for PUBLISH |
| Active policy registration | `WORKSPACE_ROOT/runtime/governance/policy_profile.md` | Read on STATUS, INSPECT, PUBLISH |
| Governance event log | `WORKSPACE_ROOT/runtime/governance/events.md` | Read on STATUS |

---

## Outputs

### Persisted Outputs

| Artifact | Path | Write Mode | Operations |
|----------|------|-----------|------------|
| Policy Profile file | `WORKSPACE_ROOT/runtime/governance/policies/<profile_id>.md` | Write (new file) | PUBLISH |
| Active policy registration | `WORKSPACE_ROOT/runtime/governance/policy_profile.md` | Write or update | PUBLISH |
| Governance event log | `WORKSPACE_ROOT/runtime/governance/events.md` | Append-only | PUBLISH |

The governance event log is shared across M12, M13, and M14. M14 appends only `POLICY_ACTIVATED` and `POLICY_SUPERSEDED` events. M14 must never modify or delete existing event records.

### External Output

| Output | Description |
|--------|-------------|
| Activation confirmation | Policy profile_id, version, effective_at, path, event summary |
| Status report | Active policy summary and version history |
| Inspection report | Full content of the requested policy version |

---

## Operations

### PUBLISH

Creates and activates a new Policy Profile. PUBLISH is atomic: a policy is either fully activated or not activated at all.

**If no active policy exists (first activation):**
- Write new policy file
- Create active policy registration
- Append `POLICY_ACTIVATED` event to `events.md`

**If an active policy exists (supersession):**
- Human confirmation required before any write
- Write new policy file
- Update old policy file: `status → SUPERSEDED`
- Update active policy registration to new policy
- Append `POLICY_SUPERSEDED` event (referencing the superseded policy) to `events.md`
- Append `POLICY_ACTIVATED` event (referencing the new policy) to `events.md`

PUBLISH requires explicit human authorization. No policy becomes active without a human confirmation step.

### STATUS

Read-only. Displays:
- Active Policy Profile summary (profile_id, policy_version, effective_at, rule count, gap_default)
- Version history table from the active policy registration

### INSPECT `[<profile_id>]`

Read-only. Displays the full content of a specific policy version.

If `<profile_id>` is omitted: displays the active policy.

---

## Policy Profile Schema

A valid Policy Profile must conform to the following structure:

```
# Policy Profile — <profile_id>

profile_id:      <unique identifier, e.g. policy_v1>
policy_version:  <version label, e.g. v1>
status:          ACTIVE
effective_at:    <ISO 8601 timestamp>
authored_by:     <identity of the human actor who authorized this policy>
supersedes:      <profile_id of the superseded policy>  ← conditional, omit on first activation

---

## Gap Default

gap_default: <APPROVED | ESCALATE | DELEGATE | DENY>

---

## Rules

### <rule_id>

rule_id:        <identifier, e.g. PP-01>
action_class:   <pipeline-run | ...>
base_id:        <base identifier or * for wildcard>
current_state:  <coordination state or *>
target_state:   <coordination state or *>
verdict_code:   <APPROVED | ESCALATE | DELEGATE | REJECTED | DENY>
verdict_scope:  <INVOCATION_SCOPED | UNTIL_STATE_CHANGE | PERSISTENT>
parameters:     <additional parameters — required for ESCALATE and DELEGATE>
  authority:    <authority identifier>  ← required for ESCALATE
  delegate_target: <delegate identifier>  ← required for DELEGATE
tier:           <tier identifier>  ← required for ESCALATE and DELEGATE
precondition:   <named predicate — optional; closed vocabulary, see PP-V14>
description:    <human-readable rule description>

---

## Terminal Authority Sets

### tier: <tier_name>

terminal_authority:
  - <authority_1>
  - <authority_2>

---

## Response Intervals  ← conditional; required if DELEGATE rules are present

tier: <tier_name>
response_interval: <interval, e.g. 72h>
```

---

## Policy Profile Validation Rules

| Rule | Check | Class |
|------|-------|-------|
| PP-V1 | `profile_id` present and non-empty | BLOCKING |
| PP-V2 | `policy_version` present and non-empty | BLOCKING |
| PP-V3 | `status: ACTIVE` present | BLOCKING |
| PP-V4 | `effective_at` present and parseable as ISO 8601 | BLOCKING |
| PP-V5 | `authored_by` present and non-empty | BLOCKING |
| PP-V6 | `## Gap Default` section present with `gap_default` set to a recognized verdict code | BLOCKING |
| PP-V7 | `## Rules` section present with at least one rule | BLOCKING |
| PP-V8 | Each rule has `rule_id`, `verdict_code`, `verdict_scope` (non-empty) | BLOCKING |
| PP-V9 | ESCALATE rules carry `authority` and `tier` in `parameters` | BLOCKING |
| PP-V10 | DELEGATE rules carry `delegate_target` and `tier` in `parameters` | BLOCKING |
| PP-V11 | `## Terminal Authority Sets` section present if any ESCALATE or DELEGATE rule exists | BLOCKING |
| PP-V12 | If SUPERSESSION: `supersedes` field present and matches the current active `profile_id` | BLOCKING |
| PP-V13 | `profile_id` of new policy does not already exist in `policies/` directory | BLOCKING |
| PP-V14 | Any `precondition` is a recognised predicate, and its rule is `INVOCATION_SCOPED` | BLOCKING |

### PP-V14 — Precondition well-formedness

A rule may carry a `precondition`. The vocabulary is **closed**: there is no expression language, no operators and no composition. Exactly three predicates are recognised, defined in `docs/commands/governance-run_execution.md` § Rule Preconditions:

| Predicate | Holds when |
|---|---|
| `prior_outcome_resolved` | This same Governing Situation was already escalated and closed by a terminal human decision of APPROVED |
| `prior_outcome_open` | This same Governing Situation currently carries an open outcome |
| `no_prior_outcome` | No outcome has ever been recorded for this Governing Situation |

`prior_outcome_resolved` accepts an optional qualifier — `prior_outcome_resolved(current_policy)`, the default, or `prior_outcome_resolved(any_policy)` to honour decisions taken under a superseded profile.

PP-V14 fails, BLOCKING, when:

1. a `precondition` names anything outside this vocabulary — including a plausible-looking phrase such as `prior_escalation_outcome_closed`, which is **not** a recognised predicate; or
2. a rule carrying a `precondition` does not declare `verdict_scope: INVOCATION_SCOPED`.

**Why the scope constraint.** A conditional rule producing a retained Verdict is incoherent: the Verdict would outlive the condition that justified it, and a later invocation would be authorised by a precondition that no longer holds. A precondition must be re-evaluated on every cycle, which is what `INVOCATION_SCOPED` means.

**What a precondition is for.** It closes an escalation loop honestly. An unconditional ESCALATE rule has no terminating path: it re-matches on every re-evaluation, and M13's closure of the outcome authorises nothing by itself (PE-7, GP-08, I-8G-02). The intended pattern is a pair — a guarded rule placed before the general one:

```text
### PP-01R
rule_id: PP-01R
action_class: *
target_state: BASELINED
verdict_code: APPROVED
verdict_scope: INVOCATION_SCOPED
precondition: prior_outcome_resolved(any_policy)
description: Baselining already escalated to the project owner and approved by them proceeds
             without re-escalating the same decision.

### PP-01
rule_id: PP-01
action_class: *
target_state: BASELINED
verdict_code: ESCALATE
verdict_scope: INVOCATION_SCOPED
parameters:
  authority: project-owner
tier: project-owner
description: Any baselining not already decided requires explicit project-owner sign-off.
```

This expresses "escalate once, then honour the decision" without naming a single base. It is what `policy_v3` of `demo-inventory-01` should have been able to say, and could not.

> **History.** Until 2026-10-31 this rule was the opposite: **no** rule could declare a precondition, because the M12 evaluator did not evaluate them and a published precondition was silently ignored. Workspace `demo-inventory-01` lost a policy version to that gap on 2026-10-30 — `policy_v2` carried `precondition: prior_escalation_outcome_closed`, copied from the `gov-e2e` fixture, and had no effect; the loop was broken instead by naming two bases directly in `policy_v3`. The capability is now implemented (PE-9, RA-6 amended). The old spelling remains invalid: it was never a recognised predicate, and PP-V14 now says so explicitly rather than accepting it in silence. See finding F-03 of (internal review note).

---

## Event Formats

### POLICY_ACTIVATED

```
event_type:      POLICY_ACTIVATED
policy_id:       <profile_id of the activated policy>
policy_version:  <policy_version of the activated policy>
activated_at:    <ISO 8601 timestamp — same as effective_at in policy file>
activated_by:    <authored_by value from the policy file>
```

### POLICY_SUPERSEDED

```
event_type:    POLICY_SUPERSEDED
policy_id:     <profile_id of the superseded policy>
superseded_by: <profile_id of the new policy>
effective_at:  <effective_at of the new policy>
recorded_at:   <ISO 8601 timestamp of this event record>
recorded_by:   <authored_by of the new policy>
```

These event formats are contractualized in M12 L2 (`docs/commands/governance-run_execution.md`). M14 must produce them verbatim-compliant.

---

## Write Ordering — PUBLISH (Supersession)

Write ordering is mandatory. Each step must be verified before the next begins.

1. **Write new policy file** → `policies/<new_profile_id>.md` → verify file exists
2. **Update old policy file** → `status: ACTIVE → SUPERSEDED` → verify
3. **Append `POLICY_SUPERSEDED` event** → `events.md` → verify event present
4. **Update active policy registration** → `policy_profile.md` → verify new profile_id is active
5. **Append `POLICY_ACTIVATED` event** → `events.md` → verify event present

On any write failure: stop immediately. Report current state of repository. Do not proceed to remaining steps. Do not attempt rollback on already-written steps — manual recovery required.

---

## Owned Paths

```
WORKSPACE_ROOT/runtime/governance/policies/          ← policy files (M14 writes, M12 reads)
WORKSPACE_ROOT/runtime/governance/policy_profile.md  ← active policy registration (M14 writes, M12 reads)
WORKSPACE_ROOT/runtime/governance/events.md          ← shared append-only log (M12/M13/M14 all append)
```

M14 must never write to any path outside the above set, except to read from `runtime/current_workspace.md` and `runtime/workspaces.md` for workspace resolution.

---

## Runtime Principles

**PA-01 — Activation is Atomic**
A Policy Profile is either fully activated or not activated. There is no intermediate state in which a policy file exists without a corresponding `POLICY_ACTIVATED` event and an updated active registration.

**PA-02 — Event Log is Append-Only**
M14 appends `POLICY_ACTIVATED` and `POLICY_SUPERSEDED` events to `events.md`. It never modifies or deletes existing events.

**PA-03 — One Active Policy at a Time**
At any point, exactly one policy profile has `status: ACTIVE`. A supersession must complete fully (including `POLICY_SUPERSEDED` event and updated registration) before the new policy is considered active.

**PA-04 — Human Authorization Required**
No policy becomes active without explicit human authorization at the PUBLISH confirmation prompt. M14 must not auto-activate any policy without confirmation.

**PA-05 — Policy Files are Immutable Once Superseded**
A superseded policy file may not be modified after its `status` is updated to `SUPERSEDED`. It remains as an immutable historical record.

**PA-06 — profile_id Uniqueness**
Each published policy must carry a unique `profile_id`. Auto-versioning (policy_v1, policy_v2, ...) is the default; the human actor may override.

**PA-07 — M12 Compatibility**
All `POLICY_SUPERSEDED` events produced by M14 must conform to the field structure defined in `docs/commands/governance-run_execution.md` (TR-SUPERS-1). A `POLICY_SUPERSEDED` event that is malformed causes M12 to skip it with a WARNING (per M12 L2), which silently breaks supersession invalidation. M14 must validate event field completeness before appending.

**PA-08 — Write Ordering Enforced**
The write ordering defined above (5-step sequence for SUPERSEDE) is mandatory. Out-of-order writes are not permitted.

---

## Failure Handling

| Condition | Action |
|-----------|--------|
| No Policy Profile definition provided | BLOCKED — cannot PUBLISH without content |
| PP-V1 through PP-V14 validation failure | BLOCKED — report failing rule and reason; no file written |
| Workspace resolution failure | BLOCKED |
| Policy file write failure | BLOCKED — report; no event appended |
| Old policy file update failure (supersession) | BLOCKED — new policy file written but not yet activated; report partial state |
| `events.md` append failure | BLOCKED — report; registration may or may not have been updated; manual recovery required |
| Human cancels confirmation | BLOCKED — no file operations performed |

---

## Completion Criteria

**PUBLISH** — complete when:
- New policy file exists at `policies/<profile_id>.md` with `status: ACTIVE`
- Active policy registration updated to new `profile_id`
- `POLICY_ACTIVATED` event present in `events.md`
- If supersession: `POLICY_SUPERSEDED` event present in `events.md`; old policy file has `status: SUPERSEDED`
- All PP-V1 through PP-V14 validation rules passed

**STATUS** — complete when active policy and version history are displayed.

**INSPECT** — complete when the requested policy version content is displayed.
