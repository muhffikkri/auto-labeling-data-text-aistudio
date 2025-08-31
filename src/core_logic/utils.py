# src/core_logic/utils.py

import os
import google.generativeai as genai
from dotenv import load_dotenv
from typing import List

_is_api_configured = False

def setup_api_for_utils():
    """Mengonfigurasi API Key untuk fungsi utilitas."""
    global _is_api_configured
    if _is_api_configured:
        return

    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY_1")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY_1 tidak ditemukan di .env")
    genai.configure(api_key=api_key)
    _is_api_configured = True

def get_compatible_models() -> List[str]:
    """
    Mengembalikan daftar nama model yang mendukung 'generateContent'.
    """
    setup_api_for_utils()
    compatible_models = []
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            # Mengambil nama pendek (misal: 'gemini-1.5-pro-latest')
            short_name = model.name.split('/')[-1]
            compatible_models.append(short_name)
    return sorted(compatible_models)

def test_single_prompt(prompt: str) -> str:
    """
    Mengirim satu prompt ke model dan mengembalikan responsnya.
    """
    setup_api_for_utils()
    model_name = os.getenv("MODEL_NAME", "gemini-1.5-pro-latest")
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    return response.text