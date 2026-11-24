"""Published PDF envelopes and views retain independent native visibility contracts."""

import pytest
from sqlalchemy import Column, MetaData, Table, select, text
from sqlalchemy.schema import CreateSchema, CreateTable

from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import (
    NativeIdentity,
    execute_native_sql,
    native_owner,
    native_privilege_sql,
)
from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
from corpus_structure.semantic.pdf_domain import PREFIX
from corpus_structure.semantic.pdf_publication_native import (
    published_pin_programs,
    published_view_programs,
)


@pytest.fixture
def published_envelopes(infrastructure_rollback):
    connection = infrastructure_rollback
    model = MetaData(info=get_metadata().info)
    for name in (
        "ops.pdf_published_revision",
        "ops.pdf_stage_build",
        "ops.pdf_build_validation",
        "ops.pdf_frozen_build",
        "ops.pdf_product",
        "ops.pdf_producer_certification",
        "ops.pdf_roundtrip_oracle",
        "kb.pdf_record_access",
        "kb.pdf_record_page_access",
        "kb.pdf_record_companion",
        "sem.input",
    ):
        source = get_metadata().tables[name]
        Table(
            source.name,
            model,
            *(Column(c.name, c.type) for c in source.columns),
            schema=source.schema,
        )
    for schema in ("ops", "kb", "sem"):
        connection.execute(CreateSchema(schema))
        for role in (
            "corpus_sem_publisher",
            "corpus_sem_writer",
            "corpus_sem_reader",
            "corpus_sem_evaluator",
            "corpus_sem_admitter",
        ):
            execute_native_sql(
                connection,
                native_privilege_sql(
                    NativeIdentity("schema", "", schema),
                    role,
                    None if role == "corpus_sem_publisher" else "usage",
                ),
            )
    with native_owner(connection, "corpus_sem_publisher"):
        for relation in model.tables.values():
            connection.execute(CreateTable(relation))
        # Decoder output deliberately differs from the stored wire representation.
        connection.exec_driver_sql("""
            CREATE FUNCTION ops.pdf_companion_body(text,text,text,text,jsonb)
            RETURNS jsonb LANGUAGE sql IMMUTABLE AS $$
              SELECT $5 || jsonb_build_object('value',$5->'decoded')
            $$
        """)
        from corpus_structure.semantic.native_program_registry import render_programs

        domain = trusted_pdf_context().domain
        programs = render_programs(
            (*published_pin_programs(model), *published_view_programs(model, domain)),
            registry_schemas=frozenset({"ops"}),
            prerequisites=frozenset(
                {
                    NativeIdentity(
                        "function",
                        "ops",
                        "pdf_companion_body",
                        ("text", "text", "text", "text", "jsonb"),
                    ),
                    NativeIdentity(
                        "function",
                        "ops",
                        "pdf_companion_field_bytes",
                        ("text", "text", "text", "text", "text"),
                    ),
                }
            ),
        )
        for item in programs:
            for statement in item.declared_definition.install_sql:
                execute_native_sql(connection, statement)
    published = model.tables["ops.pdf_published_revision"]
    for build, task, key, release in (("b1", 7, "one", "r1"), ("b2", 8, "two", "r2")):
        connection.execute(
            published.insert().values(
                build_id=build,
                task_id=task,
                product_key=key,
                release_id=release,
                logical_digest="logical-" + build,
                schema_digest="schema",
                recipe_digest="recipe",
                source_digest="source",
                frozen_digest="frozen",
                kind="native",
            )
        )
        connection.execute(
            model.tables["ops.pdf_stage_build"]
            .insert()
            .values(
                build_id=build,
                task_id=task,
                release_id=release,
                state="published",
                source_digest="source",
                schema_digest="schema",
                recipe_digest="recipe",
            )
        )
        connection.execute(
            model.tables["ops.pdf_build_validation"]
            .insert()
            .values(
                build_id=build,
                frozen_digest="frozen",
                logical_digest="logical-" + build,
                contract_digest="contract-" + build,
                native_callbacks=True,
                certification_basis="round-trip-verified",
                lowering_identity="lowering",
                attested_logical_digest="logical-" + build,
                native_document_digest="native-digest",
                oracle_receipt_id="oracle-" + build,
            )
        )
        for input_name, input_kind, digest in (
            (PREFIX + "schema/pdf_products", "dependency", "contract-" + build),
            ("execution/schema/pdf_products", "dependency", "legacy-decoy"),
            (PREFIX + "schema/pdf_products", "source", "wrong-kind"),
        ):
            connection.execute(
                model.tables["sem.input"]
                .insert()
                .values(
                    release_id=release,
                    input_name=input_name,
                    input_kind=input_kind,
                    content_digest=digest,
                )
            )
    return connection, model


def test_published_views_keep_exact_dependency_health_and_model_field_order(published_envelopes):
    connection, model = published_envelopes
    companions = model.tables["kb.pdf_record_companion"]
    for build, revision, local, ordinal, body in (
        ("b1", "wrong", "foreign-revision", -9, {"source_scope": "partial", "result": "wrong"}),
        ("b1", "b1", "unscoped", -8, {"result": "unscoped"}),
        ("b1", "b1", "z", 0, {"source_scope": "whole", "result": "late"}),
        (
            "b1",
            "b1",
            "a",
            0,
            {
                "source_scope": "partial",
                "page_start": 1,
                "page_end": 2,
                "result": "first",
                "nested": {"page_start": 3},
            },
        ),
        ("b2", "b2", "a", 0, {"source_scope": "whole", "result": "second"}),
    ):
        connection.execute(
            companions.insert().values(
                product_id=build,
                revision_id=revision,
                family="health",
                local_id=local,
                ordinal=ordinal,
                body=body,
            )
        )
    for family, view in (("access", "pdf_published_item"), ("region", "pdf_published_region")):
        relation = model.tables["kb.pdf_record_" + family]
        connection.execute(
            relation.insert().values(product_id="b1", revision_id="other", pointer="#/texts/0")
        )
        # Existing views intentionally join the published product, without a revision predicate.
        with native_owner(connection, "corpus_sem_reader"):
            result = connection.execute(text("SELECT * FROM ops." + view))
            assert tuple(result.keys()) == (
                "task_id",
                "product_key",
                *(c.name for c in relation.columns if c.name not in ("product_id", "revision_id")),
            )
            assert [(r.task_id, r.product_key, r.pointer) for r in result] == [
                (7, "one", "#/texts/0")
            ]
    with native_owner(connection, "corpus_sem_admitter"):
        rows = (
            connection.execute(text("SELECT * FROM ops.pdf_selected_product ORDER BY task_id"))
            .mappings()
            .all()
        )
    assert [(r["task_id"], r["contract_digest"], r["health"]) for r in rows] == [
        (7, "contract-b1", {"result": "first", "nested": {"page_start": 3}}),
        (8, "contract-b2", {"result": "second"}),
    ]
    for row in rows:
        assert tuple(row) == (
            "task_id",
            "product_key",
            "content_digest",
            "release_id",
            "contract_digest",
            "schema_digest",
            "recipe_digest",
            "parent_task_id",
            "parent_product_key",
            "parent_digest",
            "native_json",
            "health",
            "payload",
        )
        assert all(
            row[field] is None
            for field in (
                "parent_task_id",
                "parent_product_key",
                "parent_digest",
                "native_json",
                "payload",
            )
        )


def test_published_coverage_decodes_and_preserves_existing_product_scope(published_envelopes):
    connection, model = published_envelopes
    companion = model.tables["kb.pdf_record_companion"]
    decoded = {
        "section_pointer": "#/body",
        "membership": "complete",
        "universe": "native",
        "outcome": "success",
        "policy": "declared",
    }
    for family, kind, build, revision in (
        ("native_metadata", "recognition_coverage", "b1", "other"),
        ("native_metadata", "other", "b1", "b1"),
        ("other", "recognition_coverage", "b1", "b1"),
        ("native_metadata", "recognition_coverage", "not-published", "not-published"),
    ):
        connection.execute(
            companion.insert().values(
                product_id=build,
                revision_id=revision,
                family=family,
                local_id=kind,
                body={"kind": kind, "value": {"outcome": "wrong"}, "decoded": decoded},
            )
        )
    with native_owner(connection, "corpus_sem_reader"):
        assert connection.execute(
            text("SELECT * FROM ops.pdf_published_coverage")
        ).mappings().all() == [
            {"task_id": 7, "product_key": "one", **decoded},
        ]
    definition = connection.scalar(
        text("SELECT pg_get_viewdef('ops.pdf_published_coverage'::regclass)")
    )
    assert "AS MATERIALIZED" in definition


def test_published_readers_keep_exact_composite_pins_and_validation_custody(published_envelopes):
    connection, model = published_envelopes
    for name, values in (
        ("ops.pdf_frozen_build", dict(build_id="b1", frozen_digest="frozen", kind="native")),
        (
            "ops.pdf_product",
            dict(
                task_id=7,
                product_key="one",
                content_digest="logical-b1",
                release_id="r1",
                artifact_digest="source",
                kind="native",
                contract_digest="contract-b1",
            ),
        ),
        (
            "ops.pdf_producer_certification",
            dict(
                build_id="b1",
                lowering_identity="lowering",
                logical_digest="logical-b1",
                native_document_digest="native-digest",
                kind="native",
            ),
        ),
        (
            "ops.pdf_roundtrip_oracle",
            dict(
                oracle_receipt_id="oracle-b1",
                lowering_identity="lowering",
                kind="native",
                state="passed",
                actual_native_digest="native-digest",
                native_document_digest="native-digest",
                build_id="b1",
                frozen_digest="frozen",
            ),
        ),
    ):
        connection.execute(model.tables[name].insert().values(**values))
    for routine, relation in (
        ("revision", "ops.pdf_published_revision"),
        ("validation", "ops.pdf_build_validation"),
    ):
        query = text("SELECT * FROM ops.read_pdf_published_" + routine + "(:task,:key,:digest)")
        expected = connection.execute(
            select(model.tables[relation]).where(model.tables[relation].c.build_id == "b1")
        ).one()
        with native_owner(connection, "corpus_sem_reader"):
            assert (
                connection.execute(query, dict(task=7, key="one", digest="logical-b1")).one()
                == expected
            )
            for parameters in (
                dict(task=8, key="one", digest="logical-b1"),
                dict(task=7, key="two", digest="logical-b1"),
                dict(task=7, key="one", digest="wrong"),
            ):
                assert connection.execute(query, parameters).all() == []
    validation = model.tables["ops.pdf_build_validation"]
    connection.execute(
        validation.update()
        .where(validation.c.build_id == "b1")
        .values(attested_logical_digest="wrong")
    )
    with native_owner(connection, "corpus_sem_reader"):
        assert (
            connection.execute(
                text("SELECT * FROM ops.read_pdf_published_validation(7,'one','logical-b1')")
            ).all()
            == []
        )
        assert (
            len(
                connection.execute(
                    text("SELECT * FROM ops.read_pdf_published_revision(7,'one','logical-b1')")
                ).all()
            )
            == 1
        )
    build = model.tables["ops.pdf_stage_build"]
    connection.execute(build.update().where(build.c.build_id == "b1").values(state="prepared"))
    with native_owner(connection, "corpus_sem_reader"):
        assert (
            connection.execute(
                text("SELECT * FROM ops.read_pdf_published_revision(7,'one','logical-b1')")
            ).all()
            == []
        )


def test_published_acl_keeps_public_closed_and_purpose_grants(published_envelopes):
    connection, _ = published_envelopes
    actual = (
        connection.execute(
            text("""
        SELECT p.proname, p.prosecdef, p.provolatile, p.proconfig,
          r.rolname AS owner, a.grantee, a.privilege_type
        FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
        JOIN pg_roles r ON r.oid=p.proowner CROSS JOIN LATERAL aclexplode(p.proacl) a
        WHERE n.nspname='ops' AND p.proname IN
          ('read_pdf_published_revision','read_pdf_published_validation')
    """)
        )
        .mappings()
        .all()
    )
    owners = {r["owner"] for r in actual}
    assert owners == {"corpus_sem_publisher"}
    roles = dict(connection.execute(text("SELECT oid,rolname FROM pg_roles")).all())
    for name in ("read_pdf_published_revision", "read_pdf_published_validation"):
        rows = [row for row in actual if row["proname"] == name]
        assert {(roles.get(row["grantee"], "PUBLIC"), row["privilege_type"]) for row in rows} == {
            (role, "EXECUTE")
            for role in (
                "corpus_sem_publisher",
                "corpus_sem_writer",
                "corpus_sem_reader",
                "corpus_sem_evaluator",
            )
        }
        assert all(
            row["prosecdef"]
            and row["provolatile"] == "s"
            and row["proconfig"] == ["search_path=pg_catalog, pg_temp"]
            for row in rows
        )
    for name, extra in (
        ("pdf_published_item", ()),
        ("pdf_published_region", ()),
        ("pdf_selected_product", ("corpus_sem_admitter",)),
        ("pdf_published_coverage", ()),
    ):
        rows = connection.execute(
            text("""
            SELECT r.rolname,a.grantee,a.privilege_type FROM pg_class c
            JOIN pg_roles r ON r.oid=c.relowner CROSS JOIN LATERAL aclexplode(c.relacl) a
            WHERE c.oid=CAST(:name AS regclass)
        """),
            {"name": "ops." + name},
        ).all()
        assert {row.rolname for row in rows} == {"corpus_sem_publisher"}
        assert {
            (roles.get(row.grantee, "PUBLIC"), row.privilege_type)
            for row in rows
            if row.grantee
            != next(oid for oid, role in roles.items() if role == "corpus_sem_publisher")
        } == {
            (role, "SELECT")
            for role in ("corpus_sem_writer", "corpus_sem_reader", "corpus_sem_evaluator", *extra)
        }
