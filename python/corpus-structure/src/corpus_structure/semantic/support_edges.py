"""Declared native support edges shared by validity and disclosure traversal."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import cast as typing_cast

from jsonasobj2 import as_dict
from sqlalchemy import (
    Integer,
    Text,
    and_,
    case,
    cast,
    column,
    func,
    literal,
    or_,
    select,
    true,
    union_all,
)
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.model.compiled import compiled_model, running_model

from .native_program import core_reference


@dataclass(frozen=True)
class SupportEdge:
    name: str
    source: str
    target: str
    relation: str
    group: str
    profiles: tuple[str, ...]


def declared_support_edges(model=None):
    compiled = (
        running_model()
        if model is None
        else compiled_model(
            {
                **model.info["physical_sources"],
                "linkml:types": model.info["physical_linkml_types"],
            }
        )
    )
    enum = compiled.view("operation-vocabularies.yaml").get_enum("SupportEdgeKind")
    if enum is None:
        raise ValueError("missing support edge declarations")
    edges = []
    for name, member in typing_cast(dict[str, Any], enum.permissible_values).items():
        annotation = member.annotations.get("cs:edge")
        values: Any = as_dict(annotation.value) if annotation is not None else None
        if not isinstance(values, dict) or set(values) != {
            "source",
            "target",
            "relation",
            "group",
            "profiles",
        }:
            raise ValueError("support edge lacks its declared traversal: " + name)
        if not values["profiles"] or set(values["profiles"]) - {
            "validity",
            "scope",
            "public",
            "lineage",
        }:
            raise ValueError("support edge has invalid traversal profiles: " + name)
        edges.append(
            SupportEdge(
                name,
                values["source"],
                values["target"],
                values["relation"],
                values["group"],
                tuple(values["profiles"]),
            )
        )
    return tuple(edges)


def declared_support_references(model=None):
    compiled = (
        running_model()
        if model is None
        else compiled_model(
            {
                **model.info["physical_sources"],
                "linkml:types": model.info["physical_linkml_types"],
            }
        )
    )
    enum = compiled.view("operation-vocabularies.yaml").get_enum("SupportReferenceKind")
    if enum is None:
        raise ValueError("missing native support reference kinds")
    rules = []
    for name, member in typing_cast(dict[str, Any], enum.permissible_values).items():
        annotation = member.annotations.get("cs:reference")
        value: Any = as_dict(annotation.value) if annotation is not None else None
        if (
            not isinstance(value, dict)
            or not {"order", "field", "identity"} <= value.keys()
            or value.keys() - {"order", "field", "identity", "values"}
        ):
            raise ValueError("native support reference lacks its declared mapping: " + name)
        rules.append((value["order"], name, value["field"], value.get("values"), value["identity"]))
    if len({rule[0] for rule in rules}) != len(rules):
        raise ValueError("native support reference repeats its selection order")
    return tuple(sorted(rules))


def reference_node(reference):
    """Read the same declared reference mapping used by native traversal."""
    if isinstance(reference, dict):
        for _, kind, field, values, identity_field in declared_support_references():
            selected = (
                reference.get(field) in values
                if values is not None
                else reference.get(field) is not None
            )
            if selected:
                identity = reference.get(identity_field)
                if isinstance(identity, str) and identity:
                    return kind, identity
                break
    raise ValueError("unrecognized native support reference")


def support_reference_node(reference):
    """The installed classifier refuses references outside the declared native shapes."""
    node = func.ops.ddo_support_reference_node(reference, type_=JSONB())
    return node["kind"].astext, node["id"].astext


def support_edge_queries(
    model,
    kind,
    identity,
    profile,
    *,
    authority=None,
    boundary=None,
    product_ids=None,
    selected_support=False,
):
    uses = model.tables["ops.demand_use"]
    populations = model.tables["ops.data_population"]
    episodes = model.tables["ops.data_derivation"]
    support = model.tables["ops.data_derivation_support"]
    originals = model.tables["ops.data_derivation_original_support"]
    definitions = model.tables["sem.data_operation_definition"]
    demands = model.tables["ops.data_demand"]
    empty_json = cast(literal("[]"), JSONB())

    def items(value, name):
        return (
            func.jsonb_array_elements(func.coalesce(value, empty_json))
            .table_valued(column("value", JSONB()))
            .render_derived(name=name)
        )

    selected = items(uses.c.selection["support"], "selected_support_reference")
    selected_populations = items(uses.c.selection["populations"], "selected_population_reference")
    reference_kind, reference_id = support_reference_node(selected.c.value)

    def episode_kind(value):
        return (
            case((authority(value), "authority"), else_="episode")
            if authority
            else literal("episode")
        )

    visible = ~authority(uses.c.derivation_id) if authority else true()
    if authority:
        reference_kind = case(
            (and_(reference_kind == "episode", authority(reference_id)), "authority"),
            else_=reference_kind,
        )

    substitute = (
        select(1)
        .select_from(
            episodes.join(
                definitions,
                and_(
                    definitions.c.release_id == episodes.c.release_id,
                    definitions.c.recipe == episodes.c.recipe,
                ),
            ).join(demands, demands.c.id == uses.c.demand_id)
        )
        .where(
            episodes.c.id == uses.c.derivation_id,
            definitions.c.support_contract["provenance"].astext == "value_substitution",
            demands.c.strength == "value",
        )
        .correlate(uses)
        .exists()
    )
    # A value use relies on its authenticated selection. The producing episode
    # retains historical support but cannot rehabilitate the current selection.
    choice = (
        case((substitute, 2), else_=1) if profile == "validity" or selected_support else literal(0)
    )
    null_text = cast(literal(None), Text())

    def edge(alternative, target, child):
        return select(
            cast(alternative, Integer()).label("alternative"),
            cast(literal(target) if isinstance(target, str) else target, Text()).label(
                "child_kind"
            ),
            child.label("child_id"),
        )

    authority_report = cast(
        func.ops.ddo_structural_report_support(uses.c.id, boundary, product_ids), JSONB()
    )
    builders = {
        "public-authority-report": edge(literal(0), "use", authority_report["use_id"].astext).where(
            kind == "use",
            uses.c.id == identity,
            authority(uses.c.derivation_id) if authority else literal(False),
        ),
        "terminal": edge(literal(0), null_text, null_text).where(
            kind.not_in(("episode", "use", "population"))
        ),
        "episode-producer": edge(literal(0), "producer", identity).where(kind == "episode"),
        "episode-support": edge(
            literal(0),
            case(
                (support.c.admission_use_id.is_not(None), "use"),
                else_=episode_kind(support.c.support_derivation_id),
            ),
            func.coalesce(support.c.admission_use_id, support.c.support_derivation_id),
        ).where(kind == "episode", support.c.derivation_id == identity),
        "episode-original": edge(literal(0), "original", originals.c.admission_id).where(
            kind == "episode", originals.c.derivation_id == identity
        ),
        "use-choice": edge(choice, null_text, null_text)
        .select_from(uses)
        .where(kind == "use", uses.c.id == identity),
        "use-producer": edge(choice, "producer", uses.c.derivation_id)
        .select_from(uses)
        .where(kind == "use", uses.c.id == identity),
        "use-episode": edge(choice, episode_kind(uses.c.derivation_id), uses.c.derivation_id)
        .select_from(uses)
        .where(
            kind == "use", uses.c.id == identity, choice == 1 if profile == "validity" else true()
        ),
        "use-selected-support": edge(choice, reference_kind, reference_id)
        .select_from(uses.join(selected, true()))
        .where(
            kind == "use",
            uses.c.id == identity,
            visible,
            choice == 2 if profile == "validity" else true(),
        ),
        "use-population": edge(choice, "population", populations.c.id)
        .select_from(
            uses.join(selected_populations, true()).join(
                populations,
                and_(
                    populations.c.id == selected_populations.c.value["population_id"].astext,
                    populations.c.demand_id == uses.c.demand_id,
                ),
            )
        )
        .where(kind == "use", uses.c.id == identity, visible),
        "population-use": edge(literal(0), "use", uses.c.id)
        .select_from(
            populations.join(
                uses,
                and_(
                    uses.c.id == populations.c.evidence["admission_use_id"].astext,
                    uses.c.derivation_id == populations.c.evidence["derivation_id"].astext,
                    uses.c.demand_id == populations.c.demand_id,
                ),
            )
        )
        .where(kind == "population", populations.c.id == identity),
        "population-parent": edge(
            literal(0),
            "population",
            populations.c.evidence["selection"]["parent_population_id"].astext,
        ).where(kind == "population", populations.c.id == identity),
        "historical-support": edge(literal(0), "episode", support.c.support_derivation_id).where(
            kind == "episode", support.c.derivation_id == identity
        ),
    }
    expected = {
        "public-authority-report": ("use", "use", "ops.demand_use", "conjunctive"),
        "terminal": ("terminal", "choice", "native-terminal", "conjunctive"),
        "episode-producer": ("episode", "producer", "ops.data_derivation", "conjunctive"),
        "episode-support": ("episode", "reference", "ops.data_derivation_support", "conjunctive"),
        "episode-original": (
            "episode",
            "original",
            "ops.data_derivation_original_support",
            "conjunctive",
        ),
        "use-choice": ("use", "choice", "ops.demand_use", "alternative"),
        "use-producer": ("use", "producer", "ops.demand_use", "alternative"),
        "use-episode": ("use", "episode", "ops.demand_use", "alternative"),
        "use-selected-support": ("use", "reference", "ops.demand_use", "alternative"),
        "use-population": ("use", "population", "ops.demand_use", "alternative"),
        "population-use": ("population", "use", "ops.data_population", "conjunctive"),
        "population-parent": ("population", "population", "ops.data_population", "conjunctive"),
        "historical-support": ("episode", "episode", "ops.data_derivation_support", "conjunctive"),
    }
    declared = declared_support_edges(model)
    if {entry.name for entry in declared} != builders.keys():
        raise ValueError("support edge declarations differ from native relation bindings")
    queries = []
    for entry in declared:
        if (entry.source, entry.target, entry.relation, entry.group) != expected[entry.name]:
            raise ValueError("support edge binding differs from declaration: " + entry.name)
        if profile in entry.profiles:
            queries.append(builders[entry.name])
    return tuple(queries)


def support_explanation_rows(model, seeds, boundary, disclosed):
    """Attribute native closure judgments to their exact selected root use."""
    from sqlalchemy import BigInteger, Boolean, exists
    from sqlalchemy.dialects.postgresql import array

    uses = model.tables["ops.demand_use"].alias("explained_root_use")
    episodes = model.tables["ops.data_derivation"].alias("explained_episode")
    requests = model.tables["ops.data_request"].alias("explained_request")
    admissions = model.tables["ops.original_source_admission"].alias("explained_original")
    revoked = model.tables["ops.data_revocation"].alias("explained_revocation")
    outputs = model.tables["ops.data_derivation_output"].alias("explained_output")
    empty = array([], type_=Text())
    reached = select(
        seeds.c.id.label("root_use_id"), literal("use").label("kind"), seeds.c.id.label("id")
    ).cte("explained_selected_nodes", recursive=True)
    selected_edges = union_all(
        *(
            query.correlate(reached)
            for query in support_edge_queries(
                model, reached.c.kind, reached.c.id, "validity", selected_support=True
            )
        )
    ).lateral("explained_selected_edge")
    reached = reached.union(
        select(reached.c.root_use_id, selected_edges.c.child_kind, selected_edges.c.child_id)
        .select_from(reached.join(selected_edges, true()))
        .where(selected_edges.c.child_id.is_not(None))
    )
    root_validity = (
        func.ops.ddo_valid_closure(array([seeds.c.id]), empty, boundary, empty)
        .table_valued(column("kind", Text()), column("id", Text()), column("valid", Boolean()))
        .lateral("explained_validity")
    )
    closure = (
        select(root_validity.c.kind, root_validity.c.id, root_validity.c.valid)
        .select_from(root_validity)
        .where(
            exists(
                select(1)
                .select_from(reached)
                .where(
                    reached.c.root_use_id == seeds.c.id,
                    reached.c.kind == root_validity.c.kind,
                    reached.c.id == root_validity.c.id,
                )
            )
        )
        .lateral("explained_reached")
    )
    episode_node = closure.c.kind.in_(("episode", "producer"))
    original_node = closure.c.kind == "original"
    original_match = and_(
        original_node,
        revoked.c.scope
        == case(
            (
                admissions.c.project_id.is_not(None),
                func.ops.ddo_scope(admissions.c.project_id, admissions.c.original_source),
            ),
            else_=None,
        ),
        or_(
            and_(
                revoked.c.selector_kind == "original-admission",
                revoked.c.selector == admissions.c.id,
            ),
            and_(
                revoked.c.selector_kind == "original-source",
                revoked.c.selector == admissions.c.source_reference,
            ),
            and_(
                revoked.c.selector_kind == "product", revoked.c.selector == admissions.c.product_id
            ),
        ),
    )
    episode_match = and_(
        episode_node,
        revoked.c.scope
        == case(
            (
                requests.c.project_id.is_not(None),
                func.ops.ddo_scope(requests.c.project_id, requests.c.original_source),
            ),
            else_=None,
        ),
        or_(
            and_(revoked.c.selector_kind == "derivation", revoked.c.selector == episodes.c.id),
            and_(revoked.c.selector_kind == "recipe", revoked.c.selector == episodes.c.recipe),
            and_(revoked.c.selector_kind == "runtime", revoked.c.selector == episodes.c.runtime_id),
            and_(
                revoked.c.selector_kind == "product",
                exists(
                    select(1)
                    .select_from(outputs)
                    .where(
                        outputs.c.derivation_id == episodes.c.id,
                        outputs.c.product_id == revoked.c.selector,
                    )
                ).correlate(episodes, revoked),
            ),
        ),
    )
    epoch = cast(
        core_reference("boundary", "trust_snapshot", type_=JSONB()).op("->>")(revoked.c.scope),
        BigInteger(),
    )
    relation = (
        seeds.join(uses, uses.c.id == seeds.c.id)
        .join(closure, true())
        .outerjoin(episodes, and_(episode_node, episodes.c.id == closure.c.id))
        .outerjoin(requests, requests.c.id == episodes.c.request_id)
        .outerjoin(admissions, and_(original_node, admissions.c.id == closure.c.id))
        .outerjoin(
            revoked,
            and_(~closure.c.valid, or_(episode_match, original_match), revoked.c.epoch <= epoch),
        )
    )
    visible_kind = case((episode_node, "episode"), else_=closure.c.kind)
    record = func.jsonb_build_object(
        "root_use_id",
        uses.c.id,
        "root_derivation_id",
        uses.c.derivation_id,
        "node_kind",
        closure.c.kind,
        "node_id",
        closure.c.id,
        "valid",
        closure.c.valid,
        "revocation_id",
        revoked.c.id,
        "selector_kind",
        revoked.c.selector_kind,
        "selector",
        revoked.c.selector,
        "support_path",
        func.jsonb_build_array(
            literal("use:").concat(uses.c.id), closure.c.kind.concat(":").concat(closure.c.id)
        ),
    )
    key = literal("ops.data_support_explanation:").concat(
        cast(func.jsonb_build_array(uses.c.id, closure.c.kind, closure.c.id, revoked.c.id), Text())
    )
    return (
        select(
            key.label("key"),
            literal("ops.data_support_explanation").label("relation"),
            record.label("record"),
        )
        .select_from(relation)
        .where(disclosed(visible_kind, closure.c.id))
    )
