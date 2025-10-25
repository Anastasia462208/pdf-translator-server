# Руководство по развертыванию PDF Translator Server

## 🚀 Быстрый старт

### Вариант 1: Автоматическая установка (рекомендуется)

Для быстрой установки на Ubuntu сервере используйте скрипт `deploy.sh`:

```bash
# Клонируйте репозиторий
git clone https://github.com/Anastasia462208/pdf-translator-server.git
cd pdf-translator-server

# Запустите скрипт установки
chmod +x deploy.sh
./deploy.sh
```

Скрипт автоматически:
- Установит Python и зависимости
- Создаст виртуальное окружение
- Установит все необходимые пакеты
- Настроит Nginx (опционально)
- Создаст systemd service для автозапуска (опционально)

### Вариант 2: Ручная установка

#### Шаг 1: Подготовка сервера

```bash
# Обновление системы
sudo apt-get update
sudo apt-get upgrade -y

# Установка Python и необходимых пакетов
sudo apt-get install -y python3 python3-pip python3-venv git
```

#### Шаг 2: Клонирование репозитория

```bash
cd /home/YOUR_USER
git clone https://github.com/Anastasia462208/pdf-translator-server.git
cd pdf-translator-server
```

#### Шаг 3: Настройка Python окружения

```bash
# Создание виртуального окружения
python3 -m venv venv

# Активация окружения
source venv/bin/activate

# Установка зависимостей
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

#### Шаг 4: Создание рабочих директорий

```bash
mkdir -p uploads outputs
```

#### Шаг 5: Тестовый запуск

```bash
# Запуск в режиме разработки
python server.py --host 0.0.0.0 --port 5000
```

Откройте браузер и перейдите по адресу `http://YOUR_SERVER_IP:5000`

---

## 🔧 Production развертывание

### Настройка Gunicorn

Gunicorn - это production WSGI сервер для Python приложений.

#### Установка

```bash
source venv/bin/activate
pip install gunicorn
```

#### Запуск

```bash
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 600 server:app
```

Параметры:
- `-w 4` - количество worker процессов (рекомендуется 2-4 × количество CPU ядер)
- `-b 0.0.0.0:5000` - адрес и порт для прослушивания
- `--timeout 600` - таймаут для обработки запросов (важно для больших PDF)

### Настройка Systemd Service

Создайте файл `/etc/systemd/system/pdf-translator.service`:

```ini
[Unit]
Description=PDF Translator Server
After=network.target

[Service]
User=YOUR_USER
WorkingDirectory=/home/YOUR_USER/pdf-translator-server
Environment="PATH=/home/YOUR_USER/pdf-translator-server/venv/bin"
ExecStart=/home/YOUR_USER/pdf-translator-server/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 --timeout 600 server:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Замените `YOUR_USER` на ваше имя пользователя!**

#### Управление сервисом

```bash
# Перезагрузка конфигурации systemd
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable pdf-translator

# Запуск сервиса
sudo systemctl start pdf-translator

# Проверка статуса
sudo systemctl status pdf-translator

# Остановка сервиса
sudo systemctl stop pdf-translator

# Перезапуск сервиса
sudo systemctl restart pdf-translator

# Просмотр логов
sudo journalctl -u pdf-translator -f
```

### Настройка Nginx

Nginx будет работать как reverse proxy перед Gunicorn.

#### Установка Nginx

```bash
sudo apt-get install -y nginx
```

#### Создание конфигурации

Создайте файл `/etc/nginx/sites-available/pdf-translator`:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # Замените на ваш домен или IP

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Увеличенные таймауты для обработки больших файлов
        proxy_connect_timeout 600;
        proxy_send_timeout 600;
        proxy_read_timeout 600;
        send_timeout 600;
    }

    # Максимальный размер загружаемого файла
    client_max_body_size 50M;
}
```

#### Активация конфигурации

```bash
# Создание символической ссылки
sudo ln -s /etc/nginx/sites-available/pdf-translator /etc/nginx/sites-enabled/

# Удаление дефолтной конфигурации (опционально)
sudo rm /etc/nginx/sites-enabled/default

# Проверка конфигурации
sudo nginx -t

# Перезагрузка Nginx
sudo systemctl reload nginx
```

### Настройка SSL (HTTPS) с Let's Encrypt

```bash
# Установка Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Получение SSL сертификата
sudo certbot --nginx -d your-domain.com

# Автоматическое обновление сертификата
sudo certbot renew --dry-run
```

---

## 🔒 Безопасность

### Firewall (UFW)

```bash
# Включение UFW
sudo ufw enable

# Разрешение SSH
sudo ufw allow ssh

# Разрешение HTTP и HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Проверка статуса
sudo ufw status
```

### Ограничение доступа к API

Для ограничения доступа к API можно добавить аутентификацию. Пример с API ключами в Nginx:

```nginx
location /api/ {
    if ($http_x_api_key != "YOUR_SECRET_KEY") {
        return 403;
    }
    proxy_pass http://127.0.0.1:5000;
    # ... остальные настройки proxy
}
```

---

## 📊 Мониторинг

### Просмотр логов

```bash
# Логи systemd service
sudo journalctl -u pdf-translator -f

# Логи Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Проверка использования ресурсов

```bash
# Процессы Python
ps aux | grep gunicorn

# Использование памяти
free -h

# Использование диска
df -h

# Размер папок uploads и outputs
du -sh /home/YOUR_USER/pdf-translator-server/uploads
du -sh /home/YOUR_USER/pdf-translator-server/outputs
```

---

## 🧹 Обслуживание

### Очистка временных файлов

Создайте cron задачу для автоматической очистки старых файлов:

```bash
# Открыть crontab
crontab -e

# Добавить задачу (очистка файлов старше 24 часов каждый день в 3:00)
0 3 * * * find /home/YOUR_USER/pdf-translator-server/uploads -type f -mtime +1 -delete
0 3 * * * find /home/YOUR_USER/pdf-translator-server/outputs -type f -mtime +1 -delete
```

### Обновление кода

```bash
cd /home/YOUR_USER/pdf-translator-server

# Получение обновлений
git pull origin master

# Активация окружения
source venv/bin/activate

# Обновление зависимостей (если изменились)
pip install -r requirements.txt

# Перезапуск сервиса
sudo systemctl restart pdf-translator
```

---

## 🐛 Решение проблем

### Сервер не запускается

```bash
# Проверка логов
sudo journalctl -u pdf-translator -n 50

# Проверка портов
sudo netstat -tulpn | grep 5000

# Проверка прав доступа
ls -la /home/YOUR_USER/pdf-translator-server
```

### Ошибки при переводе

```bash
# Проверка доступа к Google Translate
curl -I https://translate.google.com

# Проверка установки PyMuPDF
source venv/bin/activate
python -c "import fitz; print(fitz.__version__)"
```

### Проблемы с памятью

Если сервер использует слишком много памяти, уменьшите количество workers в Gunicorn:

```bash
# В файле /etc/systemd/system/pdf-translator.service
# Измените -w 4 на -w 2
ExecStart=/home/YOUR_USER/pdf-translator-server/venv/bin/gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 server:app

# Перезагрузите конфигурацию
sudo systemctl daemon-reload
sudo systemctl restart pdf-translator
```

---

## 📝 Примечания

- **Сервер 144.31.30.28**: Если вы хотите развернуть на вашем существующем сервере (144.31.30.28), следуйте инструкциям выше, заменив пути и пользователя на соответствующие.

- **Порты**: По умолчанию используется порт 5000. Убедитесь, что он не занят другими приложениями.

- **Ресурсы**: Для обработки больших PDF файлов рекомендуется минимум 2GB RAM.

- **Резервное копирование**: Регулярно создавайте резервные копии конфигурационных файлов и базы данных (если используется).

---

## 🔗 Полезные ссылки

- **GitHub репозиторий**: https://github.com/Anastasia462208/pdf-translator-server
- **Документация Flask**: https://flask.palletsprojects.com/
- **Документация Gunicorn**: https://docs.gunicorn.org/
- **Документация Nginx**: https://nginx.org/ru/docs/

---

## 💡 Рекомендации

1. **Используйте HTTPS** в production для защиты данных
2. **Настройте мониторинг** для отслеживания работоспособности
3. **Регулярно обновляйте** зависимости для безопасности
4. **Настройте автоматическую очистку** временных файлов
5. **Используйте CDN** для статических файлов при высокой нагрузке

---

Создано для автоматизации перевода PDF документов 🚀

