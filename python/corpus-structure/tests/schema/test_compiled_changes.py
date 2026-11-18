"""Independent expectations for the released model's fact comparison."""

from corpus_structure.model.compiled import compiled_model
from corpus_structure.schema.compiled_changes import compare_compiled_models


def test_comparison_names_added_column_member_and_changed_check():
    before = {
        "physical.yaml": b"""id: urn:physical
name: physical
classes:
  record:
    attributes:
      id: {range: string}
    annotations:
      ph:checks: {tag: 'ph:checks', value: [{name: positive, minimum: 0}]}
enums:
  Status:
    annotations: {cs:openness: pack-extensible}
    permissible_values: {ready: {}}
""",
    }
    after = {
        "physical.yaml": before["physical.yaml"]
        .replace(
            b"      id: {range: string}", b"      id: {range: string}\n      note: {range: string}"
        )
        .replace(b"minimum: 0", b"minimum: 1")
        .replace(b"{ready: {}}", b"{ready: {}, pending: {}}"),
    }
    comparison = compare_compiled_models(compiled_model(before), compiled_model(after))
    assert [(item.element, item.kind, item.before, item.after) for item in comparison.changes] == [
        (
            "classes/record/annotations/ph:checks/value",
            "changed",
            [{"name": "positive", "minimum": 0}],
            [{"name": "positive", "minimum": 1}],
        ),
        ("classes/record/attributes/note", "added", None, {"range": "string"}),
        ("enums/Status/permissible_values/pending", "added", None, {}),
    ]
    assert comparison.before != comparison.after
    assert compare_compiled_models(compiled_model(before), compiled_model(before)).changes == ()
