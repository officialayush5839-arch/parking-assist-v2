"""Range / timestamp validation."""

from processing.validation import validate_range, validate_timestamp


def test_range_valid():
    result = validate_range(1.5, 0.1, 4.5)
    assert result.valid
    assert result.reason is None


def test_range_out_of_bounds():
    assert not validate_range(5.0, 0.1, 4.5).valid
    assert not validate_range(-1.0, 0.1, 4.5).valid


def test_range_missing():
    assert not validate_range(None, 0.1, 4.5).valid


def test_range_non_numeric():
    assert not validate_range("abc", 0.1, 4.5).valid


def test_timestamp_stale():
    import time

    assert not validate_timestamp(time.time() - 60, max_age_s=5.0).valid


def test_timestamp_fresh():
    import time

    assert validate_timestamp(time.time(), max_age_s=5.0).valid


def test_timestamp_missing():
    assert not validate_timestamp(None, max_age_s=5.0).valid