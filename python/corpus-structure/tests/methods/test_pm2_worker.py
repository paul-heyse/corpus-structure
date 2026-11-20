"""Shared runtime identities retain transitive installed-distribution custody."""

import json
import subprocess
import sys
from importlib.metadata import PathDistribution

import pytest

from corpus_structure.methods import pm2_native
from corpus_structure.semantic.file_custody import FileCustodyError


def test_runtime_identity_tracks_transitive_distribution_reinstallation(tmp_path, monkeypatch):
    installed = list(pm2_native.distributions())
    metadata = tmp_path / "worker_transitive_dependency-1.0.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text("Name: worker-transitive-dependency\nVersion: 1.0\n")
    record = metadata / "RECORD"
    record.write_text("worker_dependency.py,sha256=first,8\n")
    monkeypatch.setattr(
        pm2_native, "distributions", lambda: [*installed, PathDistribution(metadata)]
    )

    first = pm2_native._runtime_identity("d1")
    assert pm2_native._runtime_identity("d1") == first
    record.write_text("worker_dependency.py,sha256=other,8\n")
    with pytest.raises(FileCustodyError, match=r"acquired file changed:.*RECORD; restart required"):
        pm2_native._runtime_identity("d1")
    restarted = subprocess.run(
        [
            sys.executable,
            "-c",
            "import json, sys\n"
            "from importlib.metadata import PathDistribution\n"
            "from pathlib import Path\n"
            "from corpus_structure.methods import pm2_native\n"
            "installed = list(pm2_native.distributions())\n"
            "pm2_native.distributions = lambda: [*installed, PathDistribution(Path(sys.argv[1]))]\n"
            "print(json.dumps(pm2_native._runtime_identity('d1')))\n",
            str(metadata),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    changed = json.loads(restarted.stdout)
    assert changed["lock_sha256"] == first["lock_sha256"]
    assert changed["distributions_sha256"] != first["distributions_sha256"]
