"""Session lifetime and cancellation controls without starting native providers."""

import json
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

from corpus_structure.methods import characterization_resources as resources
from corpus_structure.methods.gliner import GlinerProfile
from corpus_structure.methods.pm2_worker import Pm2WorkerRefused


@pytest.fixture
def lifetimes(monkeypatch):
    opened, closed, preflight = [], [], []

    class Worker:
        def __init__(self, active, kind):
            self.active, self.kind, self.closed = active, kind, False
            self.startup = {"runtime_identity": {"version": "frozen"}, "assets": {}}
            self.profile = None

        def infer(self, payload, *, check_active=None):
            self.active()
            if check_active is not None:
                check_active()
            return payload

        def extract(self, *_args, check_active=None, **_kwargs):
            if check_active is not None:
                check_active()
            return ()

        def close(self):
            if not self.closed:
                self.closed = True
                closed.append(self)

    @contextmanager
    def open_worker(**kwargs):
        kwargs["check_active"]()
        worker = Worker(kwargs["check_active"], kwargs["device"])
        opened.append(worker)
        try:
            yield worker
        finally:
            worker.close()

    def gliner(profile):
        worker = Worker(lambda: None, "gliner")
        worker.profile = profile
        opened.append(worker)
        return worker

    def checked(**kwargs):
        preflight.append(kwargs)
        return {"runtime_identity": {"version": "frozen"}, "assets": {"size": 1}}

    monkeypatch.setattr(resources, "_open_pm2_worker", open_worker)
    monkeypatch.setattr(resources, "GlinerWorker", gliner)
    monkeypatch.setattr(resources, "_preflight_pm2_runtime", checked)
    return opened, closed, preflight


def pm2_arguments(
    tmp_path, *, provider="hanlp", identity="one", name="profile", device="cpu"
) -> dict[str, Any]:
    profile = tmp_path / (name + ".json")
    profile.write_text(
        json.dumps(dict(provider=provider, device=device, runtime_identity=identity))
    )
    return dict(
        provider=provider,
        python=Path("/fixture/python"),
        script=Path("/fixture/native.py"),
        profile=profile,
        device=device,
        check_active=lambda: None,
    )


def changed_arguments(arguments: dict[str, Any], **updates: Any) -> dict[str, Any]:
    changed: dict[str, Any] = arguments.copy()
    changed.update(updates)
    return changed


def gliner_profile(tmp_path):
    return GlinerProfile(
        snapshot=tmp_path,
        checkpoint="fixture",
        revision="pinned",
        artifact_hashes=tuple(
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


def test_cpu_resident_reuses_exact_content_across_temporary_paths_and_nested_sessions(
    tmp_path, lifetimes
):
    opened, closed, _ = lifetimes
    with resources.characterization_resource_session():
        first = pm2_arguments(tmp_path)
        with resources.borrowed_pm2_worker(**first) as one:
            assert one.infer({"first": True}) == {"first": True}
        first["profile"].unlink()
        with (
            resources.characterization_resource_session(),
            resources.borrowed_pm2_worker(**pm2_arguments(tmp_path, name="another")) as two,
        ):
            assert two is one
        assert len(opened) == 1 and closed == []
    assert closed == [one]


def test_resident_callback_tracks_current_task_and_clears_completed_borrow(tmp_path, lifetimes):
    calls = []
    completed = False

    def old_task():
        assert not completed, "resident invoked the completed task lease"
        calls.append("old")

    def current_task():
        calls.append("current")

    with resources.characterization_resource_session():
        arguments = pm2_arguments(tmp_path)
        with resources.borrowed_pm2_worker(
            **changed_arguments(arguments, check_active=old_task)
        ) as worker:
            worker.infer({}, check_active=old_task)
        completed = True
        calls.clear()
        with resources.borrowed_pm2_worker(
            **changed_arguments(arguments, check_active=current_task)
        ) as reused:
            assert reused is worker
            reused.infer({}, check_active=current_task)
        assert calls and set(calls) == {"current"}
        with pytest.raises(Pm2WorkerRefused, match="no active borrower"):
            worker.infer({})


def test_profile_replacement_and_session_failure_close_every_resident(tmp_path, lifetimes):
    opened, closed, _ = lifetimes
    with (
        pytest.raises(RuntimeError, match="outer failure"),
        resources.characterization_resource_session(),
    ):
        for provider in ("hanlp", "maverick", "dipo", "d1"):
            with resources.borrowed_pm2_worker(
                **pm2_arguments(tmp_path, provider=provider, name=provider)
            ):
                pass
        with resources.borrowed_gliner_worker(gliner_profile(tmp_path)):
            pass
        assert len(opened) == 5 and closed == []
        with resources.borrowed_pm2_worker(**pm2_arguments(tmp_path, identity="changed")):
            assert len(closed) == 1
            assert sum(not worker.closed for worker in opened) == 5
        raise RuntimeError("outer failure")
    assert len(opened) == len(closed) == 6


def test_cancelled_borrow_retires_worker_and_next_task_gets_fresh_owner(tmp_path, lifetimes):
    opened, closed, _ = lifetimes
    cancelled = False

    def current():
        if cancelled:
            raise RuntimeError("cancelled current task")

    with resources.characterization_resource_session():
        arguments = pm2_arguments(tmp_path)
        with (
            pytest.raises(RuntimeError, match="cancelled current"),
            resources.borrowed_pm2_worker(
                **changed_arguments(arguments, check_active=current)
            ) as worker,
        ):
            cancelled = True
            worker.infer({})
        assert closed == [worker]
        with resources.borrowed_pm2_worker(**arguments) as fresh:
            assert fresh is not worker
    assert len(opened) == len(closed) == 2


def test_borrow_admission_does_not_replace_active_owner(tmp_path, lifetimes):
    with (
        resources.characterization_resource_session(),
        resources.borrowed_pm2_worker(**pm2_arguments(tmp_path)) as active,
    ):
        with (
            pytest.raises(Pm2WorkerRefused, match="active borrower"),
            resources.borrowed_pm2_worker(**pm2_arguments(tmp_path, identity="other")),
        ):
            pytest.fail("overlapping borrow admitted")
        assert active.infer({"still": "current"}) == {"still": "current"}


def test_changed_frozen_artifacts_replace_worker_even_with_identical_profile_file(
    tmp_path, lifetimes
):
    opened, closed, _ = lifetimes
    args = pm2_arguments(tmp_path)
    with resources.characterization_resource_session():
        with resources.borrowed_pm2_worker(**args, frozen_artifacts={"weights": "first"}) as first:
            pass
        with resources.borrowed_pm2_worker(
            **args, frozen_artifacts={"weights": "second"}
        ) as second:
            assert second is not first and closed == [first]
    assert len(opened) == len(closed) == 2


@pytest.mark.parametrize("session, device", ((False, "cpu"), (False, "cuda"), (True, "cuda")))
def test_ordinary_and_cuda_borrows_keep_existing_teardown(tmp_path, lifetimes, session, device):
    from contextlib import nullcontext

    opened, closed, _ = lifetimes
    with resources.characterization_resource_session() if session else nullcontext():
        for _ in range(2):
            with resources.borrowed_pm2_worker(**pm2_arguments(tmp_path, device=device)):
                pass
            assert len(opened) == len(closed)
    assert len(opened) == 2


def test_preflight_selection_cache_is_bounded_and_returns_independent_values(tmp_path, lifetimes):
    _, _, checked = lifetimes
    args: dict[str, Any] = dict(
        python=Path("/fixture/python"),
        script=Path("/fixture/native.py"),
        project=tmp_path,
        provider="hanlp",
        assets=tmp_path,
        frozen_runtime={"version": "one"},
        frozen_artifacts={},
    )
    callbacks = []
    with resources.characterization_resource_session():
        first = resources.characterization_pm2_preflight(
            **args, check_active=lambda: callbacks.append("first")
        )
        first["assets"]["size"] = 999
        again = resources.characterization_pm2_preflight(
            **args, check_active=lambda: callbacks.append("second")
        )
        assert again["assets"]["size"] == 1 and len(checked) == 1
        resources.characterization_pm2_preflight(
            **changed_arguments(args, frozen_runtime={"version": "two"})
        )
        resources.characterization_pm2_preflight(**args)
        assert len(checked) == 3  # Returning to an old profile cannot grow a historical cache.
    assert callbacks == ["first", "first", "second", "second"]
    resources.characterization_pm2_preflight(**args)
    resources.characterization_pm2_preflight(**args)
    assert len(checked) == 5


def test_gliner_reuses_exact_profile_and_keeps_current_explicit_callback(tmp_path, lifetimes):
    opened, closed, _ = lifetimes
    profile = gliner_profile(tmp_path)
    calls = []
    with resources.characterization_resource_session():
        with resources.borrowed_gliner_worker(
            profile, check_active=lambda: calls.append("one")
        ) as one:
            cast(Any, one).extract(check_active=lambda: calls.append("one"))
        calls.clear()
        with resources.borrowed_gliner_worker(
            profile, check_active=lambda: calls.append("two")
        ) as two:
            assert two is one
            cast(Any, two).extract(check_active=lambda: calls.append("two"))
        assert calls and set(calls) == {"two"}
        with resources.borrowed_gliner_worker(
            replace(profile, threads=profile.threads + 1)
        ) as changed:
            assert one.closed and changed is not one
        assert len(opened) == 2 and closed == [one]
    assert len(closed) == 2
