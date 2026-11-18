"""`tooling library inventory` and the offered-surface loader against a fixture environment.

The fixture packages are written here for the purpose and materialized under `tmp_path`; every
expectation below is written by hand from the fixture source, not produced by the code under
test. Line numbers in expected locations refer to the source strings in this file.
"""

from __future__ import annotations

import json
import sys
import sysconfig
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from corpus_tooling.library import inventory
from corpus_tooling.library.app import REGISTRATIONS, make_library_app
from corpus_tooling.library.installed import Installation
from corpus_tooling.library.inventory_items import InventorySelection, surface_inventory
from corpus_tooling.library.surface import (
    PathResolution,
    load_offered_surface,
    resolve_written_path,
)
from corpus_tooling.library.target import read_environment
from corpus_tooling.output import ToolFailure

SITE = "lib/python3.12/site-packages"

INIT = '''\
"""Fixture package: an offered surface written for the inventory tests."""

import warnings

import otherpkg
from fixturepkg._core import Engine, make_engine
from fixturepkg.plugins import Plugin, PluginBase, register
from fixturepkg.settings import Options
from otherpkg import Widget

try:
    from fixturepkg._fast import accelerate
except ImportError:

    def accelerate(data: bytes) -> bytes:
        """Pure-Python fallback."""
        return data


Error = otherpkg.Error

__all__ = [
    "Engine",
    "Error",
    "Options",
    "Plugin",
    "PluginBase",
    "Widget",
    "accelerate",
    "legacy",
    "make_engine",
    "register",
]


@warnings.deprecated("Use make_engine instead.")
def legacy(workers: int = 1) -> Engine:
    """Make an engine the old way."""
    return make_engine(workers)
'''

CORE = '''\
"""Engine internals: a private module whose definitions are exposed publicly."""

from typing import Annotated

from typing_extensions import Doc


class Engine:
    """Runs jobs."""

    def __init__(self, workers: Annotated[int, Doc("How many workers run.")] = 1) -> None:
        self.workers = workers

    def start(self) -> None:
        """Start the engine."""


def make_engine(workers: int = 1) -> Engine:
    """Make an engine.

    Args:
        workers: The worker count.
    """
    return Engine(workers)
'''

API = '''\
"""Re-exports without __all__: only redundant aliases are public."""

from fixturepkg._core import Engine as Engine
from fixturepkg._core import make_engine
from otherpkg import Widget as Widget
'''

PLUGINS = '''\
"""Plugin interfaces."""

import abc
from typing import Protocol

_REGISTRY: dict[str, type] = {}


class Plugin(Protocol):
    """A plugin."""

    def run(self) -> None: ...


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
'''

SETTINGS = '''\
"""Engine settings."""

from typing import TypedDict


class Options(TypedDict, total=False):
    """Engine options."""

    verbose: bool


class ExtendedOptions(Options):
    """Options with more keys."""

    color: bool
'''

CONFIG = '''\
"""Configuration read from the environment and from entry points."""

import os
from importlib.metadata import entry_points

GROUP = "fixture.plugins"

HOME = os.environ["FIXTURE_HOME"]


def debug_enabled() -> bool:
    """Whether debugging is on."""
    return os.getenv("FIXTURE_DEBUG") == "1"


def lookup(name: str) -> str | None:
    """Read any variable."""
    return os.environ.get(name)


def plugin_groups():
    """Load plugins."""
    return entry_points(group=GROUP), entry_points(group=_suffix())


def _suffix() -> str:
    return "fixture.dynamic"


def main() -> None:
    """The console script."""
'''

SUB = '''\
"""A subclass whose methods are inherited."""

from fixturepkg._core import Engine


class Turbo(Engine):
    """A faster engine."""

    def boost(self) -> None:
        """Go faster."""
'''

OTHER = '''\
"""The second fixture distribution."""

from fixturepkg._core import Engine as Engine


class Widget:
    """A widget from another distribution."""


class Error(Exception):
    """An error from another distribution."""
'''

DEMO_TOOL = '''\
"""A module with a public function and a demo block."""

LEVEL = 1


def helper() -> int:
    """Public API."""
    return LEVEL


if __name__ == "__main__":
    import sys

    class DemoThing:
        """Demo only."""

        def show(self) -> None:
            """Demo only."""

    def run_demo() -> None:
        """Demo only."""

    for count in range(2):
        result = helper() + count
    LEVEL = 2
    sys.exit(0)
'''

FIXTURE_FILES = {
    "fixturepkg/__init__.py": INIT,
    "fixturepkg/_core.py": CORE,
    "fixturepkg/api.py": API,
    "fixturepkg/plugins.py": PLUGINS,
    "fixturepkg/settings.py": SETTINGS,
    "fixturepkg/config.py": CONFIG,
    "fixturepkg/sub.py": SUB,
    "fixturepkg/broken.py": "def broken(:\n",
    "fixturepkg/_fast.cpython-312-x86_64-linux-gnu.so": "",
    "fixturepkg/_typed.cpython-312-x86_64-linux-gnu.so": "",
    "fixturepkg/_typed.pyi": "def typed_helper() -> int: ...\n",
}

SITE_FILES: dict[str, str] = {
    **FIXTURE_FILES,
    "fixture_pkg-1.0.0.dist-info/METADATA": (
        "Metadata-Version: 2.1\nName: fixture-pkg\nVersion: 1.0.0\n"
    ),
    "fixture_pkg-1.0.0.dist-info/RECORD": "".join(
        f"{path},,\n" for path in [*FIXTURE_FILES, "fixture_pkg-1.0.0.dist-info/METADATA"]
    ),
    "fixture_pkg-1.0.0.dist-info/entry_points.txt": (
        "[console_scripts]\nfixture = fixturepkg.config:main\n\n"
        "[fixture.plugins]\nbuiltin = fixturepkg.plugins:PluginBase\n"
    ),
    "otherpkg/__init__.py": OTHER,
    "other_dist-2.0.0.dist-info/METADATA": "Metadata-Version: 2.1\nName: other-dist\nVersion: 2.0.0\n",
    "other_dist-2.0.0.dist-info/RECORD": "otherpkg/__init__.py,,\n",
    # Script code under a `__main__` guard is not offered API.
    "demopkg/__init__.py": '"""Demo fixture."""\n',
    "demopkg/tool.py": DEMO_TOOL,
    "demo_pkg-0.1.0.dist-info/METADATA": "Metadata-Version: 2.1\nName: demo-pkg\nVersion: 0.1.0\n",
    "demo_pkg-0.1.0.dist-info/RECORD": "demopkg/__init__.py,,\ndemopkg/tool.py,,\n",
    # A namespace package: two portions from two distributions, no `nsfix/__init__.py`.
    "nsfix/alpha/__init__.py": '"""Alpha portion."""\n\n\ndef alpha() -> int:\n    return 1\n',
    "nsfix/beta/__init__.py": '"""Beta portion."""\n\n\ndef beta() -> int:\n    return 2\n',
    "nsfix_alpha-0.1.0.dist-info/METADATA": "Metadata-Version: 2.1\nName: nsfix-alpha\nVersion: 0.1.0\n",
    "nsfix_alpha-0.1.0.dist-info/RECORD": "nsfix/alpha/__init__.py,,\n",
    "nsfix_beta-0.2.0.dist-info/METADATA": "Metadata-Version: 2.1\nName: nsfix-beta\nVersion: 0.2.0\n",
    "nsfix_beta-0.2.0.dist-info/RECORD": "nsfix/beta/__init__.py,,\n",
}


def _write(root: Path, files: dict[str, str]) -> None:
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A locked project whose `.venv` holds only the fixture distributions."""
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", tmp_path.as_posix())
    monkeypatch.delenv("UV_PROJECT_ENVIRONMENT", raising=False)
    monkeypatch.delenv("TTY_COMPATIBLE", raising=False)
    root = tmp_path / "project"
    _write(
        root,
        {
            "pyproject.toml": '[project]\nname = "consumer"\nrequires-python = ">=3.12"\n',
            "uv.lock": "version = 1\n",
            ".venv/pyvenv.cfg": "implementation = CPython\nversion_info = 3.12.7\n",
        },
    )
    _write(root / ".venv" / SITE, SITE_FILES)
    return root


def _site(project: Path) -> Path:
    return project / ".venv" / SITE


@pytest.fixture
def cli() -> typer.Typer:
    root = typer.Typer()

    @root.callback()
    def _root() -> None: ...

    root.add_typer(make_library_app((*REGISTRATIONS, inventory.register)), name="library")
    return root


def _run(cli: typer.Typer, project: Path, *args: str):
    return CliRunner().invoke(cli, ["library", "--project", str(project), "inventory", *args])


def _envelope(cli: typer.Typer, project: Path, *args: str) -> dict:
    result = _run(cli, project, *args, "--json")
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


def _paths(envelope: dict) -> list[str]:
    return [item["path"] for item in envelope["items"]]


def _item(envelope: dict, path: str) -> dict:
    (found,) = [item for item in envelope["items"] if item["path"] == path]
    return found


# --- the default view ------------------------------------------------------------------------


def test_default_view_is_the_public_top_level_surface(cli, project) -> None:
    envelope = _envelope(cli, project, "fixturepkg")
    assert envelope["view"] == "offered_symbol"
    rows = [
        (
            item["path"],
            item["symbol_kind"],
            item["declared_path"],
            item["in_all"],
            item["public"],
            item["markers"],
        )
        for item in envelope["items"]
    ]
    assert rows == [
        ("fixturepkg", "module", "fixturepkg", False, True, []),
        ("fixturepkg.Engine", "class", "fixturepkg._core.Engine", True, True, []),
        ("fixturepkg.Error", "attribute", "fixturepkg.Error", True, True, []),
        (
            "fixturepkg.Options",
            "class",
            "fixturepkg.settings.Options",
            True,
            True,
            ["configuration"],
        ),
        (
            "fixturepkg.Plugin",
            "class",
            "fixturepkg.plugins.Plugin",
            True,
            True,
            ["extension_point"],
        ),
        (
            "fixturepkg.PluginBase",
            "class",
            "fixturepkg.plugins.PluginBase",
            True,
            True,
            ["extension_point"],
        ),
        ("fixturepkg.accelerate", "function", "fixturepkg.accelerate", True, True, ["extra_gated"]),
        ("fixturepkg.api", "module", "fixturepkg.api", False, True, []),
        ("fixturepkg.config", "module", "fixturepkg.config", False, True, []),
        ("fixturepkg.legacy", "function", "fixturepkg.legacy", True, True, ["deprecated"]),
        ("fixturepkg.make_engine", "function", "fixturepkg._core.make_engine", True, True, []),
        ("fixturepkg.plugins", "module", "fixturepkg.plugins", False, True, []),
        (
            "fixturepkg.register",
            "function",
            "fixturepkg.plugins.register",
            True,
            True,
            ["extension_point"],
        ),
        ("fixturepkg.settings", "module", "fixturepkg.settings", False, True, []),
        ("fixturepkg.sub", "module", "fixturepkg.sub", False, True, []),
    ]
    assert "fixturepkg" not in sys.modules  # D2: never imported


def test_symbol_identity_and_marker_reasons(cli, project) -> None:
    envelope = _envelope(cli, project, "fixturepkg")
    engine = _item(envelope, "fixturepkg.Engine")
    assert engine["exposed_paths"] == ["fixturepkg.Engine", "fixturepkg.api.Engine"]
    assert engine["import_root"] == "fixturepkg"
    assert (engine["distribution"], engine["distribution_version"]) == ("fixture-pkg", "1.0.0")
    assert engine["location"] == "fixturepkg/_core.py:8"
    assert engine["summary"] == "Runs jobs."
    assert engine["depth"] == 1

    error = _item(envelope, "fixturepkg.Error")
    assert error["assigned_from"] == "otherpkg.Error"
    assert error["location"] == "fixturepkg/__init__.py:20"

    assert _item(envelope, "fixturepkg.Options")["exposed_paths"] == [
        "fixturepkg.Options",
        "fixturepkg.settings.Options",
    ]
    reasons = {item["path"]: item["marker_reasons"] for item in envelope["items"]}
    assert reasons["fixturepkg.Options"] == {"configuration": "TypedDict"}
    assert reasons["fixturepkg.Plugin"] == {"extension_point": "Protocol class"}
    assert reasons["fixturepkg.PluginBase"] == {
        "extension_point": "abstract base class (abc.ABC); abstract methods: setup"
    }
    assert reasons["fixturepkg.register"] == {
        "extension_point": "registration decorator: stores its argument `cls` and returns it"
    }
    assert reasons["fixturepkg.legacy"] == {"deprecated": "Use make_engine instead."}
    assert reasons["fixturepkg.accelerate"] == {
        "extra_gated": "bound under try/except ImportError at fixturepkg/__init__.py:12"
    }


def test_signatures_and_parameter_documentation(cli, project) -> None:
    envelope = _envelope(cli, project, "fixturepkg", "--depth", "2")
    make_engine = _item(envelope, "fixturepkg.make_engine")
    assert make_engine["signature"] == "make_engine(workers: int = 1) -> Engine"
    assert make_engine["returns"] == "Engine"
    assert make_engine["parameters"] == [
        {
            "name": "workers",
            "kind": "positional or keyword",
            "annotation": "int",
            "default": "1",
            "description": "The worker count.",
        }
    ]
    # `Annotated[..., Doc(...)]` text reaches the parameters (griffe-typingdoc).
    init = _item(envelope, "fixturepkg.Engine.__init__")
    assert init["declared_path"] == "fixturepkg._core.Engine.__init__"
    workers = [p for p in init["parameters"] if p["name"] == "workers"]
    assert workers[0]["description"] == "How many workers run."
    engine = _item(envelope, "fixturepkg.Engine")
    assert [p["name"] for p in engine["parameters"]] == ["self", "workers"]
    assert engine["parameters"][1]["description"] == "How many workers run."
    # An instance attribute assigned in `__init__` is a class member with Griffe's label.
    attribute = _item(envelope, "fixturepkg.Engine.workers")
    assert attribute["symbol_kind"] == "attribute"
    assert "instance-attribute" in attribute["labels"]
    assert _item(envelope, "fixturepkg.plugins.PluginBase")["bases"] == ["abc.ABC"]
    assert _item(envelope, "fixturepkg.legacy")["decorators"] == [
        # Griffe renders expressions through the parser: string quotes are normalized.
        "warnings.deprecated('Use make_engine instead.')"
    ]


def test_coverage_separates_skipped_inputs_from_unresolved_rows(cli, project) -> None:
    envelope = _envelope(cli, project, "fixturepkg")
    coverage = envelope["coverage"]
    # Seven .py files loaded and scanned; the stub-only and broken modules are not among them.
    assert coverage["scanned"] == 7
    skipped = [(row["input"], row["reason"]) for row in coverage["skipped_inputs"]]
    assert skipped == [
        ("fixturepkg/_fast.cpython-312-x86_64-linux-gnu.so", "compiled_without_stub"),
        ("fixturepkg/broken.py", "parse_error"),
    ]
    assert coverage["skipped_inputs"][1]["detail"].startswith("SyntaxError")
    unresolved = [
        (row["kind"], row["subject"], row["location"], row["detail"])
        for row in coverage["unresolved"]
    ]
    assert unresolved == [
        (
            "non_literal_entry_point_group",
            "_suffix()",
            "fixturepkg/config.py:23:39",
            "read in fixturepkg.config.plugin_groups",
        ),
        (
            "non_literal_env_var",
            "name",
            "fixturepkg/config.py:18:12",
            "read in fixturepkg.config.lookup",
        ),
        (
            "unresolved_alias",
            "fixturepkg.Widget",
            "fixturepkg/__init__.py:9",
            "target otherpkg.Widget is not in the loaded package",
        ),
        (
            "unresolved_alias",
            "fixturepkg.api.Widget",
            "fixturepkg/api.py:5",
            "target otherpkg.Widget is not in the loaded package",
        ),
    ]
    assert coverage["unavailable_metadata"] == []
    assert "fixturepkg.__all__ lists 10 names; 10 are bound statically" in envelope["notes"]
    assert _run(cli, project, "fixturepkg", "--json", "--strict").exit_code == 1


def test_unresolved_rows_alone_do_not_trip_strict(cli, project) -> None:
    result = _run(cli, project, "otherpkg", "--json", "--strict")
    assert result.exit_code == 0, result.output
    envelope = json.loads(result.stdout)
    assert envelope["coverage"]["skipped_inputs"] == []
    assert [row["subject"] for row in envelope["coverage"]["unresolved"]] == ["otherpkg.Engine"]
    assert _paths(envelope) == ["otherpkg", "otherpkg.Error", "otherpkg.Widget"]


# --- views ---------------------------------------------------------------------------------------


def test_depth_two_adds_submodule_and_class_members(cli, project) -> None:
    envelope = _envelope(cli, project, "fixturepkg", "--depth", "2")
    deeper = [path for path in _paths(envelope) if path.count(".") == 2]
    assert deeper == [
        # Members of `_core.Engine`, reached through its first public exposure.
        "fixturepkg.Engine.__init__",
        "fixturepkg.Engine.start",
        "fixturepkg.Engine.workers",
        "fixturepkg.api.Engine",
        "fixturepkg.config.GROUP",
        "fixturepkg.config.HOME",
        "fixturepkg.config.debug_enabled",
        "fixturepkg.config.lookup",
        "fixturepkg.config.main",
        "fixturepkg.config.plugin_groups",
        "fixturepkg.plugins.Plugin",
        "fixturepkg.plugins.PluginBase",
        "fixturepkg.plugins.register",
        "fixturepkg.settings.ExtendedOptions",
        "fixturepkg.settings.Options",
        "fixturepkg.sub.Turbo",
    ]
    start = _item(envelope, "fixturepkg.Engine.start")
    assert start["exposed_paths"] == ["fixturepkg.Engine.start", "fixturepkg.api.Engine.start"]
    reasons = {item["path"]: item["marker_reasons"] for item in envelope["items"]}
    assert reasons["fixturepkg.config.HOME"] == {
        "configuration": "reads environment variables: FIXTURE_HOME"
    }
    assert reasons["fixturepkg.config.debug_enabled"] == {
        "configuration": "reads environment variables: FIXTURE_DEBUG"
    }
    assert reasons["fixturepkg.config.lookup"] == {
        "configuration": "reads environment variables: name (not a literal)"
    }
    assert reasons["fixturepkg.config.plugin_groups"] == {
        "extension_point": "reads entry-point groups: _suffix() (not a literal), fixture.plugins"
    }
    assert reasons["fixturepkg.settings.ExtendedOptions"] == {"configuration": "TypedDict"}


def test_kind_match_marker_and_paging(cli, project) -> None:
    functions = _envelope(cli, project, "fixturepkg", "--depth", "2", "--kind", "function")
    assert _paths(functions) == [
        "fixturepkg.Engine.__init__",
        "fixturepkg.Engine.start",
        "fixturepkg.accelerate",
        "fixturepkg.config.debug_enabled",
        "fixturepkg.config.lookup",
        "fixturepkg.config.main",
        "fixturepkg.config.plugin_groups",
        "fixturepkg.legacy",
        "fixturepkg.make_engine",
        "fixturepkg.plugins.register",
        "fixturepkg.register",
    ]
    # --match is unbounded in depth and also matches exposed paths.
    matched = _envelope(cli, project, "fixturepkg", "--match", "fixturepkg.Engine*")
    assert _paths(matched) == [
        "fixturepkg.Engine",
        "fixturepkg.Engine.__init__",
        "fixturepkg.Engine.start",
        "fixturepkg.Engine.workers",
        "fixturepkg.api.Engine",
    ]
    assert _paths(_envelope(cli, project, "fixturepkg", "--match", "Turbo")) == [
        "fixturepkg.sub.Turbo",
        "fixturepkg.sub.Turbo.boost",
    ]
    marked = _envelope(cli, project, "fixturepkg", "--marker", "extension_point")
    assert _paths(marked) == [
        "fixturepkg.Plugin",
        "fixturepkg.PluginBase",
        "fixturepkg.config.plugin_groups",
        "fixturepkg.plugins.Plugin",
        "fixturepkg.plugins.PluginBase",
        "fixturepkg.plugins.register",
        "fixturepkg.register",
    ]
    either = _envelope(
        cli,
        project,
        "fixturepkg",
        "--depth",
        "1",
        "--marker",
        "deprecated",
        "--marker",
        "extra_gated",
    )
    assert _paths(either) == ["fixturepkg.accelerate", "fixturepkg.legacy"]
    page = _envelope(cli, project, "fixturepkg", "--limit", "3", "--offset", "2")
    assert _paths(page) == ["fixturepkg.Error", "fixturepkg.Options", "fixturepkg.Plugin"]
    assert page["truncated"] == [{"list": "items", "shown": 3, "total": 15}]


def test_private_lists_non_public_bindings(cli, project) -> None:
    envelope = _envelope(cli, project, "fixturepkg", "--private", "--depth", "1")
    core = _item(envelope, "fixturepkg._core")
    assert (core["public"], core["in_all"]) == (False, False)
    assert "fixturepkg._typed" in _paths(envelope)
    assert "fixturepkg._core" not in _paths(_envelope(cli, project, "fixturepkg", "--depth", "1"))


def test_package_view_lists_reads_and_declared_entry_points(cli, project) -> None:
    envelope = _envelope(cli, project, "fixturepkg", "--view", "package")
    assert envelope["view"] == "package_fact"
    facts = [
        (item["category"], item["name"], item["symbol"], item["location"], item["detail"])
        for item in envelope["items"]
    ]
    assert facts == [
        (
            "entry_point",
            "console_scripts:fixture",
            "fixturepkg.config.main",
            "fixture_pkg-1.0.0.dist-info",
            "fixturepkg.config:main",
        ),
        (
            "entry_point",
            "fixture.plugins:builtin",
            "fixturepkg.plugins.PluginBase",
            "fixture_pkg-1.0.0.dist-info",
            "fixturepkg.plugins:PluginBase",
        ),
        (
            "entry_point_group",
            "fixture.plugins",
            "fixturepkg.config.plugin_groups",
            "fixturepkg/config.py:23",
            "",
        ),
        (
            "env_var",
            "FIXTURE_DEBUG",
            "fixturepkg.config.debug_enabled",
            "fixturepkg/config.py:13",
            "",
        ),
        ("env_var", "FIXTURE_HOME", "fixturepkg.config.HOME", "fixturepkg/config.py:8", ""),
    ]
    assert {item["distribution"] for item in envelope["items"]} == {"fixture-pkg"}


def test_namespace_package_lists_portions_by_distribution(cli, project) -> None:
    envelope = _envelope(cli, project, "nsfix")
    rows = [(item["path"], item["distribution"]) for item in envelope["items"]]
    assert rows == [("nsfix", None), ("nsfix.alpha", "nsfix-alpha"), ("nsfix.beta", "nsfix-beta")]
    assert (
        "nsfix is a namespace package; its portions are listed separately: "
        "nsfix.alpha (nsfix-alpha 0.1.0), nsfix.beta (nsfix-beta 0.2.0)"
    ) in envelope["notes"]
    package = _envelope(cli, project, "nsfix", "--view", "package")
    assert [(i["category"], i["name"], i["distribution"]) for i in package["items"]] == [
        ("namespace_portion", "nsfix.alpha", "nsfix-alpha"),
        ("namespace_portion", "nsfix.beta", "nsfix-beta"),
    ]


def test_missing_package_is_a_tool_failure(cli, project) -> None:
    # `typer` is installed for the tool itself, not in the fixture environment.
    result = _run(cli, project, "typer", "--json")
    assert result.exit_code == 3
    assert json.loads(result.stdout)["error"]["kind"] == "package_not_found"


def test_a_dotted_path_is_a_usage_error(cli, project) -> None:
    result = _run(cli, project, "fixturepkg.api")
    assert result.exit_code == 2


# --- the loader and the join ---------------------------------------------------------------------


@pytest.mark.parametrize("extension", ["griffe_typingdocs", "griffe_typingdoc._internal.static"])
def test_an_extension_that_loads_nothing_is_refused(project, extension) -> None:
    with pytest.raises(ToolFailure) as failure:
        load_offered_surface(["fixturepkg"], [_site(project)], extensions=(extension,))
    assert failure.value.error.kind == "griffe_extension_missing"


@pytest.mark.parametrize(
    ("written", "expected"),
    [
        # Exposed and declared paths differ.
        (
            "fixturepkg.Engine",
            PathResolution("fixturepkg.Engine", "fixturepkg._core.Engine", "fixturepkg.Engine", ""),
        ),
        (
            "fixturepkg.Engine.start",
            PathResolution(
                "fixturepkg.Engine.start",
                "fixturepkg._core.Engine.start",
                "fixturepkg.Engine.start",
                "",
            ),
        ),
        # An inherited member resolves to the base class's declaration.
        (
            "fixturepkg.sub.Turbo.start",
            PathResolution(
                "fixturepkg.sub.Turbo.start",
                "fixturepkg._core.Engine.start",
                "fixturepkg.sub.Turbo.start",
                "",
            ),
        ),
        # Longest resolvable prefix with the unmatched tail.
        (
            "fixturepkg.Engine.workers.bit_length",
            PathResolution(
                "fixturepkg.Engine.workers.bit_length",
                "fixturepkg._core.Engine.workers",
                "fixturepkg.Engine.workers",
                "bit_length",
            ),
        ),
        # An assignment alias keeps the assigning module's path and names the source.
        (
            "fixturepkg.Error.args",
            PathResolution(
                "fixturepkg.Error.args",
                "fixturepkg.Error",
                "fixturepkg.Error",
                "args",
                assigned_from="otherpkg.Error",
            ),
        ),
        # Stopped at an alias whose target is not loaded.
        (
            "fixturepkg.Widget.render",
            PathResolution(
                "fixturepkg.Widget.render",
                None,
                "fixturepkg.Widget",
                "render",
                unresolved_alias="fixturepkg.Widget",
                alias_target="otherpkg.Widget",
            ),
        ),
        # Not in the loaded package at all.
        ("json.dumps", PathResolution("json.dumps", None, None, "json.dumps")),
    ],
)
def test_resolve_written_path(project, written, expected) -> None:
    surface = load_offered_surface(["fixturepkg"], [_site(project)])
    assert resolve_written_path(surface, written) == expected


def test_resolve_written_path_on_the_tools_pinned_typer() -> None:
    """typer is pinned in the tooling project, so this declared path moves only on purpose."""
    surface = load_offered_surface(["typer"], [Path(sysconfig.get_paths()["purelib"])])
    resolution = resolve_written_path(surface, "typer.Option")
    assert (resolution.declared_path, resolution.unmatched_tail) == ("typer.params.Option", "")


# --- script code under a `__main__` guard ------------------------------------------------------


def test_names_bound_only_under_a_main_guard_are_not_offered(cli, project) -> None:
    envelope = _envelope(cli, project, "demopkg", "--depth", "9")
    # `LEVEL` is also bound outside the guard, so it stays; the demo class (and its method),
    # function, loop variables and import are left out.
    assert _paths(envelope) == [
        "demopkg",
        "demopkg.tool",
        "demopkg.tool.LEVEL",
        "demopkg.tool.helper",
    ]
    assert (
        '5 names in 1 module are bound only under a __main__ guard (`if __name__ == "__main__":`) '
        "and are not offered symbols; --view package lists them (main_guard_binding) and "
        "--private shows them"
    ) in envelope["notes"]
    package = _envelope(cli, project, "demopkg", "--view", "package")
    facts = [
        (item["category"], item["name"], item["location"], item["distribution"])
        for item in package["items"]
    ]
    assert facts == [
        ("main_guard_binding", "demopkg.tool.DemoThing", "demopkg/tool.py:14", "demo-pkg"),
        ("main_guard_binding", "demopkg.tool.count", "demopkg/tool.py:23", "demo-pkg"),
        ("main_guard_binding", "demopkg.tool.result", "demopkg/tool.py:24", "demo-pkg"),
        ("main_guard_binding", "demopkg.tool.run_demo", "demopkg/tool.py:20", "demo-pkg"),
        ("main_guard_binding", "demopkg.tool.sys", "demopkg/tool.py:12", "demo-pkg"),
    ]
    private = _envelope(cli, project, "demopkg", "--depth", "9", "--private")
    shown = {item["path"]: item["public"] for item in private["items"]}
    assert shown["demopkg.tool.DemoThing"] is False
    assert shown["demopkg.tool.DemoThing.show"] is False
    assert shown["demopkg.tool.run_demo"] is False
    assert shown["demopkg.tool.helper"] is True


def test_compare_route_leaves_main_guard_bindings_out(project) -> None:
    """`compare` builds its offered rows through `surface_inventory` at unbounded depth."""
    surface = load_offered_surface(["demopkg"], [_site(project)])
    installation = Installation(read_environment(project / ".venv"))
    result = surface_inventory(surface, "demopkg", installation, InventorySelection(depth=None))
    assert [symbol.path for symbol in result.symbols] == [
        "demopkg",
        "demopkg.tool",
        "demopkg.tool.LEVEL",
        "demopkg.tool.helper",
    ]
