import sys, json, yaml
from linkml_runtime import SchemaView
from linkml_map.transformer.object_transformer import ObjectTransformer
from linkml_map.inference.schema_mapper import SchemaMapper
from linkml_runtime.dumpers import yaml_dumper
d=sys.argv[1]
src=SchemaView(f"{d}/v1.yaml"); tgt=SchemaView(f"{d}/v2.yaml")
spec=yaml.safe_load(open(f"{d}/spec.yaml"))
spec["class_derivations"]["Value"]={"populated_from":"Value","slot_derivations":{"t":{}}}
tr=ObjectTransformer(source_schemaview=src, target_schemaview=tgt, strict=True) if 'strict' in ObjectTransformer.__dataclass_fields__ else ObjectTransformer(source_schemaview=src, target_schemaview=tgt)
print("strict field:", 'strict' in ObjectTransformer.__dataclass_fields__)
tr.create_transformer_specification(spec)
for o in [{"id":"o1","status":"ok","values":[{"t":"NumberValue","num":"1.50"},{"t":"TextValue","text":"a"}]},{"id":"o4","status":"weird"}]:
    try: print("->", json.dumps(tr.map_object(o, source_type="Obs"), default=str))
    except Exception as e: print("EXC", type(e).__name__, str(e)[:300])
derived=SchemaMapper(source_schemaview=src).derive_schema(tr.specification)
print(yaml_dumper.dumps(derived))

