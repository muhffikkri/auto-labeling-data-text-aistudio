import pandas as pd
from dotenv import load_dotenv
import os
import google.generativeai as genai
import time
from tqdm import tqdm
import glob
import re
import argparse
import random

# --- MANAJEMEN MULTIPLE API KEY ---
load_dotenv()
API_KEYS = []
i = 1
while True:
    key = os.getenv(f'GOOGLE_API_KEY_{i}')
    if key:
        API_KEYS.append(key)
        i += 1
    else:
        break
if not API_KEYS:
    raise ValueError("❌ Tidak ada API Key. Pastikan file .env berisi setidaknya GOOGLE_API_KEY_1")
print(f"🔑 Ditemukan {len(API_KEYS)} API Key untuk digunakan dalam rotasi.")
current_key_index = 0
genai.configure(api_key=API_KEYS[current_key_index])

def rotate_api_key():
    """Beralih ke API key berikutnya dalam daftar."""
    global current_key_index
    current_key_index = (current_key_index + 1) % len(API_KEYS)
    print(f"\n⚠️ Merotasi ke API Key #{current_key_index + 1}...")
    new_key = API_KEYS[current_key_index]
    genai.configure(api_key=new_key)

# ---------------------------------------------------

def genai_generate(prompt="", temperature=1.0, top_p=1.0, top_k=40)->list[str]:
    """
    Mengirimkan prompt ke model dan menangani respons kosong dengan aman.
    """
    # Menggunakan model yang lebih baru dan stabil
    model = genai.GenerativeModel("gemini-2.5-pro")
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                top_p=top_p,
                top_k=top_k
            )
        )
        
        # Validasi krusial untuk mencegah crash karena respons kosong (MAX_TOKENS)
        if not response.parts:
            finish_reason = "UNKNOWN"
            # Coba dapatkan alasan finish dari kandidat pertama jika ada
            if response.candidates:
                finish_reason = response.candidates[0].finish_reason.name
            raise ValueError(f"Respons tidak berisi konten. Finish Reason: {finish_reason}")

        output = response.text.strip().split("\n")
        return output
    except Exception as e:
        raise Exception(f"Error saat request API: {e}")

def open_dataset(__path__):
    """Membaca file Excel dan memuatnya ke dalam DataFrame pandas."""
    try:
        df = pd.read_excel(rf"{__path__}")
        return df
    except FileNotFoundError:
        raise NameError(f"Error: File not found at '{__path__}'")
    except Exception as e:
        raise Exception(f"Error reading file '{__path__}': {e}")

def finalize_results(output_dir, base_name):
    """
    Menggabungkan semua file batch (labeled dan unlabeled) menjadi dua file akhir.
    """
    print("\n🏁 Memulai proses finalisasi...")
    
    # --- Proses file yang berhasil dilabeli ---
    labeled_files = glob.glob(os.path.join(output_dir, f"{base_name}_batch*_labeled.xlsx"))
    if labeled_files:
        df_list = [pd.read_excel(f) for f in labeled_files]
        full_labeled_df = pd.concat(df_list, ignore_index=True)
        final_labeled_path = os.path.join(output_dir, f"{base_name}_FULL_labeled.xlsx")
        full_labeled_df.to_excel(final_labeled_path, index=False)
        print(f"✅ Berhasil menggabungkan {len(labeled_files)} batch berlabel ke: {final_labeled_path}")
    else:
        print("⚠️ Tidak ada batch berlabel yang ditemukan untuk digabungkan.")

    # --- Proses file yang gagal (unlabeled) ---
    unlabeled_dir = os.path.join(output_dir, "unlabeled")
    unlabeled_files = glob.glob(os.path.join(unlabeled_dir, f"{base_name}_batch*_unlabeled.xlsx"))
    if unlabeled_files:
        df_list = [pd.read_excel(f) for f in unlabeled_files]
        full_unlabeled_df = pd.concat(df_list, ignore_index=True)
        final_unlabeled_path = os.path.join(output_dir, f"{base_name}_FULL_unlabeled.xlsx")
        full_unlabeled_df.to_excel(final_unlabeled_path, index=False)
        print(f"✅ Berhasil menggabungkan {len(unlabeled_files)} batch GAGAL (unlabeled) ke: {final_unlabeled_path}")
    else:
        print("ℹ️ Tidak ada batch yang gagal karena limit token.")


def labeling(df_path, temperature=1.0, top_p=1.0, top_k=40, batch_size=300, max_retry=2):
    """
    Mengorkestrasi proses pelabelan, mengisolasi batch yang gagal karena limit token.
    """
    base_name = os.path.splitext(os.path.basename(df_path))[0]
    output_dir = os.path.join("results", base_name)
    unlabeled_dir = os.path.join(output_dir, "unlabeled")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(unlabeled_dir, exist_ok=True) # Buat sub-direktori untuk file gagal
    
    print(f"📂 Direktori output: {output_dir}")
    print(f"🗂️ Direktori unlabeled: {unlabeled_dir}")
    
    # Cek jika pekerjaan sudah selesai (berdasarkan file final)
    if os.path.exists(os.path.join(output_dir, f"{base_name}_FULL_labeled.xlsx")):
         print(f"\n❌ PEKERJAAN SELESAI. Hapus file di '{output_dir}' untuk menjalankan ulang.")
         return

    df_master = open_dataset(df_path)
    total_rows = len(df_master)
    if "label" not in df_master.columns: df_master["label"] = None
    if "justifikasi" not in df_master.columns: df_master["justifikasi"] = None

    print("\n🏁 Memulai proses verifikasi dan pelabelan per-batch...")
    for start in tqdm(range(0, total_rows, batch_size), desc="Overall Progress", unit="batch"):
        end = min(start + batch_size, total_rows)
        
        # Cek apakah file Labeled atau Unlabeled untuk batch ini sudah ada
        labeled_filename = os.path.join(output_dir, f"{base_name}_batch{start + 1:03d}_{end:03d}_labeled.xlsx")
        unlabeled_filename = os.path.join(unlabeled_dir, f"{base_name}_batch{start + 1:03d}_{end:03d}_unlabeled.xlsx")

        if os.path.exists(labeled_filename) or os.path.exists(unlabeled_filename):
            print(f"\n--- Batch {start + 1}-{end} sudah diproses (labeled/unlabeled). Melewati. ---")
            continue

        print(f"\n--- Memeriksa Batch Baris {start + 1}-{end} ---")
        
        batch_slice = df_master.iloc[start:end]
        if batch_slice['label'].notna().all():
            print(f"✅ Status: Sudah Terisi di Sumber. Membuat checkpoint gratis...")
            batch_slice.to_excel(labeled_filename, index=False)
            continue

        print(f"⚠️ Status: Perlu Diproses.")
        
        tweets_to_process = batch_slice["full_text"].tolist()
        num_texts = len(tweets_to_process)
        if num_texts == 0: continue
        numbered_texts = "\n".join([f"{i+1}. {text}" for i, text in enumerate(tweets_to_process)])

        valid = False
        attempts = 0
        token_limit_error_detected = False

        while not valid and attempts < max_retry:
            attempts += 1
            print(f"\n🔄 Memproses batch (percobaan {attempts}/{max_retry} dengan Key #{current_key_index + 1}) ...")
            
            prompt = f"""
            [Salin-tempel prompt panjang Anda di sini]
            ---
            TUGAS UTAMA:
            Anda akan diberikan {num_texts} teks bernomor...
            ---
            {numbered_texts}
            """
            
            try:
                output = genai_generate(prompt, temperature, top_p, top_k)
                if len(output) != num_texts:
                    print(f"❌ KESALAHAN JUMLAH OUTPUT: Diharapkan {num_texts}, diterima {len(output)}. Mencoba lagi...")
                    time.sleep(3); continue
                
                # Validasi format...
                valid = True # Jika semua validasi lolos

            except Exception as e:
                print(f"❌ Error pada API Key #{current_key_index + 1}: {e}")
                error_string = str(e).lower()

                # --- LOGIKA DETEKSI DAN ISOLASI ERROR TOKEN LIMIT ---
                if "max_tokens" in error_string or "finish reason: max_tokens" in error_string:
                    print("⛔️ ERROR TOKEN LIMIT TERDETEKSI! Batch ini terlalu besar.")
                    print(f"📝 Menyimpan batch {start + 1}-{end} sebagai unlabeled...")
                    batch_slice.to_excel(unlabeled_filename, index=False)
                    token_limit_error_detected = True
                    break # Hentikan percobaan untuk batch ini

                # Logika retry untuk error lainnya (kuota, server, dll)
                if any(keyword in error_string for keyword in ["quota", "limit", "permission denied"]):
                    rotate_api_key()
                wait_time = (2 ** attempts) + (random.random())
                print(f"Menunggu {wait_time:.2f} detik sebelum mencoba lagi...")
                time.sleep(wait_time)

        # Setelah loop percobaan selesai...
        if valid:
            print("✅ Batch valid, memperbarui hasil...")
            labels, justifikasi = [], []
            for line in output:
                parts = line.split(" - ", 1)
                labels.append(parts[0].strip())
                justifikasi.append(parts[1].strip() if len(parts) > 1 else "")
            
            # Buat salinan slice untuk diisi agar tidak mengubah DataFrame asli di loop
            labeled_slice = batch_slice.copy()
            labeled_slice['label'] = labels
            labeled_slice['justifikasi'] = justifikasi
            labeled_slice.to_excel(labeled_filename, index=False)
            print(f"💾 Checkpoint berlabel '{os.path.basename(labeled_filename)}' disimpan.")
        
        elif not token_limit_error_detected:
            # Hanya jalankan ini jika kegagalan BUKAN karena token limit
            print(f"❌ Gagal memproses batch {start + 1}-{end} setelah {max_retry} percobaan. Melewati.")

        print("--- Jeda 32 detik untuk mematuhi limit 2 RPM Free Tier ---")
        time.sleep(32) # Jeda panjang untuk mematuhi limit RPM yang ketat
    
    # --- PANGGIL FUNGSI FINALISASI DI AKHIR ---
    finalize_results(output_dir, base_name)


def main(filename, batch_size):
    os.makedirs("dataset", exist_ok=True)
    os.makedirs("results", exist_ok=True)
    dataset_path = f"dataset/{filename}.xlsx"
    if not os.path.exists(dataset_path):
        print(f"❌ Error: File dataset tidak ditemukan di '{dataset_path}'")
        return
    labeling(df_path=dataset_path, batch_size=batch_size, temperature=0.3, max_retry=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Skrip pelabelan otomatis dengan isolasi batch gagal.", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("filename", type=str, help="Nama dasar file dataset (tanpa .xlsx).")
    parser.add_argument("batch_size", type=int, help="Jumlah baris per permintaan API. Turunkan jika sering terjadi error token limit.")
    args = parser.parse_args()
    main(args.filename, args.batch_size)