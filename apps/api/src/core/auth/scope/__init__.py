"""
Scope providers for data access filtering.

Available providers:
- none: No filtering (default)
- ownership: User sees own records only
- hierarchical: Organization hierarchy (requires extensions.auth.scoping)
"""

from .none import NoScopeProvider, OwnershipScopeProvider

__all__ = ["NoScopeProvider", "OwnershipScopeProvider"]
