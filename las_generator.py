import lasio
import numpy as np

# Создаём новый объект LASFile
las = lasio.LASFile()

# Устанавливаем версию LAS
las.version.VERS.value = 2.0
las.version.WRAP.value = 'NO'  # без переноса строк

# Добавляем заголовки (опционально, но рекомендуется)
las.well.WELL.value = 'TEST_WELL'
las.well.UWI.value = '123456789'
las.well.COMP.value = 'PYTHON_GENERATOR'
las.well.DATE.value = '2025-04-05'

# Определяем кривые
# DEPT — глубина (обязательная кривая в LAS)
depth = np.linspace(1000.0, 1009.0, 10)  # 10 точек от 1000 до 1009 метров
gr = np.random.uniform(20, 150, size=10)  # случайные значения GR

# Добавляем кривую глубины
las.append_curve('DEPT', depth, unit='M', descr='Depth')

# Добавляем кривую GR
las.append_curve('GR', gr, unit='GAPI', descr='Gamma Ray')

# Сохраняем в файл
output_file = 'generated_curve.las'
las.write(output_file, version=2.0)

print(f"LAS файл версии 2.0 успешно создан: {output_file}")