"""P5: Hypothesis 6.170.12 with Pydantic 2.14.1 models and a canonical-JSON key function.

Questions:
  a. Does ``st.from_type(Model)`` / ``st.builds(Model)`` honour field constraints (Field(ge=..),
     Annotated[..., Len], Literal, discriminated unions, nested models), or produce invalid input?
  b. Recursive JSON strategy + permutation invariance: a key over sorted-key canonical JSON is
     equal for permuted dict insertion order and reordered ``and`` arguments (D9 §4 property).
  c. Settings profiles and deadlines: register/load a CI profile.

Run (root .venv: hypothesis==6.170.12, pydantic==2.14.1):
    .venv/bin/python -I probes/p5_hypothesis_pydantic.py
"""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal, Union

from annotated_types import Len
from hypothesis import HealthCheck, given, settings, strategies as st
from pydantic import BaseModel, Field, ValidationError


class Phrase(BaseModel):
    op: Literal["phrase"]
    text: Annotated[str, Len(min_length=1)]


class Cmp(BaseModel):
    op: Literal["lt", "le", "eq"]
    lhs: str
    rhs: str


class And(BaseModel):
    op: Literal["and"]
    args: Annotated[list[Union[Phrase, Cmp, "And"]], Len(min_length=2)]


Node = Annotated[Union[Phrase, Cmp, And], Field(discriminator="op")]


class Claim(BaseModel):
    local_ref: Annotated[str, Field(pattern=r"^C[0-9]+$")]
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    conditions: Node | None = None


def tally(strategy, model, n=200):
    ok = bad = 0

    @settings(max_examples=n, database=None, suppress_health_check=list(HealthCheck), deadline=None)
    @given(strategy)
    def run(x):
        nonlocal ok, bad
        try:
            model.model_validate(x.model_dump() if isinstance(x, BaseModel) else x)
            ok += 1
        except ValidationError:
            bad += 1

    try:
        run()
        return {"valid": ok, "invalid": bad}
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {str(e)[:160]}"}


def canonical(obj) -> bytes:
    """Stand-in for D1 §10.1: sorted keys, no whitespace, UTF-8; 'and' args sorted canonically."""
    def norm(x):
        if isinstance(x, dict):
            x = {k: norm(v) for k, v in x.items()}
            if x.get("op") == "and":
                x["args"] = sorted(x["args"], key=lambda a: json.dumps(a, sort_keys=True))
            return x
        if isinstance(x, list):
            return [norm(v) for v in x]
        return x
    return json.dumps(norm(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def key(obj) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


json_values = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text(),
    lambda kids: st.lists(kids, max_size=4) | st.dictionaries(st.text(max_size=5), kids, max_size=4),
    max_leaves=20,
)


@st.composite
def permuted_pair(draw):
    v = draw(json_values)

    def shuffle(x):
        if isinstance(x, dict):
            items = draw(st.permutations([(k, shuffle(w)) for k, w in x.items()]))
            return dict(items)
        if isinstance(x, list):
            return [shuffle(w) for w in x]
        return x

    return v, shuffle(v)


leaf = st.builds(dict, op=st.just("lt"), lhs=st.sampled_from("abxy"), rhs=st.sampled_from("0123"))


@st.composite
def and_reordered(draw):
    args = draw(st.lists(leaf, min_size=2, max_size=5))
    return {"op": "and", "args": args}, {"op": "and", "args": draw(st.permutations(args))}


def main():
    settings.register_profile("ci", max_examples=300, deadline=None, derandomize=True, database=None,
                              print_blob=True)
    settings.register_profile("dev", max_examples=50, deadline=500)
    settings.load_profile("ci")
    out = {
        "from_type_Claim": tally(st.from_type(Claim), Claim),
        "builds_Claim": tally(st.builds(Claim), Claim),
        "from_type_And": tally(st.from_type(And), And),
        "profile_loaded": settings.default.max_examples,
    }

    @given(permuted_pair())
    def perm_invariant(pair):
        a, b = pair
        assert key(a) == key(b)

    @given(and_reordered())
    def and_invariant(pair):
        a, b = pair
        assert key(a) == key(b)

    for name, test in (("dict_permutation_invariance", perm_invariant), ("and_reorder_invariance", and_invariant)):
        try:
            test()
            out[name] = "passed"
        except AssertionError as e:
            out[name] = f"failed: {e}"
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
