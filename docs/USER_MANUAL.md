# User Manual - BNR Exchange Rate Monitor

## Table of Contents
1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Configuration](#configuration)
4. [Usage](#usage)
5. [Troubleshooting](#troubleshooting)
6. [FAQ](#faq)

## Introduction

The BNR Exchange Rate Monitor is an automated system that fetches daily exchange rates from the Romanian National Bank (BNR) and sends formatted email notifications. This system is designed for individuals and businesses who need regular updates on EUR, USD, and GBP exchange rates.

### What This System Does
- **Fetches Exchange Rates**: Automatically retrieves current exchange rates for EUR, USD, and GBP from BNR
- **Sends Daily Emails**: Delivers formatted daily reports via email
- **Runs Automatically**: Executes daily at 13:30 Romania time without manual intervention
- **Handles Errors Gracefully**: Continues operation even if some rates are unavailable

### Key Benefits
- **Automated**: No manual intervention required
- **Reliable**: Built with enterprise-grade error handling
- **Secure**: Uses industry-standard security practices
- **Transparent**: Comprehensive logging and monitoring

## Getting Started

### Prerequisites

Before setting up the BNR Exchange Rate Monitor, ensure you have:

1. **Gmail Account**: A Gmail account for sending emails
2. **App Password**: Gmail App Password (not your regular password)
3. **Recipient Email**: Email address where you want to receive daily reports
4. **GitHub Account**: For hosting and running the automated system

### Step 1: Fork the Repository

1. Go to [https://github.com/bogdanrobu92/CURS_BNR](https://github.com/bogdanrobu92/CURS_BNR)
2. Click the "Fork" button to create your own copy
3. Clone your forked repository to your local machine

### Step 2: Set Up Gmail App Password

1. **Enable 2-Factor Authentication** on your Gmail account
2. Go to [Google Account Settings](https://myaccount.google.com/)
3. Navigate to **Security** → **2-Step Verification** → **App passwords**
4. Generate a new App Password for "Mail"
5. **Save this password** - you'll need it for configuration

### Step 3: Configure GitHub Secrets

1. Go to your forked repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Add the following secrets:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `EMAIL_SENDER` | your-email@gmail.com | Your Gmail address |
| `EMAIL_PASS` | your-app-password | Gmail App Password (16 characters) |
| `EMAIL_RECIPIENT` | recipient@example.com | Where to send daily reports |

### Step 4: Enable GitHub Actions

1. In your repository, go to **Actions** tab
2. Click **I understand my workflows, go ahead and enable them**
3. The system will now run automatically

## Configuration

### Environment Variables

The system uses three environment variables for configuration:

```bash
EMAIL_SENDER=your-email@gmail.com    # Your Gmail address
EMAIL_PASS=your-app-password         # Gmail App Password
EMAIL_RECIPIENT=recipient@example.com # Recipient email address
```

### Supported Currencies

The system currently monitors these currencies:
- **EUR** (Euro)
- **USD** (US Dollar)
- **GBP** (British Pound)

### Scheduling

The system runs automatically:
- **Daily at 13:30 Romania time** (10:30 UTC)
- **Manual trigger** available via GitHub Actions
- **On code changes** (for testing)

## Usage

### Automatic Operation

Once configured, the system operates automatically:

1. **Daily at 13:30 Romania time**, GitHub Actions triggers the job
2. **System fetches** current exchange rates from BNR
3. **Email is sent** with formatted daily report
4. **Logs are generated** for monitoring and troubleshooting

### Manual Execution

You can also run the system manually:

1. Go to your repository's **Actions** tab
2. Select **Daily BNR Email** workflow
3. Click **Run workflow**
4. Click **Run workflow** button

### Email Format

Daily emails include:

```
Subject: Curs BNR 15.01.2024

Curs BNR - 15.01.2024

EUR: 4.9500
USD: 4.5500
GBP: 5.7500
```

If a rate is unavailable, it shows:
```
EUR: Curs indisponibil
```

## Troubleshooting

### Common Issues

#### 1. Email Not Received

**Symptoms**: No daily emails received
**Solutions**:
- Check spam/junk folder
- Verify `EMAIL_RECIPIENT` is correct
- Check GitHub Actions logs for errors
- Verify Gmail App Password is correct

#### 2. Authentication Error

**Symptoms**: "SMTP authentication failed" in logs
**Solutions**:
- Verify Gmail App Password is correct (16 characters)
- Ensure 2-Factor Authentication is enabled
- Check that `EMAIL_SENDER` matches your Gmail address

#### 3. API Timeout

**Symptoms**: "Request failed" or timeout errors
**Solutions**:
- Check internet connection
- Verify BNR API is accessible
- Wait and try again (temporary issue)

#### 4. No Exchange Rates

**Symptoms**: Email shows "Curs indisponibil" for all currencies
**Solutions**:
- Check BNR website for API status
- Verify API URL is accessible
- Check GitHub Actions logs for detailed errors

### Checking Logs

1. Go to your repository's **Actions** tab
2. Click on the latest workflow run
3. Click on **run-script** job
4. Review the logs for error messages

### Testing Locally

To test the system locally:

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables**:
   ```bash
   export EMAIL_SENDER="your-email@gmail.com"
   export EMAIL_PASS="your-app-password"
   export EMAIL_RECIPIENT="recipient@example.com"
   ```

3. **Run the system**:
   ```bash
   python main.py
   ```

4. **Run tests**:
   ```bash
   python run_tests.py --mode all
   ```

## FAQ

### Q: Can I add more currencies?
A: Yes, edit the `SUPPORTED_CURRENCIES` list in `main.py` and add the new currency codes.

### Q: Can I change the email schedule?
A: Yes, edit the cron expression in `.github/workflows/schedule.yml`. The current schedule is `'30 10 * * *'` (13:30 Romania time).

### Q: Can I send emails to multiple recipients?
A: Currently, the system sends to one recipient. For multiple recipients, you would need to modify the code.

### Q: What happens if BNR API is down?
A: The system will log an error and send an email with "Curs indisponibil" for unavailable rates.

### Q: How secure is this system?
A: Very secure. It uses:
- Gmail App Passwords (not your main password)
- TLS encryption for all communications
- Input validation and sanitization
- No sensitive data in logs

### Q: Can I run this on my own server?
A: Yes, you can run it on any server with Python 3.9+ and internet access. You'll need to set up your own scheduling (cron, systemd, etc.).

### Q: How much does this cost?
A: The system is free to use. It only uses:
- GitHub Actions (free for public repositories)
- Gmail SMTP (free with Gmail account)
- BNR API (free)

### Q: Can I customize the email format?
A: Yes, edit the email formatting code in the `job()` function in `main.py`.

### Q: How do I update the system?
A: The system updates automatically when you push changes to your repository. GitHub Actions will run the new version.

### Q: What if I need help?
A: Check the troubleshooting section above, review the logs, or create an issue in the repository.

## Support

### Getting Help

1. **Check this manual** for common solutions
2. **Review GitHub Actions logs** for error details
3. **Run tests locally** to verify configuration
4. **Create an issue** in the repository if problems persist

### System Status

- **GitHub Actions**: Check repository Actions tab
- **BNR API**: Check [BNR website](https://www.bnr.ro/)
- **Gmail**: Check [Gmail status](https://www.google.com/appsstatus)

### Updates

The system is regularly updated with:
- Security improvements
- Bug fixes
- New features
- Performance optimizations

---

**Last Updated**: 2024-01-15  
**Version**: 2.0.0  
**Support**: Create an issue in the repository
