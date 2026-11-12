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


def _source_frontier(
    scheduled, pending, execute, *, prepare=lambda: True, prerequisites=lambda: False
):
    from corpus_structure.orchestrate.ready import SourceClaimFrontier

    policy = SimpleNamespace(
        max_claims=2, max_active_stage_runs=1, max_reply_bytes=8, max_packet_bytes=16
    )
    budget = OwnedByteBudget(64)
    admission = SourceAdmission(policy, budget)
    claimed = []

    def claim(method, config, identity):
        rows = pending[identity]
        if not rows:
            return ()
        task = rows.pop(0)
        claimed.append(task)
        return (task,)

    frontier = SourceClaimFrontier(
        [(SimpleNamespace(name=name), None, name) for name in scheduled],
        admission,
        claim=claim,
        execute=execute,
        prepare=prepare,
        has_prerequisites=prerequisites,
        capacity_wait=lambda method: None,
    )
    return frontier, admission, budget, claimed


def test_ordinary_source_refills_same_method_before_slow_other_method_finishes():
    early = Future()
    events = []
    handles = []
    pending = {"many": ["one", "two", "three"], "slow": ["slow"]}

    def execute(method, config, claimed, permit):
        (task,) = claimed
        future = early if task == "slow" else Future()
        if task != "slow":
            assert not early.done()
            future.set_result(task)
        events.append(("started", task))
        handle = Handle(future)
        handles.append(handle)
        (value,) = yield (PreparedWork(lambda: handle),)
        events.append(("settled", value))
        if task == "three":
            early.set_result("slow")

    frontier, admission, budget, claims = _source_frontier(("many", "slow"), pending, execute)
    drive_prepared_work(frontier.plan(), lambda: None)
    assert claims == ["one", "slow", "two", "three"]
    assert events.index(("settled", "three")) < events.index(("settled", "slow"))
    assert all(handle.retired and not handle.cancelled for handle in handles)
    assert frontier.permits == set()
    assert admission.used["claim"] == budget.used_bytes == 0


def test_ordinary_source_fills_same_method_window_and_replaces_individual_completion():
    first = Future()
    pending = {"many": ["one", "two", "three", "four"]}
    started = []

    def execute(method, config, claimed, permit):
        (task,) = claimed
        started.append(task)
        if task == "one":
            future = first
        else:
            future = Future()
            future.set_result(task)
        if task in {"two", "three", "four"}:
            assert not first.done()
        yield (PreparedWork(lambda: Handle(future)),)
        if task == "four":
            first.set_result("one")

    frontier, admission, budget, claims = _source_frontier(("many",), pending, execute)
    drive_prepared_work(frontier.plan(), lambda: None)
    assert started == claims == ["one", "two", "three", "four"]
    assert admission.used["claim"] == budget.used_bytes == 0


def test_source_frontier_waits_for_registration_capacity_without_blocking_sibling():
    ready = False
    pending = {"many": []}
    registered = False
    events = []

    def execute(method, config, claimed, permit):
        assert ready
        events.extend(claimed)
        if False:
            yield

    def prepare():
        nonlocal registered
        if not ready:
            events.append("registration-wait")
            return False
        if not registered:
            pending["many"].append("one")
            registered = True
        return True

    frontier, admission, budget, claims = _source_frontier(
        ("many",), pending, execute, prepare=prepare
    )

    def sibling():
        nonlocal ready
        future = Future()
        future.set_result("released")
        yield (PreparedWork(lambda: Handle(future)),)
        events.append("sibling-released")
        ready = True

    def operation():
        yield ReadyGroup((frontier.plan(), sibling()))

    drive_prepared_work(operation(), lambda: None)
    assert (
        events.index("registration-wait") < events.index("sibling-released") < events.index("one")
    )
    assert claims == ["one"]
    assert admission.used["claim"] == budget.used_bytes == 0


def test_source_frontier_stops_new_claims_after_failure_and_drains_useful_sibling():
    pending = {"failure": ["bad", "unclaimed"], "useful": ["retained"]}
    events = []

    def execute(method, config, claimed, permit):
        (task,) = claimed
        if task == "bad":
            raise ValueError("fenced task failure")
        future = Future()
        future.set_result(task)
        yield (PreparedWork(lambda: Handle(future)),)
        events.append(task)

    frontier, admission, budget, claims = _source_frontier(("failure", "useful"), pending, execute)
    with pytest.raises(ValueError, match="fenced task failure"):
        drive_prepared_work(frontier.plan(), lambda: None)
    assert claims == ["bad", "retained"]
    assert events == ["retained"]
    assert pending["failure"] == ["unclaimed"]
    assert admission.used["claim"] == budget.used_bytes == 0


def test_source_frontier_cancellation_releases_admitted_and_running_claims():
    pending = {"many": ["one", "two", "unclaimed"]}
    handles = []

    def execute(method, config, claimed, permit):
        handle = Handle(Future())
        handles.append(handle)
        yield (PreparedWork(lambda: handle),)

    frontier, admission, budget, claims = _source_frontier(("many",), pending, execute)

    def active():
        if len(handles) == 2 and all(handle.future.running() for handle in handles):
            raise RuntimeError("operation cancelled")
        if len(handles) == 2:
            for handle in handles:
                handle.future.set_running_or_notify_cancel()

    with pytest.raises(RuntimeError, match="operation cancelled"):
        drive_prepared_work(frontier.plan(), active)
    assert claims == ["one", "two"]
    assert all(handle.cancelled for handle in handles)
    assert admission.used["claim"] == budget.used_bytes == 0


def test_source_claim_waits_for_shared_bytes_with_zero_claims_then_sibling_releases():
    pending = {"many": ["one"]}
    events = []

    def execute(method, config, claimed, permit):
        events.extend(claimed)
        if False:
            yield

    frontier, admission, budget, claims = _source_frontier(("many",), pending, execute)
    budget.reserve(60)  # Existing CPU/provider/read ownership, independently of claims.
    assert admission.used["claim"] == 0
    assert frontier.admit() is None
    assert claims == []

    def sibling():
        future = Future()
        future.set_result("owned reply")
        yield (PreparedWork(lambda: Handle(future)),)
        events.append("bytes-released")
        budget.release(60)

    def operation():
        yield ReadyGroup((frontier.plan(), sibling()))

    drive_prepared_work(operation(), lambda: None)
    assert events == ["bytes-released", "one"]
    assert claims == ["one"]
    assert admission.used["claim"] == budget.used_bytes == 0


def test_one_source_claim_larger_than_complete_byte_policy_refuses_immediately():
    from corpus_structure.semantic.cpu_execution import CapacityExceeded

    policy = SimpleNamespace(max_claims=1, max_active_stage_runs=1, max_reply_bytes=17)
    owner = SourceAdmission(policy, OwnedByteBudget(16))
    with pytest.raises(CapacityExceeded, match="one complete source claim"):
        owner.try_take("claim")
    assert owner.used["claim"] == owner.budget.used_bytes == 0


def test_source_frontier_admits_smaller_useful_method_when_other_draft_waits():
    pending = {"text.compose_view": ["large"], "many": ["small"]}
    settled = []

    def execute(method, config, claimed, permit):
        (task,) = claimed
        settled.append(task)
        if task == "small":
            budget.release(52)
        if False:
            yield

    frontier, admission, budget, claims = _source_frontier(
        ("text.compose_view", "many"), pending, execute
    )
    budget.reserve(52)  # Twelve bytes left: ordinary draft fits, composer does not.
    small = frontier.admit()
    assert small is not None and claims == ["small"]
    drive_prepared_work(small, lambda: None)
    drive_prepared_work(frontier.plan(), lambda: None)
    assert settled == ["small", "large"]
    assert admission.used["claim"] == budget.used_bytes == 0


def test_registration_read_wait_still_admits_already_registered_useful_task():
    registration_ready = False
    pending = {"many": ["already-registered"]}
    settled = []

    def prepare():
        return registration_ready

    def execute(method, config, claimed, permit):
        nonlocal registration_ready
        assert not registration_ready
        settled.extend(claimed)
        registration_ready = True
        if False:
            yield

    frontier, admission, budget, claims = _source_frontier(
        ("many",), pending, execute, prepare=prepare
    )
    drive_prepared_work(frontier.plan(), lambda: None)
    assert claims == settled == ["already-registered"]
    assert registration_ready
    assert admission.used["claim"] == budget.used_bytes == 0
