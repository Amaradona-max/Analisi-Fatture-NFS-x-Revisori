# Guida operativa (procedura attuale funzionante)

Questa guida descrive esclusivamente la procedura **attualmente implementata e corretta** per:

- Elaborare il file **FT NFS Ricevute**
- Elaborare il file **FT Pisa Ricevute (Fase 1)**
- Eseguire il **confronto NFS vs Pisa** sul periodo **Gennaio 2025**
- Scaricare e leggere i file Excel di output generati dall’app

## 1) Avvio applicazione (locale)

### Backend (API)

Da cartella:

`nfs-ft-app/backend`

Esegui:

```bash
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Endpoint principali esposti:

- `POST /api/process-file` (elabora FT NFS Ricevute)
- `POST /api/process-file-pisa` (elabora FT Pisa Ricevute – Fase 1)
- `POST /api/process-compare` (confronto NFS vs Pisa)
- `GET /api/download/{file_id}` (download Excel di output)
- `GET /api/health` (healthcheck)

### Frontend (UI)

Da cartella:

`nfs-ft-app/frontend`

Esegui:

```bash
npm run dev -- --host 0.0.0.0 --port 5173
```

Apri l’app nel browser:

`http://localhost:5173/`

## 2) Elaborazione FT NFS Ricevute (file singolo)

### 2.1 Input richiesto (colonne minime)

Il file deve contenere almeno queste colonne (nomi originali del file Excel):

- `C_NOME`
- `FAT_DATDOC`
- `FAT_NDOC`
- `FAT_DATREG`
- `FAT_PROT`
- `FAT_NUM`
- `IMPONIBILE`
- `FAT_TOTFAT`
- `FAT_TOTIVA`
- `RA_IMPON`
- `RA_CODTRIB`
- `RA_IMPOSTA`
- `TMC_G8`

### 2.2 Regole applicate

Durante l’elaborazione NFS:

- Vengono rimossi i duplicati considerando la coppia:
  - `FAT_NUM` + `C_NOME`
- Vengono mantenute solo le righe con protocolli ammessi:
  - Fatture cartacee (Fase 2): `P`, `2P`, `LABI`, `FCBI`, `FCSI`, `FCBE`, `FCSE`
  - Fatture elettroniche (Fase 3): `EP`, `2EP`, `EL`, `2EL`, `EZ`, `2EZ`, `EZP`, `FPIC`, `FSIC`, `FPEC`, `FSEC`, `AFIC`, `ASIC`, `AFEC`, `ASEC`, `ACBI`, `ACSI`, `ACBE`, `ACSE`

### 2.3 Output generato

Scaricando l’output dell’elaborazione NFS ottieni un Excel con 3 fogli:

- `Dati`: elenco righe (con date formattate `dd/mm/yyyy` e importi con 2 decimali)
- `Fatture Cartacee`: riepilogo per protocolli Fase 2
- `Fatture Elettroniche`: riepilogo per protocolli Fase 3

## 3) Elaborazione FT Pisa Ricevute (Fase 1)

### 3.1 Input richiesto (colonne minime)

Il file Pisa deve contenere almeno:

- `Creditore`
- `Numero fattura`
- `Data emissione`
- `Data documento`
- `Data pagamento`
- `IVA`
- `Importo fattura`
- `Identificativo SDI`

### 3.2 Regole di calcolo (Fase 1)

Per ogni riga:

- `Totale fatture` = `Importo fattura` (convertito in numero; supporta virgola come separatore decimale)
- `Ivam` = `IVA` (convertito in numero; supporta virgola come separatore decimale)
- `Imponibile` = `Totale fatture` − `Ivam`

Classificazione:

- **Cartacee**: `Identificativo SDI` vuoto / nullo / “0…” / oppure con lunghezza ≤ 3
- **Elettroniche**: tutte le altre

### 3.3 Output generato

Scaricando l’output dell’elaborazione Pisa ottieni un Excel con 3 fogli:

- `Dati`: elenco righe (date `dd/mm/yyyy`, importi a 2 decimali)
- `Fatture Cartacee`: conteggio + somma `Totale fatture`
- `Fatture Elettroniche`: conteggio + somma `Totale fatture`

Controllo atteso per la Fase 1 (come riferimento operativo):

- `Fatture Cartacee`: **N.253** e **€ 974.610,34** (Totale fatture)

## 4) Confronto FT NFS Ricevute vs FT Pisa Ricevute (Gennaio 2025)

### 4.1 Input del confronto

Il confronto usa i **file originali** caricati (prima dell’elaborazione singola), con queste regole:

- NFS: periodo filtrato con data `FAT_DATREG` (rinominata `Datat reg.`) nel mese **Gennaio 2025**
- Pisa: periodo filtrato con `Data emissione` nel mese **Gennaio 2025**

### 4.2 Regole NFS (nel confronto)

1) Rimozione duplicati:
- prima del confronto i duplicati NFS vengono rimossi con chiave `FAT_NUM` + `C_NOME`

2) Filtri:
- sono considerate solo righe con protocollo appartenente a Fase 2 o Fase 3 (liste in §2.2)

3) Classificazione cartacee/elettroniche:
- **Cartacee NFS** = (protocollo in Fase 2) **e** `Identificativo SDI` vuoto
- **Elettroniche NFS** = tutte le altre righe NFS rimaste dopo i filtri

4) Importo usato:
- per entrambe le categorie (cartacee/elettroniche) l’importo è `Imponibile`

### 4.3 Regole Pisa (nel confronto)

Classificazione cartacee/elettroniche:

- **Cartacee Pisa** = `Identificativo SDI` vuoto (o nullo/0)
- **Elettroniche Pisa** = `Identificativo SDI` valorizzato

Importo usato:

- per entrambe le categorie l’importo è `Importo fattura`

### 4.4 Normalizzazione Identificativo SDI

Nel confronto l’`Identificativo SDI` viene normalizzato per evitare mismatch tipici del formato Excel:

- i valori numerici tipo `12345.0` vengono trattati come `12345`
- vuoti / null / `0` vengono considerati “SDI vuoto”

## 5) Output del confronto (Excel)

Scaricando il file di confronto ottieni un Excel con i seguenti fogli.

### 5.1 Foglio “Confronto”

Riepilogo per Gennaio 2025:

- Cartacee: numero + importo NFS vs Pisa e delta
- Elettroniche: numero + importo NFS vs Pisa e delta
- Totale: totali e delta

### 5.2 Foglio “Fatture da Verificare”

Elenco delle sole righe **da controllare**, costruito aggregando per `Identificativo SDI` (non vuoto) e segnalando gli scostamenti.

Colonna `Esito`:

- `Solo NFS`: SDI presente solo nel NFS
- `Solo Pisa`: SDI presente solo nel Pisa
- `Importo diverso`: SDI presente in entrambi ma importi diversi
- `Numero diverso`: SDI presente in entrambi ma conteggio righe diverso

Nota operativa:

- se per uno stesso SDI i campi descrittivi (es. creditore/numero/data) non sono univoci, l’output mostra `MULTIPLE` nel campo interessato.

### 5.3 Foglio “Differenze Elettroniche SDI”

Analisi dettagliata delle fatture elettroniche (SDI valorizzato) mostrando:

- `Solo Pisa`: SDI presente nel Pisa (Gennaio 2025) ma assente nel NFS (Gennaio 2025)
- `Solo NFS`: SDI presente nel NFS (Gennaio 2025) ma assente nel Pisa (Gennaio 2025)
- `NFS SDI vuoto`: righe NFS considerate elettroniche ma con SDI vuoto (casistiche anomale da verificare)

### 5.4 Foglio “Differenze SDI in Comune”

Questo foglio considera solo gli SDI che sono:

- presenti sia in NFS che in Pisa (Gennaio 2025)
- **univoci** su entrambi i lati (1 riga in NFS e 1 riga in Pisa)

Vengono riportate solo le righe con `Delta Importo` diverso da 0 (tolleranza 0,01).

### 5.5 Foglio “Pisa Solo - Mese NFS”

Per ogni SDI che è:

- presente nel Pisa (Gennaio 2025) come elettronica
- assente nel NFS (Gennaio 2025) come elettronica

il foglio ricerca lo stesso SDI nel file NFS completo e riporta:

- `NFS Mesi trovati`: elenco mesi (`YYYY-MM`) in cui lo SDI compare nel NFS
- `NFS Prima registrazione`: prima data `Datat reg.` trovata nel NFS

## 6) Deploy: GitHub e Vercel

### 6.1 GitHub

La procedura è:

1) Commit delle modifiche locali
2) Push su branch `main`

### 6.2 Vercel

Se il progetto Vercel è collegato al repository GitHub:

- ogni push su `main` avvia automaticamente un nuovo deploy

Verifica:

- Vercel → Project → Deployments → controlla l’ultimo deploy associato all’ultimo commit su `main`
