"""Rich agent proposal boundaries compiled from a named semantic release.

Authored proposals are source reports. Locating their evidence never selects their claims or
activates definitions. Semantic admission and scientific selection retain their existing owners.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from corpus_structure.core.evidence import MacroDef, RenditionContent
from corpus_structure.core.locators import LocatorIndex
from corpus_structure.methods.llm.cascade import Cascade, FrameSentence, Step
from corpus_structure.methods.llm.packet import SentenceEntry
from corpus_structure.methods.llm.parts import PAGE_CHARS, Part, text_hash

from .prepare import preview_schema
from .publication import native_constraints
from .types import PreparedRelease, ResolvedDependencies, SourceArtifact, SourceBundle

_MODEL = Path(__file__).resolve().parents[1] / "model" / "semantic" / "agent.yaml"
_EMPTY_DEPENDENCIES = ResolvedDependencies()
SEMANTIC_AGENT_VERSION = "semantic-1"


def proposal_inputs(
    bundle: SourceBundle,
    dependencies: ResolvedDependencies = _EMPTY_DEPENDENCIES,
    *,
    qualification_class: str = "Qualification",
    statement_class: str = "SourceStatement",
) -> SourceBundle:
    """Archive model-facing boundaries with the exact candidate vocabulary."""
    from .observations import observation_inputs

    bundle = observation_inputs(bundle)
    if {source.name for source in bundle.sources} & {"agent", "agent-root"}:
        raise ValueError("reserved agent module name already supplied")
    candidate = preview_schema(bundle, dependencies)
    module = yaml.safe_load(_MODEL.read_bytes())
    qualification = next((d for d in candidate.classes if d.name == qualification_class), None)
    if qualification is None or not (
        qualification.name == "Qualification" or "Qualification" in qualification.ancestors
    ):
        raise ValueError("agent operation needs an explicit Qualification class or subclass")
    module["classes"]["AgentClaim"]["attributes"]["qualification"]["range"] = qualification_class
    entities = [
        d
        for d in candidate.classes
        if not d.abstract and (d.name == "Entity" or "Entity" in d.ancestors)
    ]
    if not entities:
        raise ValueError("agent proposals require a declared Entity hierarchy")
    predicates = {p.iri for definition in entities for p in definition.properties if p.name != "id"}
    if not predicates:
        raise ValueError("agent proposals require at least one declared entity property")
    statement = next((d for d in candidate.classes if d.name == statement_class), None)
    if statement is None or not (
        statement.name == "SourceStatement" or "SourceStatement" in statement.ancestors
    ):
        raise ValueError("agent operation needs an explicit SourceStatement class or subclass")
    kind_property = next((p for p in statement.properties if p.name == "statement_kind"), None)
    if kind_property is None:
        raise ValueError("agent statement binding requires a statement_kind property")
    statement_enum = kind_property.range
    module["classes"]["AgentStatementBinding"]["attributes"]["statement"]["range"] = statement_class
    module["enums"]["AgentStatementKind"]["permissible_values"] = {
        **{name: {} for name in sorted(candidate.enum_members(statement_enum))},
        "outside": {"description": "An explicitly unresolved external statement reference."},
    }
    module["enums"]["AgentClassIRI"]["permissible_values"] = {d.iri: {} for d in entities}
    module["enums"]["AgentPropertyIRI"]["permissible_values"] = {
        iri: {} for iri in sorted(predicates)
    }
    return SourceBundle(
        "agent-root",
        (
            *bundle.sources,
            SourceArtifact("agent", yaml.safe_dump(module, sort_keys=True).encode()),
            SourceArtifact(
                "agent-root",
                yaml.safe_dump(
                    {
                        "id": "https://corpus-structure.dev/semantic/agent-root",
                        "name": "semantic_agent_root",
                        "imports": [bundle.root, "agent"],
                    }
                ).encode(),
            ),
        ),
    )


@dataclass(frozen=True)
class ProposalSentence:
    id: str
    locator: str
    start: int
    end: int


@dataclass(frozen=True)
class ProposalFrame:
    unit_ref: str
    text: str
    sentences: tuple[ProposalSentence, ...]

    def __post_init__(self) -> None:
        if not self.unit_ref or len({sentence.id for sentence in self.sentences}) != len(
            self.sentences
        ):
            raise ValueError("proposal frame needs a unit and unique sentence identities")
        if any(
            not sentence.locator or not 0 <= sentence.start < sentence.end <= len(self.text)
            for sentence in self.sentences
        ):
            raise ValueError("proposal sentence lies outside canonical source text")


def source_frame(
    unit_ref: str, content: RenditionContent, page: str, sentences: Sequence[SentenceEntry]
) -> ProposalFrame:
    """Project the served sentence identities from the immutable source rendition."""
    index = LocatorIndex(content, page)
    located = []
    for sentence in sentences:
        segment = index.resolve(sentence.locator)
        if content.canonical_text[segment.start : segment.end] != sentence.text:
            raise ProposalRefused("packet sentence differs from source frame")
        located.append(ProposalSentence(sentence.id, sentence.locator, segment.start, segment.end))
    return ProposalFrame(unit_ref, content.canonical_text, tuple(located))


def statement_anchor(
    anchor: str, frame: ProposalFrame, *, index: LocatorIndex | None = None
) -> str:
    """Resolve a local handle through its frame, never through another packet's namespace.

    A source report may use its declared unit or supplied canonical sentence locators. The
    consolidation boundary can additionally resolve an explicit source locator on the exact
    rendition; unsupported strings never become located statement identities.
    """
    sentences = {sentence.id: sentence.locator for sentence in frame.sentences}
    known = {frame.unit_ref, *sentences.values()}
    if anchor in sentences:
        anchor = sentences[anchor]
    elif anchor not in known and index is None:
        raise ProposalRefused("statement anchor is not declared by the bound source frame")
    if (
        anchor not in known
        and anchor not in sentences
        and anchor[:1] in {"s", "c"}
        and anchor[1:].isdigit()
    ):
        raise ProposalRefused("local statement handle is not declared by the bound source frame")
    if index is not None:
        try:
            return str(index.generate(index.resolve(anchor)))
        except (ValueError, LookupError) as error:
            raise ProposalRefused(
                "statement anchor is not located on its bound rendition"
            ) from error
    return anchor


@dataclass(frozen=True)
class ProposalIssue:
    path: str
    code: str
    detail: str


@dataclass(frozen=True)
class LocatedProposal:
    authored: BaseModel
    stored: BaseModel
    issues: tuple[ProposalIssue, ...]

    @property
    def clean(self) -> bool:
        return not self.issues


class ProposalRefused(ValueError):
    """The batch is not meaningful under its declared source/release context."""


def _property_value(value: Mapping[str, Any], range_name: str) -> Any:
    # Structural Value types retain their full typed records; primitive property boundaries
    # consume the contained primitive, keeping exact Decimal meaning and explicit null separate.
    if range_name in {"string", "uri", "uriorcurie"} and value["kind"] == "text":
        return value["text"]
    if range_name in {"integer", "decimal"} and value["kind"] == "number":
        number = value["number"]
        if (
            range_name == "integer"
            and isinstance(number, Decimal)
            and number == number.to_integral_value()
        ):
            return int(number)
        return number
    if range_name in {"float", "double"} and value["kind"] == "float":
        return value["number"]
    if range_name == "boolean" and value["kind"] == "boolean":
        return value["boolean"]
    if range_name == "date" and value["kind"] == "date":
        return value["date"]
    if range_name == "datetime" and value["kind"] == "instant":
        return value["instant"]
    return dict(value)


def _check_references(
    prepared: PreparedRelease, raw: Mapping[str, Any], known: Mapping[str, tuple[str, ...]]
) -> None:
    sections = (
        "entities",
        "statements",
        "claims",
        "alternatives",
        "unsupported",
        "identity_exclusions",
    )
    identifiers = [item["id"] for section in sections for item in raw.get(section, ())]
    if any(not identifier for identifier in identifiers) or len(identifiers) != len(
        set(identifiers)
    ):
        raise ProposalRefused("proposal local identifiers must be nonempty and unique")
    entities = {item["id"]: item for item in raw.get("entities", ())}
    statements = {item["id"] for item in raw.get("statements", ())}
    claims = {item["id"] for item in raw.get("claims", ())}
    definitions = {definition.iri: definition for definition in prepared.definitions}
    for alternative in raw.get("alternatives", ()):
        if len(alternative["members"]) < 2 or len(set(alternative["members"])) != len(
            alternative["members"]
        ):
            raise ProposalRefused("an alternative needs at least two distinct claim references")
        if set(alternative["members"]) - claims:
            raise ProposalRefused("alternative refers to an undeclared claim")
    exclusions = raw.get("identity_exclusions", ())
    if exclusions and prepared.execution_model_id is None:
        raise ProposalRefused("identity exclusions require the composed semantic-2 profile")
    for exclusion in exclusions:
        if not exclusion["reason"].strip():
            raise ProposalRefused("identity exclusion needs a nonempty reason")
        left, right = exclusion["left"], exclusion["right"]
        if left == right:
            raise ProposalRefused("identity exclusion cannot refer to itself")
        for endpoint in (left, right):
            universe = entities if endpoint["kind"] == "local" else known
            if endpoint["target"] not in universe:
                raise ProposalRefused("identity exclusion endpoint is outside the bound packet")
    from .reference_positions import class_reference_value, reference_position

    constraints = native_constraints(prepared)

    def check_value(value, definition, prop):
        position = reference_position(prepared, definition.name, prop.name)
        if position.kind == "class":
            try:
                target = class_reference_value(prepared, value)
            except ValueError as exc:
                raise ProposalRefused(
                    "entity-ranged property requires an explicit entity reference"
                ) from exc
            if target in entities:
                target_classes = (entities[target]["class_iri"],)
            else:
                target_classes = known.get(target, ())
            if not any(
                iri in definitions
                and (
                    definitions[iri].name == prop.range or prop.range in definitions[iri].ancestors
                )
                for iri in target_classes
            ):
                raise ProposalRefused("entity reference lacks the declared range membership")
            return
        native_range = constraints[definition.iri, prop.iri]["native_range"]
        if prop.range in {vocab.enum for vocab in prepared.vocabularies}:
            native_range = "string"
        prepared.property_adapter(
            definition.name, prop.name, item=prop.multivalued
        ).validate_python(_property_value(value, native_range), strict=True)

    for entity in entities.values():
        definition = definitions[entity["class_iri"]]
        for attribute in entity.get("attributes", ()):
            prop = next((p for p in definition.properties if p.iri == attribute["predicate"]), None)
            if prop is None:
                raise ProposalRefused("entity attribute does not apply to its declared class")
            check_value(attribute["value"], definition, prop)

    for claim in raw.get("claims", ()):
        if claim.get("statement") is not None and claim["statement"] not in statements:
            raise ProposalRefused("claim refers to an undeclared statement")
        if claim["subject"] in entities:
            class_iris = (entities[claim["subject"]]["class_iri"],)
        elif claim["subject"] in known:
            class_iris = known[claim["subject"]]
        else:
            raise ProposalRefused(
                "claim subject must be declared locally or in the bound reference snapshot"
            )
        applicable = [
            (definition, prop)
            for iri in class_iris
            if iri in definitions
            for definition in (definitions[iri],)
            for prop in definition.properties
            if prop.iri == claim["predicate"]
        ]
        if not applicable:
            raise ProposalRefused("claim property does not apply to its declared subject class")
        # The generated property adapter, not a second list of ranges, owns domain validation.
        errors = []
        for definition, prop in applicable:
            try:
                check_value(claim["object"], definition, prop)
                break
            except ValueError as exc:
                errors.append(str(exc))
        else:
            raise ProposalRefused(
                "claim object violates its release-derived property boundary: " + "; ".join(errors)
            )


def _refuse_rounded_decimals(prepared: PreparedRelease, batch: Mapping[str, Any]) -> None:
    """Use Pydantic's two schema modes to find Decimal input positions before JSON conversion."""
    validation = prepared.json_schema("AgentAuthoredBatch", mode="validation")
    serialization = prepared.json_schema("AgentAuthoredBatch", mode="serialization")

    def resolve(schema, root, value):
        while "$ref" in schema:
            reference = schema["$ref"]
            if not reference.startswith("#/$defs/"):
                raise ProposalRefused("proposal schema has an external unresolved reference")
            schema = root["$defs"][reference.removeprefix("#/$defs/")]
        discriminator = schema.get("discriminator")
        if discriminator is not None and isinstance(value, Mapping):
            reference = discriminator["mapping"].get(value.get(discriminator["propertyName"]))
            if reference is not None:
                return resolve({"$ref": reference}, root, value)
        return schema

    def visit(value, before, after, path):
        before, after = resolve(before, validation, value), resolve(after, serialization, value)
        accepts_number = before.get("type") == "number" or any(
            branch.get("type") == "number" for branch in before.get("anyOf", ())
        )
        if type(value) is float and accepts_number and after.get("type") == "string":
            raise ProposalRefused(
                f"{path}: exact decimals require lexical strings or exact integers, "
                "not binary floats"
            )
        if isinstance(value, Mapping):
            for name, item in value.items():
                if name in before.get("properties", {}) and name in after.get("properties", {}):
                    visit(
                        item,
                        before["properties"][name],
                        after["properties"][name],
                        f"{path}.{name}",
                    )
                elif isinstance(before.get("additionalProperties"), Mapping) and isinstance(
                    after.get("additionalProperties"), Mapping
                ):
                    visit(
                        item,
                        before["additionalProperties"],
                        after["additionalProperties"],
                        f"{path}[{name!r}]",
                    )
        elif isinstance(value, (tuple, list)) and "items" in before and "items" in after:
            for index, item in enumerate(value):
                visit(item, before["items"], after["items"], f"{path}[{index}]")

    visit(batch, validation, serialization, "$")


def locate_proposal(
    prepared: PreparedRelease,
    batch: Mapping[str, Any],
    frame: ProposalFrame,
    *,
    macros: Mapping[str, MacroDef] | None = None,
    known_classes: Mapping[str, tuple[str, ...]] | None = None,
) -> LocatedProposal:
    """Validate rich proposals and locate every citation without dropping items."""
    _refuse_rounded_decimals(prepared, batch)

    def decimal_lexical(value):
        if isinstance(value, Decimal) and value.is_finite():
            return str(value)
        raise TypeError(f"unsupported authored JSON value {type(value).__name__}")

    authored = prepared.validate_json(
        "AgentAuthoredBatch",
        json.dumps(batch, ensure_ascii=False, allow_nan=False, default=decimal_lexical),
    )
    raw = authored.model_dump(mode="python")
    if raw["unit_ref"] != frame.unit_ref:
        raise ProposalRefused("proposal unit does not match its bound source frame")
    _check_references(prepared, raw, known_classes or {})
    declared = {item["id"]: item["class_iri"] for item in raw.get("entities", ())}
    known = known_classes or {}
    iri_definitions = {definition.iri: definition for definition in prepared.definitions}

    from .reference_positions import collect_references

    for reference in collect_references(prepared, "AgentAuthoredBatch", raw):
        if reference.kind != "class":
            # Fact endpoints retain the source dependency/unresolved policy during consolidation.
            continue
        classes = (
            (declared[reference.target],)
            if reference.target in declared
            else known.get(reference.target, ())
        )
        if not any(
            iri in iri_definitions
            and (
                iri_definitions[iri].name == reference.range
                or reference.range in iri_definitions[iri].ancestors
            )
            for iri in classes
        ):
            raise ProposalRefused(
                "nested entity reference must be declared with its required class"
            )

    stored = copy.deepcopy(raw)
    for statement in stored.get("statements", ()):
        if statement["kind"] != "outside":
            statement["anchor"] = statement_anchor(statement["anchor"], frame)
    sentences = {sentence.id: sentence for sentence in frame.sentences}
    cascade = Cascade(
        frame.text,
        [FrameSentence(s.id, s.start, s.end) for s in frame.sentences],
        dict(macros or {}),
    )
    issues = []
    for section in ("claims", "unsupported", "identity_exclusions"):
        for index, item in enumerate(stored.get(section, ())):
            located = []
            for ordinal, citation in enumerate(item["evidence"]):
                path = f"{section}[{index}].evidence[{ordinal}]"
                if not citation["quote"] or citation["sentence"] not in sentences:
                    raise ProposalRefused(
                        f"{path}: citation needs nonempty quote and a declared sentence"
                    )
                found = cascade.locate(citation["quote"], citation["sentence"])
                row = dict(citation)
                row["placement"] = found.step.value if found.step is not None else "not_found"
                row["matches"] = found.matches
                row["picked"] = found.picked
                row["timeouts"] = tuple(step.value for step in found.timeouts)
                if found.score is not None:
                    row["alignment_score"] = Decimal(str(found.score))
                if found.fuzzy_counts is not None:
                    row["fuzzy_counts"] = found.fuzzy_counts
                row["outcome"] = "unlocated"
                if found.found and found.sentence is not None:
                    row.update(
                        locator=sentences[found.sentence].locator,
                        start=found.start,
                        end=found.end,
                        outcome="coarse"
                        if found.step in {Step.TOKENS, Step.CHARACTERS}
                        else "located",
                    )
                if row["outcome"] != "located":
                    issues.append(
                        ProposalIssue(
                            path, row["outcome"], "source quote placement is " + row["outcome"]
                        )
                    )
                located.append(row)
            item["evidence"] = tuple(located)
    return LocatedProposal(
        authored, prepared.validate_python("AgentStoredBatch", stored), tuple(issues)
    )


@dataclass(frozen=True)
class KnownProposalEntity:
    entity_id: str
    label: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProposalPacket:
    release_id: str
    frame: ProposalFrame
    schema: bytes
    guideline: str
    configuration: bytes
    known_classes: tuple[tuple[str, tuple[str, ...]], ...] = ()
    known_entities: tuple[KnownProposalEntity, ...] = ()
    bootstrap_terms: tuple[str, ...] = ()
    macros: tuple[tuple[str, MacroDef], ...] = ()

    @property
    def schema_hash(self) -> str:
        from hashlib import sha256

        return sha256(self.schema).hexdigest()

    @property
    def hash(self) -> str:
        from dataclasses import asdict
        from hashlib import sha256

        from .identity import canonical_bytes

        return sha256(
            canonical_bytes(
                [
                    self.release_id,
                    asdict(self.frame),
                    self.schema_hash,
                    self.guideline,
                    self.configuration.decode(),
                    self.known_classes,
                    [asdict(entity) for entity in self.known_entities],
                    self.bootstrap_terms,
                    [(name, macro.model_dump(mode="json")) for name, macro in self.macros],
                ]
            )
        ).hexdigest()

    def parts(self) -> tuple[Part, ...]:
        from .identity import canonical_bytes

        data = {
            "schema": self.schema.decode(),
            "guideline": self.guideline,
            "unit": canonical_bytes(
                {
                    "unit_ref": self.frame.unit_ref,
                    "sentences": [
                        {
                            "id": sentence.id,
                            "locator": sentence.locator,
                            "text": self.frame.text[sentence.start : sentence.end],
                        }
                        for sentence in self.frame.sentences
                    ],
                    "known_classes": dict(self.known_classes),
                    "known_entities": [
                        {
                            "entity_id": entity.entity_id,
                            "label": entity.label,
                            "aliases": entity.aliases,
                        }
                        for entity in self.known_entities
                    ],
                    "bootstrap_terms": self.bootstrap_terms,
                    "macros": {name: macro.model_dump(mode="json") for name, macro in self.macros},
                }
            ).decode(),
        }
        return tuple(Part(name, text, text_hash(text)) for name, text in data.items())

    def part_pages(self, part: Part) -> list[str]:
        """Use the existing packet character cap for source pages; never truncate source text."""
        configuration = json.loads(self.configuration)
        size = configuration.get("packet_cap_chars", 18_000) if part.name == "unit" else PAGE_CHARS
        if type(size) is not int or size < 1:
            raise ProposalRefused("packet_cap_chars must be a positive integer")
        return part.pages(size=size)


def proposal_packet(
    prepared: PreparedRelease,
    frame: ProposalFrame,
    *,
    guideline: str,
    configuration: Mapping[str, Any],
    known_classes: Mapping[str, tuple[str, ...]] | None = None,
    known_entities: tuple[KnownProposalEntity, ...] = (),
    bootstrap_terms: tuple[str, ...] = (),
    macros: Mapping[str, MacroDef] | None = None,
) -> ProposalPacket:
    """Bind all model-facing parts and their complete source frame before queuing agent work."""
    from .identity import canonical_bytes

    schema = prepared.json_schema("AgentAuthoredBatch", mode="serialization")
    if prepared.execution_model_id is None:
        schema = copy.deepcopy(schema)
        properties = schema.get("properties")
        if isinstance(properties, dict):
            properties.pop("identity_exclusions", None)
    schema["$id"] = prepared.release_id + "/agent/authored"
    return ProposalPacket(
        prepared.release_id,
        frame,
        canonical_bytes(schema),
        guideline,
        canonical_bytes(dict(configuration)),
        tuple(sorted((known_classes or {}).items())),
        tuple(sorted(known_entities, key=lambda entity: entity.entity_id)),
        bootstrap_terms,
        tuple(sorted((macros or {}).items())),
    )
