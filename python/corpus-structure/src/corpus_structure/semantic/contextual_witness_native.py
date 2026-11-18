"""Original current source/cue custody for private authored witness bindings."""

from sqlalchemy import Boolean, Column, Text, and_, any_, func, or_, select
from sqlalchemy.dialects.postgresql import ARRAY, array

from .contextual_admission_native import (
    _ContextualPrograms,
    _field,
    _items,
    _json,
    _object,
    _plain,
    _reject,
    _text,
    _value,
)
from .native_program import (
    Assign,
    Continue,
    ForQuery,
    If,
    Local,
    Raise,
    Return,
    SelectInto,
    Statement,
    column_type,
    core_relation_row,
)


def contextual_witness_native_sql(*, target_metadata=None) -> str:
    p = _ContextualPrograms(target_metadata)
    row, context, result = (_value(name) for name in ("row_meaning", "context_", "result"))
    p.add(
        "ddo_contextual_input_reference",
        (("row_meaning", "jsonb"), ("contribution", "boolean")),
        (
            Assign(
                "result",
                _object(
                    product_id=_text(row, "product_id"),
                    member_id=_plain(_field(row, "member_id")),
                    kind_contract=_text(row, "kind_contract"),
                    project_id=_text(context, "project_id"),
                    subject=_text(context, "subject"),
                    subject_definition=_text(context, "subject_definition"),
                    original_source=_plain(_field(context, "original_source")),
                    analyzed_scope_meaning=func.data.canonical_json(
                        _field(context, "analyzed_scope")
                    ),
                ),
            ),
            If(
                _value("contribution", Boolean()),
                (
                    Assign(
                        "result",
                        result.op("||")(
                            _object(contribution_id=_text(row, "body", "contribution_id"))
                        ),
                    ),
                ),
            ),
            Return(func.jsonb_strip_nulls(result)),
        ),
        (p.local("context_", initial=_field(row, "context")), p.local("result")),
        returns="jsonb",
        immutable=True,
        strict=True,
        definer=False,
    )
    episodes, requests, outputs, receipts, intents, admissions = (
        p.table(name)
        for name in (
            "ops.data_derivation",
            "ops.data_request",
            "ops.data_derivation_output",
            "ops.data_publication_receipt",
            "ops.data_completion_intent",
            "ops.original_source_admission",
        )
    )
    basis, current, query, inventory, source, hypotheses_row, cues = (
        _value(name)
        for name in (
            "basis",
            "row_",
            "query_row",
            "inventory_row",
            "source_row",
            "hypothesis_row",
            "cues",
        )
    )
    name, seen = _value("name_", Text()), _value("seen", ARRAY(Text()))
    query_value, hypotheses, inventory_value, query_basis, occurrence, original_source = (
        _value(name)
        for name in (
            "query_",
            "hypotheses",
            "inventory_",
            "query_basis",
            "original_occurrence",
            "original_source",
        )
    )
    cue, reference, assertion, carrier, actual_refs = (
        _value(name) for name in ("cue", "reference_", "assertion_", "carrier_", "actual_refs")
    )
    role_rows = _items(_field(basis, "roles")[1], "role_row")
    cue_rows = _items(cues, "cue_row")
    cue_support = _items(_plain(_field(cue, "support")), "cue_support")
    hypothesis_support = _items(_plain(_field(hypotheses_row, "support")), "hypothesis_support")
    anchors = _items(_plain(_field(cue, "body", "anchors")), "anchor")
    assertion_rows = _items(hypotheses["hypotheses"], "assertion_row")
    cited = _items(assertion["cue_refs"], "cited")
    targets = _items(inventory_value["targets"], "target")
    joined = (
        episodes.join(outputs, outputs.c.derivation_id == episodes.c.id)
        .join(requests, requests.c.id == episodes.c.request_id)
        .join(
            receipts,
            and_(
                receipts.c.derivation_id == episodes.c.id,
                receipts.c.intent_id == episodes.c.intent_id,
            ),
        )
    )

    def producer(target, selected, allowed, *, query_role=False):
        support = _items(_plain(_field(selected, "support")), "selected_support")
        conditions = [
            outputs.c.product_id == _text(selected, "product_id"),
            outputs.c.member_id.is_(None),
            requests.c.operation_id.in_(allowed),
            select(1)
            .select_from(support)
            .where(
                support.c.value["kind"].astext == "computation",
                support.c.value["derivation_id"].astext == episodes.c.id,
            )
            .exists(),
        ]
        if query_role:
            conditions.append(outputs.c.role == "query")
        return SelectInto(
            select(core_relation_row(episodes)).select_from(joined).where(*conditions),
            (target,),
            strict=True,
        )

    scalar_assignment: tuple[Statement, ...] = (Raise("case not found", "20000"),)
    for role, target in reversed(
        (
            ("source", "source_row"),
            ("query", "query_row"),
            ("inventory", "inventory_row"),
            ("hypotheses", "hypothesis_row"),
        )
    ):
        scalar_assignment = (If(name == role, (Assign(target, current),), scalar_assignment),)
    genuine_cue = (
        select(1)
        .select_from(
            episodes.join(
                receipts,
                and_(
                    receipts.c.derivation_id == episodes.c.id,
                    receipts.c.intent_id == episodes.c.intent_id,
                ),
            ).join(outputs, outputs.c.derivation_id == episodes.c.id)
        )
        .where(
            episodes.c.id == reference["derivation_id"].astext,
            episodes.c.outcome == "success",
            outputs.c.product_id == _text(cue, "product_id"),
            or_(outputs.c.member_id.is_(None), outputs.c.member_id == _text(cue, "member_id")),
        )
        .exists()
    )
    p.add(
        "ddo_contextual_witness_inputs",
        (("r", "ops.data_request"), ("completion", "jsonb")),
        (
            p.bind(),
            Assign("basis", func.ops.ddo_cpu_input_basis(p.row("original", "ops.data_request"))),
            ForQuery(
                ("row_",),
                select(role_rows.c.value),
                (
                    Assign("name_", _text(current, "role")),
                    _reject(
                        or_(
                            name.not_in(("source", "query", "inventory", "hypotheses", "cues")),
                            _field(current, "multiplicity").is_distinct_from(
                                _json(["integer", "1"])
                            ),
                        ),
                        "contextual witness input population is foreign or repeated",
                    ),
                    If(
                        name == "cues",
                        (
                            Assign("cues", cues.op("||")(func.jsonb_build_array(current))),
                            Continue(),
                        ),
                    ),
                    _reject(name == any_(seen), "contextual witness requires exact scalar inputs"),
                    Assign("seen", func.array_append(seen, name)),
                    *scalar_assignment,
                ),
            ),
            _reject(
                or_(
                    query.is_(None),
                    inventory.is_(None),
                    source.is_(None),
                    hypotheses_row.is_(None),
                    cues == _json([]),
                    *(
                        _field(value, "member_id").is_distinct_from(_json(["null"]))
                        for value in (query, inventory, hypotheses_row)
                    ),
                    _field(query, "context").is_distinct_from(_field(basis, "context")),
                    _field(inventory, "context").is_distinct_from(_field(basis, "context")),
                ),
                "contextual witness lacks its exact selected input context/population",
            ),
            Assign("query_", _plain(_field(query, "body"))),
            Assign("hypotheses", _plain(_field(hypotheses_row, "body"))),
            Assign(
                "inventory_",
                func.data.record_source_json(_plain(_field(inventory, "body"))["inventory"]),
            ),
            producer(
                "query_episode",
                query,
                (
                    "retrieve.contextual_query/declared",
                    "retrieve.contextual_query/selected-context",
                ),
                query_role=True,
            ),
            _reject(
                ~func.ops.ddo_contextual_dependencies_valid(
                    p.row("query_episode", "ops.data_derivation", "id")
                ),
                "contextual witness query lacks original native/CPU publication",
            ),
            producer("inventory_episode", inventory, ("retrieve.contextual_inventory/declared",)),
            _reject(
                ~func.ops.ddo_contextual_dependencies_valid(
                    p.row("inventory_episode", "ops.data_derivation", "id")
                ),
                "contextual witness inventory lacks its genuine native/CPU producer",
            ),
            p.lookup(
                "query_request",
                "ops.data_request",
                requests.c.id == p.row("query_episode", "ops.data_derivation", "request_id"),
            ),
            p.lookup(
                "query_intent",
                "ops.data_completion_intent",
                intents.c.id == p.row("query_episode", "ops.data_derivation", "intent_id"),
            ),
            *p.restore("query_request", "query_episode", "query_intent"),
            Assign(
                "query_basis",
                func.ops.ddo_cpu_input_basis(p.row("query_request", "ops.data_request")),
            ),
            p.role(query_basis, "occurrence", "original_occurrence"),
            p.role(query_basis, "source", "original_source"),
            Assign("carrier_", func.ops.ddo_contextual_input_reference(occurrence, True)),
            _reject(
                or_(
                    carrier.is_distinct_from(query_value["carrier"]),
                    func.ops.ddo_contextual_input_reference(source, False).is_distinct_from(
                        func.ops.ddo_contextual_input_reference(original_source, False)
                    ),
                    func.ops.ddo_rich_role_population(basis, "source").is_distinct_from(
                        func.ops.ddo_rich_role_population(query_basis, "source")
                    ),
                ),
                "contextual witness source/query carrier differs from original query custody",
            ),
            Assign("actual_refs", _json([])),
            ForQuery(
                ("cue",),
                select(cue_rows.c.value),
                (
                    _reject(
                        or_(
                            func.jsonb_array_length(_plain(_field(cue, "support"))) == 0,
                            _field(cue, "body", "pin").is_distinct_from(
                                _field(query, "body", "source_pin")
                            ),
                            _field(cue, "body", "occurrence_id").is_(None),
                            func.jsonb_array_length(
                                func.coalesce(_plain(_field(cue, "body", "anchors")), _json([]))
                            )
                            == 0,
                            select(1)
                            .select_from(anchors)
                            .where(
                                or_(
                                    anchors.c.value["precision"].astext.is_distinct_from("exact"),
                                    anchors.c.value["space"].astext.is_distinct_from("native"),
                                    anchors.c.value["pin"].is_distinct_from(
                                        query_value["source_pin"]
                                    ),
                                )
                            )
                            .exists(),
                            and_(
                                func.ops.ddo_contextual_input_reference(cue, True) == carrier,
                                func.ops.ddo_rich_support_population(
                                    _plain(_field(cue, "support"))
                                ).is_distinct_from(
                                    func.ops.ddo_rich_support_population(
                                        _plain(_field(occurrence, "support"))
                                    )
                                ),
                            ),
                        ),
                        "contextual witness cue differs from actual original parent/source/anchors",
                    ),
                    ForQuery(
                        ("reference_",),
                        select(cue_support.c.value),
                        (
                            _reject(
                                or_(
                                    reference["kind"].astext.is_distinct_from("computation"),
                                    ~genuine_cue,
                                ),
                                "contextual witness cue lacks its actual original producer/common receipt",
                            ),
                        ),
                    ),
                    Assign(
                        "actual_refs",
                        actual_refs.op("||")(
                            func.jsonb_build_array(
                                func.ops.ddo_contextual_input_reference(cue, True)
                            )
                        ),
                    ),
                ),
            ),
            _reject(
                ~actual_refs.contains(func.jsonb_build_array(carrier)),
                "contextual witness omits its exact qualifying query carrier",
            ),
            _reject(
                ~select(1)
                .select_from(hypothesis_support)
                .where(hypothesis_support.c.value["kind"].astext == "authored")
                .exists(),
                "contextual witness lacks admitted authored hypotheses",
            ),
            ForQuery(
                ("reference_",),
                select(hypothesis_support.c.value),
                (
                    p.lookup(
                        "admission",
                        "ops.original_source_admission",
                        admissions.c.id == reference["admission_id"].astext,
                        admissions.c.source_reference == reference["source_reference"].astext,
                        admissions.c.product_id == _text(hypotheses_row, "product_id"),
                    ),
                    _reject(
                        or_(
                            reference["kind"].astext.is_distinct_from("authored"),
                            p.row("admission", "ops.original_source_admission", "reference")[
                                "kind"
                            ].astext.is_distinct_from("authored-fact"),
                            p.row("admission", "ops.original_source_admission", "reference")[
                                "author"
                            ].astext.is_distinct_from(hypotheses["author_assertion"].astext),
                            func.data.ddo_normalize(
                                p.row("admission", "ops.original_source_admission", "reference")[
                                    "meaning_body"
                                ]
                            ).is_distinct_from(_field(hypotheses_row, "body")),
                        ),
                        "contextual witness author assertion differs from original authored admission",
                    ),
                ),
            ),
            ForQuery(
                ("assertion_",),
                select(assertion_rows.c.value),
                (
                    _reject(
                        or_(
                            ~assertion["cue_refs"].contains(func.jsonb_build_array(carrier)),
                            select(1)
                            .select_from(cited)
                            .where(~actual_refs.contains(func.jsonb_build_array(cited.c.value)))
                            .exists(),
                            ~select(1)
                            .select_from(targets)
                            .where(
                                targets.c.value["target_id"].astext.collate("C")
                                == assertion["target_id"].astext.collate("C")
                            )
                            .exists(),
                        ),
                        "contextual witness assertion differs from exact carrier/cues/selected target",
                    ),
                ),
            ),
        ),
        (
            p.local("original", "ops.data_request", p.row("r", "ops.data_request")),
            *(
                p.local(name)
                for name in (
                    "basis",
                    "row_",
                    "query_row",
                    "inventory_row",
                    "source_row",
                    "hypothesis_row",
                    "query_",
                    "hypotheses",
                    "inventory_",
                    "query_basis",
                    "original_occurrence",
                    "original_source",
                    "cue",
                    "reference_",
                    "assertion_",
                    "actual_refs",
                    "carrier_",
                )
            ),
            p.local("cues", initial=_json([])),
            *(
                p.local(name, "ops.data_derivation")
                for name in ("query_episode", "inventory_episode")
            ),
            p.local("query_request", "ops.data_request"),
            p.local("query_intent", "ops.data_completion_intent"),
            p.local("admission", "ops.original_source_admission"),
            Local("seen", column_type(Column("seen", ARRAY(Text()))), array([], type_=Text())),
            p.local("name_", "text"),
        ),
    )
    return p.script()
