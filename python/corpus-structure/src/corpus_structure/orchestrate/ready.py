"""Invocation-local admission for source lifetimes, separate from durable claim authority."""

from concurrent.futures import Future
from contextlib import ExitStack, contextmanager
from types import SimpleNamespace

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy


class _Permit:
    def __init__(self, owner, kind, reserved=0):
        self.owner, self.kind, self.active = owner, kind, True
        self.reserved = reserved

    def release(self):
        if self.active:
            self.owner.used[self.kind] -= 1
            if self.reserved:
                self.owner.budget.release(self.reserved)
            self.active = False


class _AdmissionHandle:
    def __init__(self, permit):
        self.future = Future()
        self.future.set_result(permit)

    def collect(self):
        return self.future.result()

    def cancel(self):
        self.future.result().release()

    def retire(self):
        # The plan, not this completed admission response, owns the lifetime.
        return True


class SourceAdmission:
    def __init__(self, policy, budget):
        self.budget, self.policy = budget, policy
        self.limits = {"stage": policy.max_active_stage_runs, "claim": policy.max_claims}
        self.used = {kind: 0 for kind in self.limits}

    def try_take(self, kind, draft_bytes=None):
        if self.used[kind] >= self.limits[kind]:
            return None
        reserve = (
            (self.policy.max_reply_bytes if draft_bytes is None else draft_bytes)
            if kind == "claim"
            else 0
        )
        if reserve:
            from corpus_structure.semantic.cpu_execution import CapacityExceeded

            try:
                self.budget.reserve(reserve)
            except CapacityExceeded:
                if not self.used["claim"]:
                    raise
                return None
        self.used[kind] += 1
        return _Permit(self, kind, reserve)

    def try_work(self, kind):
        permit = self.try_take(kind)
        return None if permit is None else _AdmissionHandle(permit)


def source_admission(execution):
    owner = getattr(execution, "_source_admission", None)
    if owner is None:
        owner = SourceAdmission(execution.cpu.policy, execution.cpu.budget)
        execution._source_admission = owner
    return owner


@contextmanager
def owned_source_execution(prepared, *, policy: CharacterizationExecutionPolicy | None = None):
    """Own physical state for a low-level caller already supplying its released contract.

    This scope does not grant full release verification; live source/native admission stays
    with the ordinary operations. Public demands use VerifiedExecutionPreparation instead.
    """
    from corpus_structure.methods.characterization_resources import ProviderExecution
    from corpus_structure.semantic.cpu_execution import CPUExecutionScope

    with ExitStack() as closers:
        cpu = CPUExecutionScope(prepared, policy)
        closers.callback(cpu.close)
        providers = ProviderExecution(cpu.budget, cpu.policy)
        closers.callback(providers.close)
        methods = set()
        opened = True

        def require_release(release_id):
            if not opened or cpu.prepared.release_id != release_id:
                raise ValueError("source execution is closed or belongs to another release")
            return cpu.prepared

        def register(registry):
            for method in registry.methods():
                close = getattr(method, "close", None)
                if close is not None and id(method) not in methods:
                    methods.add(id(method))
                    closers.callback(close)

        try:
            yield SimpleNamespace(
                cpu=cpu,
                policy=cpu.policy,
                providers=providers,
                register_methods=register,
                require_release=require_release,
            )
        finally:
            opened = False
