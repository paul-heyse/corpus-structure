"""`tooling library selection`: the graph reading against hand-written uv documents, the command
through a stubbed uv run, and uv itself (contract, stale-lock and no-interpreter tests, skipped
without uv)."""

import json
import os
import shutil
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from corpus_tooling.library import selection
from corpus_tooling.library.app import REGISTRATIONS, make_library_app
from corpus_tooling.library.selection import (
    SelectionGraph,
    SelectionOptions,
    UvSchemaChanged,
    load_selection,
    run_uv_tree,
    selection_items,
)
from corpus_tooling.library.target import Project

REGISTRY = {"registry": {"url": "https://pypi.org/simple"}}


def _node(name: str, version: str, kind, *dependencies, source=None) -> dict:
    return {
        "name": name,
        "version": version,
        "source": source or REGISTRY,
        "kind": kind,
        "dependencies": [
            {"id": target} if isinstance(target, str) else {"id": target[0], "marker": target[1]}
            for target in dependencies
        ],
    }


# Two members: `app` (the virtual workspace root) and `lib`. Edges run dependent -> dependency.
#   app      -> lib, alpha, beta[fast]          app:dev -> checker
#   lib      -> alpha, epsilon (marker linux)   beta[fast] -> beta, delta
#   alpha    -> gamma      epsilon -> gamma     delta -> gamma
# gamma is transitive through four paths; zeta is not selected.
APP = "app==0.0.0@virtual+/w"
LINUX = "sys_platform == 'linux'"
DOCUMENT = {
    "schema": {"version": "preview"},
    "inverted": False,
    "members": [
        {"name": "app", "path": "/w", "id": APP},
        {"name": "lib", "path": "/w/lib", "id": "lib==0.1.0@editable+/w/lib"},
    ],
    "resolution": {
        "workspace+/w": {"kind": "workspace", "path": "/w", "dependencies": []},
        APP: _node(
            "app",
            "0.0.0",
            "package",
            "lib==0.1.0@editable+/w/lib",
            "alpha==1.0@r",
            "beta[fast]==2.0@r",
            source={"virtual": "/w"},
        ),
        "app:dev==0.0.0@virtual+/w": _node(
            "app", "0.0.0", {"group": "dev"}, "checker==3.0@r", source={"virtual": "/w"}
        ),
        "lib==0.1.0@editable+/w/lib": _node(
            "lib",
            "0.1.0",
            "package",
            "alpha==1.0@r",
            ("epsilon==0.5@r", LINUX),
            source={"editable": "/w/lib"},
        ),
        "alpha==1.0@r": _node("alpha", "1.0", "package", "gamma==4.0@r"),
        "beta[fast]==2.0@r": _node("beta", "2.0", {"extra": "fast"}, "beta==2.0@r", "delta==1.1@r"),
        "beta==2.0@r": _node("beta", "2.0", "package"),
        "checker==3.0@r": _node("checker", "3.0", "package"),
        "delta==1.1@r": _node("delta", "1.1", "package", "gamma==4.0@r"),
        "epsilon==0.5@r": _node("epsilon", "0.5", "package", "gamma==4.0@r"),
        "gamma==4.0@r": _node("gamma", "4.0", "package"),
    },
}

OPTIONS = SelectionOptions()


def _items(document=DOCUMENT, names=("gamma",), paths=5):
    graph = SelectionGraph.from_document(document)
    return {
        (item.distribution, item.version): item
        for item in selection_items(graph, names, OPTIONS, paths)
    }


def test_transitive_distribution_reports_every_path_shortest_first() -> None:
    gamma = _items()[("gamma", "4.0")]
    assert gamma.selected is True
    assert gamma.direct is False
    assert gamma.required_by == ["alpha", "delta", "epsilon"]
    assert gamma.path_count == 4
    assert gamma.paths == [
        "app > alpha > gamma",
        "lib > alpha > gamma",
        f"lib >[{LINUX}] epsilon > gamma",
        "app > beta[fast] > delta > gamma",
    ]
    assert gamma.via_extras == ["beta[fast]"]
    assert gamma.via_groups == []
    assert gamma.markers == []
    assert gamma.unconditional is True
    assert gamma.source == "registry"
    assert gamma.scope == "platform=universal groups=default lock=unverified"


def test_direct_selection_through_an_extra_node_reports_the_extra() -> None:
    beta = _items(names=("Beta",))[("beta", "2.0")]
    assert beta.direct is True
    assert beta.selected_extras == ["fast"]
    assert beta.required_by == ["app"]
    assert beta.paths == ["app > beta[fast] > beta"]
    assert beta.via_extras == []


def test_group_node_selects_directly_and_is_named() -> None:
    checker = _items(names=("checker",))[("checker", "3.0")]
    assert checker.direct is True
    assert checker.via_groups == ["app:dev"]
    assert checker.required_by == ["app:dev"]
    assert checker.paths == ["app:dev > checker"]


def test_marker_edge_is_reported_and_makes_the_only_path_conditional() -> None:
    epsilon = _items(names=("epsilon",))[("epsilon", "0.5")]
    assert epsilon.direct is True
    assert epsilon.markers == [LINUX]
    assert epsilon.unconditional is False
    assert epsilon.paths == [f"lib >[{LINUX}] epsilon"]


def test_not_selected_is_a_row_not_an_error() -> None:
    zeta = _items(names=("zeta",))[("zeta", None)]
    assert zeta.selected is False
    assert zeta.direct is False
    assert zeta.paths == []
    assert zeta.path_count == 0
    assert zeta.unconditional is None


def test_paths_are_bounded_but_counted() -> None:
    gamma = _items(paths=2)[("gamma", "4.0")]
    assert gamma.paths == ["app > alpha > gamma", "lib > alpha > gamma"]
    assert gamma.path_count == 4


def test_member_is_selected_by_the_member_that_depends_on_it() -> None:
    lib = _items(names=("lib",))[("lib", "0.1.0")]
    assert lib.workspace_member is True
    assert lib.direct is True
    assert lib.paths == ["app > lib"]


def test_a_forked_resolution_gives_one_row_per_version_with_versioned_labels() -> None:
    document = {
        "members": [{"name": "app", "id": APP}],
        "resolution": {
            APP: _node(
                "app",
                "0.0.0",
                "package",
                ("omega==1.0@r", "python_full_version < '3.13'"),
                ("omega==2.0@r", "python_full_version >= '3.13'"),
            ),
            "omega==1.0@r": _node("omega", "1.0", "package"),
            "omega==2.0@r": _node("omega", "2.0", "package"),
        },
    }
    items = _items(document, names=("omega",))
    assert sorted(items) == [("omega", "1.0"), ("omega", "2.0")]
    assert items[("omega", "1.0")].paths == ["app >[python_full_version < '3.13'] omega==1.0"]
    assert items[("omega", "2.0")].markers == ["python_full_version >= '3.13'"]


def test_a_missing_field_is_reported_as_a_schema_change() -> None:
    with pytest.raises(UvSchemaChanged, match="resolution"):
        SelectionGraph.from_document({"members": []})
    broken = json.loads(json.dumps(DOCUMENT))
    del broken["resolution"]["gamma==4.0@r"]["dependencies"]
    with pytest.raises(UvSchemaChanged, match="dependencies"):
        SelectionGraph.from_document(broken)


def test_options_map_to_uv_flags_and_a_stated_scope() -> None:
    options = SelectionOptions(groups=("lint",), no_dev=True)
    assert options.uv_arguments() == ["--frozen", "--universal", "--group", "lint", "--no-dev"]
    assert options.describe() == "platform=universal groups=default+lint-dev lock=unverified"
    assert SelectionOptions(all_groups=True).uv_arguments() == [
        "--frozen",
        "--universal",
        "--all-groups",
    ]
    command = selection.uv_tree_command(
        "uv", Project(Path("/w"), Path("/w/uv.lock"), None), OPTIONS
    )
    assert command == [
        "uv",
        "tree",
        "--project",
        "/w",
        "--frozen",
        "--universal",
        "--offline",
        "--no-python-downloads",
        "--color",
        "never",
        "--format",
        "json",
        "--preview-features",
        "json-output",
    ]


# --- the command, with uv stubbed ------------------------------------------------------------


@pytest.fixture
def cli() -> typer.Typer:
    root = typer.Typer()

    @root.callback()
    def _root() -> None: ...

    root.add_typer(make_library_app((*REGISTRATIONS, selection.register)), name="library")
    return root


@pytest.fixture
def uv_runs(monkeypatch) -> list[SelectionOptions]:
    seen: list[SelectionOptions] = []

    def fake(project, options):
        seen.append(options)
        return DOCUMENT, "0.13.7"

    monkeypatch.setattr(selection, "run_uv_tree", fake)
    return seen


def test_command_delivers_items_scope_and_uv_version(cli, trees, uv_runs) -> None:
    result = CliRunner().invoke(
        cli,
        [
            "library",
            "--project",
            str(trees.project),
            "selection",
            "gamma",
            "zeta",
            "--group",
            "lint",
            "--paths",
            "1",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    envelope = json.loads(result.stdout)
    assert envelope["view"] == "selection"
    assert envelope["tool"]["authorities"]["uv"] == "0.13.7"
    assert uv_runs == [SelectionOptions(groups=("lint",))]
    assert [(item["distribution"], item["selected"]) for item in envelope["items"]] == [
        ("gamma", True),
        ("zeta", False),
    ]
    assert envelope["items"][0]["paths"] == ["app > alpha > gamma"]
    assert envelope["coverage"]["scanned"] == 10  # every node but the workspace container
    notes = envelope["notes"]
    assert (
        "selection scope: platform=universal groups=default+lint lock=unverified (every "
        "platform: edges keep their markers and are not filtered to this machine)"
    ) in notes
    assert any(note.startswith("zeta: not in the resolution") for note in notes)
    assert any("at most 1 shortest paths" in note for note in notes)


def test_the_unverified_lock_is_always_stated(cli, trees, uv_runs) -> None:
    result = CliRunner().invoke(
        cli, ["library", "--project", str(trees.project), "selection", "gamma", "--json"]
    )
    assert result.exit_code == 0, result.output
    notes = json.loads(result.stdout)["notes"]
    assert any(note.startswith("uv.lock was read as it stands") for note in notes)
    removed = CliRunner().invoke(
        cli, ["library", "--project", str(trees.project), "selection", "gamma", "--frozen"]
    )
    assert removed.exit_code == 2  # --frozen and --universal are no longer options


def test_an_environment_without_a_project_is_refused(cli, trees, uv_runs) -> None:
    result = CliRunner().invoke(
        cli, ["library", "--project", str(trees.env_only), "selection", "gamma", "--json"]
    )
    assert result.exit_code == 3
    envelope = json.loads(result.stdout)
    assert envelope["status"] == "failed"
    assert envelope["error"]["kind"] == "no_project"
    assert uv_runs == []


def test_a_changed_schema_fails_with_exit_3(cli, trees, monkeypatch) -> None:
    monkeypatch.setattr(selection, "run_uv_tree", lambda project, options: ({"members": []}, "9.9"))
    result = CliRunner().invoke(
        cli, ["library", "--project", str(trees.project), "selection", "gamma", "--json"]
    )
    assert result.exit_code == 3
    assert json.loads(result.stdout)["error"]["kind"] == "uv_schema_changed"


# --- uv itself -------------------------------------------------------------------------------

needs_uv = pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not on PATH")

# A dependency-free project and the lock uv writes for it (uv 0.13.7, hand-copied).
SMALL_LOCK = (
    'version = 1\nrevision = 3\nrequires-python = ">=3.12"\n\n'
    '[[package]]\nname = "small"\nversion = "0.1.0"\nsource = { virtual = "." }\n'
)


def _small_project(root: Path, version: str) -> Project:
    root.mkdir()
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "small"\nversion = "{version}"\nrequires-python = ">=3.12"\n'
        "dependencies = []\n"
    )
    (root / "uv.lock").write_text(SMALL_LOCK)
    return Project(root=root, lock=root / "uv.lock", pyproject=root / "pyproject.toml")


@needs_uv
def test_uv_reads_a_current_lock(tmp_path) -> None:
    tree = load_selection(_small_project(tmp_path / "small", "0.1.0"))
    assert tree.graph.members == frozenset({"small"})
    assert tree.graph.is_selected("small")
    assert tree.uv_version != "unknown"


@needs_uv
def test_a_stale_lock_is_read_as_it_stands(tmp_path) -> None:
    project = _small_project(tmp_path / "small", "0.2.0")  # the lock still says 0.1.0
    tree = load_selection(project)
    assert [node.version for node in tree.graph.packages("small")] == ["0.1.0"]


@needs_uv
def test_uv_never_runs_the_project_environments_interpreter(tmp_path, monkeypatch) -> None:
    """D2: with a cold uv cache, `uv tree --locked` (or a current-platform `--frozen`) queries
    the project's `.venv/bin/python`. The command must never run it: the fake interpreter here
    would leave a marker file."""
    project = _small_project(tmp_path / "small", "0.1.0")
    marker = tmp_path / "interpreter-ran"
    python = project.root / ".venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text(f"#!/bin/sh\ntouch {marker}\nexit 1\n")
    python.chmod(0o755)
    (project.root / ".venv" / "pyvenv.cfg").write_text("home = /usr/bin\nversion_info = 3.12.7\n")
    monkeypatch.setenv("UV_CACHE_DIR", str(tmp_path / "cold-cache"))
    monkeypatch.setenv("UV_PYTHON", str(python))  # stripped before uv runs
    tree = load_selection(project, SelectionOptions(all_groups=True))
    assert tree.graph.is_selected("small")
    assert not marker.exists()
    assert os.environ["UV_PYTHON"] == str(python)


@needs_uv
def test_contract_uv_tree_json_holds_the_fields_this_reader_uses() -> None:
    """Pins the preview `uv tree --format json` fields against the repository's root project:
    a uv upgrade that renames or drops one fails here."""
    root = Path(__file__).resolve().parents[2]
    project = Project(root=root, lock=root / "uv.lock", pyproject=root / "pyproject.toml")
    document, _ = run_uv_tree(project, SelectionOptions())
    assert document["schema"] == {"version": "preview"}
    assert document["inverted"] is False
    assert all({"name", "id"} <= set(member) for member in document["members"])
    nodes = document["resolution"]
    member_ids = {member["id"] for member in document["members"]}
    assert member_ids <= set(nodes)
    kinds = set()
    for node in nodes.values():
        assert {"kind", "dependencies"} <= set(node)
        assert all("id" in edge and set(edge) <= {"id", "marker"} for edge in node["dependencies"])
        if node["kind"] == "workspace":
            continue
        assert {"name", "version", "source"} <= set(node)
        kind = node["kind"]
        kinds.add(kind if isinstance(kind, str) else next(iter(kind)))
    assert {"package", "extra", "group"} <= kinds
    assert any("marker" in edge for node in nodes.values() for edge in node["dependencies"])
    graph = SelectionGraph.from_document(document)
    assert graph.unknown_kinds == ()
