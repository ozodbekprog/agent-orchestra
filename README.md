# agent-orchestra

Terminalda ishlaydigan shaxsiy AI yordamchi (Claude kabi) — **chat + amal + orkestr + xotira**.

Uch rejim (avtomatik aniqlanadi):
- **CHAT** — oddiy gap → tez suhbat (to'g'ridan OpenRouter API, xotira bilan)
- **AMAL (action)** — "papka/fayl yarat, buyruq bajar" → opencode HAQIQIY ish bajaradi
  (real papkada bash/fayl tool'lari bilan). `/do <amal>` bilan majburan.
- **ORKESTR (task)** — `/task <matn>` → director bo'ladi, workerlar parallel, keyin yig'adi
- **Xotira** sessiyalar orasida saqlanadi (`.history.json`); model tanlovi `.state.json`

⚠️  **Diqqat:** amal rejimi kompyuteringizda HAQIQIY buyruq bajaradi (yaratish/o'chirish/ishga
tushirish). Standart papka — uy (`~`); `/cd <yo'l>` bilan o'zgartiring. Xohlagan papkada sinang.

## Ishga tushirish
```bash
ao                      # yangi terminal ochib (yoki: source ~/.bashrc)
# yoki to'g'ridan-to'g'ri:
python3 -m orchestra
```

Terminalda:
```
siz › salom
🤖 › Salom, ser! Qanday yordam bera olaman?

siz › ORBITAL uchun landing page qur
⚙  Vazifa aniqlandi → parallel orkestr
   ✅ ...  ✅ ...  ✅ ...
```

Buyruqlar: `/do <amal>` `/task <matn>` `/cd <yo'l>` `/model` `/clear` `/help` `/exit`

## Arxitektura
```
        Terminal (repl.py)
              │
      router.py — chat'mi yoki vazifa?
        ┌─────┴───────────────┐
        ▼                     ▼
   CHAT (llm.py)      VAZIFA (director + pool)
   to'g'ridan API     director bo'ladi → workerlar
   + xotira (store)   parallel (engine=opencode, izolyatsiya)
                      → director yig'adi
```

## Fayllar
- `config.yaml` — chat modeli, director, worker pool, fallback, limitlar
- `orchestra/repl.py` — interaktiv terminal (asosiy)
- `orchestra/llm.py` — tez chat (to'g'ridan OpenRouter API)
- `orchestra/store.py` — suhbat xotirasi (JSON)
- `orchestra/router.py` — chat vs vazifa tasnifi
- `orchestra/director.py` — vazifani bo'lish/yig'ish
- `orchestra/pool.py` — parallel dispatch + retry/fallback
- `orchestra/engine.py` — opencode'ni izolyatsiya bilan chaqirish

## Modellar (gibrid, hozircha $0 bepul)
- chat: `nvidia/nemotron-3-super-120b:free` (tez + o'zbekchani biladi)
- director: `openai/gpt-oss-20b:free` (+ fallbacklar)
- workers: 5 ta bepul model pool
- **Balansga $10 qo'ysangiz:** chat/director'ni `gemini-2.5-flash` yoki `claude-haiku-4.5`
  ga o'tkazing — ancha tez va ishonchli, kunlik limit 1000 ga chiqadi.

## Yo'l xaritasi
- [x] Phase 1 — parallel orkestr yadrosi
- [x] Chat rejimi + xotira + aqlli marshrutlash + interaktiv terminal
- [ ] Phase 3 — Telegram bot interfeysi
- [ ] Phase 4 — kanal kontenti avtomatlashtirish
- [ ] streaming javob (token-token), balans bo'lsa ishonchli modellar
