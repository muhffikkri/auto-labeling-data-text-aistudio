# src/core_logic/env_manager.py

import os
import logging
from dotenv import load_dotenv, set_key, find_dotenv
from typing import Dict, List, Tuple

def load_env_variables() -> Tuple[Dict[str, str], List[str]]:
    """
    Memuat variabel konfigurasi dan API keys dari file .env.

    Returns:
        Tuple[Dict[str, str], List[str]]: 
        Sebuah tuple berisi:
        - Dictionary untuk setting umum (MODEL_NAME, dll.)
        - List berisi API keys.
    """
    load_dotenv()
    
    # Load model fallback list
    model_fallback_str = os.getenv("MODEL_FALLBACK_LIST", "")
    if model_fallback_str:
        # Parse comma-separated string menjadi list, hapus whitespace
        model_list = [model.strip() for model in model_fallback_str.split(",") if model.strip()]
    else:
        # Default fallback list jika tidak ada di .env
        model_list = ["gemini-1.5-pro-latest", "gemini-1.5-flash-latest"]
    
    settings = {
        "MODEL_NAME": os.getenv("MODEL_NAME", model_list[0]),  # Default ke model pertama dalam list
        "OUTPUT_DIR": os.getenv("OUTPUT_DIR", "results"),
        "DATASET_DIR": os.getenv("DATASET_DIR", "dataset"),
        "MODEL_LIST": model_list,  # Tambahkan model fallback list
    }
    
    api_keys = []
    i = 1
    while True:
        key = os.getenv(f"GOOGLE_API_KEY_{i}")
        if key:
            api_keys.append(key)
            i += 1
        else:
            break
            
    return settings, api_keys

def save_env_variables(settings: Dict[str, str], api_keys: List[str]):
    """
    Menyimpan settings dan API keys ke dalam file .env.
    Akan membuat file .env jika belum ada.
    """
    env_file = find_dotenv()
    if not env_file:
        # Jika .env tidak ada, buat file kosong
        with open(".env", "w") as f:
            pass
        env_file = find_dotenv()

    # Menyimpan settings umum
    for key, value in settings.items():
        set_key(env_file, key, value)
        
    # Menghapus key lama sebelum menulis yang baru untuk menghindari sisa
    # (Ini adalah pendekatan sederhana, library dotenv tidak punya fungsi 'unset')
    # Kita akan baca semua, hapus yang GOOGLE_API_KEY, lalu tulis ulang
    with open(env_file, 'r') as f:
        lines = f.readlines()
    with open(env_file, 'w') as f:
        for line in lines:
            if not line.strip().startswith('GOOGLE_API_KEY_'):
                f.write(line)

    # Menulis API keys yang baru
    for i, key_value in enumerate(api_keys, 1):
        if key_value.strip(): # Hanya simpan jika tidak kosong
            set_key(env_file, f"GOOGLE_API_KEY_{i}", key_value)

def load_and_log_config() -> Tuple[Dict[str, str], List[str]]:
    """
    Memuat variabel konfigurasi dan API keys, lalu mencatatnya ke log.
    """
    settings, api_keys = load_env_variables() # Panggil fungsi yang sudah ada

    logging.info("🔧 Konfigurasi Proyek Dimuat:")
    for key, value in settings.items():
        if key == "MODEL_LIST":
            logging.info(f"   - {key}: {', '.join(value)}")
        else:
            logging.info(f"   - {key}: {value}")
    
    logging.info(f"📋 Model Fallback Sequence: {' → '.join(settings['MODEL_LIST'])}")
        
    if not api_keys:
        raise ValueError("❌ Tidak ada API Key di .env. Pastikan setidaknya GOOGLE_API_KEY_1 ada.")
    
    logging.info(f"🔑 Ditemukan {len(api_keys)} API Key untuk rotasi.")
    
    return settings, api_keys