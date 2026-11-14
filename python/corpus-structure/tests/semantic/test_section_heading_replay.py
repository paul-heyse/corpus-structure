"""Detached section citation replay over a controlled complete native packet."""

import base64
import json
from copy import deepcopy
from dataclasses import asdict, replace
from hashlib import sha256
from types import SimpleNamespace

import pytest
from methods.m1_producer_support import view

from corpus_structure.core.evidence import config_key
from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.methods.contextual_candidates import (
    ContextualCandidatesWithQueryContext,
    ContextualQueryConfig,
)
from corpus_structure.methods.contextual_embeddings import identity
from corpus_structure.semantic.contributions import contribution_identity, occurrence_identity
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.record_contracts import anchor_identity
from corpus_structure.semantic.source_contexts import record_source_pin
from corpus_structure.semantic.structural_products import ExternalSourceRef
from corpus_structure.serve.contributions import ContributionRequest
from corpus_structure.serve.review_bundle import (
    SECTION_PACKET_INPUT,
    ReviewSelection,
    verify_review_bundle,
    write_review_bundle,
)
from semantic.review_bundle_doubles import (
    synthetic_source_projection as synthetic_source_projection,
)


def _source(view_id, pointer, text, label, release):
    original = view()
    product = replace(original.ref.native_product, content_digest=f"{view_id:x}" * 64)
    pieces = (dict(kind="native_text", item_ref=pointer, start=0, end=len(text)),)
    items = (
        original.items[0],
        dict(self_ref=pointer, label=label, text=text, content_layer="body"),
    )
    projection = dict(
        text=text,
        pieces=pieces,
        items=[item["self_ref"] for item in items],
        ancestors=[],
        health={},
    )
    prepared = replace(
        original,
        ref=replace(
            original.ref,
            id=view_id,
            key=f"source:{view_id}",
            document_id=view_id,
            native_product=product,
            projection_digest=sha256(canonical_bytes(projection)).hexdigest(),
        ),
        text=text,
        pieces=pieces,
        items=items,
    )
    ref = ExternalSourceRef(
        project_id="project",
        run_id=1,
        cut_id=2,
        release_id=release,
        result_revision=0,
        source_view_id=view_id,
        native_task_id=prepared.ref.native_product.task_id,
        native_product_key=prepared.ref.native_product.product_key,
        native_content_digest=prepared.ref.native_product.content_digest,
        projection_digest=prepared.ref.projection_digest,
        recipe_digest=prepared.ref.recipe_digest,
        coordinate_version=2,
    )
    return prepared, ref


@pytest.mark.parametrize("outside", [False, True])
@pytest.mark.parametrize("version", ["11", "12"])
def test_detached_section_replay_requires_complete_witnesses(
    monkeypatch, tmp_path, outside, version, synthetic_source_projection
):
    work = "c" * 64
    documents = {view_id: {"content_hash": f"{view_id + 1:x}" * 64} for view_id in (7, 8, 9)}
    packet = canonical_bytes(
        {
            "version": 1,
            "packets": {row["content_hash"]: work for row in documents.values()},
            "native_products": {
                f"{view_id:x}" * 64: row["content_hash"] for view_id, row in documents.items()
            },
        }
    )
    manifest = canonical_bytes(
        {"dependencies": [[SECTION_PACKET_INPUT, sha256(packet).hexdigest()]]}
    )
    release = "release:" + sha256(manifest).hexdigest()
    contract = {
        "release_id": release,
        "section_packets": {
            "manifest_base64": base64.b64encode(manifest).decode(),
            "input_base64": base64.b64encode(packet).decode(),
        },
    }
    source, cue = _source(7, "#/texts/1", "See Section 6.2.", "text", release)
    first, first_ref = _source(8, "#/texts/2", "6.2 First heading", "section_header", release)
    second, second_ref = _source(9, "#/texts/3", "6.2 Second heading", "section_header", release)
    from methods.navigation_fixture import primary_navigation

    from corpus_structure.methods.witnessed_source_links import (
        match_named_source_links,
        navigation_index,
    )
    from corpus_structure.semantic.structural_products import StructuralPassage

    primary_by_view = {entry.ref.id: primary_navigation(entry) for entry in (source, first, second)}
    primary_layers = {
        pin: layer for layers in primary_by_view.values() for pin, layer in layers.items()
    }
    selected = StructuralPassage(
        passage_id="cue",
        source_ref="cue",
        scope="chapter",
        start=0,
        end=len(source.text),
        text=source.text,
    )
    inspection = match_named_source_links(
        source.text,
        source.pieces,
        {item["self_ref"]: item for item in source.items},
        (selected,),
        primary_layers=primary_by_view[source.ref.id],
        projection=source.ref.projection_digest,
        source_view_id=source.ref.id,
    )
    (citation,) = [match for match in inspection.matches if match.kind == "section_citation"]
    pin = record_source_pin(native_source_frame(source, ()))
    anchor = dict(
        pin=pin,
        space="native",
        pointer="#/texts/1",
        precision="exact",
        start=4,
        end=15,
        source_piece="Section 6.2",
    )
    anchor["anchor_id"] = anchor_identity(anchor)
    original = dict(
        kind="occurrence",
        semantic_type="structural.located_participant",
        operation_key="named",
        item_key="mention",
        pin=pin,
        anchors=(anchor,),
        occurrence_id=occurrence_identity((anchor,)),
        value=source_value(
            dict(
                role="named_link_subject",
                source_pointer="#/texts/1",
                start=4,
                end=15,
                text="Section 6.2",
                named_cue=citation.evidence(),
                primary_node=citation.witness.primary_node,
            )
        ),
    )
    original["contribution_id"] = contribution_identity(original)
    scoped = dict(
        origin_task_id=101,
        origin_unit_id=7,
        method="structure.scoped_relations",
        project_id="project",
        configuration={},
        body=dict(
            source=source.ref.key,
            release_id=release,
            operation_version="17",
            contributions=[original],
            origin_task_id=101,
        ),
    )

    def heading_targets(refs, *_):
        targets = []
        for target, target_ref in ((first, first_ref), (second, second_ref)):
            if target_ref not in refs:
                continue
            pointer, label = target.items[1]["self_ref"], target.text
            targets.append(
                dict(
                    target_id=identity(
                        "section-heading",
                        [
                            target_ref.native_content_digest,
                            target_ref.native_product_key,
                            pointer,
                            0,
                            len(label),
                        ],
                    ),
                    pointer=pointer,
                    label=label,
                    designator="6.2",
                    primary_witnesses=[
                        record.reference.values()
                        for record in navigation_index(
                            primary_by_view[target.ref.id],
                            target.ref.projection_digest,
                            source_view_id=target.ref.id,
                        ).select("section_heading")
                    ],
                    scope="chapter",
                    work_id="parent-pdf:" + work,
                    citations=[target_ref.model_dump(mode="json")],
                )
            )
        return {"targets": sorted(targets, key=lambda row: row["target_id"]), "complete": True}

    def unavailable(_profile):
        raise OSError("controlled encoder failure")

    monkeypatch.setattr(
        "corpus_structure.methods.contextual_candidates.verify_encoder_implementation", unavailable
    )
    config = ContextualQueryConfig(
        characterization_layers=tuple(pin.values() for pin in primary_layers),
        source_dependency_method="structure.scoped_relations",
        section_sources=(cue,) if outside else (cue, first_ref, second_ref),
        section_catalog_sources=(first_ref, second_ref) if outside else (),
        source_product_digest=cue.native_content_digest,
        source_projection_digest=cue.projection_digest,
        scope="chapter",
    )
    reader = SimpleNamespace(
        source_view=lambda _: source,
        characterization_layers=lambda _: primary_layers,
        contextual_mutual_neighbors=lambda report: dict(
            policy="mutual-exact-cosine-top5-2",
            inventory_id=report["inventories"][0]["inventory_id"],
            profile_id=report["profiles"][0]["profile_id"]
            if len(report["profiles"]) == 1
            else None,
            status=(
                "profile_unavailable"
                if len(report["profiles"]) != 1
                else "vector_coverage_unavailable"
            )
            if report["inventories"][0]["targets"]
            else "completed",
            directed_ranks=[],
            edges=[],
        ),
        source_result=lambda *_: scoped["body"],
        contextual_section_headings=heading_targets,
    )
    producer = ContextualCandidatesWithQueryContext()
    producer.version = version  # Historical literal-only v11 remains independently replayable.
    (result,) = producer.run(
        (SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW, 7, source.ref.key)),),
        config,
        SimpleNamespace(reader=reader, check_active=lambda: None),
    )
    configuration = config.model_dump(mode="json")
    retained = json.loads(
        canonical_bytes(
            dict(
                origin_task_id=102,
                origin_unit_id=7,
                method="retrieve.contextual",
                project_id="project",
                configuration=configuration,
                body=dict(
                    source=source.ref.key,
                    operation_version=version,
                    release_id=release,
                    configuration_hash=config_key("retrieve.contextual", version, configuration),
                    contribution_operations=result.contribution_operations,
                    contributions=result.contributions,
                ),
            )
        )
    )
    sources = {
        entry.ref.id: dict(
            source_view_id=entry.ref.id,
            ref=asdict(entry.ref),
            text=entry.text,
            context=entry.context(),
        )
        for entry in (source, first, second)
    }
    selection = ReviewSelection(selections=(ContributionRequest(run_id=1),))

    def write(name, payload, release_contract=contract):
        def rows():
            yield "selections", dict(selection_index=0, run_id=1, cut_id=2)
            yield (
                "inventory",
                dict(
                    selection_index=0,
                    population="report",
                    row=dict(origin_task_id=102, source_view_id=7),
                ),
            )
            yield "contracts", release_contract
            yield "reports", scoped
            yield "reports", payload
            for source_row in sources.values():
                yield "sources", source_row
            for document_id, document in documents.items():
                yield "documents", {"id": document_id, **document}

        return write_review_bundle(selection, tmp_path / name, rows())

    # This adapter test starts after the shared archive/pin/source authentication
    # boundary (tested independently); all working layers are real producer results.
    monkeypatch.setattr(
        "corpus_structure.serve.primary_characterization_replay.retained_primary_layers",
        lambda *_args: (primary_layers, {}),
    )
    monkeypatch.setattr("corpus_structure.semantic.constructions.navigation._SECTION_HEADING", None)
    monkeypatch.setattr(
        "corpus_structure.semantic.constructions.navigation._named_recipe",
        lambda *_args, **_kwargs: pytest.fail("detached replay reran primary recognition"),
    )
    if not outside:
        from corpus_structure.serve.contextual_witness_replay import _heading_inventory

        missing_original = {
            pin: layer
            for pin, layer in primary_layers.items()
            if second.ref.id not in layer.payload["source_scope"]["source_view_ids"]
        }
        available, _, complete = _heading_inventory(
            config,
            source.ref.id,
            sources,
            documents,
            json.loads(packet),
            primary_layers=missing_original,
        )
        assert not complete and len(available) == 1
        assert available[0].pointer == first.items[1]["self_ref"]
    with pytest.raises(ValueError, match="section inventories cannot combine"):
        ContextualQueryConfig.model_validate(
            {**configuration, "required_occurrence_ids": [original["occurrence_id"]]}
        )
    manifest = write("valid", retained)
    assert verify_review_bundle(tmp_path / "valid") == manifest
    (resolution,) = retained["body"]["contribution_operations"][0]["contextual_enrichment"][
        "section_resolutions"
    ]
    assert resolution["outcome"] == ("outside_inventory" if outside else "ambiguous")

    tampered = deepcopy(retained)
    report = tampered["body"]["contribution_operations"][0]["contextual_enrichment"]
    report["candidate_lists"][0]["channel_results"] = []
    with pytest.raises(ValueError, match="complete eligible witness channel"):
        write("missing-witness", tampered)
    if not outside:
        tampered_primary = deepcopy(retained)
        targets = tampered_primary["body"]["contribution_operations"][0]["contextual_enrichment"][
            "section_targets"
        ]
        targets[0]["primary_witnesses"] = targets[1]["primary_witnesses"]
        with pytest.raises(ValueError, match="complete selected native sources"):
            write("wrong-heading-primary", tampered_primary)
    tampered_contract = deepcopy(contract)
    tampered_contract["section_packets"]["input_base64"] = base64.b64encode(
        b'{"native_products":{},"packets":{},"version":1}'
    ).decode()
    with pytest.raises(ValueError, match="mapping differs from release input"):
        write("changed-map", retained, tampered_contract)
    if not outside:
        tampered = deepcopy(retained)
        report = tampered["body"]["contribution_operations"][0]["contextual_enrichment"]
        report["section_targets"].pop()
        with pytest.raises(ValueError, match="complete selected native sources"):
            write("missing-heading", tampered)
