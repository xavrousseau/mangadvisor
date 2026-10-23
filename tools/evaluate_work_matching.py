"""Measure real work-ID accuracy without counting abstentions as successes.

Usage:
    python tools/evaluate_work_matching.py --gold gold.json --predictions predictions.json

Gold format (independently checked against authoritative source records):
[{"case_id":"...","expected_manga_id":123,"evidence_url":"https://..."},
 {"case_id":"...","expected_manga_id":null,"evidence_url":"https://..."}]

Predictions format:
[{"case_id":"...","suggested_manga_id":123,"decision":"STRONG_REVIEW_SUGGESTION"},
 {"case_id":"...","suggested_manga_id":null,"decision":"ABSTAIN"}]

No automatic SQL writes or network calls. Default acceptance REQUIRES >=48 labeled
cases, >=20 known linkable cases and precision, recall AND total-case coverage >=0.95.
A low-confidence suggestion never counts as an accepted prediction.
"""
from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any


def evaluate(gold: list[dict[str, Any]],
             predictions: list[dict[str, Any]],
             *, min_cases: int = 48, min_linkable: int = 20,
             min_precision: float = 0.95, min_recall: float = 0.95,
             min_total_coverage: float = 0.95
             ) -> dict[str, Any]:
    indexed: dict[str, dict[str, Any]] = {}
    missing_evidence = []
    for row in gold:
        key = str(row.get("case_id") or "").strip()
        if not key or key in indexed:
            raise ValueError("Missing or repeated case_id in reference set.")
        if not str(row.get("evidence_url") or "").startswith("https://"):
            missing_evidence.append(key)
        expected = row.get("expected_manga_id")
        if expected is not None and (type(expected) is not int or expected <= 0):
            raise ValueError("Gold work IDs must be positive integers or null.")
        indexed[key] = row
    responses: dict[str, dict[str, Any]] = {}
    for row in predictions:
        key = str(row.get("case_id") or "").strip()
        if not key or key in responses:
            raise ValueError("Missing or repeated case_id in predictions.")
        if key not in indexed:
            raise ValueError("Predictions contain a case without gold label.")
        responses[key] = row
    total = len(indexed)
    linkable = sum(x["expected_manga_id"] is not None for x in indexed.values())
    accepted = correct = false_positive = false_link = 0
    abstained_on_linkable = 0
    errors = []
    for key, row in indexed.items():
        response = responses.get(key,{})
        decision = response.get("decision") or "ABSTAIN"
        pred = response.get("suggested_manga_id")
        if decision == "ABSTAIN":
            if pred is not None:
                raise ValueError("Abstention must not carry a selected work ID.")
            if row["expected_manga_id"] is not None:
                abstained_on_linkable += 1
            continue
        if decision != "STRONG_REVIEW_SUGGESTION" or type(pred) is not int or pred<=0:
            raise ValueError("Only strong review suggestions with a valid ID count.")
        accepted += 1
        if row["expected_manga_id"] == pred:
            correct += 1
        else:
            false_positive += 1
            if row["expected_manga_id"] is None:
                false_link += 1
            errors.append({"case_id":key,"expected":row["expected_manga_id"],
                           "suggested":pred})
    precision = correct/accepted if accepted else 0.0
    recall = correct/linkable if linkable else 0.0
    # Total-case coverage stops a perfect score on only the easy 20/48 cases.
    # Unmatched no-MAL cases are unresolved, not automatically correct.
    total_coverage = correct/total if total else 0.0
    # No-match outcomes cannot become "true positive" by doing nothing.
    sufficient = (total>=min_cases and linkable>=min_linkable and
                  not missing_evidence and len(responses)==total)
    passed = (sufficient and precision>=min_precision and
              recall>=min_recall and total_coverage>=min_total_coverage)
    return {
        "reference_cases":total, "linkable_cases":linkable,
        "cases_with_missing_evidence":missing_evidence,
        "prediction_cases":len(responses),
        "accepted_suggestions":accepted,
        "correct_suggestions":correct,
        "false_positives":false_positive,
        "false_links_to_unindexed_works":false_link,
        "abstentions_on_linkable":abstained_on_linkable,
        "precision":round(precision,6),"recall":round(recall,6),
        "total_case_coverage":round(total_coverage,6),
        "acceptance_min_precision":min_precision,
        "acceptance_min_recall":min_recall,
        "acceptance_min_total_case_coverage":min_total_coverage,
        "sufficient_gold_and_predictions":sufficient,
        "target_95_met":passed,
        "errors":errors,
        "note":"Work IDs only; edition/ISBN accuracy needs a separate verified gold set.",
    }


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description="Independent work-ID gold evaluation")
    parser.add_argument("--gold",required=True)
    parser.add_argument("--predictions",required=True)
    parser.add_argument("--output")
    args=parser.parse_args(argv)
    a=json.loads(pathlib.Path(args.gold).read_text(encoding="utf-8"))
    b=json.loads(pathlib.Path(args.predictions).read_text(encoding="utf-8"))
    if not isinstance(a,list) or not isinstance(b,list):
        parser.error("Both files must contain JSON arrays.")
    report=evaluate(a,b)
    rendered=json.dumps(report,indent=2,ensure_ascii=False)
    if args.output:
        pathlib.Path(args.output).write_text(rendered+"\n",encoding="utf-8")
    print(rendered)
    return 0 if report["target_95_met"] else 2


if __name__=="__main__":
    raise SystemExit(main())
