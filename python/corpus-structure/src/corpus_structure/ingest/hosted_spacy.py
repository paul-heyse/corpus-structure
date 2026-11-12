"""CPU tokenizer and detached learned-pipeline facade over the shared CUDA host."""

from __future__ import annotations

import base64
from itertools import islice
from types import SimpleNamespace

import spacy
from confection import Config
from spacy.tokens import Doc


class HostedPipeline:
    def __init__(self, configuration):
        self.configuration = configuration
        self._selection = None
        try:
            package = spacy.util.get_package_path(configuration.model)
        except ModuleNotFoundError as error:
            if error.name != configuration.model:
                raise
            raise OSError(
                f"spaCy model package {configuration.model!r} is not installed"
            ) from error
        paths = tuple(package.glob("*/config.cfg"))
        if len(paths) != 1:
            raise ValueError("selected spaCy package has no unique pipeline configuration")
        original = spacy.util.load_config(paths[0])
        self._config = original.copy()
        self.pipe_names = [
            name for name in original["nlp"]["pipeline"] if name not in configuration.exclude
        ]
        self._config["nlp"]["pipeline"] = self.pipe_names
        # Load tokenizer/vocabulary data only. No learned weights enter a parent
        # or a CPU parser process merely to prepare protected source atoms.
        self._base = spacy.load(configuration.model, exclude=original["nlp"]["pipeline"])
        self.vocab, self.tokenizer, self.meta = (
            self._base.vocab,
            self._base.tokenizer,
            self._base.meta,
        )
        from .sentences import SentenceConfigError

        if spacy.__version__ != configuration.spacy_version:
            raise SentenceConfigError(
                f"spaCy {spacy.__version__} is installed; the configuration names "
                f"{configuration.spacy_version}"
            )
        if self.meta.get("version") != configuration.model_version:
            raise SentenceConfigError(
                f"{configuration.model} {self.meta.get('version')} is installed; "
                f"the configuration names {configuration.model_version}"
            )

    @property
    def config(self):
        return self._config

    def get_pipe_meta(self, name):
        return SimpleNamespace(factory=self._config["components"][name]["factory"])

    def observe(self, startup):
        self._config = Config().from_str(startup["native_configuration"])
        self.pipe_names = [entry["name"] for entry in startup["components"]]

    def selection(self):
        from corpus_structure.methods.native_profiles import spacy_selection

        if self._selection is None:
            self._selection = spacy_selection(self.configuration)
        return self._selection

    def decode(self, values):
        return [
            Doc(self.vocab).from_bytes(base64.b64decode(value, validate=True)) for value in values
        ]

    def pipe(self, inputs, *, as_tuples=False, batch_size=None, n_process=1, endpoint=None):
        from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
        from corpus_structure.methods.native_host import NativeHostGroup

        if n_process != 1:
            raise ValueError("learned spaCy uses one shared resident instance")
        selection = self.selection()
        # A direct/HTML operation owns this same host implementation only for its
        # learned phase. Exhaustion/close proves host death before returning.
        from corpus_structure.settings import NemotronSettings

        with NativeHostGroup(
            CharacterizationExecutionPolicy(), endpoint or NemotronSettings().endpoint
        ) as group:
            group.declare((selection,))
            iterator = iter(inputs)
            while population := list(
                islice(
                    iterator,
                    min(batch_size or self.configuration.batch_size, self.configuration.batch_size),
                )
            ):
                docs = [item[0] if as_tuples else item for item in population]
                payload = dict(
                    version="spacy-host-1",
                    documents=[
                        dict(content=base64.b64encode(doc.to_bytes()).decode("ascii"))
                        for doc in docs
                    ],
                )
                result = group.infer(selection, payload, lambda: None)
                self.observe(group.startup(selection, lambda: None))
                decoded = self.decode(result["documents"])
                if len(decoded) != len(docs):
                    raise ValueError("spaCy changed admitted document population")
                for original, doc, item in zip(docs, decoded, population, strict=True):
                    if original.text != doc.text or len(original) != len(doc):
                        raise ValueError("spaCy changed exact prepared layout")
                    yield (doc, item[1]) if as_tuples else doc
