"""
Agenti per generare immagini da diverse prospettive mantenendo la coerenza
"""
from typing import Dict, Optional, List
from pathlib import Path
from nano_banana_client import NanoBananaClient
from config import Config
import time

class ImageAgent:
    """Agente base per la generazione di immagini"""
    
    def __init__(self, client: NanoBananaClient, view_angle: str):
        self.client = client
        self.view_angle = view_angle
        self.generated_image_path: Optional[str] = None
        
    def generate(self, base_prompt: str, reference_image_path: Optional[str] = None, consistency_data: Optional[Dict] = None) -> Dict:
        """
        Genera un'immagine dalla prospettiva specifica
        
        Args:
            base_prompt: Prompt base per l'immagine
            reference_image_path: Immagine di riferimento per coerenza
            consistency_data: Dati per mantenere coerenza con altre immagini
            
        Returns:
            Dizionario con i risultati della generazione
        """
        # Costruisci il prompt specifico per questa vista
        prompt = self._build_prompt(base_prompt, consistency_data)
        
        # Usa l'immagine di riferimento se disponibile
        ref_image = reference_image_path or (consistency_data.get("reference_image") if consistency_data else None)
        
        try:
            response = self.client.generate_image(
                prompt=prompt,
                reference_image_path=ref_image,
                view_angle=self.view_angle
            )
            
            # Il client salva già l'immagine, quindi aggiorna il percorso se presente
            if "local_path" in response:
                self.generated_image_path = response["local_path"]
            
            return response
            
        except Exception as e:
            return {"error": str(e), "view_angle": self.view_angle}
    
    def _build_prompt(self, base_prompt: str, consistency_data: Optional[Dict]) -> str:
        """Costruisce il prompt specifico per questa vista"""
        view_descriptions = {
            "front": "vista frontale, angolazione frontale, inquadratura frontale",
            "back": "vista posteriore, angolazione retro, inquadratura posteriore",
            "left": "vista laterale sinistra, angolazione laterale sinistra, profilo sinistro",
            "right": "vista laterale destra, angolazione laterale destra, profilo destro",
            "top": "vista dall'alto, angolazione top view, vista aerea, vista dall'alto"
        }
        
        view_desc = view_descriptions.get(self.view_angle, "")
        
        # Aggiungi informazioni di coerenza se disponibili
        consistency_parts = []
        if consistency_data:
            if "color_scheme" in consistency_data:
                consistency_parts.append(f"schema colori: {consistency_data['color_scheme']}")
            if "style" in consistency_data:
                consistency_parts.append(f"stile: {consistency_data['style']}")
            if "characteristics" in consistency_data:
                consistency_parts.append(f"caratteristiche: {consistency_data['characteristics']}")
        
        consistency_str = ", ".join(consistency_parts) if consistency_parts else ""
        
        if consistency_str:
            return f"{base_prompt}, {view_desc}, {consistency_str}, mantenere coerenza visiva"
        else:
            return f"{base_prompt}, {view_desc}, mantenere coerenza visiva"
    
    def _get_output_path(self) -> str:
        """Genera il percorso di output per l'immagine"""
        output_dir = Path(Config.OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = int(time.time())
        return str(output_dir / f"{self.view_angle}_{timestamp}.png")


class FrontViewAgent(ImageAgent):
    """Agente per la vista frontale"""
    def __init__(self, client: NanoBananaClient):
        super().__init__(client, "front")


class BackViewAgent(ImageAgent):
    """Agente per la vista posteriore"""
    def __init__(self, client: NanoBananaClient):
        super().__init__(client, "back")


class LeftViewAgent(ImageAgent):
    """Agente per la vista laterale sinistra"""
    def __init__(self, client: NanoBananaClient):
        super().__init__(client, "left")


class RightViewAgent(ImageAgent):
    """Agente per la vista laterale destra"""
    def __init__(self, client: NanoBananaClient):
        super().__init__(client, "right")


class TopViewAgent(ImageAgent):
    """Agente per la vista dall'alto"""
    def __init__(self, client: NanoBananaClient):
        super().__init__(client, "top")


class ConsistencyManager:
    """Gestore della coerenza tra le immagini generate"""
    
    def __init__(self):
        self.consistency_data: Dict = {}
        self.generated_images: Dict[str, str] = {}
        
    def extract_consistency_data(self, first_image_response: Dict) -> Dict:
        """
        Estrae dati di coerenza dalla prima immagine generata
        
        Args:
            first_image_response: Risposta dell'API per la prima immagine
            
        Returns:
            Dizionario con dati di coerenza
        """
        # Estrai informazioni che possono essere usate per mantenere coerenza
        consistency = {
            "model": first_image_response.get("model", Config.DEFAULT_MODEL),
        }
        
        # Se c'è un'immagine locale, usala come riferimento
        if "local_path" in first_image_response:
            consistency["reference_image"] = first_image_response["local_path"]
        
        return consistency
    
    def update_consistency(self, new_data: Dict):
        """Aggiorna i dati di coerenza"""
        self.consistency_data.update(new_data)
    
    def get_consistency_data(self) -> Dict:
        """Restituisce i dati di coerenza attuali"""
        return self.consistency_data.copy()
    
    def register_image(self, view_angle: str, image_path: str):
        """Registra un'immagine generata"""
        self.generated_images[view_angle] = image_path
    
    def get_reference_image(self) -> Optional[str]:
        """Restituisce il percorso dell'immagine di riferimento"""
        # Usa la prima immagine generata come riferimento
        if self.generated_images:
            return list(self.generated_images.values())[0]
        return None