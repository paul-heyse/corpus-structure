"""Current nominal contextual products from controlled native observations."""

from corpus_structure.semantic.characterization_manifests import append_manifest, manifest_contract
from corpus_structure.semantic.construction_products import (
    CharacterizationSnapshot,
    interpreted_member_contracts,
    validate_interpreted_product,
)
from corpus_structure.semantic.contextual_characterization import (
    ContextInput,
    ContextPart,
    ContextualLayer,
)
from corpus_structure.semantic.contextual_native_products import (
    ContextualNativeProduct,
    contextual_native_values,
)
from corpus_structure.semantic.data_operation_identity import (
    body_identity,
    contextual_product_identity,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_value
from methods.native_evidence_support import profiles


def context_builder(case):
    frame = case.primary.frame
    context = ContextInput.build([ContextPart(frame, 0, len(frame.text))], frame.value["selectors"])
    return ContextualLayer(
        frame.value["source"],
        {"selectors": list(context.focal)},
        {"key": "text.contextual_native/source-native"},
        context,
    )


def canonical_tokens(case, builder):
    text = case.primary.frame.text
    return [
        dict(
            text=text[row["start"] : row["end"]],
            sentence=row["sentence"],
            start=row["start"],
            end=row["end"],
            occurrences=[builder.occurrence(case.primary.frame, row["start"], row["end"])],
        )
        for row in case.words
    ]


def dipo_reply():
    return dict(
        mode="learned",
        post_tokenizer_tokens=6,
        edus=[
            dict(tokens=[0, 2], chars=[0, 4], text="X X"),
            dict(tokens=[2, 6], chars=[4, 14], text="é x+y [3]."),
        ],
        spans=[dict(left=[0, 1], right=[1, 2], nuclearity="SN", relation="contingency-condition")],
        boundaries=[
            dict(token_end=2, learned=True, forced=False, disposition="retained"),
            dict(token_end=6, learned=True, forced=False, disposition="retained"),
        ],
    )


def context_product(case, *, maverick=None, dipo=None, products=()):
    """Execute the current assembler and validate the actual contextual nominal product."""
    prepared, model = profiles()
    frame, source = case.primary.frame, case.primary.source
    tokens = canonical_tokens(case, context_builder(case))
    empty = canonical_bytes(
        {
            "source": source.value["source"],
            "selectors": source.value["selectors"],
            "members": [],
            "coverage": [],
        }
    )
    formal = CharacterizationSnapshot("literal-fixture:formal", empty)
    if products:
        (construction,) = products
        construction = CharacterizationSnapshot(construction.semantic_id, construction.content)
    else:
        construction = CharacterizationSnapshot("literal-fixture:construction", empty)
    dependencies = (formal, construction)
    observed = []
    for provider, reply, families in (
        ("maverick", maverick, ("maverick.mentions", "maverick.clusters")),
        ("dipo", dipo, ("dipo.edus", "dipo.rst")),
    ):
        selector = dict(projection=frame.projection_digest, start=0, end=len(frame.text))
        observations = []
        if reply is not None:
            request = (
                dict(sentences=ContextualLayer.sentences(tokens))
                if provider == "maverick"
                else dict(text=frame.text)
            )
            observations = [
                source_value(
                    dict(
                        provider=provider,
                        request=request,
                        native=reply,
                        source_map=dict(
                            context_pieces=[
                                dict(source=frame.source_key, start=0, end=len(frame.text))
                            ],
                            tokens=[
                                dict(
                                    text=row["text"],
                                    sentence=row["sentence"],
                                    start=row["start"],
                                    end=row["end"],
                                )
                                for row in tokens
                            ],
                        ),
                    )
                )
            ]
        value = dict(
            source=source.value["source"],
            selectors=source.value["selectors"],
            observations=observations,
            provider=provider,
            profile_digest="0" * 64,
            source_pin=frame.pin.values(),
            standing="native_provider_observation",
            outcome="complete" if reply is not None else "partial",
            coverage=[
                dict(
                    family=family,
                    eligible=[selector],
                    examined=[selector] if reply is not None else [],
                    unexamined=[] if reply is not None else [selector],
                    availability="available" if reply is not None else "unavailable",
                    outcome="complete" if reply is not None else "failed",
                    **({} if reply is not None else {"reason": "no literal observation supplied"}),
                )
                for family in families
            ],
        )
        name = "DdoMaverick" if provider == "maverick" else "DdoDipo"
        value = append_manifest(value, manifest_contract(prepared, model, name + "Manifest"))
        if provider == "maverick":
            (manifest,) = value["members"]
            manifest["body"]["annotations_input"] = {"variant": "product", "role": "annotations"}
        content = canonical_bytes(value)
        checked = prepared.validate_json(name + "Observations", content)
        product_id = contextual_product_identity(
            kind=manifest_contract(prepared, model, name + "Observations"),
            context=case.primary.context,
            body=body_identity(checked.model_dump(mode="python", exclude_unset=True)).key,
        ).key
        observed.append(CharacterizationSnapshot(product_id, content))
    value = contextual_native_values(
        source,
        frame,
        dependencies,
        observed[0],
        observed[1],
        interpreted_member_contracts(prepared, model),
        "literal-fixture",
        lambda: None,
    )
    product = validate_interpreted_product(
        prepared,
        model,
        value,
        source,
        (*dependencies, *observed),
        product_type=ContextualNativeProduct,
        subject_context=case.primary.context,
        contextual_proxy_inputs={"formal": formal, "constructions": construction},
    )
    return product
