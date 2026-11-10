"""Archived vocabulary facts for semantic comparison; no current ontology acquisition."""

from dataclasses import asdict


def vocabulary_facets(prepared):
    """Separate admitted membership, descriptive meaning and source/check provenance."""
    metadata = prepared.vocabulary_metadata
    unknowns = set()
    if metadata["status"] == "corrupt":
        from .releases import ReleaseConflict

        raise ReleaseConflict(metadata["reason"])
    if metadata["status"] != "available":
        unknowns.add("Archived vocabulary metadata unavailable: " + prepared.release_id)
    facets, consumers = {}, {}
    for snapshot in prepared.vocabularies:
        enum = snapshot.enum
        members = {m.value: dict(meaning=m.meaning) for m in snapshot.members}
        facets[("vocabulary_membership", enum)] = members
        facets[("vocabulary_labels", enum)] = {m.value: m.label for m in snapshot.members}
        details = metadata.get("enums", {}).get(enum)
        fields = details.get("fields", []) if details else []
        consumers[enum] = sorted({f"{f['class_name']}.{f['property']}" for f in fields})
        if details is not None:
            descriptions = {}
            checks = {}
            for member in details["members"]:
                value = member["value"]
                descriptions[value] = {
                    k: v
                    for k, v in member.items()
                    if k not in {"value", "status", "source", "source_digest", "coverage"}
                }
                checks[value] = {
                    k: member[k]
                    for k in ("status", "source", "source_digest", "coverage")
                    if k in member
                }
            facets[("vocabulary_metadata", enum)] = descriptions
            facets[("vocabulary_checks", enum)] = dict(
                members=checks, unchecked=details.get("unchecked", [])
            )
        facets[("vocabulary_sources", enum)] = {
            k: v for k, v in asdict(snapshot).items() if k not in {"members", "enum", "unchecked"}
        }
    if metadata["status"] == "available":
        facets[("vocabulary_source_profiles", "sources")] = metadata.get("sources", {})
    return facets, consumers, unknowns


def append_vocabulary_impact(before, after, changes, unknowns, changed_members, missing):
    original_count = len(changes)
    old, old_uses, old_unknown = vocabulary_facets(before)
    new, new_uses, new_unknown = vocabulary_facets(after)
    unknowns.update(old_unknown | new_unknown)
    metadata_available = not (old_unknown or new_unknown)
    for aspect, enum in sorted(old.keys() | new.keys()):
        if not metadata_available and aspect in {
            "vocabulary_metadata",
            "vocabulary_checks",
            "vocabulary_source_profiles",
        }:
            continue
        key = aspect, enum
        left, right = old.get(key, missing), new.get(key, missing)
        if left == right:
            continue
        changes.append(
            dict(
                kind="added" if left is missing else "removed" if right is missing else "changed",
                model_ref="enum:" + enum,
                aspect=aspect,
                consumers=sorted(set(old_uses.get(enum, []) + new_uses.get(enum, []))),
                reason=(
                    "Archived vocabulary facts differ; retained record/review uses "
                    "require an explicitly bound population."
                ),
                members=changed_members(left, right, "enum:" + enum + "/" + aspect),
            )
        )
    if len(changes) != original_count:
        unknowns.add(
            "Retained vocabulary uses were not surveyed; supply an "
            "explicit source/review population for impact assessment."
        )
