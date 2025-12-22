from google import genai
from google.genai import types
from typing import Optional, Dict, Any
from pathlib import Path
from PIL import Image
from config import Config

class NanoBananaClient:
    """
    Client per le API di Nano Banana (Google Gemini Image Generation)
    """
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Inizializza il client per l'API di Gemini
        
        Args:
            api_key: Chiave API di Google Gemini (se None, usa Config.GEMINI_API_KEY)
            model: Modello da usare (gemini-2.5-flash-image)
        """
        self.api_key = api_key or Config.GEMINI_API_KEY
        self.model = model or Config.DEFAULT_MODEL
        self.client = genai.Client(api_key=self.api_key)
        
    def generate_image(
        self,
        prompt: str,
        reference_image_path: Optional[str] = None,
        view_angle: str = "front",
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Genera un'immagine usando l'API di Gemini (Nano Banana)
        
        Args:
            prompt: Descrizione dell'immagine da generare
            reference_image_path: Percorso all'immagine di riferimento per coerenza
            view_angle: Angolazione della vista (front, back, left, right, top)
            model: Modello da usare (override del default)
            **kwargs: Parametri aggiuntivi per l'API
            
        Returns:
            Dizionario con la risposta dell'API contenente il percorso locale dell'immagine
        """
        model_name = model or self.model
        
        # Prepara il prompt con l'angolazione specifica
        view_prompts = {
            "front": f"{prompt}, vista frontale, angolazione frontale, inquadratura frontale",
            "back": f"{prompt}, vista posteriore, angolazione retro, inquadratura posteriore",
            "left": f"{prompt}, vista laterale sinistra, angolazione laterale sinistra, profilo sinistro",
            "right": f"{prompt}, vista laterale destra, angolazione laterale destra, profilo destro",
            "top": f"{prompt}, vista dall'alto, angolazione top view, vista aerea, vista dall'alto"
        }
        
        enhanced_prompt = view_prompts.get(view_angle, prompt)
        
        # Prepara i contenuti della richiesta
        contents = []
        
        # Se c'è un'immagine di riferimento, aggiungila per mantenere coerenza
        if reference_image_path:
            try:
                # Carica l'immagine di riferimento
                ref_image = Image.open(reference_image_path)
                # Aggiungi l'immagine come parte del contenuto
                contents.append(ref_image)
                # Aggiungi istruzioni per mantenere coerenza e generare da nuova angolazione
                enhanced_prompt = (
                    f"Genera una nuova immagine dello stesso oggetto/soggetto mostrato nell'immagine di riferimento, "
                    f"mantenendo la stessa identità visiva, colori, stile e caratteristiche. "
                    f"{enhanced_prompt}"
                )
            except Exception as e:
                print(f"Avviso: Impossibile caricare l'immagine di riferimento: {e}")
        
        # Aggiungi il prompt testuale
        contents.append(enhanced_prompt)
        
        try:
            # Genera il contenuto usando l'API di Gemini
            response = self.client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                    **kwargs
                )
            )
            
            # Estrai l'immagine dalla risposta
            result = {
                "view_angle": view_angle,
                "model": model_name,
                "prompt": enhanced_prompt
            }
            
            # Cerca l'immagine nella risposta
            image_saved = False
            for part in response.parts:
                if part.text is not None:
                    result["text"] = part.text
                elif part.inline_data is not None:
                    # Salva l'immagine
                    image = part.as_image()
                    output_path = self._get_output_path(view_angle)
                    image.save(output_path)
                    result["local_path"] = str(output_path)
                    # Non includere l'oggetto Image nel risultato (non è JSON serializzabile)
                    # L'immagine è già salvata su disco
                    image_saved = True
                    break
            
            if not image_saved:
                result["error"] = "Nessuna immagine trovata nella risposta"
            
            return result
            
        except Exception as e:
            return {
                "error": str(e),
                "view_angle": view_angle,
                "model": model_name
            }
    
    def edit_image(
        self,
        image_path: str,
        edit_prompt: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Modifica un'immagine esistente usando un prompt testuale
        
        Args:
            image_path: Percorso all'immagine da modificare
            edit_prompt: Prompt che descrive le modifiche da apportare
            model: Modello da usare
            
        Returns:
            Dizionario con il risultato della modifica
        """
        model_name = model or self.model
        
        try:
            # Carica l'immagine
            image = Image.open(image_path)
            
            # Prepara i contenuti: immagine + prompt di modifica
            contents = [image, edit_prompt]
            
            # Genera la versione modificata
            response = self.client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"]
                )
            )
            
            result = {
                "edit_prompt": edit_prompt,
                "model": model_name
            }
            
            # Estrai l'immagine modificata
            for part in response.parts:
                if part.inline_data is not None:
                    edited_image = part.as_image()
                    output_path = self._get_output_path("edited")
                    edited_image.save(output_path)
                    result["local_path"] = str(output_path)
                    result["image"] = edited_image
                    break
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_output_path(self, view_angle: str) -> Path:
        """Genera il percorso di output per l'immagine"""
        import time
        output_dir = Path(Config.OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = int(time.time())
        return output_dir / f"{view_angle}_{timestamp}.png"