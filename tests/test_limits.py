import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import pytest
from fastapi.testclient import TestClient
from app.limits import SlidingWindow, DailyBudget, Limits
from app import main as m


# ---------- чистая логика ----------
def test_window_blocks_after_limit_and_recovers():
    w = SlidingWindow([(3, 60)])
    assert [w.hit("a", now=t) for t in (0, 1, 2)] == [0, 0, 0]
    assert w.hit("a", now=3) > 0                 # четвёртый в окне отклонён
    assert w.hit("b", now=3) == 0                # другой ключ не затронут
    assert w.hit("a", now=70) == 0               # окно прошло

def test_window_multiple_rules():
    w = SlidingWindow([(2, 10), (3, 100)])
    assert w.hit("k", now=0) == 0 and w.hit("k", now=1) == 0
    assert w.hit("k", now=2) > 0                 # минутное правило
    assert w.hit("k", now=20) == 0               # короткое окно прошло, третий из трёх
    assert w.hit("k", now=40) > 0                # длинное правило

def test_window_memory_is_capped():
    w = SlidingWindow([(1, 60)], max_keys=100)
    for i in range(1000): w.hit(f"ip{i}", now=i)
    assert len(w._hits) <= 100

def test_budget_runs_out_and_counts_by_kind():
    b = DailyBudget({"chat": 2})
    assert [b.take("chat") for _ in range(3)] == [True, True, False]
    assert b.take("tts") is True                 # вид без лимита

# ---------- через HTTP ----------
@pytest.fixture()
def client():
    m.limits = Limits(enabled=True)               # чистое состояние на каждый тест
    return TestClient(m.app)

def body(msg="Как оформить отпуск?", sid="sess-aaaa"):
    return {"message": msg, "session_id": sid, "provider": "local"}

def test_normal_chat_works(client):
    r = client.post("/api/chat", json=body())
    assert r.status_code == 200 and r.json()["provider"] == "local"

def test_long_message_rejected(client):
    assert client.post("/api/chat", json=body("подскажи " * 100)).status_code == 422   # 900 знаков

def test_bad_session_id_rejected(client):
    assert client.post("/api/chat", json=body(sid="../../etc")).status_code == 422
    assert client.post("/api/chat", json=body(sid="x" * 65)).status_code == 422

def test_burst_gets_429_with_retry_after(client):
    codes = [client.post("/api/chat", json=body(sid=f"s-{i:04d}")).status_code for i in range(12)]
    assert codes[:8] == [200] * 8 and 429 in codes[8:]
    r = client.post("/api/chat", json=body(sid="s-9999"))
    assert r.status_code == 429 and int(r.headers["retry-after"]) >= 1

def test_one_request_at_a_time_per_session(client):
    import asyncio
    async def run():
        async with m.limits.one_at_a_time("same-session"):
            with pytest.raises(Exception) as e:
                async with m.limits.one_at_a_time("same-session"): pass
            assert "429" in str(e.value) or getattr(e.value, "status_code", 0) == 429
        async with m.limits.one_at_a_time("same-session"): pass     # после выхода снова можно
    asyncio.run(run())

def test_budget_exhausted_falls_back_to_local_not_error(client):
    m.limits = Limits(enabled=True, caps={"chat": 0})
    r = client.post("/api/chat", json={"message": "Как оформить отпуск?", "session_id": "sess-bbbb", "provider": "auto"})
    assert r.status_code == 200 and r.json()["provider"] == "local"

def test_oversized_audio_rejected(client):
    big = b"\x00" * (2 * 1024 * 1024 + 10)
    r = client.post("/api/voice/transcribe", files={"file": ("v.webm", big, "audio/webm")})
    assert r.status_code == 413

def test_non_audio_rejected(client):
    r = client.post("/api/voice/transcribe", files={"file": ("x.txt", b"hello", "text/plain")})
    assert r.status_code == 415

def test_forwarded_header_ignored_unless_trusted(client):
    for i in range(8): client.post("/api/chat", json=body(sid=f"t-{i:04d}"), headers={"x-forwarded-for": f"1.1.1.{i}"})
    assert client.post("/api/chat", json=body(sid="t-9999"), headers={"x-forwarded-for": "9.9.9.9"}).status_code == 429

def test_errors_do_not_leak_provider_text(client, monkeypatch):
    async def boom(*a, **k): raise RuntimeError("Incorrect API key provided: sk-SECRET123")
    monkeypatch.setattr(m.chat_service, "answer", boom)
    r = client.post("/api/chat", json=body())
    assert r.status_code == 502 and "sk-SECRET123" not in r.text

def test_admin_reindex_refuses_default_token(client):
    assert client.post("/api/admin/reindex", headers={"x-admin-token": "change-me"}).status_code == 403
