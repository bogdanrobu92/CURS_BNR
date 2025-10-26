#!/usr/bin/env python3
"""Backfill Oct 25 data using Oct 24 rate."""
from datetime import datetime
from database.models import DatabaseManager, ExchangeRate

db = DatabaseManager()

# Get the Oct 24 EUR rate
rates = db.get_rates_by_currency('EUR')
if rates:
    # Get the most recent Oct 24 rate
    oct24_rate = next((r for r in reversed(rates) if r.timestamp.strftime('%Y-%m-%d') == '2025-10-24'), None)
    
    if oct24_rate:
        # Create Oct 25 entry with same rate
        oct25_rate = ExchangeRate(
            id=None,
            currency='EUR',
            rate=oct24_rate.rate,
            source='BNR (Fallback)',
            timestamp=datetime(2025, 10, 25, 12, 0, 0),  # Oct 25 at noon
            multiplier=1,
            is_valid=True
        )
        
        db.save_exchange_rates([oct25_rate])
        print(f"✅ Backfilled Oct 25 data: EUR {oct25_rate.rate}")
    else:
        print("❌ No Oct 24 rate found")
else:
    print("❌ No EUR rates found in database")

