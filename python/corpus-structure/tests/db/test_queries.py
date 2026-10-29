"""C2 queries against a production C1 materialization of independent authored fixtures."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from corpus_structure.schema.pack import DOMAINS
from corpus_structure.serve.explain import ClaimExplanation, explain
from corpus_structure.serve.journey import QueryRefused, serve_query
from corpus_structure.serve.queries import GENERIC
from corpus_structure.serve.registry import build_registry
from corpus_structure.serve.results import ClaimAnswer, EntityAnswer


@pytest.fixture
def ready(finalized_pool_run):
    return finalized_pool_run


def test_c1_trace_generic_and_pack_questions(ready):
    reg = build_registry(GENERIC, DOMAINS / "statistics")
    with ready.engine.connect() as conn:

        def ask(name, **params):
            return serve_query(conn, reg, name, params, run=ready.run)

        all_ = ask("claims")
        assert all_.rows
        typed = [ClaimAnswer.model_validate(r) for r in all_.rows]
        assert all(r.status == "accepted" for r in typed)
        assert all(r.premise for r in typed if r.modality == "supposed")
        unresolved = [
            r
            for r in typed
            if isinstance(r.object, EntityAnswer) and r.object.type == "core:ExternalReference"
        ]
        assert unresolved and all(r.conditional for r in unresolved)
        for r in unresolved:
            assert isinstance(r.object, EntityAnswer)
            assert r.object.descriptor and r.object.citation and r.object.citation.locator
        assert all_.coverage.unresolved_references >= 1 and all_.coverage.partial
        profile = ask("family_profile", family="normal")
        assert profile.rows
        assert len([r for r in profile.rows if r["predicate"] == "stat:identical_parameter"]) == 2
        assert ask("statement", locator="special/Normal.html#rel1").rows
        key = ClaimAnswer.model_validate(all_.rows[0]).key
        assert ask("evidence", key=key).rows
        entity = ask("entity", label="normal")
        assert any(r["type"] == "stat:DistributionFamily" for r in entity.rows)
        trans = ask("transformations_of", family="normal")
        assert trans.rows and all(r["definiens"] for r in trans.rows)
        assert ask("find", text="normally distributed").rows
        detail = explain(conn, ready.run, "claim", key)
        assert isinstance(detail.detail, ClaimExplanation)
        assert detail.detail.m19_task_id == ready.m19
        assert detail.detail.supports
        assert detail.detail.claim.key == key


def test_keyset_pagination_matches_unpaged_logical_rows(ready):
    reg = build_registry(GENERIC, DOMAINS / "statistics")
    with ready.engine.connect() as conn:
        full = serve_query(conn, reg, "claims", run=ready.run)
        page = serve_query(conn, reg, "claims", run=ready.run, max_rows=2)
        found = list(page.rows)
        while page.next_page_token:
            page = serve_query(conn, reg, "claims", page_token=page.next_page_token, max_rows=2)
            found += page.rows
        assert found == full.rows
        with pytest.raises(QueryRefused, match="size limit"):
            serve_query(conn, reg, "claims", run=ready.run, max_chars=100)


def test_explain_selects_exact_claim_from_sealed_m19(ready):
    import json

    reg = build_registry(GENERIC, DOMAINS / "statistics")
    with ready.engine.begin() as conn:
        key = ClaimAnswer.model_validate(
            serve_query(conn, reg, "claims", run=ready.run).rows[-1]
        ).key
        schema = conn.execute(
            text(

                    "SELECT id FROM meta.payload_schema WHERE kind='verification' ORDER BY "
                    'id DESC LIMIT 1'

            )
        ).scalar_one()
        for task, claim, marker in [
            (ready.m19, key, "sealed-only"),
            (ready.m19_again, key, "other-pass"),
            (ready.m19, "clm:unrelated", "other-claim"),
        ]:
            ordinal = conn.execute(
                text("SELECT coalesce(max(ordinal),-1)+1 FROM kb.observation WHERE task_id=:t"),
                {"t": task},
            ).scalar_one()
            payload = {
                "claim_key": claim,
                "verifier": "validate.rules",
                "verdict": "refuted",
                "detail": {
                    "rule": marker,
                    "severity": "warning",
                    "message": "independent seeded outcome",
                },
            }
            conn.execute(
                text(

                        'INSERT INTO '
                        'kb.observation(task_id,ordinal,kind,payload,payload_schema_id,outcome)'
                        " VALUES(:t,:n,'verification',CAST(:p AS jsonb),:s,'produced')"

                ),
                {"t": task, "n": ordinal, "p": json.dumps(payload), "s": schema},
            )
        result = explain(conn, ready.run, "claim", key)
        assert isinstance(result.detail, ClaimExplanation)
        assert result.detail.claim.key == key
        serialized = result.model_dump_json()
        assert "sealed-only" in serialized
        assert "other-pass" not in serialized and "other-claim" not in serialized


def test_unresolved_external_premise_edge_is_a_served_gap(ready):
    from sqlalchemy import insert, select

    from corpus_structure.core.db import metadata

    e, c, er = (metadata.tables[n] for n in ("kb.entity", "kb.claim", "kb.claim_entity_ref"))
    reg = build_registry(GENERIC, DOMAINS / "statistics")
    with ready.engine.begin() as conn:
        ref = conn.execute(
            select(e.c.id, e.c.key).where(
                e.c.run_id == ready.run,
                e.c.type == "core:ExternalReference",
                e.c.resolved_to_id.is_(None),
            )
        ).one()
        source = conn.execute(
            select(c.c.id, c.c.key)
            .where(
                c.c.run_id == ready.run, c.c.status == "accepted", c.c.object_entity_id.is_(None)
            )
            .order_by(c.c.key)
        ).first()
        assert source is not None
        conn.execute(
            c.update()
            .where(c.c.id == source.id)
            .values(qualifiers={"core:conditions": {"op": "claim", "ref": ref.key}})
        )
        conn.execute(
            insert(er).values(
                run_id=ready.run,
                claim_id=source.id,
                role="condition_premise",
                path="/qualifiers/core:conditions/ref",
                entity_id=ref.id,
            )
        )
        answer = serve_query(
            conn,
            reg,
            "claims",
            {
                "predicate": conn.execute(
                    select(c.c.predicate).where(c.c.id == source.id)
                ).scalar_one()
            },
            run=ready.run,
        )
        row = ClaimAnswer.model_validate(next(r for r in answer.rows if r["key"] == source.key))
        external = next(x for x in row.entity_references if x.role == "condition_premise")
        assert (
            external.entity.descriptor
            and external.entity.citation
            and external.entity.citation.locator
        )
        assert row.conditional is True


def test_parameter_mapping_excludes_other_members_of_requested_construction(ready):
    from sqlalchemy import insert, select

    from corpus_structure.core.db import metadata

    e, c, ce = (metadata.tables[n] for n in ("kb.entity", "kb.claim", "kb.claim_evidence"))
    reg = build_registry(GENERIC, DOMAINS / "statistics")
    with ready.engine.begin() as conn:
        family = conn.execute(
            select(e.c.id, e.c.key, e.c.schema_version_id)
            .where(e.c.run_id == ready.run, e.c.type == "stat:DistributionFamily")
            .order_by(e.c.id)
        ).first()
        assert family is not None
        construction = conn.execute(
            insert(e)
            .values(
                run_id=ready.run,
                key="ent:fixture-construction",
                schema_version_id=family.schema_version_id,
                type="stat:FamilyConstruction",
                label="fixture construction",
                scope="global",
            )
            .returning(e.c.id)
        ).scalar_one()
        other = conn.execute(
            insert(e)
            .values(
                run_id=ready.run,
                key="ent:fixture-other-family",
                schema_version_id=family.schema_version_id,
                type="stat:DistributionFamily",
                label="other fixture family",
                scope="global",
            )
            .returning(e.c.id)
        ).scalar_one()
        span = conn.execute(select(ce.c.span_id).limit(1)).scalar_one()
        for subject, key in [
            (family.id, "clm:fixture-requested-mapping"),
            (other, "clm:fixture-other-mapping"),
        ]:
            id_ = conn.execute(
                insert(c)
                .values(
                    run_id=ready.run,
                    key=key,
                    subject_id=subject,
                    predicate="stat:member_of_construction",
                    object_entity_id=construction,
                    schema_version_id=family.schema_version_id,
                    status="accepted",
                    establishment="stated",
                )
                .returning(c.c.id)
            ).scalar_one()
            conn.execute(insert(ce).values(claim_id=id_, span_id=span, role="primary"))
        result = serve_query(
            conn,
            reg,
            "parameter_mapping",
            {"construction": "ent:fixture-construction", "family": family.key},
            run=ready.run,
        )
        keys = {r["key"] for r in result.rows}
        assert "clm:fixture-requested-mapping" in keys
        assert "clm:fixture-other-mapping" not in keys
