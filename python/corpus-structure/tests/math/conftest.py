"""Math fixtures backed by importable spawned page workers."""

import pytest
from math_support import (
    BINDERS,
    CONSTANTS,
    DATA,
    INDEX,
    PACK_MACROS,
    S0R2_PAGES,
    SPIKE_PAGES,
    MathEnv,
    PageMath,
    analyse_all,
    coverage_all,
)


@pytest.fixture(scope="session")
def spike_pages() -> dict[str, PageMath]:
    return analyse_all(SPIKE_PAGES)


@pytest.fixture(scope="session")
def s0r2_pages() -> dict[str, PageMath]:
    return analyse_all(S0R2_PAGES)


@pytest.fixture(scope="session")
def env() -> MathEnv:
    return MathEnv(PACK_MACROS, CONSTANTS, BINDERS, DATA, INDEX)


@pytest.fixture(scope="session")
def analyse_pages():
    return analyse_all


@pytest.fixture(scope="session")
def coverage_of():
    return coverage_all
