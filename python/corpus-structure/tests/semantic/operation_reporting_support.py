"""Shared controlled inputs and builders for operation reporting support."""

from functools import lru_cache

from corpus_structure.semantic.composed import data_operation_dependencies
from semantic.data_operation_declaration_support import contract, declarations
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.types import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)


@lru_cache(maxsize=1)
def report_inputs():
    source = SourceArtifact(
        "m",
        b"""id: https://example.org/report-test
name: report_test
prefixes: {ex: 'https://example.org/'}
default_prefix: ex
types:
 integer: {base: int, uri: 'http://www.w3.org/2001/XMLSchema#integer'}
 string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}
classes:
 Thing:
  attributes:
   label: {range: string, required: true}
""",
    )
    return (
        SourceBundle("m", (source,)),
        data_operation_dependencies(ResolvedDependencies(), declarations(contract(id="claim"))),
        PreparationProfile(version="semantic-2"),
    )


@lru_cache(maxsize=1)
def prepared():
    return prepare_release(*report_inputs())


def runtime(prepared, extra=()):
    import json
    from corpus_structure.semantic.data_operation_runtime import prepare_data_operation_runtime

    required = json.loads(next(a.content for a in prepared.artifacts if a.kind == "data_operation_runtime_inputs.json"))
    names = {item["name"] for item in required}
    inputs = tuple(source for source in report_inputs()[1].artifacts if source.name in names)
    return prepare_data_operation_runtime(prepared, (*inputs, *extra), execution_profile="controlled-report-runtime", observed={})
