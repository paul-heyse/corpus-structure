"""Process-owned execution resources; a run borrows one explicit physical lifetime."""

from __future__ import annotations

from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass
from threading import Lock
from typing import Any


class ExecutionPreparationDeferred(Exception):
    """Current physical borrowers can retire and make room for cold preparation."""


@dataclass
class _OwnedBody:
    content: bytes
    credit: Any
    references: int = 0


@dataclass
class _VerifiedBasis:
    basis: Any
    header: tuple
    runtime: tuple
    capsule: bytes
    bodies: tuple[_OwnedBody, ...]
    context: Any = None
    references: int = 0


class ProcessExecutionHost:
    """One active run, one budget and retained, authenticated idle preparation.

    Eviction retires the CPU generation before releasing a capsule: its workers
    may still retain reconstructed releases even after shared-memory unlink.
    The verified-basis LRU itself remains reusable after that generation retires.
    """

    def __init__(self):
        self.policy: Any = None
        self.budget: Any = None
        self.resources: Any = None
        self._bases: OrderedDict[tuple, _VerifiedBasis] = OrderedDict()
        self._bodies: dict[int, _OwnedBody] = {}
        self._run_lock = Lock()
        self._token = None
        self._execution = None
        self._borrowed: list[_VerifiedBasis] = []
        self._quarantine = None
        self._closed = False

    def _check(self):
        if self._quarantine is not None:
            from corpus_structure.core.work import PhysicalRetirementUncertain

            raise PhysicalRetirementUncertain("process execution host is quarantined; confirm managed process cleanup before restart") from self._quarantine
        if self._closed:
            raise RuntimeError("process execution host is closed")

    def _configure(self, policy):
        from corpus_structure.semantic.cpu_execution import OwnedByteBudget

        from corpus_structure.semantic.determinants import BYTE_LIBRARIES, DEPLOYMENT_LIBRARIES, determinant_version
        from corpus_structure.semantic.types import SEMANTIC_COMPILER_VERSION

        self._run_determinants = (
            *((name, determinant_version(name)) for name in sorted(set(BYTE_LIBRARIES) | set(DEPLOYMENT_LIBRARIES))),
            ("semantic-compiler", SEMANTIC_COMPILER_VERSION),
        )
        if self.policy is not None and self.policy != policy:
            self.retire_resources()
            for key in tuple(self._bases):
                self._evict(key)
        self.policy = policy
        if self.budget is None or self.budget.limit != policy.max_owned_bytes:
            self.budget = OwnedByteBudget(policy.max_owned_bytes)

    @contextmanager
    def run(self, policy):
        if not self._run_lock.acquire(blocking=False):
            raise RuntimeError("process execution host already has an active run")
        token = object()
        try:
            self._check()
            self._configure(policy)
            self._token = token
            yield token
        finally:
            for entry in self._borrowed:
                entry.references -= 1
            self._borrowed.clear()
            self._token = None
            try:
                self._trim_idle()
            finally:
                self._run_lock.release()

    def _require_run(self, token):
        self._check()
        if token is not self._token or token is None:
            raise RuntimeError("execution resources require their active host run")

    def _evict(self, key):
        entry = self._bases[key]
        if self._execution is not None and self._execution.has_live_requests():
            raise ExecutionPreparationDeferred("execution preparation awaits physical request retirement")
        if entry.references:
            raise RuntimeError("active execution capsule cannot be evicted")
        self.retire_cpu()
        self._release_bodies(entry.bodies)
        del self._bases[key]

    def _retain_bodies(self, buffers):
        bodies = []
        try:
            for content in {id(value): value for value in buffers}.values():
                if type(content) is not bytes:
                    raise TypeError("execution basis retains immutable encoded bytes")
                body = self._bodies.get(id(content))
                if body is None:
                    body = _OwnedBody(content, self.budget.admit(len(content)))
                    self._bodies[id(content)] = body
                body.references += 1
                bodies.append(body)
        except BaseException:
            self._release_bodies(bodies)
            raise
        return tuple(bodies)

    def _release_bodies(self, bodies):
        for body in bodies:
            body.references -= 1
            if not body.references:
                body.credit.release()
                del self._bodies[id(body.content)]

    def _trim_idle(self):
        if self.policy is None or self._quarantine is not None:
            return
        if self.resources is not None:
            cpu = self.resources.cpu
            if cpu is not None and (len(cpu._release_capsules) > self.policy.max_idle_capsules
                or cpu.preparation_bytes > self.policy.max_idle_capsule_bytes):
                self.retire_resources()
        while True:
            idle = [(key, entry) for key, entry in self._bases.items() if not entry.references]
            active_bodies = {id(body) for entry in self._bases.values() if entry.references for body in entry.bodies}
            idle_bodies = {id(body): body for _, entry in idle for body in entry.bodies}
            idle_bytes = sum(len(body.content) for identity, body in idle_bodies.items() if identity not in active_bodies)
            cpu_bytes = (self.resources.cpu.preparation_bytes
                         if self.resources is not None and self.resources.cpu is not None else 0)
            if (len(idle) <= self.policy.max_idle_capsules
                and idle_bytes + cpu_bytes <= self.policy.max_idle_capsule_bytes):
                return
            self._evict(idle[0][0])

    def acquire_basis(self, engine, connection, release_id, runtime_id, *, source_root, token):
        """Reuse verified meaning only after fresh protected header/runtime reads."""
        from sqlalchemy import String, func, literal_column, select

        from corpus_structure.semantic.archive_reader import _archive_header
        from corpus_structure.semantic.data_operation_service import acquire_data_execution_basis
        from corpus_structure.semantic.metadata import table
        from corpus_structure.semantic.refusals import SemanticRefusal
        from corpus_structure.semantic.cpu_execution import CapacityExceeded, release_capsule

        self._require_run(token)
        root = source_root.resolve() if source_root is not None else None
        key = engine, release_id, runtime_id, root, self._run_determinants
        entry = self._bases.get(key)
        if entry is None and self._live_requests():
            raise ExecutionPreparationDeferred("cold execution basis awaits current physical owners")
        header = _archive_header(connection, release_id)
        if header is None or header.finalized_digest != header.content_digest:
            raise SemanticRefusal("execution basis requires its protected finalized archive")
        stored = table("sem.runtime_binding")
        runtime = connection.execute(select(
            stored.c.release_id, stored.c.runtime_id, stored.c.execution_profile,
            func.octet_length(stored.c.manifest_bytes), func.octet_length(stored.c.archive_bytes),
            *(literal_column(f"sem.runtime_binding.{name}", type_=String()).cast(String())
              for name in ("tableoid", "xmin", "ctid")),
        ).where(stored.c.release_id == release_id, stored.c.runtime_id == runtime_id)).one()
        if entry is not None:
            if entry.header != tuple(header) or entry.runtime != tuple(runtime):
                raise SemanticRefusal("verified execution archive/runtime changed; restart required")
        else:
            basis = acquire_data_execution_basis(connection, release_id, runtime_id, source_root=root)
            observed = _archive_header(connection, release_id)
            if observed is None or tuple(observed) != tuple(header):
                raise SemanticRefusal("execution archive changed while verifying its basis")
            capsule = release_capsule(basis.prepared)
            buffers = (capsule, basis.runtime.manifest, basis.runtime.archive)
            unique = {id(content): content for content in buffers}
            request_bytes = 2 * self.policy.max_packet_bytes + 3 * self.policy.max_reply_bytes
            required = sum(len(content) for identity, content in unique.items() if identity not in self._bodies) + request_bytes
            while required > self.budget.limit - self.budget.used_bytes:
                idle = next((key for key, item in self._bases.items() if not item.references), None)
                if idle is None:
                    raise CapacityExceeded("execution capsules and one complete request exceed owned capacity")
                self._evict(idle)
                required = sum(len(content) for identity, content in unique.items() if identity not in self._bodies) + request_bytes
            entry = _VerifiedBasis(basis, tuple(header), tuple(runtime), capsule, self._retain_bodies(buffers))
            self._bases[key] = entry
        self._bases.move_to_end(key)
        if not any(held is entry for held in self._borrowed):
            entry.references += 1
            self._borrowed.append(entry)
        return entry.basis

    def context(self, basis):
        from corpus_structure.orchestrate.data_operations import _BasisExecution

        entry = next((entry for entry in self._borrowed if entry.basis is basis), None)
        if entry is None:
            return _BasisExecution(basis)
        if entry.context is None:
            entry.context = _BasisExecution(basis)
        return entry.context

    def execution(self, executor, token):
        from corpus_structure.orchestrate.data_operations import _RunExecution

        self._require_run(token)
        if self._execution is not None:
            raise RuntimeError("host resources already belong to an active physical run")
        executor.budget = self.budget
        if self.resources is not None and self.resources.resource_key != (executor.port_workers, executor.nemotron_endpoint):
            self.retire_resources()
        if self.resources is None:
            from types import SimpleNamespace

            from corpus_structure.methods.characterization_resources import ProviderExecution
            from corpus_structure.methods.native_host import NativeHostResidency
            from corpus_structure.orchestrate.data_operations import _OwnedPythonPool
            from corpus_structure.semantic.cpu_execution import CPUExecutionScope

            native = NativeHostResidency(self.policy, executor.nemotron_endpoint)
            self.resources = SimpleNamespace(
                resource_key=(executor.port_workers, executor.nemotron_endpoint),
                pool=_OwnedPythonPool(executor.port_workers),
                cpu=CPUExecutionScope(executor.prepared, self.policy, budget=self.budget, retain_schema=False),
                native_hosts=native,
                providers=ProviderExecution(self.budget, self.policy, native_group=native),
            )
        if self.resources.cpu is None:
            from corpus_structure.semantic.cpu_execution import CPUExecutionScope

            self.resources.cpu = CPUExecutionScope(executor.prepared, self.policy, budget=self.budget, retain_schema=False)
        try:
            self.resources.native_hosts.begin_run()
        except BaseException as failure:
            self._quarantine = failure
            raise
        return _RunExecution(executor, self)

    def _live_requests(self):
        return self._execution is not None and self._execution.has_live_requests()

    def ensure_request_room(self, request_bytes):
        from corpus_structure.semantic.cpu_execution import CapacityExceeded

        while request_bytes > self.budget.limit - self.budget.used_bytes:
            if self._live_requests():
                return  # Stage-A admission waits for existing owners to retire.
            idle = next((key for key, entry in self._bases.items() if not entry.references), None)
            if idle is not None:
                self._evict(idle)
            elif self.resources is not None and self.resources.cpu.preparation_bytes:
                self.retire_cpu()
            else:
                raise CapacityExceeded("execution preparation and one complete request exceed owned capacity")

    def cpu_for_release(self, prepared, request_bytes):
        from corpus_structure.semantic.cpu_execution import CapacityExceeded, release_capsule

        entry = next((entry for entry in self._borrowed if entry.basis.prepared is prepared), None)
        content = entry.capsule if entry is not None else release_capsule(prepared)
        while True:
            retained = prepared.release_id in self.resources.cpu._release_capsules
            required = request_bytes if retained else max(2 * len(content), len(content) + request_bytes)
            if required <= self.budget.limit - self.budget.used_bytes:
                return self.resources.cpu.for_release(prepared, request_bytes=request_bytes, capsule_bytes=content)
            if self._live_requests():
                raise ExecutionPreparationDeferred("CPU capsule preparation awaits current physical borrowers")
            idle = next((key for key, entry in self._bases.items() if not entry.references), None)
            if idle is not None:
                self._evict(idle)
            elif self.resources.cpu.preparation_bytes:
                self.retire_cpu()
            else:
                raise CapacityExceeded("native preparation and one complete request exceed owned capacity")

    def retire_cpu(self):
        resources = self.resources
        if resources is None or resources.cpu is None:
            return
        if (self._execution is not None and self._execution.has_live_requests()
            or resources.cpu._admissions or resources.cpu._submissions or resources.cpu._stream_transports):
            raise ExecutionPreparationDeferred("CPU generation still has physical borrowers")
        try:
            resources.cpu.close()
        except BaseException as error:
            self._quarantine = error
            raise
        if not resources.cpu._physical_retired:
            from corpus_structure.core.work import PhysicalRetirementUncertain

            self._quarantine = PhysicalRetirementUncertain("CPU capsule eviction lacks confirmed group retirement")
            raise self._quarantine
        from corpus_structure.semantic.cpu_execution import CPUExecutionScope

        resources.cpu = None
        for entry in self._bases.values():
            if entry.context is not None:
                entry.context.cpu, entry.context.prepared_schema = None, False
        if self._execution is not None:
            prepared = self._execution.executor.prepared
            resources.cpu = CPUExecutionScope(prepared, self.policy, budget=self.budget, retain_schema=False)
            self._execution.cpu = resources.cpu
            for context in self._execution.executor._contexts.values():
                context.cpu, context.prepared_schema = None, False
            self._execution.executor._preparation_bytes = 0

    def retire_resources(self):
        resources = self.resources
        if resources is None:
            return
        failures = []
        for owner in (resources.providers, resources.native_hosts, resources.cpu, resources.pool):
            if owner is None:
                continue
            try:
                owner.close()
            except BaseException as error:
                failures.append(error)
        confirmed = resources.pool.drained and (resources.cpu is None or resources.cpu._physical_retired) and resources.native_hosts.physical_drained and resources.providers.retire()
        if not confirmed:
            from corpus_structure.core.work import PhysicalRetirementUncertain

            error = PhysicalRetirementUncertain("execution generation join remains unconfirmed; charges retained")
            self._quarantine = error
            failures.append(error)
        else:
            self.resources = None
        if failures:
            raise BaseExceptionGroup("process execution resource retirement failed", failures)

    @contextmanager
    def external_gpu(self, check_active):
        self._check()
        resources = self.resources
        if resources is None:
            yield
        else:
            with resources.native_hosts.external_gpu(check_active):
                yield

    def close(self):
        if self._closed:
            return
        if not self._run_lock.acquire(blocking=False):
            raise RuntimeError("cannot close an active process execution run")
        try:
            self.retire_resources()
            for key in tuple(self._bases):
                self._evict(key)
            self._closed = True
        finally:
            self._run_lock.release()


_PROCESS_LOCK = Lock()
_PROCESS_HOST = None
_PROCESS_REFERENCES = 0


@contextmanager
def execution_host_scope():
    """CLI/MCP and standalone calls share exactly one installed process owner."""
    global _PROCESS_HOST, _PROCESS_REFERENCES
    with _PROCESS_LOCK:
        if _PROCESS_HOST is None:
            _PROCESS_HOST = ProcessExecutionHost()
        host = _PROCESS_HOST
        _PROCESS_REFERENCES += 1
    try:
        yield host
    finally:
        with _PROCESS_LOCK:
            _PROCESS_REFERENCES -= 1
            if not _PROCESS_REFERENCES:
                try:
                    host.close()
                finally:
                    # A quarantined host stays installed, retaining custody and
                    # refusing further work until this process restarts.
                    if host._closed:
                        _PROCESS_HOST = None


@contextmanager
def external_execution_gpu(check_active):
    host = _PROCESS_HOST
    if host is None:
        yield
    else:
        with host.external_gpu(check_active):
            yield
