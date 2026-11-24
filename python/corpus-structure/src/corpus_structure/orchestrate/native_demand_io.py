"""Native transactions, admission and claim custody for demand execution."""

from contextlib import contextmanager
from contextvars import copy_context
from threading import Event, Thread
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

    def retain(self, claim, callback, *, cancel_on_stop=False):
        if not cancel_on_stop:
            return self.owner.retain(
                claim, lambda connection: callback(DataOperationStorage(connection))
            )
        from corpus_structure.core.db.lifetime import BorrowerCancellation
        from corpus_structure.core.execution_control import check_execution_active

        cancellation = BorrowerCancellation()
        done = Event()
        failures = []

        def watch_stop():
            while not done.wait(0.05):
                try:
                    check_execution_active()
                    self.owner()
                except BaseException as error:
                    failures.append(error)
                    cancellation.request_cancel()
                    return

        context = copy_context()
        watcher = Thread(
            target=context.run, args=(watch_stop,), name="native-retain-stop", daemon=True
        )
        watcher.start()
        try:
            return self.owner.retain(
                claim,
                lambda connection: callback(
                    DataOperationStorage(connection, cancellation=cancellation)
                ),
                cancellation=cancellation,
            )
        except BaseException as error:
            for failure in failures:
                error.add_note("retention stop requested: " + repr(failure))
            raise
        finally:
            done.set()
            watcher.join()

    def retain_pdf_adoption(self, claim, callback, cancellation):
        """Serialize document adoption and lease maintenance on the same claim."""

        def adopt(connection):
            renewed = DataOperationStorage(connection).renew_data_request(
                {**claim.fence, "lease_seconds": 300}
            )
            if renewed["state"] == "lost":
                raise ClaimFenceLost(claim, renewed["reason"])
            return callback(connection)

        return self.owner.retain(claim, adopt, cancellation=cancellation)


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
