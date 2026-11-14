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
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import BaseModel

from corpus_structure.core.evidence import MacroDef
from corpus_structure.core.locators import LocatorIndex
from corpus_structure.methods.llm.parts import PAGE_CHARS, Part, text_hash

from .types import PreparedRelease, ResolvedDependencies, SourceArtifact, SourceBundle

if TYPE_CHECKING:
    from .declared_record_sources import DeclaredNativeFrameSource
    from .product_reference import ProductReference


_MODEL = Path(__file__).resolve().parents[1] / "model" / "semantic" / "agent.yaml"
_EMPTY_DEPENDENCIES = ResolvedDependencies()
SEMANTIC_AGENT_VERSION = "semantic-7"
MAX_KNOWN = 30


def proposal_inputs(
    bundle: SourceBundle,
    dependencies: ResolvedDependencies = _EMPTY_DEPENDENCIES,
    *,
    qualification_class: str = "Qualification",
    statement_class: str = "SourceStatement",
    model_content: bytes | None = None,
    observation_content: bytes | None = None,
) -> SourceBundle:
    """Archive model-facing boundaries with the exact candidate vocabulary."""
    from .observations import observation_inputs

    bundle = observation_inputs(bundle, model_content=observation_content)
    if {source.name for source in bundle.sources} & {"agent", "agent-root"}:
        raise ValueError("reserved agent module name already supplied")
    from .prepare import preview_schema

    candidate = preview_schema(bundle, dependencies)
    module = yaml.safe_load(_MODEL.read_bytes() if model_content is None else model_content)
    qualification = next((d for d in candidate.classes if d.name == qualification_class), None)
    if qualification is None or not (
        qualification.name == "Qualification" or "Qualification" in qualification.ancestors
    ):
        raise ValueError("agent operation needs an explicit Qualification class or subclass")
    module["classes"]["AgentClaim"]["attributes"]["qualification"]["range"] = qualification_class
    module["classes"]["SourceAttributeAssertion"]["attributes"]["qualification"]["range"] = (
        qualification_class
    )
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
    for contextual, canonical in (
        ("AgentStatementRole", "StatementRole"),
        ("AgentEvidenceRole", "EvidenceRole"),
    ):
        module["enums"][contextual]["permissible_values"] = {
            name: {} for name in sorted(candidate.enum_members(canonical))
        }
    # Resolve the effective member metadata through the ordinary release preparer, rather
    # than reproducing LinkML inheritance/include semantics in the producer.
    module["enums"]["SourceEstablishment"]["permissible_values"] = {
        name: {}
        for name in sorted(candidate.enum_members("Establishment", subset="source_admissible"))
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


@dataclass(frozen=True)
class NativeFrameSource:
    """One pinned native source with coordinates in its own text projection."""

    unit_ref: str
    text: str
    sentences: tuple[ProposalSentence, ...]
    source_view_id: int
    native_product: ProductReference
    section_pointer: str
    membership: str
    projection_digest: str
    recipe_digest: str
    native_context: str
    version: int = 2

    @property
    def source_key(self):
        return self.source_view_id

    @property
    def original_key(self):
        return self.native_product

    def __post_init__(self) -> None:
        from .identity import canonical_bytes

        # Reuse coordinate/handle validation while keeping the historical dataclass/hash intact.
        ProposalFrame(self.unit_ref, self.text, self.sentences)
        if self.source_view_id < 1 or self.membership not in {"direct", "descendants"}:
            raise ValueError("native frame requires a real source view and membership policy")
        if self.version not in {2, 3}:
            raise ValueError("unsupported native frame contract version")
        context = json.loads(self.native_context)
        if not isinstance(context, dict) or set(context) - {"integrated_context_json"} != {
            "items",
            "pieces",
            "ancestors",
            "health",
        }:
            raise ValueError("native frame context must retain items, pieces, ancestry and health")
        if "integrated_context_json" in context:
            if self.version != 3:
                raise ValueError("integrated frame requires contract version 3")
            integrated = json.loads(context["integrated_context_json"])
            selection = integrated["selection"]
            if selection != dict(
                task_id=self.native_product.task_id,
                product_key=self.native_product.product_key,
                content_digest=self.native_product.content_digest,
            ):
                raise ValueError("integrated frame companion differs from selected product")
            if canonical_bytes(integrated).decode() != context["integrated_context_json"]:
                raise ValueError("integrated frame companion must use canonical semantic JSON")
        if canonical_bytes(context).decode() != self.native_context:
            raise ValueError("native frame context must use canonical semantic JSON")
        for digest in (
            self.projection_digest,
            self.recipe_digest,
            self.native_product.content_digest,
        ):
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("native frame requires immutable product/projection/recipe pins")
        for sentence in self.sentences:
            expected = native_address(self, start=sentence.start, end=sentence.end)
            if sentence.locator != expected:
                raise ValueError("native sentence locator differs from its qualified projection")
        aliases = {entry["handle"]: entry for entry in native_evidence_entries(self)}
        for sentence in self.sentences:
            if sentence.id.startswith("native_evidence:"):
                entry = aliases.get(sentence.id)
                if entry is None or (sentence.start, sentence.end, sentence.locator) != (
                    entry["start"],
                    entry["end"],
                    entry["locator"],
                ):
                    raise ValueError(
                        "native evidence handle differs from its retained projection piece"
                    )


@dataclass(frozen=True)
class NativeProposalFrame(NativeFrameSource):
    """Primary unit and bounded direct ancestor sources, without mixing coordinates."""

    context_sources: tuple[NativeFrameSource, ...] = ()

    def __post_init__(self) -> None:
        super().__post_init__()
        ancestors = {
            item.get("self_ref", item.get("pointer"))
            for item in json.loads(self.native_context)["ancestors"]
        }
        ids = {self.source_view_id}
        for source in self.context_sources:
            if (
                source.source_view_id in ids
                or source.membership != "direct"
                or source.native_product != self.native_product
                or source.section_pointer not in ancestors
            ):
                raise ValueError(
                    "native context source must be a distinct direct ancestor of the same product"
                )
            ids.add(source.source_view_id)
        native_frame_entries(self)


def native_frame_source(frame: NativeFrameSource) -> NativeFrameSource:
    from dataclasses import fields

    return NativeFrameSource(
        **{field.name: getattr(frame, field.name) for field in fields(NativeFrameSource)}
    )


def native_frame_entries(
    frame: NativeProposalFrame,
) -> dict[str, tuple[NativeFrameSource, ProposalSentence]]:
    entries: dict[str, tuple[NativeFrameSource, ProposalSentence]] = {
        sentence.id: (frame, sentence) for sentence in frame.sentences
    }
    if frame.context_sources and any(key.startswith("native_context:") for key in entries):
        raise ValueError("native context handle namespace is reserved")
    for source in frame.context_sources:
        for sentence in source.sentences:
            handle = f"native_context:{source.source_view_id}:{sentence.id}"
            if handle in entries:
                raise ValueError("duplicate native source evidence handle")
            entries[handle] = (source, sentence)
    return entries


def native_statement_source(frame: NativeProposalFrame, anchor: str) -> NativeFrameSource:
    entries = native_frame_entries(frame)
    if anchor in entries:
        return entries[anchor][0]
    sources = (frame, *frame.context_sources)
    direct = [source for source in sources if source.unit_ref == anchor]
    if len(direct) == 1:
        return direct[0]
    if not anchor.startswith("pdf:"):
        raise ProposalRefused("statement anchor is outside the supplied native sources")
    try:
        address = json.loads(anchor[4:])
    except (ValueError, TypeError) as error:
        raise ProposalRefused("invalid qualified native address") from error
    candidates = []
    for source in sources:
        if address.get("product_digest") != source.native_product.content_digest:
            continue
        if "pointer" in address:
            pointers = {
                item.get("self_ref", item.get("pointer"))
                for item in json.loads(source.native_context)["items"]
            } | {source.section_pointer}
            if address["pointer"] not in pointers:
                continue
            expected = native_address(source, pointer=address["pointer"])
        else:
            if address.get("source_view_id") != source.source_view_id:
                continue
            try:
                expected = native_address(source, start=address["start"], end=address["end"])
            except KeyError, TypeError, ValueError:
                continue
        if expected == anchor:
            candidates.append(source)
    if len(candidates) != 1:
        raise ProposalRefused("native address is absent or ambiguous among supplied frame sources")
    return candidates[0]


def native_frame_from_dict(raw: Mapping[str, Any]) -> NativeProposalFrame:
    from .product_reference import ProductReference

    def source(value):
        fields = dict(value)
        fields["sentences"] = tuple(ProposalSentence(**entry) for entry in fields["sentences"])
        fields["native_product"] = ProductReference(**fields["native_product"])
        return fields

    primary = source(raw)
    primary["context_sources"] = tuple(
        NativeFrameSource(**source(value)) for value in raw.get("context_sources", ())
    )
    return NativeProposalFrame(**primary)


def native_frame_identity(frame: ProposalFrame | NativeProposalFrame) -> dict[str, Any]:
    from dataclasses import asdict

    value = asdict(frame)
    if isinstance(frame, NativeProposalFrame) and frame.version == 2:
        value.pop("version", None)
        for source in value.get("context_sources", ()):
            if source.get("version") == 2:
                source.pop("version", None)
    if isinstance(frame, NativeProposalFrame) and not frame.context_sources:
        value.pop("context_sources", None)
    return value


def native_address(
    frame: NativeFrameSource | DeclaredNativeFrameSource,
    *,
    pointer: str | None = None,
    start: int | None = None,
    end: int | None = None,
) -> str:
    """Typed native address encoded canonically, never parsed as an HTML locator."""
    from .declared_record_sources import DeclaredNativeFrameSource
    from .identity import canonical_bytes

    value: dict[str, str | int]
    if isinstance(frame, DeclaredNativeFrameSource):
        pin = frame.pin.values()
        value = {
            name: pin[name]
            for name in (
                "source_product",
                "document",
                "projection_digest",
                "section_pointer",
                "membership",
            )
        }
        if "source_member" in pin:
            value["source_member"] = pin["source_member"]
    else:
        value = {"product_digest": frame.native_product.content_digest}
    if pointer is not None:
        if start is not None or end is not None or not pointer.startswith("#/"):
            raise ValueError("native item address cannot mix projected offsets")
        value["pointer"] = pointer
    else:
        if start is None or end is None or not 0 <= start < end <= len(frame.text):
            raise ValueError("native projection address lies outside its source view")
        value.update(projection_digest=frame.projection_digest, start=start, end=end)
        if not isinstance(frame, DeclaredNativeFrameSource):
            value["source_view_id"] = frame.source_view_id
    return "pdf:" + canonical_bytes(value).decode()


def native_evidence_entries(frame: NativeFrameSource) -> tuple[dict[str, Any], ...]:
    """Deterministic evidence handles over retained native projection pieces, not PDF glyphs."""
    context = json.loads(frame.native_context)
    integrated = (
        json.loads(context["integrated_context_json"])
        if "integrated_context_json" in context
        else None
    )
    entries = []
    for index, piece in enumerate(context["pieces"]):
        if (
            piece.get("kind") != "native_text"
            or not piece.get("item_ref")
            or piece["start"] >= piece["end"]
        ):
            continue
        entry = dict(
            handle=f"native_evidence:{index}",
            pointer=piece["item_ref"],
            start=piece["start"],
            end=piece["end"],
            text=frame.text[piece["start"] : piece["end"]],
            locator=native_address(frame, start=piece["start"], end=piece["end"]),
        )
        for name in ("cell_index", "source_field"):
            if name in piece:
                entry[name] = piece[name]
        if integrated is not None:
            matches = [
                row
                for row in integrated.get("occurrences", ())
                if row.get("body", row).get("pointer") == piece["item_ref"]
                and (
                    "cell_index" not in piece
                    or row.get("body", row).get("cell_index") == piece["cell_index"]
                )
            ]
            entry["integrated_selection"] = integrated["selection"]
            entry["occurrences"] = [
                dict(
                    occurrence_id=row["occurrence_id"],
                    precision=row.get("precision", "unknown"),
                    address_space=row.get("address_space", "unknown"),
                )
                for row in matches
            ]
            precisions = {row.get("precision", "unknown") for row in matches}
            entry["precision"] = next(iter(precisions)) if len(precisions) == 1 else "unknown"
        entries.append(entry)
    return tuple(entries)


def native_source_frame(
    view: Any, sentences: Sequence[tuple[str, int, int]]
) -> NativeProposalFrame:
    """Bind actual prepared section context and supplied sentence offsets without inference."""
    from dataclasses import asdict, is_dataclass

    from .identity import canonical_bytes

    def plain(value: Any) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json")
        if is_dataclass(value) and not isinstance(value, type):
            return plain(asdict(value))
        if isinstance(value, Mapping):
            return {key: plain(child) for key, child in value.items()}
        if isinstance(value, (tuple, list)):
            return [plain(child) for child in value]
        return value

    context = canonical_bytes(
        plain(view.context())
        if hasattr(view, "context")
        else {
            name: plain(getattr(view, name)) for name in ("items", "pieces", "ancestors", "health")
        }
    ).decode()
    ref = view.ref
    # Coordinates are authored from the already prepared text projection, never guessed by
    # searching repeated strings in the book or reinterpreted as PDF glyph positions.
    if any(id.startswith(("native_evidence:", "native_context:")) for id, _, _ in sentences):
        raise ValueError("native evidence handles are reserved for retained projection pieces")
    aliases = tuple(
        (f"native_evidence:{index}", piece["start"], piece["end"])
        for index, piece in enumerate(json.loads(context)["pieces"])
        if piece.get("kind") == "native_text"
        and piece.get("item_ref")
        and piece["start"] < piece["end"]
    )
    located = tuple(
        ProposalSentence(
            id,
            "pdf:"
            + canonical_bytes(
                {
                    "product_digest": ref.native_product.content_digest,
                    "source_view_id": ref.id,
                    "projection_digest": ref.projection_digest,
                    "start": start,
                    "end": end,
                }
            ).decode(),
            start,
            end,
        )
        for id, start, end in (*sentences, *aliases)
    )
    return NativeProposalFrame(
        ref.key,
        view.text,
        located,
        ref.id,
        ref.native_product,
        ref.section_pointer,
        ref.membership,
        ref.projection_digest,
        ref.recipe_digest,
        context,
        version=3,
    )


def statement_anchor(
    anchor: str, frame: ProposalFrame | NativeProposalFrame, *, index: LocatorIndex | None = None
) -> str:
    """Resolve a local handle through its frame, never through another packet's namespace.

    A source report may use its declared unit or supplied canonical sentence locators. The
    consolidation boundary can additionally resolve an explicit source locator on the exact
    rendition; unsupported strings never become located statement identities.
    """
    if isinstance(frame, NativeProposalFrame):
        entries = native_frame_entries(frame)
        if anchor in entries:
            return entries[anchor][1].locator
        source = native_statement_source(frame, anchor)
        if anchor == source.unit_ref:
            return native_address(source, pointer=source.section_pointer)
        allowed = {sentence.locator for sentence in source.sentences}
        allowed.update(
            native_address(source, pointer=item.get("self_ref", item.get("pointer")))
            for item in json.loads(source.native_context)["items"]
        )
        if anchor not in allowed:
            raise ProposalRefused("statement anchor is outside the supplied native entries")
        return anchor
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
    from .publication import native_constraints
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
    frame: ProposalFrame | NativeProposalFrame,
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
    from .statement_types import statement_definition

    declared.update(
        {item["id"]: statement_definition(prepared).iri for item in raw.get("statements", ())}
    )

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
    source_entries = (
        native_frame_entries(frame)
        if isinstance(frame, NativeProposalFrame)
        else {sentence.id: (frame, sentence) for sentence in frame.sentences}
    )
    sentences = {handle: sentence for handle, (_, sentence) in source_entries.items()}
    from corpus_structure.methods.llm.cascade import Cascade, FrameSentence, Located, Step

    from .analysis_contracts import prepare_placement_policy

    placement_policy = prepare_placement_policy(prepared)
    cascade = Cascade(
        frame.text,
        [
            FrameSentence(s.id, s.start, s.end)
            for s in frame.sentences
            if not isinstance(frame, NativeProposalFrame) or not s.id.startswith("native_evidence:")
        ],
        dict(macros or {}),
        policy=placement_policy,
    )
    native_cascades = {}

    issues = []
    evidence_items = [
        (f"{section}[{index}]", item)
        for section in ("claims", "unsupported", "identity_exclusions")
        for index, item in enumerate(stored.get(section, ()))
    ]
    evidence_items.extend(
        (f"entities[{index}].attributes[{ordinal}]", attribute)
        for index, entity in enumerate(stored.get("entities", ()))
        for ordinal, attribute in enumerate(entity.get("attributes", ()))
    )
    for item_path, item in evidence_items:
        located = []
        for ordinal, citation in enumerate(item["evidence"]):
            path = f"{item_path}.evidence[{ordinal}]"
            if not citation["quote"] or citation["sentence"] not in sentences:
                raise ProposalRefused(
                    f"{path}: citation needs nonempty quote and a declared sentence"
                )
            handle = citation["sentence"]
            source, sentence = source_entries[handle]
            native_alias = isinstance(frame, NativeProposalFrame) and (
                source is not frame or sentence.id.startswith("native_evidence:")
            )
            # Native aliases name one retained item/cell/formula piece. A quote outside that
            # piece cannot relocate into another sentence or use a fuzzy reinterpretation.
            if native_alias:
                if citation["quote"] not in source.text[sentence.start : sentence.end]:
                    found = Located()
                else:
                    if handle not in native_cascades:
                        native_cascades[handle] = Cascade(
                            source.text,
                            [FrameSentence(handle, sentence.start, sentence.end)],
                            dict(macros or {}),
                            policy=placement_policy,
                        )
                    found = native_cascades[handle].locate(citation["quote"], handle)
            else:
                found = cascade.locate(citation["quote"], sentence.id)
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
                    outcome="coarse" if found.step in {Step.TOKENS, Step.CHARACTERS} else "located",
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
    frame: ProposalFrame | NativeProposalFrame
    schema: bytes
    guideline: str
    configuration: bytes
    known_classes: tuple[tuple[str, tuple[str, ...]], ...] = ()
    known_entities: tuple[KnownProposalEntity, ...] = ()
    bootstrap_terms: tuple[str, ...] = ()
    macros: tuple[tuple[str, MacroDef], ...] = ()
    native_observations: tuple[Mapping[str, Any], ...] = ()

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
                    native_frame_identity(self.frame),
                    self.schema_hash,
                    self.guideline,
                    self.configuration.decode(),
                    self.known_classes,
                    [asdict(entity) for entity in self.known_entities],
                    self.bootstrap_terms,
                    [(name, macro.model_dump(mode="json")) for name, macro in self.macros],
                    *([self.native_observations] if self.native_observations else []),
                ]
            )
        ).hexdigest()

    def parts(self) -> tuple[Part, ...]:
        from dataclasses import asdict

        from .identity import canonical_bytes

        data = {
            "schema": self.schema.decode(),
            "guideline": self.guideline,
            "unit": canonical_bytes(
                {
                    "unit_ref": self.frame.unit_ref,
                    **(
                        {
                            "native_source": {
                                "source_view_id": self.frame.source_view_id,
                                "native_product": asdict(self.frame.native_product),
                                "section_pointer": self.frame.section_pointer,
                                "membership": self.frame.membership,
                                "projection_digest": self.frame.projection_digest,
                                "recipe_digest": self.frame.recipe_digest,
                                "context": json.loads(self.frame.native_context),
                                "native_evidence": native_evidence_entries(self.frame),
                                "context_sources": [
                                    dict(
                                        source_view_id=source.source_view_id,
                                        unit_ref=source.unit_ref,
                                        native_product=asdict(source.native_product),
                                        section_pointer=source.section_pointer,
                                        membership=source.membership,
                                        projection_digest=source.projection_digest,
                                        recipe_digest=source.recipe_digest,
                                        context=json.loads(source.native_context),
                                        sentences=[
                                            dict(
                                                id=f"native_context:{source.source_view_id}:{sentence.id}",
                                                locator=sentence.locator,
                                                text=source.text[sentence.start : sentence.end],
                                            )
                                            for sentence in source.sentences
                                            if not sentence.id.startswith("native_evidence:")
                                        ],
                                        native_evidence=[
                                            dict(
                                                entry,
                                                handle=f"native_context:{source.source_view_id}:{entry['handle']}",
                                            )
                                            for entry in native_evidence_entries(source)
                                        ],
                                    )
                                    for source in self.frame.context_sources
                                ],
                            }
                        }
                        if isinstance(self.frame, NativeProposalFrame)
                        else {}
                    ),
                    "sentences": [
                        {
                            "id": sentence.id,
                            "locator": sentence.locator,
                            "text": self.frame.text[sentence.start : sentence.end],
                        }
                        for sentence in self.frame.sentences
                        if not isinstance(self.frame, NativeProposalFrame)
                        or not sentence.id.startswith("native_evidence:")
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
                    **(
                        {"native_observations": self.native_observations}
                        if self.native_observations
                        else {}
                    ),
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
    frame: ProposalFrame | NativeProposalFrame,
    *,
    guideline: str,
    configuration: Mapping[str, Any],
    known_classes: Mapping[str, tuple[str, ...]] | None = None,
    known_entities: tuple[KnownProposalEntity, ...] = (),
    bootstrap_terms: tuple[str, ...] = (),
    macros: Mapping[str, MacroDef] | None = None,
    native_observations: tuple[Mapping[str, Any], ...] = (),
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
        native_observations,
    )
