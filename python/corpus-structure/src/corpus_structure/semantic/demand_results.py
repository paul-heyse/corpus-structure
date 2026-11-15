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

    @property
    def record(self) -> dict[str, Any]:
        return wire_json_loads(self.content)

    @property
    def cut(self) -> CutSelection:
        return CutSelection.from_native(self.record)

    @property
    def continuation(self) -> dict[str, Any] | None:
        return self.record["continuation"]

    def members(self, *, include_support: bool = False) -> tuple[dict[str, Any], ...]:
        """Retain nominal member references, context and authentic episode/use pins."""
        page = self.record
        closure = page.get("support_closure")
        if page["view"] != "products" or not isinstance(closure, dict):
            raise ValueError("member reads require a body-bearing selected result")
        kinds = {item["kind_contract"]: item["kind"] for item in closure["kinds"]}
        member_rows = {(item["product_id"], item["member_id"]): item for item in closure["members"]}
        products = {item["id"]: item for item in closure["products"]}
        occurrences = []
        uses = closure["uses"] if include_support else page["uses"]
        for use in uses:
            if use.get("fate") != "fulfilled":
                continue
            for output in closure["outputs"]:
                if output["derivation_id"] != use["derivation_id"]:
                    continue
                product_id = output["product_id"]
                selected_member = output["member_id"]
                projected = [row for (product, member), row in member_rows.items() if product == product_id and (selected_member is None or member == selected_member)]
                if selected_member is None:
                    projected.insert(0, dict(products[product_id], product_id=product_id, member_id=None, body=products[product_id]["canonical_body"]))
                for row in projected:
                    occurrences.append(dict(
                        product_id=product_id, member_id=row["member_id"], kind_contract=row["kind_contract"], kind=kinds[row["kind_contract"]],
                        subject=row["subject"], original_source=row["original_source"], analyzed_scope=row["analyzed_scope"],
                        body=decode_semantic_value(row["body"]), meaning_body=row["body"],
                        use_id=use["use_id"] if "use_id" in use else use["id"], derivation_id=use["derivation_id"],
                        role=output["role"], position=output["position"], multiplicity=output["multiplicity"],
                    ))
        for admission in page.get("original_source_admissions", ()):
            product = products.get(admission["product_id"])
            if product is not None:
                occurrences.append(dict(
                    product_id=product["id"], member_id=None, kind_contract=product["kind_contract"], kind=kinds[product["kind_contract"]],
                    subject=admission["subject"], original_source=admission["original_source"], analyzed_scope=admission["analyzed_scope"],
                    body=decode_semantic_value(product["canonical_body"]), meaning_body=product["canonical_body"],
                    admission_id=admission["admission_id"], source_reference=admission["source_reference"],
                ))
        return tuple(occurrences)

    def report(self) -> dict[str, Any]:
        page = self.record
        return dict(version="demand-result-v1", cut_id=self.cut.identity, cut=self.cut.record,
                    complete=page["continuation"] is None, state=page.get("state", "active"),
                    obligations=page["obligations"], uses=page["uses"],
                    populations=page["populations"], original_source_admissions=page.get("original_source_admissions", []),
                    attempt_failures=page.get("attempt_failures", []),
                    support_closure=page.get("support_closure"), continuation=page["continuation"])


def read_demand_result(connection, demand_id: str, *, project_id: str, continuation=None,
                       cut: CutSelection | None = None, limit: int = 100,
                       max_bytes: int = 8 * 1024 * 1024,
                       view: Literal["frontier", "products"] = "products", scope: Mapping[str, str] | None = None) -> DemandResult:
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
    page = DemandResult(json_bytes(native))
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


def verify_detached_result(record: Mapping[str, Any]) -> DemandResult:
    """Verify exact product identities and closed selected links without inference.

    This establishes internal integrity against the captured pins, not independent
    authenticity or present trust. Current trust requires native reacquisition.
    """
    from jsonschema import Draft7Validator
    from .data_operation_wire import validate_native_wire
    page = DemandResult(json_bytes(validate_native_wire("read_demand_result", "output", dict(record))))
    closure = record.get("support_closure")
    if record["view"] != "products" or not isinstance(closure, dict):
        raise ValueError("detached result requires complete selected bodies and support")
    kinds = {item["kind_contract"]: item for item in closure["kinds"]}
    products = {item["id"]: item for item in closure["products"]}
    if len(products) != len(closure["products"]) or len(kinds) != len(closure["kinds"]):
        raise ValueError("duplicate detached product or kind")
    for product in products.values():
        kind = kinds[product["kind_contract"]]
        decoded = decode_semantic_value(product["canonical_body"])
        Draft7Validator(kind["meaning_schema"]).validate(product["canonical_body"])
        Draft7Validator(kind["body_schema"]).validate(decoded)
        body = body_identity(decoded).key
        context = SubjectContext(product["project_id"], product["subject"], product["original_source"], json_bytes(product["analyzed_scope"]))
        if body != product["body_digest"] or contextual_product_identity(kind=product["kind_contract"], context=context, body=body).key != product["id"]:
            raise ValueError("detached product differs from its semantic identity")
    members = {(row["product_id"], row["member_id"]): row for row in closure["members"]}
    for member in members.values():
        product = products[member["product_id"]]
        kind = kinds[member["kind_contract"]]
        Draft7Validator(kind["meaning_schema"]).validate(member["body"])
        decoded = decode_semantic_value(member["body"])
        Draft7Validator(kind["body_schema"]).validate(decoded)
        packets = decode_semantic_value(product["canonical_body"]).get("members", ())
        if not any(packet["member_id"] == member["member_id"] and packet["kind_contract"] == member["kind_contract"] and packet["body"] == decoded and packet["context"] == dict(subject=member["subject"], original_source=member["original_source"], analyzed_scope=member["analyzed_scope"]) for packet in packets):
            raise ValueError("detached member differs from its canonical container")
    episodes = {row["id"]: row for row in closure["episodes"]}
    uses = {row["id"]: row for row in closure["uses"]}
    originals = {row["id"]: row for row in closure["original_admissions"]}
    for use in record["uses"]:
        retained = uses.get(use["use_id"])
        if retained is None or any(retained[key] != use[key] for key in ("obligation_id", "request_id", "derivation_id", "selection", "trust_snapshot")):
            raise ValueError("detached selected use differs from its retained episode binding")
    for edge in (*closure["inputs"], *closure["outputs"]):
        if edge["derivation_id"] not in episodes or edge["product_id"] not in products or (edge["member_id"] is not None and (edge["product_id"], edge["member_id"]) not in members):
            raise ValueError("detached role edge has an absent endpoint")
    for edge in closure["support"]:
        if edge["derivation_id"] not in episodes or edge["support_derivation_id"] not in episodes or (edge["admission_use_id"] is not None and edge["admission_use_id"] not in uses):
            raise ValueError("detached support closure is incomplete")
    for edge in closure["original_support"]:
        if edge["derivation_id"] not in episodes or edge["admission_id"] not in originals:
            raise ValueError("detached original support closure is incomplete")
    return page
