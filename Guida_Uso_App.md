# Guida passo passo all’uso dell’app

Questa guida spiega, in modo semplice e sequenziale, come ottenere il file di confronto finale e come interpretare i risultati principali.

## 1) Apri l’app

- Apri l’interfaccia dell’applicazione nel browser.

## 2) Prepara i file da caricare

- File NFS FT Pagato (formato .xlsx).
- File FT Pisa Pagato (formato .xlsx).

Assicurati che i file siano quelli del periodo che vuoi analizzare.

## 3) Avvia il confronto

- Nella sezione Confronto completo carica i due file (NFS e Pisa).
- Avvia l’elaborazione.
- Attendi il completamento del processo.

## 4) Scarica il file di confronto

- Quando l’elaborazione termina, scarica il file riepilogativo.
- Il file è un Excel con più fogli.

## 5) Fogli principali e cosa contengono

### Confronto
- Riepilogo delle quantità e degli importi per cartacee ed elettroniche.
- Permette di vedere le differenze complessive tra NFS e Pisa.

### Differenze tra file
- Elenco delle fatture elettroniche presenti in Pisa ma non in NFS.
- Colonne principali: File, Categoria, Ragione sociale, Numero fattura, Data documento, Data Registrazione Fattura, Data immissione, Imponibile, imposta, Importo tot. fattura, Identificativo SDI.

### Delta FT in dettaglio
- Elenco dettagliato delle fatture Pisa che risultano in eccesso rispetto a NFS:
  - Fatture cartacee (Pisa) senza corrispondenza in NFS.
  - Fatture elettroniche (Pisa) senza corrispondenza in NFS.
- Serve per capire quali documenti mancano nel file NFS.

## 6) Come leggere i risultati

- Se nel foglio Confronto il Delta Numero è diverso da zero:
  - Vai al foglio Delta FT in dettaglio per vedere il dettaglio delle fatture mancanti in NFS.
- Se il Delta Numero è zero:
  - Non ci sono fatture Pisa che mancano in NFS.

## 7) Consigli pratici

- Usa sempre i file più recenti e dello stesso periodo.
- Dopo ogni modifica o aggiornamento dell’app, rigenera il confronto.
- Se non trovi un foglio atteso, ripeti l’elaborazione e riscarica il file.

## 8) Risultato finale atteso

Un file Excel con i fogli:
- Confronto
- Differenze tra file
- Delta FT in dettaglio

Da questi fogli puoi verificare rapidamente:
- Se i totali NFS e Pisa sono coerenti.
- Quali fatture Pisa non risultano presenti in NFS.
