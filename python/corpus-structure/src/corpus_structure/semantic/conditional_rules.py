"""Bounded LinkML conditional rules lowered by its native JSON Schema generator.

The boundary's ordinary types remain Pydantic's responsibility. Only the native rule
fragments are evaluated here; a successful boundary check is not persisted-state admission.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Never, cast

from jsonschema import Draft201909Validator
from linkml.generators.common.build import ClassResult as GenericClassResult
from linkml.generators.jsonschemagen import ClassResult, JsonSchemaGenerator
from linkml_runtime.linkml_model import ClassDefinition, SlotDefinition
from linkml_runtime.linkml_model.meta import AnonymousClassExpression, ClassRule
from linkml_runtime.utils.schemaview import SchemaView
from pydantic import model_validator
from pydantic_core import PydanticCustomError

from .types import Diagnostic, PreparationError

# These are result-affecting settings, archived alongside the native fragments.
CONDITIONAL_RULE_OPTIONS = {
    "generator": "linkml.generators.jsonschemagen.JsonSchemaGenerator",
    "dialect": "https://json-schema.org/draft/2019-09/schema",
    "preserve_names": True,
    "include_null": False,
    "not_closed": False,
    "use_curies": False,
    "expand_subproperty_of": False,
    "include_range_class_descendants": False,
    "alias_policy": "class_induced_slot",
    "fragment_keywords": ["if", "then", "else", "allOf"],
}

_RULE_METADATA = {"description", "title", "comments"}
_RULE_FIELDS = _RULE_METADATA | {"preconditions", "postconditions", "elseconditions", "open_world"}
_CONDITION_FIELDS = {"required", "value_presence", "equals_string", "equals_string_in", "alias"}


def _expressions(cls: ClassDefinition):
    # The generated metamodel annotations include accepted constructor inputs;
    # SchemaView's loaded objects have already materialized these concrete types.
    for rule in cast(list[ClassRule], cls.rules or []):
        for expression in (rule.preconditions, rule.postconditions, rule.elseconditions):
            if expression is not None:
                expression = cast(AnonymousClassExpression, expression)
                yield cast(dict[str, SlotDefinition], expression.slot_conditions or {})


def _refuse(location: str, message: str) -> Never:
    raise PreparationError((Diagnostic("conditional_rule", location, message, "unsupported"),))


def inspect_rule_declarations(rules: Any, location: str) -> None:
    """Reject unsupported authored fields before LinkML can coerce or ignore them."""
    if not isinstance(rules, list) or not rules:
        _refuse(location, "rules must be a nonempty sequence")
    for index, rule in enumerate(rules):
        path = f"{location}/{index}"
        if not isinstance(rule, dict) or set(rule) - _RULE_FIELDS:
            _refuse(path, "unsupported conditional-rule fields")
        if "open_world" in rule and not isinstance(rule["open_world"], bool):
            _refuse(path, "open_world must be an explicit boolean")
        if "preconditions" not in rule:
            _refuse(path, "nonempty preconditions are required")
        if not any(key in rule for key in ("postconditions", "elseconditions")):
            _refuse(path, "a conditional rule requires a consequence")
        for branch in ("preconditions", "postconditions", "elseconditions"):
            if branch not in rule:
                continue
            expression = rule[branch]
            branch_path = f"{path}/{branch}"
            if not isinstance(expression, dict) or set(expression) != {"slot_conditions"}:
                _refuse(branch_path, "only a nonempty conjunction of slot_conditions is supported")
            slots = expression["slot_conditions"]
            if not isinstance(slots, dict) or not slots:
                _refuse(branch_path, "slot_conditions must be a nonempty mapping")
            absent = 0
            for name, condition in slots.items():
                slot_path = f"{branch_path}/{name}"
                if not isinstance(condition, dict) or not condition:
                    _refuse(slot_path, "empty slot conditions are unsupported")
                if set(condition) - _CONDITION_FIELDS:
                    _refuse(slot_path, "unsupported conditional slot fields")
                if "required" in condition and not isinstance(condition["required"], bool):
                    _refuse(slot_path, "required must be an explicit boolean")
                presence = condition.get("value_presence")
                if "value_presence" in condition and (
                    not isinstance(presence, str) or presence not in {"PRESENT", "ABSENT"}
                ):
                    _refuse(slot_path, "value_presence must be PRESENT or ABSENT")
                if "required" in condition and presence is not None:
                    _refuse(slot_path, "required and value_presence cannot both be declared")
                if "equals_string" in condition and not isinstance(condition["equals_string"], str):
                    _refuse(slot_path, "equals_string must be a string literal")
                if "equals_string_in" in condition:
                    choices = condition["equals_string_in"]
                    if (
                        not isinstance(choices, list)
                        or not choices
                        or any(not isinstance(choice, str) for choice in choices)
                    ):
                        _refuse(slot_path, "equals_string_in requires nonempty string choices")
                if "equals_string" in condition and "equals_string_in" in condition:
                    _refuse(slot_path, "declare one string-choice constraint")
                has_choice = "equals_string" in condition or "equals_string_in" in condition
                if presence == "ABSENT":
                    absent += 1
                    if has_choice:
                        _refuse(slot_path, "an absent value cannot have string constraints")
                if not has_choice and presence is None and condition.get("required") is not True:
                    _refuse(slot_path, "slot condition must constrain presence or a string value")
                if branch == "preconditions" and condition.get("required") is False:
                    _refuse(slot_path, "precondition choices require presence")
                if "alias" in condition and not isinstance(condition["alias"], str):
                    _refuse(slot_path, "alias must be a string")
            if absent > 1:
                _refuse(
                    branch_path,
                    "native lowering cannot represent multiple ABSENT conditions faithfully",
                )


def _is_string(view: SchemaView, range_name: str) -> bool:
    if range_name in view.all_enums():
        return True
    seen: set[str] = set()
    while range_name not in seen:
        if range_name in {"string", "str", "uri", "uriorcurie"}:
            return True
        seen.add(range_name)
        definition = view.get_type(range_name)
        if definition is None:
            return False
        range_name = str(definition.typeof or definition.base or "string")
    return False


class _RuleGenerator(JsonSchemaGenerator):
    """Capture rules at the native lifecycle boundary, before document assembly."""

    fragments: dict[str, dict[str, Any]]

    def before_generate_class(self, cls: ClassDefinition, sv: SchemaView) -> ClassDefinition:
        slots = {str(slot.name): slot for slot in sv.class_induced_slots(cls.name)}
        for ancestor in sv.class_ancestors(cls.name):
            ancestor_cls = sv.get_class(ancestor)
            assert ancestor_cls is not None
            for conditions in _expressions(ancestor_cls):
                for name, condition in conditions.items():
                    condition.alias = str.__str__(slots[name].alias or name)
        return cls

    def after_generate_class[T: GenericClassResult](self, cls: T, sv: SchemaView) -> T:
        assert isinstance(cls, ClassResult)
        fragment = {
            key: deepcopy(cls.schema_[key])
            for key in ("if", "then", "else", "allOf")
            if key in cls.schema_
        }
        if fragment:
            self.fragments[str(cls.source.name)] = fragment
        return cls


def compile_conditional_rules(view: SchemaView) -> dict[str, dict[str, Any]]:
    """Compile rule-only fragments once, including native inherited rules.

    Alias normalization changes names only. The native generator owns every rule
    predicate and branch; unsupported constructs are never removed to obtain output.
    """
    if not any(cls.rules for cls in view.all_classes().values()):
        return {}
    schema = deepcopy(view.schema)
    assert schema is not None
    normalized = SchemaView(schema)
    # Each class's inherited rules must see its own effective slot aliases.
    for name in normalized.all_classes():
        slots = {str(slot.name): slot for slot in normalized.class_induced_slots(name)}
        aliases = [str.__str__(slot.alias or slot_name) for slot_name, slot in slots.items()]
        if len(set(aliases)) != len(aliases):
            _refuse(str(name), "conditional boundary aliases must be unique")
        for ancestor in normalized.class_ancestors(name):
            ancestor_cls = normalized.get_class(ancestor)
            assert ancestor_cls is not None
            for conditions in _expressions(ancestor_cls):
                for slot_name, condition in conditions.items():
                    slot = slots.get(slot_name)
                    if slot is None:
                        _refuse(f"{name}/{slot_name}", "rule references an unknown class slot")
                    if slot.multivalued:
                        _refuse(
                            f"{name}/{slot_name}", "conditional multivalued slots are unsupported"
                        )
                    has_choice = condition.equals_string is not None or bool(
                        condition.equals_string_in
                    )
                    if has_choice and not _is_string(normalized, str(slot.range or "string")):
                        _refuse(
                            f"{name}/{slot_name}",
                            "conditional choices require a scalar string slot",
                        )
                    alias = str.__str__(slot.alias or slot_name)
                    if condition.alias is not None and condition.alias != alias:
                        _refuse(f"{name}/{slot_name}", "conditional and boundary aliases differ")
    generator = _RuleGenerator(
        schema,
        preserve_names=True,
        include_null=False,
        not_closed=False,
        use_curies=False,
        expand_subproperty_of=False,
        include_range_class_descendants=False,
    )
    generator.fragments = {}
    generator.serialize()
    for fragment in generator.fragments.values():
        Draft201909Validator.check_schema(fragment)
    return generator.fragments


def conditional_model_namespace(fragment: dict[str, Any]) -> dict[str, Any]:
    """Build one compiled rule validator and export the same native fragment."""
    if not fragment:
        return {}
    normalized = deepcopy(fragment)
    validator = Draft201909Validator(normalized)

    def validate_rules(model: Any) -> Any:
        # Keep exact Python values and field presence. JSON serialization would lose
        # Decimal/date types and can accidentally turn omitted defaults into members.
        fields = type(model).model_fields
        values = {
            fields[name].alias or name: getattr(model, name) for name in model.model_fields_set
        }
        error = next(validator.iter_errors(values), None)
        if error is not None:
            raise PydanticCustomError(
                "conditional_rule",
                "conditional rule failed: {message}",
                {
                    "message": error.message,
                    "keyword": error.validator,
                    "instance_path": list(error.absolute_path),
                    "schema_path": list(error.absolute_schema_path),
                },
            )
        return model

    def json_schema(cls: Any, core_schema: Any, handler: Any) -> dict[str, Any]:
        result = handler(core_schema)
        result.update(deepcopy(normalized))
        return result

    return {
        "_validate_conditional_rules": model_validator(mode="after")(validate_rules),
        "__get_pydantic_json_schema__": classmethod(json_schema),
    }


def compile_native_conditionals(
    view: SchemaView, fragments: dict[str, dict[str, Any]], scope: str
) -> list[dict[str, Any]]:
    """Lower only the admitted generator grammar to fixed native registry data."""
    from hashlib import sha256

    from .identity import canonical_bytes

    result: list[dict[str, Any]] = []
    for name, fragment in sorted(fragments.items()):
        aliases = {
            str.__str__(slot.alias or slot.name): str(slot.name)
            for slot in view.class_induced_slots(name)
        }

        def atoms(
            expression: dict[str, Any],
            *,
            name: str = name,
            aliases: dict[str, str] = aliases,
        ) -> list[dict[str, Any]]:
            if not isinstance(expression, dict) or set(expression) - {
                "required",
                "properties",
                "not",
                "allOf",
            }:
                _refuse(name, "unsupported generated conditional expression")
            rows: list[dict[str, Any]] = []

            def atom(alias: str, presence: str, choices=None):
                if alias not in aliases:
                    _refuse(name, f"unresolved conditional alias {alias}")
                rows.append({"property": aliases[alias], "presence": presence, "choices": choices})

            for alias in expression.get("required", []):
                atom(alias, "present")
            for alias, constraint in expression.get("properties", {}).items():
                if constraint == {}:
                    continue
                if set(constraint) == {"const"} and isinstance(constraint["const"], str):
                    choices = [constraint["const"]]
                elif set(constraint) == {"enum"} and isinstance(constraint["enum"], list):
                    choices = constraint["enum"]
                    if not choices or any(not isinstance(v, str) for v in choices):
                        _refuse(name, "native choices must be nonempty strings")
                else:
                    _refuse(name, "unsupported generated property condition")
                atom(alias, "optional", choices)
            if "not" in expression:
                negated = expression["not"]
                if (
                    not isinstance(negated, dict)
                    or set(negated) != {"required"}
                    or len(negated["required"]) != 1
                ):
                    _refuse(name, "unsupported generated negation")
                atom(negated["required"][0], "absent")
            for child in expression.get("allOf", []):
                rows.extend(atoms(child))
            return rows

        def rules(node, *, name: str = name):
            if set(node) == {"allOf"}:
                for child in node["allOf"]:
                    yield from rules(child)
            elif set(node) <= {"if", "then", "else"} and "if" in node:
                yield node
            else:
                _refuse(name, "unsupported generated rule composition")

        cls = view.get_class(name)
        assert cls is not None
        for index, rule in enumerate(rules(fragment)):
            result.append(
                {
                    "class_id": view.get_uri(cls, expand=True),
                    "rule_id": sha256(canonical_bytes([name, index, rule])).hexdigest(),
                    "scope": scope,
                    "branches": {
                        branch: atoms(rule.get(branch, {})) for branch in ("if", "then", "else")
                    },
                }
            )
    return result
