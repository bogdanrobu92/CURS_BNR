# GitHub Pages Deployment Guide

This guide explains how to deploy the BNR Exchange Rate Monitor to GitHub Pages.

## 🚀 **Deployment Architecture**

### **Frontend (GitHub Pages)**
- **URL**: `https://bogdanrobu92.github.io/CURS_BNR`
- **Location**: `docs/index.html`
- **Updates**: Automatic on push to main branch

### **Backend (GitHub Actions)**
- **API Data**: `api/` directory
- **Schedule**: Every 6 hours
- **Trigger**: On code changes

## 📁 **File Structure**

```
CURS_BNR/
├── docs/
│   └── index.html          # Frontend dashboard
├── api/
│   ├── proxy.js            # API proxy for GitHub Pages
│   ├── rates-latest.json   # Latest exchange rates
│   ├── rates-history.json  # Historical data
│   ├── rates-trends.json   # Trend analysis
│   ├── rates-statistics.json # Statistics
│   ├── sources-status.json # Data source status
│   ├── health.json         # System health
│   ├── system-info.json    # System information
│   └── export-data.json    # Complete data export
├── .github/workflows/
│   ├── pages.yml           # GitHub Pages deployment
│   └── api-server.yml      # API data collection
└── .nojekyll              # Disable Jekyll processing
```

## 🔧 **Setup Instructions**

### **1. Enable GitHub Pages**

1. Go to your repository settings
2. Navigate to "Pages" section
3. Set source to "GitHub Actions"
4. Save the configuration

### **2. Configure Secrets (Optional)**

For email functionality, add these secrets in repository settings:

- `EMAIL_SENDER`: Your email address
- `EMAIL_PASS`: Your email password/app password
- `EMAIL_RECIPIENT`: Recipient email address

### **3. Deploy**

The deployment happens automatically when you push to the main branch:

```bash
git add .
git commit -m "Deploy to GitHub Pages"
git push origin main
```

## 🌐 **Access Your Dashboard**

Once deployed, your dashboard will be available at:

- **Main Dashboard**: `https://bogdanrobu92.github.io/CURS_BNR`
- **API Data**: `https://bogdanrobu92.github.io/CURS_BNR/api/`

## 📊 **Features Available**

### **Frontend Dashboard**
- Real-time exchange rates
- Interactive charts and trends
- System health monitoring
- Data source status
- Statistics and analytics
- Data export capabilities

### **API Endpoints**
- `/api/rates-latest.json` - Latest rates
- `/api/rates-history.json` - Historical data
- `/api/rates-trends.json` - Trend analysis
- `/api/rates-statistics.json` - Statistics
- `/api/sources-status.json` - Source status
- `/api/health.json` - Health status
- `/api/export-data.json` - Complete export

## 🔄 **Update Schedule**

- **API Data**: Every 6 hours via GitHub Actions
- **Frontend**: On every push to main branch
- **Manual**: Trigger workflow manually if needed

## 🛠️ **Troubleshooting**

### **Common Issues**

1. **Dashboard not loading**
   - Check if GitHub Pages is enabled
   - Verify the workflow completed successfully
   - Check browser console for errors

2. **API data not updating**
   - Check GitHub Actions workflow status
   - Verify API data files exist in `api/` directory
   - Check for CORS issues in browser console

3. **Charts not displaying**
   - Ensure Chart.js is loading
   - Check for JavaScript errors
   - Verify API data format

### **Debug Steps**

1. Check GitHub Actions logs
2. Verify API data files are present
3. Test API endpoints directly
4. Check browser developer tools

## 📈 **Monitoring**

- **GitHub Actions**: Check workflow status
- **GitHub Pages**: Monitor deployment status
- **API Data**: Verify files are updated regularly
- **Dashboard**: Test functionality manually

## 🔒 **Security Notes**

- API data is publicly accessible
- No sensitive data in frontend
- Email credentials stored as secrets
- Database runs in GitHub Actions (ephemeral)

## 🎯 **Next Steps**

1. **Custom Domain**: Configure custom domain in GitHub Pages settings
2. **CDN**: Add CloudFlare or similar for better performance
3. **Monitoring**: Set up uptime monitoring
4. **Backup**: Regular database backups
5. **Scaling**: Consider external database for production use

## 📞 **Support**

For issues or questions:
- Check GitHub Actions logs
- Review this documentation
- Test API endpoints manually
- Check browser console for errors
