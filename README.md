# PDF Translator with AI

Профессиональный веб-сервис для перевода PDF документов с сохранением форматирования, изображений и макета. Использует OpenAI API для высококачественного перевода с поддержкой специализированных терминологических словарей.

## 🌟 Основные возможности

- **AI-перевод высокого качества**: Использует GPT-4.1 Mini, GPT-4.1 Nano или Gemini 2.5 Flash
- **Сохранение форматирования**: Полное сохранение макета, шрифтов, цветов и позиций текста
- **Обработка изображений**: Извлечение и вставка изображений без потери качества
- **Специализированные словари**: Поддержка терминологических словарей (включен керамический словарь EN-RU)
- **Пакетная обработка**: Эффективная обработка больших документов
- **Контекстный перевод**: Учет контекста предыдущих переводов для связности
- **Unicode поддержка**: Корректная работа с кириллицей и другими алфавитами (DejaVu Sans)
- **Два режима вывода**:
  - Side-by-side (оригинал | перевод)
  - Translation-only (только перевод)
- **Веб-интерфейс**: Удобный интерфейс с drag & drop и прогресс-баром
- **CLI интерфейс**: Командная строка для автоматизации

## 📋 Требования

- Python 3.11+
- OpenAI API ключ
- Шрифты DejaVu (для кириллицы)
- Ubuntu 22.04 или аналогичная система

## 🚀 Быстрый старт

### 1. Клонирование репозитория

```bash
git clone https://github.com/Anastasia462208/pdf-translator-server.git
cd pdf-translator-server
```

### 2. Установка зависимостей

```bash
# Установка Python пакетов
pip install -r requirements.txt

# Установка шрифтов DejaVu (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y fonts-dejavu
```

### 3. Настройка API ключа

Создайте файл `.env` в корне проекта:

```bash
OPENAI_API_KEY=your-openai-api-key-here
```

Или установите переменную окружения:

```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

### 4. Запуск веб-сервера

```bash
python3 web_app.py
```

Откройте браузер: `http://localhost:5000`

## 💻 Использование

### Веб-интерфейс

1. Откройте `http://localhost:5000`
2. Загрузите PDF файл (drag & drop или выбор файла)
3. Выберите исходный и целевой языки
4. Выберите AI модель (рекомендуется gpt-4.1-mini)
5. Включите side-by-side режим (опционально)
6. Нажмите "Translate PDF"
7. Дождитесь завершения и скачайте результат

### Командная строка (CLI)

```bash
# Базовый перевод
python3 main.py input.pdf -o output.pdf -t ru

# Side-by-side режим
python3 main.py input.pdf -o output.pdf -t ru --side-by-side

# Выбор модели
python3 main.py input.pdf -o output.pdf -t ru --model gpt-4.1-mini

# Выбор исходного языка
python3 main.py input.pdf -o output.pdf -s en -t ru

# Справка
python3 main.py --help
```

## 🏗️ Архитектура

```
pdf-translator-server/
├── web_app.py              # Flask веб-сервер
├── main.py                 # CLI интерфейс
├── extractor.py            # Извлечение контента из PDF (PyMuPDF)
├── translator.py           # AI перевод (OpenAI API)
├── reconstructor.py        # Реконструкция PDF с переводом
├── config.py               # Конфигурация (языки, модели)
├── utils.py                # Вспомогательные функции
├── requirements.txt        # Python зависимости
├── templates/
│   └── index.html          # Веб-интерфейс
├── ceramic_dictionary_en_ru.json  # Керамический словарь (JSON)
└── ceramic_dictionary_en_ru.md    # Керамический словарь (Markdown)
```

## 🔧 Модули

### Extractor (extractor.py)
- Извлекает текст с позициями, шрифтами, размерами и цветами
- Извлекает изображения в полном разрешении
- Группирует текст в блоки для перевода

### Translator (translator.py)
- Использует OpenAI API для перевода
- Пакетная обработка (до 10 блоков за раз)
- Контекстно-зависимый перевод
- Поддержка специализированных промптов

### Reconstructor (reconstructor.py)
- Создает новый PDF с переводом
- Сохраняет макет и форматирование
- Side-by-side или translation-only режимы
- Автоматическое масштабирование текста

## 🌍 Поддерживаемые языки

Английский, Русский, Немецкий, Французский, Испанский, Итальянский, Португальский, Голландский, Польский, Чешский, Турецкий, Арабский, Китайский, Японский, Корейский и другие (25+ языков).

## 🤖 Поддерживаемые AI модели

- **gpt-4.1-mini** (рекомендуется) - баланс качества и скорости
- **gpt-4.1-nano** - быстрый, экономичный
- **gemini-2.5-flash** - альтернатива от Google

## 📚 Керамический словарь

Включен профессиональный англо-русский словарь керамических терминов (50+ терминов):
- Bisque → Утель (утиль)
- Glaze → Глазурь
- Slip → Шликер
- И многие другие...

Словарь доступен в двух форматах:
- `ceramic_dictionary_en_ru.json` - для программного использования
- `ceramic_dictionary_en_ru.md` - для чтения

## 🐳 Развертывание с Docker

```bash
# Создать Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python3", "web_app.py"]
EOF

# Собрать образ
docker build -t pdf-translator .

# Запустить контейнер
docker run -d -p 5000:5000 -e OPENAI_API_KEY=your-key pdf-translator
```

## 🚀 Production развертывание

### С Gunicorn

```bash
# Установка
pip install gunicorn

# Запуск
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 300 web_app:app
```

### С Nginx

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_connect_timeout 600;
        proxy_send_timeout 600;
        proxy_read_timeout 600;
    }

    client_max_body_size 50M;
}
```

### Systemd Service

```ini
[Unit]
Description=PDF Translator Service
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/path/to/pdf-translator-server
Environment="OPENAI_API_KEY=your-key"
ExecStart=/usr/bin/python3 web_app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## ⚠️ Известные ограничения

1. **Веб-интерфейс**: Таймаут ~60 секунд (для больших файлов используйте CLI)
2. **Размер файла**: Максимум 50 МБ
3. **Шрифты**: Используется DejaVu Sans для всех языков (оригинальные шрифты не сохраняются)
4. **Таблицы**: Сложные таблицы могут требовать ручной корректировки

## 🔍 Устранение неполадок

### Проблемы с кириллицей
Убедитесь, что установлены шрифты DejaVu:
```bash
sudo apt-get install fonts-dejavu
```

### Ошибки OpenAI API
Проверьте API ключ:
```bash
echo $OPENAI_API_KEY
```

### Проблемы с PyMuPDF
Переустановите PyMuPDF:
```bash
pip uninstall PyMuPDF
pip install PyMuPDF==1.23.8
```

## 📝 Лицензия

MIT License

## 👤 Автор

Разработано для профессионального перевода PDF документов с сохранением форматирования.

Специальная благодарность за тестирование и валидацию керамической терминологии.

## 🤝 Вклад

Pull requests приветствуются! Для крупных изменений сначала откройте issue для обсуждения.

## 📧 Контакты

GitHub: [@Anastasia462208](https://github.com/Anastasia462208)

---

**Версия:** 2.0.0  
**Дата обновления:** 26 октября 2025

