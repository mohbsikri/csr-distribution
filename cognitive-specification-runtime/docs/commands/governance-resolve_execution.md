# Governance Outcome Resolution Runtime — Execution Specification

**Version:** 1.0
**Status:** VALIDATED
**Milestone:** M13
**Layer:** Layer 2 Execution Specification
**Authoritative L1:** docs/commands/governance-resolve.md

---

## 1. Runtime Invocation Model

M13 supports four modes. Mode is determined at Phase 0 from the invocation form.

### 1.1 STATUS Mode

**Invocation:** `/governance-resolve`

**Purpose:** Present all open governance outcomes in the active workspace. No resolution is
processed. Validity evaluation executes as a mandatory side effect.

**Behavior:**
1. Execute Phase 0 through Phase 6 (Governance State Reconstruction, Open Outcome Reconstruction, and Validity
   Evaluation complete before presentation).
2. Present all outcomes in the OPEN set derived after Phase 6.
3. For each open outcome: display outcome_id, outcome_type, base, tier, created_at,
   policy_version, session_id, and elapsed time (DELEGATION_ASSIGNED only).
4. Report count of outcomes closed during this invocation's validity evaluation.
5. Execute Phase 10 (Projection Refresh) and Phase 11 (Session Result Determination).

**Validity evaluation:** Mandatory. May close outcomes as a side effect. STATUS is not
read-only when open outcomes satisfy validity failure conditions.

**Result:** STATUS_COMPLETED.

---

### 1.2 INSPECT Mode

**Invocation:** `/governance-resolve <outcome_id>`

**Purpose:** Present full detail for one governance outcome. No resolution is processed.
Validity evaluation executes as a mandatory side effect.

**Behavior:**
1. Execute Phase 0 through Phase 6.
2. Verify target_outcome_id exists in the reconstructed outcome registry.
3. If not found: BLOCKED.
4. Present full outcome record: all fields, current state (OPEN or CLOSED), closure path
   if CLOSED, and all M13-produced events with matching outcome_id.
5. Execute Phase 10 and Phase 11.

**Result:** INSPECTION_COMPLETED.

---

### 1.3 RESOLVE Mode

**Invocation:** `/governance-resolve <outcome_id> APPROVED|REJECTED|DENIED`

**Purpose:** Submit a terminal external governance decision for one open outcome. Validates
the resolution and records it if valid.

**Behavior:**
1. Execute Phase 0 through Phase 6.
2. Verify target_outcome_id is in the OPEN set (post-validity). If CLOSED: BLOCKED. If
   not found: BLOCKED.
3. Execute Phase 7 (Mode Routing) → Phase 8 (Resolution Validation).
4. If validation fails: VALIDATION_REJECTED.
5. If validation passes: Execute Phase 9 (Resolution Processing).
6. Execute Phase 10 (Projection Refresh) and Phase 11 (Session Result Determination).

**Result:** RESOLUTION_COMPLETED (success) or VALIDATION_REJECTED (validation failure) or
BLOCKED (precondition or state failure).

---

### 1.4 VALIDATE Mode

**Invocation:** `/governance-resolve --validate`

**Purpose:** Execute validity evaluation only. Close all outcomes that fail validity conditions. No resolution is processed. Used for maintenance invocations and by operators before M11 resume attempts.

**Behavior:**
1. Execute Phase 0 through Phase 6 (Governance State Reconstruction, Open Outcome Reconstruction, and Validity Evaluation complete).
2. All validity closures from Phase 6 have already executed.
3. VALIDATE mode does not produce an outcome presentation table. Open outcomes are not listed in VALIDATE mode output.
4. Execute Phase 10 (Projection Refresh) and Phase 11 (Session Result Determination).

**Output:** The VALIDATE mode result report includes:
- `VALIDITY_CLOSURE_COUNT` — number of outcomes closed during Phase 6.
- `VALIDITY_CLOSURE_LIST` — for each outcome closed during Phase 6: `outcome_id` and `closure_path`. If no outcomes were closed: empty list.
- Any WARNINGs issued during this session.

The distinction between STATUS and VALIDATE is output only: STATUS presents the post-validity OPEN_SET; VALIDATE does not.

**Validity evaluation:** Mandatory. Identical execution path to STATUS mode through Phase 6.

**Result:** `VALIDITY_COMPLETED`.

---

## 2. Preconditions

Preconditions are validated in Phase 2 (Artifact Discovery) and Phase 3 (Precondition
Validation). Failures are BLOCKING unless noted.

| ID | Condition | Failure Action |
|----|-----------|----------------|
| PC-01 | `docs/commands/governance-resolve.md` is readable | `BLOCKED — L1 contract not found: docs/commands/governance-resolve.md` |
| PC-02 | `runtime/current_workspace.md` is readable | `BLOCKED — Workspace control file unavailable` |
| PC-03 | `runtime/workspaces.md` is readable | `BLOCKED — Workspace registry unavailable` |
| PC-04 | Active Policy Profile is readable | `BLOCKED — Active Policy Profile unavailable. Resolution validation and supersession detection require the Policy Profile.` |
| PC-05 | `WORKSPACE_ROOT/runtime/governance/events.md` exists and is readable, OR does not exist | If present but unreadable: `BLOCKED — Governance event log present but unreadable`. If absent: initialize in Phase 2.3. |
| PC-06 | `WORKSPACE_ROOT/runtime/governance/` directory exists, OR does not exist | If absent: create in Phase 2.2. If creation fails: `BLOCKED — Cannot initialize M13 directory` |
| PC-07 | (RESOLVE, INSPECT) `target_outcome_id` is specified and non-empty | `BLOCKED — Unrecognized invocation form. See usage above.` (caught at Phase 0) |
| PC-08 | (RESOLVE) `decision_type` is APPROVED, REJECTED, or DENIED | `BLOCKED — Unrecognized invocation form. See usage above.` (caught at Phase 0) |
| PC-09 | (RESOLVE) `target_outcome_id` identifies an existing outcome | `BLOCKED — Outcome not found: <outcome_id>` (evaluated at Phase 7.1) |

PC-07 and PC-08 are enforced at Phase 0. PC-09 is enforced at Phase 7. All remaining
preconditions are enforced at Phase 2 or Phase 3.

---

## 3. Runtime Phases

### Phase 0 — Invocation Parsing

**Purpose:** Parse the raw invocation, determine mode, and extract parameters. Assign
session_ref.

**Inputs:** Raw invocation string.

**Steps:**

0.1 Assign `session_ref`:

```text
session_ref = "M13-" + ISO-8601 timestamp (millisecond precision)
```

session_ref uniquely identifies this M13 invocation and is carried on all events produced
in this session.

0.2 Match invocation against defined forms (RD-1):

| Invocation Form | MODE | Parameters |
|----------------|------|------------|
| No arguments | STATUS | — |
| `--validate` | VALIDATE | — |
| `<outcome_id>` (single token, not `--validate`) | INSPECT | target_outcome_id = `<outcome_id>` |
| `<outcome_id> APPROVED` | RESOLVE | target_outcome_id, decision_type = APPROVED |
| `<outcome_id> REJECTED` | RESOLVE | target_outcome_id, decision_type = REJECTED |
| `<outcome_id> DENIED` | RESOLVE | target_outcome_id, decision_type = DENIED |
| Any other form | — | BLOCKED |

0.3 If invocation form is unrecognizable:

```text
BLOCKED — Unrecognized invocation form. See usage above.
```

Stop. Session result = BLOCKED.

0.4 Record MODE, target_outcome_id (if applicable), decision_type (if applicable),
session_ref in session context. Do not persist — session context is in-memory only.

**Outputs:** MODE, session_ref, target_outcome_id (RESOLVE/INSPECT), decision_type
(RESOLVE).

**Failure behavior:** BLOCKED on unrecognized invocation. No event appended.

---

### Phase 1 — Workspace Resolution

**Purpose:** Resolve the active workspace and construct WORKSPACE_ROOT. All subsequent
paths are prefixed with WORKSPACE_ROOT.

**Inputs:** `runtime/current_workspace.md`, `runtime/workspaces.md`.

**Steps:**

1.1 Read `runtime/current_workspace.md`. Parse `workspace_id` from:

```text
workspace_id: <value>
```

If file is absent or unreadable: BLOCKED.

1.2 Construct:

```text
WORKSPACE_ROOT = workspaces/<workspace_id>/
```

1.3 Verify `WORKSPACE_ROOT` directory exists. If not:

```text
BLOCKED — Workspace Root Not Found: workspaces/<workspace_id>/
```

1.4 Validate registry entry in `runtime/workspaces.md`:

**R4a:** Locate row where workspace_id matches 1.1 value. If absent:

```text
BLOCKED — Workspace Drift: workspace_id '<value>' not found in runtime/workspaces.md
```

**R4b:** If row `status` is `archived`:

```text
BLOCKED — Workspace Archived: workspace_id '<value>' has status 'archived'
```

If `status` is `paused` or `completed`:

```text
WARNING — Workspace status is '<status>' for workspace_id '<value>', expected 'active'
```

Proceed.

**R4c:** If `runtime_version` is absent or empty:

```text
WARNING — Registry entry incomplete: runtime_version missing for workspace_id '<value>'
```

**R4d:** If `last_active` is absent or empty:

```text
WARNING — Registry entry incomplete: last_active missing for workspace_id '<value>'
```

**R4e:** If more than one registry row has `status: active`:

```text
WARNING — Multiple active workspaces in registry. Using runtime/current_workspace.md as authority.
```

1.5 Record WORKSPACE_ROOT and workspace_id in session context.

**Outputs:** WORKSPACE_ROOT, workspace_id.

**Failure behavior:** BLOCKING on R4a, R4b(archived), absent current_workspace.md,
absent workspace root. WARNING and continue on R4b(paused/completed), R4c, R4d, R4e.

---

### Phase 2 — Artifact Discovery

**Purpose:** Verify required artifacts exist and are readable. Initialize the M13 directory and event log on first invocation.

**Inputs:** WORKSPACE_ROOT, `docs/commands/governance-resolve.md`, Policy Profile path, `WORKSPACE_ROOT/runtime/governance/`.

**Steps:**

2.1 Verify PC-01: `docs/commands/governance-resolve.md` is readable. If not: BLOCKED.

2.2 Verify `WORKSPACE_ROOT/runtime/governance/` directory:
- If directory exists: proceed.
- If directory does not exist: create it. If creation fails: BLOCKED (PC-06).

2.3 Verify PC-05: `WORKSPACE_ROOT/runtime/governance/events.md`:
- If file exists and is readable: proceed.
- If file does not exist: initialize as an empty append-only log. Record initialization in session context. If initialization fails: BLOCKED.
- If file exists and is unreadable: BLOCKED (PC-05).

2.4 Verify PC-04: Active Policy Profile is readable. If not: BLOCKED.

Attempt to read at `WORKSPACE_ROOT/governance/policy_profile.md`. Parse the active policy version into `current_policy_version`. If the file is readable but the version field is absent or empty: BLOCKED — Policy Profile version field missing.

2.5 Verify `WORKSPACE_ROOT/runtime/pipeline/events.md` (M11 event log):
- If file exists and is readable: record as available. Set `m11_events_readable = TRUE`.
- If file does not exist or is unreadable: record as unavailable. Set `m11_events_readable = FALSE`.

When `m11_events_readable = FALSE`, the associated WARNING is not emitted at Phase 2.5. It is emitted at Phase 6.4 when validity evaluation processes the flag in context. Phase 2.5 records the flag only.

M11 events.md unavailability is a WARNING condition surfaced at Phase 6.4, not BLOCKED.

**Outputs:** Confirmed readable artifacts, initialized `events.md` if new, `current_policy_version`, `m11_events_readable` flag.

**Failure behavior:** BLOCKED on PC-01, PC-04, PC-05 (unreadable), PC-06 (create fails). WARNING deferred to Phase 6.4 on M11 events.md unavailability.

---

### Phase 3 — Precondition Validation

**Purpose:** Apply mode-specific precondition checks and confirm runtime is ready to proceed.

**Inputs:** MODE, target_outcome_id, decision_type (RESOLVE), session context.

**Steps:**

3.1 For all modes: confirm WORKSPACE_ROOT, current_policy_version, and session_ref are set
in session context. If any are missing: BLOCKED — Session initialization failure.

3.2 For STATUS and VALIDATE modes: no additional preconditions. Proceed to Phase 4.

3.3 For INSPECT mode: confirm target_outcome_id is non-empty. This is enforced by Phase 0
(PC-07). Proceed to Phase 4.

3.4 For RESOLVE mode: confirm target_outcome_id and decision_type are non-empty and that
decision_type ∈ {APPROVED, REJECTED, DENIED}. Both are enforced by Phase 0 (PC-07,
PC-08). Proceed to Phase 4.

**Outputs:** Confirmation that preconditions are satisfied for the determined mode.

**Failure behavior:** BLOCKED on session context failure. Mode-specific failures already
caught by Phase 0.

---

### Phase 4 — Governance State Reconstruction

**Purpose:** Read and parse all governance events from the authoritative event log. Build the candidate outcome set from M12-produced creation events. Extract required outcome fields. The governance projection (`governance_state.md`) is never read as input to this phase.

**Inputs:** `WORKSPACE_ROOT/runtime/governance/events.md` (authoritative source).

**Steps:**

4.1 Read all events from `WORKSPACE_ROOT/runtime/governance/events.md` in chronological order. Parse each event record into a structured event object. Retain the full `event_log_chronology` in session context for use by Phase 5.

4.2 Filter the `event_log_chronology` for M12-produced outcome creation events:

```text
event_type ∈ {ESCALATION_RECORDED, DELEGATION_ASSIGNED}
```

Each such event is a candidate outcome. Build the `candidate_outcome_set`.

4.3 For each candidate outcome, extract required fields from the event record (see Reconstruction Rules Section 8). Required fields: `outcome_id`, `outcome_type`, `base`, `tier`, `policy_version`, `session_id`, `created_at`. Fields covered by pending DMAs may be absent.

If a required field is absent and is covered by a pending DMA: record a WARNING for that outcome identifying the missing field and the relevant DMA. Do not stop — continue reconstruction with available fields.

**Outputs:** `event_log_chronology` (full event sequence, retained in session context for Phase 5), `candidate_outcome_set` (M12-produced creation events with extracted fields), field-level DMA warnings.

**Failure behavior:** BLOCKED if `events.md` is unreadable (caught at Phase 2.3). WARNING for missing DMA fields — continue with available data.

---

### Phase 5 — Open Outcome Reconstruction

**Purpose:** Classify each candidate outcome from Phase 4 as OPEN or CLOSED by applying the reconstruction rules against the `event_log_chronology`. Build `OPEN_SET`, `CLOSED_SET`, and `ALL_OUTCOMES`.

**Inputs:** `candidate_outcome_set` and `event_log_chronology` (both from Phase 4). No new reads from `events.md` — uses event data already loaded in Phase 4.

**Steps:**

5.1 For each candidate outcome O in `candidate_outcome_set`, apply RR-4 (CLOSED Determination):

Search `event_log_chronology` for terminal lifecycle events with matching `outcome_id`:

```text
event_type ∈ {RESOLUTION_RECORDED, OUTCOME_SUPERSEDED, DELEGATION_EXPIRED, OUTCOME_INVALIDATED}
AND outcome_id = O.outcome_id
```

If found: outcome is CLOSED. Record `closure_path` from the terminal event's `closure_path` field. Record `closed_at` from the terminal event timestamp.

5.2 Apply RR-5 (OPEN Determination):

If no terminal lifecycle event was found for O in Step 5.1: outcome is OPEN.

5.3 Apply RR-7 (Duplicate Terminal Event Handling — Defensive):

If multiple terminal lifecycle events are found for the same `outcome_id`:
- Apply the first terminal event in chronological order.
- Record `WARNING — Duplicate closure events detected for outcome_id: <id>. First event applied. Subsequent events ignored.`
- Continue.

5.4 Build final state:

```text
OPEN_SET     = { outcomes classified OPEN in Steps 5.1—5.2 }
CLOSED_SET   = { outcomes classified CLOSED in Step 5.1 }
ALL_OUTCOMES = OPEN_SET ∪ CLOSED_SET
```

**Outputs:** `OPEN_SET`, `CLOSED_SET`, `ALL_OUTCOMES`.

**Failure behavior:** No new reads in this phase. All artifact failures are caught at Phase 4. Defensive duplicate detection produces WARNING and continues — it does not stop.

---

### Phase 6 — Validity Evaluation

**Purpose:** Evaluate all open outcomes for the three validity failure conditions. Close any outcome that fails a validity check before any mode-specific processing occurs. Validity evaluation is mandatory at every invocation in every mode.

**Inputs:** `OPEN_SET` (from Phase 5), `current_policy_version`, Policy Profile (response intervals), M11 events.md (if available), `m11_events_readable` flag.

**Execution constraint:** Phase 6 completes before Phase 7 (Mode Routing) begins. This ordering is absolute and applies in all modes.

**Steps:**

6.1 For each outcome in `OPEN_SET`, apply RD-9 (Closure Path Precedence). Evaluate all three validity conditions independently. Apply the first matching condition in the declared precedence order.

**Step 6.2 — SUPERSEDED Check (highest precedence)**

For each outcome O in `OPEN_SET` (RD-4):

```text
if O.policy_version ≠ current_policy_version:
    Execute RA-03 (Append OUTCOME_SUPERSEDED)
    Move O from OPEN_SET to CLOSED_SET with closure_path = SUPERSEDED
```

**Step 6.3 — EXPIRED Check (second precedence)**

For each outcome O remaining in `OPEN_SET` where `O.outcome_type = DELEGATION_ASSIGNED` (RD-5):

```text
elapsed_time = current_time − O.created_at
response_interval = Policy Profile terminal response interval for O.tier

if elapsed_time > response_interval:
    Execute RA-04 (Append DELEGATION_EXPIRED)
    Move O from OPEN_SET to CLOSED_SET with closure_path = EXPIRED
```

For outcomes where `O.outcome_type ≠ DELEGATION_ASSIGNED`: skip.

**Step 6.4 — INVALIDATED Check (third precedence)**

If `m11_events_readable = FALSE`:

```text
WARNING — M11 event log unreadable: session invalidation detection and base CLOSED
state detection unavailable.
Outcomes that may be incorrectly held OPEN: <list of open outcome_ids by base>
INVALIDATED check skipped. Validity coverage is reduced.

Under degraded validity coverage, SUPERSEDED and EXPIRED checks remain complete.
Only INVALIDATED detection is absent. Outcomes that would close as INVALIDATED
remain OPEN until the next invocation where M11 events.md is readable.
```

Do not stop. Proceed to Step 6.5.

If `m11_events_readable = TRUE`:

For each outcome O remaining in `OPEN_SET` (RD-6):

```text
Condition 1 — Originating session terminal:
  Find SESSION_END or SESSION_FAILED events in M11 events.md where
  session_id = O.session_id and result ∈ {FAILED, BLOCKED}.
  If found: invalidation_condition = ORIGINATING_SESSION_TERMINAL

Condition 2 — Newer M11 session exists for same base:
  Find SESSION_START events in M11 events.md where base = O.base and
  event_timestamp > O.created_at.
  If found: invalidation_condition = NEWER_SESSION_EXISTS

Condition 3 — Base CLOSED coordination state:
  Derive current coordination state of O.base from M11 events.md.
  If coordination state = CLOSED: invalidation_condition = BASE_CLOSED

if any invalidation condition holds:
    Execute RA-05 (Append OUTCOME_INVALIDATED) with the highest-precedence condition
    Move O from OPEN_SET to CLOSED_SET with closure_path = INVALIDATED
```

Invalidation condition precedence: `ORIGINATING_SESSION_TERMINAL` > `NEWER_SESSION_EXISTS` > `BASE_CLOSED`. Only the highest-precedence condition is recorded in the event.

6.5 After all three checks complete: `OPEN_SET` contains only outcomes that passed all three validity checks at this invocation time.

**Outputs:** Updated `OPEN_SET` (outcomes that passed validity), additional entries in `CLOSED_SET` (outcomes closed this invocation), `VALIDITY_CLOSURE_COUNT` (count of outcomes closed during this phase), `VALIDITY_CLOSURE_LIST` (list of `{outcome_id, closure_path}` for each outcome closed during this phase).

**Failure behavior:** BLOCKED if Policy Profile becomes unreadable mid-execution (should have been caught at Phase 2.4). WARNING if `m11_events_readable = FALSE` — INVALIDATED check skipped with coverage characterization stated above. Continue in both WARNING cases.

---

### Phase 7 — Mode Routing

**Purpose:** Route execution to the appropriate mode-specific path based on MODE and the current state of the target outcome (RESOLVE mode only).

**Inputs:** MODE, `OPEN_SET`, `CLOSED_SET`, `ALL_OUTCOMES`, `target_outcome_id` (RESOLVE/INSPECT), `VALIDITY_CLOSURE_COUNT`, `VALIDITY_CLOSURE_LIST`.

**Steps:**

7.1 Route by mode (RD-1):

**STATUS:**
Execute STATUS presentation using current `OPEN_SET`. Present each outcome with fields: `outcome_id`, `outcome_type`, `base`, `tier`, `policy_version`, `session_id`, `created_at`, and `elapsed_time` (DELEGATION_ASSIGNED only). Report `VALIDITY_CLOSURE_COUNT` and `VALIDITY_CLOSURE_LIST` for outcomes closed during Phase 6.
→ Proceed to Phase 10.

**VALIDATE:**
Phase 6 has already completed all validity closures. No additional action required. VALIDATE mode does not produce an outcome presentation table. Open outcomes are not listed. `VALIDITY_CLOSURE_COUNT` and `VALIDITY_CLOSURE_LIST` (from Phase 6) are included in the Phase 11 result report.
→ Proceed to Phase 10.

**INSPECT:**
7.2 Verify `target_outcome_id` exists in `ALL_OUTCOMES` (RD-2):
- Found: present full outcome record. Include all event fields, current state, `closure_path` (if CLOSED), and all M13-produced events with matching `outcome_id` from the event log.
- Not found: `BLOCKED — Outcome not found: <target_outcome_id>`. Stop. `RESOLUTION_RECEIVED` is not appended for this BLOCKED condition.
→ Proceed to Phase 10.

**RESOLVE:**
7.3 Verify `target_outcome_id` exists in `ALL_OUTCOMES` (RD-2):
- Not found: `BLOCKED — Outcome not found: <target_outcome_id>`. Stop. `RESOLUTION_RECEIVED` is not appended for this BLOCKED condition.

7.4 Verify `target_outcome_id` is in `OPEN_SET` (RD-3):
- Found in `OPEN_SET`: proceed to Phase 8.
- Found in `CLOSED_SET`: `BLOCKED — Outcome already closed: <target_outcome_id>. Closure path: <closure_path>.` Stop.

`RESOLUTION_RECEIVED` is not appended when BLOCKED at Step 7.4. Execution stops before Phase 8 is reached. The operator's resolution attempt leaves no record in the governance event log. This applies whether the outcome was CLOSED before this invocation began or closed during Phase 6 validity evaluation within this invocation.

**Outputs:** Presentation output (STATUS/INSPECT) or declared no-output (VALIDATE), or routing decision to Phase 8 (RESOLVE).

**Failure behavior:** BLOCKED on outcome not found (INSPECT, RESOLVE) or outcome already closed (RESOLVE). `RESOLUTION_RECEIVED` is not appended for any BLOCKED condition at Phase 7.

---

### Phase 8 — Resolution Validation

**Purpose (RESOLVE mode only):** Validate the resolution attempt for terminal authority eligibility and decision type. Append `RESOLUTION_RECEIVED` before any validation outcome is determined.

**Entry condition:** Phase 8 is reached only when Phase 7 RESOLVE routing passes — `target_outcome_id` was confirmed in `OPEN_SET`. `RESOLUTION_RECEIVED` is appended only within this phase. It is never appended for outcomes that reached BLOCKED at Phase 7.

**Inputs:** `target_outcome_id`, `decision_type`, submitter identity (from invocation context), active Policy Profile, target outcome record (from `OPEN_SET`).

**Steps:**

8.1 Retrieve outcome `O = OPEN_SET[target_outcome_id]`. Retrieve `O.tier`.

8.2 Execute RA-01 — Append `RESOLUTION_RECEIVED`. This event is appended unconditionally before validation proceeds. It records the submission attempt regardless of whether validation passes or fails.

```text
RESOLUTION_RECEIVED fields: outcome_id, decision_type (as submitted), submitter,
session_ref, timestamp.
```

8.3 Authority Eligibility Validation (RD-7):

Read the `terminal_authority_set` for tier `O.tier` from the active Policy Profile.

```text
if submitter ∈ terminal_authority_set → eligibility = ELIGIBLE
else                                   → eligibility = INELIGIBLE
```

If INELIGIBLE:
Execute RA-06 — Append `RESOLUTION_REJECTED` with reason `INELIGIBLE_AUTHORITY`.
→ Proceed to Phase 10. Session result = `VALIDATION_REJECTED`.

8.4 Terminal Decision Type Validation — Defensive (RD-8):

```text
if decision_type ∈ {APPROVED, REJECTED, DENIED} → decision_valid = TRUE
else                                              → decision_valid = FALSE
```

If `decision_valid = FALSE` (defensive guard — not reachable via CLI invocation):
Execute RA-06 — Append `RESOLUTION_REJECTED` with reason `NON_TERMINAL_DECISION_TYPE`.
→ Proceed to Phase 10. Session result = `VALIDATION_REJECTED`.

8.5 Both validations passed. Proceed to Phase 9 (Resolution Processing).

**Outputs:** `RESOLUTION_RECEIVED` event appended; `RESOLUTION_REJECTED` event appended (if validation failed); validation result (VALID or REJECTED).

**Failure behavior:** VALIDATION_FAILURE on `INELIGIBLE_AUTHORITY` or `NON_TERMINAL_DECISION_TYPE`. Always append `RESOLUTION_RECEIVED` first (EI-04).

---

### Phase 9 — Resolution Processing

**Purpose (RESOLVE mode, validation-passed path only):** Record the valid terminal
decision and transition the outcome to RESOLVED.

**Inputs:** target_outcome_id, decision_type, submitter, outcome O from OPEN_SET.

**Steps:**

9.1 Execute RA-02 — Append RESOLUTION_RECORDED.

```text
RESOLUTION_RECORDED fields: outcome_id, decision_type, submitter, session_ref,
timestamp, closure_path = RESOLVED.
```

9.2 Move outcome O from OPEN_SET to CLOSED_SET in session context. Set O.closure_path =
RESOLVED, O.decision_type = decision_type, O.closed_at = timestamp from RESOLUTION_RECORDED.

9.3 Confirm write succeeded. If RESOLUTION_RECORDED append failed:

```text
WRITE_FAILURE — RESOLUTION_RECORDED could not be appended.
outcome_id: <outcome_id>
Events appended this session before failure: RESOLUTION_RECEIVED
Projection not updated. Session result = FAILED.
```

Stop. Do not proceed to Phase 10.

**Outputs:** RESOLUTION_RECORDED event appended, outcome transitioned to CLOSED in session
context.

**Failure behavior:** WRITE_FAILURE on append failure. Report appended events and stop.

---

### Phase 10 — Projection Refresh

**Purpose:** Rebuild and write the governance outcome projection from the current derived
outcome state. Executes in all modes after all outcome operations complete.

**Inputs:** OPEN_SET, CLOSED_SET (current session state), session_ref, workspace_id,
current_policy_version.

**Execution constraint (EI-10):** Phase 10 executes only after all event appends for this
session are complete. Events are always written before the projection is updated.

**Steps:**

10.1 Build governance_state.md content (see Section 7 — Governance State Projection for
format specification).

10.2 Execute RA-07 — Write governance_state.md (overwrite).

10.3 Verify write succeeded. If write fails:

```text
WRITE_FAILURE — governance_state.md could not be written.
Events appended this session: <list>
Event log is authoritative. Projection is stale. Session result = FAILED.
```

Note: a write failure in Phase 10 does not invalidate events already appended. The event
log is the authoritative source (RR-6). The projection can be reconstructed from the event
log on the next invocation.

**Outputs:** governance_state.md written (or write failure recorded).

**Failure behavior:** WRITE_FAILURE recorded. Session result = FAILED if projection write
fails, regardless of mode.

---

### Phase 11 — Session Result Determination

**Purpose:** Determine and report the session result code based on mode and execution path.

**Inputs:** MODE, execution path taken, validation result (RESOLVE mode), write failure flag, `VALIDITY_CLOSURE_COUNT`, `VALIDITY_CLOSURE_LIST`.

**Steps:**

11.1 Apply result determination rules (RD-10):

| Condition | Session Result |
|-----------|----------------|
| Phase 10 WRITE_FAILURE | `FAILED` |
| Phase 9 WRITE_FAILURE (`RESOLUTION_RECORDED`) | `FAILED` |
| Any BLOCKED condition reached | `BLOCKED` |
| RESOLVE mode — Phase 9 completed | `RESOLUTION_COMPLETED` |
| RESOLVE mode — Phase 8 VALIDATION_FAILURE | `VALIDATION_REJECTED` |
| VALIDATE mode — Phase 10 completed | `VALIDITY_COMPLETED` |
| STATUS mode — Phase 7 completed | `STATUS_COMPLETED` |
| INSPECT mode — Phase 7 completed | `INSPECTION_COMPLETED` |

11.2 Report result. Include:
- Session result code.
- MODE.
- `session_ref`.
- `VALIDITY_CLOSURE_COUNT` (all modes) — number of outcomes closed during Phase 6.
- For `VALIDITY_COMPLETED`: `VALIDITY_CLOSURE_LIST` — for each outcome closed during Phase 6: `outcome_id` and `closure_path`. If no outcomes were closed: empty list.
- For `RESOLUTION_COMPLETED`: `outcome_id`, `decision_type`, `closure_path = RESOLVED`.
- For `VALIDATION_REJECTED`: `outcome_id`, `rejection_reason`, `submitter`.
- For `BLOCKED`: blocking condition and reason.
- For `FAILED`: write failure details.
- Any WARNINGs issued during this session.

**Outputs:** Session result code and report.

---

## 4. Phase I/O Summary

| Phase | Inputs | Outputs |
|-------|--------|---------|
| 0 | Invocation arguments | MODE, session_ref, target_outcome_id (RESOLVE/INSPECT), decision_type (RESOLVE) |
| 1 | runtime/current_workspace.md, runtime/workspaces.md | WORKSPACE_ROOT, workspace_id |
| 2 | WORKSPACE_ROOT, docs/commands/governance-resolve.md, Policy Profile path | confirmed artifacts, events.md initialized, current_policy_version, m11_events_readable |
| 3 | MODE, target_outcome_id, decision_type (RESOLVE), session context | preconditions confirmed |
| 4 | WORKSPACE_ROOT/runtime/governance/events.md | event_log_chronology, candidate_outcome_set, DMA warnings |
| 5 | candidate_outcome_set, event_log_chronology | OPEN_SET, CLOSED_SET, ALL_OUTCOMES |
| 6 | OPEN_SET, current_policy_version, Policy Profile, M11 events.md (if available) | updated OPEN_SET, updated CLOSED_SET, VALIDITY_CLOSURE_COUNT, VALIDITY_CLOSURE_LIST |
| 7 | MODE, OPEN_SET, CLOSED_SET, ALL_OUTCOMES, target_outcome_id | presentation (STATUS/INSPECT/VALIDATE) or routing to Phase 8 (RESOLVE) |
| 8 | target_outcome_id, decision_type, submitter, Policy Profile, OPEN_SET | RESOLUTION_RECEIVED appended; RESOLUTION_REJECTED (if failed); validation result |
| 9 | target_outcome_id, decision_type, submitter, OPEN_SET | RESOLUTION_RECORDED appended, outcome in CLOSED_SET |
| 10 | OPEN_SET, CLOSED_SET, session_ref, workspace_id, current_policy_version | governance_state.md written |
| 11 | MODE, execution path, write failure flag, VALIDITY_CLOSURE_COUNT, VALIDITY_CLOSURE_LIST | session result code and report |

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

## 6. Event Model

All M13-produced events are appended to `WORKSPACE_ROOT/runtime/governance/events.md`.
The event log is append-only. No existing event record is modified after it is written
(EI-06).

---

### RESOLUTION_RECEIVED

**Ownership:** M13

**Trigger:** Phase 8.2 — first action of every RESOLVE mode invocation. Appended before
any validation result is determined.

**Required fields:**

| Field | Description | Constraints |
|-------|-------------|-------------|
| `event_type` | `RESOLUTION_RECEIVED` | Literal |
| `outcome_id` | Identifier of the outcome against which resolution is submitted | Must be non-empty |
| `decision_type` | The decision type as submitted (may be non-terminal) | String |
| `submitter` | Identity of the resolution submitter | Must be non-empty |
| `timestamp` | ISO-8601 timestamp of the resolution attempt | Millisecond precision |
| `session_ref` | M13 session identifier for this invocation | From Phase 0 |

**Append semantics:** Exactly one RESOLUTION_RECEIVED per RESOLVE mode invocation. Always
appended before RESOLUTION_RECORDED or RESOLUTION_REJECTED.

---

### RESOLUTION_RECORDED

**Ownership:** M13

**Trigger:** Phase 9.1 — after both validation checks (RD-7 and RD-8) pass.

**Required fields:**

| Field | Description | Constraints |
|-------|-------------|-------------|
| `event_type` | `RESOLUTION_RECORDED` | Literal |
| `outcome_id` | Identifier of the resolved outcome | Must match a known OPEN outcome |
| `decision_type` | Terminal decision: APPROVED, REJECTED, or DENIED | Must be terminal |
| `submitter` | Identity of the resolution submitter | Must be non-empty |
| `timestamp` | ISO-8601 timestamp | Millisecond precision |
| `session_ref` | M13 session identifier | From Phase 0 |
| `closure_path` | `RESOLVED` | Literal |

**Append semantics:** Exactly one RESOLUTION_RECORDED per successful RESOLVE mode invocation.
This event is the authoritative closure record for the RESOLVED closure path.

---

### RESOLUTION_REJECTED

**Ownership:** M13

**Trigger:** Phase 8.3 (INELIGIBLE_AUTHORITY) or Phase 8.4 (NON_TERMINAL_DECISION_TYPE).

**Required fields:**

| Field | Description | Constraints |
|-------|-------------|-------------|
| `event_type` | `RESOLUTION_REJECTED` | Literal |
| `outcome_id` | Identifier of the outcome against which resolution was attempted | Must be non-empty |
| `decision_type` | The decision type as submitted | String |
| `submitter` | Identity of the resolution submitter | Must be non-empty |
| `rejection_reason` | `INELIGIBLE_AUTHORITY` or `NON_TERMINAL_DECISION_TYPE` | One of these two values |
| `timestamp` | ISO-8601 timestamp | Millisecond precision |
| `session_ref` | M13 session identifier | From Phase 0 |

**Append semantics:** Appended after RESOLUTION_RECEIVED in the same session. Outcome
remains OPEN. The target outcome's expiration timer is unaffected.

---

### OUTCOME_SUPERSEDED

**Ownership:** M13

**Trigger:** Phase 6.2 (RD-4) — policy_version mismatch detected on an OPEN outcome.

**Required fields:**

| Field | Description | Constraints |
|-------|-------------|-------------|
| `event_type` | `OUTCOME_SUPERSEDED` | Literal |
| `outcome_id` | Identifier of the superseded outcome | Must match an OPEN outcome |
| `policy_version_at_creation` | Policy Profile version recorded in the outcome creation event | From DMA-01 |
| `policy_version_current` | Current active Policy Profile version | From Phase 2.4 |
| `timestamp` | ISO-8601 timestamp | Millisecond precision |
| `session_ref` | M13 session identifier | From Phase 0 |
| `closure_path` | `SUPERSEDED` | Literal |

**Append semantics:** Closes the outcome. This event constitutes the terminal lifecycle
event for the SUPERSEDED closure path. Exactly one OUTCOME_SUPERSEDED per outcome_id.

---

### DELEGATION_EXPIRED

**Ownership:** M13

**Trigger:** Phase 6.3 (RD-5) — elapsed time exceeds response interval for a
DELEGATION_ASSIGNED outcome.

**Required fields:**

| Field | Description | Constraints |
|-------|-------------|-------------|
| `event_type` | `DELEGATION_EXPIRED` | Literal |
| `outcome_id` | Identifier of the expired outcome | Must match an OPEN DELEGATION_ASSIGNED outcome |
| `delegation_assigned_at` | Timestamp from the DELEGATION_ASSIGNED creation event | ISO-8601 |
| `response_interval` | Policy Profile-defined response interval for O.tier | Duration value |
| `elapsed_time` | Computed elapsed time: current_time − delegation_assigned_at | Duration value |
| `timestamp` | ISO-8601 timestamp of expiration detection | Millisecond precision |
| `session_ref` | M13 session identifier | From Phase 0 |
| `closure_path` | `EXPIRED` | Literal |

**Append semantics:** Closes the outcome. This event constitutes the terminal lifecycle
event for the EXPIRED closure path. Exactly one DELEGATION_EXPIRED per outcome_id.

---

### OUTCOME_INVALIDATED

**Ownership:** M13

**Trigger:** Phase 6.4 (RD-6) — one or more INVALIDATED conditions detected on an OPEN
outcome.

**Required fields:**

| Field | Description | Constraints |
|-------|-------------|-------------|
| `event_type` | `OUTCOME_INVALIDATED` | Literal |
| `outcome_id` | Identifier of the invalidated outcome | Must match an OPEN outcome |
| `invalidation_condition` | `ORIGINATING_SESSION_TERMINAL`, `NEWER_SESSION_EXISTS`, or `BASE_CLOSED` | Highest-precedence condition only |
| `timestamp` | ISO-8601 timestamp | Millisecond precision |
| `session_ref` | M13 session identifier | From Phase 0 |
| `closure_path` | `INVALIDATED` | Literal |

**Append semantics:** Closes the outcome. This event constitutes the terminal lifecycle
event for the INVALIDATED closure path. Exactly one OUTCOME_INVALIDATED per outcome_id.

---

## 7. Governance State Projection

`WORKSPACE_ROOT/runtime/governance/governance_state.md` is the M13-maintained governance
outcome projection. It is a reconstructable artifact — it is written after event appends
complete and is never read as a derivation input (EI-09).

### Cross-Runtime Write Constraint

`governance_state.md` is exclusively owned by M13. M12 must not write to `governance_state.md`. M12 records all governance evaluation state through the shared event log (`runtime/governance/events.md`) only. A write to `governance_state.md` by M12 would constitute a workspace contamination violation against M13's owned artifact.

This constraint must be verified when M12 Layer 2 is authored. If M12 Layer 2 introduces any write to `governance_state.md`, an M12 Layer 2 amendment is required before integration with M13.

### Projection Format

```markdown
# Governance Outcome State

**Version:** 1.1
**Generated:** <ISO-8601 timestamp>
**Session:** <session_ref>
**Workspace:** <workspace_id>
**Policy Profile Version:** <current_policy_version>
**Source Event Count:** <N>
**Source Last Event:** <ISO-8601 timestamp of the final event in runtime/governance/events.md at write time>

---

> **Projection watermark.** The two `Source *` fields record the state of
> `runtime/governance/events.md` at the moment this file was written. Any reader must compare
> them against that log before trusting anything below: if either differs, this projection is
> **STALE** and the event log is authoritative. See "Staleness Detection" in this section.

---

## Open Outcomes

| outcome_id | outcome_type | base | tier | policy_version | session_id | created_at | elapsed |
|------------|--------------|------|------|----------------|------------|------------|---------|
| <id>       | <type>       | <b>  | <t>  | <pv>           | <sid>      | <ts>       | <e>     |

`elapsed` is present only for DELEGATION_ASSIGNED outcomes. Format: `Xd Xh Xm` elapsed /
`Xd Xh Xm` allowed.

## Closed Outcomes

| outcome_id | outcome_type | base | closure_path | closed_at | decision_type | submitter |
|------------|--------------|------|--------------|-----------|---------------|-----------|
| <id>       | <type>       | <b>  | <path>       | <ts>      | <dt>          | <sub>     |

`decision_type` and `submitter` are populated for RESOLVED outcomes only. All other
closure paths carry `—` in these fields.

---

## Session Summary

**Open outcomes:** N
**Closed this session:** N
  - RESOLVED: N
  - SUPERSEDED: N
  - EXPIRED: N
  - INVALIDATED: N
**Total closed (all sessions):** N

---

## Warnings

<List of warnings issued during this session, if any. Empty section if none.>
```

### Staleness Detection

`governance_state.md` is a projection owned exclusively by M13 and refreshed only when M13 runs. M12 produces governance outcomes without ever writing it (AD-002, DMA-05). Between an M12 cycle and the next M13 invocation, the projection is therefore **correct as of its own watermark and wrong about the present** — and nothing in it previously said so.

The two watermark fields make the gap detectable without changing ownership:

| Field | Value at write time |
|---|---|
| `Source Event Count` | Number of event records in `runtime/governance/events.md` |
| `Source Last Event` | Timestamp of the final event in that log |

**Reader rule — binding on every consumer of this file.** Before using any content below the header, read `runtime/governance/events.md` and compare. If the current event count or final timestamp differs from the watermark, the projection is **STALE**: do not report its Open Outcomes table as the current set, and either reconstruct open outcomes directly from the event log (RR-1 / AD-001, the same reconstruction M13 performs) or state plainly that the projection predates the current state and name the watermark it carries.

A reader that cannot reconstruct must say the projection is stale. It must never present stale figures as current.

> **Why this exists.** On 2026-10-30, workspace `demo-inventory-01` carried a `governance_state.md` reporting `Open outcomes: 0` while three outcomes were open in the event log — `VD-GS-20261030-093000-001`, `VD-GS-20261030-093500-001`, `VD-GS-20261030-094000-001`. The file was correct for its own M13 session and had even been annotated by hand to explain the situation. The behaviour was exactly as specified, which is the point: the only artifact presented as a governance dashboard showed the inverse of reality to anyone who did not also read the event log, and nothing mechanical distinguished a fresh projection from a superseded one. See finding F-06 of (internal review note).
>
> The watermark is deliberately a **detection** mechanism, not a repair. Letting M12 refresh the projection would resolve the staleness and violate AD-002 / DMA-05, trading a visible inconsistency for a contaminated ownership model. A projection that can prove its own age is enough.

### Projection Write Rules

- `governance_state.md` is overwritten on every invocation.
- The watermark fields are captured **after** all event appends complete (EI-10) and immediately before the write, so they describe the log the projection was actually derived from.
- `governance_state.md` is written after all event appends are complete (EI-10).
- `governance_state.md` is derived entirely from `OPEN_SET` and `CLOSED_SET` at the end of Phase 10. It is not constructed by reading the prior `governance_state.md`.
- If `governance_state.md` does not exist, it is created. If it exists, it is overwritten.

---

## 8. Reconstruction Rules

**Authoritative source:** `WORKSPACE_ROOT/runtime/governance/events.md`

The governance projection (governance_state.md) is never read as input to reconstruction.

---

### RR-1 — Event Log as Sole Derivation Input

M13 derives all outcome state from `WORKSPACE_ROOT/runtime/governance/events.md`. No
other artifact is authoritative for outcome state. This rule holds in all phases and for
all modes.

---

### RR-2 — Candidate Outcome Discovery

Candidate outcomes are identified by reading M12-produced event types from the event log:

```text
event_type ∈ {ESCALATION_RECORDED, DELEGATION_ASSIGNED}
```

Each such event defines one candidate outcome. An outcome_id is assigned by M12 and
recorded in the creation event.

---

### RR-3 — Required Fields from Candidate Outcome Events

For each candidate outcome, extract:

| Field | Source | DMA Dependency |
|-------|--------|----------------|
| `outcome_id` | Creation event | None — assigned by M12 |
| `outcome_type` | Event type field | None |
| `base` | Creation event | Verify present; DMA candidate if absent |
| `tier` | Creation event | DMA-03 |
| `policy_version` | Creation event | DMA-01 |
| `session_id` | Creation event | DMA-02 |
| `created_at` | Creation event timestamp | None |

Fields covered by pending DMAs may be absent until the DMA is applied. Record a WARNING
for each absent required field. Continue reconstruction with available fields.

---

### RR-4 — CLOSED Determination

An outcome is CLOSED if the event log contains a terminal lifecycle event with a matching
outcome_id:

```text
event_type ∈ {RESOLUTION_RECORDED, OUTCOME_SUPERSEDED, DELEGATION_EXPIRED, OUTCOME_INVALIDATED}
AND outcome_id = candidate.outcome_id
```

Record the terminal event's closure_path and timestamp as the outcome's closure record.

---

### RR-5 — OPEN Determination

An outcome is OPEN if RR-4 finds no terminal lifecycle event for its outcome_id.

---

### RR-6 — Projection Non-Authoritative

governance_state.md is never read during RR-2 through RR-5. If governance_state.md is
absent or corrupt, reconstruction proceeds from the event log without interruption.

---

### RR-7 — Duplicate Terminal Event Handling (Defensive)

If multiple terminal lifecycle events are found for the same outcome_id (should not occur
under EI-11):

- Apply the first terminal event in chronological order.
- Record a WARNING: `WARNING — Duplicate closure events detected for outcome_id: <id>.
  First event applied. Subsequent events ignored.`
- Continue.

---

## 9. Failure Handling

### BLOCKED

Session terminates. No further phase execution.

`RESOLUTION_RECEIVED` is not appended for any BLOCKED condition. This applies to all BLOCKED cases including `BLOCKED — Outcome already closed` and `BLOCKED — Outcome not found`. Execution stops before Phase 8 is reached for any BLOCKED condition at Phase 7. An operator whose RESOLVE attempt is BLOCKED — including when the target outcome closes during Phase 6 validity evaluation within the same invocation — has no trace of the attempt in the governance event log.

| Condition | Message | Phase |
|-----------|---------|-------|
| Unrecognized invocation form | `BLOCKED — Unrecognized invocation form. See usage above.` | 0 |
| L1 contract unreadable | `BLOCKED — L1 contract not found: docs/commands/governance-resolve.md` | 2 |
| Governance event log present but unreadable | `BLOCKED — Governance event log present but unreadable` | 2 |
| Active Policy Profile unavailable | `BLOCKED — Active Policy Profile unavailable. Resolution validation and supersession detection require the Policy Profile.` | 2 |
| Governance directory creation failure | `BLOCKED — Cannot initialize M13 directory` | 2 |
| Workspace root not found | `BLOCKED — Workspace Root Not Found: workspaces/<workspace_id>/` | 1 |
| Workspace not in registry (R4a) | `BLOCKED — Workspace Drift: workspace_id '<value>' not found in runtime/workspaces.md` | 1 |
| Workspace archived (R4b) | `BLOCKED — Workspace Archived: workspace_id '<value>' has status 'archived'` | 1 |
| Session context failure | `BLOCKED — Session initialization failure` | 3 |
| Outcome not found | `BLOCKED — Outcome not found: <outcome_id>` | 7 |
| Outcome already closed | `BLOCKED — Outcome already closed: <outcome_id>. Closure path: <closure_path>.` | 7 |

---

### VALIDATION_FAILURE

Resolution attempt invalid. RESOLUTION_RECEIVED and RESOLUTION_REJECTED appended.
Outcome remains OPEN. Session continues to Phase 9, 10, 11.

| Reason Code | Condition |
|-------------|-----------|
| `INELIGIBLE_AUTHORITY` | Submitter not in terminal authority tier for O.tier per active Policy Profile |
| `NON_TERMINAL_DECISION_TYPE` | decision_type not in {APPROVED, REJECTED, DENIED} (defensive guard) |

Session result = VALIDATION_REJECTED.

---

### WARNING

Non-fatal. Session continues with reduced capability where applicable.

| Condition | Impact |
|-----------|--------|
| M11 events.md unreadable | INVALIDATED check skipped. Open outcome_ids potentially affected are listed. |
| DMA field absent in outcome creation event | Reconstruction proceeds with available fields. Affected outcome_ids listed. |
| Duplicate terminal event for same outcome_id | First event applied; subsequent ignored. |
| Workspace status paused or completed | Processing continues. Discrepancy recorded. |
| Multiple active workspaces in registry | current_workspace.md used as authority. |

All WARNINGs are included in the Phase 11 session result report and in the governance_state.md
Warnings section.

---

### WRITE_FAILURE

Event log or projection write failed.

**Event log write failure (RA-01 through RA-06):**
- Stop event processing for the affected outcome.
- For RESOLUTION_RECEIVED failure: session result = FAILED. Report failure. Do not proceed
  to RA-02 or RA-06.
- For validity closure event failure (RA-03 through RA-05): record failure for the affected
  outcome. Continue processing remaining outcomes. Include failure in Phase 11 report.
- Report all events appended in this session before failure.

**Projection write failure (RA-07):**
- Session result = FAILED.
- Do not re-attempt.
- Note: event log is authoritative. Projection is reconstructable from the event log on
  the next invocation. Data integrity is not compromised by a projection write failure.

---

## 10. Session Result Codes

| Code | Meaning | Produced In |
|------|---------|-------------|
| `RESOLUTION_COMPLETED` | RESOLVE mode — valid terminal decision accepted and recorded. Outcome closed as RESOLVED. | Phase 11 |
| `VALIDITY_COMPLETED` | VALIDATE mode — validity evaluation complete. Zero or more outcomes closed. | Phase 11 |
| `STATUS_COMPLETED` | STATUS mode — open outcomes presented. Validity evaluation completed. | Phase 11 |
| `INSPECTION_COMPLETED` | INSPECT mode — outcome detail presented. Validity evaluation completed. | Phase 11 |
| `VALIDATION_REJECTED` | RESOLVE mode — resolution attempt failed authority eligibility or decision type validation. RESOLUTION_RECEIVED and RESOLUTION_REJECTED appended. | Phase 11 |
| `BLOCKED` | Precondition failure, invocation error, or outcome state violation. Session terminated before resolution or validity processing. | Phase 11 |
| `FAILED` | Write failure on event log or governance projection. | Phase 11 |

---

## 11. Runtime Invariants

These invariants govern M13 execution. Each is derived from an L1 runtime principle (MP-01
through MP-08). An invariant violation is a NON_RECOVERABLE failure that must halt execution
immediately.

---

**Correspondence with the L1 contract `[S5-narrow finding, 2026-11-01]`.** EI-01 through EI-10 below restate, in execution-level detail, the same ten invariants the L1 contract declares as RI-01 through RI-10 — same order, same subject, this file's own vocabulary. EI-11 has no RI counterpart; it is execution-only. If this set and the L1 contract's RI-NNN set are ever edited independently, check both — they describe the same invariants from two levels of detail, not two different sets of rules.

### EI-01 — Outcome Closure Finality (MP-01)

A closed governance outcome is permanently closed. M13 never reopens a closed outcome and
never appends terminal lifecycle events that would transition a CLOSED outcome's state.

**Enforcement:** Phase 7 RESOLVE routing (RD-3) stops execution with BLOCKED if the target
outcome is CLOSED. Phase 6 validity checks skip outcomes already in CLOSED_SET.

---

### EI-02 — No Outcome Creation (MP-06)

M13 never appends ESCALATION_RECORDED or DELEGATION_ASSIGNED events. If any M13 code
path would append these event types, stop immediately and report invariant violation. This
invariant has no exceptions.

**Enforcement:** Static constraint. No M13 action (RA-01 through RA-07) appends these
event types.

---

### EI-03 — Terminal Decisions Only (MP-02)

The decision_type field in a RESOLUTION_RECORDED event must be APPROVED, REJECTED, or
DENIED. No other value is permissible.

**Enforcement:** RD-8 (defensive guard at Phase 8.4) verifies this before RA-02 executes.

---

### EI-04 — RESOLUTION_RECEIVED Before RESOLUTION_RECORDED or RESOLUTION_REJECTED (MP-07)

In every RESOLVE mode invocation, RA-01 (RESOLUTION_RECEIVED) executes before RA-02
(RESOLUTION_RECORDED) or RA-06 (RESOLUTION_REJECTED). If the ordering would be violated:
stop immediately.

**Enforcement:** Phase 8.2 executes RA-01 as its first step, before any validation result
is determined.

---

### EI-05 — Validity Evaluation Before Resolution Processing (MP-04)

Phase 6 (Validity Evaluation) completes before Phase 8 (Resolution Validation) begins in
any RESOLVE mode invocation. This ordering is absolute.

**Enforcement:** Phase sequence: Phase 6 → Phase 7 (Mode Routing) → Phase 8 (Resolution
Validation). There is no path from Phase 0 to Phase 8 that bypasses Phase 6.

---

### EI-06 — Append-Only Event Log (MP-03)

The governance event log (runtime/governance/events.md) is append-only. No existing event
record is modified after it is written. Only append operations are permitted. governance_state.md
may be overwritten; events.md may not.

**Enforcement:** RA-01 through RA-06 append only. No M13 action reads and re-writes the
event log.

---

### EI-07 — No M11 or M12 Invocation (MP-08)

M13 reads M11 events.md and governance events.md as inputs. M13 never invokes M11, M12,
or any other CSR runtime as a command.

**Enforcement:** Static constraint. Phase 6 INVALIDATED check reads M11 events.md as a
file; it does not invoke M11 as a command.

---

### EI-08 — Expiration Timer Immutable (MP-01, MP-02)

The expiration timer for a DELEGATION_ASSIGNED outcome runs from the timestamp in the
DELEGATION_ASSIGNED event created by M12. An invalid resolution attempt (RESOLUTION_REJECTED)
does not reset or extend the timer. RA-06 does not modify the DELEGATION_ASSIGNED event
record.

**Enforcement:** RD-5 derives elapsed_time from O.created_at (from the original
DELEGATION_ASSIGNED event). RESOLUTION_REJECTED does not alter O.created_at.

---

### EI-09 — Governance Projection Non-Authoritative (MP-03)

`governance_state.md` is never read during Phase 4 (Governance State Reconstruction), Phase 5 (Open Outcome Reconstruction), Phase 6 (Validity Evaluation), Phase 8 (Resolution Validation), or Phase 9 (Resolution Processing). It is written in Phase 10 (Projection Refresh) only.

**Enforcement:** Phases 4 and 5 read only `governance/events.md`. Phase 6 reads `OPEN_SET` derived in Phase 5. Phase 10 writes `governance_state.md`. No phase in the sequence reads it as input.

---

### EI-10 — Event-Before-Projection Write Ordering (MP-03)

All event appends for this session (RA-01 through RA-06) complete before RA-07 (Projection
Refresh) executes.

**Enforcement:** Phase sequence: Phase 6—9 (event appends) → Phase 10 (RA-07). There is
no path to Phase 10 that bypasses the event-appending phases.

---

### EI-11 — Single Closure Per Outcome (MP-01)

M13 appends at most one terminal lifecycle event per outcome_id. Before executing any of
RA-03, RA-04, or RA-05, M13 verifies that no prior terminal lifecycle event exists for
the target outcome_id in the event log.

**Enforcement:** RA-03, RA-04, and RA-05 each include a prior terminal event check (EI-11
guard) before appending. If a prior terminal event is found: WARNING, skip, continue.

---

## 12. Traceability Rules

### TR-1 — Outcome Lineage

Every outcome in the governance state registry traces to its M12-produced creation event
by outcome_id. The creation event carries the base, tier, policy_version, session_id, and
created_at that define the outcome's origin context.

---

### TR-2 — Resolution Lineage

Every RESOLUTION_RECORDED event traces to a preceding RESOLUTION_RECEIVED event with
matching outcome_id and session_ref in the same invocation. This linkage is verifiable by
inspecting the event log in chronological order.

---

### TR-3 — Rejection Lineage

Every RESOLUTION_REJECTED event traces to a preceding RESOLUTION_RECEIVED event with
matching outcome_id and session_ref in the same invocation. The RESOLUTION_REJECTED event
carries the rejection_reason identifying which validation check failed.

---

### TR-4 — Closure Lineage

Every CLOSED outcome traces to its terminal lifecycle event by outcome_id. The terminal
event carries the closure_path, the closing timestamp, and the session_ref of the M13
invocation that closed it. For RESOLVED outcomes, the decision_type and submitter are also
recorded.

---

### TR-5 — Session Reference

Every M13-produced event carries session_ref identifying the M13 invocation that produced
it. Given a session_ref, all events produced in that invocation are recoverable from the
event log.

---

### TR-6 — DMA Field Traceability

When DMA-01, DMA-02, and DMA-03 are applied to M12 L2:

- `policy_version` (DMA-01) becomes a verifiable field in OUTCOME_SUPERSEDED events.
- `session_id` (DMA-02) becomes a verifiable field in OUTCOME_INVALIDATED events.
- `tier` (DMA-03) becomes a verifiable field in RESOLUTION_REJECTED (INELIGIBLE_AUTHORITY)
  and RESOLUTION_RECORDED events.

Until the DMAs are applied, traceability for these fields is partial. WARNINGs issued
during Phase 4.3 record which outcomes are affected.

---

## 13. DMA Registry

The following cross-milestone amendments are required before M13 end-to-end validation.
All items are APPLIED in this materialization.

---

### DMA-01

**Source:** M13 Boundary Refinement

**Description:** M12 ESCALATION_RECORDED and DELEGATION_ASSIGNED events must include the
Policy Profile version active at outcome creation time.

**Status:** APPLIED

**Application Target:** M12 Layer 2 Amendment

**Required by:** RD-4 (SUPERSEDED check), OUTCOME_SUPERSEDED event (policy_version_at_creation
field), RR-3 (reconstruction field requirements).

---

### DMA-02

**Source:** M13 Layer 1 Contract Challenge — BF-1

**Description:** M12 ESCALATION_RECORDED and DELEGATION_ASSIGNED events must include the
M11 session_id that triggered the M12 evaluation.

**Status:** APPLIED

**Application Target:** M12 Layer 2 Amendment

**Required by:** RD-6 (INVALIDATED check, Condition 1 — originating session terminal),
RR-3 (reconstruction field requirements).

---

### DMA-03

**Source:** M13 Layer 1 Contract Challenge — BF-1

**Description:** M12 ESCALATION_RECORDED and DELEGATION_ASSIGNED events must include the
escalation or delegation tier, matching the tier label defined in the active Policy Profile.

**Status:** APPLIED

**Application Target:** M12 Layer 2 Amendment

**Required by:** RD-5 (EXPIRED check — response interval lookup by tier), RD-7 (authority
eligibility — terminal authority set lookup by tier), RR-3 (reconstruction field requirements).

---

## 4. Runtime Decisions

### RD-1 — Invocation Form Recognition

**Input:** Raw invocation string.

**Decision:**

```text
No arguments              → MODE = STATUS
"--validate"              → MODE = VALIDATE
"<id>" (single token)     → MODE = INSPECT, target_outcome_id = <id>
"<id> APPROVED"           → MODE = RESOLVE, decision_type = APPROVED
"<id> REJECTED"           → MODE = RESOLVE, decision_type = REJECTED
"<id> DENIED"             → MODE = RESOLVE, decision_type = DENIED
All other forms           → BLOCKED
```

**Outcomes:** MODE assigned; or BLOCKED.

---

### RD-2 — Outcome Existence

**Input:** target_outcome_id, ALL_OUTCOMES registry.

**Decision:**

```text
outcome_id ∈ ALL_OUTCOMES → EXISTS
outcome_id ∉ ALL_OUTCOMES → NOT_FOUND → BLOCKED
```

**Outcomes:** EXISTS or BLOCKED.

---

### RD-3 — Outcome State for RESOLVE Routing

**Input:** target_outcome_id, OPEN_SET, CLOSED_SET.

**Decision:**

```text
outcome_id ∈ OPEN_SET    → OPEN → proceed to Phase 8
outcome_id ∈ CLOSED_SET  → CLOSED → BLOCKED (already closed)
outcome_id ∉ either set  → BLOCKED (not found)
```

**Outcomes:** OPEN or BLOCKED.

---

### RD-4 — SUPERSEDED Condition

**Input:** Outcome O (OPEN), current_policy_version.

**Decision:**

```text
O.policy_version == current_policy_version → no action
O.policy_version ≠ current_policy_version  → SUPERSEDED → execute RA-03
```

Requires DMA-01 field (policy_version) in O's creation event.

**Outcomes:** SUPERSEDED or no action.

---

### RD-5 — EXPIRED Condition

**Input:** Outcome O (OPEN), current_time, Policy Profile response interval for O.tier.

**Decision:**

```text
O.outcome_type ≠ DELEGATION_ASSIGNED → skip (EXPIRED applies to DELEGATION_ASSIGNED only)
elapsed_time = current_time − O.created_at
if elapsed_time > Policy Profile response interval for O.tier → EXPIRED → execute RA-04
else → no action
```

**Outcomes:** EXPIRED or no action or skipped.

---

### RD-6 — INVALIDATED Condition

**Input:** Outcome O (OPEN), M11 events.md content (if available).

**Decision:**

```text
if m11_events_readable = FALSE:
    → skip (WARNING already issued at Phase 6.4)

Condition 1: Find M11 session terminal event where session_id = O.session_id and
             result ∈ {FAILED, BLOCKED}
             → if found: invalidation_condition = ORIGINATING_SESSION_TERMINAL → INVALIDATED

Condition 2: Find M11 SESSION_START for base = O.base where timestamp > O.created_at
             → if found: invalidation_condition = NEWER_SESSION_EXISTS → INVALIDATED

Condition 3: Derive coordination state of O.base from M11 events.md.
             → if CLOSED: invalidation_condition = BASE_CLOSED → INVALIDATED

Multiple conditions: apply highest-precedence condition only.
Precedence: ORIGINATING_SESSION_TERMINAL > NEWER_SESSION_EXISTS > BASE_CLOSED
```

Requires DMA-02 field (session_id) and DMA-03 field (base correlation) in O's creation
event.

**Outcomes:** INVALIDATED or no action or skipped.

---

### RD-7 — Authority Eligibility

**Input:** submitter identity, O.tier, active Policy Profile.

**Decision:**

```text
terminal_authority_set = Policy Profile terminal authorities for O.tier
if submitter ∈ terminal_authority_set → ELIGIBLE
else                                  → INELIGIBLE → execute RA-06 (INELIGIBLE_AUTHORITY)
```

Requires DMA-03 field (tier) in O's creation event.

**Outcomes:** ELIGIBLE or INELIGIBLE.

---

### RD-8 — Terminal Decision Type Validation (Defensive)

**Input:** decision_type.

**Decision:**

```text
decision_type ∈ {APPROVED, REJECTED, DENIED} → TERMINAL
else                                          → NON_TERMINAL → execute RA-06
```

Under conforming invocation (enforced at Phase 0), this condition is unreachable. It
exists as a defensive invariant.

**Outcomes:** TERMINAL or NON_TERMINAL.

---

### RD-9 — Closure Path Precedence

**Input:** Set of validity failures for one outcome O.

**Decision:**

```text
if SUPERSEDED condition holds: apply SUPERSEDED. Discard other conditions for O.
else if EXPIRED condition holds: apply EXPIRED. Discard INVALIDATED for O.
else if INVALIDATED condition holds: apply INVALIDATED.
else: no validity failure. O remains OPEN.
```

This implements the Closure Path Precedence Rule from L1.

**Outcomes:** One closure path applied, or no action.

---

### RD-10 — Session Result Determination

**Input:** MODE, execution path, write failures, BLOCKED conditions.

**Decision table:** See Phase 11.1.

---

## 5. Runtime Actions

### RA-01 — Append RESOLUTION_RECEIVED

**Trigger:** Phase 8.2 — first step of resolution validation in RESOLVE mode, before any
validation result is determined.

**Procedure:**
1. Construct RESOLUTION_RECEIVED event record (see Section 6).
2. Append record to `WORKSPACE_ROOT/runtime/governance/events.md`.
3. Verify append succeeded. If append fails: WRITE_FAILURE. Do not proceed.

**Invariant:** RA-01 executes before RA-02 or RA-06 in every RESOLVE mode invocation
(EI-04).

**Postcondition:** RESOLUTION_RECEIVED record exists in events.md for this outcome_id and
session_ref.

---

### RA-02 — Append RESOLUTION_RECORDED

**Trigger:** Phase 9.1 — after both validations in Phase 8 pass.

**Procedure:**
1. Construct RESOLUTION_RECORDED event record (see Section 6).
2. Append record to `WORKSPACE_ROOT/runtime/governance/events.md`.
3. Verify append succeeded. If append fails: WRITE_FAILURE.

**Invariant:** RA-01 (RESOLUTION_RECEIVED) has already been appended before RA-02 executes
(EI-04).

**Postcondition:** RESOLUTION_RECORDED record exists in events.md. Outcome transitions to
CLOSED with closure_path = RESOLVED in session context.

---

### RA-03 — Append OUTCOME_SUPERSEDED

**Trigger:** Phase 6.2 — SUPERSEDED condition confirmed for outcome O.

**Procedure:**
1. Verify EI-11: no prior terminal lifecycle event exists for O.outcome_id. If found:
   record WARNING (duplicate closure detected). Do not append. Continue to next outcome.
2. Construct OUTCOME_SUPERSEDED event record (see Section 6).
3. Append record to `WORKSPACE_ROOT/runtime/governance/events.md`.
4. Verify append succeeded. If append fails: record WRITE_FAILURE for this outcome.
   Continue processing remaining outcomes. Report failure at Phase 11.

**Postcondition:** OUTCOME_SUPERSEDED record exists in events.md. O moves to CLOSED_SET.

---

### RA-04 — Append DELEGATION_EXPIRED

**Trigger:** Phase 6.3 — EXPIRED condition confirmed for DELEGATION_ASSIGNED outcome O.

**Procedure:**
1. Verify EI-11: no prior terminal lifecycle event exists for O.outcome_id. If found:
   WARNING. Skip. Continue.
2. Construct DELEGATION_EXPIRED event record (see Section 6).
3. Append record to `WORKSPACE_ROOT/runtime/governance/events.md`.
4. Verify append succeeded. If fails: WRITE_FAILURE for this outcome. Continue.

**Postcondition:** DELEGATION_EXPIRED record exists in events.md. O moves to CLOSED_SET.

---

### RA-05 — Append OUTCOME_INVALIDATED

**Trigger:** Phase 6.4 — INVALIDATED condition confirmed for outcome O.

**Procedure:**
1. Verify EI-11: no prior terminal lifecycle event exists for O.outcome_id. If found:
   WARNING. Skip. Continue.
2. Construct OUTCOME_INVALIDATED event record (see Section 6).
3. Append record to `WORKSPACE_ROOT/runtime/governance/events.md`.
4. Verify append succeeded. If fails: WRITE_FAILURE for this outcome. Continue.

**Postcondition:** OUTCOME_INVALIDATED record exists in events.md. O moves to CLOSED_SET.

---

### RA-06 — Append RESOLUTION_REJECTED

**Trigger:** Phase 8.3 (INELIGIBLE_AUTHORITY) or Phase 8.4 (NON_TERMINAL_DECISION_TYPE).

**Procedure:**
1. Construct RESOLUTION_REJECTED event record (see Section 6) with applicable
   rejection_reason.
2. Append record to `WORKSPACE_ROOT/runtime/governance/events.md`.
3. Verify append succeeded. If fails: WRITE_FAILURE.

**Invariant:** RA-01 (RESOLUTION_RECEIVED) has already been appended before RA-06 executes
(EI-04).

**Postcondition:** RESOLUTION_REJECTED record exists in events.md. Outcome remains in
OPEN_SET unchanged. Expiration timer is not reset (EI-08).

---

### RA-07 — Refresh Governance Projection

**Trigger:** Phase 10 — after all event appends are complete.

**Procedure:**
1. Construct governance_state.md content from current OPEN_SET and CLOSED_SET (see
   Section 7 — Governance State Projection).
2. Write governance_state.md to `WORKSPACE_ROOT/runtime/governance/governance_state.md`
   (overwrite semantics).
3. Verify write succeeded. If fails: WRITE_FAILURE.

**Invariant:** RA-07 executes after all event appends for this session (EI-10).

**Postcondition:** governance_state.md reflects current outcome state. Event log remains
authoritative — projection is a reconstructable cache only.

---

## References

```text
docs/commands/governance-resolve.md          — Layer 1 Contract (authoritative)
docs/commands/governance-run.md              — M12 Layer 1 Contract (outcome creation, Verdict model)
docs/commands/pipeline-run.md               — M11 Layer 1 Contract (Governance Pause, resume detection)
docs/commands/pipeline-run_execution.md     — M11 Layer 2 (state derivation model, session event schema)
docs/governance/csr_certification_framework.md — CSR Certification Framework
docs/decisions/ADR-001-csr-language-policy.md  — language policy (canonical artifacts English; interaction surface in the user's language)
```

---

## Applied Amendments

| Amendment | Description | Applied |
|-----------|-------------|---------|
| DMA-01 | Added `policy_version` field to ESCALATION_RECORDED and DELEGATION_ASSIGNED events. Required for M13 supersession detection. | Yes |
| DMA-02 | Added `m11_session_id` field to ESCALATION_RECORDED and DELEGATION_ASSIGNED events. Required for M13 session invalidation detection. | Yes |
| DMA-03 | Added `tier` field to ESCALATION_RECORDED and DELEGATION_ASSIGNED events. Required for M13 terminal authority validation. | Yes |
