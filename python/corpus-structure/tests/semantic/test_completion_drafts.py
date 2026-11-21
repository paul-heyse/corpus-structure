"""Private custody survives failure before native intent without changing producer facts."""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256

import pytest

from corpus_structure.semantic._data_operation_wire import WireInspectDataCompletionDraftResult
from corpus_structure.semantic.completion_drafts import CompletionDraftStore
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_wire import wire_contracts


def request():
    return dict(
        request_id="request:original",
        generation=2,
        task_id=5,
        attempt=3,
        holder="original-holder",
        runtime_id="runtime:original",
        completion=dict(
            outcome="empty", outputs=[], inputs=[], support=[], implementation_revision="code:one"
        ),
    )


def acknowledge(store, **changes):
    return store.acknowledge(
        changes.pop("request", request()),
        writer_schema=json_bytes(wire_contracts()["retain_data_completion_intent"]["input"]),
        release_id="release:original",
        operation="source.pdf/capture",
        basis=b'{"recipe":"recipe:one","binding":"binding:one","execution_origin":"origin:one"}',
        check_active=changes.pop("check_active", lambda: None),
        **changes,
    )


def test_known_rollback_and_lost_acknowledgment_preserve_exact_draft(tmp_path):
    store = CompletionDraftStore(tmp_path, max_bytes=65536)
    first = acknowledge(store)
    # The settlement transaction fails after the independent private acknowledgment.
    with pytest.raises(RuntimeError, match="rollback"):
        raise RuntimeError("native intent rollback")
    reopened = CompletionDraftStore(tmp_path, max_bytes=65536)
    assert reopened.open(first.identity) == first
    assert acknowledge(reopened) == first
    assert first.native_request() == request()
    assert tuple(reopened.candidates("request:original", 2)) == (first,)
    assert tuple(reopened.candidates("request:other", 2)) == ()
    assert first.release_id == "release:original"
    assert len(tuple(tmp_path.glob("*.ack"))) == 1
    assert sha256((tmp_path / (first.identity + ".ack")).read_bytes()).hexdigest() == first.identity


def test_concurrent_acknowledgment_converges_on_one_exact_body(tmp_path):
    store = CompletionDraftStore(tmp_path, max_bytes=65536)
    with ThreadPoolExecutor(max_workers=3) as workers:
        results = tuple(workers.map(lambda _: acknowledge(store), range(6)))
    assert len({draft.identity for draft in results}) == 1
    assert len(tuple(tmp_path.glob("*.body"))) == len(tuple(tmp_path.glob("*.ack"))) == 1


def test_lost_claim_before_ack_keeps_body_inert(tmp_path):
    calls = 0

    def check_active():
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("claim lost")

    store = CompletionDraftStore(tmp_path, max_bytes=65536)
    with pytest.raises(RuntimeError, match="claim lost"):
        acknowledge(store, check_active=check_active)
    assert len(tuple(tmp_path.glob("*.body"))) == 1
    assert tuple(tmp_path.glob("*.ack")) == ()
    assert tuple(store.candidates("request:original", 2)) == ()
    draft = acknowledge(store)
    assert store.open(draft.identity).native_request() == request()


def test_changed_body_or_unexpected_extent_refuses(tmp_path):
    store = CompletionDraftStore(tmp_path, max_bytes=65536)
    draft = acknowledge(store)
    path = tmp_path / (draft.identity + ".body")
    original = path.read_bytes()
    path.write_bytes(original + b" ")
    with pytest.raises(ValueError, match="extent"):
        store.open(draft.identity)
    path.write_bytes(original.replace(b"original-holder", b"forged---holder"))
    with pytest.raises(ValueError, match="acknowledged body"):
        store.open(draft.identity)


def test_foreign_shape_and_oversized_drafts_refuse_before_ack(tmp_path):
    store = CompletionDraftStore(tmp_path, max_bytes=100)
    with pytest.raises(ValueError, match="byte bound"):
        acknowledge(store)
    assert not tuple(tmp_path.glob("*.ack"))
    with pytest.raises(ValueError):
        CompletionDraftStore(tmp_path, max_bytes=65536).open("../escape")


def test_executor_acknowledges_before_native_rollback_and_retries_original_request(
    tmp_path, monkeypatch
):
    from datetime import UTC, datetime
    from types import SimpleNamespace

    from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
    from corpus_structure.orchestrate.data_operations import (
        NativeDemandExecutor,
        NativeRequestClaim,
    )
    from corpus_structure.semantic.data_operation_ports import PythonPortIdentity

    store = CompletionDraftStore(tmp_path, max_bytes=65536)
    executor = object.__new__(NativeDemandExecutor)
    executor.completion_drafts = store
    executor._draft_origins = {(5, 3): {"origin_id": "origin:actual"}}
    executor.policy = CharacterizationExecutionPolicy(max_reply_bytes=65536)
    operation = SimpleNamespace(output_witnesses=(), outcomes=("empty",))
    context = SimpleNamespace(
        model=SimpleNamespace(operation=lambda _: operation),
        basis=SimpleNamespace(
            captured_contracts=None,
            runtime=SimpleNamespace(manifest=b"runtime", archive=b"archive"),
        ),
    )
    monkeypatch.setattr(executor, "_execution_context", lambda claim: context)
    claim = NativeRequestClaim(
        "request:original",
        2,
        5,
        3,
        "original-holder",
        "release:original",
        datetime.now(UTC),
        runtime_id="runtime:original",
    )
    ready = SimpleNamespace(operation="source.pdf/capture", binding=b'{"inputs":[],"support":[]}')
    answer = SimpleNamespace(
        operation=ready.operation,
        outputs=(),
        outcome="empty",
        execution_evidence=None,
        product_validation_evidence=None,
        cpu_execution_evidence=None,
        pdf_execution_evidence=None,
        pdf_observation_evidence=None,
        provider_execution_evidence=None,
    )
    port = SimpleNamespace(
        identity=PythonPortIdentity(
            "model",
            ready.operation,
            "definition",
            "recipe",
            "code:one",
            "declaration",
            "source",
            b"{}",
            "eligibility",
        )
    )
    attempts = []

    def retain(_, action):
        assert len(tuple(tmp_path.glob("*.ack"))) == 1

        def native(request):
            attempts.append(request)
            if len(attempts) == 1:
                raise RuntimeError("intent rollback")
            return {"intent_id": "intent:retained"}

        return action(SimpleNamespace(retain_data_completion_intent=native))

    owner = SimpleNamespace(check_claim=lambda _: None, retain=retain)
    with pytest.raises(RuntimeError, match="intent rollback"):
        executor._retain_answer(ready, claim, answer, port, owner)
    assert executor._retain_answer(ready, claim, answer, port, owner).intent_id == "intent:retained"
    assert attempts == [request(), request()]
    assert len(tuple(tmp_path.glob("*.ack"))) == 1


def test_cleanup_retains_unsettled_and_resumes_exact_marker(tmp_path, monkeypatch):
    from pathlib import Path

    store = CompletionDraftStore(tmp_path, max_bytes=65536)
    draft = acknowledge(store)

    def unavailable(payload) -> WireInspectDataCompletionDraftResult:
        assert payload["draft_id"] == draft.identity
        assert payload["producer"] == request()
        return {
            "state": "retained",
            "reason": "retirement-unconfirmed",
            "intent_id": "intent:one",
            "receipt_id": "receipt:one",
            "failure_id": None,
        }

    result = store.retire(draft.identity, project_id="project", inspect=unavailable)
    assert result.state == "retained"
    assert store.open(draft.identity) == draft

    def eligible(payload) -> WireInspectDataCompletionDraftResult:
        return {
            **unavailable(payload),
            "state": "eligible",
            "reason": "retired",
            "failure_id": "failure:one",
        }

    unlink = Path.unlink

    def interrupted(path, *args, **options):
        if path.suffix == ".body":
            raise OSError("interrupted body removal")
        return unlink(path, *args, **options)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", interrupted)
        with pytest.raises(OSError, match="interrupted"):
            store.retire(draft.identity, project_id="project", inspect=eligible)
    assert (tmp_path / (draft.identity + ".retired")).is_file()
    assert (tmp_path / (draft.identity + ".body")).is_file()
    assert not tuple(store.candidates("request:original", 2))

    def no_new_inspection(_):
        raise AssertionError("durable retirement marker already authorized exact deletion")

    reopened = CompletionDraftStore(tmp_path, max_bytes=65536)
    with pytest.raises(ValueError, match="selected custody"):
        reopened.retire(draft.identity, project_id="other", inspect=no_new_inspection)
    with ThreadPoolExecutor(max_workers=3) as workers:
        reports = tuple(
            workers.map(
                lambda _: reopened.retire(
                    draft.identity, project_id="project", inspect=no_new_inspection
                ),
                range(3),
            )
        )
    assert {report.state for report in reports} == {"retired"}
    assert {report.intent_id for report in reports} == {"intent:one"}
    assert not tuple(tmp_path.glob("*.body"))
    with pytest.raises(ValueError, match="already retired"):
        acknowledge(store)


def test_inspection_failure_and_foreign_file_leave_draft_unretired(tmp_path):
    store = CompletionDraftStore(tmp_path, max_bytes=65536)
    draft = acknowledge(store)

    def unavailable(_):
        raise OSError("native inspection unavailable")

    with pytest.raises(OSError, match="native inspection unavailable"):
        store.retire(draft.identity, project_id="project", inspect=unavailable)
    assert store.open(draft.identity) == draft
    (candidate,) = tmp_path.glob("*.candidate")
    candidate.unlink()
    other = tmp_path / "foreign"
    other.write_bytes(b"foreign")
    candidate.symlink_to(other)
    with pytest.raises(ValueError, match="foreign file custody"):
        store.retire(
            draft.identity,
            project_id="project",
            inspect=lambda _: {
                "state": "eligible",
                "reason": "retired",
                "intent_id": "intent",
                "receipt_id": "receipt",
                "failure_id": "failure",
            },
        )
    assert other.read_bytes() == b"foreign"
    assert not tuple(tmp_path.glob("*.retired"))


def test_draft_reopens_with_captured_writer_after_ambient_contract_changes(tmp_path, monkeypatch):
    from corpus_structure.semantic import data_operation_wire

    store = CompletionDraftStore(tmp_path, max_bytes=65536)
    draft = acknowledge(store)
    monkeypatch.setattr(data_operation_wire, "wire_contracts", lambda: {})
    assert store.open(draft.identity).native_request() == request()


def test_legacy_draft_requires_authenticated_writer_basis(tmp_path):
    from corpus_structure.semantic.completion_drafts import DraftWriterContractUnavailable

    store = CompletionDraftStore(tmp_path, max_bytes=65536)
    draft = acknowledge(store)
    envelope = __import__("json").loads((tmp_path / (draft.identity + ".ack")).read_bytes())
    envelope["format"] = "ddo-completion-draft-v1"
    envelope.pop("writer_schema")
    envelope.pop("writer_schema_sha256")
    content = json_bytes(envelope)
    identity = sha256(content).hexdigest()
    (tmp_path / (identity + ".ack")).write_bytes(content)
    (tmp_path / (identity + ".body")).write_bytes(draft.request)
    with pytest.raises(DraftWriterContractUnavailable):
        store.open(identity)
    acquired = []

    def writer(release):
        acquired.append(release)
        return json_bytes(wire_contracts()["retain_data_completion_intent"]["input"])

    reopened = CompletionDraftStore(tmp_path, max_bytes=65536, writer_schema_for_release=writer)
    assert reopened.open(identity).native_request() == request()
    assert acquired == ["release:original"]
