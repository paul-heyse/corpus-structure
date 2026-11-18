"""Griffe static load of installed packages: timing, publicity, exports, deprecation."""

import sys
import sysconfig
import time

import astroid
import griffe

SITE = [sysconfig.get_paths()["purelib"]]


def load(name: str) -> tuple[griffe.Object, set[str], float]:
    loader = griffe.GriffeLoader(allow_inspection=False, search_paths=SITE)
    start = time.perf_counter()
    module = loader.load(name, try_relative_path=False)
    unresolved, _ = loader.resolve_aliases(external=False)
    return module, unresolved, time.perf_counter() - start


def walk(obj):
    for member in obj.members.values():
        if member.is_alias:
            continue
        yield member
        if member.is_module or member.is_class:
            yield from walk(member)


for name in ("typer", "pydantic", "structlog"):
    module, unresolved, seconds = load(name)
    public = sorted(n for n, m in module.members.items() if m.is_public)
    print(f"{name}: {seconds:.2f}s public_top_level={len(public)} exports={len(module.exports or [])} unresolved={len(unresolved)}")
    if name == "typer":
        for symbol in ("Typer", "Option", "Argument", "Context", "run"):
            print(f"  typer.{symbol}: is_public={module.members[symbol].is_public}")
        astroid_names = astroid.MANAGER.ast_from_module_name("typer").wildcard_import_names()
        print(f"  astroid wildcard_import_names={len(astroid_names)} has_Typer={'Typer' in astroid_names}")
    if name == "pydantic":
        functions = [m for m in walk(module) if m.is_function]
        decorated = [f for f in functions if any("deprecated" in str(d.value) for d in f.decorators)]
        flagged = [f for f in functions if f.deprecated]
        print(f"  functions decorated @deprecated={len(decorated)} griffe .deprecated set={len(flagged)}")
    print(f"  target imported into this process: {name in sys.modules}")
