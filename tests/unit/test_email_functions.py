"""
Unit tests for email functionality.
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path to import main module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import send_email


class TestSendEmail:
    """Test email sending functionality."""
    
    def test_send_email_success(self, mock_smtp_server, sample_email_body):
        """Test successful email sending."""
        result = send_email("Test Subject", sample_email_body, "test@example.com")
        
        assert result is True
        mock_smtp_server.login.assert_called_once()
        mock_smtp_server.send_message.assert_called_once()
    
    def test_send_email_invalid_recipient(self, sample_email_body):
        """Test email sending with invalid recipient."""
        result = send_email("Test Subject", sample_email_body, "invalid-email")
        
        assert result is False
    
    def test_send_email_missing_credentials(self, sample_email_body):
        """Test email sending with missing credentials."""
        with patch.dict(os.environ, {}, clear=True):
            result = send_email("Test Subject", sample_email_body, "test@example.com")
            
            assert result is False
    
    def test_send_email_invalid_sender(self, sample_email_body):
        """Test email sending with invalid sender email."""
        with patch.dict(os.environ, {'EMAIL_SENDER': 'invalid-email', 'EMAIL_PASS': 'pass'}):
            result = send_email("Test Subject", sample_email_body, "test@example.com")
            
            assert result is False
    
    def test_send_email_empty_subject(self, sample_email_body):
        """Test email sending with empty subject."""
        result = send_email("", sample_email_body, "test@example.com")
        
        assert result is False
    
    def test_send_email_empty_body(self):
        """Test email sending with empty body."""
        result = send_email("Test Subject", "", "test@example.com")
        
        assert result is False
    
    def test_send_email_smtp_authentication_error(self, sample_email_body):
        """Test email sending with SMTP authentication error."""
        with patch('smtplib.SMTP_SSL') as mock_smtp:
            mock_server = Mock()
            mock_server.login.side_effect = Exception("Authentication failed")
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            result = send_email("Test Subject", sample_email_body, "test@example.com")
            
            assert result is False
    
    def test_send_email_smtp_error(self, sample_email_body):
        """Test email sending with SMTP error."""
        with patch('smtplib.SMTP_SSL') as mock_smtp:
            mock_server = Mock()
            mock_server.send_message.side_effect = Exception("SMTP error")
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            result = send_email("Test Subject", sample_email_body, "test@example.com")
            
            assert result is False
    
    def test_send_email_subject_length_limit(self, sample_email_body):
        """Test email sending with subject length limit."""
        long_subject = "A" * 150  # Longer than 100 character limit
        result = send_email(long_subject, sample_email_body, "test@example.com")
        
        assert result is True
        # Verify subject was truncated
        call_args = mock_smtp_server.send_message.call_args[0][0]
        assert len(call_args['Subject']) <= 100
    
    def test_send_email_message_format(self, sample_email_body):
        """Test email message format."""
        send_email("Test Subject", sample_email_body, "test@example.com")
        
        # Verify message was created correctly
        call_args = mock_smtp_server.send_message.call_args[0][0]
        assert call_args['Subject'] == "Test Subject"
        assert call_args['From'] == "test@example.com"
        assert call_args['To'] == "test@example.com"
        assert 'Date' in call_args
