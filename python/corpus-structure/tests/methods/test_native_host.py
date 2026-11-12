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


def test_declared_group_is_lazy_and_keeps_custody_until_both_host_deaths_are_proven(monkeypatch):
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
        def __init__(self, selections, policy, *, check_active):
            check_active()
            self.name = selections[0].native.host
            self.failed_once = self.name == "314"
            hosts.append(self)
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
    assert {host.name for host in hosts} == {"314", "312"}
    with pytest.raises(Pm2WorkerRefused, match="not declared"):
        group.declare((selection(parameters={"new": True}),))
    with pytest.raises(Pm2WorkerError, match="unproven"):
        group.close()
    assert events == ["lease-enter", "close-314", "close-312"]
    group.close()
    group.close()
    assert events[-3:] == ["close-314", "close-312", "lease-exit"]


def test_unselected_child_does_not_claim_a_real_provider_adapter_exists():
    with pytest.raises(NotImplementedError, match=r"not integrated.*unselected"):
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
