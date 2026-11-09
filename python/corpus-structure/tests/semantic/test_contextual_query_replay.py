"""Detached contextual replay binds the exact retained parser and rendered signal."""

from dataclasses import asdict
from hashlib import sha256

import pytest

from corpus_structure.core.evidence import config_key
from corpus_structure.methods.contextual_candidates import ContextualQueryConfig
from corpus_structure.methods.contextual_embeddings import E5, identity
from corpus_structure.semantic.contributions import (
    contribution_identity,
    occurrence_identity,
    operation_identity,
)
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.record_contracts import anchor_identity
from corpus_structure.semantic.source_contexts import record_source_pin
from corpus_structure.serve.contributions import ContributionRequest
from corpus_structure.serve.review_bundle import (
    ReviewSelection,
    verify_review_bundle,
    write_review_bundle,
)

from .test_section_heading_replay import _source
from .test_section_heading_replay import synthetic_source_projection as synthetic_source_projection


@pytest.mark.parametrize("substitution", [None, "cut", "endpoint", "receipt", "render", "vector"])
def test_detached_v11_query_receipt_uses_original_context(
    tmp_path, synthetic_source_projection, substitution
):
    release, project, runtime = "release", "project", "retained-runtime"
    pointer = "#/texts/30"
    text = "A supervisor approves the request."
    source, _ = _source(7, pointer, text, "text", release)
    pin = record_source_pin(native_source_frame(source, ()))

    def occurrence(literal, key, semantic_type, operation):
        start = text.index(literal)
        anchor = dict(
            pin=pin,
            pointer=pointer,
            space="native",
            precision="exact",
            start=start,
            end=start + len(literal),
            source_piece=literal,
        )
        anchor["anchor_id"] = anchor_identity(anchor)
        row = dict(
            pin=pin,
            kind="occurrence",
            semantic_type=semantic_type,
            item_key=key,
            anchors=[anchor],
            occurrence_id=occurrence_identity((anchor,)),
            operation_key=operation,
        )
        return dict(row, contribution_id=contribution_identity(row))

    predicate = occurrence("approves", "predicate", "source_occurrence", "parser-op")
    argument = occurrence("the request", "argument", "source_occurrence", "parser-op")
    root = dict(
        pin=pin,
        kind="group",
        semantic_type="linguistic.predicate_frame",
        item_key="frame",
        operation_key="parser-op",
        members=[predicate["contribution_id"], argument["contribution_id"]],
        value=source_value(
            dict(
                predicate="predicate",
                dependency_arguments=[dict(role="obj", location="argument")],
                srl_frames=[],
            )
        ),
    )
    root["contribution_id"] = contribution_identity(root)
    reference = dict(
        contribution_id=root["contribution_id"],
        project_id=project,
        release_id=release,
        run_id=9,
        cut_id=10,
        result_revision=4,
        selected_task_id=12,
        origin_task_id=11,
        runtime_fingerprint=runtime,
    )
    carrier = occurrence("request", "focal", "contextual.located_mention", "unbound")
    occurrence_id = carrier["occurrence_id"]
    cfg = ContextualQueryConfig.model_validate(
        dict(
            source_product_digest=pin["product_digest"],
            source_projection_digest=pin["projection_digest"],
            scope="fixture",
            relationship_constraints=[
                dict(
                    constraint_id="fixture-denotation",
                    relation_kinds=["denotes"],
                    occurrence_role="observed_source_mention",
                    target_role="retained_definition_component",
                    multiplicity="one",
                    exhaustive=False,
                )
            ],
            target_components=[
                dict(
                    reference=dict(
                        product_id="fixture-product",
                        component_id="b" * 64,
                        operation_id="structure.definition_components",
                        operation_version="9",
                        project_id=project,
                        release_id=release,
                        run_id=3,
                        cut_id=4,
                        result_revision=4,
                        selected_task_id=5,
                        origin_task_id=5,
                        runtime_fingerprint=runtime,
                        dependencies=["source"],
                    ),
                    label="request",
                    description="a document awaiting review",
                    scope="fixture",
                )
            ],
            query_context=dict(
                recipe="located-frame-1",
                bindings=[dict(occurrence_id=occurrence_id, evidence=reference)],
            ),
        )
    ).model_dump(mode="json")
    key = operation_identity("retrieve.contextual", "11", cfg, pin)
    carrier = occurrence("request", "focal", "contextual.located_mention", key)
    receipt = dict(
        recipe="located-frame-1",
        evidence=reference,
        signals=[
            dict(label="Predicate", anchor_ids=[predicate["anchors"][0]["anchor_id"]]),
            dict(label="Dependency obj", anchor_ids=[argument["anchors"][0]["anchor_id"]]),
        ],
        omissions=[],
    )
    representation = identity("located-query-context", receipt)
    actual_text = (
        "Mention: request\nType: unknown\nPredicate: approves\n"
        "Dependency obj: the request\nContext: A supervisor approves the request."
    )
    rendered = dict(
        object_id=occurrence_id,
        source_binding=pin["source"],
        role="query",
        text=actual_text,
        truncated=False,
        representation_digest=representation,
        final_input_digest=sha256((E5.query_prompt + actual_text).encode()).hexdigest(),
    )
    vector_binding = [
        occurrence_id,
        pin["source"],
        E5.profile_id,
        rendered["final_input_digest"],
        representation,
    ]
    vector = dict(
        vector_id=identity("context-vector", vector_binding),
        object_id=occurrence_id,
        source_binding=pin["source"],
        profile_id=E5.profile_id,
        input_digest=rendered["final_input_digest"],
        representation_digest=representation,
        values=[1.0, *([0.0] * (E5.dimension - 1))],
    )
    parser_rows = [root, predicate, argument]
    report = dict(
        origin_task_id=21,
        origin_unit_id=source.ref.id,
        unit_type="source_view",
        project_id=project,
        method="retrieve.contextual",
        configuration=cfg,
        origin_run_id=19,
        runtime_fingerprint=runtime,
        body=dict(
            source=pin["source"],
            operation_version="11",
            release_id=release,
            configuration_hash=config_key("retrieve.contextual", "11", cfg),
            contributions=[carrier],
            parse_detail=source_value(
                dict(
                    query_context={occurrence_id: dict(receipt, outcome="rendered")},
                    encoder_inputs=[rendered],
                )
            ),
            contribution_operations=[
                dict(
                    operation_key=key,
                    operation_version="11",
                    outcome="succeeded",
                    question="retained producer occurrence roles and contextual encoder products",
                    computation_dependencies=[root["contribution_id"]],
                    contextual_enrichment=dict(
                        candidate_lists=[],
                        vectors=[vector],
                        profiles=[dict(profile_id=E5.profile_id, dimension=E5.dimension)],
                        inventories=[dict(inventory_id="fixture", targets=[], semantic_groups=[])],
                        neighborhood=dict(
                            policy="mutual-exact-cosine-top5-2",
                            inventory_id="fixture",
                            profile_id=E5.profile_id,
                            status="completed",
                            directed_ranks=[],
                            edges=[],
                        ),
                    ),
                )
            ],
        ),
    )
    if substitution == "receipt":
        receipt["signals"][1]["anchor_ids"] = receipt["signals"][0]["anchor_ids"]
    if substitution == "render":
        rendered["text"] = rendered["text"].replace("Dependency obj:", "Dependency nsubj:")
        rendered["final_input_digest"] = sha256(
            (E5.query_prompt + rendered["text"]).encode()
        ).hexdigest()
    if substitution == "vector":
        vector["representation_digest"] = "foreign"
    # Re-encode modified payloads so all JSON/Parquet and content digests remain internally valid.
    report["body"]["parse_detail"] = source_value(
        dict(
            query_context={occurrence_id: dict(receipt, outcome="rendered")},
            encoder_inputs=[rendered],
        )
    )

    def rows():
        binding = dict(release_id=release, data_revision=4)
        yield (
            "selections",
            dict(selection_index=0, run_id=19, cut_id=20, project_id=project, binding=binding),
        )
        yield (
            "selections",
            dict(
                selection_index=1,
                run_id=9,
                cut_id=99 if substitution == "cut" else 10,
                project_id=project,
                binding=binding,
            ),
        )
        yield (
            "inventory",
            dict(
                selection_index=0,
                population="report",
                row=dict(
                    origin_task_id=21,
                    selected_task_id=21,
                    source_view_id=source.ref.id,
                    cut_member=True,
                    origin_run_id=19,
                    origin_project_id=project,
                    runtime_fingerprint=runtime,
                ),
            ),
        )
        for parser in parser_rows[:-1] if substitution == "endpoint" else parser_rows:
            yield (
                "inventory",
                dict(
                    selection_index=1,
                    population="contribution",
                    row=dict(
                        contribution_id=parser["contribution_id"],
                        source_view_id=source.ref.id,
                        selected_task_id=12,
                        origin_task_id=11,
                        origin_run_id=8,
                        origin_project_id=project,
                        runtime_fingerprint=runtime,
                        cut_member=True,
                    ),
                ),
            )
        yield "contracts", dict(release_id=release)
        yield "reports", report
        yield (
            "reports",
            dict(
                origin_task_id=11,
                origin_run_id=8,
                origin_unit_id=source.ref.id,
                unit_type="source_view",
                project_id=project,
                method="extract.pm2_hanlp",
                runtime_fingerprint=runtime,
                body=dict(source=pin["source"], release_id=release, contributions=parser_rows),
            ),
        )
        yield (
            "sources",
            dict(
                source_view_id=source.ref.id,
                ref=asdict(source.ref),
                text=text,
                context=source.context(),
            ),
        )
        yield (
            "closure_dependencies",
            dict(
                required_by="origin-task:21", reason="declared_query_context", reference=reference
            ),
        )

    selection = ReviewSelection(
        selections=(ContributionRequest(run_id=19), ContributionRequest(run_id=9))
    )
    destination = tmp_path / "receipt"
    errors = dict(
        cut="exact selected raw producer custody",
        endpoint="selected endpoint inventory missing",
        receipt="receipt differs from original parser evidence",
        render="rendering differs from its source and signal",
        vector="vector differs from the retained encoder input",
    )
    if substitution:
        with pytest.raises(ValueError, match=errors[substitution]):
            write_review_bundle(selection, destination, rows())
        assert not destination.exists()
    else:
        manifest = write_review_bundle(selection, destination, rows())
        assert verify_review_bundle(destination) == manifest
