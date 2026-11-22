"""Independent source expectations and existing file-publication custody."""

from collections.abc import Callable, Generator
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest
from model_change_support import model_checkout as model_checkout

from corpus_structure.schema.declarations import ModelError
from corpus_structure.schema.model_change import ChangeRequest, apply_preview, prepare_preview
from corpus_structure.schema.source_migrations import (
    AuthoredSourceChange,
    SourceMigration,
    SourceRoot,
    prepare_source_migration,
)


def operation_metadata():
    # These temporary callables transform an integer; they do not implement the
    # production claim-source address operation or its enforcement invariants.
    return {
        "id": "urn:test:source-change",
        "profile": "derivation",
        "subject": "test-integer",
        "subject_definition": {
            "id": "test-integer",
            "identifier_kind": "primitive:integer",
            "scope": "project",
        },
        "discovery_relation": "role-associated",
        "context": [],
        "roles": [
            {
                "name": "input",
                "parameter": "x",
                "kind": "primitive:integer",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "value_substitution",
                    "source": "selected-input",
                    "coverage": {"role": "input", "description": "one-integer-input"},
                },
            },
            {
                "name": "result",
                "kind": "primitive:integer",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [],
        "invariants": [],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "one-integer-result",
        },
        "outcomes": ["returned"],
        "state_dimensions": [{"name": "completion", "values": ["pending", "success"]}],
        "transitions": [
            {
                "dimension": "completion",
                "before": "pending",
                "after": "success",
                "outcome": "returned",
            },
        ],
        "dependencies": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "none",
            "cancellation": "call-boundary",
            "ownership": "immutable-input-value",
        },
        "behavior": "test-integer-transform-v1",
        "parameters": {},
        "binding": {"operator": "scan", "roles": ["input"]},
    }


def migration(root, *, consumer="from api import old\nanswer = old(1)\n"):
    directory = root / "src"
    directory.mkdir()
    metadata = operation_metadata()
    before = (
        "def old(x: int) -> int:\n    return x\nold__data_operation__ = " + repr(metadata) + "\n"
    ).encode()
    (directory / "api.py").write_bytes(before)
    (directory / "consumer.py").write_bytes(consumer.encode())
    (root / "schema.yaml").write_text(
        "id: urn:test\nname: target\nprefixes: {t: 'urn:test:'}\ndefault_prefix: t\nclasses: {Thing: {description: Example}}\n"
    )
    (root / "target.yaml").write_text(
        "version: data-operation-inputs-v1\nroot: target\nschemas: [{name: target, path: schema.yaml}]\npython:\n  interpreter: python-3.14\n  interpretation: closed-python-operations-v1\n  stub_policy: source-authoritative\n  sources: [{module: api, path: src/api.py}]\n"
    )
    return SourceMigration(
        kind="symbol_move",
        owner="urn:test:source-change",
        sources=(
            AuthoredSourceChange(
                path="src/api.py",
                module="api",
                before=sha256(before).hexdigest(),
                after="def new(x: int) -> int:\n    return x\nnew__data_operation__ = "
                + repr(metadata)
                + "\n",
            ),
        ),
        roots=(SourceRoot(path="src", module=""),),
        old_name="api.old",
        new_name="api.new",
    )


def test_symbol_move_preserves_unrelated_source_and_existing_apply(model_checkout):
    root, _ = model_checkout
    request = migration(root, consumer="from api import old\r\nanswer = old(1)  # retained\r\n")
    preview = prepare_preview(
        root, ChangeRequest(data_operations="target.yaml", source_migrations=(request,))
    )
    assert preview.source_migrations[0].ready
    assert (root / "src/api.py").read_text().startswith("def old")
    apply_preview(root, preview)
    assert (root / "src/api.py").read_text() == request.sources[0].after
    assert (
        root / "src/consumer.py"
    ).read_bytes() == b"from api import new\r\nanswer = new(1)  # retained\r\n"
    apply_preview(root, preview)  # exact settled bytes are retryable


def test_added_caller_invalidates_complete_preview(model_checkout):
    root, _ = model_checkout
    preview = prepare_preview(
        root, ChangeRequest(data_operations="target.yaml", source_migrations=(migration(root),))
    )
    (root / "src/added.py").write_text("from api import old\n")
    with pytest.raises(ModelError, match="membership"):
        apply_preview(root, preview)
    assert (root / "src/api.py").read_text().startswith("def old")


def test_dynamic_required_site_blocks_apply_but_remains_inspectable(model_checkout):
    root, _ = model_checkout
    preview = prepare_preview(
        root,
        ChangeRequest(
            data_operations="target.yaml",
            source_migrations=(
                migration(root, consumer="import api\nanswer = getattr(api, 'old')(1)\n"),
            ),
        ),
    )
    assert not preview.source_migrations[0].ready
    assert preview.files
    assert any(item.state == "unresolved" for item in preview.source_migrations[0].outcomes)
    with pytest.raises(ModelError, match="unresolved"):
        apply_preview(root, preview)


def test_same_spelled_local_is_not_renamed(tmp_path):
    request = migration(tmp_path, consumer="def old(x):\n    return x + 1\nanswer = old(1)\n")
    preview = prepare_source_migration(tmp_path, request)
    assert preview.ready
    assert "src/consumer.py" not in preview.after


def test_authoritative_annotation_stage_preserves_body(tmp_path):
    request = migration(tmp_path)
    before = b"def old(x):\n    return x\n"
    (tmp_path / "src/api.py").write_bytes(before)
    owner = request.sources[0].model_copy(
        update={
            "before": sha256(before).hexdigest(),
            "after": "def old(x: int) -> int:\n    return x\n",
        }
    )
    request = request.model_copy(update={"kind": "annotations", "sources": (owner,)})
    preview = prepare_source_migration(tmp_path, request)
    assert preview.ready
    assert preview.after["src/api.py"] == "def old(x: int) -> int:\n    return x\n"


def test_stale_owner_revision_refuses(tmp_path):
    request = migration(tmp_path)
    (tmp_path / "src/api.py").write_text("def old(x): return 2\n")
    with pytest.raises(ValueError, match="revision"):
        prepare_source_migration(tmp_path, request)


def test_unknown_receiver_dispatch_blocks_readiness(tmp_path):
    preview = prepare_source_migration(
        tmp_path, migration(tmp_path, consumer="def call(receiver):\n    return receiver.old()\n")
    )
    assert not preview.ready
    assert any(item.state == "unresolved" for item in preview.outcomes)


def test_annotation_owner_cannot_be_excluded(tmp_path):
    request = migration(tmp_path).model_copy(
        update={"kind": "annotations", "excluded": ("src/api.py",)}
    )
    with pytest.raises(ValueError, match="exclusions"):
        prepare_source_migration(tmp_path, request)


def test_non_utf8_caller_is_explicitly_unsupported(tmp_path):
    request = migration(tmp_path)
    (tmp_path / "src/consumer.py").write_bytes(b"# coding: latin-1\nfrom api import old\n")
    preview = prepare_source_migration(tmp_path, request)
    assert not preview.ready
    assert any(
        item.path == "src/consumer.py" and item.state == "unsupported" for item in preview.outcomes
    )


def test_relative_alias_import_move(tmp_path):
    request = migration(tmp_path, consumer="from .api import old as invoke\nanswer = invoke(1)\n")
    request = request.model_copy(
        update={
            "roots": (SourceRoot(path="src", module="pkg"),),
            "sources": (request.sources[0].model_copy(update={"module": "pkg.api"}),),
            "old_name": "pkg.api.old",
            "new_name": "pkg.api.new",
        }
    )
    preview = prepare_source_migration(tmp_path, request)
    assert preview.ready
    assert preview.after["src/consumer.py"] == "from .api import new\nanswer = new(1)\n"


@pytest.mark.parametrize(
    "consumer",
    ["from exports import old\nanswer = old(1)\n", "import exports\nanswer = exports.old(1)\n"],
)
def test_reexport_chain_is_unresolved_instead_of_silently_broken(tmp_path, consumer):
    request = migration(tmp_path, consumer=consumer)
    (tmp_path / "src/exports.py").write_text("from api import old\n")
    preview = prepare_source_migration(tmp_path, request)
    assert not preview.ready
    assert any(
        item.path == "src/consumer.py" and item.state == "unresolved" for item in preview.outcomes
    )


def test_semantic_preparation_change_invalidates_readiness(tmp_path, monkeypatch):
    from corpus_structure.schema import source_migrations

    request = migration(tmp_path)
    preview = prepare_source_migration(tmp_path, request)
    monkeypatch.setattr(source_migrations, "preparation_identity", lambda: "changed-compiler")
    with pytest.raises(ValueError, match="semantic preparation"):
        source_migrations.check_source_migration(tmp_path, preview)


@pytest.mark.parametrize(
    "consumer",
    [
        "import api\ndef call(name): return getattr(api, name)(1)\n",
        "import api\nlookup = getattr\ndef call(name): return lookup(api, name)(1)\n",
    ],
)
def test_nonliteral_dynamic_lookup_is_not_claimed_covered(tmp_path, consumer):
    preview = prepare_source_migration(tmp_path, migration(tmp_path, consumer=consumer))
    assert not preview.ready
    assert any(item.state == "unresolved" for item in preview.outcomes)


@pytest.mark.parametrize(
    "consumer",
    [
        "from api import old as invoke\ndef call(new): return invoke(1)\n",
        "from api import old as invoke\ndef new(): return 2\nanswer = invoke(1)\n",
    ],
)
def test_destination_local_name_collision_blocks_alias_normalization(tmp_path, consumer):
    request = migration(tmp_path, consumer=consumer)
    preview = prepare_source_migration(tmp_path, request)
    assert not preview.ready


def test_unrelated_mixed_imports_are_unchanged(tmp_path):
    request = migration(tmp_path, consumer="from .helpers import x\nfrom pkg.helpers import y\n")
    request = request.model_copy(
        update={
            "roots": (SourceRoot(path="src", module="pkg"),),
            "sources": (request.sources[0].model_copy(update={"module": "pkg.api"}),),
            "old_name": "pkg.api.old",
            "new_name": "pkg.api.new",
        }
    )
    preview = prepare_source_migration(tmp_path, request)
    assert preview.ready
    assert "src/consumer.py" not in preview.after


def test_symbol_move_cannot_silently_change_keyword_contract(model_checkout):
    root, _ = model_checkout
    request = migration(root, consumer="from api import old\nanswer = old(x=1)\n")
    owner = request.sources[0]
    after = (
        owner.after.replace("x: int", "y: int")
        .replace("return x", "return y")
        .replace("'parameter': 'x'", "'parameter': 'y'")
    )
    request = request.model_copy(update={"sources": (owner.model_copy(update={"after": after}),)})
    with pytest.raises(ModelError, match="cannot change the callable contract"):
        prepare_preview(
            root, ChangeRequest(data_operations="target.yaml", source_migrations=(request,))
        )
    assert (root / "src/api.py").read_text().startswith("def old(x:")


def test_authored_source_outside_compiled_input_closure_refuses(model_checkout):
    root, _ = model_checkout
    request = migration(root)
    before = "def other(x):\n    return x\n"
    (root / "src/other.py").write_text(before)
    owner = AuthoredSourceChange(
        path="src/other.py",
        module="other",
        before=sha256(before.encode()).hexdigest(),
        after="def other(x: int) -> int:\n    return x\n",
    )
    request = request.model_copy(update={"kind": "annotations", "sources": (owner,)})
    with pytest.raises(ModelError, match="outside the acquired operation source closure"):
        prepare_preview(
            root, ChangeRequest(data_operations="target.yaml", source_migrations=(request,))
        )


def context_migration(
    root, *, consumer="from api import old, new\ndef invoke(context):\n    return old(1)\n"
):
    from corpus_structure.schema.source_migrations import CallContextChange

    request = migration(root, consumer=consumer)
    # This proposed owner supplies a genuine separately named/context-bearing callable.
    source = request.sources[0]
    after = source.after + "def bound(x: int, context: int) -> int:\n    return x + context\n"
    return request.model_copy(
        update={
            "kind": "call_context",
            "sources": (source.model_copy(update={"after": after}),),
            "calls": (
                CallContextChange(
                    path="src/consumer.py",
                    before="old(1)",
                    after="new(context)",
                    context_names=("context",),
                ),
            ),
        }
    )


def test_call_context_uses_explicit_qualified_owner_and_supplied_context(tmp_path):
    preview = prepare_source_migration(tmp_path, context_migration(tmp_path))
    assert preview.ready
    assert (
        preview.after["src/consumer.py"]
        == "from api import new\ndef invoke(context):\n    return new(context)\n"
    )
    namespace = {}
    exec(
        preview.after["src/consumer.py"].replace(
            "from api import new", "def new(value): return value + 3"
        ),
        namespace,
    )
    assert namespace["invoke"](7) == 10


def test_call_context_does_not_guess_dynamic_receiver(tmp_path):
    request = context_migration(
        tmp_path, consumer="def invoke(receiver, context):\n    return receiver.old(1)\n"
    )
    preview = prepare_source_migration(tmp_path, request)
    assert not preview.ready
    assert any(item.state == "unresolved" for item in preview.outcomes)


def test_call_context_refuses_context_bound_only_in_another_scope(tmp_path):
    request = context_migration(
        tmp_path,
        consumer="from api import old, new\ndef other(context): return context\ndef invoke():\n    return old(1)\n",
    )
    preview = prepare_source_migration(tmp_path, request)
    assert not preview.ready


def test_call_context_refuses_unmapped_additional_owned_call(tmp_path):
    request = context_migration(
        tmp_path,
        consumer="from api import old, new\ndef invoke(context):\n    return old(1) + old(2)\n",
    )
    preview = prepare_source_migration(tmp_path, request)
    assert not preview.ready


def test_call_context_refuses_shadowed_same_spelled_callable(tmp_path):
    request = context_migration(tmp_path, consumer="def invoke(old, context):\n    return old(1)\n")
    assert not prepare_source_migration(tmp_path, request).ready


def test_owned_call_context_preview_and_existing_apply(model_checkout):
    root, _ = model_checkout
    request = context_migration(root)
    preview = prepare_preview(
        root, ChangeRequest(data_operations="target.yaml", source_migrations=(request,))
    )
    assert preview.source_migrations[0].ready
    apply_preview(root, preview)
    assert "return new(context)" in (root / "src/consumer.py").read_text()
    apply_preview(root, preview)


def test_call_context_correspondence_must_belong_to_effective_owner(model_checkout):
    root, _ = model_checkout
    request = context_migration(root).model_copy(update={"old_name": "api.unowned"})
    with pytest.raises(ModelError, match="owned callable"):
        prepare_preview(
            root, ChangeRequest(data_operations="target.yaml", source_migrations=(request,))
        )


def test_call_context_retains_exact_declaration_owned_selector_proof(tmp_path):
    from corpus_structure.schema.source_migrations import CallContextChange

    src = tmp_path / "src"
    src.mkdir()
    before = b"class Owner:\n    __selection_operation__ = {'id': 'urn:old-selection'}\n    def select(self, view, config):\n        return view\n"
    (src / "api.py").write_bytes(before)
    (src / "consumer.py").write_text(
        "from api import Owner\ndef invoke(receiver, view, config, inputs):\n    return Owner.select(receiver, view, config)\n"
    )
    request = SourceMigration(
        kind="call_context",
        owner="urn:old-selection",
        new_owner="urn:producer",
        sources=(
            AuthoredSourceChange(
                path="src/api.py",
                module="api",
                before=sha256(before).hexdigest(),
                after="class Owner:\n    def select_hydrated(self, inputs):\n        return inputs\n",
            ),
        ),
        roots=(SourceRoot(path="src", module=""),),
        old_name="api.Owner.select",
        new_name="api.Owner.select_hydrated",
        calls=(
            CallContextChange(
                path="src/consumer.py",
                before="Owner.select(receiver, view, config)",
                after="Owner.select_hydrated(receiver, inputs)",
                context_names=("inputs",),
            ),
        ),
    )
    preview = prepare_source_migration(tmp_path, request)
    assert preview.ready
    (proof,) = preview.call_proofs
    assert proof.owner == "urn:old-selection" and proof.callable == "api.Owner.select"
    assert proof.source_digest == sha256(before).hexdigest()
    assert proof.signature == "select(view, config)"
    assert "return Owner.select_hydrated(receiver, inputs)" in preview.after["src/consumer.py"]


def test_call_context_coordinates_removed_owner_import_and_actual_caller(tmp_path, monkeypatch):
    import sys
    from types import ModuleType

    request = context_migration(tmp_path)
    preview = prepare_source_migration(tmp_path, request)
    assert preview.ready
    api = ModuleType("api")
    exec(preview.after["src/api.py"], api.__dict__)
    monkeypatch.setitem(sys.modules, "api", api)
    consumer = {}
    exec(preview.after["src/consumer.py"], consumer)
    assert consumer["invoke"](17) == 17


def test_call_context_refuses_owned_callable_value_escape(tmp_path):
    request = context_migration(
        tmp_path,
        consumer="from api import old, new\ndef invoke(context):\n    callback = old\n    return old(1)\n",
    )
    preview = prepare_source_migration(tmp_path, request)
    assert not preview.ready


def test_authored_body_update_compiles_drift_without_renaming(model_checkout):
    root, _ = model_checkout
    move = migration(root)
    owner = move.sources[0]
    content = (root / owner.path).read_text().replace("return x\n", "return x + 1\n")
    update = move.model_copy(
        update={
            "kind": "authored_update",
            "old_name": None,
            "new_name": None,
            "sources": (owner.model_copy(update={"after": content}),),
        }
    )
    preview = prepare_preview(
        root, ChangeRequest(data_operations="target.yaml", source_migrations=(update,))
    )
    assert preview.source_migrations[0].ready
    assert preview.source_comparison is not None
    assert {"implementation", "recipe"} <= {
        item.facet for item in preview.source_comparison.changes
    }
    assert (root / "src/api.py").read_text() != content
    assert all(outcome.source_digest for outcome in preview.source_migrations[0].outcomes)
    assert preview.discovery is not None
    assert preview.discovery["backend"] == "ast-grep-py"
    apply_preview(root, preview)
    assert (root / "src/api.py").read_text() == content


def test_real_cli_authored_preview_sources_apply_and_retry(model_checkout, monkeypatch, tmp_path):
    import json

    import yaml
    from typer.testing import CliRunner

    from corpus_structure.cli import recipes
    from corpus_structure.cli.app import build_full_app

    app = build_full_app()

    root, _ = model_checkout
    move = migration(root)
    owner = move.sources[0]
    content = (root / owner.path).read_text().replace("return x\n", "return x + 2\n")
    update = move.model_copy(
        update={
            "kind": "authored_update",
            "old_name": None,
            "new_name": None,
            "sources": (owner.model_copy(update={"after": content}),),
        }
    )
    request = root / "change.yaml"
    request.write_text(
        yaml.safe_dump(
            ChangeRequest(data_operations="target.yaml", source_migrations=(update,)).model_dump(
                mode="json"
            )
        )
    )
    monkeypatch.setattr(recipes, "checkout", lambda ctx=None: root)
    monkeypatch.setenv("CORPUS_CI_RESULTS", str(tmp_path / "cli-results"))
    runner = CliRunner()
    result = runner.invoke(app, ["model", "change", "preview", str(request), "--json"])
    assert result.exit_code == 0, result.output
    identifier = json.loads(result.stdout)["result_id"]
    assert (root / owner.path).read_text() != content
    viewed = runner.invoke(
        app, ["model", "change", "inspect", identifier, "--view", "sources", "--json"]
    )
    assert viewed.exit_code == 0, viewed.output
    report = json.loads(viewed.stdout)
    assert report["migrations"][0]["ready"]
    assert report["outcomes"]
    assert "recipe" in {row["facet"] for row in report["comparison"]["changes"]}
    for _ in range(2):
        applied = runner.invoke(app, ["model", "change", "apply", identifier, "--json"])
        assert applied.exit_code == 0, applied.output
    assert (root / owner.path).read_text() == content


@pytest.mark.parametrize(
    "filename,classname,owner",
    [
        ("m1_declared.py", "M1SourceCandidatesOperation", "extract.m1_candidates"),
        (
            "contextual_declared.py",
            "ContextualRetrievalOperation",
            "retrieve.contextual/declared",
        ),
        (
            "captured_document_composition.py",
            "ComposeCapturedDocumentOperation",
            "text.compose_view/captured-full-native",
        ),
    ],
)
def test_actual_family_source_and_caller_move_preserves_dispatch(
    tmp_path, filename, classname, owner
):
    import __future__

    import ast
    from types import SimpleNamespace

    directory = tmp_path / "src"
    directory.mkdir()
    actual = Path(__file__).parents[2] / "src/corpus_structure/methods" / filename
    raw = actual.read_bytes()
    (directory / filename).write_bytes(raw)
    module = "corpus_structure.methods." + filename.removesuffix(".py")
    renamed = "Updated" + classname
    (directory / "consumer.py").write_text(
        f"from {module} import {classname}\nselected = {classname}\n"
    )
    (directory / "independent.py").write_text("value = 17\n")
    request = SourceMigration(
        kind="symbol_move",
        owner=owner,
        old_name=module + "." + classname,
        new_name=module + "." + renamed,
        roots=(SourceRoot(path="src", module="corpus_structure.methods"),),
        sources=(
            AuthoredSourceChange(
                path="src/" + filename,
                module=module,
                before=sha256(raw).hexdigest(),
                after=raw.decode().replace(classname, renamed),
            ),
        ),
    )
    preview = prepare_source_migration(tmp_path, request)
    assert preview.ready
    assert (
        preview.after["src/consumer.py"]
        == f"from {module} import {renamed}\nselected = {renamed}\n"
    )
    unchanged = next(row for row in preview.outcomes if row.path == "src/independent.py")
    assert unchanged.state == "already_satisfied"
    assert unchanged.sites == ()
    assert any(row.sites for row in preview.outcomes if row.path == "src/consumer.py")

    # Execute the real adapter's run body with controlled delegated kernels. The
    # test exercises source transformation and argument/order/receiver fidelity,
    # not provider inference or publication qualification.
    def run_body(source, name):
        tree = ast.parse(source)
        classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
        if filename == "captured_document_composition.py":
            shared = ast.parse(actual.with_name("full_document_composition.py").read_bytes())
            classes.update(
                (node.name, node) for node in shared.body if isinstance(node, ast.ClassDef)
            )

        cls = classes[name]
        while True:
            methods = [
                node
                for node in cls.body
                if isinstance(node, ast.FunctionDef) and node.name == "run"
            ]
            if methods:
                (run,) = methods
                break
            assert len(cls.bases) == 1 and isinstance(cls.bases[0], ast.Name)
            cls = classes[cls.bases[0].id]

        calls, orderings = [], []

        def kernel(*args):
            calls.append(args)
            return {"selected": "independent"}

        def streaming(*args):
            calls.append(args)
            yield "physical-step"
            return {"selected": "independent"}

        def order_composition(sources, products):
            orderings.append((sources, products))
            return sources, tuple(reversed(products))

        namespace = dict(
            execute_declared_m1=streaming,
            execute_retrieval_profile=kernel,
            execute_view_profile=kernel,
            ordered_composition_inputs=order_composition,
        )
        executable = ast.Module(body=[run], type_ignores=[])
        exec(
            compile(executable, filename, "exec", flags=__future__.annotations.compiler_flag),
            namespace,
        )
        function = cast(Callable[..., object], namespace["run"])
        receiver = SimpleNamespace(marker="authentic receiver")
        if filename == "m1_declared.py":
            args = ({"primary": 1}, {"annotations": 2}, {"construction": 3}, ({"source": 4},))
            stream = function(receiver, *args)
            assert isinstance(stream, Generator)
            assert next(stream) == "physical-step"
            with pytest.raises(StopIteration) as stopped:
                next(stream)
            assert stopped.value.value == {"selected": "independent"}
            assert calls == [(receiver, *args)]
        elif filename == "contextual_declared.py":
            args = ({"query": 1}, {"inventory": 2}, {"vectors": 3}, {"policy": 4}, {"scores": 5})
            assert function(receiver, *args) == {"selected": "independent"}
            assert calls == [(receiver, *args)]
        else:
            groups = tuple(({"group": i},) for i in range(8))
            assert function(receiver, *groups) == {"selected": "independent"}
            expected = tuple({"group": i} for i in range(1, 8))
            assert orderings == [(groups[0], expected)]
            ordered = tuple(reversed(expected))
            assert calls == [(receiver, groups[0], ordered, ordered, "full_characterization")]
        return calls[0][1:]

    assert run_body(raw, classname) == run_body(preview.after["src/" + filename], renamed)


@pytest.mark.parametrize("inherited", [False, True])
def test_owned_class_move_compiles_complete_interface_and_existing_apply(model_checkout, inherited):
    root, _ = model_checkout
    move = migration(root, consumer="from api import OldOperation\nselected = OldOperation\n")
    metadata = operation_metadata()
    metadata["entrypoints"] = ["run"]
    before = (
        "class OldOperation:\n    __data_operation__ = "
        + repr(metadata)
        + "\n    def run(self, x: int) -> int:\n        return x\n"
    ).encode()
    if inherited:
        base_metadata = {**metadata, "abstract": True}
        before = (
            "class BaseOperation:\n    __data_operation__ = "
            + repr(base_metadata)
            + "\n    def run(self, x: int) -> int:\n        return x\nclass OldOperation(BaseOperation):\n    __data_operation__ = {'abstract': False}\n"
        ).encode()
    (root / "src/api.py").write_bytes(before)
    owner = move.sources[0].model_copy(
        update={
            "before": sha256(before).hexdigest(),
            "after": before.decode().replace("OldOperation", "NewOperation"),
        }
    )
    request = move.model_copy(
        update={"old_name": "api.OldOperation", "new_name": "api.NewOperation", "sources": (owner,)}
    )
    preview = prepare_preview(
        root, ChangeRequest(data_operations="target.yaml", source_migrations=(request,))
    )
    assert preview.source_migrations[0].ready
    assert preview.source_comparison is not None
    apply_preview(root, preview)
    assert (
        root / "src/consumer.py"
    ).read_text() == "from api import NewOperation\nselected = NewOperation\n"
    assert "class NewOperation" in (root / "src/api.py").read_text()


def test_declared_preview_uses_explicit_archived_source_comparison(model_checkout):
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.data_operation_preparation import prepare_data_operation_inputs
    from corpus_structure.semantic.source_comparison import compare_data_operation_models

    root, _ = model_checkout
    migration(root)
    before = bound_data_operation_model(prepare_data_operation_inputs(root, "target.yaml")[3])
    path = root / "src/api.py"
    path.write_text(path.read_text().replace("return x\n", "return x + 9\n"))
    after = bound_data_operation_model(prepare_data_operation_inputs(root, "target.yaml")[3])
    comparison = compare_data_operation_models(before, after)
    from corpus_structure.semantic.model_comparison import compare_declared_models

    declared = compare_declared_models(before, after).model_dump(mode="json")
    preview = prepare_preview(
        root,
        ChangeRequest(data_operations="target.yaml"),
        source_comparison=comparison,
        comparison=declared,
    )
    assert preview.source_migrations == ()
    assert preview.source_comparison == comparison
    assert preview.comparison == declared
    with pytest.raises(ModelError, match="declared model comparison differs"):
        prepare_preview(
            root,
            ChangeRequest(data_operations="target.yaml"),
            comparison={**declared, "after_digest": "0" * 64},
        )
    with pytest.raises(ModelError, match="different model pairs"):
        prepare_preview(
            root,
            ChangeRequest(data_operations="target.yaml"),
            source_comparison=comparison,
            comparison={**declared, "before_digest": "0" * 64},
        )
    assert "recipe" in {row.facet for row in comparison.changes}
    with pytest.raises(ModelError, match="source comparison differs"):
        prepare_preview(
            root,
            ChangeRequest(data_operations="target.yaml"),
            source_comparison=comparison.model_copy(update={"after_digest": "0" * 64}),
        )


def test_native_cli_compares_archived_ddo_without_source_migrations(
    model_checkout, commit_db_engine, commit_application_settings, monkeypatch, tmp_path
):
    import json

    import yaml
    from sqlalchemy import select
    from typer.testing import CliRunner

    from corpus_structure.cli import recipes
    from corpus_structure.cli.app import build_full_app

    app = build_full_app()
    from corpus_structure.cli.output import CliState
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.data_operation_preparation import prepare_data_operation_inputs
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.migrations import current_revision
    from corpus_structure.semantic.releases import open_release, persist_release

    root, _ = model_checkout
    migration(root)
    bundle, dependencies, profile, archived = prepare_data_operation_inputs(root, "target.yaml")
    old_model = bound_data_operation_model(archived)
    with commit_db_engine.begin() as connection:
        persist_release(connection, bundle, dependencies, profile, archived)
        predecessor = current_revision(connection)
        before_releases = connection.execute(select(table("sem.release").c.release_id)).all()

    # The archived before-source now differs from the checkout. Neither comparison
    # side may be replaced by a second reading of this proposed local source.
    path = root / "src/api.py"
    proposed = path.read_text().replace("return x\n", "return x + 9\n")
    path.write_text(proposed)
    new_model = bound_data_operation_model(prepare_data_operation_inputs(root, "target.yaml")[3])
    configured = commit_application_settings.model_copy(
        update={"ci_results": tmp_path / "native-cli-results"}
    )
    monkeypatch.setattr(recipes, "checkout", lambda ctx=None: root)
    runner = CliRunner()

    def invoke(*args, body=None):
        result = runner.invoke(
            app,
            [*args, "--json"],
            input=body,
            obj=CliState(settings_factory=lambda: configured),
        )
        assert result.exit_code == 0, result.output
        return json.loads(result.stdout)

    request = ChangeRequest(data_operations="target.yaml", archive_release=archived.release_id)
    assert request.source_migrations == ()
    preview = invoke(
        "model", "change", "preview", "-", body=yaml.safe_dump(request.model_dump(mode="json"))
    )
    sources = invoke("model", "change", "inspect", preview["result_id"], "--view", "sources")
    assert sources["migrations"] == sources["outcomes"] == []
    comparison = sources["comparison"]
    assert comparison["before_digest"] == sha256(old_model.content).hexdigest()
    assert comparison["after_digest"] == sha256(new_model.content).hexdigest()
    assert comparison["before_digest"] != comparison["after_digest"]
    assert {change["facet"] for change in comparison["changes"]} == {"implementation", "recipe"}
    assert {change["operation"] for change in comparison["changes"]} == {"urn:test:source-change"}
    assert comparison["breakages"] == []
    declared = invoke("model", "change", "inspect", preview["result_id"], "--view", "model")
    assert declared["comparison"]["version"] == "declared-data-model-comparison-v1"
    assert declared["comparison"]["before_digest"] == sha256(old_model.content).hexdigest()
    assert declared["comparison"]["after_digest"] == sha256(new_model.content).hexdigest()
    assert any(
        change["model_ref"] == "urn:test:source-change/recipe"
        for change in declared["comparison"]["changes"]
    )
    assert declared["comparison"]["complete"]

    unbound = invoke(
        "model", "change", "preview", "-", body=yaml.safe_dump({"data_operations": "target.yaml"})
    )
    unavailable = invoke("model", "change", "inspect", unbound["result_id"], "--view", "sources")
    assert unavailable["comparison"] is None
    assert path.read_text() == proposed
    with commit_db_engine.connect() as connection:
        assert current_revision(connection) == predecessor
        assert (
            connection.execute(select(table("sem.release").c.release_id)).all() == before_releases
        )
        retained = bound_data_operation_model(open_release(connection, archived.release_id))
    assert retained.content == old_model.content
    assert retained.source_interfaces == old_model.source_interfaces
