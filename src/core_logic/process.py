# src/core_logic/process.py

import argparse
import glob
import os
import random
import time
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Any
import json # <<< PERUBAHAN DIMULAI

import google.generativeai as genai
from google.generativeai import types
import pandas as pd
from .env_manager import load_and_log_config
from .request_tracker import log_request
from .session_manager import start_session, get_current_session, end_current_session
from tqdm import tqdm
import threading

# ... (semua fungsi dari setup_logging hingga open_dataset tetap sama) ...
# ... Saya akan langsung ke fungsi yang diubah.                 ...

LOG_DIR = "logs"

# Variabel global untuk state
API_KEYS: List[str] = []
current_key_index: int = 0
CONFIG: Dict[str, str] = {}
MODEL_FALLBACK_LIST: List[str] = []
current_model_index: int = 0

def setup_logging():
    """
    Mengonfigurasi logging untuk menyimpan ke file dan menampilkan di konsol.
    """
    os.makedirs(LOG_DIR, exist_ok=True)
    log_filename = datetime.now().strftime("labeling_%Y-%m-%d.log")
    log_filepath = os.path.join(LOG_DIR, log_filename)

    # Konfigurasi dasar logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_filepath), # Simpan ke file
            logging.StreamHandler()            # Tampilkan di terminal
        ]
    )

def initialize_labeling_process() -> None:
    """
    Inisialisasi proses pelabelan dengan memuat konfigurasi dan menyiapkan API.
    """
    global API_KEYS, current_key_index, CONFIG, MODEL_FALLBACK_LIST, current_model_index
    
    # Muat konfigurasi menggunakan fungsi terpusat dari env_manager
    settings, api_keys = load_and_log_config()
    
    # Atur variabel global
    CONFIG = settings
    API_KEYS = api_keys
    current_key_index = 0
    
    # Setup model fallback
    MODEL_FALLBACK_LIST = CONFIG['MODEL_LIST']
    current_model_index = 0
    CONFIG['MODEL_NAME'] = MODEL_FALLBACK_LIST[current_model_index]


def load_config_and_keys() -> None:
    """
    Alias untuk initialize_labeling_process() untuk kompatibilitas dengan GUI.
    Memuat konfigurasi dan API keys dari environment variables.
    """
    initialize_labeling_process()
    
    # Log model awal yang digunakan
    logging.info(f"🎯 Model Awal: {CONFIG['MODEL_NAME']}")
    logging.info(f"📋 Model Fallback Tersedia: {len(MODEL_FALLBACK_LIST)} model")
    
    # Konfigurasi Gemini dengan API key pertama
    genai.configure(api_key=API_KEYS[current_key_index])

def rotate_api_key() -> None:
    """Beralih ke API key berikutnya dalam daftar."""
    global current_key_index
    current_key_index = (current_key_index + 1) % len(API_KEYS)
    new_key = API_KEYS[current_key_index]
    genai.configure(api_key=new_key)
    logging.warning(f"Merotasi ke API Key #{current_key_index + 1}...")

def rotate_model() -> bool:
    """
    Beralih ke model berikutnya dalam daftar fallback ketika mencapai batas kuota.
    
    Returns:
        bool: True jika berhasil beralih ke model berikutnya, False jika semua model habis.
    """
    global current_model_index, CONFIG
    
    # Coba beralih ke model berikutnya
    next_model_index = current_model_index + 1
    
    # Cek apakah masih ada model dalam daftar fallback
    if next_model_index < len(MODEL_FALLBACK_LIST):
        # Update index dan model name
        current_model_index = next_model_index
        old_model = CONFIG['MODEL_NAME']
        CONFIG['MODEL_NAME'] = MODEL_FALLBACK_LIST[current_model_index]
        
        # Log perpindahan model
        logging.warning(f"⚠️ Batas kuota tercapai untuk {old_model}")
        logging.warning(f"🔄 Beralih ke model berikutnya: {CONFIG['MODEL_NAME']}")
        logging.info(f"📊 Model ke-{current_model_index + 1} dari {len(MODEL_FALLBACK_LIST)} tersedia")
        
        return True
    else:
        # Semua model dalam fallback list sudah habis
        logging.error(f"❌ KRITIS: Semua model dalam fallback list telah mencapai batas kuota harian!")
        logging.error(f"💡 Model yang telah dicoba: {', '.join(MODEL_FALLBACK_LIST)}")
        logging.error(f"🛑 Proses pelabelan dihentikan. Coba lagi besok atau tambah model ke fallback list.")
        
        return False

def load_prompt_template(filepath: str = "prompt_template.txt") -> str:
    """
    Memuat isi template prompt dari file eksternal dan memperbaiki format kurung kurawal.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Escape semua kurung kurawal kecuali placeholder {data_json}
        # Pertama, ganti {data_json} dengan placeholder sementara
        content = content.replace('{data_json}', '__DATA_JSON_PLACEHOLDER__')
        
        # Escape semua kurung kurawal yang tersisa
        content = content.replace('{', '{{').replace('}', '}}')
        
        # Kembalikan placeholder {data_json}
        content = content.replace('__DATA_JSON_PLACEHOLDER__', '{data_json}')
        
        return content
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ File prompt '{filepath}' tidak ditemukan.")

# <<< PERUBAHAN DIMULAI
def generate_from_gemini(prompt: str, generation_config: Dict, response_schema: Any = None) -> List[Dict[str, Any]]:
    """
    Mengirimkan prompt ke model Gemini dan menghasilkan keluaran JSON terstruktur.
    
    Args:
        prompt (str): Teks prompt yang akan dikirim ke model Gemini.
        generation_config (Dict): Konfigurasi generasi model (misalnya max tokens, temperature, dsb.).
        response_schema (types.Schema): Skema JSON yang harus diikuti oleh output model.

    Returns:
        List[Dict[str, Any]]: Daftar dictionary hasil parsing dari output JSON model.

    Raises:
        ValueError: Jika respons dari model tidak berisi konten atau JSON tidak valid.
        Exception: Jika terjadi error saat melakukan request API.
    """
    model = genai.GenerativeModel(CONFIG['MODEL_NAME'])
    
    # Record start time untuk tracking response time
    start_time = time.time()
    request_successful = False
    error_message = None
    
    try:
        # Extended timeout for large batches (up to 250 items)
        REQUEST_TIMEOUT = 900  # 15 minutes timeout for large batches
        
        logging.info(f"🚀 Mengirim prompt ke model {CONFIG['MODEL_NAME']}...")
        logging.info(f"   └─ Request timeout: {REQUEST_TIMEOUT} seconds (15 minutes)")
        logging.info(f"   └─ Prompt length: {len(prompt):,} characters")
        
        # Simplified generation config without response schema for compatibility
        full_generation_config = genai.types.GenerationConfig(
            **generation_config
        )
        
        # Track request start time for timeout detection
        request_start = time.time()
        logging.info(f"   └─ Request started at: {time.strftime('%H:%M:%S')}")
        
        response = model.generate_content(prompt, generation_config=full_generation_config)
        request_duration = time.time() - request_start
        
        logging.info(f"📥 Response diterima dalam {request_duration:.2f} seconds ({request_duration/60:.1f} minutes)")
        
        # Log warning if request takes very long
        if request_duration > 300:  # 5 minutes
            logging.warning(f"⚠️ Request duration sangat lama: {request_duration/60:.1f} minutes")
        
        if not response.parts:
            finish_reason = response.candidates[0].finish_reason.name if response.candidates else "UNKNOWN"
            error_message = f"Respons tidak berisi konten. Finish Reason: {finish_reason}"
            logging.error(f"🚫 Response kosong dari model:")
            logging.error(f"   └─ Finish Reason: {finish_reason}")
            logging.error(f"   └─ Candidates: {len(response.candidates) if response.candidates else 0}")
            raise ValueError(error_message)
        
        # Log raw response untuk debugging
        raw_response_text = response.text.strip()
        logging.info(f"📥 Raw response dari model (length: {len(raw_response_text)}):")
        
        # Show preview of response
        if len(raw_response_text) > 400:
            logging.info(f"   └─ First 200 chars: {raw_response_text[:200]}...")
            logging.info(f"   └─ Last 200 chars: ...{raw_response_text[-200:]}")
        else:
            logging.info(f"   └─ Full response: {raw_response_text}")
        
        # Check if response is empty or whitespace only
        if not raw_response_text:
            error_message = "Response text kosong setelah strip"
            logging.error(f"🚫 {error_message}")
            raise ValueError(error_message)
            
        # Parsing JSON di sini untuk memastikan validitas sebelum dikembalikan
        try:
            result = json.loads(raw_response_text)
            logging.info(f"✅ JSON parsing berhasil: {type(result)} dengan {len(result) if isinstance(result, list) else 'N/A'} items")
        except json.JSONDecodeError as json_error:
            # Enhanced JSON error logging
            logging.error(f"🚫 JSON Decode Error Detail:")
            logging.error(f"   └─ Error: {json_error}")
            logging.error(f"   └─ Position: line {json_error.lineno}, column {json_error.colno}")
            logging.error(f"   └─ Raw text repr: {repr(raw_response_text[:500])}")
            
            # Try to find and extract JSON from response (markdown wrapped or truncated)
            import re
            
            # Pattern 1: Extract from markdown code blocks
            markdown_pattern = r'```(?:json)?\s*(\[.*?\])\s*```'
            markdown_matches = re.findall(markdown_pattern, raw_response_text, re.DOTALL)
            
            if markdown_matches:
                logging.info(f"   └─ Found JSON in markdown blocks, trying to parse...")
                try:
                    result = json.loads(markdown_matches[0])
                    logging.info(f"✅ Successfully parsed markdown JSON with {len(result)} items")
                    logging.info(f"🎯 Returning parsed result to calling function...")
                    request_successful = True
                    return result
                except json.JSONDecodeError:
                    logging.error(f"   └─ Markdown JSON also invalid")
            
            # Pattern 2: Extract JSON arrays (even if truncated)
            json_pattern = r'\[.*?\]'
            json_matches = re.findall(json_pattern, raw_response_text, re.DOTALL)
            
            if json_matches:
                logging.info(f"   └─ Found {len(json_matches)} potential JSON arrays, trying to parse...")
                for i, match in enumerate(json_matches):
                    try:
                        result = json.loads(match)
                        logging.info(f"✅ Successfully parsed extracted JSON #{i+1} with {len(result)} items")
                        request_successful = True
                        return result
                    except json.JSONDecodeError:
                        logging.warning(f"   └─ JSON match #{i+1} invalid, trying next...")
                        continue
            
            # Pattern 3: Try to fix truncated JSON by adding closing brackets
            if raw_response_text.strip().startswith('['):
                logging.info(f"   └─ Attempting to fix truncated JSON...")
                
                # Count open and close brackets
                open_brackets = raw_response_text.count('[')
                close_brackets = raw_response_text.count(']')
                open_braces = raw_response_text.count('{')
                close_braces = raw_response_text.count('}')
                
                # Try to complete the JSON
                fixed_json = raw_response_text.strip()
                
                # Add missing closing braces
                missing_braces = open_braces - close_braces
                if missing_braces > 0:
                    # Remove incomplete object/entry at the end
                    last_complete_brace = fixed_json.rfind('}')
                    if last_complete_brace > 0:
                        fixed_json = fixed_json[:last_complete_brace + 1]
                
                # Add missing closing bracket
                missing_brackets = open_brackets - close_brackets
                if missing_brackets > 0:
                    fixed_json += ']' * missing_brackets
                
                try:
                    result = json.loads(fixed_json)
                    logging.info(f"✅ Successfully parsed fixed JSON with {len(result)} items")
                    logging.warning(f"   ⚠️  JSON was truncated but recovered {len(result)} items")
                    request_successful = True
                    return result
                except json.JSONDecodeError:
                    logging.error(f"   └─ Could not fix truncated JSON")
            
            # If all parsing attempts fail, raise original error
            logging.error(f"🚫 All JSON parsing attempts failed")
            raise json_error
            
        request_successful = True
        return result
        
    except json.JSONDecodeError as e:
        error_message = f"Gagal mem-parsing JSON dari respons model: {e}"
        logging.error(f"🚫 JSON parsing gagal setelah semua upaya")
        raise ValueError(error_message) from e
    except Exception as e:
        error_message = f"Error saat request API: {e}"
        logging.error(f"🚫 API request error: {error_message}")
        raise Exception(error_message) from e
    finally:
        # Record request metrics
        response_time = time.time() - start_time
        logging.info(f"🔄 Recording request metrics (response_time: {response_time:.2f}s)...")
        
        request_id = log_request(
            api_key_index=current_key_index + 1,  # 1-based indexing for display
            model_name=CONFIG['MODEL_NAME'],
            success=request_successful,
            response_time=response_time,
            error_message=error_message
        )
        logging.info(f"✅ Request logged with ID: {request_id}")
        
        # Force save untuk persistence setiap request labeling
        logging.info(f"🔄 Starting session stats save...")
        from .request_tracker import get_request_tracker
        tracker = get_request_tracker()
        logging.info(f"📊 Got request tracker instance")
        
        tracker._save_session_stats()
        logging.info(f"✅ Session stats saved successfully")
        logging.info(f"🎯 generate_from_gemini() finally block completed")
# <<< PERUBAHAN SELESAI

def open_dataset(dataset_dir: str, base_filename: str) -> Tuple[pd.DataFrame, str]:
    """
    Membuka dataset dari direktori dengan prioritas file CSV, kemudian XLSX.
    """
    csv_path = os.path.join(dataset_dir, f"{base_filename}.csv")
    xlsx_path = os.path.join(dataset_dir, f"{base_filename}.xlsx")

    try:
        if os.path.exists(csv_path):
            logging.info(f"Ditemukan file CSV: '{csv_path}'")
            return pd.read_csv(csv_path), csv_path
        elif os.path.exists(xlsx_path):
            logging.info(f"Ditemukan file XLSX: '{xlsx_path}'")
            return pd.read_excel(xlsx_path), xlsx_path
        else:
            raise FileNotFoundError(f"Dataset tidak ditemukan. Tidak ada file '{csv_path}' atau '{xlsx_path}'.")
    except Exception as e:
        raise Exception(f"Gagal membaca file dataset: {e}") from e


# <<< PERUBAHAN DIMULAI: Seluruh fungsi label_dataset dioptimalkan untuk resume
def create_or_resume_output_file(df_master: pd.DataFrame, base_name: str, output_dir: str) -> tuple[str, pd.DataFrame, dict]:
    """
    Membuat atau melanjutkan file output tunggal untuk labeling.
    
    Returns:
        tuple: (filepath, working_df, progress_info)
        - filepath: Path ke file output
        - working_df: DataFrame untuk dikerjakan (copy dari master dengan progress existing)
        - progress_info: Dict dengan info progress (total, labeled, unlabeled, percent)
    """
    from datetime import datetime
    
    # Generate filename dengan timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{base_name}_labeled_{timestamp}.xlsx"
    filepath = os.path.join(output_dir, filename)
    
    # Cek apakah ada file existing dengan pattern yang sama
    existing_files = []
    if os.path.exists(output_dir):
        for f in os.listdir(output_dir):
            if f.startswith(f"{base_name}_labeled_") and f.endswith(".xlsx"):
                existing_files.append(f)
    
    if existing_files:
        # Gunakan file yang paling baru
        existing_files.sort(reverse=True)
        latest_file = existing_files[0]
        filepath = os.path.join(output_dir, latest_file)
        
        logging.info(f"📂 File existing ditemukan: {latest_file}")
        
        try:
            # Load existing progress
            existing_df = pd.read_excel(filepath)
            logging.info(f"✅ Loaded existing file dengan {len(existing_df)} baris")
            
            # Ensure required columns exist
            if "label" not in existing_df.columns: 
                existing_df["label"] = None
            if "justifikasi" not in existing_df.columns: 
                existing_df["justifikasi"] = None
            if 'id' not in existing_df.columns:
                existing_df['id'] = range(len(existing_df))
            
            # Use existing file as working dataframe
            working_df = existing_df.copy()
            
        except Exception as e:
            logging.warning(f"⚠️ Error loading existing file: {e}")
            logging.info("🔄 Membuat file baru...")
            working_df = df_master.copy()
            
    else:
        logging.info(f"🆕 Membuat file output baru: {filename}")
        working_df = df_master.copy()
        
        # Ensure required columns
        if "label" not in working_df.columns: 
            working_df["label"] = None
        if "justifikasi" not in working_df.columns: 
            working_df["justifikasi"] = None
        if 'id' not in working_df.columns:
            working_df['id'] = range(len(working_df))
    
    # Calculate progress
    total_rows = len(working_df)
    labeled_rows = working_df['label'].notna().sum()
    unlabeled_rows = total_rows - labeled_rows
    percent_complete = (labeled_rows / total_rows * 100) if total_rows > 0 else 0
    
    progress_info = {
        'total': total_rows,
        'labeled': labeled_rows,
        'unlabeled': unlabeled_rows,
        'percent': percent_complete
    }
    
    logging.info(f"📊 Progress: {labeled_rows}/{total_rows} ({percent_complete:.1f}%) - {unlabeled_rows} remaining")
    
    return filepath, working_df, progress_info


def find_optimal_batches(df: pd.DataFrame, batch_size: int) -> List[tuple]:
    """
    Menemukan batch yang optimal untuk diproses (skip baris yang sudah dilabeli parsial).
    
    Returns:
        List[tuple]: List of (start_idx, end_idx) untuk batch yang perlu diproses
    """
    total_rows = len(df)
    batches_to_process = []
    
    for start in range(0, total_rows, batch_size):
        end = min(start + batch_size, total_rows)
        batch_slice = df.iloc[start:end]
        
        # Hitung status labeling dalam batch ini
        labeled_count = batch_slice['label'].notna().sum()
        total_in_batch = len(batch_slice)
        
        # Skip batch yang sudah complete
        if labeled_count == total_in_batch:
            logging.info(f"⏭️ Skip batch {start+1}-{end} (already complete: {labeled_count}/{total_in_batch})")
            continue
        
        # Skip batch yang sudah parsial (untuk efisiensi quota)
        if labeled_count > 0:
            logging.info(f"⏭️ Skip batch {start+1}-{end} (partial: {labeled_count}/{total_in_batch} - tidak efisien)")
            continue
        
        # Proses batch yang benar-benar kosong
        logging.info(f"✅ Queue batch {start+1}-{end} (unlabeled: 0/{total_in_batch})")
        batches_to_process.append((start, end))
    
    return batches_to_process


def label_dataset(df_master: pd.DataFrame, base_name: str, batch_size: int, max_retry: int, generation_config: Dict, text_column_name: str, allowed_labels: List[str], stop_event: threading.Event) -> None:
    """
    Mengorkestrasi proses pelabelan dengan single file output dan resume capability.
    Membuat copy dataset ke results folder, lalu update in-place.
    """
    output_dir_for_project = os.path.join(CONFIG['OUTPUT_DIR'], base_name)
    os.makedirs(output_dir_for_project, exist_ok=True)
    
    logging.info(f"📂 Direktori output proyek: {output_dir_for_project}")

    # <<< SESSION MANAGEMENT: Inisialisasi session baru >>>
    session_manager = start_session(base_name, batch_size)
    logging.info(f"🚀 Session dimulai: {session_manager.session_id}")
    logging.info(f"📁 Session directory: {session_manager.session_dir}")

    # <<< SINGLE FILE OUTPUT: Create or resume >>>
    output_filepath, working_df, progress_info = create_or_resume_output_file(df_master, base_name, output_dir_for_project)
    
    logging.info(f"📄 Output file: {os.path.basename(output_filepath)}")
    logging.info(f"📊 Progress: {progress_info['labeled']}/{progress_info['total']} ({progress_info['percent']:.1f}%)")
    
    # Check if already complete
    if progress_info['unlabeled'] == 0:
        logging.warning(f"🎉 DATASET SUDAH SELESAI! Semua {progress_info['total']} baris sudah dilabeli.")
        if session_manager:
            session_manager.end_session(progress_info['total'])
        return

    prompt_template = load_prompt_template()
    
    # <<< OPTIMAL BATCH PROCESSING: Find batches to process >>>
    batches_to_process = find_optimal_batches(working_df, batch_size)
    
    if not batches_to_process:
        logging.warning(f"📋 Tidak ada batch yang perlu diproses. Semua batch sudah complete atau parsial.")
        logging.info(f"💡 Gunakan batch size yang lebih kecil untuk memproses baris parsial, atau review manual untuk baris yang gagal.")
        if session_manager:
            session_manager.end_session(progress_info['total'])
        return
    
    logging.info(f"🎯 Akan memproses {len(batches_to_process)} batch optimal dari total {progress_info['unlabeled']} baris belum dilabeli")

    total_rows = len(working_df)
    
    # End of function - will be replaced with new implementation
    logging.info("⚠️ Function implementation incomplete - needs update")
    session_manager.end_session(total_rows)
    
    # Check if all batches are already processed by scanning existing batch files
    total_batches_expected = (total_rows + batch_size - 1) // batch_size  # Ceiling division
    existing_batches = 0
    completed_batches = 0
    
    for i in range(0, total_rows, batch_size):
        end = min(i + batch_size, total_rows)
        batch_filename = f"{base_name}_batch{i+1:03d}_{end:03d}.xlsx"
        batch_filepath = os.path.join(output_dir_for_project, batch_filename)
        
        if os.path.exists(batch_filepath):
            existing_batches += 1
            # Check if this batch is fully labeled
            try:
                batch_df = pd.read_excel(batch_filepath)
                if batch_df['label'].notna().all():  # All rows have labels
                    completed_batches += 1
            except:
                pass  # If can't read file, consider it incomplete
    
    if existing_batches == total_batches_expected and completed_batches == total_batches_expected:
        logging.warning(f"🎉 SEMUA BATCH SUDAH SELESAI! Ditemukan {completed_batches}/{total_batches_expected} batch lengkap.")
        logging.info("💡 Hapus file batch yang ingin diproses ulang, atau ubah nama proyek untuk memulai baru.")
        if session_manager:
            session_manager.end_session(total_rows)
        return

    logging.info("🏁 Memulai proses pelabelan per-batch dengan penyimpanan real-time...")
    
    try:
        for start in tqdm(range(0, total_rows, batch_size), desc="Overall Progress", unit="batch"):
            logging.info(f"🔄 Starting batch loop iteration: {start+1}-{min(start + batch_size, total_rows)}")
            
            if stop_event.is_set():
                logging.warning("Proses dihentikan oleh pengguna.")
                break  

            end = min(start + batch_size, total_rows)
            batch_id = f"batch_{start+1}_{end}"
            
            logging.info(f"📋 Processing batch {start+1}-{end} (ID: {batch_id})")

            # <<< SESSION TRACKING: Start batch tracking >>>
            batch_info = session_manager.start_batch(batch_id, start, end)
            logging.info(f"🚀 Session tracking started for batch {batch_id}")

            # Get batch slice from working dataframe (single file approach)
            batch_slice = working_df.iloc[start:end].copy()

            # Find rows that need labeling (label is NaN/None)
            unlabeled_in_batch = batch_slice[batch_slice['label'].isna()]

            # If no rows need labeling, batch is complete
            if unlabeled_in_batch.empty:
                logging.info(f"✅ Batch {start+1}-{end} sudah lengkap ({len(batch_slice)} items). Melewati...")
                session_manager.end_batch(
                    batch_info, success=True, items_processed=len(batch_slice), items_failed=0
                )
                continue
            
            logging.info(f"🔄 Batch {start+1}-{end}: {len(unlabeled_in_batch)}/{len(batch_slice)} items perlu dilabeli.")

            # Prepare data for processing (only unlabeled items)
            data_to_process = unlabeled_in_batch[['id', text_column_name]].to_dict(orient='records')
            data_json_string = json.dumps(data_to_process, indent=2)

            is_batch_valid = False
            attempts = 0
            token_limit_error_detected = False
            batch_error_message = None

            while not is_batch_valid and attempts < max_retry:
                attempts += 1
                prompt = prompt_template.format(data_json=data_json_string)
            
            try:
                logging.info(f"🔄 Mengirim request ke API untuk batch {start+1}-{end}...")
                logging.info(f"   └─ Batch size: {len(unlabeled_in_batch)} items")
                logging.info(f"   └─ Large batch optimization: {'ENABLED' if len(unlabeled_in_batch) > 100 else 'DISABLED'}")
                
                # Add extra logging for large batches (>100 items)
                if len(unlabeled_in_batch) > 100:
                    logging.info(f"⚡ Processing large batch ({len(unlabeled_in_batch)} items) - this may take 5-15 minutes...")
                    logging.info(f"   └─ Expected processing time: {len(unlabeled_in_batch) * 2}+ seconds")
                    logging.info(f"   └─ Please be patient, do not interrupt...")
                
                output_list = generate_from_gemini(prompt, generation_config)
                logging.info(f"🎯 generate_from_gemini() completed, received result")
                logging.info(f"📥 Response diterima dari API - processing hasil...")
                logging.info(f"🔄 Checking hasil type dan format...")
                
                # Immediate type and basic validation
                logging.info(f"   └─ Result type: {type(output_list)}")
                logging.info(f"   └─ Result is list: {isinstance(output_list, list)}")
                if isinstance(output_list, list):
                    logging.info(f"   └─ List length: {len(output_list)}")
                else:
                    logging.warning(f"   └─ Unexpected type, content preview: {str(output_list)[:200]}...")

                # <<< PERUBAHAN BARU: Tampilkan output model untuk monitoring >>>
                logging.info(f"🤖 Starting model response analysis...")
                logging.info(f"🤖 Model Response untuk batch {start+1}-{end}:")
                logging.info(f"   📊 Jumlah hasil: {len(output_list) if isinstance(output_list, list) else 'Bukan list'}")
                logging.info(f"   📋 Tipe data: {type(output_list)}")
                
                # Show processing efficiency for large batches
                if len(unlabeled_in_batch) > 100 and isinstance(output_list, list):
                    success_rate = (len(output_list) / len(unlabeled_in_batch)) * 100
                    logging.info(f"   📈 Success rate: {success_rate:.1f}% ({len(output_list)}/{len(unlabeled_in_batch)} items)")
                
                logging.info(f"🔍 Starting preview generation...")
                
                # Tampilkan preview output (maksimal 3 item pertama)
                logging.info(f"🔄 Checking if output_list is valid for preview...")
                logging.info(f"   └─ isinstance(output_list, list): {isinstance(output_list, list)}")
                logging.info(f"   └─ len(output_list) > 0: {len(output_list) > 0 if isinstance(output_list, list) else 'N/A'}")
                
                if isinstance(output_list, list) and len(output_list) > 0:
                    preview_count = min(3, len(output_list))
                    logging.info(f"   📝 Generating preview untuk {preview_count} item...")
                    logging.info(f"   📝 Starting preview loop iteration...")
                    
                    # Add timeout protection for preview generation
                    import time
                    preview_start_time = time.time()
                    PREVIEW_TIMEOUT = 30  # 30 seconds timeout
                    
                    try:
                        for i in range(preview_count):
                            # Check timeout
                            if time.time() - preview_start_time > PREVIEW_TIMEOUT:
                                logging.error(f"⏰ TIMEOUT: Preview generation exceeded {PREVIEW_TIMEOUT} seconds")
                                break
                                
                            logging.info(f"      🔄 Processing preview item {i+1}/{preview_count}...")
                            try:
                                item = output_list[i]
                                logging.info(f"      └─ Item {i+1} retrieved, type: {type(item)}")
                                
                                if isinstance(item, dict):
                                    item_id = item.get('id', 'N/A')
                                    item_label = item.get('label', 'N/A')
                                    item_justifikasi = item.get('justifikasi', 'N/A')
                                    logging.info(f"      └─ Item {i+1}: ID={item_id}, Label={item_label}")
                                    
                                    # Safe justifikasi processing with timeout check
                                    if time.time() - preview_start_time > PREVIEW_TIMEOUT:
                                        logging.error(f"⏰ TIMEOUT during justifikasi processing")
                                        break
                                        
                                    justifikasi_preview = str(item_justifikasi)[:50] if item_justifikasi else 'N/A'
                                    logging.info(f"         Justifikasi preview: '{justifikasi_preview}...'")
                                else:
                                    item_preview = str(item)[:100] if item else 'N/A'
                                    logging.info(f"      Item {i+1}: {item_preview}...")
                                    
                                logging.info(f"      ✅ Item {i+1} preview completed")
                            except Exception as item_error:
                                logging.error(f"      ❌ Error processing item {i+1}: {item_error}")
                                try:
                                    item_content = str(output_list[i])[:200] if i < len(output_list) else 'Index out of range'
                                    logging.error(f"         Item content: {item_content}...")
                                except:
                                    logging.error(f"         Could not preview item content")
                        
                        preview_duration = time.time() - preview_start_time
                        logging.info(f"✅ Preview loop completed successfully in {preview_duration:.2f} seconds")
                        
                        if len(output_list) > 3:
                            logging.info(f"   📝 ... dan {len(output_list) - 3} item lainnya")
                        
                    except Exception as preview_error:
                        logging.error(f"❌ Error during preview generation: {preview_error}")
                        logging.error(f"   └─ This might indicate data format issues")
                        import traceback
                        logging.error(f"   └─ Traceback: {traceback.format_exc()}")
                else:
                    logging.warning(f"   ⚠️ Output tidak dalam format yang diharapkan: {str(output_list)[:200]}...")

                logging.info(f"🔍 Starting validation process...")
                logging.info(f"   └─ Expected items: {len(unlabeled_in_batch)}")
                logging.info(f"   └─ Received items: {len(output_list) if isinstance(output_list, list) else 'non-list'}")
                logging.info(f"   └─ Type check: {type(output_list)}")
                
                # <<< PERUBAHAN 2: Validasi disesuaikan dengan jumlah data yang dikirim >>>
                if not isinstance(output_list, list) or len(output_list) != len(unlabeled_in_batch):
                    logging.warning(f"❌ Jumlah output JSON tidak sesuai. Diharapkan {len(unlabeled_in_batch)}, diterima {len(output_list)}. Mencoba lagi...")
                    time.sleep(3)
                    continue
                
                logging.info(f"✅ Validation PASSED - data format dan jumlah sesuai!")
                logging.info(f"✅ Batch {start+1}-{end} berhasil diproses dan divalidasi!")
                logging.info(f"🎯 Keluar dari loop retry, melanjutkan ke penyimpanan...")
                is_batch_valid = True

            except Exception as e:
                # ... (logika error handling tetap sama) ...
                logging.error(f"Error pada API Key #{current_key_index + 1} saat memproses batch {start+1}-{end}", exc_info=True)
                error_string = str(e).lower()
                if "max_tokens" in error_string or "finish reason: max_tokens" in error_string:
                    logging.error(f"⛔️ ERROR TOKEN LIMIT! Menyimpan batch {start+1}-{end} dengan hasil parsial...")
                    batch_slice.to_excel(batch_filepath, index=False) # Save partial results
                    token_limit_error_detected = True
                    break
                if any(keyword in error_string for keyword in ["quota", "limit", "permission denied"]):
                    # Coba rotasi model terlebih dahulu
                    if rotate_model():
                        # Berhasil beralih ke model baru, coba lagi dengan model baru
                        logging.info(f"🔄 Mencoba ulang batch {start+1}-{end} dengan model baru...")
                        continue  # Langsung coba lagi tanpa menunggu
                    else:
                        # Semua model habis, hentikan proses
                        logging.error(f"🛑 Menghentikan proses karena semua model mencapai batas kuota.")
                        batch_error_message = "Semua model mencapai batas kuota"
                        stop_event.set()
                        break
                else:
                    # Error lain, rotasi API key seperti biasa
                    rotate_api_key()
                    batch_error_message = f"API error pada attempt {attempts}"
                
                # Adaptive wait time based on batch size
                base_wait_time = (2 ** attempts) + random.random()
                if len(unlabeled_in_batch) > 100:
                    # Longer wait for large batches to avoid overwhelming API
                    adaptive_wait_time = base_wait_time * 2
                    logging.info(f"⏳ Large batch detected - extending wait time to {adaptive_wait_time:.1f} seconds")
                else:
                    adaptive_wait_time = base_wait_time
                
                time.sleep(adaptive_wait_time)

            # <<< SESSION TRACKING: End batch dengan hasil >>>
            logging.info(f"🔄 Post-processing batch {start+1}-{end} - checking is_batch_valid: {is_batch_valid}")
            
            if is_batch_valid:
                logging.info(f"✅ Batch VALID - starting DataFrame creation and storage...")
                
                try:
                    output_df = pd.DataFrame(output_list)
                    logging.info(f"📊 DataFrame created successfully from output_list")
                except Exception as df_error:
                    logging.error(f"❌ Error creating DataFrame: {df_error}")
                    raise df_error
                
                logging.info(f"💾 Menyimpan hasil batch {start+1}-{end}:")
                logging.info(f"   📊 DataFrame shape: {output_df.shape}")
                logging.info(f"   📋 Columns: {list(output_df.columns) if not output_df.empty else 'Empty DataFrame'}")
                
                label_distribution = None
                if not output_df.empty:
                    # Tampilkan statistik label sebelum menyimpan
                    if 'label' in output_df.columns:
                        label_counts = output_df['label'].value_counts()
                        label_distribution = dict(label_counts)
                        logging.info(f"   📈 Distribusi label: {label_distribution}")
                    
                    # Update working_df dengan hasil dari batch (single file approach)
                    # Siapkan kedua DataFrame dengan 'id' sebagai index
                    output_df.set_index('id', inplace=True)
                    
                    # Update working_df langsung untuk baris yang diproses
                    for idx, row in output_df.iterrows():
                        working_df.loc[working_df['id'] == idx, 'label'] = row['label']
                        working_df.loc[working_df['id'] == idx, 'justifikasi'] = row['justifikasi']

                # Save ke single output file (bukan per batch)
                working_df.to_excel(output_filepath, index=False)
                logging.info(f"   💾 Single file updated: {os.path.basename(output_filepath)}")
                
                # Calculate current progress
                labeled_count = working_df['label'].notna().sum()
                total_count = len(working_df)
                progress_percent = (labeled_count / total_count * 100) if total_count > 0 else 0
                logging.info(f"   📊 Progress: {labeled_count}/{total_count} ({progress_percent:.1f}%) completed")
                
                # Session tracking untuk batch sukses
                session_manager.end_batch(
                    batch_info, 
                    success=True, 
                    items_processed=len(unlabeled_in_batch),
                    items_failed=0,
                    label_distribution=label_distribution,
                    model_used=CONFIG.get('MODEL_NAME'),
                    api_key_index=current_key_index + 1
                )
                
            elif not token_limit_error_detected:
                logging.warning(f"Gagal memproses {len(unlabeled_in_batch)} baris dalam batch {start+1}-{end} setelah {max_retry} percobaan.")
                # Save current state ke single output file
                working_df.to_excel(output_filepath, index=False)
                logging.info(f"   💾 Current progress saved: {os.path.basename(output_filepath)}")
                
                # Calculate current progress
                labeled_count = working_df['label'].notna().sum()
                total_count = len(working_df)
                progress_percent = (labeled_count / total_count * 100) if total_count > 0 else 0
                logging.info(f"   ⚠️  Progress: {labeled_count}/{total_count} ({progress_percent:.1f}%) - batch failed")
                
                # Session tracking untuk batch gagal
                session_manager.end_batch(
                    batch_info,
                    success=False,
                    items_processed=0,
                    items_failed=len(unlabeled_in_batch),
                    error_message=batch_error_message or f"Gagal setelah {max_retry} percobaan",
                    model_used=CONFIG.get('MODEL_NAME'),
                    api_key_index=current_key_index + 1
                )
            else:
                # Token limit error - save current state
                working_df.to_excel(output_filepath, index=False)
                logging.info(f"   💾 Current progress saved (token limit): {os.path.basename(output_filepath)}")
                
                # Calculate current progress
                labeled_count = working_df['label'].notna().sum()
                total_count = len(working_df)
                progress_percent = (labeled_count / total_count * 100) if total_count > 0 else 0
                logging.info(f"   ⚠️  Progress: {labeled_count}/{total_count} ({progress_percent:.1f}%) - token limit")
                
                # Token limit error
                session_manager.end_batch(
                    batch_info,
                    success=False,
                    items_processed=0,
                    items_failed=len(unlabeled_in_batch),
                    error_message="Token limit exceeded",
                    model_used=CONFIG.get('MODEL_NAME'),
                    api_key_index=current_key_index + 1
                )

            # Adaptive delay between batches based on batch size
            logging.info(f"🔄 Batch {start+1}-{end} processing completed, preparing for next batch...")
            
            if len(unlabeled_in_batch) > 100:
                inter_batch_delay = 5  # 5 seconds for large batches
                logging.info(f"⏳ Large batch completed - waiting {inter_batch_delay}s before next batch...")
            else:
                inter_batch_delay = 2  # 2 seconds for normal batches
                logging.info(f"⏳ Batch completed - waiting {inter_batch_delay}s before next batch...")
            
            time.sleep(inter_batch_delay)
            logging.info(f"✅ Inter-batch delay completed, continuing to next iteration...")
            
            # Cek apakah proses dihentikan karena semua model habis
            if stop_event.is_set():
                logging.warning("🛑 Proses dihentikan karena semua model mencapai batas kuota harian.")
                break
        
        # Session completed - single file output
        logging.info("🏁 Semua batch telah diproses!")
        
        # Final save and progress report
        working_df.to_excel(output_filepath, index=False)
        final_labeled = working_df['label'].notna().sum()
        final_total = len(working_df)
        final_percent = (final_labeled / final_total * 100) if final_total > 0 else 0
        
        logging.info(f"📄 Final result: {os.path.basename(output_filepath)}")
        logging.info(f"� Final progress: {final_labeled}/{final_total} ({final_percent:.1f}%) completed")
        logging.info("💡 All results consolidated in single output file.")
        
    except Exception as e:
        logging.error(f"❌ Error fatal dalam session: {e}")
    finally:
        # <<< SESSION MANAGEMENT: End session >>>
        if session_manager:
            session_manager.end_session(total_rows)
            logging.info(f"🏁 Session selesai: {session_manager.session_id}")
            logging.info(f"📊 Final stats: {session_manager.get_current_stats()}")

# <<< PERUBAHAN SELESAI