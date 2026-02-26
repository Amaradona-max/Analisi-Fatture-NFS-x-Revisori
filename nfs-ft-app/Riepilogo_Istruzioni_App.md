# Guida operativa — 1. Query Fatture NFS (Ricevute 2025)

Questa guida descrive la procedura completa, passo passo, per:
- elaborare il file **FT NFS Ricevute**
- elaborare il file **FT Pisa Ricevute**
- generare il **Confronto** tra i due file sul periodo **01/01/2025–31/12/2025**

## Prerequisiti
- File in formato `.xlsx` (massimo 50 MB).
- I file devono contenere le colonne richieste (vedi sezione “Colonne richieste”).

## Procedura passo passo

### 1) Elaborazione FT NFS Ricevute
1. Apri la sezione **FT NFS Ricevute**.
2. Seleziona il file `.xlsx` (es. `FT NFS Ricevute al 31.12.2025.xlsx`).
3. Attendi la fine dell’elaborazione.
4. Verifica il riepilogo mostrato a schermo:
   - **Record Totali**
   - **Duplicati rimossi**
   - **Fase 2 – Cartacee**
   - **Fase 3 – Elettroniche**
5. Clicca **Scarica File Elaborato** per ottenere l’Excel di output.

**Cosa trovi nel file scaricato (NFS)**
- `Dati`: righe elaborate e normalizzate.
- `Fatture Cartacee`: riepilogo per protocolli cartacei (Fase 2).
- `Fatture Elettroniche`: riepilogo per protocolli elettronici (Fase 3).
- `Fatture Elettroniche SDI Unico` (se presente): sole elettroniche con SDI non vuoto e non duplicato.

### 2) Elaborazione FT Pisa Ricevute
1. Apri la sezione **FT Pisa Ricevute**.
2. Seleziona il file `.xlsx` (es. `FT Pisa Ricevute al 31.12.2025.xlsx`).
3. Attendi la fine dell’elaborazione.
4. Verifica il riepilogo mostrato a schermo:
   - **Record Totali**
   - **Fase 2 – Cartacee**
   - **Fase 3 – Elettroniche**
5. Clicca **Scarica File Elaborato** per ottenere l’Excel di output.

**Cosa trovi nel file scaricato (Pisa)**
- `Dati`: righe elaborate (con colonne di interesse e formati data/importo).
- `Fatture Cartacee`: riepilogo (numero totale e imponibile totale).
- `Fatture Elettroniche`: riepilogo (numero totale e imponibile totale).
- `Fatture Elettroniche SDI` (se presente): dettaglio delle sole elettroniche.

### 3) Confronto tra FT NFS e FT Pisa (periodo 2025)
1. Apri la sezione **Confronto**.
2. Carica i due file:
   - **FT NFS**: file NFS Ricevute
   - **FT Pisa**: file Pisa Ricevute
   In alternativa, se disponibili, usa **Usa ultimi file caricati**.
3. Clicca **Confronta e genera file**.
4. A fine elaborazione verifica il riepilogo a schermo:
   - blocco **NFS**: `Cartacee` e `Elettroniche` con **conteggio** e **importo**
   - blocco **Pisa**: `Cartacee` e `Elettroniche` con **conteggio** e **importo**
5. Clicca **Scarica file confronto** per ottenere l’Excel di confronto.
6. Per ripetere da zero, usa **Nuovo confronto**.

**Cosa trovi nel file scaricato (Confronto)**
- `Confronto`: tabella riassuntiva (Cartacee/Elettroniche/Totale) con delta.
- `Dati e Valori Attesi`: riepilogo NFS vs Pisa con delta.
- `Differenze tra file`: righe “in più” (o mancanti) nei due file.
- `Differenze Elettroniche SDI`: differenze basate su Identificativo SDI.
- `Differenze SDI in Comune`: SDI presenti in entrambi con importi/quantità diverse.

## Regole usate (come vengono calcolati i numeri)

### Periodo considerato nel Confronto
- Il confronto considera solo righe nel periodo **01/01/2025–31/12/2025**.
- La data usata per il filtro è:
  - **NFS**: data di registrazione/immissione (`FAT_DATREG` oppure `DATA_REG_FATTURA`)
  - **Pisa**: `Data emissione`

### Cartacee vs Elettroniche
- **NFS**
  - Cartacee: protocolli di Fase 2.
  - Elettroniche: protocolli di Fase 3.
- **Pisa**
  - Cartacee: `Identificativo SDI` vuoto / nullo / `0`.
  - Elettroniche: `Identificativo SDI` valorizzato.

## Colonne richieste (per evitare “Colonne mancanti”)

### FT NFS Ricevute
- Colonne minime richieste:
  - `C_NOME`, `FAT_PROT`, `FAT_NUM`, `FAT_NDOC`, `FAT_DATDOC`, `IMPONIBILE`, `FAT_TOTFAT`, `FAT_TOTIVA`,
    `RA_IMPON`, `RA_IMPOSTA`, `RA_CODTRIB`, `TMC_G8`
  - data registrazione: `FAT_DATREG` oppure `DATA_REG_FATTURA`

### FT Pisa Ricevute
- Colonne minime richieste:
  - `Creditore`, `Numero fattura`, `Data emissione`, `Data documento`, `IVA`, `Importo fattura`, `Identificativo SDI`

## Problemi comuni
- **Colonne mancanti**: verifica che i nomi colonna nel file corrispondano esattamente a quelli richiesti.
- **Numeri/importi con virgola**: l’app gestisce sia `,` sia `.` nei campi importo.
- **Il confronto mostra ancora i valori precedenti**: esegui **Nuovo confronto** e ricarica i file (o aggiorna la pagina e ripeti il confronto).

## Log chiusure giornata (automatico)
Questa sezione viene aggiornata automaticamente dalla funzione di “chiusura giornata”.
