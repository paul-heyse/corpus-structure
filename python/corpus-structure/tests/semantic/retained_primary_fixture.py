"""Explicit sealed-wire producers for historical native publication scenarios.

These fixture methods are confined to tests. Current production obtains declared
products through the native operation model; no legacy worker or Reader facade is
restored here. Existing builders remain the authority for the sealed wire values.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from spacy.lang.en import English

from corpus_structure.core.method import Resources, UnitRef, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.semantic.constructions.resources import construction_digest
from corpus_structure.semantic.formal_evidence import grammar_identity
from corpus_structure.semantic.product_reference import ProductReference


class _Selection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    characterization_base_document: dict
    characterization_source_scope: dict
    characterization_layers: tuple[dict, ...] = ()
    model: Literal["none"] = "none"


class _FormalSelection(_Selection):
    grammar: str = Field(default_factory=grammar_identity)
    context: str = "source-only"


class _ConstructionSelection(_Selection):
    grammar: str = Field(default_factory=construction_digest)
    context: str = "retained-native-sentences-and-source-pieces-1"


class _SealedPrimary:
    version = "1"
    family = MethodFamily.EXTRACT
    unit_type = TaskUnitType.DOCUMENT
    tier = MethodTier.DETERMINISTIC
    confidence_source = None
    resources = Resources()

    @staticmethod
    def select(run, cfg):
        base = ProductReference(**cfg.characterization_base_document)
        refs = tuple(
            run.reader.source_view_ref(identity)
            for identity in cfg.characterization_source_scope["source_view_ids"]
        )
        if not refs or any(ref is None or ref.native_product != base for ref in refs):
            raise ValueError("historical fixture source differs from its selected original base")
        documents = {ref.document_id for ref in refs if ref is not None}
        if len(documents) != 1:
            raise ValueError("historical fixture requires one actual original document")
        return (UnitRef(TaskUnitType.DOCUMENT, next(iter(documents))),)

    def input_digest(self, unit, cfg):
        from corpus_structure.core.method import Digest
        from corpus_structure.semantic.identity import canonical_bytes

        return Digest(canonical_bytes(cfg.model_dump(mode="json")))

    @staticmethod
    def layer(reader, cfg, operation):
        raise NotImplementedError("a concrete historical family owns layer construction")

    def plan(self, units, cfg, ctx):
        yield from ()
        return self.run(units, cfg, ctx)

    def run(self, units, cfg, ctx):
        return tuple(
            UnitResult(
                ref=unit.ref,
                outcome=ObservationOutcome.PRODUCED,
                characterization_layer=self.layer(
                    unit.run.reader, cfg, ctx.characterization_operation(unit.ref)
                ),
            )
            for unit in units
        )



class _NativeSelection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    characterization_base_document: dict
    characterization_source_scope: dict
    characterization_layers: tuple[dict, ...] = ()
    model: str = "spacy-en_core_web_sm-3.8.0"
    grammar: Literal["none"] = "none"
    context: str = "source-blocks-and-canonical-sentences-1"
    characterization_profile: Literal["spacy_only"] = "spacy_only"


class SealedNativeFixture(_SealedPrimary):
    """Only the actual spaCy layer required by historical sealed-reader scenarios."""

    name = "text.native_evidence"
    version = "2"
    Config = _NativeSelection

    @staticmethod
    def layer(reader, cfg, operation):
        from corpus_structure.ingest.annotations import AnnotationProfile, annotate
        from corpus_structure.ingest.sentences import SentenceConfig, pipeline
        from corpus_structure.methods.native_evidence import _availability, native_run
        from corpus_structure.methods.native_evidence_layers import SPACY_FAMILIES, NativeEvidenceBuilder
        from corpus_structure.methods.source_preparation import annotation_inputs

        if cfg.characterization_layers:
            raise ValueError("historical native fixture is the independent first layer")
        scope = cfg.characterization_source_scope
        profile = AnnotationProfile(SentenceConfig(exclude=("ner",)))
        builder = NativeEvidenceBuilder(
            cfg.characterization_base_document, scope, operation,
            profile="spacy_only", families=SPACY_FAMILIES,
        )
        builder.operation["required_layers"] = []
        layouts, texts, requests, owners = [], [], [], []
        for identity in scope["source_view_ids"]:
            view = reader.source_view(identity)
            selectors = [row for row in scope["selectors"] if row["projection"] == view.ref.projection_digest]
            pointers = tuple(dict.fromkeys(row["native_pointer"] for row in selectors if row.get("native_pointer")))
            inputs = tuple(row for row in annotation_inputs(
                view, profile=profile, max_annotation_chars=32768,
                region_pointers=pointers or None,
            ) if any(row.layout.block_start >= selected.get("start", 0)
                     and row.layout.block_end <= selected.get("end", len(view.text))
                     for selected in selectors))
            for piece in view.pieces:
                if piece["kind"] == "native_text" and any(
                    selected.get("start", 0) < piece["end"]
                    and selected.get("end", len(view.text)) > piece["start"]
                    and (not selected.get("native_pointer") or selected["native_pointer"] == piece["item_ref"])
                    for selected in selectors
                ) and not any(row.layout.block_start <= piece["start"]
                              and row.layout.block_end >= piece["end"] for row in inputs):
                    raise ValueError("historical native fixture requires complete selected native blocks")
            if not inputs:
                for family in SPACY_FAMILIES:
                    builder.record(family, selectors, "empty")
            requests.extend(inputs)
            owners.extend(view for _ in inputs)
        # One actual resident pipeline population for all explicitly selected views.
        products = annotate(requests, profile, require_complete=False) if requests else ()
        for view, product in zip(owners, products, strict=True):
            builder.spacy(view, product, "spacy")
            layouts.append(dict(view=view.ref.id, layout=product.layout_digest))
            texts.append(dict(view=view.ref.id, text=product.text_digest))
        nlp = pipeline(profile.configuration)
        run = native_run(
            "spacy", "spacy_only", nlp.config.to_str(),
            model=profile.configuration.model, version=profile.configuration.model_version,
            runtime_version=profile.configuration.spacy_version, layout=layouts, text=texts,
            components=[dict(name=name, factory=nlp.get_pipe_meta(name).factory) for name in nlp.pipe_names],
            packages=[dict(name="spacy", version=profile.configuration.spacy_version),
                      dict(name=profile.configuration.model, version=profile.configuration.model_version)],
        )
        run["availability"] = _availability(builder, "spacy")
        builder.native_runs.append(run)
        return builder.finish(reader.prepared)

class SealedFormalFixture(_SealedPrimary):
    name = "text.formal_evidence"
    Config = _FormalSelection

    @staticmethod
    def layer(reader, cfg, operation):
        from corpus_structure.semantic.characterization import validate_layer
        from corpus_structure.semantic.formal_evidence import FAMILIES, build_formal_layer
        from corpus_structure.semantic.identity import canonical_bytes

        scope = cfg.characterization_source_scope
        payloads = []
        for identity in scope["source_view_ids"]:
            view = reader.source_view(identity)
            selected = {
                **scope,
                "source_view_ids": [identity],
                "source_views": [
                    row for row in scope["source_views"] if row["source_view_id"] == identity
                ],
                "selectors": [
                    row
                    for row in scope["selectors"]
                    if row["projection"] == view.ref.projection_digest
                ],
            }
            payloads.append(
                build_formal_layer(view, reader.prepared, operation, source_scope=selected).payload
            )
        value = {**payloads[0], "source_scope": scope}
        for inventory in ("occurrences", "annotations", "memberships", "roles", "terms", "choices"):
            rows = {}
            for payload in payloads:
                for row in payload[inventory]:
                    previous = rows.setdefault(row["local_id"], row)
                    if previous != row:
                        raise ValueError("historical formal fixture has conflicting immutable rows")
            value[inventory] = list(rows.values())
        coverage = []
        for family in FAMILIES:
            parts = [
                next(row for row in payload["coverage"] if row["family"] == family)
                for payload in payloads
            ]
            combined = {**parts[0]}
            for key in ("eligible", "examined", "unexamined"):
                combined[key] = list(
                    {canonical_bytes(row): row for part in parts for row in part[key]}.values()
                )
            combined["outcome"] = (
                "partial"
                if any(part["outcome"] not in {"complete", "empty"} for part in parts)
                else "complete"
                if any(part["outcome"] == "complete" for part in parts)
                else "empty"
            )
            if combined["outcome"] == "partial":
                combined["reason"] = "; ".join(
                    dict.fromkeys(part["reason"] for part in parts if part.get("reason"))
                )
            coverage.append(combined)
        value["coverage"] = coverage
        value["outcome"] = (
            "partial"
            if any(row["outcome"] not in {"complete", "empty"} for row in coverage)
            else "complete"
        )
        return validate_layer(reader.prepared, value)


class SealedConstructionFixture(_SealedPrimary):
    name = "text.constructions"
    Config = _ConstructionSelection

    @staticmethod
    def layer(reader, cfg, operation):
        from corpus_structure.semantic.constructions import (
            FAMILIES,
            ConstructionLayer,
            ProtectedAtom,
        )
        from corpus_structure.semantic.constructions.matching import (
            PreparedConstructions,
            retained_documents,
        )
        from corpus_structure.semantic.constructions.navigation import populate_navigation
        from corpus_structure.semantic.constructions.retained_rules import populate

        base = cfg.characterization_base_document
        scope = cfg.characterization_source_scope
        pins = tuple(ProductReference(**row) for row in cfg.characterization_layers)
        dependencies = reader.characterization_layers(pins)
        layer = ConstructionLayer(
            base, scope, operation, families=(*FAMILIES, "construction.navigation")
        )
        layer.operation["required_layers"] = [pin.values() for pin in pins]
        vocab = English().vocab
        prepared = PreparedConstructions(vocab)
        for identity in scope["source_view_ids"]:
            view = reader.source_view(identity)
            items = {item["self_ref"]: item for item in view.items}
            for piece in view.pieces:
                if piece["kind"] != "native_text":
                    continue
                start, end = piece["start"], piece["end"]
                atoms = (
                    (ProtectedAtom(0, end - start, layer.occurrence(view, start, end)),)
                    if items.get(piece["item_ref"], {}).get("label")
                    in {"formula", "reference", "reference_marker"}
                    else ()
                )
                layer.region(view, start, end, atoms)
            for pin, container, doc, columns, start, _end in retained_documents(
                dependencies, view, vocab
            ):
                layer.native(view, pin, container, doc, columns, start, prepared)
            for pin, report in dependencies.items():
                if any(row["provider"] == "spacy" for row in report.payload.get("native_runs", ())):
                    populate(layer, view, pin, report)
            populate_navigation(layer, view, dependencies)
        releases = {reader.prepared.release_id: reader.prepared}
        for report in dependencies.values():
            identity = report.payload["release_id"]
            if identity not in releases:
                releases[identity] = reader.characterization_release(identity)
        return layer.finish(reader.prepared, dependencies=dependencies, releases=releases)
