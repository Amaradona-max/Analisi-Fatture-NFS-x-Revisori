# Guida Passo-Passo: Sviluppo App Gestione NFS/FT

## FASE 1: SETUP INIZIALE

### Step 1.1: Creazione Progetto Backend (Python + FastAPI)

```bash
# Crea directory progetto
mkdir nfs-ft-app
cd nfs-ft-app
mkdir backend frontend
cd backend

# Crea ambiente virtuale
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oppure: venv\Scripts\activate  # Windows

# Installa dipendenze
pip install fastapi uvicorn python-multipart pandas openpyxl
pip freeze > requirements.txt
```

### Step 1.2: Struttura Backend

```bash
# Crea struttura directory
mkdir -p app/{api,core,services,models}
touch app/__init__.py
touch app/main.py
touch app/api/__init__.py
touch app/api/routes.py
touch app/services/__init__.py
touch app/services/file_processor.py
touch app/core/__init__.py
touch app/core/config.py
```

Struttura finale:
```
backend/
├── venv/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py
│   └── services/
│       ├── __init__.py
│       └── file_processor.py
├── uploads/           # Creata automaticamente
├── outputs/           # Creata automaticamente
└── requirements.txt
```

---

## FASE 2: CODICE BACKEND

### Step 2.1: Configurazione (app/core/config.py)

```python
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # Directories
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    OUTPUT_DIR: Path = BASE_DIR / "outputs"
    
    # File constraints
    MAX_FILE_SIZE: int = 52428800  # 50MB
    ALLOWED_EXTENSIONS: set = {".xlsx"}
    
    # CORS
    ALLOWED_ORIGINS: list = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # React dev server
    ]
    
    # Cleanup
    FILE_RETENTION_HOURS: int = 24
    
    class Config:
        env_file = ".env"

settings = Settings()

# Crea directories se non esistono
settings.UPLOAD_DIR.mkdir(exist_ok=True)
settings.OUTPUT_DIR.mkdir(exist_ok=True)
```

### Step 2.2: File Processor (app/services/file_processor.py)

```python
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils.dataframe import dataframe_to_rows
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class NFSFTFileProcessor:
    """Processore per file NFS/FT Excel"""
    
    # Protocolli validi
    PROTOCOLLI_FASE2 = ['P', '2P', 'LABI', 'FCBI', 'FCSI', 'FCBE', 'FCSE']
    PROTOCOLLI_FASE3 = ['EP', '2EP', 'EL', '2EL', 'EZ', '2EZ', 'EZP', 
                        'FPIC', 'FSIC', 'FPEC', 'FSEC']
    
    # Mappatura descrizioni Fase 2
    DESCRIZIONI_FASE2 = {
        'P': 'Fatture Cartacee San',
        '2P': 'Fatture Cartacee Ter',
        'LABI': 'Fatture Lib.Prof. San',
        'FCBI': 'Fatture Cartacee Estere San',
        'FCSI': 'Fatture Cartacee Estere San',
        'FCBE': 'Fatture Cartacee Estere San',
        'FCSE': 'Fatture Cartacee Estere San'
    }
    
    # Mappatura descrizioni Fase 3
    DESCRIZIONI_FASE3 = {
        'EP': 'Fatture Elettroniche San',
        '2EP': 'Fatture Elettroniche Ter',
        'EL': 'Fatture Elettroniche Lib.Prof. San',
        '2EL': 'Fatture Elettroniche Lib.Prof. Ter',
        'EZ': 'Fatture Elettroniche Commerciali San',
        '2EZ': 'Fatture Elettroniche Commerciali Ter',
        'EZP': 'Fatture Elettroniche Commerciali San',
        'FPIC': 'Fatture Elettroniche Estere San',
        'FSIC': 'Fatture Elettroniche Estere San',
        'FPEC': 'Fatture Elettroniche Estere San',
        'FSEC': 'Fatture Elettroniche Estere San'
    }
    
    # Colonne richieste nel file input
    REQUIRED_COLUMNS = [
        'C_NOME', 'FAT_DATDOC', 'FAT_NDOC', 'FAT_DATREG',
        'FAT_PROT', 'FAT_NUM', 'IMPONIBILE', 'FAT_TOTIVA',
        'PA_IMPORTO', 'DMA_NUM', 'TMA_DTGEN', 'FAT_TOTFAT', 'TMC_G8'
    ]
    
    def __init__(self):
        self.all_protocols = self.PROTOCOLLI_FASE2 + self.PROTOCOLLI_FASE3
    
    def validate_file(self, df: pd.DataFrame) -> None:
        """Valida che il file contenga le colonne richieste"""
        missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Colonne mancanti: {', '.join(missing_cols)}")
    
    def process_file(self, input_path: Path, output_path: Path) -> Dict[str, Any]:
        """
        Processa il file Excel NFS/FT
        
        Args:
            input_path: Path del file input
            output_path: Path del file output
            
        Returns:
            Dict con statistiche elaborazione
        """
        try:
            # 1. Carica file
            logger.info(f"Caricamento file: {input_path}")
            df = pd.read_excel(input_path)
            
            # 2. Valida struttura
            self.validate_file(df)
            
            # 3. Pulizia protocolli
            df['FAT_PROT'] = df['FAT_PROT'].astype(str).str.strip()
            
            # 4. Filtra protocolli validi
            df_filtrato = df[df['FAT_PROT'].isin(self.all_protocols)].copy()
            
            if len(df_filtrato) == 0:
                raise ValueError("Nessun protocollo valido trovato nel file")
            
            # 5. Crea colonna Tot. Importo Mandato
            df_filtrato['Tot. Importo Mandato'] = df_filtrato['FAT_TOTFAT']
            
            # 6. Seleziona e riordina colonne
            colonne_ordinate = [
                'C_NOME', 'FAT_DATDOC', 'FAT_NDOC', 'FAT_DATREG',
                'FAT_PROT', 'FAT_NUM', 'IMPONIBILE', 'FAT_TOTIVA',
                'PA_IMPORTO', 'DMA_NUM', 'TMA_DTGEN',
                'Tot. Importo Mandato', 'TMC_G8'
            ]
            
            df_finale = df_filtrato[colonne_ordinate].copy()
            
            # 7. Rinomina colonne
            df_finale.columns = [
                'Ragione sociale', 'Data Fatture', 'N. fatture',
                'Data Ricevimento', 'Protocollo', 'N. Protocollo',
                'Tot. imponibile', 'Imposta', 'Tot. Fatture',
                'N. Mandato', 'Data Mandato', 'Tot. Importo Mandato',
                'Id. SDI'
            ]
            
            # 8. Ordina per Data Ricevimento
            df_finale = df_finale.sort_values('Data Ricevimento')
            
            # 9. Calcola statistiche
            stats = self._calculate_stats(df_finale)
            
            # 10. Crea file Excel
            self._create_excel_output(df_finale, output_path)
            
            logger.info(f"File elaborato con successo: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Errore elaborazione file: {str(e)}")
            raise
    
    def _calculate_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calcola statistiche sui dati elaborati"""
        fase2_count = df[df['Protocollo'].isin(self.PROTOCOLLI_FASE2)].shape[0]
        fase3_count = df[df['Protocollo'].isin(self.PROTOCOLLI_FASE3)].shape[0]
        
        return {
            'total_records': len(df),
            'fase2_records': fase2_count,
            'fase3_records': fase3_count,
            'protocols_fase2': self._count_by_protocol(df, self.PROTOCOLLI_FASE2),
            'protocols_fase3': self._count_by_protocol(df, self.PROTOCOLLI_FASE3)
        }
    
    def _count_by_protocol(self, df: pd.DataFrame, protocols: list) -> Dict[str, int]:
        """Conta record per protocollo"""
        counts = {}
        for prot in protocols:
            counts[prot] = len(df[df['Protocollo'] == prot])
        return counts
    
    def _create_excel_output(self, df: pd.DataFrame, output_path: Path) -> None:
        """Crea file Excel con 3 fogli"""
        wb = Workbook()
        
        # Stile intestazione
        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF')
        
        # FOGLIO 1: Dati
        ws_dati = wb.active
        ws_dati.title = 'Dati'
        
        for r in dataframe_to_rows(df, index=False, header=True):
            ws_dati.append(r)
        
        # Formatta intestazione
        for cell in ws_dati[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Auto-dimensiona colonne
        for column in ws_dati.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
            ws_dati.column_dimensions[column_letter].width = min(max_length + 2, 50)
        
        # FOGLIO 2: Nota Riepilogativa 2
        ws_nota2 = wb.create_sheet('Nota Riepilogativa 2')
        self._create_summary_sheet(
            ws_nota2, df, self.PROTOCOLLI_FASE2, 
            self.DESCRIZIONI_FASE2, header_fill, header_font
        )
        
        # FOGLIO 3: Nota Riepilogativa 3
        ws_nota3 = wb.create_sheet('Nota Riepilogativa 3')
        self._create_summary_sheet(
            ws_nota3, df, self.PROTOCOLLI_FASE3,
            self.DESCRIZIONI_FASE3, header_fill, header_font
        )
        
        # Salva
        wb.save(output_path)
    
    def _create_summary_sheet(self, ws, df, protocols, descriptions, header_fill, header_font):
        """Crea foglio riepilogativo"""
        # Intestazione
        ws['A1'] = 'PROTOCOLLO'
        ws['B1'] = 'DESCRIZIONE'
        ws['C1'] = 'NUMERO TOTALE'
        
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Dati
        row = 2
        for prot in protocols:
            count = len(df[df['Protocollo'] == prot])
            ws[f'A{row}'] = prot
            ws[f'B{row}'] = descriptions[prot]
            ws[f'C{row}'] = count
            row += 1
        
        # Totale
        ws[f'A{row}'] = 'TOTALE'
        ws[f'A{row}'].font = Font(bold=True)
        ws[f'C{row}'] = f'=SUM(C2:C{row-1})'
        ws[f'C{row}'].font = Font(bold=True)
        
        # Dimensioni colonne
        ws.column_dimensions['A'].width = 15
        ws.column_dimensions['B'].width = 40
        ws.column_dimensions['C'].width = 20
```

### Step 2.3: API Routes (app/api/routes.py)

```python
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import uuid
import shutil
import logging
from datetime import datetime

from app.core.config import settings
from app.services.file_processor import NFSFTFileProcessor

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/process-file")
async def process_file(file: UploadFile = File(...)):
    """
    Processa file NFS/FT Excel
    
    Returns:
        - file_id: ID univoco per download
        - summary: Statistiche elaborazione
        - download_url: URL per scaricare file elaborato
    """
    
    # Valida estensione
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato file non valido. Formati supportati: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    
    # Genera ID univoco
    file_id = str(uuid.uuid4())
    
    # Path temporanei
    upload_path = settings.UPLOAD_DIR / f"{file_id}_input{file_ext}"
    output_path = settings.OUTPUT_DIR / f"{file_id}_output.xlsx"
    
    try:
        # Salva file caricato
        with upload_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Valida dimensione
        file_size = upload_path.stat().st_size
        if file_size > settings.MAX_FILE_SIZE:
            upload_path.unlink()
            raise HTTPException(
                status_code=400,
                detail=f"File troppo grande. Dimensione massima: {settings.MAX_FILE_SIZE / 1024 / 1024:.0f}MB"
            )
        
        # Processa file
        processor = NFSFTFileProcessor()
        stats = processor.process_file(upload_path, output_path)
        
        # Cleanup file input
        upload_path.unlink()
        
        return {
            "success": True,
            "file_id": file_id,
            "summary": stats,
            "download_url": f"/api/download/{file_id}"
        }
        
    except ValueError as e:
        # Errori validazione
        if upload_path.exists():
            upload_path.unlink()
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        # Errori generici
        logger.error(f"Errore elaborazione: {str(e)}")
        if upload_path.exists():
            upload_path.unlink()
        if output_path.exists():
            output_path.unlink()
        raise HTTPException(status_code=500, detail="Errore durante l'elaborazione del file")


@router.get("/download/{file_id}")
async def download_file(file_id: str):
    """Download file elaborato"""
    
    output_path = settings.OUTPUT_DIR / f"{file_id}_output.xlsx"
    
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="File non trovato o scaduto")
    
    # Nome file con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"File_Riepilogativo_NFS_FT_{timestamp}.xlsx"
    
    return FileResponse(
        path=output_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "NFS/FT File Processor"}
```

### Step 2.4: Main App (app/main.py)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.api.routes import router

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# App
app = FastAPI(
    title="NFS/FT File Processor API",
    description="API per elaborazione file Excel NFS/FT",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(router, prefix="/api", tags=["files"])

@app.get("/")
async def root():
    return {
        "message": "NFS/FT File Processor API",
        "version": "1.0.0",
        "docs": "/docs"
    }
```

### Step 2.5: File .env

```bash
# .env
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
MAX_FILE_SIZE=52428800
FILE_RETENTION_HOURS=24
```

### Step 2.6: Testa Backend

```bash
# Avvia server
uvicorn app.main:app --reload --port 8000

# Test endpoint
curl http://localhost:8000/
curl http://localhost:8000/api/health
```

---

## FASE 3: FRONTEND (React + Vite)

### Step 3.1: Creazione Progetto

```bash
cd ../frontend

# Crea progetto React con Vite
npm create vite@latest . -- --template react

# Installa dipendenze
npm install
npm install axios react-dropzone lucide-react
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

### Step 3.2: Configura Tailwind (tailwind.config.js)

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

### Step 3.3: Stile Base (src/index.css)

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
```

---

**CONTINUA NELLA PARTE 2...**

Questa è la prima parte. Vuoi che continui con:
- Frontend React completo (componenti, hooks, UI)
- Script di deployment
- Testing
- Documentazione deployment?
