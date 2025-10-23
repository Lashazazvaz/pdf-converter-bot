#!/usr/bin/env python3
"""
Скрипт для запуска PDF Converter Telegram Bot
"""

import os
import sys
import logging
from pathlib import Path

# Добавляем текущую директорию в путь Python
sys.path.insert(0, str(Path(__file__).parent))

def check_requirements():
    """Проверяет наличие необходимых файлов и зависимостей"""
    required_files = ['bot.py', 'config.py', 'pdf_converter.py', 'requirements.txt']
    missing_files = []
    
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Отсутствуют необходимые файлы: {', '.join(missing_files)}")
        return False
    
    # Проверяем наличие .env файла
    if not Path('.env').exists():
        print("⚠️  Файл .env не найден!")
        print("Создайте файл .env на основе env_example.txt и добавьте ваш BOT_TOKEN")
        return False
    
    return True

def check_dependencies():
    """Проверяет установленные зависимости"""
    try:
        import telegram
        import pdf2docx
        import pdfplumber
        import pandas
        import openpyxl
        import docx
        import fitz
        from dotenv import load_dotenv
        print("✅ Все зависимости установлены")
        return True
    except ImportError as e:
        print(f"❌ Отсутствует зависимость: {e}")
        print("Установите зависимости командой: pip install -r requirements.txt")
        return False

def main():
    """Основная функция"""
    print("🤖 PDF Converter Telegram Bot")
    print("=" * 40)
    
    # Проверяем файлы
    if not check_requirements():
        sys.exit(1)
    
    # Проверяем зависимости
    if not check_dependencies():
        sys.exit(1)
    
    # Проверяем токен бота
    from dotenv import load_dotenv
    load_dotenv()
    
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token or bot_token == 'YOUR_BOT_TOKEN_HERE':
        print("❌ Не установлен токен бота!")
        print("Добавьте BOT_TOKEN в файл .env")
        sys.exit(1)
    
    print("✅ Конфигурация проверена")
    print("🚀 Запускаем бота...")
    print("Нажмите Ctrl+C для остановки")
    print("=" * 40)
    
    # Запускаем бота
    try:
        from bot import main as bot_main
        bot_main()
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
