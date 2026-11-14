"""Controlled native values exercise mappings and hypotheses, never provider passage."""

import json
from dataclasses import asdict

from corpus_structure.methods.pm2_result import _parser_products, pm2_contribution_values
from corpus_structure.semantic.construction_products import CharacterizationSnapshot
from corpus_structure.semantic.contextual_native_products import contextual_native_values
from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.learned_primary import maverick_input
from corpus_structure.semantic.model_characterization import prepare_model_scope
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.sentence_products import _blocks, source_annotation_rows, validate_source_annotations
from semantic.test_source_annotations import acquired as acquired, detached as detached


def test_declared_maverick_mapping_retains_original_contributions_and_context_hypotheses(acquired, detached):
    prepared, model, configuration, _ = acquired
    source, annotation = detached
    product = validate_source_annotations(prepared, model, annotation, source, configuration=configuration)
    frame = DeclaredNativeFrameSource(source.content.decode(), source_annotation_rows(annotation)[0]["source"]["content"])
    (block,), _ = _blocks(source)
    mapping = prepare_model_scope(frame, (block.start, block.end), (block.start, block.end)).mapping
    tokens, request = maverick_input(source, product, frame, block, mapping)
    native = {"outcome": "succeeded", "tokens": [token.text for token in tokens.tokens],
        "mentions": [[0, 1]], "clusters": [[[0, 1]]]}
    parsed = _parser_products("maverick", tokens, request, native, prepared)
    rows, coordinates, _ = pm2_contribution_values(tokens, parsed.locations, parsed.products,
        prepared=prepared, provider="maverick", input_digest="controlled-native-input",
        operation_key="controlled-native-operation", question="pm2.maverick.coreference")
    assert [row["semantic_type"] for row in rows] == ["source_occurrence", "maverick.mention", "maverick.cluster"]
    occurrence = rows[0]
    assert occurrence["pin"] == frame.pin.values()
    assert occurrence["anchors"][0]["pointer"] == "#/texts/0"
    assert coordinates[0]["text"] == source.value["text"]
    fact = {"provider": "maverick", "request": request, "native": native,
        "source_map": {"context_pieces": [asdict(piece) for piece in mapping.context.pieces],
            "tokens": [asdict(token) for token in tokens.tokens]}}
    common = {"source": source.value["source"], "selectors": source.value["selectors"], "coverage": []}
    maverick = CharacterizationSnapshot("selected-native-maverick", canonical_bytes({**common, "observations": [source_value(fact)]}))
    dipo = CharacterizationSnapshot("selected-native-dipo", canonical_bytes({**common, "observations": []}))
    contracts = {tag: "controlled:" + tag for tag in ("occurrence", "annotation", "membership", "role", "term", "choice", "contextual_manifest")}
    result = contextual_native_values(source, frame, (), maverick, dipo, contracts, "controlled-assets", lambda: None)
    assert result["outcome"] == "partial"
    assert result["dependencies"] == [{"product_id": "selected-native-maverick"}, {"product_id": "selected-native-dipo"}]
    bodies = [packet["body"] for packet in result["members"]]
    assert any(body.get("kind") == "native.mention" for body in bodies)
    assert any(body.get("kind") == "contextual.referent_hypothesis" for body in bodies)
    assert all("source_view_id" not in extent for body in bodies if body["record_type"] == "occurrence" for extent in body["extents"])
    assert len([body for body in bodies if body["record_type"] == "manifest"]) == 1
    assert any(row["family"] == "dipo.rst" and row["outcome"] == "partial" for row in result["coverage"])
