# BNR Exchange Rate Monitor - Documentation

Welcome to the BNR Exchange Rate Monitor documentation site!

## 🚀 Quick Start

This is a static documentation site for the BNR Exchange Rate Monitor project. The main application runs on GitHub Actions and provides:

- **Daily Exchange Rate Monitoring**: Automated fetching of EUR, USD, GBP rates from Romanian National Bank
- **Email Notifications**: Daily formatted reports sent to specified recipients
- **API Endpoints**: RESTful API for accessing current and historical data
- **Health Monitoring**: System health checks and alerting

## 📊 Live Data

- **Current Rates**: Check the main page for real-time exchange rates
- **API Data**: Access JSON endpoints for programmatic access
- **Health Status**: Monitor system health and availability

## 🔗 Links

- **Main Application**: [GitHub Repository](https://github.com/bogdanrobu92/CURS_BNR)
- **Technical Documentation**: [Technical Specification](TECHNICAL_SPECIFICATION.md)
- **User Guide**: [User Manual](USER_MANUAL.md)

## 📈 API Endpoints

- `/api/rates-latest.json` - Latest exchange rates
- `/api/health.json` - System health status
- `/api/sources-status.json` - Data source availability

## 🛠️ Development

This documentation site is automatically deployed via GitHub Pages when changes are pushed to the main branch.

---

**Version**: 2.0.0  
**Last Updated**: $(date)  
**Maintainer**: Bogdan Robu
