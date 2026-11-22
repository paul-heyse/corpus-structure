"""Settlement and binding use exact producer proof targets under the acquired cut."""

from dataclasses import replace
from datetime import UTC, datetime
from typing import cast

import pytest
from sqlalchemy import bindparam, insert, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DBAPIError
from sqlalchemy.schema import CreateTable

from corpus_structure.semantic._data_operation_wire import WireOutputMember
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import (
    DataRuleRead,
    EffectiveDataRule,
    EffectiveKind,
    SubjectContext,
)
from corpus_structure.semantic.data_operation_partitions import partition_header, partition_packet
from corpus_structure.semantic.data_operation_values import decode_semantic_value, semantic_value
from corpus_structure.semantic.data_read_boundary_native import read_boundary_native_programs
from corpus_structure.semantic.established_validity import (
    RuleObservedInput,
    successful_rule_attestation,
)
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import execute_native_sql
from corpus_structure.semantic.rule_establishment_native import rule_establishment_native_programs
from semantic.test_data_product_admission_programs import (
    partition_fixture,
    product_connection,  # noqa: F401
    realize,
)


def test_inline_rule_projections_reuse_only_their_observed_row_facts(
    product_connection,  # noqa: F811
):
    context, packet, _, _ = partition_fixture(product_connection)
    body = decode_semantic_value(packet["body"])
    rules = (
        (
            "unique-coverage",
            "unique",
            "coverage",
            {"paths": ["family"]},
            ("family",),
        ),
        (
            "ordered-region",
            "predicate",
            "lexicon",
            {"expression": {"op": "le", "args": [{"field": "start"}, {"field": "end"}]}},
            ("start", "end"),
        ),
    )
    table = get_metadata().tables["sem.data_rule"]
    for rule_id, form, collection, parameters, paths in rules:
        spec = {
            "id": rule_id,
            "scope": "product",
            "collection": collection,
            "checker": "admission",
            "fingerprint": rule_id,
            "form": form,
            "parameters": {**parameters, "inline_collection": True},
            "reads": [{"side": "source", "path": path, "groups": []} for path in paths],
        }
        product_connection.execute(
            insert(table).values(
                release_id="release",
                rule_id=rule_id,
                kind_contract="partitioned",
                fingerprint=rule_id,
                specification=spec,
            )
        )
    coverage = [{"family": "math", "outcome": "complete"}, {"family": "chem", "outcome": "empty"}]
    lexicon = [{"start": 2, "end": 5}]

    def publish(coverage, lexicon):
        return realize(
            product_connection,
            context,
            {**packet, "body": semantic_value({**body, "coverage": coverage, "lexicon": lexicon})},
        )

    original = publish(coverage, lexicon)
    counts = text("SELECT count(*) FROM kb.data_validity")
    assert product_connection.scalar(counts) == 2
    edited = publish([coverage[1], {**coverage[0], "outcome": "partial"}], lexicon)
    assert original != edited
    assert product_connection.scalar(counts) == 2
    with (
        pytest.raises(DBAPIError, match="unique-coverage violated"),
        product_connection.begin_nested(),
    ):
        publish([coverage[0], coverage[0]], lexicon)
    with (
        pytest.raises(DBAPIError, match="ordered-region violated"),
        product_connection.begin_nested(),
    ):
        publish(coverage, [{"start": 5, "end": 2}])


def test_producer_attestations_require_exact_target_and_live_establishment(
    product_connection,  # noqa: F811
):
    conn = product_connection
    model = get_metadata()
    for name in (
        "ops.data_request",
        "ops.data_derivation_output",
        "ops.data_derivation_input",
        "ops.data_demand_read",
        "kb.data_validity_establishment",
    ):
        conn.execute(CreateTable(model.tables[name], include_foreign_key_constraints=[]))
    # The isolation fixture supplies the support owner's decisions explicitly.
    # The actual partition premise, cutoff, settlement and binding routines run unchanged.
    conn.exec_driver_sql(
        "CREATE FUNCTION ops.ddo_apply_bound_product_rules(text,text,text,text) RETURNS void"
        " LANGUAGE sql AS 'SELECT'"
    )
    conn.exec_driver_sql(
        "CREATE FUNCTION ops.ddo_support_scopes(text,text,jsonb) RETURNS TABLE (scope text)"
        " LANGUAGE sql AS $$ SELECT 'selected-scope'::text $$"
    )
    conn.exec_driver_sql("CREATE TEMP TABLE refused_episode (id text PRIMARY KEY)")
    conn.exec_driver_sql(
        "CREATE FUNCTION ops.ddo_node_valid(text,text,ops.data_demand_read) RETURNS bool"
        " LANGUAGE sql AS $$ SELECT NOT EXISTS (SELECT 1 FROM pg_temp.refused_episode WHERE id=$2) $$"
    )
    visibility = next(
        program
        for program in read_boundary_native_programs(model)
        if program.name == "ddo_read_visible"
    )
    execute_native_sql(conn, visibility.render())
    for declaration in rule_establishment_native_programs(model):
        execute_native_sql(conn, declaration.routine.render())
    context, packet, bodies, declaration = partition_fixture(conn)
    packet["partitions"] = [
        partition_packet("tokens", part, n, n * 10, n * 10 + 5, [{**body[0], "label": part}])
        for n, (part, body) in enumerate(zip(("b", "a", "é"), bodies, strict=True))
    ]
    packet["body"] = semantic_value({"tokens": partition_header(packet["partitions"])})
    product = realize(conn, context, packet)
    output = model.tables["ops.data_derivation_output"]
    conn.execute(
        insert(output),
        [
            {
                "derivation_id": episode,
                "role": "result",
                "position": 0,
                "multiplicity": 1,
                "product_id": product,
            }
            for episode in ("first", "second")
        ],
    )
    premise_sql = text(
        "SELECT ops.ddo_rule_premise(:rule,:product,:partition,NULL,NULL)"
    ).bindparams(bindparam("rule", type_=JSONB()))
    kind = EffectiveKind(
        "urn:partitioned",
        "partitioned",
        "class",
        json_bytes({"collections": {"tokens": declaration}}),
    )
    subject = SubjectContext(
        context["project_id"],
        context["subject"],
        context["original_source"],
        json_bytes(context["analyzed_scope"]),
        subject_definition=context["subject_definition"],
    )
    result = cast(
        WireOutputMember, {"role": "result", "position": 0, "multiplicity": 1, "product": packet}
    )
    partitions = {item["partition_key"]: item for item in result["product"]["partitions"]}
    rule = EffectiveDataRule(
        id="check",
        fingerprint="fingerprint",
        kind=kind.semantic_id,
        kind_contract="partitioned",
        collection="tokens",
        scope="partition",
        form="attested",
        parameters=b"{}",
        reads=(DataRuleRead("source", "optional", ()),),
        checker="producer",
        checker_operation="actual-producer",
        checker_callable="fixture:checker",
        checker_determinant="captured-checker",
    )
    body_rule = replace(
        rule,
        id="body",
        fingerprint="body-fingerprint",
        scope="product",
        collection=None,
        reads=(DataRuleRead("source", "$all", ()),),
    )
    for checker in (rule, body_rule):
        conn.execute(
            insert(model.tables["sem.data_rule"]).values(
                release_id="release",
                rule_id=checker.id,
                kind_contract=checker.kind_contract,
                fingerprint=checker.fingerprint,
                specification=checker.record,
            )
        )

    def claim(checker: EffectiveDataRule, part: str | None = None):
        assertion = successful_rule_attestation(
            checker,
            kind,
            "actual-producer",
            result,
            subject,
            partition=partitions[part] if part is not None else None,
        )
        assert (
            assertion.premise
            == conn.execute(
                premise_sql, dict(rule=checker.record, product=product, partition=part)
            ).scalar_one()
        )
        return assertion.model_dump(mode="json")

    entries = [claim(rule, part) for part in ("b", "a", "é")]
    assert entries[0]["premise"] == entries[2]["premise"]
    assert entries[0]["premise"] != entries[1]["premise"]
    grouped = replace(
        rule,
        reads=(
            DataRuleRead("source", "label", ("labels",)),
            DataRuleRead("source", "optional", ("labels",)),
        ),
    )
    claim(grouped, "a")
    entries.append(claim(body_rule))
    producer = {"release_id": "release", "operation_id": "actual-producer"}
    settle = text(
        "SELECT ops.ddo_settle_rule_attestations("
        "jsonb_populate_record(NULL::ops.data_request,:request),:completion,:episode)"
    ).bindparams(bindparam("request", type_=JSONB()), bindparam("completion", type_=JSONB()))

    def run_settle(assertions, episode, request=producer):
        conn.execute(
            settle,
            dict(
                request=request,
                episode=episode,
                completion={"execution_evidence": {"rule_attestations": assertions}},
            ),
        )

    check_shape = text("SELECT ops.ddo_require_rule_assertion_shape(:completion)").bindparams(
        bindparam("completion", type_=JSONB())
    )
    conn.execute(
        check_shape, {"completion": {"execution_evidence": {"rule_attestations": entries}}}
    )
    with pytest.raises(DBAPIError, match="invalid rule attestation"), conn.begin_nested():
        conn.execute(
            check_shape,
            {
                "completion": {
                    "execution_evidence": {
                        "rule_attestations": [{**entries[0], "output_position": True}]
                    }
                }
            },
        )
    for wrong in (
        [],
        entries[:-1],
        [entries[0], *entries],
        [{**entries[0], "premise": "forged"}, *entries[1:]],
    ):
        with pytest.raises(DBAPIError, match="rule attestation"), conn.begin_nested():
            run_settle(wrong, "first")
    with pytest.raises(DBAPIError, match="undeclared rule attestation"), conn.begin_nested():
        run_settle(entries, "first", {**producer, "operation_id": "adopter"})
    assert conn.execute(text("SELECT count(*) FROM kb.data_validity")).scalar_one() == 0
    run_settle(entries, "first")
    run_settle(entries, "first")
    run_settle(entries, "second")
    assert conn.execute(text("SELECT count(*) FROM kb.data_validity")).scalar_one() == 3
    assert (
        conn.execute(text("SELECT count(*) FROM kb.data_validity_establishment")).scalar_one() == 6
    )

    at, xid, snapshot = conn.execute(
        text("SELECT clock_timestamp(),pg_current_xact_id()::text,pg_current_snapshot()::text")
    ).one()
    bind = text(
        "SELECT ops.ddo_require_bound_rules("
        "jsonb_populate_record(NULL::ops.data_request,:request),:release,"
        "jsonb_populate_record(NULL::ops.data_demand_read,:boundary),:locked,:roles,:manifest)"
    ).bindparams(
        *(
            bindparam(key, type_=JSONB())
            for key in ("request", "boundary", "locked", "roles", "manifest")
        )
    )
    boundary = {"frontier_at": at.isoformat(), "owner_xid": xid, "read_snapshot": snapshot}

    def run_bind(
        *, acquired=boundary, locked=True, required="check", targets=(), release="release"
    ):
        conn.execute(
            bind,
            dict(
                request={"release_id": "release", "project_id": context["project_id"]},
                release=release,
                boundary=acquired,
                locked={"selected-scope": 0} if locked else {},
                roles=[{"name": "input", "required_rules": [required]}],
                manifest=[{"role": "input", "product_id": product}, *targets],
            ),
        )

    run_bind()
    run_bind(required="body")
    source_rule = replace(
        body_rule,
        id="source-dependent",
        fingerprint="source-dependent-fingerprint",
        parameters=b'{"input_reads":{"source":["tokens.placement_root","tokens.root"]}}',
    )
    conn.execute(
        insert(model.tables["sem.data_rule"]),
        [
            dict(
                release_id="source-release",
                rule_id=checker.id,
                kind_contract=checker.kind_contract,
                fingerprint=checker.fingerprint,
                specification=checker.record,
            )
            for checker in (body_rule, source_rule)
        ],
    )
    conn.execute(
        insert(model.tables["ops.data_derivation_input"]).values(
            derivation_id="second",
            role="source",
            position=0,
            multiplicity=1,
            product_id=product,
        )
    )

    def source_claim(value):
        return successful_rule_attestation(
            source_rule,
            kind,
            "actual-producer",
            result,
            subject,
            selected_inputs={"source": (RuleObservedInput(value),)},
        ).model_dump(mode="json")

    source_request = {**producer, "release_id": "source-release"}
    run_bind(required="body", release="source-release")
    with pytest.raises(DBAPIError, match="rule"), conn.begin_nested():
        run_bind(required="source-dependent", release="source-release")
    actual_source = decode_semantic_value(result["product"]["body"])
    declared_claim = source_claim(actual_source)
    assert source_claim({**actual_source, "unobserved": "different"}) == declared_claim
    tokens = actual_source["tokens"]
    assert source_claim({**actual_source, "tokens": {**tokens, "item_count": 800}}) == declared_claim
    for field in ("placement_root", "root"):
        changed = source_claim({**actual_source, "tokens": {**tokens, field: "wrong"}})
        assert changed != declared_claim
        with pytest.raises(DBAPIError, match="missing or conflicting"), conn.begin_nested():
            run_settle([claim(body_rule), changed], "second", source_request)
    run_settle([claim(body_rule), declared_claim], "second", source_request)
    observed_at = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
    run_bind(
        required="source-dependent",
        release="source-release",
        acquired={**boundary, "frontier_at": observed_at.isoformat()},
    )
    next_rule = replace(rule, fingerprint="revised-fingerprint")
    conn.execute(
        insert(model.tables["sem.data_rule"]).values(
            release_id="revised-release",
            rule_id=next_rule.id,
            kind_contract=next_rule.kind_contract,
            fingerprint=next_rule.fingerprint,
            specification=next_rule.record,
        )
    )
    with pytest.raises(DBAPIError, match="required rule check"), conn.begin_nested():
        run_bind(release="revised-release")
    run_settle(
        [claim(next_rule, part) for part in ("a", "b", "é")],
        "second",
        {**producer, "release_id": "revised-release"},
    )
    refreshed_at = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
    run_bind(
        release="revised-release", acquired={**boundary, "frontier_at": refreshed_at.isoformat()}
    )
    with pytest.raises(DBAPIError, match="required rule check"), conn.begin_nested():
        run_bind(locked=False)
    with pytest.raises(DBAPIError, match="required rule check"), conn.begin_nested():
        run_bind(acquired={**boundary, "frontier_at": datetime(2000, 1, 1, tzinfo=UTC).isoformat()})
    conn.exec_driver_sql("INSERT INTO pg_temp.refused_episode VALUES ('first')")
    run_bind()
    conn.exec_driver_sql("INSERT INTO pg_temp.refused_episode VALUES ('second')")
    with pytest.raises(DBAPIError, match="required rule check"), conn.begin_nested():
        run_bind()

    pair = {
        "checker": "admission",
        "scope": "partition-pair",
        "collection": "tokens",
        "form": "refers_to",
        "fingerprint": "pair-fingerprint",
        "parameters": {
            "paths": ["start", "end"],
            "target_paths": ["start", "end"],
            "target_role": "target",
            "target_kind": "urn:partitioned",
            "target_collection": "tokens",
            "target_key": "label",
        },
        "reads": [
            {"side": "source", "path": "label", "groups": ["labels"]},
            {"side": "source", "path": "start", "groups": ["geometry"]},
            {"side": "target", "path": "start", "groups": ["geometry"]},
        ],
    }
    conn.execute(
        insert(model.tables["sem.data_rule"]).values(
            release_id="release",
            rule_id="pair",
            kind_contract="partitioned",
            fingerprint=pair["fingerprint"],
            specification=pair,
        )
    )
    establish_pair = text(
        "SELECT ops.ddo_establish_rule(:rule,:product,:partition,:product,:partition)"
    ).bindparams(bindparam("rule", type_=JSONB()))
    for part in ("b", "a", "é"):
        conn.execute(establish_pair, dict(rule=pair, product=product, partition=part))
    target = {"role": "target", "product_id": product, "multiplicity": 1}
    run_bind(required="pair", targets=(target,))
    for targets in ((), (target, {**target, "member_id": "not-a-whole-product"})):
        with pytest.raises(DBAPIError, match="required rule pair"), conn.begin_nested():
            run_bind(required="pair", targets=targets)
