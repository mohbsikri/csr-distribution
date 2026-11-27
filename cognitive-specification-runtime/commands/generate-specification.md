# /generate-specification

## Purpose

Transform consolidated knowledge artifacts into structured draft specification artifacts.

This command is non-interactive. It applies a deterministic structural transformation to consolidated (and zero-conflict extracted) knowledge artifacts to produce one draft specification per source group, records generation metadata in the specification log, and reports the completion state.

This command implements Step 7 — Specification Generation of the CSR pipeline.

---

## Workspace Resolution

Before any file operation, resolve the active workspace:

```text
Step W1: Read runtime/current_workspace.md and parse workspace_id.
         If absent or empty: record resolver_workspace_id as null; skip W2–W3; proceed to W4.
Step W2: Build WORKSPACE_ROOT = workspaces/<workspace_id>/
Step W3: Verify WORKSPACE_ROOT exists. If not found, stop and report:
         STATUS: BLOCKED — Workspace Root Not Found: workspaces/<workspace_id>/
Step W4: Read runtime/workspaces.md. Validate registry (R4a–R4e):
         R4a: workspace_id must be present in registry — BLOCKING if missing.
         R4b: status must not be 'archived' — BLOCKING; warn if 'paused' or 'completed'.
         R4c: runtime_version must be present — WARNING if missing.
         R4d: last_active must be present — WARNING if missing.
         R4e (M10 revision): count entries with status:active in runtime/workspaces.md.
              Case A — Normal: exactly one active entry; its workspace_id = resolver_workspace_id → continue.
              Case B — Drift: exactly one active entry; its workspace_id ≠ resolver_workspace_id →
                       BLOCKING: STATUS: BLOCKED — WORKSPACE DRIFT DETECTED. Resolver names
                       <resolver_workspace_id>; registry active entry is <registry_active_workspace_id>.
                       Run /workspace-lifecycle SWITCH to synchronize runtime/current_workspace.md.
              Case C — Resolver absent: resolver_workspace_id is null; one active entry in registry →
                       BLOCKING: STATUS: BLOCKED — RESOLVER ABSENT. Registry identifies
                       <registry_active_workspace_id> as active but runtime/current_workspace.md is
                       absent or empty. Run /workspace-lifecycle SWITCH <registry_active_workspace_id>.
              Case D — No active entry: zero status:active entries in registry →
                       BLOCKING: STATUS: BLOCKED — NO ACTIVE WORKSPACE. Registry has no status:active
                       entry. Run /workspace-lifecycle SWITCH to designate an active workspace.
              Case E — Multiple active entries: more than one status:active entry in registry →
                       BLOCKING: STATUS: BLOCKED — REGISTRY INTEGRITY VIOLATION. Multiple status:active
                       entries in runtime/workspaces.md. Manual correction required.
Step W5: All subsequent paths are prefixed with WORKSPACE_ROOT.
```

## Workspace Isolation

All file operations must target paths prefixed with `WORKSPACE_ROOT`.

Exceptions (not workspace-scoped): `runtime/current_workspace.md`, `runtime/workspaces.md`, `docs/`, `templates/`, `.claude/`

Any operation targeting a path outside `WORKSPACE_ROOT` that is not on the exception list must be rejected and reported as workspace contamination.

---

## Preconditions

Before execution:

1. All specification artifacts must exist and be readable:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/generate-specification.md
${CLAUDE_PLUGIN_ROOT}/docs/commands/generate-specification_execution.md
${CLAUDE_PLUGIN_ROOT}/templates/prompts/generate_specification_prompt.md
```

2. At least one of the following must exist:

```text
WORKSPACE_ROOT/knowledge_base/consolidated/*_consolidated.md   (at least one file)
WORKSPACE_ROOT/knowledge_base/extracted/*_knowledge.md         (at least one file, zero-conflict fallback)
```

3. When consolidated artifacts are present, the consolidation authority record must exist and be readable:

```text
WORKSPACE_ROOT/knowledge_base/consolidated/consolidation_report.md
```

4. The draft specification output directory must exist:

```text
WORKSPACE_ROOT/specifications/draft/
```

5. The conflicts report is required for ADVISORY flag insertion — WARNING only if absent:

```text
WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md
```

If absent: ADVISORY unresolved conflict flags cannot be inserted. Report a WARNING and proceed.

6. At least one eligible source group must exist after eligibility determination. Eligibility is verified during execution as defined in the execution specification.

If any BLOCKING precondition fails, report the failure explicitly and stop. Do not proceed to execution.

---

## Execution

### Step 1 — Load Specifications

Read and assimilate:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/generate-specification.md
${CLAUDE_PLUGIN_ROOT}/docs/commands/generate-specification_execution.md
${CLAUDE_PLUGIN_ROOT}/templates/prompts/generate_specification_prompt.md
```

The repository is the source of truth.

Ignore any prior conversational assumptions not present in the repository.

All execution procedures are defined in `${CLAUDE_PLUGIN_ROOT}/docs/commands/generate-specification_execution.md`.

All behavioral constraints, decision rules, and artifact format requirements are defined in `${CLAUDE_PLUGIN_ROOT}/templates/prompts/generate_specification_prompt.md`.

---

### Step 2 — Execute Specification Generation Runtime

Execute the runtime defined in:

```text
${CLAUDE_PLUGIN_ROOT}/templates/prompts/generate_specification_prompt.md
```

Execution is non-interactive. Conduct it in the following order as defined in the execution specification:

1. Resolve the active workspace and verify the output directory exists.
2. **Detect template_mode (Phase 1.5):** Read `spec_template_version` from `runtime/workspaces.md` for the active workspace. `v1` → `template_mode = STD`; `legacy` or absent → `template_mode = LEGACY` (WARNING if absent). If `spec_mode = V2` (lineage.md present), force `template_mode = LEGACY` regardless of `spec_template_version`.
3. Discover consolidated and extracted source candidates; load the consolidation authority record (extract `**Type:**` and `**Consolidated Artifact (Secondary):**` fields for CONTRADICTION records; build dual-path Consolidation Index registering CONTRADICTION records under both primary and secondary paths; stop on PARTIAL RECORD DETECTED if any CONSOLIDATED CONTRADICTION record is missing the secondary path), conflicts report (build type-dispatched Conflicts Index: AMBIGUITY → 1 entry per conflict using `Section:` in `**Affected Item:**`; GAP → 1 entry per conflict using annotation after ` — ` in `**Absent from:**`; CONTRADICTION → 2 entries per conflict using `Item A Section:` and `Item B Section:`), and generation log.
4. Determine eligibility for each candidate — every BLOCKING conflict for the source must be CONSOLIDATED; for CONTRADICTION conflicts, the source is associated via either the primary (`**Consolidated Artifact:**`) or secondary (`**Consolidated Artifact (Secondary):**`) path (dual-path lookup); EXTRACTED candidates are unconditionally eligible for this check.
5. Load source artifacts; perform the ADR-001 language compliance check for each candidate.
6. Resolve the canonical specification section structure for each eligible candidate.
7. Assemble draft specification documents — **LEGACY mode:** content reproduced verbatim from source artifacts; ADVISORY UNRESOLVED flags inserted; 7-section structure. **STD mode:** execute Phase 6-STD (FR/AC/NFR/OP derivation, S0–S15 sections, Annexes A/B); see STD Mode Guidance in `${CLAUDE_PLUGIN_ROOT}/templates/prompts/generate_specification_prompt.md`.
8. Write draft specification artifacts to `WORKSPACE_ROOT/specifications/draft/`.
9. Write or update the generation log at `WORKSPACE_ROOT/specifications/draft/specifications_report.md`.
10. Run post-execution validation rules SG1–SG16 (SG14–SG16 apply to STD mode only).

Do not introduce business logic beyond what is defined in the specification artifacts.

Do not modify `WORKSPACE_ROOT/knowledge_base/consolidated/consolidation_report.md`, `WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md`, any `*_consolidated.md` file in `WORKSPACE_ROOT/knowledge_base/consolidated/`, or any `*_knowledge.md` file in `WORKSPACE_ROOT/knowledge_base/extracted/`.

---

## ADR-001 Compliance

All draft specification artifacts must be written in English, as required by:

```text
${CLAUDE_PLUGIN_ROOT}/docs/decisions/ADR-001-csr-language-policy.md
```

The upstream pipeline guarantees English content in all consumed artifacts. This command performs no translation.

If non-English content is detected in a source artifact during execution: report an ADR-001 compliance failure for that candidate and continue with remaining candidates. If all candidates fail ADR-001: declare SPECIFICATION BLOCKED.

---

## Bilingual Output

Per `${CLAUDE_PLUGIN_ROOT}/docs/conventions/bilingual_output.md`, generate two companion specification files for each produced artifact:

```text
WORKSPACE_ROOT/specifications/draft/<base>_specification_en.md   ← ADR-001 primary (English)
WORKSPACE_ROOT/specifications/draft/<base>_specification_fr.md   ← FR companion
```

The EN file is the ADR-001-compliant primary artifact (written in English). The FR file is the translated companion. Both share the same rule IDs, Status, and traceability structure. Technical identifiers are not translated.

If the source knowledge artifact contains content in the workspace primary language (e.g., French), the EN file is the translated version and the FR file preserves the source content.

---

## Validation

Before reporting the completion state, verify that:

* every specification declared as GENERATED in the log has a corresponding file at the declared path that exists and is readable;
* **LEGACY mode:** every generated specification file has all seven required header fields with non-empty values and `**Status:** DRAFT` in its header block;
* **STD mode:** every generated specification file has a valid YAML frontmatter block (8 fields) plus a generation metadata block (7 fields) in the body;
* `Conflicts Incorporated` in each CONSOLIDATED-type specification matches the `**Conflicts Resolved:**` field of its source consolidated artifact; EXTRACTED-type specifications carry `none`;
* `Questions Incorporated` in each CONSOLIDATED-type specification matches the union of question IDs from the `## Resolved Conflicts` table of its source consolidated artifact; EXTRACTED-type specifications carry `none`;
* all write operations targeted paths within `WORKSPACE_ROOT/specifications/draft/`;
* `WORKSPACE_ROOT/specifications/draft/specifications_report.md` exists and is readable;
* all source consolidated and extracted artifacts are unmodified from their state at load time;
* `consolidation_report.md` is unmodified from their state at load time;
* **LEGACY mode:** resolution notes in CONSOLIDATED-type specifications are present verbatim from the source consolidated artifact — no note missing, paraphrased, or summarized;
* all post-execution validation rules SG1–SG16 defined in the execution specification pass (SG14–SG16 apply to STD mode only).

---

## Failure Handling

Stop execution and report an explicit error when:

* any specification artifact cannot be read;
* workspace resolution fails (workspace root not found, workspace archived, workspace ID not in registry, workspace contamination);
* `WORKSPACE_ROOT/specifications/draft/` does not exist;
* no source artifacts exist (no consolidated and no extracted);
* `consolidation_report.md` is absent when consolidated artifacts are present;
* a CONTRADICTION conflict has status CONSOLIDATED in `consolidation_report.md` but is missing `**Consolidated Artifact (Secondary):**` — stop immediately and report PARTIAL RECORD DETECTED; do not classify as SKIP;
* no eligible source groups remain after eligibility determination;
* the generation log write fails after specification files have been produced — append a GENERATION FAILURE NOTE to each affected specification file and stop.

Do not silently continue after a blocking failure.

Per-candidate failures (unreadable artifact, missing required header fields, ADR-001 compliance failure, write failure): continue with remaining candidates. Declare SPECIFICATION PARTIAL at completion.

For all failure conditions, per-candidate failure categories, and recovery procedures, follow `${CLAUDE_PLUGIN_ROOT}/docs/commands/generate-specification_execution.md` Phase 10.

---

## Completion Criteria

Execution is complete when:

* at least one draft specification was generated;
* a draft specification artifact exists at the declared path for each processed source group;
* `WORKSPACE_ROOT/specifications/draft/specifications_report.md` has been written or updated with GENERATED entries for each processed source group;
* all source consolidated and extracted artifacts are unmodified;
* all post-execution validation rules SG1–SG13 pass;
* the completion state has been reported.

---

## Completion Reporting

Report one of three completion states:

```text
STATUS: SPECIFICATION COMPLETE
```

```text
STATUS: SPECIFICATION PARTIAL
```

```text
STATUS: SPECIFICATION BLOCKED
```

Completion state definitions are specified in `${CLAUDE_PLUGIN_ROOT}/docs/commands/generate-specification.md`.

Include in the report:

* number of specifications generated (CONSOLIDATED-type and EXTRACTED-type counts);
* list of generated specification artifact paths;
* any ineligible source groups with stated reasons;
* any per-candidate failures with stated reasons;
* any warnings issued during execution (including missing conflicts report, workspace drift).

---

## Expected Output

**V1 mode (LEGACY template):**

```text
WORKSPACE_ROOT/specifications/draft/<base>_specification.md          ← new or overwritten per source group
WORKSPACE_ROOT/specifications/draft/<base>_traceability.md           ← traceability matrix
WORKSPACE_ROOT/specifications/draft/specifications_report.md         ← written or updated in-place
```

**V1 mode (STD template — spec_template_version: v1):**

```text
WORKSPACE_ROOT/specifications/draft/<base>_specification.md          ← YAML frontmatter + S0–S15 + Annexes A/B
WORKSPACE_ROOT/specifications/draft/<base>_traceability.md           ← extended traceability matrix (FR/AC/NFR/OP rows)
WORKSPACE_ROOT/specifications/draft/specifications_report.md         ← written or updated in-place
```

**V2 mode** (when `runtime/lineage.md` is present — forces LEGACY template regardless of spec_template_version):

```text
WORKSPACE_ROOT/specifications/draft/<inherited_base>_specification_v2.md   ← merged v1+v2 spec with Section Δ
WORKSPACE_ROOT/specifications/draft/<inherited_base>_traceability_v2.md    ← full v2 traceability matrix
WORKSPACE_ROOT/specifications/draft/specifications_report.md               ← updated in-place
```

V2 mode reads (read-only):

```text
WORKSPACE_ROOT/runtime/lineage.md                                     ← V2 context signal
WORKSPACE_ROOT/specifications/stable/<inherited_base>_specification.md ← inherited v1 BASELINED spec
```

No other repository areas are modified by this command.

`WORKSPACE_ROOT/knowledge_base/consolidated/*_consolidated.md` files are read as input and must not be modified.
`WORKSPACE_ROOT/knowledge_base/extracted/*_knowledge.md` files are read as input and must not be modified.
`WORKSPACE_ROOT/knowledge_base/consolidated/consolidation_report.md` is read as input and must not be modified.
`WORKSPACE_ROOT/knowledge_base/conflicts/conflicts_report.md` is read as input and must not be modified.
