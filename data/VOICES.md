# Голоса комментатора

## Важно про DonationAlerts

Голоса вроде **«Дед Мороз»**, **«Питер Гриффин»**, **«Древний рус»** на DonationAlerts — это **не публичный API**. У стримов свой закрытый каталог, часто это клоны (RVC) или загруженные MP3, а не Edge TTS.

В Kolesoblya по умолчанию включены **похожие по настроению персонажи** (низкий/быстрый голос, другой язык на русском тексте) в `data/ai_tts_characters.json`.

Чтобы получить **максимально близкий** к DA голос для любого текста:

1. Подними локально **RVC / XTTS / Piper API** с нужной моделью.
2. В `ai_tts_characters.json` включи `custom_http` (`enabled: true`) или свой объект с `"provider": "http"`.
3. В `.env`: `AI_TTS_HTTP_URL=http://127.0.0.1:7860/tts` (твой endpoint, POST JSON `{"text":"..."}` → MP3/WAV или JSON с `audioBase64`).

## Файлы

| Файл | Назначение |
|------|------------|
| `data/ai_tts_characters.json` | **Персонажи** (Дед Мороз, Питер, древний рус, …) |
| `data/ai_tts_roster.json` | Классические Edge-голоса (если `AI_TTS_POOL=roster`) |
| `data/edge_tts_catalog.json` | Все 322 голоса Microsoft Edge |
| `.env` → `AI_TTS_VOICE` | `random` или id персонажа, напр. `ded_moroz` |

## API

**http://127.0.0.1:5000/api/ai/voices**

- `active` — кто в ротации сейчас  
- `characters` — полный список персонажей  
- `sileroAvailable` — установлен ли torch для Silero  

## Переменные .env

| Переменная | Значение |
|------------|----------|
| `AI_TTS_VOICE` | `random` или `ded_moroz`, `peter_griffin`, … |
| `AI_TTS_POOL` | `characters` (по умолчанию) или `roster` |
| `AI_TTS_HTTP_URL` | URL для `provider: http` |

## Русский текст

Фразы комментатора **на русском**. Голоса `en-US`, `de-DE` и т.п. в Edge **не читают кириллицу** — только кусок латиницы (название игры). Все персонажи используют **`ru-RU-*` или `uk-UA-*`**; различие — скорость и питч.

## Персонажи по умолчанию (Edge)

| id | Описание |
|----|----------|
| `ded_moroz` | Низкий медленный RU |
| `drevniy_rus` | Очень медленный «древний» RU |
| `peter_griffin` | Быстрый RU-муж (высокий темп) |
| `babushka` | RU женский |
| `zombie` | Очень низкий медленный |
| `chipmunk` | Высокий быстрый UA |
| `narrator_epic` | UK диктор |
| `villain` | Низкий DE «злодей» |

Включи/выключи в `ai_tts_characters.json`: `"enabled": true/false`.

## Silero (локально, другой тембр)

```powershell
pip install torch pydub
# ffmpeg в PATH — для MP3
```

В `ai_tts_characters.json` поставь `"enabled": true` у `silero_aidar`, `silero_baya`, `silero_xenia`.

## Классический roster (только Edge-акценты)

`.env`: `AI_TTS_POOL=roster` — снова ротация из `ai_tts_roster.json`.

## Комментатор

Фразы из `ai_comment_phrases.jsonl` + Edge TTS, без LLM. Включение: `COMMENTATOR_ENABLED=1` в `.env`. Статус: `/api/comment/status`, сокет `game_comment`.
