import json
import os
import shutil
from dataclasses import asdict, replace
from hashlib import sha256
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest
import yaml

from corpus_structure.methods.gliner import (
    GlinerInput,
    GlinerPack,
    GlinerPreparation,
    GlinerProfile,
    GlinerRefused,
    GlinerReport,
    effective_profile_fingerprint,
    map_literal,
    map_record_field,
    prepare_input,
)
from corpus_structure.methods.gliner_worker import (
    GlinerWorker,
    GlinerWorkerError,
    _Reply,
    _send_reply,
)
from methods.gliner_worker_cases import controlled_child


@pytest.fixture
def profile(tmp_path):
    return GlinerProfile(
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
        timeout_seconds=5,
    )


def declaration() -> dict[str, Any]:
    return {
        "structures": {
            "definition": {
                "mode": "natural",
                "anchor": "term",
                "fields": [
                    {"name": "term", "dtype": "str", "cardinality": "optional_one"},
                    {
                        "name": "kind",
                        "dtype": "str",
                        "choices": ["distribution", "theorem"],
                        "cardinality": "optional_one",
                    },
                ],
            }
        }
    }


def test_strict_schema_and_order():
    source = declaration()
    pack = GlinerPack.from_declaration("release1", source)
    assert pack.compile().to_dict()["structures"]["definition"]["anchor"] == "term"
    assert pack.field_is_classified("definition", "kind")
    assert not pack.field_is_classified("definition", "term")
    source["structures"]["definition"]["fields"].reverse()
    assert GlinerPack.from_declaration("release1", source).fingerprint != pack.fingerprint
    del source["structures"]["definition"]["anchor"]
    with pytest.raises(GlinerRefused, match="explicit natural"):
        GlinerPack.from_declaration("release1", source)
    with pytest.raises(ValueError):
        GlinerPack.from_declaration("release1", {"unsupported": []})


def test_native_preparation_boundaries(profile):
    prepared = SimpleNamespace(
        text="İe\u0301\u200d.", start_token_idx=[0, 4], end_token_idx=[4, 5], input_ids=[1, 2, 3]
    )
    calls = []

    def transform(text, schema, max_len):
        calls.append((text, schema, max_len))
        return prepared

    model = SimpleNamespace(processor=SimpleNamespace(transform_record=transform))
    item = GlinerInput("context", "b" * 64, "İe\u0301\u200d")
    receipt = prepare_input(model, "native-schema", item, profile)
    assert calls == [(item.text, "native-schema", None)]
    assert (receipt.synthetic_suffix, receipt.words, receipt.subwords) == (".", 2, 3)
    with pytest.raises(GlinerRefused, match="word bound"):
        prepare_input(model, "schema", item, replace(profile, max_words=1))
    with pytest.raises(GlinerRefused, match="subword bound"):
        prepare_input(model, "schema", item, replace(profile, max_subwords=2))
    with pytest.raises(GlinerRefused, match="byte bound"):
        prepare_input(model, "schema", item, replace(profile, max_input_bytes=1))
    prepared.text = "changed"
    with pytest.raises(GlinerRefused, match="changed source"):
        prepare_input(model, "schema", item, profile)


class ControlledWorker(GlinerWorker):
    _child_target = staticmethod(controlled_child)


def test_resident_worker_empty_is_success(profile):
    worker = ControlledWorker(profile)
    pack = GlinerPack("release", "{}")
    try:
        result = worker.extract(pack, (GlinerInput("one", "a" * 64, "empty"),))
        pid = worker.pid
        assert result[0].raw == {}
        second = worker.extract(pack, (GlinerInput("two", "b" * 64, "empty"),))
        assert worker.pid == pid and second[0].context_id == "two"
    finally:
        worker.close()
    assert worker.closed and worker.pid is None


@pytest.mark.parametrize("mode", ["crash", "error", "stale"])
def test_failure_retires_owner(profile, mode):
    worker = ControlledWorker(profile)
    with pytest.raises(GlinerWorkerError):
        worker.extract(GlinerPack("release", "{}"), (GlinerInput("one", "a" * 64, mode),))
    assert worker.closed and worker.pid is None
    with pytest.raises(GlinerWorkerError, match="closed"):
        worker.extract(GlinerPack("release", "{}"), (GlinerInput("one", "a" * 64, "empty"),))


def test_request_refusal_keeps_the_same_healthy_resident_for_independent_input(profile):
    worker = ControlledWorker(profile)
    try:
        with pytest.raises(GlinerRefused, match="controlled request limit"):
            worker.extract(GlinerPack("release", "{}"), (GlinerInput("one", "a" * 64, "refused"),))
        first_pid = worker.pid
        assert first_pid is not None and not worker.closed
        (report,) = worker.extract(
            GlinerPack("release", "{}"), (GlinerInput("two", "b" * 64, "empty"),)
        )
        assert report.context_id == "two"
        assert worker.pid == first_pid and not worker.closed
    finally:
        worker.close()


def test_production_child_loop_continues_after_native_preparation_refusal(profile):
    from methods.gliner_worker_cases import native_protocol_child

    class NativeProtocolWorker(GlinerWorker):
        _child_target = staticmethod(native_protocol_child)

    # This checks protocol recovery, not startup latency. Real preparation imports
    # compete with the full suite; the dedicated timeout test retains its short budget.
    worker = NativeProtocolWorker(replace(profile, timeout_seconds=60))
    pack = GlinerPack.from_declaration("release", {"entities": ["term"]}, version="native-local-v1")
    try:
        with pytest.raises(GlinerRefused, match="subword bound"):
            worker.extract(pack, (GlinerInput("one", "a" * 64, "refused"),))
        first_pid = worker.pid
        (report,) = worker.extract(pack, (GlinerInput("two", "b" * 64, "empty"),))
        assert worker.pid == first_pid and not worker.closed
        assert report.resident_reused and report.raw == {"entities": {"term": []}}
        from corpus_structure.methods.model_observation import installed_policy, request_digest

        inference = installed_policy()[0]["inference"]
        for policy in ("nested", "allow"):
            item = GlinerInput(policy, "c" * 64, "empty", "text.model_characterization/1:cue")
            (overlapping,) = worker.extract(pack, (item,), overlap_policy=policy)
            assert worker.pid == first_pid and overlapping.resident_reused
            assert overlapping.computation == request_digest(
                pack, asdict(worker.profile), (item,), 0.5, policy, False, inference
            )
            assert overlapping.computation != request_digest(
                pack, asdict(worker.profile), (item,), 0.5, policy, True, inference
            )
    finally:
        worker.close()


def test_timeout_kills_and_joins(profile):
    worker = ControlledWorker(replace(profile, timeout_seconds=0.5))
    with pytest.raises(GlinerWorkerError, match="timed out"):
        worker.extract(GlinerPack("release", "{}"), (GlinerInput("one", "a" * 64, "hang"),))
    assert worker.closed and worker.pid is None


def test_cancellation_startup_and_inference(profile):
    class Cancelled(BaseException):
        pass

    worker = ControlledWorker(profile)
    calls = 0

    def check_active():
        nonlocal calls
        calls += 1
        if calls >= 3:
            raise Cancelled()

    with pytest.raises(Cancelled):
        worker.extract(
            GlinerPack("release", "{}"),
            (GlinerInput("one", "a" * 64, "hang"),),
            check_active=check_active,
        )
    assert worker.closed and worker.pid is None


def test_admission_before_start(profile):
    worker = ControlledWorker(replace(profile, max_batch_bytes=2))
    with pytest.raises(GlinerRefused, match="byte bound"):
        worker.extract(GlinerPack("release", "{}"), (GlinerInput("one", "a" * 64, "too long"),))
    assert worker.pid is None
    worker._lock.acquire()
    try:
        with pytest.raises(GlinerRefused, match="saturated"):
            worker.extract(GlinerPack("release", "{}"), (GlinerInput("one", "a" * 64, "ok"),))
    finally:
        worker._lock.release()
        worker.close()


def test_native_splitter_unicode_coordinates():
    from gliner2.processing.word_splitter import WhitespaceTokenSplitter

    text = "İ e\u0301 a\u200db"
    assert list(WhitespaceTokenSplitter()(text)) == [
        ("i\u0307", 0, 1),
        ("e\u0301", 2, 4),
        ("a\u200db", 5, 8),
    ]


def test_profile_identity_and_artifact_mismatch(profile):
    assert replace(profile, max_words=100).fingerprint != profile.fingerprint
    assert replace(profile, threads=1).fingerprint != profile.fingerprint
    with pytest.raises(GlinerRefused, match="missing snapshot artifact"):
        profile.verify_artifacts()
    path = profile.snapshot / "config.json"
    path.write_text("changed")
    with pytest.raises(GlinerRefused, match="snapshot artifact differs"):
        profile.verify_artifacts()


def test_cancellation_before_native_start(profile):
    worker = ControlledWorker(profile)

    def no_ownership():
        raise RuntimeError("lease lost")

    with pytest.raises(RuntimeError, match="lease lost") as error:
        worker.extract(
            GlinerPack("release", "{}"),
            (GlinerInput("one", "a" * 64, "empty"),),
            check_active=no_ownership,
        )
    assert worker.closed and worker.pid is None
    assert any("operation=batch_extract" in note for note in error.value.__notes__)


def test_independent_ipc_cleanup_after_process_failure(profile):
    worker = ControlledWorker(profile)
    process = Mock(spec=BaseProcess)
    process.pid = 123
    process.is_alive.side_effect = [True, True, False]
    process.terminate.side_effect = RuntimeError("terminate failure")
    connection = Mock(spec=Connection)
    worker._process = process
    worker._connection = connection
    with pytest.raises(GlinerWorkerError, match="teardown failed") as failure:
        worker._stop(graceful=False)
    process.kill.assert_called_once_with()
    assert any("terminate failure" in note for note in failure.value.__notes__)
    connection.close.assert_called_once_with()
    assert worker._connection is None
    assert worker._process is None and worker.closed


@pytest.fixture
def source_context():
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.product_reference import ProductReference
    from corpus_structure.semantic.proposals import NativeFrameSource
    from corpus_structure.semantic.source_contexts import (
        NativeSourceContext,
        SourceSlice,
        SyntheticText,
    )

    pieces = [{"kind": "native_text", "item_ref": "#/texts/1", "start": 0, "end": 7}]
    native = {
        "pieces": pieces,
        "items": [{"self_ref": "#/texts/1"}],
        "ancestors": [],
        "health": {"inline_coverage": "unknown"},
    }
    projection = {**native, "text": "mean 12", "items": ["#/texts/1"]}
    source = NativeFrameSource(
        "unit:1",
        "mean 12",
        (),
        1,
        ProductReference(17, "integrated", "a" * 64),
        "#/groups/1",
        "direct",
        sha256(canonical_bytes(projection)).hexdigest(),
        "c" * 64,
        canonical_bytes(native).decode(),
        version=3,
    )
    context = NativeSourceContext(
        source,
        (),
        (SourceSlice(1, 0, 4), SyntheticText("|", "separator"), SourceSlice(1, 5, 7)),
        "test mapping",
        "fixture-policy",
        "explicit selection",
    )
    return context


def test_actual_context_owner_synthetic_crossing_and_classified_offsets(source_context):
    from corpus_structure.semantic.source_contexts import ContextRefused

    context = source_context
    item = GlinerInput.from_context(context)
    report = GlinerReport(
        item.context_id,
        item.context_digest,
        "compute",
        "profile",
        "pack",
        GlinerPreparation("mean|12.", ".", 4, 5, 7),
        "{}",
        "{}",
        0.0,
        False,
    )
    anchors = map_literal(report, context, {"text": "12", "start": 5, "end": 7})
    assert [(anchor.start, anchor.end, anchor.quote) for anchor in anchors] == [(5, 7, "12")]
    with pytest.raises(ContextRefused, match="synthetic"):
        map_literal(report, context, {"text": "mean|12", "start": 0, "end": 7})
    pack = GlinerPack.from_declaration("release", declaration())
    with pytest.raises(GlinerRefused, match="classified"):
        map_record_field(
            pack,
            "definition",
            "kind",
            replace(report, pack=pack.fingerprint),
            context,
            {"text": "mean", "start": 0, "end": 4},
        )

    with pytest.raises(GlinerRefused, match="another source context"):
        map_literal(
            replace(report, context_digest="e" * 64), context, {"text": "12", "start": 5, "end": 7}
        )
    with pytest.raises(GlinerRefused, match="reconstruct"):
        map_literal(report, context, {"text": ".", "start": 7, "end": 8})
    with pytest.raises(GlinerRefused, match="reconstruct"):
        map_literal(report, context, {"text": "distribution", "start": 0, "end": 4})
    assert dict(report.diagnostics)["suppression"] == "unavailable"


@pytest.mark.skipif(
    os.environ.get("CORPUS_GLINER_DIAGNOSTIC") != "1", reason="pinned Base checkpoint is opt-in"
)
def test_native_boundary_diagnostic_observes_and_rescores_exact_occurrence(source_context):
    from corpus_structure.methods.m1_source import M1Config
    from corpus_structure.methods.pm2_source import PM2SourceMap, SourceMapSegment

    declaration_path = Path(__file__).resolve().parents[4] / "domains/statistics/m1-methods.yaml"
    config = yaml.safe_load(declaration_path.read_text())["configs"]["extract.m1_candidates"][
        "default"
    ]
    profile = M1Config.model_validate(config).profile()
    mapping = PM2SourceMap(
        source_context,
        source_context.text,
        (SourceMapSegment(0, 4, 0), SourceMapSegment(5, 7, 5)),
        ((5, 7),),
    )
    pack = GlinerPack.from_declaration(
        "diagnostic-fixture", {"entities": {"number": "numeric literal"}}, version="native-local-v1"
    )
    worker = GlinerWorker(profile)
    try:
        with pytest.raises(GlinerRefused, match="atom"):
            worker.diagnose(pack, mapping, ((5, 6),))
        with pytest.raises(GlinerRefused, match="unmapped"):
            worker.diagnose(pack, mapping, ((0, 7),))
        assert worker.pid is None

        first = worker.diagnose(pack, mapping)
        assert first.raw["explicit"] == []
        assert first.raw["source_map_digest"] == mapping.input_digest
        assert first.request_digest is None and first.observation_digest is None
        native = next(row for row in first.raw["ordinary"] if row["input_chars"] == [5, 7])

        with pytest.raises(GlinerRefused, match="native word boundaries"):
            worker.diagnose(pack, mapping, ((0, 3),))

        second = worker.diagnose(pack, mapping, ((5, 7),))
        (explicit,) = second.raw["explicit"]
        assert second.resident_reused and second.computation != first.computation
        assert explicit["input_chars"] == [5, 7]
        assert explicit["ordinary_pair_logit"] == pytest.approx(native["pair_logit"])
        assert explicit["pair_logit"] == pytest.approx(native["pair_logit"], abs=1e-5)
    finally:
        worker.close()


@pytest.mark.parametrize("classified_first", [False, True])
def test_duplicate_field_names_refused_before_native_compilation(classified_first):
    source = declaration()
    first = {"name": "kind", "dtype": "str", "cardinality": "optional_one"}
    second = {**first, "choices": ["mean", "median"]}
    if classified_first:
        first, second = second, first
    source["structures"]["definition"]["fields"] = [
        {"name": "term", "dtype": "str", "cardinality": "optional_one"},
        first,
        second,
    ]
    with pytest.raises(GlinerRefused, match="duplicate structure field"):
        GlinerPack.from_declaration("release", source)
    # Direct detached declarations are still refused by the field interpretation seam.
    unchecked = GlinerPack("release", json.dumps(source))
    with pytest.raises(GlinerRefused, match="unambiguous"):
        unchecked.field_is_classified("definition", "kind")


def test_different_pack_cannot_reinterpret_classified_report_as_literal(source_context):
    classified = declaration()
    classified["structures"]["definition"]["fields"][1]["choices"] = ["mean", "median"]
    original_pack = GlinerPack.from_declaration("release", classified)
    literal = declaration()
    del literal["structures"]["definition"]["fields"][1]["choices"]
    foreign_pack = GlinerPack.from_declaration("release", literal)
    report = GlinerReport(
        source_context.dependency_digest,
        source_context.dependency_digest,
        "compute",
        "profile",
        original_pack.fingerprint,
        GlinerPreparation("mean|12.", ".", 4, 5, 7),
        "{}",
        "{}",
        0.0,
        False,
    )
    assert source_context.text[0:4] == "mean"  # Valid literal cue cannot override schema lineage.
    with pytest.raises(GlinerRefused, match="another schema pack"):
        map_record_field(
            foreign_pack,
            "definition",
            "kind",
            report,
            source_context,
            {"text": "mean", "start": 0, "end": 4},
        )


@pytest.fixture
def acquired_profiles(profile, tmp_path):
    original, relocated = tmp_path / "original", tmp_path / "relocated"
    hashes = []
    for name, _ in profile.artifact_hashes:
        path = original / name
        path.parent.mkdir(parents=True, exist_ok=True)
        content = ("independent fixture for " + name).encode()
        path.write_bytes(content)
        hashes.append((name, sha256(content).hexdigest()))
        copy = relocated / name
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, copy)
    return (
        replace(profile, snapshot=original, artifact_hashes=tuple(hashes)),
        replace(profile, snapshot=relocated, artifact_hashes=tuple(reversed(hashes))),
    )


@pytest.mark.parametrize(
    "extra",
    [
        "added_tokens.json",
        "special_tokens_map.json",
        "tokenizer.model",
        ".cache/download/metadata.json",
    ],
)
def test_snapshot_rejects_unbound_loader_inputs(acquired_profiles, extra):
    profile, _ = acquired_profiles
    profile.verify_artifacts()
    unexpected = profile.snapshot / extra
    unexpected.parent.mkdir(parents=True, exist_ok=True)
    unexpected.write_text("{}")
    with pytest.raises(GlinerRefused, match="unexpected snapshot entry"):
        profile.verify_artifacts()


def test_relocated_snapshot_and_permuted_manifest_preserve_computation_identity(acquired_profiles):
    left, right = acquired_profiles
    left.verify_artifacts()
    right.verify_artifacts()
    assert left.snapshot != right.snapshot
    assert left.artifact_hashes != right.artifact_hashes
    assert left.fingerprint == right.fingerprint
    effective_left = {
        "profile": left.fingerprint,
        "snapshot": str(left.snapshot),
        "config": {
            "_name_or_path": str(left.snapshot),
            "model_name": "semantic-backbone",
            "pool_size": 192,
        },
        "splitter": "whitespace",
        "dtype": "float32",
    }
    effective_right = {
        **effective_left,
        "snapshot": str(right.snapshot),
        "config": {**effective_left["config"], "_name_or_path": str(right.snapshot)},
    }
    fingerprint = effective_profile_fingerprint(json.dumps(effective_left))
    assert effective_profile_fingerprint(json.dumps(effective_right)) == fingerprint
    effective_right["config"]["pool_size"] = 193
    assert effective_profile_fingerprint(json.dumps(effective_right)) != fingerprint
    assert effective_left["config"]["_name_or_path"] == str(left.snapshot)


@pytest.mark.parametrize("metadata", ["context_id", "release", "pack_version"])
def test_oversized_detached_metadata_refused_before_child_start(profile, metadata):
    worker = ControlledWorker(profile)
    pack, item = GlinerPack("release", "{}"), GlinerInput("one", "a" * 64, "x")
    too_large = "x" * (profile.max_metadata_bytes + 1)
    if metadata == "context_id":
        item = replace(item, context_id=too_large)
    elif metadata == "release":
        pack = replace(pack, release=too_large)
    else:
        pack = replace(pack, version=too_large)
    with pytest.raises(GlinerRefused, match="metadata byte bound"):
        worker.extract(pack, (item,))
    assert worker.pid is None
    worker.close()


def test_entire_request_frame_refused_before_child_start(profile):
    worker = ControlledWorker(replace(profile, max_request_frame_bytes=128))
    with pytest.raises(GlinerRefused, match="request frame byte bound"):
        worker.extract(GlinerPack("release", "{}"), (GlinerInput("one", "a" * 64, "x"),))
    assert worker.pid is None and not worker.closed


@pytest.mark.parametrize("oversized", ["preparation", "metadata", "effective_config"])
def test_entire_native_reply_frame_includes_preparation_and_metadata(profile, oversized):
    bounded = replace(profile, max_reply_frame_bytes=2048)
    report = GlinerReport(
        "one",
        "a" * 64,
        "compute",
        "profile",
        "pack",
        GlinerPreparation("x", "", 1, 2, 1),
        "{}",
        "{}",
        0.0,
        False,
    )
    if oversized == "preparation":
        report = replace(report, preparation=replace(report.preparation, consumed_text="x" * 5000))
    elif oversized == "metadata":
        report = replace(report, context_id="x" * 5000)
    else:
        report = replace(report, effective_profile_json="x" * 5000)
    connection = Mock(spec=Connection)
    with pytest.raises(GlinerRefused, match="reply frame byte bound"):
        _send_reply(connection, _Reply(1, reports=(report,)), bounded)
    connection.send_bytes.assert_not_called()


@pytest.mark.parametrize("mode", ["oversized-preparation", "oversized-metadata"])
def test_oversized_peer_reply_retires_owner(profile, mode):
    worker = ControlledWorker(replace(profile, max_reply_frame_bytes=2048))
    with pytest.raises(GlinerWorkerError, match="IPC failed"):
        worker.extract(GlinerPack("release", "{}"), (GlinerInput("one", "a" * 64, mode),))
    assert worker.closed and worker.pid is None
