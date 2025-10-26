# Руководство по развертыванию PDF Translator

Подробное руководство по развертыванию приложения на различных платформах.

## 🐳 Docker (Рекомендуется)

### Локальное развертывание

```bash
# Клонировать репозиторий
git clone https://github.com/Anastasia462208/pdf-translator-server.git
cd pdf-translator-server

# Создать .env файл
echo "OPENAI_API_KEY=your-api-key-here" > .env

# Собрать образ
docker build -t pdf-translator .

# Запустить контейнер
docker run -d \
  --name pdf-translator \
  -p 5000:5000 \
  --env-file .env \
  pdf-translator

# Проверить логи
docker logs pdf-translator

# Остановить
docker stop pdf-translator

# Удалить
docker rm pdf-translator
```

### Docker Compose

Создайте `docker-compose.yml`:

```yaml
version: '3.8'

services:
  pdf-translator:
    build: .
    ports:
      - "5000:5000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./uploads:/app/uploads
      - ./outputs:/app/outputs
    restart: unless-stopped
```

Запуск:

```bash
docker-compose up -d
```

## 🖥️ VPS/Dedicated Server (Ubuntu)

### 1. Подготовка сервера

```bash
# Обновление системы
sudo apt-get update
sudo apt-get upgrade -y

# Установка Python и зависимостей
sudo apt-get install -y python3.11 python3-pip git fonts-dejavu nginx

# Создание пользователя (опционально)
sudo adduser pdfapp
sudo usermod -aG sudo pdfapp
su - pdfapp
```

### 2. Установка приложения

```bash
# Клонирование
cd ~
git clone https://github.com/Anastasia462208/pdf-translator-server.git
cd pdf-translator-server

# Виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
pip install gunicorn

# Настройка переменных окружения
nano .env
# Добавьте: OPENAI_API_KEY=your-key-here
```

### 3. Systemd Service

Создайте `/etc/systemd/system/pdf-translator.service`:

```ini
[Unit]
Description=PDF Translator Service
After=network.target

[Service]
Type=simple
User=pdfapp
WorkingDirectory=/home/pdfapp/pdf-translator-server
Environment="PATH=/home/pdfapp/pdf-translator-server/venv/bin"
EnvironmentFile=/home/pdfapp/pdf-translator-server/.env
ExecStart=/home/pdfapp/pdf-translator-server/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:5000 \
    --timeout 300 \
    --access-logfile /var/log/pdf-translator/access.log \
    --error-logfile /var/log/pdf-translator/error.log \
    web_app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Создайте директорию для логов:

```bash
sudo mkdir -p /var/log/pdf-translator
sudo chown pdfapp:pdfapp /var/log/pdf-translator
```

Запустите сервис:

```bash
sudo systemctl daemon-reload
sudo systemctl enable pdf-translator
sudo systemctl start pdf-translator
sudo systemctl status pdf-translator
```

### 4. Nginx Reverse Proxy

Создайте `/etc/nginx/sites-available/pdf-translator`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Логи
    access_log /var/log/nginx/pdf-translator-access.log;
    error_log /var/log/nginx/pdf-translator-error.log;

    # Максимальный размер файла
    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Увеличенные таймауты для больших файлов
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }

    # Статические файлы (если нужно)
    location /static {
        alias /home/pdfapp/pdf-translator-server/static;
        expires 30d;
    }
}
```

Активируйте конфигурацию:

```bash
sudo ln -s /etc/nginx/sites-available/pdf-translator /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5. SSL с Let's Encrypt

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## ☁️ Cloud Platforms

### Railway.app

1. Создайте аккаунт на [railway.app](https://railway.app)
2. Нажмите "New Project" → "Deploy from GitHub repo"
3. Выберите репозиторий
4. Добавьте переменную окружения: `OPENAI_API_KEY`
5. Railway автоматически определит Dockerfile и развернет приложение

### Render.com

1. Создайте аккаунт на [render.com](https://render.com)
2. Нажмите "New +" → "Web Service"
3. Подключите GitHub репозиторий
4. Настройки:
   - **Environment**: Docker
   - **Instance Type**: Starter (или выше)
   - **Environment Variables**: `OPENAI_API_KEY=your-key`
5. Нажмите "Create Web Service"

### Heroku

```bash
# Установка Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# Логин
heroku login

# Создание приложения
cd pdf-translator-server
heroku create your-app-name

# Установка переменных окружения
heroku config:set OPENAI_API_KEY=your-key

# Развертывание
git push heroku main

# Открыть приложение
heroku open
```

### DigitalOcean App Platform

1. Создайте аккаунт на [DigitalOcean](https://www.digitalocean.com)
2. Перейдите в "App Platform" → "Create App"
3. Подключите GitHub репозиторий
4. Настройки:
   - **Type**: Web Service
   - **Environment Variables**: `OPENAI_API_KEY`
   - **Instance Size**: Basic (1GB RAM минимум)
5. Нажмите "Create Resources"

### AWS EC2

```bash
# Подключение к EC2
ssh -i your-key.pem ubuntu@your-ec2-ip

# Установка Docker
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo usermod -aG docker ubuntu

# Клонирование и запуск
git clone https://github.com/Anastasia462208/pdf-translator-server.git
cd pdf-translator-server
echo "OPENAI_API_KEY=your-key" > .env
docker build -t pdf-translator .
docker run -d -p 80:5000 --env-file .env pdf-translator
```

## 🔧 Обслуживание

### Просмотр логов

```bash
# Systemd
sudo journalctl -u pdf-translator -f

# Docker
docker logs -f pdf-translator

# Nginx
sudo tail -f /var/log/nginx/pdf-translator-error.log
```

### Обновление приложения

```bash
# С systemd
cd ~/pdf-translator-server
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart pdf-translator

# С Docker
cd ~/pdf-translator-server
git pull
docker build -t pdf-translator .
docker stop pdf-translator
docker rm pdf-translator
docker run -d --name pdf-translator -p 5000:5000 --env-file .env pdf-translator
```

### Очистка временных файлов

Создайте cron job:

```bash
crontab -e
```

Добавьте:

```cron
# Очистка файлов старше 1 часа каждый час
0 * * * * find /home/pdfapp/pdf-translator-server/uploads -type f -mmin +60 -delete
0 * * * * find /home/pdfapp/pdf-translator-server/outputs -type f -mmin +60 -delete
```

## 🔒 Безопасность

### Базовая аутентификация (опционально)

Добавьте в Nginx конфигурацию:

```nginx
location / {
    auth_basic "Restricted Access";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://127.0.0.1:5000;
    # ... остальные настройки
}
```

Создайте пароль:

```bash
sudo apt-get install apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd admin
```

### Firewall

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 📊 Мониторинг

### Простой health check

```bash
curl http://localhost:5000/
```

### Uptime monitoring

Используйте сервисы:
- [UptimeRobot](https://uptimerobot.com)
- [Pingdom](https://www.pingdom.com)
- [StatusCake](https://www.statuscake.com)

## ❓ Проблемы и решения

### Приложение не запускается

```bash
# Проверить логи
sudo journalctl -u pdf-translator -n 50

# Проверить порт
sudo netstat -tulpn | grep 5000

# Проверить API ключ
cat .env
```

### Ошибки с шрифтами

```bash
# Переустановить шрифты
sudo apt-get install --reinstall fonts-dejavu
fc-cache -f -v
```

### Высокое использование памяти

Увеличьте RAM или уменьшите количество workers в gunicorn:

```bash
gunicorn --workers 2 --bind 127.0.0.1:5000 web_app:app
```

---

**Дополнительная помощь**: Откройте issue на GitHub

