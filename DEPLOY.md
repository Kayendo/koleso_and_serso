# Kolesoblya / DOTAG 3 — деплой в интернет

Пошаговая инструкция «с нуля»: только GitHub и этот репозиторий.

---

## Что получится

- Игра доступна по адресу `http://IP_СЕРВЕРА` (или `https://твой-домен.ru`)
- Все игроки видят одно поле в реальном времени (WebSocket)
- Файлы в `data/` можно править на сервере **без пересборки фронта**

---

## Шаг 0. Что нужно купить/завести

1. **VPS** (виртуальный сервер) — Ubuntu 22.04 или 24.04  
   Подойдут: [Timeweb Cloud](https://timeweb.cloud), [Hetzner](https://www.hetzner.com/cloud), Selectel, Reg.ru  
   **Минимум:** 1 CPU, 2 GB RAM, 20 GB диск (~300–600 ₽/мес)

2. **(Опционально) Домен** — если хочешь красивый URL и HTTPS  
   Без домена можно играть просто по IP.

3. **GitHub** — уже есть: `Kayendo/koleso_and_serso`

---

## Шаг 1. Создай VPS

В панели хостинга:

1. Создай сервер **Ubuntu 22.04**
2. Запиши **IP-адрес** (например `123.45.67.89`)
3. Запиши **логин/пароль root** или добавь **SSH-ключ**

---

## Шаг 2. Подключись к серверу с Windows

**PowerShell** (Windows 10+):

```powershell
ssh root@123.45.67.89
```

(подставь свой IP; пароль спросит при первом входе)

Если `ssh` не найден — установи [PuTTY](https://www.putty.org/) или включи OpenSSH в Windows.

---

## Шаг 3. Автоустановка (одна команда)

На сервере (под root):

```bash
apt-get update && apt-get install -y git
git clone https://github.com/Kayendo/koleso_and_serso.git /opt/kolesoblya
cd /opt/kolesoblya
bash deploy/install.sh
```

Скрипт сам:

- поставит Python, Node, Nginx
- соберёт фронтенд
- создаст `.env` с случайным `SECRET_KEY`
- запустит сервис `kolesoblya`

**Время:** ~5–15 минут.

---

## Шаг 4. Укажи IP в nginx

```bash
nano /etc/nginx/sites-available/kolesoblya
```

Строку:

```
server_name YOUR_DOMAIN_OR_IP;
```

замени на свой IP или домен, например:

```
server_name 123.45.67.89;
```

Сохрани: `Ctrl+O`, Enter, `Ctrl+X`.

```bash
nginx -t && systemctl reload nginx
```

---

## Шаг 5. Открой порт 80 в файрволе хостинга

В панели VPS (Security / Firewall):

- **Inbound TCP 80** — разрешить (для HTTP)
- **Inbound TCP 443** — если будешь ставить HTTPS

Порт **5000** наружу открывать **не нужно** — nginx проксирует на localhost.

---

## Шаг 6. Проверь в браузере

Открой: `http://123.45.67.89` (свой IP)

- Должно открыться поле DOTAG 3
- Войди как игрок (логины в `backend/accounts.py`)
- Админ: `admin` / `admin99`

---

## Шаг 7. Смени пароли (важно!)

На **своём компе** отредактируй `backend/accounts.py`, закоммить и на сервере:

```bash
cd /opt/kolesoblya
sudo -u kolesoblya git pull
sudo systemctl restart kolesoblya
```

---

## Шаг 8. HTTPS (если есть домен)

1. В DNS домена добавь **A-запись** → IP сервера  
2. В nginx укажи `server_name dotag.tvoi-domen.ru;`
3. На сервере:

```bash
apt-get install -y certbot python3-certbot-nginx
certbot --nginx -d dotag.tvoi-domen.ru
```

Игра откроется по `https://...`

---

## Как обновлять `data/` в лайве

### Без перезапуска (сразу или после F5)

| Файл | Эффект |
|------|--------|
| `data/genre_*.txt` | Новые игры на колесе — сразу |
| `data/games_question.txt` | Клетка «?» |
| `data/games_trallalero.txt` | Траллalero |
| `data/casino_news.txt` | Бегущая строка — после F5 у игрока |

### Нужна кнопка «Перечитать data» (админ)

В **админ-панели** → **«Перечитать data/»** — подтягивает:

- `items.txt` (предметы)
- фразы комментатора
- голоса TTS
- пул GIF

### Редактирование на сервере

```bash
ssh root@123.45.67.89
nano /opt/kolesoblya/data/genre_3_action.txt
```

Или через **WinSCP** / **FileZilla**: хост = IP, пользователь `root`, путь `/opt/kolesoblya/data/`

---

## Как обновить код с GitHub

```bash
cd /opt/kolesoblya
sudo -u kolesoblya git pull
sudo -u kolesoblya bash -lc 'cd frontend && npm ci && npx vite build'
sudo systemctl restart kolesoblya
```

Если менялся **только** `data/` — достаточно правки файла (+ кнопка админа для items).

---

## Полезные команды

```bash
# Статус сервера
systemctl status kolesoblya

# Логи (ошибки)
journalctl -u kolesoblya -f

# Перезапуск
systemctl restart kolesoblya

# Бэкап базы (прогресс игроков)
cp /opt/kolesoblya/kolesoblya.db ~/backup-$(date +%F).db
```

---

## Частые проблемы

**Страница не открывается**  
→ Проверь firewall (порт 80), `systemctl status kolesoblya`, `nginx -t`

**Вошёл, но ходы не синхронизируются**  
→ WebSocket: nginx должен проксировать Upgrade (конфиг уже в `deploy/nginx-kolesoblya.conf`)

**502 Bad Gateway**  
→ `systemctl restart kolesoblya`, смотри `journalctl -u kolesoblya -n 50`

**Мало RAM при сборке**  
→ `install.sh` создаёт swap 2G автоматически

---

## Структура на сервере

```
/opt/kolesoblya/
├── data/              ← правишь списки игр
├── kolesoblya.db      ← прогресс (бэкапь!)
├── .env               ← секреты, не в git
├── frontend/dist/     ← собранный UI
└── uploads/avatars/   ← аватарки игроков
```
