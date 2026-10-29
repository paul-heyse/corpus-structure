"""Source profiles: the loader, the compiled role matcher and the schema-version check
(ingest and math §3.2; D4 M01 "Configuration" and "Profile vocabulary"; D2 §12.1; ADR-0022).

A profile is `sources/<name>.yaml`: one source's HTML conventions and its place in the corpus. It
loads into `SourceProfile`, a frozen Pydantic model whose fields are those of the `SourceProfile`
class in `model/system.yaml`, field for field (`BlockHint`, `SectionHint`, `CorpusIndex`,
`DetailsKinds` and `SynthesisRule` likewise); the model's interim mirror guard keeps the two equal
until a generated form exists (P0-M-1). Unknown keys are refused (`extra="forbid"`), so a profile
never silently loses a convention: the D4 vocabulary keys the class does not declare yet
(`encoding`, `section_source`, `layout`, `verbatim`, `img_alt`) are refused at load until the class
declares them.

Domain-bearing fields are typed by the generated vocabularies, never left as strings:

- statement kinds (`block_hints`, `section_hints`, `details_kinds`) are `StatementKind` members,
  or a pack-scoped kind written `<prefix>:<name>`; a bare name that is no core member (`Proof` for
  `proof`) is refused at load;
- `synthesize.predicate` is a prefixed predicate; a `core:` one must be a core predicate;
- `orphan_text` is a `SegmentKind`, `object` and `evidence` are `SynthesisObject` and
  `SynthesisEvidence` members.

Every CSS selector compiles at load with `cssselect2.compile_selector_list`; one that does not
rejects the profile. `compile_profile` registers the rules once, as role payloads in one
`cssselect2.Matcher`, the only role engine M01 runs.

`check_profile(profile, schema_version)` lists the profile's version-scoped names (its statement
kinds, pack-scoped ones included, and its predicates) that the schema version lacks, each with a
code, its field and the name. It is pure; orchestration refuses a run on any result (P0-O-1;
DA-010).
"""

from __future__ import annotations

import re
from collections.abc import Collection, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal, NamedTuple, Protocol, Self

import cssselect2
import yaml
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    JsonValue,
    ValidationError,
    field_validator,
    model_validator,
)

from corpus_structure.core._model import names
from corpus_structure.core.vocab import (
    SegmentKind,
    StatementKind,
    SynthesisEvidence,
    SynthesisObject,
)

# python/corpus-structure/src/corpus_structure/ingest/profile.py -> the repository root (D9 §1).
REPO = Path(__file__).resolve().parents[5]
SOURCES_DIR = REPO / "sources"

_PROFILE_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")
_PACK_NAME = re.compile(r"^([a-z][a-z0-9_]*):([a-z][a-z0-9_]*)$")
_PREDICATE = re.compile(r"^([a-z][a-z0-9_]*):([A-Za-z_][A-Za-z0-9_]*)$")
_ENVIRONMENT = re.compile(r"^[A-Za-z]+\*?$")
CORE_PREDICATES: frozenset[str] = frozenset(names.PREDICATES)


class ProfileError(ValueError):
    """A profile that does not load: unreadable, unknown keys, unknown core names, bad selectors."""

    def __init__(self, name: str, reason: str) -> None:
        super().__init__(f"source profile {name!r} is refused: {reason}")
        self.name = name
        self.reason = reason


# --- Core-typed names -------------------------------------------------------------------------


def _statement_kind(value: object) -> object:
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


def _predicate(value: object) -> object:
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


# A statement kind: a core member, or a pack-scoped `<prefix>:<name>` the schema version declares.
StatementKindName = Annotated[StatementKind | str, BeforeValidator(_statement_kind)]
PredicateName = Annotated[str, BeforeValidator(_predicate)]
Selector = Annotated[str, Field(min_length=1)]


def _keyed(value: object, key: str, single: str | None = None) -> object:
    """The YAML form `{<key>: {…}}` (or `{<key>: <single>}`) as a list of objects with `key`."""
    if not isinstance(value, Mapping):
        return value
    out = []
    for name, body in value.items():
        if single is not None and not isinstance(body, Mapping):
            body = {single: body}
        if not isinstance(body, Mapping):
            raise ValueError(f"{name!r}: expected a mapping, got {body!r}")
        out.append({key: name, **body})
    return out


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# --- The system classes ------------------------------------------------------------------------


class CorpusIndex(_Frozen):
    """The corpus index of a source profile."""

    file: str = Field(min_length=1)
    page: str = Field(min_length=1)
    first_pass: str | None = None


class BlockHint(_Frozen):
    """A statement-kind hint for blocks of one selector."""

    selector: Selector
    statement_kind: StatementKindName
    claim_bearing: bool | None = None


class SectionHint(_Frozen):
    """The statement kind of units under a section title."""

    title: str = Field(min_length=1)
    statement_kind: StatementKindName


class SynthesisRule(_Frozen):
    """The claim a block's containment states (D5 §3.5)."""

    statement_kind: StatementKindName
    predicate: PredicateName
    object: SynthesisObject
    evidence: SynthesisEvidence


class DetailsKinds(_Frozen):
    """How details blocks become statements, and the claims their containment states."""

    default: StatementKindName
    inside_example_or_exercise: StatementKindName | None = None
    by_summary: dict[str, StatementKindName] = Field(default_factory=dict)
    synthesize: tuple[SynthesisRule, ...] = ()

    @field_validator("synthesize", mode="before")
    @classmethod
    def _synthesize_by_kind(cls, value: object) -> object:
        return _keyed(value, "statement_kind")

    @model_validator(mode="after")
    def _one_rule_per_kind(self) -> Self:
        kinds = [str(rule.statement_kind) for rule in self.synthesize]
        if len(kinds) != len(set(kinds)):
            raise ValueError(f"synthesize names a statement kind twice: {kinds}")
        return self

    def kind_of(self, summary: str | None, in_example_or_exercise: bool) -> StatementKind | str:
        """A details block's statement kind: by its summary text, then by context, then default."""
        if summary is not None and summary in self.by_summary:
            return self.by_summary[summary]
        if in_example_or_exercise and self.inside_example_or_exercise is not None:
            return self.inside_example_or_exercise
        return self.default

    def rule_for(self, kind: StatementKind | str) -> SynthesisRule | None:
        return next((r for r in self.synthesize if str(r.statement_kind) == str(kind)), None)


# The JSON-ranged slots of the class (`exclude`, `math`, `references`, `render`) are typed here by
# what D4 M01's profile vocabulary allows; the class leaves them as `Json`.


class MathSpec(_Frozen):
    """Math delimiters, bare display environments and the page macro source (D4 M01 `math`)."""

    inline: tuple[str, str] | None = ("\\(", "\\)")
    display: tuple[str, str] | None = ("\\[", "\\]")
    display_environments: tuple[str, ...] = ()
    page_macros: Selector | None = None

    @model_validator(mode="after")
    def _delimiters(self) -> Self:
        pairs = [pair for pair in (self.inline, self.display) if pair is not None]
        if not pairs:
            raise ValueError("math declares no delimiter pair")
        if any(not delimiter for pair in pairs for delimiter in pair):
            raise ValueError("a math delimiter is empty")
        for name in self.display_environments:
            if not _ENVIRONMENT.match(name):
                raise ValueError(f"{name!r} is not an environment name")
        return self

    @property
    def pairs(self) -> dict[str, str]:
        """Opener to closer, inline first."""
        return dict(pair for pair in (self.inline, self.display) if pair is not None)


class ReferenceSpec(_Frozen):
    """In-text reference links and their rendering (D1 §3.1; D4 M01 `references`)."""

    selector: Selector
    render: Literal["browser", "placeholder", "empty"] = "browser"


ListMarkerStyle = Literal["parenthesized", "browser", "none"]


class RenderSpec(_Frozen):
    """Rendering conventions for script- or style-produced text (D4 M01 `render`)."""

    q: Literal["quotes", "bare"] = "bare"
    list_markers: dict[Selector, ListMarkerStyle] = Field(default_factory=dict)
    summary: Literal["heading", "drop"] = "heading"
    figure: Literal["caption", "drop"] = "caption"


DEFAULT_EXCLUDE: dict[str, str] = {"scripts": "script, noscript"}
DEFAULT_SECTIONS: tuple[str, ...] = ("h1", "h2", "h3", "h4", "h5", "h6")


class SourceProfile(_Frozen):
    """A source's HTML conventions and its place in the corpus (`model/system.yaml`
    `SourceProfile`; D2 §12.1, D4 M01)."""

    version: str = Field(min_length=1)
    root: str = Field(min_length=1)
    index: CorpusIndex | None = None
    language: str = "english"
    applies_to: str = Field(min_length=1)
    exclude: dict[str, Selector] = Field(default_factory=lambda: dict(DEFAULT_EXCLUDE))
    title: Selector = "h1"
    sections: tuple[Selector, ...] = DEFAULT_SECTIONS
    unit: Selector | None = None
    block_hints: tuple[BlockHint, ...] = ()
    section_hints: tuple[SectionHint, ...] = ()
    details_kinds: DetailsKinds = DetailsKinds(default=StatementKind.PROOF)
    math: MathSpec = MathSpec()
    references: ReferenceSpec | None = None
    render: RenderSpec = RenderSpec()
    orphan_text: SegmentKind = SegmentKind.PARAGRAPH

    @field_validator("block_hints", mode="before")
    @classmethod
    def _hints_by_selector(cls, value: object) -> object:
        return _keyed(value, "selector")

    @field_validator("section_hints", mode="before")
    @classmethod
    def _hints_by_title(cls, value: object) -> object:
        return _keyed(value, "title", single="statement_kind")

    @field_validator("root")
    @classmethod
    def _relative_root(cls, root: str) -> str:
        if root.startswith("/") or ".." in root.split("/"):
            raise ValueError(f"root {root!r} must be a path under the corpus root")
        return root.rstrip("/")

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if not self.applies_to.startswith(self.root + "/"):
            raise ValueError(f"applies_to {self.applies_to!r} must lie under root {self.root!r}")
        for field, values in (
            ("block_hints", [h.selector for h in self.block_hints]),
            ("section_hints", [h.title for h in self.section_hints]),
            ("sections", list(self.sections)),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"{field} names an entry twice")
        for field, selector in self.selectors():
            try:
                cssselect2.compile_selector_list(selector)
            except cssselect2.SelectorError as error:
                raise ValueError(
                    f"{field}: selector {selector!r} does not compile: {error}"
                ) from None
        return self

    def selectors(self) -> Iterator[tuple[str, str]]:
        """Every CSS selector of the profile, with the field that holds it."""
        for name, selector in self.exclude.items():
            yield f"exclude.{name}", selector
        yield "title", self.title
        for rank, selector in enumerate(self.sections):
            yield f"sections[{rank}]", selector
        if self.unit is not None:
            yield "unit", self.unit
        for hint in self.block_hints:
            yield "block_hints", hint.selector
        if self.references is not None:
            yield "references.selector", self.references.selector
        for selector in self.render.list_markers:
            yield "render.list_markers", selector
        if self.math.page_macros is not None:
            yield "math.page_macros", self.math.page_macros

    def statement_kinds(self) -> Iterator[tuple[str, StatementKind | str]]:
        """Every statement kind the profile names, with its field."""
        for hint in self.block_hints:
            yield f"block_hints[{hint.selector}].statement_kind", hint.statement_kind
        for section in self.section_hints:
            yield f"section_hints[{section.title}]", section.statement_kind
        details = self.details_kinds
        yield "details_kinds.default", details.default
        if details.inside_example_or_exercise is not None:
            yield "details_kinds.inside_example_or_exercise", details.inside_example_or_exercise
        for summary, kind in details.by_summary.items():
            yield f"details_kinds.by_summary[{summary}]", kind
        for rule in details.synthesize:
            yield f"details_kinds.synthesize[{rule.statement_kind}]", rule.statement_kind

    def predicates(self) -> Iterator[tuple[str, str]]:
        for rule in self.details_kinds.synthesize:
            yield f"details_kinds.synthesize[{rule.statement_kind}].predicate", rule.predicate

    def resolved(self) -> dict[str, JsonValue]:
        """The resolved profile, defaults included: what enters `ingest.html`'s configuration hash
        (D4 M01)."""
        return self.model_dump(mode="json")


# --- Loading -----------------------------------------------------------------------------------


def parse_profile(name: str, data: Any) -> SourceProfile:
    """Validate parsed YAML as a profile; any failure is a `ProfileError` naming the profile."""
    try:
        return SourceProfile.model_validate(data)
    except ValidationError as error:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in e['loc']) or '<profile>'}: {e['msg']}"
            for e in error.errors()
        )
        raise ProfileError(name, problems) from None


def load_profile(name: str, directory: Path = SOURCES_DIR) -> SourceProfile:
    """`sources/<name>.yaml`, validated against the source-profile class."""
    if not _PROFILE_NAME.match(name):
        raise ProfileError(name, "a profile name is lower-case letters, digits, '-' and '_'")
    path = directory / f"{name}.yaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ProfileError(name, f"{path} cannot be read: {error}") from None
    return parse_profile(name, data)


# --- The schema-version check -----------------------------------------------------------------


class SchemaVocabulary(Protocol):
    """What the check reads of a compiled schema version (P0-S-1): its statement-kind members,
    core and pack-scoped (pack members as `<prefix>:<name>`), and its prefixed predicates."""

    @property
    def statement_kinds(self) -> Collection[str]: ...

    @property
    def predicates(self) -> Collection[str]: ...


IssueCode = Literal["unknown_statement_kind", "unknown_predicate"]


class ProfileIssue(NamedTuple):
    code: IssueCode
    field: str
    name: str


def check_profile(
    profile: SourceProfile, schema_version: SchemaVocabulary
) -> tuple[ProfileIssue, ...]:
    """The profile's names that the schema version lacks; empty when the run may start."""
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
    return tuple(issues)


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
        (selector, Rule("exclude", name)) for name, selector in profile.exclude.items()
    ]
    if profile.render.summary == "drop":
        rules.append(("details > summary", Rule("exclude", "summaries")))
    if profile.render.figure == "drop":
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
        (s, Rule("list_marker", s, style)) for s, style in profile.render.list_markers.items()
    ]
    if profile.math.page_macros is not None:
        rules.append((profile.math.page_macros, Rule("macros", "page_macros")))
    return rules


def compile_profile(profile: SourceProfile) -> CompiledProfile:
    rules = tuple(profile_rules(profile))
    matcher = cssselect2.Matcher()
    for selector, rule in rules:
        for compiled in cssselect2.compile_selector_list(selector):
            matcher.add_selector(compiled, rule)
    return CompiledProfile(profile, rules, matcher)
