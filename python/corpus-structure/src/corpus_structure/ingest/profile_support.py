"""The hand-written part the generated source-profile classes use (model and projections §3.3).

`ingest/_shapes.py` is generated from `model/system.yaml`'s `SourceProfile` (`schema/stage_b.py`);
what its classes call or inherit by hand is here, and this module never imports it:

- the `ci:validator` hooks: a statement kind is a core `StatementKind` member or a pack-scoped
  `<prefix>:<name>` (a bare name that is no core member, such as `Proof`, is refused); a
  synthesized predicate is prefixed and, when `core:`, a core predicate; the profile root is a
  relative path; each keyed collection names an entry once; the math delimiters are declared; and
  every CSS selector compiles with `cssselect2.compile_selector_list`;
- the `ci:mixin` method classes: how a details block's kind and synthesis rule are chosen, the
  math delimiter pairs, and the profile's selectors, statement kinds, predicates and resolved form.

`ingest/profile.py` loads, checks and compiles profiles and re-exports the classes.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

import cssselect2
from pydantic import JsonValue

from corpus_structure.core._model import names
from corpus_structure.core.vocab import StatementKind

if TYPE_CHECKING:
    from corpus_structure.ingest._shapes import SynthesisRule

_PACK_NAME = re.compile(r"^([a-z][a-z0-9_]*):([a-z][a-z0-9_]*)$")
_PREDICATE = re.compile(r"^([a-z][a-z0-9_]*):([A-Za-z_][A-Za-z0-9_]*)$")
_ENVIRONMENT = re.compile(r"^[A-Za-z]+\*?$")
CORE_PREDICATES: frozenset[str] = frozenset(names.PREDICATES)


# --- Validator hooks (`ci:validator`) ----------------------------------------------------------


def statement_kind(value: object) -> object:
    """A statement kind: a core member, or a pack-scoped `<prefix>:<name>` the schema version
    declares (`check_profile`); `core:<name>` is the core member."""
    if isinstance(value, StatementKind) or not isinstance(value, str):
        return value
    pack = _PACK_NAME.match(value)
    if pack is not None:
        if pack.group(1) == names.PREFIX:
            return _core_kind(pack.group(2))
        return value  # pack-scoped: checked against the run's schema version (check_profile)
    return _core_kind(value)


def _core_kind(value: str) -> StatementKind:
    try:
        return StatementKind(value)
    except ValueError:
        members = ", ".join(kind.value for kind in StatementKind)
        raise ValueError(
            f"{value!r} is not a core statement kind ({members}); a pack-scoped kind is "
            "written <prefix>:<name>"
        ) from None


def predicate(value: object) -> object:
    """A prefixed predicate; a `core:` one is a core predicate."""
    if not isinstance(value, str):
        return value
    match = _PREDICATE.match(value)
    if match is None:
        raise ValueError(f"{value!r} is not a prefixed predicate (<prefix>:<name>)")
    if match.group(1) == names.PREFIX and match.group(2) not in CORE_PREDICATES:
        raise ValueError(
            f"{value!r} is not a core predicate ({', '.join(sorted(CORE_PREDICATES))})"
        )
    return value


def relative_root(root: str) -> str:
    """The profile root is a path under the corpus root, kept without a trailing slash."""
    if root.startswith("/") or ".." in root.split("/"):
        raise ValueError(f"root {root!r} must be a path under the corpus root")
    return root.rstrip("/")


def one_entry_per_key(details: Any) -> None:
    """A details block's synthesis rules name a statement kind once, its summaries a text once."""
    kinds = [str(rule.statement_kind) for rule in details.synthesize]
    if len(kinds) != len(set(kinds)):
        raise ValueError(f"synthesize names a statement kind twice: {kinds}")
    summaries = [entry.summary for entry in details.by_summary]
    if len(summaries) != len(set(summaries)):
        raise ValueError(f"by_summary names a summary twice: {summaries}")


def delimiters(spec: Any) -> None:
    """At least one math delimiter pair, none empty; display environments are names."""
    pairs = [pair for pair in (spec.inline, spec.display) if pair is not None]
    if not pairs:
        raise ValueError("math declares no delimiter pair")
    if any(not delimiter for pair in pairs for delimiter in pair):
        raise ValueError("a math delimiter is empty")
    for name in spec.display_environments:
        if not _ENVIRONMENT.match(name):
            raise ValueError(f"{name!r} is not an environment name")


def consistent(profile: Any) -> None:
    """`applies_to` lies under `root`, each keyed list names an entry once, and every selector
    compiles."""
    if not profile.applies_to.startswith(profile.root + "/"):
        raise ValueError(
            f"applies_to {profile.applies_to!r} must lie under root {profile.root!r}"
        )
    for field, values in (
        ("exclude", [r.name for r in profile.exclude]),
        ("render.list_markers", [r.selector for r in profile.render.list_markers]),
        ("block_hints", [h.selector for h in profile.block_hints]),
        ("section_hints", [h.title for h in profile.section_hints]),
        ("sections", list(profile.sections)),
    ):
        if len(values) != len(set(values)):
            raise ValueError(f"{field} names an entry twice")
    for field, selector in profile.selectors():
        try:
            cssselect2.compile_selector_list(selector)
        except cssselect2.SelectorError as error:
            raise ValueError(f"{field}: selector {selector!r} does not compile: {error}") from None


# --- Method classes (`ci:mixin`) ---------------------------------------------------------------


class DetailsKindsMethods:
    """How a details block becomes a statement."""

    def kind_of(self, summary: str | None, in_example_or_exercise: bool) -> StatementKind | str:
        """A details block's statement kind: by its summary text, then by context, then default."""
        d: Any = self
        by_summary = {entry.summary: entry.statement_kind for entry in d.by_summary}
        if summary is not None and summary in by_summary:
            return by_summary[summary]
        if in_example_or_exercise and d.inside_example_or_exercise is not None:
            return d.inside_example_or_exercise
        return d.default

    def rule_for(self, kind: StatementKind | str) -> SynthesisRule | None:
        d: Any = self
        return next((r for r in d.synthesize if str(r.statement_kind) == str(kind)), None)


class MathSpecMethods:
    """The math delimiters."""

    @property
    def pairs(self) -> dict[str, str]:
        """Opener to closer, inline first."""
        m: Any = self
        return dict(pair for pair in (m.inline, m.display) if pair is not None)


class SourceProfileMethods:
    """A profile's selectors, statement kinds, predicates and resolved form."""

    def selectors(self) -> Iterator[tuple[str, str]]:
        """Every CSS selector of the profile, with the field that holds it."""
        p: Any = self
        for rule in p.exclude:
            yield f"exclude.{rule.name}", rule.selector
        yield "title", p.title
        for rank, selector in enumerate(p.sections):
            yield f"sections[{rank}]", selector
        if p.unit is not None:
            yield "unit", p.unit
        for hint in p.block_hints:
            yield "block_hints", hint.selector
        if p.references is not None:
            yield "references.selector", p.references.selector
        for marker in p.render.list_markers:
            yield "render.list_markers", marker.selector
        if p.math.page_macros is not None:
            yield "math.page_macros", p.math.page_macros
        for selector in p.layout:
            yield "layout", selector
        for selector in p.verbatim:
            yield "verbatim", selector

    def statement_kinds(self) -> Iterator[tuple[str, StatementKind | str]]:
        """Every statement kind the profile names, with its field."""
        p: Any = self
        for hint in p.block_hints:
            yield f"block_hints[{hint.selector}].statement_kind", hint.statement_kind
        for section in p.section_hints:
            yield f"section_hints[{section.title}]", section.statement_kind
        details = p.details_kinds
        yield "details_kinds.default", details.default
        if details.inside_example_or_exercise is not None:
            yield "details_kinds.inside_example_or_exercise", details.inside_example_or_exercise
        for entry in details.by_summary:
            yield f"details_kinds.by_summary[{entry.summary}]", entry.statement_kind
        for rule in details.synthesize:
            yield f"details_kinds.synthesize[{rule.statement_kind}]", rule.statement_kind

    def predicates(self) -> Iterator[tuple[str, str]]:
        p: Any = self
        for rule in p.details_kinds.synthesize:
            yield f"details_kinds.synthesize[{rule.statement_kind}].predicate", rule.predicate

    def resolved(self) -> dict[str, JsonValue]:
        """The resolved profile, defaults included: what enters `ingest.html`'s configuration hash
        (D4 M01)."""
        p: Any = self
        return p.model_dump(mode="json")
