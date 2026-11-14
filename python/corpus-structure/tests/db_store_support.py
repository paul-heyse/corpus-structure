"""Shared controlled inputs and builders for db store support."""

from __future__ import annotations

from sqlalchemy import Engine
from sqlalchemy.engine import make_url

from corpus_structure.settings import Settings


def settings_for(engine: Engine) -> Settings:
    url = make_url(engine.url).set(drivername="postgresql")
    return Settings(database={"url": url.render_as_string(hide_password=False)})
