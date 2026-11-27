#!/usr/bin/env python3
"""
B1 — PostToolUse hook: a real gate on specifications/stable/, not a narrated one.

CSR's contracts repeatedly say a baselined specification must satisfy certain
invariants (no BLOCKING open point, Statut vocabulary, a resolving TOC, ...).
Until this hook existed, "satisfies" meant "the model remembered to check" —
and on 2026-10-30 a narrated gate reported PASS on an artifact that violated it,
twice, independently (F-01, F-02 of the E2E run review). tools/csr-check exists
to make that detectable; this hook exists to make running it unconditional.

Trigger: any Write/Edit/MultiEdit whose target path is under
workspaces/<id>/specifications/stable/. Runs csr-check scoped to W-checks
(workspace artifacts) and reports ERROR findings that touch the SAME workspace
as the edited file. A finding in an unrelated workspace is not this edit's
fault and would just be noise on every unrelated baseline.

Exit 0, silent: clean, or the edit is out of scope.
Exit 2, stderr: at least one ERROR finding in the touched workspace. Per the
Claude Code hook contract, exit 2 feeds stderr back to the model as a tool
error — not merely a log line the model can choose to skip.
Exit 1: the checker itself failed to run (treated as non-blocking — a broken
hook must not become a silent, permanent block on every baseline).
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# The checker ships alongside this hook (tools/csr-check/, a sibling of
# hooks/ -- but hooks/'s OWN nesting depth differs between the two shapes
# this file runs in: <repo>/.claude/hooks/ (2 levels above the file) as a
# plain repo hook today, vs <plugin>/hooks/ (1 level above) once packaged.
# A single parents[N] cannot be correct for both depths at once, so the
# packaged form must use ${CLAUDE_PLUGIN_ROOT} (Claude Code's own name for
# "where this plugin is installed") rather than a fixed parent count; the
# non-plugin fallback needs parents[2] precisely because of the extra
# .claude/ layer. CLAUDE_PROJECT_DIR is the separate, correct name for the
# USER's own project root (where workspaces/ lives) in both shapes.
PACKAGE_ROOT = Path(os.environ["CLAUDE_PLUGIN_ROOT"]) if os.environ.get("CLAUDE_PLUGIN_ROOT") else Path(__file__).resolve().parents[2]
PROJECT_ROOT = Path(os.environ["CLAUDE_PROJECT_DIR"]) if os.environ.get("CLAUDE_PROJECT_DIR") else PACKAGE_ROOT
STABLE_RE = re.compile(r"workspaces/([^/]+)/specifications/stable/")


def normalize(path: str) -> str:
    """Hook payload paths may use the host OS separator; the checker and this
    hook both reason in forward slashes, so normalize once at the boundary."""
    return path.replace("\\", "/")


def touched_paths(tool_input: dict) -> list[str]:
    """Write/Edit carry file_path; MultiEdit same; be liberal, miss nothing."""
    paths = []
    for key in ("file_path",):
        if key in tool_input:
            paths.append(str(tool_input[key]))
    return paths


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # malformed input is not this hook's problem to enforce

    tool_name = payload.get("tool_name", "")
    if tool_name not in ("Write", "Edit", "MultiEdit"):
        return 0

    tool_input = payload.get("tool_input", {}) or {}
    workspace_ids = set()
    for p in touched_paths(tool_input):
        m = STABLE_RE.search(normalize(p))
        if m:
            workspace_ids.add(m.group(1))

    if not workspace_ids:
        return 0  # not a write under specifications/stable/ — out of B1's scope

    checker = PACKAGE_ROOT / "tools" / "csr-check" / "csr_check.py"
    if not checker.is_file():
        return 0  # checker absent (e.g. a packaged distribution) — nothing to run

    try:
        proc = subprocess.run(
            [sys.executable, str(checker), "--root", str(PROJECT_ROOT), "--format", "json"],
            capture_output=True, text=True, timeout=60,
        )
        report = json.loads(proc.stdout) if proc.stdout.strip() else {"findings": []}
    except Exception as exc:
        print(f"B1 hook: csr-check could not run ({exc}) — not blocking.", file=sys.stderr)
        return 1

    relevant = [
        f for f in report.get("findings", [])
        if f.get("severity") == "ERROR"
        and any(f"workspaces/{wid}/" in normalize(f.get("file", "")) for wid in workspace_ids)
    ]
    if not relevant:
        return 0

    lines = [
        f"B1 — csr-check found {len(relevant)} ERROR finding(s) in the workspace(s) "
        f"just written to ({', '.join(sorted(workspace_ids))}):",
        "",
    ]
    for f in relevant[:10]:
        loc = f"{f.get('file')}:{f.get('line')}" if f.get("line") else f.get("file", "")
        lines.append(f"  [{f.get('check')}] {loc} — {f.get('message')}")
    if len(relevant) > 10:
        lines.append(f"  ... and {len(relevant) - 10} more.")
    lines.append("")
    lines.append("This is a real gate, not a reminder: the write already happened, and this "
                  "is unconditional feedback rather than a narrated check. Run "
                  "`python tools/csr-check/csr_check.py` for full detail before treating this "
                  "baseline as final.")
    print("\n".join(lines), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
