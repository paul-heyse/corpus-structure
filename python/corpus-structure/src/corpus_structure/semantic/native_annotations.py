"""Prepared spaCy annotation work in the shared post-capture CUDA host."""

from __future__ import annotations

import base64
from dataclasses import dataclass

from corpus_structure.ingest.annotations import AnnotationUnavailable, annotate
from corpus_structure.ingest.sentences import make_doc, pipeline
from corpus_structure.methods.characterization_resources import PM2Work
from corpus_structure.methods.model_observation import ordered_native_bytes
from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection


@dataclass(frozen=True)
class AnnotationBatch:
    products: tuple = ()
    unavailable_type: str | None = None
    message: str | None = None
    missing_components: tuple = ()
    availability: tuple = ()

    def require_available(self):
        if self.unavailable_type is not None:
            raise AnnotationUnavailable(self.message or "native annotation unavailable", missing_components=self.missing_components, availability=self.availability)
        return self.products


class _AnnotationHandle:
    def __init__(self, handle, inputs, profile, nlp):
        self._handle, self.inputs, self.profile, self.nlp = handle, inputs, profile, nlp
        self.future = handle.future
        self._result = None

    def collect(self):
        if self._result is None:
            reply = self._handle.collect()
            if reply is None:
                return None
            payload = reply.payload
            self.nlp.observe(reply.startup)
            docs = self.nlp.decode(payload["documents"])
            if len(docs) != len(self.inputs):
                raise ValueError("native spaCy changed admitted block population")
            products = tuple(annotate(self.inputs, self.profile, require_complete=False, processed_docs=docs))
            self._result = AnnotationBatch(products)
        return self._result

    def cancel(self):
        self._handle.cancel()

    def retire(self):
        return self._handle.retire()


def annotation_work(execution, inputs, profile, check_active, *, native_profile=None, require_complete=False):
    from corpus_structure.core.work import PreparedWork
    import spacy
    from uuid import uuid4

    nlp = pipeline(profile.configuration)
    selected = next((s for s in execution.native_group._selections.values() if s.provider == "spacy" and s.native.parameters == profile.configuration.model_dump(mode="json")), None)
    selection = NativeSelection(NativeProfile(**native_profile), spacy.util.get_package_path(profile.configuration.model)) if native_profile is not None else selected if selected is not None else nlp.selection()
    execution.declare_native((selection,))
    if profile.execution_profile is None:
        from dataclasses import replace
        profile = replace(profile, execution_profile=selection.native.fingerprint)
    docs = [make_doc(nlp, item.block, item.layout, start=item.layout.block_start, recipe=item.layout.recipe) for item in inputs]
    payload = dict(version="spacy-host-1", documents=[dict(content=base64.b64encode(doc.to_bytes()).decode("ascii")) for doc in docs])
    request = PM2Work(selection, ordered_native_bytes(payload), uuid4().hex, (check_active,))
    underlying = execution.work(request)

    def submit():
        handle = underlying.try_submit()
        return None if handle is None else _AnnotationHandle(handle, inputs, profile, nlp)

    return PreparedWork(submit, abandon=underlying.abandon)
