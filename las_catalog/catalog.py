# las_catalog/catalog.py

import os
import glob
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    from las_memory import read_las
except ImportError:
    # Попытка импорта если запускается как модуль внутри проекта
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from las_memory import read_las


def scan_directory(directory_path: str) -> List[Dict[str, Any]]:
    """
    Рекурсивно сканирует директорию на наличие *.LAS файлов.
    
    Args:
        directory_path: Путь к корневой директории для сканирования
        
    Returns:
        Список словарей с информацией о найденных LAS файлах (по одному словарю на кривую)
    """
    results = []
    
    # Нормализуем путь и используем raw string для Windows-style путей
    dir_path = Path(directory_path).resolve()
    
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory_path}")
    
    if not dir_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory_path}")
    
    # Рекурсивный поиск всех *.LAS файлов (регистронезависимый)
    las_files = []
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            if file.upper().endswith('.LAS'):
                las_files.append(os.path.join(root, file))
    
    # Обработка каждого файла
    for las_file in las_files:
        try:
            file_infos = _process_las_file(las_file)
            # _process_las_file возвращает список записей (по одной на кривую)
            results.extend(file_infos)
        except Exception as e:
            # Если файл не удалось прочитать, добавляем запись с ошибкой
            results.append({
                'file_path': las_file,
                'well': None,
                'strt': None,
                'stop': None,
                'step': None,
                'mnemonic': None,
                'unit': None,
                'description': None,
                'error': str(e)
            })
    
    return results


def _process_las_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Обрабатывает один LAS файл и извлекает информацию.
    
    Args:
        file_path: Полный путь к LAS файлу
        
    Returns:
        Список словарей (по одному на каждую кривую в файле)
    """
    results = []
    
    # Читаем файл как байты для автоматического определения кодировки
    with open(file_path, 'rb') as f:
        raw_data = f.read()
    
    # Парсим LAS файл
    parsed = read_las(raw_data)
    
    header = parsed.get('header')
    well_section = parsed.get('well', {})
    curves = parsed.get('curves', [])
    
    # Извлекаем WELL значение
    well_value = None
    if 'WELL' in well_section:
        well_value = well_section['WELL'].get('value')
    
    # Извлекаем STRT, STOP, STEP из секции WELL
    strt = well_section.get('STRT', {}).get('value') if 'STRT' in well_section else None
    stop = well_section.get('STOP', {}).get('value') if 'STOP' in well_section else None
    step = well_section.get('STEP', {}).get('value') if 'STEP' in well_section else None
    
    # Конвертируем путь в Windows-style с обратными слэшами
    file_path_windows = str(Path(file_path)).replace('/', '\\')
    
    # Для каждой кривой создаем отдельную запись
    for curve in curves:
        record = {
            'file_path': file_path_windows,
            'well': well_value,
            'strt': strt,
            'stop': stop,
            'step': step,
            'mnemonic': curve.mnemonic,
            'unit': curve.unit,
            'description': curve.description,
            'error': None
        }
        results.append(record)
    
    # Если кривых нет, все равно добавляем одну запись с информацией о файле
    if not curves:
        record = {
            'file_path': file_path_windows,
            'well': well_value,
            'strt': strt,
            'stop': stop,
            'step': step,
            'mnemonic': None,
            'unit': None,
            'description': None,
            'error': None
        }
        results.append(record)
    
    return results


def generate_catalog(directory_path: str, output_file: str) -> str:
    """
    Сканирует директорию и генерирует TSV файл с каталогом LAS файлов.
    
    Args:
        directory_path: Путь к корневой директории для сканирования
        output_file: Путь к выходному TSV файлу
        
    Returns:
        Путь к созданному файлу
    """
    # Получаем все данные
    all_records = scan_directory(directory_path)
    
    # Записываем в TSV формат (UTF-8, разделитель - табуляция)
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        # Заголовок
        headers = ['LAS', 'скважина', 'кривые', 'STRT', 'STOP', 'STEP', 
                   'МNEM', 'единицы измерения', 'комментарий', 'путь к файлу']
        f.write('\t'.join(headers) + '\n')
        
        # Данные
        for record in all_records:
            row = [
                '1' if record.get('mnemonic') else '0',  # Флаг наличия кривой
                str(record.get('well') or ''),
                str(record.get('mnemonic') or ''),
                str(record.get('strt') or ''),
                str(record.get('stop') or ''),
                str(record.get('step') or ''),
                str(record.get('mnemonic') or ''),
                str(record.get('unit') or ''),
                str(record.get('description') or ''),
                str(record.get('file_path') or '')
            ]
            f.write('\t'.join(row) + '\n')
    
    return output_file


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python catalog.py <directory_path> [output_file.tsv]")
        sys.exit(1)
    
    dir_path = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else 'las_catalog.tsv'
    
    result_file = generate_catalog(dir_path, output)
    print(f"Catalog generated: {result_file}")
    print(f"Total records: {len(scan_directory(dir_path))}")
