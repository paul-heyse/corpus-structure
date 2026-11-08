"""Source-local link recipes over exact retained native text pieces."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from corpus_structure.ingest.annotation_views import annotation_view
from corpus_structure.ingest.annotations import AnnotationProduct, AnnotationUnavailable
from corpus_structure.methods.annotation_rules import (
    AnnotationRule,
    PreparedAnnotationRules,
    RoleBinding,
)
from corpus_structure.semantic.observations import source_python

QUESTION = "source_witnessed_links"
VERSION = "1"

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


def recapped_declarations(text, pieces, items, passages):
    """Resolve a named recap only within one complete selected passage and parent."""
    physical = [
        p
        for p in pieces
        if p.get("kind") == "native_text"
        and p.get("source_field", "text") == "text"
        and "cell_index" not in p
        and items.get(p.get("item_ref"), {}).get("content_layer") == "body"
    ]
    for passage in passages or ():
        rows = [
            (p, items[p["item_ref"]], text[p["start"] : p["end"]])
            for p in physical
            if passage.start <= p["start"] < p["end"] <= passage.end
        ]
        for i, (piece, node, literal) in enumerate(rows):
            use = RECAP.match(literal)
            parent = node.get("parent")
            if use is None or parent is None:
                continue
            symbol, name = use["symbol"], use["name"]
            earlier = [
                (p, block)
                for p, other, block in rows[:i]
                if other.get("parent") == parent and symbol in LET.findall(block)
            ]
            if len(earlier) != 1 or LET.findall(earlier[0][1]).count(symbol) != 1:
                continue
            declaration, declaration_text = earlier[0]
            binding = DECLARATION.match(declaration_text)
            if (
                binding is None
                or binding["symbol"] != symbol
                or binding["name"] != name
                or not binding["description"].startswith(
                    "a " + binding["family"] + " with parameters "
                )
            ):
                continue

            def extent(start, match, group):
                return start + match.start(group), start + match.end(group)

            yield RecappedDeclaration(
                declaration["item_ref"],
                piece["item_ref"],
                symbol,
                extent(declaration["start"], binding, "name"),
                extent(declaration["start"], binding, "description"),
                (piece["start"], piece["start"] + use.end("symbol")),
                extent(piece["start"], use, "equation"),
                passage.scope,
                passage.passage_id,
                passage.effective_version,
            )


NAMED_QUESTION = "source_named_links"
NAMED_VERSION = "2"
NAMED_COVERAGE_VERSION = "3"
NAMED_ANNOTATION_VERSIONS = frozenset({NAMED_VERSION, NAMED_COVERAGE_VERSION})
INHERITANCE_QUESTION = "source_scope_inheritance"


def qualified_inheritance(contributions):
    """Project already-qualified list and clause inheritance without reattaching cues."""
    rows = {row["contribution_id"]: row for row in contributions}
    qualified = [
        row
        for row in contributions
        if row.get("component", {}).get("kind") == "predicate_qualifier"
        and row["component"]["qualifier_kind"] in {"condition", "assumption"}
    ]
    edges = []
    for row in qualified:
        component = row["component"]
        cue = rows[component["qualifier_contribution_id"]]
        host = rows[component["host_contribution_id"]]
        witness = component.get("host_witness")
        governing = cue["component"].get("governing_token")
        listed = witness is not None and witness["kind"] == "list_intro"
        coordinated = (
            witness is None
            and governing is not None
            and governing != host["component"]["predicate_token"]
        )
        if listed or coordinated:
            edges.append((cue, host, row))
    return len(qualified), tuple(edges)


def procedure_artifact_bindings(contributions):
    """Index settled scoped caption references by the exact located source mention."""
    rows = {row["contribution_id"]: row for row in contributions}
    references = {}
    for row in contributions:
        if row.get("component", {}).get("attachment_kind") != "artifact_reference_target":
            continue
        mention = source_python(rows[row["members"][0]]["value"])
        key = (mention["source_pointer"], mention["start"], mention["end"])
        references.setdefault(key, []).append(row["contribution_id"])
    return {
        key: tuple(identifiers) for key, identifiers in references.items() if len(identifiers) == 1
    }


def procedure_artifact_endpoint(rows, link, annotation, artifact_id):
    """Bind the recipe's exact action token to the original caption relationship."""
    from corpus_structure.semantic.observations import source_python

    verb = annotation.tokens[link.witness.tokens["verb"]]
    actions = [
        row
        for row in rows.values()
        if row.get("semantic_type") == "structural.located_participant"
        and (value := source_python(row["value"])).get("role") == "procedure_action"
        and (value["source_pointer"], value["start"], value["end"])
        == (link.pointer, verb.start, verb.end)
        and link.witness.annotation in row["computation_dependencies"]
    ]
    if len(actions) != 1:
        return None
    artifact = rows[artifact_id]
    return actions[0], rows[artifact["members"][1]], artifact


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
        headings = {}
        for pointer, start, literal in rows:
            if items[pointer].get("label") == "section_header" and (
                heading := _SECTION_HEADING.match(literal)
            ):
                headings.setdefault(heading["code"], []).append(
                    (pointer, start, start + len(literal))
                )
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
                targets = headings.get(match["code"], ())
                target = targets[0] if len(targets) == 1 else None
                yield NamedLink(
                    pointer,
                    "section_citation" if match["cue"].lower() == "see" else "definition_reference",
                    extent(match, "mention"),
                    extent(match, "cue"),
                    target[0] if target else None,
                    target[1:] if target else None,
                    passage.scope,
                    passage.passage_id,
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


@dataclass(frozen=True, slots=True, kw_only=True)
class NamedLinkMatch(NamedLink):
    witness: NamedCueWitness

    def evidence(self) -> dict[str, Any]:
        return asdict(self.witness)


@dataclass(frozen=True, slots=True)
class NamedLinkInspection:
    matches: tuple[NamedLinkMatch, ...]
    inspected_count: int
    incomplete: bool

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
    if version == NAMED_COVERAGE_VERSION:
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


@lru_cache(maxsize=1)
def _named_recipe(version=NAMED_VERSION):
    from spacy.lang.en import English

    recipe = json.loads(Path(__file__).with_name("named_link_rules.json").read_bytes())
    if recipe["version"] != NAMED_VERSION:
        raise ValueError("named link recipe differs from the released version")
    if version == NAMED_COVERAGE_VERSION:
        coverage = json.loads(Path(__file__).with_name("named_link_coverage.json").read_bytes())
        if coverage["version"] != version:
            raise ValueError("named link coverage differs from the released version")
        recipe.update(coverage)
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


def match_named_source_links(
    text, pieces, items, passages, annotations, *, annotation_errors=(), version=NAMED_VERSION
) -> NamedLinkInspection:
    """Find typed link cues on restored annotations and keep their exact source roles."""
    recipe, variants, prepared = _named_recipe(version)
    pieces = {
        p["item_ref"]: p
        for p in pieces
        if p["kind"] == "native_text"
        and p.get("source_field", "text") == "text"
        and "cell_index" not in p
        and items.get(p["item_ref"], {}).get("content_layer") == "body"
        and items[p["item_ref"]].get("label") in {"text", "paragraph", "list_item"}
    }
    by_block = {
        product.block_id: product
        for product in annotations
        if isinstance(product, AnnotationProduct)
    }
    matches = []
    inspected = set()
    strict_coverage = version == NAMED_COVERAGE_VERSION
    incomplete = bool(annotation_errors) and not strict_coverage
    for pointer, piece in pieces.items():
        selected = [p for p in passages or () if p.start < piece["end"] and piece["start"] < p.end]
        if not selected:
            continue
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
        try:
            view = annotation_view(
                annotation, text[annotation.block_start : annotation.block_end], prepared.vocab
            )
        except AnnotationUnavailable:
            if strict_coverage:
                raise
            incomplete = True
            continue
        result = prepared.match(view)
        incomplete |= any(status != "available" for _, _, status in result.availability)
        inspected.add(pointer)
        tokens = annotation.tokens
        for match in result.matches:
            rule = variants[match.rule, match.variant]
            nodes = dict(zip((n["id"] for n in rule["nodes"]), match.nodes, strict=True))
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
    return NamedLinkInspection(tuple(matches), len(inspected), incomplete)
