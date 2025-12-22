"""Configurazione per l'API di Nano Banana (Google Gemini)"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configurazione dell'applicazione"""
    # Google Gemini API Key (Nano Banana usa Gemini API)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", os.getenv("NANO_BANANA_API_KEY", ""))
    
    # fal.ai API Key per Hunyuan3D
    FAL_KEY = os.getenv("FAL_KEY", "")
    
    # Modelli disponibili:
    # - gemini-2.5-flash-image (Nano Banana) - veloce, 1024px
    # - gemini-3-pro-image-preview (Nano Banana Pro) - alta qualità, fino a 4K
    DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-image")
    PRO_MODEL = "gemini-3-pro-image-preview"
    
    # Directory per salvare le immagini generate
    OUTPUT_DIR = "generated_images"
    
    # Directory per salvare i modelli 3D generati
    OUTPUT_3D_DIR = "generated_3Dmodels"
    
    @classmethod
    def validate(cls):
        """Valida che la configurazione sia completa"""
        if not cls.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY non configurata. "
                "Imposta la variabile d'ambiente GEMINI_API_KEY o NANO_BANANA_API_KEY nel file .env. "
                "Ottieni la chiave su: https://ai.google.dev/"
            )

