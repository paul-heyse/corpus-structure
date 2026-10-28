import sys, yaml, json
from linkml_runtime import SchemaView
from linkml_map.transformer.object_transformer import ObjectTransformer
from linkml_map.inference.inverter import TransformationSpecificationInverter
from linkml_map.inference.schema_mapper import SchemaMapper
d = sys.argv[1]
src = SchemaView(f"{d}/v1.yaml"); tgt = SchemaView(f"{d}/v2.yaml")
tr = ObjectTransformer(source_schemaview=src, target_schemaview=tgt)
tr.load_transformer_specification(f"{d}/spec.yaml")
cases = {
 "full": {"id":"o1","status":"ok","note":"x","detail":{"n_tokens":3},"values":[{"t":"NumberValue","num":"1.50"},{"t":"TextValue","text":"a"}]},
 "absent_note": {"id":"o2","status":"fail","detail":{"n_tokens":0}},
 "null_note": {"id":"o3","status":"fail","note":None},
 "unknown_status": {"id":"o4","status":"weird"},
}
for k,o in cases.items():
    try:
        print(k, "->", json.dumps(tr.map_object(o, source_type="Obs"), default=str))
    except Exception as e:
        print(k, "EXC", type(e).__name__, str(e)[:200])
inv = TransformationSpecificationInverter(source_schemaview=src, target_schemaview=tgt).invert(tr.specification)
print("inverted class derivs:", [(c.name, c.populated_from, {k:v.populated_from for k,v in c.slot_derivations.items()}) for c in inv.class_derivations])
print("inverted enum derivs:", {k:(v.populated_from, {p:q.populated_from for p,q in (v.permissible_value_derivations or {}).items()}) for k,v in inv.enum_derivations.items()})
tr2 = ObjectTransformer(source_schemaview=tgt, target_schemaview=src); tr2.specification = inv
print("roundtrip:", json.dumps(tr2.map_object(tr.map_object(cases["full"], source_type="Obs"), source_type="Obs"), default=str))
derived = SchemaMapper(source_schemaview=src).derive_schema(tr.specification)
print("derived classes:", {c: list(derived.classes[c].attributes.keys()) if derived.classes[c].attributes else None for c in derived.classes})
print("derived enums:", {e: list(v.permissible_values) for e,v in derived.enums.items()})
