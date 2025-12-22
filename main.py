"""Script principale per orchestrare gli agenti e generare immagini coerenti"""
import argparse
from pathlib import Path
from nano_banana_client import NanoBananaClient
from image_agents import (
    FrontViewAgent,
    BackViewAgent,
    LeftViewAgent,
    RightViewAgent,
    TopViewAgent,
    ConsistencyManager
)
from config import Config

def main():
    """Funzione principale"""
    parser = argparse.ArgumentParser(
        description="Genera immagini coerenti da diverse prospettive usando Nano Banana API"
    )
    parser.add_argument(
        "prompt",
        type=str,
        help="Descrizione dell'oggetto/personaggio da generare"
    )
    parser.add_argument(
        "--reference-image",
        type=str,
        help="Percorso a un'immagine di riferimento (opzionale)"
    )
    parser.add_argument(
        "--views",
        nargs="+",
        choices=["front", "back", "left", "right", "top", "all"],
        default=["all"],
        help="Viste da generare (default: all)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory di output (default: generated_images)"
    )
    parser.add_argument(
        "--model",
        type=str,
        choices=["flash", "pro"],
        default="flash",
        help="Modello da usare: flash (Nano Banana, veloce) o pro (Nano Banana Pro, alta qualità)"
    )
    parser.add_argument(
        "--generate-3d",
        action="store_true",
        help="Genera automaticamente un modello 3D dopo aver generato le immagini (richiede FAL_KEY)"
    )
    parser.add_argument(
        "--textured-mesh",
        action="store_true",
        help="Genera mesh con texture per il modello 3D (costa 3x di più, richiede --generate-3d)"
    )
    
    args = parser.parse_args()
    
    # Valida configurazione
    try:
        Config.validate()
    except ValueError as e:
        print(f"Errore di configurazione: {e}")
        print("Ottieni la chiave API su: https://ai.google.dev/")
        return
    
    # Imposta directory di output se specificata
    if args.output_dir:
        Config.OUTPUT_DIR = args.output_dir
    
    # Seleziona il modello
    model = Config.DEFAULT_MODEL if args.model == "flash" else Config.PRO_MODEL
    
    # Crea il client API
    client = NanoBananaClient(model=model)
    
    # Crea il gestore di coerenza
    consistency_manager = ConsistencyManager()
    
    # Determina quali viste generare
    views_to_generate = []
    if "all" in args.views:
        views_to_generate = ["front", "back", "left", "right", "top"]
    else:
        views_to_generate = args.views
    
    # Crea gli agenti
    agents = {
        "front": FrontViewAgent(client),
        "back": BackViewAgent(client),
        "left": LeftViewAgent(client),
        "right": RightViewAgent(client),
        "top": TopViewAgent(client)
    }
    
    print(f"Generazione immagini per: {args.prompt}")
    print(f"Modello: {model}")
    print(f"Viste da generare: {', '.join(views_to_generate)}")
    print("-" * 50)
    
    # Genera le immagini
    results = {}
    reference_image = args.reference_image
    
    for i, view in enumerate(views_to_generate):
        print(f"\n[{i+1}/{len(views_to_generate)}] Generando vista {view}...")
        
        agent = agents[view]
        
        # Usa i dati di coerenza se disponibili
        consistency_data = None
        if i > 0:  # Dopo la prima immagine, usa i dati di coerenza
            consistency_data = consistency_manager.get_consistency_data()
            # Usa la prima immagine come riferimento
            ref = consistency_manager.get_reference_image()
            if ref:
                reference_image = ref
        
        result = agent.generate(
            base_prompt=args.prompt,
            reference_image_path=reference_image,
            consistency_data=consistency_data
        )
        
        results[view] = result
        
        # Aggiorna il gestore di coerenza
        if "error" not in result:
            if i == 0:  # Prima immagine: estrai dati di coerenza
                consistency_data = consistency_manager.extract_consistency_data(result)
                consistency_manager.update_consistency(consistency_data)
            
            if "local_path" in result:
                consistency_manager.register_image(view, result["local_path"])
                print(f"✓ Immagine salvata: {result['local_path']}")
            else:
                print(f"✓ Immagine generata (dettagli: {result.get('text', 'N/A')})")
        else:
            print(f"✗ Errore: {result['error']}")
    
    # Riepilogo
    print("\n" + "=" * 50)
    print("Riepilogo generazione:")
    print("=" * 50)
    
    successful = sum(1 for r in results.values() if "error" not in r)
    failed = len(results) - successful
    
    print(f"Immagini generate con successo: {successful}/{len(results)}")
    print(f"Errori: {failed}")
    
    if successful > 0:
        print("\nImmagini salvate:")
        for view, result in results.items():
            if "error" not in result and "local_path" in result:
                print(f"  - {view}: {result['local_path']}")
    
    # Salva un report JSON
    report_path = Path(Config.OUTPUT_DIR) / "generation_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Pulisci i risultati rimuovendo oggetti non serializzabili
    def clean_for_json(obj):
        """Rimuove oggetti non serializzabili per JSON"""
        if isinstance(obj, dict):
            return {k: clean_for_json(v) for k, v in obj.items() 
                   if not k.startswith('_') and not hasattr(v, '__call__')}
        elif isinstance(obj, list):
            return [clean_for_json(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            # Salta oggetti complessi come Image
            return str(type(obj).__name__)
        else:
            try:
                import json
                json.dumps(obj)  # Test se è serializzabile
                return obj
            except (TypeError, ValueError):
                return str(obj)
    
    cleaned_results = clean_for_json(results)
    cleaned_consistency = clean_for_json(consistency_manager.get_consistency_data())
    
    with open(report_path, "w", encoding="utf-8") as f:
        import json
        json.dump({
            "prompt": args.prompt,
            "model": model,
            "views": views_to_generate,
            "results": cleaned_results,
            "consistency_data": cleaned_consistency
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\nReport salvato: {report_path}")
    
    # Genera modello 3D se richiesto
    if args.generate_3d:
        print("\n" + "=" * 50)
        print("Generazione Modello 3D")
        print("=" * 50)
        
        # Verifica che abbiamo almeno le 3 viste necessarie
        required_views_for_3d = ["front", "back", "left"]
        available_views = [v for v in required_views_for_3d if v in results and "error" not in results[v]]
        
        if len(available_views) < 3:
            print(f"\n⚠ Impossibile generare modello 3D: mancano le viste necessarie.")
            print(f"  Richieste: {', '.join(required_views_for_3d)}")
            print(f"  Disponibili: {', '.join(available_views)}")
        else:
            try:
                from hunyuan3d_client import Hunyuan3DClient
                
                # Verifica FAL_KEY
                if not Config.FAL_KEY:
                    print("\n⚠ FAL_KEY non configurata. Salto la generazione 3D.")
                    print("  Imposta FAL_KEY nel file .env per abilitare la generazione 3D.")
                else:
                    # Prepara i percorsi delle immagini (include tutte le viste disponibili)
                    image_paths = {}
                    all_views = ["front", "back", "left", "right", "top"]
                    for view in all_views:
                        if view in results and "local_path" in results[view]:
                            image_paths[view] = results[view]["local_path"]
                    
                    # Crea il client e genera il modello
                    import asyncio
                    client = Hunyuan3DClient()
                    result = asyncio.run(client.generate_3d_from_multi_view_images(
                        image_paths=image_paths,
                        textured_mesh=args.textured_mesh,
                        output_dir=Config.OUTPUT_3D_DIR
                    ))
                    
                    if result.get("success"):
                        print(f"\n✓ Modello 3D generato: {result['model_path']}")
                        print(f"  Dimensione: {result.get('file_size', 'N/A')} bytes")
                    else:
                        print(f"\n✗ Errore nella generazione 3D: {result.get('error', 'Errore sconosciuto')}")
                        
            except ImportError:
                print("\n⚠ Pacchetto fal-client non installato. Salto la generazione 3D.")
                print("  Installa con: pip install fal-client")
            except Exception as e:
                print(f"\n✗ Errore durante la generazione 3D: {e}")

if __name__ == "__main__":
    main()

