from pathlib import Path
from typing import Any, Dict
import logging

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows


logger = logging.getLogger(__name__)


class NFSFTFileProcessor:
    PROTOCOLLI_FASE2 = ["P", "2P", "LABI", "FCBI", "FCSI", "FCBE", "FCSE"]
    PROTOCOLLI_FASE3 = ["EP", "2EP", "EL", "2EL", "EZ", "2EZ", "EZP", "FPIC", "FSIC", "FPEC", "FSEC"]

    DESCRIZIONI_FASE2 = {
        "P": "Fatture Cartacee San",
        "2P": "Fatture Cartacee Ter",
        "LABI": "Fatture Lib.Prof. San",
        "FCBI": "Fatture Cartacee Estere San",
        "FCSI": "Fatture Cartacee Estere San",
        "FCBE": "Fatture Cartacee Estere San",
        "FCSE": "Fatture Cartacee Estere San",
    }

    DESCRIZIONI_FASE3 = {
        "EP": "Fatture Elettroniche San",
        "2EP": "Fatture Elettroniche Ter",
        "EL": "Fatture Elettroniche Lib.Prof. San",
        "2EL": "Fatture Elettroniche Lib.Prof. Ter",
        "EZ": "Fatture Elettroniche Commerciali San",
        "2EZ": "Fatture Elettroniche Commerciali Ter",
        "EZP": "Fatture Elettroniche Commerciali San",
        "FPIC": "Fatture Elettroniche Estere San",
        "FSIC": "Fatture Elettroniche Estere San",
        "FPEC": "Fatture Elettroniche Estere San",
        "FSEC": "Fatture Elettroniche Estere San",
    }

    REQUIRED_COLUMNS = [
        "C_NOME",
        "FAT_DATDOC",
        "FAT_NDOC",
        "FAT_DATREG",
        "FAT_PROT",
        "FAT_NUM",
        "IMPONIBILE",
        "FAT_TOTIVA",
        "PA_IMPORTO",
        "DMA_NUM",
        "TMA_DTGEN",
        "FAT_TOTFAT",
        "TMC_G8",
    ]

    def __init__(self) -> None:
        self.all_protocols = self.PROTOCOLLI_FASE2 + self.PROTOCOLLI_FASE3

    def validate_file(self, df: pd.DataFrame) -> None:
        missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Colonne mancanti: {', '.join(missing_cols)}")

    def process_file(self, input_path: Path, output_path: Path) -> Dict[str, Any]:
        try:
            logger.info("Caricamento file: %s", input_path)
            df = pd.read_excel(input_path)

            self.validate_file(df)

            df["FAT_PROT"] = df["FAT_PROT"].astype(str).str.strip()
            df_filtrato = df[df["FAT_PROT"].isin(self.all_protocols)].copy()

            if len(df_filtrato) == 0:
                raise ValueError("Nessun protocollo valido trovato nel file")

            df_filtrato["Tot. Importo Mandato"] = df_filtrato["IMPONIBILE"]

            colonne_ordinate = [
                "C_NOME",
                "FAT_DATDOC",
                "FAT_NDOC",
                "FAT_DATREG",
                "FAT_PROT",
                "FAT_NUM",
                "IMPONIBILE",
                "FAT_TOTIVA",
                "PA_IMPORTO",
                "DMA_NUM",
                "TMA_DTGEN",
                "Tot. Importo Mandato",
                "TMC_G8",
            ]

            df_finale = df_filtrato[colonne_ordinate].copy()
            df_finale.columns = [
                "Ragione sociale",
                "Data Fatture",
                "N. fatture",
                "Data Ricevimento",
                "Protocollo",
                "N. Protocollo",
                "Tot. imponibile",
                "Imposta",
                "Tot. Fatture",
                "N. Mandato",
                "Data Mandato",
                "Tot. Importo Mandato",
                "Id. SDI",
            ]

            df_finale = df_finale.sort_values("Data Ricevimento")

            stats = self._calculate_stats(df_finale)
            self._create_excel_output(df_finale, output_path)

            logger.info("File elaborato con successo: %s", stats)
            return stats
        except Exception as exc:
            logger.error("Errore elaborazione file: %s", str(exc))
            raise

    def _calculate_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        fase2_count = df[df["Protocollo"].isin(self.PROTOCOLLI_FASE2)].shape[0]
        fase3_count = df[df["Protocollo"].isin(self.PROTOCOLLI_FASE3)].shape[0]

        return {
            "total_records": len(df),
            "fase2_records": fase2_count,
            "fase3_records": fase3_count,
            "duplicates_removed": 0,
            "protocols_fase2": self._count_by_protocol(df, self.PROTOCOLLI_FASE2),
            "protocols_fase3": self._count_by_protocol(df, self.PROTOCOLLI_FASE3),
        }

    def _count_by_protocol(self, df: pd.DataFrame, protocols: list) -> Dict[str, int]:
        counts = {}
        for prot in protocols:
            counts[prot] = len(df[df["Protocollo"] == prot])
        return counts

    def _create_excel_output(self, df: pd.DataFrame, output_path: Path) -> None:
        wb = Workbook()

        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")

        ws_dati = wb.active
        ws_dati.title = "Dati"

        for r in dataframe_to_rows(df, index=False, header=True):
            ws_dati.append(r)

        for cell in ws_dati[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for column in ws_dati.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            ws_dati.column_dimensions[column_letter].width = min(max_length + 2, 50)

        ws_nota2 = wb.create_sheet("Nota Riepilogativa 2")
        self._create_summary_sheet(
            ws_nota2,
            df,
            self.PROTOCOLLI_FASE2,
            self.DESCRIZIONI_FASE2,
            header_fill,
            header_font,
        )

        ws_nota3 = wb.create_sheet("Nota Riepilogativa 3")
        self._create_summary_sheet(
            ws_nota3,
            df,
            self.PROTOCOLLI_FASE3,
            self.DESCRIZIONI_FASE3,
            header_fill,
            header_font,
        )

        wb.save(output_path)

    def _create_summary_sheet(self, ws, df, protocols, descriptions, header_fill, header_font):
        ws["A1"] = "PROTOCOLLO"
        ws["B1"] = "DESCRIZIONE"
        ws["C1"] = "NUMERO TOTALE"

        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        row = 2
        for prot in protocols:
            count = len(df[df["Protocollo"] == prot])
            ws[f"A{row}"] = prot
            ws[f"B{row}"] = descriptions[prot]
            ws[f"C{row}"] = count
            row += 1

        ws[f"A{row}"] = "TOTALE"
        ws[f"A{row}"].font = Font(bold=True)
        ws[f"C{row}"] = f"=SUM(C2:C{row - 1})"
        ws[f"C{row}"].font = Font(bold=True)

        ws.column_dimensions["A"].width = 15
        ws.column_dimensions["B"].width = 40
        ws.column_dimensions["C"].width = 20
