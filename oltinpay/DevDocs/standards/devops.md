# DEVOPS GUIDE
## Для Claude Code — PM2 + Nginx + Ubuntu

> **Цель:** Единый стиль деплоя и настройки серверов
> **Референс:** PM2, Nginx, Ubuntu официальная документация
> **Версия:** Ubuntu 22.04+, Nginx 1.24+, PM2 5+

---

## 🎯 КЛЮЧЕВЫЕ ПРИНЦИПЫ

```
ВСЕГДА                              НИКОГДА
────────────────────────────────    ────────────────────────────────
✓ Non-root пользователь для apps    ✗ Запуск от root
✓ PM2 ecosystem.config.js           ✗ Ручной pm2 start
✓ Nginx reverse proxy               ✗ Прямой доступ к Node.js портам
✓ SSL через Certbot                 ✗ HTTP в production
✓ UFW firewall                      ✗ Открытые порты
✓ Environment variables             ✗ Secrets в коде
✓ pm2 startup + pm2 save            ✗ Ручной запуск после reboot
✓ Log rotation                      ✗ Бесконечные логи
```

---

## 🖥️ НАСТРОЙКА СЕРВЕРА (Ubuntu)

### Начальная настройка

```bash
# ═══════════════════════════════════════════════════════════════════
# Обновление системы
# ═══════════════════════════════════════════════════════════════════
sudo apt update && sudo apt upgrade -y

# ═══════════════════════════════════════════════════════════════════
# Создание пользователя для деплоя
# ═══════════════════════════════════════════════════════════════════
sudo adduser deploy
sudo usermod -aG sudo deploy

# Настройка SSH для пользователя
sudo mkdir -p /home/deploy/.ssh
sudo cp ~/.ssh/authorized_keys /home/deploy/.ssh/
sudo chown -R deploy:deploy /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
sudo chmod 600 /home/deploy/.ssh/authorized_keys

# ═══════════════════════════════════════════════════════════════════
# Базовые утилиты
# ═══════════════════════════════════════════════════════════════════
sudo apt install -y \
    curl \
    wget \
    git \
    htop \
    vim \
    unzip \
    build-essential
```

### Firewall (UFW)

```bash
# ═══════════════════════════════════════════════════════════════════
# Настройка UFW
# ═══════════════════════════════════════════════════════════════════
sudo ufw default deny incoming
sudo ufw default allow outgoing

# SSH (ВАЖНО: сначала разрешить SSH!)
sudo ufw allow ssh
# или конкретный порт
sudo ufw allow 22/tcp

# HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Включение
sudo ufw enable

# Проверка
sudo ufw status verbose
```

### Установка Node.js

```bash
# ═══════════════════════════════════════════════════════════════════
# Node.js через NodeSource (рекомендуется)
# ═══════════════════════════════════════════════════════════════════

# Node.js 20 LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Проверка
node --version
npm --version

# ═══════════════════════════════════════════════════════════════════
# Альтернатива: NVM (для нескольких версий)
# ═══════════════════════════════════════════════════════════════════
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 20
nvm use 20
nvm alias default 20
```

### Установка PostgreSQL

```bash
# ═══════════════════════════════════════════════════════════════════
# PostgreSQL
# ═══════════════════════════════════════════════════════════════════
sudo apt install -y postgresql postgresql-contrib

# Запуск и автозапуск
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Создание пользователя и БД
sudo -u postgres psql

# В psql:
CREATE USER myapp WITH PASSWORD 'secure_password';
CREATE DATABASE myapp_db OWNER myapp;
GRANT ALL PRIVILEGES ON DATABASE myapp_db TO myapp;
\q

# Проверка подключения
psql -h localhost -U myapp -d myapp_db
```

### Установка Redis

```bash
# ═══════════════════════════════════════════════════════════════════
# Redis
# ═══════════════════════════════════════════════════════════════════
sudo apt install -y redis-server

# Настройка для production
sudo vim /etc/redis/redis.conf
# Изменить:
# supervised systemd
# maxmemory 256mb
# maxmemory-policy allkeys-lru

sudo systemctl restart redis
sudo systemctl enable redis

# Проверка
redis-cli ping  # PONG
```

---

## 📦 PM2

### Установка

```bash
# Глобальная установка
sudo npm install -g pm2

# Проверка
pm2 --version
```

### Ecosystem Config

```javascript
// ecosystem.config.js

module.exports = {
  apps: [
    {
      // ═══════════════════════════════════════════════════════════
      // Основное приложение
      // ═══════════════════════════════════════════════════════════
      name: 'api',
      script: './dist/index.js',

      // Cluster mode (использовать все CPU)
      instances: 'max',        // или конкретное число: 2, 4
      exec_mode: 'cluster',

      // Автоперезапуск
      autorestart: true,
      watch: false,            // true только для dev
      max_memory_restart: '1G',

      // Перезапуск при ошибках
      min_uptime: '10s',
      max_restarts: 10,
      restart_delay: 4000,

      // Логи
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      error_file: './logs/error.log',
      out_file: './logs/out.log',
      merge_logs: true,

      // Environment
      env: {
        NODE_ENV: 'development',
        PORT: 3000,
      },
      env_production: {
        NODE_ENV: 'production',
        PORT: 3000,
      },
    },

    {
      // ═══════════════════════════════════════════════════════════
      // Background Worker
      // ═══════════════════════════════════════════════════════════
      name: 'worker',
      script: './dist/worker.js',
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      cron_restart: '0 0 * * *',  // Перезапуск каждый день в полночь

      env_production: {
        NODE_ENV: 'production',
      },
    },
  ],

  // ═══════════════════════════════════════════════════════════════
  // Деплой конфигурация
  // ═══════════════════════════════════════════════════════════════
  deploy: {
    production: {
      user: 'deploy',
      host: ['server1.example.com'],
      ref: 'origin/main',
      repo: 'git@github.com:user/repo.git',
      path: '/var/www/myapp',
      'pre-deploy-local': '',
      'post-deploy': 'npm ci && npm run build && pm2 reload ecosystem.config.js --env production',
      'pre-setup': '',
    },
  },
};
```

### PM2 Команды

```bash
# ═══════════════════════════════════════════════════════════════════
# Запуск
# ═══════════════════════════════════════════════════════════════════
pm2 start ecosystem.config.js                    # Development
pm2 start ecosystem.config.js --env production   # Production

# Только определённое приложение
pm2 start ecosystem.config.js --only api

# ═══════════════════════════════════════════════════════════════════
# Управление
# ═══════════════════════════════════════════════════════════════════
pm2 list                    # Список процессов
pm2 status                  # Статус
pm2 show api                # Детали приложения

pm2 restart api             # Перезапуск (с downtime)
pm2 reload api              # Graceful reload (без downtime, для cluster)
pm2 stop api                # Остановка
pm2 delete api              # Удаление из PM2

pm2 restart all             # Перезапуск всех
pm2 reload all              # Reload всех

# ═══════════════════════════════════════════════════════════════════
# Масштабирование
# ═══════════════════════════════════════════════════════════════════
pm2 scale api +2            # Добавить 2 инстанса
pm2 scale api 4             # Установить 4 инстанса

# ═══════════════════════════════════════════════════════════════════
# Мониторинг
# ═══════════════════════════════════════════════════════════════════
pm2 monit                   # Интерактивный монитор
pm2 logs                    # Все логи
pm2 logs api                # Логи приложения
pm2 logs api --lines 100    # Последние 100 строк

# ═══════════════════════════════════════════════════════════════════
# Автозапуск при перезагрузке сервера
# ═══════════════════════════════════════════════════════════════════
pm2 startup                 # Генерирует команду для systemd
# Выполнить команду, которую покажет PM2

pm2 save                    # Сохранить текущий список процессов

# После изменений:
pm2 save                    # Пересохранить

# ═══════════════════════════════════════════════════════════════════
# Логи
# ═══════════════════════════════════════════════════════════════════
pm2 flush                   # Очистить все логи
pm2 reloadLogs              # Reload log files

# Log rotation
pm2 install pm2-logrotate
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:retain 7
pm2 set pm2-logrotate:compress true
```

### PM2 с Python (FastAPI/uvicorn)

```javascript
// ecosystem.config.js для Python

module.exports = {
  apps: [
    {
      name: 'fastapi',
      script: 'uvicorn',
      args: 'src.main:app --host 0.0.0.0 --port 8000',
      interpreter: '/home/deploy/myapp/.venv/bin/python',
      cwd: '/var/www/myapp',

      instances: 1,           // uvicorn сам управляет workers
      exec_mode: 'fork',
      autorestart: true,
      max_memory_restart: '1G',

      env_production: {
        NODE_ENV: 'production',
      },
    },
  ],
};
```

---

## 🌐 NGINX

### Установка

```bash
sudo apt install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Проверка
sudo nginx -t
```

### Базовая конфигурация

```nginx
# /etc/nginx/sites-available/myapp

# Upstream (для load balancing)
upstream node_app {
    server 127.0.0.1:3000;
    # server 127.0.0.1:3001;  # Дополнительные инстансы
    keepalive 64;
}

server {
    listen 80;
    server_name example.com www.example.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name example.com www.example.com;

    # ═══════════════════════════════════════════════════════════════
    # SSL (будет настроено Certbot)
    # ═══════════════════════════════════════════════════════════════
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # ═══════════════════════════════════════════════════════════════
    # Security Headers
    # ═══════════════════════════════════════════════════════════════
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # ═══════════════════════════════════════════════════════════════
    # Gzip
    # ═══════════════════════════════════════════════════════════════
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript application/xml;

    # ═══════════════════════════════════════════════════════════════
    # Logs
    # ═══════════════════════════════════════════════════════════════
    access_log /var/log/nginx/myapp.access.log;
    error_log /var/log/nginx/myapp.error.log;

    # ═══════════════════════════════════════════════════════════════
    # Static files (если есть)
    # ═══════════════════════════════════════════════════════════════
    location /static/ {
        alias /var/www/myapp/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # ═══════════════════════════════════════════════════════════════
    # API Proxy
    # ═══════════════════════════════════════════════════════════════
    location / {
        proxy_pass http://node_app;
        proxy_http_version 1.1;

        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # ═══════════════════════════════════════════════════════════════
    # Health check (для мониторинга)
    # ═══════════════════════════════════════════════════════════════
    location /health {
        proxy_pass http://node_app/health;
        access_log off;
    }
}
```

### Активация сайта

```bash
# Создать symlink
sudo ln -s /etc/nginx/sites-available/myapp /etc/nginx/sites-enabled/

# Удалить default (опционально)
sudo rm /etc/nginx/sites-enabled/default

# Проверить конфигурацию
sudo nginx -t

# Перезагрузить
sudo systemctl reload nginx
```

### SSL с Certbot

```bash
# ═══════════════════════════════════════════════════════════════════
# Установка Certbot
# ═══════════════════════════════════════════════════════════════════
sudo apt install -y certbot python3-certbot-nginx

# ═══════════════════════════════════════════════════════════════════
# Получение сертификата
# ═══════════════════════════════════════════════════════════════════
sudo certbot --nginx -d example.com -d www.example.com

# ═══════════════════════════════════════════════════════════════════
# Автообновление (уже настроено автоматически)
# ═══════════════════════════════════════════════════════════════════
# Проверить timer
sudo systemctl status certbot.timer

# Тест обновления
sudo certbot renew --dry-run
```

### Nginx для нескольких приложений

```nginx
# /etc/nginx/sites-available/apps

# App 1 - API
upstream api_app {
    server 127.0.0.1:3000;
}

# App 2 - Admin
upstream admin_app {
    server 127.0.0.1:3001;
}

# App 3 - FastAPI
upstream python_app {
    server 127.0.0.1:8000;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    # SSL...

    location / {
        proxy_pass http://api_app;
        # proxy headers...
    }
}

server {
    listen 443 ssl http2;
    server_name admin.example.com;

    # SSL...

    location / {
        proxy_pass http://admin_app;
        # proxy headers...
    }
}

server {
    listen 443 ssl http2;
    server_name backend.example.com;

    # SSL...

    location / {
        proxy_pass http://python_app;
        # proxy headers...
    }
}
```

---

## 📂 СТРУКТУРА ДЕПЛОЯ

```
/var/www/
├── myapp/
│   ├── current -> releases/20241201120000    # Symlink на текущий релиз
│   ├── releases/
│   │   ├── 20241201120000/                   # Релиз 1
│   │   │   ├── dist/
│   │   │   ├── node_modules/
│   │   │   ├── ecosystem.config.js
│   │   │   └── ...
│   │   └── 20241130100000/                   # Релиз 2 (предыдущий)
│   ├── shared/
│   │   ├── .env                              # Environment variables
│   │   └── logs/                             # Persistent logs
│   └── repo/                                 # Git репозиторий
│
└── another-app/
    └── ...
```

---

## 🚀 ДЕПЛОЙ СКРИПТЫ

### Простой деплой

```bash
#!/bin/bash
# deploy.sh

set -e

APP_DIR="/var/www/myapp"
REPO_URL="git@github.com:user/repo.git"
BRANCH="main"

echo "🚀 Starting deployment..."

# Переходим в директорию
cd $APP_DIR

# Pull latest changes
git pull origin $BRANCH

# Install dependencies
npm ci --production

# Build
npm run build

# Restart PM2
pm2 reload ecosystem.config.js --env production

echo "✅ Deployment completed!"
```

### Zero-downtime деплой

```bash
#!/bin/bash
# deploy-zero-downtime.sh

set -e

APP_NAME="myapp"
APP_DIR="/var/www/$APP_NAME"
RELEASES_DIR="$APP_DIR/releases"
SHARED_DIR="$APP_DIR/shared"
REPO_DIR="$APP_DIR/repo"
CURRENT_LINK="$APP_DIR/current"

TIMESTAMP=$(date +%Y%m%d%H%M%S)
RELEASE_DIR="$RELEASES_DIR/$TIMESTAMP"
KEEP_RELEASES=5

echo "🚀 Deploying $APP_NAME..."

# ═══════════════════════════════════════════════════════════════════
# 1. Clone/Update repository
# ═══════════════════════════════════════════════════════════════════
if [ ! -d "$REPO_DIR" ]; then
    git clone $REPO_URL $REPO_DIR
fi

cd $REPO_DIR
git fetch origin
git reset --hard origin/main

# ═══════════════════════════════════════════════════════════════════
# 2. Create new release
# ═══════════════════════════════════════════════════════════════════
mkdir -p $RELEASE_DIR
cp -r $REPO_DIR/* $RELEASE_DIR/

cd $RELEASE_DIR

# ═══════════════════════════════════════════════════════════════════
# 3. Link shared files
# ═══════════════════════════════════════════════════════════════════
ln -sf $SHARED_DIR/.env $RELEASE_DIR/.env
ln -sf $SHARED_DIR/logs $RELEASE_DIR/logs

# ═══════════════════════════════════════════════════════════════════
# 4. Install & Build
# ═══════════════════════════════════════════════════════════════════
npm ci --production
npm run build

# ═══════════════════════════════════════════════════════════════════
# 5. Switch symlink (atomic operation)
# ═══════════════════════════════════════════════════════════════════
ln -sfn $RELEASE_DIR $CURRENT_LINK

# ═══════════════════════════════════════════════════════════════════
# 6. Reload PM2
# ═══════════════════════════════════════════════════════════════════
cd $CURRENT_LINK
pm2 reload ecosystem.config.js --env production

# ═══════════════════════════════════════════════════════════════════
# 7. Cleanup old releases
# ═══════════════════════════════════════════════════════════════════
cd $RELEASES_DIR
ls -t | tail -n +$((KEEP_RELEASES + 1)) | xargs -r rm -rf

echo "✅ Deployed $APP_NAME to $RELEASE_DIR"
```

### GitHub Actions

```yaml
# .github/workflows/deploy.yml

name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Build
        run: npm run build

      - name: Run tests
        run: npm test

      - name: Deploy to server
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /var/www/myapp
            git pull origin main
            npm ci --production
            npm run build
            pm2 reload ecosystem.config.js --env production
```

---

## 📊 МОНИТОРИНГ

### Логи

```bash
# ═══════════════════════════════════════════════════════════════════
# PM2 логи
# ═══════════════════════════════════════════════════════════════════
pm2 logs                    # Все логи в реальном времени
pm2 logs api --lines 200    # Последние 200 строк
pm2 flush                   # Очистить логи

# ═══════════════════════════════════════════════════════════════════
# Nginx логи
# ═══════════════════════════════════════════════════════════════════
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# ═══════════════════════════════════════════════════════════════════
# System logs
# ═══════════════════════════════════════════════════════════════════
journalctl -u nginx -f
journalctl -u postgresql -f
dmesg | tail -20
```

### Системный мониторинг

```bash
# ═══════════════════════════════════════════════════════════════════
# Ресурсы
# ═══════════════════════════════════════════════════════════════════
htop                        # Интерактивный монитор
free -h                     # Память
df -h                       # Диск
du -sh /var/www/*           # Размер директорий

# ═══════════════════════════════════════════════════════════════════
# Сеть
# ═══════════════════════════════════════════════════════════════════
ss -tulpn                   # Открытые порты
netstat -an | grep :3000    # Подключения к порту

# ═══════════════════════════════════════════════════════════════════
# Процессы
# ═══════════════════════════════════════════════════════════════════
ps aux | grep node
ps aux | grep nginx
```

---

## 🔒 БЕЗОПАСНОСТЬ

### SSH Hardening

```bash
# /etc/ssh/sshd_config

# Отключить root login
PermitRootLogin no

# Только SSH ключи
PasswordAuthentication no
PubkeyAuthentication yes

# Ограничить пользователей
AllowUsers deploy

# Изменить порт (опционально)
# Port 2222

# Перезапуск SSH
sudo systemctl restart sshd
```

### Fail2ban

```bash
# Установка
sudo apt install -y fail2ban

# Конфигурация
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo vim /etc/fail2ban/jail.local

# Настройки:
# [sshd]
# enabled = true
# port = ssh
# filter = sshd
# logpath = /var/log/auth.log
# maxretry = 3
# bantime = 3600

sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Статус
sudo fail2ban-client status sshd
```

### Автообновления безопасности

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## ✅ ЧЕКЛИСТ ДЕПЛОЯ

```
СЕРВЕР
□ Ubuntu обновлён
□ Non-root пользователь создан
□ SSH ключи настроены
□ UFW включён (22, 80, 443)
□ Fail2ban установлен

ПРИЛОЖЕНИЕ
□ Node.js/Python установлен
□ PM2 установлен глобально
□ ecosystem.config.js создан
□ pm2 startup выполнен
□ pm2 save выполнен
□ Log rotation настроен

NGINX
□ Nginx установлен
□ Site config создан
□ Symlink в sites-enabled
□ nginx -t проходит
□ SSL сертификат получен
□ HTTP→HTTPS редирект

БАЗА ДАННЫХ
□ PostgreSQL установлен
□ Пользователь и БД созданы
□ Бэкапы настроены

МОНИТОРИНГ
□ Логи доступны
□ pm2 monit работает
□ Health check endpoint
```

---

## 🚀 БЫСТРЫЕ КОМАНДЫ

```bash
# ═══════════════════════════════════════════════════════════════════
# Полный деплой с нуля
# ═══════════════════════════════════════════════════════════════════

# 1. Сервер
sudo apt update && sudo apt upgrade -y
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs nginx certbot python3-certbot-nginx

# 2. PM2
sudo npm install -g pm2
pm2 startup
# Выполнить команду из вывода

# 3. Приложение
cd /var/www/myapp
npm ci --production
npm run build

# 4. PM2 запуск
pm2 start ecosystem.config.js --env production
pm2 save

# 5. Nginx
sudo vim /etc/nginx/sites-available/myapp
sudo ln -s /etc/nginx/sites-available/myapp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 6. SSL
sudo certbot --nginx -d example.com

# ═══════════════════════════════════════════════════════════════════
# Обновление приложения
# ═══════════════════════════════════════════════════════════════════
cd /var/www/myapp
git pull
npm ci --production
npm run build
pm2 reload ecosystem.config.js --env production
```

---

**Версия:** 1.0
**Дата:** 01.12.2025
