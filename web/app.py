"""
Flask web application for BNR Exchange Rate Monitor.
Provides real-time dashboard, API endpoints, and system management.
"""
import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
import psutil

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import DatabaseManager, ExchangeRate, SystemMetrics
from sources.backup_sources import BackupRateProvider
from monitoring.health_check import HealthChecker
from monitoring.metrics import MetricsCollector

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
db_manager = DatabaseManager()
rate_provider = BackupRateProvider()
health_checker = HealthChecker()
metrics_collector = MetricsCollector()


@app.route('/')
def dashboard():
    """Main dashboard page."""
    return render_template('dashboard.html')


@app.route('/api/rates/latest')
def get_latest_rates():
    """Get latest exchange rates."""
    try:
        rates = db_manager.get_latest_rates()
        
        # Group by currency and get latest
        latest_rates = {}
        for rate in rates:
            if rate.currency not in latest_rates:
                latest_rates[rate.currency] = {
                    'rate': rate.rate,
                    'source': rate.source,
                    'timestamp': rate.timestamp.isoformat(),
                    'multiplier': rate.multiplier
                }
        
        return jsonify({
            'success': True,
            'data': latest_rates,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error getting latest rates: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/rates/history')
def get_rate_history():
    """Get historical exchange rates."""
    try:
        currency = request.args.get('currency')
        days = int(request.args.get('days', 7))
        
        start_date = datetime.now() - timedelta(days=days)
        rates = db_manager.get_rates_by_date_range(start_date, datetime.now(), currency)
        
        # Group by currency and date
        history = {}
        for rate in rates:
            if rate.currency not in history:
                history[rate.currency] = []
            
            history[rate.currency].append({
                'rate': rate.rate,
                'source': rate.source,
                'timestamp': rate.timestamp.isoformat()
            })
        
        return jsonify({
            'success': True,
            'data': history,
            'period_days': days
        })
    
    except Exception as e:
        logger.error(f"Error getting rate history: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/rates/trends')
def get_rate_trends():
    """Get rate trends and analysis."""
    try:
        currency = request.args.get('currency', 'EUR')
        days = int(request.args.get('days', 7))
        
        trends = db_manager.get_rate_trends(currency, days)
        
        trend_data = []
        for trend in trends:
            trend_data.append({
                'currency': trend.currency,
                'current_rate': trend.current_rate,
                'previous_rate': trend.previous_rate,
                'change_absolute': trend.change_absolute,
                'change_percentage': trend.change_percentage,
                'trend_direction': trend.trend_direction,
                'volatility': trend.volatility,
                'timestamp': trend.timestamp.isoformat()
            })
        
        return jsonify({
            'success': True,
            'data': trend_data,
            'currency': currency,
            'period_days': days
        })
    
    except Exception as e:
        logger.error(f"Error getting rate trends: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/rates/statistics')
def get_rate_statistics():
    """Get currency statistics."""
    try:
        currency = request.args.get('currency', 'EUR')
        days = int(request.args.get('days', 30))
        
        stats = db_manager.get_currency_statistics(currency, days)
        
        return jsonify({
            'success': True,
            'data': stats,
            'currency': currency,
            'period_days': days
        })
    
    except Exception as e:
        logger.error(f"Error getting rate statistics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/sources/status')
def get_sources_status():
    """Get status of all rate sources."""
    try:
        status = rate_provider.get_source_status()
        
        return jsonify({
            'success': True,
            'data': status,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error getting sources status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/sources/refresh')
def refresh_rates():
    """Manually refresh rates from all sources."""
    try:
        # Get rates from all sources
        all_rates = rate_provider.get_rates_with_fallback()
        
        # Save to database
        saved_rates = []
        for source_name, rates in all_rates.items():
            for currency, rate in rates.items():
                exchange_rate = ExchangeRate(
                    id=None,
                    currency=currency,
                    rate=rate,
                    source=source_name,
                    timestamp=datetime.now(),
                    multiplier=1,
                    is_valid=True
                )
                rate_id = db_manager.save_exchange_rate(exchange_rate)
                saved_rates.append(rate_id)
        
        return jsonify({
            'success': True,
            'message': f'Refreshed {len(saved_rates)} rates from {len(all_rates)} sources',
            'sources': list(all_rates.keys()),
            'rates_saved': len(saved_rates)
        })
    
    except Exception as e:
        logger.error(f"Error refreshing rates: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/health')
def get_health_status():
    """Get system health status."""
    try:
        # Run health checks
        health_checks = health_checker.run_health_checks()
        health_summary = health_checker.get_health_summary()
        
        # Check for alerts
        alerts = health_checker.check_for_alerts()
        
        health_data = {
            'overall_status': health_summary['status'],
            'checks': []
        }
        
        for check in health_checks:
            health_data['checks'].append({
                'service': check.service,
                'status': check.status,
                'message': check.message,
                'response_time': check.response_time,
                'timestamp': check.timestamp.isoformat()
            })
        
        if alerts:
            health_data['alerts'] = alerts
        
        return jsonify({
            'success': True,
            'data': health_data,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error getting health status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/metrics/system')
def get_system_metrics():
    """Get system performance metrics."""
    try:
        days = int(request.args.get('days', 7))
        metrics = db_manager.get_system_metrics(days)
        
        metrics_data = []
        for metric in metrics:
            metrics_data.append({
                'timestamp': metric.timestamp.isoformat(),
                'job_execution_time': metric.job_execution_time,
                'api_response_time': metric.api_response_time,
                'email_send_time': metric.email_send_time,
                'rates_retrieved': metric.rates_retrieved,
                'rates_failed': metric.rates_failed,
                'job_success': metric.job_success,
                'error_count': metric.error_count,
                'memory_usage_mb': metric.memory_usage_mb,
                'cpu_percent': metric.cpu_percent
            })
        
        return jsonify({
            'success': True,
            'data': metrics_data,
            'period_days': days
        })
    
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/export')
def export_data():
    """Export data in various formats."""
    try:
        format_type = request.args.get('format', 'json')
        days = int(request.args.get('days', 30))
        
        data = db_manager.export_data(format_type, days)
        
        if format_type == 'json':
            return jsonify(json.loads(data))
        elif format_type == 'csv':
            return data, 200, {'Content-Type': 'text/csv'}
        else:
            return data, 200, {'Content-Type': 'text/plain'}
    
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/system/info')
def get_system_info():
    """Get system information."""
    try:
        # Get system information
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        system_info = {
            'python_version': sys.version,
            'platform': os.name,
            'memory': {
                'total_gb': round(memory.total / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2),
                'percent_used': memory.percent
            },
            'disk': {
                'total_gb': round(disk.total / (1024**3), 2),
                'free_gb': round(disk.free / (1024**3), 2),
                'percent_used': round((disk.used / disk.total) * 100, 2)
            },
            'database_path': str(db_manager.db_path),
            'database_size_mb': round(db_manager.db_path.stat().st_size / (1024**2), 2) if db_manager.db_path.exists() else 0
        }
        
        return jsonify({
            'success': True,
            'data': system_info,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('web/templates', exist_ok=True)
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
