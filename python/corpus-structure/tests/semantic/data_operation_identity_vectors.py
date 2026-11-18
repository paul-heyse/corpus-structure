"""Independent literal expectations shared by DDO identity controls."""

import json
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class SubjectVector:
    project: str
    source: str
    subject: str
    definition: str
    scope: bytes

    def embed(self, **values) -> str:
        context = {
            "project_id": self.project,
            "original_source": self.source,
            "subject": self.subject,
            "subject_definition": self.definition,
        }
        fields = [f"{json.dumps(key)}:{json.dumps(value)}" for key, value in context.items()]
        fields.append('"analyzed_scope":' + self.scope.decode())
        outer = [f"{json.dumps(key)}:{json.dumps(value)}" for key, value in values.items()]
        outer.append('"subject_context":{' + ",".join(fields) + "}")
        return "{" + ",".join(outer) + "}"


@dataclass(frozen=True)
class ContextualProductVector:
    name: str
    kind: str
    body: str
    context: SubjectVector
    literal: bytes

    def native_json(self) -> str:
        return self.context.embed(kind=self.kind, body=self.body, subject=self.context.subject)


@dataclass(frozen=True)
class RequestVector:
    recipe: str
    inputs: dict[str, str]
    parameters: dict[str, str]
    inference: str
    context: SubjectVector
    literal: bytes

    def native_json(self) -> str:
        return self.context.embed(
            recipe=self.recipe,
            inputs=self.inputs,
            parameters=self.parameters,
            inference=self.inference,
            subject=self.context.subject,
        )


# Authored from ADR-0100 and the version-1 framing contract. Neither a production
# normalizer nor a production identity function constructs these expected bytes.
_CONTEXT = SubjectVector("project:a", "original:a", "local", "document", b'{"page":1.25}')
_CONTEXT_FRAME = (
    b'["mapping",[["analyzed_scope",["mapping",[["page",["decimal","1.25"]]]]],'
    b'["original_source",["string","original:a"]],["project_id",["string","project:a"]],'
    b'["subject",["string","local"]],["subject_definition",["string","document"]]]]'
)
_PRODUCT = ContextualProductVector(
    "base",
    "kind:one",
    "body:one",
    _CONTEXT,
    b'["ddo","product","1",["mapping",[["body",["string","body:one"]],'
    b'["kind",["string","kind:one"]],["subject",["string","local"]],'
    b'["subject_context",' + _CONTEXT_FRAME + b"]]]]",
)
CONTEXTUAL_PRODUCTS = (
    _PRODUCT,
    replace(
        _PRODUCT,
        name="other-project",
        context=replace(_CONTEXT, project="project:b"),
        literal=_PRODUCT.literal.replace(b'"project:a"', b'"project:b"'),
    ),
    replace(
        _PRODUCT,
        name="other-source",
        context=replace(_CONTEXT, source="original:b"),
        literal=_PRODUCT.literal.replace(b'"original:a"', b'"original:b"'),
    ),
    replace(
        _PRODUCT,
        name="other-scope",
        context=replace(_CONTEXT, scope=b'{"page":2.25}'),
        literal=_PRODUCT.literal.replace(b'"decimal","1.25"', b'"decimal","2.25"'),
    ),
    replace(
        _PRODUCT, name="equal-json-number", context=replace(_CONTEXT, scope=b'{"page":1.2500}')
    ),
    replace(
        _PRODUCT,
        name="other-definition",
        context=replace(_CONTEXT, definition="passage"),
        literal=_PRODUCT.literal.replace(b'"document"', b'"passage"'),
    ),
    replace(
        _PRODUCT,
        name="other-local-subject",
        context=replace(_CONTEXT, subject="alternative"),
        literal=_PRODUCT.literal.replace(b'"local"', b'"alternative"'),
    ),
)
REQUEST = RequestVector(
    "recipe:a",
    {"source": "result:a"},
    {"mode": "exact"},
    "inference:a",
    _CONTEXT,
    b'["ddo","semantic-request","1",["mapping",[["inference",["string","inference:a"]],'
    b'["inputs",["mapping",[["source",["string","result:a"]]]]],'
    b'["parameters",["mapping",[["mode",["string","exact"]]]]],'
    b'["recipe",["string","recipe:a"]],["subject",["string","local"]],'
    b'["subject_context",' + _CONTEXT_FRAME + b"]]]]",
)

JSON_MEANING_VECTORS = (
    ("null", ["null"]),
    ("true", ["boolean", True]),
    ('"1"', ["string", "1"]),
    ("1", ["decimal", "1"]),
    ("1.0", ["decimal", "1"]),
    ("1e6", ["decimal", "1000000"]),
    ("-0.0", ["decimal", "0"]),
    (
        '{"page":1,"slots":[false,"x",null]}',
        [
            "mapping",
            [
                ["page", ["decimal", "1"]],
                ["slots", ["sequence", [["boolean", False], ["string", "x"], ["null"]]]],
            ],
        ],
    ),
)
