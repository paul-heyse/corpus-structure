"""Pinned current result reads and exact detached replay over native demand custody.

The native reader alone acquires authorization, visibility and sorted trust locks.
This owner projects retained selections; it never consults a latest run, schedules
work, copies task identities or changes the producing episode of a reused value.
"""
from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from hashlib import sha256
from typing import TYPE_CHECKING, Any, Literal, cast

from .data_operation_identity import (
    body_identity, contextual_product_identity, decode_semantic_value, semantic_value,
)
from .data_operation_json import json_bytes, wire_json_loads
from .data_operation_model import SubjectContext

if TYPE_CHECKING:
    from ._data_operation_wire import WireReadDemandResultRequest


def _read_request(value):
    from .data_operation_wire import validate_native_wire
    # This is the explicit public ingress: the captured field correspondence gives
    # demand/read strings their nominal request roles after runtime Draft7 admission.
    return cast("WireReadDemandResultRequest", validate_native_wire("read_demand_result", "input", value))


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
                                            analyzed_scope=output["analyzed_scope"], body=body, meaning_body=output["body"]))
                packets = body.get("members", ()) if isinstance(body, dict) else ()
                projected = [packet for packet in packets if output["member_id"] is None or packet["member_id"] == output["member_id"]]
                if output["member_id"] is not None and len(projected) != 1:
                    raise ValueError("selected output member is absent from its canonical product")
                occurrences.extend(dict(header, member_id=packet["member_id"], kind_contract=packet["kind_contract"],
                                        **packet["context"], body=packet["body"], meaning_body=semantic_value(packet["body"])) for packet in projected)
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
                       view: Literal["frontier", "products", "support"] = "products", scope: Mapping[str, Any] | None = None) -> DemandResult:
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
    native = DataOperationStorage(connection).read_demand_result(_read_request(request))
    if native["project_id"] != project_id:
        raise ValueError("demand belongs to another project")
    page = DemandResult(json_bytes(native), json_bytes(request))
    if cut is not None and page.cut.content != cut.content:
        raise ValueError("continuation differs from the pinned cut selection")
    return page


def stream_demand_result(connection, demand_id: str, *, project_id: str, limit=100,
                         max_bytes=8 * 1024 * 1024, scope: Mapping[str, Any] | None = None) -> Iterator[DemandResult]:
    """Same-session bounded pages retain the acquisition and its transaction locks."""
    continuation, cut = None, None
    while True:
        page = read_demand_result(connection, demand_id, project_id=project_id,
                                  continuation=continuation, cut=cut, limit=limit, max_bytes=max_bytes, scope=scope)
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
        native = DataOperationStorage(connection).read_demand_result(_read_request(request))
        if CutSelection.from_native(native).content != cut.content:
            raise ValueError("support continuation differs from its selected result")
        support = native["support_page"]
        if not isinstance(support, dict):
            raise ValueError("native support projection is unavailable")
        yield from (dict(record) for record in support["records"])
        if support["complete"]:
            break
        if not support["after"] or support["after"] == request.get("support_after"):
            raise ValueError("native support cursor did not advance")
        request["support_after"] = support["after"]


from contextlib import contextmanager


@contextmanager
def selected_record_index(connection, demand_id, *, project_id, scope, read_id=None,
                          expected_cut=None, max_bytes=8388608, page_rows=100):
    """Keep one pinned native acquisition and its complete temporary witness index."""
    from pathlib import Path
    from tempfile import TemporaryDirectory
    from .data_operation_read_index import SelectedRecordIndex
    continuation = None if read_id is None else dict(demand_id=demand_id, read_id=read_id, scope=dict(scope), view="products")
    cut = None
    with TemporaryDirectory(prefix="selected-read-") as scratch:
        index = SelectedRecordIndex(Path(scratch) / "support.sqlite")
        try:
            while True:
                page = read_demand_result(connection, demand_id, project_id=project_id,
                    continuation=continuation, cut=cut, scope=scope, limit=page_rows, max_bytes=max_bytes)
                cut = page.cut
                if expected_cut is not None and cut.identity != expected_cut:
                    raise ValueError("selected resource belongs to another cut/trust assessment")
                for record in stream_selected_support(connection, page):
                    index.append(json_bytes(record), allow_equal=True)
                continuation = page.continuation
                if continuation is None:
                    break
            yield cut, index
        finally:
            index.close()


def verify_detached_result(record: Mapping[str, Any], *, records=(), index=None, wire_schema=None, kinds=None, definitions=None, runtimes=None, source_artifacts=None, validate_closure=True) -> DemandResult:
    """Verify links and exact value identities against an explicit captured closure.

    Export verification authenticates the captured contracts/runtime and trusted
    manifest first. A page alone establishes neither authenticity nor current trust.
    """
    from jsonschema import Draft7Validator
    from .data_operation_wire import validate_native_wire, validate_wire_schema
    admitted = validate_native_wire("read_demand_result", "output", dict(record)) if wire_schema is None else validate_wire_schema(wire_schema, dict(record))
    page = DemandResult(json_bytes(admitted))
    closure = {}
    if index is None:
        for row in records:
            relation = row["relation"]
            key = row["key"]
            previous = closure.setdefault(relation, {}).get(key)
            if previous is not None and previous != row["record"]:
                raise ValueError("detached support key has conflicting records")
            closure[relation][key] = row["record"]
    def rows(name):
        return closure.get(name, {}).values() if index is None else index.rows(name)
    def rows_for(name, **fields):
        return (row for row in rows(name) if all(row[key] == value for key, value in fields.items())) if index is None else index.rows_for(name, **fields)

    def row_map(name, *fields):
        if index is not None:
            return index.mapping(name, fields)
        return {(row[fields[0]] if len(fields) == 1 else tuple(row[field] for field in fields)): row for row in rows(name)}
    actual_kinds = row_map("sem.data_kind_contract", "kind_contract")
    if kinds is not None and any(kinds.get(key) != value for key, value in actual_kinds.items()):
        raise ValueError("detached kind differs from its captured release contract")
    products = row_map("kb.data_product", "id")
    for product in products.values() if validate_closure else ():
        kind = actual_kinds[product["kind_contract"]]
        decoded = decode_semantic_value(product["canonical_body"])
        Draft7Validator(kind["meaning_schema"]).validate(product["canonical_body"])
        Draft7Validator(kind["body_schema"]).validate(decoded)
        body = body_identity(decoded).key
        context = SubjectContext(product["project_id"], product["subject"], product["original_source"], json_bytes(product["analyzed_scope"]))
        if body != product["body_digest"] or contextual_product_identity(kind=product["kind_contract"], context=context, body=body).key != product["id"]:
            raise ValueError("detached product differs from its semantic identity")
    members = row_map("kb.data_product_member", "product_id", "member_id")
    for member in members.values() if validate_closure else ():
        product = products[member["product_id"]]
        kind = actual_kinds[member["kind_contract"]]
        Draft7Validator(kind["meaning_schema"]).validate(member["body"])
        decoded = decode_semantic_value(member["body"])
        Draft7Validator(kind["body_schema"]).validate(decoded)
        packets = decode_semantic_value(product["canonical_body"]).get("members", ())
        if not any(packet["member_id"] == member["member_id"] and packet["kind_contract"] == member["kind_contract"] and packet["body"] == decoded and packet["context"] == dict(subject=member["subject"], original_source=member["original_source"], analyzed_scope=member["analyzed_scope"]) for packet in packets):
            raise ValueError("detached member differs from its canonical container")
    actual_definitions = row_map("sem.data_operation_definition", "release_id", "operation_id")
    if definitions is not None:
        from .metadata import table
        stored_fields = tuple(table("sem.data_operation_definition").c.keys())
        # The archive additionally carries definition/eligibility/binding facts.
        # Compare exactly the native row projection, not that larger artifact.
        for key, value in actual_definitions.items():
            expected = definitions.get(key)
            if expected is None or value != {name: expected[name] for name in stored_fields}:
                raise ValueError("detached operation differs from its captured release contract")
    requests = row_map("ops.data_request", "id")
    episodes = row_map("ops.data_derivation", "id")
    if validate_closure:
        for episode in episodes.values():
            if runtimes is not None and (episode["release_id"], episode["runtime_id"]) not in runtimes:
                raise ValueError("detached producing episode lacks its exact runtime archive")
            request = requests[episode["request_id"]]
            definition = actual_definitions[episode["release_id"], request["operation_id"]]
            if episode["recipe"] != request["recipe"] or definition["recipe"] != episode["recipe"]:
                raise ValueError("detached producing recipe differs from captured definition")
    uses = row_map("ops.demand_use", "id")
    originals = row_map("ops.original_source_admission", "id")
    output_edges = row_map("ops.data_derivation_output", "derivation_id", "role", "position")
    populations = row_map("ops.data_population", "id")
    intents = row_map("ops.data_completion_intent", "id")
    receipts = row_map("ops.data_publication_receipt", "derivation_id")
    supports = row_map("ops.data_derivation_support", "derivation_id", "occurrence")
    original_supports = row_map("ops.data_derivation_original_support", "derivation_id", "occurrence")

    def required(mapping, key, label):
        value = mapping.get(key)
        if value is None:
            raise ValueError("detached " + label + " is missing from its support closure")
        return value

    def support_reference(reference):
        if reference.get("kind", "computation") in {"original-source", "authored"}:
            original = required(originals, reference["admission_id"], "original support")
            if original["source_reference"] != reference["source_reference"]:
                raise ValueError("detached original support names another source")
        else:
            episode = required(episodes, reference["derivation_id"], "support episode")
            if reference.get("admission_use_id") is not None:
                selected = required(uses, reference["admission_use_id"], "support use")
                if selected["derivation_id"] != episode["id"]:
                    raise ValueError("detached support use names another producing episode")

    def binding_endpoints(binding):
        for selected_input in binding.get("inputs", ()):
            required(products, selected_input["product_id"], "selected input product")
            if selected_input.get("member_id") is not None:
                required(members, (selected_input["product_id"], selected_input["member_id"]), "selected input member")
        for reference in binding.get("support", ()):
            support_reference(reference)
        for reference in binding.get("populations", ()):
            required(populations, reference["population_id"], "selected population")

    if validate_closure:
        from collections import Counter
        for episode in episodes.values():
            request = required(requests, episode["request_id"], "producing request")
            intent = required(intents, episode["intent_id"], "completion intent")
            receipt = required(receipts, episode["id"], "publication receipt")
            if receipt["intent_id"] != intent["id"] or any(intent[name] != episode[name] for name in ("request_id", "generation", "runtime_id", "producer_task_id", "producer_attempt")):
                raise ValueError("detached producing episode differs from its completion/publication custody")
            payload = intent["payload"]
            definition = actual_definitions[episode["release_id"], request["operation_id"]]
            collections = {role["name"]: role["collection"] for role in definition.get("input_roles", ())}
            def input_signature(row):
                return (row["role"], row["product_id"], row.get("member_id"), row["multiplicity"], row["position"] if collections.get(row["role"]) == "sequence" else None)
            if Counter(map(input_signature, payload["inputs"])) != Counter(map(input_signature, rows_for("ops.data_derivation_input", derivation_id=episode["id"]))):
                raise ValueError("detached input roles differ from the sealed completion")
            expected_outputs = set()
            for output in payload["outputs"]:
                edge_key = (episode["id"], output["role"], output["position"])
                edge = required(output_edges, edge_key, "producing output edge")
                expected_outputs.add(edge_key)
                produced = output["product"]
                context = SubjectContext(request["project_id"], request["subject"], request["original_source"], json_bytes(request["analyzed_scope"]))
                product_key = contextual_product_identity(kind=produced["kind_contract"], context=context, body=body_identity(decode_semantic_value(produced["body"])).key).key
                if edge["product_id"] != product_key or edge["member_id"] != output.get("member_id") or edge["multiplicity"] != output["multiplicity"]:
                    raise ValueError("detached output role differs from the sealed completion")
            actual_outputs = {(row["derivation_id"], row["role"], row["position"]) for row in rows_for("ops.data_derivation_output", derivation_id=episode["id"])}
            if actual_outputs != expected_outputs:
                raise ValueError("detached output inventory differs from the sealed completion")
            for occurrence, reference in enumerate(payload["support"]):
                support_reference(reference)
                original = reference.get("kind", "computation") in {"original-source", "authored"}
                edge = required(original_supports if original else supports, (episode["id"], occurrence), "producing support edge")
                expected = dict(role=reference.get("role", "support"), position=reference.get("position", occurrence))
                expected.update({name: reference.get(name) for name in (("admission_id", "source_reference") if original else ("admission_use_id",))})
                if not original:
                    expected["support_derivation_id"] = reference["derivation_id"]
                if any(edge[name] != value for name, value in expected.items()):
                    raise ValueError("detached support edge differs from the sealed completion")
            if sum(1 for _ in rows_for("ops.data_derivation_support", derivation_id=episode["id"])) + sum(1 for _ in rows_for("ops.data_derivation_original_support", derivation_id=episode["id"])) != len(payload["support"]):
                raise ValueError("detached support closure inventory differs from the sealed completion")
    if validate_closure and source_artifacts is not None:
        for admission in originals.values():
            reference = admission["reference"]
            if reference.get("kind") == "original-document" and reference["content_hash"] not in source_artifacts:
                raise ValueError("detached selected original bytes are missing")
    if validate_closure:
        from .data_operation_identity import SemanticRequestKey
        for retained in uses.values():
            if retained["request_id"] is None:
                continue
            request = requests.get(retained["request_id"])
            if request is None:
                # An unsettled use has no producing episode. Its request is not
                # needed as semantic evidence, and its fate remains explicit.
                if retained["derivation_id"] is not None:
                    raise ValueError("settled use lacks its semantic request")
                binding_endpoints(retained["selection"])
                continue
            if retained["derivation_id"] is not None:
                episode = required(episodes, retained["derivation_id"], "selected producing episode")
                if episode["request_id"] != retained["request_id"]:
                    raise ValueError("detached selected episode names another semantic request")
            binding = retained["selection"]
            binding_endpoints(binding)
            expected = SemanticRequestKey(request["recipe"], request["subject"], decode_semantic_value(binding["request_inputs"]), decode_semantic_value(binding["parameters"]), binding["inference"], subject_context=SubjectContext(request["project_id"], request["subject"], request["original_source"], json_bytes(request["analyzed_scope"]))).identity.key
            if expected != request["request_key"]:
                raise ValueError("detached request differs from its exact selected meaning")
    for use in record["uses"]:
        retained = uses.get(use["use_id"])
        if retained is None or any(retained[key] != use[key] for key in ("obligation_id", "request_id", "derivation_id", "selection", "trust_snapshot")):
            raise ValueError("detached selected use differs from its retained episode binding")
        if use["derivation_id"] is None:
            if use["products"]:
                raise ValueError("detached unsettled use cannot supply produced outputs")
        else:
            required(episodes, use["derivation_id"], "selected producing episode")
        for product in use["products"]:
            edge = required(output_edges, (use["derivation_id"], product["role"], product["position"]), "selected output edge")
            if any(edge[name] != product[name] for name in ("product_id", "member_id", "multiplicity")):
                raise ValueError("detached selected output differs from its authentic role edge")
            actual = products.get(product["product_id"])
            if actual is None or ("body" in product and actual["canonical_body"] != product["body"]):
                raise ValueError("detached selected body differs from its support closure")
    if validate_closure:
        for population in populations.values():
            evidence = population["evidence"]
            if evidence.get("admission_use_id") is not None:
                selected = required(uses, evidence["admission_use_id"], "population producing use")
                if selected["derivation_id"] != evidence["derivation_id"] or selected["demand_id"] != population["demand_id"]:
                    raise ValueError("detached population producer differs from its selected use")
            parent = evidence.get("selection", {}).get("parent_population_id")
            if parent is not None:
                required(populations, parent, "parent population")
    from itertools import chain
    for edge in chain(rows("ops.data_derivation_input"), rows("ops.data_derivation_output")) if validate_closure else ():
        if edge["derivation_id"] not in episodes or edge["product_id"] not in products or (edge["member_id"] is not None and (edge["product_id"], edge["member_id"]) not in members):
            raise ValueError("detached role edge has an absent endpoint")
    for edge in rows("ops.data_derivation_support") if validate_closure else ():
        if edge["derivation_id"] not in episodes or edge["support_derivation_id"] not in episodes or (edge["admission_use_id"] is not None and edge["admission_use_id"] not in uses):
            raise ValueError("detached support closure is incomplete")
    for edge in rows("ops.data_derivation_original_support") if validate_closure else ():
        if edge["derivation_id"] not in episodes or edge["admission_id"] not in originals:
            raise ValueError("detached original support closure is incomplete")
    return page
