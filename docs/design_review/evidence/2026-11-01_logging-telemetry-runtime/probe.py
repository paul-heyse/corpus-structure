"""Bounded isolated telemetry qualification; run via run_probes.py."""
import importlib.metadata as md
import inspect
import io
import json
import logging
import pathlib
import sys
import time

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, BatchSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.exporter.otlp.json.file import FileSpanExporter, FileMetricExporter
from opentelemetry.exporter.otlp.json.file._log_exporter import FileLogExporter

OUT = pathlib.Path(sys.argv[2])
case = sys.argv[1]

def read(name):
    return [json.loads(x) for x in (OUT / name).read_text().splitlines()]

if case == 'direct':
    from opentelemetry.sdk._logs import LoggerProvider
    from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor
    from opentelemetry.instrumentation.logging.handler import LoggingHandler
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

    tp = TracerProvider(shutdown_on_exit=False)
    tp.add_span_processor(SimpleSpanProcessor(FileSpanExporter(OUT/'spans.jsonl')))
    trace.set_tracer_provider(tp)
    lp = LoggerProvider(shutdown_on_exit=False)
    lp.add_log_record_processor(SimpleLogRecordProcessor(FileLogExporter(OUT/'logs.jsonl')))
    handler = LoggingHandler(logger_provider=lp)
    logger = logging.getLogger('probe.foreign'); logger.setLevel(logging.INFO); logger.addHandler(handler)
    reader = PeriodicExportingMetricReader(FileMetricExporter(OUT/'metrics.jsonl'), export_interval_millis=float('inf'))
    mp = MeterProvider(metric_readers=[reader], shutdown_on_exit=False)
    meter = mp.get_meter('probe'); count = meter.create_counter('probe.completed', unit='{operation}')
    with tp.get_tracer('probe').start_as_current_span('parent') as parent:
        for i in range(2):
            with tp.get_tracer('probe').start_as_current_span('invocation', attributes={'attempt':i}):
                logger.info('safe event',extra={'occurrence_id':f'event-{i}','safe_count':3})
                count.add(1, {'operation':'probe'})
    assert tp.force_flush(); assert lp.force_flush(); assert mp.force_flush()
    logger.removeHandler(handler); handler.close(); lp.shutdown(); mp.shutdown(); tp.shutdown()
    data={n:read(n+'.jsonl') for n in ['spans','logs','metrics']}
    spans=[s for x in data['spans'] for r in x['resourceSpans'] for scope in r['scopeSpans'] for s in scope['spans']]
    assert len(spans)==3
    assert len({s['traceId'] for s in spans})==1
    logs=[r for x in data['logs'] for resource in x['resourceLogs'] for scope in resource['scopeLogs'] for r in scope['logRecords']]
    assert len(logs)==2 and all(r['traceId']==spans[0]['traceId'] for r in logs)
    metrics=[m for x in data['metrics'] for r in x['resourceMetrics'] for scope in r['scopeMetrics'] for m in scope['metrics']]
    assert metrics and metrics[0]['sum']['dataPoints'][0]['asInt']=='2'
    stream=io.StringIO(); exporter=FileSpanExporter(stream=stream);exporter.shutdown(); assert not stream.closed
    print(json.dumps({'outcome':'passed','spans':len(spans),'logs':len(logs),'metric_total':2,'borrowed_stream_closed':stream.closed}))

elif case == 'logfire':
    import logfire
    host=TracerProvider(shutdown_on_exit=False)
    host.add_span_processor(SimpleSpanProcessor(FileSpanExporter(OUT/'host-spans.jsonl')))
    trace.set_tracer_provider(host)
    local=logfire.configure(local=True,send_to_logfire=False,console=False,metrics=False,inspect_arguments=False,
        additional_span_processors=[SimpleSpanProcessor(FileSpanExporter(OUT/'logfire-spans.jsonl'))])
    assert trace.get_tracer_provider() is host
    for i in range(2):
        with local.span('local invocation', invocation=i):
            local.info('safe event', occurrence_id=f'local-{i}')
    with trace.get_tracer('native.consumer').start_as_current_span('native operation'):pass
    assert local.force_flush()
    assert local.shutdown()
    with host.get_tracer('probe').start_as_current_span('host survives'):pass
    host.shutdown()
    rows=read('logfire-spans.jsonl'); spans=[s for x in rows for r in x['resourceSpans'] for scope in r['scopeSpans'] for s in scope['spans']]
    names=[s['name'] for s in spans]
    assert names.count('local invocation')==2 and names.count('safe event')==2
    assert 'native operation' not in names
    print(json.dumps({'outcome':'passed','local_names':names,'host_unchanged':True,'native_consumer_uses_host':True}))

elif case in ('pydantic', 'pydantic_global'):
    import logfire
    from pydantic import BaseModel, ValidationError
    class Before(BaseModel):value:int
    local=logfire.configure(local=case!='pydantic_global',send_to_logfire=False,console=False,metrics=False,inspect_arguments=False,
        additional_span_processors=[SimpleSpanProcessor(FileSpanExporter(OUT/'validation-spans.jsonl'))])
    local.instrument_pydantic(record='failure')
    class After(BaseModel):value:int
    for cls in (Before,After):
        try:cls(value='invalid')
        except ValidationError:pass
    local.shutdown()
    spans=[s for x in read('validation-spans.jsonl') for r in x['resourceSpans'] for scope in r['scopeSpans'] for s in scope['spans']]
    if case=='pydantic_global':
        assert spans and any('After' in json.dumps(s) for s in spans)
        assert not any('Before' in json.dumps(s) for s in spans)
    else:
        assert not spans, 'Pinned plugin uses GLOBAL_CONFIG, not the selected local instance'
    print(json.dumps({'outcome':'passed','configuration':case,'before_instrumented':False,'after_instrumented':bool(spans),'spans':len(spans)}))

elif case == 'flush_deadline':
    class Slow(SpanExporter):
        def export(self, spans):time.sleep(.25);return SpanExportResult.SUCCESS
    provider=TracerProvider(shutdown_on_exit=False)
    provider.add_span_processor(BatchSpanProcessor(Slow(),schedule_delay_millis=60000))
    with provider.get_tracer('probe').start_as_current_span('bounded-synthetic'):pass
    start=time.monotonic(); result=provider.force_flush(timeout_millis=10);elapsed=time.monotonic()-start
    provider.shutdown()
    assert elapsed>.2
    print(json.dumps({'outcome':'passed','question':'does force_flush timeout preempt exporter','preempts':False,'requested_timeout_ms':10,'elapsed_seconds':elapsed,'returned':result}))

elif case == 'http_timeout':
    import socket, threading
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    sock=socket.socket(); sock.bind(('127.0.0.1',0));sock.listen();port=sock.getsockname()[1]
    def stall():
        conn,_=sock.accept()
        with conn:time.sleep(.5)
        sock.close()
    thread=threading.Thread(target=stall);thread.start()
    exporter=OTLPSpanExporter(endpoint=f'http://127.0.0.1:{port}/v1/traces',timeout=.1)
    start=time.monotonic();result=exporter.export([]); elapsed=time.monotonic()-start
    exporter.shutdown(); thread.join(1)
    assert result is SpanExportResult.FAILURE and elapsed<.5
    print(json.dumps({'outcome':'passed','export_result':result.name,'configured_timeout_seconds':.1,'elapsed_seconds':elapsed}))

elif case == 'api':
    import logfire
    from logfire.query_client import LogfireQueryClient
    from opentelemetry.instrumentation.logging.handler import LoggingHandler
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    modules=[FileSpanExporter,FileMetricExporter,FileLogExporter,LoggingHandler,LogfireQueryClient]
    print(json.dumps({'versions':{n:md.version(n) for n in ['opentelemetry-api','opentelemetry-sdk','opentelemetry-exporter-otlp-json-file','opentelemetry-instrumentation-logging','logfire','logfire-sdk','pydantic','sqlalchemy']},'signatures':{f'{c.__module__}.{c.__name__}':str(inspect.signature(c)) for c in modules},'query_methods':{n:str(inspect.signature(getattr(LogfireQueryClient,n))) for n in ['query_json_rows','query_arrow','query_csv','info']},'logfire_shutdown':str(inspect.signature(logfire.shutdown))},indent=2))
