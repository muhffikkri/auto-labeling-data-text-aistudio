# tests/conftest.py

import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path

# Menambahkan path root project untuk import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture(scope="session")
def project_root():
    """Fixture untuk mendapatkan path root project"""
    return Path(__file__).parent.parent


@pytest.fixture(scope="function")
def temp_workspace(tmp_path):
    """Fixture untuk membuat workspace temporary yang terisolasi"""
    # Buat struktur folder yang diperlukan
    (tmp_path / "results").mkdir()
    (tmp_path / "dataset").mkdir()
    (tmp_path / "logs").mkdir()
    
    return tmp_path


@pytest.fixture(scope="function")
def sample_dataframe():
    """Fixture untuk mendapatkan sample DataFrame untuk testing"""
    import pandas as pd
    
    return pd.DataFrame({
        'id': [0, 1, 2],
        'tweet_text': [
            "Ini adalah tweet positif tentang universitas.",
            "Layanan di kampus ini sangat buruk.",
            "Pendaftaran dibuka besok."
        ],
        'label': [None, None, None],
        'justifikasi': [None, None, None]
    })


@pytest.fixture(scope="function")
def mock_config():
    """Fixture untuk mock konfigurasi testing"""
    return {
        'MODEL_NAME': 'gemini-test-model',
        'OUTPUT_DIR': 'test_results',
        'DATASET_DIR': 'test_dataset',
    }


@pytest.fixture(scope="function")
def mock_api_keys():
    """Fixture untuk mock API keys"""
    return ['TEST_KEY_1', 'TEST_KEY_2', 'TEST_KEY_3']


@pytest.fixture(autouse=True)
def cleanup_logging():
    """Fixture untuk membersihkan logging configuration setelah setiap test"""
    import logging
    
    yield
    
    # Reset logging handlers
    logger = logging.getLogger()
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Reset logging level
    logging.getLogger().setLevel(logging.WARNING)


def pytest_configure(config):
    """Konfigurasi pytest yang dijalankan sekali di awal"""
    # Menambahkan custom markers
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "api: mark test as requiring API access"
    )


def pytest_collection_modifyitems(config, items):
    """Modifikasi item collection untuk menambahkan markers otomatis"""
    for item in items:
        # Tambahkan marker berdasarkan path file
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Tambahkan marker slow untuk test yang mungkin lambat
        if "test_labeling_flow" in str(item.fspath):
            item.add_marker(pytest.mark.slow)