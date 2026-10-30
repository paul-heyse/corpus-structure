"""Model-derived parsing products, immutable original bytes and build-pinned relational reads.

The LinkML companion supplies record shapes through the existing semantic compiler. Domain
checks below establish partition, occurrence and origin semantics; database checks additionally
establish endpoint custody. Bulk publication uses a fenced native function, never ORM sessions.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, select, text

from .identity import canonical_bytes
from .metadata import table
from .prepare import prepare_release
from .types import PreparedRelease, SourceArtifact, SourceBundle

PARSING_MODEL = Path(__file__).resolve().parents[1] / "model/semantic/parsing-products.yaml"
PARSING_CONTRACT_DIGEST = sha256(PARSING_MODEL.read_bytes()).hexdigest()
COLLECTIONS = (
    "representations",
    "components",
    "nodes",
    "relationships",
    "endpoints",
    "mappings",
    "mapping_endpoints",
    "dependencies",
)
RELATIONS = {
    "representations": "kb.parsing_representation",
    "components": "kb.parsing_component",
    "nodes": "kb.parsing_node",
    "relationships": "kb.parsing_relationship",
    "endpoints": "kb.parsing_endpoint",
    "mappings": "kb.parsing_mapping",
    "mapping_endpoints": "kb.parsing_mapping_endpoint",
    "dependencies": "kb.parsing_dependency",
}


class ParsingProductUnavailable(ValueError):
    """The retained contract has no admitted reader in this implementation."""


@lru_cache(maxsize=1)
def parsing_contract() -> PreparedRelease:
    """Reuse the admitted compiler and its cached, frozen Pydantic boundary adapters."""
    return prepare_release(
        SourceBundle("parsing", (SourceArtifact("parsing", PARSING_MODEL.read_bytes()),))
    )


def _index(rows: list[dict[str, Any]], *keys: str) -> dict[Any, dict[str, Any]]:
    result = {}
    for row in rows:
        key = tuple(row[k] for k in keys)
        if key in result:
            raise ValueError(f"duplicate parsing occurrence identity: {keys}/{key}")
        result[key] = row
    return result


def _ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: row["ordinal"])
    if [row["ordinal"] for row in ordered] != list(range(len(ordered))):
        raise ValueError("parsing endpoint/component ordinals must be contiguous from zero")
    return ordered


def _covers(extents: list[tuple[int, int]], length: int) -> bool:
    end = 0
    for start, stop in sorted(extents):
        if start > end:
            return False
        end = max(end, stop)
    return end == length


def _validate_product(p: dict[str, Any], original: bytes) -> None:
    if p["artifact_digest"] != sha256(original).hexdigest():
        raise ValueError("original artifact digest differs")
    if p["lifecycle"] not in {"available", "failed", "cancelled"}:
        raise ValueError("only terminal parsing products may be persisted")
    reps = _index(p["representations"], "representation_id")
    components = _index(p["components"], "component_id")
    nodes = _index(p["nodes"], "node_id")
    relations = _index(p["relationships"], "relationship_id")
    mappings = _index(p["mappings"], "mapping_id")
    dependencies = _index(p["dependencies"], "name")
    originals = [rep for rep in reps.values() if rep["kind"] == "original"]
    if len(originals) != 1:
        raise ValueError("one original byte representation is required, including decoding failure")
    if sum(rep["kind"] == "canonical" for rep in reps.values()) != 1:
        raise ValueError("one canonical representation declares the build's output universe")
    for rep in reps.values():
        if rep["kind"] == "original":
            if (
                rep["unit"] != "byte"
                or rep.get("text_content") is not None
                or rep["extent_length"] != len(original)
            ):
                raise ValueError("original representation must retain its exact byte space")
        elif (
            rep["unit"] != "codepoint"
            or not isinstance(rep.get("text_content"), str)
            or rep["extent_length"] != len(rep["text_content"])
        ):
            raise ValueError("text representation must declare its codepoint length")
        if rep["kind"] == "decoded" and any(
            not rep.get(key) for key in ("encoding", "decoder", "newline_policy")
        ):
            raise ValueError("decoded representation requires encoding, decoder and newline policy")

    def extent(row: dict[str, Any]) -> None:
        rep = reps.get((row["representation_id"],))
        if (
            rep is None
            or row["unit"] != rep["unit"]
            or not 0 <= row["start_offset"] <= row["end_offset"] <= rep["extent_length"]
        ):
            raise ValueError(
                "extent has missing representation, swapped coordinate unit or invalid bounds"
            )

    for row in components.values():
        extent(row)
    for row in nodes.values():
        fields = ("representation_id", "unit", "start_offset", "end_offset")
        if row["origin"] == "literal":
            if any(key not in row for key in fields) or row.get("origin_reason") is not None:
                raise ValueError("literal node requires its representation-qualified extent")
            extent(row)
        elif any(key in row for key in fields) or not row.get("origin_reason"):
            raise ValueError("synthetic node requires a reason and no fabricated literal extent")
    for rep in reps.values():
        rows = _ordered(
            [r for r in components.values() if r["representation_id"] == rep["representation_id"]]
        )
        position = 0
        for row in rows:
            if row["start_offset"] < position or row["start_offset"] == row["end_offset"]:
                raise ValueError("component partition overlaps or contains an empty component")
            if rep["partition_state"] == "complete" and row["start_offset"] != position:
                raise ValueError("complete partition has a gap")
            position = row["end_offset"]
        if rep["partition_state"] == "complete" and position != rep["extent_length"]:
            raise ValueError("partial partition cannot be declared complete")
        if rep["recognition_state"] == "complete" and any(
            row["category"] == "unknown" for row in rows
        ):
            raise ValueError("unknown material cannot establish complete recognition")

    def custody(row: dict[str, Any]) -> bool:
        target = row.get("target_task_id")
        dep = row.get("dependency_name")
        if target is None:
            if dep is not None:
                raise ValueError("local endpoint cannot declare dependency custody")
            return True
        declared = dependencies.get((dep,))
        if declared is None or target != declared["target_task_id"]:
            raise ValueError("cross-build endpoint requires its named dependency")
        return False

    _index(p["endpoints"], "relationship_id", "ordinal")
    for row in p["endpoints"]:
        if (row["relationship_id"],) not in relations:
            raise ValueError("endpoint has no relationship occurrence")
        if (row.get("component_id") is None) == (row.get("node_id") is None):
            raise ValueError("endpoint must identify exactly one component or structural node")
        if custody(row) and (
            (row.get("component_id"),) not in components and (row.get("node_id"),) not in nodes
        ):
            raise ValueError("endpoint has no local occurrence custody")
    containment = {}
    for relation in relations.values():
        rows = _ordered(
            [r for r in p["endpoints"] if r["relationship_id"] == relation["relationship_id"]]
        )
        if len(rows) < 2:
            raise ValueError("relationship requires at least two ordered endpoints")
        expected_roles = {
            "contains": ("parent", "child"),
            "structural_parent": ("parent", "child"),
            "reference": ("source", "target"),
            "binds": ("invocation", "definition"),
            "derived_from": ("target", "source"),
            "sequence": ("source", "target"),
        }[relation["kind"]]
        if tuple(row["role"] for row in rows) != expected_roles:
            raise ValueError(
                "relationship endpoints differ from the supported ordered role contract"
            )
        if relation["kind"] in {"contains", "structural_parent"}:
            if (
                len(rows) != 2
                or [r["role"] for r in rows] != ["parent", "child"]
                or any(
                    r.get("target_task_id") is not None or r.get("node_id") is None for r in rows
                )
            ):
                raise ValueError("containment requires local ordered parent/child structural nodes")
            parent, child = (nodes[(r["node_id"],)] for r in rows)
            if (
                relation["kind"] == "contains"
                and parent["origin"] == child["origin"] == "literal"
                and (
                    parent["representation_id"] != child["representation_id"]
                    or not parent["start_offset"]
                    <= child["start_offset"]
                    <= child["end_offset"]
                    <= parent["end_offset"]
                )
            ):
                raise ValueError("illegal structural containment extent")
            containment.setdefault(parent["node_id"], []).append(child["node_id"])
    visited: set[str] = set()
    active: set[str] = set()
    for node in containment:
        stack = [(node, False)]
        while stack:
            current, leaving = stack.pop()
            if leaving:
                active.remove(current)
                visited.add(current)
            elif current in active:
                raise ValueError("containment cycle")
            elif current not in visited:
                active.add(current)
                stack.append((current, True))
                stack.extend((child, False) for child in containment.get(current, ()))
    _index(p["mapping_endpoints"], "mapping_id", "side", "ordinal")
    for row in p["mapping_endpoints"]:
        if (row["mapping_id"],) not in mappings:
            raise ValueError("mapping endpoint has no transformation occurrence")
        if custody(row):
            extent(row)
    for mapping in mappings.values():
        counts = {}
        for side in ("source", "target"):
            counts[side] = len(
                _ordered(
                    [
                        r
                        for r in p["mapping_endpoints"]
                        if r["mapping_id"] == mapping["mapping_id"] and r["side"] == side
                    ]
                )
            )
        fidelity = mapping["fidelity"]
        if (
            (fidelity == "exact" and not all(counts.values()))
            or (fidelity == "synthetic" and (counts["source"] or not counts["target"]))
            or (fidelity == "excluded" and (not counts["source"] or counts["target"]))
        ):
            raise ValueError("mapping fidelity differs from its ordered source/target extents")
        if fidelity == "exact":
            if mapping["operation"] != "copy":
                raise ValueError("exact mapping requires the supported copy transformation")
            endpoints = [
                r for r in p["mapping_endpoints"] if r["mapping_id"] == mapping["mapping_id"]
            ]
            if len({r["unit"] for r in endpoints}) != 1:
                raise ValueError("exact copy cannot substitute byte and codepoint spaces")
            if all(r.get("target_task_id") is None for r in endpoints):
                values = {}
                for side in ("source", "target"):
                    parts = []
                    for endpoint in _ordered([r for r in endpoints if r["side"] == side]):
                        rep = reps[(endpoint["representation_id"],)]
                        if rep["unit"] == "byte":
                            part = original[endpoint["start_offset"] : endpoint["end_offset"]]
                        else:
                            part = rep["text_content"][
                                endpoint["start_offset"] : endpoint["end_offset"]
                            ].encode("utf8")
                        parts.append(part)
                    values[side] = b"".join(parts)
                if values["source"] != values["target"]:
                    raise ValueError("exact copy mapping content differs")
    if p["provenance_state"] == "complete":
        if any(rep["kind"] == "canonical" and rep["extent_length"] for rep in reps.values()):
            raise ValueError(
                "complete original-to-canonical provenance requires a "
                "qualified decoding/projection transform"
            )
        if any(m["fidelity"] == "unknown" for m in mappings.values()):
            raise ValueError("unknown mapping cannot establish complete provenance")
        for rep in reps.values():
            if rep["kind"] == "canonical" and not _covers(
                [
                    (r["start_offset"], r["end_offset"])
                    for r in p["mapping_endpoints"]
                    if r["side"] == "target"
                    and r.get("target_task_id") is None
                    and r["representation_id"] == rep["representation_id"]
                ],
                rep["extent_length"],
            ):
                raise ValueError("complete provenance leaves canonical material unmapped")


@dataclass(frozen=True, slots=True)
class PreparedParsingProduct:
    """Deep immutable transport: canonical bytes, never a mutable nested model copy."""

    payload: bytes
    original: bytes
    contract_digest: str

    @property
    def digest(self) -> str:
        return sha256(self.payload).hexdigest()

    def values(self) -> dict[str, Any]:
        return json.loads(self.payload)


def prepare_parsing_product(
    payload: Mapping[str, Any], original_bytes: bytes | bytearray | memoryview
) -> PreparedParsingProduct:
    original_bytes = bytes(original_bytes)
    value = (
        parsing_contract()
        .validate_json("ParsingProduct", json.dumps(dict(payload)))
        .model_dump(mode="json")
    )
    for key in COLLECTIONS:
        value.setdefault(key, [])
    _validate_product(value, original_bytes)
    return PreparedParsingProduct(canonical_bytes(value), original_bytes, PARSING_CONTRACT_DIGEST)


def store_parsing_product(
    conn: Connection, *, task_id: int, attempt: int, holder: str, product: PreparedParsingProduct
) -> str:
    """Publish only behind the same running-attempt custody as source completion."""
    checked = prepare_parsing_product(product.values(), product.original)
    if checked != product:
        raise ValueError("parsing contract or canonical payload differs")
    return conn.execute(
        text(
            "SELECT ops.publish_parsing_product("
            ":task,:attempt,:holder,:contract,:payload,:original)"
        ),
        dict(
            task=task_id,
            attempt=attempt,
            holder=holder,
            contract=product.contract_digest,
            payload=product.payload,
            original=product.original,
        ),
    ).scalar_one()


def read_parsing_product(conn: Connection, *, task_id: int) -> PreparedParsingProduct | None:
    """A pinned missing product is unavailable; a matching corrupt product refuses."""
    products, artifacts = table("ops.parsing_product"), table("kb.source_artifact")
    row = (
        conn.execute(
            select(products, artifacts.c.content.label("original"))
            .outerjoin(artifacts, products.c.artifact_digest == artifacts.c.artifact_digest)
            .where(products.c.task_id == task_id)
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        return None
    if row["original"] is None:
        raise ValueError("retained parsing product has lost its original artifact custody")
    if row["contract_digest"] != PARSING_CONTRACT_DIGEST:
        raise ParsingProductUnavailable("retained parsing contract is unsupported by this reader")
    result = prepare_parsing_product(json.loads(bytes(row["payload"])), bytes(row["original"]))
    if result.digest != row["product_digest"] or result.contract_digest != row["contract_digest"]:
        raise ValueError("retained parsing product digest/contract differs")
    values = result.values()
    for field, relation in RELATIONS.items():
        stored = []
        for native in conn.execute(
            select(table(relation)).where(table(relation).c.task_id == task_id)
        ).mappings():
            item = {
                key: value
                for key, value in native.items()
                if key != "task_id" and value is not None
            }
            if item.get("target_task_id") == task_id:
                item.pop("target_task_id")
            stored.append(item)
        expected = values[field]
        if sorted(canonical_bytes(item) for item in stored) != sorted(
            canonical_bytes(item) for item in expected
        ):
            raise ValueError(f"retained parsing relational projection differs: {relation}")
    return result
