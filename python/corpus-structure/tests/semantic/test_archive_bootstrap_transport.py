"""Archive bootstrap uses installed native capability, independent of release admission.

These controls assess only Python/Core transport. Native archive replay, purpose
permissions, finalization and activation CAS remain separate real database controls.
"""

from unittest.mock import Mock

import pytest
from pydantic import ValidationError
from sqlalchemy import BigInteger, Text
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.exc import MultipleResultsFound, NoResultFound

from corpus_structure.semantic import archive_native, releases
from corpus_structure.semantic.identifiers import ProjectId, ReleaseId
from corpus_structure.semantic.operation_value_types import NativeResultViolation


def test_archive_bootstrap_binds_literal_release_and_consumes_one_native_result():
    connection = Mock()
    connection.execute.return_value.scalar_one.return_value = None
    value = ReleaseId("release:literal'\\binary")
    assert archive_native.prepare_release_archive(connection, value) is None
    statement, parameters = connection.execute.call_args.args
    compiled = statement.compile(dialect=dialect())
    assert 'sem.prepare_release_archive(' in str(compiled)
    assert parameters == {"release_id": value}
    assert value not in str(compiled)
    assert isinstance(compiled.binds["release_id"].type, Text)
    connection.execute.return_value.scalar_one.assert_called_once()

    connection.reset_mock()
    connection.execute.return_value.one.return_value = (value,)
    assert archive_native.publish_release_archive(connection, value) == value
    statement, parameters = connection.execute.call_args.args
    assert 'sem.publish_release_archive(' in str(statement.compile(dialect=dialect()))
    assert parameters == {"release_id": value}
    connection.begin_nested.assert_not_called()
    connection.commit.assert_not_called()
    connection.rollback.assert_not_called()


@pytest.mark.parametrize('value', [None, 7, b'release:bytes'])
@pytest.mark.parametrize('invoke', [archive_native.prepare_release_archive,
                                    archive_native.publish_release_archive])
def test_archive_bootstrap_refuses_nontext_identity_before_native_call(value, invoke):
    connection = Mock()
    with pytest.raises(ValidationError):
        invoke(connection, value)
    connection.execute.assert_not_called()


@pytest.mark.parametrize('value', [None, 7, b'release:bytes'])
def test_archive_publication_malformed_native_identity_retains_result_attribution(value):
    connection = Mock()
    connection.execute.return_value.one.return_value = (value,)
    with pytest.raises(NativeResultViolation) as refused:
        archive_native.publish_release_archive(connection, ReleaseId('release:exact'))
    assert (refused.value.operation, refused.value.result_class, refused.value.field) == (
        'archive', 'publish_release_archive', 'release_id'
    )


@pytest.mark.parametrize('error', [NoResultFound, MultipleResultsFound])
def test_archive_bootstrap_requires_one_native_response(error):
    connection = Mock()
    connection.execute.return_value.scalar_one.side_effect = error
    with pytest.raises(NativeResultViolation):
        archive_native.prepare_release_archive(connection, ReleaseId('release:exact'))


def test_activation_preserves_native_cas_types_and_explicit_null_parent():
    request = releases._ActivationRequest(
        project_id=ProjectId('project:exact'), release_id=ReleaseId('release:exact'), expected_parent=None,
        expected_generation=2**63-1,
    )
    compiled = releases._activate_release.compile(dialect=dialect())
    assert 'sem.activate_release(' in str(compiled)
    assert isinstance(compiled.binds['expected_generation'].type, BigInteger)
    assert isinstance(compiled.binds['expected_parent'].type, Text)
    assert request.model_dump() == {
        'project_id': 'project:exact', 'release_id': 'release:exact',
        'expected_parent': None, 'expected_generation': 2**63-1,
    }
    for generation in (True, '1', 2**63, -(2**63)-1):
        with pytest.raises(ValidationError):
            releases._ActivationRequest.model_validate({
                'project_id':'project:exact', 'release_id':'release:exact',
                'expected_parent':'release:parent', 'expected_generation':generation,
            })
