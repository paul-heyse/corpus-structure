"""Read an explicit local declaration chain from retained HanLP roles."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from itertools import pairwise
from typing import Any, Self

from pydantic import Field, model_validator

from corpus_structure.core.method import Digest, Resources, UnitRef, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.source_contexts import (
    ContextRefused,
    NativeSourceContext,
    NativeSpanEvidence,
    SourceSlice,
    evidence_anchor,
    record_source_pin,
)
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

from .pm2_hanlp_products import _dependency_graph, _Frame
from .pm2_source import MappedSource

CHAIN_VERSION = "definition-declaration-chain-2"
CHAIN_METHOD = "structure.definition_declaration_components"
_LABEL_NUMBER = re.compile(r"[0-9]+(?:\.[0-9]+)*")
_SCOPE_MARKERS = frozenset(
    {"if", "unless", "although", "except", "not", "never", "reportedly", "allegedly"}
)
_QUOTES = frozenset({'"', "\u201c", "\u201d", "\u2018", "\u2019", "``", "''"})


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
        found = []
        for item in cfg.selections:
            ctx.check_active()
            passage = passages[item.passage_id]
            source_ref = refs[passage.source_ref]
            view = ctx.reader.source_view(source_ref.source_view_id)
            layers = ctx.reader.primary_characterization(
                source_ref.source_view_id,
                families=(
                    "hanlp.tokens",
                    "hanlp.lemma",
                    "hanlp.pos",
                    "hanlp.dependency",
                    "hanlp.srl",
                    "construction.source_readings",
                ),
            )
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


class DeclarationNotQualified(ValueError):
    """An available role population does not establish the selected definition."""


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
    primary_keys: Mapping[int, str] | None = None

    def frame_key(self, predicate):
        return (
            self.primary_keys[predicate]
            if self.primary_keys is not None
            else f"s{self.number}/predicate/{predicate}"
        )

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


def _declaration_chain_from_sentences(candidates, passage):
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


def primary_declaration_component(layers, view, passage):
    """Apply domain declaration checks to exact native roles and primary voice nodes."""
    from corpus_structure.semantic.characterization import annotation_reference
    from corpus_structure.semantic.constructions.retained_rules import PRIMARY_RULE_VOCABULARY
    from corpus_structure.semantic.proposals import native_source_frame

    source = native_source_frame(view, ())
    if (
        not 0 <= passage.start < passage.end <= len(view.text)
        or view.text[passage.start : passage.end] != passage.text
    ):
        raise DeclarationNotQualified("declaration passage differs from exact source")
    context = NativeSourceContext(
        source,
        (),
        (SourceSlice(view.ref.id, passage.start, passage.end),),
        "primary declaration roles",
        "primary-declaration-roles-1",
        "exact selected passage",
        max_chars=len(passage.text),
        max_pieces=1024,
    )
    evidence, voices, native_sentences = [], {}, []
    for pin, report in layers.items():
        if report.reference(pin.task_id) != pin or report.base_document != view.ref.native_product:
            raise DeclarationNotQualified("declaration primary layer pin or base differs")
        body = report.payload
        occurrences = {row["local_id"]: row for row in body["occurrences"]}

        def extents(node, *, occurrences=occurrences):
            values = [
                part for key in node.get("occurrences", ()) for part in occurrences[key]["extents"]
            ]
            if not values or any(
                part.get("synthetic")
                or part["source_view_id"] != view.ref.id
                or part["projection"] != view.ref.projection_digest
                or part.get("text") != view.text[part.get("start", -1) : part.get("end", -1)]
                for part in values
            ):
                raise DeclarationNotQualified(
                    "declaration native role has no exact selected source"
                )
            return tuple((part["start"], part["end"]) for part in values)

        terms = {row["local_id"]: row for row in body["terms"]}
        for term in terms.values():
            if term["kind"] != "predicate" or term["vocabulary"] != PRIMARY_RULE_VOCABULARY:
                continue
            members = {
                edge["role"]: terms[edge["target"]]
                for edge in term.get("children", ())
                if "target" in edge
            }
            if "predicate" not in members or "voice" not in members:
                continue
            spans = extents(members["predicate"])
            if len(spans) == 1 and passage.start <= spans[0][0] < spans[0][1] <= passage.end:
                coverage = next(
                    (
                        row
                        for row in body["coverage"]
                        if row["family"] == "construction.source_readings"
                    ),
                    None,
                )
                if (
                    coverage is None
                    or coverage["availability"] != "available"
                    or coverage["outcome"] not in {"complete", "empty"}
                    or coverage.get("unexamined")
                ):
                    raise DeclarationNotQualified(
                        "declaration primary voice coverage is incomplete"
                    )
                voices.setdefault(spans[0], []).append(
                    (members["voice"]["value"], annotation_reference(pin, term["local_id"]))
                )
        runs = {
            row["local_id"] for row in body.get("native_runs", ()) if row["provider"] == "hanlp"
        }
        annotations = {row["local_id"]: row for row in body["annotations"]}
        sentences = {}
        for row in annotations.values():
            token = row.get("native_token")
            if token is not None and token["native_run"] in runs:
                sentences.setdefault(token["sentence"], []).append(row)
        for sentence, rows in sentences.items():
            rows.sort(key=lambda row: row["native_token"]["index"])
            spans = [extents(row) for row in rows]
            if any(len(parts) != 1 for parts in spans):
                raise DeclarationNotQualified("declaration native token is discontinuous")
            positions = tuple(parts[0] for parts in spans)
            if positions[0][0] >= passage.end or positions[-1][1] <= passage.start:
                continue
            if not passage.start <= positions[0][0] < positions[-1][1] <= passage.end:
                raise DeclarationNotQualified("declaration passage cuts a native sentence")
            if [row["native_token"]["index"] for row in rows] != list(range(len(rows))):
                raise DeclarationNotQualified("declaration native token population is incomplete")
            for family in (
                "hanlp.tokens",
                "hanlp.lemma",
                "hanlp.pos",
                "hanlp.dependency",
                "hanlp.srl",
            ):
                coverage = next((row for row in body["coverage"] if row["family"] == family), None)
                if (
                    coverage is None
                    or coverage["availability"] != "available"
                    or coverage["outcome"] not in {"complete", "empty"}
                    or coverage.get("unexamined")
                    or not any(
                        selector["projection"] == view.ref.projection_digest
                        and selector.get("start", 0) <= positions[0][0]
                        and selector.get("end", len(view.text)) >= positions[-1][1]
                        for selector in coverage["examined"]
                    )
                ):
                    raise DeclarationNotQualified("declaration native role coverage is incomplete")
            native_sentences.append(
                (positions[0][0], pin, body, annotations, sentence, rows, positions)
            )
    native_sentences.sort(key=lambda row: row[0])
    if len(native_sentences) != 3 or any(
        left[0] == right[0] for left, right in pairwise(native_sentences)
    ):
        raise DeclarationNotQualified("declaration requires three unique exact native sentences")
    sentences = []
    for number, (_start, pin, body, annotations, _sentence, rows, positions) in enumerate(
        native_sentences
    ):
        tokens = [row["native_token"] for row in rows]
        if any(
            not all(
                key in token
                for key in ("lemma", "tag", "dependency", "native_head", "head_index_base")
            )
            or token["head_index_base"] != 1
            for token in tokens
        ):
            raise DeclarationNotQualified("declaration native token columns are unavailable")
        heads, relations, children = _dependency_graph(
            [[token["native_head"], token["dependency"]] for token in tokens], len(tokens)
        )
        references = {row["local_id"]: index for index, row in enumerate(rows)}
        locations = {}

        def located(a, b, *, number=number, positions=positions, locations=locations):
            key = f"s{number}/span/{a}-{b}"
            start, end = positions[a][0], positions[b - 1][1]
            pieces = tuple(
                context.map_span(
                    start - passage.start,
                    end - passage.start,
                    literal=view.text[start:end],
                    allow_multiple=True,
                )
            )
            native_pieces = tuple(
                piece for piece in pieces if isinstance(piece, NativeSpanEvidence)
            )
            if len(native_pieces) != len(pieces):
                raise DeclarationNotQualified(
                    "declaration role has no original native character correspondence"
                )
            anchors = tuple(
                evidence_anchor(context, piece, native=True)[0] for piece in native_pieces
            )
            locations[key] = MappedSource(
                context.dependency_digest,
                context.dependency_digest,
                context.dependency_digest,
                (),
                native_pieces,
                anchors,
                (),
            )
            return key

        memberships = body["memberships"]
        groups = {}
        keys = {}
        for group in annotations.values():
            if group["kind"] != "native.srl_group":
                continue
            args, predicate = [], None
            group_evidence = [annotation_reference(pin, group["local_id"])]
            for member in sorted(
                (row for row in memberships if row["group"] == group["local_id"]),
                key=lambda row: row.get("order", 0),
            ):
                role = annotations.get(member["member"])
                if role is None or role["kind"] != "native.srl_role":
                    raise DeclarationNotQualified("declaration native SRL member is missing")
                ids = [
                    row["member"]
                    for row in sorted(
                        (
                            row
                            for row in memberships
                            if row["group"] == role["local_id"] and row["role"] == "token"
                        ),
                        key=lambda row: row.get("order", 0),
                    )
                ]
                if not ids or not all(key in references for key in ids):
                    if any(key in references for key in ids):
                        raise DeclarationNotQualified("declaration native SRL crosses sentences")
                    args = []
                    break
                indices = tuple(references[key] for key in ids)
                if indices != tuple(range(indices[0], indices[-1] + 1)):
                    raise DeclarationNotQualified(
                        "declaration native SRL is not an ordered token interval"
                    )
                location = located(indices[0], indices[-1] + 1)
                label = role["native_label"]
                if label == "PRED":
                    if predicate is not None or len(indices) != 1:
                        raise DeclarationNotQualified(
                            "declaration native SRL has no unique predicate"
                        )
                    predicate = indices[0]
                else:
                    args.append(dict(role=label, location=location, head=None))
                group_evidence.append(annotation_reference(pin, role["local_id"]))
            if predicate is None or not args:
                continue
            span = positions[predicate]
            offered = voices.get(span, ())
            if len(offered) != 1 or offered[0][0] not in {"active", "passive", "copular"}:
                raise DeclarationNotQualified("declaration lacks one exact retained primary voice")
            _voice, voice_ref = offered[0]
            predicate_location = located(predicate, predicate + 1)
            groups.setdefault(predicate, []).append(
                dict(predicate=predicate_location, arguments=args)
            )
            keys[predicate] = annotation_reference(pin, group["local_id"]).identity
            evidence.extend([*group_evidence, voice_ref])
        frames = {}
        for predicate, srl in groups.items():
            frames[predicate] = _Frame.model_validate_json(
                json.dumps(
                    dict(
                        sentence=number,
                        predicate_token=predicate,
                        syntactic_head=heads[predicate]
                        if relations[predicate] == "cop"
                        else predicate,
                        predicate=located(predicate, predicate + 1),
                        focus=located(0, len(tokens)),
                        voice=voices[positions[predicate]][0][0],
                        dependency_arguments=[],
                        srl_frames=srl,
                    )
                )
            )
        evidence.extend(annotation_reference(pin, row["local_id"]) for row in rows)
        sentences.append(
            _Sentence(
                context,
                number,
                tuple(token["text"] for token in tokens),
                tuple(token["lemma"].casefold() for token in tokens),
                tuple(token["tag"] for token in tokens),
                heads,
                relations,
                children,
                positions,
                frames,
                locations,
                keys,
            )
        )
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
