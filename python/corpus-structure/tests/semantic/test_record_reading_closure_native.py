"""Native direct-reading custody and structural-predictor controls.

These require the coherent forward native head. Pure checks do not qualify them.
"""

from dataclasses import replace
from types import SimpleNamespace

import pytest
from sqlalchemy import bindparam, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.arrow_publication import AppendPublication, stage_arrow
from corpus_structure.semantic.domain_operations import _cut_input, consolidate_cut
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.record_assertions import (
    lower_record_assertions,
)
from corpus_structure.semantic.record_projection import project_record_reports
from semantic.native_record_fixtures import RecordSourceRecipe
from semantic.native_record_fixtures import private_source as private_source
from semantic.record_publication_native_support import record_cut


@pytest.fixture
def reading_source(private_source):
    return private_source


@pytest.mark.parametrize(
    "private_source",
    [RecordSourceRecipe(composition="source-reading")],
    indirect=True,
    ids=("record-source-reading",),
)
def test_plain_graph_append_cannot_bypass_record_admission(reading_source):
    case = reading_source
    cut = record_cut(case)
    inputs = _cut_input(case.writer, cut, "unbound-reading-result")
    assert inputs.batch.record_assertion, lower_record_assertions(
        case.prepared, inputs.output_realization_id, inputs.batch.batch_id, inputs.record_reports
    ).diagnostics
    # Preserve the real graph and its independently located evidence while omitting
    # all record transport. Ordinary graph validity must not authorize this source basis.
    plain = replace(inputs.batch, **project_record_reports(case.prepared, ()), _analysis_input=None)
    with (
        case.writer.connect().execution_options(isolation_level="SERIALIZABLE") as conn,
        conn.begin() as transaction,
    ):
        conn.execute(
            text("SELECT data.begin_evaluation(:cut,:out)"),
            dict(cut=cut, out=inputs.output_realization_id),
        )
        with pytest.raises(DBAPIError, match="source-reading membership"), conn.begin_nested():
            transport = AppendPublication.from_rows(plain)
            stage_arrow(conn, transport)
            conn.execute(
                text("SELECT data.publish_batch(:r,:z,:b,:body)"),
                dict(
                    r=plain.release_id,
                    z=plain.realization_id,
                    b=plain.batch_id,
                    body=transport.content,
                ),
            )
        assert (
            conn.scalar(
                text("SELECT count(*) FROM data.batch WHERE realization_id=:out"),
                dict(out=inputs.output_realization_id),
            )
            == 0
        )
        transaction.rollback()


@pytest.mark.parametrize(
    "private_source",
    [RecordSourceRecipe(composition="source-reading")],
    indirect=True,
    ids=("record-source-reading",),
)
def test_bound_reading_uses_exact_direct_support_without_agent_observation(
    reading_source, record_source_admin
):
    case = reading_source
    result = consolidate_cut(case.writer, record_cut(case), "bound-reading-result")
    relation = table("data.record_assertion_support")
    with record_source_admin.connect() as conn:
        rows = (
            conn.execute(
                select(relation).where(
                    relation.c.release_id == case.prepared.release_id,
                    relation.c.realization_id == result.realization_id,
                )
            )
            .mappings()
            .all()
        )
        assert rows
        statement = text("SELECT data.has_record_assertion_support(:r,:z,:o,:e)")
        for row in rows:
            assert (
                conn.scalar(
                    statement,
                    dict(
                        r=case.prepared.release_id,
                        z=result.realization_id,
                        o=row["occurrence_id"],
                        e=row["evidence_id"],
                    ),
                )
                is True
            )
            assert (
                conn.scalar(
                    statement,
                    dict(
                        r=case.prepared.release_id,
                        z=result.realization_id,
                        o=row["occurrence_id"],
                        e="foreign-evidence",
                    ),
                )
                is False
            )
        assert (
            conn.scalar(
                text("SELECT count(*) FROM data.evidence_source WHERE realization_id=:z"),
                dict(z=result.realization_id),
            )
            == 0
        )


def predictor_input():
    names = [
        "present_fraction",
        "located_fraction",
        "exact_anchor_fraction",
        "unresolved_fraction",
        "classified_fraction",
        "changed_fraction",
        "alternative_count",
        "diagnostic_count",
    ]
    record = dict(
        fields=[
            dict(
                state="present",
                evidence_status="available",
                kind="classified",
                alternatives=[{}, {}],
            ),
            dict(
                state="unresolved",
                evidence_status="available",
                kind="normalized",
                alternatives=[{}],
            ),
        ],
        anchors=[dict(precision="exact"), dict(precision="item")],
    )
    feature = dict(
        algorithm=dict(features=[dict(name=name) for name in names]),
        parameters=dict(
            names=names,
            center=[0.0] * 8,
            scale=[1.0] * 8,
            coefficients=list(range(1, 9)),
            intercept=0.25,
        ),
    )
    return SimpleNamespace(record=record, feature=feature, diagnostics=["one", "two"])


def score_statement():
    return text("SELECT data.record_feature_score(:record,:diagnostics,:feature)").bindparams(
        bindparam("record", type_=JSONB),
        bindparam("diagnostics", type_=JSONB),
        bindparam("feature", type_=JSONB),
    )


def test_native_predictor_independently_uses_all_eight_structural_signals(commit_db_engine):
    sample = predictor_input()
    with commit_db_engine.connect() as conn:
        # Independent vector: [.5, 1, .5, .5, .5, .5, 3, 2].
        assert conn.scalar(score_statement(), vars(sample)) == pytest.approx(48.75, abs=1e-12)
        sample.feature["parameters"]["center"][0] = 0.25
        assert conn.scalar(score_statement(), vars(sample)) == pytest.approx(48.50, abs=1e-12)
        sample = predictor_input()
        sample.feature["parameters"]["scale"][0] = 0.5
        assert conn.scalar(score_statement(), vars(sample)) == pytest.approx(49.25, abs=1e-12)
        sample.feature["parameters"]["center"][0] = 0.125
        # First signal becomes (.5-.125)/.5=.75, adding .25 to the baseline.
        assert conn.scalar(score_statement(), vars(sample)) == pytest.approx(49.00, abs=1e-12)
        sample.feature["parameters"]["coefficients"][0] = 2.0
        assert conn.scalar(score_statement(), vars(sample)) == pytest.approx(49.75, abs=1e-12)


@pytest.mark.parametrize("kind", ["unavailable", "unknown", "misordered", "zero_scale"])
def test_native_predictor_refuses_unavailable_or_unreleased_inputs(commit_db_engine, kind):
    sample = predictor_input()
    if kind == "unavailable":
        sample.diagnostics = None
    elif kind == "unknown":
        sample.feature["algorithm"]["features"][0]["name"] = "raw_confidence"
        sample.feature["parameters"]["names"][0] = "raw_confidence"
    elif kind == "misordered":
        sample.feature["parameters"]["names"].reverse()
    else:
        sample.feature["parameters"]["scale"][0] = 0.0
    with commit_db_engine.begin() as conn, pytest.raises(DBAPIError), conn.begin_nested():
        conn.scalar(score_statement(), vars(sample))
