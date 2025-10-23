import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import hashlib
import time

logger = logging.getLogger(__name__)

class FileManager:
    """Класс для управления файлами и временными директориями"""
    
    def __init__(self, temp_dir: str = 'temp_files'):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(exist_ok=True)
        self.max_age_hours = 24  # Максимальный возраст файлов в часах
    
    def generate_unique_filename(self, original_name: str, extension: str) -> str:
        """Генерирует уникальное имя файла"""
        timestamp = int(time.time())
        hash_suffix = hashlib.md5(original_name.encode()).hexdigest()[:8]
        return f"{timestamp}_{hash_suffix}.{extension}"
    
    def cleanup_old_files(self):
        """Удаляет старые временные файлы"""
        try:
            current_time = time.time()
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > (self.max_age_hours * 3600):  # Конвертируем часы в секунды
                        file_path.unlink()
                        logger.info(f"Удален старый файл: {file_path}")
        except Exception as e:
            logger.error(f"Ошибка очистки старых файлов: {e}")
    
    def get_file_size_mb(self, file_path: str) -> float:
        """Возвращает размер файла в мегабайтах"""
        try:
            size_bytes = os.path.getsize(file_path)
            return size_bytes / (1024 * 1024)
        except Exception:
            return 0.0
    
    def format_file_size(self, size_bytes: int) -> str:
        """Форматирует размер файла в читаемый вид"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

class UserSession:
    """Класс для управления сессиями пользователей"""
    
    def __init__(self):
        self.sessions: Dict[int, Dict[str, Any]] = {}
        self.max_session_age = 3600  # 1 час в секундах
    
    def create_session(self, user_id: int) -> Dict[str, Any]:
        """Создает новую сессию для пользователя"""
        session = {
            'created_at': time.time(),
            'files_processed': 0,
            'last_activity': time.time()
        }
        self.sessions[user_id] = session
        return session
    
    def get_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает сессию пользователя"""
        if user_id in self.sessions:
            session = self.sessions[user_id]
            # Проверяем, не истекла ли сессия
            if time.time() - session['created_at'] < self.max_session_age:
                session['last_activity'] = time.time()
                return session
            else:
                # Удаляем истекшую сессию
                del self.sessions[user_id]
        return None
    
    def update_session(self, user_id: int, **kwargs):
        """Обновляет данные сессии"""
        session = self.get_session(user_id)
        if session:
            session.update(kwargs)
            session['last_activity'] = time.time()
    
    def cleanup_expired_sessions(self):
        """Удаляет истекшие сессии"""
        current_time = time.time()
        expired_users = []
        
        for user_id, session in self.sessions.items():
            if current_time - session['created_at'] > self.max_session_age:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del self.sessions[user_id]
            logger.info(f"Удалена истекшая сессия пользователя {user_id}")

class RateLimiter:
    """Класс для ограничения частоты запросов"""
    
    def __init__(self, max_requests: int = 10, time_window: int = 3600):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Dict[int, list] = {}
    
    def is_allowed(self, user_id: int) -> bool:
        """Проверяет, разрешен ли запрос пользователю"""
        current_time = time.time()
        
        if user_id not in self.requests:
            self.requests[user_id] = []
        
        # Удаляем старые запросы
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if current_time - req_time < self.time_window
        ]
        
        # Проверяем лимит
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        # Добавляем текущий запрос
        self.requests[user_id].append(current_time)
        return True
    
    def get_remaining_requests(self, user_id: int) -> int:
        """Возвращает количество оставшихся запросов"""
        if user_id not in self.requests:
            return self.max_requests
        
        current_time = time.time()
        valid_requests = [
            req_time for req_time in self.requests[user_id]
            if current_time - req_time < self.time_window
        ]
        
        return max(0, self.max_requests - len(valid_requests))

def validate_pdf_file(file_path: str) -> Dict[str, Any]:
    """Валидирует PDF файл и возвращает информацию о нем"""
    result = {
        'is_valid': False,
        'pages': 0,
        'size_mb': 0.0,
        'error': None
    }
    
    try:
        # Проверяем существование файла
        if not os.path.exists(file_path):
            result['error'] = "Файл не найден"
            return result
        
        # Проверяем размер файла
        file_size = os.path.getsize(file_path)
        result['size_mb'] = file_size / (1024 * 1024)
        
        if result['size_mb'] > 20:  # 20MB лимит
            result['error'] = "Файл слишком большой (максимум 20MB)"
            return result
        
        # Проверяем, что это PDF
        with open(file_path, 'rb') as f:
            header = f.read(4)
            if header != b'%PDF':
                result['error'] = "Файл не является PDF"
                return result
        
        # Проверяем количество страниц
        try:
            import fitz
            with fitz.open(file_path) as doc:
                result['pages'] = len(doc)
                result['is_valid'] = True
        except Exception as e:
            result['error'] = f"Ошибка чтения PDF: {str(e)}"
        
    except Exception as e:
        result['error'] = f"Ошибка валидации: {str(e)}"
    
    return result

def get_file_extension(filename: str) -> str:
    """Возвращает расширение файла"""
    return Path(filename).suffix.lower()

def sanitize_filename(filename: str) -> str:
    """Очищает имя файла от недопустимых символов"""
    import re
    # Удаляем недопустимые символы
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Ограничиваем длину
    if len(sanitized) > 100:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:95] + ext
    return sanitized
