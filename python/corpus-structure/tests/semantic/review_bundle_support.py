"""Shared controlled inputs and builders for review bundle support."""


def source_row(text="qq"):
    from hashlib import sha256

    from corpus_structure.semantic.identity import canonical_bytes

    projection = {
        "text": text,
        "pieces": [{"start": 0, "end": len(text), "item_ref": "#/texts/0"}],
        "items": ["#/texts/0"],
        "ancestors": [],
        "health": {"state": "unknown"},
    }
    return {
        "source_view_id": 1,
        "ref": {
            "id": 1,
            "key": "known",
            "document_id": 1,
            "native_product": {"task_id": 1, "product_key": "native", "content_digest": "a" * 64},
            "section_pointer": "#/texts/0",
            "membership": "direct",
            "projection_digest": sha256(canonical_bytes(projection)).hexdigest(),
            "recipe_digest": "b" * 64,
            "analysis_eligible": True,
        },
        "text": projection["text"],
        "context": {**projection, "items": [{"self_ref": "#/texts/0", "text": text}]},
    }
