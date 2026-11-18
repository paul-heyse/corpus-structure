"""Native transactions, admission and claim custody for demand execution."""

from contextlib import contextmanager
from typing import Literal, overload

from corpus_structure.semantic.claim_lifetime import ClaimFenceLost, maintained_claims
from corpus_structure.semantic.data_operation_admission import (
    AcquiredPreparedExecution,
    AcquiredPythonExecution,
    acquire_prepared_execution,
    acquire_python_execution,
    recheck_cached_execution,
)
from corpus_structure.semantic.data_operation_demands import DemandPlanner
from corpus_structure.semantic.data_operation_storage import DataOperationStorage


class NativeDemandUnit:
    def __init__(self, connection):
        self.connection = connection
        self.calls = DataOperationStorage(connection)

    def planner(self, model):
        return DemandPlanner(model, self.calls)

    def begin_nested(self):
        return self.connection.begin_nested()

    def hydrate(self, model, selection, **options):
        from corpus_structure.semantic.data_operation_consumers import hydrate_consumer_selection

        return hydrate_consumer_selection(self.connection, model, selection, **options)


class NativeDemandClaims:
    """Adapt callbacks once while retaining the production claim owner's lifecycle."""

    def __init__(self, owner):
        self.owner = owner
        self.lock = owner.lock
        self.active, self.uncertain, self.lost = owner.active, owner.uncertain, owner.lost

    def __call__(self):
        self.owner()

    def add_claim(self, claim):
        self.owner.add_claim(claim)

    def check_claim(self, claim):
        self.owner.check_claim(claim)

    def settle(self, claim, callback):
        return self.owner.settle(
            claim, lambda connection: callback(DataOperationStorage(connection))
        )

    def retain(self, claim, callback):
        return self.owner.retain(
            claim, lambda connection: callback(DataOperationStorage(connection))
        )


class NativeDemandIO:
    def __init__(self, engine, admission_engine):
        self.engine, self.admission_engine = engine, admission_engine

    @contextmanager
    def transaction(self):
        with self.engine.begin() as connection:
            yield NativeDemandUnit(connection)

    @contextmanager
    def claims(self, holder):
        def renew(connection, claim):
            result = DataOperationStorage(connection).renew_data_request(
                {**claim.fence, "lease_seconds": 300}
            )
            if result["state"] == "lost":
                raise ClaimFenceLost(claim, result["reason"])

        with maintained_claims(self.engine, (), holder, renew=renew) as owner:
            yield NativeDemandClaims(owner)

    def acquire_basis(self, host, release_id, runtime_id, **options):
        with self.engine.begin() as connection:
            return host.acquire_basis(self.engine, connection, release_id, runtime_id, **options)

    @overload
    def acquire_execution(
        self, basis, operation, *, prepared: Literal[True]
    ) -> AcquiredPreparedExecution: ...

    @overload
    def acquire_execution(
        self, basis, operation, *, prepared: Literal[False] = False
    ) -> AcquiredPythonExecution: ...

    def acquire_execution(self, basis, operation, *, prepared=False):
        acquire = acquire_prepared_execution if prepared else acquire_python_execution
        with self.admission_engine.begin() as connection:
            return acquire(
                connection,
                basis.prepared,
                basis.sources,
                operation,
                basis.runtime,
                schema=basis.schema,
                declarations=basis.declarations,
                captured_contracts=basis.captured_contracts,
            )

    def recheck_execution(self, basis, identity):
        with self.admission_engine.begin() as connection:
            recheck_cached_execution(connection, basis.prepared, basis.runtime, identity)
