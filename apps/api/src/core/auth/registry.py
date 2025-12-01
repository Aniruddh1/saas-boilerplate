"""
Authorization plugin registry.

Allows registering policy engines, scope providers, and conditions
without modifying core code. Implementations register themselves
using decorators.

Usage:
    @AuthRegistry.policy_engine("my_engine")
    class MyPolicyEngine(PolicyEngine):
        ...

    # Later, get by name:
    engine = AuthRegistry.get_policy_engine("my_engine")
"""

from typing import Type, Callable, Any
from .interfaces import PolicyEngine, ScopeProvider, ConditionEvaluator


class AuthRegistry:
    """
    Central registry for authorization components.

    Components register themselves using decorators.
    This enables extensibility without modifying factory code.
    """

    _policy_engines: dict[str, Type[PolicyEngine]] = {}
    _scope_providers: dict[str, Type[ScopeProvider]] = {}
    _condition_evaluators: dict[str, Type[ConditionEvaluator]] = {}

    # ============================================================
    # REGISTRATION DECORATORS
    # ============================================================

    @classmethod
    def policy_engine(cls, name: str) -> Callable[[Type[PolicyEngine]], Type[PolicyEngine]]:
        """
        Decorator to register a policy engine.

        Usage:
            @AuthRegistry.policy_engine("rbac")
            class RBACPolicyEngine(PolicyEngine):
                ...
        """
        def decorator(engine_class: Type[PolicyEngine]) -> Type[PolicyEngine]:
            cls._policy_engines[name] = engine_class
            return engine_class
        return decorator

    @classmethod
    def scope_provider(cls, name: str) -> Callable[[Type[ScopeProvider]], Type[ScopeProvider]]:
        """
        Decorator to register a scope provider.

        Usage:
            @AuthRegistry.scope_provider("hierarchical")
            class HierarchicalScopeProvider(ScopeProvider):
                ...
        """
        def decorator(provider_class: Type[ScopeProvider]) -> Type[ScopeProvider]:
            cls._scope_providers[name] = provider_class
            return provider_class
        return decorator

    @classmethod
    def condition(cls, condition_type: str) -> Callable[[Type[ConditionEvaluator]], Type[ConditionEvaluator]]:
        """
        Decorator to register a condition evaluator.

        Usage:
            @AuthRegistry.condition("max_amount")
            class MaxAmountCondition(ConditionEvaluator):
                ...
        """
        def decorator(evaluator_class: Type[ConditionEvaluator]) -> Type[ConditionEvaluator]:
            cls._condition_evaluators[condition_type] = evaluator_class
            return evaluator_class
        return decorator

    # ============================================================
    # GETTERS
    # ============================================================

    @classmethod
    def get_policy_engine(cls, name: str, **kwargs: Any) -> PolicyEngine:
        """
        Get a policy engine by name.

        Args:
            name: Registered name of the engine
            **kwargs: Arguments to pass to engine constructor

        Raises:
            ValueError: If engine not found
        """
        engine_class = cls._policy_engines.get(name)
        if not engine_class:
            available = list(cls._policy_engines.keys())
            raise ValueError(
                f"Unknown policy engine: '{name}'. "
                f"Available: {available}"
            )
        return engine_class(**kwargs)

    @classmethod
    def get_scope_provider(cls, name: str, **kwargs: Any) -> ScopeProvider:
        """
        Get a scope provider by name.

        Args:
            name: Registered name of the provider
            **kwargs: Arguments to pass to provider constructor

        Raises:
            ValueError: If provider not found
        """
        provider_class = cls._scope_providers.get(name)
        if not provider_class:
            available = list(cls._scope_providers.keys())
            raise ValueError(
                f"Unknown scope provider: '{name}'. "
                f"Available: {available}"
            )
        return provider_class(**kwargs)

    @classmethod
    def get_condition_evaluator(cls, condition_type: str, **kwargs: Any) -> ConditionEvaluator:
        """
        Get a condition evaluator by type.

        Args:
            condition_type: Registered type of the condition
            **kwargs: Arguments to pass to evaluator constructor

        Raises:
            ValueError: If condition type not found
        """
        evaluator_class = cls._condition_evaluators.get(condition_type)
        if not evaluator_class:
            available = list(cls._condition_evaluators.keys())
            raise ValueError(
                f"Unknown condition type: '{condition_type}'. "
                f"Available: {available}"
            )
        return evaluator_class(**kwargs)

    # ============================================================
    # INTROSPECTION
    # ============================================================

    @classmethod
    def list_policy_engines(cls) -> list[str]:
        """List all registered policy engine names."""
        return list(cls._policy_engines.keys())

    @classmethod
    def list_scope_providers(cls) -> list[str]:
        """List all registered scope provider names."""
        return list(cls._scope_providers.keys())

    @classmethod
    def list_conditions(cls) -> list[str]:
        """List all registered condition types."""
        return list(cls._condition_evaluators.keys())

    @classmethod
    def has_policy_engine(cls, name: str) -> bool:
        """Check if a policy engine is registered."""
        return name in cls._policy_engines

    @classmethod
    def has_scope_provider(cls, name: str) -> bool:
        """Check if a scope provider is registered."""
        return name in cls._scope_providers

    @classmethod
    def has_condition(cls, condition_type: str) -> bool:
        """Check if a condition type is registered."""
        return condition_type in cls._condition_evaluators
