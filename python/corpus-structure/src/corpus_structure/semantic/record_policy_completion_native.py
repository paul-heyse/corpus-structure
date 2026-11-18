"""Exact evaluator-policy completion from captured physical and public contracts.

Projection is an explicit correspondence to the public model. Native issuance
checks the actual selected producing episode and the common publication receipt.
"""

from __future__ import annotations

import json

from sqlalchemy import (
    BigInteger,
    Boolean,
    Integer,
    MetaData,
    Text,
    and_,
    case,
    cast,
    column,
    distinct,
    func,
    literal,
    or_,
    select,
    true,
    tuple_,
    union_all,
)
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.schema.integrity import role_name

from .data_operation_projections import (
    cut_selection_projection,
    record_grade_census_nodes,
    selected_support_output,
)
from .native_objects import NativeIdentity, native_privilege_sql, native_sql_script
from .native_program import (
    Assign,
    Block,
    CatchDependencyInvalidity,
    ForQuery,
    If,
    Local,
    Parameter,
    Perform,
    Raise,
    Return,
    ReturnNext,
    ReturnQuery,
    SelectInto,
    core_relation_row,
    core_variable,
    function,
    pg_type,
)
from .record_policy_authority import DdoRecordPolicyAuthorization
from .validity_programs import selected_family

_POLICY = "https://corpus-structure.dev/semantic/data-operation-record-policy/"


def _json(value):
    return cast(literal(json.dumps(value, separators=(",", ":"))), JSONB())


def _at(value, *path):
    for item in path:
        value = value[item]
    return value


def _text(value, *path):
    return _at(value, *path).astext


def _meaning(value, *path):
    for item in path:
        value = func.data.ddo_field(value, item, type_=JSONB())
    return value


def _object(**fields):
    return func.jsonb_build_object(
        *(part for key, value in fields.items() for part in (key, value)), type_=JSONB()
    )


def _items(value, name):
    return (
        func.jsonb_array_elements(value)
        .table_valued(column("value", JSONB()))
        .render_derived(name=name)
    )


def _reject(condition, message, state="23514"):
    return If(condition, (Raise(message, state),))


def _digest_text(value):
    return func.encode(func.sha256(func.convert_to(value, "UTF8")), "hex")


class _PolicyPrograms:
    def __init__(self, model: MetaData):
        self.model = model
        self.output: list[str] = []

    def table(self, name):
        return self.model.tables[name]

    def row(self, name, table, field=None):
        return core_variable(
            name, JSONB() if field is None else self.table(table).c[field].type, field
        )

    def local(self, name, table):
        return Local(name, self.table(table))

    def lookup(self, target, table, *conditions):
        relation = self.table(table)
        return SelectInto(
            select(core_relation_row(relation)).select_from(relation).where(*conditions),
            (target,),
            strict=True,
        )

    def add(
        self,
        name,
        parameters,
        statements,
        locals_=(),
        *,
        returns="void",
        setof=False,
        columns=(),
        immutable=False,
        strict=False,
        private=True,
        definer=True,
    ):
        result = pg_type(returns)
        result.setof = setof or bool(columns)
        self.output.append(
            function(
                "ops",
                name,
                parameters=tuple(
                    Parameter(key, pg_type(*kind.split("."))) for key, kind in parameters
                ),
                returns=result,
                table_columns=tuple((key, pg_type(kind)) for key, kind in columns),
                body=Block(tuple(statements), tuple(locals_)),
                volatility="immutable" if immutable else "stable",
                strict=strict,
                security_definer=definer,
                search_path=("pg_catalog", "pg_temp"),
            )
        )
        if private:
            self.output.append(
                native_privilege_sql(
                    NativeIdentity("function", "ops", name, tuple(kind for _, kind in parameters)),
                    "PUBLIC",
                    grant=False,
                )
            )

    def restored_request(self, target, producer, intent):
        request = self.row(target, "ops.data_request")

        def source(field):
            return self.row(producer, "ops.data_derivation", field)

        payload = self.row(intent, "ops.data_completion_intent", "payload")
        # Populate only the changed fields of the existing typed composite. This
        # preserves the server's composite placement and all remaining columns.
        return Assign(
            target,
            func.jsonb_populate_record(
                request,
                _object(
                    release_id=source("release_id"),
                    runtime_id=source("runtime_id"),
                    recipe=source("recipe"),
                    generation=source("generation"),
                    binding=self.row(target, "ops.data_request", "binding").op("||")(
                        _object(inputs=payload["inputs"], support=payload["support"])
                    ),
                ),
            ),
        )

    def fences(self, producer, intent):
        fields = ("producer_task_id", "producer_attempt", "runtime_id")
        return tuple_(
            *(self.row(intent, "ops.data_completion_intent", key) for key in fields)
        ).is_distinct_from(
            tuple_(*(self.row(producer, "ops.data_derivation", key) for key in fields))
        )


def record_policy_completion_native_sql(model: MetaData) -> str:
    programs = _PolicyPrograms(model)
    _authorization_projection(programs)
    _authorization_completion(programs)
    _fit_correspondence(programs)
    _fit_scopes(programs)
    _fit_selected_grade(programs)
    _fit_completion(programs)
    return native_sql_script(programs.output) + "\n"


def _authorization_projection(p):
    basis = core_variable("basis", JSONB())
    instance, feature, calibration = (
        core_variable(name, JSONB()) for name in ("instance", "feature", "calibration")
    )
    paths = {
        "algorithm": ("instance", "feature", "algorithm"),
        "parameters": ("instance", "feature", "parameters"),
        "family": ("instance", "feature", "applicability", "family"),
        "source_release_id": ("instance", "feature", "applicability", "release_id"),
        "subset": ("instance", "feature", "applicability", "subset"),
        "event_procedure": ("instance", "calibration", "event_procedure"),
        "threshold_procedure": ("instance", "threshold_procedure"),
        "threshold": ("instance", "threshold"),
        "calibration_slope": ("instance", "calibration", "slope"),
        "calibration_intercept": ("instance", "calibration", "intercept"),
        **{
            name: (name,)
            for name in (
                "family_contract",
                "reading_recipe",
                "numerical_policy",
                "judgment_basis_digest",
                "applicability",
            )
        },
    }
    derived = {
        "version": func.to_jsonb(cast(literal("record-policy-authorization-1"), Text())),
        **{
            name: func.to_jsonb(_digest_text(_text(basis, canonical)))
            for name, canonical in (
                ("policy_instance_digest", "instance_canonical_json"),
                ("feature_instance_digest", "feature_canonical_json"),
                ("calibration_digest", "calibration_canonical_json"),
            )
        },
    }
    projection = {**derived, **{name: _at(basis, *path) for name, path in paths.items()}}
    if projection.keys() != DdoRecordPolicyAuthorization.model_fields.keys():
        raise ValueError("native policy projection must cover the exact public contract")
    failures = [
        _text(basis, "version").is_distinct_from("fitted-record-policy-1"),
        *(
            func.jsonb_typeof(value).is_distinct_from("object")
            for value in (instance, feature, calibration)
        ),
        *(
            func.jsonb_typeof(basis[key]).is_distinct_from("string")
            for key in (
                "instance_canonical_json",
                "feature_canonical_json",
                "calibration_canonical_json",
            )
        ),
        *(
            cast(_text(basis, key), JSONB()).is_distinct_from(value)
            for key, value in (
                ("instance_canonical_json", instance),
                ("feature_canonical_json", feature),
                ("calibration_canonical_json", calibration),
            )
        ),
        _text(calibration, "feature_instance_digest").is_distinct_from(
            _digest_text(_text(basis, "feature_canonical_json"))
        ),
        _text(feature, "fit", "partition").is_distinct_from("feature_fit"),
        _text(feature, "fit", "standing").is_distinct_from("fitted"),
        _text(calibration, "fit", "partition").is_distinct_from("final_event_calibration"),
        _text(calibration, "fit", "standing").is_distinct_from("fitted"),
        *(
            _text(calibration, "fit", key).is_not_distinct_from(_text(feature, "fit", key))
            for key in ("frame_digest", "reference_digest")
        ),
    ]
    p.add(
        "ddo_policy_authorization_value",
        (("basis", "jsonb"),),
        (
            _reject(
                or_(*failures),
                "policy authorization differs from canonical fitted and held-out instance",
            ),
            Return(_object(**{key: projection[key] for key in sorted(projection)})),
        ),
        (
            Local("instance", pg_type("jsonb"), basis["instance"]),
            Local("feature", pg_type("jsonb"), instance["feature"]),
            Local("calibration", pg_type("jsonb"), instance["calibration"]),
        ),
        returns="jsonb",
        immutable=True,
        strict=True,
        private=False,
        definer=False,
    )
    projected = core_variable("projected", JSONB())
    meaning_fields = [
        func.jsonb_build_array(
            key,
            func.jsonb_build_array("string", _text(projected, key))
            if key in derived
            else _meaning(basis, *paths[key]),
        )
        for key in sorted(projection)
    ]
    p.add(
        "ddo_policy_authorization_meaning",
        (("basis", "jsonb"),),
        (
            Return(
                func.data.ddo_normalize(
                    func.jsonb_build_array("mapping", func.jsonb_build_array(*meaning_fields))
                )
            ),
        ),
        (
            Local(
                "projected",
                pg_type("jsonb"),
                func.ops.ddo_policy_authorization_value(func.data.ddo_json(basis)),
            ),
        ),
        returns="jsonb",
        immutable=True,
        strict=True,
        private=False,
        definer=False,
    )


def _authorization_completion(p):
    definitions, requests, products, kinds, producers, outputs, receipts, intents = (
        p.table(name)
        for name in (
            "sem.data_operation_definition",
            "ops.data_request",
            "kb.data_product",
            "sem.data_kind_contract",
            "ops.data_derivation",
            "ops.data_derivation_output",
            "ops.data_publication_receipt",
            "ops.data_completion_intent",
        )
    )

    def r(field=None):
        return p.row("r", "ops.data_request", field)

    def definition(field=None):
        return p.row("definition", "sem.data_operation_definition", field)

    def basis(field=None):
        return p.row("basis", "kb.data_product", field)

    def kind(field=None):
        return p.row("basis_kind", "sem.data_kind_contract", field)

    def producer(field=None):
        return p.row("producing", "ops.data_derivation", field)

    def fit_definition(field=None):
        return p.row("fit_definition", "sem.data_operation_definition", field)

    def fit_intent(field=None):
        return p.row("fit_intent", "ops.data_completion_intent", field)

    completion, selected, output, expected = (
        core_variable(name, JSONB()) for name in ("completion", "selected", "output", "expected")
    )
    effects = _items(definition("support_contract")["effects"], "effect")
    support = _items(completion["support"], "support")
    supported = (
        select(1)
        .select_from(support)
        .where(_text(support.c.value, "derivation_id") == producers.c.id)
        .exists()
    )
    selected_producer = (
        outputs.c.product_id == basis("id"),
        outputs.c.member_id.is_(None),
        outputs.c.role == "fitted",
        supported,
        func.ops.ddo_input_support_selection(selected).bool_op("?")(producers.c.id),
    )
    fit_contract = fit_definition("support_contract")
    fit_capabilities = fit_contract["capabilities"]["prepared_factory"]
    fit_payload = fit_intent("payload")
    expected_kind = (
        select(1)
        .select_from(kinds)
        .where(
            kinds.c.kind_contract == _text(output, "product", "kind_contract"),
            kinds.c.kind == _POLICY + "DdoRecordPolicyAuthorization",
            kinds.c.universe == "ordinary",
        )
        .exists()
    )
    p.add(
        "ddo_require_policy_authorization_completion",
        (("r", "ops.data_request"), ("completion", "jsonb")),
        (
            p.lookup(
                "definition",
                "sem.data_operation_definition",
                definitions.c.release_id == r("release_id"),
                definitions.c.operation_id == r("operation_id"),
            ),
            If(
                ~func.coalesce(definition("command_class") == "policy", False),
                (
                    _reject(
                        or_(
                            definition("operation_id") == "record_policy.authorize",
                            select(1)
                            .select_from(effects)
                            .where(
                                _text(effects.c.value, "name")
                                == "native-evaluator-policy-authorization"
                            )
                            .exists(),
                        ),
                        "policy authorization requires its exact admitted command/effect/factory",
                    ),
                    Return(),
                ),
            ),
            _reject(
                ~func.pg_has_role(
                    func.coalesce(
                        func.nullif(func.current_setting("role"), "none"), func.session_user()
                    ),
                    role_name("evaluator"),
                    "MEMBER",
                ),
                "policy authorization requires native evaluator purpose",
                "42501",
            ),
            _reject(
                or_(
                    _text(completion, "outcome").is_distinct_from("success"),
                    func.jsonb_array_length(completion["inputs"]) != 1,
                    func.jsonb_array_length(completion["outputs"]) != 1,
                ),
                "policy authorization requires one exact fitted basis and public conclusion",
            ),
            Assign("selected", completion["inputs"][0]),
            Assign("output", completion["outputs"][0]),
            _reject(
                or_(
                    _text(selected, "role").is_distinct_from("basis"),
                    _text(selected, "member_id").is_not(None),
                    cast(_text(selected, "position"), Integer()).is_distinct_from(0),
                    cast(_text(selected, "multiplicity"), Integer()).is_distinct_from(1),
                    _text(output, "role").is_distinct_from("authorization"),
                    _text(output, "member_id").is_not(None),
                    cast(_text(output, "position"), Integer()).is_distinct_from(0),
                    cast(_text(output, "multiplicity"), Integer()).is_distinct_from(1),
                    _at(output, "product", "members").is_distinct_from(_json([])),
                ),
                "policy authorization must consume and produce exact whole scalar products",
            ),
            p.lookup(
                "basis",
                "kb.data_product",
                products.c.id == _text(selected, "product_id"),
                products.c.project_id == r("project_id"),
            ),
            p.lookup(
                "basis_kind",
                "sem.data_kind_contract",
                kinds.c.kind_contract == basis("kind_contract"),
            ),
            _reject(
                or_(
                    kind("kind").is_distinct_from(_POLICY + "protected/DdoFittedRecordPolicy"),
                    kind("universe").is_distinct_from("evaluator"),
                ),
                "policy basis is not the protected fitted contract",
            ),
            _reject(
                select(func.count())
                .select_from(
                    producers.join(outputs, outputs.c.derivation_id == producers.c.id).join(
                        receipts,
                        and_(
                            receipts.c.derivation_id == producers.c.id,
                            receipts.c.intent_id == producers.c.intent_id,
                        ),
                    )
                )
                .where(
                    *selected_producer,
                    outputs.c.position == 0,
                    outputs.c.multiplicity == 1,
                    producers.c.outcome == "success",
                )
                .scalar_subquery()
                != 1,
                "policy basis lacks one exact supported successful native fit receipt",
            ),
            SelectInto(
                select(core_relation_row(producers))
                .select_from(producers.join(outputs, outputs.c.derivation_id == producers.c.id))
                .where(*selected_producer),
                ("producing",),
                strict=True,
            ),
            SelectInto(
                select(core_relation_row(definitions))
                .select_from(
                    definitions.join(
                        requests, requests.c.operation_id == definitions.c.operation_id
                    )
                )
                .where(
                    requests.c.id == producer("request_id"),
                    requests.c.project_id == r("project_id"),
                    definitions.c.release_id == producer("release_id"),
                ),
                ("fit_definition",),
                strict=True,
            ),
            p.lookup(
                "fit_intent",
                "ops.data_completion_intent",
                intents.c.id == producer("intent_id"),
                intents.c.request_id == producer("request_id"),
                intents.c.generation == producer("generation"),
            ),
            _reject(
                p.fences("producing", "fit_intent"),
                "policy fit basis differs from original producer fences",
            ),
            _reject(
                or_(
                    ~selected_family(
                        p.model,
                        fit_definition("release_id"),
                        fit_definition("operation_id"),
                        "record-fit",
                    ),
                    fit_definition("profile").is_distinct_from("derivation"),
                    fit_contract["effects"].is_distinct_from(_json([])),
                    func.nullif(_text(fit_capabilities, "entrypoint"), "").is_(None),
                    _text(fit_capabilities, "source_digest")
                    .bool_op("~")("^[0-9a-f]{64}$")
                    .is_not(True),
                    fit_definition("implementation_revision")
                    .like("implementation-slice:%")
                    .is_not(True),
                    _text(fit_payload, "implementation_revision").is_distinct_from(
                        fit_definition("implementation_revision")
                    ),
                    func.jsonb_array_length(
                        func.coalesce(
                            _at(fit_payload, "execution_evidence", "cpu_receipts"), _json([])
                        )
                    )
                    != 1,
                    producer("recipe").is_distinct_from(fit_definition("recipe")),
                ),
                "policy basis is not the actual admitted protected CPU fit implementation",
            ),
            p.lookup(
                "fit_request",
                "ops.data_request",
                requests.c.id == producer("request_id"),
                requests.c.project_id == r("project_id"),
            ),
            p.restored_request("fit_request", "producing", "fit_intent"),
            Perform(
                func.ops.ddo_require_record_fit_completion(
                    p.row("fit_request", "ops.data_request"), fit_payload
                )
            ),
            _reject(
                func.data.ddo_normalize(
                    _at(fit_payload, "outputs", 0, "product", "body")
                ).is_distinct_from(basis("canonical_body")),
                "policy basis differs from actual original fitted completion body",
            ),
            Assign(
                "expected",
                func.ops.ddo_policy_authorization_value(
                    func.data.ddo_json(basis("canonical_body"))
                ),
            ),
            _reject(
                or_(
                    _text(expected, "applicability", "project_id").is_distinct_from(
                        r("project_id")
                    ),
                    ~func.sem.ddo_model_class_contract(
                        r("release_id"), _text(expected, "family_contract")
                    ),
                    ~select(1)
                    .select_from(definitions)
                    .where(
                        definitions.c.release_id == r("release_id"),
                        definitions.c.operation_id == "resolve.m1_readings/declared",
                        definitions.c.recipe == _text(expected, "reading_recipe"),
                    )
                    .exists(),
                    ~expected_kind,
                    func.data.ddo_normalize(_at(output, "product", "body")).is_distinct_from(
                        func.ops.ddo_policy_authorization_meaning(basis("canonical_body"))
                    ),
                ),
                "policy authorization public conclusion differs from exact fitted basis and current interpretation",
            ),
        ),
        (
            p.local("definition", "sem.data_operation_definition"),
            Local("selected", pg_type("jsonb")),
            Local("output", pg_type("jsonb")),
            p.local("basis", "kb.data_product"),
            p.local("basis_kind", "sem.data_kind_contract"),
            p.local("producing", "ops.data_derivation"),
            p.local("fit_definition", "sem.data_operation_definition"),
            p.local("fit_intent", "ops.data_completion_intent"),
            p.local("fit_request", "ops.data_request"),
            Local("expected", pg_type("jsonb")),
        ),
        private=False,
    )


def _fit_correspondence(p):
    meanings = {
        key: core_variable(key + "_meaning", JSONB())
        for key in ("feature", "calibration", "specification", "basis")
    }
    (
        grade,
        calibration_grade,
        specification,
        basis,
        first,
        second,
        instance_meaning,
        instance,
        feature,
        calibration,
    ) = (
        core_variable(key, JSONB())
        for key in (
            "feature_grade",
            "calibration_grade",
            "specification",
            "basis",
            "first_",
            "second_",
            "instance_meaning",
            "instance",
            "feature",
            "calibration",
        )
    )
    feature_coverage, calibration_coverage, judgment_basis = (
        core_variable(key, Text())
        for key in ("feature_coverage", "calibration_coverage", "judgment_basis")
    )
    facts = {
        key: core_variable(key, BigInteger())
        for key in (
            "first_positive",
            "first_negative",
            "first_groups",
            "second_positive",
            "second_negative",
            "second_groups",
        )
    }
    wrong_final = core_variable("wrong_final", Boolean())

    def differences(pairs):
        return or_(*(left.is_distinct_from(right) for left, right in pairs))

    frozen = [
        (_meaning(instance_meaning, target), _meaning(meanings["specification"], source))
        for target, source in (
            ("feature", "frozen_feature"),
            ("threshold", "threshold"),
            ("threshold_procedure", "threshold_procedure"),
            ("conditioning_assumptions", "assumptions"),
        )
    ]
    frozen += [
        (_meaning(meanings["basis"], key), _meaning(meanings["specification"], key))
        for key in ("applicability", "family_contract", "reading_recipe")
    ]
    frozen.append((_text(basis, "judgment_basis_digest"), judgment_basis))
    inputs = [
        (_text(first, "partition"), "feature_fit"),
        (_text(second, "partition"), "final_event_calibration"),
        (_text(specification, "feature_selection", "frame_digest"), _text(grade, "frame_digest")),
        (
            _text(specification, "calibration_selection", "frame_digest"),
            _text(calibration_grade, "frame_digest"),
        ),
        *[
            (_text(first, key), _text(specification, "applicability", key))
            for key in ("project_id",)
        ],
        *[
            (_text(first, key), _text(specification, key))
            for key in ("family_contract", "reading_recipe")
        ],
        *[
            (_text(second, key), _text(first, key))
            for key in (
                "project_id",
                "family_contract",
                "reading_recipe",
                "family",
                "subset",
                "rubric_digest",
            )
        ],
    ]
    provenance = [
        *[
            (_text(feature, "fit", key), expected)
            for key, expected in (
                ("frame_digest", _text(grade, "frame_digest")),
                ("reference_digest", _text(first, "reference_digest")),
                ("coverage_digest", feature_coverage),
            )
        ],
        *[
            (_text(calibration, "fit", key), expected)
            for key, expected in (
                ("frame_digest", _text(calibration_grade, "frame_digest")),
                ("reference_digest", _text(second, "reference_digest")),
                ("coverage_digest", calibration_coverage),
            )
        ],
        *[
            (_text(part, "fit", "provenance"), "declared-selected-complete-record-grade-1")
            for part in (feature, calibration)
        ],
        *[
            (_text(part, "fit", "conditioning_assumptions"), _text(specification, "assumptions"))
            for part in (feature, calibration)
        ],
        *[
            (_text(feature, "applicability", key), expected)
            for key, expected in (
                ("release_id", _text(first, "prediction_release_id")),
                ("family", _text(first, "family")),
                ("subset", _text(first, "subset")),
                ("assumptions", _text(specification, "assumptions")),
            )
        ],
        (_text(calibration, "coverage_digest"), calibration_coverage),
        (_text(calibration, "event_procedure"), _text(specification, "event_procedure")),
        (_text(calibration, "assumptions"), _text(specification, "assumptions")),
        (
            _text(calibration, "feature_instance_digest"),
            _digest_text(_text(basis, "feature_canonical_json")),
        ),
    ]
    first_events, second_events = (
        _items(first["events"], "first_event"),
        _items(second["events"], "second_event"),
    )

    def populations(rows):
        return (
            func.count().filter(_text(rows.c.value, "correct") == "true"),
            func.count().filter(_text(rows.c.value, "correct") == "false"),
            func.count(distinct(_text(rows.c.value, "origin_group"))),
        )

    first_origins, second_origins = (
        _items(first["origin_groups"], "first_origin"),
        _items(second["origin_groups"], "second_origin"),
    )

    def source_ids(origins, name):
        copies = _items(origins.c.value["copied_from"], name + "_copy").lateral()
        return (
            select(_text(origins.c.value, "source", "original_source").label("id"))
            .select_from(origins)
            .union(
                select(_text(copies.c.value, "original_source")).select_from(
                    origins.join(copies, true())
                )
            )
            .cte(name)
        )

    first_sources, second_sources = (
        source_ids(first_origins, "first_sources"),
        source_ids(second_origins, "second_sources"),
    )
    diagnostics = [
        (cast(_text(part, "fit", key), BigInteger()), facts[fact])
        for part, key, fact in (
            (feature, "positive_count", "first_positive"),
            (feature, "negative_count", "first_negative"),
            (calibration, "positive_count", "second_positive"),
            (calibration, "negative_count", "second_negative"),
            (feature, "declared_origin_group_count", "first_groups"),
            (calibration, "declared_origin_group_count", "second_groups"),
        )
    ]
    p.add(
        "ddo_require_record_fit_correspondence",
        tuple((key + "_meaning", "jsonb") for key in meanings),
        (
            Assign("feature_coverage", func.ops.ddo_digest(first["coverage"])),
            Assign("calibration_coverage", func.ops.ddo_digest(second["coverage"])),
            Assign(
                "judgment_basis",
                func.ops.ddo_digest(
                    func.data.ddo_normalize(
                        func.jsonb_build_array(
                            "sequence",
                            func.jsonb_build_array(
                                func.jsonb_build_array("string", _text(grade, "frame_digest")),
                                func.jsonb_build_array(
                                    "string", _text(calibration_grade, "frame_digest")
                                ),
                                meanings["specification"],
                            ),
                        )
                    )
                ),
            ),
            _reject(
                differences(frozen),
                "fitted policy differs from actual frozen feature, typed specification or judgment basis",
            ),
            _reject(
                or_(
                    differences(inputs),
                    _text(grade, "frame_digest").is_not_distinct_from(
                        _text(calibration_grade, "frame_digest")
                    ),
                    _text(first, "reference_digest").is_not_distinct_from(
                        _text(second, "reference_digest")
                    ),
                    ~func.coalesce(
                        second["held_out_from"].bool_op("?")(_text(grade, "frame_digest")), False
                    ),
                ),
                "fit inputs differ from actual separate declared grade frames and interpretation",
            ),
            _reject(
                differences(provenance),
                "fitted feature/calibration provenance differs from actual input frames and procedure",
            ),
            SelectInto(
                select(*populations(first_events)).select_from(first_events),
                ("first_positive", "first_negative", "first_groups"),
            ),
            SelectInto(
                select(
                    *populations(second_events),
                    func.bool_or(
                        or_(
                            _text(
                                second_events.c.value, "final_event", "feature_instance_digest"
                            ).is_distinct_from(_text(calibration, "feature_instance_digest")),
                            _text(
                                second_events.c.value, "final_event", "event_procedure"
                            ).is_distinct_from(_text(specification, "event_procedure")),
                        )
                    ),
                ).select_from(second_events),
                ("second_positive", "second_negative", "second_groups", "wrong_final"),
            ),
            _reject(
                or_(differences(diagnostics), func.coalesce(wrong_final, False)),
                "fitted diagnostics or final events differ from complete actual grade populations",
            ),
            _reject(
                or_(
                    select(1)
                    .select_from(first_origins.join(second_origins, true()))
                    .where(
                        _text(first_origins.c.value, "origin_group")
                        == _text(second_origins.c.value, "origin_group")
                    )
                    .exists(),
                    select(1)
                    .select_from(
                        first_sources.join(
                            second_sources, first_sources.c.id == second_sources.c.id
                        )
                    )
                    .exists(),
                ),
                "fit and calibration share an original, known copied source or origin group",
            ),
        ),
        (
            *(
                Local(key + "_grade", pg_type("jsonb"), func.data.ddo_json(meanings[key]))
                for key in ("feature", "calibration")
            ),
            Local("specification", pg_type("jsonb"), func.data.ddo_json(meanings["specification"])),
            Local("basis", pg_type("jsonb"), func.data.ddo_json(meanings["basis"])),
            Local("first_", pg_type("jsonb"), grade["frame"]),
            Local("second_", pg_type("jsonb"), calibration_grade["frame"]),
            Local("instance_meaning", pg_type("jsonb"), _meaning(meanings["basis"], "instance")),
            Local("instance", pg_type("jsonb"), basis["instance"]),
            Local("feature", pg_type("jsonb"), instance["feature"]),
            Local("calibration", pg_type("jsonb"), instance["calibration"]),
            *(
                Local(key, pg_type("text"))
                for key in ("feature_coverage", "calibration_coverage", "judgment_basis")
            ),
            *(Local(key, pg_type("bigint")) for key in facts),
            Local("wrong_final", pg_type("bool")),
        ),
        immutable=True,
        strict=True,
        definer=False,
    )


def _fit_scopes(p):
    demands, reads, requests, producers, outputs, products, kinds, intents, read_scopes = (
        p.table(name)
        for name in (
            "ops.data_demand",
            "ops.data_demand_read",
            "ops.data_request",
            "ops.data_derivation",
            "ops.data_derivation_output",
            "kb.data_product",
            "sem.data_kind_contract",
            "ops.data_completion_intent",
            "ops.data_demand_read_scope",
        )
    )

    def d(field=None):
        return p.row("d", "ops.data_demand", field)

    def boundary(field=None):
        return p.row("boundary", "ops.data_demand_read", field)

    def r(field=None):
        return p.row("r", "ops.data_request", field)

    node_id, node_kind = core_variable("node", Text(), "id"), core_variable("node", Text(), "kind")
    operations = _items(d("selection")["operations"], "selected_operation")
    authorities = (
        select(1)
        .select_from(
            outputs.join(products, products.c.id == outputs.c.product_id).join(
                kinds, kinds.c.kind_contract == products.c.kind_contract
            )
        )
        .where(
            outputs.c.derivation_id == producers.c.id,
            kinds.c.kind.in_(
                (
                    _POLICY + "protected/DdoFittedRecordPolicy",
                    _POLICY + "DdoRecordPolicyAuthorization",
                )
            ),
        )
        .exists()
    )
    p.add(
        "ddo_record_fit_require_finite_cut",
        (("d", "ops.data_demand"), ("boundary", "ops.data_demand_read")),
        (
            _reject(
                select(1)
                .select_from(operations)
                .where(
                    _text(operations.c.value, "operation").in_(
                        ("record_policy.fit", "record_policy.authorize")
                    )
                )
                .exists(),
                "fit grade selection cannot select a fit or authorization census",
            ),
            ForQuery(
                ("node",),
                record_grade_census_nodes(p.model),
                (
                    _reject(
                        and_(
                            node_kind == "episode",
                            select(1)
                            .select_from(
                                producers.join(requests, requests.c.id == producers.c.request_id)
                            )
                            .where(
                                producers.c.id == node_id,
                                or_(
                                    requests.c.operation_id.in_(
                                        ("record_policy.fit", "record_policy.authorize")
                                    ),
                                    authorities,
                                ),
                            )
                            .exists(),
                        ),
                        "fit grade selection support reaches fitted policy authority",
                    ),
                ),
            ),
        ),
        (
            Local("p", pg_type("jsonb"), _object(scope=boundary("scope"))),
            Local("node", pg_type("record")),
        ),
    )

    specification = core_variable("specification", JSONB())
    selected, name = core_variable("selected", JSONB()), core_variable("name_", Text())
    selected_cut = cast(_text(selected, "cut_canonical_json"), JSONB())
    selections = union_all(
        select(literal("feature_grade"), specification["feature_selection"]),
        select(literal("calibration_grade"), specification["calibration_selection"]),
    )
    p.add(
        "ddo_record_fit_selections",
        (("r", "ops.data_request"),),
        (
            ForQuery(
                ("name_", "selected"),
                selections,
                (
                    _reject(
                        or_(
                            _text(selected, "project_id").is_distinct_from(r("project_id")),
                            _text(selected_cut, "project_id").is_distinct_from(r("project_id")),
                            _text(selected_cut, "demand_id").is_distinct_from(
                                _text(selected, "demand_id")
                            ),
                            _text(selected_cut, "read_id").is_distinct_from(
                                _text(selected, "read_id")
                            ),
                            _text(selected, "expected_cut").is_distinct_from(
                                literal("cut-selection:")
                                + _digest_text(_text(selected, "cut_canonical_json"))
                            ),
                        ),
                        "fit selection differs from its actual original project/cut/read pins",
                    ),
                    Assign("role_name", name),
                    Assign("selection", selected),
                    ReturnNext(),
                ),
            ),
        ),
        (
            Local(
                "specification",
                pg_type("jsonb"),
                func.ops.ddo_record_grade_input(r(), "specification", type_=JSONB())["body"],
            ),
            Local("selected", pg_type("jsonb")),
            Local("name_", pg_type("text")),
        ),
        returns="record",
        columns=(("role_name", "text"), ("selection", "jsonb")),
    )

    selection = core_variable("ddo_record_fit_cut_scopes", JSONB(), "selection")
    project = core_variable("ddo_record_fit_cut_scopes", Text(), "project")
    actual = core_variable("actual", JSONB())
    p.add(
        "ddo_record_fit_cut_scopes",
        (("project", "text"), ("selection", "jsonb")),
        (
            p.lookup(
                "d",
                "ops.data_demand",
                demands.c.id == _text(selection, "demand_id"),
                demands.c.project_id == project,
            ),
            p.lookup(
                "boundary",
                "ops.data_demand_read",
                reads.c.id == _text(selection, "read_id"),
                reads.c.demand_id == d("id"),
            ),
            Assign("p", _object(scope=boundary("scope"))),
            _reject(
                ~func.coalesce(func.ops.ddo_read_acquisition_present(boundary()), False),
                "fit grade cut requires read reacquisition",
            ),
            _reject(
                ~boundary("fit_census_eligible"),
                "fit grade selection support reaches fitted policy authority",
            ),
            SelectInto(cut_selection_projection(), ("actual",)),
            _reject(
                actual.is_distinct_from(cast(_text(selection, "cut_canonical_json"), JSONB())),
                "fit grade cut differs from exact native retained selection",
            ),
            ReturnQuery(
                select(read_scopes.c.scope)
                .where(read_scopes.c.read_id == boundary("id"), read_scopes.c.ordinary)
                .order_by(read_scopes.c.scope)
            ),
        ),
        (
            p.local("d", "ops.data_demand"),
            p.local("boundary", "ops.data_demand_read"),
            Local("p", pg_type("jsonb")),
            Local("actual", pg_type("jsonb")),
        ),
        returns="text",
        setof=True,
    )

    selected_record = core_variable("selected", JSONB(), "selection")
    rows = func.ops.ddo_record_fit_selections(r()).table_valued(column("selection", JSONB()))
    scopes = (
        func.ops.ddo_record_fit_cut_scopes(r("project_id"), selected_record)
        .table_valued(column("scope", Text()))
        .render_derived(name="scope_row")
    )
    p.add(
        "ddo_record_fit_completion_scopes",
        (("r", "ops.data_request"),),
        (
            If(
                ~selected_family(p.model, r("release_id"), r("operation_id"), "record-fit"),
                (Return(),),
            ),
            ForQuery(
                ("selected",),
                select(rows.c.selection).distinct(),
                (ReturnQuery(select(scopes.c.scope)),),
            ),
        ),
        (Local("selected", pg_type("record")),),
        returns="text",
        setof=True,
    )

    def producer(field=None):
        return p.row("producing", "ops.data_derivation", field)

    def intent(field=None):
        return p.row("intent", "ops.data_completion_intent", field)

    episode = core_variable("episode", Text())
    dependency_scopes = (
        func.ops.ddo_record_fit_completion_scopes(r())
        .table_valued(column("scope", Text()))
        .render_derived(name="dependency_scope")
    )
    p.add(
        "ddo_record_fit_dependency_scopes",
        (("episode", "text"),),
        (
            p.lookup("producing", "ops.data_derivation", producers.c.id == episode),
            p.lookup("r", "ops.data_request", requests.c.id == producer("request_id")),
            If(
                ~selected_family(p.model, r("release_id"), r("operation_id"), "record-fit"),
                (Return(),),
            ),
            p.lookup(
                "intent",
                "ops.data_completion_intent",
                intents.c.id == producer("intent_id"),
                intents.c.request_id == producer("request_id"),
                intents.c.generation == producer("generation"),
            ),
            _reject(
                p.fences("producing", "intent"),
                "fit dependency scopes differ from original producer fences",
            ),
            p.restored_request("r", "producing", "intent"),
            ReturnQuery(select(dependency_scopes.c.scope)),
        ),
        (
            p.local("r", "ops.data_request"),
            p.local("producing", "ops.data_derivation"),
            p.local("intent", "ops.data_completion_intent"),
        ),
        returns="text",
        setof=True,
    )


def _fit_selected_grade(p):
    (
        reads,
        demands,
        producers,
        definitions,
        requests,
        intents,
        receipts,
        outputs,
        products,
        kinds,
    ) = (
        p.table(name)
        for name in (
            "ops.data_demand_read",
            "ops.data_demand",
            "ops.data_derivation",
            "sem.data_operation_definition",
            "ops.data_request",
            "ops.data_completion_intent",
            "ops.data_publication_receipt",
            "ops.data_derivation_output",
            "kb.data_product",
            "sem.data_kind_contract",
        )
    )

    def r(field=None):
        return p.row("r", "ops.data_request", field)

    def boundary(field=None):
        return p.row("boundary", "ops.data_demand_read", field)

    def producer(field=None):
        return p.row("producer", "ops.data_derivation", field)

    def definition(field=None):
        return p.row("definition", "sem.data_operation_definition", field)

    def intent(field=None):
        return p.row("intent", "ops.data_completion_intent", field)

    selection, chosen, grade = (
        core_variable(key, JSONB()) for key in ("selection", "chosen", "grade")
    )
    role_name, product, derivation = (
        core_variable(key, Text()) for key in ("role_name", "p_product", "p_derivation")
    )
    admitted = core_variable("admitted", Boolean())
    inputs, support = (
        _items(r("binding")["inputs"], "item"),
        _items(r("binding")["support"], "support"),
    )
    authentic_product = (
        select(1)
        .select_from(
            receipts.join(outputs, outputs.c.derivation_id == receipts.c.derivation_id)
            .join(products, products.c.id == outputs.c.product_id)
            .join(kinds, kinds.c.kind_contract == products.c.kind_contract)
        )
        .where(
            receipts.c.derivation_id == producer("id"),
            receipts.c.intent_id == intent("id"),
            outputs.c.product_id == product,
            outputs.c.member_id.is_(None),
            outputs.c.role == "grade",
            outputs.c.position == 0,
            outputs.c.multiplicity == 1,
            kinds.c.kind == _POLICY + "protected/DdoRecordGrade",
            kinds.c.universe == "evaluator",
        )
        .exists()
    )
    payload = intent("payload")
    parsed_grade = func.data.ddo_json(grade, type_=JSONB())
    p.add(
        "ddo_record_fit_require_selection",
        (
            ("r", "ops.data_request"),
            ("role_name", "text"),
            ("selection", "jsonb"),
            ("authenticate_output", "bool"),
        ),
        (
            Perform(func.ops.ddo_record_fit_cut_scopes(r("project_id"), selection)),
            p.lookup(
                "boundary",
                "ops.data_demand_read",
                reads.c.id == _text(selection, "read_id"),
                reads.c.demand_id == _text(selection, "demand_id"),
            ),
            If(
                ~core_variable("authenticate_output", Boolean()),
                (
                    # Dependency validity authenticates exact retained custody above
                    # and needs only current ordinary epochs, never protected values.
                    Perform(func.ops.ddo_require_read_epochs(boundary(), r("project_id"), True)),
                    Return(literal(None)),
                ),
            ),
            Perform(func.ops.ddo_require_read_current(boundary(), r("project_id"), True)),
            p.lookup(
                "d",
                "ops.data_demand",
                demands.c.id == boundary("demand_id"),
                demands.c.project_id == r("project_id"),
            ),
            Assign("p", _object(scope=boundary("scope"))),
            SelectInto(selected_support_output(p.model), ("admitted",)),
            _reject(
                ~func.coalesce(admitted, False),
                "fit grade is outside exact current native selected support",
            ),
            SelectInto(
                select(inputs.c.value).where(
                    _text(inputs.c.value, "role") == role_name,
                    _text(inputs.c.value, "product_id") == product,
                    _text(inputs.c.value, "member_id").is_(None),
                    cast(_text(inputs.c.value, "multiplicity"), Integer()) == 1,
                ),
                ("chosen",),
                strict=True,
            ),
            _reject(
                or_(
                    ~select(1)
                    .select_from(support)
                    .where(
                        _text(support.c.value, "derivation_id") == derivation,
                        _text(support.c.value, "role") == role_name,
                    )
                    .exists(),
                    ~func.ops.ddo_input_support_selection(chosen).bool_op("?")(derivation),
                ),
                "fit grade selection differs from actual bound input product and producing episode",
            ),
            p.lookup(
                "producer",
                "ops.data_derivation",
                producers.c.id == derivation,
                producers.c.outcome == "success",
            ),
            SelectInto(
                select(core_relation_row(definitions))
                .select_from(
                    definitions.join(
                        requests, requests.c.operation_id == definitions.c.operation_id
                    )
                )
                .where(
                    requests.c.id == producer("request_id"),
                    requests.c.project_id == r("project_id"),
                    definitions.c.release_id == producer("release_id"),
                ),
                ("definition",),
                strict=True,
            ),
            p.lookup(
                "intent",
                "ops.data_completion_intent",
                intents.c.id == producer("intent_id"),
                intents.c.request_id == producer("request_id"),
                intents.c.generation == producer("generation"),
            ),
            _reject(
                p.fences("producer", "intent"), "fit grade differs from original producer fences"
            ),
            _reject(
                or_(
                    ~selected_family(
                        p.model,
                        definition("release_id"),
                        definition("operation_id"),
                        "record-grade",
                    ),
                    definition("profile").is_distinct_from("derivation"),
                    definition("support_contract")["effects"].is_distinct_from(_json([])),
                    func.nullif(
                        _text(
                            definition("support_contract"),
                            "capabilities",
                            "prepared_factory",
                            "entrypoint",
                        ),
                        "",
                    ).is_(None),
                    _text(payload, "implementation_revision").is_distinct_from(
                        definition("implementation_revision")
                    ),
                    producer("recipe").is_distinct_from(definition("recipe")),
                    func.jsonb_array_length(
                        func.coalesce(_at(payload, "execution_evidence", "cpu_receipts"), _json([]))
                    )
                    != 1,
                    ~authentic_product,
                ),
                "fit grade lacks actual protected grade CPU/common producer custody",
            ),
            SelectInto(
                select(products.c.canonical_body).where(
                    products.c.id == product, products.c.project_id == r("project_id")
                ),
                ("grade",),
                strict=True,
            ),
            _reject(
                or_(
                    _text(parsed_grade, "frame_digest").is_distinct_from(
                        _text(selection, "frame_digest")
                    ),
                    _text(parsed_grade, "frame", "partition").is_distinct_from(
                        cast(
                            case(
                                (role_name == "feature_grade", "feature_fit"),
                                else_="final_event_calibration",
                            ),
                            Text(),
                        )
                    ),
                ),
                "fit grade frame or partition differs from its actual selected input",
            ),
            Return(grade),
        ),
        (
            p.local("d", "ops.data_demand"),
            p.local("boundary", "ops.data_demand_read"),
            Local("p", pg_type("jsonb")),
            Local("p_use", pg_type("text"), _text(selection, "use_id")),
            Local("p_product", pg_type("text"), _text(selection, "product_id")),
            Local("p_derivation", pg_type("text"), _text(selection, "derivation_id")),
            Local("admitted", pg_type("bool")),
            Local("chosen", pg_type("jsonb")),
            Local("grade", pg_type("jsonb")),
            p.local("producer", "ops.data_derivation"),
            p.local("definition", "sem.data_operation_definition"),
            p.local("intent", "ops.data_completion_intent"),
        ),
        returns="jsonb",
    )


def _fit_completion(p):
    definitions, products, kinds, producers, requests, intents = (
        p.table(name)
        for name in (
            "sem.data_operation_definition",
            "kb.data_product",
            "sem.data_kind_contract",
            "ops.data_derivation",
            "ops.data_request",
            "ops.data_completion_intent",
        )
    )

    def r(field=None):
        return p.row("r", "ops.data_request", field)

    def definition(field=None):
        return p.row("definition", "sem.data_operation_definition", field)

    completion, output, feature, calibration, specification, cpu_output = (
        core_variable(name, JSONB())
        for name in (
            "completion",
            "output",
            "feature",
            "calibration",
            "specification",
            "cpu_output",
        )
    )
    capability = definition("support_contract")["capabilities"]["prepared_factory"]
    exact_kind = (
        select(1)
        .select_from(kinds)
        .where(
            kinds.c.kind_contract == _text(output, "product", "kind_contract"),
            kinds.c.kind == _POLICY + "protected/DdoFittedRecordPolicy",
            kinds.c.universe == "evaluator",
        )
        .exists()
    )
    not_fit = ~selected_family(p.model, r("release_id"), r("operation_id"), "record-fit")
    p.add(
        "ddo_record_fit_require_producer",
        (("r", "ops.data_request"), ("completion", "jsonb")),
        (
            If(not_fit, (Return(),)),
            p.lookup(
                "definition",
                "sem.data_operation_definition",
                definitions.c.release_id == r("release_id"),
                definitions.c.operation_id == r("operation_id"),
            ),
            _reject(
                or_(
                    definition("profile").is_distinct_from("derivation"),
                    definition("support_contract")["effects"].is_distinct_from(_json([])),
                    func.nullif(_text(capability, "entrypoint"), "").is_(None),
                    _text(capability, "source_digest").bool_op("~")("^[0-9a-f]{64}$").is_not(True),
                    definition("implementation_revision")
                    .like("implementation-slice:%")
                    .is_not(True),
                    _text(completion, "implementation_revision").is_distinct_from(
                        definition("implementation_revision")
                    ),
                    r("recipe").is_distinct_from(definition("recipe")),
                    completion["inputs"].is_distinct_from(r("binding")["inputs"]),
                    completion["support"].is_distinct_from(r("binding")["support"]),
                    func.jsonb_array_length(
                        func.coalesce(
                            _at(completion, "execution_evidence", "cpu_receipts"), _json([])
                        )
                    )
                    != 1,
                ),
                "fit completion requires actual protected fit factory/CPU and exact declared inputs",
            ),
            If(
                and_(_text(completion, "outcome") == "empty", completion["outputs"] == _json([])),
                (Return(),),
            ),
            _reject(
                or_(
                    _text(completion, "outcome").is_distinct_from("success"),
                    func.jsonb_array_length(completion["outputs"]) != 1,
                ),
                "fit completion requires one fitted scalar or a non-authoritative empty result",
            ),
            Assign("output", completion["outputs"][0]),
            _reject(
                or_(
                    _text(output, "role").is_distinct_from("fitted"),
                    _text(output, "member_id").is_not(None),
                    cast(_text(output, "position"), Integer()).is_distinct_from(0),
                    cast(_text(output, "multiplicity"), Integer()).is_distinct_from(1),
                    _at(output, "product", "members").is_distinct_from(_json([])),
                    ~exact_kind,
                ),
                "fit output differs from exact protected fitted scalar contract",
            ),
        ),
        (p.local("definition", "sem.data_operation_definition"), Local("output", pg_type("jsonb"))),
    )

    selections = func.ops.ddo_record_fit_selections(r()).table_valued(
        column("role_name", Text()), column("selection", JSONB())
    )
    chosen = _items(r("binding")["inputs"], "chosen")
    selected_role, selected_value = (
        core_variable("selected", Text(), "role_name"),
        core_variable("selected", JSONB(), "selection"),
    )
    p.add(
        "ddo_require_record_fit_completion",
        (("r", "ops.data_request"), ("completion", "jsonb")),
        (
            If(not_fit, (Return(),)),
            Perform(func.ops.ddo_record_fit_require_producer(r(), completion)),
            Assign(
                "cpu_output", _meaning(func.ops.ddo_cpu_reply_output(r(), completion), "fitted")
            ),
            ForQuery(
                ("selected",),
                select(selections),
                (
                    If(
                        selected_role == "feature_grade",
                        (
                            Assign(
                                "feature",
                                func.ops.ddo_record_fit_require_selection(
                                    r(), selected_role, selected_value, True
                                ),
                            ),
                        ),
                        (
                            Assign(
                                "calibration",
                                func.ops.ddo_record_fit_require_selection(
                                    r(), selected_role, selected_value, True
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            If(
                _text(completion, "outcome") == "empty",
                (
                    _reject(
                        cpu_output.is_distinct_from(_json(["null"])),
                        "empty fit differs from its actual CPU result",
                    ),
                    Return(),
                ),
            ),
            Assign("output", completion["outputs"][0]),
            _reject(
                cpu_output.is_distinct_from(
                    func.data.ddo_normalize(_at(output, "product", "body"))
                ),
                "fitted policy differs from its actual CPU result",
            ),
            SelectInto(
                select(products.c.canonical_body)
                .select_from(
                    chosen.join(
                        products,
                        and_(
                            products.c.id == _text(chosen.c.value, "product_id"),
                            products.c.project_id == r("project_id"),
                        ),
                    )
                )
                .where(
                    _text(chosen.c.value, "role") == "specification",
                    _text(chosen.c.value, "member_id").is_(None),
                    cast(_text(chosen.c.value, "multiplicity"), Integer()) == 1,
                ),
                ("specification",),
                strict=True,
            ),
            Perform(
                func.ops.ddo_require_record_fit_correspondence(
                    feature,
                    calibration,
                    specification,
                    func.data.ddo_normalize(_at(output, "product", "body")),
                )
            ),
            Perform(
                func.ops.ddo_policy_authorization_value(
                    func.data.ddo_json(_at(output, "product", "body"))
                )
            ),
        ),
        (
            Local("selected", pg_type("record")),
            *(
                Local(name, pg_type("jsonb"))
                for name in ("feature", "calibration", "output", "specification", "cpu_output")
            ),
        ),
    )

    def producer(field=None):
        return p.row("producing", "ops.data_derivation", field)

    def intent(field=None):
        return p.row("intent", "ops.data_completion_intent", field)

    episode = core_variable("episode", Text())
    p.add(
        "ddo_record_fit_dependencies_valid",
        (("episode", "text"),),
        (
            CatchDependencyInvalidity(
                (
                    p.lookup("producing", "ops.data_derivation", producers.c.id == episode),
                    p.lookup("r", "ops.data_request", requests.c.id == producer("request_id")),
                    If(not_fit, (Return(literal(True)),)),
                    p.lookup(
                        "intent",
                        "ops.data_completion_intent",
                        intents.c.id == producer("intent_id"),
                        intents.c.request_id == producer("request_id"),
                        intents.c.generation == producer("generation"),
                    ),
                    Assign("r", func.ops.ddo_require_episode_correspondence(producer(), intent())),
                    ForQuery(
                        ("selected",),
                        select(selections),
                        (
                            Perform(
                                func.ops.ddo_record_fit_require_selection(
                                    r(), selected_role, selected_value, False
                                )
                            ),
                        ),
                    ),
                    Return(literal(True)),
                ),
                (Return(literal(False)),),
            ),
        ),
        (
            p.local("r", "ops.data_request"),
            Local("selected", pg_type("record")),
            p.local("producing", "ops.data_derivation"),
            p.local("intent", "ops.data_completion_intent"),
        ),
        returns="bool",
    )
