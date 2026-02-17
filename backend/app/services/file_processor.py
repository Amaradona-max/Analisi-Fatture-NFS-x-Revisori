from pathlib import Path
from typing import Any, Dict, List, Optional
import logging
import re

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
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
        "RA_IMPON",
        "RA_CODTRIB",
        "RA_IMPOSTA",
        "TMC_G8",
    ]

    def __init__(self) -> None:
        self.all_protocols = self.PROTOCOLLI_FASE2 + self.PROTOCOLLI_FASE3

    def validate_file(self, df: pd.DataFrame) -> None:
        missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Colonne mancanti: {', '.join(missing_cols)}")

    def _filter_january_2025(self, df: pd.DataFrame, date_column: str) -> pd.DataFrame:
        if date_column not in df.columns:
            return df.iloc[0:0].copy()
        date_series = pd.to_datetime(df[date_column], errors="coerce")
        start = pd.Timestamp(year=2025, month=1, day=1)
        end = pd.Timestamp(year=2025, month=1, day=31)
        mask = date_series.between(start, end)
        return df[mask].copy()

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

            colonne_ordinate = [
                "C_NOME",
                "FAT_DATDOC",
                "FAT_NDOC",
                "FAT_DATREG",
                "FAT_PROT",
                "FAT_NUM",
                "FAT_TOTIVA",
                "IMPONIBILE",
                "FAT_TOTFAT",
                "RA_CODTRIB",
                "RA_IMPOSTA",
                "RA_IMPON",
                "TMC_G8",
            ]

            df_finale = df_filtrato[colonne_ordinate].copy()
            df_finale.columns = [
                "Ragione Sociale",
                "Data Fatture",
                "N. Fatture",
                "Data Registrazione",
                "Protocollo",
                "N. Protocollo",
                "Imposta",
                "Tot. Imponibile",
                "Tot. Imp. Fatture",
                "Rit. Codice Tributo",
                "Rit. Imposta",
                "Rit. Imp.",
                "Identificativo SDI",
            ]

            df_finale["Data Fatture"] = pd.to_datetime(df_finale["Data Fatture"], errors="coerce")
            df_finale["Data Registrazione"] = pd.to_datetime(df_finale["Data Registrazione"], errors="coerce")

            df_finale = df_finale.sort_values("Data Registrazione")

            df_dati = df_finale.copy()
            if "Data Registrazione" in df_dati.columns:
                df_dati["Imponibile"] = df_dati["Data Registrazione"]
                df_dati = df_dati.drop(columns=["Data Registrazione"], errors="ignore")
            df_dati = df_dati.drop(columns=["Tot. Imponibile"], errors="ignore")
            ordered_columns = [
                "Ragione Sociale",
                "Data Fatture",
                "N. Fatture",
                "Protocollo",
                "N. Protocollo",
                "Imposta",
                "Imponibile",
                "Tot. Imp. Fatture",
                "Rit. Codice Tributo",
                "Rit. Imposta",
                "Rit. Imp.",
                "Identificativo SDI",
            ]
            df_dati = df_dati[[col for col in ordered_columns if col in df_dati.columns]]

            stats = self._calculate_stats(df_finale, duplicati_rimossi)
            self._create_excel_output(df_finale, output_path, display_df=df_dati)

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

    def _create_excel_output(
        self,
        df: pd.DataFrame,
        output_path: Path,
        display_df: Optional[pd.DataFrame] = None,
    ) -> None:
        wb = Workbook()

        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        total_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
        total_font = Font(bold=True)

        ws_dati = self._add_dataframe_sheet(
            wb,
            "Dati",
            display_df if display_df is not None else df,
            header_fill,
            header_font,
            total_fill,
            total_font,
            date_columns=["Data Fatture", "Data Registrazione", "Imponibile"],
            money_columns=["Imposta", "Tot. Imponibile", "Tot. Imp. Fatture", "Rit. Imposta", "Rit. Imp."],
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
        date_format: str = "mm/dd/yyyy",
        add_totals: bool = True,
        auto_size: bool = True,
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

        if auto_size:
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                ws.column_dimensions[column_letter].width = min(max_length + 2, 50)

        date_columns = date_columns or []
        money_columns = money_columns or []
        money_columns = [column for column in money_columns if column in df.columns]
        header_index = {cell.value: cell.column for cell in ws[1]}
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

        if money_columns and add_totals:
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
        ws["D1"] = "IMPONIBILE"

        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        money_format = "#,##0.00"
        row = 2
        for prot in protocols:
            count = len(df[df["Protocollo"] == prot])
            imponibile_totale = pd.to_numeric(
                df.loc[df["Protocollo"] == prot, "Tot. Imponibile"], errors="coerce"
            ).sum()
            ws[f"A{row}"] = prot
            ws[f"B{row}"] = descriptions[prot]
            ws[f"C{row}"] = count
            ws[f"D{row}"] = imponibile_totale
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
    PHASE = 1
    INPUT_REQUIRED_COLUMNS = [
        "Creditore",
        "Numero fattura",
        "Data emissione",
        "Data documento",
        "Data pagamento",
        "IVA",
        "Importo fattura",
        "Identificativo SDI",
    ]
    OUTPUT_COLUMNS = [
        "Ragione sociale",
        "N.fatture",
        "Data emissione",
        "Data documento",
        "Data pagamento",
        "Ivam",
        "Imponibile",
        "Totale fatture",
        "Identificativo SDI",
    ]
    OUTPUT_DATE_COLUMNS = ["Data emissione", "Data documento", "Data pagamento"]
    OUTPUT_MONEY_COLUMNS = ["Ivam", "Imponibile", "Totale fatture"]
    MAX_DETAIL_ROWS = 5000

    def process_file(self, input_path: Path, output_path: Path) -> Dict[str, Any]:
        try:
            logger.info("Caricamento file Pisa Ricevute: %s", input_path)
            try:
                df = pd.read_excel(input_path, usecols=self.INPUT_REQUIRED_COLUMNS, dtype=str)
            except ValueError:
                df_header = pd.read_excel(input_path, nrows=0)
                missing_columns = [col for col in self.INPUT_REQUIRED_COLUMNS if col not in df_header.columns]
                if missing_columns:
                    raise ValueError(f"Colonne mancanti: {', '.join(missing_columns)}")
                raise

            totale_fattura = pd.to_numeric(
                df["Importo fattura"].astype(str).str.replace(",", ".", regex=False),
                errors="coerce",
            ).fillna(0)
            iva = pd.to_numeric(
                df["IVA"].astype(str).str.replace(",", ".", regex=False),
                errors="coerce",
            ).fillna(0)
            imponibile = totale_fattura - iva

            df_finale = pd.DataFrame(
                {
                    "Ragione sociale": df["Creditore"],
                    "N.fatture": df["Numero fattura"],
                    "Data emissione": pd.to_datetime(df["Data emissione"], errors="coerce"),
                    "Data documento": pd.to_datetime(df["Data documento"], errors="coerce"),
                    "Data pagamento": pd.to_datetime(df["Data pagamento"], errors="coerce"),
                    "Ivam": iva,
                    "Imponibile": imponibile,
                    "Totale fatture": totale_fattura,
                    "Identificativo SDI": df["Identificativo SDI"],
                }
            )
            df_finale = df_finale[self.OUTPUT_COLUMNS]

            cartacee_df, elettroniche_df = self._split_by_sdi(df_finale, "Identificativo SDI")
            self._create_excel_output(df_finale, cartacee_df, elettroniche_df, output_path, display_df=df_finale)
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
        display_df: Optional[pd.DataFrame] = None,
    ) -> None:
        wb = Workbook()

        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        total_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
        total_font = Font(bold=True)

        dati_df = display_df if display_df is not None else df
        self._add_dataframe_sheet(
            wb,
            "Dati",
            dati_df,
            header_fill,
            header_font,
            total_fill,
            total_font,
            date_columns=self.OUTPUT_DATE_COLUMNS,
            date_format="dd/mm/yyyy",
            money_columns=self.OUTPUT_MONEY_COLUMNS,
            auto_size=False,
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
        normalized = sdi_series.astype(str).str.strip()
        normalized_lower = normalized.str.lower()
        zero_mask = normalized_lower.str.fullmatch(r"0+(\.0+)?").fillna(False)
        short_mask = normalized.str.len().fillna(0) <= 3
        empty_mask = normalized_lower.isin(["", "nan", "none", "null"]) | zero_mask | short_mask
        cartacee_df = df[empty_mask].copy()
        elettroniche_df = df[~empty_mask].copy()
        return cartacee_df, elettroniche_df

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
        ws["B1"] = "TOTALE FATTURE"

        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        totale_fatture = pd.to_numeric(df["Totale fatture"], errors="coerce").sum()
        ws["A2"] = len(df)
        ws["B2"] = totale_fatture
        ws["B2"].number_format = "#,##0.00"

        for cell in ws[2]:
            cell.fill = total_fill
            cell.font = total_font

        ws.column_dimensions["A"].width = 20
        ws.column_dimensions["B"].width = 20


class CompareFTFileProcessor:
    NFS_REQUIRED_COLUMNS = [
        "C_NOME",
        "FAT_PROT",
        "FAT_NUM",
        "FAT_NDOC",
        "FAT_DATDOC",
        "FAT_DATREG",
        "FAT_TOTIVA",
        "IMPONIBILE",
        "FAT_TOTFAT",
        "RA_IMPON",
        "RA_IMPOSTA",
        "RA_CODTRIB",
        "TMC_G8",
    ]
    NFS_RENAME_MAP = {
        "C_NOME": "Ragione sociale",
        "FAT_PROT": "Prot.",
        "FAT_NUM": "FAT_NUM",
        "FAT_NDOC": "N.fatture",
        "FAT_DATDOC": "Data Fatture",
        "FAT_DATREG": "Datat reg.",
        "FAT_TOTIVA": "Iva",
        "IMPONIBILE": "Imponibile",
        "FAT_TOTFAT": "Tot. imp. fatture",
        "RA_IMPON": "Imp. rit.",
        "RA_IMPOSTA": "Rit. Imposta",
        "RA_CODTRIB": "Codice tributo",
        "TMC_G8": "Identificativo SDI",
    }
    NFS_DATE_COLUMNS = ["Data Fatture", "Datat reg."]
    NFS_MONEY_COLUMNS = ["Iva", "Imponibile", "Tot. imp. fatture", "Imp. rit.", "Rit. Imposta"]
    NFS_CARTACEE_PROTOCOLS = NFSFTFileProcessor.PROTOCOLLI_FASE2
    NFS_ELETTRONICHE_PROTOCOLS = NFSFTFileProcessor.PROTOCOLLI_FASE3

    PISA_REQUIRED_COLUMNS = ["Creditore", "Numero fattura", "Identificativo SDI", "Data emissione", "Importo fattura"]

    def process_files(self, nfs_input_path: Path, pisa_input_path: Path, output_path: Path) -> Dict[str, Any]:
        try:
            df_nfs_raw = pd.read_excel(nfs_input_path, usecols=self.NFS_REQUIRED_COLUMNS)
        except ValueError:
            df_nfs_header = pd.read_excel(nfs_input_path, nrows=0)
            missing_nfs = [col for col in self.NFS_REQUIRED_COLUMNS if col not in df_nfs_header.columns]
            if missing_nfs:
                raise ValueError(f"Colonne mancanti nel file NFS: {', '.join(missing_nfs)}")
            raise

        try:
            df_pisa_raw = pd.read_excel(pisa_input_path, usecols=self.PISA_REQUIRED_COLUMNS, dtype=str)
        except ValueError:
            df_pisa_header = pd.read_excel(pisa_input_path, nrows=0)
            missing_pisa = [col for col in self.PISA_REQUIRED_COLUMNS if col not in df_pisa_header.columns]
            if missing_pisa:
                raise ValueError(f"Colonne mancanti nel file Pisa: {', '.join(missing_pisa)}")
            raise

        df_nfs_lookup = df_nfs_raw[["FAT_DATREG", "TMC_G8"]].copy()
        df_nfs_lookup.rename(columns={"FAT_DATREG": "Datat reg.", "TMC_G8": "Identificativo SDI"}, inplace=True)
        df_nfs_lookup["Datat reg."] = pd.to_datetime(df_nfs_lookup["Datat reg."], errors="coerce")
        df_nfs_lookup["_SDI_KEY"] = self._normalize_sdi(df_nfs_lookup["Identificativo SDI"])

        df_nfs_deduped = df_nfs_raw.drop_duplicates(subset=["FAT_NUM", "C_NOME"]).copy()
        df_nfs = df_nfs_deduped[self.NFS_REQUIRED_COLUMNS].copy()
        df_nfs.rename(columns=self.NFS_RENAME_MAP, inplace=True)
        df_nfs["Data Fatture"] = pd.to_datetime(df_nfs["Data Fatture"], errors="coerce")
        df_nfs["Datat reg."] = pd.to_datetime(df_nfs["Datat reg."], errors="coerce")
        df_nfs["Imponibile"] = pd.to_numeric(df_nfs["Imponibile"], errors="coerce").fillna(0)

        df_pisa = df_pisa_raw[self.PISA_REQUIRED_COLUMNS].copy()
        df_pisa["Data emissione"] = pd.to_datetime(df_pisa["Data emissione"], errors="coerce")
        df_pisa["Importo fattura"] = pd.to_numeric(
            df_pisa["Importo fattura"].astype(str).str.replace(",", ".", regex=False),
            errors="coerce",
        ).fillna(0)

        df_nfs["_SDI_KEY"] = self._normalize_sdi(df_nfs["Identificativo SDI"])
        df_pisa["_SDI_KEY"] = self._normalize_sdi(df_pisa["Identificativo SDI"])

        df_nfs_jan = self._filter_january_2025(df_nfs, "Datat reg.")
        df_pisa_jan = self._filter_january_2025(df_pisa, "Data emissione")

        nfs_protocol = df_nfs_jan["Prot."].astype(str).str.strip()
        df_nfs_jan = df_nfs_jan[nfs_protocol.isin(self.NFS_CARTACEE_PROTOCOLS + self.NFS_ELETTRONICHE_PROTOCOLS)].copy()
        nfs_protocol = df_nfs_jan["Prot."].astype(str).str.strip()
        nfs_sdi_empty = self._is_empty_sdi(df_nfs_jan["_SDI_KEY"])
        nfs_cart_mask = nfs_protocol.isin(self.NFS_CARTACEE_PROTOCOLS) & nfs_sdi_empty
        nfs_elet_mask = ~nfs_cart_mask
        pisa_cart_mask = self._is_empty_sdi(df_pisa_jan["_SDI_KEY"])

        nfs_cart_count = int(nfs_cart_mask.sum())
        nfs_elet_count = int(nfs_elet_mask.sum())
        pisa_cart_count = int(pisa_cart_mask.sum())
        pisa_elet_count = int((~pisa_cart_mask).sum())

        nfs_cart_amount = round(float(df_nfs_jan.loc[nfs_cart_mask, "Imponibile"].sum()), 2)
        nfs_elet_amount = round(float(df_nfs_jan.loc[nfs_elet_mask, "Imponibile"].sum()), 2)
        pisa_cart_amount = round(float(df_pisa_jan.loc[pisa_cart_mask, "Importo fattura"].sum()), 2)
        pisa_elet_amount = round(float(df_pisa_jan.loc[~pisa_cart_mask, "Importo fattura"].sum()), 2)

        summary = {
            "period": "2025-01",
            "nfs": {
                "cartacee": {"count": nfs_cart_count, "amount": nfs_cart_amount, "amount_column": "Imponibile"},
                "elettroniche": {"count": nfs_elet_count, "amount": nfs_elet_amount, "amount_column": "Imponibile"},
            },
            "pisa": {
                "cartacee": {"count": pisa_cart_count, "amount": pisa_cart_amount, "amount_column": "Importo fattura"},
                "elettroniche": {"count": pisa_elet_count, "amount": pisa_elet_amount, "amount_column": "Importo fattura"},
            },
        }

        wb = Workbook()
        ws = wb.active
        ws.title = "Confronto"

        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        total_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
        total_font = Font(bold=True)

        headers = ["Categoria", "NFS Numero", "NFS Importo", "Pisa Numero", "Pisa Importo", "Delta Numero", "Delta Importo"]
        for col_idx, value in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=value)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        rows = [
            ("Cartacee", nfs_cart_count, nfs_cart_amount, pisa_cart_count, pisa_cart_amount),
            ("Elettroniche", nfs_elet_count, nfs_elet_amount, pisa_elet_count, pisa_elet_amount),
            (
                "Totale",
                nfs_cart_count + nfs_elet_count,
                round(nfs_cart_amount + nfs_elet_amount, 2),
                pisa_cart_count + pisa_elet_count,
                round(pisa_cart_amount + pisa_elet_amount, 2),
            ),
        ]
        money_format = "#,##0.00"
        for row_idx, (categoria, n_num, n_imp, p_num, p_imp) in enumerate(rows, start=2):
            ws.cell(row=row_idx, column=1, value=categoria)
            ws.cell(row=row_idx, column=2, value=n_num)
            ws.cell(row=row_idx, column=3, value=n_imp).number_format = money_format
            ws.cell(row=row_idx, column=4, value=p_num)
            ws.cell(row=row_idx, column=5, value=p_imp).number_format = money_format
            ws.cell(row=row_idx, column=6, value=n_num - p_num)
            ws.cell(row=row_idx, column=7, value=round(n_imp - p_imp, 2)).number_format = money_format

        for cell in ws[ws.max_row]:
            cell.fill = total_fill
            cell.font = total_font

        ws.column_dimensions["A"].width = 18
        ws.column_dimensions["B"].width = 14
        ws.column_dimensions["C"].width = 16
        ws.column_dimensions["D"].width = 14
        ws.column_dimensions["E"].width = 16
        ws.column_dimensions["F"].width = 14
        ws.column_dimensions["G"].width = 16

        self._create_fatture_da_verificare_sheet(
            wb=wb,
            df_nfs=df_nfs_jan,
            df_pisa=df_pisa_jan,
            header_fill=header_fill,
            header_font=header_font,
        )
        self._create_differenze_elettroniche_sheet(
            wb=wb,
            df_nfs=df_nfs_jan,
            df_pisa=df_pisa_jan,
            nfs_elet_mask=nfs_elet_mask,
            pisa_cart_mask=pisa_cart_mask,
            header_fill=header_fill,
            header_font=header_font,
        )
        self._create_differenze_sdi_univoche_sheet(
            wb=wb,
            df_nfs=df_nfs_jan,
            df_pisa=df_pisa_jan,
            nfs_elet_mask=nfs_elet_mask,
            pisa_cart_mask=pisa_cart_mask,
            header_fill=header_fill,
            header_font=header_font,
        )
        self._create_pisa_solo_mese_nfs_sheet(
            wb=wb,
            df_nfs_lookup=df_nfs_lookup,
            df_nfs_jan=df_nfs_jan,
            df_pisa_jan=df_pisa_jan,
            nfs_elet_mask=nfs_elet_mask,
            pisa_cart_mask=pisa_cart_mask,
            header_fill=header_fill,
            header_font=header_font,
        )

        wb.save(output_path)
        return summary

    def _filter_january_2025(self, df: pd.DataFrame, date_column: str) -> pd.DataFrame:
        if date_column not in df.columns:
            return df.iloc[0:0].copy()
        date_series = pd.to_datetime(df[date_column], errors="coerce")
        start = pd.Timestamp(year=2025, month=1, day=1)
        end = pd.Timestamp(year=2025, month=1, day=31)
        mask = date_series.between(start, end)
        return df[mask].copy()

    def _is_empty_sdi(self, series: pd.Series) -> pd.Series:
        normalized = series.astype(str).str.strip()
        normalized_lower = normalized.str.lower()
        zero_mask = normalized_lower.str.fullmatch(r"0+(\.0+)?").fillna(False)
        empty_mask = normalized_lower.isin(["", "nan", "none", "null"]) | zero_mask
        return empty_mask

    def _normalize_sdi(self, series: pd.Series) -> pd.Series:
        def normalize_value(value: Any) -> str:
            if pd.isna(value):
                return ""
            if isinstance(value, int):
                return str(value)
            if isinstance(value, float):
                if value.is_integer():
                    return str(int(value))
                return str(value).strip()
            text = str(value).strip()
            match = re.fullmatch(r"(\\d+)\\.0+", text)
            if match:
                return match.group(1)
            return text

        return series.map(normalize_value)

    def _create_fatture_da_verificare_sheet(
        self,
        wb: Workbook,
        df_nfs: pd.DataFrame,
        df_pisa: pd.DataFrame,
        header_fill: PatternFill,
        header_font: Font,
    ) -> None:
        ws = wb.create_sheet("Fatture da Verificare")

        headers = [
            "Identificativo SDI",
            "Esito",
            "NFS Ragione sociale",
            "NFS N.fatture",
            "NFS Datat reg.",
            "NFS Imponibile",
            "Pisa Creditore",
            "Pisa Numero fattura",
            "Pisa Data emissione",
            "Pisa Importo fattura",
            "Delta Numero",
            "Delta Importo",
        ]
        for col_idx, value in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=value)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        nfs_non_empty = df_nfs[~self._is_empty_sdi(df_nfs["_SDI_KEY"])].copy()
        pisa_non_empty = df_pisa[~self._is_empty_sdi(df_pisa["_SDI_KEY"])].copy()

        def build_side_agg(
            df: pd.DataFrame,
            amount_col: str,
            extra_cols: List[str],
            prefix: str,
        ) -> pd.DataFrame:
            df_local = df.copy()
            df_local["_SDI_KEY"] = df_local["_SDI_KEY"].astype(str).str.strip()
            grp = df_local.groupby("_SDI_KEY", dropna=False)

            out = pd.DataFrame(
                {
                    "Identificativo SDI": grp.size().index,
                    f"{prefix} Numero": grp.size().values,
                    f"{prefix} Importo": grp[amount_col].sum().values,
                }
            )

            for col in extra_cols:
                first_values = grp[col].apply(
                    lambda s: s.dropna().astype(str).str.strip().iloc[0] if len(s.dropna()) else ""
                )
                nunique_values = grp[col].apply(lambda s: s.dropna().astype(str).str.strip().nunique())
                values: List[str] = []
                for sdi_key in out["Identificativo SDI"]:
                    if int(nunique_values.loc[sdi_key]) > 1:
                        values.append("MULTIPLE")
                    else:
                        values.append(str(first_values.loc[sdi_key]))
                out[f"{prefix} {col}"] = values

            return out

        nfs_agg = build_side_agg(
            nfs_non_empty,
            amount_col="Imponibile",
            extra_cols=["Ragione sociale", "N.fatture", "Datat reg."],
            prefix="NFS",
        )
        pisa_agg = build_side_agg(
            pisa_non_empty,
            amount_col="Importo fattura",
            extra_cols=["Creditore", "Numero fattura", "Data emissione"],
            prefix="Pisa",
        )

        merged = nfs_agg.merge(pisa_agg, on="Identificativo SDI", how="outer")
        merged["NFS Numero"] = pd.to_numeric(merged["NFS Numero"], errors="coerce").fillna(0).astype(int)
        merged["Pisa Numero"] = pd.to_numeric(merged["Pisa Numero"], errors="coerce").fillna(0).astype(int)
        merged["NFS Importo"] = pd.to_numeric(merged["NFS Importo"], errors="coerce").fillna(0.0)
        merged["Pisa Importo"] = pd.to_numeric(merged["Pisa Importo"], errors="coerce").fillna(0.0)

        merged["Delta Numero"] = merged["NFS Numero"] - merged["Pisa Numero"]
        merged["Delta Importo"] = (merged["NFS Importo"] - merged["Pisa Importo"]).round(2)

        is_only_nfs = (merged["NFS Numero"] > 0) & (merged["Pisa Numero"] == 0)
        is_only_pisa = (merged["Pisa Numero"] > 0) & (merged["NFS Numero"] == 0)
        is_diff_amount = (merged["NFS Numero"] > 0) & (merged["Pisa Numero"] > 0) & (merged["Delta Importo"].abs() > 0.01)
        is_diff_count = (merged["NFS Numero"] > 0) & (merged["Pisa Numero"] > 0) & (merged["Delta Numero"] != 0)

        to_show = merged[is_only_nfs | is_only_pisa | is_diff_amount | is_diff_count].copy()

        def outcome(row: pd.Series) -> str:
            if row["NFS Numero"] > 0 and row["Pisa Numero"] == 0:
                return "Solo NFS"
            if row["Pisa Numero"] > 0 and row["NFS Numero"] == 0:
                return "Solo Pisa"
            if abs(float(row["Delta Importo"])) > 0.01:
                return "Importo diverso"
            if int(row["Delta Numero"]) != 0:
                return "Numero diverso"
            return ""

        to_show["Esito"] = to_show.apply(outcome, axis=1)
        to_show = to_show.sort_values(by=["Esito", "Identificativo SDI"], ascending=[True, True])

        money_format = "#,##0.00"
        date_format = "dd/mm/yyyy"
        row_idx = 2
        for _, row in to_show.iterrows():
            ws.cell(row=row_idx, column=1, value=row.get("Identificativo SDI", ""))
            ws.cell(row=row_idx, column=2, value=row.get("Esito", ""))
            ws.cell(row=row_idx, column=3, value=row.get("NFS Ragione sociale", ""))
            ws.cell(row=row_idx, column=4, value=row.get("NFS N.fatture", ""))
            nfs_date = row.get("NFS Datat reg.", "")
            pisa_date = row.get("Pisa Data emissione", "")
            c5 = ws.cell(row=row_idx, column=5, value=nfs_date if nfs_date != "" else None)
            if c5.value is not None:
                c5.number_format = date_format
            c6 = ws.cell(row=row_idx, column=6, value=float(row.get("NFS Importo", 0.0)))
            c6.number_format = money_format
            ws.cell(row=row_idx, column=7, value=row.get("Pisa Creditore", ""))
            ws.cell(row=row_idx, column=8, value=row.get("Pisa Numero fattura", ""))
            c9 = ws.cell(row=row_idx, column=9, value=pisa_date if pisa_date != "" else None)
            if c9.value is not None:
                c9.number_format = date_format
            c10 = ws.cell(row=row_idx, column=10, value=float(row.get("Pisa Importo", 0.0)))
            c10.number_format = money_format
            ws.cell(row=row_idx, column=11, value=int(row.get("Delta Numero", 0)))
            c12 = ws.cell(row=row_idx, column=12, value=float(row.get("Delta Importo", 0.0)))
            c12.number_format = money_format
            row_idx += 1

        ws.column_dimensions["A"].width = 22
        ws.column_dimensions["B"].width = 16
        ws.column_dimensions["C"].width = 26
        ws.column_dimensions["D"].width = 14
        ws.column_dimensions["E"].width = 14
        ws.column_dimensions["F"].width = 16
        ws.column_dimensions["G"].width = 26
        ws.column_dimensions["H"].width = 16
        ws.column_dimensions["I"].width = 16
        ws.column_dimensions["J"].width = 18
        ws.column_dimensions["K"].width = 14
        ws.column_dimensions["L"].width = 16

    def _create_differenze_elettroniche_sheet(
        self,
        wb: Workbook,
        df_nfs: pd.DataFrame,
        df_pisa: pd.DataFrame,
        nfs_elet_mask: pd.Series,
        pisa_cart_mask: pd.Series,
        header_fill: PatternFill,
        header_font: Font,
    ) -> None:
        ws = wb.create_sheet("Differenze Elettroniche SDI")

        headers = [
            "Sezione",
            "Identificativo SDI",
            "NFS Ragione sociale",
            "NFS N.fatture",
            "NFS Datat reg.",
            "NFS Prot.",
            "NFS Imponibile",
            "Pisa Creditore",
            "Pisa Numero fattura",
            "Pisa Data emissione",
            "Pisa Importo fattura",
        ]
        for col_idx, value in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=value)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        money_format = "#,##0.00"
        date_format = "dd/mm/yyyy"

        nfs_elet = df_nfs[nfs_elet_mask].copy()
        pisa_elet = df_pisa[~pisa_cart_mask].copy()

        nfs_elet_non_empty = nfs_elet[~self._is_empty_sdi(nfs_elet["_SDI_KEY"])].copy()
        pisa_elet_non_empty = pisa_elet[~self._is_empty_sdi(pisa_elet["_SDI_KEY"])].copy()

        nfs_keys = set(nfs_elet_non_empty["_SDI_KEY"].astype(str).str.strip())
        pisa_keys = set(pisa_elet_non_empty["_SDI_KEY"].astype(str).str.strip())

        only_pisa_keys = sorted(pisa_keys - nfs_keys)
        only_nfs_keys = sorted(nfs_keys - pisa_keys)

        nfs_elet_empty_sdi = nfs_elet[self._is_empty_sdi(nfs_elet["_SDI_KEY"])].copy()

        row_idx = 2

        def write_row(
            section: str,
            sdi: str,
            nfs_row: Optional[pd.Series],
            pisa_row: Optional[pd.Series],
        ) -> None:
            nonlocal row_idx
            ws.cell(row=row_idx, column=1, value=section)
            ws.cell(row=row_idx, column=2, value=sdi)

            if nfs_row is not None:
                ws.cell(row=row_idx, column=3, value=nfs_row.get("Ragione sociale", ""))
                ws.cell(row=row_idx, column=4, value=nfs_row.get("N.fatture", ""))
                c5 = ws.cell(row=row_idx, column=5, value=nfs_row.get("Datat reg.", None))
                if c5.value is not None:
                    c5.number_format = date_format
                ws.cell(row=row_idx, column=6, value=nfs_row.get("Prot.", ""))
                c7 = ws.cell(row=row_idx, column=7, value=float(nfs_row.get("Imponibile", 0.0)))
                c7.number_format = money_format
            else:
                for c in range(3, 8):
                    ws.cell(row=row_idx, column=c, value="")

            if pisa_row is not None:
                ws.cell(row=row_idx, column=8, value=pisa_row.get("Creditore", ""))
                ws.cell(row=row_idx, column=9, value=pisa_row.get("Numero fattura", ""))
                c10 = ws.cell(row=row_idx, column=10, value=pisa_row.get("Data emissione", None))
                if c10.value is not None:
                    c10.number_format = date_format
                c11 = ws.cell(row=row_idx, column=11, value=float(pisa_row.get("Importo fattura", 0.0)))
                c11.number_format = money_format
            else:
                for c in range(8, 12):
                    ws.cell(row=row_idx, column=c, value="")

            row_idx += 1

        nfs_first_by_key = (
            nfs_elet_non_empty.sort_values(by=["Datat reg.", "N.fatture"], na_position="last")
            .drop_duplicates(subset=["_SDI_KEY"], keep="first")
            .set_index("_SDI_KEY")
        )
        pisa_first_by_key = (
            pisa_elet_non_empty.sort_values(by=["Data emissione", "Numero fattura"], na_position="last")
            .drop_duplicates(subset=["_SDI_KEY"], keep="first")
            .set_index("_SDI_KEY")
        )

        for key in only_pisa_keys:
            write_row("Solo Pisa", key, None, pisa_first_by_key.loc[key])

        for key in only_nfs_keys:
            write_row("Solo NFS", key, nfs_first_by_key.loc[key], None)

        for _, r in nfs_elet_empty_sdi.sort_values(by=["Datat reg.", "N.fatture"], na_position="last").iterrows():
            write_row("NFS SDI vuoto", "", r, None)

        ws.column_dimensions["A"].width = 14
        ws.column_dimensions["B"].width = 22
        ws.column_dimensions["C"].width = 26
        ws.column_dimensions["D"].width = 14
        ws.column_dimensions["E"].width = 14
        ws.column_dimensions["F"].width = 12
        ws.column_dimensions["G"].width = 16
        ws.column_dimensions["H"].width = 26
        ws.column_dimensions["I"].width = 16
        ws.column_dimensions["J"].width = 16
        ws.column_dimensions["K"].width = 18

    def _create_differenze_sdi_univoche_sheet(
        self,
        wb: Workbook,
        df_nfs: pd.DataFrame,
        df_pisa: pd.DataFrame,
        nfs_elet_mask: pd.Series,
        pisa_cart_mask: pd.Series,
        header_fill: PatternFill,
        header_font: Font,
    ) -> None:
        ws = wb.create_sheet("Differenze SDI in Comune")

        headers = [
            "Identificativo SDI",
            "NFS Ragione sociale",
            "NFS N.fatture",
            "NFS Datat reg.",
            "NFS Imponibile",
            "Pisa Creditore",
            "Pisa Numero fattura",
            "Pisa Data emissione",
            "Pisa Importo fattura",
            "Delta Importo",
        ]
        for col_idx, value in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=value)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        money_format = "#,##0.00"
        date_format = "dd/mm/yyyy"

        nfs_elet = df_nfs[nfs_elet_mask].copy()
        pisa_elet = df_pisa[~pisa_cart_mask].copy()

        nfs_elet = nfs_elet[~self._is_empty_sdi(nfs_elet["_SDI_KEY"])].copy()
        pisa_elet = pisa_elet[~self._is_empty_sdi(pisa_elet["_SDI_KEY"])].copy()

        nfs_counts = nfs_elet["_SDI_KEY"].value_counts()
        pisa_counts = pisa_elet["_SDI_KEY"].value_counts()

        common_keys = set(nfs_counts.index) & set(pisa_counts.index)
        common_unique_keys = sorted(
            [k for k in common_keys if int(nfs_counts.get(k, 0)) == 1 and int(pisa_counts.get(k, 0)) == 1]
        )

        nfs_unique = nfs_elet.set_index("_SDI_KEY", drop=False)
        pisa_unique = pisa_elet.set_index("_SDI_KEY", drop=False)

        row_idx = 2
        for key in common_unique_keys:
            nfs_row = nfs_unique.loc[key]
            pisa_row = pisa_unique.loc[key]

            delta = round(float(nfs_row.get("Imponibile", 0.0)) - float(pisa_row.get("Importo fattura", 0.0)), 2)
            if abs(delta) <= 0.01:
                continue

            ws.cell(row=row_idx, column=1, value=key)
            ws.cell(row=row_idx, column=2, value=nfs_row.get("Ragione sociale", ""))
            ws.cell(row=row_idx, column=3, value=nfs_row.get("N.fatture", ""))
            c4 = ws.cell(row=row_idx, column=4, value=nfs_row.get("Datat reg.", None))
            if c4.value is not None:
                c4.number_format = date_format
            c5 = ws.cell(row=row_idx, column=5, value=float(nfs_row.get("Imponibile", 0.0)))
            c5.number_format = money_format

            ws.cell(row=row_idx, column=6, value=pisa_row.get("Creditore", ""))
            ws.cell(row=row_idx, column=7, value=pisa_row.get("Numero fattura", ""))
            c8 = ws.cell(row=row_idx, column=8, value=pisa_row.get("Data emissione", None))
            if c8.value is not None:
                c8.number_format = date_format
            c9 = ws.cell(row=row_idx, column=9, value=float(pisa_row.get("Importo fattura", 0.0)))
            c9.number_format = money_format

            c10 = ws.cell(row=row_idx, column=10, value=delta)
            c10.number_format = money_format
            row_idx += 1

        ws.column_dimensions["A"].width = 22
        ws.column_dimensions["B"].width = 26
        ws.column_dimensions["C"].width = 14
        ws.column_dimensions["D"].width = 14
        ws.column_dimensions["E"].width = 16
        ws.column_dimensions["F"].width = 26
        ws.column_dimensions["G"].width = 16
        ws.column_dimensions["H"].width = 16
        ws.column_dimensions["I"].width = 18
        ws.column_dimensions["J"].width = 16

    def _create_pisa_solo_mese_nfs_sheet(
        self,
        wb: Workbook,
        df_nfs_lookup: pd.DataFrame,
        df_nfs_jan: pd.DataFrame,
        df_pisa_jan: pd.DataFrame,
        nfs_elet_mask: pd.Series,
        pisa_cart_mask: pd.Series,
        header_fill: PatternFill,
        header_font: Font,
    ) -> None:
        ws = wb.create_sheet("Pisa Solo - Mese NFS")

        headers = [
            "Identificativo SDI",
            "Pisa Creditore",
            "Pisa Numero fattura",
            "Pisa Data emissione",
            "Pisa Importo fattura",
            "NFS Mesi trovati",
            "NFS Prima registrazione",
        ]
        for col_idx, value in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=value)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        money_format = "#,##0.00"
        date_format = "dd/mm/yyyy"

        pisa_elet = df_pisa_jan[~pisa_cart_mask].copy()
        pisa_elet = pisa_elet[~self._is_empty_sdi(pisa_elet["_SDI_KEY"])].copy()
        nfs_elet = df_nfs_jan[nfs_elet_mask].copy()
        nfs_elet = nfs_elet[~self._is_empty_sdi(nfs_elet["_SDI_KEY"])].copy()

        pisa_keys = set(pisa_elet["_SDI_KEY"].astype(str).str.strip())
        nfs_keys = set(nfs_elet["_SDI_KEY"].astype(str).str.strip())
        only_pisa_keys = sorted(pisa_keys - nfs_keys)

        pisa_first_by_key = (
            pisa_elet.sort_values(by=["Data emissione", "Numero fattura"], na_position="last")
            .drop_duplicates(subset=["_SDI_KEY"], keep="first")
            .set_index("_SDI_KEY")
        )

        df_nfs_lookup_non_empty = df_nfs_lookup[~self._is_empty_sdi(df_nfs_lookup["_SDI_KEY"])].copy()

        row_idx = 2
        for key in only_pisa_keys:
            pisa_row = pisa_first_by_key.loc[key]
            nfs_matches = df_nfs_lookup_non_empty[df_nfs_lookup_non_empty["_SDI_KEY"].astype(str).str.strip() == key].copy()
            nfs_dates = nfs_matches["Datat reg."]
            nfs_dates = pd.to_datetime(nfs_dates, errors="coerce").dropna()
            months = sorted(set(nfs_dates.dt.to_period("M").astype(str)))
            first_reg = nfs_dates.min() if len(nfs_dates) else None

            ws.cell(row=row_idx, column=1, value=key)
            ws.cell(row=row_idx, column=2, value=pisa_row.get("Creditore", ""))
            ws.cell(row=row_idx, column=3, value=pisa_row.get("Numero fattura", ""))

            c4 = ws.cell(row=row_idx, column=4, value=pisa_row.get("Data emissione", None))
            if c4.value is not None:
                c4.number_format = date_format
            c5 = ws.cell(row=row_idx, column=5, value=float(pisa_row.get("Importo fattura", 0.0)))
            c5.number_format = money_format

            ws.cell(row=row_idx, column=6, value=", ".join(months))
            c7 = ws.cell(row=row_idx, column=7, value=first_reg)
            if c7.value is not None:
                c7.number_format = date_format

            row_idx += 1

        ws.column_dimensions["A"].width = 22
        ws.column_dimensions["B"].width = 30
        ws.column_dimensions["C"].width = 18
        ws.column_dimensions["D"].width = 16
        ws.column_dimensions["E"].width = 18
        ws.column_dimensions["F"].width = 22
        ws.column_dimensions["G"].width = 20
