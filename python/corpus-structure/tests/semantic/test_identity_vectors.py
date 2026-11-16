"""Hand-authored complete semantic-key vectors and one assembled native/read journey."""

from __future__ import annotations

import json
from decimal import Decimal
from hashlib import sha256

import pytest

from corpus_structure.semantic.identity import fact_key, occurrence_key


@pytest.mark.parametrize(
    "release,realization,subject,predicate,object_value,object_meaning,qualification,qualification_meaning,preimage,digest",
    [
        (
            "release:vector",
            "realization:vector",
            "entity:alice",
            "https://example.test/name",
            "Alice",
            ["string", "Alice"],
            {"modality": "asserted", "polarity": True},
            ["mapping", [["modality", ["string", "asserted"]], ["polarity", ["boolean", True]]]],
            b'["release:vector","realization:vector","entity:alice","https://example.test/name",["string","Alice"],["mapping",[["modality",["string","asserted"]],["polarity",["boolean",true]]]]]',
            "d54e7c32ddcaf0c1c7889a13bfee2d6645517a4648f9a7bfdfe03d07d9029f9a",
        ),
        (
            "release:other",
            "realization:vector",
            "entity:alice",
            "https://example.test/name",
            "Alice",
            ["string", "Alice"],
            {"modality": "asserted", "polarity": True},
            ["mapping", [["modality", ["string", "asserted"]], ["polarity", ["boolean", True]]]],
            b'["release:other","realization:vector","entity:alice","https://example.test/name",["string","Alice"],["mapping",[["modality",["string","asserted"]],["polarity",["boolean",true]]]]]',
            "79025025c9bfb0113caca09c230589b20d496cc2d21a2fbbada34f34e18bb7e7",
        ),
        (
            "release:vector",
            "realization:other",
            "entity:alice",
            "https://example.test/name",
            "Alice",
            ["string", "Alice"],
            {"modality": "asserted", "polarity": True},
            ["mapping", [["modality", ["string", "asserted"]], ["polarity", ["boolean", True]]]],
            b'["release:vector","realization:other","entity:alice","https://example.test/name",["string","Alice"],["mapping",[["modality",["string","asserted"]],["polarity",["boolean",true]]]]]',
            "16dddabca40cb642e9481db8452447d2a471c1397cce03f933298998a65e2bab",
        ),
        (
            "release:vector",
            "realization:vector",
            "entity:bob",
            "https://example.test/name",
            "Alice",
            ["string", "Alice"],
            {"modality": "asserted", "polarity": True},
            ["mapping", [["modality", ["string", "asserted"]], ["polarity", ["boolean", True]]]],
            b'["release:vector","realization:vector","entity:bob","https://example.test/name",["string","Alice"],["mapping",[["modality",["string","asserted"]],["polarity",["boolean",true]]]]]',
            "5f42e923916b151748cd4ad8aafec7b7b6937cefeddd04dee3db0ff3fec65af0",
        ),
        (
            "release:vector",
            "realization:vector",
            "entity:alice",
            "https://example.test/label",
            "Alice",
            ["string", "Alice"],
            {"modality": "asserted", "polarity": True},
            ["mapping", [["modality", ["string", "asserted"]], ["polarity", ["boolean", True]]]],
            b'["release:vector","realization:vector","entity:alice","https://example.test/label",["string","Alice"],["mapping",[["modality",["string","asserted"]],["polarity",["boolean",true]]]]]',
            "0f67a32a063735b7ffd09d2e4b207718e8d2ad2cba205048140e11d531e38460",
        ),
        (
            "release:vector",
            "realization:vector",
            "entity:alice",
            "https://example.test/name",
            "Alice",
            ["string", "Alice"],
            {"modality": "inferred", "polarity": True},
            ["mapping", [["modality", ["string", "inferred"]], ["polarity", ["boolean", True]]]],
            b'["release:vector","realization:vector","entity:alice","https://example.test/name",["string","Alice"],["mapping",[["modality",["string","inferred"]],["polarity",["boolean",true]]]]]',
            "0c869d27400457809cdbf9cf290ae36ecd9fc4e6956b7538a1a8be6f4c00c9f5",
        ),
        (
            "release:vector",
            "realization:vector",
            "entity:alice",
            "https://example.test/value",
            Decimal("1.2300"),
            ["decimal", "1.23"],
            {},
            ["mapping", []],
            b'["release:vector","realization:vector","entity:alice","https://example.test/value",["decimal","1.23"],["mapping",[]]]',
            "270222d4bd208bcda866f56c4ab1c144b086d54698381192b899e1389de7ef51",
        ),
        (
            "release:vector",
            "realization:vector",
            "entity:alice",
            "https://example.test/value",
            -0.0,
            ["float", "-0x0.0p+0"],
            {},
            ["mapping", []],
            b'["release:vector","realization:vector","entity:alice","https://example.test/value",["float","-0x0.0p+0"],["mapping",[]]]',
            "aa39f1f6d16893171549575f8c9d0a0341025ead8d554bd55fa7207be8c058c2",
        ),
    ],
)
def test_fact_key_complete_hand_authored_vectors(
    release,
    realization,
    subject,
    predicate,
    object_value,
    object_meaning,
    qualification,
    qualification_meaning,
    preimage,
    digest,
):
    expected = json.dumps(
        [release, realization, subject, predicate, object_meaning, qualification_meaning],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    assert expected == preimage
    assert sha256(preimage).hexdigest() == digest
    assert fact_key(release, realization, subject, predicate, object_value, qualification) == (
        "fact:" + digest
    )


@pytest.mark.parametrize(
    "source,item,preimage,digest",
    [
        (
            "source:book",
            "item:3",
            b'["release:vector","realization:vector","source:book","item:3"]',
            "178f2e74ce08dc53510f0ac1a04c23e92009aaa272255f9568b1d3821b940b95",
        ),
        (
            "source:journal",
            "item:3",
            b'["release:vector","realization:vector","source:journal","item:3"]',
            "8f71567e8e376fa1c2370e7b1aff11fdc189a3f843e1d7336a3745a49a46ba11",
        ),
        (
            "source:book",
            "item:4",
            b'["release:vector","realization:vector","source:book","item:4"]',
            "1ac6c16ad9acc250193ab82a87787b68a3fb21fb6bad917fb888084d8bc9354e",
        ),
    ],
)
def test_occurrence_key_complete_hand_authored_vectors(source, item, preimage, digest):
    expected = json.dumps(
        ["release:vector", "realization:vector", source, item],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    assert expected == preimage
    assert sha256(preimage).hexdigest() == digest
    assert occurrence_key("release:vector", "realization:vector", source, item) == ("occ:" + digest)


@pytest.mark.parametrize("support_field", ["evidence", "confidence", "supports"])
def test_support_and_assessment_fields_are_not_fact_qualification(support_field):
    with pytest.raises(ValueError, match="support/assessment fields"):
        fact_key("r", "z", "s", "p", "value", {support_field: "separate"})


PREDICATE = "https://example/label"
