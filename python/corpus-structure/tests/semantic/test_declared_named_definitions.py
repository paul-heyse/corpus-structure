"""Retained semantic references and original named-role contracts, without inference."""

from types import SimpleNamespace

import pytest

from corpus_structure.methods.definition_applicability import DefinitionScope, components_from_named_matches
from corpus_structure.semantic.construction_products import CharacterizationSnapshot
from corpus_structure.semantic.constructions.declared_named import DeclaredNamedRules
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import StructuralPassage, declared_definition_component


def population():
    text = "We define variance as spread."
    spans = ((0, 2), (3, 9), (10, 18), (19, 21), (22, 28), (28, 29))
    native = CharacterizationSnapshot("native-product", canonical_bytes({"source": {"document": "book"}, "selectors": [], "members": [{"member_id": f"token-{index}", "body": {"record_type": "native_token", "block_id": "native-block", "ordinal": index, "start": start, "end": end}} for index, (start, end) in enumerate(spans)]}))
    def ref(index):
        return {"product_id": native.semantic_id, "member_id": f"token-{index}"}
    common = {"rule": "defining", "variant": "active_as", "mechanism": "dependency", "protocol": "named-annotation-match-2", "dependency_digest": "a" * 64, "native_container": {"product_id": native.semantic_id, "block_id": "native-block"}, "nodes": [], "piece_indices": [], "sentences": [], "bindings": [], "negation_occurrences": []}
    body = {"source": {"document": "book"}, "selectors": [], "coverage": [], "members": [{"body": {"record_type": "annotation", "local_id": "availability", "kind": "construction.named_availability", "rule_id": "named-rule:actual", "named_match": {**common, "status": "available"}}}, {"body": {"record_type": "annotation", "local_id": "match", "kind": "construction.named_binding", "rule_id": "named-rule:actual", "named_match": {**common, "status": "matched", "nodes": [ref(1), ref(2), ref(4)], "sentences": [{"token_index": index, "sentence": 0} for index in (1, 2, 4)], "bindings": [{"role": role, "node": role, "head": ref(index), "members": [ref(index)], "expansion": "exact", "status": "complete"} for role, index in (("defining_cue", 1), ("defined_term", 2), ("defining_content", 4))]}}}]}
    primary = CharacterizationSnapshot("construction-product", canonical_bytes(body))
    product = SimpleNamespace(block_id="native-block", dependency_digest="a" * 64, tokens=tuple(SimpleNamespace(start=start, end=end, sentence=0) for start, end in spans), sentences=(SimpleNamespace(start=0),))
    return text, native, primary, product


def test_declared_named_reader_keeps_actual_member_origin_and_original_role_algorithm():
    text, native, primary, product = population()
    result, refs, nominations, _ = DeclaredNamedRules((primary,), native).decode(product)
    (match,) = result.matches
    assert refs[match].product_id == "construction-product"
    assert refs[match].member_id == "match"
    assert match.nodes == (1, 2, 4)
    assert [(role.role, role.extents) for role in match.roles] == [("defining_cue", ((3, 9),)), ("defined_term", ((10, 18),)), ("defining_content", ((22, 28),))]
    assert nominations == {}
    passage = StructuralPassage(passage_id="native-block", source_ref="a" * 64, start=0, end=len(text), text=text, scope="native-block")
    components = components_from_named_matches(passage, result.matches, scopes={match: DefinitionScope(1, "positive", "supported")}, term_role="defined_term", content_role="defining_content", witnesses={}, component_factory=declared_definition_component)
    assert components[0].term.text == "variance" and components[0].content.text == "spread"
    assert components[0].basis == "unqualified" and components[0].interpretation == "unresolved"


@pytest.mark.parametrize("mutation", ["native-product", "native-block", "token-position", "availability"])
def test_declared_named_reader_refuses_wrong_native_members_and_unperformed_variant(mutation):
    import json

    _, native, primary, product = population()
    body = json.loads(primary.content)
    match = body["members"][1]["body"]["named_match"]
    if mutation == "native-product":
        match["native_container"]["product_id"] = "foreign-native"
    elif mutation == "native-block":
        match["native_container"]["block_id"] = "foreign-block"
    elif mutation == "token-position":
        match["nodes"][0]["member_id"] = "token-0"
        product.tokens = (SimpleNamespace(start=100, end=102, sentence=0), *product.tokens[1:])
    else:
        body["members"] = body["members"][1:]
    with pytest.raises(ValueError):
        DeclaredNamedRules((CharacterizationSnapshot(primary.semantic_id, canonical_bytes(body)),), native).decode(product)
