# /evolve-specification

## Purpose

Update a BASELINED specification in response to upstream knowledge changes, without full regeneration.

EVOLVE Runtime v1 produces a Candidate V2 — an autonomous, complete specification assembled by targeted reconstruction of impacted sections only. The Candidate V2 is then submitted to the Specification Lifecycle Runtime for BASELINE V2 creation via `/specification-lifecycle BASELINE`.

This command implements EVOLVE Runtime v1 as defined in the WP-EVOLVE-1 Implementation Contract (ADR-EVOLVE-001 through ADR-EVOLVE-006).

**Implementation status:** WP-EVOLVE-1 COMPLETE. All phases P0–P7 implemented (P0+P1: WP-EVOLVE-1A; P2: WP-EVOLVE-1B; P3: WP-EVOLVE-1C; P4: WP-EVOLVE-1D; P5: WP-EVOLVE-1E; P6: WP-EVOLVE-1F; P7: WP-EVOLVE-1G).

---

## Supported Operation

| Operation | Trigger Condition | Description |
|---|---|---|
| EVOLVE | Specification is BASELINED, no active EVOLVE_PENDING | Produce Candidate V2 from targeted reconstruction; hand off to Lifecycle Runtime for BASELINE V2 |

---

## Phase Overview

| Phase | Name | Work Package | Status |
|---|---|---|---|
| P0 | Workspace Resolution | WP-EVOLVE-1A | IMPLEMENTED |
| P1 | Change Set Intake | WP-EVOLVE-1A | IMPLEMENTED |
| P2 | Impact Graph Computation | WP-EVOLVE-1B | IMPLEMENTED |
| P3 | Governance Classification | WP-EVOLVE-1C | IMPLEMENTED |
| P4 | Human Governance | WP-EVOLVE-1D | IMPLEMENTED |
| P5 | Candidate Assembly | WP-EVOLVE-1E | IMPLEMENTED |
| P6 | Lifecycle Handoff | WP-EVOLVE-1F | IMPLEMENTED |
| P7 | E6/E7 Integration | WP-EVOLVE-1G | IMPLEMENTED |

---

## Key Constraints

| Constraint | Source |
|---|---|
| EVOLVE requires an active BASELINED specification | EV-ARCH-06 |
| Nested EVOLVE prohibited — new EVOLVE blocked if EVOLVE_PENDING active | Phase P0 Step P0.2 |
| EVOLVE does not regenerate the full specification | ADR-EVOLVE-003 |
| EVOLVE does not edit Baseline V1 line by line | ADR-EVOLVE-003 |
| BASELINE V2 creation is the exclusive responsibility of `/specification-lifecycle BASELINE` | ADR-EVOLVE-004 |
| DENY items never participate in Candidate V2 content | ADR-EVOLVE-005, EV-ARCH-08 |

---

## Produced Artifacts

| Artifact | Path | Produced by |
|---|---|---|
| Change Set | `specifications/evolve/<evolve_id>_change_set.md` | Phase P1 (updated through P7) |
| Candidate V2 | `specifications/draft/<base>_specification_candidate_v2.md` | Phase P5 |
| SQF Gate Report V2 | `specifications/draft/sqf_gate_report_v2.md` | E7 V2 (during BASELINE) |

---

*WP-EVOLVE-1 COMPLETE. Full execution specification: `docs/commands/evolve-specification_execution.md`. Lifecycle integration (E6 V2 / E7 V2 / BASELINE V2): `docs/commands/specification-lifecycle_execution.md` — BASELINE V2 — EVOLVE_PENDING Mode section.*
