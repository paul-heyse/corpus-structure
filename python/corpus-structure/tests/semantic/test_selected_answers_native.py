"""Installed native answer paging over exact current characterization outputs."""

from time import perf_counter

import pytest

from corpus_structure.semantic.data_operation_values import decode_semantic_value
from corpus_structure.semantic.demand_results import (
    ReadLimit,
    acquire_selected_cut,
    read_selected_answer,
)
from semantic.characterization_native_support import (
    characterization_source as characterization_source,
)
from semantic.characterization_native_support import (
    current_characterization_recipe as current_characterization_recipe,
)
from semantic.characterization_native_support import operation_product, operation_use

FORMAL = "text.formal_evidence/source-native"
CONSTRUCTION = "text.constructions/source-native"


def test_native_filtered_outputs_seek_within_one_obligation(
    characterization_source, record_property
):
    source = characterization_source
    demand, _, snapshot = source.run(CONSTRUCTION)
    product = operation_product(snapshot, FORMAL)
    use = operation_use(snapshot, FORMAL)
    body = decode_semantic_value(product["body"])
    expected = {
        member["member_id"]: member["body"]
        for member in body["members"]
        if member["body"]["record_type"] == "occurrence"
    }
    assert len(expected) > 1
    selected, after, read_id, cut = [], None, None, None
    with source.reader.connect() as connection, source.kernel.engine.connect() as stats:
        reader_oid = connection.exec_driver_sql("select current_user::regrole::oid").scalar_one()
        connection.commit()

        def native_totals(program):
            return stats.exec_driver_sql(
                """
                SELECT coalesce(sum(calls), 0), coalesce(sum(total_exec_time), 0)
                FROM pg_stat_statements
                WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
                  AND userid = %s AND toplevel AND strpos(query, %s) > 0
                """,
                (reader_oid, "ops." + program + "("),
            ).one()

        def observe(phase, program, operation):
            calls_before, native_before = native_totals(program)
            started = perf_counter()
            with connection.begin():
                try:
                    result = operation()
                except ReadLimit as error:
                    # The native oversized-result response succeeds; its typed
                    # client refusal is reported after that read commits.
                    result = error
            elapsed_ms = (perf_counter() - started) * 1000
            calls_after, native_after = native_totals(program)
            assert calls_after - calls_before == 1
            native_ms = native_after - native_before
            for name, value in (("elapsed_ms", elapsed_ms), ("database_exec_ms", native_ms)):
                record_property(f"{phase}_{name}", value)
            if isinstance(result, ReadLimit):
                raise result
            return result

        scope = {"operation_id": FORMAL, "product_ids": [product["product_id"]]}
        fresh = observe(
            "fresh_cut",
            "acquire_data_read_context",
            lambda: acquire_selected_cut(
                connection, demand, project_id=source.factory.project_id, scope=scope
            ),
        )
        bound = dict(
            project_id=source.factory.project_id, scope=scope, read_id=fresh.record["read_id"]
        )

        def body_page(**filters):
            return read_selected_answer(
                connection,
                "read_selected_outputs",
                demand,
                product_id=product["product_id"],
                body=True,
                limit=1,
                **bound,
                **filters,
            )

        first = observe("whole_body", "read_selected_outputs", body_page)
        assert first["cut"] == fresh.record and first["rows"][0]["member_id"] is None
        second = observe(
            "continued_body",
            "read_selected_outputs",
            lambda: body_page(after=first["answer_after"]),
        )
        assert second["rows"][0]["member_id"] == min(row["member_id"] for row in body["members"])
        assert observe("same_budget_repeat", "read_selected_outputs", body_page) == first
        with pytest.raises(ReadLimit, match="exceeds max_bytes"):
            observe(
                "smaller_budget_repeat", "read_selected_outputs", lambda: body_page(max_bytes=1)
            )
        target = max(expected)
        exact = observe(
            "exact_member", "read_selected_outputs", lambda: body_page(member_id=target)
        )
        assert not exact["answer_after"] and [row["member_id"] for row in exact["rows"]] == [target]
        assert decode_semantic_value(exact["rows"][0]["meaning_body"]) == expected[target]

    with source.reader.begin() as connection:
        parent = read_selected_answer(
            connection,
            "read_selected_outputs",
            demand,
            project_id=source.factory.project_id,
            scope={"operation_id": FORMAL, "product_ids": [product["product_id"]]},
            product_id=product["product_id"],
            limit=1,
        )
        (container,) = parent["rows"]
        assert container["member_id"] is None
        assert parent["answer_after"][-1] == ""
        after_parent = read_selected_answer(
            connection,
            "read_selected_outputs",
            demand,
            project_id=source.factory.project_id,
            read_id=parent["cut"]["read_id"],
            scope={"operation_id": FORMAL, "product_ids": [product["product_id"]]},
            product_id=product["product_id"],
            after=parent["answer_after"],
            limit=1,
        )
        (first_member,) = after_parent["rows"]
        assert first_member["member_id"] == min(member["member_id"] for member in body["members"])
        selected_kind = next(
            member["kind_contract"] for member in body["members"] if member["member_id"] in expected
        )
        kind_members = sorted(
            member["member_id"]
            for member in body["members"]
            if member["kind_contract"] == selected_kind
        )
        scope = {"operation_id": FORMAL, "product_ids": [product["product_id"]]}
        acquired = acquire_selected_cut(
            connection,
            demand,
            project_id=source.factory.project_id,
            scope=scope,
            read_id=parent["cut"]["read_id"],
        )
        assert acquired.record == parent["cut"]
        selected_args = dict(
            project_id=source.factory.project_id,
            read_id=acquired.record["read_id"],
            scope=scope,
            use_id=use["use_id"],
            product_id=product["product_id"],
            limit=1,
        )
        combined = read_selected_answer(
            connection,
            "read_selected_outputs",
            demand,
            kind_contracts=["absent-kind", selected_kind],
            **selected_args,
        )
        assert combined["cut"] == acquired.record
        assert [row["member_id"] for row in combined["rows"]] == kind_members[:1]
        continued = read_selected_answer(
            connection,
            "read_selected_outputs",
            demand,
            after=combined["answer_after"],
            kind_contract=selected_kind,
            kind_contracts=["absent-kind", selected_kind],
            **selected_args,
        )
        assert [row["member_id"] for row in continued["rows"]] == kind_members[1:2]
        inconsistent = read_selected_answer(
            connection,
            "read_selected_outputs",
            demand,
            kind_contract=selected_kind,
            kind_contracts=["absent-kind"],
            **selected_args,
        )
        assert inconsistent["rows"] == [] and inconsistent["answer_after"] is None
        for ordinal, member_id in enumerate(sorted(expected)):
            answer = read_selected_answer(
                connection,
                "read_selected_outputs",
                demand,
                project_id=source.factory.project_id,
                read_id=read_id,
                scope={"operation_id": FORMAL, "product_ids": [product["product_id"]]},
                after=after,
                product_id=product["product_id"],
                record_type="occurrence",
                body=True,
                limit=1,
                max_bytes=8 * 1024**2,
            )
            if cut is None:
                cut = answer["cut"]
                read_id = cut["read_id"]
            assert answer["cut"] == cut
            (row,) = answer["rows"]
            assert row["member_id"] == member_id
            assert row["use_id"] == use["use_id"]
            assert row["derivation_id"] == use["derivation_id"]
            assert row["product_id"] == product["product_id"]
            assert decode_semantic_value(row["meaning_body"]) == expected[member_id]
            selected.append(row["member_id"])
            after = answer["answer_after"]
            assert after == (
                [
                    use["obligation_id"],
                    use["use_id"],
                    product["role"],
                    product["position"],
                    product["product_id"],
                    member_id,
                ]
                if ordinal + 1 < len(expected)
                else None
            )
        empty = read_selected_answer(
            connection,
            "read_selected_outputs",
            demand,
            project_id=source.factory.project_id,
            scope={"operation_id": FORMAL},
            product_id="not-selected",
            body=True,
        )
        assert empty["rows"] == [] and empty["answer_after"] is None
        construction = operation_use(snapshot, CONSTRUCTION)
        facts = read_selected_answer(
            connection,
            "read_selected_derivation_facts",
            demand,
            project_id=source.factory.project_id,
            scope={"operation_id": CONSTRUCTION},
            use_id=construction["use_id"],
            derivation_id=construction["derivation_id"],
        )
        expected_inputs = {
            (row["role"], row["product_id"], row.get("member_id"), row["multiplicity"])
            for row in construction["selection"]["inputs"]
        }
        actual_inputs = {
            (row["role"], row["product_id"], row["member_id"], row["multiplicity"])
            for row in facts["rows"]
        }
        assert actual_inputs == expected_inputs
        assert any(
            reference["derivation_id"] == use["derivation_id"]
            and reference["admission_use_id"] == use["use_id"]
            for row in facts["rows"]
            if row["product_id"] == product["product_id"]
            for reference in row["support"]
        )
    assert selected == sorted(expected)
