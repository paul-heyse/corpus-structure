"""Actual semantic CLI source selection, automated routing and protected lifecycle controls."""
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import json
import pytest
from sqlalchemy import select,update,func
from sqlalchemy.exc import DBAPIError
from typer.testing import CliRunner
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding,create_run,record_method,create_task,seal_cut,register_document
from .test_operations import setup



def test_actual_cli_source_scope_agent_unknown_limit_and_cancel(semantic_db_engine,semantic_writer_engine,tmp_path,monkeypatch):
    from corpus_structure.cli import orchestrate as cli
    from corpus_structure.cli.app import app
    from corpus_structure.ingest.methods import METHODS
    from corpus_structure.methods.math.methods import METHODS as MATH
    from corpus_structure.methods.llm.agent_opus import AgentOpus
    from corpus_structure.orchestrate.registry import MethodRegistry,MethodsFile
    from corpus_structure.orchestrate.phase0 import PHASE0
    from corpus_structure.semantic import SourceArtifact,SourceBundle,ResolvedDependencies,PreparationProfile,prepare_release
    from corpus_structure.semantic.observations import observation_inputs
    from corpus_structure.semantic.proposals import proposal_inputs
    from corpus_structure.semantic.releases import persist_release
    from corpus_structure.semantic.domain_operations import domain_rule_inputs
    from corpus_structure.semantic.analytical_profile import analytical_inputs
    core=Path(__file__).parents[2]/'src/corpus_structure/model/semantic/core.yaml'
    bundle=SourceBundle('core',(SourceArtifact('core',core.read_bytes()),))
    deps=domain_rule_inputs(ResolvedDependencies(),b'rules: []')
    bundle=observation_inputs(proposal_inputs(bundle,deps));bundle,deps=analytical_inputs(bundle,deps)
    prepared=prepare_release(bundle,deps)
    with semantic_db_engine.begin() as conn:persist_release(conn,bundle,deps,PreparationProfile(),prepared)
    corpus=tmp_path/'corpus';(corpus/'toy').mkdir(parents=True)
    (corpus/'toy'/'input.html').write_text('<p>Unknown first sentence.</p><p>Unknown second sentence.</p>')
    (corpus/'toy'/'excluded.html').write_text('<p>Excluded.</p>')
    (corpus/'index.tsv').write_text('path\tfirst_pass\ninput.html\tyes\nexcluded.html\tno\n')
    sources=tmp_path/'sources';sources.mkdir()
    (sources/'test.yaml').write_text("version: '1'\nroot: toy\nindex: {file: index.tsv, page: path}\napplies_to: 'toy/*.html'\n")
    pack=tmp_path/'test';pack.mkdir();(pack/'guideline.md').write_text('Use only explicit source evidence.')
    (pack/'slices.yaml').write_text('slices:\n first-pass: [{index: first_pass}]\n scope: [input.html]\n')
    (pack/'policies.yaml').write_text('''version: '1'
chains:
 propose:
 - key: explicit-unknown
   when: "unit.claim_bearing == null"
   do: {method: agent.opus/extract, limit: 1, then: continue}
 - key: duplicate
   when: "true"
   do: {method: agent.opus/extract, then: stop}
''')
    registry=MethodRegistry((*METHODS,*MATH,AgentOpus()),MethodsFile(sections={'math':{'macros':{},'constants':[]},'binders':{'sentence_initial':['let'],'clause':[],'reopen':[],'section_wide':[]}},configs={'ingest.html':{'default':{'source_profile':'test'}},'segment.sentences':{'default':{}},'profile.segments':{'default':{}},'agent.opus':{'extract':{}}}),sources=sources)
    e=semantic_writer_engine
    @contextmanager
    def engine(_,**kwargs):yield e
    monkeypatch.setattr(cli,'ENGINE',engine)
    monkeypatch.setattr(cli,'PHASE0',lambda:{'registry_for':lambda _:registry,'domains':tmp_path,'graph':PHASE0})
    runner=CliRunner()
    initialized=runner.invoke(app,['project','init','--domain','test','--corpus',str(corpus),'--name','native','--semantic-release',prepared.release_id,'--realization','input','--json'])
    assert initialized.exit_code==0,(initialized.output,initialized.exception)
    result=runner.invoke(app,['run','--semantic-release',prepared.release_id,'--realization','input','--project','native','--domain','test','--scope','scope','--agent-mode','complete','--json'])
    assert result.exit_code==0,(result.output,result.exception)
    report=json.loads(result.stdout);run=report['run_id'];assert report['status']=='awaiting_agent'
    with e.connect() as conn:
        docs=conn.execute(select(table('ops.run').c.options).where(table('ops.run').c.id==run)).scalar_one()['corpus']['documents']
        assert len(docs)==1
        tasks=conn.execute(select(table('ops.task')).where(table('ops.task').c.run_id==run,table('ops.task').c.stage=='propose').order_by(table('ops.task').c.id)).mappings().all()
        assert len(tasks)==2
        assert [task['status'] for task in tasks]==['awaiting_agent','skipped']
        assert tasks[1]['reason']=='limit'
        assert all(task['trigger']['values']['unit.claim_bearing'] is None for task in tasks)
        assert all(task['trigger']['rule_key']=='explicit-unknown' for task in tasks)
    listed=runner.invoke(app,['tasks',str(run),'--semantic','--limit','0','--json'])
    assert listed.exit_code==0,(listed.output,listed.exception)
    assert json.loads(listed.stdout)['total']==7 and json.loads(listed.stdout)['tasks']==[]
    status=runner.invoke(app,['status',str(run),'--semantic','--json'])
    assert status.exit_code==0,(status.output,status.exception)
    assert json.loads(status.stdout)['progress']['run']['status']=='awaiting_agent'
    refused=runner.invoke(app,['run','finalize',str(run),'--output-realization','evaluated','--json'])
    assert refused.exit_code==1 and 'automated tasks are still open' in refused.output
    cancelled=runner.invoke(app,['run','cancel',str(run),'--semantic','--json'])
    assert cancelled.exit_code==0,(cancelled.output,cancelled.exception)
    assert json.loads(cancelled.stdout)['tasks_cancelled']==1


def test_cli_finalization_returns_real_receipt_and_exact_replay(semantic_db_engine,semantic_writer_engine,tmp_path,monkeypatch):
    from .test_domain_operations import fixture
    from corpus_structure.cli import orchestrate as cli
    from corpus_structure.cli.app import app
    _,run,_=fixture(semantic_db_engine,semantic_writer_engine,tmp_path/'source.html')
    @contextmanager
    def engine(_,**kwargs):yield semantic_writer_engine
    monkeypatch.setattr(cli,'ENGINE',engine)
    runner=CliRunner()
    result=runner.invoke(app,['run','finalize',str(run),'--output-realization','evaluated','--json'])
    assert result.exit_code==0,(result.output,result.exception)
    first=json.loads(result.stdout)
    assert first['run_id']==run and first['realization_id']=='evaluated' and first['receipt']['data_revision']==1
    replay=runner.invoke(app,['run','finalize',str(run),'--output-realization','evaluated','--json'])
    assert replay.exit_code==0,(replay.output,replay.exception)
    assert json.loads(replay.stdout)==first
