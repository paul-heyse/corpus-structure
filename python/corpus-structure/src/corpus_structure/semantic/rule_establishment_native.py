"""Bind rule conclusions to settled producer attestations and exact live inputs."""

from sqlalchemy import Text, and_, case, cast, column, func, literal, null, or_, select, true
from sqlalchemy.dialects.postgresql import JSONB, aggregate_order_by, array, insert
from sqlalchemy.types import NullType

from corpus_structure.schema.integrity import role_name

from .binding_recursive_native import _check, _elements, _json, _texts
from .established_validity import RuleAttestation
from .native_objects import INTERNAL_PROGRAM
from .native_program import (
    Block,
    ForQuery,
    Local,
    NativeRoutine,
    Parameter,
    Perform,
    PerformQuery,
    SelectInto,
    Sql,
    core_variable,
    pg_type,
)
from .native_program_registry import ProgramDeclaration


def _routine(name, parameters, statements, locals_=(), *, stable=False):
    return NativeRoutine(
        "ops",
        name,
        parameters=tuple(Parameter(name, pg_type(*type_)) for name, *type_ in parameters),
        returns=pg_type("void"),
        volatility="stable" if stable else None,
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(tuple(statements), tuple(locals_)),
    )


def _whole_or_partition(rule, partition):
    return or_(
        rule.c.specification["scope"].astext == "product",
        and_(
            rule.c.specification["scope"].astext.in_(("partition", "partition-pair")),
            partition.c.partition_key.is_not(None),
        ),
    )


def _rule_partition(rule, partition, product_id):
    return and_(
        rule.c.specification["scope"].astext.in_(("partition", "partition-pair")),
        partition.c.product_id == product_id,
        partition.c.collection == rule.c.specification["collection"].astext,
    )


def _rule_premise(specification, product_id, partition_key, target_product=None, target_partition=None):
    return func.ops.ddo_rule_premise(
        specification, product_id, partition_key, target_product, target_partition, type_=Text()
    )


def _input_reads(specification):
    return func.coalesce(specification["parameters"]["input_reads"], _json("{}"), type_=JSONB())


def _with_input_reads(model, base, reads, episode):
    """Reproduce the observed role premises from exact native producing input occurrences."""
    inputs = model.tables["ops.data_derivation_input"].alias("observed_inputs")
    parent = model.tables["kb.data_product"].alias("observed_product")
    member = model.tables["kb.data_product_member"].alias("observed_member")
    roles = (
        func.jsonb_each(reads)
        .table_valued(column("key", Text()), column("value", JSONB()))
        .render_derived(name="observed_roles")
    )
    fields = (
        func.jsonb_array_elements_text(roles.c.value)
        .table_valued(column("value", Text()), with_ordinality="ordinality")
        .render_derived(name="observed_paths")
    )
    body = case((inputs.c.member_id.is_(None), parent.c.canonical_body), else_=member.c.body)
    digest = case(
        (inputs.c.member_id.is_(None), parent.c.body_digest),
        else_=func.data.ddo_identity("body", member.c.body, type_=Text()),
    )
    observed_fields = (
        select(
            func.jsonb_agg(
                aggregate_order_by(
                    case(
                        (fields.c.value == "$all", func.to_jsonb(digest, type_=JSONB())),
                        else_=func.ops.ddo_partition_field(body, fields.c.value, type_=JSONB()),
                    ),
                    fields.c.ordinality,
                )
            )
        )
        .select_from(fields)
        .correlate(roles, inputs, parent, member)
        .scalar_subquery()
    )
    observed_role = (
        select(
            func.coalesce(
                func.jsonb_agg(
                    aggregate_order_by(
                        func.jsonb_build_array(inputs.c.multiplicity, observed_fields),
                        inputs.c.position,
                    )
                ),
                _json("[]"),
            )
        )
        .select_from(
            inputs.join(parent, parent.c.id == inputs.c.product_id).outerjoin(
                member,
                and_(
                    member.c.product_id == inputs.c.product_id,
                    member.c.member_id == inputs.c.member_id,
                ),
            )
        )
        .where(inputs.c.derivation_id == episode, inputs.c.role == roles.c.key)
        .correlate_except(inputs, parent, member)
        .scalar_subquery()
    )
    role_values = (
        select(
            func.jsonb_agg(
                aggregate_order_by(
                    func.jsonb_build_array(roles.c.key, observed_role),
                    func.convert_to(roles.c.key, literal("UTF8")),
                )
            )
        )
        .select_from(roles)
        .correlate_except(roles)
        .scalar_subquery()
    )
    return case(
        (reads == _json("{}"), base),
        else_=func.data.ddo_identity(
            "rule-observed-premise",
            func.data.ddo_json_meaning(func.jsonb_build_array(base, role_values)),
            type_=Text(),
        ),
    )


def _request_field(request, field):
    return core_variable("r", request.c[field].type, field)


def _attestations():
    completion = core_variable("completion", JSONB())
    return func.coalesce(completion["execution_evidence"]["rule_attestations"], _json("[]"))


def _attestation_shape():
    assertions = _elements(_attestations(), "assertions")
    assertion = core_variable("assertion", JSONB())
    strings = ("rule_id", "rule_fingerprint", "premise", "output_role")
    return _routine(
        "ddo_require_rule_assertion_shape",
        (("completion", "jsonb"),),
        (
            _check(
                func.jsonb_typeof(_attestations()).is_distinct_from("array"),
                "rule attestations must be an array",
                "23514",
            ),
            ForQuery(
                ("assertion",),
                select(assertions.c.value),
                (
                    Perform(
                        func.ops.ddo_fields(
                            assertion, array(tuple(RuleAttestation.model_fields), type_=Text())
                        )
                    ),
                    _check(
                        or_(
                            *(
                                or_(
                                    func.jsonb_typeof(assertion[field]).is_distinct_from("string"),
                                    assertion[field].astext == "",
                                )
                                for field in strings
                            ),
                            func.jsonb_typeof(assertion["output_position"]).is_distinct_from(
                                "number"
                            ),
                            ~assertion["output_position"].astext.regexp_match(r"^(0|[1-9][0-9]*)$"),
                            ~func.jsonb_typeof(assertion["partition_key"]).in_(("null", "string")),
                            assertion["partition_key"].astext == "",
                        ),
                        "invalid rule attestation",
                        "23514",
                    ),
                ),
            ),
        ),
        (Local("assertion", pg_type("jsonb")),),
        stable=True,
    )


def _settle_attestations(model):
    rules = model.tables["sem.data_rule"]
    conclusions = model.tables["kb.data_validity"]
    establishments = model.tables["kb.data_validity_establishment"]
    request = model.tables["ops.data_request"]
    outputs = model.tables["ops.data_derivation_output"]
    product = model.tables["kb.data_product"]
    partition = model.tables["kb.data_product_partition"]
    episode = core_variable("episode", Text())
    release = _request_field(request, "release_id")
    operation = _request_field(request, "operation_id")
    # Checker identities govern which assertion can establish a conclusion. The premise
    # uses the retained data scope and observed facts, which identical rules can share.
    specification = rules.c.specification.op("-")(
        array(("id", "fingerprint", "checker_callable", "checker_determinant"), type_=Text())
    )
    targets = (
        select(
            rules.c.rule_id,
            rules.c.fingerprint.label("rule_fingerprint"),
            specification.label("premise_specification"),
            product.c.id.label("product_id"),
            outputs.c.role,
            outputs.c.position,
            partition.c.partition_key,
        )
        .select_from(
            outputs.join(product, product.c.id == outputs.c.product_id)
            .join(
                rules,
                and_(
                    rules.c.release_id == release,
                    rules.c.kind_contract == product.c.kind_contract,
                    rules.c.specification["checker"].astext == "producer",
                    rules.c.specification["checker_operation"].astext == operation,
                ),
            )
            .outerjoin(partition, _rule_partition(rules, partition, product.c.id))
        )
        .where(
            outputs.c.derivation_id == episode,
            outputs.c.member_id.is_(None),
            _whole_or_partition(rules, partition),
        )
        .cte("attestation_targets")
    )
    needed = (
        select(targets.c.product_id, targets.c.partition_key, targets.c.premise_specification)
        .distinct()
        .subquery("distinct_attestation_premises")
    )
    premises = (
        select(
            needed,
            _with_input_reads(
                model,
                _rule_premise(
                    needed.c.premise_specification, needed.c.product_id, needed.c.partition_key
                ),
                _input_reads(needed.c.premise_specification),
                episode,
            ).label("premise"),
        )
        .cte("attestation_premises")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )
    expected = (
        select(
            targets.c.rule_id,
            targets.c.rule_fingerprint,
            premises.c.premise,
            targets.c.role,
            targets.c.position,
            targets.c.partition_key,
        )
        .select_from(
            targets.join(
                premises,
                and_(
                    targets.c.product_id == premises.c.product_id,
                    targets.c.partition_key.is_not_distinct_from(premises.c.partition_key),
                    targets.c.premise_specification == premises.c.premise_specification,
                ),
            )
        )
        .cte("expected_attestation")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )
    supplied = _elements(_attestations(), "supplied_attestation")
    assertion = supplied.c.value
    matches = and_(
        expected.c.rule_id == assertion["rule_id"].astext,
        expected.c.rule_fingerprint == assertion["rule_fingerprint"].astext,
        expected.c.premise == assertion["premise"].astext,
        expected.c.role == assertion["output_role"].astext,
        cast(expected.c.position, Text()) == assertion["output_position"].astext,
        expected.c.partition_key.is_not_distinct_from(assertion["partition_key"].astext),
    )
    # Group by exact target so duplicates cannot hide a missing assertion.
    matched = (
        select(
            expected.c.rule_fingerprint,
            expected.c.premise,
            expected.c.role,
            expected.c.position,
            expected.c.rule_id,
            expected.c.partition_key,
            func.count(assertion).label("assertion_count"),
        )
        .select_from(expected.outerjoin(supplied, matches))
        .group_by(*expected.c)
        .cte("matched_attestation")
    )
    admitted = core_variable("admitted", JSONB())
    message = core_variable("failure", Text())
    check = select(
        func.coalesce(
            func.jsonb_agg(
                func.jsonb_build_object(
                    "rule_fingerprint",
                    matched.c.rule_fingerprint,
                    "premise",
                    matched.c.premise,
                    "role",
                    matched.c.role,
                    "position",
                    matched.c.position,
                    type_=JSONB(),
                )
            ),
            _json("[]"),
        ),
        func.min(
            func.format(
                "missing or conflicting rule attestation %s at %s:%s/%s",
                matched.c.rule_id,
                matched.c.role,
                matched.c.position,
                func.coalesce(matched.c.partition_key, "product"),
            )
        ).filter(matched.c.assertion_count != 1),
    ).select_from(matched)
    matched_count = func.jsonb_array_length(admitted)
    accepted = _elements(admitted, "accepted_attestation").c.value
    accepted_targets = (
        select(
            accepted["rule_fingerprint"].astext.label("rule_fingerprint"),
            accepted["premise"].astext.label("premise"),
            accepted["role"].astext.label("role"),
            cast(accepted["position"].astext, outputs.c.position.type).label("position"),
        )
        .distinct()
        .subquery("accepted_target")
    )
    conclude = (
        insert(conclusions)
        .from_select(
            ("rule_fingerprint", "premise"),
            select(accepted_targets.c.rule_fingerprint, accepted_targets.c.premise).distinct(),
        )
        .on_conflict_do_nothing()
    )
    establish = (
        insert(establishments)
        .from_select(
            (
                "rule_fingerprint",
                "premise",
                "derivation_id",
                "role",
                "position",
                "created_at",
                "created_xid",
            ),
            select(
                accepted_targets.c.rule_fingerprint,
                accepted_targets.c.premise,
                episode,
                accepted_targets.c.role,
                accepted_targets.c.position,
                func.clock_timestamp(),
                cast(func.pg_current_xact_id(), Text()),
            ),
        )
        .on_conflict_do_nothing()
    )
    output_products = (
        select(product.c.id, product.c.kind_contract)
        .select_from(outputs.join(product, product.c.id == outputs.c.product_id))
        .where(outputs.c.derivation_id == episode, outputs.c.member_id.is_(None))
        .distinct()
        .subquery("output_product")
    )

    return _routine(
        "ddo_settle_rule_attestations",
        (("r", "ops", "data_request"), ("completion", "jsonb"), ("episode", "text")),
        (
            PerformQuery(
                select(
                    func.ops.ddo_apply_bound_product_rules(
                        release, output_products.c.id, output_products.c.kind_contract, episode
                    )
                ).select_from(output_products)
            ),
            SelectInto(check, ("admitted", "failure"), strict=True),
            _check(
                or_(
                    message.is_not(None), func.jsonb_array_length(_attestations()) != matched_count
                ),
                func.coalesce(message, "undeclared rule attestation"),
                "23514",
            ),
            Sql(conclude),
            Sql(establish),
        ),
        (Local("admitted", pg_type("jsonb")), Local("failure", pg_type("text"))),
    )


def _bound_rules(model):
    rule = model.tables["sem.data_rule"]
    conclusion = model.tables["kb.data_validity"]
    establishment = model.tables["kb.data_validity_establishment"]
    request = model.tables["ops.data_request"]
    outputs = model.tables["ops.data_derivation_output"]
    product = model.tables["kb.data_product"]
    partition = model.tables["kb.data_product_partition"]
    target = product.alias("pair_target")
    target_kind = model.tables["sem.data_kind_contract"].alias("pair_target_kind")
    boundary = core_variable("boundary", NullType())
    locked = core_variable("locked", JSONB())
    release = core_variable("p_release", Text())
    project = _request_field(request, "project_id")
    source = _request_field(request, "original_source")
    manifest = core_variable("manifest", JSONB())
    roles = _elements(core_variable("roles", JSONB()), "declared_role")
    inputs = _elements(manifest, "selected_input")
    required = _texts(func.coalesce(roles.c.value["required_rules"], _json("[]")), "required_rule")
    role = roles.c.value["name"].astext
    input_ = inputs.c.value
    spec = rule.c.specification
    pair = spec["scope"].astext == "partition-pair"
    parameters = spec["parameters"]
    target_role = parameters["target_role"].astext
    target_inputs = _elements(manifest, "pair_target_input")
    target_input = target_inputs.c.value
    target_matches = and_(
        target_input["member_id"].astext.is_(None),
        target_input["multiplicity"].astext == "1",
        target.c.project_id == project,
        target_kind.c.kind == parameters["target_kind"].astext,
    )
    target_id = (
        select(func.min(target.c.id))
        .select_from(
            target_inputs.outerjoin(
                target, target.c.id == target_input["product_id"].astext
            ).outerjoin(target_kind, target_kind.c.kind_contract == target.c.kind_contract)
        )
        .where(
            target_input["role"].astext == target_role,
        )
        .having(and_(func.count() == 1, func.bool_and(target_matches).is_(True)))
        .correlate(rule)
        .scalar_subquery()
    )
    target_product = case((target_role.is_(None), product.c.id), else_=target_id)
    target_partition = func.ops.ddo_rule_target_partition(
        spec, product.c.id, partition.c.partition_key, type_=Text()
    )
    applicable = and_(
        rule.c.kind_contract == product.c.kind_contract,
        product.c.project_id == project,
        input_["member_id"].astext.is_(None),
        _whole_or_partition(rule, partition),
    )
    available = (
        select(
            role.label("role_name"),
            required.c.value.label("rule_id"),
            partition.c.partition_key,
            rule.c.fingerprint,
            spec["checker"].astext.label("checker"),
            _input_reads(spec).label("input_reads"),
            product.c.id.label("product_id"),
            case(
                (
                    and_(applicable, pair, target_product.is_not(None)),
                    _rule_premise(
                        rule.c.specification,
                        product.c.id,
                        partition.c.partition_key,
                        target_product,
                        target_partition,
                    ),
                ),
                (
                    and_(applicable, ~pair),
                    _rule_premise(rule.c.specification, product.c.id, partition.c.partition_key),
                ),
                else_=null(),
            ).label("premise"),
        )
        .select_from(
            roles.join(required, true())
            .join(inputs, input_["role"].astext == role)
            .join(product, product.c.id == input_["product_id"].astext)
            .outerjoin(
                rule,
                and_(rule.c.release_id == release, rule.c.rule_id == required.c.value),
            )
            .outerjoin(partition, _rule_partition(rule, partition, product.c.id))
        )
        .where(
            # A declared partition rule over a valid empty collection is vacuous.
            or_(
                _whole_or_partition(rule, partition),
                rule.c.rule_id.is_(None),
                rule.c.kind_contract.is_distinct_from(product.c.kind_contract),
                product.c.project_id.is_distinct_from(project),
                input_["member_id"].astext.is_not(None),
                spec["scope"].astext.not_in(("product", "partition", "partition-pair")),
            )
        )
        .cte("available_premises")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )
    # Avoid proving a mismatched parent through a coincidentally equal proof key.
    selected = available
    content_matches = (
        select(1)
        .select_from(conclusion)
        .where(
            conclusion.c.rule_fingerprint == selected.c.fingerprint,
            conclusion.c.premise == selected.c.premise,
        )
        .exists()
    )
    references = func.jsonb_build_array(
        func.jsonb_build_object("derivation_id", establishment.c.derivation_id), type_=JSONB()
    )
    support_scopes = (
        func.ops.ddo_support_scopes(project, source, references)
        .table_valued(column("scope", Text()))
        .render_derived(name="witness_scope")
    )
    outside_locked_scope = (
        select(1)
        .select_from(support_scopes)
        .where(locked.has_key(support_scopes.c.scope).is_not(True))
        .correlate(establishment)
        .exists()
    )
    attestation_matches = (
        select(1)
        .select_from(
            establishment.join(
                conclusion,
                and_(
                    conclusion.c.rule_fingerprint == establishment.c.rule_fingerprint,
                    conclusion.c.premise == establishment.c.premise,
                ),
            ).join(
                outputs,
                and_(
                    establishment.c.derivation_id == outputs.c.derivation_id,
                    establishment.c.role == outputs.c.role,
                    establishment.c.position == outputs.c.position,
                ),
            )
        )
        .where(
            establishment.c.rule_fingerprint == selected.c.fingerprint,
            establishment.c.premise
            == _with_input_reads(
                model, selected.c.premise, selected.c.input_reads, establishment.c.derivation_id
            ),
            outputs.c.product_id == selected.c.product_id,
            outputs.c.member_id.is_(None),
            func.ops.ddo_read_visible(
                establishment.c.created_at, establishment.c.created_xid, boundary
            ),
            ~outside_locked_scope,
            func.ops.ddo_node_valid("episode", establishment.c.derivation_id, boundary),
        )
        .exists()
    )
    failure = (
        select(
            func.format(
                "required rule %s is not established for role %s at %s",
                selected.c.rule_id,
                selected.c.role_name,
                func.coalesce(selected.c.partition_key, "product"),
            )
        )
        .select_from(selected)
        .where(
            or_(
                and_(selected.c.checker == "admission", ~content_matches),
                and_(selected.c.checker == "producer", ~attestation_matches),
            )
        )
        .order_by(selected.c.role_name, selected.c.rule_id, selected.c.partition_key)
        .limit(1)
    )
    message = core_variable("failure", Text())
    return _routine(
        "ddo_require_bound_rules",
        (
            ("r", "ops", "data_request"),
            ("p_release", "text"),
            ("boundary", "ops", "data_demand_read"),
            ("locked", "jsonb"),
            ("roles", "jsonb"),
            ("manifest", "jsonb"),
        ),
        (
            SelectInto(failure, ("failure",)),
            _check(message.is_not(None), message, "23514"),
        ),
        (Local("failure", pg_type("text")),),
        stable=True,
    )


def rule_establishment_native_programs(model):
    """Register forward-only private programs against the rule-aware metadata."""
    if "sem.data_rule" not in model.tables:
        return ()
    return tuple(
        ProgramDeclaration(
            routine,
            source="data-operations:forward",
            owner=role_name("publisher"),
            access=INTERNAL_PROGRAM,
        )
        for routine in (_attestation_shape(), _settle_attestations(model), _bound_rules(model))
    )
