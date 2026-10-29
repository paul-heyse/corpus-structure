"""C2 queries against a production C1 materialization of independent authored fixtures."""
from __future__ import annotations
import pytest
from sqlalchemy import text
from .test_consolidate_pass import pool_run as _pool_fixture, seal

pool_run = _pool_fixture
from corpus_structure.consolidate import run_pass
from corpus_structure.serve.journey import serve_query, QueryRefused
from corpus_structure.serve.queries import GENERIC
from corpus_structure.serve.registry import build_registry
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.serve.explain import explain

@pytest.fixture
def ready(pool_run):
    seal(pool_run)
    with pool_run.engine.begin() as conn:
        run_pass(conn,pool_run.run,'finalize',pool_run.m19)
        conn.execute(text("UPDATE ops.run SET status='finished',finished_at=now() WHERE id=:r"),{'r':pool_run.run})
    return pool_run

def test_c1_trace_generic_and_pack_questions(ready):
    reg=build_registry(GENERIC,DOMAINS/'statistics')
    with ready.engine.connect() as conn:
        def ask(name,**params):return serve_query(conn,reg,name,params,run=ready.run)
        all_=ask('claims')
        assert all_.rows
        assert all(r['status']=='accepted' for r in all_.rows)
        assert all(r['premise'] for r in all_.rows if r['modality']=='supposed')
        profile=ask('family_profile',family='normal')
        assert profile.rows
        assert len([r for r in profile.rows if r['predicate']=='stat:identical_parameter'])==2
        assert ask('statement',locator='special/Normal.html#rel1').rows
        key=all_.rows[0]['key']
        assert ask('evidence',key=key).rows
        entity=ask('entity',label='normal')
        assert any(r['type']=='stat:DistributionFamily' for r in entity.rows)
        trans=ask('transformations_of',family='normal')
        assert trans.rows and all(r['definiens'] for r in trans.rows)
        assert ask('find',text='normally distributed').rows
        detail=explain(conn,ready.run,'claim',key)
        assert detail.detail.m19_task_id==ready.m19
        assert detail.detail.supports
        assert detail.detail.claim.key==key

def test_keyset_pagination_matches_unpaged_logical_rows(ready):
    reg=build_registry(GENERIC,DOMAINS/'statistics')
    with ready.engine.connect() as conn:
        full=serve_query(conn,reg,'claims',run=ready.run)
        page=serve_query(conn,reg,'claims',run=ready.run,max_rows=2)
        found=list(page.rows)
        while page.next_page_token:
            page=serve_query(conn,reg,'claims',page_token=page.next_page_token,max_rows=2)
            found+=page.rows
        assert found==full.rows
        with pytest.raises(QueryRefused,match='size limit'):
            serve_query(conn,reg,'claims',run=ready.run,max_chars=100)
