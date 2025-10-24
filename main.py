import os
import requests
import xml.etree.ElementTree as ET
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import logging
import re
import time
from typing import Optional, Dict, List
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# Import monitoring modules
try:
    from monitoring.metrics import MetricsCollector
    from monitoring.health_check import HealthChecker
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False

# Import database and backup sources
try:
    from database.models import DatabaseManager, ExchangeRate, SystemMetrics
    from sources.backup_sources import BackupRateProvider
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

# Configure secure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
BNR_API_URL = 'https://www.bnr.ro/nbrfxrates.xml'
SUPPORTED_CURRENCIES = ['EUR', 'USD', 'GBP']
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 0.3

def validate_currency(currency: str) -> bool:
    """Validate currency code format and support."""
    if not isinstance(currency, str) or len(currency) != 3:
        return False
    return currency.upper() in SUPPORTED_CURRENCIES

def validate_email(email: str) -> bool:
    """Validate email format."""
    if not isinstance(email, str) or not email:
        return False
    
    # RFC 5322 compliant email validation pattern
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9._%+-]*[a-zA-Z0-9])?@[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}$'
    
    # Additional checks for common invalid patterns
    if '..' in email or email.startswith('.') or email.endswith('.'):
        return False
    if email.count('@') != 1:
        return False
    
    return re.match(pattern, email) is not None

def create_secure_session() -> requests.Session:
    """Create a secure HTTP session with retry logic and SSL verification."""
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=RETRY_BACKOFF_FACTOR,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Set secure headers
    session.headers.update({
        'User-Agent': 'BNR-Exchange-Rate-Monitor/1.0',
        'Accept': 'application/xml, text/xml, */*',
        'Accept-Encoding': 'gzip, deflate'
    })
    
    return session

def get_bnr_api_rate(currency: str) -> Optional[str]:
    """Securely fetch exchange rate from BNR API with validation and error handling."""
    if not validate_currency(currency):
        logger.error(f"Invalid currency code: {currency}")
        return None
    
    session = create_secure_session()
    
    try:
        logger.info(f"Fetching exchange rate for {currency}")
        response = session.get(
            BNR_API_URL, 
            timeout=REQUEST_TIMEOUT,
            verify=True  # Enable SSL certificate verification
        )
        response.raise_for_status()
        
        # Parse XML safely
        try:
            tree = ET.fromstring(response.content)
        except ET.ParseError as e:
            logger.error(f"Failed to parse XML response: {e}")
            return None
        
        ns = {'ns': 'http://www.bnr.ro/xsd'}
        for rate in tree.findall('.//ns:Rate', ns):
            if rate.attrib.get('currency') == currency.upper():
                rate_value = rate.text
                if rate_value and rate_value.strip():
                    logger.info(f"Successfully retrieved rate for {currency}: {rate_value}")
                    return rate_value.strip()
        
        logger.warning(f"Currency {currency} not found in API response")
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for {currency}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching rate for {currency}: {e}")
        return None
    finally:
        session.close()

def send_email(subject: str, body: str, to_email: str) -> bool:
    """Securely send email with validation and error handling."""
    try:
        # Validate email addresses
        from_email = os.environ.get('EMAIL_SENDER')
        app_password = os.environ.get('EMAIL_PASS')
        
        if not from_email or not app_password:
            logger.error("Email credentials not found in environment variables")
            return False
            
        if not validate_email(from_email):
            logger.error(f"Invalid sender email format: {from_email}")
            return False
            
        if not validate_email(to_email):
            logger.error(f"Invalid recipient email format: {to_email}")
            return False
        
        # Sanitize subject and body
        subject = subject.strip()[:100]  # Limit subject length
        body = body.strip()
        
        if not subject or not body:
            logger.error("Empty subject or body")
            return False
        
        # Create secure email message
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
        
        # Send email with secure connection
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30) as smtp:
            smtp.login(from_email, app_password)
            smtp.send_message(msg)
            
        logger.info(f"Email sent successfully to {to_email}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication failed: {e}")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending email: {e}")
        return False

def job() -> bool:
    """Main job function with comprehensive error handling, security, monitoring, and data persistence."""
    job_start_time = time.time()
    api_start_time = None
    email_start_time = None
    
    # Initialize components
    metrics_collector = None
    db_manager = None
    rate_provider = None
    
    if MONITORING_AVAILABLE:
        try:
            metrics_collector = MetricsCollector()
        except Exception as e:
            logger.warning(f"Failed to initialize metrics collector: {e}")
    
    if DATABASE_AVAILABLE:
        try:
            db_manager = DatabaseManager()
            rate_provider = BackupRateProvider()
        except Exception as e:
            logger.warning(f"Failed to initialize database components: {e}")
    
    try:
        logger.info("Starting BNR exchange rate job")
        
        # Validate environment variables
        recipient_email = os.environ.get('EMAIL_RECIPIENT')
        if not recipient_email or not validate_email(recipient_email):
            logger.error("Invalid or missing EMAIL_RECIPIENT environment variable")
            return False
        
        # Fetch exchange rates with fallback logic
        api_start_time = time.time()
        rates = {}
        error_count = 0
        
        if rate_provider and db_manager:
            # Use backup sources with fallback
            try:
                all_rates = rate_provider.get_rates_with_fallback(SUPPORTED_CURRENCIES)
                best_rates = rate_provider.get_best_rates(SUPPORTED_CURRENCIES)
                
                # Save all rates to database
                exchange_rates = []
                for source_name, source_rates in all_rates.items():
                    for currency, rate in source_rates.items():
                        if currency in SUPPORTED_CURRENCIES:
                            exchange_rate = ExchangeRate(
                                id=None,
                                currency=currency,
                                rate=rate,
                                source=source_name,
                                timestamp=datetime.now(),
                                multiplier=1,
                                is_valid=True
                            )
                            exchange_rates.append(exchange_rate)
                
                if exchange_rates:
                    db_manager.save_exchange_rates(exchange_rates)
                    logger.info(f"Saved {len(exchange_rates)} rates to database")
                
                # Use best rates for email
                rates = best_rates
                successful_rates = len([r for r in rates.values() if r])
                
            except Exception as e:
                logger.error(f"Backup sources failed: {e}, falling back to BNR only")
                # Fallback to original BNR API
                for currency in SUPPORTED_CURRENCIES:
                    rate = get_bnr_api_rate(currency)
                    rates[currency] = rate
                    if rate:
                        logger.info(f"Retrieved {currency} rate: {rate}")
                    else:
                        logger.warning(f"Failed to retrieve {currency} rate")
                        error_count += 1
                
                successful_rates = sum(1 for rate in rates.values() if rate)
        else:
            # Original BNR API only
            for currency in SUPPORTED_CURRENCIES:
                rate = get_bnr_api_rate(currency)
                rates[currency] = rate
                if rate:
                    logger.info(f"Retrieved {currency} rate: {rate}")
                else:
                    logger.warning(f"Failed to retrieve {currency} rate")
                    error_count += 1
            
            successful_rates = sum(1 for rate in rates.values() if rate)
        
        api_response_time = time.time() - api_start_time if api_start_time else 0
        
        # Format email body with enhanced information
        today = datetime.now().strftime("%d.%m.%Y")
        body_lines = [f"Curs BNR - {today}", ""]
        
        for currency, rate in rates.items():
            if rate:
                body_lines.append(f"{currency}: {rate}")
            else:
                body_lines.append(f"{currency}: Curs indisponibil")
        
        # Add trend information if available
        if db_manager:
            try:
                trends = db_manager.get_rate_trends('EUR', 7)
                if trends:
                    latest_trend = trends[-1]
                    body_lines.append("")
                    body_lines.append("Tendințe (7 zile):")
                    body_lines.append(f"EUR: {latest_trend.change_percentage:+.2f}% ({latest_trend.trend_direction})")
            except Exception as e:
                logger.warning(f"Failed to add trend information: {e}")
        
        body = "\n".join(body_lines)
        
        # Log summary (without sensitive data)
        logger.info(f"Retrieved {successful_rates}/{len(SUPPORTED_CURRENCIES)} exchange rates")
        
        # Send email
        email_start_time = time.time()
        subject = f"Curs BNR {today}"
        email_sent = send_email(subject, body, recipient_email)
        email_send_time = time.time() - email_start_time if email_start_time else 0
        
        job_execution_time = time.time() - job_start_time
        job_success = email_sent
        
        # Collect and save metrics
        if metrics_collector:
            try:
                # Collect application metrics
                app_metrics = metrics_collector.collect_application_metrics(
                    job_execution_time=job_execution_time,
                    api_response_time=api_response_time,
                    email_send_time=email_send_time,
                    rates_retrieved=successful_rates,
                    rates_failed=len(SUPPORTED_CURRENCIES) - successful_rates,
                    job_success=job_success,
                    error_count=error_count
                )
                metrics_collector.save_metrics(app_metrics, metrics_collector.app_metrics_file)
                
                # Collect business metrics
                api_availability = (successful_rates / len(SUPPORTED_CURRENCIES)) * 100
                business_metrics = metrics_collector.collect_business_metrics(
                    eur_rate=rates.get('EUR'),
                    usd_rate=rates.get('USD'),
                    gbp_rate=rates.get('GBP'),
                    api_availability=api_availability
                )
                metrics_collector.save_metrics(business_metrics, metrics_collector.business_metrics_file)
                
                # Collect system metrics
                system_metrics = metrics_collector.collect_system_metrics()
                metrics_collector.save_metrics(system_metrics, metrics_collector.system_metrics_file)
                
            except Exception as e:
                logger.warning(f"Failed to collect metrics: {e}")
        
        # Save system metrics to database
        if db_manager:
            try:
                import psutil
                memory = psutil.virtual_memory()
                cpu_percent = psutil.cpu_percent()
                
                system_metrics = SystemMetrics(
                    id=None,
                    timestamp=datetime.now(),
                    job_execution_time=job_execution_time,
                    api_response_time=api_response_time,
                    email_send_time=email_send_time,
                    rates_retrieved=successful_rates,
                    rates_failed=len(SUPPORTED_CURRENCIES) - successful_rates,
                    job_success=job_success,
                    error_count=error_count,
                    memory_usage_mb=memory.used / (1024 * 1024),
                    cpu_percent=cpu_percent
                )
                db_manager.save_system_metrics(system_metrics)
                
            except Exception as e:
                logger.warning(f"Failed to save system metrics to database: {e}")
        
        if email_sent:
            logger.info(f"Job completed successfully in {job_execution_time:.2f} seconds")
            return True
        else:
            logger.error("Job failed - email not sent")
            return False
            
    except Exception as e:
        logger.error(f"Job failed with unexpected error: {e}")
        return False

if __name__ == "__main__":
    try:
        success = job()
        exit_code = 0 if success else 1
        logger.info(f"Script completed with exit code: {exit_code}")
        exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        exit(130)
    except Exception as e:
        logger.error(f"Script failed with critical error: {e}")
        exit(1)
