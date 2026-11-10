"""Repeat the audit counterexamples with independent acceptance assertions."""
from jsonschema import Draft202012Validator
from pydantic import TypeAdapter, ValidationError

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.operation_reporting import validation_failure_report
from corpus_structure.semantic.pdf_records import NativeMappingError, NativeSchemaMapping

results = {}
error = next(Draft202012Validator({"type": "integer"}).iter_errors("s" * 16384))
report = validation_failure_report(error, detail=True, raw_evidence=True, max_errors=1, max_bytes=1024)
data = report.model_dump(mode="json", exclude_none=True)
assert len(canonical_bytes(data)) <= 1024
assert data["validation_outcome"] == "nonconformant"
assert not data["presentation"]["render_complete"]
results["raw_bound"] = data
try:
    TypeAdapter(list[int]).validate_python(["bad"] * 20)
except ValidationError as error:
    data = validation_failure_report(error, detail=True, max_errors=1, max_bytes=1024).model_dump(mode="json", exclude_none=True)
    assert len(canonical_bytes(data)) <= 1024
    assert len(data["observations"]) <= 1 and len(data["correction_detail"]["nodes"]) <= 1
    assert data["validation_outcome"] == "nonconformant"
    results["item_bound"] = data
mapping = NativeSchemaMapping(b"{}", {}, Draft202012Validator({}), {})
try:
    mapping.validate({"items": [float("inf")]}, detail=True)
except NativeMappingError as error:
    data = validation_failure_report(error, detail=True).model_dump(mode="json", exclude_none=True)
    assert data["observations"][0]["input_path"] == "#/items/0"
    assert data["correction_detail"]["nodes"][0]["input_path"] == [
        {"kind": "field", "field": "items"}, {"kind": "index", "index": 0}]
    assert data["validation_outcome"] == "nonconformant"
    results["finite_location"] = data
else:
    raise AssertionError("nonfinite input was accepted")
print(canonical_bytes(dict(outcome="passed", controls=results)).decode())
