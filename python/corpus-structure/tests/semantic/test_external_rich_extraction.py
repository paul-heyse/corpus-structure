"""Rich declared extraction preserves native placement and independent authored semantics."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from corpus_structure.methods.llm.cascade import PlacementPolicy
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_model import ExternalExecutorContract
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.declared_proposal_frames import (
    DeclaredProposalFrame,
    DeclaredProposalSource,
)
from corpus_structure.semantic.external_extraction import (
    external_extraction_inputs,
    external_extraction_operation_sources,
    external_extraction_prompt,
    locate_external_extraction,
    rich_external_declarations,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.proposals import ProposalRefused, ProposalSentence, native_address
from corpus_structure.semantic.rich_proposals import read_rich_proposals
from corpus_structure.semantic.types import SourceArtifact, SourceBundle
from semantic.proposals_support import batch


def controlled_external_sources(directory):
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    from corpus_structure.semantic.sentence_products import sentence_operation_sources

    configuration = SentenceConfig(exclude=("ner",))
    selection = NativeSelection(
        NativeProfile(
            "spacy",
            {"controlled": "runtime"},
            {"files": {}},
            configuration.model_dump(mode="json"),
            "float32",
            "cupy",
            4,
            1,
        ),
        directory,
    )
    return combine_primary_sources(
        sentence_operation_sources(configuration, selection=selection),
        external_extraction_operation_sources(),
    )


@pytest.fixture(scope="module")
def rich_bundle():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    domain = {
        "id": "https://example.org/domain",
        "name": "domain",
        "imports": ["core"],
        "prefixes": {"ex": "https://example.org/"},
        "default_prefix": "ex",
        "classes": {"Person": {"is_a": "Entity", "attributes": {"name": {"range": "string"}}}},
    }
    return external_extraction_inputs(
        SourceBundle(
            "domain",
            (
                SourceArtifact("core", core.read_bytes()),
                SourceArtifact("domain", yaml.safe_dump(domain).encode()),
            ),
        )
    )


@pytest.fixture(scope="module")
def rich_prepared(rich_bundle):
    return prepare_release(rich_bundle)


@pytest.fixture(scope="module")
def rich_model(rich_bundle, tmp_path_factory):
    from corpus_structure.semantic.declared_math_products import math_operation_declarations

    protocol = ExternalExecutorContract(
        "external-executor-v1",
        "Read declared packet inputs and emit rich proposals.",
        "explicit-external-agent",
        "asserted-model",
        "declared-inputs-only",
    )
    return compile_data_operations(
        rich_bundle,
        declarations=(math_operation_declarations(), rich_external_declarations(protocol)),
        python_sources=controlled_external_sources(tmp_path_factory.mktemp("rich-source")),
    )


def frame():
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
    from corpus_structure.semantic.original_documents import original_document_subject
    from corpus_structure.semantic.source_products import native_projection_identity

    text = "Alice is here. Alice is here."
    value = {
        "source": {
            "document": "document:one",
            "document_subject": original_document_subject("document:one"),
            "projection": "pending",
            "section_pointer": "#/groups/0",
            "membership": "descendants",
        },
        "text": text,
        "pieces": [
            {
                "kind": "native_text",
                "item_ref": "#/texts/0",
                "source_field": "text",
                "start": 0,
                "end": 14,
            },
            {"kind": "synthetic_separator", "start": 14, "end": 15},
            {
                "kind": "native_text",
                "item_ref": "#/texts/1",
                "source_field": "text",
                "start": 15,
                "end": 29,
            },
        ],
        "items": [
            {"self_ref": "#/texts/0", "label": "text"},
            {"self_ref": "#/texts/1", "label": "text"},
        ],
        "ancestors": [],
        "recognition": [],
        "selectors": [],
    }
    projection = native_projection_identity(
        text, value["pieces"], value["items"], value["recognition"], value["ancestors"]
    )
    value["source"]["projection"] = projection
    value["selectors"] = [{"projection": projection}]
    pin = {
        "format": "declared-native-source-v1",
        "source": '["product:source",null]',
        "source_product": "product:source",
        "kind_contract": "kind:source",
        "subject": "subject:one",
        "subject_definition": "original-source-view",
        "project_id": "project:one",
        "original_source": "document:one",
        "analyzed_scope_meaning": canonical_bytes(
            semantic_value(dict(source=value["source"], selectors=value["selectors"]))
        ).decode(),
        "document": "document:one",
        "projection_digest": projection,
        "section_pointer": "#/groups/0",
        "membership": "descendants",
    }
    base = DeclaredNativeFrameSource.from_retained_record(canonical_bytes(value).decode(), canonical_bytes(pin).decode())
    sentences = tuple(
        ProposalSentence(
            "native_evidence:" + str(index), native_address(base, start=start, end=end), start, end
        )
        for index, start, end in ((0, 0, 14), (2, 15, 29))
    )
    return DeclaredProposalFrame.compose(DeclaredProposalSource.from_frame(base, sentences))


def packet():
    actual = frame()
    return {
        "version": "external-extraction-input-1",
        "unit_ref": actual.unit_ref,
        "source_pin": actual.pin.values(),
        "frame": source_value(actual.record),
        "guideline": "Preserve every rich source report field.",
        "known_reference_standing": "authored",
        "known_classes": source_value({}),
        "known_entities": [],
        "bootstrap_terms": [],
        "macros": source_value({}),
        "native_observations": source_value([]),
        "scope_standing": "explicitly-none",
    }


def test_rich_family_declares_actual_authored_batch_and_complete_captured_placement(
    rich_bundle, tmp_path
):
    from corpus_structure.semantic.declared_math_products import math_operation_declarations

    protocol = ExternalExecutorContract(
        "external-executor-v1",
        "Read declared packet inputs and emit the rich authored batch.",
        "explicit-external-agent",
        "asserted-model",
        "declared-inputs-only",
    )
    model = compile_data_operations(
        rich_bundle,
        declarations=(math_operation_declarations(), rich_external_declarations(protocol)),
        python_sources=controlled_external_sources(tmp_path),
    )
    authored = model.operation("extract.rich_external")
    assert authored.external == protocol and authored.implementation_root is None
    assert (
        next(role.kind for role in authored.roles if role.direction == "output")
        == "https://corpus-structure.dev/semantic/agent/AgentAuthoredBatch"
    )
    assert model.operation("locate.external_extraction").capabilities.prepared_factory is not None
    for role in model.operation("prepare.external_extraction").roles:
        if role.name in {"annotations", "context_annotations"}:
            assert "segment.sentences/exact-source-scope" in role.required_rules
            assert "segment.sentences/native-row-span" in role.required_rules
    assert all(slice.complete for slice in model.implementation_slices)


def test_declared_rich_placement_picks_exact_repeated_native_piece_and_retains_full_batch(
    rich_prepared,
    rich_model,
):
    actual = frame()
    raw = batch()
    raw["unit_ref"] = actual.unit_ref
    raw["statements"][0]["anchor"] = actual.unit_ref
    raw["claims"][0]["evidence"][0]["sentence"] = "native_evidence:2"
    raw["claims"].append({**deepcopy(raw["claims"][0]), "id": "c2"})
    raw["alternatives"] = [
        {
            "id": "either",
            "members": ["c1", "c2"],
            "faithful": True,
            "reason": "retained alternatives",
        }
    ]
    raw["unsupported"] = [
        {
            "id": "u",
            "kind": "unsupported_relation",
            "text": "Alice is here.",
            "reason": "no admitted relation",
            "evidence": deepcopy(raw["claims"][0]["evidence"]),
        }
    ]
    result = locate_external_extraction(
        rich_prepared,
        packet(),
        raw,
        model=rich_model,
        placement_policy=PlacementPolicy(),
        check_active=lambda: None,
    )
    rich = read_rich_proposals(rich_prepared, result)
    claims = [member for member in rich["members"] if member["body"]["proposal_type"] == "claim"]
    evidence = claims[0]["body"]["evidence"][0]
    assert (evidence["start"], evidence["end"], evidence["outcome"]) == (15, 29, "located")
    assert evidence["locator"] == native_address(actual, start=15, end=29)
    assert "source_view_id" not in evidence["locator"] and "task_id" not in evidence["locator"]
    assert [member["member_id"] for member in claims] == ["claim:c1", "claim:c2"]
    alternatives = [
        member["body"]
        for member in rich["members"]
        if member["body"]["proposal_type"] == "alternative"
    ]
    assert list(alternatives[0]["claims"]) == [{"member_id": "claim:c1"}, {"member_id": "claim:c2"}]
    unsupported = [
        member["body"]
        for member in rich["members"]
        if member["body"]["proposal_type"] == "unsupported"
    ]
    assert unsupported[0]["reason"] == "no admitted relation"
    assert (
        result["standing"] == "private_proposed"
        and result["known_reference_standing"] == "authored"
    )
    assert "stored" not in rich and "authored" not in rich
    assert len(result["coverage"]) == 6
    assert all(row["scope"] == "supplied-authored-response" for row in result["coverage"])


def test_declared_rich_prompt_uses_real_member_coordinates_and_refuses_wrong_unit(
    rich_prepared, rich_model
):
    presented = external_extraction_prompt(packet())
    assert presented["native_evidence"][1]["text"] == "Alice is here."
    assert presented["native_evidence"][1]["handle"] == "native_evidence:2"
    assert presented["known_classes"] == {} and presented["known_reference_standing"] == "authored"
    assert presented["scope_standing"] == "explicitly-none"
    raw = batch()
    with pytest.raises(ProposalRefused, match="unit"):
        locate_external_extraction(
            rich_prepared,
            packet(),
            raw,
            model=rich_model,
            placement_policy=PlacementPolicy(),
            check_active=lambda: None,
        )


@pytest.mark.parametrize("invalid", ["accepted", "duplicate-member", "false-coverage"])
def test_private_rich_member_collection_refuses_promoted_or_inconsistent_values(
    rich_prepared, rich_model, invalid
):
    actual = frame()
    raw = batch()
    raw["unit_ref"] = actual.unit_ref
    raw["statements"][0]["anchor"] = actual.unit_ref
    raw["claims"][0]["evidence"][0]["sentence"] = "native_evidence:2"
    result = locate_external_extraction(
        rich_prepared,
        packet(),
        raw,
        model=rich_model,
        placement_policy=PlacementPolicy(),
        check_active=lambda: None,
    )
    changed = deepcopy(result)
    if invalid == "accepted":
        changed["members"][0]["body"]["standing"] = "accepted"
    elif invalid == "duplicate-member":
        changed["members"] = (*changed["members"], deepcopy(changed["members"][0]))
    else:
        changed["coverage"][0]["count"] += 1
    with pytest.raises(ValueError):
        read_rich_proposals(rich_prepared, changed)


def test_declared_frame_refuses_counterfeit_projection_even_when_pin_agrees():
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource

    actual = frame()
    assert actual.view.projection == actual.projection_digest
    value, pin = json.loads(actual.source_content), json.loads(actual.pin_content)
    counterfeit = "f" * 64
    value["source"]["projection"] = pin["projection_digest"] = counterfeit
    value["selectors"] = [{"projection": counterfeit}]
    pin["analyzed_scope_meaning"] = canonical_bytes(
        semantic_value(dict(source=value["source"], selectors=value["selectors"]))
    ).decode()
    with pytest.raises(ValueError, match="declared native projection differs"):
        _ = DeclaredNativeFrameSource.from_retained_record(
            canonical_bytes(value).decode(), canonical_bytes(pin).decode()
        ).view
