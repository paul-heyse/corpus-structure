"""Independent source/operation expectations for bounded authoring explanation."""

import json

import pytest

from corpus_structure.schema.model_explanation import (
    ModelChangeExplanation,
    explain_native_operations,
    explanation_from_native,
    explanation_page,
    sql_change,
    sql_source_fact,
)


def test_sql_predicate_change_retains_source_and_describes_edits_without_equivalence():
    old = "SELECT n AS result FROM data.items WHERE n > 1 ORDER BY n"
    new = "SELECT n AS result FROM data.items WHERE n > 2 ORDER BY n"
    change = sql_change("reader.sql", old, new)
    assert change.before is not None and change.after is not None
    assert change.before.text == old and change.after.text == new
    assert change.before.sha256 != change.after.sha256
    assert change.before.statements[0].kind == "SelectStmt"
    assert "ColumnRef" in change.before.statements[0].node_kinds
    assert change.structural_edits
    assert all(
        any(key.endswith("_reference") and value != "unavailable" for key, value in edit.items())
        for edit in change.structural_edits
    )
    assert "do not establish equivalence" in change.structural_status
    report = explanation_page(
        ModelChangeExplanation(source_basis="retained", changes=(change,)), "result"
    )
    body = json.loads(report.model_dump_json())
    assert body["items"][0]["after"]["statements"][0]["excerpt"] == new
    assert "text" not in body["items"][0]["after"]


def test_unicode_failure_retains_original_coordinate_and_unknown_template():
    source = "SELECT 'é'; SELECT FROM"
    fact = sql_source_fact("unicode.sql", source)
    assert fact.status == "refused" and fact.text == source
    assert fact.position == 22
    template = sql_source_fact("generated.sql", "SELECT {projection}")
    assert (
        template.status == "unavailable"
        and template.reason is not None
        and "unexpanded" in template.reason
    )


def test_frozen_operation_multiplicity_order_acl_and_unknown_dependency_are_preserved():
    def obj(arguments, owner):
        return dict(
            identity=dict(kind="function", schema="native test", name="f", arguments=arguments),
            catalog=dict(owner=owner, acl=[["reader", "EXECUTE", False]], body="opaque"),
            source="fixture.sql",
            statements=["SELECT 1"],
        )

    changes = [
        dict(
            version=1, before=obj(["integer"], "old"), after=obj(["integer"], "new"), recreate=False
        ),
        dict(version=1, before=obj(["text"], "old"), after=None, recreate=False),
    ]
    raw = json.dumps(dict(version=1, operations=changes)).encode()
    first = explain_native_operations(raw, "candidate", limit=1)
    assert first.total == 2 and first.next_after == 1
    assert first.items[0].identity["arguments"] == ["integer"]
    assert first.items[0].changed_properties == ("owner",)
    assert first.items[0].before_acl == [["reader", "EXECUTE", False]]
    assert first.items[0].dependencies["before"] is None
    assert explain_native_operations(raw, "candidate", after=1).items[0].action == "retire"
    assert len(explanation_from_native(raw).changes) == 2
    with pytest.raises(ValueError, match="continuation"):
        explain_native_operations(raw, "candidate", after=3)


def test_native_function_explanation_preserves_statement_boundaries_body_and_acl():
    from corpus_structure.semantic.native_candidate import definition_sql
    from corpus_structure.semantic.native_objects import NativeDefinition, NativeIdentity

    before = (
        'CREATE OR REPLACE FUNCTION "native test".f() RETURNS text LANGUAGE sql '
        "AS $body$SELECT '100%: untouched; Ω'$body$"
    )
    after = before.replace("untouched", "updated")
    owner = 'ALTER FUNCTION "native test".f() OWNER TO publisher'
    revoke = 'REVOKE ALL ON FUNCTION "native test".f() FROM PUBLIC'
    identity = NativeIdentity("function", "native test", "f")
    # The production source script keeps the existing exact termination convention.
    assert definition_sql((NativeDefinition(identity, before, "native.sql", "publisher"),)) == (
        before + ";\n" + owner + ";\n" + revoke + ";"
    )

    def obj(create):
        return dict(
            identity=identity.payload(),
            source="native.sql",
            catalog=dict(owner="publisher", acl=[["reader", "EXECUTE", False]]),
            statements=[create, owner + ";\n", revoke],
        )

    payload = dict(
        version=1,
        operations=[
            dict(
                version=1,
                before=obj(before),
                after=obj(after),
                recreate=False,
            )
        ],
    )
    raw = json.dumps(payload).encode()
    (change,) = explanation_from_native(raw).changes
    for fact, create in ((change.before, before), (change.after, after)):
        assert fact is not None
        assert fact.text == create + ";\n" + owner + ";\n" + revoke + ";"
        assert fact.status == "parsed"
        assert [statement.kind for statement in fact.statements] == [
            "CreateFunctionStmt",
            "AlterOwnerStmt",
            "GrantStmt",
        ]
        assert fact.statements[0].excerpt == create
    assert not change.structural_edits
    assert change.structural_status == "unavailable: structural diff supports single parsed SELECTs"
    (operation,) = explain_native_operations(raw, "candidate").items
    assert operation.before_owner == operation.after_owner == "publisher"
    assert operation.before_acl == operation.after_acl == [["reader", "EXECUTE", False]]
    assert json.dumps(payload).encode() == raw


@pytest.mark.parametrize("committed", [False, True])
def test_baseline_retirement_is_captured_after_index_or_commit_deletion(tmp_path, committed):
    import subprocess

    from corpus_structure.schema.model_explanation import capture_sql_changes

    def git(*args):
        return (
            subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)
            .stdout.decode()
            .strip()
        )

    git("init")
    git("config", "user.email", "fixture@example.invalid")
    git("config", "user.name", "Fixture")
    source = tmp_path / "domains/statistics/retired.sql"
    source.parent.mkdir(parents=True)
    source.write_text("SELECT 1")
    git("add", ".")
    git("commit", "-m", "original")
    baseline = git("rev-parse", "HEAD")
    git("rm", "domains/statistics/retired.sql")
    if committed:
        git("commit", "-m", "retire")
    captured = capture_sql_changes(tmp_path, baseline, ("statistics",))
    assert len(captured.changes) == 1
    assert captured.changes[0].before is not None
    assert captured.changes[0].before.text == "SELECT 1"
    assert captured.changes[0].after is None


def test_captured_sql_keeps_crlf_source_bytes_and_unchanged_identity(tmp_path):
    import subprocess
    from hashlib import sha256

    from corpus_structure.schema.model_explanation import capture_sql_changes

    def git(*args):
        return (
            subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)
            .stdout.decode()
            .strip()
        )

    git("init")
    git("config", "user.email", "fixture@example.invalid")
    git("config", "user.name", "Fixture")
    git("config", "core.autocrlf", "false")
    path = tmp_path / "domains/statistics/line-ending.sql"
    path.parent.mkdir(parents=True)
    original, changed = b"SELECT 1;\r\n", b"SELECT 2;\r\n"
    path.write_bytes(original)
    git("add", ".")
    git("commit", "-m", "CRLF source")
    baseline = git("rev-parse", "HEAD")
    assert not capture_sql_changes(tmp_path, baseline, ("statistics",)).changes
    path.write_bytes(changed)
    fact = capture_sql_changes(tmp_path, baseline, ("statistics",)).changes[0]
    assert fact.before is not None and fact.after is not None
    assert fact.before.text.encode() == original and fact.after.text.encode() == changed
    assert fact.after.sha256 == sha256(changed).hexdigest()


def test_structural_edit_serialization_survives_process_identity_and_hash_seed():
    import os
    import subprocess
    import sys

    program = """from corpus_structure.schema.model_explanation import sql_change
old = 'SELECT a, b+a AS value FROM data.x WHERE a>1 ORDER BY b'
new = 'SELECT b, a+b AS value FROM data.x WHERE a>2 ORDER BY a'
print(sql_change('selected.sql', old, new).model_dump_json())
"""
    outputs = []
    for seed in ("1", "29", "101"):
        result = subprocess.run(
            [sys.executable, "-c", program],
            capture_output=True,
            text=True,
            check=True,
            env=os.environ | {"PYTHONHASHSEED": seed},
        )
        outputs.append(result.stdout)
    assert outputs[0] == outputs[1] == outputs[2]
    assert json.loads(outputs[0])["structural_edits"]


def test_sql_view_shows_late_changed_guard_from_retained_text_without_reparse(monkeypatch):
    from corpus_structure.semantic import prepared_sql

    prefix = "-- Ω retained source\r\n" + "".join(f"SELECT {i};\r\n" for i in range(42))
    old = prefix + "SELECT n FROM data.items WHERE n > 18;\r\n"
    new = prefix + "SELECT n FROM data.items WHERE n > 19;\r\n"
    change = sql_change("closure.sql", old, new)
    monkeypatch.setattr(
        prepared_sql,
        "prepare_sql",
        lambda *args, **kwargs: pytest.fail("inspection must not reanalyze retained source"),
    )
    page = explanation_page(
        ModelChangeExplanation(source_basis="retained", changes=(change,)), "preview", limit=1
    )
    row = json.loads(page.model_dump_json())["items"][0]
    assert row["after"]["statement_total"] == 43
    assert row["after"]["statements_truncated"]
    edit = row["text_changes"]["items"][0]
    assert edit["after"]["start_line_1based"] == 44
    assert "WHERE n > 19" in edit["after"]["excerpt"]
    start, end = edit["after"]["excerpt_start_character"], edit["after"]["excerpt_end_character"]
    assert new[start:end] == edit["after"]["excerpt"]
    assert row["text_changes"]["coordinate_space"] == "original_source_text"


def test_text_display_focuses_long_changed_line_and_marks_bounds():
    from corpus_structure.schema.model_explanation import retained_text_changes

    prefix = "SELECT '" + "a" * 5000
    change = sql_change("long.sql", prefix + "old';", prefix + "new';")
    shown = retained_text_changes(change)
    body = json.loads(json.dumps(shown))
    assert "new" in body["items"][0]["after"]["excerpt"]
    assert body["items"][0]["after"]["omitted_before"]
    old = "".join(f"SELECT {i};\nSELECT 0;\n" for i in range(12))
    new = "".join(f"SELECT {i + 100};\nSELECT 0;\n" for i in range(12))
    bounded = retained_text_changes(sql_change("many.sql", old, new))
    assert bounded["truncated"] is True
    assert isinstance(bounded["items"], list) and len(bounded["items"]) == 8


def test_small_sql_page_is_not_blocked_by_full_semantic_impact():
    impact = {
        "changes": [
            {"kind": "added", "model_ref": f"Type{i}", "detail": "x" * 100000} for i in range(12)
        ],
        "inventory": {"unrelated": "y" * 200000},
    }
    explanation = ModelChangeExplanation(
        source_basis="retained", changes=(sql_change("new.sql", None, "SELECT 1"),), impact=impact
    )
    page = explanation_page(explanation, "candidate", limit=1)
    assert page.items[0]["identity"] == "new.sql"
    assert page.impact is not None
    assert page.impact["total_changes"] == 12 and page.impact["truncated"] is True
    assert len(page.model_dump_json().encode()) < 8192
    assert explanation.impact == impact


def test_large_retained_sql_facts_continue_within_the_page_byte_bound():
    sql = "\n".join("SELECT '" + "Ω" * 3000 + "';" for _ in range(8))
    explanation = ModelChangeExplanation(
        source_basis="retained",
        changes=tuple(sql_change(f"source-{i}.sql", None, sql) for i in range(8)),
    )
    identities, after = [], 0
    while True:
        page = explanation_page(explanation, "candidate", after=after, limit=8)
        assert len(page.model_dump_json().encode()) <= 128 * 1024
        identities.extend(item["identity"] for item in page.items)
        if page.next_after is None:
            break
        assert page.next_after > after
        after = page.next_after
    assert identities == [f"source-{i}.sql" for i in range(8)]
