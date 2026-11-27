# /configure-theme

## Purpose

Create or manage the CSS theme for the active workspace's HTML document output.

Operations:
- `EXTRACT <file_path>` — analyze a reference document → generate custom theme.css
- `COPY <source_workspace_id>` — copy theme from another workspace
- `RESET` — remove custom theme → revert to CSR default
- `STATUS` — show current theme configuration

The theme is applied automatically by `/export-views` when generating HTML deliverables.

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

Write operations target only:
- `workspaces/<workspace_id>/theme.css` (EXTRACT, COPY, RESET)
- `workspaces/<workspace_id>/runtime/workspace_config.md` (all write operations)

Source templates (`${CLAUDE_PLUGIN_ROOT}/templates/html/`) are read-only.

---

## Invocation

```text
/configure-theme EXTRACT <file_path>
/configure-theme COPY <source_workspace_id>
/configure-theme RESET
/configure-theme STATUS
```

---

## Execution

### Step 1 — Load Specification Layers

Read and assimilate:

```text
${CLAUDE_PLUGIN_ROOT}/docs/commands/configure-theme.md                     ← L1 contract
${CLAUDE_PLUGIN_ROOT}/docs/commands/configure-theme_execution.md           ← L2 execution spec
${CLAUDE_PLUGIN_ROOT}/templates/commands/configure_theme_prompt.md         ← L3 prompt (extraction guidance)
```

### Step 2 — Execute Theme Configuration Runtime

Execute the runtime defined in `${CLAUDE_PLUGIN_ROOT}/docs/commands/configure-theme_execution.md`:

1. Workspace resolution
2. Operation dispatch (EXTRACT / COPY / RESET / STATUS)
3. Per-operation phase (Phase 3, 4, 5, or 6)
4. theme.css write (EXTRACT and COPY operations)
5. workspace_config.md update
6. Completion report

For EXTRACT: always preview extracted values and ask for user confirmation before writing.

---

## Expected Output

```text
workspaces/<workspace_id>/theme.css                        ← created/deleted by EXTRACT/COPY/RESET
workspaces/<workspace_id>/runtime/workspace_config.md      ← updated (theme field)
```

---

## Completion States

```text
STATUS: CONFIGURE-THEME COMPLETE    — theme.css written
STATUS: CONFIGURE-THEME RESET       — custom theme removed
STATUS: CONFIGURE-THEME COPIED      — theme copied from <source>
STATUS: CONFIGURE-THEME BLOCKED     — precondition failed; no changes made
```

## LOGO `[A3, 2026-11-01]`

`/configure-theme LOGO <file_path>` registers a logo image for document cover pages; `/configure-theme LOGO NONE` clears it.

Writes `logo_path` in `workspaces/<workspace_id>/runtime/workspace_config.md` — the field `/generate-views` reads for the cover page, and which no operation could write before this one. The path is validated (file exists, image extension) and stored as given relative to the repository root; the file is not copied into the workspace.

See `${CLAUDE_PLUGIN_ROOT}/docs/commands/configure-theme_execution.md` Phase 7.
