# 📌 Auto Labeling Tweets dengan Gemini

Proyek ini adalah sistem **pelabelan data otomatis**, dirancang untuk memproses dataset teks (seperti tweet) menggunakan **Google Gemini API**. Skrip ini secara cerdas menetapkan label sentimen dan relevansi (`POSITIF`, `NEGATIF`, `NETRAL`, `TIDAK RELEVAN`) beserta justifikasi singkat untuk setiap baris data.

Dibangun dengan mempertimbangkan pekerjaan skala besar, sistem ini sepenuhnya **dapat dilanjutkan (resumable)**, menangani interupsi dengan mulus, dan mengatur hasil secara sistematis untuk setiap dataset yang diproses.

---

## ✨ Fitur Utama

- 🚀 **Antarmuka Baris Perintah (CLI)** → Jalankan pelabelan untuk file apa pun dengan mudah langsung dari terminal, cukup berikan nama file dan ukuran batch.
- 📂 **Manajemen Output Terstruktur** → Secara otomatis membuat sub-direktori untuk setiap dataset di dalam folder `results/`, menjaga agar semua file batch dan hasil akhir tetap rapi dan terpisah.
- 🧠 **Logika Batch Cerdas** → Untuk setiap batch, skrip secara otomatis memutuskan tindakan terbaik:
  1.  **Lewati jika Selesai**: Melewati batch yang file hasilnya sudah ada.
  2.  **Checkpoint Gratis**: Membuat file checkpoint jika data di file sumber sudah terisi penuh, tanpa membuang kuota API.
  3.  **Proses & Timpa**: Memproses (atau memproses ulang) seluruh batch jika datanya kosong atau hanya terisi sebagian, demi menjamin konsistensi.
- 🔄 **Resume Cerdas & Checkpointing** → Jika proses dihentikan, skrip akan memuat progres dari file checkpoint **terbaru** dan secara otomatis melanjutkan pekerjaan dari sana, termasuk mengisi "lubang" data yang terlewat.
- 🔐 **Mekanisme Retry** → Mencoba ulang secara otomatis jika panggilan API gagal atau menghasilkan format yang tidak valid, meningkatkan keandalan proses.

---

## 📂 Struktur Direktori

Struktur proyek dirancang agar tetap bersih dan teratur.

```.
├── dataset/                # Folder untuk menyimpan semua file dataset input (.xlsx)
│   └── tweets_kampus_a.xlsx
│   └── data_sentimen_b.xlsx
├── results/                # Folder output utama
│   └── tweets_kampus_a/    # Sub-folder dibuat otomatis untuk setiap dataset
│       ├── ..._batch001_300_labeled.xlsx
│       ├── ..._batch301_600_labeled.xlsx
│       └── ..._full_labeled.xlsx
├── .env                    # File konfigurasi untuk menyimpan API Key
├── .gitignore
├── labeling.py             # Skrip utama untuk menjalankan pelabelan
├── requirements.txt
└── README.md
```

---

## ⚙️ Instalasi & Setup

1.  **Clone Repository:**

    ```bash
    git clone https://github.com/muhffikkri/auto-labeling-aistudio.git
    cd auto-labeling-aistudio
    ```

2.  **Buat dan Aktifkan Virtual Environment:**

    ```bash
    # Membuat venv
    python -m venv venv
    # Mengaktifkan venv (Windows)
    venv\Scripts\activate
    # Mengaktifkan venv (macOS/Linux)
    source venv/bin/activate
    ```

3.  **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Siapkan Dataset:**

    - Buat folder `dataset` jika belum ada.
    - Letakkan file Excel (`.xlsx`) Anda di dalamnya. Contoh: `dataset/tweets_kampus_a.xlsx`.

5.  **Atur API Key:**
    - Buat file baru bernama `.env` di direktori utama.
    - Isi file tersebut dengan Google Gemini API Key Anda:
      ```
      GOOGLE_API_KEY="your_api_key_here"
      ```

---

## 🚀 Cara Penggunaan

Skrip ini dijalankan melalui terminal dengan menyediakan **nama file** dan **ukuran batch** sebagai argumen.

**Sintaks Perintah:**

```bash
python labeling.py <nama_file_dataset> <ukuran_batch>
```

- `<nama_file_dataset>`: Nama file di folder `dataset` (tanpa ekstensi `.xlsx`).
- `<ukuran_batch>`: Jumlah baris yang akan diproses dalam satu siklus.

**Contoh Praktis:**

```bash
# Memproses 'tweets_kampus_a.xlsx' dengan batch berisi 300 baris
python labeling.py tweets_kampus_a 300

# Memproses 'data_sentimen_b.xlsx' dengan batch berisi 100 baris
python labeling.py data_sentimen_b 100
```

Skrip akan secara otomatis membuat folder `results/tweets_kampus_a/`, menyimpan file-file checkpoint di sana, dan membuat file `tweets_kampus_a_full_labeled.xlsx` setelah semua baris berhasil dilabeli.

---

## 📖 Dokumentasi Fungsi

- `genai_generate(...)`: Mengirimkan prompt ke model 'gemini-2.5-pro' dan mem-parsing hasilnya menjadi list string.
- `open_dataset(...)`: Membaca file Excel dan memuatnya ke dalam DataFrame pandas dengan penanganan error.
- `labeling(...)`: Mesin utama yang mengorkestrasi seluruh alur kerja pelabelan secara batch dan stateful.
- `main(...)`: Titik masuk yang memvalidasi input dari baris perintah dan memulai proses pelabelan.

---

## ⚠️ Batasan

- Hanya mendukung input file Excel (`.xlsx`).
- Kualitas label bergantung sepenuhnya pada performa model Gemini.
- Membutuhkan koneksi internet yang stabil dan API key yang aktif.
- Error karena intervensi user (misal: Ctrl+C) memungkinkan skrip dilanjutkan dari checkpoint terakhir. Kegagalan batch setelah `max_retry` akan dilewati, dan hasilnya akan ditandai sebagai `_PARTIAL_labeled.xlsx`.

---

## 🛠️ Teknologi

- Python 3.10+
- Pandas
- Google Generative AI for Python

## ⚙️ Rencana Pengembangan

1.  Menambahkan sistem logging yang lebih detail ke dalam file di folder `/logs`.
2.  Meningkatkan mekanisme retry dengan _exponential backoff_ untuk menangani limit API dengan lebih baik.
3.  Menambahkan prompt untuk verifikasi mandiri dan koreksi hasil.
4.  Dukungan untuk memproses beberapa file secara berurutan dalam satu perintah.
5.  Membuat file init untuk membuat venv dan menginstall dependencies secara otomatis
