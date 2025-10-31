#!/usr/bin/env python3
"""
Backfill news articles for historical dates.
Fetches real news articles from NewsAPI for all dates that have exchange rate data.
"""
import os
import sys
from datetime import datetime, timedelta
import time
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from database.models import DatabaseManager
    from news_fetcher import NewsFetcher
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    print("Error: Database or news_fetcher modules not available")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_dates_with_exchange_rates(db_manager: DatabaseManager) -> list:
    """Get all unique dates that have exchange rate data."""
    try:
        # Get all exchange rates
        rates = db_manager.get_rates_by_date_range(
            datetime(2020, 1, 1),  # Start from 2020
            datetime.now()
        )
        
        # Extract unique dates
        unique_dates = sorted(set(rate.timestamp.date() for rate in rates))
        logger.info(f"Found {len(unique_dates)} dates with exchange rate data")
        return unique_dates
    except Exception as e:
        logger.error(f"Error getting dates with exchange rates: {e}")
        return []

def is_sample_news_source(source: str) -> bool:
    """Check if a news source is a sample/generated source."""
    sample_sources = [
        'European Central Bank',
        'Eurostat',
        'European Commission',
        'BNR',
        'Romanian Statistical Office',
        'Financial Markets'
    ]
    return source in sample_sources

def get_dates_without_news(db_manager: DatabaseManager, dates: list) -> list:
    """Filter out dates that already have real news articles (keep dates with only sample news)."""
    try:
        dates_with_real_news = set()
        
        for date in dates:
            date_obj = datetime.combine(date, datetime.min.time())
            europe_articles = db_manager.get_news_articles(date_obj, 'europe')
            romania_articles = db_manager.get_news_articles(date_obj, 'romania')
            
            # Check if there are any real (non-sample) news articles
            has_real_news = False
            for article in europe_articles + romania_articles:
                if not is_sample_news_source(article.source):
                    has_real_news = True
                    break
            
            if has_real_news:
                dates_with_real_news.add(date)
        
        dates_without_real_news = [d for d in dates if d not in dates_with_real_news]
        logger.info(f"Found {len(dates_without_real_news)} dates without real news articles (will replace sample news)")
        return dates_without_real_news
    except Exception as e:
        logger.error(f"Error checking existing news: {e}")
        return dates

def delete_sample_news_for_date(db_manager: DatabaseManager, date: datetime) -> int:
    """Delete sample news articles for a specific date."""
    try:
        import sqlite3
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        
        # Delete sample news articles for this date
        cursor.execute("""
            DELETE FROM news_articles 
            WHERE DATE(date) = ? 
            AND source IN ('European Central Bank', 'Eurostat', 'European Commission', 
                           'BNR', 'Romanian Statistical Office', 'Financial Markets')
        """, (date.date().isoformat(),))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} sample news articles for {date.date()}")
        
        return deleted_count
    except Exception as e:
        logger.warning(f"Error deleting sample news for {date.date()}: {e}")
        return 0

def backfill_news_for_date(fetcher: NewsFetcher, db_manager: DatabaseManager, date: datetime) -> tuple:
    """Fetch and save news articles for a specific date (force API fetch, skip cache)."""
    europe_count = 0
    romania_count = 0
    
    try:
        # First, delete any existing sample news for this date
        delete_sample_news_for_date(db_manager, date)
        
        # Delete ALL cached news for this date to force fresh fetch
        import sqlite3
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM news_articles WHERE DATE(date) = ?", (date.date().isoformat(),))
        deleted_all = cursor.rowcount
        conn.commit()
        conn.close()
        if deleted_all > 0:
            logger.info(f"Cleared all cached news for {date.date()} to force fresh fetch")
        
        # Fetch European news directly from API (bypass cache)
        logger.info(f"Fetching European news for {date.date()} (bypassing cache)")
        europe_articles = fetcher._fetch_european_news(date)
        
        # Only save if we got real API articles (not sample news)
        real_europe_articles = [a for a in europe_articles if not is_sample_news_source(a.source)]
        
        if real_europe_articles:
            for article in real_europe_articles:
                try:
                    db_manager.save_news_article(article)
                    europe_count += 1
                except Exception as e:
                    logger.warning(f"Failed to save European article: {e}")
        else:
            logger.warning(f"No real European news found for {date.date()} (API may have returned no results)")
        
        # Fetch Romanian news directly from API (bypass cache)
        logger.info(f"Fetching Romanian news for {date.date()} (bypassing cache)")
        romania_articles = fetcher._fetch_romanian_news(date)
        
        # Only save if we got real API articles (not sample news)
        real_romania_articles = [a for a in romania_articles if not is_sample_news_source(a.source)]
        
        if real_romania_articles:
            for article in real_romania_articles:
                try:
                    db_manager.save_news_article(article)
                    romania_count += 1
                except Exception as e:
                    logger.warning(f"Failed to save Romanian article: {e}")
        else:
            logger.warning(f"No real Romanian news found for {date.date()} (API may have returned no results)")
        
        return europe_count, romania_count
        
    except Exception as e:
        logger.error(f"Error fetching news for {date.date()}: {e}")
        import traceback
        traceback.print_exc()
        return 0, 0

def main():
    """Main backfill function."""
    if not DATABASE_AVAILABLE:
        logger.error("Database not available. Please ensure database models are properly configured.")
        return
    
    # Check if API key is configured
    newsapi_key = os.getenv('NEWSAPI_KEY', '')
    if not newsapi_key or newsapi_key == 'demo_key':
        logger.warning("⚠️  NEWSAPI_KEY not configured!")
        logger.warning("   Set NEWSAPI_KEY environment variable or configure it in GitHub Secrets")
        logger.warning("   Example: export NEWSAPI_KEY='your_api_key_here'")
        logger.warning("   Will attempt to fetch anyway, but will fall back to sample news if API key is missing")
    
    try:
        db_manager = DatabaseManager()
        fetcher = NewsFetcher()
        
        logger.info("="*60)
        logger.info("Starting news backfill process")
        logger.info("="*60)
        
        # Get all dates with exchange rate data
        dates = get_dates_with_exchange_rates(db_manager)
        
        if not dates:
            logger.warning("No dates with exchange rate data found")
            return
        
        # Filter out dates that already have news
        dates_to_fetch = get_dates_without_news(db_manager, dates)
        
        if not dates_to_fetch:
            logger.info("✅ All dates already have real news articles!")
            logger.info("   (If you want to replace sample news with real news, delete sample news first)")
            return
        
        logger.info(f"Will fetch news for {len(dates_to_fetch)} dates")
        
        # Fetch news for each date
        total_europe = 0
        total_romania = 0
        successful_dates = 0
        failed_dates = 0
        
        for i, date in enumerate(dates_to_fetch, 1):
            date_obj = datetime.combine(date, datetime.min.time())
            
            logger.info(f"\n[{i}/{len(dates_to_fetch)}] Processing {date}")
            logger.info("-" * 60)
            
            try:
                europe_count, romania_count = backfill_news_for_date(fetcher, db_manager, date_obj)
                
                if europe_count > 0 or romania_count > 0:
                    total_europe += europe_count
                    total_romania += romania_count
                    successful_dates += 1
                    logger.info(f"✅ Successfully fetched {europe_count} European + {romania_count} Romanian articles")
                else:
                    failed_dates += 1
                    logger.warning(f"⚠️  No articles fetched for {date}")
                
                # Rate limiting - be respectful to the API
                if i < len(dates_to_fetch):
                    time.sleep(1)  # 1 second delay between requests
                    
            except Exception as e:
                logger.error(f"❌ Failed to process {date}: {e}")
                failed_dates += 1
                continue
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("Backfill Summary")
        logger.info("="*60)
        logger.info(f"Total dates processed: {len(dates_to_fetch)}")
        logger.info(f"Successful: {successful_dates}")
        logger.info(f"Failed: {failed_dates}")
        logger.info(f"Total articles fetched:")
        logger.info(f"  - European: {total_europe}")
        logger.info(f"  - Romanian: {total_romania}")
        logger.info(f"  - Total: {total_europe + total_romania}")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"Backfill failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

