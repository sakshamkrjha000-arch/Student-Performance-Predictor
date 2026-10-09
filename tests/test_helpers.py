"""Validation helpers: pure unit tests, no HTTP."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as app_module  # noqa: E402


class TestToFloat:
    def test_valid_value(self):
        assert app_module.to_float("85", 0, 100) == 85.0

    def test_decimal(self):
        assert app_module.to_float("7.5", 0, 10) == 7.5

    def test_out_of_range_returns_none(self):
        assert app_module.to_float("150", 0, 100) is None
        assert app_module.to_float("-5", 0, 100) is None

    def test_non_numeric_returns_none(self):
        assert app_module.to_float("abc", 0, 100) is None

    def test_empty_returns_none(self):
        assert app_module.to_float("", 0, 100) is None

    def test_boundary_values_accepted(self):
        assert app_module.to_float("0", 0, 100) == 0.0
        assert app_module.to_float("100", 0, 100) == 100.0


class TestToInt:
    def test_valid_value(self):
        assert app_module.to_int("22", 0, 50) == 22

    def test_float_string_rejected(self):
        assert app_module.to_int("22.5", 0, 50) is None

    def test_out_of_range_returns_none(self):
        assert app_module.to_int("99", 0, 50) is None

    def test_non_numeric_returns_none(self):
        assert app_module.to_int("abc", 0, 50) is None


class TestValidEmail:
    def test_valid_email(self):
        assert app_module.valid_email("rahul@student.com")

    def test_missing_at(self):
        assert not app_module.valid_email("rahul.student.com")

    no_tld_cases = ["x@y", "x@y.", "x@.com"]

    def test_invalid_formats(self):
        for e in self.no_tld_cases:
            assert not app_module.valid_email(e), e
