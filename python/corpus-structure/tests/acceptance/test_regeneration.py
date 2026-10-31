"""Real deterministic source preparation at the CLI boundary; provider qualification is separate."""

import json
import runpy
import shutil
from pathlib import Path

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
def test_real_source_preparation_does_not_select_partial_output(
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
        seed_retained_product,
    )

    builder = runpy.run_path(str(ROOT / "fixtures/toy/build_pdf.py"))
    domains = tmp_path / "domains"
    shutil.copytree(ROOT / "domains" / domain, domains / domain)
    corpus = tmp_path / "corpus"
    if domain == "statistics":
        sections = (("Acceptance native section", ("A controlled source statement.",)),)
        original = corpus / "fixture.pdf"
        methods = domains / domain / "methods.yaml"
        values = yaml.safe_load(methods.read_text())
        values["configs"]["ingest.pdf"]["default"]["originals"] = ["fixture.pdf"]
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
    pin = seed_retained_product(
        settings,
        domain=domain,
        corpus=corpus,
        domains=domains,
        conversion=retained_document(original.read_bytes(), sections),
    )
    pin_path = tmp_path / "retained-native.json"
    pin_path.write_text(json.dumps(pin))
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
        "--native-source",
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
            *args[: args.index("--native-source")],
            *args[args.index("--native-source") + 2 :],
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
