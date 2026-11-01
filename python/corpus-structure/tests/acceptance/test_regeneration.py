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


@pytest.mark.parametrize(
    "domain,scope_name",
    [("statistics", "acceptance-native"), ("toy", "transfer")],
)
def test_retained_integrated_cli_lifecycle(
    semantic_db_engine, tmp_path, monkeypatch, domain, scope_name
):
    settings = Settings(
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

    from ..semantic.test_pdf_integrated import IMAGE, RESPONSE, observation

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
    result = CliRunner().invoke(app, args, obj=CliState(settings_factory=lambda: settings))
    assert result.exit_code == 0, (result.output, result.exception)
    report = json.loads(result.stdout)
    assert report["status"] == "prepared" and report["selected_generation"] is None
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
            .where(tasks.c.run_id == report["run_id"], methods.c.name == "ingest.pdf_integrated")
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
            *args[: args.index("--integrated-source")],
            *args[args.index("--integrated-source") + 2 :],
            "--resume-run",
            str(report["run_id"]),
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
            "regenerate",
            "--domain",
            domain,
            "--project",
            "acceptance",
            "--corpus",
            str(corpus),
            "--resume-run",
            str(run_id),
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
        with semantic_db_engine.connect() as conn:
            project = conn.execute(select(table("data.project"))).mappings().one()
            assert project["active_release_id"] == report["release_id"]
            assert project["selected_result_run_id"] == run_id
            assert project["generation"] == selection["selected_generation"] + 2


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
    args = [
        "regenerate", "--domain", "toy", "--corpus", str(tmp_path), "--prepare-only", "--json"
    ]
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
            "regenerate", "--domain", "toy", "--corpus", str(tmp_path), option,
            str(pin), "--prepare-only", "--json",
        ],
        obj=CliState(settings_factory=Settings),
    )
    assert result.exit_code != 0
    assert "source product pin" in result.stdout
