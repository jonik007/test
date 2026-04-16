# las_memory - Библиотека для чтения LAS файлов из памяти

Легковесная библиотека для работы с LAS (Log ASCII Standard) файлами напрямую из памяти, без необходимости записи на диск. Является упрощённой альтернативой `lasio`, оптимизированной для работы с данными в памяти.

## Возможности

- Чтение LAS файлов из:
  - Байтов (`bytes`)
  - Строки (`str`)
  - File-like объектов (`io.BytesIO`, `io.StringIO`)
- Поддержка версий LAS 1.2 и 2.0
- Парсинг всех стандартных секций (~Version, ~Well, ~Curves, ~Parameter, ~Other, ~ASCII)
- Экспорт данных обратно в LAS формат
- Интеграция с pandas (опционально)
- Гибкая настройка парсинга (регистр мнемоник, игнорирование данных и т.д.)

## Установка

Библиотека не требует установки - просто скопируйте файл `las_memory.py` в ваш проект.

Зависимости:
- `numpy` - обязательна
- `pandas` - опционально (для свойства `.df`)

## Примеры использования

### Чтение из байтов

```python
from las_memory import read_bytes

# Читаем файл как байты
with open('well.las', 'rb') as f:
    las_data = f.read()

# Парсим из памяти
las = read_bytes(las_data)

# Доступ к данным
print(f"Скважина: {las.well.WELL.value}")
depth = las.curves['DEPT'].data
gr = las.curves['GR'].data
```

### Чтение из строки

```python
from las_memory import read_string

las_string = """~VERSION
 VERS.  2.0
~WELL
 WELL.  TEST_WELL
~CURVE
 DEPT.M
 GR.GAPI
~ASCII
 1000  50.5
 1001  55.2
"""

las = read_string(las_string)
```

### Чтение из буфера

```python
import io
from las_memory import read_buffer

# Из BytesIO
buffer = io.BytesIO(las_data)
las = read_buffer(buffer)

# Из StringIO
buffer_str = io.StringIO(las_string)
las = read_buffer(buffer_str)
```

### Работа с данными

```python
from las_memory import LASFile

las = LASFile(las_data)

# Доступ к заголовкам
print(las.well.WELL.value)      # Имя скважины
print(las.well.COMP.value)      # Компания
print(las.version.VERS.value)   # Версия LAS

# Доступ к кривым
for curve in las.curves:
    print(f"{curve.mnemonic}: {curve.unit} - {len(curve)} точек")

# Получение конкретной кривой
depth_curve = las.get_curve('DEPT')
gr_curve = las.get_curve('GR')

# Данные как numpy массивы
depth = depth_curve.data  # numpy.ndarray
gr = gr_curve.data

# Данные как pandas DataFrame (если установлен pandas)
df = las.df
```

### Создание нового LAS файла

```python
import numpy as np
from las_memory import LASFile, HeaderItem

# Создаём пустой объект
las = LASFile(None)

# Заполняем заголовки
las.sections['Version']['VERS'] = HeaderItem('VERS', '', '2.0', 'LAS Version')
las.sections['Well']['WELL'] = HeaderItem('WELL', '', 'MY_WELL', 'Well Name')
las.sections['Well']['COMP'] = HeaderItem('COMP', '', 'MY_CORP', 'Company')

# Добавляем кривые
depth = np.array([1000, 1001, 1002, 1003])
gr = np.array([45.5, 50.2, 48.7, 52.1])

las.append_curve('DEPT', depth, 'M', 'Depth')
las.append_curve('GR', gr, 'GAPI', 'Gamma Ray')

# Сохраняем в файл
las.write('output.las')

# Или получаем как строку
las_string = las.write()
```

### Опции парсинга

```python
# Игнорировать данные (только заголовок)
las = LASFile(data, ignore_data=True)

# Регистр мнемоник: 'upper', 'lower', 'preserve'
las = LASFile(data, mnemonic_case='upper')  # по умолчанию

# Игнорировать ошибки заголовка
las = LASFile(data, ignore_header_errors=True)

# Комбинирование опций
las = LASFile(data, mnemonic_case='preserve', ignore_data=False)
```

## API Reference

### Классы

#### `LASFile(file_ref, **kwargs)`
Основной класс для представления LAS файла.

**Аргументы:**
- `file_ref`: bytes, str или file-like объект с содержимым LAS файла
- `ignore_header_errors` (bool): игнорировать ошибки заголовка
- `mnemonic_case` (str): 'upper', 'lower', 'preserve'
- `ignore_data` (bool): не читать данные секции
- `index_unit` (str): единицы индексной кривой ('m' или 'ft')

**Атрибуты:**
- `version`: секция версии
- `well`: секция скважины
- `curves_section`: секция кривых
- `params`: секция параметров
- `other`: секция Other
- `curves`: список объектов CurveItem
- `df`: pandas DataFrame с данными (если доступен pandas)

**Методы:**
- `read(file_ref, **kwargs)`: прочитать LAS из памяти
- `get_curve(mnemonic)`: получить кривую по имени
- `append_curve(mnemonic, data, unit, descr)`: добавить кривую
- `write(to=None)`: записать в файл или вернуть строку

#### `CurveItem`
Объект кривой.

**Атрибуты:**
- `mnemonic`: имя кривой
- `unit`: единицы измерения
- `descr`: описание
- `data`: numpy массив данных
- `values`: алиас для data

#### `HeaderItem`
Элемент заголовка.

**Атрибуты:**
- `mnemonic`: имя параметра
- `unit`: единицы
- `value`: значение
- `descr`: описание

### Функции

- `read(bytes_or_str, **kwargs)`: универсальная функция чтения
- `read_bytes(data, **kwargs)`: чтение из байтов
- `read_string(text, **kwargs)`: чтение из строки
- `read_buffer(buffer, **kwargs)`: чтение из file-like объекта

## Отличия от lasio

| Характеристика | lasio | las_memory |
|----------------|-------|------------|
| Источник данных | Файлы на диске, URL | Память (bytes, str, buffer) |
| Зависимости | Множество | Только numpy |
| Размер кода | Большой | Компактный |
| Скорость | Хорошая | Отличная (нет I/O) |
| Поддержка версий LAS | 1.2, 2.0, 3.0 (частично) | 1.2, 2.0 |
| Запись в файл | Да | Да (в файл или строку) |

## Лицензия

MIT License
