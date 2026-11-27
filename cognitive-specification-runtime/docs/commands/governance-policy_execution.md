# Governance Policy Administration — Layer 2 Execution Specification

**Milestone:** M14
**Version:** 1.0
**Status:** DRAFT
**Effective Date:** 2026-06-19
**File:** `docs/commands/governance-policy_execution.md`
**Layer 1 Contract:** `docs/commands/governance-policy.md`

---

## 1. Runtime Overview

This specification defines the step-by-step execution model for the `/governance-policy` command. All behavioral rules, event formats, write ordering constraints, and validation requirements are inherited from `docs/commands/governance-policy.md` (Layer 1 Contract).

Three operations are defined:
- **PUBLISH** — create and activate a Policy Profile
- **STATUS** — read-only view of active policy and version history
- **INSPECT** — read-only view of a specific policy version

All operations resolve the active workspace and operate on governance-layer paths within `WORKSPACE_ROOT`.

---

## 2. Phase Structure

```
Phase 0 — Session Initialization
    │
    ▼
Phase 1 — Workspace Validation
    │
    ▼
Phase 2 — Operation Routing
    │
    ├── PUBLISH ─────────────────────────────────────────────────────┐
    │   │                                                            │
    │   ▼                                                            │
    │   Phase 3P — Infrastructure Initialization                     │
    │   │                                                            │
    │   ▼                                                            │
    │   Phase 4P — Policy Content Loading                            │
    │   │                                                            │
    │   ▼                                                            │
    │   Phase 5P — Policy Profile Validation (PP-V1–PP-V13)         │
    │   │                                                            │
    │   ▼                                                            │
    │   Phase 6P — Supersession Detection                            │
    │   │                                                            │
    │   ▼                                                            │
    │   Phase 7P — Confirmation Gate                                 │
    │   │                                                            │
    │   ▼                                                            │
    │   Phase 8P — Write Sequence                                    │
    │   │                                                            │
    │   ▼                                                            │
    │   Phase 9P — Post-Write Validation                             │
    │   │                                                            │
    │   ▼                                                            │
    │   Phase 10P — Session Result                                   │
    │                                                                │
    ├── STATUS ───────────────────────────────────────────────────┐  │
    │   Phase 3S — Load Active Registration                       │  │
    │   Phase 4S — Load Version History                           │  │
    │   Phase 5S — Display and Report                             │  │
    │                                                             │  │
    └── INSPECT ──────────────────────────────────────────────────┘  │
        Phase 3I — Resolve Target Profile                            │
        Phase 4I — Load and Display Policy Content                   │
```

---

## 3. Phase 0 — Session Initialization

Parse the invocation arguments:

```
/governance-policy PUBLISH   [--authored-by <identity>]
/governance-policy STATUS
/governance-policy INSPECT   [<profile_id>]
```

Record:
- `operation`: PUBLISH | STATUS | INSPECT
- `authored_by`: value from `--authored-by` flag, or null (will be requested in Phase 7P)
- `inspect_target`: profile_id from argument, or null (defaults to active policy)

If operation is absent or unrecognized: report BLOCKED — unknown operation. Stop.

---

## 4. Phase 1 — Workspace Validation

Workspace resolution is mandatory before any file operation.

```
Step W1: Read runtime/current_workspace.md — parse workspace_id.
         If absent or empty: resolver_workspace_id = null; skip W2–W3; proceed to W4.
Step W2: Build WORKSPACE_ROOT = workspaces/<workspace_id>/
Step W3: Verify WORKSPACE_ROOT exists.
         If not found: BLOCKED — Workspace Root Not Found: workspaces/<workspace_id>/
Step W4: Read runtime/workspaces.md — validate registry (R4a–R4e):
         R4a: workspace_id must be present in registry — BLOCKING if missing.
         R4b: status must not be 'archived' — BLOCKING; warn if 'paused' or 'completed'.
         R4c: runtime_version must be present — WARNING if missing.
         R4d: last_active must be present — WARNING if missing.
         R4e: count status:active entries in registry.
              Case A — Normal: exactly one active entry; workspace_id = resolver_workspace_id → continue.
              Case B — Drift: one active entry; workspace_id ≠ resolver_workspace_id → BLOCKING.
              Case C — Resolver absent: null resolver_workspace_id; one active entry → BLOCKING.
              Case D — No active entry: zero status:active entries → BLOCKING.
              Case E — Multiple active entries: more than one status:active → BLOCKING.
Step W5: All subsequent file operation paths are prefixed with WORKSPACE_ROOT.
```

Derive governance paths:

```
GOVERNANCE_DIR  = WORKSPACE_ROOT/runtime/governance/
POLICIES_DIR    = WORKSPACE_ROOT/runtime/governance/policies/
POLICY_REG      = WORKSPACE_ROOT/runtime/governance/policy_profile.md
EVENTS_LOG      = WORKSPACE_ROOT/runtime/governance/events.md
```

---

## 5. Phase 2 — Operation Routing

Route to the appropriate phase sequence based on `operation`:

| Operation | Phase sequence |
|-----------|---------------|
| PUBLISH | 3P → 4P → 5P → 6P → 7P → 8P → 9P → 10P |
| STATUS | 3S → 4S → 5S |
| INSPECT | 3I → 4I |

---

## 6. PUBLISH — Phases 3P through 10P

### Phase 3P — Infrastructure Initialization

3P.1. Verify `GOVERNANCE_DIR` exists.
- If absent: create `GOVERNANCE_DIR` and `POLICIES_DIR` (first governance operation in this workspace).

3P.2. Verify `POLICIES_DIR` exists.
- If absent after 3P.1: BLOCKED — directory creation failed.

3P.3. Check `EVENTS_LOG` existence.
- If absent: initialize `EVENTS_LOG` with header:
  ```
  # Governance Event Log

  workspace_id: <workspace_id>
  initialized: <current ISO 8601 timestamp>

  ---
  ```
- If present: confirm readable.

---

### Phase 4P — Policy Content Loading

4P.1. If policy content was provided inline in the conversation: capture as `raw_policy_content`.

4P.2. If a file path was provided instead of inline content: read the file at the given path and capture as `raw_policy_content`.

4P.3. If neither inline nor file path provided: request the human actor to supply the policy content. Present the Policy Profile schema from Layer 1 (Section "Policy Profile Schema") as a reference template. Wait for input.

4P.4. Parse `raw_policy_content` and extract the following fields into `parsed_policy`:
- `profile_id`, `policy_version`, `status`, `effective_at`, `authored_by`
- `supersedes` (may be absent)
- `gap_default` (from `## Gap Default` section)
- rule list (from `## Rules` section): one entry per `### <rule_id>` subsection, each with `rule_id`, `action_class`, `verdict_code`, `verdict_scope`, `tier` (if present), `parameters` (if present), `precondition` (if present — a named predicate from the closed vocabulary; validated by PP-V14 in Phase 5P and evaluated by M12 at PE-9)
- Terminal Authority Sets (from `## Terminal Authority Sets` section)
- Response Intervals (from `## Response Intervals` section, if present)

If `authored_by` was provided via `--authored-by` flag AND is present in the policy content: verify they match. If they conflict: use the flag value; emit WARNING.

If `authored_by` is absent from both: record as null (will be resolved in Phase 7P).

---

### Phase 5P — Policy Profile Validation

Apply PP-V1 through PP-V11, PP-V13 and PP-V14 against `parsed_policy`.

PP-V12 is applied in Phase 6P after supersession detection, once `active_profile_id` is known.

| Rule | Check |
|------|-------|
| PP-V1 | `profile_id` present and non-empty |
| PP-V2 | `policy_version` present and non-empty |
| PP-V3 | `status` field is `ACTIVE` |
| PP-V4 | `effective_at` present and parseable as ISO 8601 |
| PP-V5 | `authored_by` present and non-empty (or resolved from flag) |
| PP-V6 | `gap_default` present and set to a recognized verdict code (APPROVED, ESCALATE, DELEGATE, DENY) |
| PP-V7 | At least one rule present in `## Rules` section |
| PP-V8 | Each rule has `rule_id`, `verdict_code`, `verdict_scope` — all non-empty |
| PP-V9 | ESCALATE rules carry `authority` in `parameters` and `tier` field |
| PP-V10 | DELEGATE rules carry `delegate_target` in `parameters` and `tier` field |
| PP-V11 | If ESCALATE or DELEGATE rules exist: `## Terminal Authority Sets` section present and non-empty |
| PP-V13 | `profile_id` does not already exist as a file in `POLICIES_DIR` |
| PP-V14 | Any `precondition` names a recognised predicate, and its rule is `INVOCATION_SCOPED` |

If any BLOCKING rule fails: report the rule ID and the specific check that failed. Stop. No file is written.

If PP-V5 fails (authored_by absent) and was not provided via flag: request from human actor before proceeding. Update `parsed_policy.authored_by`.

Apply PP-V14 to every rule carrying a non-empty `precondition`. Two conditions, both BLOCKING.

**PP-V14.a — recognised predicate.** The value, stripped of any `(qualifier)` suffix, must be one of `prior_outcome_resolved`, `prior_outcome_open`, `no_prior_outcome`. A qualifier is accepted only on `prior_outcome_resolved` and only as `current_policy` or `any_policy`.

```text
STATUS: BLOCKED — PP-V14: rule <rule_id> declares precondition "<value>", which is not a
  recognised predicate.

  The precondition vocabulary is closed. There is no expression language. Recognised:
    prior_outcome_resolved[(current_policy|any_policy)]
    prior_outcome_open
    no_prior_outcome

  See docs/commands/governance-run_execution.md, "Rule Preconditions".

No file written. No event appended.
```

**PP-V14.b — scope.** A rule carrying a precondition must declare `verdict_scope: INVOCATION_SCOPED`.

```text
STATUS: BLOCKED — PP-V14: rule <rule_id> carries a precondition but declares
  verdict_scope: <value>.

  A conditional rule must be re-evaluated on every cycle. A retained Verdict would outlive
  the condition that justified it, authorising a later invocation on a precondition that no
  longer holds.

  Set verdict_scope: INVOCATION_SCOPED, or remove the precondition.

No file written. No event appended.
```

Stop on either. An unrecognised predicate is rejected rather than ignored, because a precondition accepted in silence is exactly the failure that cost workspace `demo-inventory-01` a policy version on 2026-10-30 — see the Layer 1 Contract, "PP-V14 — Precondition well-formedness".

---

### Phase 6P — Supersession Detection

6P.1. Determine whether an active policy registration exists:
- Read `POLICY_REG`.
- If `POLICY_REG` is absent: `is_first_activation = true`; `active_profile_id = null`.
- If `POLICY_REG` is present and readable: parse `profile_id` (active profile), `policy_version`. Set `is_first_activation = false`; `active_profile_id = <parsed value>`.

6P.2. If `is_first_activation = false`:
- This PUBLISH is a supersession. Apply PP-V12:
  - If `supersedes` is absent from the parsed policy: infer it from `active_profile_id`; emit WARNING that `supersedes` was inferred automatically.
  - If `supersedes` is present but does not match `active_profile_id`: BLOCKED — supersession target mismatch (PP-V12 violation). Report: found `<supersedes value>`, expected `<active_profile_id>`. Human must correct the policy content.

6P.3. Derive auto-versioning if not overridden:
- If `is_first_activation = true` AND `parsed_policy.profile_id` matches pattern `policy_v<n>`: accept as-is.
- If `is_first_activation = true` AND `profile_id` is absent or generic: auto-assign `profile_id = policy_v1`, `policy_version = v1`.
- If `is_first_activation = false`: recommended next `profile_id = policy_v<current_n + 1>`. If the human provided a different `profile_id` in the policy content, accept it (PP-V13 ensures no collision).

---

### Phase 7P — Confirmation Gate

7P.1. Present confirmation summary:

```
PUBLISH CONFIRMATION

Operation:       <FIRST ACTIVATION | SUPERSESSION>
New profile_id:  <profile_id>
Version:         <policy_version>
Effective at:    <effective_at>
Authored by:     <authored_by>
Rules:           <N> rules (<list rule_ids>)
Gap default:     <gap_default>
[If SUPERSESSION:]
  Supersedes:    <active_profile_id>
  Effect:        Verdicts produced under <active_profile_id> will be invalidated
                 at next M12 evaluation (RA-4.1, RA-5.1 — PERSISTENT and
                 UNTIL_STATE_CHANGE Verdicts produced under the superseded policy
                 are discarded during M12 Phase 3 reconstruction).

Files to write:
  + WORKSPACE_ROOT/runtime/governance/policies/<profile_id>.md  (new policy)
  [If SUPERSESSION:]
  ~ WORKSPACE_ROOT/runtime/governance/policies/<active_profile_id>.md  (status → SUPERSEDED)
  ~ WORKSPACE_ROOT/runtime/governance/policy_profile.md  (registration update)

Events to append:
  [If SUPERSESSION:]
  + POLICY_SUPERSEDED (policy_id: <active_profile_id>, superseded_by: <profile_id>)
  + POLICY_ACTIVATED (policy_id: <profile_id>)
  [If FIRST ACTIVATION:]
  + POLICY_ACTIVATED (policy_id: <profile_id>)

Confirm? (yes / cancel)
```

7P.2. Wait for explicit human response.
- `yes` (or affirmative equivalent): proceed to Phase 8P.
- `cancel`, `no`, or silence: BLOCKED — human cancelled. No file operations performed.

---

### Phase 8P — Write Sequence

Execute steps in strict order. Verify each step before proceeding to the next.

**Step 8P.1 — Write new policy file**

Write `raw_policy_content` (with `supersedes` field inserted if inferred in Phase 6P) to:
```
WORKSPACE_ROOT/runtime/governance/policies/<profile_id>.md
```

Verify: file exists and is readable. If write fails: BLOCKED — report; no subsequent steps executed.

**Step 8P.2 — Update superseded policy file status** *(SUPERSESSION only)*

Read the superseded policy file at `WORKSPACE_ROOT/runtime/governance/policies/<active_profile_id>.md`.

Update `status: ACTIVE` → `status: SUPERSEDED` in the file header.

Verify: file exists; `status` field reads `SUPERSEDED`. If update fails: BLOCKED — report; new policy file written (Step 8P.1 complete) but not yet activated; manual recovery required.

**Step 8P.3 — Append POLICY_SUPERSEDED event** *(SUPERSESSION only)*

Append to `EVENTS_LOG`:
```
---

event_type:    POLICY_SUPERSEDED
policy_id:     <active_profile_id>
superseded_by: <new profile_id>
effective_at:  <effective_at from new policy>
recorded_at:   <current ISO 8601 timestamp>
recorded_by:   <authored_by from new policy>
```

Verify: event record exists in `EVENTS_LOG`. If append fails: BLOCKED — report partial state.

**Step 8P.4 — Update active policy registration**

Write or overwrite `POLICY_REG` (`runtime/governance/policy_profile.md`):

```
# Active Policy Profile Reference

profile_id:            <new profile_id>
policy_version:        <new policy_version>
policy_artifact_path:  runtime/governance/policies/<new profile_id>.md
status:                ACTIVE
registered_at:         <current ISO 8601 timestamp>
[If SUPERSESSION:]
supersedes:            <active_profile_id>

## Note

This file is the active policy profile registration. Full policy content
is at runtime/governance/policies/<new profile_id>.md.

## History

| policy_version | activated_at | deactivated_at | reason |
|----------------|--------------|----------------|--------|
[append existing rows from prior registration if present]
[If SUPERSESSION: add row for superseded policy with deactivated_at = effective_at of new policy and reason = superseded by <new profile_id>]
| <new policy_version> | <effective_at> | — | active |
```

Verify: `POLICY_REG` exists; `profile_id` field reads the new `profile_id`. If write fails: BLOCKED — report.

**Step 8P.5 — Append POLICY_ACTIVATED event**

Append to `EVENTS_LOG`:
```
---

event_type:      POLICY_ACTIVATED
policy_id:       <new profile_id>
policy_version:  <new policy_version>
activated_at:    <effective_at from new policy>
activated_by:    <authored_by from new policy>
```

Verify: event record exists in `EVENTS_LOG`. If append fails: BLOCKED — report partial state.

---

### Phase 9P — Post-Write Validation

Apply post-write validation rules:

| Rule | Check | Class |
|------|-------|-------|
| PW-1 | New policy file exists at `policies/<profile_id>.md` | BLOCKING |
| PW-2 | New policy file contains `status: ACTIVE` | BLOCKING |
| PW-3 | `POLICY_REG` exists and `profile_id` field matches new `profile_id` | BLOCKING |
| PW-4 | `EVENTS_LOG` contains `POLICY_ACTIVATED` event with `policy_id = <new profile_id>` | BLOCKING |
| PW-5 | *(SUPERSESSION only)* `EVENTS_LOG` contains `POLICY_SUPERSEDED` event with `policy_id = <active_profile_id>` and `superseded_by = <new profile_id>` | BLOCKING |
| PW-6 | *(SUPERSESSION only)* Superseded policy file contains `status: SUPERSEDED` | BLOCKING |
| PW-7 | All writes targeted paths within `WORKSPACE_ROOT/runtime/governance/` | BLOCKING |

If any BLOCKING rule fails: report rule ID, artifact path, and check that failed. Report POLICY FAILED.

---

### Phase 10P — Session Result

Report:

```
STATUS: POLICY PUBLISHED

Operation:      <FIRST ACTIVATION | SUPERSESSION>
Profile ID:      <profile_id>
Version:         <policy_version>
Effective at:    <effective_at>
Authored by:     <authored_by>
Policy file:     WORKSPACE_ROOT/runtime/governance/policies/<profile_id>.md
Registration:    WORKSPACE_ROOT/runtime/governance/policy_profile.md
Events appended:
  <list of events appended to events.md>
Rules active:    <N> (<rule_ids>)
Gap default:     <gap_default>
[If SUPERSESSION:]
  Superseded:    <active_profile_id>
  M12 impact:    PERSISTENT and UNTIL_STATE_CHANGE Verdicts under <active_profile_id>
                 will be invalidated at next M12 Phase 3 reconstruction.
```

---

## 7. STATUS — Phases 3S through 5S

### Phase 3S — Load Active Registration

3S.1. Read `POLICY_REG`.
- If absent: report STATUS: NO ACTIVE POLICY — governance not yet initialized in this workspace. Stop.
- If present: parse all fields including `## History` table.

### Phase 4S — Load Event Count (optional context)

4S.1. Read `EVENTS_LOG` (if present).
- Count `POLICY_ACTIVATED` and `POLICY_SUPERSEDED` events for reference.
- If absent: treat as empty history; proceed.

### Phase 5S — Display and Report

Report:

```
STATUS: POLICY STATUS

Active Policy:
  Profile ID:    <profile_id>
  Version:       <policy_version>
  Effective at:  <registered_at>
  Artifact:      <policy_artifact_path>

Version History:
  | policy_version | activated_at | deactivated_at | reason |
  |----------------|--------------|----------------|--------|
  <rows from ## History table in POLICY_REG>
```

---

## 8. INSPECT — Phases 3I through 4I

### Phase 3I — Resolve Target Profile

3I.1. If `inspect_target` (profile_id from argument) is present:
- Resolve path: `WORKSPACE_ROOT/runtime/governance/policies/<inspect_target>.md`
- Verify file exists. If absent: BLOCKED — policy version not found.

3I.2. If `inspect_target` is null (no argument):
- Read `POLICY_REG` to obtain active `profile_id` and `policy_artifact_path`.
- If `POLICY_REG` absent: BLOCKED — no active policy; specify a profile_id explicitly.
- Resolve path: `WORKSPACE_ROOT/runtime/governance/policies/<active_profile_id>.md`
- Verify file exists. If absent: BLOCKED — active policy file not found at expected path.

### Phase 4I — Load and Display Policy Content

4I.1. Read full content of resolved policy file.

4I.2. Report:

```
STATUS: POLICY INSPECT

Profile ID:   <profile_id>
Version:      <policy_version>
Status:       <status>
Effective at: <effective_at>
Authored by:  <authored_by>

--- Full Policy Content ---

<full raw content of the policy file>
```

---

## 9. Validation Rules Summary

### PUBLISH — Policy Profile Validation (PP-V1–PP-V13)

Applied in Phase 5P. See Layer 1 Contract Section "Policy Profile Validation Rules."

### PUBLISH — Post-Write Validation (PW-1–PW-7)

Applied in Phase 9P. Defined in Section 6 above.

### Session-Level Invariants

| Invariant | Applies to |
|-----------|-----------|
| All writes target `WORKSPACE_ROOT/runtime/governance/` only | All operations |
| `EVENTS_LOG` is append-only; no existing record is modified or deleted | PUBLISH |
| Write ordering 8P.1 → 8P.2 → 8P.3 → 8P.4 → 8P.5 is strict | PUBLISH (SUPERSESSION) |
| Human confirmation precedes all file writes | PUBLISH |

---

## 10. Failure Handling

| Condition | Phase | Result |
|-----------|-------|--------|
| Unknown operation | Phase 0 | BLOCKED |
| Workspace resolution failure | Phase 1 | BLOCKED |
| Directory creation failure | Phase 3P | BLOCKED |
| No policy content provided | Phase 4P | Request from human; if not provided: BLOCKED |
| PP-V1 through PP-V14 failure | Phase 5P | BLOCKED — no file written |
| `supersedes` mismatch | Phase 6P | BLOCKED |
| Human cancels confirmation | Phase 7P | BLOCKED — no file operations |
| Step 8P.1 write failure | Phase 8P | BLOCKED — report; no event appended |
| Step 8P.2 update failure | Phase 8P | BLOCKED — report partial state (new file written, not activated) |
| Step 8P.3 append failure | Phase 8P | BLOCKED — report partial state |
| Step 8P.4 write failure | Phase 8P | BLOCKED — report partial state |
| Step 8P.5 append failure | Phase 8P | BLOCKED — report partial state |
| PW-1 through PW-7 failure | Phase 9P | PUBLISH FAILED — report rule and artifact |
| POLICY_REG absent on STATUS/INSPECT | Phase 3S/3I | Report no active policy |

For all BLOCKED states arising after any file has been written: explicitly describe the current repository state (what was written, what was not, what events are appended).

---

## 11. Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| DL-1: First activation vs supersession routing | Single PUBLISH operation handles both cases; detection is automatic in Phase 6P | Reduces cognitive overhead; operator uses one command regardless of context |
| DL-2: Auto-versioning | M14 auto-assigns `policy_v<n+1>` profile_id; human can override | Consistency with existing policy_v1/policy_v2 naming in gov-e2e; no manual versioning required |
| DL-3: `supersedes` field inference | M14 infers `supersedes` from active registration if absent in content | Reduces human error; prevents PP-V12 failures from typos |
| DL-4: Superseded policy file mutation | Update `status: ACTIVE → SUPERSEDED` in the superseded policy file | PA-05 (immutable after supersession) applies to content below the status field; the status header field reflects lifecycle truth |
| DL-5: Write ordering direction | New file first, then old file update, then events | Ensures events are only appended after the file system is consistent; events are the authoritative record for M12 reconstruction |
| DL-6: events.md shared log | M14 appends to the same `events.md` as M12 and M13 | Events.md is the single governance truth source; all governance actors must write to the same log |
| DL-7: policy_profile.md path | `WORKSPACE_ROOT/runtime/governance/policy_profile.md` (M12 L2 default) | Canonicalize the path per M12 L2 specification; resolves discrepancy in gov-e2e E2E setup which placed this file at `WORKSPACE_ROOT/governance/policy_profile.md` |
