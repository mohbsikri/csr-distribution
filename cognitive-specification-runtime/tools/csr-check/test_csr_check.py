#!/usr/bin/env python3
"""
Self-tests for csr-check.

A checker nobody verified is one more unverified claim, which is precisely the
failure mode this tool exists to attack. Every check therefore has both a
positive case (it fires on the defect it was written for) and a negative case
(it stays silent on the corrected version of the same artifact).

Run:
    python tools/csr-check/test_csr_check.py
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import csr_check  # noqa: E402


# --------------------------------------------------------------------------
# Fixture construction
# --------------------------------------------------------------------------

class RepoFixture:
    """A throwaway repository tree built file by file."""

    def __init__(self, root: Path):
        self.root = root

    def write(self, rel: str, content: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.strip() + "\n", encoding="utf-8")
        return path

    def spec(self, workspace: str, base: str, *, stable: bool,
             open_points: str = "", registry: str = "", body: str = "",
             acceptance: str = "") -> Path:
        folder = "stable" if stable else "draft"
        section_7 = f"\n## Section 7 — Acceptance Criteria\n\n{acceptance}\n" if acceptance else ""
        return self.write(
            f"workspaces/{workspace}/specifications/{folder}/{base}_specification_en.md",
            f"""
# {base} — Canonical Specification v1

## Section 5 — Business and Technical Rules

{body or "| ID | Description | Status |\n|---|---|---|\n| TR-001 | Something. | ACTIVE |"}
{section_7}

## Section 13 — Open Points

{open_points or "*(no open point)*"}

## Annexe A — Inference Registry

### INFERRED_DESIGN — Impact Structurel

{registry or "*(no element)*"}
"""
        )

    def gate_report(self, workspace: str, *, folder: str = "draft", i13: str = "ALL_RESOLVED") -> Path:
        return self.write(
            f"workspaces/{workspace}/specifications/{folder}/sqf_gate_report.md",
            f"""
# SQF Gate Report

## D1 — Complétude

| Indicateur | Valeur | Seuil | Statut |
|---|---|---|---|
| I1.3 Points ouverts | {i13} | ALL_RESOLVED=PASS | PASS |
"""
        )

    def conflicts(self, workspace: str, rows: str) -> Path:
        return self.write(
            f"workspaces/{workspace}/knowledge_base/conflicts/conflicts_report.md",
            f"""
# Conflicts Report

## Summary

| ID | Type | Severity | Status | Description |
|---|---|---|---|---|
{rows}
"""
        )

    def consolidation(self, workspace: str, records: str = "") -> Path:
        return self.write(
            f"workspaces/{workspace}/knowledge_base/consolidated/consolidation_report.md",
            f"""
# Consolidation Report

## Conflict Resolution Records

{records}

## Ineligible Conflicts

| Conflict ID | Reason |
|---|---|
"""
        )


OPEN_POINT_TABLE_HEADER = (
    "| ID | Description | Source | Priority | Status | Expected Resolution |\n"
    "|---|---|---|---|---|---|"
)

REGISTRY_HEADER = (
    "| Element | Rationale | Status | Propagating |\n"
    "|---|---|---|---|"
)


class CheckTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.fx = RepoFixture(Path(self._tmp.name))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_check(self, check: str) -> list[csr_check.Finding]:
        return csr_check.run(self.fx.root, only={check})

    def assertFires(self, check: str, *, contains: str = "") -> list[csr_check.Finding]:
        findings = self.run_check(check)
        self.assertTrue(findings, f"{check} should have produced a finding")
        if contains:
            joined = " ".join(f.message + " " + f.detail for f in findings)
            self.assertIn(contains, joined)
        return findings

    def assertSilent(self, check: str) -> None:
        findings = self.run_check(check)
        self.assertEqual(
            [], findings,
            f"{check} false positive: " + "; ".join(f"{f.location()} {f.message}" for f in findings),
        )


# --------------------------------------------------------------------------
# S-checks
# --------------------------------------------------------------------------

class TestS1PrincipleSequence(CheckTestCase):
    def test_out_of_order_is_reported(self):
        self.fx.write("docs/commands/x.md", """
# X

**CSR-E-01 — One**
Text.

**CSR-E-03 — Three**
Text.

**CSR-E-02 — Two**
Text.
""")
        self.assertFires("S1", contains="not in ascending order")

    def test_duplicate_id_is_an_error(self):
        self.fx.write("docs/commands/x.md", """
# X

**OA-01 — One**
Text.

**OA-02 — Two**
Text.

**OA-01 — One again**
Text.
""")
        findings = self.assertFires("S1", contains="defined twice")
        self.assertTrue(any(f.severity == csr_check.ERROR for f in findings))

    def test_gap_is_reported(self):
        self.fx.write("docs/commands/x.md", """
# X

**OAE-01 — One**
Text.

**OAE-04 — Four**
Text.
""")
        self.assertFires("S1", contains="gaps")

    def test_clean_sequence_is_silent(self):
        self.fx.write("docs/commands/x.md", """
# X

**CSR-E-01 — One**
Text.

**CSR-E-02 — Two**
Text.

**CSR-E-03 — Three**
Text.
""")
        self.assertSilent("S1")


class TestS2DanglingReferences(CheckTestCase):
    def test_reference_to_undefined_principle(self):
        self.fx.write("docs/commands/a.md", """
# A

**CSR-E-01 — One**
Text.
""")
        self.fx.write("docs/commands/b.md", """
# B

This behaviour is governed by CSR-E-09, see the contract.
""")
        self.assertFires("S2", contains="CSR-E-09")

    def test_defined_reference_is_silent(self):
        self.fx.write("docs/commands/a.md", """
# A

**CSR-E-01 — One**
Text.
""")
        self.fx.write("docs/commands/b.md", "# B\n\nGoverned by CSR-E-01.\n")
        self.assertSilent("S2")


class TestS3AdrGlossDrift(CheckTestCase):
    def test_divergent_adr_gloss_is_reported(self):
        self.fx.write("docs/decisions/ADR-001-language.md", "# ADR-001\n")
        self.fx.write("docs/commands/a.md", """
# A

## References

```text
docs/decisions/ADR-001-language.md — language policy (canonical artifacts English)
```
""")
        self.fx.write("docs/commands/b.md", """
# B

## References

```text
docs/decisions/ADR-001-language.md — language policy (canonical artifacts English)
```
""")
        self.fx.write("docs/commands/c.md", """
# C

## References

```text
docs/decisions/ADR-001-language.md — language policy (English only)
```
""")
        findings = self.assertFires("S3", contains="English only")
        self.assertEqual(1, len(findings), "only the minority gloss should be reported")
        self.assertTrue(findings[0].file.endswith("c.md"))

    def test_non_adr_phrasing_variation_is_ignored(self):
        """Scoping decision: phrasing variation outside docs/decisions/ is noise."""
        self.fx.write("docs/commands/target.md", "# T\n")
        self.fx.write("docs/commands/a.md", """
# A

## References

```text
docs/commands/target.md — M12 Layer 1 Contract
```
""")
        self.fx.write("docs/commands/b.md", """
# B

## References

```text
docs/commands/target.md — M12 Governance Runtime Contract
```
""")
        self.assertSilent("S3")


class TestS4BrokenReferences(CheckTestCase):
    def test_missing_target_is_an_error(self):
        self.fx.write("docs/commands/a.md", """
# A

## References

```text
docs/commands/does-not-exist.md — some contract
```
""")
        findings = self.assertFires("S4", contains="does-not-exist.md")
        self.assertEqual(csr_check.ERROR, findings[0].severity)

    def test_existing_target_is_silent(self):
        self.fx.write("docs/commands/target.md", "# T\n")
        self.fx.write("docs/commands/a.md", """
# A

## References

```text
docs/commands/target.md — some contract
```
""")
        self.assertSilent("S4")


# --------------------------------------------------------------------------
# W-checks — each mirrors a defect that actually reached a committed artifact
# --------------------------------------------------------------------------

class TestW1BlockingConflictNotConsolidated(CheckTestCase):
    """F-01: a BLOCKING conflict parked under 'Ineligible Conflicts' is invisible
    to the eligibility gate of /generate-specification."""

    def _workspace(self, *, consolidated: bool):
        self.fx.conflicts("ws", "| C006 | AMBIGUITY | BLOCKING | open | Undefined term. |")
        records = """
### C006

**Conflict ID:** C006
**Type:** AMBIGUITY
**Severity:** BLOCKING
**Status:** CONSOLIDATED
**Consolidated Artifact:** knowledge_base/consolidated/x_consolidated.md
""" if consolidated else ""
        self.fx.consolidation("ws", records)
        self.fx.spec("ws", "x", stable=True)

    def test_unconsolidated_blocking_conflict_fires(self):
        self._workspace(consolidated=False)
        findings = self.assertFires("W1", contains="C006")
        self.assertEqual(csr_check.ERROR, findings[0].severity)

    def test_consolidated_blocking_conflict_is_silent(self):
        self._workspace(consolidated=True)
        self.assertSilent("W1")

    def test_no_specifications_means_no_finding(self):
        """Before any specification exists, an unresolved conflict is normal work."""
        self.fx.conflicts("ws", "| C006 | AMBIGUITY | BLOCKING | open | Undefined term. |")
        self.fx.consolidation("ws", "")
        self.assertSilent("W1")


class TestW2OpenPointsVsGate(CheckTestCase):
    """F-02: I1.3 recorded ALL_RESOLVED while three open points were OPEN."""

    OPEN_ROW = (
        OPEN_POINT_TABLE_HEADER
        + "\n| OP-001 | Unresolved conflict C008. | ADVISORY | MEDIUM | OPEN | Human validation. |"
    )

    def test_open_points_with_all_resolved_fires(self):
        self.fx.spec("ws", "x", stable=True, open_points=self.OPEN_ROW)
        self.fx.gate_report("ws", i13="ALL_RESOLVED")
        findings = self.assertFires("W2", contains="ALL_RESOLVED")
        self.assertEqual(1, len(findings), "one finding per gate report, not one per occurrence")

    def test_no_open_points_is_silent(self):
        self.fx.spec("ws", "x", stable=True)
        self.fx.gate_report("ws", i13="ALL_RESOLVED")
        self.assertSilent("W2")

    def test_open_points_with_deferred_verdict_is_silent(self):
        self.fx.spec("ws", "x", stable=True, open_points=self.OPEN_ROW)
        self.fx.gate_report("ws", i13="DEFERRED")
        self.assertSilent("W2")

    def test_language_companions_counted_once(self):
        self.fx.spec("ws", "x", stable=True, open_points=self.OPEN_ROW)
        self.fx.write(
            "workspaces/ws/specifications/stable/x_specification_fr.md",
            "# x\n\n## Section 13 — Points Ouverts\n\n"
            "| ID | Description | Source | Priorité | Statut | Résolution attendue |\n"
            "|---|---|---|---|---|---|\n"
            "| OP-001 | Conflit non résolu C008. | ADVISORY | MOYENNE | OPEN | Validation humaine. |\n",
        )
        self.fx.gate_report("ws", i13="ALL_RESOLVED")
        findings = self.assertFires("W2")
        self.assertIn("1 specification(s)", findings[0].detail)


class TestW3InferenceRegistryVsBody(CheckTestCase):
    """F-10: human validation does not propagate to the Inference Registry, so the
    body says 'Validated and implemented' while the annex says PENDING_VALIDATION."""

    BODY_WITH_RESOLUTION = (
        "| ID | Description | Status |\n|---|---|---|\n"
        "| TR-001 | Historization by soft delete. **Resolution (C001):** Confirmed "
        "as the authoritative architecture. Validated and implemented. | ACTIVE |"
    )

    def test_pending_with_resolution_in_body_fires(self):
        self.fx.spec(
            "ws", "x", stable=False,
            body=self.BODY_WITH_RESOLUTION,
            registry=REGISTRY_HEADER + "\n| TR-001 | Design alternative adopted. | PENDING_VALIDATION | — |",
        )
        findings = self.assertFires("W3", contains="TR-001")
        self.assertEqual(csr_check.ERROR, findings[0].severity)

    def test_user_validated_is_silent(self):
        self.fx.spec(
            "ws", "x", stable=False,
            body=self.BODY_WITH_RESOLUTION,
            registry=REGISTRY_HEADER + "\n| TR-001 | Design alternative adopted. | USER_VALIDATED | — |",
        )
        self.assertSilent("W3")

    def test_pending_without_resolution_is_silent(self):
        """A genuinely unvalidated inference is a legitimate state, not a defect."""
        self.fx.spec(
            "ws", "x", stable=False,
            body="| ID | Description | Status |\n|---|---|---|\n| TR-006 | Categories via relation. | ACTIVE |",
            registry=REGISTRY_HEADER + "\n| TR-006 | Chosen among several models. | PENDING_VALIDATION | — |",
        )
        self.assertSilent("W3")


class TestW4BaselineCarriesBlockingOpenPoint(CheckTestCase):
    """F-01's consequence: a specification adopted as the official reference while
    a BLOCKING ambiguity on a pivotal business term is unresolved inside it."""

    BLOCKING_ROW = (
        OPEN_POINT_TABLE_HEADER
        + '\n| OP-001 | Unresolved conflict C006: the term "CPC" is not defined. '
          "| BLOCKING | HIGH | OPEN | Business to confirm. |"
    )
    ADVISORY_ROW = (
        OPEN_POINT_TABLE_HEADER
        + "\n| OP-001 | Unresolved conflict C008. | ADVISORY | MEDIUM | OPEN | Human validation. |"
    )

    def test_baselined_with_blocking_open_point_fires(self):
        self.fx.spec("ws", "x", stable=True, open_points=self.BLOCKING_ROW)
        findings = self.assertFires("W4", contains="OP-001")
        self.assertEqual(csr_check.ERROR, findings[0].severity)

    def test_draft_with_blocking_open_point_is_silent(self):
        """A draft is allowed to carry one — that is what drafts are for."""
        self.fx.spec("ws", "x", stable=False, open_points=self.BLOCKING_ROW)
        self.assertSilent("W4")

    def test_baselined_with_advisory_open_point_is_silent(self):
        self.fx.spec("ws", "x", stable=True, open_points=self.ADVISORY_ROW)
        self.assertSilent("W4")


class TestW5BaselineCarriesDisprovedCriterion(CheckTestCase):
    """ADR-007 Engagement #4: a criterion demonstrated false inside the document
    adopted as the official reference. No baseline gate can catch it — the test
    that disproves a criterion runs long after BASELINE."""

    HEADER = (
        "| ID | FR Couvert | Given | When | Then | Statut | Preuve | Démontré en |\n"
        "|---|---|---|---|---|---|---|---|"
    )
    DISPROVED = HEADER + (
        "\n| AC-007 | FR-007 | A learner scans the QR code. | Attendance is submitted. "
        "| Recorded without a Power Apps licence. | DK | INFIRMÉ | UAT 2026-10-12 |"
    )
    UNDEMONSTRATED = HEADER + (
        "\n| AC-007 | FR-007 | A learner scans the QR code. | Attendance is submitted. "
        "| Recorded without a Power Apps licence. | DK | NON_DÉMONTRÉ | — |"
    )
    DEMONSTRATED = HEADER + (
        "\n| AC-007 | FR-007 | A learner scans the QR code. | Attendance is submitted. "
        "| Recorded without a Power Apps licence. | DK | DÉMONTRÉ | UAT 2026-10-12 |"
    )
    # Column order deliberately differs from the canonical: the check must locate
    # "Preuve" by name. A positional read would land on "Statut" and stay silent.
    REORDERED = (
        "| ID | Preuve | FR Couvert | Démontré en | Given | When | Then | Statut |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| AC-007 | INFIRMÉ | FR-007 | PROD 2026-11-20 | A learner scans. "
        "| Submitted. | Recorded. | DK |"
    )
    PRE_ADR_007 = (
        "| ID | FR Couvert | Given | When | Then | Statut |\n"
        "|---|---|---|---|---|---|\n"
        "| AC-007 | FR-007 | A learner scans. | Submitted. | Recorded. | DK |"
    )

    def test_baselined_with_disproved_criterion_fires(self):
        self.fx.spec("ws", "x", stable=True, acceptance=self.DISPROVED)
        findings = self.assertFires("W5", contains="AC-007")
        self.assertEqual(csr_check.ERROR, findings[0].severity)
        self.assertIn("UAT 2026-10-12", findings[0].detail)

    def test_undemonstrated_criterion_is_silent(self):
        """The expected state of a fresh baseline — the system does not exist yet.
        Firing here would flag every correct specification."""
        self.fx.spec("ws", "x", stable=True, acceptance=self.UNDEMONSTRATED)
        self.assertSilent("W5")

    def test_demonstrated_criterion_is_silent(self):
        self.fx.spec("ws", "x", stable=True, acceptance=self.DEMONSTRATED)
        self.assertSilent("W5")

    def test_draft_with_disproved_criterion_is_silent(self):
        """A draft may record a failing test — that is how a spec gets corrected."""
        self.fx.spec("ws", "x", stable=False, acceptance=self.DISPROVED)
        self.assertSilent("W5")

    def test_column_is_located_by_name_not_position(self):
        self.fx.spec("ws", "x", stable=True, acceptance=self.REORDERED)
        self.assertFires("W5", contains="AC-007")

    def test_specification_without_proof_column_is_silent(self):
        """Baselined before ADR-007. Absence reads as NON_DÉMONTRÉ, not as an error:
        the freeze rules forbid rewriting it."""
        self.fx.spec("ws", "x", stable=True, acceptance=self.PRE_ADR_007)
        self.assertSilent("W5")

    def test_specification_without_section_7_is_silent(self):
        self.fx.spec("ws", "x", stable=True)
        self.assertSilent("W5")


class TestW6ElementStatusVocabulary(CheckTestCase):
    """One overloaded column name produced two opposite drifts in two real
    workspaces. The defect is a value, so the check reads the artifact rather than
    the contracts — whichever layer caused it, the wrong value lands here."""

    def _ac(self, last_col_name: str, value: str) -> str:
        return (
            f"| ID | FR Couvert | Given | When | Then | {last_col_name} |\n"
            "|---|---|---|---|---|---|\n"
            f"| AC-001 | FR-001 | A record is open. | The user saves. | It persists. | {value} |"
        )

    def test_draft_in_acceptance_criterion_fires(self):
        """DRAFT is the specification's lifecycle state, never an element's. The
        column carries US, and US blocks BASELINE — a generation that never emits
        US makes that gate unreachable."""
        self.fx.spec("ws", "x", stable=False, acceptance=self._ac("Source", "DRAFT"))
        findings = self.assertFires("W6", contains="DRAFT")
        self.assertEqual(csr_check.ERROR, findings[0].severity)

    def test_provenance_value_is_silent(self):
        self.fx.spec("ws", "x", stable=False, acceptance=self._ac("Source", "DK"))
        self.assertSilent("W6")

    def test_legacy_statut_header_is_still_read(self):
        """Specs generated before the 2026-11-01 rename say Statut; they are frozen
        and must stay readable, so the alias is honoured rather than ignored."""
        self.fx.spec("ws", "x", stable=True, acceptance=self._ac("Statut", "DRAFT"))
        self.assertFires("W6", contains="DRAFT")

    def test_english_status_header_is_still_read(self):
        self.fx.spec("ws", "x", stable=True, acceptance=self._ac("Status", "DRAFT"))
        self.assertFires("W6", contains="DRAFT")

    def test_lifecycle_value_in_acceptance_criterion_fires(self):
        """ACTIF is valid in Sections 5, 6 and 11 and wrong in Section 7 — the whole
        point of giving each section its own vocabulary."""
        self.fx.spec("ws", "x", stable=False, acceptance=self._ac("Source", "ACTIF"))
        self.assertFires("W6", contains="ACTIF")

    def test_table_without_given_is_not_section_7(self):
        """EVOLVE certification fixtures carry a hand-authored 4-column AC table with
        lifecycle values. It is not the STD Section 7 and must not be judged as one."""
        self.fx.spec("ws", "x", stable=True, acceptance=(
            "| ID | Libellé | FR Couvert | Statut |\n"
            "|---|---|---|---|\n"
            "| AC-001 | Libellé du critère | FR-001 | DEPRECATED |"
        ))
        self.assertSilent("W6")

    def test_one_finding_per_distinct_bad_value(self):
        """Twenty-two criteria carrying the same wrong value is one defect, not
        twenty-two. A check that floods its own output stops being read."""
        rows = "\n".join(
            f"| AC-{i:03d} | FR-{i:03d} | Open. | Save. | Persists. | DRAFT |"
            for i in range(1, 23)
        )
        self.fx.spec("ws", "x", stable=False, acceptance=(
            "| ID | FR Couvert | Given | When | Then | Source |\n"
            "|---|---|---|---|---|---|\n" + rows
        ))
        self.assertEqual(1, len(self.assertFires("W6")))


class TestW7ViewTableOfContents(CheckTestCase):
    """Generation omits the mandated TOC silently: std-synth-01 has none on any of
    its four views, and std-real-01 lacks it on one view of four whose siblings,
    produced in the same run, have it."""

    TOC = (
        '<div class="toc">\n<h2>Table des matières</h2>\n<ol>\n'
        '<li><a href="#sf-03">Résumé exécutif</a></li>\n'
        '<li><a href="#sf-04">Contexte</a></li>\n</ol>\n</div>'
    )
    BODY = "\n\n## Résumé exécutif {#sf-03}\n\nText.\n\n## Contexte {#sf-04}\n\nText.\n"

    def view(self, name: str, content: str):
        return self.fx.write(f"workspaces/ws/specifications/views/{name}.md", content)

    def test_human_view_without_toc_fires(self):
        self.view("proj_specification_fonctionnelle_fr", "# Titre" + self.BODY)
        findings = self.assertFires("W7", contains="no table of contents")
        self.assertEqual(csr_check.ERROR, findings[0].severity)

    def test_human_view_with_resolving_toc_is_silent(self):
        self.view("proj_specification_fonctionnelle_fr", "# Titre\n\n" + self.TOC + self.BODY)
        self.assertSilent("W7")

    def test_dead_anchor_fires(self):
        """The failure mode built into a hardcoded TOC: it lists the sections the
        contract expects, so omitting a conditional section leaves a dead entry."""
        self.view("proj_dossier_architecture_fr", "# Titre\n\n" + self.TOC
                  + "\n\n## Résumé exécutif {#sf-03}\n\nOnly this one exists.\n")
        self.assertFires("W7", contains="#sf-04")

    def test_view_agent_is_silent(self):
        """Consumed by an agent, not read. It has no TOC by design, and flagging it
        would train the reader to ignore this check."""
        self.view("proj_view_agent_fr", "# Titre" + self.BODY)
        self.assertSilent("W7")

    def test_english_view_names_are_covered(self):
        self.view("proj_functional_specification_en", "# Title" + self.BODY)
        self.assertFires("W7", contains="no table of contents")


class TestS5DuplicatedSqfAlgorithms(CheckTestCase):
    """The SQF indicator algorithms are spelled out twice — in the gate report
    template that defines them and the execution spec that runs them. Nothing tied
    the copies together, so an edit to one left the other computing a different
    number while still looking authoritative."""

    TPL = "templates/sqf_gate_report_template.md"
    EXE = "docs/commands/generate-specification_execution.md"

    def test_rule_present_in_one_copy_only_fires(self):
        self.fx.write(self.TPL, "I3.1 calculation: exclude OP-NNN rows. ALL_RESOLVED vocabulary.")
        self.fx.write(self.EXE, "I3.1 calculation: traced/total. ALL_RESOLVED vocabulary.")
        findings = self.assertFires("S5", contains="OP-NNN")
        self.assertEqual(csr_check.ERROR, findings[0].severity)
        self.assertIn(self.TPL, findings[0].detail)

    def test_rule_present_in_both_copies_is_silent(self):
        self.fx.write(self.TPL, "exclude OP-NNN rows. ALL_RESOLVED.")
        self.fx.write(self.EXE, "exclude OP-NNN rows. ALL_RESOLVED.")
        self.assertSilent("S5")

    def test_rule_absent_from_both_is_silent(self):
        """A rule nobody states anywhere is not drift — it is a rule that does not
        exist. Firing here would demand every listed rule forever."""
        self.fx.write(self.TPL, "nothing relevant")
        self.fx.write(self.EXE, "nothing relevant")
        self.assertSilent("S5")

    def test_missing_file_is_not_drift(self):
        self.fx.write(self.TPL, "exclude OP-NNN rows. ALL_RESOLVED.")
        self.assertSilent("S5")


class TestS6L1L2LayerPairing(CheckTestCase):
    """L1 and L2 both live in docs/commands/ under <base>.md / <base>_execution.md.
    operating-agent-execution.md was the real, pre-existing counter-example: a
    hyphen before "execution" where every one of its 23 siblings used an
    underscore -- content-complete, present on disk, and still invisible to a
    mechanical lookup for the L2 of operating-agent."""

    def test_orphan_l1_contract_fires(self):
        self.fx.write("docs/commands/foo.md", "# Foo")
        self.assertFires("S6", contains="foo.md")

    def test_orphan_l2_spec_fires(self):
        self.fx.write("docs/commands/bar_execution.md", "# Bar execution")
        self.assertFires("S6", contains="bar_execution.md")

    def test_matched_pair_is_silent(self):
        self.fx.write("docs/commands/baz.md", "# Baz")
        self.fx.write("docs/commands/baz_execution.md", "# Baz execution")
        self.assertSilent("S6")

    def test_hyphenated_execution_file_fires(self):
        """The actual historical defect: present, complete, wrong separator."""
        self.fx.write("docs/commands/quux.md", "# Quux")
        self.fx.write("docs/commands/quux-execution.md", "# Quux execution")
        findings = self.assertFires("S6", contains="quux-execution.md")
        self.assertTrue(any("naming convention" in f.message for f in findings))

    def test_prompt_template_is_not_mistaken_for_an_orphan_l1(self):
        """*-prompt-template.md is an L3 artifact living in docs/commands/, not
        an L1 contract — it must not demand a nonexistent L2 of its own."""
        self.fx.write("docs/commands/widget-prompt-template.md", "# Widget prompt")
        self.assertSilent("S6")

    def test_no_commands_directory_is_silent(self):
        self.assertSilent("S6")


class TestS8HardcodedCsrVersion(CheckTestCase):
    """templates/spec_canonical_v1.md and the L2 instruction that emits its
    header both said CSR v2.0.0 -- the version CSR carried the day the
    template was written, silently frozen into every specification generated
    since, across eight months and dozens of releases."""

    def test_hardcoded_version_in_template_fires(self):
        self.fx.write("templates/spec_canonical_v1.md", "Template: spec_canonical_v1 - CSR v2.0.0")
        findings = self.assertFires("S8", contains="CSR v2.0.0")
        self.assertEqual(csr_check.ERROR, findings[0].severity)

    def test_hardcoded_version_in_l2_fires(self):
        self.fx.write("docs/commands/generate-specification_execution.md", "Template: spec_canonical_v1 - CSR v2.8.3")
        self.assertFires("S8", contains="CSR v2.8.3")

    def test_current_runtime_version_placeholder_is_silent(self):
        self.fx.write("templates/spec_canonical_v1.md", "Template: spec_canonical_v1 - CSR CURRENT_RUNTIME_VERSION")
        self.assertSilent("S8")

    def test_out_of_scope_file_is_silent(self):
        """A historical analysis document correctly saying 'CSR v2.0.0 was
        released on this date' is a fact, not a drift risk -- only the two
        files that actually generate a spec header are in scope."""
        self.fx.write("(internal review note)", "CSR v2.0.0 was released on 2026-07-02.")
        self.assertSilent("S8")



# --------------------------------------------------------------------------
# S9 / W8 — registry schema and spec_template_version  [issue #55]
# --------------------------------------------------------------------------

_HEADER = "| workspace_id | created | status | description | last_active | runtime_version | spec_template_version |"
_SEP = "| --- | --- | --- | --- | --- | --- | --- |"


def _writer_table(template_value: str | None) -> str:
    rows = [
        "| Field | Value |", "|-------|-------|",
        "| `workspace_id` | input |", "| `created` | now |", "| `status` | `paused` |",
        "| `description` | input |", "| `last_active` | empty |",
        "| `runtime_version` | workspace_runtime_version |",
    ]
    if template_value is not None:
        rows.append(f"| `spec_template_version` | `{template_value}` — always |")
    return "\n".join(rows)


def _lifecycle_l2(create: str | None = "v1", v2: str | None = "legacy") -> str:
    return f"""
# Workspace Lifecycle Runtime — Execution Specification

#### Step 0.1a — Registry Initialization

```markdown
# Workspace Registry

{_HEADER}
{_SEP}
```

### Step 1.8 — Registry Entry Write

Append a new row to `runtime/workspaces.md` with the following field values:

{_writer_table(create)}

### Step 15.10 — Registry Entry Write

Append a new row to `runtime/workspaces.md`:

{_writer_table(v2)}
"""


def _genspec_l2(*, fallback: bool = True, v1_mode: str = "STD") -> str:
    rows = [
        "| Value | `template_mode` | Note |", "|---|---|---|",
        f"| `v1` | `{v1_mode}` | STD |", "| `legacy` | `LEGACY` | legacy |",
    ]
    if fallback:
        rows.append("| absent / empty | `LEGACY` | WARNING |")
    return "### Step 1.5.1 — Read spec_template_version\n\nExtract the column value:\n\n" + "\n".join(rows)


def _registry(*rows: str, header: str = _HEADER, sep: str = _SEP) -> str:
    return "# Workspace Registry\n\n" + "\n".join([header, sep, *rows])


class TestS9RegistrySchema(CheckTestCase):
    """Issue #54 review: Step 0.1a and csr-init.ps1 wrote a 7-column header,
    CREATE Step 1.8 and V2 Step 15.10 listed 6 fields. Every new project got
    an empty spec_template_version and generated LEGACY instead of STD v1."""

    def write_aligned(self) -> None:
        self.fx.write("docs/commands/workspace-lifecycle_execution.md", _lifecycle_l2())
        self.fx.write("templates/prompts/workspace-lifecycle_prompt.md",
                      "4. Write a new row to `runtime/workspaces.md` with these exact field values:\n\n"
                      + _writer_table("v1"))
        self.fx.write("tools/csr-init/csr-init.ps1", f'$cols = "{_HEADER}"')
        self.fx.write("docs/commands/generate-specification_execution.md", _genspec_l2())

    def test_aligned_layers_are_silent(self):
        self.write_aligned()
        self.assertSilent("S9")

    def test_create_omitting_the_column_fires(self):
        """The exact pre-#55 defect."""
        self.write_aligned()
        self.fx.write("docs/commands/workspace-lifecycle_execution.md", _lifecycle_l2(create=None))
        findings = self.assertFires("S9", contains="falls back to LEGACY")
        self.assertIn("CREATE Step 1.8", findings[0].message)
        self.assertEqual(csr_check.ERROR, findings[0].severity)

    def test_v2_omitting_the_column_fires(self):
        self.write_aligned()
        self.fx.write("docs/commands/workspace-lifecycle_execution.md", _lifecycle_l2(v2=None))
        self.assertFires("S9", contains="V2 Step 15.10")

    def test_create_writing_legacy_fires(self):
        """Decision (option A): a new classic project is v1, not legacy."""
        self.write_aligned()
        self.fx.write("docs/commands/workspace-lifecycle_execution.md", _lifecycle_l2(create="legacy"))
        self.assertFires("S9", contains="must write spec_template_version 'v1'")

    def test_v2_writing_v1_fires(self):
        """V2 is LEGACY by construction (Step 1.5.2); the registry must say so."""
        self.write_aligned()
        self.fx.write("docs/commands/workspace-lifecycle_execution.md", _lifecycle_l2(v2="v1"))
        self.assertFires("S9", contains="must write spec_template_version 'legacy'")

    def test_l3_prompt_omitting_the_column_fires(self):
        self.write_aligned()
        self.fx.write("templates/prompts/workspace-lifecycle_prompt.md",
                      "4. Write a new row to `runtime/workspaces.md` with these exact field values:\n\n"
                      + _writer_table(None))
        self.assertFires("S9", contains="L3 CREATE registry row")

    def test_csr_init_header_drift_fires(self):
        self.write_aligned()
        self.fx.write("tools/csr-init/csr-init.ps1",
                      '$cols = "| workspace_id | created | status | description | last_active | runtime_version |"')
        self.assertFires("S9", contains="csr-init.ps1")

    def test_removing_the_legacy_fallback_fires(self):
        """Non-regression for existing projects: rows written before #55 have
        no value; the fallback is what keeps them routable."""
        self.write_aligned()
        self.fx.write("docs/commands/generate-specification_execution.md", _genspec_l2(fallback=False))
        self.assertFires("S9", contains="lost its empty/absent -> LEGACY fallback")

    def test_v1_no_longer_routing_to_std_fires(self):
        self.write_aligned()
        self.fx.write("docs/commands/generate-specification_execution.md", _genspec_l2(v1_mode="LEGACY"))
        self.assertFires("S9", contains="does not route 'v1' to STD")

    def test_repository_without_lifecycle_spec_is_silent(self):
        self.assertSilent("S9")


class TestS10CreateThemeStep(CheckTestCase):
    """Issue #57: Step 1.7b lived only in L2; the model narrated, in English,
    that it was missing from the prompt and went to read the execution spec."""

    L2 = "### Step 1.7b — Theme Selection\n\nWrite `runtime/workspace_config.md` (`autonomy: GUIDED`)."
    L3 = "3b. Theme selection (L2 Step 1.7b): write `workspace_config.md` including `autonomy: GUIDED`."
    L4 = "- `CREATE` → theme selection and `runtime/workspace_config.md` (Step 1.7b)."

    def write_aligned(self) -> None:
        self.fx.write("docs/commands/workspace-lifecycle_execution.md", self.L2)
        self.fx.write("templates/prompts/workspace-lifecycle_prompt.md", self.L3)
        self.fx.write(".claude/commands/workspace-lifecycle.md", self.L4)

    def test_aligned_layers_are_silent(self):
        self.write_aligned()
        self.assertSilent("S10")

    def test_l3_without_step_fires(self):
        """The exact pre-#57 state of the prompt."""
        self.write_aligned()
        self.fx.write("templates/prompts/workspace-lifecycle_prompt.md", "3. Create a `.gitkeep` file.")
        findings = self.assertFires("S10", contains="L3 prompt omits CREATE Step 1.7b")
        self.assertEqual(csr_check.ERROR, findings[0].severity)

    def test_l3_without_autonomy_fires(self):
        self.write_aligned()
        self.fx.write("templates/prompts/workspace-lifecycle_prompt.md",
                      "3b. Theme (L2 Step 1.7b): write `workspace_config.md`.")
        self.assertFires("S10", contains="autonomy")

    def test_l4_without_step_fires(self):
        self.write_aligned()
        self.fx.write(".claude/commands/workspace-lifecycle.md", "- `CREATE` → registry write.")
        self.assertFires("S10", contains="L4 command")

    def test_l2_theme_prompt_fires(self):
        """Issue #59: the retired interactive theme prompt must not come back."""
        self.write_aligned()
        self.fx.write("docs/commands/workspace-lifecycle_execution.md",
                      self.L2 + "\n\nTHEME SELECTION — workspace x\n\nEnter choice [1]:")
        self.assertFires("S10", contains="L2 execution spec still asks the theme question")

    def test_l3_theme_question_fires(self):
        """The exact beta.4 wording of L3 step 3b."""
        self.write_aligned()
        self.fx.write("templates/prompts/workspace-lifecycle_prompt.md",
                      self.L3 + " Ask the user to choose the HTML theme.")
        self.assertFires("S10", contains="L3 prompt still asks the theme question")

    def test_l2_without_step_is_silent(self):
        self.write_aligned()
        self.fx.write("docs/commands/workspace-lifecycle_execution.md", "### Step 1.7 — .gitkeep")
        self.assertSilent("S10")


class TestW8RegistrySpecTemplateValues(CheckTestCase):
    """WR6: only a non-empty value outside {v1, legacy} is reported. Existing
    projects (empty value, or a registry predating the column) never are."""

    def test_v1_and_legacy_rows_are_silent(self):
        self.fx.write("runtime/workspaces.md", _registry(
            "| new-01 | 2026-11-09T00:00:00Z | paused | New | | 2.8.19 | v1 |",
            "| v2-01 | 2026-11-09T00:00:00Z | paused | Fork | | 2.8.19 | legacy |",
        ))
        self.assertSilent("W8")

    def test_old_row_with_empty_value_is_silent(self):
        """recette-synthetique-53 (#53) was registered with an empty cell: it
        must stay valid and keep its LEGACY fallback, never be flagged."""
        self.fx.write("runtime/workspaces.md", _registry(
            "| recette-synthetique-53 | 2026-11-09T16:00:00Z | paused | Old | | 2.8.18 | |",
        ))
        self.assertSilent("W8")

    def test_registry_without_the_column_is_silent(self):
        self.fx.write("runtime/workspaces.md", _registry(
            "| default | 2026-06-06T09:21:24Z | paused | Default | | 0.3.0 |",
            header="| workspace_id | created | status | description | last_active | runtime_version |",
            sep="| --- | --- | --- | --- | --- | --- |",
        ))
        self.assertSilent("W8")

    def test_unknown_value_warns(self):
        self.fx.write("runtime/workspaces.md", _registry(
            "| std-synth-01 | 2026-07-01T00:00:00Z | paused | Synth | | 2.0.0 | STD_V1 |",
        ))
        findings = self.assertFires("W8", contains="STD_V1")
        self.assertEqual(csr_check.WARN, findings[0].severity)


class TestB3ShareableReport(unittest.TestCase):
    """B3: csr-check's plain output is not shareable -- a W4 finding's detail is
    literally the open-point description from a baselined specification, which
    in this repository's own history has included client business-rule text and
    the term \"CPC\" verbatim. render_shareable must never emit W-family content,
    by construction rather than by stripping it after the fact."""

    def mk(self, check, severity, message, file, line=0, detail=""):
        return csr_check.Finding(check=check, severity=severity, message=message,
                                  file=file, line=line, detail=detail)

    def test_s_finding_is_included(self):
        findings = [self.mk("S4", csr_check.ERROR, "broken path", "docs/commands/x.md", 10)]
        out = csr_check.render_shareable(findings, ["S4"])
        self.assertIn("docs/commands/x.md", out)
        self.assertIn("S4", out)

    def test_w_finding_is_excluded(self):
        findings = [self.mk("W4", csr_check.ERROR, "BLOCKING open point",
                             "workspaces/client-01/specifications/stable/x.md", 5,
                             detail="the term CPC, used in the Must Have rule, is not defined")]
        out = csr_check.render_shareable(findings, ["W4"])
        self.assertNotIn("CPC", out)
        self.assertNotIn("client-01", out)
        self.assertIn("No findings", out)

    def test_mixed_shows_only_s_and_counts_withheld_w(self):
        findings = [
            self.mk("S4", csr_check.ERROR, "broken path", "docs/commands/x.md", 10),
            self.mk("W4", csr_check.ERROR, "BLOCKING open point",
                     "workspaces/client-01/specifications/stable/x.md", 5,
                     detail="business rule BR-004, term CPC"),
        ]
        out = csr_check.render_shareable(findings, ["S4", "W4"])
        self.assertIn("docs/commands/x.md", out)
        self.assertNotIn("CPC", out)
        self.assertNotIn("client-01", out)
        self.assertIn("1 workspace-layer finding(s) withheld", out)

    def test_s_finding_referencing_workspaces_is_refused_not_emitted(self):
        """Defensive guard: no S-check reads workspaces/ today, but if one ever
        did by mistake, this must fail loudly rather than leak the content."""
        findings = [self.mk("S4", csr_check.ERROR, "broken path",
                             "workspaces/client-01/oops.md", 1)]
        out = csr_check.render_shareable(findings, ["S4"])
        self.assertIn("REFUSING", out)
        self.assertNotIn("client-01", out.split("REFUSING")[0])

    def test_no_findings_at_all_is_clean(self):
        out = csr_check.render_shareable([], ["S1"])
        self.assertIn("No findings", out)


class TestRunnerContract(unittest.TestCase):
    def test_every_check_is_registered_and_callable(self):
        self.assertTrue(csr_check.CHECKS)
        for name, (desc, fn) in csr_check.CHECKS.items():
            self.assertRegex(name, r"^[SW]\d+$")
            self.assertTrue(desc.strip())
            self.assertTrue(callable(fn))

    def test_empty_repository_is_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual([], csr_check.run(Path(tmp)))

    def test_unknown_check_is_rejected(self):
        self.assertEqual(2, csr_check.main(["--only", "ZZ9", "--root", "."]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
