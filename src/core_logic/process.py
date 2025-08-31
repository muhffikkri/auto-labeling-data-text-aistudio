# src/core_logic/process.py

import argparse
import glob
import os
import random
import time
import logging
from datetime import datetime
from typing import Dict, List, Tuple

import google.generativeai as genai
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm
import threading

LOG_DIR = "logs"
LABELED_SUBDIR = "labeled"
UNLABELED_SUBDIR = "unlabeled"

# Variabel global untuk state
API_KEYS: List[str] = []
current_key_index: int = 0
CONFIG: Dict[str, str] = {}

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

def load_config_and_keys() -> None:
    """
    Memuat semua konfigurasi (path, nama model, dan API keys) dari file .env.
    """
    global API_KEYS, current_key_index, CONFIG
    load_dotenv()

    API_KEYS.clear()

    CONFIG['MODEL_NAME'] = os.getenv('MODEL_NAME', 'gemini-2.5-pro')
    CONFIG['OUTPUT_DIR'] = os.getenv('OUTPUT_DIR', 'results')
    CONFIG['DATASET_DIR'] = os.getenv('DATASET_DIR', 'dataset')

    logging.info("🔧 Konfigurasi Proyek Dimuat:")
    for key, value in CONFIG.items():
        logging.info(f"   - {key}: {value}")

    i = 1
    while True:
        key = os.getenv(f'GOOGLE_API_KEY_{i}')
        if key:
            API_KEYS.append(key)
            i += 1
        else:
            break
    if not API_KEYS:
        raise ValueError("❌ Tidak ada API Key di .env. Pastikan setidaknya GOOGLE_API_KEY_1 ada.")
    
    logging.info(f"🔑 Ditemukan {len(API_KEYS)} API Key untuk rotasi.")
    current_key_index = 0
    genai.configure(api_key=API_KEYS[current_key_index])

def rotate_api_key() -> None:
    """Beralih ke API key berikutnya dalam daftar."""
    global current_key_index
    current_key_index = (current_key_index + 1) % len(API_KEYS)
    new_key = API_KEYS[current_key_index]
    genai.configure(api_key=new_key)
    logging.warning(f"Merotasi ke API Key #{current_key_index + 1}...") # Menggunakan warning untuk event penting

def load_prompt_template(filepath: str = "prompt_template.txt") -> str:
    """
    Memuat isi template prompt dari file eksternal.

    Fungsi ini akan membaca file teks yang berisi template prompt 
    dan mengembalikan seluruh isinya sebagai string. 
    File dibuka dengan encoding UTF-8. Jika file tidak ditemukan, 
    fungsi akan melemparkan `FileNotFoundError`.

    Args:
        filepath (str, optional): Path menuju file template prompt. 
            Default: "prompt_template.txt".

    Returns:
        str: Isi template prompt dalam bentuk string.

    Raises:
        FileNotFoundError: Jika file dengan path yang diberikan tidak ditemukan.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ File prompt '{filepath}' tidak ditemukan.")

def generate_from_gemini(prompt: str, generation_config: Dict) -> List[str]:
    """
    Mengirimkan prompt ke model Gemini dan menghasilkan keluaran teks.

    Fungsi ini mengirimkan prompt ke model Gemini menggunakan konfigurasi 
    yang diberikan. Hasil keluaran berupa teks dari respons model, 
    yang diproses menjadi list string berdasarkan pemisah baris. 

    Jika respons dari model kosong atau tidak berisi konten, fungsi akan 
    melemparkan `ValueError`. Jika terjadi error lain saat request API, 
    fungsi akan melemparkan `Exception`.

    Args:
        prompt (str): Teks prompt yang akan dikirim ke model Gemini.
        generation_config (Dict): Konfigurasi generasi model (misalnya max tokens, temperature, dsb.).

    Returns:
        List[str]: Daftar string hasil keluaran model, dipisahkan berdasarkan baris.

    Raises:
        ValueError: Jika respons dari model tidak berisi konten.
        Exception: Jika terjadi error saat melakukan request API.
    """
    model = genai.GenerativeModel(CONFIG['MODEL_NAME'])
    try:
        response = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(**generation_config))
        
        if not response.parts:
            finish_reason = response.candidates[0].finish_reason.name if response.candidates else "UNKNOWN"
            raise ValueError(f"Respons tidak berisi konten. Finish Reason: {finish_reason}")

        return response.text.strip().split("\n")
    except Exception as e:
        raise Exception(f"Error saat request API: {e}") from e

def open_dataset(dataset_dir: str, base_filename: str) -> Tuple[pd.DataFrame, str]:
    """
    Membuka dataset dari direktori dengan prioritas file CSV, kemudian XLSX.

    Fungsi ini mencari dataset berdasarkan nama dasar file (`base_filename`) 
    di dalam direktori yang ditentukan. Jika ditemukan file dengan ekstensi 
    `.csv`, fungsi akan membacanya terlebih dahulu. Jika tidak ada, fungsi 
    akan mencoba membuka file `.xlsx`. Dataset yang berhasil dibaca dikembalikan 
    dalam bentuk `pandas.DataFrame` beserta path lengkap file yang digunakan.

    Args:
        dataset_dir (str): Direktori tempat file dataset berada.
        base_filename (str): Nama dasar file dataset (tanpa ekstensi).

    Returns:
        Tuple[pd.DataFrame, str]: Tuple yang berisi:
            - DataFrame hasil pembacaan dataset.
            - Path lengkap file dataset yang digunakan.

    Raises:
        FileNotFoundError: Jika file CSV maupun XLSX tidak ditemukan.
        Exception: Jika terjadi kesalahan saat membaca file dataset.
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

def finalize_results(output_dir: str, base_name: str) -> None:
    """
    Menggabungkan semua file batch hasil pelabelan menjadi file akhir.

    Fungsi ini mencari file batch yang sudah diberi label (`*_labeled.xlsx`) 
    maupun yang gagal diberi label (`*_unlabeled.xlsx`) dalam direktori output.  
    Semua batch yang ditemukan akan digabungkan menjadi satu file akhir untuk 
    masing-masing kategori (labeled dan unlabeled).  

    File hasil penggabungan disimpan di direktori output dengan nama:
    - `<base_name>_FULL_labeled.xlsx` untuk data yang berhasil dilabeli.
    - `<base_name>_FULL_unlabeled.xlsx` untuk data yang gagal dilabeli.

    Args:
        output_dir (str): Direktori utama tempat hasil batch disimpan.
        base_name (str): Nama dasar file yang digunakan untuk pencarian batch.

    Returns:
        None: Fungsi tidak mengembalikan nilai, hanya menghasilkan file Excel di direktori output.

    Catatan:
        - Jika tidak ada file batch berlabel ditemukan, fungsi hanya memberi peringatan.
        - Jika tidak ada file batch gagal ditemukan, fungsi akan memberi informasi bahwa semua berhasil.
    """
    logging.info("🏁 Memulai proses finalisasi...")
    
    # Proses file yang berhasil dilabeli
    labeled_dir = os.path.join(output_dir, LABELED_SUBDIR)
    labeled_files = glob.glob(os.path.join(labeled_dir, f"{base_name}_batch*_labeled.xlsx"))
    if labeled_files:
        full_labeled_df = pd.concat([pd.read_excel(f) for f in labeled_files], ignore_index=True)
        final_labeled_path = os.path.join(output_dir, f"{base_name}_FULL_labeled.xlsx")
        full_labeled_df.to_excel(final_labeled_path, index=False)
        logging.info(f"✅ Berhasil menggabungkan {len(labeled_files)} batch berlabel ke: {final_labeled_path}")
    else:
        logging.warning("Tidak ada batch berlabel yang ditemukan untuk digabungkan.")

    # Proses file yang gagal (unlabeled)
    unlabeled_dir = os.path.join(output_dir, UNLABELED_SUBDIR)
    unlabeled_files = glob.glob(os.path.join(unlabeled_dir, f"{base_name}_batch*_unlabeled.xlsx"))
    if unlabeled_files:
        full_unlabeled_df = pd.concat([pd.read_excel(f) for f in unlabeled_files], ignore_index=True)
        final_unlabeled_path = os.path.join(output_dir, f"{base_name}_FULL_unlabeled.xlsx")
        full_unlabeled_df.to_excel(final_unlabeled_path, index=False)
        logging.info(f"✅ Berhasil menggabungkan {len(unlabeled_files)} batch GAGAL ke: {final_unlabeled_path}")
    else:
        logging.info("Tidak ada batch yang gagal (unlabeled) untuk digabungkan.")

def label_dataset(df_master: pd.DataFrame, base_name: str, batch_size: int, max_retry: int, generation_config: Dict, text_column_name: str, allowed_labels: List[str], stop_event: threading.Event) -> None:
    """
    Mengorkestrasi proses pelabelan dataset menggunakan model Gemini secara bertahap (per-batch).

    Fungsi ini membagi dataset ke dalam beberapa batch, lalu mengirimkan teks 
    ke model Gemini untuk mendapatkan label dan justifikasi. Hasil pelabelan 
    tiap batch disimpan dalam file Excel terpisah pada direktori `labeled` 
    (jika berhasil) atau `unlabeled` (jika gagal). Setelah semua batch selesai 
    diproses, fungsi akan menggabungkan hasilnya menjadi satu file akhir 
    menggunakan `finalize_results`.

    Fitur tambahan:
    - Validasi label: setiap label hasil prediksi dicek agar sesuai dengan daftar 
      `allowed_labels`. Jika ditemukan label tidak valid, seluruh batch akan diulang.
    - Retry otomatis dengan exponential backoff.
    - Deteksi error terkait token limit.
    - Rotasi API key saat kuota habis.
    - Mendukung penghentian manual melalui `stop_event`.

    Args:
        df_master (pd.DataFrame): DataFrame berisi data mentah yang akan dilabeli.
        base_name (str): Nama dasar file output (digunakan untuk penamaan batch).
        batch_size (int): Jumlah baris data yang diproses dalam satu batch.
        max_retry (int): Batas maksimum percobaan ulang jika gagal memproses batch.
        generation_config (Dict): Konfigurasi generasi untuk model Gemini.
        text_column_name (str): Nama kolom teks pada DataFrame yang akan dilabeli.
        allowed_labels (List[str]): Daftar label yang diizinkan (case-insensitive).
        stop_event (threading.Event): Event untuk menghentikan proses pelabelan secara manual.

    Returns:
        None: Fungsi tidak mengembalikan nilai, tetapi menyimpan file Excel 
        hasil pelabelan (baik per batch maupun file akhir) ke direktori output.

    Raises:
        Exception: Jika terjadi kesalahan yang tidak tertangani saat memproses batch.

    Catatan:
        - Jika ditemukan file hasil akhir (`*_FULL_labeled.xlsx`), proses akan dihentikan.
        - Batch yang gagal karena token limit langsung disimpan ke folder `unlabeled`.
        - Jika label tidak sesuai dengan `allowed_labels`, batch akan diulang.
        - Logging digunakan untuk melacak progres, error, dan retry.
    """
    output_dir_for_project = os.path.join(CONFIG['OUTPUT_DIR'], base_name)
    labeled_dir = os.path.join(output_dir_for_project, LABELED_SUBDIR)
    unlabeled_dir = os.path.join(output_dir_for_project, UNLABELED_SUBDIR)
    
    os.makedirs(labeled_dir, exist_ok=True)
    os.makedirs(unlabeled_dir, exist_ok=True)
    
    logging.info(f"📂 Direktori output proyek: {output_dir_for_project}")
    
    if os.path.exists(os.path.join(output_dir_for_project, f"{base_name}_FULL_labeled.xlsx")):
        logging.warning(f"PEKERJAAN SELESAI. Hapus file di '{output_dir_for_project}' untuk menjalankan ulang.")
        return

    prompt_template = load_prompt_template()
    if "label" not in df_master.columns: df_master["label"] = None
    if "justifikasi" not in df_master.columns: df_master["justifikasi"] = None

    total_rows = len(df_master)
    logging.info("🏁 Memulai proses pelabelan per-batch...")

    # Siapkan set label untuk pengecekan yang efisien (case-insensitive)
    lowercase_allowed_labels = {label.lower() for label in allowed_labels}
    logging.info(f"Label yang divalidasi: {', '.join(allowed_labels)}")
    
    for start in tqdm(range(0, total_rows, batch_size), desc="Overall Progress", unit="batch"):
        if stop_event.is_set():
            logging.warning("Proses dihentikan oleh pengguna.")
            break  

        end = min(start + batch_size, total_rows)
        batch_filename_base = f"{base_name}_batch{start+1:03d}_{end:03d}"
        labeled_filename = os.path.join(labeled_dir, f"{batch_filename_base}_labeled.xlsx")
        unlabeled_filename = os.path.join(unlabeled_dir, f"{batch_filename_base}_unlabeled.xlsx")

        if os.path.exists(labeled_filename) or os.path.exists(unlabeled_filename): continue
        batch_slice = df_master.iloc[start:end]
        if batch_slice['label'].notna().all():
            batch_slice.to_excel(labeled_filename, index=False)
            continue

        tweets_to_process = batch_slice[text_column_name].tolist()
        num_texts = len(tweets_to_process)
        numbered_texts = "\n".join([f"{i+1}. {text}" for i, text in enumerate(tweets_to_process)])

        is_batch_valid = False
        attempts = 0
        token_limit_error_detected = False

        while not is_batch_valid and attempts < max_retry:
            attempts += 1
            prompt = prompt_template.format(num_texts=num_texts, numbered_texts=numbered_texts)
            
            try:
                output = generate_from_gemini(prompt, generation_config)

                # Validasi jumlah output
                if len(output) != num_texts:
                    logging.warning(f"Jumlah output tidak sesuai untuk batch {start+1}-{end}. Diharapkan {num_texts}, diterima {len(output)}. Mencoba lagi...")
                    time.sleep(3)
                    continue
                is_batch_valid = True

                # Validasi setiap label dalam output 
                all_labels_are_valid = True
                for i, line in enumerate(output):
                    try:
                        extracted_label = line.split(" - ", 1)[0].strip()
                        if extracted_label.lower() not in lowercase_allowed_labels:
                            logging.warning(f"Batch {start+1}-{end}, Baris #{i+1}: Ditemukan label tidak valid ('{extracted_label}'). Mencoba ulang seluruh batch...")
                            all_labels_are_valid = False
                            break # Hentikan pengecekan untuk batch ini, langsung retry
                    except IndexError:
                        logging.warning(f"Batch {start+1}-{end}, Baris #{i+1}: Format output salah (tidak ada ' - '). Mencoba ulang seluruh batch...")
                        all_labels_are_valid = False
                        break

                if not all_labels_are_valid:
                    time.sleep(3) # Beri jeda sebelum mencoba lagi
                    continue 

                # Jika semua cek lolos, batch dianggap valid
                is_batch_valid = True
            except Exception as e:
                # Menambahkan logging error dengan traceback 
                logging.error(f"Error pada API Key #{current_key_index + 1} saat memproses batch {start+1}-{end}", exc_info=True)
                error_string = str(e).lower()
                if "max_tokens" in error_string or "finish reason: max_tokens" in error_string:
                    logging.error(f"⛔️ ERROR TOKEN LIMIT! Menyimpan batch {start+1}-{end} sebagai 'unlabeled'...")
                    batch_slice.to_excel(unlabeled_filename, index=False)
                    token_limit_error_detected = True
                    break
                if any(keyword in error_string for keyword in ["quota", "limit", "permission denied"]):
                    rotate_api_key()
                wait_time = (2 ** attempts) + random.random()
                time.sleep(wait_time)

        if is_batch_valid:
            labels, justifications = [], []
            for line in output:
                parts = line.split(" - ", 1)
                labels.append(parts[0].strip())
                justifications.append(parts[1].strip() if len(parts) > 1 else "")
            
            labeled_slice = batch_slice.copy()
            labeled_slice['label'] = labels
            labeled_slice['justifikasi'] = justifications
            labeled_slice.to_excel(labeled_filename, index=False)
        elif not token_limit_error_detected:
            logging.warning(f"Gagal memproses batch {start+1}-{end} setelah {max_retry} percobaan.")

        time.sleep(32)
    
    finalize_results(output_dir_for_project, base_name)
