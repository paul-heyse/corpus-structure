"""Shared runtime identities retain transitive installed-distribution custody."""
from importlib.metadata import PathDistribution
from corpus_structure.methods import pm2_native

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
    changed = pm2_native._runtime_identity("d1")
    assert changed["lock_sha256"] == first["lock_sha256"]
    assert changed["distributions_sha256"] != first["distributions_sha256"]
