"""Pure controls for the unselected host checkpoint; no model/provider/GPU launches."""

import json
from concurrent.futures import Future
from contextlib import contextmanager
from pathlib import Path
from threading import BoundedSemaphore, Lock
from typing import Any

import pytest

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.methods import native_host
from corpus_structure.methods.native_host_worker import _load
from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection
from corpus_structure.methods.pm2_worker import Pm2WorkerError, Pm2WorkerRefused


def selection(provider="d1", **changes):
    values: dict[str, Any] = dict(
        provider=provider,
        runtime_identity={},
        artifacts={},
        parameters={},
        dtype="bfloat16" if provider == "d1" else "float32",
        backend="fixture",
    )
    return NativeSelection(NativeProfile(**{**values, **changes}), Path("/fixture-assets"))


def test_profile_rejects_cpu_or_changed_precision_without_loading_any_provider():
    with pytest.raises(ValueError, match="CUDA provider"):
        selection(device="cpu")
    with pytest.raises(ValueError, match="dtype"):
        selection(dtype="float32")
    value = selection().native
    assert NativeProfile.from_content(value.content) == value
    assert NativeSelection(value, Path("/other-assets")).native.fingerprint == value.fingerprint


def test_host_frame_fit_includes_unicode_and_all_multiplex_headers():
    selected = selection()
    body = {"batch": [{"state": "é界"}]}
    message = native_host.inference_frame("a" * 32, "b" * 32, selected, body)
    expected = (
        json.dumps(message, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
        + b"\n"
    )
    assert native_host.host_request_frame_size(selected, body, len(expected)) == len(expected)
    assert native_host.encode_host_frame(message, len(expected)) == expected
    with pytest.raises(Pm2WorkerRefused, match="frame byte bound"):
        native_host.host_request_frame_size(selected, body, len(expected) - 1)


def test_reader_routes_out_of_order_and_fences_only_unfinished_generation_members():
    host = native_host.NativeHost.__new__(native_host.NativeHost)
    host.generation, host._lock, host._failure, host._accepting = "a" * 32, Lock(), None, True
    host._ready = Future()
    host._ready.set_result({})
    first, second = selection(), selection("maverick")
    futures = [Future(), Future()]
    permits = [BoundedSemaphore(1), BoundedSemaphore(1)]
    for permit in permits:
        assert permit.acquire(False)
    host._pending = {
        str(i): native_host._Pending(selected, future, permit)
        for i, (selected, future, permit) in enumerate(
            zip((first, second), futures, permits, strict=True)
        )
    }
    host._route(
        dict(
            kind="result",
            generation=host.generation,
            request_id="1",
            provider=second.provider,
            profile=second.native.fingerprint,
            payload={"value": "second"},
        )
    )
    assert futures[1].result() == {"value": "second"} and not futures[0].done()
    with pytest.raises(Pm2WorkerError, match="generation") as failure:
        host._route(dict(kind="result", generation="wrong", request_id="0"))
    host._fail(failure.value)
    with pytest.raises(Pm2WorkerError, match="generation"):
        futures[0].result()
    assert futures[1].result() == {"value": "second"}
    assert all(permit.acquire(False) for permit in permits)


def test_declared_group_is_lazy_and_keeps_custody_until_host_death_is_proven(monkeypatch):
    events, hosts = [], []

    @contextmanager
    def custody(endpoint, *, check_active):
        check_active()
        events.append("lease-enter")
        try:
            yield
        finally:
            events.append("lease-exit")

    class Host:
        def __init__(self, selections, policy, *, check_active, adopt):
            check_active()
            self.name = selections[0].native.host
            self.failed_once = self.name == "primary"
            hosts.append(self)
            adopt(self)
            self.startup = {entry.native.fingerprint: {} for entry in selections}

        def close(self):
            events.append("close-" + self.name)
            if self.failed_once:
                self.failed_once = False
                raise RuntimeError("death unproven")

    monkeypatch.setattr(native_host, "suspend_resident_nemotron", custody)
    group = native_host.NativeHostGroup(CharacterizationExecutionPolicy(), host_factory=Host)
    values = (selection(), selection("maverick"))
    group.declare(values)
    group.declare(values)
    assert not hosts and events == []
    group.ensure(lambda: None)
    assert {host.name for host in hosts} == {"primary"}
    with pytest.raises(Pm2WorkerRefused, match="not declared"):
        group.declare((selection(parameters={"new": True}),))
    with pytest.raises(Pm2WorkerError, match="unproven"):
        group.close()
    assert events == ["lease-enter", "close-primary"]
    group.close()
    group.close()
    assert events[-2:] == ["close-primary", "lease-exit"]


def test_real_adapter_rejects_missing_profile_before_model_loading():
    with pytest.raises(KeyError, match="assets"):
        _load({"profile": {"provider": "gliner"}}, None)


def test_profile_nested_aliases_and_returned_declarations_cannot_change_identity():
    runtime = {"versions": [{"torch": "selected"}]}
    artifacts = {"files": {"weights": ["original"]}}
    parameters = {"decoder": {"thresholds": [0.5]}}
    selected = selection(runtime_identity=runtime, artifacts=artifacts, parameters=parameters)
    content, identity, declaration = selected.profile, selected.identity, selected.declaration()
    runtime["versions"][0]["torch"] = "changed"
    artifacts["files"]["weights"].append("changed")
    parameters["decoder"]["thresholds"][0] = 0.9
    selected.native.runtime_identity["versions"][0]["torch"] = "another-change"
    selected.native.artifacts["files"].clear()
    selected.native.parameters["decoder"].clear()
    exposed = selected.declaration()
    exposed["profile"]["runtime_identity"].clear()
    assert selected.profile == content and selected.identity == identity
    assert selected.declaration() == declaration
    assert json.loads(selected.runtime) == {"versions": [{"torch": "selected"}]}
    assert json.loads(selected.artifacts) == {"files": {"weights": ["original"]}}


def test_partial_constructor_remains_owned_when_cleanup_is_unproven(monkeypatch):
    events = []

    @contextmanager
    def custody(endpoint, *, check_active):
        events.append("lease-enter")
        try:
            yield
        finally:
            events.append("lease-exit")

    class PartialHost:
        def __init__(self, selections, policy, *, check_active, adopt):
            self.refuse_cleanup = True
            adopt(self)
            raise RuntimeError("startup failed after spawn")

        def close(self):
            events.append("close")
            if self.refuse_cleanup:
                self.refuse_cleanup = False
                raise RuntimeError("physical death not proven")

    monkeypatch.setattr(native_host, "suspend_resident_nemotron", custody)
    group = native_host.NativeHostGroup(CharacterizationExecutionPolicy(), host_factory=PartialHost)
    group.declare((selection(),))
    with pytest.raises(RuntimeError, match="startup failed"):
        group.ensure(lambda: None)
    assert "primary" in group._hosts
    with pytest.raises(Pm2WorkerError, match="unproven"):
        group.close()
    assert events == ["lease-enter", "close"]
    group.close()
    assert events == ["lease-enter", "close", "close", "lease-exit"]


def test_cancelled_startup_borrower_does_not_wait_for_shared_ready():
    from concurrent.futures import CancelledError

    group = native_host.NativeHostGroup(CharacterizationExecutionPolicy())
    group._ready = Future()

    def cancelled():
        raise CancelledError("logical borrower cancelled")

    with pytest.raises(CancelledError, match="logical borrower"):
        group.ensure(cancelled)
    assert not group._ready.done()
    assert not group._stop.is_set()


def test_conflicting_host_cache_declaration_refuses_atomically_before_custody():
    group = native_host.NativeHostGroup(CharacterizationExecutionPolicy())
    first = selection()
    other = NativeSelection(selection("hanlp").native, Path("/other-assets"))
    with pytest.raises(Pm2WorkerRefused, match="one offline backbone cache"):
        group.declare((first, other))
    assert group._selections == {}
    assert group._thread is None


@pytest.mark.parametrize("provider", ["d1", "hanlp", "maverick", "dipo"])
def test_shared_pm2_adapters_authenticate_and_delegate_without_global_retuning(
    provider, tmp_path, monkeypatch
):
    from corpus_structure.methods import native_host_adapters

    calls = []
    observed = {
        "device": "cuda:0",
        "dtype": "torch.bfloat16" if provider == "d1" else "torch.float32",
        "attention_implementation": "sdpa",
    }
    runtime, artifacts = {"lock": "shared-runtime", "python": "3.14.10"}, {"checkpoint": "exact"}

    def loader(assets, device):
        calls.append((provider, assets, device))
        return dict(observed), lambda request: {"native": request}

    def run(path):
        if Path(path).name == "pm2_native.py":
            return {
                "_runtime_identity": lambda selected, *, project: runtime,
                "_verify_assets": lambda assets, selected: artifacts,
                "_load_d1": loader,
                "_RUNTIME_PACKAGES": {provider: {"library": "selected"}},
            }
        return {"load_" + provider: loader}

    monkeypatch.setattr(native_host_adapters.runpy, "run_path", run)
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path / "hub"))
    profile = dict(
        provider=provider,
        runtime_identity=runtime,
        artifacts=artifacts,
        backend="sdpa",
        parameters={"adapter": "pm2-native-1"},
    )
    from types import SimpleNamespace

    torch = SimpleNamespace(
        __version__="selected",
        version=SimpleNamespace(cuda="selected"),
        cuda=SimpleNamespace(get_device_name=lambda: "fixture"),
    )
    metadata, infer = native_host_adapters.load(
        {"profile": profile, "assets": str(tmp_path)}, torch
    )
    assert calls == [(provider, tmp_path, "cuda")]
    assert metadata["runtime_identity"] == runtime and metadata["assets"] == artifacts
    assert metadata["attention_implementation"] == "sdpa"
    assert infer({"ordered": [2, 1]}) == {"native": {"ordered": [2, 1]}}
    profile["runtime_identity"] = {"lock": "foreign"}
    with pytest.raises(ValueError, match="runtime differs"):
        native_host_adapters.load({"profile": profile, "assets": str(tmp_path)}, object())
    assert len(calls) == 1


def test_direct_spacy_facade_loads_only_tokenizer_and_closes_phase_preserving_doc_constraints(
    monkeypatch,
):
    import base64

    import spacy
    from spacy.tokens import Doc

    from corpus_structure.ingest.hosted_spacy import HostedPipeline
    from corpus_structure.ingest.sentences import SentenceConfig

    pipeline = HostedPipeline(SentenceConfig())
    assert pipeline._base.pipe_names == []
    declared = selection("spacy")
    monkeypatch.setattr(pipeline, "selection", lambda: declared)
    events = []

    class Group:
        def __init__(self, policy, endpoint=None):
            assert endpoint == "http://127.0.0.1:8035/v1"

        def __enter__(self):
            events.append("enter")
            return self

        def __exit__(self, *error):
            events.append("exit")

        def declare(self, population):
            assert population == (declared,)

        def startup(self, selected, active):
            return dict(
                native_configuration=pipeline.config.to_str(),
                components=[
                    dict(name=name, factory=pipeline.get_pipe_meta(name).factory)
                    for name in pipeline.pipe_names
                ],
            )

        def infer(self, selected, payload, active):
            events.append("infer")
            doc = Doc(spacy.blank("en").vocab).from_bytes(
                base64.b64decode(payload["documents"][0]["content"])
            )
            assert doc[1].tag_ == "NNP" and doc[1].is_sent_start is False
            return {"documents": [base64.b64encode(doc.to_bytes()).decode("ascii")]}

    monkeypatch.setattr(native_host, "NativeHostGroup", Group)
    doc = Doc(pipeline.vocab, words=["Let", "x+y"], spaces=[True, False])
    doc[1].tag_ = "NNP"
    doc[1].is_sent_start = False
    [(restored, marker)] = list(pipeline.pipe([(doc, "exact-input")], as_tuples=True))
    assert restored.text == "Let x+y" and marker == "exact-input"
    assert events == ["enter", "infer", "exit"]


def test_analytical_gliner_borrows_frozen_population_without_new_runtime_or_custody(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace

    from corpus_structure.methods import native_host_clients
    from corpus_structure.methods.gliner import GlinerProfile
    from corpus_structure.methods.native_profiles import gliner_selection

    profile = GlinerProfile(
        tmp_path,
        "fixture",
        "immutable",
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
    frozen = gliner_selection(profile, {"runtime": "frozen-before-task"})
    declarations, closed = [], []
    group = SimpleNamespace(
        _selections={frozen.native.fingerprint: frozen},
        declare=lambda values: declarations.extend(values),
        close=lambda: closed.append(True),
    )
    monkeypatch.setattr(
        native_host_clients,
        "preflight_native_runtime",
        lambda *_args: pytest.fail("borrower repeated frozen runtime acquisition"),
    )
    borrower = native_host_clients.HostedGliner(
        profile, group=group, native_profile=frozen.native.wire
    )
    assert borrower.selection.native == frozen.native
    borrower.close()
    assert declarations == [frozen] and closed == []
    changed = frozen.native.wire
    changed["parameters"]["gliner_profile"]["max_words"] += 1
    with pytest.raises(ValueError, match="frozen native execution"):
        native_host_clients.HostedGliner(profile, group=group, native_profile=changed)
    assert declarations == [frozen]


def test_selected_domain_profile_freezes_once_and_none_preserves_old_config_shape(tmp_path):
    from types import SimpleNamespace

    from corpus_structure.methods.characterization_resources import freeze_analytical_profile
    from methods.test_m1_source_profile import config

    value = config(tmp_path)
    parameters = value.model_dump(mode="json")
    assert "native_execution_profile" not in parameters
    cache = {("gliner-runtime", str(tmp_path.absolute())): {"runtime": "operation-snapshot"}}
    frozen = freeze_analytical_profile(
        "extract.m1_candidates", parameters, SimpleNamespace(), cache=cache
    )
    assert frozen is not None
    assert parameters["native_execution_profile"] == frozen.native.wire
    assert (
        freeze_analytical_profile(
            "extract.m1_candidates", parameters, SimpleNamespace(), cache=cache
        )
        == frozen
    )


def test_spacy_placement_permits_only_native_upper_cpu_arrays():
    from types import SimpleNamespace

    import numpy

    from corpus_structure.methods.native_host_adapters import _spacy_placement

    class GPUArray:
        dtype = numpy.dtype("float32")
        shape = (2, 3)

    class Node:
        param_names = ("W",)

        def __init__(self, name, array):
            self.name, self.array = name, array

        def has_param(self, name):
            return True

        def get_param(self, name):
            return self.array

        def walk(self):
            return [self]

    lower = Node("lower", GPUArray())
    upper = Node("upper", numpy.zeros((2, 3), dtype="float32"))
    model = SimpleNamespace(
        attrs={"has_upper": True},
        has_ref=lambda name: name == "upper",
        get_ref=lambda name: upper,
        walk=lambda: [lower, upper],
    )
    nlp = SimpleNamespace(
        pipeline=[("parser", SimpleNamespace(model=model))],
        config={
            "components": {
                "parser": {
                    "model": {"@architectures": "spacy.TransitionBasedParser.v2", "use_upper": True}
                }
            }
        },
        get_pipe_meta=lambda name: SimpleNamespace(factory="parser"),
    )
    xp = SimpleNamespace(ndarray=GPUArray, float32=numpy.float32)
    count, native_cpu = _spacy_placement(nlp, xp, numpy)
    assert count == 1 and [
        (row["node"], row["parameter"], row["reason"]) for row in native_cpu
    ] == [("upper", "W", "spacy-transition-native-cpu-upper")]
    lower.array = numpy.zeros((2, 3), dtype="float32")
    with pytest.raises(RuntimeError, match=r"parser/lower/W.*numpy.ndarray"):
        _spacy_placement(nlp, xp, numpy)
    lower.array = GPUArray()
    nlp.config["components"]["parser"]["model"]["use_upper"] = False
    with pytest.raises(RuntimeError, match="parser/upper/W"):
        _spacy_placement(nlp, xp, numpy)


@pytest.fixture
def physical_host():
    import sys

    peers = []

    def create(*population, **changes):
        policy = CharacterizationExecutionPolicy(max_native_reply_bytes=4096)
        host = native_host.NativeHost(
            population or (selection(),),
            policy,
            check_active=lambda: None,
            startup_timeout=5,
            command=[
                sys.executable,
                "-I",
                "-u",
                str(Path(__file__).with_name("native_host_cases.py")),
            ],
            **changes,
        )
        peers.append(host)
        return host

    try:
        yield create
    finally:
        for host in peers:
            host.close(grace_seconds=0)


def test_real_host_peer_refusal_preserves_residency_and_healthy_siblings(physical_host):
    selected = selection()
    host = physical_host(selected)
    pid = host._process.pid
    with pytest.raises(Pm2WorkerRefused, match="controlled member refusal"):
        host.infer(selected, {"mode": "refused"}, check_active=lambda: None)
    assert host.infer(selected, {"value": "independent"}, check_active=lambda: None) == {
        "value": "independent"
    }
    assert not host.closed and host._process.pid == pid


@pytest.mark.parametrize("mode", ["crash", "foreign", "oversized", "hang"])
def test_real_host_peer_failure_fences_and_proves_process_death(physical_host, mode):
    selected = selection()
    host = physical_host(selected)
    with pytest.raises(Pm2WorkerError):
        host.infer(selected, {"mode": mode}, check_active=lambda: None, timeout=0.3)
    assert host.closed
    assert not native_host._live_group(host._process.pid)


def test_real_host_cancelled_member_preserves_other_provider_result(physical_host):
    from concurrent.futures import CancelledError, ThreadPoolExecutor
    from threading import Event

    first, second = selection(), selection("maverick")
    host = physical_host(first, second)
    cancelled, submitted = Event(), Event()

    def active():
        submitted.set()
        if cancelled.is_set():
            raise CancelledError("member cancelled")

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(host.infer, first, {"mode": "wait"}, check_active=active)
        assert submitted.wait(2)
        cancelled.set()
        assert host.infer(second, {"value": "useful sibling"}, check_active=lambda: None) == {
            "value": "useful sibling"
        }
        with pytest.raises(CancelledError):
            future.result(timeout=3)
    assert not host.closed


def test_real_host_startup_cancellation_keeps_adopted_physical_owner():
    import sys
    from concurrent.futures import CancelledError

    adopted = []

    def cancelled():
        raise CancelledError("claim ended during startup")

    with pytest.raises(CancelledError, match="claim ended"):
        native_host.NativeHost(
            (selection(),),
            CharacterizationExecutionPolicy(),
            check_active=cancelled,
            adopt=adopted.append,
            command=[
                sys.executable,
                "-I",
                "-u",
                str(Path(__file__).with_name("native_host_cases.py")),
                "startup-hang",
            ],
        )
    assert len(adopted) == 1
    assert not native_host._live_group(adopted[0]._process.pid)


def test_real_host_close_kills_descendant_even_after_leader_was_reaped(physical_host):
    selected = selection()
    host = physical_host(selected)
    reply = host.infer(selected, {"mode": "descendant"}, check_active=lambda: None)
    assert reply["child"] != host._process.pid
    assert host._process.wait(timeout=2) == 0
    assert native_host._live_group(host._process.pid)
    host.close(grace_seconds=0)
    assert not native_host._live_group(host._process.pid)
    assert not host._reader.is_alive()


@pytest.mark.parametrize(
    "changed",
    [
        "head",
        "runtime_identity",
        "assets",
        "device",
        "dtype",
        "backend",
        "native_threads",
        "profile",
        "new_semantic_field",
    ],
)
def test_parser_startup_comparison_excludes_only_process_local_stream(changed):
    from corpus_structure.methods.native_profiles import admitted_startup_matches

    admitted: dict[str, Any] = dict(
        provider="hanlp",
        head="mtl",
        runtime_identity={"python": "3.14.10"},
        assets={"checkpoint": "exact"},
        device="cuda:0",
        dtype="torch.float32",
        backend="sdpa",
        native_threads={"intra_op": 4, "inter_op": 1},
        profile="frozen",
        host_stream=123,
    )
    observed: dict[str, Any] = {**admitted, "host_stream": 987}
    assert admitted_startup_matches(observed, admitted)
    assert admitted_startup_matches(
        {key: value for key, value in observed.items() if key != "host_stream"}, admitted
    )
    observed[changed] = "different"
    assert not admitted_startup_matches(observed, admitted)
    # Ignoring the handle at admission cannot rewrite historical receipt identity.
    assert admitted["host_stream"] == 123


def test_parser_startup_pool_roster_is_observation_but_thread_count_is_a_contract():
    from copy import deepcopy

    from corpus_structure.methods.native_profiles import admitted_startup_matches

    admitted: dict[str, Any] = dict(
        provider="hanlp",
        native_threads=dict(
            intra_op=4,
            inter_op=1,
            supported_pools=[dict(filepath="/first/blas.so", user_api="blas", num_threads=4)],
        ),
    )
    observed: dict[str, Any] = dict(
        provider="hanlp",
        native_threads=dict(
            intra_op=4,
            inter_op=1,
            supported_pools=[
                dict(filepath="/other/openmp.so", user_api="openmp", num_threads=4),
                dict(filepath="/other/blas.so", user_api="blas", num_threads=4),
            ],
        ),
    )
    original = deepcopy(admitted)
    assert admitted_startup_matches(observed, admitted)
    observed["native_threads"]["supported_pools"].reverse()
    assert admitted_startup_matches(observed, admitted)
    assert admitted == original
    for count in (1, 0, -1, None, "4", True):
        changed = deepcopy(observed)
        changed["native_threads"]["supported_pools"][0]["num_threads"] = count
        assert not admitted_startup_matches(changed, admitted)
    missing = deepcopy(observed)
    missing["native_threads"]["supported_pools"][0].pop("num_threads")
    assert not admitted_startup_matches(missing, admitted)
    unknown = deepcopy(observed)
    unknown["native_threads"]["new_semantic_thread_field"] = 4
    assert not admitted_startup_matches(unknown, admitted)
