"""Select a local declaration chain from current positioned native syntax products."""

from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256

from corpus_structure.semantic.constructions.retained_declarations import DeclarationNotQualified
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import (
    DeclarationChainBinding,
    LocatedDefinitionSpan,
)

CHAIN_VERSION = "definition-declaration-chain-2"
_LABEL_NUMBER = re.compile(r"[0-9]+(?:\.[0-9]+)*")


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


def primary_declaration_component_products(products, source, passage, *, source_pin):
    """Select the same domain chain from declared positioned syntax and native support."""
    from corpus_structure.semantic.constructions.retained_declarations import (
        declaration_sentences_products,
    )
    from corpus_structure.semantic.structural_products import (
        DeclaredDeclarationChainWitness,
        DeclaredPrimaryReference,
        declared_definition_component,
    )

    sentences, evidence = declaration_sentences_products(products, source, passage)
    chain = _declaration_chain_from_sentences(sentences, passage)
    return declared_definition_component(
        term=chain.term,
        content=chain.content,
        interpretation="definition",
        basis="declaration_chain",
        declaration_chain=DeclaredDeclarationChainWitness(
            version=CHAIN_VERSION,
            primary_evidence=tuple(
                DeclaredPrimaryReference(**reference.values()) for reference in evidence
            ),
            scope_digest=sha256(
                canonical_bytes(
                    {
                        "source": source_pin,
                        "passage": [passage.start, passage.end],
                        "policy": "primary-declaration-roles-1",
                    }
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
        reason="Exact retained native declaration roles and primary voice interpretations support this local definition chain; domain admission remains separate.",
    )
