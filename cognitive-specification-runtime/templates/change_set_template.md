# Change Set

<!-- Template version: 1.1 — EVOLVE Runtime v1 / WP-EVOLVE-1F -->
<!-- Produced by: /evolve-specification Phase P1 (Change Set Intake) -->
<!-- Updated by: /evolve-specification Phases P2–P7 and /specification-lifecycle E7 V2 -->

**evolve_id:** EV-[workspace_id]-[YYYYMMDD]-[NNN]
**workspace_id:** [workspace_id]
**spec_base:** [base]
**evolve_status:** DRAFT
**produced_by:** /evolve-specification
**template_version:** 1.1

<!-- evolve_id format (EV-FR-021):
  EV-<workspace_id>-<YYYYMMDD>-<NNN>
  workspace_id  = active workspace identifier
  YYYYMMDD      = date of EVOLVE initiation (UTC)
  NNN           = sequence per workspace per day, zero-padded 3 digits (001, 002, ...)
  Example: EV-proj-demo-retail-20260702-001
-->

<!-- evolve_status values (EV-FR-022):
  DRAFT         — initialized at Phase P1 start (before filesystem write)
  IN_PROGRESS   — Phase P1 complete (Change Set written to filesystem)
  APPROVED      — governance complete: all items AUTO_APPLY or APPROVED
  PARTIAL_DENY  — governance complete: ≥1 DENY + ≥1 AUTO_APPLY or APPROVED
  DENIED        — governance complete: all items DENY (terminal — no Candidate V2 produced)
  FAILED        — error at any phase P1–P6 (terminal)
  COMPLETE      — BASELINE V2 confirmed by Specification Lifecycle Runtime (terminal)
  CANCELLED     — operator cancellation during EVOLVE_PENDING (terminal)
-->

<!-- evolve_status transition table (EV-FR-023a):
  DRAFT        → [Phase P1 initialized — Change Set written] → IN_PROGRESS
  IN_PROGRESS  → [governance complete — all APPROVED/AUTO_APPLY]  → APPROVED
  IN_PROGRESS  → [governance complete — ≥1 DENY + ≥1 APPROVED]   → PARTIAL_DENY
  IN_PROGRESS  → [governance complete — all DENY]                 → DENIED (terminal)
  IN_PROGRESS  → [error at phase P1–P6]                          → FAILED (terminal)
  APPROVED     → [BASELINE V2 confirmed by Lifecycle Runtime]     → COMPLETE (terminal)
  PARTIAL_DENY → [BASELINE V2 confirmed by Lifecycle Runtime]     → COMPLETE (terminal)
  APPROVED     → [operator cancellation during EVOLVE_PENDING]    → CANCELLED (terminal)
  PARTIAL_DENY → [operator cancellation during EVOLVE_PENDING]    → CANCELLED (terminal)

  Terminal states: DENIED, FAILED, COMPLETE, CANCELLED
  APPROVED and PARTIAL_DENY are transitional: persist from end of Phase P5
  until BASELINE V2 confirmation (→ COMPLETE) or cancellation (→ CANCELLED).
-->

---

## Section 1 — Metadata

| Champ | Valeur |
|---|---|
| evolve_id | EV-[workspace_id]-[YYYYMMDD]-[NNN] |
| workspace_id | [workspace_id] |
| spec_base | [base] |
| initiated_by | [actor name] |
| initiated_at | [YYYY-MM-DD HH:MM UTC] |
| evolve_status | DRAFT |
| failed_phase | — |
| lifecycle_handoff_event_id | — |

<!-- failed_phase: populated only when evolve_status = FAILED.
     Records the phase identifier at which the failure occurred (e.g., P2, P4).
     Value is "—" for all non-FAILED terminal states. (EV-FR-013)

lifecycle_handoff_event_id: populated by Phase P6 — Lifecycle Handoff.
     Value: EV<NNN> event ID in the Lifecycle Registry corresponding to the EVOLVE_PENDING event.
     Value is "—" until Phase P6 completes successfully. (EV-FR-073)
     Provides bidirectional traceability: Change Set ↔ Lifecycle Registry EVOLVE_PENDING event. -->

---

## Section 2 — Trigger

| Champ | Valeur |
|---|---|
| change_type | ADD \| MODIFY \| DEPRECATE \| REMOVE |
| affected_element_ids | [BR-NNN, FR-NNN, ...] |
| change_description | [Description libre du changement en amont de la base de connaissance] |
| upstream_source | [Référence : document, ADR, décision, note] |

<!-- change_type values and Decision Matrix mapping (EV-FR-061):
  ADD       — New upstream knowledge element created  → AUTO_APPLY
  MODIFY    — Existing element modified upstream       → ESCALATE (human review required)
  DEPRECATE — Existing element deprecated upstream     → ESCALATE (human review required)
  REMOVE    — Existing element removed upstream        → DENY

  STD cascade rules (EV-FR-031):
  MODIFY on BR-NNN   → cascades to FR-NNN (BR Source = this BR) + AC-NNN (FR Couvert = those FR)
  DEPRECATE on BR-NNN → same cascade as MODIFY (dependents require governance review)
  REMOVE on BR-NNN   → same cascade identification; cascade items receive ESCALATE verdict
  ADD                → no cascade (no existing elements depend on a new element)
-->

---

## Section 3 — Impact Summary

*[Populated by Phase P2 — Impact Graph Computation]*

| Champ | Valeur |
|---|---|
| impact_surface | [count of distinct impacted element IDs] |
| impacted_element_ids | [BR-NNN, FR-NNN, AC-NNN, NFR-NNN, ...] |
| preserved_section_ids | [Section N, Section M, ...] |
| dependency_chains | [description of cascade chains — e.g., BR-001 → FR-001 → AC-001] |

<!-- Impact Summary is the sole persistence of Impact Graph outputs (EV-FR-024).
     Must contain sufficient information to reconstruct the Impact Graph from Baseline V1.
     Invariant: same Baseline V1 + same Trigger = same Impact Graph. (EV-FR-035, EV-FR-036)
     The Impact Graph itself is NOT persisted as a standalone file (ADR-B4b-02). -->

---

## Section 4 — Detailed Changes

*[Phase P3 (Governance Classification): element_id, element_type, change_type, current_content, cascade_source, verdict, deny_reason. Phase P4 (Human Governance): proposed_content for ESCALATE items, verdict updated to Human-APPROVED/Human-DENIED. Phase P5 (Candidate Assembly): proposed_content for AUTO_APPLY items.]*

| element_id | element_type | change_type | current_content | proposed_content | cascade_source | verdict | deny_reason | reviewer_id | review_timestamp | review_rationale |
|---|---|---|---|---|---|---|---|---|---|---|
| [BR-NNN] | BR \| FR \| AC \| NFR | ADD \| MODIFY \| DEPRECATE \| REMOVE | [résumé contenu V1] | [résumé contenu proposé V2] | DIRECT \| [element_id] | AUTO_APPLY \| ESCALATE \| DENY \| Human-APPROVED \| Human-DENIED | — \| [raison si DENY] | — \| [reviewer name] | — \| [YYYY-MM-DD HH:MM UTC] | — \| [rationale text] |

<!-- element_type values: BR, FR, AC, NFR
     cascade_source: DIRECT = directly triggered by upstream change; or ID of triggering element

     verdict values per Change Item:
       AUTO_APPLY      — ADD: proceed to assembly without human review (EV-FR-037)
       ESCALATE        — MODIFY/DEPRECATE/REMOVE cascade: human review required (EV-FR-038, EV-FR-039, EV-FR-041)
       DENY            — REMOVE direct: excluded from Candidate V2 (EV-FR-040)
       Human-APPROVED  — ESCALATE item approved by human reviewer (Phase P4)
       Human-DENIED    — ESCALATE item denied by human reviewer; treated as DENY in aggregate (Phase P4)

     Columns reviewer_id, review_timestamp, review_rationale: populated by Phase P4 — Human Governance.
     Value "—" for all non-ESCALATE items (AUTO_APPLY, DENY) where no human review was performed.

     Items with verdict DENY or Human-DENIED must not appear in Candidate V2 content. (EV-FR-007) -->

---

## Section 5 — Governance Assessment

*[Populated at end of Phase P5 — governance complete, before Phase P6]*

| Champ | Valeur |
|---|---|
| aggregate_verdict | APPROVED \| PARTIAL_DENY \| DENIED |
| partial_deny | true \| false |
| human_review_required | true \| false |
| reviewer_id | [actor name or — if no human review] |
| review_timestamp | [YYYY-MM-DD HH:MM UTC or —] |

<!-- aggregate_verdict rules (EV-FR-066, ADR-EVOLVE-005):
  APPROVED      — all items AUTO_APPLY or Human-APPROVED
  PARTIAL_DENY  — ≥1 (DENY or Human-DENIED) AND ≥1 (AUTO_APPLY or Human-APPROVED)
  DENIED        — all items DENY or Human-DENIED → terminal, no Candidate V2 produced (EV-FR-068)

  PARTIAL_DENY is valid: Candidate V2 assembled with approved items only. (EV-FR-067) -->

---

## Section 6 — Stability Metrics

*[Element counts populated by Phase P5; SQF delta populated by E7 V2 during BASELINE]*

### 6.1 Element Counts

| Type | Count V1 | V2-added | V2-modified | DEPRECATED | Total V2 actif |
|---|---|---|---|---|---|
| BR | [n] | [n] | [n] | [n] | [n] |
| FR | [n] | [n] | [n] | [n] | [n] |
| AC | [n] | [n] | [n] | [n] | [n] |
| NFR | [n] | [n] | [n] | [n] | [n] |
| **Total** | [n] | [n] | [n] | [n] | [n] |

### 6.2 SQF Delta V1 → V2

*[Added by E7 V2 during /specification-lifecycle BASELINE — EV-FR-104]*

| Dimension | Statut V1 | Statut V2 | Delta |
|---|---|---|---|
| D1 | [PASS \| WARN \| BLOCK] | [PASS \| WARN \| BLOCK] | UNCHANGED \| IMPROVED \| DEGRADED |
| D3 | [PASS \| WARN \| BLOCK] | [PASS \| WARN \| BLOCK] | UNCHANGED \| IMPROVED \| DEGRADED |
| D5 | [PASS \| WARN \| NOT_APPLICABLE] | [PASS \| WARN \| NOT_APPLICABLE] | UNCHANGED \| IMPROVED \| DEGRADED |
| D6 | [PASS \| WARN \| NOT_APPLICABLE] | [PASS \| WARN \| NOT_APPLICABLE] | UNCHANGED \| IMPROVED \| DEGRADED |
| D7 | [PASS \| WARN \| BLOCK] | [PASS \| WARN \| BLOCK] | UNCHANGED \| IMPROVED \| DEGRADED |

<!-- SQF delta is informative only. It does not independently block BASELINE V2. (EV-FR-102)
     The gate decision is based on gate_status of sqf_gate_report_v2.md, not on the delta. -->
