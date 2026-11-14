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
from threading import Event, Lock, Thread
from time import monotonic
from typing import Any
from uuid import uuid4

from sqlalchemy import Connection, Engine

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.core.work import (
    PhysicalRetirementUncertain,
    PreparedWork,
    ReadyGroup,
    drive_prepared_work,
)
from corpus_structure.methods.native_host import NativeHostResidency, NativeRetirementUncertain
from corpus_structure.semantic.claim_lifetime import (
    ClaimFenceLost,
    ClaimSettlementUncertain,
    OwnedClaim,
    maintained_claims,
)
from corpus_structure.semantic.cpu_execution import CPUExecutionScope, OwnedByteBudget
from corpus_structure.semantic.data_operation_admission import (
    acquire_prepared_execution,
    acquire_python_execution,
    bound_data_operation_model,
)
from corpus_structure.semantic.data_operation_demands import DemandPlanner, ReadyDataRequest
from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes, wire_json_loads
from corpus_structure.semantic.data_operation_ports import (
    PortRefusal,
    PythonBatchMember,
    PythonRoleValue,
    resolve_python_port,
)
from corpus_structure.semantic.data_operation_storage import (
    DataOperationStorage,
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
    snapshot_standing: str = "fresh-read"

    @property
    def receipts_truncated(self) -> bool:
        return self.receipt_count > len(self.receipts)


def _check_batch_active(owner, claims):
    """Keep shared physical work useful without hiding individual claim loss."""
    owner()
    failures = []
    for claim in claims:
        try:
            owner.check_claim(claim)
        except (ClaimFenceLost, ClaimSettlementUncertain) as error:
            failures.append(error)
        else:
            return
    if not failures:
        raise ValueError("batch activity requires at least one claim")
    raise ExceptionGroup("no batch member has confirmed active ownership", failures)


class NativeDemandExecutionError(ExceptionGroup):
    """Useful sibling receipts remain available when an execution sweep fails."""

    def __new__(cls, result: DemandAdvance, failures: tuple[Exception, ...]):
        return super().__new__(
            cls,
            f"native demand {result.demand_id} has {len(failures)} execution failures",
            failures,
        )

    def __init__(self, result: DemandAdvance, failures: tuple[Exception, ...]):
        self.result, self.failures = result, failures
        super().__init__(
            f"native demand {result.demand_id} has {len(failures)} execution failures", failures
        )

    def derive(self, exceptions):
        return NativeDemandExecutionError(self.result, tuple(exceptions))


@dataclass(frozen=True)
class _ExecutionResult:
    receipts: tuple[bytes, ...] = ()
    failures: tuple[Exception, ...] = ()


class _OwnedPythonPool:
    """Bounded retirement of the existing invocation's provider-transport threads."""

    def __init__(self, workers):
        self.pool = ThreadPoolExecutor(max_workers=workers)
        # CPython's worker registry is retained before submit can start a thread.
        self.threads = self.pool._threads
        self.drained = False
        self.closed = False
        self.failed = False

    def __enter__(self):
        return self

    def submit(self, callback):
        if self.failed:
            raise RuntimeError("provider transport executor retains an uncertain submission")
        try:
            return self.pool.submit(callback)
        except BaseException:
            self.failed = True
            raise

    def close(self):
        if self.closed:
            return
        self.closed = True
        from corpus_structure.semantic.cpu_execution import (
            _COOPERATIVE_CLOSE_SECONDS,
            _WORKER_EXIT_SECONDS,
        )

        deadline = monotonic() + _COOPERATIVE_CLOSE_SECONDS + _WORKER_EXIT_SECONDS
        stopped = Event()
        failures = []

        def stop():
            try:
                self.pool.shutdown(wait=False, cancel_futures=True)
            except BaseException as error:
                failures.append(error)
            finally:
                stopped.set()

        stopper = Thread(target=stop, name="demand-python-stop", daemon=True)
        stopper.start()
        stopped.wait(max(0, deadline - monotonic()))
        for thread in tuple(self.threads):
            thread.join(max(0, deadline - monotonic()))
        self.drained = (
            stopped.is_set()
            and not failures
            and all(not thread.is_alive() for thread in tuple(self.threads))
        )
        if not self.drained:
            raise PhysicalRetirementUncertain(
                "native demand transport threads did not drain; capacity remains owned"
            )

    def __exit__(self, *error):
        self.close()


class _PythonWork:
    def __init__(self, future: Future, release):
        self.future, self.release = future, release
        self.retired = False
        self.drained = False

    def collect(self):
        return self.future.result()

    def cancel(self):
        self.future.cancel()

    def retire(self):
        # The request retains its own shared lease through publication.
        if not self.future.done():
            return False

        def uncertain(error):
            if isinstance(error, BaseExceptionGroup):
                return any(uncertain(child) for child in error.exceptions)
            if isinstance(error, NativeRetirementUncertain):
                return not self.drained
            return isinstance(error, PhysicalRetirementUncertain)

        if not self.future.cancelled() and uncertain(self.future.exception()):
            return False
        if not self.retired:
            self.release()
            self.retired = True
        return True


class _RequestExecution:
    """One request's shared input/transport/reply/draft credit and physical handles."""

    def __init__(self, invocation, reservation):
        self.invocation, self.reservation = invocation, reservation
        self.cpu, self.native_hosts = invocation.cpu, invocation.native_hosts
        self.providers = invocation.providers
        self.engine = invocation.executor.engine
        self.claim: NativeRequestClaim | None = None
        self.handles = []
        self.consumer_inputs = {}
        self.consumer_results = {}
        self.binding_rows = {}
        self.uncertain_submission = False

    def submit_python(self, callback):
        if getattr(self.invocation.pool, "failed", False):
            raise RuntimeError("provider transport executor is unavailable before submission")
        share = self.reservation.share()
        completed = Event()

        def owned():
            try:
                return callback()
            finally:
                completed.set()

        try:
            work = _PythonWork(self.invocation.pool.submit(owned), share.release)
        except BaseException:
            # Submit may have accepted work before losing its acknowledgement.
            # No future is not proof that this reservation is free.
            self.uncertain_submission = True
            self.invocation.uncertain_python.append((completed, share))
            raise
        self.invocation.python_work.append(work)
        return work

    def relay(self, plan):
        """Retain exact submitted handles without inventing a second scheduler."""
        value, failure = None, None
        try:
            while True:
                try:
                    work = plan.throw(failure) if failure is not None else plan.send(value)
                except StopIteration as result:
                    return result.value
                if not isinstance(work, tuple) or not all(
                    isinstance(item, PreparedWork) for item in work
                ):
                    raise TypeError("prepared capability must yield declared physical work")

                def capture(item):
                    def submit():
                        handle = item.try_submit()
                        if handle is not None:
                            self.handles.append(handle)
                        return handle

                    return PreparedWork(submit, item.abandon)

                try:
                    value = yield tuple(capture(item) for item in work)
                    failure = None
                except BaseException as error:
                    value, failure = None, error
        finally:
            plan.close()

    def retired(self):
        if self.uncertain_submission and not self.invocation.physical_retired:
            return False
        return all([handle.retire() for handle in self.handles]) and self.cpu.reservation_retired(
            self.reservation
        )


class _InvocationExecution:
    def __init__(self, executor, pool):
        self.pool, self.python_work = pool, []
        self.uncertain_python = []
        self.pending_failures = []
        self.physical_retired = False
        self.cpu = CPUExecutionScope(
            executor.prepared, executor.policy, budget=executor.budget, retain_schema=False
        )
        self.native_hosts = NativeHostResidency(executor.policy, executor.nemotron_endpoint)
        from corpus_structure.methods.characterization_resources import ProviderExecution

        self.providers = ProviderExecution(
            executor.budget, executor.policy, native_group=self.native_hosts
        )
        self.executor = executor
        self._selected_operations = None

    def __enter__(self):
        return self

    def select_operations(self, operations):
        """Declare only the native-admitted demand closure, before first serving."""
        selected = tuple(sorted(operations))
        if self._selected_operations is not None:
            if selected != self._selected_operations:
                raise PortRefusal("native demand changed its frozen operation closure")
            return
        for operation in selected:
            if (
                operation in self.executor.capability_factories
                or self.executor.model.operation(operation).capabilities.prepared_factory
                is not None
            ):
                port = self.executor._port(operation)
                self.native_hosts.declare(port.native_selections)
                if getattr(port, "requires_prepared_schema", False):
                    self.cpu.retain_schema = True
        # Capture one schema capsule only for the frozen closure's actual
        # prepared kernels, before request credits consume retained capacity.
        self.cpu.prepare()
        self._selected_operations = selected

    def __exit__(self, *error):
        failures = []
        native_drained = False
        providers_drained = False
        try:
            self.providers.close()
        except BaseException as failure:
            failures.append(failure)
        try:
            self.native_hosts.close()
            native_drained = True
        except BaseException as failure:
            failures.append(failure)
        try:
            providers_drained = self.providers.retire()
            if not providers_drained:
                raise PhysicalRetirementUncertain("provider lanes retain unretired physical work")
        except BaseException as failure:
            failures.append(failure)
        try:
            self.cpu.close()
        except BaseException as failure:
            failures.append(failure)
        try:
            self.pool.close()
        except BaseException as failure:
            failures.append(failure)
        if (
            self.pool.drained
            and native_drained
            and providers_drained
            and self.cpu._physical_retired
        ):
            for _, share in self.uncertain_python:
                share.release()
        else:
            self.executor._quarantined = True
        if native_drained and self.pool.drained:
            for work in self.python_work:
                work.drained = True
                work.retire()
                # A worker unwinding after host teardown can finish after this
                # scope exits; its still-owned share retires on actual completion.
                work.future.add_done_callback(lambda _, work=work: work.retire())
        self.physical_retired = (
            native_drained
            and providers_drained
            and self.pool.drained
            and self.cpu._physical_retired
        )
        if self.physical_retired:
            for physical, claim, owner, error, phase in self.pending_failures:
                if physical.retired():
                    try:
                        self.executor._known_failure(claim, owner, error, phase=phase)
                    except Exception as failure:
                        failures.append(failure)
                else:
                    self.executor._quarantined = True
                    failures.append(
                        PhysicalRetirementUncertain(
                            "deferred native attempt still has unretired physical work"
                        )
                    )
        if failures:
            raise BaseExceptionGroup("native demand physical cleanup failed", failures)


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
        admission_engine: Engine | None = None,
        schema: SourceBundle | None = None,
        nemotron_endpoint: str | None = None,
    ):
        if runtime.release_id != prepared.release_id:
            raise ValueError("runtime belongs to another release")
        self.engine, self.prepared, self.runtime, self.sources = engine, prepared, runtime, sources
        self.admission_engine = engine if admission_engine is None else admission_engine
        self.model = bound_data_operation_model(prepared)
        self.runtime_locations = runtime_locations
        self.schema = schema
        self.nemotron_endpoint = nemotron_endpoint
        self.capability_factories = dict(capability_factories or {})
        for operation in self.capability_factories:
            if self.model.operation(operation).capabilities.preparation == "none":
                raise PortRefusal("prepared capability supplied for an unprepared operation")
        self.policy = policy or CharacterizationExecutionPolicy()
        # Parent input + encoded child packet, retained reply + decoded output +
        # publication draft. One transferable charge covers all physical owners.
        self.reservation = 2 * self.policy.max_packet_bytes + 3 * self.policy.max_reply_bytes
        if self.reservation > self.policy.max_owned_bytes:
            raise ValueError("native input, reply and publication draft exceed owned capacity")
        self.budget = OwnedByteBudget(self.policy.max_owned_bytes)
        self._invocation = Lock()
        self._quarantined = False
        self.ports = {}
        self.consumer_selectors = {}
        self.holder = "demand-owner:" + uuid4().hex

    def _port(self, operation):
        if operation not in self.ports:
            selected = self.model.operation(operation)
            if selected.effects and selected.capabilities.prepared_factory is None:
                raise PortRefusal("effectful operation requires its captured native effect owner")
            if selected.capabilities.preparation != "none":
                from corpus_structure.semantic.data_operation_consumers import (
                    resolve_prepared_factory,
                )

                factory = (
                    resolve_prepared_factory(self.model, self.sources, operation)
                    if selected.capabilities.prepared_factory is not None
                    else self.capability_factories.get(operation)
                )
                if factory is None:
                    raise PortRefusal("declared prepared capability is not acquired")
                with self.admission_engine.begin() as connection:
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
                    custody=admission.custody,
                    sources=self.sources,
                )
                if selected.effects:
                    from corpus_structure.semantic.data_operation_pdf_effect import (
                        PdfCaptureEffectPort,
                    )

                    if not isinstance(port, PdfCaptureEffectPort):
                        raise PortRefusal(
                            "declared effect has no admitted receipt-bearing effect owner"
                        )
                admission.authorize(port.identity)
                if port.operation != selected:
                    raise PortRefusal("prepared capability differs from effective operation")
                self.ports[operation] = port
                if selected.consumer_selection is not None:
                    from corpus_structure.semantic.data_operation_consumers import (
                        resolve_consumer_selection,
                    )

                    self.consumer_selectors[operation] = resolve_consumer_selection(
                        self.model,
                        self.sources,
                        operation,
                        port.consumer_receiver,
                        authorize=lambda admission=admission, port=port: admission.authorize(
                            port.identity
                        ),
                    )
            else:
                with self.admission_engine.begin() as connection:
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
                if selected.consumer_selection is not None:
                    from corpus_structure.semantic.data_operation_consumers import (
                        resolve_consumer_selection,
                    )

                    port = self.ports[operation]
                    self.consumer_selectors[operation] = resolve_consumer_selection(
                        self.model,
                        self.sources,
                        operation,
                        port.consumer_receiver,
                        authorize=lambda admission=admission, port=port: admission.authorize(
                            port.identity
                        ),
                    )
        return self.ports[operation]

    def _renew(self, connection: Connection, claim: OwnedClaim):
        if not isinstance(claim, NativeRequestClaim):
            raise TypeError("native owner requires a request-generation fence")
        result = DataOperationStorage(connection).invoke(
            "renew_data_request", {**claim.fence, "lease_seconds": 300}
        )
        if result["state"] == "lost":
            raise ClaimFenceLost(claim, result["reason"])

    def _hydrate(self, ready: ReadyDataRequest, execution_owner=None):
        from corpus_structure.semantic.data_operation_consumers import (
            BoundConsumerSelection,
            hydrate_consumer_selection,
        )

        pins = wire_json_loads(ready.resolved.trust_evidence)
        with self.engine.begin() as connection:
            selected = hydrate_consumer_selection(
                connection,
                self.model,
                BoundConsumerSelection.from_binding(
                    ready.binding_result, operation=ready.operation
                ),
                demand_id=pins.get("demand_id", self.demand),
                read_id=pins["read_id"],
                trust_snapshot=pins["trust"],
                max_bytes=self.policy.max_packet_bytes,
            )
        if self.model.operation(ready.operation).consumer_selection is not None:
            result = self.consumer_selectors[ready.operation].select_hydrated(selected)
            if execution_owner is not None:
                execution_owner.consumer_results[ready.obligation] = result
        if execution_owner is not None:
            execution_owner.consumer_inputs[ready.obligation] = selected
            execution_owner.binding_rows[ready.obligation] = {
                role: tuple(
                    {
                        "product": value.member.product,
                        "member": value.member.member,
                        "kind_contract": value.member.kind_contract,
                        "project_id": ready.resolved.subject_context.project_id,
                        "subject": value.member.subject,
                        "original_source": value.member.original_source,
                        "analyzed_scope": wire_json_loads(value.member.analyzed_scope),
                        "body": value.value(),
                    }
                    for value in values
                )
                for role, values in selected.values
            }
        roles = {role.name: role for role in self.model.operation(ready.operation).roles}
        identities = {(value.owner, value.domain): value.key for value in self.model.identities}
        values = []
        retained_roles = {role.role: role for role in ready.binding_result.roles}
        for role, members in selected.values:
            if retained_roles[role].state == "known-absent":
                continue
            decoded = tuple(member.value() for member in members)
            if roles[role].collection == "scalar":
                if len(decoded) != 1:
                    raise PortRefusal("scalar input requires one admitted member")
                value = decoded[0]
            else:
                value = decoded
            values.append(PythonRoleValue(role, identities[roles[role].kind, "kind"], value))
        return tuple(values)

    def _retain_answer(self, ready, claim, answer, port, owner, *, physical=None):
        if answer.operation != ready.operation:
            raise PortRefusal("completion belongs to another operation")
        operation = self.model.operation(ready.operation)
        if operation.output_witnesses:
            from corpus_structure.semantic.data_operation_output_witnesses import (
                validate_output_witnesses,
            )

            if physical is None or ready.obligation not in physical.binding_rows:
                raise PortRefusal(
                    "output witnesses require their authenticated selected input rows"
                )
            bodies = {}
            for value in answer.outputs:
                if value.meaning is None:
                    raise PortRefusal("output witnesses require canonical typed output meaning")
                bodies.setdefault(value.role, []).append(
                    decode_semantic_value(wire_json_loads(value.meaning))
                )
            validate_output_witnesses(operation, bodies, physical.binding_rows[ready.obligation])
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
        positions = {}
        for value in answer.outputs:
            position = positions.get(value.role, 0)
            positions[value.role] = position + 1
            if value.meaning is None:
                raise PortRefusal("native output requires canonical typed meaning")
            outputs.append(
                {
                    "role": value.role,
                    "position": position,
                    "multiplicity": 1,
                    "product": {
                        "kind_contract": value.kind_contract,
                        "body": json.loads(value.meaning),
                        "members": [wire_json_loads(member) for member in value.members],
                    },
                }
            )
        completion = {
            "outcome": answer.outcome,
            "outputs": outputs,
            "inputs": wire_json_loads(ready.binding)["inputs"],
            "support": wire_json_loads(ready.binding)["support"],
            "implementation_revision": port.identity.implementation,
        }
        if any(
            evidence is not None
            for evidence in (
                answer.execution_evidence,
                answer.cpu_execution_evidence,
                answer.pdf_execution_evidence,
                answer.provider_execution_evidence,
            )
        ):
            from corpus_structure.semantic.data_operation_execution_evidence import (
                bind_execution_evidence,
            )

            completion["execution_evidence"] = bind_execution_evidence(
                answer.execution_evidence,
                fence=claim.fence,
                runtime_id=self.runtime.runtime_id,
                cpu_content=answer.cpu_execution_evidence,
                pdf_content=answer.pdf_execution_evidence,
                provider_content=answer.provider_execution_evidence,
            )
        if len(json_bytes(completion)) > self.policy.max_reply_bytes:
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
            claimed = DataOperationStorage(connection).invoke(
                "claim_data_request",
                {
                    "request_id": json.loads(ready.native)["request_id"],
                    "holder": self.holder,
                    "lease_seconds": 300,
                },
            )
        if claimed["state"] != "claimed":
            return None, claimed
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
        return claim, claimed

    def _publish(self, claim, retained, owner):
        def publish(connection):
            return DataOperationStorage(connection).invoke(
                "publish_data_derivation",
                {
                    **claim.fence,
                    "intent_id": retained,
                },
            )

        receipt = canonical_bytes(owner.settle(claim, publish))
        self._receipt_count += 1
        if len(self._receipt_sink) < self._receipt_limit:
            self._receipt_sink.append(receipt)
        return receipt

    def _reconcile(self, claim, retained, owner):
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
            return DataOperationStorage(connection).invoke(
                "release_data_attempt",
                {
                    **claim.fence,
                    "physical_retirement": "confirmed",
                    "failure": {
                        "code": type(error).__module__ + "." + type(error).__qualname__,
                        "message": phase + " did not complete",
                    },
                },
            )

        try:
            owner.settle(claim, release)
        except Exception as cleanup:
            error.add_note("failed attempt release: " + str(cleanup))
            raise ExceptionGroup(
                "computation and exact attempt release failed", [error, cleanup]
            ) from cleanup

    def _execute(self, ready, owner):
        reservation = self.budget.admit(self.reservation)
        physical = _RequestExecution(self._physical, reservation)
        claim, phase = None, "claim"
        try:
            claim, claimed = self._claim(ready, owner)
            if claim is None:
                return _ExecutionResult()
            physical.claim = claim
            phase = "reconciliation"
            if claimed["action"] == "reconcile":
                receipt = self._reconcile(claim, claimed.get("retained_intent_id"), owner)
            else:
                phase = "computation"
                port = self._port(ready.operation)
                inputs = self._hydrate(ready, physical)
                answer = yield from physical.relay(
                    port.plan_python(
                        inputs,
                        binding=ready.binding_result,
                        check_active=lambda: owner.check_claim(claim),
                        execution_owner=physical,
                    )
                )
                phase = "settlement"
                retained = self._retain_answer(ready, claim, answer, port, owner, physical=physical)
                receipt = self._publish(claim, retained, owner)
            return _ExecutionResult((receipt,))
        except Exception as error:
            if claim is not None and physical.retired():
                try:
                    self._known_failure(claim, owner, error, phase=phase)
                except Exception as release_error:
                    error = release_error
            elif claim is not None:
                self._physical.pending_failures.append((physical, claim, owner, error, phase))
            self._failed_requests.add(
                (json.loads(ready.native)["request_id"], json.loads(ready.native).get("generation"))
            )
            error.add_note("native obligation: " + ready.obligation)
            return _ExecutionResult(failures=(error,))
        finally:
            reservation.release()

    def _execute_batch(self, ready, owner):
        reservation = self.budget.admit(len(ready) * self.reservation)
        physical = _RequestExecution(self._physical, reservation)
        pending, receipts, failures = [], [], []
        try:
            for item in ready:
                claim, phase = None, "claim"
                try:
                    claim, claimed = self._claim(item, owner)
                    if claim is None:
                        continue
                    if claimed["action"] == "reconcile":
                        phase = "reconciliation"
                        receipts.append(
                            self._reconcile(claim, claimed.get("retained_intent_id"), owner)
                        )
                    else:
                        phase = "computation"
                        port = self._port(item.operation)
                        inputs = self._hydrate(item, physical)
                        member = f"{claim.request_id}:{claim.generation}:{claim.attempt}"
                        if item.obligation in physical.consumer_inputs:
                            physical.consumer_inputs[member] = physical.consumer_inputs[
                                item.obligation
                            ]
                            if item.obligation in physical.consumer_results:
                                physical.consumer_results[member] = physical.consumer_results[
                                    item.obligation
                                ]
                        pending.append((member, item, claim, inputs, port))
                except Exception as error:
                    if claim is not None:
                        try:
                            self._known_failure(claim, owner, error, phase=phase)
                        except Exception as release_error:
                            error = release_error
                    self._failed_requests.add(
                        (
                            json.loads(item.native)["request_id"],
                            json.loads(item.native).get("generation"),
                        )
                    )
                    error.add_note("native obligation: " + item.obligation)
                    failures.append(error)
            if pending:
                active, rejected = [], []
                for row in pending:
                    try:
                        owner.check_claim(row[2])
                    except ClaimFenceLost as error:
                        rejected.append((row, error))
                    else:
                        active.append(row)
                for (_, _item, claim, _, _), error in rejected:
                    self._failed_requests.add((claim.request_id, claim.generation))
                    failures.append(error)
                pending = tuple(active)
                try:
                    answer = None
                    if pending:
                        # One original batch remains useful while any member has
                        # authority. Each logical result settles under its own fence.
                        answer = yield from physical.relay(
                            pending[0][4].plan_batch_python(
                                tuple(
                                    PythonBatchMember(member, inputs, item.binding_result)
                                    for member, item, _, inputs, _ in pending
                                ),
                                check_active=lambda: _check_batch_active(
                                    owner, tuple(row[2] for row in pending)
                                ),
                                execution_owner=physical,
                            )
                        )
                    if answer is not None and tuple(
                        member for member, _ in answer.members
                    ) != tuple(row[0] for row in pending):
                        raise ValueError("native batch member correspondence differs")
                except Exception as error:
                    for _, _item, claim, _, _ in pending:
                        if physical.retired():
                            try:
                                self._known_failure(claim, owner, error, phase="computation")
                            except Exception as release_error:
                                failures.append(release_error)
                        else:
                            self._physical.pending_failures.append(
                                (physical, claim, owner, error, "computation")
                            )
                        self._failed_requests.add((claim.request_id, claim.generation))
                    failures.append(error)
                else:
                    for (_, item, claim, _, port), (_, result) in zip(
                        pending,
                        answer.members if answer is not None else (),
                        strict=True,
                    ):
                        try:
                            retained = self._retain_answer(
                                item, claim, result, port, owner, physical=physical
                            )
                            receipts.append(self._publish(claim, retained, owner))
                        except Exception as error:
                            try:
                                self._known_failure(claim, owner, error, phase="settlement")
                            except Exception as release_error:
                                error = release_error
                            self._failed_requests.add((claim.request_id, claim.generation))
                            error.add_note("native obligation: " + item.obligation)
                            failures.append(error)
            return _ExecutionResult(tuple(receipts), tuple(failures))
        finally:
            reservation.release()

    def _drive_page(self, snapshot, authorization, owner):
        with self.engine.begin() as connection:
            planner = DemandPlanner(self.model, DataOperationStorage(connection))
            ready = tuple(
                item
                for item in planner.ready(snapshot, authorization=authorization)
                if (
                    json.loads(item.native)["request_id"],
                    json.loads(item.native).get("generation"),
                )
                not in self._failed_requests
            )
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
                    plans.append(self._execute(item, owner))
            plans.extend(self._execute_batch(tuple(items), owner) for items in groups.values())
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

    def _result(self, demand, snapshot, *, standing="fresh-read"):
        return DemandAdvance(
            demand, snapshot, tuple(self._receipt_sink), self._receipt_count, standing
        )

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
            result = self._result(demand, self._last_snapshot or b"{}", standing="last-pinned")
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
        if self._quarantined:
            raise PhysicalRetirementUncertain(
                "native demand execution owner retains unproven physical work"
            )
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
                _OwnedPythonPool(self.policy.max_provider_jobs) as pool,
                _InvocationExecution(self, pool) as physical,
            ):
                self._physical = physical
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
                            self._last_snapshot = json_bytes(page)
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
                        physical.select_operations(
                            item["operation"] for item in page["selection"]["operations"]
                        )
                        settled, selected, fulfilled, errors = self._drive_page(
                            page, authorization, owner
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
            result = self._result(demand, json_bytes(final))
            if self._member_failures:
                raise NativeDemandExecutionError(result, tuple(self._member_failures))
            return result
        finally:
            self._invocation.release()
