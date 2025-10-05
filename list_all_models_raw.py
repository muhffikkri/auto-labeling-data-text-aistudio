#!/usr/bin/env python3
"""
Utility sederhana untuk melihat SEMUA model yang tersedia dari Google Generative AI
tanpa formatting, hanya raw list.
"""

import google.generativeai as genai
import os
from dotenv import load_dotenv

def main():
    # Load environment
    load_dotenv()
    
    # Setup API
    api_key = os.getenv('GOOGLE_API_KEY_1')
    if not api_key:
        print("Error: GOOGLE_API_KEY_1 tidak ditemukan di .env")
        return
    
    genai.configure(api_key=api_key)
    
    # Get all models
    print("=== SEMUA MODEL GOOGLE GENERATIVE AI ===")
    models = list(genai.list_models())
    
    print(f"Total model tersedia: {len(models)}")
    print("\nDaftar model:")
    for i, model in enumerate(models, 1):
        # Remove 'models/' prefix untuk readability
        clean_name = model.name.replace('models/', '')
        print(f"{i:2d}. {clean_name}")
    
    # Kategorisasi otomatis berdasarkan nama
    print("\n=== KATEGORISASI OTOMATIS ===")
    
    categories = {
        "Gemini 2.5": [],
        "Gemini 2.0": [],
        "Gemini 1.5": [],
        "Gemma": [],
        "Embedding": [],
        "Imagen": [],
        "Veo": [],
        "Lainnya": []
    }
    
    for model in models:
        name = model.name.replace('models/', '')
        if 'gemini-2.5' in name:
            categories["Gemini 2.5"].append(name)
        elif 'gemini-2.0' in name:
            categories["Gemini 2.0"].append(name)
        elif 'gemini-1.5' in name or 'gemini-flash-latest' in name or 'gemini-pro-latest' in name:
            categories["Gemini 1.5"].append(name)
        elif 'gemma' in name:
            categories["Gemma"].append(name)
        elif 'embedding' in name:
            categories["Embedding"].append(name)
        elif 'imagen' in name:
            categories["Imagen"].append(name)
        elif 'veo' in name:
            categories["Veo"].append(name)
        else:
            categories["Lainnya"].append(name)
    
    for category, models_list in categories.items():
        if models_list:
            print(f"\n{category} ({len(models_list)} model):")
            for model in models_list:
                print(f"  - {model}")

if __name__ == "__main__":
    main()