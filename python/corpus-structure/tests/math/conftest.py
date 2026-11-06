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
    PageContent,
    PageExtraction,
    PageMath,
    PageReadings,
    analyse_all,
    coverage_all,
    extraction_pages,
    reading_pages,
    retained_pages,
    scoped_pages,
)


# These session products are read-only consumer inputs. A test deliberately mutating
# one must take its own copy; spawned stages retain no mutable preparation/effect state.
@pytest.fixture(scope="session")
def spike_content() -> dict[str, PageContent]:
    return retained_pages(SPIKE_PAGES)


@pytest.fixture(scope="session")
def spike_readings(spike_content: dict[str, PageContent]) -> dict[str, PageReadings]:
    return reading_pages(spike_content)


@pytest.fixture(scope="session")
def spike_extraction(spike_readings: dict[str, PageReadings]) -> dict[str, PageExtraction]:
    return extraction_pages(spike_readings)


@pytest.fixture(scope="session")
def spike_scoped(spike_extraction: dict[str, PageExtraction]) -> dict[str, PageMath]:
    return scoped_pages(spike_extraction)


@pytest.fixture(scope="session")
def s0r2_content() -> dict[str, PageContent]:
    return retained_pages(S0R2_PAGES)


@pytest.fixture(scope="session")
def s0r2_readings(s0r2_content: dict[str, PageContent]) -> dict[str, PageReadings]:
    return reading_pages(s0r2_content)


@pytest.fixture(scope="session")
def s0r2_extraction(s0r2_readings: dict[str, PageReadings]) -> dict[str, PageExtraction]:
    return extraction_pages(s0r2_readings)


@pytest.fixture(scope="session")
def s0r2_scoped(s0r2_extraction: dict[str, PageExtraction]) -> dict[str, PageMath]:
    return scoped_pages(s0r2_extraction)


@pytest.fixture(scope="session")
def env() -> MathEnv:
    return MathEnv(PACK_MACROS, CONSTANTS, BINDERS, DATA, INDEX)


@pytest.fixture(scope="session")
def analyse_pages():
    return analyse_all


@pytest.fixture(scope="session")
def coverage_of():
    return coverage_all
