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
from telegram.error import TimedOut, NetworkError

from config import BOT_TOKEN, MAX_FILE_SIZE, TEMP_DIR, SUPPORTED_FORMATS, TIMEOUT_SETTINGS
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
    
    async def _download_file_with_timeout(self, bot, file_id: str, file_path: Path) -> bool:
        """Скачивает файл с таймаутом"""
        try:
            # Получаем информацию о файле с таймаутом
            file = await asyncio.wait_for(
                bot.get_file(file_id),
                timeout=TIMEOUT_SETTINGS['telegram_request']
            )
            
            # Скачиваем файл с таймаутом
            await asyncio.wait_for(
                file.download_to_drive(file_path),
                timeout=TIMEOUT_SETTINGS['file_download']
            )
            
            return True
            
        except asyncio.TimeoutError:
            logger.error(f"Таймаут при скачивании файла {file_id}")
            return False
        except (TimedOut, NetworkError) as e:
            logger.error(f"Ошибка сети при скачивании файла: {e}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при скачивании файла: {e}")
            return False
    
    async def _send_file_with_timeout(self, bot, chat_id: int, file_path: Path, 
                                    filename: str, caption: str) -> bool:
        """Отправляет файл с таймаутом"""
        try:
            with open(file_path, 'rb') as file:
                await asyncio.wait_for(
                    bot.send_document(
                        chat_id=chat_id,
                        document=file,
                        filename=filename,
                        caption=caption,
                        parse_mode=ParseMode.HTML
                    ),
                    timeout=TIMEOUT_SETTINGS['file_upload']
                )
            return True
            
        except asyncio.TimeoutError:
            logger.error(f"Таймаут при отправке файла {filename}")
            return False
        except (TimedOut, NetworkError) as e:
            logger.error(f"Ошибка сети при отправке файла: {e}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке файла: {e}")
            return False
    
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
            # Скачиваем файл с таймаутом
            pdf_path = self.temp_dir / file_info['file_name']
            
            download_success = await self._download_file_with_timeout(
                context.bot, 
                file_info['file_id'], 
                pdf_path
            )
            
            if not download_success:
                await query.edit_message_text(
                    "❌ Ошибка при скачивании файла!\n"
                    "Возможно, файл слишком большой или произошла ошибка сети.\n"
                    "Попробуйте еще раз."
                )
                return
            
            # Валидируем PDF
            if not self.converter.validate_pdf(str(pdf_path)):
                await query.edit_message_text("❌ Файл поврежден или не является валидным PDF!")
                self.converter.cleanup_temp_files(str(pdf_path))
                return
            
            # Выполняем конвертацию в зависимости от выбора с таймаутом
            if query.data == "convert_word":
                await self._convert_to_word_async(update, context, pdf_path, file_info)
            elif query.data == "convert_excel":
                await self._convert_to_excel_async(update, context, pdf_path, file_info)
            elif query.data == "convert_text":
                await self._extract_text_only_async(update, context, pdf_path, file_info)
            
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
    
    async def _convert_to_word_async(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                    pdf_path: Path, file_info: dict):
        """Конвертирует PDF в Word с таймаутом"""
        query = update.callback_query
        
        # Создаем имя выходного файла
        output_name = file_info['file_name'].replace('.pdf', '.docx')
        output_path = self.temp_dir / output_name
        
        try:
            # Выполняем конвертацию с таймаутом
            success = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    self.converter.convert_to_word,
                    str(pdf_path),
                    str(output_path),
                    True,  # preserve_layout
                    True   # include_images
                ),
                timeout=TIMEOUT_SETTINGS['conversion']
            )
            
            if success and output_path.exists():
                # Отправляем результат с таймаутом
                send_success = await self._send_file_with_timeout(
                    context.bot,
                    query.message.chat_id,
                    output_path,
                    output_name,
                    f"✅ <b>Конвертация завершена!</b>\n"
                    f"📄 {file_info['file_name']} → {output_name}"
                )
                
                if send_success:
                    await query.edit_message_text("✅ Файл успешно конвертирован в Word!")
                else:
                    await query.edit_message_text(
                        "❌ Ошибка при отправке файла!\n"
                        "Конвертация прошла успешно, но не удалось отправить результат."
                    )
                
                self.converter.cleanup_temp_files(str(output_path))
            else:
                await query.edit_message_text("❌ Ошибка конвертации в Word!")
                
        except asyncio.TimeoutError:
            await query.edit_message_text(
                "⏰ <b>Превышено время конвертации!</b>\n\n"
                "Файл слишком большой или сложный для обработки.\n"
                "Попробуйте отправить файл меньшего размера."
            )
            logger.error(f"Таймаут конвертации Word для файла {file_info['file_name']}")
        except Exception as e:
            await query.edit_message_text("❌ Ошибка конвертации в Word!")
            logger.error(f"Ошибка конвертации Word: {e}")
    
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
            # Отправляем результат с таймаутом
            send_success = await self._send_file_with_timeout(
                context.bot,
                query.message.chat_id,
                output_path,
                output_name,
                f"✅ <b>Конвертация завершена!</b>\n"
                f"📄 {file_info['file_name']} → {output_name}"
            )
            
            if send_success:
                await query.edit_message_text("✅ Файл успешно конвертирован в Word!")
            else:
                await query.edit_message_text(
                    "❌ Ошибка при отправке файла!\n"
                    "Конвертация прошла успешно, но не удалось отправить результат."
                )
            
            self.converter.cleanup_temp_files(str(output_path))
        else:
            await query.edit_message_text("❌ Ошибка конвертации в Word!")
    
    async def _convert_to_excel_async(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                     pdf_path: Path, file_info: dict):
        """Конвертирует PDF в Excel с таймаутом"""
        query = update.callback_query
        
        # Создаем имя выходного файла
        output_name = file_info['file_name'].replace('.pdf', '.xlsx')
        output_path = self.temp_dir / output_name
        
        try:
            # Выполняем конвертацию с таймаутом
            success = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    self.converter.extract_tables_to_excel,
                    str(pdf_path),
                    str(output_path)
                ),
                timeout=TIMEOUT_SETTINGS['conversion']
            )
            
            if success and output_path.exists():
                # Отправляем результат с таймаутом
                send_success = await self._send_file_with_timeout(
                    context.bot,
                    query.message.chat_id,
                    output_path,
                    output_name,
                    f"✅ <b>Конвертация завершена!</b>\n"
                    f"📊 {file_info['file_name']} → {output_name}"
                )
                
                if send_success:
                    await query.edit_message_text("✅ Файл успешно конвертирован в Excel!")
                else:
                    await query.edit_message_text(
                        "❌ Ошибка при отправке файла!\n"
                        "Конвертация прошла успешно, но не удалось отправить результат."
                    )
                
                self.converter.cleanup_temp_files(str(output_path))
            else:
                await query.edit_message_text("❌ Ошибка конвертации в Excel!")
                
        except asyncio.TimeoutError:
            await query.edit_message_text(
                "⏰ <b>Превышено время конвертации!</b>\n\n"
                "Файл слишком большой или сложный для обработки.\n"
                "Попробуйте отправить файл меньшего размера."
            )
            logger.error(f"Таймаут конвертации Excel для файла {file_info['file_name']}")
        except Exception as e:
            await query.edit_message_text("❌ Ошибка конвертации в Excel!")
            logger.error(f"Ошибка конвертации Excel: {e}")
    
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
            # Отправляем результат с таймаутом
            send_success = await self._send_file_with_timeout(
                context.bot,
                query.message.chat_id,
                output_path,
                output_name,
                f"✅ <b>Конвертация завершена!</b>\n"
                f"📊 {file_info['file_name']} → {output_name}"
            )
            
            if send_success:
                await query.edit_message_text("✅ Файл успешно конвертирован в Excel!")
            else:
                await query.edit_message_text(
                    "❌ Ошибка при отправке файла!\n"
                    "Конвертация прошла успешно, но не удалось отправить результат."
                )
            
            self.converter.cleanup_temp_files(str(output_path))
        else:
            await query.edit_message_text("❌ Ошибка конвертации в Excel!")
    
    async def _extract_text_only_async(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                      pdf_path: Path, file_info: dict):
        """Извлекает только текст из PDF с таймаутом"""
        query = update.callback_query
        
        try:
            # Извлекаем текст с таймаутом
            text = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    self.converter.extract_text_only,
                    str(pdf_path)
                ),
                timeout=TIMEOUT_SETTINGS['conversion']
            )
            
            if text:
                # Создаем текстовый файл
                output_name = file_info['file_name'].replace('.pdf', '.txt')
                output_path = self.temp_dir / output_name
                
                with open(output_path, 'w', encoding='utf-8') as txt_file:
                    txt_file.write(text)
                
                # Отправляем результат с таймаутом
                send_success = await self._send_file_with_timeout(
                    context.bot,
                    query.message.chat_id,
                    output_path,
                    output_name,
                    f"✅ <b>Текст извлечен!</b>\n"
                    f"📝 {file_info['file_name']} → {output_name}"
                )
                
                if send_success:
                    await query.edit_message_text("✅ Текст успешно извлечен!")
                else:
                    await query.edit_message_text(
                        "❌ Ошибка при отправке файла!\n"
                        "Текст извлечен успешно, но не удалось отправить результат."
                    )
                
                self.converter.cleanup_temp_files(str(output_path))
            else:
                await query.edit_message_text("❌ Не удалось извлечь текст из файла!")
                
        except asyncio.TimeoutError:
            await query.edit_message_text(
                "⏰ <b>Превышено время обработки!</b>\n\n"
                "Файл слишком большой или сложный для обработки.\n"
                "Попробуйте отправить файл меньшего размера."
            )
            logger.error(f"Таймаут извлечения текста для файла {file_info['file_name']}")
        except Exception as e:
            await query.edit_message_text("❌ Не удалось извлечь текст из файла!")
            logger.error(f"Ошибка извлечения текста: {e}")
    
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
            
            # Отправляем результат с таймаутом
            send_success = await self._send_file_with_timeout(
                context.bot,
                query.message.chat_id,
                output_path,
                output_name,
                f"✅ <b>Текст извлечен!</b>\n"
                f"📝 {file_info['file_name']} → {output_name}"
            )
            
            if send_success:
                await query.edit_message_text("✅ Текст успешно извлечен!")
            else:
                await query.edit_message_text(
                    "❌ Ошибка при отправке файла!\n"
                    "Текст извлечен успешно, но не удалось отправить результат."
                )
            
            self.converter.cleanup_temp_files(str(output_path))
        else:
            await query.edit_message_text("❌ Не удалось извлечь текст из файла!")
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        error = context.error
        logger.error(f"Ошибка: {error}")
        
        # Определяем тип ошибки и отправляем соответствующее сообщение
        error_message = "❌ Произошла неожиданная ошибка!\n"
        
        if isinstance(error, (TimedOut, asyncio.TimeoutError)):
            error_message = (
                "⏰ <b>Ошибка таймаута!</b>\n\n"
                "Операция заняла слишком много времени.\n"
                "Возможные причины:\n"
                "• Файл слишком большой\n"
                "• Медленное интернет-соединение\n"
                "• Высокая нагрузка на сервер\n\n"
                "Попробуйте:\n"
                "• Отправить файл меньшего размера\n"
                "• Проверить интернет-соединение\n"
                "• Попробовать еще раз через несколько минут"
            )
        elif isinstance(error, NetworkError):
            error_message = (
                "🌐 <b>Ошибка сети!</b>\n\n"
                "Проблемы с интернет-соединением.\n"
                "Проверьте подключение к интернету и попробуйте еще раз."
            )
        elif "Timed out" in str(error):
            error_message = (
                "⏰ <b>Превышено время ожидания!</b>\n\n"
                "Операция не была завершена в установленное время.\n"
                "Попробуйте отправить файл меньшего размера или повторить попытку."
            )
        
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    error_message,
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения об ошибке: {e}")

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
