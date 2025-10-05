#!/usr/bin/env python3
"""
check_tokens.py - Token Analysis and Cost Estimation Tool

Skrip utilitas mandiri untuk menganalisis jumlah token dan estimasi biaya
untuk proses pelabelan data menggunakan Gemini API tanpa mengeluarkan biaya.

Usage:
    python check_tokens.py --dataset nama_dataset --column tweet_text --batch-size 300

Author: Auto-generated for auto-labeling-data-text-aistudio project
Date: October 2025
"""

import argparse
import os
import json
import logging
import sys
from typing import Dict, Any

# Third-party imports
import google.generativeai as genai
import pandas as pd
from dotenv import load_dotenv

# Import fungsi yang sudah ada dari proyek (code reusability)
try:
    from .process import open_dataset, load_prompt_template
    from .env_manager import load_env_variables
    from .request_tracker import log_request
except ImportError as e:
    print(f"❌ Error: Tidak dapat mengimpor modul dari core_logic.")
    print(f"   Detail error: {e}")
    sys.exit(1)

# Konfigurasi logging sederhana untuk skrip ini
logging.basicConfig(level=logging.WARNING)  # Hanya tampilkan warning dan error


def setup_gemini_api() -> str:
    """
    Setup Gemini API dengan menggunakan konfigurasi dari .env file.
    
    Returns:
        str: Nama model yang digunakan
        
    Raises:
        ValueError: Jika API key tidak ditemukan
    """
    load_dotenv()
    
    # Coba ambil API key dari environment
    api_key = os.getenv('GOOGLE_API_KEY_1')
    if not api_key:
        raise ValueError("❌ GOOGLE_API_KEY_1 tidak ditemukan di file .env")
    
    # Konfigurasi Gemini API
    genai.configure(api_key=api_key)
    
    # Ambil model name dari environment atau gunakan default
    model_name = os.getenv('MODEL_NAME', 'gemini-1.5-pro-latest')
    
    return model_name


def create_sample_prompt(df_sample: pd.DataFrame, text_column: str) -> str:
    """
    Membuat prompt sampel yang identik dengan yang digunakan dalam proses pelabelan utama.
    
    Args:
        df_sample: DataFrame sampel untuk dianalisis
        text_column: Nama kolom yang berisi teks
        
    Returns:
        str: Prompt yang sudah diformat
    """
    # Pastikan ada kolom 'id'
    if 'id' not in df_sample.columns:
        df_sample = df_sample.copy()
        df_sample['id'] = range(len(df_sample))
    
    # Siapkan data dalam format yang sama dengan proses utama
    data_to_process = df_sample[['id', text_column]].to_dict(orient='records')
    data_json_string = json.dumps(data_to_process, indent=2, ensure_ascii=False)
    
    # Load template prompt (menggunakan fungsi yang sudah ada)
    try:
        prompt_template = load_prompt_template()
        # Escape curly braces untuk mencegah format error
        prompt_template = prompt_template.replace('{', '{{').replace('}', '}}')
        # Kembalikan placeholder data_json
        prompt_template = prompt_template.replace('{{data_json}}', '{data_json}')
    except FileNotFoundError:
        print("⚠️  Warning: File prompt_template.txt tidak ditemukan.")
        print("   Menggunakan template default untuk analisis...")
        prompt_template = """
Analisis sentimen untuk data berikut dalam format JSON:

{data_json}

Berikan hasil dalam format JSON array dengan struktur:
[
  {{"id": 0, "label": "POSITIF/NEGATIF/NETRAL", "justifikasi": "alasan singkat"}},
  ...
]
"""
    
    # Format prompt dengan data JSON
    full_prompt = prompt_template.format(data_json=data_json_string)
    
    return full_prompt


def calculate_token_metrics(model: Any, prompt: str, total_rows: int, batch_size: int) -> Dict[str, Any]:
    """
    Menghitung metrik token dan estimasi biaya.
    
    Args:
        model: Model Gemini yang sudah diinisialisasi
        prompt: Prompt yang akan dianalisis
        total_rows: Total baris dalam dataset
        batch_size: Ukuran batch
        
    Returns:
        Dict dengan metrik token dan biaya
    """
    # Hitung token untuk prompt sampel dengan tracking
    import time
    start_time = time.time()
    request_successful = False
    error_message = None
    
    try:
        token_count = model.count_tokens(prompt)
        input_tokens = token_count.total_tokens
        request_successful = True
        
        # Log request untuk tracking
        log_request(
            api_key_index=1,  # Asumsi menggunakan API key pertama
            model_name=model.model_name,
            success=True,
            response_time=time.time() - start_time,
            batch_info=f"Token analysis for {total_rows} rows, batch_size={batch_size}",
            tokens_used=input_tokens
        )
        
        # Force save untuk persistence
        from .request_tracker import get_request_tracker
        get_request_tracker()._save_session_stats()
        
    except Exception as e:
        error_message = f"Gagal menghitung token: {e}"
        print(f"⚠️  Warning: {error_message}")
        # Fallback: estimasi berdasarkan panjang karakter (rough estimation)
        input_tokens = len(prompt) // 4  # Rough estimate: 1 token ≈ 4 characters
        print(f"   Menggunakan estimasi berdasarkan panjang karakter: {input_tokens} token")
        
        # Log failed request
        log_request(
            api_key_index=1,
            model_name=model.model_name,
            success=False,
            response_time=time.time() - start_time,
            error_message=error_message,
            batch_info=f"Token analysis (fallback) for {total_rows} rows, batch_size={batch_size}"
        )
        
        # Force save untuk persistence
        from .request_tracker import get_request_tracker
        get_request_tracker()._save_session_stats()
    
    # Hitung metrik batch dan total
    total_batches = (total_rows + batch_size - 1) // batch_size  # Ceiling division
    total_input_tokens = input_tokens * total_batches
    
    # Estimasi biaya (berdasarkan pricing Gemini per Oktober 2025)
    # Asumsi: $3.50 per 1 juta input token untuk Gemini 1.5 Pro
    cost_per_million_tokens = 3.50
    cost_per_batch = (input_tokens / 1_000_000) * cost_per_million_tokens
    total_estimated_cost = (total_input_tokens / 1_000_000) * cost_per_million_tokens
    
    return {
        'input_tokens_per_batch': input_tokens,
        'total_batches': total_batches,
        'total_input_tokens': total_input_tokens,
        'cost_per_batch': cost_per_batch,
        'total_estimated_cost': total_estimated_cost,
        'cost_per_million_tokens': cost_per_million_tokens
    }


def generate_token_report(
    dataset_name: str,
    column_name: str,
    total_rows: int,
    sample_rows: int,
    model_name: str,
    batch_size: int,
    metrics: Dict[str, Any]
) -> str:
    """
    Menghasilkan laporan analisis token dan biaya dalam format string untuk GUI.
    
    Args:
        dataset_name: Nama dataset
        column_name: Nama kolom teks
        total_rows: Total baris dalam dataset
        sample_rows: Jumlah baris sampel yang dianalisis
        model_name: Nama model yang digunakan
        batch_size: Ukuran batch
        metrics: Metrik dari calculate_token_metrics
        
    Returns:
        str: Laporan terformat untuk ditampilkan di GUI
    """
    report = []
    report.append("="*70)
    report.append("🔍 LAPORAN ANALISIS TOKEN DAN ESTIMASI BIAYA")
    report.append("="*70)
    
    report.append("\n📊 INFORMASI DATASET:")
    report.append(f"   Dataset               : {dataset_name}")
    report.append(f"   Kolom Teks            : {column_name}")
    report.append(f"   Total Baris           : {total_rows:,}")
    report.append(f"   Baris Sampel Dianalisis: {sample_rows}")
    
    report.append("\n🎯 KONFIGURASI PEMROSESAN:")
    report.append(f"   Model Gemini          : {model_name}")
    report.append(f"   Ukuran Batch          : {batch_size}")
    report.append(f"   Total Batch Diperlukan: {metrics['total_batches']}")
    
    report.append("\n🔢 ANALISIS TOKEN:")
    report.append(f"   Token Input per Batch : {metrics['input_tokens_per_batch']:,}")
    report.append(f"   Total Token Input     : {metrics['total_input_tokens']:,}")
    
    report.append("\n💰 ESTIMASI BIAYA (INPUT TOKEN SAJA):")
    report.append(f"   Harga per 1M Token   : ${metrics['cost_per_million_tokens']:.2f}")
    report.append(f"   Biaya per Batch      : ${metrics['cost_per_batch']:.4f}")
    report.append(f"   Total Estimasi Biaya : ${metrics['total_estimated_cost']:.2f}")
    
    report.append("\n⚠️  CATATAN PENTING:")
    report.append("   • Ini HANYA menghitung token INPUT (prompt)")
    report.append("   • Biaya OUTPUT token belum termasuk (biasanya lebih mahal)")
    report.append("   • Estimasi berdasarkan pricing Gemini 1.5 Pro")
    report.append("   • Biaya sebenarnya dapat bervariasi tergantung model dan region")
    report.append("   • Untuk estimasi yang lebih akurat, gunakan beberapa sampel batch")
    
    report.append("\n" + "="*70)
    report.append("✅ Analisis selesai. Gunakan informasi ini untuk perencanaan biaya.")
    report.append("="*70)
    
    return "\n".join(report)


def print_analysis_report(
    model_name: str,
    dataset_name: str,
    text_column: str,
    batch_size: int,
    total_rows: int,
    sample_rows: int,
    metrics: Dict[str, Any]
) -> None:
    """
    Menampilkan laporan analisis yang terformat dengan baik.
    """
    # Gunakan generate_token_report untuk konsistensi
    report = generate_token_report(
        dataset_name=dataset_name,
        column_name=text_column,
        total_rows=total_rows,
        sample_rows=sample_rows,
        model_name=model_name,
        batch_size=batch_size,
        metrics=metrics
    )
    print(report)


def analyze_tokens(dataset_name: str, text_column: str, batch_size: int) -> None:
    """
    Fungsi utama untuk menganalisis token dan estimasi biaya.
    
    Args:
        dataset_name: Nama dataset (tanpa ekstensi)
        text_column: Nama kolom teks yang akan dianalisis
        batch_size: Ukuran batch untuk simulasi
    """
    try:
        print(f"🚀 Memulai analisis token untuk dataset '{dataset_name}'...")
        
        # 1. Setup Gemini API
        print("🔧 Mengatur konfigurasi Gemini API...")
        model_name = setup_gemini_api()
        model = genai.GenerativeModel(model_name)
        
        # 2. Load dataset
        print(f"📂 Memuat dataset dari direktori...")
        try:
            # Coba ambil dataset directory dari environment, atau gunakan default
            dataset_dir = os.getenv('DATASET_DIR', 'dataset')
            df, dataset_path = open_dataset(dataset_dir, dataset_name)
        except FileNotFoundError:
            # Fallback: coba dari direktori saat ini
            df, dataset_path = open_dataset('.', dataset_name)
        
        print(f"   Dataset dimuat: {dataset_path}")
        print(f"   Total baris: {len(df):,}")
        
        # 3. Validasi kolom teks
        if text_column not in df.columns:
            available_columns = ', '.join(df.columns.tolist())
            raise ValueError(f"Kolom '{text_column}' tidak ditemukan. Kolom tersedia: {available_columns}")
        
        # 4. Ambil sampel batch pertama
        sample_size = min(batch_size, len(df))
        df_sample = df.head(sample_size).copy()
        print(f"   Menganalisis {sample_size} baris pertama sebagai sampel...")
        
        # 5. Buat prompt sampel
        print("📝 Membuat prompt sampel...")
        sample_prompt = create_sample_prompt(df_sample, text_column)
        
        # Debug info: tampilkan preview prompt (truncated)
        prompt_preview = sample_prompt[:200] + "..." if len(sample_prompt) > 200 else sample_prompt
        print(f"   Preview prompt: {prompt_preview}")
        
        # 6. Hitung token dan metrik
        print("🔢 Menghitung token dan estimasi biaya...")
        metrics = calculate_token_metrics(model, sample_prompt, len(df), batch_size)
        
        # 7. Tampilkan laporan
        print_analysis_report(
            model_name=model_name,
            dataset_name=dataset_name,
            text_column=text_column,
            batch_size=batch_size,
            total_rows=len(df),
            sample_rows=sample_size,
            metrics=metrics
        )
        
    except FileNotFoundError as e:
        print(f"❌ Error: Dataset tidak ditemukan.")
        print(f"   Detail: {e}")
        print(f"   Pastikan file '{dataset_name}.csv' atau '{dataset_name}.xlsx' ada di direktori dataset.")
        sys.exit(1)
        
    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ Error tidak terduga: {e}")
        print(f"   Tipe error: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """
    Fungsi main untuk parsing argumen command-line dan menjalankan analisis.
    """
    parser = argparse.ArgumentParser(
        description="Token Analysis and Cost Estimation Tool untuk Auto-Labeling Project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Contoh penggunaan:
  python check_tokens.py --dataset my_tweets --column tweet_text --batch-size 300
  python check_tokens.py --dataset survey_data --column response_text --batch-size 100
  python check_tokens.py --dataset feedback --column comment
        """
    )
    
    parser.add_argument(
        '--dataset',
        type=str,
        required=True,
        help='Nama file dataset (tanpa ekstensi .csv/.xlsx). Contoh: my_tweets'
    )
    
    parser.add_argument(
        '--column',
        type=str,
        required=True,
        help='Nama kolom di dalam dataset yang berisi teks untuk dianalisis. Contoh: tweet_text'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=300,
        help='Ukuran batch untuk disimulasikan (default: 300)'
    )
    
    # Parse argumen
    args = parser.parse_args()
    
    # Validasi argumen
    if args.batch_size <= 0:
        print("❌ Error: Batch size harus lebih besar dari 0")
        sys.exit(1)
    
    # Jalankan analisis
    analyze_tokens(
        dataset_name=args.dataset,
        text_column=args.column,
        batch_size=args.batch_size
    )


if __name__ == "__main__":
    main()