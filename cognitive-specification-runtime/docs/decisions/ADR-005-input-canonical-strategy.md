# ADR-005 — Input Canonical Strategy

## Title

Input Canonical Strategy

---

## Status

ACCEPTED

---

## Context

The current CSR documentation listed supported input formats as illustrative examples without a formal taxonomy. Prior to WP-INPUT, this produced four documented ambiguities:

1. **Silent misclassification.** PPTX and XLSX were listed as "supported" but lacked preprocessing profiles. Sources using these formats entered the pipeline with undefined behavior.

2. **Absence of structured-data eligibility criteria.** No mechanism existed to distinguish a data dictionary (eligible) from a CRM export (ineligible) when both are CSV files. The format is identical; the relevance to the CSR mission is opposite.

3. **No ingestion traceability.** Acceptance, warning, and rejection decisions were not recorded. A source rejected informally left no trace in the workspace registry.

4. **No partial scope mechanism.** Mixed sources (XLSX workbooks with normative sheets alongside operational sheets) required manual extraction before ingestion — an untraceable, non-reproducible operation.

The WP-INPUT work package (WP-INPUT-1, WP-INPUT-1A, WP-INPUT-2A, WP-INPUT-2, WP-INPUT-CLOSEOUT) resolved these ambiguities and produced a complete input strategy. ADR-005 formalises that strategy as a CSR architectural decision.

---

## Evidence

**WP-INPUT-1 — Source Ingestion Audit (INPUT_SYSTEM_PARTIAL)**
PPTX and XLSX appeared in CSR documentation as supported formats. No preprocessing profile existed for either. The actual processing path was undefined.

**WP-INPUT-1A — Conversion Capability Assessment (CONVERSION_STRATEGY_PARTIAL)**
Office 365 v16.0 is installed and operational (Word COM, PowerPoint COM, Excel COM). DOCX, DOC, RTF, PPTX, PPT can be converted to PDF with HIGH reliability at no additional installation cost. VSDX conversion is impossible (Visio not installed). ODT/ODP fidelity via Office COM is insufficient for complex documents.

**WP-INPUT-2A — Structured Source Eligibility Audit (ELIGIBILITY_MODEL_ACCEPT_WITH_CHANGES)**
Content nature — not format — is the correct eligibility discriminant. A DDL SQL schema and a CRM export SQL dump are structurally the same format and opposites in CSR relevance. Volume alone is not determinant: a 10,000-line DDL schema is eligible; a 50-row operational export may not be.

**WP-INPUT-2 — Input Canonical Strategy (STRATEGY_ACCEPT)**
Taxonomy A/B/C/D defined, Eligibility Model (Phase 0) designed, Partial Scope mechanism specified, Rejection Traceability model produced. Verdict: STRATEGY_ACCEPT.

**WP-INPUT-CLOSEOUT — Decision Register (WP_INPUT_CLOSED_WITH_ACTIONS)**
16 decisions confirmed (D-INP-001 through D-INP-016). 6 hypotheses rejected (R-INP-001 through R-INP-006). ADR-005 creation declared as D-INP-014 (CONFIRMED — pending PO validation).

---

## Decision

CSR adopts the **Input Canonical Strategy** comprising five integrated components:

1. A **five-category Input Taxonomy** (A / A+ / B / C / D) classifying all source formats by processing path.
2. A **Category A+ path** for DOCX using Pandoc → Markdown conversion (preferred over Office COM PDF conversion — see AMBIGUITY-INP-001, AMBIGUITY-INP-002).
3. A **Category B Conversion Layer** using Office COM automation for DOC, RTF, PPTX, PPT documentary formats.
4. A **Category C Eligibility Model** (Phase 0) qualifying structured sources by content nature before preprocessing.
5. A **Rejection Traceability Model** recording all eligibility decisions in the workspace registry.

**Amendment history:**
- v1 (2026-07-04): Initial ACCEPTED — 4 categories (A/B/C/D); DOCX in Category B.
- v1.1 (2026-07-05): WP-INPUT-RT-2 amendment — DOCX promoted to Category A+ (Pandoc path); Category B restricted to DOC/RTF/PPTX/PPT. Evidence: AMBIGUITY-INP-001 (HYBRID_MODEL_RECOMMENDED: 0 Pandoc defects vs 4 COM defects) and AMBIGUITY-INP-002 (KEEP_PANDOC: windows-1252 encoding defect in COM→HTML path, C3 requires custom XML parser). PO decision: DOCX → Pandoc → Markdown.

---

## Input Taxonomy

### Category A — Canonical Formats

Processed natively by the CSR pipeline without transformation. No eligibility check required — these formats are normative by nature in the CSR context.

| Format | Preprocessing Profile | Status |
|--------|-----------------------|--------|
| PDF (.pdf) | PDF Profile — text + multimodal visual | OPERATIONAL |
| Markdown (.md) | Pass-through | OPERATIONAL |
| Text (.txt) | Pass-through | OPERATIONAL |
| Images (.png, .jpg, .jpeg, .gif, .webp) | Image Profile — multimodal | OPERATIONAL |

**Processing rule:** Ingestion → Preprocessing → Extraction. Direct path, no qualification gate.

**Limitation:** Images whose content is purely operational (CRM screenshots, inventory photos) remain in this category but will produce low-value extraction. The user is responsible for supplying images with normative content.

---

### Category A+ — DOCX (Pandoc Path)

DOCX files are processed via Pandoc → Markdown conversion, not via Office COM → PDF. This classification was determined by empirical study (AMBIGUITY-INP-001, AMBIGUITY-INP-002) and confirmed by PO decision on 2026-07-05.

| Format | Conversion Method | Reliability | Prerequisite |
|--------|-------------------|-------------|--------------|
| DOCX (.docx) | Pandoc → Markdown + embedded image extraction | HIGH | Pandoc 3.x (winget install pandoc) |

**Processing rule:** Ingestion → Pandoc conversion → Markdown + [SCHEMA:]/[FLOW:]/[VISUAL:] block extraction → Extraction.

**Why not Office COM for DOCX:**
- Word COM → PDF path produces 4 structural defects (list collapse CRITICAL, identifier split HIGH, UUID corruption HIGH, URL breakage HIGH).
- Word COM → HTML path adds windows-1252 encoding defect (French text corrupted) and violates Markdown-first principle.
- Pandoc produces 0 defects on the same corpus and satisfies all 5 CSR alignment criteria.
- "Minimize external dependencies" constraint: Pandoc (`winget install pandoc`, ~10s) costs less than any COM alternative that requires custom post-processing.

**Environment prerequisite:** Pandoc 3.x. Install: `winget install pandoc` (Windows) or `pandoc.org` (all platforms).

---

### Category B — Convertible Formats

Documentary formats (excluding DOCX — see Category A+) requiring automatic conversion to PDF before standard PDF preprocessing. No eligibility check required — documentary and presentation formats are normative by nature.

| Format | Conversion Method | Reliability | Prerequisite |
|--------|-------------------|-------------|--------------|
| DOC (.doc) | Word COM → PDF | HIGH | Office 365 v16.0 |
| RTF (.rtf) | Word COM → PDF | HIGH | Office 365 v16.0 |
| PPTX (.pptx) | PowerPoint COM → PDF | HIGH | Office 365 v16.0 |
| PPT (.ppt) | PowerPoint COM → PDF | HIGH | Office 365 v16.0 |

**Processing rule:** Ingestion → Office COM automatic conversion → PDF → PDF Preprocessing → Extraction.

**Environment prerequisite:** Office 365 v16.0 installed locally. This is a declared CSR environment constraint. If absent: explicit rejection with manual conversion alternative suggested. Category B formats do not degrade silently.

**Note on ODT/ODP:** Classified as Category D. Office COM fidelity for ODT/ODP is insufficient for complex documents. LibreOffice is not installed in the current environment.

---

### Category C — Structured Formats

Formats whose eligibility depends on content nature. An **Eligibility Check (Phase 0)** is mandatory before any preprocessing.

| Format | ADR-002 Profile | Profile Status | Fallback |
|--------|-----------------|----------------|----------|
| XLSX (.xlsx) | XLSX Profile | DESIGNED — not implemented | Excel COM → PDF (degraded) |
| CSV (.csv) | CSV Profile | DESIGNED — not implemented | Plain text (structure lost) |
| JSON (.json) | JSON/YAML Profile | DESIGNED — not implemented | Plain text (structure lost) |
| YAML (.yaml, .yml) | JSON/YAML Profile | DESIGNED — not implemented | Plain text (structure lost) |
| XML (.xml) | XML Profile | DESIGNED — not implemented | Plain text (structure lost) |
| SQL (.sql) | SQL Profile | DESIGNED — not implemented | Plain text (acceptable for DDL) |

**Processing rule:** Ingestion → Phase 0 Eligibility Check → if ACCEPT or ACCEPT\_WITH\_WARNING: native profile preprocessing → Extraction. If REJECT: traced stop.

**XLSX positioning (D-INP-015):** XLSX belongs to Category C, not Category B. Converting XLSX to PDF via Excel COM loses formulas and inter-sheet relationships — information that is normative in data dictionaries and rule registers. The native XLSX Profile (ADR-002) preserves this structure. Excel COM conversion is a temporary fallback only, annotated `preprocessing_mode: FALLBACK_PDF` (D-INP-016).

---

### Category D — Unsupported Formats

Formats without a viable processing path in the current environment. Immediate rejection with explicit message and alternative suggested.

| Format | Reason | Recommended Alternative |
|--------|--------|------------------------|
| VSDX | Visio not installed | Export to PDF from Visio, or to PNG/SVG image |
| ODT | Word COM fidelity insufficient | Export to PDF from LibreOffice or Word |
| ODP | PowerPoint COM fidelity insufficient | Export to PDF from LibreOffice or PowerPoint |
| HTML | No supported path | Export page to PDF via browser |
| URL | Not supported | Export page to PDF via browser |
| ZIP | Not supported | Extract files individually and ingest each |
| Audio | Not supported | Provide transcript as TXT or MD |
| Video | Not supported | Provide transcript or slide deck |

**Processing rule:** Immediate rejection with explicit message. Rejection recorded in `sources.md` with `eligibility_status: UNSUPPORTED`.

---

## Conversion Principles (Category B)

**Transparent conversion.** The conversion from Office format to PDF is automatic and transparent to the user. No user action is required beyond providing the original file.

**Mandatory prerequisites.** Office 365 v16.0 must be installed locally. This prerequisite is a declared CSR environment constraint, not an optional convenience. It must appear in CSR environment documentation.

**No support illusion.** Category B formats are not natively supported — they are supported through a conversion dependency. Without Office 365, Category B formats degrade to Category D until an alternative conversion path is available (see RISK-INP-001).

**Explicit failure if conversion impossible.** If conversion fails (protected file, macro blocked, Office not installed), the failure is explicit and traceable. No silent fallback to plain text.

---

## Eligibility Model (Category C)

### Foundational principle

> Eligibility decisions are based on content nature, not format.

CSR transforms normative knowledge into maintained specifications. Only content that prescribes rules, constraints, structures, or behaviors contributes to this mission. Content describing past events, operational states, or measurement data falls outside CSR scope — regardless of format.

---

### ACCEPT — Knowledge-Oriented (KO)

The source primarily encodes rules, definitions, constraints, structures, or behaviors to be specified.

**Determining signals:**
- Normative text fields: `Description`, `Rule`, `Definition`, `Purpose`, `Condition`, `Action`
- Encoded constraints: conditional formulas, `CHECK CONSTRAINT`, `required`, `enum`, `pattern`, `minLength`
- Normative metadata: `data_type`, `is_required`, `valid_states`, `foreign_key`
- Referential identifiers: `code`, `type`, `category`, `status_list`
- DDL-type SQL statements: `CREATE TABLE`, `ALTER TABLE`, `CREATE VIEW`, `FOREIGN KEY`, `CHECK`

**Processing behavior:** ACCEPT without condition. Standard preprocessing via the corresponding ADR-002 profile.

**Paradigmatic examples:**

| Source | KO Signals |
|--------|-----------|
| Data dictionary XLSX | Columns `Column Name`, `Data Type`, `Description`, `Validation Rule` |
| DDL SQL schema | `CREATE TABLE`, `CHECK CONSTRAINT`, `FOREIGN KEY` |
| API catalog JSON | `"required"`, `"enum"`, `"pattern"`, `"minLength"` |
| Dataverse schema export | Tables, columns, Business Rules, Choice columns |
| Business rules register XLSX | `Rule ID`, `Condition`, `Action`, `Priority` |
| Role matrix CSV | `Role`, `Permission`, `Scope`, `Restriction` |
| Power Automate flow JSON | `trigger`, `actions`, `conditions`, `connectors` |
| Business configuration YAML | Thresholds, delays, codes, validation parameters |

---

### REJECT — Operational Data (OD)

The source primarily encodes past instances, events, measurements, or operational states.

**Determining signals:**
- Columns dominated by dates, amounts, quantities, instance identifiers
- Row homogeneity (all structurally identical — signature of a transactional table)
- Volume > 5,000 rows with transactional headers
- Filename suggesting history or export: `export_`, `orders_`, `sales_`, `log_`, `history_`, `backup_`, date suffix
- Dominant DML-type SQL: `INSERT INTO`, `UPDATE`, `DELETE` without associated DDL
- Total absence of descriptive or normative fields

**Processing behavior:** REJECT with justified message. No preprocessing. Eligibility decision recorded in `sources.md` and `events.md`. Alternative suggested if applicable.

**Paradigmatic examples:**

| Source | OD Signals |
|--------|-----------|
| CRM export CSV | `contact_id, name, email, created_at, last_modified` × N rows |
| Order history XLSX | `order_id, customer, amount, date, status` × N rows |
| System logs JSON | `timestamp, level, service, message, trace_id` × N rows |
| Analytics export | Calculated metrics, KPIs, historical trends |
| Test data CSV | Fictional instances for unit or load tests |

---

### ACCEPT\_WITH\_WARNING — Mixed Sources (MS)

The source contains both KO and OD elements, or its signals are ambiguous and cannot support certain classification without finer analysis or explicit human input.

**Determining signals:**
- Known mixed source (backlog, product catalog, application configuration)
- Multi-sheet XLSX with heterogeneous sheets (some normative, others operational)
- SQL containing DDL and non-negligible INSERT (reference data or migration data)
- Intermediate volume (500–5,000 rows) with ambiguous headers
- Insufficient context provided by user

**Processing behavior:** ACCEPT\_WITH\_WARNING with human confirmation request and/or invitation to define a partial scope. If user confirms without scope restriction: preprocessing of the full source with annotation `[CAVEAT: mixed source — validate extracted elements before consolidation]`. If user defines a scope: preprocessing of the defined scope only.

**Paradigmatic examples:**

| Source | Ambiguity |
|--------|-----------|
| Backlog XLSX with acceptance criteria | `Description`, `AC` columns eligible / `Sprint`, `Assignee`, `Story Points` not |
| Product catalog | Category hierarchy + pricing rules eligible / product instances not |
| SQL: DDL + reference data inserts | `CREATE TABLE` + 200 `INSERT INTO countries VALUES` — DDL and reference INSERTs are KO |
| Mixed infrastructure/business YAML | Business parameters (`approval_threshold: 5000`) eligible / infra config (`host: 192.168.1.5`) not |

---

### Signal evaluation hierarchy

```
Level 1 — Contextual signals (determinant if clear)
    Filename / declared source / requester context
    → Strong OD signal → REJECT immediate (without content analysis)
    → Strong KO signal → ACCEPT immediate (without content analysis)
    → Ambiguous → Level 2

Level 2 — Structural signals (discriminating)
    Statement types (DDL vs DML), JSON schema structure, CSV headers
    → KO dominant → ACCEPT
    → OD dominant → REJECT
    → Mix or uncertain → ACCEPT_WITH_WARNING

Level 3 — Volume signals (confirmatory, not determinant alone)
    → High volume + OD headers: reinforces REJECT
    → Moderate volume + KO headers: confirms ACCEPT
    → High volume + KO headers: confirms ACCEPT (volume alone does not reject)
```

---

## Eligibility Check — Phase 0

### Position in the pipeline

Phase 0 is inserted before Phase 1 (Workspace Resolution) of `/preprocess-source`, exclusively for Category C sources.

```
/ingest-source                       (M1 — unchanged)
        │
        ▼
    sources.md entry                 (eligibility_status = PENDING)
        │
        ▼  Category C only
Phase 0 — Eligibility Check         (NEW — triggered by /preprocess-source)
        │
        ├──→ ACCEPT                  → standard preprocessing via ADR-002 profile
        ├──→ ACCEPT_WITH_WARNING     → preprocessing with CAVEAT annotation
        │                              (after human confirmation + optional scope)
        └──→ REJECT                  → stop + ELIGIBILITY_REJECTED event + sources.md
                │
                ▼
        /preprocess-source Phase 1+  (unchanged for sources passing eligibility)
```

Phase 0 applies exclusively to Category C. Categories A and B: implicit eligibility, no gate. Category D: immediate rejection without Phase 0.

### Responsibilities

**Inputs:**
- Source file (extension, name, partial content for analysis)
- User context provided at ingestion (optional)
- sources.md registry (source history)

**Outputs:**
- Decision: ACCEPT / ACCEPT\_WITH\_WARNING / REJECT
- Documented reason (list of triggering signals)
- If ACCEPT\_WITH\_WARNING: confirmation questions and scope options
- sources.md update: `eligibility_status`, `eligibility_reason`, `eligibility_date`
- events.md event: `ELIGIBILITY_DECISION`

### Mandatory character

Phase 0 is mandatory for all Category C sources. It cannot be bypassed without an explicit traceable record. If the user wishes to override a REJECT decision, this is done via OVERRIDE mode, which generates a traceable `ELIGIBILITY_OVERRIDE` event with mandatory written justification.

A silent bypass or untraceable override compromises traceability — a foundational CSR principle. A traced override is acceptable. An invisible bypass is not (D-INP-012, R-INP-006 rejected).

---

## Partial Scope

### Principle

Mixed or complex structured sources frequently contain normative content alongside operational data. Requiring the user to manually extract the normative portion before ingestion creates untraceable, non-reproducible effort. The partial scope mechanism allows the user — during Phase 0 — to restrict preprocessing to a designated subset of the source.

### Scope by format

**XLSX — Scope by named sheets**
```
scope=Rules,Config
→ Processes only sheets "Rules" and "Config"
→ Ignores sheets "Customers", "Orders"
```

**SQL — Scope by statement type**
```
scope=DDL-ONLY
→ Extracts CREATE TABLE, ALTER TABLE, FOREIGN KEY, CHECK, CREATE VIEW
→ Ignores INSERT INTO, UPDATE, DELETE
```

**JSON / YAML — Scope by top-level key**
```
scope=business_rules,validation_schemas
→ Extracts sections "business_rules" and "validation_schemas"
→ Ignores sections "infrastructure", "logging"
```

**XML — Scope by element type or namespace**
```
scope=BusinessRules,Entities
→ Extracts <BusinessRule> and <Entity> elements
→ Ignores other element types not listed
```

**CSV:** No partial scope applicable — scope is a file-level decision for CSV.

### Default behavior without scope

- ACCEPT: full file processing
- ACCEPT\_WITH\_WARNING: scope request to user before processing
- REJECT: refusal with scope proposal if applicable

### Scope traceability

The selected scope is recorded:
- In `sources.md`: new `scope` field (e.g., `Rules,Config` or `DDL-ONLY` or `ALL`)
- In `source_fingerprint`: fingerprint calculated over the processed scope, not the full file
- In `events.md`: `ELIGIBILITY_DECISION` event includes the decided scope

If the user changes scope on reprocessing, the fingerprint changes → staleness detected → overwrite proposed. This is the correct and expected behavior.

---

## Rejection Traceability

### Principle

Every eligibility decision — ACCEPT, ACCEPT\_WITH\_WARNING, or REJECT — is a CSR governance decision. It must be traced, justified, and preserved. This principle extends the `traceable decisions` core principle (CLAUDE.md) and is consistent with the KPM-001 provenance model: a source declared INELIGIBLE cannot produce SOURCE\_FACTs.

### sources.md extension

New fields added to the source registry for all Category C and Category D sources:

| Field | Type | Description |
|-------|------|-------------|
| `eligibility_status` | enum | `PENDING` / `ELIGIBLE` / `ELIGIBLE_WITH_WARNING` / `INELIGIBLE` / `UNSUPPORTED` / `OVERRIDE` |
| `eligibility_reason` | text | Decision justification (triggering signals) |
| `eligibility_date` | datetime | Decision timestamp |
| `eligibility_human_confirmed` | bool | `true` if user confirmed ACCEPT\_WITH\_WARNING or OVERRIDE |
| `scope` | text | Applied partial scope (e.g. `Rules,Config`, `DDL-ONLY`, or `ALL`) |

**`eligibility_status` vocabulary:**

| Value | Meaning |
|-------|---------|
| `PENDING` | Source ingested, Phase 0 not yet performed |
| `ELIGIBLE` | ACCEPT — source accepted without condition |
| `ELIGIBLE_WITH_WARNING` | ACCEPT\_WITH\_WARNING — accepted with reservation or scope restriction |
| `INELIGIBLE` | REJECT — operational data or ineligible content |
| `UNSUPPORTED` | Category D — format not supported in current environment |
| `OVERRIDE` | Rejected source processed on explicit user request with mandatory justification |

### events.md extension

New event type: `ELIGIBILITY_DECISION`

```markdown
## ELIGIBILITY_DECISION — <source_name> — <datetime>

- event_type: ELIGIBILITY_DECISION
- source: <source_filename>
- format_category: C
- decision: ACCEPT | ACCEPT_WITH_WARNING | REJECT | OVERRIDE
- signals:
  - <signal 1>
  - <signal 2>
- reason: <synthetic justification>
- scope: <applied scope or ALL>
- human_confirmed: true | false
- override_justification: <text if OVERRIDE, empty otherwise>
```

### Historical preservation

Eligibility decisions are never overwritten without trace. If a source is requalified (e.g., initially INELIGIBLE, then processed with a defined scope → ELIGIBLE\_WITH\_WARNING), both decisions are preserved in events.md with timestamps. The latest decision is reflected in sources.md. This satisfies the `traceable decisions` and `repository-first` core principles.

---

## Relations with Existing ADRs

### ADR-002 — Source Type Aware Extraction

**Relation: EXTENDS — amendment required**

ADR-005 introduces Phase 0 (Eligibility Check) as a prerequisite to the preprocessing profiles defined in ADR-002. ADR-002 defines the normalization stage; ADR-005 defines the qualification stage that precedes it for Category C. ADR-002 must be amended to:
- Declare Phase 0 as a pre-condition to Category C profiles
- Add an Eligibility Signals section to each Category C profile
- Add a Partial Scope section to each Category C profile
- Define the `source_fingerprint` format for structured sources including scope

See ADR-002\_AMENDMENT\_LIST for the complete amendment specification.

---

### ADR-004 — Inference Governance Policy / KPM-001

**Relation: COMPATIBLE — alignment note only**

The eligibility model is consistent with the KPM-001 provenance model. A source declared INELIGIBLE (`eligibility_status: INELIGIBLE`) cannot produce `SOURCE_FACT` (KPM-001 SF) entries in the knowledge base. This is a logical consequence of KPM-001, not an amendment to it.

An OVERRIDE decision (source rejected but processed) must be clearly annotated in the knowledge artifacts it produces, so that the non-standard eligibility status is visible to the provenance chain.

---

### ADR-001 — CSR Language Policy

**Relation: NO IMPACT**

The input strategy does not modify the output language policy. Multi-language source handling is a future work package (WP-MULTILANG-1) independent of this ADR.

---

### ADR-003 — Audience Model + HTML Pipeline

**Relation: NO IMPACT**

Output format and view generation are not affected by the input strategy.

---

## Environment Prerequisites

| Prerequisite | Required for | Current status |
|-------------|--------------|----------------|
| Pandoc 3.x | Category A+ — DOCX | REQUIRED (install: winget install pandoc) |
| Office 365 v16.0 (Word COM) | Category B — DOC, RTF | AVAILABLE (confirmed WP-INPUT-1A) |
| Office 365 v16.0 (PowerPoint COM) | Category B — PPTX, PPT | AVAILABLE (confirmed WP-INPUT-1A) |
| Office 365 v16.0 (Excel COM) | Category C — XLSX fallback only | AVAILABLE (confirmed WP-INPUT-1A) |

**Environment portability:**

| Environment | Category B | XLSX fallback |
|-------------|-----------|---------------|
| Windows + Office 365 v16.0 | SUPPORTED | SUPPORTED |
| Windows without Office 365 | Category B → Category D | Not available |
| Linux / Docker / CI (non-Windows) | Category B → Category D | Not available |

Cross-environment portability of Category B is a future work package (WP-INPUT-ENV-1). RISK-INP-001 applies.

---

## Open Risks

| ID | Description | Criticality | Blocking |
|----|-------------|-------------|----------|
| RISK-INP-001 | Office 365 dependency for Category B — non-portable to Linux/Docker | HIGH | NON (current env.) |
| RISK-INP-002 | VSDX without conversion path — Visio not installed | MEDIUM | NON |
| RISK-INP-003 | Category C profiles not yet implemented (XLSX, CSV, JSON, YAML, XML, SQL) | HIGH | NON (A/B unaffected) |
| RISK-INP-004 | Phase 0 Eligibility Check not yet implemented in `/preprocess-source` | HIGH | NON (short-term) |
| RISK-INP-005 | Multimodal quality for complex diagrams (ERD, UML, BPMN) not quantified | MEDIUM | NON |

No risk is blocking for ADR adoption. All have documented mitigations or identified future work packages.

---

## Options Considered

**Option A — Format-only classification (rejected)**
Classify all sources by file extension with no eligibility check for structured data.
Rejected: XLSX and CSV are format-neutral — a CRM export and a data dictionary are identical in format but opposite in CSR relevance. Format-only classification produces silent ingestion of operational data as normative knowledge (R-INP-003, R-INP-004 rejected).

**Option B — Blanket rejection of all structured formats (rejected)**
Reject all XLSX, CSV, JSON, SQL files as out of scope.
Rejected: data dictionaries, API schemas, DDL schemas, and business rule registers are structured formats with the highest normative value for enterprise project specifications. Blanket rejection would severely limit CSR applicability in Power Platform and enterprise contexts (R-INP-002 rejected as decision basis).

**Option C — Content eligibility without formal taxonomy (rejected)**
Apply eligibility judgment ad-hoc without a declared 4-category taxonomy.
Rejected: without an explicit taxonomy, format classification remains implicit, undocumented, and unauditable. Users cannot predict which formats are supported, or why. Governance requires explicit declaration.

**Option D — 4-category taxonomy + content-based eligibility for Category C (selected)**
Formal A/B/C/D taxonomy combined with a Phase 0 Eligibility Check for structured formats only.
Selected: the taxonomy makes format support explicit and auditable. The eligibility model anchors decisions in CSR mission rather than format. The combination satisfies governance, traceability, and extensibility requirements simultaneously.

---

## Rationale

**Mission anchoring.** The Knowledge-Oriented / Operational Data discriminant is derived directly from the CSR mission: "transform fragmented knowledge into validated and maintainable specifications." This is not an arbitrary format preference — it is a consequence of what CSR produces. Operational data does not contribute to specifications; processing it produces noise, not knowledge.

**Audit convergence.** Three independent audits (WP-INPUT-1, WP-INPUT-1A, WP-INPUT-2A) converged without contradiction on the same conclusion: the current format-list approach is insufficient and the path forward is a content-anchored taxonomy.

**Additive compatibility.** The strategy does not invalidate any existing ADR-002 profile. Category A formats continue to work identically. Category B adds a conversion step before the existing PDF profile. Category C adds a qualification gate before existing profiles. No existing behavior is broken.

**Realistic prerequisites.** Category B relies solely on Office 365, already installed and confirmed operational. Phase 0 requires no external tools. Rejection traceability extends existing `sources.md` and `events.md` structures.

**Extensibility.** The taxonomy is extensible: a new format requires only a category assignment and, for Category C, a profile in ADR-002. No architectural change is needed.

---

## Consequences

### Positive

- Format support becomes explicit, documented, and auditable via the A/B/C/D taxonomy
- Operational data sources are filtered before they can produce noise in the knowledge base
- Category B (DOCX, PPTX, RTF) becomes fully operational via Office COM automation
- Mixed sources can be partially processed via the scope mechanism — no manual extraction required
- All ingestion decisions are traceable in the workspace registry
- The ADR-004/KPM-001 provenance chain is strengthened: INELIGIBLE sources cannot silently produce SOURCE\_FACTs

### Negative

- Category B requires Office 365 v16.0 — not portable to Linux/Docker environments without additional tooling
- All Category C native profiles (XLSX, CSV, JSON, YAML, XML, SQL) remain to be implemented in ADR-002
- Phase 0 Eligibility Check requires implementation in `/preprocess-source` before the model is effective (currently design-only)
- The scope mechanism adds interactive complexity to the preprocessing flow for mixed sources

### Known Limitations

**L1 — Category C profiles not implemented.** Five ADR-002 profiles are designed but not yet implemented. Category C sources currently fall back to PLAIN TEXT (structure lost) or FALLBACK\_PDF for XLSX only. Implementation backlog: INPUT-RUNTIME-04 (SQL → CSV → JSON/YAML → XML → XLSX).

**L2 — Phase 0 not implemented.** Phase 0 is designed but not yet integrated into `/preprocess-source`. Until implemented, the eligibility model is declarative only — user discipline is the sole protection against operational data ingestion. Implementation backlog: INPUT-RUNTIME-03.

**L3 — Office 365 environment dependency.** Category B is contingent on Windows + Office 365. Cross-environment portability is a future work package (WP-INPUT-ENV-1).

**L4 — Partial scope not implemented.** The partial scope mechanism is designed but not yet implemented for any Category C format. Implementation backlog: INPUT-RUNTIME-06.

---

## Supporting Documents

| Document | Role |
|----------|------|
| [WP-INPUT-1](../analysis/WP-INPUT-1-Source-Ingestion-Audit.md) | Source ingestion audit — identified format gaps |
| [WP-INPUT-1A](../analysis/WP-INPUT-1A-Conversion-Capability-Assessment.md) | Conversion capability assessment — confirmed Office COM availability |
| [WP-INPUT-2A](../analysis/WP-INPUT-2A-Structured-Source-Eligibility-Audit.md) | Structured source eligibility audit — established KO/OD discriminant |
| [WP-INPUT-2](../analysis/WP-INPUT-2-Input-Canonical-Strategy.md) | Input canonical strategy design — normative source for this ADR |
| [WP-INPUT-CLOSEOUT](../analysis/WP-INPUT-CLOSEOUT-Report.md) | WP closeout report — decision register D-INP-001 through D-INP-016 |
| [ADR-002](ADR-002-source-type-aware-extraction.md) | Source Type Aware Extraction — extended by this ADR (Phase 0 + eligibility) |
| [ADR-002\_AMENDMENT\_LIST](../analysis/ADR-002-Amendment-List.md) | Required amendments to ADR-002 consequent to this ADR |

---

## Decision Authority

Product Owner: repository owner
Decision Date: 2026-07-04
Approval Date: 2026-07-04
Status: ACCEPTED
