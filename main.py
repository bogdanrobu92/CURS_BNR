import os
import requests
import xml.etree.ElementTree as ET
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

# Email functionality removed - focusing on data collection only

def collect_exchange_rates() -> Dict[str, str]:
    """Collect exchange rates from BNR API and save to database."""
    logger.info("Starting BNR exchange rate collection")
    
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
                
                # Use best rates
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
        
        # Log summary
        logger.info(f"Retrieved {successful_rates}/{len(SUPPORTED_CURRENCIES)} exchange rates")
        
        if successful_rates > 0:
            logger.info("Exchange rate collection completed successfully")
            return rates
        else:
            logger.error("Failed to retrieve any exchange rates")
            return {}
            
    except Exception as e:
        logger.error(f"Exchange rate collection failed with unexpected error: {e}")
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
