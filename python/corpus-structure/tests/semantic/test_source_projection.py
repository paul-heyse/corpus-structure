import json
from pathlib import Path

import pytest

from corpus_structure.core.evidence import RenditionContent, content_digest, rendition_key, segment_key
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.consolidation import assemble
from corpus_structure.semantic.source_projection import project_markup


@pytest.mark.parametrize("narrowed", [False, True])
def test_only_explicit_author_synthesis_becomes_a_located_statement_relation(narrowed):
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    sources = (SourceArtifact("semantic_core", core.read_bytes()),)
    root = "semantic_core"
    if narrowed:
        root = "narrowed"
        sources += (
            SourceArtifact(
                "narrowed",
                b"""id: https://example.org/narrowed
name: narrowed
imports: [semantic_core]
prefixes: {ex: 'https://example.org/'}
default_prefix: ex
classes:
  NarrowStatement:
    is_a: SourceStatement
    slot_usage:
      proves: {range: NarrowStatement}
  AgentStatementBinding:
    attributes:
      statement: {range: NarrowStatement}
""",
            ),
        )
    prepared = prepare_release(SourceBundle(root, sources))
    archive = json.loads((Path(__file__).with_name("fixtures") / "retained-html-inputs.json").read_bytes())["markup"]
    content = RenditionContent.model_validate(archive["content"])
    rk = rendition_key("document:test", content_digest(content))
    projections = []
    for i, draft in enumerate(archive["markup"]):
        projections.append(
            project_markup(
                prepared,
                "realization",
                observation_key=f"observation:{i}",
                payload=draft["payload"],
                content=content,
                page=archive["page"],
                source_uri="siegrist_random/random/test/Page.html",
                rendition_key=rk,
                segment_key=segment_key(rk, *draft["segment"]),
                provider="ingest.html",
                operation_version="test",
            )
        )
    items = tuple(item for projection in projections for item in projection.items)
    relations = [item for item in items if item.property_name == "proves"]
    assert len(relations) == 1
    assert relations[0].subject != relations[0].object
    assert relations[0].qualification == {"modality": "asserted", "polarity": True}
    batch = assemble(prepared, "realization", "markup", items)
    assert len(batch.entity) == 2
    assert all(ref.locator and ref.provider == "ingest.html" for ref in batch.evidence)
