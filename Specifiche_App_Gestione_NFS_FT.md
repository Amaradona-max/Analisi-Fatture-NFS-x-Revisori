# App Gestione File NFS/FT - Specifiche Tecniche

## 1. PANORAMICA DEL PROGETTO

### Scopo
Applicazione web per l'elaborazione automatica di file Excel contenenti dati di fatturazione NFS/FT, con funzionalità di:
- Caricamento file Excel (.xlsx)
- Filtraggio automatico per protocollo
- Riorganizzazione colonne secondo schema predefinito
- Eliminazione duplicati
- Generazione note riepilogative
- Download file elaborato

### Tecnologie Suggerite
- **Frontend**: React + Tailwind CSS
- **Backend**: Python (FastAPI o Flask)
- **Librerie Python**: pandas, openpyxl
- **Deploy**: Vercel (frontend) + Railway/Render (backend)

---

## 2. REGOLE DI BUSINESS

### 2.1 Protocolli da Mantenere

#### FASE 2 - Fatture Cartacee
| Protocollo | Descrizione |
|------------|-------------|
| P | Fatture Cartacee San |
| 2P | Fatture Cartacee Ter |
| LABI | Fatture Lib.Prof. San |
| FCBI | Fatture Cartacee Estere San |
| FCSI | Fatture Cartacee Estere San |
| FCBE | Fatture Cartacee Estere San |
| FCSE | Fatture Cartacee Estere San |

#### FASE 3 - Fatture Elettroniche
| Protocollo | Descrizione |
|------------|-------------|
| EP | Fatture Elettroniche San |
| 2EP | Fatture Elettroniche Ter |
| EL | Fatture Elettroniche Lib.Prof. San |
| 2EL | Fatture Elettroniche Lib.Prof. Ter |
| EZ | Fatture Elettroniche Commerciali San |
| 2EZ | Fatture Elettroniche Commerciali Ter |
| EZP | Fatture Elettroniche Commerciali San |
| FPIC | Fatture Elettroniche Estere San |
| FSIC | Fatture Elettroniche Estere San |
| FPEC | Fatture Elettroniche Estere San |
| FSEC | Fatture Elettroniche Estere San |

### 2.2 Mappatura Colonne

#### Schema di Riordinamento
```
Posizione | Colonna Originale | Nome Nuovo | Note
----------|-------------------|------------|-----
1 | N (C_NOME) | Ragione sociale | 
2 | J (FAT_DATDOC) | Data Fatture |
3 | L (FAT_NDOC) | N. fatture |
4 | K (FAT_DATREG) | Data Ricevimento | Usata per ordinamento
5 | B (FAT_PROT) | Protocollo |
6 | C (FAT_NUM) | N. Protocollo |
7 | I (IMPONIBILE) | Tot. imponibile |
8 | G (FAT_TOTIVA) | Imposta |
9 | E (PA_IMPORTO) | Tot. Fatture |
10 | X (DMA_NUM) | N. Mandato |
11 | Y (TMA_DTGEN) | Data Mandato |
12 | NUOVA | Tot. Importo Mandato | Copia colonna H (FAT_TOTFAT)
13 | AB (TMC_G8) | Id. SDI |
```

### 2.3 Elaborazione Dati

#### Step di Elaborazione
1. **Pulizia**: Rimuovi spazi bianchi dai protocolli
2. **Filtraggio**: Mantieni solo protocolli Fase 2 e Fase 3
3. **Creazione Colonne**: Crea "Tot. Importo Mandato" copiando FAT_TOTFAT (colonna H)
4. **Riordinamento**: Riorganizza colonne secondo schema
5. **Ordinamento**: Ordina per "Data Ricevimento" (colonna K)
6. **Eliminazione Duplicati**: Verifica e rimuovi duplicati (se presenti)

#### Validazioni
- File deve essere .xlsx
- Deve contenere tutte le colonne richieste
- Almeno 1 record con protocolli validi

---

## 3. STRUTTURA FILE OUTPUT

### Foglio 1: "Dati"
- Contiene tutti i record filtrati e riordinati
- Intestazione con sfondo blu (#4472C4), testo bianco, grassetto
- Colonne auto-dimensionate
- Ordinamento per "Data Ricevimento"

### Foglio 2: "Nota Riepilogativa 2"
Tabella con 3 colonne:
| PROTOCOLLO | DESCRIZIONE | NUMERO TOTALE |
|------------|-------------|---------------|
| P | Fatture Cartacee San | [conteggio] |
| ... | ... | ... |
| **TOTALE** | | **[formula SUM]** |

### Foglio 3: "Nota Riepilogativa 3"
Stessa struttura del Foglio 2, ma per protocolli Fase 3

---

## 4. INTERFACCIA UTENTE

### 4.1 Layout Principale

```
┌─────────────────────────────────────────────┐
│  🗂️  Gestione File NFS/FT                   │
├─────────────────────────────────────────────┤
│                                             │
│  [Area di Drop File]                        │
│  Trascina qui il file Excel oppure clicca   │
│  per selezionarlo                           │
│                                             │
│  ✓ Formati supportati: .xlsx                │
│  ✓ Dimensione max: 50MB                     │
│                                             │
├─────────────────────────────────────────────┤
│                                             │
│  [Barra di Progresso]                       │
│                                             │
├─────────────────────────────────────────────┤
│                                             │
│  📊 Riepilogo Elaborazione                  │
│  • Record totali: 5.352                     │
│  • Fase 2: 25 record                        │
│  • Fase 3: 5.327 record                     │
│  • Duplicati rimossi: 0                     │
│                                             │
│  [📥 Scarica File Elaborato]                │
│                                             │
└─────────────────────────────────────────────┘
```

### 4.2 Stati dell'Interfaccia

1. **Iniziale**: Area drop + istruzioni
2. **Caricamento**: Spinner + percentuale
3. **Elaborazione**: Barra progresso con step
4. **Completato**: Riepilogo + pulsante download
5. **Errore**: Messaggio errore + possibilità di ricaricare

---

## 5. API BACKEND

### Endpoint 1: Upload e Elaborazione
```
POST /api/process-file
Content-Type: multipart/form-data

Request:
- file: Excel file (.xlsx)

Response (200 OK):
{
  "success": true,
  "file_id": "uuid-generated",
  "summary": {
    "total_records": 5352,
    "fase2_records": 25,
    "fase3_records": 5327,
    "duplicates_removed": 0
  },
  "download_url": "/api/download/uuid-generated"
}

Response (400 Bad Request):
{
  "success": false,
  "error": "Descrizione errore",
  "details": "Dettagli tecnici"
}
```

### Endpoint 2: Download File
```
GET /api/download/{file_id}

Response:
- Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
- Content-Disposition: attachment; filename="File_Riepilogativo_NFS_FT_{timestamp}.xlsx"
```

---

## 6. ALGORITMO DI ELABORAZIONE (Python)

### Pseudocodice

```python
def process_nfs_ft_file(uploaded_file):
    # 1. Carica file Excel
    df = pd.read_excel(uploaded_file)
    
    # 2. Pulizia protocolli
    df['FAT_PROT'] = df['FAT_PROT'].astype(str).str.strip()
    
    # 3. Definisci protocolli validi
    protocolli_fase2 = ['P', '2P', 'LABI', 'FCBI', 'FCSI', 'FCBE', 'FCSE']
    protocolli_fase3 = ['EP', '2EP', 'EL', '2EL', 'EZ', '2EZ', 'EZP', 
                        'FPIC', 'FSIC', 'FPEC', 'FSEC']
    
    # 4. Filtra record
    df_filtrato = df[df['FAT_PROT'].isin(protocolli_fase2 + protocolli_fase3)]
    
    # 5. Crea colonna Tot. Importo Mandato
    df_filtrato['Tot. Importo Mandato'] = df_filtrato['FAT_TOTFAT']
    
    # 6. Seleziona e riordina colonne
    colonne_ordinate = ['C_NOME', 'FAT_DATDOC', 'FAT_NDOC', 'FAT_DATREG',
                        'FAT_PROT', 'FAT_NUM', 'IMPONIBILE', 'FAT_TOTIVA',
                        'PA_IMPORTO', 'DMA_NUM', 'TMA_DTGEN', 
                        'Tot. Importo Mandato', 'TMC_G8']
    
    df_finale = df_filtrato[colonne_ordinate].copy()
    
    # 7. Rinomina colonne
    df_finale.columns = ['Ragione sociale', 'Data Fatture', 'N. fatture',
                         'Data Ricevimento', 'Protocollo', 'N. Protocollo',
                         'Tot. imponibile', 'Imposta', 'Tot. Fatture',
                         'N. Mandato', 'Data Mandato', 'Tot. Importo Mandato',
                         'Id. SDI']
    
    # 8. Ordina per Data Ricevimento
    df_finale = df_finale.sort_values('Data Ricevimento')
    
    # 9. Crea file Excel con 3 fogli
    wb = Workbook()
    
    # Foglio Dati
    create_data_sheet(wb, df_finale)
    
    # Foglio Nota Riepilogativa 2
    create_summary_sheet_2(wb, df_finale, protocolli_fase2)
    
    # Foglio Nota Riepilogativa 3
    create_summary_sheet_3(wb, df_finale, protocolli_fase3)
    
    # 10. Salva e ritorna
    return wb
```

---

## 7. GESTIONE ERRORI

### Errori da Gestire

| Errore | Causa | Messaggio Utente |
|--------|-------|------------------|
| File non .xlsx | Formato sbagliato | "Formato file non valido. Carica un file .xlsx" |
| File corrotto | Excel danneggiato | "File danneggiato o non leggibile" |
| Colonne mancanti | Struttura errata | "Il file non contiene le colonne richieste" |
| Nessun record valido | Nessun protocollo | "Nessun protocollo valido trovato nel file" |
| File troppo grande | Dimensione > 50MB | "File troppo grande. Max 50MB" |

---

## 8. OTTIMIZZAZIONI SUGGERITE

### Performance
- Chunking per file grandi (>10k righe)
- Caching file processati (Redis)
- Cleanup automatico file vecchi (>24h)

### UX
- Preview primi 10 record prima download
- Possibilità di modificare mapping colonne
- Storico elaborazioni recenti
- Esportazione anche in CSV

### Sicurezza
- Validazione estensione file server-side
- Scansione antivirus file upload
- Rate limiting API
- CORS configurato correttamente

---

## 9. DEPLOYMENT

### Frontend (Vercel)
```bash
# vercel.json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "env": {
    "VITE_API_URL": "@api_url"
  }
}
```

### Backend (Railway/Render)
```bash
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 10. TESTING

### Test Unitari
- Validazione protocolli
- Mappatura colonne
- Calcolo conteggi

### Test Integrazione
- Upload file → elaborazione → download
- Gestione errori file invalidi
- Performance con file grandi

### Test E2E
- Flusso utente completo
- Download file corretto
- UI responsive

---

## 11. DOCUMENTAZIONE UTENTE

### Guida Rapida
1. Carica il file Excel cliccando o trascinando
2. Attendi l'elaborazione (pochi secondi)
3. Verifica il riepilogo
4. Scarica il file elaborato

### FAQ
**Q: Quali formati sono supportati?**  
A: Solo file .xlsx (Excel 2007+)

**Q: Cosa succede ai protocolli non in elenco?**  
A: Vengono automaticamente esclusi dal file elaborato

**Q: I dati vengono salvati?**  
A: No, i file vengono eliminati dopo 24h per privacy

---

## 12. ROADMAP FUTURE

### Fase 1 (MVP)
- [x] Upload file
- [x] Elaborazione base
- [x] Download risultato

### Fase 2
- [ ] Autenticazione utenti
- [ ] Storico elaborazioni
- [ ] Template personalizzabili

### Fase 3
- [ ] API per integrazioni
- [ ] Dashboard analytics
- [ ] Export multipli formati

---

## APPENDICE A: Esempio File Input

```
FAT_ESE | FAT_PROT | FAT_NUM | ... | C_NOME | ... | FAT_TOTFAT
--------|----------|---------|-----|--------|-----|------------
2025    | EP       | 2007    | ... | ACME   | ... | 159.19
2025    | SVI      | 1234    | ... | TEST   | ... | 500.00  (escluso)
2025    | 2EP      | 1528    | ... | CORP   | ... | 1000.50
```

## APPENDICE B: Esempio File Output

### Foglio "Dati"
```
Ragione sociale | Data Fatture | ... | Tot. Importo Mandato
----------------|--------------|-----|---------------------
ACME INC        | 2025-01-15   | ... | 159.19
CORP SRL        | 2025-01-16   | ... | 1000.50
```

### Foglio "Nota Riepilogativa 2"
```
PROTOCOLLO | DESCRIZIONE              | NUMERO TOTALE
-----------|--------------------------|---------------
P          | Fatture Cartacee San     | 7
2P         | Fatture Cartacee Ter     | 16
TOTALE     |                          | 25
```

---

**Versione**: 1.0  
**Data**: Febbraio 2025  
**Autore**: Specifiche generate per app gestione NFS/FT
