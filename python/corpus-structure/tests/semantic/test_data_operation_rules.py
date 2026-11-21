"""Independent compiler controls for the declared data-rule contract."""

import json

import pytest

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_model import read_effective_data_operations
from corpus_structure.semantic.data_operation_version import MODEL_VERSION
from corpus_structure.semantic.python_operation_sources import PythonSource, PythonSourceCollection
from corpus_structure.semantic.types import PreparationError, SourceArtifact
from semantic.data_operation_declaration_support import contract
from semantic.test_data_operation_partitions import _bundle


def declaration(identifier, form, parameters, **overrides):
    return {
        "id": identifier,
        "kind": "Collection",
        "collection": "tokens",
        "scope": "partition",
        "form": form,
        "parameters": parameters,
        "checker": "admission",
        **overrides,
    }


def compile_rules(*rules):
    return compile_data_operations(
        _bundle(),
        (
            SourceArtifact(
                "rules.yaml",
                json.dumps({"version": MODEL_VERSION, "rules": rules}).encode(),
            ),
        ),
    )


def test_rule_edit_changes_only_its_own_fingerprint_and_archives_native_record():
    unique = declaration("unique", "unique", {"paths": ["/start", "end"]})
    dense = declaration("ordinal", "dense_ordinal", {"path": "start"})
    before = compile_rules(unique, dense)
    after = compile_rules(unique, {**dense, "parameters": {"path": "start", "start": 1}})
    assert before.identities == after.identities
    by_id = {rule.id: rule for rule in before.rules}
    new_by_id = {rule.id: rule for rule in after.rules}
    assert by_id["unique"].fingerprint == new_by_id["unique"].fingerprint
    assert by_id["ordinal"].fingerprint != new_by_id["ordinal"].fingerprint
    assert json.loads(by_id["unique"].parameters) == {"paths": ["start", "end"]}
    assert by_id["ordinal"].reads[0].groups == ()
    assert [(r.path, r.groups) for r in by_id["unique"].reads] == [
        ("end", ("geometry",)),
        ("start", ("geometry",)),
    ]
    assert read_effective_data_operations(before.content).rules == before.rules
    assert json.loads(before.content)["rules"] == json.loads(
        json.dumps([rule.record for rule in before.rules])
    )


@pytest.mark.parametrize(
    ("rule", "reason"),
    [
        (declaration("bad", "unique", {"paths": ["missing"]}), "owned kind property"),
        (declaration("bad", "dense_ordinal", {"path": "end", "start": True}), "base requires"),
        (
            declaration(
                "bad",
                "refers_to",
                {"paths": ["start"], "target_paths": ["end"], "target_collection": "tokens"},
            ),
            "exact declared item address",
        ),
        (
            declaration(
                "bad",
                "attested",
                {},
                checker="producer",
                checker_callable="example.check",
                checker_operation="example",
            ),
            "captured Python sources",
        ),
    ],
)
def test_invalid_rule_refuses_compilation(rule, reason):
    with pytest.raises(PreparationError, match=reason):
        compile_rules(rule)


def test_row_predicate_is_closed_and_derives_only_paths_its_expression_reads():
    expression = {"op": "ge", "args": [{"field": "/start"}, {"value": 0}]}
    rule = compile_rules(declaration("nonnegative", "predicate", {"expression": expression})).rules[
        0
    ]
    assert [(read.path, read.groups) for read in rule.reads] == [("start", ())]
    assert json.loads(rule.parameters)["expression"]["args"][0] == {"field": "start"}
    with pytest.raises(PreparationError, match="invalid operator arity"):
        compile_rules(
            declaration(
                "bad",
                "predicate",
                {"expression": {"op": "ge", "args": [{"field": "start"}]}},
            )
        )


def test_whole_product_attestation_qualifies_binding_without_changing_recipe():
    source = PythonSourceCollection(
        (
            PythonSource(
                "example", b"def check(value: int) -> bool:\n    return value > 0\n", "example.py"
            ),
        )
    )
    operation = contract()
    attested = declaration(
        "positive",
        "attested",
        {},
        kind="integer",
        scope="product",
        checker="producer",
        checker_callable="example.check",
        checker_operation=operation["id"],
    )
    attested.pop("collection")

    def compile_operation():
        return compile_data_operations(
            declarations=(
                SourceArtifact(
                    "rules.yaml",
                    json.dumps(
                        {
                            "version": MODEL_VERSION,
                            "rules": [attested],
                            "operations": [operation],
                        }
                    ).encode(),
                ),
            ),
            python_sources=source,
        )

    before = compile_operation()
    operation["roles"][0]["required_rules"] = ["positive"]
    after = compile_operation()
    assert before.rules == after.rules
    rule = after.rules[0]
    assert rule.collection is None and rule.reads[0].path == "$all"
    assert rule.checker_determinant.startswith("implementation-slice:")
    assert after.operations[0].roles[0].required_rules == ("positive",)
    assert read_effective_data_operations(after.content).operations[0] == after.operations[0]
    old_ids = {(entry.owner, entry.domain): entry.key for entry in before.identities}
    new_ids = {(entry.owner, entry.domain): entry.key for entry in after.identities}
    assert old_ids[operation["id"], "recipe"] == new_ids[operation["id"], "recipe"]
    assert old_ids[operation["id"], "definition"] != new_ids[operation["id"], "definition"]
