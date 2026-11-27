#!/usr/bin/env python3
"""
csr-check — cross-layer consistency checker for the Cognitive Specification Runtime.

CSR's recurring defect is not wrong rules. It is rules that are true in one layer
and absent, stale or contradicted in another, with nothing able to notice. Every
check below was derived from a defect that actually reached a committed artifact,
and is named after the finding it would have caught.

Two families:

  S-checks  specification layer (docs/, .claude/commands/) — drift between the
            L1 contract, the L2 execution spec, the L3 prompt template, the L4
            command, and the ADRs they all cite.

  W-checks  workspace artifacts (workspaces/<id>/) — defects in what the runtime
            produced: conflicts that should have blocked, gates that recorded a
            verdict their own contract cannot produce, registries that contradict
            the document they live in.

Stdlib only. No configuration file: the checks read the repository as it is.

Usage:
    python tools/csr-check/csr_check.py [--root PATH] [--only S1,W3] [--format text|json]

Exit codes:
    0  no ERROR findings
    1  at least one ERROR finding
    2  the checker itself failed
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path

ERROR = "ERROR"
WARN = "WARN"


# --------------------------------------------------------------------------
# Finding model
# --------------------------------------------------------------------------

@dataclass
class Finding:
    check: str
    severity: str
    message: str
    file: str
    line: int = 0
    detail: str = ""

    def location(self) -> str:
        return f"{self.file}:{self.line}" if self.line else self.file


@dataclass
class Repo:
    """Lazily-read view of the repository, so each file is parsed at most once."""
    root: Path
    _cache: dict = field(default_factory=dict)

    def read(self, path: Path) -> str:
        key = str(path)
        if key not in self._cache:
            try:
                self._cache[key] = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                self._cache[key] = ""
        return self._cache[key]

    def lines(self, path: Path) -> list[str]:
        return self.read(path).splitlines()

    def rel(self, path: Path) -> str:
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return path.as_posix()

    def spec_docs(self) -> list[Path]:
        """Normative specification documents. Excludes analysis and workspaces."""
        out: list[Path] = []
        for sub in ("docs/commands", "docs/decisions", "docs/architecture", "docs/governance"):
            d = self.root / sub
            if d.is_dir():
                out.extend(sorted(p for p in d.rglob("*.md") if p.is_file()))
        cmds = self.root / ".claude" / "commands"
        if cmds.is_dir():
            out.extend(sorted(p for p in cmds.glob("*.md")))
        return out

    def workspaces(self) -> list[Path]:
        ws = self.root / "workspaces"
        if not ws.is_dir():
            return []
        return sorted(p for p in ws.iterdir() if p.is_dir())


# --------------------------------------------------------------------------
# Markdown helpers
# --------------------------------------------------------------------------

_SEPARATOR = re.compile(r"^\s*\|[\s:|-]+\|\s*$")


def table_rows(lines: list[str], start: int) -> list[tuple[int, list[str]]]:
    """Read a pipe table starting at or just after `start`. Returns (lineno, cells)."""
    rows: list[tuple[int, list[str]]] = []
    i = start
    seen_header = False
    while i < len(lines):
        raw = lines[i].strip()
        if not raw.startswith("|"):
            if rows or seen_header:
                break
            if raw == "" or raw.startswith(">") or raw.startswith("*"):
                i += 1
                continue
            break
        if _SEPARATOR.match(raw):
            seen_header = True
            i += 1
            continue
        cells = [c.strip() for c in raw.strip("|").split("|")]
        if not seen_header:
            seen_header = True  # header row
        else:
            rows.append((i + 1, cells))
        i += 1
    return rows


def find_heading(lines: list[str], *patterns: str) -> int:
    """Index of the first heading line matching any pattern (case-insensitive). -1 if none."""
    for idx, line in enumerate(lines):
        if not line.lstrip().startswith("#"):
            continue
        for pat in patterns:
            if re.search(pat, line, re.IGNORECASE):
                return idx
    return -1


def rows_after_heading(lines: list[str], *patterns: str) -> list[tuple[int, list[str]]]:
    idx = find_heading(lines, *patterns)
    if idx < 0:
        return []
    return table_rows(lines, idx + 1)


def table_with_header(lines: list[str], start: int) -> tuple[list[str], list[tuple[int, list[str]]]]:
    """Like `table_rows`, but also returns the header cells.

    ADR-007 widened Sections 7 and 11, and further columns are plausible. Any check
    reading those tables must locate its column by NAME, so it needs the header. A
    positional read drifts onto a neighbouring field the next time a column is added,
    and drifts silently — it still finds a value, just the wrong one.
    """
    header: list[str] = []
    i = start
    while i < len(lines):
        raw = lines[i].strip()
        if not raw.startswith("|"):
            if raw == "" or raw.startswith(">") or raw.startswith("*"):
                i += 1
                continue
            break
        if _SEPARATOR.match(raw):
            break
        header = [strip_md(c) for c in raw.strip("|").split("|")]
        break
    return header, table_rows(lines, start)


def column_index(header: list[str], *names: str) -> int:
    """Index of the first header cell matching one of `names`, or -1 if absent.

    -1 is a normal answer, not a failure: a specification baselined before the
    column existed simply does not have it.
    """
    wanted = {n.casefold() for n in names}
    for i, cell in enumerate(header):
        if cell.casefold() in wanted:
            return i
    return -1


def strip_md(text: str) -> str:
    """Remove bold/strikethrough/code markers so cell values compare cleanly.

    Underscores are deliberately preserved. CSR status vocabulary is built on
    them — PENDING_VALIDATION, USER_VALIDATED, ALL_RESOLVED, PROVENANCE_INDEXED —
    and stripping them as italic markers silently turns every status comparison
    into a mismatch. An earlier revision did exactly that, which disabled W3
    entirely while the check still reported success.
    """
    return re.sub(r"[*~`]", "", text).strip()


# --------------------------------------------------------------------------
# S-checks — specification layer
# --------------------------------------------------------------------------

# Principle families whose IDs are expected to form a contiguous, ordered sequence
# within the document that defines them.
PRINCIPLE_FAMILIES = ("CSR-E", "OAE", "OA", "PB", "PE", "PP", "RD", "GP")
_DEF_RE = re.compile(
    r"^\s*(?:#{2,6}\s*|\*\*)(?P<id>(?:" + "|".join(PRINCIPLE_FAMILIES) + r")-(?P<num>\d{1,3}))\s*(?:—|-|–|\*\*)"
)
_REF_RE = re.compile(r"\b(?P<id>(?:" + "|".join(PRINCIPLE_FAMILIES) + r")-\d{1,3})\b")


def collect_principle_definitions(repo: Repo) -> dict[str, list[tuple[Path, int]]]:
    defs: dict[str, list[tuple[Path, int]]] = defaultdict(list)
    for path in repo.spec_docs():
        for n, line in enumerate(repo.lines(path), start=1):
            m = _DEF_RE.match(line)
            if m:
                defs[m.group("id")].append((path, n))
    return defs


def check_s1_principle_sequence(repo: Repo) -> list[Finding]:
    """S1 — principle IDs are unique, contiguous and presented in ascending order.

    Derived from: while adding CSR-E-07/08 this session they were inserted before
    CSR-E-06, producing a numerically out-of-order principle list. Caught by eye.
    """
    findings: list[Finding] = []
    per_doc: dict[Path, list[tuple[str, str, int, int]]] = defaultdict(list)

    for path in repo.spec_docs():
        for n, line in enumerate(repo.lines(path), start=1):
            m = _DEF_RE.match(line)
            if m:
                pid = m.group("id")
                family = pid.rsplit("-", 1)[0]
                per_doc[path].append((family, pid, int(m.group("num")), n))

    for path, entries in per_doc.items():
        by_family: dict[str, list[tuple[str, int, int]]] = defaultdict(list)
        for family, pid, num, n in entries:
            by_family[family].append((pid, num, n))

        for family, items in by_family.items():
            if len(items) < 2:
                continue

            seen: dict[int, int] = {}
            for pid, num, n in items:
                if num in seen:
                    findings.append(Finding(
                        "S1", ERROR,
                        f"{pid} is defined twice in the same document",
                        repo.rel(path), n,
                        f"first definition at line {seen[num]}",
                    ))
                else:
                    seen[num] = n

            numbers = [num for _, num, _ in items]
            if numbers != sorted(numbers):
                out_of_order = [
                    f"{pid} (line {n})"
                    for (pid, num, n), nxt in zip(items, items[1:])
                    if num > nxt[1]
                ]
                findings.append(Finding(
                    "S1", WARN,
                    f"{family} principles are not in ascending order",
                    repo.rel(path), items[0][2],
                    "out of order after: " + ", ".join(out_of_order),
                ))

            uniq = sorted(set(numbers))
            gaps = [k for k in range(uniq[0], uniq[-1]) if k not in set(uniq)]
            if gaps:
                findings.append(Finding(
                    "S1", WARN,
                    f"{family} sequence has gaps: " + ", ".join(f"{family}-{g:02d}" for g in gaps),
                    repo.rel(path), items[0][2],
                    f"defined range {family}-{uniq[0]:02d}..{family}-{uniq[-1]:02d}",
                ))

    return findings


def check_s2_dangling_principle_refs(repo: Repo) -> list[Finding]:
    """S2 — every principle ID cited anywhere resolves to a definition.

    Derived from: a reference surviving a renumbering is exactly how a layer
    starts describing a rule that no longer exists.
    """
    defined = set(collect_principle_definitions(repo))
    if not defined:
        return []

    # Only police families that are actually defined somewhere, so an unrelated
    # token shaped like "PP-01" in a workspace policy does not raise noise.
    live_families = {pid.rsplit("-", 1)[0] for pid in defined}
    findings: list[Finding] = []
    reported: set[tuple[str, str]] = set()

    for path in repo.spec_docs():
        for n, line in enumerate(repo.lines(path), start=1):
            for m in _REF_RE.finditer(line):
                pid = m.group("id")
                family = pid.rsplit("-", 1)[0]
                if family not in live_families or pid in defined:
                    continue
                key = (repo.rel(path), pid)
                if key in reported:
                    continue
                reported.add(key)
                findings.append(Finding(
                    "S2", WARN,
                    f"{pid} is referenced but never defined",
                    repo.rel(path), n,
                    line.strip()[:160],
                ))
    return findings


_GLOSS_RE = re.compile(
    r"^\s*(?P<path>(?:docs|templates|runtime|\.claude)/[\w./-]+\.md)\s+(?:—|–|-{1,2})\s+(?P<gloss>.+?)\s*$"
)


def check_s3_reference_gloss_drift(repo: Repo) -> list[Finding]:
    """S3 — an ADR is glossed the same way in every reference block that cites it.

    Derived from the language drift: seven reference footers glossed ADR-001 as
    "language policy (English only)". A reader trusting that one-liner concludes
    the opposite of what the ADR says — which is how an entire analysis pass came
    to be written in the wrong language and then retranslated.

    Deliberately scoped to `docs/decisions/` only. An earlier revision checked
    every referenced document and produced 29 findings, essentially all of them
    harmless phrasing variation ("M12 Layer 1 Contract" vs "M12 Governance Runtime
    Contract"). That is alarm fatigue, and alarm fatigue is how the defects this
    tool exists to catch survived in the first place. An ADR is different in kind:
    it records a decision, and a one-line summary that contradicts that decision
    actively misleads, because readers trust the gloss instead of opening the file.
    """
    glosses: dict[str, dict[str, list[tuple[str, int]]]] = defaultdict(lambda: defaultdict(list))

    for path in repo.spec_docs():
        for n, line in enumerate(repo.lines(path), start=1):
            m = _GLOSS_RE.match(line)
            if not m:
                continue
            target = m.group("path")
            if not target.startswith("docs/decisions/"):
                continue
            gloss = strip_md(m.group("gloss"))
            if len(gloss) < 4:
                continue
            glosses[target][gloss].append((repo.rel(path), n))

    findings: list[Finding] = []
    for target, variants in sorted(glosses.items()):
        if len(variants) < 2:
            continue
        ranked = sorted(variants.items(), key=lambda kv: (-len(kv[1]), kv[0]))
        majority, majority_sites = ranked[0]
        for gloss, sites in ranked[1:]:
            for rel, n in sites:
                findings.append(Finding(
                    "S3", WARN,
                    f"inconsistent one-line description of {target}",
                    rel, n,
                    f'here: "{gloss}" | used by {len(majority_sites)} other file(s): "{majority}"',
                ))
    return findings


def check_s4_broken_doc_references(repo: Repo) -> list[Finding]:
    """S4 — a repository path cited in a reference block exists on disk."""
    findings: list[Finding] = []
    reported: set[tuple[str, str]] = set()

    for path in repo.spec_docs():
        for n, line in enumerate(repo.lines(path), start=1):
            m = _GLOSS_RE.match(line)
            if not m:
                continue
            target = m.group("path")
            if (repo.root / target).exists():
                continue
            key = (repo.rel(path), target)
            if key in reported:
                continue
            reported.add(key)
            findings.append(Finding(
                "S4", ERROR,
                f"referenced file does not exist: {target}",
                repo.rel(path), n,
            ))
    return findings


# SQF indicator algorithms that are written out in more than one layer. Each entry
# names a rule that must appear in every copy; if one copy is edited and the others
# are not, the gate silently computes two different numbers depending on who ran it.
#
# This is R8's real hazard, stated in the chantier register as "algorithme dupliqué —
# à patcher deux fois, comme I1.3". Patching twice works exactly once; what fails is
# the third edit, months later, by someone who does not know the second copy exists.
_DUPLICATED_SQF_RULES = (
    ("I3.1/I3.3 OP-NNN denominator exclusion (R8)",
     r"OP-\\?d|OP-NNN",
     ("templates/sqf_gate_report_template.md",
      "docs/commands/generate-specification_execution.md")),
    ("I1.3 open-point verdict vocabulary",
     r"ALL_RESOLVED",
     ("templates/sqf_gate_report_template.md",
      "docs/commands/generate-specification_execution.md")),
    ("Ambiguity detection signal list (E5 unqualified bounds)",
     r"[Uu]nqualified bounds",
     ("docs/commands/detect-conflicts_execution.md",
      "templates/commands/detect_conflicts_prompt.md")),
)


def check_s5_duplicated_sqf_algorithms(repo: Repo) -> list[Finding]:
    """S5 — an SQF rule written in two layers is present in one and missing from the other.

    The SQF gate's indicator algorithms are spelled out twice: once in the gate report
    template that defines them, once in the execution spec that runs them. Nothing ties
    the two copies together, so an edit to one leaves the other computing a different
    number — and the report still looks authoritative.

    The check is deliberately coarse: it asserts that a rule marker present in any copy
    is present in all of them. It cannot tell whether two copies say the same thing, only
    whether one of them has stopped mentioning the rule at all. That is the drift that
    actually happened with I1.3 and would have happened again with R8.
    """
    findings: list[Finding] = []

    for label, pattern, paths in _DUPLICATED_SQF_RULES:
        present, absent = [], []
        for rel in paths:
            path = repo.root / rel
            if not path.is_file():
                continue
            (present if re.search(pattern, repo.read(path)) else absent).append(rel)
        if present and absent:
            for rel in absent:
                findings.append(Finding(
                    "S5", ERROR,
                    f"{label} is missing from this copy of a duplicated algorithm",
                    rel, 0,
                    "present in: " + ", ".join(present)
                    + " · both copies define the same indicator; one has drifted",
                ))
    return findings


# L1 contracts and L2 execution specs both live in docs/commands/. The convention
# is <base>.md (L1) paired with <base>_execution.md (L2) -- underscore, always.
_L1_EXCLUDE_SUFFIXES = ("_execution.md", "-execution.md", "-prompt-template.md")


def check_s6_l1_l2_layer_pairing(repo: Repo) -> list[Finding]:
    """S6 — every L1 contract has a paired L2 execution spec, and vice versa.

    Both live in docs/commands/ under one naming convention: <base>.md paired
    with <base>_execution.md. A command whose L2 file does not follow that exact
    convention is functionally invisible to anything that looks it up
    mechanically -- including this checker's own siblings, and any future
    automation over "the L2 for command X". operating-agent-execution.md (a
    hyphen before "execution", where every one of its 23 siblings uses an
    underscore) is exactly that: content-complete, present on disk, and still an
    orphan by the convention every other pairing follows.
    """
    findings: list[Finding] = []
    cmd_dir = repo.root / "docs" / "commands"
    if not cmd_dir.is_dir():
        return findings

    all_md = sorted(p.name for p in cmd_dir.glob("*.md"))
    l1_bases = {
        name[:-3] for name in all_md
        if not any(name.endswith(suf) for suf in _L1_EXCLUDE_SUFFIXES)
    }
    l2_bases = {
        name[: -len("_execution.md")] for name in all_md
        if name.endswith("_execution.md")
    }
    # Anything ending in "-execution.md" (hyphen) or any other execution-ish
    # spelling that is NOT "_execution.md" is a naming-convention orphan by
    # construction, whichever base it was meant to pair with.
    non_conforming_exec = sorted(
        name for name in all_md
        if name.endswith("-execution.md")
    )

    for base in sorted(l1_bases - l2_bases):
        findings.append(Finding(
            "S6", ERROR,
            f"L1 contract '{base}.md' has no paired L2 execution spec '{base}_execution.md'",
            f"docs/commands/{base}.md", 0,
            "no file of that exact name exists in docs/commands/",
        ))
    for base in sorted(l2_bases - l1_bases):
        findings.append(Finding(
            "S6", ERROR,
            f"L2 execution spec '{base}_execution.md' has no paired L1 contract '{base}.md'",
            f"docs/commands/{base}_execution.md", 0,
            "no file of that exact name exists in docs/commands/",
        ))
    for name in non_conforming_exec:
        findings.append(Finding(
            "S6", ERROR,
            f"'{name}' does not follow the '<base>_execution.md' naming convention (hyphen before \"execution\", not underscore)",
            f"docs/commands/{name}", 0,
            "every other L2 file in this directory uses an underscore; a mechanical "
            "lookup for '<base>_execution.md' will not find this file",
        ))
    return findings


# A literal "CSR vX.Y.Z" baked into a generation contract or the template it
# drives. CSR's own convention — CURRENT_RUNTIME_VERSION / {{CSR_VERSION}},
# resolved from docs/implementation_status.md at run time — exists precisely
# to avoid this. A literal version string in one of these files is frozen at
# whatever CSR's version was on the day it was written, and every artifact
# generated afterward silently misreports which version produced it.
_HARDCODED_CSR_VERSION_RE = re.compile(r"CSR\s+v\d+\.\d+\.\d+")
_VERSION_SCOPED_PATHS = (
    "templates/spec_canonical_v1.md",
    "docs/commands/generate-specification_execution.md",
)


def check_s8_hardcoded_csr_version(repo: Repo) -> list[Finding]:
    """S8 — a generation artifact names a frozen CSR version instead of the
    CURRENT_RUNTIME_VERSION placeholder.

    Found live: templates/spec_canonical_v1.md and the L2 instruction that
    actually emits its header line both said "CSR v2.0.0" — the version CSR
    carried on 2026-07-01, the day the template was written. By the time this
    check was added CSR was at 2.8.3, and every specification generated across
    those eight months and dozens of releases had carried the same stale
    marker. The runtime defines CURRENT_RUNTIME_VERSION precisely so this class
    of drift cannot happen; this file simply was not using its own mechanism.
    """
    findings: list[Finding] = []
    for rel in _VERSION_SCOPED_PATHS:
        path = repo.root / rel
        if not path.is_file():
            continue
        for n, line in enumerate(repo.lines(path), 1):
            m = _HARDCODED_CSR_VERSION_RE.search(line)
            if not m:
                continue
            findings.append(Finding(
                "S8", ERROR,
                f"hardcoded version '{m.group(0)}' where CURRENT_RUNTIME_VERSION is the convention",
                rel, n,
                "this file is a generation source; a literal version string freezes "
                "at whatever CSR was on the day it was written, and every artifact "
                "generated afterward silently misreports which version produced it",
            ))
    return findings


# --------------------------------------------------------------------------
# W-checks — workspace artifacts
# --------------------------------------------------------------------------

def _specs(ws: Path) -> list[Path]:
    out: list[Path] = []
    for sub in ("specifications/draft", "specifications/stable"):
        d = ws / sub
        if d.is_dir():
            out.extend(sorted(p for p in d.glob("*_specification*.md")))
    return out


def _open_points(repo: Repo, spec: Path) -> list[tuple[int, list[str]]]:
    """Rows of Section 13 (Open Points / Points Ouverts) whose Status is OPEN."""
    lines = repo.lines(spec)
    rows = rows_after_heading(lines, r"Section\s*13\b", r"Open Points", r"Points Ouverts")
    found = []
    for n, cells in rows:
        if not cells or not re.match(r"^OP-\d+$", strip_md(cells[0])):
            continue
        if any(strip_md(c).upper() == "OPEN" for c in cells):
            found.append((n, [strip_md(c) for c in cells]))
    return found


def check_w1_blocking_conflict_not_consolidated(repo: Repo) -> list[Finding]:
    """W1 — a BLOCKING conflict was never consolidated, yet specifications exist.

    Derived from F-01. /generate-specification builds its eligibility index from
    the "Conflict Resolution Records" section alone, so a BLOCKING conflict that
    /consolidate-knowledge parked under "Ineligible Conflicts" is invisible to the
    gate meant to stop it. C006 reached a BASELINED specification this way.
    """
    findings: list[Finding] = []

    for ws in repo.workspaces():
        conflicts = ws / "knowledge_base" / "conflicts" / "conflicts_report.md"
        consolidation = ws / "knowledge_base" / "consolidated" / "consolidation_report.md"
        if not conflicts.is_file() or not consolidation.is_file():
            continue
        if not _specs(ws):
            continue

        blocking: dict[str, int] = {}
        for n, cells in rows_after_heading(repo.lines(conflicts), r"^##\s*Summary"):
            if len(cells) < 3:
                continue
            cid = strip_md(cells[0])
            if re.match(r"^C\d+$", cid) and strip_md(cells[2]).upper() == "BLOCKING":
                blocking[cid] = n

        consolidated: set[str] = set()
        ctext = repo.read(consolidation)
        for m in re.finditer(
            r"\*\*Conflict ID:\*\*\s*(C\d+)[\s\S]{0,400}?\*\*Status:\*\*\s*(\w+)", ctext
        ):
            if m.group(2).upper() == "CONSOLIDATED":
                consolidated.add(m.group(1))

        for cid, n in sorted(blocking.items()):
            if cid in consolidated:
                continue
            findings.append(Finding(
                "W1", ERROR,
                f"{cid} is BLOCKING and was never consolidated, but this project has specifications",
                repo.rel(conflicts), n,
                f"no CONSOLIDATED resolution record for {cid} in "
                f"{repo.rel(consolidation)}; the eligibility gate of /generate-specification "
                f"cannot see conflicts outside '## Conflict Resolution Records'",
            ))
    return findings


def _i13_claims_all_resolved(line: str) -> bool:
    """True when a line records I1.3's *value* as ALL_RESOLVED.

    The threshold legend of the same table row reads `ALL_RESOLVED=PASS`, so a
    gate report that correctly recorded DEFERRED still contains the string
    ALL_RESOLVED. Matching the raw line therefore flags correct reports as
    defective — which is what an earlier revision did. Read the value, not the row.
    """
    if "I1.3" not in line:
        return False

    stripped = line.strip()
    if stripped.startswith("|"):
        cells = [strip_md(c) for c in stripped.strip("|").split("|")]
        if len(cells) < 2 or "I1.3" not in cells[0]:
            return False
        return cells[1].upper().startswith("ALL_RESOLVED")

    # Prose form, e.g. "D1: PASS (I1.1 = 123%, I1.2 = PRESENT_WITH_ENTRIES, I1.3 = ALL_RESOLVED)"
    m = re.search(r"I1\.3\s*(?:=|:)?\s*([A-Z_]+)", strip_md(line))
    return bool(m and m.group(1).startswith("ALL_RESOLVED"))


def check_w2_open_points_vs_sqf_gate(repo: Repo) -> list[Finding]:
    """W2 — a gate report claims all open points resolved while open points are OPEN.

    Derived from F-02. The SQF contract can produce ALL_RESOLVED, DEFERRED or
    UNRESOLVED for I1.3; with rows at Status OPEN it cannot produce the first.
    Both baselined specifications of the 2026-10-30 run recorded ALL_RESOLVED.
    """
    findings: list[Finding] = []

    for ws in repo.workspaces():
        # A specification exists as an EN original and an FR companion carrying the
        # same open points. Count the specification once, not once per language.
        by_base: dict[str, int] = {}
        for spec in _specs(ws):
            count = len(_open_points(repo, spec))
            if not count:
                continue
            base = re.sub(r"_(en|fr)$", "", spec.stem, flags=re.IGNORECASE)
            by_base[base] = max(by_base.get(base, 0), count)
        if not by_base:
            continue

        summary = ", ".join(f"{b} ({c} OPEN)" for b, c in sorted(by_base.items()))

        for report in sorted(ws.rglob("sqf_gate_report.md")):
            hits = [
                n for n, line in enumerate(repo.lines(report), start=1)
                if _i13_claims_all_resolved(line)
            ]
            if not hits:
                continue
            extra = f" (and {len(hits) - 1} further occurrence(s) in this file)" if len(hits) > 1 else ""
            findings.append(Finding(
                "W2", ERROR,
                "I1.3 recorded as ALL_RESOLVED while open points are still OPEN",
                repo.rel(report), hits[0],
                f"unresolved open points in {len(by_base)} specification(s): {summary}{extra}. "
                f"Per the SQF contract the verdict must be DEFERRED (WARN) or "
                f"UNRESOLVED (BLOCK), never ALL_RESOLVED",
            ))
    return findings


def check_w3_inference_registry_vs_body(repo: Repo) -> list[Finding]:
    """W3 — an element is PENDING_VALIDATION in Annexe A but resolved in the body.

    Derived from F-10. Human validation does not propagate to the Inference
    Registry, so one artifact can assert both "Validated and implemented" in its
    body and PENDING_VALIDATION in its annex for the same element.
    """
    findings: list[Finding] = []

    for ws in repo.workspaces():
        for spec in _specs(ws):
            lines = repo.lines(spec)
            idx = find_heading(lines, r"INFERRED_DESIGN\s*—\s*Impact Structurel")
            if idx < 0:
                continue
            text = repo.read(spec)
            for n, cells in table_rows(lines, idx + 1):
                if len(cells) < 3:
                    continue
                element = strip_md(cells[0])
                status = strip_md(cells[2]).upper()
                if status != "PENDING_VALIDATION" or not re.match(r"^[A-Z]{1,4}-\d+$", element):
                    continue
                pattern = re.compile(
                    r"^\|\s*" + re.escape(element) + r"\s*\|[\s\S]{0,4000}?\*\*Resolution\s*\(",
                    re.MULTILINE,
                )
                if pattern.search(text):
                    findings.append(Finding(
                        "W3", ERROR,
                        f"{element} is PENDING_VALIDATION in the Inference Registry "
                        f"but carries a Resolution in the specification body",
                        repo.rel(spec), n,
                        "the same artifact asserts the element is both settled and awaiting validation",
                    ))
    return findings


def check_w4_baseline_carries_blocking_open_point(repo: Repo) -> list[Finding]:
    """W4 — a BASELINED specification carries an open point of BLOCKING severity.

    Derived from F-01's consequence. This is the state W1 and W2 let through:
    a specification adopted as the official reference while a BLOCKING ambiguity
    on a pivotal business term is still unresolved inside it.
    """
    findings: list[Finding] = []

    for ws in repo.workspaces():
        stable = ws / "specifications" / "stable"
        if not stable.is_dir():
            continue
        for spec in sorted(stable.glob("*_specification*.md")):
            for n, cells in _open_points(repo, spec):
                if any(c.upper() == "BLOCKING" for c in cells):
                    findings.append(Finding(
                        "W4", ERROR,
                        f"baselined specification carries BLOCKING open point {cells[0]}",
                        repo.rel(spec), n,
                        (cells[1][:200] + "…") if len(cells) > 1 and len(cells[1]) > 200
                        else (cells[1] if len(cells) > 1 else ""),
                    ))
    return findings


# Sections carrying an ADR-007 proof state, with the headings that locate them.
_PROOF_SECTIONS = (
    (r"Section\s*7\b", r"Acceptance Criteria", r"Crit[eè]res d.acceptation"),
    (r"Section\s*11\b", r"Exigences Non-Fonctionnelles", r"Non-Functional"),
)

# Accent-tolerant: the canonical writes INFIRMÉ, but a hand edit may drop the accent,
# and a finding must not hinge on that.
_DISPROVED = {"INFIRMÉ", "INFIRME"}


def check_w5_baseline_carries_disproved_criterion(repo: Repo) -> list[Finding]:
    """W5 — a BASELINED specification carries a criterion recorded as INFIRMÉ.

    ADR-007 Engagement #4. A criterion demonstrated false, inside the document
    adopted as the official reference, is a contradiction between the specification
    and the system that was built. No baseline gate can catch it: the test that
    disproves a criterion is normally run long after BASELINE, which is precisely
    why ADR-007 routes it here instead of to an eligibility condition.

    NON_DÉMONTRÉ is deliberately NOT a finding, and must never become one. It is the
    expected state of a freshly baselined specification — the system it describes
    does not exist yet. Reporting it would flag every correct specification and
    train the reader to ignore this check.
    """
    findings: list[Finding] = []

    for ws in repo.workspaces():
        stable = ws / "specifications" / "stable"
        if not stable.is_dir():
            continue
        for spec in sorted(stable.glob("*_specification*.md")):
            lines = repo.lines(spec)
            for patterns in _PROOF_SECTIONS:
                idx = find_heading(lines, *patterns)
                if idx < 0:
                    continue
                header, rows = table_with_header(lines, idx + 1)
                col = column_index(header, "Preuve", "Proof")
                if col < 0:
                    continue  # baselined before ADR-007 — reads as NON_DÉMONTRÉ
                for n, cells in rows:
                    if col >= len(cells):
                        continue
                    if strip_md(cells[col]).upper() not in _DISPROVED:
                        continue
                    element = strip_md(cells[0]) if cells else "?"
                    scope_col = column_index(header, "Démontré en", "Demontre en")
                    scope = (
                        strip_md(cells[scope_col])
                        if 0 <= scope_col < len(cells)
                        else ""
                    )
                    findings.append(Finding(
                        "W5", ERROR,
                        f"baselined specification records {element} as INFIRMÉ",
                        repo.rel(spec), n,
                        "an execution showed the system does not satisfy a criterion the "
                        "baselined specification still asserts"
                        + (f" · observed in: {scope}" if scope and scope != "—" else ""),
                    ))
    return findings


# Per-section vocabulary for the provenance / lifecycle column of a STD specification.
# Sections 5.1, 5.2, 6 and 11 carry a LIFECYCLE value; Section 7 carries a PROVENANCE
# value. The two were both named "Statut" until 2026-11-01, and that single overload
# produced two opposite drifts in two real workspaces: std-real-01 renamed the header
# to "Source" (following the values), demo-catalog-01 kept the header and wrote DRAFT
# (following the L3 prompt). Section 7's column is now named Source; the old spellings
# remain readable so baselined specifications are not invalidated.
_LIFECYCLE_VALUES = {"ACTIF", "ACTIVE", "DEPRECATED", "SUPERSEDED"}
_PROVENANCE_VALUES = {"SF", "UV", "DK", "TS", "US", "ID", "ID:STRUCTURAL", "ID:IMPLEMENTATION"}

_ELEMENT_SECTIONS = (
    # (id prefix, heading patterns, column names, allowed values, what the column means)
    ("AC", (r"Section\s*7\b", r"Acceptance Criteria"),
     ("Source", "Statut", "Status"), _PROVENANCE_VALUES, "KPM provenance (ADR-004)"),
    ("NFR", (r"Section\s*11\b", r"Exigences Non-Fonctionnelles", r"Non-Functional"),
     ("Statut", "Status"), _LIFECYCLE_VALUES, "lifecycle state"),
)


def check_w6_element_status_vocabulary(repo: Repo) -> list[Finding]:
    """W6 — an element carries a value outside its section's vocabulary.

    A DRAFT in an acceptance criterion is not cosmetic. That column is the carrier of
    US, and US blocks BASELINE; a generation that never emits US makes the rule
    "chaque FR ACTIF doit avoir au moins 1 AC non-US" pass vacuously and renders the
    gate unreachable. The defect is a value, not a layer, so the check reads the
    artifact rather than the contracts — whichever layer caused the drift, the wrong
    value lands here.

    Draft specifications are checked too: the point is to catch the drift at the run
    that produced it, not after it has been baselined.
    """
    findings: list[Finding] = []

    for ws in repo.workspaces():
        specs = ws / "specifications"
        if not specs.is_dir():
            continue
        for spec in sorted(specs.glob("*/*_specification*.md")):
            lines = repo.lines(spec)
            for prefix, patterns, col_names, allowed, meaning in _ELEMENT_SECTIONS:
                idx = find_heading(lines, *patterns)
                if idx < 0:
                    continue
                header, rows = table_with_header(lines, idx + 1)
                # A table without Given/When/Then is not the STD Section 7 — EVOLVE
                # certification fixtures carry a different, hand-authored shape.
                if prefix == "AC" and column_index(header, "Given") < 0:
                    continue
                col = column_index(header, *col_names)
                if col < 0:
                    continue
                seen: set[str] = set()
                for n, cells in rows:
                    if col >= len(cells) or not cells:
                        continue
                    ident = strip_md(cells[0])
                    if not re.match(rf"^{prefix}-\d+$", ident):
                        continue
                    value = strip_md(cells[col]).upper()
                    if not value or value == "—" or value in allowed or value in seen:
                        continue
                    seen.add(value)
                    findings.append(Finding(
                        "W6", ERROR,
                        f"{prefix} column holds '{strip_md(cells[col])}', outside the {meaning} vocabulary",
                        repo.rel(spec), n,
                        f"first seen on {ident}; expected one of {', '.join(sorted(allowed))}",
                    ))
    return findings


# Human-facing view types. The L2 contract gives each one a mandatory TOC section
# (SF-02, DAT-02, STD-02, QA-02). view_agent is absent on purpose: it is consumed by
# an agent, not read, and has no table of contents by design.
_HUMAN_VIEW_SUFFIXES = (
    "_specification_fonctionnelle", "_functional_specification",
    "_dossier_architecture", "_technical_architecture",
    "_specification_technique", "_technical_specification",
    "_plan_tests", "_test_plan",
)

_TOC_BLOCK_RE = re.compile(r'<div class="toc">.*?</div>', re.S)
_TOC_LINK_RE = re.compile(r'href="#([^"]+)"')
_ANCHOR_RE = re.compile(r"\{#([^}]+)\}")


def check_w7_view_table_of_contents(repo: Repo) -> list[Finding]:
    """W7 — a human-facing view is missing its mandated TOC, or links into thin air.

    The L2 contract gives every human view a TOC section, and generation omits it
    silently: std-synth-01 has none on any of its four views, and in std-real-01
    one view of four lacks it while its siblings — produced in the same run — have
    it. Same contract, same command, different output. Nothing noticed.

    The dead-anchor half guards a failure mode that has not occurred yet but is
    built into the design: the TOC in the source is a literal block copied from the
    L3 prompt, listing the sections the contract expects rather than the ones
    actually emitted. The first time a conditional section is omitted, its entry
    becomes a dead link.
    """
    findings: list[Finding] = []

    for ws in repo.workspaces():
        views = ws / "specifications" / "views"
        if not views.is_dir():
            continue
        for view in sorted(views.glob("*.md")):
            stem = view.stem
            if not any(s in stem for s in _HUMAN_VIEW_SUFFIXES):
                continue
            text = repo.read(view)
            block = _TOC_BLOCK_RE.search(text)
            if not block:
                findings.append(Finding(
                    "W7", ERROR,
                    "human-facing view has no table of contents",
                    repo.rel(view), 0,
                    "the L2 contract gives this view type a mandatory TOC section; "
                    "the exported HTML rebuilds one when a container exists, but here "
                    "the container itself is absent",
                ))
                continue
            links = set(_TOC_LINK_RE.findall(block.group(0)))
            anchors = set(_ANCHOR_RE.findall(text))
            dead = sorted(links - anchors)
            if dead:
                line = text[:block.start()].count("\n") + 1
                findings.append(Finding(
                    "W7", ERROR,
                    f"table of contents links to {len(dead)} anchor(s) that do not exist",
                    repo.rel(view), line,
                    "dead: " + ", ".join("#" + d for d in dead[:6])
                    + (" …" if len(dead) > 6 else ""),
                ))
    return findings


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# S9 / W8 — workspace registry schema and spec_template_version  [issue #55]
# --------------------------------------------------------------------------

_LIFECYCLE_L2 = "docs/commands/workspace-lifecycle_execution.md"
_LIFECYCLE_L3 = "templates/prompts/workspace-lifecycle_prompt.md"
_CSR_INIT = "tools/csr-init/csr-init.ps1"
_GENSPEC_L2 = "docs/commands/generate-specification_execution.md"
SPEC_TEMPLATE_VALUES = ("v1", "legacy")


def _registry_header(lines: list[str], start: int) -> tuple[int, list[str]]:
    """First '| workspace_id |' header line at or after `start` (lineno, cells)."""
    for i in range(max(start, 0), len(lines)):
        raw = lines[i].strip()
        if raw.startswith("| workspace_id |"):
            return i + 1, [strip_md(c) for c in raw.strip("|").split("|")]
    return 0, []


def _first_table(lines: list[str], start: int, window: int = 25) -> int:
    """Index of the first pipe-table line within `window` lines after `start`
    (prose usually sits between a step heading and its table). -1 if none."""
    for i in range(max(start, 0), min(len(lines), start + window)):
        if lines[i].strip().startswith("|"):
            return i
    return -1


def _writer_rows(lines: list[str], start: int) -> dict[str, tuple[int, str]]:
    """Field -> (lineno, value) for the `| Field | Value |` table at/after `start`."""
    out: dict[str, tuple[int, str]] = {}
    first = _first_table(lines, start)
    if first < 0:
        return out
    for n, cells in table_rows(lines, first):
        if len(cells) >= 2:
            out[strip_md(cells[0])] = (n, cells[1])
    return out


def check_s9_registry_schema(repo: Repo) -> list[Finding]:
    """S9 — every place that writes a workspace registry row names the same
    columns, and declares spec_template_version explicitly.

    Found live (issue #54 review): the registry header written by Step 0.1a
    and by csr-init.ps1 had 7 columns, but CREATE Step 1.8 and V2 Step 15.10
    listed only 6 fields. spec_template_version was left empty on every new
    project, /generate-specification Step 1.5.1 read empty as its LEGACY
    fallback, and every project created since STD v1 (mandatory for new
    workspaces, STD design section 9.4) silently generated LEGACY. Each layer
    was internally coherent; only the comparison between them showed the gap.

    Also guards the other direction: the documented empty/absent -> LEGACY
    fallback of Step 1.5.1 must stay, or every registry row written before the
    fix becomes unroutable.
    """
    findings: list[Finding] = []
    l2 = repo.root / _LIFECYCLE_L2
    if not l2.is_file():
        return findings
    l2_lines = repo.lines(l2)

    anchor = find_heading(l2_lines, r"Step 0\.1a")
    hdr_line, canonical = _registry_header(l2_lines, anchor if anchor >= 0 else 0)
    if not canonical:
        findings.append(Finding(
            "S9", ERROR, "canonical registry header not found in Step 0.1a",
            _LIFECYCLE_L2, 0,
            "every other registry writer is compared against this header",
        ))
        return findings

    writers = [
        (_LIFECYCLE_L2, l2_lines, find_heading(l2_lines, r"Step 1\.8\b"), "v1", "CREATE Step 1.8"),
        (_LIFECYCLE_L2, l2_lines, find_heading(l2_lines, r"Step 15\.10\b"), "legacy", "V2 Step 15.10"),
    ]
    l3 = repo.root / _LIFECYCLE_L3
    if l3.is_file():
        l3_lines = repo.lines(l3)
        start = next((i for i, l in enumerate(l3_lines)
                      if "Write a new row to `runtime/workspaces.md`" in l), -1)
        writers.append((_LIFECYCLE_L3, l3_lines, start, "v1", "L3 CREATE registry row"))

    for rel, lines, start, expected, label in writers:
        if start < 0:
            findings.append(Finding(
                "S9", ERROR, f"{label}: registry write table not found", rel, 0,
                "the step that writes the row could not be located",
            ))
            continue
        fields = _writer_rows(lines, start + 1)
        for col in canonical:
            if col not in fields:
                findings.append(Finding(
                    "S9", ERROR,
                    f"{label} does not write registry column '{col}'",
                    rel, start + 1,
                    f"the registry header ({_LIFECYCLE_L2}:{hdr_line}) has it; a row "
                    "written without it leaves the cell empty"
                    + ("; /generate-specification then falls back to LEGACY"
                       if col == "spec_template_version" else ""),
                ))
        if "spec_template_version" in fields:
            n, value = fields["spec_template_version"]
            if not re.search(rf"\b{re.escape(expected)}\b", strip_md(value)):
                findings.append(Finding(
                    "S9", ERROR,
                    f"{label} must write spec_template_version '{expected}'",
                    rel, n, f"found: {strip_md(value)[:80]!r}",
                ))

    init = repo.root / _CSR_INIT
    if init.is_file():
        init_lines = repo.lines(init)
        n, cols = 0, []
        for i, line in enumerate(init_lines):
            pos = line.find("| workspace_id |")
            if pos >= 0:
                seg = line[pos: line.rfind("|") + 1]
                n, cols = i + 1, [strip_md(c) for c in seg.strip("|").split("|")]
                break
        if not cols:
            findings.append(Finding(
                "S9", ERROR, "csr-init.ps1 registry header not found", _CSR_INIT, 0,
                "the script that initialises a fresh folder must write the Step 0.1a header",
            ))
        elif cols != canonical:
            findings.append(Finding(
                "S9", ERROR, "csr-init.ps1 registry header differs from Step 0.1a",
                _CSR_INIT, n, f"csr-init: {cols} / Step 0.1a: {canonical}",
            ))

    gs = repo.root / _GENSPEC_L2
    if gs.is_file():
        gs_lines = repo.lines(gs)
        h = find_heading(gs_lines, r"Step 1\.5\.1")
        first = _first_table(gs_lines, h + 1) if h >= 0 else -1
        rows = table_rows(gs_lines, first) if first >= 0 else []
        mapping = {strip_md(c[0]).lower(): strip_md(c[1]).upper() for _, c in rows if len(c) >= 2}
        expectations = (("v1", "STD"), ("legacy", "LEGACY"))
        for value, mode in expectations:
            if mapping.get(value) != mode:
                findings.append(Finding(
                    "S9", ERROR,
                    f"Step 1.5.1 does not route '{value}' to {mode}",
                    _GENSPEC_L2, 0, f"routing table read: {mapping}",
                ))
        fallback = [m for k, m in mapping.items() if "absent" in k or "empty" in k]
        if fallback != ["LEGACY"]:
            findings.append(Finding(
                "S9", ERROR,
                "Step 1.5.1 lost its empty/absent -> LEGACY fallback",
                _GENSPEC_L2, 0,
                "registry rows written before issue #55 carry no value; without the "
                "fallback they become unroutable (no migration is ever performed)",
            ))
    return findings


def check_w8_registry_spec_template_values(repo: Repo) -> list[Finding]:
    """W8 — a registry row declares a spec_template_version nobody reads.

    Only a NON-EMPTY value outside {v1, legacy} is reported (WR6). An empty
    value, or a registry with no such column, is the documented pre-#55 state:
    it reads as LEGACY and is deliberately not a finding, so the rule cannot
    retroactively invalidate existing projects. 'STD_V1' (the value the STD-I7
    brief proposed) is the realistic way to get this wrong: Step 1.5.1 would
    match neither row of its table.
    """
    findings: list[Finding] = []
    reg = repo.root / "runtime" / "workspaces.md"
    if not reg.is_file():
        return findings
    lines = repo.lines(reg)
    idx = next((i for i, l in enumerate(lines) if l.strip().startswith("| workspace_id |")), -1)
    if idx < 0:
        return findings
    header, rows = table_with_header(lines, idx)
    col = column_index(header, "spec_template_version")
    if col < 0:
        return findings
    for n, cells in rows:
        if col >= len(cells):
            continue
        value = strip_md(cells[col])
        if value and value not in SPEC_TEMPLATE_VALUES:
            findings.append(Finding(
                "W8", WARN,
                f"workspace '{strip_md(cells[0])}' declares spec_template_version '{value}'",
                "runtime/workspaces.md", n,
                "admitted values: v1, legacy (empty = pre-#55 row, read as LEGACY); "
                "/generate-specification Step 1.5.1 routes no other value",
            ))
    return findings


# --------------------------------------------------------------------------
# S10 — CREATE Step 1.7b (theme + workspace_config.md) present in every layer  [issue #57]
# --------------------------------------------------------------------------

_LIFECYCLE_L4 = ".claude/commands/workspace-lifecycle.md"
_S10_THEME_QUESTION_MARKERS = (
    "THEME SELECTION —",
    "Enter choice [1]",
    "Ask the user to choose the HTML theme",
    "Prompt the user to select a CSS theme",
)


def check_s10_create_theme_step(repo: Repo) -> list[Finding]:
    """S10 — CREATE Step 1.7b (theme selection, workspace_config.md with
    `autonomy: GUIDED`) is carried by the L3 prompt and the L4 command, not
    only by the L2 execution spec.

    Found live (issue #57 manual run): Step 1.7b existed only in L2. A CREATE
    run told the user, in English, "Step 1.7b (Theme Selection) isn't in the
    prompt — let me read Phase 1 of the execution spec." Whether the config
    file (which also carries `autonomy`) got written depended on the model
    going to look for it.
    """
    findings: list[Finding] = []
    l2 = repo.root / _LIFECYCLE_L2
    if not l2.is_file():
        return findings
    if find_heading(repo.lines(l2), r"Step 1\.7b") < 0:
        return findings
    for rel, label, needles in (
        (_LIFECYCLE_L3, "L3 prompt", ("Step 1.7b", "workspace_config.md", "autonomy")),
        (_LIFECYCLE_L4, "L4 command", ("Step 1.7b", "workspace_config.md")),
    ):
        path = repo.root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        missing = [n for n in needles if n not in text]
        if missing:
            findings.append(Finding(
                "S10", ERROR,
                f"{label} omits CREATE Step 1.7b ({', '.join(missing)})",
                rel, 0,
                "L2 Step 1.7b selects the theme and writes runtime/workspace_config.md "
                "(theme, autonomy: GUIDED); every CREATE layer must carry it",
            ))
    # Issue #59: CREATE applies the standard theme without a question; an
    # explicit request is honoured, /configure-theme changes it later. A layer
    # that still carries the retired selection prompt reintroduces the question.
    for rel, label in (
        (_LIFECYCLE_L2, "L2 execution spec"),
        (_LIFECYCLE_L3, "L3 prompt"),
        (_LIFECYCLE_L4, "L4 command"),
    ):
        path = repo.root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        hits = [m for m in _S10_THEME_QUESTION_MARKERS if m in text]
        if hits:
            findings.append(Finding(
                "S10", ERROR,
                f"{label} still asks the theme question during CREATE ({hits[0]!r})",
                rel, 0,
                "since issue #59 CREATE applies the standard theme without asking; "
                "an explicit request is honoured and /configure-theme changes it later",
            ))
    return findings


CHECKS = {
    "S1": ("principle ID sequence is unique, contiguous and ordered", check_s1_principle_sequence),
    "S2": ("every referenced principle ID is defined", check_s2_dangling_principle_refs),
    "S3": ("a document is glossed the same way everywhere", check_s3_reference_gloss_drift),
    "S4": ("referenced repository paths exist", check_s4_broken_doc_references),
    "S5": ("duplicated SQF algorithms mention the same rules", check_s5_duplicated_sqf_algorithms),
    "S6": ("every L1 contract has a paired L2 execution spec", check_s6_l1_l2_layer_pairing),
    "S8": ("no generation artifact hardcodes a CSR version", check_s8_hardcoded_csr_version),
    "S9": ("every registry writer names the same columns and declares spec_template_version", check_s9_registry_schema),
    "S10": ("CREATE Step 1.7b (theme, workspace_config.md) is carried by L2, L3 and L4", check_s10_create_theme_step),
    "W1": ("no BLOCKING conflict left unconsolidated once specs exist", check_w1_blocking_conflict_not_consolidated),
    "W2": ("SQF I1.3 agrees with the open points it describes", check_w2_open_points_vs_sqf_gate),
    "W3": ("Inference Registry agrees with the specification body", check_w3_inference_registry_vs_body),
    "W4": ("no baselined spec carries a BLOCKING open point", check_w4_baseline_carries_blocking_open_point),
    "W5": ("no baselined spec records a criterion as INFIRMÉ", check_w5_baseline_carries_disproved_criterion),
    "W6": ("element status values stay inside their section vocabulary", check_w6_element_status_vocabulary),
    "W7": ("human-facing views carry a table of contents that resolves", check_w7_view_table_of_contents),
    "W8": ("registry spec_template_version values are v1 or legacy (empty tolerated)", check_w8_registry_spec_template_values),
}


def run(root: Path, only: set[str] | None = None) -> list[Finding]:
    repo = Repo(root=root)
    findings: list[Finding] = []
    for name, (_, fn) in CHECKS.items():
        if only and name not in only:
            continue
        findings.extend(fn(repo))
    order = {ERROR: 0, WARN: 1}
    findings.sort(key=lambda f: (order.get(f.severity, 9), f.check, f.file, f.line))
    return findings


def render_text(findings: list[Finding], selected: list[str]) -> str:
    out: list[str] = []
    out.append("csr-check — cross-layer consistency")
    out.append("")
    out.append(f"checks run: {', '.join(selected)}")
    out.append("")

    if not findings:
        out.append("No findings.")
        return "\n".join(out)

    by_check: dict[str, list[Finding]] = defaultdict(list)
    for f in findings:
        by_check[f.check].append(f)

    for check in sorted(by_check, key=lambda c: (c[0], c)):
        items = by_check[check]
        out.append(f"{check} — {CHECKS[check][0]}  ({len(items)})")
        for f in items:
            out.append(f"  [{f.severity}] {f.location()}")
            out.append(f"      {f.message}")
            if f.detail:
                out.append(f"      · {f.detail}")
        out.append("")

    errors = sum(1 for f in findings if f.severity == ERROR)
    warns = len(findings) - errors
    out.append(f"{errors} error(s), {warns} warning(s)")
    return "\n".join(out)


def render_shareable(findings: list[Finding], selected: list[str]) -> str:
    """B3 — a report safe to paste into a public issue tracker.

    CSR's own doctrine, stated since csr-check's first commit: S-checks read
    docs/, .claude/commands/, templates/ — the PRODUCT. W-checks read
    workspaces/<id>/ — the USER'S MATERIAL, which may carry business rules,
    client names, anything. The plain JSON/text renderers interpolate whatever
    a finding's `detail` field holds, and a W4 finding's detail is literally the
    open-point description from a baselined specification: in this repository's
    own history that has included a client's business-rule text and the term
    "CPC" verbatim. That output is not shareable, and no amount of string-level
    redaction after the fact is a safe substitute for not including it.

    This function does not filter the output of run() after the fact — "pas un
    filtre après coup" was the explicit design constraint this function exists
    to satisfy. It is constructed from S-family findings only, by selecting on
    the check ID prefix before any rendering happens, and carries a second,
    defensive guard: even within the S family, any finding whose `file` ever
    contains "workspaces/" is refused rather than emitted. No S-check is
    written to read workspaces/ today (verified: zero references across all
    seven S-check functions), so this guard should never fire — it exists for
    the day a future S-check is added carelessly, so that day fails loudly
    here instead of leaking silently into a shared report.
    """
    s_findings = [f for f in findings if f.check.startswith("S")]

    leaked = [f for f in s_findings if "workspaces/" in f.file or "workspaces/" in f.detail]
    if leaked:
        lines = [
            "csr-check: REFUSING to render a shareable report.",
            "",
            f"{len(leaked)} S-family finding(s) reference workspaces/ content, which this "
            "report must never contain by construction. This means an S-check was written "
            "(or edited) in a way that reads workspace material — fix the check, it is not "
            "safe to redact around this after the fact.",
            "",
        ]
        for f in leaked:
            lines.append(f"  [{f.check}] {f.location()}")
        return chr(10).join(lines)

    out: list[str] = []
    out.append("# csr-check — shareable report")
    out.append("")
    out.append("Product-layer findings only (S-family: docs/, .claude/commands/, templates/, tools/).")
    out.append("No workspace or client content is included — by construction, not by filtering.")
    out.append("")

    if not s_findings:
        out.append("No findings.")
        return chr(10).join(out)

    by_check: dict[str, list[Finding]] = defaultdict(list)
    for f in s_findings:
        by_check[f.check].append(f)

    for check in sorted(by_check):
        items = by_check[check]
        out.append(f"## {check} — {CHECKS[check][0]} ({len(items)})")
        out.append("")
        for f in items:
            out.append(f"- **[{f.severity}]** `{f.location()}` — {f.message}")
            if f.detail:
                out.append(f"  - {f.detail}")
        out.append("")

    errors = sum(1 for f in s_findings if f.severity == ERROR)
    warns = len(s_findings) - errors
    out.append(f"{errors} error(s), {warns} warning(s) — product layer only. "
               f"{len(findings) - len(s_findings)} workspace-layer finding(s) withheld, not counted here.")
    return chr(10).join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="csr-check",
        description="Cross-layer consistency checker for the Cognitive Specification Runtime.",
    )
    ap.add_argument("--root", default=".", help="repository root (default: current directory)")
    ap.add_argument("--only", default="", help="comma-separated check IDs, e.g. S1,W3")
    ap.add_argument("--format", choices=("text", "json", "shareable"), default="text")
    ap.add_argument("--list", action="store_true", help="list available checks and exit")
    args = ap.parse_args(argv)

    # CSR documents are UTF-8 and full of em-dashes; a cp1252 console would mangle
    # the report and make findings harder to read than they need to be.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    if args.list:
        for name, (desc, _) in CHECKS.items():
            print(f"{name}  {desc}")
        return 0

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"csr-check: not a directory: {root}", file=sys.stderr)
        return 2

    only = {s.strip().upper() for s in args.only.split(",") if s.strip()} or None
    if only:
        unknown = only - set(CHECKS)
        if unknown:
            print(f"csr-check: unknown check(s): {', '.join(sorted(unknown))}", file=sys.stderr)
            return 2

    try:
        findings = run(root, only)
    except Exception as exc:  # the checker must never masquerade as a clean result
        print(f"csr-check: internal failure: {exc!r}", file=sys.stderr)
        return 2

    selected = sorted(only) if only else list(CHECKS)
    if args.format == "json":
        print(json.dumps({
            "checks": selected,
            "findings": [asdict(f) for f in findings],
            "errors": sum(1 for f in findings if f.severity == ERROR),
            "warnings": sum(1 for f in findings if f.severity == WARN),
        }, indent=2, ensure_ascii=False))
    elif args.format == "shareable":
        print(render_shareable(findings, selected))
    else:
        print(render_text(findings, selected))

    return 1 if any(f.severity == ERROR for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
