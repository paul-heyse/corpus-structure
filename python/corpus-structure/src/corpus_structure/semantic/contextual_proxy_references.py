"""Declared scalar targets of contextual native graph proxies."""

from functools import cache
from typing import Any, Literal, overload

from .data_product_reference import (
    DataProductMemberReference,
    SemanticReference,
    read_member_reference,
    read_semantic_reference,
)

CONTEXTUAL_NATIVE_INPUT_ROLES = ("formal", "constructions", "maverick", "dipo")

PROXY_SUPPORT = (
    ("formal", "formal_proxy_support"),
    ("constructions", "construction_proxy_support"),
)


def require_contextual_native_inputs(value):
    for role in CONTEXTUAL_NATIVE_INPUT_ROLES:
        if read_semantic_reference(value[role + "_input"]) != SemanticReference.whole(role):
            raise ValueError("native contextual input differs from its declared whole role")


def _is_proxy(body):
    return body.get("kind") in {"context.symbolic_site", "context.evidence_site"}


def contextual_proxy_roles(products):
    """Index the two actual scalar parents by their governed product key."""
    return {product: role for (role, _), product in zip(PROXY_SUPPORT, products, strict=True)}


def stage_contextual_proxy_support(packets, role_by_product):
    """Place each contextual endpoint's one admitted citation in its declared role slot."""
    fields = dict(PROXY_SUPPORT)
    supports = {field: [] for field in fields.values()}
    members = []
    for packet in packets:
        body = packet["body"]
        if _is_proxy(body):
            (raw,) = body["external_premises"]
            target = read_member_reference(raw)
            if not isinstance(target, DataProductMemberReference):
                raise ValueError("native contextual proxy requires an admitted member address")
            role = role_by_product.get(target.product.product_id)
            if role is None:
                raise ValueError("native contextual proxy is outside its declared inputs")
            supports[fields[role]].append(
                {
                    "owner": packet["member_id"],
                    "target": SemanticReference.member(role, target.member_id).values(),
                }
            )
            body = {key: child for key, child in body.items() if key != "external_premises"}
        members.append({**packet, "body": body})
    return {**supports, "members": members}


def _declared_proxy_targets(value):
    targets = {}
    for role, field in PROXY_SUPPORT:
        for support in value[field]:
            owner = support["owner"]
            target = read_semantic_reference(support["target"])
            if owner in targets or (
                target.variant != "member" or target.role != role or target.occurrence is not None
            ):
                raise ValueError("native contextual proxy needs one reference in its declared role")
            targets[owner] = target, f"/{field}/*/target"
    return targets


def _expand_proxy_members(value, references):
    """Build a working graph after all of its role targets are authorized."""
    members = []
    for packet in value["members"]:
        body = packet["body"]
        owner = packet["member_id"]
        if _is_proxy(body):
            if owner not in references or body.get("external_premises"):
                raise ValueError("native contextual proxy must use its one declared target")
            body = {**body, "external_premises": [references.pop(owner).values()]}
        members.append({**packet, "body": body})
    if references:
        raise ValueError("native contextual proxy target names an absent or non-proxy owner")
    return {**value, "members": members}


def project_contextual_proxy_graph(value, inputs):
    """Read one admitted proxy graph against independently acquired scalar inputs."""
    if not any(field in value for _, field in PROXY_SUPPORT):
        return value
    from .data_product_reference import DataProductReference, member_reference

    require_contextual_native_inputs(value)

    @cache
    def addressed(role):
        return {
            packet["member_id"]
            for packet in inputs[role].value["members"]
            if packet["body"]["record_type"] in {"annotation", "term"}
        }

    def resolve(target, *, path):
        role, member = target.role, target.member_id
        if member is None or member not in addressed(role):
            raise ValueError(
                f"native contextual proxy at {path} requires its admitted annotation or term"
            )
        return member_reference(DataProductReference(inputs[role].semantic_id), member)

    references = {
        owner: resolve(target, path=path)
        for owner, (target, path) in _declared_proxy_targets(value).items()
    }
    return _expand_proxy_members(value, references)


@overload
def expand_selected_contextual_proxies(
    value, index, cut, product_id, *, with_parents: Literal[False] = False
) -> dict[str, Any]: ...


@overload
def expand_selected_contextual_proxies(
    value, index, cut, product_id, *, with_parents: Literal[True]
) -> tuple[dict[str, Any], tuple[tuple[str, None, str], ...]]: ...


def expand_selected_contextual_proxies(value, index, cut, product_id, *, with_parents=False):
    """Read one graph authorized as a whole by an exact use in the acquired cut."""
    if not any(field in value for _, field in PROXY_SUPPORT):
        return (value, ()) if with_parents else value
    from types import SimpleNamespace

    from .data_product_reference import DataProductReference, member_reference
    from .live_reference_resolution import (
        PreparedSelectedOutputReferences,
        reference_input_address,
    )

    targets = _declared_proxy_targets(value)
    roles = CONTEXTUAL_NATIVE_INPUT_ROLES
    require_contextual_native_inputs(value)
    scope = SimpleNamespace(cut=cut, index=index)

    def resolve_all(output, use, parents):
        derivation_id = output["derivation_id"]
        episode = index.mapping("ops.data_derivation", ("id",))[derivation_id]
        request = index.mapping("ops.data_request", ("id",))[episode["request_id"]]
        selected = SimpleNamespace(
            derivation_id=derivation_id,
            use_id=use["id"],
            operation_id=request["operation_id"],
            output=output,
        )
        prepared = PreparedSelectedOutputReferences(scope, selected)
        for role in roles:
            bound = prepared.resolve(
                SemanticReference.whole(role), path="/" + role + "_input", metadata_only=True
            )
            if bound.product_id != parents[role]:
                raise ValueError("native contextual closure changes its exact original input")
        references = {}
        for (owner, (target, _)), (_, body) in zip(
            targets.items(), prepared.resolve_ordered(targets.values()), strict=True
        ):
            if (
                not isinstance(body, dict)
                or body.get("record_type") not in {"annotation", "term"}
                or target.member_id is None
                or body.get("local_id") != target.member_id
            ):
                raise ValueError(
                    "selected contextual proxy target is not its admitted annotation or term"
                )
            refs_parent = DataProductReference(parents[target.role])
            references[owner] = member_reference(refs_parent, target.member_id)
        return references

    graph = None
    first_refusal = None
    for output in index.rows_for(
        "ops.data_derivation_output", product_id=product_id, role="result"
    ):
        if output.get("member_id") is not None:
            continue
        derivation_id = output["derivation_id"]
        role_bindings = {
            role: tuple(
                index.rows_for("ops.data_derivation_input", derivation_id=derivation_id, role=role)
            )
            for role in roles
        }
        if any(len(bindings) != 1 for bindings in role_bindings.values()):
            if first_refusal is None:
                first_refusal = ValueError("selected reference lacks its scalar original input")
            continue
        originals = {role: bindings[0] for role, bindings in role_bindings.items()}
        parents = {role: original["product_id"] for role, original in originals.items()}
        if graph is not None and parents == graph[0]:
            continue
        required = {
            (role, reference_input_address(original)) for role, original in originals.items()
        }
        for use in index.rows_for("ops.demand_use", derivation_id=derivation_id, fate="fulfilled"):
            current = {
                (pin["role"], reference_input_address(pin))
                for pin in use["selection"]["inputs"]
                if pin["role"] in roles
            }
            if not required <= current:
                continue
            # Every matching use of this derivation has the same exact inputs
            # for these slots and the same historical release declaration.
            try:
                references = resolve_all(output, use, parents)
            except (KeyError, PermissionError, ValueError) as error:
                if first_refusal is None:
                    first_refusal = error
            else:
                if graph is not None:
                    raise ValueError(
                        "selected contextual product has different authorized graph parents"
                    )
                graph = parents, references
            break
    if graph is None:
        if first_refusal is not None:
            raise first_refusal
        raise ValueError("original reference parent is unavailable in any exact selected use")
    expanded = _expand_proxy_members(value, graph[1])
    parents = tuple((role, None, graph[0][role]) for role in roles)
    return (expanded, parents) if with_parents else expanded
