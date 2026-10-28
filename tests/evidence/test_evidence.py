"""corpus_evidence: records, finalize, check, generated indexes, catalog, rendered reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import get_origin

import duckdb
import pytest
from pydantic import Field, ValidationError

from corpus_evidence import catalog, citations, index, report, store
from corpus_evidence.cli import main
from corpus_evidence.model import Record, item_kind

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
        "consumed_by": ["P1 report"],
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
        "| [Probe folder](2026-01-01_probe/README.md) | 1 / 1 | OPEN-D1-1 | P1 report |"
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


def _supersede(root: Path) -> None:
    """probe.result superseded by probe.v2, which depends on it."""
    f = root / FOLDER / "records"
    (f / "probe.result.json").write_text(
        json.dumps(_record(status="superseded", superseded_by="probe.v2"))
    )
    (f / "probe.v2.json").write_text(
        json.dumps(_record(id="probe.v2", supersedes=["probe.result"], consumed_by=["P1-A"]))
    )


def test_catalog_tables_derive_from_record(root: Path, tmp_path: Path):
    _supersede(root)
    db = catalog.build(store.load(root), tmp_path / "ev.duckdb")
    con = duckdb.connect(str(db), read_only=True)
    cols = [r[0] for r in con.execute("DESCRIBE records").fetchall()]
    assert cols == ["gid", "folder", "record_path", *Record.model_fields]
    lists = {n for n, f in Record.model_fields.items() if get_origin(f.annotation) is list}
    tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    assert {f"record_{n}" for n in lists} | {"records", "record_links"} == tables
    # a number-or-text value splits into value_num / value_text; elements keep their order
    assert con.execute(
        'SELECT ord, name, value_num, value_text, "of" FROM record_results '
        f"WHERE gid = '{FOLDER}/probe.v2' ORDER BY ord"
    ).fetchall() == [(1, "matched", 9.0, None, 10), (2, "verdict", None, "yes", None)]
    assert con.execute("SELECT path, role FROM record_outputs WHERE ord = 1").fetchall() == [
        ("results/out", "table"),
        ("results/out", "table"),
    ]
    assert con.execute("SELECT kind, target_gid FROM record_links ORDER BY kind").fetchall() == [
        ("superseded_by", f"{FOLDER}/probe.v2"),
        ("supersedes", f"{FOLDER}/probe.result"),
    ]
    assert con.execute("SELECT id FROM records_for('OPEN-D1-1')").fetchall() == [("probe.v2",)]
    con.close()


def test_catalog_follows_a_model_change():
    class Extended(Record):
        reviewers: list[str] = Field(default_factory=list)
        score: int | str | None = None

    schema = catalog.arrow_schema(Extended)
    assert schema.names[-2:] == ["reviewers", "score"]
    assert str(schema.field("score").type) == "struct<num: double, text: string>"
    assert "record_reviewers" in catalog.element_tables(Extended)
    assert "record_reviewers" not in catalog.element_tables(Record)


def test_superseded_and_unknown_citations_warn(root: Path, tmp_path: Path):
    _supersede(root)
    docs = tmp_path / "docs"
    (docs / "design" / "sections").mkdir(parents=True)
    (docs / "adr").mkdir()
    (docs / "design" / "DESIGN.md").write_text(
        "**Tested** (records `probe.v2`, `probe.result`).\n"
        "Also record probe.missing and the code `probe.py` and `self.con`.\n"
    )
    (docs / "design" / "sections" / "D1.md").write_text(
        f"See [it](../../design_review/evidence/{FOLDER}/records/probe.result.json).\n"
    )
    (docs / "adr" / "0001-x.md").write_text("Rests on records probe.v2 and probe.result.\n")
    st = store.load(root)
    cited = sorted((c.path.name, c.line, c.rid) for c in citations.collect(st, docs))
    assert cited == [
        ("0001-x.md", 1, "probe.result"),
        ("0001-x.md", 1, "probe.v2"),
        ("D1.md", 1, "probe.result"),
        ("DESIGN.md", 1, "probe.result"),
        ("DESIGN.md", 1, "probe.v2"),
        ("DESIGN.md", 2, "probe.missing"),
    ]
    issues = citations.check(st, docs)
    assert all(i.severity == "warning" for i in issues)
    assert sorted(str(i) for i in issues) == [
        "warning: docs/adr/0001-x.md:1: cites superseded record probe.result "
        f"({FOLDER}); current: probe.v2",
        "warning: docs/design/DESIGN.md:1: cites superseded record probe.result "
        f"({FOLDER}); current: probe.v2",
        "warning: docs/design/DESIGN.md:2: cites unknown record probe.missing",
        "warning: docs/design/sections/D1.md:1: cites superseded record probe.result "
        f"({FOLDER}); current: probe.v2",
    ]
    # warnings do not fail the build and check
    main(["--root", str(root), "finalize", FOLDER, "probe.result", "probe.v2"])
    args = ["--root", str(root), "--docs", str(docs), "--catalog", str(tmp_path / "c.duckdb")]
    assert main(args) == 0


def test_render_tracks_query_and_value_reads(root: Path, tmp_path: Path):
    _supersede(root)
    db = catalog.build(store.load(root), tmp_path / "ev.duckdb")
    tpl = tmp_path / "rep.md.j2"
    tpl.write_text(
        "{{ query('SELECT value_num FROM record_results WHERE gid = $g AND name = $n', "
        "g='" + FOLDER + "/probe.v2', n='matched')[0].value_num }}\n"
        "{% for r in query(\"SELECT id, title FROM records WHERE folder = '" + FOLDER + "' "
        "AND status = 'superseded'\") %}{{ r.title }}{% endfor %}\n"
    )
    text = report.render(tpl, db, tmp_path / "rep.md").read_text()
    assert f"records: {FOLDER}/probe.result, {FOLDER}/probe.v2 -->" in text
    tpl.write_text(
        "{{ value(\"SELECT count(*) FROM record_results WHERE gid = '"
        + FOLDER
        + "/probe.result'\") }}\n"
    )
    text = report.render(tpl, db, tmp_path / "rep.md").read_text()
    assert f"records: {FOLDER}/probe.result -->" in text
    tpl.write_text("{{ value('SELECT 1') }}\n")
    assert "records: none -->" in report.render(tpl, db, tmp_path / "rep.md").read_text()


@pytest.mark.parametrize(
    ("ref", "kind"),
    [
        ("OPEN-D1-1", "open"),
        ("ADR-0009", "adr"),
        ("P0-F-2a", "id"),
        ("D2 §7.1", "id"),
        ("S0-report.md", "file"),
        ("trace.md", "file"),
        ("s0.adjudication", "record"),
        ("design-phase plan Q1", "document"),
    ],
)
def test_item_refs_are_typed(ref: str, kind: str):
    assert Record.model_validate(_record(answers=[ref], consumed_by=[ref])).answers == [ref]
    assert item_kind(ref) == kind


@pytest.mark.parametrize("ref", ["", "Probe report", " OPEN-D1-1", "OPEN-D1-1  x", "x" * 121])
def test_item_refs_refuse_prose(ref: str):
    with pytest.raises(ValidationError):
        Record.model_validate(_record(consumed_by=[ref]))


def test_check_warns_on_unknown_record_consumer(root: Path):
    f = root / FOLDER / "records" / "probe.result.json"
    f.write_text(json.dumps(_record(consumed_by=["probe.nowhere"])))
    assert any(
        "consumed_by names unknown record probe.nowhere" in str(i)
        for i in store.check(store.load(root))
    )
