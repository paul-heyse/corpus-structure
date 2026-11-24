"""Private custody survives failure before native intent without changing producer facts."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
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


def test_population_upload_is_owned_by_the_durable_acknowledgment(tmp_path):
    import pyarrow as pa

    from corpus_structure.semantic.data_operation_partitions import PartitionCommitment
    from corpus_structure.semantic.population_transfer import (
        PopulationUploadPartition,
        population_item_write_profile,
        population_upload_batches,
    )

    profile = population_item_write_profile(release_id="release:original")
    partition = PopulationUploadPartition(
        PartitionCommitment("rows", "one", 0, 1, 4, "digest:one", 1),
        {},
        pa.table({"item_ordinal": [0], "canonical_text": ['["mapping",[]]']}),
    )
    store = CompletionDraftStore(tmp_path, max_bytes=65536)
    draft = acknowledge(
        store,
        population_upload_batches=population_upload_batches(profile, [("result", 0, partition)]),
        population_upload_profile=profile,
        max_population_upload_bytes=65536,
    )
    assert draft.identity != acknowledge(store).identity
    reopened = store.open(draft.identity)
    assert reopened.population_upload is not None
    with reopened.population_upload.open_reader() as reader:
        assert reader.schema.equals(profile.schema, check_metadata=True)
        assert reader.read_all().to_pylist() == [
            {
                "output_role": "result",
                "output_position": 0,
                "collection": "rows",
                "partition_key": "one",
                "item_ordinal": 0,
                "canonical_text": '["mapping",[]]',
            }
        ]
    path = tmp_path / (draft.identity + ".arrow")
    upload = path.read_bytes()
    with reopened.population_upload.open_reader() as reader:
        # The COPY reader consumes an authenticated private copy, even if the
        # durable pathname is changed after acquisition.
        path.write_bytes(upload[:-1] + b"0")
        assert reader.read_all().num_rows == 1
    with pytest.raises(ValueError, match="acknowledged population upload"):
        store.open(draft.identity)


def test_population_upload_failures_never_acknowledge_partial_streams(tmp_path):
    import pyarrow as pa

    from corpus_structure.semantic.population_transfer import population_item_write_profile

    profile = population_item_write_profile(release_id="release:original")
    empty = pa.RecordBatch.from_arrays(
        [pa.array([], type=field.type) for field in profile.schema], schema=profile.schema
    )
    store = CompletionDraftStore(tmp_path, max_bytes=65536)

    def interrupted():
        yield empty
        raise RuntimeError("producer stopped before seal")

    with pytest.raises(RuntimeError, match="before seal"):
        acknowledge(
            store,
            population_upload_batches=interrupted(),
            population_upload_profile=profile,
        )
    with pytest.raises(ValueError, match="draft byte limit"):
        acknowledge(
            store,
            population_upload_batches=iter([empty]),
            population_upload_profile=profile,
            max_population_upload_bytes=1,
        )
    assert not tuple(tmp_path.glob("*.ack"))
    assert not tuple(tmp_path.glob("*.arrow"))
    assert not tuple(tmp_path.glob("pending-*"))


def test_concurrent_acknowledgment_converges_on_one_exact_body(tmp_path):
    store = CompletionDraftStore(tmp_path, max_bytes=65536)
    with ThreadPoolExecutor(max_workers=3) as workers:
        results = tuple(workers.map(lambda _: acknowledge(store), range(6)))
    assert len({draft.identity for draft in results}) == 1
    assert len(tuple(tmp_path.glob("*.body"))) == len(tuple(tmp_path.glob("*.ack"))) == 1


def test_draft_basis_retains_numeric_tokens_without_inferring_scope_from_field_names(tmp_path):
    from corpus_structure.semantic.data_operation_json import native_json_loads

    basis = b'{"ordinary":{"coordinate":0.12345678901234567890123456789},"analyzed_scope":{"coordinate":0.23456789012345678901234567891},"execution_origin":"origin:one"}'
    store = CompletionDraftStore(tmp_path, max_bytes=65536)
    draft = store.acknowledge(
        request(),
        writer_schema=json_bytes(wire_contracts()["retain_data_completion_intent"]["input"]),
        release_id="release:original",
        operation="source.pdf/capture",
        basis=basis,
        check_active=lambda: None,
    )
    original_request = (tmp_path / (draft.identity + ".body")).read_bytes()
    reopened = store.open(draft.identity)
    observed = native_json_loads(reopened.basis)
    assert observed["ordinary"]["coordinate"] == Decimal("0.12345678901234567890123456789")
    assert observed["analyzed_scope"]["coordinate"] == Decimal("0.23456789012345678901234567891")
    assert reopened.request == original_request
    assert reopened.native_request() == request()


def test_lost_claim_before_ack_removes_unpublished_body(tmp_path):
    calls = 0

    def check_active():
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("claim lost")

    store = CompletionDraftStore(tmp_path, max_bytes=65536)
    with pytest.raises(RuntimeError, match="claim lost"):
        acknowledge(store, check_active=check_active)
    assert tuple(tmp_path.glob("*.body")) == ()
    assert tuple(tmp_path.glob("*.candidate")) == ()
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
        cpu_execution_evidence=None,
        pdf_execution_evidence=None,
        pdf_observation_evidence=None,
        provider_execution_evidence=None,
        rule_attestations=(),
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

    def missing_writer(release):
        raise KeyError(release)

    unavailable = CompletionDraftStore(
        tmp_path, max_bytes=65536, writer_schema_for_release=missing_writer
    )
    with pytest.raises(DraftWriterContractUnavailable, match="writer release is unavailable"):
        unavailable.open(identity)

    acquired = []

    def writer(release):
        acquired.append(release)
        return json_bytes(wire_contracts()["retain_data_completion_intent"]["input"])

    reopened = CompletionDraftStore(tmp_path, max_bytes=65536, writer_schema_for_release=writer)
    assert reopened.open(identity).native_request() == request()
    assert acquired == ["release:original"]


@pytest.fixture
def upload_arguments():
    import pyarrow as pa

    from corpus_structure.semantic.data_operation_partitions import PartitionCommitment
    from corpus_structure.semantic.population_transfer import (
        PopulationUploadPartition,
        population_item_write_profile,
        population_upload_batches,
    )

    profile = population_item_write_profile(release_id="release:original")
    partition = PopulationUploadPartition(
        PartitionCommitment("rows", "one", 0, 1, 4, "digest:one", 1),
        {},
        pa.table({"item_ordinal": [0], "canonical_text": ['["mapping",[]]']}),
    )

    def arguments():
        return dict(
            population_upload_batches=population_upload_batches(profile, [("result", 0, partition)]),
            population_upload_profile=profile,
        )

    return arguments


@pytest.mark.parametrize("suffix", [".body", ".candidate", ".ack"])
def test_seal_failure_preserves_only_acknowledged_population(
    tmp_path, monkeypatch, upload_arguments, suffix
):
    from corpus_structure.core.execution_control import ExecutionStopped

    store = CompletionDraftStore(tmp_path, max_bytes=65536)
    atomic = store._atomic

    def fail_after_install(name, content):
        atomic(name, content)
        if name.endswith(suffix):
            raise ExecutionStopped()

    monkeypatch.setattr(store, "_atomic", fail_after_install)
    with pytest.raises(ExecutionStopped):
        acknowledge(store, **upload_arguments())
    if suffix == ".ack":
        (draft,) = store.candidates("request:original", 2)
        assert draft.population_upload is not None
        original = draft.population_upload.path.read_bytes()
        reopened = CompletionDraftStore(tmp_path, max_bytes=65536).open(draft.identity)
        with reopened.population_upload.open_reader() as reader:
            assert reader.read_all().num_rows == 1
        assert reopened.population_upload.path.read_bytes() == original
    else:
        assert not tuple(tmp_path.glob("*.body"))
        assert not tuple(tmp_path.glob("*.arrow"))
        assert not tuple(tmp_path.glob("*.candidate"))
    assert not tuple(tmp_path.glob("pending-*"))


def test_population_stop_after_installed_arrow_removes_unsealed_files(
    tmp_path, upload_arguments
):
    from corpus_structure.core.execution_control import ExecutionStopped

    store = CompletionDraftStore(tmp_path, max_bytes=65536)

    def active():
        if tuple(tmp_path.glob("*.arrow")):
            raise ExecutionStopped()

    with pytest.raises(ExecutionStopped):
        acknowledge(store, check_active=active, **upload_arguments())
    assert sorted(path.name for path in tmp_path.iterdir()) == ["OWNER"]


def test_reopening_store_retires_abandoned_staging_and_keeps_live_writer(tmp_path):
    import fcntl

    CompletionDraftStore(tmp_path, max_bytes=65536)
    identity = "a" * 64
    (tmp_path / (identity + ".body")).write_bytes(b"unsealed")
    (tmp_path / (identity + ".arrow")).write_bytes(b"unsealed")
    (tmp_path / ("b" * 64 + "." + identity + ".candidate")).touch()
    (tmp_path / "pending-abandoned").write_bytes(b"incomplete")
    live = tmp_path / "pending-live"
    with live.open("wb") as writer:
        fcntl.flock(writer.fileno(), fcntl.LOCK_EX)
        CompletionDraftStore(tmp_path, max_bytes=65536)
        assert sorted(path.name for path in tmp_path.iterdir()) == ["OWNER", "pending-live"]
    CompletionDraftStore(tmp_path, max_bytes=65536)
    assert sorted(path.name for path in tmp_path.iterdir()) == ["OWNER"]


def test_population_private_copy_observes_stop_and_preserves_original(
    tmp_path, upload_arguments
):
    from corpus_structure.core.execution_control import ExecutionStopped

    store = CompletionDraftStore(tmp_path, max_bytes=65536)
    draft = acknowledge(store, **upload_arguments())
    original = draft.population_upload.path.read_bytes()

    def stopped():
        raise ExecutionStopped()

    with pytest.raises(ExecutionStopped), draft.population_upload.open_reader(check_active=stopped):
        pytest.fail("stopped reader must not acquire its private copy")
    assert draft.population_upload.path.read_bytes() == original
    with store.open(draft.identity).population_upload.open_reader() as reader:
        assert reader.read_all().num_rows == 1
