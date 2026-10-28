"""corpus_evidence: records, finalize, check, generated indexes, catalog, rendered reports."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest
from pydantic import ValidationError

from corpus_evidence import catalog, index, report, store
from corpus_evidence.cli import main
from corpus_evidence.model import Record

FOLDER = "2026-01-01_probe"


def _record(**kw) -> dict:
    base = {
        "id": "probe.result",
        "title": "Probe result",
        "group": "P1",
        "package": "P1-A",
        "finalized": "2026-01-01",
        "question": "Does the probe work?",
        "answers": ["OPEN-D1-1"],
        "method": "Ran the probe.",
        "commands": ["probe.py"],
        "inputs": [{"path": "input.txt", "role": "input"}],
        "outputs": [{"path": "results/out", "role": "table"}],
        "results": [{"name": "matched", "value": 9, "of": 10}, {"name": "verdict", "value": "yes"}],
        "outcome": "passed",
        "conclusion": "It works.",
        "consumed_by": ["Probe report"],
    }
    base.update(kw)
    return base


@pytest.fixture
def root(tmp_path: Path) -> Path:
    f = tmp_path / FOLDER
    (f / "results" / "out").mkdir(parents=True)
    (f / "records").mkdir()
    (f / "README.md").write_text("# Probe folder\n\nWhat it is.\n")
    (f / "input.txt").write_text("in\n")
    (f / "results" / "out" / "a.tsv").write_text("k\tv\nx\t1\ny\t2\n")
    (f / "records" / "probe.result.json").write_text(json.dumps(_record()))
    (tmp_path / "README.md").write_text(
        "# Evidence\n\n## Index\n\n<!-- evidence-index:start -->\n<!-- evidence-index:end -->\n"
    )
    return tmp_path


def test_schema_rejects_unknown_fields_and_bad_status():
    with pytest.raises(ValidationError):
        Record.model_validate(_record(extra_field=1))
    with pytest.raises(ValidationError):
        Record.model_validate(_record(status="superseded"))  # without superseded_by
    with pytest.raises(ValidationError):
        Record.model_validate(_record(outputs=[{"path": "../outside"}]))


def test_finalize_then_check_detects_changed_output(root: Path):
    st = store.load(root)
    assert any("has no hash" in str(i) for i in store.check(st))
    store.finalize(st.folders[FOLDER], "probe.result")
    st = store.load(root)
    assert not [i for i in store.check(st) if i.severity == "error"]
    (root / FOLDER / "results" / "out" / "a.tsv").write_text("k\tv\nx\t3\n")
    st = store.load(root)
    assert any(
        "changed since finalization" in i.message and i.severity == "error" for i in store.check(st)
    )


def test_references_and_supersession_are_checked(root: Path):
    f = root / FOLDER / "records"
    (f / "probe.result.json").write_text(
        json.dumps(_record(status="superseded", superseded_by="probe.v2"))
    )
    (f / "probe.v2.json").write_text(json.dumps(_record(id="probe.v2", depends_on=["missing.one"])))
    issues = [str(i) for i in store.check(store.load(root))]
    assert any("probe.v2 does not list it in supersedes" in i for i in issues)
    assert any("'missing.one' does not resolve" in i for i in issues)


def test_index_is_generated_idempotently(root: Path):
    st = store.load(root)
    assert index.stale(st)
    index.write(st)
    st = store.load(root)
    assert not index.stale(st)
    folder_readme = (root / FOLDER / "README.md").read_text()
    assert (
        "## Records" in folder_readme
        and "[Probe result](records/probe.result.json)" in folder_readme
    )
    assert (
        "| [Probe folder](2026-01-01_probe/README.md) | 1 / 1 | OPEN-D1-1 | Probe report |"
        in (root / "README.md").read_text()
    )


def test_catalog_and_folder_views(root: Path, tmp_path: Path):
    (root / FOLDER / "catalog.sql").write_text(
        "CREATE VIEW out_rows AS SELECT * FROM "
        "read_csv('{{ folder }}/results/out/a.tsv', delim='\\t');"
    )
    st = store.load(root)
    db = catalog.build(st, tmp_path / "build" / "ev.duckdb")
    con = duckdb.connect(str(db), read_only=True)
    assert con.execute("SELECT count(*) FROM records_for('OPEN-D1-1')").fetchone() == (1,)
    assert con.execute(f"SELECT result('{FOLDER}/probe.result', 'matched')").fetchone() == ("9.0",)
    assert con.execute(
        f"SELECT count(*) FROM {catalog.schema_name(st.folders[FOLDER])}.out_rows"
    ).fetchone() == (2,)
    con.close()


def test_render_uses_catalog_and_refuses_undefined(root: Path, tmp_path: Path):
    db = catalog.build(store.load(root), tmp_path / "ev.duckdb")
    tpl = tmp_path / "rep.md.j2"
    tpl.write_text(
        "{% set r = record('" + FOLDER + "/probe.result') %}"
        "Matched {{ value(\"SELECT value_num FROM record_results WHERE name='matched'\") | int }} "
        "of 10 ({{ pct(0.9) }}); {{ r.title }}.\n"
    )
    out = report.render(tpl, db, tmp_path / "rep.md")
    text = out.read_text()
    assert text.startswith("Matched 9 of 10 (90%); Probe result.")
    assert f"records: {FOLDER}/probe.result" in text
    tpl.write_text("{{ missing_figure }}\n")
    with pytest.raises(Exception, match="missing_figure"):
        report.render(tpl, db, tmp_path / "rep2.md")


def test_cli_build_and_check(root: Path, tmp_path: Path):
    assert main(["--root", str(root), "finalize", FOLDER, "probe.result"]) == 0
    assert main(["--root", str(root), "--catalog", str(tmp_path / "c.duckdb")]) == 0
    assert main(["--root", str(root), "check"]) == 0


@pytest.mark.parametrize("outcome", ["passed", "failed", "blocked", "partial", "not_run"])
def test_record_outcomes_accepted(outcome: str) -> None:
    assert Record.model_validate(_record(outcome=outcome)).outcome == outcome


def test_record_outcome_unknown_refused() -> None:
    with pytest.raises(ValidationError):
        Record.model_validate(_record(outcome="skipped"))
