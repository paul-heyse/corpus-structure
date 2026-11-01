import json

from corpus_structure.settings import Settings


def test_native_candidate_refuses_runtime_target_and_existing_output_before_connection(
    cli, tmp_path, monkeypatch
):
    from corpus_structure.semantic import runtime

    def unexpected(*args, **kwargs):
        raise AssertionError("a refused authoring request must not acquire database resources")

    monkeypatch.setattr(runtime, "open_runtime_engine", unexpected)
    settings = Settings(
        database={
            "url": "postgresql://runtime@/ordinary",
            "maintenance_url": "postgresql://owner@/",
        }
    )
    out = tmp_path / "candidate"
    result = cli(
        "schema",
        "native-candidate",
        "--authoring-database",
        "ordinary",
        "--out",
        str(out),
        "--json",
        settings=lambda: settings,
    )
    assert result.exit_code == 1
    assert json.loads(result.stdout)["error"]["code"] == "SemanticRefusal"
    assert not out.exists()
    out.mkdir()
    (out / "retained").write_text("unchanged")
    result = cli(
        "schema",
        "native-candidate",
        "--authoring-database",
        "disposable",
        "--out",
        str(out),
        "--json",
        settings=lambda: settings,
    )
    assert result.exit_code == 1
    assert (out / "retained").read_text() == "unchanged"
