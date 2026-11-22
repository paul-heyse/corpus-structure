"""Project construction's formal input references for exact working graph readers."""

from types import SimpleNamespace

from .data_product_reference import DataProductReference, member_reference, read_semantic_reference


def construction_formal_parents(member):
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


def project_construction_formal_support(value, parents):
    """Restore exact graph slots from the admitted original formal input ledger."""
    if not value.get("formal_support"):
        return value
    addresses = dict(parents)
    slots = {}
    for item in value["formal_support"]:
        target = read_semantic_reference(item["target"])
        if target.role != "formal" or target.variant != "member" or target.member_id is None:
            raise ValueError("construction premise requires a formal member reference")
        product = addresses.get(target.occurrence)
        if product is None:
            raise ValueError("construction premise lacks its original formal input")
        key = item["owner"], item["use"]
        position = item["position"]
        if type(position) is not int or position < 0 or position in slots.setdefault(key, {}):
            raise ValueError("construction formal premise repeats or changes its graph position")
        slots[key][position] = member_reference(
            DataProductReference(product), target.member_id
        ).values()

    annotation_positions = {}
    for item in value.get("annotation_support", ()):
        if item["use"] in {"external_premise", "basis_external_premise"}:
            annotation_positions.setdefault((item["owner"], item["use"]), set()).add(
                item["position"]
            )
    fields = {
        "external_premise": (False, "external_premises"),
        "basis_external_premise": (True, "external_premises"),
        "required_external_choice": (False, "required_external_choices"),
        "basis_required_external_choice": (True, "required_external_choices"),
    }
    visited = set()

    def project(body):
        if body.get("record_type") == "manifest":
            return body
        owner = body["local_id"]
        result = dict(body)
        for use, (basis, field) in fields.items():
            key = owner, use
            if key not in slots:
                continue
            visited.add(key)
            if basis:
                if "basis" not in result:
                    raise ValueError("construction formal premise lacks its graph basis")
                record = result["basis"] = dict(result["basis"])
            else:
                record = result
            original = record.get(field, ())
            formal = slots[key]
            annotations = annotation_positions.get(key, set())
            size = len(original) + len(formal) + len(annotations)
            if set(formal) & annotations or any(
                type(position) is not int or not 0 <= position < size
                for position in (*formal, *annotations)
            ):
                raise ValueError("construction formal premise leaves its exact graph slot")
            remaining = iter(original)
            record[field] = [
                formal[position] if position in formal else next(remaining)
                for position in range(size)
                if position not in annotations
            ]
        if body.get("record_type") == "choice":
            # The inline alternative and its separately addressed packet must agree.
            result["members"] = [project(member) for member in body["members"]]
        return result

    packets = [dict(packet, body=project(packet["body"])) for packet in value["members"]]
    if visited != slots.keys():
        raise ValueError("construction formal premise targets an absent graph member or use")
    return {**value, "members": packets}


def expand_selected_construction_formal_support(value, index, cut, product_id):
    """Resolve all cited addresses within one entirely authorized selected use."""
    if not value.get("formal_support"):
        return value
    from .live_reference_resolution import PreparedSelectedOutputReferences

    targets = {read_semantic_reference(item["target"]) for item in value["formal_support"]}
    result, first_error = None, None
    scope = SimpleNamespace(index=index, cut=cut)
    for output in index.rows_for(
        "ops.data_derivation_output", product_id=product_id, role="result"
    ):
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
                prepared = PreparedSelectedOutputReferences(scope, selected)
                for target in targets:
                    binding, body = prepared.resolve(
                        target, path="/formal_support/*/target", with_binding=True
                    )
                    if not isinstance(body, dict) or "record_type" not in body:
                        raise ValueError(
                            "construction premise did not cite an actual formal member"
                        )
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
        raise ValueError("construction premise lacks a complete selected use")
    return project_construction_formal_support(value, result.items())
