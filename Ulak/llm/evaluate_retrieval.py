"""Run a small deterministic regression suite for source-card retrieval."""

import json
from pathlib import Path

from llm.common import select_cards


def main():
    cases = json.loads(Path(__file__).with_name("retrieval_evaluation.json").read_text(encoding="utf-8"))
    failures = []
    for case in cases:
        selected = [card["id"] for card in select_cards(case["question"])]
        expected = case["expected"]
        passed = (not selected) if expected is None else expected in selected
        print(("PASS" if passed else "FAIL"), case["question"], "=>", selected)
        if not passed:
            failures.append(case)
    print(f"\n{len(cases) - len(failures)}/{len(cases)} retrieval checks passed")
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
