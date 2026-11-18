"""`tooling library metadata` over the conftest fixture environment, extended here with a
plugin, a stubs distribution and a dependent that needs the alpha package only through extras.
Expectations are written by hand from the fixture files."""

import json
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from corpus_tooling.library import metadata, selection
from corpus_tooling.library.app import REGISTRATIONS, make_library_app
from corpus_tooling.library.installed import Installation
from corpus_tooling.library.target import read_environment

EXTRA_DISTRIBUTIONS: dict[str, str] = {
    # The alpha package now records a py.typed marker (conftest's RECORD lists only __init__).
    "Alpha_Pkg-1.2.0.dist-info/RECORD": (
        "alpha/__init__.py,,\nalpha/py.typed,,\nAlpha_Pkg-1.2.0.dist-info/METADATA,,\n"
    ),
    "alpha/__init__.py": "",
    "alpha/py.typed": "",
    # A plugin: requires alpha unconditionally and declares an entry point in its group.
    "alpha_plugin-0.5.0.dist-info/METADATA": (
        "Metadata-Version: 2.4\n"
        "Name: alpha-plugin\n"
        "Version: 0.5.0\n"
        "License-Expression: MIT\n"
        "Requires-Dist: Alpha.Pkg>=1.0\n"
    ),
    "alpha_plugin-0.5.0.dist-info/entry_points.txt": (
        "[alpha.plugins]\nfancy = alpha_plugin:Fancy\n"
    ),
    "alpha_plugin-0.5.0.dist-info/RECORD": (
        "alpha_plugin/__init__.py,,\nalpha_plugin-0.5.0.dist-info/METADATA,,\n"
    ),
    "alpha_plugin/__init__.py": "",
    # A PEP 561 stubs distribution for the `alpha` import name.
    "alpha_stubs-1.2.0.dist-info/METADATA": (
        "Metadata-Version: 2.1\nName: alpha-stubs\nVersion: 1.2.0\n"
    ),
    "alpha_stubs-1.2.0.dist-info/RECORD": (
        "alpha-stubs/__init__.pyi,,\nalpha_stubs-1.2.0.dist-info/METADATA,,\n"
    ),
    "alpha-stubs/__init__.pyi": "",
    # Needs alpha only through two of its own extras; shares only console_scripts with alpha.
    "omega-3.0.dist-info/METADATA": (
        "Metadata-Version: 2.1\n"
        "Name: omega\n"
        "Version: 3.0\n"
        "License: BSD-3-Clause\n"
        'Requires-Dist: alpha-pkg[fast]; extra == "alpha"\n'
        "Requires-Dist: Alpha_Pkg ; extra == 'all'\n"
        "Provides-Extra: alpha\n"
        "Provides-Extra: All\n"
    ),
    "omega-3.0.dist-info/entry_points.txt": "[console_scripts]\nomega = omega:main\n",
    "omega-3.0.dist-info/RECORD": "omega.py,,\nomega.pyi,,\nomega-3.0.dist-info/METADATA,,\n",
    "omega.py": "",
    "omega.pyi": "",
}

# What uv would report for the fixture project: alpha-pkg selected with its `fast` extra, beta
# selected, nothing else.
UV_DOCUMENT = {
    "members": [{"name": "fixture-root", "id": "root"}],
    "resolution": {
        "root": {
            "name": "fixture-root",
            "version": "0.0.0",
            "source": {"virtual": "."},
            "kind": "package",
            "dependencies": [{"id": "alpha-pkg[fast]"}],
        },
        "alpha-pkg[fast]": {
            "name": "alpha-pkg",
            "version": "1.2.0",
            "source": {"registry": {}},
            "kind": {"extra": "fast"},
            "dependencies": [{"id": "alpha-pkg"}, {"id": "beta"}],
        },
        "alpha-pkg": {
            "name": "alpha-pkg",
            "version": "1.2.0",
            "source": {"registry": {}},
            "kind": "package",
            "dependencies": [{"id": "beta"}],
        },
        "beta": {
            "name": "beta",
            "version": "2.0.0",
            "source": {"registry": {}},
            "kind": "package",
            "dependencies": [],
        },
    },
}


def _write(root: Path, files: dict[str, str]) -> None:
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


@pytest.fixture
def site(trees) -> Path:
    _write(trees.site_packages, EXTRA_DISTRIBUTIONS)
    return trees.site_packages


@pytest.fixture
def cli() -> typer.Typer:
    root = typer.Typer()

    @root.callback()
    def _root() -> None: ...

    root.add_typer(make_library_app((*REGISTRATIONS, metadata.register)), name="library")
    return root


@pytest.fixture
def uv_selects(monkeypatch) -> None:
    monkeypatch.setattr(selection, "run_uv_tree", lambda project, options: (UV_DOCUMENT, "0.13.7"))


def _run(cli, trees, *names: str):
    result = CliRunner().invoke(
        cli, ["library", "--project", str(trees.project), "metadata", *names, "--json"]
    )
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


def _by_name(envelope: dict) -> dict[str, dict]:
    return {item["distribution"]: item for item in envelope["items"]}


def test_alpha_metadata_extras_entry_points_typing_and_companions(cli, trees, site, uv_selects):
    envelope = _run(cli, trees, "ALPHA-pkg")
    assert envelope["view"] == "distribution_metadata"
    assert envelope["tool"]["authorities"]["uv"] == "0.13.7"
    (alpha,) = envelope["items"]
    assert alpha == {
        "kind": "distribution_metadata",
        "distribution": "alpha-pkg",
        "name": "Alpha_Pkg",
        "version": "1.2.0",
        "location": ".venv/lib/python3.12/site-packages/Alpha_Pkg-1.2.0.dist-info",
        "summary": "The alpha package.",
        "requires_python": ">=3.10",
        "license": None,
        "license_source": None,
        "provides_extra": ["fast"],
        "selected": True,
        "selected_extras": ["fast"],
        "unselected_extras": [],
        "requires_dist": ["beta>=2", 'gamma; extra == "fast"'],
        "entry_point_groups": ["alpha.plugins", "console_scripts"],
        "entry_points": {
            "alpha.plugins": ["extra = alpha.ext:Plugin"],
            "console_scripts": ["alpha = alpha.cli:main"],
        },
        "project_urls": [
            "Documentation: https://alpha.example/docs",
            "Home-page: https://alpha.example",
        ],
        "py_typed": True,
        "stub_files": False,
        "stubs_distributions": ["alpha-stubs"],
        "import_names": ["alpha"],
        "import_names_source": "top_level.txt",
        "shared_import_names": {},
        "editable": False,
        "required_by": ["alpha-plugin", "omega[all,alpha]"],
        "entry_point_peers": {"alpha.plugins": ["alpha-plugin"]},
    }
    assert envelope["coverage"]["unavailable_metadata"] == [
        {
            "subject": "alpha-pkg 1.2.0",
            "field": "license (License-Expression, License, classifier)",
        }
    ]
    assert any(
        note.startswith("selected and selected_extras come from uv") for note in envelope["notes"]
    )


def test_multi_owner_import_name_conditional_dependent_and_unselected(cli, trees, site, uv_selects):
    items = _by_name(_run(cli, trees, "beta", "gamma", "omega", "alpha-plugin"))
    beta, gamma, omega, plugin = (
        items["beta"],
        items["gamma"],
        items["omega"],
        items["alpha-plugin"],
    )
    assert beta["import_names"] == ["beta", "shared_ns"]
    assert beta["shared_import_names"] == {"shared_ns": ["gamma"]}
    assert gamma["shared_import_names"] == {"shared_ns": ["beta"]}
    assert beta["required_by"] == ["alpha-pkg"]
    assert gamma["required_by"] == ["alpha-pkg[fast]"]
    assert (beta["selected"], gamma["selected"]) == (True, False)
    assert gamma["selected_extras"] == []
    assert omega["provides_extra"] == ["all", "alpha"]
    assert omega["unselected_extras"] == ["all", "alpha"]
    assert omega["license"] == "BSD-3-Clause"
    assert omega["license_source"] == "License"
    assert (omega["py_typed"], omega["stub_files"]) == (False, True)
    assert omega["entry_point_peers"] == {}  # console_scripts is not a companion group
    assert plugin["entry_point_peers"] == {"alpha.plugins": ["alpha-pkg"]}
    assert plugin["license_source"] == "License-Expression"


def test_unmatched_name_is_unavailable_with_close_matches(cli, trees, site, uv_selects):
    envelope = _run(cli, trees, "alpah-pkg")
    assert envelope["items"] == []
    assert {"subject": "alpah-pkg", "field": "installed distribution"} in envelope["coverage"][
        "unavailable_metadata"
    ]
    assert any(
        note.startswith("alpah-pkg: no installed distribution") and "alpha-pkg" in note
        for note in envelope["notes"]
    )
    # The two unreadable fixture folders (delta, broken) are skipped inputs of the read.
    assert len(envelope["coverage"]["skipped_inputs"]) == 2


def test_editable_install_typing_is_unavailable_not_absent(cli, trees, site, uv_selects):
    (tool,) = _run(cli, trees, "local-tool")["items"]
    assert tool["editable"] is True
    assert (tool["py_typed"], tool["stub_files"]) == (None, None)
    assert tool["import_names"] == ["local_tool", "local_tool_helpers"]


def test_without_a_project_selection_is_unavailable(cli, trees, site):
    result = CliRunner().invoke(
        cli, ["library", "--project", str(trees.env_only), "metadata", "alpha-pkg", "--json"]
    )
    assert result.exit_code == 0, result.output
    envelope = json.loads(result.stdout)
    (alpha,) = envelope["items"]
    assert (alpha["selected"], alpha["selected_extras"], alpha["unselected_extras"]) == (
        None,
        None,
        None,
    )
    assert any(note.startswith("selection unavailable (no_project)") for note in envelope["notes"])
    assert "uv" not in envelope["tool"]["authorities"]


def test_reusable_functions_for_compare(trees, site):
    installation = Installation(read_environment(trees.project / ".venv"))
    (alpha,) = installation.lookup("alpha-pkg").matches
    assert metadata.advertised_extras(alpha) == ("fast",)
    assert metadata.entry_point_groups(alpha) == ("alpha.plugins", "console_scripts")
    assert [d.normalized_name for d in metadata.group_members(installation, "alpha.plugins")] == [
        "alpha-pkg",
        "alpha-plugin",
    ]
    graph = selection.SelectionGraph.from_document(UV_DOCUMENT)
    assert selection.selected_extras(graph, "Alpha_Pkg") == ("fast",)
    assert metadata.requirement_name("Alpha.Pkg[fast] >=1; extra == 'x'") == "alpha-pkg"
