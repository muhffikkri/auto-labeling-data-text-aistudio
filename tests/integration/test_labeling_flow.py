# tests/integration/test_labeling_flow.py

import os
import sys
import shutil
import pytest
import pandas as pd
import threading
from unittest.mock import patch, MagicMock
from pathlib import Path

# Menambahkan path root project untuk import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core_logic import process
from src.core_logic.env_manager import load_and_log_config


@pytest.fixture
def test_environment(tmp_path):
    """Fixture untuk menyiapkan lingkungan testing yang terisolasi"""
    # Setup test directories
    test_output_dir = tmp_path / "test_results"
    test_dataset_dir = tmp_path / "test_dataset" 
    test_logs_dir = tmp_path / "test_logs"
    
    test_output_dir.mkdir()
    test_dataset_dir.mkdir()
    test_logs_dir.mkdir()
    
    # Setup test data
    test_data = pd.DataFrame({
        'id': [0, 1, 2],
        'tweet_text': [
            "Ini adalah tweet positif tentang universitas.",
            "Layanan di kampus ini sangat buruk.",
            "Pendaftaran dibuka besok."
        ],
        'label': [None, None, None],
        'justifikasi': [None, None, None]
    })
    
    # Simpan test data
    test_csv_path = test_dataset_dir / "sample_data.csv"
    test_data.to_csv(test_csv_path, index=False)
    
    # Setup environment variables untuk testing
    test_config = {
        'MODEL_NAME': 'gemini-test-model',
        'OUTPUT_DIR': str(test_output_dir),
        'DATASET_DIR': str(test_dataset_dir),
    }
    test_api_keys = ['TEST_KEY_1', 'TEST_KEY_2']
    
    # Patch global variables
    with patch.object(process, 'CONFIG', test_config), \
         patch.object(process, 'API_KEYS', test_api_keys), \
         patch.object(process, 'current_key_index', 0), \
         patch.object(process, 'LOG_DIR', str(test_logs_dir)):
        
        yield {
            'config': test_config,
            'api_keys': test_api_keys,
            'test_data': test_data,
            'output_dir': test_output_dir,
            'dataset_dir': test_dataset_dir,
            'logs_dir': test_logs_dir,
            'tmp_path': tmp_path
        }


@pytest.fixture
def mock_genai():
    """Fixture untuk mock Gemini AI API"""
    with patch('src.core_logic.process.genai') as mock:
        yield mock


@pytest.fixture  
def stop_event():
    """Fixture untuk threading stop event"""
    return threading.Event()


class TestLabelDatasetHappyPath:
    """Test suite untuk alur normal label_dataset"""
    
    def test_label_dataset_complete_flow(self, test_environment, mock_genai, stop_event):
        """Test alur lengkap pelabelan dari awal sampai selesai"""
        
        # Setup mock response
        mock_response_data = [
            {'id': 0, 'label': 'POSITIF', 'justifikasi': 'Mengandung kata positif tentang universitas'},
            {'id': 1, 'label': 'NEGATIF', 'justifikasi': 'Mengeluh tentang layanan kampus'},
            {'id': 2, 'label': 'NETRAL', 'justifikasi': 'Informasi factual tentang pendaftaran'}
        ]
        
        with patch.object(process, 'generate_from_gemini', return_value=mock_response_data) as mock_generate, \
             patch.object(process, 'load_prompt_template', return_value="Test template {data_json}"):
            
            # Eksekusi
            df_master = test_environment['test_data'].copy()
            process.label_dataset(
                df_master=df_master,
                base_name='sample_data',
                batch_size=10,  # Lebih besar dari jumlah data untuk memproses semuanya sekaligus
                max_retry=3,
                generation_config={'temperature': 0.1},
                text_column_name='tweet_text',
                allowed_labels=['POSITIF', 'NEGATIF', 'NETRAL'],
                stop_event=stop_event
            )
            
            # Verifikasi bahwa generate_from_gemini dipanggil
            mock_generate.assert_called_once()
            
            # Verifikasi struktur output directory
            project_output_dir = test_environment['output_dir'] / 'sample_data'
            labeled_dir = project_output_dir / 'labeled'
            unlabeled_dir = project_output_dir / 'unlabeled'
            
            assert labeled_dir.exists()
            assert unlabeled_dir.exists()
            
            # Verifikasi file batch labeled dibuat
            labeled_files = list(labeled_dir.glob('*_labeled.xlsx'))
            assert len(labeled_files) == 1
            
            # Verifikasi isi file labeled
            labeled_df = pd.read_excel(labeled_files[0])
            assert len(labeled_df) == 3
            assert all(labeled_df['label'].notna())
            assert all(labeled_df['justifikasi'].notna())
            
            # Verifikasi isi sesuai dengan mock response
            for i, row in labeled_df.iterrows():
                expected = mock_response_data[i]
                assert row['label'] == expected['label']
                assert row['justifikasi'] == expected['justifikasi']
            
            # Verifikasi file final dibuat
            final_labeled_file = project_output_dir / 'sample_data_FULL_labeled.xlsx'
            assert final_labeled_file.exists()
            
            final_df = pd.read_excel(final_labeled_file)
            assert len(final_df) == 3
            assert all(final_df['label'].notna())
    
    def test_label_dataset_with_multiple_batches(self, test_environment, mock_genai, stop_event):
        """Test pelabelan dengan multiple batches"""
        
        # Setup data yang lebih besar
        large_data = pd.DataFrame({
            'id': list(range(5)),
            'tweet_text': [f"Tweet number {i}" for i in range(5)],
            'label': [None] * 5,
            'justifikasi': [None] * 5
        })
        
        # Mock response untuk setiap batch
        def mock_generate_side_effect(*args, **kwargs):
            # Return response sesuai dengan data yang dikirim
            # Asumsi: setiap batch berisi maksimal 2 item
            return [
                {'id': i, 'label': 'NETRAL', 'justifikasi': f'Justifikasi untuk tweet {i}'}
                for i in range(2)  # Simulasi batch size 2
            ]
        
        with patch.object(process, 'generate_from_gemini', side_effect=mock_generate_side_effect) as mock_generate, \
             patch.object(process, 'load_prompt_template', return_value="Test template {data_json}"):
            
            # Eksekusi dengan batch size kecil
            process.label_dataset(
                df_master=large_data,
                base_name='large_sample',
                batch_size=2,  # Batch size kecil untuk memaksa multiple batches
                max_retry=3,
                generation_config={'temperature': 0.1},
                text_column_name='tweet_text',
                allowed_labels=['POSITIF', 'NEGATIF', 'NETRAL'],
                stop_event=stop_event
            )
            
            # Verifikasi bahwa generate_from_gemini dipanggil beberapa kali
            assert mock_generate.call_count >= 2  # Minimal 2 batches untuk 5 items dengan batch size 2
            
            # Verifikasi file batch dibuat
            project_output_dir = test_environment['output_dir'] / 'large_sample'
            labeled_dir = project_output_dir / 'labeled'
            labeled_files = list(labeled_dir.glob('*_labeled.xlsx'))
            assert len(labeled_files) >= 2


class TestLabelDatasetResumeLogic:
    """Test suite untuk logika resume label_dataset"""
    
    def test_label_dataset_resume_partial_batch(self, test_environment, mock_genai, stop_event):
        """Test resume ketika batch sudah ada tetapi belum lengkap"""
        
        # Setup: buat file batch yang sudah ada dengan data sebagian
        project_output_dir = test_environment['output_dir'] / 'sample_data'
        labeled_dir = project_output_dir / 'labeled'
        labeled_dir.mkdir(parents=True, exist_ok=True)
        
        # Data batch yang sudah ada - hanya baris pertama yang terlabeli
        existing_batch_data = pd.DataFrame({
            'id': [0, 1, 2],
            'tweet_text': [
                "Ini adalah tweet positif tentang universitas.",
                "Layanan di kampus ini sangat buruk.",
                "Pendaftaran dibuka besok."
            ],
            'label': ['POSITIF', None, None],  # Hanya baris pertama terlabeli
            'justifikasi': ['Sudah dilabeli sebelumnya', None, None]
        })
        
        batch_file = labeled_dir / 'sample_data_batch001_003_labeled.xlsx'
        existing_batch_data.to_excel(batch_file, index=False)
        
        # Mock response hanya untuk baris yang belum terlabeli (id 1 dan 2)
        mock_response_data = [
            {'id': 1, 'label': 'NEGATIF', 'justifikasi': 'Keluhan tentang layanan'},
            {'id': 2, 'label': 'NETRAL', 'justifikasi': 'Informasi factual'}
        ]
        
        with patch.object(process, 'generate_from_gemini', return_value=mock_response_data) as mock_generate, \
             patch.object(process, 'load_prompt_template', return_value="Test template {data_json}"):
            
            # Eksekusi
            df_master = test_environment['test_data'].copy()
            process.label_dataset(
                df_master=df_master,
                base_name='sample_data',
                batch_size=10,
                max_retry=3,
                generation_config={'temperature': 0.1},
                text_column_name='tweet_text',
                allowed_labels=['POSITIF', 'NEGATIF', 'NETRAL'],
                stop_event=stop_event
            )
            
            # Verifikasi bahwa generate_from_gemini dipanggil dengan data yang benar
            mock_generate.assert_called_once()
            
            # Verifikasi argument yang dikirim ke generate_from_gemini
            call_args = mock_generate.call_args
            # Seharusnya hanya mengirim data untuk baris yang belum terlabeli
            
            # Verifikasi file hasil akhir
            updated_df = pd.read_excel(batch_file)
            
            # Semua baris seharusnya sekarang terlabeli
            assert all(updated_df['label'].notna())
            assert all(updated_df['justifikasi'].notna())
            
            # Data lama tidak berubah
            assert updated_df.loc[0, 'label'] == 'POSITIF'
            assert updated_df.loc[0, 'justifikasi'] == 'Sudah dilabeli sebelumnya'
            
            # Data baru sesuai mock response
            assert updated_df.loc[1, 'label'] == 'NEGATIF'
            assert updated_df.loc[2, 'label'] == 'NETRAL'
    
    def test_label_dataset_skip_completed_batch(self, test_environment, mock_genai, stop_event):
        """Test skip batch yang sudah sepenuhnya terlabeli"""
        
        # Setup: buat file batch yang sudah lengkap
        project_output_dir = test_environment['output_dir'] / 'sample_data'
        labeled_dir = project_output_dir / 'labeled'
        labeled_dir.mkdir(parents=True, exist_ok=True)
        
        # Data batch yang sudah lengkap
        complete_batch_data = pd.DataFrame({
            'id': [0, 1, 2],
            'tweet_text': [
                "Ini adalah tweet positif tentang universitas.",
                "Layanan di kampus ini sangat buruk.",
                "Pendaftaran dibuka besok."
            ],
            'label': ['POSITIF', 'NEGATIF', 'NETRAL'],  # Semua sudah terlabeli
            'justifikasi': ['Justifikasi 1', 'Justifikasi 2', 'Justifikasi 3']
        })
        
        batch_file = labeled_dir / 'sample_data_batch001_003_labeled.xlsx'
        complete_batch_data.to_excel(batch_file, index=False)
        
        with patch.object(process, 'generate_from_gemini') as mock_generate, \
             patch.object(process, 'load_prompt_template', return_value="Test template {data_json}"):
            
            # Eksekusi
            df_master = test_environment['test_data'].copy()
            process.label_dataset(
                df_master=df_master,
                base_name='sample_data',
                batch_size=10,
                max_retry=3,
                generation_config={'temperature': 0.1},
                text_column_name='tweet_text',
                allowed_labels=['POSITIF', 'NEGATIF', 'NETRAL'],
                stop_event=stop_event
            )
            
            # Verifikasi bahwa generate_from_gemini TIDAK dipanggil
            mock_generate.assert_not_called()
            
            # Verifikasi bahwa file tetap tidak berubah
            final_df = pd.read_excel(batch_file)
            pd.testing.assert_frame_equal(final_df, complete_batch_data)
    
    def test_label_dataset_skip_failed_batch(self, test_environment, mock_genai, stop_event):
        """Test skip batch yang sudah ditandai sebagai gagal (unlabeled)"""
        
        # Setup: buat file batch di folder unlabeled
        project_output_dir = test_environment['output_dir'] / 'sample_data'
        unlabeled_dir = project_output_dir / 'unlabeled'
        unlabeled_dir.mkdir(parents=True, exist_ok=True)
        
        # Data batch yang gagal
        failed_batch_data = test_environment['test_data'].copy()
        unlabeled_file = unlabeled_dir / 'sample_data_batch001_003_unlabeled.xlsx'
        failed_batch_data.to_excel(unlabeled_file, index=False)
        
        with patch.object(process, 'generate_from_gemini') as mock_generate, \
             patch.object(process, 'load_prompt_template', return_value="Test template {data_json}"):
            
            # Eksekusi
            df_master = test_environment['test_data'].copy()
            process.label_dataset(
                df_master=df_master,
                base_name='sample_data',
                batch_size=10,
                max_retry=3,
                generation_config={'temperature': 0.1},
                text_column_name='tweet_text',
                allowed_labels=['POSITIF', 'NEGATIF', 'NETRAL'],
                stop_event=stop_event
            )
            
            # Verifikasi bahwa generate_from_gemini TIDAK dipanggil
            mock_generate.assert_not_called()
            
            # Verifikasi bahwa tidak ada file labeled yang dibuat
            labeled_dir = project_output_dir / 'labeled'
            if labeled_dir.exists():
                labeled_files = list(labeled_dir.glob('*_labeled.xlsx'))
                assert len(labeled_files) == 0


class TestLabelDatasetErrorHandling:
    """Test suite untuk error handling dalam label_dataset"""
    
    def test_label_dataset_api_error_retry(self, test_environment, mock_genai, stop_event):
        """Test retry mechanism ketika terjadi API error"""
        
        # Setup mock yang gagal beberapa kali kemudian berhasil
        mock_response_data = [
            {'id': 0, 'label': 'POSITIF', 'justifikasi': 'Berhasil setelah retry'},
            {'id': 1, 'label': 'NEGATIF', 'justifikasi': 'Berhasil setelah retry'},
            {'id': 2, 'label': 'NETRAL', 'justifikasi': 'Berhasil setelah retry'}
        ]
        
        call_count = 0
        def mock_generate_with_error(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Gagal 2 kali pertama
                raise Exception("API quota exceeded")
            return mock_response_data  # Berhasil di percobaan ketiga
        
        with patch.object(process, 'generate_from_gemini', side_effect=mock_generate_with_error) as mock_generate, \
             patch.object(process, 'load_prompt_template', return_value="Test template {data_json}"), \
             patch.object(process, 'rotate_api_key') as mock_rotate:
            
            # Eksekusi
            df_master = test_environment['test_data'].copy()
            process.label_dataset(
                df_master=df_master,
                base_name='sample_data',
                batch_size=10,
                max_retry=5,  # Cukup untuk 3 percobaan
                generation_config={'temperature': 0.1},
                text_column_name='tweet_text',
                allowed_labels=['POSITIF', 'NEGATIF', 'NETRAL'],
                stop_event=stop_event
            )
            
            # Verifikasi bahwa function dipanggil 3 kali (2 gagal + 1 berhasil)
            assert mock_generate.call_count == 3
            
            # Verifikasi bahwa API key dirotasi (karena error quota)
            assert mock_rotate.called
            
            # Verifikasi hasil akhir tetap berhasil
            project_output_dir = test_environment['output_dir'] / 'sample_data'
            labeled_dir = project_output_dir / 'labeled'
            labeled_files = list(labeled_dir.glob('*_labeled.xlsx'))
            assert len(labeled_files) == 1
            
            labeled_df = pd.read_excel(labeled_files[0])
            assert all(labeled_df['label'].notna())
    
    def test_label_dataset_max_retry_exceeded(self, test_environment, mock_genai, stop_event):
        """Test ketika max retry terlampaui"""
        
        with patch.object(process, 'generate_from_gemini', side_effect=Exception("Persistent API error")) as mock_generate, \
             patch.object(process, 'load_prompt_template', return_value="Test template {data_json}"):
            
            # Eksekusi
            df_master = test_environment['test_data'].copy()
            process.label_dataset(
                df_master=df_master,
                base_name='sample_data',
                batch_size=10,
                max_retry=2,  # Retry terbatas
                generation_config={'temperature': 0.1},
                text_column_name='tweet_text',
                allowed_labels=['POSITIF', 'NEGATIF', 'NETRAL'],
                stop_event=stop_event
            )
            
            # Verifikasi bahwa function dipanggil sesuai max_retry
            assert mock_generate.call_count == 2
            
            # Verifikasi bahwa file tetap dibuat meskipun gagal (dengan data kosong)
            project_output_dir = test_environment['output_dir'] / 'sample_data'
            labeled_dir = project_output_dir / 'labeled'
            labeled_files = list(labeled_dir.glob('*_labeled.xlsx'))
            assert len(labeled_files) == 1
            
            # Data masih kosong karena gagal
            labeled_df = pd.read_excel(labeled_files[0])
            assert all(labeled_df['label'].isna())