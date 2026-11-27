# Runtime Engineering Method

## Purpose

This document defines the official implementation methodology for all CSR milestones.

It describes how the repository is evolved, validated and governed as new runtime stages are added.

The method allows:

* reproducible milestone implementation;
* architecture consistency across stages;
* repository-first development without drift;
* safe evolution of the runtime pipeline.

This method emerged from the implementation of `/ingest-source` and `/extract-knowledge`. It is grounded in observed patterns, not theory.

---

## Core Principles

### Repository-first

The repository is the authoritative source of truth at all times.

Conversation history, memory, and prior session context are not authoritative.

When repository content contradicts conversation context, the repository wins.

### Markdown-first

All artifacts — contracts, specifications, templates, commands, decisions — are stored as Markdown files.

### Human-in-the-loop

Human validation is required before any multi-file modification is applied.

No architectural decision is implemented without explicit human approval.

### Claude Code-first

Claude Code is the primary runtime engine for executing commands, running validations, and evolving the repository.

All commands are implemented as Claude Code commands in `.claude/commands/`.

### Fresh Read Before Analysis

Every analysis session begins by re-reading the relevant repository artifacts.

The instruction is explicit: ignore conversation history, ignore prior assumptions, base analysis only on current file content.

This prevents stale context from propagating into decisions.

### Contract → Execution → Prompt → Command

Every runtime command is specified across four layers before implementation begins.

The four layers are defined, consistent, and independently auditable.

### Explicit STATUS Gates

Every phase produces a named STATUS output.

No phase is bypassed. No STATUS is implicit. A blocking STATUS stops advancement until resolved.

---

## Milestone Selection

Before starting a new milestone:

1. Re-read `docs/implementation_status.md`.
2. Re-read `docs/mvp_workflow.md`.
3. Identify the next unimplemented stage in the pipeline.
4. Verify that all upstream dependencies are implemented and validated.
5. Verify that the upstream stage's output is contractualized (all fields required by the new stage are formally defined in the upstream contract).

**Output:**

```
STATUS: NEXT MILESTONE IDENTIFIED
```

If upstream dependencies are missing or undocumented, resolve them before proceeding.

---

## Specification Phase

Each command is specified through four layers. All four must exist before the Assimilation Check begins.

### Layer 1 — Contract

**File:** `docs/commands/<command>.md`

**Role:** Defines what the command does. Specifies inputs, outputs, preconditions, validation rules, failure cases, traceability rules, and completion criteria.

This is the authoritative behavioral definition. All other layers must be consistent with it.

### Layer 2 — Execution Specification

**File:** `docs/commands/<command>_execution.md`

**Role:** Defines how the command executes. Describes each phase, its inputs, actions, failure conditions, and outputs. Defines naming conventions, registry behavior, and status mappings.

This layer bridges intent (contract) and instruction (template).

### Layer 3 — Prompt Template

**File:** `templates/commands/<command>_prompt.md`

**Role:** Provides the direct LLM instruction set. Must be executable as written. Uses imperative language. Covers every behavioral rule the LLM must follow during execution.

### Layer 4 — Claude Command

**File:** `.claude/commands/<command>.md`

**Role:** The invocation entry point. Loads the specifications, orchestrates the execution steps, applies precondition checks, and delegates to the rules defined in layers 1–3.

### Consistency Requirement

The four layers must be mutually consistent on:

* input sources
* output destinations
* execution flow
* validation rules
* failure conditions
* completion criteria

Inconsistencies across layers are blocking.

---

## Assimilation Check Phase

The Assimilation Check is a mandatory gate before implementation.

### Procedure

1. Re-read all four specification layers fresh.
2. Do not rely on conversation history or prior analysis.
3. Verify consistency on each dimension:

   * objective
   * inputs
   * outputs
   * execution flow
   * validation rules
   * traceability
   * completion criteria

4. For each issue found, determine:

   * **Blocking** — prevents correct implementation
   * **Non-blocking** — can be deferred without blocking correctness

5. Apply all blocking fixes.
6. Re-run the check until no blocking issues remain.

### Required Gate

```
STATUS: READY FOR IMPLEMENTATION
```

Implementation does not begin until this STATUS is returned.

---

## Architecture Audit Phase

An Architecture Audit is required when:

* a new stage depends on output fields from an upstream stage;
* a cross-stage workflow is being validated;
* an architectural inconsistency has been detected.

### Cross-Stage Dependency Verification

For every field that a downstream stage depends on:

1. Locate the upstream stage's contract.
2. Verify the field is explicitly listed as a required output.
3. Verify the field is defined in the upstream execution specification.
4. Verify the field is present in the upstream prompt template.
5. Verify the field is present in the upstream Claude command.

If the field exists only in generated artifacts but not in specifications, it is an undocumented implementation detail.

**Output:**

```
STATUS: SAFE TO DEPEND ON <field>
```

or

```
STATUS: <field> IS AN UNDOCUMENTED IMPLEMENTATION DETAIL
```

If undocumented: formalize the field in the upstream artifacts before proceeding. Do not modify the downstream stage until the upstream contract is updated.

### Workflow Consistency Verification

Compare the implemented workflow against `docs/mvp_workflow.md`.

Every stage boundary (input → output) must match the documented pipeline.

If inconsistency is detected, determine which layer is authoritative and align the others.

**Output:**

```
STATUS: OPTION <X> IMPLEMENTED
```

---

## Plan Before Action Phase

No repository modification is applied without a validated plan.

### Procedure

1. Perform an impact analysis:

   * list every file that must change;
   * identify every location within each file;
   * count occurrences.

2. Write the modification plan:

   * for each change, show old content and new content exactly;
   * no implicit changes.

3. Present the plan to the human.

4. Wait for explicit validation.

5. Apply changes only after validation is received.

6. Verify each change after application.

### Rule

```
No modification before validation.
```

This applies to single-file edits, multi-file corrections, and architectural alignments alike.

---

## Implementation Phase

After `STATUS: READY FOR IMPLEMENTATION` and all architecture audits are resolved:

1. Execute the command following the specifications.
2. Verify each generated artifact:

   * correct location
   * correct naming convention
   * correct content structure
   * traceability preserved

3. Verify the source registry is updated.
4. Confirm no artifacts were written to unexpected locations.

---

## E2E Validation Phase

E2E Validation confirms that the full runtime chain works correctly — not just the most recently implemented command.

### Scope

Validate every link in the chain from first input to last output:

```
input/ → stage 1 → intermediate artifact → stage 2 → output artifact → registry
```

### Procedure

For each stage in the chain:

1. Verify the stage's input exists and is correct.
2. Verify the stage's output exists and was produced correctly.
3. Verify the provenance: the output was produced by the correct stage using the correct input path.
4. Verify registry state is consistent.
5. Verify workflow integrity: no stage was bypassed.

### Provenance Requirement

It is not sufficient for an artifact to exist and have valid content.

The artifact must have been produced by executing the current pipeline specification.

An artifact produced under a previous (since-corrected) specification does not satisfy E2E validation.

### Required Gate

```
STATUS: E2E VALIDATED
```

### On Failure

```
STATUS: E2E FAILED
```

Identify:

* the blocking issue;
* the affected artifacts;
* the minimal corrective action.

Apply the correction, then re-run E2E Validation.

---

## Decision Capture Phase

After `STATUS: E2E VALIDATED`. This phase applies identically to a new milestone and to a corrective patch on an already-certified milestone (e.g. a post-certification bugfix work package) — the scope of the change does not reduce the registry-update obligation. Two work packages (SQF Phase 2/WP-SQF-4, WP-EVOLVE-2) skipped this phase in 2026-07 specifically because their closure was treated as "too small to need it" — see (internal review note).

1. Document each architecture decision made during the milestone in `docs/implementation_status.md`.

   Each decision entry must include:
   * a short name;
   * a description of what was decided;
   * why it was decided (constraint or rationale).

   Cross-cutting governance decisions that affect multiple milestones or the entire pipeline are captured as Architecture Decision Records (ADRs) in `docs/decisions/`. ADRs use the format defined in `docs/decisions/ADR-001-csr-language-policy.md`. Each ADR has a sequential ID, a title, a status (PROPOSED / ACCEPTED / SUPERSEDED), and sections for Context, Decision, Rationale, Consequences, and Future Considerations.

2. Update all relevant sections of `docs/implementation_status.md`, **including the chronological `## Status` log at the top of the file** — an entry in "Chat Resume Instructions" alone is not sufficient and must not be treated as a substitute:

   * `## Status` (chronological log — mandatory entry for this work package)
   * Completed Milestones
   * Runtime Coverage
   * Implemented Commands
   * Repository State
   * Next Recommended Milestone
   * Latest Validation Result

3. Update the version number if a milestone boundary was crossed.

---

## STATUS Protocol

The STATUS protocol provides explicit decision gates throughout the method.

| STATUS | Phase | Meaning |
| ------ | ----- | ------- |
| `NEXT MILESTONE IDENTIFIED` | Milestone Selection | Dependencies verified, next stage confirmed |
| `CONSISTENT` | Assimilation Check | No issues found across all reviewed artifacts |
| `ISSUES FOUND` | Assimilation Check | One or more inconsistencies detected |
| `READY FOR IMPLEMENTATION` | Assimilation Check | All blocking issues resolved, implementation may proceed |
| `BLOCKED` | Any | A blocking issue prevents advancement; requires resolution |
| `SAFE TO DEPEND ON <field>` | Architecture Audit | Field is formally documented in upstream contract |
| `<field> IS AN UNDOCUMENTED IMPLEMENTATION DETAIL` | Architecture Audit | Field exists in generated artifacts but not in specifications |
| `FORMALLY CONTRACTUALIZED` | Architecture Audit | Field has been added to all upstream specification layers |
| `OPTION <X> SUPPORTED` | Architecture Audit | Repository evidence supports a specific workflow option |
| `INCONSISTENT / UNDECIDED` | Architecture Audit | Repository contains contradictory evidence; human decision required |
| `OPTION <X> IMPLEMENTED` | Architecture Audit | Workflow alignment applied across all affected artifacts |
| `E2E VALIDATED` | E2E Validation | Full chain validated, provenance confirmed, registry consistent |
| `E2E FAILED` | E2E Validation | At least one chain link failed; blocking issue identified |
| `METHOD DOCUMENT VALIDATED` | Method Assimilation Check | Method document is consistent with repository and principles |

---

## Definition of Done

A milestone is complete only when all of the following are true:

* [ ] All four specification layers exist and are internally consistent
* [ ] Assimilation Check returned `STATUS: READY FOR IMPLEMENTATION`
* [ ] All cross-stage dependencies are contractualized
* [ ] Architecture Audit returned required STATUS gates
* [ ] All planned modifications were presented and validated before application
* [ ] Implementation completed with artifacts in correct locations
* [ ] E2E Validation returned `STATUS: E2E VALIDATED`
* [ ] Architecture decisions documented in `docs/implementation_status.md`
* [ ] `docs/implementation_status.md` updated (milestones, coverage, commands, workflow, version) — **including a new entry in the chronological `## Status` log specifically, not only in "Chat Resume Instructions"**
* [ ] Repository is internally consistent (no `input/` references in `extract-knowledge` artifacts, etc.)

---

## Recommended Workflow

```text
Milestone Selection
  ↓  STATUS: NEXT MILESTONE IDENTIFIED
Specification
  (Contract → Execution Spec → Prompt Template → Claude Command)
  ↓
Assimilation Check
  ↓  STATUS: READY FOR IMPLEMENTATION
Architecture Audit
  (dependency check, workflow consistency)
  ↓  STATUS: SAFE TO DEPEND ON / OPTION IMPLEMENTED
Plan → Validate → Apply
  (impact analysis, human validation, modification)
  ↓
Implementation
  (execute command, verify artifacts)
  ↓
E2E Validation
  ↓  STATUS: E2E VALIDATED
Decision Capture
  (architecture decisions, status update)
  ↓
Checkpoint
  (git commit, version bump)
  ↓
Next Milestone
```

---

## Future Usage

Every future CSR milestone follows this method without exception.

### Examples

**`/detect-conflicts`**

* Consumes: `knowledge_base/extracted/`
* Produces: `knowledge_base/conflicts/`
* Dependency audit required: verify all fields consumed from extracted artifacts are contractualized in `/extract-knowledge` outputs
* Four-layer specification required before Assimilation Check

**`/generate-questions`**

* Consumes: `knowledge_base/conflicts/`
* Produces: `knowledge_base/questions/` and `output/generated_questions/`
* Dependency audit required: verify conflict record format is contractualized in `/detect-conflicts` outputs

**`/consolidate-knowledge`**

* Consumes: validated knowledge from multiple stages
* Produces: `knowledge_base/consolidated/` and `knowledge_base/decisions/`
* Multi-stage dependency audit required

### Session Recovery

When resuming work in a new session:

1. Re-read `README.md`, `CLAUDE.md`, `docs/implementation_status.md`, `docs/runtime_engineering_method.md`.
2. Run `git log --oneline -10`.
3. Identify the current phase from `docs/implementation_status.md`.
4. Continue from where the last checkpoint left off.
5. Do not assume any prior session context. Re-read artifacts fresh.

### Onboarding a New Contributor

A new contributor — human or AI — must:

1. Read this document in full.
2. Read `docs/implementation_status.md` for current project state.
3. Read `docs/mvp_workflow.md` for the target pipeline.
4. Understand that the repository is the only authoritative source.
5. Never apply modifications without presenting a plan first.
6. Never skip a STATUS gate.
