"""LDT-04 census against the hand-written fixture repository in `census_fixture/`.

Every expected row below was written by hand from the fixture source, keyed by the `# @tag`
comment on its line; the code under test is never used to produce an expectation. A tag mapped
to `[]` records that the line must yield nothing (a shadowed name). The opening slice ran an
`ast` + `symtable` engine against this same fixture: it attributed the three
`shadow-*-comprehension*` lines to `alpha.item.value` and was rejected.
"""

from __future__ import annotations

import json
import re
import shutil
from collections import Counter
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from corpus_tooling.library import census, census_scan
from corpus_tooling.library.app import REGISTRATIONS, make_library_app
from corpus_tooling.library.attribution import FileContext, attribute
from corpus_tooling.library.census_rows import CensusSite, load_census
from corpus_tooling.library.census_scan import run_census
from corpus_tooling.library.target import resolve_target

FIXTURE = Path(__file__).parent / "census_fixture"
TAG = re.compile(r"#\s*@([\w-]+)")

PYPROJECT = """[project]
name = "fixture-root"
requires-python = ">=3.12"
dependencies = ["Alpha_Pkg>=1.0", "requests"]

[dependency-groups]
dev = ["alpha-pkg[fast]"]
"""

# --- hand-written expectations ---------------------------------------------------------------

F = "alpha.Field"
SITES: dict[str, list[tuple[str, tuple[str, ...]]]] = {
    # basics.py: aliased, dotted and function-local imports, calls, decorators, references
    "import-plain": [("import", ("alpha",))],
    "import-dotted-alias": [("import", ("alpha.fields",))],
    "import-from-alias": [("import", (F,))],
    "import-from": [("import", ("alpha.validators.check",))],
    "alias-assign": [("reference", ("alpha.DEFAULT",))],
    "call-star": [("call", (F,))],
    "call-dotted": [("call", ("alpha.fields.ListField",))],
    "decorator-plain": [("decorator", ("alpha.validators.check",))],
    "decorator-call": [("decorator", ("alpha.validators.check",))],
    "instance-assign": [("call", ("alpha.App",))],
    "instance-decorator": [],
    "alias-assign-2": [("reference", ("alpha.Option",))],
    "alias-use": [],
    "reference": [("reference", ("alpha.Kind",))],
    "getattr": [],
    "dynamic-import": [],
    "dynamic-import-unknown": [],
    "string-reference": [],
    "call-result-member": [("call", ("alpha.make",))],
    "import-local": [("import", ("alpha.lazy.Loader",))],
    "local-call": [("call", ("alpha.lazy.Loader.open",))],
    # models.py, relay.py, reexport_user.py: re-exports and a repository subclass
    "models-import-field": [("import", (F,))],
    "models-import-model": [("import", ("alpha.base.Model",))],
    "models-import-beta": [],
    "record-class": [("subclass", ("alpha.base.Model",))],
    "record-field": [("call", (F,))],
    "beta-call": [],
    "relay-import": [("import", (F,))],
    "reexport-import": [("import", (F,))],
    "chain-import": [],
    "reexport-call": [("call", (F,))],
    "reexport-module-call": [("call", (F,))],
    "chain-call": [],
    # shadowing.py
    "shadowing-import": [
        ("import", (F,)),
        ("import", ("alpha.Schema",)),
        ("import", ("alpha.item",)),
    ],
    "shadow-parameter": [],
    "before-rebind": [("call", ("alpha.Schema",))],
    "after-rebind": [],  # truth: `dict`; reported as mixed_binding below
    "shadow-class-body": [],
    "class-scope-invisible": [("call", (F,))],
    "shadow-comprehension": [],
    "comprehension-outer-use": [("call", ("alpha.item.default",))],
    "shadow-comprehension-beside-use": [],
    "class-comprehension-outer-use": [("call", ("alpha.item.default",))],
    "shadow-class-comprehension": [],
    "shadow-module-comprehension": [],
    "shadow-generator": [],
    "import-global": [("import", ("alpha.registry",))],
    "global-use": [("call", ("alpha.registry.lookup",))],
    "import-nonlocal": [("import", ("alpha.loader",))],
    "nonlocal-use": [("call", ("alpha.loader.load",))],
    # conditional.py: double bindings
    "import-try": [("import", ("alpha.fast.Parser",))],
    "import-except": [("import", ("alpha.slow.Parser",))],
    "import-type-checking": [("import", ("alpha.types.Handle",))],
    "import-else": [("import", ("alpha.runtime.Handle",))],
    "double-try": [("call", ("alpha.fast.Parser", "alpha.slow.Parser"))],
    "double-annotation": [("reference", ("alpha.runtime.Handle", "alpha.types.Handle"))],
    "double-type-checking": [
        ("call", ("alpha.runtime.Handle.verify", "alpha.types.Handle.verify"))
    ],
    # typing_cases.py
    "typing-import": [
        ("import", ("alpha.Container",)),
        ("import", (F,)),
        ("import", ("alpha.Model",)),
    ],
    "generic-base": [("subclass", ("alpha.Container",))],
    "same-line-lambdas": [("call", (F,))],
    "string-annotation": [("reference", ("alpha.Model",)), ("reference", ("alpha.Model",))],
    # subclassing.py
    "subclassing-import": [("import", ("alpha",))],
    "subclass": [("subclass", ("alpha.Model",))],
    "subclass-member": [],
    "instance-member": [],
    "instantiation": [("instantiation", ("alpha.Model",))],
    # another uv project
    "other-import": [("import", (F,))],
    "other-call": [("call", (F,))],
    # mentions
    "yaml-plugin": [("mention", ("alpha",))],
    "yaml-backend": [("mention", ("alpha",))],
}

UNRESOLVED: dict[str, list[tuple[str, tuple[str, ...], str | None]]] = {
    "call-star": [("assignment_alias", ("alpha.DEFAULT",), "DEFAULT")],
    "instance-decorator": [("instance_member", ("alpha.App",), "app")],
    "alias-use": [("assignment_alias", ("alpha.Option",), "opt")],
    "getattr": [("getattr", ("alpha.hook",), None)],
    "dynamic-import": [("dynamic_import", ("alpha.plugins",), None)],
    "dynamic-import-unknown": [("dynamic_import", (), None)],
    "string-reference": [("string_reference", ("alpha.plugins.Factory",), None)],
    "call-result-member": [("instance_member", ("alpha.make",), "alpha.make()")],
    "chain-import": [("reexport_chain", (F,), None)],
    "chain-call": [("reexport_chain", (F,), None)],
    "after-rebind": [("mixed_binding", ("alpha.Schema",), None)],
    "subclass-member": [("subclass_member", ("alpha.Model",), "Account")],
    "instance-member": [("instance_member", ("alpha.Model",), "account")],
}

SCOPES = ("src", "nested/other", "nohit", "empty")


# --- fixture and helpers --------------------------------------------------------------------


@pytest.fixture
def repo(trees) -> Path:
    root = trees.project
    for source in FIXTURE.rglob("*.fixture"):
        destination = root / source.relative_to(FIXTURE).with_suffix("")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    (root / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8")
    (root / "empty").mkdir()
    return root


@pytest.fixture
def cli() -> typer.Typer:
    root = typer.Typer()

    @root.callback()
    def _root() -> None: ...

    root.add_typer(make_library_app((*REGISTRATIONS, census.register)), name="library")
    return root


def _run(cli: typer.Typer, repo: Path, *args: str):
    return CliRunner().invoke(cli, ["library", "--project", str(repo), "census", *args])


def _scope_args(*scopes: str) -> list[str]:
    return [token for scope in scopes for token in ("--scope", scope)]


def _tags(repo: Path) -> dict[tuple[str, int], str]:
    tags = {}
    for path in [*repo.rglob("*.py"), *repo.rglob("*.yaml")]:
        if ".venv" in path.parts:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            match = TAG.search(line)
            if match:
                tags[(path.relative_to(repo).as_posix(), number)] = match[1]
    return tags


def _line_of(text: str, needle: str) -> int:
    return next(n for n, line in enumerate(text.splitlines(), start=1) if needle in line)


def _sites_envelope(cli: typer.Typer, repo: Path, *roots: str) -> dict:
    result = _run(cli, repo, *roots, *_scope_args(*SCOPES), "--sites", "--json", "--limit", "0")
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


def _location_key(location: str) -> tuple[str, int]:
    path, line, _ = location.rsplit(":", 2)
    return path, int(line)


# --- the census against the fixture ---------------------------------------------------------


def test_sites_equal_the_hand_written_expectation(cli, repo) -> None:
    envelope = _sites_envelope(cli, repo, "alpha")
    assert envelope["view"] == "census_site"
    tags = _tags(repo)
    actual: dict[str, list[tuple[str, tuple[str, ...]]]] = {tag: [] for tag in SITES}
    pyproject_rows = []
    for item in envelope["items"]:
        key = (item["path"], item["line"])
        if item["path"] == "pyproject.toml":
            pyproject_rows.append((item["line"], item["use"], item["text"]))
            continue
        assert key in tags, f"a row on an untagged line: {item}"
        actual[tags[key]].append((item["use"], tuple(item["written_paths"])))
    assert {tag: sorted(rows) for tag, rows in actual.items()} == {
        tag: sorted(rows) for tag, rows in SITES.items()
    }
    assert set(tags.values()) == set(SITES)  # every tag in the fixture has an expectation
    assert sorted(pyproject_rows) == [
        (_line_of(PYPROJECT, '"Alpha_Pkg>=1.0"'), "mention", "Alpha_Pkg>=1.0"),
        (_line_of(PYPROJECT, '"alpha-pkg[fast]"'), "mention", "alpha-pkg[fast]"),
    ]


def test_unresolved_rows_equal_the_hand_written_expectation(cli, repo) -> None:
    envelope = _sites_envelope(cli, repo, "alpha")
    tags = _tags(repo)
    actual: dict[str, list[tuple[str, tuple[str, ...], str | None]]] = {}
    for row in envelope["coverage"]["unresolved"]:
        tag = tags[_location_key(row["location"])]
        actual.setdefault(tag, []).append((row["kind"], tuple(row["written_paths"]), row["owner"]))
    assert {tag: sorted(rows) for tag, rows in actual.items()} == {
        tag: sorted(rows, key=str) for tag, rows in UNRESOLVED.items()
    }


def test_site_details(cli, repo) -> None:
    envelope = _sites_envelope(cli, repo, "alpha")
    tags = _tags(repo)
    by_tag: dict[str, list[dict]] = {}
    for item in envelope["items"]:
        tag = tags.get((item["path"], item["line"]))
        if tag:
            by_tag.setdefault(tag, []).append(item)

    (star,) = by_tag["call-star"]
    assert (star["positional"], star["keywords"], star["star_args"], star["star_kwargs"]) == (
        1,
        ["default"],
        True,
        True,
    )
    (field,) = by_tag["record-field"]
    assert field["keywords"] == ["default", "min_length"]
    (decorator,) = by_tag["decorator-call"]
    assert (decorator["positional"], decorator["keywords"]) == (1, ["mode"])
    (plain,) = by_tag["decorator-plain"]
    assert (plain["column"], plain["positional"]) == (1, None)
    # `café = alpha.make()`: the call starts at character 7, UTF-8 byte 8.
    (call,) = by_tag["call-result-member"]
    assert call["column"] == 8
    (local,) = by_tag["import-local"]
    assert (local["statement"], local["module"], local["context"]) == (
        "from",
        "alpha.lazy",
        ["function"],
    )
    assert by_tag["import-try"][0]["context"] == ["module", "try"]
    assert by_tag["import-except"][0]["context"] == ["module", "try"]
    assert by_tag["import-type-checking"][0]["context"] == ["module", "type_checking"]
    assert by_tag["import-else"][0]["context"] == ["module"]
    assert by_tag["import-global"][0]["context"] == ["function"]
    (aliased,) = by_tag["import-dotted-alias"]
    assert (aliased["statement"], aliased["module"], aliased["alias"]) == (
        "import",
        "alpha.fields",
        "af",
    )
    for tag in ("reexport-import", "reexport-call", "reexport-module-call", "relay-import"):
        assert [row["via"] for row in by_tag[tag]] == ["app.models"]
    (relative,) = by_tag["reexport-import"]
    assert (relative["level"], relative["module"]) == (1, "models")
    assert by_tag["other-call"][0]["project"] == "nested/other"
    assert by_tag["record-field"][0]["project"] == "."
    assert {row["text"] for row in by_tag["yaml-backend"]} == {"backend: alpha  # @yaml-backend"}


def test_coverage_skipped_inputs_scopes_and_notes(cli, repo) -> None:
    envelope = _sites_envelope(cli, repo, "alpha")
    coverage = envelope["coverage"]
    assert coverage["no_hit_scopes"] == ["empty", "nohit"]
    python_skipped = {
        row["input"]: row["reason"]
        for row in coverage["skipped_inputs"]
        if row["input"].endswith(".py")
    }
    # broken.py fails everywhere; newer.py is valid 3.14 but the target environment is 3.12.
    assert python_skipped == {"src/app/broken.py": "parse_error", "src/app/newer.py": "parse_error"}
    # 11 Python files and settings.yaml under src, the other project's two files, the plain
    # file under nohit, and the root pyproject.toml found as the manifest above src.
    assert coverage["scanned"] == 16
    assert any("feature_version=(3, 12)" in note for note in envelope["notes"])
    assert envelope["tool"]["authorities"]["libcst"]


def test_summary_is_the_default_view(cli, repo) -> None:
    result = _run(cli, repo, "alpha", *_scope_args(*SCOPES), "--json", "--limit", "0")
    assert result.exit_code == 0, result.output
    envelope = json.loads(result.stdout)
    assert envelope["view"] == "census_symbol"
    rows = {
        (r["symbol"], r["use"], r["keyword"]): (r["count"], r["files"]) for r in envelope["items"]
    }
    # alpha.Field calls: models, basics (as F), reexport_user (twice), shadowing, typing_cases,
    # other_app.
    assert rows[(F, "call", None)] == (7, 6)
    assert rows[(F, "import", None)] == (7, 7)
    assert rows[(F, "keyword", "default")] == (3, 3)
    assert rows[(F, "keyword", "min_length")] == (1, 1)
    assert rows[("alpha.Model", "subclass", None)] == (1, 1)
    assert rows[("alpha.Model", "instantiation", None)] == (1, 1)
    assert rows[("alpha.Model", "reference", None)] == (2, 1)
    assert rows[("alpha.fast.Parser", "call", None)] == (1, 1)
    assert rows[("alpha.slow.Parser", "call", None)] == (1, 1)
    assert rows[("alpha", "mention", None)] == (4, 2)
    counts = [item["count"] for item in envelope["items"]]
    assert counts == sorted(counts, reverse=True)


def test_a_scope_without_use_exits_zero_and_is_recorded(cli, repo) -> None:
    result = _run(cli, repo, "alpha", "--scope", "nohit", "--json")
    assert result.exit_code == 0, result.output
    envelope = json.loads(result.stdout)
    # The manifest above the scope still declares the distribution: a mention, not code use.
    assert [(item["symbol"], item["use"]) for item in envelope["items"]] == [("alpha", "mention")]
    assert envelope["coverage"]["no_hit_scopes"] == ["nohit"]
    assert envelope["coverage"]["unresolved"] == []


def test_two_roots(cli, repo) -> None:
    envelope = _sites_envelope(cli, repo, "alpha", "beta")
    tags = _tags(repo)
    beta = sorted(
        (tags[(item["path"], item["line"])], item["use"], tuple(item["written_paths"]))
        for item in envelope["items"]
        if item["written_paths"][0].startswith("beta")
    )
    assert beta == [
        ("beta-call", "call", ("beta.core.render",)),
        ("models-import-beta", "import", ("beta.core",)),
    ]


def test_scope_is_required_and_must_exist(cli, repo) -> None:
    assert _run(cli, repo, "alpha", "--json").exit_code == 2
    # A path the caller names that does not exist is a usage error, as for --project.
    missing = _run(cli, repo, "alpha", "--scope", "nowhere", "--json")
    assert (missing.exit_code, missing.stdout) == (2, "")
    assert "no such scope: nowhere" in missing.stderr
    invalid = _run(cli, repo, "alpha-pkg", "--scope", "src", "--json")
    assert (invalid.exit_code, invalid.stdout) == (2, "")
    assert "not an import root: alpha-pkg" in invalid.stderr


def test_exclude_glob(cli, repo) -> None:
    result = _run(
        cli,
        repo,
        "alpha",
        "--scope",
        "src",
        "--exclude",
        "src/app/b*.py",
        "--sites",
        "--json",
        "--limit",
        "0",
    )
    envelope = json.loads(result.stdout)
    assert not any(item["path"] == "src/app/basics.py" for item in envelope["items"])
    assert "--exclude src/app/b*.py" in envelope["coverage"]["excluded"]
    assert not any(
        row["input"] == "src/app/broken.py" for row in envelope["coverage"]["skipped_inputs"]
    )


def test_rendered_views(cli, repo) -> None:
    result = _run(cli, repo, "alpha", "--scope", "src", "--limit", "3")
    assert result.exit_code == 0, result.output
    assert "view=census_symbol" in result.stdout
    assert "# unresolved\tmixed_binding" in result.stdout
    assert "next: " in result.stdout


# --- the row model and the in-process function ----------------------------------------------


def test_saved_sites_round_trip_and_equal_the_in_process_census(cli, repo, trees) -> None:
    envelope = _sites_envelope(cli, repo, "alpha")
    text = json.dumps(envelope)
    loaded = load_census(text)
    assert loaded.roots == ("alpha",)
    assert [site.model_dump(mode="json") for site in loaded.sites] == envelope["items"]
    assert [row.model_dump(mode="json") for row in loaded.unresolved] == envelope["coverage"][
        "unresolved"
    ]
    for site in loaded.sites:
        assert CensusSite.model_validate_json(site.model_dump_json()) == site

    target = resolve_target(cwd=repo, project=repo, python=None)
    direct = run_census(target, ["alpha"], [Path(scope) for scope in SCOPES], workers=1)
    key = CensusSite.sort_key
    pyproject_free = [s for s in loaded.sites if s.path != "pyproject.toml"]
    # Without an installation only the root's own name counts as a mention.
    assert sorted(direct.sites, key=key) == sorted(pyproject_free, key=key)
    assert Counter(r.kind for r in direct.unresolved) == Counter(r.kind for r in loaded.unresolved)


def test_load_census_refuses_a_truncated_or_summary_result(cli, repo) -> None:
    truncated = _run(cli, repo, "alpha", *_scope_args("src"), "--sites", "--json", "--limit", "2")
    with pytest.raises(ValueError, match="truncated"):
        load_census(truncated.stdout)
    summary = _run(cli, repo, "alpha", *_scope_args("src"), "--json", "--limit", "0")
    with pytest.raises(ValueError):
        load_census(summary.stdout)


def test_worker_processes_give_the_same_rows(repo, monkeypatch) -> None:
    target = resolve_target(cwd=repo, project=repo, python=None)
    inline = run_census(target, ["alpha"], [Path("src")], workers=1)
    monkeypatch.setattr(census_scan, "_POOL_THRESHOLD", 0)
    pooled = run_census(target, ["alpha"], [Path("src")], workers=2)
    key = CensusSite.sort_key
    assert sorted(pooled.sites, key=key) == sorted(inline.sites, key=key)
    assert sorted(pooled.unresolved, key=lambda r: r.sort_key()) == sorted(
        inline.unresolved, key=lambda r: r.sort_key()
    )


def test_engine_keeps_a_comprehension_target_apart_from_the_import_it_shadows() -> None:
    source = (
        "from alpha import item\n"
        "def f(items):\n"
        "    default = item.default()\n"
        "    return [item.value for item in items]\n"
    )
    result = attribute(source, FileContext(path="m.py", roots=frozenset({"alpha"})))
    assert [(s.line, s.use, s.written_paths) for s in result.sites] == [
        (3, "call", ("alpha.item.default",))
    ]
    assert result.unresolved == []


def test_relative_names_resolve_against_the_package() -> None:
    module = FileContext(path="a/b/c.py", roots=frozenset({"alpha"}), module="a.b.c")
    package = FileContext(path="a/b/__init__.py", roots=frozenset(), module="a.b", is_package=True)
    assert module.absolute(".models.X") == "a.b.models.X"
    assert module.absolute("..x") == "a.x"
    assert package.absolute(".models") == "a.b.models"
    assert module.absolute("...x") is None  # beyond the top-level package `a`
    assert package.absolute("..x") == "a.x"
