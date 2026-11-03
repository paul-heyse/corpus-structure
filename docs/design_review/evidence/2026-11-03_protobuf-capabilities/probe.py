"""Bounded generator and wire-semantic experiments; no product services or data."""
from __future__ import annotations
import importlib.metadata as md
import json
from pathlib import Path
import subprocess
import sys
from google.protobuf import descriptor_pb2, descriptor_pool, json_format, message_factory
from linkml.generators.protogen import ProtoGenerator

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'raw'

def command(args):
    p = subprocess.run(args, capture_output=True, text=True, check=False)
    return {'command': args, 'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}

def main():
    results = {'versions': {k: md.version(k) for k in ['linkml','protobuf','grpcio','pydantic']}, 'commands': [], 'observations': {}}
    base = '''id: https://example.org/probe
name: probe
prefixes:
  probe: https://example.org/probe/
  xsd: http://www.w3.org/2001/XMLSchema#
default_prefix: probe
types:
  integer:
    base: int
    uri: xsd:integer
  string:
    base: str
    uri: xsd:string
  decimal:
    base: Decimal
    uri: xsd:decimal
classes:
  Record:
    attributes:
'''
    fields = {'count':'      count:\n        range: integer\n        required: true\n', 'label':'      label:\n        range: string\n', 'amount':'      amount:\n        range: decimal\n'}
    for variant, order, members in [('v1',['count','label','amount'],['ACCEPT','REFUSE']),('v2',['label','count','amount'],['REFUSE','ACCEPT'])]:
        directory = RAW / variant
        directory.mkdir(exist_ok=True)
        schema = base + ''.join(fields[k] for k in order) + 'enums:\n  Choice:\n    permissible_values:\n' + ''.join('      '+k+': {}\n' for k in members)
        source = directory / 'probe.yaml'
        source.write_text(schema)
        proto = ProtoGenerator(str(source)).serialize()
        (directory / 'probe.proto').write_text(proto)
        results['commands'].append(command(['protoc',f'-I{directory}',f'--descriptor_set_out={directory / "schema.pb"}',str(directory / 'probe.proto')]))
    ds = descriptor_pb2.FileDescriptorSet.FromString((RAW/'v1/schema.pb').read_bytes())
    pool = descriptor_pool.DescriptorPool()
    for item in ds.file: pool.AddSerializedFile(item.SerializeToString())
    descriptor = pool.FindMessageTypeByName('probe.Record')
    Record = message_factory.GetMessageClass(descriptor)
    obs = results['observations']
    obs['field_numbers'] = {}
    obs['enum_numbers'] = {}
    for variant in ['v1','v2']:
        d = descriptor_pb2.FileDescriptorSet.FromString((RAW/variant/'schema.pb').read_bytes()).file[0]
        obs['field_numbers'][variant] = {f.name:f.number for f in d.message_type[0].field}
        obs['enum_numbers'][variant] = {f.name:f.number for f in d.enum_type[0].value}
    obs['scalar_presence'] = {f.name:f.has_presence for f in descriptor.fields}
    obs['required_count_missing_accepted'] = Record().SerializeToString() == b''
    try: Record(count=2**40)
    except (ValueError,OverflowError) as error: obs['large_integer_refusal'] = str(error)
    # Independent known encoding: tag 99, wire 0, integer 7.
    unknown = b'\x98\x06\x07'
    message = Record.FromString(Record(count=5).SerializeToString()+unknown)
    obs['binary_preserves_unknown'] = message.SerializeToString().endswith(unknown)
    via_json = json_format.Parse(json_format.MessageToJson(message),Record())
    obs['json_discards_unknown'] = not via_json.SerializeToString().endswith(unknown)
    obs['absent_equals_explicit_zero_wire'] = Record().SerializeToString() == Record(count=0).SerializeToString()
    results['commands'].append(command(['protoc',f'-I{RAW/"v1"}',f'--python_out={RAW/"v1"}',str(RAW/'v1/probe.proto')]))
    results['commands'].append(command([sys.executable,'-c',f'import sys; sys.dont_write_bytecode=True; sys.path.insert(0,{str(RAW/"v1")!r}); import probe_pb2']))
    results['commands'].append(command(['buf','breaking',str(RAW/'v2'),'--against',str(RAW/'v1'),'--error-format=json']))
    results['commands'].extend(command(args) for args in [['protoc','--version'],['buf','--version'],['rustc','--version']])
    # A passing probe can demonstrate a failing candidate boundary.
    assert obs['field_numbers']['v1']['count'] != obs['field_numbers']['v2']['count']
    assert obs['enum_numbers']['v1']['CHOICE_ACCEPT'] != obs['enum_numbers']['v2']['CHOICE_ACCEPT']
    assert obs['required_count_missing_accepted'] and obs['binary_preserves_unknown'] and obs['json_discards_unknown']
    assert obs['absent_equals_explicit_zero_wire'] and not obs['scalar_presence']['count']
    assert results['commands'][3]['returncode'] != 0, 'Expected modern-gencode/old-runtime refusal'
    (RAW/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))

if __name__ == '__main__': main()
