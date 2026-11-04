"""An admitted declaration-only class survives supported known-reference import."""

from contextlib import nullcontext
from dataclasses import dataclass, replace

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.orchestrate.semantic import agent_packet, queue_agent
from corpus_structure.semantic._operation_ids import CutId, RunId
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import (
    OperationBinding,
    claim_tasks,
    complete_task,
    create_run,
    register_document,
    seal_cut,
)
from corpus_structure.semantic.proposals import locate_proposal
from corpus_structure.semantic.types import PreparedRelease

from .domain_scenarios import build_domain_case


@dataclass(frozen=True)
class ImportedDeclarationCase:
    prepared: PreparedRelease
    run: RunId
    cut: CutId
    prior_run: RunId
    prior_realization: str
    prior_revision: int
    subject: str
    endpoint: str


def imported_declaration_case(admin, writer, tmp_path):
    """Use the public packet's own eligible reference universe, never injected classes."""
    from pdf_acceptance_support import publish_controlled_pdf_views, write_controlled_pdf

    prepared, prior_run, prior_cut = build_domain_case(
        admin,
        writer,
        tmp_path / "prior.pdf",
        graph=True,
        global_person_identity=True,
        membership_subtype=True,
    )
    prior = consolidate_cut(writer, prior_cut, "prior-result")
    with writer.connect() as conn:
        declarations = {
            row["local_id"]: row["entity_id"]
            for row in conn.execute(select(table("data.entity_source"))).mappings()
        }
        subject, endpoint = declarations["person"], declarations["other"]
        fact, value, selected = map(table, ("data.fact", "data.typed_value", "data.selection"))
        assert conn.execute(
            select(fact.c.fact_id)
            .join(value, value.c.value_id == fact.c.object_value_id)
            .join(selected, selected.c.fact_id == fact.c.fact_id)
            .where(
                fact.c.realization_id == prior.realization_id,
                fact.c.subject_id == subject,
                fact.c.property_id == "https://example.org/parent",
                value.c.entity_id == endpoint,
            )
        ).first()
        assert not conn.execute(
            select(table("data.membership_support")).where(
                table("data.membership_support").c.entity_id == endpoint
            )
        ).first()
    # Same logical document URI preserves legitimate reference eligibility; different
    # bytes/key avoid silently reusing the first producer's completed task.
    path = tmp_path / "next.pdf"
    original = write_controlled_pdf(path, ("Alice is here.", "Next source revision."))
    configuration = {
        "model": "controlled-known-reference-agent",
        "mode": "extract",
        "max_units": 1,
        "packet_cap_chars": 18000,
        "sentences": SentenceConfig().model_dump(mode="json"),
    }
    with writer.begin() as conn:
        document = register_document(
            conn,
            project_id="p",
            source_uri="page.html",
            original_path=str(path),
            original=original,
            metadata={"page": "next"},
            mime="application/pdf",
        )
        run = create_run(
            conn,
            project_id="p",
            binding=OperationBinding(
                prepared.release_id, prior.realization_id, prior.data_revision, b"{}"
            ),
            kind="full",
            options={"agent_configs": {"agent.general/extract": configuration}},
            code_commit="import-declared-membership",
        )
    (view,) = publish_controlled_pdf_views(
        writer,
        prepared=prepared,
        run_id=run,
        document_id=document,
        original=original,
        paragraphs=("Alice is here.",),
        keys=("next#one",),
    )
    with writer.begin() as conn:
        (task,) = queue_agent(
            conn,
            run_id=run,
            prepared=prepared,
            configuration=configuration,
            method_name="agent.general",
            units=(UnitRef(TaskUnitType.SOURCE_VIEW, view.ref.id, view.ref.key),),
        )
        packet = agent_packet(conn, run, task, prepared)
        known_classes = dict(packet.known_classes)
        assert known_classes[subject] == ("https://example.org/Person",)
        assert known_classes[endpoint] == ("https://example.org/Person",)
        sentence = next(s for s in packet.frame.sentences if s.end - s.start == 14)
        raw = {
            "unit_ref": view.ref.key,
            "entities": [],
            "statements": [],
            "claims": [
                {
                    "id": "relation",
                    "subject": subject,
                    "predicate": "https://example.org/parent",
                    "object": {"kind": "entity", "target": endpoint},
                    "qualification": {"modality": "asserted", "polarity": True},
                    "establishment": "stated",
                    "evidence": [
                        {"sentence": sentence.id, "quote": "Alice is here.", "role": "primary"}
                    ],
                }
            ],
            "alternatives": [],
            "unsupported": [],
        }
        stored = locate_proposal(
            prepared, raw, packet.frame, known_classes=known_classes
        ).stored.model_dump(mode="python")
        config_id = conn.execute(
            select(table("ops.task").c.method_config_id).where(table("ops.task").c.id == task)
        ).scalar_one()
        (lease,) = claim_tasks(
            conn, run_id=run, config_id=config_id, holder="import-worker", agent=True
        )
        complete_task(
            conn,
            task_id=task,
            attempt=lease.attempt,
            holder="import-worker",
            prepared=prepared,
            observations=[
                {
                    "payload_definition": "AgentStoredBatch",
                    "item_key": "proposal",
                    "kind": "claim_proposal",
                    "payload": stored,
                    "source_view_id": view.ref.id,
                }
            ],
        )
        cut = seal_cut(conn, run, "final", final=True)
    return ImportedDeclarationCase(
        prepared, run, cut, prior_run, prior.realization_id, prior.data_revision, subject, endpoint
    )


def test_declared_membership_survives_known_object_import_without_new_declaration(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    case = imported_declaration_case(semantic_db_engine, semantic_writer_engine, tmp_path)
    result = consolidate_cut(semantic_writer_engine, case.cut, "imported-result")
    with semantic_writer_engine.connect() as conn:
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
    assert consolidate_cut(semantic_writer_engine, case.cut, "imported-result") == result


@pytest.mark.parametrize(
    "forgery", ["valid", "revision", "run", "entity", "class", "establishment"]
)
def test_native_imported_membership_requires_exact_bound_lineage(
    semantic_db_engine, semantic_writer_engine, tmp_path, forgery
):
    from corpus_structure.semantic.analytics import compile_projection
    from corpus_structure.semantic.arrow_publication import (
        SnapshotDerivedPublication,
        publish_arrow_on_connection,
    )
    from corpus_structure.semantic.domain_operations import NativeEvidenceLink, _cut_input
    from corpus_structure.semantic.publication import EvidenceSourceRow

    case = imported_declaration_case(semantic_db_engine, semantic_writer_engine, tmp_path)
    inputs = _cut_input(semantic_writer_engine, case.cut, "hostile")
    batch = inputs.batch
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
    with (
        pytest.raises(
            DBAPIError,
            match="entity input differs from bound evaluation input"
            if forgery in {"revision", "run"}
            else "membership requires establishment and support",
        )
        if forgery != "valid"
        else nullcontext(),
        semantic_writer_engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn,
        conn.begin(),
    ):
        conn.execute(
            text("SELECT data.begin_evaluation(:cut,:out)"), {"cut": case.cut, "out": "hostile"}
        )
        publish_arrow_on_connection(conn, publication)
        conn.execute(
            text("SELECT data.finish_evaluation(:cut,:out,:batch)"),
            {"cut": case.cut, "out": "hostile", "batch": batch.batch_id},
        )
    with semantic_writer_engine.connect() as conn:
        persisted = conn.execute(
            select(table("data.realization")).where(
                table("data.realization").c.realization_id == "hostile"
            )
        ).first()
        assert (persisted is not None) == (forgery == "valid")
