"""Read-only full scalar mapping qualification against the configured corpus cluster."""
from dataclasses import asdict, replace
from hashlib import sha256
import json
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


def main():
    settings = Settings()
    configured = connection_settings(settings, "maintenance")
    url = make_url(configured.database.url).set(drivername="postgresql+psycopg", database=settings.database.template)
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            qualified = owner.qualify_unicode_identity(connection)
            owner.require_current_unicode_pair(connection)
            assert qualified == owner.QUALIFIED_PAIR
            cases = []
            for value, expected in EXPECTED:
                native = connection.exec_driver_sql("SELECT casefold(%s COLLATE pg_catalog.pg_unicode_fast)", (value,)).scalar_one()
                assert native == owner.identity_casefold(value) == expected
                cases.append({"input": value, "expected": expected, "native": native})
            assert cases[-1]["native"] != cases[-2]["native"]
            changed = replace(qualified, postgres={**qualified.postgres, "actual_version": "unqualified"})
            try:
                owner.require_unicode_identity_pair(connection, changed)
            except SemanticOperationRefusal as error:
                refusal = asdict(error.semantic_reason)
            else:
                raise AssertionError("unqualified pair was admitted by Python admission boundary")
            output = {
                "outcome": "passed", "qualification": asdict(qualified), "identity_cases": cases,
                "unqualified_pair_python_admission_refusal": refusal,
                "module_sha256": sha256(Path(owner.__file__).read_bytes()).hexdigest(),
                "limits": "PostgreSQL UTF8 text domain excludes NUL and surrogates. No normalization. Current native deployment adoption is separately owned.",
            }
    finally:
        engine.dispose()
    destination = Path(__file__).resolve().parents[1] / "results/qualified-pair.json"
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"outcome": output["outcome"], "mapping_digest": qualified.mapping_digest,
                      "mapping_count": qualified.mapping_count, "cases": len(cases)}))


if __name__ == "__main__":
    main()
