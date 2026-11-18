"""The census's rows: the per-site view, the per-symbol summary, unresolved rows and the
in-process result `run_census` returns (LDT-04).

`CensusSite` is the per-site item kind (`census --sites`) and the input `compare` consumes,
either in process from `CensusResult.sites` or from a saved `census --json --sites --limit 0`
envelope through `load_census`. `written_paths` is a set, stored sorted and unique so the JSON
is deterministic: a name bound in both branches of a `try` or under `TYPE_CHECKING` resolves to
more than one path.

Positions are a 1-based line and the UTF-8 byte offset of the node's start within that line, as
`ast` reports columns.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Annotated, ClassVar, Literal

from pydantic import AfterValidator, Field

from corpus_tooling.envelope import (
    Column,
    Envelope,
    Item,
    SkippedInput,
    Unresolved,
)

SiteUse = Literal[
    "import", "call", "instantiation", "subclass", "decorator", "reference", "mention"
]
"""What a site row records. `instantiation` is a call whose callee the same census saw used as
a base class; `compare` can reclassify other calls with the inventory."""

ImportContext = Literal["module", "function", "class", "try", "type_checking"]
_CONTEXT_ORDER: tuple[ImportContext, ...] = ("module", "function", "class", "try", "type_checking")

UnresolvedKind = Literal[
    "assignment_alias",
    "instance_member",
    "subclass_member",
    "getattr",
    "dynamic_import",
    "string_reference",
    "reexport_chain",
    "mixed_binding",
]
"""Examined and not attributable by the census's method:

- `assignment_alias`: a use of a name bound by assignment to a family expression
  (`opt = typer.Option; opt(...)`);
- `instance_member`: a member reached through a name bound to the result of a family call or
  of a repository subclass's constructor (`app.command`, `model.model_dump`);
- `subclass_member`: a member reached through a repository class with an attributed base
  (`MyModel.model_validate`);
- `getattr`: `getattr` on a family module or object;
- `dynamic_import`: `importlib.import_module` or `__import__`, with a literal naming a root or
  with an argument that is not a literal;
- `string_reference`: a string literal that is a dotted family path (`"pkg.mod:attr"`);
- `reexport_chain`: a name reached through more than one repository re-export;
- `mixed_binding`: a name that may be bound to a family symbol or to something else at the site
  (a later local assignment, a fallback in an `except` branch).
"""


def _sorted_unique(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(set(values)))


PathSet = Annotated[tuple[str, ...], AfterValidator(_sorted_unique)]


def _context_order(values: tuple[ImportContext, ...]) -> tuple[ImportContext, ...]:
    return tuple(context for context in _CONTEXT_ORDER if context in values)


class CensusSite(Item):
    """One use of an import root at one place in the scope."""

    kind: Literal["census_site"] = "census_site"
    use: SiteUse
    path: str
    line: int
    column: int = Field(description="UTF-8 byte offset of the node's start within the line.")
    project: str | None = Field(default=None, description="The uv project owning the file.")
    written_paths: PathSet
    via: str | None = Field(
        default=None, description="The repository module a one-hop re-export was followed through."
    )
    # call, instantiation and decorator-with-arguments
    positional: int | None = None
    keywords: PathSet = ()
    star_args: bool = False
    star_kwargs: bool = False
    # import
    statement: Literal["import", "from"] | None = None
    module: str | None = Field(default=None, description="The written module, without dots.")
    level: int = 0
    alias: str | None = None
    context: Annotated[tuple[ImportContext, ...], AfterValidator(_context_order)] = ()
    # mention
    text: str | None = Field(default=None, description="The mentioning line or requirement.")

    columns: ClassVar = (
        Column("use"),
        Column("written_paths", "written paths"),
        Column("path"),
        Column("line"),
        Column("column"),
        Column("project"),
        Column("via"),
        Column("keywords"),
        Column("context"),
    )
    sort_fields: ClassVar = ("path", "line", "column", "use", "written_paths")


SymbolUse = Literal[
    "import", "call", "instantiation", "subclass", "decorator", "reference", "mention", "keyword"
]


class CensusSymbol(Item):
    """Per-symbol summary: how often one written path is used one way, in how many files. A
    `keyword` row counts calls passing `keyword` to `symbol`. A site with several written paths
    counts once under each."""

    kind: Literal["census_symbol"] = "census_symbol"
    symbol: str
    use: SymbolUse
    keyword: str | None = None
    count: int
    files: int

    columns: ClassVar = (
        Column("symbol"),
        Column("use"),
        Column("keyword"),
        Column("count"),
        Column("files"),
    )
    sort_fields: ClassVar = ("count", "symbol", "use", "keyword")

    def sort_key(self) -> tuple[object, ...]:
        return (-self.count, self.symbol, self.use, self.keyword or "")


class CensusUnresolved(Unresolved):
    """`location` is `path:line:column` (UTF-8 byte column); `subject` is the source text
    examined; `owner` names the local name or repository class a member was reached through."""

    kind: UnresolvedKind
    project: str | None = None
    written_paths: PathSet = ()
    owner: str | None = None

    def sort_key(self) -> tuple[str, str, str]:
        path, line, column = _split_location(self.location)
        return (self.kind, f"{path}\0{line:09d}\0{column:09d}", self.subject)


def _split_location(location: str) -> tuple[str, int, int]:
    path, _, rest = location.rpartition(":")
    path, _, line = path.rpartition(":")
    try:
        return path, int(line), int(rest)
    except ValueError:
        return location, 0, 0


def location(path: str, line: int, column: int) -> str:
    return f"{path}:{line}:{column}"


@dataclass(frozen=True)
class ScannedGroup:
    """Files read under one scope root that one uv project owns."""

    scope: str
    project: str | None
    files: int


@dataclass(frozen=True)
class CensusResult:
    """Everything one census establishes, independent of the view a command renders."""

    roots: tuple[str, ...]
    sites: list[CensusSite]
    unresolved: list[CensusUnresolved]
    scanned: int
    scanned_groups: list[ScannedGroup] = field(default_factory=list)
    no_hit_scopes: list[str] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)
    skipped_inputs: list[SkippedInput] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


CensusSitesEnvelope = Envelope[CensusSite, CensusUnresolved]


def load_census(text: str) -> CensusResult:
    """Rebuild a census from a saved `census ROOT... --scope ... --sites --json --limit 0`.

    Refuses another view, a failed result or a truncated item list, since any of these would
    make absent rows look like absent use."""
    envelope = CensusSitesEnvelope.model_validate_json(text)
    if envelope.status != "ok":
        raise ValueError("the saved census is a failed result")
    if envelope.view != "census_site":
        raise ValueError(f"the saved census holds view {envelope.view!r}, not 'census_site'")
    if envelope.truncated:
        raise ValueError("the saved census is truncated; save it with --sites --limit 0")
    roots = _roots_from_command(envelope.command)
    coverage = envelope.coverage
    return CensusResult(
        roots=roots,
        sites=list(envelope.items),
        unresolved=list(coverage.unresolved),
        scanned=coverage.scanned,
        no_hit_scopes=list(coverage.no_hit_scopes),
        excluded=list(coverage.excluded),
        skipped_inputs=list(coverage.skipped_inputs),
        notes=list(envelope.notes),
    )


def _roots_from_command(command: str) -> tuple[str, ...]:
    """The ROOT arguments of a normalized `tooling library ... census ROOT... --option ...`."""
    import shlex

    tokens = shlex.split(command)
    if "census" not in tokens:
        return ()
    roots: list[str] = []
    rest = iter(tokens[tokens.index("census") + 1 :])
    for token in rest:
        if token.startswith("--"):
            if token in _VALUE_OPTIONS:
                next(rest, None)
            continue
        roots.append(token)
    return tuple(roots)


_VALUE_OPTIONS = {"--scope", "--exclude", "--limit", "--offset"}


def summarize(sites: Iterable[CensusSite]) -> list[CensusSymbol]:
    """The per-symbol view of a list of sites."""
    counts: dict[tuple[str, SymbolUse, str | None], int] = {}
    files: dict[tuple[str, SymbolUse, str | None], set[str]] = {}

    def add(key: tuple[str, SymbolUse, str | None], path: str) -> None:
        counts[key] = counts.get(key, 0) + 1
        files.setdefault(key, set()).add(path)

    for site in sites:
        for written in site.written_paths:
            add((written, site.use, None), site.path)
            for keyword in site.keywords:
                add((written, "keyword", keyword), site.path)
    return [
        CensusSymbol(symbol=symbol, use=use, keyword=keyword, count=count, files=len(files[key]))
        for key, count in counts.items()
        for symbol, use, keyword in [key]
    ]
