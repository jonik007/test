import os
import sys

# Определяем базовую директорию проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Поднимаемся на уровень выше, чтобы найти соседнюю папку las_memory (так как они лежат рядом в корне репо)
PROJECT_ROOT = os.path.dirname(BASE_DIR)
LAS_MEMORY_PATH = os.path.join(PROJECT_ROOT, 'las_memory')

if os.path.exists(LAS_MEMORY_PATH):
    sys.path.insert(0, LAS_MEMORY_PATH)

try:
    from las_memory import read_las
except ImportError:
    # Фоллбэк: если las_memory установлен как пакет в environment
    try:
        from las_memory import read_las
    except ImportError:
        print("Ошибка: Модуль las_memory не найден. Убедитесь, что папка las_memory находится рядом с las_viewer в корне репозитория или установлена через pip.")
        raise
# Добавляем путь к библиотеке las_memory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'las_memory'))
# Добавляем родительскую директорию в путь, чтобы найти las_memory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from flask import Flask, request, jsonify, render_template
from las_memory import read_las

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
