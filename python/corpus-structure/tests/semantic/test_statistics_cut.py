"""Actual released statistics relations retain distinct qualified and nonfunctional facts."""

from pathlib import Path
from types import SimpleNamespace

from pydantic import BaseModel
from sqlalchemy import insert, select

from corpus_structure.core.evidence import RenditionContent, Segment
from corpus_structure.core.locators import LocatorIndex
from corpus_structure.core.vocab import SegmentKind
from corpus_structure.semantic import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic.analytical_profile import analytical_inputs
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.domain_operations import consolidate_cut, domain_rule_inputs
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.observations import observation_inputs
from corpus_structure.semantic.operations import (
    OperationBinding,
    claim_tasks,
    complete_task,
    create_run,
    create_task,
    record_method,
    register_document,
    seal_cut,
    store_rendition,
)
from corpus_structure.semantic.proposals import (
    ProposalFrame,
    ProposalSentence,
    locate_proposal,
    proposal_inputs,
    proposal_packet,
)
from corpus_structure.semantic.query import QuerySpec, read_session
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.source_frames import capture_source_frame


def test_actual_statistics_cut_keeps_piecewise_values_and_multiple_relation_targets(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    root = Path(__file__).resolve().parents[4]
    model = root / "python/corpus-structure/src/corpus_structure/model/semantic"
    dependencies = domain_rule_inputs(
        ResolvedDependencies(),
        (root / "domains/statistics/schema/rules.yaml").read_bytes(),
        (root / "domains/core/schema/rules.yaml").read_bytes(),
    )
    bundle = SourceBundle(
        "statistics_semantic",
        (
            SourceArtifact(
                "statistics_semantic", (root / "domains/statistics/semantic.yaml").read_bytes()
            ),
            SourceArtifact("semantic_core", (model / "core.yaml").read_bytes()),
        ),
    )
    bundle = observation_inputs(
        proposal_inputs(bundle, dependencies, qualification_class="StatisticsQualification")
    )
    bundle, dependencies = analytical_inputs(bundle, dependencies)
    dependencies = composed_dependencies(dependencies)
    profile = PreparationProfile(version="semantic-2")
    prepared = prepare_release(bundle, dependencies, profile)
    with semantic_db_engine.begin() as conn:
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
    path.write_text(source)
    sentence = Segment(kind=SegmentKind.SENTENCE, start=0, end=len(source))
    paragraph = Segment(kind=SegmentKind.PARAGRAPH, start=0, end=len(source), children=(sentence,))
    content = RenditionContent(
        canonical_text=source,
        document=Segment(
            kind=SegmentKind.DOCUMENT, start=0, end=len(source), children=(paragraph,)
        ),
    )
    locators = LocatorIndex(content, "Statistics.html")
    unit_locator = str(locators.generate(paragraph))
    frame = ProposalFrame(
        unit_locator,
        source,
        (ProposalSentence("s1", str(locators.generate(sentence)), 0, len(source)),),
    )
    packet = proposal_packet(prepared, frame, guideline="", configuration={})

    class SourceConfig(BaseModel):
        pass

    with semantic_writer_engine.begin() as conn:
        document = register_document(
            conn,
            project_id="p",
            source_uri=path.as_uri(),
            original_path=str(path),
            original=path.read_bytes(),
            metadata={"page": "Statistics.html"},
         mime='text/html')
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
        config = record_method(
            conn,
            SimpleNamespace(
                name="agent.opus",
                version="1",
                family="agent",
                tier="agent",
                confidence_source="agent",
                unit_type="document",
                Config=SourceConfig,
            ),
            "extract",
            {},
            "config",
        )
        task = create_task(
            conn,
            run_id=run,
            config_id=config,
            stage="propose",
            unit_type="document",
            unit_id=document,
            unit_key=unit_locator,
            input_hash="input",
            packet_hash=packet.hash,
            agent=True,
        )
        claimed = claim_tasks(conn, run_id=run, config_id=config, holder="agent", agent=True)[0]
        rendition = store_rendition(
            conn,
            run_id=run,
            document_id=document,
            content=content,
            task_id=task,
            config_id=config,
            parse_detail={},
        )
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
    with semantic_writer_engine.begin() as conn:
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
                    "rendition_id": rendition,
                }
            ],
        )
        cut = seal_cut(conn, run, "final", final=True)
    result = consolidate_cut(semantic_writer_engine, cut, "evaluated")
    assert result.run_id == run
    with read_session(semantic_reader_engine, "evaluated") as session:
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
            len(session.explain(row.fact_id).supports) == 1
            for row in (*densities.rows, *relations.rows)
        )
