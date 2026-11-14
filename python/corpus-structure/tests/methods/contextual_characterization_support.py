"""Controlled inputs and builders shared by the contextual characterization consumers."""

from corpus_structure.methods.native_evidence import native_run
from corpus_structure.semantic.contextual_characterization import (
    ContextInput,
    ContextPart,
    ContextualLayer,
    digest,
)
from corpus_structure.semantic.product_reference import ProductReference


def context_builder(source):
    view, base, scope, operation = source[3:]
    context = ContextInput.build([ContextPart(view, 0, len(view.text))], scope["selectors"])
    return ContextualLayer(
        base, scope, dict(operation, key="text.contextual_characterization"), context
    )


def add_metadata(builder, providers=("maverick", "dipo")):
    for provider in providers:
        row = native_run(
            provider,
            "fixture",
            "{}",
            model="fixture",
            version="1",
            runtime_version="fixture",
            layout=[],
            text=[],
        )
        row["configuration_codec"] = provider + "-config-json-v1"
        builder.native_runs.append(row)


def dipo_reply():
    return dict(
        mode="learned",
        post_tokenizer_tokens=6,
        edus=[
            dict(tokens=[0, 2], chars=[0, 4], text="X X"),
            dict(tokens=[2, 6], chars=[4, 14], text="é x+y [3]."),
        ],
        spans=[dict(left=[0, 1], right=[1, 2], nuclearity="SN", relation="contingency-condition")],
        boundaries=[
            dict(token_end=2, learned=True, forced=False, disposition="retained"),
            dict(token_end=6, learned=True, forced=False, disposition="retained"),
        ],
    )


def canonical_tokens(builder: ContextualLayer, layers, selected=None):
    pins = (
        [ProductReference(**selected)]
        if selected
        else [
            pin
            for pin, layer in layers.items()
            if any(
                a.get("native_token", {}).get("native_run") == "spacy"
                for a in layer.payload["annotations"]
            )
        ]
    )
    if len(pins) != 1 or pins[0] not in layers:
        raise ValueError("context requires one explicitly selected retained spaCy token population")
    pin = pins[0]
    body = layers[pin].payload
    occurrences = {o["local_id"]: o for o in body["occurrences"]}
    rows = []
    for part_index, part in enumerate(builder.context.parts):
        selected_rows = []
        for annotation in body["annotations"]:
            token = annotation.get("native_token")
            if token is None or token["native_run"] != "spacy" or not token["text"].strip():
                continue
            extents = [e for oid in annotation["occurrences"] for e in occurrences[oid]["extents"]]
            if not all(
                e["projection"] == part.view.ref.projection_digest
                and part.start <= e.get("start", part.start) < e.get("end", part.end) <= part.end
                for e in extents
            ):
                continue
            if "sentence" not in token:
                raise ValueError("context token lacks complete retained sentence ownership")
            if "".join(e["text"] for e in extents) != token["text"]:
                raise ValueError("context token differs from its exact source members")
            for oid in annotation["occurrences"]:
                builder.occurrences.setdefault(oid, occurrences[oid])
            selected_rows.append(
                (
                    extents[0]["start"],
                    dict(
                        text=token["text"],
                        sentence=(part_index, pin, token["sentence"]),
                        occurrences=annotation["occurrences"],
                        source=annotation["local_id"],
                    ),
                )
            )
        rows.extend(row for _, row in sorted(selected_rows, key=lambda item: item[0]))
    if not rows:
        raise ValueError("selected examined context has no retained canonical sentence tokens")
    return rows


def reuse_native(builder: ContextualLayer, layers):
    """Consume original pinned observations, preserving their producer provenance."""
    seen = set()
    for pin, report in layers.items():
        body = report.payload
        annotations = {a["local_id"]: a for a in body["annotations"]}
        raw_families = {"maverick.mentions", "maverick.clusters", "dipo.edus", "dipo.rst"}
        raw = {}
        for key, annotation in annotations.items():
            if annotation["family"] not in raw_families:
                continue
            try:
                raw[key] = builder.proxy(pin, key, family=annotation["family"])
            except ValueError:
                continue
        # Retain native populations as attributed references, including complete
        # group membership. A reference does not claim a new provider invocation.
        for membership in body["memberships"]:
            if membership["group"] not in raw or membership["member"] not in raw:
                continue
            occurrences = {o["local_id"]: o for o in body["occurrences"]}
            for identity in membership["occurrences"]:
                builder.occurrences.setdefault(identity, occurrences[identity])
            builder.memberships.append(
                dict(
                    membership,
                    local_id="retained-membership:"
                    + digest([pin.values(), membership["local_id"]]),
                    group=raw[membership["group"]],
                    member=raw[membership["member"]],
                    scope=raw.get(membership.get("scope"), raw[membership["group"]]),
                    external_premises=[dict(layer=pin.values(), local_id=membership["local_id"])],
                    required_choices=[],
                    required_external_choices=builder.required_choices(pin, membership),
                )
            )
        mentions = {}
        for key, annotation in annotations.items():
            if annotation["kind"] not in {"native.mention", "native.unmapped_mention"}:
                continue
            try:
                proxy = builder.proxy(pin, key, family="context.reference")
            except ValueError:
                continue
            mentions[key] = proxy
            builder._mention_metadata[proxy] = annotation["native_mention"]
        for annotation in annotations.values():
            if annotation["kind"] == "native.coreference_cluster":
                members = [
                    m["member"]
                    for m in body["memberships"]
                    if m["group"] == annotation["local_id"] and m["role"] == "native_member"
                ]
                if all(member in mentions for member in members):
                    group = builder.proxy(pin, annotation["local_id"], family="context.reference")
                    keys = [mentions[member] for member in members]
                    index = {a["local_id"]: a for a in builder.annotations}
                    for order, member in enumerate(keys):
                        builder.membership(
                            group,
                            member,
                            "candidate_member",
                            order,
                            "context.reference",
                            index[member]["occurrences"],
                        )
                    builder._native_clusters.append((group, keys))
            elif (
                annotation["kind"] == "native.rst_node"
                and "condition" in annotation["native_label"].casefold()
            ):
                children = [
                    m
                    for m in body["memberships"]
                    if m["group"] == annotation["local_id"]
                    and m["role"] in {"nucleus", "satellite"}
                ]
                if len(children) != 2:
                    raise ValueError("retained RST evidence omits its directed native children")
                try:
                    native = builder.proxy(pin, annotation["local_id"], family="context.host")
                    proxies = [
                        (child["role"], builder.proxy(pin, child["member"], family="context.host"))
                        for child in children
                    ]
                except ValueError:
                    continue
                index = {a["local_id"]: a for a in builder.annotations}
                if proxies[0][0] == proxies[1][0] == "nucleus":
                    builder._rst_hosts.extend(
                        (
                            (
                                index[proxies[0][1]]["occurrences"],
                                index[proxies[1][1]]["occurrences"],
                                native,
                            ),
                            (
                                index[proxies[1][1]]["occurrences"],
                                index[proxies[0][1]]["occurrences"],
                                native,
                            ),
                        )
                    )
                else:
                    satellite = next(key for role, key in proxies if role == "satellite")
                    nucleus = next(key for role, key in proxies if role == "nucleus")
                    builder._rst_hosts.append(
                        (index[satellite]["occurrences"], index[nucleus]["occurrences"], native)
                    )
        for coverage in body["coverage"]:
            family = coverage["family"]
            if family not in {"maverick.mentions", "maverick.clusters", "dipo.edus", "dipo.rst"}:
                continue
            selectors = [p.selector() for p in builder.context.parts]
            examined = coverage.get("examined", [])
            if not all(
                any(
                    s["projection"] == old["projection"]
                    and old.get("start", 0) <= s["start"]
                    and s["end"] <= old.get("end", s["end"])
                    for old in examined
                )
                for s in selectors
            ):
                continue
            seen.add(family)
            builder.record(
                family,
                selectors,
                "complete" if coverage["outcome"] in {"complete", "empty"} else "partial",
                None
                if coverage["outcome"] in {"complete", "empty"}
                else "retained native family has incomplete coverage",
            )
    for family in {"maverick.mentions", "maverick.clusters", "dipo.edus", "dipo.rst"} - seen:
        builder.record(
            family,
            [p.selector() for p in builder.context.parts],
            "failed",
            "no compatible retained native coverage; reads do not trigger inference",
        )
