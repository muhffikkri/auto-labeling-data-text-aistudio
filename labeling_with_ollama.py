import pandas as pd
import ollama
import os
import argparse
import time
from tqdm import tqdm
import sys

# --- Bagian Pengecekan GPU (Sangat Penting) ---
# Sebelum menjalankan skrip ini, pastikan layanan Ollama Anda dapat mendeteksi GPU.
# Buka Terminal baru dan jalankan:
#
# nvidia-smi -l 1
#
# Lalu jalankan skrip Python ini. Perhatikan output dari 'nvidia-smi'.
# Jika GPU Anda bekerja, Anda akan melihat:
#   - 'GPU-Util' naik dari 0%.
#   - 'Memory-Usage' meningkat beberapa GB.
#   - Proses 'ollama' muncul di daftar proses.
#
# Jika hal di atas tidak terjadi, layanan Ollama Anda berjalan di CPU.
# Solusi paling umum adalah:
#   1. Update driver NVIDIA Anda ke versi terbaru.
#   2. Instal ulang Ollama dari situs resminya.
# ----------------------------------------------------

def parse_model_output(raw_output: str) -> str:
    """
    Membersihkan output model dari blok <think>...</think>.
    """
    think_end_tag = "</think>"
    if think_end_tag in raw_output:
        try:
            final_answer = raw_output.split(think_end_tag, 1)[1]
            return final_answer.strip()
        except IndexError:
            return ""
    else:
        return raw_output.strip()

def ollama_generate_single(prompt: str, model_name: str, temperature: float = 0.5, max_retry: int = 3) -> tuple[str | None, str | None]:
    """
    Mengirimkan prompt ke Ollama, meminta penggunaan GPU, dan memvalidasi output.
    """
    allowed_labels = ["POSITIF", "NEGATIF", "NETRAL", "TIDAK RELEVAN"]
    
    for attempt in range(max_retry):
        try:
            # --- MODIFIKASI KUNCI ADA DI SINI ---
            response = ollama.generate(
                model=model_name,
                prompt=prompt,
                options={
                    'temperature': temperature,
                    'num_gpu': 999  # Minta Ollama untuk memuat semua layer ke GPU
                }
            )
            # ------------------------------------
            
            raw_output = response['response']
            output_line = parse_model_output(raw_output)

            if " - " not in output_line:
                time.sleep(1)
                continue

            parts = output_line.split(" - ", 1)
            label = parts[0].strip()
            justification = parts[1].strip() if len(parts) > 1 else ""

            if label not in allowed_labels:
                time.sleep(1)
                continue
            
            return label, justification

        except Exception as e:
            # Cek jika error karena model tidak ditemukan
            if "model" in str(e) and "not found" in str(e):
                 print(f"\n❌ FATAL ERROR: Model '{model_name}' tidak ditemukan oleh Ollama.")
                 print(f"   Pastikan Anda sudah menjalankan 'ollama pull {model_name}' di terminal.")
                 sys.exit(1) # Keluar dari skrip
            
            print(f"\n❌ Error saat request ke Ollama (Percobaan {attempt+1}): {e}")
            time.sleep(3)

    return None, None

def labeling(df_path: str, model_name: str):
    """
    Fungsi utama untuk melabeli dataset baris per baris dengan checkpoint.
    """
    
    base_name = os.path.splitext(os.path.basename(df_path))[0]
    output_dir = os.path.join("results", base_name)
    os.makedirs(output_dir, exist_ok=True)
    
    progress_path = os.path.join(output_dir, f"{base_name}_progress.xlsx")
    final_path = os.path.join(output_dir, f"{base_name}_full_labeled.xlsx")

    print(f"📂 Direktori output: {output_dir}")

    if os.path.exists(final_path):
        print(f"\n✅ PEKERJAAN SELESAI: File final '{os.path.basename(final_path)}' sudah ada.")
        return

    start_index = 0
    if os.path.exists(progress_path):
        print(f"📖 Melanjutkan progres dari checkpoint: {os.path.basename(progress_path)}")
        df_progress = pd.read_excel(progress_path)
        last_labeled_index = df_progress['label'].last_valid_index()
        if last_labeled_index is not None:
            start_index = last_labeled_index + 1
    else:
        print(f"📖 Memulai pekerjaan baru dari: {os.path.basename(df_path)}")
        try:
            df_master = pd.read_excel(df_path)
            df_progress = df_master.copy()
            if 'label' not in df_progress.columns: df_progress['label'] = pd.NA
            if 'justifikasi' not in df_progress.columns: df_progress['justifikasi'] = pd.NA
        except Exception as e:
            print(f"❌ Gagal memuat file Excel sumber: {e}")
            return
            
    if start_index >= len(df_progress):
        print("✅ Semua baris sudah diproses. Merapikan...")
        os.rename(progress_path, final_path)
        print(f"🎉 Pekerjaan Selesai! Hasil akhir disimpan di: {final_path}")
        return

    print(f"\n🚀 Memulai pelabelan dari baris ke-{start_index + 1}...")

    total_rows = len(df_progress)
    for index, row in tqdm(df_progress.iloc[start_index:].iterrows(), total=total_rows - start_index, desc="Melabeli Baris"):
        
        if pd.notna(row['label']):
            continue

        text_to_label = row["full_text"]

        prompt = f"""
        <think>
        Tugas saya adalah menganalisis tweet dan mengklasifikasikannya ke dalam salah satu dari empat kategori (POSITIF, NEGATIF, NETRAL, TIDAK RELEVAN) terkait konteks universitas. Saya harus memberikan label dan justifikasi singkat dalam format yang ketat: `LABEL - Justifikasi`.
        
        Langkah-langkah saya:
        1.  Baca tweet dengan cermat: "{text_to_label}"
        2.  Identifikasi apakah ada penyebutan universitas secara eksplisit atau implisit yang kuat. Jika tidak, labelnya adalah TIDAK RELEVAN.
        3.  Jika relevan, evaluasi sentimennya. Apakah itu pujian (POSITIF), keluhan (NEGATIF), atau hanya informasi/pertanyaan (NETRAL)?
        4.  Rumuskan justifikasi singkat yang mendukung label pilihan saya.
        5.  Format output saya persis seperti yang diinstruksikan tanpa tambahan apa pun.
        </think>
        """

        label, justification = ollama_generate_single(prompt, model_name)

        if label and justification:
            df_progress.loc[index, 'label'] = label
            df_progress.loc[index, 'justifikasi'] = justification
            df_progress.to_excel(progress_path, index=False)
        else:
            print(f"\n⚠️ Gagal melabeli baris ke-{index + 1}. Melewati untuk sementara.")
            continue
    
    os.rename(progress_path, final_path)
    print(f"\n🎉 Pekerjaan Selesai! Hasil akhir disimpan di: {final_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="""
        Skrip pelabelan data otomatis (GPU-Aware) baris-per-baris menggunakan model AI lokal via Ollama.
        """,
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "filename", 
        type=str, 
        help="Nama dasar file dataset di folder 'dataset' (tanpa .xlsx)."
    )
    parser.add_argument(
        "--model", 
        type=str, 
        default="deepseek-coder:6.7b", 
        help="Nama model Ollama yang akan digunakan. Contoh: 'llama3:8b'"
    )

    args = parser.parse_args()

    # --- Pesan Peringatan Saat Skrip Dijalankan ---
    print("============================== PERINGATAN GPU ==============================")
    print("Skrip ini akan meminta Ollama untuk menggunakan GPU.")
    print("Silakan pantau penggunaan GPU Anda menggunakan 'nvidia-smi' di terminal lain.")
    print("Jika utilisasi GPU tidak naik, Ollama Anda mungkin berjalan dalam mode CPU.")
    print("============================================================================")
    time.sleep(3) # Beri waktu bagi pengguna untuk membaca

    os.makedirs("dataset", exist_ok=True)
    os.makedirs("results", exist_ok=True)
    
    dataset_path = f"dataset/{args.filename}.xlsx"

    if not os.path.exists(dataset_path):
        print(f"❌ Error: File dataset tidak ditemukan di '{dataset_path}'")
    else:
        labeling(df_path=dataset_path, model_name=args.model)