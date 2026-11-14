"""Project declared source-role and population meanings into frozen discovery edges."""

from .data_operation_bindings import inspect_binding_scopes
from .data_operation_demands import DiscoverySelection
from .data_operation_kind_refinements import input_kind_refinements
from .data_operation_member_contracts import derive_member_kinds


def source_discovery_relations(model, producer, output_role, target, *, choices=None,
    default_population="selected-source-views") -> tuple[DiscoverySelection, ...]:
    """Associate child-local sources and preserve original-source context universes.

    This chooses no method or dependency. The admitted role and active binding
    expression supply each population's meaning; native closure owns its facts.
    """
    operation = model.operation(target)
    output = next(role for role in model.operation(producer).roles
        if role.direction == "output" and role.name == output_role)
    member_kinds = set(derive_member_kinds(model, output.kind))
    inputs = {role.name: role for role in operation.roles if role.direction == "input"}
    compatible = [role for role in inputs.values()
        if role.support is not None and "computation" in role.support.origins
        and set(input_kind_refinements(model, (role.kind,))[role.kind]).intersection(member_kinds)]
    if not any(role.subject_target == "subject" and role.subject_field is None for role in compatible) and operation.subject != "original-source-view":
        return ()
    expression = next(binding.expression for binding in model.bindings if binding.semantic_id == operation.binding)
    scopes = inspect_binding_scopes(expression, tuple(inputs), choices or {})
    compatible = [role for role in compatible if role.name not in scopes.inactive]
    children = [role for role in compatible if role.subject_target == "subject" and role.subject_field is None]
    # Document fan-in may consume the same source kind through a document field;
    # that does not make the document operation one obligation per source child.
    if not children and operation.subject != "original-source-view":
        return ()
    result = []
    for role in children:
        name = scopes.populations.get(role.name) or (default_population if len(children) == 1 else default_population + "/" + role.name)
        result.append(DiscoverySelection(producer, output_role, target, name, target_role=role.name))
    for role in compatible:
        if role.subject_target != "original-source" or role.subject_field is None:
            continue
        population = scopes.populations.get(role.name)
        if population is None:
            raise ValueError("original-source context role requires its explicit binding population: " + target + "/" + role.name)
        # No target_role: the native exact-child association would deliberately
        # narrow to one child and destroy the declared contextual denominator.
        result.append(DiscoverySelection(producer, output_role, target, population))
    if not children:
        result.append(DiscoverySelection(producer, output_role, target, default_population))
    names = [relation.population for relation in result]
    if len(set(names)) != len(names):
        raise ValueError("distinct discovered source roles require distinct declared populations")
    return tuple(result)
