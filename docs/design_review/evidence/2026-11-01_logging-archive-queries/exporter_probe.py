"""Native exporter stream/rotation boundary, no production archive service."""
import importlib.metadata as metadata
import json
from pathlib import Path
import tempfile
from opentelemetry.exporter.otlp.json.file.trace_exporter import FileSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor


def main():
    results={'exporter':metadata.version('opentelemetry-exporter-otlp-json-file'),'sdk':metadata.version('opentelemetry-sdk')}
    with tempfile.TemporaryDirectory(prefix='logging-native-rotation-') as temp:
        root=Path(temp)
        old=(root/'old.jsonl').open('w')
        exporter=FileSpanExporter(stream=old)
        provider=TracerProvider(shutdown_on_exit=False)
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        tracer=provider.get_tracer('native-rotation')
        with tracer.start_as_current_span('first'):pass
        current=(root/'new.jsonl').open('w')
        with tracer.start_as_current_span('second'):pass
        provider.shutdown()
        assert not old.closed
        current.flush()
        assert len((root/'old.jsonl').read_text().splitlines()) == 2
        assert (root/'new.jsonl').read_text() == ''
        old.close();current.close()
        results['supplied_stream_caller_owned']=True
        results['replacing_other_stream_does_not_rotate_exporter']=True
        # Stable stream object is the necessary narrow adapter, not a new exporter.
        class Segmented:
            def __init__(self):self.paths=[];self.handle=None;self.closed=False
            def write(self,data):
                if self.handle:self.handle.close()
                path=root/f'segment-{len(self.paths)}.jsonl';self.paths.append(path)
                self.handle=path.open('w');return self.handle.write(data)
            def flush(self):self.handle.flush()
            def close(self):
                if self.handle:self.handle.close()
                self.closed=True
        stream=Segmented()
        provider=TracerProvider(shutdown_on_exit=False)
        provider.add_span_processor(SimpleSpanProcessor(FileSpanExporter(stream=stream)))
        tracer=provider.get_tracer('native-rotation')
        for name in ('left','right'):
            with tracer.start_as_current_span(name):pass
        provider.shutdown();stream.close()
        docs=[json.loads(p.read_text()) for p in stream.paths]
        names=[d['resourceSpans'][0]['scopeSpans'][0]['spans'][0]['name'] for d in docs]
        assert names==['left','right'],names
        results['stable_stream_adapter_rotates_native_export_batches']=True
        results['outcome']='passed'
        print(json.dumps(results,indent=2))

if __name__=='__main__':main()
