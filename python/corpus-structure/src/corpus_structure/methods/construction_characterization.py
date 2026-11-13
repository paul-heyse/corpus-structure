"""Shared construction and packed symbolic production from exact retained evidence."""

from __future__ import annotations

import json
import time
from collections.abc import Iterable
from functools import lru_cache
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from spacy.lang.en import English

from corpus_structure.core._model.shapes import Cost
from corpus_structure.core.method import Digest, Resources, UnitRef, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.ingest.annotations import AnnotationUnavailable
from corpus_structure.semantic.characterization_ports import execute_construction_profile
from corpus_structure.semantic.construction_products import ConstructionProduct
from corpus_structure.semantic.constructions import FAMILIES, ConstructionLayer, ProtectedAtom
from corpus_structure.semantic.constructions.declarations import GRAMMAR_FAMILIES
from corpus_structure.semantic.constructions.matching import (
    PreparedConstructions,
    retained_documents,
)
from corpus_structure.semantic.constructions.math_scope import Binders, NativeDomainRule
from corpus_structure.semantic.constructions.nodes import identity
from corpus_structure.semantic.constructions.resources import construction_digest
from corpus_structure.semantic.formal_products import FormalEvidenceProduct
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.sentence_products import SentenceInventory
from corpus_structure.semantic.source_products import FrozenNativeSource

from .annotation_rules import AnnotationRule, PreparedAnnotationRules


@lru_cache(maxsize=1)
def _construction_resources():
    vocab = English().vocab
    return vocab, PreparedConstructions(vocab)


@lru_cache(maxsize=16)
def _named_resources(content: bytes):
    vocab, _prepared = _construction_resources()
    rules = tuple(AnnotationRule.model_validate(value) for value in json.loads(content))
    return PreparedAnnotationRules(vocab, rules=rules)


class ConstructionConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    characterization_base_document: dict[str, Any] | None = None
    characterization_source_scope: dict[str, Any] | None = None
    characterization_layers: tuple[dict[str, Any], ...] = ()
    characterization_profile: Literal["symbolic_constructions"] = "symbolic_constructions"
    model: Literal["none"] = "none"
    grammar: str = Field(default_factory=construction_digest)
    context: str = "retained-native-sentences-and-source-pieces-1"
    max_region_chars: int = Field(default=4096, ge=1, le=32768)
    parse_seconds: float = Field(default=2.0, gt=0, le=120)
    annotation_rules: tuple[AnnotationRule, ...] = ()
    math_scope_binders: Binders | None = None
    math_domain_rules: tuple[NativeDomainRule, ...] = ()

    @model_validator(mode="after")
    def resource_identity(self):
        if self.grammar != construction_digest():
            raise ValueError(
                "construction configuration differs from executable grammar and pattern resources"
            )
        return self

    def require_selection(self):
        if (
            self.characterization_base_document is None
            or self.characterization_source_scope is None
        ):
            raise ValueError("construction production requires an exact base and source scope")
        pins = tuple(ProductReference(**p) for p in self.characterization_layers)
        if len(set(pins)) != len(pins):
            raise ValueError("construction dependencies must be distinct exact pins")
        return (
            ProductReference(**self.characterization_base_document),
            self.characterization_source_scope,
            pins,
        )

    @property
    def families(self):
        return (
            *FAMILIES,
            "construction.navigation",
            *(("construction.named_rules",) if self.annotation_rules else ()),
            "construction.math_scope",
        )


class ConstructionCharacterizationMethod:
    name = "text.constructions"
    version = "1"
    family = MethodFamily.EXTRACT
    unit_type = TaskUnitType.DOCUMENT
    tier = MethodTier.DETERMINISTIC
    confidence_source = None
    Config = ConstructionConfig
    resources = Resources(worker="cpu", batch_size=1, max_concurrency=1)

    @staticmethod
    def select(run, cfg: ConstructionConfig) -> Iterable[UnitRef]:
        base, scope, _ = cfg.require_selection()
        refs = [run.reader.source_view_ref(identity) for identity in scope["source_view_ids"]]
        if not refs or any(r is None or r.native_product != base for r in refs):
            raise ValueError("construction source scope is outside its selected base")
        documents = {r.document_id for r in refs if r is not None}
        if len(documents) != 1:
            raise ValueError("construction operation requires one document")
        return (UnitRef(TaskUnitType.DOCUMENT, next(iter(documents))),)

    def input_digest(self, unit, cfg):
        cfg.require_selection()
        return Digest(
            canonical_bytes(
                dict(
                    method=self.name,
                    version=self.version,
                    release_id=unit.run.reader.prepared.release_id,
                    configuration=cfg.model_dump(mode="json"),
                    document_id=unit.ref.unit_id,
                )
            )
        )

    def plan(self, units, cfg, ctx):
        from corpus_structure.semantic.cpu_execution import cpu_method_plan

        return (yield from cpu_method_plan(self, units, cfg, ctx))

    def run(self, units, cfg, ctx):
        from corpus_structure.semantic.cpu_execution import run_cpu_method

        return run_cpu_method(self, units, cfg, ctx)

    def _run_prepared(self, units, cfg: ConstructionConfig, ctx):
        base, scope, pins = cfg.require_selection()
        results = []
        vocab, prepared = _construction_resources()
        named = (
            _named_resources(
                canonical_bytes([rule.model_dump(mode="json") for rule in cfg.annotation_rules])
            )
            if cfg.annotation_rules
            else None
        )
        for unit in units:
            started = time.monotonic()
            ctx.check_active()
            if unit.ref not in self.select(unit.run, cfg):
                raise ValueError("construction task unit differs from selected document")
            reader = unit.run.reader
            operation = ctx.characterization_operation(unit.ref)
            builder = ConstructionLayer(base.values(), scope, operation, families=cfg.families)
            dependencies = reader.characterization_layers(pins) if pins else {}
            builder.operation["required_layers"] = [p.values() for p in pins]
            releases = {reader.prepared.release_id: reader.prepared}
            for report in dependencies.values():
                release = report.payload["release_id"]
                if release not in releases:
                    releases[release] = reader.characterization_release(release)
            for source_view_id in scope["source_view_ids"]:
                ctx.check_active()
                view = reader.source_view(source_view_id)
                self._view(
                    builder, view, dependencies, vocab, prepared, cfg, ctx.check_active, named=named
                )
            report = builder.finish(reader.prepared, dependencies=dependencies, releases=releases)
            results.append(
                UnitResult(
                    ref=unit.ref,
                    outcome=ObservationOutcome.PRODUCED,
                    characterization_layer=report,
                    cost=Cost(wall_ms=round((time.monotonic() - started) * 1000), model="none"),
                )
            )
        return tuple(results)

    @staticmethod
    def _view(builder, view, dependencies, vocab, prepared, cfg, check_active, *, named=None):
        from .native_evidence_layers import has_selected_native_text

        selectors = [
            s for s in builder.scope["selectors"] if s["projection"] == view.ref.projection_digest
        ]
        if not has_selected_native_text(view, selectors):
            unresolved_formal = any(
                view.ref.id in report.payload["source_scope"]["source_view_ids"]
                and any(
                    row["family"] == "formal.math" and row["outcome"] not in {"complete", "empty"}
                    for row in report.payload["coverage"]
                )
                for report in dependencies.values()
            )
            for family in cfg.families:
                for selector in selectors:
                    unavailable = family == "construction.math_scope" and unresolved_formal
                    builder.record(
                        family,
                        selector,
                        "unknown" if unavailable else "empty",
                        "formal input lacks exact projected correspondence"
                        if unavailable
                        else None,
                    )
            return
        native_items = {
            item["self_ref"]: item
            for item in (*getattr(view, "items", ()), *getattr(view, "ancestors", ()))
        }

        def pointer_selected(pointer, selector):
            selected = selector.get("native_pointer")
            if selected is None:
                return True
            seen = set()
            while pointer and pointer not in seen:
                if pointer == selected:
                    return True
                seen.add(pointer)
                pointer = (native_items.get(pointer, {}).get("parent") or {}).get("$ref")
            return False

        def admitted(a, b):
            pieces = [
                p
                for p in view.pieces
                if p["kind"] == "native_text" and p["start"] < b and a < p["end"]
            ]
            return bool(pieces) and any(
                s.get("start", 0) <= a
                and b <= s.get("end", len(view.text))
                and all(pointer_selected(p.get("item_ref"), s) for p in pieces)
                for s in selectors
            )

        sentences, protected, atom_support = {}, {}, {}
        for piece in view.pieces:
            if piece["kind"] != "native_text" or native_items.get(piece.get("item_ref"), {}).get(
                "label"
            ) not in {"formula", "reference", "reference_marker"}:
                continue
            a, b = piece["start"], piece["end"]
            protected[(a, b)] = (
                builder.occurrence(view, a, b)
                if admitted(a, b)
                else identity("source-atom", [view.ref.id, a, b, piece.get("item_ref")])
            )
        for pin, report in dependencies.items():
            payload = report.payload
            occurrences = {o["local_id"]: o for o in payload["occurrences"]}
            for annotation in payload["annotations"]:
                extents = [e for o in annotation["occurrences"] for e in occurrences[o]["extents"]]
                if not extents or any(e["source_view_id"] != view.ref.id for e in extents):
                    continue
                start, end = min(e["start"] for e in extents), max(e["end"] for e in extents)
                if not admitted(start, end):
                    continue
                if annotation["kind"] == "native.sentence":
                    sentences[(start, end)] = annotation["local_id"]
                if annotation.get("native_token", {}).get("source_role") in {"math", "reference"}:
                    protected[(start, end)] = annotation["occurrences"][0]
                    atom_support.setdefault((start, end), []).append(
                        dict(layer=pin.values(), local_id=annotation["local_id"])
                    )
                if "formal_input" in annotation and annotation.get("family") != "formal.lexical":
                    parent = annotation["formal_input"].get("parent_occurrence")
                    if parent in occurrences:
                        es = occurrences[parent]["extents"]
                        protected[(min(e["start"] for e in es), max(e["end"] for e in es))] = parent
                        atom_support.setdefault(
                            (min(e["start"] for e in es), max(e["end"] for e in es)), []
                        ).append(dict(layer=pin.values(), local_id=annotation["local_id"]))
        from .source_preparation import annotation_block_owner

        blocks = {}
        for piece in view.pieces:
            if piece["kind"] == "native_text":
                pointer = piece["item_ref"]
                owner = (
                    annotation_block_owner(pointer, native_items)
                    if pointer in native_items
                    else pointer
                )
                bounds = blocks.setdefault(owner, [piece["start"], piece["end"]])
                bounds[0], bounds[1] = min(bounds[0], piece["start"]), max(bounds[1], piece["end"])
        for owner, (start, end) in blocks.items():
            if admitted(start, end) and not any(
                start < right and left < end for left, right in sentences
            ):
                sentences[(start, end)] = owner
        attempted = []
        for (start, end), _ in sorted(sentences.items()):
            check_active()
            attempted.append((start, end))
            if any(a < end and start < b and not start <= a < b <= end for a, b in protected):
                for family in FAMILIES:
                    builder.record(
                        family,
                        dict(projection=view.ref.projection_digest, start=start, end=end),
                        "unsupported",
                        "source region cuts a protected source-owned atom",
                    )
                continue
            intervals = [
                (a, b, occurrence)
                for (a, b), occurrence in sorted(protected.items())
                if start <= a < b <= end
            ]
            intervals = [
                (a, b, o)
                for a, b, o in intervals
                if not any(c <= a and b <= d and (a, b) != (c, d) for c, d, _ in intervals)
            ]
            if any(a < c < b < d for a, b, _ in intervals for c, d, _ in intervals):
                for family in FAMILIES:
                    builder.record(
                        family,
                        dict(projection=view.ref.projection_digest, start=start, end=end),
                        "unsupported",
                        "protected occurrences overlap incompatibly",
                    )
                continue
            atoms = tuple(
                ProtectedAtom(a - start, b - start, occurrence) for a, b, occurrence in intervals
            )
            result = builder.region(
                view,
                start,
                end,
                atoms,
                max_chars=cfg.max_region_chars,
                parse_seconds=cfg.parse_seconds,
                check_active=check_active,
            )
            if result.reducer:
                for key, syntax in result.reducer.syntax.items():
                    if syntax["kind"] == "grammar.terminal" and syntax["native_label"] == "ATOM":
                        builder.annotations[key]["external_premises"] = atom_support.get(
                            (syntax["start"], syntax["end"]), []
                        )
        for piece in view.pieces:
            if piece["kind"] != "native_text":
                continue
            for selector in selectors:
                if not pointer_selected(piece.get("item_ref"), selector):
                    continue
                a, b = (
                    max(piece["start"], selector.get("start", 0)),
                    min(piece["end"], selector.get("end", len(view.text))),
                )
                if a >= b:
                    continue
                cursor = a
                for left, right in sorted(attempted):
                    if right <= cursor or left >= b:
                        continue
                    if cursor < left:
                        for family in FAMILIES:
                            builder.record(
                                family,
                                dict(
                                    projection=view.ref.projection_digest,
                                    native_pointer=piece["item_ref"],
                                    start=cursor,
                                    end=min(left, b),
                                ),
                                "unsupported",
                                "selected source has no admitted construction region",
                            )
                    cursor = max(cursor, min(right, b))
                if cursor < b:
                    for family in FAMILIES:
                        builder.record(
                            family,
                            dict(
                                projection=view.ref.projection_digest,
                                native_pointer=piece["item_ref"],
                                start=cursor,
                                end=b,
                            ),
                            "unsupported",
                            "selected source has no admitted construction region",
                        )
        native_available = False
        for pin, container, doc, native_annotations, start, end in retained_documents(
            dependencies, view, vocab
        ):
            check_active()
            if not admitted(start, end):
                continue
            native_available = True
            _, unavailable = builder.native(
                view, pin, container, doc, native_annotations, start, prepared
            )
            if unavailable:
                for family in GRAMMAR_FAMILIES:
                    builder.record(
                        family,
                        dict(projection=view.ref.projection_digest, start=start, end=end),
                        "partial",
                        "; ".join(unavailable),
                    )
        from corpus_structure.semantic.constructions.retained_rules import populate

        for pin, report in dependencies.items():
            if not any(run["provider"] == "spacy" for run in report.payload.get("native_runs", ())):
                continue
            try:
                populate(builder, view, pin, report, check_active=check_active, admitted=admitted)
            except AnnotationUnavailable as error:
                check_active()
                for selector in selectors:
                    builder.record(
                        "construction.source_readings",
                        selector,
                        "unknown",
                        "retained source-reading premises unavailable: " + str(error),
                    )
            if named is not None:
                from corpus_structure.semantic.constructions.named import populate_named

                populate_named(
                    builder, view, pin, report, named, check_active=check_active, admitted=admitted
                )
        from corpus_structure.semantic.constructions.retained_declarations import (
            populate_declaration_readings,
        )

        populate_declaration_readings(
            builder, view, dependencies, check_active=check_active, admitted=admitted
        )
        from corpus_structure.semantic.constructions.navigation import populate_navigation

        populate_navigation(
            builder, view, dependencies, check_active=check_active, admitted=admitted
        )
        from corpus_structure.semantic.constructions.math_scope import populate_math_scope

        populate_math_scope(
            builder,
            view,
            dependencies,
            vocab,
            binders=cfg.math_scope_binders,
            rules=cfg.math_domain_rules,
            check_active=check_active,
            admitted=admitted,
        )
        if not native_available:
            for family in GRAMMAR_FAMILIES:
                for selector in selectors:
                    builder.record(
                        family,
                        selector,
                        "partial",
                        "native-dependent construction coverage unavailable; "
                        "source grammar retained",
                    )


class ConstructionOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "text.constructions/source-native",
        "profile": "derivation",
        "subject": "original-source-view",
        "context": ["original-source", "selected-scope"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "source",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "parameter": "source",
                "support": {
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "origins": ["computation", "original-source"],
                    "source": "original-source",
                    "coverage": "selected-scope",
                },
            },
            {
                "name": "formal",
                "kind": "https://corpus-structure.dev/semantic/data-operation-characterization/DdoFormalProduct",
                "direction": "input",
                "minimum": 1,
                "maximum": None,
                "collection": "sequence",
                "presence": "required",
                "parameter": "formal",
                "support": {
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "origins": ["computation"],
                    "source": "original-source",
                    "coverage": "selected-scope",
                },
            },
            {
                "name": "sentences",
                "kind": "https://corpus-structure.dev/semantic/data-operation-sentences/DdoSentenceInventory",
                "direction": "input",
                "minimum": 0,
                "maximum": 1,
                "collection": "scalar",
                "presence": "optional",
                "parameter": "sentences",
                "support": {
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "origins": ["computation"],
                    "source": "original-source",
                    "coverage": "selected-scope",
                },
            },
            {
                "name": "result",
                "kind": "https://corpus-structure.dev/semantic/data-operation-constructions/DdoConstructionProduct",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": ["acquired-construction-profile"],
        "invariants": [
            "original-source-coordinates",
            "governed-semantic-member-references",
            "explicit-coverage-and-private-standing",
        ],
        "coverage": "exact-selected-source-scope",
        "outcomes": ["success", "failed"],
        "precision": "retained-positioned-characterization",
        "dependencies": [],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "cancellation": "cooperative",
            "ownership": "immutable",
        },
        "behavior": "compose retained typed construction products without upstream language "
        "reacquisition",
        "parameters": {},
        "binding": {
            "operator": "all",
            "children": [
                {"operator": "scan", "roles": ["source"]},
                {"operator": "collection", "roles": ["formal"], "collection": "sequence"},
                {"operator": "scan", "roles": ["sentences"]},
            ],
        },
        "opaque": [
            {
                "reference": (
                    "corpus_structure.semantic.characterization_ports.execute_construction_profile"
                ),
                "contract": "characterization/construction-assets",
                "role": "prepared-construction-resources",
            },
            {
                "reference": "corpus_structure.semantic.source_products.FrozenNativeSource",
                "contract": "characterization/construction-assets",
                "role": "nominal-boundary",
            },
            {
                "reference": "corpus_structure.semantic.formal_products.FormalEvidenceProduct",
                "contract": "characterization/construction-assets",
                "role": "nominal-boundary",
            },
            {
                "reference": "corpus_structure.semantic.construction_products.ConstructionProduct",
                "contract": "characterization/construction-assets",
                "role": "nominal-boundary",
            },
            {
                "reference": "corpus_structure.semantic.sentence_products.SentenceInventory",
                "contract": "characterization/construction-assets",
                "role": "nominal-boundary",
            },
        ],
        "assets": [
            {
                "reference": "construction-profile",
                "contract": "characterization/construction-assets",
                "role": "semantic-implementation-and-schema-assets",
            }
        ],
    }

    def __init__(self, profile, check_active):
        self.profile = profile
        self.check_active = check_active

    def run(
        self,
        source: FrozenNativeSource,
        formal: tuple[FormalEvidenceProduct, ...],
        sentences: SentenceInventory | None = None,
    ) -> ConstructionProduct:
        return execute_construction_profile(self, source, formal, sentences)
