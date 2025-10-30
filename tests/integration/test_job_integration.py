"""
Integration tests for the main job function.
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path to import main module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import job


class TestJobIntegration:
    """Test job function integration."""
    
    @patch('main.send_email')
    @patch('main.get_bnr_api_rate')
    def test_job_success_all_rates(self, mock_get_rate, mock_send_email, sample_rates_data):
        """Test successful job execution with all rates retrieved."""
        # Setup mocks
        mock_get_rate.side_effect = lambda currency: sample_rates_data.get(currency)
        mock_send_email.return_value = True
        
        # Execute job
        result = job()
        
        # Verify results
        assert result is True
        assert mock_get_rate.call_count == 3  # EUR, USD, GBP
        mock_send_email.assert_called_once()
        
        # Verify email content
        call_args = mock_send_email.call_args
        subject = call_args[0][0]
        body = call_args[0][1]
        
        assert "Curs BNR" in subject
        assert "EUR: 4.9500" in body
        assert "USD: 4.5500" in body
        assert "GBP: 5.7500" in body
    
    @patch('main.send_email')
    @patch('main.get_bnr_api_rate')
    def test_job_success_partial_rates(self, mock_get_rate, mock_send_email):
        """Test job execution with partial rate retrieval."""
        # Setup mocks - only EUR and USD succeed
        def mock_rate_side_effect(currency):
            rates = {'EUR': 4.9500, 'USD': 4.5500, 'GBP': None}
            return rates.get(currency)
        
        mock_get_rate.side_effect = mock_rate_side_effect
        mock_send_email.return_value = True
        
        # Execute job
        result = job()
        
        # Verify results
        assert result is True
        assert mock_get_rate.call_count == 3
        mock_send_email.assert_called_once()
        
        # Verify email content includes unavailable rate
        call_args = mock_send_email.call_args
        body = call_args[0][1]
        
        assert "EUR: 4.9500" in body
        assert "USD: 4.5500" in body
        assert "GBP: Curs indisponibil" in body
    
    @patch('main.send_email')
    @patch('main.get_bnr_api_rate')
    def test_job_failure_no_rates(self, mock_get_rate, mock_send_email):
        """Test job execution when no rates are retrieved."""
        # Setup mocks - all rates fail
        mock_get_rate.return_value = None
        mock_send_email.return_value = True
        
        # Execute job
        result = job()
        
        # Verify results
        assert result is True  # Job still succeeds, just with no rates
        assert mock_get_rate.call_count == 3
        mock_send_email.assert_called_once()
        
        # Verify email content shows all rates unavailable
        call_args = mock_send_email.call_args
        body = call_args[0][1]
        
        assert "EUR: Curs indisponibil" in body
        assert "USD: Curs indisponibil" in body
        assert "GBP: Curs indisponibil" in body
    
    @patch('main.send_email')
    @patch('main.get_bnr_api_rate')
    def test_job_failure_email_send_fails(self, mock_get_rate, mock_send_email, sample_rates_data):
        """Test job execution when email sending fails."""
        # Setup mocks
        mock_get_rate.side_effect = lambda currency: sample_rates_data.get(currency)
        mock_send_email.return_value = False
        
        # Execute job
        result = job()
        
        # Verify results
        assert result is False
        mock_send_email.assert_called_once()
    
    def test_job_failure_invalid_recipient_email(self):
        """Test job execution with invalid recipient email."""
        with patch.dict(os.environ, {'EMAIL_RECIPIENT': 'invalid-email'}):
            result = job()
            
            assert result is False
    
    def test_job_failure_missing_recipient_email(self):
        """Test job execution with missing recipient email."""
        with patch.dict(os.environ, {}, clear=True):
            result = job()
            
            assert result is False
    
    @patch('main.send_email')
    @patch('main.get_bnr_api_rate')
    def test_job_exception_handling(self, mock_get_rate, mock_send_email):
        """Test job execution with unexpected exception."""
        # Setup mocks to raise exception
        mock_get_rate.side_effect = Exception("Unexpected error")
        mock_send_email.return_value = True
        
        # Execute job
        result = job()
        
        # Verify results
        assert result is False
