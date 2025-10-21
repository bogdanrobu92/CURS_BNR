"""
Unit tests for API-related functions.
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path to import main module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import get_bnr_api_rate, create_secure_session


class TestSecureSession:
    """Test secure session creation."""
    
    def test_create_secure_session(self):
        """Test that secure session is created with proper configuration."""
        session = create_secure_session()
        
        assert session is not None
        assert 'User-Agent' in session.headers
        assert 'Accept' in session.headers
        assert 'Accept-Encoding' in session.headers
        
        # Check retry configuration
        adapter = session.get_adapter('https://www.bnr.ro')
        assert adapter.max_retries.total == 3
        assert adapter.max_retries.backoff_factor == 0.3


class TestBNRAPIRate:
    """Test BNR API rate fetching functionality."""
    
    @patch('main.create_secure_session')
    def test_get_bnr_api_rate_success(self, mock_create_session, mock_bnr_xml_response):
        """Test successful API rate retrieval."""
        # Setup mock session
        mock_session = Mock()
        mock_response = Mock()
        mock_response.content = mock_bnr_xml_response.encode('utf-8')
        mock_response.raise_for_status.return_value = None
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session
        
        # Test successful rate retrieval
        rate = get_bnr_api_rate('EUR')
        
        assert rate == '4.9500'
        mock_session.get.assert_called_once()
        mock_session.close.assert_called_once()
    
    @patch('main.create_secure_session')
    def test_get_bnr_api_rate_currency_not_found(self, mock_create_session, mock_bnr_xml_response_missing_currency):
        """Test API rate retrieval when currency is not found."""
        # Setup mock session
        mock_session = Mock()
        mock_response = Mock()
        mock_response.content = mock_bnr_xml_response_missing_currency.encode('utf-8')
        mock_response.raise_for_status.return_value = None
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session
        
        # Test currency not found
        rate = get_bnr_api_rate('USD')
        
        assert rate is None
        mock_session.close.assert_called_once()
    
    @patch('main.create_secure_session')
    def test_get_bnr_api_rate_invalid_currency(self, mock_create_session):
        """Test API rate retrieval with invalid currency."""
        # Test invalid currency
        rate = get_bnr_api_rate('INVALID')
        
        assert rate is None
        mock_create_session.assert_not_called()
    
    @patch('main.create_secure_session')
    def test_get_bnr_api_rate_network_error(self, mock_create_session):
        """Test API rate retrieval with network error."""
        # Setup mock session to raise exception
        mock_session = Mock()
        mock_session.get.side_effect = Exception("Network error")
        mock_create_session.return_value = mock_session
        
        # Test network error
        rate = get_bnr_api_rate('EUR')
        
        assert rate is None
        mock_session.close.assert_called_once()
    
    @patch('main.create_secure_session')
    def test_get_bnr_api_rate_invalid_xml(self, mock_create_session, mock_bnr_xml_response_invalid):
        """Test API rate retrieval with invalid XML response."""
        # Setup mock session
        mock_session = Mock()
        mock_response = Mock()
        mock_response.content = mock_bnr_xml_response_invalid.encode('utf-8')
        mock_response.raise_for_status.return_value = None
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session
        
        # Test invalid XML
        rate = get_bnr_api_rate('EUR')
        
        assert rate is None
        mock_session.close.assert_called_once()
    
    @patch('main.create_secure_session')
    def test_get_bnr_api_rate_http_error(self, mock_create_session):
        """Test API rate retrieval with HTTP error."""
        # Setup mock session
        mock_session = Mock()
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 500")
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session
        
        # Test HTTP error
        rate = get_bnr_api_rate('EUR')
        
        assert rate is None
        mock_session.close.assert_called_once()
