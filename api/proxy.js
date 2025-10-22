// Simple API proxy for GitHub Pages
// This allows the frontend to access API data files

const API_BASE_URL = 'https://raw.githubusercontent.com/bogdanrobu92/CURS_BNR/main/api';

// CORS proxy function
async function fetchWithCORS(url) {
    try {
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API fetch error:', error);
        throw error;
    }
}

// API endpoints
const API = {
    // Get latest rates
    async getLatestRates() {
        return await fetchWithCORS(`${API_BASE_URL}/rates-latest.json`);
    },
    
    // Get rate history
    async getRateHistory(days = 30) {
        return await fetchWithCORS(`${API_BASE_URL}/rates-history.json`);
    },
    
    // Get rate trends
    async getRateTrends(currency = 'EUR', days = 7) {
        return await fetchWithCORS(`${API_BASE_URL}/rates-trends.json`);
    },
    
    // Get statistics
    async getStatistics(currency = 'EUR', days = 30) {
        return await fetchWithCORS(`${API_BASE_URL}/rates-statistics.json`);
    },
    
    // Get sources status
    async getSourcesStatus() {
        return await fetchWithCORS(`${API_BASE_URL}/sources-status.json`);
    },
    
    // Get health status
    async getHealthStatus() {
        return await fetchWithCORS(`${API_BASE_URL}/health.json`);
    },
    
    // Get system info
    async getSystemInfo() {
        return await fetchWithCORS(`${API_BASE_URL}/system-info.json`);
    },
    
    // Export data
    async exportData(format = 'json', days = 30) {
        return await fetchWithCORS(`${API_BASE_URL}/export-data.json`);
    }
};

// Make API available globally
window.BNR_API = API;
