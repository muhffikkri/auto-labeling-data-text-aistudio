# Single File Output System - Resume Capability Implementation

## Overview

Sistem labeling yang baru menggunakan pendekatan single file output dengan resume capability untuk efisiensi dan kemudahan pengelolaan.

## Key Features

### 1. Single File Output

- **Format**: `namafile_labeled_YYYYMMDD_HHMMSS.xlsx`
- **Lokasi**: `results/[project_name]/`
- **Konsep**: Copy dataset original ke results folder, kemudian update in-place

### 2. Resume Capability

- **Auto-detect existing files** dengan pattern yang sama
- **Analisis progress** otomatis saat file dipilih
- **Smart resume** dari posisi terakhir yang belum complete

### 3. Batch Optimization

- **Skip complete batches** - batch yang sudah 100% dilabeli
- **Skip partial batches** - untuk efisiensi quota (hindari pekerjaan kecil)
- **Focus on empty batches** - proses hanya batch yang benar-benar kosong

## Implementation Details

### Helper Functions

#### `create_or_resume_output_file(df_master, base_name, output_dir)`

```python
# Returns: (filepath, working_df, progress_info)
- filepath: Path ke file output (existing atau baru)
- working_df: DataFrame untuk dikerjakan
- progress_info: {'total': int, 'labeled': int, 'unlabeled': int, 'percent': float}
```

**Logic:**

1. Cek file existing dengan pattern `{base_name}_labeled_*.xlsx`
2. Jika ada, gunakan file terbaru dan load progress
3. Jika tidak ada, buat file baru dari master dataset
4. Return progress information

#### `find_optimal_batches(df, batch_size)`

```python
# Returns: List[(start_idx, end_idx)] untuk batch yang perlu diproses
```

**Logic:**

1. Scan semua batch dalam dataset
2. Skip batch yang sudah complete (100% labeled)
3. Skip batch yang parsial (ada beberapa label) - tidak efisien untuk quota
4. Return hanya batch yang benar-benar kosong

### GUI Progress Tracking

#### New UI Elements

- **Total Baris**: Menampilkan jumlah total baris dataset
- **Sudah Dilabeli**: Counter baris yang sudah memiliki label (warna hijau)
- **Belum Dilabeli**: Counter baris yang belum dilabeli (warna merah)
- **Progress**: Persentase progress (warna biru)
- **Progress Bar**: Visual progress bar

#### Methods

- `update_progress_tracking()`: Update display elements
- `check_and_update_progress_from_file()`: Auto-check progress saat file dipilih

## Workflow

### 1. File Selection

```
User pilih file → Auto-detect existing output → Display current progress
```

### 2. Processing Start

```
Load working_df → Find optimal batches → Process empty batches only
```

### 3. Batch Processing

```
For each optimal batch:
  - Process unlabeled rows only
  - Update working_df in-place
  - Save to single output file
  - Update progress display
```

### 4. Resume Logic

```
Next run → Load existing file → Continue from where left off
```

## Benefits

### ✅ Efficiency

- **Quota Optimization**: Skip partial batches untuk fokus pada pekerjaan besar
- **No Redundant Work**: Resume dari posisi tepat tanpa mengulang
- **Single File Management**: Mudah track dan kelola

### ✅ User Experience

- **Real-time Progress**: Lihat progress secara live
- **Auto-resume**: Tidak perlu setup manual untuk melanjutkan
- **Clear Status**: Tahu persis berapa yang sudah dan belum dikerjakan

### ✅ Reliability

- **Interruption Safe**: Bisa dihentikan kapan saja dan dilanjutkan
- **No Data Loss**: Semua progress tersimpan incrementally
- **Error Recovery**: Partial results tetap tersimpan

## File Structure

### Before (Multi-file)

```
results/project_name/
├── batch001_050.xlsx
├── batch051_100.xlsx
├── batch101_150.xlsx
└── ...
```

### After (Single-file)

```
results/project_name/
└── project_name_labeled_20251005_143022.xlsx
```

## Usage Examples

### 1. New Project

```python
# User pilih dataset baru
# Sistem buat: project_name_labeled_20251005_143022.xlsx
# Progress: 0/1000 (0.0%)
```

### 2. Resume Existing

```python
# User pilih dataset yang sama
# Sistem detect: project_name_labeled_20251005_143022.xlsx
# Progress: 450/1000 (45.0%) - auto resume dari sini
```

### 3. Batch Optimization

```python
# Batch 1-50: Complete (skip)
# Batch 51-100: Partial 30/50 (skip - tidak efisien)
# Batch 101-150: Empty 0/50 (process)
# Batch 151-200: Empty 0/50 (process)
```

## Future Enhancements

### Potential Improvements

1. **Configurable Batch Strategy**: Allow processing partial batches if desired
2. **Progress Persistence**: Save progress info in separate metadata file
3. **Multi-file Support**: Option to maintain both single and multi-file outputs
4. **Background Auto-save**: Auto-save every N processed items

### Risk Mitigation

1. **File Corruption**: Regular backup during processing
2. **Memory Usage**: Stream processing for very large datasets
3. **Performance**: Optimize DataFrame operations for large files

## Conclusion

Sistem single file output dengan resume capability memberikan:

- **Simplified workflow** dengan manajemen file yang lebih mudah
- **Efficient quota usage** dengan fokus pada batch optimal
- **Better user experience** dengan progress tracking yang jelas
- **Reliable operation** dengan resume capability yang robust

Sistem ini siap untuk production use dan testing dengan dataset real.
