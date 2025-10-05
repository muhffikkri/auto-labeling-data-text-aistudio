# Panduan Pengujian Komprehensif (End-to-End)

Dokumen ini menyediakan panduan lengkap untuk melakukan pengujian pada proyek auto-labeling-data-text-aistudio, mulai dari unit test hingga pengujian End-to-End yang memerlukan koneksi internet dan API key asli.

## 📋 Daftar Isi

1. [Prasyarat](#prasyarat)
2. [Pengujian Unit dan Integrasi](#pengujian-unit-dan-integrasi)
3. [Pengujian End-to-End Manual](#pengujian-end-to-end-manual)
4. [Pengujian Fitur Resume](#pengujian-fitur-resume)
5. [Troubleshooting](#troubleshooting)

## 🛠️ Prasyarat

### Instalasi Dependensi

```bash
# Install dependensi utama
pip install -r requirements.txt

# Install dependensi development untuk testing
pip install -r requirements-dev.txt
```

### Setup Environment untuk E2E Testing

1. **Buat file `.env` di root proyek** dengan konfigurasi berikut:

   ```env
   MODEL_NAME="gemini-1.5-pro-latest"
   OUTPUT_DIR="results"
   DATASET_DIR="dataset"
   GOOGLE_API_KEY_1="your_actual_api_key_here"
   GOOGLE_API_KEY_2="your_second_api_key_here"  # Opsional untuk testing rotasi
   ```

2. **Siapkan dataset kecil untuk testing** di dalam folder `dataset/`:
   ```csv
   tweet_text
   "Ini adalah tweet positif tentang universitas yang bagus."
   "Layanan di kampus ini sangat buruk dan mengecewakan."
   "Pendaftaran mahasiswa baru dibuka besok pagi."
   "Dosen-dosen di sini sangat kompeten dan membantu."
   "Fasilitas perpustakaan perlu diperbaiki segera."
   ```
   Simpan sebagai `dataset/e2e_test.csv`

## 🧪 Pengujian Unit dan Integrasi

### Menjalankan Unit Tests

```bash
# Jalankan semua unit tests
pytest tests/unit/ -v

# Jalankan test specific function
pytest tests/unit/test_process_utils.py::TestRotateApiKey::test_rotate_api_key_single_rotation -v

# Jalankan dengan coverage report
pytest tests/unit/ --cov=src --cov-report=html
```

### Menjalankan Integration Tests

```bash
# Jalankan semua integration tests
pytest tests/integration/ -v

# Jalankan test specific untuk resume logic
pytest tests/integration/test_labeling_flow.py::TestLabelDatasetResumeLogic -v

# Jalankan dengan output verbose dan capture disabled (untuk debugging)
pytest tests/integration/ -v -s
```

### Menjalankan Semua Tests

```bash
# Jalankan semua tests (unit + integration)
pytest tests/ -v

# Dengan parallel execution (jika tersedia)
pytest tests/ -v -n auto
```

## 🚀 Pengujian End-to-End Manual

Pengujian ini bertujuan untuk memverifikasi alur kerja lengkap aplikasi dengan dependensi nyata, termasuk panggilan ke Gemini API.

### Langkah 1: Persiapan Lingkungan Bersih

```bash
# Hapus output dari testing sebelumnya
rm -rf results/
rm -rf logs/

# Pastikan dataset testing tersedia
ls dataset/e2e_test.csv
```

### Langkah 2: Jalankan Aplikasi Utama

```bash
# Jalankan aplikasi dengan GUI
python main.py

# Atau jalankan secara langsung jika ada CLI interface
python -c "from src.core_logic.process import initialize_labeling_process, label_dataset, open_dataset; initialize_labeling_process(); df, _ = open_dataset('dataset', 'e2e_test'); label_dataset(df, 'e2e_test', 5, 3, {'temperature': 0.1}, 'tweet_text', ['POSITIF', 'NEGATIF', 'NETRAL'], threading.Event())"
```

### Langkah 3: Monitor dan Verifikasi Eksekusi

1. **Monitor Output Terminal:**

   - Periksa tidak ada ERROR yang unexpected
   - Verifikasi log rotasi API key (jika applicable)
   - Pastikan progress bar berjalan normal

2. **Monitor File Log:**

   ```bash
   # Lihat log terbaru
   tail -f logs/labeling_$(date +%Y-%m-%d).log

   # Cari error dalam log
   grep -i error logs/labeling_*.log
   grep -i warning logs/labeling_*.log
   ```

### Langkah 4: Verifikasi Output Files

1. **Periksa Struktur Output:**

   ```bash
   ls -la results/e2e_test/
   # Expected:
   # ├── labeled/
   # │   └── e2e_test_batch001_005_labeled.xlsx
   # ├── unlabeled/  (kosong jika berhasil)
   # └── e2e_test_FULL_labeled.xlsx
   ```

2. **Verifikasi Konten File Excel:**
   - Buka `results/e2e_test/e2e_test_FULL_labeled.xlsx`
   - Pastikan setiap baris memiliki:
     - `label`: POSITIF, NEGATIF, atau NETRAL
     - `justifikasi`: Penjelasan yang masuk akal
   - Verifikasi tidak ada cell kosong pada kolom label dan justifikasi

### Langkah 5: Testing Manual Quality Check

Lakukan pengecekan kualitas manual:

| Tweet Text                                     | Expected Label | Actual Label | Justifikasi Quality       |
| ---------------------------------------------- | -------------- | ------------ | ------------------------- |
| "tweet positif tentang universitas yang bagus" | POSITIF        | ?            | Apakah justifikasi logis? |
| "layanan sangat buruk dan mengecewakan"        | NEGATIF        | ?            | Apakah alasan tepat?      |
| "pendaftaran dibuka besok pagi"                | NETRAL         | ?            | Apakah klasifikasi benar? |

## 🔄 Pengujian Fitur Resume

### Test 1: Resume Batch Parsial

1. **Jalankan aplikasi dan hentikan di tengah jalan:**

   ```bash
   python main.py
   # Hentikan dengan Ctrl+C ketika processing sedang berjalan
   ```

2. **Periksa file output yang tersimpan:**

   ```bash
   ls -la results/e2e_test/labeled/
   # Seharusnya ada file batch dengan beberapa baris terlabeli
   ```

3. **Jalankan kembali aplikasi:**

   ```bash
   python main.py
   # Aplikasi seharusnya melanjutkan dari batch yang belum selesai
   ```

4. **Verifikasi log resume:**
   ```bash
   tail -20 logs/labeling_$(date +%Y-%m-%d).log
   # Cari pesan "Melanjutkan batch yang sudah ada"
   ```

### Test 2: Resume dengan Batch Completed

1. **Simulasi batch yang sudah selesai:**

   - Biarkan aplikasi menyelesaikan semua batch
   - Jalankan kembali aplikasi

2. **Verifikasi pesan skip:**
   ```bash
   tail -10 logs/labeling_$(date +%Y-%m-%d).log
   # Seharusnya ada pesan "PEKERJAAN SELESAI" atau "sudah sepenuhnya terlabeli"
   ```

### Test 3: Testing API Key Rotation

1. **Setup multiple API keys di `.env`:**

   ```env
   GOOGLE_API_KEY_1="first_key"
   GOOGLE_API_KEY_2="second_key"
   GOOGLE_API_KEY_3="third_key"
   ```

2. **Simulasi quota limit:**

   - Gunakan API key dengan quota terbatas
   - Monitor log untuk rotasi key

3. **Verifikasi rotasi:**
   ```bash
   grep -i "rotasi" logs/labeling_*.log
   # Seharusnya ada pesan rotasi API key
   ```

## 🐛 Troubleshooting

### Common Issues dan Solutions

#### 1. ModuleNotFoundError saat menjalankan tests

```bash
# Solution: Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/

# Atau gunakan editable install
pip install -e .
```

#### 2. API Key Error

```bash
# Verifikasi API key valid
python -c "import google.generativeai as genai; genai.configure(api_key='your_key'); print('API key valid')"

# Periksa quota
curl -H "Authorization: Bearer YOUR_API_KEY" https://generativelanguage.googleapis.com/v1beta/models
```

#### 3. File Permission Error

```bash
# Fix permissions untuk folder output
chmod -R 755 results/
chmod -R 755 logs/
```

#### 4. Pandas/Excel Reading Error

```bash
# Install openpyxl jika belum ada
pip install openpyxl

# Verifikasi file Excel tidak corrupt
python -c "import pandas as pd; print(pd.read_excel('results/test_file.xlsx'))"
```

#### 5. Memory Issues dengan Dataset Besar

```bash
# Monitor memory usage
top -p $(pgrep -f python)

# Reduce batch size dalam konfigurasi
# Edit batch_size parameter menjadi lebih kecil (e.g., 10 -> 5)
```

### Debugging Advanced Issues

#### Enable Debug Logging

```python
# Tambahkan di awal skrip
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

#### Profile Performance

```bash
# Install profiler
pip install py-spy

# Profile aplikasi yang sedang berjalan
py-spy top --pid $(pgrep -f "python main.py")
```

#### Memory Profiling

```bash
# Install memory profiler
pip install memory-profiler

# Run dengan profiling
python -m memory_profiler main.py
```

## 📊 Expected Test Results

### Unit Tests Success Criteria

- ✅ All rotate_api_key tests pass
- ✅ All open_dataset tests pass (success + failure cases)
- ✅ All load_prompt_template tests pass
- ✅ All setup_logging tests pass

### Integration Tests Success Criteria

- ✅ Happy path labeling completes successfully
- ✅ Resume logic works for partial batches
- ✅ Skip logic works for completed batches
- ✅ Error handling with retry mechanism works
- ✅ Multiple batch processing works correctly

### E2E Tests Success Criteria

- ✅ Complete labeling workflow dari start to finish
- ✅ Output files generated dengan format yang benar
- ✅ Resume functionality bekerja setelah interruption
- ✅ API key rotation bekerja saat quota exceeded
- ✅ Quality check menunjukkan labeling results yang reasonable

## 📝 Test Report Template

Setelah menjalankan semua tests, gunakan template berikut untuk dokumentasi:

```
# Test Execution Report - [Date]

## Test Environment
- Python Version:
- Dependencies Version:
- OS:
- Dataset Size:

## Unit Tests Results
- Total Tests: X
- Passed: X
- Failed: X
- Coverage: X%

## Integration Tests Results
- Total Tests: X
- Passed: X
- Failed: X
- Issues Found: [List any issues]

## E2E Tests Results
- Dataset: e2e_test.csv (X rows)
- Processing Time: X minutes
- API Calls Made: X
- Success Rate: X%
- Quality Assessment: [Manual review notes]

## Issues Identified
1. [Issue description]
   - Severity: High/Medium/Low
   - Workaround: [If any]
   - Status: Open/Resolved

## Recommendations
1. [Recommendation 1]
2. [Recommendation 2]
```

---

**Catatan:** Pengujian E2E memerlukan koneksi internet yang stabil dan API key yang valid. Pastikan untuk tidak menggunakan API key production dalam environment testing.
