"""Captured executor preparation and controlled native transaction responses."""

import json
from contextlib import contextmanager, nullcontext
from hashlib import sha256
from threading import RLock
from types import SimpleNamespace
from typing import Any, cast

import pytest
from semantic.data_operation_declaration_support import operation
from semantic.data_operation_kernel_support import KernelRecipe, prepare_kernel
from sqlalchemy import Engine

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.orchestrate.data_operations import NativeDemandExecutor
from corpus_structure.semantic.cpu_execution import release_capsule
from corpus_structure.semantic.data_operation_model import MODEL_VERSION
from corpus_structure.semantic.data_operation_runtime import RuntimeBinding
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.python_operation_sources import PythonSourceCollection


def executor_preparation():
    operations = [operation(name) for name in ("prepared", "scalar", "batch")]
    for declaration in operations:
        declaration["capabilities"]["preparation"] = "controlled"
    operations[2]["capabilities"]["forms"] = ["batch"]
    return prepare_kernel(
        KernelRecipe(
            "executor-controls",
            """id: urn:admission
name: admission
prefixes: {a: 'urn:admission:'}
default_prefix: a
types:
  string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}
  integer: {base: int, uri: 'http://www.w3.org/2001/XMLSchema#integer'}
classes:
  Thing:
    attributes:
      id: {range: string, required: true}
""",
            canonical_bytes({"version": MODEL_VERSION, "operations": operations}),
            """version: data-operation-inputs-v1
root: admission
schemas: [{name: admission, path: schema.yaml}]
declarations: [{name: controls, path: operations.yaml}]
""",
        )
    )


class ForbiddenEngine:
    def begin(self):
        raise AssertionError("executor bypassed native I/O collaborator")

    def connect(self):
        raise AssertionError("executor bypassed native I/O collaborator")

    def raw_connection(self):
        raise AssertionError("executor bypassed native I/O collaborator")


class ControlledNativeIO:
    def __init__(self, *, calls=None, planner=None, savepoint=None, hydrate=None):
        self.calls = calls
        self.owner = Active(calls)
        self.plan: Any = planner
        self.savepoint = savepoint or (lambda: nullcontext())
        self.hydrate_inputs: Any = hydrate

    def transaction(self):
        return nullcontext(self)

    def begin_nested(self):
        return self.savepoint()

    def planner(self, model):
        return self.plan(model)

    def hydrate(self, model, selected, **options):
        return self.hydrate_inputs(model, selected, **options)

    def claims(self, holder):
        return nullcontext(self.owner)

    def acquire_execution(self, basis, operation, *, prepared=False):
        from corpus_structure.semantic.data_operation_admission import PreparedCapabilityIdentity

        identity = PreparedCapabilityIdentity(
            model_digest=sha256(basis.prepared.manifest).hexdigest(),
            operation=operation,
            definition="controlled-definition",
            recipe="controlled-recipe",
            implementation="controlled-implementation",
            declaration="controlled-declaration",
            source_digest="controlled-source",
            capabilities=b"{}",
            eligibility="controlled-eligibility",
            runtime=basis.runtime.runtime_id,
            assets=b"[]",
        )

        def authorize(actual):
            assert actual == identity

        return SimpleNamespace(identity=identity, custody=(), authorize=authorize)

    def recheck_execution(self, basis, identity):
        pass


def executor_case(
    *, prepared=None, native_io=None, policy=None, capability_factories=None, **options
):
    preparation = executor_preparation()
    prepared = preparation.prepared if prepared is None else prepared
    return NativeDemandExecutor(
        cast(Engine, ForbiddenEngine()),
        prepared,
        RuntimeBinding(prepared.release_id, "runtime:controlled", b"", b""),
        PythonSourceCollection(()),
        policy=policy,
        database_capacity=4,
        native_io=native_io or ControlledNativeIO(),
        capability_factories=capability_factories,
        **options,
    )


@pytest.fixture(scope="module")
def prepared():
    return executor_preparation().prepared


def policy_for(prepared, *, max_claims=2, credits=2):
    from dataclasses import replace

    packet = max(65536, len(release_capsule(prepared)))
    reply = 4096
    policy = CharacterizationExecutionPolicy(
        workers=2,
        max_submissions=2,
        max_claims=max_claims,
        max_packet_bytes=packet,
        max_reply_bytes=reply,
        max_native_request_bytes=1,
        max_native_reply_bytes=1,
        max_owned_bytes=1 << 40,
    )
    reservation = executor_case(prepared=prepared, policy=policy).reservation
    return replace(policy, max_owned_bytes=credits * reservation)


def execution_case(monkeypatch, prepared, policy, requests, ports, **options):
    """Replace native I/O only; exercise production admission and physical owners."""
    native_io = ControlledNativeIO()

    raw_results = {}

    def factory(prepared, model, operation, *, identity, **options):
        from corpus_structure.semantic.data_operation_identity import semantic_value
        from corpus_structure.semantic.data_operation_ports import PortCompletion, RoleValue

        port = ports[operation]
        port.operation, port.identity = model.operation(operation), identity
        output_kind = next(
            item.key
            for item in model.identities
            if item.owner
            == next(role.kind for role in port.operation.roles if role.direction == "output")
            and item.domain == "kind"
        )

        def completion(value):
            if isinstance(value, PortCompletion):
                return value
            encoded = int(value) if isinstance(value, str) and value.isdecimal() else value
            return PortCompletion(
                operation,
                (
                    RoleValue(
                        "result",
                        output_kind,
                        canonical_bytes(encoded),
                        canonical_bytes(semantic_value(encoded)),
                    ),
                ),
                outcome="produced",
            )

        def batch_inputs(members):
            from dataclasses import replace

            return tuple(
                replace(member, values=int(json.loads(member.producer)["request_id"]))
                if member.values == ()
                else member
                for member in members
            )

        if hasattr(port, "batch_input_bytes"):
            measure = port.batch_input_bytes
            port.batch_input_bytes = lambda members: measure(batch_inputs(members))
        if hasattr(port, "batch_order_key"):
            key = port.batch_order_key
            port.batch_order_key = lambda member: key(batch_inputs((member,))[0])

        if hasattr(port, "plan_python"):
            original = port.plan_python

            def scalar(*args, **kwargs):
                if args and args[0] == ():
                    args = (int(kwargs["execution_owner"].claim.request_id), *args[1:])
                value = yield from original(*args, **kwargs)
                if not isinstance(value, PortCompletion):
                    raw_results[kwargs["execution_owner"].claim.request_id] = value
                return completion(value)

            port.plan_python = scalar
        if hasattr(port, "plan_batch_python"):
            original_batch = port.plan_batch_python

            def batch(members, **kwargs):
                result = yield from original_batch(batch_inputs(members), **kwargs)
                for name, value in result.members:
                    if not isinstance(value, PortCompletion):
                        raw_results[name.split(":", 1)[0]] = value
                return SimpleNamespace(
                    members=tuple((name, completion(value)) for name, value in result.members)
                )

            port.plan_batch_python = batch
        return port

    executor: Any = executor_case(
        prepared=prepared,
        native_io=native_io,
        policy=policy,
        capability_factories=dict.fromkeys(ports, factory),
        **options,
    )
    binding = dict(
        inference="controlled-inference",
        inputs=[],
        support=[],
        populations=[],
        read_id="controlled-read",
        parameters=["mapping", []],
        request_inputs=["mapping", []],
    )
    from corpus_structure.semantic.data_operation_bindings import BindingResult
    from corpus_structure.semantic.data_operation_demands import BoundDataRequest, ReadyDataRequest
    from corpus_structure.semantic.data_operation_model import SubjectContext

    def ready_request(index, operation):
        subject = SubjectContext(
            "controlled-project", str(index), None, b"{}", subject_definition="source"
        )
        result = BindingResult(
            operation,
            str(index),
            (),
            "ready",
            (),
            canonical_bytes(["mapping", []]),
            b"{}",
            MODEL_VERSION,
            "controlled-definition",
            "controlled-eligibility",
            (),
            subject_context=subject,
            replicate=None,
        )
        resolved = result.resolved(
            inference="controlled-inference",
            subject_context=subject,
            authorization=b"{}",
            trust_evidence=b'{"read_id":"controlled-read","trust":{}}',
            execution_profile="controlled",
        )
        native = dict(
            request_id=str(index),
            generation=1,
            action="compute",
            retained_intent_id=None,
            release_id=prepared.release_id,
            runtime_id="runtime:controlled",
            binding=binding,
            binding_demand_id="demand",
            binding_obligation_id=str(index),
        )
        return ReadyDataRequest(
            str(index),
            operation,
            str(index),
            b"{}",
            b"{}",
            canonical_bytes(native),
            canonical_bytes(binding),
            resolved,
            result,
        )

    ready = tuple(ready_request(index, operation) for index, operation in enumerate(requests))
    executor._ready_items = ready

    def bound_requests(snapshot, **options):
        item = next(
            value
            for value in executor._ready_items
            if value.obligation == snapshot["obligations"][0]["obligation_id"]
        )
        values = {name: getattr(item, name) for name in vars(item) if name != "native"}
        return (BoundDataRequest(**values, request_id=json.loads(item.native)["request_id"]),)

    native_io.plan = lambda _model: SimpleNamespace(
        ready=lambda *_args, **_kw: executor._ready_items,
        logical_progress=0,
        refusals=(),
        resume=lambda demand, **options: dict(
            demand_id=demand,
            release_id=prepared.release_id,
            runtime_id="runtime:controlled",
            state="active",
            obligations=[],
            uses=[],
            populations=[],
            continuation=None,
            intent={"discovery": []},
            selection={"operations": [{"operation": name} for name in dict.fromkeys(requests)]},
        ),
        bound_requests=bound_requests,
    )
    observed = SimpleNamespace(
        claims=[], claim_sets=[], receipts=[], failures=[], live=set(), windows=[]
    )

    def claim_set(payload):
        observed.claim_sets.append(tuple(item["request_id"] for item in payload["items"]))
        results = []
        for item in payload["items"]:
            index = item["request_id"]
            observed.claims.append((index, executor.budget.used_bytes))
            observed.live.add(index)
            observed.windows.append(len(observed.live))
            metadata = json.loads(
                next(value.native for value in executor._ready_items if value.obligation == index)
            )
            results.append(
                {
                    "state": "claimed",
                    "result": {
                        **metadata,
                        "state": "claimed",
                        "task_id": int(index) + 1,
                        "attempt": 1,
                        "holder": payload["holder"],
                        "lease_until": "2026-11-17T00:00:00Z",
                        "trust_snapshot": {},
                    },
                }
            )
        return {"items": results}

    from semantic.data_operation_binding_support import WireCheckedStorage

    def read_result(request):
        from semantic.demand_result_support import demand_result_page

        result = demand_result_page()
        result["demand_id"] = request["demand_id"]
        result["read_id"] = request["read_id"]
        result["obligations"][0]["obligation_id"] = request["obligation_id"]
        return result

    retained = {}

    def retain(payload):
        retained[payload["request_id"]] = payload["completion"]
        return {"intent_id": payload["request_id"], "payload_digest": "controlled-digest"}

    def publish(payload):
        identifier = payload["request_id"]
        observed.receipts.append((identifier, raw_results[identifier]))
        observed.live.remove(identifier)
        return dict(
            derivation_id="derivation:" + identifier,
            receipt_id=identifier,
            replayed=False,
            trust_snapshot={},
        )

    def failed(payload):
        identifier = payload["request_id"]
        observed.failures.append((identifier, payload["failure"]))
        observed.live.remove(identifier)
        return dict(
            **{
                name: payload[name]
                for name in ("request_id", "generation", "task_id", "attempt", "holder")
            },
            retained_intent_id=None,
            state="released",
            failure_id="failure:" + identifier,
            replayed=False,
        )

    native_io.calls = WireCheckedStorage(
        {
            "claim_data_requests": claim_set,
            "read_demand_result": read_result,
            "retain_data_completion_intent": retain,
            "publish_data_derivation": publish,
            "release_data_attempt": failed,
        }
    )
    native_io.owner = Active(native_io.calls)
    executor._receipt_count, executor._receipt_sink, executor._receipt_limit = 0, [], 100
    executor.demand = "controlled-demand"

    from corpus_structure.semantic.data_operation_consumers import HydratedConsumerSelection

    native_io.hydrate_inputs = lambda model, selected, **options: HydratedConsumerSelection(
        selected,
        (),
        measured_bytes=len(selected.subject),
    )
    return executor, observed


@contextmanager
def execution_resources(executor):
    from corpus_structure.orchestrate.execution_host import ProcessExecutionHost

    host = ProcessExecutionHost()
    try:
        with host.run(executor.policy) as token:
            # The controlled fixture wraps this exact production budget.
            host.budget = executor.budget
            with host.execution(executor, token) as physical:
                yield physical
    finally:
        host.close()


class Active:
    def __init__(self, calls=None):
        self.calls = calls
        self.lock = RLock()
        self.active, self.uncertain, self.lost = {}, {}, {}

    def add_claim(self, claim):
        self.active[claim.request_id] = claim

    def retain(self, claim, callback):
        return callback(self.calls)

    def settle(self, claim, callback):
        result = callback(self.calls)
        self.active.pop(claim.request_id, None)
        return result

    def __call__(self):
        pass

    def check_claim(self, _):
        pass
