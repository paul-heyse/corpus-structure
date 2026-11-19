"""Compare the saved root scan and exercise small, independently specified workloads."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory

import libcst as cst
from libcst.metadata import FullRepoManager, FullyQualifiedNameProvider, QualifiedNameProvider

from corpus_structure.semantic.code_identity import capture_code_identity

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parents[3] / "python/corpus-structure/src/corpus_structure"
BASELINE = HERE.parent / "2026-11-19_udm14-15-disk-cache/raw/code-closure.json"


def scan_real_roots():
    baseline = json.loads(BASELINE.read_text())
    roots = {}
    for name, expected in baseline.items():
        captured = capture_code_identity(PACKAGE, (f"corpus_structure.{name}",))
        observed = {
            "modules": len(captured.modules),
            "complete": captured.complete,
            "unknowns": [asdict(item) for item in captured.unknowns],
        }
        assert observed == expected, name
        roots[name] = {**observed, "unknowns": len(observed["unknowns"])}
    return roots


def run_entry(root: Path):
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "import sys; sys.path.insert(0, sys.argv[1]); from fixture.entry import entry; print(entry())",
            str(root.parent),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return int(result.stdout.strip())


def run_fixtures(root: Path):
    package = root / "fixture"
    package.mkdir()
    initializer = package / "__init__.py"
    entry = package / "entry.py"
    helper = package / "helper.py"
    helper.write_text("def provide():\n    return 5\n")
    initializer.write_text(
        "def unrelated(module_name):\n    import importlib\n"
        "    return importlib.import_module(module_name)\n"
    )
    entry.write_text("from .helper import provide as source\ndef entry():\n    return source()\n")
    coarse = capture_code_identity(package, ("fixture.entry",))
    assert len(coarse.unknowns) == 1 and coarse.unknowns[0].module == "fixture"
    assert run_entry(package) == 5

    manager = FullRepoManager(root, {str(entry)}, {FullyQualifiedNameProvider})
    wrapper = manager.get_metadata_wrapper_for_path(str(entry))

    class CallNames(cst.CSTVisitor):
        METADATA_DEPENDENCIES = (QualifiedNameProvider, FullyQualifiedNameProvider)
        relative: list[str]
        absolute: list[str]

        def visit_Call(self, node: cst.Call) -> None:
            self.relative = sorted(
                item.name for item in self.get_metadata(QualifiedNameProvider, node.func)
            )
            self.absolute = sorted(
                item.name for item in self.get_metadata(FullyQualifiedNameProvider, node.func)
            )

    call_names = CallNames()
    wrapper.visit(call_names)
    relative, absolute = call_names.relative, call_names.absolute
    assert relative == [".helper.provide"] and absolute == ["fixture.helper.provide"]

    initializer.write_text("def initialize():\n    return 2\nvalue = initialize()\n")
    entry.write_text("from . import value\ndef entry():\n    return value\n")
    narrow = capture_code_identity(package, ("fixture.entry",), callables=("fixture.entry.entry",))
    assert narrow.narrowing_unknowns == ("module initialization requires whole-module interpretation",)
    assert run_entry(package) == 2
    initializer.write_text("def initialize():\n    return 3\nvalue = initialize()\n")
    changed = capture_code_identity(package, ("fixture.entry",))
    assert run_entry(package) == 3 and narrow.digest != changed.digest

    initializer.write_text("")
    entry.write_text(
        "import importlib\n\ndef entry():\n"
        "    return getattr(importlib, 'import_module')('fixture.helper').provide()\n"
    )
    indirect_before = capture_code_identity(package, ("fixture.entry",))
    assert indirect_before.complete and run_entry(package) == 5
    helper.write_text("def provide():\n    return 6\n")
    indirect_after = capture_code_identity(package, ("fixture.entry",))
    assert indirect_after.complete and run_entry(package) == 6
    assert indirect_before.digest == indirect_after.digest
    assert "fixture.helper" not in {item.module for item in indirect_after.modules}
    return {
        "uninvoked_function": {"reported_unknowns": 1, "output": 5},
        "relative_alias": {"lexical": relative, "repository_qualified": absolute},
        "initializer": {"outputs": [2, 3], "basis_changed": True, "narrowing_refused": True},
        "unrecognized_indirect_load": {
            "outputs": [5, 6],
            "reported_complete_before_and_after": True,
            "basis_changed": False,
        },
    }


def main():
    with TemporaryDirectory() as fixture:
        report = {
            "python": sys.version.split()[0],
            "libcst": version("libcst"),
            "bounded_fixtures": run_fixtures(Path(fixture)),
            "real_roots": scan_real_roots(),
        }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
