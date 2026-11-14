"""Independent literal expectations shared by DDO identity controls."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextualProductVector:
    name: str
    project: str
    source: str
    scope: bytes
    literal: bytes


# Authored from ADR-0100 and the version-1 framing contract. Neither a production
# normalizer nor a production identity function constructs these expected bytes.
_PRODUCT = (
    b'["ddo","product","1",["mapping",[["body",["string","body:one"]],'
    b'["kind",["string","kind:one"]],["subject",["string","local"]],'
    b'["subject_context",["mapping",[["analyzed_scope",["mapping",'
    b'[["page",["decimal","1.25"]]]]],["original_source",["string","original:a"]],'
    b'["project_id",["string","project:a"]],["subject",["string","local"]]]]]]]]'
)

CONTEXTUAL_PRODUCTS = (
    ContextualProductVector("base", "project:a", "original:a", b'{"page":1.25}', _PRODUCT),
    ContextualProductVector(
        "other-project",
        "project:b",
        "original:a",
        b'{"page":1.25}',
        _PRODUCT.replace(b'"project:a"', b'"project:b"'),
    ),
    ContextualProductVector(
        "other-source",
        "project:a",
        "original:b",
        b'{"page":1.25}',
        _PRODUCT.replace(b'"original:a"', b'"original:b"'),
    ),
    ContextualProductVector(
        "other-scope",
        "project:a",
        "original:a",
        b'{"page":2.25}',
        _PRODUCT.replace(b'"decimal","1.25"', b'"decimal","2.25"'),
    ),
    ContextualProductVector(
        "equal-json-number",
        "project:a",
        "original:a",
        b'{"page":1.2500}',
        _PRODUCT,
    ),
)

JSON_MEANING_VECTORS = (
    ("null", ["null"]),
    ("true", ["boolean", True]),
    ('"1"', ["string", "1"]),
    ("1", ["decimal", "1"]),
    ("1.0", ["decimal", "1"]),
    ("1e6", ["decimal", "1000000"]),
    ("-0.0", ["decimal", "0"]),
    (
        '{"page":1,"slots":[false,"x",null]}',
        [
            "mapping",
            [
                ["page", ["decimal", "1"]],
                ["slots", ["sequence", [["boolean", False], ["string", "x"], ["null"]]]],
            ],
        ],
    ),
)
