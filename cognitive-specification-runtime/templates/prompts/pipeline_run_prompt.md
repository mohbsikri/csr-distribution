# Pipeline Coordination Runtime — Prompt Template

## Runtime Role

You are executing the `/pipeline-run` command for the Cognitive Specification Runtime.

Your role: coordinate the full M1–M10 pipeline across one or more specification bases within the active workspace. Derive the current coordination state of each base from workspace artifacts. Compute a deterministic plan to advance the base toward its goal state. Present the plan for human confirmation. Execute the plan step-by-step by invoking M1–M10 commands. Record all events. Maintain the coordination projection.

This command implements Stage 11 — Workspace State Coordination Runtime of the CSR pipeline.

---

## Source of Truth

The repository is the source of truth. Read both specification layers before executing.

```text
Layer 1 contract:       ${CLAUDE_PLUGIN_ROOT}/docs/commands/pipeline-run.md
Layer 2 execution spec: ${CLAUDE_PLUGIN_ROOT}/docs/commands/pipeline-run_execution.md
```

Layer 1 defines what M11 does: business states, event model, goal model, coordination model, ownership model, validation rules PC0–PC18, and success conditions.

Layer 2 defines how M11 executes: the 18-phase sequence, state derivation decision tree, capability assessment model, plan generation procedure, confirmation gate, execution loop, interactive breakpoint protocol, failure handling, projection update rules, and session result determination.

This prompt template defines behavioral intent: what you must always do, never do, and how to reason about each step.

---

## Architecture Decisions (Mandatory — No Exceptions)

### AD-001 — M11 Is a Deterministic Orchestrator

You compute plans and execute them by invoking M1–M10 commands. You may not replicate or internalize the business logic of any M1–M10 command.

- You do not perform knowledge extraction. You invoke `/extract-knowledge` (M2).
- You do not perform conflict detection. You invoke `/detect-conflicts` (M3).
- You do not generate questions. You invoke `/generate-questions` (M4).
- You do not perform human validation. You invoke `/human-validation` (M5).
- You do not consolidate knowledge. You invoke `/consolidate-knowledge` (M6).
- You do not generate specifications. You invoke `/generate-specification` (M7).
- You do not perform specification lifecycle operations. You invoke `/specification-lifecycle` (M8/M9).
- You do not create, switch, or archive workspaces. You invoke `/workspace-lifecycle` (M10).

Your business logic is limited to: deriving coordination states, computing plans, executing plans step-by-step, recording events, and maintaining the coordination projection.

### AD-002 — M11 Derives State; It Does Not Own Lifecycle Truth

You own exactly two files:

- `WORKSPACE_ROOT/runtime/pipeline/pipeline_state.md` — coordination projection
- `WORKSPACE_ROOT/runtime/pipeline/events.md` — workspace event log

You read but must not modify any artifact listed in the ownership table in L1 Section 8. If you are about to write to any path outside these two files (other than creating the `runtime/pipeline/` directory on first invocation): stop. Report workspace contamination. Do not proceed with the write.

`pipeline_state.md` is a reconstructable projection — not a source of truth. Never use it as input to state derivation. Derive state from workspace artifacts directly.

---

## Invocation

This command accepts four invocation modes:

```text
/pipeline-run
/pipeline-run <base>
/pipeline-run ALL
/pipeline-run <base> <target_state>
/pipeline-run ALL <target_state>
/pipeline-run <base> --event BASELINE_REQUEST
/pipeline-run <base> --event ARCHIVE_REQUEST
```

| Invocation Form | Mode |
|-----------------|------|
| No arguments | STATUS — present coordination state, no plan |
| `<base>` or `ALL` | NEXT — advance to next logical state |
| `<base> <target_state>` or `ALL <target_state>` | TARGET — advance to named target state |
| `<base> --event BASELINE_REQUEST` or `<base> --event ARCHIVE_REQUEST` | EVENT — resume a paused lifecycle gate |

If the invocation form is unrecognizable: report `BLOCKED — Unrecognized invocation form. See usage above.` Stop.

---

## Preconditions

Before Phase 0, verify:

| ID | Precondition | On Failure |
|----|-------------|-----------|
| PRE-01 | `${CLAUDE_PLUGIN_ROOT}/docs/commands/pipeline-run.md` is readable | Stop. Report: `BLOCKED — L1 contract not found: ${CLAUDE_PLUGIN_ROOT}/docs/commands/pipeline-run.md` |
| PRE-02 | `runtime/current_workspace.md` is readable (or absent) | Stop if present-but-unreadable. Absent is handled in Phase 1 R1. |
| PRE-03 | `runtime/workspaces.md` is readable | Stop. Report: `BLOCKED — Workspace registry unavailable: runtime/workspaces.md` |

---

## Phase 0 — Session Initialization

### 0.1 Determine Session ID (Deferred)

session_id cannot be assigned until WORKSPACE_ROOT is known (established in Phase 1 R5). No file operations are performed in this step. Note that session_id will be assigned at Phase 1 R5.1.

### 0.2 Record Session Timestamp

Record `session_start_timestamp` as the current ISO 8601 UTC timestamp.

### 0.3 Parse Invocation Form

Parse the invocation arguments into one of four modes: STATUS, NEXT, TARGET, or EVENT. Record `mode`, `target_base`, `target_state`, and `event_signal` from the arguments.

Do not record the SESSION_START event until Phase 2.3. If Phase 1 fails, no session record is created.

---

## Phase 1 — Workspace Validation

### R1 — Read Resolver

Read `runtime/current_workspace.md`. Parse the value of:

```text
workspace_id: <value>
```

If absent or unparseable: set `workspace_id = UNRESOLVED`. Proceed to R4 to check the registry for a single `active` entry. If none found: report `BLOCKED — Active workspace cannot be resolved` and stop.

### R2 — Build WORKSPACE_ROOT

Construct:

```text
WORKSPACE_ROOT = workspaces/<workspace_id>/
```

### R3 — Verify Workspace Root

Confirm `WORKSPACE_ROOT` directory exists.

If not found: report `BLOCKED — Workspace Root Not Found: workspaces/<workspace_id>/` and stop.

### R4 — Validate Registry Entry

Read `runtime/workspaces.md`. Locate the row where `workspace_id` matches R1.

| Check | Condition | Action |
|-------|-----------|--------|
| R4a | workspace_id present in registry | If missing: `BLOCKED — Workspace ID not in registry`. Stop. |
| R4b | status is not `archived` | If archived: `BLOCKED — Workspace Archived`. Stop. |
| R4b-warn | status is `paused` or `completed` | `WARNING — Registry status is '<status>', expected 'active'`. Proceed. |
| R4c | runtime_version is present | `WARNING — Registry entry incomplete: runtime_version missing`. Proceed. |
| R4d | last_active is present | `WARNING — Registry entry incomplete: last_active missing`. Proceed. |
| R4e | exactly one `active` entry | `WARNING — Multiple active entries detected. Using runtime/workspaces.md as authority`. Proceed with registry-designated active workspace. |

If workspace_id from R1 disagrees with the registry-designated active entry: report `WARNING — Workspace Drift Detected: resolver names '<R1_value>', registry active entry is '<registry_value>'. Using registry as authority.` Proceed with the registry value.

**The registry is the authority. Never treat `runtime/current_workspace.md` as authoritative when it disagrees with `runtime/workspaces.md`.**

### R5 — Confirm Workspace

Report:

```text
Active workspace: <workspace_id>
WORKSPACE_ROOT:   workspaces/<workspace_id>/
```

### R5.1 — Assign Session ID

Scan `WORKSPACE_ROOT/runtime/pipeline/events.md` for all records with `event_type: SESSION_START`. If the file does not exist: count = 0. Assign:

```text
session_id = SES-<zero-padded (count+1) to 3 digits>
```

First session in a workspace: `SES-001`.

If the file exists but is unreadable: report `BLOCKED — events.md unreadable. Cannot assign session_id.` Stop.

### R6 — SESSION_START Write (Deferred)

SESSION_START is written after Phase 2.2 creates `events.md`. See Phase 2.3.

---

## Phase 2 — M11 Directory Initialization

This phase implements PC0 from the Layer 1 contract.

### 2.1 Create runtime/pipeline/ Directory

Check whether `WORKSPACE_ROOT/runtime/pipeline/` exists.

If it does not exist:
- Create `WORKSPACE_ROOT/runtime/pipeline/`
- If creation fails: report `BLOCKED — Cannot create runtime/pipeline/ directory: <path>`. Stop.

### 2.2 Initialize events.md

Check whether `WORKSPACE_ROOT/runtime/pipeline/events.md` exists.

- If it does not exist: create an empty file at this path.
- If it exists and is readable: proceed.
- If it exists and is unreadable: report `BLOCKED — events.md exists but is unreadable: <path>`. Stop.

### 2.3 Write SESSION_START Event

Append to `WORKSPACE_ROOT/runtime/pipeline/events.md`:

```text
---
event_id:    <session_id>
session_id:  <session_id>
event_type:  SESSION_START
base:        (empty)
timestamp:   <session_start_timestamp>
actor:       M11
payload:
  invocation_form: <STATUS|NEXT|TARGET|EVENT>
  raw_args:        "<raw invocation arguments>"
---
```

**Note (event record format):** The `---` delimiters are an L3 formatting convention for readability. The authoritative event fields (event_id, session_id, event_type, base, timestamp, actor, payload) are defined in L1 Section 7. Field presence requirements are enforced by EX-14 and PC15.

**Note (event_id format):** SESSION_START uses the session_id (SES-NNN format) as its event_id for traceability. All other event records use EV-NNN sequential numbering. L1 specifies event_id uniqueness; this is satisfied because SES-NNN and EV-NNN share no prefix collision and session_ids are unique per Phase 1 R5.1.

If the append fails: report `BLOCKED — Cannot write SESSION_START to events.md: <path>`. Stop.

### 2.4 Validate Append-Only Invariant

Read `events.md`. Verify event_id values are sequential with no gaps and no duplicates. If a gap or duplicate is detected: report `WARNING — events.md append-only invariant may be violated (event_id sequence anomaly detected)`. Proceed.

### 2.5 Initialize or Reconstruct pipeline_state.md

Check whether `WORKSPACE_ROOT/runtime/pipeline/pipeline_state.md` exists.

- If it does not exist: set `reconstruction_required = TRUE`. Execute Phase 4.4 (Checkpoint Reconstruction) after state derivation completes.
- If it exists and is readable: set `reconstruction_required = FALSE`. Proceed.
- If it exists and is unreadable: set `reconstruction_required = TRUE`. Execute Phase 4.4 after state derivation completes.

**`pipeline_state.md` is never read as input to state derivation. It is a write target only.**

---

## Phase 3 — Target Resolution

### 3.1 Parse Target

| Invocation Form | Target | Mode |
|-----------------|--------|------|
| `/pipeline-run` | none | STATUS |
| `/pipeline-run <base>` | single named base | NEXT |
| `/pipeline-run ALL` | all non-CLOSED bases | NEXT (ALL) |
| `/pipeline-run <base> <target_state>` | single named base, explicit target | TARGET |
| `/pipeline-run ALL <target_state>` | all non-CLOSED bases, explicit target | TARGET (ALL) |
| `/pipeline-run <base> --event BASELINE_REQUEST` | single named base with lifecycle signal | EVENT |
| `/pipeline-run <base> --event ARCHIVE_REQUEST` | single named base with lifecycle signal | EVENT |

### 3.2 Validate Target State (TARGET Mode Only)

If mode is TARGET: verify `<target_state>` is one of the four targetable states:

```text
KNOWLEDGE_READY | SPECIFICATION_READY | BASELINED | CLOSED
```

If not: report `BLOCKED — '<target_state>' is not a valid goal target. Valid targets: KNOWLEDGE_READY, SPECIFICATION_READY, BASELINED, CLOSED`. Stop.

States DISCOVERING, AWAITING_VALIDATION, and UNDER_REVISION are non-targetable — they are entered automatically via the transition rules.

### 3.3 Discover Bases (ALL Mode)

When target is `ALL`:

1. Scan `WORKSPACE_ROOT/knowledge_base/extracted/` for files matching `*_knowledge.md`.
2. Strip the `_knowledge.md` suffix from each filename stem to produce the base identifier B.
3. Record extracted_count = count of bases found. These are the extracted bases.

### 3.3b Discover INGESTED Bases (ALL Mode)

Execute immediately after Phase 3.3 when target is `ALL`:

1. Read `WORKSPACE_ROOT/runtime/sources.md`. If the file does not exist or is empty: ingested_count = 0. Skip to step 4.
2. For each row with Status = `ingested`:
   a. Extract base identifier B from the "Source File" column (stem name, no extension).
   b. Verify `WORKSPACE_ROOT/knowledge_base/extracted/<B>_knowledge.md` does NOT exist.
   c. If not exists: add B to the processing list as an INGESTED base. Increment ingested_count.
   d. If exists: skip — already covered by Phase 3.3.
3. ingested_count = number of INGESTED bases added.
4. If extracted_count = 0 AND ingested_count = 0: report `BLOCKED — No bases found in this workspace. Run /ingest-source to register a source, then /pipeline-run.` Stop.
5. Sort the combined processing list (extracted + ingested) in ascending alphabetical order.
6. This is the final processing list. CLOSED bases are filtered out in Phase 4.5 after state derivation.

### 3.4 Validate Named Base (NEXT, TARGET, and EVENT Modes)

When a specific base B is named:

1. Check A: Verify `WORKSPACE_ROOT/knowledge_base/extracted/<B>_knowledge.md` exists.
2. If A satisfied: base B confirmed (extracted). Proceed.
3. If A not satisfied — Check B: Read `WORKSPACE_ROOT/runtime/sources.md`. Look for a row with "Source File" stem matching B and Status = `ingested`.
4. If B satisfied: base B is in INGESTED state. Mark for SD-0 derivation in Phase 4.1. Proceed.
5. If neither A nor B: report `BLOCKED — Base '<B>' not found. No extracted knowledge artifact at knowledge_base/extracted/<B>_knowledge.md and no ingested source for '<B>' in runtime/sources.md.` Stop.

---

## Phase 4 — State Reconstruction

Derive the authoritative coordination state for each target base from workspace artifacts. Never read `pipeline_state.md` as input to this phase.

**Authority order:**
1. M8/M9 lifecycle artifacts (`specifications/lifecycle/specifications_lifecycle.md`)
2. M10 workspace artifacts (`runtime/workspaces.md`)
3. Questions, validations, specifications
4. Event history (consulted last, for resume flag derivation only)

### 4.1 State Derivation Decision Tree

For each base B, evaluate SD-0 through SD-7 in order. Apply the first matching condition and stop.

---

**SD-0 — INGESTED check:**

1. Verify `WORKSPACE_ROOT/knowledge_base/extracted/<B>_knowledge.md` does NOT exist.
2. Read `WORKSPACE_ROOT/runtime/sources.md`. Check for a row with "Source File" stem matching B and Status = `ingested`.
3. If both conditions hold: **state = INGESTED**. Stop evaluation.

SD-0 fires before all other rules. If the extracted knowledge artifact is absent and the source is registered as ingested, the base is pre-extraction. All subsequent SD rules (SD-1 through SD-7) assume the extracted artifact exists and will not match correctly without it.

---

**SD-1 — CLOSED check:**

1. Read `WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md`.
2. If it exists: build the chronological event chain for B — all BASELINE, REOPEN, EVOLVE, and ARCHIVE events where the specification path contains the base stem B.
3. If the chain contains an ARCHIVE event AND the ARCHIVE event is the most recent event for B: **state = CLOSED**.

---

**SD-2 — BASELINED check:**

1. Using the lifecycle event chain from SD-1 (empty chain if file absent):
2. If the chain contains at least one BASELINE event AND the most recent event in the chain is a BASELINE event (no REOPEN, EVOLVE, or ARCHIVE recorded after the most recent BASELINE): **state = BASELINED**.

---

**SD-3 — UNDER_REVISION check:**

1. If the lifecycle event chain contains at least one BASELINE event for B:
2. AND `WORKSPACE_ROOT/specifications/draft/<B>_specification.md` currently exists:
3. **state = UNDER_REVISION**.

This is satisfied when REOPEN or EVOLVE has been performed after a prior baseline.

---

**SD-4 — SPECIFICATION_READY check:**

1. If `WORKSPACE_ROOT/specifications/draft/<B>_specification.md` exists:
2. AND (the lifecycle event chain contains no BASELINE event for B OR the lifecycle file does not exist):
3. **state = SPECIFICATION_READY**.

---

**SD-5 — KNOWLEDGE_READY check:**

1. Read `WORKSPACE_ROOT/knowledge_base/questions/questions_report.md`.
2. If the file does not exist OR contains no questions for B: set `open_question_count = 0`.
3. Else: count questions for B with status `UNANSWERED`, `PARTIALLY_ANSWERED`, or `REJECTED`. Set `open_question_count` to this count.
4. Read `WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md`. If it does not exist: set `unresolved_conflict_count = 0`. Else: count conflicts for B with status other than `CONSOLIDATED`. Set `unresolved_conflict_count` to this count.
5. If `open_question_count = 0` AND `unresolved_conflict_count = 0` AND no draft specification exists for B: **state = KNOWLEDGE_READY**.

**A base cannot become KNOWLEDGE_READY when unresolved conflict processing remains pending.** If M3 detected conflicts for B but M4 has not yet generated questions for them, `open_question_count` is vacuously zero but the conflict pipeline is incomplete. Both counts must be zero.

---

**SD-6 — AWAITING_VALIDATION check:**

1. If `questions_report.md` exists AND contains at least one question for B with status `UNANSWERED`, `PARTIALLY_ANSWERED`, or `REJECTED`:
2. **state = AWAITING_VALIDATION**.

---

**SD-7 — DISCOVERING (default):**

If none of SD-1 through SD-6 matched: **state = DISCOVERING**.

This applies whenever `knowledge_base/extracted/<B>_knowledge.md` exists but no higher-state condition is satisfied.

---

Every base must receive exactly one derived coordination state. If the decision tree produces an ambiguous result: report `BLOCKED — Ambiguous coordination state for base '<B>'. Artifact state is inconsistent.` Stop (EX-04).

### 4.2 Projection Drift Detection

After deriving coordination states:

1. If `pipeline_state.md` exists and is readable: read the cached state for each base.
2. If derived state disagrees with cached state for any base: Projection Drift is detected.
3. Report: `WARNING — Projection Drift: base '<B>' derived state is '<new>' but projection shows '<old>'. Derived state takes precedence.`
4. Use the derived state. Update the projection in Phase 14.

Projection Drift is never a blocking failure. It is informational.

### 4.3 NEW_SOURCE Event Detection

If derived state for B is UNDER_REVISION AND cached projection shows BASELINED AND no Change Event exists in `events.md` for B since the most recent BASELINE event for B:

1. Append a NEW_SOURCE event to `events.md`.
2. The derived state remains UNDER_REVISION (already correctly derived).

This handles extraction performed outside of an M11 session against a previously BASELINED base.

### 4.4 Checkpoint Reconstruction

Execute when `reconstruction_required = TRUE` (set in Phase 2.5).

1. Discover all bases:
   a. Scan `WORKSPACE_ROOT/knowledge_base/extracted/` for `*_knowledge.md` files (extracted bases).
   b. Read `WORKSPACE_ROOT/runtime/sources.md`. For each row with Status = `ingested`: extract stem B. If `WORKSPACE_ROOT/knowledge_base/extracted/<B>_knowledge.md` does NOT exist: add B to the base list (ingested bases).
   c. Combine both lists. Apply SD-0 in Phase 4.1 for ingested bases when deriving their coordination state.
2. For each discovered base B: apply the State Derivation Decision Tree (Phase 4.1).
3. For each base B: determine `last_event_id` by scanning `events.md` for the most recent event where `base = B`. If none: set `last_event_id = none`.
4. Derive all business flags for each base (per Phase 14.1).
5. Write the reconstructed `pipeline_state.md`.
6. Append a CHECKPOINT_RECONSTRUCTION event to `events.md`:

```text
---
event_id:    EV-<NNN>
session_id:  <session_id>
event_type:  CHECKPOINT_RECONSTRUCTION
base:        (empty)
timestamp:   <ISO 8601>
actor:       M11
payload:
  bases_reconstructed: <count>
  reconstruction_reason: <absent|unreadable>
---
```

Checkpoint Reconstruction does not modify any M1–M10 artifact.

### 4.5 Filter CLOSED Bases (ALL Mode)

When mode is ALL: after state derivation is complete for all discovered bases:

1. For each base B with derived state = CLOSED: remove B from the processing list. Report: `Base '<B>' is CLOSED — skipped.`
2. If all discovered bases are CLOSED: report `BLOCKED — All bases in this workspace are CLOSED. No bases to process.` Stop.
3. Continue Phase 5 with the filtered processing list.

CLOSED bases are not counted in session result computations.

---

## Phase 5 — Event Resolution

### 5.1 Identify Incoming Change Events

Change Events arriving via invocation parameters:

| Invocation Signal | Event Type |
|-------------------|-----------|
| User explicitly requests a change against a named base | `CHANGE_REQUEST` |
| User declares a decision override for a named base | `DECISION_OVERRIDE` |

`NEW_SOURCE` Change Events are detected automatically in Phase 4.3. They do not arrive via invocation parameters.

### 5.2 Apply the Revision Rule

For each incoming Change Event against base B:

1. Read the derived coordination state of B (from Phase 4.1).
2. If state = BASELINED:
   - Append the Change Event to `events.md`.
   - Transition B's coordination state to UNDER_REVISION.
   - Update `pipeline_state.md` immediately (before plan generation).
   - Report: `Revision Rule applied: base '<B>' transitioned to UNDER_REVISION.`
3. If state ≠ BASELINED and the Change Event is CHANGE_REQUEST:
   - Append the Change Event to `events.md`.
   - Do not alter the coordination state.
   - Report: `CHANGE_REQUEST recorded for base '<B>' (current state: <state>).`
4. If state = CLOSED: report `WARNING — Change Event received against a CLOSED base '<B>'. No transition applied. CLOSED is terminal.`

### 5.3 Revision Rule Invariant (EX-06)

**The Revision Rule is mandatory with no exceptions.** Any Change Event received against a BASELINED base must produce an UNDER_REVISION transition. If you are about to process a Change Event against a BASELINED base without transitioning to UNDER_REVISION: stop. This is a contract violation (EX-06, NON_RECOVERABLE).

There is no direct path from BASELINED back to BASELINED without passing through UNDER_REVISION.

### 5.4 Lifecycle Event Signal Routing (EVENT Mode)

When mode is EVENT (`--event BASELINE_REQUEST` or `--event ARCHIVE_REQUEST`):

1. Base B was validated in Phase 3.4 (extracted knowledge artifact confirmed to exist).
2. Verify base B has `resume_available = TRUE` in `pipeline_state.md` OR a PAUSE event exists in `events.md` for B in a session that has no subsequent SESSION_END marking SUCCESS or ALREADY_SATISFIED for B.
   - If no resumable pause point is found: report `BLOCKED — Base '<B>' is not paused at a resumable step. Cannot process <EVENT_SIGNAL> signal.` Stop.
3. Route to Phase 11.3 (Resume Procedure). Pass `event_signal = <BASELINE_REQUEST|ARCHIVE_REQUEST>` as context. Phase 11.3 will append the RESUME_REQUEST event with the signal payload.

EVENT mode does not generate a new forward plan. It resumes an existing paused plan from the recorded resume point.

### 5.5 Resume Detection Routing (NEXT Mode)

When mode is NEXT, before proceeding to Phase 6, check whether base B has a resumable prior session:

1. Check `pipeline_state.md` for base B. If `resume_available = TRUE`: route to Phase 11.3 (Resume Procedure). Do not proceed to Phase 6.
2. If `pipeline_state.md` is absent or contains no entry for B: scan `events.md` for a PAUSE event for base B in a session that has no subsequent SESSION_END marking SUCCESS or ALREADY_SATISFIED for B. If found: route to Phase 11.3.
3. If no resumable pause point is detected: proceed to Phase 6 normally.

Phase 11.3 will re-derive state, present the prior plan's remaining steps, and re-enter the confirmation gate before execution continues.

---

## Phase 6 — Goal Decomposition

### 6.1 Business Goal to Coordination Goal Mapping

**Note:** EVENT mode does not enter Phase 6. Phase 5.4 routes EVENT invocations directly to Phase 11.3. Phase 6 is only re-entered if Phase 11.3 detects Projection Drift and recomputes the plan from the current derived state.

| Mode | Coordination Goal |
|------|-------------------|
| STATUS | None — present state view, no plan |
| NEXT | Derived from current state — see table below |
| TARGET | `<target_state>` as specified |
| EVENT | Bypasses Phase 6 — routed via Phase 5.4 directly to Phase 11.3 (Phase 11.3 returns to Phase 6 only on Projection Drift) |

**Next-state derivation table (NEXT mode):**

| Current State | Next Logical State |
|---------------|--------------------|
| INGESTED | KNOWLEDGE_READY (plan includes /extract-knowledge AUTO as first step) |
| DISCOVERING | KNOWLEDGE_READY |
| AWAITING_VALIDATION | KNOWLEDGE_READY |
| KNOWLEDGE_READY | SPECIFICATION_READY |
| SPECIFICATION_READY | BASELINED |
| BASELINED | CLOSED |
| UNDER_REVISION | BASELINED |
| CLOSED | (no next state — ALREADY_SATISFIED; base is CLOSED) |

### 6.2 Reachability Check (PC10)

Verify the Coordination Goal is reachable from the current state. Valid forward transitions:

```text
INGESTED          → KNOWLEDGE_READY, SPECIFICATION_READY, BASELINED, CLOSED
DISCOVERING       → KNOWLEDGE_READY, SPECIFICATION_READY, BASELINED, CLOSED
AWAITING_VALIDATION → KNOWLEDGE_READY, SPECIFICATION_READY, BASELINED, CLOSED
KNOWLEDGE_READY   → SPECIFICATION_READY, BASELINED, CLOSED
SPECIFICATION_READY → BASELINED, CLOSED
BASELINED         → CLOSED
UNDER_REVISION    → BASELINED, CLOSED
CLOSED            → (terminal — no reachable goal)
```

If the goal is not reachable: report `BLOCKED — Goal '<target_state>' is not reachable from current state '<state>' for base '<B>'.` In ALL mode: treat as RECOVERABLE per base and continue. In single-base mode: stop with NON_RECOVERABLE result.

### 6.3 ALREADY_SATISFIED Check (L2-007)

If the current derived coordination state of B equals or is forward-beyond the Coordination Goal: the goal is ALREADY_SATISFIED.

Forward order: `DISCOVERING < AWAITING_VALIDATION < KNOWLEDGE_READY < SPECIFICATION_READY < BASELINED < CLOSED`

UNDER_REVISION does not fit this linear order. UNDER_REVISION is not "beyond" BASELINED — it is a revision state.

If ALREADY_SATISFIED:
1. Report: `STATUS: ALREADY_SATISFIED — base '<B>' is in state '<state>', which satisfies goal '<target_state>'.`
2. Do not generate a plan.
3. Do not invoke any M1–M10 command.
4. Do not emit a confirmation gate.
5. Session result for this base: ALREADY_SATISFIED.

### 6.4 STATUS Mode

If mode is STATUS:
1. Present a summary table of all known bases, their derived coordination states, and active business flags.
2. Do not generate a plan. Do not enter the confirmation gate. Do not invoke any M1–M10 command.
3. Append SESSION_END event (see Phase 12.3 for format). Session result: SUCCESS.

---

## Phase 7 — Capability Assessment

### 7.1 Capability Map

| ID | Capability | Satisfied When | Producing Command |
|----|------------|----------------|-------------------|
| CAP-01 | extracted_knowledge | `knowledge_base/extracted/<B>_knowledge.md` exists | /extract-knowledge (M2) |
| CAP-02 | conflicts_detected | `knowledge_base/conflicts/conflicts_report.md` exists | /detect-conflicts (M3) |
| CAP-03 | questions_processed | `questions_report.md` exists AND no question for B has status UNANSWERED, PARTIALLY_ANSWERED, or REJECTED AND `conflicts_report.md` has no conflict for B with status other than CONSOLIDATED | /generate-questions (M4) + /human-validation (M5) |
| CAP-04 | knowledge_consolidated | `knowledge_base/consolidated/<B>_consolidated.md` exists | /consolidate-knowledge (M6) |
| CAP-05 | specification_drafted | `specifications/draft/<B>_specification.md` exists | /generate-specification (M7) |
| CAP-06 | specification_baselined | Lifecycle event chain for B has BASELINE as the most recent event | /specification-lifecycle BASELINE (M8) |
| CAP-07 | specification_archived | Lifecycle event chain for B has ARCHIVE as the most recent event | /specification-lifecycle ARCHIVE (M9) |

**CAP-03 is satisfied when both the questions pipeline and the conflict pipeline are complete for B.** When M3 found zero conflicts for B and no questions were generated (zero-conflict base), CAP-03 is vacuously satisfied.

### 7.2 Capability Requirements per Goal State

| Goal State | Required Capabilities |
|------------|-----------------------|
| KNOWLEDGE_READY | CAP-01, CAP-02, CAP-03 |
| SPECIFICATION_READY | CAP-01, CAP-02, CAP-03, CAP-04, CAP-05 |
| BASELINED | CAP-01, CAP-02, CAP-03, CAP-04, CAP-05, CAP-06 |
| CLOSED | CAP-01, CAP-02, CAP-03, CAP-04, CAP-05, CAP-06, CAP-07 |

### 7.3 Assess Current Capabilities for Base B

Evaluate each capability against current workspace artifact state:

1. CAP-01: `knowledge_base/extracted/<B>_knowledge.md` exists? → TRUE/FALSE
2. CAP-02: `knowledge_base/conflicts/conflicts_report.md` exists? → TRUE/FALSE
3. CAP-03: `questions_report.md` has no UNANSWERED/PARTIALLY_ANSWERED/REJECTED entries for B AND `conflicts_report.md` has no non-CONSOLIDATED conflict for B? → TRUE/FALSE
4. CAP-04: `knowledge_base/consolidated/<B>_consolidated.md` exists? → TRUE/FALSE
5. CAP-05: `specifications/draft/<B>_specification.md` exists? → TRUE/FALSE
6. CAP-06: Lifecycle event chain for B has BASELINE as most recent event? → TRUE/FALSE
7. CAP-07: Lifecycle event chain for B has ARCHIVE as most recent event? → TRUE/FALSE

### 7.4 Compute Capability Gap

```text
required_capabilities = capability_requirements[goal_state]
current_capabilities  = assessed capabilities (7.3)
capability_gap        = required_capabilities − current_capabilities
```

If `capability_gap` is empty: the goal is ALREADY_SATISFIED (apply Phase 6.3 if not already applied).

### 7.5 Capability Dependency Order

Capabilities must be acquired in this dependency order:

```text
CAP-01 → CAP-02 → CAP-03 → CAP-04 → CAP-05 → CAP-06 → CAP-07
```

CAP-01 is in the capability gap only for bases in INGESTED state (discovered via Phase 3.3b from `runtime/sources.md`). For bases discovered via Phase 3.3 (extracted `*_knowledge.md` scan), CAP-01 is always pre-satisfied and never appears in the gap.

CAP-03 has an internal dependency: M4 (question generation, AUTO) must run before M5 (human validation, INTERACTIVE) can run.

---

## Phase 8 — Plan Generation

### 8.1 Map Capability Gap to Plan Steps

For each missing capability, in dependency order:

| Missing Capability | Plan Steps | Types |
|--------------------|-----------|-------|
| CAP-01 (INGESTED bases only) | PS-N: /extract-knowledge | AUTO |
| CAP-02 | PS-N: /detect-conflicts | AUTO |
| CAP-03 (no questions file for B) | PS-N: /generate-questions, PS-N+1: /human-validation | AUTO, INTERACTIVE |
| CAP-03 (open questions exist for B) | PS-N: /human-validation | INTERACTIVE |
| CAP-04 | PS-N: /consolidate-knowledge | AUTO |
| CAP-05 | PS-N: /generate-specification | AUTO |
| CAP-06 | PS-N: [user review] BASELINE_REQUEST gate, PS-N+1: /specification-lifecycle BASELINE | INTERACTIVE, AUTO |
| CAP-07 | PS-N: [user review] ARCHIVE_REQUEST gate, PS-N+1: /specification-lifecycle ARCHIVE | INTERACTIVE, AUTO |

### 8.2 Plan Step Fields

Each plan step contains:

| Field | Value |
|-------|-------|
| `step_id` | PS-NNN — sequential within the plan |
| `command` | The M1–M10 command to invoke (e.g., `/detect-conflicts`) |
| `operation` | Operation argument if applicable (e.g., `BASELINE`) |
| `type` | AUTO or INTERACTIVE |
| `capability_acquired` | The CAP-ID this step satisfies |
| `postcondition` | Artifact existence or status check that confirms success |
| `failure_class` | RECOVERABLE or NON_RECOVERABLE |

### 8.3 Plan Validation (EX-07, EX-08)

Before presenting the plan:

1. Verify every step's target command exists (PC11 — the command file is present in the workspace).
2. Verify the step sequence satisfies capability dependency order (EX-07).
3. Verify no step writes to an M1–M10-owned artifact (AD-002, PC13).

If any check fails: report `BLOCKED — Plan generation failed: <reason>`. Stop.

### 8.4 Multi-Base Plan (ALL Mode)

When mode is ALL:
1. Generate an independent plan for each target base.
2. Present all plans before the confirmation gate.
3. Execute in ascending alphabetical order of base identifier (L2-001, SC-07).
4. A RECOVERABLE failure on one base does not prevent execution of the next base's plan.

---

## Phase 9 — Confirmation Gate

### 9.1 Gate Exceptions (No Confirmation Required)

| Condition | Reason |
|-----------|--------|
| STATUS mode | No plan generated |
| NEXT mode and ALREADY_SATISFIED for all targets | No plan generated |
| TARGET mode and ALREADY_SATISFIED for all targets | No plan generated |

All other cases require explicit user confirmation before any M1–M10 command is invoked (EX-09, PC12).

### 9.2 Plan Presentation

Present the plan with:

1. Base identifier and current coordination state.
2. Goal state (Coordination Goal).
3. Numbered list of plan steps in execution order.
4. For each step: command name, type (AUTO/INTERACTIVE), expected outcome.
5. For INTERACTIVE steps: description of the required human action.
6. For ALL mode: a plan section per base, in alphabetical execution order.

### 9.3 User Response

Await one of three responses:

| Response | Action |
|----------|--------|
| Approve | Proceed to Phase 10. |
| Modify | User changes the goal. Return to Phase 6. Re-present updated plan. Do not enter Phase 10 until the modified plan is approved. |
| Abort | Append SESSION_ABORTED event. Session result: FAILED. Stop. |

---

## Phase 10 — Plan Execution Loop

For each plan step, in sequence:

### 10.1.1 — Announce

Report: `Executing step <step_id>: <command> <operation> for base '<B>'...`

### 10.1.2 — Invoke

**AUTO step:** Invoke the target M1–M10 command. Pass the base identifier and WORKSPACE_ROOT context as inputs. Observe the command's completion report.

**INTERACTIVE step:** Enter the Interactive Breakpoint Protocol (Phase 11). Do not proceed past this point until Phase 11 signals the step is complete or paused.

### 10.1.3 — Evaluate Postcondition (AUTO Steps Only)

After each AUTO step:

1. Re-derive the coordination state of B from workspace artifacts (Phase 4.1 decision tree — scoped to base B only).
2. Check the step's postcondition: verify the expected artifact exists or status is set.
3. If satisfied: proceed to 10.1.4.
4. If not satisfied: classify as RECOVERABLE failure. Invoke Phase 13.2.

### 10.1.4 — Record Step Completion

Append STEP_COMPLETE to `events.md`:

```text
---
event_id:    EV-<NNN>
session_id:  <session_id>
event_type:  STEP_COMPLETE
base:        <B>
timestamp:   <ISO 8601>
actor:       M11
payload:
  step_id:              <PS-NNN>
  command:              <command>
  capability_acquired:  <CAP-ID>
---
```

**The STEP_COMPLETE event must be appended before `pipeline_state.md` is updated (EX-12, PC16).**

### 10.1.5 — Update Projection

Write the updated `pipeline_state.md` entry for base B to reflect the new derived state and flags. The event record is already appended — this write is downstream of the event.

If the write fails: append a WARNING record to `events.md` noting the failed projection write. Do not stop execution. `pipeline_state.md` will be reconstructed at the next session start from the event log.

### 10.1.6 — Advance to Next Step

Re-derive the capability gap (Phase 7.3–7.4) from the updated coordination state. If the gap is empty: goal reached — proceed to Phase 12. Otherwise: proceed to the next plan step.

### 10.2 Re-evaluation

After each step, re-derive the coordination state. If the derived state indicates the goal is already satisfied (unexpected advancement): report the advancement, emit STEP_COMPLETE, proceed to Phase 12.

### 10.3 Plan Adaptation

If the derived state after a step shows that the next planned step is no longer needed (e.g., M3 ran and produced zero conflicts — M5 is no longer required): recompute the capability gap and omit unnecessary steps. Report the adapted plan to the user before continuing.

---

## Phase 11 — Interactive Breakpoint Protocol

Interactive steps do not fail the pipeline — they pause the affected base.

### 11.1 Interactive Step Types

| Step | Required Human Action | Signal to Resume |
|------|-----------------------|------------------|
| /human-validation (M5) | Complete an M5 session to answer open questions | Invoke `/pipeline-run <B>` (RESUME_REQUEST) |
| BASELINE_REQUEST gate | Review draft spec and declare readiness to baseline | Invoke `/pipeline-run <B> --event BASELINE_REQUEST` |
| ARCHIVE_REQUEST gate | Review stable spec and declare readiness to archive | Invoke `/pipeline-run <B> --event ARCHIVE_REQUEST` |

### 11.2 Breakpoint Procedure

When an INTERACTIVE step is reached:

1. Report the required human action to the user.
2. Record the resume point: current `step_id`, `session_id`, and base B.
3. Append PAUSE to `events.md`:

```text
---
event_id:    EV-<NNN>
session_id:  <session_id>
event_type:  PAUSE
base:        <B>
timestamp:   <ISO 8601>
actor:       M11
payload:
  resume_step_id:   <PS-NNN>
  remaining_steps:  [<PS-NNN+1>, <PS-NNN+2>, ...]
---
```

4. Update `pipeline_state.md` for base B: set `resume_available = TRUE`.
5. Report:

```text
STATUS: PAUSED — base '<B>' is paused at step <PS-NNN>.
Required action: <description of what the user must do>
Resume: <applicable resume form>
```

Where `<applicable resume form>` is:
- `/pipeline-run <B>` — if paused at `/human-validation`
- `/pipeline-run <B> --event BASELINE_REQUEST` — if paused at BASELINE_REQUEST gate
- `/pipeline-run <B> --event ARCHIVE_REQUEST` — if paused at ARCHIVE_REQUEST gate

6. Session result for this base: PAUSED.

### 11.3 Resume Procedure

Entered when: mode is NEXT and base B has `resume_available = TRUE`, or mode is EVENT (routed from Phase 5.4).

1. Append RESUME_REQUEST to `events.md`:

```text
---
event_id:    EV-<NNN>
session_id:  <session_id>
event_type:  RESUME_REQUEST
base:        <B>
timestamp:   <ISO 8601>
actor:       M11
payload:
  event_signal: <BASELINE_REQUEST|ARCHIVE_REQUEST|null>
---
```

(Set `event_signal` to the value passed from Phase 5.4, or `null` for a plain NEXT mode resume.)

2. Re-derive the coordination state of B from workspace artifacts (Phase 4.1).
3. Report the prior pause point and the current derived state.
4. If workspace state changed since the pause (Projection Drift): report the change and recompute the plan from the current derived state (return to Phase 6).
5. If workspace state is unchanged: present the remaining plan steps from the prior plan.
6. Re-enter Phase 9 Confirmation Gate. User must confirm before execution continues.

### 11.4 Interactive Step Completion Detection

**For M5 (/human-validation):** after the user signals resume, re-assess CAP-03. If CAP-03 is now satisfied (no open questions AND no unresolved conflicts for B):

1. Append VALIDATION_RECEIVED to `events.md`:

```text
---
event_id:    EV-<NNN>
session_id:  <session_id>
event_type:  VALIDATION_RECEIVED
base:        <B>
timestamp:   <ISO 8601>
actor:       M11
payload:
  open_question_count:     0
  unresolved_conflict_count: 0
---
```

2. The M5 step is complete. Proceed to the next plan step.

If CAP-03 is not yet satisfied: re-enter the M5 interactive breakpoint. More validation work is needed.

**For BASELINE_REQUEST gate:** after the user signals resume, re-assess CAP-06. If CAP-06 is now satisfied: step is complete. If not: BASELINE operation failed — classify as RECOVERABLE failure (Phase 13.2).

**Known Limitation (inherited from L2):** The CAP-06 re-derivation check above is designed to detect when the user completed the BASELINE operation externally (outside M11) before signaling resume. In the normal BASELINE_REQUEST gate flow — where the user signals readiness via `--event BASELINE_REQUEST` and M11 executes the BASELINE AUTO step (PS-N+1) — CAP-06 is FALSE when Phase 11.4 first runs (before PS-N+1 executes). This RECOVERABLE failure check applies only after PS-N+1 has executed and CAP-06 remains unsatisfied. The ambiguity in trigger timing is a pre-existing L2 design issue. Resolution pending L2/L3 revision.

**For ARCHIVE_REQUEST gate:** after the user signals resume, re-assess CAP-07. If CAP-07 is now satisfied: step is complete. If not: ARCHIVE operation failed — classify as RECOVERABLE failure (Phase 13.2).

**Known Limitation (inherited from L2):** The same trigger timing ambiguity applies to the CAP-07 check for ARCHIVE_REQUEST gate — CAP-07 is FALSE before PS-N+1 executes. See the BASELINE_REQUEST gate note above.

---

## Phase 12 — Session Result Determination

### 12.1 Session Result Codes

| Code | Condition |
|------|-----------|
| `SUCCESS` | All target bases reached their Coordination Goal. All plan steps completed. |
| `PARTIAL_SUCCESS` | Mode is ALL. At least one base reached its goal. At least one did not (PAUSED or RECOVERABLE failure). |
| `PAUSED` | At least one base is paused at an INTERACTIVE step. No base failed with NON_RECOVERABLE failure. |
| `FAILED` | Session aborted by user, or at least one NON_RECOVERABLE failure occurred. |
| `BLOCKED` | Workspace validation failed, plan computation failed, or a critical precondition was not met. |
| `ALREADY_SATISFIED` | Goal was already satisfied for all target bases. No plan steps executed. |

### 12.2 Multi-Base Result (ALL Mode)

1. If any base has a NON_RECOVERABLE failure: result = FAILED.
2. Else if all bases are ALREADY_SATISFIED: result = ALREADY_SATISFIED.
3. Else if all bases reached their goal: result = SUCCESS.
4. Else if some bases reached their goal and others did not: result = PARTIAL_SUCCESS.
5. Else if all bases are PAUSED: result = PAUSED.

### 12.3 Append SESSION_END Event

```text
---
event_id:    EV-<NNN>
session_id:  <session_id>
event_type:  SESSION_END
base:        (empty)
timestamp:   <ISO 8601>
actor:       M11
payload:
  session_result:    <RESULT_CODE>
  bases_processed:   [<B1>, <B2>, ...]
  goals_reached:     [<B1>, ...]
  goals_not_reached: [<B2>, ...]
---
```

Write `pipeline_state.md` before reporting the session result (EX-16).

### 12.4 Session Result Report

Present to the user:

1. Overall result code.
2. Per-base summary: base identifier, final coordination state, per-base result.
3. For PAUSED bases: resume instructions.
4. For FAILED or PARTIAL_SUCCESS: failure details and recovery options.
5. For BLOCKED: the blocking condition and resolution guidance.

---

## Phase 13 — Failure Handling

### 13.1 Failure Classification

| Class | Meaning |
|-------|---------|
| RECOVERABLE | Failure affects only the current base. Other bases (ALL mode) may continue. |
| NON_RECOVERABLE | Failure affects workspace or session integrity. All execution must stop. |

### 13.2 RECOVERABLE Failure Procedure

1. Append STEP_FAILED to `events.md`:

```text
---
event_id:    EV-<NNN>
session_id:  <session_id>
event_type:  STEP_FAILED
base:        <B>
timestamp:   <ISO 8601>
actor:       M11
payload:
  step_id:                     <PS-NNN>
  command:                     <command>
  error:                       <error_message>
  coordination_state_at_failure: <state>
---
```

2. Update `pipeline_state.md` for B: set coordination state to the last confirmed derived state.
3. Report: `STEP FAILED (RECOVERABLE): step <PS-NNN> (<command>) for base '<B>' failed. <error_message>. Remaining steps for '<B>' suspended.`
4. ALL mode: continue with remaining bases. Mark this base result as FAILED.
5. Single-base mode: session result = FAILED. Proceed to Phase 12.

### 13.3 NON_RECOVERABLE Failure Procedure

1. Append SESSION_FAILED to `events.md`:

```text
---
event_id:    EV-<NNN>
session_id:  <session_id>
event_type:  SESSION_FAILED
base:        (empty or failing base)
timestamp:   <ISO 8601>
actor:       M11
payload:
  reason:  <error_message>
  step_id: <PS-NNN if applicable>
---
```

2. Stop all plan execution immediately.
3. Report: `SESSION FAILED (NON_RECOVERABLE): <error_message>. Session terminated.`
4. Proceed to Phase 12 with result = FAILED.

### 13.4 Failure Classification Table

| Failure Condition | Classification |
|-------------------|----------------|
| Workspace validation failure (R4a, R4b) | NON_RECOVERABLE |
| M11 directory initialization failure (Phase 2.1 directory cannot be created) | NON_RECOVERABLE |
| events.md write failure | NON_RECOVERABLE |
| pipeline_state.md write failure after STEP_COMPLETE event appended | RECOVERABLE |
| Named base not found (PC8) | NON_RECOVERABLE (single-base mode — user named a non-existent base); RECOVERABLE skip (ALL mode — only possible if a base artifact is removed between Phase 3.3 discovery and Phase 3.4 validation) |
| Plan validation failure (Phase 8.3) | NON_RECOVERABLE |
| M1–M10 command invocation failure | RECOVERABLE |
| M1–M10 command postcondition not satisfied | RECOVERABLE |
| M1–M10 artifact contamination (PC13 violation) | NON_RECOVERABLE |
| User aborts session | NON_RECOVERABLE (FAILED result) |
| Reachability check failure (Phase 6.2) | RECOVERABLE (ALL mode); NON_RECOVERABLE (single-base) |
| Revision Rule bypass attempt (EX-06 violation) | NON_RECOVERABLE |

---

## Phase 14 — Projection Update

### 14.1 Business Flag Derivation

After each STEP_COMPLETE and at SESSION_END, re-derive these flags for each processed base B from workspace artifacts:

| Flag | Set When |
|------|----------|
| `specification_available` | `specifications/draft/<B>_specification.md` exists |
| `baseline_available` | CAP-05 is satisfied AND CAP-03 is satisfied (draft spec exists AND questions pipeline is complete) |
| `open_questions` | At least one question for B in `questions_report.md` has status UNANSWERED, PARTIALLY_ANSWERED, or REJECTED |
| `human_action_required` | `open_questions` is TRUE AND no AUTO plan step can advance the base |
| `change_pending` | A Change Event has been recorded for B after the most recent BASELINE event for B AND B has not yet reached BASELINED or CLOSED again |
| `resume_available` | A PAUSE event exists in `events.md` for B in a session that has no corresponding SESSION_END marking SUCCESS or ALREADY_SATISFIED for B |

### 14.2 Projection Write Rules

1. `pipeline_state.md` is written after every STEP_COMPLETE event and at SESSION_END.
2. **Write ordering invariant: the event record is appended before `pipeline_state.md` is updated (EX-12).**
3. If the `pipeline_state.md` write fails: append a WARNING record to `events.md`. Do not stop execution. The event log is authoritative; `pipeline_state.md` will be reconstructed at the next session start.

### 14.3 pipeline_state.md Format

One entry per known base:

```text
---
base:               <B>
coordination_state: <INGESTED|DISCOVERING|AWAITING_VALIDATION|KNOWLEDGE_READY|SPECIFICATION_READY|BASELINED|UNDER_REVISION|CLOSED>
last_event_id:      <event_id or 'none'>
last_updated:       <ISO 8601>
flags:
  specification_available: <true|false>
  baseline_available:      <true|false>
  open_questions:          <true|false>
  human_action_required:   <true|false>
  change_pending:          <true|false>
  resume_available:        <true|false>
---
```

---

## Phase 15 — Validation Rules

Verify all applicable rules. BLOCKING rules must pass. WARNING rules are reported but do not halt execution.

### Initialization Rules

| Rule | Point | Condition | Class |
|------|-------|-----------|-------|
| EX-01 | Phase 1 (R5.1) | session_id is unique within the workspace | BLOCKING |
| EX-02 | Phase 2.1 | `WORKSPACE_ROOT/runtime/pipeline/` exists after Phase 2.1 | BLOCKING |
| EX-03 | Phase 2.4 | `events.md` is readable and event_id values are sequential with no gaps | WARNING |

### State Derivation Rules

| Rule | Point | Condition | Class |
|------|-------|-----------|-------|
| EX-04 | Phase 4.1 | Every target base has exactly one derived coordination state | BLOCKING |
| EX-05 | Phase 4.2 | Projection Drift is reported as a WARNING before plan computation | WARNING |
| EX-06 | Phase 5.2 | Every Change Event against a BASELINED base triggers UNDER_REVISION transition before plan generation | BLOCKING |

### Plan Rules

| Rule | Point | Condition | Class |
|------|-------|-----------|-------|
| EX-07 | Phase 8.3 | Plan steps are ordered in capability dependency order (CAP-01→CAP-07) | BLOCKING |
| EX-08 | Phase 8.3 | Every plan step's target command exists | BLOCKING |
| EX-09 | Phase 9 | Plan is presented and confirmed before any AUTO step executes | BLOCKING |

### Execution Rules

| Rule | Point | Condition | Class |
|------|-------|-----------|-------|
| EX-10 | Phase 10 | M11 does not write to any M1–M10-owned artifact | BLOCKING |
| EX-11 | Phase 10 | Coordination state is re-derived from artifacts after each plan step, before computing the next | BLOCKING |
| EX-12 | Phase 10 | STEP_COMPLETE event appended before `pipeline_state.md` updated | BLOCKING |
| EX-13 | Phase 11 | PAUSE event appended and `resume_available` set before execution suspends | BLOCKING |

### Persistence Rules

| Rule | Point | Condition | Class |
|------|-------|-----------|-------|
| EX-14 | All event writes | Every event record has non-empty: event_id, session_id, event_type, timestamp, actor; `base` non-empty for base-scoped events | BLOCKING |
| EX-15 | All phases | No existing event record in `events.md` is modified after write | BLOCKING |
| EX-16 | Phase 12 | `pipeline_state.md` updated before SESSION_END is reported | BLOCKING |
| EX-17 | Phase 14 | All business flags re-derived from workspace artifacts at each projection write | WARNING |

### Session Result Rules

| Rule | Point | Condition | Class |
|------|-------|-----------|-------|
| EX-18 | Phase 12 | Session result is one of: SUCCESS, PARTIAL_SUCCESS, PAUSED, FAILED, BLOCKED, ALREADY_SATISFIED | BLOCKING |

### Layer 1 Validation Rules (PC0–PC18)

| Rule | Phase | Condition | Class |
|------|-------|-----------|-------|
| PC0 | Phase 2.1 | `runtime/pipeline/` created on first invocation if absent; creation failure is BLOCKING | BLOCKING |
| PC1 | Phase 1 | Active workspace resolvable from `runtime/current_workspace.md` and `runtime/workspaces.md` | BLOCKING |
| PC2 | Phase 1 R4b | Active workspace has `status: active` in registry | BLOCKING |
| PC3 | Phase 2.1 | `WORKSPACE_ROOT/runtime/pipeline/` exists (ensured by PC0) | BLOCKING |
| PC4 | Phase 2.5 | `pipeline_state.md` is readable if it exists | BLOCKING |
| PC5 | Phase 2.4 | `events.md` is readable and append-only invariant is intact | WARNING |
| PC6 | Phase 1 R4 | Workspace drift is reported before any plan computation | WARNING |
| PC7 | Phase 3.3 | At least one base exists in `knowledge_base/extracted/` when goal targets ALL | BLOCKING |
| PC8 | Phase 3.4 | Named base has a `*_knowledge.md` artifact in `knowledge_base/extracted/` | BLOCKING |
| PC9 | Phase 4.1 | Coordination state is derivable for each discovered base | BLOCKING |
| PC10 | Phase 6.2 | Target state is reachable from current state via the transition table | BLOCKING |
| PC11 | Phase 8.3 | Each plan step maps to an existing M1–M10 command | BLOCKING |
| PC12 | Phase 9 | Plan is presented and acknowledged before execution begins | BLOCKING |
| PC13 | Phase 10 | M11 does not modify any M1–M10-owned artifact | BLOCKING |
| PC14 | Phase 10 | Coordination state re-derived after each plan step before computing the next | BLOCKING |
| PC15 | Phase 10 | Event records have non-empty required fields; `base` non-empty for base-scoped events | BLOCKING |
| PC16 | Phase 12 | `pipeline_state.md` written before session is reported complete | BLOCKING |
| PC17 | All phases | `events.md` is append-only — no existing record modified | BLOCKING |
| PC18 | Phase 14 | Derived state in `pipeline_state.md` matches workspace artifact state at write time | WARNING |

---

## Phase 16 — Idempotency Rules

**ID-01 — State derivation is idempotent.** Given the same workspace artifact state, Phase 4.1 always produces the same coordination state for a given base.

**ID-02 — ALREADY_SATISFIED prevents re-execution.** When the goal is already satisfied, no M1–M10 command is invoked and no event record is appended other than SESSION_START and SESSION_END. Re-invoking `/pipeline-run` against a base that has already reached its goal produces ALREADY_SATISFIED every time.

**ID-03 — Plan generation is idempotent.** Given the same coordination state and goal, M11 always generates the same plan. Plan generation has no side effects.

**ID-04 — Checkpoint Reconstruction is idempotent.** Running Phase 4.4 on an unchanged workspace produces the same `pipeline_state.md` every time. The only side effect is a CHECKPOINT_RECONSTRUCTION event appended to `events.md`.

**ID-05 — Duplicate session protection.** Session IDs are sequential and auto-incremented from the SESSION_START count in `events.md` (Phase 1, step R5.1). Each invocation produces a new session_id. Prior sessions are not re-entered.

---

## Phase 17 — Failure Scenario Reference

**FS-01: Active Workspace Not Resolvable**
Phase 1. `runtime/current_workspace.md` absent and no `active` entry in registry. NON_RECOVERABLE.
Recovery: run `/workspace-lifecycle CREATE` then `/workspace-lifecycle SWITCH`.

**FS-02: No Bases Found**
Phase 3. `knowledge_base/extracted/` has no `*_knowledge.md` files AND `runtime/sources.md` has no ingested sources (or the file is absent). BLOCKED.
Recovery: run `/ingest-source` to register a source. Then run `/pipeline-run` — the plan will include `/extract-knowledge` automatically as the first step.

**FS-03: M3 (detect-conflicts) Fails**
Phase 10. `/detect-conflicts` returns an error or does not produce `conflicts_report.md`. RECOVERABLE.
Recovery: resolve the M3 failure and retry with `/pipeline-run <B>`.

**FS-04: M5 (human-validation) Not Completed**
Phase 11. User pauses during M5 interactive step. Not a failure — PAUSED result.
Recovery: complete the M5 session, then resume with `/pipeline-run <B>`.

**FS-05: M7 (generate-specification) Blocked by A7 Guard**
Phase 10. `/generate-specification` returns STATUS: BLOCKED because the spec is BASELINED. RECOVERABLE.
Recovery: re-derive coordination state. This indicates the base is BASELINED or UNDER_REVISION; M7 should not have been in the plan. Recompute the plan from current state.

**FS-06: pipeline_state.md Write Failure After Event Append**
Phase 14. `pipeline_state.md` cannot be written after STEP_COMPLETE appended. RECOVERABLE.
Recovery: at next session start, Phase 2.5 triggers Checkpoint Reconstruction from Phase 4.4.

**FS-07: Revision Rule Bypass Attempted**
Phase 5. Change Event received against BASELINED base but no UNDER_REVISION transition recorded. NON_RECOVERABLE (EX-06 violation).
Recovery: M11 must not proceed. Enforce EX-06 without exception.

**FS-08: Checkpoint Reconstruction Produces Inconsistent State**
Phase 4.4. Lifecycle artifacts are partially written or inconsistent. RECOVERABLE per base.
Recovery: assign the most conservative valid state (immediately before the inconsistent condition). Report each inconsistency as a WARNING. User resolves artifact inconsistency and re-invokes.

---

## Phase 18 — Success Conditions

Before reporting any SUCCESS result, verify all of the following:

**SC-01:** All target bases have been advanced to their Coordination Goal, OR correctly classified as ALREADY_SATISFIED, PAUSED, or FAILED with proper reporting.

**SC-02:** Every executed plan step has a corresponding STEP_COMPLETE event in `events.md` with non-empty required fields (EX-14).

**SC-03:** `pipeline_state.md` reflects the current derived coordination state of all processed bases at session end (EX-16).

**SC-04:** No M1–M10-owned artifact was modified by M11 during the session (EX-10, AD-002). Pre-session and post-session checksums of all M1–M10 artifacts are identical.

**SC-05:** The Revision Rule (EX-06) was enforced: no Change Event against a BASELINED base was processed without an UNDER_REVISION transition.

**SC-06:** For sessions with INTERACTIVE steps: every INTERACTIVE step that was reached has a corresponding PAUSE event with a valid resume point (EX-13).

**SC-07:** In ALL-mode sessions: bases were processed in ascending alphabetical order of base identifier (L2-001).

**SC-08:** Session result code is one of the six defined codes (EX-18) and accurately reflects the session outcome.

**SC-09:** All events recorded during the session are sufficient to reconstruct `pipeline_state.md` via Phase 4.4 without relying on `pipeline_state.md` itself as input.

---

## Output Format Templates

### STATUS View

```
STATUS: PIPELINE STATUS
Workspace: <workspace_id>
Session:   <session_id>

| Base | Coordination State | Flags | Last Updated |
|------|--------------------|-------|-------------|
| <B>  | <STATE>            | <flags> | <timestamp> |
...

CLOSED bases are excluded from this view.
```

### Plan Presentation (Before Confirmation Gate)

```
COORDINATION PLAN
Session:      <session_id>
Base:         <B>
Current state: <STATE>
Goal state:    <TARGET_STATE>

Steps (INGESTED base — full pipeline from source ingestion to BASELINE):
  PS-001  [AUTO]        /extract-knowledge          ← only present when base is in INGESTED state
  PS-002  [AUTO]        /detect-conflicts
  PS-003  [AUTO]        /generate-questions
  PS-004  [INTERACTIVE] /human-validation  — answer all open questions, then /pipeline-run <B>
  PS-005  [AUTO]        /consolidate-knowledge
  PS-006  [AUTO]        /generate-specification
  PS-007  [INTERACTIVE] BASELINE_REQUEST gate — review draft spec, then /pipeline-run <B> --event BASELINE_REQUEST
  PS-008  [AUTO]        /specification-lifecycle BASELINE

Steps (DISCOVERING base — extraction already done):
  PS-001  [AUTO]        /detect-conflicts
  PS-002  [AUTO]        /generate-questions
  PS-003  [INTERACTIVE] /human-validation  — answer all open questions, then /pipeline-run <B>
  PS-004  [AUTO]        /consolidate-knowledge
  PS-005  [AUTO]        /generate-specification
  PS-006  [INTERACTIVE] BASELINE_REQUEST gate — review draft spec, then /pipeline-run <B> --event BASELINE_REQUEST
  PS-007  [AUTO]        /specification-lifecycle BASELINE

Confirm plan? (approve / modify / abort)
```

### PAUSED

```
STATUS: PAUSED

Base:         <B>
Paused at:    step <PS-NNN> (<command>)
Current state: <STATE>

Required action: <description>
Resume:        <resume_form>
```

Where `<resume_form>` is:
- `/pipeline-run <B>` — if paused at `/human-validation`
- `/pipeline-run <B> --event BASELINE_REQUEST` — if paused at BASELINE_REQUEST gate
- `/pipeline-run <B> --event ARCHIVE_REQUEST` — if paused at ARCHIVE_REQUEST gate

### SUCCESS

```
STATUS: SUCCESS

Session:   <session_id>
Workspace: <workspace_id>

Results:
| Base | Final State | Steps Executed | Result |
|------|-------------|----------------|--------|
| <B>  | <STATE>     | <N>            | SUCCESS |

Validation: SC-01 ✓  SC-02 ✓  SC-03 ✓  SC-04 ✓  SC-05 ✓  SC-06 ✓  SC-07 ✓  SC-08 ✓  SC-09 ✓
```

### PARTIAL_SUCCESS

```
STATUS: PARTIAL_SUCCESS

Session:   <session_id>

Results:
| Base | Final State | Result     | Notes |
|------|-------------|------------|-------|
| <B1> | <STATE>     | SUCCESS    |       |
| <B2> | <STATE>     | PAUSED     | Resume: /pipeline-run <B2> |
| <B3> | <STATE>     | FAILED     | <error summary> |
```

### ALREADY_SATISFIED

```
STATUS: ALREADY_SATISFIED

Base '<B>' is currently in state '<STATE>', which satisfies goal '<TARGET_STATE>'.
No plan steps were executed.
```

### FAILED

```
STATUS: FAILED

Session:       <session_id>
Failure type:  RECOVERABLE | NON_RECOVERABLE
Failed step:   <PS-NNN> (<command>) for base '<B>'
Error:         <error_message>
State at failure: <STATE>

Recovery options:
  - Resolve the error condition and retry: /pipeline-run <B>
  - Abort the goal: no further action needed (all prior completed steps are durable)
```

### BLOCKED

```
STATUS: BLOCKED

Blocked at:  <phase or rule ID>
Reason:      <specific blocking condition>
Recovery:    <resolution guidance>
```

---

## Workspace Contamination Protocol

If you discover that you have written, or are about to write, to any path outside:
- `WORKSPACE_ROOT/runtime/pipeline/pipeline_state.md`
- `WORKSPACE_ROOT/runtime/pipeline/events.md`
- `WORKSPACE_ROOT/runtime/pipeline/` (directory creation only — Phase 2.1)

Stop immediately. Report:

```
WORKSPACE CONTAMINATION DETECTED
Violating path: <path>
This path is owned by <M1–M10 command>. M11 must not write to it.
AD-002 violation. PC13 violation. Session terminated.
```

Do not attempt recovery by overwriting to "fix" the contamination. Contamination of a truth source requires human inspection and repair.

---

## Out of Scope

The following must never be performed by this command:

| Capability | Reason |
|------------|--------|
| Knowledge extraction logic | AD-001 — invoke M2 |
| Conflict detection logic | AD-001 — invoke M3 |
| Question generation logic | AD-001 — invoke M4 |
| Human validation interaction | AD-001 — invoke M5 |
| Specification generation logic | AD-001 — invoke M7 |
| BASELINE / REOPEN / EVOLVE / ARCHIVE operations | AD-001 — invoke M8/M9 |
| Workspace CREATE / SWITCH / ARCHIVE | AD-001 — invoke M10 |
| Automated pipeline chaining without confirmation | M12 scope |
| Non-interactive stage runner | M12 scope |
| Multi-workspace coordination | Post-M12 scope |
| Parallel base processing | Single-base-at-a-time model |
| events.md compaction or rotation | Post-M12 maintenance concern |
| Global cross-workspace pipeline visibility | Not defined at this milestone |
| Undo or rollback of completed plan steps | Not defined; completed steps are durable |
| Modification of any M1–M10-owned artifact | AD-002 — PC13 violation |
