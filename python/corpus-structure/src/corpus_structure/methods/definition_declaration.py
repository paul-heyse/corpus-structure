"""Read an explicit local declaration chain from retained HanLP roles."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Self

from pydantic import Field, TypeAdapter, model_validator

from corpus_structure.core.method import Digest, Resources, UnitRef, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.ingest.sentences import TextToken
from corpus_structure.semantic.contributions import contribution_identity
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.source_contexts import (
    ContextRefused,
    NativeSourceContext,
    PreparedNativeSources,
    SourceSlice,
    evidence_anchor,
    record_source_pin,
)
from corpus_structure.semantic.structural_products import (
    DeclarationChainBinding,
    DeclarationChainWitness,
    DefinitionComponentsProduct,
    DefinitionStage,
    ExternalSourceRef,
    LocatedDefinitionSpan,
    StructuralInput,
    StructuralPassage,
    StructuralProductReport,
    StructuralValue,
    definition_component,
)

from .pm2_hanlp_products import _dependency_graph, _Frame, _head, hanlp_products
from .pm2_products import PARSER_QUESTIONS, ParserProducts, parser_value_for_contract
from .pm2_source import (
    HANLP_SEAM_LAYOUT,
    HanlpLayoutDecision,
    MappedSource,
    PM2SourceMap,
    PM2TokenMap,
    ProviderToken,
    SourceMapSegment,
    hanlp_seam_layout,
)

CHAIN_VERSION = "definition-declaration-chain-1"
CHAIN_METHOD = "structure.definition_declaration_components"
_LABEL_NUMBER = re.compile(r"[0-9]+(?:\.[0-9]+)*")
_SCOPE_MARKERS = frozenset(
    {"if", "unless", "although", "except", "not", "never", "reportedly", "allegedly"}
)
_QUOTES = frozenset({'"', "\u201c", "\u201d", "\u2018", "\u2019", "``", "''"})
_LAYOUT = TypeAdapter(HanlpLayoutDecision)
_TOKENS = TypeAdapter(tuple[ProviderToken, ...])


class DeclarationChainSelection(StructuralValue):
    passage_id: str = Field(min_length=1)
    parser: RetainedContributionRef


class DeclarationComponentsConfig(StructuralValue):
    inputs: StructuralInput | None = None
    structural_input_digest: str | None = None
    selections: tuple[DeclarationChainSelection, ...] = Field(default=(), max_length=64)

    @model_validator(mode="after")
    def selected_input(self) -> Self:
        if self.inputs is None:
            if self.selections or self.structural_input_digest is not None:
                raise ValueError("absent declaration extraction cannot carry partial inputs")
            return self
        selected = {item.passage_id for item in self.selections}
        if (
            self.structural_input_digest != self.inputs.identity
            or not selected
            or len(selected) != len(self.selections)
            or not selected <= {passage.passage_id for passage in self.inputs.passages}
            or any(
                item.parser.contribution_id not in self.inputs.dependencies
                for item in self.selections
            )
        ):
            raise ValueError("declaration extraction requires exact retained parser inputs")
        return self


class DeclarationComponentsMethod:
    """A distinct declaration-only method; no change to the incumbent v9 ABI."""

    name = CHAIN_METHOD
    version = "1"
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
        found = []
        for item in cfg.selections:
            ctx.check_active()
            if item.parser.release_id != ctx.reader.prepared.release_id:
                raise ValueError("declaration parser must belong to the selected private release")
            passage = passages[item.passage_id]
            body = ctx.reader.retained_declaration_parser(item.parser)
            frame = ctx.reader.structural_source_frame(cfg.inputs, passage.source_ref)
            found.append(
                replay_declaration_chain(
                    body,
                    body["parse_detail"],
                    frame,
                    refs[passage.source_ref],
                    passage,
                    item.parser,
                    configuration=body["configuration"],
                )
            )
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


class DeclarationNotQualified(ValueError):
    """An available role population does not establish the selected definition."""


def _require(value):
    if not value:
        raise DeclarationNotQualified(
            "retained roles do not establish one complete declaration chain"
        )


def _absolute(token: ProviderToken, base: int) -> tuple[int, int]:
    if token.start is None or token.end is None:
        raise DeclarationNotQualified("native sentence includes unmapped tokens")
    return base + token.start, base + token.end


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


@dataclass(frozen=True)
class _Sentence:
    context: NativeSourceContext
    number: int
    words: tuple[str, ...]
    lemmas: tuple[str, ...]
    tags: tuple[str, ...]
    heads: tuple[int | None, ...]
    relations: tuple[str, ...]
    children: tuple[tuple[int, ...], ...]
    positions: tuple[tuple[int, int], ...]
    frames: Mapping[int, _Frame]
    locations: Mapping[str, Any]

    def frame_key(self, predicate):
        return f"s{self.number}/predicate/{predicate}"

    def child(self, head, relation):
        found = [i for i in self.children[head] if self.relations[i] == relation]
        _require(len(found) == 1)
        return found[0]

    def frame(self, predicate, voice):
        frame = self.frames.get(predicate)
        if frame is None or frame.voice != voice or len(frame.srl_frames) != 1:
            raise DeclarationNotQualified("missing unique retained UD/SRL frame")
        self.located(frame.predicate)
        return frame

    def located(self, key):
        location = self.locations.get(key)
        if not isinstance(location, MappedSource):
            raise DeclarationNotQualified("role lacks exact projected source evidence")
        try:
            for piece in location.pieces:
                evidence_anchor(self.context, piece, native=True)
        except ContextRefused as exc:
            raise DeclarationNotQualified("role lacks exact native source evidence") from exc
        return location

    def bounds(self, key):
        self.located(key)
        match = re.fullmatch(rf"s{self.number}/span/([0-9]+)-([0-9]+)", key)
        if match is None:
            raise DeclarationNotQualified("role is not one ordered token interval")
        return tuple(map(int, match.groups()))

    def srl(self, frame, role):
        return tuple(
            self.bounds(arg.location) for arg in frame.srl_frames[0].arguments if arg.role == role
        )

    def below(self, token, ancestor):
        while self.heads[token] is not None:
            token = self.heads[token]
            if token == ancestor:
                return True
        return False

    def neutral_act(self, start, end, allowed=()):
        def neutral(i):
            word = self.words[i].casefold()
            if word in _QUOTES:
                return False
            if any(left <= i < right for left, right in allowed):
                return True
            return word not in _SCOPE_MARKERS and self.relations[i] not in {"advcl", "neg"}

        _require(all(neutral(i) for i in range(start, end)))

    def intro(self, start, *, terminal, coordinated=False):
        """Recognize an overt introduction and its native copular binding."""
        _require(
            self.lemmas[start] == "let"
            and self.relations[start] in ({"conj"} if coordinated else {"root", "dep", "parataxis"})
        )
        copular_head = self.child(start, "ccomp")
        copula = self.child(copular_head, "cop")
        subject = self.child(copular_head, "nsubj")
        frame = self.frame(copula, "copular")
        _require(
            frame.syntactic_head == copular_head
            and subject == start + 1
            and copula == subject + 1
            and self.words[subject].isidentifier()
            and self.tags[subject] in {"NN", "NNS", "NNP", "NNPS"}
            and self.srl(frame, "ARG1") == ((subject, subject + 1),)
        )
        roles = self.srl(frame, "ARG2")
        _require(
            bool(roles)
            and all(copula < a < b <= terminal for a, b in roles)
            and sorted(i for a, b in roles for i in range(a, b))
            == list(range(copula + 1, terminal))
            and any(a <= copular_head < b for a, b in roles)
        )
        return copula, subject, copular_head, roles


def _sentences(mapping, reply, base, parsed):
    frames: dict[int, dict[int, _Frame]] = {}
    for product in parsed.products:
        if product.semantic_type == "linguistic.predicate_frame":
            frame = _Frame.model_validate_json(json.dumps(product.value))
            frames.setdefault(frame.sentence, {})[frame.predicate_token] = frame
    native = reply["native"]
    for number, (lemmas, tags, arcs) in enumerate(
        zip(_head(native, "lem"), _head(native, "pos"), _head(native, "dep"), strict=True)
    ):
        tokens = mapping.sentence_tokens(number)
        heads, relations, children = _dependency_graph(arcs, len(tokens))
        yield _Sentence(
            mapping.mapping.context,
            number,
            tuple(token.text for token in tokens),
            tuple(lemma.strip().casefold() for lemma in lemmas),
            tuple(tags),
            heads,
            relations,
            children,
            tuple(_absolute(token, base) for token in tokens),
            frames.get(number, {}),
            parsed.locations,
        )


def declaration_chain(
    mapping: PM2TokenMap,
    request: Mapping[str, Any],
    reply: Mapping[str, Any],
    passage: StructuralPassage,
    *,
    parsed: ParserProducts | None = None,
) -> DeclarationChain:
    """Withhold when a local introduction, parameter use, or naming role is ambiguous."""
    if mapping.layout is None or mapping.layout.outcome == "ambiguous":
        raise DeclarationNotQualified("declaration chain requires the released HanLP layout")
    (scope,) = mapping.mapping.context.pieces
    if not isinstance(scope, SourceSlice):
        raise DeclarationNotQualified("declaration chain requires an exact source slice")
    base = scope.start
    _require(
        base <= passage.start < passage.end <= scope.end
        and mapping.mapping.context.primary.text[passage.start : passage.end] == passage.text
    )
    candidates = tuple(
        sentence
        for sentence in _sentences(
            mapping, reply, base, parsed or hanlp_products(mapping, request, reply)
        )
        if sentence.positions[0][0] < passage.end
        and passage.start < sentence.positions[-1][1] <= passage.end
    )
    if len(candidates) != 3:
        raise DeclarationNotQualified("chain requires three consecutive complete local sentences")
    declarations, construction, naming = candidates
    _require(
        (construction.number, naming.number) == (declarations.number + 1, declarations.number + 2)
    )
    first = next((i for i, row in enumerate(declarations.positions) if row[0] == passage.start), -1)
    _require(
        0 <= first < len(declarations.words) - 3
        and declarations.words[first].casefold() == "definition"
        and bool(_LABEL_NUMBER.fullmatch(declarations.words[first + 1]))
        and all(s.words[-1] == "." for s in candidates)
    )
    intros = tuple(
        i for i in range(first + 2, len(declarations.words)) if declarations.lemmas[i] == "let"
    )
    _require(1 <= len(intros) <= 4 and intros[0] == first + 2)
    if declarations.heads[intros[0]] not in {None, first}:
        raise DeclarationNotQualified("first introduction does not belong to the numbered act")
    declared = []
    for index, intro in enumerate(intros):
        end = intros[index + 1] if index + 1 < len(intros) else len(declarations.words) - 1
        if index:
            _require(
                declarations.heads[intro] == intros[0]
                and declarations.words[intro - 1].casefold() == "and"
                and declarations.relations[intro - 1] == "cc"
            )
        while end > intro and declarations.words[end - 1].casefold() in {",", ";", "and"}:
            end -= 1
        copula, subject, _, allowed = declarations.intro(intro, terminal=end, coordinated=index > 0)
        declarations.neutral_act(intro, end, allowed)
        declared.append((copula, subject, declarations.words[subject]))
    _require(len({word for _, _, word in declared}) == len(declared))

    construct, subject, head, allowed = construction.intro(0, terminal=len(construction.words) - 1)
    _require(construction.heads[0] is None)
    construction.neutral_act(0, len(construction.words) - 1, allowed)
    constructed = construction.words[subject]
    _require(constructed not in {word for _, _, word in declared})
    relative = construction.child(head, "acl:relcl")
    relative_frame = construction.frame(relative, "active")
    obj = construction.child(relative, "obj")
    _require(any(a <= obj < b for a, b in construction.srl(relative_frame, "ARG1")))
    uses = []
    for copula, declaration_subject, name in declared:
        positions = [i for i, word in enumerate(construction.words) if word == name]
        _require(len(positions) == 1 and construction.below(positions[0], relative))
        uses.append(
            DeclarationChainBinding(
                frame=declarations.frame_key(copula),
                subject_token=declaration_subject,
                use_token=positions[0],
            )
        )
    ordered_uses = sorted(row.use_token for row in uses)
    first_use = ordered_uses[0]
    governor = construction.heads[first_use]
    _require(
        construction.relations[first_use] == "nmod"
        and governor is not None
        and construction.relations[governor] == "obl"
        and all(
            construction.relations[i] == "conj" and construction.heads[i] == first_use
            for i in ordered_uses[1:]
        )
    )

    predicate = naming.heads.index(None)
    _require(naming.lemmas[predicate] in {"call", "name"})
    frame = naming.frame(predicate, "passive")
    nominal = naming.child(predicate, "nsubj:pass")
    term_head = naming.child(predicate, "xcomp")
    naming.child(predicate, "aux:pass")
    antecedent = naming.child(nominal, "nmod")
    _require(
        naming.words[antecedent] == constructed
        and naming.words.count(constructed) == 1
        and naming.words[naming.child(antecedent, "case")].casefold() == "of"
    )
    subj_roles, term_roles = naming.srl(frame, "ARG1"), naming.srl(frame, "ARG2")
    _require(len(subj_roles) == len(term_roles) == 1)
    ((subj_a, subj_b),), ((term_a, term_b),) = subj_roles, term_roles
    _require(
        subj_a <= nominal < antecedent < subj_b <= predicate < term_a <= term_head < term_b
        and term_b == len(naming.words) - 1
        and all(word.casefold() == "then" for word in naming.words[:subj_a])
        and all(naming.relations[i] == "aux:pass" for i in range(subj_b, predicate))
        and not any(
            role.role.startswith("ARGM-") and role.role != "ARGM-DIS"
            for role in frame.srl_frames[0].arguments
        )
    )
    naming.neutral_act(0, len(naming.words) - 1)
    if naming.relations[term_a] == "det" and naming.heads[term_a] == term_head:
        term_a += 1

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
        term=span(naming.positions[term_a][0], naming.positions[term_b - 1][1]),
        content=span(declarations.positions[intros[0]][0], naming.positions[subj_b - 1][1]),
        bindings=tuple(uses),
        construction_frame=construction.frame_key(construct),
        construction_subject_token=subject,
        naming_frame=naming.frame_key(predicate),
        naming_antecedent_token=antecedent,
    )


def _verify_layout(mapping: PM2TokenMap, source, scope: SourceSlice):
    """Recover the one declared canonical difference and replay its native seam."""
    layout = mapping.layout
    if layout is None or layout.outcome == "ambiguous":
        raise DeclarationNotQualified("declaration chain lacks a unique source layout")
    absolute = [_absolute(token, scope.start) for token in mapping.tokens]
    atoms = {
        (scope.start + start, scope.start + end) for start, end in mapping.mapping.protected_atoms
    }
    original = [
        TextToken(a, b, source.text[b : b + 1] == " ", "math" if (a, b) in atoms else "prose")
        for a, b in absolute
    ]
    if not mapping.tokens:
        raise ValueError("declaration report has no native tokens")
    bounds = []
    for number in range(mapping.tokens[-1].sentence + 1):
        tokens = mapping.sentence_tokens(number)
        if not tokens:
            raise ValueError("declaration report has an empty sentence")
        bounds.append((_absolute(tokens[0], scope.start)[0], _absolute(tokens[-1], scope.start)[1]))
    canonical = list(bounds)
    if layout.repair is not None:
        repair = layout.repair
        a, b = repair.orphan_sentence
        seam = repair.punctuation_start
        pos = absolute.index((a, seam))
        if absolute[pos + 1] != (seam, b) or {(a, seam), (seam, b)} & atoms:
            raise ValueError("declaration report lacks its exact unprotected split")
        original[pos : pos + 2] = [TextToken(a, b, original[pos + 1].space)]
        sentence = canonical.index((repair.previous_sentence[0], b))
        canonical[sentence : sentence + 1] = [repair.previous_sentence, repair.orphan_sentence]
    pieces = json.loads(source.native_context)["pieces"]
    effective, replayed, decision = hanlp_seam_layout(
        source.text, (scope.start, scope.end), tuple(original), canonical, pieces
    )
    if (
        decision != layout
        or replayed != tuple(bounds)
        or tuple((token.start, token.end) for token in effective) != tuple(absolute)
    ):
        raise ValueError("declaration report differs from exact native seam replay")


def replay_declaration_chain(
    body: Mapping[str, Any],
    detail: Mapping[str, Any],
    source,
    source_ref: ExternalSourceRef,
    passage: StructuralPassage,
    reference: RetainedContributionRef,
    *,
    configuration: Mapping[str, Any] | None = None,
):
    """Rebind the original retained operation to its source before replaying its roles."""
    report = detail["pm2_native"]
    (operation,) = body["contribution_operations"]
    if (
        body["method"] != "extract.pm2_hanlp"
        or body["operation_version"] != "2"
        or body["release_id"] != reference.release_id
        or reference.project_id != source_ref.project_id
        or body["source"] != source.unit_ref
        or body["input_hash"] != report["input_digest"]
        or operation["question"] != PARSER_QUESTIONS["hanlp"]
        or operation["operation_version"] != "2"
        or operation["outcome"] != "succeeded"
        or report["native"]["outcome"] != "succeeded"
        or operation["report_digest"] != sha256(canonical_bytes(report)).hexdigest()
        or source.source_view_id != source_ref.source_view_id
        or source.native_product.task_id != source_ref.native_task_id
        or source.native_product.product_key != source_ref.native_product_key
        or source.native_product.content_digest != source_ref.native_content_digest
        or source.projection_digest != source_ref.projection_digest
        or source.recipe_digest != source_ref.recipe_digest
        or source.version != source_ref.coordinate_version
    ):
        raise ValueError("declaration parser differs from its exact retained operation or source")
    native_map = report["source_map"]
    (scope,) = (SourceSlice(**row) for row in native_map["context_pieces"])
    context = NativeSourceContext(
        source,
        (),
        (scope,),
        "private parser",
        "pm2-parser-scope-1",
        "explicit selected source scope",
        max_chars=65_536,
        max_pieces=1024,
        version=2,
        preparation=PreparedNativeSources((source,)),
    )
    (segment,) = (SourceMapSegment(**row) for row in native_map["segments"])
    if (
        segment != SourceMapSegment(0, len(context.text), 0)
        or scope.source_view_id != source.source_view_id
        or report["scope_digest"] != context.dependency_digest
    ):
        raise ValueError("declaration parser source map is not an exact native copy")
    native = json.loads(source.native_context)
    formula_items = {row["self_ref"] for row in native["items"] if row.get("label") == "formula"}
    protected = tuple(
        (piece["start"] - scope.start, piece["end"] - scope.start)
        for piece in native["pieces"]
        if piece.get("item_ref") in formula_items
        and piece["start"] < scope.end
        and scope.start < piece["end"]
    )
    if tuple(tuple(row) for row in native_map["protected_atoms"]) != protected:
        raise ValueError("declaration parser protected tokens differ from retained source atoms")
    mapping = PM2SourceMap(context, context.text, (segment,), protected)
    if report["source_map_digest"] != mapping.input_digest:
        raise ValueError("declaration parser source map digest differs")
    tokens = _TOKENS.validate_python(native_map["tokens"])
    effective = PM2TokenMap(mapping, tokens, _LAYOUT.validate_python(native_map["layout"]))
    if effective.layout is None or effective.layout.outcome != "repaired":
        raise DeclarationNotQualified("released declaration route requires an exact repaired seam")
    _verify_layout(effective, source, scope)
    if configuration is not None:
        from .pm2_result import pm2_input_digest

        startup = configuration.get("startup")
        if (
            configuration.get("layout_policy") != HANLP_SEAM_LAYOUT
            or configuration.get("provider") != "hanlp"
            or not isinstance(startup, Mapping)
            or report["effective_profile_digest"] != sha256(canonical_bytes(startup)).hexdigest()
            or body["input_hash"]
            != pm2_input_digest(
                effective,
                startup,
                report["request"],
                question=PARSER_QUESTIONS["hanlp"],
                operation_version="2",
            )
        ):
            raise ValueError("declaration parser input differs from its exact configured layout")
    parsed = hanlp_products(effective, report["request"], report["native"])
    chain = declaration_chain(
        effective, report["request"], report["native"], passage, parsed=parsed
    )
    rows = {row["item_key"]: row for row in body["contributions"]}
    products = {row.key: row for row in parsed.products}
    if len(rows) != len(body["contributions"]):
        raise ValueError("declaration parser repeats its original role keys")
    pin = record_source_pin(source)
    keys = (chain.naming_frame, chain.construction_frame, *(item.frame for item in chain.bindings))
    for key in keys:
        row = rows.get(key)
        expected = products[key]
        if (
            row is None
            or row["operation_key"] != operation["operation_key"]
            or row["pin"] != pin
            or row["contract"] != "PM2HanLPFrameContributionV1"
            or row["semantic_type"] != "linguistic.predicate_frame"
            or not row.get("members")
            or contribution_identity(row) != row["contribution_id"]
            or tuple(row.get("computation_dependencies", ())) != (body["input_hash"],)
            or canonical_bytes(source_python(row["value"]))
            != canonical_bytes(
                {
                    **parser_value_for_contract(expected.semantic_type, expected.value),
                    "location_keys": list(expected.members),
                    "unlocated_members": [
                        member for member in expected.members if member not in rows
                    ],
                }
            )
            or tuple(row["members"])
            != tuple(
                rows[member]["contribution_id"] for member in expected.members if member in rows
            )
        ):
            raise ValueError("declaration frame lacks its original typed retained role")
    if rows[chain.naming_frame]["contribution_id"] != reference.contribution_id:
        raise ValueError("declaration witness names a different retained predicate")
    return definition_component(
        term=chain.term,
        content=chain.content,
        interpretation="definition",
        basis="declaration_chain",
        declaration_chain=DeclarationChainWitness(
            version=CHAIN_VERSION,
            parser=reference,
            scope_digest=context.dependency_digest,
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
        reason="The definition joins exact introduced roles to their local uses and naming.",
    )
