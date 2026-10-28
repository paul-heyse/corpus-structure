"""p0q.settings-env: does validating a pydantic-settings `BaseSettings` read the environment?

Coordinator decision 26 keeps operations models (run options, method `params`) plain frozen
`BaseModel`s, never `BaseSettings`, because re-reading a stored payload through a `BaseSettings`
would mix in the current environment. This probe checks that premise under the pinned
pydantic-settings: `model_validate({})`, `model_validate({"b": 2})` and `model_validate_json("{}")`
on a `BaseSettings` with an environment value set, against the same shapes as a `BaseModel`.

Writes results/settings-env/result.json; exits 1 unless every expectation holds.
"""

from __future__ import annotations

import json
import os
import sys
from importlib.metadata import version
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

OUT = Path(__file__).resolve().parents[1] / "results" / "settings-env" / "result.json"
PREFIX = "P0Q_SETTINGS_ENV_"


class Options(BaseSettings):
    model_config = SettingsConfigDict(env_prefix=PREFIX, frozen=True)

    a: int = 0
    b: int = 0


class PlainOptions(BaseModel):
    a: int = 0
    b: int = 0


def main() -> int:
    for name in [n for n in os.environ if n.startswith(PREFIX)]:
        del os.environ[name]
    os.environ[f"{PREFIX}A"] = "1"  # the "current environment" a stored payload must not absorb

    cases = {
        "model_validate({})": (lambda c: c.model_validate({})),
        'model_validate({"b": 2})': (lambda c: c.model_validate({"b": 2})),
        'model_validate_json("{}")': (lambda c: c.model_validate_json("{}")),
    }
    # Expected per the hypothesis: the BaseSettings picks up a=1 from the environment in every
    # case; the BaseModel keeps the default a=0. A stored "b" survives either way.
    expected = {
        "model_validate({})": ({"a": 1, "b": 0}, {"a": 0, "b": 0}),
        'model_validate({"b": 2})': ({"a": 1, "b": 2}, {"a": 0, "b": 2}),
        'model_validate_json("{}")': ({"a": 1, "b": 0}, {"a": 0, "b": 0}),
    }
    rows = []
    for label, call in cases.items():
        settings, plain = call(Options).model_dump(), call(PlainOptions).model_dump()
        want_settings, want_plain = expected[label]
        rows.append(
            {
                "call": label,
                "environment": {f"{PREFIX}A": "1"},
                "base_settings": settings,
                "base_model": plain,
                "base_settings_reads_environment": settings["a"] == 1,
                "as_expected": settings == want_settings and plain == want_plain,
            }
        )
    result = {
        "probe": "p0q.settings-env",
        "versions": {
            "python": sys.version.split()[0],
            "pydantic": version("pydantic"),
            "pydantic-settings": version("pydantic-settings"),
        },
        "cases": rows,
        "all_read_environment": all(r["base_settings_reads_environment"] for r in rows),
        "all_as_expected": all(r["as_expected"] for r in rows),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["all_as_expected"] else 1


if __name__ == "__main__":
    sys.exit(main())
