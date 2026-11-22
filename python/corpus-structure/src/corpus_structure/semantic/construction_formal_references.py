"""Project construction's role-relative grammar atoms for exact graph readers."""

from types import SimpleNamespace

from .data_product_reference import DataProductReference, member_reference, read_semantic_reference


def formal_atom_parents(member):
    from .reference_resolution import selected_producing_reference_bindings

    bindings = selected_producing_reference_bindings(member)
    return tuple(
        (item.occurrence, item.product_id)
        for item in bindings.inputs
        if item.role == "formal"
        and item.occurrence_position
        and item.occurrence is not None
        and item.member_id is None
        and item.multiplicity == 1
    )


def project_formal_atom_support(value, parents):
    """Make working graph edges from the admitted parent map."""
    if not value.get("formal_atom_support"):
        return value
    addresses = dict(parents)
    edges = {}
    for item in value["formal_atom_support"]:
        target = read_semantic_reference(item["target"])
        if target.role != "formal" or target.variant != "member" or target.member_id is None:
            raise ValueError("construction syntax atom requires a formal member reference")
        product = addresses.get(target.occurrence)
        if product is None:
            raise ValueError("construction syntax atom lacks its original formal input")
        owner_edges = edges.setdefault(item["owner"], [])
        resolved = member_reference(DataProductReference(product), target.member_id).values()
        if resolved in owner_edges:
            raise ValueError("construction syntax atom repeats its supporting reference")
        owner_edges.append(resolved)

    packets = []
    for packet in value["members"]:
        if (resolved := edges.pop(packet["member_id"], None)) is None:
            packets.append(packet)
            continue
        body = packet["body"]
        if (
            body.get("kind") != "grammar.terminal"
            or body.get("native_label") != "ATOM"
            or body.get("external_premises")
        ):
            raise ValueError("construction formal premise must belong to a grammar atom")
        packets.append({**packet, "body": {**body, "external_premises": resolved}})
    if edges:
        raise ValueError("construction formal premise targets an absent grammar atom")
    return {**value, "members": packets}


def expand_selected_formal_atom_support(value, index, cut, product_id):
    """Resolve all cited addresses within one entirely authorized selected use."""
    if not value.get("formal_atom_support"):
        return value
    from .live_reference_resolution import require_selected_output_reference

    targets = {
        read_semantic_reference(item["target"]) for item in value["formal_atom_support"]
    }
    result, first_error = None, None
    scope = SimpleNamespace(index=index, cut=cut)
    for output in index.rows_for("ops.data_derivation_output", product_id=product_id, role="result"):
        if output.get("member_id") is not None:
            continue
        derivation_id = output["derivation_id"]
        episode = index.mapping("ops.data_derivation", ("id",))[derivation_id]
        request = index.mapping("ops.data_request", ("id",))[episode["request_id"]]
        for use in index.rows_for("ops.demand_use", derivation_id=derivation_id, fate="fulfilled"):
            selected = SimpleNamespace(
                output=output,
                derivation_id=derivation_id,
                use_id=use["id"],
                operation_id=request["operation_id"],
            )
            parents = {}
            try:
                for target in targets:
                    binding, body = require_selected_output_reference(
                        scope, selected, target, path="/formal_atom_support/*/target",
                        with_binding=True,
                    )
                    if not isinstance(body, dict) or body.get("record_type") != "occurrence":
                        raise ValueError("construction syntax atom did not cite a formal occurrence")
                    parents[target.occurrence] = binding.product_id
            except (KeyError, PermissionError, ValueError) as error:
                if first_error is None:
                    first_error = error
                continue
            if result is not None and parents != result:
                raise ValueError("construction has conflicting authorized original formal inputs")
            result = parents
            break
    if result is None:
        if first_error is not None:
            raise first_error
        raise ValueError("construction syntax atom lacks a complete selected use")
    return project_formal_atom_support(value, result.items())
