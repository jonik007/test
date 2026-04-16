"""
Тесты для библиотеки las_memory.
"""

import pytest
import numpy as np
from io import BytesIO, StringIO

from las_memory import read_las, LasFile, Curve
from las_memory.reader import LasParser


SAMPLE_LAS = """~VERSION INFORMATION
 VERS.                          2.0 :   CWLS LOG ASCII STANDARD - VERSION 2.0
 WRAP.                           NO :   ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M                          100 : START DEPTH
 STOP.M                          150 : STOP DEPTH
 STEP.M                            1 : STEP
 NULL.                         -999 : NULL VALUE
 WELL.                       TEST_WELL : Well Name
 COMP.                      COMPANY_X : Company
 DATE.                        2024-01 : Date
~CURVE INFORMATION
 DEPT.M                          : Depth
 GR  .GAPI                       : Gamma Ray
 DT  .US/F                       : Delta Time
 NPHI.V/V                        : Neutron Porosity
~PARAMETER INFORMATION
 BHT.DEGC                         35 : Bottom Hole Temperature
 BS.MM                            85 : Bit Size
~OTHER
 This is additional information
 about the well log.
~A
 100.0  50.0  200.0  0.25
 101.0  55.0  195.0  0.26
 102.0  60.0  190.0  0.27
 103.0  65.0  185.0  0.28
 104.0  70.0  180.0  0.29
"""


class TestReadLas:
    """Тесты функции read_las."""
    
    def test_read_from_string(self):
        """Чтение из строки."""
        las = read_las(SAMPLE_LAS)
        assert isinstance(las, LasFile)
        assert len(las.curves) == 4
    
    def test_read_from_bytes(self):
        """Чтение из байтов."""
        las = read_las(SAMPLE_LAS.encode('utf-8'))
        assert isinstance(las, LasFile)
        assert las.well.get('WELL') == 'TEST_WELL'
    
    def test_read_from_bytesio(self):
        """Чтение из BytesIO."""
        buffer = BytesIO(SAMPLE_LAS.encode('utf-8'))
        las = read_las(buffer)
        assert isinstance(las, LasFile)
        assert len(las.curves) == 4
    
    def test_read_from_stringio(self):
        """Чтение из StringIO."""
        buffer = StringIO(SAMPLE_LAS)
        las = read_las(buffer)
        assert isinstance(las, LasFile)
        assert las.well.get('WELL') == 'TEST_WELL'
    
    def test_unsupported_type(self):
        """Ошибка при неподдерживаемом типе."""
        with pytest.raises(TypeError):
            read_las(12345)


class TestLasFile:
    """Тесты класса LasFile."""
    
    @pytest.fixture
    def las(self):
        return read_las(SAMPLE_LAS)
    
    def test_well_section(self, las):
        """Тест секции WELL."""
        assert las.well.get('WELL') == 'TEST_WELL'
        assert las.well.get('COMP') == 'COMPANY_X'
        assert las.well.get('STRT') == '100'
        assert las.well.get('STOP') == '150'
    
    def test_version_section(self, las):
        """Тест секции VERSION."""
        assert las.version.get('VERS') == '2.0'
        assert las.version.get('WRAP') == 'NO'
    
    def test_curve_section(self, las):
        """Тест секции CURVE."""
        assert len(las.curve) == 4
        assert las.curve[0].mnemonic == 'DEPT'
        assert las.curve[0].unit == 'M'
        assert las.curve[1].mnemonic == 'GR'
        assert las.curve[1].unit == 'GAPI'
    
    def test_param_section(self, las):
        """Тест секции PARAM."""
        assert las.param.get('BHT') == '35'
        assert las.param.get('BS') == '85'
    
    def test_other_section(self, las):
        """Тест секции OTHER."""
        assert 'additional information' in las.other
    
    def test_curves_data(self, las):
        """Тест данных кривых."""
        assert len(las.curves) == 4
        
        depth = las.curves['DEPT']
        assert depth.mnemonic == 'DEPT'
        assert depth.unit == 'M'
        assert len(depth.data) == 5
        assert np.isclose(depth.data[0], 100.0)
        assert np.isclose(depth.data[-1], 104.0)
        
        gr = las.curves['GR']
        assert gr.mnemonic == 'GR'
        assert gr.unit == 'GAPI'
        assert len(gr.data) == 5
        assert np.isclose(gr.data[0], 50.0)
    
    def test_curve_access_by_index(self, las):
        """Доступ к кривым по индексу."""
        assert las.curves[0].mnemonic == 'DEPT'
        assert las.curves[1].mnemonic == 'GR'
        assert las.curves[2].mnemonic == 'DT'
        assert las.curves[3].mnemonic == 'NPHI'
    
    def test_curve_access_by_name(self, las):
        """Доступ к кривым по имени."""
        assert las.curves['DEPT'].mnemonic == 'DEPT'
        assert las.curves['GR'].mnemonic == 'GR'
        assert las.curves['dt'].mnemonic == 'DT'  # Регистронезависимый
    
    def test_curve_not_found(self, las):
        """Ошибка при отсутствии кривой."""
        with pytest.raises(KeyError):
            las.curves['NONEXISTENT']
    
    def test_data_property(self, las):
        """Тест свойства data."""
        data = las.data
        assert isinstance(data, np.ndarray)
        assert data.shape == (5, 4)  # 5 точек, 4 кривые
        assert np.isclose(data[0, 0], 100.0)  # DEPT
        assert np.isclose(data[0, 1], 50.0)   # GR
    
    def test_repr(self, las):
        """Тест строкового представления."""
        repr_str = repr(las)
        assert 'TEST_WELL' in repr_str
        assert '4 curves' in repr_str


class TestCurveCollection:
    """Тесты CurveCollection."""
    
    def test_mnemonics_property(self):
        """Тест свойства mnemonics."""
        las = read_las(SAMPLE_LAS)
        mnemonics = las.curves.mnemonics
        assert mnemonics == ['DEPT', 'GR', 'DT', 'NPHI']
    
    def test_iteration(self):
        """Тест итерации."""
        las = read_las(SAMPLE_LAS)
        count = 0
        for curve in las.curves:
            assert isinstance(curve, Curve)
            count += 1
        assert count == 4
    
    def test_len(self):
        """Тест длины."""
        las = read_las(SAMPLE_LAS)
        assert len(las.curves) == 4


class TestWrite:
    """Тесты записи LAS."""
    
    def test_write_to_string(self):
        """Запись в строку."""
        las = read_las(SAMPLE_LAS)
        output = las.write()
        assert isinstance(output, str)
        assert '~VERSION' in output
        assert '~WELL' in output
        assert '~CURVE' in output
        assert '~A' in output
        assert 'TEST_WELL' in output
    
    def test_write_and_read_back(self):
        """Запись и повторное чтение."""
        las1 = read_las(SAMPLE_LAS)
        output = las1.write()
        las2 = read_las(output)
        
        assert las2.well.get('WELL') == las1.well.get('WELL')
        assert len(las2.curves) == len(las1.curves)
        assert np.allclose(las2.data, las1.data, equal_nan=True)


class TestEdgeCases:
    """Тесты граничных случаев."""
    
    def test_empty_curves(self):
        """Файл без данных."""
        las_empty = """~VERSION INFORMATION
 VERS.                          2.0
~WELL INFORMATION
 WELL.                          TEST
~CURVE INFORMATION
 DEPT.M                          : Depth
~A
"""
        las = read_las(las_empty)
        assert isinstance(las, LasFile)
        assert las.well.get('WELL') == 'TEST'
    
    def test_null_values(self):
        """Обработка null значений."""
        las_with_nulls = """~VERSION INFORMATION
 VERS.                          2.0
~WELL INFORMATION
 WELL.                          TEST
~CURVE INFORMATION
 DEPT.M                          : Depth
 GR  .GAPI                       : Gamma Ray
~A
 100.0  50.0
 101.0  -999.25
 102.0  60.0
"""
        las = read_las(las_with_nulls)
        gr_data = las.curves['GR'].data
        # Null значения должны быть обработаны
        assert len(gr_data) == 3


class TestPandasIntegration:
    """Тесты интеграции с pandas."""
    
    def test_df_property(self):
        """Тест свойства df."""
        try:
            import pandas as pd
        except ImportError:
            pytest.skip("pandas не установлен")
        
        las = read_las(SAMPLE_LAS)
        df = las.df
        
        assert df is not None
        assert len(df) == 5
        assert list(df.columns) == ['DEPT', 'GR', 'DT', 'NPHI']
        assert np.isclose(df['DEPT'].iloc[0], 100.0)
        assert np.isclose(df['GR'].iloc[0], 50.0)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
