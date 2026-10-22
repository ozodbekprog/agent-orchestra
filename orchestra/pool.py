"""
pool.py — subtasklarni parallel workerlarga taqsimlaydi.

- max_parallel semaphore bilan rate-limitni hurmat qiladi (20/daqiqa)
- bepul worker xato bersa -> fallback modelga qayta yuklaydi (retry)
- on_done callback bilan har worker tugagach JONLI xabar beradi (jim qolmaydi)
"""
import asyncio
import itertools

from . import engine


async def _one(subtask: dict, model: str, sem: asyncio.Semaphore, cfg: dict,
               fallback: str) -> dict:
    async with sem:
        res = await engine.run_model(model, subtask["prompt"],
                                     timeout=cfg["limits"]["timeout_seconds"])
        tries = 0
        while not res["ok"] and tries < cfg["limits"]["max_retries"]:
            tries += 1
            res = await engine.run_model(fallback, subtask["prompt"],
                                         timeout=cfg["limits"]["timeout_seconds"])
            res["fallback_used"] = True
        res["subtask_id"] = subtask["id"]
        res["title"] = subtask.get("title", subtask["id"])
        return res


async def run_all(subtasks: list, cfg: dict, on_done=None) -> list:
    """Barcha subtasklarni parallel bajaradi. on_done(result) har tugaganda chaqiriladi."""
    sem = asyncio.Semaphore(cfg["limits"]["max_parallel"])
    pool = itertools.cycle(cfg["workers"]["free_pool"])  # round-robin
    fallback = cfg["fallback"]["model"]
    tasks = [asyncio.create_task(_one(st, next(pool), sem, cfg, fallback))
             for st in subtasks]
    results = []
    for fut in asyncio.as_completed(tasks):
        r = await fut
        results.append(r)
        if on_done:
            on_done(r)
    return results
