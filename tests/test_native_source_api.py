"""Typed native source requests remain distinct from archived scalar coordinates."""
import pytest
from pydantic import ValidationError, TypeAdapter
from corpus_structure.serve.native_source import NativeSourceRequest
from corpus_structure.serve.source import SourceRequest


def test_native_request_pin_and_continuation_identity():
    value=NativeSourceRequest(run_id=1,task_id=2,product_key='native',content_digest='a'*64)
    assert value.model_copy(update={'limit':1,'cursor':'x'}).selection_digest()==value.selection_digest()
    assert value.model_copy(update={'pointer':'#/texts/1'}).selection_digest()!=value.selection_digest()
    with pytest.raises(ValidationError):
        NativeSourceRequest(run_id=1,task_id=2,product_key='native',content_digest='bad')


def test_tool_union_distinguishes_native_and_archived_coordinates():
    adapter=TypeAdapter(SourceRequest | NativeSourceRequest)
    native=adapter.validate_python(dict(version=2,run_id=1,task_id=2,product_key='native',content_digest='a'*64))
    assert isinstance(native,NativeSourceRequest)
    archive=adapter.validate_python(dict(run_id=1,rendition_id=2))
    assert isinstance(archive,SourceRequest)
    with pytest.raises(ValidationError):
        adapter.validate_python(dict(version=2,run_id=1,rendition_id=2,task_id=2,product_key='native',content_digest='a'*64))
