#!/usr/bin/env python3
"""
list_models.py - Gemini Models Explorer and Information Tool

Skrip utilitas untuk melihat daftar model Gemini yang tersedia,
informasi quota, dan fitur yang didukung oleh setiap model.

Usage:
    python -m src.core_logic.list_models
    python -m src.core_logic.list_models --show-details
    python -m src.core_logic.list_models --check-access

Author: Auto-generated for auto-labeling-data-text-aistudio project
Date: October 2025
"""

import argparse
import os
import sys
from typing import List, Dict, Any
from datetime import datetime

# Third-party imports
import google.generativeai as genai
from dotenv import load_dotenv

# Local imports
try:
    from .env_manager import load_env_variables
except ImportError as e:
    print(f"❌ Error: Tidak dapat mengimpor env_manager: {e}")
    sys.exit(1)


def setup_gemini_api() -> bool:
    """
    Setup Gemini API dengan konfigurasi dari .env file.
    
    Returns:
        bool: True jika berhasil setup, False jika gagal
    """
    try:
        load_dotenv()
        
        # Coba ambil API key dari environment
        api_key = os.getenv('GOOGLE_API_KEY_1')
        if not api_key:
            print("⚠️  Warning: GOOGLE_API_KEY_1 tidak ditemukan di file .env")
            print("   Beberapa fitur tidak akan tersedia tanpa API key.")
            return False
        
        # Konfigurasi Gemini API
        genai.configure(api_key=api_key)
        return True
        
    except Exception as e:
        print(f"❌ Error setup API: {e}")
        return False


def get_predefined_models() -> List[Dict[str, Any]]:
    """
    Mendapatkan daftar model Gemini yang sudah diketahui dengan informasi quota.
    
    Returns:
        List[Dict]: Daftar model dengan informasi lengkap
    """
    # Data model berdasarkan dokumentasi terbaru Gemini (Oktober 2025)
    models = [
        {
            "name": "gemini-2.5-pro",
            "display_name": "Gemini 2.5 Pro",
            "category": "Text-out models", 
            "rpm": 5,
            "tpm": 250000,
            "rpd": 100,
            "description": "Model premium dengan kualitas output terbaik, quota terbatas",
            "best_for": "Tugas kompleks, analisis mendalam, kualitas tertinggi",
            "supported_features": ["text", "json_mode", "function_calling"]
        },
        {
            "name": "gemini-2.5-flash", 
            "display_name": "Gemini 2.5 Flash",
            "category": "Text-out models",
            "rpm": 10,
            "tpm": 250000, 
            "rpd": 250,
            "description": "Balance optimal antara kualitas dan speed",
            "best_for": "Sebagian besar use case, production workload",
            "supported_features": ["text", "json_mode", "function_calling", "vision"]
        },
        {
            "name": "gemini-2.5-flash-preview",
            "display_name": "Gemini 2.5 Flash Preview", 
            "category": "Text-out models",
            "rpm": 10,
            "tpm": 250000,
            "rpd": 250,
            "description": "Preview version dengan fitur experimental",
            "best_for": "Testing fitur baru, development",
            "supported_features": ["text", "json_mode", "function_calling", "vision", "experimental"]
        },
        {
            "name": "gemini-2.5-flash-lite",
            "display_name": "Gemini 2.5 Flash-Lite",
            "category": "Text-out models", 
            "rpm": 15,
            "tpm": 250000,
            "rpd": 1000,
            "description": "High throughput dengan quota besar",
            "best_for": "Batch processing, high volume tasks",
            "supported_features": ["text", "json_mode"]
        },
        {
            "name": "gemini-2.5-flash-lite-preview",
            "display_name": "Gemini 2.5 Flash-Lite Preview",
            "category": "Text-out models",
            "rpm": 15, 
            "tpm": 250000,
            "rpd": 1000,
            "description": "Preview version dari Flash-Lite",
            "best_for": "Testing high volume scenarios",
            "supported_features": ["text", "json_mode", "experimental"]
        },
        {
            "name": "gemini-2.0-flash",
            "display_name": "Gemini 2.0 Flash", 
            "category": "Text-out models",
            "rpm": 15,
            "tpm": 1000000,
            "rpd": 200,
            "description": "High token limit dengan speed tinggi",
            "best_for": "Long context tasks, document analysis",
            "supported_features": ["text", "json_mode", "long_context"]
        },
        {
            "name": "gemini-2.0-flash-lite",
            "display_name": "Gemini 2.0 Flash-Lite",
            "category": "Text-out models",
            "rpm": 30,
            "tpm": 1000000, 
            "rpd": 200,
            "description": "Fastest model dengan very high RPM",
            "best_for": "Real-time applications, speed critical tasks",
            "supported_features": ["text", "json_mode", "real_time"]
        },
        # Legacy models untuk backward compatibility
        {
            "name": "gemini-1.5-pro-latest",
            "display_name": "Gemini 1.5 Pro Latest",
            "category": "Legacy models",
            "rpm": 2,
            "tpm": 125000,
            "rpd": 50,
            "description": "Legacy model, masih didukung untuk backward compatibility",
            "best_for": "Existing projects, migration planning",
            "supported_features": ["text", "json_mode", "function_calling", "vision"]
        },
        {
            "name": "gemini-1.5-flash-latest", 
            "display_name": "Gemini 1.5 Flash Latest",
            "category": "Legacy models",
            "rpm": 5,
            "tpm": 125000,
            "rpd": 100,
            "description": "Legacy flash model",
            "best_for": "Migration dari 1.5 ke 2.x",
            "supported_features": ["text", "json_mode", "vision"]
        }
    ]
    
    return models


def get_available_models_from_api() -> List[Dict[str, Any]]:
    """
    Mendapatkan daftar model yang tersedia langsung dari Gemini API.
    
    Returns:
        List[Dict]: Daftar model dari API
    """
    try:
        models = []
        for model in genai.list_models():
            if 'generateContent' in model.supported_generation_methods:
                models.append({
                    "name": model.name.replace('models/', ''),
                    "display_name": model.display_name,
                    "description": model.description or "No description available",
                    "supported_methods": model.supported_generation_methods,
                    "input_token_limit": getattr(model, 'input_token_limit', 'Unknown'),
                    "output_token_limit": getattr(model, 'output_token_limit', 'Unknown')
                })
        return models
    except Exception as e:
        print(f"⚠️  Warning: Tidak dapat mengambil daftar model dari API: {e}")
        return []


def print_models_table(models: List[Dict[str, Any]], show_details: bool = False) -> None:
    """
    Menampilkan daftar model dalam format tabel yang rapi.
    
    Args:
        models: Daftar model untuk ditampilkan
        show_details: True untuk menampilkan detail lengkap
    """
    print("\n" + "="*100)
    print("🤖 DAFTAR MODEL GEMINI YANG TERSEDIA")
    print("="*100)
    
    if show_details:
        # Mode detail - tampilkan informasi lengkap
        for i, model in enumerate(models, 1):
            print(f"\n📋 {i}. {model['display_name']}")
            print(f"   Model Name    : {model['name']}")
            print(f"   Category      : {model.get('category', 'Unknown')}")
            
            if 'rpm' in model:
                print(f"   Quota Limits  : {model['rpm']} RPM | {model['tpm']:,} TPM | {model['rpd']} RPD")
            
            print(f"   Description   : {model.get('description', 'No description')}")
            print(f"   Best For      : {model.get('best_for', 'General use')}")
            
            if 'supported_features' in model:
                features = ', '.join(model['supported_features'])
                print(f"   Features      : {features}")
            
            if 'input_token_limit' in model:
                print(f"   Token Limits  : Input={model['input_token_limit']} | Output={model['output_token_limit']}")
                
    else:
        # Mode ringkas - tabel kompak
        print(f"\n{'No.':<4} {'Model Name':<35} {'RPM':<5} {'TPM':<8} {'RPD':<6} {'Category':<15}")
        print("-" * 100)
        
        for i, model in enumerate(models, 1):
            rpm = model.get('rpm', '?')
            tpm = f"{model.get('tpm', 0):,}" if model.get('tpm') else '?'
            rpd = model.get('rpd', '?')
            category = model.get('category', 'Unknown')[:14]
            
            print(f"{i:<4} {model['name']:<35} {rpm:<5} {tpm:<8} {rpd:<6} {category:<15}")


def print_recommendations() -> None:
    """
    Menampilkan rekomendasi pemilihan model berdasarkan use case.
    """
    print("\n" + "="*100)
    print("💡 REKOMENDASI PEMILIHAN MODEL")
    print("="*100)
    
    recommendations = [
        {
            "use_case": "🎯 Kualitas Tertinggi (Budget Tidak Terbatas)",
            "models": ["gemini-2.5-pro"],
            "notes": "RPD rendah (100), cocok untuk dataset kecil premium"
        },
        {
            "use_case": "⚖️ Balance Kualitas & Throughput (Recommended)",
            "models": ["gemini-2.5-flash", "gemini-2.5-flash-preview"],
            "notes": "RPD sedang (250), ideal untuk sebagian besar project"
        },
        {
            "use_case": "🚀 High Volume Processing",
            "models": ["gemini-2.5-flash-lite", "gemini-2.5-flash-lite-preview"],
            "notes": "RPD tinggi (1000), optimal untuk dataset besar"
        },
        {
            "use_case": "📄 Long Context Documents",
            "models": ["gemini-2.0-flash"],
            "notes": "TPM tinggi (1M), cocok untuk dokumen panjang"
        },
        {
            "use_case": "⚡ Speed Critical Applications",
            "models": ["gemini-2.0-flash-lite"],
            "notes": "RPM tertinggi (30), real-time processing"
        },
        {
            "use_case": "🔄 Migration dari 1.5.x",
            "models": ["gemini-1.5-pro-latest", "gemini-1.5-flash-latest"],
            "notes": "Backward compatibility, akan deprecated"
        }
    ]
    
    for rec in recommendations:
        print(f"\n{rec['use_case']}")
        models_str = ', '.join(rec['models'])
        print(f"   Models: {models_str}")
        print(f"   Notes : {rec['notes']}")


def check_model_access(models: List[Dict[str, Any]]) -> None:
    """
    Memeriksa akses ke setiap model dan menampilkan status.
    
    Args:
        models: Daftar model untuk dicek
    """
    print("\n" + "="*100)
    print("🔍 CEK AKSES MODEL (MEMERLUKAN API KEY)")
    print("="*100)
    
    if not setup_gemini_api():
        print("❌ Tidak dapat melakukan cek akses tanpa API key yang valid.")
        return
    
    print(f"\n{'Model Name':<35} {'Status':<15} {'Notes'}")
    print("-" * 80)
    
    for model in models[:5]:  # Test hanya beberapa model untuk menghindari rate limit
        try:
            # Coba inisialisasi model
            test_model = genai.GenerativeModel(model['name'])
            
            # Coba count tokens sebagai test ringan
            test_response = test_model.count_tokens("test")
            
            status = "✅ Accessible"
            notes = f"Token counted: {test_response.total_tokens}"
            
        except Exception as e:
            status = "❌ Error"
            error_msg = str(e)
            if "not found" in error_msg.lower():
                notes = "Model not found"
            elif "permission" in error_msg.lower():
                notes = "No permission"
            elif "quota" in error_msg.lower():
                notes = "Quota exceeded"
            else:
                notes = f"Error: {error_msg[:30]}..."
        
        print(f"{model['name']:<35} {status:<15} {notes}")
    
    print(f"\n💡 Tip: Untuk cek lengkap semua model, gunakan script terpisah untuk menghindari rate limit.")


def generate_fallback_config(models: List[Dict[str, Any]]) -> None:
    """
    Generate konfigurasi MODEL_FALLBACK_LIST yang optimal.
    """
    print("\n" + "="*100)
    print("🔧 KONFIGURASI MODEL FALLBACK YANG DISARANKAN")
    print("="*100)
    
    # Filter hanya model yang aktif (bukan legacy)
    active_models = [m for m in models if m.get('category') != 'Legacy models']
    
    # Sort berdasarkan kualitas vs throughput
    sorted_models = sorted(active_models, key=lambda x: (
        -x.get('rpd', 0),  # RPD tinggi lebih baik untuk fallback
        x.get('rpm', 999)  # RPM rendah = kualitas lebih tinggi
    ))
    
    # Buat beberapa konfigurasi untuk use case berbeda
    configs = {
        "Quality First (Recommended)": [
            "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash-lite"
        ],
        "Balanced": [
            "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-2.0-flash-lite"
        ],
        "High Volume": [
            "gemini-2.5-flash-lite", "gemini-2.0-flash-lite", "gemini-2.0-flash", "gemini-2.5-flash"
        ],
        "Legacy Support": [
            "gemini-1.5-pro-latest", "gemini-1.5-flash-latest", "gemini-2.5-flash", "gemini-2.5-flash-lite"
        ]
    }
    
    print("\n📝 Copy salah satu konfigurasi berikut ke file .env Anda:\n")
    
    for config_name, model_list in configs.items():
        print(f"# {config_name}")
        models_str = ','.join(model_list)
        print(f'MODEL_FALLBACK_LIST="{models_str}"')
        print()


def main():
    """
    Fungsi main untuk parsing argumen dan menjalankan tool.
    """
    parser = argparse.ArgumentParser(
        description="Gemini Models Explorer - Lihat daftar model dan informasi quota",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Contoh penggunaan:
  python -m src.core_logic.list_models                     # Tampilkan daftar model
  python -m src.core_logic.list_models --show-details      # Detail lengkap setiap model
  python -m src.core_logic.list_models --check-access      # Cek akses ke model (perlu API key)
  python -m src.core_logic.list_models --generate-config   # Generate fallback config
        """
    )
    
    parser.add_argument(
        '--show-details',
        action='store_true',
        help='Tampilkan informasi detail untuk setiap model'
    )
    
    parser.add_argument(
        '--check-access',
        action='store_true',
        help='Cek akses ke setiap model (memerlukan API key)'
    )
    
    parser.add_argument(
        '--generate-config',
        action='store_true',
        help='Generate konfigurasi MODEL_FALLBACK_LIST yang optimal'
    )
    
    parser.add_argument(
        '--api-only',
        action='store_true',
        help='Hanya tampilkan model dari API (bukan predefined list)'
    )
    
    args = parser.parse_args()
    
    print(f"🚀 Gemini Models Explorer - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Ambil daftar model
    if args.api_only:
        if setup_gemini_api():
            models = get_available_models_from_api()
            if not models:
                print("❌ Tidak dapat mengambil daftar model dari API.")
                return
        else:
            print("❌ API key diperlukan untuk mode --api-only.")
            return
    else:
        models = get_predefined_models()
        
        # Tambah info dari API jika tersedia
        if setup_gemini_api():
            api_models = get_available_models_from_api()
            if api_models:
                print(f"ℹ️  Informasi dari API: {len(api_models)} model tersedia di akun Anda.")
    
    # Tampilkan daftar model
    print_models_table(models, show_details=args.show_details)
    
    # Fitur tambahan
    if args.check_access:
        check_model_access(models)
    
    if args.generate_config:
        generate_fallback_config(models)
    
    # Selalu tampilkan rekomendasi
    if not args.api_only:
        print_recommendations()
    
    print(f"\n✅ Selesai. Total {len(models)} model ditampilkan.")
    print("💡 Gunakan --help untuk melihat opsi lainnya.")


if __name__ == "__main__":
    main()