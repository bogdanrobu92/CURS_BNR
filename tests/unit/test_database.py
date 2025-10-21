"""
Unit tests for database functionality.
"""
import pytest
import sys
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path to import main module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import DatabaseManager, ExchangeRate, SystemMetrics, RateTrend


class TestDatabaseManager:
    """Test database management functionality."""
    
    def test_database_initialization(self):
        """Test database initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            db_manager = DatabaseManager(db_path)
            
            # Check if database file was created
            assert Path(db_path).exists()
            
            # Check if tables were created
            import sqlite3
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                assert 'exchange_rates' in tables
                assert 'system_metrics' in tables
                assert 'rate_trends' in tables
    
    def test_save_exchange_rate(self):
        """Test saving exchange rate."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            db_manager = DatabaseManager(db_path)
            
            rate = ExchangeRate(
                id=None,
                currency="EUR",
                rate=4.9500,
                source="BNR",
                timestamp=datetime.now(),
                multiplier=1,
                is_valid=True
            )
            
            rate_id = db_manager.save_exchange_rate(rate)
            assert rate_id is not None
            assert rate_id > 0
    
    def test_save_multiple_exchange_rates(self):
        """Test saving multiple exchange rates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            db_manager = DatabaseManager(db_path)
            
            rates = [
                ExchangeRate(None, "EUR", 4.9500, "BNR", datetime.now(), 1, True),
                ExchangeRate(None, "USD", 4.5500, "BNR", datetime.now(), 1, True),
                ExchangeRate(None, "GBP", 5.7500, "BNR", datetime.now(), 1, True)
            ]
            
            ids = db_manager.save_exchange_rates(rates)
            assert len(ids) == 3
            assert all(id > 0 for id in ids)
    
    def test_get_latest_rates(self):
        """Test getting latest rates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            db_manager = DatabaseManager(db_path)
            
            # Save some test rates
            rates = [
                ExchangeRate(None, "EUR", 4.9500, "BNR", datetime.now(), 1, True),
                ExchangeRate(None, "USD", 4.5500, "BNR", datetime.now(), 1, True),
                ExchangeRate(None, "EUR", 4.9600, "ECB", datetime.now(), 1, True)
            ]
            
            for rate in rates:
                db_manager.save_exchange_rate(rate)
            
            # Get latest rates
            latest_rates = db_manager.get_latest_rates()
            assert len(latest_rates) >= 3
            
            # Check that we get the latest rate for each currency
            eur_rates = [r for r in latest_rates if r.currency == "EUR"]
            assert len(eur_rates) >= 1
    
    def test_get_rates_by_date_range(self):
        """Test getting rates by date range."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            db_manager = DatabaseManager(db_path)
            
            # Save rates with different timestamps
            now = datetime.now()
            yesterday = now - timedelta(days=1)
            last_week = now - timedelta(days=7)
            
            rates = [
                ExchangeRate(None, "EUR", 4.9500, "BNR", now, 1, True),
                ExchangeRate(None, "EUR", 4.9400, "BNR", yesterday, 1, True),
                ExchangeRate(None, "EUR", 4.9300, "BNR", last_week, 1, True)
            ]
            
            for rate in rates:
                db_manager.save_exchange_rate(rate)
            
            # Get rates from last 2 days
            recent_rates = db_manager.get_rates_by_date_range(
                now - timedelta(days=2), now
            )
            
            assert len(recent_rates) >= 2
    
    def test_get_rate_trends(self):
        """Test getting rate trends."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            db_manager = DatabaseManager(db_path)
            
            # Save rates with different timestamps for trend calculation
            now = datetime.now()
            rates = [
                ExchangeRate(None, "EUR", 4.9000, "BNR", now - timedelta(days=3), 1, True),
                ExchangeRate(None, "EUR", 4.9200, "BNR", now - timedelta(days=2), 1, True),
                ExchangeRate(None, "EUR", 4.9500, "BNR", now - timedelta(days=1), 1, True),
                ExchangeRate(None, "EUR", 4.9600, "BNR", now, 1, True)
            ]
            
            for rate in rates:
                db_manager.save_exchange_rate(rate)
            
            # Get trends
            trends = db_manager.get_rate_trends("EUR", 7)
            assert len(trends) >= 1
            
            # Check trend data
            if trends:
                trend = trends[0]
                assert trend.currency == "EUR"
                assert trend.current_rate > 0
                assert trend.previous_rate > 0
                assert trend.change_absolute != 0
                assert trend.change_percentage != 0
                assert trend.trend_direction in ['up', 'down', 'stable']
    
    def test_get_currency_statistics(self):
        """Test getting currency statistics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            db_manager = DatabaseManager(db_path)
            
            # Save test rates
            rates = [
                ExchangeRate(None, "EUR", 4.9000, "BNR", datetime.now(), 1, True),
                ExchangeRate(None, "EUR", 4.9200, "BNR", datetime.now(), 1, True),
                ExchangeRate(None, "EUR", 4.9500, "BNR", datetime.now(), 1, True),
                ExchangeRate(None, "EUR", 4.9600, "BNR", datetime.now(), 1, True)
            ]
            
            for rate in rates:
                db_manager.save_exchange_rate(rate)
            
            # Get statistics
            stats = db_manager.get_currency_statistics("EUR", 30)
            
            assert 'min_rate' in stats
            assert 'max_rate' in stats
            assert 'avg_rate' in stats
            assert 'total_rates' in stats
            assert stats['min_rate'] == 4.9000
            assert stats['max_rate'] == 4.9600
            assert stats['total_rates'] >= 4
    
    def test_save_system_metrics(self):
        """Test saving system metrics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            db_manager = DatabaseManager(db_path)
            
            metrics = SystemMetrics(
                id=None,
                timestamp=datetime.now(),
                job_execution_time=5.0,
                api_response_time=2.0,
                email_send_time=1.0,
                rates_retrieved=3,
                rates_failed=0,
                job_success=True,
                error_count=0,
                memory_usage_mb=100.0,
                cpu_percent=25.0
            )
            
            metrics_id = db_manager.save_system_metrics(metrics)
            assert metrics_id is not None
            assert metrics_id > 0
    
    def test_get_system_metrics(self):
        """Test getting system metrics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            db_manager = DatabaseManager(db_path)
            
            # Save test metrics
            metrics = SystemMetrics(
                id=None,
                timestamp=datetime.now(),
                job_execution_time=5.0,
                api_response_time=2.0,
                email_send_time=1.0,
                rates_retrieved=3,
                rates_failed=0,
                job_success=True,
                error_count=0,
                memory_usage_mb=100.0,
                cpu_percent=25.0
            )
            
            db_manager.save_system_metrics(metrics)
            
            # Get metrics
            retrieved_metrics = db_manager.get_system_metrics(7)
            assert len(retrieved_metrics) >= 1
            
            if retrieved_metrics:
                metric = retrieved_metrics[0]
                assert metric.job_execution_time == 5.0
                assert metric.rates_retrieved == 3
                assert metric.job_success is True
    
    def test_export_data(self):
        """Test data export functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            db_manager = DatabaseManager(db_path)
            
            # Save test data
            rate = ExchangeRate(None, "EUR", 4.9500, "BNR", datetime.now(), 1, True)
            db_manager.save_exchange_rate(rate)
            
            # Export JSON
            json_data = db_manager.export_data('json', 30)
            assert json_data is not None
            assert 'exchange_rates' in json_data
            
            # Export CSV
            csv_data = db_manager.export_data('csv', 30)
            assert csv_data is not None
            assert 'currency,rate,source,timestamp' in csv_data
    
    def test_cleanup_old_data(self):
        """Test cleanup of old data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            db_manager = DatabaseManager(db_path)
            
            # Save old data
            old_date = datetime.now() - timedelta(days=100)
            old_rate = ExchangeRate(None, "EUR", 4.9000, "BNR", old_date, 1, True)
            db_manager.save_exchange_rate(old_rate)
            
            # Save recent data
            recent_rate = ExchangeRate(None, "EUR", 4.9500, "BNR", datetime.now(), 1, True)
            db_manager.save_exchange_rate(recent_rate)
            
            # Cleanup old data
            deleted_count = db_manager.cleanup_old_data(90)
            assert deleted_count >= 1
            
            # Check that recent data is still there
            recent_rates = db_manager.get_latest_rates()
            assert len(recent_rates) >= 1
