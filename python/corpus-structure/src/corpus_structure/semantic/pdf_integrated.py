"""Model-governed PDF companion products, independent of recognition execution.

Preparation does no I/O or inference. Publication retains one immutable bundle under the
existing task fence. A recognizer or matching algorithm is deliberately not bound here.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from io import BytesIO
from typing import Any

from sqlalchemy import Connection, text

from .identity import canonical_bytes
from .pdf_contracts import (
    PreparedPdfContext,
    pdf_context_for_task,
    prepare_pdf_product,
    resolve_native_pointer,
    trusted_pdf_context,
)


@dataclass(frozen=True, slots=True)
class PreparedIntegratedPdfProduct:
    payload: bytes
    artifacts: tuple[bytes, ...]
    contract_digest: str
    _validated: bool = field(default=False, init=False, repr=False, compare=False)

    @property
    def digest(self) -> str:
        return sha256(self.payload).hexdigest()

    def values(self) -> dict[str, Any]:
        return json.loads(self.payload)


def _json_object(value: str, label: str) -> dict[str, Any]:
    result = json.loads(value)
    if not isinstance(result, dict):
        raise ValueError(label + " must be a JSON object")
    return result


def prepare_integrated_pdf_product(
    payload: Mapping[str, Any],
    original: bytes,
    recipe_bytes: bytes,
    *,
    artifacts: tuple[bytes, ...] = (),
    native_schema: bytes | None = None,
    context: PreparedPdfContext | None = None,
) -> PreparedIntegratedPdfProduct:
    """Admit a retained observation or integrated content with mandatory companion semantics.

    Exact external endpoint existence/custody is checked atomically at publication. The
    caller must retain the submitted image and raw response bytes even for failed passes.
    """
    context = trusted_pdf_context() if context is None else context
    context.execution.require_operation("prepare_integrated_pdf")
    supplied = dict(payload)
    content = supplied.get("content")
    native = None
    if content is not None:
        if native_schema is None:
            raise ValueError("integrated Docling content requires its retained native schema")
        native = prepare_pdf_product(
            content, original, native_schema, recipe_bytes, context=context
        )
        supplied["content"] = native.values()
        document = supplied["content"].pop("document")
        supplied["content"]["document_json"] = canonical_bytes(document).decode()
    value = context.boundary.validate_json("PdfIntegratedProduct", json.dumps(supplied)).model_dump(
        mode="json", exclude_none=True
    )
    for field_name in ("inputs", "occurrences", "relations"):
        value.setdefault(field_name, [])
    for coverage_row in value["coverage"]:
        coverage_row.setdefault("supports", [])
    if content is not None:
        value["content"].pop("document_json")
        assert native is not None
        value["content"]["document"] = native.values()["document"]
    if value["kind"] not in {"recognition_observation", "integrated"}:
        raise ValueError("native products use their preserved native publication contract")
    if not value["product_key"] or not original.startswith(b"%PDF-"):
        raise ValueError("product key and PDF original are required")
    if value["artifact_digest"] != sha256(original).hexdigest():
        raise ValueError("original digest differs from retained bytes")
    if value["recipe_digest"] != sha256(recipe_bytes).hexdigest():
        raise ValueError("recipe digest differs from retained bytes")
    inputs = value["inputs"]
    keys = [(i["role"], i["task_id"], i["product_key"]) for i in inputs]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate role-qualified product input")
    if any(not i["product_key"] for i in inputs):
        raise ValueError("input product key cannot be empty")
    occurrences = value["occurrences"]
    ids = [o["occurrence_id"] for o in occurrences]
    if any(not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("duplicate or empty occurrence identity")
    observation = value.get("observation")
    retained = {sha256(b).hexdigest(): b for b in (recipe_bytes, *artifacts)}
    if native_schema is not None:
        retained[sha256(native_schema).hexdigest()] = native_schema
    if value["kind"] == "recognition_observation":
        if observation is None or content is not None:
            raise ValueError(
                "recognition observation requires an observation body without selected content"
            )
        image = observation["image"]
        if image["artifact_digest"] not in retained or (
            "raw_response_digest" in observation
            and observation["raw_response_digest"] not in retained
        ):
            raise ValueError("submitted image and raw response bytes must be retained")
        if (
            observation["outcome"] in {"succeeded", "partial"}
            and "raw_response_digest" not in observation
        ):
            raise ValueError("successful/partial observation requires its actual raw response")
        if observation["outcome"] in {"failed", "unknown", "unsupported"} and not observation.get(
            "diagnostic"
        ):
            raise ValueError("failed/unavailable observation requires an attributable diagnostic")
        if value["health"]["execution_outcome"] != observation["outcome"]:
            raise ValueError("observation execution outcome differs from its health report")
        if image["precision"] not in {"unknown", "coarse"}:
            raise ValueError("I10/I11 have not admitted fine provider image precision")
        from PIL import Image

        with Image.open(BytesIO(retained[image["artifact_digest"]])) as submitted:
            if submitted.format != "PNG" or submitted.size != (image["width"], image["height"]):
                raise ValueError("submitted image bytes differ from declared dimensions/encoding")
            submitted.verify()
        if any(o.get("page_no", image["page_no"]) != image["page_no"] for o in occurrences):
            raise ValueError("provider occurrence page differs from submitted image")
        transform = image["transform"]
        parameters = {
            "page_width",
            "page_height",
            "page_rotation",
            "crop_left",
            "crop_top",
            "crop_right",
            "crop_bottom",
            "affine",
        }
        if transform["status"] == "unknown" and parameters & transform.keys():
            raise ValueError("unknown image transform cannot carry fabricated parameters")
        if transform["status"] == "coarse":
            if not parameters <= transform.keys() or len(transform["affine"]) != 6:
                raise ValueError(
                    "coarse image transform requires its full page/crop/affine witness"
                )
            if transform["page_rotation"] not in {0, 90, 180, 270} or not (
                0 <= transform["crop_left"] < transform["crop_right"] <= transform["page_width"]
                and 0
                <= transform["crop_top"]
                < transform["crop_bottom"]
                <= transform["page_height"]
            ):
                raise ValueError("image transform crop/page/rotation differs")
        _json_object(observation["binding"]["decoding_json"], "effective decoding")
        if (observation["usage_availability"] == "available") != ("usage_json" in observation):
            raise ValueError("usage availability differs from retained provider report")
        if "usage_json" in observation:
            _json_object(observation["usage_json"], "usage")
        if any(o["precision"] not in {"unknown", "coarse", "block"} for o in occurrences):
            raise ValueError("I10/I11 have not admitted fine provider occurrence precision")
    else:
        if content is None or observation is not None:
            raise ValueError(
                "integrated product requires Docling content and separate observation inputs"
            )
        if not {"structural", "recognition"} <= {i["role"] for i in inputs}:
            raise ValueError("integrated product requires structural and recognition inputs")
        if value["content"]["artifact_digest"] != value["artifact_digest"]:
            raise ValueError("selected content differs from original custody")
    for occurrence in occurrences:
        if ("start" in occurrence) != ("end" in occurrence):
            raise ValueError("occurrence range requires both endpoints")
        if "start" in occurrence:
            if occurrence["address_space"] not in {
                "native_item",
                "recognized_text",
                "selected_item",
                "raw_response",
            }:
                raise ValueError("range is not in a declared text/token address space")
            if occurrence["start"] > occurrence["end"] or (
                "text" in occurrence and occurrence["end"] > len(occurrence["text"])
            ):
                raise ValueError("occurrence text range is outside its declared spelling")
            if occurrence["precision"] in {"unknown", "coarse", "block", "inherited"}:
                raise ValueError("coarse occurrence cannot claim an exact text range")
        if "region" in occurrence:
            region = occurrence["region"]
            if (
                region["left"] > region["right"]
                or (region["origin"] == "top_left" and region["top"] > region["bottom"])
                or (region["origin"] == "bottom_left" and region["top"] < region["bottom"])
            ):
                raise ValueError("region bounds differ from declared coordinate origin")
            if value["kind"] == "recognition_observation" and region["precision"] not in {
                "unknown",
                "coarse",
                "block",
            }:
                raise ValueError("I10/I11 have not admitted fine provider region precision")
        if value["kind"] == "integrated":
            pointer = occurrence.get("pointer")
            if pointer is None:
                raise ValueError("selected occurrence requires a native content pointer")
            node = resolve_native_pointer(value["content"]["document"], pointer)
            if occurrence["kind"] == "cell":
                index = occurrence.get("cell_index")
                if (
                    index is None
                    or node.get("label") != "table"
                    or index >= len(node.get("data", {}).get("table_cells", ()))
                ):
                    raise ValueError("selected cell is outside its native table")
                node = node["data"]["table_cells"][index]
            elif "cell_index" in occurrence:
                raise ValueError("cell index requires a cell occurrence")
            kind = occurrence["kind"]
            if kind == "cell":
                if occurrence["address_space"] != "native_cell" or occurrence["precision"] not in {
                    "cell",
                    "item",
                    "inherited",
                    "coarse",
                    "unknown",
                }:
                    raise ValueError(
                        "selected cell address/precision differs from native cell custody"
                    )
            else:
                label = node.get("label")
                if (
                    kind not in {"item", "text", "formula", "chart", "region"}
                    or (kind != "region" and (kind == "formula") != (label == "formula"))
                    or (kind == "text" and label != "text")
                    or (
                        kind == "chart"
                        and (
                            label != "picture"
                            or not any(
                                a.get("kind", "").endswith("_chart_data")
                                for a in node.get("annotations", ())
                            )
                        )
                    )
                ):
                    raise ValueError("selected occurrence kind differs from native label")
                if occurrence["address_space"] not in {
                    "native_item",
                    "selected_item",
                    *(["pdf_points"] if kind == "region" else []),
                } or occurrence["precision"] not in {"item", "inherited", "coarse", "unknown"}:
                    raise ValueError("selected item address/precision differs from native custody")
            if "text" in occurrence and node.get("text") != occurrence["text"]:
                raise ValueError("selected occurrence text differs from Docling content")
            if "start" in occurrence and "text" not in occurrence:
                raise ValueError("selected text range requires its retained native spelling")
            if "page_no" in occurrence and not any(
                p["page_no"] == occurrence["page_no"]
                for p in resolve_native_pointer(value["content"]["document"], pointer).get(
                    "prov", ()
                )
            ):
                raise ValueError("selected occurrence page differs from native provenance")
            if kind == "region":
                index = occurrence.get("region_index")
                if (
                    index is None
                    or index >= len(node.get("prov", ()))
                    or "region" not in occurrence
                ):
                    raise ValueError("native region requires its exact provenance index/witness")
            elif "region_index" in occurrence:
                raise ValueError("region index requires a region occurrence")
            if "region" in occurrence:
                region = occurrence["region"]
                if "page_no" not in occurrence:
                    raise ValueError("PDF region requires its physical page")
                witnesses = [
                    (p["page_no"], p["bbox"])
                    for index, p in enumerate(node.get("prov", ()))
                    if kind != "region" or index == occurrence["region_index"]
                ]
                if kind == "cell" and node.get("bbox") is not None:
                    table_prov = resolve_native_pointer(value["content"]["document"], pointer).get(
                        "prov", ()
                    )
                    if len(table_prov) == 1:
                        witnesses.append((table_prov[0]["page_no"], node["bbox"]))
                if (
                    region["address_space"] != "pdf_points"
                    or region["precision"] not in {"cell", "item", "inherited", "coarse", "unknown"}
                    or not any(
                        page == occurrence["page_no"]
                        and all(
                            region[k] == box[n]
                            for k, n in (
                                ("left", "l"),
                                ("top", "t"),
                                ("right", "r"),
                                ("bottom", "b"),
                            )
                        )
                        and region["origin"]
                        == {"TOPLEFT": "top_left", "BOTTOMLEFT": "bottom_left"}.get(
                            box["coord_origin"]
                        )
                        for page, box in witnesses
                    )
                ):
                    raise ValueError("selected region differs from retained native page/geometry")
        elif "region" in occurrence:
            region = occurrence["region"]
            assert observation is not None
            image = observation["image"]
            if region["address_space"] == "submitted_pixels":
                if region["origin"] != "top_left" or not (
                    0 <= region["left"] <= region["right"] <= image["width"]
                    and 0 <= region["top"] <= region["bottom"] <= image["height"]
                ):
                    raise ValueError("provider region lies outside submitted image")
            elif region["address_space"] == "normalized_raw":
                if not all(0 <= region[k] <= 1 for k in ("left", "top", "right", "bottom")):
                    raise ValueError("normalized provider region lies outside unit frame")
            else:
                raise ValueError("provider region requires its submitted or normalized raw frame")
    if value["kind"] == "integrated":
        document = value["content"]["document"]
        nodes = [document[k] for k in ("body", "furniture")]
        nodes.extend(
            node
            for children in document.values()
            if isinstance(children, list)
            for node in children
            if isinstance(node, dict) and "self_ref" in node
        )
        expected: set[tuple[str, int | None]] = {(node["self_ref"], None) for node in nodes}
        expected.update(
            (node["self_ref"], index)
            for node in nodes
            if node.get("label") == "table"
            for index, _ in enumerate(node.get("data", {}).get("table_cells", ()))
        )
        actual = [(o["pointer"], o.get("cell_index")) for o in occurrences if o["kind"] != "region"]
        if len(actual) != len(expected) or set(actual) != expected:
            raise ValueError("selected content occurrence inventory is incomplete or ambiguous")
    relation_ids = set()
    for relation in value["relations"]:
        if not relation["relation_id"] or relation["relation_id"] in relation_ids:
            raise ValueError("duplicate or empty relation identity")
        relation_ids.add(relation["relation_id"])
        if any(not relation[k] for k in ("policy", "evidence")):
            raise ValueError("relation requires governing policy and comparison evidence")
        outcomes = (
            {"matched", "ambiguous", "unmatched", "unresolved"}
            if relation["kind"] == "correspondence"
            else {"selected", "added", "replaced", "retained_alternative", "rejected", "unresolved"}
        )
        if relation["outcome"] not in outcomes:
            raise ValueError("relation outcome differs from its declared kind")
        endpoints = relation["endpoints"]
        identities = [(e.get("input_index"), e["occurrence_id"], e["role"]) for e in endpoints]
        if len(set(identities)) != len(identities):
            raise ValueError("duplicate relationship endpoint")
        for endpoint in endpoints:
            index = endpoint.get("input_index")
            if index is None:
                if endpoint["role"] != "output" or endpoint["occurrence_id"] not in ids:
                    raise ValueError("local endpoint is not an existing output occurrence")
            elif index >= len(inputs) or endpoint["role"] == "output":
                raise ValueError("input endpoint index/role differs from declared product inputs")
        input_endpoints = [e for e in endpoints if "input_index" in e]
        outputs = [e for e in endpoints if e["role"] == "output"]
        if not input_endpoints:
            raise ValueError("relationship requires attributable input observations")
        if (
            relation["kind"] == "correspondence"
            and relation["outcome"] in {"matched", "ambiguous"}
            and len({(e.get("input_index"), e["occurrence_id"]) for e in endpoints}) < 2
        ):
            raise ValueError("matched/ambiguous correspondence requires multiple endpoints")
        if (
            relation["kind"] == "decision"
            and relation["outcome"] in {"selected", "added", "replaced"}
            and not outputs
        ):
            raise ValueError("selected integration decision requires an output occurrence")
        if relation["kind"] == "decision" and relation["outcome"] == "rejected" and outputs:
            raise ValueError("rejected decision cannot publish an output occurrence")
    if value["kind"] == "integrated" and any(
        not any(
            r["kind"] == "decision"
            and r["outcome"] in {"selected", "added", "replaced"}
            and any(
                e["role"] == "output" and e["occurrence_id"] == occurrence_id
                for e in r["endpoints"]
            )
            for r in value["relations"]
        )
        for occurrence_id in ids
    ):
        raise ValueError("every selected occurrence requires a governing integration decision")
    coverage_ids = [c["coverage_id"] for c in value["coverage"]]
    if (
        not coverage_ids
        or len(set(coverage_ids)) != len(coverage_ids)
        or any(
            not c[k]
            for c in value["coverage"]
            for k in ("coverage_id", "scope", "family", "discovery_policy", "detail")
        )
    ):
        raise ValueError("coverage requires independently identified scope/family/policy/results")
    for coverage in value["coverage"]:
        if any(
            support["input_index"] >= len(inputs) or not support["coverage_id"]
            for support in coverage["supports"]
        ):
            raise ValueError("coverage support differs from an exact input coverage pin")
        if coverage["outcome"] == "complete":
            if observation is not None:
                raise ValueError(
                    "I10/I11 unqualified observations cannot satisfy complete source coverage"
                )
            if not coverage["supports"]:
                raise ValueError("complete coverage requires qualified input coverage attribution")
    result = PreparedIntegratedPdfProduct(
        canonical_bytes(value),
        tuple(retained[k] for k in sorted(retained)),
        context.contract_digest,
    )
    object.__setattr__(result, "_validated", True)
    return result


def store_integrated_pdf_product(
    conn: Connection,
    *,
    task_id: int,
    attempt: int,
    holder: str,
    product: PreparedIntegratedPdfProduct,
    context: PreparedPdfContext | None = None,
) -> str:
    from .contracts import require_database_operation

    archived = pdf_context_for_task(conn, task_id)
    if context is not None and context != archived:
        raise ValueError("PDF context differs from producing task release")
    archived.execution.require_operation("publish_integrated_pdf")
    if (
        archived.release_id is None
        or not product._validated
        or product.contract_digest != archived.contract_digest
    ):
        raise ValueError(
            "publication requires an immutable prepared bundle under the producing archive"
        )
    require_database_operation(conn, archived.release_id, "publish_integrated_pdf")
    return conn.execute(
        text(
            "SELECT ops.publish_integrated_pdf("
            ":task,:attempt,:holder,:contract,:payload,:artifacts)"
        ),
        dict(
            task=task_id,
            attempt=attempt,
            holder=holder,
            contract=product.contract_digest,
            payload=product.payload,
            artifacts=list(product.artifacts),
        ),
    ).scalar_one()
