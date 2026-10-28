import sys
from linkml_runtime import SchemaView
d=sys.argv[1]
sv=SchemaView(f"{d}/enums.yaml")
for e in ["BizModality","Composed"]:
    ie=sv.induced_enum(e)
    print("induced_enum", e, list(ie.permissible_values))
try:
    from oaklib.utilities.subsets.value_set_expander import ValueSetExpander
    vse=ValueSetExpander()
    for e in ["BizModality","Composed"]:
        pvs=list(vse.expand_value_set(sv.get_enum(e), schema=sv.schema))
        print("OAK", e, [(p.text, list(p.in_subset or [])) for p in pvs])
except Exception as ex:
    print("OAK EXC", type(ex).__name__, ex)
