# Operating Agent Runtime — Prompt Template

**Milestone:** M15
**Layer:** Layer 3 — Prompt Template
**Status:** APPROVED
**Version:** 1.0 APPROVED
**File:** `docs/commands/operating-agent-prompt-template.md`

---

## 1. Purpose

This document defines the Layer 3 Prompt Template for the Operating Agent Runtime: the structure used to assemble, on every conversational turn, the prompt that drives the agent executing the Operating Agent.

Layer 3 exists because Layer 1 and Layer 2 define *what* the Operating Agent is and *how* it computes its behavior, but neither defines *what is placed in front of the executing agent* to make that computation happen. Layer 1 (`docs/commands/operating-agent.md`) is a contract: it defines responsibilities, the five Business States, the Business Language Policy, and the fourteen Runtime Principles OA-01–OA-14. Layer 2 (`docs/commands/operating-agent_execution.md`) is an execution specification: it defines the four-stage pipeline `Interaction Context (RO-1) → User Intent (RO-2) → Capability Assessment (RO-3) → Agent Action (RO-4)`, the seven Runtime Principles OAE-01–OAE-07, and the precise field sets of all four Runtime Objects. Layer 3 translates both into the material the executing agent actually reads: a prompt.

**Relation to Layer 1.** Every constraint Layer 1 declares as permanent — the five Business States, Archive Immutability, the Business Language Policy's never-exposed list, the distinction between a Project and a Specification, Active Execution Protection — must appear in the assembled prompt as injected content, not as paraphrase invented at Layer 3. Layer 3 carries Layer 1's vocabulary into the prompt verbatim; it does not reinterpret it.

**Relation to Layer 2.** The prompt's structure mirrors Layer 2's pipeline directly. Layer 2 defines four Runtime Objects, of which RO-1 (Interaction Context) is primary — the only object that persists across turns (Layer 2 Section 2, primacy statement; M15 Discovery Assimilation KD-1). Layer 3 reflects this primacy architecturally: the Interaction Context is the object around which the entire prompt is organized, not one block among equals.

---

## 2. Prompt Architecture

The M15 Prompt Template is **dynamic, not static**. There is no single fixed prompt text checked into the repository and reused unchanged turn after turn. Instead, the prompt is assembled fresh, every turn, from named blocks whose content is injected from the current Interaction Context, the current message, and freshly computed Capability Assessment and Recommendation Context.

This follows directly from Layer 2's architecture. Because Interaction Context (RO-1) is the only Runtime Object that persists, and because RO-2, RO-3, and RO-4 are recomputed fresh every turn (OAE-01 — Single-Pass Pipeline), a static prompt would either go stale (carrying forward content that no longer reflects the current turn) or silently drop the only thing that is supposed to persist. A dynamic, block-composed prompt is the direct architectural consequence of OAE-01 and OAE-05 (Context Persists By Default).

**Core Architectural Model:**

```text
Interaction Context  →  Prompt Context Assembly  →  Prompt Execution
```

- **Interaction Context** is read first, at the start of every turn — it is the input that makes assembly possible. It supplies Current Project Context, Current Specification Context, Business State, Active Conversation Flow, and the other RO-1 fields.
- **Prompt Context Assembly** is the act of building the six Prompt Blocks (Section 3) from Interaction Context, the current user message, and the freshly computed Capability Assessment and Agent Action Computation outputs, in the order defined by the Prompt Assembly Model (Section 4).
- **Prompt Execution** is the act of presenting the assembled prompt to the executing agent for the current turn, producing the Business Response, the updated Interaction Context, and the Session Result defined in Layer 2 Sections 12–14.

No block is authored once and reused verbatim. Every block, on every turn, is populated from the current state of the four Runtime Objects.

---

## 3. Prompt Blocks

The prompt is composed of exactly six named blocks. Each block has a fixed identity and role; its *content* varies turn to turn, but its *presence and structure* do not.

### PB-01 — Agent Identity Block

**Injected content:** The agent's name (César), type (CSR Operating Agent), mission, and authority (Advisory and Guidance Only) as declared in Layer 1 Section 0, including the self-presentation rule in its current form: **César does not re-introduce itself.** First contact is the Entry Runtime's responsibility and has already happened by the time any Operating Agent turn runs (Layer 4, `.claude/commands/csr.md` Phase 3, CSR-E-07) — so the Operating Agent never opens a turn by restating its name, role or mission, whether on a project switch, after a pause, or at hand-off. When directly asked about its identity, it answers plainly in the session's interaction language (ADR-001 § Interaction Language) — at this deployment's default: *« Je suis César, l'agent qui vous accompagne dans le Cognitive Specification Runtime. »*, which is an illustration of the default language, not a fixed string. Also injected: the Operating Agent's identity as the conversational entry point to the Cognitive Specification Runtime (Layer 1 Section 1–2); its role and the nine Responsibilities of Layer 1 Section 3 (Project Guidance, State Explanation, Action Recommendation, Project Navigation, Specification Exploration, Project Exploration, Help and Discovery, Context Reconstruction, Anomaly Signalling `[D1, 2026-11-01]`); a statement of the seven Non-Responsibilities of Layer 1 Section 4, including that Non-Responsibilities 4 and 5 (exposing internal identifiers and implementation internals) carry an explicit exception for the bounded Expert Register the user may open per Section 10 — they are not stated as unconditional.

**Stability requirement:** This block's content is identical across every execution of the Operating Agent, regardless of Interaction Context, turn number, or conversation history. It carries no per-turn data. It is the one block that is authored once, in this document, and injected unchanged. Its purpose is to anchor the executing agent's identity before any per-turn content is read, so that no later block can be misread as redefining who the agent is.

### PB-02 — Runtime Principles Block

**Injected content:** The full text of Runtime Principles OA-01 through OA-14 (Layer 1 Section 16: Context First, Business Language Only, Recommendation First, Conversation First, Intent Before Navigation, Protect Destructive Actions, Explain Consequences, Preserve User Goal, Hide Runtime Complexity, Non-Execution, Exploration Is Optional, Context Restoration, Mode Inference Not Mode Selection, Protect Active Execution) and OAE-01 through OAE-07 (Layer 2 Section 3: Single-Pass Pipeline, Capability Assessment Precedes Delegation, Denial Is Terminal For The Turn, Confirmation Gates Mutation, Context Persists By Default, Delegation Is Opaque, Mode Shapes Framing Not Logic).

**Usage:** OA-01–OA-14 govern the agent's conversational stance — what it must do regardless of which turn it is on (e.g., never expose runtime vocabulary, always recommend rather than command, always explain consequences before a destructive action). OAE-01–OAE-07 govern the agent's computational stance — how it must process the current turn (e.g., always reconstruct Interaction Context before interpreting intent, never delegate after a DENIED assessment, never let Mode Signal change a Capability Assessment outcome). Like PB-01, this block's content does not vary by turn; it is reproduced in full every time so that the principles are never assumed to be "already known" from a prior turn — Layer 2's reconstruction-first discipline applies to principles as much as to data.

### PB-03 — Interaction Context Block

**Injected content:** Current Project Context (`current_project_reference`, `current_project_business_state`); Current Specification Context (`current_specification_reference`); Business State (one of the five Layer 1 Section 5 states: `WAITING_FOR_SOURCES`, `ACTION_REQUIRED`, `SPECIFICATION_AVAILABLE`, `ARCHIVED`, `DELETED`); Active Conversation Flow (`active_conversation_flow`); and, where relevant to the turn, `user_goal_summary`, `last_agent_action`, `pending_response_expectation`, and `active_work_indicator` — the remaining RO-1 fields (Layer 2 Section 2).

**Structure:** This block is a direct rendering of RO-1 as reconstructed in Layer 2 Section 6 (Interaction Context Reconstruction) at the start of the current turn — never a cached or stale copy. Fields hold their last-known value when no update applies this turn (OAE-05 — Context Persists By Default); a field with no value yet (e.g., no Project has been opened) is rendered as explicitly empty, never omitted, so the executing agent can distinguish "not yet established" from "carried forward unchanged."

**Primacy statement.** PB-03 is the primary dynamic prompt block. Interaction Context (RO-1) is the only Runtime Object that persists across turns (Layer 2 Section 2; M15 Discovery Assimilation KD-1); PB-04 and PB-05 are derived from a fresh assessment of it each turn, and PB-01/PB-02 are stable regardless of it. PB-03 is therefore the one block whose turn-to-turn content actually carries the conversation's continuity — the Core Architectural Model (Section 2) places Interaction Context first for this reason, and PB-03 is its direct rendering.

### PB-04 — Capability Context Block

**Injected content:** Allowed actions, Restricted actions, and Confirmation requirements for the current turn's resolved target, as produced by Capability Assessment (RO-3, Layer 2 Section 9).

**Structure:** Built from the three RO-3 fields — `resolved_target`, `assessment`, `assessment_reason` — translated into three plain lists: actions whose assessment is `ALLOWED` (Allowed actions); actions whose assessment is `DENIED`, together with the `assessment_reason` (Restricted actions); and actions whose assessment is `ALLOWED_WITH_CONFIRMATION`, flagged explicitly as requiring confirmation before they may proceed (Confirmation requirements). This block is never populated from assumption — it exists only because Capability Assessment was computed fresh this turn (OAE-01); on a turn where Target Resolution did not converge (Layer 2 Section 8, ambiguous or unresolved target), this block is empty and the turn proceeds directly to Clarification Behavior (Section 10).

### PB-05 — Recommendation Context Block

**Injected content:** Recommended action, Recommended next step, and User guidance information, as produced by Agent Action Computation (RO-4, Layer 2 Section 10) when the computed action is `RECOMMEND_ACTION`, and as a supporting frame for `DELEGATE_REQUEST`, `ASK_CONFIRMATION`, and `DISPLAY_INFORMATION` on turns where a forward path exists.

**Structure:** Recommended action names the single action the agent proposes (never more than one — OA-03, Recommendation First); Recommended next step states what happens if the user agrees; User guidance information supplies any business-language context the user needs to decide (e.g., consequence of a destructive action per OA-07, or the meaning of the current Business State per Layer 1 Section 5). This block is populated only when Agent Action Computation has produced a forward-looking action; on `REFUSE_REQUEST` or `ASK_CLARIFICATION` turns, this block is empty by construction — there is nothing to recommend when the turn ends in denial or unresolved ambiguity.

**Why optionality preserves Recommendation-First.** Recommendation-First (OA-03) governs the *shape* of a recommendation when one is made — exactly one proposed action, never a menu — it does not require that every turn contain a recommendation. Forcing PB-05 to always be populated would mean fabricating a recommendation on turns that end in denial or unresolved ambiguity, which would contradict OAE-03 (Denial Is Terminal For The Turn) and mislead the user into believing a path forward exists when Capability Assessment found none. PB-05's optionality is therefore required *by* Recommendation-First, not an exception to it: a recommendation is only ever real.

### PB-06 — User Request Block

**Injected content:** User message (the current turn's raw input), Resolved intent (`intent_category` and `mode_signal` from RO-2), and Resolved target (`target_reference` from RO-2, plus the resolved value from Target Resolution, Layer 2 Section 8).

**Structure:** User message is reproduced verbatim — Layer 3 never paraphrases the user's own words before they reach the executing agent. Resolved intent and Resolved target are the outputs of User Intent Interpretation (Layer 2 Section 7) and Target Resolution (Layer 2 Section 8) for this turn; if `ambiguity_flag` is set on RO-2, Resolved intent and Resolved target are rendered as explicitly unresolved rather than guessed, which routes the turn to Clarification Behavior (Section 10).

**Response-generation behavior coverage.** The six behaviors the Operating Agent must consistently support — Explain, Guide, Recommend, Clarify, Refuse, Confirm — are not separate prompt blocks; they are response behaviors the executing agent produces from the six blocks above, under the rules of Sections 6 (Conversation Guidance — Guide), 8 (Exploration Behavior — Explain), 9 (Confirmation Behavior — Confirm), 10 (Clarification Behavior — Clarify), and 11 (Recommendation Behavior — Recommend). Refuse is governed by Capability Assessment's `DENIED` outcome (PB-04) routing to `REFUSE_REQUEST` (Layer 2 Section 10 rule 2; Section 11 item 3): on a refusal turn PB-04 is present and shows the denied action with its `assessment_reason`, PB-05 is correctly omitted (PB-05, above), and the executing agent states the denial and its reason in business language (Section 7) without manufacturing an alternative recommendation unless Capability Assessment separately allows one.

---

## 4. Prompt Assembly Model

**Block ordering** (fixed, every turn):

```text
PB-01  Agent Identity
PB-02  Runtime Principles
PB-03  Interaction Context
PB-04  Capability Context
PB-05  Recommendation Context
PB-06  User Request
```

This ordering is not arbitrary, and it is deliberately not a literal replay of Layer 2's computation order. Layer 2 computes RO-1 (Interaction Context), then RO-2 (User Intent and Target Resolution, which reads the current message), then RO-3 (Capability Assessment), then RO-4 (Agent Action) — all of that computation happens *before* the prompt is assembled, by the deterministic runtime logic Layer 2 specifies. By the time Prompt Context Assembly runs, RO-2, RO-3, and RO-4 for the current turn already exist; assembly only decides how to *present* them. Block order therefore follows a presentation dependency, not the computation sequence: identity and principles must be established before any context is read (so the executing agent interprets context through a stable lens); Interaction Context precedes Capability Context because Capability Context is meaningless without the Current Project Context it was assessed against; Capability Context precedes Recommendation Context because a recommendation is a function of the Capability Assessment outcome; and the User Request Block is placed last — even though its underlying RO-2 was computed earliest — so that the executing agent always interprets the current message in light of everything already assembled (identity, principles, context, capability, recommendation), never in isolation. Placing PB-06 last is a response-generation framing choice, not a claim that the user's message is read last.

**Mandatory blocks:** PB-01, PB-02, PB-03, PB-06. These four are present on every single turn without exception. PB-01 and PB-02 because identity and principles never lapse. PB-03 because Interaction Context reconstruction (Layer 2 Section 6) happens unconditionally at the start of every turn, even when most of its fields are empty on a first turn. PB-06 because there is no turn without a user message to interpret.

**Optional blocks:** PB-05 (Recommendation Context). This block is omitted when Agent Action Computation has not yet produced a recommendable action — for example, on a turn that ends in `ASK_CLARIFICATION` (Section 10) before Capability Assessment ever runs, there is nothing to recommend.

**Conditional blocks:** PB-04 (Capability Context). Present whenever Target Resolution (Layer 2 Section 8) converges on a resolved target and Capability Assessment (Layer 2 Section 9) runs against it. Absent when Target Resolution does not converge (ambiguous or unresolved target, Layer 2 Section 8 rule 3–4) — in that case Capability Assessment is skipped entirely (Layer 2 Section 9 rule 8) and the turn proceeds straight to `ASK_CLARIFICATION`.

**Assembly constraints:**

1. No block may be assembled out of order. The fixed ordering in this section is invariant.
2. No block's content may be sourced from a prior turn's assembled prompt. Every block is rebuilt from the current Interaction Context and the current turn's freshly computed RO-2/RO-3/RO-4 (OAE-01).
3. A block that is optional or conditional and not populated this turn is omitted entirely from the assembled prompt — it is never included empty with placeholder text, since an empty placeholder could be misread as a meaningful absence-of-restriction or absence-of-recommendation signal.
4. PB-01 and PB-02 content is reproduced in full on every turn; it is never abbreviated, referenced by pointer, or assumed already known from an earlier turn in the same conversation.

---

## 5. Context Injection Rules

| Context Element | Injection Requirement |
|---|---|
| **Current Project Context** | Injected into PB-03 from RO-1's `current_project_reference` and `current_project_business_state` exactly as reconstructed in Layer 2 Section 6 step 2 for the current turn. If the prior Current Project Context referenced a Project now in `DELETED` state, the reference is cleared per Layer 2 Section 6 step 2 and PB-03 reflects no Current Project Context, not the stale reference. |
| **Current Specification Context** | Injected into PB-03 from RO-1's `current_specification_reference`. Follows the lifecycle of Current Project Context (M15 Discovery Assimilation KD-6): cleared whenever Current Project Context clears or changes; never injected as a standalone reference detached from its owning Project. |
| **Business State** | Injected into PB-03 as one of the five values defined in Layer 1 Section 5. Always refreshed from Project business-state observations obtained via delegation (Layer 2 Section 4) — never carried forward from a stale prior-turn value when a refresh is due (Layer 2 Section 6 step 2: "other states retain and refresh business_state"). |
| **Active Conversation Flow** | Injected into PB-03 from RO-1's `active_conversation_flow` whenever a multi-turn sequence (stepping through questions, exploring a Specification section by section, an Archive/Delete confirmation exchange) is in progress. Omitted from PB-03 when no such sequence is active, per the set/clear rules of Layer 2 Section 13 step 6. |
| **Capability Assessment** | Injected into PB-04 from RO-3's `resolved_target`, `assessment`, and `assessment_reason`, computed fresh this turn per Layer 2 Section 9. Never injected from a prior turn's assessment — Capability Assessment has no persistence (OAE-01); a new assessment is required even if the resolved target is unchanged from the previous turn. |
| **Agent Recommendation** | Injected into PB-05 from RO-4's computed action when that action is `RECOMMEND_ACTION`, or as supporting framing for `DELEGATE_REQUEST` / `ASK_CONFIRMATION` / `DISPLAY_INFORMATION`. Never injected ahead of Agent Action Computation completing — Recommendation Context is always downstream of, never a substitute for, the Layer 2 Section 10 ordered-condition evaluation. |

---

## 6. Conversation Guidance Rules

**Recommendation-first behavior.** The assembled prompt must lead the executing agent toward proposing exactly one next action when PB-05 is present, never a menu of options (OA-03 — Recommendation First; Layer 1 Section 8 — no menus, no command syntax). The executing agent recommends; it does not enumerate or command.

**Goal preservation.** PB-03's `user_goal_summary` field, when populated, must be treated as authoritative for what the user is trying to accomplish across the conversation, and must not be silently overwritten by a single turn's narrower request unless the user has explicitly revised their goal (OA-08 — Preserve User Goal; Layer 2 Section 13 step 4).

**Context continuity.** Across turns, PB-03's fields persist by default (OAE-05). The executing agent must treat an unpopulated or carried-forward field as meaningful continuity, not as missing information to be re-requested from the user. A referential reply ("yes," "that one," "the second option") is resolved against `pending_response_expectation`, not treated as a new, context-free request (Layer 2 Section 7 step 2).

**User guidance.** Whenever PB-05 is present, the executing agent must supply enough business-language context (consequence of the action, what the Business State means, what happens next) that the user can decide without needing to ask a follow-up question purely to understand the recommendation itself (OA-09 — User Guidance).

---

## 7. Business Language Rules

The assembled prompt — across every block — must never expose:

- Milestone or runtime identifiers (`M1` through `M13`, `RO-1` through `RO-4`, `OA-01` through `OA-14`, `OAE-01` through `OAE-07`, or any other internal label defined in Layer 1 or Layer 2).
- M1–M13 references of any kind, including command names (`/pipeline-run`, `/governance-resolve`, etc.), coordination states (`BASELINED`, `UNDER_REVISION`, `CLOSED`), or governance vocabulary (Verdict, Governing Situation, Policy Profile, ESCALATE, DELEGATE, DENY).
- Technical execution details: phase numbers, event types, file paths, artifact names, write-ordering rules, or any content that exists only inside an L1/L2 execution specification.
- Internal governance concepts: outcome IDs, policy versions, delegation tiers, closure paths (SUPERSEDED, EXPIRED, INVALIDATED), or any M12/M13 internal vocabulary.

This rule applies regardless of which block surfaces the content. PB-04's Restricted actions and PB-05's Recommendation Context are the two blocks most likely to be populated from a Capability Assessment or Delegation outcome that *internally* carries this vocabulary (Layer 2 Section 11, Boundary Invariant — no runtime naming, ever, in delegation or response generation); both blocks must carry the translated, business-facing equivalent only, using the always-translated table of Layer 1 Section 10 as the translation authority. The user receives only business-facing language, in every block, on every turn, with no exception carved out for "internal" or "debug" framing.

---

## 8. Exploration Behavior

| Exploration Type | Prompt Guidance |
|---|---|
| **Project Exploration** | When Capability Assessment allows an informational, no-target-mutation intent (Layer 2 Section 9 rule 1) against the Current Project Context, PB-04 reflects this as an Allowed action and PB-05 (if populated) frames it as available, never gated behind any other action (Layer 1 Section 12 — always optional, never gates progress). Available even when the Project's Business State is `ARCHIVED` (Layer 2 Section 9 rule 1 explicitly includes exploring archived projects). |
| **Specification Exploration** | Available whenever Current Specification Context is set and the owning Project's Business State is `SPECIFICATION_AVAILABLE` or `ARCHIVED` (Layer 1 Section 13). Requirement origins, Decision explanations, Source traceability, Section exploration, and Specification summaries are all informational intents; PB-04 reflects them as Allowed when the target resolves. |
| **Decision Explanation** | Treated as an informational intent under Capability Assessment rule 1. The executing agent answers in business language only (Section 7), translating any underlying decision rationale that originates from M1–M13 artifacts before it reaches PB-05 or the Business Response. |
| **Requirement Explanation** | Same treatment as Decision Explanation — informational, always allowed when the target (a Specification requirement) resolves, never requiring confirmation. |
| **Traceability Requests** | Requirement-to-source tracing (Layer 1 Section 13) is informational and always allowed when the Specification target resolves; PB-06's Resolved target carries the specific requirement or section the user is tracing. |

For every exploration type, PB-04 must reflect the action as `ALLOWED` (never `ALLOWED_WITH_CONFIRMATION`) — exploration is read-only and never gates on confirmation, per Layer 1 Section 9 (Exploration Is Optional, OA-11) and Layer 2 Section 9 rule 1.

---

## 9. Confirmation Behavior

| Action | Confirmation Requirement |
|---|---|
| **Archive** | Always `ALLOWED_WITH_CONFIRMATION`, never directly `ALLOWED` (Layer 2 Section 9 rule 3). PB-04 must mark Archive as requiring confirmation even when the user's phrasing sounds final ("archive it now"); PB-05's Recommended next step states the consequence — the Project or Specification becomes permanently read-only (Layer 1 Section 5, Archive Immutability) — before the agent proceeds. If the target is already `ARCHIVED`, the assessment is `DENIED` with reason "already in that state," not `ALLOWED_WITH_CONFIRMATION`. |
| **Delete** | In business language, "delete" is implemented as Archive (M15 Discovery Assimilation, Rejected Alternatives — Soft delete behavior). The same confirmation requirement and consequence framing as Archive applies; there is exactly one terminal, immutable state, not two. |
| **Project switching during active execution** | When `active_work_indicator` is set and the user's intent would change Current Project Context, Capability Assessment produces `ALLOWED_WITH_CONFIRMATION` (Layer 2 Section 9 rule 7). PB-05 must render the full four-part Active Execution Protection dialogue (Layer 1 Section 14): (1) inform the user the other Project has work in progress, (2) explain the consequence of switching now, (3) offer the alternative of waiting or returning to the in-progress Project first, (4) recommend a separate session if true concurrency is needed. The agent never silently switches Current Project Context while `active_work_indicator` is set. |
| **Other destructive actions** | Any action that mutates a Project or Specification away from its current state and cannot be reversed by the user through the same conversational surface is treated under the same `ALLOWED_WITH_CONFIRMATION` rule as Archive/Delete (OA-06 — Protect Destructive Actions). PB-05 must explain the consequence (OA-07) before the agent treats a subsequent affirmative reply as the confirming turn (Layer 2 Section 10 rule 4 — confirmation affirmation is matched against `pending_response_expectation`, never re-asked from scratch). |

---

## 10. Clarification Behavior

| Condition | Prompt Guidance |
|---|---|
| **Ambiguous intent** | When RO-2's `ambiguity_flag` is set because `intent_category` cannot be determined, PB-06 renders Resolved intent as explicitly unresolved. Capability Assessment is skipped (Layer 2 Section 9 rule 8); PB-04 is omitted. The agent's only available action is `ASK_CLARIFICATION` (Layer 2 Section 10 rule 1), phrased as a conversational question, never as a menu (Layer 1 Section 8). |
| **Ambiguous target** | When Target Resolution (Layer 2 Section 8 rule 4) finds more than one candidate for `target_reference`, PB-06 renders Resolved target as unresolved and lists the candidates only as conversational material for the clarifying question — never as a numbered selection menu. PB-04 is omitted; Capability Assessment does not run against an unresolved target. |
| **Insufficient context** | When neither Current Project Context nor an explicit reference in the current message supplies a usable target (Layer 2 Section 8 rule 2–3), the agent asks a clarifying question rather than guessing or defaulting to `DENIED`. `ASK_CLARIFICATION` is distinct from `REFUSE_REQUEST` — insufficient context is not a denial, it is a missing input (Layer 2 Section 8 rule 3). |

In every clarification case, `pending_response_expectation` is set on RO-1 (Layer 2 Section 13 step 5) so that the user's next message is interpreted as a referential reply to the clarifying question, not as a fresh, unrelated request.

---

## 11. Recommendation Behavior

The Operating Agent recommends; it does not command. PB-05's Recommended action is always phrased as a proposal the user may accept, decline, or redirect — never as an instruction the agent has already begun carrying out (OA-03 — Recommendation First).

**Recommendation principles:**

1. Exactly one action is recommended at a time. If more than one path forward exists, the agent recommends the single best one and only surfaces alternatives if the user asks or declines the first.
2. A recommendation is never issued without the User guidance the user needs to evaluate it (Section 6, User guidance).
3. A recommendation never bypasses Capability Assessment. PB-05 is never populated for an action that Capability Assessment marked `DENIED` (Layer 2 Section 10 rule 2 — denial routes to `REFUSE_REQUEST`, not to a softened recommendation).
4. A recommendation for an `ALLOWED_WITH_CONFIRMATION` action is rendered as a recommendation to take the action *and* a request for confirmation in the same turn — not as two separate turns — except where Layer 2 Section 10's ordered conditions already require the confirmation question to be asked first (rule 3) before the recommendation can be treated as accepted.
5. The agent's recommendation never depends on which Mode Signal (A or B) was inferred for the turn (OAE-07 — Mode Shapes Framing Not Logic); Mode Signal may change how the recommendation is framed conversationally, never which action is recommended.

---

## 12. Conversation Continuity

| Continuity Element | Requirement |
|---|---|
| **Current Project Context** | Persists across turns by default (OAE-05) until the user explicitly shifts it, the Project reaches `DELETED` (cleared, Layer 2 Section 6 step 2), or an Active Execution Protection dialogue resolves with the user choosing to switch (Section 9). |
| **Current Specification Context** | Persists alongside Current Project Context; cleared whenever the owning Project's context clears or changes (KD-6); never independently persisted once its owning Project Context is gone. |
| **Active Conversation Flow** | Set when a multi-turn sequence begins (Layer 2 Section 13 step 6) and must remain set, and reflected in PB-03, for every turn within that sequence until it concludes, is abandoned, or is declined. A follow-up turn inside an active flow is interpreted as continuation of that flow, never as an unrelated new request. |
| **Clarification Sessions** | A turn that produced `ASK_CLARIFICATION` sets `pending_response_expectation`; the next user turn is resolved against it first (Layer 2 Section 7 step 2) before being treated as a fresh intent classification. |
| **Question Answering Sessions** | Where the user is stepping through outstanding questions (Layer 1 Section 7, Question Handling) as part of an Active Conversation Flow, the flow remains active and PB-03 reflects it across every question in the sequence; it concludes only when the user finishes, defers, or explicitly exits the sequence. |

---

## 13. Prompt Constraints

The assembled prompt must satisfy all of the following on every turn:

- **Conversation-first.** No block presents the user with a structured menu or command syntax as the primary interaction surface (Layer 1 Section 8; M15 Discovery Assimilation, Rejected Alternatives — Menu-first interaction).
- **Intent-first.** PB-06's Resolved intent is established before any navigation or target-specific action is taken (OA-05 — Intent Before Navigation); PB-04 is never assembled ahead of intent resolution.
- **Business-language only.** Every block, without exception, complies with Section 7.
- **Context-aware.** PB-03 is never omitted and never assembled from anything other than the current turn's reconstructed Interaction Context (Section 4, mandatory blocks; Section 5).
- **Recommendation-first.** Whenever PB-05 is present, it proposes a single action per Section 11, never a list of equally-weighted options.

---

## 14. Validation

The assembled prompt for any given turn is valid only if all of the following hold:

1. **Dynamic prompt architecture used.** The prompt was assembled fresh from Interaction Context and the current turn's data via Prompt Context Assembly (Section 2); no block was reused verbatim from a prior turn's assembled prompt.
2. **Interaction Context represented.** PB-03 is present (it is mandatory, Section 4) and reflects the current turn's reconstructed RO-1, not a stale or partial copy.
3. **Current Project Context represented.** PB-03 carries `current_project_reference` and `current_project_business_state` exactly as reconstructed this turn (Section 5), including the explicit-empty case when no Project is current.
4. **Current Specification Context represented.** PB-03 carries `current_specification_reference` consistent with its owning Project Context's lifecycle (Section 5, KD-6).
5. **Active Conversation Flow represented.** PB-03 reflects `active_conversation_flow` accurately for the current turn — present and accurate when a multi-turn sequence is active, absent when none is active (Section 12).
6. **Capability context represented.** PB-04 is present whenever Target Resolution converged this turn and Capability Assessment ran (Section 4, conditional blocks), and is correctly omitted when it did not.
7. **Recommendation context represented.** PB-05 is present whenever Agent Action Computation produced a recommendable or confirmable action this turn, and correctly omitted on `ASK_CLARIFICATION` and `REFUSE_REQUEST` turns (Section 3, PB-05).
8. **Business language policy preserved.** No block, anywhere in the assembled prompt, contains a milestone reference, runtime identifier, technical execution detail, or internal governance concept (Section 7).
9. **Conversation continuity preserved.** Fields that should persist by default (OAE-05) are carried forward unchanged when no update applies this turn; fields tied to a concluding flow, expectation, or confirmation are correctly cleared per Layer 2 Section 13 (Section 12).
10. **Recommendation-first behavior preserved.** Every populated PB-05 proposes exactly one action, framed as a recommendation the user may accept, decline, or redirect — never as a command already underway (Section 11).

---

## References

```text
docs/commands/operating-agent.md                  — M15 Layer 1 Contract (approved)
docs/commands/operating-agent_execution.md        — M15 Layer 2 Execution Specification (approved)
(internal review note)       — M15 Discovery Assimilation (non-normative)
docs/project.md                                   — MVP Blueprint
docs/runtime_engineering_method.md                — CSR engineering method, four-layer architecture
docs/architecture/workspace_runtime.md            — M10 Layer 1 Contract
docs/architecture/workspace_runtime_execution.md  — M10 Layer 2 Execution Specification
docs/commands/pipeline-run.md                     — M11 Layer 1 Contract
docs/commands/pipeline-run_execution.md           — M11 Layer 2 Execution Specification
docs/commands/governance-run.md                   — M12 Layer 1 Contract
docs/commands/governance-run_execution.md         — M12 Layer 2 Execution Specification
docs/commands/governance-resolve.md               — M13 Layer 1 Contract
docs/commands/governance-resolve_execution.md     — M13 Layer 2 Execution Specification
docs/decisions/ADR-001-csr-language-policy.md     — language policy (canonical artifacts English; interaction surface in the user's language)
```
