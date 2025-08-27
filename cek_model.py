import google.generativeai as genai
from dotenv import load_dotenv
import os

# Muat API Key Anda
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY_1') # Ambil salah satu kunci Anda untuk pengecekan
if not GOOGLE_API_KEY:
    raise ValueError("Pastikan GOOGLE_API_KEY_1 ada di file .env Anda")

genai.configure(api_key=GOOGLE_API_KEY)

print("Mencari model yang mendukung metode 'generateContent'...\n")

# Iterasi melalui semua model yang tersedia
for model in genai.list_models():
  # Periksa apakah metode 'generateContent' didukung oleh model ini
  if 'generateContent' in model.supported_generation_methods:
    print(f"- {model.name}")