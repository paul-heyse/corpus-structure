"""Compact source/coverage members emitted within each actual family product."""

from hashlib import sha256

from .identity import canonical_bytes
from .source_products import source_subject

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
        "original_source": value["source"]["document"],
        "analyzed_scope": {"source": value["source"], "selectors": value["selectors"]},
    }
    body = {
        "record_type": "manifest",
        **{key: value[key] for key in ("source", "selectors", "outcome")},
        "coverage": [
            {key: row[key] for key in _COVERAGE_FIELDS if key in row} for row in value["coverage"]
        ],
        "dependencies": value.get("dependencies", []),
    }
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
