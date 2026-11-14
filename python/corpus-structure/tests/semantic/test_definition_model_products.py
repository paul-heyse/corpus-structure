"""Independent located-role and directed-edge controls for declared definitions."""

from copy import deepcopy
from hashlib import sha256
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.contributions import operation_identity
from corpus_structure.semantic.definition_model_products import (
    QUESTION, decode_definition_window, definition_contribution, retained_definition_windows,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.structural_products import StructuralPassage


def population():
    text = "We call the expected squared deviation variance."
    window = StructuralPassage(passage_id="native-block", source_ref="a" * 64, start=0, end=len(text), text=text, scope="native-block")
    term = {"start": 39, "end": 47, "text": "variance", "interpretation": "definition"}
    content = {"start": 12, "end": 38, "text": "expected squared deviation"}
    # Actual offsets are independent expectations, never derived from production output.
    assert text[term["start"]:term["end"]] == term["text"]
    assert text[content["start"]:content["end"]] == content["text"]
    raw = {"entities": {"defined term or expression": [term], "defining text or formula": [content]}, "relation_extraction": {"term is defined or explained by": [{"head": {k: v for k, v in term.items() if k != "interpretation"}, "tail": content}]}}
    return text, window, raw


def test_declared_definition_keeps_independent_roles_and_exact_directed_attachment():
    _, window, raw = population()
    decoded = decode_definition_window(raw, window, None, envelope="reply")
    assert [(row["role"], row["span"]["text"]) for row in decoded["role_candidates"]] == [("term", "variance"), ("content", "expected squared deviation")]
    assert len(decoded["components"]) == 1
    assert decoded["components"][0]["basis"] == "model_reading"
    assert decoded["components"][0]["interpretation"] == "definition"
    raw["relation_extraction"]["term is defined or explained by"][0]["head"], raw["relation_extraction"]["term is defined or explained by"][0]["tail"] = raw["relation_extraction"]["term is defined or explained by"][0]["tail"], raw["relation_extraction"]["term is defined or explained by"][0]["head"]
    reversed_ = decode_definition_window(raw, window, None, envelope="reply")
    assert len(reversed_["role_candidates"]) == 2
    assert reversed_["components"] == []
    assert reversed_["errors"][0]["channel"] == "attachment"


def pair():
    text, window, raw = population()
    pin = {"source_product": "native-product"}
    frame = SimpleNamespace(text=text, pin=SimpleNamespace(values=lambda: pin), contains_span=lambda start,end: 0 <= start < end <= len(text))
    from dataclasses import asdict
    from corpus_structure.semantic.definition_model_products import DefinitionExtractionOptions

    request = {"question": QUESTION, "options": asdict(DefinitionExtractionOptions()), "window": window.model_dump(mode="json", exclude_none=True), "source_pin": pin}
    digest = sha256(canonical_bytes(request)).hexdigest()
    operation = operation_identity(QUESTION, "1", "native-source", digest)
    report = {"question": QUESTION, "request": request, "input_digest": digest, "native": {"raw": raw}}
    decoded = decode_definition_window(raw, window, None, envelope=digest)
    row = definition_contribution(frame, operation, {"window": request["window"], **decoded}, digest)
    candidates = {"source_pin": pin, "members": [{"member_id": "contribution:" + row["contribution_id"], "body": {**row, "candidate_type": "contribution"}}], "operations": [{"operation_key": operation, "question": QUESTION, "report_digest": sha256(canonical_bytes(report)).hexdigest(), "computation_dependencies": [digest]}]}
    observation = {"source_pin": pin, "observations": [source_value(report)]}
    return frame, observation, candidates


def test_retained_definition_pairs_actual_observation_and_candidate_without_inference():
    frame, observation, candidates = pair()
    retained = retained_definition_windows(frame, observation, candidates)
    assert len(retained) == 1
    assert retained[0][2]["components"][0]["term"]["text"] == "variance"


@pytest.mark.parametrize("mutation", ["source", "reply", "member", "missing"])
def test_retained_definition_refuses_wrong_source_reply_member_or_missing_population(mutation):
    frame, observation, candidates = pair()
    candidates = deepcopy(candidates)
    if mutation == "source":
        candidates["source_pin"] = {"source_product": "another"}
    elif mutation == "reply":
        candidates["operations"][0]["report_digest"] = "f" * 64
    elif mutation == "member":
        candidates["members"][0]["member_id"] = "another"
    else:
        candidates["members"] = []
    with pytest.raises(ValueError):
        retained_definition_windows(frame, observation, candidates)



def test_definition_question_and_evaluation_choices_keep_distinct_native_receipts():
    from dataclasses import asdict
    from corpus_structure.methods.definition_applicability import definition_pack
    from corpus_structure.methods.gliner import GlinerInput
    from corpus_structure.methods.model_observation import installed_policy, request_digest
    from corpus_structure.semantic.definition_model_products import DefinitionExtractionOptions, DefinitionQuestion
    from semantic.model_characterization_support import gliner_profile

    profile = gliner_profile().profile
    policy, _ = installed_policy()
    item = GlinerInput("unit", "original-window", "Variance is spread.", "text.gliner_definitions/source-native")
    bare = definition_pack("release", DefinitionQuestion(profile))
    described = definition_pack("release", DefinitionQuestion(profile, description_arm="described"))
    assert bare.fingerprint != described.fingerprint
    assert "defined term or expression" in bare.declaration_json and "defined term or expression" in described.declaration_json
    options = (DefinitionExtractionOptions(), DefinitionExtractionOptions(evaluation_overlap="flat"), DefinitionExtractionOptions(evaluation_overlap="nested"), DefinitionExtractionOptions(evaluation_overlap="allow"))
    receipts = {request_digest(bare, asdict(profile), (item,), 0.5, option.overlap, option.evaluation, policy["inference"]) for option in options}
    assert len(receipts) == 4
    with pytest.raises(ValueError):
        DefinitionExtractionOptions(description_arm="invented")
    with pytest.raises(ValueError):
        DefinitionExtractionOptions(term_entity="same", content_entity="same")
