# /detect-conflicts

## Purpose

Scan extracted knowledge artifacts and produce structured conflict records for downstream resolution. AMBIGUITY is detected **within** each artifact; CONTRADICTION and GAP are detected **between** artifacts. Contradiction **within** a single document is a separate capability, owned by `/extract-knowledge` (Bloc 5, corrected 2026-11-01 — see its L1 contract) and already complete by the time this command runs.

The command transforms a set of independent extracted knowledge artifacts into an explicit conflict inventory that downstream stages can act upon.

---

## Inputs

Accepted inputs:

* One or more extracted knowledge artifacts located in `workspaces/<workspace_id>/knowledge_base/extracted/`
* Knowledge index artifacts (`<base>_knowledge_index.md`) located in `workspaces/<workspace_id>/knowledge_base/extracted/` — optional input used in two-pass mode when N > 5 knowledge sources are present

All input artifacts must have been produced by `/extract-knowledge`.

---

## Two-Pass Scalability Mode

When the workspace contains more than 5 knowledge sources, /detect-conflicts operates in two-pass mode:

**Pass 1 — Index Scan (bounded context):**
Load all knowledge index artifacts (`<base>_knowledge_index.md` for each source). Identify candidate source pairs by comparing BR/TR/C IDs and topics across indices. Sources with no overlapping IDs or related topics are excluded from the detailed conflict scan.

**Pass 2 — Targeted Analysis:**
Load only the full knowledge artifacts for source pairs in the candidate set. Execute conflict detection on the targeted artifacts.

When N ≤ 5 sources, single-pass mode loads all full artifacts directly (existing behavior).

The two-pass mode does not change conflict detection outputs, validation rules, or artifact formats.

---

## Outputs

Generated conflict report stored in:

```text
workspaces/<workspace_id>/knowledge_base/conflicts/conflicts_report.md
```

The report contains all detected conflicts, classified by type and severity.

An empty report (zero conflicts detected) is a valid output.

---

## Conflict Types

| Type | Definition | Applies to |
| ---- | ---------- | ---------- |
| CONTRADICTION | Two items make opposing or logically incompatible claims | Cross-artifact, same category |
| AMBIGUITY | A single item is insufficiently specific for downstream use | Any item in any artifact |
| GAP | A knowledge category present in some sources is absent from others | Cross-artifact category comparison |
| DUPLICATION | Two items express the same knowledge in different wording | Cross-artifact, same category — optional, MVP deferred |

---

## Conflict Severity

| Severity | Definition |
| -------- | ---------- |
| BLOCKING | Conflict cannot be resolved without explicit human input. Consolidation must not proceed on the affected items until resolved. |
| ADVISORY | Conflict can be resolved by convention or automatic rule. Consolidation may proceed with a documented default. |

**Default severity by type:**

| Type | Default Severity |
| ---- | ---------------- |
| CONTRADICTION | BLOCKING |
| AMBIGUITY | BLOCKING |
| GAP | ADVISORY |
| DUPLICATION | ADVISORY |

**Severity exceptions:**

* AMBIGUITY items located in the `# Terminology` section are ADVISORY.
* GAP affecting `# Business Rules` or `# Constraints` is BLOCKING when at least one other artifact has that section populated.

---

## Conflict Record Format

Each conflict in the report must follow this structure:

```markdown
## <conflict_id>

**Type:** CONTRADICTION | AMBIGUITY | GAP
**Severity:** BLOCKING | ADVISORY
**Status:** open

**Description:** [one sentence]

**Affected Items:**
[see per-type format below]
```

### CONTRADICTION record

```markdown
**Affected Items:**

Item A:
- Source: `workspaces/<workspace_id>/knowledge_base/extracted/<file>.md`
- Section: `# <Section>`
- Content: `<exact text>`

Item B:
- Source: `workspaces/<workspace_id>/knowledge_base/extracted/<file>.md`
- Section: `# <Section>`
- Content: `<exact text>`
```

### AMBIGUITY record

```markdown
**Affected Item:**
- Source: `workspaces/<workspace_id>/knowledge_base/extracted/<file>.md`
- Section: `# <Section>`
- Content: `<exact text>`
- Reason: `<why it is ambiguous>`
```

### GAP record

```markdown
**Absent from:**
- `workspaces/<workspace_id>/knowledge_base/extracted/<file>.md` — section `# <Section>` not present

**Present in:**
- `workspaces/<workspace_id>/knowledge_base/extracted/<other_file>.md` — section `# <Section>` populated
```

---

## Conflict ID Convention

Conflict IDs are sequential integers zero-padded to three digits, prefixed with `C`:

```text
C001, C002, C003, ...
```

IDs are assigned in detection order within a single report run. They reset on each new report generation.

---

## Preconditions

At least one extracted knowledge artifact must exist in `workspaces/<workspace_id>/knowledge_base/extracted/`.

All artifacts must be accessible and readable.

Repository structure must be valid.

---

## Execution Rules

The command shall:

1. Discover all knowledge artifacts in `workspaces/<workspace_id>/knowledge_base/extracted/`.
2. Parse each artifact into sections and items.
3. Detect AMBIGUITY within each artifact.
4. Detect CONTRADICTION across artifacts by category.
5. Detect GAP by comparing category presence across artifacts.
6. Assign conflict IDs, types, severities, and statuses.
7. Generate the conflicts report.
8. Write the report to `workspaces/<workspace_id>/knowledge_base/conflicts/conflicts_report.md`.

---

## Validation Rules

Each conflict record must be:

* traceable to at least one source artifact and section;
* classified with a type from the approved taxonomy;
* assigned a severity;
* assigned status `open`.

A conflict must not be invented. Every conflict must be supported by evidence in the analyzed artifacts.

---

## Language Policy

Conflict descriptions, reasons, and all runtime-generated text in the conflict report must be written in English.

The `Content` field in each conflict record quotes directly from upstream extracted knowledge artifacts. Extracted knowledge artifacts are produced in English per the `/extract-knowledge` language policy. Conflict records therefore inherit English content from their upstream source.

If an extracted knowledge artifact is found to contain non-English text, this indicates an upstream ADR-001 compliance gap. Report it explicitly. Do not proceed with conflict detection on that artifact.

---

## Failure Cases

The command must stop when:

* no extracted knowledge artifacts exist in `workspaces/<workspace_id>/knowledge_base/extracted/`;
* an artifact cannot be read;
* repository structure is invalid;
* a conflict record cannot be traced to a source artifact.

Failures must be reported explicitly.

---

## Traceability Rules

Every conflict record must reference:

* the source artifact filename(s);
* the section name(s);
* the exact content of the affected item(s).

Traceability must remain available for downstream stages (`/generate-questions`, `/consolidate-knowledge`).

---

## Completion Criteria

The command is complete when:

* all artifacts in `workspaces/<workspace_id>/knowledge_base/extracted/` have been analyzed;
* all detected conflicts have been classified and recorded;
* `workspaces/<workspace_id>/knowledge_base/conflicts/conflicts_report.md` has been written;
* every conflict record is traceable.
