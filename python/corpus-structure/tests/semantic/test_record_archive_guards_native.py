"""Current total-DDO archives preserve independent ordinary-class admission refusals."""

from dataclasses import replace
from functools import cache

import pytest
import yaml
from sqlalchemy import text

from corpus_structure.semantic.releases import ReleaseConflict, _projection_rows, persist_release
from semantic.data_operation_kernel_support import STORAGE, prepare_kernel


@cache
def control(pattern=False):
    schema=yaml.safe_load(STORAGE.schema_text)
    label=dict(range="string",required=True)
    if pattern:
        label["pattern"]="^x$"
    schema["classes"]["ArchiveIdentityControl"]=dict(attributes={
        "id":dict(range="string",identifier=True),"label":label,
    })
    # Retain the actual existing operation archive; ordinary per-class metadata is
    # also a current consumer. No operation or dummy realization is added for it.
    return prepare_kernel(replace(STORAGE,name="archive-identity-control-"+str(pattern),
        schema_text=yaml.safe_dump(schema)))


def test_archive_negative_control_has_genuine_current_operations_and_identity_metadata():
    captured=control()
    assert captured.model.operations
    identity=captured.prepared.index.definitions["ArchiveIdentityControl"].iri
    assert any(row["class_id"]==identity and row["role"]=="identity"
        for row in _projection_rows(captured.prepared)["operation_property_role"])
    # A source with an unsupported ordinary graph regex still prepares in memory.
    definition=control(True).prepared.index.definitions["ArchiveIdentityControl"]
    assert next(prop for prop in definition.properties if prop.name=="label").pattern=="^x$"


def test_current_native_archive_refuses_omitted_ordinary_identity_role_atomically(
    commit_admitter_engine,monkeypatch,
):
    from corpus_structure.semantic import releases

    captured=control()
    identity=captured.prepared.index.definitions["ArchiveIdentityControl"].iri
    original=releases._projection_rows
    def omitted_role(prepared):
        rows=original(prepared)
        before=len(rows["operation_property_role"])
        rows["operation_property_role"]=[row for row in rows["operation_property_role"]
            if not (row["class_id"]==identity and row["role"]=="identity")]
        assert len(rows["operation_property_role"])<before
        return rows
    monkeypatch.setattr(releases,"_projection_rows",omitted_role)
    with commit_admitter_engine.begin() as conn:
        with pytest.raises(ReleaseConflict,match="archived operation_property_role projection differs"),conn.begin_nested():
            persist_release(conn,captured.bundle,captured.dependencies,captured.profile,captured.prepared)
        assert conn.scalar(text("SELECT count(*) FROM sem.release_finalization WHERE release_id=:r"),
            {"r":captured.prepared.release_id})==0


def test_current_native_archive_refuses_unsupported_ordinary_regex_without_effects(
    commit_admitter_engine,
):
    captured=control(True)
    with commit_admitter_engine.begin() as conn:
        with pytest.raises(ReleaseConflict,match="unsupported required native constraint scope or pattern"),conn.begin_nested():
            persist_release(conn,captured.bundle,captured.dependencies,captured.profile,captured.prepared)
        assert conn.scalar(text("SELECT count(*) FROM sem.release_finalization WHERE release_id=:r"),
            {"r":captured.prepared.release_id})==0
