"""Private record foundations: model counterfactuals and actual native constraints."""

import pytest
import yaml
from linkml_runtime.utils.schemaview import SchemaView
from pydantic import ValidationError
from sqlalchemy import insert, text
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.exc import DBAPIError
from sqlalchemy.schema import CreateTable

from corpus_structure.schema.relational import compile_metadata
from corpus_structure.semantic.metadata import PHYSICAL_MODEL, PHYSICAL_MODEL_ID, physical_model_id
from corpus_structure.semantic.migrations import head_revision
from corpus_structure.semantic.pdf_record_model import (
    derived_record_tables,
    record_arrow_schema,
    record_boundary_adapter,
    record_tables,
    record_upload_tables,
)


def header_binding(engine):
    from hashlib import sha256

    from corpus_structure.semantic.metadata import table

    from .test_native_closure import archive

    prepared = archive(engine)[-1]
    source = b"%PDF-1.7 foundation source"
    digest = sha256(source).hexdigest()
    with engine.begin() as conn:
        conn.execute(text("SET LOCAL ROLE corpus_sem_publisher"))
        conn.execute(
            insert(table("kb.source_artifact")), dict(artifact_digest=digest, content=source)
        )
    return dict(
        release_id=prepared.release_id,
        source_digest=digest,
        mapping_profile="pdf-native-records-v1",
    )


def test_record_field_order_types_and_model_constraints():
    for name, table in record_upload_tables().items():
        schema = record_arrow_schema(name)
        adapter = record_boundary_adapter(name)
        assert schema.names == list(table.c.keys()) == list(adapter.json_schema()["properties"])
        assert [field.nullable for field in schema] == [column.nullable for column in table.c]
        assert schema.metadata[b"physical_model_id"].decode() == PHYSICAL_MODEL_ID
    with pytest.raises(ValidationError, match="greater than or equal"):
        record_boundary_adapter("kb.pdf_record_membership").validate_python(
            dict(
                product_id="p",
                revision_id="r",
                parent_id="n",
                field_name="children",
                ordinal=-1,
                value_kind="scalar",
                scalar_json=None,
            )
        )
    with pytest.raises(ValidationError, match="literal"):
        record_boundary_adapter("kb.pdf_record_native").validate_python(
            dict(
                product_id="p",
                revision_id="r",
                record_id="n",
                native_type="TextItem",
                family="made-up",
                native_address="#/texts/0",
                scalars_json={},
                structure_json={},
            )
        )


def test_independent_model_edit_changes_ddl_arrow_boundary_and_admission(tmp_path, monkeypatch):
    from corpus_structure.semantic import native_products, pdf_record_model, source_view_native

    copied = tmp_path / "physical.yaml"
    copied.write_bytes(PHYSICAL_MODEL.read_bytes())
    (tmp_path / "pdf-staging.yaml").write_bytes(
        PHYSICAL_MODEL.with_name("pdf-staging.yaml").read_bytes()
    )
    record_path = tmp_path / "pdf-records.yaml"
    declarations = yaml.safe_load(PHYSICAL_MODEL.with_name("pdf-records.yaml").read_bytes())
    declarations["classes"]["PdfRecordMembership"]["attributes"]["ordinal"]["minimum_value"] = 2
    del declarations["enums"]["PdfNativeRecordFamily"]["permissible_values"]["cell"]
    record_path.write_text(yaml.safe_dump(declarations, sort_keys=False))
    changed = compile_metadata(SchemaView(str(copied)), target="semantic")
    ddl = str(CreateTable(changed.tables["kb.pdf_record_membership"]).compile(dialect=dialect()))
    assert "ordinal >= 2" in ddl
    assert physical_model_id(copied) != PHYSICAL_MODEL_ID
    before = native_products.current_admission_fields()
    before_arrow = record_arrow_schema("kb.pdf_record_membership")
    for module in (native_products, pdf_record_model, source_view_native):
        monkeypatch.setattr(module, "metadata", changed)
    after = native_products.current_admission_fields()
    assert before["physical_checks_source_digest"] != after["physical_checks_source_digest"]
    assert not before_arrow.equals(
        record_arrow_schema("kb.pdf_record_membership"), check_metadata=True
    )
    with pytest.raises(ValidationError, match="greater than or equal to 2"):
        record_boundary_adapter("kb.pdf_record_membership").validate_python(
            dict(
                product_id="p",
                revision_id="r",
                parent_id="n",
                field_name="children",
                ordinal=1,
                value_kind="scalar",
            )
        )
    with pytest.raises(ValidationError, match="literal"):
        record_boundary_adapter("kb.pdf_record_native").validate_python(
            dict(
                product_id="p",
                revision_id="r",
                record_id="n",
                native_type="TableCell",
                family="cell",
                native_address="#/tables/0/cells/0",
                scalars_json={},
                structure_json={},
            )
        )


def test_current_publication_uses_record_products_without_legacy_bridges():
    from corpus_structure.semantic.pdf_publication_native import publication_sql

    sql = publication_sql()
    assert "legacy_integrated_source_context" not in sql
    assert "FROM kb.native_document_" not in sql
    assert "FROM ops.native_document_product" not in sql
    assert "FROM kb.pdf_record_access" in sql
    assert "FROM ops.pdf_published_revision" in sql


def test_private_native_foundations_and_constraints(semantic_db_engine):
    from hashlib import sha256

    from corpus_structure.semantic.execution_admission import _verify_deployment_functions
    from corpus_structure.semantic.pdf_records import iter_native_records

    tables = record_tables()
    binding = header_binding(semantic_db_engine)
    with semantic_db_engine.begin() as conn:
        _verify_deployment_functions(conn)
        assert (
            conn.execute(text("SELECT version_num FROM semantic_alembic_version")).scalar_one()
            == head_revision()
        )
        assert (
            conn.execute(
                text("SELECT count(*) FROM sem.physical_contract WHERE physical_id=:id"),
                {"id": PHYSICAL_MODEL_ID},
            ).scalar_one()
            == 1
        )
        for role in (
            "corpus_sem_writer",
            "corpus_sem_reader",
            "corpus_sem_admitter",
            "corpus_sem_evaluator",
        ):
            for name in tables:
                assert not conn.execute(
                    text(
                        "SELECT has_table_privilege(:role,:name,"
                        "'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')"
                    ),
                    {"role": role, "name": name},
                ).scalar_one()
        conn.execute(text("SET LOCAL ROLE corpus_sem_publisher"))
        conn.execute(
            insert(tables["ops.pdf_record_document"]),
            dict(
                product_id="p",
                revision_id="r",
                contract_version="pdf-native-records-v1",
                native_schema_digest="a" * 64,
                root_id="root",
                **binding,
            ),
        )
        for changes in (
            {"source_digest": "c" * 64},
            {"release_id": "release:missing"},
            {"mapping_profile": "other"},
        ):
            header = dict(
                product_id="wrong",
                revision_id="r",
                contract_version="pdf-native-records-v1",
                native_schema_digest="a" * 64,
                root_id="root",
                **binding,
            )
            header.update(changes)
            with pytest.raises(DBAPIError), conn.begin_nested():
                conn.execute(insert(tables["ops.pdf_record_document"]), header)
        native = dict(
            product_id="p",
            revision_id="r",
            record_id="root",
            native_type="DoclingDocument",
            family="header",
            native_address="#",
            scalars_json={},
            structure_json={},
        )
        conn.execute(insert(tables["kb.pdf_record_native"]), native)
        invalid = dict(native, record_id="bad", native_address="#/bad", family="unmodelled")
        with pytest.raises(DBAPIError, match="check constraint"), conn.begin_nested():
            conn.execute(insert(tables["kb.pdf_record_native"]), invalid)
        for changes in ({"ordinal": -1}, {"value_kind": "unmodelled"}):
            row = dict(
                product_id="p",
                revision_id="r",
                parent_id="root",
                field_name="children",
                ordinal=0,
                value_kind="scalar",
                scalar_json=1,
            )
            row.update(changes)
            with pytest.raises(DBAPIError, match="check constraint"), conn.begin_nested():
                conn.execute(insert(tables["kb.pdf_record_membership"]), row)
        with pytest.raises(DBAPIError, match="immutable semantic content"), conn.begin_nested():
            conn.execute(text("UPDATE kb.pdf_record_native SET native_type=native_type"))
        native_fixture = {
            "schema_name": "DoclingDocument",
            "version": "1.10.0",
            "name": "Foundation",
            "body": {"self_ref": "#/body", "children": []},
            "furniture": {"self_ref": "#/furniture", "children": []},
            "groups": [],
            "texts": [],
            "pictures": [],
            "tables": [],
            "pages": {},
        }

        def unexpected_parts(*args):
            raise AssertionError("bounded fixture unexpectedly requires scalar parts")

        rows = list(
            iter_native_records(
                native_fixture,
                product_id="lowered",
                revision_id="r",
                release_id=binding["release_id"],
                source_digest=binding["source_digest"],
                record_id_for=lambda address, kind: sha256((address + kind).encode()).hexdigest(),
                write_scalar=unexpected_parts,
            )
        )
        for kind, relation in (
            ("document", "ops.pdf_record_document"),
            ("native", "kb.pdf_record_native"),
            ("membership", "kb.pdf_record_membership"),
            ("reference", "kb.pdf_record_reference"),
        ):
            adapter = record_boundary_adapter(relation)
            for row in rows:
                if row.kind == kind:
                    values = row.physical_values()
                    adapter.validate_python(values)
                    conn.execute(insert(tables[relation]), values)


def test_previous_execution_abi_requires_regeneration():
    import json

    from corpus_structure.semantic.contracts import (
        _bound_execution_model,
        compile_execution_model,
        require_payload_operation,
        trusted_execution_inputs,
    )

    current = compile_execution_model(trusted_execution_inputs())
    previous = json.loads(current.content)
    previous["inputs"]["compiler_version"] = "14"
    from corpus_structure.semantic.types import PreparationError

    with pytest.raises(
        PreparationError, match="execution product requires current compiler 23; regenerate"
    ):
        _bound_execution_model(json.dumps(previous).encode(), current.model_id)
    with pytest.raises(
        PreparationError, match="execution product requires current compiler 23; regenerate"
    ):
        require_payload_operation(
            json.dumps(previous).encode(), current.model_id, "publish_integrated_pdf"
        )


def test_artifact_native_verifier_reads_actual_parts(semantic_db_engine):
    from hashlib import sha256

    from corpus_structure.semantic.pdf_record_identity import byte_root

    tables = record_tables()
    binding = header_binding(semantic_db_engine)
    body = b"exact retained bytes\x00" * 5000
    root = byte_root((body,))[1].hex()
    with semantic_db_engine.begin() as conn:
        conn.execute(text("SET LOCAL ROLE corpus_sem_publisher"))
        conn.execute(
            insert(tables["ops.pdf_record_document"]),
            dict(
                product_id="artifact",
                revision_id="r",
                contract_version="pdf-native-records-v1",
                native_schema_digest="b" * 64,
                root_id="root",
                **binding,
            ),
        )
        stream_table, part_table = (
            tables["ops.pdf_artifact_stream"],
            tables["ops.pdf_artifact_part"],
        )
        verify = text("SELECT * FROM ops.pdf_identity_verify_artifact(:p,'r',:s,:admitted)")
        # Deliberately use a transport boundary that differs from canonical 64 KiB blocks.
        for stream_id, fault in (
            ("valid", None),
            ("gap", "offset"),
            ("changed", "bytes"),
            ("missing", "missing"),
            ("root", "root"),
        ):
            conn.execute(
                insert(stream_table),
                dict(
                    product_id="artifact",
                    revision_id="r",
                    stream_id=stream_id,
                    byte_length=len(body),
                    serialization_sha256=sha256(body).hexdigest(),
                    byte_root=("0" * 64 if fault == "root" else root),
                    encoding_profile="exact-bytes-1",
                ),
            )
            offset = 0
            for ordinal, start in enumerate(range(0, len(body), 10000)):
                part = body[start : start + 10000]
                if fault == "missing" and ordinal == 1:
                    offset += len(part)
                    continue
                if fault == "bytes" and ordinal == 1:
                    part = b"x" + part[1:]
                conn.execute(
                    insert(part_table),
                    dict(
                        product_id="artifact",
                        revision_id="r",
                        stream_id=stream_id,
                        ordinal=ordinal,
                        byte_offset=offset + (1 if fault == "offset" and ordinal == 1 else 0),
                        byte_length=len(part),
                        body=part,
                        sha256_digest=sha256(part).hexdigest(),
                    ),
                )
                offset += len(part)
            if fault:
                with pytest.raises(DBAPIError, match="artifact"), conn.begin_nested():
                    conn.execute(verify, {"p": "artifact", "s": stream_id, "admitted": None}).one()
            else:
                result = conn.execute(
                    verify, {"p": "artifact", "s": stream_id, "admitted": body}
                ).one()
                assert result.actual_length == len(body)
                assert bytes(result.actual_byte_root).hex() == root
                assert result.retained_correspondence
                with pytest.raises(DBAPIError, match="retained bytes"), conn.begin_nested():
                    conn.execute(
                        verify, {"p": "artifact", "s": stream_id, "admitted": b"different"}
                    ).one()


@pytest.mark.parametrize(
    ("declaration", "expected"),
    [
        ("a text, OUT b bigint", "sample(text)"),
        ("INOUT a text, OUT b bigint", "sample(text)"),
        ("VARIADIC a text[]", "sample(text[])"),
        ("a text", "sample(text)"),
    ],
)
def test_function_identity_uses_only_input_bearing_arguments(declaration, expected):
    from pglast import parse_sql

    from corpus_structure.semantic.native_function_signatures import function_signature

    result = "TABLE(x bigint,y bytea)" if declaration == "a text" else "record"
    statement = parse_sql(
        f"CREATE FUNCTION sample({declaration}) RETURNS {result} LANGUAGE sql AS $$SELECT 1$$"
    )[0].stmt
    from pglast import ast

    assert isinstance(statement, ast.CreateFunctionStmt)
    assert function_signature(statement) == expected


def test_output_alias_retirement_preserves_declared_overloads():
    from pglast import parse_sql

    from corpus_structure.semantic.native_function_signatures import remove_output_signature_aliases

    statement = (
        "CREATE FUNCTION sample(a text) RETURNS TABLE(x bigint,y bytea) "
        "LANGUAGE sql AS $$SELECT 1$$;"
    )
    functions = {"sample(text,bigint,bytea)": {}, "other(bigint)": {}}
    remove_output_signature_aliases(functions, parse_sql(statement))
    assert set(functions) == {"other(bigint)"}
    functions["sample(text,bigint,bytea)"] = {}
    overload = (
        "CREATE FUNCTION sample(a text,x bigint,y bytea) RETURNS record "
        "LANGUAGE sql AS $$SELECT 1$$;"
    )
    remove_output_signature_aliases(functions, parse_sql(statement + overload))
    assert "sample(text,bigint,bytea)" in functions


def test_table_return_inventory_and_model_owned_read_roles(monkeypatch):
    from corpus_structure.semantic.native_inventory import update_function_inventory
    from corpus_structure.semantic.native_products import relation_descriptor

    functions = {}
    from pathlib import Path

    update_function_inventory(
        functions,
        Path(__file__)
        .parents[2]
        .joinpath("src/corpus_structure/semantic/sql/pdf_record_artifact_identity.sql")
        .read_text(),
    )
    signature = "ops.pdf_identity_verify_artifact(text,text,text,bytea)"
    assert functions[signature]["result"] == "pg_catalog.record"
    assert functions[signature]["setof"] is True
    assert signature[:-1] + ",bigint,bytea,boolean)" not in functions
    relation = record_tables()["kb.pdf_record_reference"]
    assert relation_descriptor(relation)["read_roles"] == []
    monkeypatch.setitem(relation.info, "read_roles", ["corpus_sem_reader"])
    assert relation_descriptor(relation)["read_roles"] == ["corpus_sem_reader"]


def test_actual_native_release_guard_after_activation(semantic_db_engine, admitter):
    from uuid import uuid4

    from corpus_structure.semantic import PreparationProfile, ResolvedDependencies, prepare_release
    from corpus_structure.semantic.composed import composed_dependencies
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.releases import activate_release, persist_release

    from .test_execution_release import _bundle

    bundle = _bundle()
    dependencies = composed_dependencies(ResolvedDependencies())
    profile = PreparationProfile(version="semantic-2")
    prepared = prepare_release(bundle, dependencies, profile)
    project = str(uuid4())
    with semantic_db_engine.begin() as conn:
        conn.execute(insert(table("data.project")), dict(project_id=project))
    with admitter.begin() as conn:
        persist_release(conn, bundle, dependencies, profile, prepared)
        activate_release(
            conn, project, prepared.release_id, expected_parent=None, expected_generation=0
        )
        conn.execute(text("SELECT data.require_execution_release(:r)"), {"r": prepared.release_id})
    with semantic_db_engine.begin() as conn:
        conn.execute(text("SET LOCAL ROLE corpus_sem_publisher"))
        conn.execute(text("GRANT SELECT ON kb.pdf_record_reference TO corpus_sem_reader"))
    with (
        admitter.begin() as conn,
        pytest.raises(DBAPIError, match="native source frame projection differs"),
    ):
        conn.execute(text("SELECT data.require_execution_release(:r)"), {"r": prepared.release_id})
    with semantic_db_engine.begin() as conn:
        conn.execute(text("SET LOCAL ROLE corpus_sem_publisher"))
        conn.execute(text("REVOKE SELECT ON kb.pdf_record_reference FROM corpus_sem_reader"))
        conn.execute(
            text("GRANT SELECT(native_pointer) ON kb.pdf_record_reference TO corpus_sem_reader")
        )
    with (
        admitter.begin() as conn,
        pytest.raises(DBAPIError, match="native source frame projection differs"),
    ):
        conn.execute(text("SELECT data.require_execution_release(:r)"), {"r": prepared.release_id})


def test_graph_cell_identifiers_survive_native_relational_lowering(semantic_db_engine):
    from hashlib import sha256

    from corpus_structure.semantic.pdf_records import iter_native_records

    tables = record_tables()
    binding = header_binding(semantic_db_engine)

    def refuse_external_scalar(stream_id: str, encoding_profile: str, chunks: object):
        raise AssertionError("unexpected external scalar")

    rows = list(
        iter_native_records(
            {"label": "to_value", "source_cell_id": 10, "target_cell_id": 20},
            native_type="GraphLink",
            product_id="graph",
            revision_id="r",
            release_id=binding["release_id"],
            source_digest=binding["source_digest"],
            record_id_for=lambda address, kind: sha256((address + kind).encode()).hexdigest(),
            write_scalar=refuse_external_scalar,
        )
    )
    with semantic_db_engine.begin() as conn:
        conn.execute(text("SET LOCAL ROLE corpus_sem_publisher"))
        conn.execute(
            insert(tables["ops.pdf_record_document"]),
            dict(
                product_id="graph",
                revision_id="r",
                root_id=next(r.values["record_id"] for r in rows if r.kind == "native"),
                native_schema_digest="c" * 64,
                contract_version="pdf-native-records-v1",
                **binding,
            ),
        )
        for kind, relation in (
            ("native", "kb.pdf_record_native"),
            ("reference", "kb.pdf_record_reference"),
        ):
            for row in rows:
                if row.kind == kind:
                    values = row.physical_values()
                    record_boundary_adapter(relation).validate_python(values)
                    conn.execute(insert(tables[relation]), values)
        assert conn.execute(
            text(
                "SELECT native_pointer FROM kb.pdf_record_reference "
                "WHERE product_id='graph' ORDER BY field_name"
            )
        ).scalars().all() == ["10", "20"]


def test_derived_record_roles_keep_unbounded_numeric_in_exact_core_boundary():
    from decimal import Decimal

    from sqlalchemy import Numeric

    derived = derived_record_tables()
    assert set(derived) == {"kb.pdf_record_access", "kb.pdf_record_region"}
    assert set(record_tables()) == set(record_upload_tables()) | set(derived)
    relation = derived["kb.pdf_record_region"]
    assert isinstance(relation.c.left.type, Numeric)
    assert relation.c.left.type.precision is None and relation.c.left.type.scale is None
    exact = Decimal("123456789012345678901234567890.123456789012345678901234567890")
    value = dict(
        product_id="p",
        revision_id="p",
        pointer="#/texts/0",
        region_index=0,
        page_no=1,
        page_width=exact,
        page_height=exact,
        left=exact,
        top=exact,
        right=exact,
        bottom=exact,
        origin="TOPLEFT",
    )
    actual = record_boundary_adapter("kb.pdf_record_region").validate_python(value)
    assert actual.left == exact and type(actual.left) is Decimal
    for name in derived:
        with pytest.raises(ValueError, match=r"derived PDF record projection.*SQLAlchemy Core"):
            record_arrow_schema(name)


def test_independent_model_role_edit_changes_wire_selection(tmp_path):
    from corpus_structure.semantic.pdf_record_model import (
        derived_record_tables,
        record_upload_tables,
    )

    copied = tmp_path / "physical.yaml"
    copied.write_bytes(PHYSICAL_MODEL.read_bytes())
    (tmp_path / "pdf-records.yaml").write_bytes(
        PHYSICAL_MODEL.with_name("pdf-records.yaml").read_bytes()
    )
    declarations = yaml.safe_load(PHYSICAL_MODEL.with_name("pdf-staging.yaml").read_bytes())
    declarations["classes"]["PdfRecordAccess"]["annotations"]["pds:record_boundary_role"] = "upload"
    (tmp_path / "pdf-staging.yaml").write_text(yaml.safe_dump(declarations, sort_keys=False))
    changed = compile_metadata(SchemaView(str(copied)), target="semantic")
    assert "kb.pdf_record_access" in derived_record_tables()
    assert "kb.pdf_record_access" not in derived_record_tables(changed)
    assert "kb.pdf_record_access" in record_upload_tables(changed)
    assert "kb.pdf_record_region" in derived_record_tables(changed)
