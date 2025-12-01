"""
Production Database Migration System
Handles schema migrations with version tracking and rollback capabilities

Note: This file contains database schema definitions only - no sensitive data or credentials.
All database connections use environment variables for security.
"""

import asyncpg
from pathlib import Path
from typing import List, Dict
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class MigrationManager:
    """Production-grade migration management system"""

    def __init__(self, database_url: str, migrations_dir: str = "database/migrations"):
        self.database_url = database_url
        self.migrations_dir = Path(migrations_dir)
        self.migrations = self._load_migrations()

    def _load_migrations(self) -> List[Dict]:
        """Load migration files in order"""
        migrations = []
        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory {self.migrations_dir} does not exist")
            return migrations

        for migration_file in sorted(self.migrations_dir.glob("*.sql")):
            version = migration_file.stem
            with open(migration_file, "r") as f:
                content = f.read()
            migrations.append(
                {
                    "version": version,
                    "filename": migration_file.name,
                    "content": content,
                    "path": migration_file,
                }
            )

        logger.info(f"Loaded {len(migrations)} migrations")
        return migrations

    async def ensure_migration_table(self, conn: asyncpg.Connection):
        """Ensure migrations table exists"""
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(50) PRIMARY KEY,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                checksum VARCHAR(64) NOT NULL
            )
        """)

    async def get_applied_migrations(self, conn: asyncpg.Connection) -> set:
        """Get set of already applied migration versions"""
        try:
            rows = await conn.fetch(
                "SELECT version FROM schema_migrations ORDER BY version"
            )
            return {row["version"] for row in rows}
        except asyncpg.UndefinedTableError:
            return set()

    async def apply_migration(self, conn: asyncpg.Connection, migration: Dict) -> bool:
        """Apply a single migration"""
        try:
            # Begin transaction
            async with conn.transaction():
                # Execute migration SQL
                await conn.execute(migration["content"])

                # Record migration
                import hashlib

                checksum = hashlib.sha256(migration["content"].encode()).hexdigest()
                await conn.execute(
                    """
                    INSERT INTO schema_migrations (version, checksum, applied_at)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (version) DO NOTHING
                    """,
                    migration["version"],
                    checksum,
                    datetime.utcnow(),
                )

                logger.info(f"Applied migration {migration['version']}")
                return True

        except Exception as e:
            logger.error(f"Failed to apply migration {migration['version']}: {e}")
            raise

    async def migrate(self) -> int:
        """Run all pending migrations"""
        conn = await asyncpg.connect(self.database_url)
        try:
            await self.ensure_migration_table(conn)
            applied = await self.get_applied_migrations(conn)

            pending = [m for m in self.migrations if m["version"] not in applied]

            if not pending:
                logger.info("No pending migrations")
                return 0

            logger.info(f"Applying {len(pending)} pending migrations")
            applied_count = 0

            for migration in pending:
                await self.apply_migration(conn, migration)
                applied_count += 1

            logger.info(f"Successfully applied {applied_count} migrations")
            return applied_count

        finally:
            await conn.close()

    async def rollback_to_version(self, target_version: str) -> int:
        """Rollback migrations to a specific version"""
        conn = await asyncpg.connect(self.database_url)
        try:
            applied = await self.get_applied_migrations(conn)
            applied_versions = sorted(
                [v for v in applied if v > target_version], reverse=True
            )

            if not applied_versions:
                logger.info("No migrations to rollback")
                return 0

            # Note: This is a simplified rollback
            # In production, you'd need down migrations for each up migration
            logger.warning("Rollback functionality requires down migration files")
            return len(applied_versions)

        finally:
            await conn.close()

    async def get_migration_status(self) -> Dict:
        """Get current migration status"""
        conn = await asyncpg.connect(self.database_url)
        try:
            await self.ensure_migration_table(conn)
            applied = await self.get_applied_migrations(conn)

            all_versions = [m["version"] for m in self.migrations]
            pending = [v for v in all_versions if v not in applied]

            return {
                "total_migrations": len(all_versions),
                "applied_migrations": len(applied),
                "pending_migrations": len(pending),
                "applied_versions": sorted(applied),
                "pending_versions": sorted(pending),
                "current_version": max(applied) if applied else None,
            }

        finally:
            await conn.close()


# Production database configuration
class ProductionDBConfig:
    """Production database configuration with optimizations"""

    @staticmethod
    def get_connection_string(
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        ssl_mode: str = "require",
    ) -> str:
        """Build production connection string with security"""
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}?ssl={ssl_mode}"

    @staticmethod
    async def create_optimized_pool(database_url: str, **kwargs) -> asyncpg.Pool:
        """Create optimized connection pool for production"""
        default_config = {
            "min_size": 10,
            "max_size": 20,
            "max_queries": 50000,
            "max_inactive_connection_lifetime": 300,
            "command_timeout": 60,
            "server_settings": {
                "application_name": "modporter_ai",
                "timezone": "UTC",
                "search_path": "public",
            },
        }

        # Merge with provided config
        config = {**default_config, **kwargs}

        return await asyncpg.create_pool(database_url, **config)


# Database health monitoring
class DatabaseHealth:
    """Database health monitoring for production"""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def check_health(self) -> Dict:
        """Perform comprehensive health check"""
        health_status = {
            "status": "healthy",
            "checks": {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            # Basic connectivity
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                health_status["checks"]["connectivity"] = (
                    "pass" if result == 1 else "fail"
                )

                # Connection pool status
                health_status["checks"]["pool_size"] = self.pool.get_size()
                health_status["checks"]["pool_idle"] = self.pool.get_idle_size()

                # Database size and connections
                db_stats = await conn.fetchrow("""
                    SELECT 
                        pg_size_pretty(pg_database_size(current_database())) as db_size,
                        count(*) as active_connections
                    FROM pg_stat_activity 
                    WHERE state = 'active' AND pid != pg_backend_pid()
                """)

                health_status["checks"]["database_size"] = db_stats["db_size"]
                health_status["checks"]["active_connections"] = db_stats[
                    "active_connections"
                ]

                # Performance metrics
                perf_stats = await conn.fetchrow("""
                    SELECT 
                        avg(EXTRACT(EPOCH FROM (now() - query_start))) as avg_query_time,
                        count(*) as total_queries
                    FROM pg_stat_activity 
                    WHERE state = 'active' AND query NOT LIKE '%pg_stat_activity%'
                """)

                health_status["checks"]["avg_query_time"] = perf_stats["avg_query_time"]
                health_status["checks"]["total_queries"] = perf_stats["total_queries"]

        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["checks"]["error"] = str(e)
            logger.error(f"Database health check failed: {e}")

        return health_status


# Index optimization
class IndexOptimizer:
    """Database index optimization for production"""

    @staticmethod
    async def analyze_unused_indexes(pool: asyncpg.Pool) -> List[Dict]:
        """Find potentially unused indexes"""
        async with pool.acquire() as conn:
            unused = await conn.fetch("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes 
                WHERE idx_scan = 0 
                AND schemaname NOT IN ('pg_catalog', 'information_schema')
                ORDER BY schemaname, tablename, indexname
            """)
            return [dict(row) for row in unused]

    @staticmethod
    async def suggest_missing_indexes(pool: asyncpg.Pool) -> List[Dict]:
        """Suggest potentially missing indexes based on query patterns"""
        async with pool.acquire() as conn:
            # This would require more sophisticated analysis in production
            # For now, return basic recommendations
            suggestions = []

            # Check for large tables without proper indexes
            large_tables = await conn.fetch("""
                SELECT 
                    schemaname,
                    tablename,
                    n_tup_ins + n_tup_upd + n_tup_del as total_changes
                FROM pg_stat_user_tables
                WHERE (n_tup_ins + n_tup_upd + n_tup_del) > 10000
                ORDER BY total_changes DESC
                LIMIT 10
            """)

            for table in large_tables:
                suggestions.append(
                    {
                        "type": "consider_indexes",
                        "table": f"{table['schemaname']}.{table['tablename']}",
                        "reason": f"High activity table with {table['total_changes']} changes",
                    }
                )

            return suggestions
