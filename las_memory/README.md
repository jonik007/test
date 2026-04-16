# las_memory

Библиотека для чтения LAS файлов из памяти. Аналог [lasio](https://github.com/kinverness1/lasio), но работает с данными в памяти (bytes, str, BytesIO, StringIO) без необходимости сохранения файла на диск.

## Особенности

- Чтение LAS файлов напрямую из байтов, строк или буферов
- API, совместимый с lasio
- Поддержка основных секций LAS: VERSION, WELL, CURVE, PARAM, OTHER
- Работа с данными через numpy массивы
- Опциональная интеграция с pandas для работы с DataFrame
- Запись результата обратно в строку или файл

## Установка

```bash
pip install numpy
```

Опционально для работы с DataFrame:
```bash
pip install pandas
```

## Быстрый старт

### Чтение из байтов

```python
from las_memory import read_las

# Чтение из байтов
with open('example.las', 'rb') as f:
    data = f.read()

las = read_las(data)
print(las)
```

### Чтение из строки

```python
from las_memory import read_las

las_string = """~VERSION INFORMATION
 VERS.                          2.0 :   CWLS LOG ASCII STANDARD - VERSION 2.0
~WELL INFORMATION
 WELL.                          WELL_NAME : Well Name
~CURVE INFORMATION
 DEPT.M                          : Depth
 GR  .GAPI                       : Gamma Ray
~A
  100.0  50.0
  101.0  55.0
  102.0  60.0
"""

las = read_las(las_string)
print(f"Скважина: {las.well.get('WELL')}")
print(f"Количество кривых: {len(las.curves)}")
```

### Чтение из BytesIO

```python
from io import BytesIO
from las_memory import read_las

with open('example.las', 'rb') as f:
    buffer = BytesIO(f.read())

las = read_las(buffer)
```

### Доступ к данным

```python
# Доступ к метаданным
print(f"Версия LAS: {las.version.get('VERS')}")
print(f"Название скважины: {las.well.get('WELL')}")

# Доступ к кривым по имени
gr_curve = las.curves['GR']
print(f"Gamma Ray: {gr_curve.mnemonic}, единицы: {gr_curve.unit}")
print(f"Данные: {gr_curve.data}")

# Доступ к данным как к numpy массиву
data = las.data  # 2D numpy array
print(f"Размер данных: {data.shape}")

# Доступ по индексу
depth_data = las.curves[0].data
gr_data = las.curves['GR'].data
```

### Интеграция с pandas

```python
# Конвертация в DataFrame (требуется pandas)
df = las.df
print(df.head())
print(df.columns)
```

### Запись в строку или файл

```python
# Получить LAS как строку
las_string = las.write()
print(las_string)

# Записать в файл
with open('output.las', 'w') as f:
    las.write(f)

# Записать в StringIO
from io import StringIO
buffer = StringIO()
las.write(buffer)
content = buffer.getvalue()
```

## API

### Основные функции

#### `read_las(source, encoding='utf-8', ignore_data_errors=False, **kwargs)`

Читает LAS файл из памяти.

**Параметры:**
- `source`: Источник данных. Может быть:
  - `str`: строка с содержимым LAS файла
  - `bytes`: байты с содержимым LAS файла
  - `StringIO`: текстовый буфер
  - `BytesIO`: байтовый буфер
- `encoding`: Кодировка для декодирования байтов (по умолчанию 'utf-8')
- `ignore_data_errors`: Игнорировать ошибки при парсинге данных
- `**kwargs`: Дополнительные аргументы (для совместимости с lasio)

**Возвращает:** `LasFile` объект

### Классы

#### `LasFile`

Представляет распарсенный LAS файл.

**Атрибуты:**
- `version`: Секция ~VERSION (Header)
- `well`: Секция ~WELL (Header)
- `curve`: Секция ~CURVE (Header)
- `param`: Секция ~PARAM (Header)
- `other`: Секция ~OTHER (строка)
- `curves`: Коллекция кривых (CurveCollection)

**Свойства:**
- `data`: numpy array со всеми данными кривых
- `df`: pandas DataFrame с данными (если установлен pandas)

**Методы:**
- `write(file_obj=None)`: Записывает LAS в файл или возвращает как строку

#### `Curve`

Представляет одну кривую из LAS файла.

**Атрибуты:**
- `mnemonic`: Идентификатор кривой (например, 'GR', 'DT')
- `unit`: Единицы измерения
- `value`: Значение параметра
- `descr`: Описание кривой
- `data`: numpy array с данными

#### `CurveCollection`

Коллекция кривых с удобным доступом.

**Методы доступа:**
- По индексу: `curves[0]`
- По имени: `curves['GR']`
- Свойство `mnemonics`: список всех имен кривых
- Свойство `data`: все данные как 2D numpy array

#### `Header`

Представляет секцию заголовка.

**Методы:**
- `get(key, default)`: Получение значения по мнемонике
- `keys()`, `values()`, `items()`: Итерация по элементам

## Примеры использования

### Фильтрация данных

```python
# Получить только определенные кривые
depth = las.curves['DEPT'].data
gr = las.curves['GR'].data

# Фильтрация по глубине
mask = (depth > 1000) & (depth < 2000)
filtered_gr = gr[mask]
```

### Статистика по кривым

```python
import numpy as np

for curve in las.curves:
    data = curve.data
    print(f"{curve.mnemonic}:")
    print(f"  Min: {np.nanmin(data):.2f}")
    print(f"  Max: {np.nanmax(data):.2f}")
    print(f"  Mean: {np.nanmean(data):.2f}")
```

### Обработка нескольких файлов из памяти

```python
from io import BytesIO

files_data = [...]  # Список байтов из разных источников

for file_bytes in files_data:
    las = read_las(file_bytes)
    print(f"{las.well.get('WELL')}: {len(las.curves)} кривых")
```

## Отличия от lasio

| Функция | lasio | las_memory |
|---------|-------|------------|
| Источник данных | Файл на диске | Память (bytes, str, buffer) |
| Чтение с диска | Да | Нет |
| API | Расширенный | Базовый, совместимый |
| Зависимости | numpy, pandas (опц.) | numpy, pandas (опц.) |

## Лицензия

MIT License
