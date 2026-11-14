"""Shared controlled inputs and builders for pdf reconciliation support."""

from hashlib import sha256

from semantic.pdf_integration_support import observation


def recognized(source, raw, *, role="A", page=1):
    value = observation(source, pass_role=role)
    value["observation"]["raw_response_digest"] = sha256(raw).hexdigest()
    value["observation"]["image"].update(page_no=page, width=200, height=300)
    value["observation"]["image"]["transform"] = {
        "status": "coarse",
        "normalization": "none",
        "source_space": "pdf_points",
        "target_space": "submitted_pixels",
        "page_width": 200.0,
        "page_height": 300.0,
        "page_rotation": 0,
        "crop_left": 0.0,
        "crop_top": 0.0,
        "crop_right": 200.0,
        "crop_bottom": 300.0,
        "affine": [1.0, 0.0, 0.0, 1.0, 0.0, 0.0],
    }
    value["occurrences"] = [
        {
            "occurrence_id": f"block-{i}",
            "kind": "text",
            "address_space": "recognized_text",
            "precision": "block",
            "page_no": page,
        }
        for i in range(raw.count(b"<class_"))
    ]
    value["coverage"][0].update(scope=f"page:{page}", family="nemotron-pass-" + role)
    return value
