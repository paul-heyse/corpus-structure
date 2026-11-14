"""Independent SQL scalar/key vectors for the publication record cursor."""

import json
import struct

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.pdf_publication_native import pdf_record_logical_identity_sql
from corpus_structure.semantic.pdf_record_identity import canonical_scalar
from semantic.pdf_staging_support import private_build as private_build


def test_publication_inline_and_key_spelling(commit_db_engine):
    sql = pdf_record_logical_identity_sql()
    with commit_db_engine.begin() as conn:
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        conn.exec_driver_sql(sql, execution_options={"no_parameters": True})
        for value in (
            'quoted"\\\n',
            "\u03b1😀\x7f",
            "",
            "a/b~c",
            'quoted"\\path/segment',
            "".join(chr(code) for code in range(32, 127)),
        ):
            actual = conn.execute(
                text("SELECT ops.pdf_identity_ascii_string(:v)"), {"v": value}
            ).scalar_one()
            assert actual == json.dumps(value, ensure_ascii=True, separators=(",", ":"))
        for value in (None, True, False, 1729, -23, "unicode \u03b1"):
            actual = conn.execute(
                text("SELECT ops.pdf_identity_inline(CAST(:v AS jsonb))"), {"v": json.dumps(value)}
            ).scalar_one()
            assert actual == canonical_scalar(value)
        for value in ("", "β😀\n", "\u03b1" * 32768 + "😀"):
            actual = conn.execute(
                text("SELECT ops.pdf_identity_text(:v)"), {"v": value}
            ).scalar_one()
            assert actual == canonical_scalar(value)
        actual = conn.execute(
            text("SELECT ops.pdf_identity_inline(CAST(:v AS jsonb))"),
            {"v": json.dumps({"native_float64": struct.pack(">d", -0.0).hex()})},
        ).scalar_one()
        assert actual == canonical_scalar(-0.0)


def test_publication_inline_refuses_non_scalar(commit_db_engine):
    sql = pdf_record_logical_identity_sql()
    with commit_db_engine.begin() as conn:
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        conn.exec_driver_sql(sql, execution_options={"no_parameters": True})
        for value in (
            [],
            {},
            {"native_float64": "bad"},
            {"native_float64": "0" * 16, "extra": 1},
            1.2,
        ):
            with conn.begin_nested() as savepoint:
                with pytest.raises(DBAPIError, match=r"scalar|binary64"):
                    conn.execute(
                        text("SELECT ops.pdf_identity_inline(CAST(:v AS jsonb))"),
                        {"v": json.dumps(value)},
                    )
                savepoint.rollback()


@pytest.mark.parametrize("segmented", [False, True])
def test_actual_record_cursor_matches_independent_logical_fields(
    commit_db_engine, private_build, segmented
):
    from hashlib import sha256

    from corpus_structure.semantic.pdf_record_identity import LogicalIdentity, byte_root

    binding = dict(release_id=private_build.release_id, source_digest=private_build.source_digest)
    schema = "f" * 64
    expected = LogicalIdentity(schema, binding["release_id"], binding["source_digest"])
    expected.add_record("companion/health", "health", (("body", '{"ready":true}'), ("ordinal", 0)))
    relation = {
        "relation_id": "r1",
        "evidence": "ordered evidence",
        "endpoints": [
            {"role": "input", "input_index": 0, "occurrence_id": "before"},
            {"role": "output", "occurrence_id": "after"},
        ],
    }
    expected.add_record(
        "companion/relation",
        "r1",
        (("body", json.dumps(relation, sort_keys=True, separators=(",", ":"))), ("ordinal", 0)),
    )
    expected.add_record(
        "document",
        "root",
        (
            ("mapping_profile", "pdf-native-records-v1"),
            ("contract_version", "pdf-native-records-v1"),
            ("native_schema_digest", schema),
            ("root_id", "n"),
        ),
    )
    expected.add_record(
        "endpoint",
        '["r1",0]',
        (
            ("relation_id", "r1"),
            ("ordinal", 0),
            ("target_task_id", private_build.task_id),
            ("target_product_key", "native"),
            ("target_content_digest", "1" * 64),
            ("occurrence_id", "before"),
            ("role", "input"),
        ),
    )
    expected.add_record(
        "membership",
        '["n","children",0]',
        (("parent_id", "n"), ("field_name", "children"), ("ordinal", 0), ("value", None)),
    )
    map_key = '\u03b1/"'
    map_key_digest = canonical_scalar(map_key).hex()
    expected.add_record(
        "membership",
        f'["n","named","{map_key_digest}"]',
        (("parent_id", "n"), ("field_name", "named"), ("member_key", map_key), ("value", True)),
    )
    expected.add_record(
        "native",
        "n",
        (
            ("native_type", "TextItem"),
            ("family", "node"),
            ("children/kind", "array"),
            ("children/length", 1),
            ("named/kind", "map"),
            ("named/length", 1),
            ("note/value", -0.0),
            ("text/value", "hello"),
        ),
    )
    expected.add_record(
        "publication", "root", (("kind", "native"), ("recipe_digest", private_build.recipe_digest))
    )
    sql = pdf_record_logical_identity_sql()
    with commit_db_engine.begin() as conn:
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        # Before publication migration these two relations are not yet in the foundation.
        # Minimal identity-only tables let this independent protocol vector run against0064.
        conn.exec_driver_sql(
            "CREATE TABLE IF NOT EXISTS kb.pdf_record_companion(product_id text,"
            "revision_id text,family text,local_id text,body jsonb,ordinal bigint)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE IF NOT EXISTS kb.pdf_record_endpoint(product_id text,"
            "revision_id text,relation_id text,ordinal bigint,target_task_id bigint,"
            "target_product_key text,target_content_digest text,occurrence_id text,"
            "role text)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE IF NOT EXISTS ops.pdf_frozen_build(build_id text,"
            "frozen_digest text,kind text)"
        )
        conn.exec_driver_sql(sql, execution_options={"no_parameters": True})

        def execute(statement, parameters=None):
            query = statement.replace("'p'", "%(product)s").replace("'r'", "%(revision)s")
            for name in ("release", "source", "schema", "frozen"):
                query = query.replace(":" + name, "%(" + name + ")s")
            return conn.exec_driver_sql(
                query,
                {
                    "product": private_build.build_id,
                    "revision": private_build.build_id,
                    **(parameters or {}),
                },
            )

        execute(
            "INSERT INTO ops.pdf_frozen_build(build_id,frozen_digest,kind) "
            "VALUES ('p',:frozen,'native')",
            {"frozen": "0" * 64},
        )
        execute(
            "INSERT INTO ops.pdf_record_document VALUES ('p','r',:release,:source,"
            "'pdf-native-records-v1','pdf-native-records-v1',:schema,'n')",
            dict(release=binding["release_id"], source=binding["source_digest"], schema=schema),
        )
        execute(
            "INSERT INTO kb.pdf_record_native(product_id,revision_id,record_id,"
            "native_type,family,native_address,scalars_json,structure_json) VALUES "
            "('p','r','n','TextItem','node','#','{\"text\":\"hello\","
            '"note":{"native_float64":"8000000000000000"}}\','
            '\'{"fields":{"children":{"kind":"array","length":1},'
            '"named":{"kind":"map","length":1}}}\')'
        )
        execute(
            "INSERT INTO kb.pdf_record_membership(product_id,revision_id,parent_id,"
            "field_name,ordinal,value_kind,scalar_json) VALUES ('p','r','n',"
            "'children',0,'scalar','null')"
        )
        execute(
            "INSERT INTO kb.pdf_record_companion(product_id,revision_id,family,"
            "local_id,body,ordinal) VALUES ('p','r','health','health',"
            "'{\"ready\":true}',0)"
        )
        body = dict(relation)
        fields: tuple[tuple[str, str, str, bytes], ...] = ()
        if segmented:
            evidence = body.pop("evidence")
            assert isinstance(evidence, str)
            fields = (
                (
                    "endpoints",
                    "y",
                    "pdf-companion-json-field-v1",
                    json.dumps(body.pop("endpoints")).encode(),
                ),
                ("evidence", "s", "pdf-record-scalar-v1:s", evidence.encode()),
            )
            for name, kind, profile, payload in fields:
                size, root = byte_root((payload,))
                params = dict(
                    name=name,
                    size=size,
                    root=root.hex(),
                    profile=profile,
                    body=payload,
                    sha=sha256(payload).hexdigest(),
                    kind=kind,
                )
                execute(
                    "INSERT INTO ops.pdf_artifact_stream VALUES "
                    "('p','r',%(name)s,%(size)s,NULL,%(root)s,%(profile)s)",
                    params,
                )
                execute(
                    "INSERT INTO ops.pdf_artifact_part VALUES "
                    "('p','r',%(name)s,0,0,%(size)s,%(body)s,%(sha)s)",
                    params,
                )
            payload = map_key.encode()
            size, root = byte_root((payload,))
            params = dict(size=size, root=root.hex(), body=payload, sha=sha256(payload).hexdigest())
            execute(
                "INSERT INTO ops.pdf_artifact_stream VALUES "
                "('p','r','map-key',%(size)s,%(sha)s,%(root)s,'pdf-record-scalar-v1:s')",
                params,
            )
            execute(
                "INSERT INTO ops.pdf_artifact_part VALUES "
                "('p','r','map-key',0,0,%(size)s,%(body)s,%(sha)s)",
                params,
            )
        execute(
            "INSERT INTO kb.pdf_record_membership(product_id,revision_id,parent_id,"
            "field_name,ordinal,member_key,member_key_stream_id,value_kind,scalar_json) "
            "VALUES ('p','r','n','named',0,%(key)s,%(stream)s,'scalar','true')",
            {"key": None if segmented else map_key, "stream": "map-key" if segmented else None},
        )
        execute(
            "INSERT INTO kb.pdf_record_endpoint VALUES "
            "('p','r','r1',0,%(task)s,'native',%(digest)s,'before','input')",
            {"task": private_build.task_id, "digest": "1" * 64},
        )
        execute(
            "INSERT INTO kb.pdf_record_companion VALUES "
            "('p','r','relation','r1',%(body)s::jsonb,0)",
            {"body": json.dumps(body)},
        )
        if segmented:
            for name, kind, _, _ in fields:
                execute(
                    "INSERT INTO kb.pdf_record_companion_field VALUES "
                    "('p','r','relation','r1',%(name)s,%(name)s,%(kind)s)",
                    {"name": name, "kind": kind},
                )
        actual = execute("SELECT ops.pdf_record_logical_identity('p','r')").scalar_one()
        assert actual == expected.pin().logical_digest
        # Operational allocations are not identity-bearing.
        assert execute("SELECT ops.pdf_record_logical_identity('p','r')").scalar_one() == actual


@pytest.mark.parametrize(
    "defect", [None, "referenced-bytes", "unused-bytes", "unused-order", "unused-missing"]
)
def test_complete_identity_verifies_shared_and_unreferenced_streams(
    commit_db_engine, private_build, defect
):
    from hashlib import sha256

    from corpus_structure.semantic.pdf_record_identity import (
        LogicalIdentity,
        ScalarDescriptor,
        byte_root,
    )

    build = private_build
    schema = "f" * 64
    shared, unused = b"stable scalar", b"spare bytes"
    length, root = byte_root((shared,))
    scalar = ScalarDescriptor(b"s", length, root)
    expected = LogicalIdentity(schema, build.release_id, build.source_digest)
    expected.add_record(
        "document",
        "root",
        (
            ("mapping_profile", "pdf-native-records-v1"),
            ("contract_version", "pdf-native-records-v1"),
            ("native_schema_digest", schema),
            ("root_id", "root"),
        ),
    )
    expected.add_record(
        "native",
        "root",
        (("native_type", "TextItem"), ("family", "node"), ("a/value", scalar), ("b/value", scalar)),
    )
    expected.add_record(
        "publication", "root", (("kind", "native"), ("recipe_digest", build.recipe_digest))
    )
    with commit_db_engine.begin() as conn:
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        conn.exec_driver_sql(
            pdf_record_logical_identity_sql(), execution_options={"no_parameters": True}
        )
        params = dict(
            p=build.build_id, release=build.release_id, source=build.source_digest, schema=schema
        )
        conn.execute(
            text("INSERT INTO ops.pdf_frozen_build VALUES (:p,:digest,'native')"),
            params | {"digest": "0" * 64},
        )
        predecessor = "prior-" + build.build_id
        for product in (build.build_id, predecessor):
            conn.execute(
                text(
                    "INSERT INTO ops.pdf_record_document VALUES (:p,:p,:release,:source,"
                    "'pdf-native-records-v1','pdf-native-records-v1',:schema,'root')"
                ),
                params | {"p": product},
            )
        conn.execute(
            text(
                "INSERT INTO kb.pdf_record_native(product_id,revision_id,record_id,"
                "native_type,family,native_address,scalars_json,structure_json) VALUES "
                "(:p,:p,'root','TextItem','node','#','{}',CAST(:structure AS jsonb))"
            ),
            params
            | {
                "structure": json.dumps(
                    {
                        "fields": {
                            field: {"kind": "parts", "stream_id": "shared"} for field in ("a", "b")
                        }
                    }
                )
            },
        )
        for stream, content in (("shared", shared), ("unused", unused)):
            size, stream_root = byte_root((content,))
            body = (
                b"broken scalar"
                if defect == "referenced-bytes" and stream == "shared"
                else b"spare byte!"
                if defect == "unused-bytes" and stream == "unused"
                else content
            )
            for product, original in ((build.build_id, False), (predecessor, True)):
                conn.execute(
                    text(
                        "INSERT INTO ops.pdf_artifact_stream VALUES "
                        "(:p,:p,:stream,:size,:sha,:root,'pdf-record-scalar-v1:s')"
                    ),
                    dict(
                        p=product,
                        stream=stream,
                        size=size,
                        sha=sha256(content).hexdigest(),
                        root=stream_root.hex(),
                    ),
                )
                if not original and defect == "unused-missing" and stream == "unused":
                    continue
                part = content if original else body
                conn.execute(
                    text(
                        "INSERT INTO ops.pdf_artifact_part VALUES "
                        "(:p,:p,:stream,:ordinal,0,:size,:body,:sha)"
                    ),
                    dict(
                        p=product,
                        stream=stream,
                        ordinal=int(
                            not original and defect == "unused-order" and stream == "unused"
                        ),
                        size=size,
                        body=part,
                        sha=sha256(part).hexdigest(),
                    ),
                )
        for arguments in (":p,:p", ":p,:p,:prior"):
            statement = text(f"SELECT ops.pdf_record_logical_identity({arguments})")
            with conn.begin_nested() as savepoint:
                if defect is not None:
                    with pytest.raises(
                        DBAPIError,
                        match=(
                            r"artifact (actual bytes/ordinal/offset/length/digest|"
                            r"verified inventory/root) differs"
                        ),
                    ):
                        conn.execute(statement, params | {"prior": predecessor})
                    savepoint.rollback()
                else:
                    actual = conn.execute(statement, params | {"prior": predecessor}).scalar_one()
                    assert actual == expected.pin().logical_digest
