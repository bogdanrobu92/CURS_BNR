#!/usr/bin/env python3
"""
Test script for date filtering functionality.
"""
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate_api_data import generate_chart_data

def test_date_filtering():
    """Test the date filtering functionality."""
    print("Testing date filtering functionality...")
    
    # Test 1: All data (no date filter)
    print("\n1. Testing all data (no date filter):")
    result1 = generate_chart_data()
    if result1['success']:
        labels = result1['data']['labels']
        print(f"   - Total data points: {len(labels)}")
        print(f"   - Date range: {labels[0]} to {labels[-1]}")
    else:
        print("   - Failed to generate data")
    
    # Test 2: Specific date range (last 7 days)
    print("\n2. Testing specific date range (last 7 days):")
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    result2 = generate_chart_data(start_date_str=start_date, end_date_str=end_date)
    if result2['success']:
        labels = result2['data']['labels']
        print(f"   - Date range: {start_date} to {end_date}")
        print(f"   - Data points: {len(labels)}")
        if labels:
            print(f"   - Actual range: {labels[0]} to {labels[-1]}")
    else:
        print("   - Failed to generate filtered data")
    
    # Test 3: Single day
    print("\n3. Testing single day (today):")
    today = datetime.now().strftime('%Y-%m-%d')
    result3 = generate_chart_data(start_date_str=today, end_date_str=today)
    if result3['success']:
        labels = result3['data']['labels']
        print(f"   - Date: {today}")
        print(f"   - Data points: {len(labels)}")
    else:
        print("   - Failed to generate single day data")
    
    print("\nDate filtering test completed!")

if __name__ == "__main__":
    from datetime import timedelta
    test_date_filtering()
