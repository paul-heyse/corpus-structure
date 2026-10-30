"""Model-derived parsing products, immutable original bytes and build-pinned relational reads.

The LinkML companion supplies record shapes through the existing semantic compiler. Domain
checks below establish partition, occurrence and origin semantics; database checks additionally
establish endpoint custody. Bulk publication uses a fenced native function, never ORM sessions.
"""

from __future__ import annotations

import base64
import json
from bisect import bisect_left, bisect_right
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import Connection, select, text

from .identity import canonical_bytes
from .metadata import table
from .prepare import prepare_release
from .types import PreparedRelease, SourceArtifact, SourceBundle

if TYPE_CHECKING:
    from .contracts import ExecutionModelProducts

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
    from .contracts import trusted_execution_inputs

    return _parsing_boundary(trusted_execution_inputs().schema)


@lru_cache(maxsize=16)
def _parsing_boundary(bundle: SourceBundle) -> PreparedRelease:
    return prepare_release(bundle)


@dataclass(frozen=True, slots=True)
class PreparedParsingContext:
    """One archived schema/execution binding reused by pure kernels and pinned readers."""

    release_id: str | None
    boundary: PreparedRelease
    execution: ExecutionModelProducts
    contract_digest: str


def prepare_parsing_context(
    prepared: PreparedRelease, execution_schema: SourceBundle
) -> PreparedParsingContext:
    """Prepare from explicitly supplied archived inputs, without database/default lookup."""
    from .contracts import bound_execution_model, execution_payload

    model = bound_execution_model(prepared)
    if not any(c.id == "ParsingProduct" for c in model.concepts):
        raise ParsingProductUnavailable(
            "bound execution model has no supported parsing contract profile"
        )
    payload = execution_payload(prepared)
    if payload is None:
        raise ParsingProductUnavailable("parsing context requires a composed execution binding")
    manifest = json.loads(payload)["inputs"]["schema"]
    actual = {
        "root": execution_schema.root,
        "sources": [{"name": s.name, "sha256": s.digest} for s in execution_schema.sources],
    }
    if actual != manifest:
        raise ValueError(
            "explicit parsing schema inputs differ from the archived execution binding"
        )
    source = next((s for s in execution_schema.sources if s.name == "parsing_products"), None)
    if source is None:
        raise ParsingProductUnavailable("archived execution model has no parsing schema")
    return PreparedParsingContext(
        prepared.release_id, _parsing_boundary(execution_schema), model, source.digest
    )


def parsing_context_for_release(
    conn: Connection, prepared: PreparedRelease
) -> PreparedParsingContext:
    """Acquire original dependency bytes once at an explicit archive entry boundary."""
    from .contracts import execution_payload

    payload = execution_payload(prepared)
    if payload is None:
        raise ParsingProductUnavailable("parsing context requires a composed execution binding")
    manifest = json.loads(payload)["inputs"]["schema"]
    inputs = table("sem.input")
    names = ["execution/schema/" + s["name"] for s in manifest["sources"]]
    rows = conn.execute(
        select(inputs.c.input_name, inputs.c.content).where(
            inputs.c.release_id == prepared.release_id,
            inputs.c.input_kind == "dependency",
            inputs.c.input_name.in_(names),
        )
    ).mappings()
    sources = {r["input_name"]: bytes(r["content"]) for r in rows}
    if set(sources) != set(names):
        raise ValueError("archived parsing schema dependency custody is incomplete")
    bundle = SourceBundle(
        manifest["root"],
        tuple(
            SourceArtifact(s["name"], sources["execution/schema/" + s["name"]])
            for s in manifest["sources"]
        ),
    )
    return prepare_parsing_context(prepared, bundle)


@lru_cache(maxsize=1)
def _trusted_parsing_context() -> PreparedParsingContext:
    from .contracts import compile_execution_model, trusted_execution_inputs

    return PreparedParsingContext(
        None,
        parsing_contract(),
        compile_execution_model(trusted_execution_inputs()),
        PARSING_CONTRACT_DIGEST,
    )


def parsing_context_for_task(
    conn: Connection, task_id: int, context: PreparedParsingContext | None = None
) -> PreparedParsingContext:
    from .releases import open_release

    task, run = table("ops.task"), table("ops.run")
    release = conn.execute(
        select(run.c.release_id)
        .join_from(task, run, task.c.run_id == run.c.id)
        .where(task.c.id == task_id)
    ).scalar_one()
    if context is not None:
        if context.release_id != release:
            raise ValueError("parsing context differs from the producing task release")
        return context
    return parsing_context_for_release(conn, open_release(conn, release))


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


def representation_text(row: Mapping[str, Any]) -> str:
    """Decode the one explicit text variant without losing embedded NUL code points."""
    plain, encoded = row.get("text_content"), row.get("text_content_utf8_base64")
    if isinstance(plain, str) and encoded is None:
        if "\x00" in plain:
            raise ValueError("NUL source text requires the binary-safe representation variant")
        return plain
    if plain is None and isinstance(encoded, str):
        return base64.b64decode(encoded, validate=True).decode("utf8", errors="strict")
    raise ValueError("text representation requires exactly one typed content variant")


def _validate_product(p: dict[str, Any], original: bytes, context: PreparedParsingContext) -> None:
    from .parsing_contracts import parsing_relationships

    relationship_profiles = parsing_relationships(context.execution)
    adapter_id = p.get("adapter_id")
    adapter = next(
        (a for a in context.execution.parsing_adapters if a.adapter_id == adapter_id), None
    )
    if adapter_id is not None and adapter is None:
        raise ValueError("parsing product adapter is not admitted by its bound execution contract")
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
    relation_endpoints: dict[str, list[dict[str, Any]]] = defaultdict(list)
    mapping_endpoints: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    target_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for endpoint in p["endpoints"]:
        relation_endpoints[endpoint["relationship_id"]].append(endpoint)
    for endpoint in p["mapping_endpoints"]:
        mapping_endpoints[endpoint["mapping_id"], endpoint["side"]].append(endpoint)
        if endpoint["side"] == "target" and endpoint.get("target_task_id") is None:
            target_rows[endpoint["representation_id"]].append(endpoint)
    target_index = {}
    for representation, rows in target_rows.items():
        rows.sort(key=lambda row: (row["start_offset"], row["end_offset"]))
        maximum = 0
        prefix = []
        for row in rows:
            maximum = max(maximum, row["end_offset"])
            prefix.append(maximum)
        target_index[representation] = ([row["start_offset"] for row in rows], prefix, rows)
    originals = [rep for rep in reps.values() if rep["kind"] == "original"]
    text_values = {
        rep["representation_id"]: representation_text(rep)
        for rep in reps.values()
        if rep["kind"] != "original"
    }
    if len(originals) != 1:
        raise ValueError("one original byte representation is required, including decoding failure")
    if sum(rep["kind"] == "canonical" for rep in reps.values()) != 1:
        raise ValueError("one canonical representation declares the build's output universe")
    for rep in reps.values():
        if rep["kind"] == "original":
            if (
                rep["unit"] != "byte"
                or rep.get("text_content") is not None
                or rep.get("text_content_utf8_base64") is not None
                or rep["extent_length"] != len(original)
            ):
                raise ValueError("original representation must retain its exact byte space")
        elif rep["unit"] != "codepoint" or rep["extent_length"] != len(
            text_values[rep["representation_id"]]
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
            raise ValueError("nonliteral node requires a reason and no fabricated literal extent")
        if (
            row["kind"] == "text"
            and row["origin"] == "derived"
            and (
                row.get("name") not in {"text", "tail"}
                or "value" not in row
                or row.get("ordinal") not in {0, 1}
            )
        ):
            raise ValueError("derived final text slot requires its location, value and ordinal")
        if row["kind"] == "attribute" and (
            not row.get("name")
            or "value" not in row
            or "ordinal" not in row
            or row["ordinal"] < 0
            or row.get("attribute_outcome") not in {"retained", "discarded_duplicate", "unknown"}
        ):
            raise ValueError(
                "attribute occurrence requires its name, value, ordinal and native outcome"
            )
        for prefix in ("name", "value"):
            start, end = row.get(prefix + "_start_offset"), row.get(prefix + "_end_offset")
            if (start is None) != (end is None) or (
                start is not None
                and (
                    row["kind"] != "attribute"
                    or row["origin"] != "literal"
                    or not row["start_offset"] <= start <= end <= row["end_offset"]
                )
            ):
                raise ValueError(
                    "attribute lexical subrange must be paired and contained "
                    "in its literal occurrence"
                )
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
        rows = _ordered(relation_endpoints[relation["relationship_id"]])
        if len(rows) < 2:
            raise ValueError("relationship requires at least two ordered endpoints")
        expected_roles = tuple(
            endpoint.role for endpoint in relationship_profiles[relation["kind"]].endpoints
        )
        if tuple(row["role"] for row in rows) != expected_roles:
            raise ValueError(
                "relationship endpoints differ from the supported ordered role contract"
            )
        if relation["kind"] == "attribute_of":
            if any(
                row.get("target_task_id") is not None or row.get("node_id") is None for row in rows
            ):
                raise ValueError("attribute ownership requires local structural occurrences")
            attribute, owner = (nodes[(row["node_id"],)] for row in rows)
            if attribute["kind"] != "attribute" or owner["kind"] != "element":
                raise ValueError("attribute ownership requires an attribute and an element")
        if relation["kind"] == "text_of":
            if any(
                row.get("target_task_id") is not None or row.get("node_id") is None for row in rows
            ):
                raise ValueError("text ownership requires local structural occurrences")
            slot, owner = (nodes[(row["node_id"],)] for row in rows)
            if (
                slot["kind"] != "text"
                or slot["origin"] != "derived"
                or owner["kind"] not in {"element", "comment"}
            ):
                raise ValueError(
                    "text ownership requires a derived final slot and its native owner"
                )
        if (
            relation["kind"] == "derived_from"
            and rows[0].get("target_task_id") is None
            and rows[0].get("node_id") is not None
        ):
            target = nodes[(rows[0]["node_id"],)]
            if (
                target["kind"] == "text"
                and target["origin"] == "derived"
                and relation.get("ordinal") is None
            ):
                raise ValueError(
                    "final text source contributions require explicit relationship order"
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
            counts[side] = len(_ordered(mapping_endpoints[mapping["mapping_id"], side]))
        fidelity = mapping["fidelity"]
        if fidelity == "transformed" and (
            adapter is None
            or "mapping/" + mapping["operation"] not in adapter.capabilities
            or not all(counts.values())
        ):
            raise ValueError(
                "transformed contribution requires its admitted adapter/operation "
                "and both extent sets"
            )
        if (
            (fidelity == "exact" and not all(counts.values()))
            or (fidelity == "synthetic" and (counts["source"] or not counts["target"]))
            or (fidelity == "excluded" and (not counts["source"] or counts["target"]))
        ):
            raise ValueError("mapping fidelity differs from its ordered source/target extents")
        if fidelity == "exact":
            if mapping["operation"] != "copy":
                raise ValueError("exact mapping requires the supported copy transformation")
            endpoints = (
                mapping_endpoints[mapping["mapping_id"], "source"]
                + mapping_endpoints[mapping["mapping_id"], "target"]
            )
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
                            part = text_values[rep["representation_id"]][
                                endpoint["start_offset"] : endpoint["end_offset"]
                            ].encode("utf8")
                        parts.append(part)
                    values[side] = b"".join(parts)
                if values["source"] != values["target"]:
                    raise ValueError("exact copy mapping content differs")
    if p["provenance_state"] == "complete":
        if p.get("provenance_universe", "canonical_output") != "canonical_output":
            raise ValueError("unsupported provenance universe")

        established: set[tuple[str, int, int]] = set()

        def rooted(representation: str, start: int, end: int, path: frozenset[str]) -> bool:
            key = (representation, start, end)
            if key in established:
                return True
            if start == end or reps[(representation,)]["kind"] == "original":
                return True
            if len(path) >= 64:
                return False
            covered = []
            starts, prefix, targets = target_index.get(representation, ([], [], []))
            for target in targets[bisect_right(prefix, start) : bisect_left(starts, end)]:
                if target["end_offset"] <= start:
                    continue
                mapping = mappings[(target["mapping_id"],)]
                if mapping["mapping_id"] in path or mapping["fidelity"] == "unknown":
                    return False
                if mapping["fidelity"] == "synthetic":
                    if adapter is None or "mapping/synthetic" not in adapter.capabilities:
                        return False
                else:
                    sources = mapping_endpoints[mapping["mapping_id"], "source"]
                    if not sources or any(
                        r.get("target_task_id") is not None
                        or not rooted(
                            r["representation_id"],
                            r["start_offset"],
                            r["end_offset"],
                            path | {mapping["mapping_id"]},
                        )
                        for r in sources
                    ):
                        return False
                covered.append(
                    (
                        max(start, target["start_offset"]) - start,
                        min(end, target["end_offset"]) - start,
                    )
                )
            valid = _covers(covered, end - start)
            if valid:
                established.add(key)
            return valid

        if any(
            rep["kind"] == "canonical"
            and not rooted(rep["representation_id"], 0, rep["extent_length"], frozenset())
            for rep in reps.values()
        ):
            raise ValueError(
                "complete provenance requires a qualified decoding/projection transform "
                "rooted in original bytes or admitted synthetic rules"
            )


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
    payload: Mapping[str, Any],
    original_bytes: bytes | bytearray | memoryview,
    *,
    context: PreparedParsingContext | None = None,
) -> PreparedParsingProduct:
    context = _trusted_parsing_context() if context is None else context
    context.execution.require_operation("prepare_parsing_product")
    original_bytes = bytes(original_bytes)
    value = context.boundary.validate_json("ParsingProduct", json.dumps(dict(payload))).model_dump(
        mode="json"
    )
    for key in COLLECTIONS:
        value.setdefault(key, [])
    value.setdefault("provenance_universe", "canonical_output")
    _validate_product(value, original_bytes, context)
    return PreparedParsingProduct(canonical_bytes(value), original_bytes, context.contract_digest)


def store_parsing_product(
    conn: Connection,
    *,
    task_id: int,
    attempt: int,
    holder: str,
    product: PreparedParsingProduct,
    context: PreparedParsingContext | None = None,
) -> str:
    """Publish only behind the same running-attempt custody as source completion."""
    from .contracts import require_database_operation

    context = parsing_context_for_task(conn, task_id, context)
    context.execution.require_operation("publish_parsing_product")
    if context.release_id is None:
        raise ValueError("publication requires the producing task's archived release")
    require_database_operation(conn, context.release_id, "publish_parsing_product")
    checked = prepare_parsing_product(product.values(), product.original, context=context)
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


def read_parsing_product(
    conn: Connection, *, task_id: int, context: PreparedParsingContext | None = None
) -> PreparedParsingProduct | None:
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
    context = parsing_context_for_task(conn, task_id, context)
    context.execution.require_operation("read_parsing_product")
    conn.execute(
        text("SELECT ops.require_parsing_product(:task,:contract)"),
        {"task": task_id, "contract": context.contract_digest},
    )
    if row["contract_digest"] != context.contract_digest:
        raise ParsingProductUnavailable("retained parsing contract is unsupported by this reader")
    result = prepare_parsing_product(
        json.loads(bytes(row["payload"])), bytes(row["original"]), context=context
    )
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
