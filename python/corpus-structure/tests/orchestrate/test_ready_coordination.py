"""Independent completion and admission, with source-order results and owned cleanup."""

from concurrent.futures import Future
from types import SimpleNamespace

import pytest

from corpus_structure.core.work import PreparedWork, ReadyGroup, drive_prepared_work
from corpus_structure.orchestrate.ready import SourceAdmission
from corpus_structure.semantic.cpu_execution import OwnedByteBudget


class Handle:
    def __init__(self, future):
        self.future, self.retired, self.cancelled = future, False, False
        self.check_active = lambda: None

    def collect(self):
        return self.future.result()

    def retire(self):
        self.retired = True
        return self.future.done()

    def cancel(self):
        self.cancelled = True
        self.future.cancel()


def test_later_completion_enables_follow_up_while_early_region_waits():
    early, later = Future(), Future()
    later.set_result("later-input")
    events = []
    handles = [Handle(early), Handle(later)]

    def first():
        (value,) = yield (PreparedWork(lambda: handles[0]),)
        events.append("early-done")
        return value

    def second():
        (value,) = yield (PreparedWork(lambda: handles[1]),)
        assert not early.done()
        assert value == "later-input"
        events.append("later-reduced")
        follow_up = Future()
        follow_up.set_result("later-output")
        (result,) = yield (PreparedWork(lambda: Handle(follow_up)),)
        events.append("later-settled")
        early.set_result("early-output")
        return result

    def invocation():
        return (yield ReadyGroup((first(), second()), max_active=2))

    assert drive_prepared_work(invocation(), lambda: None) == ("early-output", "later-output")
    assert events == ["later-reduced", "later-settled", "early-done"]
    assert all(handle.retired for handle in handles)


def test_one_failed_region_drains_independently_useful_sibling_before_propagation():
    events = []

    def failed():
        if False:
            yield
        raise ValueError("failed region")

    def useful():
        future = Future()
        future.set_result("retained")
        (result,) = yield (PreparedWork(lambda: Handle(future)),)
        events.append(result)
        return result

    def invocation():
        return (yield ReadyGroup((failed(), useful()), max_active=2))

    with pytest.raises(ValueError, match="failed region"):
        drive_prepared_work(invocation(), lambda: None)
    assert events == ["retained"]


def test_stage_and_claim_limits_precede_claim_and_release_draft_credit():
    policy = SimpleNamespace(max_active_stage_runs=2, max_claims=1, max_reply_bytes=8)
    budget = OwnedByteBudget(32)
    owner = SourceAdmission(policy, budget)
    stages = [owner.try_take("stage"), owner.try_take("stage")]
    assert owner.try_take("stage") is None
    claim = owner.try_take("claim")
    assert claim is not None
    assert budget.used_bytes == 8
    assert owner.try_take("claim") is None
    assert owner.try_work("claim") is None
    claim.release()
    assert budget.used_bytes == 0
    next_claim = owner.try_work("claim")
    assert next_claim is not None
    assert next_claim.collect().active
    assert next_claim.retire()  # Admission response retirement does not release task credit.
    assert budget.used_bytes == 8
    next_claim.collect().release()
    for stage in stages:
        assert stage is not None
        stage.release()
    assert owner.used == {"stage": 0, "claim": 0}
    assert budget.used_bytes == 0


def test_generator_handles_work_error_without_losing_its_own_cleanup():
    future = Future()
    future.set_exception(ValueError("invalid reply"))
    handle = Handle(future)

    def operation():
        try:
            yield (PreparedWork(lambda: handle),)
        except ValueError:
            return "explicit partial"

    assert drive_prepared_work(operation(), lambda: None) == "explicit partial"
    assert handle.cancelled and handle.retired


def test_lost_claim_cancels_pending_work_without_cancelling_useful_sibling():
    pending, useful = Future(), Future()
    useful.set_result("useful sibling")
    lost = Handle(pending)

    def current_claim():
        raise RuntimeError("claim renewal failed")

    lost.check_active = current_claim

    def stale_plan():
        try:
            yield (PreparedWork(lambda: lost),)
        except RuntimeError as error:
            assert str(error) == "claim renewal failed"
            return "stale discarded"

    def useful_plan():
        (value,) = yield (PreparedWork(lambda: Handle(useful)),)
        return value

    def invocation():
        return (yield ReadyGroup((stale_plan(), useful_plan()), max_active=2))

    assert drive_prepared_work(invocation(), lambda: None) == ("stale discarded", "useful sibling")
    assert lost.cancelled and pending.cancelled() and lost.retired


def test_fixed_capacity_stall_refuses_and_closes_plan_instead_of_waiting_forever():
    from corpus_structure.semantic.cpu_execution import CapacityExceeded

    budget = OwnedByteBudget(10)
    budget.reserve(8)  # Retained regional state has no running consumer that can release it.
    closed = []

    def submit():
        try:
            budget.reserve(5)
        except CapacityExceeded:
            return None
        pytest.fail("over-capacity work was admitted")

    def plan():
        try:
            yield (PreparedWork(submit),)
            pytest.fail("unsubmitted work returned a result")
        finally:
            closed.append(True)
            budget.release(8)

    with pytest.raises(RuntimeError, match="no in-flight work"):
        drive_prepared_work(plan(), lambda: None)
    assert closed == [True]
    assert budget.used_bytes == 0
