#!/usr/bin/env python3
"""
Change detection module for BNR Exchange Rate Monitor.
Detects significant changes (>2% in ≤2 months) in exchange rates.
"""
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from dataclasses import dataclass

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from database.models import DatabaseManager, ExchangeRate, RateAlert
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False


@dataclass
class ChangePoint:
    """Represents a significant change point in exchange rates."""
    start_date: datetime
    end_date: datetime
    start_rate: float
    end_rate: float
    change_percent: float
    duration_days: int
    alert_type: str  # 'positive' or 'negative'
    severity: str    # 'low', 'medium', 'high'


class ChangeDetector:
    """Detects significant changes in exchange rates."""
    
    def __init__(self, change_threshold: float = 2.0, max_duration_days: int = 60):
        """
        Initialize change detector.
        
        Args:
            change_threshold: Minimum percentage change to trigger alert (default: 2.0%)
            max_duration_days: Maximum duration in days for alert (default: 60 days)
        """
        self.change_threshold = change_threshold
        self.max_duration_days = max_duration_days
    
    def detect_changes(self, rates: List[ExchangeRate]) -> List[ChangePoint]:
        """
        Detect significant changes in exchange rates.
        
        Args:
            rates: List of exchange rates sorted by timestamp
            
        Returns:
            List of ChangePoint objects representing significant changes
        """
        if len(rates) < 2:
            return []
        
        changes = []
        rates_by_date = {rate.timestamp.date(): rate for rate in rates}
        sorted_dates = sorted(rates_by_date.keys())
        
        # Look for significant changes within the max duration window
        for i, start_date in enumerate(sorted_dates):
            start_rate = rates_by_date[start_date].rate
            
            # Check all possible end dates within the max duration
            for j in range(i + 1, len(sorted_dates)):
                end_date = sorted_dates[j]
                end_rate = rates_by_date[end_date].rate
                
                # Calculate duration
                duration_days = (end_date - start_date).days
                
                # Skip if duration exceeds max
                if duration_days > self.max_duration_days:
                    break
                
                # Calculate percentage change
                change_percent = ((end_rate - start_rate) / start_rate) * 100
                
                # Check if change is significant
                if abs(change_percent) >= self.change_threshold:
                    # Determine alert type and severity
                    alert_type = 'positive' if change_percent > 0 else 'negative'
                    severity = self._calculate_severity(abs(change_percent), duration_days)
                    
                    change_point = ChangePoint(
                        start_date=datetime.combine(start_date, datetime.min.time()),
                        end_date=datetime.combine(end_date, datetime.min.time()),
                        start_rate=start_rate,
                        end_rate=end_rate,
                        change_percent=change_percent,
                        duration_days=duration_days,
                        alert_type=alert_type,
                        severity=severity
                    )
                    
                    changes.append(change_point)
        
        # Remove overlapping changes (keep the most significant one)
        return self._remove_overlapping_changes(changes)
    
    def _calculate_severity(self, change_percent: float, duration_days: int) -> str:
        """
        Calculate severity based on change percentage and duration.
        
        Args:
            change_percent: Absolute change percentage
            duration_days: Duration in days
            
        Returns:
            Severity level: 'low', 'medium', or 'high'
        """
        # High severity: >5% change or >3% in <7 days
        if change_percent > 5.0 or (change_percent > 3.0 and duration_days < 7):
            return 'high'
        
        # Medium severity: >3% change or >2% in <14 days
        elif change_percent > 3.0 or (change_percent > 2.0 and duration_days < 14):
            return 'medium'
        
        # Low severity: 2-3% change
        else:
            return 'low'
    
    def _remove_overlapping_changes(self, changes: List[ChangePoint]) -> List[ChangePoint]:
        """
        Remove overlapping changes, keeping the most significant one.
        
        Args:
            changes: List of change points
            
        Returns:
            List of non-overlapping change points
        """
        if not changes:
            return []
        
        # Sort by significance (higher change percentage first)
        sorted_changes = sorted(changes, key=lambda x: abs(x.change_percent), reverse=True)
        
        non_overlapping = []
        used_dates = set()
        
        for change in sorted_changes:
            # Check if this change overlaps with any already selected change
            start_date = change.start_date.date()
            end_date = change.end_date.date()
            
            # Create a set of all dates in this change period
            change_dates = set()
            current_date = start_date
            while current_date <= end_date:
                change_dates.add(current_date)
                current_date += timedelta(days=1)
            
            # Check for overlap
            if not change_dates.intersection(used_dates):
                non_overlapping.append(change)
                used_dates.update(change_dates)
        
        # Sort by start date
        return sorted(non_overlapping, key=lambda x: x.start_date)
    
    def save_alerts_to_database(self, changes: List[ChangePoint], currency: str = 'EUR') -> int:
        """
        Save detected changes as alerts to the database.
        
        Args:
            changes: List of detected changes
            currency: Currency code
            
        Returns:
            Number of alerts saved
        """
        if not DATABASE_AVAILABLE:
            print("Database not available, cannot save alerts")
            return 0
        
        try:
            db_manager = DatabaseManager()
            saved_count = 0
            
            for change in changes:
                alert = RateAlert(
                    id=None,
                    currency=currency,
                    start_date=change.start_date,
                    end_date=change.end_date,
                    start_rate=change.start_rate,
                    end_rate=change.end_rate,
                    change_percent=change.change_percent,
                    duration_days=change.duration_days,
                    alert_type=change.alert_type,
                    severity=change.severity,
                    timestamp=datetime.now()
                )
                
                db_manager.save_rate_alert(alert)
                saved_count += 1
            
            print(f"Saved {saved_count} rate alerts to database")
            return saved_count
            
        except Exception as e:
            print(f"Error saving alerts to database: {e}")
            return 0


def analyze_exchange_rates(currency: str = 'EUR') -> List[ChangePoint]:
    """
    Analyze exchange rates and detect significant changes.
    
    Args:
        currency: Currency to analyze
        
    Returns:
        List of detected significant changes
    """
    if not DATABASE_AVAILABLE:
        print("Database not available for change analysis")
        return []
    
    try:
        db_manager = DatabaseManager()
        
        # Get all rates for the currency
        rates = db_manager.get_rates_by_currency(currency)
        
        if not rates:
            print(f"No rates found for {currency}")
            return []
        
        # Sort by timestamp
        rates.sort(key=lambda x: x.timestamp)
        
        # Detect changes
        detector = ChangeDetector(change_threshold=2.0, max_duration_days=60)
        changes = detector.detect_changes(rates)
        
        # Save to database
        detector.save_alerts_to_database(changes, currency)
        
        return changes
        
    except Exception as e:
        print(f"Error analyzing exchange rates: {e}")
        return []


if __name__ == "__main__":
    # Test the change detection
    print("Analyzing exchange rates for significant changes...")
    changes = analyze_exchange_rates('EUR')
    
    if changes:
        print(f"\nFound {len(changes)} significant changes:")
        for i, change in enumerate(changes, 1):
            print(f"{i}. {change.start_date.date()} to {change.end_date.date()}")
            print(f"   Rate: {change.start_rate:.4f} → {change.end_rate:.4f}")
            print(f"   Change: {change.change_percent:+.2f}% ({change.duration_days} days)")
            print(f"   Type: {change.alert_type}, Severity: {change.severity}")
            print()
    else:
        print("No significant changes detected.")
