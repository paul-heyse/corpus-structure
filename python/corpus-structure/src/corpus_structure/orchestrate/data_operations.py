"""Execute admitted native demands without stage-run or method-name policy.

Semantic readiness and effect permission stay with the native bindings. This owner
connects pure Python capabilities to existing fenced task custody and short native
transactions; provider/prepared capabilities use their separately admitted owners.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from sqlalchemy import Connection, Engine, select

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.core.work import PreparedWork, ReadyGroup, drive_prepared_work
from corpus_structure.semantic.claim_lifetime import (
    ClaimFenceLost, ClaimSettlementUncertain, OwnedClaim, maintained_claims,
)
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
    receipt_count: int
    snapshot_standing: str = 'fresh-read'

    @property
    def receipts_truncated(self) -> bool:
        return self.receipt_count > len(self.receipts)


class NativeDemandExecutionError(RuntimeError):
    """Useful sibling receipts remain available when an execution sweep fails."""

    def __init__(self, result: DemandAdvance, failures: tuple[Exception, ...]):
        self.result, self.failures = result, failures
        super().__init__(f"native demand {result.demand_id} has {len(failures)} execution failures")


@dataclass(frozen=True)
class _ExecutionResult:
    receipts: tuple[bytes, ...] = ()
    failures: tuple[Exception, ...] = ()


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
        result = DataOperationStorage(connection).invoke(
            "renew_data_request", {**claim.fence, "lease_seconds": 300}
        )
        if result['state'] == 'lost':
            raise ClaimFenceLost(claim, result['reason'])

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
                        relation.c.support_evidence == json.loads(member.support_evidence),
                        relation.c.support_episodes == list(member.support_episodes),
                        relation.c.position.is_not_distinct_from(member.position),
                        relation.c.multiplicity == member.multiplicity,
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
        if answer.outcome not in self.model.operation(ready.operation).outcomes:
            raise PortRefusal("completion outcome is outside the declared operation")
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
            "outcome": answer.outcome,
            "outputs": outputs,
            "inputs": json.loads(ready.binding)["inputs"],
            "support": json.loads(ready.binding)["support"],
            "implementation_revision": port.identity.implementation,
        }
        if answer.execution_evidence is not None or answer.cpu_execution_evidence is not None:
            from corpus_structure.semantic.data_operation_execution_evidence import (
                bind_execution_evidence,
            )

            completion["execution_evidence"] = bind_execution_evidence(
                answer.execution_evidence,
                fence=claim.fence,
                runtime_id=self.runtime.runtime_id,
                cpu_content=answer.cpu_execution_evidence,
            )
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

    def _claim(self, ready, owner):
        with self.engine.begin() as connection:
            claimed = DataOperationStorage(connection).invoke('claim_data_request', {
                'request_id': json.loads(ready.native)['request_id'],
                'holder': self.holder, 'lease_seconds': 300,
            })
        if claimed['state'] != 'claimed':
            return None, claimed
        claim = NativeRequestClaim(
            claimed['request_id'], claimed['generation'], claimed['task_id'],
            claimed['attempt'], claimed['holder'], self.prepared.release_id,
            datetime.fromisoformat(claimed['lease_until'].replace('Z', '+00:00')),
        )
        owner.add_claim(claim)
        return claim, claimed

    def _publish(self, claim, retained, owner):
        def publish(connection):
            return DataOperationStorage(connection).invoke('publish_data_derivation', {
                **claim.fence, 'intent_id': retained,
            })
        receipt = canonical_bytes(owner.settle(claim, publish))
        self._receipt_count += 1
        if len(self._receipt_sink) < self._receipt_limit:
            self._receipt_sink.append(receipt)
        return receipt

    def _reconcile(self, claim, retained, owner):
        if not retained:
            raise ValueError('native reconciliation lacks exact retained intent')
        def adopt(connection):
            return DataOperationStorage(connection).invoke('adopt_data_completion_intent', {
                **claim.fence, 'intent_id': retained,
            })
        owner.retain(claim, adopt)
        return self._publish(claim, retained, owner)

    def _known_failure(self, claim, owner, error, *, phase):
        """Release only a known-retired computation, never uncertain settlement."""
        if claim is None or isinstance(error, (ClaimFenceLost, ClaimSettlementUncertain)):
            return
        try:
            owner.check_claim(claim)
        except ClaimFenceLost:
            return
        # Preserve the actual exception to the caller. The immutable native record
        # describes custody without copying protected values from exception text.
        def release(connection):
            return DataOperationStorage(connection).invoke('release_data_attempt', {
                **claim.fence, 'physical_retirement': 'confirmed',
                'failure': {'code': type(error).__module__ + '.' + type(error).__qualname__,
                            'message': phase + ' did not complete'},
            })
        try:
            owner.settle(claim, release)
        except Exception as cleanup:
            error.add_note('failed attempt release: ' + str(cleanup))
            raise ExceptionGroup('computation and exact attempt release failed', [error, cleanup])

    def _execute(self, ready, owner, pool):
        reserve = self.reservation
        self.budget.reserve(reserve)
        work_items: list[_PythonWork] = []
        claim, phase = None, 'claim'
        try:
            claim, claimed = self._claim(ready, owner)
            if claim is None:
                return _ExecutionResult()
            phase = 'reconciliation'
            if claimed['action'] == 'reconcile':
                receipt = self._reconcile(claim, claimed.get('retained_intent_id'), owner)
            else:
                phase = 'computation'
                port = self._port(ready.operation)
                inputs = self._hydrate(ready)
                def calculate():
                    return self._invoke(port, inputs, ready, owner, claim)
                def submit():
                    work = _PythonWork(pool.submit(calculate), lambda: self.budget.release(reserve))
                    work_items.append(work)
                    return work
                (answer,) = yield (PreparedWork(submit),)
                phase = 'settlement'
                retained = self._retain_answer(ready, claim, answer, port, owner)
                receipt = self._publish(claim, retained, owner)
            return _ExecutionResult((receipt,))
        except Exception as error:
            if claim is not None and (not work_items or work_items[0].future.done()):
                try:
                    self._known_failure(claim, owner, error, phase=phase)
                except Exception as release_error:
                    error = release_error
            self._failed_requests.add((json.loads(ready.native)['request_id'],
                                       json.loads(ready.native).get('generation')))
            error.add_note('native obligation: ' + ready.obligation)
            return _ExecutionResult(failures=(error,))
        finally:
            if not work_items:
                self.budget.release(reserve)
            else:
                work_items[0].parent_done = True
                work_items[0].retire()

    def _execute_batch(self, ready, owner, pool):
        reserve = len(ready) * self.reservation
        self.budget.reserve(reserve)
        work_items: list[_PythonWork] = []
        pending, receipts, failures = [], [], []
        try:
            for item in ready:
                claim, phase = None, 'claim'
                try:
                    claim, claimed = self._claim(item, owner)
                    if claim is None:
                        continue
                    if claimed['action'] == 'reconcile':
                        phase = 'reconciliation'
                        receipts.append(self._reconcile(claim, claimed.get('retained_intent_id'), owner))
                    else:
                        phase = 'computation'
                        port = self._port(item.operation)
                        inputs = self._hydrate(item)
                        member = f'{claim.request_id}:{claim.generation}:{claim.attempt}'
                        pending.append((member, item, claim, inputs, port))
                except Exception as error:
                    if claim is not None:
                        try:
                            self._known_failure(claim, owner, error, phase=phase)
                        except Exception as release_error:
                            error = release_error
                    self._failed_requests.add((json.loads(item.native)['request_id'],
                                               json.loads(item.native).get('generation')))
                    error.add_note('native obligation: ' + item.obligation)
                    failures.append(error)
            if pending:
                def calculate():
                    active, rejected = [], []
                    for row in pending:
                        try:
                            owner.check_claim(row[2])
                        except ClaimFenceLost as error:
                            rejected.append((row, error))
                        else:
                            active.append(row)
                    answer = active[0][4].invoke_batch_python(tuple(
                        PythonBatchMember(member, inputs, item.binding_result)
                        for member, item, _, inputs, _ in active
                    )) if active else None
                    return tuple(active), tuple(rejected), answer
                def submit():
                    work = _PythonWork(pool.submit(calculate), lambda: self.budget.release(reserve))
                    work_items.append(work)
                    return work
                try:
                    (computed,) = yield (PreparedWork(submit),)
                    active, rejected, answer = computed
                    for (_, item, claim, _, _), error in rejected:
                        self._failed_requests.add((claim.request_id, claim.generation))
                        failures.append(error)
                    pending = active
                    if answer is not None and tuple(member for member, _ in answer.members) != tuple(row[0] for row in pending):
                        raise ValueError('native batch member correspondence differs')
                except Exception as error:
                    for _, item, claim, _, _ in pending:
                        try:
                            self._known_failure(claim, owner, error, phase='computation')
                        except Exception as release_error:
                            failures.append(release_error)
                        self._failed_requests.add((claim.request_id, claim.generation))
                    failures.append(error)
                else:
                    for (_, item, claim, _, port), (_, result) in zip(
                        pending, answer.members if answer is not None else (), strict=True,
                    ):
                        try:
                            retained = self._retain_answer(item, claim, result, port, owner)
                            receipts.append(self._publish(claim, retained, owner))
                        except Exception as error:
                            try:
                                self._known_failure(claim, owner, error, phase='settlement')
                            except Exception as release_error:
                                error = release_error
                            self._failed_requests.add((claim.request_id, claim.generation))
                            error.add_note('native obligation: ' + item.obligation)
                            failures.append(error)
            return _ExecutionResult(tuple(receipts), tuple(failures))
        finally:
            if not work_items:
                self.budget.release(reserve)
            else:
                work_items[0].parent_done = True
                work_items[0].retire()

    def _drive_page(self, snapshot, authorization, owner, pool):
        with self.engine.begin() as connection:
            planner = DemandPlanner(self.model, DataOperationStorage(connection))
            ready = tuple(item for item in planner.ready(snapshot, authorization=authorization)
                          if (json.loads(item.native)['request_id'],
                              json.loads(item.native).get('generation')) not in self._failed_requests)
            selected = tuple(getattr(planner, "selected_population_ids", ()))
            fulfilled = planner.fulfilled_request_ids
        receipts, failures = [], []

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
                receipts.extend(result.receipts)
                failures.extend(result.failures)

        drive_prepared_work(plan(), owner)
        return tuple(receipts), selected, fulfilled, tuple(failures)

    @property
    def capacity(self):
        return min(self.policy.max_claims, self.policy.max_owned_bytes // self.reservation)

    def advance(self, demand: str, *, authorization: bytes = b"{}", limit: int = 100):
        """Advance one complete bounded-page sweep, including later independent work."""
        return self.run(demand, authorization=authorization, limit=limit, max_rounds=1)

    def _result(self, demand, snapshot, *, standing='fresh-read'):
        return DemandAdvance(demand, snapshot, tuple(self._receipt_sink),
                             self._receipt_count, standing)

    @contextmanager
    def _report_execution_failure(self, demand):
        try:
            yield
        except NativeDemandExecutionError:
            raise
        except Exception as error:
            if not self._receipt_count and not self._member_failures:
                raise
            failures = (*self._member_failures, error)
            result = self._result(demand, self._last_snapshot or b'{}', standing='last-pinned')
            raise NativeDemandExecutionError(result, failures) from error

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
        self._receipt_sink, self._member_failures = [], []
        self._receipt_count, self._receipt_limit = 0, limit
        self._last_snapshot = None
        self._failed_requests = set()
        seen_discovered = set()
        seen_fulfilled = set()
        try:
            with (
                self._report_execution_failure(demand),
                maintained_claims(self.engine, (), self.holder, renew=self._renew) as owner,
                ThreadPoolExecutor(max_workers=self.policy.workers) as pool,
            ):
                for _ in range(max_rounds):
                    progress = False
                    continuation = None
                    while True:
                        with self.engine.begin() as connection:
                            planner = DemandPlanner(self.model, DataOperationStorage(connection))
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
                            if (page["release_id"], page["runtime_id"]) != (
                                self.prepared.release_id,
                                self.runtime.runtime_id,
                            ):
                                raise PortRefusal(
                                    "execution context differs from native demand custody"
                                )
                            self._last_snapshot = canonical_bytes(page)
                            if page.get("state") == "cancelled":
                                return self._result(demand, self._last_snapshot)
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
                        settled, selected, fulfilled, errors = self._drive_page(
                            page, authorization, owner, pool
                        )
                        self._member_failures.extend(errors)
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
            result = self._result(demand, canonical_bytes(final))
            if self._member_failures:
                raise NativeDemandExecutionError(result, tuple(self._member_failures)) from ExceptionGroup(
                    'native demand execution failures', self._member_failures,
                )
            return result
        finally:
            self._invocation.release()
