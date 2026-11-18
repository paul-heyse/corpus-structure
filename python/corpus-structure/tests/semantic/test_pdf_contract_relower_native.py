"""Authenticated old PDF facts retain their own identity during a forward DATA step."""

from hashlib import sha256

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.native_objects import execute_native_sql
from corpus_structure.semantic.pdf_domain import CONTRACT
from corpus_structure.semantic.pdf_domain_native import pdf_domain_native_sql
from corpus_structure.semantic.types import SourceArtifact


def _fixture(conn, *, changed_input=False, current_contract=False):
    conn.exec_driver_sql("CREATE SCHEMA sem; CREATE SCHEMA ops")
    conn.exec_driver_sql("""
CREATE TABLE sem.input(release_id text,input_kind text,input_name text,
 content bytea,content_digest text);
CREATE TABLE sem.data_operation_definition(release_id text,support_contract jsonb);
CREATE TABLE sem.pdf_operation_contract(release_id text,operation_id text,
 contract_id text,contract_digest text,PRIMARY KEY(release_id,operation_id));
""")
    payload = b"authenticated retained input"
    facet = canonical_bytes(
        {
            "inputs": [
                {"name": "pdf-domain/schema/pdf_products", "sha256": sha256(payload).hexdigest()}
            ],
            "actions": {"owned-action": {"contract": {"id": "owned-action"}}},
        }
    )
    old_digest = sha256(facet).hexdigest()
    for name, content in ((CONTRACT, facet), ("pdf-domain/schema/pdf_products", payload)):
        conn.execute(
            text("INSERT INTO sem.input VALUES ('retained','dependency',:name,:body,:digest)"),
            {
                "name": name,
                "body": b"changed input" if changed_input and name != CONTRACT else content,
                "digest": sha256(content).hexdigest(),
            },
        )
    support = {
        "capabilities": {"preparation": "pdf-native"},
        "assets": [
            {
                "reference": CONTRACT,
                "contract": "pdf-native/helper-bindings",
                "role": "native-pdf-helper-bindings",
                "content_digest": old_digest,
            }
        ],
    }
    conn.execute(
        text("INSERT INTO sem.data_operation_definition VALUES ('retained',CAST(:body AS jsonb))"),
        {"body": canonical_bytes(support).decode()},
    )
    current = SourceArtifact(
        CONTRACT, facet if current_contract else canonical_bytes({"current": "different contract"})
    )
    execute_native_sql(conn, pdf_domain_native_sql(sources=(current,)))
    return old_digest


def test_forward_relower_keeps_retained_contract_and_fresh_admission_refuses_it(
    semantic_bare_engine,
):
    with semantic_bare_engine.begin() as conn:
        old_digest = _fixture(conn)
        conn.execute(text("SELECT sem.admit_pdf_operation_contracts('retained',false)"))
        assert conn.execute(
            text("SELECT operation_id,contract_id,contract_digest FROM sem.pdf_operation_contract")
        ).all() == [("owned-action", "owned-action", old_digest)]
        with pytest.raises(DBAPIError, match="PDF domain contract differs"), conn.begin_nested():
            conn.execute(text("SELECT sem.admit_pdf_operation_contracts('retained',true)"))


def test_forward_relower_refuses_changed_retained_input_atomically(semantic_bare_engine):
    with semantic_bare_engine.begin() as conn:
        _fixture(conn, changed_input=True)
        with pytest.raises(DBAPIError, match="PDF domain input differs"), conn.begin_nested():
            conn.execute(text("SELECT sem.admit_pdf_operation_contracts('retained',false)"))
        assert conn.scalar(text("SELECT count(*) FROM sem.pdf_operation_contract")) == 0


def test_current_contract_reads_only_its_authenticated_named_input(semantic_bare_engine):
    read = text("SELECT ops.pdf_contract_input('retained', 'schema/pdf_products')")
    with semantic_bare_engine.begin() as conn:
        _fixture(conn, current_contract=True)
        conn.execute(text("SELECT sem.admit_pdf_operation_contracts('retained',true)"))
        assert conn.scalar(read) == b"authenticated retained input"
        conn.execute(
            text(
                "UPDATE sem.input SET content_digest = repeat('0', 64) "
                "WHERE input_name = 'pdf-domain/schema/pdf_products'"
            )
        )
        with pytest.raises(DBAPIError) as refusal, conn.begin_nested():
            conn.scalar(read)
        assert getattr(refusal.value.orig, "sqlstate", None) == "P0002"
