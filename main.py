import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import logging
import re
import time
from typing import Optional, Dict, List, Tuple
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
    from fallback_handler import apply_fallback_if_needed
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

# Configure structured logging
try:
    from utils.logging_config import setup_logging, get_logger
    logger = setup_logging(
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        log_file=os.getenv('LOG_FILE', 'main.log'),
        log_dir=os.getenv('LOG_DIR', 'logs'),
        use_json=os.getenv('LOG_FORMAT', '').lower() == 'json'
    )
    logger = get_logger(__name__)
except ImportError:
    # Fallback to basic logging if logging_config not available
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
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

def validate_rate(rate: float) -> bool:
    """Validate rate is reasonable."""
    if rate <= 0:
        logger.warning(f"Invalid rate: {rate} (must be positive)")
        return False
    # RON rates typically between 0.1-100 for major currencies
    if rate >= 100 or rate < 0.1:
        logger.warning(f"Suspicious rate value: {rate} (expected range: 0.1-100)")
        return False
    return True

# Email validation removed - no longer needed

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

# Simple cache for BNR API responses (5 minute TTL)
_BNR_API_CACHE: Dict[str, Tuple[float, Optional[float]]] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes

def get_bnr_api_rate(currency: str) -> Optional[float]:
    """Securely fetch exchange rate from BNR API with validation and error handling.
    
    Uses caching to avoid redundant API calls within a short time window.
    """
    if not validate_currency(currency):
        logger.error(f"Invalid currency code: {currency}")
        return None
    
    # Check cache first
    cache_key = currency.upper()
    current_time = time.time()
    
    if cache_key in _BNR_API_CACHE:
        cached_time, cached_rate = _BNR_API_CACHE[cache_key]
        if current_time - cached_time < _CACHE_TTL_SECONDS:
            logger.debug(f"Using cached rate for {currency}: {cached_rate}")
            return cached_rate
    
    # Cache miss or expired - fetch from API
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
                    try:
                        float_rate = float(rate_value.strip())
                        logger.info(f"Successfully retrieved rate for {currency}: {float_rate}")
                        # Update cache
                        _BNR_API_CACHE[cache_key] = (current_time, float_rate)
                        return float_rate
                    except ValueError:
                        logger.error(f"Invalid rate value for {currency}: {rate_value}")
                        return None
        
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

def detect_rate_changes(
    current_rates: Dict[str, float], 
    db_manager: DatabaseManager,
    threshold_percent: float = 2.0
) -> List[Dict]:
    """Detect significant rate changes and return alerts.
    
    Args:
        current_rates: Dictionary of current exchange rates {currency: rate}
        db_manager: Database manager instance
        threshold_percent: Minimum percentage change to trigger alert (default: 2.0%)
    
    Returns:
        List of dictionaries with change information:
        {
            'currency': str,
            'previous_rate': float,
            'current_rate': float,
            'change_percent': float,
            'change_absolute': float
        }
    """
    alerts = []
    
    if not DATABASE_AVAILABLE or not db_manager:
        return alerts
    
    for currency, current_rate in current_rates.items():
        try:
            latest_db_rates = db_manager.get_latest_rates(currency)
            if latest_db_rates:
                # Get the most recent rate from DB (excluding current rate if it was just saved)
                previous_rate = None
                for rate in reversed(latest_db_rates):
                    if rate.currency == currency and rate.source != 'BNR (Fallback)':
                        previous_rate = rate.rate
                        break
                
                if previous_rate and previous_rate > 0:
                    change_absolute = current_rate - previous_rate
                    change_percent = abs((change_absolute / previous_rate) * 100)
                    
                    if change_percent >= threshold_percent:
                        alerts.append({
                            'currency': currency,
                            'previous_rate': previous_rate,
                            'current_rate': current_rate,
                            'change_percent': change_percent,
                            'change_absolute': change_absolute,
                            'direction': 'up' if change_absolute > 0 else 'down'
                        })
                        logger.warning(
                            f"Significant rate change detected for {currency}: "
                            f"{previous_rate:.4f} -> {current_rate:.4f} "
                            f"({change_percent:.2f}% {'increase' if change_absolute > 0 else 'decrease'})"
                        )
        except Exception as e:
            logger.warning(f"Error detecting rate changes for {currency}: {e}")
            continue
    
    return alerts

# Email functionality removed - focusing on data collection only

def fetch_rates_from_bnr_api(currencies: List[str]) -> Tuple[Dict[str, Optional[float]], int]:
    """Fetch rates from BNR API for given currencies.
    
    Supports both sync and async modes based on USE_ASYNC environment variable.
    
    Args:
        currencies: List of currency codes to fetch
        
    Returns:
        Tuple of (rates dictionary, error_count)
    """
    # Check if async mode is enabled
    use_async = os.getenv('USE_ASYNC', 'false').lower() == 'true'
    
    if use_async:
        try:
            from utils.async_fetcher import run_async_collection
            rates = run_async_collection(currencies, BNR_API_URL, REQUEST_TIMEOUT)
            error_count = sum(1 for rate in rates.values() if rate is None)
            return rates, error_count
        except ImportError:
            logger.warning("Async fetcher not available, falling back to sync mode")
        except Exception as e:
            logger.warning(f"Async fetch failed: {e}, falling back to sync mode")
    
    # Fallback to sync mode
    rates: Dict[str, Optional[float]] = {}
    error_count = 0
    
    for currency in currencies:
        rate = get_bnr_api_rate(currency)
        rates[currency] = rate
        if rate is not None:
            logger.info(f"Retrieved {currency} rate: {rate}")
        else:
            logger.warning(f"Failed to retrieve {currency} rate")
            error_count += 1
    
    return rates, error_count

def collect_exchange_rates() -> Dict[str, float]:
    """Collect exchange rates from BNR API and save to database."""
    logger.info("Starting BNR exchange rate collection")
    
    # Initialize monitoring
    metrics_collector = None
    health_checker = None
    if MONITORING_AVAILABLE:
        try:
            metrics_collector = MetricsCollector()
            health_checker = HealthChecker()
            # Run initial health checks
            health_checks = health_checker.run_health_checks()
            health_summary = health_checker.get_health_summary()
            logger.info(f"Health check status: {health_summary['status']}")
            
            # Check for alerts
            alerts = health_checker.check_for_alerts()
            if alerts:
                logger.warning(f"Health alerts detected: {len(alerts)} alerts")
                for alert in alerts:
                    logger.warning(f"  - {alert}")
        except Exception as e:
            logger.warning(f"Failed to initialize monitoring components: {e}")
    
    start_time = time.time()
    api_start_time = start_time
    
    # Initialize components
    db_manager = None
    rate_provider = None
    
    if DATABASE_AVAILABLE:
        try:
            db_manager = DatabaseManager()
            rate_provider = BackupRateProvider()
        except Exception as e:
            logger.warning(f"Failed to initialize database components: {e}")
    
    try:
        # Fetch exchange rates with fallback logic
        rates: Dict[str, Optional[float]] = {}
        error_count = 0
        
        if rate_provider and db_manager:
            # Use backup sources with fallback
            api_start_time = time.time()  # Initialize before try block
            try:
                all_rates = rate_provider.get_rates_with_fallback(SUPPORTED_CURRENCIES)
                best_rates = rate_provider.get_best_rates(SUPPORTED_CURRENCIES)
                api_response_time = time.time() - api_start_time
                
                # Save all rates to database
                exchange_rates = []
                for source_name, source_rates in all_rates.items():
                    for currency, rate in source_rates.items():
                        if currency in SUPPORTED_CURRENCIES:
                            if not validate_rate(rate):
                                logger.warning(f"Invalid rate for {currency}: {rate}, skipping")
                                continue
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
                    try:
                        db_manager.save_exchange_rates(exchange_rates)
                        logger.info(f"Saved {len(exchange_rates)} rates to database")
                    except Exception as db_error:
                        logger.error(f"Failed to save rates to database: {db_error}")
                        # Continue with best_rates even if save failed
                
                # Use best rates
                rates = best_rates
                successful_rates = len([r for r in rates.values() if r is not None])
                
            except Exception as e:
                logger.error(f"Backup sources failed: {e}, falling back to BNR only")
                # Calculate api_response_time from the start of API call attempt
                api_response_time = time.time() - api_start_time
                # Fallback to original BNR API
                rates, error_count = fetch_rates_from_bnr_api(SUPPORTED_CURRENCIES)
                successful_rates = sum(1 for rate in rates.values() if rate is not None)
                
                # Save the BNR rates to database
                if successful_rates > 0 and db_manager:
                    try:
                        exchange_rates = []
                        for currency, rate in rates.items():
                            if rate is not None:
                                exchange_rate = ExchangeRate(
                                    id=None,
                                    currency=currency,
                                    rate=rate,
                                    source='BNR',
                                    timestamp=datetime.now(),
                                    multiplier=1,
                                    is_valid=True
                                )
                                exchange_rates.append(exchange_rate)
                        if exchange_rates:
                            db_manager.save_exchange_rates(exchange_rates)
                            logger.info(f"Saved {len(exchange_rates)} BNR rates to database")
                    except Exception as db_error:
                        logger.error(f"Failed to save BNR rates to database: {db_error}")
        else:
            # Original BNR API only
            api_start_time = time.time()
            rates, error_count = fetch_rates_from_bnr_api(SUPPORTED_CURRENCIES)
            api_response_time = time.time() - api_start_time
            successful_rates = sum(1 for rate in rates.values() if rate is not None)
        
        # Apply fallback logic if API didn't return data
        if successful_rates == 0 and db_manager:
            logger.info("No rates from API, applying fallback logic...")
            rates = apply_fallback_if_needed(rates, db_manager, SUPPORTED_CURRENCIES, max_age_days=3)
            successful_rates = len([r for r in rates.values() if r is not None])
            logger.info(f"After fallback: Retrieved {successful_rates}/{len(SUPPORTED_CURRENCIES)} exchange rates")
        
        # Log summary
        logger.info(f"Retrieved {successful_rates}/{len(SUPPORTED_CURRENCIES)} exchange rates")
        
        # Collect and save metrics
        if metrics_collector:
            try:
                execution_time = time.time() - start_time
                rates_failed = len(SUPPORTED_CURRENCIES) - successful_rates
                
                app_metrics = metrics_collector.collect_application_metrics(
                    job_execution_time=execution_time,
                    api_response_time=api_response_time,
                    email_send_time=0.0,  # Email functionality removed
                    rates_retrieved=successful_rates,
                    rates_failed=rates_failed,
                    job_success=successful_rates > 0,
                    error_count=error_count
                )
                metrics_collector.save_metrics(app_metrics, metrics_collector.app_metrics_file)
                logger.info(f"Metrics collected: execution_time={execution_time:.2f}s, rates_retrieved={successful_rates}, rates_failed={rates_failed}")
            except Exception as e:
                logger.warning(f"Failed to save metrics: {e}")
        
        # Run final health checks after collection
        if health_checker:
            try:
                final_health_checks = health_checker.run_health_checks()
                final_summary = health_checker.get_health_summary()
                logger.info(f"Final health check status: {final_summary['status']}")
                
                # Check for new alerts after collection
                final_alerts = health_checker.check_for_alerts()
                if final_alerts:
                    logger.warning(f"Post-collection health alerts: {len(final_alerts)} alerts")
                    for alert in final_alerts:
                        logger.warning(f"  - {alert}")
            except Exception as e:
                logger.warning(f"Failed to run final health checks: {e}")
        
        # Detect significant rate changes
        if db_manager and successful_rates > 0:
            try:
                final_rates = {k: v for k, v in rates.items() if v is not None}
                rate_changes = detect_rate_changes(final_rates, db_manager, threshold_percent=2.0)
                if rate_changes:
                    logger.info(f"Detected {len(rate_changes)} significant rate changes")
                    for alert in rate_changes:
                        logger.info(
                            f"  {alert['currency']}: {alert['change_percent']:.2f}% "
                            f"({alert['direction']})"
                        )
            except Exception as e:
                logger.warning(f"Failed to detect rate changes: {e}")
        
        if successful_rates > 0:
            logger.info("Exchange rate collection completed successfully")
            # Filter out None values and return only float values
            return {k: v for k, v in rates.items() if v is not None}
        else:
            logger.error("Failed to retrieve any exchange rates")
            return {}
            
    except Exception as e:
        logger.error(f"Exchange rate collection failed with unexpected error: {e}")
        # Still try to save metrics even on error
        if metrics_collector:
            try:
                execution_time = time.time() - start_time
                app_metrics = metrics_collector.collect_application_metrics(
                    job_execution_time=execution_time,
                    api_response_time=0.0,
                    email_send_time=0.0,
                    rates_retrieved=0,
                    rates_failed=len(SUPPORTED_CURRENCIES),
                    job_success=False,
                    error_count=error_count + 1
                )
                metrics_collector.save_metrics(app_metrics, metrics_collector.app_metrics_file)
            except Exception:
                pass  # Don't fail on metrics save error
        return {}

if __name__ == "__main__":
    try:
        rates = collect_exchange_rates()
        success = len(rates) > 0
        exit_code = 0 if success else 1
        logger.info(f"Script completed with exit code: {exit_code}")
        exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        exit(130)
    except Exception as e:
        logger.error(f"Script failed with critical error: {e}")
        exit(1)
