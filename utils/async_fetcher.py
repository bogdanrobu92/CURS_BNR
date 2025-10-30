"""
Async support for concurrent API calls using asyncio and aiohttp.
Provides async versions of BNR API fetching functions for improved performance.
"""
import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from typing import Dict, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Cache for async calls (shared with sync version)
_ASYNC_CACHE: Dict[str, tuple] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes


async def fetch_bnr_api_rate_async(
    session: aiohttp.ClientSession,
    currency: str,
    api_url: str = 'https://www.bnr.ro/nbrfxrates.xml',
    timeout: int = 30
) -> Optional[float]:
    """Asynchronously fetch exchange rate from BNR API.
    
    Args:
        session: aiohttp ClientSession instance
        currency: Currency code (e.g., 'EUR', 'USD', 'GBP')
        api_url: BNR API URL
        timeout: Request timeout in seconds
        
    Returns:
        Exchange rate as float, or None if not found or error occurred
    """
    from main import validate_currency
    
    if not validate_currency(currency):
        logger.error(f"Invalid currency code: {currency}")
        return None
    
    # Check cache first
    cache_key = currency.upper()
    current_time = datetime.now().timestamp()
    
    if cache_key in _ASYNC_CACHE:
        cached_time, cached_rate = _ASYNC_CACHE[cache_key]
        if current_time - cached_time < _CACHE_TTL_SECONDS:
            logger.debug(f"Using cached rate for {currency}: {cached_rate}")
            return cached_rate
    
    try:
        logger.info(f"Fetching exchange rate for {currency} (async)")
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        
        async with session.get(api_url, timeout=timeout_obj, ssl=True) as response:
            response.raise_for_status()
            content = await response.read()
            
            # Parse XML safely
            try:
                tree = ET.fromstring(content)
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
                            logger.info(f"Successfully retrieved rate for {currency}: {float_rate} (async)")
                            # Update cache
                            _ASYNC_CACHE[cache_key] = (current_time, float_rate)
                            return float_rate
                        except ValueError:
                            logger.error(f"Invalid rate value for {currency}: {rate_value}")
                            return None
            
            logger.warning(f"Currency {currency} not found in API response")
            return None
            
    except asyncio.TimeoutError:
        logger.error(f"Request timeout for {currency}")
        return None
    except aiohttp.ClientError as e:
        logger.error(f"Request failed for {currency}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching rate for {currency}: {e}")
        return None


async def fetch_all_rates_async(
    currencies: List[str],
    api_url: str = 'https://www.bnr.ro/nbrfxrates.xml',
    timeout: int = 30
) -> Dict[str, Optional[float]]:
    """Fetch all exchange rates concurrently using async/await.
    
    Args:
        currencies: List of currency codes to fetch
        api_url: BNR API URL
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary mapping currency codes to exchange rates
    """
    rates: Dict[str, Optional[float]] = {}
    
    async with aiohttp.ClientSession() as session:
        # Create tasks for concurrent fetching
        tasks = [
            fetch_bnr_api_rate_async(session, currency, api_url, timeout)
            for currency in currencies
        ]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for currency, result in zip(currencies, results):
            if isinstance(result, Exception):
                logger.error(f"Error fetching {currency}: {result}")
                rates[currency] = None
            else:
                rates[currency] = result
    
    return rates


async def collect_exchange_rates_async(
    currencies: List[str],
    api_url: str = 'https://www.bnr.ro/nbrfxrates.xml',
    timeout: int = 30
) -> Dict[str, Optional[float]]:
    """Async version of collect_exchange_rates for concurrent API calls.
    
    Args:
        currencies: List of currency codes to fetch
        api_url: BNR API URL
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary mapping currency codes to exchange rates
    """
    logger.info(f"Starting async BNR exchange rate collection for {len(currencies)} currencies")
    
    rates = await fetch_all_rates_async(currencies, api_url, timeout)
    
    successful = sum(1 for rate in rates.values() if rate is not None)
    logger.info(f"Async collection complete: {successful}/{len(currencies)} rates retrieved")
    
    return rates


def run_async_collection(
    currencies: List[str],
    api_url: str = 'https://www.bnr.ro/nbrfxrates.xml',
    timeout: int = 30
) -> Dict[str, Optional[float]]:
    """Synchronous wrapper for async collection.
    
    Args:
        currencies: List of currency codes to fetch
        api_url: BNR API URL
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary mapping currency codes to exchange rates
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # No event loop running, create new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(
        collect_exchange_rates_async(currencies, api_url, timeout)
    )


if __name__ == "__main__":
    """Test async collection."""
    import sys
    
    currencies = ['EUR', 'USD', 'GBP']
    if len(sys.argv) > 1:
        currencies = sys.argv[1].split(',')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print(f"Fetching rates for: {', '.join(currencies)}")
    rates = run_async_collection(currencies)
    
    for currency, rate in rates.items():
        if rate:
            print(f"{currency}: {rate}")
        else:
            print(f"{currency}: Failed")

