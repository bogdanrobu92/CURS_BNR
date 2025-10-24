#!/usr/bin/env python3
"""
Back-fill historical exchange rate data from BNR API.
This script fetches historical data and populates the database.
"""
import os
import sys
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time
import logging
from typing import Dict, List, Optional
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from database.models import DatabaseManager, ExchangeRate
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# BNR API configuration
BNR_API_BASE = 'https://www.bnr.ro/nbrfxrates.xml'
SUPPORTED_CURRENCIES = ['EUR', 'USD', 'GBP']
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 0.3

def create_secure_session() -> requests.Session:
    """Create a secure HTTP session with retry logic."""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=RETRY_BACKOFF_FACTOR,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    session.headers.update({
        'User-Agent': 'BNR-Exchange-Rate-Monitor/2.0.0',
        'Accept': 'application/xml, text/xml, */*',
        'Accept-Encoding': 'gzip, deflate'
    })
    
    return session

def get_bnr_historical_rates(date: datetime) -> Dict[str, float]:
    """Fetch exchange rates for a specific date from BNR API."""
    session = create_secure_session()
    
    try:
        # BNR API accepts date parameter for historical data
        date_str = date.strftime('%Y-%m-%d')
        url = f"{BNR_API_BASE}?date={date_str}"
        
        logger.info(f"Fetching rates for {date_str}")
        response = session.get(url, timeout=REQUEST_TIMEOUT, verify=True)
        response.raise_for_status()
        
        # Parse XML response
        try:
            tree = ET.fromstring(response.content)
        except ET.ParseError as e:
            logger.error(f"Failed to parse XML response for {date_str}: {e}")
            return {}
        
        ns = {'ns': 'http://www.bnr.ro/xsd'}
        rates = {}
        
        for rate in tree.findall('.//ns:Rate', ns):
            currency = rate.attrib.get('currency')
            rate_value = rate.text
            
            if currency and rate_value and currency in SUPPORTED_CURRENCIES:
                try:
                    rates[currency] = float(rate_value)
                except ValueError:
                    logger.warning(f"Invalid rate value for {currency} on {date_str}: {rate_value}")
                    continue
        
        logger.info(f"Retrieved {len(rates)} rates for {date_str}")
        return rates
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for {date_str}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error fetching rates for {date_str}: {e}")
        return {}
    finally:
        session.close()

def backfill_date_range(start_date: datetime, end_date: datetime, db_manager: DatabaseManager) -> int:
    """Back-fill data for a date range."""
    total_rates_saved = 0
    current_date = start_date
    
    while current_date <= end_date:
        # Skip weekends (BNR doesn't publish rates on weekends)
        if current_date.weekday() < 5:  # Monday = 0, Friday = 4
            rates = get_bnr_historical_rates(current_date)
            
            if rates:
                # Save rates to database
                exchange_rates = []
                for currency, rate in rates.items():
                    exchange_rate = ExchangeRate(
                        id=None,
                        currency=currency,
                        rate=rate,
                        source='BNR',
                        timestamp=current_date,
                        multiplier=1,
                        is_valid=True
                    )
                    exchange_rates.append(exchange_rate)
                
                if exchange_rates:
                    try:
                        db_manager.save_exchange_rates(exchange_rates)
                        total_rates_saved += len(exchange_rates)
                        logger.info(f"Saved {len(exchange_rates)} rates for {current_date.strftime('%Y-%m-%d')}")
                    except Exception as e:
                        logger.error(f"Failed to save rates for {current_date.strftime('%Y-%m-%d')}: {e}")
            else:
                logger.warning(f"No rates found for {current_date.strftime('%Y-%m-%d')}")
        
        # Move to next day
        current_date += timedelta(days=1)
        
        # Add small delay to be respectful to the API
        time.sleep(0.5)
    
    return total_rates_saved

def get_existing_dates(db_manager: DatabaseManager) -> set:
    """Get dates that already have data in the database."""
    try:
        rates = db_manager.get_rates_by_date_range(
            datetime(2020, 1, 1),  # Start from 2020
            datetime.now()
        )
        existing_dates = set()
        for rate in rates:
            existing_dates.add(rate.timestamp.date())
        return existing_dates
    except Exception as e:
        logger.error(f"Error getting existing dates: {e}")
        return set()

def main():
    """Main back-fill function."""
    if not DATABASE_AVAILABLE:
        logger.error("Database not available. Please ensure database models are properly configured.")
        return
    
    try:
        db_manager = DatabaseManager()
        logger.info("Database connection established")
        
        # Get existing dates to avoid duplicates
        existing_dates = get_existing_dates(db_manager)
        logger.info(f"Found {len(existing_dates)} existing dates in database")
        
        # Define back-fill periods
        backfill_periods = [
            {
                'name': 'Last 3 months',
                'start': datetime.now() - timedelta(days=90),
                'end': datetime.now()
            },
            {
                'name': 'Last year',
                'start': datetime.now() - timedelta(days=365),
                'end': datetime.now() - timedelta(days=90)
            },
            {
                'name': 'Previous year',
                'start': datetime.now() - timedelta(days=730),
                'end': datetime.now() - timedelta(days=365)
            }
        ]
        
        total_saved = 0
        
        for period in backfill_periods:
            logger.info(f"\n=== Back-filling {period['name']} ===")
            logger.info(f"Period: {period['start'].strftime('%Y-%m-%d')} to {period['end'].strftime('%Y-%m-%d')}")
            
            # Filter out existing dates
            current_date = period['start']
            dates_to_fetch = []
            
            while current_date <= period['end']:
                if current_date.weekday() < 5 and current_date.date() not in existing_dates:
                    dates_to_fetch.append(current_date)
                current_date += timedelta(days=1)
            
            logger.info(f"Need to fetch {len(dates_to_fetch)} new dates")
            
            if dates_to_fetch:
                period_saved = backfill_date_range(
                    min(dates_to_fetch),
                    max(dates_to_fetch),
                    db_manager
                )
                total_saved += period_saved
                logger.info(f"Saved {period_saved} rates for {period['name']}")
            else:
                logger.info(f"No new dates to fetch for {period['name']}")
        
        logger.info(f"\n=== Back-fill Complete ===")
        logger.info(f"Total rates saved: {total_saved}")
        
        # Generate updated API data
        logger.info("Generating updated API data...")
        try:
            import subprocess
            result = subprocess.run([sys.executable, 'generate_api_data.py'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("API data generation completed successfully")
            else:
                logger.error(f"API data generation failed: {result.stderr}")
        except Exception as e:
            logger.error(f"Error generating API data: {e}")
        
    except Exception as e:
        logger.error(f"Back-fill failed with error: {e}")

if __name__ == "__main__":
    main()
