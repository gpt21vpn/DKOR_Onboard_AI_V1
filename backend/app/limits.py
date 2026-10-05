"""Антиспам и защита платных API.

Три независимых слоя, потому что каждый закрывает своё:
  1. скользящие окна на IP и на сессию: против серий запросов подряд;
  2. один запрос в обработке на сессию: против двойных отправок и скриптов;
  3. суточный бюджет на всё приложение: против любого обхода (смена IP,
     подделка X-Forwarded-For). Когда бюджет кончился, чат не падает,
     а переключается на локальный режим без внешних вызовов и без расходов.

Состояние в памяти процесса. Для одного контейнера (Render) этого достаточно;
при нескольких воркерах лимиты считаются отдельно в каждом.
"""
from __future__ import annotations

import asyncio
import hmac
import time
from collections import Counter, OrderedDict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import HTTPException, Request


class SlidingWindow:
    """Лимит по нескольким окнам сразу: [(5, 60), (40, 3600)] = 5 в минуту и 40 в час."""

    def __init__(self, rules: list[tuple[int, int]], max_keys: int = 20000):
        self.rules = rules
        self.horizon = max(w for _, w in rules)
        self.max_keys = max_keys
        self._hits: "OrderedDict[str, deque[float]]" = OrderedDict()

    def hit(self, key: str, now: float | None = None) -> int:
        """Регистрирует обращение. 0 = можно, иначе через сколько секунд повторить."""
        now = time.monotonic() if now is None else now
        q = self._hits.get(key)
        if q is None:
            q = self._hits[key] = deque()
            if len(self._hits) > self.max_keys:          # потолок памяти: выбрасываем самых старых
                self._hits.popitem(last=False)
        else:
            self._hits.move_to_end(key)
        while q and now - q[0] > self.horizon:
            q.popleft()
        for limit, window in self.rules:
            recent = [t for t in q if now - t <= window]
            if len(recent) >= limit:
                return max(1, int(window - (now - recent[0])) + 1)
        q.append(now)
        return 0


class DailyBudget:
    def __init__(self, caps: dict[str, int]):
        self.caps, self.used, self.day = caps, Counter(), self._today()

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def take(self, kind: str) -> bool:
        if self.day != self._today():
            self.day, self.used = self._today(), Counter()
        cap = self.caps.get(kind)
        if cap is None:
            return True
        if self.used[kind] >= cap:
            return False
        self.used[kind] += 1
        return True


def client_ip(request: Request, trust_proxy: bool) -> str:
    """За прокси Render request.client.host один для всех: берём адрес из X-Forwarded-For.
    Заголовок можно подделать, поэтому на него нельзя опираться одного: есть суточный бюджет."""
    if trust_proxy:
        xff = request.headers.get("x-forwarded-for", "")
        if xff:
            return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class Limits:
    def __init__(self, enabled: bool = True, trust_proxy: bool = False, admin_token: str | None = None,
                 caps: dict[str, int] | None = None):
        self.enabled, self.trust_proxy, self.admin_token = enabled, trust_proxy, admin_token
        self.ip = {
            "chat": SlidingWindow([(8, 60), (60, 3600), (200, 86400)]),
            "stt": SlidingWindow([(4, 60), (20, 3600)]),
            "tts": SlidingWindow([(6, 60), (40, 3600)]),
        }
        self.session = SlidingWindow([(12, 600)])
        self.budget = DailyBudget(caps or {"chat": 400, "stt": 100, "tts": 150})
        self._busy: set[str] = set()

    def _bypass(self, request: Request) -> bool:
        tok = request.headers.get("x-admin-token")
        return bool(self.admin_token) and bool(tok) and hmac.compare_digest(tok, self.admin_token)

    def check(self, request: Request, kind: str, session: str | None = None) -> None:
        if not self.enabled or self._bypass(request):
            return
        retry = self.ip[kind].hit(f"{kind}:{client_ip(request, self.trust_proxy)}")
        if not retry and session and kind == "chat":
            retry = self.session.hit(f"s:{session}")
        if retry:
            raise HTTPException(429, "Слишком много запросов. Подождите немного и повторите.",
                                headers={"Retry-After": str(retry)})

    def spend(self, kind: str) -> bool:
        """True, если суточный бюджет позволяет платный вызов."""
        return (not self.enabled) or self.budget.take(kind)

    @asynccontextmanager
    async def one_at_a_time(self, session: str):
        if not self.enabled:
            yield
            return
        if session in self._busy:
            raise HTTPException(429, "Предыдущий вопрос ещё обрабатывается.", headers={"Retry-After": "3"})
        self._busy.add(session)
        try:
            yield
        finally:
            self._busy.discard(session)
