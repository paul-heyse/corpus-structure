"""Compact source/coverage members emitted within each actual family product."""

from hashlib import sha256

from .identity import canonical_bytes
from .source_products import source_subject

_LEARNED_KIND_PREFIX = "https://corpus-structure.dev/semantic/data-operation-learned/Ddo"


def is_learned_observation(prepared, kind):
    return (
        kind.startswith(_LEARNED_KIND_PREFIX)
        and "DdoLearnedObservation" in prepared.index.by_iri[kind].ancestors
    )


def learned_manifest_input_roles(prepared, kind):
    if not kind.startswith(_LEARNED_KIND_PREFIX):
        return ()
    definition = prepared.index.by_iri[kind]
    if definition.name == "DdoContextualNativeProduct":
        from .contextual_proxy_references import CONTEXTUAL_NATIVE_INPUT_ROLES

        return CONTEXTUAL_NATIVE_INPUT_ROLES
    if "DdoLearnedObservation" in definition.ancestors:
        members = next(prop for prop in definition.properties if prop.name == "members")
        packet = prepared.index.definitions[members.range]
        body = next(prop for prop in packet.properties if prop.name == "body")
        definition = prepared.index.definitions[body.range]
    if "DdoCharacterizedProduct" not in definition.ancestors:
        return ()
    inputs = tuple(prop for prop in definition.properties if prop.range == "DdoSemanticReference")
    if any(
        not prop.name.endswith("_input") or not prop.required or prop.multivalued for prop in inputs
    ):
        raise ValueError("learned manifest requires closed scalar dependency roles")
    return tuple(prop.name.removesuffix("_input") for prop in inputs)


def learned_dependency_products(prepared, kind, value, member):
    """Resolve every declared whole input through its exact selected producer use."""
    from .data_product_reference import SemanticReference, read_semantic_reference
    from .reference_resolution import selected_producing_reference_bindings

    roles = learned_manifest_input_roles(prepared, kind)
    if not roles:
        return ()
    if member is None:
        raise ValueError("learned characterization lacks its acquired producing inputs")
    manifest = value
    if (
        value.get("record_type") != "manifest"
        and prepared.index.by_iri[kind].name != "DdoContextualNativeProduct"
    ):
        (packet,) = value["members"]
        manifest = packet["body"]
    producing = selected_producing_reference_bindings(member, require_complete=True)
    products = []
    for role in roles:
        reference = read_semantic_reference(manifest[role + "_input"])
        if reference != SemanticReference.whole(role):
            raise ValueError("learned dependency differs from its declared whole input role")
        original = producing.resolve(reference)
        if original.member_id is not None:
            raise ValueError("learned dependency requires its exact whole producing input")
        products.append(original.product_id)
    return tuple(products)


# This is the declared common coverage view; richer per-operation columns stay in the parent.
_COVERAGE_FIELDS = (
    "family",
    "eligible",
    "examined",
    "unexamined",
    "availability",
    "outcome",
    "reason",
)


def manifest_contract(prepared, model, name):
    owner = prepared.index.definitions[name].iri
    return next(
        identity.key
        for identity in model.identities
        if identity.owner == owner and identity.domain == "kind"
    )


def compact_manifest(value, kind_contract):
    context = {
        "subject": source_subject(value["source"]),
        "subject_definition": "original-source-view",
        "original_source": value["source"]["document"],
        "analyzed_scope": {"source": value["source"], "selectors": value["selectors"]},
    }
    body = {
        "record_type": "manifest",
        **{key: value[key] for key in ("source", "selectors", "outcome")},
        "coverage": [
            {key: row[key] for key in _COVERAGE_FIELDS if key in row} for row in value["coverage"]
        ],
    }
    if "dependencies" in value:
        body["dependencies"] = value["dependencies"]
    return {
        "member_id": "characterization-manifest:"
        + sha256(canonical_bytes([kind_contract, context])).hexdigest(),
        "kind_contract": kind_contract,
        "context": context,
        "body": body,
    }


def append_manifest(value, kind_contract):
    if any(packet["body"].get("record_type") == "manifest" for packet in value.get("members", ())):
        raise ValueError("producer already contains a compact characterization manifest")
    return {**value, "members": [*value.get("members", ()), compact_manifest(value, kind_contract)]}


def analytical_packets(value, kind_contract):
    """Validate the one summary against its actual parent before exposing analytical units."""
    manifests = [
        packet for packet in value["members"] if packet["body"].get("record_type") == "manifest"
    ]
    if manifests != [compact_manifest(value, kind_contract)]:
        raise ValueError(
            "compact manifest differs from its actual parent source/coverage/dependencies"
        )
    return tuple(
        packet for packet in value["members"] if packet["body"].get("record_type") != "manifest"
    )
