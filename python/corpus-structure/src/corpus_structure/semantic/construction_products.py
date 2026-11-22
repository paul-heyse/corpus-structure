"""Ordinary symbolic constructions from retained primary source characterizations.

The grammar/reducer and local graph checks are shared with the released legacy
projection. Native admission, execution recipes and physical receipts stay outside
these source-addressed semantic facts.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any, ClassVar, Self, overload

import yaml
from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.methods.annotation_rules import AnnotationRule, PreparedAnnotationRules
from corpus_structure.semantic.characterization import (
    _inventory_field,
    admitted_characterization_graph,
    validate_inventory_topology,
)
from corpus_structure.semantic.native_source_view import (
    freeze_native,
    matches_positioned_source_extent,
)
from corpus_structure.semantic.source_products import (
    native_selected_ranges,
    native_selected_unprojected_atoms,
    native_selector_covers_extent,
    native_selector_facts,
)

from .characterization import (
    attachment_policies,
    validate_attachment_basis,
    verify_interpreted_attachment_witnesses,
    verify_inventory_native_scores,
    verify_inventory_occurrence_ids,
)
from .characterization_evidence import (
    validate_navigation_token_premises,
    verify_navigation_source_fields,
)
from .characterization_manifests import analytical_packets, append_manifest, manifest_contract
from .constructions.declarations import FAMILIES, GRAMMAR_FAMILIES
from .constructions.layers import ConstructionLayer, ConstructionSource
from .constructions.math_scope import Binders, NativeDomainRule
from .data_operation_identity import body_identity, contextual_product_identity
from .data_operation_model import BoundRoleMember, EffectiveDataOperationModel, SubjectContext
from .data_product_reference import (
    DataProductReference,
    SemanticReference,
    read_semantic_reference,
    reference_inputs,
)
from .formal_products import FormalEvidenceProduct, formal_product_inputs
from .formal_readings import FormalSourceReadings
from .identity import canonical_bytes
from .sentence_products import (
    SourceAnnotations,
    retained_source_annotation_products,
    sentence_product_inputs,
    verify_source_annotation_carrier,
)
from .source_products import (
    FrozenNativeSource,
    source_subject,
)
from .types import PreparedRelease, SourceArtifact, SourceBundle

_MODEL = Path(__file__).parents[1] / "model/semantic/data-operation-constructions.yaml"
_INVENTORIES = (
    ("occurrences", "occurrence"),
    ("annotations", "annotation"),
    ("memberships", "membership"),
    ("roles", "role"),
    ("terms", "term"),
    ("choices", "choice"),
)

_MEMBER_VARIANTS = (*_INVENTORIES, ("choice_members", "choice_member"))


def _basis_projection(content: bytes, characterization: bytes) -> bytes:
    """Derive native-address shape from the one captured authored basis family."""
    import copy

    model = yaml.safe_load(content)
    original = yaml.safe_load(characterization)["classes"]
    family = {
        "CharacterizationAttachmentBasis",
        *(name for name in original if name.startswith("CharacterizationNavigation")),
    }
    while True:
        expanded = family | {name for name, body in original.items() if body.get("is_a") in family}
        if expanded == family:
            break
        family = expanded

    def target(name):
        return "DdoSemantic" + name.removeprefix("Characterization")

    def retarget(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: (target(item) if key == "range" and item in family else retarget(item))
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [retarget(item) for item in value]
        return value

    for name in sorted(family):
        if name == "CharacterizationNavigationToken":
            # The source role owns the address separately from this token's label and index.
            continue
        body = retarget(copy.deepcopy(original[name]))
        parent = original[name].get("is_a")
        if parent in family and parent != "CharacterizationAttachmentBasis":
            # Rule-specific verification is a derived standalone shape, not a
            # second kind-dispatch candidate alongside its generic basis kind.
            chain = []
            current = name
            while current in family:
                chain.append(current)
                current = original[current].get("is_a")
            attributes = {}
            for ancestor in reversed(chain):
                attributes.update(copy.deepcopy(original[ancestor].get("attributes", {})))
            body = retarget({"is_a": "SourceRecordProduct", "attributes": attributes})
        else:
            body["is_a"] = target(parent) if parent in family else "SourceRecordProduct"
        body.pop("class_uri", None)
        body["annotations"] = {**body.get("annotations", {}), "cs:data_universe": "ordinary"}
        if name == "CharacterizationAttachmentBasis":
            body["abstract"] = True
        model["classes"][target(name)] = body
    return yaml.safe_dump(model, sort_keys=False).encode()


def construction_product_inputs(bundle: SourceBundle) -> SourceBundle:
    bundle = formal_product_inputs(sentence_product_inputs(reference_inputs(bundle)))
    root = "data_operation_constructions_root"
    if {"data_operation_constructions", root} & {source.name for source in bundle.sources}:
        raise ValueError("construction profile uses reserved schema names")
    original = next(
        source.content for source in bundle.sources if source.name == "characterization"
    )
    content = _basis_projection(_MODEL.read_bytes(), original)
    return SourceBundle(
        root,
        (
            *bundle.sources,
            SourceArtifact("data_operation_constructions", content),
            SourceArtifact(
                root,
                yaml.safe_dump(
                    dict(
                        id="urn:corpus:data-operation-constructions-root",
                        name=root,
                        imports=[bundle.root, "data_operation_constructions"],
                    )
                ).encode(),
            ),
        ),
    )


class ConstructionOptions(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    max_region_chars: int = Field(default=4096, gt=0)
    parse_seconds: float = Field(default=2, gt=0)
    annotation_rules: tuple[AnnotationRule, ...] = ()
    math_scope_binders: Binders | None = None
    math_domain_rules: tuple[NativeDomainRule, ...] = ()


def load_construction_options(domain: Path) -> ConstructionOptions:
    """Acquire domain-authored rules once before freezing operation custody."""
    return ConstructionOptions.model_validate(
        yaml.safe_load((domain / "construction.yaml").read_bytes())
    )


def interpreted_member_contracts(prepared, model):
    identities = {(item.owner, item.domain): item.key for item in model.identities}
    result = {}
    for definition in prepared.definitions:
        if "DdoInterpretedMember" not in definition.ancestors or definition.abstract:
            continue
        tag = next(
            prop.equals_string for prop in definition.properties if prop.name == "record_type"
        )
        if tag == "manifest":
            continue
        if tag is None or tag in result:
            raise ValueError("construction members require unique nominal discriminators")
        result[tag] = identities[definition.iri, "kind"]
    if set(result) != {tag for _, tag in _MEMBER_VARIANTS}:
        raise ValueError("construction member contracts differ from actual inventories")
    result["construction_manifest"] = manifest_contract(prepared, model, "DdoConstructionManifest")
    result["contextual_manifest"] = manifest_contract(prepared, model, "DdoContextualManifest")
    return result


@dataclass(frozen=True)
class _InterpretedPayload:
    content: bytes
    value: Mapping[str, Any]
    inventory: Mapping[str, Any]
    meaning: bytes
    members: tuple[bytes, ...]
    body_digest: str
    kind_contract: str
    construction_formal_parents: tuple[tuple[str, str], ...] = ()
    contextual_input_parents: tuple[tuple[str, str, str], ...] = ()
    dependency_products: tuple[str, ...] = ()


@dataclass(frozen=True, init=False)
class InterpretedProduct:
    manifest_name: ClassVar[str]
    kind_name: ClassVar[str]
    content: bytes
    prepared: PreparedRelease
    model: EffectiveDataOperationModel
    subject_context: SubjectContext | None
    _payload: ClassVar[_InterpretedPayload]
    _source: ClassVar[FrozenNativeSource]

    def __init__(self, *args, **kwargs):
        raise TypeError(
            "interpreted evidence requires validated production or exact native acquisition"
        )

    @classmethod
    def _from_payload(cls, payload, source, prepared, model, subject_context) -> Self:
        product = object.__new__(cls)
        object.__setattr__(product, "content", payload.content)
        object.__setattr__(product, "prepared", prepared)
        object.__setattr__(product, "model", model)
        object.__setattr__(product, "subject_context", subject_context)
        object.__setattr__(product, "_source", source)
        object.__setattr__(product, "_payload", payload)
        return product

    def _require_acquired(self):
        if "_payload" not in vars(self) or self.content is not self._payload.content:
            raise TypeError("interpreted evidence lacks its acquired payload")

    def __deepcopy__(self, memo):
        self._require_acquired()
        return self

    def with_context(self, context: SubjectContext | None):
        self._require_acquired()
        return self._from_payload(self._payload, self._source, self.prepared, self.model, context)

    def require_readable_from(self, source, model, dependencies):
        self._require_acquired()
        FrozenNativeSource._require_acquired(source)
        if self._source.value != source.value:
            raise ValueError("construction product belongs to another original source/scope")
        kind = self.prepared.index.definitions[self.kind_name].iri
        if not any(
            (item.owner, item.domain, item.key) == (kind, "kind", self._payload.kind_contract)
            for item in model.identities
        ):
            raise ValueError("construction product has another nominal contract")
        available = {product.semantic_id for product in dependencies}
        if not set(self.dependency_products) <= available:
            raise ValueError("interpreted product lacks its exact retained dependency closure")

    @property
    def dependency_products(self):
        """Exact arguments of this acquired producer origin, outside serialized meaning."""
        self._require_acquired()
        return self._payload.dependency_products

    def _publication_context(self):
        if self.subject_context is None:
            raise ValueError(
                "native product identity requires an explicit acquired subject context"
            )
        return self.subject_context

    @property
    def value(self) -> Mapping[str, Any]:
        self._require_acquired()
        return self._payload.value

    def publication(self, role, kind_contract):
        from .data_operation_ports import RoleValue

        self._require_acquired()
        if kind_contract != self._payload.kind_contract:
            raise ValueError("interpreted publication changes its acquired kind")
        return RoleValue(
            role, kind_contract, self.content, self._payload.meaning, self._payload.members
        )

    @cached_property
    def semantic_id(self):
        self._require_acquired()
        return contextual_product_identity(
            kind=self._payload.kind_contract,
            context=self._publication_context(),
            body=self._payload.body_digest,
        ).key

    @property
    def reference(self):
        return DataProductReference(self.semantic_id)

    def inventory(self):
        self._require_acquired()
        return self._payload.inventory


@dataclass(frozen=True, init=False)
class ConstructionProduct(InterpretedProduct):
    kind_name: ClassVar[str] = "DdoPrimaryConstructionProduct"
    manifest_name: ClassVar[str] = "DdoConstructionManifest"

    @property
    def construction_formal_parents(self):
        self._require_acquired()
        return self._payload.construction_formal_parents


@dataclass(frozen=True)
class CharacterizationSnapshot:
    """Private owned kernel transfer, derived from parent-validated nominal products."""

    product_id: str
    content: bytes
    partitions: tuple[bytes, ...] | None = None
    construction_formal_parents: tuple[tuple[str, str], ...] = ()
    contextual_input_parents: tuple[tuple[str, str, str], ...] = ()

    @property
    def semantic_id(self):
        return self.product_id

    @cached_property
    def value(self) -> Mapping[str, Any]:
        return freeze_native(json.loads(self.content))

    @classmethod
    def from_product(cls, product):
        positions = getattr(product, "construction_formal_parents", ())
        snapshot = cls(
            product.semantic_id,
            product.content,
            getattr(product, "partitions", None),
            positions,
            getattr(product, "contextual_input_parents", ()),
        )
        object.__setattr__(snapshot, "value", product.value)
        return snapshot

    def inventory(self):
        body = self.value
        result = {name: [] for name, _ in _INVENTORIES}
        result["source_facts"] = []
        names = {tag: name for name, tag in _INVENTORIES}
        for packet in body.get("members", ()):
            tag = packet["body"]["record_type"]
            if tag in names:
                result[names[tag]].append(packet["body"])
            elif tag not in {"choice_member", "manifest"}:
                result["source_facts"].append(packet)
        return {**result, "coverage": body["coverage"]}


def _requested_regions(source: FrozenNativeSource):
    selected = source.value
    index = source.selector_index()
    result = []
    unknown = []
    for selector in selected["selectors"]:
        intervals = []
        for piece in selected["pieces"]:
            if piece["kind"] != "native_text":
                continue
            match = index.matches(selector, piece["item_ref"])
            if match is None:
                unknown.append(selector)
            if match is not True:
                continue
            a, b = (
                max(piece["start"], selector.get("start", 0)),
                min(piece["end"], selector.get("end", len(selected["text"]))),
            )
            if a < b:
                if intervals and source.view.native_gap(intervals[-1][1], a):
                    intervals[-1] = (intervals[-1][0], b)
                else:
                    intervals.append((a, b))
        result.extend(intervals)
    return tuple(result), tuple(unknown)


def _clip_sentence_regions(regions, boundaries):
    """Join open intervals in one sweep, then restore region/sentence order."""
    events = []
    for population, rows in enumerate(
        (regions, tuple((row["start"], row["end"]) for row in boundaries))
    ):
        for ordinal, (start, end) in enumerate(rows):
            if start < end:
                events.extend(
                    ((start, 1, population, ordinal, end), (end, 0, population, ordinal, start))
                )
    active = ({}, {})
    clipped = []
    for position, opening, population, ordinal, other in sorted(events):
        if not opening:
            active[population].pop(ordinal)
            continue
        for counterpart, (start, end) in active[1 - population].items():
            region, sentence = (ordinal, counterpart) if population == 0 else (counterpart, ordinal)
            clipped.append((region, sentence, (max(position, start), min(other, end))))
        active[population][ordinal] = position, other
    return [interval for _region, _sentence, interval in sorted(clipped)]


def construction_product_values(
    source: FrozenNativeSource,
    formal: tuple[CharacterizationSnapshot, ...],
    options: ConstructionOptions,
    member_contracts: dict[str, str],
    *,
    native: CharacterizationSnapshot | None = None,
    check_active: Callable[[], None] = lambda: None,
):
    """Actual grammar inference consumes primary lexical positions and formal atoms."""
    selected = source.value
    readings = FormalSourceReadings._from_retained(
        selected,
        tuple(
            (DataProductReference(product.semantic_id), product.inventory()) for product in formal
        ),
        tuple(row for product in formal for row in product.value["lexicon"]),
    )
    view = ConstructionSource.from_native(source)
    builder = ConstructionLayer(
        selected["source"],
        {"selectors": selected["selectors"]},
        {"key": "text.constructions/source-native"},
        families=(
            *FAMILIES,
            "construction.math_scope",
            "construction.navigation",
            *(("construction.named_rules",) if options.annotation_rules else ()),
        ),
    )
    atom_references = {}
    for product in formal:
        for packet in product.value["members"]:
            if packet["body"]["record_type"] == "occurrence":
                atom_references.setdefault(packet["member_id"], []).append(
                    {"product_id": product.semantic_id, "member_id": packet["member_id"]}
                )
    attempted = set()
    requested, unknown = _requested_regions(source)
    for selector in unknown:
        for family in GRAMMAR_FAMILIES:
            builder.record(family, selector, "unknown", "selected original ancestry is unavailable")
    regions = []
    for product in formal:
        for region in product.value["lexicon"]:
            regions.extend(
                (max(region["start"], a), min(region["end"], b))
                for a, b in requested
                if max(region["start"], a) < min(region["end"], b)
            )
    native_products = ()
    if native is not None:
        native_products = retained_source_annotation_products(source, native)
        boundaries = [
            {"start": row.start, "end": row.end}
            for product in native_products
            for row in product.sentences
        ]
        regions = _clip_sentence_regions(regions, boundaries)
        sentence_coverage = [
            row
            for row in json.loads(native.content)["coverage"]
            if row["family"] == "spacy.sentences"
        ]
        if not sentence_coverage or any(
            row["outcome"] not in {"complete", "empty"}
            or row["availability"] != "available"
            or row.get("unexamined")
            for row in sentence_coverage
        ):
            for family in GRAMMAR_FAMILIES:
                for selector in selected["selectors"]:
                    builder.record(
                        family,
                        selector,
                        "unknown",
                        "selected native sentence boundaries are incomplete",
                    )
    for start, end in regions:
        if (start, end) in attempted or start == end:
            continue
        attempted.add((start, end))
        try:
            atoms, terminals = readings.positioned(start=start, end=end)
        except ValueError as error:
            for family in GRAMMAR_FAMILIES:
                builder.record(
                    family,
                    dict(projection=view.projection, start=start, end=end),
                    "unsupported",
                    str(error),
                )
            continue
        result = builder.region(
            view,
            start,
            end,
            atoms,
            terminals=terminals,
            max_chars=options.max_region_chars,
            parse_seconds=options.parse_seconds,
            check_active=check_active,
        )
        if result.reducer is not None:
            for key, node in result.reducer.syntax.items():
                if node["kind"] == "grammar.terminal" and node["native_label"] == "ATOM":
                    supporting = [
                        atom
                        for atom in atoms
                        if (atom.start + start, atom.end + start) == (node["start"], node["end"])
                    ]
                    builder.annotations[key]["external_premises"] = [
                        ref
                        for atom in supporting
                        for ref in atom_references.get(atom.occurrence, ())
                    ]
    vocab = None
    if native is not None:
        from .constructions.matching import (
            PreparedConstructions,
            retained_native_documents,
            retained_native_vocab,
        )
        from .constructions.retained_rules import populate_source_reading_products

        vocab = retained_native_vocab(source, native)
        thresholds, _ = readings.fields(family="formal.threshold", start=0, end=len(view.text))
        by_start = {}
        for threshold in thresholds:
            if threshold.normalized["kind"] == "threshold" and threshold.normalized[
                "domain_status"
            ] in {"valid", "unresolved"}:
                by_start.setdefault(threshold.start, []).append(threshold)
        populate_source_reading_products(
            builder,
            view,
            source,
            native,
            annotation_products=native_products,
            formal_thresholds=by_start,
            vocab=vocab,
            check_active=check_active,
            admitted=lambda a, b: any(start <= a < b <= end for start, end in requested),
        )
        patterns = PreparedConstructions(vocab)
        for block, doc, annotations, start, _end in retained_native_documents(
            source, native, vocab
        ):
            check_active()
            # The working Doc retains the full original block. Only positively
            # selected original units participate; no dependency is rewritten.
            selected_annotations = {
                i: row
                for i, row in annotations.items()
                if any(
                    a <= start + doc[i].idx and start + doc[i].idx + len(doc[i]) <= b
                    for a, b in requested
                )
            }
            if not selected_annotations:
                continue
            _, unavailable = builder.native(view, block, doc, selected_annotations, start, patterns)
            if unavailable:
                for family in GRAMMAR_FAMILIES:
                    for selector in selected["selectors"]:
                        builder.record(family, selector, "partial", "; ".join(unavailable))
    from .constructions.navigation import populate_navigation_products

    populate_navigation_products(
        builder,
        view,
        source,
        native,
        annotation_products=native_products,
        check_active=check_active,
        admitted=lambda a, b: any(start <= a < b <= end for start, end in requested),
    )
    from .constructions.math_scope import populate_math_scope_products

    if native is None:
        vocab = None
    populate_math_scope_products(
        builder,
        view,
        source,
        native,
        formal,
        vocab,
        binders=options.math_scope_binders,
        rules=options.math_domain_rules,
        check_active=check_active,
        admitted=lambda a, b: any(start <= a < b <= end for start, end in requested),
    )
    if options.annotation_rules:
        from .constructions.named import NAMED_FAMILY, populate_named_products

        if native is None:
            for selector in selected["selectors"]:
                builder.record(
                    NAMED_FAMILY,
                    selector,
                    "unknown",
                    "named rules require retained native annotations",
                )
        else:
            assert vocab is not None
            populate_named_products(
                builder,
                view,
                source,
                native,
                PreparedAnnotationRules(vocab, rules=options.annotation_rules),
                annotation_products=native_products,
                check_active=check_active,
                admitted=lambda a, b: any(start <= a < b <= end for start, end in requested),
            )
    if native is None:
        for family in GRAMMAR_FAMILIES:
            for selector in selected["selectors"]:
                builder.record(
                    family,
                    selector,
                    "partial",
                    "native-dependent construction coverage unavailable; source grammar retained",
                )
    facts = builder.facts()
    support, formal_support = _stage_construction_support(facts, formal)
    value = interpreted_product_value(source, facts, member_contracts)
    return {
        **value,
        "annotation_support": support,
        "formal_support": formal_support,
    }


_BINDING_USES = {
    "named_binding_head",
    "named_binding_member",
    "named_binding_antecedent",
}
_ANNOTATION_USES = _BINDING_USES | {
    "external_premise",
    "basis_external_premise",
    "named_node",
    "navigation_token",
}


def _annotation_item(value) -> SemanticReference:
    reference = read_semantic_reference(value)
    key = reference.item_key
    if (
        reference.variant != "partition-item"
        or reference.role != "sentences"
        or reference.collection != "rows"
        or reference.occurrence is not None
        or key is None
        or len(key) != 2
        or key[0] not in {"sentence", "token"}
        or type(key[1]) is not int
        or key[1] < 0
    ):
        raise ValueError("annotation support requires an exact selected sentence or token item")
    return reference


def annotation_support_index(value):
    """Index primary annotation evidence by local graph owner and declared use."""
    result: dict[tuple[str, str, int | None], dict[int, SemanticReference]] = {}
    for row in value.get("annotation_support", ()):
        owner, use, position = row["owner"], row["use"], row["position"]
        binding = row.get("binding_position")
        if (
            use not in _ANNOTATION_USES
            or type(position) is not int
            or position < 0
            or (binding is not None and (type(binding) is not int or binding < 0))
            or ((binding is not None) != (use in _BINDING_USES))
        ):
            raise ValueError("annotation support has an invalid position or use")
        group = result.setdefault((owner, use, binding), {})
        if position in group:
            raise ValueError("annotation support repeats a graph slot")
        reference = _annotation_item(row["target"])
        if use not in {"external_premise", "basis_external_premise"} and (
            reference.item_key is None or reference.item_key[0] != "token"
        ):
            raise ValueError("named and navigation support requires a selected token item")
        group[position] = reference
    return {key: tuple(sorted(rows.items())) for key, rows in result.items()}


def _stage_construction_support(facts, formal):
    """Lift computed input references while retaining their exact graph positions."""
    references, formal_references = [], []
    positions = {product.semantic_id: position for position, product in enumerate(formal)}
    if len(positions) != len(formal):
        raise ValueError("construction repeats an original formal input")

    def entry(owner, use, position, value, binding=None):
        references.append(
            {
                "owner": owner,
                "use": use,
                "position": position,
                **({"binding_position": binding} if binding is not None else {}),
                "target": _annotation_item(value).values(),
            }
        )

    def split_premises(owner, use, record, field="external_premises"):
        if field not in record:
            return
        retained = []
        for position, value in enumerate(record[field]):
            if value.get("role") == "sentences" and field == "external_premises":
                entry(owner, use, position, value)
            elif value.get("product_id") in positions:
                formal_references.append(
                    dict(
                        owner=owner,
                        use=use,
                        position=position,
                        target=SemanticReference.member(
                            "formal",
                            value["member_id"],
                            occurrence=str(positions[value["product_id"]]),
                        ).values(),
                    )
                )
            else:
                retained.append(value)
        record[field] = retained

    nodes = (
        row
        for name, _ in _INVENTORIES
        for item in facts[name]
        for row in ((item, *item["members"]) if name == "choices" else (item,))
    )
    for node in nodes:
        owner = node["local_id"]
        split_premises(owner, "external_premise", node)
        split_premises(owner, "required_external_choice", node, "required_external_choices")
        if "basis" in node:
            node["basis"] = dict(node["basis"])
            split_premises(owner, "basis_external_premise", node["basis"])
            split_premises(
                owner, "basis_required_external_choice", node["basis"], "required_external_choices"
            )
        if "named_match" in node:
            named = node["named_match"] = dict(node["named_match"])
            for position, ref in enumerate(named.pop("nodes", ())):
                entry(owner, "named_node", position, ref)
            if "bindings" in named:
                named["bindings"] = [dict(row) for row in named["bindings"]]
            for binding, row in enumerate(named.get("bindings", ())):
                entry(owner, "named_binding_head", 0, row.pop("head"), binding)
                for name, use in (
                    ("members", "named_binding_member"),
                    ("antecedent_members", "named_binding_antecedent"),
                ):
                    for position, ref in enumerate(row.pop(name, ())):
                        entry(owner, use, position, ref, binding)
        if node.get("navigation", {}).get("native_tokens"):
            navigation = node["navigation"] = dict(node["navigation"])
            tokens = navigation["native_tokens"] = [
                dict(row) for row in navigation["native_tokens"]
            ]
            for position, token in enumerate(tokens):
                entry(owner, "navigation_token", position, token.pop("native_node"))
    return (
        sorted(
            references,
            key=lambda row: (
                row["owner"],
                row["use"],
                row.get("binding_position", -1),
                row["position"],
            ),
        ),
        sorted(formal_references, key=lambda row: (row["owner"], row["use"], row["position"])),
    )


def _annotation_dependency(body):
    return "execution_profile" in body and "block_coverage" in body


def _selected_annotation_blocks(selected):
    from .enriched_document_products import RetainedCharacterizationProduct

    native = []
    for product in selected:
        if type(product) is SourceAnnotations:
            native.append((product.value, product.partition_blocks))
        elif (
            type(product) is RetainedCharacterizationProduct
            and (blocks := product.partition_blocks) is not None
        ):
            native.append((product.value, blocks))
    return native


def verify_interpreted_annotation_support(support, items, layouts, annotations, nodes):
    """Authenticate graph slots against addresses and layouts from the admitted annotation."""
    for owner, use, binding in support:
        rows = support[owner, use, binding]
        node = _inventory_field(nodes, owner, None)
        if node is None or any(address not in items for _, address in rows):
            raise ValueError(
                "construction annotation support does not resolve an exact graph/item address"
            )
        named = _inventory_field(node, "named_match", None)
        if use in {"external_premise", "basis_external_premise"}:
            record = node if use == "external_premise" else _inventory_field(node, "basis", None)
            if record is None or any(
                position >= len(rows) + len(_inventory_field(record, "external_premises", ()))
                for position, _ in rows
            ):
                raise ValueError("construction annotation premise leaves its graph slot")
        elif use == "navigation_token":
            navigation = _inventory_field(node, "navigation", {})
            block = _inventory_field(navigation, "block", None)
            tokens = _inventory_field(navigation, "native_tokens", ())
            layout = _inventory_field(layouts, block, None)
            if (
                layout is None
                or _inventory_field(navigation, "annotation", None) != "annotation:" + layout
            ):
                raise ValueError("construction navigation lacks its exact original native block")
            if tuple(position for position, _ in rows) != tuple(range(len(tokens))) or any(
                address != (block, ("token", token["index"]))
                for (_, address), token in zip(rows, tokens, strict=True)
            ):
                raise ValueError("construction navigation support changes its native token layout")
        elif (
            named is None
            or (binding is not None and binding >= len(_inventory_field(named, "bindings", ())))
            or tuple(position for position, _ in rows) != tuple(range(len(rows)))
            or any(address[0] != named["block_id"] for _, address in rows)
        ):
            raise ValueError("named rule token leaves its exact original native block")

    for node in annotations:
        owner = node["local_id"]
        if named := _inventory_field(node, "named_match", None):
            if _inventory_field(layouts, named["block_id"], None) != named["dependency_digest"]:
                raise ValueError("named rule lacks its exact original native block")
            node_refs = _inventory_field(support, (owner, "named_node", None), ())
            if tuple(address[1] for _, address in node_refs) != tuple(
                ("token", row["token_index"]) for row in _inventory_field(named, "sentences", ())
            ) or any(
                len(_inventory_field(support, (owner, "named_binding_head", position), ())) != 1
                for position in range(len(_inventory_field(named, "bindings", ())))
            ):
                raise ValueError("named rule lacks its exact native node or binding head")
        tokens = _inventory_field(_inventory_field(node, "navigation", {}), "native_tokens", ())
        references = _inventory_field(support, (owner, "navigation_token", None), ())
        if len(references) != len(tokens):
            raise ValueError("construction navigation lacks its exact selected tokens")


def _validated_annotation_support(value, selected, annotations, nodes, *, established=False):
    support = annotation_support_index(value)
    if not support and not any(
        "named_match" in row or row.get("navigation", {}).get("native_tokens")
        for row in annotations
    ):
        return {}
    native = _selected_annotation_blocks(selected)
    if len(native) != 1:
        raise ValueError("construction requires its exact selected annotation partitions")
    # The contextual binding requires the producer's attestation. Its retained dependency
    # closure still requires this exact admitted annotation product.
    if not established:
        ((header, blocks),) = native
        requested = {ref.partition_key for rows in support.values() for _, ref in rows}
        items = {
            (block.key, (row["record_type"], row["ordinal"]))
            for block in blocks
            if block.key in requested
            for row in block.rows
        }
        layouts = {
            row["annotation"]["block_id"]: row["annotation"]["dependency_digest"]
            for row in header["block_layouts"]
        }
        verify_interpreted_annotation_support(
            {
                key: tuple((position, (ref.partition_key, ref.item_key)) for position, ref in rows)
                for key, rows in support.items()
            },
            items,
            layouts,
            annotations,
            nodes,
        )
    navigation = {}
    for node in annotations:
        owner = node["local_id"]
        if tokens := node.get("navigation", {}).get("native_tokens"):
            references = support.get((owner, "navigation_token", None), ())
            navigation[owner] = {
                **node,
                "external_premises": [
                    *node.get("external_premises", ()),
                    *(
                        ref.values()
                        for _, ref in support.get((owner, "external_premise", None), ())
                    ),
                ],
                "navigation": {
                    **node["navigation"],
                    "native_tokens": [
                        {**token, "native_node": ref.values()}
                        for token, (_, ref) in zip(tokens, references, strict=True)
                    ],
                },
            }
    return navigation


def interpreted_product_value(source, facts, member_contracts):
    """Package one actual graph inventory with original scope and genuine support."""
    selected = source.value
    facts["choice_members"] = [
        dict(group_id=group["local_id"], **member)
        for group in facts["choices"]
        for member in group["members"]
    ]
    coordinate = dict(selected["source"])
    selectors = [dict(selector) for selector in selected["selectors"]]
    context = dict(
        subject=source_subject(coordinate),
        subject_definition="original-source-view",
        original_source=coordinate["document"],
        analyzed_scope=dict(source=coordinate, selectors=selectors),
    )
    value = dict(
        source=coordinate,
        selectors=selectors,
        outcome=facts["outcome"],
        coverage=facts["coverage"],
        members=[
            dict(
                member_id=row["local_id"],
                kind_contract=member_contracts[tag],
                context=context,
                body={"record_type": tag, **row},
            )
            for name, tag in _MEMBER_VARIANTS
            for row in facts[name]
        ],
    )

    return append_manifest(value, member_contracts["construction_manifest"])


def verify_interpreted_literal_source(product, source):
    """Check interpreted occurrences against the selected source and examined scope."""
    if product["source"] != source["source"] or tuple(product["selectors"]) != tuple(
        source["selectors"]
    ):
        raise ValueError("construction product changes its exact original source/scope")
    text = source["text"]
    for packet in product["members"]:
        body = packet["body"]
        if body["record_type"] != "occurrence":
            continue
        for extent in body["extents"]:
            start, end = extent["start"], extent["end"]
            if not 0 <= start <= end <= len(text) or extent["text"] != text[start:end]:
                raise ValueError("construction occurrence changes original positioned source")


def verify_interpreted_body_coverage(coverage, outcome, inventory):
    """Check the agreement between analytical families and their reported standing."""
    covered_families = {row["family"] for row in coverage}
    if len(covered_families) != len(coverage):
        raise ValueError("construction repeats family coverage")
    analytical_families = {
        item["family"]
        for name in ("annotations", "memberships", "roles", "terms", "choices")
        for item in inventory[name]
    }
    if not analytical_families <= covered_families:
        raise ValueError("construction analytical family lacks declared coverage")
    for row in coverage:
        if row["outcome"] in {"complete", "empty"}:
            has_gap = row["availability"] != "available"
            if "unexamined" in row:
                has_gap = has_gap or bool(row["unexamined"])
            if has_gap or (row["eligible"] and not row["examined"]):
                raise ValueError("complete or empty family requires available examined coverage")
        if row["outcome"] == "empty" and row["family"] in analytical_families:
            raise ValueError("successful empty family contains analytical output")
    if outcome == "complete" and any(
        row["outcome"] not in {"complete", "empty"} for row in coverage
    ):
        raise ValueError("complete product contains incomplete family coverage")


def _interpreted_inventory(packets):
    inventory, all_nodes, alternatives, _ = admitted_characterization_graph(packets)
    indexes = {name: {row["local_id"]: row for row in inventory[name]} for name in inventory}
    choices = {address: alternatives[address][0] for address in alternatives}
    return inventory, indexes, all_nodes, choices


def verify_interpreted_inventory_topology(packets):
    """Check exact projected member links and structural cycles for an interpreted output."""
    inventory, indexes, all_nodes, choices = _interpreted_inventory(packets)
    validate_inventory_topology(inventory, indexes, all_nodes, choices)
    return inventory, indexes, all_nodes, choices


def verify_interpreted_source_coverage(coverage, source):
    """Check that complete families examine all eligible original ranges and atoms."""
    parents, pages = native_selector_facts(source["items"], source["ancestors"])
    for row in coverage:
        if row["outcome"] not in {"complete", "empty"}:
            continue
        eligible = native_selected_ranges(
            source, row["eligible"], parents, pages, include_unknown=True
        )
        examined = native_selected_ranges(source, row["examined"], parents, pages)
        eligible_atoms = native_selected_unprojected_atoms(
            source, row["eligible"], parents, pages, include_unknown=True
        )
        examined_atoms = native_selected_unprojected_atoms(source, row["examined"], parents, pages)
        if not eligible_atoms <= examined_atoms or any(
            not any(c <= a and b <= d for c, d in examined) for a, b in eligible
        ):
            raise ValueError("complete or empty family leaves eligible source scope unexamined")


def verify_interpreted_positioned_geometry(packets, source):
    """Bind occurrence geometry to the exact selected extents, pointers and piece placement."""
    parents, pages = native_selector_facts(source["items"], source["ancestors"])
    projection = source["source"]["projection"]
    limit = len(source["text"])
    pieces = source["pieces"]
    ends = tuple(piece["end"] for piece in pieces)
    native = tuple(piece for piece in pieces if piece["kind"] == "native_text")
    native_ends = tuple(piece["end"] for piece in native)
    for packet in packets:
        body = packet["body"]
        if body["record_type"] != "occurrence":
            continue
        for extent in body["extents"]:
            if (
                extent["projection"] != projection
                or not native_selector_covers_extent(
                    parents, pages, source["selectors"], extent, limit
                )
                or not matches_positioned_source_extent(pieces, ends, native, native_ends, extent)
            ):
                raise ValueError("construction occurrence changes original positioned source")


def verify_interpreted_dependency_members(product, nodes, dependencies, *, include_annotations):
    """Bind external graph premises and alternative choices to actual primary members."""
    external = {
        (product_id, packet["member_id"]): packet["body"]
        for product_id, dependency in dependencies
        if include_annotations or not _annotation_dependency(dependency)
        for packet in dependency["members"]
    }
    external_choices = {
        key for key, body in external.items() if body["record_type"] == "choice_member"
    }
    if "formal_support" in product:
        for packet in product["members"]:
            body = packet["body"]
            public_nodes = (body, *body["members"]) if body["record_type"] == "choice" else (body,)
            for public in public_nodes:
                for record in (public, _inventory_field(public, "basis", {})):
                    if any(
                        _inventory_field(record, field, ())
                        for field in ("external_premises", "required_external_choices")
                    ):
                        raise ValueError("construction product retains a computed formal input pin")
    for address in nodes:
        node = nodes[address]
        basis = _inventory_field(node, "basis", {})
        for ref in (
            *_inventory_field(node, "external_premises", ()),
            *_inventory_field(basis, "external_premises", ()),
        ):
            if (ref["product_id"], ref["member_id"]) not in external:
                raise ValueError("construction has dangling primary semantic member premise")
        for ref in (
            *_inventory_field(node, "required_external_choices", ()),
            *_inventory_field(basis, "required_external_choices", ()),
        ):
            if (ref["product_id"], ref["member_id"]) not in external_choices:
                raise ValueError("construction requires an actual primary choice alternative")


@overload
def validate_interpreted_product[Product: InterpretedProduct](
    prepared,
    model,
    value,
    source,
    formal,
    *,
    product_type: type[Product],
    subject_context=None,
    contextual_proxy_inputs=None,
    contextual_roles=None,
) -> Product: ...


@overload
def validate_interpreted_product(
    prepared,
    model,
    value,
    source,
    formal,
    *,
    subject_context=None,
    contextual_proxy_inputs=None,
    contextual_roles=None,
) -> ConstructionProduct: ...


def validate_interpreted_product(
    prepared,
    model,
    value,
    source,
    formal,
    *,
    product_type: type[InterpretedProduct] = ConstructionProduct,
    subject_context=None,
    contextual_proxy_inputs=None,
    contextual_roles=None,
):
    return _checked_interpreted_product(
        prepared,
        model,
        value,
        source,
        formal,
        product_type=product_type,
        subject_context=subject_context,
        contextual_proxy_inputs=contextual_proxy_inputs,
        contextual_roles=contextual_roles,
    )


def _checked_interpreted_product[Product: InterpretedProduct](
    prepared,
    model,
    value,
    source,
    formal,
    *,
    product_type: type[Product],
    subject_context=None,
    contextual_proxy_inputs=None,
    bound_member=None,
    contextual_roles=None,
) -> Product:
    from .data_operation_ports import project_product_members
    from .data_operation_values import semantic_value

    typed = prepared.validate_json(product_type.kind_name, canonical_bytes(value))
    checked = typed.model_dump(mode="json", exclude_unset=True)
    typed_value = typed.model_dump(mode="python", exclude_unset=True)
    kind = prepared.index.definitions[product_type.kind_name].iri
    kind_contract = next(
        item.key for item in model.identities if (item.owner, item.domain) == (kind, "kind")
    )
    body_digest = body_identity(typed_value).key
    graph_value = checked
    parents = ()
    contextual_parents = ()
    if product_type is ConstructionProduct:
        from .construction_formal_references import (
            construction_formal_parents,
            project_construction_formal_support,
        )

        parents = (
            tuple(
                (str(position), item.semantic_id)
                for position, item in enumerate(formal)
                if not _annotation_dependency(item.value)
            )
            if bound_member is None
            else construction_formal_parents(bound_member)
        )
        graph_value = project_construction_formal_support(checked, parents)
    if contextual_proxy_inputs is not None:
        from .contextual_proxy_references import project_contextual_proxy_graph

        graph_value = project_contextual_proxy_graph(checked, contextual_proxy_inputs)
    if product_type is ContextualMeaningProduct:
        from .contextual_input_references import (
            contextual_input_parents,
            project_contextual_input_support,
        )

        if bound_member is None:
            if contextual_roles is None:
                raise ValueError("contextual graph requires its exact producing input roles")
            contextual_parents = tuple(
                (role, str(position), product.semantic_id)
                for role, products in contextual_roles.items()
                for position, product in enumerate(products)
            )
        else:
            contextual_parents = contextual_input_parents(bound_member)
        graph_value = project_contextual_input_support(checked, contextual_parents)
    packets = analytical_packets(
        graph_value,
        manifest_contract(prepared, model, product_type.manifest_name),
    )
    selected = source.value
    if bound_member is None:
        verify_interpreted_literal_source(checked, selected)
    elif (
        subject_context is None
        or bound_member.kind_contract != kind_contract
        or bound_member.member is not None
        or contextual_product_identity(
            kind=kind_contract, context=subject_context, body=body_digest
        ).key
        != bound_member.product
        or checked["source"] != selected["source"]
        or tuple(checked["selectors"]) != tuple(selected["selectors"])
    ):
        raise ValueError("construction body differs from its exact selected native product/source")
    contracts = interpreted_member_contracts(prepared, model)
    inventory, indexes, all_nodes, _ = (
        verify_interpreted_inventory_topology(packets)
        if bound_member is None
        else _interpreted_inventory(packets)
    )
    context = dict(
        subject=source_subject(selected["source"]),
        subject_definition="original-source-view",
        original_source=selected["source"]["document"],
        analyzed_scope=dict(source=selected["source"], selectors=list(selected["selectors"])),
    )
    for packet in packets:
        if (
            packet["kind_contract"] != contracts[packet["body"]["record_type"]]
            or packet["context"] != context
        ):
            raise ValueError("construction packet changes admitted nominal meaning or identity")
    if bound_member is None:
        verify_inventory_occurrence_ids(checked)
        verify_interpreted_positioned_geometry(packets, selected)
    if bound_member is None:
        dependencies = tuple((product.semantic_id, product.value) for product in formal)
        verify_interpreted_dependency_members(
            checked,
            all_nodes,
            dependencies,
            include_annotations=product_type is not ConstructionProduct,
        )
    navigation = (
        _validated_annotation_support(
            checked,
            formal,
            inventory["annotations"],
            all_nodes,
            established=bound_member is not None,
        )
        if product_type is ConstructionProduct
        else {}
    )
    if bound_member is None:
        verify_navigation_source_fields(indexes)
    validate_navigation_token_premises(indexes["annotations"] | navigation)
    if bound_member is None:
        policies = attachment_policies(prepared)

        for role in inventory["roles"]:
            validate_attachment_basis(
                role["basis"],
                policies,
                lambda name, body: prepared.validate_json(
                    "DdoSemantic" + name.removeprefix("Characterization"), canonical_bytes(body)
                ),
            )
        verify_interpreted_attachment_witnesses(inventory["roles"], all_nodes, policies)
    if bound_member is None:
        verify_inventory_native_scores(packets)
        verify_interpreted_body_coverage(checked["coverage"], checked["outcome"], inventory)
        verify_interpreted_source_coverage(checked["coverage"], selected)
    payload = _InterpretedPayload(
        canonical_bytes(checked),
        freeze_native(checked),
        freeze_native({name: inventory[name] for name, _ in _INVENTORIES}),
        canonical_bytes(semantic_value(typed_value)),
        project_product_members(model, kind, typed_value),
        body_digest,
        kind_contract,
        parents,
        contextual_parents,
        tuple(product.semantic_id for product in formal),
    )
    return product_type._from_payload(payload, source, prepared, model, subject_context)


def _original_construction_dependencies(member, products):
    """Require the full original formal/annotation roles from one acquired producer."""
    from .construction_formal_references import construction_input_parents

    inputs = construction_input_parents(member)
    available = {product.semantic_id: product for product in products}
    if len(available) != len(products) or any(product not in available for _, _, product in inputs):
        raise ValueError("construction lacks its exact retained dependency closure")
    return tuple(available[product] for _, _, product in inputs)


def validate_construction_product(prepared, model, value, source, formal, *, subject_context=None):
    return validate_interpreted_product(
        prepared,
        model,
        value,
        source,
        tuple(formal),
        product_type=ConstructionProduct,
        subject_context=subject_context,
    )


def acquired_construction_product(
    prepared,
    model,
    value,
    source,
    formal,
    *,
    subject_context: SubjectContext,
    member: BoundRoleMember,
):
    """Read the exact whole construction after native binding established its required rules."""
    if type(member) is not BoundRoleMember:
        raise TypeError("selected construction requires its acquired native binding member")
    return _checked_interpreted_product(
        prepared,
        model,
        value,
        source,
        _original_construction_dependencies(member, formal),
        product_type=ConstructionProduct,
        subject_context=subject_context,
        bound_member=member,
    )


@dataclass(frozen=True)
class PreparedConstructionProfile:
    prepared: PreparedRelease
    model: EffectiveDataOperationModel

    def run(
        self,
        source: FrozenNativeSource,
        formal: tuple[FormalEvidenceProduct, ...],
        options: ConstructionOptions | None = None,
        *,
        sentences: SourceAnnotations | None = None,
        check_active: Callable[[], None] = lambda: None,
        subject_context: SubjectContext | None = None,
    ):
        options = ConstructionOptions() if options is None else options
        source = FrozenNativeSource.acquire(self.prepared, source)
        if sentences is not None:
            sentences = verify_source_annotation_carrier(
                self.prepared, self.model, sentences, source
            )
        FormalSourceReadings.from_products(formal, source, prepared=self.prepared, model=self.model)
        return self._construct(
            source,
            tuple(sorted(formal, key=lambda product: product.semantic_id)),
            options,
            sentences=sentences,
            check_active=check_active,
            subject_context=subject_context,
        )

    def _construct(
        self,
        source: FrozenNativeSource,
        formal: tuple[FormalEvidenceProduct, ...],
        options: ConstructionOptions,
        *,
        sentences: SourceAnnotations | None,
        check_active: Callable[[], None],
        subject_context: SubjectContext | None = None,
    ):
        snapshots = tuple(CharacterizationSnapshot.from_product(product) for product in formal)
        native = CharacterizationSnapshot.from_product(sentences) if sentences is not None else None
        value = construction_product_values(
            source,
            snapshots,
            options,
            interpreted_member_contracts(self.prepared, self.model),
            native=native,
            check_active=check_active,
        )
        return validate_construction_product(
            self.prepared,
            self.model,
            value,
            source,
            (*formal, *((sentences,) if sentences is not None else ())),
            subject_context=subject_context,
        )


@dataclass(frozen=True, init=False)
class ContextualMeaningProduct(InterpretedProduct):
    kind_name: ClassVar[str] = "DdoContextualMeaningProduct"
    manifest_name: ClassVar[str] = "DdoContextualManifest"

    @property
    def contextual_input_parents(self):
        self._require_acquired()
        return self._payload.contextual_input_parents


@dataclass(frozen=True)
class PreparedContextualProfile:
    prepared: PreparedRelease
    model: EffectiveDataOperationModel

    def run(
        self,
        source: FrozenNativeSource,
        constructions: tuple[ConstructionProduct, ...],
        formal: tuple[FormalEvidenceProduct, ...],
        *,
        roots=None,
        env=None,
        supporting=(),
        check_active=lambda: None,
        subject_context: SubjectContext | None = None,
        max_nodes=20000,
    ):
        source = FrozenNativeSource.acquire(self.prepared, source)
        FormalSourceReadings.from_products(formal, source, prepared=self.prepared, model=self.model)
        for product in constructions:
            if type(product) is not ConstructionProduct:
                raise TypeError("contextual inputs require acquired construction products")
            product.require_readable_from(source, self.model, (*formal, *supporting))
        return self._evaluate(
            source,
            tuple(sorted(constructions, key=lambda product: product.semantic_id)),
            tuple(sorted(formal, key=lambda product: product.semantic_id)),
            roots=roots,
            env=env,
            supporting=tuple(sorted(supporting, key=lambda product: product.semantic_id)),
            check_active=check_active,
            subject_context=subject_context,
            max_nodes=max_nodes,
        )

    def _evaluate(
        self,
        source,
        constructions,
        formal,
        *,
        roots=None,
        env=None,
        supporting=(),
        check_active,
        subject_context=None,
        max_nodes=20000,
    ):
        for product in supporting:
            if product.value["source"] != source.value["source"]:
                raise ValueError("context support belongs to another original source")
        roles = dict(formal=formal, supporting=supporting, constructions=constructions)
        products = (*formal, *supporting, *constructions)
        symbolic = tuple(product.reference for product in constructions)
        snapshots = tuple(CharacterizationSnapshot.from_product(product) for product in products)
        value = contextual_product_values(
            source,
            snapshots,
            symbolic,
            interpreted_member_contracts(self.prepared, self.model),
            roots=roots,
            env=env,
            check_active=check_active,
            max_nodes=max_nodes,
            input_roles={
                role: tuple(CharacterizationSnapshot.from_product(product) for product in values)
                for role, values in roles.items()
            },
        )
        return validate_interpreted_product(
            self.prepared,
            self.model,
            value,
            source,
            products,
            product_type=ContextualMeaningProduct,
            subject_context=subject_context,
            contextual_roles=roles,
        )


def contextual_product_values(
    source: FrozenNativeSource,
    products: tuple[CharacterizationSnapshot, ...],
    symbolic: tuple[DataProductReference, ...],
    contracts: dict[str, str],
    *,
    roots=None,
    env=None,
    check_active: Callable[[], None] = lambda: None,
    max_nodes=20000,
    input_roles=None,
) -> dict[str, Any]:
    from .constructions.evaluation import ContextualEvaluator, environment

    evaluator = ContextualEvaluator.from_products(
        source, products, check_active=check_active, max_nodes=max_nodes, symbolic_products=symbolic
    )
    env = environment() if env is None else env
    roots = evaluator.default_roots(env) if roots is None else tuple(roots)
    if any(
        not isinstance(ref.product, DataProductReference)
        for ref in (*roots, *env.hypotheses, *env.proposals, *env.choices)
    ) or any(not isinstance(pin, DataProductReference) for pin in env.context_layers):
        raise ValueError("source-native contextual evaluation requires governed semantic addresses")
    selected = source.value
    selectors = [dict(selector) for selector in selected["selectors"]]
    facts: dict[str, Any] = evaluator.facts(
        {"selectors": selectors},
        {"key": "text.contextual_evaluation/source-native"},
        roots,
        env,
    )
    facts["choice_members"] = [
        dict(group_id=group["local_id"], **member)
        for group in facts["choices"]
        for member in group["members"]
    ]
    coordinate = dict(selected["source"])
    context = dict(
        subject=source_subject(coordinate),
        subject_definition="original-source-view",
        original_source=coordinate["document"],
        analyzed_scope=dict(source=coordinate, selectors=selectors),
    )
    value = dict(
        source=coordinate,
        selectors=selectors,
        dependencies=[DataProductReference(product.semantic_id).values() for product in products],
        outcome=facts["outcome"],
        coverage=facts["coverage"],
        members=[
            dict(
                member_id=row["local_id"],
                kind_contract=contracts[tag],
                context=context,
                body={"record_type": tag, **row},
            )
            for name, tag in _MEMBER_VARIANTS
            for row in facts[name]
        ],
        roots=[ref.values() for ref in roots],
        environment=dict(
            context_products=[pin.values() for pin in env.context_layers],
            hypotheses=[ref.values() for ref in env.hypotheses],
            proposals=[ref.values() for ref in env.proposals],
            choices=[ref.values() for ref in env.choices],
            bindings=[binding.values() for binding in env.bindings],
            attribution=[ref.values() for ref in env.attribution],
        ),
    )
    from .contextual_input_references import pack_contextual_input_support

    if input_roles is None:
        symbolic_ids = {pin.product_id for pin in symbolic}
        input_roles = {
            "constructions": tuple(
                product for product in products if product.semantic_id in symbolic_ids
            ),
            "supporting": tuple(
                product for product in products if _annotation_dependency(product.value)
            ),
            "formal": tuple(
                product
                for product in products
                if product.semantic_id not in symbolic_ids
                and not _annotation_dependency(product.value)
            ),
        }
    return pack_contextual_input_support(
        append_manifest(value, contracts["contextual_manifest"]), input_roles
    )
