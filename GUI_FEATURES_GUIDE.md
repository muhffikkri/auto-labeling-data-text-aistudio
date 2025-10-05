# 🎯 GUI AUTO-LABELING: Panduan Lengkap Fitur Terbaru

## 🚀 Overview Aplikasi

Aplikasi GUI Auto-Labeling telah diperbarui dengan fitur-fitur canggih untuk memberikan pengalaman yang lebih lengkap dan profesional dalam proses pelabelan data teks otomatis menggunakan Google Generative AI.

## 📋 Daftar Tab dan Fitur

### 1. 🏠 **Tab Proses Utama**

**Fungsi**: Workflow utama pelabelan dataset

- ✅ **File Dataset Input**: Pilih file CSV/XLSX dengan file dialog
- ✅ **Nama Kolom Teks**: Konfigurasi nama kolom yang berisi teks (default: `full_text`)
- ✅ **Label yang Diizinkan**: Input daftar label separated by comma
- ✅ **Ukuran Batch**: Konfigurasi jumlah data per batch API request
- ✅ **Tombol Start/Stop**: Kontrol proses pelabelan dengan aman
- ✅ **Real-time Logging**: Monitor progres dan error secara live

### 2. 🔍 **Tab Analisis Token** ⭐ _BARU_

**Fungsi**: Analisis biaya dan token sebelum pelabelan

- ✅ **Input Dataset**: Pilih file untuk analisis (independent dari tab utama)
- ✅ **Nama Kolom**: Specify kolom teks yang akan dianalisis
- ✅ **Ukuran Batch**: Test dengan ukuran batch tertentu
- ✅ **Analisis Real-time**: Request langsung ke model untuk akurasi
- ✅ **Estimasi Biaya**: Kalkulasi biaya input token yang akurat
- ✅ **Preview Token**: Menampilkan jumlah token per batch dan total
- ✅ **Rekomendasi Batch**: Saran ukuran batch optimal

**Output yang Ditampilkan**:

```
📊 INFORMASI DATASET:
   Dataset: sample_data
   Total Baris: 618
   Baris Sampel: 10

🎯 KONFIGURASI PEMROSESAN:
   Model Gemini: gemini-2.5-pro
   Ukuran Batch: 10
   Total Batch: 62

🔢 ANALISIS TOKEN:
   Token Input per Batch: 2,191
   Total Token Input: 135,842

💰 ESTIMASI BIAYA:
   Biaya per Batch: $0.0077
   Total Estimasi: $0.48
```

### 3. 📈 **Tab Statistik Request** ⭐ _BARU_

**Fungsi**: Monitoring quota dan performance real-time

- ✅ **Real-time Statistics**: Refresh manual dan auto-refresh setiap 5 detik
- ✅ **Request Tracking**: Counter detail per API key dan model
- ✅ **Success Rate**: Persentase keberhasilan request
- ✅ **Response Time**: Average, min, max response time
- ✅ **Quota Monitoring**: Prediksi kapan akan hit limit
- ✅ **Export Statistics**: Save statistik ke file untuk analisis
- ✅ **Clear Statistics**: Reset semua tracking data

**Informasi yang Ditampilkan**:

```
📅 Session: 0:15:34 (started: 2025-10-04T22:45:12)
📊 Total Requests: 247
✅ Success Rate: 94.3% (233/247)
⚡ Avg Response Time: 1.23s
🚀 Request Rate: 15.8 req/min

🔑 API KEY STATISTICS:
API_KEY_1: 62 requests (96.8% success)
API_KEY_2: 58 requests (93.1% success)

🤖 MODEL STATISTICS:
gemini-2.5-pro: 89 requests (98.9% success)
gemini-2.5-flash: 94 requests (93.6% success)

📈 QUOTA PREDICTIONS:
⚠️  gemini-2.5-pro: 89/100 (89.0%)
   └─ Est. limit in: 2.3 hours
✅ gemini-2.5-flash: 94/250 (37.6%)
```

### 4. 📁 **Tab Hasil**

**Fungsi**: Monitoring file output dan hasil pelabelan

- ✅ **Ringkasan Pekerjaan**: Waktu mulai, selesai, durasi
- ✅ **Daftar File**: Tree view semua file yang dihasilkan
- ✅ **Kategorisasi**: Labeled, Unlabeled, Final files
- ✅ **Info Ukuran**: File size dalam KB
- ✅ **Auto Refresh**: Update otomatis setelah pelabelan

### 5. 🤖 **Tab Chat Tester**

**Fungsi**: Testing prompt langsung ke model

- ✅ **Input Prompt**: Multi-line text input
- ✅ **Send Request**: Kirim langsung ke Gemini API
- ✅ **Response Display**: Hasil response dalam format yang readable
- ✅ **Error Handling**: Display error message jika ada masalah API

### 6. 📝 **Tab Editor Prompt**

**Fungsi**: Edit template prompt secara visual

- ✅ **Visual Editor**: Multi-line text editor dengan syntax highlighting
- ✅ **Save/Load**: Simpan perubahan ke `prompt_template.txt`
- ✅ **Reload**: Muat ulang dari file jika ada perubahan eksternal

### 7. ⚙️ **Tab Pengaturan**

**Fungsi**: Konfigurasi environment dan API

- ✅ **Model Configuration**: Setup MODEL_NAME dan fallback list
- ✅ **Directory Settings**: OUTPUT_DIR dan DATASET_DIR
- ✅ **API Keys Management**: Input multiple API keys (satu per baris)
- ✅ **Save to .env**: Simpan semua konfigurasi ke file environment

### 8. ❓ **Tab Bantuan**

**Fungsi**: Dokumentasi dan troubleshooting

- ✅ **Panduan Workflow**: Step-by-step usage guide
- ✅ **Fitur Explanation**: Penjelasan semua fitur aplikasi
- ✅ **Troubleshooting**: Common issues dan solusinya
- ✅ **Tips Optimasi**: Best practices untuk efisiensi dan performance

## 🔧 Fitur Backend yang Terintegrasi

### ⚡ **Model Fallback System**

- Otomatis beralih ke model lain jika quota habis
- Support 5 model Gemini terbaru
- Logging detail setiap rotasi model

### 📊 **Request Tracking System**

- Real-time monitoring setiap API request
- Success rate dan response time tracking
- Quota usage prediction dengan akurasi tinggi
- Persistent storage untuk historical data

### 💰 **Token Analysis**

- Kalkulasi token dengan request ke model actual
- Estimasi biaya yang akurat per batch dan total
- Fallback estimation jika model tidak support count_tokens

### 🔄 **Auto-resume Capability**

- Checkpoint system untuk melanjutkan dari batch terakhir
- Detection file yang sudah selesai diproses
- Graceful shutdown dengan tombol stop

## 🚀 Cara Menggunakan

### 1. **Setup Awal**

1. Buka **Tab Pengaturan**
2. Masukkan API keys Google Generative AI (satu per baris)
3. Konfigurasi model fallback list
4. Set direktori output dan dataset
5. Klik **"Simpan Pengaturan ke .env"**

### 2. **Analisis Biaya (Recommended)**

1. Buka **Tab Analisis Token**
2. Pilih file dataset yang akan diproses
3. Set nama kolom teks (default: `full_text`)
4. Set ukuran batch untuk testing (mulai dari 10-20)
5. Klik **"🔍 Analisis Token dan Biaya"**
6. Review estimasi biaya dan token usage

### 3. **Pelabelan Dataset**

1. Buka **Tab Proses Utama**
2. Pilih file dataset (.csv atau .xlsx)
3. Konfigurasi nama kolom teks
4. Set label yang diizinkan (separated by comma)
5. Set ukuran batch berdasarkan hasil analisis token
6. Klik **"Mulai Proses Pelabelan"**
7. Monitor progres di real-time logging

### 4. **Monitoring Performance**

1. Buka **Tab Statistik Request**
2. Enable **"Auto-refresh (5s)"** untuk monitoring real-time
3. Monitor quota usage dan success rate
4. Export statistik jika diperlukan untuk analisis

### 5. **Review Hasil**

1. Buka **Tab Hasil**
2. Check ringkasan pekerjaan (waktu, durasi)
3. Review file yang dihasilkan
4. Download atau analisis file final

## 🔍 Debugging dan Troubleshooting

### **❌ Error Token Limit**

1. Gunakan **Tab Analisis Token** untuk cek ukuran optimal
2. Kurangi ukuran batch di **Tab Proses Utama**
3. Monitor di **Tab Statistik Request**

### **❌ Error Quota**

1. Check quota usage di **Tab Statistik Request**
2. Add more API keys di **Tab Pengaturan**
3. Enable model fallback system

### **❌ Error Dataset**

1. Pastikan format file CSV/XLSX
2. Check nama kolom di **Tab Analisis Token** dulu
3. Validate data tidak ada yang kosong

## 🎯 Best Practices

### **💡 Efisiensi Biaya**

- Selalu gunakan **Tab Analisis Token** sebelum pelabelan besar
- Test dengan ukuran batch kecil (10-20) dulu
- Monitor quota di **Tab Statistik Request**

### **⚡ Performance Optimization**

- Setup multiple API keys untuk throughput maksimal
- Enable auto-refresh di **Tab Statistik Request**
- Gunakan model fallback untuk reliability

### **🛡️ Data Safety**

- Sistem checkpoint otomatis save progress
- Graceful shutdown dengan tombol stop
- File backup otomatis di folder output

---

## 🎉 **Kesimpulan**

GUI Auto-Labeling sekarang merupakan **enterprise-grade application** dengan fitur-fitur:

✅ **Professional UI/UX** dengan 8 tab terorganisir
✅ **Real-time monitoring** dengan statistik detail
✅ **Cost estimation** sebelum processing
✅ **Quota management** dengan prediksi akurat  
✅ **Auto-resume capability** untuk reliability
✅ **Multi-API key support** untuk scalability
✅ **Model fallback system** untuk high availability

**🚀 Ready for production use dengan dataset skala besar!**
