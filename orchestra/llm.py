"""
llm.py — OpenRouter API'ga TO'G'RIDAN-TO'G'RI (tez) chat chaqiruvi.
opencode'ning sekin "cold start"isiz — oddiy suhbat uchun. Kalit auth.json'dan olinadi.
Asosiy model qotsa/429 bersa, fallback modellar bilan urinadi.
"""
import json
import os
import urllib.error
import urllib.request

AUTH = os.path.expanduser("~/.local/share/opencode/auth.json")
API = "https://openrouter.ai/api/v1/chat/completions"


def _key() -> str:
    return json.load(open(AUTH))["openrouter"]["key"]


def _call(model: str, messages: list, timeout: int) -> str:
    mid = model.split("openrouter/", 1)[-1]  # API'da prefiks yo'q
    body = {"model": mid, "messages": messages}
    req = urllib.request.Request(
        API, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {_key()}",
                 "Content-Type": "application/json",
                 "X-Title": "agent-orchestra"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    return d["choices"][0]["message"]["content"]


def chat(messages: list, cfg: dict):
    """(javob_matni, ishlatilgan_model) qaytaradi. Hech biri ishlamasa xato matni."""
    models = [cfg["chat"]["model"]] + cfg["chat"].get("fallbacks", [])
    timeout = cfg["chat"].get("timeout_seconds", 60)
    last = ""
    for m in models:
        try:
            txt = _call(m, messages, timeout)
            if txt and txt.strip():
                return txt.strip(), m
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
        except Exception as e:
            last = str(e)[:120]
    return f"[Kechirasiz ser, modellar javob bermadi: {last}]", "none"
