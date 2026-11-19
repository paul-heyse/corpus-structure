"""Summarize preserved UDM-20 receipts without opening any database connection."""

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
REPOSITORY = FOLDER.parents[3]
EVIDENCE = FOLDER.parent
BOOK = "1dd5d45ded4b4ea38399fb121a44d28c"
DISCOVERY = "3fed447a2a5649538c80ac05c1ed7c47"
INTERRUPTED = "82ba77a0731148faa0bd827ead1373cb"


def read(path):
    return json.loads(path.read_bytes())


def retained(result):
    return EVIDENCE / ("2026-11-18_cli-" + result)


def test_receipt(result):
    folder = retained(result) / "raw/ordinary"
    reports = [json.loads(line) for line in (folder / "reportlog.jsonl").read_text().splitlines()]
    return {
        "id": result,
        "original_outcome": read(retained(result) / "invocation.json")["outcome"],
        "reports": [
            {key: report.get(key) for key in ("nodeid", "when", "outcome", "duration")}
            for report in reports
            if report.get("$report_type") == "TestReport"
        ],
        "private_child_settlement": read(folder / "private-host-child-settlement.json"),
        "supervisor": read(folder / "runner.process.json"),
        "pytest_process": read(folder / "pytest.process.json"),
        "retained_report_matches_managed": (folder / "reportlog.jsonl").read_bytes()
        == (REPOSITORY / "build/ci" / result / "ordinary/reportlog.jsonl").read_bytes(),
    }


def main():
    manifest = read(FOLDER / "raw/book-manifest.json")
    native_path = retained(BOOK) / "raw/native.json"
    native = read(native_path)
    snapshot = native["snapshot"]
    journal = FOLDER / "raw/book-observations.jsonl"
    journal_digest = hashlib.sha256(journal.read_bytes()).hexdigest()
    assert journal_digest == manifest["observations"]["sha256"]
    rows = [json.loads(line) for line in journal.read_text().splitlines()]
    assert [row["sequence"] for row in rows] == list(range(1, len(rows) + 1))
    failures = [row for row in rows if row["message"] == "native_demand.execution_failed"]
    obligations = {row["obligation_id"]: row for row in snapshot["obligations"]}
    timeouts = []
    for row in failures:
        if row["fields"].get("sqlstate") != "57014":
            continue
        stack = row["exception"]["stacks"][0]
        obligation_id = next(
            (note.removeprefix("native obligation: ") for note in stack["exc_notes"]
             if note.startswith("native obligation: ")),
            None,
        )
        obligation = obligations.get(obligation_id)
        timeouts.append({
            "sequence": row["sequence"],
            "timestamp": row["timestamp"],
            "task_id": row["bindings"]["task_id"],
            "attempt": row["bindings"]["attempt"],
            "request_id": row["bindings"]["request_id"],
            "obligation_id": obligation_id,
            "sqlstate": row["fields"]["sqlstate"],
            "phase": row["fields"]["phase"],
            "server_context_functions": sorted(set(re.findall(
                r'(?:SQL|PL/pgSQL) function "?([\w.]+)', stack["exc_value"]
            ))),
            "server_context_contains_intent_insert": "INSERT INTO ops.data_completion_intent" in stack["exc_value"],
            "driver_parameter_repr_omitted_characters": [int(value) for value in re.findall(
                r"\(([0-9]+) characters truncated\)", stack["exc_value"]
            )],
            "operation_in_last_pinned_snapshot": obligation.get("operation_id") if obligation else None,
            "analyzed_scope_in_last_pinned_snapshot": obligation.get("analyzed_scope") if obligation else None,
            "selected_intent_in_last_pinned_snapshot": obligation.get("intent_id") if obligation else None,
        })
    aggregate = next(row for row in rows if row["kind"] == "unexpected_exception")
    summary = {
        "observation_date": "2026-11-19",
        "method": "Read retained bytes and settled managed manifests; no database connection or execution.",
        "book": {
            "id": BOOK,
            "outcome": manifest["outcome"],
            "cleanup": manifest["operation_account"]["cleanup"],
            "target": manifest["operation_account"]["acquired_target"],
            "demand_id": native["demand_id"],
            "journal_sha256": journal_digest,
            "journal_records": len(rows),
            "journal_collection_omitted": manifest["observations"]["omitted"],
            "failure_events": len(failures),
            "failure_phases": dict(Counter(row["fields"].get("phase") for row in failures)),
            "failure_types": dict(Counter(row["exception"]["stacks"][0]["exc_type"] for row in failures)),
            "aggregate_failure": aggregate["exception"]["stacks"][0]["exc_value"],
            "aggregate_exception_omissions": aggregate["exception"]["omissions"],
            "timeouts": timeouts,
            "snapshot_standing": native["snapshot_standing"],
            "snapshot_frontier_at": snapshot["frontier_at"],
            "receipt_acknowledgments": native["receipt_count"],
            "receipts_truncated": native["receipts_truncated"],
            "obligations_in_snapshot": len(snapshot["obligations"]),
            "discovery_populations": [
                {"id": item["population_id"], "name": item["name"], "complete": item["complete"], "members": len(item["members"])}
                for item in snapshot["populations"]
            ],
            "intent_inspection_states": dict(Counter(item["state"] for item in snapshot["completion_inspections"].values())),
            "retained_native_matches_managed": native_path.read_bytes() == (REPOSITORY / "build/ci" / BOOK / "native.json").read_bytes(),
            "not_established": [
                "Current final standing or exact identity of the narrated unresolved intent.",
                "Exact pages, sentence counts and UTF-8 completion sizes of all nine timed-out regions.",
                "Per-statement timings, lock waits, query plans, dominant cost or post-repair margin.",
                "The identity or classification of the omitted aggregate exception child.",
                "Final source/stage or provider/book qualification.",
            ],
        },
        "discovery_failure": test_receipt(DISCOVERY),
        "interrupted_fixture": test_receipt(INTERRUPTED),
    }
    (FOLDER / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"failure_events": len(failures), "statement_timeouts": len(timeouts), "journal_sha256": journal_digest}))


if __name__ == "__main__":
    main()
