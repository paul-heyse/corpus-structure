"""Native sealed report cut -> fresh qualified result with independent policy expectations."""

from dataclasses import replace

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.domain_operations import (
    DomainOperationRefused,
    consolidate_cut,
)
from corpus_structure.semantic.metadata import table

from .domain_scenarios import build_domain_case
from .inventory_reading import inventory_alternatives, inventory_assessments


def test_actual_cut_publishes_fresh_result_and_preserves_reports(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    prepared, run, cut = build_domain_case(
        semantic_db_engine, semantic_writer_engine, tmp_path / "source.html"
    )
    result = consolidate_cut(semantic_writer_engine, cut, "evaluated")
    assert result.run_id == run and result.realization_id == "evaluated" and result.reports == 1
    assert consolidate_cut(semantic_writer_engine, cut, "evaluated").receipt == result.receipt

    class OtherVersion:
        release_id = prepared.release_id
        version = "unsupported-operation-version"

        def evaluate(self, inputs, scope, fused):
            raise AssertionError("unadmitted policy must not evaluate")

    with pytest.raises(DomainOperationRefused, match="policy version"):
        consolidate_cut(semantic_writer_engine, cut, "evaluated", policy=OtherVersion())
    with semantic_writer_engine.connect() as conn:
        job = (
            conn.execute(select(table("ops.run")).where(table("ops.run").c.id == run))
            .mappings()
            .one()
        )
        assert job["status"] == "finished" and job["result_realization_id"] == "evaluated"
        assert (
            conn.execute(
                select(table("data.realization").c.data_revision).where(
                    table("data.realization").c.realization_id == "source"
                )
            ).scalar_one()
            == 0
        )
        assert conn.execute(
            select(table("data.occurrence")).where(
                table("data.occurrence").c.realization_id == "evaluated"
            )
        ).all()
        assert conn.execute(select(table("data.evidence_source"))).all()
        cover = conn.execute(
            select(table("data.coverage").c.family, table("data.coverage").c.outcome)
        ).all()
        assert ("unsupported", "partial") in cover
        original = conn.execute(select(table("kb.observation").c.payload)).scalar_one()
        assert original["statements"][0]["id"] == "s" and original["unsupported"][0]["id"] == "u"


def test_released_rule_rejects_scientific_claim_without_erasing_source(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    rules = b"""rules:
- id: test.reject
  applies_to: ex:name
  at: [finalize]
  severity: error
  check: "claim.value&.v == 'Bob'"
"""
    prepared, _run, cut = build_domain_case(
        semantic_db_engine, semantic_writer_engine, tmp_path / "source.html", rules=rules
    )
    consolidate_cut(semantic_writer_engine, cut, "evaluated")
    with semantic_writer_engine.connect() as conn:
        outcomes = conn.execute(select(table("data.assessment").c.outcome)).scalars().all()
        assert "rejected" in outcomes and "refuted" in outcomes
        assert len(conn.execute(select(table("data.occurrence"))).all()) >= 2
        name = next(
            p.iri
            for d in prepared.definitions
            if d.name == "Person"
            for p in d.properties
            if p.name == "name"
        )
        assert not conn.execute(
            select(table("data.fact").c.fact_id)
            .join(
                table("data.selection"),
                table("data.selection").c.fact_id == table("data.fact").c.fact_id,
            )
            .where(table("data.fact").c.property_id == name)
        ).first()


def test_atomic_cut_inference_has_distinct_exact_receipts(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    _prepared, _run, cut = build_domain_case(
        semantic_db_engine, semantic_writer_engine, tmp_path / "source.html", graph=True
    )
    result = consolidate_cut(semantic_writer_engine, cut, "evaluated")
    assert result.receipt.data_revision == 1
    assert result.data_revision == 2
    assert len(result.derivation_receipts) == 1 and result.derivation_receipts[0].data_revision == 2
    assert consolidate_cut(semantic_writer_engine, cut, "evaluated") == result
    with semantic_writer_engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT f.subject_id,f.property_id,v.entity_id FROM data.fact f JOIN "
                "data.typed_value v ON "
                "(v.release_id,v.realization_id,v.value_id)="
                "(f.release_id,f.realization_id,f.object_value_id) "
                "WHERE f.realization_id='evaluated' AND f.property_id IN "
                "('https://example.org/parent','https://example.org/child')"
            )
        ).all()
        parent = next(row for row in rows if row.property_id.endswith("/parent"))
        assert (parent.entity_id, "https://example.org/child", parent.subject_id) in rows
        assert conn.execute(select(table("data.derivation"))).all()


def test_native_candidate_publication_binds_operation_profile_cut_and_target(
    semantic_db_engine,
    semantic_writer_engine,
    tmp_path,
):
    from corpus_structure.semantic.analytics import compile_projection
    from corpus_structure.semantic.arrow_publication import AppendPublication, stage_arrow
    from corpus_structure.semantic.domain_operations import _cut_input

    prepared, _run, cut = build_domain_case(
        semantic_db_engine, semantic_writer_engine, tmp_path / "source.html"
    )
    inputs = _cut_input(semantic_writer_engine, cut, "candidate-output")
    compiled = compile_projection(prepared, inputs.source_binding, kind="candidate")
    transport = AppendPublication.from_rows(inputs.batch)
    bound = dict(
        r=prepared.release_id,
        z=inputs.output_realization_id,
        b=transport.batch_id,
        content=transport.content,
        sr=inputs.source_binding.release_id,
        sz=inputs.source_binding.realization_id,
        revision=inputs.source_binding.data_revision,
        capture=inputs.source_binding.capture_id,
        operation="evaluate",
        projection=compiled.projection_id,
        contract="candidate",
        cut=cut,
        profile=compiled.profile.digest,
    )
    changes = [
        ({"projection": "projection:wrong"}, "compiled projection differs"),
        ({"profile": "wrong"}, "arithmetic profile differs"),
        ({"cut": 0}, "requires bound cut/profile"),
        ({"z": inputs.source_binding.realization_id}, "source/target differs"),
        ({"operation": "append"}, "does not permit derived projection"),
    ]
    with (
        semantic_writer_engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn,
        conn.begin() as transaction,
    ):
        conn.execute(
            text("SELECT data.begin_evaluation(:cut,:out)"),
            {"cut": cut, "out": inputs.output_realization_id},
        )
        for mutation, diagnostic in changes:
            with pytest.raises(DBAPIError, match=diagnostic), conn.begin_nested():
                stage_arrow(conn, transport)
                conn.execute(
                    text(
                        "SELECT data.publish_derived_batch_v2(:r,:z,:b,:content,"
                        ":sr,:sz,:revision,:capture,:operation,:projection,:contract,:cut,:profile)"
                    ),
                    {**bound, **mutation},
                )
        assert (
            conn.scalar(
                text("SELECT count(*) FROM data.batch WHERE realization_id=:out"),
                {"out": inputs.output_realization_id},
            )
            == 0
        )
        transaction.rollback()


def test_native_finish_refuses_source_occurrence_without_cut_evidence(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    from corpus_structure.semantic.analytics import compile_projection
    from corpus_structure.semantic.arrow_publication import (
        SnapshotDerivedPublication,
        publish_arrow_on_connection,
    )
    from corpus_structure.semantic.domain_operations import _cut_input

    _prepared, run, cut = build_domain_case(
        semantic_db_engine, semantic_writer_engine, tmp_path / "source.html"
    )
    inputs = _cut_input(semantic_writer_engine, cut, "hostile")
    batch = replace(inputs.batch, evidence_source=()).bind_preparation(inputs.prepared)
    compiled = compile_projection(inputs.prepared, inputs.source_binding, kind="candidate")
    publication = SnapshotDerivedPublication.from_rows(
        batch,
        source=inputs.source_binding,
        operation_id="evaluate",
        projection_id=compiled.projection_id,
        contract_id="candidate",
        cut_id=cut,
        profile_digest=compiled.profile.digest,
    )
    with (
        pytest.raises(DBAPIError, match="source occurrence has no located evidence"),
        semantic_writer_engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn,
        conn.begin(),
    ):
        conn.execute(
            text("SELECT data.begin_evaluation(:cut,:out)"), {"cut": cut, "out": "hostile"}
        )
        publish_arrow_on_connection(conn, publication)
        conn.execute(
            text("SELECT data.finish_evaluation(:cut,:out,:batch)"),
            {"cut": cut, "out": "hostile", "batch": batch.batch_id},
        )
    with semantic_writer_engine.connect() as conn:
        assert not conn.execute(
            select(table("data.realization")).where(
                table("data.realization").c.realization_id == "hostile"
            )
        ).first()
        assert (
            conn.execute(
                select(table("ops.run").c.result_realization_id).where(table("ops.run").c.id == run)
            ).scalar_one()
            is None
        )


def test_writer_cannot_create_untrusted_stage_relations(semantic_writer_engine):
    with (
        pytest.raises(DBAPIError, match="permission denied to create temporary tables"),
        semantic_writer_engine.begin() as conn,
    ):
        conn.exec_driver_sql("CREATE TEMP TABLE sp_entity(entity_id text)")


def test_stage_disposal_refuses_writer_owned_imitation(semantic_db_engine, semantic_writer_engine):
    # Deliberately widen only this disposable test database to exercise the disposal
    # guard independently of the normal principal's earlier TEMP privilege refusal.
    with semantic_db_engine.begin() as conn:
        database = conn.scalar(text("SELECT current_database()"))
        quoted = conn.dialect.identifier_preparer.quote(database)
        conn.exec_driver_sql(f"GRANT TEMP ON DATABASE {quoted} TO corpus_sem_writer")
    with (
        pytest.raises(DBAPIError, match="untrusted staging relation sp_record_report"),
        semantic_writer_engine.begin() as conn,
    ):
        conn.exec_driver_sql("CREATE TEMP TABLE sp_record_report(task_id bigint)")
        conn.exec_driver_sql("SELECT data.end_stage()")


def test_same_fact_reports_keep_statement_specific_rule_decisions(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    rules = (
        b"rules:\n- id: test.statement\n  applies_to: ex:name\n  at: [finalize]\n  "
        b"severity: error\n  check: \"claim.statement_kind == 'theorem'\"\n"
    )
    _prepared, _run, cut = build_domain_case(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path / "source.html",
        rules=rules,
        duplicate=True,
    )
    consolidate_cut(semantic_writer_engine, cut, "evaluated")
    with semantic_writer_engine.connect() as conn:
        o, f, a = table("data.occurrence"), table("data.fact"), table("data.assessment")
        decisions = conn.execute(
            select(o.c.fact_id, a.c.outcome)
            .join(f, (f.c.fact_id == o.c.fact_id) & (f.c.realization_id == o.c.realization_id))
            .join(a, a.c.occurrence_id == o.c.occurrence_id)
            .where(
                f.c.property_id == "https://example.org/name",
                a.c.operation_id == "consolidate.status",
            )
        ).all()
        assert len(decisions) == 2 and len({r.fact_id for r in decisions}) == 1
        assert {r.outcome for r in decisions} == {"accepted", "rejected"}
        selected = conn.execute(
            select(table("data.selection").c.fact_id).where(
                table("data.selection").c.fact_id == decisions[0].fact_id
            )
        ).scalar_one()
        assert selected == decisions[0].fact_id


@pytest.mark.parametrize(
    ("formulas", "outcome", "selected"),
    [
        (("a+b", "b+a"), "equivalent", 2),
        (("a+1", "a+2"), "different", 0),
        (("f(x)", "g(x)"), "undecided", 0),
    ],
)
def test_native_scientific_comparison_preserves_facts_and_uncertainty(
    semantic_db_engine, semantic_writer_engine, tmp_path, formulas, outcome, selected
):
    _prepared, _run, cut = build_domain_case(
        semantic_db_engine, semantic_writer_engine, tmp_path / "source.html", formulas=formulas
    )
    consolidate_cut(semantic_writer_engine, cut, "evaluated")
    with semantic_writer_engine.connect() as conn:
        a, f, s = table("data.assessment"), table("data.fact"), table("data.selection")
        rows = (
            conn.execute(select(a).where(a.c.operation_id == "scientific.value_equivalence"))
            .mappings()
            .all()
        )
        assert len(rows) == 2 and {r["outcome"] for r in rows} == {outcome}
        assert all(r["counterpart_fact_id"] and r["counterpart_occurrence_id"] for r in rows)
        assert {r["occurrence_id"] for r in rows} == {r["counterpart_occurrence_id"] for r in rows}
        assert all(r["context_value_id"] and r["comparison_tier"] for r in rows)
        assert all(r["reason"] and not r["reason"].startswith('{"other_fact_id"') for r in rows)
        if outcome == "undecided":
            assert all(r["uncertainty"] for r in rows)
        assert (
            len(
                conn.execute(
                    select(f.c.fact_id).where(f.c.property_id == "https://example.org/name")
                ).all()
            )
            == 2
        )
        assert (
            len(
                conn.execute(
                    select(s.c.fact_id)
                    .join(f, f.c.fact_id == s.c.fact_id)
                    .where(f.c.property_id == "https://example.org/name")
                ).all()
            )
            == selected
        )
        if outcome == "equivalent":
            reps = table("data.scientific_representative")
            components = (
                conn.execute(
                    select(reps)
                    .join(f, f.c.fact_id == reps.c.fact_id)
                    .where(f.c.property_id == "https://example.org/name")
                )
                .mappings()
                .all()
            )
            assert len(components) == 2
            assert {row["representative_fact_id"] for row in components} == {
                min(row["fact_id"] for row in components)
            }
            assert len({row["component_id"] for row in components}) == 1


@pytest.mark.parametrize("local_known", [False, True])
def test_known_input_reference_and_declared_key_converge_with_lineage(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path, local_known
):
    _prepared, run, cut = build_domain_case(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path / "source.html",
        known=True,
        local_known=local_known,
    )
    consolidate_cut(semantic_writer_engine, cut, "evaluated")
    with semantic_writer_engine.connect() as conn:
        lineage = conn.execute(select(table("data.entity_input"))).mappings().one()
        assert lineage["entity_id"] == "known:alice" and lineage["input_entity_id"] == "known:alice"
        assert (
            lineage["input_realization_id"] == "source"
            and lineage["input_data_revision"] == 1
            and lineage["run_id"] == run
        )
        assert conn.execute(
            select(table("data.fact").c.subject_id).where(
                table("data.fact").c.realization_id == "evaluated",
                table("data.fact").c.property_id == "https://example.org/name",
            )
        ).scalars().all() == ["known:alice"]
        prior = (
            conn.execute(
                select(table("data.occurrence").c.realization_id).where(
                    table("data.occurrence").c.source == "prior-source"
                )
            )
            .scalars()
            .all()
        )
        assert prior and set(prior) == {"source"}
    if not local_known:
        from corpus_structure.semantic.analytics import load_packet
        from corpus_structure.semantic.query import read_session

        uri = semantic_reader_engine.url.set(drivername="postgresql").render_as_string(
            hide_password=False
        )
        with read_session(semantic_reader_engine, "evaluated") as session:
            packet = load_packet(session, uri)
        assert packet.to_table("entity_input").to_pylist()[0]["input_data_revision"] == 1
        assert len(packet.to_table("fact_input").to_pylist()) == 2
        assert {
            row["input_realization_id"] for row in packet.to_table("fact_input").to_pylist()
        } == {"source"}


def test_actual_cut_nested_references_preserve_literal_fields_and_unresolved_source(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    from corpus_structure.semantic.query import QuerySpec, read_session

    _prepared, _run, cut = build_domain_case(
        semantic_db_engine, semantic_writer_engine, tmp_path / "source.html", nary=True
    )
    consolidate_cut(semantic_writer_engine, cut, "evaluated")
    with read_session(semantic_reader_engine, "evaluated") as session:
        cls = session.class_handle("Person")
        result = session.query(QuerySpec(cls, session.property_handle(cls, "relation")))
        obj = result.rows[0].object
        assert obj.ref == "other" and obj.endpoint != "other"
        assert obj.roles["r"].ref == "other" and obj.roles["r"].target == obj.endpoint
        refs = session._entities({obj.endpoint})
        assert refs[obj.endpoint].memberships[0].class_iri == "https://example.org/Person"
    with semantic_writer_engine.connect() as conn:
        assessments = (
            conn.execute(
                select(table("data.assessment").c.outcome).where(
                    table("data.assessment").c.operation_id == "consolidate.status"
                )
            )
            .scalars()
            .all()
        )
        assert assessments == ["candidate"]
    with semantic_reader_engine.connect() as conn:
        assert conn.execute(select(table("data.entity_source"))).all()


def test_required_endpoint_identity_is_not_fabricated(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    _prepared, _run, cut = build_domain_case(
        semantic_db_engine, semantic_writer_engine, tmp_path / "source.html", nary=True, broken=True
    )
    consolidate_cut(semantic_writer_engine, cut, "evaluated")
    with semantic_writer_engine.connect() as conn:
        assert not conn.execute(select(table("data.fact"))).first()
        coverage = conn.execute(
            select(table("data.coverage").c.outcome, table("data.coverage").c.reason)
        ).all()
        assert any(
            row.outcome == "partial" and "required identifying fields" in (row.reason or "")
            for row in coverage
        )
        assert (
            conn.execute(select(table("kb.observation").c.payload)).scalar_one()["entities"][1][
                "reference"
            ]["description"]
            == "outside unresolved person"
        )


def test_claim_references_use_canonical_premise_fact_and_separate_source_view_ids(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    from corpus_structure.semantic.domain_operations import _cut_input

    _prepared, _run, cut = build_domain_case(
        semantic_db_engine, semantic_writer_engine, tmp_path / "source.html", claim_chain=True
    )
    inputs = _cut_input(semantic_writer_engine, cut, "evaluated")
    by_ref = {c.local_id: c for c in inputs.candidates}
    assert by_ref["p1"].fact_id == by_ref["p2"].fact_id
    assert by_ref["d1"].fact_id == by_ref["d2"].fact_id
    assert by_ref["d1"].qualification["condition"]["ref"] == by_ref["p1"].fact_id
    first, second = by_ref["d1"].rule_qualification, by_ref["d2"].rule_qualification
    assert first is not None and second is not None
    assert first["condition"]["ref"] == by_ref["p1"].occurrence_id
    assert second["condition"]["ref"] == by_ref["p2"].occurrence_id
    consolidate_cut(semantic_writer_engine, cut, "evaluated")


def test_cyclic_claim_reference_stays_explicit_unresolved_report(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    _prepared, _run, cut = build_domain_case(
        semantic_db_engine, semantic_writer_engine, tmp_path / "source.html", cycle=True
    )
    consolidate_cut(semantic_writer_engine, cut, "evaluated")
    with semantic_writer_engine.connect() as conn:
        assert not conn.execute(select(table("data.fact"))).first()
        assert (
            "cyclic source claim reference"
            in conn.execute(select(table("data.coverage").c.reason)).scalars().all()
        )


@pytest.mark.parametrize("operator", ["compare", "not"])
def test_scientific_restriction_profile_never_drops_uninterpreted_domain(
    semantic_db_engine, semantic_writer_engine, tmp_path, operator
):
    comparison = {
        "kind": "compare",
        "relation": ">",
        "lhs": {"kind": "formula", "language": "latex", "expression": "x"},
        "rhs": {"kind": "formula", "language": "latex", "expression": "0"},
    }
    condition = comparison if operator == "compare" else {"kind": "not", "term": comparison}
    _prepared, _run, cut = build_domain_case(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path / "source.html",
        formulas=(r"\sqrt{x^2}", "x"),
        condition=condition,
    )
    consolidate_cut(semantic_writer_engine, cut, "evaluated")
    with semantic_writer_engine.connect() as conn:
        rows = conn.execute(
            select(
                table("data.assessment").c.outcome, table("data.assessment").c.uncertainty
            ).where(table("data.assessment").c.operation_id == "scientific.value_equivalence")
        ).all()
        assert len(rows) == 2
        assert {row.outcome for row in rows} == (
            {"equivalent"} if operator == "compare" else {"undecided"}
        )
        if operator == "not":
            assert all(row.uncertainty for row in rows)


def test_independent_source_binding_disagreement_persists_one_compact_group(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    from corpus_structure.semantic.query import QuerySpec, read_session

    _prepared, _run, cut = build_domain_case(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path / "source.html",
        formulas=("x",),
        report_count=2,
        global_person_identity=True,
    )
    consolidate_cut(semantic_writer_engine, cut, "evaluated")
    with read_session(semantic_reader_engine, "evaluated") as session:
        cls = session.class_handle("Person")
        prop = session.property_handle(cls, "name")
        result = session.query(QuerySpec(cls, prop))
        assert len(result.rows) == 2 and len({row.source for row in result.rows}) == 2
        explanation = session.explain(result.rows[0].fact_id)
        assert len(inventory_alternatives(session, explanation.fact_id)) == 1
        group = inventory_alternatives(session, explanation.fact_id)[0]
        assert set(group.member_fact_ids) == {row.fact_id for row in result.rows}
        assert (
            __import__("json").loads(group.reason)["generated"][0]["kind"]
            == "qualifier_binding_disagreement"
        )
        assert {
            row.outcome
            for row in inventory_assessments(session, explanation.fact_id)
            if row.operation_id == "consolidate.status"
        } == {"ambiguous"}
        assert not session.query(QuerySpec(cls, prop, "accepted")).rows
    with semantic_reader_engine.connect() as conn:
        assert len(conn.execute(select(table("data.alternative_member"))).all()) == 2


@pytest.mark.parametrize("duplicate", [False, True])
def test_authored_alternatives_retain_source_reason_without_duplicate_fact_groups(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path, duplicate
):
    from corpus_structure.semantic.query import QuerySpec, read_session

    formulas = ("x", "x") if duplicate else ("x+1", "x+2")
    _prepared, _run, cut = build_domain_case(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path / "source.html",
        formulas=formulas,
        authored_alternative=True,
    )
    consolidate_cut(semantic_writer_engine, cut, "evaluated")
    with read_session(semantic_reader_engine, "evaluated") as session:
        cls = session.class_handle("Person")
        prop = session.property_handle(cls, "name")
        rows = session.query(QuerySpec(cls, prop)).rows
        explanation = session.explain(rows[0].fact_id)
        assert len(inventory_alternatives(session, explanation.fact_id)) == (0 if duplicate else 1)
        if not duplicate:
            source = __import__("json").loads(
                inventory_alternatives(session, explanation.fact_id)[0].reason
            )["sources"][0]
            assert source == {
                "observation_key": rows[0].source,
                "local_id": "choice",
                "faithful": True,
                "reason": "source explicitly contrasts these possibilities",
            }
            assert not session.query(QuerySpec(cls, prop, "accepted")).rows
        else:
            assert len(session.query(QuerySpec(cls, prop, "accepted")).rows) == 1


def test_primitive_alias_rule_view_keeps_source_value_kind(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    rules = (
        b"rules:\n- id: count.literal\n  applies_to: ex:name\n  severity: error\n  at: "
        b"[finalize]\n  check: \"claim.value&.t == 'number' and claim.value&.v == '4'\"\n"
    )
    _prepared, _run, cut = build_domain_case(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path / "source.html",
        integer_alias=True,
        rules=rules,
    )
    consolidate_cut(semantic_writer_engine, cut, "evaluated")
    with semantic_writer_engine.connect() as conn:
        statuses = (
            conn.execute(
                select(table("data.assessment").c.outcome).where(
                    table("data.assessment").c.operation_id == "consolidate.status"
                )
            )
            .scalars()
            .all()
        )
        assert statuses == ["accepted"]


@pytest.mark.parametrize("operand", ["fallback", "constant"])
def test_recorded_math_fallbacks_and_constants_drive_native_science(
    semantic_db_engine,
    semantic_writer_engine,
    semantic_reader_engine,
    tmp_path,
    operand,
):
    from corpus_structure.semantic.query import QuerySpec, read_session

    _prepared, _run, cut = build_domain_case(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path / "source.html",
        # The declared Euler constant discharges the denominator's nonzero premise.
        formulas=(r"\A", "x") if operand == "fallback" else (r"\frac{1}{e}", "e^{-1}"),
        math={
            "macros": {r"\A": "x", "unused": "z"},
            "constants": ["e", r"\pi"],
        },
    )
    consolidate_cut(semantic_writer_engine, cut, "evaluated")
    with read_session(semantic_reader_engine, "evaluated") as session:
        cls = session.class_handle("Person")
        prop = session.property_handle(cls, "name")
        rows = session.query(QuerySpec(cls, prop)).rows
        if operand == "fallback":
            used = next(row.object for row in rows if row.object.expression.startswith(r"\A"))
            assert used.macro_context[r"\A"].body == "x" and "unused" not in used.macro_context
        selected = session.query(QuerySpec(cls, prop, "accepted")).rows
        expected_facts = {row.fact_id for row in rows}
        assert len(expected_facts) == 2
        assert {row.fact_id for row in selected} == expected_facts
        representative = table("data.scientific_representative")
        representatives = (
            session.connection.execute(
                select(representative).where(
                    session.scope(representative), representative.c.fact_id.in_(expected_facts)
                )
            )
            .mappings()
            .all()
        )
        assert {row["fact_id"]: row["representative_fact_id"] for row in representatives} == {
            fact_id: min(expected_facts) for fact_id in expected_facts
        }
        assert {row["policy_id"] for row in representatives} == {"min-fact-id-1"}
        assert {
            a.outcome
            for a in inventory_assessments(session, rows[0].fact_id)
            if a.operation_id == "scientific.value_equivalence"
        } == {"equivalent"}


def test_unqualified_log_domain_is_not_cancelled_into_accepted_equivalence(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    from corpus_structure.semantic.query import QuerySpec, read_session

    _, _, cut = build_domain_case(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path / "source.html",
        formulas=(r"e^{\ln x}", "x"),
        math={"constants": ["e"]},
    )
    consolidate_cut(semantic_writer_engine, cut, "evaluated")
    with read_session(semantic_reader_engine, "evaluated") as session:
        cls = session.class_handle("Person")
        prop = session.property_handle(cls, "name")
        rows = session.query(QuerySpec(cls, prop)).rows
        assert not session.query(QuerySpec(cls, prop, "accepted")).rows
        assert {
            assessment.outcome
            for row in rows
            for assessment in inventory_assessments(session, row.fact_id)
            if assessment.operation_id == "scientific.value_equivalence"
        } == {"undecided"}


def test_conflicting_recorded_constant_profiles_refuse_cut(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    _prepared, _run, cut = build_domain_case(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path / "source.html",
        formulas=("x",),
        report_count=2,
        global_person_identity=True,
        math={"constants": ["e"]},
        second_math={"constants": []},
    )
    with pytest.raises(
        DomainOperationRefused, match="incompatible recorded mathematical constant profiles"
    ):
        consolidate_cut(semantic_writer_engine, cut, "evaluated")
    with semantic_writer_engine.connect() as conn:
        assert not conn.execute(
            select(table("data.realization")).where(
                table("data.realization").c.realization_id == "evaluated"
            )
        ).first()


def test_known_input_roles_filter_before_value_hydration(
    semantic_db_engine, semantic_writer_engine, tmp_path, monkeypatch
):
    from corpus_structure.semantic.query import ReadSession

    _prepared, run, cut = build_domain_case(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path / "source.html",
        known=True,
        input_noise=True,
    )
    with semantic_db_engine.connect() as conn:
        facts = (
            conn.execute(
                select(table("data.fact")).where(table("data.fact").c.realization_id == "source")
            )
            .mappings()
            .all()
        )
    noise_ids = {
        f["object_value_id"] for f in facts if f["property_id"] == "https://example.org/note"
    }
    expected_ids = {
        f["object_value_id"]
        for f in facts
        if f["property_id"] in {"https://example.org/id", "https://example.org/name"}
    }
    assert noise_ids
    assert expected_ids
    loaded = set()
    original = ReadSession.load_values

    def observe(self, value_ids, *args, **kwargs):
        loaded.update(value_ids)
        return original(self, value_ids, *args, **kwargs)

    monkeypatch.setattr(ReadSession, "load_values", observe)
    consolidate_cut(semantic_writer_engine, cut, "evaluated")
    assert expected_ids <= loaded
    assert not noise_ids & loaded
    with semantic_db_engine.connect() as conn:
        assert (
            conn.scalar(
                select(table("data.entity_input").c.input_entity_id).where(
                    table("data.entity_input").c.run_id == run
                )
            )
            == "known:alice"
        )
        assert (
            conn.scalar(
                select(table("data.fact").c.fact_id).where(
                    table("data.fact").c.realization_id == "evaluated",
                    table("data.fact").c.property_id == "https://example.org/note",
                )
            )
            is None
        )


def test_declared_endpoint_and_isolate_publish_without_invented_properties(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    _prepared, _run, cut = build_domain_case(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path / "source.html",
        graph=True,
        isolated_entity=True,
    )
    consolidate_cut(semantic_writer_engine, cut, "evaluated")
    with semantic_writer_engine.connect() as conn:
        sources = conn.execute(select(table("data.entity_source"))).mappings().all()
        declared = {row["local_id"]: row["entity_id"] for row in sources}
        assert {"other", "isolated"} <= declared.keys()
        for local in ("other", "isolated"):
            memberships = (
                conn.execute(
                    select(table("data.membership")).where(
                        table("data.membership").c.entity_id == declared[local]
                    )
                )
                .mappings()
                .all()
            )
            assert [(m["class_id"], m["establishment"]) for m in memberships] == [
                ("https://example.org/Person", "agent_asserted")
            ]
            assert not conn.execute(
                select(table("data.membership_support")).where(
                    table("data.membership_support").c.entity_id == declared[local]
                )
            ).first()
            assert not conn.execute(
                select(table("data.fact")).where(
                    table("data.fact").c.subject_id == declared[local],
                    table("data.fact").c.property_id == "https://example.org/name",
                )
            ).first()
        assert not conn.execute(
            select(table("data.fact")).where(
                table("data.fact").c.subject_id == declared["isolated"]
            )
        ).first()
        assert not conn.execute(
            select(table("data.occurrence")).where(
                table("data.occurrence").c.item.like("entities/%")
            )
        ).first()


@pytest.mark.parametrize(
    "forgery", ["valid", "class", "declaration", "resolution", "cut", "source_cut"]
)
def test_native_declared_membership_refuses_forged_lineage(
    semantic_db_engine, semantic_writer_engine, tmp_path, forgery
):
    from contextlib import nullcontext

    from corpus_structure.semantic.analytics import compile_projection
    from corpus_structure.semantic.arrow_publication import (
        SnapshotDerivedPublication,
        publish_arrow_on_connection,
    )
    from corpus_structure.semantic.domain_operations import NativeEvidenceLink, _cut_input
    from corpus_structure.semantic.publication import EvidenceSourceRow

    prepared, _run, cut = build_domain_case(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path / "source.html",
        graph=True,
        membership_subtype=True,
        unselected_report=forgery == "source_cut",
    )
    inputs = _cut_input(semantic_writer_engine, cut, "hostile")
    batch = inputs.batch
    endpoint = next(row for row in batch.entity_source if row.local_id == "other")
    if forgery == "class":
        other_class = next(d.iri for d in prepared.definitions if d.name == "PersonSubtype")
        batch = replace(
            batch,
            membership=tuple(
                replace(row, class_id=other_class) if row.entity_id == endpoint.entity_id else row
                for row in batch.membership
            ),
        )
    elif forgery == "declaration":
        batch = replace(
            batch,
            entity_source=tuple(
                replace(row, local_id="not-declared") if row == endpoint else row
                for row in batch.entity_source
            ),
        )
    elif forgery == "source_cut":
        with semantic_writer_engine.connect() as conn:
            observation = table("kb.observation")
            task = table("ops.task")
            foreign_observation = conn.execute(
                select(observation.c.id)
                .join(task, task.c.id == observation.c.task_id)
                .where(
                    task.c.run_id != inputs.run_id,
                    observation.c.payload_definition == "AgentStoredBatch",
                )
            ).scalar_one()
        assert foreign_observation not in {report["id"] for report in inputs.reports}
        batch = replace(
            batch,
            entity_source=tuple(
                replace(row, observation_id=foreign_observation) if row == endpoint else row
                for row in batch.entity_source
            ),
        )
    elif forgery == "resolution":
        batch = replace(
            batch,
            entity_resolution=tuple(
                replace(row, operation_id="not-resolve-identity")
                if row.local_id == "other"
                else row
                for row in batch.entity_resolution
            ),
        )
    evidence_sources = []
    for eid, link in sorted(inputs.source_links.items()):
        assert isinstance(link, NativeEvidenceLink)
        evidence_sources.append(
            EvidenceSourceRow(
                eid,
                link.observation_id,
                None,
                None,
                source_view_id=link.source_view_id,
                native_address=link.native_address,
            )
        )
    batch = replace(batch, evidence_source=tuple(evidence_sources)).bind_preparation(prepared)
    compiled = compile_projection(prepared, inputs.source_binding, kind="candidate")
    publication = SnapshotDerivedPublication.from_rows(
        batch,
        source=inputs.source_binding,
        operation_id="evaluate",
        projection_id=compiled.projection_id,
        contract_id="candidate",
        cut_id=int(cut) + 1000 if forgery == "cut" else cut,
        profile_digest=compiled.profile.digest,
    )
    with (
        pytest.raises(
            DBAPIError,
            match=(
                "membership requires establishment and support"
                if forgery == "class"
                else "entity source is outside the bound final observation cut"
                if forgery == "source_cut"
                else None
            ),
        )
        if forgery != "valid"
        else nullcontext(),
        semantic_writer_engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn,
        conn.begin(),
    ):
        conn.execute(
            text("SELECT data.begin_evaluation(:cut,:out)"), {"cut": cut, "out": "hostile"}
        )
        publish_arrow_on_connection(conn, publication)
        conn.execute(
            text("SELECT data.finish_evaluation(:cut,:out,:batch)"),
            {"cut": cut, "out": "hostile", "batch": batch.batch_id},
        )
    with semantic_writer_engine.connect() as conn:
        persisted = conn.execute(
            select(table("data.realization")).where(
                table("data.realization").c.realization_id == "hostile"
            )
        ).first()
        assert (persisted is not None) == (forgery == "valid")
