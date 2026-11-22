"""Contextual graph edges addressed in their original unordered input roles."""

from functools import partial
from types import SimpleNamespace
from typing import Any, Literal, overload

from .data_product_reference import SemanticReference, read_semantic_reference
from .native_source_view import thaw_native

CONTEXTUAL_INPUT_ROLES = ("formal", "constructions", "supporting")
CONTEXTUAL_MEMBER_FIELDS = tuple(role + "_member_support" for role in CONTEXTUAL_INPUT_ROLES)
CONTEXTUAL_PRODUCT_FIELDS = tuple(role + "_product_support" for role in CONTEXTUAL_INPUT_ROLES)


def _graph_bodies(value):
    for packet in value["members"]:
        body = packet["body"]
        yield packet["member_id"], body
        if body.get("record_type") == "choice":
            for member in body.get("members", ()):
                yield member["local_id"], member


def _locations(value):
    for owner, body in _graph_bodies(value):
        for prefix, selected in (("", body), ("basis_", body.get("basis", {}))):
            for field, use in (
                ("external_premises", "premise"),
                ("required_external_choices", "choice"),
            ):
                if field in selected:
                    yield owner, prefix + use, selected, field
    yield "$context", "root", value, "roots"
    environment = value["environment"]
    for field in ("hypotheses", "proposals", "choices", "attribution", "context_products"):
        yield "$context", field, environment, field
    for position, binding in enumerate(environment.get("bindings", ())):
        for field in ("variable", "binder"):
            yield str(position), "binding_" + field, binding, field


def pack_contextual_input_support(value, roles) -> dict[str, Any]:
    """Replace concrete external pins with declared role-local input addresses."""
    value = thaw_native(value)
    addresses = {}
    for role in CONTEXTUAL_INPUT_ROLES:
        for position, product in enumerate(roles.get(role, ())):
            if product.semantic_id in addresses:
                raise ValueError("contextual input repeats an exact report across producing roles")
            addresses[product.semantic_id] = (role, str(position))
    slots = {field: [] for field in (*CONTEXTUAL_MEMBER_FIELDS, *CONTEXTUAL_PRODUCT_FIELDS)}
    seen = set()
    for owner, use, parent, field in _locations(value):
        scalar = use.startswith("binding_")
        references = [parent[field]] if scalar else parent.get(field, ())
        for position, reference in enumerate(references):
            product_id = reference["product_id"]
            if product_id not in addresses:
                raise ValueError("contextual graph cites a report outside its producing inputs")
            role, occurrence = addresses[product_id]
            member_id = reference.get("member_id")
            target = (
                SemanticReference.whole(role, occurrence=occurrence)
                if member_id is None
                else SemanticReference.member(role, member_id, occurrence=occurrence)
            )
            key = owner, use, position, target
            if key in seen:
                continue
            seen.add(key)
            slots[role + "_" + target.variant + "_support"].append(
                dict(owner=owner, use=use, position=position, target=target.values())
            )
        if scalar:
            parent.pop(field)
        else:
            parent[field] = []
    value["environment"]["bindings"] = []
    value.pop("dependencies", None)
    for packet in value["members"]:
        if packet["body"].get("record_type") == "manifest":
            packet["body"].pop("dependencies", None)
    return {**value, **slots}


def contextual_input_parents(member):
    from .reference_resolution import selected_producing_reference_bindings

    return tuple(
        (item.role, item.occurrence, item.product_id)
        for item in selected_producing_reference_bindings(member, require_complete=True).inputs
        if item.role in CONTEXTUAL_INPUT_ROLES
        and item.occurrence_position
        and item.occurrence is not None
        and item.member_id is None
        and item.multiplicity == 1
    )


def require_contextual_choice_alternative(reference, member, resolve):
    """A cited external choice is one exact flattened alternative of its admitted group."""
    if (
        not isinstance(member, dict)
        or member.get("record_type") != "choice_member"
        or member.get("local_id") != reference.member_id
        or not isinstance(member.get("group_id"), str)
    ):
        raise ValueError("contextual choice reference requires an actual packed alternative")
    group = resolve(
        SemanticReference.member(
            reference.role, member["group_id"], occurrence=reference.occurrence
        )
    )
    if not isinstance(group, dict) or group.get("record_type") != "choice":
        raise ValueError("contextual choice alternative lacks its admitted packed group")
    alternatives = [item for item in group["members"] if item["local_id"] == reference.member_id]
    expected = {
        key: value for key, value in member.items() if key not in {"record_type", "group_id"}
    }
    if len(alternatives) != 1 or alternatives[0] != expected:
        raise ValueError("contextual choice alternative differs from its admitted packed group")


def project_contextual_input_support(value, parents) -> dict[str, Any]:
    """Recover working graph addresses from one authenticated original binding."""
    value = thaw_native(value)
    if "dependencies" in value or value["environment"].get("bindings", ()):
        raise ValueError("contextual graph retains an unscoped dependency or binding")
    addresses = {}
    for role, occurrence, product in parents:
        if (role, occurrence) in addresses:
            raise ValueError("contextual producing inputs repeat an original ledger address")
        addresses[role, occurrence] = product
    references = {}
    grouped = {}
    for role in CONTEXTUAL_INPUT_ROLES:
        for variant in ("member", "product"):
            for slot in value[role + "_" + variant + "_support"]:
                target = read_semantic_reference(slot["target"])
                if (target.role, target.variant) != (role, variant):
                    raise ValueError("contextual input support differs from its declared role")
                product = addresses.get((role, target.occurrence))
                if product is None:
                    raise ValueError("contextual input support lacks its exact original input")
                reference = {"product_id": product}
                if target.member_id is not None:
                    reference["member_id"] = target.member_id
                key = slot["owner"], slot["use"], slot["position"]
                if key in references:
                    raise ValueError("contextual input support repeats a logical slot")
                references[key] = reference
                grouped.setdefault((slot["owner"], slot["use"]), {})[slot["position"]] = reference
    bindings = {}
    for key, reference in references.items():
        owner, use, position = key
        if use.startswith("binding_"):
            if position != 0 or not owner.isdecimal():
                raise ValueError("contextual binding support has an invalid logical slot")
            bindings.setdefault(int(owner), {})[use.removeprefix("binding_")] = reference
    if set(bindings) != set(range(len(bindings))):
        raise ValueError("contextual input support has incomplete binding positions")
    value["environment"]["bindings"] = [bindings[position] for position in range(len(bindings))]
    consumed = set()
    for owner, use, parent, field in _locations(value):
        scalar = use.startswith("binding_")
        selected = grouped.get((owner, use), {})
        if scalar:
            if set(selected) != {0}:
                raise ValueError("contextual binding lacks its exact addressed endpoint")
            parent[field] = selected[0]
        else:
            if parent.get(field):
                raise ValueError("contextual graph retains an unscoped external input")
            if set(selected) != set(range(len(selected))):
                raise ValueError("contextual input support has incomplete edge positions")
            parent[field] = [selected[position] for position in range(len(selected))]
        consumed.update((owner, use, position) for position in selected)
    if consumed != set(references):
        raise ValueError("contextual input support names an absent graph owner or use")
    return value


@overload
def expand_selected_contextual_inputs(
    value, index, cut, product_id, *, with_parents: Literal[False] = False
) -> dict[str, Any]: ...


@overload
def expand_selected_contextual_inputs(
    value, index, cut, product_id, *, with_parents: Literal[True]
) -> tuple[dict[str, Any], tuple[tuple[str, str, str], ...]]: ...


def expand_selected_contextual_inputs(value, index, cut, product_id, *, with_parents=False):
    """Authorize the complete graph through one exact selected use before expansion."""
    if not all(field in value for field in CONTEXTUAL_MEMBER_FIELDS):
        return (value, ()) if with_parents else value
    from .live_reference_resolution import PreparedSelectedOutputReferences

    targets = tuple(
        dict.fromkeys(
            ("/" + field + "/*/target", read_semantic_reference(slot["target"]))
            for field in (*CONTEXTUAL_MEMBER_FIELDS, *CONTEXTUAL_PRODUCT_FIELDS)
            for slot in value[field]
        )
    )
    choices = {
        ("/" + field + "/*/target", read_semantic_reference(slot["target"]))
        for field in CONTEXTUAL_MEMBER_FIELDS
        for slot in value[field]
        if slot["use"] in {"choice", "basis_choice", "choices"}
    }
    scope = SimpleNamespace(index=index, cut=cut)
    selected_parents, first_error = None, None
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
                for original in index.rows_for(
                    "ops.data_derivation_input", derivation_id=derivation_id
                ):
                    role = original["role"]
                    if role not in CONTEXTUAL_INPUT_ROLES:
                        continue
                    reference = SemanticReference.whole(role, occurrence=str(original["position"]))
                    binding = prepared.resolve(
                        reference,
                        path="/" + role + "_product_support/*/target",
                        metadata_only=True,
                    )
                    parents[role, reference.occurrence] = binding.product_id
                for path, target in targets:
                    if target.variant == "product":
                        binding = prepared.resolve(target, path=path, metadata_only=True)
                    else:
                        binding, body = prepared.resolve(target, path=path, with_binding=True)
                        if (path, target) in choices:
                            require_contextual_choice_alternative(
                                target, body, partial(prepared.resolve, path=path)
                            )
                    parents[target.role, target.occurrence] = binding.product_id
            except (KeyError, PermissionError, ValueError) as error:
                if first_error is None:
                    first_error = error
                continue
            if selected_parents is not None and parents != selected_parents:
                raise ValueError("contextual graph has conflicting authorized original inputs")
            selected_parents = parents
            break
    if selected_parents is None:
        if first_error is not None:
            raise first_error
        raise ValueError("contextual graph lacks a complete selected use")
    parents = tuple(
        (role, occurrence, product) for (role, occurrence), product in selected_parents.items()
    )
    expanded = project_contextual_input_support(value, parents)
    return (expanded, parents) if with_parents else expanded
