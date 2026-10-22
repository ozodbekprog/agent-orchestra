"""
agent.py — HAQIQIY amal bajaruvchi rejim (Claude Code kabi).

opencode'ni FOYDALANUVCHINING haqiqiy papkasida (izolyatsiyasiz) ishga tushiradi,
shunda u bash/fayl tool'lari bilan chinakam ish bajaradi: papka/fayl yaratadi,
buyruq bajaradi va h.k. opencode harakatlarini JONLI ko'rsatadi.
"""
import os
import re
import subprocess
import threading

OPENCODE = os.path.expanduser("~/.npm-global/bin/opencode")
ANSI = re.compile(r"\x1b\[[0-9;]*m")

# opencode chiqishidagi meta/banner qatorlarni yashiramiz
_SKIP = ("opencode", "█", "▀", "▄", "░")


def run_action(instruction: str, workdir: str, model: str = "",
               timeout: int = 150, on_line=None) -> str:
    """opencode'ni real papkada ishga tushiradi. To'liq chiqishni qaytaradi."""
    workdir = os.path.expanduser(workdir or "~")
    os.makedirs(workdir, exist_ok=True)

    env = dict(os.environ)
    env["PATH"] = os.path.dirname(OPENCODE) + os.pathsep + env.get("PATH", "")

    cmd = [OPENCODE, "run", "--dir", workdir]
    if model:
        cmd += ["-m", model]
    cmd.append(instruction)

    proc = subprocess.Popen(cmd, cwd=workdir, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, env=env)
    timer = threading.Timer(timeout, proc.kill)
    timer.start()
    lines = []
    try:
        for raw in proc.stdout:
            line = ANSI.sub("", raw.rstrip("\n"))
            st = line.strip()
            if not st or st.startswith(_SKIP):
                continue
            if st.startswith(">") and "·" in st:   # "> build · model" meta
                continue
            lines.append(line)
            if on_line:
                on_line(line)
        proc.wait()
    finally:
        timer.cancel()
    return "\n".join(lines)
