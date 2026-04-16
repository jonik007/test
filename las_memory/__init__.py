"""
las_memory - Библиотека для чтения LAS файлов из памяти.

Аналог lasio, но работает с данными в памяти (bytes, str, BytesIO, StringIO)
без необходимости сохранения файла на диск.
"""

__version__ = "0.1.0"
__author__ = "Assistant"

from .reader import read_las, LasFile
from .curves import Curve
from .header import Header, SectionItem

__all__ = ["read_las", "LasFile", "Curve", "Header", "SectionItem"]
