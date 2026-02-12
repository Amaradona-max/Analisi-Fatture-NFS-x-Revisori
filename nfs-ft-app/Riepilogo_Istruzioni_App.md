# Riepilogo istruzioni applicazione

## Sezioni applicazione
- Due sezioni separate: FT NFS Pagato e FT Pisa Pagato.
- Caricamento file .xlsx con elaborazione e download separati.

## FT NFS Pagato
- Flusso originale con protocolli Fase 2 e Fase 3.
- Duplicati rimossi su FAT_NUM e C_NOME.
- Filtra solo protocolli previsti.
- Output con fogli Dati, Fatture Cartacee, Fatture Elettroniche.

## FT Pisa Pagato – origine dati
Dal file originale FT Pisa Pagato usare queste colonne in ordine nel foglio Dati:
1. Colonna H (Creditore) → Ragione Sociale
2. Colonna C → nome originale
3. Colonna D → nome originale
4. Colonna E → nome originale
5. Colonna F → nome originale
6. Colonna O → nome originale
7. Colonna L (Importo Pagato) → Imponibile
8. Colonna J (Importo Fattura) → Imp.Tot. Fatture
9. Colonna A → nome originale

## FT Pisa Pagato – filtri
- Considerare solo righe con Data Pagamento (colonna F) valorizzata.
- Fatture Cartacee: colonna A (Identificativo SDI) vuota.
- Fatture Elettroniche: colonna A (Identificativo SDI) non vuota.

## FT Pisa Pagato – output
- Foglio Dati con ordine e rinomina indicati.
- Foglio Fatture Cartacee: Numero Totale e Imponibile.
- Foglio Fatture Elettroniche: Numero Totale e Imponibile.
