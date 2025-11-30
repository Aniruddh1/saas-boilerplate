"""
Hook manager for lifecycle events.
"""
from __future__ import annotations

from typing import Callable, Any, Awaitable, TypeVar, ParamSpec
from dataclasses import dataclass, field
from enum import IntEnum
from collections import defaultdict
import asyncio
import logging

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


class HookPriority(IntEnum):
    """Hook execution priority (lower runs first)."""
    FIRST = 0
    EARLY = 25
    NORMAL = 50
    LATE = 75
    LAST = 100


@dataclass
class Hook:
    """Registered hook information."""
    name: str
    handler: Callable[..., Awaitable[Any]]
    priority: HookPriority = HookPriority.NORMAL
    once: bool = False  # Run only once then unregister
    source: str = ""  # Plugin/module that registered this


@dataclass
class HookResult:
    """Result from running hooks."""
    hook_name: str
    results: list[Any] = field(default_factory=list)
    errors: list[tuple[str, Exception]] = field(default_factory=list)
    stopped: bool = False  # Was propagation stopped?


class HookManager:
    """
    Manages lifecycle hooks throughout the application.

    Predefined hooks:
    - app.startup: Application starting
    - app.shutdown: Application shutting down
    - request.before: Before handling request
    - request.after: After handling request
    - user.created: User was created
    - user.updated: User was updated
    - user.deleted: User was deleted
    - auth.login: User logged in
    - auth.logout: User logged out
    - auth.failed: Authentication failed
    - org.created: Organization created
    - project.created: Project created
    - api_key.created: API key generated
    - webhook.sending: About to send webhook
    - webhook.sent: Webhook delivered
    - task.started: Background task started
    - task.completed: Background task completed
    - task.failed: Background task failed

    Example usage:
    ```python
    hooks = HookManager()

    # Register a hook
    @hooks.on("user.created")
    async def send_welcome_email(user: User):
        await email.send_welcome(user.email)

    # Trigger hooks
    await hooks.trigger("user.created", user=new_user)
    ```
    """

    def __init__(self):
        self._hooks: dict[str, list[Hook]] = defaultdict(list)
        self._once_executed: set[str] = set()

    def register(
        self,
        name: str,
        handler: Callable[..., Awaitable[Any]],
        *,
        priority: HookPriority = HookPriority.NORMAL,
        once: bool = False,
        source: str = "",
    ) -> Hook:
        """Register a hook handler."""
        hook = Hook(
            name=name,
            handler=handler,
            priority=priority,
            once=once,
            source=source,
        )

        self._hooks[name].append(hook)
        # Sort by priority
        self._hooks[name].sort(key=lambda h: h.priority)

        logger.debug(f"Registered hook: {name} (priority={priority})")
        return hook

    def unregister(self, name: str, handler: Callable) -> bool:
        """Unregister a hook handler."""
        hooks = self._hooks.get(name, [])
        for i, hook in enumerate(hooks):
            if hook.handler is handler:
                del hooks[i]
                return True
        return False

    def on(
        self,
        name: str,
        *,
        priority: HookPriority = HookPriority.NORMAL,
        once: bool = False,
    ) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
        """Decorator to register a hook handler."""
        def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
            self.register(name, func, priority=priority, once=once)
            return func
        return decorator

    async def trigger(
        self,
        name: str,
        *args,
        stop_on_error: bool = False,
        stop_on_false: bool = False,
        **kwargs,
    ) -> HookResult:
        """
        Trigger all handlers for a hook.

        Args:
            name: Hook name to trigger
            stop_on_error: Stop execution if a handler raises
            stop_on_false: Stop if a handler returns False
            *args, **kwargs: Passed to handlers
        """
        result = HookResult(hook_name=name)
        hooks_to_remove = []

        for hook in self._hooks.get(name, []):
            # Check if once-hook already executed
            hook_id = f"{name}:{id(hook.handler)}"
            if hook.once and hook_id in self._once_executed:
                continue

            try:
                handler_result = await hook.handler(*args, **kwargs)
                result.results.append(handler_result)

                if hook.once:
                    self._once_executed.add(hook_id)
                    hooks_to_remove.append(hook)

                if stop_on_false and handler_result is False:
                    result.stopped = True
                    break

            except Exception as e:
                result.errors.append((hook.source or str(hook.handler), e))
                logger.error(f"Hook {name} handler error: {e}")

                if stop_on_error:
                    result.stopped = True
                    break

        # Remove once-hooks
        for hook in hooks_to_remove:
            self._hooks[name].remove(hook)

        return result

    async def trigger_parallel(
        self,
        name: str,
        *args,
        **kwargs,
    ) -> HookResult:
        """Trigger all handlers in parallel."""
        result = HookResult(hook_name=name)
        hooks = self._hooks.get(name, [])

        if not hooks:
            return result

        async def run_hook(hook: Hook) -> tuple[Any, Exception | None]:
            try:
                return await hook.handler(*args, **kwargs), None
            except Exception as e:
                return None, e

        tasks = [run_hook(hook) for hook in hooks]
        results = await asyncio.gather(*tasks)

        for hook, (res, err) in zip(hooks, results):
            if err:
                result.errors.append((hook.source or str(hook.handler), err))
            else:
                result.results.append(res)

        return result

    async def filter(
        self,
        name: str,
        value: Any,
        *args,
        **kwargs,
    ) -> Any:
        """
        Run hooks as filters, passing value through each handler.

        Each handler receives the value from the previous handler
        and should return the (possibly modified) value.
        """
        for hook in self._hooks.get(name, []):
            try:
                value = await hook.handler(value, *args, **kwargs)
            except Exception as e:
                logger.error(f"Filter hook {name} error: {e}")

        return value

    def has_hooks(self, name: str) -> bool:
        """Check if any hooks are registered for name."""
        return bool(self._hooks.get(name))

    def list_hooks(self, name: str | None = None) -> list[str]:
        """List registered hook names, optionally filtered by prefix."""
        names = list(self._hooks.keys())
        if name:
            names = [n for n in names if n.startswith(name)]
        return sorted(names)

    def clear(self, name: str | None = None) -> None:
        """Clear hooks. If name given, clear only that hook."""
        if name:
            self._hooks.pop(name, None)
        else:
            self._hooks.clear()
            self._once_executed.clear()


# Global hook manager instance
hooks = HookManager()
