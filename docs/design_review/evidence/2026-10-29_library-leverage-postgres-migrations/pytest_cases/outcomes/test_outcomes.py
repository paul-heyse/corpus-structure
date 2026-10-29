import pytest
from hypothesis import given, settings
from hypothesis import strategies as st


def test_passes():
    assert True


def test_skip_blocked():
    pytest.skip("blocked: example prerequisite absent")


@given(st.integers())
def test_profile_visible(n):
    # Records which profile governed generation when the test body ran.
    assert settings.default.derandomize is True, "ci profile not active"


@given(st.integers(min_value=0, max_value=10_000))
def test_generated_failure(n):
    assert n < 5000
