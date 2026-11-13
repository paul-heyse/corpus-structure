"""Execute admitted native demands without stage-run or method-name policy.

Semantic readiness and effect permission stay with the native bindings. This owner
connects pure Python capabilities to existing fenced task custody and short native
transactions; provider/prepared capabilities use their separately admitted owners.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from sqlalchemy import Connection, Engine, select

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.core.work import PreparedWork, ReadyGroup, drive_prepared_work
from corpus_structure.semantic.claim_lifetime import OwnedClaim, maintained_claims
from corpus_structure.semantic.cpu_execution import OwnedByteBudget
from corpus_structure.semantic.data_operation_admission import (
    acquire_prepared_execution,
    acquire_python_execution,
    bound_data_operation_model,
)
from corpus_structure.semantic.data_operation_demands import DemandPlanner, ReadyDataRequest
from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.data_operation_ports import (
    PortRefusal,
    PythonBatchMember,
    PythonRoleValue,
    resolve_python_port,
)
from corpus_structure.semantic.data_operation_storage import (
    DataOperationStorage,
    admitted_data_projection,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.python_operation_sources import PythonSourceCollection
from corpus_structure.semantic.runtime_bindings import RuntimeBinding
from corpus_structure.semantic.types import PreparedRelease, SourceBundle


@dataclass(frozen=True)
class NativeRequestClaim:
    request_id: str
    generation: int
    task_id: int
    attempt: int
    holder: str
    release_id: str
    deadline: datetime

    @property
    def fence(self) -> dict[str, Any]:
        return {
            name: getattr(self, name)
            for name in ("request_id", "generation", "task_id", "attempt", "holder")
        }


@dataclass(frozen=True)
class DemandAdvance:
    """Native snapshot remains authoritative, including incomplete/awaiting fates."""

    demand_id: str
    snapshot: bytes
    receipts: tuple[bytes, ...]


class _PythonWork:
    def __init__(self, future: Future, release):
        self.future, self.release = future, release
        self.retired = False
        self.parent_done = False

    def collect(self):
        return self.future.result()

    def cancel(self):
        self.future.cancel()

    def retire(self):
        # Reply/draft credit transfers to the parent through publication. The
        # parent releases it; retiring the future alone cannot release those bytes.
        if not self.future.done():
            return False
        if self.parent_done and not self.retired:
            self.release()
            self.retired = True
        return True


class NativeDemandExecutor:
    """One invocation's native claims, CPU capacity and exact settlement owner."""

    def __init__(
        self,
        engine: Engine,
        prepared: PreparedRelease,
        runtime: RuntimeBinding,
        sources: PythonSourceCollection,
        *,
        policy: CharacterizationExecutionPolicy | None = None,
        runtime_locations: Mapping[str, Path] | None = None,
        capability_factories: Mapping[str, Callable[..., Any]] | None = None,
        schema: SourceBundle | None = None,
    ):
        if runtime.release_id != prepared.release_id:
            raise ValueError("runtime belongs to another release")
        self.engine, self.prepared, self.runtime, self.sources = engine, prepared, runtime, sources
        self.model = bound_data_operation_model(prepared)
        self.runtime_locations = runtime_locations
        self.schema = schema
        self.capability_factories = dict(capability_factories or {})
        for operation in self.capability_factories:
            if self.model.operation(operation).capabilities.preparation == "none":
                raise PortRefusal("prepared capability supplied for an unprepared operation")
        self.policy = policy or CharacterizationExecutionPolicy()
        self.reservation = self.policy.max_packet_bytes + 2 * self.policy.max_reply_bytes
        if self.reservation > self.policy.max_owned_bytes:
            raise ValueError("native input, reply and publication draft exceed owned capacity")
        self.budget = OwnedByteBudget(self.policy.max_owned_bytes)
        self._invocation = Lock()
        self.ports = {}
        self.holder = "demand-owner:" + uuid4().hex

    def _port(self, operation):
        if operation not in self.ports:
            selected = self.model.operation(operation)
            if selected.effects:
                raise PortRefusal("effectful operation requires its declared effect owner")
            if selected.capabilities.preparation != "none":
                factory = self.capability_factories.get(operation)
                if factory is None:
                    raise PortRefusal("declared prepared capability is not acquired")
                with self.engine.begin() as connection:
                    admission = acquire_prepared_execution(
                        connection,
                        self.prepared,
                        self.sources,
                        operation,
                        self.runtime,
                        schema=self.schema,
                    )
                port = factory(
                    self.prepared,
                    self.model,
                    operation,
                    identity=admission.identity,
                    authorize=admission.authorize,
                )
                admission.authorize(port.identity)
                if port.operation != selected:
                    raise PortRefusal("prepared capability differs from effective operation")
                self.ports[operation] = port
            else:
                with self.engine.begin() as connection:
                    admission = acquire_python_execution(
                        connection,
                        self.prepared,
                        self.sources,
                        operation,
                        self.runtime,
                        schema=self.schema,
                    )
                self.ports[operation] = resolve_python_port(
                    self.model,
                    self.sources,
                    operation,
                    authorize=admission.authorize,
                    runtime_locations=self.runtime_locations,
                    schema=self.schema,
                    prepared=self.prepared,
                )
        return self.ports[operation]

    def _invoke(self, port, inputs, ready, owner, claim):
        owner.check_claim(claim)
        if port.operation.capabilities.preparation != "none":
            return port.invoke_python(
                inputs,
                binding=ready.binding_result,
                check_active=lambda: owner.check_claim(claim),
            )
        return port.invoke_python(inputs, binding=ready.binding_result)

    def _renew(self, connection: Connection, claim: OwnedClaim):
        if not isinstance(claim, NativeRequestClaim):
            raise TypeError("native owner requires a request-generation fence")
        DataOperationStorage(connection).invoke(
            "renew_data_request", {**claim.fence, "lease_seconds": 300}
        )

    def _hydrate(self, ready: ReadyDataRequest):
        pins = json.loads(ready.resolved.trust_evidence)
        with self.engine.begin() as connection:
            projections = admitted_data_projection(
                connection,
                pins.get("demand_id", self.demand),
                ready.operation,
                pins["trust"],
                self.model,
                read_id=pins["read_id"],
                subject=ready.subject,
                original_source=pins.get("original_source"),
            )
            by_kind = {p.kind: p for p in projections}
            values = []
            size = 0
            for role in ready.resolved.roles:
                if role.state == "known-absent":
                    continue
                declaration = next(
                    r for r in self.model.operation(ready.operation).roles if r.name == role.role
                )
                relation = by_kind[declaration.kind].relation
                decoded = []
                for member in role.members:
                    query = select(relation.c.meaning_body).where(
                        relation.c.product == member.product,
                        relation.c.member.is_not_distinct_from(member.member),
                        relation.c.subject == member.subject,
                    )
                    rows = connection.execute(query).scalars().all()
                    if len(rows) != 1:
                        raise ValueError("bound member no longer has one admitted body")
                    size += len(canonical_bytes(rows[0])) * member.multiplicity
                    if size > self.policy.max_packet_bytes:
                        raise ValueError("admitted inputs exceed complete packet capacity")
                    decoded.extend([decode_semantic_value(rows[0])] * member.multiplicity)
                if declaration.collection == "scalar":
                    if len(decoded) != 1:
                        raise PortRefusal("scalar input requires one admitted member")
                    value = decoded[0]
                else:
                    value = tuple(decoded)
                contract = next(
                    i.key
                    for i in self.model.identities
                    if i.owner == declaration.kind and i.domain == "kind"
                )
                values.append(PythonRoleValue(role.role, contract, value))
            return tuple(values)

    def _retain_answer(self, ready, claim, answer, port, owner):
        if answer.operation != ready.operation:
            raise PortRefusal("completion belongs to another operation")
        if (
            sum(
                len(value.content) + len(value.meaning or b"") + sum(map(len, value.members))
                for value in answer.outputs
            )
            > self.policy.max_reply_bytes
        ):
            raise ValueError("completion reply exceeds owned reply capacity")
        outputs = []
        for value in answer.outputs:
            if value.meaning is None:
                raise PortRefusal("native output requires canonical typed meaning")
            outputs.append(
                {
                    "role": value.role,
                    "position": 0,
                    "multiplicity": 1,
                    "product": {
                        "kind_contract": value.kind_contract,
                        "body": json.loads(value.meaning),
                        "members": [json.loads(member) for member in value.members],
                    },
                }
            )
        completion = {
            "outcome": "success",
            "outputs": outputs,
            "inputs": json.loads(ready.binding)["inputs"],
            "support": json.loads(ready.binding)["support"],
            "implementation_revision": port.identity.implementation,
        }
        if len(canonical_bytes(completion)) > self.policy.max_reply_bytes:
            raise ValueError("completion exceeds owned draft capacity")

        def retain(connection):
            return DataOperationStorage(connection).invoke(
                "retain_data_completion_intent",
                {
                    **claim.fence,
                    "runtime_id": self.runtime.runtime_id,
                    "completion": completion,
                },
            )

        return owner.retain(claim, retain)["intent_id"]

    def _execute(self, ready, owner, pool):
        reserve = self.reservation
        self.budget.reserve(reserve)
        work_items: list[_PythonWork] = []
        try:
            with self.engine.begin() as connection:
                claimed = DataOperationStorage(connection).invoke(
                    "claim_data_request",
                    {
                        "request_id": json.loads(ready.native)["request_id"],
                        "holder": self.holder,
                        "lease_seconds": 300,
                    },
                )
            if claimed["state"] != "claimed":
                return None
            claim = NativeRequestClaim(
                claimed["request_id"],
                claimed["generation"],
                claimed["task_id"],
                claimed["attempt"],
                claimed["holder"],
                self.prepared.release_id,
                datetime.fromisoformat(claimed["lease_until"].replace("Z", "+00:00")),
            )
            owner.add_claim(claim)
            retained = claimed.get("retained_intent_id")
            if claimed["action"] == "reconcile":
                if not retained:
                    raise ValueError("native reconciliation lacks exact retained intent")

                def adopt(connection):
                    return DataOperationStorage(connection).invoke(
                        "adopt_data_completion_intent",
                        {
                            **claim.fence,
                            "intent_id": retained,
                        },
                    )

                owner.retain(claim, adopt)
            else:
                port = self._port(ready.operation)
                inputs = self._hydrate(ready)

                def calculate():
                    return self._invoke(port, inputs, ready, owner, claim)

                def submit():
                    work = _PythonWork(pool.submit(calculate), lambda: self.budget.release(reserve))
                    work_items.append(work)
                    return work

                (answer,) = yield (PreparedWork(submit),)
                retained = self._retain_answer(ready, claim, answer, port, owner)

            def publish(connection):
                return DataOperationStorage(connection).invoke(
                    "publish_data_derivation",
                    {
                        **claim.fence,
                        "intent_id": retained,
                    },
                )

            return canonical_bytes(owner.settle(claim, publish))
        finally:
            if not work_items:
                self.budget.release(reserve)
            else:
                work = work_items[0]
                work.parent_done = True
                work.retire()

    def _execute_batch(self, ready, owner, pool):
        reserve = len(ready) * self.reservation
        self.budget.reserve(reserve)
        work_items: list[_PythonWork] = []
        try:
            pending = []
            receipts = []
            for item in ready:
                with self.engine.begin() as connection:
                    claimed = DataOperationStorage(connection).invoke(
                        "claim_data_request",
                        {
                            "request_id": json.loads(item.native)["request_id"],
                            "holder": self.holder,
                            "lease_seconds": 300,
                        },
                    )
                if claimed["state"] != "claimed":
                    continue
                claim = NativeRequestClaim(
                    claimed["request_id"],
                    claimed["generation"],
                    claimed["task_id"],
                    claimed["attempt"],
                    claimed["holder"],
                    self.prepared.release_id,
                    datetime.fromisoformat(claimed["lease_until"].replace("Z", "+00:00")),
                )
                owner.add_claim(claim)
                if claimed["action"] == "reconcile":
                    retained = claimed["retained_intent_id"]

                    def adopt(connection, claim=claim, retained=retained):
                        return DataOperationStorage(connection).invoke(
                            "adopt_data_completion_intent",
                            {
                                **claim.fence,
                                "intent_id": retained,
                            },
                        )

                    owner.retain(claim, adopt)

                    def publish(connection, claim=claim, retained=retained):
                        return DataOperationStorage(connection).invoke(
                            "publish_data_derivation",
                            {
                                **claim.fence,
                                "intent_id": retained,
                            },
                        )

                    receipts.append(canonical_bytes(owner.settle(claim, publish)))
                else:
                    member = f"{claim.request_id}:{claim.generation}:{claim.attempt}"
                    pending.append((member, item, claim, self._hydrate(item)))
            if pending:
                port = self._port(pending[0][1].operation)

                def calculate():
                    for _, _, claim, _ in pending:
                        owner.check_claim(claim)
                    return port.invoke_batch_python(
                        tuple(
                            PythonBatchMember(member, values, item.binding_result)
                            for member, item, _, values in pending
                        )
                    )

                def submit():
                    work = _PythonWork(pool.submit(calculate), lambda: self.budget.release(reserve))
                    work_items.append(work)
                    return work

                (answer,) = yield (PreparedWork(submit),)
                if tuple(member for member, _ in answer.members) != tuple(
                    member for member, _, _, _ in pending
                ):
                    raise ValueError("native batch member correspondence differs")
                failures = []
                for (_, item, claim, _), (_, result) in zip(pending, answer.members, strict=True):
                    try:
                        retained = self._retain_answer(item, claim, result, port, owner)

                        def publish(connection, claim=claim, retained=retained):
                            return DataOperationStorage(connection).invoke(
                                "publish_data_derivation",
                                {
                                    **claim.fence,
                                    "intent_id": retained,
                                },
                            )

                        receipts.append(canonical_bytes(owner.settle(claim, publish)))
                    except Exception as error:
                        failures.append(error)
                if failures:
                    raise ExceptionGroup("native batch member settlement failed", failures)
            return tuple(receipts)
        finally:
            if not work_items:
                self.budget.release(reserve)
            else:
                work = work_items[0]
                work.parent_done = True
                work.retire()

    def _drive_page(self, snapshot, authorization, owner, pool):
        with self.engine.begin() as connection:
            planner = DemandPlanner(self.model, DataOperationStorage(connection))
            ready = planner.ready(snapshot, authorization=authorization)
            selected = tuple(getattr(planner, "selected_population_ids", ()))
        receipts = []

        def plan():
            groups = {}
            plans: list[Any] = []
            for item in ready:
                if self.model.operation(item.operation).capabilities.forms == ("batch",):
                    groups.setdefault(item.operation, []).append(item)
                else:
                    plans.append(self._execute(item, owner, pool))
            plans.extend(
                self._execute_batch(tuple(items), owner, pool) for items in groups.values()
            )
            results = yield ReadyGroup(tuple(plans), max_active=self.capacity)
            for result in results:
                if isinstance(result, tuple):
                    receipts.extend(result)
                elif result is not None:
                    receipts.append(result)

        drive_prepared_work(plan(), owner)
        return tuple(receipts), selected, fulfilled

    @property
    def capacity(self):
        return min(self.policy.max_claims, self.policy.max_owned_bytes // self.reservation)

    def advance(self, demand: str, *, authorization: bytes = b"{}", limit: int = 100):
        """Advance one complete bounded-page sweep, including later independent work."""
        return self.run(demand, authorization=authorization, limit=limit, max_rounds=1)

    def run(
        self, demand: str, *, authorization: bytes = b"{}", limit: int = 100, max_rounds: int = 100
    ):
        """Replenish dependency-ready work until idle or an explicit round bound.

        Every sweep consumes one pinned read, including its continuation pages.
        Publication and governed discovery become visible on the next fresh sweep.
        Idle is not a completeness claim: the returned native snapshot retains
        waiting owners, unresolved inputs, partial populations and failures.
        """
        if type(max_rounds) is not int or max_rounds < 1:
            raise ValueError("round bound must be a positive integer")
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("frontier page bound must be between one and 1000")
        if not self._invocation.acquire(blocking=False):
            raise RuntimeError("execution owner already has an active invocation")
        self.demand = demand
        receipts = []
        seen_discovered = set()
        seen_fulfilled = set()
        try:
            with maintained_claims(self.engine, (), self.holder, renew=self._renew) as owner:
                with ThreadPoolExecutor(max_workers=self.policy.workers) as pool:
                    for _ in range(max_rounds):
                        progress = False
                        continuation = None
                        while True:
                            with self.engine.begin() as connection:
                                planner = DemandPlanner(
                                    self.model, DataOperationStorage(connection)
                                )
                                page = planner.resume(
                                    demand,
                                    limit=min(limit, self.capacity),
                                    **(
                                        {
                                            key: continuation[key]
                                            for key in (
                                                "selection",
                                                "after",
                                                "trust_snapshot",
                                                "read_id",
                                            )
                                        }
                                        if continuation
                                        else {}
                                    ),
                                )
                                if page.get("state") == "cancelled":
                                    return DemandAdvance(
                                        demand, canonical_bytes(page), tuple(receipts)
                                    )
                                for use in page["uses"]:
                                    if use["fate"] != "fulfilled":
                                        continue
                                    obligation = next(
                                        item
                                        for item in page["obligations"]
                                        if item["obligation_id"] == use["obligation_id"]
                                    )
                                    for relation in page["intent"]["discovery"]:
                                        if relation["producer"] != obligation["operation_id"]:
                                            continue
                                        for product in use["products"]:
                                            if product["role"] != relation["output_role"]:
                                                continue
                                            identity = (
                                                relation["population"],
                                                product["product_id"],
                                                use["derivation_id"],
                                            )
                                            if identity not in seen_discovered:
                                                planner.expand_discovery(
                                                    page,
                                                    population=identity[0],
                                                    product=identity[1],
                                                    derivation=identity[2],
                                                )
                                                seen_discovered.add(identity)
                                                progress = True
                            settled, selected, fulfilled = self._drive_page(
                                page, authorization, owner, pool
                            )
                            receipts.extend(settled)
                            progress = (
                                progress
                                or bool(settled)
                                or bool(selected)
                                or bool(set(fulfilled) - seen_fulfilled)
                            )
                            seen_fulfilled.update(fulfilled)
                            continuation = page.get("continuation")
                            if continuation is None:
                                break
                        if not progress:
                            break
            with self.engine.begin() as connection:
                final = DemandPlanner(self.model, DataOperationStorage(connection)).resume(
                    demand, limit=limit
                )
            return DemandAdvance(demand, canonical_bytes(final), tuple(receipts))
        finally:
            self._invocation.release()
