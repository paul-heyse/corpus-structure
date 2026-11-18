"""Hand-written fixture trees for target, installation and baseline tests.

The trees are materialized under `tmp_path` rather than committed as files: a committed
`uv.lock` or `pyproject.toml` under `tooling/tests/` would itself be found by repository scans
(and by uv, ruff and pyrefly project discovery). `@ROOT@` is replaced by the tree's root, for the
absolute paths an editable install records.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

SITE = "lib/python3.12/site-packages"

# A fake Python 3.12 environment: pyvenv.cfg plus hand-written .dist-info folders.
ENVIRONMENT: dict[str, str] = {
    "pyvenv.cfg": (
        "home = /opt/python3.12/bin\n"
        "implementation = CPython\n"
        "version_info = 3.12.7\n"
        "include-system-site-packages = false\n"
    ),
    # Declared import names (top_level.txt), extras, entry points and project URLs.
    f"{SITE}/Alpha_Pkg-1.2.0.dist-info/METADATA": (
        "Metadata-Version: 2.1\n"
        "Name: Alpha_Pkg\n"
        "Version: 1.2.0\n"
        "Summary: The alpha package.\n"
        "Home-page: https://alpha.example\n"
        "Requires-Python: >=3.10\n"
        "Project-URL: Documentation, https://alpha.example/docs\n"
        "Requires-Dist: beta>=2\n"
        'Requires-Dist: gamma; extra == "fast"\n'
        "Provides-Extra: fast\n"
    ),
    f"{SITE}/Alpha_Pkg-1.2.0.dist-info/top_level.txt": "alpha\n",
    f"{SITE}/Alpha_Pkg-1.2.0.dist-info/entry_points.txt": (
        "[console_scripts]\nalpha = alpha.cli:main\n\n[alpha.plugins]\nextra = alpha.ext:Plugin\n"
    ),
    f"{SITE}/Alpha_Pkg-1.2.0.dist-info/RECORD": (
        "alpha/__init__.py,,\nAlpha_Pkg-1.2.0.dist-info/METADATA,,\n"
    ),
    # Import names inferred from RECORD; `shared_ns` is shared with gamma.
    f"{SITE}/beta-2.0.0.dist-info/METADATA": "Metadata-Version: 2.1\nName: beta\nVersion: 2.0.0\n",
    f"{SITE}/beta-2.0.0.dist-info/RECORD": (
        "beta/__init__.py,,\n"
        "beta/core.py,,\n"
        "shared_ns/beta_part.py,,\n"
        "beta-2.0.0.dist-info/METADATA,,\n"
        "beta-2.0.0.dist-info/RECORD,,\n"
        "../../../bin/beta,,\n"
    ),
    # `Distribution.files` omits RECORD entries that do not exist, so the modules are present.
    f"{SITE}/beta/__init__.py": "",
    f"{SITE}/beta/core.py": "",
    f"{SITE}/shared_ns/beta_part.py": "",
    f"{SITE}/gamma.py": "",
    f"{SITE}/shared_ns/gamma_part.py": "",
    f"{SITE}/_gamma_ext.cpython-312-x86_64-linux-gnu.so": "",
    f"{SITE}/__pycache__/gamma.cpython-312.pyc": "",
    f"{SITE}/gamma-0.3.0.dist-info/METADATA": "Metadata-Version: 2.1\nName: gamma\nVersion: 0.3.0\n",
    f"{SITE}/gamma-0.3.0.dist-info/RECORD": (
        "gamma.py,,\n"
        "shared_ns/gamma_part.py,,\n"
        "_gamma_ext.cpython-312-x86_64-linux-gnu.so,,\n"
        "__pycache__/gamma.cpython-312.pyc,,\n"
        "LICENSE,,\n"
        "gamma-0.3.0.dist-info/RECORD,,\n"
    ),
    # A top-level file without a module suffix is not an import name.
    f"{SITE}/LICENSE": "MIT\n",
    # An editable workspace package: RECORD lists only a .pth file.
    f"{SITE}/local_tool-0.1.0.dist-info/METADATA": (
        "Metadata-Version: 2.4\nName: local-tool\nVersion: 0.1.0\n"
    ),
    f"{SITE}/local_tool-0.1.0.dist-info/RECORD": (
        "local_tool.pth,,\nlocal_tool-0.1.0.dist-info/RECORD,,\n"
    ),
    f"{SITE}/local_tool-0.1.0.dist-info/direct_url.json": (
        '{"url": "file://@ROOT@/workspace/tool", "dir_info": {"editable": true}}\n'
    ),
    f"{SITE}/local_tool.pth": "@ROOT@/workspace/tool/src\nimport _never_executed\n",
    # A malformed entry_points.txt (no `=`): unreadable, reported as a skipped input.
    f"{SITE}/delta-1.0.0.dist-info/METADATA": "Metadata-Version: 2.1\nName: delta\nVersion: 1.0.0\n",
    f"{SITE}/delta-1.0.0.dist-info/entry_points.txt": "[g]\nnoequals\n",
    # Metadata without a Name: unreadable, reported as a skipped input.
    f"{SITE}/broken-0.0.0.dist-info/METADATA": "Metadata-Version: 2.1\nVersion: 0.0.0\n",
}

EDITABLE_SOURCE: dict[str, str] = {
    "workspace/tool/pyproject.toml": '[project]\nname = "local-tool"\nversion = "0.1.0"\n',
    "workspace/tool/src/local_tool/__init__.py": "",
    "workspace/tool/src/local_tool_helpers.py": "",
    "workspace/tool/src/not-a-module/readme.txt": "",
}

PROJECT: dict[str, str] = {
    "pyproject.toml": (
        "[project]\n"
        'name = "fixture-root"\n'
        'requires-python = ">=3.12"\n'
        "\n"
        "[dependency-groups]\n"
        'dev = ["pytest"]\n'
        'lint = ["ruff"]\n'
        "\n"
        "[tool.uv.workspace]\n"
        'members = ["packages/*"]\n'
        'exclude = ["packages/excluded"]\n'
    ),
    "uv.lock": 'version = 1\nrevision = 3\nrequires-python = ">=3.12"\n',
    "packages/one/pyproject.toml": (
        '[project]\nname = "one"\nrequires-python = ">=3.12"\n\n[dependency-groups]\ndocs = []\n'
    ),
    "packages/two/pyproject.toml": '[project]\nname = "two"\n',
    "packages/excluded/pyproject.toml": '[project]\nname = "excluded"\n',
    "packages/notes/README.md": "Not a member: no pyproject.toml.\n",
    "nested/other/pyproject.toml": '[project]\nname = "other"\nrequires-python = ">=3.11"\n',
    "nested/other/uv.lock": "version = 1\n",
}


def write_tree(root: Path, files: dict[str, str]) -> None:
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.replace("@ROOT@", root.as_posix()), encoding="utf-8")


@dataclass(frozen=True)
class Trees:
    root: Path
    project: Path
    """`fixture-root`, with the fake environment as its own `.venv`."""
    elsewhere: Path
    """A second copy of the fake environment, belonging to no project."""
    env_only: Path
    """A directory holding only `.venv` (no pyproject.toml, no uv.lock)."""

    @property
    def site_packages(self) -> Path:
        """The project environment's site-packages."""
        return self.project / ".venv" / SITE


@pytest.fixture
def trees(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Trees:
    # The test temp directory may sit inside this repository's work tree; keep git from
    # discovering it, so a tree is in a repository only when a test creates one.
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", tmp_path.as_posix())
    monkeypatch.delenv("UV_PROJECT_ENVIRONMENT", raising=False)
    monkeypatch.delenv("TTY_COMPATIBLE", raising=False)
    root = tmp_path
    write_tree(root, EDITABLE_SOURCE)
    write_tree(root / "project", PROJECT)
    for environment in ("project/.venv", "elsewhere/env", "envonly/.venv"):
        write_tree(root, {f"{environment}/{path}": text for path, text in ENVIRONMENT.items()})
    return Trees(
        root=root,
        project=root / "project",
        elsewhere=root / "elsewhere" / "env",
        env_only=root / "envonly",
    )
