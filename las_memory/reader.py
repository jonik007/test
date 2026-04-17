import re
import logging
from typing import List, Dict, Any, Optional, Union, Tuple
from io import StringIO, BytesIO

# Импорты классов данных
try:
    from .header import Header, CurveInfo
    from .curves import CurveData
except ImportError:
    # Фоллбэк если запуск идет не как модуль, а напрямую (редко, но бывает)
    class Header:
        def __init__(self):
            self.version = {}
            self.well = {}
            self.curves = []
            self.parameters = {}
    class CurveInfo:
        def __init__(self, mnemonic="", unit="", api_code="", description=""):
            self.mnemonic = mnemonic
            self.unit = unit
            self.api_code = api_code
            self.description = description
    class CurveData:
        def __init__(self, data=None):
            self.data = data if data is not None else []

logger = logging.getLogger(__name__)

def detect_encoding(raw_data: bytes) -> str:
    """Пытается определить кодировку для русских символов."""
    # Порядок важен: сначала пробуем DOS (cp866), потом UTF-8, потом Windows (cp1251), потом latin-1
    encodings = ['cp866', 'utf-8', 'cp1251', 'latin-1']
    
    for enc in encodings:
        try:
            raw_data.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    
    # Если ничего не подошло, возвращаем latin-1 (он принимает любые байты)
    return 'latin-1'

class LasParser:
    def __init__(self, content: str):
        self.content = content
        self.lines = content.splitlines()
        self.header = Header()
        self.data: List[List[float]] = []
        self.curve_names: List[str] = []
        
    def parse(self) -> Tuple[Header, List[str], List[List[float]]]:
        self._parse_header()
        self._parse_data()
        return self.header, self.curve_names, self.data

    def _parse_header(self):
        current_section = None
        
        for line in self.lines:
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith('#'):
                continue
            
            # Детекция секции по первой букве после ~
            if line_stripped.startswith('~'):
                section_type = line_stripped[1].upper()
                
                if section_type == 'V':
                    current_section = 'VERSION'
                elif section_type == 'W':
                    current_section = 'WELL'
                elif section_type == 'C':
                    current_section = 'CURVE'
                elif section_type == 'P':
                    current_section = 'PARAMETER'
                elif section_type == 'O':
                    current_section = 'OTHER'
                elif section_type == 'A':
                    current_section = 'ASCII'
                else:
                    current_section = 'UNKNOWN'
                continue

            if current_section == 'VERSION':
                self._parse_version_line(line_stripped)
            elif current_section == 'WELL':
                self._parse_well_line(line_stripped)
            elif current_section == 'CURVE':
                self._parse_curve_line(line_stripped)
            elif current_section == 'PARAMETER':
                self._parse_parameter_line(line_stripped)

    def _parse_version_line(self, line: str):
        key, value, unit, descr = self._parse_line_components(line)
        if key:
            self.header.version[key] = {'value': value, 'unit': unit, 'description': descr}

    def _parse_well_line(self, line: str):
        key, value, unit, descr = self._parse_line_components(line)
        if key:
            self.header.well[key] = {'value': value, 'unit': unit, 'description': descr}

    def _parse_curve_line(self, line: str):
        key, value, unit, descr = self._parse_line_components(line)
        if key:
            self.header.curves.append(CurveInfo(
                mnemonic=key,
                unit=unit,
                api_code=value,
                description=descr
            ))

    def _parse_parameter_line(self, line: str):
        key, value, unit, descr = self._parse_line_components(line)
        if key:
            self.header.parameters[key] = {'value': value, 'unit': unit, 'description': descr}

    def _parse_line_components(self, line: str) -> Tuple[str, str, str, str]:
        if ':' in line:
            parts = line.split(':', 1)
            data_part = parts[0].strip()
            descr = parts[1].strip()
        else:
            data_part = line.strip()
            descr = ""

        tokens = data_part.split()
        if not tokens:
            return "", "", "", ""
        
        mnemonic_unit = tokens[0]
        value = " ".join(tokens[1:]) if len(tokens) > 1 else ""
        
        if '.' in mnemonic_unit:
            mnem, unit = mnemonic_unit.split('.', 1)
        else:
            mnem = mnemonic_unit
            unit = ""
            
        return mnem, value, unit, descr

    def _parse_data(self):
        in_data_section = False
        self.data = []
        self.curve_names = [c.mnemonic for c in self.header.curves]
        
        for line in self.lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            if line_stripped.startswith('~'):
                if line_stripped[1].upper() == 'A':
                    in_data_section = True
                else:
                    in_data_section = False
                continue
            
            if in_data_section:
                if line_stripped.startswith('#'):
                    continue
                
                try:
                    clean_line = line_stripped.replace(',', ' ')
                    values = [float(x) for x in clean_line.split()]
                    self.data.append(values)
                except ValueError:
                    continue

def read_las(source: Union[str, bytes, StringIO, BytesIO], encoding: Optional[str] = None) -> Dict[str, Any]:
    """
    Читает LAS файл из строки, байтов или буфера.
    Автоматически определяет кодировку, если переданы байты и encoding не указан.
    """
    content = ""
    
    if isinstance(source, bytes):
        if encoding is None:
            encoding = detect_encoding(source)
        content = source.decode(encoding)
    elif isinstance(source, BytesIO):
        b_data = source.getvalue()
        if encoding is None:
            encoding = detect_encoding(b_data)
        content = b_data.decode(encoding)
    elif isinstance(source, StringIO):
        content = source.getvalue()
    elif isinstance(source, str):
        content = source
    else:
        raise ValueError("Unsupported source type.")

    parser = LasParser(content)
    header, curve_names, data_list = parser.parse()
    
    result = {
        'header': header,
        'curve_names': curve_names,
        'data': data_list,
        'version': header.version,
        'well': header.well,
        'curves': header.curves
    }
    
    # Попытка подключить pandas
    try:
        import numpy as np
        import pandas as pd
        
        if data_list and len(data_list) > 0 and len(data_list[0]) > 0:
            df = pd.DataFrame(data_list, columns=curve_names)
            result['df'] = df
            result['numpy'] = df.values
        else:
            result['df'] = pd.DataFrame()
            result['numpy'] = np.array([])
            
    except ImportError:
        result['df'] = None
        result['numpy'] = None
        
    return result