import os
import sys
from flask import Flask, request, jsonify, render_template

# --- Настройка путей для импорта las_memory ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
LAS_MEMORY_DIR = os.path.join(PROJECT_ROOT, 'las_memory')

if os.path.exists(LAS_MEMORY_DIR):
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    print(f"SUCCESS: Added to path: {PROJECT_ROOT}")
    print(f"SUCCESS: Found las_memory at: {LAS_MEMORY_DIR}")
else:
    print(f"ERROR: las_memory folder not found at {LAS_MEMORY_DIR}")
    sys.exit(1)

try:
    from las_memory import read_las
    print("SUCCESS: Module las_memory imported successfully.")
except ImportError as e:
    print(f"CRITICAL ERROR: Failed to import read_las: {e}")
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
        # Читаем файл в память (байты)
        file_content = file.read()
        
        # Вызываем парсер (автодетект кодировки теперь внутри функции)
        result = read_las(file_content)
        
        # result - это словарь: {'header': HeaderObj, 'curve_names': [...], 'df': DataFrame, ...}
        header_obj = result['header']
        df = result.get('df')
        curve_names = result.get('curve_names', [])

        # --- Извлечение метаинформации ---
        # Доступ к данным через словари внутри объекта header (well, version)
        well_data = getattr(header_obj, 'well', {})
        version_data = getattr(header_obj, 'version', {})
        
        # Helper функция для безопасного получения значения
        def get_well_value(key, default='Не указано'):
            if key in well_data:
                val = well_data[key].get('value', '')
                return val if val else default
            return default

        metadata = {
            'well_name': get_well_value('WELL'),
            'field': get_well_value('FLD'),
            'location': get_well_value('LOC'),
            'province': get_well_value('PROV'),
            'county': get_well_value('CNTY'),
            'state': get_well_value('ST'),
            'country': get_well_value('CTRY'),
            'service_company': get_well_value('SRVC'),
            'date': get_well_value('DATE'),
            'api': get_well_value('API'),
            'run_number': get_well_value('RUN'),
            'version': f"{version_data.get('VERS', {}).get('value', '?')} / {version_data.get('WRAP', {}).get('value', '?')}"
        }
        
        # --- Формирование таблицы данных ---
        table_headers = curve_names
        table_data = []
        total_rows = 0
        
        if df is not None and not df.empty:
            total_rows = len(df)
            # Берем первые 100 строк для отображения
            display_df = df.head(100)
            
            # Преобразуем DataFrame в список словарей для JSON
            # replace NaN на None для корректной сериализации в JSON
            table_data = display_df.where(pd.notnull(display_df), None).to_dict(orient='records')
        else:
            # Если pandas не подключился или данных нет
            pass

        # --- Информация о кривых (для справки) ---
        curves_info = []
        if hasattr(header_obj, 'curves'):
            for curve in header_obj.curves:
                curves_info.append({
                    'mnemonic': curve.mnemonic,
                    'unit': curve.unit,
                    'descr': curve.description
                })

        return jsonify({
            'success': True,
            'metadata': metadata,
            'curves_info': curves_info,
            'table_headers': table_headers,
            'table_data': table_data,
            'total_rows': total_rows,
            'displayed_rows': len(table_data)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc() # Вывод полной ошибки в консоль сервера
        return jsonify({'error': f'Ошибка при обработке файла: {str(e)}'}), 500

if __name__ == '__main__':
    # Импорт pandas здесь, чтобы ошибка импорта не ломала старт приложения, 
    # но была видна при обработке
    try:
        import pandas as pd
    except ImportError:
        print("WARNING: pandas not installed. Table data will be limited.")
        
    app.run(debug=True, host='0.0.0.0', port=5001)