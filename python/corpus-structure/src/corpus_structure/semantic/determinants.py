"""One owner of release-producing and runtime-acceptance determinants."""

import sys
from importlib.metadata import version

_BASE_BYTE_LIBRARIES = (
    "linkml",
    "linkml-runtime",
    "pydantic",
    "rdflib",
    "pyshacl",
    "oaklib",
    "linkml-term-validator",
    "valuesets",
    "pyoxigraph",
    "jsonschema",
    "cattrs",
)
SCIENTIFIC_LIBRARIES = ("sympy", "rule-engine", "numpy", "lark", "regex")
BYTE_LIBRARIES = (*_BASE_BYTE_LIBRARIES, "pydantic-core", *SCIENTIFIC_LIBRARIES, "python")
BOUNDARY_LIBRARIES = ("python", "pydantic", "pydantic-core", "jsonschema", "cattrs")
DEPLOYMENT_LIBRARIES = ("sqlalchemy", "psycopg", "pglast", "alembic")


def determinant_version(name: str) -> str:
    return sys.version if name == "python" else version(name)


def boundary_compatible(recorded: dict[str, str], compiler: str) -> bool:
    return compiler == "14" and all(
        recorded.get(name) == determinant_version(name) for name in BOUNDARY_LIBRARIES
    )


def scientific_compatible(recorded: dict[str, str]) -> bool:
    return all(recorded.get(name) == determinant_version(name) for name in SCIENTIFIC_LIBRARIES)
