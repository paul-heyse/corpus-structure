"""Replay retained Nemotron requests against real submitted frames and the application mapper."""

import argparse
import json
from collections import Counter
from hashlib import sha256
from importlib.metadata import version
from io import BytesIO
from pathlib import Path

import pypdfium2
from docling.utils.nemotron_parse_v3_5_utils import parse_nemotron_parse_v3_5
from docling_core.types.doc import Size
from PIL import Image

from corpus_structure.ingest.pdf_hierarchy import native_nodes, project_section_nodes
from corpus_structure.ingest.pdf_recognition import (
    PreparedRecognitionSource,
    RecognitionPage,
    recognition_observation_values,
    render_recognition_page,
)
from corpus_structure.ingest.pdf_recognition_methods import PdfIntegratedIngestConfig
from corpus_structure.ingest.pdf_reconciliation import map_pdf_observation
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.pdf_integrated import (
    PreparedPdfOriginal,
    prepare_integrated_pdf_product,
)

PAGES = (108, 151, 301, 398, 416, 509)


def digest(data):
    return sha256(data).hexdigest()


def image_bytes(image, encoding, **options):
    stream = BytesIO()
    image.save(stream, format=encoding, **options)
    return stream.getvalue()


def verify_request(row, result, raw, artifacts, directory, page_png):
    retained_row = next(r for r in result["requests"] if r["ordinal"] == row["ordinal"])
    assert retained_row == {k: v for k, v in row.items() if k != "receipt_digests"}
    assert digest(raw) == row["raw_digest"]
    reply = json.loads((directory / row["http_response"]).read_bytes())
    choice = reply["choices"][0]
    assert raw == choice["message"]["content"].encode()
    assert row["finish_reason"] == choice["finish_reason"]
    assert digest(artifacts[0]) == row["submitted_digest"]
    if row["crop"] is None:
        assert artifacts[0] == page_png
        return
    crop = row["crop"]
    assert crop in result["decisions"]
    with Image.open(BytesIO(page_png)) as page, page.crop(crop["pixels"]) as region:
        assert region.size == (row["width"], row["height"])
        jpeg = image_bytes(region, "JPEG", quality=95)
    assert jpeg == (directory / crop["jpeg_path"]).read_bytes()
    assert digest(jpeg) == crop["jpeg_digest"]
    with Image.open(BytesIO(jpeg)) as decoded, decoded.convert("RGB") as submitted:
        assert image_bytes(submitted, "PNG") == artifacts[0]


def document_summary(document):
    wire = document.model_dump(mode="json", by_alias=True, exclude_none=True)
    geometry = {}

    def split(value, path):
        if isinstance(value, list):
            return [split(item, (*path, i)) for i, item in enumerate(value)]
        if isinstance(value, dict):
            content = {}
            for key, item in value.items():
                if key in {"prov", "bbox"} or (path[:1] == ("pages",) and key == "size"):
                    geometry["/".join(map(str, (*path, key)))] = item
                else:
                    content[key] = split(item, (*path, key))
            return content
        return value

    content = split({k: v for k, v in wire.items() if k != "version"}, ())
    nodes = [node for node, _level in document.iterate_items(traverse_pictures=True)]
    return {
        "native_version": wire["version"],
        "wire_sha256": digest(canonical_bytes(wire)),
        "content_sha256": digest(canonical_bytes(content)),
        "geometry_sha256": digest(canonical_bytes(geometry)),
        "geometry_fields": len(geometry),
        "located_geometry_sha256": digest(
            canonical_bytes([value for value in geometry.values() if value])
        ),
        "labels": dict(Counter(str(node.label) for node in nodes)),
        "tables": [[table.data.num_rows, table.data.num_cols] for table in document.tables],
        "linked_captions": [
            {"owner": node.self_ref, "caption": ref.resolve(document).text}
            for node in [*document.tables, *document.pictures]
            for ref in node.captions
        ],
        "charts": [
            {
                "ref": picture.self_ref,
                "classifications": [
                    prediction.class_name for prediction in picture.meta.classification.predictions
                ],
                "shape": [chart.chart_data.num_rows, chart.chart_data.num_cols],
            }
            for picture in document.pictures
            if (chart := getattr(picture.meta, "tabular_chart", None)) is not None
        ],
    }, wire


def project_mapped(document, wire_sha256):
    nodes = native_nodes(document)
    body = document.body.self_ref
    projection = project_section_nodes(
        nodes, wire_sha256, body, "descendant", section_refs=frozenset({body}), selected_items=nodes
    )
    return {"text": projection.text, "pieces": [piece.to_wire() for piece in projection.pieces]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("retained_run", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--docling", required=True)
    args = parser.parse_args()

    versions = {
        name: version(name)
        for name in ("docling", "docling-slim", "docling-core", "pypdfium2", "pillow")
    }
    assert versions["docling"] == versions["docling-slim"] == args.docling
    assert versions["docling-core"] == {"2.145.0": "2.105.0", "2.148.0": "2.106.0"}[args.docling]
    custody = PreparedPdfOriginal(args.original.read_bytes())
    source = PreparedRecognitionSource(custody.content, custody.digest)
    config = json.loads((args.retained_run / "input.json").read_bytes())["configuration"]
    recipe = PdfIntegratedIngestConfig.model_validate(config).recognition_recipe()
    rows = []
    args.output.mkdir(parents=True, exist_ok=True)

    with pypdfium2.PdfDocument(custody.content) as original:
        for page_no in PAGES:
            directory = (
                args.retained_run
                / "recognition"
                / source.digest
                / recipe.digest
                / f"page-{page_no:05d}"
                / "attempt-00001"
            )
            input_bytes = (directory / "input.json").read_bytes()
            result_bytes = (directory / "result.json").read_bytes()
            request = json.loads(input_bytes)
            result = json.loads(result_bytes)
            png, transform = render_recognition_page(original, page_no, recipe.render_scale)
            assert request["source_digest"] == source.digest
            assert request["recipe_digest"] == recipe.digest
            assert transform == request["transform"]
            assert png == (directory / "page.png").read_bytes()
            page = RecognitionPage(page_no, directory, result, request["transform"], reused=True)
            requests = list(page.requests())
            assert [row["ordinal"] for row, _, _ in requests] == list(
                range(len(result["requests"]))
            )
            for row, raw, artifacts in requests:
                verify_request(row, result, raw, artifacts, directory, png)
                payload = recognition_observation_values(
                    page, row, raw, source=source, recipe=recipe
                )
                prepared = prepare_integrated_pdf_product(
                    payload, custody, recipe.to_bytes(), artifacts=artifacts
                )
                observation = prepared.values()
                mapped = map_pdf_observation(observation, raw)
                role = observation["observation"]["pass_role"]
                if role == "B":
                    assert mapped.dispositions == (
                        {"outcome": "evidence_only", "reason": "layout_pass"},
                    )
                    assert not mapped.origins and not mapped.document.body.children
                direct = parse_nemotron_parse_v3_5(
                    raw.decode(),
                    Size(width=row["width"], height=row["height"]),
                    page_no,
                    normalize_heading_levels=False,
                )
                direct_summary, direct_wire = document_summary(direct)
                mapped_summary, mapped_wire = document_summary(mapped.document)
                projection = project_mapped(mapped.document, mapped_summary["wire_sha256"])
                key = f"page-{page_no:05d}-request-{row['ordinal']:03d}"
                (args.output / f"{key}.native.json").write_bytes(
                    canonical_bytes(
                        {
                            "direct_parser": direct_wire,
                            "application_mapper": mapped_wire,
                            "projection": projection,
                        }
                    )
                )
                rows.append(
                    {
                        "page": page_no,
                        "request": row["ordinal"],
                        "role": role,
                        "stage": row["stage"],
                        "outcome": row["outcome"],
                        "raw_sha256": digest(raw),
                        "original_page_png_sha256": digest(png),
                        "input_receipt_sha256": digest(input_bytes),
                        "result_receipt_sha256": digest(result_bytes),
                        "request_receipt_sha256": row["receipt_digests"][
                            f"request-{row['ordinal']:03d}.json"
                        ],
                        "crop_pixels": row["crop"]["pixels"] if role == "C" else None,
                        "image": observation["observation"]["image"],
                        "observation_sha256": prepared.digest,
                        "contract_sha256": prepared.contract_digest,
                        "raw_occurrences": len(observation["occurrences"]),
                        "direct_parser": direct_summary,
                        "application_mapper": mapped_summary,
                        "origin_links": len(mapped.origins),
                        "origins_sha256": digest(canonical_bytes(mapped.origins)),
                        "projection_text_sha256": digest(projection["text"].encode()),
                        "projection_pieces_sha256": digest(canonical_bytes(projection["pieces"])),
                        "dispositions": dict(Counter(d["outcome"] for d in mapped.dispositions)),
                        "dispositions_sha256": digest(canonical_bytes(mapped.dispositions)),
                    }
                )
    (args.output / "summary.json").write_text(
        json.dumps(
            {
                "versions": versions,
                "original_sha256": source.digest,
                "recipe_sha256": recipe.digest,
                "roles": dict(Counter(row["role"] for row in rows)),
                "rows": rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
