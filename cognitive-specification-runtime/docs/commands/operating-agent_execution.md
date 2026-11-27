# Operating Agent Runtime — Layer 2 Execution Specification

**Milestone:** M15
**Version:** 1.0 (APPROVED)
**Status:** APPROVED
**File:** `docs/commands/operating-agent_execution.md`
**Layer 1 Contract:** `docs/commands/operating-agent.md`

---

## 1. Purpose

This document defines the execution behavior of the Operating Agent Runtime: how the Operating Agent processes a single conversational turn, from the moment a user message arrives to the moment a Business Response and an updated Interaction Context are produced.

The Layer 1 Contract defines what the Operating Agent is responsible for, what business states and actions it presents, and what it must never do. This Layer 2 specification defines how those responsibilities are carried out at runtime, as a repeatable execution behavior. It does not define prompts, Claude commands, file operations, or any implementation mechanism. It defines execution behavior only.

The Operating Agent Runtime executes the following authoritative pipeline on every conversational turn:

```text
Interaction Context → User Intent → Capability Assessment → Agent Action
```

Every turn is reconstructed against this pipeline. No stage is skipped, and no stage is re-ordered. A turn that does not require a target, a delegation, or a state change still passes through all four stages — the later stages simply resolve to their simplest outcome (e.g., no target required, capability trivially Allowed).

This specification covers: the four Runtime Objects produced by the pipeline (Section 2), the Runtime Principles governing execution (Section 3), the inputs and outputs of the runtime (Sections 4–5), the procedure for each pipeline stage (Sections 6–10), the delegation boundary (Section 11), response generation (Section 12), context carry-forward (Section 13), the result classification model (Section 14), the design decisions this specification fixes (Section 15), and the validation model (Section 16).

---

## 2. Runtime Objects

The pipeline produces exactly four Runtime Objects per turn, in order. Each object is the input to the stage that follows it.

Among these four, Interaction Context (RO-1) is the primary runtime object of the Operating Agent Runtime: it is the only one that persists and carries forward across turns, and it is both the output of the previous turn's pipeline and the starting input to the current turn's pipeline (Section 6). RO-2, RO-3, and RO-4 are recomputed fresh on every turn from RO-1 and the current user message; none of them persist independently of it.

### RO-1 — Interaction Context

The Operating Agent's reconstructed understanding of the conversation's standing, prior to interpreting the current turn.

| Field | Description |
|-------|-------------|
| `current_project_reference` | The Project currently in conversational focus (the Current Project Context defined in Section 9 of the Layer 1 Contract), or none if no Project is yet in focus |
| `current_project_business_state` | The business state (one of the five defined in Layer 1 Section 5) last observed for the Current Project Context, or none |
| `current_specification_reference` | The Specification, within the Current Project Context, currently in conversational focus — established when the user's recent turns concern a specific Specification (requirement explanation, traceability, exploration, or questioning, per Layer 1 Section 13), or none if no Specification is yet in focus |
| `user_goal_summary` | A business-language summary of what the user is trying to accomplish with the Current Project Context, carried forward across turns |
| `last_agent_action` | The Agent Action (RO-4) produced on the prior turn, used to interpret short or referential user replies (e.g., "yes", "do it") |
| `pending_response_expectation` | Set when the prior turn ended in a clarifying question or a confirmation request; names what kind of reply is expected (a clarification answer, or a confirmation) |
| `active_conversation_flow` | Identifies a multi-turn conversational sequence currently underway — such as stepping through a set of outstanding questions one at a time, exploring a Specification section by section, or progressing through an Archive or Delete confirmation — so that a follow-up turn is interpreted as a continuation of that sequence rather than as a new, unrelated request |
| `active_work_indicator` | Set when work is actively in progress on the Current Project Context such that switching focus away from it would interrupt or invalidate that work (Layer 1 Section 14) |

RO-1 is entirely expressed in business language. It never holds a CSR runtime identifier, artifact path, or execution-state value.

### RO-2 — User Intent

The Operating Agent's classification of what the user wants from the current turn.

| Field | Description |
|-------|-------------|
| `intent_category` | One classification drawn from the Supported User Actions (Layer 1 Section 7), the Exploration capabilities (Layer 1 Sections 12–13), Help and Discovery (Layer 1 Section 11), the Expert Register (Layer 1 Section 10) or Anomaly Signalling (Layer 1 Section 11b) `[D1, 2026-11-01]`, or a Status/Recommendation request (Layer 1 Section 3, Responsibilities 2–3) |
| `mode_signal` | Mode A (Guidance/Pilotage) or Mode B (Understanding/Exploration), inferred per Layer 1 Section 6 |
| `target_reference` | The user's own naming of what the intent applies to, as stated or implied in the current turn, prior to resolution (RO match in Section 8) |
| `ambiguity_flag` | Set when the current turn's wording supports more than one `intent_category` with comparable plausibility |

### RO-3 — Capability Assessment

The Operating Agent's classification of whether the resolved intent, against its resolved target, may proceed.

| Field | Description |
|-------|-------------|
| `resolved_target` | The single Project, Specification, Question, or other business entity the intent applies to, or none if the intent requires no target |
| `assessment` | One of three values: `ALLOWED`, `ALLOWED_WITH_CONFIRMATION`, `DENIED` |
| `assessment_reason` | The business-language reason for the assessment (e.g., the target's business state, Archive Immutability, an Out-of-Scope capability), used later in Business Response Generation |

### RO-4 — Agent Action

The single action the Operating Agent takes in response to the turn. Exactly one Agent Action is computed per turn.

| Action | Description |
|--------|-------------|
| `DISPLAY_INFORMATION` | Answer an exploratory question or state a project's standing, with no request for further user decision |
| `ASK_CLARIFICATION` | Ask the user to resolve an ambiguity in intent or target before proceeding |
| `ASK_CONFIRMATION` | Ask the user to explicitly confirm a consequential or destructive action before it is delegated |
| `RECOMMEND_ACTION` | Lead with a recommended next action, per Recommendation First (Layer 1 OA-03), when the user's evident intent is to make progress |
| `DELEGATE_REQUEST` | Hand a state-changing action to the runtime boundary beneath the Operating Agent (Section 11) |
| `REFUSE_REQUEST` | Decline to proceed, with a stated business-language reason, when the Capability Assessment is `DENIED` |
| `UPDATE_CONTEXT` | Change the Current Project Context (e.g., opening or switching to a different Project) without delegating a state-changing action |

---

## 3. Runtime Principles

**OAE-01 — Single-Pass Pipeline**
Every turn passes through Interaction Context Reconstruction, User Intent Interpretation, Target Resolution, and Capability Assessment exactly once, in that order, before an Agent Action is computed. No stage is skipped, even when its outcome is trivial.

**OAE-02 — Capability Assessment Precedes Delegation**
No `DELEGATE_REQUEST` Agent Action is computed without a preceding Capability Assessment that resolved to `ALLOWED`, or to `ALLOWED_WITH_CONFIRMATION` followed by explicit user affirmation in a subsequent turn.

**OAE-03 — Denial Is Terminal For The Turn**
A Capability Assessment of `DENIED` produces a `REFUSE_REQUEST` Agent Action. The turn does not proceed to Runtime Delegation under any condition.

**OAE-04 — Confirmation Gates Mutation**
Every intent whose execution would mutate or remove a Project or its Specification is assessed as `ALLOWED_WITH_CONFIRMATION` at minimum. `DELEGATE_REQUEST` for such an intent is never computed in the same turn as the first `ASK_CONFIRMATION`; it is only computed after the user's explicit affirmative reply.

**OAE-05 — Context Persists By Default**
Interaction Context Update (Section 13) preserves the Current Project Context and the user's goal summary across turns. Either is changed only when the user explicitly redirects focus, or when the Current Project Context's Project transitions to `DELETED`.

**OAE-06 — Delegation Is Opaque**
Runtime Delegation (Section 11) and Business Response Generation (Section 12) never surface the identity, internal state, artifacts, or mechanics of the runtime that handled a delegated action. The user-visible consequence of delegation is always expressed as a change (or non-change) in business state.

**OAE-07 — Mode Shapes Framing, Not Logic**
The Mode A/B signal (RO-2) determines how a response is framed — leading with a recommendation versus leading with an answer — and never determines the Capability Assessment outcome or which Agent Actions are available for a given intent and target.

---

## 4. Runtime Inputs

On every turn, the Operating Agent Runtime receives:

| Input | Description |
|-------|-------------|
| Current user message | The conversational input for this turn |
| Available conversation history | Whatever portion of the current session's conversation remains available to the Operating Agent at this turn |
| Prior Interaction Context | The Interaction Context (RO-1) carried forward from the previous turn or previous session, when one exists (Section 6) |
| Project business-state observations | The existence, business state (Layer 1 Section 5), outstanding-question standing, and Specification availability of the user's Projects, obtained exclusively through Runtime Delegation (Section 11) |

The Operating Agent Runtime never reads a CSR runtime artifact directly. Every fact about a Project's standing that did not originate in the conversation itself is obtained by delegating an observation request to the appropriate runtime boundary and receiving back a business-state fact.

---

## 5. Runtime Outputs

On every turn, the Operating Agent Runtime produces:

| Output | Description |
|--------|-------------|
| Business Response | The user-facing content produced by Business Response Generation (Section 12) |
| Updated Interaction Context | The Interaction Context (RO-1) carried forward to the next turn (Section 13) |
| Session Result | The outcome classification for the turn (Section 14) |
| Delegation Request (conditional) | Present only when the Agent Action is `DELEGATE_REQUEST`: the business-described action handed to the runtime boundary beneath the Operating Agent (Section 11) |

---

## 6. Interaction Context Reconstruction

This stage produces RO-1 for the current turn.

1. **Recover prior Interaction Context.** If a prior Interaction Context exists (from an earlier turn in this session, or from a previous session), it is the starting point. If none exists, RO-1 is initialized with no Current Project Context, no goal summary, and no pending response expectation.

2. **Validate the Current Project Context, if one exists.** Obtain the current business state of the Current Project Context's Project through delegation (Section 11).
   - If the Project's business state is now `DELETED`: clear `current_project_reference`, `current_project_business_state`, and `current_specification_reference` (a Specification belongs to exactly one Project and cannot remain in focus once its Project no longer exists). The Business Response for this turn will inform the user that the project they were focused on no longer exists, once Intent Interpretation determines whether this fact is relevant to the turn.
   - If the Project's business state is `ARCHIVED`: retain it as the Current Project Context, and retain `current_specification_reference` if one was set. Archive Immutability (Layer 1 Section 5) is enforced later, at Capability Assessment (Section 9) — it does not clear the context.
   - For any other business state: retain the Current Project Context and update `current_project_business_state` to the freshly observed value.

3. **Carry forward goal, last action, pending expectation, and active flow.** `user_goal_summary`, `last_agent_action`, `pending_response_expectation`, and `active_conversation_flow` are copied forward unchanged. They are updated only by Interaction Context Update (Section 13), after the current turn's Agent Action is computed.

4. **First-turn case.** If this is the first turn of a new session and a prior Interaction Context exists from an earlier session, Context Restoration applies (Layer 1 OA-12): the reconstructed Current Project Context and the user's last known goal are stated to the user as part of the Business Response, rather than silently assumed.

---

## 7. User Intent Interpretation

This stage produces RO-2 for the current turn, using RO-1 as context.

1. **Classify the intent category.** Interpret the current user message, in light of the available conversation history and RO-1, against the full vocabulary of supported intents: the Project Lifecycle, Source Management, Question Handling, Specification Handling, Project Exploration, and Assistance actions (Layer 1 Section 7, including the Expert Register and Anomaly Signalling intents `[D1, 2026-11-01]`); the Project and Specification Exploration capabilities (Layer 1 Sections 12–13); Help and Discovery (Layer 1 Section 11); and Status/Recommendation requests (Layer 1 Section 3).

2. **Resolve referential replies.** If the current message is a short or referential reply (e.g., "yes", "do it", "the second one") and `pending_response_expectation` is set, interpret the message against that expectation rather than reclassifying it as a new, unrelated intent.

3. **Infer the mode signal.** Classify the intent as Mode A (the user is trying to make something happen) or Mode B (the user is trying to understand something), per Layer 1 Section 6. This signal is recorded but, per OAE-07, does not affect any subsequent stage's logic — only the framing applied during Business Response Generation.

4. **Detect ambiguity.** If the current message plausibly supports more than one `intent_category` with no clear preference between them, set `ambiguity_flag`. An ambiguous intent is not resolved by guessing; it is carried into Target Resolution and Capability Assessment unresolved, and will produce an `ASK_CLARIFICATION` Agent Action (Section 10).

5. **Record the user's own target reference.** Capture however the user referred to the target of their intent in this turn (by name, by description, by "it"/"this project", or not at all). This raw reference is resolved against actual business entities in Target Resolution (Section 8); it is not resolved here.

---

## 8. Target Resolution

This stage resolves `target_reference` (RO-2) into `resolved_target` (RO-3), for intents that require a target. Intents with no target (e.g., Create Project, Request Help, Request Technical Detail, Report an Anomaly `[D1, 2026-11-01]`) skip directly to a `resolved_target` of none.

1. **Explicit reference takes precedence.** If the user named or clearly described a specific Project, Specification, or Question in the current turn, resolve to that entity.

2. **Default to the Current Project Context.** If the user gave no explicit reference and a Current Project Context exists (RO-1), resolve the target relative to it. This is the default behavior described in Layer 1 Section 9: every project-related request is interpreted relative to the Current Project Context unless redirected.

3. **No resolvable target.** If the intent requires a target, no explicit reference was given, and no Current Project Context exists, resolution fails. This does not produce a `DENIED` Capability Assessment — it produces an `ASK_CLARIFICATION` Agent Action (Section 10), since the gap is one of missing information, not of disallowed action.

4. **Ambiguous reference.** If the user's reference matches more than one candidate entity (e.g., a search returns multiple Projects with similar names), resolution fails with multiple candidates. This also produces `ASK_CLARIFICATION`, presenting the candidates conversationally rather than as a menu (Layer 1 Section 8).

5. **Sub-target resolution.** For intents directed at a Specification, a Question, a source, or a history entry, the owning Project is resolved first (steps 1–4), and the specific sub-entity is then resolved within that Project's scope, applying the same precedence (explicit reference, then default, then ask). For a Specification specifically, the default (step 2) is the Current Specification Context (`current_specification_reference`) when one exists within the resolved Project; if none exists and the intent requires one, resolution proceeds to step 3 (ask).

---

## 9. Capability Assessment

This stage produces the `assessment` and `assessment_reason` fields of RO-3, given the resolved intent category and resolved target (or its absence).

1. **Intents requiring no target, and pure information intents, are `ALLOWED`.** Creating a new Project, requesting help, requesting technical detail (Layer 1 Section 10, Expert Register), reporting an anomaly (Layer 1 Section 11b) `[D1, 2026-11-01]`, and any read-only exploration of a Project that is not `DELETED` (sources, questions, decisions, history, current state, and — once available — Specification content, traceability, and origins) are `ALLOWED` regardless of the target's other business-state details. Archive Immutability permits consultation and exploration of an `ARCHIVED` Project (Layer 1 Section 5); this assessment reflects that explicitly.

2. **Mutating intents are `ALLOWED` only against a Project that is not `ARCHIVED` or `DELETED`.** Adding sources and answering outstanding questions are assessed `DENIED` against an `ARCHIVED` or `DELETED` Project, citing Archive Immutability or non-existence as the reason (Layer 1 Section 7, Non-Responsibility 7). Against any other business state, these intents are `ALLOWED`.

3. **Destructive intents are `ALLOWED_WITH_CONFIRMATION`, never directly `ALLOWED`.** Archiving and deleting a Project are assessed `ALLOWED_WITH_CONFIRMATION` whenever the Project is not already in the target state (an already-`ARCHIVED` Project cannot be archived again; an already-`DELETED` Project cannot be deleted again — both are assessed `DENIED` with reason "already in that state"). This reflects Layer 1 OA-06 and OA-07: no destructive action is ever assessed as proceeding without a confirmation step.

4. **Renaming follows the mutation rule.** Renaming is assessed `ALLOWED` against a Project that is not `ARCHIVED` or `DELETED`, and `DENIED` otherwise, for the same reason as step 2.

5. **A target that no longer exists is `DENIED`.** Any intent — including a purely informational one — directed at a Project resolved to business state `DELETED` is assessed `DENIED`, with reason that the Project no longer exists as a referenceable entity (Layer 1 Section 5).

6. **Out-of-scope intents are `DENIED`.** An intent that maps to a capability outside the Operating Agent's responsibility (Layer 1 Section 15) is assessed `DENIED`, with reason that the capability does not exist within the Operating Agent's scope.

7. **A Current Project Context switch while active work is in progress is `ALLOWED_WITH_CONFIRMATION`.** When the resolved target of an Open/Search/Create intent is a different Project than the Current Project Context, and `active_work_indicator` is set for the present Current Project Context, the switch itself is assessed `ALLOWED_WITH_CONFIRMATION`. The confirmation step for this case is the four-part Active Execution Protection dialogue (Layer 1 Section 14), not a simple yes/no — this is elaborated in Section 11 and Section 12.

8. **Ambiguous or unresolved targets are not assessed.** If Target Resolution (Section 8) did not produce a single `resolved_target`, Capability Assessment is not performed for this turn; the turn proceeds directly to an `ASK_CLARIFICATION` Agent Action.

---

## 10. Agent Action Computation

This stage produces RO-4, the single Agent Action for the turn, from RO-2 and RO-3.

Evaluate in order; the first matching condition determines the Agent Action:

1. If `ambiguity_flag` is set (RO-2), or Target Resolution did not produce a single `resolved_target` for an intent that requires one (Section 8) → `ASK_CLARIFICATION`.
2. If `assessment` is `DENIED` (RO-3) → `REFUSE_REQUEST`.
3. If `assessment` is `ALLOWED_WITH_CONFIRMATION` and `pending_response_expectation` does not already record an affirmed confirmation for this exact intent and target → `ASK_CONFIRMATION`.
4. If `assessment` is `ALLOWED_WITH_CONFIRMATION` and the current turn is the user's affirmative reply to a prior `ASK_CONFIRMATION` for this exact intent and target → `DELEGATE_REQUEST`.
5. If `assessment` is `ALLOWED` and the intent is a pure navigation change (Open Project, or a successful Search resolving to one Project) with no other CSR state change implied → `UPDATE_CONTEXT`.
6. If `assessment` is `ALLOWED` and the intent is a state-changing action other than navigation (Create Project, Add Sources, Answer Outstanding Questions) → `DELEGATE_REQUEST`.
7. If `assessment` is `ALLOWED` and the intent is informational (View Outstanding Questions, Download/Explore Specification, View Project Information/History, Help, Request Technical Detail, Report an Anomaly `[D1, 2026-11-01]`, any Section 12/13 exploration query) and `mode_signal` is Mode B → `DISPLAY_INFORMATION`.
8. If `assessment` is `ALLOWED` and the intent is a Status/Recommendation request, or `mode_signal` is Mode A with the user's evident goal being to make progress → `RECOMMEND_ACTION`.

A turn produces exactly one Agent Action. `RECOMMEND_ACTION` may still include explanatory content drawn from the same business-state facts a `DISPLAY_INFORMATION` action would use (Recommendation First, Layer 1 OA-03, leads with the recommendation rather than omitting context) — this is a Business Response Generation concern (Section 12), not a second Agent Action.

---

## 11. Runtime Delegation

This stage applies only when the Agent Action is `DELEGATE_REQUEST`. It defines the boundary between the Operating Agent and the CSR runtimes beneath it (Layer 1 Section 2).

### Delegation Targets

The Operating Agent recognizes four delegation targets, corresponding to the four runtime groupings in Layer 1 Section 2:

| Delegation Target | Handles |
|--------------------|---------|
| Workspace Capability | Project container lifecycle: creation, archival |
| Coordination Capability | Progressing a Project through its pipeline: source ingestion, answering questions, and any "make progress" request |
| Governance Capability | Authorization of Coordination Capability actions — never invoked directly by the Operating Agent; its consequences are observed, not requested |
| Resolution Capability | Channeling a human authority decision when the Coordination Capability reports that one is needed |

Every `DELEGATE_REQUEST` names exactly one delegation target and carries only business-relevant content: the target Project, the action class (in business terms), and any parameters the user has already supplied or confirmed. It never carries a runtime-internal identifier, because the Operating Agent never possesses one.

### Delegation Procedure

1. **Single delegation per turn.** A turn that computes `DELEGATE_REQUEST` issues exactly one delegation. If the underlying action requires multiple runtime steps, that sequencing is the responsibility of the delegation target, not the Operating Agent.
2. **Delegation is opaque to the user.** The user is never informed which delegation target was used, nor shown any output specific to it. The user is informed only of the eventual business-relevant consequence.
3. **Observation, not interpretation.** The Operating Agent observes one of two business-relevant consequences from a delegation: (a) the action proceeded, and the Project's business state may have changed; or (b) a decision is needed before the action can proceed. The Operating Agent never observes, stores, or reasons about the internal mechanism that produced either consequence.
4. **A decision-needed consequence becomes `ACTION_REQUIRED`.** When delegation reports that a decision is needed (whether the decision belongs to the user directly, or to a human authority reached through the Resolution Capability), the Project's business state is represented to the user as `ACTION_REQUIRED` (Layer 1 Section 5), never as a runtime-specific pause state.
5. **The Operating Agent never resolves what it delegates.** It never bypasses the Governance Capability's authorization function, and it never produces a Resolution Capability decision on the user's behalf without the user's explicit input (Layer 1 Section 4, Non-Responsibility 2).
6. **Active Execution Protection delegation case.** When Capability Assessment classified a Current Project Context switch as `ALLOWED_WITH_CONFIRMATION` due to active work in progress (Section 9, step 7), and the user declines to switch, no delegation occurs and the Current Project Context is unchanged. If the user proceeds anyway, the switch is carried out as an `UPDATE_CONTEXT` action (Section 13) — switching focus is never itself delegated to a runtime, since it changes only the Operating Agent's own conversational state.

### Boundary Invariant

No part of Runtime Delegation, and no part of Business Response Generation (Section 12) that follows it, ever names a CSR runtime by milestone number or internal name, references a runtime-internal identifier, or describes a runtime mechanism. This invariant holds regardless of which delegation target was used or what consequence was observed.

---

## 12. Business Response Generation

This stage produces the Business Response (Section 5) from the Agent Action (RO-4) and its supporting facts (RO-1, RO-2, RO-3, and any delegation observation from Section 11).

1. **Anchor to context, when relevant.** If the Business Response concerns the Current Project Context, and the conversation has not already established that focus in this turn, state it plainly rather than assuming the user remembers (Layer 1 OA-01, Context Awareness).
2. **Produce content matching the Agent Action:**
   - `DISPLAY_INFORMATION` — answer the question or state the standing, directly and specifically, not as a generic restatement (Layer 1 Section 13). For a Request Technical Detail intent, content is the expert-register explanation Layer 1 Section 10 permits — this is the one case where step 4 below does not apply as written; see its exception. For a Report an Anomaly intent, content is the business-language description of the signalling mechanism and, if the user proceeds, guidance to run it themselves (Layer 1 Section 11b) — never a runtime-generated report.
   - `ASK_CLARIFICATION` — ask a conversational question that resolves the ambiguity, never a menu (Layer 1 Section 8).
   - `ASK_CONFIRMATION` — for an ordinary destructive action, state the consequence and ask for explicit confirmation of that specific action (Layer 1 OA-06, OA-07). For the Active Execution Protection case (Section 9, step 7), present the full four-part dialogue: inform that other work is in progress, explain the consequence of switching, offer an alternative (waiting or returning to it first), and recommend a separate session for concurrent work (Layer 1 Section 14).
   - `RECOMMEND_ACTION` — lead with the recommended next action; supporting explanation follows, not precedes, the recommendation (Layer 1 OA-03).
   - `DELEGATE_REQUEST` — acknowledge that the action is proceeding, in business terms, before or as the delegation occurs; the eventual consequence is reported once observed (Section 11, step 3).
   - `REFUSE_REQUEST` — state plainly that the action is not available, and why, in business language, without speculating on workarounds (Layer 1 Section 15).
   - `UPDATE_CONTEXT` — confirm the new Current Project Context and, if useful, restate its standing (Context Restoration pattern, applied mid-conversation).
3. **Apply the Business Language Policy translation.** Every runtime-derived fact feeding the response is translated to business language per the table in Layer 1 Section 10 before it appears in the response. A fact that has no entry in that table is described in terms of its business-relevant consequence, never its runtime mechanism.
4. **Pre-delivery compliance check.** Before the response is finalized, it is checked against the Business Language Policy (Layer 1 Section 10): no milestone reference, no runtime identifier, no internal artifact name, and no execution-state term may appear. A response that fails this check is rewritten before delivery, not delivered with a caveat.
   **Exception `[D1, 2026-11-01]`:** this check does not apply to a `DISPLAY_INFORMATION` response produced while the Expert Register is open (Layer 1 Section 10) — that register exists precisely to permit the vocabulary this check otherwise forbids, on the user's own explicit request. The exception is scoped to the single response answering that request; the very next turn's compliance check applies unconditionally again, per Layer 1 Section 10's "never carried forward" rule.

---

## 13. Interaction Context Update

This stage produces the updated Interaction Context (RO-1 for the next turn), after the current turn's Agent Action and Business Response are finalized.

1. **Current Project Context.**
   - Preserved unchanged, by default (OAE-05), for any Agent Action other than `UPDATE_CONTEXT` or a Project's transition to `DELETED`.
   - Set to the newly resolved target when the Agent Action is `UPDATE_CONTEXT`.
   - Cleared when the Current Project Context's Project has transitioned to `DELETED` (detected in Section 6, step 2, or as the direct consequence of a `DELETE_REQUEST` delegation observed in this turn).
2. **Business state refresh.** `current_project_business_state` is updated to whatever was most recently observed for the Current Project Context — either from Section 6's reconstruction, or from a delegation observation in this turn.
3. **Current Specification Context.**
   - Set to the Specification the current turn resolved (Section 8, step 5) whenever that turn's intent concerned a specific Specification.
   - Preserved unchanged across turns whose intent does not name or imply a different Specification, so follow-up questions about "it" continue to resolve to the same Specification.
   - Cleared whenever the Current Project Context changes or clears (step 1), since a Specification cannot remain in focus once its owning Project is no longer in focus.
4. **Goal summary.** `user_goal_summary` is preserved by default. It is updated only when the user's current turn explicitly states or revises what they are trying to accomplish.
5. **Last action and pending expectation.**
   - `last_agent_action` is set to the Agent Action computed this turn (RO-4).
   - `pending_response_expectation` is set when the Agent Action is `ASK_CLARIFICATION` or `ASK_CONFIRMATION` (naming what reply is expected), and cleared otherwise — including after a `DELEGATE_REQUEST` that followed a confirmed `ASK_CONFIRMATION`, since the expectation has now been satisfied.
6. **Active conversation flow.** `active_conversation_flow` is set when the Agent Action begins or continues a multi-turn sequence — stepping through outstanding questions, exploring a Specification across several turns, or an Archive/Delete confirmation exchange — and is cleared once that sequence concludes (the last question is answered, the exploration is abandoned or redirected, or the confirmation exchange resolves into a `DELEGATE_REQUEST` or is declined).
7. **Active work indicator.** Set when a delegation observation (Section 11) indicates the Coordination Capability has started work on the Current Project Context that has not yet reached a business-stable point (a Specification produced, a baseline reached, or `ACTION_REQUIRED` reached and awaiting the user). Cleared when that work concludes or when `ACTION_REQUIRED` is reached, since waiting for the user is not "active work in progress" in the sense Active Execution Protection (Layer 1 Section 14) protects against.

---

## 14. Session Result Model

Every turn concludes with exactly one Session Result, determined by the Agent Action (RO-4) computed for that turn.

| Session Result | Produced By |
|-----------------|-------------|
| `RESPONSE_PROVIDED` | `DISPLAY_INFORMATION` or `RECOMMEND_ACTION` |
| `CLARIFICATION_REQUIRED` | `ASK_CLARIFICATION` |
| `CONFIRMATION_REQUIRED` | `ASK_CONFIRMATION` |
| `DELEGATION_REQUESTED` | `DELEGATE_REQUEST` |
| `REQUEST_DENIED` | `REFUSE_REQUEST` |
| `CONTEXT_UPDATED` | `UPDATE_CONTEXT` |

The Session Result is recorded as part of the turn's outcome (Section 5) and is available to inform the next turn's Interaction Context Reconstruction (Section 6, via `pending_response_expectation` and `last_agent_action`) — it is not itself stored as a separate field of RO-1.

---

## 15. Runtime Decisions

**RD-OAE-01 — Capability Assessment Is Re-Evaluated Every Turn**
Capability Assessment (Section 9) is never cached or assumed from a prior turn. Even when the same intent and target recur across turns, the assessment is recomputed from the freshly observed business state each time. The Interaction Context (RO-1) carries forward conversational facts, never a capability verdict.

**RD-OAE-02 — Mode Signal Never Gates Logic**
Per OAE-07, the Mode A/B signal is computed (Section 7) and consumed only in Agent Action Computation (Section 10, steps 7–8, to choose between `DISPLAY_INFORMATION` and `RECOMMEND_ACTION`) and Business Response Generation (Section 12, framing). It is never read by Target Resolution or Capability Assessment.

**RD-OAE-03 — Denial Precedes Delegation Unconditionally**
The ordering in Agent Action Computation (Section 10) places the `DENIED` check (step 2) before any confirmation or delegation check. A `DENIED` assessment can never be reached after a delegation has already been requested in the same turn.

**RD-OAE-04 — Only the Five Business States Appear in Capability Assessment**
Capability Assessment (Section 9) reasons exclusively in terms of the five business states defined in Layer 1 Section 5. No execution-state, runtime-phase, or coordination-state vocabulary is used as a condition anywhere in this stage, consistent with Layer 1 Section 5's statement that execution states are not business states.

**RD-OAE-05 — Switching Context Is Never Itself Delegated**
A Current Project Context switch (the `UPDATE_CONTEXT` Agent Action) is resolved entirely within the Operating Agent's own conversational state. It is never sent to a delegation target, because no CSR runtime owns "what the Operating Agent and the user are currently discussing."

**RD-OAE-06 — Confirmation Affirmation Is Matched, Not Re-Asked**
When a Capability Assessment of `ALLOWED_WITH_CONFIRMATION` recurs because the user has just affirmed a prior `ASK_CONFIRMATION` (Section 10, step 4), the Operating Agent does not re-issue the same confirmation question. `pending_response_expectation` (RO-1) is the mechanism that distinguishes a fresh occurrence of the intent from the affirmed continuation of one already asked.

---

## 16. Validation

**V-01 — Pipeline Completeness.** Every turn's processing is traceable through all four stages — Interaction Context Reconstruction, User Intent Interpretation (including Target Resolution), Capability Assessment, and Agent Action Computation — even when a stage's outcome is trivial.

**V-02 — No Unassessed Action.** No Agent Action other than `ASK_CLARIFICATION` is computed for a turn whose Target Resolution did not conclude (a single resolved target, or a confirmed absence of any required target).

**V-03 — No Premature Delegation.** No `DELEGATE_REQUEST` Agent Action is computed except where Capability Assessment resolved to `ALLOWED`, or to `ALLOWED_WITH_CONFIRMATION` followed by an explicit affirmative reply recorded via `pending_response_expectation`.

**V-04 — Business Language Compliance.** No Business Response contains a CSR milestone reference, runtime-internal identifier, artifact path, command name, or execution-state term (Layer 1 Section 10). This is verified by the pre-delivery compliance check (Section 12, step 4) on every turn.

**V-05 — Destructive Action Confirmation.** Every Archive or Delete intent that reaches `DELEGATE_REQUEST` is preceded, in an earlier turn, by an `ASK_CONFIRMATION` Agent Action for that exact intent and target, and by the user's explicit affirmative reply.

**V-06 — Active Execution Protection Completeness.** Every Current Project Context switch attempted while `active_work_indicator` is set for the present context produces the full four-part Active Execution Protection dialogue (Section 12), not an abbreviated or partial version of it.

**V-07 — Context Persistence.** The Current Project Context and `user_goal_summary` are unchanged across a turn unless that turn's Agent Action is `UPDATE_CONTEXT`, the user explicitly revised the goal, or the Current Project Context's Project transitioned to `DELETED`. The Current Specification Context (`current_specification_reference`) follows the same persistence rule and additionally clears whenever the Current Project Context changes or clears. `active_conversation_flow` persists only while the sequence it names remains unresolved, and clears once that sequence concludes, is abandoned, or is declined.

**V-08 — Session Result Mapping.** Every turn's Session Result corresponds to its Agent Action exactly as defined in Section 14 — no turn produces a Session Result outside that mapping.

**V-09 — Mode Non-Interference.** No record of a Capability Assessment outcome or an available Agent Action differs solely because `mode_signal` differs; only the choice between `DISPLAY_INFORMATION` and `RECOMMEND_ACTION`, and response framing, may depend on it.

**V-10 — Denial Reason Traceability.** Every `REFUSE_REQUEST` Agent Action carries an `assessment_reason` (RO-3) that traces to a specific Layer 1 rule (Archive Immutability, Out of Scope, non-existence of a `DELETED` target, or an already-satisfied destructive action), stated in business language in the resulting response, without naming the rule by any internal identifier.

---

## References

```text
docs/commands/operating-agent.md              — M15 Layer 1 Contract
docs/project.md                               — CSR vision, MVP objectives, core principles
docs/runtime_engineering_method.md            — CSR four-layer implementation methodology
docs/architecture/workspace_runtime.md        — M10 Workspace Runtime Contract
docs/commands/pipeline-run.md                 — M11 Pipeline Coordination Runtime Contract
docs/commands/governance-run.md               — M12 Governance Runtime Contract
docs/commands/governance-resolve.md           — M13 Governance Outcome Resolution Runtime Contract
docs/decisions/ADR-001-csr-language-policy.md — language policy (canonical artifacts English; interaction surface in the user's language)
```
