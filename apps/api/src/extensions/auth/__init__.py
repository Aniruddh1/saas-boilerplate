"""
Authorization Extensions.

Optional extensions for the core authorization system.
Import the extensions you need to register them.

Available:
- rbac: Role-based access control with permissions
- scoping: Hierarchical data scoping (coming soon)

Usage:
    # In main.py or app startup:
    from src.extensions.auth import rbac  # Registers RBAC engine
"""

# Extensions are imported on-demand to register themselves
