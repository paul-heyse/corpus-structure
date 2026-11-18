"""LDT-05 `compare` against a hand-written fixture pair: a package (`fixlib`, in a fake 3.12
environment) and a repository using it, in two uv projects.

Every expected state below is written by hand from the fixture source; the code under test is
never used to produce an expectation. Line numbers are found by searching the fixture text for a
hand-picked needle. Selection comes from a hand-written uv document (no live uv). The
deprecated-use rows need a real pyrefly run over the fixture; those tests skip when pyrefly is
not installed, and the parsing and join are also tested on hand-written pyrefly records.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from corpus_tooling.library import compare, selection
from corpus_tooling.library.app import REGISTRATIONS, make_library_app
from corpus_tooling.library.deprecated_use import (
    DeprecatedRecord,
    checked_modules,
    parse_pyrefly_output,
    run_pyrefly,
)
from corpus_tooling.library.target import read_environment

SITE = "lib/python3.12/site-packages"

# --- the package -----------------------------------------------------------------------------

INIT = '''\
"""Fixture library for the compare tests."""

from typing import TYPE_CHECKING

from typing_extensions import deprecated

from fixlib._core import Engine, Report, configure, make_engine
from fixlib.plugins import Hook, PluginBase, load_plugins, register, register_hook
from fixlib.settings import Options

if TYPE_CHECKING:
    from fixlib.stamps import *
    from fixlib.twins_a import *
    from fixlib.twins_b import *

__all__ = [
    "Engine",
    "Hook",
    "Options",
    "PluginBase",
    "Report",
    "Stamp",
    "Twin",
    "configure",
    "legacy",
    "load_plugins",
    "make_engine",
    "register",
    "register_hook",
    "unused_helper",
]


@deprecated("Use make_engine instead.")
def legacy(workers: int = 1) -> Engine:
    """Make an engine the old way."""
    return make_engine(workers)


def unused_helper() -> None:
    """Nobody calls this from the main project."""


def __getattr__(name: str) -> object:
    raise AttributeError(name)
'''

CORE = '''\
"""A private module whose definitions the package exposes at its top level."""

from typing_extensions import deprecated


class Engine:
    """Runs jobs."""

    def __init__(self, workers: int = 1, *, name: str = "engine") -> None:
        self.workers = workers

    def start(self) -> None:
        """Start."""

    def stop(self) -> None:
        """Stop."""

    def report(self) -> "Report":
        """What ran."""

    @deprecated("Use start instead.")
    def run(self) -> None:
        """The old way to start."""


class Report:
    """Returned by `Engine.report`; the repository never names it."""

    def summary(self) -> str:
        """One line."""
        return ""


def make_engine(workers: int = 1, retries: int = 0, *, label: str = "") -> Engine:
    """Make an engine."""
    return Engine(workers)


def configure(path: str, strict: bool = False, **options: object) -> None:
    """Configure from a file."""
'''

PLUGINS = '''\
"""Extension points."""

import abc
from importlib.metadata import entry_points
from typing import Protocol

_REGISTRY: dict[str, type] = {}


class Hook(Protocol):
    """A hook nobody implements."""

    def __call__(self) -> None: ...


class PluginBase(abc.ABC):
    """Base for plugins."""

    @abc.abstractmethod
    def setup(self) -> None:
        """Prepare the plugin."""


def register(name: str):
    """Register a plugin class under a name."""

    def decorator(cls):
        _REGISTRY[name] = cls
        return cls

    return decorator


def register_hook(name: str, priority: int = 0) -> None:
    """Register a hook by name."""


def load_plugins() -> list[object]:
    """Load plugins from two entry-point groups."""
    return [*entry_points(group="fixlib.plugins"), *entry_points(group="fixlib.unused")]
'''

SETTINGS = '''\
"""Settings."""

from typing import TypedDict


class Options(TypedDict, total=False):
    """Engine options."""

    verbose: bool
    color: bool
'''

# A name defined in both branches of `if TYPE_CHECKING:` is not bound by the package's
# wildcard re-export in Griffe: `fixlib.Stamp` has no static binding.
STAMPS = '''\
from typing import TYPE_CHECKING

__all__ = ["Stamp"]

if TYPE_CHECKING:
    Stamp = int
else:

    class Stamp:
        """A stamp."""
'''

# The same in two modules: `fixlib.Twin` could come from either; the join does not guess.
TWINS = '''\
from typing import TYPE_CHECKING

__all__ = ["Twin"]

if TYPE_CHECKING:
    Twin = str
else:

    class Twin:
        """A twin."""
'''

PACKAGE = {
    "fixlib/__init__.py": INIT,
    "fixlib/_core.py": CORE,
    "fixlib/plugins.py": PLUGINS,
    "fixlib/settings.py": SETTINGS,
    "fixlib/stamps.py": STAMPS,
    "fixlib/twins_a.py": TWINS,
    "fixlib/twins_b.py": TWINS,
    "fixlib/py.typed": "",
}

SITE_FILES = {
    **PACKAGE,
    "fixlib_dist-1.0.0.dist-info/METADATA": (
        "Metadata-Version: 2.1\nName: fixlib-dist\nVersion: 1.0.0\n"
        "Provides-Extra: fast\nProvides-Extra: cli\n"
    ),
    "fixlib_dist-1.0.0.dist-info/RECORD": "".join(f"{path},,\n" for path in PACKAGE),
    "plugin_dist-0.1.0.dist-info/METADATA": (
        "Metadata-Version: 2.1\nName: plugin-dist\nVersion: 0.1.0\n"
    ),
    "plugin_dist-0.1.0.dist-info/entry_points.txt": "[fixlib.plugins]\np = plugin_mod:P\n",
    "plugin_dist-0.1.0.dist-info/RECORD": "plugin_mod.py,,\n",
    "plugin_mod.py": "class P: ...\n",
}

# --- the repository --------------------------------------------------------------------------

ENGINES = '''\
"""Uses of fixlib."""

import fixlib
from fixlib import Engine, Options, legacy
from fixlib._core import make_engine as build


class Turbo(Engine):
    """A repository subclass."""


@fixlib.register("turbo")
class TurboPlugin(fixlib.PluginBase):
    def setup(self) -> None: ...


def go(opts: dict[str, object]) -> Options:
    turbo = Turbo()
    turbo.start()
    Turbo.stop(turbo)
    turbo.run()
    fixlib.make_engine(1, 2)
    build(label="x")
    fixlib.configure("cfg.toml", **opts)
    fixlib.register_hook("h")
    fixlib.missing_thing()
    fixlib.Stamp()
    fixlib.Twin()
    legacy()
    return fixlib.Options(verbose=True)
'''

OTHER_APP = """\
import fixlib

fixlib.unused_helper()
"""

PYPROJECT = '[project]\nname = "consumer"\nrequires-python = ">=3.12"\n'
CONFIG = "implementation = CPython\nversion_info = 3.12.7\n"

UV_DOCUMENT = {
    "members": [{"name": "consumer", "id": "consumer"}],
    "resolution": {
        "consumer": {
            "name": "consumer",
            "version": "0.0.0",
            "source": {"virtual": "."},
            "kind": "package",
            "dependencies": [{"id": "fixlib-dist[fast]"}],
        },
        "fixlib-dist[fast]": {
            "name": "fixlib-dist",
            "version": "1.0.0",
            "source": {"registry": {}},
            "kind": {"extra": "fast"},
            "dependencies": [{"id": "fixlib-dist"}],
        },
        "fixlib-dist": {
            "name": "fixlib-dist",
            "version": "1.0.0",
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


def _project(root: Path) -> None:
    _write(root, {"pyproject.toml": PYPROJECT, "uv.lock": "version = 1\n"})
    _write(root / ".venv", {"pyvenv.cfg": CONFIG})
    _write(root / ".venv" / SITE, SITE_FILES)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", tmp_path.as_posix())
    monkeypatch.delenv("UV_PROJECT_ENVIRONMENT", raising=False)
    monkeypatch.delenv("TTY_COMPATIBLE", raising=False)
    monkeypatch.setattr(selection, "run_uv_tree", lambda project, options: (UV_DOCUMENT, "0.13.7"))
    root = tmp_path / "project"
    _project(root)
    _write(root, {"src/app/__init__.py": "", "src/app/engines.py": ENGINES})
    _project(root / "nested" / "other")
    _write(root / "nested" / "other", {"src/other_app/__init__.py": OTHER_APP})
    return root


@pytest.fixture
def cli() -> typer.Typer:
    root = typer.Typer()

    @root.callback()
    def _root() -> None: ...

    root.add_typer(make_library_app((*REGISTRATIONS, compare.register)), name="library")
    return root


def _run(cli: typer.Typer, repo: Path, *args: str):
    return CliRunner().invoke(cli, ["library", "--project", str(repo), "compare", *args])


def _view(cli: typer.Typer, repo: Path, view: str, *extra: str) -> dict:
    result = _run(
        cli, repo, "fixlib", "--scope", "src", "--view", view, "--json", "--limit", "0", *extra
    )
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


def _symbols(envelope: dict, project: str = ".") -> dict[str, dict]:
    return {item["path"]: item for item in envelope["items"] if item["project"] == project}


def _line(text: str, needle: str) -> int:
    return next(n for n, line in enumerate(text.splitlines(), start=1) if needle in line)


PYREFLY = shutil.which("pyrefly") or (
    str(Path(sys.executable).parent / "pyrefly")
    if os.access(Path(sys.executable).parent / "pyrefly", os.X_OK)
    else None
)
needs_pyrefly = pytest.mark.skipif(PYREFLY is None, reason="pyrefly is not installed")

# --- symbol states ---------------------------------------------------------------------------


def test_symbol_states_equal_the_hand_written_expectation(cli, repo) -> None:
    envelope = _view(cli, repo, "symbols", "--no-deprecated")
    assert envelope["view"] == "compare_symbol"
    rows = {
        path: (item["state"], item["declared_path"]) for path, item in _symbols(envelope).items()
    }
    referenced = "referenced"
    unreferenced = "unreferenced in scope"
    unresolved = "unresolved"
    expected = {
        # Defined in the private `_core`, exposed at the top: one symbol, used through both.
        "fixlib.make_engine": (referenced, "fixlib._core.make_engine"),
        "fixlib.Engine": (referenced, "fixlib._core.Engine"),
        # Inherited members reached through the repository subclass and its instance.
        "fixlib.Engine.start": (unresolved, "fixlib._core.Engine.start"),
        "fixlib.Engine.stop": (unresolved, "fixlib._core.Engine.stop"),
        "fixlib.Engine.run": (unresolved, "fixlib._core.Engine.run"),  # pyrefly not run here
        "fixlib.Engine.__init__": (unresolved, "fixlib._core.Engine.__init__"),
        "fixlib.Engine.workers": (unresolved, "fixlib._core.Engine.workers"),
        "fixlib.Engine.report": (unresolved, "fixlib._core.Engine.report"),
        # Never named, but `Engine.report` (reached) returns it: its members are unresolved.
        "fixlib.Report": (unreferenced, "fixlib._core.Report"),
        "fixlib.Report.summary": (unresolved, "fixlib._core.Report.summary"),
        "fixlib.configure": (referenced, "fixlib._core.configure"),
        "fixlib.register": (referenced, "fixlib.plugins.register"),
        "fixlib.register_hook": (referenced, "fixlib.plugins.register_hook"),
        "fixlib.PluginBase": (referenced, "fixlib.plugins.PluginBase"),
        "fixlib.PluginBase.setup": (unresolved, "fixlib.plugins.PluginBase.setup"),
        "fixlib.Hook": (unreferenced, "fixlib.plugins.Hook"),
        "fixlib.Hook.__call__": (unreferenced, "fixlib.plugins.Hook.__call__"),
        "fixlib.load_plugins": (unreferenced, "fixlib.plugins.load_plugins"),
        "fixlib.Options": (referenced, "fixlib.settings.Options"),
        "fixlib.Options.verbose": (referenced, "fixlib.settings.Options.verbose"),
        "fixlib.Options.color": (unresolved, "fixlib.settings.Options.color"),
        "fixlib.legacy": (referenced, "fixlib.legacy"),
        "fixlib.unused_helper": (unreferenced, "fixlib.unused_helper"),
        # The lazily exported `fixlib.Stamp`, recovered through `from fixlib.stamps import *`.
        "fixlib.stamps.Stamp": (referenced, "fixlib.stamps.Stamp"),
        # `fixlib.Twin` could be either; not joined, so neither is called unreferenced.
        "fixlib.twins_a.Twin": (unresolved, "fixlib.twins_a.Twin"),
        "fixlib.twins_b.Twin": (unresolved, "fixlib.twins_b.Twin"),
    }
    assert rows == expected
    items = _symbols(envelope)
    assert items["fixlib.make_engine"]["uses"] == {"call": 2, "import": 1}
    assert items["fixlib.Engine.start"]["detail"].startswith(
        "member of fixlib._core.Engine, which is subclassed in scope"
    )
    assert items["fixlib.stamps.Stamp"]["route"] == (
        "fixlib.Stamp: no static binding; recovered through `from fixlib.stamps import *` in its "
        "source"
    )
    assert items["fixlib.twins_a.Twin"]["detail"] == (
        "may be the lazily exported `fixlib.Twin`, which the join could not resolve"
    )
    assert items["fixlib.Options.verbose"]["uses"] == {"keyword": 1}
    assert items["fixlib.Report.summary"]["detail"].startswith(
        "member of fixlib._core.Report, which is in the annotation of fixlib._core.Engine.report"
    )


def test_states_filter_and_summary(cli, repo) -> None:
    unreferenced = _view(cli, repo, "symbols", "--no-deprecated", "--state", "unreferenced")
    assert sorted(_symbols(unreferenced)) == [
        "fixlib.Hook",
        "fixlib.Hook.__call__",
        "fixlib.Report",
        "fixlib.load_plugins",
        "fixlib.unused_helper",
    ]
    summary = _view(cli, repo, "summary", "--no-deprecated")
    assert summary["view"] == "compare_module"
    (top,) = [m for m in summary["items"] if m["project"] == "." and m["module"] == "fixlib"]
    # Engine (+ __init__, report, run, start, stop, workers), Hook (+ __call__), Options
    # (+ color, verbose), PluginBase (+ setup), Report (+ summary), configure, legacy,
    # load_plugins, make_engine, register, register_hook, unused_helper: 23 under `fixlib`.
    assert (top["symbols"], top["referenced"], top["unreferenced"], top["unresolved"]) == (
        23,
        9,
        5,
        9,
    )
    assert top["not_in_inventory"] == 2  # fixlib.missing_thing, fixlib.Twin
    assert top["unreferenced_examples"] == [  # shallowest first, at most five
        "fixlib.Hook",
        "fixlib.Report",
        "fixlib.load_plugins",
        "fixlib.unused_helper",
        "fixlib.Hook.__call__",
    ]


def test_not_in_inventory(cli, repo) -> None:
    envelope = _view(cli, repo, "not-in-inventory", "--no-deprecated")
    rows = {
        item["written_path"]: (item["reason"], item["resolved_prefix"], item["unmatched_tail"])
        for item in envelope["items"]
        if item["project"] == "."
    }
    assert rows == {
        "fixlib.missing_thing": ("unmatched_tail", "fixlib", "missing_thing"),
        "fixlib.Twin": ("unmatched_tail", "fixlib", "Twin"),
    }
    (twin,) = [i for i in envelope["items"] if i["written_path"] == "fixlib.Twin"]
    line = _line(ENGINES, "fixlib.Twin()")
    assert twin["first_location"] == f"src/app/engines.py:{line}:4"
    # The census labels it a call; only a joined class is reclassified as an instantiation.
    assert (twin["uses"], twin["count"], twin["files"]) == (["call"], 1, 1)


# --- parameters ------------------------------------------------------------------------------


def test_parameters_equal_the_hand_written_expectation(cli, repo) -> None:
    envelope = _view(cli, repo, "parameters", "--no-deprecated")
    rows = {
        (item["callable"], item["parameter"]): (item["parameter_kind"], item["state"])
        for item in envelope["items"]
        if item["project"] == "."
    }
    parameter, key = "parameter", "configuration_key"
    assert rows == {
        # `fixlib.make_engine(1, 2)` binds `retries` by position; `build(label=...)` the keyword.
        ("fixlib.make_engine", "workers"): (parameter, "passed"),
        ("fixlib.make_engine", "retries"): (parameter, "passed"),
        ("fixlib.make_engine", "label"): (parameter, "passed"),
        # Called once with **opts: what is not passed explicitly is unresolved.
        ("fixlib.configure", "path"): (parameter, "passed"),
        ("fixlib.configure", "strict"): (parameter, "unresolved"),
        ("fixlib.register_hook", "name"): (parameter, "passed"),
        ("fixlib.register_hook", "priority"): (parameter, "never passed"),
        ("fixlib.register", "name"): (parameter, "passed"),
        ("fixlib.legacy", "workers"): (parameter, "never passed"),
        # Subclassed, never called directly: its constructor's parameters are unresolved.
        ("fixlib.Engine", "workers"): (parameter, "unresolved"),
        ("fixlib.Engine", "name"): (parameter, "unresolved"),
        ("fixlib.Options", "verbose"): (key, "passed"),
        ("fixlib.Options", "color"): (key, "never passed"),
    }
    items = {(i["callable"], i["parameter"]): i for i in envelope["items"]}
    assert items[("fixlib.configure", "strict")]["detail"] == "a call passes *args or **kwargs"
    assert (
        items[("fixlib.make_engine", "retries")]["calls"],
        items[("fixlib.make_engine", "retries")]["passed_in"],
    ) == (2, 1)


# --- extension points, extras, entry points --------------------------------------------------


def test_extension_points(cli, repo) -> None:
    envelope = _view(cli, repo, "extension-points", "--no-deprecated")
    rows = [
        (item["path"], item["subclasses"], item["registrations"], item["state"])
        for item in envelope["items"]
        if item["project"] == "."
    ]
    # Those without a repository subclass or registration come first.
    assert rows == [
        ("fixlib.Hook", 0, 0, "unreferenced in scope"),
        ("fixlib.load_plugins", 0, 0, "unreferenced in scope"),
        ("fixlib.PluginBase", 1, 0, "referenced"),
        ("fixlib.register", 0, 1, "referenced"),
        ("fixlib.register_hook", 0, 1, "referenced"),
    ]


def test_extras_and_entry_point_groups(cli, repo) -> None:
    extras = _view(cli, repo, "extras", "--no-deprecated")
    assert [
        (item["project"], item["distribution"], item["extra"], item["selected"])
        for item in extras["items"]
    ] == [
        (".", "fixlib-dist", "cli", False),
        (".", "fixlib-dist", "fast", True),
    ]
    assert extras["tool"]["authorities"]["uv"] == "0.13.7"
    groups = _view(cli, repo, "entry-points", "--no-deprecated")
    assert [
        (item["group"], item["populated_by"], item["read_by"])
        for item in groups["items"]
        if item["project"] == "."
    ] == [
        ("fixlib.unused", [], "fixlib.plugins.load_plugins"),
        ("fixlib.plugins", ["plugin-dist"], "fixlib.plugins.load_plugins"),
    ]


# --- several projects, saved census, usage -------------------------------------------------


def test_a_scope_spanning_two_projects_is_compared_per_project_in_one_envelope(cli, repo) -> None:
    result = _run(
        cli,
        repo,
        "fixlib",
        "--scope",
        "src",
        "--scope",
        "nested/other/src",
        "--view",
        "symbols",
        "--no-deprecated",
        "--json",
        "--limit",
        "0",
    )
    assert result.exit_code == 0, result.output
    assert result.stdout.count("\n") == 1  # one envelope
    envelope = json.loads(result.stdout)
    assert {item["project"] for item in envelope["items"]} == {".", "nested/other"}
    main, other = _symbols(envelope, "."), _symbols(envelope, "nested/other")
    assert main["fixlib.unused_helper"]["state"] == "unreferenced in scope"
    assert other["fixlib.unused_helper"]["state"] == "referenced"
    assert other["fixlib.make_engine"]["state"] == "unreferenced in scope"
    assert any(
        note.startswith("project nested/other: environment nested/other/.venv")
        for note in envelope["notes"]
    )
    extras = json.loads(
        _run(
            cli,
            repo,
            "fixlib",
            "--scope",
            "src",
            "--scope",
            "nested/other/src",
            "--view",
            "extras",
            "--no-deprecated",
            "--json",
        ).stdout
    )
    assert {item["project"] for item in extras["items"]} == {".", "nested/other"}


def test_saved_census_gives_the_same_comparison(cli, repo, tmp_path) -> None:
    census_cli = typer.Typer()

    @census_cli.callback()
    def _root() -> None: ...

    census_cli.add_typer(make_library_app(REGISTRATIONS), name="library")
    saved = CliRunner().invoke(
        census_cli,
        [
            "library",
            "--project",
            str(repo),
            "census",
            "fixlib",
            "--scope",
            "src",
            "--sites",
            "--json",
            "--limit",
            "0",
        ],
    )
    assert saved.exit_code == 0, saved.output
    path = tmp_path / "census.json"
    path.write_text(saved.stdout, encoding="utf-8")
    direct = _view(cli, repo, "symbols", "--no-deprecated")
    result = _run(
        cli,
        repo,
        "fixlib",
        "--census",
        str(path),
        "--view",
        "symbols",
        "--no-deprecated",
        "--json",
        "--limit",
        "0",
    )
    assert result.exit_code == 0, result.output
    loaded = json.loads(result.stdout)
    assert loaded["items"] == direct["items"]
    assert any(note.startswith(f"census read from {path.as_posix()}") for note in loaded["notes"])


def test_scope_or_census_is_required_and_exclusive(cli, repo, tmp_path) -> None:
    neither = _run(cli, repo, "fixlib", "--json")
    assert (neither.exit_code, neither.stdout) == (2, "")
    assert "pass --scope" in neither.stderr
    saved = tmp_path / "c.json"
    saved.write_text("{}", encoding="utf-8")
    both = _run(cli, repo, "fixlib", "--scope", "src", "--census", str(saved), "--json")
    assert (both.exit_code, both.stdout) == (2, "")
    unreadable = _run(cli, repo, "fixlib", "--census", str(saved), "--json")
    assert unreadable.exit_code == 2
    missing = _run(cli, repo, "fixlib", "--scope", "nowhere", "--json")
    assert missing.exit_code == 2


def test_rendered_summary_is_bounded(cli, repo) -> None:
    result = _run(cli, repo, "fixlib", "--scope", "src", "--no-deprecated")
    assert result.exit_code == 0, result.output
    assert "view=compare_module" in result.stdout
    assert "# columns\tproject\tmodule\tsymbols" in result.stdout


# --- deprecated use --------------------------------------------------------------------------


@needs_pyrefly
def test_deprecated_use_is_reported_and_joined_to_the_inventory(cli, repo) -> None:
    envelope = _view(cli, repo, "deprecated")
    rows = [
        (
            item["path"],
            item["line"],
            item["column"],
            item["deprecated_path"],
            item["declared_path"],
            item["inventory_marked"],
        )
        for item in envelope["items"]
    ]
    engines = "src/app/engines.py"
    import_line = _line(ENGINES, "from fixlib import Engine, Options, legacy")
    assert rows == [
        # On the import line pyrefly names the bare imported name; the census import row joins it.
        (engines, import_line, 37, "fixlib.legacy", "fixlib.legacy", True),
        # Through an instance of a repository subclass: the census cannot attribute this one.
        (
            engines,
            _line(ENGINES, "turbo.run()"),
            5,
            "fixlib._core.Engine.run",
            "fixlib._core.Engine.run",
            True,
        ),
        (engines, _line(ENGINES, "    legacy()"), 5, "fixlib.legacy", "fixlib.legacy", True),
    ]
    assert envelope["items"][1]["message"] == "Use start instead."
    assert envelope["tool"]["authorities"]["pyrefly"]
    assert any(
        "deprecated use from pyrefly over exactly the scope's 2 Python files" in note
        for note in envelope["notes"]
    )
    symbols = _symbols(_view(cli, repo, "symbols"))
    # The deprecated-use authority shows `run` used, where the census alone left it unresolved.
    assert symbols["fixlib.Engine.run"]["state"] == "referenced"
    assert symbols["fixlib.Engine.run"]["uses"] == {"deprecated_use": 1}


def test_unmarked_and_unparsed_pyrefly_records_join_by_hand(repo) -> None:
    """A pyrefly row the inventory does not mark stands on its own; a description that does
    not parse is an unresolved row (hand-written records, no pyrefly run)."""
    from corpus_tooling.library.compare_join import compare_project
    from corpus_tooling.library.installed import Installation
    from corpus_tooling.library.inventory_items import InventorySelection, surface_inventory
    from corpus_tooling.library.surface import load_offered_surface

    environment = read_environment(repo / ".venv")
    surface = load_offered_surface(["fixlib"], environment.site_packages)
    inventory = surface_inventory(
        surface, "fixlib", Installation(environment), InventorySelection(depth=None)
    )
    path = repo / "src" / "app" / "engines.py"
    records = [
        (DeprecatedRecord(path, 3, 1, "fixlib.unused_helper", "gone"), "src/app/engines.py"),
        (DeprecatedRecord(path, 4, 1, None, "`odd` format"), "src/app/engines.py"),
        (DeprecatedRecord(path, 5, 1, "otherlib.thing", "other"), "src/app/engines.py"),
    ]
    result = compare_project(
        project=".",
        roots=["fixlib"],
        surface=surface,
        symbols=inventory.symbols,
        sites=[],
        unresolved=[],
        deprecated=records,
    )
    (use,) = result.deprecated
    assert (use.deprecated_path, use.declared_path, use.inventory_marked) == (
        "fixlib.unused_helper",
        "fixlib.unused_helper",
        False,
    )
    assert [problem.kind for problem in result.deprecated_problems] == ["deprecated_unparsed"]
    assert result.deprecated_elsewhere == 1
    states = {state.offered.path: state.state for state in result.symbols}
    assert states["fixlib.unused_helper"] == "referenced"


PYREFLY_DOCUMENT = {
    "errors": [
        {
            "line": 1,
            "column": 20,
            "stop_line": 1,
            "stop_column": 30,
            "path": "src/app/use.py",
            "code": -2,
            "name": "deprecated",
            "description": "`old_helper` is deprecated\n  Use new_helper instead.",
            "concise_description": "`old_helper` is deprecated",
            "severity": "error",
        },
        {
            "line": 8,
            "column": 5,
            "stop_line": 8,
            "stop_column": 16,
            "path": "src/app/use.py",
            "code": -2,
            "name": "deprecated",
            "description": "`depfix._models.Model.dict` is deprecated\n  Use dump instead.",
            "concise_description": "`depfix._models.Model.dict` is deprecated",
            "severity": "error",
        },
        {
            "line": 9,
            "column": 1,
            "path": "src/app/use.py",
            "name": "deprecated",
            "description": "Something else entirely",
            "concise_description": "Something else entirely",
        },
        {
            "line": 2,
            "column": 1,
            "path": "src/app/use.py",
            "name": "bad-assignment",
            "description": "not ours",
            "concise_description": "not ours",
        },
    ]
}


def test_pyrefly_records_parse_from_a_hand_written_document() -> None:
    records = parse_pyrefly_output(json.dumps(PYREFLY_DOCUMENT))
    assert [(r.line, r.column, r.deprecated, r.qualified, r.message) for r in records] == [
        (1, 20, "old_helper", False, "Use new_helper instead."),
        (8, 5, "depfix._models.Model.dict", True, "Use dump instead."),
        (9, 1, None, False, "Something else entirely"),
    ]
    with pytest.raises(ValueError, match="lacks"):
        parse_pyrefly_output(json.dumps({"errors": [{"name": "deprecated"}]}))
    assert checked_modules(" INFO 0 errors\n INFO 724 modules (4,684 dependent modules); …") == 724
    assert checked_modules(" INFO 1 module (12 dependent modules)") == 1


@needs_pyrefly
def test_pyrefly_contract_on_the_real_environment(tmp_path) -> None:
    """The fields and description pattern `compare` relies on, against the installed pyrefly
    and pydantic (the tool's own environment)."""
    pytest.importorskip("pydantic")
    source = tmp_path / "uses_pydantic.py"
    source.write_text(
        "from pydantic import BaseModel, parse_obj_as\n"
        "\n"
        "\n"
        "class M(BaseModel):\n"
        "    x: int = 0\n"
        "\n"
        "\n"
        "M().dict()  # type: ignore\n"
        "parse_obj_as(int, 1)\n",
        encoding="utf-8",
    )
    run = run_pyrefly([source], read_environment(Path(sys.prefix)))
    assert run.checked_modules == 1
    found = [(r.path, r.line, r.column, r.deprecated) for r in run.records]
    assert found == [
        (source, 1, 33, "parse_obj_as"),  # the bare imported name on an import line
        (source, 8, 1, "pydantic.main.BaseModel.dict"),  # reported despite `# type: ignore`
        (source, 9, 1, "pydantic.deprecated.tools.parse_obj_as"),
    ]
    assert "model_dump" in run.records[1].message
