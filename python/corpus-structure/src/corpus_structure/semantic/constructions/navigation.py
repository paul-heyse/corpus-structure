"""Primary source navigation declarations, named roles and literal source cues."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal

from corpus_structure.ingest.annotation_views import annotation_view
from corpus_structure.ingest.annotations import (
    AnnotationProduct,
    AnnotationProfile,
    AnnotationUnavailable,
)
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.annotation_rules import (
    AnnotationRule,
    PreparedAnnotationRules,
    RoleBinding,
)
from corpus_structure.semantic.structural_products import StructuralPassage

QUESTION = "source_witnessed_links"
VERSION = "1"
ORDERED_VERSION = "2"
ORDERED_LIMIT_REASON = (
    "Selected recaps lack a unique exact ordered declaration or equation occurrence."
)

# A recap names both the declared meaning and the literal occurrence used by
# the equation. A bare repeat of the same glyph is not a scope witness.
DECLARATION = re.compile(
    r"^Let (?P<symbol>[A-Za-z]) be (?P<description>a [^.\n]+)\. "
    r"A (?P<family>[^.\n]+?) with these parameters is said to be a (?P<name>[^.\n]+)\."
)
RECAP = re.compile(
    r"^We have seen above that it is possible to simulate a (?P<name>[^.\n]+) "
    r"(?P<symbol>[A-Za-z])\.[^.\n]*\bthe simulated values for (?P=symbol)"
    r" using the equation (?P<equation>[^.\n]+)\."
)
LET = re.compile(r"\bLet ([A-Za-z]) (?:be|denote|represent)\b")
SOURCE_SYMBOL_DECLARATION = re.compile(
    r"\b(?:where|let)\s+([A-Za-z][A-Za-z0-9_]*)\s+(?:denotes|is|be|represents)\s+([^.;\n]+)",
    re.IGNORECASE,
)
_ORDERED_DECLARATION_CUE = re.compile(
    r"\b(?:let|where|suppose|define)[ \t\r\n]+([a-z])[ \t\r\n]+"
    r"(?:be|denotes?|is|represents?)\b",
    re.IGNORECASE | re.ASCII,
)
_LINE_SPACING = str.maketrans("\n\t", "  ")


@dataclass(frozen=True, slots=True)
class RecappedDeclaration:
    declaration_pointer: str
    use_pointer: str
    symbol: str
    name: tuple[int, int]
    declaration: tuple[int, int]
    recap: tuple[int, int]
    equation: tuple[int, int]
    scope: str
    passage: str
    effective_version: str | None
    primary_node: Mapping[str, Any] | None = field(default=None, kw_only=True)
    declaration_node: Mapping[str, Any] | None = field(default=None, kw_only=True)


@dataclass(frozen=True, slots=True)
class OrderedRecappedDeclaration(RecappedDeclaration):
    """A recap and its exact source spans; name anchors follow projection order."""

    symbol_site: tuple[int, int]
    name_pieces: tuple[tuple[str, int, int], ...]


def ordered_witness_selection(query: StructuralPassage, passage: StructuralPassage):
    return tuple((p.passage_id, p.start, p.end, p.effective_version) for p in (query, passage))


def _children(node):
    return tuple(item.get("$ref") for item in node.get("children", ()))


def _parent(node):
    return (node.get("parent") or {}).get("$ref")


NAMED_QUESTION = "source_named_links"
NAMED_VERSION = "2"
NAMED_COVERAGE_VERSION = "3"
NAMED_PIECE_VERSION = "4"
NAMED_NATIVE_PIECES_INPUT = "execution/implementation/operations/named-link-native-pieces.json"
NAMED_ANNOTATION_VERSIONS = frozenset({NAMED_VERSION, NAMED_COVERAGE_VERSION, NAMED_PIECE_VERSION})
INHERITANCE_QUESTION = "source_scope_inheritance"


_NAME = r"[A-Za-z][A-Za-z0-9_ -]{0,79}?"
_NAMED_LINK = re.compile(
    r"^(?P<left>" + _NAME + r") (?P<cue>is hereafter called|is renamed to|specializes|supersedes)"
    r" (?P<right>" + _NAME + r")\.$"
)
_ACRONYM = re.compile(
    r"^(?P<left>[A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+){1,7}) (?P<cue>\()(?P<right>[A-Z]{2,8})\)\.$"
)
SECTION_CUE = re.compile(
    r"\b(?P<cue>[Ss]ee|[Aa]s defined in) (?P<mention>Section (?P<code>[0-9]+(?:\.[0-9]+)+))\b"
)
_EXTERNAL_CUE = re.compile(
    r"\b(?P<cue>[Ss]ee) "
    r"(?P<mention>ISO(?:/IEC)? [0-9]+(?::[0-9]{4})?|RFC [0-9]+"
    r"|[A-Z][A-Za-z]+ and [A-Z][A-Za-z]+\.[0-9]+)(?=[. ,;)]|$)"
)
_SECTION_HEADING = re.compile(r"^(?:Section )?(?P<code>[0-9]+(?:\.[0-9]+)+)(?:\s|$)")
_KINDS = {
    "is hereafter called": "alias",
    "is renamed to": "renames",
    "specializes": "specializes",
    "supersedes": "supersedes",
}


@dataclass(frozen=True, slots=True)
class NamedLink:
    pointer: str
    kind: str
    left: tuple[int, int]
    cue: tuple[int, int]
    target_pointer: str | None
    right: tuple[int, int] | None
    scope: str
    passage: str
    resolution: str | None = None
    designator: str | None = field(default=None, kw_only=True)


def named_source_links(text, pieces, items, passages):
    """Resolve exact naming grammar and same-selection structural citations."""
    for passage in passages or ():
        rows = [
            (p["item_ref"], p["start"], text[p["start"] : p["end"]])
            for p in pieces
            if p.get("kind") == "native_text"
            and p.get("source_field", "text") == "text"
            and "cell_index" not in p
            and passage.start <= p["start"] < p["end"] <= passage.end
            and items.get(p["item_ref"], {}).get("content_layer") == "body"
        ]
        for pointer, start, literal in rows:
            if items[pointer].get("label") not in {"text", "paragraph", "list_item"}:
                continue

            def extent(match, group, start=start):
                a, b = match.span(group)
                return start + a, start + b

            if match := _NAMED_LINK.fullmatch(literal):
                if match["left"].casefold() != match["right"].casefold():
                    yield NamedLink(
                        pointer,
                        _KINDS[match["cue"]],
                        extent(match, "left"),
                        extent(match, "cue"),
                        pointer,
                        extent(match, "right"),
                        passage.scope,
                        passage.passage_id,
                    )
            elif (match := _ACRONYM.fullmatch(literal)) and (
                "".join(word[0] for word in match["left"].split()) == match["right"]
            ):
                yield NamedLink(
                    pointer,
                    "alias",
                    extent(match, "left"),
                    extent(match, "cue"),
                    pointer,
                    extent(match, "right"),
                    passage.scope,
                    passage.passage_id,
                )
            for match in SECTION_CUE.finditer(literal):
                yield NamedLink(
                    pointer,
                    "section_citation" if match["cue"].lower() == "see" else "definition_reference",
                    extent(match, "mention"),
                    extent(match, "cue"),
                    None,
                    None,
                    passage.scope,
                    passage.passage_id,
                    "target_selection_required",
                    designator=match["code"],
                )
            for match in _EXTERNAL_CUE.finditer(literal):
                yield NamedLink(
                    pointer,
                    "external_citation",
                    extent(match, "mention"),
                    extent(match, "cue"),
                    None,
                    None,
                    passage.scope,
                    passage.passage_id,
                    "external_target_unavailable",
                )


@dataclass(frozen=True, slots=True, kw_only=True)
class NamedCueWitness:
    rule: str
    variant: str
    mechanism: str
    kind: str
    annotation: str
    block: str
    tokens: dict[str, int]
    subject: tuple[int, int]
    cue: tuple[int, int]
    argument: tuple[int, int] | None
    designator: str | None
    scope: str
    effective_version: str | None
    resolution: str
    primary_node: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class NamedLinkMatch(NamedLink):
    witness: NamedCueWitness
    definition_subject: tuple[tuple[int, int], str] | None = None

    def evidence(self) -> dict[str, Any]:
        return asdict(self.witness)


@dataclass(frozen=True, slots=True)
class NamedLinkInspection:
    matches: tuple[NamedLinkMatch, ...]
    inspected_count: int
    incomplete: bool
    inspected_pointers: tuple[str, ...] = ()

    def outcome(self) -> str:
        if not self.inspected_count:
            return "unsupported" if self.incomplete else "empty"
        if self.incomplete or any(m.resolution != "located" for m in self.matches):
            return "limited"
        return "succeeded" if self.matches else "empty"


def named_definition_subject(text, start, cue_start, *, version=NAMED_VERSION):
    """Return a source-named term or explicitly marked identifier before its cue."""
    recipe, _, _ = _named_recipe(version)
    patterns = [("term", recipe["definition_subject_pattern"])]
    if version in (NAMED_COVERAGE_VERSION, NAMED_PIECE_VERSION):
        patterns.insert(0, ("identifier", recipe["definition_identifier_pattern"]))
    for kind, pattern in patterns:
        match = re.search(pattern, text[start:cue_start])
        if match is not None:
            lo, hi = match.span(1 if match[1] is not None else 2)
            return (start + lo, start + hi), kind
    return None


def explicit_named_definition_extent(text, start, cue_start, *, version=NAMED_VERSION):
    found = named_definition_subject(text, start, cue_start, version=version)
    return found[0] if found is not None else None


@lru_cache(maxsize=8)
def _named_recipe(version=NAMED_VERSION, native_piece_policy: bytes | None = None):
    from spacy.lang.en import English

    recipe = json.loads(Path(__file__).with_name("navigation_rules.json").read_bytes())
    if recipe["version"] != NAMED_VERSION:
        raise ValueError("named link recipe differs from the released version")
    if version in (NAMED_COVERAGE_VERSION, NAMED_PIECE_VERSION):
        coverage = json.loads(Path(__file__).with_name("navigation_coverage.json").read_bytes())
        if coverage["version"] != NAMED_COVERAGE_VERSION:
            raise ValueError("named link coverage differs from the released version")
        recipe.update(coverage)
        if version == NAMED_PIECE_VERSION:
            if native_piece_policy is None:
                native_piece_policy = (
                    Path(__file__).with_name("navigation_native_pieces.json").read_bytes()
                )
            pieces = json.loads(native_piece_policy)
            if (
                not isinstance(pieces, dict)
                or set(pieces) != {"version", "joined_piece_kinds"}
                or pieces["version"] != NAMED_PIECE_VERSION
                or not isinstance(kinds := pieces["joined_piece_kinds"], list)
                or not kinds
                or any(kind not in ("section_citation", "definition_reference") for kind in kinds)
                or len(kinds) != len(set(kinds))
            ):
                raise ValueError("named link native-piece policy differs from the released version")
            recipe.update(pieces)
    elif version != NAMED_VERSION:
        raise ValueError("unknown named link recipe")
    variants = {}
    rules = []
    for rule in recipe["rules"]:
        key = (rule["rule"], rule["variant"])
        variants[key] = rule
        if rule["mechanism"] == "token":
            pattern = [node["attrs"] for node in rule["nodes"]]
            bindings = {"match": RoleBinding(node="match")}
        else:
            pattern = [
                dict(
                    RIGHT_ID=node["id"],
                    RIGHT_ATTRS=node["attrs"],
                    **({"LEFT_ID": node["parent"], "REL_OP": ">"} if "parent" in node else {}),
                )
                for node in rule["nodes"]
            ]
            bindings = {"cue": RoleBinding(node=rule["cue"][0])}
        rules.append(
            AnnotationRule(
                rule=key[0],
                variant=key[1],
                mechanism=rule["mechanism"],
                pattern=pattern,
                bindings=bindings,
            )
        )
    return recipe, variants, PreparedAnnotationRules(English().vocab, rules=tuple(rules))


_DOTTED_DESIGNATOR = re.compile(r"[ \t]+(?P<code>[0-9]+(?:\.[0-9]+)+)(?!\w|\.[0-9])")
_CITATION_SUFFIX = re.compile(
    r"[ \t]+(?P<mention>ISO(?:/IEC)? [0-9]+(?::[0-9]{4})?|RFC [0-9]+"
    r"|[A-Z][A-Za-z]+ and [A-Z][A-Za-z]+\.[0-9]+)(?=[. ,;)]|$)"
)
_INITIAL_WORD = re.compile(r"[A-Z][A-Za-z]*\Z")
_ACRONYM_WORD = re.compile(r"[A-Z]{2,8}\Z")


def _word_run(doc, start, step, sentence):
    indices = []
    while 0 <= start < len(doc) and len(indices) < 8:
        if doc[start].sent.start != sentence or not _INITIAL_WORD.fullmatch(doc[start].text):
            break
        indices.append(start)
        start += step
    return tuple(sorted(indices))


def _nominal_extent(text, tokens, index, recipe):
    row = tokens[index]
    indices = [index]
    for i, other in enumerate(tokens):
        if (
            i != index
            and other.head == index
            and other.sentence == row.sentence
            and other.dependency in recipe["nominal_dependencies"]
        ):
            indices.append(i)
    indices.sort()
    if len(indices) > recipe["nominal_max_tokens"] or indices != list(
        range(indices[0], indices[-1] + 1)
    ):
        return (row.start, row.end), False
    first, last = tokens[indices[0]], tokens[indices[-1]]
    # The retained tokenizer treats an initial such as "A." as one token.
    end = last.end - bool(re.fullmatch(r"[A-Z]\.", text[last.start : last.end]))
    return (first.start, end), True


def _named_roles(text, doc, tokens, piece, rule, nodes, recipe):
    cue_rows = [tokens[nodes[key]] for key in rule["cue"]]
    cue = (min(r.start for r in cue_rows), max(r.end for r in cue_rows))
    kind = rule["kind"]
    if kind in {"section_citation", "definition_reference"}:
        section = tokens[nodes["section"]]
        code = _DOTTED_DESIGNATOR.match(text[section.end : piece["end"]])
        if code:
            return (section.start, section.end + code.end()), cue, None, code["code"], True
    elif kind == "external_citation":
        citation = _CITATION_SUFFIX.match(text[cue[1] : piece["end"]])
        if citation:
            a, b = citation.span("mention")
            return (cue[1] + a, cue[1] + b), cue, None, None, True
    elif rule["variant"] == "parenthesized":
        name = doc[nodes["acronym"]].text
        left = _word_run(doc, nodes["open"] - 1, -1, doc[nodes["open"]].sent.start)
        if (
            len(left) >= 2
            and _ACRONYM_WORD.fullmatch(name)
            and "".join(doc[i].text[0] for i in left) == name
        ):
            abbreviation = tokens[nodes["acronym"]]
            return (
                (tokens[left[0]].start, tokens[left[-1]].end),
                cue,
                (abbreviation.start, abbreviation.end),
                None,
                True,
            )
    elif rule["variant"] == "apposition":
        sentence = doc[nodes["hereafter"]].sent.start
        left = _word_run(doc, nodes["comma"] - 1, -1, sentence)
        right = _word_run(doc, nodes["hereafter"] + 1, 1, sentence)
        if left and right:
            return (
                (tokens[left[0]].start, tokens[left[-1]].end),
                cue,
                (tokens[right[0]].start, tokens[right[-1]].end),
                None,
                True,
            )
    elif kind == "procedure_reference":
        artifact = tokens[nodes["argument"]]
        code = _DOTTED_DESIGNATOR.match(text[artifact.end : piece["end"]])
        if code:
            return (artifact.start, artifact.end + code.end()), cue, cue, code["code"], True
    else:
        left, left_complete = _nominal_extent(text, tokens, nodes[rule["subject"]], recipe)
        right, right_complete = _nominal_extent(text, tokens, nodes[rule["argument"]], recipe)
        if text[slice(*left)].casefold() != text[slice(*right)].casefold():
            return left, cue, right, None, left_complete and right_complete
    return None


def _native_text_piece_key(piece):
    """Match the exact projected identity, with default text field normalized."""
    if (
        piece.get("kind") == "native_text"
        and piece.get("source_field") in (None, "text")
        and piece.get("cell_index") is None
        and isinstance(piece.get("item_ref"), str)
        and type(piece.get("start")) is int
        and type(piece.get("end")) is int
        and 0 <= piece["start"] < piece["end"]
    ):
        return piece["item_ref"], piece["start"], piece["end"]
    return None


def _annotation_piece_owners(annotations):
    """Index exact retained pieces; multiple owners remain distinguishable."""
    owners = defaultdict(list)
    for annotation in annotations:
        for index, piece in enumerate(annotation.native_pieces):
            key = _native_text_piece_key(piece.to_wire())
            if (
                key is not None
                and annotation.block_start <= piece.start < piece.end <= annotation.block_end
            ):
                owners[key].append((annotation, index))
    return owners


def _piece_contains_token(piece, index, token):
    return (
        token.piece_indices == (index,)
        and piece["start"] <= token.start < token.end <= piece["end"]
    )


def _piece_contains_roles(piece, index, tokens, roles):
    for extent in roles:
        if extent is None:
            continue
        start, end = extent
        if not piece["start"] <= start < end <= piece["end"]:
            return False
        if any(
            not _piece_contains_token(piece, index, token)
            for token in tokens
            if token.start < end and start < token.end
        ):
            return False
    return True


def match_named_source_links(
    text,
    pieces,
    items,
    passages,
    annotations,
    *,
    annotation_errors=(),
    version=NAMED_VERSION,
    native_piece_policy: bytes | None = None,
) -> NamedLinkInspection:
    """Find typed link cues on restored annotations and keep their exact source roles."""
    if native_piece_policy is not None and version != NAMED_PIECE_VERSION:
        raise ValueError("native-piece policy requires the joined-piece recipe")
    recipe, variants, prepared = _named_recipe(version, native_piece_policy)
    piece_version = version == NAMED_PIECE_VERSION
    physical_pieces = [
        p
        for p in pieces
        if (
            _native_text_piece_key(p) is not None
            if piece_version
            else p["kind"] == "native_text"
            and p.get("source_field", "text") == "text"
            and "cell_index" not in p
        )
        and items.get(p["item_ref"], {}).get("content_layer") == "body"
        and items[p["item_ref"]].get("label") in {"text", "paragraph", "list_item"}
    ]
    products = tuple(product for product in annotations if isinstance(product, AnnotationProduct))
    by_block = {product.block_id: product for product in products}
    # Older releases keyed the projection and retained annotation on the same pointer.
    by_pointer = {piece["item_ref"]: piece for piece in physical_pieces}
    piece_counts = Counter(piece["item_ref"] for piece in physical_pieces) if piece_version else {}
    owners = _annotation_piece_owners(products) if piece_version else {}
    block_counts = Counter(product.block_id for product in products) if piece_version else {}
    matched_blocks = {}
    matches = []
    inspected = set()
    strict_coverage = version in (NAMED_COVERAGE_VERSION, NAMED_PIECE_VERSION)
    incomplete = bool(annotation_errors) and not strict_coverage
    for piece in physical_pieces if piece_version else by_pointer.values():
        pointer = piece["item_ref"]
        selected = [p for p in passages or () if p.start < piece["end"] and piece["start"] < p.end]
        if not selected:
            continue
        piece_index = None
        if piece_version:
            key = _native_text_piece_key(piece)
            candidates = owners.get(key, ()) if key is not None else ()
            if piece_counts[pointer] != 1 or len(candidates) != 1:
                incomplete = True
                continue
            ((annotation, piece_index),) = candidates
            if block_counts[annotation.block_id] != 1:
                incomplete = True
                continue
        else:
            annotation = by_block.get(pointer)
            if annotation is None:
                incomplete = True
                continue
        if strict_coverage:
            availability = {column.attribute: column.status for column in annotation.availability}
            if any(
                availability.get(column) not in {"complete", "not_applicable"}
                for column in recipe["required_columns"]
            ):
                incomplete = True
                continue
        if annotation.block_id not in matched_blocks:
            try:
                view = annotation_view(
                    annotation, text[annotation.block_start : annotation.block_end], prepared.vocab
                )
            except AnnotationUnavailable:
                if strict_coverage:
                    raise
                incomplete = True
                continue
            matched_blocks[annotation.block_id] = view, prepared.match(view)
        view, result = matched_blocks[annotation.block_id]
        incomplete |= any(status != "available" for _, _, status in result.availability)
        inspected.add(pointer)
        tokens = annotation.tokens
        for match in result.matches:
            rule = variants[match.rule, match.variant]
            if (
                piece_version
                and annotation.block_id != pointer
                and rule["kind"] not in recipe["joined_piece_kinds"]
            ):
                continue
            nodes = dict(zip((n["id"] for n in rule["nodes"]), match.nodes, strict=True))
            if piece_index is not None and not all(
                _piece_contains_token(piece, piece_index, tokens[index]) for index in nodes.values()
            ):
                continue
            sentences = {tokens[index].sentence for index in nodes.values()}
            if len(sentences) != 1:
                continue
            (sentence_index,) = sentences
            if sentence_index is None:
                continue
            found = _named_roles(text, view.doc, tokens, piece, rule, nodes, recipe)
            if found is None:
                continue
            left, cue, right, designator, complete = found
            if piece_index is not None and not _piece_contains_roles(
                piece, piece_index, tokens, (left, cue, right)
            ):
                continue
            sentence = annotation.sentences[sentence_index]
            prefix = text[sentence.start : cue[0]]
            quoted = prefix.count('"') % 2 == 1 or prefix.count("“") > prefix.count("”")
            cautious = bool(
                match.negation_extents
                or re.search(r"\b(?:do|does|did) not\s*$", prefix, re.I)
                or any(
                    token.head in nodes.values()
                    and (
                        (token.dependency == "mark" and token.lemma.lower() in {"if", "unless"})
                        or (
                            token.dependency == "aux"
                            and token.lemma.lower() in {"may", "might", "could", "would"}
                        )
                    )
                    for token in tokens
                )
            )
            kind = rule["kind"]
            if not complete or quoted or cautious:
                resolution = "insufficient_evidence"
            elif kind in {"section_citation", "definition_reference"}:
                resolution = "target_selection_required"
            elif kind == "external_citation":
                resolution = "external_target_unavailable"
            elif kind == "procedure_reference":
                resolution = "target_selection_required"
            else:
                resolution = "located"
            for passage in selected:
                lo, hi = max(passage.start, piece["start"]), min(passage.end, piece["end"])
                if not all(lo <= a < b <= hi for a, b in (left, cue)):
                    continue
                scoped_right = right if right is None or lo <= right[0] < right[1] <= hi else None
                state = resolution if scoped_right == right else "insufficient_evidence"
                definition_subject = None
                if (
                    piece_index is not None
                    and kind == "definition_reference"
                    and state == "target_selection_required"
                    and (
                        concept := named_definition_subject(
                            text, lo, cue[0], version=NAMED_COVERAGE_VERSION
                        )
                    )
                    is not None
                    and _piece_contains_roles(piece, piece_index, tokens, (concept[0],))
                ):
                    definition_subject = concept
                matches.append(
                    NamedLinkMatch(
                        pointer=pointer,
                        kind=kind,
                        left=left,
                        cue=cue,
                        target_pointer=pointer if state == "located" else None,
                        right=scoped_right,
                        scope=passage.scope,
                        passage=passage.passage_id,
                        resolution=state,
                        definition_subject=definition_subject,
                        witness=NamedCueWitness(
                            rule=match.rule,
                            variant=match.variant,
                            mechanism=match.mechanism,
                            kind=kind,
                            annotation="annotation:" + annotation.dependency_digest,
                            block=annotation.block_id,
                            tokens=nodes,
                            subject=left,
                            cue=cue,
                            argument=scoped_right,
                            designator=designator,
                            scope=passage.scope,
                            effective_version=passage.effective_version,
                            resolution=state,
                        ),
                    )
                )
    return NamedLinkInspection(tuple(matches), len(inspected), incomplete, tuple(sorted(inspected)))


FAMILY = "construction.navigation"
CODEC = "source-navigation-v1"
_ARTIFACT = re.compile(r"\b(Table|Figure|Theorem|Section)\s+([A-Z]?\d[\w./-]*)", re.IGNORECASE)
_ARTIFACT_PREFIX = re.compile(r"\b(?:in|see|from)\s+$", re.I)
_NOTE_ALL = re.compile(r"(?:This note applies to )?all rows[.!]?", re.I)
_NOTE_AXIS = re.compile(r"^(?:Only )?the (.+?) (row|column|band)\b", re.I)
_TABLE_SCHEMATIC = re.compile(
    r"\bdata shown in Table (\d+(?:\.\d+)+)\b.*?"
    r"\bgeneral data table will look as shown in Table (\d+(?:\.\d+)+)\b",
    re.I | re.S,
)
_TABLE_ROLES = (
    (re.compile(r"\brow sums by (\w+) and (\w+)", re.I), "row_sum"),
    (re.compile(r"\bcolumn sums by (\w+) and (\w+)", re.I), "column_sum"),
    (re.compile(r"\bsize of the data set will be denoted by (\w+)", re.I), "sample_count"),
    (re.compile(r"\bijth entry in the table will be denoted by (sij)\b", re.I), "observed_count"),
)


_ALIAS = re.compile(
    r'\s*\((?:alias:|also called|also known as)\s*"([^"\r\n]+)"\s*\)', re.I | re.ASCII
)
_ALIAS_ABSENCE = re.compile(r"\s*\((aliases:\s*none)\s*\)", re.I | re.ASCII)


def source_alias_fields(text: str, artifact_end: int, source_pointer: str) -> dict:
    """Read explicit alias declarations attached to this exact artifact citation."""
    spans = []
    cursor = artifact_end
    while (match := _ALIAS.match(text, cursor)) is not None and match.group(1).strip():
        start, end = match.span(1)
        spans.append(dict(source_pointer=source_pointer, start=start, end=end, text=match.group(1)))
        cursor = match.end()
    if spans:
        return dict(
            aliases=tuple(span["text"] for span in spans),
            alias_state="observed",
            alias_occurrences=tuple(spans),
        )
    if (absence := _ALIAS_ABSENCE.match(text, artifact_end)) is not None:
        start, end = absence.span(1)
        return dict(
            aliases=(),
            alias_state="known_empty",
            alias_occurrences=(),
            alias_absence=dict(
                source_pointer=source_pointer, start=start, end=end, text=absence.group(1)
            ),
        )
    return dict(aliases=(), alias_state="unknown", alias_occurrences=())


_ARTIFACT_LABEL = re.compile(
    r"\s*\((numbering namespace|revision):[ \t]*([A-Za-z0-9][A-Za-z0-9_.-]*)\)",
    re.ASCII,
)


def artifact_source_labels(text: str, artifact_end: int, pointer: str):
    """Only adjacent declarations supply numbering or revision evidence."""
    from corpus_structure.semantic.artifact_identity import ArtifactAliasSpan, ArtifactSourceLabel

    labels: dict[str, list[ArtifactAliasSpan]] = defaultdict(list)
    cursor = artifact_end
    while (match := _ARTIFACT_LABEL.match(text, cursor)) is not None:
        start, end = match.span(2)
        labels[match[1]].append(
            ArtifactAliasSpan(source_pointer=pointer, start=start, end=end, text=match[2])
        )
        cursor = match.end()
    return tuple(
        ArtifactSourceLabel(
            state="unknown" if not values else "observed" if len(values) == 1 else "unresolved",
            value=next(iter(values)) if len(values) == 1 else None,
            evidence=tuple(labels[kind]),
        )
        for kind in ("numbering namespace", "revision")
        for values in ({span.text for span in labels[kind]},)
    )


_REFERENCE_PREFIX = re.compile(r"[ \t]*(?:See|Consult)[ \t]+", re.I | re.ASCII)
_REFERENCE_TARGET = re.compile(
    r"[ \t]+\((?:hereafter|also published as|also cited as)[ \t]+(Table|Figure)[ \t]+"
    r"([A-Za-z]?[0-9]+(?:[.-][0-9]+)*[A-Za-z]?)[ \t]+in numbering namespace[ \t]+"
    r"([A-Za-z0-9][A-Za-z0-9_.-]*)\)(?=\.|$)",
    re.I | re.ASCII,
)


def explicit_artifact_reference(text: str, start: int, end: int, pointer: str, artifact):
    """Recover the exact NCE-06 mention role and an explicit scoped target cue."""
    from corpus_structure.semantic.artifact_identity import (
        ArtifactAliasSpan,
        ArtifactReferenceDesignator,
    )

    if artifact.occurrence_role != "reference" or not _REFERENCE_PREFIX.fullmatch(text, 0, start):
        return None
    target = _REFERENCE_TARGET.match(text, end)
    if target is None or target[1].lower() != artifact.artifact_kind:
        return None
    return ArtifactReferenceDesignator(
        target_code=target[2],
        target_numbering=target[3],
        cue=ArtifactAliasSpan(
            source_pointer=pointer, start=0, end=target.end(), text=text[: target.end()]
        ),
    )


_RELATION_LABEL = re.compile(r"[ \t]+\((?:numbering namespace|revision):[ \t]*[A-Za-z0-9_.-]+\)")
_WORK_CUE = re.compile(r"[ \t]+\(work:[ \t]*([A-Za-z0-9][A-Za-z0-9_.-]*)\)")
_ARTIFACT_RELATION = re.compile(
    r"[ \t]+\((cites|same lineage as|supersedes)[ \t]+(Table|Figure|Theorem|Section)[ \t]+"
    r"([A-Za-z]?[0-9]+(?:[.-][0-9]+)*[A-Za-z]?)[ \t]+in numbering namespace[ \t]+"
    r"([A-Za-z0-9][A-Za-z0-9_.-]*)(?:[ \t]+of work[ \t]+([A-Za-z0-9][A-Za-z0-9_.-]*))?"
    r"(?:[ \t]+revision[ \t]+([A-Za-z0-9][A-Za-z0-9_.-]*))?\)"
)
_RELATION_KINDS: dict[str, Literal["reference", "same_lineage", "supersedes"]] = {
    "cites": "reference",
    "same lineage as": "same_lineage",
    "supersedes": "supersedes",
}


def populate_navigation(
    layer, view, dependencies, *, check_active=lambda: None, admitted=lambda a, b: True
):
    """Characterize source navigation once; target selection remains a consumer operation."""
    from corpus_structure.methods.native_evidence_layers import retained_annotation_products
    from corpus_structure.semantic.characterization import annotation_reference

    from .nodes import identity

    items = {item["self_ref"]: item for item in (*view.ancestors, *view.items)}
    pieces = [
        p for p in view.pieces if p["kind"] == "native_text" and admitted(p["start"], p["end"])
    ]
    products = []
    tokens = {}
    incomplete = False
    for pin, report in dependencies.items():
        body = report.payload
        runs = [run for run in body.get("native_runs", ()) if run["provider"] == "spacy"]
        if not runs:
            continue
        if len(runs) != 1:
            raise ValueError("navigation requires one exact native spaCy run per layer")
        run = runs[0]
        profile = AnnotationProfile(
            SentenceConfig(
                spacy_version=run["runtime_version"],
                model=run["model"],
                model_version=run["model_version"],
                exclude=("ner",),
            )
        )
        products.extend(
            product
            for product in retained_annotation_products({pin: report}, view, profile)
            if admitted(product.block_start, product.block_end)
        )
        for annotation in body["annotations"]:
            native = annotation.get("native_token")
            if native is not None and native["native_run"] == run["local_id"]:
                tokens.setdefault((native["container"], native["index"]), []).append(
                    annotation_reference(pin, annotation["local_id"]).values()
                )

    def emit(
        kind, pointer, roles, *, native_tokens=(), status="complete", source_labels=(), **values
    ):
        check_active()
        bound = []
        for role, spans in roles.items():
            spans = (
                (spans,)
                if isinstance(spans, tuple)
                and len(spans) == 2
                and all(type(v) is int for v in spans)
                else spans
            )
            occurrences = [layer.occurrence(view, a, b) for a, b in spans if a < b]
            if occurrences:
                bound.append(dict(role=role, occurrences=occurrences))
        labels = []
        for i, (label_kind, value, span) in enumerate(source_labels):
            oid = layer.occurrence(view, *span)
            bound.append(dict(role="source_label/" + str(i), occurrences=[oid]))
            labels.append(dict(kind=label_kind, value=value, occurrences=[oid]))
        navigation = dict(
            codec=CODEC,
            kind=kind,
            pointer=pointer,
            status=status,
            roles=bound,
            native_tokens=list(native_tokens),
            **values,
        )
        if labels:
            navigation["source_labels"] = labels
        key = identity("navigation", [view.ref.id, navigation])
        regions = [
            (product.block_start, product.block_end)
            for product in products
            if product.block_id == values.get("block")
        ]
        if not regions:
            regions = [(p["start"], p["end"]) for p in pieces if p["item_ref"] == pointer]
        if not regions:
            regions = [(a, b) for a, b, target in literal_regions if target == pointer]
        focal = [
            dict(projection=view.ref.projection_digest, start=e["start"], end=e["end"])
            for role in bound
            for oid in role["occurrences"]
            for e in layer.occurrences[oid]["extents"]
        ]
        layer.annotations[key] = dict(
            local_id=key,
            kind="construction.navigation",
            family=FAMILY,
            vocabulary=CODEC,
            status="interpreted" if status == "complete" else "unknown",
            navigation=navigation,
            occurrences=list(dict.fromkeys(oid for role in bound for oid in role["occurrences"])),
            context=dict(
                focal=focal,
                examined=[
                    dict(projection=view.ref.projection_digest, start=a, end=b)
                    for a, b in dict.fromkeys(regions)
                ],
                gaps=[],
            ),
            external_premises=[token["native_node"] for token in native_tokens],
        )
        return key

    physical = [
        p for p in pieces if p.get("source_field", "text") == "text" and p.get("cell_index") is None
    ]
    literal_regions = {(p["start"], p["end"], p["item_ref"]) for p in physical}
    by_pointer = {p["item_ref"]: p for p in physical}
    for pointer, item in items.items():
        if item.get("label") != "inline":
            continue
        children = [by_pointer.get(child) for child in _children(item)]
        if not children or any(child is None for child in children):
            continue
        children = [child for child in children if child is not None]
        if all(left["end"] == right["start"] for left, right in pairwise(children)):
            literal_regions.add((children[0]["start"], children[-1]["end"], pointer))
    for start, end, pointer in sorted(literal_regions):
        literal = view.text[start:end]
        binding = DECLARATION.match(literal.translate(_LINE_SPACING))
        if binding is not None and binding["description"].startswith(
            "a " + binding["family"] + " with parameters "
        ):
            emit(
                "declaration_template",
                pointer,
                {
                    name: (start + binding.start(name), start + binding.end(name))
                    for name in ("symbol", "description", "family", "name")
                },
            )
    for piece in physical:
        check_active()
        pointer, start, end = piece["item_ref"], piece["start"], piece["end"]
        literal = view.text[start:end]
        for match in SOURCE_SYMBOL_DECLARATION.finditer(literal):
            emit(
                "symbol_declaration",
                pointer,
                {
                    name: (start + match.start(group), start + match.end(group))
                    for name, group in (("match", 0), ("symbol", 1), ("description", 2))
                },
                introducer=match[0].split()[0].lower(),
            )
        for match in _ORDERED_DECLARATION_CUE.finditer(literal):
            emit(
                "declaration_cue",
                pointer,
                {
                    "symbol": (start + match.start(1), start + match.end(1)),
                    "cue": (start + match.start(), start + match.end()),
                },
                introducer=match[0].split()[0].lower(),
                variant="simple_let" if LET.match(literal, match.start()) else "ordered",
            )
        match = RECAP.match(literal.translate(_LINE_SPACING))
        if match is not None:
            emit(
                "recap",
                pointer,
                {
                    **{
                        name: (start + match.start(name), start + match.end(name))
                        for name in ("symbol", "name", "equation")
                    },
                    "cue": (start, start + match.end("symbol")),
                },
            )
        for match in _ARTIFACT.finditer(literal):
            code = match[2].removesuffix(".")
            artifact_end = match.start(2) + len(code)
            prefix = _ARTIFACT_PREFIX.search(literal[: match.start()])
            roles = {
                "subject": (start + match.start(), start + match.start(2) + len(code)),
                "designator": (start + match.start(2), start + match.start(2) + len(code)),
            }
            if prefix is not None:
                roles["cue"] = (
                    start + prefix.start(),
                    start + prefix.start() + len(prefix[0].rstrip()),
                )
            aliases = source_alias_fields(literal, artifact_end, pointer)
            for i, alias in enumerate(aliases.get("alias_occurrences", ())):
                roles["alias/" + str(i)] = (start + alias["start"], start + alias["end"])
            if aliases.get("alias_absence") is not None:
                absence = aliases["alias_absence"]
                roles["alias_absence"] = (start + absence["start"], start + absence["end"])
            if items.get(pointer, {}).get("label") == "caption":
                tail = literal[artifact_end:]
                title = tail.strip(" .:\n")
                if title:
                    title_start = artifact_end + len(tail) - len(tail.lstrip(" .:\n"))
                    roles["caption_title"] = (start + title_start, start + title_start + len(title))
            labels = []
            cursor = artifact_end
            while (label := _ARTIFACT_LABEL.match(literal, cursor)) is not None:
                labels.append(
                    (
                        "numbering_namespace" if label[1] == "numbering namespace" else "revision",
                        label[2],
                        (start + label.start(2), start + label.end(2)),
                    )
                )
                cursor = label.end()
            emit(
                "artifact_reference" if prefix is not None else "artifact_mention",
                pointer,
                roles,
                artifact_kind=match[1].lower(),
                designator=code,
                alias_state=aliases["alias_state"],
                source_labels=labels,
            )
            if (
                _REFERENCE_PREFIX.fullmatch(literal, 0, match.start())
                and (target := _REFERENCE_TARGET.match(literal, artifact_end)) is not None
                and target[1].lower() == match[1].lower()
            ):
                emit(
                    "artifact_explicit_reference",
                    pointer,
                    {
                        "subject": roles["subject"],
                        "cue": (start, start + target.end()),
                        "target_designator": (start + target.start(2), start + target.end(2)),
                        "target_numbering": (start + target.start(3), start + target.end(3)),
                    },
                    artifact_kind=target[1].lower(),
                    designator=target[2],
                    numbering_namespace=target[3],
                )
            cursor = artifact_end
            while (label := _RELATION_LABEL.match(literal, cursor)) is not None:
                cursor = label.end()
            if (marker := _WORK_CUE.match(literal, cursor)) is not None:
                cursor = marker.end()
                emit(
                    "artifact_work",
                    pointer,
                    {
                        "subject": roles["subject"],
                        "cue": (start + marker.start(), start + marker.end()),
                        "work": (start + marker.start(1), start + marker.end(1)),
                    },
                    work=marker[1],
                )
            while (relation := _ARTIFACT_RELATION.match(literal, cursor)) is not None:
                cursor = relation.end()
                operands = {
                    "subject": roles["subject"],
                    "cue": (start + relation.start(), start + relation.end()),
                    "target_designator": (start + relation.start(3), start + relation.end(3)),
                    "target_numbering": (start + relation.start(4), start + relation.end(4)),
                }
                for group, name in ((5, "target_work"), (6, "target_revision")):
                    if relation[group] is not None:
                        operands[name] = (
                            start + relation.start(group),
                            start + relation.end(group),
                        )
                emit(
                    "artifact_relation",
                    pointer,
                    operands,
                    relation_kind=_RELATION_KINDS[relation[1]],
                    artifact_kind=relation[2].lower(),
                    designator=relation[3],
                    numbering_namespace=relation[4],
                    **({"work": relation[5]} if relation[5] else {}),
                    **({"revision": relation[6]} if relation[6] else {}),
                )
        heading = (
            _SECTION_HEADING.match(literal)
            if items.get(pointer, {}).get("label") == "section_header"
            else None
        )
        if heading is not None:
            emit(
                "section_heading",
                pointer,
                {
                    "heading": (start, end),
                    "designator": (start + heading.start("code"), start + heading.end("code")),
                },
                designator=heading["code"],
            )
        stripped = literal.strip()
        offset = start + len(literal) - len(literal.lstrip())
        if _NOTE_ALL.fullmatch(stripped):
            emit("note_scope", pointer, {"cue": (offset, offset + len(stripped))}, axis="all")
        elif (match := _NOTE_AXIS.match(stripped)) is not None:
            emit(
                "note_scope",
                pointer,
                {
                    "cue": (offset, offset + match.end()),
                    "label": (offset + match.start(1), offset + match.end(1)),
                },
                axis=match[2].lower(),
                label=match[1].casefold(),
            )
        if (match := _TABLE_SCHEMATIC.search(literal)) is not None and match[1] != match[2]:
            emit(
                "table_schematic",
                pointer,
                {
                    "observed": (start + match.start(1), start + match.end(1)),
                    "schematic": (start + match.start(2), start + match.end(2)),
                    "cue": (start + match.start(), start + match.end()),
                },
            )
        for pattern, role in _TABLE_ROLES:
            if (match := pattern.search(literal)) is not None:
                emit(
                    "table_role",
                    pointer,
                    {
                        "cue": (start + match.start(), start + match.end()),
                        **{
                            "symbol/" + str(i): (start + match.start(i), start + match.end(i))
                            for i in range(1, len(match.groups()) + 1)
                        },
                    },
                    measure_role=role,
                )

    for piece in pieces:
        if piece.get("cell_index") is None:
            continue
        literal = view.text[piece["start"] : piece["end"]]
        geometry_role = {
            "frequency": "frequency",
            "relative frequency": "relative_frequency",
            "winning": "row_key",
            "outcome": "row_key",
        }.get(literal.strip().casefold())
        if geometry_role is not None:
            emit(
                "table_geometry",
                piece["item_ref"],
                {"cue": (piece["start"], piece["end"])},
                geometry_role=geometry_role,
                cell_index=piece["cell_index"],
            )
        for pattern, role in (
            (r"\b(?:mean|variance|probability|count|frequency|standard deviation)\b", "value_role"),
            (r"[%$€£]|\b(?:kg|USD|EUR|seconds|meters)\b", "unit"),
        ):
            if (match := re.search(pattern, literal, re.I)) is not None:
                emit(
                    "table_role",
                    piece["item_ref"],
                    {"cue": (piece["start"] + match.start(), piece["start"] + match.end())},
                    measure_role=role,
                    cell_index=piece["cell_index"],
                )

    # The native matcher owns linguistic role expansion and cautious/quoted scope here.
    selections = tuple(
        StructuralPassage(
            passage_id="primary/" + str(i),
            source_ref="primary",
            start=s.get("start", 0),
            end=s.get("end", len(view.text)),
            text=view.text[s.get("start", 0) : s.get("end", len(view.text))],
            scope="primary",
        )
        for i, s in enumerate(layer.scope["selectors"])
        if s["projection"] == view.ref.projection_digest
        and s.get("start", 0) < s.get("end", len(view.text))
    )
    for match in named_source_links(view.text, pieces, items, selections):
        roles = dict(subject=match.left, cue=match.cue)
        if match.right is not None and match.target_pointer == match.pointer:
            roles["argument"] = match.right
        emit(
            "lexical_named_link",
            match.pointer,
            roles,
            relation_kind=match.kind,
            resolution=match.resolution
            or (
                "target_selection_required" if match.target_pointer != match.pointer else "located"
            ),
            **({"designator": match.designator} if match.designator is not None else {}),
        )
    inspection = match_named_source_links(
        view.text, pieces, items, selections, tuple(products), version=NAMED_PIECE_VERSION
    )
    named_pieces = [
        p
        for p in physical
        if items.get(p["item_ref"], {}).get("content_layer") == "body"
        and items.get(p["item_ref"], {}).get("label") in {"text", "paragraph", "list_item"}
    ]
    incomplete |= inspection.incomplete or (bool(named_pieces) and not products)
    for piece in named_pieces:
        pointer = piece["item_ref"]
        emit(
            "named_availability",
            pointer,
            {"source": (piece["start"], piece["end"])},
            status="complete" if pointer in inspection.inspected_pointers else "unavailable",
        )
    for match in inspection.matches:
        witness = match.witness
        native_tokens = []
        for name, index in witness.tokens.items():
            references = tokens.get((f"spacy/{view.ref.id}/{witness.block}/block", index), ())
            if len(references) != 1:
                incomplete = True
                break
            native_tokens.append(dict(name=name, index=index, native_node=references[0]))
        else:
            roles = dict(subject=match.left, cue=match.cue)
            if match.right is not None:
                roles["argument"] = match.right
            if match.definition_subject is not None:
                roles["definition_subject"] = match.definition_subject[0]
            emit(
                "named_link",
                match.pointer,
                roles,
                native_tokens=native_tokens,
                rule=witness.rule,
                variant=witness.variant,
                mechanism=witness.mechanism,
                annotation=witness.annotation,
                block=witness.block,
                resolution=witness.resolution,
                relation_kind=witness.kind,
                **({"designator": witness.designator} if witness.designator is not None else {}),
                **(
                    {"definition_subject_kind": match.definition_subject[1]}
                    if match.definition_subject is not None
                    else {}
                ),
            )
    for selector in layer.scope["selectors"]:
        if selector["projection"] == view.ref.projection_digest:
            layer.record(
                FAMILY,
                selector,
                "partial" if incomplete else "complete",
                "native navigation columns or matching population incomplete"
                if incomplete
                else None,
            )


@dataclass(frozen=True, slots=True)
class NavigationRecord:
    reference: Any
    payload: Mapping[str, Any]
    occurrences: Mapping[str, Any]

    def fragments(self, role):
        found = [row for row in self.payload["roles"] if row["role"] == role]
        if not found:
            return ()
        if len(found) != 1:
            raise ValueError("navigation role identity repeats")
        return tuple(
            extent for oid in found[0]["occurrences"] for extent in self.occurrences[oid]["extents"]
        )

    def span(self, role):
        values = self.fragments(role)
        return (
            None if not values else (min(e["start"] for e in values), max(e["end"] for e in values))
        )

    def text(self, role):
        return "".join(e["text"] for e in self.fragments(role))


class NavigationIndex:
    """Exact retained semantic fields; constructing this index performs no recognition."""

    def __init__(self, layers, projection, *, source_view_id=None):
        from corpus_structure.semantic.characterization import annotation_reference

        self.records = []
        self.coverage = []
        for pin, report in (layers or {}).items():
            if report.reference(pin.task_id) != pin:
                raise ValueError("navigation requires exact retained layer pins")
            body = report.payload
            if (
                source_view_id is not None
                and source_view_id not in body["source_scope"]["source_view_ids"]
            ):
                continue
            occurrences = {o["local_id"]: o for o in body["occurrences"]}
            self.coverage.extend(
                c
                for c in body["coverage"]
                if c["family"] == FAMILY
                and any(s["projection"] == projection for s in c.get("examined", ()))
            )
            for annotation in body["annotations"]:
                navigation = annotation.get("navigation")
                if navigation is None:
                    continue
                if navigation["codec"] != CODEC or annotation["family"] != FAMILY:
                    raise ValueError("unsupported retained navigation codec or family")
                refs = [oid for role in navigation["roles"] for oid in role["occurrences"]]
                if any(oid not in occurrences for oid in refs):
                    raise ValueError("navigation role has an unknown source occurrence")
                extents = [e for oid in refs for e in occurrences[oid]["extents"]]
                if not extents or any(
                    e.get("synthetic") or "text" not in e or "start" not in e or "end" not in e
                    for e in extents
                ):
                    raise ValueError("navigation roles require literal source evidence")
                if any(
                    e["projection"] != projection
                    or (source_view_id is not None and e["source_view_id"] != source_view_id)
                    for e in extents
                ):
                    continue
                if annotation.get("required_choices") or annotation.get(
                    "required_external_choices"
                ):
                    raise ValueError("navigation projection requires explicit analytical choices")
                self.records.append(
                    NavigationRecord(
                        annotation_reference(pin, annotation["local_id"]), navigation, occurrences
                    )
                )

    @property
    def complete(self):
        return bool(self.coverage) and all(
            c["availability"] == "available" and c["outcome"] in {"complete", "empty"}
            for c in self.coverage
        )

    def select(self, kind, pointer=None):
        return tuple(
            row
            for row in self.records
            if row.payload["kind"] == kind
            and (pointer is None or row.payload["pointer"] == pointer)
        )

    def require(self):
        if not self.complete:
            raise ValueError("required primary navigation coverage is missing or incomplete")
        return self
