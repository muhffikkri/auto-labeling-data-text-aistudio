import pandas as pd
from dotenv import load_dotenv
import os
import google.generativeai as genai
import time
from tqdm import tqdm

# Load API key dari .env
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)

def genai_generate(prompt="", temperature=1.0, top_p=1.0, top_k=40)->list[str]:
    """
    Mengirim permintaan ke model Gemini (gemini-2.5-pro) untuk menghasilkan teks
    berdasarkan prompt yang diberikan.

    Fungsi ini menggunakan Google Generative AI (Gemini API) untuk menghasilkan
    keluaran berupa teks yang dibagi per baris. Parameter tambahan seperti 
    `temperature`, `top_p`, dan `top_k` dapat digunakan untuk mengatur variasi 
    dan kreativitas jawaban model.

    Args:
        prompt (str): 
            Input berupa teks atau instruksi yang akan diberikan ke model.
        temperature (float, optional): 
            Nilai antara 0.0-2.0 untuk mengatur kreativitas model. 
            Semakin tinggi nilainya, semakin beragam jawabannya. Default = 1.0.
        top_p (float, optional): 
            Probabilitas kumulatif untuk nucleus sampling (0.0-1.0). 
            Nilai lebih rendah membatasi keluaran ke kata dengan probabilitas lebih tinggi. Default = 1.0.
        top_k (int, optional): 
            Membatasi jumlah kandidat token dengan probabilitas tertinggi yang dipertimbangkan 
            pada setiap langkah. Default = 40.

    Returns:
        list[str]: 
            Daftar string hasil keluaran model, dipisahkan per baris.

    Raises:
        Exception: 
            Jika terjadi kesalahan pada saat request API (contoh: API key salah, 
            koneksi internet bermasalah, atau respons tidak sesuai).

    Expected Output:
        - Jika berhasil: 
            List teks yang dihasilkan, misalnya:
            `["Sepakbola adalah olahraga...", "Dimainkan oleh dua tim...", "Tujuannya mencetak gol."]`
        - Jika gagal: 
            Muncul Exception dengan pesan error.

    Usage Example:
        >>> genai_generate("Jelaskan tentang sepakbola")
        ["Sepakbola adalah olahraga tim.", 
         "Dimainkan oleh 11 pemain di masing-masing tim.", 
         "Tujuan permainan adalah mencetak gol."]

    Limitations:
        - Membutuhkan koneksi internet aktif.
        - Membutuhkan API Key yang valid di file `.env`.
        - Respons model bergantung pada ketersediaan server Gemini.
        - Hasil keluaran mungkin tidak selalu konsisten (dipengaruhi temperature/top_p/top_k).
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
        # Ambil output
        output = response.text.strip().split("\n")
        return output
    except Exception as e:
        # print(f"Error saat request API: {e}")
        time.sleep(3)
        raise Exception(f"❌ Error saat request API: {e}")

def open_dataset(__path__):
    """
    Membuka file dataset Excel dan mengembalikannya sebagai DataFrame pandas.

    Fungsi ini mencoba membaca file Excel (`.xlsx`) dari path yang diberikan 
    (tanpa ekstensi). Jika file tidak ditemukan atau ada kesalahan lain saat 
    membaca file, fungsi akan melempar exception yang sesuai.

    Args:
        __path__ (str): 
            Path ke file Excel tanpa ekstensi `.xlsx`. 
            Misalnya, `"dataset/mydata"` akan membuka file `"dataset/mydata.xlsx"`.

    Returns:
        pandas.DataFrame: 
            DataFrame berisi isi file Excel.

    Raises:
        NameError: 
            Jika file tidak ditemukan pada path yang diberikan.
        Exception: 
            Jika terjadi error lain saat membaca file (contoh: format file rusak, 
            file terkunci, atau bukan file Excel).

    Expected Output:
        - Jika berhasil:
            DataFrame pandas dengan isi file Excel.
        - Jika gagal:
            Exception sesuai dengan jenis error (NameError atau Exception).

    Usage Example:
        >>> df = open_dataset("dataset/mydata")
        >>> print(df.head())
             id   text    label
        0    1   Halo    None
        1    2   Apa     None

    Limitations:
        - Hanya mendukung file Excel dengan ekstensi `.xlsx`.
        - Membutuhkan library `pandas` terinstall.
        - Path harus valid dan file harus dapat diakses.
    """
    try:
        df = pd.read_excel(rf"{__path__}.xlsx")
        return df
    except FileNotFoundError:
        raise NameError(f"Error: File not found at '{__path__}'")
    except Exception as e:
        raise Exception(f"Error reading file '{__path__}': {e}")

def labeling(df_path, batch_size=300, temperature=1.0, top_p=1.0, top_k=40, max_retry=3): 
    """
    Melakukan proses pelabelan otomatis terhadap dataset teks menggunakan model Gemini.

    Fungsi ini membaca dataset berupa file Excel, lalu melakukan labeling teks 
    (sentimen & relevansi dalam konteks universitas) ke dalam 4 kategori: 
    "POSITIF", "NEGATIF", "NETRAL", atau "TIDAK RELEVAN".  
    Justifikasi diberikan untuk setiap label, termasuk catatan deteksi buzzer.  
    Proses berjalan secara batch dengan checkpoint otomatis untuk mencegah hilangnya 
    hasil jika proses terhenti.

    Args:
        df_path (str):
            Nama file dataset tanpa ekstensi, misalnya `"tweets_dataset"`.
            Fungsi akan mencari file di `"dataset/{df_path}.xlsx"` atau 
            melanjutkan dari `"results/{df_path}_labeled.xlsx"` jika tersedia.
        batch_size (int, optional):
            Jumlah baris teks yang diproses per batch. Default = 300.
        temperature (float, optional):
            Parameter kontrol kreativitas model (semakin rendah → semakin deterministik).
            Default = 1.0.
        top_p (float, optional):
            Parameter nucleus sampling (0-1). Default = 1.0.
        top_k (int, optional):
            Batas jumlah token kandidat teratas untuk sampling. Default = 40.
        max_retry (int, optional):
            Jumlah maksimal percobaan ulang per batch jika output tidak valid.
            Default = 3.

    Returns:
        None:
            Hasil disimpan dalam file Excel baru di folder `results/` dengan nama:
            `{df_path}_labeled.xlsx`.

    Raises:
        Exception:
            Jika terjadi error saat membaca dataset atau berinteraksi dengan model Gemini.
        ValueError:
            Jika format output model tidak sesuai atau jumlah baris hasil tidak sama 
            dengan jumlah input (setelah percobaan ulang melebihi `max_retry`).

    Expected Output:
        - Dataset hasil labeling dalam file Excel, dengan tambahan kolom:
          - `label`: kategori sentimen (POSITIF, NEGATIF, NETRAL, TIDAK RELEVAN).
          - `justifikasi`: alasan singkat dan catatan buzzer (jika ada).
        - Progress log pada console (checkpoint, batch processing, validasi, error).

    Usage Example:
        >>> labeling("tweets_dataset", batch_size=200, temperature=0.7, top_p=0.9, top_k=40)
        📂 Membuka dataset asli: dataset/tweets_dataset.xlsx
        ➡️ Mulai dari baris 0 (checkpoint)
        🔄 Memproses batch 0:200 (percobaan 1) ...
        ✅ Batch valid, menyimpan hasil ...
        💾 Checkpoint tersimpan di results/tweets_dataset_labeled.xlsx
        ✅ Labeling selesai, hasil disimpan ke results/tweets_dataset_labeled.xlsx

    Limitations:
        - Hanya mendukung input file Excel (`.xlsx`).
        - Bergantung pada kualitas respons dari model Gemini; bisa gagal jika model
          memberikan output dengan format tidak valid.
        - Proses labeling bisa lama jika dataset sangat besar.
        - Jika semua data sudah terlabeli sebelumnya, fungsi akan berhenti otomatis.

    Notes:
        - Fungsi mendukung **resume mode**: jika file hasil labeling sudah ada, 
          proses akan dilanjutkan dari checkpoint terakhir.
        - Hasil disimpan secara berkala setelah setiap batch, sehingga aman jika proses terhenti.
    """
    # Cek apakah file sudah pernah dikerjakan sebelumnya
    output_path = "results/" + df_path + "_labeled.xlsx"

    # Jika sudah ada file hasil, lanjutkan dari situ
    if os.path.exists(output_path):
        print(f"📂 Melanjutkan dari checkpoint: {output_path}")
        df = open_dataset(output_path)
    else:
        print(f"📂 Membuka dataset asli: dataset/{df_path}.xlsx")

        df = open_dataset("dataset/" + df_path)
        # Pastikan kolom label & justifikasi ada
        if "label" not in df.columns:
            df["label"] = None
        if "justifikasi" not in df.columns:
            df["justifikasi"] = None

    # Cari baris terakhir yang sudah ada label
    last_labeled = df["label"].last_valid_index()
    if last_labeled is None:
        start_index = 0
    else:
        start_index = last_labeled + 1

    if df["label"].notna().sum() == len(df):
        print("✅ Semua data sudah terlabeli, tidak ada pekerjaan baru.")
        return

    print(f"➡️ Mulai dari baris {start_index} (checkpoint)")

    # Hitung total batch yang perlu diproses
    total_batches = (len(df) - start_index + batch_size - 1) // batch_size
        
    # Loop batch mulai dari start_index
    for start in tqdm(range(start_index, len(df), batch_size), 
                      desc="🔄 Labeling batches", 
                      total=total_batches, 
                      unit="batch"):
        end = start + batch_size
        batch = df.iloc[start:end]

        # Ambil teks dari kolom full_text
        texts = batch["full_text"].tolist()

        # Inisialisasi jumlah percobaan
        valid = False
        attempts = 0

        while not valid and attempts < max_retry:
            attempts += 1
            print(f"\n🔄 Memproses batch {start}:{end} (percobaan {attempts}) ...")

            # Prompt untuk Gemini
            prompt = f"""
            Prompt untuk Pelabelan Tweet ke dalam Kategori Sentimen Positif, Negatif, Netral, atau Tidak Relevan dalam Konteks Universitas dengan Deteksi Buzzer

            Tujuan
            Anda bertindak sebagai validator untuk proyek pelabelan teks. Tugas Anda adalah mengklasifikasikan tweet ke dalam empat kategori: "POSITIF", "NEGATIF", "NETRAL", atau "TIDAK RELEVAN" dalam konteks universitas tertentu, sambil menandai tweet yang terindikasi sebagai buzzer (akun yang memposting secara terkoordinasi atau dengan motif promosi/manipulasi). Dataset ini akan digunakan untuk fine-tuning model AI (Transformer/IndoBERTweet) yang mampu memahami konteks, nuansa, dan maksud utama dari sebuah tweet terkait universitas.

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
            
            output = genai_generate(prompt, temperature, top_p, top_k)

            # Validator 
            if len(output) != len(texts):
                print(f"Jumlah output ({len(output)}) tidak sesuai input ({len(texts)})")
                time.sleep(2)
                continue

            # pastikan format LABEL - Justifikasi
            allowed_labels = ["POSITIF", "NEGATIF", "NETRAL", "TIDAK RELEVAN"]
            format_valid = all(
                any(output_line.startswith(label) for label in allowed_labels) and "-" in output_line
                for output_line in output
            )

            if not format_valid:
                print("❌ Format output tidak valid (tidak sesuai LABEL - Justifikasi)")
                time.sleep(2)
                continue

            # kalau lolos semua → valid
            valid = True
            print("✅ Batch valid, menyimpan hasil ...")

            # Split ke 2 kolom: label + justifikasi
            labels, justifikasi = [], []
            for line in output:
                if "-" in line:
                    label, justification = line.split("-", 1)
                    labels.append(label.strip())
                    justifikasi.append(justification.strip())
                else:
                    labels.append(line.strip())
                    justifikasi.append("")

            df.loc[start:end-1, "label"] = labels
            df.loc[start:end-1, "justifikasi"] = justifikasi

        if not valid:
            print(f"❌ Gagal memproses batch {start}:{end} setelah {max_retry} percobaan. Lewati batch ini.")

    # Simpan ke Excel baru
    
    df.to_excel(output_path, index=False)
    print("✅ Labeling selesai, hasil disimpan ke data_labeled.xlsx")


def main():
    # Baca file Excel (masukkan nama file yang sudah disimpan di folder dataset tanpa ekstensi nya)
    __filename__ = "data_testing"
    labeling(__filename__)

if __name__ == "__main__":
    main()