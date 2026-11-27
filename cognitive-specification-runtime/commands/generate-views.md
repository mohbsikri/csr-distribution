# /generate-views

## Purpose

Generate audience-derived view artifacts from a BASELINED canonical specification.

This command implements ADR-003 — Specification Audience Model. It produces four audience-specific views derived from a BASELINED canonical specification. Views are generated artifacts; they are never governed by the specification lifecycle and must never be edited directly.

This command implements Stage 9 — Audience View Generation of the CSR pipeline.

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
                       BLOCKING: STATUS: BLOCKED — WORKSPACE DRIFT DETECTED.
              Case C — Resolver absent: resolver_workspace_id is null; one active entry in registry →
                       BLOCKING: STATUS: BLOCKED — RESOLVER ABSENT.
              Case D — No active entry: zero status:active entries in registry →
                       BLOCKING: STATUS: BLOCKED — NO ACTIVE WORKSPACE.
              Case E — Multiple active entries: more than one status:active entry →
                       BLOCKING: STATUS: BLOCKED — REGISTRY INTEGRITY VIOLATION.
Step W5: All subsequent paths are prefixed with WORKSPACE_ROOT.
```

## Workspace Isolation

All write operations must target paths within `WORKSPACE_ROOT/specifications/views/` or `WORKSPACE_ROOT/specifications/draft/specifications_report.md`.

Exceptions (not workspace-scoped): `runtime/current_workspace.md`, `runtime/workspaces.md`, `docs/`, `templates/`, `.claude/`

---

## Preconditions

1. Active workspace resolves correctly (W1–W5).
2. The following canonical specification exists and is readable:
   ```text
   WORKSPACE_ROOT/specifications/stable/<base>_specification.md
   ```
3. The canonical specification carries BASELINED status (STD: `status: BASELINED` in YAML; LEGACY: `**Status:** BASELINED` in Markdown bold). If status ≠ BASELINED: BLOCKED.
4. The `specifications/views/` directory exists or can be created.

---

## Execution

### Step 1 — Load Specification Layers

Read and assimilate all three layers:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/generate-views.md                     ← L1 contract
${CLAUDE_PLUGIN_ROOT}/docs/commands/generate-views_execution.md           ← L2 execution spec
${CLAUDE_PLUGIN_ROOT}/templates/commands/generate_views_prompt.md         ← L3 prompt (section structures, diagrams, [GAP] rules)
```

The repository is the source of truth.

### Step 2 — Execute View Generation Runtime

Execute the runtime defined in `${CLAUDE_PLUGIN_ROOT}/docs/commands/generate-views_execution.md`.

Phases: workspace resolution → load L3 prompt → load canonical spec (**detect spec format: STD if first line `---`, LEGACY otherwise**) → parse status/spec_id/baseline_date (YAML for STD, Markdown bold for LEGACY) → detect Inference Registry heading (`## Annexe A — Inference Registry` for STD, `## Inference Registry` for LEGACY) → build STD section content map (Phase 2c, STD only) → prepare output directory → generate 5 documents (SF + DAT + STD + QA + Agent) with bilingual pairs using spec-format-aware content sourcing → update generation log → report.

Section structures, Mermaid diagram templates, [GAP] block rules, cover page HTML, and document naming are all defined in `${CLAUDE_PLUGIN_ROOT}/templates/commands/generate_views_prompt.md`.

---

## Audience Content Scope

Content scope for each view profile (Métier, Architecte, Développeur, Agent IA) is defined in:

```text
${CLAUDE_PLUGIN_ROOT}/docs/decisions/ADR-003-specification-audience-model.md
${CLAUDE_PLUGIN_ROOT}/docs/commands/generate-views_execution.md
```

## Expected Output

Eight view files are generated (four document types × two languages), with professional names per `${CLAUDE_PLUGIN_ROOT}/templates/commands/generate_views_prompt.md`:

```text
WORKSPACE_ROOT/specifications/views/<base>_specification_fonctionnelle_fr.md
WORKSPACE_ROOT/specifications/views/<base>_functional_specification_en.md
WORKSPACE_ROOT/specifications/views/<base>_dossier_architecture_fr.md
WORKSPACE_ROOT/specifications/views/<base>_technical_architecture_en.md
WORKSPACE_ROOT/specifications/views/<base>_specification_technique_fr.md
WORKSPACE_ROOT/specifications/views/<base>_technical_specification_en.md
WORKSPACE_ROOT/specifications/views/<base>_view_agent_fr.md
WORKSPACE_ROOT/specifications/views/<base>_view_agent_en.md
WORKSPACE_ROOT/specifications/draft/specifications_report.md  ← updated (GAP count per view)
```

Agent IA views remain Markdown only and are not exported to HTML by /export-views.

## Completion Reporting

```text
STATUS: GENERATE-VIEWS COMPLETE
STATUS: GENERATE-VIEWS PARTIAL
STATUS: GENERATE-VIEWS BLOCKED
```
