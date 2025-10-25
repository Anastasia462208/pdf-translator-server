# Быстрое развертывание на сервере 144.31.30.28

## 📋 Инструкция для вашего сервера

Эта инструкция описывает шаги для развертывания PDF Translator Server на вашем сервере **144.31.30.28**.

---

## 🚀 Шаг 1: Подключение к серверу

```bash
ssh root@144.31.30.28
```

---

## 📥 Шаг 2: Клонирование репозитория

```bash
cd /root
git clone https://github.com/Anastasia462208/pdf-translator-server.git
cd pdf-translator-server
```

---

## ⚙️ Шаг 3: Автоматическая установка

```bash
chmod +x deploy.sh
./deploy.sh
```

Скрипт предложит:
1. **Установить Nginx?** - Ответьте `y` (да)
2. **Создать systemd service?** - Ответьте `y` (да)

---

## 🔧 Шаг 4: Настройка Nginx (если уже установлен)

Если Nginx уже установлен на сервере, добавьте новую конфигурацию:

```bash
sudo nano /etc/nginx/sites-available/pdf-translator
```

Вставьте следующую конфигурацию:

```nginx
server {
    listen 8080;  # Используем другой порт, чтобы не конфликтовать с существующими сервисами
    server_name 144.31.30.28;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 600;
        proxy_send_timeout 600;
        proxy_read_timeout 600;
        send_timeout 600;
    }

    client_max_body_size 50M;
}
```

Активируйте конфигурацию:

```bash
sudo ln -s /etc/nginx/sites-available/pdf-translator /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🔥 Шаг 5: Настройка Firewall

Откройте порт 8080 для доступа:

```bash
sudo ufw allow 8080/tcp
sudo ufw reload
```

---

## ✅ Шаг 6: Проверка работы

### Проверка статуса сервиса:

```bash
sudo systemctl status pdf-translator
```

### Проверка логов:

```bash
sudo journalctl -u pdf-translator -f
```

### Тестирование через браузер:

Откройте в браузере: **http://144.31.30.28:8080**

---

## 🛠️ Управление сервисом

```bash
# Запуск
sudo systemctl start pdf-translator

# Остановка
sudo systemctl stop pdf-translator

# Перезапуск
sudo systemctl restart pdf-translator

# Просмотр логов
sudo journalctl -u pdf-translator -f
```

---

## 🧹 Автоматическая очистка файлов

Настройте автоматическую очистку старых файлов:

```bash
crontab -e
```

Добавьте:

```bash
# Очистка файлов старше 24 часов каждый день в 3:00
0 3 * * * find /root/pdf-translator-server/uploads -type f -mtime +1 -delete
0 3 * * * find /root/pdf-translator-server/outputs -type f -mtime +1 -delete
```

---

## 📊 Мониторинг

### Проверка использования ресурсов:

```bash
# Процессы
ps aux | grep gunicorn

# Память
free -h

# Диск
df -h
du -sh /root/pdf-translator-server/uploads
du -sh /root/pdf-translator-server/outputs
```

---

## 🔄 Обновление

Для обновления сервера до новой версии:

```bash
cd /root/pdf-translator-server
git pull origin master
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart pdf-translator
```

---

## 🐛 Решение проблем

### Если сервис не запускается:

```bash
# Проверьте логи
sudo journalctl -u pdf-translator -n 50

# Проверьте порт
sudo netstat -tulpn | grep 5000

# Запустите вручную для отладки
cd /root/pdf-translator-server
source venv/bin/activate
python server.py --host 0.0.0.0 --port 5000
```

### Если порт 8080 занят:

Измените порт в конфигурации Nginx на другой (например, 8081, 8082):

```bash
sudo nano /etc/nginx/sites-available/pdf-translator
# Измените listen 8080; на listen 8081;

sudo nginx -t
sudo systemctl reload nginx
sudo ufw allow 8081/tcp
```

---

## 📝 Примечания

- Сервер будет доступен по адресу: **http://144.31.30.28:8080**
- Максимальный размер файла: **50 МБ**
- Файлы автоматически удаляются через 24 часа
- Сервис автоматически запускается при перезагрузке сервера

---

## 🎯 Готово!

Ваш PDF Translator Server успешно развернут и готов к работе! 🚀

**Доступ:**
- Веб-интерфейс: http://144.31.30.28:8080
- API endpoint: http://144.31.30.28:8080/api/translate

**GitHub репозиторий:** https://github.com/Anastasia462208/pdf-translator-server

