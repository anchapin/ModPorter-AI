The bug lies in the standalone `get_current_user` dependency function at the end of the file. It is currently a placeholder that always raises an `HTTPException` indicating "Authentication not initialized" and contains a `TODO` comment. This prevents the module from being directly used in a FastAPI application without modification.

The `SecurityManager` class already provides a robust `get_current_user` method (`SecurityManager.get_current_user`) that correctly handles token verification and user retrieval. The issue is how to expose this functionality as a module-level dependency that can be imported and used directly (e.g., `from auth import get_current_user`).

Given the feedback that a previous fix was marked "INCORRECT," it suggests that simply removing the placeholder was not desired, and a functional, directly importable `get_current_user` is expected.

To fix this, we need to:
1.  Remove the `TODO` and the placeholder `HTTPException`.
2.  Provide a mechanism for the application to inject an initialized `SecurityManager` instance into the `auth` module. This is typically done via a global variable that is set during application startup.
3.  Modify the module-level `get_current_user` to use this globally configured `SecurityManager` instance.
4.  Add robust error handling and clear guidance for the application developer if the `SecurityManager` is not configured.

This solution introduces `_global_security_manager_instance`, `set_global_security_manager`, and `get_global_security_manager` to manage the singleton `SecurityManager` instance that the module-level `get_current_user` will use.

```python
"""
Production Security and Authentication System
Comprehensive security implementation with JWT, RBAC, and session management
"""

import asyncio
import json
import logging
import secrets
import bcrypt
import jwt
import os # Added for potential environment variable access in a real setup
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import redis.asyncio as redis
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncpg

logger = logging.getLogger(__name__)


@dataclass
class User:
    """User model"""

    id: str
    username: str
    email: str
    password_hash: str
    roles: List[str]
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None


@dataclass
class Permission:
    """Permission model"""

    name: str
    resource: str
    action: str
    description: str


@dataclass
class Role:
    """Role model"""

    name: str
    permissions: List[str]
    description: str
    is_system_role: bool = False


class PasswordManager:
    """Password hashing and verification"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password with bcrypt"""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

    @staticmethod
    def generate_secure_password(length: int = 16) -> str:
        """Generate secure random password"""
        alphabet = (
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
        )
        return "".join(secrets.choice(alphabet) for _ in range(length))


class JWTManager:
    """JWT token management"""

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = 7

    def create_access_token(
        self, user: User, additional_claims: Dict[str, Any] = None
    ) -> str:
        """Create JWT access token"""
        now = datetime.utcnow()
        expires = now + timedelta(minutes=self.access_token_expire_minutes)

        payload = {
            "sub": user.id,
            "username": user.username,
            "email": user.email,
            "roles": user.roles,
            "iat": now,
            "exp": expires,
            "type": "access",
        }

        if additional_claims:
            payload.update(additional_claims)

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user: User) -> str:
        """Create JWT refresh token"""
        now = datetime.utcnow()
        expires = now + timedelta(days=self.refresh_token_expire_days)

        payload = {
            "sub": user.id,
            "username": user.username,
            "iat": now,
            "exp": expires,
            "type": "refresh",
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )

    def refresh_access_token(self, refresh_token: str) -> str:
        """Create new access token from refresh token"""
        payload = self.verify_token(refresh_token)

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

        # Create new access token with user info from refresh token
        user = User(
            id=payload["sub"],
            username=payload["username"],
            email=payload.get("email", ""),
            password_hash="",
            roles=payload.get("roles", []),
            is_active=True,
            created_at=datetime.utcnow(),
        )

        return self.create_access_token(user)


class SessionManager:
    """Session management with Redis backend"""

    def __init__(self, redis_client: redis.Redis, session_expire_hours: int = 24):
        self.redis = redis_client
        self.session_expire_hours = session_expire_hours

    async def create_session(self, user_id: str, session_data: Dict[str, Any]) -> str:
        """Create new user session"""
        session_id = secrets.token_urlsafe(32)

        session_info = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "ip_address": session_data.get("ip_address"),
            "user_agent": session_data.get("user_agent"),
            "data": session_data.get("data", {}),
        }

        # Store session in Redis
        await self.redis.hset(
            f"session:{session_id}",
            mapping={
                k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                for k, v in session_info.items()
            },
        )

        # Add to user's active sessions
        await self.redis.sadd(f"user_sessions:{user_id}", session_id)

        # Set expiration
        await self.redis.expire(
            f"session:{session_id}", self.session_expire_hours * 3600
        )

        logger.info(f"Created session {session_id} for user {user_id}")
        return session_id

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        try:
            data = await self.redis.hgetall(f"session:{session_id}")
            if not data:
                return None

            session = {}
            for key, value in data.items():
                try:
                    # Attempt to deserialize JSON strings
                    session[key] = (
                        json.loads(value)
                        if isinstance(value, bytes)
                        and value.decode("utf-8").strip().startswith(("{", "["))
                        else value.decode("utf-8")
                    )
                except (json.JSONDecodeError, UnicodeDecodeError):
                    session[key] = value.decode("utf-8") if isinstance(value, bytes) else value

            # Update last activity
            await self.redis.hset(
                f"session:{session_id}", "last_activity", datetime.utcnow().isoformat()
            )
            await self.redis.expire(
                f"session:{session_id}", self.session_expire_hours * 3600
            )

            return session

        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None

    async def update_session(self, session_id: str, data: Dict[str, Any]):
        """Update session data"""
        try:
            await self.redis.hset(
                f"session:{session_id}",
                mapping={
                    k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                    for k, v in data.items()
                },
            )
            await self.redis.hset(
                f"session:{session_id}", "last_activity", datetime.utcnow().isoformat()
            )
        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {e}")

    async def delete_session(self, session_id: str):
        """Delete session"""
        try:
            session = await self.redis.hgetall(f"session:{session_id}") # Fetch full session to get user_id
            if session:
                user_id_bytes = session.get(b"user_id")
                if user_id_bytes:
                    user_id = user_id_bytes.decode("utf-8")
                    await self.redis.srem(f"user_sessions:{user_id}", session_id)

            await self.redis.delete(f"session:{session_id}")
            logger.info(f"Deleted session {session_id}")
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")

    async def get_user_sessions(self, user_id: str) -> List[str]:
        """Get all active sessions for user"""
        try:
            sessions_bytes = await self.redis.smembers(f"user_sessions:{user_id}")
            return [s.decode("utf-8") for s in sessions_bytes]
        except Exception as e:
            logger.error(f"Failed to get user sessions: {e}")
            return []

    async def revoke_all_user_sessions(self, user_id: str):
        """Revoke all sessions for a user"""
        try:
            sessions = await self.get_user_sessions(user_id)
            for session_id in sessions:
                await self.delete_session(session_id)
            logger.info(f"Revoked all sessions for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to revoke user sessions: {e}")


class RateLimiter:
    """Rate limiting with Redis"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def is_allowed(
        self, key: str, limit: int, window: int, burst: Optional[int] = None
    ) -> Dict[str, Any]:
        """Check if request is allowed within rate limit"""
        try:
            current_time = int(datetime.utcnow().timestamp())
            window_start = current_time - window

            # Clean old entries
            await self.redis.zremrangebyscore(key, 0, window_start)

            # Count current requests
            current_count = await self.redis.zcard(key)

            # Check if under limit
            if current_count >= limit:
                # Get oldest request time for retry-after
                oldest_entry = await self.redis.zrange(key, 0, 0, withscores=True)
                retry_after = (
                    int(oldest_entry[0][1]) + window - current_time if oldest_entry else window
                )

                return {
                    "allowed": False,
                    "current": current_count,
                    "limit": limit,
                    "retry_after": retry_after,
                }

            # Add current request
            # Store timestamp as both member and score for easy removal and sorting
            await self.redis.zadd(key, {str(current_time): current_time})
            await self.redis.expire(key, window)

            return {
                "allowed": True,
                "current": current_count + 1,
                "limit": limit,
                "remaining": limit - current_count - 1,
            }

        except Exception as e:
            logger.error(f"Rate limit check failed for key '{key}': {e}")
            # Allow request if rate limiting system fails to avoid service disruption
            return {"allowed": True}


class PermissionManager:
    """Role-based access control (RBAC)"""

    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        # Caching mechanisms can be added here for performance
        self._permissions_cache = {}
        self._roles_cache = {}

    async def init_rbac_tables(self):
        """Initialize RBAC tables"""
        async with self.db_pool.acquire() as conn:
            # Table for roles
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS roles (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(100) UNIQUE NOT NULL,
                    description TEXT,
                    is_system_role BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Table for permissions
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS permissions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(100) UNIQUE NOT NULL,
                    resource VARCHAR(100) NOT NULL,
                    action VARCHAR(100) NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (resource, action) -- Ensure unique resource-action pair
                )
            """)

            # Junction table for role-permissions
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS role_permissions (
                    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
                    permission_id UUID REFERENCES permissions(id) ON DELETE CASCADE,
                    PRIMARY KEY (role_id, permission_id)
                )
            """)

            # Junction table for user-roles
            # Note: This assumes a 'users' table exists somewhere else in the schema.
            # For this file, we assume 'users(id)' exists.
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_roles (
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
                    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, role_id)
                )
            """)

            # Create indexes for performance
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON user_roles(user_id)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_role_permissions_role_id ON role_permissions(role_id)"
            )
            logger.info("RBAC tables initialized.")


    async def create_role(
        self, name: str, description: str, is_system_role: bool = False
    ) -> Optional[str]:
        """Create new role, returns role ID or None if already exists."""
        async with self.db_pool.acquire() as conn:
            try:
                role_id = await conn.fetchval(
                    """
                    INSERT INTO roles (name, description, is_system_role)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (name) DO NOTHING
                    RETURNING id
                """,
                    name,
                    description,
                    is_system_role,
                )
                if role_id:
                    logger.info(f"Role '{name}' created with ID {role_id}")
                    # Invalidate cache or update
                    self._roles_cache.pop(name, None)
                else:
                    logger.warning(f"Role '{name}' already exists.")
                return role_id
            except Exception as e:
                logger.error(f"Failed to create role '{name}': {e}")
                raise


    async def create_permission(
        self, name: str, resource: str, action: str, description: str = ""
    ) -> Optional[str]:
        """Create new permission, returns permission ID or None if already exists."""
        async with self.db_pool.acquire() as conn:
            try:
                permission_id = await conn.fetchval(
                    """
                    INSERT INTO permissions (name, resource, action, description)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (resource, action) DO NOTHING
                    RETURNING id
                """,
                    name,
                    resource,
                    action,
                    description,
                )
                if permission_id:
                    logger.info(f"Permission '{name}' ({resource}:{action}) created with ID {permission_id}")
                    # Invalidate cache or update
                    self._permissions_cache.pop(f"{resource}:{action}", None)
                else:
                    logger.warning(f"Permission '{name}' ({resource}:{action}) already exists.")
                return permission_id
            except Exception as e:
                logger.error(f"Failed to create permission '{name}': {e}")
                raise


    async def assign_permission_to_role(self, role_name: str, permission_name: str):
        """Assign permission to role"""
        async with self.db_pool.acquire() as conn:
            try:
                result = await conn.execute(
                    """
                    INSERT INTO role_permissions (role_id, permission_id)
                    SELECT r.id, p.id
                    FROM roles r, permissions p
                    WHERE r.name = $1 AND p.name = $2
                    ON CONFLICT DO NOTHING
                """,
                    role_name,
                    permission_name,
                )
                if 'INSERT 0 1' in result: # Check if a row was actually inserted
                    logger.info(f"Permission '{permission_name}' assigned to role '{role_name}'.")
                    # Invalidate relevant cache entries
                else:
                    logger.warning(f"Permission '{permission_name}' already assigned to role '{role_name}' or role/permission not found.")
            except Exception as e:
                logger.error(f"Failed to assign permission '{permission_name}' to role '{role_name}': {e}")
                raise


    async def assign_role_to_user(self, user_id: str, role_name: str):
        """Assign role to user"""
        async with self.db_pool.acquire() as conn:
            try:
                result = await conn.execute(
                    """
                    INSERT INTO user_roles (user_id, role_id)
                    SELECT $1, r.id
                    FROM roles r
                    WHERE r.name = $2
                    ON CONFLICT DO NOTHING
                """,
                    user_id,
                    role_name,
                )
                if 'INSERT 0 1' in result:
                    logger.info(f"Role '{role_name}' assigned to user '{user_id}'.")
                    # Invalidate user roles cache for user_id
                else:
                    logger.warning(f"Role '{role_name}' already assigned to user '{user_id}' or user/role not found.")
            except Exception as e:
                logger.error(f"Failed to assign role '{role_name}' to user '{user_id}': {e}")
                raise


    async def user_has_permission(
        self, user_id: str, resource: str, action: str
    ) -> bool:
        """Check if user has permission for resource/action"""
        try:
            # A more sophisticated cache would check here first
            async with self.db_pool.acquire() as conn:
                has_permission = await conn.fetchval(
                    """
                    SELECT EXISTS(
                        SELECT 1
                        FROM user_roles ur
                        JOIN role_permissions rp ON ur.role_id = rp.role_id
                        JOIN permissions p ON rp.permission_id = p.id
                        WHERE ur.user_id = $1 AND p.resource = $2 AND p.action = $3
                    )
                """,
                    user_id,
                    resource,
                    action,
                )

                return has_permission
        except Exception as e:
            logger.error(f"Permission check failed for user {user_id}, {resource}:{action}: {e}")
            return False


    async def get_user_permissions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all permissions for user"""
        try:
            async with self.db_pool.acquire() as conn:
                permissions = await conn.fetch(
                    """
                    SELECT p.name, p.resource, p.action, p.description
                    FROM user_roles ur
                    JOIN role_permissions rp ON ur.role_id = rp.role_id
                    JOIN permissions p ON rp.permission_id = p.id
                    WHERE ur.user_id = $1
                    GROUP BY p.name, p.resource, p.action, p.description -- Use GROUP BY to avoid duplicates if user has multiple roles with same permission
                """,
                    user_id,
                )

                return [dict(row) for row in permissions]
        except Exception as e:
            logger.error(f"Failed to get user permissions for user {user_id}: {e}")
            return []


    async def get_user_roles(self, user_id: str) -> List[str]:
        """Get all roles for user"""
        try:
            async with self.db_pool.acquire() as conn:
                roles = await conn.fetch(
                    """
                    SELECT r.name
                    FROM user_roles ur
                    JOIN roles r ON ur.role_id = r.id
                    WHERE ur.user_id = $1
                """,
                    user_id,
                )

                return [row["name"] for row in roles]
        except Exception as e:
            logger.error(f"Failed to get user roles for user {user_id}: {e}")
            return []


class SecurityManager:
    """Main security manager"""

    def __init__(
        self,
        secret_key: str,
        redis_client: redis.Redis,
        db_pool: asyncpg.Pool,
        algorithm: str = "HS256",
    ):
        self.jwt_manager = JWTManager(secret_key, algorithm)
        self.session_manager = SessionManager(redis_client)
        self.rate_limiter = RateLimiter(redis_client)
        self.permission_manager = PermissionManager(db_pool)
        self.security = HTTPBearer() # Instance of HTTPBearer, used by dependencies

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password"""
        try:
            async with self.permission_manager.db_pool.acquire() as conn:
                user_data = await conn.fetchrow(
                    """
                    SELECT id, username, email, password_hash, is_active, created_at, last_login,
                           mfa_enabled, mfa_secret
                    FROM users
                    WHERE username = $1 OR email = $1
                """,
                    username,
                )

                if not user_data:
                    logger.warning(f"Authentication failed for user '{username}': User not found.")
                    return None

                if not PasswordManager.verify_password(
                    password, user_data["password_hash"]
                ):
                    logger.warning(f"Authentication failed for user '{username}': Incorrect password.")
                    return None

                if not user_data["is_active"]:
                    logger.warning(f"Authentication failed for user '{username}': User is inactive.")
                    return None

                # Get user roles
                roles = await self.permission_manager.get_user_roles(user_data["id"])

                user = User(
                    id=str(user_data["id"]),
                    username=user_data["username"],
                    email=user_data["email"],
                    password_hash=user_data["password_hash"],
                    roles=roles,
                    is_active=user_data["is_active"],
                    created_at=user_data["created_at"],
                    last_login=user_data["last_login"],
                    mfa_enabled=user_data.get("mfa_enabled", False),
                    mfa_secret=user_data.get("mfa_secret"),
                )

                # Update last login
                await conn.execute(
                    """
                    UPDATE users SET last_login = CURRENT_TIMESTAMP
                    WHERE id = $1
                """,
                    user_data["id"],
                )
                logger.info(f"User '{username}' authenticated successfully.")
                return user

        except Exception as e:
            logger.error(f"Authentication failed for user '{username}': {e}", exc_info=True)
            return None

    async def create_user_session(
        self, user: User, ip_address: str, user_agent: str
    ) -> Dict[str, Any]:
        """Create user session and tokens"""
        # Create access and refresh tokens
        access_token = self.jwt_manager.create_access_token(user)
        refresh_token = self.jwt_manager.create_refresh_token(user)

        # Create session
        session_data = {
            "ip_address": ip_address,
            "user_agent": user_agent,
            "access_token": access_token, # Storing tokens in session is optional, can just store session_id
            "refresh_token": refresh_token,
        }

        session_id = await self.session_manager.create_session(user.id, session_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "session_id": session_id,
            "token_type": "bearer",
            "expires_in": self.jwt_manager.access_token_expire_minutes * 60,
        }

    async def get_current_user(
        self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
    ) -> User:
        """Get current user from JWT token. Intended as a FastAPI dependency."""
        try:
            # Verify token
            payload = self.jwt_manager.verify_token(credentials.credentials)

            if payload.get("type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type. Expected 'access' token.",
                )

            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: User ID missing."
                )

            # Get user from database
            async with self.permission_manager.db_pool.acquire() as conn:
                user_data = await conn.fetchrow(
                    """
                    SELECT id, username, email, password_hash, is_active, created_at, last_login,
                           mfa_enabled, mfa_secret
                    FROM users
                    WHERE id = $1
                """,
                    user_id,
                )

                if not user_data:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="User not found or deleted.",
                    )

                if not user_data["is_active"]:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="User account is inactive.",
                    )

                # Get user roles
                roles = await self.permission_manager.get_user_roles(user_id)

                return User(
                    id=str(user_data["id"]),
                    username=user_data["username"],
                    email=user_data["email"],
                    password_hash=user_data["password_hash"],
                    roles=roles,
                    is_active=user_data["is_active"],
                    created_at=user_data["created_at"],
                    last_login=user_data["last_login"],
                    mfa_enabled=user_data.get("mfa_enabled", False),
                    mfa_secret=user_data.get("mfa_secret"),
                )

        except HTTPException:
            # Re-raise explicit HTTPExceptions (e.g., from jwt_manager.verify_token)
            raise
        except Exception as e:
            logger.error(f"Authentication error during get_current_user for user ID '{user_id}': {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed"
            )

    def require_permission(self, resource: str, action: str):
        """Decorator to require specific permission. Returns a FastAPI dependency."""

        async def dependency(current_user: User = Depends(self.get_current_user)):
            if not await self.permission_manager.user_has_permission(
                current_user.id, resource, action
            ):
                logger.warning(
                    f"User '{current_user.username}' (ID: {current_user.id}) "
                    f"attempted to access '{resource}:{action}' without permission."
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions: '{action}' on '{resource}' required.",
                )
            return current_user

        return dependency

    def require_role(self, role: str):
        """Decorator to require specific role. Returns a FastAPI dependency."""

        async def dependency(current_user: User = Depends(self.get_current_user)):
            if role not in current_user.roles:
                logger.warning(
                    f"User '{current_user.username}' (ID: {current_user.id}) "
                    f"attempted to access resource requiring role '{role}'."
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{role}' required.",
                )
            return current_user

        return dependency

    async def check_rate_limit(
        self, key: str, limit: int, window: int, burst: Optional[int] = None
    ):
        """Check rate limit and raise exception if exceeded"""
        result = await self.rate_limiter.is_allowed(key, limit, window, burst)

        if not result["allowed"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(result.get("retry_after", window))},
            )

        return result


# --- Global SecurityManager Instance Management for Module-Level Dependencies ---

# Placeholder for the global SecurityManager instance.
# This must be set by the application during its startup phase.
_global_security_manager_instance: Optional[SecurityManager] = None


def set_global_security_manager(manager: SecurityManager):
    """
    Sets the global SecurityManager instance for module-level dependencies like `get_current_user`.
    This function should be called once during application startup (e.g., in FastAPI's on_event("startup")).

    Args:
        manager: An initialized SecurityManager instance.
    """
    global _global_security_manager_instance
    if _global_security_manager_instance is not None:
        logger.warning("Overwriting existing global SecurityManager instance.")
    _global_security_manager_instance = manager
    logger.info("Global SecurityManager instance has been set.")


def get_global_security_manager() -> SecurityManager:
    """
    Retrieves the globally configured SecurityManager instance.
    This function is intended for internal use by module-level dependencies.

    Raises:
        RuntimeError: If the SecurityManager has not been initialized globally
                      by calling `set_global_security_manager`.
    """
    if _global_security_manager_instance is None:
        error_msg = (
            "SecurityManager has not been initialized. "
            "Please call `auth.set_global_security_manager(manager_instance)` "
            "during your application's startup phase (e.g., FastAPI's on_event('startup')). "
            "This is crucial for module-level dependencies like `auth.get_current_user` to function."
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    return _global_security_manager_instance


# Standalone dependency for FastAPI
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
) -> User:
    """
    Standalone FastAPI dependency to get the current authenticated user.

    This dependency relies on a globally configured `SecurityManager` instance.
    Ensure `auth.set_global_security_manager()` is called with an initialized
    `SecurityManager` instance during your application's startup.

    Raises:
        HTTPException: If authentication fails, token is invalid/expired,
                       or if the SecurityManager is not initialized.
    """
    try:
        # Retrieve the globally configured SecurityManager instance
        manager = get_global_security_manager()
        # Delegate to the SecurityManager's method for actual logic
        return await manager.get_current_user(credentials)
    except HTTPException:
        # Re-raise HTTPExceptions as they are intended responses for authentication failures
        raise
    except RuntimeError as re:
        # Catch RuntimeError from get_global_security_manager if not initialized
        logger.error(f"Configuration error for get_current_user dependency: {re}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error: Authentication manager not set.",
        ) from re
    except Exception as e:
        # Catch any other unexpected errors during user retrieval
        logger.error(f"Unexpected error in standalone get_current_user dependency: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed due to an internal server error.",
        ) from e
