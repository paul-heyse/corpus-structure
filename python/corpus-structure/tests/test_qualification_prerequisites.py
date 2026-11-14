"""Named asset checks admit availability before expensive scenario setup."""

from pathlib import Path

import pytest


@pytest.fixture
def prerequisite_checks(request):
    # pytest registers the existing conftest by its absolute path; do not import it twice.
    plugin = request.config.pluginmanager.get_plugin(str(Path(__file__).with_name("conftest.py")))
    assert plugin is not None
    return plugin


def test_pm2_assets_require_an_existing_directory(prerequisite_checks, monkeypatch, tmp_path):
    monkeypatch.delenv("CORPUS_PM2_NATIVE_TEST_ASSETS", raising=False)
    assert prerequisite_checks._missing_pm2_native_assets() == (
        "CORPUS_PM2_NATIVE_TEST_ASSETS must name an available native provider assets directory"
    )
    monkeypatch.setenv("CORPUS_PM2_NATIVE_TEST_ASSETS", str(tmp_path / "missing"))
    assert prerequisite_checks._missing_pm2_native_assets() is not None
    monkeypatch.setenv("CORPUS_PM2_NATIVE_TEST_ASSETS", str(tmp_path))
    assert prerequisite_checks._missing_pm2_native_assets() is None


def test_retained_assets_report_each_missing_or_lfs_pointer(prerequisite_checks, tmp_path):
    missing = tmp_path / "missing"
    pointer = tmp_path / "pointer"
    pointer.write_bytes(b"version https://git-lfs.github.com/spec/v1\noid sha256:fixture\n")
    assert prerequisite_checks._missing_retained_files((missing, pointer)) == (
        f"retained asset requires {missing}; retained asset requires Git LFS hydration of {pointer}"
    )
    missing.write_bytes(b"available original")
    pointer.write_bytes(b"available capture")
    assert prerequisite_checks._missing_retained_files((missing, pointer)) is None


def test_page85_requires_original_capture_and_recipe(prerequisite_checks, monkeypatch, tmp_path):
    monkeypatch.setattr(prerequisite_checks, "REPO", tmp_path)
    source = tmp_path / "explicit-original.pdf"
    monkeypatch.setenv("CORPUS_PDF_QUALIFICATION_SOURCE", str(source))
    capture = tmp_path / "docs/design_review/evidence/2026-10-31_pdf-serialization-retention/raw"
    payload = capture / "convert.payload.json"
    recipe = capture / "convert.recipe.json"
    assert prerequisite_checks._missing_page85_native_capture() == "; ".join(
        f"retained asset requires {path}" for path in (source, payload, recipe)
    )
    capture.mkdir(parents=True)
    source.write_bytes(b"%PDF-1.7 hydrated original")
    payload.write_bytes(b"{}")
    recipe.write_bytes(b"{}")
    assert prerequisite_checks._missing_page85_native_capture() is None


def test_task86_witness_checks_hydration_before_decompression(
    prerequisite_checks, monkeypatch, tmp_path
):
    witness = tmp_path / "witness.json.gz"
    monkeypatch.setenv("CORPUS_PDF_REPLAY_PAYLOAD", str(witness))
    assert prerequisite_checks._missing_task86_witness() == f"retained asset requires {witness}"
    witness.write_bytes(b"version https://git-lfs.github.com/spec/v1\n")
    assert prerequisite_checks._missing_task86_witness() == (
        f"retained asset requires Git LFS hydration of {witness}"
    )
    witness.write_bytes(b"\x1f\x8bavailable witness")
    assert prerequisite_checks._missing_task86_witness() is None
