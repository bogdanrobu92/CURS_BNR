#!/usr/bin/env python3
"""
News fetcher module for BNR Exchange Rate Monitor.
Fetches news articles from various sources for specific dates.
"""
import os
import sys
import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from database.models import DatabaseManager, NewsArticle
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

try:
    from config import config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False


class NewsFetcher:
    """Fetches news articles from various sources."""
    
    def __init__(self):
        """Initialize news fetcher with API configurations."""
        # Use config if available, otherwise fall back to environment variables
        if CONFIG_AVAILABLE:
            self.newsapi_key = config.NEWSAPI_KEY or os.getenv('NEWSAPI_KEY', 'demo_key')
            self.guardian_key = config.GUARDIAN_KEY or os.getenv('GUARDIAN_KEY', 'demo_key')
        else:
            self.newsapi_key = os.getenv('NEWSAPI_KEY', 'demo_key')
            self.guardian_key = os.getenv('GUARDIAN_KEY', 'demo_key')
        
        # Log API key status (without exposing the key)
        if self.newsapi_key and self.newsapi_key != 'demo_key':
            print(f"✅ NewsAPI key configured (length: {len(self.newsapi_key)})")
        else:
            print("⚠️ NewsAPI key not set - will use sample news")
        
        if self.guardian_key and self.guardian_key != 'demo_key':
            print(f"✅ Guardian API key configured (length: {len(self.guardian_key)})")
        else:
            print("⚠️ Guardian API key not set - will skip Guardian API")
        
        # API endpoints
        self.newsapi_url = "https://newsapi.org/v2/everything"
        self.guardian_url = "https://content.guardianapis.com/search"
        
        # Headers for requests
        self.headers = {
            'User-Agent': 'BNR-Exchange-Rate-Monitor/1.0'
        }
    
    def _get_source_url(self, source: str) -> str:
        """Get the appropriate URL for a news source."""
        source_urls = {
            'European Central Bank': 'https://www.ecb.europa.eu/home/html/index.en.html',
            'Eurostat': 'https://ec.europa.eu/eurostat/data/database',
            'European Commission': 'https://ec.europa.eu/info/news_en',
            'BNR': 'https://www.bnr.ro',
            'Romanian Statistical Office': 'https://insse.ro',
            'Financial Markets': 'https://www.bnr.ro/nbrfxrates.xml'
        }
        return source_urls.get(source, 'https://www.bnr.ro')
    
    def fetch_news_for_date(self, date: datetime, region: str = 'europe') -> List[NewsArticle]:
        """
        Fetch news articles for a specific date and region.
        
        Args:
            date: Date to fetch news for
            region: Region to fetch news for ('europe' or 'romania')
            
        Returns:
            List of NewsArticle objects
        """
        articles = []
        
        # Check cache first
        if DATABASE_AVAILABLE:
            try:
                db_manager = DatabaseManager()
                cached_articles = db_manager.get_news_articles(date, region)
                if cached_articles:
                    print(f"Found {len(cached_articles)} cached articles for {date.date()} ({region})")
                    return cached_articles
            except Exception as e:
                print(f"Error checking cache: {e}")
        
        # Fetch from APIs
        if region == 'europe':
            articles.extend(self._fetch_european_news(date))
        elif region == 'romania':
            articles.extend(self._fetch_romanian_news(date))
        
        # Cache the articles
        if DATABASE_AVAILABLE and articles:
            try:
                db_manager = DatabaseManager()
                for article in articles:
                    db_manager.save_news_article(article)
                print(f"Cached {len(articles)} articles for {date.date()} ({region})")
            except Exception as e:
                print(f"Error caching articles: {e}")
        
        return articles
    
    def _fetch_european_news(self, date: datetime, force_no_fallback: bool = False) -> List[NewsArticle]:
        """Fetch European news articles."""
        articles = []
        
        # Try NewsAPI first
        try:
            newsapi_articles = self._fetch_from_newsapi(date, 'europe')
            articles.extend(newsapi_articles)
            if newsapi_articles:
                print(f"✅ NewsAPI returned {len(newsapi_articles)} European articles")
            else:
                print(f"⚠️ NewsAPI returned 0 European articles for {date.date()}")
        except Exception as e:
            print(f"❌ NewsAPI error: {e}")
        
        # Try Guardian API as backup
        try:
            guardian_articles = self._fetch_from_guardian(date, 'europe')
            articles.extend(guardian_articles)
            if guardian_articles:
                print(f"✅ Guardian API returned {len(guardian_articles)} European articles")
        except Exception as e:
            print(f"⚠️ Guardian API error: {e}")
        
        # If no real articles, generate sample data (unless forced not to)
        if not articles and not force_no_fallback:
            print(f"⚠️ No real articles found, generating sample news for {date.date()}")
            articles = self._generate_sample_news(date, 'europe')
        
        return articles
    
    def _fetch_romanian_news(self, date: datetime, force_no_fallback: bool = False) -> List[NewsArticle]:
        """Fetch Romanian news articles."""
        articles = []
        
        # Try NewsAPI with Romania-specific queries
        try:
            newsapi_articles = self._fetch_from_newsapi(date, 'romania')
            articles.extend(newsapi_articles)
            if newsapi_articles:
                print(f"✅ NewsAPI returned {len(newsapi_articles)} Romanian articles")
            else:
                print(f"⚠️ NewsAPI returned 0 Romanian articles for {date.date()}")
        except Exception as e:
            print(f"❌ NewsAPI Romania error: {e}")
        
        # If no real articles, generate sample data (unless forced not to)
        if not articles and not force_no_fallback:
            print(f"⚠️ No real articles found, generating sample news for {date.date()}")
            articles = self._generate_sample_news(date, 'romania')
        
        return articles
    
    def _fetch_from_newsapi(self, date: datetime, region: str) -> List[NewsArticle]:
        """Fetch articles from NewsAPI."""
        if not self.newsapi_key or self.newsapi_key == 'demo_key':
            print(f"NewsAPI: Skipping (no API key configured)")
            return []
        
        print(f"NewsAPI: Fetching for {date.date()} ({region})")
        
        # Calculate date range (±1 day for better coverage)
        from_date = (date - timedelta(days=1)).strftime('%Y-%m-%d')
        to_date = (date + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Set up query parameters based on region
        if region == 'europe':
            query = 'europe OR EU OR "European Union" OR euro OR ECB'
        else:  # romania
            query = 'romania OR "Romanian" OR BNR OR "National Bank of Romania"'
        
        params = {
            'q': query,
            'from': from_date,
            'to': to_date,
            'sortBy': 'publishedAt',
            'language': 'en',
            'pageSize': 10,
            'apiKey': self.newsapi_key
        }
        
        print(f"NewsAPI: Calling API with query='{query[:50]}...', date range={from_date} to {to_date}")
        
        response = requests.get(self.newsapi_url, params=params, headers=self.headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        print(f"NewsAPI: Status={data.get('status')}, Total Results={data.get('totalResults', 0)}")
        
        articles = []
        
        for i, article_data in enumerate(data.get('articles', []), 1):
            try:
                print(f"NewsAPI: Parsing article {i}/{len(data.get('articles', []))}")
                print(f"  Title: {article_data.get('title', 'N/A')[:50]}...")
                print(f"  Published: {article_data.get('publishedAt', 'N/A')}")
                
                published_at = datetime.fromisoformat(article_data['publishedAt'].replace('Z', '+00:00'))
                
                article = NewsArticle(
                    id=None,
                    date=date,
                    region=region,
                    title=article_data.get('title', ''),
                    description=article_data.get('description', ''),
                    source=article_data.get('source', {}).get('name', 'NewsAPI'),
                    url=article_data.get('url', ''),
                    published_at=published_at,
                    timestamp=datetime.now()
                )
                articles.append(article)
                print(f"  ✅ Parsed successfully")
            except Exception as e:
                print(f"  ❌ NewsAPI: Error parsing article: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"NewsAPI: Parsed {len(articles)} articles successfully")
        return articles
    
    def _fetch_from_guardian(self, date: datetime, region: str) -> List[NewsArticle]:
        """Fetch articles from Guardian API."""
        if not self.guardian_key or self.guardian_key == 'demo_key':
            print(f"Guardian API: Skipping (no API key configured)")
            return []
        
        # Calculate date range
        from_date = (date - timedelta(days=1)).strftime('%Y-%m-%d')
        to_date = (date + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Set up query based on region
        if region == 'europe':
            query = 'europe OR "European Union" OR euro OR ECB'
        else:  # romania
            query = 'romania OR "Romanian" OR BNR'
        
        params = {
            'q': query,
            'from-date': from_date,
            'to-date': to_date,
            'order-by': 'newest',
            'page-size': 10,
            'api-key': self.guardian_key
        }
        
        response = requests.get(self.guardian_url, params=params, headers=self.headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        articles = []
        
        for article_data in data.get('response', {}).get('results', []):
            try:
                published_at = datetime.fromisoformat(article_data['webPublicationDate'].replace('Z', '+00:00'))
                
                article = NewsArticle(
                    id=None,
                    date=date,
                    region=region,
                    title=article_data.get('webTitle', ''),
                    description=article_data.get('fields', {}).get('trailText', ''),
                    source='The Guardian',
                    url=article_data.get('webUrl', ''),
                    published_at=published_at,
                    timestamp=datetime.now()
                )
                articles.append(article)
            except Exception as e:
                print(f"Error parsing Guardian article: {e}")
                continue
        
        return articles
    
    def _generate_sample_news(self, date: datetime, region: str) -> List[NewsArticle]:
        """Generate sample news articles for demonstration with date-specific variations."""
        date_str = date.strftime('%Y/%m/%d')
        day_of_year = date.timetuple().tm_yday
        month_name = date.strftime('%B')
        
        if region == 'europe':
            # Vary content based on date to make each day unique
            news_templates = [
                {
                    'title': f'European Central Bank {month_name} Policy Meeting',
                    'description': f'The ECB reviewed monetary policy in {month_name}, with key decisions expected on interest rates and inflation targets.',
                    'source': 'European Central Bank',
                    'url': f'https://www.ecb.europa.eu/press/pr/date/{date.year}/html/ecb.pr{date.strftime("%y%m%d")}.en.html'
                },
                {
                    'title': f'EU Economic Indicators Show {month_name} Trends',
                    'description': f'Economic data for {month_name} reveals continued growth patterns across European Union member states, with GDP figures showing resilience.',
                    'source': 'Eurostat',
                    'url': f'https://ec.europa.eu/eurostat/web/products-eurostat-news/-/ddn-{date.strftime("%Y%m%d")}-1'
                },
                {
                    'title': f'Euro Zone Inflation Update for {date.strftime("%B %d")}',
                    'description': f'Consumer price data for {date.strftime("%B %d, %Y")} shows inflation trends in the euro area, with implications for ECB policy decisions.',
                    'source': 'European Commission',
                    'url': f'https://ec.europa.eu/commission/presscorner/detail/en/ip_{date.year}_{date.strftime("%m%d")}'
                }
            ]
            # Rotate templates based on day of year to create variation
            sample_articles = []
            for i, template in enumerate(news_templates):
                title = template['title']
                desc = template['description']
                # Add slight variation based on day
                if i == 0:
                    title = title.replace('Policy Meeting', f'Policy Update - Day {day_of_year}')
                elif i == 1:
                    title = title.replace('Trends', f'Performance Analysis')
                sample_articles.append({
                    'title': title,
                    'description': desc,
                    'source': template['source'],
                    'url': template['url']
                })
        else:  # romania
            # Vary content based on date to make each day unique
            news_templates = [
                {
                    'title': f'BNR {month_name} Monetary Policy Review',
                    'description': f'The National Bank of Romania reviewed monetary policy on {date.strftime("%B %d")}, focusing on inflation control and exchange rate stability.',
                    'source': 'BNR',
                    'url': f'https://www.bnr.ro/Press-release-{date.strftime("%Y-%m-%d")}.aspx'
                },
                {
                    'title': f'Romanian Economic Performance in {month_name}',
                    'description': f'Economic indicators for {date.strftime("%B %d, %Y")} suggest continued growth in the Romanian economy, with positive trends across sectors.',
                    'source': 'Romanian Statistical Office',
                    'url': f'https://insse.ro/cms/en/content/press-release-nr-{date.strftime("%m")}-{date.year}'
                },
                {
                    'title': f'RON Exchange Rate Update - {date.strftime("%B %d")}',
                    'description': f'The Romanian Leu exchange rate showed {["stability", "moderate fluctuations", "strengthening"][day_of_year % 3]} against major currencies on {date.strftime("%B %d")}.',
                    'source': 'Financial Markets',
                    'url': f'https://www.bnr.ro/Exchange-rates-{date.strftime("%Y-%m-%d")}.aspx'
                }
            ]
            sample_articles = news_templates
        
        articles = []
        for i, article_data in enumerate(sample_articles):
            # Spread articles across the day
            published_at = date.replace(hour=9 + i * 4, minute=0, second=0)
            
            article = NewsArticle(
                id=None,
                date=date,
                region=region,
                title=article_data['title'],
                description=article_data['description'],
                source=article_data['source'],
                url=article_data['url'],
                published_at=published_at,
                timestamp=datetime.now()
            )
            articles.append(article)
        
        return articles


def get_news_for_date(date_str: str, region: str = None) -> Dict:
    """
    Get news articles for a specific date.
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        region: Optional region filter ('europe' or 'romania')
        
    Returns:
        Dictionary with news data
    """
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
        fetcher = NewsFetcher()
        
        if region:
            articles = fetcher.fetch_news_for_date(date, region)
            return {
                'success': True,
                'date': date_str,
                'region': region,
                'articles': [
                    {
                        'title': article.title,
                        'description': article.description,
                        'source': article.source,
                        'url': article.url,
                        'published_at': article.published_at.isoformat()
                    }
                    for article in articles
                ],
                'timestamp': datetime.now().isoformat()
            }
        else:
            # Get both European and Romanian news
            europe_articles = fetcher.fetch_news_for_date(date, 'europe')
            romania_articles = fetcher.fetch_news_for_date(date, 'romania')
            
            return {
                'success': True,
                'date': date_str,
                'europe': [
                    {
                        'title': article.title,
                        'description': article.description,
                        'source': article.source,
                        'url': article.url,
                        'published_at': article.published_at.isoformat()
                    }
                    for article in europe_articles
                ],
                'romania': [
                    {
                        'title': article.title,
                        'description': article.description,
                        'source': article.source,
                        'url': article.url,
                        'published_at': article.published_at.isoformat()
                    }
                    for article in romania_articles
                ],
                'timestamp': datetime.now().isoformat()
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


if __name__ == "__main__":
    # Test the news fetcher
    print("Testing news fetcher...")
    
    # Test with today's date
    today = datetime.now().strftime('%Y-%m-%d')
    result = get_news_for_date(today)
    
    if result['success']:
        print(f"\nNews for {today}:")
        print(f"European articles: {len(result.get('europe', []))}")
        print(f"Romanian articles: {len(result.get('romania', []))}")
        
        if 'europe' in result and result['europe']:
            print("\nSample European article:")
            print(f"Title: {result['europe'][0]['title']}")
            print(f"Source: {result['europe'][0]['source']}")
        
        if 'romania' in result and result['romania']:
            print("\nSample Romanian article:")
            print(f"Title: {result['romania'][0]['title']}")
            print(f"Source: {result['romania'][0]['source']}")
    else:
        print(f"Error: {result['error']}")
