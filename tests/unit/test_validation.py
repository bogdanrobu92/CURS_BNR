"""
Unit tests for validation functions.
"""
import pytest
import sys
import os

pytestmark = pytest.mark.unit

# Add parent directory to path to import main module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import validate_currency, validate_rate


class TestCurrencyValidation:
    """Test currency validation functionality."""
    
    def test_validate_currency_valid_codes(self):
        """Test validation of valid currency codes."""
        valid_currencies = ['EUR', 'USD', 'GBP', 'eur', 'usd', 'gbp']
        for currency in valid_currencies:
            assert validate_currency(currency) is True, f"Should validate {currency}"
    
    def test_validate_currency_invalid_codes(self):
        """Test validation of invalid currency codes."""
        invalid_currencies = ['RON', 'CAD', 'JPY', 'ABC', 'EU', 'USDD', '']
        for currency in invalid_currencies:
            assert validate_currency(currency) is False, f"Should reject {currency}"
    
    def test_validate_currency_non_string(self):
        """Test validation with non-string inputs."""
        non_string_inputs = [123, None, [], {}, True]
        for input_val in non_string_inputs:
            assert validate_currency(input_val) is False, f"Should reject {type(input_val)}"
    
    def test_validate_currency_case_insensitive(self):
        """Test that validation is case insensitive."""
        assert validate_currency('eur') is True
        assert validate_currency('EUR') is True
        assert validate_currency('Eur') is True


class TestRateValidation:
    """Test rate validation functionality."""
    
    def test_validate_rate_valid_rates(self):
        """Test validation of valid exchange rates."""
        valid_rates = [4.95, 4.55, 5.75, 0.1, 99.99, 10.0]
        for rate in valid_rates:
            assert validate_rate(rate) is True, f"Should validate {rate}"
    
    def test_validate_rate_invalid_rates(self):
        """Test validation of invalid exchange rates."""
        invalid_rates = [0, -1, 101, 1000, -0.01]
        for rate in invalid_rates:
            assert validate_rate(rate) is False, f"Should reject {rate}"
    
    def test_validate_rate_edge_cases(self):
        """Test rate validation edge cases."""
        assert validate_rate(0.1) is True  # Minimum valid
        assert validate_rate(100.0) is False  # Maximum invalid (exclusive)
        assert validate_rate(99.99) is True  # Just below maximum
        assert validate_rate(0.11) is True  # Just above minimum
