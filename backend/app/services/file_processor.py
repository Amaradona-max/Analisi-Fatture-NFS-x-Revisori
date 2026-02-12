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
    PROTOCOLLI_FASE3 = [
        "EP",
        "2EP",
        "EL",
        "2EL",
        "EZ",
        "2EZ",
        "EZP",
        "FPIC",
        "FSIC",
        "FPEC",
        "FSEC",
        "AFIC",
        "ASIC",
        "AFEC",
        "ASEC",
        "ACBI",
        "ACSI",
        "ACBE",
        "ACSE",
    ]

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
        "AFIC": "Fatture Elettroniche Estere San",
        "ASIC": "Fatture Elettroniche Estere San",
        "AFEC": "Fatture Elettroniche Estere San",
        "ASEC": "Fatture Elettroniche Estere San",
        "ACBI": "Fatture Elettroniche Estere San",
        "ACSI": "Fatture Elettroniche Estere San",
        "ACBE": "Fatture Elettroniche Estere San",
        "ACSE": "Fatture Elettroniche Estere San",
    }

    REQUIRED_COLUMNS = [
        "C_NOME",
        "FAT_DATDOC",
        "FAT_NDOC",
        "FAT_DATREG",
        "FAT_PROT",
        "FAT_NUM",
        "IMPONIBILE",
        "FAT_TOTFAT",
        "FAT_TOTIVA",
        "DMA_NUM",
        "RA_CODTRIB",
        "RA_IMPOSTA",
        "TMA_TOT",
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
            totale_iniziale = len(df)
            df_senza_duplicati = df.drop_duplicates(subset=["FAT_NUM", "C_NOME"]).copy()
            duplicati_rimossi = totale_iniziale - len(df_senza_duplicati)
            df_filtrato = df_senza_duplicati[df_senza_duplicati["FAT_PROT"].isin(self.all_protocols)].copy()

            if len(df_filtrato) == 0:
                raise ValueError("Nessun protocollo valido trovato nel file")

            df_filtrato["RA_CODTRIB"] = (
                df_filtrato["RA_CODTRIB"]
                .astype(str)
                .str.strip()
                .where(lambda value: value.isin(["I9", "RO"]), "")
            )
            df_filtrato["Tot. Importo Mandato"] = df_filtrato["TMA_TOT"]

            colonne_ordinate = [
                "C_NOME",
                "FAT_DATDOC",
                "FAT_NDOC",
                "FAT_DATREG",
                "FAT_PROT",
                "FAT_NUM",
                "IMPONIBILE",
                "FAT_TOTFAT",
                "FAT_TOTIVA",
                "RA_CODTRIB",
                "DMA_NUM",
                "Tot. Importo Mandato",
                "TMC_G8",
            ]

            df_finale = df_filtrato[colonne_ordinate].copy()
            df_finale.columns = [
                "Ragione Sociale",
                "Data Fatture",
                "N. Fatture",
                "Data Ricevimento",
                "Protocollo",
                "N. Protocollo",
                "Tot. Imponibile",
                "Importo Tot. Fatture",
                "Imposta",
                "Ritenuta d'acconto",
                "N. Mandato",
                "Tot. Importo Mandato",
                "Identificativo SDI",
            ]

            df_finale["Data Fatture"] = pd.to_datetime(df_finale["Data Fatture"], errors="coerce")
            df_finale["Data Ricevimento"] = pd.to_datetime(df_finale["Data Ricevimento"], errors="coerce")

            df_finale = df_finale.sort_values("Data Ricevimento")

            stats = self._calculate_stats(df_finale, duplicati_rimossi)
            self._create_excel_output(df_finale, output_path)

            logger.info("File elaborato con successo: %s", stats)
            return stats
        except Exception as exc:
            logger.error("Errore elaborazione file: %s", str(exc))
            raise

    def _calculate_stats(self, df: pd.DataFrame, duplicates_removed: int) -> Dict[str, Any]:
        fase2_count = df[df["Protocollo"].isin(self.PROTOCOLLI_FASE2)].shape[0]
        fase3_count = df[df["Protocollo"].isin(self.PROTOCOLLI_FASE3)].shape[0]

        return {
            "total_records": len(df),
            "fase2_records": fase2_count,
            "fase3_records": fase3_count,
            "duplicates_removed": duplicates_removed,
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
        total_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
        total_font = Font(bold=True)

        ws_dati = self._add_dataframe_sheet(
            wb,
            "Dati",
            df,
            header_fill,
            header_font,
            total_fill,
            total_font,
            date_columns=["Data Fatture", "Data Ricevimento"],
            money_columns=["Tot. Imponibile", "Importo Tot. Fatture", "Imposta", "Tot. Importo Mandato"],
            use_active=True,
        )

        ws_nota2 = wb.create_sheet("Fatture Cartacee")
        self._create_summary_sheet(
            ws_nota2,
            df,
            self.PROTOCOLLI_FASE2,
            self.DESCRIZIONI_FASE2,
            header_fill,
            header_font,
                total_fill,
                total_font,
        )

        ws_nota3 = wb.create_sheet("Fatture Elettroniche")
        self._create_summary_sheet(
            ws_nota3,
            df,
            self.PROTOCOLLI_FASE3,
            self.DESCRIZIONI_FASE3,
            header_fill,
            header_font,
                total_fill,
                total_font,
        )

        wb.save(output_path)

    def _add_dataframe_sheet(
        self,
        wb: Workbook,
        title: str,
        df: pd.DataFrame,
        header_fill: PatternFill,
        header_font: Font,
        total_fill: PatternFill,
        total_font: Font,
        date_columns=None,
        money_columns=None,
        use_active: bool = False,
    ):
        ws = wb.active if use_active else wb.create_sheet(title)
        ws.title = title

        for r in dataframe_to_rows(df, index=False, header=True):
            ws.append(r)

        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            ws.column_dimensions[column_letter].width = min(max_length + 2, 50)

        date_columns = date_columns or []
        money_columns = money_columns or []
        header_index = {cell.value: cell.column for cell in ws[1]}
        date_format = "mm/dd/yyyy"
        money_format = "#,##0.00"

        for column_name in date_columns:
            column_index = header_index.get(column_name)
            if column_index:
                for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=column_index, max_col=column_index):
                    for cell in row:
                        if cell.value is not None:
                            cell.number_format = date_format

        for column_name in money_columns:
            column_index = header_index.get(column_name)
            if column_index:
                for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=column_index, max_col=column_index):
                    for cell in row:
                        if cell.value is not None:
                            cell.number_format = money_format

        if money_columns:
            totals = {}
            for column_name in money_columns:
                totals[column_name] = pd.to_numeric(df[column_name], errors="coerce").sum()
            total_row = ["TOTALE"] + [""] * (len(df.columns) - 1)
            for column_name, total_value in totals.items():
                total_row[df.columns.get_loc(column_name)] = total_value
            ws.append(total_row)
            total_row_index = ws.max_row
            for cell in ws[total_row_index]:
                cell.fill = total_fill
                cell.font = total_font
            for column_name in money_columns:
                column_index = header_index.get(column_name)
                if column_index:
                    ws.cell(row=total_row_index, column=column_index).number_format = money_format

        return ws

    def _create_summary_sheet(self, ws, df, protocols, descriptions, header_fill, header_font, total_fill, total_font):
        ws["A1"] = "PROTOCOLLO"
        ws["B1"] = "DESCRIZIONE"
        ws["C1"] = "NUMERO TOTALE"
        ws["D1"] = "IMPORTO TOTALE"

        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        money_format = "#,##0.00"
        row = 2
        for prot in protocols:
            count = len(df[df["Protocollo"] == prot])
            importo_totale = pd.to_numeric(
                df.loc[df["Protocollo"] == prot, "Importo Tot. Fatture"], errors="coerce"
            ).sum()
            ws[f"A{row}"] = prot
            ws[f"B{row}"] = descriptions[prot]
            ws[f"C{row}"] = count
            ws[f"D{row}"] = importo_totale
            ws[f"D{row}"].number_format = money_format
            row += 1

        ws[f"A{row}"] = "TOTALE"
        ws[f"A{row}"].font = total_font
        ws[f"C{row}"] = f"=SUM(C2:C{row - 1})"
        ws[f"C{row}"].font = total_font
        ws[f"D{row}"] = f"=SUM(D2:D{row - 1})"
        ws[f"D{row}"].number_format = money_format
        for cell in ws[row]:
            cell.fill = total_fill
            cell.font = total_font

        ws.column_dimensions["A"].width = 15
        ws.column_dimensions["B"].width = 40
        ws.column_dimensions["C"].width = 20
        ws.column_dimensions["D"].width = 20


class PisaFTFileProcessor(NFSFTFileProcessor):
    SELECTED_LETTERS = ["H", "C", "D", "E", "F", "O", "L", "J", "A"]
    RENAME_MAP = {
        "H": "Ragione Sociale",
        "L": "Imponibile",
        "J": "Imp.Tot. Fatture",
    }
    MONEY_COLUMNS = ["Imponibile", "Imp.Tot. Fatture"]

    def process_file(self, input_path: Path, output_path: Path) -> Dict[str, Any]:
        try:
            logger.info("Caricamento file Pisa Ricevute: %s", input_path)
            df = pd.read_excel(input_path)

            required_indices = self._letters_to_indices(self.SELECTED_LETTERS)
            max_index = max(required_indices)
            if df.shape[1] <= max_index:
                missing_letters = [
                    letter for letter, index in zip(self.SELECTED_LETTERS, required_indices) if index >= df.shape[1]
                ]
                raise ValueError(f"Colonne mancanti: {', '.join(missing_letters)}")

            data_pagamento_column = df.columns[self._letters_to_indices(["F"])[0]]
            pagamento_series = df[data_pagamento_column]
            pagamento_mask = ~(pagamento_series.isna() | (pagamento_series.astype(str).str.strip() == ""))
            df_pagato = df[pagamento_mask].copy()

            selected_indices = self._letters_to_indices(self.SELECTED_LETTERS)
            selected_columns = []
            for letter, index in zip(self.SELECTED_LETTERS, selected_indices):
                selected_columns.append(self.RENAME_MAP.get(letter) or df_pagato.columns[index])

            df_finale = df_pagato.iloc[:, selected_indices].copy()
            df_finale.columns = selected_columns

            sdi_column = df.columns[self._letters_to_indices(["A"])[0]]
            cartacee_df, elettroniche_df = self._split_by_sdi(df_finale, sdi_column)
            self._create_excel_output(df_finale, cartacee_df, elettroniche_df, output_path)
            stats = {
                "total_records": len(df_finale),
                "fase2_records": len(cartacee_df),
                "fase3_records": len(elettroniche_df),
                "duplicates_removed": 0,
                "protocols_fase2": {"Cartacee": len(cartacee_df)},
                "protocols_fase3": {"Elettroniche": len(elettroniche_df)},
            }
            logger.info("File Pisa Ricevute elaborato con successo: %s", stats)
            return stats
        except Exception as exc:
            logger.error("Errore elaborazione file Pisa Ricevute: %s", str(exc))
            raise

    def _create_excel_output(
        self,
        df: pd.DataFrame,
        cartacee_df: pd.DataFrame,
        elettroniche_df: pd.DataFrame,
        output_path: Path,
    ) -> None:
        wb = Workbook()

        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        total_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
        total_font = Font(bold=True)

        self._add_dataframe_sheet(
            wb,
            "Dati",
            df,
            header_fill,
            header_font,
            total_fill,
            total_font,
            money_columns=self.MONEY_COLUMNS,
            use_active=True,
        )

        ws_cartacee = wb.create_sheet("Fatture Cartacee")
        self._create_simple_summary_sheet(
            ws_cartacee,
            cartacee_df,
            header_fill,
            header_font,
            total_fill,
            total_font,
        )

        ws_elettroniche = wb.create_sheet("Fatture Elettroniche")
        self._create_simple_summary_sheet(
            ws_elettroniche,
            elettroniche_df,
            header_fill,
            header_font,
            total_fill,
            total_font,
        )

        wb.save(output_path)

    def _split_by_sdi(self, df: pd.DataFrame, sdi_column: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        sdi_series = df[sdi_column]
        empty_mask = sdi_series.isna() | (sdi_series.astype(str).str.strip() == "")
        cartacee_df = df[empty_mask].copy()
        elettroniche_df = df[~empty_mask].copy()
        return cartacee_df, elettroniche_df

    def _letters_to_indices(self, letters: list[str]) -> list[int]:
        return [ord(letter) - ord("A") for letter in letters]

    def _create_simple_summary_sheet(
        self,
        ws,
        df: pd.DataFrame,
        header_fill: PatternFill,
        header_font: Font,
        total_fill: PatternFill,
        total_font: Font,
    ) -> None:
        ws["A1"] = "NUMERO TOTALE"
        ws["B1"] = "IMPONIBILE"

        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        imponibile_totale = pd.to_numeric(df["Imponibile"], errors="coerce").sum()
        ws["A2"] = len(df)
        ws["B2"] = imponibile_totale
        ws["B2"].number_format = "#,##0.00"

        for cell in ws[2]:
            cell.fill = total_fill
            cell.font = total_font

        ws.column_dimensions["A"].width = 20
        ws.column_dimensions["B"].width = 20
