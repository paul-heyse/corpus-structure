"""Actual released statistics relations retain distinct qualified and nonfunctional facts."""

from pathlib import Path
from types import SimpleNamespace

from pydantic import BaseModel
from sqlalchemy import insert, select

from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import (
    OperationBinding,
    claim_tasks,
    complete_task,
    create_run,
    create_task,
    record_method,
    register_document,
    seal_cut,
)
from corpus_structure.semantic.proposals import (
    SEMANTIC_AGENT_VERSION,
    locate_proposal,
    native_source_frame,
    proposal_packet,
)
from corpus_structure.semantic.query import QuerySpec, read_session
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.source_frames import capture_source_frame
from semantic.inventory_reading import inventory_supports
from semantic.method_dimensions_support import prepare_fixture_pack


def test_actual_statistics_cut_keeps_piecewise_values_and_multiple_relation_targets(
    commit_db_engine, commit_writer_engine, commit_reader_engine, tmp_path
):
    root = Path(__file__).resolve().parents[4]
    bundle, dependencies, profile, prepared = prepare_fixture_pack(
        root / "domains/statistics", "pdf.controlled-source"
    )
    with commit_db_engine.begin() as conn:
        persist_release(conn, bundle, dependencies, profile, prepared)
        conn.execute(insert(table("data.project")).values(project_id="p"))
        conn.execute(
            insert(table("data.realization")).values(
                realization_id="source", project_id="p", release_id=prepared.release_id
            )
        )
    source = (
        "The density is 1 for x > 0 and 2 for x < 0. BranchFamily is a special "
        "case of FirstParent and SecondParent."
    )
    path = tmp_path / "Statistics.html"
    from pdf_acceptance_support import publish_controlled_pdf_views, write_controlled_pdf

    original = write_controlled_pdf(path, (source,))

    class SourceConfig(BaseModel):
        pass

    with commit_writer_engine.begin() as conn:
        document = register_document(
            conn,
            project_id="p",
            source_uri=path.as_uri(),
            original_path=str(path),
            original=original,
            metadata={"page": "Statistics.html"},
            mime="application/pdf",
        )
        key = conn.execute(
            select(table("kb.document").c.key).where(table("kb.document").c.id == document)
        ).scalar_one()
        run = create_run(
            conn,
            project_id="p",
            binding=OperationBinding(prepared.release_id, "source", 0, b"{}"),
            kind="full",
            options={"corpus": {"documents": [key]}},
            code_commit="test",
        )
    (view,) = publish_controlled_pdf_views(
        commit_writer_engine,
        prepared=prepared,
        run_id=run,
        document_id=document,
        original=original,
        paragraphs=(source,),
    )
    with commit_writer_engine.begin() as conn:
        unit_locator = view.ref.key
        frame = native_source_frame(view, (("s1", 0, len(source)),))
        packet = proposal_packet(prepared, frame, guideline="", configuration={})
        config = record_method(
            conn,
            SimpleNamespace(
                name="agent.opus",
                version=SEMANTIC_AGENT_VERSION,
                family="agent",
                tier="agent",
                confidence_source="agent",
                unit_type="source_view",
                Config=SourceConfig,
            ),
            "extract",
            {},
            "config",
            prepared=prepared,
        )
        task = create_task(
            conn,
            run_id=run,
            config_id=config,
            stage="propose",
            unit_type="source_view",
            unit_id=view.ref.id,
            unit_key=unit_locator,
            input_hash="input",
            packet_hash=packet.hash,
            agent=True,
        )
        claimed = claim_tasks(conn, run_id=run, config_id=config, holder="agent", agent=True)[0]
        capture_source_frame(conn, task, packet)
    namespace = "https://corpus-structure.dev/domains/statistics/"

    def formula(expression):
        return {"kind": "formula", "language": "latex", "expression": expression}

    claims = []
    for index, (expression, relation) in enumerate([("1", ">"), ("2", "<")]):
        claims.append(
            {
                "id": "density" + str(index),
                "subject": "family",
                "predicate": namespace + "pdf",
                "object": formula(expression),
                "qualification": {
                    "modality": "asserted",
                    "polarity": True,
                    "condition": {
                        "kind": "compare",
                        "relation": relation,
                        "lhs": formula("x"),
                        "rhs": formula("0"),
                    },
                },
                "establishment": "stated",
                "statement": "s",
                "statement_role": "conclusion",
                "evidence": [{"sentence": "s1", "quote": source, "role": "primary"}],
            }
        )
    for target in ("first", "second"):
        claims.append(
            {
                "id": target,
                "subject": "family",
                "predicate": namespace + "special_case_of",
                "object": {"kind": "entity", "target": target + "-entity"},
                "qualification": {"modality": "asserted", "polarity": True},
                "establishment": "stated",
                "statement": "s",
                "statement_role": "conclusion",
                "evidence": [{"sentence": "s1", "quote": source, "role": "primary"}],
            }
        )
    raw = {
        "unit_ref": unit_locator,
        "entities": [
            {"id": ref, "class_iri": namespace + "DistributionFamily", "label": label}
            for ref, label in [
                ("family", "BranchFamily"),
                ("first-entity", "FirstParent"),
                ("second-entity", "SecondParent"),
            ]
        ],
        "statements": [{"id": "s", "kind": "theorem", "anchor": unit_locator}],
        "claims": claims,
        "alternatives": [],
        "unsupported": [],
    }
    located = locate_proposal(
        prepared,
        raw,
        frame,
    )
    assert located.clean
    with commit_writer_engine.begin() as conn:
        complete_task(
            conn,
            task_id=task,
            attempt=claimed.attempt,
            holder="agent",
            prepared=prepared,
            observations=[
                {
                    "payload_definition": "AgentStoredBatch",
                    "item_key": "proposal",
                    "kind": "claim_proposal",
                    "payload": located.stored.model_dump(mode="python"),
                    "source_view_id": view.ref.id,
                }
            ],
        )
        cut = seal_cut(conn, run, "final", final=True)
    result = consolidate_cut(commit_writer_engine, cut, "evaluated")
    assert result.run_id == run
    with read_session(commit_reader_engine, "evaluated") as session:
        cls = session.class_handle("DistributionFamily")
        densities = session.query(QuerySpec(cls, session.property_handle(cls, "pdf"), "accepted"))
        relations = session.query(
            QuerySpec(cls, session.property_handle(cls, "special_case_of"), "accepted")
        )
        assert {row.object.expression for row in densities.rows} == {"1", "2"}
        qualifications = [
            row.qualification.model_dump()
            for row in densities.rows
            if row.qualification is not None
        ]
        assert len(qualifications) == 2
        assert {value["condition"]["relation"] for value in qualifications} == {"<", ">"}
        assert len(relations.rows) == 2
        assert len({row.object for row in relations.rows}) == 2
        assert all(
            len(inventory_supports(session, row.fact_id)) == 1
            for row in (*densities.rows, *relations.rows)
        )
