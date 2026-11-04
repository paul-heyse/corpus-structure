"""Summarize frozen reconstruction receipts only; no DB, tokenizer or model."""

from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def receipt(path):
    data = path.read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=sha256(data).hexdigest())


def main():
    out = HERE / (sys.argv[1] if len(sys.argv) > 1 else "attempt-001")
    ledger = rows(out / "record-disposition.jsonl")
    audits = rows(out / "request-audit.jsonl")
    dataset = rows(out / "training-targets.jsonl")
    origins = rows(out / "training-target-origins.jsonl")
    conflicts = rows(out / "conditioning-conflicts.jsonl")
    assert len(ledger) == 270 and len(dataset) == len(origins)
    status, errors, field_errors, population = Counter(), Counter(), Counter(), Counter()
    example_counts = Counter()
    unique_by_variant = defaultdict(set)
    collated_records, collated_by_variant = set(), defaultdict(set)
    for audit in audits:
        status[audit["status"]] += 1
        if audit["status"] == "collated":
            collated_records.update(audit["mapped"])
            collated_by_variant[audit["family"], audit["variant"]].update(audit["mapped"])
        for outside in audit["outside_population"]:
            population[outside["reason"]] += 1
        for error in audit["errors"]:
            reason = error["reason"]
            if reason.startswith("["):
                try:
                    for nested in json.loads(reason):
                        field_errors[audit["family"], nested["role"], nested["reason"]] += 1
                    reason = "one or more independently authored roles cannot map exactly"
                except (ValueError, TypeError, KeyError):
                    pass
            errors[reason] += 1
    for example, origin in zip(dataset, origins, strict=True):
        family, variant = origin["audit"]["family"], origin["audit"]["variant"]
        count = len(example["output"]["target_records"])
        example_counts[family, variant, "positive" if count else "genuine_zero"] += 1
        for alias in origin["all_alias_origins"]:
            unique_by_variant[family, variant].update(row["record_id"] for row in alias["origins"])
    terminal = defaultdict(Counter)
    for entry in ledger:
        if entry["emitted_requests"]:
            cause = "represented"
        elif entry["record_id"] in collated_records:
            cause = "all initially collated requests refused for conditioning conflict/incomplete identical input"
        elif entry["mapped_requests"]:
            cause = "mapped reading excluded by whole-request completeness/collision/capacity"
        else:
            cause = "no applicable complete exact mapped request"
        terminal[entry["family"]][cause] += 1
    bounded = [audit for audit in audits if "source_words" in audit]
    summary = dict(
        outcome="passed", original_records=len(ledger), requests=len(audits), request_status=dict(status),
        source_contexts=len(rows(out / "source-contexts.jsonl")),
        full_mapped_unique=dict(Counter(e["family"] for e in ledger if e["mapped_requests"])),
        initially_collated_unique=dict(Counter(e["family"] for e in ledger if e["record_id"] in collated_records)),
        emitted_examples=[dict(family=f, variant=v, kind=k, examples=n) for (f, v, k), n in sorted(example_counts.items())],
        emitted_unique_by_variant=[dict(family=f, variant=v, records=len(ids)) for (f, v), ids in sorted(unique_by_variant.items())],
        initially_collated_unique_by_variant=[dict(family=f, variant=v, records=len(ids)) for (f, v), ids in sorted(collated_by_variant.items())],
        emitted_record_instances=sum(len(e["output"]["target_records"]) for e in dataset),
        terminal_dispositions={family: dict(counts) for family, counts in terminal.items()},
        request_error_occurrences=dict(errors),
        role_error_occurrences=[dict(family=f, role=r, reason=reason, occurrences=n) for (f, r, reason), n in sorted(field_errors.items())],
        outside_population_occurrences=dict(population),
        conditioning_conflicts=dict(requests=len(conflicts),
            groups=len({row["conditioning_digest"] for row in conflicts}),
            with_excluded_same_input=sum(bool(row["excluded_same_input_requests"]) for row in conflicts)),
        native_preparation_bounds=dict(max_source_words=max(a["source_words"] for a in bounded),
            max_prefix_words=max(a["prefix_words"] for a in bounded),
            max_total_subwords=max(a["total_subwords"] for a in bounded),
            old_facade_refused_requests=sum(not a["old_facade_admissible"] for a in bounded)),
        assembly_excluded_records=[dict(record_id=e["record_id"], represented=bool(e["emitted_requests"]),
            reasons=e["assembly_exclusions"]) for e in ledger if e["assembly_exclusions"]],
        input_receipts=[receipt(out / name) for name in ("summary.json", "record-disposition.jsonl", "request-audit.jsonl",
            "training-targets.jsonl", "training-target-origins.jsonl", "contextual-configuration.json")],
        script=receipt(Path(__file__)),
        limits="mapping/metadata counts only; no model/forward/loss/training/heldout/quality claim")
    with (out / "analysis.json").open("x") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    (out / "analyze-executed.py.txt").write_bytes(Path(__file__).read_bytes())
    print(json.dumps(summary, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
