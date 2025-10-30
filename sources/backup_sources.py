"""
Backup data sources for exchange rate monitoring.
Provides fallback APIs when primary BNR API is unavailable.
"""
import os
import requests
import json
import logging
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter


@dataclass
class RateSource:
    """Exchange rate source configuration."""
    name: str
    url: str
    api_key: Optional[str] = None
    timeout: int = 30
    priority: int = 1  # Lower number = higher priority


class BackupRateProvider:
    """Backup exchange rate provider with multiple sources."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.sources = self._initialize_sources()
        self.session = self._create_secure_session()
    
    def _initialize_sources(self) -> List[RateSource]:
        """Initialize available rate sources."""
        sources = [
            # Primary: BNR (Romanian National Bank)
            RateSource(
                name="BNR",
                url="https://www.bnr.ro/nbrfxrates.xml",
                priority=1
            ),
            # Backup 1: European Central Bank
            RateSource(
                name="ECB",
                url="https://api.exchangerate.host/latest?base=EUR",
                priority=2
            ),
            # Backup 2: Fixer.io (requires API key)
            RateSource(
                name="Fixer",
                url="https://api.fixer.io/latest?base=EUR",
                api_key=os.environ.get('FIXER_API_KEY'),
                priority=3
            ),
            # Backup 3: ExchangeRate-API
            RateSource(
                name="ExchangeRate-API",
                url="https://api.exchangerate-api.com/v4/latest/EUR",
                priority=4
            )
        ]
        
        # Filter out sources without API keys
        return [source for source in sources if not source.api_key or source.api_key != 'None']
    
    def _create_secure_session(self) -> requests.Session:
        """Create secure HTTP session."""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        session.headers.update({
            'User-Agent': 'BNR-Exchange-Rate-Monitor/2.0.0',
            'Accept': 'application/json, application/xml, text/xml, */*',
            'Accept-Encoding': 'gzip, deflate'
        })
        
        return session
    
    def get_rates_from_bnr(self) -> Dict[str, float]:
        """Get rates from BNR (primary source)."""
        bnr_source = next((s for s in self.sources if s.name == "BNR"), None)
        if not bnr_source:
            self.logger.error("BNR source not found")
            return {}
        
        try:
            response = self.session.get(
                bnr_source.url,
                timeout=bnr_source.timeout,
                verify=True
            )
            response.raise_for_status()
            
            import xml.etree.ElementTree as ET
            tree = ET.fromstring(response.content)
            ns = {'ns': 'http://www.bnr.ro/xsd'}
            
            rates = {}
            for rate in tree.findall('.//ns:Rate', ns):
                currency = rate.attrib.get('currency')
                rate_value = rate.text
                if currency and rate_value:
                    try:
                        rates[currency] = float(rate_value)
                    except ValueError:
                        continue
            
            self.logger.info(f"BNR: Retrieved {len(rates)} rates")
            return rates
            
        except Exception as e:
            self.logger.error(f"BNR API failed: {e}")
            return {}
    
    def get_rates_from_ecb(self) -> Dict[str, float]:
        """Get rates from European Central Bank."""
        ecb_source = next((s for s in self.sources if s.name == "ECB"), None)
        if not ecb_source:
            self.logger.error("ECB source not found")
            return {}
        
        try:
            response = self.session.get(
                ecb_source.url,
                timeout=ecb_source.timeout,
                verify=True
            )
            response.raise_for_status()
            
            data = response.json()
            rates = data.get('rates', {})
            
            # Convert to RON if available, otherwise return EUR-based rates
            ron_rate = rates.get('RON', 1.0)
            converted_rates = {}
            
            for currency, rate in rates.items():
                if currency in ['USD', 'GBP']:
                    # Convert to RON
                    converted_rates[currency] = ron_rate / rate
                elif currency == 'EUR':
                    converted_rates[currency] = ron_rate
            
            self.logger.info(f"ECB: Retrieved {len(converted_rates)} rates")
            return converted_rates
            
        except Exception as e:
            self.logger.error(f"ECB API failed: {e}")
            return {}
    
    def get_rates_from_fixer(self) -> Dict[str, float]:
        """Get rates from Fixer.io."""
        fixer_source = next((s for s in self.sources if s.name == "Fixer"), None)
        if not fixer_source:
            self.logger.warning("Fixer source not found")
            return {}
        
        if not fixer_source.api_key:
            self.logger.warning("Fixer.io API key not configured")
            return {}
        
        try:
            url = f"{fixer_source.url}&access_key={fixer_source.api_key}"
            response = self.session.get(
                url,
                timeout=fixer_source.timeout,
                verify=True
            )
            response.raise_for_status()
            
            data = response.json()
            if not data.get('success', False):
                self.logger.error(f"Fixer.io API error: {data.get('error', 'Unknown error')}")
                return {}
            
            rates = data.get('rates', {})
            ron_rate = rates.get('RON', 1.0)
            converted_rates = {}
            
            for currency, rate in rates.items():
                if currency in ['USD', 'GBP']:
                    converted_rates[currency] = ron_rate / rate
                elif currency == 'EUR':
                    converted_rates[currency] = ron_rate
            
            self.logger.info(f"Fixer: Retrieved {len(converted_rates)} rates")
            return converted_rates
            
        except Exception as e:
            self.logger.error(f"Fixer.io API failed: {e}")
            return {}
    
    def get_rates_from_exchangerate_api(self) -> Dict[str, float]:
        """Get rates from ExchangeRate-API."""
        exchangerate_source = next((s for s in self.sources if s.name == "ExchangeRate-API"), None)
        if not exchangerate_source:
            self.logger.error("ExchangeRate-API source not found")
            return {}
        
        try:
            response = self.session.get(
                exchangerate_source.url,
                timeout=exchangerate_source.timeout,
                verify=True
            )
            response.raise_for_status()
            
            data = response.json()
            rates = data.get('rates', {})
            ron_rate = rates.get('RON', 1.0)
            converted_rates = {}
            
            for currency, rate in rates.items():
                if currency in ['USD', 'GBP']:
                    converted_rates[currency] = ron_rate / rate
                elif currency == 'EUR':
                    converted_rates[currency] = ron_rate
            
            self.logger.info(f"ExchangeRate-API: Retrieved {len(converted_rates)} rates")
            return converted_rates
            
        except Exception as e:
            self.logger.error(f"ExchangeRate-API failed: {e}")
            return {}
    
    def get_rates_with_fallback(self, target_currencies: List[str] = None) -> Dict[str, Dict[str, float]]:
        """Get rates from all sources with fallback logic."""
        if target_currencies is None:
            target_currencies = ['EUR', 'USD', 'GBP']
        
        all_rates = {}
        
        # Try each source in priority order
        for source in self.sources:
            try:
                if source.name == "BNR":
                    rates = self.get_rates_from_bnr()
                elif source.name == "ECB":
                    rates = self.get_rates_from_ecb()
                elif source.name == "Fixer":
                    rates = self.get_rates_from_fixer()
                elif source.name == "ExchangeRate-API":
                    rates = self.get_rates_from_exchangerate_api()
                else:
                    continue
                
                if rates:
                    all_rates[source.name] = rates
                    self.logger.info(f"Successfully retrieved rates from {source.name}")
                
            except Exception as e:
                self.logger.error(f"Failed to get rates from {source.name}: {e}")
                continue
        
        return all_rates
    
    def get_best_rates(self, target_currencies: List[str] = None) -> Dict[str, float]:
        """Get the best available rates using fallback logic."""
        if target_currencies is None:
            target_currencies = ['EUR', 'USD', 'GBP']
        
        all_rates = self.get_rates_with_fallback(target_currencies)
        best_rates = {}
        
        for currency in target_currencies:
            best_rate = None
            best_source = None
            
            # Try sources in priority order
            for source in self.sources:
                if source.name in all_rates and currency in all_rates[source.name]:
                    rate = all_rates[source.name][currency]
                    if rate and rate > 0:  # Valid rate
                        best_rate = rate
                        best_source = source.name
                        break
            
            if best_rate:
                best_rates[currency] = best_rate
                self.logger.info(f"Best rate for {currency}: {best_rate} (from {best_source})")
            else:
                self.logger.warning(f"No valid rate found for {currency}")
        
        return best_rates
    
    def validate_rates(self, rates: Dict[str, float], tolerance: float = 0.1) -> Dict[str, bool]:
        """Validate rates against each other for consistency."""
        validation_results = {}
        
        # Basic validation
        for currency, rate in rates.items():
            if rate <= 0:
                validation_results[currency] = False
                self.logger.warning(f"Invalid rate for {currency}: {rate}")
            else:
                validation_results[currency] = True
        
        # Cross-validation between sources
        all_rates = self.get_rates_with_fallback()
        if len(all_rates) > 1:
            for currency in rates.keys():
                currency_rates = []
                for source, source_rates in all_rates.items():
                    if currency in source_rates:
                        currency_rates.append(source_rates[currency])
                
                if len(currency_rates) > 1:
                    # Check if rates are within tolerance
                    min_rate = min(currency_rates)
                    max_rate = max(currency_rates)
                    variation = (max_rate - min_rate) / min_rate
                    
                    if variation > tolerance:
                        validation_results[f"{currency}_consistency"] = False
                        self.logger.warning(f"High variation in {currency} rates: {variation:.2%}")
                    else:
                        validation_results[f"{currency}_consistency"] = True
        
        return validation_results
    
    def get_source_status(self) -> Dict[str, Dict[str, any]]:
        """Get status of all rate sources."""
        status = {}
        
        for source in self.sources:
            try:
                start_time = datetime.now()
                
                if source.name == "BNR":
                    rates = self.get_rates_from_bnr()
                elif source.name == "ECB":
                    rates = self.get_rates_from_ecb()
                elif source.name == "Fixer":
                    rates = self.get_rates_from_fixer()
                elif source.name == "ExchangeRate-API":
                    rates = self.get_rates_from_exchangerate_api()
                else:
                    continue
                
                response_time = (datetime.now() - start_time).total_seconds()
                
                status[source.name] = {
                    'available': len(rates) > 0,
                    'response_time': response_time,
                    'rates_count': len(rates),
                    'priority': source.priority,
                    'last_check': datetime.now().isoformat()
                }
                
            except Exception as e:
                status[source.name] = {
                    'available': False,
                    'error': str(e),
                    'priority': source.priority,
                    'last_check': datetime.now().isoformat()
                }
        
        return status
