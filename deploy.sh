#!/bin/bash

# Скрипт для развертывания PDF Translator Server на Ubuntu сервере

set -e

echo "=========================================="
echo "PDF Translator Server - Установка"
echo "=========================================="

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${YELLOW}Внимание: Некоторые команды требуют sudo${NC}"
fi

# Обновление системы
echo -e "\n${GREEN}[1/7] Обновление системы...${NC}"
sudo apt-get update

# Установка Python и pip
echo -e "\n${GREEN}[2/7] Установка Python и зависимостей...${NC}"
sudo apt-get install -y python3 python3-pip python3-venv

# Создание виртуального окружения
echo -e "\n${GREEN}[3/7] Создание виртуального окружения...${NC}"
python3 -m venv venv
source venv/bin/activate

# Установка Python пакетов
echo -e "\n${GREEN}[4/7] Установка Python пакетов...${NC}"
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# Создание необходимых директорий
echo -e "\n${GREEN}[5/7] Создание рабочих директорий...${NC}"
mkdir -p uploads outputs

# Установка Nginx (опционально)
read -p "Установить Nginx? (y/n): " install_nginx
if [ "$install_nginx" = "y" ]; then
    echo -e "\n${GREEN}[6/7] Установка Nginx...${NC}"
    sudo apt-get install -y nginx
    
    # Получение пути к проекту
    PROJECT_DIR=$(pwd)
    
    # Создание конфигурации Nginx
    echo -e "\n${GREEN}Создание конфигурации Nginx...${NC}"
    sudo tee /etc/nginx/sites-available/pdf-translator > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_connect_timeout 600;
        proxy_send_timeout 600;
        proxy_read_timeout 600;
        send_timeout 600;
    }

    client_max_body_size 50M;
}
EOF

    # Активация конфигурации
    sudo ln -sf /etc/nginx/sites-available/pdf-translator /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo nginx -t && sudo systemctl reload nginx
    
    echo -e "${GREEN}✓ Nginx настроен${NC}"
fi

# Создание systemd service
read -p "Создать systemd service для автозапуска? (y/n): " create_service
if [ "$create_service" = "y" ]; then
    echo -e "\n${GREEN}[7/7] Создание systemd service...${NC}"
    
    PROJECT_DIR=$(pwd)
    USER=$(whoami)
    
    sudo tee /etc/systemd/system/pdf-translator.service > /dev/null <<EOF
[Unit]
Description=PDF Translator Server
After=network.target

[Service]
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 --timeout 600 server:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable pdf-translator
    sudo systemctl start pdf-translator
    
    echo -e "${GREEN}✓ Systemd service создан и запущен${NC}"
fi

echo -e "\n=========================================="
echo -e "${GREEN}Установка завершена!${NC}"
echo -e "=========================================="
echo -e "\nДля запуска вручную:"
echo -e "  source venv/bin/activate"
echo -e "  python server.py"
echo -e "\nДля запуска с Gunicorn:"
echo -e "  gunicorn -w 4 -b 0.0.0.0:5000 server:app"
echo -e "\nПроверка статуса service:"
echo -e "  sudo systemctl status pdf-translator"
echo -e "\nПросмотр логов:"
echo -e "  sudo journalctl -u pdf-translator -f"
echo -e "\n=========================================="

