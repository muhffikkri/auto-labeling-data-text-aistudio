import pandas as pd
from dotenv import load_dotenv
import os
import google.generativeai as genai
import time
from tqdm import tqdm
import glob
import re 
import argparse

# Load API key dari .env
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)

def genai_generate(prompt="", temperature=1.0, top_p=1.0, top_k=40)->list[str]:
    """
    Mengirimkan prompt ke model 'gemini-2.5-pro' dan mem-parsing hasilnya.

    Fungsi ini berinteraksi dengan Google Generative AI API untuk menghasilkan konten
    teks berdasarkan prompt yang diberikan. Respons dari API, yang diharapkan
    berupa teks dengan baris-baris terpisah, akan di-strip dan dipecah menjadi
    sebuah list string. Fungsi ini juga menangani error dengan jeda 3 detik
    sebelum melempar exception untuk mengatasi masalah koneksi sesaat.

    Args:
        prompt (str):
            Teks input atau instruksi yang akan dikirim ke model AI.
        temperature (float, optional):
            Mengontrol keacakan output (0.0-2.0). Nilai lebih tinggi
            menghasilkan jawaban yang lebih kreatif. Default: 1.0.
        top_p (float, optional):
            Mengontrol keragaman melalui sampling nukleus (0.0-1.0).
            Default: 1.0.
        top_k (int, optional):
            Mengontrol keragaman dengan membatasi token yang dipertimbangkan.
            Default: 40.

    Returns:
        list[str]:
            Sebuah list berisi string, di mana setiap elemen adalah satu baris
            dari output yang dihasilkan oleh model.

    Raises:
        Exception:
            Dilemparkan jika terjadi kesalahan saat berkomunikasi dengan API.
            Akan ada jeda 3 detik sebelum exception ini dilemparkan.

    Usage Example:
        >>> prompt_cuaca = "Jelaskan secara singkat tentang musim hujan di Indonesia."
        >>> hasil = genai_generate(prompt_cuaca)
        >>> print(hasil)
        ['Musim hujan di Indonesia umumnya terjadi antara bulan Oktober hingga April.',
         'Ditandai dengan peningkatan curah hujan yang signifikan.',
         'Dipengaruhi oleh angin muson barat.']

    Limitations:
        - Membutuhkan koneksi internet dan API Key Google yang valid di file .env.
        - Performa dan kualitas respons bergantung pada ketersediaan layanan Google Gemini.
    """
    # Inisialisasi model
    model = genai.GenerativeModel("gemini-2.5-pro")
    try:
        # Buat request ke Gemini
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                top_p=top_p,
                top_k=top_k
            )
        )
        # Ambil output dan proses menjadi list
        output = response.text.strip().split("\n")
        return output
    except Exception as e:
        # Beri jeda singkat sebelum gagal untuk menangani error sementara
        time.sleep(3)
        raise Exception(f"❌ Error saat request API: {e}")

def open_dataset(__path__):
    """
    Membaca file Excel dan memuatnya ke dalam DataFrame pandas.

    Fungsi ini berfungsi sebagai wrapper untuk `pandas.read_excel` dengan
    penanganan error yang disesuaikan. Ia akan mencoba membuka file dari path
    yang diberikan dan melempar exception yang jelas jika file tidak ditemukan
    atau terjadi error lain saat proses pembacaan.

    Args:
        __path__ (str):
            Path lengkap menuju file Excel yang akan dibuka, harus
            menyertakan ekstensi file (contoh: '.xlsx').

    Returns:
        pd.DataFrame:
            DataFrame pandas yang berisi data dari file Excel jika berhasil.

    Raises:
        NameError:
            Dilemparkan secara spesifik jika file tidak ditemukan pada path
            (dibangkitkan dari FileNotFoundError).
        Exception:
            Dilemparkan untuk semua error lain yang terjadi selama
            proses pembacaan file (misalnya, file korup atau format tidak valid).

    Usage Example:
        >>> # Asumsikan file 'dataset/data_mahasiswa.xlsx' ada
        >>> df_mahasiswa = open_dataset("dataset/data_mahasiswa.xlsx")
        >>> print(df_mahasiswa.head())

    Limitations:
        - Fungsi ini bergantung sepenuhnya pada library `pandas`.
        - Paling optimal untuk file berformat '.xlsx' sesuai konvensi proyek.
    """
    try:
        df = pd.read_excel(rf"{__path__}")
        return df
    except FileNotFoundError:
        # Melempar NameError untuk konsistensi historis atau spesifik
        raise NameError(f"Error: File not found at '{__path__}'")
    except Exception as e:
        # Menangkap error lain dari pandas, seperti file korup
        raise Exception(f"Error reading file '{__path__}': {e}")

def labeling(df_path, batch_size=300, temperature=1.0, top_p=1.0, top_k=40, max_retry=5):
    """
    Mengorkestrasi proses pelabelan otomatis dari awal hingga akhir.

    Fungsi ini adalah mesin utama yang mengatur seluruh alur kerja pelabelan.
    Ia bekerja dengan melakukan iterasi pada dataset dalam potongan seukuran
    batch. Untuk setiap batch, ia menerapkan logika prioritas untuk menentukan
    tindakan yang paling efisien: melewati pekerjaan yang sudah selesai, membuat
    checkpoint untuk data yang sudah ada, atau memproses data yang belum lengkap
    menggunakan AI.

    Args:
        df_path (str):
            Path lengkap menuju file dataset asli di dalam folder `/dataset`.
            Contoh: "dataset/tweets_undip.xlsx".
        batch_size (int, optional):
            Jumlah baris yang akan diperiksa dan diproses dalam satu siklus.
            Default: 300.
        temperature (float, optional):
            Parameter kreativitas untuk model AI (0.0-2.0). Default: 1.0.
        top_p (float, optional):
            Parameter sampling nukleus untuk model AI (0.0-1.0). Default: 1.0.
        top_k (int, optional):
            Parameter sampling top-k untuk model AI. Default: 40.
        max_retry (int, optional):
            Jumlah percobaan ulang maksimum jika panggilan API gagal untuk
            satu batch. Default: 5.

    Returns:
        None.
            Fungsi ini tidak mengembalikan nilai. Hasilnya disimpan ke dalam
            file-file di direktori `/results/<nama_file>/`.

    Key Features:
    - **Manajemen Folder Otomatis**: Membuat sub-direktori yang rapi untuk
      setiap dataset di dalam folder `/results`.
    - **Resume Cerdas**: Jika skrip dihentikan, ia akan melanjutkan progres
      dengan memuat file checkpoint terbaru yang ditemukan.
    - **Pencegahan Kerja Ganda**: Secara otomatis mendeteksi jika pekerjaan
      sudah selesai (file `_full_labeled.xlsx` ada) dan berhenti.

    Logic Flow per Batch:
    Untuk setiap rentang baris (misal, 1-300, 301-600, ...), fungsi ini akan:
    1.  **Lewati jika Selesai**: Memeriksa apakah file hasil untuk batch
        tersebut (misal, `..._batch001_300_labeled.xlsx`) sudah ada.
        Jika ya, batch ini akan dilewati.
    2.  **Checkpoint Gratis**: Jika file hasil belum ada, ia memeriksa file
        dataset *asli*. Jika semua baris dalam rentang batch ini sudah
        memiliki label, sebuah file checkpoint akan dibuat secara otomatis
        tanpa memanggil AI.
    3.  **Proses & Timpa**: Jika kedua kondisi di atas tidak terpenuhi (artinya
        batch tersebut kosong atau hanya terisi sebagian), seluruh rentang
        batch akan dikirim ke AI untuk diproses (atau diproses ulang).
        Hasilnya akan menimpa data yang ada untuk batch tersebut dan
        disimpan sebagai checkpoint baru.
    """

    # Langkah 1: Persiapan
    base_name = os.path.splitext(os.path.basename(df_path))[0]
    output_dir = os.path.join("results", base_name)
    os.makedirs(output_dir, exist_ok=True)
    print(f"📂 Direktori output: {output_dir}")

    full_output_path = os.path.join(output_dir, f"{base_name}_full_labeled.xlsx")
    if os.path.exists(full_output_path):
        print(f"\n❌ PEKERJAAN SELESAI: File '{os.path.basename(full_output_path)}' sudah ada. Hapus untuk menjalankan ulang.")
        return

    # Langkah 2: Muat dataset asli dan pastikan kolom ada
    print(f"📖 Membaca dataset asli: {df_path}")
    df_master = open_dataset(df_path)
    total_rows = len(df_master)
    
    # === PERBAIKAN DI SINI ===
    # Pastikan kolom 'label' dan 'justifikasi' ada di df_master SEGERA setelah dimuat.
    if "label" not in df_master.columns:
        df_master["label"] = None
    if "justifikasi" not in df_master.columns:
        df_master["justifikasi"] = None
    # ==========================
    
    # Inisialisasi df_progress. Kita akan memuat progres jika ada, jika tidak mulai dari master.
    result_files = glob.glob(os.path.join(output_dir, f"{base_name}_batch*.xlsx"))
    if result_files:
        latest_file = max(result_files, key=os.path.getmtime)
        print(f"📖 Melanjutkan progres dari checkpoint terbaru: {os.path.basename(latest_file)}")
        df_progress = open_dataset(latest_file)
    else:
        print("📖 Memulai pekerjaan baru dari dataset asli.")
        df_progress = df_master.copy()
        # Baris pengecekan kolom di sini menjadi redundan tetapi tidak berbahaya
        if "label" not in df_progress.columns: df_progress["label"] = None
        if "justifikasi" not in df_progress.columns: df_progress["justifikasi"] = None


    # Langkah 3: Iterasi per batch dan putuskan tindakan
    print("\n🏁 Memulai proses verifikasi dan pelabelan per-batch...")
    for start in tqdm(range(0, total_rows, batch_size), desc="Overall Progress", unit="batch"):
        end = min(start + batch_size, total_rows)
        batch_filename = os.path.join(output_dir, f"{base_name}_batch{start + 1:03d}_{end:03d}_labeled.xlsx")

        print(f"\n--- Memeriksa Batch Baris {start + 1}-{end} ---")

        # Prioritas 1: Apakah file hasil untuk batch ini sudah ada?
        if os.path.exists(batch_filename):
            print(f"✅ Status: Sudah Selesai. File '{os.path.basename(batch_filename)}' ditemukan. Melewati.")
            continue

        # Prioritas 2: Cek data sumber jika file hasil tidak ada
        batch_slice_master = df_master.iloc[start:end]
        # Baris ini sekarang aman karena df_master dijamin memiliki kolom 'label'
        if batch_slice_master['label'].notna().all():
            print(f"✅ Status: Sudah Terisi di Sumber. Membuat checkpoint gratis...")
            df_progress.update(batch_slice_master)
            df_progress.to_excel(batch_filename, index=False)
            print(f"💾 Checkpoint '{os.path.basename(batch_filename)}' dibuat.")
            continue

        # Prioritas 3: Proses batch (karena kosong atau terisi sebagian)
        print(f"⚠️ Status: Perlu Diproses (kosong atau terisi sebagian).")
        
        texts = df_progress.iloc[start:end]["full_text"].tolist()

        valid = False
        attempts = 0
        while not valid and attempts < max_retry:
            attempts += 1
            print(f"\n🔄 Memproses batch untuk baris {start + 1} - {end} (percobaan {attempts}) ...")
            
            # (Prompt untuk Gemini tetap sama)
            prompt = f"""
            Prompt untuk Pelabelan Tweet ke dalam Kategori Sentimen Positif, Negatif, Netral, atau Tidak Relevan dalam Konteks Universitas dengan Deteksi Buzzer

            Tujuan
            Anda bertindak sebagai validator untuk proyek pelabelan teks. Tugas Anda adalah mengklasifikasikan tweet ke dalam empat kategori: "POSITIF", "NEGatif", "NETRAL", atau "TIDAK RELEVAN" dalam konteks universitas tertentu, sambil menandai tweet yang terindikasi sebagai buzzer (akun yang memposting secara terkoordinasi atau dengan motif promosi/manipulasi). Dataset ini akan digunakan untuk fine-tuning model AI (Transformer/IndoBERTweet) yang mampu memahami konteks, nuansa, dan maksud utama dari sebuah tweet terkait universitas.

            Prinsip Utama
            - Fokus Inti: Labeli setiap tweet berdasarkan sentimen yang dominan (positif, negatif, atau netral) dalam konteks universitas tertentu. Jika tweet tidak relevan dengan universitas, labeli sebagai "TIDAK RELEVAN". Tandai tweet yang menunjukkan indikasi buzzer dalam justifikasi.
            - Konteks dan Semantik: Perhatikan makna keseluruhan tweet, termasuk nuansa, sarkasme, atau konteks implisit. Tweet harus jelas terkait dengan universitas tertentu (misal, [Nama Kampus], mahasiswa, dosen, atau kegiatan kampus). Tweet yang bersifat promosi, candaan, atau pertanyaan tanpa sentimen jelas dapat diklasifikasikan sebagai NETRAL jika relevan dengan universitas.
            - Deteksi Buzzer: Tandai tweet yang terindikasi buzzer dengan mencatat pola promosi berlebihan, penggunaan hashtag tidak wajar, atau bahasa yang tidak alami dalam justifikasi. Ini membantu memisahkan sentimen autentik dari konten yang dimanipulasi.

            Kategori dan Pedoman

            POSITIF
            - Definisi Inti: Tweet yang menyampaikan emosi, pandangan, atau penilaian positif terkait universitas, seperti pujian, dukungan, atau kegembiraan.
            - Cakupan: Ucapan selamat, pujian terhadap kegiatan, fasilitas, atau prestasi universitas, ekspresi optimisme, atau promosi dengan nada positif.
            - Contoh Tweet: "Keren banget acara wisuda [Nama Kampus], bikin bangga!" (Fokus: pujian positif)
            - Indikator: Tweet mengandung kata-kata positif, ekspresi emosi gembira, atau dukungan yang jelas terkait universitas.
            - Catatan Buzzer: Perhatikan jika tweet menggunakan bahasa promosi berlebihan atau hashtag tidak relevan (misal, #KampusNo1 setiap tweet).

            NEGATIF
            - Definisi Inti: Tweet yang menyampaikan emosi, pandangan, atau penilaian negatif terkait universitas, seperti kritik, keluhan, atau kemarahan.
            - Cakupan: Kritik terhadap kebijakan, layanan, atau fasilitas universitas, ekspresi kekecewaan, atau hinaan terkait kampus.
            - Contoh Tweet: "Pelayanan [Nama Kampus] lambat banget, bikin kesel!" (Fokus: keluhan negatif)
            - Indikator: Tweet mengandung kata-kata negatif, ekspresi emosi marah atau kecewa, atau kritik yang jelas terkait universitas.
            - Catatan Buzzer: Perhatikan jika tweet berulang dengan nada negatif seragam dari beberapa akun, menunjukkan serangan terkoordinasi.

            NETRAL
            - Definisi Inti: Tweet yang tidak menyampaikan emosi atau penilaian positif maupun negatif, hanya berfokus pada informasi objektif atau pertanyaan tanpa sentimen, dan relevan dengan universitas.
            - Cakupan: Pengumuman, fakta, atau pertanyaan netral terkait universitas, seperti jadwal, pendaftaran, atau informasi resmi.
            - Contoh Tweet: "Pendaftaran mahasiswa baru [Nama Kampus] dibuka 1 Agustus 2025." (Fokus: informasi netral)
            - Indikator: Tweet bersifat informatif, tidak mengandung emosi atau penilaian subjektif, dan relevan dengan universitas.
            - Catatan Buzzer: Perhatikan jika tweet informatif berulang dari akun yang sama dengan pola promosi.

            TIDAK RELEVAN
            - Definisi Inti: Tweet yang tidak relevan dengan konteks universitas, meskipun mungkin mengandung sentimen positif, negatif, atau netral.
            - Cakupan: Tweet yang tidak menyebutkan universitas, kegiatan kampus, atau elemen terkait, atau tweet yang bersifat umum tanpa kaitan spesifik.
            - Contoh Tweet: "Wisuda temenku keren banget, salut!" (Fokus: pujian positif tetapi tidak menyebut universitas tertentu)
            - Indikator: Tweet tidak memiliki kaitan jelas dengan universitas tertentu.
            - Catatan Buzzer: Tweet promosi umum tanpa kaitan universitas sering kali terindikasi buzzer.

            Aturan Emas untuk Mengatasi Ambiguitas
            1. Fokus Utama: Tanyakan, "Apakah tweet ini relevan dengan universitas tertentu dan menyampaikan emosi positif, negatif, atau informasi netral? Apakah ada indikasi buzzer?" Jika tidak ada kaitan dengan universitas, labeli sebagai TIDAK RELEVAN.
            2. Spesifik vs. Umum: Pilih kategori yang paling sesuai berdasarkan isi dan relevansi tweet. Jika tweet mengandung sentimen tetapi tidak relevan dengan universitas (misal, "Pelayanan buruk banget!" tanpa menyebut kampus), klasifikasikan sebagai TIDAK RELEVAN. Tandai pola buzzer jika terdeteksi.

            Instruksi Pelabelan
            - Jumlah Data: Labeli {len(texts)} tweet yang diberikan.
            - Format Output:
            - Gunakan format: LABEL KATEGORI - Justifikasi [Alasan singkat untuk label dan skor. Catatan: TERINDIKASI BUZZER jika ada pola promosi, hashtag berlebihan, atau aktivitas mencurigakan].
            - Contoh:
                1. POSITIF - Tweet memuji acara wisuda [Nama Kampus] dengan nada gembira. Skor tinggi karena sentimen positif dan relevansi jelas.
                2. TIDAK RELEVAN - Tweet mengandung pujian tetapi tidak menyebut universitas tertentu. Catatan: TERINDIKASI BUZZER karena penggunaan hashtag promosi berulang (#KampusTerbaik).

            Contoh Tambahan untuk Klarifikasi
            1. Tweet: "Selamat buat [Nama Kampus] atas akreditasi A, bikin bangga alumni! #KampusTerbaik"
            - Label: POSITIF
            - Justifikasi: Tweet mengandung ucapan selamat dan ekspresi kebanggaan terkait [Nama Kampus]. Skor agak rendah karena hashtag #KampusTerbaik mungkin menunjukkan promosi. Catatan: TERINDIKASI BUZZER karena hashtag promosi.
            2. Tweet: "Sistem pendaftaran [Nama Kampus] error lagi, parah!"
            - Label: NEGATIF
            - Justifikasi: Tweet mengeluhkan masalah teknis [Nama Kampus] dengan nada kecewa. Skor tinggi karena sentimen negatif dan relevansi jelas.
            3. Tweet: "Jadwal kuliah [Nama Kampus] sudah diumumkan di situs resmi."
            - Label: NETRAL
            - Justifikasi: Tweet hanya menyampaikan informasi tanpa emosi atau penilaian, relevan dengan [Nama Kampus]. Skor tinggi karena bersifat informatif.
            4. Tweet: "Acara seru, tapi parkirannya chaos."
            - Label: TIDAK RELEVAN
            - Justifikasi: Tweet mengandung sentimen positif dan negatif tetapi tidak menyebut universitas tertentu. Skor tinggi karena ketidakrelevanan jelas.
            5. Tweet: "Apa kabar mahasiswa baru [Nama Kampus]?"
            - Label: NETRAL
            - Justifikasi: Tweet berupa pertanyaan tanpa ekspresi emosi, relevan dengan [Nama Kampus]. Skor tinggi karena bersifat netral dan relevan.
            6. Tweet: "Gabung [Nama Kampus], universitas nomor satu di Indonesia! #KampusTerbaik"
            - Label: POSITIF
            - Justifikasi: Tweet memuji [Nama Kampus] dengan nada promosi. Skor agak rendah karena bahasa berlebihan. Catatan: TERINDIKASI BUZZER karena penggunaan hashtag promosi dan nada tidak alami.

            Catatan Tambahan
            - Konteks X: Tweet sering pendek, informal, dan dapat mengandung sarkasme, meme, atau hashtag. Perhatikan konteks ini untuk menentukan sentimen, relevansi, dan indikasi buzzer.
            - Ambiguitas: Jika tweet ambigu (misal, relevansinya tidak jelas, sentimennya tidak tegas, atau ada indikasi buzzer), pilih kategori berdasarkan fokus utama, berikan skor keyakinan lebih rendah, dan jelaskan ambiguitas di justifikasi.
            - Referensi Eksternal: Jika diperlukan, gunakan sumber resmi seperti situs universitas atau Indonesia.go.id untuk memverifikasi fakta, atau analisis profil X untuk mendeteksi pola buzzer (misal, frekuensi posting atau interaksi akun).

            Output yang Diinginkan
            Untuk setiap tweet, berikan:
            LABEL KATEGORI - Justifikasi [Alasan singkat untuk label dan skor. Catatan: TERINDIKASI BUZZER jika ada pola promosi, hashtag berlebihan, atau aktivitas mencurigakan].
            Contoh:
            1. POSITIF - Tweet memuji akreditasi [Nama Kampus] dengan nada bangga. Skor tinggi karena sentimen positif dan relevansi sangat jelas.
            Output HARUS berjumlah {len(texts)} baris, sesuai urutan input. Hanya tulis label dan justifikasi (dengan - sebagai pemisah) saja per baris tanpa tambahan teks lain.
            
            Teks:
            {texts}
            """
            
            try:
                output = genai_generate(prompt, temperature, top_p, top_k)
                if len(output) != len(texts):
                    print(f"❌ Jumlah output ({len(output)}) tidak sesuai input ({len(texts)})")
                    time.sleep(2)
                    continue
                allowed_labels = ["POSITIF", "NEGATIF", "NETRAL", "TIDAK RELEVAN"]
                format_valid = all(
                    any(output_line.strip().startswith(label) for label in allowed_labels) and " - " in output_line
                    for output_line in output
                )
                if not format_valid:
                    print("❌ Format output tidak valid (tidak sesuai 'LABEL - Justifikasi')")
                    time.sleep(2)
                    continue
                valid = True
            except Exception as e:
                print(f"❌ Error saat memanggil API: {e}")
                time.sleep(5)

        if valid:
            print("✅ Batch valid, memperbarui hasil...")
            labels, justifikasi = [], []
            for line in output:
                parts = line.split(" - ", 1)
                labels.append(parts[0].strip())
                justifikasi.append(parts[1].strip() if len(parts) > 1 else "")

            df_progress.iloc[start:end, df_progress.columns.get_loc('label')] = labels
            df_progress.iloc[start:end, df_progress.columns.get_loc('justifikasi')] = justifikasi

            df_progress.to_excel(batch_filename, index=False)
            print(f"💾 Checkpoint baru '{os.path.basename(batch_filename)}' disimpan.")
        else:
            print(f"❌ Gagal memproses batch untuk baris {start + 1}-{end} setelah {max_retry} percobaan. Melewati batch ini.")
    
    # Langkah 4: Finalisasi
    print("\n🏁 Proses iterasi batch selesai.")
    if df_progress['label'].notna().all():
        df_progress.to_excel(full_output_path, index=False)
        print(f"✅ Semua baris telah terisi! Hasil akhir yang lengkap disimpan di: {full_output_path}")
    else:
        partial_output_path = os.path.join(output_dir, f"{base_name}_PARTIAL_labeled.xlsx")
        df_progress.to_excel(partial_output_path, index=False)
        print(f"⚠️ Masih ada baris yang belum terlabeli. Hasil parsial disimpan di: {partial_output_path}")


def main(filename, batch_size):
    """
    Menginisialisasi lingkungan dan memulai proses pelabelan untuk file target.

    Fungsi ini bertindak sebagai titik masuk utama yang dipanggil oleh parser
    argumen baris perintah. Tugas utamanya adalah mempersiapkan lingkungan
    kerja (memastikan folder `dataset` dan `results` ada) dan melakukan
    validasi input dasar (memastikan file dataset yang diminta benar-benar ada).
    Jika semua pra-pemeriksaan berhasil, ia akan memanggil fungsi `labeling`
    untuk memulai pekerjaan inti.

    Args:
        filename (str):
            Nama dasar dari file dataset yang berada di folder `/dataset`,
            tanpa menyertakan path atau ekstensi `.xlsx`.
        batch_size (int):
            Jumlah baris yang akan diproses per batch, yang akan diteruskan
            ke fungsi `labeling`.

    Returns:
        None.
            Fungsi ini tidak mengembalikan nilai. Ia akan mencetak status
            atau pesan error ke konsol dan keluar jika file tidak ditemukan.

    Notes:
        - Fungsi ini dirancang untuk dipanggil dari blok `if __name__ == '__main__':`
          setelah argumen baris perintah di-parsing.
    """
    # Membuat folder yang diperlukan jika belum ada
    os.makedirs("dataset", exist_ok=True)
    os.makedirs("results", exist_ok=True)

    # Membangun path lengkap ke file dataset
    dataset_path = f"dataset/{filename}.xlsx"
    
    # Memeriksa apakah file dataset benar-benar ada
    if not os.path.exists(dataset_path):
        print(f"❌ Error: File dataset tidak ditemukan di '{dataset_path}'")
        print("Pastikan nama file benar dan file tersebut ada di dalam folder 'dataset'.")
        return
        
    # Memanggil fungsi pelabelan dengan parameter yang diterima
    labeling(df_path=dataset_path, batch_size=batch_size)

if __name__ == "__main__":
    # Inisialisasi parser
    parser = argparse.ArgumentParser(
        description="""
        Skrip pelabelan data otomatis menggunakan AI Generatif.
        
        Skrip ini memproses file Excel dari folder /dataset, melabeli baris-baris
        yang kosong secara batch, dan menyimpan hasilnya di subfolder dalam /results.
        Mendukung melanjutkan pekerjaan dari checkpoint terakhir.
        """,
        formatter_class=argparse.RawTextHelpFormatter # Untuk format deskripsi yang lebih baik
    )

    # Tambahkan argumen yang diperlukan
    parser.add_argument(
        "filename", 
        type=str, 
        help="Nama dasar file dataset yang akan diproses (tanpa ekstensi .xlsx).\nContoh: 'undip_undip_2022_01_01'"
    )
    parser.add_argument(
        "batch_size", 
        type=int, 
        help="Jumlah baris yang akan diproses dalam satu batch.\nContoh: 300"
    )

    # Parsing argumen dari baris perintah
    args = parser.parse_args()

    # Panggil fungsi main dengan argumen yang telah diparsing
    main(args.filename, args.batch_size)