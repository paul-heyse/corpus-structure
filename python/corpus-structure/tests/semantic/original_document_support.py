"""Real current source-operation preparation for bounded source/transport controls."""

from functools import lru_cache

from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_storage import native_operation_declarations, native_protocol_sources
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.data_operation_artifacts import capture_port_generator_sources
from corpus_structure.semantic.types import ResolvedDependencies, SourceArtifact, SourceBundle


@lru_cache(maxsize=1)
def source_admission_inputs():
    sources = native_protocol_sources()
    bundle = SourceBundle("source_test", (SourceArtifact("source_test", b'''id: urn:source-test
name: source_test
prefixes:
  s: "urn:source:"
  xsd: "http://www.w3.org/2001/XMLSchema#"
default_prefix: s
types: {string: {base: str, uri: xsd:string}}
classes: {Source: {attributes: {name: {range: string}}}}
'''),))
    dependencies = data_operation_dependencies(ResolvedDependencies((*sources, *capture_port_generator_sources())), (native_operation_declarations(sources),))
    return bundle, dependencies, prepare_release(bundle, dependencies)


def prepared_source_admission():
    return source_admission_inputs()[2]
