# PDF Translator Server

Веб-сервер для перевода PDF документов с сохранением структуры, форматирования и изображений.

## Возможности

- 📄 Перевод PDF документов с сохранением структуры
- 🖼️ Извлечение и сохранение изображений
- 🌍 Поддержка множества языков (английский, русский, немецкий, французский, испанский и др.)
- 📚 Поддержка пользовательских словарей терминов
- 🎨 Генерация HTML-документа с переводом
- 📦 Скачивание результата в виде ZIP-архива
- 🔄 Асинхронная обработка с отображением прогресса
- 🔌 REST API для программного доступа

## Требования

- Python 3.8+
- pip

## Установка

### 1. Клонирование репозитория

```bash
git clone https://github.com/YOUR_USERNAME/pdf-translator-server.git
cd pdf-translator-server
```

### 2. Создание виртуального окружения

```bash
python3 -m venv venv
source venv/bin/activate  # Для Linux/Mac
# или
venv\Scripts\activate  # Для Windows
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

## Запуск

### Локальный запуск

```bash
python server.py
```

Сервер будет доступен по адресу: http://localhost:5000

### Запуск с доступом из сети

```bash
python server.py --host 0.0.0.0 --port 5000
```

### Запуск на production сервере

Для production рекомендуется использовать **Gunicorn** или **uWSGI** с **Nginx**.

#### Установка Gunicorn

```bash
pip install gunicorn
```

#### Запуск с Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:5000 server:app
```

#### Настройка Systemd Service

Создайте файл `/etc/systemd/system/pdf-translator.service`:

```ini
[Unit]
Description=PDF Translator Server
After=network.target

[Service]
User=YOUR_USER
WorkingDirectory=/path/to/pdf-translator-server
Environment="PATH=/path/to/pdf-translator-server/venv/bin"
ExecStart=/path/to/pdf-translator-server/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 server:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Запустите сервис:

```bash
sudo systemctl daemon-reload
sudo systemctl enable pdf-translator
sudo systemctl start pdf-translator
```

#### Настройка Nginx

Создайте файл `/etc/nginx/sites-available/pdf-translator`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Увеличиваем таймауты для больших файлов
        proxy_connect_timeout 600;
        proxy_send_timeout 600;
        proxy_read_timeout 600;
        send_timeout 600;
    }

    # Увеличиваем максимальный размер загружаемого файла
    client_max_body_size 50M;
}
```

Активируйте конфигурацию:

```bash
sudo ln -s /etc/nginx/sites-available/pdf-translator /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Использование

### Веб-интерфейс

1. Откройте браузер и перейдите по адресу http://localhost:5000
2. Загрузите PDF файл
3. Выберите исходный и целевой языки
4. (Опционально) Добавьте словарь терминов в формате JSON
5. Нажмите "Перевести документ"
6. Дождитесь завершения обработки
7. Скачайте результат или просмотрите в браузере

### REST API

#### Загрузка документа для перевода

```bash
curl -X POST http://localhost:5000/api/translate \
  -F "pdf=@document.pdf" \
  -F "source_lang=en" \
  -F "target_lang=ru" \
  -F 'terminology_json={"AI":"ИИ","Machine Learning":"Машинное обучение"}'
```

Ответ:

```json
{
  "success": true,
  "task_id": "uuid-here",
  "status_url": "/api/status/uuid-here",
  "download_url": "/download/uuid-here"
}
```

#### Проверка статуса

```bash
curl http://localhost:5000/api/status/uuid-here
```

Ответ:

```json
{
  "status": "processing",
  "progress": 45,
  "stage": "Перевод текста..."
}
```

#### Скачивание результата

```bash
curl -O http://localhost:5000/download/uuid-here
```

## Формат словаря терминов

Словарь терминов должен быть в формате JSON:

```json
{
  "Artificial Intelligence": "Искусственный интеллект",
  "Machine Learning": "Машинное обучение",
  "Neural Network": "Нейронная сеть"
}
```

## Структура проекта

```
pdf-translator-server/
├── server.py              # Основной файл сервера
├── requirements.txt       # Зависимости Python
├── README.md             # Документация
├── uploads/              # Папка для загруженных файлов (создается автоматически)
└── outputs/              # Папка для результатов (создается автоматически)
```

## Ограничения

- Максимальный размер файла: 50 МБ
- Поддерживаемые форматы: только PDF

## Технологии

- **Flask** - веб-фреймворк
- **PyMuPDF (fitz)** - работа с PDF
- **deep-translator** - перевод текста через Google Translate
- **Threading** - асинхронная обработка

## Лицензия

MIT

## Автор

Создано для автоматизации перевода PDF документов с сохранением форматирования.

