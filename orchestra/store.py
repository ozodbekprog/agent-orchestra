"""
store.py — suhbat XOTIRASI + SESSION STATISTIKASI.
Tarixni JSON faylga saqlaydi (sessiyalar orasida eslab qoladi).
"""
import json
import os
import time

HIST = os.path.join(os.path.dirname(__file__), "..", ".history.json")
STATE = os.path.join(os.path.dirname(__file__), "..", ".state.json")

# Session statistika fayli
STATS = os.path.join(os.path.dirname(__file__), "..", ".stats.json")


def load() -> list:
    if os.path.exists(HIST):
        try:
            return json.load(open(HIST, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
    return []


def save(messages: list):
    try:
        json.dump(messages, open(HIST, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    except OSError:
        pass


def clear():
    if os.path.exists(HIST):
        os.remove(HIST)


def load_state() -> dict:
    """Tanlangan chat modeli kabi sozlamalar (sessiyalar orasida eslanadi)."""
    if os.path.exists(STATE):
        try:
            return json.load(open(STATE, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_state(state: dict):
    try:
        json.dump(state, open(STATE, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    except OSError:
        pass


# ---------- Session statistikasi ----------

def _default_stats() -> dict:
    return {
        "session_count": 0,
        "total_queries": 0,
        "total_chat": 0,
        "total_action": 0,
        "total_task": 0,
        "started_at": time.time(),
        "last_seen": time.time(),
        "models_used": {},
    }


def load_stats() -> dict:
    if os.path.exists(STATS):
        try:
            return json.load(open(STATS, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return _default_stats()
    return _default_stats()


def save_stats(stats: dict):
    stats["last_seen"] = time.time()
    try:
        json.dump(stats, open(STATS, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    except OSError:
        pass


def record_query(mode: str, model: str = ""):
    st = load_stats()
    st["total_queries"] = st.get("total_queries", 0) + 1
    key = f"total_{mode}"
    if key in st:
        st[key] += 1
    if model:
        mu = st.setdefault("models_used", {})
        mu[model] = mu.get(model, 0) + 1
    save_stats(st)
