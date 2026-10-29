"""The expected server extensions (DA-018; D3 §3, §13; foundations §3.8): one reader for everyone.

`ops/postgresql/extensions.txt` records each extension's expected `extversion`, one
`<extension> <version>` per line. `scripts/pg_provision.sh` installs those versions in
`cs_template`; this module reads the record for the overlay's assertion (frozen into migration
0001), `ci db init`, `open_store`'s startup check and the test fixtures. A database whose
extensions differ is refused, naming both versions and `just db-provision`.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from pathlib import Path

EXTENSION_RECORD = Path(__file__).resolve().parents[6] / "ops" / "postgresql" / "extensions.txt"
PROVISION = "run just db-provision, then clone the database from cs_template"
FOUND = "SELECT extname, extversion FROM pg_extension"


class ExtensionVersionMismatch(RuntimeError):
    """The server's extensions differ from the record: `wrong` maps each to (expected, found)."""

    def __init__(self, wrong: Mapping[str, tuple[str, str | None]]) -> None:
        self.wrong = dict(wrong)
        listed = ", ".join(
            f"{name} {found or 'absent'} (expected {expected})"
            for name, (expected, found) in sorted(self.wrong.items())
        )
        super().__init__(f"extensions differ from {EXTENSION_RECORD.name}: {listed}: {PROVISION}")


def expected_extensions(path: Path = EXTENSION_RECORD) -> dict[str, str]:
    """The record of expected extension versions: `<extension> <version>` per line."""
    expected: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        fields = line.split("#", 1)[0].split()
        if not fields:
            continue
        if len(fields) != 2 or fields[0] in expected:
            raise ValueError(f"{path}:{number}: expected one '<extension> <version>', got {line!r}")
        expected[fields[0]] = fields[1]
    return expected


def mismatches(
    found: Iterable[tuple[str, str]], expected: Mapping[str, str] | None = None
) -> dict[str, tuple[str, str | None]]:
    """Each expected extension whose installed version (from `FOUND`'s rows) differs."""
    expected = expected_extensions() if expected is None else expected
    installed = dict(found)
    return {
        name: (version, installed.get(name))
        for name, version in expected.items()
        if installed.get(name) != version
    }


def check(found: Iterable[tuple[str, str]], expected: Mapping[str, str] | None = None) -> None:
    """Refuse with `ExtensionVersionMismatch` unless every expected version is installed."""
    wrong = mismatches(found, expected)
    if wrong:
        raise ExtensionVersionMismatch(wrong)


def _literal(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.\-]+", value):
        raise ValueError(f"unexpected extension name or version {value!r}")
    return f"'{value}'"


def assertion_sql(expected: Mapping[str, str] | None = None) -> str:
    """A `DO` block that fails (`P0001`) unless each expected extension is installed at its
    recorded version, naming the extension, both versions and `just db-provision`."""
    expected = expected_extensions() if expected is None else expected
    checks = []
    for name, version in sorted(expected.items()):
        checks.append(
            f"  SELECT extversion INTO found FROM pg_extension WHERE extname = {_literal(name)};\n"
            f"  IF found IS DISTINCT FROM {_literal(version)} THEN\n"
            f"    RAISE EXCEPTION 'extension {name} is %, expected {version}: {PROVISION}',\n"
            f"      coalesce(found, 'absent');\n"
            f"  END IF;\n"
        )
    return "DO $$\nDECLARE found text;\nBEGIN\n" + "".join(checks) + "END $$"
