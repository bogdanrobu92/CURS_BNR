"""
Unit tests for validation functions.
"""
import pytest
import sys
import os

# Add parent directory to path to import main module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import validate_currency, validate_email


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


class TestEmailValidation:
    """Test email validation functionality."""
    
    def test_validate_email_valid_addresses(self):
        """Test validation of valid email addresses."""
        valid_emails = [
            'test@example.com',
            'user.name@domain.co.uk',
            'user+tag@example.org',
            'user123@test-domain.com',
            'a@b.co'
        ]
        for email in valid_emails:
            assert validate_email(email) is True, f"Should validate {email}"
    
    def test_validate_email_invalid_addresses(self):
        """Test validation of invalid email addresses."""
        invalid_emails = [
            'invalid-email',
            '@example.com',
            'user@',
            'user@.com',
            'user..name@example.com',
            'user@example..com',
            '',
            'user@example',
            'user name@example.com'
        ]
        for email in invalid_emails:
            assert validate_email(email) is False, f"Should reject {email}"
    
    def test_validate_email_edge_cases(self):
        """Test email validation edge cases."""
        assert validate_email(None) is False
        assert validate_email(123) is False
        assert validate_email([]) is False
        assert validate_email({}) is False
