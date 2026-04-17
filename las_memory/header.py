from typing import Dict, List, Any, Optional

class CurveInfo:
    """Информация об одной кривой."""
    def __init__(self, mnemonic: str, unit: str = "", api_code: str = "", description: str = ""):
        self.mnemonic = mnemonic
        self.unit = unit
        self.api_code = api_code
        self.description = description

    def __repr__(self):
        return f"CurveInfo({self.mnemonic}, {self.unit}, {self.description})"

class Header:
    """Контейнер для всех секций заголовка LAS файла."""
    def __init__(self):
        # Словари для хранения данных секций
        # Структура: { 'MNEM': {'value': ..., 'unit': ..., 'description': ...} }
        self.version: Dict[str, Dict[str, Any]] = {}
        self.well: Dict[str, Dict[str, Any]] = {}
        self.parameters: Dict[str, Dict[str, Any]] = {}
        
        # Список объектов CurveInfo
        self.curves: List[CurveInfo] = []
        
        # Сырые данные для секции OTHER (если нужно)
        self.other: str = ""

    def get_well_value(self, mnemonic: str) -> Optional[str]:
        """Получить значение параметра из секции WELL."""
        if mnemonic in self.well:
            return self.well[mnemonic].get('value')
        return None

    def get_version_value(self, mnemonic: str) -> Optional[str]:
        """Получить значение параметра из секции VERSION."""
        if mnemonic in self.version:
            return self.version[mnemonic].get('value')
        return None

    def get_curve_names(self) -> List[str]:
        """Вернуть список имен кривых."""
        return [c.mnemonic for c in self.curves]

    def __repr__(self):
        return f"<Header: Well={self.get_well_value('WELL')}, Curves={len(self.curves)}>"