import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Токен бота (получите у @BotFather)
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# Максимальный размер файла в байтах (20MB)
MAX_FILE_SIZE = 20 * 1024 * 1024

# Временная папка для обработки файлов
TEMP_DIR = 'temp_files'

# Поддерживаемые форматы
SUPPORTED_FORMATS = {
    'pdf': ['application/pdf']
}

# Настройки конвертации
CONVERSION_SETTINGS = {
    'word': {
        'preserve_layout': True,
        'include_images': True,
        'table_recognition': True
    },
    'excel': {
        'extract_tables': True,
        'preserve_formatting': True
    }
}
