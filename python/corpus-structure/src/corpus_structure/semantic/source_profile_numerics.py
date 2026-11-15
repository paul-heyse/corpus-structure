"""Numerical meaning of source character ratios, separate from integer counts."""

from platform import python_version
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat


class SourceRatioNumericalPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    python_version: str
    arithmetic: Literal["python-binary64-division"] = "python-binary64-division"
    decimal_places: Annotated[int, Field(ge=0, le=15)]
    rounding: Literal["python-round-nearest-ties-even-binary-input"] = "python-round-nearest-ties-even-binary-input"
    empty_denominator: Annotated[FiniteFloat, Field(ge=0, le=0)] = 0.0
    equality: Literal["canonical-exact"] = "canonical-exact"
    counts: Literal["exact-integer-interval-union"] = "exact-integer-interval-union"

    def require_runtime(self):
        if self.python_version != python_version():
            raise ValueError("source ratio policy differs from selected Python arithmetic")


def source_ratio_numerical_policy():
    from .source_profiles import SOURCE_RATIO_DECIMAL_PLACES, SOURCE_RATIO_EMPTY_FRACTION

    return SourceRatioNumericalPolicy(
        python_version=python_version(),
        decimal_places=SOURCE_RATIO_DECIMAL_PLACES,
        empty_denominator=SOURCE_RATIO_EMPTY_FRACTION,
    )
