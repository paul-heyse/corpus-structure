"""The census's attributed pass: one function from a file's source text to attributed site rows
and unresolved rows (`attribute`).

The engine resolves the base name of every call, attribute chain, base class and decorator to
the bindings it may refer to at that site, honoring import aliases, scopes and shadowing, and
then decides per site:

- every candidate binding is an import of a root (or a one-hop repository re-export of one):
  an attributed row whose `written_paths` are those imports plus the attribute tail;
- some candidates are family imports and others are not: `mixed_binding`;
- the name is bound by assignment to a family expression: `assignment_alias`;
- the name is bound to the result of a family call, or of a repository subclass's
  constructor, and a member is reached through it: `instance_member`;
- the name is a repository class with an attributed base and a member is reached through it:
  `subclass_member`;
- a re-export followed for more than one hop: `reexport_chain`.

Nothing is guessed about the owner of a member reached through an instance or subclass.
Import statements themselves are rows of the exact pass (`census_scan`), not of this one.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from corpus_tooling.library.census_rows import (
    CensusSite,
    CensusUnresolved,
    SiteUse,
    UnresolvedKind,
    location,
)

_LINE_BREAK = re.compile(r"\r\n|\r|\n")
_MAX_DEPTH = 4


def under_root(qualified: str, roots: Iterable[str]) -> bool:
    """Whether a written path is a root or lies below one; a root may be dotted
    (`google.protobuf`)."""
    return any(qualified == root or qualified.startswith(root + ".") for root in roots)


@dataclass(frozen=True)
class ReExport:
    """A repository module-level name that stands for a family path."""

    path: str
    hop: int
    """1 when the module imports it from a root; n when it imports it from a module at hop n-1."""
    via: str
    """The repository module holding the name (the module a user of the name imports from)."""


@dataclass(frozen=True)
class FileContext:
    """What the attributed pass needs to know about one file besides its text."""

    path: str
    roots: frozenset[str]
    module: str | None = None
    """The file's dotted module name, when it lies in a package; relative imports need it."""
    is_package: bool = False
    project: str | None = None
    reexports: Mapping[str, ReExport] = field(default_factory=dict)
    """`module.name` of repository re-exports of family names (the exact pass's table)."""

    def absolute(self, qualified: str) -> str | None:
        """A qualified name with its leading dots resolved against the file's package."""
        level = len(qualified) - len(qualified.lstrip("."))
        if level == 0:
            return qualified
        if self.module is None:
            return None
        parts = self.module.split(".")
        package = parts if self.is_package else parts[:-1]
        if level - 1 >= len(package):
            return None  # beyond the top-level package
        base = package[: len(package) - (level - 1)]
        tail = qualified[level:]
        return ".".join([*base, tail] if tail else base) or None

    def is_root(self, qualified: str) -> bool:
        return under_root(qualified, self.roots)

    def imported(self, qualified: str) -> Candidate:
        """The candidate an import-bound qualified name (absolute or relative) stands for."""
        absolute = self.absolute(qualified)
        if absolute is None:
            return OTHER
        if self.is_root(absolute):
            return Candidate("family", (absolute,))
        entry = lookup_reexport(self.reexports, absolute)
        if entry is None:
            return OTHER
        return Candidate("family" if entry.hop == 1 else "chain", (entry.path,), via=entry.via)


def lookup_reexport(table: Mapping[str, ReExport], absolute: str) -> ReExport | None:
    """The re-export an absolute repository path reaches through its longest `module.name`
    prefix in the table, with the remaining tail appended to the family path."""
    parts = absolute.split(".")
    for cut in range(len(parts), 1, -1):
        entry = table.get(".".join(parts[:cut]))
        if entry is not None:
            return ReExport(".".join([entry.path, *parts[cut:]]), entry.hop, entry.via)
    return None


CandidateKind = Literal["family", "alias", "instance", "repo_class", "chain", "other"]


@dataclass(frozen=True)
class Candidate:
    """One binding a name may refer to at a site, already classified."""

    kind: CandidateKind
    paths: tuple[str, ...] = ()
    via: str | None = None
    owner: str | None = None
    detail: str = ""

    def extended(self, attributes: Sequence[str]) -> Candidate:
        """The candidate for `name.a.b` when this one is for `name`: family and alias paths
        take the tail; an instance or class keeps its own paths (the tail is a member)."""
        if not attributes or self.kind not in ("family", "alias", "chain"):
            return self
        tail = ".".join(attributes)
        return Candidate(
            self.kind,
            tuple(f"{path}.{tail}" for path in self.paths),
            self.via,
            self.owner,
            self.detail,
        )


OTHER = Candidate("other")


@dataclass(frozen=True)
class Decision:
    kind: Literal["attributed"] | UnresolvedKind
    paths: tuple[str, ...]
    via: str | None = None
    owner: str | None = None
    detail: str = ""


def _union(candidates: Iterable[Candidate]) -> tuple[str, ...]:
    return tuple(sorted({path for candidate in candidates for path in candidate.paths}))


def _via(candidates: Iterable[Candidate]) -> str | None:
    vias = sorted({candidate.via for candidate in candidates if candidate.via})
    return ", ".join(vias) or None


def decide(candidates: Sequence[Candidate], *, member: bool) -> Decision | None:
    """Turn the candidate bindings of one site into a row decision. `member` is true when the
    site reaches an attribute of the name (`name.attr`) rather than the name itself."""
    kinds = {candidate.kind for candidate in candidates}
    family = [candidate for candidate in candidates if candidate.kind == "family"]
    if not kinds or kinds == {"other"}:
        return None
    if kinds == {"family"}:
        return Decision("attributed", _union(family), via=_via(family))
    if family:
        return Decision(
            "mixed_binding",
            _union(family),
            via=_via(family),
            detail="also bound to something other than a root import in this scope",
        )
    for kind, unresolved in (
        ("chain", "reexport_chain"),
        ("alias", "assignment_alias"),
        ("instance", "instance_member"),
        ("repo_class", "subclass_member"),
    ):
        chosen = [candidate for candidate in candidates if candidate.kind == kind]
        if not chosen or (kind in ("instance", "repo_class") and not member):
            continue
        owners = sorted({candidate.owner for candidate in chosen if candidate.owner})
        details = sorted({candidate.detail for candidate in chosen if candidate.detail})
        return Decision(
            unresolved,  # type: ignore[arg-type]
            _union(chosen),
            via=_via(chosen),
            owner=", ".join(owners) or None,
            detail="; ".join(details),
        )
    return None


def value_candidate(
    decision: Decision | None,
    candidates: Sequence[Candidate],
    *,
    call: bool,
    member: bool,
    owner: str,
) -> Candidate:
    """What a name bound by `owner = <value>` (or `with <value> as owner`) stands for.

    For a call value, `decision` and `candidates` describe the callee; otherwise the value
    expression itself. `member` is true when that expression reaches an attribute."""
    kinds = {candidate.kind for candidate in candidates}
    from_family = decision is not None and decision.kind in ("instance_member", "subclass_member")
    if call:
        if decision is not None and decision.kind == "attributed":
            return Candidate("instance", decision.paths, owner=owner, detail="result of a call")
        if decision is not None and from_family:
            return Candidate(
                "instance", decision.paths, owner=owner, detail=f"result of {decision.owner}"
            )
        if not member and kinds == {"repo_class"}:
            names = ", ".join(sorted({c.owner for c in candidates if c.owner}))
            return Candidate(
                "instance", _union(candidates), owner=owner, detail=f"instance of {names}"
            )
        if kinds == {"alias"}:
            return Candidate("instance", _union(candidates), owner=owner, detail="call of an alias")
        return OTHER
    if decision is not None and decision.kind == "attributed":
        return Candidate("alias", decision.paths, via=decision.via, owner=owner)
    if member:
        if decision is not None and from_family:
            return Candidate(
                "instance", decision.paths, owner=owner, detail=f"member of {decision.owner}"
            )
        return OTHER
    if len(kinds) != 1:
        return OTHER
    (kind,) = kinds
    if kind == "alias":
        return Candidate("alias", _union(candidates), owner=owner)
    if kind == "instance":
        others = ", ".join(sorted({c.owner for c in candidates if c.owner}))
        return Candidate("instance", _union(candidates), owner=owner, detail=f"bound to {others}")
    if kind == "repo_class":
        return Candidate("repo_class", _union(candidates), owner=candidates[0].owner)
    if kind == "chain":
        return Candidate("chain", _union(candidates), via=_via(candidates), owner=owner)
    return OTHER


@dataclass
class Attribution:
    """The attributed pass's rows for one file."""

    sites: list[CensusSite] = field(default_factory=list)
    unresolved: list[CensusUnresolved] = field(default_factory=list)


@dataclass(frozen=True)
class CallShape:
    positional: int
    keywords: tuple[str, ...]
    star_args: bool
    star_kwargs: bool


class RowSink:
    """Builds rows for one file, converting character columns to UTF-8 byte offsets."""

    def __init__(self, context: FileContext, source: str) -> None:
        self.context = context
        self._lines = _LINE_BREAK.split(source)
        self.result = Attribution()

    def byte_column(self, line: int, character: int) -> int:
        if not 0 < line <= len(self._lines):
            return character
        return len(self._lines[line - 1][:character].encode("utf-8", "surrogatepass"))

    def emit(
        self,
        use: SiteUse,
        decision: Decision | None,
        *,
        line: int,
        column: int,
        subject: str,
        call: CallShape | None = None,
    ) -> None:
        """Record one site; `column` is already a UTF-8 byte offset."""
        if decision is None:
            return
        if decision.kind == "attributed":
            self.result.sites.append(
                CensusSite(
                    use=use,
                    path=self.context.path,
                    line=line,
                    column=column,
                    project=self.context.project,
                    written_paths=decision.paths,
                    via=decision.via,
                    positional=call.positional if call else None,
                    keywords=call.keywords if call else (),
                    star_args=call.star_args if call else False,
                    star_kwargs=call.star_kwargs if call else False,
                )
            )
            return
        self.unresolved(
            decision.kind,  # type: ignore[arg-type]
            line=line,
            column=column,
            subject=subject,
            paths=decision.paths,
            owner=decision.owner,
            detail=decision.detail,
        )

    def unresolved(
        self,
        kind: UnresolvedKind,
        *,
        line: int,
        column: int,
        subject: str,
        paths: tuple[str, ...] = (),
        owner: str | None = None,
        detail: str = "",
    ) -> None:
        self.result.unresolved.append(
            CensusUnresolved(
                kind=kind,
                subject=" ".join(subject.split())[:200],
                location=location(self.context.path, line, column),
                detail=detail,
                project=self.context.project,
                written_paths=paths,
                owner=owner,
            )
        )


def call_shape(
    arguments: Iterable[tuple[str | None, str]],
) -> CallShape:
    """`arguments` are (keyword or None, star) pairs; star is "", "*" or "**"."""
    positional = 0
    keywords: list[str] = []
    star_args = star_kwargs = False
    for keyword, star in arguments:
        if star == "*":
            star_args = True
        elif star == "**":
            star_kwargs = True
        elif keyword is not None:
            keywords.append(keyword)
        else:
            positional += 1
    return CallShape(positional, tuple(keywords), star_args, star_kwargs)


def attribute(source: str, context: FileContext) -> Attribution:
    """The attributed pass over one file's source text (already judged valid by `ast`).

    The engine is LibCST (`_attribution_libcst`). The opening slice of LDT-04 also ran an
    `ast` + `symtable` engine against the census fixture and rejected it: PEP 709 inlines
    comprehensions, so a comprehension target that shadows an imported name used elsewhere in
    the same function, class body or module is classified with that import, a silent wrong
    attribution."""
    from corpus_tooling.library import _attribution_libcst

    return _attribution_libcst.attribute(source, context)
