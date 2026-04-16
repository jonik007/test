"""
Библиотека для чтения LAS файлов из памяти (bytes или str).

Подобна lasio, но оптимизирована для работы с данными в памяти,
а не с файлами на диске.
"""

import io
import logging
import re
from typing import Union, Optional, Dict, Any, List
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class HeaderItem:
    """Элемент заголовка LAS файла."""
    mnemonic: str = ""
    unit: str = ""
    value: Any = None
    descr: str = ""
    
    def __str__(self):
        return f"{self.mnemonic}: {self.value} {self.unit} - {self.descr}"


@dataclass
class CurveItem:
    """Элемент кривой (данных) LAS файла."""
    mnemonic: str = ""
    unit: str = ""
    descr: str = ""
    data: np.ndarray = field(default_factory=lambda: np.array([]))
    
    @property
    def values(self) -> np.ndarray:
        """Возвращает массив данных кривой."""
        return self.data
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        return self.data[idx]


class SectionItems(dict):
    """Коллекция элементов секции с доступом по индексу и имени."""
    
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
    
    def __setattr__(self, name, value):
        if name in ('_keys_order',):
            super().__setattr__(name, value)
        else:
            self[name] = value
    
    def keys(self):
        return list(self.keys()) if hasattr(self, '_keys_order') else super().keys()
    
    def values(self):
        return [self[k] for k in self.keys()]
    
    def items(self):
        return [(k, self[k]) for k in self.keys()]
    
    def __iter__(self):
        return iter(super().keys())
    
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(super().values())[key]
        return super().__getitem__(key)
    
    def append(self, item):
        """Добавить элемент в секцию."""
        if hasattr(item, 'mnemonic'):
            self[item.mnemonic] = item
        else:
            self[str(len(self))] = item


class LASFile:
    """
    Класс для представления LAS файла, загруженного из памяти.
    
    Поддерживает загрузку из:
    - bytes (байтовое содержимое файла)
    - str (текстовое содержимое файла)
    - file-like объект (io.BytesIO, io.StringIO)
    
    Пример использования:
        # Из байтов
        with open('well.las', 'rb') as f:
            las_data = f.read()
        las = LASFile(las_data)
        
        # Из строки
        las = LASFile(las_string)
        
        # Из BytesIO
        las = LASFile(io.BytesIO(las_data))
        
        # Доступ к данным
        depth = las.curves['DEPT'].data
        gr = las.curves['GR'].data
        print(las.well.WELL.value)
    """
    
    def __init__(self, file_ref: Union[bytes, str, io.IOBase], **kwargs):
        """
        Инициализация LAS файла из памяти.
        
        Arguments:
            file_ref: байты, строка или file-like объект с содержимым LAS файла
            
        Keyword Arguments:
            ignore_header_errors (bool): игнорировать ошибки заголовка (False)
            ignore_comments (tuple): символы комментариев в заголовках
            ignore_data_comments (str): символ комментариев в секции данных
            mnemonic_case (str): 'preserve', 'upper', 'lower' - регистр мнемоник
            ignore_data (bool): не читать данные, только заголовок
            null_policy (str): политика обработки NULL значений
            index_unit (str): единицы измерения индексной кривой ('m' или 'ft')
        """
        self.sections = {
            'Version': SectionItems(),
            'Well': SectionItems(),
            'Curves': SectionItems(),
            'Parameter': SectionItems(),
            'Other': ''
        }
        self.curves: List[CurveItem] = []
        self.index_unit: Optional[str] = None
        self.version = self.sections['Version']
        self.well = self.sections['Well']
        self.curves_section = self.sections['Curves']
        self.params = self.sections['Parameter']
        self.other = self.sections['Other']
        self._raw_text = ""
        
        if file_ref is not None:
            self.read(file_ref, **kwargs)
    
    def read(self, file_ref: Union[bytes, str, io.IOBase], **kwargs):
        """
        Читать LAS файл из памяти.
        
        Arguments:
            file_ref: байты, строка или file-like объект
            
        Keyword Arguments: те же что и в __init__
        """
        # Конвертируем входные данные в текстовый поток
        text = self._convert_to_text(file_ref)
        self._raw_text = text
        
        # Разбираем файл
        self._parse(text, **kwargs)
    
    def _convert_to_text(self, file_ref: Union[bytes, str, io.IOBase]) -> str:
        """Конвертировать input в текстовую строку."""
        if isinstance(file_ref, bytes):
            # Пытаемся определить кодировку
            try:
                return file_ref.decode('utf-8')
            except UnicodeDecodeError:
                return file_ref.decode('latin-1')
        elif isinstance(file_ref, str):
            return file_ref
        elif hasattr(file_ref, 'read'):
            # file-like объект
            content = file_ref.read()
            if isinstance(content, bytes):
                try:
                    return content.decode('utf-8')
                except UnicodeDecodeError:
                    return content.decode('latin-1')
            return content
        else:
            raise TypeError(f"Unsupported type: {type(file_ref)}")
    
    def _parse(self, text: str, **kwargs):
        """Разобрать текст LAS файла."""
        ignore_comments = kwargs.get('ignore_comments', ('#',))
        mnemonic_case = kwargs.get('mnemonic_case', 'upper')
        ignore_data = kwargs.get('ignore_data', False)
        
        lines = text.split('\n')
        current_section = None
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Пропускаем пустые строки
            if not line:
                i += 1
                continue
            
            # Проверяем начало секции
            section_match = re.match(r'^~(\w+)', line)
            if section_match:
                section_name = section_match.group(1)
                current_section = self._get_section_name(section_name)
                i += 1
                continue
            
            if current_section == 'Version':
                self._parse_header_line(line, self.sections['Version'], 
                                       ignore_comments, mnemonic_case)
            elif current_section == 'Well':
                self._parse_header_line(line, self.sections['Well'], 
                                       ignore_comments, mnemonic_case)
            elif current_section == 'Curves':
                self._parse_header_line(line, self.sections['Curves'], 
                                       ignore_comments, mnemonic_case)
            elif current_section == 'Parameter':
                self._parse_header_line(line, self.sections['Parameter'], 
                                       ignore_comments, mnemonic_case)
            elif current_section == 'Other':
                # Секция Other может быть многострочной
                other_lines = []
                while i < len(lines):
                    next_line = lines[i].strip()
                    if next_line.startswith('~'):
                        break
                    if next_line and not next_line.startswith(ignore_comments):
                        other_lines.append(next_line)
                    i += 1
                self.sections['Other'] = '\n'.join(other_lines)
                continue
            elif current_section == 'ASCII':
                if not ignore_data:
                    # Собираем все строки данных
                    data_lines = []
                    while i < len(lines):
                        data_line = lines[i].strip()
                        if data_line and not data_line.startswith(ignore_comments):
                            data_lines.append(data_line)
                        i += 1
                    self._parse_data(data_lines, **kwargs)
                    break
            
            i += 1
    
    def _get_section_name(self, section_name: str) -> str:
        """Нормализовать имя секции."""
        section_map = {
            'V': 'Version',
            'VERSION': 'Version',
            'W': 'Well',
            'WELL': 'Well',
            'C': 'Curves',
            'CURVE': 'Curves',
            'P': 'Parameter',
            'PARAMETER': 'Parameter',
            'O': 'Other',
            'OTHER': 'Other',
            'A': 'ASCII',
            'ASCII': 'ASCII',
        }
        return section_map.get(section_name.upper(), section_name)
    
    def _parse_header_line(self, line: str, section: SectionItems, 
                          ignore_comments: tuple, mnemonic_case: str):
        """Разобрать строку заголовка."""
        # Удаляем комментарии в начале строки
        for comment_char in ignore_comments:
            if line.startswith(comment_char):
                return
        
        # Инициализируем переменные
        mnemonic = ''
        unit = ''
        value = ''
        descr = ''
        
        # Разделяем по ':' чтобы отделить описание
        if ':' in line:
            left_part, right_part = line.split(':', 1)
            left_part = left_part.strip()
            right_part = right_part.strip()
        else:
            left_part = line.strip()
            right_part = ''
        
        # Парсим левую часть: "MNEMONIC.UNIT VALUE" или "MNEMONIC. VALUE" или "MNEMONIC VALUE"
        parts = left_part.split()
        if not parts:
            return
        
        # Первый элемент - это mnemonic.unit или mnemonic
        mnemonic_unit = parts[0]
        
        # Разбираем mnemonic.unit.value в разных форматах
        if '.' in mnemonic_unit:
            parts_mu = mnemonic_unit.split('.')
            mnemonic = parts_mu[0].strip()
            
            # Проверяем сколько частей после split
            if len(parts_mu) >= 2:
                unit = parts_mu[1].strip()
            
            # Если есть третья часть (например DEPT.M.1000), это значение
            if len(parts_mu) >= 3:
                value = parts_mu[2].strip()
            elif len(parts) >= 2:
                # Значение может быть отдельным словом
                value = parts[1].strip()
        else:
            mnemonic = mnemonic_unit
            unit = ''
            # Значение может быть следующим словом
            if len(parts) >= 2:
                value = parts[1].strip()
        
        # Если значение не найдено, пробуем получить из правой части
        if not value and right_part:
            # Проверяем есть ли значение перед описанием (формат "value : description")
            if ' : ' in right_part:
                potential_value = right_part.split(' : ')[0].strip()
                # Если потенциальное значение не пустое и не начинается с пробела
                if potential_value:
                    value = potential_value
                    descr = right_part.split(' : ', 1)[1].strip()
            else:
                # Вся правая часть - это значение
                value = right_part
        
        # Если описание ещё не найдено, пробуем найти его
        if not descr and right_part:
            if ' : ' in right_part:
                descr = right_part.split(' : ', 1)[1].strip()
            elif right_part.startswith(' '):
                descr = right_part.strip()
        
        # Применяем регистр к мнемонике
        if mnemonic_case == 'upper':
            mnemonic = mnemonic.upper()
        elif mnemonic_case == 'lower':
            mnemonic = mnemonic.lower()
        
        # Создаём элемент заголовка
        header_item = HeaderItem(
            mnemonic=mnemonic,
            unit=unit,
            value=value,
            descr=descr
        )
        
        section[mnemonic] = header_item
    
    def _parse_data(self, data_lines: List[str], **kwargs):
        """Разобрать секцию данных."""
        if not data_lines or not self.curves_section:
            return
        
        null_policy = kwargs.get('null_policy', 'strict')
        
        # Определяем разделитель (пробелы, табы, запятые)
        sample_line = data_lines[0]
        if ',' in sample_line:
            delimiter = ','
        elif '\t' in sample_line:
            delimiter = '\t'
        else:
            delimiter = None  # произвольные пробелы
        
        # Преобразуем в numpy массив
        try:
            data_array = np.genfromtxt(
                data_lines,
                delimiter=delimiter,
                dtype=float
            )
        except Exception as e:
            logger.warning(f"Error parsing data with numpy: {e}")
            # Пробуем парсить вручную
            data_array = self._parse_data_manual(data_lines)
        
        if data_array.ndim == 1:
            data_array = data_array.reshape(-1, 1)
        
        # Распределяем данные по кривым
        curve_names = list(self.curves_section.keys())
        
        for i, curve_name in enumerate(curve_names):
            if i < data_array.shape[1]:
                curve_item = self.curves_section[curve_name]
                curve_obj = CurveItem(
                    mnemonic=curve_item.mnemonic,
                    unit=curve_item.unit,
                    descr=curve_item.descr,
                    data=data_array[:, i]
                )
                self.curves.append(curve_obj)
    
    def _parse_data_manual(self, data_lines: List[str]) -> np.ndarray:
        """Ручной парсинг данных (fallback)."""
        rows = []
        for line in data_lines:
            values = line.split()
            row = []
            for v in values:
                try:
                    row.append(float(v))
                except ValueError:
                    row.append(np.nan)
            if row:
                rows.append(row)
        return np.array(rows)
    
    @property
    def df(self):
        """Вернуть данные как pandas DataFrame (если pandas доступен)."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for df property")
        
        data_dict = {}
        for curve in self.curves:
            data_dict[curve.mnemonic] = curve.data
        return pd.DataFrame(data_dict)
    
    def get_curve(self, mnemonic: str) -> Optional[CurveItem]:
        """Получить кривую по имени."""
        for curve in self.curves:
            if curve.mnemonic.upper() == mnemonic.upper():
                return curve
        return None
    
    def append_curve(self, mnemonic: str, data: np.ndarray, 
                    unit: str = '', descr: str = ''):
        """Добавить кривую."""
        curve = CurveItem(mnemonic=mnemonic, unit=unit, descr=descr, data=data)
        self.curves.append(curve)
        self.curves_section[mnemonic] = HeaderItem(
            mnemonic=mnemonic, unit=unit, descr=descr
        )
    
    def write(self, to: Optional[str] = None) -> Optional[str]:
        """
        Записать LAS файл.
        
        Arguments:
            to: путь к файлу для записи. Если None, возвращает строку.
            
        Returns:
            str содержимое если to=None, иначе None
        """
        lines = []
        
        # Версия
        lines.append('~VERSION INFORMATION')
        for item in self.sections['Version'].values():
            lines.append(f" {item.mnemonic}.{'.' if item.unit else ''}{item.unit} {item.value} : {item.descr}")
        
        # Well
        lines.append('~WELL INFORMATION')
        for item in self.sections['Well'].values():
            lines.append(f" {item.mnemonic}.{'.' if item.unit else ''}{item.unit} {item.value} : {item.descr}")
        
        # Curves
        lines.append('~CURVE INFORMATION')
        for curve in self.curves:
            lines.append(f" {curve.mnemonic}.{'.' if curve.unit else ''}{curve.unit} : {curve.descr}")
        
        # Parameter
        lines.append('~PARAMETER INFORMATION')
        for item in self.sections['Parameter'].values():
            lines.append(f" {item.mnemonic}.{'.' if item.unit else ''}{item.unit} {item.value} : {item.descr}")
        
        # Other
        if self.sections['Other']:
            lines.append('~OTHER')
            lines.append(self.sections['Other'])
        
        # ASCII
        lines.append('~ASCII')
        if self.curves:
            n_points = len(self.curves[0].data)
            for i in range(n_points):
                row = []
                for curve in self.curves:
                    if i < len(curve.data):
                        row.append(str(curve.data[i]))
                    else:
                        row.append('')
                lines.append(' '.join(row))
        
        content = '\n'.join(lines)
        
        if to:
            with open(to, 'w') as f:
                f.write(content)
            return None
        else:
            return content
    
    def __repr__(self):
        well_name = self.well.get('WELL', HeaderItem()).value if 'WELL' in self.well else 'Unknown'
        n_curves = len(self.curves)
        n_points = len(self.curves[0]) if self.curves else 0
        return f"<LASFile '{well_name}' with {n_curves} curves and {n_points} points>"


# Удобные функции для чтения из памяти
def read(bytes_or_str: Union[bytes, str, io.IOBase], **kwargs) -> LASFile:
    """
    Прочитать LAS файл из памяти.
    
    Arguments:
        bytes_or_str: байты, строка или file-like объект
        
    Returns:
        LASFile объект
    """
    return LASFile(bytes_or_str, **kwargs)


def read_bytes(data: bytes, **kwargs) -> LASFile:
    """Прочитать LAS файл из байтов."""
    return LASFile(data, **kwargs)


def read_string(text: str, **kwargs) -> LASFile:
    """Прочитать LAS файл из строки."""
    return LASFile(text, **kwargs)


def read_buffer(buffer: io.IOBase, **kwargs) -> LASFile:
    """Прочитать LAS файл из file-like объекта."""
    return LASFile(buffer, **kwargs)
