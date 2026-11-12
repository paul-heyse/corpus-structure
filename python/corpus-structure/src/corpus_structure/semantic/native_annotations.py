"""Prepared spaCy annotation work in the shared post-capture CUDA host."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

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
            raise AnnotationUnavailable(
                self.message or "native annotation unavailable",
                missing_components=self.missing_components,
                availability=self.availability,
            )
        return self.products


class _AnnotationHandle:
    def __init__(self, handle, inputs, profile, nlp, require_complete):
        self._handle, self.inputs, self.profile, self.nlp = handle, inputs, profile, nlp
        self.future = handle.future
        self._result = None
        self.require_complete = require_complete

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
            products = tuple(
                annotate(
                    self.inputs,
                    self.profile,
                    require_complete=self.require_complete,
                    processed_docs=docs,
                )
            )
            self._result = AnnotationBatch(products)
        return self._result

    def cancel(self):
        self._handle.cancel()

    def flush(self):
        self._handle.flush()

    def retire(self):
        return self._handle.retire()


def annotation_work(
    execution, inputs, profile, check_active, *, native_profile=None, require_complete=False
):
    import spacy

    from corpus_structure.core.work import PreparedWork

    nlp: Any = pipeline(profile.configuration)
    selected = next(
        (
            s
            for s in execution.native_group._selections.values()
            if s.provider == "spacy"
            and s.native.parameters == profile.configuration.model_dump(mode="json")
        ),
        None,
    )
    selection = (
        NativeSelection(
            NativeProfile(**native_profile),
            spacy.util.get_package_path(profile.configuration.model),
        )
        if native_profile is not None
        else selected
        if selected is not None
        else nlp.selection()
    )
    execution.declare_native((selection,))
    if profile.execution_profile is None:
        from dataclasses import replace

        profile = replace(profile, execution_profile=selection.native.fingerprint)

    def factory():
        from uuid import uuid4

        check_active()
        docs = [
            make_doc(
                nlp,
                item.block,
                item.layout,
                start=item.layout.block_start,
                recipe=item.layout.recipe,
            )
            for item in inputs
        ]
        payload = dict(
            version="spacy-host-1",
            documents=[
                dict(content=base64.b64encode(doc.to_bytes()).decode("ascii")) for doc in docs
            ],
        )
        return PM2Work(selection, ordered_native_bytes(payload), uuid4().hex, (check_active,))

    underlying = execution.lazy_work(factory, lane_key="spacy")

    def submit():
        handle = underlying.try_submit()
        return (
            None
            if handle is None
            else _AnnotationHandle(handle, inputs, profile, nlp, require_complete)
        )

    return PreparedWork(submit, abandon=underlying.abandon)
