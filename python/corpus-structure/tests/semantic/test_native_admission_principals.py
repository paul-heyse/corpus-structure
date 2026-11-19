"""Independent restricted-principal predicates retained across typed authoring."""

import pytest
from pglast import parse_plpgsql, parse_sql
from pglast.visitors import Visitor
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.sql.elements import ClauseElement

from corpus_structure.model.compiled import running_model
from corpus_structure.semantic.native_admission_principals import (
    principal_catalog_checks,
    restricted_principal_checks,
)
from corpus_structure.semantic.native_program import Block, Local, Raise, function, pg_type

# These predicates preserve the prior admission policy independently of its Core builder.
# Qualification of PostgreSQL catalog names does not change those policy conditions.
_EXPECTED = (
    (
        "unrestricted evaluation principal",
        "23514",
        """EXISTS(SELECT 1 FROM pg_roles r WHERE r.rolname='corpus_sem_evaluator'
        AND (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls))
        OR EXISTS(SELECT 1 FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member
        WHERE r.rolname='corpus_sem_evaluator')""",
    ),
    (
        "evaluator schema mutation privilege",
        "23514",
        """EXISTS(SELECT 1 FROM (VALUES('sem'),('data'),('ops'),('kb'),('eval')) schemas(name)
        WHERE coalesce(has_schema_privilege('corpus_sem_evaluator',to_regnamespace(schemas.name),'CREATE'),false))""",
    ),
    (
        "evaluator direct write privilege",
        "23514",
        """EXISTS(SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname IN ('sem','data','ops','kb','eval') AND c.relkind IN ('r','p')
        AND (has_table_privilege('corpus_sem_evaluator',c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')
        OR has_any_column_privilege('corpus_sem_evaluator',c.oid,'INSERT,UPDATE')))""",
    ),
    (
        "reference data leaked to source principal",
        "23514",
        """EXISTS(SELECT 1 FROM (VALUES('corpus_sem_writer'),('corpus_sem_reader')) roles(name)
        WHERE coalesce(has_schema_privilege(roles.name,to_regnamespace('eval'),'USAGE,CREATE'),false))
        OR EXISTS(SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace,
        (VALUES('corpus_sem_writer'),('corpus_sem_reader')) roles(name)
        WHERE n.nspname='eval' AND c.relkind IN ('r','p')
        AND (has_table_privilege(roles.name,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')
        OR has_any_column_privilege(roles.name,c.oid,'SELECT,INSERT,UPDATE')))""",
    ),
    (
        "unrestricted application principal",
        "23514",
        """EXISTS(SELECT 1 FROM pg_roles r WHERE r.rolname IN ('corpus_sem_writer','corpus_sem_reader')
        AND (r.rolsuper OR r.rolcreaterole OR r.rolbypassrls))
        OR pg_has_role('corpus_sem_writer','corpus_sem_publisher','MEMBER')
        OR pg_has_role('corpus_sem_reader','corpus_sem_publisher','MEMBER')
        OR pg_has_role('corpus_sem_writer',owner_name,'MEMBER')
        OR pg_has_role('corpus_sem_reader',owner_name,'MEMBER')""",
    ),
    (
        "application schema mutation privilege",
        "23514",
        """EXISTS(SELECT 1 FROM (VALUES('corpus_sem_writer'),('corpus_sem_reader')) roles(name),
        (VALUES('sem'),('data'),('ops'),('kb')) schemas(name)
        WHERE coalesce(has_schema_privilege(roles.name,to_regnamespace(schemas.name),'CREATE'),false))""",
    ),
    (
        "application direct semantic write privilege",
        "23514",
        """EXISTS(SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace,
        (VALUES('corpus_sem_writer'),('corpus_sem_reader')) roles(name)
        WHERE n.nspname IN ('sem','data') AND c.relkind IN ('r','p')
        AND (has_table_privilege(roles.name,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')
        OR has_any_column_privilege(roles.name,c.oid,'INSERT,UPDATE')))""",
    ),
    (
        "application private kernel privilege",
        "23514",
        """EXISTS(SELECT 1 FROM (VALUES('corpus_sem_writer'),('corpus_sem_reader')) roles(name),
        (VALUES('data.publish_contract_batch(text,text,text,bytea)'),('data.validate_state(text,text)'),
        ('data.publish_pre_execution_analysis_batch(text,text,text,bytea,bigint)'),
        ('data.finish_pre_contract_evaluation(bigint,text,text)')) kernels(signature)
        WHERE coalesce(has_function_privilege(roles.name,to_regprocedure(kernels.signature),'EXECUTE'),false))""",
    ),
    (
        "admission principal has reference access",
        "42501",
        """EXISTS(SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='eval' AND c.relkind IN ('r','p')
        AND has_table_privilege('corpus_sem_admitter',c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE'))""",
    ),
    (
        "privileged runtime principal",
        "42501",
        """EXISTS(SELECT 1 FROM (VALUES('corpus_sem_writer'),('corpus_sem_reader'),
        ('corpus_sem_admitter'),('corpus_sem_evaluator')) principal(name)
        WHERE has_database_privilege(principal.name,current_database(),'TEMP')
        OR pg_has_role(principal.name,'corpus_sem_publisher','MEMBER')
        OR pg_has_role(principal.name,owner_name,'MEMBER'))""",
    ),
)


def _policy_tree(sql):
    class CatalogQualification(Visitor):
        def visit_RangeVar(self, ancestors, node):
            if node.schemaname == "pg_catalog":
                node.schemaname = None

        def visit_FuncCall(self, ancestors, node):
            if len(node.funcname) == 2 and node.funcname[0].sval == "pg_catalog":
                node.funcname = node.funcname[1:]

    tree = parse_sql("SELECT " + sql)
    CatalogQualification()(tree)
    return tree[0].stmt


@pytest.mark.parametrize(
    "position,expected", enumerate(_EXPECTED), ids=[row[0] for row in _EXPECTED]
)
def test_principal_refusal_preserves_complete_policy_predicate(position, expected):
    metadata = running_model().physical()
    checks = (*principal_catalog_checks(metadata), *restricted_principal_checks(metadata))
    check = checks[position]
    message, sqlstate, condition = expected
    assert check.then == (Raise(message, sqlstate),)
    assert check.otherwise == ()
    assert isinstance(check.condition, ClauseElement)
    actual = str(check.condition.compile(dialect=dialect(), compile_kwargs={"literal_binds": True}))
    assert _policy_tree(actual) == _policy_tree(condition)


def test_principal_program_preserves_pre_and_post_generic_check_split():
    metadata = running_model().physical()
    principal, restricted = (
        principal_catalog_checks(metadata),
        restricted_principal_checks(metadata),
    )
    assert len(principal) == 8
    assert len(restricted) == 2
    sql = function(
        "public",
        "admission_principal_control",
        parameters=(),
        returns=pg_type("void"),
        body=Block((*principal, *restricted), (Local("owner_name", pg_type("text")),)),
        search_path=("pg_catalog", "pg_temp"),
    )
    assert parse_plpgsql(sql)
