"""Read acknowledged retained sentence bytes for the SBX partition entry check."""

import json
from collections import Counter
from hashlib import sha256
from pathlib import Path

from corpus_structure.semantic.data_operation_values import decode_semantic_value


def census():
    identity = "531b190420630bdd3146514bf9d97f6b1edf3193ce0ce97a8291e77d314cc7a0"
    namespace = Path(
        "build/data/completion-drafts/7942cfc2a5f7ebb8fbe2048e7d068f3bf5f45c90c6ec738f58d53ccd130945ac"
    )
    acknowledgement = (namespace / (identity + ".ack")).read_bytes()
    assert sha256(acknowledgement).hexdigest() == identity
    retained = json.loads(acknowledgement)
    content = (namespace / (identity + ".body")).read_bytes()
    assert len(content) == retained["request_bytes"]
    assert sha256(content).hexdigest() == retained["request_sha256"]
    request = json.loads(content)
    value = decode_semantic_value(request["completion"]["outputs"][0]["product"]["body"])
    rows, nulls, absent, fields = [], Counter(), Counter(), set()
    for block in value["blocks"]:
        annotation = block["annotation"]
        tokens, sentences = annotation["tokens"], annotation["sentences"]
        start, end = annotation["block_start"], annotation["block_end"]
        assert all(start <= sentence["start"] < sentence["end"] <= end for sentence in sentences)
        assert all(start <= token["start"] < token["end"] <= end for token in tokens)
        for token in tokens:
            if token.get("sentence") is not None:
                sentence = sentences[token["sentence"]]
                assert sentence["start"] <= token["start"] < token["end"] <= sentence["end"]
            fields.update(token)
            nulls.update(key for key, item in token.items() if item is None)
        rows.append(
            {
                "block_id": annotation["block_id"],
                "start": start,
                "end": end,
                "tokens": len(tokens),
                "sentences": len(sentences),
                "bytes": len(json.dumps(block, ensure_ascii=False, separators=(",", ":")).encode()),
            }
        )
    for block in value["blocks"]:
        for token in block["annotation"]["tokens"]:
            absent.update(fields - token.keys())

    def distribution(field):
        ordered = sorted(row[field] for row in rows)
        return {
            "total": sum(ordered),
            "min": ordered[0],
            "median": ordered[len(ordered) // 2],
            "p95": ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))],
            "max": ordered[-1],
        }

    return {
        "outcome": "passed",
        "scope": "authenticated local historical sentence answer; no native publication or full-book claim",
        "draft_id": identity,
        "request_bytes": len(content),
        "request_sha256": retained["request_sha256"],
        "blocks": len(rows),
        "block_bytes": distribution("bytes"),
        "tokens": distribution("tokens"),
        "sentences": distribution("sentences"),
        "explicit_null_token_fields": dict(nulls),
        "absent_token_fields": dict(absent),
        "largest_blocks": sorted(rows, key=lambda row: row["bytes"], reverse=True)[:5],
    }


if __name__ == "__main__":
    print(json.dumps(census(), indent=2, sort_keys=True))
