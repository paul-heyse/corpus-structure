"""Current pack journeys over independently authored, controlled PDF source paragraphs.

The paragraph/answer author owns expected meaning. This helper supplies only native source
custody, current pack preparation, task leasing and the production finalization boundary.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import anyio
from fastmcp import Client
from pdf_acceptance_support import publish_controlled_pdf_views, write_controlled_pdf
from sqlalchemy import Engine, insert

from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.orchestrate.semantic import queue_agent
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operation_results import RunId
from corpus_structure.semantic.operations import OperationBinding, create_run, register_document
from corpus_structure.semantic.regeneration import prepare_pack
from corpus_structure.semantic.releases import activate_release, persist_release
from corpus_structure.semantic.types import PreparedRelease

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
        keys=tuple(f"reference.pdf#case-{i}" for i in range(len(cases))),
    )
    with writer.begin() as conn:
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
