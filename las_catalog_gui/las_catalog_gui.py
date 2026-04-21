"""
GUI-каталогизатор LAS-файлов на основе Tkinter.
Позволяет выбрать каталог, рекурсивно найти все *.LAS файлы,
и отобразить информацию о скважинах и кривых в таблице.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

# Импорт функционала из las_memory
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from las_memory import LasMemory
except ImportError:
    messagebox.showerror("Ошибка", "Модуль las_memory не найден!")
    sys.exit(1)


class LasCatalogGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LAS Catalog Viewer")
        self.root.geometry("1200x600")
        
        # Фрейм для кнопок
        self.button_frame = ttk.Frame(root)
        self.button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.select_btn = ttk.Button(
            self.button_frame, 
            text="Выбрать каталог", 
            command=self.select_directory
        )
        self.select_btn.pack(side=tk.LEFT, padx=5)
        
        self.export_btn = ttk.Button(
            self.button_frame,
            text="Экспорт в TSV",
            command=self.export_to_tsv,
            state=tk.DISABLED
        )
        self.export_btn.pack(side=tk.LEFT, padx=5)
        
        self.status_label = ttk.Label(self.button_frame, text="")
        self.status_label.pack(side=tk.RIGHT, padx=5)
        
        # Таблица данных
        self.tree_frame = ttk.Frame(root)
        self.tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Определение колонок
        columns = (
            "file_path", "well", "fld", "strt", "stop", "step",
            "mnem", "unit", "descr"
        )
        
        self.tree = ttk.Treeview(
            self.tree_frame, 
            columns=columns, 
            show="headings",
            selectmode="browse"
        )
        
        # Настройка заголовков
        self.tree.heading("file_path", text="Путь к файлу")
        self.tree.heading("well", text="WELL")
        self.tree.heading("fld", text="FLD")
        self.tree.heading("strt", text="STRT")
        self.tree.heading("stop", text="STOP")
        self.tree.heading("step", text="STEP")
        self.tree.heading("mnem", text="MNEM (кривая)")
        self.tree.heading("unit", text="Ед. изм.")
        self.tree.heading("descr", text="Комментарий")
        
        # Настройка ширины колонок
        self.tree.column("file_path", width=200)
        self.tree.column("well", width=100)
        self.tree.column("fld", width=80)
        self.tree.column("strt", width=80)
        self.tree.column("stop", width=80)
        self.tree.column("step", width=80)
        self.tree.column("mnem", width=100)
        self.tree.column("unit", width=80)
        self.tree.column("descr", width=200)
        
        # Скроллбары
        self.vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.hsb = ttk.Scrollbar(self.tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)
        
        # Размещение элементов
        self.tree.grid(row=0, column=0, sticky='nsew')
        self.vsb.grid(row=0, column=1, sticky='ns')
        self.hsb.grid(row=1, column=0, sticky='ew')
        
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)
        
        # Хранилище данных
        self.catalog_data = []
        self.current_directory = None
    
    def select_directory(self):
        """Открыть диалог выбора каталога"""
        directory = filedialog.askdirectory(title="Выберите каталог с LAS-файлами")
        if directory:
            self.current_directory = directory
            self.status_label.config(text=f"Сканирование: {directory}")
            self.root.update()
            self.scan_directory(directory)
    
    def scan_directory(self, directory):
        """Рекурсивное сканирование каталога на наличие LAS-файлов"""
        self.catalog_data = []
        las_files = []
        
        # Поиск всех .LAS файлов
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.las'):
                    las_files.append(os.path.join(root, file))
        
        if not las_files:
            messagebox.showinfo("Информация", "LAS-файлы не найдены в выбранном каталоге")
            self.status_label.config(text="Файлы не найдены")
            return
        
        self.status_label.config(text=f"Найдено файлов: {len(las_files)}. Обработка...")
        self.root.update()
        
        # Обработка каждого файла
        processed_count = 0
        for las_path in las_files:
            try:
                las = LasMemory()
                las.read_from_file(las_path)
                
                # Получение информации о скважине
                well = las.get_header_value('WELL', '')
                fld = las.get_header_value('FLD', '')
                strt = las.get_header_value('STRT', '')
                stop = las.get_header_value('STOP', '')
                step = las.get_header_value('STEP', '')
                
                # Получение информации о кривых
                curves = las.get_curves_info()
                
                for curve in curves:
                    mnem = curve.get('MNEM', '')
                    unit = curve.get('UNIT', '')
                    descr = curve.get('DESCR', '')
                    
                    # Нормализация пути (замена / на \ для Windows)
                    normalized_path = las_path.replace('/', '\\')
                    
                    self.catalog_data.append({
                        'file_path': normalized_path,
                        'well': well,
                        'fld': fld,
                        'strt': strt,
                        'stop': stop,
                        'step': step,
                        'mnem': mnem,
                        'unit': unit,
                        'descr': descr
                    })
                
                processed_count += 1
                if processed_count % 10 == 0:
                    self.status_label.config(text=f"Обработано: {processed_count}/{len(las_files)}")
                    self.root.update()
                    
            except Exception as e:
                print(f"Ошибка при обработке файла {las_path}: {e}")
                continue
        
        self.display_data()
        self.status_label.config(text=f"Готово. Загружено записей: {len(self.catalog_data)}")
        self.export_btn.config(state=tk.NORMAL)
    
    def display_data(self):
        """Отображение данных в таблице"""
        # Очистка таблицы
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Добавление данных
        for row in self.catalog_data:
            self.tree.insert('', tk.END, values=(
                row['file_path'],
                row['well'],
                row['fld'],
                row['strt'],
                row['stop'],
                row['step'],
                row['mnem'],
                row['unit'],
                row['descr']
            ))
    
    def export_to_tsv(self):
        """Экспорт данных в TSV-файл"""
        if not self.catalog_data:
            messagebox.showwarning("Предупреждение", "Нет данных для экспорта")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".tsv",
            filetypes=[("TSV files", "*.tsv"), ("All files", "*.*")],
            title="Сохранить как TSV"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    # Заголовок
                    headers = ['file_path', 'well', 'fld', 'strt', 'stop', 'step', 'mnem', 'unit', 'descr']
                    f.write('\t'.join(headers) + '\n')
                    
                    # Данные
                    for row in self.catalog_data:
                        values = [str(row[h]) for h in headers]
                        f.write('\t'.join(values) + '\n')
                
                messagebox.showinfo("Успех", f"Данные успешно экспортированы в {file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")


def main():
    root = tk.Tk()
    app = LasCatalogGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
