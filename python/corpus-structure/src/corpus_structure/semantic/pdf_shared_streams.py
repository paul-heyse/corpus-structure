"""Project-scoped immutable PDF byte storage and the fixed incoming part shape."""

from pathlib import Path

from sqlalchemy import CheckConstraint, Column, MetaData, Table
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.schema import CreateTable

from .pdf_record_model import artifact_part_upload_table


def shared_streams_sql(metadata) -> str:
    upload = artifact_part_upload_table(metadata)
    pg = dialect()
    columns = ",".join(f"{pg.identifier_preparer.quote(column.name)} {column.type.compile(dialect=pg)}" for column in upload.columns)
    return Path(__file__).with_name("sql").joinpath("pdf_shared_streams.sql").read_text().replace("__PART_COLUMNS__", columns)


def part_wire_contract_sql(metadata) -> str:
    """Only a private temporary normalized wire shape, never a durable part store."""
    upload = artifact_part_upload_table(metadata)
    contract = Table(
        "pdf_part_wire_contract", MetaData(),
        *(Column(column.name, column.type, nullable=column.nullable) for column in upload.columns),
        *(CheckConstraint(str(check.sqltext), name=check.name) for check in upload.constraints if isinstance(check, CheckConstraint)),
        prefixes=["TEMPORARY"], postgresql_on_commit="DROP",
    )
    ddl = str(CreateTable(contract).compile(dialect=dialect()))
    # Compare the server-normalized columns as well as owner/constraints. This
    # contract is publisher-owned, ungranted, and cannot survive this transaction.
    expected = ",".join(
        "ROW(" + str(index) + "," + "'" + column.name + "'," + "'" + column.type.compile(dialect=dialect())
        + "'::regtype::oid,-1," + str(not column.nullable).lower() + ",'','')::text"
        for index, column in enumerate(upload.columns, 1)
    )
    return f"""
CREATE OR REPLACE FUNCTION ops.pdf_part_upload_contract() RETURNS regclass
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $wire$
DECLARE contract regclass:=to_regclass('pg_temp.pdf_part_wire_contract');
BEGIN
 IF contract IS NULL THEN {ddl}; contract:='pg_temp.pdf_part_wire_contract'::regclass; END IF;
 PERFORM ops.require_pdf_stage_scratch('pdf_part_wire_contract',contract);
 IF ARRAY(SELECT ROW(attnum,attname,atttypid,atttypmod,attnotnull,attgenerated,attidentity)::text
 FROM pg_attribute WHERE attrelid=contract AND attnum>0 AND NOT attisdropped ORDER BY attnum)
 IS DISTINCT FROM ARRAY[{expected}]::text[] THEN
 RAISE EXCEPTION 'PDF upload part contract has stale columns' USING ERRCODE='23514'; END IF;
 RETURN contract;
END $wire$;
REVOKE ALL ON FUNCTION ops.pdf_part_upload_contract() FROM PUBLIC;
"""


def part_template(relation) -> str:
    return "ops.pdf_part_upload_contract()" if relation.name == "pdf_stage_artifact_part" else f"'{relation.fullname}'::regclass"


def verified_shared_stream_ids(connection, build, descriptors):
    """A probe authenticates the current build; callers cannot name another project."""
    from . import _pdf_native_calls as calls
    from .data_operation_json import json_bytes
    from .identifiers import TaskAttempt, TaskId

    rows = tuple(descriptors)
    if not rows:
        return frozenset()
    return frozenset(row.stream_id for row in calls.probe_pdf_shared_streams(
        connection, build_id=build.build_id, task_id=TaskId(build.task_id),
        attempt=TaskAttempt(build.attempt), holder=build.holder, streams=json_bytes(rows),
    ) if row.verified)


class PdfSharedStreamTransfer:
    """Invocation-owned descriptor facts; every omission uses a fresh native probe."""

    def __init__(self):
        self.descriptors = {}

    def omit_verified_parts(self, connection, build, relations):
        for batch in relations.get("artifact_stream", ()):
            for row in batch.to_pylist():
                self.descriptors[row["stream_id"]] = row
        if set(relations) != {"artifact_part"}:
            return False
        ids = set()
        for batch in relations["artifact_part"]:
            if any(value != build.build_id for name in ("product_id", "revision_id")
                   for value in batch.column(name).to_pylist()):
                raise ValueError("shared part replay changes its owned build")
            ids.update(batch.column("stream_id").to_pylist())
        if not ids or not ids <= self.descriptors.keys():
            return False
        return ids <= verified_shared_stream_ids(connection, build, (self.descriptors[key] for key in sorted(ids)))
