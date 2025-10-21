# Technical Specification - BNR Exchange Rate Monitor

## Document Information
- **Version**: 2.0.0
- **Date**: 2024-01-15
- **Author**: Bogdan Robu
- **Status**: Production Ready

## 1. System Overview

### 1.1 Purpose
The BNR Exchange Rate Monitor is an automated system that fetches daily exchange rates from the Romanian National Bank (BNR) and sends formatted email notifications to specified recipients.

### 1.2 Scope
- Real-time exchange rate monitoring for EUR, USD, GBP
- Automated daily email reporting
- Secure, enterprise-grade implementation
- Comprehensive testing and monitoring

### 1.3 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    BNR Exchange Rate Monitor                   │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Input     │  │  Processing │  │   Output    │            │
│  │ Validation  │  │   Engine    │  │  Generation │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│           │               │               │                    │
│           ▼               ▼               ▼                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Security  │  │   Retry     │  │   Email     │            │
│  │   Layer     │  │   Logic     │  │   Delivery  │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

## 2. Functional Requirements

### 2.1 Core Functions

#### 2.1.1 Exchange Rate Fetching
- **Function**: `get_bnr_api_rate(currency: str) -> Optional[str]`
- **Input**: 3-letter currency code (EUR, USD, GBP)
- **Output**: Exchange rate as string or None
- **Error Handling**: Graceful degradation on API failures

#### 2.1.2 Email Notification
- **Function**: `send_email(subject: str, body: str, to_email: str) -> bool`
- **Input**: Subject, body, recipient email
- **Output**: Success/failure boolean
- **Security**: Gmail SMTP with App Password authentication

#### 2.1.3 Job Orchestration
- **Function**: `job() -> bool`
- **Process**: Fetch rates → Format email → Send notification
- **Output**: Success/failure status
- **Logging**: Comprehensive operation logging

### 2.2 Data Flow

1. **Trigger**: GitHub Actions scheduler (daily at 13:30 Romania time)
2. **Validation**: Environment variables and input validation
3. **API Call**: Secure HTTP request to BNR API
4. **Processing**: XML parsing and rate extraction
5. **Formatting**: Email body generation
6. **Delivery**: SMTP email sending
7. **Logging**: Operation status and error reporting

## 3. Non-Functional Requirements

### 3.1 Performance Requirements
- **API Response Time**: < 30 seconds
- **Job Execution Time**: < 5 minutes
- **Memory Usage**: < 50MB
- **Concurrent Requests**: Support up to 10 simultaneous requests

### 3.2 Reliability Requirements
- **Uptime**: 99.9% (GitHub Actions dependent)
- **Error Rate**: < 1%
- **Recovery Time**: < 5 minutes
- **Data Integrity**: 100% accuracy in rate transmission

### 3.3 Security Requirements
- **Authentication**: Gmail App Password authentication
- **Encryption**: TLS 1.2+ for all network communications
- **Input Validation**: Comprehensive validation and sanitization
- **Error Handling**: No sensitive data exposure in logs
- **Dependency Security**: Pinned versions with vulnerability scanning

### 3.4 Maintainability Requirements
- **Code Coverage**: > 80%
- **Documentation**: Comprehensive API and user documentation
- **Testing**: Unit, integration, and performance tests
- **Code Quality**: Type hints, linting, and formatting

## 4. Technical Architecture

### 4.1 Technology Stack
- **Language**: Python 3.9+
- **HTTP Client**: Requests with urllib3
- **Email**: SMTP with MIME
- **Testing**: Pytest with coverage
- **CI/CD**: GitHub Actions
- **Monitoring**: Built-in logging

### 4.2 Dependencies

#### Core Dependencies
```python
requests>=2.31.0,<3.0.0
urllib3>=2.0.0,<3.0.0
certifi>=2023.7.22
charset-normalizer>=3.3.0
idna>=3.4
```

#### Testing Dependencies
```python
pytest>=7.4.0,<8.0.0
pytest-cov>=4.1.0,<5.0.0
pytest-mock>=3.11.0,<4.0.0
pytest-xdist>=3.3.0,<4.0.0
pytest-benchmark>=4.0.0,<5.0.0
```

#### Quality Dependencies
```python
black>=23.7.0,<24.0.0
flake8>=6.0.0,<7.0.0
mypy>=1.5.0,<2.0.0
```

### 4.3 Configuration

#### Environment Variables
```bash
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASS=your-app-password
EMAIL_RECIPIENT=recipient@example.com
```

#### Application Constants
```python
BNR_API_URL = 'https://www.bnr.ro/nbrfxrates.xml'
SUPPORTED_CURRENCIES = ['EUR', 'USD', 'GBP']
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 0.3
```

## 5. API Specification

### 5.1 BNR API Integration

#### Endpoint
- **URL**: `https://www.bnr.ro/nbrfxrates.xml`
- **Method**: GET
- **Format**: XML
- **Authentication**: None required
- **Rate Limiting**: Not specified

#### Response Format
```xml
<?xml version="1.0" encoding="UTF-8"?>
<DataSet xmlns="http://www.bnr.ro/xsd">
    <Body>
        <Cube date="2024-01-15">
            <Rate currency="EUR" multiplier="1">4.9500</Rate>
            <Rate currency="USD" multiplier="1">4.5500</Rate>
            <Rate currency="GBP" multiplier="1">5.7500</Rate>
        </Cube>
    </Body>
</DataSet>
```

### 5.2 Email API

#### SMTP Configuration
- **Server**: smtp.gmail.com
- **Port**: 465 (SSL)
- **Authentication**: Gmail App Password
- **Security**: TLS 1.2+

#### Email Format
```
Subject: Curs BNR 15.01.2024
From: your-email@gmail.com
To: recipient@example.com
Date: Mon, 15 Jan 2024 13:30:00 +0200

Curs BNR - 15.01.2024

EUR: 4.9500
USD: 4.5500
GBP: 5.7500
```

## 6. Error Handling

### 6.1 Error Categories

#### Network Errors
- **API Timeout**: Retry with exponential backoff
- **Connection Error**: Log and return None
- **HTTP Error**: Log status code and return None

#### Data Errors
- **Invalid XML**: Log parsing error and return None
- **Missing Currency**: Log warning and return None
- **Invalid Rate**: Log warning and return None

#### Email Errors
- **Authentication Error**: Log and return False
- **SMTP Error**: Log and return False
- **Invalid Email**: Validate and return False

### 6.2 Error Recovery
- **Retry Logic**: 3 attempts with exponential backoff
- **Graceful Degradation**: Continue with available data
- **Comprehensive Logging**: All errors logged with context
- **Status Reporting**: Clear success/failure indicators

## 7. Testing Strategy

### 7.1 Test Types

#### Unit Tests
- **Coverage**: 100% of business logic
- **Scope**: Individual functions and methods
- **Tools**: Pytest with mocking
- **Location**: `tests/unit/`

#### Integration Tests
- **Coverage**: End-to-end workflows
- **Scope**: Complete job execution
- **Tools**: Pytest with service mocking
- **Location**: `tests/integration/`

#### Performance Tests
- **Coverage**: Response times and resource usage
- **Scope**: Load testing and benchmarking
- **Tools**: Pytest-benchmark and psutil
- **Location**: `tests/performance/`

### 7.2 Test Execution
```bash
# All tests
python run_tests.py --mode all

# Specific types
python run_tests.py --mode unit
python run_tests.py --mode integration
python run_tests.py --mode performance

# CI mode
python run_tests.py --mode ci
```

## 8. Deployment

### 8.1 GitHub Actions Workflow

#### Triggers
- **Schedule**: Daily at 13:30 Romania time
- **Manual**: Workflow dispatch
- **Push/PR**: On code changes

#### Jobs
1. **Test**: Multi-version testing (Python 3.9, 3.10, 3.11)
2. **Security Scan**: Bandit and Safety vulnerability scanning
3. **Run Script**: Production execution (scheduled only)

#### Artifacts
- Test results and coverage reports
- Security scan reports
- Error logs (on failure)

### 8.2 Environment Setup

#### GitHub Secrets
- `EMAIL_SENDER`: Gmail sender address
- `EMAIL_PASS`: Gmail App Password
- `EMAIL_RECIPIENT`: Recipient email address

#### Repository Settings
- Actions enabled
- Branch protection rules
- Required status checks

## 9. Monitoring and Logging

### 9.1 Logging Configuration
```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

### 9.2 Log Levels
- **INFO**: Normal operations and successful actions
- **WARNING**: Non-critical issues (e.g., currency not found)
- **ERROR**: Critical failures requiring attention

### 9.3 Monitoring Points
- **API Response Times**: Tracked and logged
- **Job Execution Status**: Success/failure reporting
- **Error Rates**: Categorized error tracking
- **Resource Usage**: Memory and CPU monitoring

## 10. Security Considerations

### 10.1 Data Security
- **No Sensitive Data**: Credentials stored in environment variables
- **Input Validation**: All inputs validated and sanitized
- **Output Sanitization**: Email content properly formatted

### 10.2 Network Security
- **TLS Encryption**: All network communications encrypted
- **Certificate Verification**: SSL certificates validated
- **Secure Headers**: Appropriate HTTP headers set

### 10.3 Code Security
- **Dependency Scanning**: Regular vulnerability checks
- **Code Analysis**: Static analysis with Bandit
- **Input Validation**: Comprehensive input checking

## 11. Maintenance and Support

### 11.1 Regular Maintenance
- **Dependency Updates**: Monthly security updates
- **Code Quality**: Continuous improvement
- **Documentation**: Regular updates

### 11.2 Troubleshooting
- **Log Analysis**: Comprehensive error logging
- **Test Execution**: Automated testing for debugging
- **Performance Monitoring**: Resource usage tracking

### 11.3 Support Procedures
1. Check GitHub Actions logs
2. Verify environment variables
3. Run local tests
4. Check BNR API status
5. Verify Gmail credentials

## 12. Future Enhancements

### 12.1 Planned Features
- **Additional Currencies**: Support for more currencies
- **Multiple Recipients**: Support for multiple email recipients
- **Backup Data Sources**: Alternative rate providers
- **Web Dashboard**: Real-time monitoring interface

### 12.2 Technical Improvements
- **Database Storage**: Historical rate storage
- **API Rate Limiting**: Intelligent rate limiting
- **Health Checks**: Automated health monitoring
- **Metrics Collection**: Detailed performance metrics

---

**Document Status**: Approved  
**Next Review**: 2024-04-15  
**Version Control**: Git tracked
