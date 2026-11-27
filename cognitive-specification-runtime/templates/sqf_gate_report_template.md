# SQF Gate Report

<!-- Template version: 1.1 — SQF Phase 2 / Q-GATE-1 (D1 + D3 + D5 + D6 + D7) -->
<!-- Produced by: /generate-specification Phase 8.7 (D1 + D3 + D5 + D6) -->
<!-- Updated by: /specification-lifecycle E6 extension (D7) -->

**workspace_id:** [workspace_id]
**spec_base:** [base]
**spec_draft:** specifications/draft/[base]_specification.md
**generated:** [YYYY-MM-DD]
**sqf_phase:** Q-GATE-1
**sqf_version:** 1.1
**gate_status:** PENDING_D7 | PASS | WARN | BLOCK

<!-- gate_status values:
  PENDING_D7  — D1 + D3 evaluated; D7 not yet evaluated (pre-BASELINE)
  PASS        — All evaluated dimensions PASS
  WARN        — No BLOCK; at least one WARN dimension
  BLOCK       — At least one dimension = BLOCK; BASELINE refused
-->

---

## D1 — Complétude

<!-- Evaluated during /generate-specification Phase 7 -->

| Indicateur | Valeur | Seuil | Statut |
|---|---|---|---|
| I1.1 Taux KB→Spec | [count_traced]/[count_kb] = [pct]% | ≥ 90% → PASS / 75–89% → WARN / < 75% → BLOCK | PASS \| WARN \| BLOCK \| N/A |
| I1.2 Table hors-périmètre | PRESENT_WITH_ENTRIES \| PRESENT_EMPTY \| ABSENT | PRESENT_WITH_ENTRIES → PASS / PRESENT_EMPTY → WARN / ABSENT → BLOCK | PASS \| WARN \| BLOCK |
| I1.3 Points ouverts | ALL_RESOLVED \| DEFERRED \| UNRESOLVED \| NO_SECTION | ALL_RESOLVED / NO_SECTION → PASS / DEFERRED → WARN / UNRESOLVED → BLOCK | PASS \| WARN \| BLOCK |

<!-- I1.1 calculation:
  count_kb  = lines matching **BR-NNN**: in # Business Rules
            + lines matching **TR-NNN**: in # Technical Rules
            + lines matching **C-NNN**: in # Constraints
            (source: knowledge_base/extracted/<base>_knowledge.md or consolidated/)
  count_traced = traceability matrix rows where "Knowledge Artifact" column is non-empty AND != "—"
  If count_kb = 0 → I1.1 = N/A (WARN)
  If KB artifact absent → I1.1 = N/A (WARN)
-->

<!-- I1.2 detection:
  Search spec for heading: "Out of scope" | "Hors-périmètre" | "Hors périmètre" (case-insensitive)
  Found with ≥1 table row or list item → PRESENT_WITH_ENTRIES (PASS)
  Found with 0 entries → PRESENT_EMPTY (WARN)
  Not found → ABSENT (BLOCK)
-->

<!-- I1.3 detection:
  Search spec for heading: "Open points" | "Points ouverts" (case-insensitive)
  Not found → NO_SECTION (PASS)
  Found + closure statement ("All open points resolved" / "0 points ouverts") → ALL_RESOLVED (PASS)
  Found + 0 pending rows → ALL_RESOLVED (PASS)
  Found + all pending rows have deferral marker → DEFERRED (WARN)
  Found + at least one pending row without deferral → UNRESOLVED (BLOCK)
-->

**Score D1 :** L[0–4]
**D1 Gate Status :** PASS | WARN | BLOCK

<!-- D1 gate_status = worst_of(I1.1, I1.2, I1.3)
  Score: PASS → L3, WARN → L2, BLOCK (I1.1 ≥ 60%) → L1, BLOCK (I1.1 < 60%) → L0
-->

<!-- [Si WARN ou BLOCK : liste des éléments manquants ou partiels] -->

---

## D3 — Traçabilité

<!-- Evaluated during /generate-specification Phase 7 -->

| Indicateur | Valeur | Seuil | Statut |
|---|---|---|---|
| I3.1 Taux traçabilité table | [traced_rows]/[total_rows] = [pct]% | ≥ 95% → PASS / 80–94% → WARN / < 80% → BLOCK | PASS \| WARN \| BLOCK |
| I3.3 Couverture Provenance Index | [indexed_rows]/[total_rows] = [pct]% | ≥ 90% → PASS / 75–89% → WARN / < 75% → BLOCK | PASS \| WARN \| BLOCK |
| KPM Status | PROVENANCE_INDEXED \| NO_PROVENANCE_INDEX | — | — |

<!-- I3.1 calculation:
  total_rows   = count(data rows in traceability matrix, excluding header)
  op_rows      = count(rows whose ID matches ^OP-\d+$)
  scored_rows  = total_rows - op_rows        (R8 — see note below)
  traced_rows  = count(non-OP rows where "Knowledge Artifact" is non-empty AND != "—")
  I3.1         = traced_rows / scored_rows
  If scored_rows = 0 (matrix holds only open points) → WARN, never BLOCK
  If "Knowledge Artifact" column absent → I3.1 = 0% (BLOCK)
  If total_rows = 0 → I3.1 = EMPTY_MATRIX (BLOCK)
  Thresholds: ≥ 95% → PASS (L3 or L4), 80–94% → WARN (L2), < 80% → BLOCK (L1 or L0)
  Note: 100% → PASS (L4), 95–99% → PASS (L3)
-->

<!-- I3.3 calculation:
  Denominator excludes OP-NNN rows, exactly as I3.1 (R8).
  indexed_rows = count(non-OP rows where "Provenance" column is non-empty AND != "—")
  If KPM Status = NO_PROVENANCE_INDEX → I3.3 = WARN (never BLOCK — T-MODE)
  If "Provenance" column absent → I3.3 = WARN (never BLOCK — T-MODE)
  If KPM Status = PROVENANCE_INDEXED:
    ≥ 90% → PASS, 75–89% → WARN, < 75% → BLOCK
-->

**OP-NNN rows are excluded from both D3 denominators (R8, 2026-11-01).**

An `OP-NNN` row exists *because* something is unresolved, undefined or awaiting a decision. By construction it has no Knowledge Artifact and no Provenance entry — there is no settled knowledge to point at; that is what makes it an open point. Counting it as an untraced row makes I3.1 and I3.3 penalise the honest reporting of a gap, and rewards a specification that stays silent about what it does not know.

This was not theoretical. On `demo-inventory-01`, the OP-NNN rows **alone** produced the WARN recorded in lifecycle events EV001 and EV002:

| Base | With OP rows | Without |
|---|---|---|
| `cdc_demo-inventory` | 51/54 = 94% → **WARN** | 51/51 = 100% → PASS |
| `demo-inventory-mockup_transcript` | 21/24 = 88% → **WARN** | 21/21 = 100% → PASS |

Every other untraced row in the repository is a genuine traceability gap and still counts.

**Excluded, not hidden.** The count is reported alongside the indicator so an open point never becomes invisible by being discounted — Section 13 remains the place where it is answered for, and `csr-check` W4 still blocks a BLOCKING open point in a baselined spec.

**Score D3 :** L[0–4]
**D3 Gate Status :** PASS | WARN | BLOCK

<!-- D3 gate_status = worst_of(I3.1, I3.3)
  Exception: I3.3 in T-MODE is capped at WARN (never causes BLOCK)
-->

<!-- [Si WARN ou BLOCK : liste des lignes traceability sans source ou sans Provenance] -->

---

## D5 — Testabilité

<!-- Evaluated during /generate-specification Phase 8.7 -->
<!-- INFORMATIVE ONLY — statuts autorisés : PASS, WARN, NOT_APPLICABLE. BLOCK interdit. -->
<!-- NOT_APPLICABLE si template_mode = LEGACY (Section 7 AC absente) — neutre pour gate_status -->

| Indicateur | Valeur | Seuil | Statut |
|---|---|---|---|
| I5.1 Taux FR couverts par AC | [fr_covered]/[fr_total] = [pct]% | ≥ 80% → PASS / < 80% → WARN / STD absent → NOT_APPLICABLE | PASS \| WARN \| NOT_APPLICABLE |

<!-- I5.1 calculation:
  Source: Section 7 (AC-NNN table, "FR Couvert" column) + Section 6 (FR-NNN table)
  fr_total   = count(FR-NNN rows in Section 6 table)
  fr_covered = count(distinct FR-NNN values in "FR Couvert" column of Section 7 AC table)
  If template_mode = LEGACY → I5.1 = NOT_APPLICABLE
  If fr_total = 0 OR Section 7 absent → I5.1 = NOT_APPLICABLE
  pct = fr_covered / fr_total
  ≥ 80% → PASS  |  < 80% → WARN
  Thresholds bootstrapped (N=2). Recalibration required at B8-v2 (N ≥ 5 gate reports).
-->

**Score D5 :** L[0–4] | NOT_APPLICABLE
**D5 Gate Status :** PASS | WARN | NOT_APPLICABLE

<!-- D5 = NOT_APPLICABLE: excluded from gate_status computation (neutral) -->
<!-- D5 = WARN: contributes WARN to gate_status if no BLOCK from D1/D3/D7 -->

<!-- [Si WARN : liste des FR sans AC correspondant] -->

---

## D6 — Couverture Métier

<!-- Evaluated during /generate-specification Phase 8.7 -->
<!-- INFORMATIVE ONLY — statuts autorisés : PASS, WARN, NOT_APPLICABLE. BLOCK interdit. -->
<!-- NOT_APPLICABLE si template_mode = LEGACY (colonne "BR Source" absente) — neutre pour gate_status -->
<!-- Scope : BR-NNN uniquement. TR-NNN exclus du numérateur ET du dénominateur. -->

| Indicateur | Valeur | Seuil | Statut |
|---|---|---|---|
| I6.1 Taux BR couverts par FR | [br_covered]/[br_total] = [pct]% | ≥ 70% → PASS / < 70% → WARN / STD absent → NOT_APPLICABLE | PASS \| WARN \| NOT_APPLICABLE |

<!-- I6.1 calculation:
  Source: Section 6 (FR-NNN table, "BR Source" column) + Section 5.1 (BR-NNN table)
  br_total   = count(BR-NNN rows in Section 5.1 table) — TR-NNN excluded
  br_covered = count(distinct BR-NNN values in "BR Source" column of Section 6 FR table)
  If template_mode = LEGACY → I6.1 = NOT_APPLICABLE
  If br_total = 0 OR "BR Source" column absent from Section 6 → I6.1 = NOT_APPLICABLE
  pct = br_covered / br_total
  ≥ 70% → PASS  |  < 70% → WARN
  Thresholds bootstrapped (N=2). Recalibration required at B8-v2 (N ≥ 5 gate reports).
  PENDING_VALIDATION BRs without FR projection count as uncovered — intentional coverage signal.
-->

**Score D6 :** L[0–4] | NOT_APPLICABLE
**D6 Gate Status :** PASS | WARN | NOT_APPLICABLE

<!-- D6 = NOT_APPLICABLE: excluded from gate_status computation (neutral) -->
<!-- D6 = WARN: contributes WARN to gate_status if no BLOCK from D1/D3/D7 -->

<!-- [Si WARN : liste des BR sans FR source correspondant] -->

---

## D7 — Gouvernance des Inférences

*[Section ajoutée par E6 gate étendu lors du BASELINE check — /specification-lifecycle]*

<!-- Evaluated during /specification-lifecycle BASELINE E6 extension -->
<!-- Placeholder: this section is filled when /specification-lifecycle BASELINE is executed -->
<!-- If /specification-lifecycle BASELINE has not run, this section reads as below -->

| Indicateur | Valeur | Statut |
|---|---|---|
| I7.1 E6 gate status | PASS \| T_MODE \| FAIL | PASS \| WARN \| BLOCK |
| I7.3 Taux validation HITL | [validated]/[total] = [pct]% | PASS \| WARN |
| Éléments ID structural PENDING_VALIDATION | [count] | — |
| D7 — lecture indicative à la génération `[R11]` | PASS \| WARN \| BLOCK \| — | *(non contraignante)* |

<!-- I7.1 calculation (E6 gate extension):
  Read **KPM Status** from spec draft header
  If KPM Status = NO_PROVENANCE_INDEX → I7.1 = T_MODE (WARN)
  If KPM Status = PROVENANCE_INDEXED:
    Read "### INFERRED_DESIGN — Impact Structurel" from ## Inference Registry
    If any row has Statut = PENDING_VALIDATION → I7.1 = FAIL (BLOCK)
    Else → I7.1 = PASS
-->

<!-- I7.3 calculation:
  total_ir_entries = count(all rows across 4 IR subsections, excluding *(aucun élément)*)
  pending_entries  = count(rows where Statut = PENDING_VALIDATION)
  validated_entries = total_ir_entries - pending_entries
  I7.3 = validated_entries / total_ir_entries  (100% if total = 0 → PASS)
  100% or IR empty → PASS
  < 100% but 0 structural PENDING → WARN (implementation-level only)
  < 100% with structural PENDING → BLOCK (absorbed by I7.1 FAIL — coherence guaranteed)
-->

> **Lecture indicative vs évaluation `[R11, 2026-11-01]`.** D7 est **évalué** par l'extension E6 de `/specification-lifecycle` au BASELINE ; c'est la seule évaluation qui fait foi. `/generate-specification` en produit en plus une **lecture indicative**, à partir des mêmes entrées, parce que ses deux indicateurs lisent le registre d'inférences que la génération vient elle-même d'écrire.
>
> Sans elle, une spécification qui reste en draft — l'état normal de la plupart des spécifications, la plupart du temps — ne recevait **aucun** verdict D7, y compris quand ce verdict aurait été BLOCK. Le rapport affichait `PENDING_D7`, qu'un lecteur comprend comme « pas encore évalué » et non comme « ne passerait pas ».
>
> La lecture indicative **ne bloque rien**. Un draft qui porte des inférences structurelles non validées est *correct* : c'est ce pour quoi `PENDING_VALIDATION` existe, et bloquer la génération dessus rendrait impossible de produire l'artefact même dans lequel ces inférences sont consignées pour validation. Elle n'est pas non plus une preuve : E6 recalcule tout au BASELINE, et un BLOCK indicatif devient couramment un PASS réel une fois la session de validation tenue.

**Score D7 :** L[0–4]
**D7 Gate Status :** PASS | WARN | BLOCK

<!-- D7 gate_status:
  if I7.1 = BLOCK → D7 = BLOCK
  elif I7.1 = WARN (T_MODE) OR I7.3 = WARN → D7 = WARN
  else → D7 = PASS
  Score: PASS → L3, WARN → L2, BLOCK → L0 or L1
-->

<!-- [Si BLOCK : liste des éléments INFERRED_DESIGN structural PENDING_VALIDATION] -->

---

## Verdict Global

**D1 :** PASS | WARN | BLOCK
**D3 :** PASS | WARN | BLOCK
**D5 :** PASS | WARN | NOT_APPLICABLE
**D6 :** PASS | WARN | NOT_APPLICABLE
**D7 :** PASS | WARN | BLOCK | PENDING

**Gate Status Global :** PASS | WARN | BLOCK | PENDING_D7
**Décision BASELINE :** AUTORISÉ | AUTORISÉ AVEC RÉSERVES | REFUSÉ | EN ATTENTE D7

<!-- gate_status global rules:
  D5 / D6 are INFORMATIVE ONLY — BLOCK forbidden; NOT_APPLICABLE is neutral (excluded).
  if D7 not yet evaluated → gate_status = PENDING_D7
  if D1 = BLOCK OR D3 = BLOCK OR D7 = BLOCK → gate_status = BLOCK
  elif any of {D1, D3, D5, D6, D7} = WARN (NOT_APPLICABLE excluded) → gate_status = WARN
  else → gate_status = PASS
-->

<!-- Décision BASELINE:
  PASS  → AUTORISÉ
  WARN  → AUTORISÉ AVEC RÉSERVES (réserves documentées ci-dessous)
  BLOCK → REFUSÉ (dimensions bloquantes + actions requises ci-dessous)
  PENDING_D7 → EN ATTENTE D7 (exécuter /specification-lifecycle BASELINE)
-->

<!-- [Si WARN : liste des réserves documentées] -->
<!-- [Si BLOCK : dimension(s) bloquante(s) + action(s) requise(s)] -->
