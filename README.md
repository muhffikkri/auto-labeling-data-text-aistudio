# 📌 Auto Labeling Tweets dengan Gemini

Proyek ini merupakan sistem **pelabelan otomatis** untuk dataset teks (misalnya tweet) menggunakan **Google Gemini API**.  
Label yang dihasilkan meliputi kategori sentimen dan relevansi:

- POSITIF
- NEGATIF
- NETRAL
- TIDAK RELEVAN

Setiap teks juga diberi **justifikasi singkat** (alasan pemilihan label + catatan buzzer jika terdeteksi).  
Hasil labeling akan otomatis tersimpan dalam file Excel (`.xlsx`) dengan **checkpoint** agar proses bisa dilanjutkan tanpa kehilangan progress.

---

## ✨ Fitur Utama

- 🔄 **Checkpointing** → proses bisa dilanjutkan dari hasil terakhir.
- 📊 **Output Excel** → hasil labeling otomatis tersimpan dengan kolom tambahan (`label`, `justifikasi`).
- ⚡ **Batch Processing** → data besar bisa diproses bertahap (default 300 baris per batch).
- 🔐 **Retry Mechanism** → otomatis retry jika model menghasilkan output tidak valid.
- 🎛 **Configurable Parameters** → atur `temperature`, `top_p`, `top_k`, `batch_size`, dll.

---

## 📂 Struktur Direktori

```
├── dataset/ # Folder dataset input (Excel .xlsx)
│ └── tweets_dataset.xlsx
├── prompt/ # Folder untuk menyimpan prompt
│ └── tweets_dataset_labeled.xlsx
├── results/ # Folder output hasil labeling
│ └── tweets_dataset_labeled.xlsx
├── labeling.py # Script utama
├── requirements.txt # Dependency Python
└── README.md # Dokumentasi project
```

---

## ⚙️ Instalasi & Setup

1. Clone repository:

   ```bash
   git clone https://github.com/username/auto-labeling-aistudio.git
   cd auto-labeling-aistudio
   ```

2. Buat virtual environment python

   ```bash
   python -m venv venv
   ```

3. Aktifkan virtual environment:

   ```bash
   venv/bin/activate
   ```

4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Siapkan folder dataset dan letakkan file Excel (`.xlsx`) di dalamnya.
   Contoh: `dataset/tweets_dataset.xlsx`

6. Buat file .env dan atur **Google Gemini API Key**:

   ```bash
   GOOGLE_API_KEY="your_api_key_here"
   ```

---

## 🚀 Cara Penggunaan

Jalankan script `labeling.py`:

```bash
python labeling.py
```

Atau langsung panggil fungsi di dalam Python:

```python
from labeling import labeling

# Melakukan labeling dataset
labeling("tweets_dataset", batch_size=200, temperature=0.7, top_p=0.9, top_k=40)
```

Output akan tersimpan di folder `results/` dengan nama:
`tweets_dataset_labeled.xlsx`

---

## 📖 Dokumentasi Fungsi

```python
genai_generate(prompt, temperature=1.0, top_p=1.0, top_k=40)
```

Mengirim prompt ke Gemini dan mengembalikan hasil dalam bentuk list string.

```python
open_dataset(path)
```

Membuka dataset Excel (`.xlsx`) dan mengembalikan DataFrame pandas.

```python
labeling(df_path, batch_size=300, temperature=1.0, top_p=1.0, top_k=40, max_retry=3)
```

Melakukan labeling otomatis terhadap dataset teks, menyimpan hasil ke Excel dengan checkpoint.

---

## ⚠️ Batasan

- Hanya mendukung input file `.xlsx`.
- Bergantung pada kualitas output Gemini (bisa error jika format output salah).
- Proses bisa lama untuk dataset yang sangat besar.
- Membutuhkan koneksi internet stabil dan API key aktif.
- Error karena intervensi user tidak akan tersimpan, namun error karena max attemps akan menyimpan batch terakhir yang berhasil dikerjakan

---

## 📌 Contoh Output

Dataset hasil labeling akan memiliki kolom tambahan:

| text                                       | label         | justifikasi                                      |
| ------------------------------------------ | ------------- | ------------------------------------------------ |
| "Program ini bagus untuk mahasiswa"        | POSITIF       | Menyatakan dukungan dan hal baik terkait kampus. |
| "Birokrasi ribet bikin malas daftar ulang" | NEGATIF       | Keluhan langsung terkait layanan universitas.    |
| "Aku makan bakso enak banget"              | TIDAK RELEVAN | Tidak ada hubungan dengan kampus/universitas.    |

---

## 🛠️ Teknologi

- Python 3.12.6
- Pandas
- Google Gemini API

## ⚙ Potential update:

1. Menambahkan self_improvement_prompt, correction_prompt, verification_system_prompt
2. Meningkatkan mekanisme retry dengan exponential backoff
3. Menambahkan logging untuk setiap langkah proses
4. Menyimpan log error pada /logs
