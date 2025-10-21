#!/usr/bin/env python3
"""
Metrics collection module for BNR Exchange Rate Monitor.
Collects and reports system performance and operational metrics.
"""
import os
import sys
import time
import json
import logging
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class SystemMetrics:
    """System performance metrics."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    load_average: Optional[float] = None


@dataclass
class ApplicationMetrics:
    """Application-specific metrics."""
    timestamp: datetime
    job_execution_time: float
    api_response_time: float
    email_send_time: float
    rates_retrieved: int
    rates_failed: int
    job_success: bool
    error_count: int


@dataclass
class BusinessMetrics:
    """Business logic metrics."""
    timestamp: datetime
    eur_rate: Optional[str]
    usd_rate: Optional[str]
    gbp_rate: Optional[str]
    total_rates_available: int
    api_availability: float


class MetricsCollector:
    """Metrics collection and reporting system."""
    
    def __init__(self, metrics_dir: str = "metrics"):
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        # Initialize metrics files
        self.system_metrics_file = self.metrics_dir / "system_metrics.jsonl"
        self.app_metrics_file = self.metrics_dir / "app_metrics.jsonl"
        self.business_metrics_file = self.metrics_dir / "business_metrics.jsonl"
    
    def collect_system_metrics(self) -> SystemMetrics:
        """Collect system performance metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / (1024 * 1024 * 1024)
            
            # Load average (Unix-like systems)
            load_avg = None
            if hasattr(os, 'getloadavg'):
                load_avg = os.getloadavg()[0]
            
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                disk_usage_percent=disk_usage_percent,
                disk_free_gb=disk_free_gb,
                load_average=load_avg
            )
            
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                disk_usage_percent=0.0,
                disk_free_gb=0.0
            )
    
    def collect_application_metrics(self, 
                                  job_execution_time: float,
                                  api_response_time: float,
                                  email_send_time: float,
                                  rates_retrieved: int,
                                  rates_failed: int,
                                  job_success: bool,
                                  error_count: int) -> ApplicationMetrics:
        """Collect application-specific metrics."""
        return ApplicationMetrics(
            timestamp=datetime.now(),
            job_execution_time=job_execution_time,
            api_response_time=api_response_time,
            email_send_time=email_send_time,
            rates_retrieved=rates_retrieved,
            rates_failed=rates_failed,
            job_success=job_success,
            error_count=error_count
        )
    
    def collect_business_metrics(self,
                               eur_rate: Optional[str],
                               usd_rate: Optional[str],
                               gbp_rate: Optional[str],
                               api_availability: float) -> BusinessMetrics:
        """Collect business logic metrics."""
        rates = [eur_rate, usd_rate, gbp_rate]
        total_rates_available = sum(1 for rate in rates if rate is not None)
        
        return BusinessMetrics(
            timestamp=datetime.now(),
            eur_rate=eur_rate,
            usd_rate=usd_rate,
            gbp_rate=gbp_rate,
            total_rates_available=total_rates_available,
            api_availability=api_availability
        )
    
    def save_metrics(self, metrics: Any, filename: Path) -> None:
        """Save metrics to JSONL file."""
        try:
            # Convert to dict and add timestamp
            metrics_dict = asdict(metrics)
            metrics_dict['timestamp'] = metrics_dict['timestamp'].isoformat()
            
            # Append to file
            with open(filename, 'a') as f:
                f.write(json.dumps(metrics_dict) + '\n')
                
        except Exception as e:
            self.logger.error(f"Failed to save metrics to {filename}: {e}")
    
    def load_metrics(self, filename: Path, hours: int = 24) -> List[Dict]:
        """Load metrics from the last N hours."""
        try:
            if not filename.exists():
                return []
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            metrics = []
            
            with open(filename, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        # Convert timestamp back to datetime for comparison
                        timestamp = datetime.fromisoformat(data['timestamp'])
                        if timestamp >= cutoff_time:
                            metrics.append(data)
                    except (json.JSONDecodeError, KeyError):
                        continue
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to load metrics from {filename}: {e}")
            return []
    
    def generate_system_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate system performance report."""
        metrics = self.load_metrics(self.system_metrics_file, hours)
        
        if not metrics:
            return {"error": "No system metrics available"}
        
        # Calculate averages
        cpu_avg = sum(m['cpu_percent'] for m in metrics) / len(metrics)
        memory_avg = sum(m['memory_percent'] for m in metrics) / len(metrics)
        disk_avg = sum(m['disk_usage_percent'] for m in metrics) / len(metrics)
        
        # Find peaks
        cpu_peak = max(m['cpu_percent'] for m in metrics)
        memory_peak = max(m['memory_percent'] for m in metrics)
        
        return {
            "period_hours": hours,
            "total_measurements": len(metrics),
            "cpu": {
                "average_percent": round(cpu_avg, 2),
                "peak_percent": round(cpu_peak, 2)
            },
            "memory": {
                "average_percent": round(memory_avg, 2),
                "peak_percent": round(memory_peak, 2)
            },
            "disk": {
                "average_usage_percent": round(disk_avg, 2)
            }
        }
    
    def generate_application_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate application performance report."""
        metrics = self.load_metrics(self.app_metrics_file, hours)
        
        if not metrics:
            return {"error": "No application metrics available"}
        
        # Calculate averages
        job_time_avg = sum(m['job_execution_time'] for m in metrics) / len(metrics)
        api_time_avg = sum(m['api_response_time'] for m in metrics) / len(metrics)
        email_time_avg = sum(m['email_send_time'] for m in metrics) / len(metrics)
        
        # Calculate success rate
        successful_jobs = sum(1 for m in metrics if m['job_success'])
        success_rate = (successful_jobs / len(metrics)) * 100
        
        # Calculate error rate
        total_errors = sum(m['error_count'] for m in metrics)
        error_rate = (total_errors / len(metrics)) * 100
        
        return {
            "period_hours": hours,
            "total_jobs": len(metrics),
            "success_rate_percent": round(success_rate, 2),
            "error_rate_percent": round(error_rate, 2),
            "performance": {
                "average_job_time_seconds": round(job_time_avg, 2),
                "average_api_time_seconds": round(api_time_avg, 2),
                "average_email_time_seconds": round(email_time_avg, 2)
            }
        }
    
    def generate_business_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate business metrics report."""
        metrics = self.load_metrics(self.business_metrics_file, hours)
        
        if not metrics:
            return {"error": "No business metrics available"}
        
        # Calculate availability
        api_availability_avg = sum(m['api_availability'] for m in metrics) / len(metrics)
        
        # Calculate rate availability
        total_rates_available = sum(m['total_rates_available'] for m in metrics)
        max_possible_rates = len(metrics) * 3  # 3 currencies
        rate_availability = (total_rates_available / max_possible_rates) * 100
        
        # Get latest rates
        latest = metrics[-1]
        
        return {
            "period_hours": hours,
            "total_measurements": len(metrics),
            "api_availability_percent": round(api_availability_avg, 2),
            "rate_availability_percent": round(rate_availability, 2),
            "latest_rates": {
                "eur": latest.get('eur_rate'),
                "usd": latest.get('usd_rate'),
                "gbp": latest.get('gbp_rate')
            }
        }
    
    def generate_comprehensive_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive metrics report."""
        return {
            "report_timestamp": datetime.now().isoformat(),
            "period_hours": hours,
            "system": self.generate_system_report(hours),
            "application": self.generate_application_report(hours),
            "business": self.generate_business_report(hours)
        }
    
    def cleanup_old_metrics(self, days: int = 30) -> None:
        """Clean up metrics older than specified days."""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        for filename in [self.system_metrics_file, self.app_metrics_file, self.business_metrics_file]:
            if not filename.exists():
                continue
            
            try:
                # Read all lines
                with open(filename, 'r') as f:
                    lines = f.readlines()
                
                # Filter recent lines
                recent_lines = []
                for line in lines:
                    try:
                        data = json.loads(line.strip())
                        timestamp = datetime.fromisoformat(data['timestamp'])
                        if timestamp >= cutoff_time:
                            recent_lines.append(line)
                    except (json.JSONDecodeError, KeyError):
                        continue
                
                # Write back recent lines
                with open(filename, 'w') as f:
                    f.writelines(recent_lines)
                
                self.logger.info(f"Cleaned up old metrics from {filename}")
                
            except Exception as e:
                self.logger.error(f"Failed to cleanup {filename}: {e}")


def main():
    """Main metrics collection function."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    collector = MetricsCollector()
    
    # Collect current system metrics
    print("Collecting system metrics...")
    system_metrics = collector.collect_system_metrics()
    collector.save_metrics(system_metrics, collector.system_metrics_file)
    
    print(f"System metrics collected:")
    print(f"  CPU: {system_metrics.cpu_percent}%")
    print(f"  Memory: {system_metrics.memory_percent}%")
    print(f"  Disk: {system_metrics.disk_usage_percent}%")
    
    # Generate reports
    print("\nGenerating reports...")
    system_report = collector.generate_system_report(24)
    app_report = collector.generate_application_report(24)
    business_report = collector.generate_business_report(24)
    
    print(f"System Report (24h): {system_report}")
    print(f"Application Report (24h): {app_report}")
    print(f"Business Report (24h): {business_report}")
    
    # Cleanup old metrics
    print("\nCleaning up old metrics...")
    collector.cleanup_old_metrics(30)
    
    print("Metrics collection completed")


if __name__ == "__main__":
    main()
