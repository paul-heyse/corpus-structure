"""Owned nested identifiers associate projections without changing their subjects."""

import copy

import pytest

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.types import PreparationError, SourceArtifact, SourceBundle
from semantic.data_operation_declaration_support import source_declaration


@pytest.mark.parametrize(
    "field,valid",
    [
        ("/source/document", True),
        ("/source", False),
        ("/source/missing", False),
        ("/source/document/x", False),
        ("/source/~9", False),
        ("/related/document", False),
    ],
)
def test_compiler_validates_the_whole_inline_nominal_subject_path(field, valid):
    schema = SourceBundle(
        "nested",
        (
            SourceArtifact(
                "nested",
                b"""id: 'urn:nested:'
name: nested
prefixes: {n: 'urn:nested:'}
default_prefix: n
default_range: string
types:
  string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}
classes:
  Source:
    attributes:
      document: {required: true}
  Product:
    attributes:
      source: {range: Source, inlined: true, required: true}
      related: {range: Source, inlined: true, multivalued: true}
""",
            ),
        ),
    )
    declaration = source_declaration()
    output = declaration["roles"][0]
    output.update(kind="Product", maximum=1, collection="scalar")
    incoming = copy.deepcopy(output)
    incoming.update(
        name="source",
        direction="input",
        subject_field=field,
        support=dict(
            provenance="value_substitution",
            identity_requirements=[],
            source="original-source",
            coverage="selected-scope",
        ),
    )
    declaration["roles"].insert(0, incoming)
    artifact = SourceArtifact(
        "operation",
        canonical_bytes({"version": "data-operation-model-v1", "operations": [declaration]}),
    )
    if valid:
        result = compile_data_operations(schema=schema, declarations=(artifact,))
        assert result.operations[0].roles[0].subject_field == "/source/document"
    else:
        with pytest.raises(PreparationError, match="subject association"):
            compile_data_operations(schema=schema, declarations=(artifact,))
