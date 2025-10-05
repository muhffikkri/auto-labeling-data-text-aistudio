# tests/unit/test_process_utils.py

import os
import sys
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

# Menambahkan path root project untuk import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core_logic import process


class TestRotateApiKey:
    """Test suite untuk fungsi rotate_api_key"""
    
    def test_rotate_api_key_single_rotation(self):
        """Test rotasi API key dari index 0 ke 1"""
        with patch.object(process, 'API_KEYS', ['KEY1', 'KEY2']), \
             patch.object(process, 'current_key_index', 0), \
             patch('src.core_logic.process.genai') as mock_genai:
            
            # Eksekusi
            process.rotate_api_key()
            
            # Verifikasi
            assert process.current_key_index == 1
            mock_genai.configure.assert_called_once_with(api_key='KEY2')
    
    def test_rotate_api_key_wrap_around(self):
        """Test rotasi API key yang kembali ke index 0 setelah mencapai akhir"""
        with patch.object(process, 'API_KEYS', ['KEY1', 'KEY2']), \
             patch.object(process, 'current_key_index', 1), \
             patch('src.core_logic.process.genai') as mock_genai:
            
            # Eksekusi
            process.rotate_api_key()
            
            # Verifikasi
            assert process.current_key_index == 0
            mock_genai.configure.assert_called_once_with(api_key='KEY1')
    
    def test_rotate_api_key_multiple_rotations(self):
        """Test beberapa kali rotasi API key"""
        with patch.object(process, 'API_KEYS', ['KEY1', 'KEY2', 'KEY3']), \
             patch.object(process, 'current_key_index', 0), \
             patch('src.core_logic.process.genai') as mock_genai:
            
            # Rotasi pertama: 0 -> 1
            process.rotate_api_key()
            assert process.current_key_index == 1
            
            # Rotasi kedua: 1 -> 2
            process.rotate_api_key()
            assert process.current_key_index == 2
            
            # Rotasi ketiga: 2 -> 0 (wrap around)
            process.rotate_api_key()
            assert process.current_key_index == 0
            
            # Verifikasi bahwa genai.configure dipanggil 3 kali
            assert mock_genai.configure.call_count == 3


class TestOpenDataset:
    """Test suite untuk fungsi open_dataset"""
    
    def test_open_dataset_csv_success(self):
        """Test berhasil membuka file CSV"""
        # Setup
        test_dir = os.path.join(os.path.dirname(__file__), '..', 'test_dataset')
        
        # Eksekusi
        df, file_path = process.open_dataset(test_dir, 'sample_data')
        
        # Verifikasi
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3  # Sesuai dengan sample_data.csv
        assert 'tweet_text' in df.columns
        assert file_path.endswith('sample_data.csv')
        
        # Verifikasi isi data
        expected_texts = [
            "Ini adalah tweet positif tentang universitas.",
            "Layanan di kampus ini sangat buruk.",
            "Pendaftaran dibuka besok."
        ]
        actual_texts = df['tweet_text'].tolist()
        assert actual_texts == expected_texts
    
    def test_open_dataset_xlsx_priority(self, tmp_path):
        """Test prioritas CSV over XLSX ketika keduanya ada"""
        # Setup - buat file CSV dan XLSX dengan konten berbeda
        csv_file = tmp_path / "test_priority.csv"
        xlsx_file = tmp_path / "test_priority.xlsx"
        
        # CSV dengan konten khusus
        csv_content = pd.DataFrame({'text': ['CSV content']})
        csv_content.to_csv(csv_file, index=False)
        
        # XLSX dengan konten berbeda
        xlsx_content = pd.DataFrame({'text': ['XLSX content']})
        xlsx_content.to_excel(xlsx_file, index=False)
        
        # Eksekusi
        df, file_path = process.open_dataset(str(tmp_path), 'test_priority')
        
        # Verifikasi bahwa CSV diprioritaskan
        assert df['text'].iloc[0] == 'CSV content'
        assert file_path.endswith('.csv')
    
    def test_open_dataset_file_not_found(self):
        """Test error ketika file tidak ditemukan"""
        test_dir = os.path.join(os.path.dirname(__file__), '..', 'test_dataset')
        
        # Eksekusi & Verifikasi
        with pytest.raises(FileNotFoundError) as exc_info:
            process.open_dataset(test_dir, 'nonexistent_file')
        
        assert "Dataset tidak ditemukan" in str(exc_info.value)
    
    def test_open_dataset_invalid_directory(self):
        """Test error ketika direktori tidak ada"""
        # Eksekusi & Verifikasi
        with pytest.raises(Exception):
            process.open_dataset('/nonexistent/directory', 'sample_data')


class TestLoadPromptTemplate:
    """Test suite untuk fungsi load_prompt_template"""
    
    def test_load_prompt_template_default_file(self, tmp_path):
        """Test memuat template dari file default"""
        # Setup
        template_content = "Test prompt template dengan {data_json}"
        template_file = tmp_path / "prompt_template.txt"
        template_file.write_text(template_content, encoding='utf-8')
        
        # Ubah working directory sementara
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            # Eksekusi
            result = process.load_prompt_template()
            
            # Verifikasi
            assert result == template_content
        finally:
            # Restore working directory
            os.chdir(original_cwd)
    
    def test_load_prompt_template_custom_file(self, tmp_path):
        """Test memuat template dari file custom"""
        # Setup
        template_content = "Custom template with {data_json} placeholder"
        template_file = tmp_path / "custom_template.txt"
        template_file.write_text(template_content, encoding='utf-8')
        
        # Eksekusi
        result = process.load_prompt_template(str(template_file))
        
        # Verifikasi
        assert result == template_content
    
    def test_load_prompt_template_file_not_found(self):
        """Test error ketika file template tidak ditemukan"""
        # Eksekusi & Verifikasi
        with pytest.raises(FileNotFoundError) as exc_info:
            process.load_prompt_template('nonexistent_template.txt')
        
        assert "tidak ditemukan" in str(exc_info.value)


class TestSetupLogging:
    """Test suite untuk fungsi setup_logging"""
    
    def test_setup_logging_creates_log_directory(self, tmp_path):
        """Test bahwa setup_logging membuat direktori log"""
        # Setup
        original_log_dir = process.LOG_DIR
        test_log_dir = str(tmp_path / "test_logs")
        
        with patch.object(process, 'LOG_DIR', test_log_dir):
            # Eksekusi
            process.setup_logging()
            
            # Verifikasi
            assert os.path.exists(test_log_dir)
    
    def test_setup_logging_configures_handlers(self, tmp_path):
        """Test bahwa setup_logging mengonfigurasi logging handlers"""
        import logging
        
        # Setup
        original_log_dir = process.LOG_DIR
        test_log_dir = str(tmp_path / "test_logs")
        
        with patch.object(process, 'LOG_DIR', test_log_dir):
            # Eksekusi
            process.setup_logging()
            
            # Verifikasi bahwa log file dibuat
            log_files = [f for f in os.listdir(test_log_dir) if f.startswith('labeling_') and f.endswith('.log')]
            assert len(log_files) > 0
            
            # Verifikasi bahwa logger memiliki handlers
            logger = logging.getLogger()
            assert len(logger.handlers) >= 2  # FileHandler dan StreamHandler