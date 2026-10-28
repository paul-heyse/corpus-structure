from __future__ import annotations

from pathlib import Path

import pytest

import check_pins

MANIFEST = """[workspace]
members = []

[workspace.metadata.pins]
families = ["arrow(-.+)?", "datafusion"]

[workspace.dependencies]
arrow-array = "=59.3.0"
"""

LOCK = """version = 4

[[package]]
name = "arrow-array"
version = "59.3.0"

[[package]]
name = "syn"
version = "1.0.0"

[[package]]
name = "syn"
version = "2.0.0"
"""

PINNED = """serde = "=1.0.228"
fork = { git = "https://example.invalid/fork", rev = "abc" }
local = { path = "crates/local" }
"""


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "Cargo.toml").write_text(MANIFEST)
    (tmp_path / "Cargo.lock").write_text(LOCK)
    return tmp_path


def test_single_versions_pass_and_unrelated_duplicates_are_ignored(root: Path) -> None:
    assert check_pins.main([], root) == 0


def test_a_second_family_version_fails(root: Path) -> None:
    lock = root / "Cargo.lock"
    lock.write_text(LOCK + '\n[[package]]\nname = "arrow-array"\nversion = "58.0.0"\n')
    family = check_pins.families(root / "Cargo.toml")
    assert check_pins.duplicates(lock, family) == {"arrow-array": ["58.0.0", "59.3.0"]}
    assert check_pins.main([], root) == 1


def test_no_declared_families_checks_only_pins(root: Path) -> None:
    (root / "Cargo.toml").write_text(MANIFEST.replace('"arrow(-.+)?", "datafusion"', ""))
    assert check_pins.families(root / "Cargo.toml") is None
    assert check_pins.main([], root) == 0


def test_exact_pins_git_revs_and_path_dependencies_pass_without_a_row(root: Path) -> None:
    (root / "Cargo.toml").write_text(MANIFEST + PINNED)
    assert not (root / "docs").exists()
    assert check_pins.unpinned(root / "Cargo.toml") == []
    assert check_pins.main([], root) == 0


def test_carets_floors_and_caps_fail(root: Path) -> None:
    loose = (
        'serde = "1.0.228"\ntoml = { version = "0.9" }\nanyhow = ">=1.0"\n'
        'rand = "~0.8"\nlog = "0.4.*"\nitoa = "=1.0, <2"\n'
    )
    (root / "Cargo.toml").write_text(MANIFEST + loose)
    assert check_pins.unpinned(root / "Cargo.toml") == [
        "anyhow: not pinned exactly ('>=1.0'; use =x.y.z)",
        "itoa: not pinned exactly ('=1.0, <2'; use =x.y.z)",
        "log: not pinned exactly ('0.4.*'; use =x.y.z)",
        "rand: not pinned exactly ('~0.8'; use =x.y.z)",
        "serde: not pinned exactly ('1.0.228'; use =x.y.z)",
        "toml: not pinned exactly ('0.9'; use =x.y.z)",
    ]
    assert check_pins.main([], root) == 1


def test_a_git_dependency_needs_a_rev(root: Path) -> None:
    git = (
        'a = { git = "https://example.invalid/a", tag = "v1" }\n'
        'b = { git = "https://example.invalid/b", branch = "main" }\n'
        'c = { git = "https://example.invalid/c" }\n'
    )
    (root / "Cargo.toml").write_text(MANIFEST + git)
    assert check_pins.unpinned(root / "Cargo.toml") == [
        "a: git dependency without a rev",
        "b: git dependency without a rev",
        "c: git dependency without a rev",
    ]


def test_a_family_member_must_be_pinned_exactly(root: Path) -> None:
    (root / "Cargo.toml").write_text(MANIFEST.replace('"=59.3.0"', '"59.3.0"'))
    assert check_pins.unpinned(root / "Cargo.toml") == [
        "arrow-array: not pinned exactly ('59.3.0'; use =x.y.z)",
    ]
    assert check_pins.main([], root) == 1


def test_missing_lockfile_is_not_run_not_failure(root: Path) -> None:
    (root / "Cargo.lock").unlink()
    assert check_pins.main([], root) == 0


# --- Python manifests (DA-022) ----------------------------------------------------------------

ROOT_PYPROJECT = """[project]
name = "root"
version = "0"
dependencies = ["member-a", "local-tool"]

[dependency-groups]
dev = ["pytest==9.2.0", {include-group = "lint"}]
lint = ["ruff==0.17.3"]

[tool.uv.workspace]
members = ["packages/*"]
exclude = ["packages/skipped"]

[tool.uv.sources]
member-a = { workspace = true }
local-tool = { path = "tools/local" }
"""

MEMBER = """[project]
name = "member-a"
version = "0"
dependencies = ["psycopg[binary]==3.3.6", "regex==2026.9.29 ; python_version >= '3.14'"]

[project.optional-dependencies]
gpu = ["torch==2.9.1"]

[build-system]
requires = ["uv_build==0.13.6"]
"""


@pytest.fixture
def workspace(root: Path) -> Path:
    (root / "pyproject.toml").write_text(ROOT_PYPROJECT)
    for name, text in (("a", MEMBER), ("skipped", MEMBER.replace("==2.9.1", ">=2"))):
        (root / "packages" / name).mkdir(parents=True)
        (root / "packages" / name / "pyproject.toml").write_text(text)
    (root / "packages" / "no-manifest").mkdir()
    return root


def test_exact_python_pins_and_workspace_or_path_sources_pass(workspace: Path) -> None:
    assert check_pins.manifests(workspace) == [
        workspace / "pyproject.toml",
        workspace / "packages" / "a" / "pyproject.toml",
    ]
    for path in check_pins.manifests(workspace):
        assert check_pins.python_unpinned(path) == []
    assert check_pins.main([], workspace) == 0


def test_a_python_range_fails_the_pin_check(workspace: Path) -> None:
    member = workspace / "packages" / "a" / "pyproject.toml"
    member.write_text(MEMBER.replace("psycopg[binary]==3.3.6", "psycopg[binary]>=3.3"))
    assert check_pins.python_unpinned(member) == [
        "[project] dependencies: psycopg[binary]>=3.3: not pinned exactly ('>=3.3'; use ==x.y.z)",
    ]
    assert check_pins.main([], workspace) == 1


def test_every_python_table_is_read(workspace: Path) -> None:
    loose = (
        ROOT_PYPROJECT.replace('"pytest==9.2.0"', '"pytest~=9.2"')
        .replace('"ruff==0.17.3"', '"ruff"')
        .replace('"member-a", "local-tool"', '"member-a", "local-tool", "rich==15.*"')
    )
    (workspace / "pyproject.toml").write_text(
        loose + '\n[build-system]\nrequires = ["uv_build<1"]\n'
    )
    member = workspace / "packages" / "a" / "pyproject.toml"
    member.write_text(MEMBER.replace("torch==2.9.1", "torch==2.9.1,<3"))
    assert check_pins.python_unpinned(workspace / "pyproject.toml") == [
        "[project] dependencies: rich==15.*: not pinned exactly ('==15.*'; use ==x.y.z)",
        "[dependency-groups] dev: pytest~=9.2: not pinned exactly ('~=9.2'; use ==x.y.z)",
        "[dependency-groups] lint: ruff: not pinned exactly ('no version'; use ==x.y.z)",
        "[build-system] requires: uv_build<1: not pinned exactly ('<1'; use ==x.y.z)",
    ]
    assert check_pins.python_unpinned(member) == [
        "[project.optional-dependencies] gpu: torch==2.9.1,<3: "
        "not pinned exactly ('==2.9.1,<3'; use ==x.y.z)",
    ]


def test_a_member_inherits_the_root_sources(workspace: Path) -> None:
    member = workspace / "packages" / "a" / "pyproject.toml"
    member.write_text(MEMBER.replace('"torch==2.9.1"', '"local-tool"'))
    inherited = check_pins.sources(check_pins.tomllib.loads(ROOT_PYPROJECT))
    assert check_pins.python_unpinned(member, inherited) == []
    assert check_pins.python_unpinned(member) == [
        "[project.optional-dependencies] gpu: local-tool: not pinned exactly ('no version'; "
        "use ==x.y.z)",
    ]
    assert check_pins.main([], workspace) == 0


def test_a_python_git_source_needs_a_rev(workspace: Path) -> None:
    text = ROOT_PYPROJECT.replace(
        'local-tool = { path = "tools/local" }',
        'local-tool = { git = "https://example.invalid/t", branch = "main" }',
    )
    (workspace / "pyproject.toml").write_text(text)
    assert check_pins.python_unpinned(workspace / "pyproject.toml") == [
        "[project] dependencies: local-tool: git source without a rev",
    ]
