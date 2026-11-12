"""Explicit lane admission, routing and lifecycle without mocked-provider passage claims."""

from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from threading import Event

import pytest

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.methods import characterization_resources as resources
from corpus_structure.semantic.cpu_execution import OwnedByteBudget
from corpus_structure.semantic.identity import canonical_bytes


@pytest.fixture
def runtime(monkeypatch):
    opened, closed = [], []

    class Worker:
        def __init__(self, active, device):
            self.active, self.closed = active, False
            self.requests = []
            self.startup = dict(
                runtime_identity={"runtime": "frozen"},
                assets={"artifact": 1},
                device=device,
                dtype="torch.bfloat16" if device == "cuda" else "torch.float32",
            )

        def infer(self, payload, *, check_active):
            self.active()
            check_active()
            self.requests.append(payload)
            if payload.get("prepare_bulk"):
                return dict(
                    outcome="prepared_batch",
                    members=[
                        dict(ordinal=i, text=sentence)
                        for i, sentence in enumerate(payload["sentences"])
                    ],
                )
            return payload

    @contextmanager
    def open_worker(**kwargs):
        assert kwargs["max_request_bytes"] == execution.policy.max_native_request_bytes
        assert kwargs["max_reply_bytes"] == execution.policy.max_native_reply_bytes
        worker = Worker(kwargs["check_active"], kwargs["device"])
        opened.append(worker)
        try:
            yield worker
        finally:
            worker.closed = True
            closed.append(worker)

    monkeypatch.setattr(resources, "_open_pm2_worker", open_worker)
    monkeypatch.setattr(
        resources,
        "_preflight_pm2_runtime",
        lambda **kwargs: dict(runtime_identity={"runtime": "frozen"}, assets={"artifact": 1}),
    )
    policy = CharacterizationExecutionPolicy(max_provider_jobs=2)
    execution = resources.ProviderExecution(OwnedByteBudget(policy.max_owned_bytes), policy)
    try:
        yield execution, opened, closed
    finally:
        execution.close()


def selection(provider="maverick", profile=b'{"provider":"maverick","device":"cpu"}'):
    return resources.PM2Selection(
        provider,
        Path("/fixture/python"),
        Path("/fixture/script"),
        Path("/fixture/project"),
        Path("/fixture/assets"),
        profile,
        b'{"runtime":"frozen"}',
        b'{"artifact":1}',
    )


def work(key, value, *, selected=None, active=lambda: None):
    return resources.PM2Work(selected or selection(), canonical_bytes(value), key, (active,))


def result(handle):
    handle.flush()
    handle.future.result(timeout=5)
    reply = handle.collect()
    handle.retire()
    return reply.payload


def test_exact_compatible_requests_share_resident_and_keep_private_correlation(runtime):
    execution, opened, closed = runtime
    first = execution.try_submit(work("one", {"value": 1}))
    assert result(first) == {"value": 1}
    second = execution.try_submit(work("two", {"value": 2}))
    assert result(second) == {"value": 2}
    assert len(opened) == 1
    assert not closed
    execution.close()
    assert closed == opened
    assert execution.budget.used_bytes == 0


def test_completed_reply_holds_byte_capacity_until_parent_retirement(runtime):
    execution, _, _ = runtime
    handle = execution.try_submit(work("one", {}))
    handle.flush()
    handle.future.result(timeout=5)
    before = execution.budget.used_bytes
    assert before > 0
    handle.collect()
    assert execution.budget.used_bytes == before
    handle.retire()
    assert execution.budget.used_bytes == 0


def test_native_lazy_admission_uses_native_limits_independently_of_cpu(runtime):
    execution, _, _ = runtime
    execution.policy = replace(
        execution.policy,
        max_packet_bytes=1,
        max_reply_bytes=1,
        max_native_request_bytes=1024,
        max_native_reply_bytes=2048,
    )
    request = work("native", {"body": "x" * 100})
    intent = execution.lazy_work(lambda: request, lane_key="maverick")
    handle = intent.try_submit()
    assert handle is not None
    assert execution.budget.used_bytes == execution._request_size(request) + 2048
    assert result(handle) == {"body": "x" * 100}
    assert execution.budget.used_bytes == 0


def test_native_request_and_reply_limits_are_enforced_independently(runtime):
    from corpus_structure.semantic.cpu_execution import CapacityExceeded

    execution, _, _ = runtime
    execution.policy = replace(execution.policy, max_native_request_bytes=16)
    with pytest.raises(CapacityExceeded, match="native request"):
        execution.try_submit(work("oversize", {"body": "x" * 100}))
    execution.policy = replace(
        execution.policy, max_native_request_bytes=1024, max_native_reply_bytes=16
    )
    handle = execution.try_submit(work("reply", {}))
    handle.flush()
    handle.future.result(timeout=5)
    assert handle.collect().error_type == "CapacityExceeded"
    handle.retire()
    assert execution.budget.used_bytes == 0


def test_one_exchange_and_one_pending_backpressure_instead_of_refusing_valid_work(runtime):
    execution, _, _ = runtime
    entered, release = Event(), Event()

    def active():
        entered.set()
        assert release.wait(timeout=5)

    first = execution.try_submit(work("one", {}, active=active))
    first.flush()
    assert entered.wait(timeout=5)
    second = execution.try_submit(work("two", {}))
    assert second is not None
    assert execution.try_submit(work("three", {})) is None
    release.set()
    assert result(first) == {}
    assert result(second) == {}


def test_profile_replacement_waits_for_active_owner_then_closes_old_resident(runtime):
    execution, opened, closed = runtime
    assert result(execution.try_submit(work("one", {}))) == {}
    changed = replace(
        selection(), profile=b'{"provider":"maverick","device":"cpu","options":"changed"}'
    )
    assert result(execution.try_submit(work("two", {}, selected=changed))) == {}
    assert len(opened) == 2 and closed == [opened[0]]


def test_stale_first_borrower_does_not_stop_useful_batch_member(runtime):
    execution, opened, _ = runtime

    def stale():
        raise RuntimeError("lost claim")

    request = resources.PM2Work(selection(), b"{}", "shared", (stale, lambda: None))
    assert result(execution.try_submit(request)) == {}
    assert len(opened) == 1


def test_frozen_artifact_mismatch_refuses_before_starting(runtime):
    execution, opened, _ = runtime
    changed = replace(selection(), artifacts=b'{"artifact":2}')
    handle = execution.try_submit(work("wrong", {}, selected=changed))
    handle.flush()
    handle.future.result(timeout=5)
    with pytest.raises(resources.Pm2WorkerRefused, match="frozen selection"):
        _ = handle.collect().payload
    handle.retire()
    assert not opened


def test_close_attempts_every_native_lane_when_one_closer_fails(runtime):
    execution, _, _ = runtime
    assert result(execution.try_submit(work("one", {}))) == {}
    other = replace(
        selection(), provider="d1", device="cuda", profile=b'{"provider":"d1","device":"cuda"}'
    )
    assert (
        result(execution.try_submit(work("two", {"batch": [{"state": "source"}]}, selected=other)))[
            "batch"
        ][0]["state"]
        == "source"
    )
    completed = []
    first = execution._lanes["maverick"]
    original = first.close

    def bad():
        original()
        raise RuntimeError("teardown failed")

    first.close = bad
    second = execution._lanes["cuda"]
    closer = second.close
    second.close = lambda: (closer(), completed.append("d1"))
    with pytest.raises(RuntimeError, match="teardown failed"):
        execution.close()
    assert completed == ["d1"]
    first.close = original


def test_explicit_flush_coalesces_ready_d1_requests_and_preserves_member_commitments(runtime):
    execution, opened, _ = runtime
    execution.coalescing_providers = frozenset({"d1"})
    selected = replace(
        selection(), provider="d1", device="cuda", profile=b'{"provider":"d1","device":"cuda"}'
    )
    first = execution.try_submit(work("one", {"batch": [{"state": "first"}]}, selected=selected))
    second = execution.try_submit(work("two", {"batch": [{"state": "second"}]}, selected=selected))
    assert not opened  # Admission only; no timing-based dispatch window.
    first.flush()
    one, two = result(first), result(second)
    assert len(opened[0].requests) == 1
    assert one["batch"][0]["state"] == "first"
    assert two["batch"][0]["state"] == "second"
    a, b = one["batch"][0]["batch_receipt"], two["batch"][0]["batch_receipt"]
    assert a["digest"] == b["digest"]
    assert (a["member_ordinal"], b["member_ordinal"]) == (0, 1)


def test_cancelled_queued_work_releases_owned_body_without_dispatch(runtime):
    execution, opened, _ = runtime
    handle = execution.try_submit(work("one", {}))
    handle.cancel()
    assert handle.retire()
    assert not execution._lanes["maverick"].pending
    assert execution.budget.used_bytes == 0
    assert not opened


def test_gliner_coalescing_refuses_bad_logical_input_before_enqueue_and_preserves_valid(
    runtime, monkeypatch, tmp_path
):
    from dataclasses import dataclass

    from corpus_structure.methods.gliner import (
        GlinerInput,
        GlinerPack,
        GlinerProfile,
        GlinerRefused,
    )
    from corpus_structure.methods.gliner_worker import GlinerAdmission

    calls = []

    @dataclass(frozen=True)
    class Report:
        context_id: str

    class Worker:
        closed = False

        def __init__(self, profile):
            pass

        def prepare_members(self, pack, inputs, **kwargs):
            calls.append(("prepare", tuple(item.context_id for item in inputs)))
            return tuple(
                GlinerAdmission(
                    i,
                    item.context_id,
                    item.context_digest,
                    item.context_id != "native-refused",
                    "native word bound" if item.context_id == "native-refused" else None,
                )
                for i, item in enumerate(inputs)
            )

        def extract(self, pack, inputs, **kwargs):
            calls.append(("infer", tuple(item.context_id for item in inputs)))
            return tuple(Report(item.context_id) for item in inputs)

        def close(self):
            self.closed = True

    monkeypatch.setattr(resources, "GlinerWorker", Worker)
    execution, _, _ = runtime
    execution.coalescing_providers = frozenset({"gliner"})
    profile = GlinerProfile(
        tmp_path.absolute(),
        "fixture",
        "pinned",
        tuple(
            (name, "a" * 64)
            for name in (
                "config.json",
                "encoder_config/config.json",
                "model.safetensors",
                "tokenizer.json",
                "tokenizer_config.json",
            )
        ),
    )
    profile = replace(profile, version="gliner2-2.1.0-cpu-fp32-standard-whitespace-v1")
    pack = GlinerPack("release", "1", "{}")

    def request(identity, text):
        return resources.GLiNERWork(
            profile,
            pack,
            (GlinerInput(identity, "a" * 64, text),),
            0.5,
            "flat",
            identity,
            (lambda: None,),
        )

    native_bad = execution.try_submit(request("native-refused", "short invalid native preparation"))
    good = execution.try_submit(request("good", "X is given"))
    used = execution.budget.used_bytes
    with pytest.raises(GlinerRefused, match="input byte bound"):
        execution.try_submit(request("oversized", "X" * 32769))
    assert execution.budget.used_bytes == used
    assert len(execution._lanes["gliner"].pending) == 2
    good.flush()
    native_bad.future.result(timeout=5)
    good.future.result(timeout=5)
    assert native_bad.collect().error_type == "GlinerRefused"
    assert good.collect().reports == (Report("good"),)
    assert calls == [("prepare", ("native-refused", "good")), ("infer", ("good",))]
    native_bad.retire()
    good.retire()


def test_unsubmitted_provider_intent_is_charged_and_abandoned_without_native_work(runtime):
    execution, opened, _ = runtime
    intent = execution.work(work("pending", {"value": "retained"}))
    assert execution.budget.used_bytes > 0
    intent.abandon()
    assert execution.budget.used_bytes == 0
    assert not opened
    another = execution.work(work("owned", {"value": "retained"}))
    handle = another.try_submit()
    another.abandon()  # Ownership was transferred; this must not release it twice.
    assert result(handle) == {"value": "retained"}
    assert execution.budget.used_bytes == 0


def test_lazy_production_intent_waits_for_transient_budget_before_serializing(runtime):
    execution, _, _ = runtime
    entered, release = Event(), Event()

    def active():
        entered.set()
        assert release.wait(timeout=5)

    first = execution.try_submit(work("active", {"value": "in flight"}, active=active))
    first.flush()
    assert entered.wait(timeout=5)
    remaining = execution.budget.limit - execution.budget.used_bytes
    execution.budget.reserve(remaining)  # A concurrent CPU/regional reservation.
    materialized = []

    def factory():
        materialized.append(True)
        return work("later", {"value": "after admission"})

    intent = execution.lazy_work(factory, lane_key="maverick")
    try:
        assert intent.try_submit() is None
        assert not materialized
        assert not first.future.done()  # A real active future can release pressure.
    finally:
        execution.budget.release(remaining)
        release.set()
    second = intent.try_submit()
    assert second is not None
    assert materialized == [True]
    intent.abandon()  # Successful submission transferred ownership to the handle.
    assert result(first) == {"value": "in flight"}
    assert result(second) == {"value": "after admission"}
    assert execution.budget.used_bytes == 0


def test_abandoned_lazy_intent_never_materializes_or_reserves_body(runtime):
    execution, opened, _ = runtime
    materialized = []
    intent = execution.lazy_work(lambda: materialized.append(True), lane_key="maverick")
    assert execution.budget.used_bytes == 0
    intent.abandon()
    with pytest.raises(ValueError, match="abandoned"):
        intent.try_submit()
    assert not materialized and not opened


def test_d1_client_defaults_to_cuda_and_cpu_requests_refuse_before_admission(runtime):
    from types import SimpleNamespace

    execution, opened, _ = runtime
    ctx = SimpleNamespace(
        check_active=lambda: None, settings=SimpleNamespace(nemotron_endpoint=None)
    )
    arguments = dict(
        provider="d1",
        assets=Path("/fixture/assets"),
        runtime={"runtime": "frozen"},
        artifacts={"artifact": 1},
    )
    client = resources.pm2_client(execution, ctx, **arguments)
    assert client.selection_factory().device == "cuda"
    with pytest.raises(resources.Pm2WorkerRefused, match="requires CUDA"):
        resources.pm2_client(execution, ctx, **arguments, device="cpu")
    with pytest.raises(ValueError, match="requires CUDA"):
        replace(selection(), provider="d1", device="cpu")
    assert not opened
    assert execution.budget.used_bytes == 0


def test_native_client_cohort_and_reply_preserve_declared_question_option_and_state_order(runtime, monkeypatch):
    import json
    from hashlib import sha256
    from types import SimpleNamespace

    from corpus_structure.core.method import ReadyGroup, drive_prepared_work
    from corpus_structure.methods.model_observation import validate_pm2_batch_receipt
    from corpus_structure.methods.pm2_worker import _encode_request

    execution, opened, _ = runtime
    execution.coalescing_providers = frozenset({"d1"})
    ctx = SimpleNamespace(
        check_active=lambda: None, settings=SimpleNamespace(nemotron_endpoint=None)
    )
    arguments = dict(
        provider="d1",
        assets=Path("/fixture/assets"),
        runtime={"runtime": "frozen"},
        artifacts={"artifact": 1},
    )
    session = SimpleNamespace(requests=[])
    opened.append(session)
    monkeypatch.setattr(execution.native_group, "startup", lambda selected, active: dict(runtime_identity={"runtime": "frozen"}, assets={"artifact": 1}, device="cuda", dtype="torch.bfloat16"))

    def infer(selected, payload, active):
        active()
        session.requests.append(payload)
        return payload

    monkeypatch.setattr(execution.native_group, "infer", infer)
    clients = [resources.pm2_client(execution, ctx, **arguments) for _ in range(2)]
    member = {
        "state": {"z_state": "first", "a_state": "second"},
        "questions": {
            "z_question": {
                "type": "choice",
                "criteria": {"z_option": "first", "a_option": "second"},
            },
            "a_question": {"type": "text"},
        },
    }

    def plan():
        return (yield ReadyGroup(tuple(client.infer({"batch": [member]}) for client in clients)))

    replies = drive_prepared_work(plan(), ctx.check_active)
    assert len(opened[0].requests) == 1
    wire = json.loads(_encode_request(1, opened[0].requests[0], 1_048_576))["payload"]
    for native in wire["batch"]:
        assert tuple(native["state"]) == ("z_state", "a_state")
        assert tuple(native["questions"]) == ("z_question", "a_question")
        assert tuple(native["questions"]["z_question"]["criteria"]) == ("z_option", "a_option")
    for ordinal, reply in enumerate(replies):
        native = reply["batch"][0]
        assert tuple(native["state"]) == ("z_state", "a_state")
        assert tuple(native["questions"]) == ("z_question", "a_question")
        assert tuple(native["questions"]["z_question"]["criteria"]) == ("z_option", "a_option")
        receipt = native["batch_receipt"]
        expected = sha256(
            json.dumps(member, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        assert receipt["version"] == 2
        assert receipt["members"][ordinal] == expected
        validate_pm2_batch_receipt(receipt, member, "d1")
        reordered = {**member, "questions": dict(reversed(tuple(member["questions"].items())))}
        with pytest.raises(ValueError, match="exact request"):
            validate_pm2_batch_receipt(receipt, reordered, "d1")
        reordered_options = {
            **member,
            "questions": {
                **member["questions"],
                "z_question": {
                    **member["questions"]["z_question"],
                    "criteria": dict(
                        reversed(tuple(member["questions"]["z_question"]["criteria"].items()))
                    ),
                },
            },
        }
        with pytest.raises(ValueError, match="exact request"):
            validate_pm2_batch_receipt(receipt, reordered_options, "d1")


def test_historical_v1_pm2_receipt_keeps_original_canonical_hash_semantics():
    from hashlib import sha256

    from corpus_structure.methods.model_observation import validate_pm2_batch_receipt

    header = dict(provider="d1", profile="a" * 64, runtime="b" * 64)
    member = {"z": 1, "a": 2}
    members = [sha256(canonical_bytes(member)).hexdigest()]
    receipt = dict(
        version=1,
        header=header,
        members=members,
        digest=sha256(canonical_bytes([header, members])).hexdigest(),
        member_ordinal=0,
    )
    validate_pm2_batch_receipt(receipt, dict(reversed(tuple(member.items()))), "d1")
    with pytest.raises(ValueError, match="exact request"):
        validate_pm2_batch_receipt({**receipt, "version": True}, member, "d1")


@pytest.mark.parametrize("provider", ["d1", "hanlp"])
@pytest.mark.parametrize("fits", [False, True])
def test_pm2_coalescing_admits_exact_merged_utf8_wire_frame(runtime, provider, fits):
    import json

    execution, opened, _ = runtime
    selected = replace(
        selection(),
        provider=provider,
        device="cuda" if provider == "d1" else "cpu",
        profile=canonical_bytes(
            dict(provider=provider, device="cuda" if provider == "d1" else "cpu")
        ),
    )
    key = "batch" if provider == "d1" else "sentences"
    members = (
        ([{"state": "é" * 200}], [{"state": "界" * 200}])
        if provider == "d1"
        else (
            [["é" * 200]],
            [["界" * 200]],
        )
    )
    options = {} if provider == "d1" else {"prepare_bulk": True}
    payloads = [{**options, key: value} for value in members]
    merged = {**options, key: [value for member in members for value in member]}
    # Independent actual wire representation, including framing, UTF-8 and newline.
    frame = (
        json.dumps(
            dict(kind="infer", request_id=1, payload=merged),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode()
        + b"\n"
    )
    execution.policy = replace(execution.policy, max_native_request_bytes=len(frame) - (not fits))
    handles = [
        execution.try_submit(work(str(i), payload, selected=selected))
        for i, payload in enumerate(payloads)
    ]
    held = execution.budget.used_bytes
    assert held > 0
    handles[0].flush()
    replies = []
    for handle in handles:
        handle.future.result(timeout=5)
        replies.append(handle.collect().payload)
    # Collected replies and their original request credits stay owned until retirement.
    assert execution.budget.used_bytes == held
    assert len(opened[0].requests) == (1 if fits else 2)
    if provider == "d1":
        assert [reply["batch"][0]["state"] for reply in replies] == ["é" * 200, "界" * 200]
        receipts = [reply["batch"][0]["batch_receipt"] for reply in replies]
        assert [receipt["member_ordinal"] for receipt in receipts] == ([0, 1] if fits else [0, 0])
        assert (receipts[0]["digest"] == receipts[1]["digest"]) == fits
    else:
        assert [[member["text"] for member in reply["members"]] for reply in replies] == list(
            members
        )
    for handle in handles:
        handle.retire()
    assert execution.budget.used_bytes == 0


@pytest.mark.parametrize("threads,interop", [(2, 1), (4, 2)])
@pytest.mark.parametrize("route", ["eager", "intent", "lazy"])
def test_gliner_frozen_thread_mismatch_refuses_shared_admission_before_startup(
    runtime, monkeypatch, threads, interop, route
):
    from semantic.test_model_characterization import gliner_profile

    from corpus_structure.methods.gliner import GlinerInput, GlinerPack, GlinerRefused

    execution, _, _ = runtime
    execution.policy = replace(
        execution.policy,
        provider_threads=threads,
        provider_interop_threads=interop,
    )
    monkeypatch.setattr(
        resources, "GlinerWorker", lambda *args: pytest.fail("launched mismatched profile")
    )
    request = resources.GLiNERWork(
        gliner_profile().profile,
        GlinerPack("release", "1", "{}"),
        (GlinerInput("context", "a" * 64, "source"),),
        0.5,
        "flat",
        "one",
        (lambda: None,),
    )
    with pytest.raises(GlinerRefused, match="threads/inter-op"):
        if route == "eager":
            execution.try_submit(request)
        elif route == "intent":
            execution.work(request)
        else:
            execution.lazy_work(lambda: request, lane_key="gliner").try_submit()
    assert not execution._handles
    assert all(not lane.pending and lane.worker is None for lane in execution._lanes.values())
    assert execution.budget.used_bytes == 0


def test_pm2_combined_frame_fit_uses_actual_next_resident_request_ordinal(runtime):
    import json

    execution, opened, _ = runtime
    selected = replace(
        selection(), provider="d1", device="cuda", profile=b'{"provider":"d1","device":"cuda"}'
    )
    startup = execution.try_submit(resources.PM2Work(selected, None, "startup", (lambda: None,)))
    assert result(startup) == {}
    opened[0].next_request_id = 10
    first_payload = {"batch": [{"state": "a" * 200}]}
    second_payload = {"batch": [{"state": "b" * 200}]}
    merged = {"batch": [*first_payload["batch"], *second_payload["batch"]]}
    frame = (
        json.dumps(dict(kind="infer", request_id=1, payload=merged), separators=(",", ":")).encode()
        + b"\n"
    )
    execution.policy = replace(execution.policy, max_native_request_bytes=len(frame))
    first = execution.try_submit(work("one", first_payload, selected=selected))
    second = execution.try_submit(work("two", second_payload, selected=selected))
    first.flush()
    assert result(first)["batch"][0]["state"] == "a" * 200
    assert result(second)["batch"][0]["state"] == "b" * 200
    assert len(opened[0].requests) == 2
