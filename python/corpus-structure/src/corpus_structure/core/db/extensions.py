"""The expected server extensions (DA-018; D3 §3, §13; foundations §3.8): one reader for everyone.

`ops/postgresql/extensions.txt` records each extension's expected `extversion`, one
`<extension> <version>` per line. `scripts/pg_provision.sh` installs those versions in
`cs_template`; this module reads the record for `ci db init`, `open_store`'s startup check
and the test fixtures. A database whose
extensions differ is refused, naming both versions and `just db-provision`.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path

EXTENSION_RECORD = Path("ops/postgresql/extensions.txt")
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


def expected_extensions(path: Path | None = None) -> dict[str, str]:
    """The record of expected extension versions: `<extension> <version>` per line."""
    if path is None:
        path = next(
            (
                record
                for parent in Path(__file__).resolve().parents
                if (record := parent / EXTENSION_RECORD).is_file()
            ),
            None,
        )
        if path is None:
            raise FileNotFoundError(
                f"PostgreSQL extension record is unavailable: {EXTENSION_RECORD}"
            )
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
