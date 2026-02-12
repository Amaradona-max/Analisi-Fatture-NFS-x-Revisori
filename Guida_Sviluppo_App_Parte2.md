# Guida Passo-Passo: Sviluppo App Gestione NFS/FT - PARTE 2

## FASE 3: FRONTEND (Continua)

### Step 3.4: API Service (src/services/api.js)

```javascript
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'multipart/form-data',
  },
});

export const fileAPI = {
  /**
   * Carica e processa file Excel
   * @param {File} file - File da caricare
   * @param {Function} onProgress - Callback per progresso upload
   * @returns {Promise} Risposta API con statistiche
   */
  processFile: async (file, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await api.post('/api/process-file', formData, {
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress?.(percentCompleted);
        },
      });
      return response.data;
    } catch (error) {
      throw new Error(
        error.response?.data?.detail || 'Errore durante il caricamento del file'
      );
    }
  },

  /**
   * Scarica file elaborato
   * @param {string} fileId - ID del file da scaricare
   * @returns {Promise<Blob>} File blob
   */
  downloadFile: async (fileId) => {
    try {
      const response = await api.get(`/api/download/${fileId}`, {
        responseType: 'blob',
      });
      return response.data;
    } catch (error) {
      throw new Error('Errore durante il download del file');
    }
  },

  /**
   * Health check
   * @returns {Promise} Status API
   */
  healthCheck: async () => {
    const response = await api.get('/api/health');
    return response.data;
  },
};

export default api;
```

### Step 3.5: Componente FileUpload (src/components/FileUpload.jsx)

```javascript
import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileSpreadsheet, AlertCircle } from 'lucide-react';

const FileUpload = ({ onFileSelect, disabled }) => {
  const [error, setError] = useState(null);

  const onDrop = useCallback(
    (acceptedFiles, rejectedFiles) => {
      setError(null);

      if (rejectedFiles.length > 0) {
        const rejection = rejectedFiles[0];
        if (rejection.errors[0]?.code === 'file-too-large') {
          setError('File troppo grande. Dimensione massima: 50MB');
        } else if (rejection.errors[0]?.code === 'file-invalid-type') {
          setError('Formato file non valido. Carica un file .xlsx');
        } else {
          setError('File non valido');
        }
        return;
      }

      if (acceptedFiles.length > 0) {
        onFileSelect(acceptedFiles[0]);
      }
    },
    [onFileSelect]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    },
    maxSize: 52428800, // 50MB
    maxFiles: 1,
    disabled,
  });

  return (
    <div className="w-full">
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-12 text-center cursor-pointer
          transition-colors duration-200
          ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />
        
        <div className="flex flex-col items-center gap-4">
          {isDragActive ? (
            <FileSpreadsheet className="w-16 h-16 text-blue-500" />
          ) : (
            <Upload className="w-16 h-16 text-gray-400" />
          )}
          
          <div className="space-y-2">
            <p className="text-lg font-medium text-gray-700">
              {isDragActive
                ? 'Rilascia il file qui'
                : 'Trascina qui il file Excel oppure clicca per selezionarlo'}
            </p>
            <p className="text-sm text-gray-500">
              ✓ Formati supportati: .xlsx
              <br />
              ✓ Dimensione massima: 50MB
            </p>
          </div>
        </div>
      </div>

      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}
    </div>
  );
};

export default FileUpload;
```

### Step 3.6: Componente ProgressBar (src/components/ProgressBar.jsx)

```javascript
import React from 'react';

const ProgressBar = ({ progress, status }) => {
  return (
    <div className="w-full space-y-2">
      <div className="flex justify-between text-sm text-gray-600">
        <span>{status}</span>
        <span>{progress}%</span>
      </div>
      
      <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
        <div
          className="bg-blue-600 h-2.5 rounded-full transition-all duration-300 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
};

export default ProgressBar;
```

### Step 3.7: Componente Summary (src/components/Summary.jsx)

```javascript
import React from 'react';
import { FileCheck, FileText, Download } from 'lucide-react';

const Summary = ({ summary, onDownload, downloading }) => {
  return (
    <div className="w-full space-y-6">
      <div className="flex items-center gap-3">
        <FileCheck className="w-8 h-8 text-green-600" />
        <h2 className="text-2xl font-bold text-gray-800">
          Elaborazione Completata
        </h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-blue-50 p-6 rounded-lg border border-blue-200">
          <div className="flex items-center gap-3 mb-2">
            <FileText className="w-5 h-5 text-blue-600" />
            <h3 className="font-semibold text-gray-700">Record Totali</h3>
          </div>
          <p className="text-3xl font-bold text-blue-600">
            {summary.total_records.toLocaleString('it-IT')}
          </p>
        </div>

        <div className="bg-green-50 p-6 rounded-lg border border-green-200">
          <h3 className="font-semibold text-gray-700 mb-2">Fase 2 - Cartacee</h3>
          <p className="text-3xl font-bold text-green-600">
            {summary.fase2_records.toLocaleString('it-IT')}
          </p>
          <div className="mt-3 space-y-1 text-xs text-gray-600">
            {Object.entries(summary.protocols_fase2).map(([prot, count]) => (
              count > 0 && (
                <div key={prot} className="flex justify-between">
                  <span>{prot}:</span>
                  <span className="font-medium">{count}</span>
                </div>
              )
            ))}
          </div>
        </div>

        <div className="bg-purple-50 p-6 rounded-lg border border-purple-200 md:col-span-2">
          <h3 className="font-semibold text-gray-700 mb-2">Fase 3 - Elettroniche</h3>
          <p className="text-3xl font-bold text-purple-600 mb-3">
            {summary.fase3_records.toLocaleString('it-IT')}
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-1 text-xs text-gray-600">
            {Object.entries(summary.protocols_fase3).map(([prot, count]) => (
              count > 0 && (
                <div key={prot} className="flex justify-between">
                  <span>{prot}:</span>
                  <span className="font-medium">{count}</span>
                </div>
              )
            ))}
          </div>
        </div>
      </div>

      <button
        onClick={onDownload}
        disabled={downloading}
        className="w-full md:w-auto px-8 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 
                   text-white font-semibold rounded-lg transition-colors duration-200
                   flex items-center justify-center gap-2 mx-auto"
      >
        <Download className="w-5 h-5" />
        {downloading ? 'Download in corso...' : 'Scarica File Elaborato'}
      </button>
    </div>
  );
};

export default Summary;
```

### Step 3.8: App Component (src/App.jsx)

```javascript
import React, { useState } from 'react';
import { FileSpreadsheet, RefreshCw, AlertCircle } from 'lucide-react';
import FileUpload from './components/FileUpload';
import ProgressBar from './components/ProgressBar';
import Summary from './components/Summary';
import { fileAPI } from './services/api';

function App() {
  const [file, setFile] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [downloading, setDownloading] = useState(false);

  const handleFileSelect = async (selectedFile) => {
    setFile(selectedFile);
    setError(null);
    setResult(null);
    setProcessing(true);
    setProgress(0);
    setStatus('Caricamento file...');

    try {
      // Upload e processing
      const response = await fileAPI.processFile(selectedFile, (uploadProgress) => {
        setProgress(uploadProgress);
        if (uploadProgress === 100) {
          setStatus('Elaborazione in corso...');
        }
      });

      setStatus('Completato!');
      setResult(response);
      setProcessing(false);
    } catch (err) {
      setError(err.message);
      setProcessing(false);
      setFile(null);
    }
  };

  const handleDownload = async () => {
    if (!result?.file_id) return;

    setDownloading(true);
    try {
      const blob = await fileAPI.downloadFile(result.file_id);
      
      // Crea link temporaneo per download
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
      link.download = `File_Riepilogativo_NFS_FT_${timestamp}.xlsx`;
      
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('Errore durante il download del file');
    } finally {
      setDownloading(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setResult(null);
    setError(null);
    setProcessing(false);
    setProgress(0);
    setStatus('');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="flex items-center justify-center gap-3 mb-4">
            <FileSpreadsheet className="w-12 h-12 text-blue-600" />
            <h1 className="text-4xl font-bold text-gray-800">
              Gestione File NFS/FT
            </h1>
          </div>
          <p className="text-gray-600">
            Elaborazione automatica file Excel con filtraggio protocolli e note riepilogative
          </p>
        </div>

        {/* Main Card */}
        <div className="bg-white rounded-2xl shadow-xl p-8 space-y-8">
          {/* Error Message */}
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-red-800">{error}</p>
              </div>
              <button
                onClick={() => setError(null)}
                className="text-red-600 hover:text-red-800"
              >
                ✕
              </button>
            </div>
          )}

          {/* Upload Area */}
          {!processing && !result && (
            <FileUpload onFileSelect={handleFileSelect} disabled={processing} />
          )}

          {/* Processing */}
          {processing && (
            <div className="space-y-6">
              <div className="flex items-center gap-3">
                <RefreshCw className="w-6 h-6 text-blue-600 animate-spin" />
                <h3 className="text-lg font-semibold text-gray-700">
                  Elaborazione in corso...
                </h3>
              </div>
              <ProgressBar progress={progress} status={status} />
              <p className="text-sm text-gray-600 text-center">
                File: <span className="font-medium">{file?.name}</span>
              </p>
            </div>
          )}

          {/* Results */}
          {result && !processing && (
            <div className="space-y-6">
              <Summary
                summary={result.summary}
                onDownload={handleDownload}
                downloading={downloading}
              />
              
              <div className="pt-6 border-t border-gray-200">
                <button
                  onClick={handleReset}
                  className="w-full md:w-auto px-6 py-2 text-gray-700 hover:text-gray-900 
                             font-medium transition-colors duration-200 mx-auto block"
                >
                  Elabora nuovo file
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-sm text-gray-600">
          <p>Versione 1.0.0 | Supporto: .xlsx | Max 50MB</p>
        </div>
      </div>
    </div>
  );
}

export default App;
```

### Step 3.9: Variabili Ambiente Frontend (.env)

```bash
# .env
VITE_API_URL=http://localhost:8000
```

### Step 3.10: Testa Frontend

```bash
# Avvia dev server
npm run dev

# Apri browser su http://localhost:5173
```

---

## FASE 4: TESTING

### Step 4.1: Test Backend (backend/tests/test_processor.py)

```python
import pytest
from pathlib import Path
import pandas as pd
from app.services.file_processor import NFSFTFileProcessor

@pytest.fixture
def sample_dataframe():
    """Crea DataFrame di test"""
    return pd.DataFrame({
        'C_NOME': ['ACME Inc', 'Test Corp'],
        'FAT_DATDOC': ['2025-01-01', '2025-01-02'],
        'FAT_NDOC': ['F001', 'F002'],
        'FAT_DATREG': ['2025-01-01', '2025-01-02'],
        'FAT_PROT': ['EP', 'P'],
        'FAT_NUM': [1, 2],
        'IMPONIBILE': [100.0, 200.0],
        'FAT_TOTIVA': [22.0, 44.0],
        'PA_IMPORTO': [122.0, 244.0],
        'DMA_NUM': ['M001', 'M002'],
        'TMA_DTGEN': ['2025-01-01', '2025-01-02'],
        'FAT_TOTFAT': [122.0, 244.0],
        'TMC_G8': ['ID1', 'ID2']
    })

def test_validate_file_success(sample_dataframe):
    processor = NFSFTFileProcessor()
    processor.validate_file(sample_dataframe)  # Non deve sollevare eccezioni

def test_validate_file_missing_columns():
    processor = NFSFTFileProcessor()
    df = pd.DataFrame({'WRONG_COL': [1, 2]})
    
    with pytest.raises(ValueError, match="Colonne mancanti"):
        processor.validate_file(df)

def test_calculate_stats(sample_dataframe):
    processor = NFSFTFileProcessor()
    df_processed = sample_dataframe.copy()
    df_processed.columns = [
        'Ragione sociale', 'Data Fatture', 'N. fatture',
        'Data Ricevimento', 'Protocollo', 'N. Protocollo',
        'Tot. imponibile', 'Imposta', 'Tot. Fatture',
        'N. Mandato', 'Data Mandato', 'FAT_TOTFAT', 'Id. SDI'
    ]
    
    stats = processor._calculate_stats(df_processed)
    
    assert stats['total_records'] == 2
    assert stats['fase2_records'] == 1  # P
    assert stats['fase3_records'] == 1  # EP
```

### Step 4.2: Esegui Test

```bash
cd backend
pip install pytest pytest-cov

# Esegui test
pytest tests/ -v

# Con coverage
pytest tests/ --cov=app --cov-report=html
```

---

## FASE 5: DEPLOYMENT

### Step 5.1: Backend su Railway

1. **Crea Dockerfile (backend/Dockerfile)**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Installa dipendenze
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia codice
COPY . .

# Crea directory
RUN mkdir -p uploads outputs

# Esponi porta
EXPOSE 8000

# Avvia app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

2. **Deploy su Railway**

```bash
# Installa Railway CLI
npm install -g @railway/cli

# Login
railway login

# Inizializza progetto
railway init

# Deploy
railway up

# Ottieni URL
railway domain
```

3. **Variabili ambiente su Railway**
```
ALLOWED_ORIGINS=https://your-frontend.vercel.app
MAX_FILE_SIZE=52428800
```

### Step 5.2: Frontend su Vercel

1. **Configura vercel.json (frontend/)**

```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/" }
  ],
  "env": {
    "VITE_API_URL": "@api_url"
  }
}
```

2. **Deploy**

```bash
# Installa Vercel CLI
npm install -g vercel

# Deploy
cd frontend
vercel

# Produzione
vercel --prod
```

3. **Configura variabili ambiente su Vercel Dashboard**
```
VITE_API_URL=https://your-backend.railway.app
```

---

## FASE 6: MANUTENZIONE

### Step 6.1: Script Cleanup (backend/cleanup.py)

```python
"""Script per pulizia file vecchi"""
import os
from pathlib import Path
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_old_files(directory: Path, hours: int = 24):
    """Elimina file più vecchi di N ore"""
    now = datetime.now()
    cutoff = now - timedelta(hours=hours)
    
    deleted = 0
    for file_path in directory.glob('*'):
        if file_path.is_file():
            file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_time < cutoff:
                file_path.unlink()
                deleted += 1
                logger.info(f"Eliminato: {file_path.name}")
    
    logger.info(f"Pulizia completata. File eliminati: {deleted}")
    return deleted

if __name__ == "__main__":
    from app.core.config import settings
    
    logger.info("Inizio pulizia file...")
    cleanup_old_files(settings.UPLOAD_DIR, settings.FILE_RETENTION_HOURS)
    cleanup_old_files(settings.OUTPUT_DIR, settings.FILE_RETENTION_HOURS)
```

### Step 6.2: Cron Job (crontab)

```bash
# Esegui cleanup ogni ora
0 * * * * cd /path/to/backend && /path/to/venv/bin/python cleanup.py
```

---

## FASE 7: MONITORING

### Step 7.1: Logging Avanzato

```python
# backend/app/main.py
from fastapi import Request
import time

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} "
        f"completed in {process_time:.2f}s "
        f"with status {response.status_code}"
    )
    
    return response
```

### Step 7.2: Health Check

```bash
# Script health check
#!/bin/bash
curl -f http://localhost:8000/api/health || exit 1
```

---

## CHECKLIST FINALE

### Backend
- [ ] Tutti i test passano
- [ ] CORS configurato correttamente
- [ ] Variabili ambiente impostate
- [ ] Logging funzionante
- [ ] Cleanup automatico attivo
- [ ] Health check risponde

### Frontend
- [ ] Build senza errori
- [ ] API URL configurata
- [ ] Upload file funziona
- [ ] Download funziona
- [ ] UI responsive
- [ ] Gestione errori corretta

### Deployment
- [ ] Backend deployato e accessibile
- [ ] Frontend deployato e accessibile
- [ ] CORS tra frontend/backend OK
- [ ] SSL certificati attivi
- [ ] Monitoring attivo

### Documentazione
- [ ] README.md completo
- [ ] API documentata (Swagger)
- [ ] Guida utente creata
- [ ] Variabili ambiente documentate

---

## COMANDI RAPIDI

```bash
# Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload

# Frontend
cd frontend
npm run dev

# Test
cd backend && pytest tests/ -v
cd frontend && npm test

# Build
cd frontend && npm run build

# Deploy
railway up  # Backend
vercel --prod  # Frontend
```

---

**Fine Guida Parte 2**

Ora hai tutto il necessario per sviluppare, testare e deployare la tua app!
