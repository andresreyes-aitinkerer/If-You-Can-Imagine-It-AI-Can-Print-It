"""Client per interagire con l'API Hunyuan3D di fal.ai per generare modelli 3D"""
from typing import Dict, Optional, Any
from pathlib import Path
import asyncio
import requests
from config import Config
import fal_client


class Hunyuan3DClient:
    """Client per l'API Hunyuan3D di fal.ai"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Inizializza il client per l'API di fal.ai
        
        Args:
            api_key: Chiave API di fal.ai (se None, usa Config.FAL_KEY)
        """
        self.api_key = api_key or Config.FAL_KEY
        
        if not self.api_key:
            raise ValueError(
                "FAL_KEY non configurata. "
                "Imposta la variabile d'ambiente FAL_KEY nel file .env. "
                "Ottieni la chiave su: https://fal.ai/"
            )
        
        # Configura il client (se necessario)
        # fal_client non richiede configurazione esplicita, usa FAL_KEY dall'ambiente
    
    async def _upload_file(self, file_path: str) -> str:
        """
        Carica un file su fal.ai storage usando upload_file_async e restituisce l'URL
        
        Args:
            file_path: Percorso locale del file da caricare
            
        Returns:
            URL pubblico del file caricato su fal.ai storage
        """
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File non trovato: {file_path}")
        
        try:
            url = await fal_client.upload_file_async(file_path)
            return url
        except Exception as e:
            raise Exception(f"Errore durante il caricamento del file {file_path} su fal.ai storage: {e}")
    
    async def generate_3d_model(
        self,
        front_image_path: str,
        back_image_path: str,
        left_image_path: str,
        right_image_path: Optional[str] = None,
        top_image_path: Optional[str] = None,
        seed: Optional[int] = None,
        num_inference_steps: int = 50,
        guidance_scale: float = 7.5,
        octree_resolution: int = 256,
        textured_mesh: bool = False,
        output_dir: Optional[str] = None,
        webhook_url: Optional[str] = None,
        convert_to_stl: bool = False
    ) -> Dict[str, Any]:
        """
        Genera un modello 3D dalle immagini multi-prospettiva (metodo asincrono)
        
        Args:
            front_image_path: Percorso all'immagine frontale
            back_image_path: Percorso all'immagine posteriore
            left_image_path: Percorso all'immagine laterale sinistra
            right_image_path: Percorso all'immagine laterale destra (opzionale)
            top_image_path: Percorso all'immagine dall'alto (opzionale)
            seed: Seed per la generazione (opzionale)
            num_inference_steps: Numero di step di inferenza (default: 50)
            guidance_scale: Scala di guida (default: 7.5)
            octree_resolution: Risoluzione octree (default: 256)
            textured_mesh: Se True, genera mesh con texture (costa 3x di più)
            output_dir: Directory dove salvare il modello 3D (default: Config.OUTPUT_3D_DIR)
            webhook_url: URL webhook opzionale per ricevere i risultati (opzionale)
            convert_to_stl: Se True, converte anche il modello in formato STL (default: False)
            
        Returns:
            Dizionario con i risultati della generazione
        """
        output_dir = output_dir or Config.OUTPUT_3D_DIR
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        try:
            def is_url(path: str) -> bool:
                """Verifica se il percorso è un URL pubblico"""
                return path.startswith(("http://", "https://"))
            
            def validate_image_path(path: str, view_name: str) -> str:
                """Valida il percorso dell'immagine e restituisce l'URL"""
                if is_url(path):
                    return path
                else:
                    # Se è un percorso locale, prova a passarlo come file aperto
                    # L'API potrebbe accettare file aperti direttamente
                    if Path(path).exists():
                        # Prova a passare il file aperto invece dell'URL
                        return path
                    else:
                        raise FileNotFoundError(
                            f"Immagine {view_name} non trovata: {path}. "
                            "L'API richiede URL pubblici (http/https) o percorsi di file locali esistenti."
                        )
            
            # Valida e prepara le immagini
            print("Preparazione immagini...")
            front_url = validate_image_path(front_image_path, "frontale")
            back_url = validate_image_path(back_image_path, "posteriore")
            left_url = validate_image_path(left_image_path, "laterale sinistra")
            
            image_urls = {
                "front": front_url,
                "back": back_url,
                "left": left_url
            }
            
            # Aggiungi right e top se disponibili
            if right_image_path:
                image_urls["right"] = validate_image_path(right_image_path, "laterale destra")
            
            if top_image_path:
                image_urls["top"] = validate_image_path(top_image_path, "dall'alto")
            
            print(f"✓ Immagini preparate:")
            for view, path in image_urls.items():
                print(f"  - {view.capitalize()}: {path}")
            
            # Prepara i parametri di input (l'API richiede solo front, back, left)
            # Se i percorsi non sono URL, prova a passare i file aperti
            input_params = {
                "front_image_url": front_url,
                "back_image_url": back_url,
                "left_image_url": left_url,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale,
                "octree_resolution": octree_resolution,
                "textured_mesh": textured_mesh
            }
            
            # Aggiungi right e top se disponibili (potrebbero essere supportati in futuro)
            if "right" in image_urls:
                input_params["right_image_url"] = image_urls["right"]
            if "top" in image_urls:
                input_params["top_image_url"] = image_urls["top"]
            
            if seed is not None:
                input_params["seed"] = seed
            
            # Se ci sono percorsi locali, caricali su fal.ai storage
            files_to_upload = {}
            for key, value in input_params.items():
                if key.endswith("_image_url") and not is_url(value):
                    # È un percorso locale, caricalo su fal.ai storage
                    if Path(value).exists():
                        files_to_upload[key] = value
            
            # Carica i file locali su fal.ai storage
            if files_to_upload:
                print("Caricamento file locali su fal.ai storage...")
                for key, file_path in files_to_upload.items():
                    print(f"  Caricamento {Path(file_path).name}...")
                    public_url = await self._upload_file(file_path)
                    input_params[key] = public_url
                    print(f"  ✓ Caricato: {public_url}")
            
            # Invia la richiesta all'API in modo asincrono
            print("\nGenerazione modello 3D...")
            print("(Questo processo può richiedere diversi minuti)")
            
            handler = await fal_client.submit_async(
                "fal-ai/hunyuan3d/v2/multi-view",
                arguments=input_params,
                webhook_url=webhook_url
            )
            
            request_id = handler.request_id
            print(f"Request ID: {request_id}")
            print("Attesa completamento elaborazione...")
            
            # Polling dello status fino al completamento
            model_id = "fal-ai/hunyuan3d/v2/multi-view"
            while True:
                status = fal_client.status(model_id, request_id, with_logs=True)
                
                # Gestisci i log se disponibili
                if hasattr(status, 'logs') and status.logs:
                    for log in status.logs:
                        if isinstance(log, dict):
                            message = log.get("message", "")
                        else:
                            message = getattr(log, "message", "")
                        if message:
                            print(f"  {message}")
                
                # Controlla lo stato (può essere un attributo o una proprietà)
                if hasattr(status, 'status'):
                    status_value = status.status
                elif isinstance(status, dict):
                    status_value = status.get("status")
                else:
                    # Prova ad accedere come attributo
                    status_value = getattr(status, 'status', None)
                
                if status_value == "COMPLETED":
                    break
                elif status_value in ["FAILED", "CANCELLED"]:
                    error_msg = None
                    if hasattr(status, 'error'):
                        error_msg = status.error
                    elif isinstance(status, dict):
                        error_msg = status.get("error")
                    else:
                        error_msg = getattr(status, 'error', None)
                    
                    return {
                        "success": False,
                        "error": f"Richiesta {status_value.lower()}: {error_msg or 'Errore sconosciuto'}",
                        "request_id": request_id
                    }
                
                # Attendi prima del prossimo polling
                await asyncio.sleep(2)
            
            # Ottieni il risultato finale
            result = await fal_client.result_async(model_id, request_id)
            
            # Estrai il modello 3D dalla risposta
            # Il formato della risposta è:
            # {
            #   "model_mesh": {
            #     "url": "...",
            #     "content_type": "...",
            #     "file_name": "...",
            #     "file_size": ...
            #   },
            #   "seed": ...
            # }
            result_data = result if isinstance(result, dict) else getattr(result, 'data', result)
            
            if isinstance(result_data, dict) and "model_mesh" in result_data:
                mesh_data = result_data["model_mesh"]
                
                # Estrai i dati del modello
                mesh_url = mesh_data.get("url") if isinstance(mesh_data, dict) else getattr(mesh_data, "url", None)
                file_name = mesh_data.get("file_name") if isinstance(mesh_data, dict) else getattr(mesh_data, "file_name", None)
                file_size = mesh_data.get("file_size") if isinstance(mesh_data, dict) else getattr(mesh_data, "file_size", None)
                content_type = mesh_data.get("content_type") if isinstance(mesh_data, dict) else getattr(mesh_data, "content_type", None)
                seed = result_data.get("seed") if isinstance(result_data, dict) else getattr(result_data, "seed", None)
                
                if mesh_url:
                    # Scarica il modello 3D nella cartella generated_3Dmodels
                    print(f"\nDownload modello 3D da: {mesh_url}")
                    model_path = self._download_model(mesh_url, output_dir, file_name)
                    
                    result_dict = {
                        "success": True,
                        "model_path": str(model_path),
                        "model_url": mesh_url,
                        "seed": seed,
                        "file_name": file_name or "model.glb",
                        "file_size": file_size,
                        "content_type": content_type,
                        "request_id": request_id
                    }
                    
                    # Converti in STL se richiesto
                    if convert_to_stl:
                        try:
                            stl_path = self._convert_glb_to_stl(model_path)
                            result_dict["stl_path"] = str(stl_path)
                            result_dict["stl_file_name"] = stl_path.name
                        except Exception as e:
                            print(f"  ⚠ Errore durante la conversione STL: {e}")
                            result_dict["stl_conversion_error"] = str(e)
                    
                    return result_dict
                else:
                    return {
                        "success": False,
                        "error": "URL del modello non trovato nella risposta"
                    }
            else:
                return {
                    "success": False,
                    "error": "Modello 3D non trovato nella risposta",
                    "response": result_data
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    
    def _convert_glb_to_stl(self, glb_path: Path) -> Path:
        """
        Converte un file GLB in formato STL
        
        Args:
            glb_path: Percorso del file GLB da convertire
            
        Returns:
            Percorso del file STL creato
        """
        try:
            import trimesh
        except ImportError:
            raise ImportError(
                "Il pacchetto 'trimesh' non è installato. "
                "Installa con: pip install trimesh"
            )
        
        if not glb_path.exists():
            raise FileNotFoundError(f"File GLB non trovato: {glb_path}")
        
        # Carica il modello GLB
        print(f"  Conversione GLB -> STL: {glb_path.name}")
        mesh = trimesh.load(str(glb_path))
        
        # Se il modello contiene più mesh, combinale
        if isinstance(mesh, trimesh.Scene):
            # Combina tutte le mesh della scena
            combined = trimesh.util.concatenate([
                geom for geom in mesh.geometry.values() 
                if isinstance(geom, trimesh.Trimesh)
            ])
            mesh = combined
        
        # Crea il percorso per il file STL
        stl_path = glb_path.with_suffix('.stl')
        
        # Salva come STL
        mesh.export(str(stl_path))
        
        print(f"  ✓ STL salvato: {stl_path}")
        return stl_path
    
    def _download_model(self, url: str, output_dir: str, file_name: Optional[str] = None) -> Path:
        """
        Scarica il modello 3D dall'URL fornito nella cartella generated_3Dmodels
        
        Args:
            url: URL del modello 3D
            output_dir: Directory dove salvare il modello (default: generated_3Dmodels)
            file_name: Nome del file dalla risposta API (opzionale)
            
        Returns:
            Percorso del file scaricato
        """
        # Assicurati che la directory esista
        output_path_obj = Path(output_dir)
        output_path_obj.mkdir(parents=True, exist_ok=True)
        
        # Determina il nome del file
        if file_name:
            filename = file_name
        else:
            # Estrai il nome dall'URL se non fornito
            filename = url.split("/")[-1]
            if not filename or "." not in filename:
                filename = "model_3d.glb"
        
        output_path = output_path_obj / filename
        
        # Scarica il file
        print(f"  Salvando in: {output_path}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"  ✓ Modello scaricato: {output_path}")
        return output_path
    
    async def generate_3d_from_multi_view_images(
        self,
        image_paths: Dict[str, str],
        convert_to_stl: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Genera un modello 3D da un dizionario di immagini multi-view
        
        Args:
            image_paths: Dizionario con chiavi 'front', 'back', 'left' (richieste)
                        e opzionalmente 'right', 'top'
            convert_to_stl: Se True, converte anche il modello in formato STL (default: False)
            **kwargs: Parametri aggiuntivi per generate_3d_model
            
        Returns:
            Dizionario con i risultati della generazione
        """
        required_views = ["front", "back", "left"]
        
        for view in required_views:
            if view not in image_paths:
                return {
                    "success": False,
                    "error": f"Immagine {view} mancante. Richieste: {', '.join(required_views)}"
                }
        
        return await self.generate_3d_model(
            front_image_path=image_paths["front"],
            back_image_path=image_paths["back"],
            left_image_path=image_paths["left"],
            right_image_path=image_paths.get("right"),
            top_image_path=image_paths.get("top"),
            convert_to_stl=convert_to_stl,
            **kwargs
        )
