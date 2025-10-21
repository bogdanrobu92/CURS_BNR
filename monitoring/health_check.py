#!/usr/bin/env python3
"""
Health check module for BNR Exchange Rate Monitor.
Provides system health monitoring and alerting capabilities.
"""
import os
import sys
import time
import logging
import requests
import smtplib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


@dataclass
class HealthStatus:
    """Health status data class."""
    service: str
    status: str  # 'healthy', 'degraded', 'unhealthy'
    message: str
    timestamp: datetime
    response_time: Optional[float] = None
    error_count: int = 0


class HealthChecker:
    """Health monitoring and alerting system."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.health_history: List[HealthStatus] = []
        self.alert_threshold = 3  # Number of consecutive failures before alert
        self.max_history = 100  # Maximum health history entries
        
    def check_bnr_api_health(self) -> HealthStatus:
        """Check BNR API health and response time."""
        start_time = time.time()
        
        try:
            response = requests.get(
                'https://www.bnr.ro/nbrfxrates.xml',
                timeout=30,
                verify=True
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                return HealthStatus(
                    service="BNR API",
                    status="healthy",
                    message=f"API responding normally (HTTP {response.status_code})",
                    timestamp=datetime.now(),
                    response_time=response_time
                )
            else:
                return HealthStatus(
                    service="BNR API",
                    status="degraded",
                    message=f"API returned HTTP {response.status_code}",
                    timestamp=datetime.now(),
                    response_time=response_time
                )
                
        except requests.exceptions.Timeout:
            return HealthStatus(
                service="BNR API",
                status="unhealthy",
                message="API timeout after 30 seconds",
                timestamp=datetime.now(),
                response_time=time.time() - start_time
            )
        except requests.exceptions.ConnectionError:
            return HealthStatus(
                service="BNR API",
                status="unhealthy",
                message="Connection error - API unreachable",
                timestamp=datetime.now(),
                response_time=time.time() - start_time
            )
        except Exception as e:
            return HealthStatus(
                service="BNR API",
                status="unhealthy",
                message=f"Unexpected error: {str(e)}",
                timestamp=datetime.now(),
                response_time=time.time() - start_time
            )
    
    def check_email_service_health(self) -> HealthStatus:
        """Check email service health."""
        try:
            # Test SMTP connection
            from_email = os.environ.get('EMAIL_SENDER')
            app_password = os.environ.get('EMAIL_PASS')
            
            if not from_email or not app_password:
                return HealthStatus(
                    service="Email Service",
                    status="unhealthy",
                    message="Email credentials not configured",
                    timestamp=datetime.now()
                )
            
            # Test SMTP connection
            with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10) as smtp:
                smtp.login(from_email, app_password)
                
            return HealthStatus(
                service="Email Service",
                status="healthy",
                message="SMTP connection successful",
                timestamp=datetime.now()
            )
            
        except smtplib.SMTPAuthenticationError:
            return HealthStatus(
                service="Email Service",
                status="unhealthy",
                message="SMTP authentication failed",
                timestamp=datetime.now()
            )
        except smtplib.SMTPException as e:
            return HealthStatus(
                service="Email Service",
                status="degraded",
                message=f"SMTP error: {str(e)}",
                timestamp=datetime.now()
            )
        except Exception as e:
            return HealthStatus(
                service="Email Service",
                status="unhealthy",
                message=f"Unexpected error: {str(e)}",
                timestamp=datetime.now()
            )
    
    def check_system_health(self) -> HealthStatus:
        """Check overall system health."""
        try:
            # Check if main module can be imported
            import main
            
            # Check environment variables
            required_vars = ['EMAIL_SENDER', 'EMAIL_PASS', 'EMAIL_RECIPIENT']
            missing_vars = [var for var in required_vars if not os.environ.get(var)]
            
            if missing_vars:
                return HealthStatus(
                    service="System",
                    status="unhealthy",
                    message=f"Missing environment variables: {', '.join(missing_vars)}",
                    timestamp=datetime.now()
                )
            
            return HealthStatus(
                service="System",
                status="healthy",
                message="System configuration valid",
                timestamp=datetime.now()
            )
            
        except ImportError as e:
            return HealthStatus(
                service="System",
                status="unhealthy",
                message=f"Import error: {str(e)}",
                timestamp=datetime.now()
            )
        except Exception as e:
            return HealthStatus(
                service="System",
                status="unhealthy",
                message=f"System error: {str(e)}",
                timestamp=datetime.now()
            )
    
    def run_health_checks(self) -> List[HealthStatus]:
        """Run all health checks."""
        checks = [
            self.check_system_health(),
            self.check_bnr_api_health(),
            self.check_email_service_health()
        ]
        
        # Store in history
        self.health_history.extend(checks)
        
        # Keep only recent history
        if len(self.health_history) > self.max_history:
            self.health_history = self.health_history[-self.max_history:]
        
        return checks
    
    def get_health_summary(self) -> Dict[str, any]:
        """Get overall health summary."""
        if not self.health_history:
            return {"status": "unknown", "message": "No health checks performed"}
        
        recent_checks = self.health_history[-10:]  # Last 10 checks
        
        # Count statuses
        status_counts = {}
        for check in recent_checks:
            status_counts[check.status] = status_counts.get(check.status, 0) + 1
        
        # Determine overall status
        if status_counts.get('unhealthy', 0) > 0:
            overall_status = 'unhealthy'
        elif status_counts.get('degraded', 0) > 0:
            overall_status = 'degraded'
        else:
            overall_status = 'healthy'
        
        return {
            "status": overall_status,
            "status_counts": status_counts,
            "total_checks": len(recent_checks),
            "last_check": recent_checks[-1].timestamp.isoformat() if recent_checks else None
        }
    
    def check_for_alerts(self) -> List[str]:
        """Check if any alerts should be triggered."""
        alerts = []
        
        if len(self.health_history) < self.alert_threshold:
            return alerts
        
        # Check for consecutive failures
        recent_checks = self.health_history[-self.alert_threshold:]
        
        # Group by service
        services = {}
        for check in recent_checks:
            if check.service not in services:
                services[check.service] = []
            services[check.service].append(check)
        
        # Check each service for consecutive failures
        for service, checks in services.items():
            if len(checks) >= self.alert_threshold:
                consecutive_failures = 0
                for check in reversed(checks):
                    if check.status in ['unhealthy', 'degraded']:
                        consecutive_failures += 1
                    else:
                        break
                
                if consecutive_failures >= self.alert_threshold:
                    alerts.append(f"ALERT: {service} has {consecutive_failures} consecutive failures")
        
        return alerts
    
    def send_health_alert(self, alerts: List[str]) -> bool:
        """Send health alert email."""
        try:
            from_email = os.environ.get('EMAIL_SENDER')
            app_password = os.environ.get('EMAIL_PASS')
            to_email = os.environ.get('EMAIL_RECIPIENT')
            
            if not all([from_email, app_password, to_email]):
                self.logger.error("Cannot send alert - email credentials not configured")
                return False
            
            # Create alert message
            subject = f"BNR Monitor Health Alert - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            body = f"""
BNR Exchange Rate Monitor Health Alert

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Alerts:
{chr(10).join(f"- {alert}" for alert in alerts)}

Health Summary:
{self.get_health_summary()}

Please check the system logs for more details.
"""
            
            # Send email
            msg = MIMEText(body, 'plain', 'utf-8')
            msg['Subject'] = subject
            msg['From'] = from_email
            msg['To'] = to_email
            
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(from_email, app_password)
                smtp.send_message(msg)
            
            self.logger.info(f"Health alert sent: {len(alerts)} alerts")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send health alert: {e}")
            return False
    
    def generate_health_report(self) -> str:
        """Generate detailed health report."""
        summary = self.get_health_summary()
        
        report = f"""
BNR Exchange Rate Monitor - Health Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Overall Status: {summary['status'].upper()}
Total Checks: {summary['total_checks']}
Last Check: {summary['last_check']}

Status Breakdown:
"""
        
        for status, count in summary['status_counts'].items():
            report += f"  {status}: {count}\n"
        
        report += "\nRecent Health Checks:\n"
        
        # Show last 5 checks
        recent_checks = self.health_history[-5:] if self.health_history else []
        for check in recent_checks:
            report += f"  {check.timestamp.strftime('%H:%M:%S')} - {check.service}: {check.status} - {check.message}\n"
        
        return report


def main():
    """Main health check function."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    checker = HealthChecker()
    
    print("Running health checks...")
    checks = checker.run_health_checks()
    
    # Print results
    for check in checks:
        status_icon = "✅" if check.status == "healthy" else "⚠️" if check.status == "degraded" else "❌"
        print(f"{status_icon} {check.service}: {check.status} - {check.message}")
    
    # Check for alerts
    alerts = checker.check_for_alerts()
    if alerts:
        print(f"\n🚨 {len(alerts)} alerts triggered:")
        for alert in alerts:
            print(f"  - {alert}")
        
        # Send alert email
        if checker.send_health_alert(alerts):
            print("📧 Alert email sent")
        else:
            print("❌ Failed to send alert email")
    
    # Generate report
    report = checker.generate_health_report()
    print(f"\n{report}")
    
    # Return exit code based on health
    summary = checker.get_health_summary()
    if summary['status'] == 'unhealthy':
        sys.exit(1)
    elif summary['status'] == 'degraded':
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
