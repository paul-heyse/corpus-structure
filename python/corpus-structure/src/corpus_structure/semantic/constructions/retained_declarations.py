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
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.source_contexts import (
    ContextRefused,
    NativeSourceContext,
    NativeSpanEvidence,
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


def _emit_declaration_sentence(layer, view, sentence, *, source_key, premises):
    facts = _facts(sentence)
    root = identity("declaration-sentence", [source_key, sentence.positions])

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
    )
    layer.terms[key]["premises"] = [annotation]
    return dict(term_id=key, references=premises)


def _declared_sentences(source, native_products, canonical, hanlp, *, admitted, source_frame=None):
    """Index original canonical units and actual HanLP heads without re-recognition."""
    from ..data_operation_partitions import partition_header
    from ..data_product_reference import SemanticReference, read_semantic_reference
    from ..declared_record_sources import DeclaredNativeFrameSource
    from ..hanlp_products import canonical_hanlp_rows
    from ..sentence_partitions import COLLECTION, blocks_from_packets
    from ..source_contexts import PreparedNativeSources, source_slice

    selected = source.value
    body = json.loads(hanlp.content)
    if body["source"] != selected["source"] or tuple(body["selectors"]) != tuple(selected["selectors"]):
        raise DeclarationNotQualified(
            "declaration HanLP differs from exact original source and scope"
        )
    if read_semantic_reference(body["canonical_input"]) != SemanticReference.whole("canonical"):
        raise DeclarationNotQualified("declaration HanLP input has no canonical producing role")
    candidates = sorted(canonical_hanlp_rows(source, canonical), key=lambda item: item[0]["start"])
    addresses = {(sentence["block_id"], sentence["ordinal"]) for sentence, _ in candidates}
    if len({(row["start"], row["end"]) for row, _ in candidates}) != len(candidates):
        raise DeclarationNotQualified("declaration requires unique exact canonical sentences")
    packets = tuple(json.loads(packet) for packet in hanlp.partitions)
    if partition_header(packets) != body[COLLECTION]:
        raise DeclarationNotQualified(
            "declaration HanLP partitions differ from their exact commitment"
        )
    grouped = {}
    for block in blocks_from_packets(packets):
        for unit in block.rows:
            if unit["record_type"] not in {"token", "srl_group"}:
                continue
            key = block.key, unit["sentence_ordinal"]
            reference = SemanticReference.item(
                "canonical", COLLECTION, block.key, ("sentence", key[1])
            )
            if key not in addresses or read_semantic_reference(unit["sentence"]) != reference:
                raise DeclarationNotQualified(
                    "declaration HanLP sentence leaves its canonical input"
                )
            grouped.setdefault(key, []).append(unit)
    if not candidates:
        return
    if source_frame is None:
        if not native_products:
            raise DeclarationNotQualified(
                "declaration syntax requires an admitted original source frame"
            )
        source_frame = DeclaredNativeFrameSource(
            source.content.decode(), canonical_bytes(native_products[0].source.values()).decode()
        )
    if not isinstance(source_frame, DeclaredNativeFrameSource) or source_frame.value != selected:
        raise DeclarationNotQualified(
            "declaration frame differs from its exact selected original source"
        )
    frame = source_frame
    context = NativeSourceContext(
        frame,
        (),
        (source_slice(frame, 0, len(frame.text)),),
        "primary declaration roles",
        "primary-declaration-roles-1",
        "exact selected source",
        max_chars=max(1, len(frame.text)),
        max_pieces=max(1, len(frame.pieces)),
        max_sources=1,
        version=2,
        preparation=PreparedNativeSources((frame,), max_sources=1),
    )
    for number, (original, canonical_tokens) in enumerate(candidates):
        start, end = original["start"], original["end"]
        if not admitted(start, end):
            continue
        key = original["block_id"], original["ordinal"]
        selector = dict(projection=selected["source"]["projection"], start=start, end=end)
        try:
            units = grouped.get(key, ())
            tokens = sorted(
                (row for row in units if row["record_type"] == "token"),
                key=lambda row: row["ordinal"],
            )
            refs = [reference for reference, _ in canonical_tokens]
            _require(tokens and [row["ordinal"] for row in tokens] == list(range(len(tokens))))
            _require([row["token"] for row in tokens] == refs)
            positions = original["token_extents"]
            _require(start <= positions[0][0] < positions[-1][1] <= end)

            def native_reference(row, *, key=key):
                return SemanticReference.item(
                    "hanlp", COLLECTION, key[0], (key[1], row["record_type"], row["ordinal"])
                )

            for family in (
                "hanlp.tokens",
                "hanlp.lemma",
                "hanlp.pos",
                "hanlp.dependency",
                "hanlp.srl",
            ):
                coverage = [row for row in body["coverage"] if row["family"] == family]
                _require(
                    coverage
                    and any(
                        row["availability"] == "available"
                        and row["outcome"] in {"complete", "empty", "partial"}
                        and any(
                            value["projection"] == selector["projection"]
                            and value.get("start", 0) <= start
                            and value.get("end", len(frame.text)) >= end
                            for value in row.get("examined", ())
                        )
                        for row in coverage
                    )
                )
                _require(
                    not any(
                        value["projection"] == selector["projection"]
                        and value.get("start", 0) < end
                        and value.get("end", len(frame.text)) > start
                        for row in coverage
                        for value in row.get("unexamined", ())
                    )
                )
            _require(
                all(
                    all(
                        field in row
                        for field in ("lemma", "pos", "dependency_head", "dependency_label")
                    )
                    for row in tokens
                )
            )
            heads, relations, children = _dependency_graph(
                [[row["dependency_head"], row["dependency_label"]] for row in tokens], len(tokens)
            )
            locations = {}

            def located(
                a, b, *, tokens=tokens, number=number, positions=positions, locations=locations
            ):
                _require(0 <= a < b <= len(tokens))
                key = f"s{number}/span/{a}-{b}"
                left, right = positions[a][0], positions[b - 1][1]
                pieces = tuple(
                    context.map_span(
                        left, right, literal=frame.text[left:right], allow_multiple=True
                    )
                )
                native_pieces = tuple(
                    piece for piece in pieces if isinstance(piece, NativeSpanEvidence)
                )
                if not native_pieces or len(native_pieces) != len(pieces):
                    raise DeclarationNotQualified(
                        "declaration role lacks original native correspondence"
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

            groups, keys, evidence = {}, {}, []
            for group in (row for row in units if row["record_type"] == "srl_group"):
                args, predicate = [], None
                for role in group["roles"]:
                    left, right = role["start"], role["end"]
                    _require(
                        0 <= left < right <= len(tokens) and role["tokens"] == refs[left:right]
                    )
                    location = located(left, right)
                    if role["label"] == "PRED":
                        _require(predicate is None and right == left + 1)
                        predicate = left
                    else:
                        args.append(_Argument(role["label"], location))
                if predicate is None:
                    raise DeclarationNotQualified("declaration native SRL has no unique predicate")
                groups.setdefault(predicate, []).append(_SRL(tuple(args)))
                reference = native_reference(group)
                keys[predicate] = identity("hanlp-frame", reference.values())
                evidence.append(reference)
            frames = {}
            for predicate, srl in groups.items():
                head = heads[predicate] if relations[predicate] == "cop" else predicate
                if head is None:
                    raise DeclarationNotQualified(
                        "declaration copular predicate has no syntactic head"
                    )
                frames[predicate] = _Frame(
                    head,
                    located(predicate, predicate + 1),
                    "copular"
                    if relations[predicate] == "cop"
                    else "passive"
                    if any(relations[index] == "aux:pass" for index in children[predicate])
                    else "active",
                    tuple(srl),
                )
            evidence.extend(native_reference(token) for token in tokens)
            sentence = _Sentence(
                context,
                number,
                tuple(frame.text[a:b] for a, b in positions),
                tuple(row["lemma"].casefold() for row in tokens),
                tuple(row["pos"] for row in tokens),
                heads,
                relations,
                children,
                positions,
                frames,
                locations,
                keys,
                tuple(evidence),
            )
        except (DeclarationNotQualified, ValueError, KeyError, IndexError) as error:
            yield selector, None, str(error)
        else:
            yield selector, sentence, None


def populate_declaration_products(
    layer,
    view,
    source,
    native,
    canonical,
    hanlp,
    *,
    annotation_products=None,
    source_frame=None,
    check_active=lambda: None,
    admitted=lambda start, end: True,
):
    """Publish shared declaration syntax from independently acquired native products."""
    from ..sentence_products import retained_source_annotation_products

    if DECLARATION_FAMILY not in layer.families:
        layer.families = (*layer.families, DECLARATION_FAMILY)
        layer.operation["produced_families"].append(DECLARATION_FAMILY)
    if canonical is None or hanlp is None or (source_frame is None and native is None):
        for selector in source.value["selectors"]:
            layer.record(
                DECLARATION_FAMILY,
                selector,
                "unknown",
                "declaration syntax requires an admitted source frame and exact canonical and HanLP products",
            )
        return []
    products = (
        tuple(annotation_products)
        if annotation_products is not None
        else retained_source_annotation_products(source, native)
        if native is not None
        else ()
    )
    premise_sets = []
    try:
        produced = False
        for selector, sentence, reason in _declared_sentences(
            source, products, canonical, hanlp, admitted=admitted, source_frame=source_frame
        ):
            check_active()
            produced = True
            if sentence is None:
                layer.record(
                    DECLARATION_FAMILY, selector, "unknown", "declaration syntax: " + str(reason)
                )
                continue
            layer.record(DECLARATION_FAMILY, selector, "complete")
            premise_sets.append(
                _emit_declaration_sentence(
                    layer,
                    view,
                    sentence,
                    source_key=view.key,
                    premises=[ref.values() for ref in sentence.evidence],
                )
            )
        if not produced:
            outcome = (
                "empty" if json.loads(canonical.content)["outcome"] == "complete" else "unknown"
            )
            for selector in source.value["selectors"]:
                layer.record(
                    DECLARATION_FAMILY,
                    selector,
                    outcome,
                    None
                    if outcome == "empty"
                    else "canonical declaration population is incomplete",
                )
    except (DeclarationNotQualified, ValueError, KeyError, IndexError) as error:
        for selector in source.value["selectors"]:
            layer.record(
                DECLARATION_FAMILY, selector, "unknown", "declaration syntax: " + str(error)
            )

    return premise_sets


def declaration_sentences_products(products, source, passage):
    """Read positioned declaration facts with their exact admitted native premises."""
    from types import SimpleNamespace

    from ..data_product_reference import (
        DataProductReference,
        member_reference,
        read_semantic_reference,
    )

    selected = source.value
    if (
        not 0 <= passage.start < passage.end <= len(selected["text"])
        or selected["text"][passage.start : passage.end] != passage.text
    ):
        raise DeclarationNotQualified("declaration passage differs from exact original source")
    found, evidence = [], []

    def read(term, terms) -> Any:
        children = term.get("children", ())
        if not children:
            return json.loads(term["value"])
        if all(row["role"] == "item" for row in children):
            return tuple(
                read(terms[row["target"]], terms)
                for row in sorted(children, key=lambda row: row["order"])
            )
        return {row["role"]: read(terms[row["target"]], terms) for row in children}

    for product in products:
        body = json.loads(product.content)
        if body["source"] != selected["source"] or tuple(body["selectors"]) != tuple(selected["selectors"]):
            raise DeclarationNotQualified(
                "declaration product differs from exact original source and analyzed scope"
            )
        facts = product.inventory()
        terms = {row["local_id"]: row for row in facts["terms"]}
        occurrences = {row["local_id"]: row for row in facts["occurrences"]}

        support = {row["term_id"]: row["references"] for row in body["term_support"]}
        if len(support) != len(body["term_support"]):
            raise DeclarationNotQualified("declaration repeats native term support")

        for term in terms.values():
            if (
                term.get("vocabulary") != PRIMARY_RULE_VOCABULARY
                or term["value"] != "declaration_sentence"
            ):
                continue
            extents = [
                extent for key in term["occurrences"] for extent in occurrences[key]["extents"]
            ]
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
                    extent.get("synthetic")
                    or extent["projection"] != selected["source"]["projection"]
                    or extent["text"] != selected["text"][extent["start"] : extent["end"]]
                    for extent in extents
                )
            ):
                raise DeclarationNotQualified("declaration passage cuts primary sentence")
            coverage = [row for row in body["coverage"] if row["family"] == DECLARATION_FAMILY]
            if not any(
                row["availability"] == "available"
                and any(
                    selector["projection"] == selected["source"]["projection"]
                    and selector.get("start", 0) <= extents[0]["start"]
                    and selector.get("end", len(selected["text"])) >= extents[-1]["end"]
                    for selector in row.get("examined", ())
                )
                for row in coverage
            ) or any(
                selector["projection"] == selected["source"]["projection"]
                and selector.get("start", 0) < extents[-1]["end"]
                and selector.get("end", len(selected["text"])) > extents[0]["start"]
                for row in coverage
                for selector in row.get("unexamined", ())
            ):
                raise DeclarationNotQualified("declaration primary coverage is incomplete")
            premises = support.get(term["local_id"], ())
            if not premises or not all(
                ref.variant == "partition-item" and ref.role == "hanlp" and ref.collection == "rows"
                for ref in map(read_semantic_reference, premises)
            ):
                raise DeclarationNotQualified("declaration native term support is unavailable")
            data = read(term, terms)
            if (
                not isinstance(data, dict)
                or len(data["words"]) != len(data["positions"])
                or any(
                    not 0 <= a < b <= len(selected["text"]) or selected["text"][a:b] != word
                    for word, (a, b) in zip(data["words"], data["positions"], strict=True)
                )
                or any(left[1] > right[0] for left, right in pairwise(data["positions"]))
            ):
                raise DeclarationNotQualified(
                    "primary declaration sentence differs from exact native text"
                )
            reference = member_reference(
                DataProductReference(product.semantic_id), term["local_id"]
            )
            found.append(SimpleNamespace(**data, reference=reference))
            evidence.append(reference)
    found.sort(key=lambda value: value.positions[0][0])
    if len(found) != 3 or len({value.positions[0][0] for value in found}) != 3:
        raise DeclarationNotQualified("declaration requires three unique characterized sentences")
    return tuple(found), tuple(evidence)
