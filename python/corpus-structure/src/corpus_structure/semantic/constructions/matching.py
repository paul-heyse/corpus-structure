"""Named native matches, token alignment and unfiltered overlapping proposals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from spacy.attrs import IS_ALPHA, LOWER
from spacy.language import Language
from spacy.matcher import DependencyMatcher, Matcher, PhraseMatcher
from spacy.pipeline import SpanRuler
from spacy.tokens import Doc, Span

from .declarations import FAMILIES

RAW_GROUP = "tc_construction_raw"


@dataclass(frozen=True)
class Match:
    rule_id: str
    family: str
    mechanism: str
    bindings: tuple[tuple[str, tuple[int, ...]], ...]
    tokens: tuple[int, ...]
    alignments: tuple[int, ...] = ()
    anchors: tuple[tuple[str, int], ...] = ()


class PreparedConstructions:
    def __init__(self, vocab):
        if not {LOWER, IS_ALPHA} <= vocab.lex_attr_getters.keys():
            raise ValueError("construction patterns require language lexical attribute getters")
        self.vocab = vocab
        self.token = Matcher(vocab, validate=True)
        self.phrase = PhraseMatcher(vocab, attr="LOWER", validate=True)
        self.dependency = {}
        self.metadata: dict[int, tuple[str, tuple[str, ...], str]] = {}
        lexical = (
            ("negation", 4, [{"LOWER": {"IN": ["not", "never", "neither"]}}]),
            (
                "modality",
                4,
                [{"LOWER": {"IN": ["may", "might", "must", "can", "could", "should"]}}],
            ),
            (
                "quantification",
                4,
                [{"LOWER": {"IN": ["all", "every", "each", "some", "any", "no"]}}],
            ),
            ("condition_cue", 5, [{"LOWER": {"IN": ["if", "unless", "provided"]}}]),
            (
                "function_cue",
                7,
                [
                    {"LOWER": {"IN": ["define", "assume", "suppose", "let", "show", "prove"]}},
                    {"IS_ALPHA": True, "OP": "+"},
                ],
            ),
            ("question", 7, [{"TEXT": "?"}]),
            ("definition_approx", 7, [{"LOWER": {"FUZZY1": "defined"}}, {"LOWER": "as"}]),
        )
        for name, family, pattern in lexical:
            label = "tc." + name + ".v1"
            self.token.add(label, [pattern])
            self.metadata[vocab.strings[label]] = (
                FAMILIES[family],
                ("cue", "content"),
                "token:fuzzy1" if name == "definition_approx" else "token",
            )
        for name, family, phrases in (
            ("definition_cue", 7, ("is called", "is defined as", "we define")),
            ("exception_cue", 5, ("except for", "other than", "even if", "as long as")),
            ("temporal_cue", 5, ("after", "before", "until", "while")),
            ("causal_cue", 5, ("because", "because of", "therefore")),
            ("comparative_cue", 5, ("greater than", "less than", "as many as")),
        ):
            label = "tc." + name + ".v1"
            self.phrase.add(label, [Doc(vocab, words=list(map(str, p.split()))) for p in phrases])
            self.metadata[vocab.strings[label]] = (FAMILIES[family], ("cue",), "phrase")
        configurations = (
            ("active", 0, {"POS": "VERB"}, "subject", {"DEP": "nsubj"}),
            ("passive", 2, {"POS": {"IN": ["VERB", "AUX"]}}, "patient", {"DEP": "nsubjpass"}),
            ("copular", 0, {"POS": "AUX"}, "subject", {"DEP": "nsubj"}),
            ("complement", 1, {}, "complement", {"DEP": {"IN": ["ccomp", "xcomp"]}}),
            ("relative", 1, {}, "relative", {"DEP": "relcl"}),
            ("modification", 1, {}, "modifier", {"DEP": {"IN": ["amod", "acl", "appos"]}}),
            ("coordination", 3, {}, "conjunct", {"DEP": "conj"}),
            ("auxiliary", 2, {}, "auxiliary", {"DEP": {"IN": ["aux", "auxpass"]}}),
            ("negative_target", 4, {}, "cue", {"DEP": "neg"}),
            ("clause_relation", 5, {}, "clause", {"DEP": "advcl"}),
            (
                "reporting",
                6,
                {"LEMMA": {"IN": ["say", "report", "claim", "state", "write"]}},
                "content",
                {"DEP": "ccomp"},
            ),
        )
        for name, family, head, role, child in configurations:
            label = "tc.native." + name + ".v1"
            pattern = [
                {"RIGHT_ID": "governor", "RIGHT_ATTRS": head},
                {"LEFT_ID": "governor", "REL_OP": ">", "RIGHT_ID": role, "RIGHT_ATTRS": child},
            ]
            matcher = DependencyMatcher(vocab, validate=True)
            matcher.add(label, [pattern])
            requirements = {"DEP"}
            if "POS" in head or "POS" in child:
                requirements.add("POS")
            if "LEMMA" in head or "LEMMA" in child:
                requirements.add("LEMMA")
            self.dependency[vocab.strings[label]] = (matcher, requirements)
            self.metadata[vocab.strings[label]] = (
                FAMILIES[family],
                ("governor", role),
                "dependency",
            )
        self.collector = SpanRuler(
            Language(vocab=vocab),
            spans_key=RAW_GROUP,
            spans_filter=None,
            annotate_ents=False,
            overwrite=True,
            validate=True,
        )

    def match(self, doc: Doc) -> tuple[tuple[Match, ...], tuple[str, ...]]:
        if doc.vocab is not self.vocab:
            raise ValueError("construction matchers require their prepared vocabulary")
        matches, spans = [], []
        for label, start, end, alignment in cast(
            list[tuple[int, int, int, list[int]]], self.token(doc, with_alignments=True)
        ):
            family, names, mechanism = self.metadata[label]
            bindings = tuple(
                (
                    name,
                    tuple(
                        i for i, p in zip(range(start, end), alignment, strict=True) if p == index
                    ),
                )
                for index, name in enumerate(names)
                if index in alignment
            )
            matches.append(
                Match(
                    doc.vocab.strings[label],
                    family,
                    mechanism,
                    bindings,
                    tuple(range(start, end)),
                    tuple(alignment),
                )
            )
        for label, start, end in self.phrase(doc):
            family, _, mechanism = self.metadata[label]
            matches.append(
                Match(
                    doc.vocab.strings[label],
                    family,
                    mechanism,
                    (("cue", tuple(range(start, end))),),
                    tuple(range(start, end)),
                )
            )
        unavailable = []
        for rule, (matcher, requirements) in self.dependency.items():
            if all(
                doc.has_annotation(attribute, require_complete=True) for attribute in requirements
            ):
                for label, indices in matcher(doc):
                    family, names, mechanism = self.metadata[label]
                    # Subtree members remain discontinuous and native; do not use the
                    # enclosing left/right interval as the membership claim.
                    bindings = tuple(
                        (name, (i,) if index == 0 else tuple(t.i for t in doc[i].subtree))
                        for index, (name, i) in enumerate(zip(names, indices, strict=True))
                    )
                    matches.append(
                        Match(
                            doc.vocab.strings[label],
                            family,
                            mechanism,
                            bindings,
                            tuple(indices),
                            anchors=tuple(zip(names, indices, strict=True)),
                        )
                    )
            else:
                unavailable.append(
                    doc.vocab.strings[rule]
                    + " requires complete "
                    + ",".join(sorted(requirements))
                    + " columns"
                )
        for match in matches:
            for name, indices in match.bindings:
                if indices and tuple(sorted(indices)) == tuple(
                    range(min(indices), max(indices) + 1)
                ):
                    spans.append(
                        Span(doc, min(indices), max(indices) + 1, label=name, span_id=match.rule_id)
                    )
        self.collector.set_annotations(doc, spans)
        return tuple(matches), tuple(unavailable)


def retained_documents(layers, view, vocab):
    """Rebuild native working Docs without tokenization, inference or whitespace loss."""
    for pin, report in layers.items():
        payload = report.payload
        occurrences = {o["local_id"]: o for o in payload["occurrences"]}
        groups = {}
        for annotation in payload["annotations"]:
            native = annotation.get("native_token")
            if native is None or annotation.get("native_scheme") != "spacy-token-columns-1":
                continue
            extents = [e for o in annotation["occurrences"] for e in occurrences[o]["extents"]]
            if not extents or any(e["source_view_id"] != view.ref.id for e in extents):
                continue
            groups.setdefault(native["container"], []).append(
                (annotation, min(e["start"] for e in extents), max(e["end"] for e in extents))
            )
        for container, rows in groups.items():
            rows.sort(key=lambda row: row[0]["native_token"]["index"])
            if [r[0]["native_token"]["index"] for r in rows] != list(range(len(rows))):
                raise ValueError("retained native token indices are not a complete container")
            block = next(
                (
                    annotation
                    for annotation in payload["annotations"]
                    if annotation["local_id"] == container
                ),
                None,
            )
            if block is None or block["kind"] != "native.block":
                raise ValueError("retained native tokens lack their exact block container")
            bounds = [
                extent for oid in block["occurrences"] for extent in occurrences[oid]["extents"]
            ]
            if not bounds or any(
                extent["source_view_id"] != view.ref.id
                or extent["projection"] != view.ref.projection_digest
                for extent in bounds
            ):
                raise ValueError("retained native block differs from selected source")
            start, end = min(e["start"] for e in bounds), max(e["end"] for e in bounds)
            doc, doc_to_annotation = _working_document(view.text, start, end, rows, vocab)
            yield pin, container, doc, doc_to_annotation, start, end


def _working_document(text, start, end, rows, vocab):
    """One whitespace/head reconstruction owner for released and native projections."""
    words, spaces, owners, native_to_doc, doc_to_annotation = [], [], [], {}, {}
    cursor = start
    for annotation, a, b in rows:
        if a < cursor or text[a:b] != annotation["native_token"]["text"]:
            raise ValueError("retained native token differs from source")
        if a > cursor:
            gap = text[cursor:a]
            if not gap.isspace():
                raise ValueError("retained native columns leave non-whitespace source unexamined")
            if gap == " " and words:
                spaces[-1] = True
            else:
                words.append(gap)
                spaces.append(False)
                owners.append(None)
        native_to_doc[annotation["native_token"]["index"]] = len(words)
        doc_to_annotation[len(words)] = annotation
        words.append(text[a:b])
        spaces.append(False)
        owners.append(annotation)
        cursor = b
    if cursor < end:
        gap = text[cursor:end]
        if not gap.isspace():
            raise ValueError("retained native columns leave trailing source unexamined")
        if gap == " " and words:
            spaces[-1] = True
        else:
            words.append(gap)
            spaces.append(False)
            owners.append(None)
    columns = {
        column
        for column in ("lemma", "pos", "tag", "morphology", "dependency", "native_head")
        if all(column in r[0]["native_token"] for r in rows)
    }
    kwargs: dict[str, Any] = {}
    for column, attr in (
        ("lemma", "lemmas"),
        ("pos", "pos"),
        ("tag", "tags"),
        ("morphology", "morphs"),
    ):
        if column in columns:
            kwargs[attr] = [
                (
                    "|".join(a["native_token"][column])
                    if column == "morphology"
                    else a["native_token"][column]
                )
                if a
                else "SPACE"
                if column == "pos"
                else "_SP"
                if column == "tag"
                else " "
                if column == "lemma"
                else ""
                for a in owners
            ]
    if {"dependency", "native_head"} <= columns:
        kwargs["heads"] = [
            native_to_doc[a["native_token"]["native_head"]] if a else i
            for i, a in enumerate(owners)
        ]
        kwargs["deps"] = [a["native_token"]["dependency"] if a else "dep" for a in owners]
    if all("sent_start" in row[0]["native_token"] for row in rows):
        kwargs["sent_starts"] = [a["native_token"]["sent_start"] if a else None for a in owners]
    doc = Doc(vocab, words=words, spaces=spaces, **kwargs)
    if doc.text != text[start:end]:
        raise ValueError("retained native working Doc changed arbitrary whitespace")
    return doc, doc_to_annotation


def retained_native_vocab(source, native):
    """Seed source lexemes from retained primary values before enabling pattern getters."""
    import json

    from spacy.lang.en import English
    from spacy.vocab import Vocab

    body = json.loads(native.content)
    text = source.value["text"]
    vocab: Any = Vocab(lex_attr_getters={})
    seen = {}
    attributes = (
        ("LOWER", "lower"),
        ("IS_ALPHA", "is_alpha"),
        ("IS_SPACE", "is_space"),
        ("IS_PUNCT", "is_punct"),
        ("IS_QUOTE", "is_quote"),
        ("LIKE_NUM", "like_num"),
    )
    from ..sentence_products import source_annotation_member_values

    for token in source_annotation_member_values(body):
        if token["record_type"] != "token":
            continue
        spelling = text[token["start"] : token["end"]]
        values = {name: token[field] for name, field in attributes}
        if spelling in seen and seen[spelling] != values:
            raise ValueError("retained native lexeme attributes disagree for one original spelling")
        seen[spelling] = values
        vocab[spelling].set_attrs(**values)
    # Only new authored pattern words use language getters; every original source
    # token lexeme was already acquired above without running those getters.
    vocab.lex_attr_getters = cast(Any, English().vocab).lex_attr_getters
    return vocab


def retained_native_documents(source, native, vocab):
    """Materialize actual retained token columns; no tokenization or NLP call."""
    import json

    body = json.loads(native.content)
    text = source.value["text"]
    groups = {}
    from ..sentence_products import source_annotation_member_values

    for token in source_annotation_member_values(body):
        if token["record_type"] == "token":
            groups.setdefault(token["block_id"], []).append(token)
    for item in body["blocks"]:
        annotation = item["annotation"]
        block = dict(
            block_id=annotation["block_id"],
            start=annotation["block_start"],
            end=annotation["block_end"],
        )
        tokens = sorted(groups.get(block["block_id"], ()), key=lambda row: row["ordinal"])
        if not tokens:
            continue
        if [row["ordinal"] for row in tokens] != list(range(len(tokens))):
            raise ValueError("retained native token ordinals do not form their actual block")
        by_id = {row["local_id"]: row["ordinal"] for row in tokens}
        rows = []
        for token in tokens:
            columns = dict(
                index=token["ordinal"],
                text=text[token["start"] : token["end"]],
                **{
                    key: token[key]
                    for key in ("lemma", "pos", "tag", "morphology", "dependency", "sent_start")
                    if key in token
                },
            )
            if token.get("head_ref") is not None:
                if token["head_ref"] not in by_id:
                    raise ValueError("retained native dependency head leaves its original block")
                columns["native_head"] = by_id[token["head_ref"]]
            # This is an internal column view for the shared working-Doc owner,
            # never a fabricated released annotation or published member packet.
            evidence = dict(local_id=token["local_id"], native_token=columns)
            rows.append((evidence, token["start"], token["end"]))
        start, end = block["start"], block["end"]
        doc, annotations = _working_document(text, start, end, rows, vocab)
        yield block["block_id"], doc, annotations, start, end
