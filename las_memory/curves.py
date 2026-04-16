"""
Модуль для представления кривых (кривых скважины).
"""

from typing import List, Optional, Union
import numpy as np


class Curve:
    """
    Представляет одну кривую из LAS файла.
    
    Атрибуты:
        mnemonic: Идентификатор кривой (например, 'GR', 'DT')
        unit: Единицы измерения (например, 'GAPI', 'US/F')
        value: Значение параметра (обычно пустая строка)
        descr: Описание кривой
        data: numpy array с данными кривой
    """
    
    def __init__(
        self,
        mnemonic: str = "",
        unit: str = "",
        value: str = "",
        descr: str = "",
        data: Optional[np.ndarray] = None
    ):
        self.mnemonic = mnemonic
        self.unit = unit
        self.value = value
        self.descr = descr
        self.data = data if data is not None else np.array([])
    
    def __repr__(self):
        return f"Curve(mnemonic='{self.mnemonic}', unit='{self.unit}', descr='{self.descr}')"
    
    def __len__(self):
        return len(self.data)
    
    @property
    def header_line(self) -> str:
        """Возвращает строку заголовка кривой в формате LAS."""
        return f"{self.mnemonic:<16}{self.unit:<14}{self.value:>10}:{self.descr}"


class CurveCollection:
    """
    Коллекция кривых с удобным доступом по индексу и имени.
    """
    
    def __init__(self, curves: Optional[List[Curve]] = None):
        self._curves = curves if curves is not None else []
    
    def append(self, curve: Curve):
        self._curves.append(curve)
    
    def __getitem__(self, key):
        if isinstance(key, int):
            return self._curves[key]
        elif isinstance(key, str):
            for curve in self._curves:
                if curve.mnemonic.upper() == key.upper():
                    return curve
            raise KeyError(f"Кривая '{key}' не найдена")
        else:
            raise TypeError("Ключ должен быть int или str")
    
    def __len__(self):
        return len(self._curves)
    
    def __iter__(self):
        return iter(self._curves)
    
    def __repr__(self):
        return f"CurveCollection({len(self._curves)} curves)"
    
    @property
    def mnemonics(self) -> List[str]:
        """Список имен всех кривых."""
        return [c.mnemonic for c in self._curves]
    
    @property
    def data(self) -> np.ndarray:
        """
        Возвращает все данные кривых как 2D numpy array.
        Каждая колонка - отдельная кривая.
        """
        if not self._curves:
            return np.array([])
        
        # Проверяем, что все кривые имеют одинаковую длину
        lengths = [len(c.data) for c in self._curves if len(c.data) > 0]
        if not lengths:
            return np.array([])
        
        max_len = max(lengths)
        data_arrays = []
        
        for curve in self._curves:
            if len(curve.data) == 0:
                data_arrays.append(np.full(max_len, np.nan))
            elif len(curve.data) < max_len:
                # Дополняем до максимальной длины
                padded = np.full(max_len, np.nan)
                padded[:len(curve.data)] = curve.data
                data_arrays.append(padded)
            else:
                data_arrays.append(curve.data)
        
        return np.column_stack(data_arrays)
