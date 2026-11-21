"""Declared native graph interpretations over the protected selected-record index.

Raw historical custody remains in the index. Current support edges come from
exact admitted uses, never a recursive scan of arbitrary JSON values.
"""

from hashlib import sha256

from .data_operation_json import json_bytes
from .graph_inspection import GraphNode, GraphOccurrence, GraphSnapshot


def snapshot_from_index(prepared, cut, index, projection):
    """Pure selected/offline interpretation after native or detached authentication."""
    from .data_operation_admission import bound_data_operation_model

    model = bound_data_operation_model(prepared)
    specification = model.projection_definition(projection)
    if cut.record["release_id"] != prepared.release_id:
        raise ValueError("selected graph release differs from native cut")
    if index.cut is not None and index.cut.content != cut.content:
        raise ValueError("selected graph index belongs to another cut")
    if projection == "source-hierarchy":
        from .source_hierarchy_graph import source_hierarchy_snapshot

        return source_hierarchy_snapshot(prepared, model, cut, index)
    if projection not in {"bound-requests", "selected-support"}:
        raise ValueError("this projection requires its source/assessment acquisition owner")
    nodes, occurrences, unknowns = {}, {}, []

    def identity(relation, key):
        return relation + ":" + json_bytes(key).decode()

    def node(relation, key, kind, row):
        name = identity(relation, key)
        value = GraphNode(identity=name, kind=kind, payload_json=json_bytes(row).decode())
        if name in nodes and nodes[name] != value:
            raise ValueError("selected graph repeats a nominal node with different facts")
        nodes[name] = value
        return name

    def edge(source, target, relation, role, *, position=None, multiplicity=1, witness=None):
        if source not in nodes or target not in nodes:
            raise ValueError("selected graph occurrence lacks its authenticated endpoint")
        occurrence = GraphOccurrence(
            identity="graph-occurrence:"
            + sha256(json_bytes([source, target, relation, role, position, witness])).hexdigest(),
            source=source,
            target=target,
            relation=relation,
            role=role,
            position=position,
            multiplicity=multiplicity,
            attributes_json=json_bytes(witness or {}).decode(),
        )
        occurrences[occurrence.identity] = occurrence

    uses = {row["id"]: row for row in index.rows("ops.demand_use")}
    episodes = {row["id"]: row for row in index.rows("ops.data_derivation")}
    requests = {row["id"]: row for row in index.rows("ops.data_request")}
    populations = {row["id"]: row for row in index.rows("ops.data_population")}
    admissions = {row["id"]: row for row in index.rows("ops.original_source_admission")}
    frontier_uses = {row["use_id"]: row for row in index.frontier_rows("uses")}
    for name, row in frontier_uses.items():
        if name in uses and any(
            uses[name].get(key) != row.get(key)
            for key in ("request_id", "derivation_id", "selection")
        ):
            raise ValueError("selected frontier and support use custody differ")
    all_uses = uses | {name: {**row, "id": name} for name, row in frontier_uses.items()}
    from .authority_leaf import NativeAuthorityLeaf

    authorities = tuple(
        NativeAuthorityLeaf.model_validate(row) for row in index.rows("ops.data_authority_leaf")
    )
    for leaf in authorities:
        node(
            "ops.data_authority_leaf",
            [leaf.derivation_id, leaf.use_id],
            "authority",
            leaf.model_dump(mode="json"),
        )
        unknowns.append(
            "protected dependencies of native authority " + leaf.derivation_id + " are undisclosed"
        )
    from .execution_evidence_leaf import NativeExecutionEvidenceLeaf

    for value in index.rows("ops.data_execution_evidence_leaf"):
        execution = NativeExecutionEvidenceLeaf.model_validate_json(json_bytes(value))
        # The declared semantic-support graph is intact. Hidden physical batch
        # evidence is a separate limit, not a missing semantic dependency edge.
        unknowns.append(
            "whole physical CPU cohort for selected member " + execution.member + " is undisclosed"
        )

    def authority_reference(reference):
        if reference.get("kind") in {"original-source", "authored"}:
            return None
        matching = tuple(
            leaf
            for leaf in authorities
            if (
                leaf.derivation_id == reference.get("derivation_id")
                and (
                    reference.get("admission_use_id") is None
                    or leaf.use_id == reference["admission_use_id"]
                )
            )
        )
        if matching:
            leaf = min(matching, key=lambda value: value.use_id or "")
            return identity("ops.data_authority_leaf", [leaf.derivation_id, leaf.use_id])
        return None

    def required(relation, key, field):
        name = identity(relation, key)
        if name not in nodes:
            raise ValueError("selected graph lacks required " + field + " endpoint: " + name)
        return name

    from .support_edges import reference_node

    def reference(reference):
        kind, key = reference_node(reference)
        authority = authority_reference(reference)
        if authority is not None:
            return authority
        relation, description = {
            "original": ("ops.original_source_admission", "original support"),
            "use": ("ops.demand_use", "selected support use"),
            "episode": ("ops.data_derivation", "support episode"),
        }[kind]
        return required(relation, key, description)

    if projection == "bound-requests":
        if not index.has_frontier:
            unknowns.append("authenticated selected frontier was not supplied with this index")
        for name, row in requests.items():
            node("ops.data_request", name, "request", row)
        for name, row in all_uses.items():
            node("ops.demand_use", name, "use", row)
        for row in index.frontier_rows("obligations"):
            owner = node("ddo.selected-obligation", row["obligation_id"], "obligation", row)
            for use_id, use in frontier_uses.items():
                if use.get("obligation_id") == row["obligation_id"]:
                    edge(
                        owner,
                        required("ops.demand_use", use_id, "selected obligation use"),
                        "requires",
                        "selected-use",
                        witness={"obligation_id": row["obligation_id"], "use_id": use_id},
                    )
            if row.get("request_id"):
                # Waiting/attached requests without an episode have no exported raw
                # request row. Their exact selected frontier owns the identity.
                if row["request_id"] not in requests:
                    node(
                        "ops.data_request",
                        row["request_id"],
                        "request",
                        {
                            "id": row["request_id"],
                            "operation_id": row["operation_id"],
                            "frontier_only": True,
                        },
                    )
                edge(
                    owner,
                    required("ops.data_request", row["request_id"], "bound request"),
                    "requires",
                    "request",
                    witness={"obligation_id": row["obligation_id"]},
                )
        for name, row in populations.items():
            node("ops.data_population", name, "population", row)

        def producer_request(ref):
            kind, key = reference_node(ref)
            authority = authority_reference(ref)
            if authority is not None:
                return authority
            if kind == "original":
                return None
            if kind == "use":
                support = all_uses.get(key)
                if support is None:
                    raise ValueError("bound request lacks its selected support use")
                return required("ops.data_request", support["request_id"], "producer request")
            producer = episodes.get(key)
            if producer is None:
                raise ValueError("bound request lacks its producing episode")
            return required("ops.data_request", producer["request_id"], "producer request")

        for name, row in all_uses.items():
            owner = required("ops.demand_use", name, "use")
            if row.get("request_id") is None:
                if row.get("fate") in {"attached", "fulfilled"} or row.get("historical_fate") in {
                    "attached",
                    "fulfilled",
                }:
                    raise ValueError("attached or fulfilled use lacks its semantic request")
                continue  # Recorded availability fates do not fabricate a request/binding.
            request = required("ops.data_request", row["request_id"], "request")
            edge(request, owner, "requires", "selected-use", witness={"use_id": name})
            for position, ref in enumerate(row.get("selection", {}).get("support", ())):
                target = producer_request(ref)
                if target is not None:
                    edge(
                        owner,
                        target,
                        "selected-input",
                        ref.get("role", ""),
                        position=ref.get("position"),
                        multiplicity=ref.get("multiplicity", 1),
                        witness={"reference": ref, "selection_position": position},
                    )
            for position, ref in enumerate(row.get("selection", {}).get("populations", ())):
                edge(
                    owner,
                    required("ops.data_population", ref["population_id"], "selected population"),
                    "population",
                    "selected-population",
                    position=ref.get("position"),
                    witness={"reference": ref, "selection_position": position},
                )
    else:
        for relation, rows, kind in (
            ("kb.data_product", index.rows("kb.data_product"), "product"),
            ("ops.data_derivation", episodes.values(), "episode"),
            ("ops.demand_use", all_uses.values(), "use"),
            ("ops.data_population", populations.values(), "population"),
            ("ops.original_source_admission", admissions.values(), "original"),
        ):
            for row in rows:
                admitted_kind = (
                    "authored"
                    if relation == "ops.original_source_admission"
                    and row.get("evidence", {}).get("standing") == "authored"
                    else kind
                )
                node(relation, row["id"], admitted_kind, row)
        for row in index.rows("kb.data_product_member"):
            member = node(
                "kb.data_product_member", [row["product_id"], row["member_id"]], "member", row
            )
            edge(
                required("kb.data_product", row["product_id"], "member product"),
                member,
                "output",
                "member",
                witness={"member_id": row["member_id"]},
            )
        for row in index.rows("kb.data_product_partition"):
            fact = {key: value for key, value in row.items() if key != "body"}
            partition = node(
                "kb.data_product_partition",
                [row["product_id"], row["collection"], row["partition_key"]],
                "partition",
                fact,
            )
            edge(
                required("kb.data_product", row["product_id"], "partition product"),
                partition,
                "output",
                row["collection"],
                position=row["ordinal"],
                witness={"partition_key": row["partition_key"]},
            )
        for leaf in authorities:
            edge(
                identity("ops.data_authority_leaf", [leaf.derivation_id, leaf.use_id]),
                required("kb.data_product", leaf.product_id, "authority output"),
                "output",
                "authorization",
                position=0,
                witness={"receipt_id": leaf.receipt_id, "protected_dependencies": "undisclosed"},
            )
        for table, relation in (
            ("ops.data_derivation_input", "input"),
            ("ops.data_derivation_output", "output"),
        ):
            for row in index.rows(table):
                key = (
                    [row["product_id"], row["member_id"]]
                    if row.get("member_id") is not None
                    else row["product_id"]
                )
                target = required(
                    "kb.data_product_member" if isinstance(key, list) else "kb.data_product",
                    key,
                    relation,
                )
                edge(
                    required("ops.data_derivation", row["derivation_id"], "producing episode"),
                    target,
                    relation,
                    row["role"],
                    position=row["position"],
                    multiplicity=row.get("multiplicity", 1),
                    witness=row,
                )
        for name, row in all_uses.items():
            owner = required("ops.demand_use", name, "use")
            if row.get("request_id") is None:
                if row.get("fate") in {"attached", "fulfilled"} or row.get("historical_fate") in {
                    "attached",
                    "fulfilled",
                }:
                    raise ValueError("attached or fulfilled use lacks its semantic request")
                continue
            if row.get("derivation_id"):
                edge(
                    owner,
                    required("ops.data_derivation", row["derivation_id"], "selected producer"),
                    "admission",
                    "selected-producer",
                    witness={"use_id": name},
                )
            for position, ref in enumerate(row.get("selection", {}).get("support", ())):
                edge(
                    owner,
                    reference(ref),
                    "support",
                    ref.get("role", ""),
                    position=ref.get("position"),
                    multiplicity=ref.get("multiplicity", 1),
                    witness={"reference": ref, "selection_position": position},
                )
            for position, ref in enumerate(row.get("selection", {}).get("populations", ())):
                edge(
                    owner,
                    required("ops.data_population", ref["population_id"], "population"),
                    "population",
                    "selected-population",
                    position=ref.get("position"),
                    witness={"reference": ref, "selection_position": position},
                )
        selected_episodes = {
            row["derivation_id"] for row in all_uses.values() if row.get("derivation_id")
        }
        for table, target_field, target_relation in (
            ("ops.data_derivation_support", "support_derivation_id", "ops.data_derivation"),
            (
                "ops.data_derivation_original_support",
                "admission_id",
                "ops.original_source_admission",
            ),
        ):
            for row in index.rows(table):
                if row["derivation_id"] in selected_episodes:
                    continue  # Selected-use support supersedes the historical support list.
                if table == "ops.data_derivation_support":
                    target = reference(
                        dict(
                            kind="computation",
                            derivation_id=row[target_field],
                            admission_use_id=row.get("admission_use_id"),
                        )
                    )
                else:
                    target = required(target_relation, row[target_field], "producing support")
                edge(
                    required("ops.data_derivation", row["derivation_id"], "producing episode"),
                    target,
                    "support",
                    row.get("role", ""),
                    position=row.get("position"),
                    witness=row,
                )
        for name, row in admissions.items():
            edge(
                required("ops.original_source_admission", name, "original admission"),
                required("kb.data_product", row["product_id"], "admitted product"),
                "admission",
                "admitted-product",
                witness={"admission_id": name},
            )
    for name, row in populations.items():
        owner = required("ops.data_population", name, "population")
        evidence = row["evidence"]
        if evidence.get("admission_use_id"):
            edge(
                owner,
                required(
                    "ops.demand_use", evidence["admission_use_id"], "population producing use"
                ),
                "population",
                "producer",
                witness=evidence,
            )
        elif evidence.get("derivation_id"):
            producer = episodes.get(evidence["derivation_id"])
            if producer is None:
                raise ValueError("population lacks producing episode")
            target = (
                required("ops.data_request", producer["request_id"], "population request")
                if projection == "bound-requests"
                else required("ops.data_derivation", producer["id"], "population producer")
            )
            edge(owner, target, "population", "producer", witness=evidence)
        parent = evidence.get("selection", {}).get("parent_population_id")
        if parent is not None:
            edge(
                owner,
                required("ops.data_population", parent, "parent population"),
                "population",
                "parent",
                witness=evidence,
            )
    return GraphSnapshot(
        projection=projection,
        specification=specification.identity_bytes.hex(),
        pins_json=json_bytes({**cut.record, "cut_id": cut.identity}).decode(),
        nodes=tuple(nodes[key] for key in sorted(nodes)),
        occurrences=tuple(occurrences[key] for key in sorted(occurrences)),
        standing="partial" if unknowns else "complete",
        unknowns=tuple(unknowns),
    )


def selected_graph_snapshot(prepared, cut, index, request):
    """Interpret a detached, authenticated index without a database transaction."""
    if request.projection == "assessment":
        from corpus_structure.evaluate.assessment_graph import assessment_graph_snapshot

        addresses = tuple(
            (member.product_id, member.member_id) for member in request.assessed_members
        )
        return assessment_graph_snapshot(
            prepared, cut, index, members=addresses, max_bytes=request.max_examined_bytes
        )
    return snapshot_from_index(prepared, cut, index, request.projection)


def selected_graph_budget_snapshot(prepared, request, error):
    """Preserve an acquired native cut when examination could not retain its closure."""
    from .data_operation_admission import bound_data_operation_model

    specification = bound_data_operation_model(prepared).projection_definition(request.projection)
    pins = {**error.cut.record, "cut_id": error.cut.identity}
    return GraphSnapshot(
        projection=request.projection,
        specification=specification.identity_bytes.hex(),
        pins_json=json_bytes(pins).decode(),
        nodes=(),
        occurrences=(),
        standing="partial",
        unknowns=(str(error),),
    )
