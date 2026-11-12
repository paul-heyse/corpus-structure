"""Versioned, source-authored task meanings over declared retained relations.

Public authoring contract (not a universal logical form): entities name ordered
original source extents; assertions name literal directed roles under role_scheme.
``witness`` asks for a positive/existential characterization under at least one
explicit feasible support, not unconditionality when authored conditions are omitted.
Matched witnesses retain their actual support conditions in the result. Unknown,
missing, cyclic or incompatible support never establishes a positive witness.
``complete_slots`` closes only
explicit (subject, relation) slots, including conditional choice requirements.
Anchor conventions: predicate entities use the explicit written predicate HEAD;
operator/binder entities use their literal CUE. Target/body predicates use their
head, nested operators/binders their cue. Participants use nominal HEAD/pronoun,
following only explicit retained head/source children, never noun-head heuristics.
Implicit variable sites require support=implicit_site and explicit retained
zero-width coordinates; this is not a written occurrence or a fabricated quote.
Missing occurrence coordinates remain unavailable. Literal entities require
support=literal (the default) and nonempty original extents.
Literal cue/connective endpoints are kind=source; provider modal targets are the
whole literal quoted clause, kind=source. Local author IDs are incidental;
distinct entities remain distinct even at equal coordinates. No parser, language
interpretation or complete reading expansion runs
here. Undefined family/scheme projections report an assessment contract gap.

construction-children-v1 roles: grammatical_subject/object are grammatical roles,
not agent/patient; predicate is the written predicate head; agent is an explicitly
retained agent; cue is the overt operator cue; target is its directed scope target;
restrictor/body/variable are the quantifier's declared restriction/body/variable;
head/modifier/antecedent/complement/attachment_cue retain those literal child roles.
Other declared construction child names keep their public spelling, without aliases.
Supported construction-children-v1 families: construction.predication/scope/embedding/
inflection/coordination/clause_relation/attribution/function/source_readings/math_scope,
and meaning.predication/scope/reference/attribution/attachment/function. The binding
context scheme supports context.binding only. Undefined combinations are unavailable.
For modal_force only, construction-children-v1 also admits the explicit typed
character_modal_force_v1 model-question adapter: modal_cue, modal_target, modal_force
are joined solely by retained depends_on IDs and private_proposal memberships.
Operator value is modality:<exact declared option> (epistemic/deontic/dynamic/other/
no_modal/insufficient), never a probability or native auxiliary alias. The operator
is anchored at its located modal cue; cue and target assertions point to literal
source entities. Absent/insufficient/withheld questions never fabricate a relation.
model-question-source-v1 supports host_choice/referent_choice only. Question operators
use value=<task>:<answer state> at the frozen focal source, with focus and host/referent
roles to exact source entities. Only explicitly compatible offered host sets have
multiple endpoints; nonpositive states preserve focus without inventing an endpoint.
Retained candidate identities, extents and external choices supply all correspondence.
contextual-source-hypotheses-1 binding: declared_binding_site links binder to its
explicit variable site. Reference/binding/host assertions retain their literal
context-role names. Private hypotheses remain private in returned witnesses.

formal-children-v1 supports task=formal on formal.math only. All entities have
kind=formal and explicit value. Operators use the full exact source expression
extent; atoms use their exact written atom extent. Values: positive/negate,
add/subtract/multiply/divide/power, equals/not_equals/less_than/less_or_equal/
greater_than/greater_or_equal, membership/application/interval, set_union/
set_intersection/set_minus/set_product/set_written_product, tuple/list_of_expressions/
set_list/empty_set. Atom values are literal represented spellings; only the declared
symbol: serializer prefix is erased. Identity/content wrappers are erased; group/
content wrappers are erased unless an entity explicitly asks value=group. Roles
left/right preserve operand sides, numerator/denominator division sides, base/
exponent power sides, operand unary argument, member/set membership sides,
function/arguments application, lower/upper interval bounds; cue/open/close/
separator preserve literal syntax when asked. Explicit assertion.order compares
child order; omitted order makes no order claim beyond named directed roles. Optional
value/order/standing constraints apply only to the entity/assertion supplying them;
omission on another node never becomes an implicit null-value constraint.
No commutation, reassociation or algebraic rewrite occurs. Unsupported productions
or unavailable exact formal correspondence remain contract-unavailable.

Task and facet are different axes. Literal semantic disjunction uses a roles task
with left/right/connective child assertions; analytical uncertainty uses groups.
A positive choice task requires explicit groups. Empty-group/absence questions are
not yet a supported task contract and must remain unassessed, not a vacuous witness.

Choice groups are factorized: members have roots and directed requires; assertions
may require members. Joint queries ask about exactly that supplied selection (not
whether an invented completion could work). Exclusive conflicts or missing explicit
prerequisites are forbidden; unknown compatibility is unknown, never a policy refusal
masquerading as a source prohibition. No Cartesian expansion is performed.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python

VERSION = "characterization-task-reference-v1"

# These are declared meanings, not aliases inferred from arbitrary value strings.
TASK_ROLES = {
    "roles": frozenset(
        {
            "grammatical_subject",
            "grammatical_object",
            "predicate",
            "agent",
            "copula",
            "complement",
            "auxiliary",
            "aspect",
            "focus",
            "governor",
            "head",
            "modifier",
            "attachment_cue",
            "antecedent",
            "body",
            "left",
            "right",
            "connective",
            "agent_cue",
        }
    ),
    "scope": frozenset(
        {
            "cue",
            "target",
            "restrictor",
            "body",
            "variable",
            "quantifier_cue",
            "negative_cue",
            "negative_target",
            "predicate",
            "grammatical_subject",
            "grammatical_object",
            "auxiliary",
            "aspect",
        }
    ),
    "binding": frozenset({"variable", "declared_binding_site"}),
    "choices": frozenset(),
    "modal_force": frozenset({"cue", "target"}),
    "host_choice": frozenset({"focus", "host"}),
    "referent_choice": frozenset({"focus", "referent"}),
    "formal": frozenset(
        {
            "left",
            "right",
            "cue",
            "operand",
            "numerator",
            "denominator",
            "base",
            "exponent",
            "member",
            "set",
            "function",
            "arguments",
            "open",
            "close",
            "content",
            "lower",
            "upper",
            "separator",
        }
    ),
}
ROLE_DEFINITIONS = {
    "grammatical_subject": "Retained grammatical subject; no semantic actor coercion.",
    "grammatical_object": "Retained grammatical object; no patient coercion.",
    "predicate": "Explicit written predicate head of a construction.",
    "agent": "Explicit retained agent endpoint, distinct from grammatical subject.",
    "cue": "Explicit overt cue of the operator or binder.",
    "target": "Directed scope target of an operator.",
    "restrictor": "Declared restriction of a quantified participant.",
    "body": "Declared proposition/body of a binder or embedding.",
    "variable": "Explicit variable site attached to its binder.",
    "declared_binding_site": "Contextual binder-to-variable hypothesis; private standing retained.",
    "copula": "Explicit copular word.",
    "complement": "Declared complement.",
    "auxiliary": "Explicit auxiliary.",
    "aspect": "Explicit aspect cue.",
    "focus": "Declared focal endpoint.",
    "host": "Exact source endpoint of the selected offered host or compatible host set.",
    "referent": "Exact source antecedent selected from the frozen offered population.",
    "governor": "Declared governing endpoint.",
    "head": "Declared head.",
    "modifier": "Declared modifier.",
    "attachment_cue": "Explicit attachment cue.",
    "antecedent": "Declared antecedent.",
    "left": "Left coordination endpoint.",
    "right": "Right coordination endpoint.",
    "connective": "Explicit connective.",
    "agent_cue": "Explicit agent-introducing cue.",
    "quantifier_cue": "Explicit quantifier cue.",
    "negative_cue": "Explicit negative cue.",
    "negative_target": "Declared target of the negative cue.",
}


class _Closed(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TaskExtent(_Closed):
    source_view_id: StrictInt = Field(gt=0)
    projection: str = Field(pattern=r"^[a-f0-9]{64}$")
    native_pointer: str = Field(min_length=1)
    start: StrictInt = Field(ge=0)
    end: StrictInt = Field(ge=0)

    @model_validator(mode="after")
    def ordered(self):
        if self.end < self.start:
            raise ValueError("task entity source extent is reversed")
        return self


class TaskEntity(_Closed):
    id: str = Field(min_length=1)
    kind: Literal[
        "predicate", "participant", "operator", "binder", "variable", "source", "unknown", "formal"
    ]
    extents: tuple[TaskExtent, ...] = Field(min_length=1, max_length=64)
    value: str | None = None
    support: Literal["literal", "implicit_site"] = "literal"

    @model_validator(mode="after")
    def literal_meaning(self):
        if self.support == "implicit_site":
            if self.kind != "variable" or any(e.start != e.end for e in self.extents):
                raise ValueError(
                    "implicit site requires a variable with explicit zero-width site coordinates"
                )
        elif any(e.start == e.end for e in self.extents):
            raise ValueError("literal task entity cannot invent a zero-width written occurrence")
        if self.kind == "formal" and not self.value:
            raise ValueError(
                "formal task entities require their explicit declared operator/atom value"
            )
        if self.value is not None and self.kind not in {"operator", "binder", "formal"}:
            raise ValueError("only an explicit operator/binder semantic label may be compared")
        return self


class TaskAssertion(_Closed):
    subject: str = Field(min_length=1)
    relation: str = Field(min_length=1)
    object: str = Field(min_length=1)
    requires: tuple[str, ...] = Field(default=(), max_length=64)
    order: StrictInt | None = Field(default=None, ge=0)
    standing: str | None = None


class TaskSlot(_Closed):
    subject: str = Field(min_length=1)
    relation: str = Field(min_length=1)


class TaskMember(_Closed):
    id: str = Field(min_length=1)
    root: str = Field(min_length=1)
    requires: tuple[str, ...] = Field(default=(), max_length=64)


class TaskGroup(_Closed):
    id: str = Field(min_length=1)
    compatibility: Literal["exclusive", "compatible", "unknown"]
    members: tuple[TaskMember, ...] = Field(min_length=1, max_length=64)


class JointQuery(_Closed):
    members: tuple[str, ...] = Field(min_length=1, max_length=64)
    expected: Literal["permitted", "forbidden", "unknown"]


class SemanticTaskReference(_Closed):
    version: Literal["characterization-task-reference-v1"]
    task: Literal[
        "roles",
        "scope",
        "binding",
        "choices",
        "modal_force",
        "formal",
        "host_choice",
        "referent_choice",
    ]
    role_scheme: Literal[
        "construction-children-v1",
        "contextual-source-hypotheses-1",
        "formal-children-v1",
        "model-question-source-v1",
    ]
    mode: Literal["witness", "complete_slots"]
    focus: str = Field(min_length=1)
    entities: tuple[TaskEntity, ...] = Field(min_length=1, max_length=128)
    assertions: tuple[TaskAssertion, ...] = Field(default=(), max_length=256)
    complete_slots: tuple[TaskSlot, ...] = Field(default=(), max_length=64)
    groups: tuple[TaskGroup, ...] = Field(default=(), max_length=32)
    joint_queries: tuple[JointQuery, ...] = Field(default=(), max_length=64)

    @model_validator(mode="after")
    def closed_task(self):
        entities = {e.id for e in self.entities}
        members = [m.id for g in self.groups for m in g.members]
        groups = [g.id for g in self.groups]
        if (
            len(entities) != len(self.entities)
            or len(set(members)) != len(members)
            or len(set(groups)) != len(groups)
        ):
            raise ValueError("task identities must be unique in their typed populations")
        if self.focus not in entities:
            raise ValueError("task focus must identify an independently anchored entity")
        if self.mode == "witness" and (
            self.complete_slots or not (self.assertions or self.groups or self.joint_queries)
        ):
            raise ValueError(
                "witness tasks require positive assertions/choices without closed slots"
            )
        if self.mode == "complete_slots" and not self.complete_slots and self.task != "choices":
            raise ValueError("complete task requires explicit named slots")
        allowed = TASK_ROLES[self.task]
        if any(
            a.subject not in entities
            or a.object not in entities
            or a.relation not in allowed
            or not set(a.requires) <= set(members)
            for a in self.assertions
        ):
            raise ValueError("task assertion has an undeclared endpoint, role or choice")
        if any(s.subject not in entities or s.relation not in allowed for s in self.complete_slots):
            raise ValueError("task complete slot has an undeclared subject or role")
        if self.mode == "complete_slots" and any(
            (a.subject, a.relation) not in {(s.subject, s.relation) for s in self.complete_slots}
            for a in self.assertions
        ):
            raise ValueError("complete task assertions must belong to named slots")
        if any(
            m.root not in entities or not set(m.requires) <= set(members)
            for g in self.groups
            for m in g.members
        ):
            raise ValueError("task choice member has an undeclared root or prerequisite")
        if any(
            len(set(q.members)) != len(q.members) or not set(q.members) <= set(members)
            for q in self.joint_queries
        ):
            raise ValueError("joint query must identify distinct declared members")
        if self.task == "choices" and not self.groups:
            raise ValueError("choice task requires an explicit factorized choice question")
        if (self.role_scheme == "formal-children-v1") != (self.task == "formal"):
            raise ValueError("formal task and formal-child scheme must be selected together")
        if self.role_scheme == "contextual-source-hypotheses-1" and self.task != "binding":
            raise ValueError("contextual scheme currently declares only binding tasks")
        if (self.role_scheme == "model-question-source-v1") != (
            self.task in {"host_choice", "referent_choice"}
        ):
            raise ValueError("candidate question tasks require the model-question source scheme")
        return self


def joint_outcome(groups, selected):
    members = {m["id"]: (g, m) for g in groups for m in g["members"]}
    if not set(selected) <= members.keys():
        return "unknown"
    by_group = Counter()
    unknown = False
    for key in selected:
        group, member = members[key]
        if not set(member.get("requires", ())) <= set(selected):
            return "forbidden"
        by_group[group["id"]] += 1
        if by_group[group["id"]] > 1:
            if group["compatibility"] == "exclusive":
                return "forbidden"
            unknown |= group["compatibility"] == "unknown"
    return "unknown" if unknown else "permitted"


def witness_support(groups, required):
    """Check explicit prerequisite closure, never search or complete alternatives.

    This answers whether the matched positive claim has a grounded support. Joint
    queries keep their separate exact-selection meaning in joint_outcome.
    """
    members = {m["id"]: m for group in groups for m in group["members"]}
    active, closed = set(), set()
    pending = [(member, False) for member in sorted(set(required))]
    while pending:
        member, leaving = pending.pop()
        if leaving:
            active.remove(member)
            closed.add(member)
            continue
        if member in closed:
            continue
        if member not in members:
            return dict(
                status="unknown",
                reason="missing_prerequisite",
                members=sorted(closed | active | {member}),
            )
        if member in active:
            return dict(
                status="unknown", reason="cyclic_prerequisite", members=sorted(closed | active)
            )
        active.add(member)
        pending.append((member, True))
        pending.extend(
            (dependency, False) for dependency in sorted(set(members[member].get("requires", ())))
        )
    outcome = joint_outcome(groups, closed)
    return dict(
        status="feasible" if outcome == "permitted" else outcome,
        reason=None
        if outcome == "permitted"
        else "exclusive_conflict"
        if outcome == "forbidden"
        else "unknown_compatibility",
        members=sorted(closed),
    )


_CONSTRUCTION_FAMILIES = frozenset(
    {
        "construction.predication",
        "construction.scope",
        "construction.embedding",
        "construction.inflection",
        "construction.coordination",
        "construction.clause_relation",
        "construction.attribution",
        "construction.function",
        "construction.source_readings",
        "construction.math_scope",
        "meaning.predication",
        "meaning.scope",
        "meaning.reference",
        "meaning.attribution",
        "meaning.attachment",
        "meaning.function",
    }
)
_KINDS = {"predicate", "participant", "operator", "binder", "unknown"}
_EXTENTS = ("source_view_id", "projection", "native_pointer", "start", "end")


class ContractUnavailable(ValueError):
    pass


def _entity_meaning(entity, *, compare_value=False):
    value = {
        "kind": entity["kind"],
        "extents": entity["extents"],
        "support": entity.get("support", "literal"),
    }
    if compare_value:
        value["value"] = entity.get("value")
    return value


def _entity_compatible(actual, expected):
    required = _entity_meaning(expected, compare_value=expected.get("value") is not None)
    observed = _entity_meaning(actual, compare_value=True)
    return all(observed.get(key) == value for key, value in required.items())


class TaskPopulation:
    """Merge qualified witnesses, never content-deduplicate distinct assertions."""

    def __init__(self, predictions, reference, family, *, output_first=False):
        self.reference, self.family = reference, family
        self.output_first = output_first
        self.nodes, self.roots = {}, set()
        self.entities, self.assertions, self.groups = {}, [], []
        self._normalizing = set()
        self._formal_precision_checked = set()
        indexed_graphs = {}
        for prediction in predictions:
            graph = prediction.get("task_graph", prediction.get("graph"))
            if graph is None:
                raise ContractUnavailable(
                    "semantic task population lacks its declared witness projection"
                )
            graph_id = id(graph)
            identities = indexed_graphs.get(graph_id)
            if identities is None:
                identities = {
                    n["id"]: canonical_bytes(n["qualified_identity"]).decode()
                    for n in graph["nodes"]
                }
                indexed_graphs[graph_id] = identities
                for node in graph["nodes"]:
                    key = identities[node["id"]]
                    self.nodes[key] = dict(
                        node, edges=[dict(e, target=identities[e["target"]]) for e in node["edges"]]
                    )
            self.roots.add(identities[prediction.get("task_graph_root", graph["root"])])
        self.variable_sites = {
            e["target"]
            for node in self.nodes.values()
            for e in node["edges"]
            if e["label"] == "child" and e.get("role") == "variable"
        }
        self.claim_roots = set(self.roots)
        pending = list(self.roots)
        while pending:
            root = pending.pop()
            node = self.nodes[root]
            children = [e for e in node["edges"] if e["label"] == "child"]
            if (
                node["value"]["collection"] == "terms"
                and len(children) == 1
                and children[0].get("role") == "reading"
            ):
                target = children[0]["target"]
                if target not in self.claim_roots:
                    self.claim_roots.add(target)
                    pending.append(target)
        if len(self.nodes) > 20000:
            raise ContractUnavailable("retained task witness population exceeds bounded projection")

    def links(self, key, label):
        return [e for e in self.nodes[key]["edges"] if e["label"] == label]

    def extents(self, key):
        row = self.nodes[key]["value"]
        if row["collection"] == "occurrences":
            values = row["extents"]
        else:
            values = [
                e
                for edge in sorted(
                    self.links(key, "occurrences"), key=lambda e: e.get("position", 0)
                )
                for e in self.nodes[edge["target"]]["value"]["extents"]
            ]
        if not values or any(not all(field in e for field in _EXTENTS) for e in values):
            raise ContractUnavailable(
                "task endpoint lacks authenticated original source coordinates"
            )
        return [{field: e[field] for field in _EXTENTS} for e in values]

    def literal_head(self, key):
        visited = set()
        while key not in visited:
            visited.add(key)
            row = self.nodes[key]["value"]
            if row["collection"] != "terms" or row.get("kind") != "participant":
                return key
            children = self.links(key, "child")
            heads = [e for e in children if e.get("role") == "head"]
            if not heads:
                heads = [e for e in children if e.get("role") == "source"]
            if len(heads) != 1:
                return key
            key = heads[0]["target"]
        raise ContractUnavailable("cyclic literal head/source wrapper")

    def formal_precision(self, key):
        """Honor retained correspondence precision, not just coordinate presence."""
        from corpus_structure.semantic.formal_sources import mapped_formal_extents

        if key in self._formal_precision_checked:
            return
        pending, visited = [key], set()
        while pending:
            current = pending.pop()
            if current in visited:
                continue
            visited.add(current)
            node = self.nodes[current]
            detail = node["value"].get("formal")
            if detail is not None:
                for edge in self.links(current, "formal.input_id"):
                    input_key = edge["target"]
                    input_node = self.nodes[input_key]
                    formal_input = input_node["value"].get("formal_input")
                    if formal_input is None:
                        raise ContractUnavailable(
                            "formal constituent lacks retained input correspondence"
                        )
                    formal_input = dict(formal_input)
                    correspondence = [
                        dict(row, source_occurrences=[]) for row in formal_input["correspondence"]
                    ]
                    for origin in self.links(
                        input_key, "formal_input.correspondence.source_occurrences"
                    ):
                        correspondence[origin["correspondence"]]["source_occurrences"].append(
                            origin["target"]
                        )
                    formal_input["correspondence"] = correspondence
                    occurrences = {
                        origin["target"]: self.nodes[origin["target"]]["value"]
                        for origin in self.links(
                            input_key, "formal_input.correspondence.source_occurrences"
                        )
                    }
                    try:
                        mapped = mapped_formal_extents(
                            formal_input, detail["start"], detail["end"], occurrences
                        )
                    except (ValueError, KeyError, TypeError) as error:
                        raise ContractUnavailable(
                            "formal constituent has no exact original-source correspondence: "
                            + str(error)
                        ) from error
                    mapped_coordinates = [
                        {field: extent[field] for field in _EXTENTS} for extent in mapped
                    ]
                    if mapped_coordinates != self.extents(key):
                        raise ContractUnavailable(
                            "formal term coordinates differ from its exact retained correspondence"
                        )
            pending.extend(
                edge["target"]
                for edge in node["edges"]
                if edge["label"] in {"premises", "external_premises"}
            )
        self._formal_precision_checked.add(key)

    def formal_entity(self, key):
        self.formal_precision(key)
        visited = set()
        while True:
            if key in visited:
                raise ContractUnavailable("cyclic formal identity/content wrapper")
            visited.add(key)
            row = self.nodes[key]["value"]
            if row["collection"] != "terms" or row.get("family") != "formal.math":
                raise ContractUnavailable("formal endpoint lacks a declared mathematical term")
            value = row.get("value", "")
            content = [e for e in self.links(key, "child") if e.get("role") == "content"]
            preserve_group = any(e.value == "group" for e in self.reference.entities)
            if value == "identity" or (value == "group" and not preserve_group):
                if len(content) != 1:
                    raise ContractUnavailable("formal wrapper lacks unique explicit content")
                key = content[0]["target"]
                continue
            break
        if (
            value.startswith("uninterpreted:")
            or value == "@sequence"
            or row.get("kind") == "unknown"
        ):
            raise ContractUnavailable("formal production has no declared semantic association")
        operators = {
            "group",
            "positive",
            "negate",
            "add",
            "subtract",
            "multiply",
            "divide",
            "power",
            "equals",
            "not_equals",
            "less_than",
            "less_or_equal",
            "greater_than",
            "greater_or_equal",
            "membership",
            "application",
            "interval",
            "set_union",
            "set_intersection",
            "set_minus",
            "set_product",
            "set_written_product",
            "tuple",
            "list_of_expressions",
            "set_list",
            "empty_set",
        }
        if row.get("kind") in {"operator", "predicate"} and value not in operators:
            raise ContractUnavailable("formal operator is outside the declared semantic vocabulary")
        if row.get("kind") == "participant" and value.startswith("symbol:"):
            value = value.removeprefix("symbol:")
        identity = key + "#formal"
        self.entities[identity] = dict(
            id=identity,
            kind="formal",
            extents=self.extents(key),
            value=value,
            witness=self.nodes[key]["qualified_identity"],
            standing=row.get("status"),
        )
        return identity

    def entity(self, key, *, variable=False, source=False):
        variable = variable or key in self.variable_sites
        if key in self._normalizing:
            raise ContractUnavailable("cyclic task wrapper normalization")
        self._normalizing.add(key)
        try:
            row = self.nodes[key]["value"]
            collection, kind = row["collection"], row.get("kind")
            if (
                source
                and self.reference.task in {"host_choice", "referent_choice"}
                and collection in {"terms", "annotations"}
            ):
                identity = key + "#source"
                self.entities[identity] = dict(
                    id=identity,
                    kind="source",
                    extents=self.extents(key),
                    value=None,
                    witness=self.nodes[key]["qualified_identity"],
                )
                return identity
            if collection == "annotations" and kind in {
                "context.symbolic_site",
                "context.evidence_site",
            }:
                endpoints = self.links(key, "external_premises")
                if len(endpoints) != 1:
                    raise ContractUnavailable(
                        "context proxy does not declare exactly one source endpoint"
                    )
                return self.entity(endpoints[0]["target"], variable=variable, source=source)
            children = self.links(key, "child")
            if source and collection == "annotations":
                identity = key + "#source"
                self.entities[identity] = dict(
                    id=identity,
                    kind="source",
                    extents=self.extents(key),
                    value=None,
                    witness=self.nodes[key]["qualified_identity"],
                )
                return identity
            if collection == "terms":
                readings = [e for e in children if e.get("role") == "reading"]
                if len(children) == len(readings) == 1:
                    return self.entity(readings[0]["target"], variable=variable, source=source)
                if kind not in _KINDS:
                    raise ContractUnavailable("retained term has no declared task-kind projection")
                anchor_key = key
                anchor_role = (
                    "predicate"
                    if kind == "predicate"
                    else "cue"
                    if kind in {"operator", "binder"}
                    else "head"
                    if kind == "participant"
                    else None
                )
                if (
                    kind == "operator"
                    and not any(e.get("role") == "cue" for e in children)
                    and any(e.get("role") == "connective" for e in children)
                ):
                    anchor_role = "connective"
                if (
                    kind == "participant"
                    and not any(e.get("role") == "head" for e in children)
                    and any(e.get("role") == "source" for e in children)
                ):
                    anchor_role = "source"
                anchors = [e for e in children if e.get("role") == anchor_role]
                if (
                    len(anchors) == 1
                    and self.nodes[anchors[0]["target"]]["value"]["collection"] == "terms"
                ):
                    anchor_key = anchors[0]["target"]
                anchor_key = self.literal_head(anchor_key)
                # Only declared wrappers share the lexical endpoint identity; binders
                # and operators keep their distinct qualified retained identities.
                identity = anchor_key if kind in {"predicate", "participant"} else key
                task_kind = "source" if source else "variable" if variable else kind
                identity += "#" + task_kind
                value = None
                if kind in {"operator", "binder"}:
                    literal = row.get("value", "")
                    if literal == "negation" or literal.startswith(
                        ("modality:", "relative_scope:")
                    ):
                        value = literal
                extents = self.extents(anchor_key)
                implicit = (
                    variable
                    and row.get("status") == "implicit"
                    and all(e["start"] == e["end"] for e in extents)
                )
                if any(e["start"] == e["end"] for e in extents) and not implicit:
                    raise ContractUnavailable(
                        "zero-width endpoint lacks an explicitly retained implicit variable site"
                    )
                entity = dict(
                    id=identity,
                    kind=task_kind,
                    extents=extents,
                    value=None if source else value,
                    support="implicit_site" if implicit else "literal",
                    witness=self.nodes[key]["qualified_identity"],
                    standing=row.get("status"),
                )
            else:
                raise ContractUnavailable("retained endpoint is not a declared source term/proxy")
            self.entities[identity] = entity
            return identity
        finally:
            self._normalizing.remove(key)

    def requirements(self, key):
        return [
            e["target"]
            for e in self.nodes[key]["edges"]
            if e["label"]
            in {
                "required_choices",
                "required_external_choices",
                "basis.choice_refs",
                "basis.required_external_choices",
            }
        ]

    def build(self):
        ref = self.reference
        if ref.task in {"host_choice", "referent_choice"}:
            self._candidate_questions()
            if ref.groups or any(a["requires"] for a in self.assertions):
                self._choices()
            return self
        if ref.task == "formal":
            if self.family != "formal.math" or ref.role_scheme != "formal-children-v1":
                raise ContractUnavailable(
                    "formal-child task requires the retained formal.math family"
                )
            for key, node in self.nodes.items():
                row = node["value"]
                if (
                    row["collection"] != "terms"
                    or row.get("family") != self.family
                    or (self.output_first and key not in self.claim_roots)
                ):
                    continue
                self.formal_precision(key)
                # Syntax wrappers are declared erasures, not additional assertions.
                if row.get("value") in {"formal-reading", "identity"} or (
                    row.get("value") == "group"
                    and not any(e.value == "group" for e in ref.entities)
                ):
                    continue
                anchors = self.extents(key) if self.links(key, "occurrences") else []
                if not any(
                    anchors == [e.model_dump(mode="json") for e in entity.extents]
                    for entity in ref.entities
                ):
                    continue
                subject = self.formal_entity(key)
                for edge in self.links(key, "child"):
                    if edge.get("role") not in TASK_ROLES["formal"]:
                        raise ContractUnavailable("formal child role has no declared task meaning")
                    self.assertions.append(
                        dict(
                            subject=subject,
                            relation=edge["role"],
                            object=self.formal_entity(edge["target"]),
                            requires=self.requirements(key),
                            order=edge.get("order"),
                            standing=row.get("status"),
                            witness=node["qualified_identity"],
                        )
                    )
            if ref.groups or any(a["requires"] for a in self.assertions):
                self._choices()
            return self
        if ref.task == "modal_force":
            if (
                self.family != "character_modal_force_v1"
                or ref.role_scheme != "construction-children-v1"
            ):
                raise ContractUnavailable(
                    "modal force requires the declared character_modal_force_v1 question adapter"
                )
            self._modal_questions()
            return self
        if ref.role_scheme == "construction-children-v1":
            if self.family not in _CONSTRUCTION_FAMILIES:
                raise ContractUnavailable(
                    "family has no declared construction-child task projection"
                )
            for key, node in self.nodes.items():
                row = node["value"]
                if (
                    row["collection"] != "terms"
                    or row.get("family") != self.family
                    or (self.output_first and key not in self.claim_roots)
                ):
                    continue
                if row.get("kind") not in _KINDS:
                    raise ContractUnavailable("retained term has an undefined task representation")
                if not self.links(key, "occurrences") and row.get("status") in {
                    "unknown",
                    "implicit",
                }:
                    raise ContractUnavailable(
                        "unlocated implicit/unknown family endpoint cannot establish slot absence"
                    )
                edges = [
                    e for e in self.links(key, "child") if e.get("role") in TASK_ROLES[ref.task]
                ]
                if edges or self.links(key, "occurrences"):
                    self.entity(key)
                for edge in edges:
                    if edge.get("role") not in TASK_ROLES[ref.task]:
                        continue
                    if self.nodes[edge["target"]]["value"]["collection"] == "choices":
                        raise ContractUnavailable(
                            "packed child slot requires an explicit choice-endpoint task adapter"
                        )
                    subject = self.entity(key)
                    target = self.entity(
                        edge["target"],
                        variable=edge.get("role") == "variable",
                        source=edge.get("role")
                        in {
                            "cue",
                            "connective",
                            "quantifier_cue",
                            "negative_cue",
                            "auxiliary",
                            "aspect",
                            "agent_cue",
                            "attachment_cue",
                        },
                    )
                    self.assertions.append(
                        dict(
                            subject=subject,
                            relation=edge["role"],
                            object=target,
                            requires=self.requirements(key),
                            order=edge.get("order"),
                            standing=row.get("status"),
                            witness=node["qualified_identity"],
                        )
                    )
        elif self.family == "context.binding" and ref.task == "binding":
            for key, node in self.nodes.items():
                row = node["value"]
                if (
                    row["collection"] != "roles"
                    or row.get("family") != self.family
                    or (self.output_first and key not in self.claim_roots)
                ):
                    continue
                if (
                    row.get("scheme") != ref.role_scheme
                    or row.get("role") != "declared_binding_site"
                ):
                    raise ContractUnavailable(
                        "context binding role has an undeclared scheme/meaning"
                    )
                owners, members = self.links(key, "owner"), self.links(key, "member")
                if len(owners) != 1 or len(members) != 1:
                    raise ContractUnavailable("context role lacks exact directed endpoints")
                self.assertions.append(
                    dict(
                        subject=self.entity(owners[0]["target"]),
                        relation=row["role"],
                        object=self.entity(members[0]["target"], variable=True),
                        requires=self.requirements(key),
                        order=None,
                        standing=row.get("basis", {}).get("status"),
                        witness=node["qualified_identity"],
                    )
                )
        else:
            raise ContractUnavailable("task/family/scheme combination has no declared adapter")
        if ref.groups or ref.task == "choices" or any(a["requires"] for a in self.assertions):
            self._choices()
        return self

    def _candidate_questions(self):
        """Read the frozen question population, never infer language or candidate identity."""
        task = self.reference.task
        family, question, role = (
            ("character_host_choice_v1", "host", "host")
            if task == "host_choice"
            else ("character_referent_choice_v1", "referent", "referent")
        )
        if self.family != family:
            raise ContractUnavailable("candidate question family differs from declared task")
        index = {
            (
                canonical_bytes(n["qualified_identity"]["layer"]),
                n["qualified_identity"]["local_id"],
            ): k
            for k, n in self.nodes.items()
        }

        def resolve(reference):
            try:
                return index[(canonical_bytes(reference["layer"]), reference["local_id"])]
            except (KeyError, TypeError) as error:
                raise ContractUnavailable(
                    "frozen candidate lacks its exact retained endpoint"
                ) from error

        def endpoint(description):
            key = resolve(description["reference"])
            expected = [
                {field: extent[field] for field in _EXTENTS}
                for extent in description["source_members"]
            ]
            if self.extents(key) != expected:
                raise ContractUnavailable("frozen candidate source differs from retained endpoint")
            identity = key + "#source"
            self.entities[identity] = dict(
                id=identity,
                kind="source",
                extents=expected,
                value=None,
                witness=self.nodes[key]["qualified_identity"],
            )
            return identity

        def required(*descriptions):
            return sorted(
                {
                    resolve(choice)
                    for d in descriptions
                    for choice in d.get("required_external_choices", ())
                }
            )

        for key, node in self.nodes.items():
            row = node["value"]
            answer = row.get("model_answer", {})
            if (
                row["collection"] != "annotations"
                or row.get("family") != family
                or answer.get("question_key") != question
                or (self.output_first and key not in self.claim_roots)
            ):
                continue
            if not self.output_first:
                expected_focus = next(
                    entity
                    for entity in self.reference.entities
                    if entity.id == self.reference.focus
                )
                # A missing request is an unavailable result only where its recorded
                # question scope intersects the independently inspected focal source.
                # Other scopes cannot poison this source-first question's population.
                if not any(
                    all(actual[field] == getattr(expected, field) for field in _EXTENTS[:3])
                    and actual["start"] < expected.end
                    and expected.start < actual["end"]
                    for actual in self.extents(key)
                    for expected in expected_focus.extents
                ):
                    continue
            if answer.get("family") != family or answer.get("answer_kind") != "choice":
                raise ContractUnavailable("candidate question is not the declared typed choice")
            try:
                native = source_python(answer["native_answer"])
                frozen = native["request"]["interpretation"]["frozen_candidates"]
                focus = frozen["focus"]
                alternatives = {a["key"]: a for a in frozen["alternatives"]}
                if len(alternatives) != len(frozen["alternatives"]):
                    raise ContractUnavailable("frozen candidate keys are not unique")
                focus_id = endpoint(focus)
                state = answer["state"]
                operator = key + "#" + task
                self.entities[operator] = dict(
                    id=operator,
                    kind="operator",
                    extents=self.entities[focus_id]["extents"],
                    value=task + ":" + state,
                    witness=node["qualified_identity"],
                )
                self.assertions.append(
                    dict(
                        subject=operator,
                        relation="focus",
                        object=focus_id,
                        requires=required(focus),
                        order=None,
                        standing="private_proposal",
                        witness=node["qualified_identity"],
                    )
                )
                selected = answer.get("selected_keys", ())
                if state != "proposed":
                    if selected:
                        raise ContractUnavailable(
                            "nonpositive candidate answer selects an endpoint"
                        )
                    continue
                if len(selected) != 1 or selected[0] not in alternatives:
                    raise ContractUnavailable(
                        "selected candidate was not one frozen offered option"
                    )
                offered = alternatives[selected[0]]
                members = offered["members"]
                if not members or (
                    len(members) > 1
                    and (task != "host_choice" or offered.get("compatibility") != "compatible")
                ):
                    raise ContractUnavailable(
                        "multiple endpoints lack explicit compatible host-set meaning"
                    )
                if len({canonical_bytes(m["reference"]) for m in members}) != len(members):
                    raise ContractUnavailable("candidate option repeats an endpoint")
                for member in members:
                    target = endpoint(member)
                    for support in offered.get(
                        "hypothesis_supports", [dict(required_external_choices=[])]
                    ):
                        self.assertions.append(
                            dict(
                                subject=operator,
                                relation=role,
                                object=target,
                                requires=required(focus, member, support),
                                order=None,
                                standing="private_proposal",
                                witness=node["qualified_identity"],
                            )
                        )
            except (KeyError, TypeError, ValueError) as error:
                if isinstance(error, ContractUnavailable):
                    raise
                raise ContractUnavailable(
                    "candidate question lacks its exact frozen source population"
                ) from error

    def _modal_questions(self):
        local_index = {
            (
                canonical_bytes(n["qualified_identity"]["layer"]),
                n["qualified_identity"]["local_id"],
            ): key
            for key, n in self.nodes.items()
        }

        def proposal(question_key):
            offered = []
            for key, node in self.nodes.items():
                row = node["value"]
                if (
                    row["collection"] != "memberships"
                    or row.get("family") != self.family
                    or row.get("role") != "private_proposal"
                ):
                    continue
                if any(e["target"] == question_key for e in self.links(key, "group")):
                    offered.extend(e["target"] for e in self.links(key, "member"))
            if len(offered) != 1:
                raise ContractUnavailable("modal task lacks a unique retained located proposal")
            return offered[0]

        for key, node in self.nodes.items():
            row = node["value"]
            answer = row.get("model_answer", {})
            if (
                row["collection"] != "annotations"
                or row.get("family") != self.family
                or answer.get("question_key") != "modal_force"
                or (self.output_first and key not in self.claim_roots)
            ):
                continue
            if answer.get("family") != self.family or answer.get("answer_kind") != "choice":
                raise ContractUnavailable(
                    "modal task question is not the declared native typed choice"
                )
            if answer.get("state") != "proposed":
                continue
            selected = answer.get("selected_keys", ())
            if len(selected) != 1 or selected[0] not in {
                "epistemic",
                "deontic",
                "dynamic",
                "other",
                "no_modal",
                "insufficient",
            }:
                raise ContractUnavailable("modal question has an undeclared selected option")
            layer = canonical_bytes(node["qualified_identity"]["layer"])
            dependencies = {}
            for dependency in answer.get("depends_on", ()):
                target = local_index.get((layer, dependency))
                if target is None:
                    raise ContractUnavailable(
                        "modal dependency is unavailable in exact family population"
                    )
                prior = self.nodes[target]["value"].get("model_answer", {})
                if prior.get("family") == self.family:
                    dependencies[prior.get("question_key")] = target
            if not {"modal_cue", "modal_target"} <= dependencies.keys():
                raise ContractUnavailable("modal force lacks declared cue/target dependency links")
            if any(
                self.nodes[prior]["value"]["model_answer"].get("state") != "proposed"
                for prior in dependencies.values()
            ):
                continue
            cue, target = (proposal(dependencies[name]) for name in ("modal_cue", "modal_target"))
            operator = key + "#modal_force"
            cue_id, target_id = cue + "#source", target + "#source"
            self.entities[operator] = dict(
                id=operator,
                kind="operator",
                extents=self.extents(cue),
                value="modality:" + selected[0],
                witness=node["qualified_identity"],
            )
            for identity, source in ((cue_id, cue), (target_id, target)):
                self.entities[identity] = dict(
                    id=identity,
                    kind="source",
                    extents=self.extents(source),
                    value=None,
                    witness=self.nodes[source]["qualified_identity"],
                )
            for relation, endpoint in (("cue", cue_id), ("target", target_id)):
                self.assertions.append(
                    dict(
                        subject=operator,
                        relation=relation,
                        object=endpoint,
                        requires=self.requirements(key),
                        order=None,
                        standing="private_proposal",
                        witness=node["qualified_identity"],
                    )
                )

    def _choices(self):
        for key, node in self.nodes.items():
            row = node["value"]
            if row["collection"] != "choices":
                continue
            members = []
            for edge in self.links(key, "alternative"):
                member_id = edge["target"]
                roots = self.links(member_id, "root")
                if len(roots) != 1:
                    raise ContractUnavailable(
                        "choice member lacks an explicit unique semantic root"
                    )
                members.append(
                    dict(
                        id=member_id,
                        root=self.formal_entity(roots[0]["target"])
                        if self.reference.task == "formal"
                        else self.entity(
                            roots[0]["target"],
                            source=self.reference.task in {"host_choice", "referent_choice"},
                        ),
                        requires=self.requirements(member_id),
                    )
                )
            self.groups.append(
                dict(
                    id=key,
                    compatibility=row["compatibility"],
                    members=members,
                    witness=node["qualified_identity"],
                )
            )


def _task_graph(entities, assertions, groups, focus, *, expected=False):
    from networkx import MultiDiGraph

    graph = MultiDiGraph()
    for entity in entities:
        graph.add_node(
            ("entity", entity["id"]),
            meaning=_entity_meaning(
                entity, compare_value=not expected or entity.get("value") is not None
            ),
            focus=entity["id"] == focus,
        )
    for position, assertion in enumerate(assertions):
        key = ("assertion", position)
        meaning = dict(relation=assertion["relation"])
        if not expected or assertion.get("order") is not None:
            meaning["order"] = assertion.get("order")
        if not expected or assertion.get("standing") is not None:
            meaning["standing"] = assertion.get("standing")
        graph.add_node(key, meaning=meaning, focus=False)
        graph.add_edge(key, ("entity", assertion["subject"]), label="subject")
        graph.add_edge(key, ("entity", assertion["object"]), label="object")
        for required in set(assertion.get("requires", ())):
            graph.add_edge(key, ("member", required), label="requires")
    for group in groups:
        key = ("group", group["id"])
        graph.add_node(key, meaning=dict(compatibility=group["compatibility"]), focus=False)
        for member in group["members"]:
            target = ("member", member["id"])
            graph.add_node(target, meaning=dict(choice_member=True), focus=False)
            graph.add_edge(key, target, label="member")
            graph.add_edge(target, ("entity", member["root"]), label="root")
            for required in set(member.get("requires", ())):
                graph.add_edge(target, ("member", required), label="requires")
    return graph


def score_task(reference, family, predictions, *, output_first=False):
    """Project a complete relevant family population into the declared task boundary."""
    from networkx.algorithms.isomorphism import MultiDiGraphMatcher

    ref = (
        reference
        if isinstance(reference, SemanticTaskReference)
        else SemanticTaskReference.model_validate_json(canonical_bytes(reference))
    )
    expected = ref.model_dump(mode="json")
    result: dict[str, Any] = dict(
        version=VERSION,
        task=ref.task,
        role_scheme=ref.role_scheme,
        mode=ref.mode,
        status="unavailable",
        exact_match=None,
        differences=[],
        witnesses=[],
        match_scope=dict(
            grain="declared_task_assertions",
            mode=ref.mode,
            interpretation="positive_existence_under_explicit_feasible_support"
            if ref.mode == "witness"
            else "complete_named_slots_and_declared_choice_constraints",
            unconditionality="not_asserted"
            if ref.mode == "witness"
            else "declared_assertion_conditions",
            linguistic_generality="not_established",
        ),
    )
    try:
        population = TaskPopulation(predictions, ref, family, output_first=output_first)
        result["witnesses"] = [
            population.nodes[key]["qualified_identity"] for key in population.roots
        ]
        population.build()
        assessed_choice_groups = set()
        expected_focus_groups = set()
        if output_first and ref.task == "choices":
            assessed_choice_groups = {
                key
                for key in population.roots
                if population.nodes[key]["value"]["collection"] == "choices"
            }
            expected_focus_groups = {
                group.id
                for group in ref.groups
                if any(member.root == ref.focus for member in group.members)
            }
            if not assessed_choice_groups or not expected_focus_groups:
                raise ContractUnavailable(
                    "output-first choice task requires a frozen assessed choice group "
                    "and a declared focus-group"
                )
            result["match_scope"]["assessed_choice_groups"] = [
                population.nodes[key]["qualified_identity"]
                for key in sorted(assessed_choice_groups)
            ]
        entities = list(population.entities.values())
        focus = next(e for e in expected["entities"] if e["id"] == ref.focus)
        compare_value = any(e.value is not None for e in ref.entities)
        matches = [e for e in entities if _entity_compatible(e, focus)]
        # An empty known adapter is a genuine missing assertion, unlike an unknown
        # adapter. Keep a typed missing focus in the diff rather than guessing one.
        if not matches:
            return dict(
                result,
                status="scored",
                exact_match=False,
                differences=[dict(kind="missing_focus", expected=focus, actual_entities=entities)],
            )
        expected_graph = _task_graph(
            expected["entities"],
            expected["assertions"],
            expected["groups"],
            ref.focus,
            expected=True,
        )
        picked = population.assertions
        if ref.mode == "complete_slots":
            expected_entities = {entity["id"]: entity for entity in expected["entities"]}
            picked = [
                assertion
                for assertion in picked
                if any(
                    assertion["relation"] == slot.relation
                    and _entity_compatible(
                        population.entities[assertion["subject"]], expected_entities[slot.subject]
                    )
                    for slot in ref.complete_slots
                )
            ]
        used = {a[field] for a in picked for field in ("subject", "object")}
        # Only the named source slots/choice roots and their directed prerequisite
        # closure belong to this question. Other page-local alternatives are not votes.
        expected_anchors = {canonical_bytes(_entity_meaning(e)) for e in expected["entities"]}
        member_groups = {m["id"]: g["id"] for g in population.groups for m in g["members"]}
        required_members = {
            member for assertion in picked for member in assertion.get("requires", ())
        }
        selected_groups = {
            g["id"]
            for g in population.groups
            if any(
                canonical_bytes(_entity_meaning(population.entities[m["root"]])) in expected_anchors
                for m in g["members"]
            )
        }
        selected_groups.update(member_groups[m] for m in required_members if m in member_groups)
        while True:
            prerequisites = {
                member
                for group in population.groups
                if group["id"] in selected_groups
                for m in group["members"]
                for member in m.get("requires", ())
            }
            expanded = selected_groups | {
                member_groups[m] for m in prerequisites if m in member_groups
            }
            if expanded == selected_groups:
                break
            selected_groups = expanded
        groups = [g for g in population.groups if g["id"] in selected_groups]
        used.update(m["root"] for g in groups for m in g["members"])
        known_members = {m["id"] for g in groups for m in g["members"]}
        if ref.mode != "witness" and (
            not required_members <= known_members
            or any(
                not set(m.get("requires", ())) <= known_members
                for g in groups
                for m in g["members"]
            )
        ):
            raise ContractUnavailable(
                "task choice prerequisite lacks its exact retained group closure"
            )
        result["witnesses"] = [a["witness"] for a in picked] + [g["witness"] for g in groups]
        if len(used) > 128 or len(picked) > 256 or len(groups) > 32:
            raise ContractUnavailable("projected task population exceeds declared reference bounds")
        support_failures = []
        claim_root_mismatch = False
        for actual_focus in matches:
            selected_entities = [
                e for e in entities if e["id"] in used or e["id"] == actual_focus["id"]
            ]
            actual_graph = _task_graph(
                selected_entities,
                picked,
                groups,
                actual_focus["id"],
            )
            matcher = MultiDiGraphMatcher(
                actual_graph,
                expected_graph,
                node_match=lambda a, b: (
                    a.get("focus") == b.get("focus")
                    and all(
                        key in a.get("meaning", {}) and a["meaning"][key] == value
                        for key, value in b.get("meaning", {}).items()
                    )
                ),
                edge_match=lambda a, b: (
                    Counter(e["label"] for e in a.values())
                    == Counter(e["label"] for e in b.values())
                ),
            )
            mappings = (
                matcher.isomorphisms_iter()
                if ref.mode == "complete_slots"
                else matcher.subgraph_monomorphisms_iter()
            )
            for mapping in mappings:
                if assessed_choice_groups:
                    matched_focus_groups = {
                        actual_id[1]
                        for actual_id, expected_id in mapping.items()
                        if expected_id[0] == "group" and expected_id[1] in expected_focus_groups
                    }
                    if not assessed_choice_groups <= matched_focus_groups:
                        claim_root_mismatch = True
                        continue
                member_map = {
                    expected_id[1]: actual_id[1]
                    for actual_id, expected_id in mapping.items()
                    if expected_id[0] == "member"
                }
                differences = []
                for query in ref.joint_queries:
                    outcome = joint_outcome(groups, [member_map[m] for m in query.members])
                    if outcome != query.expected:
                        differences.append(
                            dict(
                                kind="joint_choice",
                                members=list(query.members),
                                expected=query.expected,
                                actual=outcome,
                            )
                        )
                support = None
                matched_assertions = []
                if not differences and ref.mode == "witness":
                    matched_assertions = [
                        picked[actual_id[1]]
                        for actual_id, expected_id in mapping.items()
                        if expected_id[0] == "assertion"
                    ]
                    support = witness_support(
                        groups,
                        [
                            member
                            for assertion in matched_assertions
                            for member in assertion.get("requires", ())
                        ],
                    )
                    if support["status"] != "feasible":
                        support_failures.append(
                            dict(
                                kind="witness_support",
                                **support,
                                assertions=[a["witness"] for a in matched_assertions],
                            )
                        )
                        continue
                if not differences:
                    return dict(
                        result,
                        status="scored",
                        exact_match=True,
                        differences=[],
                        support_conditions=dict(
                            support, assertion_witnesses=[a["witness"] for a in matched_assertions]
                        )
                        if support is not None
                        else None,
                    )
        if claim_root_mismatch and not support_failures:
            return dict(
                result,
                status="scored",
                exact_match=False,
                differences=[
                    dict(
                        kind="frozen_choice_group_not_matched",
                        assessed_groups=result["match_scope"]["assessed_choice_groups"],
                        expected_focus_groups=sorted(expected_focus_groups),
                    )
                ],
            )
        if support_failures:
            unknown = any(support["status"] == "unknown" for support in support_failures)
            return dict(
                result,
                status="unavailable" if unknown else "scored",
                exact_match=None if unknown else False,
                reason="witness_support_unknown" if unknown else "witness_support_impossible",
                differences=support_failures,
            )
        actual_claims = [
            dict(
                a,
                subject_anchor=_entity_meaning(
                    population.entities[a["subject"]], compare_value=compare_value
                ),
                object_anchor=_entity_meaning(
                    population.entities[a["object"]], compare_value=compare_value
                ),
            )
            for a in picked
        ]
        return dict(
            result,
            status="scored",
            exact_match=False,
            differences=[
                dict(
                    kind="task_structure_mismatch",
                    expected_assertions=expected["assertions"],
                    expected_groups=expected["groups"],
                    actual_assertions=actual_claims,
                    actual_groups=groups,
                )
            ],
        )
    except (ContractUnavailable, KeyError) as error:
        return dict(
            result,
            reason=str(error),
            differences=[dict(kind="assessment_contract_unavailable", reason=str(error))],
        )
