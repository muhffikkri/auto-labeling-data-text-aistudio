# src/gui/app.py

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import queue
import logging
import threading
import os
from datetime import datetime
import glob

# Mengimpor fungsi logic, env manager, dan utils  
from src.core_logic import process
from src.core_logic import env_manager
from src.core_logic import utils  

class QueueHandler(logging.Handler):
    """
    Handler logging khusus untuk mengirim pesan log ke dalam Queue.

    Digunakan agar log Python bisa diteruskan ke antarmuka GUI 
    melalui antrian (`queue.Queue`) dan ditampilkan secara real-time.

    Args:
        log_queue (queue.Queue): Antrian tempat pesan log dimasukkan.
    """
    def __init__(self, log_queue):
        """Inisialisasi QueueHandler dengan objek antrian log."""
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        """
        Memasukkan pesan log yang diformat ke dalam antrian.

        Args:
            record (logging.LogRecord): Objek log yang dikirim oleh logging.
        """
        self.log_queue.put(self.format(record))

class LabelingApp(tk.Tk):
    """
    Aplikasi GUI untuk pelabelan otomatis dataset teks menggunakan model Gemini.

    Aplikasi ini menyediakan antarmuka interaktif untuk:
      - Memilih dataset (.csv / .xlsx).
      - Menentukan label yang diizinkan & ukuran batch.
      - Memulai / menghentikan proses pelabelan.
      - Memantau progres melalui log real-time.
      - Melihat hasil batch maupun file final.
      - Mengelola konfigurasi (.env).
      - Menguji prompt langsung ke model (Chat Tester).
      - Membaca dokumentasi penggunaan.

    Inherits:
        tk.Tk: Kelas utama untuk aplikasi tkinter.
    """
    
    def __init__(self):
        """Inisialisasi jendela utama, tab, logging, dan variabel kontrol GUI."""
        super().__init__()

        self.title("Aplikasi Pelabelan Otomatis")
        self.geometry("900x700")

        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        self.stop_event = threading.Event()
        self.start_time = None
        self.end_time = None

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(pady=10, padx=10, fill="both", expand=True)

        # Membuat Frame untuk setiap Tab
        self.main_tab = ttk.Frame(self.notebook, padding="10")
        self.results_tab = ttk.Frame(self.notebook, padding="10")
        self.chat_tab = ttk.Frame(self.notebook, padding="10")  
        self.prompt_tab = ttk.Frame(self.notebook, padding="10")
        self.settings_tab = ttk.Frame(self.notebook, padding="10")
        self.help_tab = ttk.Frame(self.notebook, padding="10")

        self.notebook.add(self.main_tab, text='Proses Utama')
        self.notebook.add(self.results_tab, text='Hasil')
        self.notebook.add(self.chat_tab, text='Chat Tester')  
        self.notebook.add(self.prompt_tab, text='Editor Prompt')
        self.notebook.add(self.settings_tab, text='Pengaturan')
        self.notebook.add(self.help_tab, text='Bantuan')

        # Mengisi konten setiap tab
        self.create_main_tab_widgets()
        self.create_results_tab_widgets()
        self.create_chat_tab_widgets()  
        self.create_prompt_tab_widgets()
        self.create_settings_tab_widgets()
        self.create_help_tab_widgets()
        
        self.load_settings_to_gui()
        self.load_prompt_to_gui()

        # Setup logging
        self.log_queue = queue.Queue()
        self.queue_handler = QueueHandler(self.log_queue)
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", handlers=[self.queue_handler])
        self.after(100, self.process_log_queue)
    
    def create_main_tab_widgets(self):
        """
        Membuat widget pada tab 'Proses Utama'.

        Termasuk:
            - Input file dataset.
            - Input daftar label yang diizinkan.
            - Input ukuran batch.
        """
        controls_frame = ttk.LabelFrame(self.main_tab, text="Pengaturan Proses", padding="10")
        controls_frame.pack(fill=tk.X, pady=5)
        controls_frame.columnconfigure(1, weight=1)

        # Input file 
        ttk.Label(controls_frame, text="File Dataset:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.filepath_var = tk.StringVar()
        filepath_entry = ttk.Entry(controls_frame, textvariable=self.filepath_var, state="readonly")
        filepath_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        browse_button = ttk.Button(controls_frame, text="Pilih File...", command=self.browse_file)
        browse_button.grid(row=0, column=2, padx=5, pady=5)

        # --- PERUBAHAN: Input untuk Nama Kolom Teks ---
        ttk.Label(controls_frame, text="Nama Kolom Teks:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.text_column_var = tk.StringVar(value="full_text") # Default value
        text_column_entry = ttk.Entry(controls_frame, textvariable=self.text_column_var)
        text_column_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        # Input untuk Label yang Diizinkan 
        ttk.Label(controls_frame, text="Label yang Diizinkan\n(dipisah koma):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.allowed_labels_var = tk.StringVar(value="positif, negatif, netral, tidak relevan")
        allowed_labels_entry = ttk.Entry(controls_frame, textvariable=self.allowed_labels_var)
        allowed_labels_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        
        # Input Batch Size 
        ttk.Label(controls_frame, text="Ukuran Batch:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.batch_size_var = tk.StringVar(value="50")
        batch_size_entry = ttk.Entry(controls_frame, textvariable=self.batch_size_var)
        batch_size_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        # --- PERBAIKAN: Pindahkan Tombol Start/Stop ke sini ---
        # Frame untuk tombol Start dan Stop
        buttons_frame = ttk.Frame(self.main_tab)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        self.start_button = ttk.Button(buttons_frame, text="Mulai Proses Pelabelan", command=self.start_labeling_thread)
        self.start_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        self.stop_button = ttk.Button(buttons_frame, text="Hentikan Proses", command=self.stop_labeling, state="disabled")
        self.stop_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        # ---------------------------------------------------

        # --- PERBAIKAN: Pindahkan Log Output ke sini ---
        # Frame untuk Log Output
        log_frame = ttk.LabelFrame(self.main_tab, text="Log Proses", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True) # expand=True agar mengisi sisa ruang
        
        self.log_text = scrolledtext.ScrolledText(log_frame, state="disabled", wrap=tk.WORD, bg="#2b2b2b", fg="white")
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def create_prompt_tab_widgets(self):
        """
        Membuat widget pada tab 'Editor Prompt'.

        Termasuk:
            - Editor teks untuk mengedit isi `prompt_template.txt`.
            - Tombol "Simpan" untuk menulis perubahan ke file.
            - Tombol "Muat Ulang" untuk membaca ulang isi file.
        """
        prompt_frame = ttk.LabelFrame(self.prompt_tab, text="Template Prompt (prompt_template.txt)", padding="10")
        prompt_frame.pack(fill=tk.BOTH, expand=True)

        self.prompt_text_editor = scrolledtext.ScrolledText(prompt_frame, wrap=tk.WORD, relief="solid", borderwidth=1, height=10)
        self.prompt_text_editor.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        buttons_frame = ttk.Frame(prompt_frame)
        buttons_frame.pack(fill=tk.X)
        
        save_button = ttk.Button(buttons_frame, text="Simpan Perubahan ke File", command=self.save_prompt_from_gui)
        save_button.pack(side=tk.RIGHT, padx=5)
        
        reload_button = ttk.Button(buttons_frame, text="Muat Ulang dari File", command=self.load_prompt_to_gui)
        reload_button.pack(side=tk.RIGHT)

    def create_results_tab_widgets(self):
        """
        Membuat widget pada tab 'Hasil'.

        Termasuk:
            - Ringkasan pekerjaan (mulai, selesai, durasi).
            - Daftar file hasil (labeled, unlabeled, final).
            - Tombol refresh daftar file.
        """
        summary_frame = ttk.LabelFrame(self.results_tab, text="Ringkasan Pekerjaan", padding="10")
        summary_frame.pack(fill=tk.X, pady=5)
        summary_frame.columnconfigure(1, weight=1)
        self.start_time_var = tk.StringVar(value="-")
        self.end_time_var = tk.StringVar(value="-")
        self.duration_var = tk.StringVar(value="-")
        ttk.Label(summary_frame, text="Waktu Mulai:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        ttk.Label(summary_frame, textvariable=self.start_time_var).grid(row=0, column=1, padx=5, pady=2, sticky="w")
        ttk.Label(summary_frame, text="Waktu Selesai:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        ttk.Label(summary_frame, textvariable=self.end_time_var).grid(row=1, column=1, padx=5, pady=2, sticky="w")
        ttk.Label(summary_frame, text="Total Durasi:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        ttk.Label(summary_frame, textvariable=self.duration_var).grid(row=2, column=1, padx=5, pady=2, sticky="w")
        files_frame = ttk.LabelFrame(self.results_tab, text="File yang Dihasilkan", padding="10")
        files_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        refresh_button = ttk.Button(files_frame, text="🔄 Refresh Daftar File", command=self.refresh_results_view)
        refresh_button.pack(anchor="ne", pady=5)
        self.results_tree = ttk.Treeview(files_frame, columns=("filename", "subfolder", "size"), show="headings")
        self.results_tree.heading("filename", text="Nama File")
        self.results_tree.heading("subfolder", text="Kategori")
        self.results_tree.heading("size", text="Ukuran")
        self.results_tree.column("filename", width=400)
        self.results_tree.column("subfolder", width=100)
        self.results_tree.column("size", width=100, anchor="e")
        scrollbar = ttk.Scrollbar(files_frame, orient="vertical", command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def create_chat_tab_widgets(self):
        """
        Membuat widget pada tab 'Chat Tester'.

        Termasuk:
            - Area output untuk menampilkan respons AI.
            - Area input untuk memasukkan prompt.
            - Tombol kirim untuk mengirim prompt ke model.
        """
        chat_frame = ttk.Frame(self.chat_tab)
        chat_frame.pack(fill=tk.BOTH, expand=True)

        # Area untuk menampilkan respons AI
        response_frame = ttk.LabelFrame(chat_frame, text="Respons AI", padding="10")
        response_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.chat_response_text = scrolledtext.ScrolledText(response_frame, state="disabled", wrap=tk.WORD, bg="#f0f0f0")
        self.chat_response_text.pack(fill=tk.BOTH, expand=True)

        # Area untuk input prompt
        prompt_frame = ttk.LabelFrame(chat_frame, text="Masukkan Prompt Anda", padding="10")
        prompt_frame.pack(fill=tk.X)
        self.chat_prompt_text = tk.Text(prompt_frame, height=5, relief="solid", borderwidth=1)
        self.chat_prompt_text.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=(0, 10))
        
        self.chat_send_button = ttk.Button(prompt_frame, text="Kirim", command=self.send_chat_prompt_thread)
        self.chat_send_button.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT)

    def create_settings_tab_widgets(self):
        """
        Membuat widget pada tab 'Pengaturan'.

        Menyediakan input untuk mengedit nilai di file `.env`:
            - MODEL_NAME
            - OUTPUT_DIR
            - DATASET_DIR
            - GOOGLE_API_KEYs
        """
        settings_frame = ttk.LabelFrame(self.settings_tab, text="Konfigurasi .env", padding="10")
        settings_frame.pack(fill=tk.BOTH, expand=True)
        settings_frame.columnconfigure(1, weight=1)
        ttk.Label(settings_frame, text="MODEL_NAME:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.model_name_var = tk.StringVar()
        ttk.Entry(settings_frame, textvariable=self.model_name_var).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Label(settings_frame, text="OUTPUT_DIR:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.output_dir_var = tk.StringVar()
        ttk.Entry(settings_frame, textvariable=self.output_dir_var).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ttk.Label(settings_frame, text="DATASET_DIR:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.dataset_dir_var = tk.StringVar()
        ttk.Entry(settings_frame, textvariable=self.dataset_dir_var).grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        ttk.Label(settings_frame, text="GOOGLE_API_KEYs\n(satu per baris):").grid(row=3, column=0, padx=5, pady=5, sticky="nw")
        self.api_keys_text = tk.Text(settings_frame, height=5, width=40, relief="solid", borderwidth=1)
        self.api_keys_text.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        save_button = ttk.Button(settings_frame, text="Simpan Pengaturan ke .env", command=self.save_settings_from_gui)
        save_button.grid(row=4, column=0, columnspan=2, pady=15, sticky="ew")
        
    def create_help_tab_widgets(self):
        """
        Membuat widget pada tab 'Bantuan'.

        Menampilkan teks panduan cepat, mekanisme aplikasi,
        serta persyaratan dataset.
        """
        help_text_content = """Selamat Datang di Aplikasi Pelabelan Otomatis!

Aplikasi ini dirancang untuk mempermudah proses pelabelan data teks dalam jumlah besar menggunakan Google AI (Gemini).

===============================
Panduan Cepat (Workflow)
===============================
1.  Tab Pengaturan: Pastikan semua konfigurasi (nama model, direktori, API key) sudah benar. Klik "Simpan" jika Anda melakukan perubahan.
2.  Tab Proses Utama: Klik "Pilih File..." untuk memilih dataset Anda.
3.  Tab Proses Utama: Atur "Ukuran Batch" (jumlah baris per permintaan API). Nilai yang lebih kecil (misal: 20-50) lebih aman dari error token limit.
4.  Klik "Mulai Proses Pelabelan".
5.  Pantau log di Tab Proses Utama dan lihat file yang dihasilkan di Tab Hasil.
6.  Jika perlu, klik "Hentikan Proses". Proses akan berhenti dengan aman setelah batch saat ini selesai.

===============================
Mekanisme Aplikasi
===============================
-   Batching: Data Anda tidak dikirim sekaligus, melainkan dalam potongan-potongan kecil (batch) untuk efisiensi dan menghindari limit API.
-   Checkpoint: Setelah setiap batch berhasil diproses, hasilnya langsung disimpan sebagai file Excel kecil. Jika aplikasi error atau ditutup, Anda bisa menjalankannya lagi tanpa kehilangan progres.
-   Rotasi API Key: Jika Anda memasukkan lebih dari satu API key dan terjadi error kuota, aplikasi akan otomatis beralih ke key berikutnya.
-   Logging: Semua aktivitas, peringatan, dan error dicatat di Tab Proses Utama dan juga disimpan permanen di folder `logs/`.

===============================
Persyaratan Dataset
===============================
-   Format file harus .csv atau .xlsx.
-   WAJIB memiliki kolom dengan nama persis `full_text` yang berisi teks untuk dilabeli.
"""
        help_frame = ttk.Frame(self.help_tab, padding="10")
        help_frame.pack(fill=tk.BOTH, expand=True)
        help_text = scrolledtext.ScrolledText(help_frame, wrap=tk.WORD, state="normal", bg="#f0f0f0")
        help_text.insert(tk.END, help_text_content)
        help_text.configure(state="disabled")
        help_text.pack(fill=tk.BOTH, expand=True)

    def load_prompt_to_gui(self):
        """Membaca file prompt_template.txt dan menampilkannya di editor."""
        try:
            with open("prompt_template.txt", "r", encoding="utf-8") as f:
                prompt_content = f.read()
            self.prompt_text_editor.delete("1.0", tk.END)
            self.prompt_text_editor.insert("1.0", prompt_content)
        except FileNotFoundError:
            messagebox.showerror("Error", "File 'prompt_template.txt' tidak ditemukan. Buat file tersebut terlebih dahulu.")
        except Exception as e:
            messagebox.showerror("Error Membaca File", f"Gagal memuat prompt: {e}")

    def save_prompt_from_gui(self):
        """Menyimpan konten dari editor ke file prompt_template.txt."""
        try:
            prompt_content = self.prompt_text_editor.get("1.0", tk.END)
            with open("prompt_template.txt", "w", encoding="utf-8") as f:
                f.write(prompt_content)
            messagebox.showinfo("Berhasil", "Template prompt berhasil disimpan ke 'prompt_template.txt'.")
        except Exception as e:
            messagebox.showerror("Error Menyimpan File", f"Gagal menyimpan prompt: {e}")
            
    def send_chat_prompt_thread(self):
        """
        Memulai thread baru untuk mengirim prompt dari tab Chat Tester.

        - Mengecek apakah prompt kosong.
        - Menonaktifkan tombol/input saat request berlangsung.
        - Menjalankan `run_chat_task` di thread terpisah.
        """
        prompt = self.chat_prompt_text.get("1.0", tk.END).strip()
        if not prompt:
            messagebox.showwarning("Peringatan", "Prompt tidak boleh kosong.")
            return

        # Nonaktifkan tombol dan input untuk mencegah permintaan ganda
        self.chat_send_button.config(state="disabled")
        self.chat_prompt_text.config(state="disabled")

        # Jalankan di thread terpisah
        threading.Thread(
            target=self.run_chat_task,
            args=(prompt,),
            daemon=True
        ).start()

    def run_chat_task(self, prompt):
        """
        Worker di background untuk mengirim prompt ke model Gemini.

        Args:
            prompt (str): Teks prompt yang dimasukkan user.

        Alur:
            - Menampilkan pesan "loading".
            - Memanggil `utils.test_single_prompt`.
            - Menampilkan respons atau error di GUI.
        """
        try:
            # Tampilkan pesan loading di GUI
            self.chat_response_text.config(state="normal")
            self.chat_response_text.delete("1.0", tk.END)
            self.chat_response_text.insert("1.0", "⏳ Meminta respons dari AI, harap tunggu...")
            self.chat_response_text.config(state="disabled")

            # Panggil fungsi dari utils
            response_text = utils.test_single_prompt(prompt)

            # Tampilkan hasil di GUI
            self.chat_response_text.config(state="normal")
            self.chat_response_text.delete("1.0", tk.END)
            self.chat_response_text.insert("1.0", response_text)
            self.chat_response_text.config(state="disabled")

        except Exception as e:
            error_message = f"💥 Terjadi Error:\n\n{e}\n\nPastikan GOOGLE_API_KEY_1 di tab Pengaturan sudah benar dan valid."
            self.chat_response_text.config(state="normal")
            self.chat_response_text.delete("1.0", tk.END)
            self.chat_response_text.insert("1.0", error_message)
            self.chat_response_text.config(state="disabled")
            messagebox.showerror("Error API", error_message)
        finally:
            # Aktifkan kembali tombol dan input
            self.chat_send_button.config(state="normal")
            self.chat_prompt_text.config(state="normal")

    def load_settings_to_gui(self):  
        """
        Membaca konfigurasi dari file `.env` lalu menampilkan ke GUI.

        Variabel yang dimuat:
            - MODEL_NAME
            - OUTPUT_DIR
            - DATASET_DIR
            - GOOGLE_API_KEYs
        """
        try:
            settings, api_keys = env_manager.load_env_variables()
            self.model_name_var.set(settings.get("MODEL_NAME", ""))
            self.output_dir_var.set(settings.get("OUTPUT_DIR", ""))
            self.dataset_dir_var.set(settings.get("DATASET_DIR", ""))
            self.api_keys_text.delete("1.0", tk.END)
            self.api_keys_text.insert("1.0", "\n".join(api_keys))
        except Exception as e: messagebox.showerror("Error Baca .env", f"Gagal memuat konfigurasi dari .env: {e}")

    def save_settings_from_gui(self):  
        """
        Menyimpan konfigurasi dari GUI ke file `.env`.

        Akan menimpa file `.env` lama dengan nilai baru.
        """
        try:
            settings = { "MODEL_NAME": self.model_name_var.get(), "OUTPUT_DIR": self.output_dir_var.get(), "DATASET_DIR": self.dataset_dir_var.get() }
            api_keys = self.api_keys_text.get("1.0", tk.END).strip().split("\n")
            env_manager.save_env_variables(settings, api_keys)
            messagebox.showinfo("Berhasil", "Pengaturan telah berhasil disimpan ke file .env.")
        except Exception as e: messagebox.showerror("Error Simpan .env", f"Gagal menyimpan konfigurasi ke .env: {e}")
    
    def browse_file(self):  
        """
        Membuka file dialog untuk memilih dataset (.csv / .xlsx).

        Hasil path file disimpan ke `self.filepath_var`.
        """
        filepath = filedialog.askopenfilename(title="Pilih file dataset", filetypes=[("All supported", ".csv .xlsx"), ("CSV files", "*.csv"), ("Excel files", "*.xlsx")])
        if filepath: self.filepath_var.set(filepath)

    def process_log_queue(self):  
        """
        Memproses antrian log dan menampilkannya di widget log GUI.

        Dipanggil secara periodik setiap 100 ms dengan `after()`.
        """
        try:
            while True:
                record = self.log_queue.get(block=False)
                self.log_text.configure(state="normal")
                self.log_text.insert(tk.END, record + "\n")
                self.log_text.configure(state="disabled")
                self.log_text.see(tk.END)
        except queue.Empty: pass
        self.after(100, self.process_log_queue)

    def stop_labeling(self):  
        """
        Menghentikan proses pelabelan secara aman.

        - Menyetel `stop_event`.
        - Menonaktifkan tombol stop.
        - Proses akan berhenti setelah batch berjalan selesai.
        """
        logging.info("Tombol HENTIKAN ditekan. Proses akan berhenti setelah batch saat ini selesai...")
        self.stop_event.set()
        self.stop_button.config(state="disabled")

    def start_labeling_thread(self):  
        """
        Memulai thread baru untuk proses pelabelan dataset.

        Validasi:
            - File dataset sudah dipilih.
            - Batch size valid.
            - Label yang diizinkan tidak kosong.

        Menyimpan informasi waktu mulai & mengatur state tombol.
        """
        filepath = self.filepath_var.get(); 
        if not filepath: messagebox.showerror("Error", "Silakan pilih file dataset terlebih dahulu."); return
        try: batch_size = int(self.batch_size_var.get())
        except ValueError: messagebox.showerror("Error", "Ukuran batch harus berupa angka."); return

        # Ambil dan proses daftar label dari GUI 
        labels_string = self.allowed_labels_var.get().strip()
        if not labels_string:
            messagebox.showerror("Error", "Daftar 'Label yang Diizinkan' tidak boleh kosong.")
            return
        # Membersihkan input: split berdasarkan koma, hapus spasi, dan buang entri kosong
        allowed_labels = [label.strip() for label in labels_string.split(',') if label.strip()]
        if not allowed_labels:
            messagebox.showerror("Error", "Format 'Label yang Diizinkan' tidak valid.")
            return
        
        text_column = self.text_column_var.get().strip()
        if not text_column: messagebox.showerror("Error", "'Nama Kolom Teks' tidak boleh kosong."); return

        # Reset dan setup
        self.start_time = datetime.now()
        self.start_time_var.set(self.start_time.strftime("%Y-%m-%d %H:%M:%S"))
        self.end_time_var.set("Sedang berjalan...")
        self.duration_var.set("-")
        self.refresh_results_view()
        self.start_button.config(state="disabled", text="Sedang Memproses...")
        self.stop_button.config(state="normal")
        self.stop_event.clear()
        self.labeling_thread = threading.Thread(
            target=self.run_labeling_task,
            args=(filepath, batch_size, allowed_labels, text_column,self.stop_event),
            daemon=True
        )
        self.labeling_thread.start()

    def run_labeling_task(self, filepath, batch_size, allowed_labels, text_column, stop_event):  
        """
        Worker di background untuk memproses dataset.

        Args:
            filepath (str): Lokasi file dataset.
            batch_size (int): Jumlah data per batch.
            allowed_labels (List[str]): Label yang diperbolehkan.
            text_column (str): Nama kolom yang berisi teks.
            stop_event (threading.Event): Event untuk menghentikan proses.

        Proses:
            - Load dataset.
            - Panggil `process.label_dataset`.
            - Update GUI dengan status mulai, selesai, durasi.
        """
        try: 
            base_name = os.path.splitext(os.path.basename(filepath))[0]
            dataset_dir = os.path.dirname(filepath)
            process.load_config_and_keys()
            df, _ = process.open_dataset(dataset_dir, base_name)
            logging.info(f"✅ Dataset '{base_name}' dimuat. Total baris: {len(df)}")
            generation_config = {"temperature": 0.3, "top_p": 1.0, "top_k": 40}
            process.label_dataset(
                df_master=df, 
                base_name=base_name, 
                batch_size=batch_size, 
                max_retry=2, 
                text_column_name=text_column,
                generation_config=generation_config, 
                allowed_labels=allowed_labels, 
                stop_event=stop_event
            )
            if not stop_event.is_set(): logging.info("🎉🎉🎉 Proses Pelabelan Selesai! 🎉🎉🎉")
        except Exception as e:
            logging.critical("💥 Terjadi error fatal dalam proses pelabelan.", exc_info=True)
            if isinstance(e, KeyError):
                e = f"{e}\n\n-> Pastikan nama kolom '{text_column}' ada di file Anda."
            messagebox.showerror("Error Fatal", f"Terjadi error: {e}\n\nLihat file log untuk detail.")
        finally:
            self.end_time = datetime.now()
            self.end_time_var.set(self.end_time.strftime("%Y-%m-%d %H:%M:%S"))
            if self.start_time:
                duration = self.end_time - self.start_time
                total_seconds = int(duration.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                self.duration_var.set(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            self.start_button.config(state="normal", text="Mulai Proses Pelabelan")
            self.stop_button.config(state="disabled")
            self.refresh_results_view() 

    def refresh_results_view(self):  
        """
        Memperbarui daftar file hasil pelabelan di tab 'Hasil'.

        Mencari file dalam folder hasil sesuai struktur:
            - `labeled/`
            - `unlabeled/`
            - `final/`

        File yang ditemukan akan ditampilkan dalam Treeview 
        beserta informasi nama, kategori, dan ukuran.
        """
        for item in self.results_tree.get_children(): self.results_tree.delete(item)
        filepath = self.filepath_var.get()
        if not filepath: return
        settings, _ = env_manager.load_env_variables()
        base_name = os.path.splitext(os.path.basename(filepath))[0]
        output_dir = os.path.join(settings.get("OUTPUT_DIR", "results"), base_name)
        if not os.path.isdir(output_dir): return
        for subdir in ["labeled", "unlabeled", ""]:
            search_path = os.path.join(output_dir, subdir, "*.xlsx")
            for f in glob.glob(search_path):
                filename = os.path.basename(f)
                filesize_kb = round(os.path.getsize(f) / 1024, 2)
                category = os.path.basename(os.path.dirname(f)) if subdir else "Final"
                self.results_tree.insert("", "end", values=(filename, category.capitalize(), f"{filesize_kb} KB"))