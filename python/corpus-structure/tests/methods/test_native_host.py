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
def test_shared_pm2_adapters_authenticate_and_delegate_without_global_retuning(provider, tmp_path, monkeypatch):
    from corpus_structure.methods import native_host_adapters

    calls = []
    observed = {"device": "cuda:0", "dtype": "torch.bfloat16" if provider == "d1" else "torch.float32", "attention_implementation": "sdpa"}
    runtime, artifacts = {"lock": "shared-runtime"}, {"checkpoint": "exact"}

    def loader(assets, device):
        calls.append((provider, assets, device))
        return dict(observed), lambda request: {"native": request}

    def run(path):
        if Path(path).name == "pm2_native.py":
            return {"_runtime_identity": lambda selected, *, project: runtime, "_verify_assets": lambda assets, selected: artifacts, "_load_d1": loader}
        return {"load_" + provider: loader}

    monkeypatch.setattr(native_host_adapters.runpy, "run_path", run)
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path / "hub"))
    profile = dict(provider=provider, runtime_identity=runtime, artifacts=artifacts, backend="sdpa")
    metadata, infer = native_host_adapters.load({"profile": profile, "assets": str(tmp_path)}, object())
    assert calls == [(provider, tmp_path, "cuda")]
    assert metadata["runtime_identity"] == runtime and metadata["assets"] == artifacts
    assert metadata["attention_implementation"] == "sdpa"
    assert infer({"ordered": [2, 1]}) == {"native": {"ordered": [2, 1]}}
    profile["runtime_identity"] = {"lock": "foreign"}
    with pytest.raises(ValueError, match="runtime differs"):
        native_host_adapters.load({"profile": profile, "assets": str(tmp_path)}, object())
    assert len(calls) == 1


def test_direct_spacy_facade_loads_only_tokenizer_and_closes_phase_preserving_doc_constraints(monkeypatch):
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
            return dict(native_configuration=pipeline.config.to_str(), components=[dict(name=name, factory=pipeline.get_pipe_meta(name).factory) for name in pipeline.pipe_names])
        def infer(self, selected, payload, active):
            events.append("infer")
            doc = Doc(spacy.blank("en").vocab).from_bytes(base64.b64decode(payload["documents"][0]["content"]))
            assert doc[1].tag_ == "NNP" and doc[1].is_sent_start is False
            return {"documents": [base64.b64encode(doc.to_bytes()).decode("ascii")]}

    monkeypatch.setattr(native_host, "NativeHostGroup", Group)
    doc = Doc(pipeline.vocab, words=["Let", "x+y"], spaces=[True, False])
    doc[1].tag_ = "NNP"
    doc[1].is_sent_start = False
    [(restored, marker)] = list(pipeline.pipe([(doc, "exact-input")], as_tuples=True))
    assert restored.text == "Let x+y" and marker == "exact-input"
    assert events == ["enter", "infer", "exit"]
