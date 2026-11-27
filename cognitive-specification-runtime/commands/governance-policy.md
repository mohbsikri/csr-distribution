# /governance-policy

## Purpose

Administer the lifecycle of Policy Profiles for the Governance Layer. Create, activate, inspect, and supersede Policy Profiles that govern the M12 Governance Evaluation Runtime.

This command implements Milestone 14 — Governance Policy Administration.

---

## Workspace Resolution

Before any file operation, resolve the active workspace:

```
Step W1: Read runtime/current_workspace.md — parse workspace_id.
         If absent or empty: resolver_workspace_id = null; skip W2–W3; proceed to W4.
Step W2: Build WORKSPACE_ROOT = workspaces/<workspace_id>/
Step W3: Verify WORKSPACE_ROOT exists.
         If not found: BLOCKED — Workspace Root Not Found.
Step W4: Read runtime/workspaces.md — validate registry (R4a–R4e).
         R4a: workspace_id in registry — BLOCKING if missing.
         R4b: status not 'archived' — BLOCKING; warn if 'paused' or 'completed'.
         R4c: runtime_version present — WARNING if missing.
         R4d: last_active present — WARNING if missing.
         R4e: exactly one status:active entry matching resolver — Cases A–E as defined in
              ${CLAUDE_PLUGIN_ROOT}/docs/commands/governance-policy_execution.md Phase 1.
Step W5: All subsequent paths prefixed with WORKSPACE_ROOT.
```

Derive governance paths:
```
GOVERNANCE_DIR  = WORKSPACE_ROOT/runtime/governance/
POLICIES_DIR    = WORKSPACE_ROOT/runtime/governance/policies/
POLICY_REG      = WORKSPACE_ROOT/runtime/governance/policy_profile.md
EVENTS_LOG      = WORKSPACE_ROOT/runtime/governance/events.md
```

---

## Invocation

```
/governance-policy PUBLISH   [--authored-by <identity>]
/governance-policy STATUS
/governance-policy INSPECT   [<profile_id>]
```

- **PUBLISH** — Create and activate a new Policy Profile.
- **STATUS** — Display active policy summary and version history. Read-only.
- **INSPECT `[<profile_id>]`** — Display full content of a policy version. Read-only.
  If `<profile_id>` is omitted: display the active policy.

---

## Preconditions

1. Specification artifacts must exist and be readable:
   - `${CLAUDE_PLUGIN_ROOT}/docs/commands/governance-policy.md`
   - `${CLAUDE_PLUGIN_ROOT}/docs/commands/governance-policy_execution.md`
   - `${CLAUDE_PLUGIN_ROOT}/templates/prompts/governance_policy_prompt.md`

2. **PUBLISH** — policy content must be provided (inline, file reference, or requested from human).
3. **STATUS / INSPECT** — `POLICY_REG` must exist (or an informative NOT INITIALIZED message is returned).

---

## Step 1 — Load Specifications

Read and assimilate:

```
${CLAUDE_PLUGIN_ROOT}/docs/commands/governance-policy.md
${CLAUDE_PLUGIN_ROOT}/docs/commands/governance-policy_execution.md
${CLAUDE_PLUGIN_ROOT}/templates/prompts/governance_policy_prompt.md
```

The repository is the source of truth. Ignore any prior conversational assumptions not present in these files.

---

## Step 2 — Route Operation

Parse invocation arguments. Determine operation: PUBLISH, STATUS, or INSPECT.

If operation is absent or unrecognized: report BLOCKED — unknown operation. Stop.

---

## Step 3 — Execute Runtime

Execute the operation per the phase sequences defined in `${CLAUDE_PLUGIN_ROOT}/docs/commands/governance-policy_execution.md`, guided by the behavioral rules in `${CLAUDE_PLUGIN_ROOT}/templates/prompts/governance_policy_prompt.md`.

### PUBLISH execution sequence:

1. Initialize governance infrastructure (GOVERNANCE_DIR, POLICIES_DIR, EVENTS_LOG).
2. Load policy content (inline, file, or request from human).
3. Validate PP-V1 through PP-V13. Stop on any BLOCKING failure.
4. Detect first activation vs supersession (read POLICY_REG).
5. Infer `supersedes` if absent; validate PP-V12. Derive auto-versioned profile_id.
6. Present confirmation summary — include M12 Verdict invalidation impact on supersession.
7. Wait for explicit human confirmation. Stop on cancellation.
8. Execute write sequence (5 steps, verify each):
   - 8P.1: Write new policy file → verify
   - 8P.2: Update superseded file status → verify  *(SUPERSESSION only)*
   - 8P.3: Append POLICY_SUPERSEDED event → verify  *(SUPERSESSION only)*
   - 8P.4: Write/update POLICY_REG registration → verify
   - 8P.5: Append POLICY_ACTIVATED event → verify
9. Apply post-write validation PW-1 through PW-7.
10. Report POLICY PUBLISHED with full artifact and event summary.

### STATUS execution sequence:

1. Read POLICY_REG. If absent: report no active policy.
2. Display active policy summary and version history table.

### INSPECT execution sequence:

1. Resolve target profile_id (from argument or active registration).
2. Read policy file. If absent: BLOCKED — policy version not found.
3. Display full policy content.

---

## Workspace Isolation

All write operations must target paths within `WORKSPACE_ROOT/runtime/governance/`.

Exceptions (read-only, not workspace-scoped): `runtime/current_workspace.md`, `runtime/workspaces.md`, `docs/`, `templates/`

Any write outside `WORKSPACE_ROOT/runtime/governance/` must be rejected and reported as workspace contamination.

---

## Invariants

These rules must never be violated:

- Never modify or delete an existing event record in `events.md`. Append only.
- Never activate a policy without explicit human confirmation.
- Never proceed past a failed write step — report partial state and stop.
- Write ordering is strict: 8P.1 → 8P.2 → 8P.3 → 8P.4 → 8P.5 (no reordering).
- `POLICY_SUPERSEDED` event fields must be complete (policy_id, superseded_by, effective_at, recorded_at, recorded_by) — validate before appending (PA-07 / TR-SUPERS-1).

---

## Completion Reporting

```
STATUS: POLICY PUBLISHED        ← PUBLISH success
STATUS: POLICY BLOCKED          ← PUBLISH stopped (no files written, or partial with state description)
STATUS: POLICY FAILED           ← post-write validation failure (PW-1–PW-7)
STATUS: POLICY STATUS           ← STATUS operation complete
STATUS: POLICY INSPECT          ← INSPECT operation complete
```

---

## Expected Outputs

```
WORKSPACE_ROOT/runtime/governance/policies/<profile_id>.md   ← new policy file (PUBLISH)
WORKSPACE_ROOT/runtime/governance/policy_profile.md          ← active registration (PUBLISH)
WORKSPACE_ROOT/runtime/governance/events.md                  ← POLICY_ACTIVATED and/or POLICY_SUPERSEDED appended (PUBLISH)
```

STATUS and INSPECT produce no file outputs.
