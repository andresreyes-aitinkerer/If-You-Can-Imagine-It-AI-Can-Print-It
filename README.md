# If you can imagine it, AI can print it - Sistema di Generazione Immagini Multi-Prospettiva

Sistema di agenti per generare immagini coerenti da diverse prospettive utilizzando l'API di Google Gemini (nota anche come Nano Banana e Nano Banana Pro).

> **Nota**: "Nano Banana" e "Nano Banana Pro" sono i nomi informali per i modelli di generazione immagini di Google Gemini:
> - **Nano Banana** = `gemini-2.5-flash-image` (veloce, 1024px)
> - **Nano Banana Pro** = `gemini-3-pro-image-preview` (alta qualità, fino a 4K)

## Caratteristiche

- 🎨 Generazione di immagini da 5 prospettive diverse:
  - **Frontale**: Vista frontale dell'oggetto
  - **Retro**: Vista posteriore
  - **Lato Sinistro**: Vista laterale sinistra
  - **Lato Destro**: Vista laterale destra
  - **Top View**: Vista dall'alto

- 🔗 **Coerenza Visiva**: Sistema automatico per mantenere la coerenza tra le diverse immagini generate
- 🤖 **Agenti Specializzati**: Ogni agente è specializzato per una specifica prospettiva
- 📊 **Report Automatici**: Generazione di report JSON con i risultati
- 🎲 **Generazione 3D**: Integrazione con Hunyuan3D (fal.ai) per convertire le immagini multi-view in modelli 3D

## Installazione

1. Clona o scarica il progetto

2. Installa le dipendenze:
```bash
pip install -r requirements.txt
```

3. Configura le variabili d'ambiente:
   - Crea un file `.env` nella root del progetto
   - Ottieni una API key gratuita su [Google AI Studio](https://ai.google.dev/)
   - (Opzionale) Ottieni una API key per fal.ai su [fal.ai](https://fal.ai/) per la generazione 3D
   - Aggiungi le tue API keys nel file `.env`:
   ```
   GEMINI_API_KEY=your_api_key_here
   FAL_KEY=your_fal_api_key_here  # Opzionale, solo per generazione 3D
   ```
   
   > **Nota**: Puoi anche usare `NANO_BANANA_API_KEY` come nome alternativo per compatibilità.

## Utilizzo

### Uso Base

Genera tutte le viste di un oggetto:
```bash
python main.py "un robot umanoide futuristico"
```

### Generare Viste Specifiche

Genera solo alcune viste:
```bash
python main.py "un robot umanoide futuristico" --views front back top
```

### Con Immagine di Riferimento

Usa un'immagine esistente come riferimento per mantenere la coerenza:
```bash
python main.py "un robot umanoide futuristico" --reference-image path/to/reference.png
```

### Personalizzare Directory di Output

```bash
python main.py "un robot umanoide futuristico" --output-dir my_images
```

### Scegliere il Modello

Usa il modello Pro per immagini di alta qualità (più lento):
```bash
python main.py "un robot umanoide futuristico" --model pro
```

Usa il modello Flash per generazione veloce (default):
```bash
python main.py "un robot umanoide futuristico" --model flash
```

### Generare Modello 3D

Dopo aver generato le immagini, puoi creare automaticamente un modello 3D usando Hunyuan3D:

**Opzione 1: Automaticamente dopo la generazione delle immagini**
```bash
python main.py "un robot umanoide futuristico" --generate-3d
```

**Opzione 2: Con mesh texturizzata (costa 3x di più)**
```bash
python main.py "un robot umanoide futuristico" --generate-3d --textured-mesh
```

**Opzione 3: Usando lo script dedicato**
```bash
# Genera 3D dalle immagini più recenti nella directory di output
python generate_3d.py

# Oppure specifica i percorsi delle immagini
python generate_3d.py --front path/to/front.png --back path/to/back.png --left path/to/left.png

# Oppure carica da un report JSON
python generate_3d.py --report generated_images/generation_report.json
```

**Parametri avanzati per la generazione 3D:**
```bash
python generate_3d.py \
  --front front.png --back back.png --left left.png \
  --textured \
  --steps 50 \
  --guidance 7.5 \
  --resolution 256 \
  --seed 42 \
  --convert-to-stl
```

**Altri parametri utili:**
```bash
# Specifica una directory personalizzata per le immagini
python generate_3d.py --images-dir my_images

# Converte tutti i modelli GLB esistenti in formato STL
python generate_3d.py --convert-existing
```

## Struttura del Progetto

```
.
├── main.py                 # Script principale
├── nano_banana_client.py   # Client per l'API di Nano Banana
├── image_agents.py         # Agenti per le diverse prospettive
├── hunyuan3d_client.py     # Client per l'API Hunyuan3D (fal.ai)
├── generate_3d.py          # Script per generare modelli 3D
├── config.py              # Configurazione
├── requirements.txt       # Dipendenze Python
├── README.md              # Questo file
├── .env                   # Variabili d'ambiente (da creare)
├── generated_images/      # Directory di output immagini (creata automaticamente)
│   ├── front_*.png
│   ├── back_*.png
│   ├── left_*.png
│   ├── right_*.png
│   ├── top_*.png
│   └── generation_report.json
└── generated_3Dmodels/    # Directory di output modelli 3D (creata automaticamente)
    ├── *.glb               # Modelli 3D generati
    └── *.stl               # Modelli 3D convertiti in STL (opzionale)
```

## Come Funziona

1. **Inizializzazione**: Il sistema crea un client API e un gestore di coerenza
2. **Prima Immagine**: Viene generata la prima vista (solitamente frontale) che serve come riferimento
3. **Estrazione Coerenza**: Dalla prima immagine vengono estratti dati di coerenza (stile, colori, caratteristiche)
4. **Immagini Successive**: Le viste successive usano la prima immagine come riferimento e i dati di coerenza per mantenere uniformità
5. **Salvataggio**: Tutte le immagini vengono salvate nella directory di output con un report JSON

## Agenti Disponibili

- `FrontViewAgent`: Genera viste frontali
- `BackViewAgent`: Genera viste posteriori
- `LeftViewAgent`: Genera viste laterali sinistre
- `RightViewAgent`: Genera viste laterali destre
- `TopViewAgent`: Genera viste dall'alto

## Sistema di Coerenza

Il `ConsistencyManager` gestisce automaticamente:
- Estrazione di dati di coerenza dalla prima immagine
- Uso dell'immagine di riferimento per le viste successive
- Mantenimento di stile, colori e caratteristiche tra le immagini

## Esempi di Prompt

- `"un gatto siamese elegante"`
- `"un'auto sportiva rossa"`
- `"un personaggio fantasy con armatura"`
- `"un edificio moderno in vetro"`

## Generazione 3D con Hunyuan3D

Il sistema supporta la generazione di modelli 3D dalle immagini multi-prospettiva utilizzando l'API [Hunyuan3D di fal.ai](https://fal.ai/models/fal-ai/hunyuan3d/v2/multi-view/api).

### Requisiti

- API Key di fal.ai (ottieni su [fal.ai](https://fal.ai/))
- Almeno 3 immagini: frontale, posteriore e laterale sinistra
- Il pacchetto `fal-client` installato (incluso in `requirements.txt`)

### Come Funziona

1. **Genera le immagini multi-view** usando `main.py`
2. **Converti in 3D** usando `generate_3d.py` o l'opzione `--generate-3d`
3. Il modello 3D viene salvato come file `.glb` nella directory `generated_3Dmodels/`

### Parametri 3D

**Per `main.py` (opzione `--generate-3d`):**
- `--textured-mesh`: Genera mesh con texture (costa 3x di più)

**Per `generate_3d.py`:**
- `--textured`: Genera mesh con texture (costa 3x di più)
- `--steps`: Numero di step di inferenza (default: 50)
- `--guidance`: Scala di guida (default: 7.5)
- `--resolution`: Risoluzione octree (default: 256)
- `--seed`: Seed per riproducibilità
- `--images-dir`: Directory dove cercare le immagini (default: `generated_images`)
- `--output-dir`: Directory dove salvare il modello 3D (default: `generated_3Dmodels`)
- `--convert-to-stl`: Converte anche il modello GLB in formato STL
- `--convert-existing`: Converte tutti i modelli GLB esistenti in formato STL

### Formato Output

I modelli 3D vengono salvati in formato GLB (binary glTF) di default, compatibile con:
- Blender
- Unity
- Unreal Engine
- Three.js
- E molti altri software 3D

Con l'opzione `--convert-to-stl`, viene generato anche un file STL, utile per la stampa 3D.

## Note

- **API Keys**: 
  - Ottieni una chiave API gratuita per Google Gemini su [Google AI Studio](https://ai.google.dev/)
  - Ottieni una chiave API per fal.ai su [fal.ai](https://fal.ai/) per la generazione 3D
- **Modelli Immagini**: 
  - `gemini-2.5-flash-image` (Nano Banana): Veloce, ottimizzato per bassa latenza, risoluzione 1024px
  - `gemini-3-pro-image-preview` (Nano Banana Pro): Alta qualità, fino a 4K, ideale per asset professionali
- Le immagini vengono salvate automaticamente nella directory `generated_images/`
- I modelli 3D vengono salvati automaticamente nella directory `generated_3Dmodels/`
- Il sistema genera un report JSON con tutti i dettagli della generazione
- Per migliori risultati, usa un'immagine di riferimento quando disponibile
- Tutte le immagini generate includono una filigrana SynthID per identificare il contenuto AI
- La generazione 3D può richiedere diversi minuti a seconda della complessità

## Troubleshooting

**Errore: "GEMINI_API_KEY non configurata"**
- Verifica che il file `.env` esista e contenga la chiave API
- Ottieni una chiave API gratuita su [https://ai.google.dev/](https://ai.google.dev/)
- Puoi usare `GEMINI_API_KEY` o `NANO_BANANA_API_KEY` nel file `.env`

**Immagini non coerenti**
- Prova a usare un'immagine di riferimento con `--reference-image`
- Assicurati che il prompt sia dettagliato e specifico

**Errori di connessione**
- Verifica la tua connessione internet
- Controlla che la chiave API sia valida e non scaduta
- Assicurati di aver installato correttamente `google-genai`: `pip install google-genai`

**Errore: "FAL_KEY non configurata" (per generazione 3D)**
- Verifica che il file `.env` contenga `FAL_KEY=your_api_key_here`
- Ottieni una chiave API su [fal.ai](https://fal.ai/)
- Assicurati di aver installato `fal-client`: `pip install fal-client`

**Errore durante la generazione 3D**
- Verifica di avere almeno 3 immagini: front, back, left
- Controlla che le immagini siano accessibili e in formato valido
- La generazione 3D può richiedere diversi minuti, sii paziente

## Riferimenti

- [Documentazione ufficiale Google Gemini Image Generation](https://ai.google.dev/gemini-api/docs/image-generation?hl=it)
- [Google AI Studio](https://ai.google.dev/) - Ottieni la tua API key gratuita
- [SDK Google GenAI per Python](https://github.com/google/generative-ai-python)
- [Hunyuan3D API Documentation](https://fal.ai/models/fal-ai/hunyuan3d/v2/multi-view/api) - Documentazione API per generazione 3D
- [fal.ai](https://fal.ai/) - Piattaforma per modelli AI

## Licenza

Questo progetto è fornito "così com'è" per uso personale e educativo.

