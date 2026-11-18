"""LinkML-owned operation grammar and vocabulary projections of one captured model."""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, cast, get_args

from linkml.validator import Validator
from linkml.validator.plugins import JsonschemaValidationPlugin, RecommendedSlotsPlugin
from linkml.validator.report import Severity
from linkml_runtime.linkml_model.meta import (
    AnonymousSlotExpression,
    EnumDefinition,
    PermissibleValue,
)
from linkml_runtime.utils.schemaview import SchemaView

from corpus_structure.semantic.types import Diagnostic, PreparationError, SourceArtifact

if TYPE_CHECKING:
    from corpus_structure.model.compiled import CompiledModel

DECLARATION_ROOT = "operation-declarations.yaml"
_CAPTURE_PREFIX = "operation-declaration-model/"
_DECLARATION_SOURCES = (
    DECLARATION_ROOT,
    "operation-vocabularies.yaml",
    "operation-integrity-vocabularies.yaml",
    "linkml:types",
)


def declaration_sources(model: CompiledModel | None = None) -> tuple[SourceArtifact, ...]:
    """Capture the grammar used to interpret the operation declarations in a release."""
    if model is None:
        from corpus_structure.model.compiled import running_model

        model = running_model()
    return tuple(
        SourceArtifact(_CAPTURE_PREFIX + name, model.sources[name]) for name in _DECLARATION_SOURCES
    )


def captured_declaration_model(sources: tuple[SourceArtifact, ...]) -> CompiledModel | None:
    from corpus_structure.model.compiled import compiled_model

    selected = tuple(source for source in sources if source.name.startswith(_CAPTURE_PREFIX))
    if not selected:
        return None
    payload = {source.name.removeprefix(_CAPTURE_PREFIX): source.content for source in selected}
    if len(payload) != len(selected) or set(payload) != set(_DECLARATION_SOURCES):
        raise ValueError(
            "capture requires exactly the operation declaration grammar and its imports"
        )
    return compiled_model(payload)


def _annotations(value) -> dict[str, Any]:
    raw = value.annotations or {}
    items = raw.items() if hasattr(raw, "items") else vars(raw).items()
    return {str(key): getattr(annotation, "value", annotation) for key, annotation in items}


def _members(enum: EnumDefinition) -> dict[str, PermissibleValue]:
    # LinkML's constructors normalize permissible-value mappings to hydrated values.
    return cast(dict[str, PermissibleValue], enum.permissible_values or {})


@dataclass(frozen=True)
class Vocabulary:
    name: str
    openness: str
    members: frozenset[str]
    statuses: tuple[tuple[str, str | None], ...]
    annotations: Any


def _string_range(view: SchemaView, name: str | None) -> bool:
    seen = set()
    while name and name not in seen:
        seen.add(name)
        if name == "string":
            return True
        definition = view.get_type(name)
        name = str(definition.typeof) if definition and definition.typeof else None
    return False


def check_declared_openness(view: SchemaView) -> None:
    """Check declared validation/extension meaning while preserving open descriptions."""
    enums = {str(name): enum for name, enum in view.all_enums().items()}

    def refuse(location, message):
        raise PreparationError((Diagnostic("vocabulary_openness", location, message),))

    for name, enum in enums.items():
        openness = _annotations(enum).get("cs:openness")
        if openness is not None and openness not in {"closed", "pack-extensible", "open"}:
            refuse(name, "unknown declared vocabulary openness")

        def extension(expression, owner=name):
            for parent in expression.inherits or ():
                target = enums.get(str(parent))
                if target and _annotations(target).get("cs:openness") == "closed":
                    refuse(owner, "cannot extend closed vocabulary " + str(parent))
            for included in expression.include or ():
                extension(included, owner)

        extension(enum)
    for cls in view.all_classes():
        for slot in view.class_induced_slots(cls):
            alternatives = cast(list[AnonymousSlotExpression], slot.any_of or [])
            open_members = [
                str(item.range)
                for item in alternatives
                if str(item.range) in enums
                and _annotations(enums[str(item.range)]).get("cs:openness") == "open"
            ]
            plain = enums.get(str(slot.range))
            if plain and _annotations(plain).get("cs:openness") == "open":
                refuse(f"{cls}/{slot.name}", "open vocabulary requires a string alternative")
            if open_members and not any(_string_range(view, item.range) for item in alternatives):
                refuse(f"{cls}/{slot.name}", "open vocabulary requires a string alternative")
            if any(_string_range(view, item.range) for item in alternatives):
                for item in alternatives:
                    enum = enums.get(str(item.range))
                    if enum and _annotations(enum).get("cs:openness") == "closed":
                        refuse(
                            f"{cls}/{slot.name}", "closed vocabulary cannot admit arbitrary text"
                        )


class OperationDeclarations:
    """One validator/context and immutable vocabulary facts per captured model."""

    def __init__(self, model: CompiledModel):
        self.view = model.private_view(DECLARATION_ROOT)
        check_declared_openness(self.view)
        schema = self.view.schema
        if schema is None:
            raise ValueError("operation declaration schema is unavailable")
        self.validator = Validator(
            schema,
            validation_plugins=[JsonschemaValidationPlugin(closed=True), RecommendedSlotsPlugin()],
        )
        self._lock = RLock()
        self.vocabularies = MappingProxyType(
            {
                str(name): Vocabulary(
                    str(name),
                    str(_annotations(enum)["cs:openness"]),
                    frozenset(_members(enum)),
                    tuple(
                        (member, value.status if value.status else None)
                        for member, value in _members(enum).items()
                    ),
                    MappingProxyType(
                        {
                            member: _freeze(_annotations(value))
                            for member, value in _members(enum).items()
                        }
                    ),
                )
                for name, enum in self.view.all_enums().items()
                if "cs:openness" in _annotations(enum)
            }
        )

    def _structural_value(self, value, class_name):
        if not isinstance(value, dict):
            return _literal_values(value)
        slots = {str(slot.name): slot for slot in self.view.class_induced_slots(class_name)}
        result = {}
        for name, item in value.items():
            slot = slots.get(name)
            if slot is None:
                result[name] = _literal_values(item)
            elif slot.range == "OperationAny" and not slot.any_of:
                # LinkML 1.12.1 generates linkml:Any without arrays. These slots
                # explicitly delegate their payload to its semantic owner (typed
                # binding literals, JSON Schema, parameter dictionaries). Validate
                # presence/outer collection shape here without narrowing payloads.
                result[name] = (
                    [None for _ in item]
                    if slot.multivalued and isinstance(item, (tuple, list))
                    else item
                    if slot.multivalued
                    else None
                )
            elif self.view.get_class(slot.range) is not None:
                result[name] = (
                    [self._structural_value(member, slot.range) for member in item]
                    if slot.multivalued and isinstance(item, (tuple, list))
                    else self._structural_value(item, slot.range)
                )
            else:
                result[name] = _literal_values(item)
        return result

    def validate(self, value: Any, owner: str, target_class="DataOperationDeclaration"):
        diagnostics = []
        # The plugin's context lazily generates JSON Schema. One held validator
        # supplies one construction even when preparation callers overlap.
        with self._lock:
            results = tuple(
                self.validator.iter_results(
                    self._structural_value(value, target_class), target_class
                )
            )
        for result in results:
            if result.severity in {Severity.ERROR, Severity.FATAL}:
                source = result.source
                path = tuple(str(part) for part in getattr(source, "absolute_path", ()))
                message = result.message or "invalid operation declaration"
                if getattr(source, "validator", None) == "additionalProperties":
                    fields = set(source.instance) - set(source.schema.get("properties", {}))
                    message = "unsupported fields: " + ", ".join(sorted(fields))
                elif (
                    getattr(source, "validator", None) == "type"
                    and source.validator_value == "object"
                ):
                    message = "expected a string-keyed record"
                elif path and path[-1] == "operator":
                    message = "unsupported relational binding construct " + str(source.instance)
                raise PreparationError(
                    (Diagnostic("data_operation_contract", "/".join((owner, *path)), message),)
                )
            if result.type == "recommended slots" and target_class == "DataOperationDeclaration":
                # This schema has one recommended declaration. Its warning supplies the
                # consequence; the validity owner adds no independent absence warning.
                slot = self.view.induced_slot("validity_family", target_class)
                if slot.recommended and value.get("validity_family") is None:
                    diagnostics.append(
                        Diagnostic(
                            "validity_undetermined",
                            owner,
                            "validity family not declared; conservative validity applies; "
                            "declare validity_family: [<family>…] or [none]",
                            "advisory",
                        )
                    )
        if target_class == "DataOperationDeclaration":
            for field, enum_name in (("ownership", "Ownership"), ("preparation", "Preparation")):
                term = value["capabilities"][field]
                if term not in self.vocabularies[enum_name].members:
                    diagnostics.append(
                        Diagnostic(
                            field + "_unknown_term",
                            owner + "/capabilities/" + field,
                            "open vocabulary term is not assessed: " + term,
                            "advisory",
                        )
                    )
        return tuple(diagnostics)


def _literal_values(value):
    """JSON-shaped view; preserve tuple literals and semantic scalar types without coercion."""
    if isinstance(value, (tuple, list)):
        return [_literal_values(item) for item in value]
    if isinstance(value, dict):
        return {key: _literal_values(item) for key, item in value.items()}
    return value


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def declarations(model: CompiledModel | None = None) -> OperationDeclarations:
    if model is None:
        from corpus_structure.model.compiled import running_model

        model = running_model()
    return model.projection(("operation-declarations",), lambda: OperationDeclarations(model))


def vocabulary(name: str, model: CompiledModel | None = None) -> Vocabulary:
    return declarations(model).vocabularies[name]


def vocabulary_members(name: str, model: CompiledModel | None = None) -> frozenset[str]:
    return vocabulary(name, model).members


def check_literal_members(name: str, literal, model: CompiledModel | None = None) -> None:
    """A static typing copy refuses drift from its declared vocabulary."""
    actual = frozenset(get_args(getattr(literal, "__value__", literal)))
    expected = vocabulary_members(name, model)
    if actual != expected:
        raise ValueError(
            f"{name}: Python Literal differs from declared vocabulary; "
            f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
        )


def task_lifecycle(model: CompiledModel | None = None):
    """Return a private lifecycle projection of the same captured native protocol."""
    from copy import deepcopy

    from corpus_structure.semantic.data_operation_protocol import data_task_lifecycle

    if model is None:
        from corpus_structure.model.compiled import running_model

        model = running_model()
    result = model.projection(
        ("data-task-lifecycle",),
        lambda: data_task_lifecycle(model.sources["data-operation-native.yaml"]),
    )
    return deepcopy(result)
