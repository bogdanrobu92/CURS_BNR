"""
Integration tests for database operations.
Tests database operations including bulk inserts, transactions, and error handling.
"""
import pytest
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path

from database.models import DatabaseManager, ExchangeRate, SystemMetrics, RateAlert


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    db_manager = DatabaseManager(db_path)
    yield db_manager, db_path
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


class TestDatabaseOperations:
    """Integration tests for database operations."""
    
    def test_save_exchange_rate(self, temp_db):
        """Test saving a single exchange rate."""
        db_manager, db_path = temp_db
        
        rate = ExchangeRate(
            id=None,
            currency='EUR',
            rate=4.9500,
            source='BNR',
            timestamp=datetime.now(),
            multiplier=1,
            is_valid=True
        )
        
        rate_id = db_manager.save_exchange_rate(rate)
        assert rate_id > 0
        
        # Verify it was saved
        rates = db_manager.get_latest_rates('EUR')
        assert len(rates) > 0
        assert rates[0].currency == 'EUR'
        assert rates[0].rate == 4.9500
    
    def test_save_exchange_rates_bulk(self, temp_db):
        """Test bulk insert of exchange rates."""
        db_manager, db_path = temp_db
        
        rates = [
            ExchangeRate(
                id=None,
                currency='EUR',
                rate=4.9500,
                source='BNR',
                timestamp=datetime.now(),
                multiplier=1,
                is_valid=True
            ),
            ExchangeRate(
                id=None,
                currency='USD',
                rate=4.5500,
                source='BNR',
                timestamp=datetime.now(),
                multiplier=1,
                is_valid=True
            ),
            ExchangeRate(
                id=None,
                currency='GBP',
                rate=5.7500,
                source='BNR',
                timestamp=datetime.now(),
                multiplier=1,
                is_valid=True
            )
        ]
        
        ids = db_manager.save_exchange_rates(rates)
        assert len(ids) == 3
        assert all(id > 0 for id in ids)
        assert ids == sorted(ids)  # Should be sequential
        
        # Verify all were saved
        latest_rates = db_manager.get_latest_rates()
        assert len(latest_rates) >= 3
        
        currencies = {rate.currency for rate in latest_rates}
        assert 'EUR' in currencies
        assert 'USD' in currencies
        assert 'GBP' in currencies
    
    def test_save_exchange_rates_empty_list(self, temp_db):
        """Test bulk insert with empty list."""
        db_manager, db_path = temp_db
        
        ids = db_manager.save_exchange_rates([])
        assert ids == []
    
    def test_transaction_rollback_on_error(self, temp_db):
        """Test that transactions rollback on error."""
        db_manager, db_path = temp_db
        
        # Save a valid rate first
        valid_rate = ExchangeRate(
            id=None,
            currency='EUR',
            rate=4.9500,
            source='BNR',
            timestamp=datetime.now(),
            multiplier=1,
            is_valid=True
        )
        valid_id = db_manager.save_exchange_rate(valid_rate)
        
        # Try to save invalid rates (should fail and rollback)
        invalid_rates = [
            ExchangeRate(
                id=None,
                currency='EUR',
                rate=4.9500,
                source='BNR',
                timestamp=datetime.now(),
                multiplier=1,
                is_valid=True
            ),
            ExchangeRate(
                id=None,
                currency=None,  # Invalid - should cause error
                rate=4.5500,
                source='BNR',
                timestamp=datetime.now(),
                multiplier=1,
                is_valid=True
            )
        ]
        
        # This should raise an exception
        with pytest.raises(Exception):
            db_manager.save_exchange_rates(invalid_rates)
        
        # Verify the valid rate is still there (rollback worked)
        rates = db_manager.get_latest_rates('EUR')
        assert len(rates) == 1
        assert rates[0].id == valid_id
    
    def test_get_rates_by_currency(self, temp_db):
        """Test getting rates by currency."""
        db_manager, db_path = temp_db
        
        # Save multiple rates for EUR
        for i in range(5):
            rate = ExchangeRate(
                id=None,
                currency='EUR',
                rate=4.9500 + i * 0.01,
                source='BNR',
                timestamp=datetime.now(),
                multiplier=1,
                is_valid=True
            )
            db_manager.save_exchange_rate(rate)
        
        rates = db_manager.get_rates_by_currency('EUR')
        assert len(rates) == 5
        assert all(rate.currency == 'EUR' for rate in rates)
    
    def test_get_rates_by_date_range(self, temp_db):
        """Test getting rates by date range."""
        db_manager, db_path = temp_db
        
        base_date = datetime.now()
        
        # Save rates at different times
        for i in range(5):
            rate = ExchangeRate(
                id=None,
                currency='EUR',
                rate=4.9500,
                source='BNR',
                timestamp=base_date.replace(day=base_date.day - i),
                multiplier=1,
                is_valid=True
            )
            db_manager.save_exchange_rate(rate)
        
        start_date = base_date.replace(day=base_date.day - 3)
        end_date = base_date
        
        rates = db_manager.get_rates_by_date_range(start_date, end_date, 'EUR')
        assert len(rates) >= 3
        assert all(start_date <= rate.timestamp <= end_date for rate in rates)
    
    def test_save_system_metrics(self, temp_db):
        """Test saving system metrics."""
        db_manager, db_path = temp_db
        
        metrics = SystemMetrics(
            id=None,
            timestamp=datetime.now(),
            job_execution_time=10.5,
            api_response_time=2.3,
            email_send_time=1.0,
            rates_retrieved=3,
            rates_failed=0,
            job_success=True,
            error_count=0,
            memory_usage_mb=50.5,
            cpu_percent=25.0
        )
        
        metrics_id = db_manager.save_system_metrics(metrics)
        assert metrics_id > 0
        
        # Verify it was saved
        saved_metrics = db_manager.get_system_metrics(days=1)
        assert len(saved_metrics) > 0
        assert saved_metrics[0].job_execution_time == 10.5
    
    def test_save_rate_alert(self, temp_db):
        """Test saving rate alerts."""
        db_manager, db_path = temp_db
        
        alert = RateAlert(
            id=None,
            currency='EUR',
            start_date=datetime.now(),
            end_date=datetime.now(),
            start_rate=4.9000,
            end_rate=5.0000,
            change_percent=2.04,
            duration_days=1,
            alert_type='positive',
            severity='medium',
            timestamp=datetime.now()
        )
        
        alert_id = db_manager.save_rate_alert(alert)
        assert alert_id > 0
        
        # Verify it was saved
        alerts = db_manager.get_rate_alerts('EUR')
        assert len(alerts) > 0
        assert alerts[0].currency == 'EUR'
        assert alerts[0].change_percent == 2.04
    
    def test_cleanup_old_data(self, temp_db):
        """Test cleaning up old data."""
        db_manager, db_path = temp_db
        
        # Save some old data
        old_date = datetime.now() - timedelta(days=100)
        for i in range(3):
            rate = ExchangeRate(
                id=None,
                currency='EUR',
                rate=4.9500,
                source='BNR',
                timestamp=old_date,
                multiplier=1,
                is_valid=True
            )
            db_manager.save_exchange_rate(rate)
        
        # Save some recent data
        recent_date = datetime.now()
        for i in range(2):
            rate = ExchangeRate(
                id=None,
                currency='USD',
                rate=4.5500,
                source='BNR',
                timestamp=recent_date,
                multiplier=1,
                is_valid=True
            )
            db_manager.save_exchange_rate(rate)
        
        # Cleanup data older than 90 days
        deleted_count = db_manager.cleanup_old_data(days=90)
        assert deleted_count >= 3
        
        # Verify old data is gone
        rates = db_manager.get_rates_by_currency('EUR')
        assert len(rates) == 0
        
        # Verify recent data is still there
        rates = db_manager.get_rates_by_currency('USD')
        assert len(rates) == 2
    
    def test_connection_context_manager(self, temp_db):
        """Test connection context manager."""
        db_manager, db_path = temp_db
        
        # Test successful operation
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
        
        # Test rollback on error
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO exchange_rates (currency, rate, source, timestamp) VALUES (?, ?, ?, ?)", 
                             ('EUR', 4.95, 'BNR', datetime.now()))
                # Force an error
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Verify rollback worked (no data saved)
        rates = db_manager.get_latest_rates('EUR')
        assert len(rates) == 0

