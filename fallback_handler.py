"""Fallback handler for BNR exchange rates when API returns no new data."""

from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging
try:
    from database.models import DatabaseManager, ExchangeRate
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

logger = logging.getLogger(__name__)

def get_last_published_rate(currency: str, db_manager: DatabaseManager) -> Optional[ExchangeRate]:
    """Get the most recent exchange rate for a currency from the database."""
    try:
        rates = db_manager.get_rates_by_currency(currency)
        if rates:
            # Get the most recent rate (last in chronological order)
            last_rate = rates[-1]
            logger.info(f"Found last published rate for {currency}: {last_rate.rate} from {last_rate.timestamp}")
            return last_rate
        return None
    except Exception as e:
        logger.error(f"Error retrieving last published rate: {e}")
        return None

def apply_fallback_if_needed(rates: Dict[str, Optional[float]], db_manager: DatabaseManager, supported_currencies: List[str], max_age_days: int = 3) -> Dict[str, Optional[float]]:
    """
    Apply fallback logic: if BNR API returns no data, use the last published rate.
    
    Args:
        rates: Dictionary of fetched rates (may be empty or incomplete). Values are Optional[float].
        db_manager: Database manager instance
        supported_currencies: List of supported currency codes to process
        max_age_days: Maximum age (in days) for which to accept a fallback rate
    
    Returns:
        Dictionary with rates (either from API or fallback) as Optional[float]
    """
    if not DATABASE_AVAILABLE or not db_manager:
        logger.warning("Database not available, cannot apply fallback")
        return rates
    
    fallback_applied = False
    now = datetime.now()
    max_age = timedelta(days=max_age_days)
    
    # Check each currency
    for currency in supported_currencies:
        if currency in rates and rates[currency] is not None:
            # We have a rate, check if it's recent
            last_rate = get_last_published_rate(currency, db_manager)
            if last_rate:
                rate_age = now - last_rate.timestamp
                if rate_age > max_age:
                    # Rate is too old, try to fetch from API (already done above)
                    logger.info(f"Rate for {currency} is older than {max_age_days} days, keeping API rate")
            continue
        
        # No rate from API, try fallback
        logger.info(f"No rate from API for {currency}, attempting fallback...")
        last_rate = get_last_published_rate(currency, db_manager)
        
        if last_rate:
            rate_age = now - last_rate.timestamp
            if rate_age <= max_age:
                rates[currency] = last_rate.rate
                logger.info(f"Applied fallback for {currency}: using rate {last_rate.rate} from {last_rate.timestamp}")
                fallback_applied = True
                
                # Save the fallback rate to database with today's date
                try:
                    from database.models import ExchangeRate
                    fallback_rate = ExchangeRate(
                        id=None,
                        currency=currency,
                        rate=last_rate.rate,
                        source='BNR (Fallback)',
                        timestamp=now,
                        multiplier=1,
                        is_valid=True
                    )
                    db_manager.save_exchange_rates([fallback_rate])
                    logger.info(f"Saved fallback rate for {currency} to database")
                except Exception as e:
                    logger.warning(f"Failed to save fallback rate to database: {e}")
            else:
                logger.warning(f"Last rate for {currency} is too old ({rate_age.days} days), not applying fallback")
        else:
            logger.warning(f"No fallback available for {currency}")
    
    if fallback_applied:
        logger.info("Fallback rates applied successfully")
    
    return rates

