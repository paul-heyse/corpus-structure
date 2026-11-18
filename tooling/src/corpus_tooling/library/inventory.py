"""`tooling library inventory PACKAGE`: what an installed import package offers.

Two views over one static Griffe load (`surface.load_offered_surface`; the target is never
imported):

- `symbols` (default, item `offered_symbol`): one row per binding in the package tree, from the
  root module down through submodules and class members. A row carries the symbol identity
  (distribution, import root, the row's path, every public `exposed_paths` of the same
  declaration, its `declared_path`), publicity as two facts (`in_all`, `public`), signature,
  parameter documentation and markers with their reasons. `--depth` defaults to 1 (the
  top-level surface) and is unbounded when `--match` or `--marker` selects rows. Non-public
  rows are listed only with `--private`.
- `package` (item `package_fact`): environment-variable names and entry-point groups the
  package's source reads, the entry points its distributions declare, and namespace portions.

Coverage: skipped inputs are files not examined (compiled modules without a stub, parse
failures, files Griffe did not load); unresolved rows are aliases Griffe could not resolve and
reads whose name is not a string literal. Neither kind trips the other's field (DP-02).
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, ClassVar, Literal

import typer
from pydantic import BaseModel, ConfigDict, Field

from corpus_tooling.envelope import Column, Envelope, Item, Unresolved
from corpus_tooling.library.context import library_envelope, library_state
from corpus_tooling.output import DEFAULT_LIMIT, JsonOpt, LimitOpt, OffsetOpt, StrictOpt, emit

if TYPE_CHECKING:
    from corpus_tooling.library.inventory_items import InventoryResult


class View(StrEnum):
    symbols = "symbols"
    package = "package"


class SymbolKind(StrEnum):
    module = "module"
    class_ = "class"
    function = "function"
    attribute = "attribute"
    type_alias = "type_alias"


class Marker(StrEnum):
    deprecated = "deprecated"
    extension_point = "extension_point"
    configuration = "configuration"
    extra_gated = "extra_gated"


class ParameterInfo(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    kind: str | None
    annotation: str | None = None
    default: str | None = None
    description: str | None = None
    """From the docstring's parameter sections, including `Annotated[..., Doc(...)]` text."""


class OfferedSymbol(Item):
    kind: Literal["offered_symbol"] = "offered_symbol"
    path: str
    """This row's binding: where the name sits in the package tree."""
    symbol_kind: SymbolKind
    declared_path: str
    """Where Griffe finds the definition (an alias row names its final target)."""
    exposed_paths: list[str]
    """Every public path binding the same declaration (redundant aliases, re-exports)."""
    import_root: str
    distribution: str | None
    """Normalized name of the distribution whose files hold the declaration."""
    distribution_version: str | None
    depth: int
    """Path components below the import root (the root is 0)."""
    in_all: bool
    """Named in the parent module's `__all__`."""
    public: bool
    """Public by Griffe's rules: `__all__`, convention, or a redundant-alias re-export."""
    assigned_from: str | None = None
    """For an assignment alias (`X = other.Y`): the right-hand side's path."""
    inherited_from: str | None = None
    """For a member inherited from a base class no public path reaches: that base. The row's
    `path` is then also an exposed path, since it is the only public way to the member."""
    markers: list[Marker]
    marker_reasons: dict[str, str]
    summary: str = ""
    signature: str | None = None
    parameters: list[ParameterInfo] = Field(default_factory=list)
    returns: str | None = None
    overloads: list[str] = Field(default_factory=list)
    bases: list[str] = Field(default_factory=list)
    decorators: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    annotation: str | None = None
    value: str | None = None
    """An attribute's value as written, cut at 120 characters (marked with `…`)."""
    location: str | None = None
    """The declaration's file, relative to site-packages, and line."""

    columns: ClassVar = (
        Column("path"),
        Column("symbol_kind", "kind"),
        Column("declared_path", "declared"),
        Column("in_all", "in __all__"),
        Column("public"),
        Column("markers"),
        Column("summary"),
    )
    sort_fields: ClassVar = ("path",)


FactCategory = Literal[
    "env_var", "entry_point_group", "entry_point", "namespace_portion", "main_guard_binding"
]


class PackageFact(Item):
    kind: Literal["package_fact"] = "package_fact"
    category: FactCategory
    """`env_var` / `entry_point_group`: read by the package's source; `entry_point`: declared
    in its distribution's metadata; `namespace_portion`: a portion of a namespace package;
    `main_guard_binding`: a module-level name bound only under `if __name__ == "__main__":`,
    left out of the offered symbols."""
    name: str
    symbol: str | None
    """The symbol the fact belongs to: the reading function, class, assignment or module; the
    object an entry point names."""
    location: str
    detail: str = ""
    distribution: str | None = None

    columns: ClassVar = (
        Column("category"),
        Column("name"),
        Column("symbol"),
        Column("location"),
        Column("distribution"),
        Column("detail"),
    )
    sort_fields: ClassVar = ("category", "name", "location")


class InventoryUnresolved(Unresolved):
    kind: Literal["unresolved_alias", "non_literal_env_var", "non_literal_entry_point_group"]


def _import_root(value: str) -> str:
    if not value.isidentifier():
        raise typer.BadParameter(
            f"{value!r} is not an import root; name a top-level package such as `pydantic` "
            "and narrow with --match"
        )
    return value


def inventory(
    ctx: typer.Context,
    package: Annotated[
        str,
        typer.Argument(
            help="An installed top-level import package, such as `pydantic`.",
            callback=_import_root,
        ),
    ],
    view: Annotated[
        View,
        typer.Option(
            "--view",
            help="symbols: the offered symbols; package: package facts (symbol filters ignored).",
        ),
    ] = View.symbols,
    depth: Annotated[
        int | None,
        typer.Option(
            "--depth",
            min=0,
            help="Path components below the root (default 1; unbounded with --match/--marker).",
        ),
    ] = None,
    kind: Annotated[
        list[SymbolKind] | None, typer.Option("--kind", help="Only these symbol kinds.")
    ] = None,
    match: Annotated[
        str | None,
        typer.Option(
            "--match",
            help="Substring, or glob when it holds * ? [, of the path, declared or exposed paths.",
        ),
    ] = None,
    marker: Annotated[
        list[Marker] | None, typer.Option("--marker", help="Only rows carrying any of these.")
    ] = None,
    private: Annotated[
        bool, typer.Option("--private", help="Also list non-public bindings.")
    ] = False,
    json: JsonOpt = False,
    limit: LimitOpt = DEFAULT_LIMIT,
    offset: OffsetOpt = 0,
    strict: StrictOpt = False,
) -> None:
    """What an installed package offers: public symbols with identity, markers and docs."""
    from corpus_tooling.library.inventory_items import InventorySelection, build_inventory

    state = library_state(ctx)
    selection = InventorySelection(
        depth=depth if depth is not None else (None if match or marker else 1),
        kinds=frozenset(kind or ()),
        match=match,
        markers=frozenset(marker or ()),
        private=private,
    )
    result = build_inventory(package, state.target, state.installation, selection)
    if view is View.package:
        envelope = _envelope(ctx, PackageFact, result.facts, result, limit, offset)
    else:
        envelope = _envelope(ctx, OfferedSymbol, result.symbols, result, limit, offset)
    emit(envelope, json=json, strict=strict)


def _envelope[I: Item](
    ctx: typer.Context,
    item_type: type[I],
    items: Sequence[I],
    result: InventoryResult,
    limit: int,
    offset: int,
) -> Envelope[I, InventoryUnresolved]:
    return library_envelope(
        ctx,
        item_type,
        items,
        limit=limit,
        offset=offset,
        unresolved_type=InventoryUnresolved,
        authorities=result.authorities,
        scanned=result.scanned,
        skipped_inputs=result.skipped_inputs,
        unresolved=result.unresolved,
        unavailable_metadata=result.unavailable_metadata,
        notes=result.notes,
    )


def register(group: typer.Typer) -> None:
    group.command("inventory")(inventory)
