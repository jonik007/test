"""
las_memory - Библиотека для чтения LAS файлов из памяти.

Аналог lasio, но работает с данными в памяти (bytes, str, BytesIO, StringIO)
без необходимости сохранения файла на диск. Поддерживает автодетект кодировки
для русских символов (UTF-8, Windows-1251, CP866/DOS, KOI8-R).
"""

__version__ = "0.2.0"
__author__ = "Assistant"

from .reader import read_las, LasFile, detect_encoding
from .curves import Curve
from .header import Header, SectionItem

__all__ = ["read_las", "LasFile", "Curve", "Header", "SectionItem", "detect_encoding"]
