"""Acquisition and normalized composition do not prepare component packs."""

import json
import os
import subprocess
import sys
from pathlib import Path

from corpus_structure.semantic import regeneration
from corpus_structure.semantic.regeneration import DOMAINS


def test_acquire_and_compose_never_invoke_compiler(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("acquisition/composition must not compile")

    monkeypatch.setattr(regeneration, "prepare_release", forbidden)
    inputs = regeneration.acquire_pack(DOMAINS / "statistics")

    def ambient_read(path):
        raise AssertionError(f"ambient source read during composition: {path}")

    monkeypatch.setattr(Path, "read_bytes", ambient_read)
    first = regeneration.compose_pack_inputs((inputs,))
    second = regeneration.compose_pack_inputs((inputs,))
    assert first == second
    assert inputs.name == "statistics"
    assert inputs.bundle.sources
    assert not any(artifact.name.startswith("execution/") for artifact in first[1].artifacts)


def test_prepare_normalizes_duplicates_and_compiles_only_composed_root(monkeypatch):
    calls = []
    sentinel = object()

    def prepare(bundle, dependencies, profile):
        calls.append((bundle, dependencies, profile))
        return sentinel

    monkeypatch.setattr(regeneration, "prepare_release", prepare)
    result = regeneration.prepare_packs((DOMAINS / "statistics", DOMAINS / "statistics"))
    assert result[-1] is sentinel
    assert calls == [result[:3]]


def test_current_pack_acquisition_has_real_source_contracts_without_old_catalog(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("current pack preparation cannot compile or acquire an old catalog")

    bundle, dependencies, profile, prepared = regeneration.prepare_pack(DOMAINS / "statistics")
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model

    model = bound_data_operation_model(prepared)
    assert model.operation("data.inspect_data_operation_release").profile == "read"
    assert model.operation("rich.consolidate").profile == "derivation"
    admission = model.operation("rich.admit")
    assert admission.profile == "command"
    assert {effect.name for effect in admission.effects} == {"native-rich-knowledge-admission"}
    assert "StatisticsQualification" in prepared.index.definitions
    assert {"data_operation_rich_proposals", "source-readings"} <= {
        source.name for source in bundle.sources
    }
    pin_fields = {prop.name for prop in prepared.index.definitions["RecordSourcePin"].properties}
    assert {"source_product", "kind_contract", "subject_definition"} <= pin_fields
    assert not {"source_view_id", "native_product_task_id"} & pin_fields
    assert not any(artifact.name.startswith("execution/") for artifact in dependencies.artifacts)
    assert profile.version == "semantic-2"


REPO = DOMAINS.parent
STATISTICS = DOMAINS / "statistics"

HASHES = (
    "import sys; from pathlib import Path\n"
    "from corpus_structure.semantic.regeneration import prepare_packs\n"
    "c = prepare_packs((Path(sys.argv[1]),))[3]\n"
    "print(c.release_id, *(a.digest for a in c.artifacts))"
)


def test_hashes_are_equal_across_processes_hash_seeds_and_load_paths(tmp_path: Path) -> None:
    def run(path: str, cwd: Path, seed: str) -> str:
        env = {**os.environ, "PYTHONHASHSEED": seed}
        out = subprocess.run(
            [sys.executable, "-c", HASHES, path],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout

    absolute = run(str(STATISTICS), tmp_path, "1")
    relative = run("domains/statistics", REPO, "2")
    assert absolute == relative and absolute.split()[0].startswith("release:")


def test_ci_schema_compile_prints_the_artifacts(cli, tmp_path: Path) -> None:
    result = cli(
        "schema", "compile", "--domains", str(REPO / "domains"), "--json", "--out", str(tmp_path)
    )
    assert result.exit_code == 0, result.output
    out = json.loads(result.stdout)
    assert out["packs"] == ["statistics"] and out["release_id"].startswith("release:")
    assert out["operation_model_id"] is not None and out["artifacts"]
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "sources").is_dir()
    assert len(list(tmp_path.glob("*.artifact"))) == len(out["artifacts"])
    refused = cli("schema", "compile", "--domains", str(tmp_path), "--domain", "nothere")
    assert refused.exit_code == 1 and "semantic.yaml" in refused.stderr
