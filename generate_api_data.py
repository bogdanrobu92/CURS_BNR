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
    from change_detector import analyze_exchange_rates
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

try:
    from news_fetcher import get_news_for_date
    NEWS_AVAILABLE = True
except ImportError:
    NEWS_AVAILABLE = False

def generate_chart_data(currencies=['EUR'], start_date_str=None, end_date_str=None):
    """Generate chart data for EUR only with optional date filtering."""
    
    if DATABASE_AVAILABLE:
        try:
            db_manager = DatabaseManager()
            
            # Parse date range parameters
            if start_date_str and end_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                    print(f"Filtering data from {start_date_str} to {end_date_str}")
                except ValueError:
                    print("Invalid date format, using all available data")
                    start_date = datetime(2014, 1, 1)
                    end_date = datetime.now()
            else:
                # Get all available rates from database
                start_date = datetime(2014, 1, 1)
                end_date = datetime.now()
            
            rates = db_manager.get_rates_by_date_range(start_date, end_date)
            
            if not rates:
                print("No rates found, using sample data")
                return generate_sample_data(currencies)
            
            # Group by currency and create chart data
            chart_data = {
                'labels': [],
                'datasets': []
            }
            
            # Group rates by DATE (not timestamp) to get one value per day
            # We'll prefer BNR source and take the most recent rate for each day
            from collections import defaultdict
            rates_by_date = defaultdict(list)
            
            for rate in rates:
                date_key = rate.timestamp.date()
                rates_by_date[date_key].append(rate)
            
            # Sort dates
            unique_dates = sorted(rates_by_date.keys())
            chart_data['labels'] = [d.strftime('%Y-%m-%d') for d in unique_dates]
            
            # Create datasets for each currency
            for currency in currencies:
                daily_rates = []
                
                for date in unique_dates:
                    # Get all rates for this date and currency
                    date_rates = [r for r in rates_by_date[date] 
                                 if r.currency == currency]
                    
                    if date_rates:
                        # Prefer BNR source, otherwise take the most recent
                        bnr_rates = [r for r in date_rates if 'BNR' in r.source]
                        if bnr_rates:
                            # Take the most recent BNR rate
                            best_rate = max(bnr_rates, key=lambda r: r.timestamp)
                        else:
                            # Take the most recent rate from any source
                            best_rate = max(date_rates, key=lambda r: r.timestamp)
                        
                        daily_rates.append(best_rate.rate)
                    else:
                        daily_rates.append(None)
                
                # Create dataset
                dataset = {
                    'label': currency,
                    'data': daily_rates,
                    'borderColor': get_currency_color(currency),
                    'backgroundColor': get_currency_color(currency) + '20',
                    'fill': False,
                    'tension': 0.4
                }
                chart_data['datasets'].append(dataset)
            
            # Detect and include alerts for significant changes
            alerts = []
            try:
                # Analyze exchange rates for significant changes
                changes = analyze_exchange_rates('EUR')
                
                # Convert changes to alert format for frontend
                for change in changes:
                    alert = {
                        'start_date': change.start_date.strftime('%Y-%m-%d'),
                        'end_date': change.end_date.strftime('%Y-%m-%d'),
                        'start_rate': change.start_rate,
                        'end_rate': change.end_rate,
                        'change_percent': change.change_percent,
                        'duration_days': change.duration_days,
                        'alert_type': change.alert_type,
                        'severity': change.severity
                    }
                    alerts.append(alert)
                
                print(f"Detected {len(alerts)} significant changes")
                
            except Exception as e:
                print(f"Error detecting changes: {e}")
            
            return {
                'success': True,
                'data': chart_data,
                'alerts': alerts,
                'currencies': currencies,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error generating chart data from database: {e}")
            return generate_sample_data(currencies)
    else:
        return generate_sample_data(currencies)

def generate_sample_data(currencies=['EUR']):
    """Generate sample data for demonstration."""
    
    # Generate 30 days of sample data
    now = datetime.now()
    point_count = 30
    time_step = timedelta(days=1)
    
    # Generate labels
    labels = []
    for i in range(point_count, -1, -1):
        date = now - (i * time_step)
        labels.append(date.strftime('%Y-%m-%d'))
    
    # Generate EUR dataset only
    import random
    dataset = {
        'label': 'EUR',
        'data': [],
        'borderColor': get_currency_color('EUR'),
        'backgroundColor': get_currency_color('EUR') + '20',
        'fill': False,
        'tension': 0.4
    }
    
    # Generate rate data with some variation
    base_rate = 5.08  # Current EUR rate
    for i in range(point_count + 1):
        variation = (random.random() - 0.5) * 0.1
        rate = base_rate + variation
        dataset['data'].append(round(rate, 4))
    
    return {
        'success': True,
        'data': {
            'labels': labels,
            'datasets': [dataset]
        },
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
            
            # Get only EUR rates
            rates_data = {}
            for rate in latest_rates:
                if rate.currency == 'EUR':
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
                'rate': 5.0835,
                'source': 'BNR',
                'timestamp': datetime.now().isoformat(),
                'multiplier': 1
            }
        },
        'timestamp': datetime.now().isoformat(),
        'sample_data': True
    }

def generate_news_data():
    """Generate news data for all dates with exchange rates."""
    if DATABASE_AVAILABLE and NEWS_AVAILABLE:
        try:
            db_manager = DatabaseManager()
            
            # Get all unique dates with exchange rates
            import sqlite3
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            
            # Get all unique dates from exchange_rates table
            cursor.execute("""
                SELECT DISTINCT DATE(timestamp) as date
                FROM exchange_rates
                ORDER BY date DESC
            """)
            dates = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            # Build comprehensive news data with all dates
            news_data = {
                'success': True,
                'dates': {}
            }
            
            print(f"Generating news data for {len(dates)} dates...")
            for date_str in dates:
                try:
                    news_for_date = get_news_for_date(date_str)
                    news_data['dates'][date_str] = {
                        'europe': news_for_date.get('europe', []),
                        'romania': news_for_date.get('romania', []),
                        'timestamp': news_for_date.get('timestamp', datetime.now().isoformat())
                    }
                    print(f"  ✅ {date_str}: {len(news_for_date.get('europe', []))} European, {len(news_for_date.get('romania', []))} Romanian articles")
                except Exception as e:
                    print(f"  ⚠️  Error fetching news for {date_str}: {e}")
                    news_data['dates'][date_str] = {
                        'europe': [],
                        'romania': [],
                        'timestamp': datetime.now().isoformat()
                    }
            
            news_data['timestamp'] = datetime.now().isoformat()
            return news_data
            
        except Exception as e:
            print(f"Error generating news data from database: {e}")
            return generate_sample_news_data()
    else:
        return generate_sample_news_data()

def generate_sample_news_data():
    """Generate sample news data."""
    return {
        'success': True,
        'dates': {
            datetime.now().strftime('%Y-%m-%d'): {
                'europe': [],
                'romania': [],
                'timestamp': datetime.now().isoformat()
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
    
    # Generate chart data for EUR only
    chart_data = generate_chart_data()
    filename = api_dir / 'chart-data.json'
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
    
    # Generate news data for all dates
    news_data = generate_news_data()
    filename = api_dir / 'news.json'
    with open(filename, 'w') as f:
        json.dump(news_data, f, indent=2)
    print(f"Generated {filename}")
    
    print("API data generation completed!")

if __name__ == "__main__":
    main()
