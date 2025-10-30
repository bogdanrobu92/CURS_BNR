"""
Comprehensive structured logging configuration for BNR Exchange Rate Monitor.
Provides JSON formatter and rotating file handler for production-ready logging.
"""
import json
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON string representation of the log record
        """
        log_data = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data, ensure_ascii=False)


class StructuredFormatter(logging.Formatter):
    """Human-readable structured formatter for development."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record in a structured, human-readable format.
        
        Args:
            record: Log record to format
            
        Returns:
            Formatted log string
        """
        base_format = (
            f"{self.formatTime(record, self.datefmt)} - "
            f"{record.levelname:8s} - "
            f"{record.name}:{record.lineno} - "
            f"{record.funcName}() - "
            f"{record.getMessage()}"
        )
        
        if record.exc_info:
            base_format += f"\n{self.formatException(record.exc_info)}"
        
        return base_format


def setup_logging(
    log_level: str = 'INFO',
    log_file: Optional[str] = None,
    log_dir: str = 'logs',
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    use_json: bool = False
) -> logging.Logger:
    """Configure comprehensive logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file name (default: app.log)
        log_dir: Directory for log files (default: logs)
        max_bytes: Maximum log file size before rotation (default: 10MB)
        backup_count: Number of backup log files to keep (default: 5)
        use_json: Whether to use JSON formatter (default: False, uses structured format)
        
    Returns:
        Configured root logger
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Determine log file path
    if log_file is None:
        log_file = os.getenv('LOG_FILE', 'app.log')
    
    log_file_path = log_path / log_file
    
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatter
    if use_json or os.getenv('LOG_FORMAT', '').lower() == 'json':
        formatter = JSONFormatter()
    else:
        formatter = StructuredFormatter(
            fmt='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Console handler (always use structured format for readability)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = StructuredFormatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)  # File handler captures all levels
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Error log file handler (only ERROR and above)
    error_log_file = log_path / 'error.log'
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Initialize logging on module import if LOG_INIT is set
if os.getenv('LOG_INIT', '').lower() == 'true':
    setup_logging(
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        log_file=os.getenv('LOG_FILE'),
        log_dir=os.getenv('LOG_DIR', 'logs'),
        use_json=os.getenv('LOG_FORMAT', '').lower() == 'json'
    )

