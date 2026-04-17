"""
Основной модуль для чтения LAS файлов из памяти.
"""

import re
from io import StringIO, BytesIO
from typing import Union, Dict, List, Optional, Any, Tuple
import numpy as np

from .header import Header, SectionItem
from .curves import Curve, CurveCollection


def detect_encoding(data: bytes) -> str:
    """
    Автодетект кодировки для LAS файлов с поддержкой русских символов.
    
    Порядок проверки:
    1. UTF-8 (стандартная современная кодировка) - приоритет если валидный UTF-8
    2. Windows-1251 (CP1251) - стандартная кодировка Windows для кириллицы
    3. CP866 (DOS) - старая DOS кодировка для русских символов
    4. KOI8-R - альтернативная русская кодировка
    
    Args:
        data: Байты файла для анализа
        
    Returns:
        str: Название обнаруженной кодировки
    """
    # Пустые данные - возвращаем utf-8 по умолчанию
    if not data:
        return 'utf-8'
    
    encodings_to_try = [
        ('utf-8', 'UTF-8'),
        ('windows-1251', 'Windows-1251 (CP1251)'),
        ('cp866', 'DOS (CP866)'),
        ('koi8-r', 'KOI8-R'),
    ]
    
    valid_decodings = []
    
    for encoding, encoding_name in encodings_to_try:
        try:
            # Пробуем декодировать
            text = data.decode(encoding)
            
            # Проверяем, содержит ли текст кириллические символы
            has_cyrillic = any('\u0400' <= char <= '\u04FF' for char in text)
            
            # Проверяем на наличие некорректных символов (замененных или управляющих)
            # которые могут указывать на неправильную кодировку
            has_replacement = '\ufffd' in text
            
            if not has_replacement:
                # Если есть кириллица - это хороший кандидат
                if has_cyrillic:
                    valid_decodings.append((encoding, True))
                else:
                    valid_decodings.append((encoding, False))
                
        except (UnicodeDecodeError, LookupError):
            continue
    
    # Если нашли валидные декодирования
    if valid_decodings:
        # Приоритет: UTF-8 с кириллицей > Windows-1251 с кириллицей > CP866 с кириллицей > KOI8-R с кириллицей
        # Затем UTF-8 без кириллицы > остальные
        
        # Сначала ищем UTF-8
        for encoding, has_cyrillic in valid_decodings:
            if encoding == 'utf-8':
                return 'utf-8'
        
        # Затем ищем кодировки с кириллицей в порядке приоритета
        priority_encodings = ['windows-1251', 'cp866', 'koi8-r']
        for priority_enc in priority_encodings:
            for encoding, has_cyrillic in valid_decodings:
                if encoding == priority_enc and has_cyrillic:
                    return encoding
        
        # Если нет кириллицы, возвращаем первую валидную
        return valid_decodings[0][0]
    
    # Если ничего не подошло, возвращаем utf-8 как fallback
    return 'utf-8'


class LasFile:
    """
    Представляет parsed LAS файл.
    
    Атрибуты:
        version: Секция ~VERSION
        well: Секция ~WELL
        curve: Секция ~CURVE
        param: Секция ~PARAM
        other: Секция ~OTHER (текст)
        curves: Коллекция кривых с данными
    """
    
    def __init__(self):
        self.version = Header("~VERSION")
        self.well = Header("~WELL")
        self.curve = Header("~CURVE")
        self.param = Header("~PARAM")
        self.other = ""
        self.curves = CurveCollection()
    
    def __repr__(self):
        well_name = self.well.get("WELL", "Unknown")
        return f"LasFile(well='{well_name}', {len(self.curves)} curves)"
    
    @property
    def data(self) -> np.ndarray:
        """Возвращает все данные кривых как 2D numpy array."""
        return self.curves.data
    
    @property
    def df(self):
        """
        Возвращает данные как pandas DataFrame (если pandas доступен).
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas не установлен. Установите: pip install pandas")
        
        if not self.curves:
            return None
        
        data = self.data
        columns = [c.mnemonic for c in self.curves]
        return pd.DataFrame(data, columns=columns)
    
    def write(self, file_obj=None) -> Optional[str]:
        """
        Записывает LAS файл в файловый объект или возвращает как строку.
        
        Args:
            file_obj: Файловый объект для записи. Если None, возвращает строку.
        
        Returns:
            Строку с содержимым LAS файла, если file_obj is None, иначе None.
        """
        lines = []
        
        # Версия
        lines.append("~VERSION INFORMATION")
        lines.append(" VERS.                          2.0 :   CWLS LOG ASCII STANDARD - VERSION 2.0")
        for item in self.version:
            lines.append(item.header_line)
        
        # Well секция
        lines.append("~WELL INFORMATION")
        for item in self.well:
            lines.append(item.header_line)
        
        # Curve секция
        lines.append("~CURVE INFORMATION")
        for item in self.curve:
            lines.append(item.header_line)
        
        # Param секция
        lines.append("~PARAMETER INFORMATION")
        for item in self.param:
            lines.append(item.header_line)
        
        # Other секция
        if self.other.strip():
            lines.append("~OTHER")
            lines.append(self.other.strip())
        
        # Данные
        lines.append("~A")
        
        if self.curves:
            data = self.data
            for row in data:
                values = []
                for val in row:
                    if np.isnan(val):
                        values.append("-999.25")  # Стандартный null value для LAS
                    else:
                        values.append(f"{val:.5f}")
                lines.append("  ".join(values))
        
        content = "\n".join(lines)
        
        if file_obj is None:
            return content
        else:
            file_obj.write(content)
            return None


def read_las(
    source: Union[str, bytes, StringIO, BytesIO],
    encoding: Optional[str] = None,
    auto_detect_encoding: bool = True,
    ignore_data_errors: bool = False,
    **kwargs
) -> LasFile:
    """
    Читает LAS файл из памяти.
    
    Args:
        source: Источник данных. Может быть:
            - str: строка с содержимым LAS файла
            - bytes: байты с содержимым LAS файла
            - StringIO: текстовый буфер
            - BytesIO: байтовый буфер
        encoding: Кодировка для декодирования байтов. Если None и auto_detect_encoding=True,
                  будет использован автодетект кодировки.
        auto_detect_encoding: Автоматически определять кодировку для байтовых данных.
                              Проверяет UTF-8, Windows-1251, CP866 (DOS), KOI8-R.
                              Игнорируется, если encoding явно указан или source не bytes/BytesIO.
        ignore_data_errors: Игнорировать ошибки при парсинге данных
        **kwargs: Дополнительные аргументы (для совместимости с lasio)
    
    Returns:
        LasFile: Объект с распарсенными данными
    
    Примеры:
        >>> from io import BytesIO
        >>> with open('file.las', 'rb') as f:
        ...     data = f.read()
        >>> las = read_las(data)  # Автодетект кодировки
        
        >>> las = read_las(data, encoding='windows-1251')  # Явная кодировка
        
        >>> las = read_las(BytesIO(data), auto_detect_encoding=True)
        
        >>> las = read_las(las_string)
    """
    # Конвертируем источник в строку
    if isinstance(source, bytes):
        if encoding is None and auto_detect_encoding:
            encoding = detect_encoding(source)
        elif encoding is None:
            encoding = 'utf-8'
        text = source.decode(encoding)
    elif isinstance(source, BytesIO):
        data = source.read()
        if encoding is None and auto_detect_encoding:
            encoding = detect_encoding(data)
        elif encoding is None:
            encoding = 'utf-8'
        text = data.decode(encoding)
    elif isinstance(source, StringIO):
        text = source.getvalue()
    elif isinstance(source, str):
        text = source
    else:
        raise TypeError(f"Неподдерживаемый тип источника: {type(source)}")
    
    parser = LasParser(text, ignore_data_errors=ignore_data_errors)
    return parser.parse()


class LasParser:
    """
    Парсер LAS файлов.
    """
    
    def __init__(self, text: str, ignore_data_errors: bool = False):
        self.text = text
        self.ignore_data_errors = ignore_data_errors
        self.lines = text.split('\n')
    
    def parse(self) -> LasFile:
        """Парсит текст и возвращает LasFile объект."""
        las = LasFile()
        
        current_section = None
        in_data = False
        
        i = 0
        while i < len(self.lines):
            line = self.lines[i].strip()
            
            # Пропускаем пустые строки и комментарии вне секций
            if not line:
                i += 1
                continue
            
            # Проверяем начало секции
            if line.startswith('~'):
                section_match = re.match(r'~\s*(\w+)(?:\s+(.*))?', line, re.IGNORECASE)
                if section_match:
                    section_name = section_match.group(1).upper()
                    section_title = section_match.group(2) or ""
                    
                    # Поддержка различных вариантов написания названий секций
                    if section_name == 'VERSION' or section_name.startswith('VERSION'):
                        current_section = las.version
                        current_section.title = "~VERSION"
                    elif section_name == 'WELL' or section_name.startswith('WELL'):
                        current_section = las.well
                        current_section.title = "~WELL"
                    elif section_name == 'CURVE' or section_name.startswith('CURVE'):
                        current_section = las.curve
                        current_section.title = "~CURVE"
                    elif section_name in ('PARAM', 'PARAMETER') or section_name.startswith('PARAM'):
                        current_section = las.param
                        current_section.title = "~PARAM"
                    elif section_name == 'OTHER':
                        current_section = None
                        las.other = ""
                    elif section_name == 'A' or section_name == 'ASCII':  # Секция данных
                        current_section = None
                        in_data = True
                        i += 1
                        break
                    else:
                        current_section = None
                    
                    i += 1
                    continue
            
            # Обрабатываем содержимое секции
            if current_section is not None:
                item = self._parse_header_line(line)
                if item:
                    current_section.append(item)
            elif current_section is None and '~OTHER' in [l.strip() for l in self.lines[:i]]:
                # Собираем OTHER текст
                if not line.startswith('~'):
                    las.other += line + '\n'
            
            i += 1
        
        # Парсим данные
        if in_data:
            self._parse_data(las, i)
        
        return las
    
    def _parse_header_line(self, line: str) -> Optional[SectionItem]:
        """Парсит строку заголовка и возвращает SectionItem."""
        # Удаляем комментарии после ':'
        comment_idx = line.find(':')
        
        if comment_idx == -1:
            # Нет двоеточия - пробуем распарсить как mnemonic.value без описания
            # Например: "WELL.                          TEST" или "VERS.  2.0"
            main_part = line.strip()
            descr = ""
        else:
            descr = line[comment_idx + 1:].strip()
            main_part = line[:comment_idx].strip()
        
        # LAS формат: MNEMONIC(16 символов) UNIT(14 символов) VALUE(10 символов) : DESC
        # Но часто форматируется свободно. Пробуем разные подходы.
        
        # Сначала пробуем строгий формат с фиксированными полями
        mnemonic = main_part[:16].strip() if len(main_part) >= 16 else ""
        rest = main_part[16:].strip() if len(main_part) > 16 else ""
        
        # Если mnemonic содержит точку (например DEPT.M), разделяем
        if '.' in mnemonic and len(mnemonic.split('.')) == 2:
            parts = mnemonic.split('.')
            mnemonic = parts[0]
            unit_from_mnemonic = parts[1]
        else:
            unit_from_mnemonic = ""
        
        # Парсим оставшуюся часть для unit и value
        unit = ""
        value = ""
        
        if rest:
            # Пытаемся выделить unit (обычно первый элемент)
            parts = rest.split(None, 1)  # Разделить на максимум 2 части
            if parts:
                potential_unit = parts[0]
                # Проверяем, выглядит ли это как unit
                if '/' in potential_unit or potential_unit.upper() in ['M', 'FT', 'GAPI', 'OHMM', 'US/F', 'V/V', 'DEGC', 'MM', 'IN']:
                    unit = potential_unit
                    value = parts[1].strip() if len(parts) > 1 else ""
                else:
                    # Возможно это value без unit
                    value = rest
        elif unit_from_mnemonic:
            # Unit был извлечен из mnemonic
            unit = unit_from_mnemonic
        
        # Если mnemonic все еще пуст или rest пуст, пробуем альтернативный парсинг
        # Для случаев типа "GR  .GAPI" где точка перед unit
        if not unit and rest == "" and len(main_part) < 16:
            # Пробуем найти точку в main_part
            dot_idx = main_part.find('.')
            if dot_idx > 0:
                mnemonic = main_part[:dot_idx].strip()
                unit = main_part[dot_idx+1:].strip()
        
        # Дополнительная проверка для случаев с точкой в начале value
        # Например "GR  .GAPI" -> mnemonic="GR", unit="GAPI"
        if not unit and value.startswith('.'):
            unit = value.lstrip('.')
            value = ""
        
        # Обработка случая когда unit присоединен к mnemonic (BHT.DEGC)
        # и значение находится после пробелов
        if unit_from_mnemonic and not unit and value:
            unit = unit_from_mnemonic
        
        # Если mnemonic все еще пуст, пробуем распарсить по пробелам
        if not mnemonic:
            parts = main_part.split()
            if parts:
                first = parts[0]
                if '.' in first:
                    mnemonic, unit_from_mnemonic = first.split('.', 1)
                    unit = unit_from_mnemonic
                else:
                    mnemonic = first
                if len(parts) > 1:
                    value = ' '.join(parts[1:])
        
        # Дополнительная обработка для случаев типа "BHT.DEGC 35" где DEGC - это unit
        # а 35 - значение, но mnemonic был извлечен как "BHT.DEGC"
        if '.' in mnemonic and not unit and value:
            parts = mnemonic.split('.', 1)
            mnemonic = parts[0]
            unit = parts[1]
        
        return SectionItem(mnemonic=mnemonic, unit=unit, value=value.strip(), descr=descr)
    
    def _parse_data(self, las: LasFile, start_idx: int):
        """Парсит секцию данных '~A'."""
        data_lines = []
        
        for i in range(start_idx, len(self.lines)):
            line = self.lines[i].strip()
            if not line:
                continue
            if line.startswith('~'):
                break
            data_lines.append(line)
        
        if not data_lines:
            return
        
        # Парсим числа из строк
        all_values = []
        for line in data_lines:
            # Разделяем по пробелам
            parts = line.split()
            for part in parts:
                try:
                    val = float(part)
                    # Проверяем на null значения
                    if val < -999:
                        val = np.nan
                    all_values.append(val)
                except ValueError:
                    if not self.ignore_data_errors:
                        all_values.append(np.nan)
                    else:
                        all_values.append(np.nan)
        
        if not all_values:
            return
        
        # Определяем количество кривых
        n_curves = len(las.curve)
        if n_curves == 0:
            # Если нет определения кривых, пытаемся определить по первой строке
            first_parts = data_lines[0].split()
            n_curves = len(first_parts)
        
        # Преобразуем в 2D массив
        n_points = len(all_values) // n_curves
        data_array = np.array(all_values[:n_points * n_curves]).reshape(n_points, n_curves)
        
        # Создаем кривые
        for j in range(min(n_curves, data_array.shape[1])):
            if j < len(las.curve):
                header_item = las.curve[j]
                curve = Curve(
                    mnemonic=header_item.mnemonic,
                    unit=header_item.unit,
                    descr=header_item.descr,
                    data=data_array[:, j]
                )
            else:
                curve = Curve(
                    mnemonic=f"CURVE{j}",
                    data=data_array[:, j]
                )
            las.curves.append(curve)
