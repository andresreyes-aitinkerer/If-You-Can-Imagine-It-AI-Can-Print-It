"""Script per generare modelli 3D dalle immagini multi-prospettiva usando Hunyuan3D"""
import argparse
import json
from pathlib import Path
from hunyuan3d_client import Hunyuan3DClient
from config import Config
from image_agents import ConsistencyManager


def resolve_image_path(path: str, search_dir: str = None) -> str:
    """
    Risolve il percorso di un'immagine, cercando in generated_images se non trovato
    
    Args:
        path: Percorso dell'immagine (può essere relativo o assoluto)
        search_dir: Directory dove cercare se il file non esiste (default: Config.OUTPUT_DIR)
        
    Returns:
        Percorso risolto del file
    """
    file_path = Path(path)
    
    # Se il file esiste già (percorso assoluto o relativo alla directory corrente), restituiscilo
    if file_path.exists():
        return str(file_path.resolve())
    
    # Se non esiste, cerca nella directory di output
    search_dir = search_dir or Config.OUTPUT_DIR
    search_path = Path(search_dir) / path
    
    if search_path.exists():
        return str(search_path.resolve())
    
    # Se ancora non trovato, prova a cercare per nome nella directory di output
    # (utile se l'utente passa solo il nome del file come "front.png")
    if not path.startswith('/') and not path.startswith('\\') and '\\' not in path and '/' not in path:
        search_path_obj = Path(search_dir)
        if search_path_obj.exists():
            # Prima prova il nome esatto
            exact_match = search_path_obj / path
            if exact_match.exists():
                return str(exact_match.resolve())
            
            # Poi prova pattern come "front_*.png" se l'utente passa "front.png"
            # Estrai il nome base (senza estensione) e cerca pattern
            base_name = Path(path).stem  # "front" da "front.png"
            pattern = f"{base_name}_*.png"
            matches = list(search_path_obj.glob(pattern))
            if matches:
                # Prendi il file più recente
                latest = max(matches, key=lambda p: p.stat().st_mtime)
                return str(latest.resolve())
            
            # Prova anche pattern generico con il nome
            pattern2 = f"*{path}"
            matches2 = list(search_path_obj.glob(pattern2))
            if matches2:
                latest = max(matches2, key=lambda p: p.stat().st_mtime)
                return str(latest.resolve())
    
    # Se non trovato, restituisci il percorso originale (verrà gestito come errore dopo)
    return path


def find_latest_images(output_dir: str) -> dict:
    """
    Trova le immagini più recenti nella directory di output
    
    Args:
        output_dir: Directory dove cercare le immagini
        
    Returns:
        Dizionario con i percorsi delle immagini trovate
    """
    output_path = Path(output_dir)
    if not output_path.exists():
        return {}
    
    # Cerca i file più recenti per ogni vista
    views = ["front", "back", "left", "right", "top"]
    found_images = {}
    
    for view in views:
        # Cerca file che iniziano con il nome della vista
        pattern = f"{view}_*.png"
        matching_files = list(output_path.glob(pattern))
        
        if matching_files:
            # Prendi il file più recente
            latest = max(matching_files, key=lambda p: p.stat().st_mtime)
            found_images[view] = str(latest)
    
    return found_images


def load_images_from_report(report_path: str) -> dict:
    """
    Carica i percorsi delle immagini da un report JSON
    
    Args:
        report_path: Percorso al file report JSON
        
    Returns:
        Dizionario con i percorsi delle immagini
    """
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        results = report.get("results", {})
        image_paths = {}
        
        for view, result in results.items():
            if "error" not in result and "local_path" in result:
                image_paths[view] = result["local_path"]
        
        return image_paths
    except Exception as e:
        print(f"Errore nel caricamento del report: {e}")
        return {}


async def main():
    """Funzione principale"""
    parser = argparse.ArgumentParser(
        description="Genera modelli 3D dalle immagini multi-prospettiva usando Hunyuan3D"
    )
    parser.add_argument(
        "--images-dir",
        type=str,
        default=None,
        help="Directory contenente le immagini (default: Config.OUTPUT_DIR)"
    )
    parser.add_argument(
        "--report",
        type=str,
        default=None,
        help="Percorso al file report JSON con i percorsi delle immagini"
    )
    parser.add_argument(
        "--front",
        type=str,
        help="Percorso all'immagine frontale"
    )
    parser.add_argument(
        "--back",
        type=str,
        help="Percorso all'immagine posteriore"
    )
    parser.add_argument(
        "--left",
        type=str,
        help="Percorso all'immagine laterale sinistra"
    )
    parser.add_argument(
        "--right",
        type=str,
        help="Percorso all'immagine laterale destra (opzionale)"
    )
    parser.add_argument(
        "--top",
        type=str,
        help="Percorso all'immagine dall'alto (opzionale)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory dove salvare il modello 3D (default: generated_3Dmodels)"
    )
    parser.add_argument(
        "--textured",
        action="store_true",
        help="Genera mesh con texture (costa 3x di più)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed per la generazione (opzionale)"
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=50,
        help="Numero di step di inferenza (default: 50)"
    )
    parser.add_argument(
        "--guidance",
        type=float,
        default=7.5,
        help="Scala di guida (default: 7.5)"
    )
    parser.add_argument(
        "--resolution",
        type=int,
        default=256,
        help="Risoluzione octree (default: 256)"
    )
    parser.add_argument(
        "--convert-to-stl",
        action="store_true",
        help="Converte anche il modello GLB in formato STL (mantiene entrambi i file)"
    )
    parser.add_argument(
        "--convert-existing",
        action="store_true",
        help="Converte tutti i modelli GLB esistenti nella cartella generated_3Dmodels in formato STL"
    )
    
    args = parser.parse_args()
    
    # Valida configurazione
    try:
        Config.validate()
    except ValueError as e:
        print(f"Errore di configurazione: {e}")
        print("Ottieni la chiave API su: https://ai.google.dev/")
        return
    
    # Se è richiesta solo la conversione dei file esistenti
    if args.convert_existing:
        output_dir = args.output_dir or Config.OUTPUT_3D_DIR
        output_path = Path(output_dir)
        
        if not output_path.exists():
            print(f"Errore: La directory {output_dir} non esiste.")
            return
        
        # Trova tutti i file GLB nella directory
        glb_files = list(output_path.glob("*.glb"))
        
        if not glb_files:
            print(f"Nessun file GLB trovato in {output_dir}")
            return
        
        print("=" * 50)
        print("Conversione Modelli GLB -> STL")
        print("=" * 50)
        print(f"\nTrovati {len(glb_files)} file GLB in {output_dir}")
        
        # Crea il client per usare il metodo di conversione
        try:
            client = Hunyuan3DClient()
        except Exception as e:
            print(f"Errore nell'inizializzazione del client: {e}")
            return
        
        converted = 0
        errors = 0
        
        for glb_file in glb_files:
            stl_file = glb_file.with_suffix('.stl')
            
            # Salta se il file STL esiste già
            if stl_file.exists():
                print(f"\n⏭ Saltato {glb_file.name} (STL già esistente: {stl_file.name})")
                continue
            
            try:
                print(f"\n📦 Conversione: {glb_file.name}")
                stl_path = client._convert_glb_to_stl(glb_file)
                converted += 1
                print(f"  ✓ Convertito: {stl_path.name}")
            except Exception as e:
                errors += 1
                print(f"  ✗ Errore: {e}")
        
        print("\n" + "=" * 50)
        print("Risultato Conversione")
        print("=" * 50)
        print(f"  ✓ Convertiti: {converted}")
        if errors > 0:
            print(f"  ✗ Errori: {errors}")
        print(f"  ⏭ Saltati: {len(glb_files) - converted - errors}")
        return
    
    # Verifica FAL_KEY
    if not Config.FAL_KEY:
        print("Errore: FAL_KEY non configurata.")
        print("Imposta la variabile d'ambiente FAL_KEY nel file .env.")
        print("Ottieni la chiave su: https://fal.ai/")
        return
    
    # Determina i percorsi delle immagini
    image_paths = {}
    
    if args.front and args.back and args.left:
        # Usa i percorsi specificati, risolvendoli se necessario
        image_paths = {
            "front": resolve_image_path(args.front),
            "back": resolve_image_path(args.back),
            "left": resolve_image_path(args.left)
        }
        # Aggiungi right e top se specificati
        if args.right:
            image_paths["right"] = resolve_image_path(args.right)
        if args.top:
            image_paths["top"] = resolve_image_path(args.top)
    elif args.report:
        # Carica dal report
        image_paths = load_images_from_report(args.report)
    else:
        # Cerca nella directory di output
        images_dir = args.images_dir or Config.OUTPUT_DIR
        image_paths = find_latest_images(images_dir)
    
    # Verifica che abbiamo le immagini necessarie
    required = ["front", "back", "left"]
    missing = [v for v in required if v not in image_paths]
    
    if missing:
        print(f"Errore: Immagini mancanti: {', '.join(missing)}")
        print("\nOpzioni:")
        print("  1. Usa --front, --back, --left per specificare i percorsi")
        print("  2. Usa --report per caricare da un report JSON")
        print("  3. Assicurati che le immagini siano in --images-dir")
        return
    
    # Verifica che i file esistano
    for view, path in image_paths.items():
        file_path = Path(path)
        
        if not file_path.exists():
            if not file_path.is_absolute():
                alt_path = Path(Config.OUTPUT_DIR) / path
                if alt_path.exists():
                    image_paths[view] = str(alt_path)
                    print(f"ℹ File {view} trovato in {Config.OUTPUT_DIR}: {alt_path}")
                    continue
            
            # Se ancora non trovato, prova solo il nome del file in generated_images
            filename = file_path.name
            alt_path = Path(Config.OUTPUT_DIR) / filename
            if alt_path.exists():
                image_paths[view] = str(alt_path)
                print(f"ℹ File {view} trovato in {Config.OUTPUT_DIR}: {alt_path}")
                continue
            
            # Se ancora non trovato, errore
            print(f"Errore: File non trovato per {view}: {path}")
            print(f"  Cercato anche in: {Config.OUTPUT_DIR}/{path}")
            print(f"  Cercato anche in: {Config.OUTPUT_DIR}/{filename}")
            return
    
    print("=" * 50)
    print("Generazione Modello 3D con Hunyuan3D")
    print("=" * 50)
    print(f"\nImmagini utilizzate:")
    for view in ["front", "back", "left", "right", "top"]:
        if view in image_paths:
            print(f"  - {view}: {image_paths[view]}")
    
    print(f"\nParametri:")
    print(f"  - Textured mesh: {args.textured}")
    print(f"  - Inference steps: {args.steps}")
    print(f"  - Guidance scale: {args.guidance}")
    print(f"  - Octree resolution: {args.resolution}")
    if args.seed:
        print(f"  - Seed: {args.seed}")
    
    print("\n" + "-" * 50)
    
    # Crea il client
    try:
        client = Hunyuan3DClient()
    except Exception as e:
        print(f"Errore nell'inizializzazione del client: {e}")
        return
    
    # Genera il modello 3D
    output_dir = args.output_dir or Config.OUTPUT_3D_DIR
    
    result = await client.generate_3d_from_multi_view_images(
        image_paths=image_paths,
        seed=args.seed,
        num_inference_steps=args.steps,
        guidance_scale=args.guidance,
        octree_resolution=args.resolution,
        textured_mesh=args.textured,
        output_dir=output_dir,
        convert_to_stl=args.convert_to_stl
    )
    
    # Mostra i risultati
    print("\n" + "=" * 50)
    print("Risultato Generazione 3D")
    print("=" * 50)
    
    if result.get("success"):
        print(f"\n✓ Modello 3D generato con successo!")
        print(f"  - Percorso GLB: {result['model_path']}")
        print(f"  - Nome file: {result['file_name']}")
        print(f"  - Dimensione: {result.get('file_size', 'N/A')} bytes")
        if result.get('stl_path'):
            print(f"  - Percorso STL: {result['stl_path']}")
            print(f"  - Nome file STL: {result.get('stl_file_name', 'N/A')}")
        if result.get('seed'):
            print(f"  - Seed: {result['seed']}")
        if result.get('request_id'):
            print(f"  - Request ID: {result['request_id']}")
        if result.get('stl_conversion_error'):
            print(f"  ⚠ Errore conversione STL: {result['stl_conversion_error']}")
    else:
        print(f"\n✗ Errore durante la generazione:")
        print(f"  {result.get('error', 'Errore sconosciuto')}")
        if 'response' in result:
            print(f"\nRisposta API: {result['response']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
