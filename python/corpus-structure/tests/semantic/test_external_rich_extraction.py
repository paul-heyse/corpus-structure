"""Rich declared extraction preserves native placement and independent authored semantics."""

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from corpus_structure.methods.llm.cascade import PlacementPolicy
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_model import ExternalExecutorContract
from corpus_structure.semantic.declared_proposal_frames import DeclaredProposalFrame
from corpus_structure.semantic.external_extraction import (
    external_extraction_inputs,
    external_extraction_operation_sources,
    external_extraction_prompt,
    locate_external_extraction,
    located_external_batch,
    rich_external_declarations,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.proposals import ProposalRefused, ProposalSentence, native_address
from semantic.proposals_support import batch


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


def frame():
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource

    text = "Alice is here. Alice is here."
    value = {
        "source": {
            "document": "document:one",
            "projection": "a" * 64,
            "section_pointer": "#/groups/0",
            "membership": "descendants",
        },
        "text": text,
        "pieces": [
            {"kind": "native_text", "item_ref": "#/texts/0", "start": 0, "end": 14},
            {"kind": "native_text", "item_ref": "#/texts/1", "start": 15, "end": 29},
        ],
        "items": [{"self_ref": "#/texts/0"}, {"self_ref": "#/texts/1"}],
        "ancestors": [],
        "recognition": [],
        "selectors": [{"projection": "a" * 64}],
    }
    pin = {
        "format": "declared-native-source-v1",
        "source": '["product:source",null]',
        "source_product": "product:source",
        "kind_contract": "kind:source",
        "subject": "subject:one",
        "project_id": "project:one",
        "original_source": "document:one",
        "analyzed_scope_meaning": '["null"]',
        "document": "document:one",
        "projection_digest": "a" * 64,
        "section_pointer": "#/groups/0",
        "membership": "descendants",
    }
    base = DeclaredNativeFrameSource(canonical_bytes(value).decode(), canonical_bytes(pin).decode())
    sentences = tuple(
        ProposalSentence(
            "native_evidence:" + str(index), native_address(base, start=start, end=end), start, end
        )
        for index, (start, end) in enumerate(((0, 14), (15, 29)))
    )
    return DeclaredProposalFrame(base.source_content, base.pin_content, sentence_values=sentences)


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


def test_rich_family_declares_actual_authored_batch_and_complete_captured_placement(rich_bundle):
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
        python_sources=external_extraction_operation_sources(),
    )
    authored = model.operation("extract.rich_external")
    assert authored.external == protocol and authored.implementation_root is None
    assert (
        next(role.kind for role in authored.roles if role.direction == "output")
        == "https://corpus-structure.dev/semantic/agent/AgentAuthoredBatch"
    )
    assert model.operation("locate.external_extraction").capabilities.prepared_factory is not None
    assert all(slice.complete for slice in model.implementation_slices)


def test_declared_rich_placement_picks_exact_repeated_native_piece_and_retains_full_batch(
    rich_prepared,
):
    actual = frame()
    raw = batch()
    raw["unit_ref"] = actual.unit_ref
    raw["statements"][0]["anchor"] = actual.unit_ref
    raw["claims"][0]["evidence"][0]["sentence"] = "native_evidence:1"
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
        rich_prepared, packet(), raw, placement_policy=PlacementPolicy(), check_active=lambda: None
    )
    stored, issues = located_external_batch(rich_prepared, result)
    wire = stored.model_dump(mode="python")
    evidence = wire["claims"][0]["evidence"][0]
    assert (evidence["start"], evidence["end"], evidence["outcome"]) == (15, 29, "located")
    assert evidence["locator"] == native_address(actual, start=15, end=29)
    assert "source_view_id" not in evidence["locator"] and "task_id" not in evidence["locator"]
    assert len(wire["claims"]) == 2 and wire["alternatives"][0]["members"] == ("c1", "c2")
    assert wire["unsupported"][0]["reason"] == "no admitted relation" and issues == ()
    assert (
        result["standing"] == "unselected_source_report"
        and result["known_reference_standing"] == "authored"
    )


def test_declared_rich_prompt_uses_real_member_coordinates_and_refuses_wrong_unit(rich_prepared):
    presented = external_extraction_prompt(packet())
    assert presented["native_evidence"][1]["text"] == "Alice is here."
    assert presented["native_evidence"][1]["handle"] == "native_evidence:1"
    assert presented["known_classes"] == {} and presented["known_reference_standing"] == "authored"
    assert presented["scope_standing"] == "explicitly-none"
    raw = batch()
    with pytest.raises(ProposalRefused, match="unit"):
        locate_external_extraction(
            rich_prepared,
            packet(),
            raw,
            placement_policy=PlacementPolicy(),
            check_active=lambda: None,
        )
