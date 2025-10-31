"""
Configuration module for BNR Exchange Rate Monitor.
Centralizes all configuration settings with environment variable support.
"""
import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class Config:
    """Application configuration with environment variable support."""
    
    # API Configuration
    BNR_API_URL: str = os.getenv('BNR_API_URL', 'https://www.bnr.ro/nbrfxrates.xml')
    REQUEST_TIMEOUT: int = int(os.getenv('REQUEST_TIMEOUT', '30'))
    MAX_RETRIES: int = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_BACKOFF_FACTOR: float = float(os.getenv('RETRY_BACKOFF_FACTOR', '0.3'))
    
    # Currency Configuration
    SUPPORTED_CURRENCIES: List[str] = field(default_factory=lambda: os.getenv('CURRENCIES', 'EUR,USD,GBP').split(','))
    
    # Database Configuration
    DB_PATH: str = os.getenv('DB_PATH', 'data/exchange_rates.db')
    
    # Flask Configuration
    FLASK_HOST: str = os.getenv('FLASK_HOST', '0.0.0.0')
    FLASK_PORT: int = int(os.getenv('PORT', '5000'))
    FLASK_DEBUG: bool = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Monitoring Configuration
    METRICS_DIR: str = os.getenv('METRICS_DIR', 'metrics')
    
    # Rate Validation Configuration
    MIN_RATE: float = float(os.getenv('MIN_RATE', '0.1'))
    MAX_RATE: float = float(os.getenv('MAX_RATE', '100.0'))
    
    # Fallback Configuration
    FALLBACK_MAX_AGE_DAYS: int = int(os.getenv('FALLBACK_MAX_AGE_DAYS', '3'))
    
    # Rate Change Detection Configuration
    RATE_CHANGE_THRESHOLD_PERCENT: float = float(os.getenv('RATE_CHANGE_THRESHOLD_PERCENT', '2.0'))
    
    # Data Cleanup Configuration
    CLEANUP_OLD_DATA_DAYS: int = int(os.getenv('CLEANUP_OLD_DATA_DAYS', '90'))
    
    # News API Configuration
    NEWSAPI_KEY: str = os.getenv('NEWSAPI_KEY', '')
    GUARDIAN_KEY: str = os.getenv('GUARDIAN_KEY', '')


# Global config instance
config = Config()

