"""Detached-column contracts with controlled Docs; no learned-provider success claim."""

import copy
import json
from pathlib import Path

import pytest
import spacy

from corpus_structure.ingest import annotations
from corpus_structure.ingest.sentences import SentenceConfig, make_doc, prepare_layout
from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.canonical_sentences import canonical_packet_values, canonical_projection_spec
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_model import BoundRoleMember
from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource, DeclaredRecordSource, DeclaredSourcePin
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.sentence_products import (
    _blocks,
    _detach_annotation_block,
    annotation_manifest,
    sentence_operation_sources,
    sentence_product_inputs,
    source_annotation_rows,
    spacy_family_coverage,
    validate_source_annotations,
)
from corpus_structure.semantic.source_products import FrozenNativeSource, source_subject


@pytest.fixture(scope="module")
def acquired(tmp_path_factory):
    directory = tmp_path_factory.mktemp("controlled-annotations")
    configuration = SentenceConfig(exclude=("ner",))
    selection = NativeSelection(NativeProfile("spacy", {"controlled": "runtime"}, {},
        configuration.model_dump(mode="json"), "float32", "cupy", 4, 1), directory)
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = sentence_product_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    prepared = prepare_release(bundle)
    model = compile_data_operations(schema=bundle,
        python_sources=sentence_operation_sources(configuration, selection=selection),
        definitions=prepared.definitions, vocabularies=prepared.vocabularies)
    return prepared, model, configuration, selection


@pytest.fixture
def detached(acquired, monkeypatch):
    prepared, model, configuration, selection = acquired
    nlp = spacy.blank("en")
    monkeypatch.setattr(annotations, "pipeline", lambda _configuration: nlp)
    text = "A valve opens."
    source = FrozenNativeSource.from_projection(prepared, document="document:one", section_pointer="#/body",
        membership="descendants", text=text,
        pieces=[dict(kind="native_text", start=0, end=len(text), item_ref="#/texts/0", source_field="text")],
        items=[dict(self_ref="#/texts/0", label="text", text=text, orig=text)])
    scope = canonical_bytes(dict(source=source.value["source"], selectors=source.value["selectors"]))
    member = BoundRoleMember("controlled-original-product", "controlled-source-kind", source_subject(source.value["source"]),
        "document:one", scope, b"{}", (), b"{}", member="controlled-original-member")
    address = DeclaredRecordSource.from_bound(source, member, project="controlled-project")
    pin = DeclaredSourcePin(canonical_bytes(address.pin()).decode())
    (block,), coverage = _blocks(source)
    layout = prepare_layout(nlp, block.block, start=block.start)
    doc = make_doc(nlp, block.block, layout, start=block.start)
    for index, token in enumerate(doc):
        token.is_sent_start = index == 0
    detached = _detach_annotation_block(source.value, block, layout, doc, pin, configuration, selection.native.fingerprint)
    availability = dict(block_id=block.block_id, start=block.start, end=block.end,
        attributes={row["attribute"]: row["status"] for row in detached["annotation"]["availability"]})
    value = dict(source=source.value["source"], selectors=source.value["selectors"],
        configuration=configuration.model_dump(mode="json"), execution_profile=selection.native.fingerprint,
        block_coverage=coverage, coverage=spacy_family_coverage(source.value, coverage, [availability]), blocks=[detached])
    value["outcome"] = "complete" if all(row["outcome"] in {"complete", "empty"} for row in value["coverage"]) else "partial"
    contract = next(identity.key for identity in model.identities
        if identity.owner == prepared.index.definitions["DdoSourceAnnotationManifest"].iri and identity.domain == "kind")
    value["members"] = [annotation_manifest(value, kind_contract=contract)]
    return source, value


def test_one_annotation_population_preserves_existing_payload_and_compact_manifest(acquired, detached):
    prepared, model, configuration, _selection = acquired
    source, value = detached
    product = validate_source_annotations(prepared, model, value, source, configuration=configuration)
    rows = source_annotation_rows(json.loads(product.content))
    frame = DeclaredNativeFrameSource(source.content.decode(), rows[0]["source"]["content"])
    restored = annotations.restore_annotations(rows, source=frame,
        profile=annotations.AnnotationProfile(configuration, execution_profile=value["execution_profile"]), require_complete=False)
    assert len(restored) == 1 and len(restored[0].tokens) == 4
    assert restored[0].block_start == 0 and restored[0].block_end == len(source.value["text"])
    assert product.value.outcome == "partial"
    assert len(value["members"]) == 1
    assert set(value["members"][0]["body"]) == {"source", "selectors", "coverage", "outcome"}
    assert not any("tokens" in packet["body"] or "blocks" in packet["body"] for packet in value["members"])
    assert "annotation_columns" not in value
    assert "DdoSentenceInventory" not in prepared.index.definitions
    from corpus_structure.semantic.data_operation_output_witnesses import validate_output_witnesses
    pin = value["blocks"][0]["annotation"]["source"]
    selected = {"source": [{"product": pin["source_product"], "member": pin.get("source_member"),
        "project_id": pin["project_id"], "kind_contract": pin["kind_contract"], "subject": pin["subject"],
        "original_source": pin["original_source"], "analyzed_scope": {"source": source.value["source"], "selectors": source.value["selectors"]},
        "body": source.value}]}
    operation = model.operation("segment.sentences/source-native")
    validate_output_witnesses(operation, {"result": [value]}, selected)
    foreign = copy.deepcopy(value)
    foreign["blocks"][0]["annotation"]["source"]["source_product"] = "foreign-parent"
    with pytest.raises(ValueError, match="complete selected input member"):
        validate_output_witnesses(operation, {"result": [foreign]}, selected)


def test_canonical_projection_uses_annotations_without_native_label_determinants(acquired, detached):
    prepared, model, _configuration, _selection = acquired
    _source, value = detached
    projection = canonical_projection_spec(model, prepared.index.definitions["DdoCanonicalSentences"].iri)
    canonical = canonical_packet_values(value, projection)
    changed = copy.deepcopy(value)
    changed["blocks"][0]["annotation"]["tokens"][0]["lemma"] = "another-native-label"
    assert canonical_packet_values(changed, projection) == canonical
    assert len(canonical["members"]) == 5
    sentence = next(packet["body"] for packet in canonical["members"] if packet["body"]["record_type"] == "sentence")
    assert sentence["start"] == 0 and sentence["end"] == 14
    assert len(sentence["token_ids"]) == 4
    prepared.validate_json("DdoCanonicalSentences", canonical_bytes(canonical))


def test_empty_annotation_producer_emits_closed_manifest_without_invoking_provider(acquired, monkeypatch):
    from corpus_structure.semantic.sentence_products import prepare_sentence_profile
    prepared, model, configuration, selection = acquired
    monkeypatch.setattr("corpus_structure.semantic.sentence_products.pipeline", lambda *_: pytest.fail("empty original loaded a model"))
    source = FrozenNativeSource.from_projection(prepared, document="document:empty", section_pointer="#/body",
        membership="descendants", text="", pieces=(), items=())
    profile = prepare_sentence_profile(prepared, model, configuration, selection=selection)
    product = profile.run(source)
    value = json.loads(product.content)
    assert value["blocks"] == [] and product.execution_receipts == ()
    assert value["outcome"] == "complete" and len(value["members"]) == 1
    assert all(row["outcome"] == "empty" for row in value["coverage"])
