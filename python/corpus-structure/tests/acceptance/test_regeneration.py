"""Real deterministic source preparation at the CLI boundary; provider qualification is separate."""

import json
from pathlib import Path

import pytest
from sqlalchemy import select, text
from typer.testing import CliRunner

from corpus_structure.cli.app import app
from corpus_structure.cli.output import CliState
from corpus_structure.semantic.metadata import table
from corpus_structure.settings import Settings

ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.parametrize("domain,slice_name,source", [
    ("statistics", "trace", "fixtures/trace/corpus"),
    ("toy", "transfer", "fixtures/toy/corpus"),
])
def test_real_source_preparation_does_not_select_partial_output(semantic_db_engine, tmp_path, domain, slice_name, source):
    settings = Settings(database={"url": semantic_db_engine.url.set(drivername="postgresql", username="corpus_sem_writer").render_as_string(hide_password=False)},
                        paths={"data_dir": tmp_path / "data", "model_cache": tmp_path / "models"})
    with semantic_db_engine.connect() as conn:
        before = conn.execute(text("SELECT table_schema,table_name FROM information_schema.tables WHERE table_schema IN ('data','sem','kb','ops','eval') ORDER BY 1,2")).all()
    args = ["regenerate", "--domain", domain, "--project", "acceptance", "--corpus", str(ROOT / source),
            "--slice", slice_name, "--prepare-only", "--json"]
    result = CliRunner().invoke(app, args, obj=CliState(settings_factory=lambda: settings))
    assert result.exit_code == 0, (result.output, result.exception)
    report = json.loads(result.stdout)
    assert report["status"] == "prepared" and report["selected_generation"] is None
    with semantic_db_engine.connect() as conn:
        project = conn.execute(select(table("data.project"))).mappings().one()
        assert project["selected_result_run_id"] is None and project["active_release_id"] is None
        assert conn.scalar(select(table("ops.run").c.status).where(table("ops.run").c.id == report["run_id"])) == "running"
        states = conn.execute(select(table("ops.task").c.status)).scalars().all()
        assert "awaiting_agent" in states
        after = conn.execute(text("SELECT table_schema,table_name FROM information_schema.tables WHERE table_schema IN ('data','sem','kb','ops','eval') ORDER BY 1,2")).all()
        assert after == before  # Domain class and relation additions are registry data, no per-type DDL.
    # Preparation resumption uses the archived release and the original task identities.
    resumed = CliRunner().invoke(app, [*args, "--resume-run", str(report["run_id"])], obj=CliState(settings_factory=lambda: settings))
    assert resumed.exit_code == 0, (resumed.output, resumed.exception)
    assert json.loads(resumed.stdout)["run_id"] == report["run_id"]
