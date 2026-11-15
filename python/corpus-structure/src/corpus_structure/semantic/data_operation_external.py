"""Native task-owned external work: immutable packets and receipt-bearing results.

A caller supplies actor/model assertions, never execution receipts or native fences
manufactured from run/task aliases. PostgreSQL owns every admission and publication.
"""

from __future__ import annotations

from corpus_structure.semantic.identifiers import ProjectId

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, cast
from uuid import uuid4

from sqlalchemy import Engine
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic._data_operation_wire import WireAdoptDataCompletionIntentRequest, WireAttemptFence, WireClaimDataRequestResult, WireClaimExternalDataPacketRequest, WireCompletion, WireDemandId, WireExternalPacketId, WireInspectExternalDataResultResult, WirePublishDataDerivationRequest, WireReadExternalDataQueueRequest, WireReadExternalDataQueueResult, WireReleaseExternalDataPacketResult, WireRenewDataRequestResult, wire_attempt_fence

from .data_operation_admission import bound_data_operation_model
from .data_operation_identity import semantic_value
from .data_operation_json import json_bytes, wire_json_loads
from .data_operation_model import EffectiveDataOperationModel
from .data_operation_ports import PortRefusal, project_product_members
from .data_operation_storage import DataOperationStorage
from .data_operation_wire import validate_wire_schema
from .releases import load_release_inputs

_FENCE = ("request_id", "generation", "task_id", "attempt", "holder")


def _fence(claim: Mapping[str, Any]) -> WireAttemptFence:
    """Copy only the native authority's actual complete returned attempt fence."""
    return wire_attempt_fence(claim)


@dataclass(frozen=True)
class ExternalResultPort:
    """An actual native-read packet, frozen before caller-controlled result decoding."""

    packet: bytes
    model: EffectiveDataOperationModel
    max_reply_bytes: int

    def completion(self, result: dict) -> dict:
        if len(json_bytes(result)) > self.max_reply_bytes:
            raise PortRefusal("external result exceeds owned reply capacity")
        if not isinstance(result, dict) or set(result) != {"outcome", "outputs"}:
            raise PortRefusal("external result requires exactly outcome and outputs")
        packet = wire_json_loads(self.packet)
        operation = self.model.operation(packet["operation_id"])
        recipe = next(
            item.key
            for item in self.model.identities
            if item.owner == operation.semantic_id and item.domain == "recipe"
        )
        if operation.external is None or recipe != packet["recipe"]:
            raise PortRefusal("external result has no exact admitted protocol owner")
        if result["outcome"] not in packet["outcomes"]:
            raise PortRefusal("external outcome is outside the admitted protocol")
        if not isinstance(result["outputs"], list):
            raise PortRefusal("external outputs require a bounded role/body array")
        roles = {role["role"]: role for role in packet["result_contract"]}
        identities = {(item.owner, item.domain): item.key for item in self.model.identities}
        owners = {
            identities[role.kind, "kind"]: role.kind
            for role in operation.roles
            if role.direction == "output"
        }
        positions, outputs = {}, []
        for output in result["outputs"]:
            if not isinstance(output, dict) or set(output) != {"role", "body"}:
                raise PortRefusal("external output requires exactly role and body")
            if type(output["role"]) is not str:
                raise PortRefusal("external output role must be an exact declared string")
            role = roles.get(output["role"])
            if role is None:
                raise PortRefusal("external output names an undeclared role")
            body = validate_wire_schema(role["schema"], output["body"])
            position = positions.get(output["role"], 0)
            positions[output["role"]] = position + 1
            members = project_product_members(self.model, owners[role["kind_contract"]], body)
            outputs.append(
                {
                    "role": output["role"],
                    "position": position,
                    "multiplicity": 1,
                    "product": {
                        "kind_contract": role["kind_contract"],
                        "body": semantic_value(body),
                        "members": [wire_json_loads(member) for member in members],
                    },
                }
            )
        # Native retention independently enforces outcome-sensitive cardinality,
        # kind meaning/member schemas and exact input/support/output witnesses.
        completion = {
            "outcome": result["outcome"],
            "outputs": outputs,
            "inputs": packet["binding"]["inputs"],
            "support": packet["binding"]["support"],
            "implementation_revision": packet["implementation_revision"],
        }
        if len(json_bytes(completion)) > self.max_reply_bytes:
            raise PortRefusal("external completion exceeds owned draft capacity")
        return completion


class ExternalDataSession:
    """Short native transactions; no connection or remote process held during agent work."""

    def __init__(
        self,
        engine: Engine,
        project_id: str,
        *,
        demand_id: str | None = None,
        max_packet_bytes: int = 8 * 1024 * 1024,
        max_reply_bytes: int = 8 * 1024 * 1024,
    ):
        if not project_id or min(max_packet_bytes, max_reply_bytes) < 1:
            raise ValueError("external session requires project identity and positive byte bounds")
        self.engine, self.project_id, self.demand_id = engine, project_id, demand_id
        self.max_packet_bytes, self.max_reply_bytes = max_packet_bytes, max_reply_bytes
        self.holder = "external-owner:" + uuid4().hex

    def _invoke[T](self, invoke: Callable[[DataOperationStorage], T], *, replay: bool = False) -> T:
        try:
            with self.engine.begin() as connection:
                return invoke(DataOperationStorage(connection))
        except DBAPIError as error:
            if not replay or not error.connection_invalidated:
                raise
            # Exact same immutable request only. A second uncertainty is surfaced
            # with packet/intent identity; no fresh external computation is invoked.
            with self.engine.begin() as connection:
                return invoke(DataOperationStorage(connection))

    def queue(self, *, limit: int = 1) -> WireReadExternalDataQueueResult:
        payload: WireReadExternalDataQueueRequest = {
            "project_id": ProjectId(self.project_id),
            "limit": limit,
        }
        if self.demand_id:
            payload["demand_id"] = WireDemandId(self.demand_id)
        return self._invoke(lambda storage: storage.read_external_data_queue(payload))

    def claim(self, packet_id: str, *, lease_seconds: int = 300) -> WireClaimDataRequestResult:
        # Resolve the exact queue head in this session's scope; no caller task alias.
        # Explicit packet claim still authenticates current trust and task under lock.
        payload: WireClaimExternalDataPacketRequest = {
            "packet_id": WireExternalPacketId(packet_id),
            "project_id": ProjectId(self.project_id),
            "holder": self.holder,
            "lease_seconds": lease_seconds,
        }
        if self.demand_id:
            payload["demand_id"] = WireDemandId(self.demand_id)
        return self._invoke(lambda storage: storage.claim_external_data_packet(payload))

    def renew(
        self, claim: Mapping[str, Any], *, lease_seconds: int = 300
    ) -> WireRenewDataRequestResult:
        return self._invoke(
            lambda storage: storage.renew_data_request(
                {**_fence(claim), "lease_seconds": lease_seconds}
            )
        )

    def _read(self, packet_id: str, claim: Mapping[str, Any]) -> dict:
        read = self._invoke(
            lambda storage: storage.read_external_data_packet(
                {
                    "packet_id": WireExternalPacketId(packet_id),
                    **_fence(claim),
                    "max_bytes": self.max_packet_bytes,
                }
            )
        )
        packet = read["packet"]
        if not isinstance(packet, dict):
            raise PortRefusal("external packet must be an object")
        if packet["project_id"] != self.project_id:
            raise PortRefusal("external packet belongs to another project")
        return dict(read)

    def read(self, packet_id: str, claim: Mapping[str, Any]) -> dict:
        read = self._read(packet_id, claim)
        from .data_operation_identity import decode_semantic_value

        views = []
        for item in read["packet"]["inputs"]:
            value = decode_semantic_value(item["meaning"])
            if isinstance(value, dict) and value.get("version") == "external-extraction-input-1":
                from .external_extraction import external_extraction_prompt

                value = external_extraction_prompt(value)
            views.append(
                {
                    "role": item["role"],
                    "position": item["position"],
                    "multiplicity": item["multiplicity"],
                    "value": value,
                }
            )
        return {**read, "input_views": views}

    def submit(
        self,
        packet_id: str,
        claim: Mapping[str, Any],
        result: dict,
        *,
        actor_assertion: str,
        model_assertion: str | None,
    ) -> dict:
        read = self._read(packet_id, claim)
        packet = read["packet"]
        if packet["project_id"] != self.project_id:
            raise PortRefusal("external packet belongs to another project")
        with self.engine.begin() as connection:
            _, _, _, prepared = load_release_inputs(connection, packet["release_id"])
            model = bound_data_operation_model(prepared)
        port = ExternalResultPort(json_bytes(packet), model, self.max_reply_bytes)
        completion = port.completion(result)
        retained = self._invoke(
            lambda storage: storage.admit_external_data_result(
                {
                    "packet_id": WireExternalPacketId(packet_id),
                    **_fence(claim),
                    "actor_assertion": actor_assertion,
                    "model_assertion": model_assertion,
                    "completion": cast(WireCompletion, completion),
                }
            ),
            replay=True,
        )
        try:
            publication = self._invoke(
                lambda storage: storage.publish_data_derivation(
                    {**_fence(claim), "intent_id": retained["intent_id"]}
                ),
                replay=True,
            )
        except DBAPIError:
            inspected = self.inspect(packet_id)
            if inspected["state"] != "committed":
                raise
            return dict(inspected)
        return {
            "packet_id": WireExternalPacketId(packet_id),
            "receipt": retained["receipt"],
            "intent_id": retained["intent_id"],
            "publication": publication,
            "state": "committed",
        }

    def reconcile(self, packet_id: str, claim: Mapping[str, Any]) -> dict:
        """Publish an existing exact retained intent without asking the actor again."""
        inspected = self.inspect(packet_id)
        if inspected["state"] == "committed":
            return dict(inspected)
        receipt = inspected["receipt"]
        if (
            inspected["state"] != "retained"
            or receipt is None
            or any(receipt[name] != claim[name] for name in ("request_id", "generation", "task_id"))
        ):
            raise PortRefusal(
                "reconciliation requires this packet's retained native result and task"
            )
        payload = {**_fence(claim), "intent_id": inspected["intent_id"]}
        self._invoke(
            lambda storage: storage.adopt_data_completion_intent(
                cast(WireAdoptDataCompletionIntentRequest, payload)
            ),
            replay=True,
        )
        self._invoke(
            lambda storage: storage.publish_data_derivation(
                cast(WirePublishDataDerivationRequest, payload)
            ),
            replay=True,
        )
        return dict(self.inspect(packet_id))

    def inspect(self, packet_id: str) -> WireInspectExternalDataResultResult:
        return self._invoke(
            lambda storage: storage.inspect_external_data_result(
                {"packet_id": WireExternalPacketId(packet_id)}
            )
        )

    def located(
        self, demand_id: str, *, limit: int = 100, continuation: dict | None = None
    ) -> dict:
        """Read mechanically placed rich reports through the native pinned public result."""
        from .data_operation_identity import decode_semantic_value
        from .data_operation_service import read_data_demand
        from .external_extraction import located_external_batch

        if self.demand_id is not None and demand_id != self.demand_id:
            raise PortRefusal("located report demand is outside this session scope")
        with self.engine.begin() as connection:
            snapshot = read_data_demand(
                connection,
                demand_id,
                limit=limit,
                max_bytes=self.max_reply_bytes,
                view="products",
                continuation=continuation,
            )
            if snapshot["project_id"] != self.project_id:
                raise PortRefusal("located report demand belongs to another project")
            _, _, _, prepared = load_release_inputs(connection, snapshot["release_id"])
            model = bound_data_operation_model(prepared)
        kind = "https://corpus-structure.dev/semantic/data-operation-external-extraction/DdoLocatedExternalExtraction"
        contract = next(
            (item.key for item in model.identities if item.owner == kind and item.domain == "kind"),
            None,
        )
        if contract is None:
            raise PortRefusal("selected release has no rich external placement contract")
        reports = []
        for use in snapshot["uses"]:
            for product in use["products"]:
                if product["kind_contract"] != contract or product["body_state"] != "present":
                    continue
                value = decode_semantic_value(product["body"])
                stored, issues = located_external_batch(prepared, value)
                reports.append(
                    {
                        "use_id": use["use_id"],
                        "fate": use["fate"],
                        "product": product,
                        "standing": value["standing"],
                        "stored": stored.model_dump(mode="python", exclude_unset=True),
                        "issues": list(issues),
                    }
                )
        return {
            "demand_id": demand_id,
            "read_id": snapshot["read_id"],
            "trust_snapshot": snapshot["trust_snapshot"],
            "continuation": snapshot["continuation"],
            "reports": reports,
        }

    def release(
        self, packet_id: str, claim: Mapping[str, Any], *, reason: str
    ) -> WireReleaseExternalDataPacketResult:
        return self._invoke(
            lambda storage: storage.release_external_data_packet(
                {"packet_id": WireExternalPacketId(packet_id), **_fence(claim), "reason": reason}
            ),
            replay=True,
        )
