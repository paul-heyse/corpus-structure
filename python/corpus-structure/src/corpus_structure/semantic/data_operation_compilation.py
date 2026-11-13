"""Pure phased compilation of declaration/Python operation authoring into one IR.

This is an opt-in foundation. It grants no runtime capability and changes no native
routing. All referenced assets, Python modules and LinkML imports must be supplied.
"""

from __future__ import annotations

import json
from dataclasses import asdict, fields, replace
from typing import Any, Never, cast

import networkx as nx
import yaml
from linkml_runtime.dumpers import json_dumper
from linkml_runtime.utils.yamlutils import DupCheckYamlLoader

from .data_operation_model import (
    MODEL_VERSION,
    BindingExpression,
    BindingField,
    EffectContract,
    EffectiveDataOperationModel,
    EffectiveIdentity,
    EffectiveKind,
    EffectiveOperation,
    FactOrigin,
    ImplementationCapabilities,
    InputSupport,
    OpaqueBoundary,
    OperationRole,
    RelationalBinding,
    SemanticEdge,
    SemanticNode,
    SourceUnknown,
    StateDimension,
    StateTransition,
)
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
_PROFILES = {"derivation", "discovery", "selection", "command", "read"}
_BINDING_OPERATORS = {
    "scan",
    "join",
    "equal",
    "literal",
    "same",
    "distinct",
    "cardinality",
    "collection",
    "all",
    "choice",
    "optional",
    "forall",
    "absent",
}
_METADATA_FIELDS = {
    "id",
    "profile",
    "subject",
    "context",
    "roles",
    "applicability",
    "invariants",
    "coverage",
    "outcomes",
    "precision",
    "dependencies",
    "state_dimensions",
    "transitions",
    "effects",
    "capabilities",
    "behavior",
    "parameters",
    "assets",
    "binding",
    "kinds",
    "entrypoints",
    "opaque",
    "bound_inputs",
    "abstract",
    "replicate_policy",
    "support_policy",
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
        {
            "operator",
            "roles",
            "fields",
            "value",
            "children",
            "minimum",
            "maximum",
            "collection",
            "selected",
            "population",
            "impact",
        },
    )
    operator = value.get("operator")
    if operator not in _BINDING_OPERATORS:
        _fail(operation, "unsupported relational binding construct " + str(operator))
    impact = value.get("impact", "result")
    if impact not in {"result", "eligibility"}:
        _fail(operation, "binding predicate requires result/eligibility semantics")
    selected_roles = _strings(value.get("roles", []), operation + "/binding/roles")
    if not set(selected_roles) <= roles:
        _fail(operation, "binding uses an undeclared role")
    fields = []
    for record in value.get("fields", []):
        record = _mapping(record, operation, {"role", "projection", "field"})
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
    if operator in {"join", "equal"} and len(fields) < 2:
        _fail(operation, operator + " requires qualified projection fields")
    if operator == "literal" and (len(fields) != 1 or "value" not in value):
        _fail(operation, "literal predicates require one field and a typed literal")
    if operator in {"forall", "absent"} and not value.get("population"):
        _fail(operation, "absence/quantification requires an explicitly closed population")
    if operator == "choice" and not value.get("selected"):
        _fail(operation, "alternatives require an explicit selected alternative")
    minimum, maximum = value.get("minimum"), value.get("maximum")
    if minimum is not None and (type(minimum) is not int or minimum < 0):
        _fail(operation, "invalid minimum cardinality")
    if maximum is not None and (type(maximum) is not int or maximum < (minimum or 0)):
        _fail(operation, "incompatible cardinality")
    collection = value.get("collection")
    if collection is not None and collection not in {"scalar", "sequence", "bag", "set"}:
        _fail(operation, "unsupported collection meaning")
    children = tuple(_expression(child, operation, roles) for child in value.get("children", []))
    if operator in {"all", "choice", "optional", "forall"} and not children:
        _fail(operation, operator + " requires a nested binding")
    literal = None
    if "value" in value:
        # Typed semantic codec, including explicit float/decimal lexical representations.
        from .value_codec import value_meaning

        literal = canonical_bytes(value_meaning(value["value"]))
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
    )


def _kind_products(
    bundle: SourceBundle | None,
    definitions: tuple[ClassDefinition, ...] | None,
    vocabularies: tuple[VocabularySnapshot, ...],
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
            EffectiveKind(semantic_id, name, "primitive", canonical_bytes({"primitive": name}))
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
            facts["policies"] = annotations
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
    for field in expression.fields:
        projection = aliases.get(field.projection, field.projection)
        if projection not in kinds:
            _fail(owner, "unresolved binding projection " + field.projection)
        if projection != roles[field.role].kind:
            _fail(owner, "binding projection differs from its qualified role kind")
        property_id = projection + "/property/" + field.field
        if property_id not in kinds:
            _fail(owner, "unresolved binding projection field " + property_id)
        ranges.append(json.loads(kinds[property_id].facts)["range"])
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
    if expression.operator == "choice" and expression.selected not in roles:
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


def compile_data_operations(
    schema: SourceBundle | None = None,
    declarations: tuple[SourceArtifact, ...] = (),
    python_sources: PythonSourceCollection | None = None,
    *,
    definitions: tuple[ClassDefinition, ...] | None = None,
    vocabularies: tuple[VocabularySnapshot, ...] = (),
) -> EffectiveDataOperationModel:
    """Compile the actual supplied inputs; no installed-model or target import fallback."""
    kinds, nodes, edges, aliases = _kind_products(schema, definitions, vocabularies)
    frontend = ClosedPythonSources(python_sources) if python_sources is not None else None
    authored: list[tuple[dict[str, Any], tuple, tuple[FactOrigin, ...], str | None]] = []
    slices = []
    seen_sources: set[str] = set()
    for source in declarations:
        if source.name in seen_sources:
            _fail(source.name, "duplicate operation declaration input")
        seen_sources.add(source.name)
        try:
            raw = _source_values(yaml.load(source.content, Loader=DupCheckYamlLoader))
        except (ValueError, yaml.YAMLError) as exc:
            _fail(source.name, str(exc))
        raw = _mapping(raw, source.name, {"version", "operations", "kinds"})
        if raw.get("version") != MODEL_VERSION:
            _fail(source.name, "unsupported operation declaration version")
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
        for facts in frontend.operations():
            slices.append(facts.implementation)
            authored.append(
                (
                    json.loads(facts.metadata),
                    facts.surfaces,
                    facts.origins,
                    facts.implementation.root,
                )
            )
    # Register all semantic kind owners before resolving any operation/role references.
    for raw, _, origins, _ in authored:
        for record in raw.get("kinds", []):
            record = _mapping(
                record,
                "kinds",
                {
                    "id",
                    "name",
                    "python",
                    "primitive",
                    "scope",
                    "invariants",
                    "interpretation",
                    "references",
                    "json_schema",
                },
            )
            semantic_id = _text(record.get("id"), "kind/id")
            if record.get("json_schema") is not None:
                try:
                    checked_json_schema(record["json_schema"])
                except (ValueError, TypeError) as exc:
                    _fail(semantic_id, "invalid closed wire schema: " + str(exc))
                if record.get("python") or record.get("primitive"):
                    _fail(semantic_id, "wire schema kind cannot claim a second representation authority")
            facts = dict(record)
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
                json_schema_category(record["json_schema"]) if record.get("json_schema") is not None else "class" if record.get("python") else "primitive",
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
    _materialize_json_schema_properties(kinds, nodes, edges)
    operations = []
    bindings = []
    for raw, surfaces, origins, implementation_root in authored:
        raw = _mapping(raw, "operation", _METADATA_FIELDS)
        semantic_id = _text(raw.get("id"), "operation/id")
        if any(operation.semantic_id == semantic_id for operation in operations):
            _fail(semantic_id, "duplicate operation semantic identity")
        if raw.get("profile") not in _PROFILES:
            _fail(semantic_id, "operation requires an explicit supported profile")
        roles = []
        role_names = set()
        for record in raw.get("roles", []):
            record = _mapping(
                record,
                semantic_id,
                {
                    "name",
                    "kind",
                    "direction",
                    "minimum",
                    "maximum",
                    "collection",
                    "presence",
                    "support",
                    "parameter",
                    "alternatives",
                    "selected",
                },
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
            if direction not in {"input", "output"}:
                _fail(semantic_id, "role direction must be explicit")
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
                    {
                        "provenance",
                        "source",
                        "coverage",
                        "authorization",
                        "closure",
                        "identity_requirements",
                    },
                )
                if data.get("provenance") not in {"exact", "value_substitution"}:
                    _fail(semantic_id, "input provenance substitution policy must be explicit")
                identity_requirements = _strings(data.get("identity_requirements", []), semantic_id)
                if not set(identity_requirements) <= {"episode", "provider", "alternative"}:
                    _fail(semantic_id, "unsupported input support identity dimension")
                if data["provenance"] == "exact" and "episode" not in identity_requirements:
                    _fail(semantic_id, "exact provenance requires explicit episode identity")
                support = InputSupport(
                    data["provenance"],
                    _text(data.get("source"), semantic_id),
                    _text(data.get("coverage"), semantic_id),
                    _strings(data.get("authorization", []), semantic_id),
                    _strings(data.get("closure", []), semantic_id),
                    cast(Any, identity_requirements),
                )
            elif record.get("support") is not None:
                _fail(semantic_id, "support requirements belong to input roles")
            alternatives = _strings(record.get("alternatives", []), semantic_id)
            selected = record.get("selected")
            if presence == "alternative" and (not alternatives or selected not in alternatives):
                _fail(semantic_id, "alternative roles require a selected declared alternative")
            if presence != "alternative" and (alternatives or selected is not None):
                _fail(semantic_id, "only alternative roles carry a selected alternative")
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
                )
            )
        if semantic_id in kinds or semantic_id in nodes:
            _fail(semantic_id, "semantic operation identity collides with another owned fact")
        if not roles:
            _fail(semantic_id, "operation requires named input/output roles")
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
        dimensions = []
        for record in raw.get("state_dimensions", []):
            record = _mapping(record, semantic_id, {"name", "values"})
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
            record = _mapping(
                record, semantic_id, {"name", "authorization", "idempotency", "fulfillment"}
            )
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
            record = _mapping(
                record, semantic_id, {"dimension", "before", "after", "outcome", "effects"}
            )
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
        capabilities = _mapping(
            raw.get("capabilities"),
            semantic_id,
            {"forms", "preparation", "cancellation", "ownership", "limits"},
        )
        forms = _strings(capabilities.get("forms"), semantic_id, empty=False)
        if not set(forms) <= {"scalar", "batch", "stream"}:
            _fail(semantic_id, "unsupported invocation capability")
        capability = ImplementationCapabilities(
            cast(Any, forms),
            _text(capabilities.get("preparation"), semantic_id),
            _text(capabilities.get("cancellation"), semantic_id),
            _text(capabilities.get("ownership"), semantic_id),
            _strings(capabilities.get("limits", []), semantic_id),
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
        assets = tuple(OpaqueBoundary(**record) for record in raw.get("assets", []))
        from .data_operation_identity import validate_opaque_boundary

        for asset in assets:
            try:
                validate_opaque_boundary(asdict(asset))
            except ValueError as exc:
                _fail(semantic_id, "invalid captured semantic asset: " + str(exc))
        operation = EffectiveOperation(
            semantic_id,
            raw["profile"],
            _text(raw.get("subject"), semantic_id),
            _strings(raw.get("context"), semantic_id),
            tuple(roles),
            _strings(raw.get("applicability"), semantic_id),
            _strings(raw.get("invariants"), semantic_id),
            _text(raw.get("coverage"), semantic_id),
            outcomes,
            _text(raw.get("precision"), semantic_id),
            _strings(raw.get("dependencies"), semantic_id),
            tuple(dimensions),
            tuple(transitions),
            tuple(effects),
            capability,
            _text(raw.get("behavior"), semantic_id),
            canonical_bytes(_mapping(raw.get("parameters", {}), semantic_id)),
            assets,
            surfaces,
            implementation_root,
            origins,
            binding_id,
            _text(raw.get("replicate_policy", "deterministic-single-result"), semantic_id),
            _text(raw.get("support_policy", "all-declared-input-support"), semantic_id),
        )
        operations.append(operation)
        nodes[semantic_id] = SemanticNode(semantic_id, "operation", operation.definition)

        # Binding bytes retain the complete closed vocabulary
        # and explicitly export typed literal payloads.
        def binding_payload(expression):
            data = asdict(expression)
            data["value"] = json.loads(expression.value) if expression.value is not None else None
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
    for semantic_id, kind in kinds.items():
        nodes[semantic_id] = SemanticNode(semantic_id, "kind:" + kind.category, kind.facts)
    for edge in edges:
        if edge.source not in nodes or edge.target not in nodes:
            _fail(edge.source, "unresolved typed semantic reference " + edge.target)
    for relation in ("inherits", "operation_dependency"):
        graph = nx.DiGraph()
        graph.add_nodes_from(nodes)
        graph.add_edges_from((e.source, e.target) for e in edges if e.relation == relation)
        cyclic = [
            tuple(sorted(component))
            for component in nx.strongly_connected_components(graph, backend="networkx")
            if len(component) > 1 or any(graph.has_edge(node, node) for node in component)
        ]
        if cyclic:
            _fail("model/" + relation, "unsupported cycle: " + repr(sorted(cyclic)))
    model = EffectiveDataOperationModel(
        MODEL_VERSION,
        tuple(kinds[key] for key in sorted(kinds)),
        tuple(sorted(operations, key=lambda o: o.semantic_id)),
        tuple(sorted(bindings, key=lambda b: b.semantic_id)),
        tuple(nodes[key] for key in sorted(nodes)),
        tuple(sorted(edges, key=lambda e: (e.source, e.target, e.relation, e.role))),
        tuple(slices),
    )

    return replace(model, identities=_compile_identities(model))


def _binding_record(expression: BindingExpression, *, result_only: bool = False) -> dict | None:
    if result_only and expression.impact == "eligibility":
        return None
    data: dict[str, Any] = asdict(expression)
    data["value"] = json.loads(expression.value) if expression.value is not None else None
    data["children"] = [
        record
        for child in expression.children
        if (record := _binding_record(child, result_only=result_only)) is not None
    ]
    return data


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

    graph = SemanticGraph(model.semantic_records())
    identities = []
    kinds = {}
    incomplete_kinds = {kind.semantic_id for kind in model.kinds if not kind.complete}
    for kind in model.kinds:
        if incomplete_kinds.intersection(graph.closure((kind.semantic_id,))):
            continue
        identity = kind_fingerprint(graph, kind.semantic_id)
        kinds[kind.semantic_id] = identity.key
        identities.append(
            EffectiveIdentity(
                kind.semantic_id, identity.domain, identity.key, identity.canonical_input
            )
        )
    slices = {}
    for implementation in model.implementation_slices:
        if implementation.complete:
            identity = implementation_slice_fingerprint(
                implementation.semantic_records(), implementation.root
            )
            slices[implementation.root] = identity
            identities.append(
                EffectiveIdentity(
                    implementation.root, identity.domain, identity.key, identity.canonical_input
                )
            )
    bindings = {binding.semantic_id: binding for binding in model.bindings}
    for operation in model.operations:
        binding = bindings[operation.binding]
        if any(role.kind not in kinds for role in operation.roles):
            continue
        kind_contracts = {role.name: kinds[role.kind] for role in operation.roles}
        definition = definition_fingerprint(
            {
                "definition": json.loads(operation.definition),
                "binding": _binding_record(binding.expression),
                "kind_contracts": kind_contracts,
            }
        )
        eligibility = eligibility_fingerprint(
            {
                "eligibility": json.loads(operation.eligibility),
                "binding": _binding_record(binding.expression),
            }
        )
        identities += [
            EffectiveIdentity(
                operation.semantic_id, identity.domain, identity.key, identity.canonical_input
            )
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
            {
                "recipe": json.loads(operation.recipe),
                "kind_contracts": kind_contracts,
                "binding": _binding_record(binding.expression, result_only=True),
            },
            implementation_slices=implementation_slices,
        )
        identities.append(
            EffectiveIdentity(
                operation.semantic_id, recipe.domain, recipe.key, recipe.canonical_input
            )
        )
    return tuple(identities)


def project_operation_binding(model: EffectiveDataOperationModel, binding):
    """Construct DDO-02 request/admission identities from the compiled role policies.

    This pure projection does not resolve native rows, assert support validity or
    authorize execution. It preserves their supplied evidence for later admission.
    """
    from .data_operation_identity import (
        AdmissionManifest,
        CollectionValue,
        OptionalValue,
        SemanticRequestKey,
    )

    operation = model.operation(binding.operation)
    identities = {(item.owner, item.domain): item.key for item in model.identities}
    recipe = identities.get((operation.semantic_id, "recipe"))
    if recipe is None:
        _fail(operation.semantic_id, "reusable identity has unknown implementation determinants")
    if operation.replicate_policy == "deterministic-single-result":
        if binding.replicate is not None:
            _fail(
                operation.semantic_id, "deterministic operation does not admit replicate selection"
            )
    elif operation.replicate_policy == "explicit-replicates":
        _text(binding.replicate, operation.semantic_id + "/replicate")
    else:
        _fail(operation.semantic_id, "unsupported replicate identity policy")
    input_roles = {role.name: role for role in operation.roles if role.direction == "input"}
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
            for value in (member.product, member.subject, member.original_source):
                _text(value, name)
            if type(member.multiplicity) is not int or member.multiplicity < 1:
                _fail(name, "invalid bound member multiplicity")
            if member.position is not None and (
                type(member.position) is not int or member.position < 0
            ):
                _fail(name, "invalid bound member position")
            if member.kind_contract != identities[role.kind, "kind"]:
                _fail(name, "bound member kind contract differs from the compiled kind")
            if role.collection == "sequence" and member.position is None:
                _fail(name, "ordered members require explicit positions")
            value = {
                "product": member.product,
                "kind": member.kind_contract,
                "subject": member.subject,
                "member": member.member,
                "original_source": member.original_source,
                "analyzed_scope": json.loads(member.analyzed_scope),
                "coverage": json.loads(member.coverage),
                "position": member.position,
                "multiplicity": member.multiplicity,
            }
            assert role.support is not None
            if "episode" in role.support.identity_requirements:
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
                    "episodes": member.support_episodes,
                    "evidence": json.loads(member.support_evidence),
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
                expression.operator in {"forall", "absent"}
                and (not expression.roles or role_name in expression.roles)
            ) or any(requires_population(child, role_name) for child in expression.children)

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
            json.loads(actual.population_witness) if actual.population_witness is not None else None
        )
        values[name] = {
            "value": OptionalValue(actual.state, collection if actual.state == "present" else None),
            "population_witness": witness,
            "selected_alternative": actual.selected_alternative,
        }
        support[name] = {
            "members": actual_support,
            "population_witness": witness,
            "selected_alternative": actual.selected_alternative,
        }
    request = SemanticRequestKey(
        recipe,
        binding.subject,
        values,
        {"parameters": json.loads(binding.parameters), "replicate": binding.replicate},
        binding.inference,
    )
    admission = AdmissionManifest(
        request.identity.key,
        identities[operation.semantic_id, "eligibility"],
        {
            "selected_support": support,
            "definition_revision": identities[operation.semantic_id, "definition"],
            "trust_evidence": json.loads(binding.trust_evidence),
        },
        json.loads(binding.authorization),
        binding.execution_profile,
    )
    return request, admission



def _materialize_json_schema_properties(kinds, nodes, edges) -> None:
    """Realize the same closed wire schema as typed model fields, without a shadow catalog."""
    from .data_operation_wire import json_schema_field_type, json_schema_properties

    for kind in tuple(kinds.values()):
        schema = json.loads(kind.facts).get("json_schema")
        if schema is None:
            continue
        for name, field_schema, required in json_schema_properties(schema):
            target, multivalued = json_schema_field_type(field_schema)
            if target not in kinds:
                _fail(kind.semantic_id, "wire property range lacks an effective kind: " + target)
            root = field_schema
            prop_id = kind.semantic_id + "/property/" + name
            prop = PropertyDefinition(
                name, prop_id, target, required, multivalued,
                root.get("minItems") if multivalued else None,
                root.get("maxItems") if multivalued else None,
                str(root["minimum"]) if "minimum" in root else None,
                str(root["maximum"]) if "maximum" in root else None,
                root.get("pattern"), True,
            )
            facts = {**asdict(prop), "json_schema": field_schema}
            kinds[prop_id] = EffectiveKind(prop_id, name, "property", canonical_bytes(facts), kind.origins)
            edges.extend((SemanticEdge(kind.semantic_id, prop_id, "property", role=name), SemanticEdge(prop_id, target, "range")))
