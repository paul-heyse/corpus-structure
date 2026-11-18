"""Captured-model lowering and provider-profile admission as typed native programs.

The two digest values are bound by native_sql from the captured kernel/compiler
artifacts after generation. They are values, never parser or identifier templates.
"""

import json

from pglast import ast
from pglast.stream import RawStream
from sqlalchemy import (
    BigInteger,
    Boolean,
    Text,
    and_,
    case,
    cast,
    column,
    func,
    literal,
    literal_column,
    not_,
    null,
    or_,
    select,
    tuple_,
)
from sqlalchemy.dialects.postgresql import JSONB, aggregate_order_by, array, insert

from .native_program import (
    Assign,
    Block,
    ForQuery,
    If,
    Local,
    Parameter,
    Perform,
    Raise,
    Return,
    SelectInto,
    Sql,
    core_variable,
    function,
    pg_type,
    sql_function,
)

SOURCE_DIGEST = "__DDO_SOURCE_DIGEST__"
LOWERING_DIGEST = "__DDO_LOWERING_DIGEST__"


def _json(value):
    return cast(literal(json.dumps(value, separators=(",", ":"))), JSONB())


def _object(*values):
    return func.jsonb_build_object(*values, type_=JSONB())


def _array(*values):
    return func.jsonb_build_array(*values, type_=JSONB())


def _rows(value, name, *, ordinal=False):
    return (
        func.jsonb_array_elements(value)
        .table_valued(
            column("value", JSONB()), **({"with_ordinality": "ordinal"} if ordinal else {})
        )
        .render_derived()
        .alias(name)
    )


def _hash(value):
    return func.encode(func.sha256(value), "hex")


def _decode(value):
    return cast(func.convert_from(value, "UTF8"), JSONB())


def _row(name, table):
    return {field.name: core_variable(name, field.type, field.name) for field in table.c}


def _exists(relation, *conditions):
    return select(1).select_from(relation).where(*conditions).exists()


def _refuse(condition, message, state="P0001"):
    return If(condition, (Raise(message, state),))


def _fields(value, names):
    return Perform(func.ops.ddo_fields(value, array(list(names), type_=Text())))


def _null_record(table):
    return literal_column(
        RawStream()(
            ast.TypeCast(
                arg=ast.A_Const(isnull=True), typeName=pg_type(str(table.schema), table.name)
            )
        )
    )


def _program(
    schema,
    name,
    parameters,
    statements,
    locals_=(),
    *,
    returns="jsonb",
    stable=False,
    immutable=False,
    security=True,
    strict=False,
):
    return function(
        schema,
        name,
        parameters=parameters,
        returns=pg_type(returns),
        body=Block(tuple(statements), tuple(locals_)),
        security_definer=security,
        search_path=("pg_catalog", "pg_temp"),
        volatility="immutable" if immutable else "stable" if stable else None,
        strict=strict,
    )


def _provider_programs(model):
    inputs = model.tables["sem.input"]
    definitions = model.tables["sem.data_operation_definition"]
    runtimes = model.tables["sem.runtime_binding"]
    derivations = model.tables["ops.data_derivation"]
    intents = model.tables["ops.data_completion_intent"]
    release, operation = (
        core_variable("release_", inputs.c.release_id.type),
        core_variable("operation_", JSONB()),
    )
    asset, profile, attestation, manifest = (
        core_variable(name, JSONB()) for name in ("asset", "profile", "attestation", "manifest")
    )
    content = core_variable("content_", inputs.c.content.type)
    assets = _rows(operation["assets"], "assets")
    role = assets.c.value["role"].astext == "provider-inference-profile"
    profile_program = _program(
        "sem",
        "ddo_provider_profile",
        (Parameter("release_", pg_type("text")), Parameter("operation_", pg_type("jsonb"))),
        (
            If(
                select(func.count()).select_from(assets).where(role).scalar_subquery() == 0,
                (Return(null()),),
            ),
            SelectInto(select(assets.c.value).where(role), ("asset",), True),
            SelectInto(
                select(inputs.c.content).where(
                    inputs.c.release_id == release,
                    inputs.c.input_kind == "dependency",
                    inputs.c.input_name == "data-operations/contracts/" + asset["contract"].astext,
                ),
                ("content_",),
                True,
            ),
            _refuse(
                _hash(content).is_distinct_from(asset["content_digest"].astext),
                "provider profile captured digest differs",
            ),
            Assign("profile", _decode(content)),
            _fields(profile, ("version", "identity", "meaning")),
            _refuse(
                or_(
                    profile["version"].astext.is_distinct_from("provider-inference-profile-v1"),
                    *(
                        profile["meaning"][position].is_distinct_from(_json(value))
                        for position, value in enumerate(("ddo", "inference", "1"))
                    ),
                    func.jsonb_array_length(profile["meaning"]).is_distinct_from(4),
                    func.data.ddo_identity("inference", profile["meaning"][3]).is_distinct_from(
                        profile["identity"].astext
                    ),
                    content.is_distinct_from(
                        func.convert_to(func.data.canonical_json(profile), "UTF8")
                    ),
                ),
                "provider profile canonical meaning differs",
            ),
            Return(
                profile.concat(
                    _object(
                        "contract",
                        asset["contract"].astext,
                        "sha256",
                        asset["content_digest"].astext,
                    )
                )
            ),
        ),
        (
            Local("asset", pg_type("jsonb")),
            Local("content_", pg_type("bytea")),
            Local("profile", pg_type("jsonb")),
        ),
        stable=True,
    )
    field, semantic = core_variable("field", JSONB()), core_variable("semantic_fields", JSONB())
    execution_fields = _rows(attestation["execution_meaning"][3][1], "execution_fields")
    semantic_fields = _rows(attestation["execution_meaning"][3][1], "semantic_profile_fields")
    semantic_role = func.data.ddo_field(semantic_fields.c.value[1], "role", type_=JSONB())[1].astext
    role_value = func.data.ddo_field(field[1], "role", type_=JSONB())[1].astext
    attest_program = _program(
        "sem",
        "ddo_validate_provider_attestation",
        (Parameter("attestation", pg_type("jsonb")), Parameter("profile", pg_type("jsonb"))),
        (
            _fields(
                attestation,
                ("version", "identity", "meaning", "execution_identity", "execution_meaning"),
            ),
            _refuse(
                or_(
                    attestation["version"].astext.is_distinct_from(
                        "provider-profile-attestation-v1"
                    ),
                    attestation["identity"].is_distinct_from(profile["identity"]),
                    attestation["meaning"].is_distinct_from(profile["meaning"]),
                    *(
                        attestation["execution_meaning"][position].is_distinct_from(_json(value))
                        for position, value in enumerate(("ddo", "execution-profile", "1"))
                    ),
                    func.jsonb_array_length(attestation["execution_meaning"]).is_distinct_from(4),
                    func.data.ddo_identity(
                        "execution-profile", attestation["execution_meaning"][3]
                    ).is_distinct_from(attestation["execution_identity"].astext),
                ),
                "provider execution attestation differs",
            ),
            ForQuery(
                ("field",),
                select(execution_fields.c.value),
                (
                    _refuse(
                        or_(role_value.is_(None), role_value.not_in(("semantic", "execution"))),
                        "unknown provider projection field role",
                    ),
                ),
            ),
            SelectInto(
                select(
                    _array(
                        "mapping",
                        func.coalesce(
                            func.jsonb_agg(
                                aggregate_order_by(
                                    _array(
                                        semantic_fields.c.value[0],
                                        func.data.ddo_field(semantic_fields.c.value[1], "value"),
                                    ),
                                    semantic_fields.c.value[0].astext.collate("C"),
                                )
                            ),
                            _json([]),
                        ),
                    )
                ).where(semantic_role == "semantic"),
                ("semantic_fields",),
            ),
            _refuse(
                func.data.ddo_identity("inference", semantic).is_distinct_from(
                    profile["identity"].astext
                ),
                "execution profile semantic subset differs",
            ),
        ),
        (Local("semantic_fields", pg_type("jsonb")), Local("field", pg_type("jsonb"))),
        returns="void",
        immutable=True,
        security=False,
    )
    operation_id, runtime_id = (
        core_variable("operation_", definitions.c.operation_id.type),
        core_variable("runtime_", runtimes.c.runtime_id.type),
    )
    definition = _row("definition", definitions)
    require_program = _program(
        "ops",
        "ddo_require_provider_profile",
        (
            Parameter("release_", pg_type("text")),
            Parameter("operation_", pg_type("text")),
            Parameter("runtime_", pg_type("text")),
        ),
        (
            SelectInto(
                select(definitions).where(
                    definitions.c.release_id == release, definitions.c.operation_id == operation_id
                ),
                ("definition",),
                True,
            ),
            Assign("profile", definition["support_contract"]["provider_profile"]),
            If(profile.is_(None), (Return(null()),)),
            SelectInto(
                select(_decode(runtimes.c.manifest_bytes)).where(
                    runtimes.c.release_id == release, runtimes.c.runtime_id == runtime_id
                ),
                ("manifest",),
                True,
            ),
            Assign("attestation", manifest["provider_profiles"][operation_id]),
            _refuse(
                or_(
                    manifest["version"].astext.is_distinct_from(
                        "data-operation-runtime-binding-v2"
                    ),
                    attestation["profile"].is_distinct_from(profile),
                ),
                "runtime lacks authentic producing provider profile",
            ),
            Perform(
                func.sem.ddo_validate_provider_attestation(attestation["attestation"], profile)
            ),
            Return(profile["identity"].astext),
        ),
        (
            Local("definition", definitions),
            Local("manifest", pg_type("jsonb")),
            Local("profile", pg_type("jsonb")),
            Local("attestation", pg_type("jsonb")),
        ),
        returns="text",
        stable=True,
    )
    episode_id = core_variable("episode_", derivations.c.id.type)
    episode, intent = _row("episode", derivations), _row("intent", intents)
    profiles, operation_name = (
        core_variable("profiles", BigInteger()),
        core_variable("operation_", definitions.c.operation_id.type),
    )
    episode_program = _program(
        "ops",
        "ddo_episode_provider_identity",
        (Parameter("episode_", pg_type("text")),),
        (
            SelectInto(
                select(derivations).where(derivations.c.id == episode_id), ("episode",), True
            ),
            SelectInto(
                select(intents).where(intents.c.id == episode["intent_id"]), ("intent",), True
            ),
            _refuse(
                or_(
                    *(
                        intent[name].is_distinct_from(episode[name])
                        for name in ("request_id", "generation", "runtime_id")
                    )
                ),
                "producing provider intent custody differs",
            ),
            SelectInto(
                select(
                    func.count(
                        func.distinct(
                            func.coalesce(
                                definitions.c.support_contract["provider_profile"], _json(None)
                            )
                        )
                    ),
                    func.min(definitions.c.operation_id),
                ).where(
                    definitions.c.release_id == episode["release_id"],
                    definitions.c.recipe == episode["recipe"],
                ),
                ("profiles", "operation_"),
            ),
            _refuse(
                or_(profiles != 1, operation_name.is_(None)),
                "producing recipe provider profile is unavailable or ambiguous",
            ),
            Return(
                func.ops.ddo_require_provider_profile(
                    episode["release_id"], operation_name, intent["runtime_id"]
                )
            ),
        ),
        (
            Local("episode", derivations),
            Local("intent", intents),
            Local("operation_", pg_type("text")),
            Local("profiles", pg_type("bigint")),
        ),
        returns="text",
        stable=True,
    )
    return (profile_program, attest_program, require_program, episode_program)


def _kind_contracts_program():
    model, kind = core_variable("p_model", JSONB()), core_variable("p_kind", Text())
    family = select(kind.label("kind")).cte("family", recursive=True)
    edges = _rows(model["edges"], "edges")
    family = family.union(
        select(edges.c.value["source"].astext)
        .select_from(family.join(edges, literal(True)))
        .where(
            edges.c.value["relation"].astext == "inherits",
            edges.c.value["target"].astext == family.c.kind,
        )
    )
    kinds, identities = _rows(model["kinds"], "kinds"), _rows(model["identities"], "identities")
    query = (
        select(
            func.coalesce(
                func.jsonb_agg(
                    aggregate_order_by(
                        identities.c.value["key"].astext, identities.c.value["key"].astext
                    )
                ),
                _json([]),
            )
        )
        .select_from(
            family.join(kinds, kinds.c.value["semantic_id"].astext == family.c.kind).join(
                identities,
                and_(
                    identities.c.value["owner"].astext == family.c.kind,
                    identities.c.value["domain"].astext == "kind",
                ),
            )
        )
        .where(
            not_(
                func.coalesce(
                    cast(kinds.c.value["facts"]["json"]["abstract"].astext, Boolean()), False
                )
            ),
            func.coalesce(cast(kinds.c.value["complete"].astext, Boolean()), True),
        )
    )
    return sql_function(
        "sem",
        "ddo_input_kind_contracts",
        parameters=(Parameter("p_model", pg_type("jsonb")), Parameter("p_kind", pg_type("text"))),
        returns=pg_type("jsonb"),
        body=query,
        volatility="immutable",
        strict=True,
        search_path=("pg_catalog", "pg_temp"),
    )


def _classify_programs(model):
    operation = core_variable("operation", Text())
    families = (
        ("record-grade", ("record_policy.grade",)),
        ("record-fit", ("record_policy.fit",)),
        (
            "operation-event",
            (
                "operation_event.frame",
                "operation_event.fit",
                "operation_event.authorize",
                "urn:corpus:operation:score-operation-event",
            ),
        ),
        (
            "contextual",
            (
                "retrieve.contextual_query/declared",
                "retrieve.contextual_query/selected-context",
                "retrieve.contextual_target_vector/declared",
                "retrieve.contextual_vectors/selection",
                "retrieve.contextual_targets/curated",
                "retrieve.contextual_targets/components",
                "retrieve.contextual_target/declared",
                "retrieve.contextual_inventory/declared",
                "retrieve.contextual_scores/declared",
                "retrieve.contextual/declared",
                "retrieve.contextual_witnesses/declared",
                "retrieve.contextual/with-witnesses",
            ),
        ),
        (
            "definition",
            (
                "structure.definition_applicability/declared",
                "structure.definition_declaration_components/declared",
                "structure.definition_components/declared",
                "structure.definition_named_components/declared",
            ),
        ),
        ("artifact", ("structure.artifact_identity/declared",)),
        (
            "rich",
            (
                "rich.admit",
                "rich.consolidate",
                "prepare.external_extraction",
                "locate.external_extraction",
            ),
        ),
    )
    validity = sql_function(
        "ops",
        "ddo_classify_validity",
        parameters=(Parameter("operation", pg_type("text")),),
        returns=pg_type("text"),
        body=select(case(*((operation.in_(names), family) for family, names in families))),
        volatility="immutable",
        strict=True,
        search_path=("pg_catalog", "pg_temp"),
    )
    definition = core_variable("definition", JSONB())
    command = _program(
        "ops",
        "ddo_classify_command",
        (Parameter("definition", pg_type("sem", "data_operation_definition")),),
        (
            Return(
                case(
                    *(
                        (
                            getattr(func.ops, "ddo_" + family + "_command_eligible")(definition),
                            family,
                        )
                        for family in ("pdf", "policy", "structural", "rich", "operation_event")
                    )
                )
            ),
        ),
        returns="text",
        immutable=True,
        security=False,
        strict=True,
    )
    return validity, command


def _lowering_program(model, subject_scopes):
    artifacts, kinds, kind_releases, definitions, releases, scopes = (
        model.tables[name]
        for name in (
            "sem.artifact",
            "sem.data_kind_contract",
            "sem.data_kind_release",
            "sem.data_operation_definition",
            "sem.data_operation_release",
            "sem.data_subject_scope",
        )
    )
    (
        p,
        archived,
        k,
        o,
        operation,
        expected_inputs,
        expected_outputs,
        expected_support,
        subject,
        provider,
    ) = (
        core_variable(name, JSONB())
        for name in (
            "p",
            "archived",
            "k",
            "o",
            "operation",
            "expected_inputs",
            "expected_outputs",
            "expected_support",
            "subject_",
            "provider_profile",
        )
    )
    new_release = core_variable("p_new_release", Boolean())
    old, lowered, header = (
        _row("old", kinds),
        _row("lowered", definitions),
        _row("header", releases),
    )
    lowered_value = core_variable("lowered", JSONB())
    subjects = _rows(archived["subject_definitions"], "subjects")
    kind_rows, operation_rows = (
        _rows(p["kinds"], "kind_rows"),
        _rows(p["operations"], "operation_rows"),
    )
    archive_kinds, archive_identities, archive_operations, archive_bindings = (
        _rows(archived[name], "archive_" + name)
        for name in ("kinds", "identities", "operations", "bindings")
    )
    roles = _rows(operation["roles"], "roles", ordinal=True)
    support_roles = _rows(operation["roles"], "support_roles")
    role_identities = _rows(archived["identities"], "role_identities")
    role_contract = (
        select(role_identities.c.value["key"].astext)
        .where(
            role_identities.c.value["owner"].astext == roles.c.value["kind"].astext,
            role_identities.c.value["domain"].astext == "kind",
        )
        .correlate(roles)
        .scalar_subquery()
    )
    base_role = _object(
        "kind_contract",
        role_contract,
        "identity_requirements",
        func.coalesce(roles.c.value["support"]["identity_requirements"], _json([])),
    )
    input_role = base_role.concat(
        _object(
            "accepted_kind_contracts",
            func.sem.ddo_input_kind_contracts(archived, roles.c.value["kind"].astext),
        )
    )

    def role_query(extra, direction):
        return select(
            func.coalesce(
                func.jsonb_agg(aggregate_order_by(roles.c.value.concat(extra), roles.c.ordinal)),
                _json([]),
            )
        ).where(roles.c.value["direction"].astext == direction)

    result_fields = _rows(func.coalesce(operation["result_fields"], _json([])), "result_fields")
    binding_query = (
        select(archive_bindings.c.value["expression"])
        .where(archive_bindings.c.value["semantic_id"].astext == operation["binding"].astext)
        .scalar_subquery()
    )

    def identity_query(owner, domain):
        return (
            select(archive_identities.c.value["key"].astext)
            .where(
                archive_identities.c.value["owner"].astext == owner,
                archive_identities.c.value["domain"].astext == domain,
            )
            .scalar_subquery()
        )

    nodes = select(o["binding"].label("node")).cte("nodes", recursive=True)
    child_nodes = _rows(func.coalesce(nodes.c.node["children"], _json([])), "child_nodes")
    nodes = nodes.union_all(
        select(child_nodes.c.value).select_from(nodes.join(child_nodes, literal(True)))
    )
    quantified = (
        select(1)
        .select_from(nodes)
        .where(nodes.c.node["operator"].astext.in_(("forall", "absent", "membership", "covers")))
        .exists()
    )
    derived_names = (
        "binding_expression",
        "definition_identity",
        "eligibility_identity",
        "quantified",
        "validity_family",
        "command_class",
        "dependencies",
    )
    kind_steps = (
        _refuse(
            not_(
                _exists(
                    archive_kinds,
                    archive_kinds.c.value["semantic_id"].astext == k["kind"].astext,
                    func.coalesce(
                        archive_kinds.c.value["facts"]["json"]["universe"].astext, "ordinary"
                    )
                    == k["universe"].astext,
                    func.coalesce(
                        archive_kinds.c.value["facts"]["json"]["projection_families"], _json([])
                    )
                    == k["families"],
                )
            ),
            "kind purpose/projection policy differs from archived facts",
        ),
        _refuse(
            not_(
                _exists(
                    archive_identities,
                    archive_identities.c.value["owner"].astext == k["kind"].astext,
                    archive_identities.c.value["domain"].astext == "kind",
                    archive_identities.c.value["key"].astext == k["kind_contract"].astext,
                )
            ),
            "kind identity differs from archived effective model",
        ),
        Sql(
            insert(kinds)
            .values(
                kind_contract=k["kind_contract"].astext,
                kind=k["kind"].astext,
                body_schema=k["body_schema"],
                meaning_schema=k["meaning_schema"],
                member_schema=k["member_schema"],
                member_contracts=k["member_contracts"],
                families=k["families"],
                universe=k["universe"].astext,
            )
            .on_conflict_do_nothing()
        ),
        SelectInto(
            select(kinds).where(kinds.c.kind_contract == k["kind_contract"].astext), ("old",), True
        ),
        _refuse(
            or_(
                *(
                    old[name].is_distinct_from(
                        k[name].astext if name in ("kind", "universe") else k[name]
                    )
                    for name in (
                        "kind",
                        "universe",
                        "body_schema",
                        "meaning_schema",
                        "member_schema",
                        "member_contracts",
                        "families",
                    )
                )
            ),
            "kind contract changed under stable identity",
        ),
        Sql(
            insert(kind_releases)
            .values(release_id=p["release_id"].astext, kind_contract=old["kind_contract"])
            .on_conflict_do_nothing()
        ),
    )
    operation_steps = (
        SelectInto(
            select(archive_operations.c.value).where(
                archive_operations.c.value["semantic_id"].astext == o["operation_id"].astext
            ),
            ("operation",),
            True,
        ),
        Perform(func.ops.ddo_replicate_required(operation["replicate_policy"].astext)),
        _refuse(
            not_(
                _exists(
                    subjects, subjects.c.value["semantic_id"].astext == operation["subject"].astext
                )
            ),
            "operation subject has no admitted definition",
        ),
        SelectInto(role_query(input_role, "input"), ("expected_inputs",)),
        SelectInto(role_query(base_role, "output"), ("expected_outputs",)),
        Assign(
            "expected_support",
            _object(
                "policy",
                operation["support_policy"],
                "coverage",
                operation["coverage"],
                "outcomes",
                operation["outcomes"],
                "replicate_policy",
                operation["replicate_policy"],
                "state_dimensions",
                operation["state_dimensions"],
                "transitions",
                operation["transitions"],
                "effects",
                operation["effects"],
                "capabilities",
                operation["capabilities"],
                "provenance",
                case(
                    (
                        _exists(
                            support_roles,
                            support_roles.c.value["support"] != _json(None),
                            support_roles.c.value["support"]["provenance"].astext
                            != "value_substitution",
                        ),
                        "exact",
                    ),
                    else_="value_substitution",
                ),
                "assets",
                operation["assets"],
                "numerical_policy",
                operation["numerical_policy"],
                "result_fields",
                select(
                    func.coalesce(
                        func.jsonb_object_agg(
                            result_fields.c.value[0].astext, result_fields.c.value[1].astext
                        ),
                        _json({}),
                    )
                ).scalar_subquery(),
            ),
        ),
        Assign(
            "provider_profile", func.sem.ddo_provider_profile(p["release_id"].astext, operation)
        ),
        If(
            provider.is_not(None),
            (
                Assign(
                    "expected_support",
                    expected_support.concat(_object("provider_profile", provider)),
                ),
            ),
        ),
        If(
            operation["external"].is_not(None),
            (
                Assign(
                    "expected_support",
                    expected_support.concat(_object("external", operation["external"])),
                ),
            ),
        ),
        If(
            func.coalesce(operation["output_witnesses"], _json([])) != _json([]),
            (
                Assign(
                    "expected_support",
                    expected_support.concat(
                        _object("output_witnesses", operation["output_witnesses"])
                    ),
                ),
            ),
        ),
        _refuse(
            or_(
                o["input_roles"].is_distinct_from(expected_inputs),
                o["output_roles"].is_distinct_from(expected_outputs),
                o["subject_definition"].astext.is_distinct_from(operation["subject"].astext),
                o["support_contract"].is_distinct_from(expected_support),
                o["profile"].is_distinct_from(operation["profile"]),
                o["binding"].is_distinct_from(binding_query),
                o["definition"].astext.is_distinct_from(
                    identity_query(o["operation_id"].astext, "definition")
                ),
                o["eligibility"].astext.is_distinct_from(
                    identity_query(o["operation_id"].astext, "eligibility")
                ),
                o["implementation_revision"].astext.is_distinct_from(
                    func.coalesce(
                        identity_query(
                            operation["implementation_root"].astext, "implementation-slice"
                        ),
                        case(
                            (operation["external"].is_(None), operation["behavior"].astext),
                            else_="external:" + o["recipe"].astext,
                        ),
                    )
                ),
            ),
            "native definition projection disagrees with archived operation facts",
        ),
        _refuse(
            not_(
                _exists(
                    archive_identities,
                    archive_identities.c.value["owner"].astext == o["operation_id"].astext,
                    archive_identities.c.value["domain"].astext == "recipe",
                    archive_identities.c.value["key"].astext == o["recipe"].astext,
                )
            ),
            "recipe differs from archived effective model",
        ),
        Assign(
            "lowered",
            func.jsonb_populate_record(
                _null_record(definitions),
                o.concat(
                    _object(
                        "release_id",
                        p["release_id"].astext,
                        "binding_expression",
                        o["binding"],
                        "definition_identity",
                        o["definition"].astext,
                        "eligibility_identity",
                        o["eligibility"].astext,
                        "dependencies",
                        _object(
                            "required",
                            func.coalesce(operation["dependencies"], _json([])),
                            "potential",
                            func.coalesce(operation["potential_dependencies"], _json([])),
                        ),
                    )
                ),
            ),
        ),
        Assign(
            "lowered",
            func.jsonb_populate_record(
                lowered_value,
                _object(
                    "quantified",
                    quantified,
                    "validity_family",
                    func.ops.ddo_classify_validity(lowered["operation_id"]),
                ),
            ),
        ),
        Assign(
            "lowered",
            func.jsonb_populate_record(
                lowered_value,
                _object("command_class", func.ops.ddo_classify_command(lowered_value)),
            ),
        ),
        Sql(
            insert(definitions)
            .from_select(
                tuple(definitions.c.keys()),
                select(*(lowered[field.name] for field in definitions.c)),
            )
            .on_conflict_do_nothing()
        ),
        If(
            not_(new_release),
            (
                Sql(
                    definitions.update()
                    .values({name: lowered[name] for name in derived_names})
                    .where(
                        definitions.c.release_id == lowered["release_id"],
                        definitions.c.operation_id == lowered["operation_id"],
                        tuple_(*(definitions.c[name] for name in derived_names)).is_distinct_from(
                            tuple_(*(lowered[name] for name in derived_names))
                        ),
                    )
                ),
            ),
        ),
        _refuse(
            not_(
                _exists(
                    definitions,
                    definitions.c.release_id == lowered["release_id"],
                    definitions.c.operation_id == lowered["operation_id"],
                    func.to_jsonb(definitions.table_valued()) == func.to_jsonb(lowered_value),
                )
            ),
            "operation definition changed under admitted release",
        ),
    )
    subject_steps = (
        Sql(
            insert(scopes)
            .values(
                release_id=p["release_id"].astext,
                subject_definition=subject["semantic_id"].astext,
                scope=subject["scope"].astext,
            )
            .on_conflict_do_nothing()
        ),
        _refuse(
            not_(
                _exists(
                    scopes,
                    scopes.c.release_id == p["release_id"].astext,
                    scopes.c.subject_definition == subject["semantic_id"].astext,
                    scopes.c.scope == subject["scope"].astext,
                )
            ),
            "subject scope changed under admitted release",
        ),
    )
    native_projection = and_(
        artifacts.c.release_id == p["release_id"].astext,
        artifacts.c.artifact_name == "data_operation_native_definitions.json",
    )
    statements = (
        _fields(p, ("release_id", "model_digest", "native_digest", "kinds", "operations")),
        _refuse(
            and_(
                new_release,
                p["native_digest"].astext.is_distinct_from(
                    func.sem.data_operation_native_descriptor(type_=JSONB())["source_digest"].astext
                ),
            ),
            "native source correspondence mismatch",
        ),
        SelectInto(
            select(_decode(artifacts.c.content)).where(
                artifacts.c.release_id == p["release_id"].astext,
                artifacts.c.artifact_name == "data_operations.json",
                _hash(artifacts.c.content) == p["model_digest"].astext,
            ),
            ("archived",),
        ),
        _refuse(archived.is_(None), "effective operation archive is absent or differs"),
        _refuse(
            or_(
                func.jsonb_typeof(archived["subject_definitions"]).is_distinct_from("array"),
                _exists(
                    subjects,
                    or_(
                        func.nullif(subjects.c.value["semantic_id"].astext, "").is_(None),
                        not_(_json(subject_scopes).has_key(subjects.c.value["scope"].astext)),
                    ),
                ),
                select(subjects.c.value["semantic_id"].astext)
                .group_by(subjects.c.value["semantic_id"].astext)
                .having(func.count() != 1)
                .exists(),
            ),
            "release subject definitions are unavailable or invalid",
            "23514",
        ),
        _refuse(
            not_(
                _exists(
                    artifacts,
                    native_projection,
                    _decode(artifacts.c.content) == p.op("-", return_type=JSONB())("release_id"),
                )
            ),
            "native definition projection differs from authenticated release artifact",
        ),
        ForQuery(("k",), select(kind_rows.c.value), kind_steps),
        ForQuery(("o",), select(operation_rows.c.value), operation_steps),
        ForQuery(("subject_",), select(subjects.c.value), subject_steps),
        Sql(
            insert(releases)
            .from_select(
                (
                    "release_id",
                    "model_digest",
                    "native_definitions_digest",
                    "native_kernel_digest",
                    "lowering_digest",
                ),
                select(
                    p["release_id"].astext,
                    p["model_digest"].astext,
                    artifacts.c.content_digest,
                    p["native_digest"].astext,
                    literal(LOWERING_DIGEST),
                ).where(native_projection),
            )
            .on_conflict_do_nothing()
        ),
        If(
            not_(new_release),
            (
                Sql(
                    releases.update()
                    .values(lowering_digest=LOWERING_DIGEST)
                    .where(
                        releases.c.release_id == p["release_id"].astext,
                        releases.c.model_digest == p["model_digest"].astext,
                        releases.c.native_kernel_digest == p["native_digest"].astext,
                        releases.c.lowering_digest.is_distinct_from(LOWERING_DIGEST),
                    )
                ),
            ),
        ),
        SelectInto(
            select(releases).where(releases.c.release_id == p["release_id"].astext),
            ("header",),
            True,
        ),
        _refuse(
            or_(
                header["model_digest"].is_distinct_from(p["model_digest"].astext),
                header["native_kernel_digest"].is_distinct_from(p["native_digest"].astext),
                header["lowering_digest"].is_distinct_from(LOWERING_DIGEST),
                header["native_definitions_digest"].is_distinct_from(
                    select(artifacts.c.content_digest).where(native_projection).scalar_subquery()
                ),
            ),
            "release facts changed under admitted release",
        ),
        Perform(func.sem.admit_pdf_operation_contracts(p["release_id"].astext, new_release)),
        Return(
            _object("release_id", p["release_id"].astext, "model_digest", p["model_digest"].astext)
        ),
    )
    return _program(
        "sem",
        "ddo_lower_data_operation_definitions",
        (Parameter("p_payload", pg_type("jsonb")), Parameter("p_new_release", pg_type("bool"))),
        statements,
        (
            Local("p", pg_type("jsonb"), core_variable("p_payload", JSONB())),
            *(
                Local(name, pg_type("jsonb"))
                for name in (
                    "k",
                    "o",
                    "archived",
                    "operation",
                    "expected_inputs",
                    "expected_outputs",
                    "expected_support",
                    "subject_",
                    "provider_profile",
                )
            ),
            Local("old", kinds),
            Local("lowered", definitions),
            Local("header", releases),
        ),
    )


def _relower_program(model):
    finalizations, definitions, artifacts, runtimes = (
        model.tables[name]
        for name in (
            "sem.release_finalization",
            "sem.data_operation_definition",
            "sem.artifact",
            "sem.runtime_binding",
        )
    )
    release = core_variable("p_release", finalizations.c.release_id.type)
    projection, result = core_variable("projection", JSONB()), core_variable("result", JSONB())
    return _program(
        "sem",
        "relower_admitted_data_operation_release",
        (Parameter("p_release", pg_type("text")),),
        (
            _refuse(
                or_(
                    not_(_exists(finalizations, finalizations.c.release_id == release)),
                    not_(_exists(definitions, definitions.c.release_id == release)),
                ),
                "re-lowering requires an already admitted finalized release",
                "23514",
            ),
            SelectInto(
                select(_decode(artifacts.c.content)).where(
                    artifacts.c.release_id == release,
                    artifacts.c.artifact_name == "data_operation_native_definitions.json",
                    _hash(artifacts.c.content) == artifacts.c.content_digest,
                ),
                ("projection",),
                True,
            ),
            Assign(
                "result",
                func.sem.ddo_lower_data_operation_definitions(
                    projection.concat(_object("release_id", release)), False
                ),
            ),
            Sql(
                runtimes.update()
                .values(
                    execution_profile=_decode(runtimes.c.manifest_bytes)["execution_profile"].astext
                )
                .where(runtimes.c.release_id == release, runtimes.c.execution_profile.is_(None))
            ),
            _refuse(
                _exists(
                    runtimes,
                    runtimes.c.release_id == release,
                    func.nullif(runtimes.c.execution_profile, "").is_(None),
                ),
                "admitted runtime lacks an execution profile",
                "23514",
            ),
            Return(result),
        ),
        (Local("projection", pg_type("jsonb")), Local("result", pg_type("jsonb"))),
    )


def compiler_native_sql(model, *, subject_scopes):
    """Compile the one release-lowering owner against its captured physical model."""
    if not subject_scopes or any(
        not isinstance(value, str) or not value for value in subject_scopes
    ):
        raise ValueError("compiler requires the captured closed subject scope vocabulary")
    descriptor = sql_function(
        "sem",
        "data_operation_native_descriptor",
        parameters=(),
        returns=pg_type("jsonb"),
        body=select(_object("version", "data-operation-native-v1", "source_digest", SOURCE_DIGEST)),
        volatility="immutable",
        search_path=("pg_catalog", "pg_temp"),
    )
    admit = _program(
        "sem",
        "admit_data_operation_definitions",
        (Parameter("p_payload", pg_type("jsonb")),),
        (
            Return(
                func.sem.ddo_lower_data_operation_definitions(
                    core_variable("p_payload", JSONB()), True
                )
            ),
        ),
    )
    return (
        ";\n".join(
            (
                descriptor,
                _kind_contracts_program(),
                *_provider_programs(model),
                *_classify_programs(model),
                _lowering_program(model, tuple(subject_scopes)),
                admit,
                _relower_program(model),
            )
        )
        + ";\n"
    )
