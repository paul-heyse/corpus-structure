import os

import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    """Keep ordinary pytest scratch in this checkout, using pytest's own allocation."""
    config.addinivalue_line("markers", "db: uses the PostgreSQL test database")
    if config.option.basetemp is not None or "PYTEST_DEBUG_TEMPROOT" in os.environ:
        return
    root = config.rootpath / "build" / "tmp" / "pytest"
    root.mkdir(parents=True, exist_ok=True)
    environment = pytest.MonkeyPatch()
    config.add_cleanup(environment.undo)
    environment.setenv("PYTEST_DEBUG_TEMPROOT", str(root))
