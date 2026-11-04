"""Summarize mapping-only counterfactual routes from the frozen diagnostic rows."""

from collections import Counter
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def main():
    out = HERE / (sys.argv[1] if len(sys.argv) > 1 else "attempt-002")
    inputs = json.loads((out / "routing-diagnostic-inputs.json").read_text())
    rows = [json.loads(line) for line in (out / "routing-diagnostic.jsonl").read_text().splitlines()]
    original = [json.loads(line) for line in (HERE / "attempt-001/record-disposition.jsonl").read_text().splitlines()]
    families = {row["record_id"]: row["family"] for row in original}
    result = []
    for identity in inputs["record_ids"]:
        attempts = [row for row in rows if row["record_id"] == identity]
        complete = [row for row in attempts if row["mapping_complete"]]
        budget = [row for row in complete if row["native_preparation"]["admitted"]]
        scoped = [row for row in budget if not row["scope_errors"]]
        clean = [row for row in scoped if not row["whole_family_errors"] and not row["natural_anchor_collisions"]]
        errors = Counter((error["role"], error["reason"]) for row in attempts for error in row["errors"])
        blockers = Counter((failure["record_id"], error["role"], error["reason"])
            for row in scoped for failure in row["whole_family_errors"] for error in failure["errors"])
        best = min(clean, key=lambda row: (row["native_preparation"]["subwords"], row["context_chars"], row["context_id"])) if clean else None
        result.append(dict(record_id=identity, family=families[identity], attempted_contexts=len(attempts),
            complete_role_mapping_contexts=len(complete), native_budget_admitted_contexts=len(budget),
            annotation_scope_clean_contexts=len(scoped), whole_family_complete_contexts=len(clean),
            best_context=best,
            mapping_errors=[dict(role=role, reason=reason, occurrences=count) for (role, reason), count in errors.items()],
            other_reading_blockers=[dict(record_id=identity, role=role, reason=reason, occurrences=count)
                for (identity, role, reason), count in blockers.items()],
            scope_clean_collision_contexts=sum(bool(row["natural_anchor_collisions"]) for row in scoped)))
    summary = dict(outcome="passed", target_records=len(result), rows=result,
        complete_roles_by_family=dict(Counter(row["family"] for row in result if row["complete_role_mapping_contexts"])),
        whole_family_clean_by_family=dict(Counter(row["family"] for row in result if row["whole_family_complete_contexts"])),
        limits="Counterfactual existing-context mapping and native encoding budgets only; no runtime route, target-builder capacity, conditioning-universe integration, encoder or inference qualification.")
    with (out / "routing-summary.json").open("x") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    (out / "routing_analysis-executed.py.txt").write_bytes(Path(__file__).read_bytes())
    print(json.dumps({key: value for key, value in summary.items() if key != "rows"}))


if __name__ == "__main__":
    main()
