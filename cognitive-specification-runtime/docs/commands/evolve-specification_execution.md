# /evolve-specification — Execution Specification

## Purpose

This document defines the execution behavior of the `/evolve-specification` command.

The Layer 1 contract (`docs/commands/evolve-specification.md`) defines what the command does. This document defines how it executes: the phase sequence, algorithms, file operations, validation procedures, and failure handling for each phase.

EVOLVE Runtime v1 operates in 7 sequential phases (P1–P7). This execution specification is implemented incrementally per work package.

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

Phase P2 is implemented (WP-EVOLVE-1B). Phase P3 is implemented (WP-EVOLVE-1C). Phase P4 is implemented (WP-EVOLVE-1D). Phase P5 is implemented (WP-EVOLVE-1E). Phase P6 is implemented (WP-EVOLVE-1F). Phase P7 is implemented (WP-EVOLVE-1G) — E6 V2 and E7 V2 integration with the Specification Lifecycle Runtime.

---

## Phase P0 — Workspace Resolution

Apply standard workspace resolution (W1–W5):

```text
W1: Read runtime/current_workspace.md → parse workspace_id
W2: WORKSPACE_ROOT = workspaces/<workspace_id>/
W3: Verify WORKSPACE_ROOT exists → BLOCKED if not found
W4: Validate registry entry in runtime/workspaces.md (R4a–R4e)
W5: All subsequent paths prefixed with WORKSPACE_ROOT
```

If workspace resolution fails at any step: stop immediately. Report:

```text
STATUS: BLOCKED — Workspace resolution failed at W<N>: <reason>
No Change Set created.
```

### Step P0.1 — Verify Baseline Eligibility

After workspace resolution, verify the workspace holds an active BASELINED specification for the target `<base>`:

1. Read Lifecycle Registry: `WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md`
2. Build `spec_state_index` (same as specification-lifecycle Phase 1 Step 1.2)
3. Look up `<base>` in `spec_state_index`
4. Verify `status = BASELINED`

If no BASELINED entry found for `<base>`:

```text
STATUS: BLOCKED — No active BASELINED specification found for base <base>.
EVOLVE requires an active BASELINED specification.
No Change Set created.
```

Record the Baseline V1 path as `baseline_v1_path` for use in subsequent phases.

### Step P0.2 — Check for Existing EVOLVE_PENDING

Scan the Lifecycle Registry event log for `<base>`. Check whether any existing EVOLVE_PENDING event has not been resolved by a subsequent BASELINE V2 event or an EVOLVE_CANCELLED event:

```text
For each event in event_log (reverse chronological order):
  if event.base == <base>:
    if event.event_type == EVOLVE_PENDING
       AND event.evolve_status ∈ {APPROVED, PARTIAL_DENY}:
      → BLOCKED (active EVOLVE_PENDING)
    if event.event_type == BASELINE and event.version > last_EVOLVE_PENDING_version:
      → No active EVOLVE_PENDING (prior one was resolved by BASELINE V2)
      → break
    if event.event_type == EVOLVE_CANCELLED:
      → No active EVOLVE_PENDING (prior EVOLVE was cancelled — WP-EVOLVE-2)
      → break
```

If an unresolved EVOLVE_PENDING is found:

```text
STATUS: BLOCKED — An EVOLVE_PENDING operation is already active for base <base>.
evolve_id: <evolve_id from existing event>
Resolve by running /specification-lifecycle BASELINE on the existing Candidate V2,
or cancel the active EVOLVE before initiating a new one.
No new Change Set created.
```

---

## Phase P1 — Change Set Intake

**Objective:** Create and persist the Change Set artifact before any impact computation begins. (EV-FR-001)

**Input:** Human-provided upstream change description.

**Output:** Change Set written to `WORKSPACE_ROOT/specifications/evolve/<evolve_id>_change_set.md` with `evolve_status = IN_PROGRESS`. (EV-FR-001, EV-FR-023)

**Contract references:** EV-FR-001, EV-FR-002, EV-FR-013, EV-FR-020, EV-FR-021, EV-FR-022, EV-FR-023, EV-FR-023a, EV-FR-024, EV-FR-025, EV-FR-026

---

### Step P1.1 — Collect Trigger Input

Request the following from the human initiator (EV-FR-002):

```text
[1] change_type           : ADD | MODIFY | DEPRECATE | REMOVE
[2] affected_element_ids  : comma-separated list of upstream knowledge element IDs
                            (e.g., BR-003, TR-007)
[3] change_description    : free-text description of the upstream change
[4] upstream_source       : reference — document, ADR, decision record, or note
[5] initiator_name        : actor name
```

**Validation:**

| Field | Rule |
|---|---|
| `change_type` | Must be exactly one of: ADD, MODIFY, DEPRECATE, REMOVE |
| `affected_element_ids` | Non-empty; each ID matches pattern `[A-Z]+-[0-9]+` (e.g., BR-003) |
| `change_description` | Non-empty string |
| `initiator_name` | Non-empty string |

If any required field is missing or invalid, stop without creating Change Set:

```text
STATUS: BLOCKED — Change Set Intake cannot proceed.
Invalid or missing: <field_name> — <reason>
No Change Set created.
```

---

### Step P1.2 — Generate evolve_id

Generate `evolve_id` following format `EV-<workspace_id>-<YYYYMMDD>-<NNN>` (EV-FR-021):

```text
workspace_id = value from Phase P0 Step W1
YYYYMMDD     = current date UTC (format YYYYMMDD, e.g., 20260702)
NNN          = sequence number, zero-padded to 3 digits

NNN derivation:
  Scan WORKSPACE_ROOT/specifications/evolve/ for files matching:
    EV-<workspace_id>-<YYYYMMDD>-*.md
  NNN = count(matching files) + 1
  If no matching files exist: NNN = 001
```

Example: `EV-proj-demo-retail-20260702-001`

---

### Step P1.3 — Create evolve Directory

Check whether `WORKSPACE_ROOT/specifications/evolve/` exists. (EV-FR-026)

If the directory does not exist: create it before proceeding.

If directory creation fails:

```text
STATUS: BLOCKED — Cannot create directory: WORKSPACE_ROOT/specifications/evolve/
Error: <reason>
No Change Set created.
```

---

### Step P1.4 — Instantiate Change Set (evolve_status = DRAFT)

Using template `templates/change_set_template.md`, instantiate the Change Set with the following field values:

**Section 1 — Metadata:**

| Field | Value |
|---|---|
| evolve_id | Generated in Step P1.2 |
| workspace_id | From Phase P0 |
| spec_base | `<base>` target |
| initiated_by | `initiator_name` from Step P1.1 |
| initiated_at | Current timestamp UTC (YYYY-MM-DD HH:MM UTC) |
| evolve_status | `DRAFT` |
| failed_phase | — |

**Section 2 — Trigger:**

| Field | Value |
|---|---|
| change_type | From Step P1.1 |
| affected_element_ids | From Step P1.1 |
| change_description | From Step P1.1 |
| upstream_source | From Step P1.1 |

**Sections 3–6:** Initialize with placeholder content as defined in `templates/change_set_template.md`. These sections will be populated by Phases P2–P7 and E7 V2.

---

### Step P1.5 — Write Change Set to Filesystem

Write the instantiated Change Set to: (EV-FR-025)

```text
WORKSPACE_ROOT/specifications/evolve/<evolve_id>_change_set.md
```

Confirm the file is written and readable before proceeding.

The Change Set must be on the filesystem before any impact computation begins. (EV-FR-001)

If the write fails:

```text
STATUS: FAILED — Change Set could not be written to filesystem.
Path  : WORKSPACE_ROOT/specifications/evolve/<evolve_id>_change_set.md
Error : <reason>
```

Update Change Set `evolve_status = FAILED` and `failed_phase = P1` if a partial file was written. (EV-FR-013)

---

### Step P1.6 — Update evolve_status to IN_PROGRESS

Update the `evolve_status` field in the Change Set from `DRAFT` to `IN_PROGRESS`. (EV-FR-023, EV-FR-023a)

Transition: `DRAFT → [Phase P1 initialisée — Change Set written to filesystem] → IN_PROGRESS`

Re-write the Change Set with `evolve_status = IN_PROGRESS`.

---

### Step P1.7 — Phase P1 Completion Report

```text
PHASE P1 COMPLETE — Change Set Intake

evolve_id     : <evolve_id>
workspace_id  : <workspace_id>
spec_base     : <base>
change_type   : <change_type>
affected_ids  : <affected_element_ids>
evolve_status : IN_PROGRESS
change_set    : WORKSPACE_ROOT/specifications/evolve/<evolve_id>_change_set.md

→ Next: Phase P2 — Impact Graph Computation
```

---

## Phase P2 — Impact Graph Computation

**Objective:** Compute the complete set of specification elements impacted by the upstream change, including cascade chains derived from STD element dependencies. Persist outputs exclusively in Change Set Section 3. (EV-FR-003, EV-FR-029)

**Input:**
- Baseline V1 specification: path = `baseline_v1_path` (recorded in Phase P0 Step P0.1)
- Change Set Section 2 — Trigger: `change_type`, `affected_element_ids`

**Output:** Change Set Section 3 (Impact Summary) populated with `impact_surface`, `impacted_element_ids`, `preserved_section_ids`, `dependency_chains`. (EV-FR-004, EV-FR-005, EV-FR-036)

**Determinism invariant:** This phase is purely functional. Given the same Baseline V1 content and the same Trigger input, Phase P2 produces identical outputs on every execution. No timestamps, random values, or external state are used in the computation. (EV-FR-035)

**Contract references:** EV-FR-003, EV-FR-004, EV-FR-005, EV-FR-027, EV-FR-028, EV-FR-029, EV-FR-030, EV-FR-031, EV-FR-032, EV-FR-033, EV-FR-034, EV-FR-035, EV-FR-036

---

### Step P2.1 — Load Baseline V1

Read the specification file at `baseline_v1_path`. (EV-FR-027)

Detect `template_mode`:

```text
STD Detection:
  If the file's first non-empty line is exactly `---` (YAML front matter marker):
    template_mode = STD
  Else:
    template_mode = LEGACY
```

If the file cannot be read:

```text
STATUS: FAILED — Cannot read Baseline V1 specification.
Path  : <baseline_v1_path>
Error : <reason>
→ Update Change Set: evolve_status = FAILED, failed_phase = P2
Stop.
```

---

### Step P2.2 — Build Element Index

**For template_mode = LEGACY:** Skip Step P2.2. Cascade rules do not apply in LEGACY mode (no structured "BR Source" or "FR Couvert" columns). Proceed directly to Step P2.4.

**For template_mode = STD:**

Parse the Baseline V1 specification. Extract element IDs and inter-element dependencies from Markdown tables.

**BR Index** (Section 5.1 — heading contains "Règles de Gestion"):

```text
br_ids = []
For each Markdown table row in Section 5.1:
  If ID column value matches pattern ^BR-[0-9]+$:
    Add to br_ids
```

**TR Index** (Section 5.2 — heading contains "Exigences Techniques"):

```text
tr_ids = []
For each Markdown table row in Section 5.2:
  If ID column value matches pattern ^TR-[0-9]+$:
    Add to tr_ids
```

**FR Index** (Section 6 — heading contains "Exigences Fonctionnelles"):

```text
fr_index = {}   (fr_id → list of br_sources)
For each Markdown table row in Section 6:
  If ID column value matches pattern ^FR-[0-9]+$:
    Extract "BR Source" column value
    Parse comma-separated BR-NNN identifiers → br_sources_list
    fr_index[fr_id] = br_sources_list
```

**AC Index** (Section 7 — heading contains "Critères d'Acceptation"):

```text
ac_index = {}   (ac_id → list of fr_couvert)
For each Markdown table row in Section 7:
  If ID column value matches pattern ^AC-[0-9]+$:
    Extract "FR Couvert" column value
    Parse comma-separated FR-NNN identifiers → fr_couvert_list
    ac_index[ac_id] = fr_couvert_list
```

**NFR Index** (Section 8 — heading contains "Non-Fonctionnelles"):

```text
nfr_ids = []
For each Markdown table row in Section 8:
  If ID column value matches pattern ^NFR-[0-9]+$:
    Add to nfr_ids
```

**Section Element Map** (used in Step P2.7 for preserved_section_ids):

```text
section_element_map = {
  "Section 5.1": br_ids,
  "Section 5.2": tr_ids,
  "Section 6":   list(fr_index.keys()),
  "Section 7":   list(ac_index.keys()),
  "Section 8":   nfr_ids,
}
Sections 1, 2, 3, 4, 9, and beyond: no tracked elements → always preserved.
```

---

### Step P2.3 — Validate affected_element_ids

For each element_id in `affected_element_ids` (from Change Set Section 2):

```text
Determine element_type by ID prefix:
  ^BR-[0-9]+$  → type = BR
  ^TR-[0-9]+$  → type = TR
  ^FR-[0-9]+$  → type = FR
  ^AC-[0-9]+$  → type = AC
  ^NFR-[0-9]+$ → type = NFR
  (other)      → type = UNKNOWN → emit warning, treat as DIRECT impact only:
                 "WARN: Unknown element type for <id> — treated as DIRECT impact only"

In STD mode: verify element exists in Element Index.
  If not found in index → emit warning:
  "WARN: <element_id> not found in Baseline V1 element tables — treated as DIRECT impact only"
```

Warnings do not stop execution.

---

### Step P2.4 — Initialize Direct Impact Set

```text
impacted_set = ordered set
cascade_map  = {}   (element_id → "DIRECT" or <source_element_id>)

For each element_id in affected_element_ids:  (EV-FR-030)
  impacted_set.add(element_id)
  cascade_map[element_id] = "DIRECT"
```

---

### Step P2.5 — Apply Cascade Rules

**For change_type = ADD:**

```text
No cascade. impacted_set = affected_element_ids only. (EV-FR-031)
Proceed to Step P2.6.
```

**For change_type ∈ {MODIFY, DEPRECATE, REMOVE} and template_mode = STD:** (EV-FR-031, EV-FR-032)

```text
For each element_id in affected_element_ids:
  element_type = type determined in Step P2.3

  If element_type = BR:

    FR cascade — Level 1:
      For each (fr_id, br_sources) in fr_index:
        If element_id ∈ br_sources AND fr_id ∉ impacted_set:
          impacted_set.add(fr_id)
          cascade_map[fr_id] = element_id

    AC cascade — Level 2:
      fr_ids_from_this_cascade = [fr_id added during FR cascade above for this element_id]
      For each fr_id in fr_ids_from_this_cascade:
        For each (ac_id, fr_couvert) in ac_index:
          If fr_id ∈ fr_couvert AND ac_id ∉ impacted_set:
            impacted_set.add(ac_id)
            cascade_map[ac_id] = fr_id

  If element_type = FR:

    AC cascade — Level 1:
      For each (ac_id, fr_couvert) in ac_index:
        If element_id ∈ fr_couvert AND ac_id ∉ impacted_set:
          impacted_set.add(ac_id)
          cascade_map[ac_id] = element_id

  If element_type ∈ {TR, AC, NFR}:
    No cascade. Leaf elements or no tracked downstream dependencies.
```

**For change_type ∈ {MODIFY, DEPRECATE, REMOVE} and template_mode = LEGACY:**

```text
No cascade. impacted_set = affected_element_ids only.
LEGACY specs have no structured BR Source / FR Couvert columns.
```

**Note on REMOVE:** Phase P2 cascade identification for REMOVE is identical to MODIFY and DEPRECATE. The rule that cascade items receive ESCALATE verdict (rather than DENY) is enforced by Phase P4 (Decision Matrix). Phase P2 does not assign verdicts.

---

### Step P2.6 — Compute Impact Surface

```text
impact_surface        = len(impacted_set)  (EV-FR-033)
impacted_element_ids  = sorted(impacted_set)
                        (ascending alphanumeric sort per element prefix: BR < FR < AC < NFR < TR)
```

---

### Step P2.7 — Compute Preserved Sections

**For template_mode = STD:** (EV-FR-034)

```text
preserved_section_ids = []

For sections with tracked elements (section_element_map):
  For each (section_id, elements) in section_element_map:
    overlap = [e for e in elements if e in impacted_set]
    If len(overlap) == 0:
      preserved_section_ids.append(section_id)

For sections without tracked elements (1, 2, 3, 4, 9, and beyond):
  Always add to preserved_section_ids.

Result: sorted list of all preserved section IDs.
```

**For template_mode = LEGACY:**

```text
preserved_section_ids = ["N/A — LEGACY mode, no section element map"]
```

---

### Step P2.8 — Build Dependency Chain Descriptions

```text
chains = []

For each element_id in affected_element_ids (in input order):
  chain = "<element_id> (DIRECT)"

  If change_type ∈ {MODIFY, DEPRECATE, REMOVE} and template_mode = STD:
    cascaded_fr = sorted([fr_id for fr_id in impacted_set
                          if cascade_map.get(fr_id) == element_id])
    cascaded_ac = sorted([ac_id for ac_id in impacted_set
                          if cascade_map.get(ac_id) in cascaded_fr])

    If cascaded_fr is non-empty:
      chain += " → " + join(cascaded_fr, ", ")
    If cascaded_ac is non-empty:
      chain += " → " + join(cascaded_ac, ", ")

  chains.append(chain)

dependency_chains = join(chains, " / ")
```

Example outputs:

```text
MODIFY BR-001                   →  "BR-001 (DIRECT) → FR-001, FR-002 → AC-001, AC-002"
DEPRECATE BR-001                →  "BR-001 (DIRECT) → FR-001, FR-002 → AC-001, AC-002"
REMOVE BR-001                   →  "BR-001 (DIRECT) → FR-001 → AC-001"
ADD BR-003                      →  "BR-003 (DIRECT)"
MODIFY FR-003                   →  "FR-003 (DIRECT) → AC-005, AC-006"
MODIFY BR-001, BR-002 (multi)   →  "BR-001 (DIRECT) → FR-001 → AC-001 / BR-002 (DIRECT) → FR-002 → AC-002"
```

---

### Step P2.9 — Update Change Set Section 3

Update Section 3 — Impact Summary in the Change Set file at:

```text
WORKSPACE_ROOT/specifications/evolve/<evolve_id>_change_set.md
```

Replace the placeholder marker and placeholder rows with computed values: (EV-FR-036)

```markdown
## Section 3 — Impact Summary

| Champ | Valeur |
|---|---|
| impact_surface | <impact_surface> |
| impacted_element_ids | <impacted_element_ids, comma-separated> |
| preserved_section_ids | <preserved_section_ids, comma-separated> |
| dependency_chains | <dependency_chains string> |
```

If the write fails:

```text
STATUS: FAILED — Cannot update Change Set Section 3.
Path  : WORKSPACE_ROOT/specifications/evolve/<evolve_id>_change_set.md
Error : <reason>
→ evolve_status = FAILED, failed_phase = P2
Stop.
```

---

### Step P2.10 — Phase P2 Completion Report

```text
PHASE P2 COMPLETE — Impact Graph Computation

evolve_id          : <evolve_id>
template_mode      : <STD | LEGACY>
change_type        : <change_type>
affected_ids       : <affected_element_ids>
impact_surface     : <impact_surface>
impacted_ids       : <impacted_element_ids>
preserved_sections : <preserved_section_ids>
dependency_chains  : <dependency_chains>

→ Next: Phase P3 — Candidate Generation
```

---

## Phase P3 — Governance Classification

**Objective:** Classify each element in the impacted set as AUTO_APPLY, ESCALATE, or DENY based on its change_type and cascade role. Populate Change Set Section 4 (Detailed Changes) and Section 5 (Governance Assessment). Update `evolve_status` when governance is deterministically complete at Phase P3.

**Input:**
- Change Set Section 2: `change_type`, `affected_element_ids`
- Change Set Section 3: `impacted_element_ids`
- Baseline V1 specification at `baseline_v1_path`

**Output:**
- Change Set Section 4 — per-element rows with `verdict`, `current_content`, `cascade_source`
- Change Set Section 5 — `aggregate_verdict`, `human_review_required`
- Change Set Section 1 — `evolve_status` updated if governance is complete at P3

**Contract references:** EV-FR-037, EV-FR-038, EV-FR-039, EV-FR-040, EV-FR-041, EV-FR-042, EV-FR-043

---

### Classification Rules

| change_type | Role | Verdict | EV-FR |
|---|---|---|---|
| ADD | DIRECT | AUTO_APPLY | EV-FR-037 |
| MODIFY | DIRECT | ESCALATE | EV-FR-038 |
| MODIFY | CASCADE | AUTO_APPLY | EV-FR-038 |
| DEPRECATE | DIRECT | ESCALATE | EV-FR-039 |
| DEPRECATE | CASCADE | ESCALATE | EV-FR-039 |
| REMOVE | DIRECT | DENY | EV-FR-040 |
| REMOVE | CASCADE | ESCALATE | EV-FR-041 |

Role = "DIRECT" if `element_id ∈ affected_element_ids`; "CASCADE" otherwise.

---

### Step P3.1 — Read Change Set State

Read the Change Set at `WORKSPACE_ROOT/specifications/evolve/<evolve_id>_change_set.md`.

Extract:
- Section 2: `change_type`, `affected_element_ids`
- Section 3: `impacted_element_ids`

Derive:

```text
direct_ids  = set(affected_element_ids)
cascade_ids = set(impacted_element_ids) − direct_ids
all_ids     = list(impacted_element_ids)  (DIRECT elements listed first, CASCADE elements after)
```

If Change Set cannot be read or `evolve_status ≠ IN_PROGRESS`:

```text
STATUS: BLOCKED — Change Set not in expected state for Phase P3.
Reason: <evolve_status value or read error>
No modification to Change Set.
Stop.
```

---

### Step P3.2 — Load Baseline V1

Read Baseline V1 at `baseline_v1_path`. Detect `template_mode` (same STD detection as Step P2.1).

**For template_mode = STD:** Build `fr_index` and `ac_index` (same algorithm as Step P2.2 — fr_index: FR-id → br_sources; ac_index: AC-id → fr_couvert list).

Build **content_map** for the `current_content` column in Section 4:

```text
For each element_id in all_ids:
  Locate the table row for element_id in its section in Baseline V1
  Extract description column value (second column after ID)
  content_map[element_id] = value, truncated to 120 characters (append "…" if truncated)
```

**For template_mode = LEGACY:** Skip index build. `content_map[element_id] = "[LEGACY — manual review required]"` for all elements.

If Baseline V1 cannot be read:

```text
STATUS: FAILED — Cannot read Baseline V1 specification.
→ evolve_status = FAILED, failed_phase = P3
Stop.
```

---

### Step P3.3 — Derive cascade_source per element

```text
cascade_source_map = {}

For element_id in direct_ids:
  cascade_source_map[element_id] = "DIRECT"

For element_id in cascade_ids (template_mode = STD only):

  If element_id prefix = FR:
    Find br_id such that br_id ∈ direct_ids AND br_id ∈ fr_index[element_id].br_sources
    cascade_source_map[element_id] = br_id  (the direct BR that triggered this FR)
    If no such br_id found: cascade_source_map[element_id] = "UNKNOWN_SOURCE"

  If element_id prefix = AC:
    Try: find fr_id in cascade_ids such that fr_id ∈ ac_index[element_id].fr_couvert
    If found: cascade_source_map[element_id] = fr_id       (intermediate cascade FR)
    Else:
      find fr_id in direct_ids such that fr_id ∈ ac_index[element_id].fr_couvert
      cascade_source_map[element_id] = fr_id if found else "UNKNOWN_SOURCE"

For element_id in cascade_ids (template_mode = LEGACY):
  cascade_source_map[element_id] = "UNKNOWN_SOURCE — LEGACY mode"
```

---

### Step P3.4 — Classify each element

```text
For each element_id in all_ids:
  role         = "DIRECT" if element_id ∈ direct_ids else "CASCADE"
  element_type = prefix of element_id  (BR / FR / AC / NFR / TR)

  verdict = lookup Classification Rules table above using (change_type, role)

  deny_reason:
    If verdict = DENY: "REMOVE — element excluded from Candidate V2"
    Else: "—"

  proposed_content:
    If verdict = AUTO_APPLY: "[To be generated — Phase P5 Candidate Assembly]"
    If verdict = ESCALATE:   "[Pending human review — Phase P4 Human Governance]"
    If verdict = DENY:       "DENIED — excluded from Candidate V2"
```

---

### Step P3.5 — Write Change Set Section 4

Remove the placeholder content in Section 4 (placeholder note + example row).

Write one table row per element in `all_ids`: (EV-FR-043)

```markdown
## Section 4 — Detailed Changes

| element_id | element_type | change_type | current_content | proposed_content | cascade_source | verdict | deny_reason |
|---|---|---|---|---|---|---|---|
| <element_id> | <type> | <trigger change_type> | <content_map[element_id]> | <proposed_content> | <cascade_source_map[element_id]> | <verdict> | <deny_reason> |
```

The `change_type` column uses the trigger `change_type` from Section 2 for all rows (all elements are impacted by the same upstream trigger).

If write fails:

```text
STATUS: FAILED — Cannot write Change Set Section 4.
→ evolve_status = FAILED, failed_phase = P3
Stop.
```

---

### Step P3.6 — Compute Governance Assessment

```text
auto_apply_count = count(rows where verdict = AUTO_APPLY)
escalate_count   = count(rows where verdict = ESCALATE)
deny_count       = count(rows where verdict = DENY)

human_review_required = (escalate_count > 0)

If escalate_count > 0:
  aggregate_verdict = "[Pending Phase P4 — Human Governance]"
  partial_deny      = (deny_count > 0)

Elif deny_count = 0:                                  (all AUTO_APPLY)
  aggregate_verdict = "APPROVED"                      (EV-FR-042)
  partial_deny      = false

Elif auto_apply_count = 0:                            (all DENY)
  aggregate_verdict = "DENIED"                        (EV-FR-042)
  partial_deny      = false

Else:                                                 (mix DENY + AUTO_APPLY, no ESCALATE)
  aggregate_verdict = "PARTIAL_DENY"                  (EV-FR-042, ADR-EVOLVE-005)
  partial_deny      = true
```

---

### Step P3.7 — Write Change Set Section 5

Replace placeholder in Section 5 with computed values: (EV-FR-043)

```markdown
## Section 5 — Governance Assessment

| Champ | Valeur |
|---|---|
| aggregate_verdict | <aggregate_verdict> |
| partial_deny | <true \| false> |
| human_review_required | <true \| false> |
| reviewer_id | — |
| review_timestamp | — |
```

If write fails:

```text
STATUS: FAILED — Cannot write Change Set Section 5.
→ evolve_status = FAILED, failed_phase = P3
Stop.
```

---

### Step P3.8 — Update evolve_status

```text
If aggregate_verdict = "APPROVED":
  Update Section 1: evolve_status = APPROVED
  Transition: IN_PROGRESS → [governance complete — all AUTO_APPLY] → APPROVED

If aggregate_verdict = "PARTIAL_DENY":
  Update Section 1: evolve_status = PARTIAL_DENY
  Transition: IN_PROGRESS → [governance complete — ≥1 DENY + ≥1 AUTO_APPLY] → PARTIAL_DENY

If aggregate_verdict = "DENIED":
  Update Section 1: evolve_status = DENIED
  Transition: IN_PROGRESS → [governance complete — all DENY] → DENIED (terminal)

If aggregate_verdict = "[Pending Phase P4 — Human Governance]":
  evolve_status remains IN_PROGRESS
  (governance is not yet complete — Phase P4 updates evolve_status after human decisions)
```

If `aggregate_verdict = "DENIED"` — emit terminal report and stop:

```text
STATUS: EVOLVE DENIED
evolve_id        : <evolve_id>
aggregate_verdict: DENIED
All <deny_count> item(s) received verdict DENY.
No Candidate V2 will be produced.
Change Set preserved at: WORKSPACE_ROOT/specifications/evolve/<evolve_id>_change_set.md
Specification remains BASELINED. EVOLVE_PENDING is NOT set.
```

---

### Step P3.9 — Phase P3 Completion Report

```text
PHASE P3 COMPLETE — Governance Classification

evolve_id             : <evolve_id>
change_type           : <change_type>
items_classified      : <total>
  AUTO_APPLY          : <auto_apply_count>
  ESCALATE            : <escalate_count>
  DENY                : <deny_count>
human_review_required : <true | false>
aggregate_verdict     : <APPROVED | PARTIAL_DENY | DENIED | Pending Phase P4>
evolve_status         : <updated value>

→ Phase P4 — Human Governance          [if human_review_required = true]
→ Phase P5 — Candidate V2 Assembly     [if aggregate ∈ {APPROVED, PARTIAL_DENY} and no ESCALATE]
→ EVOLVE DENIED — operation complete   [if aggregate_verdict = DENIED]
```

---

## Phase P4 — Human Governance

**Objective:** Resolve all ESCALATE items from Phase P3 through human review. Collect APPROVE or DENY decisions per item, update verdicts with full traceability fields, and compute the final aggregate_verdict.

**Trigger:** Phase P4 executes only if `human_review_required = true` in Change Set Section 5. If `human_review_required = false`, Phase P4 is SKIPPED and the flow proceeds to Phase P5. (EV-FR-044)

**Input:**
- Change Set: all sections; specifically Section 4 rows with `verdict = ESCALATE`
- Human reviewer: APPROVE/DENY decisions, reviewer_id, review_rationale per item

**Output:**
- Change Set Section 4 — ESCALATE rows updated to Human-APPROVED or Human-DENIED, with `reviewer_id`, `review_timestamp`, `review_rationale`
- Change Set Section 5 — final `aggregate_verdict`, `reviewer_id`, `review_timestamp`
- Change Set Section 1 — `evolve_status` updated to final state

**Contract references:** EV-FR-044, EV-FR-045, EV-FR-046, EV-FR-047, EV-FR-048, EV-FR-049, EV-FR-050, EV-FR-051, EV-FR-052, EV-FR-053, EV-FR-054, EV-FR-055

---

### Step P4.0 — Skip Check

Read Change Set Section 5: `human_review_required`. (EV-FR-044)

If `human_review_required = false`:

```text
Phase P4 SKIPPED — human_review_required = false
No ESCALATE items. Governance was complete at Phase P3.
evolve_status: <value set by Phase P3>
→ Proceed to Phase P5 — Candidate Assembly
```

---

### Step P4.1 — Read Change Set State

Extract from Change Set:
- Section 1: `evolve_id`, `evolve_status` (must be `IN_PROGRESS`)
- Section 2: `change_type`, `affected_element_ids`, `change_description`, `upstream_source`
- Section 4: all rows where `verdict = ESCALATE`

```text
escalate_items = [Section 4 rows where verdict = ESCALATE]
```

If Change Set cannot be read or `evolve_status ≠ IN_PROGRESS`:

```text
STATUS: BLOCKED — Change Set not in expected state for Phase P4.
Reason: <evolve_status or read error>
Stop.
```

---

### Step P4.2 — Present Human Decision Package (per ESCALATE item)

For each item in `escalate_items`, in Section 4 order: (EV-FR-045)

```text
═══════════════════════════════════════════════════════════════
HUMAN REVIEW REQUIRED — ESCALATE ITEM
═══════════════════════════════════════════════════════════════
Item            : <element_id> (<element_type>)
Change Trigger  : <change_type> on <affected_element_ids>

[1] PROBLEM
  Element <element_id> requires a governance decision.
  Classification reason:
    MODIFY direct       → content of this element is being changed; human review required
    DEPRECATE (any)     → element or its parent is being deprecated; governance required
    REMOVE cascade      → parent element removed; this dependent element requires a decision

[2] CONTEXT
  Upstream source   : <upstream_source from Section 2>
  Change description: <change_description from Section 2>
  Cascade source    : <cascade_source from Section 4>

[3] CURRENT STATE
  <current_content from Section 4>

[4] PROPOSED CHANGE
  Upstream trigger: <change_type> applied to <affected_element_ids>
  If APPROVED: this element will be updated in Candidate V2 to reflect the upstream change.
  Content generation occurs in Phase P5 — Candidate Assembly.

[5] OPTIONS
  APPROVE — include element in Candidate V2; content will be generated in Phase P5
  DENY    — exclude element from Candidate V2; element absent from Candidate V2

[6] CONSEQUENCES
  APPROVE: element appears in Candidate V2 with updated content aligned to upstream change.
           Specification maintains coherence with the upstream change.
  DENY   : element excluded from Candidate V2. If other items are approved, result is
           PARTIAL_DENY. If all items are denied, result is DENIED (no Candidate V2).

[7] RECOMMENDATION
  No automated recommendation — human judgment required.
═══════════════════════════════════════════════════════════════
```

---

### Step P4.3 — Collect reviewer decision (per item)

For each item in `escalate_items`: (EV-FR-046)

```text
Required inputs from reviewer:
  [1] decision        : APPROVE | DENY     (must be exactly one)
  [2] reviewer_id     : <name or ID>       (non-empty)
  [3] review_rationale: <text explanation> (non-empty)
```

**Validation:**

| Field | Rule |
|---|---|
| `decision` | Must be exactly `APPROVE` or `DENY` |
| `reviewer_id` | Non-empty string |
| `review_rationale` | Non-empty string |

If any field is missing or invalid:

```text
STATUS: BLOCKED — Incomplete review input for <element_id>.
Missing or invalid: <field_name>
Re-present item for correction.
```

Process decisions **item by item**: write each item's update to the Change Set (Step P4.4) immediately after collecting its decision, before proceeding to the next item.

---

### Step P4.4 — Update Change Set Section 4 per item

For each reviewed item: (EV-FR-047, EV-FR-048, EV-FR-049, EV-FR-050, EV-FR-051, EV-FR-052)

**If decision = APPROVE:**

```text
verdict          → Human-APPROVED
proposed_content → "[Approved by <reviewer_id> — content generated in Phase P5]"
reviewer_id      → <reviewer_id>                        (EV-FR-048)
review_timestamp → current timestamp UTC (YYYY-MM-DD HH:MM UTC)  (EV-FR-049)
review_rationale → <review_rationale>                   (EV-FR-050)
deny_reason      → "—"
```

**If decision = DENY:**

```text
verdict          → Human-DENIED
proposed_content → "DENIED — excluded from Candidate V2"
reviewer_id      → <reviewer_id>                        (EV-FR-048)
review_timestamp → current timestamp UTC (YYYY-MM-DD HH:MM UTC)  (EV-FR-049)
review_rationale → <review_rationale>                   (EV-FR-050)
deny_reason      → "Human-DENIED: <review_rationale>"  (EV-FR-052)
```

If write fails:

```text
STATUS: FAILED — Cannot update Change Set Section 4 for <element_id>.
→ evolve_status = FAILED, failed_phase = P4
Stop.
```

---

### Step P4.5 — Compute final aggregate_verdict

After all ESCALATE items have been reviewed: (EV-FR-053)

```text
approved_verdicts = {AUTO_APPLY, Human-APPROVED}
denied_verdicts   = {DENY, Human-DENIED}

approved_count = count(Section 4 rows where verdict ∈ approved_verdicts)
denied_count   = count(Section 4 rows where verdict ∈ denied_verdicts)

If denied_count = 0:
  final_aggregate = "APPROVED"      (all AUTO_APPLY or Human-APPROVED)

Elif approved_count = 0:
  final_aggregate = "DENIED"        (all DENY or Human-DENIED — terminal)

Else:
  final_aggregate = "PARTIAL_DENY"  (≥1 approved + ≥1 denied, per ADR-EVOLVE-005)
```

---

### Step P4.6 — Update Change Set Section 5

Replace Section 5 values with final governance assessment: (EV-FR-054)

```markdown
| aggregate_verdict | <final_aggregate> |
| partial_deny | <true if PARTIAL_DENY else false> |
| human_review_required | true |
| reviewer_id | <comma-separated list of all unique reviewer_ids> |
| review_timestamp | <latest review_timestamp from Section 4 rows reviewed in P4> |
```

If write fails:

```text
STATUS: FAILED — Cannot update Change Set Section 5.
→ evolve_status = FAILED, failed_phase = P4
Stop.
```

---

### Step P4.7 — Update evolve_status

Per EV-FR-023a and EV-FR-055: (EV-FR-055)

```text
If final_aggregate = "APPROVED":
  Update Section 1: evolve_status = APPROVED
  Transition: IN_PROGRESS → [governance complete — all APPROVED/AUTO_APPLY] → APPROVED

If final_aggregate = "PARTIAL_DENY":
  Update Section 1: evolve_status = PARTIAL_DENY
  Transition: IN_PROGRESS → [governance complete — ≥1 DENY + ≥1 APPROVED] → PARTIAL_DENY

If final_aggregate = "DENIED":
  Update Section 1: evolve_status = DENIED
  Transition: IN_PROGRESS → [governance complete — all DENY] → DENIED (terminal)
```

If `final_aggregate = "DENIED"` — terminal report:

```text
STATUS: EVOLVE DENIED (after human governance)
evolve_id        : <evolve_id>
aggregate_verdict: DENIED
All items received verdict DENY or Human-DENIED after human review.
No Candidate V2 will be produced.
Change Set preserved at: WORKSPACE_ROOT/specifications/evolve/<evolve_id>_change_set.md
Specification remains BASELINED. EVOLVE_PENDING is NOT set.
```

Stop. No further phases.

---

### Step P4.8 — Phase P4 Completion Report

```text
PHASE P4 COMPLETE — Human Governance

evolve_id               : <evolve_id>
escalate_items_reviewed : <escalate_count>
  Human-APPROVED        : <human_approved_count>
  Human-DENIED          : <human_denied_count>
combined_approved       : <auto_apply_count + human_approved_count>
combined_denied         : <deny_count + human_denied_count>
final_aggregate_verdict : <APPROVED | PARTIAL_DENY | DENIED>
evolve_status           : <updated value>

→ Phase P5 — Candidate Assembly      [if aggregate ∈ {APPROVED, PARTIAL_DENY}]
→ EVOLVE DENIED — operation complete  [if aggregate = DENIED]
```

---

## Phase P5 — Candidate Assembly

**Objective:** Assemble the Candidate V2 — a complete, autonomous specification produced by targeted reconstruction of impacted sections. Non-impacted sections are copied verbatim from Baseline V1. The Candidate V2 can be read independently of Baseline V1. (ADR-EVOLVE-003, EV-FR-062)

**Precondition:** `evolve_status ∈ {APPROVED, PARTIAL_DENY}` (EV-FR-056)

**Input:**
- Change Set: Section 2 (trigger), Section 3 (impact graph), Section 4 (verdicts)
- Baseline V1 specification at `baseline_v1_path`

**Output:**
- Candidate V2: `WORKSPACE_ROOT/specifications/draft/<base>_specification_candidate_v2.md`
- Change Set Section 6.1 updated with element counts

**Contract references:** EV-FR-056, EV-FR-057, EV-FR-058, EV-FR-059, EV-FR-060, EV-FR-061, EV-FR-062, EV-FR-063, EV-FR-064

---

### ADR-EVOLVE-003 Principle

> EVOLVE reconstructs only impacted sections. Non-impacted sections are preserved verbatim. The result is an autonomous, complete specification — not a delta document.

---

### Step P5.0 — Verify State

Read Change Set Section 1: `evolve_status`. (EV-FR-056)

If `evolve_status ∉ {APPROVED, PARTIAL_DENY}`:

```text
STATUS: BLOCKED — Candidate Assembly requires evolve_status = APPROVED or PARTIAL_DENY.
Current evolve_status: <value>
Stop.
```

---

### Step P5.1 — Read Assembly Inputs

**From Change Set Section 3** (Impact Graph outputs): (EV-FR-057)

```text
impacted_element_ids  = list from Section 3
preserved_section_ids = list from Section 3
```

**From Change Set Section 4** (verdicts per element): (EV-FR-058)

```text
approved_items = [Section 4 rows where verdict ∈ {AUTO_APPLY, Human-APPROVED}]
excluded_items = [Section 4 rows where verdict ∈ {DENY, Human-DENIED}]
excluded_ids   = set(row.element_id for row in excluded_items)
```

**From Change Set Section 2** (trigger):

```text
change_type        = value from Section 2
change_description = value from Section 2
upstream_source    = value from Section 2
affected_element_ids = value from Section 2
```

Read Baseline V1 from `baseline_v1_path`. Build Element Index (fr_index, ac_index, section_element_map — same algorithm as Step P2.2).

---

### Step P5.2 — Build Section Assembly Plan

For each section in Baseline V1:

```text
section_plan = {}

For each section_id in Baseline V1 (in document order):
  elements_in_section = section_element_map.get(section_id, [])
  impacted_in_section = [id for id in elements_in_section if id in set(impacted_element_ids)]

  If section_id in preserved_section_ids OR len(impacted_in_section) = 0:
    section_plan[section_id] = PRESERVE         (EV-FR-059)

  Else:
    section_plan[section_id] = RECONSTRUCT      (EV-FR-060)
    reconstruct_detail[section_id] = {
      "to_update" : [id for id in impacted_in_section if id not in excluded_ids],
      "to_exclude": [id for id in impacted_in_section if id in excluded_ids],
    }
```

For ADD change_type: new elements have no row in Baseline V1. Identify the target section for each ADD element:
```text
add_elements = [id for id in approved_items if id not in Baseline V1 element_index]
For each add_element:
  target_section = section by element_type prefix:
    BR  → Section 5.1
    TR  → Section 5.2
    FR  → Section 6
    AC  → Section 7
    NFR → Section 8
  Mark that section as RECONSTRUCT and include add_element in "to_insert" list.
```

---

### Step P5.3 — Generate Updated Element Content

For each element in `approved_items` where `section_plan[section] = RECONSTRUCT`:

**ADD + AUTO_APPLY — new element:**
```text
Generate new table row:
  element_id    = new ID (next available in sequence for that type)
  description   = derived from change_description in Section 2
  upstream_source = upstream_source from Section 2 (for provenance)
  For FR ADD: BR Source column = triggering BR if specified in change_description
  Format: same column structure as existing rows in that section
```

**MODIFY direct + Human-APPROVED — updated element:**
```text
Take current_content (Section 4 current_content field) as base
Apply change_description: update description to reflect the upstream modification
Preserve all structural columns (ID, cross-references) unless change_description specifies otherwise
Generate updated table row with modified description
```

**MODIFY cascade + AUTO_APPLY — cascade-updated element:**
```text
For FR cascading from modified BR:
  Update FR description to reference modified BR context (from change_description)
  Preserve BR Source column (cross-reference to modified BR unchanged)
For AC cascading from updated FR:
  Update AC description if FR description change warrants it (apply judgment from change_description)
  Preserve FR Couvert column reference
  Preserve Preuve and Démontré en columns verbatim            (ADR-007)
```

**`Preuve` / `Démontré en` / `Mesuré` are carried through every cascade unchanged (ADR-007).** They record what an execution established about the system; an EVOLVE cycle revises the specification, which cannot retroactively change what a past test observed.

**One exception, and it requires a human.** When a cascade changes the *substance* of an AC or NFR — its Given/When/Then, or its Seuil — a prior `DÉMONTRÉ` may no longer refer to the criterion now written. The demonstration proved the old criterion, not the new one. In that case **do not silently preserve and do not silently reset**: surface it in the change set for human decision, as `PROOF_STALE`, naming the element, the prior scope, and what changed. Silently keeping it would assert a demonstration that never happened; silently clearing it would destroy a real test result. Both are information loss.

**Specifications baselined before ADR-007** carry no such columns. Do not rewrite them — post-BASELINE identifiers are frozen. Add the columns at the next EVOLVE cycle, initialised to `NON_DÉMONTRÉ` / `—`, as part of the candidate V2 assembly.

**`Responsable` on OP-NNN is preserved verbatim through every cycle (E4).** It records a human assignment; an EVOLVE cycle revises the specification and has no authority to reassign who owns a gap. Never clear it, never infer one for a newly created OP — a new open point is emitted with `—` and stays that way until somebody takes it. A specification baselined before E4 has no such column: add it at the next cycle, initialised to `—`, like the ADR-007 columns above.

**Nature of this evolution, for the revision history (E7).** `/generate-views` derives whether an evolution is *functional* or *documentary* from the change set this cycle produced. Record the change set so that derivation is possible: the element families touched (`BR`, `TR`, `D`, `FR`, `NFR`), and whether any `Given`/`When`/`Then` cell of an AC or any `Seuil` of an NFR was modified.

Touching any of those makes the evolution **functional** — the specified system changed. Everything else is **documentary**. The distinction matters to a reader deciding whether to re-plan, and is the one thing a version number cannot tell them.

Changes confined to `Preuve`, `Mesuré` or `Démontré en` are not an evolution at all (ADR-007 Engagement #6) and produce no cycle, hence no revision row.

**DEPRECATE + Human-APPROVED — deprecated element:**
```text
Prepend "[DEPRECATED] " to element description
Add deprecation note: "Deprecated per <upstream_source>"
Preserve all other fields (ID, cross-references)
Element remains in table (deprecated, not removed)
```

**REMOVE cascade + Human-APPROVED — orphaned reference update:**
```text
For FR whose BR Source references the removed BR:
  Update BR Source column: "—" (parent BR removed)
  Update FR description to note dependency on removed BR (per change_description)
For AC whose FR Couvert references an updated FR:
  Apply corresponding update if FR change materially affects the AC description
```

---

### Step P5.4 — Assemble Candidate V2 Section by Section

Process Baseline V1 from top to bottom, section by section:

```text
candidate_sections = []

For each section in Baseline V1 (in document order):

  If section_plan[section_id] = PRESERVE:                    (EV-FR-059)
    Append full section content verbatim (heading, prose, tables, all content)
    No modification of any kind.

  If section_plan[section_id] = RECONSTRUCT:                 (EV-FR-060)
    Append section heading and introductory prose (verbatim from Baseline V1)
    Append table header row (verbatim)

    For each existing element row in the section table:
      element_id = row ID column value

      If element_id NOT in impacted_element_ids:
        Append row verbatim              (not impacted — preserve unchanged)

      Elif element_id in excluded_ids:  (EV-FR-061)
        SKIP row                         (excluded from Candidate V2 — DENY or Human-DENIED)

      Else:
        Append updated row from Step P5.3

    After existing rows: insert ADD elements targeted at this section:
      For each add_element in reconstruct_detail[section_id].to_insert:
        Append new row from Step P5.3

candidate_v2_body = join(candidate_sections)
```

**Post-assembly integrity check:**
```text
Verify: every excluded_id is absent from candidate_v2_body
Verify: every ADD element in approved_items appears in candidate_v2_body
Verify: total section count in Candidate V2 = total section count in Baseline V1
```

If any check fails:
```text
STATUS: FAILED — Candidate V2 integrity check failed.
Detail: <failing check description>
→ evolve_status = FAILED, failed_phase = P5
Stop.
```

---

### Step P5.5 — Build Candidate V2 Metadata Header

Prepend YAML front matter (from `templates/candidate_specification_template.md`): (EV-FR-063)

```yaml
---
document_type: CANDIDATE_V2
spec_base: <base>
candidate_version: v2-<YYYYMMDD>
source_baseline: <version from Lifecycle Registry for this workspace+base>
source_baseline_path: <baseline_v1_path>
evolve_id: <evolve_id>
generation_timestamp: <current timestamp UTC — YYYY-MM-DD HH:MM UTC>
assembly_status: CANDIDATE
assembly_summary: >
  <change_type> on <affected_element_ids>.
  Approved: <len(approved_items)> item(s) (AUTO_APPLY + Human-APPROVED).
  Excluded: <len(excluded_items)> item(s) (DENY + Human-DENIED).
  Sections reconstructed: <count of RECONSTRUCT sections>.
  Sections preserved: <count of PRESERVE sections>.
excluded_elements: <comma-separated excluded_ids, or "none">
---
```

---

### Step P5.6 — Write Candidate V2

Create directory `WORKSPACE_ROOT/specifications/draft/` if it does not exist.

Write Candidate V2 (metadata header + assembled body) to: (EV-FR-064)

```text
WORKSPACE_ROOT/specifications/draft/<base>_specification_candidate_v2.md
```

If the write fails:

```text
STATUS: FAILED — Cannot write Candidate V2.
Path  : WORKSPACE_ROOT/specifications/draft/<base>_specification_candidate_v2.md
Error : <reason>
→ evolve_status = FAILED, failed_phase = P5
Stop.
```

---

### Step P5.7 — Update Change Set Section 6.1 (Element Counts)

Count elements by type across V1 baseline and Candidate V2 decisions:

```text
For each element_type in {BR, FR, AC, NFR}:
  count_v1       = count of elements in Baseline V1 Element Index for this type
  v2_added       = count of ADD approved_items for this type
  v2_modified    = count of MODIFY or DEPRECATE approved_items for this type
  deprecated     = count of DEPRECATE approved_items for this type
  total_v2_actif = count_v1 + v2_added
                   − count(REMOVE direct items for this type in excluded_items)
```

Write computed values to Section 6.1 of the Change Set.

Note: Section 6.2 (SQF Delta V1 → V2) remains as placeholder. It is populated by E7 V2 during Phase P7 (`/specification-lifecycle BASELINE`).

---

### Step P5.8 — Phase P5 Completion Report

```text
PHASE P5 COMPLETE — Candidate Assembly

evolve_id              : <evolve_id>
candidate_v2_path      : WORKSPACE_ROOT/specifications/draft/<base>_specification_candidate_v2.md
candidate_version      : v2-<YYYYMMDD>
assembly_status        : CANDIDATE (not yet BASELINED — requires Phase P6 Lifecycle Handoff)

sections_preserved     : <count> [<section IDs>]
sections_reconstructed : <count> [<section IDs>]
elements_approved      : <count> (AUTO_APPLY + Human-APPROVED)
elements_excluded      : <count> (DENY + Human-DENIED) — absent from Candidate V2

→ Phase P6 — Lifecycle Handoff
```

---

## Phase P6 — Lifecycle Handoff

**Objective:** Register the Candidate V2 as an EVOLVE_PENDING operation in the Lifecycle Registry, enabling `/specification-lifecycle BASELINE` to discover and process the Candidate V2 for promotion to Baseline V2. EVOLVE Runtime terminates after this phase — Baseline V2 creation is the exclusive responsibility of the Specification Lifecycle Runtime. (ADR-EVOLVE-004)

**Precondition:** Phase P5 complete. `evolve_status ∈ {APPROVED, PARTIAL_DENY}` and Candidate V2 present at `WORKSPACE_ROOT/specifications/draft/<base>_specification_candidate_v2.md`.

**Input:**
- Change Set: Section 1 (`evolve_id`, `evolve_status`, `spec_base`), Section 5 (`aggregate_verdict`)
- Candidate V2: `WORKSPACE_ROOT/specifications/draft/<base>_specification_candidate_v2.md`
- Lifecycle Registry: `WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md`

**Output:**
- EVOLVE_PENDING event record appended to Lifecycle Registry Event Log (EV-FR-071, EV-FR-072)
- Lifecycle Registry Metadata and Active State Index `Last Event` updated (EV-FR-072)
- Change Set Section 1: `lifecycle_handoff_event_id` field added for cross-reference traceability (EV-FR-073)
- EVOLVE Runtime terminates (ADR-EVOLVE-004)

**EVOLVE Runtime boundary (ADR-EVOLVE-004):**

> After Phase P6, EVOLVE Runtime stops. No further phases execute within `/evolve-specification`. The human operator must invoke `/specification-lifecycle BASELINE` to promote the Candidate V2 to Baseline V2. EVOLVE Runtime does not invoke, trigger, or delegate to the Specification Lifecycle Runtime.

**Contract references:** EV-FR-065, EV-FR-066, EV-FR-067, EV-FR-068, EV-FR-069, EV-FR-070, EV-FR-071, EV-FR-072, EV-FR-073, EV-FR-074

---

### Step P6.0 — Precondition Verification

**EV-FR-068 — DENIED terminal check:**

Read Change Set Section 5: `aggregate_verdict`.

If `aggregate_verdict = DENIED`:

```text
STATUS: EVOLVE DENIED — Lifecycle Handoff not performed.
evolve_id        : <evolve_id>
aggregate_verdict: DENIED

All impacted elements received verdict DENY or Human-DENIED.
No EVOLVE_PENDING registered in Lifecycle Registry.
Specification <base> remains BASELINED at its current version.
Change Set preserved at: WORKSPACE_ROOT/specifications/evolve/<evolve_id>_change_set.md
EVOLVE Runtime terminates. No further action.
```

Stop. Do not proceed.

---

**EV-FR-065 — Candidate V2 present:**

```text
candidate_v2_path = WORKSPACE_ROOT/specifications/draft/<base>_specification_candidate_v2.md
Verify: file exists and is readable.
```

If absent or unreadable:

```text
STATUS: FAILED — P6 Precondition: Candidate V2 not found at expected path.
Path  : WORKSPACE_ROOT/specifications/draft/<base>_specification_candidate_v2.md
Phase P5 must complete before Phase P6 can register EVOLVE_PENDING.
→ Update Change Set: evolve_status = FAILED, failed_phase = P6
Stop.
```

---

**EV-FR-066 — Change Set evolve_status valid:**

Read Change Set Section 1: `evolve_status`.

If `evolve_status ∉ {APPROVED, PARTIAL_DENY}`:

```text
STATUS: FAILED — P6 Precondition: Change Set evolve_status is not APPROVED or PARTIAL_DENY.
Current evolve_status: <value>
Expected: APPROVED or PARTIAL_DENY (set by Phase P3 or Phase P4).
→ Update Change Set: evolve_status = FAILED, failed_phase = P6
Stop.
```

---

**EV-FR-067 — aggregate_verdict valid:**

`aggregate_verdict` was read in the EV-FR-068 check above.

If `aggregate_verdict ∉ {APPROVED, PARTIAL_DENY}`:

```text
STATUS: FAILED — P6 Precondition: aggregate_verdict is not APPROVED or PARTIAL_DENY.
Current aggregate_verdict: <value>
Expected: APPROVED or PARTIAL_DENY (Phase P3 or P4 output).
→ Update Change Set: evolve_status = FAILED, failed_phase = P6
Stop.
```

---

### Step P6.1 — Load Lifecycle Registry

Read Lifecycle Registry at: (EV-FR-071)

```text
WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md
```

If absent:

```text
STATUS: FAILED — P6: Lifecycle Registry not found.
Path: WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md
EVOLVE_PENDING cannot be registered without an active Lifecycle Registry.
→ Update Change Set: evolve_status = FAILED, failed_phase = P6
Stop.
```

Derive `next_event_id`:

```text
Scan the ## Event Log section for all entries matching pattern EV<NNN>.
Extract numeric portion of each match; take the maximum.
next_event_id = "EV" + zero_pad(max + 1, 3 digits)
If no entries exist: next_event_id = "EV001"
```

---

### Step P6.2 — Build EVOLVE_PENDING Event Record

Collect fields for the EVOLVE_PENDING event record: (EV-FR-069, EV-FR-070, EV-FR-071)

```text
event_id          = next_event_id
event_type        = EVOLVE_PENDING
evolve_id         = <evolve_id from Change Set Section 1>
base              = <spec_base from Change Set Section 1>
handoff_date      = current date UTC (YYYY-MM-DD UTC)
evolve_status     = <APPROVED | PARTIAL_DENY>   (from Change Set Section 1)
aggregate_verdict = <APPROVED | PARTIAL_DENY>   (from Change Set Section 5)
candidate_v2_path = specifications/draft/<base>_specification_candidate_v2.md
change_set_path   = specifications/evolve/<evolve_id>_change_set.md
```

**For APPROVED (EV-FR-069):**

```text
All impacted items approved (AUTO_APPLY + Human-APPROVED).
Candidate V2 contains all impacted elements. excluded_elements = "none".
```

**For PARTIAL_DENY (EV-FR-070):**

```text
≥1 item excluded (DENY or Human-DENIED). Candidate V2 is a partial assembly.
excluded_elements: read from Candidate V2 YAML front matter field `excluded_elements`.
```

---

### Step P6.3 — Write EVOLVE_PENDING to Lifecycle Registry

Perform all three writes to the Lifecycle Registry in a single write operation (read-modify-write cycle): (EV-FR-072)

**1. Append to `## Event Log`:**

```markdown
### <event_id> — EVOLVE_PENDING

**Event ID:** <event_id>
**Event Type:** EVOLVE_PENDING
**evolve_id:** <evolve_id>
**Base:** <base>
**Date:** <YYYY-MM-DD UTC>
**evolve_status:** <APPROVED | PARTIAL_DENY>
**aggregate_verdict:** <APPROVED | PARTIAL_DENY>
**Candidate V2 Path:** specifications/draft/<base>_specification_candidate_v2.md
**Change Set Path:** specifications/evolve/<evolve_id>_change_set.md

---
```

**2. Update `## Metadata`:**

```text
Last Updated: <current date UTC>
Total Baselines, Active Baselines, Superseded, Archived: all counts unchanged.
(Spec <base> status remains BASELINED — only a new EVOLVE_PENDING event is appended.)
```

**3. Update `## Active State Index`:**

```text
For the row where Base = <base>:
  Update: Last Event = <current date UTC>
  Unchanged: Spec ID, Status (remains BASELINED), Current Path, Version Sequence.
  Baseline V1 remains the active specification.
```

If registry write fails:

```text
STATUS: FAILED — P6: Cannot write EVOLVE_PENDING to Lifecycle Registry.
Path  : WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md
Error : <reason>
The Candidate V2 exists but has NOT been registered as EVOLVE_PENDING.
→ Update Change Set: evolve_status = FAILED, failed_phase = P6
Stop.
```

---

### Step P6.4 — Update Change Set Section 1 (Cross-Reference)

Add `lifecycle_handoff_event_id` field to the Change Set Section 1 Metadata table: (EV-FR-073)

```markdown
| lifecycle_handoff_event_id | <event_id> |
```

This field creates bidirectional traceability: Change Set → Lifecycle Registry EVOLVE_PENDING event.

If Change Set update fails: WARNING only — the Lifecycle Registry record is authoritative.

```text
WARNING: Could not update Change Set Section 1 with lifecycle_handoff_event_id.
Change Set  : WORKSPACE_ROOT/specifications/evolve/<evolve_id>_change_set.md
Registry    : Lifecycle event <event_id> is authoritative for the EVOLVE_PENDING record.
Continue.
```

---

### Step P6.5 — Phase P6 Completion Report (EV-FR-074)

```text
PHASE P6 COMPLETE — Lifecycle Handoff

evolve_id           : <evolve_id>
spec_base           : <base>
aggregate_verdict   : <APPROVED | PARTIAL_DENY>
evolve_status       : <APPROVED | PARTIAL_DENY>

EVOLVE_PENDING registered in Lifecycle Registry:
  Event ID          : <event_id>
  Registry          : WORKSPACE_ROOT/specifications/lifecycle/specifications_lifecycle.md
  Candidate V2      : WORKSPACE_ROOT/specifications/draft/<base>_specification_candidate_v2.md
  Change Set        : WORKSPACE_ROOT/specifications/evolve/<evolve_id>_change_set.md

═══════════════════════════════════════════════════════════════════
EVOLVE RUNTIME COMPLETE — Phases P0–P6
═══════════════════════════════════════════════════════════════════

EVOLVE Runtime has completed all authorized phases.
Baseline V1 for <base> remains active at its current version.

Required next action (human operator):
  /specification-lifecycle BASELINE
  The Specification Lifecycle Runtime will detect EVOLVE_PENDING via event <event_id>
  and apply E6 V2 + E7 V2 quality gates before promoting Candidate V2 to Baseline V2.
  [E6 V2 / E7 V2 integration defined in Phase P7 — WP-EVOLVE-1G]

EVOLVE Runtime will NOT execute further actions.
Baseline V2 creation is the exclusive responsibility of /specification-lifecycle BASELINE.
(ADR-EVOLVE-004)
═══════════════════════════════════════════════════════════════════
```

---

## Phase P7 — E6/E7 Integration

**Objective:** Define the integration contract between EVOLVE Runtime and the Specification Lifecycle Runtime for Baseline V2 creation. Phase P7 is passive from EVOLVE Runtime's perspective: after Phase P6 completes (EVOLVE_PENDING registered), the human operator invokes `/specification-lifecycle BASELINE`. The Lifecycle Runtime drives E6 V2 and E7 V2 validation, Baseline V2 creation, and Change Set completion.

**Implementation:** The E6 V2 and E7 V2 algorithms are implemented in `docs/commands/specification-lifecycle_execution.md` — BASELINE V2 — EVOLVE_PENDING Mode section. Phase P7 documents the integration contract from the EVOLVE Runtime's perspective.

---

### EVOLVE Runtime state after Phase P6

After Phase P6 completes successfully (EV-FR-074):

- Change Set: `evolve_status ∈ {APPROVED, PARTIAL_DENY}` (transitional)
- Lifecycle Registry: EVOLVE_PENDING event registered (`event_type = EVOLVE_PENDING`)
- Candidate V2: `WORKSPACE_ROOT/specifications/draft/<base>_specification_candidate_v2.md`

The EVOLVE Runtime will NOT execute further actions.
Baseline V2 creation is the exclusive responsibility of `/specification-lifecycle BASELINE`. (ADR-EVOLVE-004)

---

### E6 V2 — Impact-Aware Inference Validation contract (EV-FR-078 to EV-FR-083)

Applied by Lifecycle Runtime on Candidate V2:

```text
Invariant: Baseline V1 passed E6 → zero INFERRED_DESIGN structural PENDING_VALIDATION entries.
Preserved sections in Candidate V2 are verbatim copies from Baseline V1 (ADR-EVOLVE-003).
Therefore: any PENDING_VALIDATION found in Candidate V2 = from reconstructed (impacted) sections.
Impact-aware property is satisfied by this invariant — no element-level correlation required.

E6 V2 result:
  PASS  — zero INFERRED_DESIGN structural PENDING_VALIDATION in Candidate V2 (EV-FR-081)
  BLOCK — ≥1 INFERRED_DESIGN structural PENDING_VALIDATION found (EV-FR-082)
```

E6 V2 BLOCK: BASELINE V2 refused. EVOLVE_PENDING remains active. Candidate V2 must be corrected before retry.

---

### E7 V2 — Candidate Validation Review contract (EV-FR-084 to EV-FR-090)

Applied by Lifecycle Runtime on Candidate V2, after E6 V2 PASS:

```text
Check 1: Required YAML front matter fields present and non-empty (EV-FR-086)
Check 2: excluded_elements absent from Candidate V2 body (EV-FR-087)
Check 3: Candidate V2 body non-empty below YAML closing "---" (EV-FR-088)

E7 V2 result:
  PASS  — all checks pass (EV-FR-089)
  BLOCK — any check fails (EV-FR-090)
```

SQF re-computation (EV-FR-102): out of scope for this release. Change Set Section 6.2 remains as placeholder.

E7 V2 BLOCK: BASELINE V2 refused. EVOLVE_PENDING remains active.

---

### BASELINE V2 Creation contract (EV-FR-091 to EV-FR-099)

If E6 V2 PASS and E7 V2 PASS, after human confirmation (EV-FR-091):

1. Baseline V1 versioned as SUPERSEDED: `specifications/stable/<base>_specification_v<n>.md` (EV-FR-097)
2. Candidate V2 promoted to Baseline V2: `specifications/stable/<base>_specification.md` (EV-FR-098)
3. Candidate V2 deleted from `specifications/draft/` (EV-FR-096)
4. Change Set `evolve_status → COMPLETE` (terminal — EV-FR-094) — ADR-EVOLVE-004
5. Lifecycle Registry: BASELINE V2 event appended with `evolve_id` and `EVOLVE_PENDING Resolved` fields (EV-FR-099)
6. Active State Index updated: `version_sequence + 1`, `status = BASELINED`, `Last Event = today` (EV-FR-093)

---

### CANCELLED contract (EV-FR-085, EV-FR-100, EV-FR-101)

If human operator responds `cancel` at Phase 4 V2 confirmation prompt:

1. Change Set `evolve_status → CANCELLED` (terminal — EV-FR-100)
2. EVOLVE_CANCELLED event appended to Lifecycle Registry Event Log (EV-FR-101)
3. No Baseline V2 created; Candidate V2 preserved
4. Specification `<base>` remains BASELINED at Baseline V1

---

**Contract references:** EV-FR-075, EV-FR-076, EV-FR-077, EV-FR-078, EV-FR-079, EV-FR-080, EV-FR-081, EV-FR-082, EV-FR-083, EV-FR-084, EV-FR-085, EV-FR-086, EV-FR-087, EV-FR-088, EV-FR-089, EV-FR-090, EV-FR-091, EV-FR-092, EV-FR-093, EV-FR-094, EV-FR-095, EV-FR-096, EV-FR-097, EV-FR-098, EV-FR-099, EV-FR-100, EV-FR-101, EV-FR-102, EV-FR-103

---

## Failure Handling Summary

| Phase | Condition | Action |
|---|---|---|
| P0 | Workspace resolution fails (W1–W5) | BLOCKED — no Change Set created |
| P0 | No BASELINED specification for `<base>` | BLOCKED — no Change Set created |
| P0 | EVOLVE_PENDING already active | BLOCKED — no Change Set created |
| P1 | Trigger input missing or invalid | BLOCKED — no Change Set created |
| P1 | Directory creation fails | BLOCKED — no Change Set created |
| P1 | Filesystem write fails | FAILED — `evolve_status = FAILED`, `failed_phase = P1` if partial write |
| P2 | Baseline V1 unreadable | FAILED — `evolve_status = FAILED`, `failed_phase = P2` |
| P2 | Change Set Section 3 write fails | FAILED — `evolve_status = FAILED`, `failed_phase = P2` |
| P3 | Baseline V1 unreadable at P3 | FAILED — `evolve_status = FAILED`, `failed_phase = P3` |
| P3 | Section 4 write fails | FAILED — `evolve_status = FAILED`, `failed_phase = P3` |
| P3 | Section 5 write fails | FAILED — `evolve_status = FAILED`, `failed_phase = P3` |
| P3 | All items DENY | DENIED (terminal) — `evolve_status = DENIED`, no Candidate V2 produced |
| P4 | Section 4 write fails for reviewed item | FAILED — `evolve_status = FAILED`, `failed_phase = P4` |
| P4 | Section 5 write fails after all reviews | FAILED — `evolve_status = FAILED`, `failed_phase = P4` |
| P4 | All items DENY or Human-DENIED | DENIED (terminal) — `evolve_status = DENIED`, no Candidate V2 |
| P5 | evolve_status not APPROVED or PARTIAL_DENY | BLOCKED — assembly cannot proceed |
| P5 | Candidate V2 write fails | FAILED — `evolve_status = FAILED`, `failed_phase = P5` |
| P5 | Integrity check fails after assembly | FAILED — `evolve_status = FAILED`, `failed_phase = P5` |
| P6 | aggregate_verdict = DENIED at P6.0 | Terminal — EVOLVE DENIED; no EVOLVE_PENDING; Change Set unmodified (already DENIED) |
| P6 | Candidate V2 absent at expected path | FAILED — `evolve_status = FAILED`, `failed_phase = P6` |
| P6 | evolve_status ∉ {APPROVED, PARTIAL_DENY} | FAILED — `evolve_status = FAILED`, `failed_phase = P6` |
| P6 | aggregate_verdict ∉ {APPROVED, PARTIAL_DENY} | FAILED — `evolve_status = FAILED`, `failed_phase = P6` |
| P6 | Lifecycle Registry absent | FAILED — `evolve_status = FAILED`, `failed_phase = P6` |
| P6 | Lifecycle Registry write fails (Step P6.3) | FAILED — `evolve_status = FAILED`, `failed_phase = P6` |
| P6 | Change Set Section 1 update fails (Step P6.4) | WARNING only — Lifecycle Registry is authoritative; continue |
| P7 | E6 V2 BLOCK — INFERRED_DESIGN structural PENDING_VALIDATION in Candidate V2 | BLOCKED — BASELINE V2 refused; Lifecycle Runtime reports; EVOLVE_PENDING remains active |
| P7 | E7 V2 BLOCK — Candidate V2 coherence failure | BLOCKED — BASELINE V2 refused; Lifecycle Runtime reports; EVOLVE_PENDING remains active |
| P7 | Phase 4 V2 "no" — human aborts | BLOCKED — EVOLVE_PENDING remains active; operator can retry later |
| P7 | Phase 4 V2 "cancel" — human cancels EVOLVE | CANCELLED (terminal) — Change Set updated; EVOLVE_CANCELLED event written |
| P7 | BA1v2 — write SUPERSEDED Baseline V1 fails | BLOCKED — Lifecycle Runtime reports; no further changes |
| P7 | BA3v2 — write Baseline V2 fails | BLOCKED — Baseline V1 versioned; manual recovery required |
| P7 | Registry write fails after Phase 5 V2 | CRITICAL — Lifecycle Runtime reports; Baseline V2 file OK; registry NOT updated |

For all FAILED states after Change Set creation: update Change Set `evolve_status = FAILED` and `failed_phase = P<N>` in Section 1 Metadata before stopping. (EV-FR-013)
