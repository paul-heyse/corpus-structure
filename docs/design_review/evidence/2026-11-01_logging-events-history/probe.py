"""Bounded library boundary investigation; synthetic expectations, no product implementation."""
from __future__ import annotations
import copy, inspect, io, json, logging, platform
from importlib.metadata import version
from pathlib import Path
import structlog, logbook, eliot
from eliot.testing import MemoryLogger
from eliot.parse import Parser
from loguru import logger as loguru

ROOT=Path(__file__).parent
results={"python":platform.python_version(),"versions":{p:version(p) for p in ('structlog','loguru','Logbook','eliot')},"checks":{}}
def check(name, condition, detail=None):
    results['checks'][name]={'outcome':'passed' if condition else 'failed','detail':detail}
    assert condition, (name,detail)

# Producer processing; raw exception info consumed before safe retained branches.
def normalize(logger, method, event):
    event=copy.deepcopy(event)
    event.pop('authorization',None)
    event.setdefault('occurrence_id','synthetic-native')
    return event
exception_processor=structlog.processors.ExceptionRenderer(structlog.tracebacks.ExceptionDictTransformer(show_locals=False))
shared=[structlog.contextvars.merge_contextvars,structlog.stdlib.add_log_level]
structlog.configure(processors=shared+[exception_processor,normalize,structlog.stdlib.ProcessorFormatter.wrap_for_formatter],logger_factory=structlog.stdlib.LoggerFactory(),wrapper_class=structlog.stdlib.BoundLogger,cache_logger_on_first_use=False)
streams=[io.StringIO(),io.StringIO()]
base=logging.getLogger('synthetic');base.setLevel(logging.DEBUG);base.propagate=False;base.handlers=[]
def branch_mutate(logger,method,event):
    event['nested']['branch']='mutated'
    return event
for i,stream in enumerate(streams):
    handler=logging.StreamHandler(stream)
    handler.setFormatter(structlog.stdlib.ProcessorFormatter(foreign_pre_chain=shared+[structlog.stdlib.ExtraAdder(),exception_processor,normalize],processors=[lambda l,m,e:copy.deepcopy(e),structlog.stdlib.ProcessorFormatter.remove_processors_meta]+([branch_mutate] if i==0 else [])+[structlog.processors.JSONRenderer()]))
    base.addHandler(handler)
with structlog.contextvars.bound_contextvars(operation_id='operation-a'):
    structlog.get_logger('synthetic').info('finished',nested={'count':2},authorization='synthetic-secret')
    base.warning('foreign %s','warning',extra={'occurrence_id':'foreign-1','nested':{'count':3}})
    try:
        secret_local='synthetic-secret-local'
        raise ExceptionGroup('synthetic group',[ValueError('safe reason')])
    except ExceptionGroup:
        structlog.get_logger('synthetic').exception('unexpected',nested={'count':4})
records=[[json.loads(line) for line in s.getvalue().splitlines()] for s in streams]
check('field_fidelity',records[1][0]['nested']=={'count':2} and records[1][0]['operation_id']=='operation-a')
check('branch_detachment',records[0][0]['nested']['branch']=='mutated' and 'branch' not in records[1][0]['nested'])
check('foreign_fields',records[1][1]['occurrence_id']=='foreign-1' and records[1][1]['event']=='foreign warning')
check('structured_exception_group',bool(records[1][2]['exception']) and 'synthetic-secret-local' not in streams[1].getvalue())
check('safe_fields_all_destinations',all('synthetic-secret' not in s.getvalue() for s in streams))
check('context_reset',structlog.contextvars.get_contextvars()=={})
(ROOT/'raw'/'branches.json').write_text(json.dumps(records,indent=2))

# Loguru supports structured extras, but stdlib bridge and its singleton add responsibilities.
loguru.remove(); seen=[]
sid=loguru.add(lambda message:seen.append(copy.deepcopy(message.record['extra'])),format='{message}',diagnose=False,enqueue=False)
loguru.bind(occurrence_id='loguru-1',nested={'count':2}).info('finished')
loguru.remove(sid)
check('loguru_structured_extra',seen==[{'occurrence_id':'loguru-1','nested':{'count':2}}])

# Native FCH: isolated operation buffers, bounded records, reset/release semantics.
def rec(oid,level=logbook.DEBUG):
    return logbook.LogRecord('synthetic',level,'safe',extra={'occurrence_id':oid})
a_sink=logbook.TestHandler();b_sink=logbook.TestHandler()
a=logbook.FingersCrossedHandler(a_sink,buffer_size=3,reset=False,pull_information=False)
b=logbook.FingersCrossedHandler(b_sink,buffer_size=3,reset=False,pull_information=False)
for i in range(5):a.handle(rec(f'a{i}'));b.handle(rec(f'b{i}'))
check('fch_no_capacity_release',not a_sink.records and not b_sink.records)
a.handle(rec('a-error',logbook.ERROR))
a_ids=[r.extra['occurrence_id'] for r in a_sink.records]
check('fch_count_bound_original_ids',a_ids==['a3','a4','a-error'],a_ids)
check('fch_scope_isolation',not b_sink.records)
a.handle(rec('a-after'))
check('fch_post_trigger_passes',a_sink.records[-1].extra['occurrence_id']=='a-after')
b.close();check('fch_success_close_does_not_release',not b_sink.records)
reset_sink=logbook.TestHandler();reset=logbook.FingersCrossedHandler(reset_sink,buffer_size=3,reset=True,pull_information=False)
reset.handle(rec('r-debug'));reset.handle(rec('r-error',logbook.ERROR));reset.handle(rec('r-after'))
check('fch_reset_rebuffers',not reset.triggered and len(reset_sink.records)==2 and len(reset.buffered_records)==1)
a.close();reset.close()

# Native Eliot parser, real emitted records, independent expectations.
memory=MemoryLogger()
with eliot.start_action(logger=memory,action_type='root'):
    try:
        with eliot.start_action(logger=memory,action_type='attempt-failed'):
            raise ValueError('safe failed attempt')
    except ValueError:
        pass
    with eliot.start_action(logger=memory,action_type='recovery'):
        pass
messages=copy.deepcopy(memory.messages)
# Do not infer application outcome from a normal return/action succeeded.
complete=list(Parser.parse_stream(reversed(messages)))
check('eliot_out_of_order_complete',len(complete)==1 and complete[0].is_complete())
missing_terminal=[m for m in messages if not (m.get('action_type')=='root' and m.get('action_status')=='succeeded')]
partial=list(Parser.parse_stream(missing_terminal))
check('eliot_missing_terminal_incomplete',len(partial)==1 and not partial[0].is_complete())
missing_child=[m for m in messages if m is not None and not (m.get('action_type')=='attempt-failed' and m.get('action_status')=='started')]
partial_child=list(Parser.parse_stream(missing_child))
check('eliot_missing_child_start_incomplete',len(partial_child)==1 and not partial_child[0].is_complete())
check('eliot_failed_attempt_preserved',any(m.get('action_type')=='attempt-failed' and m.get('action_status')=='failed' for m in messages))
check('eliot_tree_action_names',{c.action_type for c in complete[0].root().children}=={'attempt-failed','recovery'})
# A second contributor remains data rather than a second native tree parent.
fanin_memory=MemoryLogger()
with eliot.start_action(logger=fanin_memory,action_type='fan-in-root'):
    with eliot.start_action(logger=fanin_memory,action_type='join'):
        eliot.Message.new(message_type='dependencies',contributors=['producer-a','producer-b']).write(logger=fanin_memory)
fanin_tree=list(Parser.parse_stream(reversed(fanin_memory.messages)))[0]
join=next(c for c in fanin_tree.root().children if c.action_type=='join')
check('eliot_fanin_metadata_not_parents',join.children[0].contents['contributors']==['producer-a','producer-b'])
refusal_memory=MemoryLogger()
with eliot.start_action(logger=refusal_memory,action_type='deliberate-refusal'):
    refusal_result={'outcome':'refused'}
check('eliot_normal_return_not_domain_success',refusal_result['outcome']=='refused' and refusal_memory.messages[-1]['action_status']=='succeeded')
(ROOT/'raw'/'fanin-refusal.json').write_text(json.dumps({'fanin':fanin_memory.messages,'refusal':refusal_memory.messages},indent=2))
(ROOT/'raw'/'eliot-history.json').write_text(json.dumps({'messages':messages,'missing_terminal':missing_terminal,'missing_child':missing_child},indent=2))
# Capture installed exact source rather than relying on older stable documentation.
(ROOT/'raw'/'native-sources.txt').write_text('\n'.join(inspect.getsource(x) for x in [logbook.FingersCrossedHandler,Parser.parse_stream,eliot.parse.Task.is_complete]))
(ROOT/'raw'/'results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
