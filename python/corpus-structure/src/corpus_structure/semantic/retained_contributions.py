"""Exact custody reference for an independently retained source contribution."""

from typing import Annotated

from pydantic import Field

from .structural_base import StructuralValue


class RetainedContributionRef(StructuralValue):
    contribution_id: Annotated[str, Field(pattern=r"^source-contribution:[0-9a-f]{64}$")]
    project_id: Annotated[str, Field(min_length=1)]
    run_id: Annotated[int, Field(strict=True, gt=0)]
    cut_id: Annotated[int, Field(strict=True, gt=0)]
    release_id: Annotated[str, Field(min_length=1)]
    result_revision: Annotated[int, Field(strict=True, ge=0)]
    selected_task_id: Annotated[int, Field(strict=True, gt=0)]
    origin_task_id: Annotated[int, Field(strict=True, gt=0)]
    runtime_fingerprint: Annotated[str, Field(min_length=1)]
