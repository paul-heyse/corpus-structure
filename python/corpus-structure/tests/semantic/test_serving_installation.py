"""Installation changes invalidate continuation without granting cache reuse."""

import pytest

from corpus_structure._query_custody import SourceCustodyError
from corpus_structure.semantic.serving_installation import _capture_installation


@pytest.mark.parametrize("mutation", ["changed-resource", "added-source", "removed-source"])
def test_installation_refuses_observed_drift(tmp_path, mutation):
    source = tmp_path / "selection.py"
    source.write_text("order = 1\n")
    resource = tmp_path / "policy.yaml"
    resource.write_text("limit: 4\n")
    installation = _capture_installation(tmp_path)
    assert installation.digest == _capture_installation(tmp_path).digest
    if mutation == "changed-resource":
        resource.write_text("limit: 5\n")
    elif mutation == "added-source":
        (tmp_path / "extra.py").write_text("policy = 2\n")
    else:
        source.unlink()
    with pytest.raises(SourceCustodyError, match="restart required"):
        installation.check()
