"""Source profiles: the loader, the compiled role matcher and the schema-version check
(ingest and math §3.2; D4 M01 "Configuration" and "Profile vocabulary"; D2 §12.1; ADR-0022).

A profile is `sources/<name>.yaml`: one source's HTML conventions and its place in the corpus. It
loads into `SourceProfile`, a frozen Pydantic model generated from the `SourceProfile` class of
`model/system.yaml` with its nested classes (`CorpusIndex`, `ExcludeRule`, `BlockHint`,
`SectionHint`, `DetailsKinds`, `SummaryKind`, `SynthesisRule`, `MathSpec`, `ReferenceSpec`,
`RenderSpec`, `ListMarkerRule`; `ingest/_shapes.py`, Stage B, P0-M-5), re-exported here; their
validators and methods are hand-written in `ingest/profile_support.py`. Unknown keys are refused
(`extra="forbid"`), so a profile never silently loses a convention. The D4 vocabulary keys M01 does
not implement yet load (`encoding` other than `sniff`, `section_source: layout`, `layout`,
`verbatim`, `img_alt: true`), and are then refused with the code `not_implemented`:
`unimplemented(profile)` lists them, `compile_profile` refuses such a profile and `check_profile`
reports them.

The class's keyed lists are written in YAML as mappings keyed by their identifier, as LinkML
inlines them (`exclude: {scripts: "script, noscript"}`, `block_hints: {"p.dfn": {…}}`,
`by_summary: {Answer: solution}`, `list_markers: {"ol.sub": parenthesized}`).

Domain-bearing fields are typed by the generated vocabularies, never left as strings:

- statement kinds (`block_hints`, `section_hints`, `details_kinds`) are `StatementKind` members,
  or a pack-scoped kind written `<prefix>:<name>`; a bare name that is no core member (`Proof` for
  `proof`) is refused at load;
- `synthesize.predicate` is a prefixed predicate; a `core:` one must be a core predicate;
- `orphan_text` is a `SegmentKind`, `object` and `evidence` are `SynthesisObject` and
  `SynthesisEvidence` members, and the rendering and section-source choices are the generated
  `ReferenceRender`, `QuoteRender`, `ListMarkerStyle`, `SummaryRender`, `FigureRender` and
  `SectionSource` members.

Every CSS selector compiles at load with `cssselect2.compile_selector_list`
(`profile_support.consistent`); one that does not rejects the profile. `compile_profile` registers
the rules once, as role payloads in one `cssselect2.Matcher`, the only role engine M01 runs.

`check_profile(profile, schema_version)` lists the profile's version-scoped names (its statement
kinds, pack-scoped ones included, and its predicates) that the schema version lacks, and its
unimplemented keys, each with a code, its field and the name. It is pure; orchestration refuses a
run on any result (P0-O-1; DA-010).
"""

from __future__ import annotations

import re
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, NamedTuple, Protocol

import cssselect2
import yaml
from pydantic import ValidationError

from corpus_structure.core.vocab import FigureRender, SectionSource, SummaryRender
from corpus_structure.ingest._shapes import (
    BlockHint,
    CorpusIndex,
    DetailsKinds,
    ExcludeRule,
    ListMarkerRule,
    MathSpec,
    ReferenceSpec,
    RenderSpec,
    SectionHint,
    SourceProfile,
    SummaryKind,
    SynthesisRule,
)
from corpus_structure.ingest.profile_support import CORE_PREDICATES

__all__ = [
    "CORE_PREDICATES", "DEFAULT_EXCLUDE", "DEFAULT_SECTIONS", "EXCLUSIVE_ROLES", "SNIFF",
    "SOURCES_DIR", "BlockHint", "CompiledProfile", "CorpusIndex", "DetailsKinds", "ExcludeRule",
    "ListMarkerRule", "MathSpec", "ProfileError", "ProfileIssue", "ReferenceSpec", "RenderSpec",
    "Rule", "SchemaVocabulary", "SectionHint", "SourceProfile", "SummaryKind", "SynthesisRule",
    "check_profile", "compile_profile", "load_profile", "parse_profile", "profile_rules",
    "unimplemented",
]  # fmt: skip

# python/corpus-structure/src/corpus_structure/ingest/profile.py -> the repository root (D9 §1).
REPO = Path(__file__).resolve().parents[5]
SOURCES_DIR = REPO / "sources"

_PROFILE_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")

# The model's defaults (`SourceProfile`'s `ifabsent` and `ci:py_default`).
_FIELDS = SourceProfile.model_fields
DEFAULT_EXCLUDE: tuple[ExcludeRule, ...] = _FIELDS["exclude"].default
SNIFF: str = _FIELDS["encoding"].default
DEFAULT_SECTIONS: tuple[str, ...] = _FIELDS["sections"].default


ErrorCode = Literal["invalid", "not_implemented"]


class ProfileError(ValueError):
    """A refused profile: `invalid` (unreadable, unknown keys, unknown core names, bad selectors)
    or `not_implemented` (a vocabulary key M01 does not implement yet)."""

    def __init__(self, name: str, reason: str, code: ErrorCode = "invalid") -> None:
        super().__init__(f"source profile {name!r} is refused ({code}): {reason}")
        self.name = name
        self.reason = reason
        self.code: ErrorCode = code


# --- Loading -----------------------------------------------------------------------------------


def parse_profile(name: str, data: Any, *, prepared: Any = None) -> SourceProfile:
    """Validate parsed YAML as a profile; any failure is a `ProfileError` naming the profile."""
    try:
        context=release_vocabulary(prepared) if prepared is not None else None
        profile=SourceProfile.model_validate(data,context=context)
        if context is not None:
            kinds=set(context['statement_kinds'])
            problems=[field for field,kind in profile.statement_kinds() if str(kind) not in kinds]
            problems += [field for field,predicate in profile.predicates() if predicate not in context['predicates']]
            problems += [issue.field for issue in unimplemented(profile)]
            if problems:raise ProfileError(name,'unsupported or undeclared bound fields: '+', '.join(problems))
        return profile
    except ValidationError as error:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in e['loc']) or '<profile>'}: {e['msg']}"
            for e in error.errors()
        )
        raise ProfileError(name, problems) from None


def load_profile(name: str, directory: Path = SOURCES_DIR, *, prepared: Any = None) -> SourceProfile:
    """`sources/<name>.yaml`, validated against the source-profile class."""
    if not _PROFILE_NAME.match(name):
        raise ProfileError(name, "a profile name is lower-case letters, digits, '-' and '_'")
    path = directory / f"{name}.yaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ProfileError(name, f"{path} cannot be read: {error}") from None
    return parse_profile(name, data,prepared=prepared)


# --- The schema-version check -----------------------------------------------------------------


class SchemaVocabulary(Protocol):
    """What the check reads of a compiled schema version (P0-S-1): its statement-kind members,
    core and pack-scoped (pack members as `<prefix>:<name>`), and its prefixed predicates."""

    @property
    def statement_kinds(self) -> Collection[str]: ...

    @property
    def predicates(self) -> Collection[str]: ...


IssueCode = Literal["unknown_statement_kind", "unknown_predicate", "not_implemented"]


class ProfileIssue(NamedTuple):
    code: IssueCode
    field: str
    name: str


def unimplemented(profile: SourceProfile) -> tuple[ProfileIssue, ...]:
    """The vocabulary keys the profile sets to something M01 does not implement yet (D4 M01)."""
    issues = []
    if profile.encoding != SNIFF:
        issues.append(ProfileIssue("not_implemented", "encoding", profile.encoding))
    if profile.section_source is not SectionSource.BODY:
        issues.append(ProfileIssue("not_implemented", "section_source", profile.section_source))
    issues += [ProfileIssue("not_implemented", "layout", s) for s in profile.layout]
    issues += [ProfileIssue("not_implemented", "verbatim", s) for s in profile.verbatim]
    if profile.img_alt:
        issues.append(ProfileIssue("not_implemented", "img_alt", "true"))
    return tuple(issues)


def check_profile(
    profile: SourceProfile, schema_version: SchemaVocabulary
) -> tuple[ProfileIssue, ...]:
    """The profile's names that the schema version lacks, and its unimplemented keys; empty when
    the run may start."""
    kinds = set(schema_version.statement_kinds)
    predicates = set(schema_version.predicates)
    issues = [
        ProfileIssue("unknown_statement_kind", field, str(kind))
        for field, kind in profile.statement_kinds()
        if str(kind) not in kinds
    ]
    issues += [
        ProfileIssue("unknown_predicate", field, name)
        for field, name in profile.predicates()
        if name not in predicates
    ]
    return (*issues, *unimplemented(profile))


# --- The compiled matcher ----------------------------------------------------------------------

Role = Literal[
    "exclude", "title", "section", "unit", "block_hint", "reference", "list_marker", "macros"
]
EXCLUSIVE_ROLES: frozenset[Role] = frozenset({"exclude", "unit", "title"})


@dataclass(frozen=True, slots=True)
class Rule:
    """One role payload: the role, a name (the exclusion rule, the selector) and its data."""

    role: Role
    name: str
    data: Any = None


@dataclass(frozen=True, slots=True)
class CompiledProfile:
    """A profile with its rules registered once in one `cssselect2.Matcher`."""

    profile: SourceProfile
    rules: tuple[tuple[str, Rule], ...]
    matcher: cssselect2.Matcher

    def match(self, wrapper: cssselect2.ElementWrapper) -> list[Rule]:
        """The element's rules, lowest precedence first (specificity, then profile order)."""
        return [payload for *_, payload in self.matcher.match(wrapper)]


def profile_rules(profile: SourceProfile) -> list[tuple[str, Rule]]:
    """(selector, rule) for every role of the profile, in profile order."""
    rules: list[tuple[str, Rule]] = [
        (rule.selector, Rule("exclude", rule.name)) for rule in profile.exclude
    ]
    if profile.render.summary is SummaryRender.DROP:
        rules.append(("details > summary", Rule("exclude", "summaries")))
    if profile.render.figure is FigureRender.DROP:
        rules.append(("figure", Rule("exclude", "figures")))
    rules.append((profile.title, Rule("title", "title")))
    rules += [(s, Rule("section", s, rank)) for rank, s in enumerate(profile.sections)]
    if profile.unit is not None:
        rules.append((profile.unit, Rule("unit", "unit")))
    rules += [
        (hint.selector, Rule("block_hint", hint.selector, hint)) for hint in profile.block_hints
    ]
    if profile.references is not None:
        refs = profile.references
        rules.append((refs.selector, Rule("reference", refs.selector, refs.render)))
    rules += [
        (m.selector, Rule("list_marker", m.selector, m.style)) for m in profile.render.list_markers
    ]
    if profile.math.page_macros is not None:
        rules.append((profile.math.page_macros, Rule("macros", "page_macros")))
    return rules


def compile_profile(profile: SourceProfile, name: str = "<profile>") -> CompiledProfile:
    """The profile's rules in one Matcher; a profile with unimplemented keys is refused."""
    missing = unimplemented(profile)
    if missing:
        reason = "; ".join(f"{issue.field}: {issue.name!r}" for issue in missing)
        raise ProfileError(name, f"not implemented by M01: {reason}", code="not_implemented")
    rules = tuple(profile_rules(profile))
    matcher = cssselect2.Matcher()
    for selector, rule in rules:
        for compiled in cssselect2.compile_selector_list(selector):
            matcher.add_selector(compiled, rule)
    return CompiledProfile(profile, rules, matcher)


def release_vocabulary(prepared: Any) -> dict[str, frozenset[str]]:
    """One release owns profile name membership; installed enum classes are representations."""
    import json
    try:kinds=prepared.enum_members('StatementKind')
    except StopIteration:kinds=frozenset()
    iris={p.iri for definition in prepared.definitions for p in definition.properties}
    predicates=set(iris)
    for row in prepared.registry_rows:
        if row.kind=='prefix':
            prefix=json.loads(row.body)['uri']
            predicates.update(row.name+':'+iri[len(prefix):] for iri in iris if iri.startswith(prefix))
    return {'statement_kinds':kinds,'predicates':frozenset(predicates)}
