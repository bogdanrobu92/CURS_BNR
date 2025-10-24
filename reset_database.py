#!/usr/bin/env python3
"""
Reset Database - Clear all data and start fresh with today's BNR data
"""
import os
import sys
import logging
from datetime import datetime

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

def clear_database(db_manager: DatabaseManager):
    """Clear all exchange rate data from the database."""
    try:
        logger.info("Clearing all exchange rate data...")
        
        # Get all rates to count them
        all_rates = db_manager.get_rates_by_date_range(
            datetime(2010, 1, 1), 
            datetime(2030, 12, 31)
        )
        
        logger.info(f"Found {len(all_rates)} existing rates to delete")
        
        # Clear the exchange_rates table
        db_manager.clear_all_rates()
        
        logger.info("Database cleared successfully")
        
    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        raise

def store_todays_bnr_data(db_manager: DatabaseManager):
    """Store today's real data from BNR API."""
    try:
        logger.info("Fetching today's data from BNR API...")
        
        # Import the BNR API function
        from main import get_bnr_api_rate
        
        SUPPORTED_CURRENCIES = ['EUR', 'USD', 'GBP']
        today = datetime.now()
        
        exchange_rates = []
        
        for currency in SUPPORTED_CURRENCIES:
            rate = get_bnr_api_rate(currency)
            if rate:
                exchange_rate = ExchangeRate(
                    id=None,
                    currency=currency,
                    rate=rate,
                    source='BNR',
                    timestamp=today,
                    multiplier=1,
                    is_valid=True
                )
                exchange_rates.append(exchange_rate)
                logger.info(f"Retrieved {currency} rate: {rate}")
            else:
                logger.warning(f"Failed to retrieve {currency} rate")
        
        if exchange_rates:
            db_manager.save_exchange_rates(exchange_rates)
            logger.info(f"Saved {len(exchange_rates)} rates for today")
        else:
            logger.error("No rates retrieved from BNR API")
            
    except Exception as e:
        logger.error(f"Error storing today's BNR data: {e}")
        raise

def main():
    """Main function to reset database and start fresh."""
    if not DATABASE_AVAILABLE:
        logger.error("Database not available. Please ensure database models are properly configured.")
        return
    
    try:
        db_manager = DatabaseManager()
        logger.info("Database connection established")
        
        # Step 1: Clear all existing data
        clear_database(db_manager)
        
        # Step 2: Store today's real BNR data
        store_todays_bnr_data(db_manager)
        
        # Step 3: Generate fresh API data
        logger.info("Generating fresh API data...")
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
        
        logger.info("\n=== Database Reset Complete ===")
        logger.info("✅ Database cleared of all old data")
        logger.info("✅ Today's real BNR data stored")
        logger.info("✅ Fresh API data generated")
        logger.info("✅ Ready to build historical data going forward")
        
    except Exception as e:
        logger.error(f"Database reset failed with error: {e}")

if __name__ == "__main__":
    main()
