"""Bounded Unicode default-folding qualification for Python/PostgreSQL identity.

No normalization is performed. PostgreSQL text excludes NUL and surrogates; the
qualification covers every remaining Unicode scalar mapping and exact sequence cases.
"""

from __future__ import annotations

import json
import platform
import sys
import unicodedata
from dataclasses import asdict, dataclass
from functools import cache
from hashlib import sha256
from typing import TYPE_CHECKING, Any

from .identity import canonical_bytes
from .refusals import SemanticOperationRefusal, SemanticReason

if TYPE_CHECKING:
    from sqlalchemy import Connection

    from .types import PreparedRelease

PROFILE = "unicode-default-casefold-1"
DOMAIN = "unicode-scalars-except-nul-no-normalization"


def identity_casefold(value: str) -> str:
    if "\0" in value or any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise SemanticOperationRefusal(
            SemanticReason(
                "unsupported_interpretation",
                "resolve_identity",
                None,
                expected=DOMAIN,
                actual="non-postgresql-text-scalar",
            )
        )
    return value.casefold()


@cache
def python_folding_mapping() -> tuple[tuple[int, str], ...]:
    return tuple(
        (code, folded)
        for code in range(1, 0x110000)
        if not 0xD800 <= code <= 0xDFFF
        for folded in (chr(code).casefold(),)
        if folded != chr(code)
    )


def _digest(mapping) -> str:
    return sha256(canonical_bytes(mapping)).hexdigest()


@cache
def python_identity_runtime() -> dict[str, str]:
    return {
        "implementation": platform.python_implementation(),
        "python": sys.version,
        "ucd": unicodedata.unidata_version,
        "mapping_digest": _digest(python_folding_mapping()),
    }


def postgres_identity_runtime(connection: Connection) -> dict[str, Any]:
    row = (
        connection.exec_driver_sql("""
        SELECT current_setting('server_version') AS server_version,
               current_setting('server_version_num') AS server_version_num,
               current_setting('server_encoding') AS encoding,
               c.collprovider::text AS provider, c.collversion AS recorded_version,
               pg_collation_actual_version(c.oid) AS actual_version
        FROM pg_collation c
        WHERE c.oid = 'pg_catalog.pg_unicode_fast'::regcollation
    """)
        .mappings()
        .one()
    )
    return dict(row)


@dataclass(frozen=True)
class UnicodeIdentityQualification:
    profile: str
    domain: str
    python: dict[str, str]
    postgres: dict[str, Any]
    mapping_digest: str
    mapping_count: int

    def content(self) -> bytes:
        return canonical_bytes(asdict(self))


def qualify_unicode_identity(connection: Connection) -> UnicodeIdentityQualification:
    """Compare the complete scalar folding relation, not a sample parity assertion."""
    postgres = postgres_identity_runtime(connection)
    if postgres["encoding"] != "UTF8" or postgres["provider"] != "b":
        raise SemanticOperationRefusal(
            SemanticReason(
                "incompatible_bindings",
                "resolve_identity",
                None,
                expected="UTF8 builtin pg_unicode_fast",
                actual=str(postgres),
            )
        )
    native = tuple(
        (row[0], row[1])
        for row in connection.exec_driver_sql("""
            SELECT code, casefold(chr(code) COLLATE pg_catalog.pg_unicode_fast)
            FROM generate_series(1, 1114111) AS scalars(code)
            WHERE code NOT BETWEEN 55296 AND 57343
              AND casefold(chr(code) COLLATE pg_catalog.pg_unicode_fast) <> chr(code)
            ORDER BY code
        """)
    )
    python = python_folding_mapping()
    if native != python:
        raise SemanticOperationRefusal(
            SemanticReason(
                "incompatible_bindings",
                "resolve_identity",
                None,
                expected=_digest(python),
                actual=_digest(native),
                detail="Python/PostgreSQL Unicode folding mappings differ",
            )
        )
    return UnicodeIdentityQualification(
        PROFILE, DOMAIN, dict(python_identity_runtime()), postgres, _digest(native), len(native)
    )


def require_unicode_identity_pair(
    connection: Connection,
    qualification: UnicodeIdentityQualification,
) -> None:
    """Admission compares exact qualified determinants; it does not re-run mapping scans."""
    if (
        qualification.profile != PROFILE
        or qualification.domain != DOMAIN
        or qualification.python != python_identity_runtime()
        or qualification.postgres != postgres_identity_runtime(connection)
        or qualification.mapping_digest != python_identity_runtime()["mapping_digest"]
        or qualification.mapping_count != len(python_folding_mapping())
    ):
        raise SemanticOperationRefusal(
            SemanticReason(
                "incompatible_bindings",
                "resolve_identity",
                None,
                expected="exact qualified Unicode runtime/collation pair",
                actual="unqualified or changed determinants",
            )
        )


# Independently qualified on 2026-11-03. This is an exact supported runtime pair,
# not a promise about other Python builds, UCDs, PostgreSQL versions or collations.
# Evidence: docs/design_review/evidence/2026-11-03_unicode-identity/records/ac03.unicode.json.
QUALIFIED_PAIR = UnicodeIdentityQualification(
    PROFILE,
    DOMAIN,
    {
        "implementation": "CPython",
        "python": "3.14.10 (main, Oct 26 2026, 14:09:22) [Clang 23.1.3 ]",
        "ucd": "16.0.0",
        "mapping_digest": "97b00ff02d8ab202d343184b422f25c8ea8e0b30db3f9334ed3b2d909a615d02",
    },
    {
        "server_version": "18.6 (Ubuntu 18.6-1.pgdg24.04+2)",
        "server_version_num": "180006",
        "encoding": "UTF8",
        "provider": "b",
        "recorded_version": "1",
        "actual_version": "1",
    },
    "97b00ff02d8ab202d343184b422f25c8ea8e0b30db3f9334ed3b2d909a615d02",
    1557,
)


def qualified_python_identity_recipe() -> bytes:
    """Producing artifacts retain only the independently qualified Python determinants."""
    if QUALIFIED_PAIR.python != python_identity_runtime():
        raise SemanticOperationRefusal(
            SemanticReason(
                "incompatible_bindings",
                "resolve_identity",
                None,
                expected="independently qualified Python Unicode runtime",
                actual="unqualified Python/UCD/build or folding mapping",
            )
        )
    return QUALIFIED_PAIR.content()


def require_current_unicode_pair(connection: Connection) -> None:
    require_unicode_identity_pair(connection, QUALIFIED_PAIR)


def requires_unicode_identity(prepared) -> bool:
    """Select folding admission from compiled identity/qualification and label bindings."""
    import json

    for definition in prepared.definitions:
        identifying = {name for group in definition.identity_groups for name in group}
        qualification = (
            definition.name == "Qualification" or "Qualification" in definition.ancestors
        )
        if any(
            prop.case_policy == "casefold"
            and (
                prop.name in identifying
                or "display" in prepared.index.property_roles.get((definition.iri, prop.iri), ())
                or (qualification and prop.key_role != "provenance")
            )
            for prop in definition.properties
        ):
            return True
    return any(
        json.loads(row.body).get("cs:case") == "casefold"
        for row in prepared.registry_rows
        if row.kind == "operation_class"
    )


def require_unicode_identity_release(connection: Connection, prepared: PreparedRelease) -> None:
    """Bind producing recipe and actual database before any current folding operation."""
    expected = qualified_python_identity_recipe().decode("utf-8")
    if json.loads(prepared.manifest)["libraries"].get("unicode-identity") != expected:
        raise SemanticOperationRefusal(
            SemanticReason(
                "incompatible_bindings",
                "resolve_identity",
                prepared.release_id,
                expected="qualified producing Unicode recipe",
                actual="missing or incompatible recipe",
            )
        )
    require_current_unicode_pair(connection)
