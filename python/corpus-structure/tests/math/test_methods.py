"""`normalize.formula`, `extract.math` and `resolve.symbol_scope` as registered methods under O1
(ingest and math §5 P0-I-2b): real runs over the vendored trace pages on a database clone, with
phase 0's registry and graph and the statistics pack.

The runs are created and run through `commands.start_run`, whose inline worker loop calls each
method on this test's (the main) thread, where the grammar's deadline runs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, text

from corpus_structure.core import tex
from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import RunKind, RunStatus
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.llm.packet import unit_inputs
from corpus_structure.methods.math.context import standing_context
from corpus_structure.methods.math.methods import MathSection
from corpus_structure.methods.math.scope import Binders, resolve_scopes
from corpus_structure.methods.math.spans import extract, formula_values, read_spans
from corpus_structure.orchestrate import commands, context, phase0, project
from corpus_structure.orchestrate.registry import load_methods
from corpus_structure.schema.pack import DOMAINS

REPO = Path(__file__).resolve().parents[4]
CORPUS = REPO / "fixtures/trace/corpus"
TRACE = REPO / "fixtures/trace"
TRACE_UNITS = ("T1-leadin", "T1-dfn1", "T2", "T3", "T4")
PAGES = 4
MATH = ("normalize.formula", "extract.math", "resolve.symbol_scope")
PACK = load_methods(DOMAINS / "statistics" / "methods.yaml").sections


def full_run(engine: Engine, tmp: Path, **explicit: Any) -> int:
    url = engine.url.set(drivername="postgresql").render_as_string(hide_password=False)
    report = commands.start_run(
        engine,
        url=url,
        registry_for=phase0.registry,
        graph=phase0.PHASE0,
        run_pass=phase0.stub_pass,
        evaluate=phase0.stub_evaluate,
        kind=RunKind.FULL,
        explicit=explicit or None,
        domains=DOMAINS,
        method_settings=MethodSettings(data_dir=tmp, model_cache=tmp),
    )
    assert report.status is RunStatus.FINISHED
    return report.run_id


def statuses(engine: Engine, run_id: int) -> dict[str, list[str]]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT m.name, t.status FROM ops.task t JOIN ops.method_config c ON c.id = "
                "t.method_config_id JOIN ops.method m ON m.id = c.method_id WHERE t.run_id = :r "
                "AND t.unit_type = 'rendition' AND m.name = ANY(:m) ORDER BY t.id"
            ),
            {"r": run_id, "m": list(MATH)},
        )
        out: dict[str, list[str]] = {}
        for name, status in rows:
            out.setdefault(name, []).append(status)
        return out


def kinds(engine: Engine, run_id: int) -> dict[str, int]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT kind, count(*) FROM kb.run_observation WHERE run_id = :r GROUP BY kind"),
            {"r": run_id},
        )
        return {str(k): int(n) for k, n in rows}


def test_math_runs_write_observations_reuse_them_and_feed_the_packet_adapter(
    committing_db: Engine, tmp_path: Path
) -> None:
    engine = committing_db
    with engine.begin() as conn:
        project.init_project(
            conn,
            domain="statistics",
            corpus=CORPUS,
            registry=phase0.registry(DOMAINS / "statistics"),
            domains=DOMAINS,
        )

    # One task per rendition and method; mention, relation, value and scope observations.
    first = full_run(engine, tmp_path)
    assert statuses(engine, first) == {m: ["done"] * PAGES for m in MATH}
    found = kinds(engine, first)
    assert all(found.get(k, 0) > 0 for k in ("mention", "relation", "value", "scope")), found
    with engine.connect() as conn:
        parse_rate = conn.execute(
            text(
                "SELECT value FROM ops.measurement WHERE run_id = :r AND metric = "
                "'math.parse_rate' AND scope_type = 'run'"
            ),
            {"r": first},
        ).scalar_one()
        assert 0.9 < parse_rate <= 1.0

    # A rerun reuses every math task.
    second = full_run(engine, tmp_path)
    assert statuses(engine, second) == {m: ["reused"] * PAGES for m in MATH}
    assert kinds(engine, second) == found

    # M09 rerun with identical output: new M09 tasks, M13 reused (its digest holds payload
    # hashes, never task ids).
    third = full_run(engine, tmp_path, fresh=("extract.math",))
    third_statuses = statuses(engine, third)
    assert third_statuses["extract.math"] == ["done"] * PAGES
    assert third_statuses["resolve.symbol_scope"] == ["reused"] * PAGES
    assert third_statuses["normalize.formula"] == ["reused"] * PAGES

    # The stored mentions and scopes feed A1's packet adapter unchanged: each trace unit's standing
    # context equals I2a's over the in-memory scopes of the same rendition.
    section = MathSection.model_validate(PACK["math"])
    binders = Binders.model_validate(PACK["binders"])
    with engine.connect() as conn:
        view = context.run_view(conn, first)
        renditions = {r.document_key: r.rendition_id for r in view.reader.renditions()}
        pages = {
            str(k): str(u) for k, u in conn.execute(text("SELECT key, source_uri FROM kb.document"))
        }
        by_page = {pages[k].split("/random/", 1)[1]: rid for k, rid in renditions.items()}
        compared = 0
        for name in TRACE_UNITS:
            fixture = json.loads((TRACE / f"{name}.segments.json").read_text(encoding="utf-8"))
            rendition = by_page[fixture["page"]]
            inputs = unit_inputs(
                view.reader,
                rendition_id=rendition,
                document_id=None,
                unit_key=fixture["unit_key"],
                reference_run_id=None,
                pack_macros=section.macro_table(),
                golden=True,
            )
            content = inputs.content
            macros = tex.effective_macros(content.macros, section.macro_table())
            readings = read_spans(content, macros, section.constants)
            extraction = extract(readings)
            scopes = resolve_scopes(
                content,
                formula_values(readings),
                extraction.mentions,
                extraction.relations,
                macros,
                binders,
                SentenceConfig(),
            )
            expected = standing_context(content, inputs.page, scopes, inputs.unit)
            got = [(c.id, c.locator, c.text) for c in inputs.context]
            assert got == [(c.id, c.locator, c.text) for c in expected], name
            compared += len(got)
        assert compared > 0  # T2's two context sentences at least
