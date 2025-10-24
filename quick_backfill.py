#!/usr/bin/env python3
"""
Quick back-fill script for specific date ranges.
Usage: python3 quick_backfill.py [start_date] [end_date]
Example: python3 quick_backfill.py 2024-01-01 2024-01-31
"""
import sys
import argparse
from datetime import datetime, timedelta
import logging

# Add parent directory to path
sys.path.insert(0, '.')

from backfill_historical_data import backfill_date_range
from database.models import DatabaseManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='Quick back-fill historical exchange rate data')
    parser.add_argument('start_date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('end_date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--force', action='store_true', help='Force back-fill even if data exists')
    
    args = parser.parse_args()
    
    try:
        # Parse dates
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
        
        if start_date > end_date:
            logger.error("Start date must be before end date")
            return
        
        logger.info(f"Back-filling data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Initialize database
        db_manager = DatabaseManager()
        
        # Check existing data if not forcing
        if not args.force:
            existing_dates = set()
            try:
                rates = db_manager.get_rates_by_date_range(start_date, end_date)
                existing_dates = {rate.timestamp.date() for rate in rates}
                logger.info(f"Found {len(existing_dates)} existing dates in range")
            except Exception as e:
                logger.warning(f"Could not check existing dates: {e}")
        
        # Back-fill data
        total_saved = backfill_date_range(start_date, end_date, db_manager)
        
        logger.info(f"Back-fill complete! Saved {total_saved} exchange rates")
        
        # Generate API data
        logger.info("Generating API data...")
        try:
            import subprocess
            result = subprocess.run([sys.executable, 'generate_api_data.py'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("API data generation completed")
            else:
                logger.error(f"API data generation failed: {result.stderr}")
        except Exception as e:
            logger.error(f"Error generating API data: {e}")
        
    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        logger.error("Please use YYYY-MM-DD format")
    except Exception as e:
        logger.error(f"Back-fill failed: {e}")

if __name__ == "__main__":
    main()
