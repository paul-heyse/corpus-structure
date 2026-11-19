"""Source choices from the authenticated operation inputs of one release."""

from pathlib import PurePosixPath

import yaml
from pydantic import BaseModel, ConfigDict, TypeAdapter, model_validator

PACK_BINDINGS = "operation/source-packs.json"


class SourcePackBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str
    module: str
    prefix: str

    @model_validator(mode="after")
    def canonical(self):
        if (
            not self.name
            or self.name in {".", ".."}
            or PurePosixPath(self.name).name != self.name
            or not self.module
            or self.prefix not in {"", f"pack/{self.name}/"}
        ):
            raise ValueError("invalid archived source pack binding")
        return self


def source_slices(dependencies, domain: str | None) -> dict:
    """Resolve the supplied pack name and slices entirely from retained bytes."""
    from corpus_structure.orchestrate.source_request import SourceRequestError

    artifacts = {artifact.name: artifact.content for artifact in dependencies.artifacts}
    if len(artifacts) != len(dependencies.artifacts):
        raise SourceRequestError("release repeats an archived operation input")
    try:
        if PACK_BINDINGS in artifacts:
            bindings = TypeAdapter(tuple[SourcePackBinding, ...]).validate_json(
                artifacts[PACK_BINDINGS]
            )
        else:
            # Historical composed artifacts already retain the pack directory name.
            names = {
                name.split("/")[1]
                for name in artifacts
                if name.startswith("pack/")
                and any(
                    name.endswith("/operation/" + filename)
                    for filename in (
                        "methods.yaml",
                        "guideline.md",
                        "slices.yaml",
                        "pm2-definition-policy.json",
                    )
                )
            }
            bindings = tuple(
                SourcePackBinding(name=name, module=name, prefix=f"pack/{name}/")
                for name in sorted(names)
            )
        if len({binding.name for binding in bindings}) != len(bindings):
            raise SourceRequestError("release repeats a source pack binding")
        if not bindings and domain is None:
            prefix = ""
        else:
            selected = [binding for binding in bindings if domain is None or binding.name == domain]
            if len(selected) != 1:
                raise SourceRequestError("select one archived source pack with --domain")
            prefix = selected[0].prefix
        content = artifacts.get(prefix + "operation/slices.yaml")
        scopes = {} if content is None else yaml.safe_load(content)
        if not isinstance(scopes, dict):
            raise SourceRequestError("archived source slices require a mapping")
        return scopes
    except (ValueError, yaml.YAMLError) as error:
        raise SourceRequestError(f"invalid archived source selection: {error}") from error
