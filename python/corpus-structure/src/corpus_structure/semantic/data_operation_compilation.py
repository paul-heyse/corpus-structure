"""Pure phased compilation of declaration/Python operation authoring into one IR.

This is an opt-in foundation. It grants no runtime capability and changes no native
routing. All referenced assets, Python modules and LinkML imports must be supplied.
"""

from __future__ import annotations

import ast
import json
from dataclasses import asdict, fields, replace
from typing import TYPE_CHECKING, Any, Never, cast, get_args

import yaml
from linkml_runtime.dumpers import json_dumper
from linkml_runtime.utils.yamlutils import DupCheckYamlLoader

from corpus_structure.schema.operation_declarations import (
    OperationDeclarations,
    captured_declaration_model,
)
from corpus_structure.schema.operation_declarations import (
    declarations as operation_declarations,
)

from .data_operation_json import json_loads, scope_identity, wire_json_loads
from .data_operation_model import (
    BindingExpression,
    BindingField,
    BindingOperand,
    ConsumerSelectionCapability,
    CoverageContract,
    CoverageResultOwner,
    EffectContract,
    EffectiveDataOperationModel,
    EffectiveIdentity,
    EffectiveKind,
    EffectiveOperation,
    EnforcementClaim,
    ExternalExecutorContract,
    FactOrigin,
    ImplementationCapabilities,
    InputCoverage,
    InputSupport,
    NumericalPolicyReference,
    OpaqueBoundary,
    OperationRole,
    RelationalBinding,
    ReplicatePolicy,
    SemanticEdge,
    SemanticNode,
    SourceUnknown,
    StateDimension,
    StateTransition,
    StreamSettlement,
    SubjectDefinition,
    SubjectScope,
    ValidityClaim,
    compiled_graph_projections,
    operation_role_record,
    validate_replicate_selection,
    validate_subject_context,
    validate_subject_source,
)
from .data_operation_version import MODEL_VERSION
from .data_operation_wire import checked_json_schema, json_schema_category
from .identity import canonical_bytes
from .python_operation_sources import ClosedPythonSources, PythonSourceCollection
from .types import (
    ClassDefinition,
    Diagnostic,
    PreparationError,
    PropertyDefinition,
    SourceArtifact,
    SourceBundle,
    VocabularyMember,
    VocabularySnapshot,
)

if TYPE_CHECKING:
    from corpus_structure.model.compiled import CompiledModel

_PRIMITIVES = {
    "string",
    "integer",
    "boolean",
    "float",
    "double",
    "decimal",
    "date",
    "datetime",
    "uri",
    "uriorcurie",
    "bytes",
    "json",
}


def _fail(location: str, message: str, code: str = "data_operation_contract") -> Never:
    raise PreparationError((Diagnostic(code, location, message),))


def _source_values(value: Any) -> Any:
    """Lower only the location-carrying YAML scalar subclasses, preserving type meaning."""
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, str):
        return str.__str__(value)
    if isinstance(value, int):
        return int.__int__(value)
    if isinstance(value, float):
        return float.__float__(value)
    if isinstance(value, list):
        return [_source_values(item) for item in value]
    if isinstance(value, dict):
        return {_source_values(key): _source_values(item) for key, item in value.items()}
    return value


def _mapping(value: Any, location: str, allowed: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        _fail(location, "expected a string-keyed record")
    if allowed is not None and value.keys() - allowed:
        _fail(location, "unsupported fields: " + ", ".join(sorted(value.keys() - allowed)))
    return value


def _strings(value: Any, location: str, *, empty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or any(
        not isinstance(item, str) or not item for item in value
    ):
        _fail(location, "expected explicit string references")
    if len(set(value)) != len(value) or (not empty and not value):
        _fail(location, "references must be distinct" + (" and nonempty" if not empty else ""))
    return tuple(value)


def _text(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(location, "expected nonempty semantic value")
    return value


def _expression(value: Any, operation: str, roles: set[str]) -> BindingExpression:
    value = _mapping(
        value,
        operation + "/binding",
    )
    operator = value.get("operator")
    impact = value.get("impact", "result")
    if impact not in {"result", "eligibility"}:
        _fail(operation, "binding predicate requires result/eligibility semantics")
    selected_roles = _strings(value.get("roles", []), operation + "/binding/roles")
    if not set(selected_roles) <= roles:
        _fail(operation, "binding uses an undeclared role")
    fields = []
    for record in value.get("fields", []):
        record = _mapping(record, operation)
        if record.get("role") not in roles:
            _fail(operation, "binding field uses an undeclared role")
        fields.append(
            BindingField(
                *(
                    _text(record.get(key), operation + "/binding/" + key)
                    for key in ("role", "projection", "field")
                )
            )
        )
    if operator in {"same", "distinct", "join"} and len(selected_roles) < 2:
        _fail(operation, operator + " requires at least two explicit roles")
    if operator in {"join", "equal"} and len(fields) < 2 and not value.get("operands"):
        _fail(operation, operator + " requires qualified projection fields")
    if operator == "literal" and (len(fields) != 1 or "value" not in value):
        _fail(operation, "literal predicates require one field and a typed literal")
    if operator in {"forall", "absent"} and not value.get("population"):
        _fail(operation, "absence/quantification requires an explicitly closed population")
    if operator == "choice" and not (value.get("selected") or value.get("choice_parameter")):
        _fail(operation, "alternatives require an explicit selected alternative")
    if operator == "choice" and value.get("selected") and value.get("choice_parameter"):
        _fail(operation, "alternatives require exactly one static or frozen demand selector")
    minimum, maximum = value.get("minimum"), value.get("maximum")
    if minimum is not None and (type(minimum) is not int or minimum < 0):
        _fail(operation, "invalid minimum cardinality")
    if maximum is not None and (type(maximum) is not int or maximum < (minimum or 0)):
        _fail(operation, "incompatible cardinality")
    collection = value.get("collection")
    if collection is not None and collection not in {"scalar", "sequence", "bag", "set"}:
        _fail(operation, "unsupported collection meaning")
    children = tuple(_expression(child, operation, roles) for child in value.get("children", []))
    if operator in {"choice", "optional", "forall"} and not children:
        _fail(operation, operator + " requires a nested binding")
    from .value_codec import value_meaning

    literal = None
    if "value" in value:
        # Typed semantic codec, including explicit float/decimal lexical representations.
        from .value_codec import value_meaning

        literal = canonical_bytes(value_meaning(value["value"]))
    operands = []
    for operand in value.get("operands", []):
        operand = _mapping(
            operand,
            operation + "/operand",
        )
        kind = operand.get("kind")
        if kind not in {"field", "literal", "parameter", "population"}:
            _fail(operation, "unsupported binding operand")
        value_type = _text(operand.get("value_type"), operation + "/operand/type")
        allowed = {
            "kind",
            "value_type",
            "field" if kind == "field" else "value" if kind == "literal" else "name",
        }
        if kind == "population" and "population_projection" in operand:
            allowed.add("population_projection")
        projection_mode = operand.get("population_projection", "member")
        if projection_mode not in {"member", "qualified-context"}:
            _fail(operation, "unsupported population projection")
        if projection_mode == "qualified-context" and value_type != "subject-context":
            _fail(operation, "qualified-context population requires subject-context type")
        if set(operand) != allowed:
            _fail(operation, "operand fields do not match its declared source kind")
        field = None
        if kind == "field":
            raw_field = _mapping(operand.get("field"), operation)
            if raw_field.get("role") not in roles:
                _fail(operation, "binding operand uses an undeclared role")
            field = BindingField(
                *(_text(raw_field.get(key), operation) for key in ("role", "projection", "field"))
            )
        if kind in {"parameter", "population"} and not operand.get("name"):
            _fail(operation, "named operand requires a frozen demand key")
        if kind == "literal" and "value" not in operand:
            _fail(operation, "literal operand requires a value")
        if kind != "literal" and "value" in operand:
            _fail(operation, "only literal operands may contain a value")
        operands.append(
            BindingOperand(
                cast(Any, kind),
                value_type,
                field,
                operand.get("name"),
                canonical_bytes(value_meaning(operand["value"])) if kind == "literal" else None,
                cast(Any, projection_mode),
            )
        )
    if operator == "range" and len(operands) != 3:
        _fail(operation, "range requires typed value, inclusive lower and upper operands")
    if operator == "membership" and len(operands) != 2:
        _fail(operation, "membership requires typed value and collection operands")
    if operator == "membership" and operands[1].kind == "field":
        _fail(operation, "membership universe requires a frozen sequence or population")
    if operator == "covers" and (
        len(operands) != 2
        or operands[0].kind != "field"
        or operands[1].kind not in {"parameter", "literal", "population"}
    ):
        _fail(operation, "covers requires a qualified scalar field and frozen sequence")
    if operator in {"equal", "join"} and operands and len(operands) < 2:
        _fail(operation, "equality requires two or more operands")
    return BindingExpression(
        cast(Any, operator),
        selected_roles,
        tuple(fields),
        literal,
        children,
        minimum,
        maximum,
        collection,
        value.get("selected"),
        value.get("population"),
        impact,
        tuple(operands),
        value.get("choice_parameter"),
    )


def _kind_policies(
    universe: Any, families: Any, owner: str, grammar: OperationDeclarations
) -> dict[str, Any]:
    """Normalize explicit kind-owned access/projection capabilities once."""
    if (
        not isinstance(universe, str)
        or universe not in grammar.vocabularies["KindUniverse"].members
    ):
        _fail(owner, "kind universe must be ordinary, source or evaluator")
    if not isinstance(families, (list, tuple)) or any(
        not isinstance(family, str)
        or family not in grammar.vocabularies["ProjectionFamily"].members
        for family in families
    ):
        _fail(owner, "projection_families must be an array of supported projection family names")
    if len(set(families)) != len(families):
        _fail(owner, "projection_families must not contain duplicates")
    return {"universe": universe, "projection_families": sorted(families)}


def _annotation_kind_policies(
    annotations: dict[str, str], owner: str, grammar: OperationDeclarations
) -> dict[str, Any]:
    try:
        families = json.loads(annotations.get("cs:projection_families", "[]"))
    except (ValueError, TypeError) as exc:
        _fail(owner, "cs:projection_families must be a JSON array string: " + str(exc))
    return _kind_policies(annotations.get("cs:data_universe", "ordinary"), families, owner, grammar)


def _kind_products(
    bundle: SourceBundle | None,
    definitions: tuple[ClassDefinition, ...] | None,
    vocabularies: tuple[VocabularySnapshot, ...],
    grammar: OperationDeclarations,
):
    kinds: dict[str, EffectiveKind] = {}
    nodes: dict[str, SemanticNode] = {}
    edges: list[SemanticEdge] = []
    aliases: dict[str, str] = {}

    def add_kind(kind: EffectiveKind) -> None:
        if kind.semantic_id in kinds:
            _fail(kind.semantic_id, "duplicate schema semantic identity")
        kinds[kind.semantic_id] = kind

    for name in sorted(_PRIMITIVES):
        semantic_id = "primitive:" + name
        add_kind(
            EffectiveKind(
                semantic_id,
                name,
                "primitive",
                canonical_bytes(
                    {"primitive": name, **_kind_policies("ordinary", [], semantic_id, grammar)}
                ),
            )
        )
        aliases[name] = semantic_id
    if bundle is not None:
        from .conditional_rules import CONDITIONAL_RULE_OPTIONS, compile_conditional_rules
        from .prepare import _view, effective_class_definitions, enum_requires_vocabulary
        from .types import PreparationProfile

        profile = PreparationProfile(version="semantic-2")
        view = _view(bundle, profile)
        rule_fragments = compile_conditional_rules(view)
        if definitions is None:
            definitions = effective_class_definitions(view, profile, view.all_enums())
        for definition in definitions:
            aliases[definition.name] = definition.iri
        for enum_name, enum in view.all_enums().items():
            aliases[enum_name] = view.expand_curie(str(enum.enum_uri))
        declared_types = {}
        for source in bundle.sources:
            raw_source = yaml.load(source.content, Loader=DupCheckYamlLoader)
            for name in raw_source.get("types", {}):
                declared_types[str(name)] = "type:" + str(raw_source["id"]) + "#" + str(name)
        for name in view.all_types():
            aliases[name] = declared_types[name]
        source_map = {}
        for source in bundle.sources:
            raw = yaml.load(source.content, Loader=DupCheckYamlLoader)
            for category in ("classes", "slots", "types", "enums"):
                for name in raw.get(category, {}):
                    source_map[category, name] = source.name
        for definition in definitions:
            origins = (
                FactOrigin(
                    "definition",
                    "extracted",
                    source_map.get(("classes", definition.name), bundle.root),
                    definition.name,
                ),
            )
            facts: dict[str, Any] = asdict(definition)
            facts["properties"] = []
            from .prepare import _annotations

            annotations = _annotations(view.get_class(definition.name))
            facts["source_scope"] = annotations.get("cs:scope", "global")
            facts["case_policy"] = annotations.get("cs:case", "preserve")
            facts.update(_annotation_kind_policies(annotations, definition.iri, grammar))
            facts["policies"] = {
                key: value
                for key, value in annotations.items()
                if key not in {"cs:data_universe", "cs:projection_families"}
            }
            if definition.name in rule_fragments:
                facts["conditional_rules"] = rule_fragments[definition.name]
                facts["conditional_interpretation"] = CONDITIONAL_RULE_OPTIONS
            for prop in definition.properties:
                property_id = definition.iri + "/property/" + prop.name
                prop_facts = asdict(prop)
                prop_facts["range"] = aliases.get(prop.range, prop.range)
                prop_facts["policies"] = _annotations(view.induced_slot(prop.name, definition.name))
                declaring_class = next(
                    (
                        name
                        for name in (definition.name, *definition.ancestors)
                        if (parent_definition := view.get_class(name)) is not None
                        and prop.name in (parent_definition.attributes or {})
                    ),
                    None,
                )
                declaration_source = (
                    source_map.get(("classes", declaring_class), bundle.root)
                    if declaring_class
                    else source_map.get(("slots", prop.name), bundle.root)
                )
                property_origins = (
                    FactOrigin(
                        "definition",
                        "extracted",
                        declaration_source,
                        (declaring_class + "." if declaring_class else "slot:") + prop.name,
                    ),
                )
                add_kind(
                    EffectiveKind(
                        property_id,
                        definition.name + "." + prop.name,
                        "property",
                        canonical_bytes(prop_facts),
                        property_origins,
                    )
                )
                edges.append(SemanticEdge(definition.iri, property_id, "property", prop.name))
                if prop.range not in aliases:
                    _fail(property_id, "unresolved effective property range " + prop.range)
                edges.append(SemanticEdge(property_id, aliases[prop.range], "range"))
                if prop.inverse:
                    # Inverse relationships are effective meaning,
                    # rather than producer dependencies.
                    prop_facts["inverse"] = prop.inverse
                    edges.append(
                        SemanticEdge(
                            property_id,
                            aliases[prop.range] + "/property/" + prop.inverse,
                            "inverse",
                        )
                    )
            add_kind(
                EffectiveKind(
                    definition.iri, definition.name, "class", canonical_bytes(facts), origins
                )
            )
            for parent in definition.ancestors:
                edges.append(SemanticEdge(definition.iri, aliases[parent], "inherits"))
        for name, enum in view.all_enums().items():
            semantic_id = aliases[name]
            facts = cast(dict[str, Any], json_dumper.to_dict(enum))
            facts["enum_uri"] = semantic_id
            for member in facts.get("permissible_values", {}).values():
                if member.get("meaning"):
                    member["meaning"] = view.expand_curie(str(member["meaning"]))
                member.pop("from_schema", None)
            snapshot = next((item for item in vocabularies if item.enum == name), None)
            if snapshot is not None:
                facts["effective_members"] = [asdict(member) for member in snapshot.members]
                facts["unchecked"] = snapshot.unchecked
            elif enum_requires_vocabulary(enum):
                _fail(
                    semantic_id,
                    "external enum closure requires an explicitly supplied effective vocabulary",
                )
            facts.pop("from_schema", None)
            facts.pop("description", None)
            add_kind(
                EffectiveKind(
                    semantic_id,
                    name,
                    "enum",
                    canonical_bytes(facts),
                    (
                        FactOrigin(
                            "definition",
                            "extracted",
                            source_map.get(("enums", name), bundle.root),
                            name,
                        ),
                    ),
                )
            )
        for name, typ in view.all_types().items():
            semantic_id = aliases[name]
            facts = cast(dict[str, Any], json_dumper.to_dict(typ))
            facts["uri"] = view.expand_curie(str(typ.uri)) if typ.uri else None
            from .prepare import _primitive

            facts["effective_primitive"] = _primitive(view, name).__name__
            if typ.typeof:
                facts["typeof"] = aliases.get(str(typ.typeof), str(typ.typeof))
            facts.pop("from_schema", None)
            facts.pop("description", None)
            add_kind(
                EffectiveKind(
                    semantic_id,
                    name,
                    "type",
                    canonical_bytes(facts),
                    (
                        FactOrigin(
                            "definition",
                            "extracted",
                            source_map.get(("types", name), bundle.root),
                            name,
                        ),
                    ),
                )
            )
            if typ.typeof:
                if str(typ.typeof) not in aliases:
                    _fail(name, "unresolved effective type parent " + str(typ.typeof))
                edges.append(SemanticEdge(semantic_id, aliases[str(typ.typeof)], "inherits"))
    return kinds, nodes, edges, aliases


def _validate_binding_fields(
    expression: BindingExpression,
    roles: dict[str, OperationRole],
    kinds: dict[str, EffectiveKind],
    aliases: dict[str, str],
    owner: str,
) -> None:
    ranges = []
    for field in (
        *expression.fields,
        *(operand.field for operand in expression.operands if operand.field is not None),
    ):
        projection = aliases.get(field.projection, field.projection)
        if projection not in kinds:
            _fail(owner, "unresolved binding projection " + field.projection)
        if projection != roles[field.role].kind:
            _fail(owner, "binding projection differs from its qualified role kind")
        if field.field == "@context":
            ranges.append("subject-context")
            continue
        if field.field in {"@product", "@member"}:
            ranges.append("primitive:string")
            continue
        property_id = projection + "/property/" + field.field
        if property_id not in kinds:
            _fail(owner, "unresolved binding projection field " + property_id)
        ranges.append(json.loads(kinds[property_id].facts)["range"])
    for operand in expression.operands:
        expected = aliases.get(operand.value_type, operand.value_type)
        if expected == "subject-context":
            if not (
                (
                    operand.kind == "field"
                    and operand.field is not None
                    and operand.field.field == "@context"
                )
                or (
                    operand.kind == "population"
                    and operand.population_projection == "qualified-context"
                )
            ):
                _fail(
                    owner,
                    "subject-context operands require native context fields or population projection",
                )
            continue
        if expected not in kinds:
            _fail(owner, "unresolved operand type " + operand.value_type)
        if operand.kind == "literal":
            many = expression.operator == "membership" and operand is expression.operands[-1]
            synthetic = EffectiveKind(
                owner + "/literal",
                "literal",
                "property",
                canonical_bytes(
                    asdict(
                        PropertyDefinition(
                            "value",
                            owner + "/literal",
                            expected,
                            True,
                            many,
                            None,
                            None,
                            None,
                            None,
                            None,
                            False,
                            nullable=False,
                        )
                    )
                ),
            )
            _validate_literal(
                BindingExpression("literal", value=operand.value), kinds[expected], synthetic, owner
            )
        if operand.field is not None:
            if operand.field.field in {"@product", "@member"}:
                if expected != "primitive:string":
                    _fail(owner, "native header binding fields require the primitive string type")
                continue
            property_id = (
                aliases.get(operand.field.projection, operand.field.projection)
                + "/property/"
                + operand.field.field
            )
            if json.loads(kinds[property_id].facts)["range"] != expected:
                _fail(owner, "operand type differs from projected field range")
    if (
        expression.operator in {"equal", "join", "range", "membership", "covers"}
        and expression.operands
    ):
        types = {
            aliases.get(operand.value_type, operand.value_type) for operand in expression.operands
        }
        if len(types) != 1:
            _fail(owner, "binding operands require compatible element types")
    if expression.operator == "literal":
        _validate_literal(
            expression,
            kinds[ranges[0]],
            kinds[
                aliases.get(expression.fields[0].projection, expression.fields[0].projection)
                + "/property/"
                + expression.fields[0].field
            ],
            owner,
        )
    if expression.operator in {"join", "equal"} and len(set(ranges)) > 1:
        _fail(owner, "binding equality requires compatible typed fields")
    if (
        expression.operator == "cardinality"
        and expression.minimum is None
        and expression.maximum is None
    ):
        _fail(owner, "cardinality predicates require an explicit bound")
    if expression.operator == "collection" and expression.collection is None:
        _fail(owner, "collection predicates require explicit collection meaning")
    if expression.operator == "scan" and not expression.roles:
        _fail(owner, "role scans require explicit roles")
    if (
        expression.operator == "choice"
        and expression.selected is not None
        and expression.selected not in roles
    ):
        _fail(owner, "selected alternative must name a declared role")
    for child in expression.children:
        _validate_binding_fields(child, roles, kinds, aliases, owner)


def _validate_literal(
    expression: BindingExpression, kind: EffectiveKind, property_kind: EffectiveKind, owner: str
) -> None:
    """Use the production field-boundary authority for typed predicate literals."""
    from datetime import date, datetime
    from decimal import Decimal

    from .boundary import build_boundary_adapters
    from .prepare import _PRIMITIVES

    def decode(value):
        tag = value[0]
        if tag == "null":
            return None
        if tag in {"string", "boolean"}:
            return value[1]
        if tag == "integer":
            return int(value[1])
        if tag == "float":
            return float.fromhex(value[1])
        if tag == "decimal":
            return Decimal(value[1])
        if tag == "date":
            return date.fromisoformat(value[1])
        if tag == "datetime":
            return datetime.fromisoformat(value[1])
        if tag == "sequence":
            return tuple(decode(item) for item in value[1])
        if tag == "mapping":
            return {name: decode(item) for name, item in value[1]}
        _fail(owner, "unsupported semantic literal tag " + tag)

    facts = json.loads(kind.facts)
    prop_facts = json.loads(property_kind.facts)
    wire_schema = prop_facts.get("json_schema", facts.get("json_schema"))
    if wire_schema is not None:
        from .data_operation_wire import validate_wire_schema

        def wire_json(value):
            # The semantic sequence codec uses tuples internally; this explicit
            # wire lowering restores JSON arrays without converting typed values.
            if isinstance(value, tuple):
                return [wire_json(item) for item in value]
            if isinstance(value, dict):
                return {name: wire_json(item) for name, item in value.items()}
            return value

        if expression.value is None:
            _fail(owner, "typed binding literal requires an explicit value")
        try:
            validate_wire_schema(wire_schema, wire_json(decode(json.loads(expression.value))))
        except (TypeError, ValueError) as exc:
            _fail(
                owner,
                "typed binding literal violates its effective wire field contract: " + str(exc),
            )
        return
    prop = PropertyDefinition(
        **{field.name: prop_facts[field.name] for field in fields(PropertyDefinition)}
    )
    prop = replace(prop, name="value", required=True)
    primitives = {}
    vocabularies = ()
    if kind.category == "enum":
        members = facts.get("effective_members")
        if members is None:
            members = [
                {"value": name, "meaning": member.get("meaning"), "label": member.get("text")}
                for name, member in facts.get("permissible_values", {}).items()
            ]
        vocabularies = (
            VocabularySnapshot(
                prop.range,
                tuple(VocabularyMember(**member) for member in members),
                "effective-kind",
            ),
        )
    elif kind.category == "class":
        if prop.inlined:
            _fail(owner, "inlined object literals require a declared typed product predicate")
        primitives[prop.range] = str
    else:
        primitive = facts.get("primitive") or facts.get("effective_primitive")
        by_name = {value.__name__: value for value in _PRIMITIVES.values()}
        representation = _PRIMITIVES.get(primitive) or by_name.get(primitive)
        if representation is None:
            _fail(owner, "literal range has no admitted scalar representation")
        primitives[prop.range] = representation
    definition = ClassDefinition(
        "BindingLiteral", "urn:corpus:compiler:binding-literal", (), (prop,), ()
    )
    try:
        ((_, adapter),) = build_boundary_adapters(
            (definition,),
            vocabularies,
            primitive_types=primitives,
            aliases={},
            conditional_fragments={},
        )
        assert expression.value is not None
        adapter.validate_python({"value": decode(json.loads(expression.value))}, strict=True)
    except (ValueError, TypeError) as exc:
        _fail(owner, "typed binding literal violates its effective field contract: " + str(exc))


def _validity_claim(raw, grammar, owner, diagnostics):
    values = raw.get("validity_family")
    if values is None:
        return ValidityClaim()
    if not values or len(values) != len(set(values)):
        _fail(owner, "validity_family requires a nonempty set of distinct claims")
    sentinels = {"none", "undetermined"} & set(values)
    if sentinels and len(values) != 1:
        _fail(owner, "validity_family cannot mix none or undetermined with other claims")
    if values == ["none"]:
        return ValidityClaim((), False)
    if values == ["undetermined"]:
        diagnostics.append(
            Diagnostic(
                "validity_undetermined",
                owner,
                "validity family not declared; conservative validity applies",
                "advisory",
                remedy="declare validity_family: [<family>…] or [none]",
            )
        )
        return ValidityClaim()
    vocabulary = grammar.vocabularies["ValidityFamily"]
    statuses = dict(vocabulary.statuses)
    provisional = sorted(value for value in values if statuses.get(value) == "provisional")
    if provisional:
        diagnostics.append(
            Diagnostic(
                "validity_family_provisional",
                owner,
                "conservative validity applies to provisional families: " + ", ".join(provisional),
                "advisory",
            )
        )
    for value in values:
        if value in provisional:
            continue
        requirements = vocabulary.annotations[value].get("cs:requirements", {})
        for field, allowed in requirements.items():
            actual = raw.get(field)
            if field in {"forms", "preparation"}:
                actual = raw["capabilities"].get(field)
            if field == "effects_empty":
                actual = not raw.get("effects", [])
            if isinstance(actual, list):
                actual = tuple(actual)
            if actual not in allowed:
                _fail(owner, f"validity family {value} requires {field} within {allowed!r}")
    return ValidityClaim(tuple(sorted(set(values) - set(provisional))), bool(provisional))


def compile_data_operations(
    schema: SourceBundle | None = None,
    declarations: tuple[SourceArtifact, ...] = (),
    python_sources: PythonSourceCollection | None = None,
    *,
    definitions: tuple[ClassDefinition, ...] | None = None,
    vocabularies: tuple[VocabularySnapshot, ...] = (),
    captured_contracts: tuple[SourceArtifact, ...] = (),
    declaration_model: CompiledModel | None = None,
) -> EffectiveDataOperationModel:
    """Compile supplied inputs without importing candidate code or ambient models.

    Authored JSON-schema kinds own closed JSON shape. An explicit nominal_namespace
    allows local definition ranges only when that entire namespace belongs to one
    supplied source artifact. Producer implementation custody separately owns Python
    validators and algorithms that JSON Schema cannot express.
    """
    declaration_grammar = operation_declarations(
        declaration_model
        if declaration_model is not None
        else captured_declaration_model(captured_contracts)
    )
    diagnostics: list[Diagnostic] = []
    kinds, nodes, edges, aliases = _kind_products(
        schema, definitions, vocabularies, declaration_grammar
    )
    supplied_contracts = {}
    for artifact in (
        *captured_contracts,
        *(python_sources.boundary_contracts if python_sources is not None else ()),
    ):
        previous = supplied_contracts.get(artifact.name)
        if previous is not None and previous.content != artifact.content:
            _fail(artifact.name, "captured semantic contracts disagree on exact source bytes")
        supplied_contracts[artifact.name] = artifact
    frontend = ClosedPythonSources(python_sources) if python_sources is not None else None
    python_facts = frontend.operations() if frontend is not None else ()
    authored: list[tuple[dict[str, Any], tuple, tuple[FactOrigin, ...], str | None]] = []
    slices = []
    seen_sources: set[str] = set()
    kind_documents: list[tuple[dict[str, Any], tuple, tuple[FactOrigin, ...], None]] = []
    for source in declarations:
        if source.name in seen_sources:
            _fail(source.name, "duplicate operation declaration input")
        seen_sources.add(source.name)
        try:
            raw = _source_values(yaml.load(source.content, Loader=DupCheckYamlLoader))
        except (ValueError, yaml.YAMLError) as exc:
            _fail(source.name, str(exc))
        raw = _mapping(raw, source.name)
        declaration_grammar.validate(raw, source.name, "DataOperationDocument")
        if raw.get("version") != MODEL_VERSION:
            _fail(source.name, "unsupported operation declaration version")
        if raw.get("kinds") and not raw.get("operations"):
            kind_documents.append(
                (raw, (), (FactOrigin("kind", "authored", source.name, source.name),), None)
            )
        for value in raw.get("operations", []):
            value = dict(_mapping(value, source.name))
            if "kinds" in value:
                _fail(source.name, "declaration kinds belong to the document, not each operation")
            value["kinds"] = raw.get("kinds", [])
            authored.append(
                (
                    value,
                    (),
                    (FactOrigin("definition", "authored", source.name, str(value.get("id"))),),
                    None,
                )
            )
    if frontend is not None:
        for facts in python_facts:
            slices.append(facts.implementation)
            authored.append(
                (
                    json.loads(facts.metadata),
                    facts.surfaces,
                    facts.origins,
                    facts.implementation.root,
                )
            )
    selections = [item for item in captured_contracts if item.name == "operation-selection.json"]
    if len(selections) > 1:
        _fail("operation-selection", "duplicate requested-operation selection")
    if selections:
        requested = json.loads(selections[0].content)
        if (
            not isinstance(requested, list)
            or not requested
            or any(not isinstance(i, str) for i in requested)
        ):
            _fail("operation-selection", "requested operations require a nonempty identifier list")
        by_id = {}
        for value in authored:
            identifier = value[0].get("id")
            if identifier in by_id:
                _fail(str(identifier), "duplicate operation semantic identity")
            by_id[identifier] = value
        selected = set()
        pending = list(requested)
        while pending:
            identifier = pending.pop()
            if identifier in selected:
                continue
            if identifier not in by_id:
                _fail(identifier, "requested operation closure is outside captured sources")
            selected.add(identifier)
            operation = by_id[identifier][0]
            pending.extend(
                (*operation.get("dependencies", ()), *operation.get("potential_dependencies", ()))
            )
        # Protocol infrastructure remains available through its fixed native projection.
        selected.update(
            identifier
            for identifier, value in by_id.items()
            if str(value[0].get("behavior", "")).startswith("ddo-native-v1:")
        )
        for value in authored:
            if value[0].get("id") not in selected and value[0].get("kinds"):
                kind_documents.append(({"kinds": value[0]["kinds"]}, (), value[2], None))
        authored = [value for value in authored if value[0].get("id") in selected]
        roots = {value[3] for value in authored if value[3] is not None}
        slices = [part for part in slices if part.root in roots]
    # Validate shape once before any semantic pass consumes nested records.
    for raw, _, _, _ in authored:
        diagnostics.extend(declaration_grammar.validate(raw, str(raw.get("id", "operation"))))
    # Register all semantic kind owners before resolving any operation/role references.
    namespace_owners = {}
    for raw, _, origins, _ in (*authored, *kind_documents):
        for record in raw.get("kinds", []):
            declaration_grammar.validate(record, "kinds", "OperationKind")
            record = _mapping(
                record,
                "kinds",
            )
            semantic_id = _text(record.get("id"), "kind/id")
            namespace = record.get("nominal_namespace")
            if namespace is not None:
                namespace = _text(namespace, semantic_id + "/nominal_namespace")
                if (
                    record.get("json_schema") is None
                    or not semantic_id.startswith(namespace)
                    or not namespace.endswith((":", "/", "#"))
                    or namespace in {"primitive:", "urn:corpus:data-wire:"}
                ):
                    _fail(
                        semantic_id, "nominal schema namespace requires its own closed schema owner"
                    )
                owner = frozenset(origin.source for origin in origins)
                if namespace in namespace_owners and namespace_owners[namespace] != owner:
                    _fail(semantic_id, "nominal schema namespace has conflicting source owners")
                namespace_owners[namespace] = owner
            if record.get("json_schema") is not None:
                try:
                    checked_json_schema(record["json_schema"])
                except (ValueError, TypeError) as exc:
                    _fail(semantic_id, "invalid closed wire schema: " + str(exc))
                if record.get("python") or record.get("primitive"):
                    _fail(
                        semantic_id,
                        "wire schema kind cannot claim a second representation authority",
                    )
            facts = {
                **record,
                **_kind_policies(
                    record.get("universe", "ordinary"),
                    record.get("projection_families", []),
                    semantic_id,
                    declaration_grammar,
                ),
            }
            if record.get("python"):
                if frontend is None:
                    _fail(semantic_id, "Python kind facts require supplied Python sources")
                facts["effective_python"] = frontend.kind_facts(record["python"])
            if record.get("primitive") and record["primitive"] not in _PRIMITIVES:
                _fail(semantic_id, "unsupported primitive kind")
            unknowns = tuple(
                SourceUnknown(**item)
                for item in facts.get("effective_python", {}).get("unknowns", ())
            )
            kind = EffectiveKind(
                semantic_id,
                record.get("name", semantic_id),
                json_schema_category(record["json_schema"])
                if record.get("json_schema") is not None
                else "class"
                if record.get("python")
                else "primitive",
                canonical_bytes(facts),
                origins,
                not unknowns,
                unknowns,
            )
            if semantic_id in kinds:
                if kinds[semantic_id].facts != kind.facts:
                    _fail(semantic_id, "duplicate semantic kind ownership")
                continue  # document-level kind facts are shared by every operation
            kinds[semantic_id] = kind
            aliases[semantic_id] = semantic_id
            for target in record.get("references", []):
                edges.append(SemanticEdge(semantic_id, target, "type_reference"))
    # Python and schema authoring share the same property graph. Annotation text
    # remains evidence; only this closed type vocabulary acquires a resolved range.
    python_types = {
        json.loads(kind.facts).get("python"): kind.semantic_id
        for kind in kinds.values()
        if json.loads(kind.facts).get("python")
    }
    primitive_types = {
        "str": "string",
        "int": "integer",
        "bool": "boolean",
        "float": "float",
        "bytes": "bytes",
        "Decimal": "decimal",
        "date": "date",
        "datetime": "datetime",
    }
    for kind in tuple(kinds.values()):
        for field in json.loads(kind.facts).get("effective_python", {}).get("fields", []):
            annotation = field["annotation"] or ""
            nullable = annotation.endswith(" | None")
            value_annotation = annotation.removesuffix(" | None")
            multivalued = value_annotation.startswith(("list[", "tuple[", "set[", "frozenset["))
            element = (
                value_annotation.split("[", 1)[1].rsplit("]", 1)[0]
                if multivalued
                else value_annotation
            )
            element = element.replace(", ...", "")
            target = (
                python_types.get(element)
                or aliases.get(element)
                or ("primitive:" + primitive_types[element] if element in primitive_types else None)
            )
            if target is None:
                unknown = SourceUnknown(
                    str(json.loads(kind.facts).get("python")),
                    field["owner"],
                    "unresolved Python kind field annotation: " + annotation,
                    True,
                )
                kinds[kind.semantic_id] = replace(
                    kinds[kind.semantic_id],
                    complete=False,
                    unknowns=(*kinds[kind.semantic_id].unknowns, unknown),
                )
                continue
            property_id = kind.semantic_id + "/property/" + field["name"]
            kinds[property_id] = EffectiveKind(
                property_id,
                field["name"],
                "property",
                canonical_bytes(
                    {
                        **asdict(
                            PropertyDefinition(
                                field["name"],
                                property_id,
                                target,
                                field["default"] is None,
                                multivalued,
                                None,
                                None,
                                None,
                                None,
                                None,
                                False,
                                nullable=nullable,
                            )
                        ),
                        "default": field["default"],
                        "python_owner": field["owner"],
                    }
                ),
                kind.origins,
            )
            edges.extend(
                (
                    SemanticEdge(kind.semantic_id, property_id, "property"),
                    SemanticEdge(property_id, target, "range"),
                )
            )
    _materialize_json_schema_properties(kinds, nodes, edges)
    # A property projection shares its owning kind's access/projection policy.
    # It never infers a capability from a name or a field's representation.
    for kind_id, kind in tuple(kinds.items()):
        if kind.category != "property":
            continue
        owner = kinds.get(kind_id.rsplit("/property/", 1)[0])
        if owner is not None:
            owner_facts = json.loads(owner.facts)
            policy = _kind_policies(
                owner_facts.get("universe", "ordinary"),
                owner_facts.get("projection_families", []),
                owner.semantic_id,
                declaration_grammar,
            )
            kinds[kind_id] = replace(
                kind, facts=canonical_bytes({**json.loads(kind.facts), **policy})
            )
    operations = []
    subject_definitions = {}
    bindings = []
    for raw, surfaces, origins, implementation_root in authored:
        raw = _mapping(raw, "operation")
        semantic_id = _text(raw.get("id"), "operation/id")
        if any(operation.semantic_id == semantic_id for operation in operations):
            _fail(semantic_id, "duplicate operation semantic identity")
        roles = []
        role_names = set()
        for record in raw.get("roles", []):
            record = _mapping(
                record,
                semantic_id,
            )
            name = _text(record.get("name"), semantic_id + "/role")
            if name in role_names:
                _fail(semantic_id, "duplicate semantic role " + name)
            role_names.add(name)
            kind_name = _text(record.get("kind"), semantic_id + "/kind")
            kind = aliases.get(kind_name, kind_name)
            if kind not in kinds:
                _fail(semantic_id + "/" + name, "unresolved role kind " + kind)
            direction = record.get("direction")
            minimum, maximum = record.get("minimum"), record.get("maximum")
            if (
                type(minimum) is not int
                or minimum < 0
                or (maximum is not None and (type(maximum) is not int or maximum < minimum))
            ):
                _fail(semantic_id, "incompatible role cardinality")
            collection = record.get("collection")
            presence = record.get("presence")
            if collection not in {"scalar", "sequence", "bag", "set"} or presence not in {
                "required",
                "optional",
                "alternative",
            }:
                _fail(semantic_id, "collection and presence meaning must be explicit")
            if collection == "scalar" and maximum != 1:
                _fail(semantic_id, "a scalar role requires maximum one")
            if presence == "required" and minimum == 0:
                _fail(semantic_id, "required role cannot admit zero")
            if presence == "optional" and minimum != 0:
                _fail(semantic_id, "optional role must admit zero")
            support = None
            if direction == "input":
                data = _mapping(
                    record.get("support"),
                    semantic_id,
                )
                if data.get("provenance") not in {"exact", "value_substitution"}:
                    _fail(semantic_id, "input provenance substitution policy must be explicit")
                identity_requirements = _strings(data.get("identity_requirements", []), semantic_id)
                if not set(identity_requirements) <= {
                    "episode",
                    "provider",
                    "alternative",
                    "original-source",
                }:
                    _fail(semantic_id, "unsupported input support identity dimension")
                allowed_origins = _strings(
                    data.get("origins", ["computation"]),
                    semantic_id,
                    empty=False,
                )
                if not set(allowed_origins) <= {"computation", "original-source", "authored"}:
                    _fail(semantic_id, "unsupported input support origin")
                if (
                    data["provenance"] == "exact"
                    and "computation" in allowed_origins
                    and "episode" not in identity_requirements
                ):
                    _fail(
                        semantic_id,
                        "exact computation provenance requires explicit episode identity",
                    )
                if (
                    data["provenance"] == "exact"
                    and {"original-source", "authored"} & set(allowed_origins)
                    and "original-source" not in identity_requirements
                ):
                    _fail(
                        semantic_id, "exact original provenance requires original-source identity"
                    )
                if "original-source" in identity_requirements and not {
                    "original-source",
                    "authored",
                } & set(allowed_origins):
                    _fail(
                        semantic_id,
                        "original-source identity requires an allowed original support origin",
                    )
                source_set = data.get("source_set")
                if (source_set is not None) != (data.get("source") == "frozen-source-set"):
                    _fail(semantic_id, "frozen source-set policy requires its explicit named set")
                if source_set is not None:
                    source_set = _text(source_set, semantic_id + "/source_set")
                support = InputSupport(
                    data["provenance"],
                    _text(data.get("source"), semantic_id),
                    _input_coverage(data.get("coverage"), name, semantic_id),
                    _strings(data.get("authorization", []), semantic_id),
                    _strings(data.get("closure", []), semantic_id),
                    cast(Any, identity_requirements),
                    source_set,
                    cast(Any, allowed_origins),
                )
            elif record.get("support") is not None:
                _fail(semantic_id, "support requirements belong to input roles")
            alternatives = _strings(record.get("alternatives", []), semantic_id)
            selected = record.get("selected")
            if presence == "alternative" and (
                not alternatives or (selected is not None and selected not in alternatives)
            ):
                _fail(semantic_id, "alternative roles require a selected declared alternative")
            if presence != "alternative" and (alternatives or selected is not None):
                _fail(semantic_id, "only alternative roles carry a selected alternative")
            subject_target = record.get("subject_target", "subject")
            if subject_target not in {"subject", "original-source", "source-set"}:
                _fail(semantic_id, "unsupported subject association target")
            if subject_target == "source-set" and (
                direction != "input"
                or support is None
                or support.source_set is None
                or record.get("subject_field") is not None
            ):
                _fail(
                    semantic_id,
                    "source-set association requires an exact input source set without a root subject field",
                )
            if subject_target == "original-source" and (
                direction != "input" or not record.get("subject_field")
            ):
                _fail(semantic_id, "original-source association requires an input subject field")
            subject_field = record.get("subject_field")
            if subject_field is not None:
                subject_field = _text(subject_field, semantic_id + "/subject_field")
                if direction != "input":
                    _fail(semantic_id, "subject associations belong to input roles")
                from .data_operation_subjects import subject_field_kind

                try:
                    subject_field_kind(kinds, kind, subject_field)
                except ValueError as error:
                    _fail(semantic_id, str(error))
            roles.append(
                OperationRole(
                    name,
                    kind,
                    cast(Any, direction),
                    minimum,
                    maximum,
                    cast(Any, collection),
                    cast(Any, presence),
                    support,
                    record.get("parameter"),
                    alternatives,
                    selected,
                    subject_field,
                    cast(Any, subject_target),
                )
            )
        if semantic_id in kinds or semantic_id in nodes:
            _fail(semantic_id, "semantic operation identity collides with another owned fact")
        if not roles:
            _fail(semantic_id, "operation requires named input/output roles")
        result_fields = _mapping(raw.get("result_fields", {}), semantic_id)
        if result_fields:
            output_names = {role.name for role in roles if role.direction == "output"}
            if set(result_fields) != output_names:
                _fail(semantic_id, "result fields must map every declared output role exactly")
            for field in result_fields.values():
                _text(field, semantic_id)
            if len(set(result_fields.values())) != len(result_fields):
                _fail(semantic_id, "result fields must identify distinct returned fields")

        from .data_operation_output_witnesses import compile_output_witnesses

        try:
            output_witnesses = compile_output_witnesses(
                raw.get("output_witnesses", []), roles, kinds, aliases
            )
        except ValueError as error:
            _fail(semantic_id, str(error))

        def annotation_kind(annotation, role, owner=semantic_id):
            text = annotation or ""
            if text.endswith(" | None"):
                if role.presence != "optional":
                    _fail(owner, "nullable callable input requires optional role presence")
                text = text.removesuffix(" | None")
            collection_annotation = text.startswith(("list[", "tuple[", "set[", "frozenset["))
            if collection_annotation:
                if role.collection == "scalar":
                    _fail(owner, "scalar role differs from callable collection annotation")
                text = text.split("[", 1)[1].rsplit("]", 1)[0].replace(", ...", "")
            elif role.collection != "scalar":
                if text in primitive_types or text in aliases:
                    _fail(owner, "collection role requires a callable collection annotation")
                # An unresolved/bundle return is not relabelled as a primitive
                # collection. Its existing kind/implementation unknowns remain.
                return
            target = (
                python_types.get(text)
                or aliases.get(text)
                or ("primitive:" + primitive_types[text] if text in primitive_types else None)
            )
            if target is None:
                candidates = [
                    identity
                    for python, identity in python_types.items()
                    if python.rsplit(".", 1)[-1] == text
                ]
                target = candidates[0] if len(candidates) == 1 else None
            if target is not None and target != role.kind:
                _fail(owner, "semantic role kind differs from callable annotation")

        def logical_annotation(annotation, raw=raw, surfaces=surfaces):
            if raw.get("capabilities", {}).get("forms") != ["batch"] or len(surfaces) != 1:
                return annotation
            try:
                node = ast.parse(annotation, mode="eval").body
            except SyntaxError, TypeError:
                return annotation
            if not (
                isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and node.value.id == "tuple"
                and isinstance(node.slice, ast.Tuple)
                and len(node.slice.elts) == 2
                and isinstance(node.slice.elts[1], ast.Constant)
                and node.slice.elts[1].value is Ellipsis
            ):
                return annotation
            return ast.unparse(node.slice.elts[0])

        for surface in surfaces:
            parameters = {p.name for p in surface.parameters if p.name not in {"self", "cls"}}
            mapped = {role.parameter for role in roles if role.parameter is not None}
            if not mapped <= parameters:
                _fail(surface.exposed, "role parameter is absent from the extracted callable")
            if any(
                parameter.annotation is None
                for parameter in surface.parameters
                if parameter.name not in {"self", "cls"}
            ):
                _fail(
                    surface.exposed,
                    "supported operation invocation parameters require explicit annotations",
                )
            if surface.returns is None:
                _fail(
                    surface.exposed, "supported operation invocation requires a return annotation"
                )
            by_parameter = {parameter.name: parameter for parameter in surface.parameters}
            for name, parameter in raw.get("parameters", {}).items():
                if not isinstance(parameter, dict) or "kind" not in parameter:
                    continue
                if name not in by_parameter or name in mapped:
                    _fail(
                        surface.exposed,
                        "nominal semantic parameter lacks a distinct callable parameter",
                    )
                parameter_kind = aliases.get(parameter["kind"], parameter["kind"])
                annotation_kind(
                    logical_annotation(by_parameter[name].annotation),
                    OperationRole(
                        name,
                        parameter_kind,
                        "input",
                        0,
                        None,
                        parameter.get("collection", "scalar"),
                        "optional",
                    ),
                )
            for role in roles:
                if role.parameter is not None and role.direction == "input":
                    annotation_kind(
                        logical_annotation(by_parameter[role.parameter].annotation), role
                    )
            outputs = [role for role in roles if role.direction == "output"]
            if result_fields:
                result_annotation: ast.expr | None = None
                try:
                    result_annotation = ast.parse(
                        logical_annotation(surface.returns), mode="eval"
                    ).body
                except SyntaxError:
                    _fail(surface.exposed, "result correspondence requires a typed mapping return")
                if not (
                    isinstance(result_annotation, ast.Subscript)
                    and isinstance(result_annotation.value, ast.Name)
                    and result_annotation.value.id == "dict"
                    and isinstance(result_annotation.slice, ast.Tuple)
                    and len(result_annotation.slice.elts) == 2
                    and isinstance(result_annotation.slice.elts[0], ast.Name)
                    and result_annotation.slice.elts[0].id == "str"
                ):
                    _fail(surface.exposed, "result correspondence requires dict[str, T] return")
                for role in outputs:
                    annotation_kind(ast.unparse(result_annotation.slice.elts[1]), role)
            elif len(outputs) == 1:
                annotation_kind(logical_annotation(surface.returns), outputs[0])
        dimensions = []
        for record in raw.get("state_dimensions", []):
            record = _mapping(record, semantic_id)
            dimensions.append(
                StateDimension(
                    _text(record.get("name"), semantic_id),
                    _strings(record.get("values"), semantic_id, empty=False),
                )
            )
        if len({d.name for d in dimensions}) != len(dimensions):
            _fail(semantic_id, "duplicate state dimension")
        effects = []
        for record in raw.get("effects", []):
            record = _mapping(record, semantic_id)
            effects.append(
                EffectContract(
                    _text(record.get("name"), semantic_id),
                    _strings(record.get("authorization"), semantic_id, empty=False),
                    _text(record.get("idempotency"), semantic_id),
                    _text(record.get("fulfillment"), semantic_id),
                )
            )
        if len({e.name for e in effects}) != len(effects):
            _fail(semantic_id, "duplicate effect")
        if effects and raw["profile"] != "command":
            _fail(semantic_id, "effects require the command profile")
        if raw["profile"] == "command" and not effects:
            _fail(semantic_id, "commands require explicit authorized effects")
        outcomes = _strings(raw.get("outcomes"), semantic_id, empty=False)
        transitions = []
        for record in raw.get("transitions", []):
            record = _mapping(record, semantic_id)
            transition = StateTransition(
                record["dimension"],
                record["before"],
                record["after"],
                record["outcome"],
                _strings(record.get("effects", []), semantic_id),
            )
            dimension = next((d for d in dimensions if d.name == transition.dimension), None)
            if (
                dimension is None
                or transition.before not in dimension.values
                or transition.after not in dimension.values
            ):
                _fail(semantic_id, "transition refers to unknown state")
            if transition.outcome not in outcomes or not set(transition.effects) <= {
                effect.name for effect in effects
            }:
                _fail(semantic_id, "transition outcome/effect correspondence differs")
            transitions.append(transition)
        # Materialize conventional outcome correspondence into the admitted model.
        # Native publication consumes these exact transitions; it has no fallback.
        completion = next((item for item in dimensions if item.name == "completion"), None)
        if completion is None:
            completion = StateDimension("completion", ("pending", "success", "empty", "failed"))
            dimensions.append(completion)
        for outcome in outcomes:
            matches = [
                item
                for item in transitions
                if item.dimension == "completion"
                and item.before == "pending"
                and item.outcome == outcome
            ]
            if not matches and outcome in {"success", "empty", "failed"}:
                transitions.append(StateTransition("completion", "pending", outcome, outcome, ()))
                matches = [transitions[-1]]
            if (
                len(matches) != 1
                or matches[0].after not in {"success", "empty", "failed"}
                or matches[0].effects
                or matches[0].after not in completion.values
                or "pending" not in completion.values
            ):
                _fail(semantic_id, "outcome requires one explicit completion terminal mapping")
        capabilities = _mapping(
            raw.get("capabilities"),
            semantic_id,
        )
        forms = _strings(capabilities.get("forms"), semantic_id, empty=False)
        settlement = None
        if capabilities.get("stream_settlement") is not None:
            record = _mapping(
                capabilities["stream_settlement"],
                semantic_id,
            )
            if record.get("mode") != "terminal-atomic" or forms != ("stream",):
                _fail(semantic_id, "terminal settlement requires exactly the stream form")
            output = next(
                (
                    role
                    for role in roles
                    if role.direction == "output" and role.name == record.get("output_role")
                ),
                None,
            )
            if (
                output is None
                or len([role for role in roles if role.direction == "output"]) != 1
                or record.get("terminal_outcome") not in outcomes
            ):
                _fail(semantic_id, "stream settlement requires one declared output and outcome")
            settlement = StreamSettlement(
                "terminal-atomic", output.name, record["terminal_outcome"]
            )

        def captured_method(name, *, semantic_id=semantic_id, origins=origins):
            if frontend is None or not isinstance(name, str) or not name.isidentifier():
                _fail(semantic_id, "captured capability requires its supplied Python owner")
            origin = next((origin for origin in origins if origin.field == "callable"), None)
            if origin is None:
                _fail(semantic_id, "captured capability lacks a callable owner")
            declaration = origin.exposed_as or origin.declaration
            owner = declaration.rsplit(".", 1)[0]
            entrypoint = owner + "." + name
            member = frontend.resolve(entrypoint)
            from hashlib import sha256

            import griffe

            if not isinstance(member, griffe.Function):
                _fail(semantic_id, "captured capability is not an original method")
            # Griffe resolves the exposed inherited name to its actual supplier.
            # Runtime custody inspects that supplier's captured syntax and code.
            entrypoint = member.path
            source = frontend.modules[frontend._module_for(entrypoint)].source
            from .python_module_projection import admitted_operation_module_digest

            return ConsumerSelectionCapability(
                entrypoint,
                sha256(source.content).hexdigest(),
                admitted_operation_module_digest(source.content),
            )

        factory = (
            captured_method(capabilities["prepared_factory"])
            if capabilities.get("prepared_factory") is not None
            else None
        )
        selection = (
            captured_method(raw["consumer_selection"])
            if raw.get("consumer_selection") is not None
            else None
        )
        capability = ImplementationCapabilities(
            cast(Any, forms),
            _text(capabilities.get("preparation"), semantic_id),
            _text(capabilities.get("cancellation"), semantic_id),
            _text(capabilities.get("ownership"), semantic_id),
            _strings(capabilities.get("limits", []), semantic_id),
            settlement,
            factory,
            capabilities.get("cpu_receipts"),
        )
        binding_id = semantic_id + "/binding"
        binding = RelationalBinding(
            binding_id,
            semantic_id,
            _expression(raw.get("binding"), semantic_id, role_names),
            origins,
        )
        _validate_binding_fields(
            binding.expression, {role.name: role for role in roles}, kinds, aliases, semantic_id
        )
        if binding_id in kinds or binding_id in nodes:
            _fail(binding_id, "generated binding identity collides with another owned fact")
        bindings.append(binding)
        assets = tuple(
            replace(
                asset,
                reuse_eligible=asset.reuse_eligible
                and supplied_contracts[asset.contract].reuse_eligible,
            )
            if asset.contract in supplied_contracts
            else asset
            for record in raw.get("assets", [])
            for asset in (OpaqueBoundary(**record),)
        )
        from .data_operation_identity import validate_opaque_boundary

        for asset in assets:
            try:
                validate_opaque_boundary(asdict(asset))
            except ValueError as exc:
                _fail(semantic_id, "invalid captured semantic asset: " + str(exc))
        numerical_policy = None
        if raw.get("numerical_policy") is not None:
            policy_reference = _mapping(raw["numerical_policy"], semantic_id)
            asset_name = _text(policy_reference.get("asset"), semantic_id)
            asset = supplied_contracts.get(asset_name)
            if asset is None or not any(
                owner.contract == asset_name and owner.content_digest == asset.digest
                for owner in assets
            ):
                _fail(semantic_id, "numerical policy requires its actual captured operation asset")
            pointer = _text(policy_reference.get("pointer"), semantic_id)
            from .data_operation_subjects import subject_field_path
            from .data_operation_wire import validate_wire_schema

            try:
                body = wire_json_loads(asset.content)
                for part in subject_field_path(pointer):
                    body = body[part]
                policy_kind = _text(policy_reference.get("kind"), semantic_id)
                policy_kind = aliases.get(policy_kind, policy_kind)
                policy_schema = json.loads(kinds[policy_kind].facts)["json_schema"]
                validate_wire_schema(policy_schema, body)
                from .data_operation_wire import json_schema_properties

                if not isinstance(body, dict) or set(body) != {
                    name for name, _, _ in json_schema_properties(policy_schema)
                }:
                    _fail(semantic_id, "numerical policy requires every explicit semantic field")
            except (KeyError, TypeError, ValueError) as error:
                _fail(
                    semantic_id,
                    "numerical policy differs from its nominal captured kind: " + str(error),
                )
            numerical_policy = NumericalPolicyReference(
                policy_kind, asset_name, asset.digest, pointer, canonical_bytes(body)
            )
        from .data_operation_parameters import compile_nominal_parameters

        try:
            parameter_definitions = compile_nominal_parameters(
                _mapping(raw.get("parameters", {}), semantic_id),
                schema=schema,
                definitions=definitions,
                vocabularies=vocabularies,
                kinds=kinds,
            )
        except (ValueError, TypeError) as exc:
            _fail(semantic_id, "invalid nominal parameters: " + str(exc))
        for name, parameter in parameter_definitions.items():
            if isinstance(parameter, dict) and "kind" in parameter:
                edges.append(SemanticEdge(semantic_id, parameter["kind"], "parameter-kind", name))
        external = None
        if raw.get("external") is not None:
            record = _mapping(
                raw["external"],
                semantic_id,
            )
            if (
                record.get("version") != "external-executor-v1"
                or record.get("reference_scope") != "declared-inputs-only"
            ):
                _fail(
                    semantic_id,
                    "external execution requires its closed protocol and declared-input reference scope",
                )
            if (
                surfaces
                or implementation_root is not None
                or factory is not None
                or selection is not None
                or forms != ("scalar",)
            ):
                _fail(
                    semantic_id,
                    "authored external protocol cannot acquire a Python callable or batch/stream owner",
                )
            exposed = {role.kind for role in roles}
            pending = list(exposed)
            while pending:
                current = pending.pop()
                for edge in edges:
                    if (
                        edge.source == current
                        and edge.target in kinds
                        and edge.target not in exposed
                    ):
                        exposed.add(edge.target)
                        pending.append(edge.target)
            if any(
                json.loads(kinds[kind].facts).get("universe", "ordinary") == "evaluator"
                for kind in exposed
            ):
                _fail(
                    semantic_id, "external packets/results cannot expose protected evaluator kinds"
                )
            if capability.preparation != "external":
                _fail(semantic_id, "external protocol requires explicit external preparation")
            if effects and any(
                effect.authorization != ("native-purpose:write",)
                or effect.idempotency != "external-packet"
                or effect.fulfillment != "native-publication-receipt"
                for effect in effects
            ):
                _fail(
                    semantic_id,
                    "external effects require native write authorization, packet idempotency and native publication receipt fulfillment",
                )
            external = ExternalExecutorContract(
                "external-executor-v1",
                _text(record.get("instructions"), semantic_id),
                _text(record.get("requested_actor"), semantic_id),
                None
                if record.get("requested_model") is None
                else _text(record["requested_model"], semantic_id),
                "declared-inputs-only",
            )
        subject = _text(raw.get("subject"), semantic_id)
        subject_record = _mapping(
            raw.get("subject_definition"),
            semantic_id,
        )
        if subject_record.get("id") != subject:
            _fail(semantic_id, "operation subject differs from its declared subject definition")
        additional_subjects = raw.get("subject_definitions", [])
        if not isinstance(additional_subjects, list):
            _fail(semantic_id, "additional subject definitions require a declaration list")
        for declared_subject in (subject_record, *additional_subjects):
            declared_subject = _mapping(declared_subject, semantic_id)
            subject_id = _text(declared_subject.get("id"), semantic_id)
            identifier_name = _text(declared_subject.get("identifier_kind"), semantic_id)
            identifier_kind = aliases.get(identifier_name, identifier_name)
            if identifier_kind not in kinds:
                _fail(semantic_id, "subject definition requires a resolved identifier kind")
            subject_scope = declared_subject.get("scope")
            if subject_scope not in get_args(SubjectScope):
                _fail(semantic_id, "unsupported subject scope relation")
            subject_definition = SubjectDefinition(
                subject_id, identifier_kind, cast(SubjectScope, subject_scope)
            )
            if (
                subject_id in subject_definitions
                and subject_definitions[subject_id] != subject_definition
            ):
                _fail(semantic_id, "subject definition has conflicting semantic owners")
            subject_definitions[subject_id] = subject_definition
            subject_node = "subject:" + subject_id
            subject_payload = canonical_bytes(asdict(subject_definition))
            if subject_node in nodes and nodes[subject_node].payload != subject_payload:
                _fail(semantic_id, "subject definition has conflicting semantic owners")
            nodes[subject_node] = SemanticNode(subject_node, "subject", subject_payload)
            edges.append(SemanticEdge(subject_node, identifier_kind, "subject_identifier_kind"))
        discovery_relation = raw.get("discovery_relation")
        if discovery_relation not in {"role-associated", "subject-population"}:
            _fail(semantic_id, "operation requires explicit subject discovery relation")
        subject_node = "subject:" + subject
        edges.append(SemanticEdge(semantic_id, subject_node, "operation_subject"))
        replicate_policy = raw.get("replicate_policy", "deterministic-single-result")
        if replicate_policy not in get_args(ReplicatePolicy):
            _fail(semantic_id, "unsupported replicate policy")
        operation = EffectiveOperation(
            semantic_id,
            raw["profile"],
            subject,
            _strings(raw.get("context"), semantic_id),
            tuple(roles),
            _enforcement_claims(raw.get("applicability"), semantic_id),
            _enforcement_claims(raw.get("invariants"), semantic_id),
            _coverage_contract(raw.get("coverage"), binding_id, semantic_id),
            outcomes,
            None
            if raw.get("precision_description") is None
            else _text(raw["precision_description"], semantic_id),
            _strings(raw.get("dependencies"), semantic_id),
            tuple(dimensions),
            tuple(transitions),
            tuple(effects),
            capability,
            _text(raw.get("behavior"), semantic_id),
            canonical_bytes(parameter_definitions),
            assets,
            surfaces,
            implementation_root,
            origins,
            binding_id,
            cast(ReplicatePolicy, replicate_policy),
            _text(raw.get("support_policy", "all-declared-input-support"), semantic_id),
            _strings(raw.get("potential_dependencies", []), semantic_id),
            tuple(sorted(result_fields.items())),
            selection,
            output_witnesses,
            external,
            discovery_relation=discovery_relation,
            numerical_policy=numerical_policy,
            validity=_validity_claim(raw, declaration_grammar, semantic_id, diagnostics),
        )
        operations.append(operation)
        if raw.get("validity_family") == ["none"]:
            inputs = {role.kind for role in operation.roles if role.direction == "input"}
            family_vocabulary = declaration_grammar.vocabularies["ValidityFamily"]
            statuses = dict(family_vocabulary.statuses)
            for family, annotations in family_vocabulary.annotations.items():
                if statuses.get(family) == "provisional":
                    continue
                exposed = inputs & set(annotations.get("cs:protected_inputs", ()))
                if exposed:
                    diagnostics.append(
                        Diagnostic(
                            "validity_claim_unprotected",
                            semantic_id,
                            f"none claim consumes inputs protected by {family}: {', '.join(sorted(exposed))}",
                            "advisory",
                        )
                    )
        nodes[semantic_id] = SemanticNode(semantic_id, "operation", operation.definition)

        # Binding bytes retain the complete closed vocabulary
        # and explicitly export typed literal payloads.
        def binding_payload(expression):
            data = asdict(expression)
            data["value"] = json.loads(expression.value) if expression.value is not None else None
            data["operands"] = [
                {
                    **{
                        key: value
                        for key, value in asdict(operand).items()
                        if key != "population_projection" or value != "member"
                    },
                    "value": json.loads(operand.value) if operand.value is not None else None,
                }
                for operand in expression.operands
            ]
            data["children"] = [binding_payload(child) for child in expression.children]
            return data

        nodes[binding_id] = SemanticNode(
            binding_id, "binding", canonical_bytes(binding_payload(binding.expression))
        )
        edges.append(SemanticEdge(semantic_id, binding_id, "binding"))
        for role in roles:
            edges.append(
                SemanticEdge(
                    semantic_id,
                    role.kind,
                    "input_kind" if role.direction == "input" else "output_kind",
                    role.name,
                )
            )
        for dependency in operation.dependencies:
            edges.append(SemanticEdge(semantic_id, dependency, "operation_dependency"))
        for dependency in operation.potential_dependencies:
            edges.append(SemanticEdge(semantic_id, dependency, "potential_operation_dependency"))
    for semantic_id, kind in kinds.items():
        nodes[semantic_id] = SemanticNode(semantic_id, "kind:" + kind.category, kind.facts)
    for edge in edges:
        if edge.source not in nodes or edge.target not in nodes:
            _fail(edge.source, "unresolved typed semantic reference " + edge.target)
    model = EffectiveDataOperationModel(
        MODEL_VERSION,
        tuple(kinds[key] for key in sorted(kinds)),
        tuple(sorted(operations, key=lambda o: o.semantic_id)),
        tuple(sorted(bindings, key=lambda b: b.semantic_id)),
        tuple(nodes[key] for key in sorted(nodes)),
        tuple(sorted(edges, key=lambda e: (e.source, e.target, e.relation, e.role))),
        tuple(slices),
        graph_projections=compiled_graph_projections(tuple(nodes.values()), edges, slices),
        subject_definitions=tuple(subject_definitions[key] for key in sorted(subject_definitions)),
    )

    from .source_interfaces import export_source_interfaces

    model = _resolve_enforcement_claims(
        model, {name: artifact.digest for name, artifact in supplied_contracts.items()}
    )
    model = replace(model, identities=_compile_identities(model))
    return replace(
        model,
        source_interfaces=export_source_interfaces(frontend, python_facts, model).content
        if frontend is not None
        else None,
        diagnostics=tuple(diagnostics),
    )


def _input_coverage(value, role, owner):
    value = _mapping(value, owner)
    if value.get("role") != role:
        _fail(owner, "input coverage must reference its actual bound role")
    return InputCoverage(role, _text(value.get("description"), owner))


def _coverage_contract(value, binding, owner):
    value = _mapping(value, owner)
    if value.get("binding") != "self":
        _fail(owner, "coverage must resolve its own actual relational binding")
    entries = value.get("result_owners")
    if not isinstance(entries, list) or not entries:
        _fail(owner, "coverage requires an explicit actual result owner")
    result_owners = []
    interpretations = {
        "implementation": "captured-python-slice-v1",
        "native-admission": "captured-native-admission-v1",
        "declared-contract": "authored-result-contract-v1",
    }
    for entry in entries:
        entry = _mapping(entry, owner)
        kind = entry.get("kind")
        if kind not in interpretations:
            _fail(
                owner,
                "coverage requires an implementation, native admission or declared result owner",
            )
        result_owners.append(
            CoverageResultOwner(
                kind, _text(entry.get("reference"), owner), interpretations[kind], b"{}"
            )
        )
    return CoverageContract(
        binding, b"{}", b"{}", tuple(result_owners), _text(value.get("description"), owner)
    )


def _enforcement_claims(value, owner):
    if not isinstance(value, list):
        _fail(owner, "enforcement claims require explicit tagged records")
    claims = []
    revisions = {
        "binding": "binding-expression-v1",
        "schema": "effective-schema-v1",
        "implementation": "captured-python-slice-v1",
        "native-admission": "captured-native-admission-v1",
    }
    for entry in value:
        entry = _mapping(entry, owner)
        if entry.get("kind") == "documentation":
            entry = _mapping(entry, owner)
            claims.append(EnforcementClaim("documentation", text=_text(entry.get("text"), owner)))
            continue
        entry = _mapping(entry, owner)
        kind = entry.get("kind")
        if kind not in revisions or entry.get("interpretation") != revisions[kind]:
            _fail(owner, "unsupported enforcement interpretation")
        parameters = _mapping(entry.get("parameters"), owner)
        if parameters:
            _fail(owner, "enforcement owner does not admit additional parameters")
        claims.append(
            EnforcementClaim(
                kind,
                reference=_text(entry.get("reference"), owner),
                interpretation=revisions[kind],
                parameters=canonical_bytes(parameters),
            )
        )
    return tuple(claims)


def _resolve_enforcement_claims(model, captured_assets):
    from .data_operation_identity import implementation_slice_fingerprint, kind_fingerprint

    try:
        graph = model.projection_graph("semantic-reference")
    except ValueError as error:
        _fail("model/graph", str(error))
    kinds = {kind.semantic_id: kind for kind in model.kinds}
    bindings = {binding.semantic_id: binding for binding in model.bindings}
    slices = {implementation.root: implementation for implementation in model.implementation_slices}

    def resolve(claim, operation):
        if claim.kind == "documentation":
            return claim
        reference = claim.reference
        if claim.kind == "binding":
            if reference != operation.binding or reference not in bindings:
                _fail(operation.semantic_id, "unknown operation binding enforcement reference")
            semantics = _binding_record(bindings[reference].expression)
        elif claim.kind == "schema":
            if reference not in kinds or any(
                not kinds[owner].complete for owner in graph.closure((reference,)) if owner in kinds
            ):
                _fail(operation.semantic_id, "unknown complete schema enforcement reference")
            semantics = {"kind_contract": kind_fingerprint(graph, reference).key}
        elif claim.kind == "implementation":
            implementation = slices.get(operation.implementation_root)
            if (
                implementation is None
                or not implementation.complete
                or reference not in {node.id for node in implementation.nodes}
            ):
                _fail(
                    operation.semantic_id, "unknown captured implementation enforcement reference"
                )
            semantics = {
                "implementation_slice": implementation_slice_fingerprint(
                    implementation.semantic_records(), implementation.root
                ).key
            }
        elif claim.kind == "native-admission":
            matches = [
                asset
                for asset in operation.assets
                if asset.reference == reference
                and asset.role == "native-admission-policy"
                and asset.content_digest is not None
                and captured_assets.get(asset.contract) == asset.content_digest
            ]
            if len(matches) != 1:
                _fail(
                    operation.semantic_id, "unknown captured native admission enforcement reference"
                )
            semantics = asdict(matches[0])
        else:
            _fail(operation.semantic_id, "unknown enforcement source")
        return replace(claim, semantics=canonical_bytes(semantics))

    def coverage(operation):
        contract = operation.coverage
        if contract.binding != operation.binding or contract.binding not in bindings:
            _fail(operation.semantic_id, "coverage has no checked operation binding")
        binding = bindings[contract.binding]
        subject = next(
            subject
            for subject in model.subject_definitions
            if subject.semantic_id == operation.subject
        )

        def selection(result_only):
            return canonical_bytes(
                {
                    "subject_definition": asdict(subject),
                    "context": operation.context,
                    "input_roles": [
                        operation_role_record(role, result_only=result_only)
                        for role in operation.roles
                        if role.direction == "input"
                    ],
                    "binding": _binding_record(binding.expression, result_only=result_only),
                }
            )

        owners = []
        for owner in contract.result_owners:
            if owner.kind == "implementation":
                implementation = slices.get(operation.implementation_root)
                if owner.reference != "self" or implementation is None:
                    _fail(
                        operation.semantic_id,
                        "coverage lacks its actual captured implementation owner",
                    )
                reference = implementation.root
                semantics = {
                    "implementation_slice": implementation_slice_fingerprint(
                        implementation.semantic_records(), implementation.root
                    ).key
                    if implementation.complete
                    else None,
                    "complete": implementation.complete,
                    **(
                        {"unknowns": [asdict(unknown) for unknown in implementation.unknowns]}
                        if not implementation.complete
                        else {}
                    ),
                }
            elif owner.kind == "native-admission":
                claim = resolve(
                    EnforcementClaim(
                        "native-admission",
                        reference=owner.reference,
                        interpretation=owner.interpretation,
                        parameters=b"{}",
                    ),
                    operation,
                )
                reference, semantics = owner.reference, json.loads(claim.semantics)
            elif owner.kind == "declared-contract":
                if owner.reference != "self" or operation.implementation_root is not None:
                    _fail(
                        operation.semantic_id,
                        "declared result coverage belongs only to a nonslice contract",
                    )
                reference = operation.semantic_id
                semantics = {
                    "behavior": operation.behavior,
                    "outcomes": operation.outcomes,
                    "effects": [asdict(effect) for effect in operation.effects],
                }
            else:
                _fail(operation.semantic_id, "unsupported authored result coverage owner")
            owners.append(replace(owner, reference=reference, semantics=canonical_bytes(semantics)))
        for kind in sorted({role.kind for role in operation.roles if role.direction == "output"}):
            owners.append(
                CoverageResultOwner(
                    "schema",
                    kind,
                    "effective-schema-v1",
                    canonical_bytes(
                        {
                            "kind_contract": kind_fingerprint(graph, kind).key,
                            "complete": kinds[kind].complete,
                        }
                    ),
                )
            )
        return replace(
            contract,
            selection=selection(False),
            result_selection=selection(True),
            result_owners=tuple(owners),
        )

    operations = tuple(
        replace(
            operation,
            applicability=tuple(resolve(claim, operation) for claim in operation.applicability),
            invariants=tuple(resolve(claim, operation) for claim in operation.invariants),
            coverage=coverage(operation),
        )
        for operation in model.operations
    )
    definitions = {operation.semantic_id: operation.definition for operation in operations}
    nodes = tuple(
        replace(node, payload=definitions[node.id]) if node.id in definitions else node
        for node in model.nodes
    )
    return replace(
        model,
        operations=operations,
        nodes=nodes,
        graph_projections=compiled_graph_projections(
            nodes, model.edges, model.implementation_slices
        ),
    )


def _binding_record(expression: BindingExpression, *, result_only: bool = False) -> dict | None:
    if result_only and expression.impact == "eligibility":
        return None
    data: dict[str, Any] = asdict(expression)
    data["value"] = json.loads(expression.value) if expression.value is not None else None
    data["operands"] = [
        {
            **{
                key: value
                for key, value in asdict(operand).items()
                if key != "population_projection" or value != "member"
            },
            "value": json.loads(operand.value) if operand.value is not None else None,
        }
        for operand in expression.operands
    ]
    data["children"] = [
        record
        for child in expression.children
        if (record := _binding_record(child, result_only=result_only)) is not None
    ]
    return data


def native_kind_dependencies(
    model: EffectiveDataOperationModel,
    *,
    unavailable: frozenset[str] = frozenset(),
    defer_invalid_members: bool = False,
) -> tuple[set[str], dict[str, tuple[str, ...]]]:
    """Resolve the nominal members represented in the installed kind contract."""
    from .data_operation_kind_refinements import input_kind_refinements
    from .data_operation_member_contracts import derive_member_kinds

    roots = {
        role.kind
        for operation in model.operations
        for role in operation.roles
        if role.direction == "input"
    }
    used = {role.kind for operation in model.operations for role in operation.roles}
    used.update(
        model.subject_definition(operation.subject).identifier_kind
        for operation in model.operations
    )
    used.update(
        parameter["kind"]
        for operation in model.operations
        for parameter in json.loads(operation.parameters).values()
        if isinstance(parameter, dict) and "kind" in parameter
    )
    refinements = input_kind_refinements(model, roots - unavailable) if roots else {}
    used.update(kind for family in refinements.values() for kind in family)
    dependencies: dict[str, tuple[str, ...]] = {}
    pending = list(used - unavailable)
    while pending:
        kind = pending.pop()
        if kind in dependencies:
            continue
        try:
            members = derive_member_kinds(model, kind)
        except PreparationError:
            if not defer_invalid_members:
                raise
            # An explanatory compile can hold a kind the native projection will refuse.
            members = ()
        dependencies[kind] = members
        pending.extend(member for member in members if member not in unavailable)
    return roots, dependencies


def operation_recipe_input(
    operation: EffectiveOperation,
    subject_definition: SubjectDefinition,
    subject_kind_contract: str,
    kind_contracts: dict[str, str],
    parameter_contracts: dict[str, str],
    binding: BindingExpression,
) -> dict:
    """The same result-determining fields for compilation and comparison."""
    return {
        "recipe": json.loads(operation.recipe),
        "subject_definition": asdict(subject_definition),
        "subject_identifier_kind_contract": subject_kind_contract,
        "kind_contracts": kind_contracts,
        **({"parameter_kind_contracts": parameter_contracts} if parameter_contracts else {}),
        "binding": _binding_record(binding, result_only=True),
    }


def _compile_identities(model: EffectiveDataOperationModel) -> tuple[EffectiveIdentity, ...]:
    """Consume the DDO-02 encoding directly; never issue a reusable unknown recipe."""
    from .data_operation_identity import (
        SemanticGraph,
        definition_fingerprint,
        eligibility_fingerprint,
        implementation_slice_fingerprint,
        kind_fingerprint,
        recipe_fingerprint,
    )

    try:
        graph = model.projection_graph("semantic-reference")
    except ValueError as error:
        _fail("model/graph", str(error))
    identities = []
    kinds = {}
    incomplete_kinds = {kind.semantic_id for kind in model.kinds if not kind.complete}
    unavailable = frozenset(
        kind.semantic_id
        for kind in model.kinds
        if incomplete_kinds.intersection(graph.closure((kind.semantic_id,)))
    )
    _, members = native_kind_dependencies(
        model, unavailable=unavailable, defer_invalid_members=True
    )
    records = model.semantic_records()
    records["edges"] = (
        *records["edges"],
        *(
            asdict(SemanticEdge(kind, member, "member_contract"))
            for kind, contained in members.items()
            for member in contained
        ),
    )
    graph = SemanticGraph(records)
    for kind in model.kinds:
        if unavailable.intersection(graph.closure((kind.semantic_id,))):
            continue
        identity = kind_fingerprint(graph, kind.semantic_id)
        kinds[kind.semantic_id] = identity.key
        identities.append(EffectiveIdentity(kind.semantic_id, identity.domain, identity.key))
    slices = {}
    for implementation in model.implementation_slices:
        if implementation.complete:
            identity = implementation_slice_fingerprint(
                implementation.semantic_records(), implementation.root
            )
            slices[implementation.root] = identity
            identities.append(EffectiveIdentity(implementation.root, identity.domain, identity.key))
    bindings = {binding.semantic_id: binding for binding in model.bindings}
    for operation in model.operations:
        binding = bindings[operation.binding]
        subject_definition = model.subject_definition(operation.subject)
        if subject_definition.identifier_kind not in kinds:
            continue
        subject_kind_contract = kinds[subject_definition.identifier_kind]
        parameter_kinds = {
            name: parameter["kind"]
            for name, parameter in json.loads(operation.parameters).items()
            if isinstance(parameter, dict) and "kind" in parameter
        }
        if any(kind not in kinds for kind in parameter_kinds.values()):
            continue
        parameter_contracts = {name: kinds[kind] for name, kind in parameter_kinds.items()}
        if any(role.kind not in kinds for role in operation.roles):
            continue
        kind_contracts = {role.name: kinds[role.kind] for role in operation.roles}
        definition = definition_fingerprint(
            {
                "definition": json.loads(operation.definition),
                "subject_definition": asdict(subject_definition),
                "subject_identifier_kind_contract": subject_kind_contract,
                "binding": _binding_record(binding.expression),
                "kind_contracts": kind_contracts,
                **(
                    {"parameter_kind_contracts": parameter_contracts} if parameter_contracts else {}
                ),
            }
        )
        eligibility = eligibility_fingerprint(
            {
                "eligibility": json.loads(operation.eligibility),
                "binding": _binding_record(binding.expression),
            }
        )
        identities += [
            EffectiveIdentity(operation.semantic_id, identity.domain, identity.key)
            for identity in (definition, eligibility)
        ]
        if (
            operation.implementation_root is not None
            and operation.implementation_root not in slices
        ):
            continue
        implementation_slices = (
            ()
            if operation.implementation_root is None
            else (slices[operation.implementation_root],)
        )
        recipe = recipe_fingerprint(
            operation_recipe_input(
                operation,
                subject_definition,
                subject_kind_contract,
                kind_contracts,
                parameter_contracts,
                binding.expression,
            ),
            implementation_slices=implementation_slices,
        )
        identities.append(EffectiveIdentity(operation.semantic_id, recipe.domain, recipe.key))
    return tuple(identities)


def project_population_witness(
    witness: dict | None,
    identity_requirements: tuple[str, ...],
    *,
    model: EffectiveDataOperationModel,
) -> dict | None:
    """Separate stable population meaning from the authenticated receipt/support.

    Physical demand/use IDs and trust epochs are admission evidence. A declared
    exact episode determinant remains semantic, including a closure producer
    episode when the role has no present members.
    """
    if witness is None:
        return None
    if witness.get("reason") == "unselected-declared-branch":
        if (
            set(witness) != {"complete", "members", "selection", "reason"}
            or witness["complete"] is not True
            or witness["members"] != []
            or not isinstance(witness["selection"], dict)
        ):
            _fail("population-witness", "invalid frozen branch witness")
        return witness
    context_projection = witness.get("projection") == "qualified-context"
    expected_fields = {"identity", "complete", "members", "evidence"} | (
        {"projection"} if context_projection else set()
    )
    if (
        set(witness) != expected_fields
        or not isinstance(witness["identity"], str)
        or not witness["identity"]
        or type(witness["complete"]) is not bool
        or not isinstance(witness["members"], list)
        or (
            not context_projection
            and any(not isinstance(member, str) or not member for member in witness["members"])
        )
        or not isinstance(witness["evidence"], dict)
    ):
        _fail("population-witness", "invalid structured population witness")
    members = witness["members"]
    if context_projection:
        from .data_operation_json import json_bytes
        from .data_operation_model import SubjectContext

        try:
            contexts = [
                SubjectContext(
                    project_id=member["project_id"],
                    subject=member["subject"],
                    original_source=member["original_source"],
                    analyzed_scope=json_bytes(member["analyzed_scope"]),
                    subject_definition=member["subject_definition"],
                )
                for member in (
                    _mapping(
                        value,
                        "population-witness/context",
                        {field.name for field in fields(SubjectContext)},
                    )
                    for value in members
                )
            ]
        except (TypeError, KeyError, ValueError) as error:
            raise ValueError("invalid qualified-context population witness") from error
        for context in contexts:
            validate_subject_context(model, context)
        if len(set(contexts)) != len(contexts):
            _fail("population-witness", "duplicate qualified contexts")
        members = [context.identity_record for context in contexts]
    elif len(set(members)) != len(members):
        _fail("population-witness", "duplicate member identifiers")
    meaning = {"identity": witness["identity"], "complete": witness["complete"], "members": members}
    if context_projection:
        meaning["projection"] = "qualified-context"
    if "episode" in identity_requirements:
        episode = _text(witness["evidence"].get("derivation_id"), "population-witness/episode")
        meaning["support_episodes"] = [episode]
    return meaning


def project_operation_binding(
    model: EffectiveDataOperationModel, binding, *, execution_scope: str | None = None
):
    """Construct DDO-02 request/admission identities from the compiled role policies.

    This pure projection does not resolve native rows, assert support validity or
    authorize execution. It preserves their supplied evidence for later admission.
    """
    from .data_operation_identity import AdmissionManifest, SemanticRequestKey
    from .data_operation_values import CollectionValue, OptionalValue, decode_semantic_value

    operation = model.operation(binding.operation)
    try:
        validate_subject_context(
            model, binding.subject_context, subject_definition=operation.subject
        )
    except ValueError as error:
        _fail(operation.semantic_id, str(error))
    identities = {(item.owner, item.domain): item.key for item in model.identities}
    recipe = identities.get((operation.semantic_id, "recipe"))
    if recipe is None:
        _fail(operation.semantic_id, "reusable identity has unknown implementation determinants")
    try:
        validate_replicate_selection(
            operation.replicate_policy, binding.replicate, owner=operation.semantic_id
        )
    except ValueError as error:
        _fail(operation.semantic_id, str(error))
    input_roles = {role.name: role for role in operation.roles if role.direction == "input"}
    from .data_operation_kind_refinements import input_kind_contracts

    accepted = input_kind_contracts(model, (role.kind for role in input_roles.values()))
    bound_roles = {role.role: role for role in binding.roles}
    if len(bound_roles) != len(binding.roles) or bound_roles.keys() != input_roles.keys():
        _fail(operation.semantic_id, "resolved inputs differ from compiled input roles")
    values = {}
    support = {}
    for name, role in input_roles.items():
        actual = bound_roles[name]
        if actual.state not in {"present", "known-absent", "unavailable", "unknown"}:
            _fail(name, "unknown resolved role state")
        if actual.state != "present" and actual.members:
            _fail(name, "non-present roles cannot carry present members")
        if actual.state == "known-absent" and role.presence == "required":
            _fail(name, "required role cannot be known absent")
        if role.presence == "alternative" and actual.selected_alternative not in role.alternatives:
            _fail(name, "resolved alternative is outside the declared population")
        if role.presence != "alternative" and actual.selected_alternative is not None:
            _fail(name, "selected alternative belongs only to an alternative role")
        total = sum(member.multiplicity for member in actual.members)
        if actual.state == "present" and (
            total < role.minimum or (role.maximum is not None and total > role.maximum)
        ):
            _fail(name, "resolved role cardinality differs from its compiled contract")
        members: list[dict[str, Any]] = []
        actual_support = []
        for member in actual.members:
            for value in (member.product, member.subject):
                _text(value, name)
            try:
                validate_subject_source(model, member.subject_definition, member.original_source)
            except ValueError as error:
                _fail(name, str(error))
            if type(member.multiplicity) is not int or member.multiplicity < 1:
                _fail(name, "invalid bound member multiplicity")
            if member.position is not None and (
                type(member.position) is not int or member.position < 0
            ):
                _fail(name, "invalid bound member position")
            if member.kind_contract not in accepted[role.kind]:
                _fail(name, "bound member kind contract differs from the compiled kind")
            if role.collection == "sequence" and member.position is None:
                _fail(name, "ordered members require explicit positions")
            member_identity = member.product
            if member.member is not None:
                evidence = wire_json_loads(member.support_evidence)
                member_identity = _text(evidence.get("member_body_identity"), name + "/member-body")
            value = {
                "product": member_identity,
                "kind": member.kind_contract,
                "subject": member.subject,
                "subject_definition": member.subject_definition,
                "member": member.member,
                "original_source": member.original_source,
                "analyzed_scope": scope_identity(json_loads(member.analyzed_scope)),
                "coverage": json.loads(member.coverage),
                "position": member.position if role.collection == "sequence" else None,
                "multiplicity": member.multiplicity,
            }
            assert role.support is not None
            from .data_operation_support import (
                AuthoredFactSupportReference,
                OriginalSourceSupportReference,
                support_reference_records,
            )

            originals = tuple(
                reference
                for reference in member.support_references
                if isinstance(
                    reference, (OriginalSourceSupportReference, AuthoredFactSupportReference)
                )
            )
            actual_origins = {reference.kind for reference in member.support_references}
            if not actual_origins <= set(role.support.origins) or (
                not actual_origins and role.support.origins != ("computation",)
            ):
                _fail(name, "bound support origin is outside declared admission policy")
            if "original-source" in role.support.identity_requirements and originals:
                value["original_sources"] = tuple(
                    sorted({ref.source_reference for ref in originals})
                )
            if "episode" in role.support.identity_requirements and (
                "computation" in actual_origins or not actual_origins
            ):
                if not member.support_episodes:
                    _fail(name, "required episode identity is unavailable")
                value["support_episodes"] = tuple(sorted(_strings(member.support_episodes, name)))
            for dimension, selected in (
                ("provider", member.provider_identity),
                ("alternative", member.alternative_identity),
            ):
                if dimension in role.support.identity_requirements:
                    value[dimension] = _text(selected, name + "/required-" + dimension)
            members.append(value)
            actual_support.append(
                {
                    "product": member.product,
                    "member": member.member,
                    "position": member.position,
                    "episodes": member.support_episodes,
                    "support_references": support_reference_records(member.support_references),
                    "evidence": wire_json_loads(member.support_evidence),
                    "provider": member.provider_identity,
                    "alternative": member.alternative_identity,
                }
            )
        if role.collection == "sequence":
            if len({member.position for member in actual.members}) != len(actual.members):
                _fail(name, "duplicate ordered input position")
            members.sort(key=lambda item: cast(int, item["position"]))
            collection = CollectionValue("ordered-bag", tuple(members))
        elif role.collection == "set":
            collection = CollectionValue("set", tuple(members))
        elif role.collection == "bag":
            collection = CollectionValue("bag", tuple(members))
        else:
            collection = tuple(members)

        def requires_population(expression, role_name):
            return (
                (
                    expression.operator in {"forall", "absent"}
                    and (not expression.roles or role_name in expression.roles)
                )
                or (
                    any(operand.kind == "population" for operand in expression.operands)
                    and any(
                        operand.field is not None and operand.field.role == role_name
                        for operand in expression.operands
                    )
                )
                or any(requires_population(child, role_name) for child in expression.children)
            )

        compiled_binding = next(
            item for item in model.bindings if item.semantic_id == operation.binding
        )
        if (
            requires_population(compiled_binding.expression, name)
            and actual.population_witness is None
        ):
            _fail(name, "closed population binding requires its population witness")
        if actual.state == "known-absent" and actual.population_witness is None:
            _fail(name, "known absence requires a closed population witness")
        witness = (
            wire_json_loads(actual.population_witness)
            if actual.population_witness is not None
            else None
        )
        values[name] = {
            "value": OptionalValue(actual.state, collection if actual.state == "present" else None),
            "population_witness": project_population_witness(
                witness, role.support.identity_requirements if role.support else (), model=model
            )
            if requires_population(compiled_binding.expression, name)
            or actual.state == "known-absent"
            else None,
            "selected_alternative": actual.selected_alternative,
        }
        support[name] = {
            "members": actual_support,
            "population_witness": witness,
            "selected_alternative": actual.selected_alternative,
        }
    parameters = {
        "parameters": decode_semantic_value(json.loads(binding.parameters)),
        "replicate": binding.replicate,
    }
    if binding.source_sets != b"{}":
        parameters["source_sets"] = {
            name: [
                {**entry, "analyzed_scope": scope_identity(entry["analyzed_scope"])}
                for entry in scope["entries"]
            ]
            for name, scope in wire_json_loads(binding.source_sets).items()
        }
    reusable = all(asset.reuse_eligible for asset in operation.assets)
    if not reusable and execution_scope is None:
        _fail(operation.semantic_id, "attempt-only execution requires its demand scope")
    request = SemanticRequestKey(
        recipe,
        binding.subject,
        values,
        parameters,
        binding.inference,
        subject_context=binding.subject_context,
        execution_scope=execution_scope if not reusable else None,
    )
    admission = AdmissionManifest(
        request.identity.key,
        identities[operation.semantic_id, "eligibility"],
        {
            "selected_support": support,
            "definition_revision": identities[operation.semantic_id, "definition"],
            "trust_evidence": wire_json_loads(binding.trust_evidence),
        },
        json.loads(binding.authorization),
        binding.execution_profile,
    )
    return request, admission


def _materialize_json_schema_properties(kinds, nodes, edges) -> None:
    """Realize the same closed wire schema as typed model fields, without a shadow catalog."""
    from jsonschema import Draft7Validator

    from .data_operation_wire import (
        KIND_PREFIX,
        json_schema_field_type,
        json_schema_properties,
        schema_closure,
    )

    for kind in tuple(kinds.values()):
        kind_facts = json.loads(kind.facts)
        schema = kind_facts.get("json_schema")
        if schema is None:
            continue
        namespace = kind_facts.get("nominal_namespace") or (
            KIND_PREFIX
            if kind.semantic_id.startswith(KIND_PREFIX) and kind_facts.get("scope") == "native-wire"
            else None
        )
        for name, field_schema, required in json_schema_properties(schema):
            try:
                target, multivalued = json_schema_field_type(
                    field_schema, nominal_namespace=namespace
                )
            except ValueError as exc:
                _fail(
                    kind.semantic_id,
                    "unsupported nominal JSON Schema property projection: " + str(exc),
                )
            if target not in kinds:
                _fail(kind.semantic_id, "wire property range lacks an effective kind: " + target)
            if namespace is not None and target.startswith(namespace):
                local_name = target.removeprefix(namespace)
                definitions = field_schema.get("definitions", {})
                target_facts = json.loads(kinds[target].facts)
                target_schema = target_facts.get("json_schema")
                if kind_facts.get("nominal_namespace") is not None and (
                    target_facts.get("nominal_namespace") != namespace
                    or {origin.source for origin in kinds[target].origins}
                    != {origin.source for origin in kind.origins}
                ):
                    _fail(
                        kind.semantic_id,
                        "local nominal reference differs from its supplied schema owner",
                    )
                if local_name not in definitions or target_schema != schema_closure(
                    definitions[local_name], definitions
                ):
                    _fail(
                        kind.semantic_id,
                        "unsupported nominal JSON Schema property projection: "
                        "local definition differs from its declared wire owner",
                    )
            root = field_schema
            prop_id = kind.semantic_id + "/property/" + name
            prop = PropertyDefinition(
                name,
                prop_id,
                target,
                required,
                multivalued,
                root.get("minItems") if multivalued else None,
                root.get("maxItems") if multivalued else None,
                str(root["minimum"]) if "minimum" in root else None,
                str(root["maximum"]) if "maximum" in root else None,
                root.get("pattern"),
                True,
                nullable=Draft7Validator(field_schema).is_valid(None),
            )
            facts = {**asdict(prop), "json_schema": field_schema}
            kinds[prop_id] = EffectiveKind(
                prop_id, name, "property", canonical_bytes(facts), kind.origins
            )
            edges.extend(
                (
                    SemanticEdge(kind.semantic_id, prop_id, "property", role=name),
                    SemanticEdge(prop_id, target, "range"),
                )
            )
