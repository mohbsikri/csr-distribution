# /governance-run

## Command Purpose

M12 — Governance Evaluation Runtime determines whether an M11 coordination plan is authorized to proceed under the active Policy Profile.

**M12 evaluates. M12 does not:**

- coordinate pipeline execution
- invoke M1–M10 commands
- invoke M11
- resolve escalation or delegation outcomes
- write `governance_state.md` (owned exclusively by M13 — DMA-05)

M12 receives an M11 Plan, reconstructs Governance State from the event log, evaluates each plan step against the active Policy Profile, and returns a Verdict Set and a Governance Cycle Result Code to the caller.

This command implements Stage 12 — Governance Evaluation Runtime of the CSR pipeline.

---

## Specification Layers

Read and assimilate all three specification layers before executing:

```text
Layer 1 contract:       ${CLAUDE_PLUGIN_ROOT}/docs/commands/governance-run.md
Layer 2 execution spec: ${CLAUDE_PLUGIN_ROOT}/docs/commands/governance-run_execution.md
Layer 3 prompt:         ${CLAUDE_PLUGIN_ROOT}/templates/prompts/governance_run_prompt.md
```

Layer 1 defines what M12 does: Verdict vocabulary, Verdict structure, Governance State, Policy Profile contract, Governing Situation model, Runtime Principles (GP-01–GP-10), Governance Cycle Result Codes, owned paths, and non-goals.

Layer 2 defines how M12 executes: the 10-phase sequence (Phase 0–9), decision trees (DT-1 through DT-5), policy evaluation rules (PA-1–PA-4, PE-1–PE-8), verdict production rules (VP-1–VP-8), reconstruction rules (RA-1–RA-12), ordering rules (OR-1–OR-5), invalidation rules (IV-1–IV-7), failure handling, persistence rules (PR-1–PR-6), and runtime invariants (RI-01–RI-08).

Layer 3 defines behavioral intent: what M12 must always do, must never do, and how to reason at each phase.

The repository is the source of truth. Do not rely on prior conversational context. All behavioral rules and execution procedures are defined in L1, L2, and L3.

---

## Invocation Context

M12 is not directly user-invoked. It is invoked programmatically by M11 during:

- **Phase 9.5 — Initial Governance Evaluation Gate**: M12 evaluates the M11 Plan before first execution.
- **Phase 8.G — Governance Gate Resume**: M12 re-evaluates remaining plan steps after M13 resolves a governance outcome.

M11 supplies the following session context when invoking M12:

| Input | Format | Required |
|-------|--------|----------|
| M11 Plan | Ordered list of plan steps with command, base_id, current_state, target_state, step_type | REQUIRED |
| `plan_source` | Path or inline reference to the M11 Plan artifact | REQUIRED |
| `m11_session_id` | M11 session identifier — SES-NNN format | REQUIRED (DMA-02) |
| `mode` | Evaluation mode | OPTIONAL — default: EVALUATE |

M12 reads and does not modify any M11-supplied artifact.

---

## Required Runtime Inputs

Before executing, verify all required inputs are accessible:

| Input | Path | Required |
|-------|------|----------|
| Governance event log | `WORKSPACE_ROOT/runtime/governance/events.md` | Required if it exists; absent treated as empty history |
| Active Policy Profile | `WORKSPACE_ROOT/runtime/governance/policies/` | REQUIRED — at least one active profile must exist |
| M11 Plan | `plan_source` (supplied by caller) | REQUIRED |
| Workspace resolver | `runtime/current_workspace.md` | REQUIRED |

If any REQUIRED input is absent or unreadable: emit `GOVERNANCE_BLOCKED`. Stop. Do not proceed to execution.

---

## Runtime Loading Procedure

### Step 1 — Load Specification Layers

Read and assimilate in order:

1. `${CLAUDE_PLUGIN_ROOT}/docs/commands/governance-run.md` — Layer 1 Contract
2. `${CLAUDE_PLUGIN_ROOT}/docs/commands/governance-run_execution.md` — Layer 2 Execution Specification
3. `${CLAUDE_PLUGIN_ROOT}/templates/prompts/governance_run_prompt.md` — Layer 3 Behavioral Prompt

Layer 3 is the executable behavioral authority for this session. All phase execution, decision routing, event writing, and failure handling follow L3 behavioral intent as grounded in L1 and L2.

Do not proceed to Step 2 until all three layers are read and assimilated.

### Step 2 — Load Runtime Artifacts

Resolve the active workspace and load governed artifacts:

1. Read `runtime/current_workspace.md`. Parse `workspace_id`.
2. Construct `WORKSPACE_ROOT = workspaces/<workspace_id>/`.
3. Verify `WORKSPACE_ROOT` exists.
4. Read or initialize `WORKSPACE_ROOT/runtime/governance/events.md`.
5. Load the active Policy Profile from `WORKSPACE_ROOT/runtime/governance/policies/`.

Workspace resolution follows L2 Phase 1 procedures. Policy Profile loading follows L2 Phase 3 and PA-1 through PA-4.

---

## Workspace Isolation Enforcement

M12 owns exactly one file:

```text
WORKSPACE_ROOT/runtime/governance/events.md    (append-only)
```

M12 may create `WORKSPACE_ROOT/runtime/governance/` on first invocation (L2 Phase 2).

**All other writes are prohibited. The following path is explicitly prohibited under DMA-05:**

```text
WORKSPACE_ROOT/runtime/governance/governance_state.md    ← NEVER WRITTEN BY M12
```

`governance_state.md` is exclusively owned and written by M13 — Governance Outcome Resolution Runtime. M12 must not read it as a state derivation input and must never write it under any condition.

If a write to any path outside `events.md` is about to occur: stop immediately. Report workspace contamination. Terminate the governance cycle with `GOVERNANCE_FAILED`. Follow the Contamination Protocol defined in L3.

---

## Execution Procedure

Execute the runtime defined in `${CLAUDE_PLUGIN_ROOT}/templates/prompts/governance_run_prompt.md`.

All phase logic, decision trees, and behavioral constraints are defined in L1, L2, and L3. Do not reproduce them here. The high-level execution sequence is:

**Phase 0–1:** Initialize session and validate workspace.

**Phase 2:** Initialize governance directory and event log. Write `GOVERNANCE_SESSION_START`.

**Phase 3:** Reconstruct Governance State from `events.md` — Supersession Set, active Policy Profile, Prior Verdict Register (PERSISTENT and UNTIL_STATE_CHANGE partitions), Escalation History, Delegation Assignments. Follow RA-1 through RA-12 and OR-1. Never read `governance_state.md` as input (GP-01, RI-01, DMA-05).

**Phase 4:** Parse the M11 Plan and derive one Governing Situation per plan step. Apply GSD-1 through GSD-6. No plan step may be skipped.

**Phase 5:** Evaluate each Governing Situation against the active Policy Profile. Apply DT-1 (Prior Verdict check) then PE-1 through PE-8 (policy evaluation). The active Policy Profile is the sole Verdict authority (GP-08).

**Phase 6:** Assemble the Verdict Set. Write each Verdict as a `VERDICT_PRODUCED` event to `events.md`. Write `ESCALATION_RECORDED` for each ESCALATE Verdict. Write `DELEGATION_ASSIGNED` for each DELEGATE Verdict. All DMA-01/02/03 required fields must be present.

**Phase 7:** Apply the GP-08 Reconciliation Check. Apply DT-4 to determine the Governance Cycle Result Code. Write `GOVERNANCE_SESSION_END`. Return result to caller.

**Phase 8 (cross-cutting):** Classify and handle all failure conditions per L2 Section 14. Every failure must be named and reported.

**Phase 9 (no-op):** No action. `governance_state.md` is M13's exclusive responsibility (DMA-05).

---

## Event Persistence Requirements

All events are appended to `WORKSPACE_ROOT/runtime/governance/events.md`. The event log is append-only. No existing event record may be modified (RI-07, PR-2).

### Ordering Rules (OR-1 through OR-5)

| Rule | Requirement |
|------|-------------|
| OR-1 | Supersession Set must be fully built before any Prior Verdict retention check |
| OR-2 | Phase 3 (reconstruction) must complete before Phase 5 (evaluation) begins |
| OR-3 | Each `VERDICT_PRODUCED` event must be appended before any governance state projection is updated |
| OR-4 | `VERDICT_INVALIDATED` events (if written) must appear before `GOVERNANCE_SESSION_END` |
| OR-5 | Invalidation filter (RA-4.1, RA-5.1) must be applied in Phase 3 before Phase 5 receives the Prior Verdict Register |

### DMA Required Fields

Every `ESCALATION_RECORDED` and `DELEGATION_ASSIGNED` event must contain all three DMA-added fields. Omitting any field is a NON_RECOVERABLE failure — stop the cycle with `GOVERNANCE_FAILED`:

**ESCALATION_RECORDED mandatory fields (DMA-01, DMA-02, DMA-03):**

| Field | DMA | Purpose |
|-------|-----|---------|
| `policy_version` | DMA-01 | Active Policy Profile version at evaluation time — required by M13 for supersession detection |
| `m11_session_id` | DMA-02 | M11 session identifier (SES-NNN) — required by M13 for originating session correlation |
| `tier` | DMA-03 | Escalation tier from the matching policy rule — required by M13 for terminal authority eligibility validation |

**DELEGATION_ASSIGNED mandatory fields (DMA-01, DMA-02, DMA-03):**

| Field | DMA | Purpose |
|-------|-----|---------|
| `policy_version` | DMA-01 | Active Policy Profile version at evaluation time — required by M13 for supersession detection |
| `m11_session_id` | DMA-02 | M11 session identifier (SES-NNN) — required by M13 for originating session correlation |
| `tier` | DMA-03 | Delegation tier from the matching policy rule — required by M13 for terminal authority eligibility validation |

---

## Output Contract

M12 returns exactly two outputs to M11 at cycle completion:

| Output | Returned when |
|--------|--------------|
| **Governance Cycle Result Code** | Always — one of: `GOVERNANCE_COMPLETE`, `GOVERNANCE_ESCALATED`, `GOVERNANCE_DENIED`, `GOVERNANCE_FAILED`, `GOVERNANCE_BLOCKED` |
| **Verdict Set** | When result is `GOVERNANCE_COMPLETE`, `GOVERNANCE_ESCALATED`, or `GOVERNANCE_DENIED` — one Verdict per M11 plan step |

The Verdict Set is **not** returned when result is `GOVERNANCE_FAILED` or `GOVERNANCE_BLOCKED`.

No additional output artifacts are produced. M12 does not write `governance_state.md`. M12 does not modify M11 artifacts.

Result code semantics and Verdict Set structure are defined in L1 (Governance Cycle Result Codes, Governance Verdict Structure).

---

## Failure Contract

All failure conditions, classifications, and result codes are defined in L2 Section 14 (Failure Handling) and L3 (Failure Handling section). Do not invent new failure classes.

| Class | Handling |
|-------|----------|
| `NON_RECOVERABLE` | Stop cycle. Append `GOVERNANCE_SESSION_END` with result code. Report failure. Do not return a partial Verdict Set. |
| `RECOVERABLE` | Record failure for the affected step or record. Emit WARNING. Continue remaining steps. |

NON_RECOVERABLE conditions and their result codes are enumerated in L2 Section 14 and L3 Phase 8.

---

## Validation

Before reporting cycle completion, verify all of the following gates:

| Gate | Requirement |
|------|-------------|
| VG-1 | `${CLAUDE_PLUGIN_ROOT}/docs/commands/governance-run.md` (L1) was read and assimilated before execution began |
| VG-2 | `${CLAUDE_PLUGIN_ROOT}/docs/commands/governance-run_execution.md` (L2) was read and assimilated before execution began |
| VG-3 | `${CLAUDE_PLUGIN_ROOT}/templates/prompts/governance_run_prompt.md` (L3) was read and assimilated before execution began |
| VG-4 | `governance_state.md` was never written (DMA-05 enforced) |
| VG-5 | Every `ESCALATION_RECORDED` and `DELEGATION_ASSIGNED` event contains `policy_version`, `m11_session_id`, and `tier` (DMA-01/02/03 enforced) |
| VG-6 | No write occurred outside `WORKSPACE_ROOT/runtime/governance/events.md` (workspace isolation enforced) |
| VG-7 | Output is exactly: Governance Cycle Result Code + Verdict Set (or Result Code alone on FAILED/BLOCKED) — matches L1 Output Contract |
| VG-8 | No behavioral rule was introduced or applied that is not traceable to L1, L2, or L3 |

If any gate fails: report the failing gate and the violation. Terminate with `GOVERNANCE_FAILED`.
