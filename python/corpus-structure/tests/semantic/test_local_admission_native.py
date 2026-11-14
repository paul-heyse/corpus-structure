"""Real sealed-cut common publication and local witness refusal controls."""

from dataclasses import asdict, replace
from typing import Any

import pytest
from native_refusals import native_refusal
from sqlalchemy import select, text

from corpus_structure.semantic.analytics import compile_projection
from corpus_structure.semantic.arrow_publication import AppendPublication, stage_arrow
from corpus_structure.semantic.domain_operations import _cut_input, consolidate_cut
from corpus_structure.semantic.local_admission import assertion_identity
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.serve.contributions import ContributionRequest, serve_contributions
from semantic.local_admission_scenarios import LocalWitnessRecipe
from semantic.native_record_fixtures import private_source as private_source


@pytest.fixture
def local_source(scenario_seeds):
    with scenario_seeds.commit_clone(LocalWitnessRecipe()) as clone:
        yield clone.stage.bind(clone.writer, clone=clone)


@pytest.fixture
def local_witness_case(scenario_seeds):
    with scenario_seeds.rollback_family(LocalWitnessRecipe()) as family:
        yield family.stage.bind(family.reader), family


def test_exact_local_claims_publish_without_complete_record_or_unit_attachment(local_source):
    case, _, cut = local_source
    result = consolidate_cut(case.writer, cut, "local-source-public")
    assert consolidate_cut(case.writer, cut, "local-source-public") == result
    with read_snapshot(case.writer) as conn:
        relation = table("data.local_assertion")
        rows = tuple(
            conn.execute(
                select(relation).where(relation.c.realization_id == result.realization_id)
            ).mappings()
        )
        assert len(rows) == 2
        assert {row["event"] for row in rows} == {"source_occurrence", "source_literal_quote"}
        assert {row["literal_pieces_json"] for row in rows} == {'["12"]'}
        records = table("data.record_assertion")
        assert not conn.execute(
            select(records).where(records.c.realization_id == result.realization_id)
        ).all()
        page = serve_contributions(
            conn,
            ContributionRequest(run_id=case.run, include_publication=True, include_support=True),
        )
        assert page.inventory_counts["local_assertion_witnesses"] == 2
        public = [item["row"] for item in page.items if item["population"] == "local_assertion"]
        assert len(public) == 2
        for row in public:
            assert isinstance(row, dict)
            assert row["scientific_support"] == "unmodeled"
            assert "semantic_type" not in row
        summary = serve_contributions(
            conn, ContributionRequest(run_id=case.run, include_publication=True)
        )
        assert summary.inventory_counts == page.inventory_counts
        for item in summary.items:
            if item["population"] == "local_assertion":
                row = item["row"]
                assert isinstance(row, dict)
                assert "anchors" not in row and "literal_pieces" not in row


@pytest.mark.parametrize(
    "corruption", ["event", "event_swap", "basis", "cut", "literal", "contribution", "append"]
)
def test_native_local_witness_refusals_rollback_receipt_and_all_rows(
    local_witness_case, corruption
):
    (case, _, cut), family = local_witness_case
    inputs = _cut_input(case.writer, cut, "local-source-forged")
    assert inputs.batch.local_assertion
    clean = replace(inputs.batch, _analysis_input=None)
    first, *rest = clean.local_assertion
    changes: dict[str, Any] = {
        "event": dict(event="attached_unit"),
        "event_swap": dict(
            event="source_occurrence"
            if first.event == "source_literal_quote"
            else "source_literal_quote"
        ),
        "basis": dict(basis="independent_source_judgment"),
        "cut": dict(cut_id=cut + 999),
        "literal": dict(literal_pieces_json='["13"]'),
        "contribution": dict(contribution_id="foreign"),
        "append": {},
    }[corruption]
    changed = replace(first, **changes)
    # Possessing the hash algorithm does not confer source/event authority.
    changed = replace(
        changed,
        assertion_id=assertion_identity(
            {key: value for key, value in asdict(changed).items() if key != "assertion_id"}
        ),
    )
    batch = replace(clean, local_assertion=(changed, *rest))
    if corruption == "append":
        from corpus_structure.semantic.record_projection import project_record_reports

        # Exercise the local append guard without unrelated record-report transport
        # satisfying the earlier source-record append refusal.
        batch = replace(batch, **project_record_reports(case.prepared, ()))
    compiled = compile_projection(case.prepared, inputs.source_binding, kind="candidate")
    with family.principal("write", isolation_level="SERIALIZABLE") as conn:
        conn.execute(
            text("SELECT data.begin_evaluation(:cut,:out)"),
            dict(cut=cut, out=inputs.output_realization_id),
        )

        def publish(candidate, *, append=False):
            transport = AppendPublication.from_rows(candidate)
            stage_arrow(conn, transport)
            if append:
                conn.execute(
                    text("SELECT data.publish_batch(:r,:z,:b,:content)"),
                    dict(
                        r=candidate.release_id,
                        z=candidate.realization_id,
                        b=candidate.batch_id,
                        content=transport.content,
                    ),
                )
            else:
                conn.execute(
                    text(
                        "SELECT data.publish_derived_batch_v2(:r,:z,:b,:content,:sr,:sz,:revision,"
                        ":capture,'evaluate',:projection,'candidate',:cut,:profile)"
                    ),
                    dict(
                        r=candidate.release_id,
                        z=candidate.realization_id,
                        b=candidate.batch_id,
                        content=transport.content,
                        sr=inputs.source_binding.release_id,
                        sz=inputs.source_binding.realization_id,
                        revision=inputs.source_binding.data_revision,
                        capture=inputs.source_binding.capture_id,
                        projection=compiled.projection_id,
                        cut=cut,
                        profile=compiled.profile.digest,
                    ),
                )

        with conn.begin_nested() as positive:
            publish(clean)
            assert (
                conn.scalar(
                    text("SELECT count(*) FROM data.local_assertion WHERE realization_id=:z"),
                    dict(z=clean.realization_id),
                )
                == 2
            )
            positive.rollback()
        expected = {
            "event": ("23514", None, "local assertion policy or event is inapplicable"),
            "basis": ("23514", None, "local assertion policy or event is inapplicable"),
            "event_swap": ("23514", None, "source witness does not authorize this local event"),
            "literal": (
                "23514",
                None,
                "local assertion content or intrinsic identity differs from its exact witness",
            ),
            "append": (
                "23514",
                None,
                "local source assertions require sealed-cut derived publication",
            ),
            "cut": ("23503", "fk_local_assertion_cut_id", None),
            "contribution": ("23503", "fk_local_assertion_origin_task_id_contribution_id", None),
        }[corruption]
        with (
            native_refusal(expected[0], constraint=expected[1], message=expected[2]),
            conn.begin_nested(),
        ):
            publish(batch, append=corruption == "append")
        assert (
            conn.scalar(
                text("SELECT count(*) FROM data.batch WHERE realization_id=:z"),
                dict(z=clean.realization_id),
            )
            == 0
        )
    with case.writer.connect() as conn:
        assert (
            conn.scalar(
                text(
                    "SELECT count(*) FROM data.local_assertion "
                    "WHERE realization_id='local-source-forged'"
                )
            )
            == 0
        )
