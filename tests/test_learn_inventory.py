from pathlib import Path

import pytest

from app.learn_inventory import RAW_FIXTURES_DIR, get_inventory_payload, list_inventory_fixtures


def test_raw_fixtures_exist() -> None:
    assert (RAW_FIXTURES_DIR / "aws_toxic_ssh_bucket.json").is_file()
    assert (RAW_FIXTURES_DIR / "gcp_toxic_ssh_bucket.json").is_file()


def test_aws_inventory_has_raw_and_normalized() -> None:
    data = get_inventory_payload("aws", normalized_preview_limit=10)
    assert data["raw"]["cloud"] == "aws"
    assert "nodes" in data["normalized"]
    assert data["normalized"]["_preview"]["totals"]["nodes"] > 0


def test_enterprise_inventory_truncates() -> None:
    data = get_inventory_payload("enterprise", normalized_preview_limit=10)
    assert len(data["normalized"]["assets"]) == 10
    assert data["normalized"]["_preview"]["totals"]["assets"] == 500


def test_unknown_fixture_raises() -> None:
    with pytest.raises(ValueError):
        get_inventory_payload("nope")
