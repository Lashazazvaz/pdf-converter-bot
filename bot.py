import os
import logging
import asyncio
from pathlib import Path
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Document
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from telegram.constants import ParseMode

from config import BOT_TOKEN, MAX_FILE_SIZE, TEMP_DIR, SUPPORTED_FORMATS
from pdf_converter import PDFConverter

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class PDFBot:
    """Telegram бот для конвертации PDF файлов"""
    
    def __init__(self):
        self.converter = PDFConverter(TEMP_DIR)
        self.temp_dir = Path(TEMP_DIR)
        self.temp_dir.mkdir(exist_ok=True)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        welcome_text = """
🤖 <b>PDF Converter Bot</b>

Добро пожаловать! Я помогу вам конвертировать PDF файлы в различные форматы.

<b>Доступные функции:</b>
📄 PDF → Word (DOCX)
📊 PDF → Excel (XLSX) 
📝 Извлечение только текста
📋 Извлечение таблиц

<b>Как использовать:</b>
1. Отправьте PDF файл
2. Выберите тип конвертации
3. Получите результат!

<b>Команды:</b>
/start - Начать работу
/help - Помощь
/info - Информация о боте

Просто отправьте PDF файл, чтобы начать! 🚀
        """
        
        keyboard = [
            [InlineKeyboardButton("📄 PDF → Word", callback_data="convert_word")],
            [InlineKeyboardButton("📊 PDF → Excel", callback_data="convert_excel")],
            [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text, 
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
📖 <b>Справка по использованию бота</b>

<b>Поддерживаемые форматы:</b>
• Входной: PDF
• Выходные: DOCX, XLSX

<b>Типы конвертации:</b>

<b>📄 PDF → Word:</b>
• Сохранение макета и форматирования
• Включение изображений
• Распознавание таблиц

<b>📊 PDF → Excel:</b>
• Извлечение всех таблиц
• Сохранение структуры данных
• Создание отдельных листов для каждой страницы

<b>Ограничения:</b>
• Максимальный размер файла: 20MB
• Поддерживаются только PDF файлы

<b>Как использовать:</b>
1. Отправьте PDF файл боту
2. Выберите тип конвертации
3. Дождитесь обработки
4. Получите готовый файл

<b>Поддержка:</b>
Если у вас возникли проблемы, обратитесь к администратору.
        """
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
    
    async def info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /info"""
        info_text = """
ℹ️ <b>Информация о боте</b>

<b>Версия:</b> 1.0.0
<b>Разработчик:</b> PDF Converter Team
<b>Язык программирования:</b> Python
<b>Библиотеки:</b> python-telegram-bot, pdf2docx, pdfplumber

<b>Возможности:</b>
✅ Конвертация PDF в Word
✅ Конвертация PDF в Excel  
✅ Извлечение текста
✅ Извлечение таблиц
✅ Сохранение форматирования
✅ Обработка изображений

<b>Безопасность:</b>
🔒 Все файлы обрабатываются локально
🔒 Временные файлы автоматически удаляются
🔒 Ваши данные не сохраняются на сервере
        """
        
        await update.message.reply_text(info_text, parse_mode=ParseMode.HTML)
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик загруженных документов"""
        document = update.message.document
        
        # Проверяем тип файла
        if not document.mime_type in SUPPORTED_FORMATS['pdf']:
            await update.message.reply_text(
                "❌ Поддерживаются только PDF файлы!\n"
                "Пожалуйста, отправьте файл в формате PDF."
            )
            return
        
        # Проверяем размер файла
        if document.file_size > MAX_FILE_SIZE:
            await update.message.reply_text(
                f"❌ Файл слишком большой!\n"
                f"Максимальный размер: {MAX_FILE_SIZE // (1024*1024)}MB\n"
                f"Размер вашего файла: {document.file_size // (1024*1024)}MB"
            )
            return
        
        # Сохраняем информацию о файле в контексте
        context.user_data['current_file'] = {
            'file_id': document.file_id,
            'file_name': document.file_name,
            'file_size': document.file_size
        }
        
        # Показываем меню выбора типа конвертации
        keyboard = [
            [InlineKeyboardButton("📄 PDF → Word", callback_data="convert_word")],
            [InlineKeyboardButton("📊 PDF → Excel", callback_data="convert_excel")],
            [InlineKeyboardButton("📝 Только текст", callback_data="convert_text")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"📁 <b>Файл получен:</b> {document.file_name}\n"
            f"📏 <b>Размер:</b> {document.file_size // 1024} KB\n\n"
            f"Выберите тип конвертации:",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "help":
            await self.help_command(update, context)
            return
        
        if query.data == "cancel":
            context.user_data.pop('current_file', None)
            await query.edit_message_text("❌ Операция отменена.")
            return
        
        # Проверяем, есть ли файл для обработки
        if 'current_file' not in context.user_data:
            await query.edit_message_text(
                "❌ Файл не найден!\n"
                "Пожалуйста, отправьте PDF файл сначала."
            )
            return
        
        file_info = context.user_data['current_file']
        
        # Показываем статус обработки
        await query.edit_message_text("⏳ Обрабатываю файл... Пожалуйста, подождите.")
        
        try:
            # Скачиваем файл
            file = await context.bot.get_file(file_info['file_id'])
            pdf_path = self.temp_dir / file_info['file_name']
            
            await file.download_to_drive(pdf_path)
            
            # Валидируем PDF
            if not self.converter.validate_pdf(str(pdf_path)):
                await query.edit_message_text("❌ Файл поврежден или не является валидным PDF!")
                self.converter.cleanup_temp_files(str(pdf_path))
                return
            
            # Выполняем конвертацию в зависимости от выбора
            if query.data == "convert_word":
                await self._convert_to_word(update, context, pdf_path, file_info)
            elif query.data == "convert_excel":
                await self._convert_to_excel(update, context, pdf_path, file_info)
            elif query.data == "convert_text":
                await self._extract_text_only(update, context, pdf_path, file_info)
            
        except Exception as e:
            logger.error(f"Ошибка обработки файла: {e}")
            await query.edit_message_text(
                "❌ Произошла ошибка при обработке файла!\n"
                "Попробуйте еще раз или обратитесь к администратору."
            )
        finally:
            # Очищаем временные файлы
            if 'pdf_path' in locals():
                self.converter.cleanup_temp_files(str(pdf_path))
            context.user_data.pop('current_file', None)
    
    async def _convert_to_word(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                              pdf_path: Path, file_info: dict):
        """Конвертирует PDF в Word"""
        query = update.callback_query
        
        # Создаем имя выходного файла
        output_name = file_info['file_name'].replace('.pdf', '.docx')
        output_path = self.temp_dir / output_name
        
        # Выполняем конвертацию
        success = self.converter.convert_to_word(
            str(pdf_path), 
            str(output_path),
            preserve_layout=True,
            include_images=True
        )
        
        if success and output_path.exists():
            # Отправляем результат
            with open(output_path, 'rb') as docx_file:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=docx_file,
                    filename=output_name,
                    caption=f"✅ <b>Конвертация завершена!</b>\n"
                           f"📄 {file_info['file_name']} → {output_name}",
                    parse_mode=ParseMode.HTML
                )
            
            await query.edit_message_text("✅ Файл успешно конвертирован в Word!")
            self.converter.cleanup_temp_files(str(output_path))
        else:
            await query.edit_message_text("❌ Ошибка конвертации в Word!")
    
    async def _convert_to_excel(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                               pdf_path: Path, file_info: dict):
        """Конвертирует PDF в Excel"""
        query = update.callback_query
        
        # Создаем имя выходного файла
        output_name = file_info['file_name'].replace('.pdf', '.xlsx')
        output_path = self.temp_dir / output_name
        
        # Выполняем конвертацию
        success = self.converter.extract_tables_to_excel(str(pdf_path), str(output_path))
        
        if success and output_path.exists():
            # Отправляем результат
            with open(output_path, 'rb') as excel_file:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=excel_file,
                    filename=output_name,
                    caption=f"✅ <b>Конвертация завершена!</b>\n"
                           f"📊 {file_info['file_name']} → {output_name}",
                    parse_mode=ParseMode.HTML
                )
            
            await query.edit_message_text("✅ Файл успешно конвертирован в Excel!")
            self.converter.cleanup_temp_files(str(output_path))
        else:
            await query.edit_message_text("❌ Ошибка конвертации в Excel!")
    
    async def _extract_text_only(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                pdf_path: Path, file_info: dict):
        """Извлекает только текст из PDF"""
        query = update.callback_query
        
        # Извлекаем текст
        text = self.converter.extract_text_only(str(pdf_path))
        
        if text:
            # Создаем текстовый файл
            output_name = file_info['file_name'].replace('.pdf', '.txt')
            output_path = self.temp_dir / output_name
            
            with open(output_path, 'w', encoding='utf-8') as txt_file:
                txt_file.write(text)
            
            # Отправляем результат
            with open(output_path, 'rb') as txt_file:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=txt_file,
                    filename=output_name,
                    caption=f"✅ <b>Текст извлечен!</b>\n"
                           f"📝 {file_info['file_name']} → {output_name}",
                    parse_mode=ParseMode.HTML
                )
            
            await query.edit_message_text("✅ Текст успешно извлечен!")
            self.converter.cleanup_temp_files(str(output_path))
        else:
            await query.edit_message_text("❌ Не удалось извлечь текст из файла!")
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        logger.error(f"Ошибка: {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Произошла неожиданная ошибка!\n"
                "Попробуйте еще раз или обратитесь к администратору."
            )

def main():
    """Основная функция запуска бота"""
    if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("❌ Ошибка: Не установлен токен бота!")
        print("Создайте файл .env и добавьте BOT_TOKEN=ваш_токен")
        return
    
    # Создаем экземпляр бота
    bot = PDFBot()
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("help", bot.help_command))
    application.add_handler(CommandHandler("info", bot.info_command))
    application.add_handler(MessageHandler(filters.Document.ALL, bot.handle_document))
    application.add_handler(CallbackQueryHandler(bot.handle_callback))
    
    # Добавляем обработчик ошибок
    application.add_error_handler(bot.error_handler)
    
    # Запускаем бота
    print("🤖 Бот запущен! Нажмите Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
