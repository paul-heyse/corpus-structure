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
)


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
        version="gliner2-2.1.0-cpu-fp32-standard-whitespace-v1",
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


def test_cuda_profiles_are_explicit_and_cannot_reinterpret_cpu_history(profile):
    from corpus_structure.methods.gliner import CUDA_CODEPOINT_PROFILE, CUDA_WHITESPACE_PROFILE

    original = asdict(profile)
    whitespace = replace(profile, version=CUDA_WHITESPACE_PROFILE)
    codepoint = replace(profile, version=CUDA_CODEPOINT_PROFILE)
    assert profile.device == "cpu" and not profile.codepoint_splitter
    assert whitespace.device == codepoint.device == "cuda"
    assert not whitespace.codepoint_splitter and codepoint.codepoint_splitter
    assert len({profile.fingerprint, whitespace.fingerprint, codepoint.fingerprint}) == 3
    assert asdict(profile) == original
    assert "device" not in original  # historical serialized shape is unchanged


def test_new_profiles_default_to_cuda_without_changing_explicit_cpu_history(profile):
    values = asdict(profile)
    values.pop("version")
    assert GlinerProfile(**values).device == "cuda"
    assert GlinerProfile(**asdict(profile)).device == "cpu"


@pytest.mark.parametrize("kind", ["metadata", "frame", "input"])
def test_hosted_gliner_refuses_invalid_request_before_native_start(profile, kind):
    from types import SimpleNamespace
    from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
    from corpus_structure.methods.native_profiles import gliner_selection
    from corpus_structure.methods.native_host_clients import HostedGliner
    from corpus_structure.methods.gliner import CUDA_WHITESPACE_PROFILE

    selected = replace(profile, version=CUDA_WHITESPACE_PROFILE)
    if kind == "frame":
        selected = replace(selected, max_request_frame_bytes=128)
    frozen = gliner_selection(selected, {"runtime": "frozen-before-task"})
    calls = []
    group = SimpleNamespace(_selections={frozen.native.fingerprint: frozen}, policy=CharacterizationExecutionPolicy(), declare=lambda values: None, infer=lambda *args, **kwargs: calls.append(True))
    worker = HostedGliner(selected, group=group, native_profile=frozen.native.wire)
    pack = GlinerPack("release", "{}")
    item = GlinerInput("one", "a" * 64, "source")
    if kind == "metadata":
        pack = replace(pack, release="x"*(selected.max_metadata_bytes+1))
    elif kind == "input":
        item = replace(item, text="x"*(selected.max_input_bytes+1))
    with pytest.raises(GlinerRefused):
        worker.extract(pack, (item,))
    assert not calls and not worker.closed
