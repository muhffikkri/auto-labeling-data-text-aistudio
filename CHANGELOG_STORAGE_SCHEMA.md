# Changelog: Perubahan Skema Penyimpanan

## Perubahan Utama (2024)

### ✅ **Skema Penyimpanan Real-Time - Enhanced Stability**

**SEBELUM:** Folder terpisah labeled/unlabeled

```
output/
  project_name/
    labeled/
      batch001_labeled.xlsx
      batch002_labeled.xlsx
    unlabeled/
      batch003_unlabeled.xlsx
```

**SESUDAH:** Real-time storage per batch dengan semua status

```
output/
  project_name/
    project_name_batch001_050.xlsx  ← Semua baris (berhasil/gagal/belum)
    project_name_batch051_100.xlsx  ← Semua baris (berhasil/gagal/belum)
    project_name_batch101_150.xlsx  ← Semua baris (berhasil/gagal/belum)
    # Manual copy oleh user setelah review
```

### 🔧 **Keuntungan Skema Real-Time:**

1. **Crash Resistant**: Hasil tersimpan real-time, tidak hilang saat internet mati
2. **Complete Visibility**: Setiap file berisi SEMUA baris dengan status masing-masing
3. **Manual Review**: User kontrol penuh untuk review sebelum copy final
4. **Resume Friendly**: Proses dapat dilanjutkan dari batch terakhir
5. **Transparent Status**: Dapat melihat progress per batch secara real-time

### 📁 **Format File Real-Time:**

- **Batch Files**: `{project_name}_batch{start:03d}_{end:03d}.xlsx`
  - Contoh: `mydata_batch001_050.xlsx` (item 1-50)
  - Berisi SEMUA data batch:
    - ✅ Baris berhasil: ada label + justifikasi
    - ❌ Baris gagal: label kosong, justifikasi kosong
    - ⏳ Baris belum diproses: label kosong, justifikasi kosong
  - File disimpan setiap selesai proses batch

### 📊 **Status Tracking:**

Setiap file batch menunjukkan:

```
Log: 📊 Status: 45 labeled / 50 total rows
     Artinya: 45 berhasil, 5 gagal/belum diproses
```

### 🛡️ **Perlindungan Gangguan Eksternal:**

1. **Internet Terputus**: File batch tersimpan, dapat resume dari terakhir
2. **Program Crash**: Tidak ada data hilang, semua batch tersimpan
3. **Power Loss**: File batch sudah tersimpan di disk
4. **User Error**: Dapat review per batch sebelum copy manual

### 🔍 **Manual Review Process:**

1. **Check Progress**: Lihat log untuk status per batch
2. **Review Files**: Buka setiap file batch untuk periksa kualitas
3. **Quality Control**: Periksa label dan justifikasi yang dihasilkan
4. **Manual Copy**: Copy file yang sudah divalidasi ke lokasi final
5. **Selective Retry**: Hapus batch yang ingin diproses ulang

### 🚫 **Removed Features:**

- ❌ Auto-copy ke file `_COMPLETE.xlsx`
- ❌ Automatic file merging
- ❌ Folder split labeled/unlabeled

**Alasan**: User control lebih baik untuk quality assurance

### � **Detection Logic:**

Program otomatis deteksi status completion:

- ✅ **Fully Complete**: Semua batch ada & semua baris labeled
- 🔄 **Partial**: Beberapa batch masih ada baris kosong
- 🆕 **New Project**: Belum ada file batch

---

## Testing Status: ✅ PASSED

- ✅ Real-time storage logic implemented
- ✅ All rows preservation (success/fail/pending)
- ✅ Manual review workflow enabled
- ✅ Crash resistance enhanced
- ✅ Resume capability maintained
- ✅ Session logging preserved
