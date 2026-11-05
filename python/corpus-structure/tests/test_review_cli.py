"""Offline review entrypoints do not construct database settings."""

import json


def test_review_help_is_lazy(cli):
    def refuse():
        raise AssertionError("settings should be lazy")

    for arguments in (
        ("review", "--help"),
        ("review", "verify", "--help"),
        ("structure", "list", "--help"),
    ):
        result = cli(*arguments, settings=refuse)
        assert result.exit_code == 0, result.output


def test_offline_verify_refuses_missing_bundle_without_settings(cli, tmp_path):
    def refuse():
        raise AssertionError("offline verification opened settings")

    result = cli("review", "verify", str(tmp_path / "missing"), "--json", settings=refuse)
    assert result.exit_code == 1
    error = json.loads(result.stdout)["error"]
    assert error["code"] == "ValueError"
    assert error["message"] == "review member missing or not an ordinary file"
