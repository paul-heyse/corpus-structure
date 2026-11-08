"""Detached section citation replay over a controlled complete native packet."""

import base64
import json
from copy import deepcopy
from dataclasses import asdict, replace
from hashlib import sha256
from types import SimpleNamespace

import pytest
from methods.test_m1_producer import view

from corpus_structure.core.evidence import config_key
from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.methods.contextual_candidates import (
    ContextualCandidateConfig,
    ContextualCandidates,
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

from .test_review_bundle import synthetic_source_projection as synthetic_source_projection


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
def test_detached_section_replay_requires_complete_witnesses(
    monkeypatch, tmp_path, outside, synthetic_source_projection
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
                named_cue=dict(
                    kind="section_citation",
                    designator="6.2",
                    scope="chapter",
                    resolution="target_selection_required",
                ),
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
            operation_version="7",
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
    config = ContextualCandidateConfig(
        source_dependency_method="structure.scoped_relations",
        section_sources=(cue,) if outside else (cue, first_ref, second_ref),
        section_catalog_sources=(first_ref, second_ref) if outside else (),
        source_product_digest=cue.native_content_digest,
        source_projection_digest=cue.projection_digest,
        scope="chapter",
    )
    reader = SimpleNamespace(
        source_view=lambda _: source,
        source_result=lambda *_: scoped["body"],
        contextual_section_headings=heading_targets,
    )
    (result,) = ContextualCandidates().run(
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
                    operation_version="7",
                    release_id=release,
                    configuration_hash=config_key("retrieve.contextual", "7", configuration),
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
