"""
engine.py — opencode'ni fon rejimida, izolyatsiya bilan chaqiruvchi qatlam.

Har bir chaqiruv alohida XDG_DATA_HOME/XDG_CONFIG_HOME oladi -> "database is locked"
muammosi bo'lmaydi (parallel test'da o'rgangan saboq). auth.json har bir izolyatsiyalangan
data-dir ichiga nusxalanadi, aks holda OpenRouter kaliti topilmaydi.
"""
import asyncio
import os
import shutil
import tempfile

OPENCODE = os.path.expanduser("~/.npm-global/bin/opencode")
REAL_AUTH = os.path.expanduser("~/.local/share/opencode/auth.json")


async def run_model(model: str, prompt: str, timeout: int = 150) -> dict:
    """Bitta modelni izolyatsiyada ishga tushiradi.

    Qaytaradi: {"model", "ok": bool, "text": str, "error": str, "seconds": float}
    """
    workdir = tempfile.mkdtemp(prefix="orch_")
    data_home = os.path.join(workdir, "data")
    cfg_home = os.path.join(workdir, "cfg")

    # auth.json'ni izolyatsiyalangan data-dir ichiga nusxalaymiz (OpenRouter kaliti uchun)
    oc_data = os.path.join(data_home, "opencode")
    os.makedirs(oc_data, exist_ok=True)
    if os.path.exists(REAL_AUTH):
        shutil.copy2(REAL_AUTH, os.path.join(oc_data, "auth.json"))

    env = dict(os.environ)
    env["XDG_DATA_HOME"] = data_home
    env["XDG_CONFIG_HOME"] = cfg_home
    env["PATH"] = os.path.dirname(OPENCODE) + os.pathsep + env.get("PATH", "")

    loop = asyncio.get_event_loop()
    start = loop.time()
    try:
        proc = await asyncio.create_subprocess_exec(
            OPENCODE, "run", "-m", model, "--dir", workdir, prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
        )
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {"model": model, "ok": False, "text": "",
                    "error": f"timeout ({timeout}s)", "seconds": loop.time() - start}

        text = _clean(out.decode("utf-8", "replace"))
        ok = proc.returncode == 0 and text and "Error:" not in text[:200] \
            and "No provider available" not in text
        return {"model": model, "ok": bool(ok), "text": text,
                "error": "" if ok else _extract_error(text),
                "seconds": loop.time() - start}
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _clean(s: str) -> str:
    """ANSI ranglarni va opencode banner qatorlarini tozalaydi."""
    import re
    s = re.sub(r"\x1b\[[0-9;]*m", "", s)
    lines = []
    for ln in s.splitlines():
        st = ln.strip()
        if not st:
            continue
        # opencode boshidagi "> build · model" kabi meta qatorlarni tashlab yuboramiz
        if st.startswith(">") and "·" in st:
            continue
        lines.append(ln)
    return "\n".join(lines).strip()


def _extract_error(text: str) -> str:
    for ln in text.splitlines():
        if "Error" in ln or "provider" in ln.lower():
            return ln.strip()[:200]
    return text[:120] or "unknown error"
