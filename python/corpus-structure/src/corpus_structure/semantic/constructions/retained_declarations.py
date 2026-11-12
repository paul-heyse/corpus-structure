"""Primary, source-located declaration syntax characterized from retained HanLP evidence.

Domain chain selection remains in methods.definition_declaration. This producer owns
all lexical, UD and SRL recognition used by that consumer.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from itertools import pairwise
from typing import Any

from corpus_structure.methods.pm2_hanlp_products import _dependency_graph
from corpus_structure.methods.pm2_source import MappedSource
from corpus_structure.semantic.characterization import annotation_reference
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.source_contexts import (
    ContextRefused,
    NativeSourceContext,
    NativeSpanEvidence,
    SourceSlice,
    evidence_anchor,
)

from .forest import identity
from .retained_rules import PRIMARY_RULE_VOCABULARY

DECLARATION_FAMILY = "construction.declaration_syntax"

_SCOPE_MARKERS = frozenset(
    {"if", "unless", "although", "except", "not", "never", "reportedly", "allegedly"}
)
_QUOTES = frozenset({'"', "\u201c", "\u201d", "\u2018", "\u2019", "``", "''"})


class DeclarationNotQualified(ValueError):
    pass


def _require(value):
    if not value:
        raise DeclarationNotQualified("native roles do not establish declaration syntax")


@dataclass(frozen=True)
class _Argument:
    role: str
    location: str


@dataclass(frozen=True)
class _SRL:
    arguments: tuple[_Argument, ...]


@dataclass(frozen=True)
class _Frame:
    syntactic_head: int
    predicate: str
    voice: str
    srl_frames: tuple[_SRL, ...]


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
    evidence: tuple = ()

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


def _prepare_sentences(layers, view, passage):
    """Decode and index each immutable dependency once for this characterization."""
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
    prepared = {}
    for pin, report in layers.items():
        body = report.payload
        if (
            report.reference(pin.task_id) != pin
            or body["base_document"] != view.ref.native_product.values()
        ):
            raise DeclarationNotQualified("declaration primary layer pin or base differs")
        runs = {
            row["local_id"] for row in body.get("native_runs", ()) if row["provider"] == "hanlp"
        }
        if not runs:
            continue
        native_annotations = {row["local_id"]: row for row in body["annotations"]}
        occurrences = {row["local_id"]: row for row in body["occurrences"]}
        memberships = {}
        for row in body["memberships"]:
            memberships.setdefault(row["group"], []).append(row)
        sentences, token_keys = {}, {}
        for row in native_annotations.values():
            token = row.get("native_token")
            if token is not None and token["native_run"] in runs:
                key = (token["native_run"], token["container"], token["sentence"])
                sentences.setdefault(key, []).append(row)
                token_keys[row["local_id"]] = key
        groups = {}
        for group in native_annotations.values():
            if group["kind"] != "native.srl_group":
                continue
            keys = {
                token_keys[token["member"]]
                for member in memberships.get(group["local_id"], ())
                for token in memberships.get(member["member"], ())
                if token["role"] == "token" and token["member"] in token_keys
            }
            if not keys:
                # Native IDs locate the enclosing sentence even when its role support
                # is missing entirely. They are used only to route a local refusal.
                keys = {key for key in sentences if group["local_id"].startswith(key[1] + "/srl/")}
            for key in keys:
                groups.setdefault(key, []).append(group)
        prepared[pin] = (body, native_annotations, occurrences, memberships, sentences, groups)
    return context, prepared


def _sentences(layers, view, passage, *, sentence_key=None, prepared=None):
    context, indexed = (
        prepared if prepared is not None else _prepare_sentences(layers, view, passage)
    )
    evidence, native_sentences = [], []
    for pin, (
        body,
        native_annotations,
        occurrences,
        memberships,
        population,
        group_index,
    ) in indexed.items():

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

        sentences = (
            population
            if sentence_key is None
            else (
                {sentence_key[1]: population[sentence_key[1]]}
                if sentence_key[0] == pin and sentence_key[1] in population
                else {}
            )
        )
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
                    or coverage["outcome"] not in {"complete", "empty", "partial"}
                    or any(
                        selector.get("projection") == view.ref.projection_digest
                        and selector.get("start", 0) < positions[-1][1]
                        and selector.get("end", len(view.text)) > positions[0][0]
                        for selector in coverage.get("unexamined", ())
                    )
                    or not any(
                        selector["projection"] == view.ref.projection_digest
                        and selector.get("start", 0) <= positions[0][0]
                        and selector.get("end", len(view.text)) >= positions[-1][1]
                        for selector in coverage["examined"]
                    )
                ):
                    raise DeclarationNotQualified("declaration native role coverage is incomplete")
            native_sentences.append(
                (
                    positions[0][0],
                    pin,
                    body,
                    native_annotations,
                    sentence,
                    rows,
                    positions,
                    memberships,
                    group_index,
                )
            )
    native_sentences.sort(key=lambda row: row[0])
    if any(left[0] == right[0] for left, right in pairwise(native_sentences)):
        raise DeclarationNotQualified("declaration requires unique exact native sentences")
    sentences = []
    for number, (
        _start,
        pin,
        _body,
        native_annotations,
        _sentence,
        rows,
        positions,
        memberships,
        group_index,
    ) in enumerate(native_sentences):
        evidence_start = len(evidence)
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

        groups: dict[int, list[dict[str, Any]]] = {}
        keys = {}
        for group in group_index.get(_sentence, ()):
            args, predicate = [], None
            group_evidence = [annotation_reference(pin, group["local_id"])]
            for member in sorted(
                memberships.get(group["local_id"], ()),
                key=lambda row: row.get("order", 0),
            ):
                role = native_annotations.get(member["member"])
                if role is None or role["kind"] != "native.srl_role":
                    raise DeclarationNotQualified("declaration native SRL member is missing")
                ids = [
                    row["member"]
                    for row in sorted(
                        (
                            row
                            for row in memberships.get(role["local_id"], ())
                            if row["role"] == "token"
                        ),
                        key=lambda row: row.get("order", 0),
                    )
                ]
                if not ids or not all(key in references for key in ids):
                    raise DeclarationNotQualified(
                        "declaration native SRL has missing or cross-sentence token support"
                    )
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
            if predicate is None:
                raise DeclarationNotQualified("declaration native SRL has no retained predicate")
            predicate_location = located(predicate, predicate + 1)
            groups.setdefault(predicate, []).append(
                dict(predicate=predicate_location, arguments=args)
            )
            keys[predicate] = annotation_reference(pin, group["local_id"]).identity
            evidence.extend(group_evidence)
        frames = {}
        for predicate, srl in groups.items():
            syntactic_head = heads[predicate] if relations[predicate] == "cop" else predicate
            if syntactic_head is None:
                raise DeclarationNotQualified("copular predicate lacks its native syntactic head")
            frames[predicate] = _Frame(
                syntactic_head,
                located(predicate, predicate + 1),
                "copular"
                if relations[predicate] == "cop"
                else "passive"
                if any(relations[i] == "aux:pass" for i in children[predicate])
                else "active",
                tuple(
                    _SRL(tuple(_Argument(arg["role"], arg["location"]) for arg in row["arguments"]))
                    for row in srl
                ),
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
                tuple(evidence[evidence_start:]),
            )
        )
    return tuple(sentences), tuple(dict.fromkeys(evidence))


def _facts(sentence):
    """Characterize local syntax independently of a definition label or chain."""
    intros = []
    starts = [i for i, lemma in enumerate(sentence.lemmas) if lemma == "let"]
    for order, start in enumerate(starts):
        end = starts[order + 1] if order + 1 < len(starts) else len(sentence.words) - 1
        while end > start and sentence.words[end - 1].casefold() in {",", ";", "and"}:
            end -= 1
        coordinated = sentence.relations[start] == "conj"
        try:
            copula, subject, head, allowed = sentence.intro(
                start, terminal=end, coordinated=coordinated
            )
            sentence.neutral_act(start, end, allowed)
        except DeclarationNotQualified, ValueError, IndexError:
            continue
        parent = sentence.heads[start]
        intro = dict(
            start=start,
            end=end,
            copula=copula,
            subject=subject,
            head=head,
            parent=parent,
            coordinated=coordinated,
            coordinate_cue=(
                start > 0
                and sentence.words[start - 1].casefold() == "and"
                and sentence.relations[start - 1] == "cc"
            ),
            frame=sentence.frame_key(copula),
        )
        relative = []
        try:
            verb = sentence.child(head, "acl:relcl")
            frame = sentence.frame(verb, "active")
            obj = sentence.child(verb, "obj")
            _require(any(a <= obj < b for a, b in sentence.srl(frame, "ARG1")))
            for token in range(len(sentence.words)):
                governor = sentence.heads[token]
                if (
                    sentence.below(token, verb)
                    and sentence.relations[token] == "nmod"
                    and governor is not None
                    and sentence.relations[governor] == "obl"
                ):
                    uses = [
                        token,
                        *(i for i in sentence.children[token] if sentence.relations[i] == "conj"),
                    ]
                    relative.append(tuple(sorted(uses)))
        except DeclarationNotQualified, ValueError, IndexError:
            pass
        intro["relative_uses"] = tuple(relative)
        intros.append(intro)
    naming = None
    try:
        predicate = sentence.heads.index(None)
        _require(sentence.lemmas[predicate] in {"call", "name"})
        frame = sentence.frame(predicate, "passive")
        nominal = sentence.child(predicate, "nsubj:pass")
        term_head = sentence.child(predicate, "xcomp")
        sentence.child(predicate, "aux:pass")
        antecedent = sentence.child(nominal, "nmod")
        _require(sentence.words[sentence.child(antecedent, "case")].casefold() == "of")
        subj_roles, term_roles = sentence.srl(frame, "ARG1"), sentence.srl(frame, "ARG2")
        _require(len(subj_roles) == len(term_roles) == 1)
        ((subj_a, subj_b),), ((term_a, term_b),) = subj_roles, term_roles
        _require(
            subj_a <= nominal < antecedent < subj_b <= predicate < term_a <= term_head < term_b
            and term_b == len(sentence.words) - 1
            and all(word.casefold() == "then" for word in sentence.words[:subj_a])
            and all(sentence.relations[i] == "aux:pass" for i in range(subj_b, predicate))
            and not any(
                role.role.startswith("ARGM-") and role.role != "ARGM-DIS"
                for role in frame.srl_frames[0].arguments
            )
        )
        sentence.neutral_act(0, len(sentence.words) - 1)
        if sentence.relations[term_a] == "det" and sentence.heads[term_a] == term_head:
            term_a += 1
        naming = dict(
            predicate=predicate,
            antecedent=antecedent,
            subject_end=subj_b,
            term_start=term_a,
            term_end=term_b,
            frame=sentence.frame_key(predicate),
        )
    except DeclarationNotQualified, ValueError, IndexError:
        pass
    return dict(intros=tuple(intros), naming=naming)


def populate_declaration_readings(
    layer, view, dependencies, *, check_active=lambda: None, admitted=lambda start, end: True
):
    """Retain reusable declaration syntax once, before any domain chain is selected."""
    from types import SimpleNamespace

    passage = SimpleNamespace(start=0, end=len(view.text), text=view.text)
    if not any(
        any(run["provider"] == "hanlp" for run in report.payload.get("native_runs", ()))
        for report in dependencies.values()
    ):
        return
    if DECLARATION_FAMILY not in layer.families:
        layer.families = (*layer.families, DECLARATION_FAMILY)
        layer.operation["produced_families"].append(DECLARATION_FAMILY)
    candidates = []
    prepared = _prepare_sentences(dependencies, view, passage)
    for pin, (_body, _annotations, occurrences, _memberships, grouped, _groups) in prepared[
        1
    ].items():
        for key, rows in grouped.items():
            spans = [
                part
                for row in rows
                for oid in row.get("occurrences", ())
                for part in occurrences.get(oid, {}).get("extents", ())
                if part.get("projection") == view.ref.projection_digest
                and "start" in part
                and "end" in part
            ]
            if not spans:
                # No located premise means no sentence can be characterized. It does not
                # invalidate located sibling inventories or their positive coverage.
                continue
            start, end = min(part["start"] for part in spans), max(part["end"] for part in spans)
            if not admitted(start, end):
                continue
            candidates.append(
                ((pin, key), dict(projection=view.ref.projection_digest, start=start, end=end))
            )
    for sentence_key, selector in candidates:
        check_active()
        try:
            sentences, _evidence = _sentences(
                dependencies, view, passage, sentence_key=sentence_key, prepared=prepared
            )
            if len(sentences) != 1:
                raise DeclarationNotQualified("native sentence population is missing or ambiguous")
            (sentence,) = sentences
        except (DeclarationNotQualified, ValueError, KeyError, IndexError) as error:
            layer.record(
                DECLARATION_FAMILY, selector, "unknown", "declaration syntax: " + str(error)
            )
            continue
        layer.record(DECLARATION_FAMILY, selector, "complete")
        facts = _facts(sentence)
        root = identity("declaration-sentence", [view.ref.id, sentence.positions])
        premises = [
            dict(layer=ref.layer.values(), local_id=ref.local_id) for ref in sentence.evidence
        ]

        def emit(value, name, *, positions=(), root=root):
            key = identity("declaration-fact", [root, name])
            children = []
            if isinstance(value, dict):
                kind, label = "operator", "{}"
                children = [
                    dict(role=role, target=emit(item, name + "/" + role), structural=True)
                    for role, item in value.items()
                ]
            elif isinstance(value, (tuple, list)):
                kind, label = "operator", "[]"
                children = [
                    dict(
                        role="item",
                        order=i,
                        target=emit(item, name + "/" + str(i)),
                        structural=True,
                    )
                    for i, item in enumerate(value)
                ]
            else:
                kind, label = "participant", json.dumps(value, ensure_ascii=False)
            layer.terms[key] = dict(
                local_id=key,
                family=DECLARATION_FAMILY,
                kind=kind,
                vocabulary=PRIMARY_RULE_VOCABULARY,
                value=label,
                status="interpreted",
                occurrences=[layer.occurrence(view, a, b) for a, b in positions],
                children=children,
            )
            return key

        data = dict(words=sentence.words, positions=sentence.positions, facts=facts)
        key = emit(
            data,
            "declaration_sentence",
            positions=((sentence.positions[0][0], sentence.positions[-1][1]),),
        )
        layer.terms[key]["value"] = "declaration_sentence"
        layer.terms[key]["external_premises"] = premises
        annotation = identity("declaration-syntax", [root])
        layer.annotations[annotation] = dict(
            local_id=annotation,
            family=DECLARATION_FAMILY,
            kind="construction",
            vocabulary=PRIMARY_RULE_VOCABULARY,
            rule_id="tc.source.declaration_syntax.v1",
            native_scheme="retained-hanlp-declaration-syntax-1",
            native_label="declaration_sentence",
            status="interpreted",
            occurrences=layer.terms[key]["occurrences"],
            external_premises=premises,
        )
        layer.terms[key]["premises"] = [annotation]


def declaration_sentences(layers, view, passage):
    """Read only retained primary facts; no lexical, dependency or SRL recognition."""
    from types import SimpleNamespace

    found, evidence = [], []
    for pin, report in layers.items():
        if report.reference(pin.task_id) != pin or report.base_document != view.ref.native_product:
            raise DeclarationNotQualified("declaration layer differs from exact source")
        body = report.payload
        terms = {row["local_id"]: row for row in body["terms"]}
        occurrences = {row["local_id"]: row for row in body["occurrences"]}

        def read(term: dict[str, Any], *, terms=terms) -> Any:
            children = term.get("children", ())
            if not children:
                return json.loads(term["value"])
            if all(row["role"] == "item" for row in children):
                return tuple(
                    read(terms[row["target"]]) for row in sorted(children, key=lambda r: r["order"])
                )
            return {row["role"]: read(terms[row["target"]]) for row in children}

        for term in terms.values():
            if (
                term.get("vocabulary") != PRIMARY_RULE_VOCABULARY
                or term["value"] != "declaration_sentence"
            ):
                continue
            extents = [part for key in term["occurrences"] for part in occurrences[key]["extents"]]
            if (
                not extents
                or extents[-1]["end"] <= passage.start
                or extents[0]["start"] >= passage.end
            ):
                continue
            if (
                extents[0]["start"] < passage.start
                or extents[-1]["end"] > passage.end
                or any(
                    part.get("synthetic")
                    or part["source_view_id"] != view.ref.id
                    or part["projection"] != view.ref.projection_digest
                    or part["text"] != view.text[part["start"] : part["end"]]
                    for part in extents
                )
            ):
                raise DeclarationNotQualified("declaration passage cuts primary sentence")
            coverage = next(
                (row for row in body["coverage"] if row["family"] == DECLARATION_FAMILY), None
            )
            if (
                coverage is None
                or coverage["availability"] != "available"
                or not any(
                    selector.get("projection") == view.ref.projection_digest
                    and selector.get("start", 0) <= extents[0]["start"]
                    and selector.get("end", len(view.text)) >= extents[-1]["end"]
                    for selector in coverage.get("examined", ())
                )
                or any(
                    selector.get("projection") == view.ref.projection_digest
                    and selector.get("start", 0) < extents[-1]["end"]
                    and selector.get("end", len(view.text)) > extents[0]["start"]
                    for selector in coverage.get("unexamined", ())
                )
            ):
                raise DeclarationNotQualified("declaration primary coverage is incomplete")
            from corpus_structure.semantic.product_reference import ProductReference

            for premise in term.get("external_premises", ()):
                support = layers.get(ProductReference(**premise["layer"]))
                if support is None or premise["local_id"] not in {
                    row["local_id"] for row in support.payload["annotations"]
                }:
                    raise DeclarationNotQualified("declaration native support is unavailable")
            data = read(term)
            if not isinstance(data, dict):
                raise DeclarationNotQualified(
                    "primary declaration sentence is not a structured mapping"
                )
            if (
                len(data["words"]) != len(data["positions"])
                or any(
                    not 0 <= a < b <= len(view.text) or view.text[a:b] != word
                    for word, (a, b) in zip(data["words"], data["positions"], strict=True)
                )
                or any(a[1] > b[0] for a, b in pairwise(data["positions"]))
            ):
                raise DeclarationNotQualified("primary sentence differs from exact native text")
            ref = annotation_reference(pin, term["local_id"])
            data["reference"] = ref
            found.append(SimpleNamespace(**data))
            evidence.append(ref)
    found.sort(key=lambda s: s.positions[0][0])
    if len(found) != 3 or len({s.positions[0][0] for s in found}) != 3:
        raise DeclarationNotQualified("declaration requires three unique characterized sentences")
    return tuple(found), tuple(evidence)
