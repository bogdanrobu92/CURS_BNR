"""
Database models for BNR Exchange Rate Monitor.
Provides data persistence and historical analysis capabilities.
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExchangeRate:
    """Exchange rate data model."""
    id: Optional[int]
    currency: str
    rate: float
    source: str
    timestamp: datetime
    multiplier: int = 1
    is_valid: bool = True


@dataclass
class RateTrend:
    """Rate trend analysis data model."""
    currency: str
    current_rate: float
    previous_rate: float
    change_absolute: float
    change_percentage: float
    trend_direction: str  # 'up', 'down', 'stable'
    volatility: float


@dataclass
class RateAlert:
    """Rate alert data model for significant changes."""
    id: Optional[int]
    currency: str
    start_date: datetime
    end_date: datetime
    start_rate: float
    end_rate: float
    change_percent: float
    duration_days: int
    alert_type: str  # 'positive' or 'negative'
    severity: str    # 'low', 'medium', 'high'
    timestamp: datetime


@dataclass
class NewsArticle:
    """News article data model for caching."""
    id: Optional[int]
    date: datetime
    region: str  # 'europe' or 'romania'
    title: str
    description: str
    source: str
    url: str
    published_at: datetime
    timestamp: datetime


@dataclass
class SystemMetrics:
    """System metrics data model."""
    id: Optional[int]
    timestamp: datetime
    job_execution_time: float
    api_response_time: float
    email_send_time: float
    rates_retrieved: int
    rates_failed: int
    job_success: bool
    error_count: int
    memory_usage_mb: float
    cpu_percent: float


class DatabaseManager:
    """Database management and operations."""
    
    def __init__(self, db_path: str = "data/exchange_rates.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
    
    def init_database(self) -> None:
        """Initialize database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Exchange rates table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exchange_rates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    currency TEXT NOT NULL,
                    rate REAL NOT NULL,
                    source TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    multiplier INTEGER DEFAULT 1,
                    is_valid BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # System metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    job_execution_time REAL NOT NULL,
                    api_response_time REAL NOT NULL,
                    email_send_time REAL NOT NULL,
                    rates_retrieved INTEGER NOT NULL,
                    rates_failed INTEGER NOT NULL,
                    job_success BOOLEAN NOT NULL,
                    error_count INTEGER NOT NULL,
                    memory_usage_mb REAL NOT NULL,
                    cpu_percent REAL NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Rate trends table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rate_trends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    currency TEXT NOT NULL,
                    current_rate REAL NOT NULL,
                    previous_rate REAL NOT NULL,
                    change_absolute REAL NOT NULL,
                    change_percentage REAL NOT NULL,
                    trend_direction TEXT NOT NULL,
                    volatility REAL NOT NULL,
                    timestamp DATETIME NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Rate alerts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rate_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    currency TEXT NOT NULL,
                    start_date DATETIME NOT NULL,
                    end_date DATETIME NOT NULL,
                    start_rate REAL NOT NULL,
                    end_rate REAL NOT NULL,
                    change_percent REAL NOT NULL,
                    duration_days INTEGER NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # News articles table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS news_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATETIME NOT NULL,
                    region TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    source TEXT NOT NULL,
                    url TEXT NOT NULL,
                    published_at DATETIME NOT NULL,
                    timestamp DATETIME NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rates_currency_timestamp ON exchange_rates(currency, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rates_timestamp ON exchange_rates(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON system_metrics(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_currency_date ON rate_alerts(currency, start_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON rate_alerts(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trends_currency_timestamp ON rate_trends(currency, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_date_region ON news_articles(date, region)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_timestamp ON news_articles(timestamp)")
            
            conn.commit()
    
    def clear_all_rates(self) -> None:
        """Clear all exchange rate data from the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM exchange_rates")
            cursor.execute("DELETE FROM rate_trends")
            cursor.execute("DELETE FROM system_metrics")
            conn.commit()
    
    def save_exchange_rate(self, rate: ExchangeRate) -> int:
        """Save exchange rate to database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO exchange_rates 
                (currency, rate, source, timestamp, multiplier, is_valid)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                rate.currency,
                rate.rate,
                rate.source,
                rate.timestamp,
                rate.multiplier,
                rate.is_valid
            ))
            return cursor.lastrowid
    
    def save_exchange_rates(self, rates: List[ExchangeRate]) -> List[int]:
        """Save multiple exchange rates to database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            ids = []
            for rate in rates:
                cursor.execute("""
                    INSERT INTO exchange_rates 
                    (currency, rate, source, timestamp, multiplier, is_valid)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    rate.currency,
                    rate.rate,
                    rate.source,
                    rate.timestamp,
                    rate.multiplier,
                    rate.is_valid
                ))
                ids.append(cursor.lastrowid)
            return ids
    
    def get_latest_rates(self, currency: Optional[str] = None) -> List[ExchangeRate]:
        """Get latest exchange rates."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if currency:
                cursor.execute("""
                    SELECT * FROM exchange_rates 
                    WHERE currency = ? AND is_valid = 1
                    ORDER BY timestamp DESC
                """, (currency,))
            else:
                cursor.execute("""
                    SELECT * FROM exchange_rates 
                    WHERE is_valid = 1
                    ORDER BY timestamp DESC
                """)
            
            rows = cursor.fetchall()
            return [self._row_to_exchange_rate(row) for row in rows]
    
    def get_rates_by_currency(self, currency: str) -> List[ExchangeRate]:
        """Get all exchange rates for a specific currency."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM exchange_rates 
                WHERE currency = ? AND is_valid = 1
                ORDER BY timestamp ASC
            """, (currency,))
            
            rows = cursor.fetchall()
            return [self._row_to_exchange_rate(row) for row in rows]
    
    def get_rates_by_date_range(self, 
                               start_date: datetime, 
                               end_date: datetime,
                               currency: Optional[str] = None) -> List[ExchangeRate]:
        """Get exchange rates by date range."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if currency:
                cursor.execute("""
                    SELECT * FROM exchange_rates 
                    WHERE currency = ? AND timestamp BETWEEN ? AND ? AND is_valid = 1
                    ORDER BY timestamp DESC
                """, (currency, start_date, end_date))
            else:
                cursor.execute("""
                    SELECT * FROM exchange_rates 
                    WHERE timestamp BETWEEN ? AND ? AND is_valid = 1
                    ORDER BY timestamp DESC
                """, (start_date, end_date))
            
            rows = cursor.fetchall()
            return [self._row_to_exchange_rate(row) for row in rows]
    
    def get_rate_trends(self, currency: str, days: int = 7) -> List[RateTrend]:
        """Calculate rate trends for a currency."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get rates for the specified period
            start_date = datetime.now() - timedelta(days=days)
            cursor.execute("""
                SELECT * FROM exchange_rates 
                WHERE currency = ? AND timestamp >= ? AND is_valid = 1
                ORDER BY timestamp ASC
            """, (currency, start_date))
            
            rows = cursor.fetchall()
            rates = [self._row_to_exchange_rate(row) for row in rows]
            
            # Calculate trends
            trends = []
            for i in range(1, len(rates)):
                current = rates[i]
                previous = rates[i-1]
                
                change_absolute = current.rate - previous.rate
                change_percentage = (change_absolute / previous.rate) * 100
                
                if change_percentage > 0.1:
                    trend_direction = 'up'
                elif change_percentage < -0.1:
                    trend_direction = 'down'
                else:
                    trend_direction = 'stable'
                
                # Calculate volatility (simplified)
                volatility = abs(change_percentage)
                
                trend = RateTrend(
                    currency=current.currency,
                    current_rate=current.rate,
                    previous_rate=previous.rate,
                    change_absolute=change_absolute,
                    change_percentage=change_percentage,
                    trend_direction=trend_direction,
                    volatility=volatility
                )
                trends.append(trend)
            
            return trends
    
    def get_currency_statistics(self, currency: str, days: int = 30) -> Dict:
        """Get statistics for a currency."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            start_date = datetime.now() - timedelta(days=days)
            cursor.execute("""
                SELECT 
                    MIN(rate) as min_rate,
                    MAX(rate) as max_rate,
                    AVG(rate) as avg_rate,
                    COUNT(*) as total_rates,
                    COUNT(DISTINCT DATE(timestamp)) as days_with_data
                FROM exchange_rates 
                WHERE currency = ? AND timestamp >= ? AND is_valid = 1
            """, (currency, start_date))
            
            row = cursor.fetchone()
            if not row:
                return {}
            
            return {
                'min_rate': row[0],
                'max_rate': row[1],
                'avg_rate': row[2],
                'total_rates': row[3],
                'days_with_data': row[4],
                'period_days': days
            }
    
    def save_system_metrics(self, metrics: SystemMetrics) -> int:
        """Save system metrics to database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO system_metrics 
                (timestamp, job_execution_time, api_response_time, email_send_time,
                 rates_retrieved, rates_failed, job_success, error_count,
                 memory_usage_mb, cpu_percent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.timestamp,
                metrics.job_execution_time,
                metrics.api_response_time,
                metrics.email_send_time,
                metrics.rates_retrieved,
                metrics.rates_failed,
                metrics.job_success,
                metrics.error_count,
                metrics.memory_usage_mb,
                metrics.cpu_percent
            ))
            return cursor.lastrowid
    
    def get_system_metrics(self, days: int = 7) -> List[SystemMetrics]:
        """Get system metrics for the specified period."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            start_date = datetime.now() - timedelta(days=days)
            cursor.execute("""
                SELECT * FROM system_metrics 
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            """, (start_date,))
            
            rows = cursor.fetchall()
            return [self._row_to_system_metrics(row) for row in rows]
    
    def export_data(self, format: str = 'json', days: int = 30) -> str:
        """Export data in specified format."""
        start_date = datetime.now() - timedelta(days=days)
        rates = self.get_rates_by_date_range(start_date, datetime.now())
        metrics = self.get_system_metrics(days)
        
        data = {
            'export_info': {
                'timestamp': datetime.now().isoformat(),
                'period_days': days,
                'total_rates': len(rates),
                'total_metrics': len(metrics)
            },
            'exchange_rates': [
                {
                    'currency': rate.currency,
                    'rate': rate.rate,
                    'source': rate.source,
                    'timestamp': rate.timestamp.isoformat(),
                    'multiplier': rate.multiplier
                } for rate in rates
            ],
            'system_metrics': [
                {
                    'timestamp': metric.timestamp.isoformat(),
                    'job_execution_time': metric.job_execution_time,
                    'api_response_time': metric.api_response_time,
                    'rates_retrieved': metric.rates_retrieved,
                    'job_success': metric.job_success
                } for metric in metrics
            ]
        }
        
        if format.lower() == 'json':
            return json.dumps(data, indent=2)
        elif format.lower() == 'csv':
            # Simple CSV export
            csv_lines = ['currency,rate,source,timestamp']
            for rate in rates:
                csv_lines.append(f"{rate.currency},{rate.rate},{rate.source},{rate.timestamp.isoformat()}")
            return '\n'.join(csv_lines)
        else:
            return str(data)
    
    def cleanup_old_data(self, days: int = 90) -> int:
        """Clean up old data to keep database size manageable."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Delete old exchange rates
            cursor.execute("DELETE FROM exchange_rates WHERE timestamp < ?", (cutoff_date,))
            rates_deleted = cursor.rowcount
            
            # Delete old system metrics
            cursor.execute("DELETE FROM system_metrics WHERE timestamp < ?", (cutoff_date,))
            metrics_deleted = cursor.rowcount
            
            # Delete old trends
            cursor.execute("DELETE FROM rate_trends WHERE timestamp < ?", (cutoff_date,))
            trends_deleted = cursor.rowcount
            
            conn.commit()
            return rates_deleted + metrics_deleted + trends_deleted
    
    def _row_to_exchange_rate(self, row) -> ExchangeRate:
        """Convert database row to ExchangeRate object."""
        return ExchangeRate(
            id=row['id'],
            currency=row['currency'],
            rate=row['rate'],
            source=row['source'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            multiplier=row['multiplier'],
            is_valid=bool(row['is_valid'])
        )
    
    def _row_to_system_metrics(self, row) -> SystemMetrics:
        """Convert database row to SystemMetrics object."""
        return SystemMetrics(
            id=row['id'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            job_execution_time=row['job_execution_time'],
            api_response_time=row['api_response_time'],
            email_send_time=row['email_send_time'],
            rates_retrieved=row['rates_retrieved'],
            rates_failed=row['rates_failed'],
            job_success=bool(row['job_success']),
            error_count=row['error_count'],
            memory_usage_mb=row['memory_usage_mb'],
            cpu_percent=row['cpu_percent']
        )
    
    def save_rate_alert(self, alert: RateAlert) -> int:
        """Save rate alert to database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO rate_alerts 
                (currency, start_date, end_date, start_rate, end_rate, 
                 change_percent, duration_days, alert_type, severity, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.currency,
                alert.start_date,
                alert.end_date,
                alert.start_rate,
                alert.end_rate,
                alert.change_percent,
                alert.duration_days,
                alert.alert_type,
                alert.severity,
                alert.timestamp
            ))
            return cursor.lastrowid
    
    def get_rate_alerts(self, currency: str = None, start_date: datetime = None, 
                       end_date: datetime = None) -> List[RateAlert]:
        """Get rate alerts with optional filtering."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM rate_alerts WHERE 1=1"
            params = []
            
            if currency:
                query += " AND currency = ?"
                params.append(currency)
            
            if start_date:
                query += " AND start_date >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND end_date <= ?"
                params.append(end_date)
            
            query += " ORDER BY start_date DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_rate_alert(row) for row in rows]
    
    def _row_to_rate_alert(self, row) -> RateAlert:
        """Convert database row to RateAlert object."""
        return RateAlert(
            id=row['id'],
            currency=row['currency'],
            start_date=datetime.fromisoformat(row['start_date']),
            end_date=datetime.fromisoformat(row['end_date']),
            start_rate=row['start_rate'],
            end_rate=row['end_rate'],
            change_percent=row['change_percent'],
            duration_days=row['duration_days'],
            alert_type=row['alert_type'],
            severity=row['severity'],
            timestamp=datetime.fromisoformat(row['timestamp'])
        )
    
    def save_news_article(self, article: NewsArticle) -> int:
        """Save news article to database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO news_articles 
                (date, region, title, description, source, url, published_at, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                article.date,
                article.region,
                article.title,
                article.description,
                article.source,
                article.url,
                article.published_at,
                article.timestamp
            ))
            return cursor.lastrowid
    
    def get_news_articles(self, date: datetime, region: str = None) -> List[NewsArticle]:
        """Get news articles for a specific date and optional region."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if region:
                cursor.execute("""
                    SELECT * FROM news_articles 
                    WHERE date = ? AND region = ?
                    ORDER BY published_at DESC
                """, (date, region))
            else:
                cursor.execute("""
                    SELECT * FROM news_articles 
                    WHERE date = ?
                    ORDER BY region, published_at DESC
                """, (date,))
            
            rows = cursor.fetchall()
            return [self._row_to_news_article(row) for row in rows]
    
    def _row_to_news_article(self, row) -> NewsArticle:
        """Convert database row to NewsArticle object."""
        return NewsArticle(
            id=row['id'],
            date=datetime.fromisoformat(row['date']),
            region=row['region'],
            title=row['title'],
            description=row['description'],
            source=row['source'],
            url=row['url'],
            published_at=datetime.fromisoformat(row['published_at']),
            timestamp=datetime.fromisoformat(row['timestamp'])
        )
