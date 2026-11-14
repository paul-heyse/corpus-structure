"""Ordinary symbolic constructions from retained primary source characterizations.

The grammar/reducer and local graph checks are shared with the released legacy
projection. Native admission, execution recipes and physical receipts stay outside
these source-addressed semantic facts.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .characterization import (
    attachment_policies,
    occurrence_id,
    validate_attachment_basis,
    validate_inventory_graph,
)
from .constructions.declarations import FAMILIES, GRAMMAR_FAMILIES
from .constructions.layers import ConstructionLayer, ConstructionSource
from .data_operation_identity import body_identity, contextual_product_identity
from .data_operation_model import EffectiveDataOperationModel, SubjectContext
from .data_product_reference import DataProductReference, member_reference, reference_inputs
from .formal_products import FormalEvidenceProduct, formal_product_inputs
from .formal_readings import FormalSourceReadings
from .identity import canonical_bytes
from .sentence_products import SourceAnnotations, SourceAnnotationReadings, sentence_product_inputs
from .source_products import FrozenNativeSource, source_subject
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
    family = {"CharacterizationAttachmentBasis"}
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
                key: (
                    "DdoSemanticMemberReference"
                    if key == "range" and item == "CharacterizationQualifiedReference"
                    else retarget(item)
                )
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [retarget(item) for item in value]
        return value

    for name in sorted(family):
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


def interpreted_member_contracts(prepared, model):
    identities = {(item.owner, item.domain): item.key for item in model.identities}
    result = {}
    for definition in prepared.definitions:
        if "DdoInterpretedMember" not in definition.ancestors or definition.abstract:
            continue
        tag = next(
            prop.equals_string for prop in definition.properties if prop.name == "record_type"
        )
        if tag is None or tag in result:
            raise ValueError("construction members require unique nominal discriminators")
        result[tag] = identities[definition.iri, "kind"]
    if set(result) != {tag for _, tag in _MEMBER_VARIANTS}:
        raise ValueError("construction member contracts differ from actual inventories")
    return result


@dataclass(frozen=True)
class InterpretedProduct:
    kind_name: ClassVar[str]
    content: bytes
    prepared: PreparedRelease
    model: EffectiveDataOperationModel
    subject_context: SubjectContext | None = None

    def _publication_context(self):
        if self.subject_context is None:
            raise ValueError(
                "native product identity requires an explicit acquired subject context"
            )
        return self.subject_context

    @property
    def value(self):
        return self.prepared.validate_json(self.kind_name, self.content)

    @property
    def semantic_id(self):
        kind = next(
            item.key
            for item in self.model.identities
            if item.owner == self.prepared.index.definitions[self.kind_name].iri
            and item.domain == "kind"
        )
        value = self.value.model_dump(mode="python", exclude_unset=True)
        return contextual_product_identity(
            kind=kind, context=self._publication_context(), body=body_identity(value).key
        ).key

    @property
    def reference(self):
        return DataProductReference(self.semantic_id)

    def inventory(self):
        result = {name: [] for name, _ in _INVENTORIES}
        names = {tag: name for name, tag in _INVENTORIES}
        for packet in json.loads(self.content)["members"]:
            if packet["body"]["record_type"] != "choice_member":
                result[names[packet["body"]["record_type"]]].append(packet["body"])
        return result


@dataclass(frozen=True)
class ConstructionProduct(InterpretedProduct):
    kind_name: ClassVar[str] = "DdoConstructionProduct"


@dataclass(frozen=True)
class CharacterizationSnapshot:
    """Private owned kernel transfer, derived from parent-validated nominal products."""

    product_id: str
    content: bytes

    @property
    def semantic_id(self):
        return self.product_id

    def inventory(self):
        body = json.loads(self.content)
        result = {name: [] for name, _ in _INVENTORIES}
        result["source_facts"] = []
        names = {tag: name for name, tag in _INVENTORIES}
        for packet in body.get("members", ()):
            tag = packet["body"]["record_type"]
            if tag in names:
                result[names[tag]].append(packet["body"])
            elif tag != "choice_member":
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
                if intervals and all(
                    row["kind"] != "native_text"
                    for row in selected["pieces"]
                    if intervals[-1][1] < row["end"] and row["start"] < a
                ):
                    intervals[-1] = (intervals[-1][0], b)
                else:
                    intervals.append((a, b))
        result.extend(intervals)
    return tuple(result), tuple(unknown)


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
        tuple(row for product in formal for row in json.loads(product.content)["lexicon"]),
    )
    view = ConstructionSource.from_native(source)
    builder = ConstructionLayer(
        selected["source"],
        {"selectors": selected["selectors"]},
        {"key": "text.constructions/source-native"},
        semantic=True,
    )
    atom_references = {}
    for product in formal:
        for packet in json.loads(product.content)["members"]:
            if packet["body"]["record_type"] == "occurrence":
                atom_references.setdefault(packet["member_id"], []).append(
                    member_reference(
                        DataProductReference(product.semantic_id), packet["member_id"]
                    ).values()
                )
    attempted = set()
    requested, unknown = _requested_regions(source)
    for selector in unknown:
        for family in FAMILIES:
            builder.record(family, selector, "unknown", "selected original ancestry is unavailable")
    regions = []
    for product in formal:
        for region in json.loads(product.content)["lexicon"]:
            regions.extend(
                (max(region["start"], a), min(region["end"], b))
                for a, b in requested
                if max(region["start"], a) < min(region["end"], b)
            )
    if native is not None:
        native_body = json.loads(native.content)
        boundaries = [
            packet["body"]
            for packet in native_body["members"]
            if packet["body"]["record_type"] == "sentence"
        ]
        regions = [
            (max(a, row["start"]), min(b, row["end"]))
            for a, b in regions
            for row in boundaries
            if max(a, row["start"]) < min(b, row["end"])
        ]
        if native_body["outcome"] != "complete":
            for family in FAMILIES:
                for selector in selected["selectors"]:
                    builder.record(
                        family,
                        selector,
                        "unknown",
                        "selected native sentence characterization is incomplete",
                    )
    for start, end in regions:
        if (start, end) in attempted or start == end:
            continue
        attempted.add((start, end))
        try:
            atoms, terminals = readings.positioned(start=start, end=end)
        except ValueError as error:
            for family in FAMILIES:
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
    if native is not None:
        from .constructions.matching import (
            PreparedConstructions,
            retained_native_documents,
            retained_native_vocab,
        )

        vocab = retained_native_vocab(source, native)
        patterns = PreparedConstructions(vocab)
        pin = DataProductReference(native.semantic_id)
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
            _, unavailable = builder.native(
                view, pin, block, doc, selected_annotations, start, patterns
            )
            if unavailable:
                for family in FAMILIES:
                    for selector in selected["selectors"]:
                        builder.record(family, selector, "partial", "; ".join(unavailable))
    if native is None:
        for family in GRAMMAR_FAMILIES:
            for selector in selected["selectors"]:
                builder.record(
                    family,
                    selector,
                    "partial",
                    "native-dependent construction coverage unavailable; source grammar retained",
                )
    facts: dict[str, Any] = builder.facts()
    facts["choice_members"] = [
        dict(group_id=group["local_id"], **member)
        for group in facts["choices"]
        for member in group["members"]
    ]
    coordinate = selected["source"]
    context = dict(
        subject=source_subject(coordinate),
        original_source=coordinate["document"],
        analyzed_scope=dict(source=coordinate, selectors=selected["selectors"]),
    )
    return dict(
        source=coordinate,
        selectors=selected["selectors"],
        dependencies=[
            DataProductReference(product.semantic_id).values()
            for product in (*formal, *((native,) if native is not None else ()))
        ],
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


def validate_interpreted_product(
    prepared,
    model,
    value,
    source,
    formal,
    *,
    product_type=ConstructionProduct,
    subject_context=None,
):
    checked = prepared.validate_json(product_type.kind_name, canonical_bytes(value)).model_dump(
        mode="json", exclude_unset=True
    )
    selected = source.value
    if checked["source"] != selected["source"] or checked["selectors"] != selected["selectors"]:
        raise ValueError("construction product changes its exact original source/scope")
    expected_dependencies = [
        DataProductReference(product.semantic_id).values() for product in formal
    ]
    if checked.get("dependencies", []) != expected_dependencies:
        raise ValueError("construction product changes selected primary dependencies")
    contracts = interpreted_member_contracts(prepared, model)
    inventory = {name: [] for name, _ in _INVENTORIES}
    names = {tag: name for name, tag in _INVENTORIES}
    context = dict(
        subject=source_subject(selected["source"]),
        original_source=selected["source"]["document"],
        analyzed_scope=dict(source=selected["source"], selectors=selected["selectors"]),
    )
    seen = set()
    for packet in checked.get("members", []):
        row = packet["body"]
        if (
            packet["kind_contract"] != contracts[row["record_type"]]
            or packet["member_id"] != row["local_id"]
            or packet["context"] != context
            or packet["member_id"] in seen
        ):
            raise ValueError("construction packet changes admitted nominal meaning or identity")
        seen.add(packet["member_id"])
        if row["record_type"] != "choice_member":
            inventory[names[row["record_type"]]].append(row)
    expected_alternatives = {
        member["local_id"]: dict(record_type="choice_member", group_id=group["local_id"], **member)
        for group in inventory["choices"]
        for member in group["members"]
    }
    actual_alternatives = {
        packet["member_id"]: packet["body"]
        for packet in checked["members"]
        if packet["body"]["record_type"] == "choice_member"
    }
    if expected_alternatives != actual_alternatives:
        raise ValueError("alternative member projection differs from owning packed choice group")
    indexes = {name: {row["local_id"]: row for row in rows} for name, rows in inventory.items()}
    all_nodes = {key: row for index in indexes.values() for key, row in index.items()}
    choices = {}
    for group in inventory["choices"]:
        for member in group["members"]:
            if member["local_id"] in all_nodes:
                raise ValueError("construction repeats a packed choice identity")
            choices[member["local_id"]] = group
            all_nodes[member["local_id"]] = member
    for occurrence in inventory["occurrences"]:
        if occurrence["local_id"] != occurrence_id(selected["source"], occurrence["extents"]):
            raise ValueError("construction occurrence changes original source identity")
        for extent in occurrence["extents"]:
            if (
                extent["projection"] != selected["source"]["projection"]
                or extent["text"] != selected["text"][extent["start"] : extent["end"]]
                or not any(
                    piece.get("item_ref") == extent["native_pointer"]
                    and piece["start"] <= extent["start"] <= extent["end"] <= piece["end"]
                    for piece in selected["pieces"]
                )
            ):
                raise ValueError("construction occurrence changes original positioned source")
    external = {
        (product.semantic_id, packet["member_id"])
        for product in formal
        for packet in json.loads(product.content)["members"]
    }
    for node in all_nodes.values():
        basis = node.get("basis", {})
        for ref in (
            *node.get("external_premises", ()),
            *node.get("required_external_choices", ()),
            *basis.get("external_premises", ()),
            *basis.get("required_external_choices", ()),
        ):
            if (ref["product_id"], ref["member_id"]) not in external:
                raise ValueError("construction has dangling primary semantic member premise")
    policies = attachment_policies(prepared)

    def validate_basis(basis):
        validate_attachment_basis(
            basis,
            policies,
            lambda name, body: prepared.validate_json(
                "DdoSemantic" + name.removeprefix("Characterization"), canonical_bytes(body)
            ),
        )
        return (
            policies.get("released_construction", {}).get("rules", {}).get(basis.get("rule_id"), {})
        )

    validate_inventory_graph(inventory, indexes, all_nodes, choices, validate_basis)
    return product_type(canonical_bytes(checked), prepared, model, subject_context)


def validate_construction_product(prepared, model, value, source, formal, *, subject_context=None):
    available = {product.semantic_id: product for product in formal}
    requested = [row["product_id"] for row in value.get("dependencies", ())]
    if len(set(requested)) != len(requested) or any(key not in available for key in requested):
        raise ValueError("construction lacks its exact retained dependency closure")
    selected = tuple(available[key] for key in requested)
    return validate_interpreted_product(
        prepared, model, value, source, selected, subject_context=subject_context
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
        source = FrozenNativeSource.acquire(self.prepared, source.value)
        FormalSourceReadings.from_products(formal, source)
        snapshots = tuple(
            CharacterizationSnapshot(product.semantic_id, product.content) for product in formal
        )
        native = None
        if sentences is not None:
            SourceAnnotationReadings(sentences, source)
            native = CharacterizationSnapshot(sentences.semantic_id, sentences.content)
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


@dataclass(frozen=True)
class ContextualMeaningProduct(InterpretedProduct):
    kind_name: ClassVar[str] = "DdoContextualMeaningProduct"


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
        source = FrozenNativeSource.acquire(self.prepared, source.value)
        FormalSourceReadings.from_products(formal, source)
        for product in supporting:
            if (
                product.value.model_dump(mode="json", exclude_unset=True)["source"]
                != source.value["source"]
            ):
                raise ValueError("context support belongs to another original source")
        checked = tuple(
            validate_construction_product(
                self.prepared,
                self.model,
                json.loads(product.content),
                source,
                (*formal, *supporting),
                subject_context=product.subject_context,
            )
            for product in constructions
        )
        products = (*formal, *supporting, *checked)
        symbolic = tuple(product.reference for product in checked)
        snapshots = tuple(
            CharacterizationSnapshot(product.semantic_id, product.content) for product in products
        )
        value = contextual_product_values(
            source,
            snapshots,
            symbolic,
            interpreted_member_contracts(self.prepared, self.model),
            roots=roots,
            env=env,
            check_active=check_active,
            max_nodes=max_nodes,
        )
        return validate_interpreted_product(
            self.prepared,
            self.model,
            value,
            source,
            products,
            product_type=ContextualMeaningProduct,
            subject_context=subject_context,
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
    facts: dict[str, Any] = evaluator.facts(
        {"selectors": selected["selectors"]},
        {"key": "text.contextual_evaluation/source-native"},
        roots,
        env,
    )
    facts["choice_members"] = [
        dict(group_id=group["local_id"], **member)
        for group in facts["choices"]
        for member in group["members"]
    ]
    coordinate = selected["source"]
    context = dict(
        subject=source_subject(coordinate),
        original_source=coordinate["document"],
        analyzed_scope=dict(source=coordinate, selectors=selected["selectors"]),
    )
    value = dict(
        source=coordinate,
        selectors=selected["selectors"],
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
    return value
