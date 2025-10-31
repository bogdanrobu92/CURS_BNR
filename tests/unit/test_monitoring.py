"""
Unit tests for monitoring system.
"""
import pytest
import sys
import os
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path to import main module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitoring.metrics import MetricsCollector, SystemMetrics, ApplicationMetrics, BusinessMetrics
from monitoring.health_check import HealthChecker, HealthStatus


class TestSystemMetrics:
    """Test system metrics collection."""
    
    def test_system_metrics_creation(self):
        """Test SystemMetrics dataclass creation."""
        metrics = SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=50.0,
            memory_percent=75.0,
            memory_used_mb=1024.0,
            disk_usage_percent=60.0,
            disk_free_gb=100.0,
            load_average=1.5
        )
        
        assert metrics.cpu_percent == 50.0
        assert metrics.memory_percent == 75.0
        assert metrics.memory_used_mb == 1024.0
        assert metrics.disk_usage_percent == 60.0
        assert metrics.disk_free_gb == 100.0
        assert metrics.load_average == 1.5
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('os.getloadavg')
    def test_collect_system_metrics(self, mock_getloadavg, mock_disk, mock_memory, mock_cpu):
        """Test system metrics collection."""
        # Setup mocks
        mock_cpu.return_value = 25.0
        mock_memory.return_value = Mock(percent=60.0, used=512*1024*1024)
        mock_disk.return_value = Mock(used=100*1024*1024*1024, total=200*1024*1024*1024, free=100*1024*1024*1024)
        mock_getloadavg.return_value = (1.0, 1.5, 2.0)
        
        collector = MetricsCollector()
        metrics = collector.collect_system_metrics()
        
        assert metrics.cpu_percent == 25.0
        assert metrics.memory_percent == 60.0
        assert metrics.memory_used_mb == 512.0
        assert metrics.disk_usage_percent == 50.0
        assert metrics.disk_free_gb == 100.0
        assert metrics.load_average == 1.0


class TestApplicationMetrics:
    """Test application metrics collection."""
    
    def test_application_metrics_creation(self):
        """Test ApplicationMetrics dataclass creation."""
        metrics = ApplicationMetrics(
            timestamp=datetime.now(),
            job_execution_time=5.0,
            api_response_time=2.0,
            email_send_time=1.0,
            rates_retrieved=3,
            rates_failed=0,
            job_success=True,
            error_count=0
        )
        
        assert metrics.job_execution_time == 5.0
        assert metrics.api_response_time == 2.0
        assert metrics.email_send_time == 1.0
        assert metrics.rates_retrieved == 3
        assert metrics.rates_failed == 0
        assert metrics.job_success is True
        assert metrics.error_count == 0
    
    def test_collect_application_metrics(self):
        """Test application metrics collection."""
        collector = MetricsCollector()
        metrics = collector.collect_application_metrics(
            job_execution_time=5.0,
            api_response_time=2.0,
            email_send_time=1.0,
            rates_retrieved=3,
            rates_failed=0,
            job_success=True,
            error_count=0
        )
        
        assert metrics.job_execution_time == 5.0
        assert metrics.api_response_time == 2.0
        assert metrics.email_send_time == 1.0
        assert metrics.rates_retrieved == 3
        assert metrics.rates_failed == 0
        assert metrics.job_success is True
        assert metrics.error_count == 0


class TestBusinessMetrics:
    """Test business metrics collection."""
    
    def test_business_metrics_creation(self):
        """Test BusinessMetrics dataclass creation."""
        metrics = BusinessMetrics(
            timestamp=datetime.now(),
            eur_rate="4.9500",
            usd_rate="4.5500",
            gbp_rate="5.7500",
            total_rates_available=3,
            api_availability=100.0
        )
        
        assert metrics.eur_rate == "4.9500"
        assert metrics.usd_rate == "4.5500"
        assert metrics.gbp_rate == "5.7500"
        assert metrics.total_rates_available == 3
        assert metrics.api_availability == 100.0
    
    def test_collect_business_metrics(self):
        """Test business metrics collection."""
        collector = MetricsCollector()
        metrics = collector.collect_business_metrics(
            eur_rate="4.9500",
            usd_rate="4.5500",
            gbp_rate="5.7500",
            api_availability=100.0
        )
        
        assert metrics.eur_rate == "4.9500"
        assert metrics.usd_rate == "4.5500"
        assert metrics.gbp_rate == "5.7500"
        assert metrics.total_rates_available == 3
        assert metrics.api_availability == 100.0
    
    def test_collect_business_metrics_partial_rates(self):
        """Test business metrics collection with partial rates."""
        collector = MetricsCollector()
        metrics = collector.collect_business_metrics(
            eur_rate="4.9500",
            usd_rate=None,
            gbp_rate="5.7500",
            api_availability=66.67
        )
        
        assert metrics.eur_rate == "4.9500"
        assert metrics.usd_rate is None
        assert metrics.gbp_rate == "5.7500"
        assert metrics.total_rates_available == 2
        assert metrics.api_availability == 66.67


class TestMetricsCollector:
    """Test MetricsCollector functionality."""
    
    def test_metrics_collector_initialization(self):
        """Test MetricsCollector initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = MetricsCollector(temp_dir)
            
            assert collector.metrics_dir == Path(temp_dir)
            assert collector.metrics_dir.exists()
            # Files are created as Path objects but don't exist until data is written
            assert collector.system_metrics_file == Path(temp_dir) / "system_metrics.jsonl"
            assert collector.app_metrics_file == Path(temp_dir) / "app_metrics.jsonl"
            assert collector.business_metrics_file == Path(temp_dir) / "business_metrics.jsonl"
    
    def test_save_metrics(self):
        """Test saving metrics to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = MetricsCollector(temp_dir)
            
            metrics = SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=50.0,
                memory_percent=75.0,
                memory_used_mb=1024.0,
                disk_usage_percent=60.0,
                disk_free_gb=100.0
            )
            
            collector.save_metrics(metrics, collector.system_metrics_file)
            
            # Verify file was created and contains data
            assert collector.system_metrics_file.exists()
            with open(collector.system_metrics_file, 'r') as f:
                data = json.loads(f.read().strip())
                assert data['cpu_percent'] == 50.0
                assert data['memory_percent'] == 75.0
    
    def test_load_metrics(self):
        """Test loading metrics from file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = MetricsCollector(temp_dir)
            
            # Create test data
            test_data = {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': 50.0,
                'memory_percent': 75.0,
                'memory_used_mb': 1024.0,
                'disk_usage_percent': 60.0,
                'disk_free_gb': 100.0
            }
            
            with open(collector.system_metrics_file, 'w') as f:
                f.write(json.dumps(test_data) + '\n')
            
            # Load metrics
            metrics = collector.load_metrics(collector.system_metrics_file, 24)
            
            assert len(metrics) == 1
            assert metrics[0]['cpu_percent'] == 50.0
            assert metrics[0]['memory_percent'] == 75.0
    
    def test_generate_system_report(self):
        """Test system report generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = MetricsCollector(temp_dir)
            
            # Create test data
            for i in range(5):
                metrics = SystemMetrics(
                    timestamp=datetime.now() - timedelta(hours=i),
                    cpu_percent=50.0 + i,
                    memory_percent=75.0 + i,
                    memory_used_mb=1024.0 + i * 100,
                    disk_usage_percent=60.0 + i,
                    disk_free_gb=100.0 - i
                )
                collector.save_metrics(metrics, collector.system_metrics_file)
            
            # Generate report
            report = collector.generate_system_report(24)
            
            assert 'period_hours' in report
            assert 'total_measurements' in report
            assert 'cpu' in report
            assert 'memory' in report
            assert 'disk' in report
            assert report['total_measurements'] == 5


class TestHealthChecker:
    """Test health checking functionality."""
    
    def test_health_status_creation(self):
        """Test HealthStatus dataclass creation."""
        status = HealthStatus(
            service="Test Service",
            status="healthy",
            message="All systems operational",
            timestamp=datetime.now(),
            response_time=1.5,
            error_count=0
        )
        
        assert status.service == "Test Service"
        assert status.status == "healthy"
        assert status.message == "All systems operational"
        assert status.response_time == 1.5
        assert status.error_count == 0
    
    @patch('requests.get')
    def test_check_bnr_api_health_success(self, mock_get):
        """Test BNR API health check with success."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        checker = HealthChecker()
        status = checker.check_bnr_api_health()
        
        assert status.service == "BNR API"
        assert status.status == "healthy"
        assert "API responding normally" in status.message
        assert status.response_time is not None
    
    @patch('requests.get')
    def test_check_bnr_api_health_timeout(self, mock_get):
        """Test BNR API health check with timeout."""
        mock_get.side_effect = Exception("Timeout")
        
        checker = HealthChecker()
        status = checker.check_bnr_api_health()
        
        assert status.service == "BNR API"
        assert status.status == "unhealthy"
        assert "Unexpected error" in status.message
    
    @patch('smtplib.SMTP_SSL')
    def test_check_email_service_health_success(self, mock_smtp):
        """Test email service health check with success."""
        # Setup mock SMTP
        mock_server = Mock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        with patch.dict(os.environ, {'EMAIL_SENDER': 'test@example.com', 'EMAIL_PASS': 'password'}):
            checker = HealthChecker()
            status = checker.check_email_service_health()
            
            assert status.service == "Email Service"
            assert status.status == "healthy"
            assert "SMTP connection successful" in status.message
    
    def test_check_email_service_health_missing_credentials(self):
        """Test email service health check with missing credentials."""
        with patch.dict(os.environ, {}, clear=True):
            checker = HealthChecker()
            status = checker.check_email_service_health()
            
            assert status.service == "Email Service"
            assert status.status == "unhealthy"
            assert "Email credentials not configured" in status.message
    
    def test_check_system_health_success(self):
        """Test system health check with success."""
        with patch.dict(os.environ, {'EMAIL_SENDER': 'test@example.com', 'EMAIL_PASS': 'password', 'EMAIL_RECIPIENT': 'recipient@example.com'}):
            checker = HealthChecker()
            status = checker.check_system_health()
            
            assert status.service == "System"
            assert status.status == "healthy"
            assert "System configuration valid" in status.message
    
    def test_check_system_health_missing_vars(self):
        """Test system health check with missing environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            checker = HealthChecker()
            status = checker.check_system_health()
            
            assert status.service == "System"
            assert status.status == "unhealthy"
            assert "Missing environment variables" in status.message
    
    def test_run_health_checks(self):
        """Test running all health checks."""
        with patch.dict(os.environ, {'EMAIL_SENDER': 'test@example.com', 'EMAIL_PASS': 'password', 'EMAIL_RECIPIENT': 'recipient@example.com'}):
            checker = HealthChecker()
            checks = checker.run_health_checks()
            
            assert len(checks) == 3
            assert any(check.service == "System" for check in checks)
            assert any(check.service == "BNR API" for check in checks)
            assert any(check.service == "Email Service" for check in checks)
    
    def test_get_health_summary(self):
        """Test health summary generation."""
        checker = HealthChecker()
        
        # Add some test health statuses
        checker.health_history = [
            HealthStatus("Service1", "healthy", "OK", datetime.now()),
            HealthStatus("Service2", "degraded", "Warning", datetime.now()),
            HealthStatus("Service3", "healthy", "OK", datetime.now())
        ]
        
        summary = checker.get_health_summary()
        
        assert 'status' in summary
        assert 'status_counts' in summary
        assert 'total_checks' in summary
        assert summary['total_checks'] == 3
        assert summary['status_counts']['healthy'] == 2
        assert summary['status_counts']['degraded'] == 1
    
    def test_check_for_alerts(self):
        """Test alert checking functionality."""
        checker = HealthChecker()
        checker.alert_threshold = 2
        
        # Add consecutive failures - need at least alert_threshold failures
        checker.health_history = [
            HealthStatus("Service1", "unhealthy", "Error", datetime.now()),
            HealthStatus("Service1", "unhealthy", "Error", datetime.now()),
            HealthStatus("Service1", "unhealthy", "Error", datetime.now())
        ]
        
        alerts = checker.check_for_alerts()
        
        # Should have alert since we have 3 consecutive failures >= threshold of 2
        assert len(alerts) >= 1
        assert any("Service1" in alert for alert in alerts)
