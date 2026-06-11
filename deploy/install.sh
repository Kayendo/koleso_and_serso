#!/usr/bin/env bash
# Установка Kolesoblya на чистый Ubuntu 22.04/24.04 (VPS).
# Запуск на сервере: sudo bash deploy/install.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/kolesoblya}"
APP_USER="${APP_USER:-kolesoblya}"
REPO_URL="${REPO_URL:-https://github.com/Kayendo/koleso_and_serso.git}"
BRANCH="${BRANCH:-master}"

if [[ "${EUID:-0}" -ne 0 ]]; then
  echo "Запусти от root: sudo bash deploy/install.sh"
  exit 1
fi

echo "==> Пакеты системы"
apt-get update -qq
apt-get install -y -qq git curl nginx python3 python3-venv python3-pip \
  build-essential ca-certificates

if ! command -v node >/dev/null 2>&1 || [[ "$(node -v 2>/dev/null || echo v0)" < "v18" ]]; then
  echo "==> Node.js 20"
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y -qq nodejs
fi

if [[ ! -f /swapfile ]] && [[ "$(free -m | awk '/^Swap:/{print $2}')" -eq 0 ]]; then
  echo "==> Swap 2G (для npm build)"
  fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

if ! id "$APP_USER" &>/dev/null; then
  echo "==> Пользователь $APP_USER"
  useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
fi

mkdir -p "$APP_DIR"
if [[ ! -d "$APP_DIR/.git" ]]; then
  echo "==> Клон репозитория"
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
else
  echo "==> Обновление репозитория"
  sudo -u "$APP_USER" git -C "$APP_DIR" fetch origin
  sudo -u "$APP_USER" git -C "$APP_DIR" checkout "$BRANCH"
  sudo -u "$APP_USER" git -C "$APP_DIR" pull --ff-only origin "$BRANCH" || true
fi

chown -R "$APP_USER:$APP_USER" "$APP_DIR"

echo "==> Python venv + зависимости"
sudo -u "$APP_USER" python3 -m venv "$APP_DIR/.venv"
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

echo "==> Сборка фронтенда"
sudo -u "$APP_USER" bash -lc "cd '$APP_DIR/frontend' && npm ci && npx vite build"

if [[ ! -f "$APP_DIR/.env" ]]; then
  echo "==> .env"
  SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  cp "$APP_DIR/deploy/env.production.example" "$APP_DIR/.env"
  sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET/" "$APP_DIR/.env"
  chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
  echo "Создан $APP_DIR/.env — при необходимости отредактируй ALLOWED_ORIGINS"
fi

mkdir -p "$APP_DIR/uploads/avatars"
chown -R "$APP_USER:$APP_USER" "$APP_DIR/uploads"

echo "==> systemd"
cp "$APP_DIR/deploy/kolesoblya.service" /etc/systemd/system/kolesoblya.service
systemctl daemon-reload
systemctl enable kolesoblya
systemctl restart kolesoblya

echo "==> nginx"
NGINX_SITE="/etc/nginx/sites-available/kolesoblya"
cp "$APP_DIR/deploy/nginx-kolesoblya.conf" "$NGINX_SITE"
ln -sf "$NGINX_SITE" /etc/nginx/sites-enabled/kolesoblya
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo ""
echo "Готово. Сервер слушает порт 80."
echo "1) Отредактируй server_name в $NGINX_SITE (IP или домен)"
echo "2) nginx -t && systemctl reload nginx"
echo "3) Открой в браузере: http://IP_СЕРВЕРА"
echo "4) Логин admin / admin99 — смени пароль в backend/accounts.py и redeploy"
echo ""
systemctl --no-pager status kolesoblya | head -5
