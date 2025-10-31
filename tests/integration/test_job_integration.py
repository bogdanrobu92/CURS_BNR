"""
Integration tests for the main job function.
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path to import main module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import collect_exchange_rates


class TestJobIntegration:
    """Test collect_exchange_rates function integration."""
    
    @patch('main.BackupRateProvider')
    @patch('main.DatabaseManager')
    def test_collect_exchange_rates_success(self, mock_db_manager, mock_rate_provider):
        """Test successful rate collection."""
        # Setup mocks
        mock_provider_instance = mock_rate_provider.return_value
        mock_provider_instance.get_rates_with_fallback.return_value = {
            'BNR': {'EUR': 4.95, 'USD': 4.55, 'GBP': 5.75}
        }
        mock_provider_instance.get_best_rates.return_value = {
            'EUR': 4.95, 'USD': 4.55, 'GBP': 5.75
        }
        
        mock_db_instance = mock_db_manager.return_value
        mock_db_instance.save_exchange_rates.return_value = [1, 2, 3]
        
        # Execute collection
        result = collect_exchange_rates()
        
        # Verify results
        assert isinstance(result, dict)
        assert len(result) == 3
        assert 'EUR' in result
        assert 'USD' in result
        assert 'GBP' in result
    
    @patch('main.BackupRateProvider')
    @patch('main.DatabaseManager')
    def test_collect_exchange_rates_partial_success(self, mock_db_manager, mock_rate_provider):
        """Test collection with partial rate retrieval."""
        # Setup mocks - only EUR and USD succeed
        mock_provider_instance = mock_rate_provider.return_value
        mock_provider_instance.get_rates_with_fallback.return_value = {
            'BNR': {'EUR': 4.95, 'USD': 4.55}
        }
        mock_provider_instance.get_best_rates.return_value = {
            'EUR': 4.95, 'USD': 4.55
        }
        
        mock_db_instance = mock_db_manager.return_value
        mock_db_instance.save_exchange_rates.return_value = [1, 2]
        
        # Execute collection
        result = collect_exchange_rates()
        
        # Verify results
        assert isinstance(result, dict)
        assert len(result) == 2
        assert 'EUR' in result
        assert 'USD' in result
    
    @patch('main.BackupRateProvider')
    @patch('main.DatabaseManager')
    def test_collect_exchange_rates_failure_no_rates(self, mock_db_manager, mock_rate_provider):
        """Test collection when no rates are retrieved."""
        # Setup mocks - all rates fail
        mock_provider_instance = mock_rate_provider.return_value
        mock_provider_instance.get_rates_with_fallback.return_value = {}
        mock_provider_instance.get_best_rates.return_value = {}
        
        mock_db_instance = mock_db_manager.return_value
        
        # Execute collection
        result = collect_exchange_rates()
        
        # Verify results
        assert isinstance(result, dict)
        assert len(result) == 0
    
    @patch('main.BackupRateProvider')
    @patch('main.DatabaseManager')
    @patch('main.MetricsCollector')
    @patch('main.HealthChecker')
    @patch('main.fetch_rates_from_bnr_api')
    def test_collect_exchange_rates_exception_handling(self, mock_fetch_rates, mock_health_checker, mock_metrics_collector, mock_db_manager, mock_rate_provider):
        """Test collection with unexpected exception."""
        # Setup mocks to raise exception
        mock_rate_provider.side_effect = Exception("Unexpected error")
        mock_db_manager.side_effect = Exception("Unexpected error")
        mock_fetch_rates.return_value = ({}, 3)  # No rates, 3 errors
        
        mock_metrics_instance = mock_metrics_collector.return_value
        mock_metrics_instance.collect_application_metrics.return_value = {}
        mock_metrics_instance.save_metrics.return_value = None
        
        # Execute collection
        result = collect_exchange_rates()
        
        # Verify results - should return empty dict on error
        assert isinstance(result, dict)
        assert len(result) == 0
