"""Keep the Maverick detection population separate from proposed co-membership."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, NonNegativeInt

from .pm2_products import ParserProduct, ParserProducts
from .pm2_source import MappedSource, PM2TokenMap, SourceMapRefused, map_maverick


class Mention(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    first: NonNegativeInt
    last: NonNegativeInt
    detected: bool
    supplied: bool
    clustered: bool


class LocalCluster(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    ordinal: NonNegativeInt
    member_keys: tuple[str, ...]


def maverick_products(
    mapping: PM2TokenMap, request: Mapping[str, Any], reply: Mapping[str, Any]
) -> ParserProducts:
    sentences = [
        [token.text for token in mapping.sentence_tokens(index)]
        for index in sorted({token.sentence for token in mapping.tokens})
    ]
    if request["sentences"] != sentences or reply["tokens"] != [
        token.text for token in mapping.tokens
    ]:
        raise ValueError("Maverick tokens differ from the admitted source map")
    detected = {tuple(span) for span in reply["mentions"]}
    supplied = {tuple(span) for span in request.get("predefined_mentions", ())}
    clusters = [tuple(dict.fromkeys(tuple(pair) for pair in group)) for group in reply["clusters"]]
    assigned = {span for group in clusters for span in group}
    if sum(map(len, clusters)) != len(assigned):
        raise ValueError("canonical Maverick mention has competing membership in one partition")

    locations: dict[str, MappedSource | SourceMapRefused] = {}
    products = []
    for first, last in sorted(detected | supplied | assigned):
        key = f"mention:{first}:{last}"
        location = key + ":extent"
        try:
            locations[location] = map_maverick(
                mapping, first, last, scope_digest=mapping.mapping.scope_digest
            )
        except SourceMapRefused as exc:
            locations[location] = exc
        value = Mention(
            first=first,
            last=last,
            detected=(first, last) in detected,
            supplied=(first, last) in supplied,
            clustered=(first, last) in assigned,
        )
        products.append(ParserProduct(key, "maverick.mention", value.model_dump(), (location,)))
    for index, cluster in enumerate(clusters):
        keys = tuple(f"mention:{first}:{last}" for first, last in sorted(cluster))
        value = LocalCluster(ordinal=index, member_keys=keys)
        products.append(
            ParserProduct(f"cluster:{index}", "maverick.cluster", value.model_dump(), keys)
        )
    return ParserProducts(locations, tuple(products))


def earlier_local_members(mention: str, cluster: LocalCluster) -> tuple[str, ...]:
    """The preceding members are alternatives within this scope, without native ranks."""
    return cluster.member_keys[: cluster.member_keys.index(mention)]
