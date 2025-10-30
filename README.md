# BNR Exchange Rate Monitor

A secure, enterprise-grade application that monitors Romanian National Bank (BNR) exchange rates and sends daily email reports.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GitHub        │    │   BNR API       │    │   Gmail SMTP    │
│   Actions       │───▶│   (XML Feed)    │───▶│   (Email)       │
│   (Scheduler)   │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BNR Exchange Rate Monitor                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Validation  │  │   Retry     │  │   Logging   │            │
│  │ & Security  │  │   Logic     │  │  & Alerts   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Features

### Core Functionality
- **Real-time Exchange Rates**: Fetches EUR, USD, GBP rates from BNR
- **Automated Scheduling**: Daily execution via GitHub Actions
- **Email Notifications**: Formatted daily reports via Gmail SMTP
- **Multi-currency Support**: Extensible currency configuration

### Security & Quality
- **Input Validation**: Comprehensive validation for all inputs
- **SSL/TLS Security**: Encrypted connections with certificate verification
- **Error Handling**: Graceful degradation and comprehensive logging
- **Dependency Security**: Pinned versions with vulnerability scanning
- **Code Quality**: Type hints, linting, and automated testing

### Testing & Monitoring
- **Unit Tests**: 100% coverage of business logic
- **Integration Tests**: End-to-end workflow testing
- **Performance Tests**: Load testing and benchmarking
- **Security Scanning**: Automated vulnerability detection
- **CI/CD Pipeline**: Automated testing and deployment

## 📋 Requirements

### System Requirements
- Python 3.9+ (tested on 3.9, 3.10, 3.11)
- Internet connection for API access
- Gmail account with App Password

### Dependencies
See `requirements.txt` for complete dependency list.

## 🛠️ Installation

### 1. Clone Repository
```bash
git clone https://github.com/bogdanrobu92/CURS_BNR.git
cd CURS_BNR
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
Set the following environment variables:
```bash
export EMAIL_SENDER="your-email@gmail.com"
export EMAIL_PASS="your-app-password"
export EMAIL_RECIPIENT="recipient@example.com"
```

### 4. Run Tests
```bash
# Run all tests
python run_tests.py --mode all

# Run specific test types
python run_tests.py --mode unit
python run_tests.py --mode integration
python run_tests.py --mode performance
```

## 🔧 Usage

### Manual Execution
```bash
python main.py
```

### Automated Execution
The application runs automatically via GitHub Actions:
- **Schedule**: Daily at 13:30 Romania time (10:30 UTC)
- **Manual**: Trigger via GitHub Actions UI
- **Push/PR**: Runs tests on code changes

### Configuration
Edit `main.py` to modify:
- Supported currencies (`SUPPORTED_CURRENCIES`)
- API timeout (`REQUEST_TIMEOUT`)
- Retry settings (`MAX_RETRIES`, `RETRY_BACKOFF_FACTOR`)

## 📊 API Reference

### Core Functions

#### `get_bnr_api_rate(currency: str) -> Optional[float]`
Fetches exchange rate for specified currency from BNR API.

**Parameters:**
- `currency` (str): 3-letter currency code (EUR, USD, GBP)

**Returns:**
- `Optional[float]`: Exchange rate as float, or None if not found

**Raises:**
- No exceptions (graceful error handling)

#### `send_email(subject: str, body: str, to_email: str) -> bool`
Sends email notification via Gmail SMTP.

**Parameters:**
- `subject` (str): Email subject (max 100 chars)
- `body` (str): Email body content
- `to_email` (str): Recipient email address

**Returns:**
- `bool`: True if email sent successfully, False otherwise

#### `job() -> bool`
Main job function that orchestrates the entire process.

**Returns:**
- `bool`: True if job completed successfully, False otherwise

### Configuration Constants

```python
BNR_API_URL = 'https://www.bnr.ro/nbrfxrates.xml'
SUPPORTED_CURRENCIES = ['EUR', 'USD', 'GBP']
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 0.3
```

## 🧪 Testing

### Test Structure
```
tests/
├── unit/                    # Unit tests
│   ├── test_validation.py
│   ├── test_api_functions.py
│   └── test_email_functions.py
├── integration/             # Integration tests
│   └── test_job_integration.py
├── performance/             # Performance tests
│   └── test_performance.py
└── conftest.py             # Shared fixtures
```

### Running Tests
```bash
# All tests with coverage
python run_tests.py --mode all --coverage --html

# Specific test types
python run_tests.py --mode unit
python run_tests.py --mode integration
python run_tests.py --mode performance

# CI mode (full reporting)
python run_tests.py --mode ci
```

### Test Coverage
- **Target**: 80% minimum coverage
- **Current**: 100% for core functions
- **Reports**: HTML, XML, and terminal output

## 🔒 Security

### Security Features
- **Input Validation**: All inputs validated and sanitized
- **SSL/TLS**: Encrypted connections with certificate verification
- **Error Handling**: No sensitive data in logs
- **Dependency Security**: Pinned versions with vulnerability scanning
- **Environment Variables**: Secure credential management

### Security Scanning
```bash
# Run security scans
bandit -r . -f json -o bandit-report.json
safety check --json --output safety-report.json
```

## 📈 Monitoring & Logging

### Log Levels
- **INFO**: Normal operations and successful actions
- **WARNING**: Non-critical issues (e.g., currency not found)
- **ERROR**: Critical failures requiring attention

### Monitoring
- **GitHub Actions**: Automated execution monitoring
- **Test Results**: Automated test reporting
- **Security Reports**: Vulnerability scanning results
- **Coverage Reports**: Code coverage metrics

## 🚀 Deployment

### GitHub Actions
The application is deployed via GitHub Actions with:
- **Multi-version testing**: Python 3.9, 3.10, 3.11
- **Security scanning**: Bandit and Safety
- **Code quality**: Flake8, MyPy, Black
- **Test coverage**: Comprehensive reporting

### Environment Setup
1. Fork the repository
2. Set up GitHub Secrets:
   - `EMAIL_SENDER`: Your Gmail address
   - `EMAIL_PASS`: Gmail App Password
   - `EMAIL_RECIPIENT`: Recipient email address
3. Enable GitHub Actions

## 📚 Documentation

- **API Documentation**: See code docstrings
- **Security Guide**: See `SECURITY.md`
- **Test Documentation**: See test files
- **Deployment Guide**: See GitHub Actions workflow

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Install development dependencies
4. Run tests: `python run_tests.py --mode all`
5. Submit a pull request

### Code Quality
- Follow PEP 8 style guidelines
- Add type hints to all functions
- Write tests for new features
- Update documentation

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### Troubleshooting
1. Check GitHub Actions logs for execution issues
2. Verify environment variables are set correctly
3. Ensure Gmail App Password is valid
4. Check BNR API availability

### Common Issues
- **Authentication Error**: Verify Gmail App Password
- **API Timeout**: Check internet connection and BNR API status
- **Test Failures**: Run tests locally to debug

## 📊 Metrics

### Performance Targets
- **API Response Time**: < 30 seconds
- **Job Execution Time**: < 5 minutes
- **Memory Usage**: < 50MB
- **Test Coverage**: > 80%

### Reliability
- **Uptime**: 99.9% (GitHub Actions dependent)
- **Error Rate**: < 1%
- **Recovery Time**: < 5 minutes

---

**Version**: 2.0.0  
**Last Updated**: 2024-01-15  
**Maintainer**: Bogdan Robu
