"""Run the ordinary scoped-relation and contextual graph for one retained source cue."""

import argparse
import json
from pathlib import Path

from sqlalchemy import select

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.methods.contextual_candidates import ContextualCandidatesWithNamedBindings
from corpus_structure.methods.scoped_relations import ScopedRelationsWithRoleClosure
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import ExternalSourceRef, StructuralInput
from corpus_structure.settings import Settings


def replay(inventory: dict, binding: dict, output: Path, *, mapped_pieces: bool) -> dict:
    if inventory["outcome"] != "passed" or inventory["consuming_release"] != binding["release_id"]:
        raise ValueError("replay requires the inventory checked under the exact consuming release")
    cue = ExternalSourceRef.model_validate(inventory["cue_source"])
    scope = inventory["scope"]
    inputs = StructuralInput.model_validate(
        {
            "question": "Recover the explicitly cited numbered section from retained source",
            "scope": scope,
            "inventory_id": f"section-replay:{cue.identity}",
            "policy_id": "source-grounded-private-proposals-2",
            "sources": [cue],
            "passages": [inventory["cue_passage"]],
            "dependencies": [cue.identity],
        }
    )
    if mapped_pieces:
        from corpus_structure.methods.scoped_relations import ScopedRelationsWithJoinedCitations

        scoped = ScopedRelationsWithJoinedCitations()
    else:
        scoped = ScopedRelationsWithRoleClosure()
    contextual = ContextualCandidatesWithNamedBindings()
    registry = MethodRegistry(
        (scoped, contextual),
        MethodsFile(
            configs={
                scoped.name: {
                    "bounded": {
                        "inputs": inputs.model_dump(mode="json"),
                        "structural_input_digest": inputs.identity,
                    }
                },
                contextual.name: {
                    "bounded": {
                        "profile": "e5",
                        "source_dependency_method": scoped.name,
                        "semantic_types": ["structural.located_participant"],
                        "section_sources": inventory["source_refs"],
                        "source_product_digest": cue.native_content_digest,
                        "source_projection_digest": cue.projection_digest,
                        "scope": scope,
                    }
                },
            }
        ),
    )
    graph = Graph(
        (
            (
                Stage.SCOPE,
                (
                    Step(f"{scoped.name}/bounded"),
                    Step(f"{contextual.name}/bounded", upstream=(scoped.name,)),
                ),
            ),
        ),
        policy_propose=False,
    )
    with open_runtime_engine(Settings(), "pm2-section-replay", purpose="write") as engine:
        with read_snapshot(engine) as conn:
            prepared = open_release(conn, binding["release_id"])
            realization = table("data.realization")
            revision = conn.execute(
                select(realization.c.data_revision).where(
                    realization.c.realization_id == binding["realization_id"],
                    realization.c.release_id == prepared.release_id,
                    realization.c.project_id == binding["project"],
                )
            ).scalar_one()
        result = run_source_methods(
            engine,
            project_id=binding["project"],
            prepared=prepared,
            binding=OperationBinding(
                prepared.release_id,
                binding["realization_id"],
                revision,
                canonical_bytes({"source": cue.identity, "scope": scope}),
            ),
            registry=registry,
            graph=graph,
            method_settings=MethodSettings(
                data_dir=output, model_cache=Path.home() / ".cache/docling/models"
            ),
            selected_sources=(cue,),
            kind="slice",
        )
    return result.model_dump(mode="json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--mapped-pieces", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            replay(
                json.loads(args.inventory.read_bytes()),
                json.loads(args.binding.read_bytes()),
                args.data_dir,
                mapped_pieces=args.mapped_pieces,
            ),
            indent=2,
        )
    )
