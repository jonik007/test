"""
Модуль для работы с заголовками LAS файла.
"""

from typing import Dict, List, Optional


class SectionItem:
    """
    Представляет одну строку в секции заголовка LAS.
    
    Атрибуты:
        mnemonic: Идентификатор (например, WELL, DATE)
        unit: Единицы измерения
        value: Значение
        descr: Описание
    """
    
    def __init__(
        self,
        mnemonic: str = "",
        unit: str = "",
        value: str = "",
        descr: str = ""
    ):
        self.mnemonic = mnemonic
        self.unit = unit
        self.value = value
        self.descr = descr
    
    def __repr__(self):
        return f"SectionItem(mnemonic='{self.mnemonic}', value='{self.value}')"
    
    @property
    def header_line(self) -> str:
        """Возвращает строку в формате LAS."""
        if self.unit:
            return f"{self.mnemonic:<16}{self.unit:<14}{self.value:>10}:{self.descr}"
        else:
            return f"{self.mnemonic:<16}{'':<14}{self.value:>10}:{self.descr}"


class Header:
    """
    Представляет секцию заголовка (~WELL, ~VERSION, etc.)
    
    Позволяет доступ к элементам как по индексу, так и по имени мнемоники.
    """
    
    def __init__(self, title: str = ""):
        self.title = title
        self._items: List[SectionItem] = []
        self._mnemonic_index: Dict[str, int] = {}
    
    def append(self, item: SectionItem):
        """Добавляет элемент в заголовок."""
        idx = len(self._items)
        self._items.append(item)
        self._mnemonic_index[item.mnemonic.upper()] = idx
    
    def __getitem__(self, key):
        if isinstance(key, int):
            return self._items[key]
        elif isinstance(key, str):
            idx = self._mnemonic_index.get(key.upper())
            if idx is not None:
                return self._items[idx]
            raise KeyError(f"Элемент '{key}' не найден в секции {self.title}")
        else:
            raise TypeError("Ключ должен быть int или str")
    
    def __len__(self):
        return len(self._items)
    
    def __contains__(self, key):
        if isinstance(key, str):
            return key.upper() in self._mnemonic_index
        return False
    
    def get(self, key: str, default=None):
        """Получает значение по мнемонике, возвращает default если не найдено."""
        try:
            return self[key].value
        except KeyError:
            return default
    
    def keys(self):
        """Возвращает все мнемоники в секции."""
        return [item.mnemonic for item in self._items]
    
    def values(self):
        """Возвращает все значения в секции."""
        return [item.value for item in self._items]
    
    def items(self):
        """Возвращает пары (mnemonic, value)."""
        return [(item.mnemonic, item.value) for item in self._items]
    
    def __repr__(self):
        return f"Header({self.title}, {len(self._items)} items)"
    
    def __iter__(self):
        return iter(self._items)
