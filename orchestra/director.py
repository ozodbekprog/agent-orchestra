"""
director.py — vazifani qismlarga bo'ladi va yig'adi.
Bo'lish (decompose) director qotsa fallback modellar bilan ketma-ket urinadi.
"""
import json
import re

from . import engine

_DECOMPOSE = """You are a task planner. Split the user's task into 2 to 5 INDEPENDENT \
subtasks that can run in parallel by separate workers. \
Return ONLY a compact JSON array and nothing else. \
Each item: {{"id":"s1","title":"short title","prompt":"full self-contained instruction"}}.
If the task is atomic, return one item.
USER TASK: {task}"""

_AGGREGATE = """You are the lead. Merge the worker results into ONE clear, cohesive final \
answer for the original task. Remove overlap, keep good structure. Answer in the user's language.
ORIGINAL TASK: {task}

WORKER RESULTS:
{results}

Final answer:"""


async def decompose(task: str, cfg: dict) -> list:
    """Director + fallbacklar bilan urinadi; ishonchli JSON qaytmasa, bitta subtask."""
    candidates = [cfg["director"]["model"]] + cfg["director"].get("fallbacks", [])
    timeout = cfg["limits"]["timeout_seconds"]
    for model in candidates:
        res = await engine.run_model(model, _DECOMPOSE.format(task=task), timeout=timeout)
        if res["ok"]:
            parsed = _parse_json_array(res["text"])
            if parsed:
                return parsed
    # hammasi qotsa — vazifani bitta qism sifatida ishlaymiz (tizim to'xtamaydi)
    return [{"id": "s1", "title": "Full task", "prompt": task}]


async def aggregate(task: str, results: list, cfg: dict) -> str:
    blob = "\n\n".join(
        f"### {r.get('title', r['model'])}\n"
        f"{r['text'] if r['ok'] else '[FAILED: ' + r['error'] + ']'}"
        for r in results
    )
    # bitta muvaffaqiyatli natija bo'lsa, yig'ishga hojat yo'q (vaqt/token tejash)
    ok_results = [r for r in results if r["ok"]]
    if len(ok_results) <= 1:
        return ok_results[0]["text"] if ok_results else blob

    candidates = [cfg["director"]["model"]] + cfg["director"].get("fallbacks", [])
    for model in candidates:
        res = await engine.run_model(model, _AGGREGATE.format(task=task, results=blob),
                                     timeout=cfg["limits"]["timeout_seconds"])
        if res["ok"]:
            return res["text"]
    return blob  # yig'ish qotsa — xom natijalarni ko'rsatamiz


def _parse_json_array(text: str):
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        return None
    try:
        arr = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    out = []
    for i, it in enumerate(arr, 1):
        if not isinstance(it, dict):
            continue
        out.append({
            "id": it.get("id") or f"s{i}",
            "title": it.get("title") or f"Subtask {i}",
            "prompt": it.get("prompt") or it.get("title") or "",
        })
    return [o for o in out if o["prompt"]] or None
