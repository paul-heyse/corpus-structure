"""Real deterministic source preparation at the CLI boundary; provider qualification is separate."""

import json
import runpy
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from sqlalchemy import select, text
from typer.testing import CliRunner

from corpus_structure.cli.app import app
from corpus_structure.cli.output import CliState
from corpus_structure.semantic.metadata import table
from corpus_structure.settings import Settings

ROOT = Path(__file__).resolve().parents[4]


def retained_integrated_cli(semantic_db_engine, tmp_path, monkeypatch, domain, scope_name):
    settings = Settings(
        ci_results=tmp_path / "cli-results",
        database={
            "url": semantic_db_engine.url.set(
                drivername="postgresql", username="corpus_sem_writer"
            ).render_as_string(hide_password=False)
        },
        paths={"data_dir": tmp_path / "data", "model_cache": tmp_path / "models"},
    )
    from pdf_acceptance_support import (
        install_no_inference_boundary,
        retained_document,
        seed_retained_integrated_product,
    )

    from ..semantic.pdf_integration_support import IMAGE, RESPONSE, observation

    builder = runpy.run_path(str(ROOT / "fixtures/toy/build_pdf.py"))
    domains = tmp_path / "domains"
    shutil.copytree(ROOT / "domains" / domain, domains / domain)
    corpus = tmp_path / "corpus"
    if domain == "statistics":
        sections = (("Acceptance native section", ("A controlled source statement.",)),)
        original = corpus / "fixture.pdf"
        methods = domains / domain / "methods.yaml"
        values = yaml.safe_load(methods.read_text())
        for method in ("ingest.pdf", "ingest.pdf_integrated"):
            values["configs"][method]["default"]["originals"] = ["fixture.pdf"]
        methods.write_text(yaml.safe_dump(values, sort_keys=False))
        (domains / domain / "slices.yaml").write_text(
            yaml.safe_dump(
                {
                    "version": "0.2.0",
                    "slices": {
                        "acceptance-native": [{"native_sections": ["Acceptance native section"]}]
                    },
                }
            )
        )
    else:
        sections = builder["SECTIONS"]
        original = corpus / "toy.pdf"
    builder["write_pdf"](original, sections)
    monkeypatch.setattr("corpus_structure.schema.pack.DOMAINS", domains)
    install_no_inference_boundary(monkeypatch, tmp_path / "no-model-assets")
    conversion = retained_document(original.read_bytes(), sections)
    pin = seed_retained_integrated_product(
        settings,
        domain=domain,
        corpus=corpus,
        domains=domains,
        conversion=conversion,
        observation=observation(
            SimpleNamespace(original=original.read_bytes(), recipe=conversion.recipe),
            pass_role="B",
        ),
        raw_response=RESPONSE,
        artifacts=(IMAGE, RESPONSE),
    )
    pin_path = tmp_path / "retained-integrated.json"
    pin_path.write_text(json.dumps(pin))

    args = [
        "regenerate",
        "--domain",
        domain,
        "--project",
        "acceptance",
        "--corpus",
        str(corpus),
        "--scope",
        scope_name,
        "--integrated-source",
        str(pin_path),
        "--prepare-only",
        "--json",
    ]
    return SimpleNamespace(
        settings=settings, domains=domains, corpus=corpus, pin=pin, pin_path=pin_path, args=args
    )


@pytest.mark.parametrize(
    "domain,scope_name",
    [("statistics", "acceptance-native"), ("toy", "transfer")],
)
def test_retained_integrated_cli_lifecycle(
    semantic_db_engine, semantic_writer_engine, tmp_path, monkeypatch, domain, scope_name
):
    case = retained_integrated_cli(semantic_db_engine, tmp_path, monkeypatch, domain, scope_name)
    settings, domains, pin = case.settings, case.domains, case.pin
    pin_path = case.pin_path

    def forbidden_reselection(*args, **kwargs):
        raise AssertionError("retained integrated input must not repeat reconciliation")

    monkeypatch.setattr(
        "corpus_structure.ingest.pdf_reconciliation.select_pdf_integration", forbidden_reselection
    )
    with semantic_db_engine.connect() as conn:
        before = conn.execute(
            text(
                "SELECT table_schema,table_name FROM information_schema.tables "
                "WHERE table_schema IN ('data','sem','kb','ops','eval') ORDER BY 1,2"
            )
        ).all()
    args = case.args
    result = CliRunner().invoke(app, args, obj=CliState(settings_factory=lambda: settings))
    assert result.exit_code == 0, (result.output, result.exception)
    report = json.loads(result.stdout)
    assert report["characterization_views"]
    assert report["status"] == "prepared" and report["selected_generation"] is None
    from corpus_structure.orchestrate.characterization import characterization_sources
    from corpus_structure.semantic.characterization_store import read_view
    from corpus_structure.semantic.product_reference import ProductReference

    with semantic_writer_engine.connect() as conn:
        source_runs = {
            source.run_id
            for selected in report["characterization_views"]
            for reference in (ProductReference(**selected),)
            for source in characterization_sources(
                conn, reference, read_view(conn, reference), project_id="acceptance"
            )
        }
    assert report["run_id"] not in source_runs
    with semantic_db_engine.connect() as conn:
        project = conn.execute(select(table("data.project"))).mappings().one()
        assert project["selected_result_run_id"] is None and project["active_release_id"] is None
        assert (
            conn.scalar(
                select(table("ops.run").c.status).where(table("ops.run").c.id == report["run_id"])
            )
            == "running"
        )
        cut = table("ops.input_cut")
        assert (
            conn.scalar(
                select(cut.c.id).where(
                    cut.c.run_id == report["run_id"], cut.c.name == "source-ready"
                )
            )
            is not None
        )
        tasks = table("ops.task")
        task_identities = conn.execute(
            select(tasks.c.id, tasks.c.method_config_id, tasks.c.unit_key, tasks.c.input_hash)
            .where(tasks.c.run_id == report["run_id"])
            .order_by(tasks.c.id)
        ).all()
        states = (
            conn.execute(select(tasks.c.status).where(tasks.c.run_id == report["run_id"]))
            .scalars()
            .all()
        )
        assert "awaiting_agent" in states
        configs, methods = table("ops.method_config"), table("ops.method")
        source_config = conn.execute(
            select(configs.c.params)
            .join(tasks, tasks.c.method_config_id == configs.c.id)
            .join(methods, methods.c.id == configs.c.method_id)
            .where(tasks.c.run_id.in_(source_runs), methods.c.name == "ingest.pdf_integrated")
        ).scalar_one()
        assert source_config["integrated_product"] == pin
        assert source_config["native_product"] is None
        views = table("kb.source_view")
        selected_pins = conn.execute(
            select(
                views.c.native_task_id, views.c.native_product_key, views.c.native_content_digest
            ).distinct()
        ).all()
        assert selected_pins == [(pin["task_id"], pin["product_key"], pin["content_digest"])]
        after = conn.execute(
            text(
                "SELECT table_schema,table_name FROM information_schema.tables "
                "WHERE table_schema IN ('data','sem','kb','ops','eval') ORDER BY 1,2"
            )
        ).all()
        assert (
            after == before
        )  # Domain class and relation additions are registry data, no per-type DDL.
    # Preparation resumption uses the archived release and the original task identities.
    resumed = CliRunner().invoke(
        app,
        [
            "run",
            "resume",
            str(report["run_id"]),
            "--project",
            "acceptance",
            "--prepare-only",
            "--json",
        ],
        obj=CliState(settings_factory=lambda: settings),
    )
    assert resumed.exit_code == 0, (resumed.output, resumed.exception)
    assert json.loads(resumed.stdout)["run_id"] == report["run_id"]

    with semantic_db_engine.connect() as conn:
        tasks = table("ops.task")
        assert (
            conn.execute(
                select(tasks.c.id, tasks.c.method_config_id, tasks.c.unit_key, tasks.c.input_hash)
                .where(tasks.c.run_id == report["run_id"])
                .order_by(tasks.c.id)
            ).all()
            == task_identities
        )

    if domain == "toy":
        # Controlled empty reports exercise the actual submission/finalization lifecycle.
        # They establish orchestration behavior only, with no provider/extraction claim.
        from corpus_structure.intervene.semantic_server import SemanticAgentSession
        from corpus_structure.orchestrate.commands import finalize_bound_run
        from corpus_structure.semantic.authored_sql import (
            admit_archived_sql,
            analyze_archived_sql,
            has_authored_sql,
        )
        from corpus_structure.semantic.publication import admit_release
        from corpus_structure.semantic.regeneration import prepare_pack
        from corpus_structure.semantic.releases import activate_release, persist_release
        from corpus_structure.semantic.runtime import open_runtime_engine

        run_id = report["run_id"]
        with open_runtime_engine(
            settings, "acceptance-controlled-completion", purpose="write"
        ) as engine:
            session = SemanticAgentSession(engine, run_id)
            completed = 0
            while leased := session.next("extract", 1).tasks:
                for task in leased:
                    active = session.active(task.task_id)
                    for part in active.manifest()["parts"]:
                        for page in range(1, part["pages"] + 1):
                            assert active.read(part["name"], page)
                    checked = active.check(
                        {"unit_ref": task.unit_key, "entities": [], "claims": []},
                        packet_hash=active.packet.hash,
                        schema_hash=active.packet.schema_hash,
                    )
                    with engine.begin() as conn:
                        result = active.commit(conn, checked)
                    assert result.disposition == "completed_accepted"
                    completed += 1
            assert completed > 0
            output = f"result:acceptance:{run_id}"
            finalize_bound_run(engine, run_id, output)

        # Activate a separately admitted release while the completed result stays unselected.
        guideline = domains / domain / "guideline.md"
        guideline.write_text(guideline.read_text() + "\nControlled alternate release.\n")
        bundle, dependencies, profile, alternate = prepare_pack(domains / domain)
        assert alternate.release_id != report["release_id"]
        with open_runtime_engine(settings, "acceptance-alternate-admit", purpose="admit") as engine:
            with engine.begin() as conn:
                persist_release(conn, bundle, dependencies, profile, alternate)
                if not has_authored_sql(alternate):
                    admit_release(alternate, connection=conn)
            with (
                open_runtime_engine(
                    settings, "acceptance-alternate-read", purpose="read"
                ) as reader,
                reader.connect() as conn,
            ):
                analyzed = analyze_archived_sql(conn, alternate.release_id)
            with engine.begin() as conn:
                admit_archived_sql(conn, alternate.release_id, analyzed=analyzed)
                admit_release(alternate, connection=conn)
                activate_release(
                    conn,
                    "acceptance",
                    alternate.release_id,
                    expected_parent=None,
                    expected_generation=0,
                    sql_admissions=analyzed,
                )

        def forbidden_provider(*args, **kwargs):
            raise AssertionError("completed run resumption must not invoke a provider")

        monkeypatch.setattr("corpus_structure.intervene.automated.extract_run", forbidden_provider)
        select_args = [
            "run",
            "resume",
            str(run_id),
            "--project",
            "acceptance",
            "--select-result",
            "--activate-release",
            "--json",
        ]
        selected = CliRunner().invoke(
            app, select_args, obj=CliState(settings_factory=lambda: settings)
        )
        assert selected.exit_code == 0, (selected.output, selected.exception)
        selection = json.loads(selected.stdout)
        assert selection["status"] == "complete" and selection["provider"] is None
        assert selection["release_id"] == report["release_id"]
        assert selection["output_realization_id"] == output
        with semantic_db_engine.connect() as conn:
            project = conn.execute(select(table("data.project"))).mappings().one()
            assert project["active_release_id"] == report["release_id"]
            assert project["selected_result_run_id"] == run_id
            assert project["generation"] == selection["selected_generation"]
        repeated = CliRunner().invoke(
            app, select_args, obj=CliState(settings_factory=lambda: settings)
        )
        assert repeated.exit_code == 0, (repeated.output, repeated.exception)
        assert (
            json.loads(repeated.stdout)["selected_generation"] == selection["selected_generation"]
        )

        # A later release activation preserves the selected result pointer. Resuming must
        # restore its release even when the desired run is already selected.
        with (
            open_runtime_engine(settings, "acceptance-reactivate", purpose="admit") as engine,
            engine.begin() as conn,
        ):
            activate_release(
                conn,
                "acceptance",
                alternate.release_id,
                expected_parent=report["release_id"],
                expected_generation=selection["selected_generation"],
                sql_admissions=analyzed,
            )
        restored = CliRunner().invoke(
            app, select_args, obj=CliState(settings_factory=lambda: settings)
        )
        assert restored.exit_code == 0, (restored.output, restored.exception)
        restored_report = json.loads(restored.stdout)
        assert restored_report["semantic_impact"]["before_release"] == alternate.release_id
        assert restored_report["semantic_impact"]["after_release"] == report["release_id"]
        assert any("Native admission" in item for item in restored_report["compatibility_advice"])
        with semantic_db_engine.connect() as conn:
            project = conn.execute(select(table("data.project"))).mappings().one()
            assert project["active_release_id"] == report["release_id"]
            assert project["selected_result_run_id"] == run_id
            assert project["generation"] == selection["selected_generation"] + 2
        writer_only = settings.model_copy(
            update={
                "database": settings.database.model_copy(
                    update={"admission_url": "postgresql://nonexistent_ingest_control@"}
                ),
                "runtime": settings.runtime.model_copy(update={"default_project": "acceptance"}),
            }
        )
        ingested = CliRunner().invoke(
            app,
            ["ingest", "--integrated-source", str(pin_path), "--json"],
            obj=CliState(settings_factory=lambda: writer_only),
        )
        assert ingested.exit_code == 0, (ingested.output, ingested.exception)
        prepared_only = json.loads(ingested.stdout)
        assert prepared_only["release_id"] == report["release_id"]
        assert prepared_only["realization_id"] == output
        assert prepared_only["status"] == "source_ready" and prepared_only["cut_id"] > 0


@pytest.mark.parametrize("failure_kind", ["failure", "interruption"])
def test_initial_source_failure_retains_committed_run(
    semantic_db_engine, tmp_path, monkeypatch, failure_kind
):
    from structlog.contextvars import get_contextvars

    from corpus_structure.cli.managed import ResultStore
    from corpus_structure.ingest.pdf_recognition_methods import IngestPdfIntegrated
    from corpus_structure.orchestrate import commands, semantic
    from corpus_structure.orchestrate.liveness import observe_supervisor

    case = retained_integrated_cli(semantic_db_engine, tmp_path, monkeypatch, "toy", "transfer")
    store = ResultStore(case.settings.ci_results)
    baseline_context = get_contextvars()
    runs = table("ops.run")
    with semantic_db_engine.connect() as conn:
        before = set(conn.scalars(select(runs.c.id)))
    created, selected, closed = [], [], []
    native_start = commands.start_bound_run
    native_groups = semantic._source_step_groups
    native_close = IngestPdfIntegrated.close
    primary = (
        RuntimeError("controlled initial source failure")
        if failure_kind == "failure"
        else KeyboardInterrupt("controlled initial source interruption")
    )

    def start(*args, **kwargs):
        callback = kwargs["on_created"]

        def acquired(identity):
            with semantic_db_engine.connect() as conn:
                row = conn.execute(
                    select(runs.c.id, runs.c.project_id, runs.c.release_id).where(
                        runs.c.id == identity.run_id
                    )
                ).one()
            assert (identity.run_id, identity.project, identity.release_id) == tuple(row)
            assert identity.run_id not in before
            created.append(identity)
            callback(identity)

        kwargs["on_created"] = acquired
        return native_start(*args, **kwargs)

    def groups(*args, **kwargs):
        assert len(created) == 1
        (item,) = store.list(None, 20, "regenerate").results
        identity = created[0]
        expected = {
            "run_id": identity.run_id,
            "project": "acceptance",
            "release_id": identity.release_id,
        }
        assert item.details["observation_bindings"] == expected
        assert item.stage == "source_running" and item.outcome == "running"
        assert {key: get_contextvars().get(key) for key in expected} == expected
        selected.append(identity.run_id)
        return native_groups(*args, **kwargs)

    def stop(self, units, cfg, ctx):
        assert selected and len(created) == 1
        raise primary

    def close(self):
        closed.append(self.name)
        return native_close(self)

    monkeypatch.setattr(commands, "start_bound_run", start)
    monkeypatch.setattr(semantic, "_source_step_groups", groups)
    monkeypatch.setattr(IngestPdfIntegrated, "run", stop)
    monkeypatch.setattr(IngestPdfIntegrated, "close", close)
    result = CliRunner().invoke(app, case.args, obj=CliState(lambda: case.settings))
    assert result.exit_code == (1 if failure_kind == "failure" else 130), result.output
    if failure_kind == "failure":
        assert result.exception is primary
    assert get_contextvars() == baseline_context
    assert len(created) == 1 and "ingest.pdf_integrated" in closed
    with semantic_db_engine.connect() as conn:
        after = set(conn.scalars(select(runs.c.id))) - before
        assert after == {created[0].run_id}
        native = conn.execute(
            select(runs.c.id, runs.c.project_id, runs.c.release_id, runs.c.status).where(
                runs.c.id == created[0].run_id
            )
        ).one()
        assert native.status == ("failed" if failure_kind == "failure" else "cancelled")
        assert observe_supervisor(conn, native.id)[0] is False
    (item,) = store.list(None, 20, "regenerate").results
    assert item.outcome == ("failed" if failure_kind == "failure" else "interrupted")
    inspected = CliRunner().invoke(
        app,
        ["results", "inspect", item.id, "--json"],
        obj=CliState(lambda: case.settings),
    )
    assert inspected.exit_code == 0, inspected.output
    report = json.loads(inspected.stdout)
    assert report["native"]["availability"] == "available", report["native"]
    assert report["native"]["run"]["run_id"] == native.id
    assert report["native"]["run"]["status"] == native.status
    assert report["bindings"] == {
        "invocation_id": item.id,
        "run_id": native.id,
        "project": native.project_id,
        "release_id": native.release_id,
        "provider_invocation": None,
        "task_id": None,
        "attempt": None,
        "request_id": None,
        "method": None,
    }
    assert any(action["command"] == f"ci status {native.id}" for action in report["next_actions"])
    assert not any(action["kind"] == "recover_result" for action in report["next_actions"])


@pytest.mark.parametrize("source_fails", [False, True])
def test_initial_source_diagnostic_binding_failure_preserves_native_outcome(
    semantic_db_engine, tmp_path, monkeypatch, source_fails
):
    from structlog.contextvars import get_contextvars

    from corpus_structure.cli.managed import Invocation, ResultStore
    from corpus_structure.ingest.pdf_recognition_methods import IngestPdfIntegrated

    case = retained_integrated_cli(semantic_db_engine, tmp_path, monkeypatch, "toy", "transfer")
    before_context = get_contextvars()
    binding_calls, calls = [], []
    primary = RuntimeError("controlled source failure after unavailable diagnostics")
    native_run = IngestPdfIntegrated.run

    def unavailable(self, **bindings):
        binding_calls.append(bindings)
        raise OSError("controlled observation publication failure")

    def run(self, units, cfg, ctx):
        calls.append(self.name)
        if source_fails:
            raise primary
        return native_run(self, units, cfg, ctx)

    monkeypatch.setattr(Invocation, "bind_observations", unavailable)
    monkeypatch.setattr(IngestPdfIntegrated, "run", run)
    result = CliRunner().invoke(app, case.args, obj=CliState(lambda: case.settings))
    assert result.exit_code == int(source_fails), result.output
    assert calls == ["ingest.pdf_integrated"]
    assert len({call["run_id"] for call in binding_calls}) == len(binding_calls)
    if source_fails:
        assert len(binding_calls) == 1
        assert result.exception is primary
    else:
        assert len(binding_calls) > 1
        report = json.loads(result.stdout)
        assert report["status"] == "prepared"
        assert report["run_id"] == binding_calls[-1]["run_id"]
    assert get_contextvars() == before_context
    (item,) = ResultStore(case.settings.ci_results).list(None, 20, "regenerate").results
    assert item.outcome == ("failed" if source_fails else "passed")
    assert item.details["observation_binding_unavailable"] == "OSError"
    assert "observation_bindings" not in item.details
    assert "Native run observation binding unavailable: OSError" in result.stderr
    with semantic_db_engine.connect() as conn:
        runs = table("ops.run")
        states = dict(
            conn.execute(
                select(runs.c.id, runs.c.status).where(
                    runs.c.id.in_([call["run_id"] for call in binding_calls])
                )
            )
            .tuples()
            .all()
        )
        if source_fails:
            assert states[binding_calls[0]["run_id"]] == "failed"
        else:
            assert states[binding_calls[0]["run_id"]] == "finished"
            primary_runs = [call["run_id"] for call in binding_calls[1:-1]]
            assert primary_runs and all(states[identity] == "running" for identity in primary_runs)
            tasks = table("ops.task")
            assert set(
                conn.scalars(select(tasks.c.status).where(tasks.c.run_id.in_(primary_runs)))
            ) <= {"done", "empty", "reused"}
            assert states[binding_calls[-1]["run_id"]] == "running"


@pytest.mark.parametrize(
    "options,message",
    [
        (("--native-source", "PIN", "--integrated-source", "PIN"), "mutually exclusive"),
        (
            ("--native-source", "PIN", "--resume-run", "1"),
            "retains its original source input binding",
        ),
        (
            ("--integrated-source", "PIN", "--resume-run", "1"),
            "retains its original source input binding",
        ),
    ],
)
def test_source_input_roles_are_mutually_exclusive(tmp_path, options, message):
    pin = tmp_path / "pin.json"
    pin.write_text("{}")
    args = ["regenerate", "--domain", "toy", "--corpus", str(tmp_path), "--prepare-only", "--json"]
    result = CliRunner().invoke(
        app,
        [*args, *(str(pin) if value == "PIN" else value for value in options)],
        obj=CliState(settings_factory=Settings),
    )
    assert result.exit_code != 0
    assert message in result.stdout


@pytest.mark.parametrize("option", ["--native-source", "--integrated-source"])
def test_source_pin_requires_the_typed_contract(tmp_path, option):
    pin = tmp_path / "pin.json"
    pin.write_text('{"task_id":"not-an-integer","product_key":"untyped"}')
    result = CliRunner().invoke(
        app,
        [
            "regenerate",
            "--domain",
            "toy",
            "--corpus",
            str(tmp_path),
            option,
            str(pin),
            "--prepare-only",
            "--json",
        ],
        obj=CliState(settings_factory=Settings),
    )
    assert result.exit_code != 0
    assert "source product pin" in result.stdout


def test_repeated_default_preparation_reuses_exact_primary_custody(
    semantic_db_engine, tmp_path, monkeypatch
):
    from corpus_structure.orchestrate.phase0 import CHARACTERIZATION_METHODS

    case = retained_integrated_cli(
        semantic_db_engine, tmp_path, monkeypatch, "statistics", "acceptance-native"
    )
    runner = CliRunner()
    state = CliState(settings_factory=lambda: case.settings)
    first = runner.invoke(app, case.args, obj=state)
    assert first.exit_code == 0, (first.output, first.exception)
    original = json.loads(first.stdout)
    assert original["characterization_views"]

    def no_repeated_inference(*args, **kwargs):
        pytest.fail("unchanged automatic preparation repeated a primary producer")

    for method in CHARACTERIZATION_METHODS:
        if method.name != "text.compose_view":
            monkeypatch.setattr(type(method), "run", no_repeated_inference)
    repeated = runner.invoke(app, case.args, obj=state)
    assert repeated.exit_code == 0, (repeated.output, repeated.exception)
    current = json.loads(repeated.stdout)
    assert current["run_id"] != original["run_id"]
    assert current["characterization_views"] == original["characterization_views"]
