"""`tooling library census ROOT... --scope PATH...`: how repository code uses import roots.

The default view (`census_symbol`) counts each written path's uses by kind, with the keywords
passed to it; `--sites` gives one row per site (`census_site`), the form `compare` reads back
(`--sites --json --limit 0`). Coverage lists the files read, the scopes with no use, what was
excluded, the files that failed to parse and the uses that could not be attributed, by kind.
`run_census` (in `census_scan`) is the same census as a plain function.
"""

from __future__ import annotations

import platform
from collections.abc import Sequence
from importlib.metadata import version
from pathlib import Path
from typing import Annotated

import typer

from corpus_tooling.envelope import Envelope, Item
from corpus_tooling.library.census_rows import (
    CensusSite,
    CensusSymbol,
    CensusUnresolved,
    summarize,
)
from corpus_tooling.library.census_scan import resolve_scope, run_census
from corpus_tooling.library.context import library_envelope, library_state
from corpus_tooling.library.target import Target
from corpus_tooling.output import (
    DEFAULT_LIMIT,
    JsonOpt,
    LimitOpt,
    OffsetOpt,
    StrictOpt,
    emit,
)


def check_roots(roots: Sequence[str], target: Target | None = None) -> None:
    """Refuse a ROOT that is not a dotted import name, or that is a submodule of a regular
    package in the target environment (`pydantic.main`): uses written through the parent
    (`from pydantic import BaseModel`) would not count, so the result would read as no use.
    A portion of a namespace package (`google.protobuf`) is a root of its own. Usage errors
    (exit 2)."""
    invalid = [root for root in roots if not all(part.isidentifier() for part in root.split("."))]
    if invalid:
        raise typer.BadParameter(
            f"not an import root: {', '.join(invalid)}; pass top-level import names such as "
            "`pydantic`, not distribution names",
            param_hint="'ROOTS...'",
        )
    environment = target.environment if target is not None else None
    if environment is None:
        return
    for root in roots:
        top = root.split(".", 1)[0]
        if root != top and any(
            (site / top / name).is_file()
            for site in environment.site_packages
            for name in ("__init__.py", "__init__.pyi")
        ):
            raise typer.BadParameter(
                f"{root} is a submodule of the regular package {top}: uses written through "
                f"{top} would not count; pass {top} (and narrow the result with --match)",
                param_hint="'ROOTS...'",
            )


def check_scopes(target: Target, scopes: Sequence[Path]) -> None:
    """Refuse a `--scope` that does not exist: a usage error (exit 2), as for every path the
    caller names (`--project`, `--python`, `overview FILE`)."""
    missing = [path for path in scopes if not resolve_scope(target, path).exists()]
    if missing:
        shown = ", ".join(target.display(resolve_scope(target, path)) for path in missing)
        raise typer.BadParameter(
            f"no such scope: {shown} (relative scopes resolve against the project)",
            param_hint="'--scope'",
        )


def census(
    ctx: typer.Context,
    roots: Annotated[
        list[str],
        typer.Argument(
            help="Import roots, such as `pydantic` or `typer rich`.", show_default=False
        ),
    ],
    scope: Annotated[
        list[Path],
        typer.Option(
            "--scope",
            help="A directory or file to scan, relative to the project; repeat for several. "
            "Required: no default scope.",
            show_default=False,
        ),
    ],
    exclude: Annotated[
        list[str] | None,
        typer.Option(
            "--exclude",
            help="Leave out paths matching this glob (matched against the shown path, such as "
            "`**/migrations/**`); repeatable.",
        ),
    ] = None,
    sites: Annotated[
        bool, typer.Option("--sites", help="One row per site instead of the per-symbol summary.")
    ] = False,
    json: JsonOpt = False,
    limit: LimitOpt = DEFAULT_LIMIT,
    offset: OffsetOpt = 0,
    strict: StrictOpt = False,
) -> None:
    """How code under the scopes uses the import roots: imports, calls, subclasses,
    instantiations, decorators, references and mentions, with what could not be attributed."""
    state = library_state(ctx)
    target = state.target
    check_roots(roots, target)
    check_scopes(target, scope)
    installation = state.installation if target.environment is not None else None
    result = run_census(target, roots, scope, installation=installation, excludes=exclude or ())
    scanned = [
        f"scanned {group.scope}: {group.files} files of project {group.project or '(none)'}"
        for group in result.scanned_groups
    ]
    authorities = {"libcst": version("libcst"), "python-ast": platform.python_version()}

    def view[I: Item](item_type: type[I], items: list[I]) -> Envelope[I, CensusUnresolved]:
        return library_envelope(
            ctx,
            item_type,
            items,
            limit=limit,
            offset=offset,
            unresolved_type=CensusUnresolved,
            authorities=authorities,
            scanned=result.scanned,
            no_hit_scopes=result.no_hit_scopes,
            excluded=result.excluded,
            skipped_inputs=result.skipped_inputs,
            unresolved=result.unresolved,
            notes=[*result.notes, *scanned],
        )

    if sites:
        emit(view(CensusSite, result.sites), json=json, strict=strict)
    else:
        emit(view(CensusSymbol, summarize(result.sites)), json=json, strict=strict)


def register(group: typer.Typer) -> None:
    group.command("census")(census)
