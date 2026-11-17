"""Missing and unhydrated E5 custody is an external prerequisite, before inference."""

from semantic import actual_e5_support


def test_e5_prerequisite_names_absent_selected_snapshot(monkeypatch, tmp_path):
    missing = tmp_path / "absent-snapshot"
    monkeypatch.setattr(actual_e5_support, "configured_e5", lambda: (None, missing))
    assert actual_e5_support.missing_e5_snapshot() == f"configured E5 snapshot requires {missing}"


def test_e5_prerequisite_names_missing_and_pointer_assets_together(monkeypatch, tmp_path):
    monkeypatch.setattr(actual_e5_support, "configured_e5", lambda: (None, tmp_path))
    weights = tmp_path / "model.safetensors"
    weights.write_text("version https://git-lfs.github.com/spec/v1\noid sha256:unhydrated\n")
    reason = actual_e5_support.missing_e5_snapshot()
    assert f"configured E5 snapshot requires Git LFS hydration of {weights}" in reason
    assert f"configured E5 snapshot requires {tmp_path / 'modules.json'}" in reason
    assert f"configured E5 snapshot requires {tmp_path / 'tokenizer.json'}" in reason
