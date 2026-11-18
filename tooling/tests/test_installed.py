from pathlib import Path

from corpus_tooling.library.installed import EntryPoint, Installation
from corpus_tooling.library.target import read_environment


def _installation(trees) -> Installation:
    return Installation(read_environment(trees.project / ".venv"))


def test_lookup_hits_by_any_spelling_of_the_name(trees) -> None:
    installation = _installation(trees)
    for spelling in ("alpha-pkg", "Alpha_Pkg", "alpha.pkg", "ALPHA__PKG"):
        (hit,) = installation.lookup(spelling).matches
        assert hit.name == "Alpha_Pkg"
        assert hit.normalized_name == "alpha-pkg"
    alpha = installation.lookup("alpha-pkg").matches[0]
    assert alpha.version == "1.2.0"
    assert alpha.summary == "The alpha package."
    assert alpha.requires_python == ">=3.10"
    assert alpha.requires == ("beta>=2", 'gamma; extra == "fast"')
    assert alpha.extras == ("fast",)
    assert alpha.entry_points == (
        EntryPoint(group="alpha.plugins", name="extra", value="alpha.ext:Plugin"),
        EntryPoint(group="console_scripts", name="alpha", value="alpha.cli:main"),
    )
    assert alpha.project_urls == (
        ("Documentation", "https://alpha.example/docs"),
        ("Home-page", "https://alpha.example"),
    )
    assert alpha.import_names == ("alpha",)
    assert alpha.import_names_source == "top_level.txt"
    assert alpha.editable is False
    assert alpha.metadata_path == trees.site_packages / "Alpha_Pkg-1.2.0.dist-info"


def test_lookup_miss_offers_close_matches(trees) -> None:
    lookup = _installation(trees).lookup("gama")
    assert lookup.matches == ()
    assert "gamma" in lookup.close_matches
    assert _installation(trees).lookup("zzzzzz").close_matches == ()


def test_import_name_with_two_owners_and_names_inferred_from_record(trees) -> None:
    installation = _installation(trees)
    assert installation.import_map == {
        "_gamma_ext": ("gamma",),
        "alpha": ("alpha-pkg",),
        "beta": ("beta",),
        "gamma": ("gamma",),
        "local_tool": ("local-tool",),
        "local_tool_helpers": ("local-tool",),
        "shared_ns": ("beta", "gamma"),
    }
    owners = installation.import_owners("shared_ns.beta_part")
    assert [dist.normalized_name for dist in owners] == ["beta", "gamma"]
    gamma = installation.lookup("gamma").matches[0]
    assert gamma.import_names == ("_gamma_ext", "gamma", "shared_ns")
    assert gamma.import_names_source == "record"


def test_editable_distribution_is_mapped_from_its_pth_directory(trees) -> None:
    (tool,) = _installation(trees).lookup("local_tool").matches
    assert tool.editable is True
    assert tool.direct_url == f"file://{trees.root.as_posix()}/workspace/tool"
    assert tool.import_names == ("local_tool", "local_tool_helpers")
    assert tool.import_names_source == "editable_pth"


def test_editable_without_pth_falls_back_to_the_project_src(trees) -> None:
    (trees.site_packages / "local_tool.pth").unlink()
    (tool,) = _installation(trees).lookup("local-tool").matches
    assert tool.import_names == ("local_tool", "local_tool_helpers")
    assert tool.import_names_source == "editable_src"


def test_unreadable_metadata_is_a_skipped_input(trees) -> None:
    installation = _installation(trees)
    assert [dist.normalized_name for dist in installation.distributions] == [
        "alpha-pkg",
        "beta",
        "gamma",
        "local-tool",
    ]
    broken, delta = installation.skipped
    assert (Path(broken.input).name, broken.reason) == (
        "broken-0.0.0.dist-info",
        "unreadable_metadata",
    )
    assert broken.detail == "METADATA lacks Name or Version"
    assert (Path(delta.input).name, delta.reason) == (
        "delta-1.0.0.dist-info",
        "unreadable_metadata",
    )
    assert delta.detail.startswith("TypeError")
