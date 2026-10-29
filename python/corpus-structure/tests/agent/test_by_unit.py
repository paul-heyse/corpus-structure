"""`agent_reuse: by_unit` on a fixture guideline (P0-A-1; agent interface §3.2, §6; DA-017).
Guideline v1 is frozen for phase 0, so the fixture is the statistics guideline with section 10.4
declared to apply to definition units only. A run under `by_unit` completes the five trace units;
after an edit to 10.4, a second run reuses exactly the units whose recorded features exclude 10.4 (a
statement kind other than definition) and asks again for the rest: definition units, and units that
record no statement kind (they cannot exclude it)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import Engine, text

from corpus_structure.intervene.testing import submit_batches
from corpus_structure.methods.llm import parts as parts_

DECLARED = "<!-- core -->\n<!-- applies: statement_kind=definition -->\n"


def guideline(agent: SimpleNamespace, version: int, extra: str = "") -> str:
    base = (agent.STATISTICS / "guideline.md").read_text(encoding="utf-8")
    base = base.replace("# Annotation guideline v1", f"# Annotation guideline v{version}", 1)
    head = "## 10.4 Entities\n<!-- core -->\n"
    assert base.count(head) == 1
    return base.replace(head, "## 10.4 Entities\n" + DECLARED + extra, 1)


@pytest.fixture(scope="module")
def by_unit_world(
    world_engine: Engine, tmp_path_factory: pytest.TempPathFactory
) -> SimpleNamespace:
    return SimpleNamespace(engine=world_engine, tmp=tmp_path_factory.mktemp("by_unit"))


def test_a_section_edit_asks_again_only_where_it_applies(
    agent: SimpleNamespace, by_unit_world: SimpleNamespace
) -> None:
    w = agent.build_world(by_unit_world.engine, by_unit_world.tmp, guideline=guideline(agent, 1))
    first = agent.start_run(w, agent_reuse="by_unit")
    tools = agent.tools(w.engine)
    batches = {
        agent.s0(n)["unit_key"]: (agent.s0(n)["batch"], agent.s0(n)["frame"])
        for n in agent.TRACE_UNITS
    }
    assert {r.status for r in submit_batches(tools.server, first, batches).values()} == {"done"}

    edited = guideline(agent, 2, "Entities of definition units carry their defining sentence.\n")
    (w.pack / "guideline.md").write_text(edited, encoding="utf-8")
    second = agent.start_run(w, agent_reuse="by_unit")
    with w.engine.connect() as conn:
        assert (
            conn.execute(
                text(
                    "SELECT count(DISTINCT guideline_version_id) FROM ops.run WHERE id IN (:a, :b)"
                ),
                {"a": first, "b": second},
            ).scalar_one()
            == 2
        )
        statuses = dict(
            conn.execute(
                text(
                    "SELECT t.unit_key, t.status FROM ops.task t JOIN ops.method_config c ON c.id "
                    "= "
                    "t.method_config_id JOIN ops.method m ON m.id = c.method_id WHERE m.name = "
                    "'agent.opus' AND t.run_id = :r"
                ),
                {"r": second},
            ).all()
        )
    section = next(s for s in parts_.sections(edited) if s.id == "10.4")
    expected = {}
    for key in statuses:
        from corpus_structure.core.locators import LocatorIndex
        from corpus_structure.core.locators import parse as parse_locator

        page = parse_locator(key).page
        content = agent.page_content(page)
        features = parts_.unit_features(LocatorIndex(content, page).resolve(key))
        expected[key] = "awaiting_agent" if parts_.applies(section, features) else "reused"
    assert statuses == expected
    assert set(expected.values()) == {"awaiting_agent", "reused"}  # both outcomes occur
