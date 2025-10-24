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
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

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
    
    app.run(host='0.0.0.0', port=5000, debug=True)
