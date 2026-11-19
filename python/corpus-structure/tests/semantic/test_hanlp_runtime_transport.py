"""HanLP physical execution custody preserves its independently declared inference."""

from pathlib import Path

from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_runtime import prepare_data_operation_runtime
from corpus_structure.semantic.hanlp_products import (
    hanlp_execution_custody,
    hanlp_profile_assets,
    hanlp_provider_asset,
)
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.python_operation_sources import PythonSourceCollection
from corpus_structure.semantic.types import ResolvedDependencies, SourceArtifact, SourceBundle


def inputs(directory: Path, *, runtime: str, adapter: str = "pm2-native-1"):
    selection = NativeSelection(
        NativeProfile("hanlp", {"installed": runtime}, {}, {"adapter": adapter}, "float32", "sdpa"),
        directory,
    )
    return data_operation_dependencies(
        ResolvedDependencies(),
        python_sources=PythonSourceCollection(
            (),
            boundary_contracts=(
                hanlp_provider_asset(selection),
                hanlp_profile_assets(selection),
                hanlp_execution_custody(selection),
            ),
        ),
    )


def bundle():
    return SourceBundle(
        "tiny",
        (
            SourceArtifact(
                "tiny",
                b"""id: urn:tiny
name: tiny
prefixes: {t: 'urn:tiny:'}
default_prefix: t
classes: {Thing: {}}
""",
            ),
        ),
    )


def test_hanlp_changed_runtime_keeps_release_and_changes_exact_execution(tmp_path):
    first = inputs(tmp_path, runtime="installed-a")
    second = inputs(tmp_path, runtime="installed-b")
    a = prepare_release(bundle(), first)
    b = prepare_release(bundle(), second)
    assert a.release_id == b.release_id
    first_runtime = prepare_data_operation_runtime(
        a, first.artifacts, execution_profile="source-native", observed={}
    )
    second_runtime = prepare_data_operation_runtime(
        b, second.artifacts, execution_profile="source-native", observed={}
    )
    assert first_runtime.runtime_id != second_runtime.runtime_id
    name = "runtime-transport/hanlp/execution-custody"
    assert first_runtime.input(name).content != second_runtime.input(name).content


def test_hanlp_changed_inference_stays_a_material_release_change(tmp_path):
    original = prepare_release(bundle(), inputs(tmp_path, runtime="installed-a"))
    changed = prepare_release(
        bundle(), inputs(tmp_path, runtime="installed-a", adapter="changed-preprocessing")
    )
    assert original.release_id != changed.release_id
