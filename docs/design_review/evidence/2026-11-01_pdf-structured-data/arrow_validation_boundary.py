"""Bounded installed-library checks; no database or production changes."""
import importlib.metadata as metadata
import pyarrow as pa

print({name:metadata.version(name) for name in ['pyarrow','pydantic','pydantic-settings']})
schema=pa.schema([pa.field('x',pa.int64(),nullable=False),pa.field('nested',pa.struct([pa.field('word',pa.string(),nullable=False)]),nullable=False)])
batch=pa.RecordBatch.from_pylist([{'x':None,'nested':{'word':None}}],schema=schema)
batch.validate(full=True)
print('full validation accepts null despite nonnullable schema',batch.to_pylist())
domain_schema=pa.schema([pa.field('confidence',pa.float64(),metadata={b'jsonschema':b'{"minimum":0,"maximum":1}'})])
invalid_domain=pa.RecordBatch.from_pylist([{'confidence':2.0}],schema=domain_schema)
invalid_domain.validate(full=True)
print('full validation does not enforce domain metadata',invalid_domain.to_pylist())
schema2=pa.schema([pa.field('text',pa.string(),metadata={b'role':b'ocr'}),pa.field('value',pa.float64())],metadata={b'profile':b'v1'})
batch2=pa.RecordBatch.from_pylist([{'text':'a\0b','value':-0.0}],schema=schema2)
sink=pa.BufferOutputStream()
with pa.ipc.new_stream(sink,schema2,options=pa.ipc.IpcWriteOptions(compression='zstd')) as writer:
    writer.write_batch(batch2)
reader=pa.ipc.open_stream(sink.getvalue());restored=reader.read_next_batch()
print('schema metadata exact',reader.schema.equals(schema2,check_metadata=True),'text',repr(restored[0][0].as_py()),'float',restored[1][0].as_py().hex())
print('batch validate doc',pa.RecordBatch.validate.__doc__)
