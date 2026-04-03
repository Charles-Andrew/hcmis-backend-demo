from app.repositories.attendance import _normalize_snapshot_name


def test_normalize_snapshot_name_removes_null_bytes_and_collapses_whitespace():
    assert _normalize_snapshot_name("Nikki\x00\x00 Anne  Cruz\x00") == "Nikki Anne Cruz"


def test_normalize_snapshot_name_handles_none():
    assert _normalize_snapshot_name(None) == ""
