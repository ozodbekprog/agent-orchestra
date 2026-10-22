"""
cli.py — terminal kirish nuqtasi.
Ishlatish:  python -m orchestra.cli "vazifangiz matni"
"""
import asyncio
import os
import sys
import time

import yaml

from . import director, pool

CONFIG = os.path.join(os.path.dirname(__file__), "..", "config.yaml")

C_DIM = "\033[90m"; C_CYAN = "\033[96m"; C_GREEN = "\033[92m"
C_RED = "\033[91m"; C_BOLD = "\033[1m"; C_OFF = "\033[0m"


def load_config() -> dict:
    with open(CONFIG) as f:
        return yaml.safe_load(f)


def _short(model: str) -> str:
    return model.split("/")[-1]


def _print_result_line(r: dict):
    if r["ok"]:
        tag = f"{C_GREEN}✅{C_OFF}"
        fb = f" {C_DIM}(fallback){C_OFF}" if r.get("fallback_used") else ""
    else:
        tag = f"{C_RED}❌{C_OFF}"; fb = f" {C_RED}{r['error']}{C_OFF}"
    print(f"   {tag} {r['title']} {C_DIM}[{_short(r['model'])}, {r['seconds']:.0f}s]{C_OFF}{fb}")


async def _orchestrate(task: str, cfg: dict):
    print(f"{C_BOLD}🎯 Vazifa:{C_OFF} {task}\n")
    print(f"{C_DIM}Director ({_short(cfg['director']['model'])}) qismlarga bo'lmoqda...{C_OFF}")
    subtasks = await director.decompose(task, cfg)
    print(f"{C_CYAN}→ {len(subtasks)} ta parallel qism:{C_OFF}")
    for s in subtasks:
        print(f"   • {s['title']}")

    print(f"\n{C_DIM}Workerlar parallel ishlamoqda (max {cfg['limits']['max_parallel']})...{C_OFF}")
    results = await pool.run_all(subtasks, cfg, on_done=_print_result_line)

    print(f"\n{C_DIM}Director natijalarni yig'moqda...{C_OFF}\n")
    final = await director.aggregate(task, results, cfg)

    print(f"{C_BOLD}{'='*60}\n📋 YAKUNIY NATIJA\n{'='*60}{C_OFF}\n")
    print(final)


async def run(task: str):
    cfg = load_config()
    t0 = time.time()
    try:
        await asyncio.wait_for(_orchestrate(task, cfg),
                               timeout=cfg["limits"].get("overall_timeout", 300))
    except asyncio.TimeoutError:
        print(f"\n{C_RED}⏱  Global timeout — vazifa juda uzun cho'zildi (bepul modellar sekin).{C_OFF}")
    print(f"\n{C_DIM}⏱  Jami: {time.time()-t0:.0f}s{C_OFF}")


def main():
    if len(sys.argv) < 2:
        print("Ishlatish: python -m orchestra.cli \"vazifangiz\"")
        sys.exit(1)
    task = " ".join(sys.argv[1:])
    asyncio.run(run(task))


if __name__ == "__main__":
    main()
