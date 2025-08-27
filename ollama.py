import pandas as pd
import ollama
import os
import argparse
import time
from tqdm import tqdm

def ollama_generate_single(prompt: str, model_name: str, temperature: float = 0.5, max_retry: int = 3) -> tuple[str | None, str | None]:
    """
    Mengirimkan prompt ke Ollama, memvalidasi, dan mem-parsing output.

    Fungsi ini mencoba beberapa kali untuk mendapatkan output yang valid dari model
    dengan format "LABEL - Justifikasi".

    Args:
        prompt (str): Prompt lengkap untuk dikirim ke model.
        model_name (str): Nama model Ollama yang akan digunakan.
        temperature (float): Parameter kreativitas untuk model.
        max_retry (int): Jumlah percobaan ulang jika output tidak valid.

    Returns:
        tuple[str | None, str | None]: Tuple berisi (label, justifikasi) jika berhasil,
                                       atau (None, None) jika gagal setelah semua percobaan.
    """
    allowed_labels = ["POSITIF", "NEGATIF", "NETRAL", "TIDAK RELEVAN"]
    
    for attempt in range(max_retry):
        try:
            response = ollama.generate(
                model=model_name,
                prompt=prompt,
                options={'temperature': temperature}
            )
            output_line = response['response'].strip()

            # Mencari pemisah " - " dalam output
            if " - " not in output_line:
                time.sleep(1)
                continue

            parts = output_line.split(" - ", 1)
            label = parts[0].strip()
            justification = parts[1].strip() if len(parts) > 1 else ""

            # Validasi apakah label yang dihasilkan ada dalam daftar yang diizinkan
            if label not in allowed_labels:
                time.sleep(1)
                continue
            
            # Jika semua validasi lolos, kembalikan hasilnya
            return label, justification

        except Exception as e:
            print(f"\n❌ Error saat request ke Ollama (Percobaan {attempt+1}): {e}")
            time.sleep(3)

    # Jika loop selesai tanpa hasil yang valid
    # print(f"\n Gagal mendapatkan output yang valid untuk prompt setelah {max_retry} percobaan.")
    return None, None

def labeling(df_path: str, model_name: str = "deepseek-coder:6.7b"):
    """
    Fungsi utama untuk melabeli dataset baris per baris dengan checkpoint.

    Skrip ini memuat dataset, melanjutkan dari checkpoint jika ada, melabeli
    setiap baris yang kosong, dan menyimpan progres secara atomik setelah setiap
    baris berhasil diproses.

    Args:
        df_path (str): Path lengkap menuju file dataset Excel.
        model_name (str): Nama model Ollama yang akan digunakan.
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
        # Cari baris terakhir yang sudah diisi untuk menentukan titik mulai
        last_labeled_index = df_progress['label'].last_valid_index()
        if last_labeled_index is not None:
            start_index = last_labeled_index + 1
    else:
        print(f"📖 Memulai pekerjaan baru dari: {os.path.basename(df_path)}")
        try:
            df_master = pd.read_excel(df_path)
            # Buat salinan untuk menyimpan progres
            df_progress = df_master.copy()
            # Pastikan kolom label dan justifikasi ada
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
    # Membuat progress bar dengan tqdm
    for index, row in tqdm(df_progress.iloc[start_index:].iterrows(), total=total_rows - start_index, desc="Melabeli Baris"):
        
        # Jika baris ini sudah memiliki label (misalnya dari pekerjaan sebelumnya), lewati
        if pd.notna(row['label']):
            continue

        text_to_label = row["full_text"]

        # Prompt yang lebih detail untuk hasil yang lebih baik
        prompt = f"""
        Anda bertindak sebagai validator untuk proyek pelabelan teks. Tugas Anda adalah mengklasifikasikan tweet ke dalam empat kategori: "POSITIF", "NEGATIF", "NETRAL", atau "TIDAK RELEVAN" dalam konteks universitas tertentu. Dataset ini akan digunakan untuk fine-tuning model AI (Transformer/IndoBERTweet) yang mampu memahami konteks, nuansa, dan maksud utama dari sebuah tweet terkait universitas.

        Prinsip Utama
        - Fokus Inti: Labeli setiap tweet berdasarkan sentimen yang dominan (positif, negatif, atau netral) dalam konteks universitas tertentu. Jika tweet tidak relevan dengan universitas, labeli sebagai "TIDAK RELEVAN". Tandai tweet yang menunjukkan indikasi buzzer dalam justifikasi.
        - Konteks dan Semantik: Perhatikan makna keseluruhan tweet, termasuk nuansa, sarkasme, atau konteks implisit. Tweet harus jelas terkait dengan universitas tertentu (misal, [Nama Kampus], mahasiswa, dosen, atau kegiatan kampus). Tweet yang bersifat promosi, candaan, atau pertanyaan tanpa sentimen jelas dapat diklasifikasikan sebagai NETRAL jika relevan dengan universitas.

        Kategori dan Pedoman

        POSITIF
        - Definisi Inti: Tweet yang menyampaikan emosi, pandangan, atau penilaian positif terkait universitas, seperti pujian, dukungan, atau kegembiraan.
        - Cakupan: Ucapan selamat, pujian terhadap kegiatan, fasilitas, atau prestasi universitas, ekspresi optimisme, atau promosi dengan nada positif.
        - Contoh Tweet: "Keren banget acara wisuda [Nama Kampus], bikin bangga!" (Fokus: pujian positif)
        - Indikator: Tweet mengandung kata-kata positif, ekspresi emosi gembira, atau dukungan yang jelas terkait universitas.

        NEGATIF
        - Definisi Inti: Tweet yang menyampaikan emosi, pandangan, atau penilaian negatif terkait universitas, seperti kritik, keluhan, atau kemarahan.
        - Cakupan: Kritik terhadap kebijakan, layanan, atau fasilitas universitas, ekspresi kekecewaan, atau hinaan terkait kampus.
        - Contoh Tweet: "Pelayanan [Nama Kampus] lambat banget, bikin kesel!" (Fokus: keluhan negatif)
        - Indikator: Tweet mengandung kata-kata negatif, ekspresi emosi marah atau kecewa, atau kritik yang jelas terkait universitas.

        NETRAL
        - Definisi Inti: Tweet yang tidak menyampaikan emosi atau penilaian positif maupun negatif, hanya berfokus pada informasi objektif atau pertanyaan tanpa sentimen, dan relevan dengan universitas.
        - Cakupan: Pengumuman, fakta, atau pertanyaan netral terkait universitas, seperti jadwal, pendaftaran, atau informasi resmi.
        - Contoh Tweet: "Pendaftaran mahasiswa baru [Nama Kampus] dibuka 1 Agustus 2025." (Fokus: informasi netral)
        - Indikator: Tweet bersifat informatif, tidak mengandung emosi atau penilaian subjektif, dan relevan dengan universitas.

        TIDAK RELEVAN
        - Definisi Inti: Tweet yang tidak relevan dengan konteks universitas, meskipun mungkin mengandung sentimen positif, negatif, atau netral.
        - Cakupan: Tweet yang tidak menyebutkan universitas, kegiatan kampus, atau elemen terkait, atau tweet yang bersifat umum tanpa kaitan spesifik.
        - Contoh Tweet: "Wisuda temenku keren banget, salut!" (Fokus: pujian positif tetapi tidak menyebut universitas tertentu)
        - Indikator: Tweet tidak memiliki kaitan jelas dengan universitas tertentu.

        Aturan Emas untuk Mengatasi Ambiguitas
        1. Fokus Utama: Tanyakan, "Apakah tweet ini relevan dengan universitas tertentu dan menyampaikan emosi positif, negatif, atau informasi netral? Apakah ada indikasi buzzer?" Jika tidak ada kaitan dengan universitas, labeli sebagai TIDAK RELEVAN.
        2. Spesifik vs. Umum: Pilih kategori yang paling sesuai berdasarkan isi dan relevansi tweet. Jika tweet mengandung sentimen tetapi tidak relevan dengan universitas (misal, "Pelayanan buruk banget!" tanpa menyebut kampus), klasifikasikan sebagai TIDAK RELEVAN. Tandai pola buzzer jika terdeteksi.

        Instruksi Pelabelan
        - Format Output: LABEL KATEGORI - Justifikasi [Alasan singkat untuk label].
        - Contoh:
        1. POSITIF - Tweet memuji acara wisuda [Nama Kampus] dengan nada gembira.
        2. TIDAK RELEVAN - Tweet mengandung pujian tetapi tidak menyebut universitas tertentu. 

        Contoh Tambahan untuk Klarifikasi
        1. Tweet: "Selamat buat [Nama Kampus] atas akreditasi A, bikin bangga alumni! #KampusTerbaik"
        - Label: POSITIF
        - Justifikasi: Tweet mengandung ucapan selamat dan ekspresi kebanggaan terkait [Nama Kampus]. 
        2. Tweet: "Sistem pendaftaran [Nama Kampus] error lagi, parah!"
        - Label: NEGATIF
        - Justifikasi: Tweet mengeluhkan masalah teknis [Nama Kampus] dengan nada kecewa. 
        3. Tweet: "Jadwal kuliah [Nama Kampus] sudah diumumkan di situs resmi."
        - Label: NETRAL
        - Justifikasi: Tweet hanya menyampaikan informasi tanpa emosi atau penilaian, relevan dengan [Nama Kampus]. 
        4. Tweet: "Acara seru, tapi parkirannya chaos."
        - Label: TIDAK RELEVAN
        - Justifikasi: Tweet mengandung sentimen positif dan negatif tetapi tidak menyebut universitas tertentu. 
        5. Tweet: "Apa kabar mahasiswa baru [Nama Kampus]?"
        - Label: NETRAL
        - Justifikasi: Tweet berupa pertanyaan tanpa ekspresi emosi, relevan dengan [Nama Kampus]. 
        6. Tweet: "Gabung [Nama Kampus], universitas nomor satu di Indonesia! #KampusTerbaik"
        - Label: POSITIF
        - Justifikasi: Tweet memuji [Nama Kampus] dengan nada promosi.

        Catatan Tambahan
        - Konteks X: Tweet sering pendek, informal, dan dapat mengandung sarkasme, meme, atau hashtag. Perhatikan konteks ini untuk menentukan sentimen, relevansi, dan indikasi buzzer.
        - Ambiguitas: Jika tweet ambigu (misal, relevansinya tidak jelas, sentimennya tidak tegas, atau ada indikasi buzzer), pilih kategori berdasarkan fokus utama dan jelaskan ambiguitas di justifikasi.

        Respon harus berupa label - justifikasi. tidak boleh ada tambahan teks apapun karena akan diparse secara otomatis.

        Teks yang harus dianalisis:
        {text_to_label}
        """

        label, justification = ollama_generate_single(prompt, model_name)

        if label and justification:
            # Menggunakan .loc untuk memastikan data ditulis di lokasi yang benar
            df_progress.loc[index, 'label'] = label
            df_progress.loc[index, 'justifikasi'] = justification
            
            # Simpan seluruh DataFrame sebagai checkpoint setelah setiap baris berhasil
            # Ini adalah cara yang atomik dan aman
            df_progress.to_excel(progress_path, index=False)
        else:
            # Gagal mendapatkan label yang valid, biarkan kosong untuk dicoba lagi nanti
            # tqdm akan otomatis mencetak di baris baru
            print(f"\n⚠️ Gagal melabeli baris ke-{index + 1}. Melewati untuk sementara.")
            continue
    
    # --- Langkah 4: Finalisasi ---
    # Ganti nama file progress menjadi file final setelah loop selesai
    os.rename(progress_path, final_path)
    print(f"\n🎉 Pekerjaan Selesai! Hasil akhir disimpan di: {final_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="""
        Skrip pelabelan data otomatis baris-per-baris menggunakan model AI lokal via Ollama.
        Skrip ini mendukung checkpoint dan melanjutkan pekerjaan secara otomatis.
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

    # Memastikan folder yang diperlukan ada
    os.makedirs("dataset", exist_ok=True)
    os.makedirs("results", exist_ok=True)
    
    dataset_path = f"dataset/{args.filename}.xlsx"

    if not os.path.exists(dataset_path):
        print(f"❌ Error: File dataset tidak ditemukan di '{dataset_path}'")
    else:
        labeling(df_path=dataset_path, model_name=args.model)