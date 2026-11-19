"""Compile the native guards for archived declared-operation projections."""

from sqlalchemy import (
    Boolean,
    Integer,
    Text,
    cast,
    column,
    exists,
    func,
    literal,
    or_,
    select,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB, aggregate_order_by

from corpus_structure.schema.integrity import role_name

from .data_operation_model import MODEL_VERSION
from .native_objects import INTERNAL_PROGRAM, native_sql_script
from .native_program import (
    Block,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Perform,
    Raise,
    SelectInto,
    core_variable,
    pg_type,
)
from .native_program_registry import ProgramDeclaration
from .scientific_evidence import SCIENTIFIC_POLICY_INPUT
from .types import SEMANTIC_COMPILER_VERSION


def _json_bytes(value):
    return cast(func.pg_catalog.convert_from(value, "UTF8"), JSONB())


def _elements(value, name, *, text=False):
    unpack = (
        func.pg_catalog.jsonb_array_elements_text if text else func.pg_catalog.jsonb_array_elements
    )
    field = column("value", Text()) if text else column("value", JSONB())
    return unpack(value).table_valued(field).render_derived(name=name).lateral()


def _array(value, *order):
    return func.coalesce(
        func.pg_catalog.jsonb_agg(aggregate_order_by(value, *order)),
        cast(literal("[]"), JSONB()),
    )


def _row_array(rows):
    value = func.pg_catalog.to_jsonb(rows.table_valued(), type_=JSONB())
    return select(_array(value, cast(value, Text()))).select_from(rows)


def _guard(name, source, body, *locals_):
    return ProgramDeclaration(
        NativeRoutine(
            "sem",
            name,
            parameters=(Parameter("r", pg_type("text")),),
            returns=pg_type("void"),
            body=Block(body, tuple(Local(name, pg_type("jsonb")) for name in locals_)),
            security_definer=True,
            search_path=("pg_catalog", "pg_temp"),
        ),
        source=source,
        owner=role_name("publisher"),
        access=INTERNAL_PROGRAM,
    )


def scientific_layout_program(target):
    release_id = core_variable("r", Text())
    recipe = core_variable("recipe", JSONB())
    supported = func.data.execution_contract_descriptor(type_=JSONB())["scientific_report_layout"]
    artifact = target.tables["sem.artifact"]
    return _guard(
        "require_scientific_layout",
        "authoring/scientific-layout.sql",
        (
            SelectInto(
                select(_json_bytes(artifact.c.content)).where(
                    artifact.c.release_id == release_id,
                    artifact.c.artifact_name == SCIENTIFIC_POLICY_INPUT,
                ),
                ("recipe",),
            ),
            If(
                or_(
                    recipe.is_(None),
                    supported.is_(None),
                    func.pg_catalog.jsonb_build_object(
                        "comparison_paths",
                        recipe["comparison_paths"],
                        "array_rules",
                        recipe["array_rules"],
                    ).is_distinct_from(supported),
                ),
                (
                    Raise(
                        func.pg_catalog.format(
                            "unsupported scientific report layout in release %s", release_id
                        ),
                        "23514",
                    ),
                ),
            ),
        ),
        "recipe",
    )


def execution_projection_check_program(target):
    release_id = core_variable("r", Text())
    document = core_variable("document", JSONB())
    actual = core_variable("actual", JSONB())
    expected = core_variable("expected", JSONB())
    release = target.tables["sem.release"]
    registry = target.tables["sem.registry_row"]
    artifact = target.tables["sem.artifact"]
    decision = target.tables["sem.scientific_decision_rule"]
    property_role = target.tables["sem.operation_property_role"]
    manifest = _json_bytes(release.c.manifest_bytes)
    selected_release = release.c.release_id == release_id
    selected_row = registry.c.release_id == release_id

    registry_rows = _elements(document["products"]["registry_rows"], "archived_rows")
    archived_row = registry_rows.c.value

    rules = _elements(_json_bytes(artifact.c.content)["decision_rules"], "decision_rules")
    decision_rows = (
        select(
            release_id.label("release_id"),
            *(
                rules.c.value[name].astext.label(name)
                for name in ("policy_id", "evidence_tier", "agreement", "decision", "decision_tier")
            ),
        )
        .select_from(artifact.join(rules, true()))
        .where(
            artifact.c.release_id == release_id,
            artifact.c.artifact_name == SCIENTIFIC_POLICY_INPUT,
        )
        .subquery("archived_decisions")
    )

    definitions = _elements(document["products"]["definitions"], "definitions")
    definition = definitions.c.value
    properties = _elements(definition["properties"], "properties")
    props = (
        select(definition.label("definition"), properties.c.value.label("property"))
        .select_from(definitions.join(properties, true()))
        .where(
            definition["name"].astext != "SourceRecordProduct",
            ~definition["ancestors"].has_key("SourceRecordProduct"),
        )
        .cte("props")
    )
    declaration, prop = props.c.definition, props.c.property
    groups = _elements(declaration["identity_groups"], "identity_groups")
    members = _elements(groups.c.value, "members", text=True)
    reg = registry.alias("reg")
    body = _json_bytes(reg.c.body)
    roles = (
        select(literal("identity").label("role"))
        .where(
            exists(
                select(1)
                .select_from(groups.join(members, true()))
                .where(members.c.value == prop["name"].astext)
                .correlate(props)
            )
        )
        .union_all(
            select(literal("required"))
            .correlate(props)
            .where(
                or_(
                    cast(prop["required"].astext, Boolean()),
                    func.coalesce(cast(prop["minimum_cardinality"].astext, Integer()), 0) > 0,
                )
            ),
            select(literal("display")).where(
                exists(
                    select(1)
                    .correlate(props)
                    .where(
                        reg.c.release_id == release_id,
                        reg.c.kind == "operation_property",
                        body["class"].astext == declaration["name"].astext,
                        body["property"].astext == prop["iri"].astext,
                        body["cs:role"].astext == "display",
                    )
                )
            ),
        )
        .lateral("roles")
    )
    property_rows = (
        select(
            release_id.label("release_id"),
            declaration["iri"].astext.label("class_id"),
            prop["iri"].astext.label("property_id"),
            roles.c.role,
        )
        .distinct()
        .select_from(props.join(roles, true()))
        .subquery("archived_properties")
    )
    installed_decisions = select(decision).where(decision.c.release_id == release_id).subquery()
    installed_roles = (
        select(property_role).where(property_role.c.release_id == release_id).subquery()
    )

    def refuse(condition, message):
        return If(condition, (Raise(message, "23514"),))

    return _guard(
        "require_execution_projection",
        "authoring/execution-projection-check.sql",
        (
            SelectInto(
                select(_json_bytes(release.c.prepared_bytes)).where(selected_release),
                ("document",),
                strict=True,
            ),
            refuse(
                select(manifest["profile"]["compiler_version"].astext)
                .where(selected_release)
                .scalar_subquery()
                .is_distinct_from(SEMANTIC_COMPILER_VERSION),
                "execution projection requires current compiler ABI; regenerate",
            ),
            SelectInto(
                select(
                    _array(
                        func.pg_catalog.jsonb_build_object(
                            "kind",
                            registry.c.kind,
                            "name",
                            registry.c.name,
                            "body_hex",
                            func.pg_catalog.encode(registry.c.body, "hex"),
                        ),
                        registry.c.kind,
                        registry.c.name,
                    )
                ).where(selected_row),
                ("actual",),
            ),
            SelectInto(
                select(
                    _array(archived_row, archived_row["kind"].astext, archived_row["name"].astext)
                ),
                ("expected",),
            ),
            refuse(actual.is_distinct_from(expected), "archived registry projection differs"),
            refuse(
                ~exists(
                    select(1).where(selected_release, manifest.has_key("data_operation_model"))
                ),
                "execution projection requires current declared data operations",
            ),
            Perform(func.sem.require_archive_bytes(release_id)),
            refuse(
                exists(select(1).where(selected_row, registry.c.kind == "execution_model")),
                "target archive contains legacy execution projection",
            ),
            refuse(
                ~exists(
                    select(1).where(
                        artifact.c.release_id == release_id,
                        artifact.c.artifact_name == "data_operations.json",
                        _json_bytes(artifact.c.content)["version"].astext == MODEL_VERSION,
                    )
                ),
                "unsupported target operation archive",
            ),
            SelectInto(_row_array(decision_rows), ("expected",)),
            SelectInto(_row_array(installed_decisions), ("actual",)),
            refuse(
                actual.is_distinct_from(expected),
                "archived scientific_decision_rule projection differs",
            ),
            SelectInto(_row_array(property_rows), ("expected",)),
            SelectInto(_row_array(installed_roles), ("actual",)),
            refuse(
                actual.is_distinct_from(expected),
                "archived operation_property_role projection differs",
            ),
        ),
        "document",
        "actual",
        "expected",
    )


def execution_projection_check_sql(target) -> str:
    return native_sql_script((execution_projection_check_program(target).render(),)) + "\n"
