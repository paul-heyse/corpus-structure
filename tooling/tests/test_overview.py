"""`tooling library overview`: a hand-written overview with a fenced `#` line, a deeper heading,
a numbering gap, a number-only title, an addendum and a stated version."""

import json

import pytest
import typer
from typer.testing import CliRunner

from corpus_tooling.library import overview
from corpus_tooling.library.app import REGISTRATIONS, make_library_app
from corpus_tooling.library.overview import compare_versions, stated_version

LINES = [
    "# Widget 2.0.0 — Library Overview",  # 1
    "",  # 2
    "Research date: November 1, 2026 · Target: Widget 2.1.0 · Python ≥3.11",  # 3
    "",  # 4
    "The latest stable release. Other 9.9.9 is only prose.",  # 5
    "",  # 6
    "## 1. Orientation",  # 7
    "",  # 8
    "```python",  # 9
    "# comment inside a fence",  # 10
    "## not a heading either",  # 11
    "```",  # 12
    "",  # 13
    "## 2. Model",  # 14
    "",  # 15
    "### 2.1 Detail",  # 16
    "",  # 17
    "## 4. Skipped number",  # 18
    "",  # 19
    "## 5",  # 20
    "",  # 21
    "## Overall assessment",  # 22
    "",  # 23
    "# Widget — Addendum",  # 24
    "",  # 25
    "The latest stable release. Other 3.0.0 is mentioned in prose.",  # 26
    "",  # 27
    "## 1. Extra semantics",  # 28
    "",  # 29
    "## 1. Repeated",  # 30
    "text",  # 31
]
TEXT = "\n".join(LINES) + "\n"


@pytest.fixture
def cli() -> typer.Typer:
    root = typer.Typer()

    @root.callback()
    def _root() -> None: ...

    root.add_typer(make_library_app((*REGISTRATIONS, overview.register)), name="library")
    return root


def _run(cli, trees, *args: str) -> dict:
    path = trees.project / "docs" / "widget.md"
    path.parent.mkdir()
    path.write_text(TEXT, encoding="utf-8")
    result = CliRunner().invoke(
        cli, ["library", "--project", str(trees.project), "overview", str(path), *args, "--json"]
    )
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


def _rows(envelope: dict) -> list[tuple]:
    return [
        (i["role"], i["part"], i["line"], i["end_line"], i["number"], i["title"], i["flags"])
        for i in envelope["items"]
    ]


def test_section_map_of_parts_and_sections(cli, trees) -> None:
    envelope = _run(cli, trees, "--distribution", "Alpha_Pkg")
    assert envelope["view"] == "overview_section"
    assert _rows(envelope) == [
        ("part", "main", 1, 23, None, "Widget 2.0.0 — Library Overview", []),
        ("section", "main", 7, 13, "1", "Orientation", []),
        ("section", "main", 14, 17, "2", "Model", []),
        ("section", "main", 18, 19, "4", "Skipped number", ["numbering_gap"]),
        ("section", "main", 20, 21, "5", "", ["title_only_number"]),
        ("section", "main", 22, 23, None, "Overall assessment", []),
        ("part", "addendum 1", 24, 31, None, "Widget — Addendum", []),
        ("section", "addendum 1", 28, 29, "1", "Extra semantics", []),
        ("section", "addendum 1", 30, 31, "1", "Repeated", ["numbering_out_of_order"]),
    ]
    main, addendum = (item for item in envelope["items"] if item["role"] == "part")
    # The labelled statement wins over the version in the title; prose never counts.
    assert (main["stated_version"], main["stated_subject"], main["stated_line"]) == (
        "2.1.0",
        "Widget",
        3,
    )
    assert main["stated_text"] == "Target: Widget 2.1.0"
    assert (main["distribution"], main["installed_version"]) == ("alpha-pkg", "1.2.0")
    assert main["version_status"] == "overview_newer"
    assert addendum["stated_version"] is None
    assert addendum["installed_version"] == "1.2.0"
    assert addendum["version_status"] is None
    assert envelope["tool"]["authorities"]["markdown-it-py"]
    assert envelope["coverage"]["unavailable_metadata"] == []


def test_default_distribution_is_the_stem_and_its_absence_is_reported(cli, trees) -> None:
    envelope = _run(cli, trees)
    main = envelope["items"][0]
    assert (main["distribution"], main["installed_version"], main["version_status"]) == (
        "widget",
        None,
        None,
    )
    assert main["stated_version"] == "2.1.0"
    assert envelope["coverage"]["unavailable_metadata"] == [
        {"subject": "widget", "field": "installed distribution", "detail": ""}
    ]
    assert any(note.startswith("widget: no installed distribution") for note in envelope["notes"])


@pytest.mark.parametrize(
    ("title", "opening", "expected"),
    [
        (
            "Rich 15.0.0 — Overview",
            "Target: Rich 15.0.0 · Typer integration: Typer 0.27.3",
            "15.0.0",
        ),
        (
            "ty — Reference",
            "Research date: November 12, 2026 | Version: 0.0.101 | Status: beta",
            "0.0.101",
        ),
        ("NetworkX — Overview", "Version 3.7 · Released September 21, 2026", "3.7"),
        (
            "Griffe — Overview",
            "Research date: x | Current stable release: 2.4.1 (October 22, 2026)",
            "2.4.1",
        ),
        ("LibCST 1.9.0 — Capability Addendum", "Research date: October 29, 2026", "1.9.0"),
        ("Typer — Overview", "Typer 0.28.0 was released on November 6, 2026.", None),
        ("Tree-sitter — Reference", "Version scope", None),
    ],
)
def test_stated_version_patterns(title: str, opening: str, expected: str | None) -> None:
    found = stated_version(title, 1, [(3, opening)])
    assert (found.version if found else None) == expected


@pytest.mark.parametrize(
    ("stated", "installed", "status"),
    [
        ("15.0.0", "15.0.0", "same"),
        ("5.3.2", "5.3.2.0", "same"),
        ("0.27.3", "0.28.0", "overview_older"),
        ("2.16.2", "2.16.1", "overview_newer"),
        ("2.0rc1", "2.0", "not_comparable"),
    ],
)
def test_version_comparison(stated: str, installed: str, status: str) -> None:
    assert compare_versions(stated, installed) == status
