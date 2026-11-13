"""Bounded recipe and acquired-port check for captured Python builtins."""

import copy
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_ports import PythonRoleValue, resolve_python_port
from corpus_structure.semantic.identity import claim_source_item__data_operation__
from corpus_structure.semantic.python_operation_sources import PythonSource, PythonSourceCollection

metadata = copy.deepcopy(claim_source_item__data_operation__)
name = "ddo_builtin_probe"
rows = []
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / (name + ".py")
    sys.path.insert(0, directory)
    try:
        for number in (7, 8):
            code = (
                "def fake_len(value):\n    return " + str(number) + "\n"
                '__builtins__ = {"len": fake_len, "int": int, "str": str}\n'
                "def derive(index: int) -> str:\n    return str(len((index,)))\n"
                "derive__data_operation__ = " + repr(metadata) + "\n"
            )
            path.write_text(code)
            sources = PythonSourceCollection((PythonSource(name, code.encode(), str(path)),))
            model = compile_data_operations(python_sources=sources)
            operation = model.operations[0]
            recipe = next(
                i.key for i in model.identities
                if i.owner == operation.semantic_id and i.domain == "recipe"
            )
            sys.modules.pop(name, None)
            Path(importlib.util.cache_from_source(str(path))).unlink(missing_ok=True)
            port = resolve_python_port(model, sources, operation.semantic_id, authorize=lambda _: None)
            input_kind = next(r.kind for r in operation.roles if r.name == "index")
            contract = next(
                i.key for i in model.identities if i.owner == input_kind and i.domain == "kind"
            )
            values = (PythonRoleValue("index", contract, 1),)
            output = port.invoke_python(values).outputs[0].value()
            port.function.__builtins__["len"] = lambda value: 9
            after_mutation = port.invoke_python(values).outputs[0].value()
            rows.append({
                "source_value": number,
                "complete": model.implementation_slices[0].complete,
                "unknowns": [u.reason for u in model.implementation_slices[0].unknowns],
                "nodes": [n.id for n in model.implementation_slices[0].nodes],
                "recipe": recipe,
                "output": output,
                "after_builtin_mutation": after_mutation,
            })
    finally:
        sys.path.remove(directory)
        sys.modules.pop(name, None)

result = {"variants": rows, "same_recipe": rows[0]["recipe"] == rows[1]["recipe"]}
print(json.dumps(result, indent=2))
assert all(row["complete"] and not row["unknowns"] for row in rows)
assert result["same_recipe"]
assert [row["output"] for row in rows] == ["7", "8"]
assert [row["after_builtin_mutation"] for row in rows] == ["9", "9"]
