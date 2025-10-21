#!/usr/bin/env python3
"""
Startup script for BNR Exchange Rate Monitor Web Dashboard.
"""
import os
import sys
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Start the web dashboard."""
    print("🏦 Starting BNR Exchange Rate Monitor Web Dashboard...")
    
    # Check if required modules are available
    try:
        from web.app import app
        print("✅ Web application loaded successfully")
    except ImportError as e:
        print(f"❌ Failed to import web application: {e}")
        print("Please install required dependencies: pip install -r requirements.txt")
        sys.exit(1)
    
    # Check database initialization
    try:
        from database.models import DatabaseManager
        db_manager = DatabaseManager()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"⚠️  Database initialization warning: {e}")
    
    # Check backup sources
    try:
        from sources.backup_sources import BackupRateProvider
        rate_provider = BackupRateProvider()
        print("✅ Backup rate sources initialized successfully")
    except Exception as e:
        print(f"⚠️  Backup sources warning: {e}")
    
    # Start the Flask application
    print("\n🚀 Starting web server...")
    print("📊 Dashboard will be available at: http://localhost:5000")
    print("🔗 API endpoints available at: http://localhost:5000/api/")
    print("\nPress Ctrl+C to stop the server")
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n👋 Web dashboard stopped")
    except Exception as e:
        print(f"❌ Error starting web server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
