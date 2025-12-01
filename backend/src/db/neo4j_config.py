"""
Neo4j Database Configuration and Connection Management

This module provides optimized configuration settings for Neo4j
connections with proper pooling, retry logic, and performance tuning.
"""

import os
import time
import logging
from typing import Dict, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ConnectionStrategy(Enum):
    """Connection strategy for Neo4j."""

    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    RANDOM = "random"


@dataclass
class Neo4jPerformanceConfig:
    """Configuration for Neo4j performance optimization."""

    # Connection Pool Settings
    max_connection_pool_size: int = 50
    connection_acquisition_timeout: int = 60
    max_connection_lifetime: int = 3600  # 1 hour
    connection_idle_timeout: int = 300  # 5 minutes
    max_transaction_retry_time: int = 30  # 30 seconds

    # Query Settings
    query_timeout: int = 30  # 30 seconds
    max_transaction_retry_count: int = 3

    # Performance Tuning
    fetch_size: int = 1000  # Rows to fetch at once
    connection_timeout: int = 30  # Connection timeout
    socket_keepalive: bool = True
    socket_timeout: int = 0  # 0 = system default

    # Caching Settings
    query_cache_size: int = 1000
    result_cache_ttl: int = 300  # 5 minutes

    # Monitoring
    enable_metrics: bool = True
    metrics_collection_interval: int = 60  # seconds

    # Security
    encrypted: bool = False  # Set to True for production
    trust_strategy: str = "TRUST_ALL_CERTIFICATES"

    # High Availability (if using cluster)
    connection_strategy: ConnectionStrategy = ConnectionStrategy.ROUND_ROBIN
    load_balancing_strategy: str = "ROUND_ROBIN"

    def __post_init__(self):
        """Load settings from environment variables."""
        # Override with environment variables if present
        self.max_connection_pool_size = int(
            os.getenv("NEO4J_MAX_POOL_SIZE", self.max_connection_pool_size)
        )
        self.connection_acquisition_timeout = int(
            os.getenv("NEO4J_ACQUISITION_TIMEOUT", self.connection_acquisition_timeout)
        )
        self.max_connection_lifetime = int(
            os.getenv("NEO4J_MAX_LIFETIME", self.max_connection_lifetime)
        )
        self.connection_idle_timeout = int(
            os.getenv("NEO4J_IDLE_TIMEOUT", self.connection_idle_timeout)
        )
        self.query_timeout = int(os.getenv("NEO4J_QUERY_TIMEOUT", self.query_timeout))
        self.fetch_size = int(os.getenv("NEO4J_FETCH_SIZE", self.fetch_size))
        self.encrypted = os.getenv("NEO4J_ENCRYPTED", "false").lower() == "true"


@dataclass
class Neo4jEndpoints:
    """Neo4j endpoint configuration for multiple servers."""

    primary: str
    replicas: list[str] = field(default_factory=list)
    read_replicas: list[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "Neo4jEndpoints":
        """Create endpoints from environment variables."""
        primary = os.getenv("NEO4J_URI", "bolt://localhost:7687")

        replicas = []
        replica_urls = os.getenv("NEO4J_REPLICA_URIS", "").split(",")
        for url in replica_urls:
            url = url.strip()
            if url:
                replicas.append(url)

        read_replicas = []
        read_urls = os.getenv("NEO4J_READ_REPLICA_URIS", "").split(",")
        for url in read_urls:
            url = url.strip()
            if url:
                read_replicas.append(url)

        return cls(primary=primary, replicas=replicas, read_replicas=read_replicas)


class Neo4jQueryBuilder:
    """Helper class for building optimized queries."""

    @staticmethod
    def with_index_hints(
        query: str, node_labels: list[str] = None, properties: list[str] = None
    ) -> str:
        """Add index hints to Cypher query."""
        if not node_labels and not properties:
            return query

        hints = []

        if node_labels:
            for label in node_labels:
                hints.append(f"USING INDEX n:{label}(node_type)")

        if properties:
            for prop in properties:
                hints.append(f"USING INDEX n:KnowledgeNode({prop})")

        # Insert hints after MATCH clause
        if "MATCH" in query:
            parts = query.split("MATCH", 1)
            if len(parts) == 2:
                query = f"MATCH {' '.join(hints)} " + parts[1].strip()

        return query

    @staticmethod
    def with_pagination(query: str, skip: int = 0, limit: int = 100) -> str:
        """Add pagination to query."""
        if "SKIP" in query or "LIMIT" in query:
            return query  # Already paginated

        return f"{query} SKIP {skip} LIMIT {limit}"

    @staticmethod
    def with_optimization(query: str, options: Dict[str, Any] = None) -> str:
        """Add query plan optimizations."""
        if not options:
            return query

        # Add planner hints
        if "use_index" in options:
            query = query.replace("MATCH (n", "MATCH (n USE INDEX")

        if "join_strategy" in options:
            join_strategy = options["join_strategy"]
            if "JOIN" in query.upper():
                query = query.replace("JOIN", f"JOIN USING {join_strategy}")

        return query


class Neo4jRetryHandler:
    """Handles retry logic for Neo4j operations."""

    def __init__(
        self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 10.0
    ):
        """
        Initialize retry handler.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries (exponential backoff)
            max_delay: Maximum delay between retries
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    def retry_on_failure(self, operation: callable, *args, **kwargs):
        """
        Execute operation with retry logic.

        Args:
            operation: Function to execute
            *args, **kwargs: Arguments for the operation

        Returns:
            Result of the operation

        Raises:
            Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                last_exception = e

                # Don't retry on certain exceptions
                if self._should_not_retry(e):
                    raise

                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2**attempt), self.max_delay)
                    logger.warning(
                        f"Neo4j operation failed (attempt {attempt + 1}/{self.max_retries + 1}), retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Neo4j operation failed after {self.max_retries + 1} attempts: {e}"
                    )

        if last_exception is not None:
            raise last_exception
        else:
            raise RuntimeError(
                "Operation failed after retries, but no exception was captured. This should not happen."
            )

    def _should_not_retry(self, exception: Exception) -> bool:
        """Check if exception should not be retried."""
        # Don't retry on authentication or syntax errors
        error_str = str(exception).lower()

        no_retry_patterns = [
            "authentication",
            "syntax error",
            "invalid syntax",
            "unauthorized",
            "forbidden",
        ]

        return any(pattern in error_str for pattern in no_retry_patterns)


class Neo4jConnectionManager:
    """Manages Neo4j connections with pooling and failover."""

    def __init__(self, config: Neo4jPerformanceConfig):
        """Initialize connection manager."""
        self.config = config
        self.endpoints = Neo4jEndpoints.from_env()
        self.current_primary_index = 0
        self.current_replica_index = 0
        self.retry_handler = Neo4jRetryHandler(
            max_retries=config.max_transaction_retry_count,
            base_delay=1.0,
            max_delay=5.0,
        )

        # Connection pools for different endpoints
        self._pools = {}

        logger.info(
            f"Initialized Neo4j connection manager with {len(self.endpoints.replicas) + 1} endpoints"
        )

    def get_driver_config(self) -> Dict[str, Any]:
        """Get Neo4j driver configuration."""
        return {
            "max_connection_lifetime": self.config.max_connection_lifetime,
            "max_connection_pool_size": self.config.max_connection_pool_size,
            "connection_acquisition_timeout": self.config.connection_acquisition_timeout,
            "connection_timeout": self.config.connection_timeout,
            "socket_keepalive": self.config.socket_keepalive,
            "socket_timeout": self.config.socket_timeout,
            "encrypted": self.config.encrypted,
            "trust": self.config.trust_strategy,
            "fetch_size": self.config.fetch_size,
            "max_transaction_retry_time": self.config.max_transaction_retry_time,
        }

    def get_primary_uri(self) -> str:
        """Get current primary URI with simple failover."""
        # Try primary first
        if self._is_healthy(self.endpoints.primary):
            return self.endpoints.primary

        # Try replicas
        for replica in self.endpoints.replicas:
            if self._is_healthy(replica):
                logger.warning(
                    f"Primary endpoint unavailable, failing over to replica: {replica}"
                )
                return replica

        # Fall back to primary even if unhealthy
        logger.error("All endpoints appear unhealthy, using primary as last resort")
        return self.endpoints.primary

    def get_read_uri(self) -> str:
        """Get best read endpoint."""
        # Try read replicas first
        for replica in self.endpoints.read_replicas:
            if self._is_healthy(replica):
                return replica

        # Try regular replicas
        for replica in self.endpoints.replicas:
            if self._is_healthy(replica):
                return replica

        # Fall back to primary
        return self.endpoints.primary

    def _is_healthy(self, uri: str) -> bool:
        """Check if endpoint is healthy."""
        # Simple health check - could be enhanced with actual pings
        try:
            # Basic URI validation
            if not uri or not uri.startswith(("bolt://", "neo4j://", "neo4j+s://")):
                return False

            # In production, you might want to do an actual health check
            # For now, assume all configured endpoints are potentially healthy
            return True
        except Exception:
            return False


# Global configuration instance
neo4j_config = Neo4jPerformanceConfig()
connection_manager = Neo4jConnectionManager(neo4j_config)


# Configuration validation
def validate_configuration() -> bool:
    """Validate Neo4j configuration."""
    errors = []

    # Check required settings
    if not os.getenv("NEO4J_URI"):
        errors.append("NEO4J_URI is required")

    if not os.getenv("NEO4J_USER"):
        errors.append("NEO4J_USER is required")

    if not os.getenv("NEO4J_PASSWORD"):
        errors.append("NEO4J_PASSWORD is required")

    # Validate numeric settings
    if neo4j_config.max_connection_pool_size <= 0:
        errors.append("max_connection_pool_size must be positive")

    if neo4j_config.query_timeout <= 0:
        errors.append("query_timeout must be positive")

    if errors:
        logger.error(f"Neo4j configuration validation failed: {errors}")
        return False

    logger.info("Neo4j configuration validation passed")
    return True


# Initialize and validate on import
if not validate_configuration():
    logger.error("Invalid Neo4j configuration, performance may be degraded")
