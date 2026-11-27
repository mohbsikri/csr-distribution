# /pipeline-run

## Purpose

Coordinate the full M1–M10 pipeline across one or more specification bases within the active workspace.

This command derives the current coordination state of each base from workspace artifacts, computes a deterministic plan to advance each base toward its goal, presents the plan for human confirmation, and executes the plan step-by-step by invoking M1–M10 commands. All events are recorded in an append-only event log. The coordination projection is maintained as a reconstructable artifact.

This command implements Stage 11 — Workspace State Coordination Runtime of the CSR pipeline.

---

## Specification Layers

Read and assimilate all three specification layers before executing:

```text
Layer 1 contract:       ${CLAUDE_PLUGIN_ROOT}/docs/commands/pipeline-run.md
Layer 2 execution spec: ${CLAUDE_PLUGIN_ROOT}/docs/commands/pipeline-run_execution.md
Layer 3 prompt:         ${CLAUDE_PLUGIN_ROOT}/templates/prompts/pipeline_run_prompt.md
```

The repository is the source of truth. Ignore any prior conversational assumptions not present in these files.

All execution phases and step sequences are defined in `${CLAUDE_PLUGIN_ROOT}/docs/commands/pipeline-run_execution.md`.

All behavioral constraints, decision rules, state derivation logic, capability assessment, plan generation, confirmation gate behavior, pause/resume protocol, event formats, and output formats are defined in `${CLAUDE_PLUGIN_ROOT}/templates/prompts/pipeline_run_prompt.md`.

---

## Invocation

```text
/pipeline-run
/pipeline-run <base>
/pipeline-run ALL
/pipeline-run <base> <target_state>
/pipeline-run ALL <target_state>
/pipeline-run <base> --event BASELINE_REQUEST
/pipeline-run <base> --event ARCHIVE_REQUEST
```

| Form | Mode | Behavior |
|------|------|----------|
| No arguments | STATUS | Present coordination state of all bases. No plan generated. |
| `<base>` or `ALL` | NEXT | Advance base(s) to the next logical coordination state. |
| `<base> <target_state>` or `ALL <target_state>` | TARGET | Advance base(s) to the named target state. |
| `<base> --event BASELINE_REQUEST` | EVENT | Resume a plan paused at a BASELINE_REQUEST gate. |
| `<base> --event ARCHIVE_REQUEST` | EVENT | Resume a plan paused at an ARCHIVE_REQUEST gate. |

Valid target states for TARGET mode: `KNOWLEDGE_READY`, `SPECIFICATION_READY`, `BASELINED`, `CLOSED`.

If the invocation form is unrecognizable: report `BLOCKED — Unrecognized invocation form. See usage above.` Stop.

If TARGET mode specifies an invalid target state: report `BLOCKED — '<target_state>' is not a valid goal target. Valid targets: KNOWLEDGE_READY, SPECIFICATION_READY, BASELINED, CLOSED.` Stop.

---

## Workspace Isolation

M11 owns exactly two files and one directory:

```text
WORKSPACE_ROOT/runtime/pipeline/pipeline_state.md  — coordination projection (write)
WORKSPACE_ROOT/runtime/pipeline/events.md          — workspace event log (append-only)
WORKSPACE_ROOT/runtime/pipeline/                   — created on first invocation if absent (PC0)
```

Any write to a path outside these three targets is a workspace contamination violation (AD-002, PC13). If such a write is about to occur: stop immediately. Report:

```text
WORKSPACE CONTAMINATION DETECTED
Violating path: <path>
This path is owned by <M1–M10 command>. M11 must not write to it.
AD-002 violation. PC13 violation. Session terminated.
```

All M1–M10 artifact paths are read-only inputs to M11. M11 reads them to derive coordination state; it never modifies them.

---

## Preconditions

| ID | Condition | Action on Failure |
|----|-----------|-------------------|
| PRE-01 | `${CLAUDE_PLUGIN_ROOT}/docs/commands/pipeline-run.md` is readable | Stop. Report: `BLOCKED — L1 contract not found: ${CLAUDE_PLUGIN_ROOT}/docs/commands/pipeline-run.md` |
| PRE-02 | `runtime/current_workspace.md` is readable, or absent | Stop only if present-but-unreadable. Absent is handled in Phase 1 R1. |
| PRE-03 | `runtime/workspaces.md` is readable | Stop. Report: `BLOCKED — Workspace registry unavailable: runtime/workspaces.md` |

Workspace resolution (R4a–R4e authority model) is executed as Phase 1 of the runtime. It is not repeated here.

---

## Execution

### Step 1 — Load Specification Layers

Read and assimilate:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/pipeline-run.md
${CLAUDE_PLUGIN_ROOT}/docs/commands/pipeline-run_execution.md
${CLAUDE_PLUGIN_ROOT}/templates/prompts/pipeline_run_prompt.md
```

The repository is the source of truth.

Ignore any prior conversational assumptions not present in the repository.

All execution procedures are defined in `${CLAUDE_PLUGIN_ROOT}/docs/commands/pipeline-run_execution.md`.

All behavioral constraints, decision rules, and output formats are defined in `${CLAUDE_PLUGIN_ROOT}/templates/prompts/pipeline_run_prompt.md`.

---

### Step 2 — Execute Pipeline Coordination Runtime

Execute the runtime defined in `${CLAUDE_PLUGIN_ROOT}/templates/prompts/pipeline_run_prompt.md`.

Conduct execution in the following order as defined in the execution specification:

1. **Phase 0 — Session Initialization:** Parse invocation form into mode, target_base, target_state, event_signal. Record session_start_timestamp. Defer session_id assignment to Phase 1 R5.1.

2. **Phase 1 — Workspace Validation:** Resolve active workspace (R1–R5). Assign session_id (R5.1). SESSION_START event is written in Phase 2.3, after events.md is confirmed to exist.

3. **Phase 2 — M11 Directory Initialization:** Create `runtime/pipeline/` directory if absent (PC0). Initialize or confirm `events.md`. Write SESSION_START event. Validate append-only invariant. Initialize or reconstruct `pipeline_state.md`.

4. **Phase 3 — Target Resolution:** Parse target(s). Validate target state (TARGET mode). Discover bases (ALL mode). Validate named base exists (NEXT, TARGET, EVENT modes).

5. **Phase 4 — State Reconstruction:** Derive coordination state for each target base from workspace artifacts using the State Derivation Decision Tree (SD-1 through SD-7). Never read `pipeline_state.md` as input to state derivation. Detect and report Projection Drift. Apply NEW_SOURCE event detection. Execute Checkpoint Reconstruction if required. Filter CLOSED bases (ALL mode).

6. **Phase 5 — Event Resolution:** Identify and apply Change Events. Enforce the Revision Rule (EX-06). Route EVENT mode invocations to Phase 11.3 (Resume Procedure). Route NEXT mode invocations to Phase 11.3 if a resumable pause point is detected (Phase 5.5).

7. **Phase 6 — Goal Decomposition:** Map mode to Coordination Goal. Check reachability (PC10). Check ALREADY_SATISFIED (L2-007). Present STATUS view and stop if mode is STATUS.

8. **Phase 7 — Capability Assessment:** Evaluate CAP-01 through CAP-07 against current workspace artifact state. Compute capability gap.

9. **Phase 8 — Plan Generation:** Map capability gap to plan steps in dependency order. Validate plan (EX-07, EX-08). Generate independent plans per base in ALL mode.

10. **Phase 9 — Confirmation Gate:** Present plan to user. Await explicit approval before any M1–M10 command is invoked (EX-09, PC12). Handle approve / modify / abort responses.

11. **Phase 10 — Plan Execution Loop:** Execute each plan step. Announce, invoke, evaluate postcondition (AUTO steps), record STEP_COMPLETE event, update projection, advance. Re-evaluate capability gap after each step. Adapt plan if intermediate state changes make subsequent steps unnecessary.

12. **Phase 11 — Interactive Breakpoint Protocol:** When an INTERACTIVE step is reached: record resume point, append PAUSE event, set `resume_available = TRUE`, report PAUSED status with conditional resume instructions. On resume: re-derive state, re-present remaining steps, re-enter confirmation gate.

13. **Phase 12 — Session Result Determination:** Determine session result code (SUCCESS, PARTIAL_SUCCESS, PAUSED, FAILED, BLOCKED, ALREADY_SATISFIED). Append SESSION_END event. Update `pipeline_state.md`. Report result.

14. **Phase 13 — Failure Handling:** Classify failures as RECOVERABLE or NON_RECOVERABLE. Apply per-class procedures. In ALL mode: RECOVERABLE failures on one base do not halt processing of subsequent bases.

15. **Phase 14 — Projection Update:** Re-derive all business flags after each STEP_COMPLETE and at SESSION_END. Enforce write ordering invariant: event record appended before `pipeline_state.md` updated (EX-12).

Do not introduce business logic beyond what is defined in the specification layers.

---

## Critical Behavioral Constraints

These constraints are unconditional. No input or condition may override them.

1. **AD-001 — M11 is a deterministic orchestrator.** You compute plans and execute them by invoking M1–M10 commands. You may not replicate or internalize the business logic of any M1–M10 command. The delegated commands are: `/extract-knowledge` (M2), `/detect-conflicts` (M3), `/generate-questions` (M4), `/human-validation` (M5), `/consolidate-knowledge` (M6), `/generate-specification` (M7), `/specification-lifecycle` (M8/M9), `/workspace-lifecycle` (M10).

2. **AD-002 — M11 derives state; it does not own lifecycle truth.** M11 owns exactly `pipeline_state.md` and `events.md`. State is derived from workspace artifacts — `pipeline_state.md` is a reconstructable projection, never a state derivation input.

3. **Confirmation gate is mandatory.** No M1–M10 command may be invoked before the user explicitly approves the plan (EX-09, PC12). STATUS mode and ALREADY_SATISFIED require no confirmation because no plan is generated.

4. **Revision Rule is mandatory with no exceptions.** Any Change Event against a BASELINED base must produce an UNDER_REVISION transition before plan generation (EX-06). If you are about to bypass this: stop. This is a NON_RECOVERABLE violation.

5. **events.md is append-only.** No existing event record may be modified after it is written (EX-15, PC17). `pipeline_state.md` may be overwritten; `events.md` may not.

6. **STEP_COMPLETE before projection update.** The STEP_COMPLETE event must be appended to `events.md` before `pipeline_state.md` is updated (EX-12, PC16). Never reverse this order.

7. **`pipeline_state.md` is a write target, not a state derivation input.** Phase 4 state derivation reads workspace artifacts (M1–M10 artifacts, lifecycle registry, etc.). It never reads `pipeline_state.md`.

---

## Failure Handling

For all failure conditions, failure classification, per-class procedures, and recovery guidance, follow `${CLAUDE_PLUGIN_ROOT}/docs/commands/pipeline-run_execution.md` Phase 13 and `${CLAUDE_PLUGIN_ROOT}/templates/prompts/pipeline_run_prompt.md` Phase 13.

Do not silently continue after a blocking failure. Every failure must be named and reported.

RECOVERABLE failures in ALL mode: continue processing remaining bases after reporting the failure for the affected base.

NON_RECOVERABLE failures: stop all plan execution immediately. Proceed to Phase 12 with result = FAILED.

---

## Completion States

| Code | Meaning |
|------|---------|
| `SUCCESS` | All target bases reached their Coordination Goal. All plan steps completed. |
| `PARTIAL_SUCCESS` | ALL mode — at least one base reached its goal; at least one did not. |
| `PAUSED` | At least one base is paused at an INTERACTIVE step. No NON_RECOVERABLE failure. |
| `FAILED` | Session aborted by user, or at least one NON_RECOVERABLE failure occurred. |
| `BLOCKED` | Workspace validation failed, plan computation failed, or a critical precondition was not met. |
| `ALREADY_SATISFIED` | Goal already satisfied for all target bases. No plan steps executed. |

Output format for each completion state is defined in `${CLAUDE_PLUGIN_ROOT}/templates/prompts/pipeline_run_prompt.md` Output Format Templates section.

---

## Examples

```text
/pipeline-run
```
Present coordination state of all bases. No plan generated.

```text
/pipeline-run payments
```
NEXT mode — derive current state of the `payments` base and advance it to the next logical coordination state.

```text
/pipeline-run ALL
```
NEXT mode — advance all non-CLOSED bases to their next logical coordination state, in ascending alphabetical order.

```text
/pipeline-run payments BASELINED
```
TARGET mode — advance the `payments` base to BASELINED, executing all required pipeline stages.

```text
/pipeline-run payments --event BASELINE_REQUEST
```
EVENT mode — resume the `payments` base from a BASELINE_REQUEST gate pause.

```text
/pipeline-run ALL KNOWLEDGE_READY
```
TARGET mode — advance all non-CLOSED bases to KNOWLEDGE_READY.

---

## Expected Output

```text
WORKSPACE_ROOT/runtime/pipeline/events.md          — appended with SESSION_START, STEP_COMPLETE, PAUSE, RESUME_REQUEST, STEP_FAILED, SESSION_END, SESSION_FAILED events as applicable
WORKSPACE_ROOT/runtime/pipeline/pipeline_state.md  — written or updated with coordination state and business flags for each processed base
```

No other repository areas are modified by this command. All M1–M10 artifacts are read-only inputs.

---

## References

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/pipeline-run.md                  — Layer 1 contract (business states, event model, validation rules PC0–PC18)
${CLAUDE_PLUGIN_ROOT}/docs/commands/pipeline-run_execution.md        — Layer 2 execution specification (18 phases, state derivation, capability model)
${CLAUDE_PLUGIN_ROOT}/templates/prompts/pipeline_run_prompt.md       — Layer 3 prompt template (behavioral intent, output formats, failure scenarios)
${CLAUDE_PLUGIN_ROOT}/docs/decisions/ADR-001-csr-language-policy.md  — language policy (canonical artifacts English; interaction surface in the user's language)
```
