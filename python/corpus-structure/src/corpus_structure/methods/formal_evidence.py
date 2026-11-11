"""Operation adapter for reusable positioned formal evidence."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from corpus_structure.core.evidence import MacroDef
from corpus_structure.core.method import (
    Digest,
    MethodContext,
    Resources,
    SourceRunContext,
    UnitRef,
    UnitResult,
    UnitView,
)
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.methods.math import grammar as math_grammar
from corpus_structure.semantic.characterization import validate_layer
from corpus_structure.semantic.formal_evidence import (
    FAMILIES,
    PROFILE,
    build_formal_layer,
    grammar_identity,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.product_reference import ProductReference


class FormalEvidenceConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    characterization_base_document: dict | None = None
    characterization_source_scope: dict | None = None
    characterization_layers: tuple[dict, ...] = ()
    model: Literal["none"] = "none"
    grammar: str = Field(default_factory=grammar_identity, min_length=1)
    context: Literal["source-only"] = "source-only"
    profile: Literal["positioned-formal-v1"] = PROFILE
    math_start: math_grammar.Kind = "any_value"
    parse_seconds: float = Field(default=math_grammar.PARSE_SECONDS, gt=0)
    max_forest_nodes: int = Field(default=20000, ge=1)
    max_inline_chars: int = Field(default=2048, ge=1)
    macros: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def supported_grammar(self):
        if self.grammar != grammar_identity():
            raise ValueError("formal configuration differs from the installed effective grammar")
        return self

    def require_selection(self):
        if (
            self.characterization_base_document is None
            or self.characterization_source_scope is None
        ):
            raise ValueError(
                "formal evidence requires an exact frozen base document and source scope"
            )
        pins = tuple(ProductReference(**pin) for pin in self.characterization_layers)
        if len(set(pins)) != len(pins):
            raise ValueError("formal evidence requires distinct selected layer pins")
        return (
            ProductReference(**self.characterization_base_document),
            self.characterization_source_scope,
            pins,
        )


class FormalEvidenceMethod:
    name = "text.formal_evidence"
    version = "1"
    family = MethodFamily.NORMALIZE
    unit_type = TaskUnitType.DOCUMENT
    tier = MethodTier.DETERMINISTIC
    confidence_source = None
    Config = FormalEvidenceConfig
    resources = Resources(worker="cpu", batch_size=1)

    def select(self, run: SourceRunContext, cfg: FormalEvidenceConfig) -> Iterable[UnitRef]:
        base, scope, _pins = cfg.require_selection()
        refs = [run.reader.source_view_ref(identity) for identity in scope["source_view_ids"]]
        if not refs or any(ref is None or ref.native_product != base for ref in refs):
            raise ValueError("formal source scope differs from the run's exact selected document")
        documents = {ref.document_id for ref in refs if ref is not None}
        if len(documents) != 1:
            raise ValueError("formal evidence requires one selected document")
        return (UnitRef(TaskUnitType.DOCUMENT, next(iter(documents))),)

    def input_digest(self, unit: UnitView, cfg: FormalEvidenceConfig) -> Digest:
        cfg.require_selection()
        if unit.ref not in self.select(unit.run, cfg):
            raise ValueError("positioned formal evidence requires its exact selected document")
        return Digest(
            canonical_bytes(
                dict(
                    method=self.name,
                    version=self.version,
                    release_id=unit.run.reader.prepared.release_id,
                    configuration=cfg.model_dump(mode="json"),
                    document=unit.ref.unit_id,
                )
            )
        )

    def run(
        self, units: Sequence[UnitView], cfg: FormalEvidenceConfig, ctx: MethodContext
    ) -> Sequence[UnitResult]:
        results = []
        _base, scope, pins = cfg.require_selection()
        for unit in units:
            ctx.check_active()
            if unit.ref not in self.select(unit.run, cfg):
                raise ValueError("positioned formal evidence requires its exact selected document")
            operation = ctx.characterization_operation(unit.ref)
            if any(
                operation[key] != expected
                for key, expected in {
                    "key": self.name,
                    "version": self.version,
                    "model": cfg.model,
                    "grammar": cfg.grammar,
                    "context": cfg.context,
                }.items()
            ):
                raise ValueError("formal task determinants differ from its frozen configuration")
            reader = unit.run.reader
            payloads = []
            for identity in scope["source_view_ids"]:
                view = reader.source_view(identity)
                selected_scope = {
                    **scope,
                    "source_view_ids": [identity],
                    "source_views": [
                        pin for pin in scope["source_views"] if pin["source_view_id"] == identity
                    ],
                    "selectors": [
                        selector
                        for selector in scope["selectors"]
                        if selector["projection"] == view.ref.projection_digest
                    ],
                }
                payloads.append(
                    build_formal_layer(
                        view,
                        reader.prepared,
                        operation,
                        math_start=cfg.math_start,
                        parse_seconds=cfg.parse_seconds,
                        max_forest_nodes=cfg.max_forest_nodes,
                        max_inline_chars=cfg.max_inline_chars,
                        macros={name: MacroDef(body=body) for name, body in cfg.macros.items()},
                        check_active=ctx.check_active,
                        source_scope=selected_scope,
                    ).payload
                )
            body = {**payloads[0], "source_scope": scope}
            for inventory in (
                "occurrences",
                "annotations",
                "memberships",
                "roles",
                "terms",
                "choices",
            ):
                rows = {}
                for payload in payloads:
                    for row in payload.get(inventory, ()):
                        if row["local_id"] in rows and rows[row["local_id"]] != row:
                            raise ValueError(
                                "formal scopes produce conflicting immutable identities"
                            )
                        rows[row["local_id"]] = row
                body[inventory] = list(rows.values())
            coverage = []
            for family in FAMILIES:
                rows = [
                    next(row for row in payload["coverage"] if row["family"] == family)
                    for payload in payloads
                ]
                combined = {**rows[0]}
                for field in ("eligible", "examined", "unexamined"):
                    combined[field] = list(
                        {
                            canonical_bytes(selector): selector
                            for row in rows
                            for selector in row.get(field, ())
                        }.values()
                    )
                combined["outcome"] = (
                    "partial"
                    if any(row["outcome"] not in {"complete", "empty"} for row in rows)
                    else "complete"
                    if any(row["outcome"] == "complete" for row in rows)
                    else "empty"
                )
                if combined["outcome"] == "partial":
                    combined["reason"] = "; ".join(
                        dict.fromkeys(row["reason"] for row in rows if row.get("reason"))
                    )
                coverage.append(combined)
            body["coverage"] = coverage
            body["outcome"] = (
                "partial"
                if any(row["outcome"] not in {"complete", "empty"} for row in coverage)
                else "complete"
            )
            dependencies = reader.characterization_layers(pins) if pins else {}
            body["dependencies"] = [pin.values() for pin in pins]
            body["operation"]["required_layers"] = [pin.values() for pin in pins]
            releases = {reader.prepared.release_id: reader.prepared}
            for report in dependencies.values():
                release_id = report.payload["release_id"]
                if release_id not in releases:
                    releases[release_id] = reader.characterization_release(release_id)
            layer = validate_layer(
                reader.prepared, body, dependencies=dependencies, releases=releases
            )
            ctx.check_active()
            results.append(
                UnitResult(
                    ref=unit.ref, outcome=ObservationOutcome.PRODUCED, characterization_layer=layer
                )
            )
        return results
