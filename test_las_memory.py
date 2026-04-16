"""Тесты для библиотеки las_memory - чтение LAS из памяти."""

import io
import numpy as np

# Импортируем нашу библиотеку
from las_memory import LASFile, read, read_bytes, read_string, read_buffer


def test_read_from_bytes():
    """Тест чтения из байтов."""
    print("=== Тест 1: Чтение из байтов ===")
    
    # Создаём тестовый LAS файл в памяти
    las_content = b"""~VERSION INFORMATION
 VERS.                  2.0 : CWLS log ASCII Standard -VERSION 2.0
 WRAP.                   NO : One line per depth step
~WELL INFORMATION
 STRT.M                1000 : START DEPTH
 STOP.M                1005 : STOP DEPTH
 STEP.M                   1 : STEP
 NULL.              -9999.25 : NULL VALUE
 COMP.      TEST_COMPANY : COMPANY
 WELL.        TEST_WELL : WELL
 UWI .        123456789 : UNIQUE WELL ID
~CURVE INFORMATION
 DEPT.M     : Depth
 GR  .GAPI  : Gamma Ray
 NPHI.V/V   : Neutron Porosity
~PARAMETER INFORMATION
~OTHER
 This is other section
~ASCII
 1000.0  50.5  0.15
 1001.0  55.2  0.18
 1002.0  60.1  0.20
 1003.0  58.7  0.17
 1004.0  52.3  0.16
 1005.0  48.9  0.14
"""
    
    # Читаем из байтов
    las = read_bytes(las_content)
    
    print(f"Файл: {las}")
    print(f"Скважина: {las.well.WELL.value}")
    print(f"Компания: {las.well.COMP.value}")
    print(f"UWI: {las.well.UWI.value}")
    print(f"Версия: {las.version.VERS.value}")
    
    # Проверяем кривые
    print(f"\nКоличество кривых: {len(las.curves)}")
    for curve in las.curves:
        print(f"  {curve.mnemonic}: {curve.unit} - {len(curve)} точек")
    
    # Проверяем данные
    dept_curve = las.get_curve('DEPT')
    gr_curve = las.get_curve('GR')
    
    print(f"\nГлубина: {dept_curve.data}")
    print(f"GR: {gr_curve.data}")
    
    assert len(las.curves) == 3, "Должно быть 3 кривых"
    assert las.well.WELL.value == 'TEST_WELL', "Неверное имя скважины"
    assert len(dept_curve.data) == 6, "Должно быть 6 точек"
    
    print("✓ Тест пройден!\n")


def test_read_from_string():
    """Тест чтения из строки."""
    print("=== Тест 2: Чтение из строки ===")
    
    las_content = """~VERSION INFORMATION
 VERS.                  2.0 : CWLS log ASCII Standard
~WELL INFORMATION
 WELL.        STRING_WELL : WELL NAME
~CURVE INFORMATION
 DEPT.M     : Depth
 SP  .MV    : Spontaneous Potential
~ASCII
 100.0  -50.0
 101.0  -52.5
 102.0  -48.3
"""
    
    las = read_string(las_content)
    
    print(f"Файл: {las}")
    print(f"Скважина: {las.well.WELL.value}")
    print(f"Кривые: {[c.mnemonic for c in las.curves]}")
    
    sp_curve = las.get_curve('SP')
    print(f"SP данные: {sp_curve.data}")
    
    assert las.well.WELL.value == 'STRING_WELL'
    assert len(sp_curve.data) == 3
    
    print("✓ Тест пройден!\n")


def test_read_from_buffer():
    """Тест чтения из file-like объекта."""
    print("=== Тест 3: Чтение из буфера ===")
    
    las_content = """~VERSION
 VERS.  2.0
~WELL
 WELL.  BUFFER_WELL
~CURVE
 DEPT.M
 DT  .US/M
~ASCII
 1000  200
 1001  210
 1002  205
"""
    
    # BytesIO
    buffer = io.BytesIO(las_content.encode('utf-8'))
    las = read_buffer(buffer)
    
    print(f"Файл: {las}")
    print(f"Скважина: {las.well.WELL.value}")
    
    # StringIO
    buffer_str = io.StringIO(las_content)
    las2 = read_buffer(buffer_str)
    
    print(f"Файл (StringIO): {las2}")
    
    assert las.well.WELL.value == 'BUFFER_WELL'
    
    print("✓ Тест пройден!\n")


def test_read_from_file_then_memory():
    """Тест чтения файла с диска в память."""
    print("=== Тест 4: Чтение файла с диска в память ===")
    
    # Читаем файл как байты
    with open('generated_curve.las', 'rb') as f:
        las_bytes = f.read()
    
    # Передаём в нашу библиотеку
    las = LASFile(las_bytes)
    
    print(f"Файл: {las}")
    print(f"Скважина: {las.well.WELL.value}")
    print(f"Компания: {las.well.COMP.value}")
    print(f"Количество кривых: {len(las.curves)}")
    
    for curve in las.curves:
        print(f"  {curve.mnemonic}: {len(curve)} точек, диапазон [{curve.data.min():.2f}, {curve.data.max():.2f}]")
    
    assert len(las.curves) == 2
    assert las.well.WELL.value == 'TEST_WELL'
    
    print("✓ Тест пройден!\n")


def test_write_to_string():
    """Тест записи в строку."""
    print("=== Тест 5: Запись в строку ===")
    
    # Создаём новый LAS объект
    las = LASFile(None)
    
    # Заполняем версию
    las.sections['Version']['VERS'] = HeaderItem('VERS', '', '2.0', 'LAS Version')
    las.sections['Version']['WRAP'] = HeaderItem('WRAP', '', 'NO', 'Wrap')
    
    # Заполняем well
    las.sections['Well']['WELL'] = HeaderItem('WELL', '', 'MEMORY_WELL', 'Well Name')
    las.sections['Well']['COMP'] = HeaderItem('COMP', '', 'TEST_CORP', 'Company')
    
    # Добавляем кривые
    depth = np.array([100, 101, 102, 103])
    gr = np.array([45.5, 50.2, 48.7, 52.1])
    
    las.append_curve('DEPT', depth, 'M', 'Depth')
    las.append_curve('GR', gr, 'GAPI', 'Gamma Ray')
    
    # Записываем в строку
    output = las.write()
    
    print("Сгенерированный LAS:")
    print(output[:500])
    print("...")
    
    # Проверяем что можем прочитать обратно
    las2 = LASFile(output)
    print(f"\nПрочитано обратно: {las2}")
    assert las2.well.WELL.value == 'MEMORY_WELL'
    
    print("✓ Тест пройден!\n")


def test_ignore_data():
    """Тест игнорирования данных (только заголовок)."""
    print("=== Тест 6: Только заголовок (ignore_data=True) ===")
    
    las_content = """~VERSION
 VERS.  2.0
~WELL
 WELL.  HEADER_ONLY
~CURVE
 DEPT.M
 GR  .GAPI
~ASCII
 1000  50
 1001  55
 1002  60
"""
    
    las = LASFile(las_content, ignore_data=True)
    
    print(f"Файл: {las}")
    print(f"Скважина: {las.well.WELL.value}")
    print(f"Количество кривых: {len(las.curves)}")
    
    assert las.well.WELL.value == 'HEADER_ONLY'
    assert len(las.curves) == 0  # Данные не читались
    
    print("✓ Тест пройден!\n")


def test_mnemonic_case():
    """Тест обработки регистра мнемоник."""
    print("=== Тест 7: Регистр мнемоник ===")
    
    las_content = """~VERSION
 VERS.  2.0
~WELL
 WELL.  CASE_TEST
~CURVE
 dept.M     : Depth
 gr  .GAPI  : Gamma Ray
 nphi.V/V   : Neutron
~ASCII
 100  50  0.15
 101  55  0.18
"""
    
    # По умолчанию upper
    las_upper = LASFile(las_content, mnemonic_case='upper')
    print(f"Upper: {[c.mnemonic for c in las_upper.curves]}")
    
    # Preserve
    las_preserve = LASFile(las_content, mnemonic_case='preserve')
    print(f"Preserve: {[c.mnemonic for c in las_preserve.curves]}")
    
    # Lower
    las_lower = LASFile(las_content, mnemonic_case='lower')
    print(f"Lower: {[c.mnemonic for c in las_lower.curves]}")
    
    assert all(c.mnemonic.isupper() for c in las_upper.curves)
    assert las_preserve.curves[0].mnemonic == 'dept'
    assert all(c.mnemonic.islower() for c in las_lower.curves)
    
    print("✓ Тест пройден!\n")


def test_df_property():
    """Тест свойства df (DataFrame)."""
    print("=== Тест 8: DataFrame (если pandas доступен) ===")
    
    las_content = """~VERSION
 VERS.  2.0
~WELL
 WELL.  DF_TEST
~CURVE
 DEPT.M
 GR  .GAPI
 SP  .MV
~ASCII
 100  50  -30
 101  55  -32
 102  60  -28
"""
    
    las = LASFile(las_content)
    
    try:
        df = las.df
        print(f"DataFrame:\n{df}")
        print(f"Columns: {list(df.columns)}")
        assert list(df.columns) == ['DEPT', 'GR', 'SP']
        print("✓ Тест пройден!\n")
    except ImportError:
        print("pandas не установлен, пропускаем тест\n")


# Import HeaderItem for test 5
from las_memory import HeaderItem


if __name__ == '__main__':
    print("Запуск тестов las_memory...\n")
    
    test_read_from_bytes()
    test_read_from_string()
    test_read_from_buffer()
    test_read_from_file_then_memory()
    test_write_to_string()
    test_ignore_data()
    test_mnemonic_case()
    test_df_property()
    
    print("=" * 50)
    print("Все тесты пройдены успешно! ✓")
