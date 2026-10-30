"""One owner of release-producing and runtime-acceptance determinants."""

import platform
import sys
from importlib.metadata import version

BYTE_LIBRARIES_V11 = (
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
BYTE_LIBRARIES = (*BYTE_LIBRARIES_V11, "pydantic-core", *SCIENTIFIC_LIBRARIES, "python")
BOUNDARY_LIBRARIES = ("python", "pydantic", "pydantic-core", "jsonschema", "cattrs")
DEPLOYMENT_LIBRARIES = ("sqlalchemy", "psycopg", "pglast", "alembic")


def determinant_version(name: str) -> str:
    return sys.version if name == "python" else version(name)


def boundary_compatible(recorded: dict[str, str], compiler: str) -> bool:
    required = (
        BOUNDARY_LIBRARIES if compiler in {"12", "13"} else ("pydantic", "jsonschema", "cattrs")
    )
    if compiler == "10":
        required = (*required, "linkml-runtime")
    if compiler in {"10", "11"} and (
        version("pydantic-core") != "2.50.1" or platform.python_version() != "3.14.10"
    ):
        # Those archives predate an explicit core determinant. Preserve only the
        # validated historical boundary tuple, never infer compatibility from JSON Schema.
        return False
    return all(recorded.get(name) == determinant_version(name) for name in required)


def scientific_compatible(recorded: dict[str, str]) -> bool:
    return all(recorded.get(name) == determinant_version(name) for name in SCIENTIFIC_LIBRARIES)
