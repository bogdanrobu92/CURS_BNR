"""
Pytest configuration and shared fixtures for BNR Exchange Rate Monitor tests.
"""
import pytest
import os
import tempfile
from unittest.mock import Mock, patch
from datetime import datetime


@pytest.fixture
def mock_bnr_xml_response():
    """Mock BNR XML response for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <DataSet xmlns="http://www.bnr.ro/xsd">
        <Body>
            <Cube date="2024-01-15">
                <Rate currency="EUR" multiplier="1">4.9500</Rate>
                <Rate currency="USD" multiplier="1">4.5500</Rate>
                <Rate currency="GBP" multiplier="1">5.7500</Rate>
            </Cube>
        </Body>
    </DataSet>"""


@pytest.fixture
def mock_bnr_xml_response_missing_currency():
    """Mock BNR XML response with missing currency for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <DataSet xmlns="http://www.bnr.ro/xsd">
        <Body>
            <Cube date="2024-01-15">
                <Rate currency="EUR" multiplier="1">4.9500</Rate>
            </Cube>
        </Body>
    </DataSet>"""


@pytest.fixture
def mock_bnr_xml_response_invalid():
    """Mock invalid BNR XML response for testing."""
    return """Invalid XML content"""


@pytest.fixture
def mock_environment_variables():
    """Mock environment variables for testing."""
    return {
        'EMAIL_SENDER': 'test@example.com',
        'EMAIL_PASS': 'test_password',
        'EMAIL_RECIPIENT': 'recipient@example.com'
    }


@pytest.fixture
def mock_smtp_server():
    """Mock SMTP server for email testing."""
    with patch('smtplib.SMTP_SSL') as mock_smtp:
        mock_server = Mock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        yield mock_server


@pytest.fixture
def temp_log_file():
    """Create a temporary log file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_rates_data():
    """Sample exchange rates data for testing."""
    return {
        'EUR': 4.9500,
        'USD': 4.5500,
        'GBP': 5.7500
    }


@pytest.fixture
def sample_email_body():
    """Sample email body for testing."""
    return """Curs BNR - 15.01.2024

EUR: 4.9500
USD: 4.5500
GBP: 5.7500"""


@pytest.fixture(autouse=True)
def setup_test_environment(mock_environment_variables):
    """Set up test environment variables for each test."""
    with patch.dict(os.environ, mock_environment_variables):
        yield
