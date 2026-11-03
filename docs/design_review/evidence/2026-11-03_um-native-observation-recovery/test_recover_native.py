"""Invalid immutable witnesses refuse before database acquisition or output creation."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def tool():
    path = Path(__file__).with_name("recover_native.py")
    spec = importlib.util.spec_from_file_location("um_native_recovery_tool", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("length,digest", [(3, "0" * 64), (500, "0" * 64)])
def test_bad_envelope_identity_is_refused(tool, tmp_path, length, digest):
    path = tmp_path / "native.json"
    path.write_bytes(b"{}\n")
    with pytest.raises(ValueError, match="byte identity differs"):
        tool.checked_envelope(path, {"byte_length": length, "content_digest": digest})


def test_execute_cli_rejects_changed_binding_before_any_database_or_output(tmp_path):
    witnesses = tmp_path / "witnesses"
    witnesses.mkdir()
    (witnesses / "retained-2-native.binding.json").write_text(json.dumps({
        "task_id": 2, "product_key": "native", "content_digest": "0" * 64,
    }))
    output = tmp_path / "must-not-exist"
    result = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("recover_native.py")),
         "--witnesses", str(witnesses), "--original", str(tmp_path / "not-opened.pdf"),
         "--execute", "--head", "not-used", "--output", str(output)],
        text=True, capture_output=True, check=False,
    )
    assert result.returncode != 0
    assert "native binding differs from the accepted observation witness" in result.stderr
    assert not output.exists()
