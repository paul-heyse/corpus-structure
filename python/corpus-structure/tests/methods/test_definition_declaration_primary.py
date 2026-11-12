"""Independent native role fixture for the domain declaration chain projection."""

from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace
from typing import cast

import pytest
from semantic.test_formal_evidence import source

from corpus_structure.ingest.annotations import AnnotationProduct
from corpus_structure.methods.definition_declaration import (
    DeclarationNotQualified,
    primary_declaration_component,
)
from corpus_structure.methods.native_evidence import native_run
from corpus_structure.methods.native_evidence_layers import HANLP_FAMILIES, NativeEvidenceBuilder
from corpus_structure.semantic.characterization import validate_layer
from corpus_structure.semantic.constructions.layers import ConstructionLayer
from corpus_structure.semantic.constructions.retained_rules import (
    PRIMARY_RULE_FAMILY,
    PRIMARY_RULE_VOCABULARY,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import StructuralPassage

from .primary_reading_fixture import prepared

# Each native UD/SRL fact is authored independently of the consumer's checks.
_ROWS = (
    (
        "Definition 1 Let X be a set.",
        ("Definition", "1", "Let", "X", "be", "a", "set", "."),
        ("definition", "1", "let", "X", "be", "a", "set", "."),
        (
            (0, "root"),
            (1, "nummod"),
            (1, "dep"),
            (7, "nsubj"),
            (7, "cop"),
            (7, "det"),
            (3, "ccomp"),
            (1, "punct"),
        ),
        ((("PRED", 4, 5), ("ARG1", 3, 4), ("ARG2", 5, 7)),),
        {4: "copular"},
    ),
    (
        "Let Y be a set that contains elements from the set of X.",
        (
            "Let",
            "Y",
            "be",
            "a",
            "set",
            "that",
            "contains",
            "elements",
            "from",
            "the",
            "set",
            "of",
            "X",
            ".",
        ),
        (
            "let",
            "Y",
            "be",
            "a",
            "set",
            "that",
            "contain",
            "element",
            "from",
            "the",
            "set",
            "of",
            "X",
            ".",
        ),
        (
            (0, "root"),
            (5, "nsubj"),
            (5, "cop"),
            (5, "det"),
            (1, "ccomp"),
            (7, "nsubj"),
            (5, "acl:relcl"),
            (7, "obj"),
            (11, "case"),
            (11, "det"),
            (7, "obl"),
            (13, "case"),
            (11, "nmod"),
            (1, "punct"),
        ),
        (
            (("PRED", 2, 3), ("ARG1", 1, 2), ("ARG2", 3, 13)),
            (("PRED", 6, 7), ("ARG0", 5, 6), ("ARG1", 7, 8)),
        ),
        {2: "copular", 6: "active"},
    ),
    (
        "The elements of Y are called samples.",
        ("The", "elements", "of", "Y", "are", "called", "samples", "."),
        ("the", "element", "of", "Y", "be", "call", "sample", "."),
        (
            (2, "det"),
            (6, "nsubj:pass"),
            (4, "case"),
            (2, "nmod"),
            (6, "aux:pass"),
            (0, "root"),
            (6, "xcomp"),
            (6, "punct"),
        ),
        ((("PRED", 5, 6), ("ARG1", 0, 4), ("ARG2", 6, 7)),),
        {5: "passive"},
    ),
)


def fixture():
    text = " ".join(row[0] for row in _ROWS)
    view = source((text, "text", "", ""))
    projection = dict(
        text=view.text,
        pieces=view.pieces,
        items=[item["self_ref"] for item in view.items],
        ancestors=view.ancestors,
        health=view.health,
    )
    view = replace(
        view,
        ref=replace(view.ref, projection_digest=sha256(canonical_bytes(projection)).hexdigest()),
    )
    base = view.ref.native_product.values()
    scope = dict(
        source_view_ids=[view.ref.id],
        source_views=[
            dict(
                source_view_id=view.ref.id,
                key=view.ref.key,
                base_document=base,
                section_pointer=view.ref.section_pointer,
                membership=view.ref.membership,
                projection_digest=view.ref.projection_digest,
                recipe_digest=view.ref.recipe_digest,
            )
        ],
        profile="independent-declaration-columns",
        selectors=[dict(projection=view.ref.projection_digest, start=0, end=len(text))],
    )
    operation = dict(
        key="text.native_evidence",
        version="1",
        runtime="fixture",
        model="fixture",
        grammar="none",
        configuration="fixture",
        input="fixture",
        context="source",
    )
    native = NativeEvidenceBuilder(
        base, scope, operation, profile="full_native", families=HANLP_FAMILIES
    )
    primary = ConstructionLayer(
        base, scope, dict(operation, key="text.constructions"), families=(PRIMARY_RULE_FAMILY,)
    )
    offset = 0
    for number, (sentence, words, lemmas, arcs, frames, voices) in enumerate(_ROWS):
        prepared_words = list(words)
        tokens, positions, cursor = [], [], offset
        for index, word in enumerate(words):
            start = text.index(word, cursor)
            end = start + len(word)
            cursor = end
            occurrence = native.occurrence(view, start, end)
            key = f"fixture-canonical/{number}/{index}"
            native.annotation(
                key,
                "fixture.canonical_token",
                "hanlp.tokens",
                [occurrence],
                "independent-source-token-1",
                word,
            )
            tokens.append(
                dict(
                    key=key,
                    occurrence=occurrence,
                    text=word,
                    source=SimpleNamespace(start=start, end=end, space=False, role="prose"),
                )
            )
            positions.append((start, end))
        srl = [[(" ".join(words[a:b]), role, a, b) for role, a, b in frame] for frame in frames]
        native.hanlp_sentence(
            view,
            cast(AnnotationProduct, SimpleNamespace(block_id="authored")),
            tokens,
            number,
            dict(
                lemma=list(lemmas),
                pos=["NN"] * len(words),
                dependency=[list(arc) for arc in arcs],
                srl=srl,
                constituency=["S", prepared_words],
            ),
            dict(prepared_words=prepared_words),
            "hanlp",
        )
        for index, voice in voices.items():
            start, end = positions[index]
            occurrence = primary.occurrence(view, start, end)
            key = f"voice/{number}/{index}"
            primary.terms[key + "/predicate"] = dict(
                local_id=key + "/predicate",
                kind="participant",
                family=PRIMARY_RULE_FAMILY,
                vocabulary=PRIMARY_RULE_VOCABULARY,
                value=words[index],
                status="interpreted",
                occurrences=[occurrence],
            )
            primary.terms[key + "/voice"] = dict(
                local_id=key + "/voice",
                kind="participant",
                family=PRIMARY_RULE_FAMILY,
                vocabulary=PRIMARY_RULE_VOCABULARY,
                value=voice,
                status="interpreted",
                occurrences=[occurrence],
            )
            primary.terms[key] = dict(
                local_id=key,
                kind="predicate",
                family=PRIMARY_RULE_FAMILY,
                vocabulary=PRIMARY_RULE_VOCABULARY,
                value="independent-primary-predication",
                status="interpreted",
                occurrences=[occurrence],
                children=[
                    dict(role="predicate", target=key + "/predicate", structural=True),
                    dict(role="voice", target=key + "/voice", structural=True),
                ],
            )
        offset += len(sentence) + 1
    native.native_runs.append(
        native_run(
            "hanlp",
            "full_native",
            "{}",
            model="authored-native-columns",
            version="1",
            runtime_version="1",
            layout=[],
            text=[],
        )
    )
    native_layer = native.finish(prepared())
    primary.record(PRIMARY_RULE_FAMILY, scope["selectors"][0], "complete")
    from corpus_structure.semantic.constructions.retained_declarations import populate_declaration_readings
    populate_declaration_readings(primary, view, {native_layer.reference(101): native_layer})
    primary_layer = primary.finish(prepared(), dependencies={native_layer.reference(101): native_layer})
    layers = {
        native_layer.reference(101): native_layer,
        primary_layer.reference(102): primary_layer,
    }
    passage = StructuralPassage(
        passage_id="definition",
        source_ref="source",
        start=0,
        end=len(text),
        text=text,
        scope="definition",
    )
    return view, passage, layers


def test_primary_native_declaration_chain_keeps_exact_roles_without_private_parser(monkeypatch):
    import corpus_structure.methods.pm2_hanlp_products as owner

    view, passage, layers = fixture()
    monkeypatch.setattr(
        owner,
        "hanlp_products",
        lambda *_args, **_kwargs: pytest.fail("consumer reran linguistic recognition"),
    )
    from corpus_structure.semantic.constructions import retained_declarations
    monkeypatch.setattr(retained_declarations, "_sentences", lambda *_a, **_k: pytest.fail("consumer reconstructed native sentences"))
    monkeypatch.setattr(retained_declarations, "_facts", lambda *_a, **_k: pytest.fail("consumer recognized declaration syntax"))
    component = primary_declaration_component(layers, view, passage)
    assert component.term.text == "samples"
    assert component.content.text == (
        "Let X be a set. Let Y be a set that contains elements from the set of X. The elements of Y"
    )
    witness = component.declaration_chain
    assert (
        witness is not None
        and witness.parser is None
        and witness.version == "definition-declaration-chain-2"
    )
    assert witness.primary_evidence and all(row.layer in layers for row in witness.primary_evidence)
    assert witness.naming_frame in {row.identity for row in witness.primary_evidence}
    assert len(witness.bindings) == 1
    assert witness.bindings[0].subject_token == 3 and witness.bindings[0].use_token == 12


@pytest.mark.parametrize(
    "failure", ["missing_native", "missing_voice", "broken_native_reference", "clipped_sentence"]
)
def test_primary_declaration_missing_or_substituted_native_evidence_refuses(failure):
    view, passage, layers = fixture()
    if failure == "missing_native":
        layers = {
            pin: report for pin, report in layers.items() if not report.payload.get("native_runs")
        }
    elif failure == "missing_voice":
        layers = {
            pin: report for pin, report in layers.items() if report.payload.get("native_runs")
        }
    elif failure == "broken_native_reference":
        pin = next(pin for pin, report in layers.items() if report.payload.get("native_runs"))
        body = layers[pin].payload
        body["memberships"] = [
            row
            for row in body["memberships"]
            if not (row["role"] == "token" and row["group"].endswith("/srl/0/member/0"))
        ]
        changed = validate_layer(prepared(), body)
        layers = {
            **{key: value for key, value in layers.items() if key != pin},
            changed.reference(101): changed,
        }
    else:
        passage = passage.model_copy(update=dict(start=1, text=passage.text[1:]))
    with pytest.raises((DeclarationNotQualified, ValueError)):
        primary_declaration_component(layers, view, passage)


def test_active_method_and_detached_primary_replay_use_exact_same_evidence(monkeypatch):
    from corpus_structure.methods.definition_declaration import (
        DeclarationChainSelection,
        DeclarationComponentsConfig,
        DeclarationComponentsMethod,
    )
    from corpus_structure.methods.model_observation import (
        PRIVATE_DECLARATION_INPUT,
        PRIVATE_DECLARATION_POLICY,
    )
    from corpus_structure.semantic.observations import source_value
    from corpus_structure.semantic.structural_products import (
        ExternalSourceRef,
        StructuralInput,
        StructuralProductReport,
    )
    from corpus_structure.serve import model_observation_replay as replay

    view, passage, layers = fixture()
    ref = ExternalSourceRef(
        project_id="fixture",
        run_id=1,
        cut_id=1,
        release_id="fixture",
        result_revision=0,
        source_view_id=view.ref.id,
        native_task_id=view.ref.native_product.task_id,
        native_product_key=view.ref.native_product.product_key,
        native_content_digest=view.ref.native_product.content_digest,
        projection_digest=view.ref.projection_digest,
        recipe_digest=view.ref.recipe_digest,
        coordinate_version=3,
    )
    passage = passage.model_copy(update=dict(source_ref=ref.identity))
    inputs = StructuralInput(
        question="local definition",
        scope=passage.scope,
        inventory_id="fixture",
        policy_id="declaration-primary",
        sources=(ref,),
        passages=(passage,),
        dependencies=("input-policy:fixture",),
    )
    cfg = DeclarationComponentsConfig(
        inputs=inputs,
        structural_input_digest=inputs.identity,
        selections=(DeclarationChainSelection(passage_id=passage.passage_id),),
        characterization_layers=tuple(pin.values() for pin in layers),
    )
    release = SimpleNamespace(
        manifest=canonical_bytes(
            dict(
                dependencies=[
                    [
                        PRIVATE_DECLARATION_INPUT,
                        sha256(canonical_bytes(PRIVATE_DECLARATION_POLICY)).hexdigest(),
                    ]
                ]
            )
        )
    )

    def validate(selected):
        assert selected == inputs

    reader = SimpleNamespace(
        prepared=release,
        validate_structural_inputs=validate,
        source_view=lambda identity: (
            view if identity == view.ref.id else pytest.fail("wrong source")
        ),
        primary_characterization=lambda identity, **_kwargs: (
            layers if identity == view.ref.id else pytest.fail("wrong primary source")
        ),
    )
    (result,) = DeclarationComponentsMethod().run(
        (SimpleNamespace(ref=None),), cfg, SimpleNamespace(reader=reader, check_active=lambda: None)
    )
    report = StructuralProductReport.model_validate(result.structural_product)
    from semantic.structural_release_fixture import released_report

    released = released_report(report, method=DeclarationComponentsMethod.name, version="2")
    chain = released["definition_components"]["components"][0]["declaration_chain"]
    assert chain["version"] == "definition-declaration-chain-2"
    assert "parser" not in chain and chain["primary_evidence"]
    assert chain["naming_frame"].startswith("annotation:")
    assert chain["bindings"][0]["frame"].startswith("annotation:")
    retained = dict(
        configuration=cfg.model_dump(mode="json"),
        body=dict(
            method=DeclarationComponentsMethod.name,
            operation_version="2",
            parse_detail=source_value(result.parse_detail),
        ),
    )
    monkeypatch.setattr(replay, "_primary_observation_reader", lambda *_args: (reader, layers))
    replay._verify_primary_observation(None, None, retained, report, {}, iter(()), None)
    assert report.definition_components is not None
    (component,) = report.definition_components.components
    changed = component.model_copy(
        update=dict(term=component.term.model_copy(update=dict(text="wrong")))
    )
    tampered = report.model_copy(
        update=dict(
            definition_components=report.definition_components.model_copy(
                update=dict(components=(changed,))
            )
        )
    )
    with pytest.raises(ValueError, match="exact retained projection"):
        replay._verify_primary_observation(None, None, retained, tampered, {}, iter(()), None)
