import os
import sys
from flask import Flask, request, jsonify, render_template

# Определяем директорию текущего скрипта (las_viewer)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Нам нужно подняться на уровень выше, чтобы попасть в папку 'test',
# где лежат соседние папки 'las_viewer' и 'las_memory'.
# Структура: C:\...\test\las_viewer\app.py
# Целевой путь для sys.path: C:\...\test
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# Проверяем, существует ли там папка las_memory
LAS_MEMORY_DIR = os.path.join(PROJECT_ROOT, 'las_memory')

if os.path.exists(LAS_MEMORY_DIR):
    # Добавляем РОДИТЕЛЬСКУЮ папку (test) в sys.path
    # Тогда Python сможет найти пакет 'las_memory' внутри неё
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    print(f"SUCCESS: Added to path: {PROJECT_ROOT}")
    print(f"SUCCESS: Found las_memory at: {LAS_MEMORY_DIR}")
else:
    print(f"ERROR: las_memory folder not found at {LAS_MEMORY_DIR}")
    print(f"Current BASE_DIR: {BASE_DIR}")
    print(f"Calculated PROJECT_ROOT: {PROJECT_ROOT}")
    sys.exit(1)

try:
    from las_memory import read_las
    print("SUCCESS: Module las_memory imported successfully.")
except ImportError as e:
    print(f"CRITICAL ERROR: Failed to import read_las: {e}")
    print(f"sys.path contains: {sys.path[:3]}...") # Показать первые 3 пути для отладки
    sys.exit(1)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не найден'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    
    if not file.filename.lower().endswith('.las'):
        return jsonify({'error': 'Пожалуйста, загрузите файл с расширением .las'}), 400
    
    try:
        # Читаем файл в память
        file_content = file.read()
        
        # Определяем кодировку автоматически (для русской поддержки)
        las_data = read_las(file_content, autodetect_encoding=True)
        
        # Извлекаем мета информацию
        metadata = {
            'well_name': las_data.well.get('WELL', 'Не указано'),
            'field': las_data.well.get('FLD', 'Не указано'),
            'location': las_data.well.get('LOC', 'Не указано'),
            'province': las_data.well.get('PROV', 'Не указано'),
            'county': las_data.well.get('CNTY', 'Не указано'),
            'state': las_data.well.get('ST', 'Не указано'),
            'country': las_data.well.get('CTRY', 'Не указано'),
            'service_company': las_data.well.get('SRVC', 'Не указано'),
            'date': las_data.well.get('DATE', 'Не указано'),
            'api': las_data.well.get('API', 'Не указано'),
            'run_number': las_data.well.get('RUN', 'Не указано'),
            'version': f"{las_data.version.VERS}.{las_data.version.WRAP}"
        }
        
        # Извлекаем данные кривых
        curves_data = []
        for curve in las_data.curves:
            curve_info = {
                'mnemonic': curve.mnemonic,
                'unit': curve.unit,
                'descr': curve.descr,
                'data': curve.data.tolist() if hasattr(curve.data, 'tolist') else list(curve.data)
            }
            curves_data.append(curve_info)
        
        # Формируем таблицу данных (первые 100 строк для производительности)
        table_data = []
        if len(las_data.curves) > 0:
            # Получаем длину данных (минимальная длина среди всех кривых)
            min_length = min(len(curve.data) for curve in las_data.curves if len(curve.data) > 0)
            max_rows = min(100, min_length)  # Ограничиваем 100 строками
            
            headers = [curve.mnemonic for curve in las_data.curves]
            
            for i in range(max_rows):
                row = {}
                for j, curve in enumerate(las_data.curves):
                    if len(curve.data) > i:
                        value = curve.data[i]
                        # Обрабатываем специальные значения
                        if hasattr(value, 'item'):
                            value = value.item()
                        row[headers[j]] = value
                    else:
                        row[headers[j]] = None
                table_data.append(row)
        
        return jsonify({
            'success': True,
            'metadata': metadata,
            'curves': curves_data,
            'table_headers': [curve.mnemonic for curve in las_data.curves],
            'table_data': table_data,
            'total_rows': min_length if len(las_data.curves) > 0 else 0,
            'displayed_rows': len(table_data)
        })
        
    except Exception as e:
        return jsonify({'error': f'Ошибка при обработке файла: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
