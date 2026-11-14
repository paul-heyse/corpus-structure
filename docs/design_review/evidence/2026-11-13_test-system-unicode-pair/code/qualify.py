"""Read-only Unicode requalification after the PostgreSQL 18.7 host update."""

import json
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from corpus_structure.semantic import unicode_identity as owner
from corpus_structure.semantic.refusals import SemanticOperationRefusal
from corpus_structure.semantic.runtime import connection_settings
from corpus_structure.settings import Settings

EXPECTED = (
    ("Straße", "strasse"),
    ("Σςσ", "σσσ"),
    ("İIı", "i\u0307iı"),
    ("ﬃ", "ffi"),
    ("É", "é"),
    ("E\u0301", "e\u0301"),
)


def refused(connection, qualification):
    try:
        owner.require_unicode_identity_pair(connection, qualification)
    except SemanticOperationRefusal as error:
        return asdict(error.semantic_reason)
    raise AssertionError("Changed runtime determinants were admitted")


def main():
    folder = Path(__file__).resolve().parents[1]
    settings = Settings()
    configured = connection_settings(settings, "maintenance")
    url = make_url(configured.database.url).set(
        drivername="postgresql+psycopg", database=settings.database.template
    )
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            qualified = owner.qualify_unicode_identity(connection)
            owner.require_unicode_identity_pair(connection, qualified)
            cases = []
            for value, expected in EXPECTED:
                native = connection.exec_driver_sql(
                    "SELECT casefold(%s COLLATE pg_catalog.pg_unicode_fast)", (value,)
                ).scalar_one()
                assert native == owner.identity_casefold(value) == expected
                cases.append({"input": value, "expected": expected, "native": native})
            assert cases[-1]["native"] != cases[-2]["native"]
            changed = replace(
                qualified, postgres={**qualified.postgres, "actual_version": "unqualified"}
            )
            output = {
                "outcome": "passed",
                "qualification": asdict(qualified),
                "identity_cases": cases,
                "changed_determinant_refusal": refused(connection, changed),
                "previous_pair_refusal": refused(connection, owner.QUALIFIED_PAIR),
                "module_sha256": sha256(Path(owner.__file__).read_bytes()).hexdigest(),
                "limits": "Read-only template connection; no schema, deployment, activation or normalization. PostgreSQL UTF8 text excludes NUL and surrogates.",
            }
    finally:
        engine.dispose()
    destination = folder / "results/qualified-pair.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    snapshot = folder / "inputs/unicode_identity.before.py"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_bytes(Path(owner.__file__).read_bytes())
    print(json.dumps({
        "outcome": output["outcome"],
        "postgres": qualified.postgres,
        "mapping_digest": qualified.mapping_digest,
        "mapping_count": qualified.mapping_count,
        "independent_cases": len(cases),
    }))


if __name__ == "__main__":
    main()
