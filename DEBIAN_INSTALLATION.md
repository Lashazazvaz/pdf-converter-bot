# Инструкция по установке PDF Converter Telegram Bot на Debian сервер

## Обзор проекта

PDF Converter Telegram Bot - это бот для конвертации PDF файлов в Word и Excel документы с возможностью извлечения текста и таблиц.

## Системные требования

- **ОС:** Debian 10+ (Buster, Bullseye, Bookworm)
- **Python:** 3.8 или выше
- **RAM:** минимум 512MB, рекомендуется 1GB+
- **Диск:** минимум 1GB свободного места
- **Интернет:** стабильное соединение для работы с Telegram API

## 1. Подготовка системы

### Обновление системы

```bash
sudo apt update && sudo apt upgrade -y
```

### Установка необходимых пакетов

```bash
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    wget \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    python3-dev
```

### Проверка версии Python

```bash
python3 --version
# Должно быть 3.8 или выше
```

## 2. Создание пользователя для бота (рекомендуется)

```bash
# Создаем пользователя для бота
sudo useradd -m -s /bin/bash pdfbot

# Переключаемся на пользователя бота
sudo su - pdfbot
```

## 3. Клонирование проекта

```bash
# Клонируем репозиторий (замените URL на ваш)
git clone <your-repo-url> pdf-converter-bot
cd pdf-converter-bot

# Или если у вас есть архив
# wget <your-archive-url>
# unzip pdf-converter-bot.zip
# cd pdf-converter-bot
```

## 4. Создание виртуального окружения

```bash
# Создаем виртуальное окружение
python3 -m venv venv

# Активируем виртуальное окружение
source venv/bin/activate

# Обновляем pip
pip install --upgrade pip
```

## 5. Установка зависимостей

```bash
# Устанавливаем зависимости
pip install -r requirements.txt
```

### Если возникают ошибки при установке:

```bash
# Для PyMuPDF (fitz)
sudo apt install -y libmupdf-dev

# Для Pillow
sudo apt install -y libjpeg-dev zlib1g-dev

# Переустановка с принудительным обновлением
pip install --upgrade --force-reinstall -r requirements.txt
```


## 6. Настройка конфигурации

### Создание Telegram бота

1. Найдите [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Сохраните полученный токен

### Создание файла конфигурации

```bash
# Копируем пример конфигурации
cp env_example.txt .env

# Редактируем файл конфигурации
nano .env
```

Содержимое файла `.env`:

```env
# Токен вашего Telegram бота
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Максимальный размер файла в байтах (20MB)
MAX_FILE_SIZE=20971520

# Папка для временных файлов
TEMP_DIR=temp_files
```

### Создание директории для временных файлов

```bash
mkdir -p temp_files
chmod 755 temp_files
```

## 7. Тестирование установки

```bash
# Проверяем установку
python3 run.py
```

Если все настроено правильно, бот должен запуститься и показать сообщение о готовности.

## 8. Настройка автозапуска (systemd)

### Создание systemd сервиса

```bash
# Выходим из пользователя бота
exit

# Создаем файл сервиса
sudo nano /etc/systemd/system/pdf-converter-bot.service
```

Содержимое файла сервиса:

```ini
[Unit]
Description=PDF Converter Telegram Bot
After=network.target

[Service]
Type=simple
User=pdfbot
Group=pdfbot
WorkingDirectory=/home/pdfbot/pdf-converter-bot
Environment=PATH=/home/pdfbot/pdf-converter-bot/venv/bin
ExecStart=/home/pdfbot/pdf-converter-bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Активация сервиса

```bash
# Перезагружаем systemd
sudo systemctl daemon-reload

# Включаем автозапуск
sudo systemctl enable pdf-converter-bot

# Запускаем сервис
sudo systemctl start pdf-converter-bot

# Проверяем статус
sudo systemctl status pdf-converter-bot
```

## 9. Настройка логирования

### Создание директории для логов

```bash
sudo mkdir -p /var/log/pdf-converter-bot
sudo chown pdfbot:pdfbot /var/log/pdf-converter-bot
```

### Обновление systemd сервиса для логирования

```bash
sudo nano /etc/systemd/system/pdf-converter-bot.service
```

Добавьте в секцию `[Service]`:

```ini
StandardOutput=append:/var/log/pdf-converter-bot/bot.log
StandardError=append:/var/log/pdf-converter-bot/error.log
```

Перезапустите сервис:

```bash
sudo systemctl daemon-reload
sudo systemctl restart pdf-converter-bot
```

## 10. Настройка файрвола (опционально)

```bash
# Устанавливаем ufw если не установлен
sudo apt install ufw

# Разрешаем SSH
sudo ufw allow ssh

# Включаем файрвол
sudo ufw enable
```

## 11. Мониторинг и обслуживание

### Полезные команды

```bash
# Проверка статуса бота
sudo systemctl status pdf-converter-bot

# Просмотр логов
sudo journalctl -u pdf-converter-bot -f

# Перезапуск бота
sudo systemctl restart pdf-converter-bot

# Остановка бота
sudo systemctl stop pdf-converter-bot

# Просмотр логов из файлов
tail -f /var/log/pdf-converter-bot/bot.log
tail -f /var/log/pdf-converter-bot/error.log
```

### Очистка временных файлов

```bash
# Создаем скрипт очистки
sudo nano /usr/local/bin/cleanup-pdf-bot.sh
```

Содержимое скрипта:

```bash
#!/bin/bash
# Очистка временных файлов PDF бота
find /home/pdfbot/pdf-converter-bot/temp_files -type f -mtime +1 -delete
echo "$(date): Cleaned up old temp files" >> /var/log/pdf-converter-bot/cleanup.log
```

```bash
# Делаем скрипт исполняемым
sudo chmod +x /usr/local/bin/cleanup-pdf-bot.sh

# Добавляем в crontab для ежедневной очистки
sudo crontab -e
```

Добавьте строку:

```
0 2 * * * /usr/local/bin/cleanup-pdf-bot.sh
```

## 12. Установка через Docker (альтернативный способ)

### Установка Docker

```bash
# Устанавливаем Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Добавляем пользователя в группу docker
sudo usermod -aG docker $USER

# Перезагружаемся или выполняем
newgrp docker
```

### Запуск через Docker Compose

```bash
# Переходим в директорию проекта
cd /home/pdfbot/pdf-converter-bot

# Создаем .env файл (если еще не создан)
cp env_example.txt .env
nano .env

# Запускаем через Docker Compose
docker-compose up -d

# Проверяем статус
docker-compose ps
```

## 13. Обновление бота

### Обновление кода

```bash
# Переходим в директорию проекта
cd /home/pdfbot/pdf-converter-bot

# Останавливаем сервис
sudo systemctl stop pdf-converter-bot

# Обновляем код
git pull origin main

# Активируем виртуальное окружение
source venv/bin/activate

# Обновляем зависимости
pip install -r requirements.txt

# Запускаем сервис
sudo systemctl start pdf-converter-bot
```

## 14. Устранение неполадок

### Частые проблемы

1. **Ошибка "Permission denied"**
   ```bash
   sudo chown -R pdfbot:pdfbot /home/pdfbot/pdf-converter-bot
   ```

2. **Ошибка импорта модулей**
   ```bash
   # Переустановка зависимостей
   source venv/bin/activate
   pip install --upgrade --force-reinstall -r requirements.txt
   ```

3. **Бот не отвечает**
   ```bash
   # Проверка токена
   grep BOT_TOKEN .env
   
   # Проверка логов
   sudo journalctl -u pdf-converter-bot -n 50
   ```

4. **Ошибки конвертации PDF**
   ```bash
   # Установка дополнительных библиотек
   sudo apt install -y poppler-utils
   ```


### Проверка работоспособности

```bash
# Тест подключения к Telegram API
curl -X GET "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe"

# Проверка места на диске
df -h

# Проверка использования памяти
free -h
```

## 15. Безопасность

### Рекомендации по безопасности

1. **Ограничение доступа к файлам**
   ```bash
   chmod 600 .env
   chmod 755 temp_files
   ```

2. **Регулярные обновления**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

3. **Мониторинг логов**
   ```bash
   # Настройка ротации логов
   sudo nano /etc/logrotate.d/pdf-converter-bot
   ```

   Содержимое:
   ```
   /var/log/pdf-converter-bot/*.log {
       daily
       missingok
       rotate 7
       compress
       delaycompress
       notifempty
       create 644 pdfbot pdfbot
   }
   ```

## 16. Резервное копирование

### Создание скрипта резервного копирования

```bash
sudo nano /usr/local/bin/backup-pdf-bot.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/backup/pdf-converter-bot"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Создаем архив
tar -czf $BACKUP_DIR/pdf-bot-backup-$DATE.tar.gz \
    -C /home/pdfbot pdf-converter-bot \
    --exclude=pdf-converter-bot/venv \
    --exclude=pdf-converter-bot/temp_files

# Удаляем старые бэкапы (старше 7 дней)
find $BACKUP_DIR -name "pdf-bot-backup-*.tar.gz" -mtime +7 -delete

echo "$(date): Backup created" >> /var/log/pdf-converter-bot/backup.log
```

```bash
sudo chmod +x /usr/local/bin/backup-pdf-bot.sh

# Добавляем в crontab
sudo crontab -e
```

Добавьте:
```
0 3 * * * /usr/local/bin/backup-pdf-bot.sh
```

## Заключение

После выполнения всех шагов ваш PDF Converter Telegram Bot будет:

- ✅ Установлен и настроен на Debian сервере
- ✅ Автоматически запускаться при загрузке системы
- ✅ Вести подробные логи
- ✅ Автоматически очищать временные файлы
- ✅ Регулярно создавать резервные копии
- ✅ Работать стабильно и безопасно

Для проверки работоспособности найдите вашего бота в Telegram и отправьте команду `/start`.

---

**Примечание:** Замените `<your-repo-url>` и `<YOUR_BOT_TOKEN>` на ваши реальные значения.
