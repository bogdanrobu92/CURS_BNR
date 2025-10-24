// API endpoints for chart data
// This will serve real data from your database

const API_BASE = 'https://raw.githubusercontent.com/bogdanrobu92/CURS_BNR/main/api';

// Fetch real chart data from your API
async function fetchRealChartData(period, currencies = ['EUR', 'USD', 'GBP']) {
    try {
        const response = await fetch(`${API_BASE}/chart-data.json?period=${period}&currencies=${currencies.join(',')}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching real chart data:', error);
        return null;
    }
}

// Fetch latest rates
async function fetchLatestRates() {
    try {
        const response = await fetch(`${API_BASE}/rates-latest.json`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching latest rates:', error);
        return null;
    }
}

// Export functions for use in main chart
window.ChartAPI = {
    fetchRealChartData,
    fetchLatestRates
};
