"""Native task-owned external work: immutable packets and receipt-bearing results.

A caller supplies actor/model assertions, never execution receipts or native fences
manufactured from run/task aliases. PostgreSQL owns every admission and publication.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import Engine
from sqlalchemy.exc import DBAPIError

from .data_operation_admission import bound_data_operation_model
from .data_operation_identity import semantic_value
from .data_operation_json import json_bytes, wire_json_loads
from .data_operation_model import EffectiveDataOperationModel
from .data_operation_ports import PortRefusal, project_product_members
from .data_operation_storage import DataOperationStorage
from .data_operation_wire import validate_wire_schema
from .releases import load_release_inputs

_FENCE = ("request_id", "generation", "task_id", "attempt", "holder")


def _fence(claim: dict) -> dict:
    """Copy only the native authority's actual complete returned attempt fence."""
    return {name: claim[name] for name in _FENCE}


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

    def _invoke(self, operation: str, payload: dict, *, replay: bool = False) -> dict:
        try:
            with self.engine.begin() as connection:
                return DataOperationStorage(connection).invoke(operation, payload)
        except DBAPIError as error:
            if not replay or not error.connection_invalidated:
                raise
            # Exact same immutable request only. A second uncertainty is surfaced
            # with packet/intent identity; no fresh external computation is invoked.
            with self.engine.begin() as connection:
                return DataOperationStorage(connection).invoke(operation, payload)

    def queue(self, *, limit: int = 1) -> dict:
        return self._invoke(
            "read_external_data_queue",
            {
                "project_id": self.project_id,
                **({"demand_id": self.demand_id} if self.demand_id else {}),
                "limit": limit,
            },
        )

    def claim(self, packet_id: str, *, lease_seconds: int = 300) -> dict:
        # Resolve the exact queue head in this session's scope; no caller task alias.
        # Explicit packet claim still authenticates current trust and task under lock.
        return self._invoke(
            "claim_external_data_packet",
            {
                "packet_id": packet_id,
                "project_id": self.project_id,
                **({"demand_id": self.demand_id} if self.demand_id else {}),
                "holder": self.holder,
                "lease_seconds": lease_seconds,
            },
        )

    def renew(self, claim: dict, *, lease_seconds: int = 300) -> dict:
        return self._invoke("renew_data_request", {**_fence(claim), "lease_seconds": lease_seconds})

    def read(self, packet_id: str, claim: dict) -> dict:
        read = self._invoke(
            "read_external_data_packet",
            {"packet_id": packet_id, **_fence(claim), "max_bytes": self.max_packet_bytes},
        )
        if read["packet"]["project_id"] != self.project_id:
            raise PortRefusal("external packet belongs to another project")
        return read

    def submit(
        self,
        packet_id: str,
        claim: dict,
        result: dict,
        *,
        actor_assertion: str,
        model_assertion: str | None,
    ) -> dict:
        read = self.read(packet_id, claim)
        packet = read["packet"]
        if packet["project_id"] != self.project_id:
            raise PortRefusal("external packet belongs to another project")
        with self.engine.begin() as connection:
            _, _, _, prepared = load_release_inputs(connection, packet["release_id"])
            model = bound_data_operation_model(prepared)
        port = ExternalResultPort(json_bytes(packet), model, self.max_reply_bytes)
        completion = port.completion(result)
        retained = self._invoke(
            "admit_external_data_result",
            {
                "packet_id": packet_id,
                **_fence(claim),
                "actor_assertion": actor_assertion,
                "model_assertion": model_assertion,
                "completion": completion,
            },
            replay=True,
        )
        try:
            publication = self._invoke(
                "publish_data_derivation",
                {**_fence(claim), "intent_id": retained["intent_id"]},
                replay=True,
            )
        except DBAPIError:
            inspected = self.inspect(packet_id)
            if inspected["state"] != "committed":
                raise
            return inspected
        return {
            "packet_id": packet_id,
            "receipt": retained["receipt"],
            "intent_id": retained["intent_id"],
            "publication": publication,
            "state": "committed",
        }

    def reconcile(self, packet_id: str, claim: dict) -> dict:
        """Publish an existing exact retained intent without asking the actor again."""
        inspected = self.inspect(packet_id)
        if inspected["state"] == "committed":
            return inspected
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
        self._invoke("adopt_data_completion_intent", payload, replay=True)
        self._invoke("publish_data_derivation", payload, replay=True)
        return self.inspect(packet_id)

    def inspect(self, packet_id: str) -> dict:
        return self._invoke("inspect_external_data_result", {"packet_id": packet_id})

    def release(self, packet_id: str, claim: dict, *, reason: str) -> dict:
        return self._invoke(
            "release_external_data_packet",
            {"packet_id": packet_id, **_fence(claim), "reason": reason},
            replay=True,
        )
