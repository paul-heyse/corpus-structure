"""Exercise the installed source and heading guards on tampered exact task inputs."""

import argparse
import copy
import json

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.methods.contextual_embeddings import numeric_identity
from corpus_structure.semantic.contributions import contribution_identity
from corpus_structure.semantic.observations import source_python, source_value
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def validate(conn, task, body, *, probe=False):
    statement = (
        "SELECT pg_temp.nce06_heading_probe(:task, CAST(:body AS jsonb))"
        if probe
        else "SELECT ops.validate_source_contribution_report(:task, CAST(:body AS jsonb))"
    )
    conn.execute(
        text(statement),
        {"task": task, "body": json.dumps(body)},
    ).one()


def report(body):
    (report_,) = [
        operation["contextual_enrichment"]
        for operation in body["contribution_operations"]
        if "contextual_enrichment" in operation
    ]
    return report_


def refuse(conn, task, body, diagnostic):
    try:
        with conn.begin_nested():
            validate(conn, task, body, probe=True)
    except DBAPIError as exc:
        message = exc.orig.diag.message_primary
        if exc.orig.sqlstate == "23514" and diagnostic in message:
            return message
        raise
    raise ValueError(f"installed native guard accepted tampered input: {diagnostic}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=int)
    args = parser.parse_args()
    settings = Settings()
    with (
        open_runtime_engine(settings, "nce06-native-refusal", purpose="maintenance") as engine,
        engine.connect() as conn,
        conn.begin() as transaction,
    ):
        rows = conn.execute(
            text("""
                SELECT t.id,m.name,r.body FROM ops.task t
                JOIN ops.task_result r ON r.task_id=t.id
                JOIN ops.method_config c ON c.id=t.method_config_id
                JOIN ops.method m ON m.id=c.method_id
                WHERE t.run_id=:run
            """),
            {"run": args.run},
        ).mappings()
        tasks = {row["name"]: (row["id"], row["body"]) for row in rows}
        scoped, contextual = tasks["structure.scoped_relations"], tasks["retrieve.contextual"]
        for task, body in (scoped, contextual):
            validate(conn, task, body)

        # Keep the terminal task immutable. Exercise the installed validator body as a
        # connection-local probe with only the terminal-task gate bypassed.
        definition = conn.exec_driver_sql(
            "SELECT pg_get_functiondef('ops.validate_source_contribution_report(bigint,jsonb)'::regprocedure)"
        ).scalar_one()
        terminal = "IF t.status<>'running' AND NOT EXISTS("
        if definition.count(terminal) != 1:
            raise ValueError("installed terminal admission guard changed")
        conn.exec_driver_sql(
            definition.replace(
                "FUNCTION ops.validate_source_contribution_report(",
                "FUNCTION pg_temp.nce06_heading_probe(",
                1,
            ).replace(terminal, "IF false AND NOT EXISTS(", 1)
        )

        forged_target = copy.deepcopy(contextual[1])
        report(forged_target)["section_targets"][0]["pointer"] = "#/texts/999"
        omitted_witness = copy.deepcopy(contextual[1])
        candidate = report(omitted_witness)["candidate_lists"][0]
        candidate["channel_results"] = [
            channel for channel in candidate["channel_results"] if channel["channel"] != "witness"
        ]
        candidate["policy_id"] = "exact-alias-postgresql-english-cosine-rrf60-1"
        candidate["list_id"] = numeric_identity(
            "concept-candidates", {key: value for key, value in candidate.items() if key != "list_id"}
        )
        forged_token = copy.deepcopy(scoped[1])
        (subject,) = [
            row for row in forged_token["contributions"]
            if "value" in row
            and source_python(row["value"]).get("role") == "named_link_subject"
            and source_python(row["value"]).get("named_cue", {}).get("kind") == "section_citation"
        ]
        meaning = source_python(subject["value"])
        meaning["named_cue"]["tokens"]["verb"] = meaning["named_cue"]["tokens"]["section"]
        subject["value"] = source_value(meaning)
        subject["contribution_id"] = contribution_identity(subject)

        checks = {
            "forged_heading_pointer": refuse(conn, contextual[0], forged_target, "selected target inventory"),
            "omitted_complete_witness": refuse(conn, contextual[0], omitted_witness, "witness channel"),
            "changed_retained_token_binding": refuse(conn, scoped[0], forged_token, "named cue"),
        }
        transaction.rollback()
    print(json.dumps({"outcome": "passed", "run": args.run, "checks": checks}))


if __name__ == "__main__":
    main()
