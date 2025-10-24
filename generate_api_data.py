#!/usr/bin/env python3
"""
Generate API data files for the chart system.
This script creates JSON files that the frontend can consume.
"""
import os
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from database.models import DatabaseManager
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

def generate_chart_data(period='1M', currencies=['EUR', 'USD', 'GBP']):
    """Generate chart data for the specified period and currencies."""
    
    if DATABASE_AVAILABLE:
        try:
            db_manager = DatabaseManager()
            
            # Calculate date range based on period
            now = datetime.now()
            if period == '1D':
                start_date = now - timedelta(days=1)
            elif period == '1M':
                start_date = now - timedelta(days=30)
            elif period == '1Y':
                start_date = now - timedelta(days=365)
            elif period == '5Y':
                start_date = now - timedelta(days=5*365)
            else:
                start_date = now - timedelta(days=30)
            
            # Get rates from database
            rates = db_manager.get_rates_by_date_range(start_date, now)
            
            # For periods with limited recent data, use 2024 data
            using_fallback = False
            if not rates:
                if period in ['1D', '1M', '1Y']:
                    print(f"Using 2024 data for {period} period")
                    rates = db_manager.get_rates_by_date_range(datetime(2024, 1, 1), datetime(2024, 12, 31))
                    using_fallback = True
            else:
                # Check if we have enough unique dates
                unique_dates = len(set(r.timestamp.date() for r in rates))
                if unique_dates < 5 and period in ['1D', '1M', '1Y']:
                    print(f"Only {unique_dates} unique dates for {period}, using 2024 data")
                    rates = db_manager.get_rates_by_date_range(datetime(2024, 1, 1), datetime(2024, 12, 31))
                    using_fallback = True
            
            if not rates:
                print(f"No rates found for period {period}, using sample data")
                return generate_sample_data(period, currencies)
            
            # Group by currency and create chart data
            chart_data = {
                'labels': [],
                'datasets': []
            }
            
            # Get unique timestamps and sort them
            timestamps = sorted(set(rate.timestamp for rate in rates))
            
            # Filter timestamps based on period for better performance
            # Only apply filtering if we have recent data and not using fallback
            if rates and len(set(r.timestamp.date() for r in rates)) > 5 and not using_fallback:
                if period == '1D':
                    # For 1D, take last 24 hours
                    cutoff = now - timedelta(hours=24)
                    timestamps = [ts for ts in timestamps if ts >= cutoff]
                elif period == '1M':
                    # For 1M, take last 30 days
                    cutoff = now - timedelta(days=30)
                    timestamps = [ts for ts in timestamps if ts >= cutoff]
                elif period == '1Y':
                    # For 1Y, take last 365 days
                    cutoff = now - timedelta(days=365)
                    timestamps = [ts for ts in timestamps if ts >= cutoff]
                # For 5Y, use all timestamps
            
            chart_data['labels'] = [ts.strftime('%Y-%m-%d') for ts in timestamps]
            
            # Create datasets for each currency
            for currency in currencies:
                currency_rates = [r for r in rates if r.currency == currency]
                
                # Create rate map for quick lookup
                rate_map = {r.timestamp: r.rate for r in currency_rates}
                
                # Create dataset
                dataset = {
                    'label': currency,
                    'data': [rate_map.get(ts, None) for ts in timestamps],
                    'borderColor': get_currency_color(currency),
                    'backgroundColor': get_currency_color(currency) + '20',
                    'fill': False,
                    'tension': 0.4
                }
                chart_data['datasets'].append(dataset)
            
            return {
                'success': True,
                'data': chart_data,
                'period': period,
                'currencies': currencies,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error generating chart data from database: {e}")
            return generate_sample_data(period, currencies)
    else:
        return generate_sample_data(period, currencies)

def generate_sample_data(period='1M', currencies=['EUR', 'USD', 'GBP']):
    """Generate sample data for demonstration."""
    
    # Generate time labels based on period
    now = datetime.now()
    if period == '1D':
        point_count = 24
        time_step = timedelta(hours=1)
    elif period == '1M':
        point_count = 30
        time_step = timedelta(days=1)
    elif period == '1Y':
        point_count = 52
        time_step = timedelta(weeks=1)
    elif period == '5Y':
        point_count = 60
        time_step = timedelta(days=30)
    else:
        point_count = 30
        time_step = timedelta(days=1)
    
    # Generate labels
    labels = []
    for i in range(point_count, -1, -1):
        date = now - (i * time_step)
        labels.append(date.strftime('%Y-%m-%d'))
    
    # Generate datasets
    datasets = []
    base_rates = {'EUR': 4.95, 'USD': 4.55, 'GBP': 5.75}
    
    for currency in currencies:
        dataset = {
            'label': currency,
            'data': [],
            'borderColor': get_currency_color(currency),
            'backgroundColor': get_currency_color(currency) + '20',
            'fill': False,
            'tension': 0.4
        }
        
        # Generate rate data with some variation
        for i in range(point_count + 1):
            import random
            variation = (random.random() - 0.5) * 0.1
            rate = base_rates[currency] + variation
            dataset['data'].append(round(rate, 4))
        
        datasets.append(dataset)
    
    return {
        'success': True,
        'data': {
            'labels': labels,
            'datasets': datasets
        },
        'period': period,
        'currencies': currencies,
        'timestamp': datetime.now().isoformat(),
        'sample_data': True
    }

def get_currency_color(currency):
    """Get color for currency."""
    colors = {
        'EUR': '#667eea',
        'USD': '#f093fb',
        'GBP': '#4facfe'
    }
    return colors.get(currency, '#666666')

def generate_latest_rates():
    """Generate latest rates data."""
    
    if DATABASE_AVAILABLE:
        try:
            db_manager = DatabaseManager()
            latest_rates = db_manager.get_latest_rates()
            
            # Group by currency and get latest
            rates_data = {}
            for rate in latest_rates:
                if rate.currency not in rates_data:
                    rates_data[rate.currency] = {
                        'rate': rate.rate,
                        'source': rate.source,
                        'timestamp': rate.timestamp.isoformat(),
                        'multiplier': rate.multiplier
                    }
            
            return {
                'success': True,
                'data': rates_data,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error generating latest rates from database: {e}")
            return generate_sample_latest_rates()
    else:
        return generate_sample_latest_rates()

def generate_sample_latest_rates():
    """Generate sample latest rates."""
    return {
        'success': True,
        'data': {
            'EUR': {
                'rate': 4.9500,
                'source': 'BNR',
                'timestamp': datetime.now().isoformat(),
                'multiplier': 1
            },
            'USD': {
                'rate': 4.5500,
                'source': 'BNR',
                'timestamp': datetime.now().isoformat(),
                'multiplier': 1
            },
            'GBP': {
                'rate': 5.7500,
                'source': 'BNR',
                'timestamp': datetime.now().isoformat(),
                'multiplier': 1
            }
        },
        'timestamp': datetime.now().isoformat(),
        'sample_data': True
    }

def main():
    """Generate all API data files."""
    
    # Create API directory
    api_dir = Path('api')
    api_dir.mkdir(exist_ok=True)
    
    print("Generating API data files...")
    
    # Generate chart data for different periods
    periods = ['1D', '1M', '1Y', '5Y']
    for period in periods:
        chart_data = generate_chart_data(period)
        filename = api_dir / f'chart-data-{period.lower()}.json'
        with open(filename, 'w') as f:
            json.dump(chart_data, f, indent=2)
        print(f"Generated {filename}")
    
    # Generate latest rates
    latest_rates = generate_latest_rates()
    filename = api_dir / 'rates-latest.json'
    with open(filename, 'w') as f:
        json.dump(latest_rates, f, indent=2)
    print(f"Generated {filename}")
    
    # Generate health status
    health_data = {
        'success': True,
        'data': {
            'overall_status': 'healthy',
            'checks': [
                {
                    'service': 'System',
                    'status': 'healthy',
                    'message': 'System configuration valid',
                    'response_time': None,
                    'timestamp': datetime.now().isoformat()
                }
            ]
        },
        'timestamp': datetime.now().isoformat()
    }
    filename = api_dir / 'health.json'
    with open(filename, 'w') as f:
        json.dump(health_data, f, indent=2)
    print(f"Generated {filename}")
    
    print("API data generation completed!")

if __name__ == "__main__":
    main()
