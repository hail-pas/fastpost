from typing import Any, Dict
from contextvars import ContextVar

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from starlette.types import Send, Scope, ASGIApp, Receive


class Globals:
    __slots__ = ("_vars",)

    _vars: Dict[str, ContextVar]

    def __init__(self) -> None:
        object.__setattr__(self, "_vars", {})

    def reset(self) -> None:
        for _name, var in self._vars.items():
            var.set(None)

    def _ensure_var(self, item: str) -> None:
        if item not in self._vars:
            self._vars[item] = ContextVar(f"globals:{item}")
            self._vars[item].set(None)

    def __getattr__(self, item: str) -> Any:
        self._ensure_var(item)
        try:
            return self._vars[item].get()
        except LookupError:
            self._vars[item].set(None)
            return None

    def __setattr__(self, item: str, value: Any) -> None:
        self._ensure_var(item)
        self._vars[item].set(value)


class GlobalsMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        g.reset()
        await self.app(scope, receive, send)


g = Globals()
