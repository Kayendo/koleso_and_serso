# DOTAG 3 — Dроп Oтсутствует, Только Aктивный Gейминг 3

Веб-приложение для ивента с прохождением случайных игр: поле в стиле «Монополии», синхронные фишки, колесо выбора игры, профили игроков и интеграция с HLTB.

## Стек

- **Backend:** Python 3.11+, Flask, Flask-SocketIO, SQLAlchemy, SQLite
- **Frontend:** React 18, Vite, Socket.IO client
- **Реальное время:** WebSocket (все клиенты видят броски и движение)

## Быстрый старт

```bash
# 1. Зависимости Python
cd c:\Users\Kayendo\Desktop\Kolesoblya
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 2. Фронтенд
cd frontend
npm install
npm run build
cd ..

# 3. Запуск (отдаёт API + собранный UI на :5000)
python run.py
```

Разработка с hot-reload фронта:

```bash
# Терминал 1
python run.py

# Терминал 2
cd frontend && npm run dev
```

Откройте http://127.0.0.1:5173 (прокси на API) или http://127.0.0.1:5000 после `npm run build`.

## Списки игр (редактируйте вручную)

| Файл | Назначение |
|------|------------|
| `data/genre_1_puzzle.txt` … `genre_9_strategy.txt` | Игры по жанрам / компаниям |
| `data/games_question.txt` | Клетка «?» |
| `data/games_trallalero.txt` | «Траллалеро траллала» |

Строки с `#` — комментарии. Одна игра на строку.

## Правила в коде

- Текст для модалки «Правила»: `backend/rules.py`
- Раскладка поля и компании: `backend/board.py`
- Очки: `backend/services/scoring.py`

## Учётки

Логины и пароли задаются в `backend/accounts.py` (регистрации нет). По умолчанию:

| Логин | Пароль | Роль |
|-------|--------|------|
| andryuha | koleso1 | игрок |
| zhenek | koleso2 | игрок |
| nikita | koleso3 | игрок |
| vanya | koleso4 | игрок |
| admin | admin99 | админ (не на поле, редактирование) |

## Роли

- **sudya** — судья (`is_judge`) и админ; может задать часы игры без HLTB.
- Карту могут смотреть без логина; ходы и профиль — только после входа.

## Комментатор (фразы + озвучка, без нейросети)

Раз в 30–40 с случайная фраза из `data/ai_comment_phrases.jsonl` под ситуацию игрока + Edge TTS. Сокет `game_comment`.

- Статус: `http://127.0.0.1:5000/api/comment/status`
- Голоса: `http://127.0.0.1:5000/api/ai/voices`
- `.env`: `COMMENTATOR_*`, `AI_TTS_VOICE` — см. `.env.example` и `data/VOICES.md`
- Фразы не грузятся при старте страницы — только в фоне на сервере при первом тике

## Картинки на поле

**Компании** — `frontend/public/logos/<company_key>.jpg` (подойдут и `.png`, `.webp`)  
**Особые клетки** — `frontend/public/cells/` (`start.jpg`, `question.jpg`, …)

Формат: сначала ищется `.jpg`, затем `.png`. После добавления файлов обновите страницу.

## Что доделать позже (вы писали «опишу позже»)

- Эффекты «Подлянка / Кайфарик»
- Полные правила дропа
- Автоматический парсинг Game Gauntlet (сейчас лотерея — ручной ввод названия после Roll на сайте)

## Гифки в центре поля

Случайные GIF с Tenor (`GET /api/tenor/meme`). Меняются при смене фазы игроков и **раз в час** (сокет `gif_pool_refresh`).

**Настройка пула:**
- `data/tenor_tags.txt` — теги поиска (один на строку)
- `data/gif_fallback.json` — запасные URL, если Tenor недоступен
- `.env`:
  ```env
  TENOR_POOL_REFRESH_ENABLED=1
  TENOR_POOL_REFRESH_SEC=3600
  TENOR_POOL_FIRST_DELAY=15
  TENOR_POOL_LOW=20
  TENOR_API_KEY=...
  TENOR_SEARCH_TAGS=meme,funny,gaming
  ```

Статус пула: `GET /api/tenor/config`

## Структура

```
Kolesoblya/
├── backend/          # API, сокеты, модели
├── data/             # Списки игр
├── frontend/         # React UI
├── run.py
└── requirements.txt
```
