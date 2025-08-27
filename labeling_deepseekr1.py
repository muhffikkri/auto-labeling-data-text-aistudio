import pandas as pd
import ollama
import os
import argparse
import time
from tqdm import tqdm

def parse_model_output(raw_output: str) -> str:
    """
    Membersihkan output model dari blok <think>...</think>.

    Fungsi ini mencari tag </think> dan mengembalikan teks apa pun yang muncul
    setelahnya. Jika tag tidak ditemukan, ia mengembalikan output asli.

    Args:
        raw_output (str): Output mentah dari model LLM.

    Returns:
        str: Teks yang sudah bersih, yang seharusnya hanya berisi jawaban akhir.
    """
    think_end_tag = "</think>"
    if think_end_tag in raw_output:
        # Pisahkan string berdasarkan tag akhir, ambil bagian kedua
        try:
            final_answer = raw_output.split(think_end_tag, 1)[1]
            # Bersihkan spasi kosong atau newline di awal/akhir
            return final_answer.strip()
        except IndexError:
            # Kasus langka di mana tag ada di paling akhir string
            return ""
    else:
        # Jika tidak ada tag, anggap seluruh output adalah jawaban yang valid
        return raw_output.strip()

def ollama_generate_single(prompt: str, model_name: str, temperature: float = 0.5, max_retry: int = 3) -> tuple[str | None, str | None]:
    """
    Mengirimkan prompt ke Ollama, mem-parsing, memvalidasi, dan mengambil output.
    """
    allowed_labels = ["POSITIF", "NEGATIF", "NETRAL", "TIDAK RELEVAN"]
    
    for attempt in range(max_retry):
        try:
            response = ollama.generate(
                model=model_name,
                prompt=prompt,
                options={'temperature': temperature}
            )
            
            # 1. Ambil output mentah dari model
            raw_output = response['response']
            # 2. Panggil fungsi parsing untuk membersihkan blok <think>
            output_line = parse_model_output(raw_output)

            # 3. Lanjutkan validasi seperti biasa pada output yang sudah bersih
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
            print(f"\n❌ Error saat request ke Ollama (Percobaan {attempt+1}): {e}")
            time.sleep(3)

    return None, None

def labeling(df_path: str, model_name: str = "deepseek-coder:6.7b"):
    """
    Fungsi utama untuk melabeli dataset baris per baris dengan checkpoint.
    """
    
    # --- Langkah 1: Persiapan Direktori dan Path File ---
    base_name = os.path.splitext(os.path.basename(df_path))[0]
    output_dir = os.path.join("results", base_name)
    os.makedirs(output_dir, exist_ok=True)
    
    progress_path = os.path.join(output_dir, f"{base_name}_progress.xlsx")
    final_path = os.path.join(output_dir, f"{base_name}_full_labeled.xlsx")

    print(f"📂 Direktori output: {output_dir}")

    if os.path.exists(final_path):
        print(f"\n✅ PEKERJAAN SELESAI: File final '{os.path.basename(final_path)}' sudah ada.")
        return

    # --- Langkah 2: Muat Progres atau Mulai dari Awal ---
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
            if 'label' not in df_progress.columns:
                df_progress['label'] = pd.NA
            if 'justifikasi' not in df_progress.columns:
                df_progress['justifikasi'] = pd.NA
        except Exception as e:
            print(f"❌ Gagal memuat file Excel sumber: {e}")
            return
            
    if start_index >= len(df_progress):
        print("✅ Semua baris tampaknya sudah diproses dalam file progress. Merapikan...")
        os.rename(progress_path, final_path)
        print(f"🎉 Pekerjaan Selesai! Hasil akhir disimpan di: {final_path}")
        return

    print(f"\n🚀 Memulai pelabelan dari baris ke-{start_index + 1}...")

    # --- Langkah 3: Iterasi Baris per Baris ---
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
    
    # --- Langkah 4: Finalisasi ---
    os.rename(progress_path, final_path)
    print(f"\n🎉 Pekerjaan Selesai! Hasil akhir disimpan di: {final_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="""
        Skrip pelabelan data otomatis baris-per-baris menggunakan model AI lokal via Ollama.
        """,
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "filename", 
        type=str, 
        help="Nama dasar file dataset di folder 'dataset' (tanpa ekstensi .xlsx)."
    )
    parser.add_argument(
        "--model", 
        type=str, 
        default="deepseek-coder:6.7b", 
        help="Nama model Ollama yang akan digunakan. Contoh: 'llama3:8b'"
    )

    args = parser.parse_args()

    os.makedirs("dataset", exist_ok=True)
    os.makedirs("results", exist_ok=True)
    
    dataset_path = f"dataset/{args.filename}.xlsx"

    if not os.path.exists(dataset_path):
        print(f"❌ Error: File dataset tidak ditemukan di '{dataset_path}'")
    else:
        labeling(df_path=dataset_path, model_name=args.model)