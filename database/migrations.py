"""
Database migration system for BNR Exchange Rate Monitor.
Provides version tracking and upgrade/downgrade capabilities.
"""
import sqlite3
import os
from pathlib import Path
from typing import List, Optional, Callable
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Migration:
    """Represents a database migration."""
    
    def __init__(
        self,
        version: int,
        description: str,
        upgrade: Callable[[sqlite3.Connection], None],
        downgrade: Optional[Callable[[sqlite3.Connection], None]] = None
    ):
        """Initialize a migration.
        
        Args:
            version: Migration version number (must be unique and sequential)
            description: Human-readable description of the migration
            upgrade: Function to execute when upgrading (takes connection as parameter)
            downgrade: Optional function to execute when downgrading
        """
        self.version = version
        self.description = description
        self.upgrade = upgrade
        self.downgrade = downgrade


class MigrationManager:
    """Manages database migrations."""
    
    def __init__(self, db_path: str = "data/exchange_rates.db"):
        """Initialize migration manager.
        
        Args:
            db_path: Path to the database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_migrations_table()
    
    def _init_migrations_table(self) -> None:
        """Initialize the migrations tracking table."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    description TEXT NOT NULL,
                    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
    
    def get_current_version(self) -> int:
        """Get the current database schema version.
        
        Returns:
            Current version number, or 0 if no migrations applied
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT MAX(version) FROM schema_migrations
            """)
            result = cursor.fetchone()
            return result[0] if result[0] is not None else 0
    
    def get_applied_migrations(self) -> List[int]:
        """Get list of applied migration versions.
        
        Returns:
            List of applied migration version numbers
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT version FROM schema_migrations ORDER BY version
            """)
            return [row[0] for row in cursor.fetchall()]
    
    def apply_migration(self, migration: Migration) -> None:
        """Apply a migration.
        
        Args:
            migration: Migration to apply
            
        Raises:
            ValueError: If migration version is invalid
            RuntimeError: If migration fails
        """
        current_version = self.get_current_version()
        
        if migration.version <= current_version:
            logger.warning(
                f"Migration {migration.version} already applied or version too low. "
                f"Current version: {current_version}"
            )
            return
        
        if migration.version != current_version + 1:
            raise ValueError(
                f"Migration version {migration.version} is not sequential. "
                f"Expected version {current_version + 1}"
            )
        
        logger.info(f"Applying migration {migration.version}: {migration.description}")
        
        with sqlite3.connect(self.db_path) as conn:
            try:
                migration.upgrade(conn)
                
                # Record migration
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO schema_migrations (version, description, applied_at)
                    VALUES (?, ?, ?)
                """, (migration.version, migration.description, datetime.now()))
                conn.commit()
                
                logger.info(f"Successfully applied migration {migration.version}")
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to apply migration {migration.version}: {e}")
                raise RuntimeError(f"Migration {migration.version} failed: {e}") from e
    
    def rollback_migration(self, migration: Migration) -> None:
        """Rollback a migration.
        
        Args:
            migration: Migration to rollback
            
        Raises:
            ValueError: If migration is not applied or downgrade not available
            RuntimeError: If rollback fails
        """
        current_version = self.get_current_version()
        
        if migration.version > current_version:
            raise ValueError(f"Migration {migration.version} has not been applied")
        
        if migration.downgrade is None:
            raise ValueError(f"Migration {migration.version} does not support downgrade")
        
        logger.info(f"Rolling back migration {migration.version}: {migration.description}")
        
        with sqlite3.connect(self.db_path) as conn:
            try:
                migration.downgrade(conn)
                
                # Remove migration record
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM schema_migrations WHERE version = ?
                """, (migration.version,))
                conn.commit()
                
                logger.info(f"Successfully rolled back migration {migration.version}")
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to rollback migration {migration.version}: {e}")
                raise RuntimeError(f"Rollback {migration.version} failed: {e}") from e
    
    def migrate(self, migrations: List[Migration]) -> None:
        """Apply all pending migrations.
        
        Args:
            migrations: List of migrations to apply (must be sorted by version)
        """
        current_version = self.get_current_version()
        
        # Filter pending migrations
        pending = [m for m in migrations if m.version > current_version]
        
        if not pending:
            logger.info("No pending migrations")
            return
        
        # Sort by version
        pending.sort(key=lambda m: m.version)
        
        logger.info(f"Applying {len(pending)} pending migrations")
        
        for migration in pending:
            self.apply_migration(migration)
        
        logger.info(f"Migration complete. Current version: {self.get_current_version()}")


# Define migrations
def get_migrations() -> List[Migration]:
    """Get list of all migrations.
    
    Returns:
        List of Migration objects, sorted by version
    """
    migrations = []
    
    # Migration 1: Add index for faster currency lookups (if not exists)
    def migration_001_upgrade(conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_exchange_rates_currency_lookup 
            ON exchange_rates(currency, timestamp DESC)
        """)
    
    def migration_001_downgrade(conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        cursor.execute("DROP INDEX IF EXISTS idx_exchange_rates_currency_lookup")
    
    migrations.append(Migration(
        version=1,
        description="Add index for faster currency lookups",
        upgrade=migration_001_upgrade,
        downgrade=migration_001_downgrade
    ))
    
    # Migration 2: Add index for date range queries
    def migration_002_upgrade(conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_exchange_rates_date_range 
            ON exchange_rates(timestamp, currency)
        """)
    
    def migration_002_downgrade(conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        cursor.execute("DROP INDEX IF EXISTS idx_exchange_rates_date_range")
    
    migrations.append(Migration(
        version=2,
        description="Add index for date range queries",
        upgrade=migration_002_upgrade,
        downgrade=migration_002_downgrade
    ))
    
    return migrations


def run_migrations(db_path: str = "data/exchange_rates.db") -> None:
    """Run all pending migrations.
    
    Args:
        db_path: Path to the database file
    """
    manager = MigrationManager(db_path)
    migrations = get_migrations()
    manager.migrate(migrations)


if __name__ == "__main__":
    """Run migrations when executed directly."""
    import sys
    
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/exchange_rates.db"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print(f"Running migrations on database: {db_path}")
    run_migrations(db_path)
    print("Migrations complete")

