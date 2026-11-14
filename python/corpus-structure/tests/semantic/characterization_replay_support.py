"""Shared controlled inputs and builders for characterization replay support."""

import base64
import json
import zlib
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from corpus_structure.ingest.pdf_hierarchy import section_text_recipe, section_view_key
from corpus_structure.semantic.characterization import (
    attachment_policies,
    occurrence_id,
    validate_layer,
    validate_view,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.pdf_record_identity import (
    PROTOCOL,
    IdentityFold,
    ScalarDescriptor,
    byte_root,
    record_frame,
)
from corpus_structure.semantic.pdf_records import (
    iter_native_records,
    native_record_identity_fields,
    native_schema_bytes,
)
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.serve.characterization_replay import FORMAT, CharacterizationReviewSelection
from corpus_structure.serve.review_source_projection import SECTION_TEXT_INPUT


@pytest.fixture(scope="module")
def prepared():
    from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
    from corpus_structure.semantic.characterization import characterization_inputs

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    return prepare_release(characterization_inputs(bundle))


def bundle(root, prepared, *, with_layer=True, native_evidence=False) -> dict[str, Any]:
    root.mkdir()
    document: dict[str, Any] = {
        "name": "Retained source",
        "body": {"self_ref": "#/body", "children": [{"$ref": "#/texts/0"}]},
        "texts": [
            {
                "self_ref": "#/texts/0",
                "label": "text",
                "text": "all",
                "orig": "all",
                "parent": {"$ref": "#/body"},
            }
        ],
    }
    document["pages"] = {"1": {"page_no": 1, "size": {"width": 100.0, "height": 100.0}}}
    document["texts"][0]["prov"] = [
        {
            "page_no": 1,
            "charspan": [0, 3],
            "bbox": {"l": 0.0, "t": 0.0, "r": 20.0, "b": 5.0, "coord_origin": "TOPLEFT"},
        }
    ]
    original, producer_release = "a" * 64, "release:producer"
    descriptors = {}

    def write(stream, profile, chunks):
        size, digest = byte_root(chunks)
        value = ScalarDescriptor(
            b"y" if profile == "pdf-record-native-json-v1" else profile[-1:].encode(), size, digest
        )
        descriptors[stream] = value
        return value

    rows = list(
        iter_native_records(
            document,
            product_id="base",
            revision_id="base",
            release_id=producer_release,
            source_digest=original,
            record_id_for=lambda address, kind: sha256(
                (original + "\0" + address + "\0" + kind).encode()
            ).hexdigest(),
            write_scalar=write,
        )
    )
    schema = native_schema_bytes()
    schema_digest = sha256(schema).hexdigest()
    identities = {}
    inventory, targets = [], []
    for row in rows:
        identity = native_record_identity_fields(row, scalar_descriptor=descriptors.__getitem__)
        if identity:
            family, key, fields = identity
            identities[(family, key)] = fields
        if row.kind == "native":
            scalars = json.loads(row.values["scalars_json"])
            structure = json.loads(row.values["structure_json"])["fields"]
            for name, value in structure.items():
                if value["kind"] == "object":
                    targets.append((row.values["record_id"], name, -1, value["target"]))
            if "self_ref" in scalars:
                pointer = scalars["self_ref"]
                node = document["body"] if pointer == "#/body" else document["texts"][0]
                inventory.append(
                    dict(
                        pointer=pointer,
                        record_id=row.values["record_id"],
                        label=node.get("label", "unspecified"),
                        content_layer="body",
                        parent_pointer=node.get("parent", {}).get("$ref"),
                        children=node.get("children"),
                    )
                )
        if (
            row.kind == "membership"
            and row.values["value_kind"] == "record"
            and "member_key" not in row.values
            and "member_key_stream_id" not in row.values
        ):
            targets.append(
                (
                    row.values["parent_id"],
                    row.values["field_name"],
                    row.values["ordinal"],
                    row.values["record_id"],
                )
            )
    metadata_value = {"score": -0.0, "small": 1e-7, "text": "retained"}
    metadata_bytes = canonical_bytes(metadata_value)
    metadata_length, metadata_root = byte_root((metadata_bytes,))
    metadata_body = {"kind": "runtime_report", "ordinal": 0, "pointer": "#/body"}
    input_body = {"role": "structural", "configuration": "cfg"}
    identities[("companion/input", "0")] = (
        ("body", '{"configuration":"cfg","role":"structural"}'),
        ("ordinal", 0),
    )
    identities[("companion/native_metadata", "runtime_report:0")] = (
        ("body", '{"kind":"runtime_report","ordinal":0,"pointer":"#/body"}'),
        ("ordinal", 0),
        ("value", ScalarDescriptor(b"y", metadata_length, metadata_root)),
    )
    companions = [
        dict(family="input", local_id="0", ordinal=0, body=input_body, fields=[]),
        dict(
            family="native_metadata",
            local_id="runtime_report:0",
            ordinal=0,
            body=metadata_body,
            fields=[
                dict(
                    name="value",
                    profile="pdf-companion-json-field-v1",
                    kind="y",
                    content_base64=base64.b64encode(metadata_bytes).decode(),
                )
            ],
        ),
    ]
    identities[("@context", "@context")] = (
        ("protocol", PROTOCOL),
        ("release", producer_release),
        ("source", original),
    )
    frames = [
        record_frame(schema_digest, family, key, fields)
        for (family, key), fields in sorted(identities.items())
    ]
    fold = IdentityFold("records")
    for frame in frames:
        fold.add(frame)
    base = ProductReference(7, "native", fold.digest().hex())
    proofs = [
        dict(
            product=base.values(),
            native_schema=schema_digest,
            original=original,
            producer_release=producer_release,
        ),
        dict(frames=base64.b64encode(zlib.compress(b"".join(frames))).decode()),
        dict(targets=targets),
        dict(items=inventory),
    ]
    policy = (
        b'{"content_layers":["body"],"readable_formula_originals":[],'
        b'"recipe":"native-section-text-v10"}'
    )
    policy_manifest = canonical_bytes(
        {"dependencies": [[SECTION_TEXT_INPUT, sha256(policy).hexdigest()]]}
    )
    source_release = "release:" + sha256(policy_manifest).hexdigest()
    recipe = section_text_recipe(base, analysis_eligible=True, policy=policy)
    context = dict(
        items=[document["body"], document["texts"][0]],
        ancestors=[],
        pieces=[
            dict(item_ref="#/texts/0", start=0, end=3, kind="native_text", source_field="text")
        ],
        health={"state": "unknown"},
    )
    projection = {
        "text": "all",
        "pieces": context["pieces"],
        "items": ["#/body", "#/texts/0"],
        "ancestors": [],
        "health": context["health"],
    }
    projection_digest = sha256(canonical_bytes(projection)).hexdigest()
    source_pin = dict(
        source_view_id=11,
        key=section_view_key(source_release, base, "#/body", "direct", True, recipe),
        base_document=base.values(),
        section_pointer="#/body",
        membership="direct",
        projection_digest=projection_digest,
        recipe_digest=sha256(recipe).hexdigest(),
    )
    scope = dict(
        source_view_ids=[11],
        source_views=[source_pin],
        profile="bounded",
        selectors=[{"projection": projection_digest}],
    )
    layers = {}
    if with_layer:
        extents = [
            dict(
                projection=projection_digest,
                source_view_id=11,
                native_pointer="#/texts/0",
                page=1,
                start=0,
                end=3,
                text="all",
                synthetic=False,
            )
        ]
        report = validate_layer(
            prepared,
            dict(
                format="characterization-layer-v1",
                base_document=base.values(),
                release_id=prepared.release_id,
                operation=dict(
                    key="text.test",
                    version="1",
                    runtime="test",
                    model="none",
                    grammar="none",
                    configuration="cfg",
                    input="input",
                    context="section",
                    produced_families=["scope"],
                    outcomes=["complete", "partial", "failed"],
                    result_determinants=["input"],
                ),
                source_scope=scope,
                outcome="complete",
                occurrences=[dict(local_id=occurrence_id(base, extents), extents=extents)],
                annotations=[
                    dict(
                        local_id="native-token",
                        family="scope",
                        kind="token",
                        vocabulary="toy-native",
                        native_scheme="retained-parser-v1",
                        native_label="DT",
                        status="native_evidence",
                        occurrences=[occurrence_id(base, extents)],
                    )
                ]
                if native_evidence
                else [],
                terms=[
                    dict(
                        local_id="all",
                        family="scope",
                        kind="operator",
                        vocabulary="logic",
                        value="all",
                        status="interpreted",
                        occurrences=[occurrence_id(base, extents)],
                    )
                ],
                coverage=[
                    dict(
                        family="scope",
                        operation="text.test",
                        eligible=scope["selectors"],
                        examined=scope["selectors"],
                        availability="available",
                        outcome="complete",
                        profile="bounded",
                    )
                ],
            ),
        )
        layers[report.reference(8)] = report
    view = validate_view(
        prepared,
        dict(
            format="enriched-document-view-v1",
            base_document=base.values(),
            release_id=prepared.release_id,
            source_scope=scope,
            layers=[p.values() for p in layers],
            profile="selected_layers" if layers else "source_only",
            coverage=[row for layer in layers.values() for row in layer.payload["coverage"]],
        ),
        layers,
    )
    selection = CharacterizationReviewSelection(run_id=3, **view.reference(9).values())
    files = {}

    def store(name, content):
        (root / name).write_bytes(content)
        files[name] = dict(path=name, sha256=sha256(content).hexdigest(), bytes=len(content))

    store("view.json", view.content)
    layer_members = []
    for i, (pin, layer) in enumerate(layers.items()):
        name = f"layer-{i}.json"
        store(name, layer.content)
        layer_members.append(dict(reference=pin.values(), path=name))
    policies = attachment_policies(prepared)
    names = {"AnnotationLayer", "EnrichedDocumentView"} | {
        p["class_name"] for p in policies.values()
    }
    names.update(
        rule["class_name"]
        for policy in policies.values()
        for rule in policy.get("rules", {}).values()
    )
    from corpus_structure.semantic import SourceArtifact, SourceBundle
    from corpus_structure.semantic.characterization import characterization_inputs

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    release_inputs = characterization_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    store(
        "contracts.json",
        canonical_bytes(
            dict(
                release_id=prepared.release_id,
                manifest_base64=base64.b64encode(prepared.manifest).decode(),
                schemas={name: prepared.json_schema(name) for name in names},
                attachment_policies=policies,
                sources={
                    source.name: base64.b64encode(source.content).decode()
                    for source in release_inputs.sources
                },
                dependencies={},
            )
        ),
    )
    store("native-schema.json", schema)
    store("companions.jsonl", b"".join(canonical_bytes(row) + b"\n" for row in companions))
    store("payload-schemas.json", b"{}")
    store(
        "base.json",
        canonical_bytes(
            dict(
                export_profile="pdf-complete-record-export-v1",
                binding=dict(view=selection.reference().values(), base_document=base.values()),
                product=dict(
                    product_key=base.product_key,
                    logical_digest=base.content_digest,
                    content=document,
                    inputs=[input_body],
                    native_metadata=[dict(kind="runtime_report", ordinal=0, value=metadata_value)],
                ),
            )
        ),
    )
    store("source-proofs.jsonl", b"".join(canonical_bytes(row) + b"\n" for row in proofs))
    ref = dict(
        id=11,
        document_id=17,
        key=source_pin["key"],
        native_product=base.values(),
        section_pointer="#/body",
        membership="direct",
        projection_digest=projection_digest,
        recipe_digest=source_pin["recipe_digest"],
        analysis_eligible=True,
    )
    store(
        "sources.json",
        canonical_bytes(
            [
                dict(
                    source_view_id=11,
                    ref=ref,
                    text="all",
                    context=context,
                    consumer_release=source_release,
                )
            ]
        ),
    )
    store(
        "source-contracts.json",
        canonical_bytes(
            {
                source_release: dict(
                    release_id=source_release,
                    section_text_policy=dict(
                        manifest_base64=base64.b64encode(policy_manifest).decode(),
                        input_base64=base64.b64encode(policy).decode(),
                    ),
                )
            }
        ),
    )
    manifest = dict(
        format=FORMAT,
        selection=selection.model_dump(mode="json"),
        view="view.json",
        layers=layer_members,
        files=files,
        original_source_completeness="complete_native_document_and_companions",
        completeness="exact_view_closure",
        standing="private_analyses",
    )
    (root / "manifest.json").write_bytes(canonical_bytes(manifest))
    return manifest


def construction_release_inputs():
    """A real added witnessed-rule declaration, not a relabelled release identifier."""
    import yaml

    from corpus_structure.semantic import SourceArtifact, SourceBundle
    from corpus_structure.semantic.characterization import characterization_inputs

    model_root = Path(__file__).parents[2] / "src/corpus_structure/model/semantic"
    model = yaml.safe_load((model_root / "characterization.yaml").read_bytes())
    model["classes"]["ReplayConstructionBasis"] = {
        "is_a": "CharacterizationConstructionBasis",
        "attributes": {
            "rule_id": {"required": True, "equals_string": "replay:body-v1"},
            "premises": {
                "range": "string",
                "multivalued": True,
                "required": True,
                "minimum_cardinality": 1,
            },
        },
    }
    return characterization_inputs(
        SourceBundle("core", (SourceArtifact("core", (model_root / "core.yaml").read_bytes()),)),
        model_content=yaml.safe_dump(model).encode(),
    )


def contract_data(prepared, sources):
    policies = attachment_policies(prepared)
    names = {"AnnotationLayer", "EnrichedDocumentView"} | {
        row["class_name"] for row in policies.values()
    }
    names.update(
        rule["class_name"]
        for policy in policies.values()
        for rule in policy.get("rules", {}).values()
    )
    return dict(
        release_id=prepared.release_id,
        manifest_base64=base64.b64encode(prepared.manifest).decode(),
        schemas={name: prepared.json_schema(name) for name in names},
        attachment_policies=policies,
        sources={
            source.name: base64.b64encode(source.content).decode() for source in sources.sources
        },
        dependencies={},
    )
