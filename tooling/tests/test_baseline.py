import hashlib
import json
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from corpus_tooling.cli import app
from corpus_tooling.library.context import parse_porcelain_z


def _baseline(*args: str):
    return CliRunner().invoke(app, ["library", *args, "baseline", "--json"])


def _entries(envelope: dict) -> list[tuple[str, str, str, str | None]]:
    return [
        (item["category"], item["name"], item["path"], item["requires_python"])
        for item in envelope["items"]
    ]


def test_baseline_lists_project_members_groups_and_other_projects(trees) -> None:
    result = _baseline("--project", str(trees.project))
    assert result.exit_code == 0, result.output
    envelope = json.loads(result.stdout)
    assert envelope["view"] == "baseline_entry"
    assert _entries(envelope) == [
        ("project", "fixture-root", ".", ">=3.12"),
        ("workspace_member", "one", "packages/one", ">=3.12"),
        ("workspace_member", "two", "packages/two", None),
        ("dependency_group", "dev", ".", None),
        ("dependency_group", "lint", ".", None),
        ("dependency_group", "docs", "packages/one", None),
        ("uv_project", "other", "nested/other", ">=3.11"),
    ]
    assert envelope["coverage"]["scanned"] == 4  # root, two members, nested/other
    assert envelope["coverage"]["skipped_inputs"] == []
    lock = hashlib.sha256((trees.project / "uv.lock").read_bytes()).hexdigest()
    assert envelope["baseline"]["lock_digest"] == f"sha256:{lock}"


def test_unreadable_member_pyproject_is_a_skipped_input(trees) -> None:
    (trees.project / "packages" / "two" / "pyproject.toml").write_text("[project\n")
    result = _baseline("--project", str(trees.project))
    assert result.exit_code == 0
    envelope = json.loads(result.stdout)
    assert ("workspace_member", "two", "packages/two", None) in _entries(envelope)
    (skipped,) = envelope["coverage"]["skipped_inputs"]
    assert skipped["input"] == "packages/two/pyproject.toml"
    assert skipped["reason"] == "unreadable_pyproject"
    strict = CliRunner().invoke(
        app, ["library", "--project", str(trees.project), "baseline", "--json", "--strict"]
    )
    assert strict.exit_code == 1


def _git(repository: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def test_baseline_in_a_repository_reports_revision_dirty_paths_and_tracked_projects(
    trees, monkeypatch
) -> None:
    repository = trees.project
    (repository / ".gitignore").write_text(".venv/\nignored/\n")
    (repository / "ignored").mkdir()
    (repository / "ignored" / "uv.lock").write_text("version = 1\n")
    _git(repository, "init", "-q")
    _git(repository, "add", "-A")
    _git(repository, "commit", "-q", "-m", "fixture")
    head = _git(repository, "rev-parse", "HEAD").strip()
    (repository / "packages" / "one" / "pyproject.toml").write_text(
        '[project]\nname = "one"\nrequires-python = ">=3.13"\n'
    )
    _git(repository, "mv", "packages/notes/README.md", "packages/notes/NOTES.md")
    (repository / "untracked" / "proj").mkdir(parents=True)
    (repository / "untracked" / "proj" / "uv.lock").write_text("version = 1\n")

    result = _baseline("--project", str(repository))
    assert result.exit_code == 0, result.output
    envelope = json.loads(result.stdout)
    assert envelope["baseline"]["revision"] == head
    assert envelope["baseline"]["dirty_paths"] == [
        "packages/notes/NOTES.md",
        "packages/one/pyproject.toml",
        "untracked/",
    ]
    assert "git" in envelope["tool"]["authorities"]
    projects = [entry for entry in _entries(envelope) if entry[0] == "uv_project"]
    assert projects == [
        ("uv_project", "other", "nested/other", ">=3.11"),
        ("uv_project", "proj", "untracked/proj", None),
    ]


def test_porcelain_z_reports_new_paths_of_renames() -> None:
    output = " M a.py\0R  new name.py\0old name.py\0?? dir/\0"
    assert parse_porcelain_z(output) == ["a.py", "dir/", "new name.py"]
