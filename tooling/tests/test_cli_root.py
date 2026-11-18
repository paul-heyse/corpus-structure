import subprocess
import sys
from typing import ClassVar, Literal

import pytest
from typer.testing import CliRunner

from corpus_tooling.cli import app
from corpus_tooling.envelope import Column, Envelope, Item, Unresolved
from corpus_tooling.library.baseline import BaselineEntry


def test_help_lists_the_library_group_and_its_commands() -> None:
    root = CliRunner().invoke(app, ["--help"])
    assert root.exit_code == 0
    assert "Repository tooling" in root.stdout
    assert "library" in root.stdout
    library = CliRunner().invoke(app, ["library", "--help"])
    assert library.exit_code == 0
    assert "baseline" in library.stdout
    assert "--project" in library.stdout


def test_the_tool_imports_neither_the_product_nor_heavy_libraries_at_startup() -> None:
    probe = (
        "import sys, corpus_tooling.cli\n"
        "loaded = [m for m in sys.modules if m.split('.')[0] in "
        "{'corpus_structure', 'griffe', 'libcst'}]\n"
        "assert not loaded, loaded\n"
    )
    subprocess.run([sys.executable, "-I", "-c", probe], check=True)


def test_an_item_kind_must_declare_columns_and_sort_fields() -> None:
    with pytest.raises(TypeError, match="columns"):

        class Undeclared(Item):  # pyright: ignore[reportUnusedClass]
            kind: Literal["undeclared"] = "undeclared"
            name: str

    with pytest.raises(TypeError, match="unknown"):

        class Misnamed(Item):  # pyright: ignore[reportUnusedClass]
            kind: Literal["misnamed"] = "misnamed"
            name: str
            columns: ClassVar = (Column("nam"),)
            sort_fields: ClassVar = ("name",)


def test_each_command_envelope_has_a_json_schema_with_its_closed_kinds() -> None:
    schema = Envelope[BaselineEntry, Unresolved].model_json_schema()
    assert schema["properties"]["schema"]["const"] == "tooling.library/1"
    entry = schema["$defs"]["BaselineEntry"]["properties"]
    assert entry["kind"]["const"] == "baseline_entry"
    assert set(entry["category"]["enum"]) == {
        "project",
        "workspace_member",
        "dependency_group",
        "uv_project",
    }
