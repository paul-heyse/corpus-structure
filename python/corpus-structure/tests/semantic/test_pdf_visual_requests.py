"""Current Chandra adapter controls; no provider execution or native admission claim."""

from contextlib import contextmanager, nullcontext
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from docling.datamodel.base_models import VlmStopReason
from PIL import Image

from corpus_structure.ingest import pdf_chandra, pdf_capacity
from corpus_structure.semantic import visual_requests
from corpus_structure.semantic.data_operation_json import json_bytes, wire_json_loads
from corpus_structure.semantic.data_operation_ports import PortRefusal


def selected_image():
    with Image.new("RGB", (4, 4), "white") as image, BytesIO() as output:
        image.save(output, format="PNG")
        content = output.getvalue()
    return dict(document="document:actual", source_digest="0" * 64, logical_digest="1" * 64,
                selection={"page_no": 1}, scale="2", encoding="png", content_hex=content.hex(),
                content_digest=sha256(content).hexdigest(), page_no=1, rotation=0, width=4, height=4,
                transform_json='{"status":"unknown"}')


def external_packet(image):
    return dict(packet_id="packet:actual", original_source=image["document"],
                operation_id=visual_requests.VISUAL_RECOGNIZE, release_id="release:actual",
                runtime_id="runtime:actual", protocol={"requested_actor": "datalab-chandra-2",
                    "requested_model": pdf_chandra.CHANDRA_REPOSITORY + "@" + pdf_chandra.CHANDRA_REVISION,
                    "instructions": json_bytes({"version": "chandra-native-png-v1", "policy": {
                        "repository": pdf_chandra.CHANDRA_REPOSITORY, "revision": pdf_chandra.CHANDRA_REVISION}}).decode()})


@pytest.fixture
def actor(monkeypatch, tmp_path):
    image = selected_image()
    packet = external_packet(image)
    claim = dict(state="claimed", action="compute", request_id="request:actual", generation=3,
                 task_id=17, attempt=2, holder="holder:actual",
                 lease_until=(datetime.now(UTC) + timedelta(minutes=5)).isoformat())
    session = MagicMock()
    session.inspect.return_value = {"state": "awaiting-external"}
    session.claim.return_value = claim
    session.read.return_value = {"packet_id": packet["packet_id"], "packet_digest": "9" * 64, "packet": packet, "input_views": [{"role": "image", "value": image}]}
    published = {"state": "committed", "packet_id": packet["packet_id"], "receipt": {"receipt_id": "receipt:actual"}}
    session.submit.return_value = published
    runtime = MagicMock()
    runtime.identity.return_value = {"repository": pdf_chandra.CHANDRA_REPOSITORY, "revision": pdf_chandra.CHANDRA_REVISION}
    monkeypatch.setattr(pdf_chandra, "ChandraRuntime", lambda path: runtime)
    monkeypatch.setattr(pdf_capacity, "pdf_gpu_slot", lambda **kw: nullcontext())
    monkeypatch.setattr(pdf_capacity, "suspend_resident_nemotron", lambda *args, **kw: nullcontext())
    prediction = SimpleNamespace(text='<div data-label="Formula" data-bbox="0 0 4 4">x</div>',
                                 stop_reason=VlmStopReason.END_OF_SEQUENCE, error_message=None)
    recognize = MagicMock(return_value=prediction)
    monkeypatch.setattr(pdf_chandra, "recognize_supervised", recognize)
    owner = MagicMock()
    owner.lock = nullcontext()
    owner.active = {(17, 2, "holder:actual"): claim}
    owned_claims = []

    @contextmanager
    def maintained(engine, claims, holder, **kwargs):
        owned_claims.extend(claims)
        assert holder == claim["holder"]
        yield owner

    from corpus_structure.semantic import claim_lifetime
    monkeypatch.setattr(claim_lifetime, "maintained_claims", maintained)
    return SimpleNamespace(session=session, claim=claim, packet=packet, image=image, runtime=runtime,
                           recognize=recognize, owner=owner, claims=owned_claims,
                           artifacts=tmp_path / "weights", receipts=tmp_path / "receipts", published=published)


def execute(actor):
    return visual_requests.execute_chandra_packet(actor.session, actor.packet["packet_id"],
        artifacts=actor.artifacts, receipts=actor.receipts)


def test_actual_packet_source_and_attempt_are_retained_before_native_submission(actor):
    def submit(packet_id, claim, result, **assertions):
        saved = list(actor.receipts.rglob("result.json"))
        assert len(saved) == 1
        record = wire_json_loads(saved[0].read_bytes())
        assert record["fence"] == {key: actor.claim[key] for key in ("request_id", "generation", "task_id", "attempt", "holder")}
        assert record["packet_digest"] == "9" * 64
        assert record["result"] == result
        body = result["outputs"][0]["body"]
        assert body["image"] == actor.image
        assert body["response_digest"] == sha256(body["raw_response"].encode()).hexdigest()
        assert "run_id" not in record and "invocation_key" not in record
        assert assertions["actor_assertion"] == "datalab-chandra-2"
        return actor.published

    actor.session.submit.side_effect = submit
    assert execute(actor) == actor.published
    assert (actor.claims[0].task_id, actor.claims[0].attempt, actor.claims[0].holder) == (17, 2, "holder:actual")
    assert not actor.owner.active
    actor.runtime.close.assert_called_once()


@pytest.mark.parametrize("change", ["source", "digest", "dimensions", "operation", "protocol", "policy"])
def test_wrong_packet_never_starts_inference(actor, change):
    if change == "source":
        actor.packet["original_source"] = "document:other"
    elif change == "digest":
        actor.image["content_digest"] = "f" * 64
    elif change == "dimensions":
        actor.image["width"] = 5
    elif change == "operation":
        actor.packet["operation_id"] = "another-operation"
    elif change == "protocol":
        actor.packet["protocol"]["requested_model"] = "unqualified"
    else:
        actor.packet["protocol"]["instructions"] = '{"version":"chandra-native-png-v1","policy":{}}'
    with pytest.raises(PortRefusal):
        execute(actor)
    actor.recognize.assert_not_called()
    actor.session.submit.assert_not_called()


def test_committed_or_retained_native_result_never_repeats_provider(actor):
    actor.session.inspect.return_value = actor.published
    assert execute(actor) == actor.published
    actor.recognize.assert_not_called()
    actor.session.claim.assert_not_called()
    actor.session.inspect.return_value = {"state": "retained"}
    actor.claim["action"] = "reconcile"
    actor.session.reconcile.return_value = actor.published
    assert execute(actor) == actor.published
    actor.recognize.assert_not_called()
    actor.session.reconcile.assert_called_once_with(actor.packet["packet_id"], actor.claim)


def test_lost_publication_keeps_raw_and_same_attempt_retry_uses_exact_local_result(actor):
    actor.session.submit.side_effect = RuntimeError("native receipt unavailable")
    with pytest.raises(RuntimeError, match="receipt unavailable") as caught:
        execute(actor)
    assert any("retained at" in note for note in caught.value.__notes__)
    assert len(list(actor.receipts.rglob("result.json"))) == 1
    actor.session.submit.side_effect = None
    actor.runtime.close.reset_mock()
    assert execute(actor) == actor.published
    assert actor.recognize.call_count == 1


def test_new_attempt_cannot_relabel_unadmitted_prior_raw_as_fresh_work(actor):
    actor.session.submit.side_effect = RuntimeError("native receipt unavailable")
    with pytest.raises(RuntimeError):
        execute(actor)
    actor.claim["attempt"] += 1
    with pytest.raises(PortRefusal, match="prior Chandra raw output"):
        execute(actor)
    assert actor.recognize.call_count == 1


def test_runtime_close_failure_preserves_primary_and_retained_output(actor):
    from corpus_structure.core.db.store import cleanup_unresolved

    primary = RuntimeError("native receipt unavailable")
    cleanup = RuntimeError("runtime close unavailable")
    actor.session.submit.side_effect = primary
    actor.runtime.close.side_effect = cleanup
    with pytest.raises(RuntimeError) as caught:
        execute(actor)
    assert caught.value is primary
    assert caught.value.__cause__ is cleanup
    assert cleanup_unresolved(caught.value)
    assert len(list(actor.receipts.rglob("result.json"))) == 1


def test_fence_loss_keeps_raw_original_attempt_and_never_submits(actor):
    actor.owner.check_claim.side_effect = [None, RuntimeError("fence lost")]
    with pytest.raises(RuntimeError, match="fence lost"):
        execute(actor)
    assert len(list(actor.receipts.rglob("result.json"))) == 1
    actor.session.submit.assert_not_called()


def test_mapping_refuses_changed_response_bytes_before_parser(actor):
    observation = dict(image=actor.image, raw_response="changed", response_digest="f" * 64,
                       finish_reason="end_of_sequence", runtime_identity_json="{}",
                       provider_outcome="succeeded", diagnostic="")
    with pytest.raises(PortRefusal, match="submitted/response bytes"):
        visual_requests.map_chandra_observation(observation)


def test_visual_demand_resume_preserves_native_and_external_receipts(monkeypatch, actor):
    from contextlib import contextmanager
    from corpus_structure.orchestrate.data_operations import DemandAdvance
    from corpus_structure.semantic import data_operation_service, data_operation_external

    @contextmanager
    def begin():
        yield object()
    engine = SimpleNamespace(begin=begin)
    monkeypatch.setattr(data_operation_service, "read_data_demand", lambda *a, **kw: {"project_id": "project:actual"})
    advances = [DemandAdvance("demand:actual", b'{"state":"awaiting-external"}', (b'{"native":"capture"}',), 1),
                DemandAdvance("demand:actual", b'{"state":"fulfilled"}', (b'{"native":"mapping"}',), 1)]
    native = MagicMock(side_effect=advances)
    monkeypatch.setattr(data_operation_service, "execute_data_demand", native)
    actor.session.queue.side_effect = [{"packets": [{"packet_id": "packet:actual", "operation_id": visual_requests.VISUAL_RECOGNIZE}]}, {"packets": []}]
    monkeypatch.setattr(data_operation_external, "ExternalDataSession", lambda *a, **kw: actor.session)
    complete = MagicMock(return_value=actor.published)
    monkeypatch.setattr(visual_requests, "execute_chandra_packet", complete)
    result = visual_requests.execute_visual_demand(engine, "demand:actual",
        visual_actor=visual_requests.ChandraActorInputs(actor.artifacts, actor.receipts), max_rounds=3)
    assert result.snapshot == b'{"state":"fulfilled"}'
    assert result.receipt_count == 3
    assert [wire_json_loads(value) for value in result.receipts] == [{"native": "capture"}, actor.published, {"native": "mapping"}]
    assert native.call_count == 2
    complete.assert_called_once()


def test_bounded_packet_group_reuses_child_and_drains_it_before_gpu_release(actor, monkeypatch):
    from contextlib import ExitStack

    events, owners = [], []
    factory = MagicMock(return_value=actor.runtime)
    monkeypatch.setattr(pdf_chandra, "ChandraRuntime", factory)
    @contextmanager
    def slot(**kwargs):
        events.append("gpu-open")
        try:
            yield
        finally:
            events.append("gpu-close")
    @contextmanager
    def suspended(*args, **kwargs):
        events.append("suspend-open")
        try:
            yield
        finally:
            events.append("suspend-close")
    @contextmanager
    def child(runtime):
        events.append("child-open")
        def recognize(pixels, *, check_active, before_submit):
            check_active()
            before_submit()
            return pixels
        try:
            yield recognize
        finally:
            events.append("child-close")
    monkeypatch.setattr(pdf_capacity, "pdf_gpu_slot", slot)
    monkeypatch.setattr(pdf_capacity, "suspend_resident_nemotron", suspended)
    monkeypatch.setattr(pdf_chandra, "supervised_chandra", child)
    with ExitStack() as lifetime:
        group = visual_requests._LocalChandraGroup(actor.artifacts, None, lifetime)
        for name in ("first", "second"):
            assert group.recognize(name.encode(), check_active=lambda n=name: owners.append(n),
                                   before_submit=lambda n=name: owners.append(n)) == name.encode()
        assert events == ["gpu-open", "suspend-open", "child-open"]
    assert factory.call_count == 1
    assert owners == ["first", "first", "second", "second"]
    assert events[-3:] == ["child-close", "suspend-close", "gpu-close"]
