#!/usr/bin/env python3
"""
Dynamic API server for BNR Exchange Rate Monitor.
Handles date range filtering and dynamic chart data generation.
"""
import os
import sys
import json
from datetime import datetime
from flask import Flask, jsonify, request
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from generate_api_data import generate_chart_data, generate_latest_rates
    from database.models import DatabaseManager
    from news_fetcher import get_news_for_date
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

# Configure structured logging
try:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.logging_config import setup_logging, get_logger
    logger = setup_logging(
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        log_file=os.getenv('LOG_FILE', 'api_server.log'),
        log_dir=os.getenv('LOG_DIR', 'logs'),
        use_json=os.getenv('LOG_FORMAT', '').lower() == 'json'
    )
    logger = get_logger(__name__)
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/api/chart-data.json')
def get_chart_data():
    """Get chart data with optional date range filtering."""
    try:
        # Get query parameters
        start_date = request.args.get('start')
        end_date = request.args.get('end')
        
        # Generate chart data with date filtering
        chart_data = generate_chart_data(
            currencies=['EUR'],
            start_date_str=start_date,
            end_date_str=end_date
        )
        
        return jsonify(chart_data)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/rates-latest.json')
def get_latest_rates():
    """Get latest exchange rates."""
    try:
        latest_rates = generate_latest_rates()
        return jsonify(latest_rates)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/news.json')
def get_news():
    """Get news articles for a specific date."""
    try:
        # Get query parameters
        date = request.args.get('date')
        region = request.args.get('region')  # 'europe' or 'romania'
        
        if not date:
            return jsonify({
                'success': False,
                'error': 'Date parameter is required',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # Fetch news for the specified date
        news_data = get_news_for_date(date, region)
        return jsonify(news_data)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/health.json')
def get_health():
    """Get system health status."""
    return jsonify({
        'success': True,
        'data': {
            'overall_status': 'healthy',
            'database_available': DATABASE_AVAILABLE,
            'checks': [
                {
                    'service': 'API Server',
                    'status': 'healthy',
                    'message': 'API server running',
                    'response_time': None,
                    'timestamp': datetime.now().isoformat()
                },
                {
                    'service': 'Database',
                    'status': 'healthy' if DATABASE_AVAILABLE else 'unavailable',
                    'message': 'Database connection available' if DATABASE_AVAILABLE else 'Database not available',
                    'response_time': None,
                    'timestamp': datetime.now().isoformat()
                }
            ]
        },
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("Starting BNR Exchange Rate API Server...")
    print("Available endpoints:")
    print("  GET /api/chart-data.json?start=2025-10-24&end=2025-12-31")
    print("  GET /api/rates-latest.json")
    print("  GET /api/health.json")
    
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    )
