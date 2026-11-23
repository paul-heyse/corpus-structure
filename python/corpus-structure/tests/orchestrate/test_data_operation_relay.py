"""Nested ready plans retain actual physical handles through reduction and closure."""

from concurrent.futures import Future
from types import SimpleNamespace

import pytest

from corpus_structure.core.work import PreparedWork, ReadyGroup
from corpus_structure.orchestrate.data_operations import _RequestExecution


def request_owner():
    owner = object.__new__(_RequestExecution)
    owner.handles, owner.claims, owner.claim = [], (), None
    owner.invocation = SimpleNamespace(
        executor=SimpleNamespace(demand="demand"), physical_retired=False
    )
    owner.uncertain_submission = False
    owner.cpu = SimpleNamespace(reservation_retired=lambda _: True)
    owner.reservation = object()
    owner.running = False
    owner.hydrated_inputs = None
    owner.consumer_inputs, owner.consumer_results, owner.hydrated_sizes = {}, {}, {}
    return owner


class Handle:
    def __init__(self):
        self.future: Future[str] = Future()
        self.physically_retired = False

    def collect(self) -> str:
        return self.future.result()

    def cancel(self) -> None:
        self.future.cancel()

    def retire(self) -> bool:
        return self.physically_retired


def test_ready_group_relay_retains_all_handles_after_out_of_order_reduction():
    owner = request_owner()
    handles, closed = (Handle(), Handle()), []

    def child(index):
        try:
            (reply,) = yield (PreparedWork(lambda: handles[index]),)
            return (index, reply)
        finally:
            closed.append(index)

    def parent():
        return (yield ReadyGroup((child(0), child(1)), max_active=2))

    relay = owner.relay(parent())
    group = next(relay)
    assert isinstance(group, ReadyGroup) and group.max_active == 2
    children = group.plans
    for index, plan in enumerate(children):
        (work,) = next(plan)
        assert work.try_submit() is handles[index]
    assert owner.handles == list(handles) and not owner.retired()
    values = {}
    for index in (1, 0):
        handles[index].future.set_result("reply:" + str(index))
        with pytest.raises(StopIteration) as finished:
            children[index].send((handles[index].future.result(),))
        values[index] = finished.value.value
    with pytest.raises(StopIteration) as finished:
        relay.send(tuple(values[index] for index in (0, 1)))
    assert finished.value.value == ((0, "reply:0"), (1, "reply:1"))
    assert closed == [1, 0]
    # Logical reduction never supplies physical retirement or drops custody.
    assert not owner.retired() and owner.handles == list(handles)
    handles[0].physically_retired = True
    assert not owner.retired()
    handles[1].physically_retired = True
    assert owner.retired()


def test_closing_ready_group_child_preserves_unretired_submitted_handle():
    owner, handle, closed = request_owner(), Handle(), []

    def child():
        try:
            yield (PreparedWork(lambda: handle),)
        finally:
            closed.append("child")

    def parent():
        yield ReadyGroup((child(),), max_active=1)

    relay = owner.relay(parent())
    group = next(relay)
    assert isinstance(group, ReadyGroup)
    (nested,) = group.plans
    (work,) = next(nested)
    assert work.try_submit() is handle
    nested.close()
    relay.close()
    assert closed == ["child"]
    assert owner.handles == [handle] and not owner.retired()
    handle.physically_retired = True
    assert owner.retired()


def test_retained_failure_publishes_original_frames_then_releases_body_references(monkeypatch):
    import weakref

    from corpus_structure.cli import observation_logging
    from corpus_structure.cli.exception_observations import transform_exception
    from corpus_structure.core.process_lifetime import physical_retirement_uncertain
    from corpus_structure.core.work import PhysicalRetirementUncertain
    from corpus_structure.orchestrate.data_operations import NativeDemandExecutor

    references, events = [], []

    class Body:
        pass

    class NativeFailure(ValueError):
        sqlstate = "23514"

    def failed_hydration():
        body = Body()
        references.append(weakref.ref(body))
        try:
            raise NativeFailure("native diagnostic: request=opaque-request")
        except NativeFailure as native:
            raise ExceptionGroup(
                "native and retirement failures",
                [
                    native,
                    PhysicalRetirementUncertain("physical borrower is not joined"),
                ],
            ) from native

    def capture():
        try:
            failed_hydration()
        except Exception as failure:
            return failure

    failure = capture()
    assert references[0]() is not None and physical_retirement_uncertain(failure)

    def publish(event, **details):
        events.append((event, transform_exception(details["exc_info"])))

    monkeypatch.setattr(observation_logging, "logger", lambda _: SimpleNamespace(error=publish))
    retained = NativeDemandExecutor._retained_failure(failure, phase="hydration")
    assert retained is failure and references[0]() is None
    assert failure.__cause__ is not None
    assert failure.__traceback__ is None and failure.__cause__.__traceback__ is None
    assert isinstance(failure, ExceptionGroup)
    assert isinstance(failure.exceptions[0], NativeFailure)
    assert failure.exceptions[0].sqlstate == "23514"
    assert "opaque-request" in str(failure.exceptions[0])
    assert physical_retirement_uncertain(failure)
    trace = events[0][1].model_dump(mode="json")
    assert "failed_hydration" in str(trace)
    assert "opaque-request" in str(trace)
    assert "locals" not in str(trace)


def test_completed_request_drops_body_caches_only_after_physical_retirement():
    import weakref

    owner, handle = request_owner(), Handle()

    class Body:
        pass

    body = Body()
    reference = weakref.ref(body)
    owner.handles.append(handle)
    owner.consumer_inputs["member"] = body
    owner.consumer_results["member"] = body
    owner.hydrated_inputs = body
    owner.hydrated_sizes["member"] = 100
    del body
    assert not owner.release_retired_inputs() and reference() is not None
    handle.physically_retired = True
    owner.running = True  # Physical completion alone does not finish reduction.
    assert not owner.release_retired_inputs() and reference() is not None
    owner.running = False
    assert owner.release_retired_inputs() and reference() is None
    assert not owner.handles
    assert owner.hydrated_inputs is None and not owner.consumer_inputs
    assert not owner.consumer_results and not owner.hydrated_sizes


def test_retained_statement_error_drops_parameter_body_after_structured_publication(monkeypatch):
    import weakref

    from sqlalchemy.exc import StatementError

    from corpus_structure.cli import observation_logging
    from corpus_structure.cli.exception_observations import transform_exception
    from corpus_structure.orchestrate.data_operations import NativeDemandExecutor

    class Body:
        pass

    class NativeFailure(ValueError):
        sqlstate = "23514"

    body, original = Body(), NativeFailure("native constraint diagnostic")
    reference = weakref.ref(body)
    error = StatementError(
        "statement refused", "SELECT protected_writer(:p)", {"p": body}, original
    )
    del body
    events = []

    def publish(_event, **details):
        assert error.params is not None and reference() is not None
        events.append(transform_exception(details["exc_info"]))

    monkeypatch.setattr(observation_logging, "logger", lambda _: SimpleNamespace(error=publish))
    retained = NativeDemandExecutor._retained_failure(error, phase="settlement")
    assert retained is error and error.params is None and reference() is None
    assert error.orig is original and original.sqlstate == "23514"
    trace = events[0].model_dump(mode="json")
    assert trace["stacks"][0]["exc_type"] == "StatementError"
    assert trace["stacks"][0]["exc_value"].startswith("statement refused")
