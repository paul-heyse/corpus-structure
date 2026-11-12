"""Detached named links bind annotation owners separately from native anchors."""

from base64 import b64encode
from copy import deepcopy
from dataclasses import asdict, replace
from hashlib import sha256
from importlib.resources import files

import pytest

from corpus_structure.core.evidence import config_key
from corpus_structure.methods.scoped_relations import SCOPED_VERSION, ScopedRelationsConfig
from corpus_structure.methods.source_preparation import prepare_source
from corpus_structure.methods.witnessed_source_links import NAMED_NATIVE_PIECES_INPUT
from corpus_structure.orchestrate.registry import canonical_numbers
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python, source_value
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.source_contexts import NativeSourcePin
from corpus_structure.semantic.structural_products import (
    ExternalSourceRef,
    StructuralInput,
    StructuralPassage,
)
from corpus_structure.serve.witnessed_source_link_replay import (
    NAMED_LINK_NATIVE_PIECES_FIELD,
    archived_named_link_native_pieces,
    verify_annotated_named_links,
)

from .test_m1_source_preparation import source
from .test_scoped_relations import discover_relations


def _contract(policy: bytes):
    manifest = canonical_bytes(
        {"dependencies": [[NAMED_NATIVE_PIECES_INPUT, sha256(policy).hexdigest()]]}
    )
    return {
        "release_id": "release:" + sha256(manifest).hexdigest(),
        NAMED_LINK_NATIVE_PIECES_FIELD: {
            "manifest_base64": b64encode(manifest).decode(),
            "input_base64": b64encode(policy).decode(),
        },
    }


def test_joined_citation_policy_requires_exact_archived_release_bytes():
    archived = b'{"kept":"unchanged"}'
    contract = _contract(archived)
    assert archived_named_link_native_pieces(contract) == archived
    artifact = contract[NAMED_LINK_NATIVE_PIECES_FIELD]
    assert isinstance(artifact, dict)
    artifact["input_base64"] = b64encode(archived + b"\n").decode()
    with pytest.raises(ValueError, match="not bound to its release"):
        archived_named_link_native_pieces(contract)
    with pytest.raises(ValueError, match="lack their archived"):
        archived_named_link_native_pieces({"release_id": contract["release_id"]})


def _joined_view():
    first, second = "For more detail, ", "see Section 6.1."
    text = first + second
    owner, cited, inline = "#/texts/0", "#/texts/1", "#/groups/2"
    pieces = (
        dict(kind="native_text", item_ref=owner, source_field="text", start=0, end=len(first)),
        dict(
            kind="native_text", item_ref=cited, source_field="text", start=len(first), end=len(text)
        ),
    )
    nodes = (
        dict(self_ref=owner, label="text", text=first, content_layer="body", parent={}),
        dict(self_ref=inline, label="inline", parent={"$ref": owner}),
        dict(
            self_ref=cited, label="text", text=second, content_layer="body", parent={"$ref": inline}
        ),
    )
    view = source("fixture", labels=("text",))
    digest = sha256(
        canonical_bytes(
            dict(
                text=text,
                pieces=pieces,
                items=[item["self_ref"] for item in nodes],
                ancestors=[],
                health={},
            )
        )
    ).hexdigest()
    return replace(
        view, ref=replace(view.ref, projection_digest=digest), text=text, pieces=pieces, items=nodes
    )


def _retained_reports(view, release, *, batch_size=64):
    method_version, named_version = SCOPED_VERSION, "4"
    frame = native_source_frame(view, ())
    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.ingest.sentences import SentenceConfig, pipeline

    profile = AnnotationProfile(SentenceConfig(batch_size=batch_size, exclude=("ner",)))
    native_profile = pipeline(profile.configuration).selection().native
    annotations = prepare_source(view, profile=profile, annotations_only=True)
    assert not annotations.annotation_errors
    (block,) = annotations.annotations
    assert block.block_id == "#/texts/0"
    assert block.native_pieces[1].item_ref == "#/texts/1"
    ref = ExternalSourceRef(
        project_id="fixture",
        run_id=1,
        cut_id=1,
        release_id=release,
        result_revision=0,
        source_view_id=view.ref.id,
        native_task_id=view.ref.native_product.task_id,
        native_product_key=view.ref.native_product.product_key,
        native_content_digest=view.ref.native_product.content_digest,
        projection_digest=view.ref.projection_digest,
        recipe_digest=view.ref.recipe_digest,
        coordinate_version=3,
    )
    passage = StructuralPassage(
        passage_id="cross-reference",
        source_ref=ref.identity,
        start=0,
        end=len(view.text),
        scope="fixture",
        text=view.text,
    )
    inputs = StructuralInput(
        question="section citations",
        scope=passage.scope,
        inventory_id="inventory",
        policy_id="fixture",
        sources=(ref,),
        passages=(passage,),
        dependencies=("fixture",),
    )
    output = discover_relations(
        frame,
        annotations=annotations.annotations,
        annotation_native_profile=native_profile,
        annotation_origin_task_id=41,
        passages=(passage,),
        predicate_version="5",
        witnessed_links_enabled=True,
        named_link_version=named_version,
    )
    primary = output["_primary_layers"]
    config = ScopedRelationsConfig(
        inputs=inputs,
        structural_input_digest=inputs.identity,
        characterization_layers=tuple(pin.values() for pin in primary),
    )
    params = canonical_numbers(config.model_dump(mode="json"))
    scoped = dict(
        configuration=params,
        body=dict(
            operation_version=method_version,
            configuration_hash=config_key("structure.scoped_relations", method_version, params),
            contribution_operations=(output["operation"], *output["extra_operations"]),
            contributions=output["contributions"],
        ),
    )
    producer = dict(
        method="extract.m1_annotations",
        origin_unit_id=view.ref.id,
        project_id=ref.project_id,
        input_hash="annotation-input",
        config_hash="annotation-configuration",
        body=dict(
            release_id=release,
            source=frame.unit_ref,
            operation_version="3",
            input_hash="annotation-input",
            configuration_hash="annotation-configuration",
            outcome="produced",
            parse_detail=source_value(
                dict(
                    recipe="m1-owned-linguistic-product-1",
                    source_pin=asdict(NativeSourcePin.from_source(frame)),
                )
            ),
        ),
    )
    source_row = dict(
        source_view_id=view.ref.id,
        text=view.text,
        ref=asdict(view.ref),
        context=dict(items=view.items, pieces=view.pieces, ancestors=view.ancestors, health={}),
    )
    # Use wire values so detached list/tuple comparisons match a delivered bundle.
    import json

    return (*json.loads(canonical_bytes([scoped, source_row, producer])), primary)


def test_historical_named_cue_replay_requires_current_primary_regeneration():
    scoped, source_row, producer, primary = _retained_reports(_joined_view(), "release:legacy")
    scoped["body"]["operation_version"] = "12"
    with pytest.raises(ValueError, match="current exact retained configuration"):
        verify_annotated_named_links(scoped, source_row, {41: producer}, primary_layers=primary)


def test_joined_citation_replays_exact_annotation_and_native_piece():
    _assert_joined_citation_replay(batch_size=64)


def test_joined_citation_replays_nondefault_native_batch_configuration():
    _assert_joined_citation_replay(batch_size=2)


def _assert_joined_citation_replay(*, batch_size):
    policy = (
        files("corpus_structure")
        .joinpath("semantic/constructions/navigation_native_pieces.json")
        .read_bytes()
    )
    contract = _contract(policy)
    scoped, source_row, producer, primary = _retained_reports(
        _joined_view(), contract["release_id"], batch_size=batch_size
    )
    archived = archived_named_link_native_pieces(contract)
    (cue,) = [
        row
        for row in scoped["body"]["contributions"]
        if row["kind"] == "occurrence"
        and source_python(row["value"]).get("role") == "named_link_cue"
    ]
    assert cue["anchors"][0]["pointer"] == "#/texts/1"
    witness = source_python(cue["value"])["named_cue"]
    assert witness["block"] == "#/texts/0"
    verify_annotated_named_links(
        scoped, source_row, {41: producer}, native_piece_policy=archived, primary_layers=primary
    )

    tampered = deepcopy(producer)
    detail = source_python(tampered["body"]["parse_detail"])
    detail["source_pin"]["projection_digest"] = "f" * 64
    tampered["body"]["parse_detail"] = source_value(detail)
    with pytest.raises(ValueError, match="summary differs from retained native source"):
        verify_annotated_named_links(
            scoped, source_row, {41: tampered}, native_piece_policy=archived, primary_layers=primary
        )
