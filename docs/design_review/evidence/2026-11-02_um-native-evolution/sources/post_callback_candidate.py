from sqlalchemy import create_engine, text
from corpus_structure.semantic.migrations import current_revision,upgrade
from corpus_structure.semantic.native_candidate import prepare_series_candidate

engine=create_engine('postgresql+psycopg:///cs_sem_pdf68_author_20261101_44132f1db0?host=/var/run/postgresql&port=5434')
with engine.connect() as conn:
    transaction=conn.begin()
    try:
        provenance=conn.execute(text("SELECT oid,pg_get_userbyid(datdba),shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()")).one()
        assert provenance[0]==14010645 and provenance[1]=='paul' and '1dbfc2773c354652b64626aaa56eac35' in provenance[2]
        assert current_revision(conn)=='semantic_pdf_retire_20261101'
        upgrade(conn,'semantic_pdf_support_20261102')
        candidate,authoring=prepare_series_candidate(conn,owned_authoring=True)
        assert candidate.upgrade_ops is not None
        assert not candidate.upgrade_ops.ops,candidate.upgrade_ops.ops
        assert len(authoring.desired)==61
        assert conn.scalar(text('SELECT current_user'))=='paul'
        print('PASSED exact native/ordinary candidate unchanged after Python optional-support fix;61desired/head87')
    finally:
        transaction.rollback()
    assert current_revision(conn)=='semantic_pdf_retire_20261101'
    print('PASSED outer rollback restores82; no target deployment')
engine.dispose()
