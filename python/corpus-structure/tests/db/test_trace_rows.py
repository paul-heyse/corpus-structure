"""D3 §10's T3 rows in the migrated store, D3 §9's queries over them, and the run views (P0-F-4).

The rendition is `special/Normal.html` as ingest builds it (M01 with M03) from the vendored page,
stored by `store_rendition`; the segments the queries name are found by the offsets of
`fixtures/trace/T3.segments.json`. Entities, claims, the link and the evidence are written by hand
from D3 §10's tables. Each query's expected rows are written from those tables.
"""

from __future__ import annotations

import functools
import json
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import Connection, text

from corpus_structure.core.db import repo
from corpus_structure.core.evidence import RenditionContent
from corpus_structure.ingest.html import build_rendition
from corpus_structure.ingest.profile import compile_profile, load_profile
from corpus_structure.ingest.sentences import SentenceConfig

REPO = Path(__file__).resolve().parents[4]
SOURCE = "siegrist_random/random/special/Normal.html"
FIXTURE = json.loads((REPO / "fixtures/trace/T3.segments.json").read_text(encoding="utf-8"))
QUERIES = (Path(__file__).parent / "data" / "d3_queries.sql").read_text(encoding="utf-8")
FIND, FAMILY, STATEMENT, QUALIFIER, EVIDENCE, COVERAGE, WHY = (
    q.strip() for q in re.split(r";\s*\n", QUERIES.split("\n\n", 1)[1]) if q.strip()
)


@functools.cache
def normal() -> RenditionContent:
    raw = (REPO / "fixtures/trace/corpus" / SOURCE).read_bytes()
    profile = compile_profile(load_profile("siegrist"))
    return build_rendition(raw, profile, SentenceConfig(), source_uri=SOURCE).content


def sql(db: Connection, statement: str, **params: Any) -> Any:
    return db.execute(text(statement), params)


def segment_id(db: Connection, ren: int, kind: str, start: int, end: int) -> int:
    return sql(
        db,
        "SELECT id FROM kb.segment WHERE rendition_id = :r AND kind = :k AND "
        "start_offset = :s AND end_offset = :e",
        r=ren,
        k=kind,
        s=start,
        e=end,
    ).scalar_one()


@pytest.fixture
def t3(db: Connection, world: SimpleNamespace, helpers: SimpleNamespace) -> SimpleNamespace:
    w = world
    content = normal()
    ren = repo.store_rendition(
        db,
        w.document,
        w.document_key,
        content,
        repo.Build(w.config, w.task, w.payload["parse_detail"]),
    ).id
    unit_fx = FIXTURE["segments"][0]
    unit = segment_id(db, ren, "unit", unit_fx["start"], unit_fx["end"])
    details_fx = next(s for s in FIXTURE["segments"] if s["kind"] == "details")
    details = segment_id(db, ren, "details", details_fx["start"], details_fx["end"])
    sql(
        db,
        "UPDATE ops.task SET status = 'done', unit_id = :d, finished_at = now() - interval "
        "'1 hour' WHERE id = :t",
        d=w.document,
        t=w.task,
    )

    def entity(key: str, type_: str, label: str, scope: str, seg: int | None, kind=None) -> int:
        return sql(
            db,
            "INSERT INTO kb.entity (run_id, key, schema_version_id, type, label, scope, "
            "scope_segment_id, kind) VALUES (:r, :k, :v, :t, :l, :s, :g, :n) RETURNING id",
            r=w.run,
            k=key,
            v=w.schema_version,
            t=type_,
            l=label,
            s=scope,
            g=seg,
            n=kind,
        ).scalar_one()

    e = SimpleNamespace(
        rel1=entity("stm:rel1", "core:Statement", "theorem rel1", "local", unit, "theorem"),
        proof=entity(
            "stm:rel1-proof", "core:Statement", "proof of rel1", "local", details, "proof"
        ),
        x=entity("ent:X@rel1", "stat:RandomVariable", "X", "local", unit),
        y=entity("ent:Y@rel1", "stat:RandomVariable", "a + b X", "local", unit),
        normal=entity(
            "ent:normal", "stat:DistributionFamily", "normal distribution", "global", None
        ),
    )
    formula = lambda latex: {"t": "formula", "latex": latex}  # noqa: E731
    params = {"mean": formula("\\mu"), "variance": formula("\\sigma^2")}

    def claim(
        key,
        subject,
        pred,
        obj=None,
        value=None,
        modality="asserted",
        qualifiers=None,
        role=None,
        statement=e.rel1,
        establishment="stated",
    ) -> int:
        return sql(
            db,
            "INSERT INTO kb.claim (run_id, key, subject_id, predicate, object_entity_id, "
            "object_value, schema_version_id, modality, qualifiers, statement_id, "
            "statement_role, status, establishment) VALUES (:r, :k, :s, :p, :o, "
            "CAST(:v AS jsonb), :sv, :m, CAST(:q AS jsonb), :st, :role, 'accepted', :est) "
            "RETURNING id",
            r=w.run,
            k=key,
            s=subject,
            p=pred,
            o=obj,
            v=None if value is None else json.dumps(value),
            sv=w.schema_version,
            m=modality,
            q=json.dumps(qualifiers or {}),
            st=statement,
            role=role,
            est=establishment,
        ).scalar_one()

    c = SimpleNamespace(
        c1=claim(
            "clm:C1",
            e.x,
            "stat:has_distribution",
            obj=e.normal,
            modality="supposed",
            qualifiers={"stat:param_values": params},
            role="premise",
        ),
        c2=claim(
            "clm:C2",
            e.y,
            "stat:defined_as",
            value=formula("a + b X"),
            modality="defined",
            role="definiens",
        ),
        c3=claim(
            "clm:C3",
            e.y,
            "stat:has_distribution",
            obj=e.normal,
            role="conclusion",
            qualifiers={
                "stat:param_values": {
                    "mean": formula("a + b \\mu"),
                    "variance": formula("b^2 \\sigma^2"),
                },
                "core:conditions": {"op": "claim", "ref": "clm:C1"},
            },
        ),
        c4=claim("clm:C4", e.proof, "core:proves", obj=e.rel1, statement=e.proof),
        d1=claim(
            "clm:D1",
            e.y,
            "stat:has_distribution",
            obj=e.normal,
            role="conclusion",
            establishment="derived",
            qualifiers={
                "stat:param_values": {"standard_deviation": formula("\\lvert b \\rvert \\sigma")}
            },
        ),
    )
    sql(
        db,
        "INSERT INTO kb.claim_link (run_id, from_claim_id, link_type, to_claim_id, detail) "
        "VALUES (:r, :f, 'derived_from', :t, '{\"rule\": \"stat.variance_to_sd\"}')",
        r=w.run,
        f=c.d1,
        t=c.c3,
    )
    sql(
        db,
        "INSERT INTO kb.claim_ref (run_id, claim_id, kind, path, target_claim_id) VALUES "
        "(:r, :c, 'condition_premise', '', :t)",
        r=w.run,
        c=c.c3,
        t=c.c1,
    )
    text_ = content.canonical_text
    start = text_.index("then \\(a + b X\\)", unit_fx["start"])
    primary = (start, text_.index("\\sigma^2\\).", start) + len("\\sigma^2\\)"))
    a_cond = text_.index("\\(a \\in \\R\\)", unit_fx["start"])
    b_cond = text_.index("\\(b \\in \\R \\setminus \\{0\\}\\)", unit_fx["start"])
    ranges = [
        primary,
        (a_cond, a_cond + len("\\(a \\in \\R\\)")),
        (b_cond, b_cond + len("\\(b \\in \\R \\setminus \\{0\\}\\)")),
    ]
    spans = repo.upsert_spans(db, ren, ranges)
    for span, role in zip(spans, ("primary", "condition", "condition"), strict=True):
        sql(
            db,
            "INSERT INTO kb.claim_evidence (claim_id, span_id, role) VALUES (:c, :s, :r)",
            c=c.c3,
            s=span,
            r=role,
        )
    return SimpleNamespace(ren=ren, unit=unit, entities=e, claims=c, ranges=ranges, text=text_)


def test_the_bm25_find_query_uses_the_partial_index(db: Connection, t3: SimpleNamespace) -> None:
    params = {"q": "normally distributed variance", "renditions": [t3.ren], "k": 5}
    rows = sql(db, FIND, **params).all()
    assert rows and all(r.score < 0 for r in rows)
    texts = sql(db, "SELECT text FROM kb.segment WHERE id = ANY(:i)", i=[r.id for r in rows])
    assert any("normally distributed" in t for t in texts.scalars())
    plan = "\n".join(r[0] for r in sql(db, "EXPLAIN " + FIND, **params))
    assert "segment_bm25" in plan


def test_statement_reconstruction_returns_rel1s_claims_in_order(
    db: Connection, t3: SimpleNamespace
) -> None:
    rows = sql(db, STATEMENT, run=t3_run(db), statement_id=t3.entities.rel1).all()
    assert [(r.statement_role, r.key) for r in rows][:2] == [
        ("premise", "clm:C1"),
        ("definiens", "clm:C2"),
    ]
    assert {r.key for r in rows} == {"clm:C1", "clm:C2", "clm:C3", "clm:D1"}
    c3 = next(r for r in rows if r.key == "clm:C3")
    assert c3.conditions == {"op": "claim", "ref": "clm:C1"}


def test_claims_with_a_variance_qualifier(db: Connection, t3: SimpleNamespace) -> None:
    assert set(sql(db, QUALIFIER, run=t3_run(db)).scalars()) == {"clm:C1", "clm:C3"}


def test_evidence_for_c3_names_its_unit(db: Connection, t3: SimpleNamespace) -> None:
    rows = sql(db, EVIDENCE, claim_id=t3.claims.c3).all()
    assert sorted(r.role for r in rows) == ["condition", "condition", "primary"]
    assert {r.unit_id for r in rows} == {"rel1"}
    primary = next(r for r in rows if r.role == "primary")
    assert primary.text.startswith("then \\(a + b X\\) is normally distributed")
    assert (primary.start_offset, primary.end_offset) == t3.ranges[0]


def test_family_profile_has_no_claim_about_the_family_in_t3(
    db: Connection, t3: SimpleNamespace
) -> None:
    # T3 states claims about X and Y, none whose subject is the family or one of its parameters
    assert sql(db, FAMILY, run=t3_run(db), family_key="ent:normal").all() == []


def t3_run(db: Connection) -> int:
    return sql(db, "SELECT run_id FROM kb.claim WHERE key = 'clm:C1'").scalar_one()


def test_coverage_and_why_read_fates_as_of_the_cut(
    db: Connection, world: SimpleNamespace, helpers: SimpleNamespace, t3: SimpleNamespace
) -> None:
    w = world
    sql(db, "UPDATE ops.run SET cut_at = now() WHERE id = :r", r=w.run)
    unit_key = FIXTURE["unit_key"]
    for status, reason, finished in (
        ("done", None, "now() - interval '1 minute'"),
        ("done", None, "now() + interval '1 hour'"),
        ("skipped", "scope", "now() - interval '1 minute'"),
    ):
        sql(
            db,
            "INSERT INTO ops.task (run_id, stage, unit_type, unit_id, unit_key, "
            "method_config_id, input_hash, status, reason, finished_at) VALUES (:r, 'propose', "
            f"'segment', :u, :k, :c, 'i', :s, :why, {finished})",
            r=w.run,
            u=t3.unit,
            k=unit_key,
            c=w.config,
            s=status,
            why=reason,
        )
    rows = sql(db, COVERAGE, run=w.run, documents=[w.document]).all()
    assert sorted((r.status, r.reason, r.units) for r in rows) == [
        ("done", None, 1),
        ("skipped", "scope", 1),
        ("unresolved", None, 1),
    ]
    why = sql(db, WHY, run=w.run, unit_key=unit_key).all()
    assert [r.stage for r in why] == ["propose"] * 3 and {r.name for r in why} == {"ingest.html"}


def test_the_run_views_read_as_of_the_cut(
    db: Connection, world: SimpleNamespace, helpers: SimpleNamespace
) -> None:
    w = world
    sql(db, "UPDATE ops.run SET cut_at = now() WHERE id = :r", r=w.run)
    before = helpers.new_task(
        db,
        w,
        w.run,
        stage="extract",
        unit_type="segment",
        status="done",
        finished_at=text("now() - interval '1 minute'"),
    )
    after = helpers.new_task(
        db,
        w,
        w.run,
        stage="extract",
        unit_type="segment",
        status="done",
        finished_at=text("now() + interval '1 hour'"),
    )
    for task, ordinal in ((before, 0), (after, 0)):
        sql(
            db,
            "INSERT INTO kb.observation (task_id, ordinal, kind, payload, payload_schema_id, "
            "outcome) VALUES (:t, :o, 'mention', '{}', :ps, 'produced')",
            t=task,
            o=ordinal,
            ps=w.payload["mention"],
        )
        sql(
            db,
            "INSERT INTO ops.measurement (run_id, task_id, iteration, scope_type, metric, "
            "value) VALUES (:r, :t, 0, 'run', 'm', 1)",
            r=w.run,
            t=task,
        )
    seen = set(
        sql(db, "SELECT task_id FROM kb.run_observation WHERE run_id = :r", r=w.run).scalars()
    )
    assert seen == {before}
    measured = set(
        sql(db, "SELECT task_id FROM ops.run_measurement WHERE run_id = :r", r=w.run).scalars()
    )
    assert measured == {before}
    sql(db, "UPDATE ops.run SET cut_at = NULL WHERE id = :r", r=w.run)  # unsealed: current fates
    seen = set(
        sql(db, "SELECT task_id FROM kb.run_observation WHERE run_id = :r", r=w.run).scalars()
    )
    assert seen == {before, after}


def test_run_rendition_selects_the_run_configurations_build(
    db: Connection, world: SimpleNamespace, helpers: SimpleNamespace
) -> None:
    from corpus_structure.core.evidence import Segment

    w = world

    def content(text_: str) -> RenditionContent:
        return RenditionContent(
            canonical_text=text_, document=Segment(kind="document", start=0, end=len(text_))
        )

    mine = repo.store_rendition(
        db,
        w.document,
        w.document_key,
        content("one"),
        repo.Build(w.config, w.task, w.payload["parse_detail"]),
    )
    other_task = helpers.new_task(db, w, w.run, method_config_id=w.config2)
    repo.store_rendition(
        db,
        w.document,
        w.document_key,
        content("two"),
        repo.Build(w.config2, other_task, w.payload["parse_detail"]),
    )
    sql(
        db,
        "UPDATE ops.task SET status = 'done', unit_id = :d WHERE id = :t",
        d=w.document,
        t=w.task,
    )
    rows = sql(
        db, "SELECT document_id, rendition_id FROM kb.run_rendition WHERE run_id = :r", r=w.run
    ).all()
    assert rows == [(w.document, mine.id)]


def test_generic_claim_and_evidence_readers_over_independent_trace_rows(db, t3):
    from corpus_structure.serve.protocol import QueryContext
    from corpus_structure.schema.compile import compile_schema
    from corpus_structure.schema.pack import DOMAINS, load_pack
    ctx = QueryContext(t3_run(db), db)
    ctx.reader.__dict__['compiled'] = compile_schema([load_pack(DOMAINS / 'statistics')])
    rows = list(ctx.reader.claims(include_candidates=True, include_suppositions=True))
    assert {r['key'] for r in rows} == {'clm:C1','clm:C2','clm:C3','clm:C4','clm:D1'}
    c3 = next(r for r in rows if r['key']=='clm:C3')
    assert c3['subject']['label']
    assert len(c3['evidence']) == 3
    assert any(e['text'].startswith('then') for e in c3['evidence'])
    assert all(e['locator'] for e in c3['evidence'])
    assert list(ctx.reader.claims(after='clm:C3', include_candidates=True, include_suppositions=True))[-1]['key']=='clm:D1'
