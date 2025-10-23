import os
import tempfile
import logging
import asyncio
from pathlib import Path
from typing import Optional, Tuple
import fitz  # PyMuPDF
import pdfplumber
from pdf2docx import Converter
import pandas as pd
from docx import Document
from docx.shared import Inches
import io

logger = logging.getLogger(__name__)

class PDFConverter:
    """Класс для конвертации PDF файлов в различные форматы"""
    
    def __init__(self, temp_dir: str = 'temp_files'):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(exist_ok=True)
    
    async def _run_with_timeout(self, func, *args, timeout: int = 600, **kwargs):
        """Выполняет функцию с таймаутом"""
        try:
            return await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, func, *args, **kwargs),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Таймаут при выполнении операции {func.__name__}")
            return False
        except Exception as e:
            logger.error(f"Ошибка при выполнении операции {func.__name__}: {e}")
            return False
    
    def validate_pdf(self, file_path: str) -> bool:
        """Проверяет, является ли файл валидным PDF"""
        try:
            with fitz.open(file_path) as doc:
                return len(doc) > 0
        except Exception as e:
            logger.error(f"Ошибка валидации PDF: {e}")
            return False
    
    def extract_text_only(self, pdf_path: str) -> str:
        """Извлекает только текст из PDF"""
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Ошибка извлечения текста: {e}")
            return ""
    
    def convert_to_word(self, pdf_path: str, output_path: str, 
                       preserve_layout: bool = True, 
                       include_images: bool = True) -> bool:
        """Конвертирует PDF в Word документ"""
        try:
            # Создаем временный файл для конвертации
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
                temp_docx_path = temp_file.name
            
            # Используем pdf2docx для конвертации
            cv = Converter(pdf_path)
            cv.convert(temp_docx_path, start=0, end=None)
            cv.close()
            
            # Если нужно только текст без форматирования
            if not preserve_layout:
                text = self.extract_text_only(pdf_path)
                doc = Document()
                doc.add_paragraph(text)
                doc.save(output_path)
                os.unlink(temp_docx_path)
            else:
                # Перемещаем временный файл в финальное место
                os.rename(temp_docx_path, output_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка конвертации в Word: {e}")
            return False
    
    def extract_tables_to_excel(self, pdf_path: str, output_path: str) -> bool:
        """Извлекает таблицы из PDF и сохраняет в Excel"""
        try:
            all_tables = []
            
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    tables = page.extract_tables()
                    
                    for table_num, table in enumerate(tables, 1):
                        if table:
                            # Создаем DataFrame для каждой таблицы
                            df = pd.DataFrame(table[1:], columns=table[0])
                            df['Страница'] = page_num
                            df['Таблица'] = table_num
                            all_tables.append(df)
            
            if all_tables:
                # Объединяем все таблицы
                combined_df = pd.concat(all_tables, ignore_index=True)
                
                # Сохраняем в Excel с несколькими листами
                with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                    combined_df.to_excel(writer, sheet_name='Все_таблицы', index=False)
                    
                    # Создаем отдельные листы для каждой страницы
                    for page_num in combined_df['Страница'].unique():
                        page_data = combined_df[combined_df['Страница'] == page_num]
                        sheet_name = f'Страница_{int(page_num)}'
                        page_data.to_excel(writer, sheet_name=sheet_name, index=False)
                
                return True
            else:
                # Если таблиц нет, создаем Excel с текстом
                text = self.extract_text_only(pdf_path)
                df = pd.DataFrame({'Текст': [text]})
                df.to_excel(output_path, index=False)
                return True
                
        except Exception as e:
            logger.error(f"Ошибка извлечения таблиц: {e}")
            return False
    
    def get_pdf_info(self, pdf_path: str) -> dict:
        """Получает информацию о PDF файле"""
        try:
            with fitz.open(pdf_path) as doc:
                info = {
                    'pages': len(doc),
                    'title': doc.metadata.get('title', 'Без названия'),
                    'author': doc.metadata.get('author', 'Неизвестно'),
                    'subject': doc.metadata.get('subject', ''),
                    'creator': doc.metadata.get('creator', ''),
                    'producer': doc.metadata.get('producer', ''),
                    'creation_date': doc.metadata.get('creationDate', ''),
                    'modification_date': doc.metadata.get('modDate', '')
                }
                return info
        except Exception as e:
            logger.error(f"Ошибка получения информации о PDF: {e}")
            return {}
    
    def cleanup_temp_files(self, *file_paths):
        """Удаляет временные файлы"""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception as e:
                logger.error(f"Ошибка удаления файла {file_path}: {e}")
