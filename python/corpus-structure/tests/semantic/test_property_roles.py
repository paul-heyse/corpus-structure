"""Independent expectations for the effective input universe."""

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release


def test_effective_roles_include_inherited_identity_required_and_display_only():
    raw = b"""
id: https://example.org/roles
name: roles
prefixes: {ex: 'https://example.org/'}
default_prefix: ex
types:
  string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}
classes:
  Parent:
    attributes:
      id: {identifier: true}
      label: {annotations: {'cs:role': display}}
      compulsory: {required: true}
      noise: {}
  Child:
    is_a: Parent
    attributes:
      own: {required: true}
"""
    release = prepare_release(SourceBundle("roles", (SourceArtifact("roles", raw),)))
    roles = release.index.property_roles
    parent = next(d for d in release.definitions if d.name == "Parent")
    child = next(d for d in release.definitions if d.name == "Child")
    for definition in (parent, child):
        props = {p.name: p.iri for p in definition.properties}
        assert roles[definition.iri, props["id"]] == {"identity", "required"}
        assert roles[definition.iri, props["label"]] == {"display"}
        assert roles[definition.iri, props["compulsory"]] == {"required"}
        assert (definition.iri, props["noise"]) not in roles
    assert roles[child.iri, next(p.iri for p in child.properties if p.name == "own")] == {
        "required"
    }
