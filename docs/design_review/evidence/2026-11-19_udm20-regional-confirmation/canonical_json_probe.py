"""Read-only exact-byte parity for compacting object-free native JSON values."""

import json
from pathlib import Path
from time import monotonic

from corpus_structure.semantic.metadata import table
from sqlalchemy import Text, bindparam, cast, create_engine, func, select, text
from sqlalchemy.dialects.postgresql import JSONB, JSONPATH
from sqlalchemy.engine import URL

FOLDER = Path(__file__).resolve().parent
INTENT = "intent:ef53de69dd57c40b12885f52e5c8be054e7f29a766e907b2b095ea07bb7132a6"
PATTERN = r'("(?:[^"\\]|\\.)*")|[[:space:]]+'
OBJECTS = cast('$.** ? (@.type() == "object")', JSONPATH)
engine = create_engine(
    URL.create(
        "postgresql+psycopg",
        username="paul",
        database="corpus_structure_ddo_stage",
        query={"host": "/var/run/postgresql", "port": "5434"},
    )
)
result = {
    "scope": "rollback-only read of exact retained body and independent Unicode/escape controls, no installed function changes",
    "intent": INTENT,
    "pattern": PATTERN,
    "controls": [],
}
try:
    with engine.connect() as c:
        tx = c.begin()
        try:
            c.execute(text("SET LOCAL statement_timeout='90s'"))
            p = bindparam("p", type_=JSONB)
            contains = func.jsonb_path_exists(p, OBJECTS)
            compact = func.regexp_replace(cast(p, Text), PATTERN, r"\1", "g")
            actual = func.data.canonical_json(p)
            controls = [
                None,
                True,
                17,
                -5,
                1.5,
                " a \t b\n c ",
                ["tabs\tand newlines\n", 'quotes " and slash \\', "雪 Ω \u2028 end"],
                [
                    "mapping",
                    [
                        ["short", ["string", "a b"]],
                        [
                            "long key",
                            ["sequence", [["integer", "10"], ["string", '\\" \\ "/']]],
                        ],
                    ],
                ],
                [],
                [{"long": 1, "a": " spaced "}],
                {"z": [], "a": "é  Ω"},
            ]
            query = select(
                contains.label("object_present"),
                compact.label("compact"),
                actual.label("canonical"),
            )
            for value in controls:
                observed = c.execute(query, {"p": value}).one()
                expected = json.dumps(
                    value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                )
                assert observed.canonical == expected, (
                    value,
                    observed.canonical,
                    expected,
                )
                if not observed.object_present:
                    assert observed.compact == expected, (
                        value,
                        observed.compact,
                        expected,
                    )
                result["controls"].append(
                    {
                        "input": value,
                        "object_present": observed.object_present,
                        "exact_parity": None
                        if observed.object_present
                        else observed.compact == observed.canonical,
                    }
                )
            intents = table("ops.data_completion_intent")
            value = intents.c.payload["outputs"][0]["product"]["body"]
            selection = intents.c.id == INTENT
            body = c.execute(
                select(
                    func.octet_length(cast(value, Text)),
                    func.jsonb_path_exists(value, OBJECTS),
                ).where(selection)
            ).one()
            assert body[1] is False
            observations = {}
            for name, expression in [
                ("current", func.data.canonical_json(value)),
                (
                    "compacted",
                    func.regexp_replace(cast(value, Text), PATTERN, r"\1", "g"),
                ),
            ]:
                start = monotonic()
                row = c.execute(
                    select(
                        func.octet_length(expression),
                        func.encode(
                            func.sha256(func.convert_to(expression, "UTF8")), "hex"
                        ),
                    ).where(selection)
                ).one()
                observations[name] = {
                    "bytes": row[0],
                    "sha256": row[1],
                    "seconds": monotonic() - start,
                }
            assert (
                observations["current"]["bytes"] == observations["compacted"]["bytes"]
            )
            assert (
                observations["current"]["sha256"] == observations["compacted"]["sha256"]
            )
            result.update(
                outcome="passed",
                body_jsonb_text_bytes=body[0],
                body_contains_objects=body[1],
                observations=observations,
            )
        finally:
            tx.rollback()
            result["rolled_back"] = True
finally:
    engine.dispose()
    (FOLDER / "raw/canonical-json-parity.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
print(json.dumps({k: v for k, v in result.items() if k != "controls"}))
