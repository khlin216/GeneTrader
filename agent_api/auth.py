"""
Authentication for Agent API.

Provides API key-based authentication for securing the agent API endpoints.
"""

import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from functools import wraps
from utils.logging_config import logger


@dataclass
class APIKey:
    """Represents an API key."""
    key_id: str
    key_hash: str
    name: str
    permissions: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    is_active: bool = True


class AuthManager:
    """
    Manages API key authentication.

    Features:
    - Generate and validate API keys
    - Permission-based access control
    - Key rotation support
    - Rate limiting
    """

    def __init__(
        self,
        master_key: Optional[str] = None,
        rate_limit_per_minute: int = 60
    ):
        """
        Initialize auth manager.

        Args:
            master_key: Master API key (falls back to env var AGENT_API_KEY)
            rate_limit_per_minute: Rate limit per API key
        """
        self.master_key = master_key or os.environ.get('AGENT_API_KEY', '')
        self.rate_limit_per_minute = rate_limit_per_minute

        self._api_keys: Dict[str, APIKey] = {}
        self._rate_limits: Dict[str, List[float]] = {}

        # Create master key entry if provided
        if self.master_key:
            self._add_master_key()

    def _add_master_key(self) -> None:
        """Add the master key to the registry."""
        key_hash = self._hash_key(self.master_key)
        self._api_keys['master'] = APIKey(
            key_id='master',
            key_hash=key_hash,
            name='Master Key',
            permissions=['*'],  # All permissions
            created_at=datetime.now(),
        )

    def _hash_key(self, key: str) -> str:
        """Hash an API key."""
        return hashlib.sha256(key.encode()).hexdigest()

    def generate_key(
        self,
        name: str,
        permissions: Optional[List[str]] = None,
        expires_days: Optional[int] = None
    ) -> tuple[str, APIKey]:
        """
        Generate a new API key.

        Args:
            name: Name for the key
            permissions: List of permissions (default: read-only)
            expires_days: Days until expiration

        Returns:
            (raw_key, APIKey object)
        """
        # Generate secure random key
        raw_key = secrets.token_urlsafe(32)
        key_id = secrets.token_hex(8)
        key_hash = self._hash_key(raw_key)

        expires_at = None
        if expires_days:
            expires_at = datetime.now() + timedelta(days=expires_days)

        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            permissions=permissions or ['read'],
            created_at=datetime.now(),
            expires_at=expires_at,
        )

        self._api_keys[key_id] = api_key

        logger.info(f"Generated API key: {name} (id: {key_id})")
        return raw_key, api_key

    def validate_key(self, raw_key: str) -> Optional[APIKey]:
        """
        Validate an API key.

        Args:
            raw_key: The raw API key string

        Returns:
            APIKey if valid, None otherwise
        """
        if not raw_key:
            return None

        key_hash = self._hash_key(raw_key)

        for api_key in self._api_keys.values():
            if hmac.compare_digest(api_key.key_hash, key_hash):
                # Check if active
                if not api_key.is_active:
                    return None

                # Check expiration
                if api_key.expires_at and datetime.now() > api_key.expires_at:
                    return None

                # Update last used
                api_key.last_used = datetime.now()

                return api_key

        return None

    def check_permission(self, api_key: APIKey, permission: str) -> bool:
        """
        Check if an API key has a specific permission.

        Args:
            api_key: The API key
            permission: Permission to check

        Returns:
            True if permitted
        """
        if '*' in api_key.permissions:
            return True

        return permission in api_key.permissions

    def check_rate_limit(self, key_id: str) -> bool:
        """
        Check if the API key is within rate limits.

        Args:
            key_id: API key ID

        Returns:
            True if within limit
        """
        now = time.time()
        window_start = now - 60  # 1 minute window

        if key_id not in self._rate_limits:
            self._rate_limits[key_id] = []

        # Clean old entries
        self._rate_limits[key_id] = [
            t for t in self._rate_limits[key_id]
            if t > window_start
        ]

        # Check limit
        if len(self._rate_limits[key_id]) >= self.rate_limit_per_minute:
            return False

        # Record request
        self._rate_limits[key_id].append(now)
        return True

    def revoke_key(self, key_id: str) -> bool:
        """
        Revoke an API key.

        Args:
            key_id: Key ID to revoke

        Returns:
            True if revoked
        """
        if key_id in self._api_keys:
            self._api_keys[key_id].is_active = False
            logger.info(f"Revoked API key: {key_id}")
            return True
        return False

    def list_keys(self) -> List[Dict[str, Any]]:
        """List all API keys (without hashes)."""
        return [
            {
                'key_id': k.key_id,
                'name': k.name,
                'permissions': k.permissions,
                'created_at': k.created_at.isoformat(),
                'expires_at': k.expires_at.isoformat() if k.expires_at else None,
                'is_active': k.is_active,
                'last_used': k.last_used.isoformat() if k.last_used else None,
            }
            for k in self._api_keys.values()
        ]


class APIKeyAuth:
    """
    FastAPI-compatible authentication dependency.

    Usage with FastAPI:
        auth = APIKeyAuth(auth_manager)

        @app.get("/protected")
        async def protected_endpoint(api_key: APIKey = Depends(auth)):
            return {"message": "Authenticated"}
    """

    def __init__(
        self,
        auth_manager: AuthManager,
        required_permission: Optional[str] = None
    ):
        """
        Initialize auth dependency.

        Args:
            auth_manager: Authentication manager
            required_permission: Permission required for this endpoint
        """
        self.auth_manager = auth_manager
        self.required_permission = required_permission

    def __call__(self, api_key: str) -> Optional[APIKey]:
        """
        Validate API key from request.

        This is designed to be used as a FastAPI dependency.
        """
        key = self.auth_manager.validate_key(api_key)

        if not key:
            return None

        if self.required_permission:
            if not self.auth_manager.check_permission(key, self.required_permission):
                return None

        if not self.auth_manager.check_rate_limit(key.key_id):
            return None

        return key


def require_auth(auth_manager: AuthManager, permission: Optional[str] = None):
    """
    Decorator for requiring authentication.

    Usage:
        @require_auth(auth_manager, 'write')
        def my_endpoint(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract API key from kwargs or headers
            api_key_str = kwargs.pop('api_key', None)

            if not api_key_str:
                return {'error': 'API key required'}, 401

            api_key = auth_manager.validate_key(api_key_str)

            if not api_key:
                return {'error': 'Invalid API key'}, 401

            if permission and not auth_manager.check_permission(api_key, permission):
                return {'error': 'Permission denied'}, 403

            if not auth_manager.check_rate_limit(api_key.key_id):
                return {'error': 'Rate limit exceeded'}, 429

            kwargs['api_key'] = api_key
            return func(*args, **kwargs)

        return wrapper
    return decorator
