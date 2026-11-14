"""Actual source-native CPU packets shared by lifecycle and request controls."""

from contextlib import contextmanager, suppress
from concurrent.futures import TimeoutError
from types import SimpleNamespace
from uuid import uuid4

import pytest

from corpus_structure.semantic.formal_evidence import grammar_identity
from corpus_structure.semantic.formal_products import FormalEvidenceOptions, formal_member_contracts, formal_profile_assets
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.identity import canonical_bytes
from semantic.formal_products_support import released_profile, selected


@pytest.fixture(scope="module")
def prepared():
    return released_profile().prepared


def packet(prepared):
    profile = SimpleNamespace(prepared=prepared)
    source = selected(profile, "x≥2")
    return canonical_bytes(dict(
        request_id=uuid4().hex,
        profile="formal-source-native",
        release_id=prepared.release_id,
        member_contracts=formal_member_contracts(prepared, bound_data_operation_model(prepared)),
        source=source.content.decode(), options=FormalEvidenceOptions().model_dump_json(),
        grammar=grammar_identity(), assets=formal_profile_assets().digest,
    ))


@contextmanager
def execute_formal(execution, content, check_active):
    """Drive the real asynchronous target request for synchronous boundary assertions."""
    with execution.admitted_inputs(check_active) as permit:
        handle = execution.submit_formal(permit, content, check_active)
        try:
            while not handle.future.done():
                check_active()
                if execution._closed:
                    raise RuntimeError("CPU invocation is closed")
                with suppress(TimeoutError):
                    handle.future.result(timeout=0.1)
            yield handle.collect()
        except BaseException:
            handle.cancel()
            raise
        finally:
            handle.retire()
