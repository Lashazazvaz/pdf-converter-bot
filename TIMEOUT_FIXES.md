# Исправления ошибок таймаута в Telegram боте

## Проблема
Бот получал ошибку "Timed out" при обработке файлов, что приводило к сбоям в работе.

## Причины таймаутов
1. **Скачивание файлов** - медленное интернет-соединение или большие файлы
2. **Конвертация PDF** - сложные файлы с множеством страниц или изображений
3. **Отправка результатов** - большие конвертированные файлы
4. **Запросы к Telegram API** - сетевые задержки

## Реализованные исправления

### 1. Настройки таймаутов (config.py)
```python
TIMEOUT_SETTINGS = {
    'file_download': 300,  # 5 минут для скачивания файла
    'file_upload': 300,    # 5 минут для загрузки файла
    'conversion': 600,     # 10 минут для конвертации
    'telegram_request': 30 # 30 секунд для запросов к Telegram API
}
```

### 2. Асинхронные методы с таймаутами (bot.py)

#### Скачивание файлов с таймаутом
```python
async def _download_file_with_timeout(self, bot, file_id: str, file_path: Path) -> bool:
    try:
        file = await asyncio.wait_for(
            bot.get_file(file_id),
            timeout=TIMEOUT_SETTINGS['telegram_request']
        )
        
        await asyncio.wait_for(
            file.download_to_drive(file_path),
            timeout=TIMEOUT_SETTINGS['file_download']
        )
        return True
    except asyncio.TimeoutError:
        logger.error(f"Таймаут при скачивании файла {file_id}")
        return False
```

#### Отправка файлов с таймаутом
```python
async def _send_file_with_timeout(self, bot, chat_id: int, file_path: Path, 
                                filename: str, caption: str) -> bool:
    try:
        with open(file_path, 'rb') as file:
            await asyncio.wait_for(
                bot.send_document(...),
                timeout=TIMEOUT_SETTINGS['file_upload']
            )
        return True
    except asyncio.TimeoutError:
        logger.error(f"Таймаут при отправке файла {filename}")
        return False
```

#### Конвертация с таймаутом
```python
async def _convert_to_word_async(self, update, context, pdf_path, file_info):
    try:
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
        # Обработка результата...
    except asyncio.TimeoutError:
        await query.edit_message_text(
            "⏰ Превышено время конвертации!\n\n"
            "Файл слишком большой или сложный для обработки.\n"
            "Попробуйте отправить файл меньшего размера."
        )
```

### 3. Улучшенная обработка ошибок

#### Детальные сообщения об ошибках
```python
async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    error = context.error
    
    if isinstance(error, (TimedOut, asyncio.TimeoutError)):
        error_message = (
            "⏰ Ошибка таймаута!\n\n"
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
            "🌐 Ошибка сети!\n\n"
            "Проблемы с интернет-соединением.\n"
            "Проверьте подключение к интернету и попробуйте еще раз."
        )
```

### 4. Асинхронная обработка в PDF конвертере

Добавлен метод для выполнения операций с таймаутом:
```python
async def _run_with_timeout(self, func, *args, timeout: int = 600, **kwargs):
    try:
        return await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, func, *args, **kwargs),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.error(f"Таймаут при выполнении операции {func.__name__}")
        return False
```

## Преимущества исправлений

1. **Предотвращение зависаний** - операции не будут висеть бесконечно
2. **Информативные сообщения** - пользователь понимает, что произошло
3. **Гибкие настройки** - таймауты можно настроить под разные условия
4. **Лучшая отладка** - подробное логирование ошибок
5. **Graceful degradation** - бот продолжает работать даже при ошибках

## Рекомендации по использованию

1. **Для больших файлов** - увеличьте таймауты в `TIMEOUT_SETTINGS`
2. **Для медленного интернета** - увеличьте `file_download` и `file_upload`
3. **Для сложных PDF** - увеличьте `conversion` таймаут
4. **Мониторинг** - следите за логами для выявления проблемных файлов

## Тестирование

После внедрения исправлений протестируйте:
- [ ] Скачивание больших PDF файлов
- [ ] Конвертацию сложных документов
- [ ] Отправку результатов
- [ ] Поведение при медленном интернете
- [ ] Обработку поврежденных файлов
