"""
router.py — kirishni 3 turga tasniflaydi (AI asosida, keyword fallback bilan):
  - "action" : kompyuterda HAQIQIY amal (papka/fayl yaratish, buyruq bajarish) -> opencode agent
  - "task"   : parallel orkestr (faqat /task bilan majburan)
  - "chat"   : oddiy suhbat (standart)

AI classifier model qotsa -> keyword-based fallback ga o'tadi.
"""

from . import engine

_CLASSIFY_PROMPT = """You are a classifier. Given a user message, return exactly one word:
- "action" if the user wants to CREATE/DELETE/MODIFY files/folders, INSTALL packages, RUN commands, CLONE repos, or do anything on the computer
- "task" if the user wants research, analysis, planning, explanation, multi-step thinking, or complex multi-part work
- "chat" for casual conversation, greetings, questions, small talk, or simple answers

Respond with ONLY the word: action, task, or chat.

User: {text}"""

ACTION_KW = [
    "yarat", "papka", "jild", "fayl", "o'chir", "ochir", "ko'chir", "kochir",
    "nusxa", "o'rnat", "ornat", "install", "ishga tushur", "bajar", "yukla",
    "klonla", "clone", "mkdir", "touch", "folder", "file", "create", "delete",
    "remove", "download", "git ", "npm ", "pip ", "kompyuter", "terminalda",
    "skript yoz", "kod yozib", "papkaga", "faylga", "saqlab qo'y", "yozib qo'y",
]


async def _ai_classify(text: str, cfg: dict) -> str | None:
    """AI model bilan klassifikatsiya qiladi. Hech narsa qaytarmasa None."""
    candidates = [cfg["router"]["model"]] + cfg["router"].get("fallbacks", [])
    timeout = cfg["limits"]["timeout_seconds"]
    for model in candidates:
        res = await engine.run_model(model, _CLASSIFY_PROMPT.format(text=text),
                                     timeout=timeout)
        if res["ok"]:
            t = res["text"].strip().lower().rstrip(".")
            if t in ("action", "task", "chat"):
                return t
    return None


def _kw_classify(text: str) -> str:
    t = text.lower().strip()
    if any(k in t for k in ACTION_KW):
        return "action"
    return "chat"


def classify(text: str, cfg: dict | None = None) -> str:
    import asyncio

    t = text.lower().strip()
    if t.startswith("/task"):
        return "task"
    if t.startswith("/do"):
        return "action"

    # AI classification (asalda, keyin keyword fallback)
    if cfg:
        try:
            result = asyncio.run(_ai_classify(text, cfg))
            if result:
                return result
        except Exception:
            pass

    return _kw_classify(text)
