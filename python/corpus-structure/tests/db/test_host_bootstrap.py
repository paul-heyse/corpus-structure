"""Independent host provisioning expectations; role effects roll back completely."""

from dataclasses import replace
from uuid import uuid4

import pytest
from pglast import ast, enums, parse_plpgsql, parse_sql
from pglast.stream import RawStream
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.db import host_bootstrap as host
from corpus_structure.semantic.native_objects import execute_native_sql


def test_host_principals_and_peer_files_correspond_to_declared_capabilities():
    assert [(role.purpose, role.name) for role in host.PRINCIPALS] == [
        ("publisher", "corpus_sem_publisher"),
        ("write", "corpus_sem_writer"),
        ("read", "corpus_sem_reader"),
        ("evaluate", "corpus_sem_evaluator"),
        ("fit", "corpus_sem_fitter"),
        ("admit", "corpus_sem_admitter"),
    ]
    assert host.peer_hba() == (
        "local all corpus_sem_writer,corpus_sem_reader,corpus_sem_evaluator,"
        "corpus_sem_fitter,corpus_sem_admitter peer map=corpus_semantic"
    )
    assert host.peer_hba(fitter_only=True) == "local all corpus_sem_fitter peer map=corpus_semantic"
    assert host.peer_ident("paul", fitter_only=True) == "corpus_semantic paul corpus_sem_fitter"
    assert len(host.peer_ident("paul").splitlines()) == 5
    with pytest.raises(ValueError, match="operator"):
        host.peer_ident("user name")


def test_host_renderers_quote_values_and_keep_exact_extension_versions():
    def option(options):
        assert options
        entry = options[0]
        assert isinstance(entry, ast.DefElem) and isinstance(entry.arg, ast.String)
        return entry.defname, entry.arg.sval

    create = parse_sql(host.sql_command("database-create", ["odd DB", "owner's X"]))[0].stmt
    assert isinstance(create, ast.CreatedbStmt)
    assert create.dbname == "odd DB" and option(create.options)[1] == "owner's X"
    scripts = parse_sql(host.sql_command("extension-install", ["vector", "0.8.7"]))
    assert len(scripts) == 3
    install, update = scripts[1].stmt, scripts[2].stmt
    assert isinstance(install, ast.CreateExtensionStmt)
    assert install.if_not_exists and install.extname == "vector"
    assert option(install.options)[1] == "0.8.7"
    assert isinstance(update, ast.AlterExtensionStmt)
    assert option(update.options)[1] == "0.8.7"
    template = parse_sql(host.sql_command("template", ["cs_template"]))[0].stmt
    assert isinstance(template, ast.AlterDatabaseStmt)
    assert option(template.options) == ("is_template", "true")
    for script in (
        host.semantic_roles("paul"),
        host.base_roles("paul"),
        host.sql_command("auth-check", []),
    ):
        assert isinstance(parse_sql(script)[0].stmt, ast.DoStmt)
        assert parse_plpgsql(script)
    setting = parse_sql(host.sql_command("setting", ["data_checksums"]))[0].stmt
    assert isinstance(setting, ast.VariableShowStmt) and setting.name == "data_checksums"


def test_generated_purpose_provisioning_is_idempotent_and_fitter_refuses_widened_rights(
    infrastructure_rollback, monkeypatch
):
    prefix = "host_" + uuid4().hex[:12]
    principals = tuple(replace(role, name=prefix + "_" + role.purpose) for role in host.PRINCIPALS)
    monkeypatch.setattr(host, "PRINCIPALS", principals)
    monkeypatch.setattr(host, "PUBLISHER", principals[0].name)
    connection = infrastructure_rollback
    transaction = connection.begin_nested()
    try:
        operator = connection.execute(select(func.current_user())).scalar_one()
        script = host.semantic_roles(operator)
        execute_native_sql(connection, script)
        execute_native_sql(connection, script)
        records = (
            connection.execute(
                select(host.ROLES).where(
                    host.ROLES.c.rolname.in_(tuple(role.name for role in principals))
                )
            )
            .mappings()
            .all()
        )
        by_name = {row["rolname"]: row for row in records}
        assert len(by_name) == 6
        for principal in principals:
            observed = by_name[principal.name]
            assert observed["rolcanlogin"] == principal.login
            assert not any(
                observed[name]
                for name in (
                    "rolsuper",
                    "rolcreatedb",
                    "rolcreaterole",
                    "rolreplication",
                    "rolbypassrls",
                )
            )
        membership = connection.execute(
            text(
                "SELECT m.inherit_option,m.set_option FROM pg_auth_members m "
                "JOIN pg_roles r ON r.oid=m.roleid JOIN pg_roles u ON u.oid=m.member "
                "WHERE r.rolname=:publisher AND u.rolname=:operator"
            ),
            {"publisher": principals[0].name, "operator": operator},
        ).one()
        assert tuple(membership) == (False, True)
        fitter = next(role for role in principals if role.purpose == "fit")
        assert not by_name[fitter.name]["rolinherit"]
        execute_native_sql(connection, host.semantic_roles(operator, fitter_only=True))
        # An existing fitter with widened inheritance must refuse, then recover
        # through the full normalizer inside this same rollback-only transaction.
        role = ast.RoleSpec(roletype=enums.RoleSpecType.ROLESPEC_CSTRING, rolename=fitter.name)
        execute_native_sql(
            connection,
            RawStream()(
                ast.AlterRoleStmt(
                    role=role,
                    options=(ast.DefElem(defname="inherit", arg=ast.Boolean(boolval=True)),),
                    action=1,
                )
            ),
        )
        with pytest.raises(DBAPIError, match="fitting role"), connection.begin_nested():
            execute_native_sql(connection, host.semantic_roles(operator, fitter_only=True))
        execute_native_sql(connection, script)
        assert not connection.execute(
            select(host.ROLES.c.rolinherit).where(host.ROLES.c.rolname == fitter.name)
        ).scalar_one()
    finally:
        transaction.rollback()
