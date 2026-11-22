"""Producer-owned evidence for reusable source contributions."""

from typing import Any

from .contributions import (
    CONTRIBUTION_PRIMARY_FIELDS as PRIMARY_FIELDS,
)
from .contributions import (
    CONTRIBUTION_REPEATED_FIELDS as REPEATED_FIELDS,
)
from .contributions import (
    split_contribution_evidence,
)
from .observations import source_python, source_value

SUPPORT_FIELDS = ("construction_support", "formal_support", "inherited_support")


def _dependencies(row):
    component = row.get("component") or {}
    return set(
        (
            *row.get("members", ()),
            *row.get("computation_dependencies", ()),
            *(endpoint["contribution_id"] for endpoint in row.get("endpoints", ())),
            *component.get("dependencies", ()),
            *(key for basis in component.get("bases", ()) for key in basis.get("dependencies", ())),
        )
    )


def pack_contribution_input_support(
    rows, roles, *, inherited=(), primary_evidence=()
) -> tuple[tuple[dict[str, Any], ...], dict[str, list[dict[str, Any]]]]:
    """Bind fresh evidence once; copied predicate members keep their original owner."""
    from .data_product_reference import SemanticReference
    from .declared_candidate_products import candidate_member_id

    inherited = {row["contribution_id"]: row for row in inherited}
    addresses = {}
    for role in ("constructions", "formal"):
        for member in next((value.members for value in roles if value.role == role), ()):
            if (
                member.member is not None
                or member.multiplicity != 1
                or member.reference_position is None
                or member.product in addresses
            ):
                raise ValueError("contribution evidence lacks one exact original input position")
            addresses[member.product] = (role, str(member.reference_position))
    inherited_atoms = {}
    for identifier, row in inherited.items():
        for _path, _position, reference in split_contribution_evidence(row)[1]:
            inherited_atoms.setdefault(
                (reference["product_id"], reference["member_id"]), set()
            ).add(identifier)
    rows = tuple(rows)
    by_id = {row["contribution_id"]: row for row in rows}
    support = {field: [] for field in SUPPORT_FIELDS}
    cleaned, clean_by_id, seen_evidence = [], {}, set()
    collected = {}
    for identifier, path, position, reference in primary_evidence:
        collected.setdefault(identifier, []).append((path, position, reference))

    def reaches(identifier, sought):
        pending, seen = [identifier], set()
        while pending:
            current = pending.pop()
            if current in sought:
                return True
            if current not in seen and current in by_id:
                seen.add(current)
                pending.extend(_dependencies(by_id[current]) - seen)
        return False

    for row in rows:
        clean, evidence = split_contribution_evidence(row)
        identifier = row["contribution_id"]
        member_id = candidate_member_id("contribution", clean)
        if identifier in clean_by_id:
            if clean != clean_by_id[identifier]:
                raise ValueError("contribution identity names competing domain meanings")
        else:
            clean_by_id[identifier] = clean
            cleaned.append(clean)
        evidence = (*evidence, *collected.get(identifier, ()))
        if identifier in inherited:
            if clean != split_contribution_evidence(inherited[identifier])[0]:
                raise ValueError("copied predicate member changes its original domain meaning")
            inherited_slot = dict(
                member_id=member_id,
                target=SemanticReference.member("predicates", member_id).member_value(),
            )
            if inherited_slot not in support["inherited_support"]:
                support["inherited_support"].append(inherited_slot)
            continue
        for path, position, reference in evidence:
            slot_key = identifier, path, position, reference["product_id"], reference["member_id"]
            if slot_key in seen_evidence:
                continue
            seen_evidence.add(slot_key)
            parent = addresses.get(reference["product_id"])
            if parent is None:
                origins = inherited_atoms.get(
                    (reference["product_id"], reference["member_id"]), set()
                )
                if not origins or not reaches(identifier, origins):
                    raise ValueError("contribution evidence is outside its actual producing inputs")
                # The domain dependency reaches the copied predicate member, whose
                # inherited support preserves that evidence under its own producer.
                continue
            role, occurrence = parent
            field = "construction_support" if role == "constructions" else "formal_support"
            support[field].append(
                dict(
                    member_id=member_id,
                    field=path,
                    position=position,
                    target=SemanticReference.member(
                        role, reference["member_id"], occurrence=occurrence
                    ).occurrence_member_value(),
                )
            )
    return tuple(cleaned), support


def project_contribution_input_support(report, member):
    """Restore a private working projection using the predicate's original bindings."""
    from .data_product_reference import read_semantic_reference
    from .declared_candidate_products import candidate_member_values
    from .reference_resolution import selected_producing_reference_bindings

    rows = candidate_member_values(report, candidate_type="contribution")
    if not report["construction_support"] and not report["formal_support"]:
        return rows
    bindings = selected_producing_reference_bindings(member)
    by_member = {"contribution:" + row["contribution_id"]: row for row in rows}
    decoded: dict[str, Any] = {}
    slots = sorted(
        (*report["construction_support"], *report["formal_support"]),
        key=lambda slot: (slot["member_id"], slot["field"], slot["position"]),
    )
    for slot in slots:
        row = by_member[slot["member_id"]]
        target = read_semantic_reference(slot["target"])
        binding = bindings.resolve(target, occurrence_position=True)
        reference = dict(product_id=binding.product_id, member_id=target.member_id)
        path = slot["field"].split("/")
        if path[0] == "component":
            node = row["component"]
        elif path[0] == "value":
            node = decoded.setdefault(slot["member_id"], source_python(row["value"]))
        else:
            raise ValueError("contribution evidence names another domain field")
        for part in path[1:-1]:
            node = node[int(part)] if isinstance(node, (tuple, list)) else node[part]
        name = path[-1]
        if name not in PRIMARY_FIELDS:
            raise ValueError("contribution evidence names an undeclared field")
        if name in REPEATED_FIELDS:
            values = node.setdefault(name, [])
            if slot["position"] > len(values):
                raise ValueError("contribution evidence has incomplete ordered positions")
            if slot["position"] == len(values):
                values.append(reference)
        elif slot["position"] != 0:
            raise ValueError("contribution evidence changes its scalar field position")
        else:
            node.setdefault(name, reference)
    for identifier, value in decoded.items():
        by_member[identifier]["value"] = source_value(value)
    return rows


def check_contribution_input_support(report):
    """Check ownership, canonical domain identities and exact logical evidence slots."""
    from .contributions import contribution_identity
    from .data_product_reference import read_semantic_reference

    members = {packet["member_id"]: packet["body"] for packet in report["members"]}
    if len(members) != len(report["members"]):
        raise ValueError("contribution report repeats a member")
    for identifier, body in members.items():
        if body.get("candidate_type") != "contribution":
            continue
        row = {key: value for key, value in body.items() if key != "candidate_type"}
        if split_contribution_evidence(row)[
            0
        ] != row or identifier != "contribution:" + contribution_identity(row):
            raise ValueError("contribution report changes its evidence-free domain member")
    positions, logical_slots = {}, set()
    inherited = set()
    for field in SUPPORT_FIELDS:
        for slot in report.get(field, ()):
            if slot["member_id"] not in members:
                raise ValueError("contribution evidence names another report member")
            if field == "inherited_support":
                if slot["member_id"] in inherited:
                    raise ValueError("contribution repeats its original predicate member")
                inherited.add(slot["member_id"])
                continue
            parts = slot["field"].split("/")
            if parts[0] not in {"component", "value"} or parts[-1] not in PRIMARY_FIELDS:
                raise ValueError("contribution evidence names an undeclared field")
            key = slot["member_id"], slot["field"]
            values = positions.setdefault(key, set())
            target = read_semantic_reference(slot["target"])
            logical = key, slot["position"], target
            if logical in logical_slots:
                raise ValueError("contribution evidence repeats its logical position")
            logical_slots.add(logical)
            values.add(slot["position"])
    for (_member, path), values in positions.items():
        expected = set(range(len(values))) if path.split("/")[-1] in REPEATED_FIELDS else {0}
        if values != expected:
            raise ValueError("contribution evidence has incomplete ordered positions")
    return members


def require_selected_contribution_input_support(scope, selected):
    """Authenticate report evidence through the existing exact selected-use resolver."""
    from functools import partial

    from .contextual_input_references import require_contextual_choice_alternative
    from .data_product_reference import read_semantic_reference
    from .live_reference_resolution import PreparedSelectedOutputReferences

    report = selected.body
    if not all(field in report for field in ("construction_support", "formal_support")):
        return
    members = check_contribution_input_support(report)
    prepared = PreparedSelectedOutputReferences(scope, selected)
    seen = set()
    for field in SUPPORT_FIELDS:
        path = "/" + field + "/*/target"
        for slot in report.get(field, ()):
            if slot["member_id"] not in members:
                raise ValueError("contribution evidence names another report member")
            target = read_semantic_reference(slot["target"])
            key = field, slot["member_id"], slot.get("field"), slot.get("position"), target
            if key in seen:
                raise ValueError("contribution evidence repeats its logical slot")
            seen.add(key)
            value = prepared.resolve(target, path=path)
            if field == "inherited_support":
                if value != members[slot["member_id"]]:
                    raise ValueError(
                        "inherited contribution differs from its original predicate member"
                    )
            elif slot["field"].split("/")[-1] == "primary_choices":
                require_contextual_choice_alternative(
                    target, value, partial(prepared.resolve, path=path)
                )
