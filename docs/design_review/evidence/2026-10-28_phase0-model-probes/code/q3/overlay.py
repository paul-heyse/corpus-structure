"""Q-3 probe overlay: physical access paths bound by name to the generated tables (plan §3.4).

The model declares no index; this module owns them. It binds to tables and columns by name and fails on
a missing one (at call time here; at import in the product). The BM25 predicate's kind list is the
SEARCH_BLOCK constant generated from the search_block member property (compiler.search_block_kinds).
"""

from __future__ import annotations

from sqlalchemy import Index, MetaData, Table, and_, cast, literal, select
from sqlalchemy.dialects.postgresql import REGCONFIG
from sqlalchemy.sql.ddl import CreateView


class OverlayBindingError(LookupError):
    pass


def _t(md: MetaData, name: str) -> Table:
    if name not in md.tables:
        raise OverlayBindingError(f"overlay: no table {name}")
    return md.tables[name]


def _c(t: Table, name: str):
    if name not in t.c:
        raise OverlayBindingError(f"overlay: no column {t.fullname}.{name}")
    return t.c[name]


def apply(md: MetaData, search_block: list[str]) -> list[Index]:
    seg, task, claim = _t(md, "kb.segment"), _t(md, "ops.task"), _t(md, "kb.claim")
    s, k, c = (lambda n: _c(seg, n)), (lambda n: _c(task, n)), (lambda n: _c(claim, n))
    english = cast(literal("english"), REGCONFIG)
    return [
        Index("segment_range", s("rendition_id"), s("start_offset"), s("end_offset")),
        Index("segment_kind", s("rendition_id"), s("kind")),
        Index("segment_bm25", s("text"), postgresql_using="bm25",
              postgresql_with={"text_config": "'english'"},
              postgresql_where=and_(s("kind").in_(search_block), s("ts_config") == english)),
        Index("task_pending", k("run_id"), k("stage"), k("method_config_id"), k("priority").desc(), k("id"),
              postgresql_where=k("status") == "pending"),
        Index("task_lease", k("lease_until"), postgresql_where=k("status") == "running"),
        Index("task_agent", k("run_id"), k("priority").desc(), k("id"), postgresql_where=k("status") == "awaiting_agent"),
        Index("task_cache", k("method_config_id"), k("input_hash"),
              postgresql_where=and_(k("status").in_(["done", "empty"]), k("unit_type") != "run")),
        Index("task_run", k("run_id"), k("stage")),
        Index("claim_pred", c("run_id"), c("predicate"), c("status")),
        Index("claim_subject", c("run_id"), c("subject_id")),
        Index("claim_object", c("run_id"), c("object_entity_id")),
        Index("claim_statement", c("run_id"), c("statement_id")),
    ]


def add_view(md: MetaData, mark_info: bool) -> Table:
    """A view registered through SQLAlchemy 2.1's CreateView (the run-cut views' route)."""
    run = _t(md, "ops.run")
    cv = CreateView(select(_c(run, "id"), _c(run, "status")).where(_c(run, "status") == "finished"),
                    "finished_run", schema="ops", metadata=md)
    if mark_info:
        cv.table.info["is_view"] = True
    return cv.table
