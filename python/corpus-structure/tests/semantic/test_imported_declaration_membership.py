"""An admitted declaration-only class survives supported known-reference import."""

from dataclasses import replace

import pytest
from native_refusals import native_refusal
from sqlalchemy import select, text

from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.metadata import table


def test_declared_membership_survives_known_object_import_without_new_declaration(
    imported_declaration_case,
):
    case = imported_declaration_case.stage
    commit_writer_engine = imported_declaration_case.writer
    result = consolidate_cut(commit_writer_engine, case.cut, "imported-result")
    with commit_writer_engine.connect() as conn:
        membership = table("data.membership")
        assert conn.execute(
            select(membership.c.class_id, membership.c.establishment).where(
                membership.c.realization_id == result.realization_id,
                membership.c.entity_id == case.endpoint,
            )
        ).all() == [("https://example.org/Person", "agent_asserted")]
        for name in ("membership_support", "entity_source"):
            relation = table("data." + name)
            assert not conn.execute(
                select(relation).where(
                    relation.c.realization_id == result.realization_id,
                    relation.c.entity_id == case.endpoint,
                )
            ).first()
        imported = table("data.entity_input")
        lineage = (
            conn.execute(
                select(imported).where(
                    imported.c.realization_id == result.realization_id,
                    imported.c.entity_id == case.endpoint,
                )
            )
            .mappings()
            .one()
        )
        assert lineage["input_realization_id"] == case.prior_realization
        assert lineage["input_data_revision"] == case.prior_revision
        assert lineage["input_entity_id"] == case.endpoint and lineage["run_id"] == case.run
    # Finished runs retain the same receipt without republishing their imported graph.
    assert consolidate_cut(commit_writer_engine, case.cut, "imported-result") == result


@pytest.mark.parametrize(
    "forgery", ["valid", "revision", "run", "entity", "class", "establishment"]
)
def test_native_imported_membership_requires_exact_bound_lineage(imported_membership_case, forgery):
    from corpus_structure.semantic.analytics import compile_projection
    from corpus_structure.semantic.arrow_publication import (
        SnapshotDerivedPublication,
        publish_arrow_on_connection,
    )
    from corpus_structure.semantic.domain_operations import NativeEvidenceLink, _cut_input
    from corpus_structure.semantic.publication import EvidenceSourceRow

    case = imported_membership_case.stage
    inputs = _cut_input(imported_membership_case.reader, case.cut, "hostile")
    batch = inputs.batch
    original = batch
    assert not any(row.entity_id == case.endpoint for row in batch.entity_source)
    assert not any(row.entity_id == case.endpoint for row in batch.membership_support)
    if forgery in {"revision", "run", "entity"}:
        batch = replace(
            batch,
            entity_input=tuple(
                replace(
                    row,
                    input_data_revision=(
                        row.input_data_revision + 1
                        if forgery == "revision"
                        else row.input_data_revision
                    ),
                    run_id=int(case.prior_run) if forgery == "run" else row.run_id,
                    input_entity_id=case.subject if forgery == "entity" else row.input_entity_id,
                )
                if row.entity_id == case.endpoint
                else row
                for row in batch.entity_input
            ),
        )
    elif forgery in {"class", "establishment"}:
        batch = replace(
            batch,
            membership=tuple(
                replace(
                    row,
                    class_id="https://example.org/PersonSubtype"
                    if forgery == "class"
                    else row.class_id,
                    establishment="stated" if forgery == "establishment" else row.establishment,
                )
                if row.entity_id == case.endpoint
                else row
                for row in batch.membership
            ),
        )
    # Retain inherited evidence custody and add this cut's own protected evidence.
    evidence_sources = {row.evidence_id: row for row in batch.evidence_source}
    for eid, link in sorted(inputs.source_links.items()):
        assert isinstance(link, NativeEvidenceLink)
        evidence_sources[eid] = EvidenceSourceRow(
            eid,
            link.observation_id,
            None,
            None,
            source_view_id=link.source_view_id,
            native_address=link.native_address,
        )
    batch = replace(batch, evidence_source=tuple(evidence_sources.values())).bind_preparation(
        case.prepared
    )
    compiled = compile_projection(case.prepared, inputs.source_binding, kind="candidate")
    publication = SnapshotDerivedPublication.from_rows(
        batch,
        source=inputs.source_binding,
        operation_id="evaluate",
        projection_id=compiled.projection_id,
        contract_id="candidate",
        cut_id=case.cut,
        profile_digest=compiled.profile.digest,
    )
    valid_sources = {row.evidence_id: row for row in original.evidence_source}
    for row in evidence_sources.values():
        valid_sources[row.evidence_id] = row
    original = replace(original, evidence_source=tuple(valid_sources.values())).bind_preparation(
        case.prepared
    )
    valid = SnapshotDerivedPublication.from_rows(
        original,
        source=inputs.source_binding,
        operation_id="evaluate",
        projection_id=compiled.projection_id,
        contract_id="candidate",
        cut_id=case.cut,
        profile_digest=compiled.profile.digest,
    )

    def publish(conn, actual, rows):
        conn.execute(
            text("SELECT data.begin_evaluation(:cut,:out)"), {"cut": case.cut, "out": "hostile"}
        )
        publish_arrow_on_connection(conn, actual)
        conn.execute(
            text("SELECT data.finish_evaluation(:cut,:out,:batch)"),
            {"cut": case.cut, "out": "hostile", "batch": rows.batch_id},
        )

    if forgery == "valid":
        with (
            imported_membership_case.writer.connect().execution_options(
                isolation_level="SERIALIZABLE"
            ) as conn,
            conn.begin(),
        ):
            publish(conn, publication, batch)
            assert (
                conn.scalar(
                    text("SELECT count(*) FROM data.realization WHERE realization_id='hostile'")
                )
                == 1
            )
    else:
        with imported_membership_case.principal("write", isolation_level="SERIALIZABLE") as conn:
            positive = conn.begin_nested()
            publish(conn, valid, original)
            assert (
                conn.scalar(
                    text("SELECT count(*) FROM data.realization WHERE realization_id='hostile'")
                )
                == 1
            )
            positive.rollback()
            message = (
                "entity input differs from bound evaluation input"
                if forgery in {"revision", "run"}
                else "membership requires establishment and support"
            )
            with (
                native_refusal(
                    "P0001" if forgery in {"revision", "run"} else "23514",
                    message=message,
                    context="data.check_entity_input()"
                    if forgery in {"revision", "run"}
                    else "data.validate_pre_inference_state(text,text)",
                ),
                conn.begin_nested(),
            ):
                publish(conn, publication, batch)
            for relation in ("realization", "membership", "entity_input"):
                assert (
                    conn.scalar(
                        text(f"SELECT count(*) FROM data.{relation} WHERE realization_id='hostile'")
                    )
                    == 0
                )
