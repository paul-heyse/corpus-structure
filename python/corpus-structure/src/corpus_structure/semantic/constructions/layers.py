"""Detach construction products into the existing immutable shared layer contract."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from typing import Any

from corpus_structure.semantic.characterization import occurrence_id, validate_layer
from corpus_structure.semantic.identity import canonical_bytes

from .declarations import DECLARATIONS, FAMILIES, GRAMMAR_FAMILIES, MODAL_FORCES, REVISION
from .forest import ProtectedAtom, identity, recognize
from .lexical import PositionedTerminal


@dataclass(frozen=True)
class ConstructionSource:
    """An owned source-coordinate snapshot; no physical source-view/task surrogate."""
    content: bytes

    @classmethod
    def from_native(cls, source):
        return cls(canonical_bytes(source.value))

    @property
    def value(self):
        return json.loads(self.content)

    @property
    def text(self):
        return self.value["text"]

    @property
    def pieces(self):
        return tuple(self.value["pieces"])

    @property
    def projection(self):
        return self.value["source"]["projection"]

    @property
    def key(self):
        from ..source_products import source_subject
        return source_subject(self.value["source"])


def _source_projection(view):
    return view.projection if isinstance(view,ConstructionSource) else view.ref.projection_digest


def _source_key(view):
    return view.key if isinstance(view,ConstructionSource) else view.ref.id


class ConstructionLayer:
    def __init__(
        self,
        base: Mapping[str, Any],
        scope: Mapping[str, Any],
        operation: Mapping[str, Any],
        *,
        families=FAMILIES,
        semantic: bool = False,
    ):
        self.base, self.scope = dict(base), dict(scope)
        self.semantic = semantic
        self.families = tuple(families)
        self.operation = {
            **operation,
            "produced_families": list(self.families),
            "outcomes": ["complete", "partial", "failed"],
            "preconditions": ["exact-source-projection", "protected-whole-atoms"],
            "effects": ["retain-packed-primary-interpretation"],
            "result_determinants": ["runtime", "grammar", "configuration", "input", "context"],
        }
        self.occurrences: dict[str, dict[str, Any]] = {}
        self.annotations: dict[str, dict[str, Any]] = {}
        self.terms: dict[str, dict[str, Any]] = {}
        self.choices: dict[str, dict[str, Any]] = {}
        self.memberships: dict[str, dict[str, Any]] = {}
        self.roles: dict[str, dict[str, Any]] = {}
        self.coverage: list[dict[str, Any]] = []

    def occurrence(self, view, start: int, end: int) -> str:
        if not 0 <= start <= end <= len(view.text):
            raise ValueError("construction extent lies outside its source projection")
        extents: list[dict[str,Any]] = []
        for piece in view.pieces:
            a, b = max(start, piece["start"]), min(end, piece["end"])
            if a < b or (start == end and piece["start"] <= start <= piece["end"]):
                pointer = piece.get("item_ref")
                if pointer is None:
                    pointer = next(
                        (p["item_ref"] for p in view.pieces if p.get("item_ref") and p["end"] >= a),
                        None,
                    )
                if pointer is None:
                    raise ValueError("construction source piece has no native address")
                extent = dict(
                    projection=_source_projection(view),
                    **({} if self.semantic else {"source_view_id":_source_key(view)}),
                    native_pointer=pointer,
                    start=a,
                    end=b,
                    text=view.text[a:b],
                    synthetic=start == end or piece["kind"] != "native_text",
                )
                if piece.get("page") is not None:
                    extent["page"] = piece["page"]
                extents.append(extent)
                if start == end:
                    break
        if not extents or sum(e["end"] - e["start"] for e in extents) != end - start:
            raise ValueError("construction extent crosses unmapped source")
        key = occurrence_id(self.base, extents)
        self.occurrences.setdefault(key, dict(local_id=key, extents=extents))
        return key

    def record(
        self, family: str, selector: Mapping[str, Any], outcome: str, reason: str | None = None
    ):
        row = dict(
            family=family,
            operation=self.operation["key"],
            eligible=[dict(selector)],
            examined=[] if outcome in {"unsupported", "failed", "unknown"} else [dict(selector)],
            unexamined=[dict(selector)] if outcome in {"unsupported", "failed", "unknown"} else [],
            availability="unsupported"
            if outcome == "unsupported"
            else "unavailable"
            if outcome in {"failed", "unknown"}
            else "available",
            outcome=outcome,
            profile=REVISION,
        )
        if reason:
            row["reason"] = reason
        self.coverage.append(row)

    def region(
        self,
        view,
        start: int,
        end: int,
        atoms: Sequence[ProtectedAtom] = (),
        *,
        max_chars: int = 4096,
        terminals: tuple[PositionedTerminal, ...] | None = None,
        parse_seconds: float = 2.0,
        check_active=lambda: None,
    ):
        selector = dict(projection=_source_projection(view), start=start, end=end)
        result = recognize(
            view.text[start:end],
            tuple(atoms),
            region=f"{_source_key(view)}:{start}:{end}",
            offset=start,
            max_chars=max_chars,
            terminals=terminals,
            parse_seconds=parse_seconds,
            check_active=check_active,
        )
        for family in GRAMMAR_FAMILIES:
            self.record(family, selector, result.outcome, result.reason)
        if result.reducer is None:
            return result
        reducer = result.reducer
        for key, syntax in reducer.syntax.items():
            occurrences = [self.occurrence(view, syntax["start"], syntax["end"])]
            row = {
                k: v
                for k, v in syntax.items()
                if k not in {"start", "end", "complete"} and v is not None
            }
            row.update(
                family="construction.predication",
                vocabulary=REVISION,
                native_scheme="lark-prose-1",
                status="interpreted",
                occurrences=occurrences,
            )
            self.annotations[key] = row
        for key, term in reducer.terms.items():
            a, b = reducer.positions[key]
            self.terms[key] = {**term, "occurrences": [self.occurrence(view, a, b)]}
        self.choices.update(reducer.choices)
        branch_requirements = {}
        for group in reducer.choices.values():
            for member in group["members"]:
                branch_requirements.setdefault(member["root"], []).append(member["local_id"])
        for key, required in branch_requirements.items():
            self.terms[key]["required_choices"] = required
        # A complete grammar-production witness retains its actual named bindings.
        # Prefix alternatives remain packed; only actual term endpoints gain roles.
        products_by_production = {}
        for product in reducer.terms.values():
            premises = product.get("premises")
            if isinstance(premises, list) and len(premises) == 1:
                products_by_production.setdefault(premises[0], []).append(product)
        for key, syntax in reducer.syntax.items():
            name = syntax.get("native_label", "").removeprefix("prose__")
            declaration = DECLARATIONS.get(name)
            if (
                not declaration
                or not syntax.get("complete")
                or syntax["kind"] != "grammar.production"
            ):
                continue
            for product in products_by_production.get(key, ()):
                if product["value"] != name:
                    continue
                construction = identity(
                    "construction", [key, product["local_id"], declaration.rule_id]
                )
                occurrences = self.terms[product["local_id"]]["occurrences"]
                required = branch_requirements.get(product["local_id"], [])
                self.annotations[construction] = dict(
                    local_id=construction,
                    kind="construction",
                    family=declaration.family,
                    vocabulary=REVISION,
                    status="interpreted",
                    rule_id=declaration.rule_id,
                    native_scheme="lark-prose-1",
                    native_label=syntax["native_label"],
                    occurrences=occurrences,
                    premises=[key],
                    required_choices=required,
                )
                meaning = identity("construction-meaning", [construction, product["local_id"]])
                self.memberships[meaning] = dict(
                    local_id=meaning,
                    group=construction,
                    member=product["local_id"],
                    role="meaning",
                    order=0,
                    structural=False,
                    scope=construction,
                    occurrences=occurrences,
                    family=declaration.family,
                    premises=[key],
                    required_choices=required,
                )
                for edge in product["children"]:
                    if "target" not in edge or edge["role"] not in declaration.roles:
                        continue
                    member = edge["target"]
                    # Actual endpoints must already be premises of this production.
                    if member not in self.annotations[key].get("premises", ()):
                        continue
                    binding = identity(
                        "binding", [construction, member, edge["role"], edge["order"]]
                    )
                    member_occurrences = self.terms[member]["occurrences"]
                    self.memberships[binding] = dict(
                        local_id=binding,
                        group=construction,
                        member=member,
                        role=edge["role"],
                        order=edge["order"],
                        structural=False,
                        scope=construction,
                        occurrences=member_occurrences,
                        family=declaration.family,
                        premises=[key],
                        required_choices=required,
                    )
                    role = identity("role", [construction, binding])
                    self.roles[role] = dict(
                        local_id=role,
                        owner=construction,
                        member=member,
                        role=edge["role"],
                        scheme="linguistic-grammar-role-1",
                        family=declaration.family,
                        occurrences=member_occurrences,
                        required_choices=required,
                        basis=dict(
                            kind="released_construction",
                            status="witnessed",
                            rule_id=declaration.rule_id,
                            construction=construction,
                            binding=binding,
                            production=key,
                            premises=[construction, key, binding],
                            choice_refs=required,
                        ),
                    )
        if result.root:
            root = identity(
                "root", [_source_key(view), start, end, result.root.target, result.root.choice_group]
            )
            self.terms[root] = dict(
                local_id=root,
                family="construction.predication",
                kind="unknown",
                vocabulary=REVISION,
                value="primary-reading",
                status="unknown",
                children=[result.root.edge("reading")],
                occurrences=[self.occurrence(view, start, end)],
            )
        return result

    def native(self, view, pin, container, doc, annotations, offset, prepared):
        """Keep native matches and their actual members separate from grammar claims."""
        matches, unavailable = prepared.match(doc)
        participant_ids = {}
        for index, annotation in annotations.items():
            token = doc[index]
            # Native whitespace tokens remain in their original evidence layer.
            # Layout separators do not denote participants in a source predication.
            if token.is_space:
                continue
            lexical = annotation["native_token"].get("lemma") or token.text
            # A participant's interpreted lexical label is distinct from its exact
            # native spelling. Protected mathematical atoms can contain layout
            # newlines; their original bytes remain in occurrences/native premises.
            label = " ".join(lexical.split()) or " ".join(token.text.split())
            occurrence = self.occurrence(view, offset + token.idx, offset + token.idx + len(token))
            external = dict(layer=pin.values(), local_id=annotation["local_id"])
            key = identity("native-participant", [pin.values(), annotation["local_id"]])
            participant_ids[index] = key
            self.terms[key] = dict(
                local_id=key,
                family="construction.predication",
                kind="participant",
                vocabulary=REVISION,
                value=label,
                status="interpreted",
                occurrences=[occurrence],
                external_premises=[external],
                **(
                    {"provenance": ["lexical-normalization:whitespace-folding-1"]}
                    if label != lexical
                    else {}
                ),
            )
        predicate_terms = {}
        for index, annotation in annotations.items():
            token = doc[index]
            if index not in participant_ids or token.pos_ not in {"VERB", "AUX", "ADJ", "NOUN"}:
                continue
            key = identity("native-predication", [pin.values(), annotation["local_id"]])
            predicate_terms[index] = key
            children = [dict(role="predicate", target=participant_ids[index], structural=True)]
            for child in token.children:
                if child.i not in participant_ids:
                    continue
                role = {
                    "nsubj": "grammatical_subject",
                    "nsubjpass": "grammatical_subject",
                    "dobj": "grammatical_object",
                    "obj": "grammatical_object",
                    "attr": "complement",
                    "acomp": "focus",
                    "iobj": "indirect_object",
                }.get(child.dep_)
                if role:
                    children.append(
                        dict(role=role, target=participant_ids[child.i], structural=True)
                    )
            # Unknown roles remain distinct from a claimed absent participant.
            if not any(e["role"] == "grammatical_subject" for e in children):
                unknown = identity("implicit-role", [key, "grammatical_subject"])
                self.terms[unknown] = dict(
                    local_id=unknown,
                    family="construction.predication",
                    kind="participant",
                    vocabulary=REVISION,
                    value="unresolved-subject",
                    status="unknown",
                    occurrences=[],
                )
                children.append(dict(role="grammatical_subject", target=unknown, structural=True))
            self.terms[key] = dict(
                local_id=key,
                family="construction.predication",
                kind="predicate",
                vocabulary=REVISION,
                value="native-predication-proposal",
                status="interpreted",
                children=children,
                occurrences=self.terms[participant_ids[index]]["occurrences"],
                provenance=["grammatical-role-scheme:spacy-english-dependency-1"],
                external_premises=[dict(layer=pin.values(), local_id=annotation["local_id"])],
            )
            morph = token.morph.to_dict()
            for feature, values in morph.items():
                for native_value in values.split(","):
                    cue = identity("inflection", [key, feature, native_value])
                    self.annotations[cue] = dict(
                        local_id=cue,
                        kind="construction.inflection",
                        family="construction.inflection",
                        vocabulary=REVISION,
                        native_scheme="spacy-morphology-1",
                        native_label=feature + "=" + native_value,
                        status="interpreted",
                        occurrences=self.terms[key]["occurrences"],
                        external_premises=self.terms[key]["external_premises"],
                    )
                    normalized = {
                        ("Voice", "Pass"): "voice:passive",
                        ("Voice", "Act"): "voice:active",
                        ("Tense", "Past"): "tense:past",
                        ("Tense", "Pres"): "tense:present",
                        ("Tense", "Fut"): "tense:future",
                        ("Aspect", "Prog"): "aspect:progressive",
                        ("Aspect", "Perf"): "aspect:perfective",
                        ("Aspect", "Imp"): "aspect:imperfective",
                        ("Mood", "Ind"): "mood:indicative",
                        ("Mood", "Sub"): "mood:subjunctive",
                        ("Mood", "Imp"): "mood:imperative",
                    }.get((feature, native_value))
                    if normalized:
                        meaning = identity("inflection-meaning", [cue, normalized])
                        self.terms[meaning] = dict(
                            local_id=meaning,
                            family="construction.inflection",
                            kind="operator",
                            vocabulary=REVISION,
                            value=normalized,
                            status="interpreted",
                            children=[
                                dict(role="target", target=key, structural=True),
                                dict(role="cue", target=participant_ids[index], structural=True),
                            ],
                            occurrences=self.terms[key]["occurrences"],
                            premises=[cue],
                            external_premises=self.terms[key]["external_premises"],
                        )
        for match in matches:
            members = [i for _, indices in match.bindings for i in indices if i in participant_ids]
            if not members:
                continue
            premises = [
                dict(layer=pin.values(), local_id=annotations[i]["local_id"])
                for i in dict.fromkeys(members)
            ]
            occurrences = list(
                dict.fromkeys(
                    o for i in members for o in self.terms[participant_ids[i]]["occurrences"]
                )
            )
            key = identity(
                "native-construction", [pin.values(), container, match.rule_id, match.bindings]
            )
            self.annotations[key] = dict(
                local_id=key,
                kind="construction",
                family=match.family,
                vocabulary=REVISION,
                rule_id=match.rule_id,
                native_scheme="spacy-named-match-1",
                native_label=match.mechanism,
                status="interpreted",
                occurrences=occurrences,
                external_premises=premises,
                provenance=["pattern-alignment:" + ",".join(map(str, match.alignments))]
                if match.alignments
                else [],
            )
            for role_name, indices in match.bindings:
                for order, index in enumerate(indices):
                    if index not in participant_ids:
                        continue
                    membership = identity(
                        "native-binding", [key, role_name, order, participant_ids[index]]
                    )
                    self.memberships[membership] = dict(
                        local_id=membership,
                        group=key,
                        member=participant_ids[index],
                        role=role_name,
                        order=order,
                        structural=False,
                        scope=key,
                        family=match.family,
                        occurrences=self.terms[participant_ids[index]]["occurrences"],
                        external_premises=premises,
                    )
            if match.mechanism != "dependency":
                continue
            anchors = dict(match.anchors)
            governor = anchors["governor"]
            dependent = next(index for name, index in match.anchors if name != "governor")
            if governor not in predicate_terms:
                continue
            root = predicate_terms[governor]
            meaning = identity("construction-meaning", [key, root])
            self.memberships[meaning] = dict(
                local_id=meaning,
                group=key,
                member=root,
                role="meaning",
                order=0,
                structural=False,
                scope=key,
                occurrences=self.terms[root]["occurrences"],
                family=match.family,
                external_premises=premises,
            )
            kind, value, roles = "operator", match.rule_id, []
            if "negative_target" in match.rule_id:
                roles = [
                    dict(role="target", target=root, structural=True),
                    dict(role="cue", target=participant_ids[dependent], structural=True),
                ]
                value = "negation"
            elif "auxiliary" in match.rule_id:
                roles = [
                    dict(role="target", target=root, structural=True),
                    dict(role="cue", target=participant_ids[dependent], structural=True),
                ]
                value = "voice-tense-aspect-mood-proposal"
            elif "reporting" in match.rule_id and dependent in predicate_terms:
                kind, value = "attribution", "reported-content"
                roles = [
                    dict(role="reporter_predication", target=root, structural=True),
                    dict(role="content", target=predicate_terms[dependent], structural=True),
                ]
            elif "coordination" in match.rule_id and dependent in predicate_terms:
                value = "coordination"
                roles = [
                    dict(role="left", target=root, structural=True),
                    dict(role="right", target=predicate_terms[dependent], structural=True),
                ]
                # Inherit a missing grammatical subject only across an actual conj
                # edge. Local subjects always win; no neighboring object is copied.
                child = self.terms[predicate_terms[dependent]]
                if not any(c.dep_ in {"nsubj", "nsubjpass"} for c in doc[dependent].children):
                    for edge in self.terms[root]["children"]:
                        if (
                            edge["role"] == "grammatical_subject"
                            and self.terms[edge["target"]]["status"] != "unknown"
                        ):
                            inherited = identity("inherited-subject", [key, edge["target"]])
                            self.terms[inherited] = dict(
                                local_id=inherited,
                                family="construction.coordination",
                                kind="participant",
                                vocabulary=REVISION,
                                value="inherited-grammatical-subject",
                                status="interpreted",
                                children=[
                                    dict(role="member", target=edge["target"], structural=True)
                                ],
                                occurrences=self.terms[edge["target"]]["occurrences"],
                                premises=[key],
                                external_premises=premises,
                            )
                            child["children"] = [
                                e for e in child["children"] if e["role"] != "grammatical_subject"
                            ] + [
                                dict(role="grammatical_subject", target=inherited, structural=True)
                            ]
            elif "relative" in match.rule_id and dependent in predicate_terms:
                kind, value = "predicate", "relative-gap-proposal"
                gap = identity("relative-gap", [key, participant_ids[governor]])
                self.terms[gap] = dict(
                    local_id=gap,
                    family="construction.embedding",
                    kind="participant",
                    vocabulary=REVISION,
                    value="relative-gap",
                    status="implicit",
                    occurrences=[
                        self.occurrence(
                            view, offset + doc[dependent].idx, offset + doc[dependent].idx
                        )
                    ],
                    children=[
                        dict(role="antecedent", target=participant_ids[governor], structural=True)
                    ],
                    premises=[key],
                )
                roles = [
                    dict(role="body", target=predicate_terms[dependent], structural=True),
                    dict(role="gap", target=gap, structural=True),
                ]
            elif "complement" in match.rule_id and dependent in predicate_terms:
                kind, value = "predicate", "complement"
                roles = [
                    dict(role="governor", target=root, structural=True),
                    dict(role="complement", target=predicate_terms[dependent], structural=True),
                ]
            elif "clause_relation" in match.rule_id and dependent in predicate_terms:
                kind, value = "clause_relation", "native-adverbial-clause"
                roles = [
                    dict(role="governor", target=root, structural=True),
                    dict(role="subordinate", target=predicate_terms[dependent], structural=True),
                ]
            if roles:
                semantic = identity("native-meaning", [key, value, roles])
                self.terms[semantic] = dict(
                    local_id=semantic,
                    family=match.family,
                    kind=kind,
                    vocabulary=REVISION,
                    value=value,
                    status="interpreted",
                    children=roles,
                    occurrences=occurrences,
                    premises=[key],
                    external_premises=premises,
                )
        self._native_scope(view, pin, doc, annotations, offset, participant_ids, predicate_terms)
        return matches, unavailable

    def _native_scope(self, view, pin, doc, annotations, offset, participants, predicates):
        for index, annotation in annotations.items():
            token = doc[index]
            word = token.lower_
            if word not in {
                "not",
                "never",
                *MODAL_FORCES,
                "every",
                "all",
                "each",
                "some",
                "any",
                "no",
            }:
                continue
            governor = token.head
            if word in {"every", "all", "each", "some", "any", "no"} and governor.dep_ in {
                "nsubj",
                "nsubjpass",
                "dobj",
                "obj",
                "iobj",
            }:
                governor = governor.head
            seen = set()
            while governor.i not in predicates and governor.i not in seen:
                seen.add(governor.i)
                governor = governor.head
            target = predicates.get(governor.i)
            if target is None:
                target = identity("unknown-target", [pin.values(), annotation["local_id"]])
                self.terms[target] = dict(
                    local_id=target,
                    family="construction.scope",
                    kind="unknown",
                    vocabulary=REVISION,
                    value="unresolved-operator-target",
                    status="unknown",
                    occurrences=[],
                )
            external = [dict(layer=pin.values(), local_id=annotation["local_id"])]
            cue = participants[index]
            occurrences = self.terms[cue]["occurrences"]
            if word in {"every", "all", "each", "some", "any", "no"}:
                restrictor = participants.get(token.head.i)
                if restrictor is None or token.dep_ not in {"det", "predet"}:
                    continue
                variable = identity(
                    "bound-variable", [pin.values(), annotation["local_id"], target]
                )
                self.terms[variable] = dict(
                    local_id=variable,
                    family="construction.scope",
                    kind="participant",
                    vocabulary=REVISION,
                    value="bound-occurrence",
                    status="implicit",
                    occurrences=[self.occurrence(view, offset + token.idx, offset + token.idx)],
                )
                body = identity("bound-body", [target, variable])
                original = self.terms[target]
                self.terms[body] = {
                    **original,
                    "local_id": body,
                    "children": [
                        {**edge, "target": variable}
                        if edge["role"] == "grammatical_subject"
                        and edge.get("target") == restrictor
                        else edge
                        for edge in original.get("children", ())
                    ],
                    "external_premises": external + original.get("external_premises", []),
                }
                binder = identity("native-binder", [pin.values(), annotation["local_id"], target])
                self.terms[binder] = dict(
                    local_id=binder,
                    family="construction.scope",
                    kind="binder",
                    vocabulary=REVISION,
                    value=word,
                    status="interpreted",
                    children=[
                        dict(role="variable", target=variable, structural=True),
                        dict(role="restrictor", target=restrictor, structural=True),
                        dict(role="body", target=body, structural=True),
                        dict(role="cue", target=cue, structural=True),
                    ],
                    occurrences=occurrences,
                    external_premises=external,
                )
            elif word in {"not", "never"}:
                key = identity("native-negative", [pin.values(), annotation["local_id"], target])
                self.terms[key] = dict(
                    local_id=key,
                    family="construction.scope",
                    kind="operator",
                    vocabulary=REVISION,
                    value="negation",
                    status="interpreted",
                    children=[
                        dict(role="cue", target=cue, structural=True),
                        dict(role="target", target=target, structural=True),
                    ],
                    occurrences=occurrences,
                    external_premises=external,
                )
            else:
                forces = MODAL_FORCES[word]
                roots = []
                for force in forces:
                    key = identity(
                        "native-modal", [pin.values(), annotation["local_id"], target, force]
                    )
                    self.terms[key] = dict(
                        local_id=key,
                        family="construction.scope",
                        kind="operator",
                        vocabulary=REVISION,
                        value="modality:" + force,
                        status="private_proposal",
                        children=[
                            dict(role="cue", target=cue, structural=True),
                            dict(role="target", target=target, structural=True),
                        ],
                        occurrences=occurrences,
                        external_premises=external,
                    )
                    roots.append(key)
                if len(roots) > 1:
                    group = identity(
                        "modal-force-choice", [pin.values(), annotation["local_id"], target]
                    )
                    self.choices[group] = dict(
                        local_id=group,
                        family="construction.scope",
                        compatibility="exclusive",
                        members=[
                            dict(
                                local_id=identity("modal-alternative", [group, key]),
                                root=key,
                                external_premises=external,
                            )
                            for key in roots
                        ],
                    )
                    for member in self.choices[group]["members"]:
                        self.terms[member["root"]]["required_choices"] = [member["local_id"]]
                    root = identity("modal-site", [group])
                    self.terms[root] = dict(
                        local_id=root,
                        family="construction.scope",
                        kind="operator",
                        vocabulary=REVISION,
                        value="modality",
                        status="unknown",
                        children=[dict(role="force", choice_group=group, structural=True)],
                        occurrences=occurrences,
                        external_premises=external,
                    )

    def facts(self):
        """Shared semantic inventory; released legacy envelope is a separate projection."""
        grouped = {}
        for row in self.coverage:
            grouped.setdefault(row["family"], []).append(row)
        coverage = []
        for family in self.families:
            rows = grouped.get(family, [])
            if not rows:
                for selector in self.scope["selectors"]:
                    requires_native = family in {
                        "construction.source_readings",
                        "construction.named_rules",
                    }
                    self.record(
                        family,
                        selector,
                        "unknown" if requires_native else "unsupported",
                        "construction family requires retained native columns"
                        if requires_native
                        else "no source region was selected",
                    )
                rows = [r for r in self.coverage if r["family"] == family]
            statuses = {r["outcome"] for r in rows}
            examined = list({canonical_bytes(s): s for r in rows for s in r["examined"]}.values())
            populated = any(
                row["family"] == family
                for values in (
                    self.annotations,
                    self.memberships,
                    self.roles,
                    self.terms,
                    self.choices,
                )
                for row in values.values()
            )
            outcome = (
                ("complete" if populated else "empty")
                if statuses <= {"complete", "empty"}
                else "partial"
                if examined
                else "unsupported"
                if statuses == {"unsupported"}
                else "unknown"
                if statuses <= {"unknown", "unsupported"}
                else "failed"
            )
            coverage.append(
                dict(
                    family=family,
                    operation=self.operation["key"],
                    profile=REVISION,
                    eligible=list(
                        {canonical_bytes(s): s for r in rows for s in r["eligible"]}.values()
                    ),
                    examined=examined,
                    unexamined=list(
                        {canonical_bytes(s): s for r in rows for s in r["unexamined"]}.values()
                    ),
                    availability="available"
                    if examined
                    else "unsupported"
                    if outcome == "unsupported"
                    else "unavailable",
                    outcome=outcome,
                    **(
                        {
                            "reason": "; ".join(
                                dict.fromkeys(
                                    r.get("reason", "incomplete grammar coverage")
                                    for r in rows
                                    if r["outcome"] not in {"complete", "empty"}
                                )
                            )
                        }
                        if outcome not in {"complete", "empty"}
                        else {}
                    ),
                )
            )
        return dict(
            outcome="complete"
            if all(r["outcome"] in {"complete", "empty"} for r in coverage)
            else "partial",
            occurrences=list(self.occurrences.values()),
            annotations=list(self.annotations.values()),
            memberships=list(self.memberships.values()),
            roles=list(self.roles.values()),
            terms=list(self.terms.values()),
            choices=list(self.choices.values()),
            coverage=coverage,
        )

    def payload(self, release_id: str, dependencies=()):
        return dict(
            format="characterization-layer-v1",
            base_document=self.base,
            release_id=release_id,
            operation=self.operation,
            source_scope=self.scope,
            dependencies=list(dependencies),
            **self.facts(),
        )

    def finish(self, prepared, *, dependencies=None, releases=None):
        pins = [] if dependencies is None else [p.values() for p in dependencies]
        return validate_layer(
            prepared,
            self.payload(prepared.release_id, pins),
            dependencies=dependencies,
            releases=releases,
        )
