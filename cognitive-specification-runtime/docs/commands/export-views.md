# /export-views — L1 Contract

## Purpose

Convert human-facing specification views (Spécification Fonctionnelle, Dossier d'Architecture, Spécification Technique) and the test specification book (cahier de recette) `[C2c, 2026-11-01]` from Markdown to auto-contained HTML files for stakeholder delivery.

HTML output renders Mermaid diagrams natively in any browser, applies the workspace CSS theme, and is printable to PDF from the browser. The output folder is self-contained and works offline.

Agent IA views are excluded — they are machine-readable and remain Markdown.

Requires Pandoc installed on the system. Install: `winget install pandoc` (Windows) or pandoc.org.

---

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| Active workspace BASELINED spec | Mandatory | Determines `<base>` if no argument given |
| `specifications/views/<base>_specification_fonctionnelle_fr.md` | Conditional | FR functional spec view |
| `specifications/views/<base>_functional_specification_en.md` | Conditional | EN functional spec view |
| `specifications/views/<base>_dossier_architecture_fr.md` | Conditional | FR architecture view |
| `specifications/views/<base>_technical_architecture_en.md` | Conditional | EN architecture view |
| `specifications/views/<base>_specification_technique_fr.md` | Conditional | FR technical spec view |
| `specifications/views/<base>_technical_specification_en.md` | Conditional | EN technical spec view |
| `output/test-cases/<base>_test_cases_fr.md` | Conditional `[C2c, 2026-11-01]` | FR cahier de recette |
| `output/test-cases/<base>_test_cases_en.md` | Conditional `[C2c, 2026-11-01]` | EN cahier de recette |
| `templates/html/base_template.html` | Mandatory | HTML shell with theme and base CSS placeholders |
| `templates/html/base.css` | Mandatory | Structural styles |
| `workspaces/<id>/theme.css` OR `templates/html/themes/default.css` | Mandatory | CSS design tokens |
| `templates/html/mermaid.min.js` | Recommended | Offline Mermaid rendering (WARNING if absent) |

---

## Outputs

```text
WORKSPACE_ROOT/output/deliverables/<base>_specification_fonctionnelle_fr.html
WORKSPACE_ROOT/output/deliverables/<base>_functional_specification_en.html
WORKSPACE_ROOT/output/deliverables/<base>_dossier_architecture_fr.html
WORKSPACE_ROOT/output/deliverables/<base>_technical_architecture_en.html
WORKSPACE_ROOT/output/deliverables/<base>_specification_technique_fr.html
WORKSPACE_ROOT/output/deliverables/<base>_technical_specification_en.html
WORKSPACE_ROOT/output/deliverables/<base>_test_cases_fr.html   ← conditional, [C2c, 2026-11-01]
WORKSPACE_ROOT/output/deliverables/<base>_test_cases_en.html   ← conditional, [C2c, 2026-11-01]
WORKSPACE_ROOT/output/deliverables/mermaid.min.js   ← copied once for offline rendering
```

---

## Output properties

| Property | Value |
|----------|-------|
| Format | HTML5, one file per document |
| Self-contained | CSS inlined; mermaid.min.js in same output folder |
| Offline | Yes — no CDN, no server required |
| Mermaid diagrams | flowchart, stateDiagram-v2, erDiagram, sequenceDiagram, pie |
| Print to PDF | Browser File → Print → Save as PDF |
| Theme | Workspace-specific or CSR default |

---

## Workspace Resolution

```text
Step W1: Read runtime/current_workspace.md and parse workspace_id.
Step W2: Build WORKSPACE_ROOT = workspaces/<workspace_id>/
Step W3: Verify WORKSPACE_ROOT exists.
Step W4: Read runtime/workspaces.md. Validate registry (R4a–R4e).
Step W5: All subsequent paths are prefixed with WORKSPACE_ROOT.
```

---

## Workspace Isolation

All write operations target `WORKSPACE_ROOT/output/deliverables/` only.

Source Markdown files in `WORKSPACE_ROOT/specifications/views/` are read-only.

Template files (`templates/html/`) are read-only. Theme CSS is created by `/configure-theme`.

---

## Preconditions

| ID | Condition | Action on failure |
|----|-----------|-------------------|
| P1 | Active workspace resolves (W1–W5, R4a–R4e) | BLOCKED |
| P2 | Pandoc installed (`pandoc --version` exits 0) | BLOCKED |
| P3 | `templates/html/base_template.html` exists | BLOCKED |
| P4 | `templates/html/base.css` exists | BLOCKED |
| P5 | At least one CSS theme file exists | BLOCKED |
| P6 | At least one source view file exists | BLOCKED |

---

## Failure Handling

| Condition | Behaviour |
|-----------|-----------|
| Pandoc not installed | BLOCKED — display install instructions; stop |
| HTML template or base CSS absent | BLOCKED — stop |
| No CSS theme found | BLOCKED — stop |
| All 6 source views absent | BLOCKED — run /generate-views first; stop |
| Some source views absent | PARTIAL — convert available; list missing |
| One conversion fails | EV-FAIL logged; continue with remaining views |
| mermaid.min.js absent | WARNING — diagrams won't render; export continues |
| Output directory cannot be created | BLOCKED — stop |

---

## Completion States

```text
STATUS: EXPORT-VIEWS COMPLETE   — all found views converted
STATUS: EXPORT-VIEWS PARTIAL    — at least 1 view converted; some BLOCKED_VIEW or FAILED
STATUS: EXPORT-VIEWS BLOCKED    — Pandoc absent, missing template, or no views at all
```
