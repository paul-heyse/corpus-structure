import io
import json
from importlib.metadata import version
from types import CodeType

from docling.backend.docling_parse_backend import ThreadedDoclingParseDocumentBackend
from corpus_structure.ingest.pdf_producer_contract import standard_pdf_contract, standard_pdf_execution

factory = ThreadedDoclingParseDocumentBackend.__init__
original = factory.__code__
contract = standard_pdf_contract()
assert (original.co_filename, dict(contract.files)[original.co_filename]) in contract.files
before = version("docling")
forged_module = compile(
    "def replacement(self, in_doc, path_or_stream, options=None):\n  return None",
    original.co_filename,
    "exec",
)
forged = next(value for value in forged_module.co_consts if isinstance(value, CodeType))
stream = io.BytesIO()
factory.__code__ = forged.replace(co_freevars=original.co_freevars)
try:
    try:
        with standard_pdf_execution(contract):
            factory(None, None, stream)
    except ValueError as error:
        assert "Standard PDF dependency code differs from captured source" in str(error)
        assert error.args[0].endswith(original.co_filename)
    else:
        raise AssertionError("modified installed Docling factory was admitted")
finally:
    factory.__code__ = original
assert version("docling") == before
contract.check()
print(json.dumps({"outcome": "passed", "docling": before, "factory": factory.__qualname__,
                  "producer_material": contract.digest, "changed_installed_files": 0}))
