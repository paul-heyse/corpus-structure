"""Set adoption preserves native identity, rollback, replay and real owner fences."""

import json
from dataclasses import replace

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from semantic.pdf_companion_set_support import adopt_controlled_companions, adopt_raw_companion_set
from semantic.pdf_staging_support import private_build as private_build


def occurrence(local):
    return dict(
        occurrence_id=local,
        kind="text",
        address_space="native_item",
        precision="item",
        pointer="#/texts/0",
    )


def raw(build, local="one", ordinal=0, **changes):
    return dict(
        product_id=build.build_id,
        revision_id=build.build_id,
        family="occurrence",
        local_id=local,
        ordinal=ordinal,
        body=json.dumps(occurrence(local) | changes),
    )


@pytest.mark.parametrize(
    "mutation,reason",
    [
        ("duplicate", "duplicate key"),
        ("identity", "identity/order"),
        ("order", "identity/order"),
        ("shape", "parsing record shape differs"),
    ],
)
def test_companion_set_refusal_rolls_back_every_member(
    private_build, commit_writer_engine, commit_db_engine, mutation, reason
):
    build = private_build
    rows = [raw(build), raw(build, "two", 1)]
    if mutation == "duplicate":
        rows[1] = dict(rows[0])
    elif mutation == "identity":
        rows[1]["local_id"] = "not-the-declared-occurrence"
    elif mutation == "order":
        rows[1]["ordinal"] = 0
    else:
        rows[1] = raw(build, "two", 1, unmodeled=True)
    with (
        commit_writer_engine.begin() as connection,
        pytest.raises(DBAPIError, match=reason),
        connection.begin_nested(),
    ):
        adopt_raw_companion_set(connection, build, rows, replay_key="hostile-set")
    with commit_db_engine.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM ops.pdf_stage_companion WHERE product_id=:build"),
                {"build": build.build_id},
            )
            == 0
        )


def test_companion_set_exact_replay_is_neutral_and_changed_duplicate_refuses(
    private_build, commit_writer_engine, commit_db_engine
):
    build = private_build
    for _ in range(2):
        with commit_writer_engine.begin() as connection:
            adopt_controlled_companions(
                connection, build, "occurrence", [occurrence("one"), occurrence("two")], "same-set"
            )
    with (
        commit_writer_engine.begin() as connection,
        pytest.raises(DBAPIError, match="changed companion duplicate"),
        connection.begin_nested(),
    ):
        adopt_raw_companion_set(
            connection, build, [raw(build, "one", text="changed")], replay_key="changed"
        )
    with commit_db_engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT local_id,body FROM ops.pdf_stage_companion WHERE product_id=:build ORDER BY ordinal"
            ),
            {"build": build.build_id},
        ).all()
    assert rows == [("one", occurrence("one")), ("two", occurrence("two"))]


def test_companion_set_rechecks_owner_after_scratch_transfer(private_build, commit_writer_engine):
    build = private_build
    stale = replace(build, attempt=build.attempt + 1)
    with commit_writer_engine.begin() as connection:
        with pytest.raises(DBAPIError, match=r"stale|owned/open"), connection.begin_nested():
            adopt_raw_companion_set(connection, stale, [raw(build)], replay_key="stale-owner")
        assert (
            connection.scalar(
                text("SELECT count(*) FROM ops.pdf_stage_companion WHERE product_id=:build"),
                {"build": build.build_id},
            )
            == 0
        )
