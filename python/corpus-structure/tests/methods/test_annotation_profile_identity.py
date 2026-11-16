"""Independent execution identity and retained-column conservation controls."""

from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest
from annotation_support import controlled as controlled
from annotation_support import item, selected_item

from corpus_structure.ingest import annotations
from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.native_profiles import NativeProfile
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_value


def profile_and_run(configuration=None, **changes):
    configuration = configuration or SentenceConfig(exclude=("ner",), batch_size=2)
    wire = NativeProfile(
        "spacy",
        {"runtime": "controlled"},
        {"weights": "controlled"},
        configuration.model_dump(mode="json"),
        "float32",
        "cupy",
    ).wire
    wire.update(changes)
    native = NativeProfile(**wire)
    return native, dict(
        provider="spacy",
        model=configuration.model,
        model_version=configuration.model_version,
        runtime_version=configuration.spacy_version,
        execution_profile=source_value(native.wire),
    )


def admitted_snapshot(controlled, monkeypatch, wire, profile):
    import spacy

    from corpus_structure.semantic import native_annotations

    monkeypatch.setattr(native_annotations, "pipeline", lambda _: controlled)
    monkeypatch.setattr(spacy.util, "get_package_path", lambda _: Path("controlled-fixture"))
    execution = SimpleNamespace(
        native_group=SimpleNamespace(_selections={}),
        declare_native=lambda *_: None,
        lazy_work=lambda *_args, **_kwargs: SimpleNamespace(
            try_submit=lambda: None, abandon=lambda: None
        ),
    )
    return native_annotations.annotation_work(
        execution, (), profile, lambda: None, native_profile=wire
    )


def test_retained_identity_comes_from_original_snapshot_without_ambient_runtime(
    controlled, monkeypatch
):
    from corpus_structure.methods import native_profiles

    monkeypatch.setattr(
        native_profiles, "spacy_selection", lambda *_a, **_k: pytest.fail("ambient runtime lookup")
    )
    native, _run = profile_and_run()
    profile = AnnotationProfile(
        SentenceConfig(exclude=("ner",), batch_size=2), execution_profile=native.fingerprint
    )
    admitted_snapshot(controlled, monkeypatch, native.wire, profile)


@pytest.mark.parametrize(
    "changes",
    [
        {"threads": 2},
        {"interop_threads": 2},
        {"runtime_identity": {"runtime": "different"}},
        {"artifacts": {"weights": "different"}},
        {"backend": "different"},
    ],
)
def test_explicit_execution_request_does_not_relabel_different_retained_identity(
    changes, controlled, monkeypatch
):
    original, _ = profile_and_run()
    changed, _ = profile_and_run(**changes)
    demand = AnnotationProfile(
        SentenceConfig(exclude=("ner",), batch_size=2), execution_profile=original.fingerprint
    )
    with pytest.raises(ValueError, match="execution profile"):
        admitted_snapshot(controlled, monkeypatch, changed.wire, demand)


@pytest.mark.parametrize(
    "key,value",
    [
        ("device", "cpu"),
        ("dtype", "bfloat16"),
        ("cudnn_allow_tf32", True),
        ("matmul_precision", "high"),
    ],
)
def test_retained_profile_cannot_relabel_unsupported_device_or_numerical_contract(
    key, value, controlled, monkeypatch
):
    native, run = profile_and_run()
    wire = native.wire
    wire[key] = value
    run["execution_profile"] = source_value(wire)
    with pytest.raises(ValueError, match=r"native profile|native provider"):
        admitted_snapshot(
            controlled,
            monkeypatch,
            wire,
            AnnotationProfile(SentenceConfig(exclude=("ner",), batch_size=2)),
        )


def test_missing_snapshot_refuses_explicit_admission(controlled, monkeypatch):
    native, _run = profile_and_run()
    requested = AnnotationProfile(
        SentenceConfig(exclude=("ner",), batch_size=2), execution_profile=native.fingerprint
    )
    wire = native.wire
    del wire["threads"]
    with pytest.raises(ValueError, match="complete frozen snapshot"):
        admitted_snapshot(controlled, monkeypatch, wire, requested)
    with pytest.raises(ValueError, match="parameters"):
        admitted_snapshot(controlled, monkeypatch, native.wire, AnnotationProfile())


def test_direct_columns_roundtrip_through_current_annotations_with_same_dependency(controlled):
    from corpus_structure.semantic.sentence_products import retained_source_annotation_products
    from methods.declared_primary_fixture import retained_source_annotations

    profile = AnnotationProfile(SentenceConfig(exclude=("ner",), batch_size=2))
    request, source, frame, context = selected_item(controlled, "X X.", block_id="#/texts/1")
    (direct,) = annotations.annotate((request,), profile)
    native = controlled.selection().native
    profile = replace(profile, execution_profile=native.fingerprint)
    primary = retained_source_annotations(source, frame, context, (direct,), profile)
    (restored,) = retained_source_annotation_products(source, primary)
    assert asdict(restored) == asdict(direct)
    assert restored.dependency_digest == direct.dependency_digest
    assert restored.profile_digest == sha256(canonical_bytes(profile.identity())).hexdigest()


def test_direct_annotation_rejects_wrong_profile_before_pipeline_execution(controlled):
    profile = AnnotationProfile(execution_profile="wrong-frozen-profile")
    with pytest.raises(ValueError, match="execution profile"):
        tuple(annotations.annotate((item(controlled),), profile))
    assert controlled.calls == []


def test_processed_docs_honor_already_admitted_profile_without_ambient_selection(
    controlled, monkeypatch
):
    monkeypatch.setattr(
        controlled, "selection", lambda: pytest.fail("ambient selection during collection")
    )
    profile = AnnotationProfile(execution_profile="already-authenticated-admitted-thread-profile")
    assert tuple(annotations.annotate((), profile, processed_docs=())) == ()
    with pytest.raises(ValueError, match="authenticated execution profile"):
        tuple(annotations.annotate((), AnnotationProfile(), processed_docs=()))


def test_prepared_annotation_rejects_wrong_profile_or_parameters_before_declaration(
    controlled, monkeypatch
):
    from corpus_structure.methods.native_profiles import NativeSelection
    from corpus_structure.semantic import native_annotations

    monkeypatch.setattr(native_annotations, "pipeline", lambda _: controlled)
    import spacy

    monkeypatch.setattr(spacy.util, "get_package_path", lambda _: Path("controlled-fixture"))
    native, _run = profile_and_run(SentenceConfig(exclude=("ner",)))
    selection = NativeSelection(native, Path("controlled-fixture"))
    execution = SimpleNamespace(
        native_group=SimpleNamespace(_selections={native.fingerprint: selection}),
        declare_native=lambda *_: pytest.fail("declared wrong profile"),
    )
    with pytest.raises(ValueError, match="execution profile"):
        native_annotations.annotation_work(
            execution, (), AnnotationProfile(execution_profile="wrong"), lambda: None
        )
    other, _ = profile_and_run()
    with pytest.raises(ValueError, match="parameters"):
        native_annotations.annotation_work(
            execution, (), AnnotationProfile(), lambda: None, native_profile=other.wire
        )


def test_restoration_source_changes_construction_resource_identity(
    monkeypatch,
):
    from corpus_structure.semantic.constructions.resources import construction_digest

    original = construction_digest()
    read = Path.read_bytes

    def changed(path):
        content = read(path)
        return (
            content + b"\n# hypothetical restoration correction\n"
            if path.name == "sentence_products.py"
            else content
        )

    monkeypatch.setattr(Path, "read_bytes", changed)
    assert construction_digest() != original


@pytest.mark.parametrize("coerced", [True, 2.0])
def test_retained_configuration_cannot_coerce_frozen_wire_scalar_types(
    coerced, controlled, monkeypatch
):
    native, run = profile_and_run()
    wire = native.wire
    wire["parameters"]["batch_size"] = coerced
    run["execution_profile"] = source_value(wire)
    with pytest.raises(ValueError, match="parameters"):
        admitted_snapshot(
            controlled,
            monkeypatch,
            wire,
            AnnotationProfile(SentenceConfig(exclude=("ner",), batch_size=2)),
        )


def test_prepared_annotation_refuses_other_provider_before_declaration(controlled, monkeypatch):
    from corpus_structure.semantic import native_annotations

    monkeypatch.setattr(native_annotations, "pipeline", lambda _: controlled)
    import spacy

    monkeypatch.setattr(spacy.util, "get_package_path", lambda _: Path("controlled-fixture"))
    native = NativeProfile(
        "d1",
        {"fixture": "wrong-provider"},
        {},
        AnnotationProfile().configuration.model_dump(mode="json"),
        "bfloat16",
        "torch",
    )
    execution = SimpleNamespace(
        native_group=SimpleNamespace(_selections={}),
        declare_native=lambda *_: pytest.fail("declared other provider"),
    )
    with pytest.raises(ValueError, match="another provider"):
        native_annotations.annotation_work(
            execution, (), AnnotationProfile(), lambda: None, native_profile=native.wire
        )


def test_fixture_refuses_profiled_columns_without_their_snapshot(controlled):
    from methods.declared_primary_fixture import retained_source_annotations

    profile = AnnotationProfile()
    request, source, frame, context = selected_item(controlled, block_id="#/texts/1")
    (product,) = annotations.annotate((request,), profile)
    with pytest.raises(ValueError, match=r"execution|profile"):
        retained_source_annotations(source, frame, context, (product,), profile)


@pytest.mark.parametrize("missing", ["threads", "cudnn_allow_tf32", "device", "parameters"])
def test_prepared_annotation_refuses_incomplete_explicit_snapshot_before_declaration(
    controlled, monkeypatch, missing
):
    from corpus_structure.semantic import native_annotations

    monkeypatch.setattr(native_annotations, "pipeline", lambda _: controlled)
    native = controlled.selection().native
    wire = native.wire
    del wire[missing]
    execution = SimpleNamespace(
        native_group=SimpleNamespace(_selections={}),
        declare_native=lambda *_: pytest.fail("declared incomplete snapshot"),
    )
    with pytest.raises((ValueError, TypeError), match=r"complete frozen snapshot|missing"):
        native_annotations.annotation_work(
            execution, (), AnnotationProfile(), lambda: None, native_profile=wire
        )
