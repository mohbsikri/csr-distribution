#!/usr/bin/env python3
"""
C2 -- exploratory, NOT wired into csr_check.py (same status as S5-narrow and
C4: a research-grade fuzzy-similarity probe, not a permanent check).

S5-narrow already measured L1<->L2 reformulation across all 25 pairs (1 real
case out of 8 candidates: governance-resolve RI-01..10 vs EI-01..10). This
extends the SAME method to L1<->L3 (the 18 commands that have a dedicated
prompt template under templates/commands/ or templates/prompts/), which was
never measured -- C2's own question names "L2 et L3," and only L2 had data.

Method: paragraph-level word-set Jaccard similarity, >=25-word paragraphs,
code fences and table rows excluded, threshold 0.55 -- identical parameters
to the L1<->L2 run, so the two results are comparable.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
THRESHOLD = 0.55
MIN_WORDS = 25

PAIRS = {
    "configure-theme": "templates/commands/configure_theme_prompt.md",
    "consolidate-knowledge": "templates/prompts/consolidate_knowledge_prompt.md",
    "detect-conflicts": "templates/commands/detect_conflicts_prompt.md",
    "export-views": "templates/prompts/export_views_prompt.md",
    "extract-knowledge": "templates/commands/extract_knowledge_prompt.md",
    "generate-questions": "templates/commands/generate_questions_prompt.md",
    "generate-specification": "templates/prompts/generate_specification_prompt.md",
    "generate-test-cases": "templates/commands/generate_test_cases_prompt.md",
    "generate-views": "templates/commands/generate_views_prompt.md",
    "governance-policy": "templates/prompts/governance_policy_prompt.md",
    "governance-resolve": "templates/prompts/governance_resolve_prompt.md",
    "governance-run": "templates/prompts/governance_run_prompt.md",
    "human-validation": "templates/prompts/human_validation_prompt.md",
    "ingest_source": "templates/commands/ingest_source_prompt.md",
    "pipeline-run": "templates/prompts/pipeline_run_prompt.md",
    "preprocess-source": "templates/commands/preprocess_source_prompt.md",
    "specification-lifecycle": "templates/prompts/specification_lifecycle_prompt.md",
    "workspace-lifecycle": "templates/prompts/workspace-lifecycle_prompt.md",
}


def strip_fences_and_tables(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    lines = [ln for ln in text.splitlines() if not re.match(r"^\s*\|", ln)]
    return "\n".join(lines)


def paragraphs(text: str) -> list[str]:
    text = strip_fences_and_tables(text)
    raw = re.split(r"\n\s*\n", text)
    out = []
    for p in raw:
        words = re.findall(r"[A-Za-zÀ-ÿ']+", p)
        if len(words) >= MIN_WORDS:
            out.append(p)
    return out


def word_set(p: str) -> set[str]:
    return set(w.lower() for w in re.findall(r"[A-Za-zÀ-ÿ']+", p))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def main() -> None:
    candidates = []
    for base, l3_rel in PAIRS.items():
        l1_path = REPO_ROOT / "docs" / "commands" / f"{base}.md"
        l3_path = REPO_ROOT / l3_rel
        if not l1_path.is_file() or not l3_path.is_file():
            print(f"SKIP {base}: missing file ({l1_path.exists()=}, {l3_path.exists()=})")
            continue
        l1_paras = paragraphs(l1_path.read_text(encoding="utf-8"))
        l3_paras = paragraphs(l3_path.read_text(encoding="utf-8"))
        best = 0.0
        best_pair = None
        for p1 in l1_paras:
            s1 = word_set(p1)
            for p2 in l3_paras:
                s2 = word_set(p2)
                score = jaccard(s1, s2)
                if score > best:
                    best = score
                    best_pair = (p1[:90], p2[:90])
        if best >= THRESHOLD:
            candidates.append((base, best, best_pair))

    print(f"Pairs scanned: {len(PAIRS)}")
    print(f"Candidates >= {THRESHOLD}: {len(candidates)}")
    for base, score, (p1, p2) in sorted(candidates, key=lambda x: -x[1]):
        print(f"\n--- {base} (score={score:.2f}) ---")
        print(f"  L1: {p1}...")
        print(f"  L3: {p2}...")


if __name__ == "__main__":
    main()
