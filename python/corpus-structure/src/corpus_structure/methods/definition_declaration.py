"""Read an explicit local declaration chain from retained HanLP roles."""

from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Self

from pydantic import Field, model_validator

from corpus_structure.core.method import Digest, Resources, UnitRef, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.semantic.constructions.retained_declarations import DeclarationNotQualified
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.source_contexts import record_source_pin
from corpus_structure.semantic.structural_products import (
    DeclarationChainBinding,
    DeclarationChainWitness,
    DefinitionComponentsProduct,
    DefinitionStage,
    LocatedDefinitionSpan,
    StructuralInput,
    StructuralProductReport,
    StructuralValue,
    definition_component,
)

CHAIN_VERSION = "definition-declaration-chain-2"
CHAIN_METHOD = "structure.definition_declaration_components"
_LABEL_NUMBER = re.compile(r"[0-9]+(?:\.[0-9]+)*")


class DeclarationChainSelection(StructuralValue):
    passage_id: str = Field(min_length=1)


class DeclarationComponentsConfig(StructuralValue):
    inputs: StructuralInput | None = None
    structural_input_digest: str | None = None
    selections: tuple[DeclarationChainSelection, ...] = Field(default=(), max_length=64)
    characterization_layers: tuple[dict, ...] = ()

    @model_validator(mode="after")
    def selected_input(self) -> Self:
        if self.inputs is None:
            if self.selections or self.structural_input_digest is not None:
                raise ValueError("absent declaration extraction cannot carry partial inputs")
            return self
        selected = {item.passage_id for item in self.selections}
        if (
            self.structural_input_digest != self.inputs.identity
            or not self.characterization_layers
            or not selected
            or len(selected) != len(self.selections)
            or not selected <= {passage.passage_id for passage in self.inputs.passages}
        ):
            raise ValueError("declaration extraction requires exact frozen primary layer inputs")
        return self


class DeclarationComponentsMethod:
    """A distinct declaration-only method; no change to the incumbent v9 ABI."""

    name = CHAIN_METHOD
    version = "2"
    family = MethodFamily.RESOLVE
    unit_type = TaskUnitType.RUN
    tier = MethodTier.DETERMINISTIC
    confidence_source = None
    Config = DeclarationComponentsConfig
    resources = Resources(worker="cpu", batch_size=1, max_concurrency=1)

    def select(self, run, cfg):
        return (
            (UnitRef(TaskUnitType.RUN, unit_key="definition-declarations:" + cfg.inputs.identity),)
            if cfg.inputs is not None
            else ()
        )

    def input_digest(self, unit, cfg):
        return Digest(canonical_bytes(cfg.model_dump(mode="json", exclude_none=True)))

    def run(self, units, cfg, ctx):
        from .model_observation import private_declaration_enabled

        if cfg.inputs is None:
            raise ValueError("declaration extraction requires exact selected inputs")
        if not private_declaration_enabled(ctx.reader.prepared.manifest):
            raise ValueError("declaration chain requires the matching released definition policy")
        ctx.reader.validate_structural_inputs(cfg.inputs)
        passages = {passage.passage_id: passage for passage in cfg.inputs.passages}
        refs = {source.identity: source for source in cfg.inputs.sources}
        from corpus_structure.semantic.product_reference import ProductReference

        # Resolve this task's frozen products once. Source-local selection keeps
        # unrelated documents and incomplete sentence populations independent.
        frozen = ctx.reader.characterization_layers(
            tuple(ProductReference(**pin) for pin in cfg.characterization_layers)
        )
        by_source = {}
        for pin, report in frozen.items():
            for identity in report.payload["source_scope"]["source_view_ids"]:
                by_source.setdefault(identity, {})[pin] = report
        found = []
        for item in cfg.selections:
            ctx.check_active()
            passage = passages[item.passage_id]
            source_ref = refs[passage.source_ref]
            view = ctx.reader.source_view(source_ref.source_view_id)
            layers = by_source.get(source_ref.source_view_id, {})
            found.append(primary_declaration_component(layers, view, passage))
        report = StructuralProductReport(
            kind="definition_components",
            inputs=cfg.inputs,
            definition_components=DefinitionComponentsProduct(
                components=tuple(found),
                stages=tuple(
                    DefinitionStage(
                        passage_id=item.passage_id,
                        operation="attachment",
                        outcome="succeeded",
                        reason=(
                            "Released declaration chain replayed from exact native parser roles."
                        ),
                    )
                    for item in cfg.selections
                ),
            ),
        )
        return tuple(
            UnitResult(
                ref=unit.ref,
                outcome=ObservationOutcome.PRODUCED,
                structural_product=report.model_dump(mode="json", exclude_none=True),
                parse_detail={"version": CHAIN_VERSION},
            )
            for unit in units
        )


def _require(value):
    if not value:
        raise DeclarationNotQualified(
            "retained roles do not establish one complete declaration chain"
        )


@dataclass(frozen=True)
class DeclarationChain:
    label: LocatedDefinitionSpan
    term: LocatedDefinitionSpan
    content: LocatedDefinitionSpan
    bindings: tuple[DeclarationChainBinding, ...]
    construction_frame: str
    construction_subject_token: int
    naming_frame: str
    naming_antecedent_token: int


def _declaration_chain_from_sentences(candidates, passage):
    """Select a domain definition chain from already-characterized local syntax."""
    _require(len(candidates) == 3)
    declarations, construction, naming = candidates
    first = next((i for i, row in enumerate(declarations.positions) if row[0] == passage.start), -1)
    _require(
        0 <= first < len(declarations.words) - 3
        and declarations.words[first].casefold() == "definition"
        and bool(_LABEL_NUMBER.fullmatch(declarations.words[first + 1]))
        and all(sentence.words[-1] == "." for sentence in candidates)
    )
    intros = declarations.facts["intros"]
    _require(
        1 <= len(intros) <= 4
        and intros[0]["start"] == first + 2
        and intros[0]["parent"] in {None, first}
    )
    for intro in intros[1:]:
        _require(
            intro["coordinated"]
            and intro["coordinate_cue"]
            and intro["parent"] == intros[0]["start"]
        )
    declared = [
        (row["copula"], row["subject"], declarations.words[row["subject"]]) for row in intros
    ]
    _require(len({word for _, _, word in declared}) == len(declared))
    construction_intros = construction.facts["intros"]
    _require(len(construction_intros) == 1)
    construct = construction_intros[0]
    _require(construct["start"] == 0 and construct["parent"] is None)
    constructed = construction.words[construct["subject"]]
    _require(constructed not in {word for _, _, word in declared})
    uses = []
    for _copula, subject, name in declared:
        positions = [i for i, word in enumerate(construction.words) if word == name]
        _require(len(positions) == 1)
        uses.append(
            DeclarationChainBinding(
                frame=declarations.reference.identity, subject_token=subject, use_token=positions[0]
            )
        )
    _require(tuple(sorted(row.use_token for row in uses)) in construct["relative_uses"])
    named = naming.facts["naming"]
    _require(
        named is not None
        and naming.words[named["antecedent"]] == constructed
        and naming.words.count(constructed) == 1
    )

    def span(a, b):
        _require(passage.start <= a < b <= passage.end)
        return LocatedDefinitionSpan(
            passage_id=passage.passage_id,
            start=a,
            end=b,
            text=passage.text[a - passage.start : b - passage.start],
        )

    return DeclarationChain(
        label=span(passage.start, declarations.positions[first + 1][1]),
        term=span(
            naming.positions[named["term_start"]][0], naming.positions[named["term_end"] - 1][1]
        ),
        content=span(
            declarations.positions[intros[0]["start"]][0],
            naming.positions[named["subject_end"] - 1][1],
        ),
        bindings=tuple(uses),
        construction_frame=construction.reference.identity,
        construction_subject_token=construct["subject"],
        naming_frame=naming.reference.identity,
        naming_antecedent_token=named["antecedent"],
    )


def primary_declaration_component(layers, view, passage):
    """Apply domain chain selection to exact retained primary sentence facts."""
    from corpus_structure.semantic.constructions.retained_declarations import declaration_sentences
    from corpus_structure.semantic.proposals import native_source_frame

    source = native_source_frame(view, ())
    if (
        not 0 <= passage.start < passage.end <= len(view.text)
        or view.text[passage.start : passage.end] != passage.text
    ):
        raise DeclarationNotQualified("declaration passage differs from exact source")
    sentences, evidence = declaration_sentences(layers, view, passage)
    chain = _declaration_chain_from_sentences(tuple(sentences), passage)
    return definition_component(
        term=chain.term,
        content=chain.content,
        interpretation="definition",
        basis="declaration_chain",
        declaration_chain=DeclarationChainWitness(
            version=CHAIN_VERSION,
            primary_evidence=tuple(dict.fromkeys(evidence)),
            scope_digest=sha256(
                canonical_bytes(
                    dict(
                        source=record_source_pin(source),
                        passage=[passage.start, passage.end],
                        policy="primary-declaration-roles-1",
                    )
                )
            ).hexdigest(),
            label=chain.label,
            bindings=chain.bindings,
            construction_frame=chain.construction_frame,
            construction_subject_token=chain.construction_subject_token,
            naming_frame=chain.naming_frame,
            naming_antecedent_token=chain.naming_antecedent_token,
        ),
        scope=passage.scope,
        effective_version=passage.effective_version,
        evidence=(passage.passage_id,),
        reason=(
            "Exact retained native declaration roles and primary voice interpretations "
            "support this local definition chain; domain admission remains separate."
        ),
    )
