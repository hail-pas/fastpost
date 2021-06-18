from typing import Any, Dict, Optional
from contextvars import ContextVar, Token

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from starlette.types import Send, Scope, ASGIApp, Receive

from common.redis import AsyncRedisUtil
from db import db

PreGlobals = {
    "redis": AsyncRedisUtil,
    "session": db.session,  # type: AsyncSession
    "engine": db.engine  # type: AsyncEngine
}


class Globals:
    __slots__ = ("_vars", "_reset_tokens")

    _vars: Dict[str, ContextVar]
    _reset_tokens: Dict[str, Token]

    def __init__(self) -> None:
        object.__setattr__(self, "_vars", {})
        object.__setattr__(self, '_reset_tokens', {})

    def initialize(self):
        for item, value in PreGlobals.items():
            self._ensure_var(item)
            self._vars[item].set(value)

    def session(self) -> Optional[AsyncSession]:
        self._ensure_var("session")
        try:
            return self._vars["session"].get()
        except LookupError:
            self._vars["session"].set(None)
            return None

    def engine(self) -> Optional[AsyncEngine]:
        self._ensure_var("engine")
        try:
            return self._vars["engine"].get()
        except LookupError:
            self._vars["engine"].set(None)
            return None

    def redis(self) -> Optional[AsyncRedisUtil]:
        self._ensure_var("redis")
        try:
            return self._vars["redis"].get()
        except LookupError:
            self._vars["redis"].set(None)
            return None

    def reset(self) -> None:
        for _name, var in self._vars.items():
            try:
                var.reset(self._reset_tokens[_name])
                # ValueError will be thrown if the reset() happens in
                # a different context compared to the original set().
                # Then just set to None for this new context.
            except ValueError:
                var.set(None)

    def _ensure_var(self, item: str) -> None:
        if item not in self._vars:
            self._vars[item] = ContextVar(f"globals:{item}", default=None)
            self._reset_tokens[item] = self._vars[item].set(None)

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
        g.initialize()
        await self.app(scope, receive, send)


g = Globals()
