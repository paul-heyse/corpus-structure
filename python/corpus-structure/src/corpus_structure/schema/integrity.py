"""Integrity principals projected from the captured model declarations."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from .declarations import ModelError


def annotation_values(element: Any) -> dict[str, Any]:
    """Preserve structured LinkML annotation values without stringifying them."""
    from jsonasobj2 import as_dict

    raw = getattr(element, "annotations", None) or {}
    items = raw.items() if hasattr(raw, "items") else vars(raw).items()
    return {
        str(tag): _plain_annotation(as_dict(getattr(value, "value", value))) for tag, value in items
    }


def _plain_annotation(value: Any) -> Any:
    if isinstance(value, str):
        return str.__str__(value)
    if isinstance(value, list):
        return [_plain_annotation(item) for item in value]
    if isinstance(value, dict):
        return {str.__str__(key): _plain_annotation(item) for key, item in value.items()}
    return value


@dataclass(frozen=True)
class RolePolicy:
    name: str
    key: str
    login: bool
    memberships: tuple[str, ...]
    publisher: bool
    inherit: bool | None = None


@dataclass(frozen=True)
class IntegrityPolicy:
    roles: Mapping[str, RolePolicy]
    purposes: Mapping[str, str | None]

    @property
    def publisher(self):
        return next(role.name for role in self.roles.values() if role.publisher)

    @property
    def purpose_roles(self):
        return tuple(dict.fromkeys(role for role in self.purposes.values() if role is not None))

    def role_name(self, key):
        if key == "publisher":
            return self.publisher
        purpose = {
            "writer": "write",
            "reader": "read",
            "evaluator": "evaluate",
            "admitter": "admit",
            "fitter": "fit",
        }.get(key)
        if purpose is not None:
            role = self.purpose_role(purpose)
            if role is None:
                raise ModelError([f"integrity purpose {purpose} requires a role"])
            return role
        for role in self.roles.values():
            if role.key == key:
                return role.name
        raise ModelError([f"unknown integrity role key: {key}"])

    def purpose_role(self, purpose):
        if purpose not in self.purposes:
            raise ModelError([f"unknown integrity purpose: {purpose}"])
        return self.purposes[purpose]

    def require_roles(self, roles):
        if not isinstance(roles, (list, tuple)):
            raise ModelError(["integrity read roles must be a structured list"])
        for role in roles:
            if role not in self.roles:
                raise ModelError([f"unknown integrity role: {role}"])
        return tuple(roles)


def integrity_from_view(view):
    role_enum, purpose_enum = view.get_enum("Role"), view.get_enum("Purpose")
    if role_enum is None or purpose_enum is None:
        raise ModelError(["integrity Role and Purpose declarations are required"])
    if any(
        annotation_values(enum).get("cs:openness") != "closed" for enum in (role_enum, purpose_enum)
    ):
        raise ModelError(["integrity Role and Purpose vocabularies must be closed"])
    roles = {}
    for name, member in role_enum.permissible_values.items():
        values = annotation_values(member)
        if any(key not in values for key in ("cs:login", "cs:memberships", "cs:publisher")):
            raise ModelError([f"role {name} lacks login, membership or publisher declaration"])
        if type(values["cs:login"]) is not bool or type(values["cs:publisher"]) is not bool:
            raise ModelError([f"role {name} has nonboolean login/publisher declaration"])
        inherit = values.get("cs:inherit")
        if inherit is not None and type(inherit) is not bool:
            raise ModelError([f"role {name} inheritance must be boolean"])
        memberships = values["cs:memberships"]
        if not isinstance(memberships, list) or any(not isinstance(x, str) for x in memberships):
            raise ModelError([f"role {name} memberships must be a list of roles"])
        roles[str(name)] = RolePolicy(
            str(name),
            str(name).removeprefix("corpus_sem_"),
            values["cs:login"],
            tuple(memberships),
            values["cs:publisher"],
            inherit,
        )
    if sum(role.publisher for role in roles.values()) != 1:
        raise ModelError(["integrity requires exactly one publisher role"])
    for role in roles.values():
        if any(name not in roles for name in role.memberships):
            raise ModelError([f"role {role.name} has undeclared membership"])
        if role.memberships:
            raise ModelError([f"restricted integrity role {role.name} must have no memberships"])
    purposes = {}
    for name, member in purpose_enum.permissible_values.items():
        values = annotation_values(member)
        role = values.get("cs:role")
        if role is None:
            if values.get("cs:no_role") is not True:
                raise ModelError([f"purpose {name} lacks a declared role or no-role marking"])
        elif not isinstance(role, str) or role not in roles or values.get("cs:no_role") is True:
            raise ModelError([f"purpose {name} has inconsistent role declaration"])
        purposes[str(name)] = role
    return IntegrityPolicy(MappingProxyType(roles), MappingProxyType(purposes))


def integrity():
    from corpus_structure.model.compiled import running_model

    model = running_model()
    return model.projection(
        "integrity",
        lambda: integrity_from_view(model.view("operation-integrity-vocabularies.yaml")),
    )


def role_name(key: str) -> str:
    return integrity().role_name(key)


def _schema_policies():
    from corpus_structure.model.compiled import running_model

    model = running_model()

    def project():
        view = model.view("physical.yaml", merge=False)
        policy = integrity()
        result = {}
        for name, subset in view.all_subsets().items():
            values = annotation_values(subset)
            if values.get("ph:physical_schema") is not True:
                continue
            if "ph:read_roles" not in values:
                raise ModelError([f"physical schema {name} lacks read-role default"])
            result[str(name)] = policy.require_roles(values["ph:read_roles"])
        return MappingProxyType(result)

    return model.projection("physical-schema-policies", project)


def physical_schemas():
    return tuple(_schema_policies())


def schema_read_roles(name):
    policies = _schema_policies()
    if name not in policies:
        raise ModelError([f"physical schema {name} lacks read-role default"])
    return policies[name]


def validate_relation_profile(view, annotations, name, *, profile="PhysicalRelation"):
    import json
    from copy import deepcopy

    from jsonschema import Draft7Validator
    from linkml.generators.jsonschemagen import JsonSchemaGenerator
    from linkml_runtime.linkml_model import Prefix, SchemaDefinition
    from linkml_runtime.utils.schemaview import SchemaView

    validators = getattr(view, "_physical_profile_validators", {})
    cache = validators.get(profile)
    if cache is None:
        classes = (
            "ProfileAny",
            "PhysicalRelation",
            "PhysicalColumn",
            "ForeignKey",
            "Check",
            "Index",
        )
        schema = SchemaDefinition(
            id="https://corpus-structure.org/physical-profile",
            name="physical_profile",
            prefixes={
                "linkml": Prefix(
                    prefix_prefix="linkml", prefix_reference="https://w3id.org/linkml/"
                ),
                "ph": Prefix(
                    prefix_prefix="ph", prefix_reference="https://corpus-structure.org/physical/"
                ),
            },
            default_prefix="ph",
            default_range="string",
            classes={key: deepcopy(view.get_class(key)) for key in classes},
            types=deepcopy(view.all_types()),
            enums={"FrontierGuard": deepcopy(view.get_enum("FrontierGuard"))},
        )
        profile_view = SchemaView(schema)
        generator = JsonSchemaGenerator(
            schema, schemaview=profile_view, top_class=profile, include_null=False
        )
        cache = Draft7Validator(json.loads(generator.serialize()))
        validators[profile] = cache
        view._physical_profile_validators = validators
    validator = cache
    value = {
        key.removeprefix("ph:"): item for key, item in annotations.items() if key.startswith("ph:")
    }
    if "indexes" in value:
        value["indexes"] = [
            index if isinstance(index, dict) else {"columns": index} for index in value["indexes"]
        ]
    errors = tuple(validator.iter_errors(value))
    if errors:
        raise ModelError([f"{name}: invalid physical profile: {error.message}" for error in errors])


def relation_annotations(view, name) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for ancestor in reversed(view.class_ancestors(str(name), reflexive=True)):
        result.update(annotation_values(view.get_class(ancestor)))
    return result
