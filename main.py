import os
import requests
import xml.etree.ElementTree as ET
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import logging
import re
import time
from typing import Optional, Dict, List
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

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

def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

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

def send_email(subject: str, body: str, to_email: str) -> bool:
    """Securely send email with validation and error handling."""
    try:
        # Validate email addresses
        from_email = os.environ.get('EMAIL_SENDER')
        app_password = os.environ.get('EMAIL_PASS')
        
        if not from_email or not app_password:
            logger.error("Email credentials not found in environment variables")
            return False
            
        if not validate_email(from_email):
            logger.error(f"Invalid sender email format: {from_email}")
            return False
            
        if not validate_email(to_email):
            logger.error(f"Invalid recipient email format: {to_email}")
            return False
        
        # Sanitize subject and body
        subject = subject.strip()[:100]  # Limit subject length
        body = body.strip()
        
        if not subject or not body:
            logger.error("Empty subject or body")
            return False
        
        # Create secure email message
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
        
        # Send email with secure connection
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30) as smtp:
            smtp.login(from_email, app_password)
            smtp.send_message(msg)
            
        logger.info(f"Email sent successfully to {to_email}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication failed: {e}")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending email: {e}")
        return False

def job() -> bool:
    """Main job function with comprehensive error handling and security."""
    try:
        logger.info("Starting BNR exchange rate job")
        
        # Validate environment variables
        recipient_email = os.environ.get('EMAIL_RECIPIENT')
        if not recipient_email or not validate_email(recipient_email):
            logger.error("Invalid or missing EMAIL_RECIPIENT environment variable")
            return False
        
        # Fetch exchange rates securely
        rates = {}
        for currency in SUPPORTED_CURRENCIES:
            rate = get_bnr_api_rate(currency)
            rates[currency] = rate
            if rate:
                logger.info(f"Retrieved {currency} rate: {rate}")
            else:
                logger.warning(f"Failed to retrieve {currency} rate")
        
        # Format email body securely
        today = datetime.now().strftime("%d.%m.%Y")
        body_lines = [f"Curs BNR - {today}", ""]
        
        for currency, rate in rates.items():
            if rate:
                body_lines.append(f"{currency}: {rate}")
            else:
                body_lines.append(f"{currency}: Curs indisponibil")
        
        body = "\n".join(body_lines)
        
        # Log summary (without sensitive data)
        successful_rates = sum(1 for rate in rates.values() if rate)
        logger.info(f"Retrieved {successful_rates}/{len(SUPPORTED_CURRENCIES)} exchange rates")
        
        # Send email
        subject = f"Curs BNR {today}"
        email_sent = send_email(subject, body, recipient_email)
        
        if email_sent:
            logger.info("Job completed successfully")
            return True
        else:
            logger.error("Job failed - email not sent")
            return False
            
    except Exception as e:
        logger.error(f"Job failed with unexpected error: {e}")
        return False

if __name__ == "__main__":
    try:
        success = job()
        exit_code = 0 if success else 1
        logger.info(f"Script completed with exit code: {exit_code}")
        exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        exit(130)
    except Exception as e:
        logger.error(f"Script failed with critical error: {e}")
        exit(1)
