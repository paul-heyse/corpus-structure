"""Retained semantic references and original named-role contracts, without inference."""

from types import SimpleNamespace

import pytest

from corpus_structure.methods.definition_applicability import (
    DefinitionScope,
    components_from_named_matches,
)
from corpus_structure.semantic.construction_products import CharacterizationSnapshot
from corpus_structure.semantic.constructions.declared_named import DeclaredNamedRules
from corpus_structure.semantic.data_operation_partitions import partition_header, partition_packet
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import (
    StructuralPassage,
)


def population():
    text = "We define variance as spread."
    spans = ((0, 2), (3, 9), (10, 18), (19, 21), (22, 28), (28, 29))
    packet = partition_packet(
        "rows",
        "native-block",
        0,
        0,
        len(text),
        [
            {"record_type": "token", "ordinal": index, "start": start, "end": end}
            for index, (start, end) in enumerate(spans)
        ],
    )
    native = CharacterizationSnapshot(
        "native-product",
        canonical_bytes(
            {
                "source": {"document": "book"},
                "selectors": [],
                "rows": partition_header((packet,)),
                "block_layouts": [
                    {
                        "annotation": {
                            "block_id": "native-block",
                            "block_start": 0,
                            "block_end": len(text),
                        },
                        "piece_offset": 0,
                    }
                ],
            }
        ),
        (canonical_bytes(packet),),
    )

    def ref(index):
        return {
            "variant": "partition-item",
            "role": "sentences",
            "collection": "rows",
            "partition_key": "native-block",
            "item_key": [{"kind": "text", "text": "token"}, {"kind": "integer", "integer": index}],
        }

    common = {
        "rule": "defining",
        "variant": "active_as",
        "mechanism": "dependency",
        "protocol": "named-annotation-match-2",
        "dependency_digest": "a" * 64,
        "block_id": "native-block",
        "piece_indices": [],
        "sentences": [],
        "bindings": [],
        "negation_occurrences": [],
    }
    body = {
        "source": {"document": "book"},
        "selectors": [],
        "coverage": [],
        "annotation_support": [
            {"owner": "match", "use": "named_node", "position": position, "target": ref(index)}
            for position, index in enumerate((1, 2, 4))
        ]
        + [
            {
                "owner": "match",
                "use": use,
                "position": 0,
                "binding_position": position,
                "target": ref(index),
            }
            for position, index in enumerate((1, 2, 4))
            for use in ("named_binding_head", "named_binding_member")
        ],
        "members": [
            {
                "body": {
                    "record_type": "annotation",
                    "local_id": "availability",
                    "kind": "construction.named_availability",
                    "rule_id": "named-rule:actual",
                    "named_match": {**common, "status": "available"},
                }
            },
            {
                "body": {
                    "record_type": "annotation",
                    "local_id": "match",
                    "kind": "construction.named_binding",
                    "rule_id": "named-rule:actual",
                    "named_match": {
                        **common,
                        "status": "matched",
                        "sentences": [{"token_index": index, "sentence": 0} for index in (1, 2, 4)],
                        "bindings": [
                            {
                                "role": role,
                                "node": role,
                                "expansion": "exact",
                                "status": "complete",
                            }
                            for role in (
                                "defining_cue",
                                "defined_term",
                                "defining_content",
                            )
                        ],
                    },
                }
            },
        ],
    }
    primary = CharacterizationSnapshot("construction-product", canonical_bytes(body))
    product = SimpleNamespace(
        block_id="native-block",
        dependency_digest="a" * 64,
        tokens=tuple(SimpleNamespace(start=start, end=end, sentence=0) for start, end in spans),
        sentences=(SimpleNamespace(start=0),),
    )
    return text, native, primary, product


def test_declared_named_reader_keeps_actual_member_origin_and_original_role_algorithm():
    text, native, primary, product = population()
    result, refs, nominations, _ = DeclaredNamedRules((primary,), native).decode(product)
    (match,) = result.matches
    assert refs[match].product.product_id == "construction-product"
    assert refs[match].member_id == "match"
    assert match.nodes == (1, 2, 4)
    assert [(role.role, role.extents) for role in match.roles] == [
        ("defining_cue", ((3, 9),)),
        ("defined_term", ((10, 18),)),
        ("defining_content", ((22, 28),)),
    ]
    assert nominations == {}
    passage = StructuralPassage(
        passage_id="native-block",
        source_ref="a" * 64,
        start=0,
        end=len(text),
        text=text,
        scope="native-block",
    )
    components = components_from_named_matches(
        passage,
        result.matches,
        scopes={match: DefinitionScope(1, "positive", "supported")},
        term_role="defined_term",
        content_role="defining_content",
        witnesses={},
    )
    assert components[0].term.text == "variance" and components[0].content.text == "spread"
    assert components[0].basis == "unqualified" and components[0].interpretation == "unresolved"


@pytest.mark.parametrize(
    "mutation",
    ["reference-role", "native-block", "token-position", "availability", "source", "scope"],
)
def test_declared_named_reader_refuses_wrong_native_members_and_unperformed_variant(mutation):
    import json

    _, native, primary, product = population()
    body = json.loads(primary.content)
    match = body["members"][1]["body"]["named_match"]
    if mutation == "reference-role":
        body["annotation_support"][0]["target"]["role"] = "foreign"
    elif mutation == "native-block":
        match["block_id"] = "foreign-block"
    elif mutation == "token-position":
        body["annotation_support"][0]["target"]["item_key"][1]["integer"] = 0
        product.tokens = (SimpleNamespace(start=100, end=102, sentence=0), *product.tokens[1:])
    elif mutation == "availability":
        body["members"] = body["members"][1:]
    elif mutation == "source":
        body["source"] = {"document": "another-book"}
    else:
        body["selectors"] = [{"scope": "another-block"}]
    with pytest.raises(ValueError):
        DeclaredNamedRules(
            (CharacterizationSnapshot(primary.semantic_id, canonical_bytes(body)),), native
        ).decode(product)


@pytest.mark.parametrize("state", ["available", "unavailable", None])
def test_examined_empty_named_variant_remains_distinct_from_unavailable_or_unperformed(state):
    import json

    _, native, primary, product = population()
    body = json.loads(primary.content)
    body["members"] = body["members"][:1] if state is not None else []
    body["annotation_support"] = []
    if state is not None:
        body["members"][0]["body"]["named_match"]["status"] = state
    result, references, nominations, _ = DeclaredNamedRules(
        (CharacterizationSnapshot(primary.semantic_id, canonical_bytes(body)),), native
    ).decode(product)
    assert result.matches == () and references == {} and nominations == {}
    assert result.availability == (() if state is None else (("defining", "active_as", state),))


def test_named_definition_acquisition_compiles_without_model_provider_dependencies(tmp_path):
    from pathlib import Path

    from corpus_structure.semantic.characterization_ports import construction_operation_sources
    from corpus_structure.semantic.data_operation_compilation import compile_data_operations
    from corpus_structure.semantic.declared_structural_calls import (
        structural_operation_declarations,
    )
    from corpus_structure.semantic.definition_component_products import (
        definition_component_inputs,
        definition_component_operation_sources,
    )
    from corpus_structure.semantic.formal_products import formal_operation_sources
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    from corpus_structure.semantic.types import SourceArtifact, SourceBundle

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = definition_component_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    assert "data_operation_learned" not in {source.name for source in bundle.sources}
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection
    from corpus_structure.semantic.sentence_products import sentence_operation_sources

    configuration = SentenceConfig()
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
        tmp_path,
    )
    sources = combine_primary_sources(
        formal_operation_sources(),
        construction_operation_sources(include_dependencies=False),
        sentence_operation_sources(configuration, selection=selection),
        definition_component_operation_sources(),
    )
    model = compile_data_operations(bundle, (structural_operation_declarations(),), sources)
    names = {operation.semantic_id for operation in model.operations}
    assert "structure.definition_named_components/declared" in names
    assert "structure.definition_components/declared" not in names
    assert "text.gliner_definitions/source-native" not in names
    operation = model.operation("structure.definition_named_components/declared")
    assert (
        next(role.kind for role in operation.roles if role.direction == "output")
        == "urn:corpus:structural:DeclaredNamedDefinitionComponentsReport"
    )
    assert {
        (target.path, target.input_role, target.variant) for target in operation.reference_targets
    } == {
        ("/constructions_input", "constructions", "product"),
        (
            "/witnesses/*/basis/annotation_product",
            "annotations",
            "product",
        ),
        ("/witnesses/*/basis/primary_match", "constructions", "member"),
        ("/witnesses/*/basis/primary_scope/*", "constructions", "member"),
    }
    from corpus_structure.semantic.data_operation_kind_refinements import input_kind_refinements

    assert (
        "urn:corpus:structural:DeclaredNamedDefinitionComponentsReport"
        in input_kind_refinements(
            model, ("urn:corpus:structural:DeclaredDefinitionComponentsReport",)
        )["urn:corpus:structural:DeclaredDefinitionComponentsReport"]
    )
    assert set(operation.dependencies) == {
        "segment.sentences/source-native",
        "text.constructions/source-native",
    }


def test_named_witness_uses_only_producing_roles_and_generic_component_refuses_it():
    from pydantic import ValidationError

    from corpus_structure.semantic.structural_products import (
        DeclaredDefinitionBasisWitness,
        DeclaredLocatedDefinitionComponent,
        declared_definition_component,
    )

    witness = DeclaredDefinitionBasisWitness(
        annotation_product={"variant": "product", "role": "annotations"},
        block_id="block",
        dependency_digest="a" * 64,
        rule="define",
        variant="active",
        nodes=(1,),
        primary_match={"variant": "member", "role": "constructions", "member_id": "match"},
        primary_scope=({"variant": "member", "role": "constructions", "member_id": "scope"},),
    )
    component = declared_definition_component(
        term=dict(passage_id="p", start=0, end=1, text="x"),
        content=dict(passage_id="p", start=2, end=3, text="y"),
        interpretation="definition",
        basis="matched_cue",
        scope="selected",
        evidence=("p",),
        reason="retained named binding",
    )
    assert witness.primary_match == {
        "variant": "member",
        "role": "constructions",
        "member_id": "match",
    }
    with pytest.raises(ValidationError):
        DeclaredLocatedDefinitionComponent.model_validate(
            {**component.model_dump(mode="python"), "witness": witness}
        )
