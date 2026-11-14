"""Independent source expectations and existing file-publication custody."""

from copy import deepcopy
from hashlib import sha256

import pytest
from model_change_support import model_checkout as model_checkout

from corpus_structure.schema import model
from corpus_structure.schema.model_change import ChangeRequest, apply_preview, prepare_preview
from corpus_structure.schema.source_migrations import (
    AuthoredSourceChange,
    SourceMigration,
    SourceRoot,
    prepare_source_migration,
)
from corpus_structure.semantic.identity import claim_source_item__data_operation__


def migration(root, *, consumer="from api import old\nanswer = old(1)\n"):
    directory = root / "src"
    directory.mkdir()
    metadata = deepcopy(claim_source_item__data_operation__)
    metadata["id"] = "urn:test:source-change"
    metadata["roles"][0]["parameter"] = "x"
    metadata["roles"][1]["kind"] = "integer"
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
    with pytest.raises(model.ModelError, match="membership"):
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
    with pytest.raises(model.ModelError, match="unresolved"):
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
    with pytest.raises(model.ModelError, match="cannot change the callable contract"):
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
    with pytest.raises(model.ModelError, match="outside the acquired operation source closure"):
        prepare_preview(
            root, ChangeRequest(data_operations="target.yaml", source_migrations=(request,))
        )


def context_migration(root, *, consumer="from api import old, new\ndef invoke(context):\n    return old(1)\n"):
    from corpus_structure.schema.source_migrations import CallContextChange

    request = migration(root, consumer=consumer)
    # This proposed owner supplies a genuine separately named/context-bearing callable.
    source = request.sources[0]
    after = source.after + "def bound(x: int, context: int) -> int:\n    return x + context\n"
    return request.model_copy(update={
        "kind": "call_context",
        "sources": (source.model_copy(update={"after": after}),),
        "calls": (CallContextChange(path="src/consumer.py", before="old(1)", after="new(context)", context_names=("context",)),),
    })


def test_call_context_uses_explicit_qualified_owner_and_supplied_context(tmp_path):
    preview = prepare_source_migration(tmp_path, context_migration(tmp_path))
    assert preview.ready
    assert preview.after["src/consumer.py"] == "from api import old, new\ndef invoke(context):\n    return new(context)\n"
    namespace = {}
    exec(preview.after["src/consumer.py"].replace("from api import old, new", "def new(value): return value + 3"), namespace)
    assert namespace["invoke"](7) == 10


def test_call_context_does_not_guess_dynamic_receiver(tmp_path):
    request = context_migration(tmp_path, consumer="def invoke(receiver, context):\n    return receiver.old(1)\n")
    preview = prepare_source_migration(tmp_path, request)
    assert not preview.ready
    assert any(item.state == "unresolved" for item in preview.outcomes)


def test_call_context_refuses_context_bound_only_in_another_scope(tmp_path):
    request = context_migration(tmp_path, consumer="from api import old, new\ndef other(context): return context\ndef invoke():\n    return old(1)\n")
    preview = prepare_source_migration(tmp_path, request)
    assert not preview.ready


def test_call_context_refuses_unmapped_additional_owned_call(tmp_path):
    request = context_migration(tmp_path, consumer="from api import old, new\ndef invoke(context):\n    return old(1) + old(2)\n")
    preview = prepare_source_migration(tmp_path, request)
    assert not preview.ready


def test_call_context_refuses_shadowed_same_spelled_callable(tmp_path):
    request = context_migration(tmp_path, consumer="def invoke(old, context):\n    return old(1)\n")
    assert not prepare_source_migration(tmp_path, request).ready


def test_owned_call_context_preview_and_existing_apply(model_checkout):
    root, _ = model_checkout
    request = context_migration(root)
    preview = prepare_preview(root, ChangeRequest(data_operations="target.yaml", source_migrations=(request,)))
    assert preview.source_migrations[0].ready
    apply_preview(root, preview)
    assert "return new(context)" in (root / "src/consumer.py").read_text()
    apply_preview(root, preview)


def test_call_context_correspondence_must_belong_to_effective_owner(model_checkout):
    root, _ = model_checkout
    request = context_migration(root).model_copy(update={"old_name": "api.unowned"})
    with pytest.raises(model.ModelError, match="owned callable"):
        prepare_preview(root, ChangeRequest(data_operations="target.yaml", source_migrations=(request,)))


def test_call_context_retains_exact_declaration_owned_selector_proof(tmp_path):
    from corpus_structure.schema.source_migrations import CallContextChange

    src = tmp_path / "src"
    src.mkdir()
    before = b"class Owner:\n    __selection_operation__ = {'id': 'urn:old-selection'}\n    def select(self, view, config):\n        return view\n"
    (src / "api.py").write_bytes(before)
    (src / "consumer.py").write_text("from api import Owner\ndef invoke(receiver, view, config, inputs):\n    return Owner.select(receiver, view, config)\n")
    request = SourceMigration(
        kind="call_context", owner="urn:old-selection", new_owner="urn:producer",
        sources=(AuthoredSourceChange(path="src/api.py", module="api", before=sha256(before).hexdigest(), after="class Owner:\n    def select_hydrated(self, inputs):\n        return inputs\n"),),
        roots=(SourceRoot(path="src", module=""),), old_name="api.Owner.select", new_name="api.Owner.select_hydrated",
        calls=(CallContextChange(path="src/consumer.py", before="Owner.select(receiver, view, config)", after="Owner.select_hydrated(receiver, inputs)", context_names=("inputs",)),),
    )
    preview = prepare_source_migration(tmp_path, request)
    assert preview.ready
    (proof,) = preview.call_proofs
    assert proof.owner == "urn:old-selection" and proof.callable == "api.Owner.select"
    assert proof.source_digest == sha256(before).hexdigest()
    assert proof.signature == "select(view, config)"
    assert "return Owner.select_hydrated(receiver, inputs)" in preview.after["src/consumer.py"]
