"""An admitted declaration-only class survives supported known-reference import."""

from dataclasses import dataclass
from pathlib import Path

from scenario_recipes import register_scenario_builder
from sqlalchemy import Engine, select

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
from semantic.domain_scenarios import build_domain_case


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

    @property
    def seed_files(self) -> tuple[Path, ...]:
        return ()

    def validate_clone(self, admin: Engine) -> None:
        from corpus_structure.semantic._operation_ids import DocumentId
        from corpus_structure.semantic.operations import read_original

        documents, artifacts = table("kb.document"), table("kb.source_artifact")
        with admin.connect() as conn:
            retained = conn.execute(
                select(documents.c.id, artifacts.c.artifact_digest).select_from(
                    documents.outerjoin(
                        artifacts, artifacts.c.artifact_digest == documents.c.content_hash
                    )
                )
            ).all()
            if len(retained) != 2 or any(digest is None for _, digest in retained):
                raise ValueError("imported membership seed lacks its two retained originals")
            for document, _ in retained:
                read_original(conn, DocumentId(document), prepared=self.prepared)
            cut = table("ops.input_cut")
            if (
                conn.scalar(select(cut.c.run_id).where(cut.c.id == self.cut, cut.c.final))
                != self.run
            ):
                raise ValueError("imported membership seed lacks its sealed importing cut")


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
        characterization=True,
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
    )
    from semantic.primary_native_support import bind_primary_agent_run

    with writer.begin() as conn:
        run, configuration = bind_primary_agent_run(
            conn, run, prepared, (view.ref.id,), configuration, method="agent.general"
        )
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


@dataclass(frozen=True)
class ImportedDeclarationRecipe:
    """One exact supported known-reference lineage preparation."""


def build_imported_declaration_recipe(recipe, admin, writer, directory, *, purpose_engine=None):
    return imported_declaration_case(admin, writer, directory)


register_scenario_builder(ImportedDeclarationRecipe, build_imported_declaration_recipe)
