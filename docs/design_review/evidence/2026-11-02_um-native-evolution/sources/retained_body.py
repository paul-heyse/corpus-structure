import json
from hashlib import sha256
from pathlib import Path

from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.sql import visitors
from sqlalchemy.sql.elements import ColumnClause

from corpus_structure.semantic.migrations import current_revision
from corpus_structure.semantic.native_objects import native_owner
from corpus_structure.semantic.native_sql_body import published_validation_statement

pin = dict(task=10, key='integrated', digest='d3482c7126a5db75d8bb1962bb34cabd1b8f772bc136cd3f5987744dfec7bce0')
statement = published_validation_statement()
def bind(node):
    if isinstance(node, ColumnClause) and node.is_literal and node.name in {'p_task','p_key','p_digest'}:
        return bindparam(node.name[2:], type_=node.type)
statement = visitors.replacement_traverse(statement, {}, bind)
source = str(statement)
assert 'pdf_validation_contract' not in source
engine=create_engine('postgresql+psycg:///unused') if False else create_engine('postgresql+psycopg:///corpus_pdf_20261101?host=/var/run/postgresql&port=5434')
with engine.connect() as conn:
    with conn.begin():
        conn.exec_driver_sql('SET TRANSACTION READ ONLY')
        revision=current_revision(conn)
        assert revision=='semantic_pdf_retire_20261101',revision
        with native_owner(conn,'corpus_sem_publisher'):
            publication=conn.execute(text('SELECT build_id,release_id,frozen_digest FROM ops.pdf_published_revision WHERE task_id=:task AND product_key=:key AND logical_digest=:digest'),pin).mappings().one()
            product=conn.execute(text('SELECT content_digest,contract_digest FROM ops.pdf_product WHERE task_id=:task AND product_key=:key'),pin).mappings().one()
            expected=conn.execute(text('SELECT build_id,frozen_digest,logical_digest,contract_digest,native_contract_digest,native_callbacks FROM ops.pdf_build_validation WHERE build_id=:build AND frozen_digest=:frozen AND contract_digest=:contract'),dict(build=publication['build_id'],frozen=publication['frozen_digest'],contract=product['contract_digest'])).mappings().one()
            old_epoch=conn.scalar(text('SELECT ops.pdf_validation_contract(:release)'),dict(release=publication['release_id']))
            actual=conn.execute(statement,pin).mappings().one()
            assert dict(actual)==dict(expected)
            assert actual['logical_digest']==pin['digest']==product['content_digest']
            assert actual['contract_digest']==product['contract_digest']
            assert actual['native_contract_digest']==old_epoch and actual['native_callbacks'] is True
            assert conn.execute(statement,pin|dict(digest='0'*64)).all()==[]
            outcome=dict(outcome='passed',kind='exact-current-Core-body-on-retained-data; not deployed helper',pin=pin,revision=revision,release=publication['release_id'],receipt=dict(actual),installed_original_native_contract=old_epoch,query_sha256=sha256(source.encode()).hexdigest(),read_only=conn.scalar(text("SELECT current_setting('transaction_read_only')")))
        assert outcome['read_only']=='on'
        assert current_revision(conn)==revision
        assert conn.scalar(text('SELECT current_user'))=='paul'
Path('build/um87-retained-validation-body.json').write_text(json.dumps(outcome,sort_keys=True,indent=2)+'\n')
print(json.dumps(outcome,sort_keys=True))
engine.dispose()
