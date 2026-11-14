"""Released mathematical source cues over exact retained token/sentence columns.

This owner recognizes language and source markers. Symbol binding and the extent
of a mathematical statement remain downstream domain operations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from spacy.matcher import Matcher, PhraseMatcher
from spacy.tokens import Doc, Token

from corpus_structure.semantic.data_product_reference import member_reference

from .matching import retained_documents
from .nodes import identity

FAMILY = "construction.math_scope"
VOCABULARY = "math-source-scope-1"


class Binders(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    sentence_initial: tuple[str, ...] = Field(min_length=1)
    clause: tuple[str, ...] = ()
    reopen: tuple[str, ...] = ()
    section_wide: tuple[str, ...] = ()


class NativeDomainRule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    rule_id: str
    pattern: str
    statement_kind: str
    scope_role: Literal["statement", "proof", "solution", "exercise"]


def policy_identity(binders: Binders | None, rules: tuple[NativeDomainRule, ...]) -> str:
    return identity(
        "math-source-policy",
        [
            None if binders is None else binders.model_dump(mode="json"),
            [rule.model_dump(mode="json") for rule in rules],
        ],
    )


class PreparedScopeCues:
    """Native matcher preparation over released language declarations."""

    def __init__(self, vocab, binders):
        if not Token.has_extension("primary_math_atom"):
            Token.set_extension("primary_math_atom", default=False)
        matcher, phrases = (
            Matcher(vocab, validate=True),
            PhraseMatcher(vocab, attr="LOWER", validate=True),
        )
        if binders is not None:
            initial = [value.lower() for value in binders.sentence_initial]
            matcher.add("initial", [[{"IS_SENT_START": True, "LOWER": {"IN": initial}}]])
            if binders.clause:
                matcher.add(
                    "clause",
                    [
                        [
                            {"LOWER": {"IN": [value.lower() for value in binders.clause]}},
                            {"_": {"primary_math_atom": True}},
                        ]
                    ],
                )
            if binders.reopen:
                matcher.add(
                    "reopen",
                    [
                        [
                            {"IS_SENT_START": True, "LOWER": {"IN": initial}},
                            {"OP": "{0,3}"},
                            {"LOWER": {"IN": [value.lower() for value in binders.reopen]}},
                        ]
                    ],
                )
            if binders.section_wide:
                # Pack phrases are declarations, not source text. Their token words are
                # explicit whitespace-separated lexical entries; source is never split.
                phrases.add(
                    "section_wide",
                    [Doc(vocab, words=value.split()) for value in binders.section_wide],
                )
        self.matcher, self.phrases = matcher, phrases
        self.vocab = vocab

    def match(self, doc):
        return tuple(
            [(self.vocab.strings[label], a, b) for label, a, b in self.matcher(doc)]
            + [("section_wide", a, b) for _, a, b in self.phrases(doc)]
        )


def populate_math_scope(
    layer,
    view,
    dependencies,
    vocab,
    *,
    binders,
    rules=(),
    check_active=lambda: None,
    admitted=lambda a, b: True,
):
    """Project the sealed layer representation into the shared native cue kernel."""
    blocks = []
    fields = []
    for pin, container, doc, columns, offset, end in retained_documents(dependencies, view, vocab):
        body = dependencies[pin].payload
        occurrences = {row["local_id"]: row for row in body["occurrences"]}
        sentences = {}
        for row in body["annotations"]:
            parts = [e for oid in row["occurrences"] for e in occurrences[oid]["extents"]]
            if parts:
                sentences[row["local_id"]] = (
                    min(e["start"] for e in parts),
                    max(e["end"] for e in parts),
                )
        blocks.append((pin, container, doc, columns, offset, end, sentences))
    for pin, report in dependencies.items():
        body = report.payload
        occurrences = {row["local_id"]: row for row in body["occurrences"]}
        for row in body["annotations"]:
            inp = row.get("formal_input")
            if inp is not None:
                extents = occurrences[inp["parent_occurrence"]]["extents"]
                if all(e["source_view_id"] == view.ref.id for e in extents):
                    fields.append((pin, row["local_id"], inp, extents))
    _populate_math_scope(
        layer,
        view,
        blocks,
        vocab,
        source_key=view.ref.id,
        projection=view.ref.projection_digest,
        formal_fields=fields,
        binders=binders,
        rules=rules,
        check_active=check_active,
        admitted=admitted,
    )


def populate_math_scope_products(
    layer,
    view,
    source,
    native,
    formal,
    vocab,
    *,
    binders,
    rules=(),
    check_active=lambda: None,
    admitted=lambda a, b: True,
):
    """Consume authentic native blocks/formal fields without a Reader or view surrogate."""
    import json

    from corpus_structure.semantic.data_product_reference import DataProductReference
    from corpus_structure.semantic.sentence_products import source_annotation_member_values

    from .matching import retained_native_documents

    blocks, fields = [], []
    if native is not None:
        pin = DataProductReference(native.semantic_id)
        rows = source_annotation_member_values(json.loads(native.content))
        tokens = {
            (row["block_id"], row["ordinal"]): row for row in rows if row["record_type"] == "token"
        }
        sentences = {
            row["local_id"]: (row["start"], row["end"])
            for row in rows
            if row["record_type"] == "sentence"
        }
        for block, doc, annotations, start, end in retained_native_documents(source, native, vocab):
            columns = {}
            for index, annotation in annotations.items():
                token = tokens[block, annotation["native_token"]["index"]]
                columns[index] = dict(
                    local_id=token["local_id"],
                    native_token={
                        "source_role": token["role"],
                        **({"sentence": token["sentence_ref"]} if "sentence_ref" in token else {}),
                    },
                )
            blocks.append((pin, block, doc, columns, start, end, sentences))
    for product in formal:
        value = json.loads(product.content)
        occurrences = {
            packet["member_id"]: packet["body"]
            for packet in value["members"]
            if packet["body"]["record_type"] == "occurrence"
        }
        for packet in value["members"]:
            inp = packet["body"].get("formal_input")
            if inp is not None:
                fields.append(
                    (
                        DataProductReference(product.semantic_id),
                        packet["member_id"],
                        inp,
                        occurrences[inp["parent_occurrence"]]["extents"],
                    )
                )
    _populate_math_scope(
        layer,
        view,
        blocks,
        vocab,
        source_key=view.key,
        projection=view.projection,
        formal_fields=fields,
        binders=binders,
        rules=rules,
        check_active=check_active,
        admitted=admitted,
    )


def _populate_math_scope(
    layer,
    view,
    blocks,
    vocab,
    *,
    source_key,
    projection,
    formal_fields,
    binders,
    rules,
    check_active,
    admitted,
):
    policy = policy_identity(binders, rules)
    if len({rule.rule_id for rule in rules}) != len(rules):
        raise ValueError("math source rule identities must be unique")
    prepared = None

    def emit(kind, start, end, *, label=None, premises=(), external=(), identity_hint=None):
        oid = layer.occurrence(view, start, end)
        key = identity(
            "math-source-cue",
            [
                source_key,
                policy,
                kind,
                start,
                end,
                label,
                list(premises),
                list(external),
                identity_hint,
            ],
        )
        selector = dict(projection=projection, start=start, end=end)
        row = dict(
            local_id=key,
            kind="math." + kind,
            family=FAMILY,
            vocabulary=VOCABULARY,
            status="interpreted",
            rule_id=policy,
            occurrences=[oid],
            premises=list(premises),
            external_premises=list(external),
            context=dict(focal=[selector], examined=[selector], gaps=[]),
        )
        if label is not None:
            row["native_label"] = label
        if kind in {"scope_sentence", "scope_atom"}:
            row["rule_id"] = identity("math-source-sentences", [])
        layer.annotations[key] = row
        return key

    def member(owner, target, role):
        key = identity("math-source-member", [owner, target, role])
        layer.memberships[key] = dict(
            local_id=key,
            group=owner,
            member=target,
            role=role,
            order=0,
            structural=False,
            scope=owner,
            family=FAMILY,
            occurrences=layer.annotations[target]["occurrences"],
            premises=[owner, target],
        )

    examined = []
    for pin, container, native_doc, columns, offset, end, sentence_extents in blocks:
        check_active()
        if not admitted(offset, end):
            continue
        if any("sentence" not in row["native_token"] for row in columns.values()):
            layer.record(
                FAMILY,
                dict(projection=projection, start=offset, end=end),
                "unknown",
                "retained native sentence columns unavailable",
            )
            continue
        starts, previous = [], None
        for index, _token in enumerate(native_doc):
            row = columns.get(index)
            sentence = row["native_token"]["sentence"] if row else previous
            starts.append(index == 0 or (row is not None and sentence != previous))
            if row:
                previous = sentence
        doc = Doc(
            vocab,
            words=[token.text for token in native_doc],
            spaces=[bool(token.whitespace_) for token in native_doc],
            sent_starts=starts,
        )
        if doc.text != view.text[offset:end]:
            raise ValueError("math cue working Doc changed retained native text")
        for index, row in columns.items():
            doc[index]._.primary_math_atom = row["native_token"].get("source_role") == "math"
        sentences = {}
        atoms = {}
        if any(a < end and offset < b for a, b in examined):
            layer.record(
                FAMILY,
                dict(projection=projection, start=offset, end=end),
                "unknown",
                "competing retained native token/sentence contexts",
            )
        for sent in doc.sents:
            native_sentences = {
                columns[token.i]["native_token"]["sentence"] for token in sent if token.i in columns
            }
            if not native_sentences:
                continue
            if len(native_sentences) != 1:
                raise ValueError("math cue Doc crosses retained native sentence identities")
            native_sentence = next(iter(native_sentences))
            a, b = sentence_extents[native_sentence]
            external = [
                member_reference(pin, columns[token.i]["local_id"]).values()
                for token in sent
                if token.i in columns
            ]
            sentence = emit(
                "scope_sentence",
                a,
                b,
                label=container,
                external=[member_reference(pin, native_sentence).values(), *external],
            )
            sentences[sent.start] = sentence
            for token in sent:
                if token._.primary_math_atom:
                    atom = emit(
                        "scope_atom",
                        offset + token.idx,
                        offset + token.idx + len(token),
                        external=[member_reference(pin, columns[token.i]["local_id"]).values()],
                    )
                    atoms[token.i] = atom
                    member(sentence, atom, "math_atom")
        if prepared is None:
            prepared = PreparedScopeCues(vocab, binders)
        matches = prepared.match(doc)
        for kind, a, b in matches:
            external = [
                member_reference(pin, columns[token.i]["local_id"]).values()
                for token in doc[a:b]
                if token.i in columns
            ]
            cue = emit(
                "scope_" + kind,
                offset + doc[a].idx,
                offset + doc[b - 1].idx + len(doc[b - 1]),
                premises=[sentences[doc[a].sent.start]],
                external=external,
            )
            sentence_node = sentences[doc[a].sent.start]
            layer.annotations[cue]["context"]["examined"] = layer.annotations[sentence_node][
                "context"
            ]["examined"]
            member(cue, sentence_node, "sentence")
            if kind == "clause":
                if b - 1 not in atoms:
                    raise ValueError("math clause cue lacks its exact retained native atom")
                member(cue, atoms[b - 1], "target")
        layer.record(FAMILY, dict(projection=projection, start=offset, end=end), "complete")
        examined.append((offset, end))
    patterns = [(rule, re.compile(rule.pattern)) for rule in rules]
    native = {item["self_ref"]: item for item in (*view.ancestors, *view.items)}
    seen = set()
    for piece in view.pieces:
        a, b = piece["start"], piece["end"]
        if piece["kind"] != "native_text" or not admitted(a, b):
            continue
        pointer = piece.get("item_ref")
        if pointer in seen:
            continue
        seen.add(pointer)
        literal = native.get(pointer, {}).get("text", "")
        field_premises = []
        opaque = literal != view.text[a:b]
        if patterns and opaque:
            for pin, key, inp, extents in formal_fields:
                if (
                    inp["representation"] == "recognized_latex"
                    and inp["text"] == literal
                    and extents
                    and all(
                        e["projection"] == projection and e["native_pointer"] == pointer
                        for e in extents
                    )
                    and min(e["start"] for e in extents) == a
                    and max(e["end"] for e in extents) == b
                ):
                    field_premises.append(member_reference(pin, key).values())
            if len(field_premises) != 1:
                layer.record(
                    FAMILY,
                    dict(
                        projection=projection,
                        native_pointer=pointer,
                        start=a,
                        end=b,
                    ),
                    "unknown",
                    "native domain field lacks one exact represented formal input",
                )
                continue
        emit("scope_policy", a, b, label=pointer)
        examination = emit("domain_examined", a, b, label=pointer, external=field_premises)
        layer.annotations[examination]["rule_id"] = policy_identity(None, rules)
        for rule, pattern in patterns:
            for match in pattern.finditer(literal):
                marker = emit(
                    "domain_marker",
                    a if opaque else a + match.start(),
                    b if opaque else a + match.end(),
                    label=pointer,
                    external=field_premises,
                    identity_hint=[rule.model_dump(mode="json"), match.start(), match.end()],
                )
                layer.annotations[marker]["rule_id"] = policy_identity(None, rules)
                layer.annotations[marker]["context"]["examined"] = [
                    dict(projection=projection, start=a, end=b)
                ]
                for role, value in (
                    ("rule_id", rule.rule_id),
                    ("pattern", rule.pattern),
                    ("statement_kind", rule.statement_kind),
                    ("scope_role", rule.scope_role),
                    ("coordinate_space", "recognized_latex" if opaque else "native_projection"),
                    ("input_start", str(match.start())),
                    ("input_end", str(match.end())),
                ):
                    key = identity("math-source-rule-field", [marker, role, value])
                    layer.terms[key] = dict(
                        local_id=key,
                        kind="unknown",
                        family=FAMILY,
                        vocabulary=VOCABULARY,
                        value=value,
                        status="interpreted",
                        occurrences=layer.annotations[marker]["occurrences"],
                        premises=[marker],
                    )
                    membership = identity("math-source-rule-member", [marker, key, role])
                    layer.memberships[membership] = dict(
                        local_id=membership,
                        group=marker,
                        member=key,
                        role=role,
                        order=0,
                        structural=False,
                        scope=marker,
                        family=FAMILY,
                        occurrences=layer.annotations[marker]["occurrences"],
                        premises=[marker],
                    )
        if not any(start <= a and b <= end for start, end in examined):
            layer.record(
                FAMILY,
                dict(projection=projection, native_pointer=pointer, start=a, end=b),
                "unknown",
                "retained native sentence/token context unavailable",
            )


@dataclass(frozen=True, slots=True)
class MathScopeReadings:
    sentences: tuple[tuple[int, int], ...]
    cues: tuple[tuple[str, tuple[int, int], tuple[int, int] | None], ...]
    markers: tuple[tuple[int, str, NativeDomainRule], ...]
    complete: bool

    def flags(self, position):
        sentence = next((span for span in self.sentences if span[0] <= position < span[1]), None)
        return frozenset(
            kind
            for kind, span, target in self.cues
            if span == sentence
            and (kind != "clause" or (target is not None and target[0] == position))
        )


def retained_math_scope(layers, view, *, binders, rules=()):
    """Read exact sealed layer facts without recognizing language downstream."""
    selected = []
    for pin, report in layers.items():
        if report.reference(pin.task_id) != pin:
            raise ValueError("math source projection requires exact primary layer pins")
        body = report.payload
        views = [
            row
            for row in body["source_scope"]["source_views"]
            if row["source_view_id"] == view.ref.id
        ]
        if not views:
            continue
        if (
            len(views) != 1
            or body["base_document"] != view.ref.native_product.values()
            or views[0]["projection_digest"] != view.ref.projection_digest
            or views[0]["recipe_digest"] != view.ref.recipe_digest
        ):
            raise ValueError("math source projection differs from selected source")
        if FAMILY in body["operation"]["produced_families"]:
            selected.append((pin, body))
    return _read_math_scope(
        selected,
        view.pieces,
        len(view.text),
        view.ref.projection_digest,
        lambda extent: extent["source_view_id"] == view.ref.id,
        binders=binders,
        rules=rules,
    )


def retained_math_scope_products(products, source, *, binders, rules=()):
    """Read governed construction inventories with their exact source and policy closure."""
    import json

    from corpus_structure.semantic.data_product_reference import DataProductReference

    selected = []
    names = {
        "occurrence": "occurrences",
        "annotation": "annotations",
        "term": "terms",
        "membership": "memberships",
    }
    value = source.value
    for product in products:
        body = json.loads(product.content)
        if body["source"] != value["source"] or body["selectors"] != value["selectors"]:
            raise ValueError("math source product differs from its exact original source/scope")
        inventory = {name: [] for name in names.values()}
        for packet in body["members"]:
            row = packet["body"]
            if row["record_type"] in names:
                inventory[names[row["record_type"]]].append(row)
        inventory["coverage"] = body["coverage"]
        if any(row["family"] == FAMILY for row in body["coverage"]):
            selected.append((DataProductReference(product.semantic_id), inventory))
    return _read_math_scope(
        selected,
        value["pieces"],
        len(value["text"]),
        value["source"]["projection"],
        lambda extent: extent["projection"] == value["source"]["projection"],
        binders=binders,
        rules=rules,
    )


def _read_math_scope(sources, pieces, text_length, projection, belongs, *, binders, rules):
    policy = policy_identity(binders, rules)
    sentences, cues, markers = [], [], []
    covered, policies, policy_origins = [], [], set()
    for pin, body in sources:
        annotations = {row["local_id"]: row for row in body["annotations"]}
        terms = {row["local_id"]: row for row in body["terms"]}
        occurrences = {row["local_id"]: row for row in body["occurrences"]}

        def extent(row, *, occurrences=occurrences):
            parts = [e for oid in row["occurrences"] for e in occurrences[oid]["extents"]]
            if not parts or any(not belongs(e) or e["projection"] != projection for e in parts):
                raise ValueError("math source fact has no exact literal support")
            return min(e["start"] for e in parts), max(e["end"] for e in parts)

        def selected_source(row, *, occurrences=occurrences):
            parts = [e for oid in row["occurrences"] for e in occurrences[oid]["extents"]]
            if parts and all(not belongs(e) for e in parts):
                return False
            # A selected fact must be wholly supported by this exact view and
            # projection. Equal projection digests never rebase sibling view IDs.
            if not parts or any(not belongs(e) or e["projection"] != projection for e in parts):
                raise ValueError("math source fact has no exact literal support")
            return True

        memberships = {}
        for row in body["memberships"]:
            memberships.setdefault(row["group"], {})[row["role"]] = row["member"]
        selected = [
            row
            for row in annotations.values()
            if row.get("family") == FAMILY
            and row.get("rule_id")
            in {policy, policy_identity(None, rules), identity("math-source-sentences", [])}
            and selected_source(row)
        ]
        if not selected:
            continue
        for row in selected:
            if (
                row["kind"] == ("math.domain_examined" if binders is None else "math.scope_policy")
                and row.get("rule_id") == policy
            ):
                policies.append(extent(row))
                policy_origins.add(pin)
            kind = row["kind"].removeprefix("math.scope_")
            if kind == "sentence":
                sentences.append(extent(row))
            elif kind in {"initial", "clause", "reopen", "section_wide"}:
                members = memberships.get(row["local_id"], {})
                sent = annotations[members["sentence"]]
                target = annotations[members["target"]] if "target" in members else None
                cues.append((kind, extent(sent), None if target is None else extent(target)))
            elif row["kind"] == "math.domain_marker":
                values = {
                    role: terms[key]["value"]
                    for role, key in memberships.get(row["local_id"], {}).items()
                }
                rule = NativeDomainRule(
                    **{
                        name: values[name]
                        for name in ("rule_id", "pattern", "statement_kind", "scope_role")
                    }
                )
                if rule not in rules:
                    raise ValueError("retained domain marker differs from frozen rule")
                markers.append((extent(row)[0], row["native_label"], rule))
        for coverage in body["coverage"]:
            if (
                coverage["family"] == FAMILY
                and coverage["availability"] == "available"
                and coverage["outcome"] in {"complete", "empty"}
                and not coverage.get("unexamined")
            ):
                covered.extend(
                    (s.get("start", 0), s.get("end", text_length))
                    for s in coverage["examined"]
                    if s["projection"] == projection
                )
    complete = all(
        any(a <= p["start"] and p["end"] <= b for a, b in covered)
        and any(a <= p["start"] and p["end"] <= b for a, b in policies)
        for p in pieces
        if p["kind"] == "native_text"
    )
    complete = complete and len(policy_origins) == 1
    unique = tuple(sorted(set(sentences)))
    if any(a < c < b or a < d < b for a, b in unique for c, d in unique if (a, b) != (c, d)):
        complete = False
    return MathScopeReadings(
        unique,
        tuple(dict.fromkeys(cues)),
        tuple(sorted(set(markers), key=lambda row: (row[0], row[1], row[2].rule_id))),
        complete,
    )
