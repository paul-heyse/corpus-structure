"""Current pack journeys over independently authored, controlled PDF source paragraphs.

The paragraph/answer author owns expected meaning. This helper supplies only native source
custody, current pack preparation, task leasing and the production finalization boundary.
"""

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

import anyio
import pytest
from fastmcp import Client
from pdf_acceptance_support import publish_controlled_pdf_views, write_controlled_pdf
from sqlalchemy import Engine, insert, select, text

from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.evaluate.record_alignment import RecordEvaluationFrame
from corpus_structure.evaluate.record_references import (
    PROTOCOL,
    assign_origin,
    create_reference_set,
    reference_inputs,
    source_binding,
)
from corpus_structure.evaluate.semantic import split_documents
from corpus_structure.evaluate.split import SplitConfig
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.orchestrate.semantic import queue_agent
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operation_results import RunId
from corpus_structure.semantic.operations import (
    OperationBinding,
    create_run,
    register_document,
    seal_cut,
)
from corpus_structure.semantic.record_contracts import (
    anchor_identity,
    evidence_set_identity,
    interpretation_identity,
    record_identity,
)
from corpus_structure.semantic.releases import activate_release, persist_release
from corpus_structure.semantic.types import PreparedRelease
from semantic import native_record_fixtures as source_fixture
from semantic.conftest import (
    semantic_db_engine as semantic_db_engine,
)
from semantic.conftest import (
    semantic_evaluator_engine as semantic_evaluator_engine,
)
from semantic.conftest import (
    semantic_reader_engine as semantic_reader_engine,
)
from semantic.conftest import (
    semantic_writer_engine as semantic_writer_engine,
)
from semantic.native_record_fixtures import private_source as private_source

from .agent_scenarios import lease_and_read


def publish_reference_case(
    admin: Engine,
    writer: Engine,
    directory: Path,
    domain: str,
    cases: Sequence[tuple[str, dict[str, Any]]],
) -> tuple[PreparedRelease, RunId, tuple[str, ...]]:
    """Each case is (independent paragraph, authored current proposal batch)."""
    if len(cases) != 1:
        raise ValueError("reference journeys use one independently authored source paragraph")
    # Production preparation reuse is keyed by exact acquired inputs. A domain-name
    # cache here would conceal a changed pack or query implementation in this process.
    from .method_dimensions_support import prepare_fixture_pack

    bundle, deps, profile, prepared = prepare_fixture_pack(
        DOMAINS / domain, "pdf.controlled-source", "coverage.witness"
    )
    with admin.begin() as conn:
        persist_release(conn, bundle, deps, profile, prepared)
        conn.execute(insert(table("data.project")).values(project_id="reference"))
        activate_release(
            conn, "reference", prepared.release_id, expected_parent=None, expected_generation=0
        )
        conn.execute(
            insert(table("data.realization")).values(
                project_id="reference",
                realization_id="input",
                release_id=prepared.release_id,
            )
        )
    paragraphs = tuple(text for text, _ in cases)
    path = directory / "reference.pdf"
    original = write_controlled_pdf(path, paragraphs)
    config = {
        "model": "authored-current-reference",
        "mode": "extract",
        "max_units": len(cases),
        "packet_cap_chars": 18000,
        "sentences": SentenceConfig().model_dump(mode="json"),
    }
    with writer.begin() as conn:
        run = create_run(
            conn,
            project_id="reference",
            binding=OperationBinding(prepared.release_id, "input", 0, b"{}"),
            kind="full",
            options={"agent_configs": {"agent.opus/extract": config}, "domain": domain},
            code_commit="authored-current-reference",
        )
        document = register_document(
            conn,
            project_id="reference",
            source_uri="reference.pdf",
            original_path=str(path),
            original=original,
            metadata={"page": "reference.pdf"},
            mime="application/pdf",
        )
    views = publish_controlled_pdf_views(
        writer,
        prepared=prepared,
        run_id=run,
        document_id=document,
        original=original,
        paragraphs=paragraphs,
    )
    from .primary_native_support import bind_primary_agent_run

    with writer.begin() as conn:
        run, config = bind_primary_agent_run(
            conn, run, prepared, tuple(v.ref.id for v in views), config
        )
        tasks = queue_agent(
            conn,
            run_id=run,
            prepared=prepared,
            configuration=config,
            units=tuple(UnitRef(TaskUnitType.SOURCE_VIEW, v.ref.id, v.ref.key) for v in views),
        )

    async def submit():
        async with Client(build_semantic_server(SemanticAgentSession(writer, run))) as client:
            for task, view, (paragraph, batch) in zip(tasks, views, cases, strict=True):
                unit = await lease_and_read(client, run, task)
                sentence = unit["sentences"][0]["id"]
                # Sentence identifiers and unit custody are mechanics, not expected meaning.
                import copy

                batch = copy.deepcopy(batch)
                batch["unit_ref"] = view.ref.key
                for statement in batch.get("statements", ()):
                    statement["anchor"] = sentence
                for entity in batch.get("entities", ()):
                    for attribute in entity.get("attributes", ()):
                        # Expected attribute meaning and its own quote are authored by the
                        # caller. Only the acquired sentence identifier is supplied here.
                        for citation in attribute["evidence"]:
                            matches = [
                                s for s in unit["sentences"] if citation["quote"] in s["text"]
                            ]
                            assert len(matches) == 1, (citation["quote"], unit["sentences"])
                            citation["sentence"] = matches[0]["id"]
                for claim in batch.get("claims", ()):
                    evidence = claim.get("evidence", [{"quote": paragraph, "role": "primary"}])
                    for citation in evidence:
                        matches = [s for s in unit["sentences"] if citation["quote"] in s["text"]]
                        assert len(matches) == 1, (citation["quote"], unit["sentences"])
                        citation["sentence"] = matches[0]["id"]
                    claim["evidence"] = evidence
                response = await client.call_tool(
                    "propose_claims", {"task_id": task, "batch": batch}
                )
                assert response.structured_content is not None
                assert (
                    response.structured_content["submission_disposition"] == "completed_accepted"
                ), response.structured_content
                assert response.structured_content["rejected"] == [], response.structured_content
                assert response.structured_content["accepted"]["claims"] == len(
                    batch.get("claims", ())
                ), response.structured_content

    anyio.run(submit)
    finalize_bound_run(writer, run, "reference-result")
    return prepared, run, tuple(v.ref.key for v in views)


@pytest.fixture
def private_source_options():
    return dict(bundle_transform=reference_inputs)


@pytest.fixture
def reference_source(private_source):
    case = private_source
    with case.writer.begin() as conn:
        source_fixture.complete(case, conn, ())
        case.cut = seal_cut(conn, case.run, "source-ready-references", final=False)
    return case


def expected_reading(case, logical_source):
    view = case.view_row
    pin = dict(
        source=logical_source,
        native_product_task_id=view["native_task_id"],
        product_key=view["native_product_key"],
        product_digest=view["native_content_digest"],
        projection_digest=view["projection_digest"],
        recipe_digest=view["recipe_digest"],
        source_view_id=case.view,
    )
    pointer = case.table + "/data/table_cells/0"
    anchors = [
        dict(
            pin=pin,
            space="native",
            pointer=pointer,
            precision="exact",
            start=0,
            end=2,
            source_piece="12",
        ),
        dict(pin=pin, space="native", pointer=pointer, precision="item"),
    ]
    for anchor in anchors:
        anchor["anchor_id"] = anchor_identity(anchor)
    sets = [
        dict(role=role, ordering="ordered", usage=usage, anchors=(anchor["anchor_id"],))
        for role, usage, anchor in zip(
            ("value", "location"), ("literal", "native"), anchors, strict=True
        )
    ]
    for evidence in sets:
        evidence["set_id"] = evidence_set_identity(evidence)
    fields = (
        dict(
            role="value",
            kind="literal",
            state="present",
            meaning_changing=True,
            evidence_status="available",
            evidence_sets=(sets[0]["set_id"],),
            value=dict(kind="decimal", lexical="12"),
            original="12",
            reason="source-read",
        ),
        dict(
            role="location",
            kind="native",
            state="present",
            meaning_changing=True,
            evidence_status="available",
            evidence_sets=(sets[1]["set_id"],),
            value=dict(kind="native_location", pointer=pointer),
        ),
    )
    row: dict[str, Any] = dict(
        contract="FixtureRecordFields",
        family="table",
        occurrence_recipe="source-anchor-membership-1",
        pin=pin,
        occurrence_anchors=(anchors[1]["anchor_id"],),
        standing="accepted",
        policy_version="reference-reading-1",
        anchors=tuple(anchors),
        evidence_sets=tuple(sets),
        fields=fields,
    )
    row["record_id"] = record_identity(case.prepared.release_id, row)
    row["interpretation_id"] = interpretation_identity(row)
    scopes = tuple(
        {
            key: value
            for key, value in anchor.items()
            if key in {"pin", "space", "pointer", "precision", "start", "end"}
        }
        for anchor in anchors
    )
    frame = RecordEvaluationFrame(
        view["key"],
        case.prepared.release_id,
        "independent-cell-guideline-1",
        "reference-reading-1",
        "m1-candidate-only-1",
        pin,
        frozenset(),
        anchor_scopes=scopes,
    )
    return row, frame


def create_case(
    conn,
    case,
    partition,
    *,
    captured_coordinates=(),
    include_empty_secondary=False,
    anchor_ids_only=False,
    reading=expected_reading,
    origin_group="one-original-fixture",
    label="independent-cell-reference",
):
    uri = conn.scalar(
        select(table("kb.document").c.source_uri).where(
            table("kb.document").c.id == case.view_row["document_id"]
        )
    )
    assign_origin(
        conn,
        project_id="private-records",
        origin_group=origin_group,
        partition=partition,
        source_uris=(uri,),
        provenance=dict(
            origin="independently authored two-cell native fixture",
            copies_and_editions="all coassigned",
            independence_claim="none",
        ),
    )
    split_documents(
        conn,
        "private-records",
        SplitConfig(forced_dev={uri: "controlled reference source"}),
        release_id=case.prepared.release_id,
    )
    logical = source_binding(
        conn, source_run_id=case.run, source_view_id=case.view, source_cut_id=case.cut
    )
    row, frame = reading(case, logical)
    if anchor_ids_only:
        frame = replace(
            frame,
            anchor_ids=frozenset(anchor["anchor_id"] for anchor in row["anchors"]),
            anchor_scopes=(),
        )
    frames = {frame.unit: frame}
    if include_empty_secondary:
        other = (
            conn.execute(
                select(table("kb.source_view")).where(
                    table("kb.source_view").c.id == case.other_view
                )
            )
            .mappings()
            .one()
        )
        pin = dict(
            source=source_binding(
                conn, source_run_id=case.run, source_view_id=case.other_view, source_cut_id=case.cut
            ),
            native_product_task_id=other["native_task_id"],
            product_key=other["native_product_key"],
            product_digest=other["native_content_digest"],
            projection_digest=other["projection_digest"],
            recipe_digest=other["recipe_digest"],
            source_view_id=other["id"],
        )
        frames[other["key"]] = replace(
            frame,
            unit=other["key"],
            pin=pin,
            anchor_scopes=(
                dict(
                    pin=pin, space="native", pointer=case.sibling, precision="exact", start=0, end=2
                ),
            ),
        )
    created = create_reference_set(
        conn,
        project_id="private-records",
        source_run_id=case.run,
        source_cut_id=case.cut,
        label=label,
        legacy_split="dev",
        guideline=frame.guideline_version,
        guideline_text=(
            "Read exact cell spelling and source location; preserve faithful complete readings."
        ),
        partition=partition,
        unit_keys=tuple(frames),
        frames=frames,
        captured_coordinates={frame.unit: captured_coordinates},
        reference_policy_version=frame.reference_policy_version,
        prediction_policy_version=frame.prediction_policy_version,
        sampling=dict(
            seed=37,
            strata={key: "independent-source-region" for key in frames},
            inclusion_probabilities={key: 1 for key in frames},
            provenance=dict(source="controlled native source, no producer candidates"),
            cohort="native machinery control",
        ),
    )
    unit = (
        conn.execute(
            select(table("eval.reference_unit")).where(
                table("eval.reference_unit").c.set_id == created["set_id"],
                table("eval.reference_unit").c.unit_key == frame.unit,
            )
        )
        .mappings()
        .one()
    )
    return created, unit, row, frame


def native_pass(conn, unit, row, frame, kind, actor, parents=()):
    authored = canonical_bytes(
        dict(
            protocol=PROTOCOL,
            release_id=frame.release_id,
            unit_ref=frame.unit,
            guideline=frame.guideline_version,
            reference_policy_version=frame.reference_policy_version,
            prediction_policy_version=frame.prediction_policy_version,
            reason=(
                "Independent reading of the complete supported source record, "
                "including explicit empty regions."
            ),
            adjudication_passes=parents,
            records=[] if row is None else [row],
        )
    )
    return conn.scalar(
        text("SELECT eval.record_source_record_reference_pass(:u,:k,:a,:b,CAST(:f AS jsonb))"),
        dict(
            u=unit["id"],
            k=kind,
            a=actor,
            b=authored,
            f=canonical_bytes(unit["context"][0]).decode(),
        ),
    )
