"""
Policy engines for authorization.

Available engines:
- simple: Just is_admin flag (default)
- rbac: Role-based with permissions (requires extensions.auth.rbac)
"""

from .simple import SimplePolicyEngine

__all__ = ["SimplePolicyEngine"]
