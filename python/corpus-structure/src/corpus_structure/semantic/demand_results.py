"""Pinned current result reads and exact detached replay over native demand custody.

The native reader alone acquires authorization, visibility and sorted trust locks.
This owner projects retained selections; it never consults a latest run, schedules
work, copies task identities or changes the producing episode of a reused value.
"""
from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Literal

from .data_operation_identity import (
    body_identity, contextual_product_identity, decode_semantic_value,
)
from .data_operation_json import json_bytes, wire_json_loads
from .data_operation_model import SubjectContext

_PIN_FIELDS = ("demand_id", "project_id", "release_id", "runtime_id", "selection", "trust_snapshot", "read_id", "read_snapshot", "frontier_at", "scope")


@dataclass(frozen=True)
class CutSelection:
    """Exact interpreted selection and native visibility/current trust boundary."""
    content: bytes

    def __post_init__(self):
        record = self.record
        if set(record) != set(_PIN_FIELDS) or any(not record[key] for key in ("demand_id", "project_id", "release_id", "runtime_id", "read_id", "read_snapshot", "frontier_at")):
            raise ValueError("cut selection requires every explicit native interpretation pin")

    @property
    def record(self) -> dict[str, Any]:
        return wire_json_loads(self.content)

    @property
    def identity(self) -> str:
        return "cut-selection:" + sha256(self.content).hexdigest()

    @classmethod
    def from_native(cls, page: Mapping[str, Any]) -> CutSelection:
        return cls(json_bytes({key: page[key] for key in _PIN_FIELDS}))


@dataclass(frozen=True)
class DemandResult:
    """A bounded native page; immutable bytes own all nested values."""
    content: bytes
    request: bytes = b"{}"

    @property
    def record(self) -> dict[str, Any]:
        return wire_json_loads(self.content)

    @property
    def cut(self) -> CutSelection:
        return CutSelection.from_native(self.record)

    @property
    def continuation(self) -> dict[str, Any] | None:
        return self.record["continuation"]

    def members(self) -> tuple[dict[str, Any], ...]:
        """Project actual selected packets without opening any other product body."""
        page = self.record
        if page["view"] != "products":
            raise ValueError("member reads require a body-bearing selected result")
        occurrences = []
        for use in page["uses"]:
            if use["fate"] != "fulfilled":
                continue
            for output in use["products"]:
                body = decode_semantic_value(output["body"])
                header = dict(use_id=use["use_id"], derivation_id=use["derivation_id"],
                              product_id=output["product_id"], role=output["role"],
                              position=output["position"], multiplicity=output["multiplicity"])
                if output["member_id"] is None:
                    occurrences.append(dict(header, member_id=None, kind_contract=output["kind_contract"],
                                            subject=output["subject"], original_source=output["original_source"],
                                            analyzed_scope=output["analyzed_scope"], body=body))
                packets = body.get("members", ()) if isinstance(body, dict) else ()
                projected = [packet for packet in packets if output["member_id"] is None or packet["member_id"] == output["member_id"]]
                if output["member_id"] is not None and len(projected) != 1:
                    raise ValueError("selected output member is absent from its canonical product")
                occurrences.extend(dict(header, member_id=packet["member_id"], kind_contract=packet["kind_contract"],
                                        **packet["context"], body=packet["body"]) for packet in projected)
        return tuple(occurrences)

    def report(self) -> dict[str, Any]:
        page = self.record
        return dict(version="demand-result-v1", cut_id=self.cut.identity, cut=self.cut.record,
                    complete=page["continuation"] is None, state=page.get("state", "active"),
                    obligations=page["obligations"], uses=page["uses"],
                    populations=page["populations"], original_source_admissions=page.get("original_source_admissions", []),
                    attempt_failures=page.get("attempt_failures", []),
                    support_page=page.get("support_page"), continuation=page["continuation"])


def read_demand_result(connection, demand_id: str, *, project_id: str, continuation=None,
                       cut: CutSelection | None = None, limit: int = 100,
                       max_bytes: int = 8 * 1024 * 1024,
                       view: Literal["frontier", "products", "support"] = "products", scope: Mapping[str, str] | None = None) -> DemandResult:
    """Acquire or continue one explicit target, with no default project or run lookup."""
    from .data_operation_storage import DataOperationStorage
    if not demand_id or not project_id:
        raise ValueError("current result reads require explicit demand and project")
    request = dict(continuation or {"demand_id": demand_id})
    if request.get("demand_id") != demand_id:
        raise ValueError("continuation belongs to another demand")
    if continuation is not None and request.get("view") != view:
        raise ValueError("continuation belongs to another result projection")
    if continuation is not None and scope is not None and request.get("scope", {}) != dict(scope):
        raise ValueError("continuation belongs to another examined scope")
    request.update(limit=limit, max_bytes=max_bytes, view=view)
    if continuation is None:
        request["scope"] = dict(scope or {})
    # Generated named transport validates the current Draft7 ingress and exact JSON.
    native = DataOperationStorage(connection).read_demand_result(request)
    if native["project_id"] != project_id:
        raise ValueError("demand belongs to another project")
    page = DemandResult(json_bytes(native), json_bytes(request))
    if cut is not None and page.cut.content != cut.content:
        raise ValueError("continuation differs from the pinned cut selection")
    return page


def stream_demand_result(connection, demand_id: str, *, project_id: str, limit=100,
                         max_bytes=8 * 1024 * 1024) -> Iterator[DemandResult]:
    """Same-session bounded pages retain the acquisition and its transaction locks."""
    continuation, cut = None, None
    while True:
        page = read_demand_result(connection, demand_id, project_id=project_id,
                                  continuation=continuation, cut=cut, limit=limit, max_bytes=max_bytes)
        cut = page.cut
        yield page
        continuation = page.continuation
        if continuation is None:
            break


def stream_selected_support(connection, page: DemandResult) -> Iterator[dict[str, Any]]:
    """Read a page's full required closure in bounded native pages on its session."""
    from .data_operation_storage import DataOperationStorage
    cut = page.cut
    request = {key: value for key, value in cut.record.items() if key not in {"project_id", "release_id", "runtime_id"}}
    original_request = wire_json_loads(page.request)
    for key in ("after", "limit", "max_bytes"):
        if key in original_request:
            request[key] = original_request[key]
    request["view"] = "support"
    while True:
        native = DataOperationStorage(connection).read_demand_result(request)
        if CutSelection.from_native(native).content != cut.content:
            raise ValueError("support continuation differs from its selected result")
        support = native["support_page"]
        if not isinstance(support, dict):
            raise ValueError("native support projection is unavailable")
        yield from support["records"]
        if support["complete"]:
            break
        if not support["after"] or support["after"] == request.get("support_after"):
            raise ValueError("native support cursor did not advance")
        request["support_after"] = support["after"]


def verify_detached_result(record: Mapping[str, Any], *, records, wire_schema=None, kinds=None) -> DemandResult:
    """Verify links and exact value identities against an explicit captured closure.

    Export verification authenticates the captured contracts/runtime and trusted
    manifest first. A page alone establishes neither authenticity nor current trust.
    """
    from jsonschema import Draft7Validator
    from .data_operation_wire import validate_native_wire, validate_wire_schema
    admitted = validate_native_wire("read_demand_result", "output", dict(record)) if wire_schema is None else validate_wire_schema(wire_schema, dict(record))
    page = DemandResult(json_bytes(admitted))
    closure = {}
    for row in records:
        relation = row["relation"]
        key = row["key"]
        previous = closure.setdefault(relation, {}).get(key)
        if previous is not None and previous != row["record"]:
            raise ValueError("detached support key has conflicting records")
        closure[relation][key] = row["record"]
    def rows(name):
        return tuple(closure.get(name, {}).values())
    actual_kinds = {item["kind_contract"]: item for item in rows("sem.data_kind_contract")}
    if kinds is not None and any(kinds.get(key) != value for key, value in actual_kinds.items()):
        raise ValueError("detached kind differs from its captured release contract")
    products = {item["id"]: item for item in rows("kb.data_product")}
    for product in products.values():
        kind = actual_kinds[product["kind_contract"]]
        decoded = decode_semantic_value(product["canonical_body"])
        Draft7Validator(kind["meaning_schema"]).validate(product["canonical_body"])
        Draft7Validator(kind["body_schema"]).validate(decoded)
        body = body_identity(decoded).key
        context = SubjectContext(product["project_id"], product["subject"], product["original_source"], json_bytes(product["analyzed_scope"]))
        if body != product["body_digest"] or contextual_product_identity(kind=product["kind_contract"], context=context, body=body).key != product["id"]:
            raise ValueError("detached product differs from its semantic identity")
    members = {(row["product_id"], row["member_id"]): row for row in rows("kb.data_product_member")}
    for member in members.values():
        product = products[member["product_id"]]
        kind = actual_kinds[member["kind_contract"]]
        Draft7Validator(kind["meaning_schema"]).validate(member["body"])
        decoded = decode_semantic_value(member["body"])
        Draft7Validator(kind["body_schema"]).validate(decoded)
        packets = decode_semantic_value(product["canonical_body"]).get("members", ())
        if not any(packet["member_id"] == member["member_id"] and packet["kind_contract"] == member["kind_contract"] and packet["body"] == decoded and packet["context"] == dict(subject=member["subject"], original_source=member["original_source"], analyzed_scope=member["analyzed_scope"]) for packet in packets):
            raise ValueError("detached member differs from its canonical container")
    episodes = {row["id"]: row for row in rows("ops.data_derivation")}
    uses = {row["id"]: row for row in rows("ops.demand_use")}
    originals = {row["id"]: row for row in rows("ops.original_source_admission")}
    for use in record["uses"]:
        retained = uses.get(use["use_id"])
        if retained is None or any(retained[key] != use[key] for key in ("obligation_id", "request_id", "derivation_id", "selection", "trust_snapshot")):
            raise ValueError("detached selected use differs from its retained episode binding")
        for product in use["products"]:
            actual = products.get(product["product_id"])
            if actual is None or ("body" in product and actual["canonical_body"] != product["body"]):
                raise ValueError("detached selected body differs from its support closure")
    for edge in (*rows("ops.data_derivation_input"), *rows("ops.data_derivation_output")):
        if edge["derivation_id"] not in episodes or edge["product_id"] not in products or (edge["member_id"] is not None and (edge["product_id"], edge["member_id"]) not in members):
            raise ValueError("detached role edge has an absent endpoint")
    for edge in rows("ops.data_derivation_support"):
        if edge["derivation_id"] not in episodes or edge["support_derivation_id"] not in episodes or (edge["admission_use_id"] is not None and edge["admission_use_id"] not in uses):
            raise ValueError("detached support closure is incomplete")
    for edge in rows("ops.data_derivation_original_support"):
        if edge["derivation_id"] not in episodes or edge["admission_id"] not in originals:
            raise ValueError("detached original support closure is incomplete")
    return page
