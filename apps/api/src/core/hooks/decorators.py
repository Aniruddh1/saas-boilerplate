"""
Decorator utilities for hooks.
"""

from typing import Callable, Any, Awaitable, TypeVar, ParamSpec
from functools import wraps

from .manager import hooks, HookPriority

P = ParamSpec("P")
R = TypeVar("R")


def hook(
    name: str,
    *,
    priority: HookPriority = HookPriority.NORMAL,
    once: bool = False,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """
    Decorator to register a function as a hook handler.

    Example:
    ```python
    @hook("user.created")
    async def on_user_created(user: User):
        await send_welcome_email(user)
    ```
    """
    return hooks.on(name, priority=priority, once=once)


def before(
    hook_name: str,
    *,
    priority: HookPriority = HookPriority.NORMAL,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """
    Register a 'before' hook for an action.

    Example:
    ```python
    @before("user.delete")
    async def backup_user_data(user_id: str):
        await backup_service.backup(user_id)
    ```
    """
    return hooks.on(f"{hook_name}.before", priority=priority)


def after(
    hook_name: str,
    *,
    priority: HookPriority = HookPriority.NORMAL,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """
    Register an 'after' hook for an action.

    Example:
    ```python
    @after("user.create")
    async def send_analytics(user: User):
        await analytics.track("user_created", user_id=user.id)
    ```
    """
    return hooks.on(f"{hook_name}.after", priority=priority)


def hookable(
    name: str,
) -> Callable[
    [Callable[P, Awaitable[R]]],
    Callable[P, Awaitable[R]],
]:
    """
    Make a function hookable with before/after events.

    Automatically triggers:
    - {name}.before with function arguments
    - {name}.after with function result

    Example:
    ```python
    @hookable("user.create")
    async def create_user(data: UserCreate) -> User:
        # Before hooks run here with (data,)
        user = await user_repo.create(data)
        # After hooks run here with (user,)
        return user
    ```
    """
    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Trigger before hooks
            before_result = await hooks.trigger(
                f"{name}.before",
                *args,
                stop_on_false=True,
                **kwargs,
            )

            # If before hook returned False, abort
            if before_result.stopped:
                raise HookAbortError(f"Hook {name}.before aborted execution")

            # Run the actual function
            result = await func(*args, **kwargs)

            # Trigger after hooks with result
            await hooks.trigger(f"{name}.after", result, *args, **kwargs)

            return result

        return wrapper

    return decorator


class HookAbortError(Exception):
    """Raised when a before hook aborts execution."""
    pass


def emit(name: str) -> Callable[
    [Callable[P, Awaitable[R]]],
    Callable[P, Awaitable[R]],
]:
    """
    Emit an event after function completes.

    Simpler than @hookable - just emits after, no before hook.

    Example:
    ```python
    @emit("user.updated")
    async def update_user(user_id: str, data: UserUpdate) -> User:
        ...
    ```
    """
    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            result = await func(*args, **kwargs)
            # Fire and forget - don't wait for hooks
            await hooks.trigger(name, result, *args, **kwargs)
            return result
        return wrapper
    return decorator
