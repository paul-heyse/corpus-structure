"""TR-15A bounded comparison; no installed pytest lane or generic TAP runner.

Run from the repository root with ``uv run python <this file> --attempt 001``.
Each attempt retains its own raw SQL/TAP and outcomes, including failed attempts.
"""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import traceback
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "python/corpus-structure/tests")]

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.db import extensions
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.semantic.contributions import contribution_identity
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.settings import Settings
from native_test_support import PgAdmin, principal_engine, semantic_principals, server_url
from semantic.native_record_fixtures import (
    build_record_source,
    contribution_drafts,
    contribution_envelope,
    prepare_record_source,
)
from semantic.witnessed_scenario_support import (
    authored_component_admission,
    completed_component_case,
)


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


class Comparison:
    def __init__(self, directory):
        self.directory = directory
        self.deployments = {}
        self.tap_blocked = None
        directory.mkdir(parents=True, exist_ok=False)
        (directory / "custody").mkdir()
        (directory / "publication").mkdir()
        (directory / "compare_native.py").write_bytes(Path(__file__).read_bytes())

    def record(self, event, **details):
        with (self.directory / "events.jsonl").open("a") as stream:
            stream.write(json.dumps(dict(event=event, **details), default=str) + "\n")
        print(event, flush=True)

    def identity(self, conn, purpose):
        row = conn.execute(text(
            "SELECT current_database() AS database, "
            "(SELECT oid FROM pg_database WHERE datname=current_database()) AS database_oid, "
            "current_user, session_user, current_setting('server_version') AS server_version, "
            "current_setting('port') AS port, pg_postmaster_start_time() AS server_started"
        )).mappings().one()
        deployment = self.deployments[row["database_oid"]]
        self.record("acquisition", purpose=purpose, **dict(row), deployment=deployment,
                    host=conn.connection.driver_connection.info.host)
        assert row["current_user"] == row["session_user"]
        assert deployment["revision"] == "semantic_wce_target_20261106"

    def install(self, admin, name):
        with admin.connect(name, transactional=True) as conn:
            found = conn.execute(text(extensions.FOUND)).all()
            extensions.check(found)
            assert not any(row[0] == "pgtap" for row in found)
            self.record("normal_deployment_passed", database=name, extensions=dict(found))
            observed = conn.execute(text(
                "SELECT (SELECT oid FROM pg_database WHERE datname=current_database()) AS oid, "
                "version_num AS revision FROM public.semantic_alembic_version"
            )).mappings().one()
            self.deployments[observed["oid"]] = dict(observed)
            self.record("maintenance_deployment", **dict(observed))
            conn.exec_driver_sql("CREATE EXTENSION pgtap VERSION '1.3.4'")
            assert conn.scalar(text("SELECT extversion FROM pg_extension WHERE extname='pgtap'")) == "1.3.4"
            self.record("test_only_extension_installed", database=name, version="1.3.4")

    def python_rows(self, conn, name, query, expected):
        rows = [tuple(row) for row in conn.exec_driver_sql(query)]
        assert Counter(rows) == Counter(expected)
        self.record(name, route="python", outcome="passed", rows=rows, expected=expected)

    def refusal(self, conn, name, query, expected_state, expected_message):
        try:
            with conn.begin_nested():
                conn.exec_driver_sql(query)
        except DBAPIError as error:
            state = error.orig.sqlstate
            message = error.orig.diag.message_primary
            self.record(name, route="python", sqlstate=state, message=message)
            assert state == expected_state and message == expected_message
        else:
            raise AssertionError("expected native refusal")

    def tap(self, conn, name, cases):
        """Finite literal transcript expectations, not a reusable TAP parser."""
        statements = ["SELECT public.plan(%d)" % len(cases)]
        statements += [query for query, _ in cases]
        statements += ["SELECT * FROM public.finish()"]
        (self.directory / (name + ".sql")).write_text(
            "BEGIN;\n" + ";\n".join(statements) + ";\nROLLBACK;\n"
        )
        if self.tap_blocked is not None:
            self.record(name, route="pgtap_driver", outcome="not_run",
                        missing_prerequisite=self.tap_blocked, plan=len(cases))
            return
        transcript = []
        savepoint = conn.begin_nested()
        try:
            for query in statements:
                transcript += [str(row[0]) for row in conn.exec_driver_sql(query)]
        except DBAPIError as error:
            (self.directory / (name + ".error.txt")).write_text(str(error))
            (self.directory / (name + ".tap")).write_text("\n".join(transcript))
            self.record(name, route="pgtap_driver", outcome="blocked",
                        sqlstate=error.orig.sqlstate, message=error.orig.diag.message_primary,
                        plan=len(cases), transcript=transcript)
            if error.orig.sqlstate != "42501" or "temporary tables" not in str(error.orig):
                raise
            self.tap_blocked = "purpose writer lacks database TEMP privilege required by pgTAP plan()"
            return
        finally:
            savepoint.rollback()
        (self.directory / (name + ".tap")).write_text("\n".join(transcript) + "\n")
        assert transcript[0] == f"1..{len(cases)}"
        # Each selected assertion's actual first TAP line must equal its literal expectation.
        # Diagnostic comments and finish summary remain preserved in the raw transcript.
        for (_, expected), actual in zip(cases, transcript[1:], strict=False):
            assert actual.splitlines()[0] == expected, (actual, expected)
        assert len(transcript) >= len(cases) + 1
        self.record(name, route="pgtap_driver", outcome="passed", plan=len(cases),
                    transcript=transcript)


def complete_sql(case, envelope):
    return (
        f"SELECT ops.complete_task({case.task}::bigint,{case.held.attempt}::bigint,"
        f"'records'::text,'[]'::jsonb,'done'::text,'null'::jsonb,"
        f"{literal(json.dumps(envelope))}::jsonb)"
    )


def custody(probe, admin, settings, template, token):
    name = "cs_sem_tr15_custody_" + token
    with admin.database(name, template.name, policy=template.policy) as maintenance:
        probe.install(admin, name)
        writer = principal_engine(settings, "write", name)
        try:
            case = build_record_source(maintenance, writer, probe.directory / "custody",
                                       prepare_record_source())
            result = contribution_drafts(case)
            row = deepcopy(result.contributions[1])
            aid = row["anchors"][0]["anchor_id"]
            row["computation_dependencies"] = ("retained-annotation",)
            row["component"] = dict(
                protocol="witnessed-component-1", kind="located_role", question="inspect_cell",
                question_version="1", scope="native-cell", interpretation="unassessed",
                dependencies=("retained-annotation",),
                bases=(dict(kind="matched_cue", dependencies=("retained-annotation",), anchor_ids=(aid,)),),
                rule="native-cell-control", variant="named",
                roles=(dict(role="value", anchor_ids=(aid,), head_token=0,
                            expansion="exact", outcome="complete"),),
            )
            row["contribution_id"] = contribution_identity(row)
            result = replace(result, contributions=(result.contributions[0], row))
            raw = contribution_envelope(case, result)
            invalid = deepcopy(raw)
            invalid["contributions"][1]["component"]["bases"][0]["dependencies"] = ["unavailable-premise"]
            invalid["contributions"][1]["contribution_id"] = contribution_identity(invalid["contributions"][1])
            good, bad = complete_sql(case, raw), complete_sql(case, invalid)
            with writer.begin() as conn:
                probe.identity(conn, "write")
                # The exact diagnostic is checked independently by each assertion route.
                probe.refusal(conn, "invalid_basis", bad, "23514", "component basis has unavailable dependency or source anchor")
                probe.tap(conn, "custody-refusal", [
                    (f"SELECT public.throws_ok({literal(bad)},'23514','component basis has unavailable dependency or source anchor','invalid basis')",
                     "ok 1 - invalid basis"),
                    (f"SELECT public.throws_ok({literal(bad)},'42501',NULL,'wrong SQLSTATE detected')",
                     "not ok 2 - wrong SQLSTATE detected"),
                ])
                conn.exec_driver_sql(good)
                query = ("SELECT c->'component'->'roles'->0->>'role' FROM ops.task_result r "
                         "CROSS JOIN LATERAL jsonb_array_elements(r.body->'contributions') c "
                         f"WHERE r.task_id={case.task} AND c ? 'component'")
                probe.python_rows(conn, "located_component", query, [("value",)])
                probe.tap(conn, "custody-rows", [
                    (f"SELECT public.bag_eq({literal(query)},$$VALUES ('value'::text)$$,'located component')",
                     "ok 1 - located component"),
                ])
        finally:
            writer.dispose()
    probe.record("owned_clone_disposed", database=name, exists=admin.exists(name))


def publication(probe, admin, settings, template, token):
    name = "cs_sem_tr15_publication_" + token
    with admin.database(name, template.name, policy=template.policy) as maintenance:
        probe.install(admin, name)
        writer = principal_engine(settings, "write", name)
        evaluator = principal_engine(settings, "evaluate", name)
        try:
            case = build_record_source(maintenance, writer, probe.directory / "publication",
                                       prepare_record_source())
            completed = completed_component_case(case, probe.directory / "publication")
            with evaluator.connect() as conn:
                probe.identity(conn, "evaluate")
            authored = authored_component_admission(completed, evaluator)
            run = completed.produce_component(structural_admission=(authored.admission,))
            finalize_bound_run(writer, run.run_id, "tr15-component-publication")
            # Independently authored expected public statement; no production projector.
            source = completed.source
            citation = dict(source=dict(project_id="private-records",
                native_product_key=source.native_product_key,
                native_content_digest=source.native_content_digest,
                projection_digest=source.projection_digest, recipe_digest=source.recipe_digest,
                coordinate_version=2), start=0, end=2, text="12", scope="controlled-source")
            expected = dict(version="structural-public-statement-2", kind="definition_components",
                scope="controlled-source", coverage_limits=[], exclusions=[],
                definition_component=dict(term=citation, content=citation,
                    interpretation="definition", scope="controlled-source"))
            query = ("SELECT a.policy_id, a.statement_json FROM data.structural_assertion a "
                     "JOIN ops.task t ON t.id=a.selected_task_id " + f"WHERE t.run_id={run.run_id}")
            expected_row = ("independent-definition-component-1", canonical_bytes(expected).decode())
            expected_sql = "VALUES ('independent-definition-component-1'::text," + literal(expected_row[1]) + "::text)"
            with writer.begin() as conn:
                probe.identity(conn, "write")
                probe.python_rows(conn, "component_publication", query, [expected_row])
                probe.tap(conn, "publication-rows", [
                    (f"SELECT public.bag_eq({literal(query)},{literal(expected_sql)},'exact public component')",
                     "ok 1 - exact public component"),
                    (f"SELECT public.bag_eq({literal(query + ' UNION ALL ' + query)},{literal(expected_sql)},'duplicate member detected')",
                     "not ok 2 - duplicate member detected"),
                    (f"SELECT public.bag_eq({literal(query + ' AND false')},{literal(expected_sql)},'missing member detected')",
                     "not ok 3 - missing member detected"),
                ])
                for label, mutant in (("duplicate", query + " UNION ALL " + query), ("missing", query + " AND false")):
                    actual = [tuple(row) for row in conn.exec_driver_sql(mutant)]
                    assert Counter(actual) != Counter([expected_row])
                    probe.record(label + "_member_detected", route="python", outcome="passed", rows=actual)
            wrong = completed.produce_component(structural_admission=(dict(
                authored.admission, policy_id="independent-witnessed-applicability-1"),))
            try:
                finalize_bound_run(writer, wrong.run_id, "tr15-refused-applicability")
            except Exception as error:
                probe.record("stronger_applicability_application_refusal", kind=type(error).__name__,
                             message=str(error).splitlines()[0])
                if isinstance(error, DBAPIError):
                    probe.record("stronger_applicability_sql_context", statement=error.statement,
                                 parameters=repr(error.params), sqlstate=error.orig.sqlstate,
                                 primary=error.orig.diag.message_primary)
                with writer.begin() as conn:
                    probe.identity(conn, "write")
                    cut = conn.scalar(text("SELECT id FROM ops.input_cut WHERE run_id=:run AND final"),
                                      {"run": wrong.run_id})
                    assert cut is not None
                    refused = ("SELECT data.structural_publication_candidates('private-records'," +
                               literal(case.prepared.release_id) + f",{wrong.run_id}::bigint,{cut}::bigint)")
                    probe.refusal(conn, "stronger_applicability", refused, "23514",
                                  "structural publication policy is not released")
                    probe.tap(conn, "publication-refusal", [
                        (f"SELECT public.throws_ok({literal(refused)},'23514','structural publication policy is not released','stronger applicability refused')",
                         "ok 1 - stronger applicability refused"),
                    ])
            else:
                raise AssertionError("stronger applicability unexpectedly admitted")
        finally:
            writer.dispose()
            evaluator.dispose()
    probe.record("owned_clone_disposed", database=name, exists=admin.exists(name))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", required=True)
    args = parser.parse_args()
    probe = Comparison(Path(__file__).parent / "raw" / ("attempt-" + args.attempt))
    paths = [Path(__file__), ROOT / "uv.lock", ROOT / "scripts/native_test_support.py",
             ROOT / "python/corpus-structure/tests/semantic/witnessed_scenario_support.py",
             ROOT / "python/corpus-structure/tests/semantic/native_record_fixtures.py"]
    probe.record("source_context", head=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                 hashes={str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest() for p in paths},
                 dirty=subprocess.check_output(["git", "status", "--short"], text=True),
                 tools=subprocess.check_output(["pg_prove", "--version"], text=True).strip())
    settings = Settings()
    admin = PgAdmin(server_url(settings), settings.database.template, settings=settings)
    admin.check()
    admin.check_roles(semantic_principals())
    token = uuid4().hex[:12]
    template_name = "cs_sem_tr15_head_" + token
    try:
        with admin.semantic_template(template_name) as template:
            custody(probe, admin, settings, template, token)
            publication(probe, admin, settings, template, token)
    except BaseException as error:
        probe.record("attempt_failed", kind=type(error).__name__, message=str(error).splitlines()[0])
        (probe.directory / "failure.txt").write_text(traceback.format_exc())
        raise
    finally:
        probe.record("template_disposal", database=template_name, exists=admin.exists(template_name))
    probe.record("comparison_blocked" if probe.tap_blocked else "comparison_passed",
                 missing_prerequisite=probe.tap_blocked)


if __name__ == "__main__":
    main()
