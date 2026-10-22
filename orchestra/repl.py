"""
repl.py — interaktiv terminal (Claude kabi).
Ishlatish:  python3 -m orchestra

- Oddiy gap -> tez CHAT (bitta model, to'g'ridan-to'g'ri API, xotira bilan)
- Murakkab vazifa -> PARALLEL ORKESTR (director bo'ladi, workerlar parallel)
- Xotira sessiyalar orasida saqlanadi (/clear tozalaydi)
"""
import asyncio
import os
import sys
import time

import yaml

from . import agent, director, llm, pool, router, store

CONFIG = os.path.join(os.path.dirname(__file__), "..", "config.yaml")

C_DIM = "\033[90m"; C_CYAN = "\033[96m"; C_GREEN = "\033[92m"; C_YEL = "\033[93m"
C_RED = "\033[91m"; C_BOLD = "\033[1m"; C_BLUE = "\033[94m"; C_OFF = "\033[0m"

SYSTEM = {
    "role": "system",
    "content": (
        "Sen 'agent-orchestra' — Mr Khashimov uchun terminalda ishlaydigan shaxsiy "
        "yordamchisan. Unga hurmat bilan 'ser' yoki 'Mr Khashimov' deb murojaat qil. "
        "Qisqa, aniq va tabiiy o'zbek tilida javob ber. Foydali va samimiy bo'l."
    ),
}


def load_config() -> dict:
    with open(CONFIG) as f:
        return yaml.safe_load(f)


def available_models(cfg: dict) -> list:
    """Tanlanadigan bepul chat modellari ro'yxati [{id, note}, ...]."""
    items = list(cfg["chat"].get("available", []))
    ids = {i["id"] for i in items}
    cur = cfg["chat"]["model"]
    if cur not in ids:  # joriy model ro'yxatda bo'lmasa qo'shamiz
        items.insert(0, {"id": cur, "note": "joriy"})
    return items


def show_models(cfg: dict):
    cur = cfg["chat"]["model"]
    print(f"\n{C_BOLD}Chat modellari{C_OFF} {C_DIM}(hozirgi ✦ bilan belgilangan){C_OFF}")
    for i, m in enumerate(available_models(cfg), 1):
        mark = f"{C_GREEN}✦{C_OFF}" if m["id"] == cur else " "
        print(f"  {mark} {C_CYAN}{i}{C_OFF}. {m['id'].split('/')[-1]:<32} {C_DIM}{m.get('note','')}{C_OFF}")


def model_command(arg: str, cfg: dict) -> bool:
    """/model — tanlash. arg raqam yoki nom bo'lsa to'g'ridan almashadi. Almashsa True."""
    models = available_models(cfg)
    show_models(cfg)
    if not arg:
        try:
            arg = input(f"{C_BLUE}Tanlang (raqam yoki Enter=bekor) ›{C_OFF} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); return False
    if not arg:
        print(f"{C_DIM}Bekor qilindi.{C_OFF}\n"); return False

    chosen = None
    if arg.isdigit() and 1 <= int(arg) <= len(models):
        chosen = models[int(arg) - 1]["id"]
    else:  # nom bo'yicha qidiramiz
        for m in models:
            if arg.lower() in m["id"].lower():
                chosen = m["id"]; break
    if not chosen:
        print(f"{C_YEL}Topilmadi: {arg}{C_OFF}\n"); return False

    cfg["chat"]["model"] = chosen
    st = store.load_state(); st["chat_model"] = chosen; store.save_state(st)
    print(f"{C_GREEN}✅ Chat modeli o'zgardi:{C_OFF} {chosen.split('/')[-1]}\n")
    return True


def banner(cfg, workdir):
    print(f"{C_BOLD}{C_CYAN}🚀 agent-orchestra{C_OFF} {C_DIM}— terminal yordamchi (Claude kabi){C_OFF}")
    print(f"{C_DIM}chat: {cfg['chat']['model'].split('/')[-1]}  ·  "
          f"amal: {cfg['agent']['model'].split('/')[-1]}  ·  📁 {workdir}{C_OFF}")
    print(f"{C_DIM}Buyruqlar: /help  /do <amal>  /task <matn>  /cd <yo'l>  /clear  /model  /exit{C_OFF}\n")


def help_text():
    print(f"""{C_BOLD}Buyruqlar:{C_OFF}
  {C_CYAN}/do <amal>{C_OFF}    kompyuterda HAQIQIY amal (papka/fayl yaratish, buyruq bajarish)
  {C_CYAN}/task <matn>{C_OFF}  vazifani parallel orkestrga yubor (4 ta model birga)
  {C_CYAN}/cd <yo'l>{C_OFF}    amallar bajariladigan papkani o'zgartir
  {C_CYAN}/model{C_OFF}        chat modelini tanla (bepul modellar ro'yxati)
  {C_CYAN}/status{C_OFF}       sessiya statistikasini ko'rsat
  {C_CYAN}/clear{C_OFF}        suhbat xotirasini tozala
  {C_CYAN}/help{C_OFF}         bu yordam   ·   {C_CYAN}/exit{C_OFF}  chiqish

{C_DIM}Rejimlar avtomatik: oddiy gap → chat; "papka yarat / fayl / buyruq" → amal; /task → orkestr.{C_OFF}
""")

def show_status(cfg, workdir):
    import time as _t
    st = store.load_stats()
    pid = st.get("session_count", 0)
    uptime = _t.time() - st.get("started_at", _t.time())
    h, rem = divmod(int(uptime), 3600); m, s = divmod(rem, 60)
    print(f"{C_BOLD}{C_CYAN}📊 Sessiya statistikasi{C_OFF}")
    print(f"  {C_DIM}Sessiya:{C_OFF} #{pid}  ·  ishlagan: {h}h {m:02d}m {s:02d}s")
    print(f"  {C_DIM}Jami so'rovlar:{C_OFF} {st.get('total_queries', 0)}  "
          f"({C_GREEN}chat:{C_OFF}{st.get('total_chat',0)}  "
          f"{C_YEL}amal:{C_OFF}{st.get('total_action',0)}  "
          f"{C_CYAN}orkestr:{C_OFF}{st.get('total_task',0)})")
    print(f"  {C_DIM}Chat modeli:{C_OFF} {cfg['chat']['model'].split('/')[-1]}")
    print(f"  {C_DIM}Amal modeli:{C_OFF} {cfg['agent']['model'].split('/')[-1]}")
    print(f"  {C_DIM}Worker pool:{C_OFF} {len(cfg['workers']['free_pool'])} ta model  "
          f"(max {cfg['limits']['max_parallel']} parallel)")
    print(f"  {C_DIM}Ishchi papka:{C_OFF} {workdir}")
    mu = st.get("models_used", {})
    if mu:
        print(f"  {C_DIM}Modellar:{C_OFF}")
        for m, c in sorted(mu.items(), key=lambda x: -x[1]):
            print(f"    · {m.split('/')[-1]:<32} {c}x")
    print()


# ---------- CHAT rejimi ----------
def do_chat(history: list, cfg: dict):
    turns = cfg["chat"].get("history_turns", 12)
    msgs = [SYSTEM] + history[-turns:]
    print(f"{C_DIM}o'ylayapti...{C_OFF}", end="\r", flush=True)
    t = time.time()
    reply, used = llm.chat(msgs, cfg)
    print(" " * 20, end="\r")  # "o'ylayapti" ni tozalash
    print(f"{C_GREEN}🤖 ›{C_OFF} {reply}  {C_DIM}[{used.split('/')[-1]}, {time.time()-t:.1f}s]{C_OFF}\n")
    return reply


# ---------- VAZIFA (orkestr) rejimi ----------
def _line(r):
    if r["ok"]:
        tag = f"{C_GREEN}✅{C_OFF}"; extra = f" {C_DIM}(fallback){C_OFF}" if r.get("fallback_used") else ""
    else:
        tag = f"{C_RED}❌{C_OFF}"; extra = f" {C_RED}{r['error']}{C_OFF}"
    print(f"   {tag} {r['title']} {C_DIM}[{r['model'].split('/')[-1]}, {r['seconds']:.0f}s]{C_OFF}{extra}")


async def _run_task(task: str, cfg: dict):
    print(f"{C_DIM}Director qismlarga bo'lmoqda...{C_OFF}")
    subtasks = await director.decompose(task, cfg)
    print(f"{C_CYAN}→ {len(subtasks)} ta parallel qism{C_OFF}")
    print(f"{C_DIM}Workerlar parallel ishlamoqda (max {cfg['limits']['max_parallel']})...{C_OFF}")
    results = await pool.run_all(subtasks, cfg, on_done=_line)
    print(f"{C_DIM}Yig'moqda...{C_OFF}\n")
    final = await director.aggregate(task, results, cfg)
    print(f"{C_BOLD}{'─'*56}{C_OFF}")
    print(final)
    print(f"{C_BOLD}{'─'*56}{C_OFF}\n")
    return final


# ---------- ACTION (haqiqiy amal) rejimi ----------
def do_action(instruction: str, workdir: str, cfg: dict) -> str:
    import time as _t
    print(f"{C_DIM}📁 {workdir}  ·  {cfg['agent']['model'].split('/')[-1]}{C_OFF}")
    t = _t.time()

    def on_line(ln: str):
        s = ln.strip()
        if s.startswith("$") or s.startswith("←") or s.startswith("→"):
            print(f"   {C_YEL}{s}{C_OFF}")          # bajarilgan buyruq/fayl amali
        else:
            print(f"   {C_DIM}{s}{C_OFF}")

    out = agent.run_action(instruction, workdir, cfg["agent"]["model"],
                           cfg["agent"].get("timeout_seconds", 150), on_line=on_line)
    print(f"{C_DIM}⏱  {_t.time()-t:.0f}s{C_OFF}\n")
    return out


def do_task(task: str, cfg: dict):
    t = time.time()
    try:
        final = asyncio.run(asyncio.wait_for(
            _run_task(task, cfg), timeout=cfg["limits"].get("overall_timeout", 300)))
    except asyncio.TimeoutError:
        print(f"{C_RED}⏱  Global timeout — bepul modellar juda sekin bo'ldi.{C_OFF}\n")
        final = "[timeout]"
    print(f"{C_DIM}⏱  {time.time()-t:.0f}s{C_OFF}\n")
    return final


# ---------- Asosiy sikl ----------
def main():
    cfg = load_config()
    # saqlangan sozlamalarni tiklaymiz
    st = store.load_state()
    if st.get("chat_model"):
        cfg["chat"]["model"] = st["chat_model"]
    workdir = os.path.expanduser(st.get("workdir") or cfg["agent"].get("workdir", "~"))
    history = store.load()
    # sessiya statistikasini yangilaymiz
    st_s = store.load_stats()
    st_s["session_count"] = st_s.get("session_count", 0) + 1
    st_s["started_at"] = st_s.get("started_at", time.time())
    store.save_stats(st_s)
    banner(cfg, workdir)
    if history:
        print(f"{C_DIM}(oldingi suhbatdan {len(history)} xabar eslab qolindi){C_OFF}\n")

    while True:
        try:
            user = input(f"{C_BLUE}siz ›{C_OFF} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{C_DIM}Xayr, ser! 👋{C_OFF}")
            break
        if not user:
            continue

        low = user.lower()
        if low in ("/exit", "/quit", "exit", "quit"):
            print(f"{C_DIM}Xayr, ser! 👋{C_OFF}")
            break
        if low == "/help":
            help_text(); continue
        if low == "/clear":
            store.clear(); history = []
            print(f"{C_YEL}Xotira tozalandi.{C_OFF}\n"); continue
        if low == "/model" or low.startswith("/model ") or low == "/models":
            arg = user[6:].strip() if len(user) > 6 else ""
            model_command(arg, cfg)
            continue

        if low.startswith("/cd") or low.startswith("/workdir"):
            path = user.split(None, 1)[1].strip() if len(user.split(None, 1)) > 1 else ""
            if path:
                workdir = os.path.expanduser(path)
                st = store.load_state(); st["workdir"] = workdir; store.save_state(st)
                print(f"{C_GREEN}📁 Amal papkasi:{C_OFF} {workdir}\n")
            else:
                print(f"{C_DIM}📁 Hozirgi amal papkasi: {workdir}{C_OFF}\n")
            continue

        if low in ("/status", "/stats"):
            show_status(cfg, workdir); continue

        mode = router.classify(user, cfg)

        if mode == "action":
            instruction = user[3:].strip() if low.startswith("/do") else user
            if not instruction:
                print(f"{C_YEL}Ishlatish: /do <amal>{C_OFF}\n"); continue
            print(f"{C_DIM}🛠  Amal rejimi (haqiqiy ish bajariladi){C_OFF}")
            out = do_action(instruction, workdir, cfg)
            history.append({"role": "user", "content": user})
            history.append({"role": "assistant", "content": out[-1500:]})
            store.save(history)
            store.record_query("action", cfg["agent"]["model"])

        elif mode == "task":
            task = user[5:].strip() if low.startswith("/task") else user
            if not task:
                print(f"{C_YEL}Ishlatish: /task <vazifa matni>{C_OFF}\n"); continue
            print(f"{C_DIM}⚙  Parallel orkestr{C_OFF}")
            final = do_task(task, cfg)
            history.append({"role": "user", "content": user})
            history.append({"role": "assistant", "content": final})
            store.save(history)
            store.record_query("task", "orkestr")

        else:  # chat
            history.append({"role": "user", "content": user})
            reply = do_chat(history, cfg)
            history.append({"role": "assistant", "content": reply})
            store.save(history)
            store.record_query("chat", cfg["chat"]["model"])


if __name__ == "__main__":
    main()
