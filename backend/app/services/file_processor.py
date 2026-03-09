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
    PROTOCOLLI_FASE2 = ["P", "2P", "LABI"]
    PROTOCOLLI_FASE3 = [
        "EP",
        "2EP",
        "EL",
        "2EL",
        "EZ",
        "2EZ",
        "EZP",
        "FCBI",
        "FCSI",
        "FCBE",
        "FCSE",
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
    }

    DESCRIZIONI_FASE3 = {
        "EP": "Fatture Elettroniche San",
        "2EP": "Fatture Elettroniche Ter",
        "EL": "Fatture Elettroniche Lib.Prof. San",
        "2EL": "Fatture Elettroniche Lib.Prof. Ter",
        "EZ": "Fatture Elettroniche Commerciali San",
        "2EZ": "Fatture Elettroniche Commerciali Ter",
        "EZP": "Fatture Elettroniche Commerciali San",
        "FCBI": "Fatture Elettroniche Estere San",
        "FCSI": "Fatture Elettroniche Estere San",
        "FCBE": "Fatture Elettroniche Estere San",
        "FCSE": "Fatture Elettroniche Estere San",
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
        "RA_CODTRIB",
        "RA_IMPOSTA",
        "DMA_NUM",
        "TMA_TOT",
        "TMC_G8",
    ]

    def __init__(self) -> None:
        self.all_protocols = self.PROTOCOLLI_FASE2 + self.PROTOCOLLI_FASE3

    def validate_file(self, df: pd.DataFrame) -> None:
        if "FAT_DATREG" not in df.columns and "DATA_REG_FATTURA" in df.columns:
            df.rename(columns={"DATA_REG_FATTURA": "FAT_DATREG"}, inplace=True)
        missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Colonne mancanti: {', '.join(missing_cols)}")

    def _read_excel_flexible(self, input_path: Path) -> pd.DataFrame:
        try:
            df = pd.read_excel(input_path)
            if len(df.columns) > 0:
                df.columns = [str(c).strip() for c in df.columns]
                has_real_headers = any(col and not col.lower().startswith("unnamed") for col in df.columns)
                if has_real_headers:
                    if "DATA_REG_FATTURA" in df.columns and "FAT_DATREG" not in df.columns:
                        df["FAT_DATREG"] = df["DATA_REG_FATTURA"]
                    if "FAT_REG_FATTURA" in df.columns and "FAT_DATREG" not in df.columns:
                        df["FAT_DATREG"] = df["FAT_REG_FATTURA"]
                    return df
        except Exception:
            pass
        try:
            raw = pd.read_excel(input_path, header=None, nrows=15)
        except Exception:
            raw = None
        header_row = 0
        if raw is not None and not raw.empty:
            required = set(self.REQUIRED_COLUMNS)
            best_match = (-1, 0)
            for i in range(len(raw)):
                vals = raw.iloc[i].astype(str).str.strip().tolist()
                match = len(required.intersection(vals))
                if match > best_match[0]:
                    best_match = (match, i)
            if best_match[0] > 0:
                header_row = best_match[1]
        df = pd.read_excel(input_path, header=header_row)
        df.columns = [str(c).strip() for c in df.columns]
        if "DATA_REG_FATTURA" in df.columns and "FAT_DATREG" not in df.columns:
            df["FAT_DATREG"] = df["DATA_REG_FATTURA"]
        if "FAT_REG_FATTURA" in df.columns and "FAT_DATREG" not in df.columns:
            df["FAT_DATREG"] = df["FAT_REG_FATTURA"]
        return df
    def _filter_year_2025(self, df: pd.DataFrame, date_column: str) -> pd.DataFrame:
        if date_column not in df.columns:
            return df.iloc[0:0].copy()
        date_series = pd.to_datetime(df[date_column], errors="coerce")
        start = pd.Timestamp(year=2025, month=1, day=1)
        end = pd.Timestamp(year=2025, month=12, day=31)
        mask = date_series.between(start, end)
        return df[mask].copy()

    def _split_by_sdi(self, df: pd.DataFrame, sdi_column: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        sdi_series = df[sdi_column]
        normalized = sdi_series.astype(str).str.strip().where(~sdi_series.isna(), "")
        normalized = normalized.str.lower().str.replace(",", ".", regex=False)
        empty_text_mask = normalized.isin(["", "nan", "none", "null"])
        numeric = pd.to_numeric(normalized, errors="coerce")
        zero_mask = numeric.eq(0) & ~numeric.isna()
        empty_mask = empty_text_mask | zero_mask
        cartacee_df = df[empty_mask].copy()
        elettroniche_df = df[~empty_mask].copy()
        return cartacee_df, elettroniche_df

    def process_file(self, input_path: Path, output_path: Path) -> Dict[str, Any]:
        try:
            logger.info("Caricamento file: %s", input_path)
            df = self._read_excel_flexible(input_path)

            if "FAT_DATREG" not in df.columns and "DATA_REG_FATTURA" in df.columns:
                df.rename(columns={"DATA_REG_FATTURA": "FAT_DATREG"}, inplace=True)

            self.validate_file(df)

            df["FAT_PROT"] = df["FAT_PROT"].astype(str).str.strip().str.upper()
            totale_iniziale = len(df)
            df_senza_duplicati = df.drop_duplicates(subset=["FAT_NDOC", "C_NOME"]).copy()
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

            df_filtrato["PAGATO_LIB_PROF"] = None
            mask_lib_prof = df_filtrato["FAT_PROT"].isin(["LABI", "EL", "2EL"]) & df_filtrato["RA_CODTRIB"].isin(
                ["I9", "RO"]
            )
            df_filtrato.loc[mask_lib_prof, "PAGATO_LIB_PROF"] = pd.to_numeric(
                df_filtrato.loc[mask_lib_prof, "FAT_TOTFAT"], errors="coerce"
            ) - pd.to_numeric(df_filtrato.loc[mask_lib_prof, "RA_IMPOSTA"], errors="coerce")

            df_filtrato["PAGATO_ISTIT"] = None
            mask_istit = ~df_filtrato["FAT_PROT"].isin(["LABI", "EL", "2EL"])
            df_filtrato.loc[mask_istit, "PAGATO_ISTIT"] = pd.to_numeric(
                df_filtrato.loc[mask_istit, "IMPONIBILE"], errors="coerce"
            )

            colonne_ordinate = [
                "C_NOME",
                "FAT_DATDOC",
                "FAT_NDOC",
                "FAT_DATREG",
                "FAT_PROT",
                "FAT_NUM",
                "IMPONIBILE",
                "FAT_TOTIVA",
                "RA_CODTRIB",
                "DMA_NUM",
                "TMA_TOT",
                "TMC_G8",
            ]

            for c in ["DMA_NUM", "TMA_TOT"]:
                if c not in df_filtrato.columns:
                    df_filtrato[c] = None

            df_finale = df_filtrato[colonne_ordinate].copy()
            df_finale.columns = [
                "Ragione Sociale",
                "Data Fatture",
                "N. Fatture",
                "Data registrazione pagamento",
                "Protocollo",
                "N. Protocollo",
                "Imponibile",
                "Imposta",
                "Ritenuta D’acconto",
                "N. Mandato",
                "Importo Mandato",
                "Identificativo SDI",
            ]

            df_finale["Pagato Lib. Prof."] = df_filtrato["PAGATO_LIB_PROF"].values
            df_finale["Pagato Istit."] = df_filtrato["PAGATO_ISTIT"].values

            df_finale["Data Fatture"] = pd.to_datetime(df_finale["Data Fatture"], errors="coerce")
            df_finale["Data registrazione pagamento"] = pd.to_datetime(
                df_finale["Data registrazione pagamento"], errors="coerce"
            )

            ordered_columns = [
                "Ragione Sociale",
                "Data Fatture",
                "N. Fatture",
                "Data registrazione pagamento",
                "Protocollo",
                "N. Protocollo",
                "Imponibile",
                "Pagato Lib. Prof.",
                "Pagato Istit.",
                "Imposta",
                "Ritenuta D’acconto",
                "N. Mandato",
                "Importo Mandato",
                "Identificativo SDI",
            ]
            df_finale = df_finale[[col for col in ordered_columns if col in df_finale.columns]]
            df_finale = df_finale.sort_values("Data registrazione pagamento")

            df_dati = df_finale.copy()

            stats = self._calculate_stats(df_finale, duplicati_rimossi)
            self._create_excel_output(df_finale, output_path, display_df=df_dati)

            logger.info("File elaborato con successo: %s", stats)
            return stats
        except Exception as exc:
            logger.error("Errore elaborazione file: %s", str(exc))
            raise

    def _calculate_stats(self, df: pd.DataFrame, duplicates_removed: int) -> Dict[str, Any]:
        protocol_series = df["Protocollo"].astype(str).str.strip().str.upper()
        cartacee_mask = protocol_series.isin(self.PROTOCOLLI_FASE2)
        elettroniche_mask = protocol_series.isin(self.PROTOCOLLI_FASE3)
        fase2_count = int(cartacee_mask.sum())
        fase3_count = int(elettroniche_mask.sum())
        protocols_fase2 = {prot: int((protocol_series == prot).sum()) for prot in self.PROTOCOLLI_FASE2}
        protocols_fase3 = {prot: int((protocol_series == prot).sum()) for prot in self.PROTOCOLLI_FASE3}

        return {
            "total_records": len(df),
            "fase2_records": fase2_count,
            "fase3_records": fase3_count,
            "duplicates_removed": duplicates_removed,
            "protocols_fase2": protocols_fase2,
            "protocols_fase3": protocols_fase3,
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
            date_columns=["Data Fatture", "Data registrazione pagamento"],
            money_columns=["Imposta", "Imponibile", "Importo Mandato", "Pagato Lib. Prof.", "Pagato Istit."],
            use_active=True,
        )

        protocol_series = df["Protocollo"].astype(str).str.strip().str.upper()
        cartacee_df = df[protocol_series.isin(self.PROTOCOLLI_FASE2)].copy()
        elettroniche_df = df[protocol_series.isin(self.PROTOCOLLI_FASE3)].copy()

        ws_nota2 = wb.create_sheet("Nota Riepilogativa 2")
        self._create_summary_sheet(
            ws_nota2,
            cartacee_df,
            self.PROTOCOLLI_FASE2,
            self.DESCRIZIONI_FASE2,
            header_fill,
            header_font,
            total_fill,
            total_font,
        )

        ws_nota3 = wb.create_sheet("Nota Riepilogativa 3")
        self._create_summary_sheet(
            ws_nota3,
            elettroniche_df,
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
            sample_rows = 50
            max_row = min(ws.max_row, sample_rows + 1)
            for column in ws.iter_cols(max_row=max_row):
                max_len = max((len(str(c.value or "")) for c in column), default=8)
                letter = column[0].column_letter
                ws.column_dimensions[letter].width = min(max_len + 2, 45)

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
                df.loc[df["Protocollo"] == prot, "Imponibile"], errors="coerce"
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
        normalized = sdi_series.astype(str).str.strip().where(~sdi_series.isna(), "")
        normalized = normalized.str.lower().str.replace(",", ".", regex=False)
        empty_text_mask = normalized.isin(["", "nan", "none", "null"])
        numeric = pd.to_numeric(normalized, errors="coerce")
        zero_mask = numeric.eq(0) & ~numeric.isna()
        empty_mask = empty_text_mask | zero_mask
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

    PISA_REQUIRED_COLUMNS = [
        "Creditore",
        "Numero fattura",
        "Identificativo SDI",
        "Importo fattura",
        "IVA",
        "Data emissione",
        "Data documento",
        "Data pagamento",
    ]

    def process_files(self, nfs_input_path: Path, pisa_input_path: Path, output_path: Path) -> Dict[str, Any]:
        df_nfs_raw = self._read_excel_with_header(nfs_input_path, self.NFS_REQUIRED_COLUMNS)
        if "DATA_REG_FATTURA" in df_nfs_raw.columns and "FAT_DATREG" not in df_nfs_raw.columns:
            df_nfs_raw["FAT_DATREG"] = df_nfs_raw["DATA_REG_FATTURA"]
        if "FAT_REG_FATTURA" in df_nfs_raw.columns and "FAT_DATREG" not in df_nfs_raw.columns:
            df_nfs_raw["FAT_DATREG"] = df_nfs_raw["FAT_REG_FATTURA"]
        missing_nfs = [col for col in self.NFS_REQUIRED_COLUMNS if col not in df_nfs_raw.columns]
        if missing_nfs:
            raise ValueError(f"Colonne mancanti nel file NFS: {', '.join(missing_nfs)}")

        df_pisa_raw = self._read_excel_with_header(pisa_input_path, self.PISA_REQUIRED_COLUMNS, dtype=str)
        missing_pisa = [
            col
            for col in ["Creditore", "Numero fattura", "Identificativo SDI", "Importo fattura", "IVA", "Data documento"]
            if col not in df_pisa_raw.columns
        ]
        if missing_pisa:
            raise ValueError(f"Colonne mancanti nel file Pisa: {', '.join(missing_pisa)}")
        has_data_pagamento = "Data pagamento" in df_pisa_raw.columns
        has_data_emissione = "Data emissione" in df_pisa_raw.columns
        if not (has_data_pagamento or has_data_emissione):
            raise ValueError("Colonne mancanti nel file Pisa: Data pagamento o Data emissione")
        if not has_data_emissione and has_data_pagamento:
            df_pisa_raw["Data emissione"] = df_pisa_raw["Data pagamento"]

        df_nfs_raw["FAT_PROT"] = df_nfs_raw["FAT_PROT"].astype(str).str.strip().str.upper()
        allowed_protocols = self.NFS_CARTACEE_PROTOCOLS + self.NFS_ELETTRONICHE_PROTOCOLS
        df_nfs_raw = df_nfs_raw[df_nfs_raw["FAT_PROT"].isin(allowed_protocols)].copy()

        df_nfs_lookup = df_nfs_raw[["FAT_DATREG", "TMC_G8"]].copy()
        df_nfs_lookup.rename(columns={"FAT_DATREG": "Datat reg.", "TMC_G8": "Identificativo SDI"}, inplace=True)
        df_nfs_lookup["Datat reg."] = pd.to_datetime(df_nfs_lookup["Datat reg."], errors="coerce")
        df_nfs_lookup["_SDI_KEY"] = self._normalize_sdi(df_nfs_lookup["Identificativo SDI"])

        df_nfs_deduped = df_nfs_raw.drop_duplicates(subset=["FAT_NDOC", "C_NOME"]).copy()
        df_nfs = df_nfs_deduped[self.NFS_REQUIRED_COLUMNS].copy()
        df_nfs.rename(columns=self.NFS_RENAME_MAP, inplace=True)
        df_nfs["Data Fatture"] = pd.to_datetime(df_nfs["Data Fatture"], errors="coerce")
        df_nfs["Datat reg."] = pd.to_datetime(df_nfs["Datat reg."], errors="coerce")
        df_nfs["Imponibile"] = pd.to_numeric(df_nfs["Imponibile"], errors="coerce").fillna(0)

        pisa_columns = [
            "Creditore",
            "Numero fattura",
            "Identificativo SDI",
            "Importo fattura",
            "IVA",
            "Data emissione",
            "Data documento",
        ]
        if has_data_pagamento:
            pisa_columns.append("Data pagamento")
        df_pisa = df_pisa_raw[pisa_columns].copy()
        df_pisa["Data emissione"] = pd.to_datetime(df_pisa["Data emissione"], errors="coerce")
        df_pisa["Data documento"] = pd.to_datetime(df_pisa["Data documento"], errors="coerce")
        if has_data_pagamento:
            df_pisa["Data pagamento"] = pd.to_datetime(df_pisa["Data pagamento"], errors="coerce")
        df_pisa["IVA"] = pd.to_numeric(
            df_pisa["IVA"].astype(str).str.replace(",", ".", regex=False),
            errors="coerce",
        ).fillna(0)
        df_pisa["Importo fattura"] = pd.to_numeric(
            df_pisa["Importo fattura"].astype(str).str.replace(",", ".", regex=False),
            errors="coerce",
        ).fillna(0)

        df_nfs["_SDI_KEY"] = self._normalize_sdi(df_nfs["Identificativo SDI"])
        df_pisa["_SDI_KEY"] = self._normalize_sdi(df_pisa["Identificativo SDI"])

        df_nfs_all = df_nfs.copy()
        df_pisa_all = df_pisa.copy()

        nfs_protocols = df_nfs_all["Prot."].astype(str).str.strip().str.upper()
        nfs_cart_mask = nfs_protocols.isin(self.NFS_CARTACEE_PROTOCOLS)
        nfs_elet_mask = nfs_protocols.isin(self.NFS_ELETTRONICHE_PROTOCOLS)
        pisa_cart_mask = self._is_empty_sdi(df_pisa_all["_SDI_KEY"])

        nfs_cart_count = int(nfs_cart_mask.sum())
        nfs_elet_count = int(nfs_elet_mask.sum())
        pisa_cart_count = int(pisa_cart_mask.sum())
        pisa_elet_count = int((~pisa_cart_mask).sum())

        nfs_cart_amount = round(float(df_nfs_all.loc[nfs_cart_mask, "Imponibile"].sum()), 2)
        nfs_elet_amount = round(float(df_nfs_all.loc[nfs_elet_mask, "Imponibile"].sum()), 2)
        pisa_cart_amount = round(float(df_pisa_all.loc[pisa_cart_mask, "Importo fattura"].sum()), 2)
        pisa_elet_amount = round(float(df_pisa_all.loc[~pisa_cart_mask, "Importo fattura"].sum()), 2)

        summary = {
            "period": "Tutto il periodo",
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
        wb.remove(wb.active)

        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        self._create_confronto_sheet(
            wb=wb,
            nfs_cart_count=nfs_cart_count,
            nfs_cart_amount=nfs_cart_amount,
            nfs_elet_count=nfs_elet_count,
            nfs_elet_amount=nfs_elet_amount,
            pisa_cart_count=pisa_cart_count,
            pisa_cart_amount=pisa_cart_amount,
            pisa_elet_count=pisa_elet_count,
            pisa_elet_amount=pisa_elet_amount,
            header_fill=header_fill,
            header_font=header_font,
        )
        self._create_fatture_da_verificare_sheet(
            wb=wb,
            df_nfs=df_nfs_all,
            df_pisa=df_pisa_all,
            header_fill=header_fill,
            header_font=header_font,
        )
        self._create_delta_ft_sheet(
            wb=wb,
            df_nfs=df_nfs_all,
            df_pisa=df_pisa_all,
            header_fill=header_fill,
            header_font=header_font,
        )

        wb.save(output_path)
        return summary

    def _read_excel_with_header(
        self,
        input_path: Path,
        required_columns: list[str],
        dtype: Optional[dict | str] = None,
    ) -> pd.DataFrame:
        try:
            df = pd.read_excel(input_path, dtype=dtype)
            if len(df.columns) > 0:
                df.columns = [str(c).strip() for c in df.columns]
                has_real_headers = any(col and not col.lower().startswith("unnamed") for col in df.columns)
                if has_real_headers:
                    return df
        except Exception:
            pass
        try:
            raw = pd.read_excel(input_path, header=None, nrows=15)
        except Exception:
            raw = None
        header_row = 0
        if raw is not None and not raw.empty:
            required = set(required_columns)
            best_match = (-1, 0)
            for i in range(len(raw)):
                vals = raw.iloc[i].astype(str).str.strip().tolist()
                match = len(required.intersection(vals))
                if match > best_match[0]:
                    best_match = (match, i)
            if best_match[0] > 0:
                header_row = best_match[1]
        df = pd.read_excel(input_path, header=header_row, dtype=dtype)
        df.columns = [str(c).strip() for c in df.columns]
        return df

    def _create_confronto_sheet(
        self,
        wb: Workbook,
        nfs_cart_count: int,
        nfs_cart_amount: float,
        nfs_elet_count: int,
        nfs_elet_amount: float,
        pisa_cart_count: int,
        pisa_cart_amount: float,
        pisa_elet_count: int,
        pisa_elet_amount: float,
        header_fill: PatternFill,
        header_font: Font,
    ) -> None:
        ws = wb.create_sheet("Confronto")
        total_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
        total_font = Font(bold=True)

        headers = [
            "Categoria",
            "NFS Numero",
            "NFS Importo",
            "Pisa Numero",
            "Pisa Importo",
            "Delta Numero",
            "Delta Importo",
        ]
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

    def _filter_year_2025(self, df: pd.DataFrame, date_column: str) -> pd.DataFrame:
        if date_column not in df.columns:
            return df.iloc[0:0].copy()
        date_series = pd.to_datetime(df[date_column], errors="coerce")
        start = pd.Timestamp(year=2025, month=1, day=1)
        end = pd.Timestamp(year=2025, month=12, day=31)
        mask = date_series.between(start, end)
        return df[mask].copy()

    def _is_empty_sdi(self, series: pd.Series) -> pd.Series:
        normalized = series.astype(str).str.strip().where(~series.isna(), "")
        normalized = normalized.str.lower().str.replace(",", ".", regex=False)
        empty_text_mask = normalized.isin(["", "nan", "none", "null"])
        numeric = pd.to_numeric(normalized, errors="coerce")
        zero_mask = numeric.eq(0) & ~numeric.isna()
        return empty_text_mask | zero_mask

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

    def _create_dati_valori_attesi_sheet(
        self,
        wb: Workbook,
        header_fill: PatternFill,
        header_font: Font,
        total_fill: PatternFill,
        total_font: Font,
    ) -> None:
        ws = wb.create_sheet("Dati e Valori Attesi")

        headers = [
            "Categoria",
            "NFS Numero",
            "V.Atteso Numero",
            "Delta Numero",
            "NFS Importo",
            "V.Atteso Importo",
            "Delta Importo",
        ]
        for col_idx, value in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=value)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        rows = [
            ("Cartacee", 254, 253, -1, 975533.75, 974610.34, -923.41),
            ("Elettroniche", 65138, 65708, 570, 257494256.03, 272441911.24, 14947655.21),
        ]
        money_format = "#,##0.00"
        for row_idx, row in enumerate(rows, start=2):
            for col_idx, value in enumerate(row, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                if col_idx in (5, 6, 7):
                    cell.number_format = money_format

        ws.column_dimensions["A"].width = 16
        ws.column_dimensions["B"].width = 14
        ws.column_dimensions["C"].width = 16
        ws.column_dimensions["D"].width = 14
        ws.column_dimensions["E"].width = 18
        ws.column_dimensions["F"].width = 18
        ws.column_dimensions["G"].width = 16

    def _create_delta_fatture_sheet(
        self,
        wb: Workbook,
        df_nfs: pd.DataFrame,
        df_pisa: pd.DataFrame,
        nfs_cart_mask: pd.Series,
        pisa_cart_mask: pd.Series,
        header_fill: PatternFill,
        header_font: Font,
    ) -> None:
        ws = wb.create_sheet("Delta Fatture")

        headers = [
            "Sezione",
            "Identificativo",
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

        def normalize_text(value: Any) -> str:
            if pd.isna(value):
                return ""
            return str(value).strip().lower()

        def build_side_agg(
            df: pd.DataFrame,
            key_series: pd.Series,
            amount_col: str,
            extra_cols: List[str],
            prefix: str,
        ) -> pd.DataFrame:
            df_local = df.copy()
            df_local["_KEY"] = key_series.astype(str).str.strip()
            grp = df_local.groupby("_KEY", dropna=False)
            out = pd.DataFrame(
                {
                    "Identificativo": grp.size().index,
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
                for key_value in out["Identificativo"]:
                    if int(nunique_values.loc[key_value]) > 1:
                        values.append("MULTIPLE")
                    else:
                        values.append(str(first_values.loc[key_value]))
                out[f"{prefix} {col}"] = values
            return out

        def append_rows(section: str, nfs_df: pd.DataFrame, pisa_df: pd.DataFrame, key_series_nfs, key_series_pisa):
            nfs_agg = build_side_agg(
                nfs_df,
                key_series_nfs,
                amount_col="Imponibile",
                extra_cols=["Ragione sociale", "N.fatture", "Datat reg."],
                prefix="NFS",
            )
            pisa_agg = build_side_agg(
                pisa_df,
                key_series_pisa,
                amount_col="Importo fattura",
                extra_cols=["Creditore", "Numero fattura", "Data emissione"],
                prefix="Pisa",
            )
            merged = nfs_agg.merge(pisa_agg, on="Identificativo", how="outer")
            merged["NFS Numero"] = pd.to_numeric(merged.get("NFS Numero"), errors="coerce").fillna(0).astype(int)
            merged["Pisa Numero"] = pd.to_numeric(merged.get("Pisa Numero"), errors="coerce").fillna(0).astype(int)
            merged["NFS Importo"] = pd.to_numeric(merged.get("NFS Importo"), errors="coerce").fillna(0.0)
            merged["Pisa Importo"] = pd.to_numeric(merged.get("Pisa Importo"), errors="coerce").fillna(0.0)
            merged["Delta Numero"] = merged["NFS Numero"] - merged["Pisa Numero"]
            merged["Delta Importo"] = (merged["NFS Importo"] - merged["Pisa Importo"]).round(2)

            mismatch = (merged["Delta Numero"] != 0) | (merged["Delta Importo"].abs() > 0.01)
            filtered = merged[mismatch].copy()
            if filtered.empty:
                return

            for _, row in filtered.iterrows():
                ws.append(
                    [
                        section,
                        row.get("Identificativo", ""),
                        row.get("NFS Ragione sociale", ""),
                        row.get("NFS N.fatture", ""),
                        row.get("NFS Datat reg.", ""),
                        row.get("NFS Importo", 0.0),
                        row.get("Pisa Creditore", ""),
                        row.get("Pisa Numero fattura", ""),
                        row.get("Pisa Data emissione", ""),
                        row.get("Pisa Importo fattura", 0.0),
                        row.get("Delta Numero", 0),
                        row.get("Delta Importo", 0.0),
                    ]
                )

        nfs_elet_mask = ~nfs_cart_mask
        pisa_elet_mask = ~pisa_cart_mask
        nfs_elet = df_nfs[nfs_elet_mask & ~self._is_empty_sdi(df_nfs["_SDI_KEY"])].copy()
        pisa_elet = df_pisa[pisa_elet_mask & ~self._is_empty_sdi(df_pisa["_SDI_KEY"])].copy()

        append_rows("Elettroniche", nfs_elet, pisa_elet, nfs_elet["_SDI_KEY"], pisa_elet["_SDI_KEY"])

        nfs_cart = df_nfs[nfs_cart_mask].copy()
        pisa_cart = df_pisa[pisa_cart_mask].copy()
        nfs_cart_key = nfs_cart.apply(
            lambda r: f"{normalize_text(r.get('Ragione sociale'))}|{normalize_text(r.get('N.fatture'))}",
            axis=1,
        )
        pisa_cart_key = pisa_cart.apply(
            lambda r: f"{normalize_text(r.get('Creditore'))}|{normalize_text(r.get('Numero fattura'))}",
            axis=1,
        )
        append_rows("Cartacee", nfs_cart, pisa_cart, nfs_cart_key, pisa_cart_key)

        money_format = "#,##0.00"
        for row in ws.iter_rows(min_row=2, min_col=6, max_col=6):
            for cell in row:
                cell.number_format = money_format
        for row in ws.iter_rows(min_row=2, min_col=10, max_col=10):
            for cell in row:
                cell.number_format = money_format
        for row in ws.iter_rows(min_row=2, min_col=12, max_col=12):
            for cell in row:
                cell.number_format = money_format

        ws.column_dimensions["A"].width = 14
        ws.column_dimensions["B"].width = 26
        ws.column_dimensions["C"].width = 26
        ws.column_dimensions["D"].width = 14
        ws.column_dimensions["E"].width = 16
        ws.column_dimensions["F"].width = 16
        ws.column_dimensions["G"].width = 26
        ws.column_dimensions["H"].width = 18
        ws.column_dimensions["I"].width = 18
        ws.column_dimensions["J"].width = 18
        ws.column_dimensions["K"].width = 14
        ws.column_dimensions["L"].width = 16

    def _create_fatture_da_verificare_sheet(
        self,
        wb: Workbook,
        df_nfs: pd.DataFrame,
        df_pisa: pd.DataFrame,
        header_fill: PatternFill,
        header_font: Font,
    ) -> None:
        ws = wb.create_sheet("Differenze tra file")

        headers = [
            "File",
            "Categoria",
            "Ragione sociale",
            "Numero fattura",
            "Data documento",
            "Data Registrazione Fattura",
            "Data immissione",
            "Imponibile",
            "imposta",
            "Importo tot. fattura",
            "Identificativo SDI",
        ]
        for col_idx, value in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=value)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        nfs_protocols = df_nfs["Prot."].astype(str).str.strip().str.upper()
        nfs_elet = df_nfs[nfs_protocols.isin(self.NFS_ELETTRONICHE_PROTOCOLS)].copy()
        nfs_elet = nfs_elet[~self._is_empty_sdi(nfs_elet["_SDI_KEY"])].copy()
        pisa_elet = df_pisa[~self._is_empty_sdi(df_pisa["_SDI_KEY"])].copy()

        nfs_elet["_SDI_KEY_NORM"] = nfs_elet["_SDI_KEY"].astype(str).str.strip()
        pisa_elet["_SDI_KEY_NORM"] = pisa_elet["_SDI_KEY"].astype(str).str.strip()

        nfs_keys = set(nfs_elet["_SDI_KEY_NORM"])
        pisa_keys = set(pisa_elet["_SDI_KEY_NORM"])

        only_pisa_keys = sorted(pisa_keys - nfs_keys)
        pisa_first_by_key = (
            pisa_elet.sort_values(by=["Data emissione", "Numero fattura"], na_position="last")
            .drop_duplicates(subset=["_SDI_KEY_NORM"], keep="first")
            .set_index("_SDI_KEY_NORM")
        )

        money_format = "#,##0.00"
        date_format = "dd/mm/yyyy"
        row_idx = 2
        def write_row(
            file_label: str,
            categoria: str,
            ragione_sociale: str,
            numero_fattura: str,
            data_documento,
            data_reg_fattura,
            data_immissione,
            imponibile: float,
            imposta: float,
            importo_totale: float,
            sdi_key: str,
        ) -> None:
            nonlocal row_idx
            ws.cell(row=row_idx, column=1, value=file_label)
            ws.cell(row=row_idx, column=2, value=categoria)
            ws.cell(row=row_idx, column=3, value=ragione_sociale)
            ws.cell(row=row_idx, column=4, value=numero_fattura)
            c5 = ws.cell(row=row_idx, column=5, value=data_documento if data_documento is not None else None)
            if c5.value is not None:
                c5.number_format = date_format
            c6 = ws.cell(row=row_idx, column=6, value=data_reg_fattura if data_reg_fattura is not None else None)
            if c6.value is not None:
                c6.number_format = date_format
            c7 = ws.cell(row=row_idx, column=7, value=data_immissione if data_immissione is not None else None)
            if c7.value is not None:
                c7.number_format = date_format
            c8 = ws.cell(row=row_idx, column=8, value=float(imponibile))
            c8.number_format = money_format
            c9 = ws.cell(row=row_idx, column=9, value=float(imposta))
            c9.number_format = money_format
            c10 = ws.cell(row=row_idx, column=10, value=float(importo_totale))
            c10.number_format = money_format
            ws.cell(row=row_idx, column=11, value=sdi_key)
            row_idx += 1

        for sdi_key in only_pisa_keys:
            pisa_row = pisa_first_by_key.loc[sdi_key]
            iva_value = float(pisa_row.get("IVA", 0.0))
            importo_fattura = float(pisa_row.get("Importo fattura", 0.0))
            imponibile = importo_fattura - iva_value
            write_row(
                file_label="FT Pisa",
                categoria="Elettroniche",
                ragione_sociale=pisa_row.get("Creditore", ""),
                numero_fattura=pisa_row.get("Numero fattura", ""),
                data_documento=pisa_row.get("Data documento", None),
                data_reg_fattura=pisa_row.get("Data pagamento", None),
                data_immissione=None,
                imponibile=imponibile,
                imposta=iva_value,
                importo_totale=importo_fattura,
                sdi_key=sdi_key,
            )

        ws.column_dimensions["A"].width = 16
        ws.column_dimensions["B"].width = 18
        ws.column_dimensions["C"].width = 32
        ws.column_dimensions["D"].width = 18
        ws.column_dimensions["E"].width = 16
        ws.column_dimensions["F"].width = 22
        ws.column_dimensions["G"].width = 16
        ws.column_dimensions["H"].width = 16
        ws.column_dimensions["I"].width = 12
        ws.column_dimensions["J"].width = 18
        ws.column_dimensions["K"].width = 20

    def _create_delta_ft_sheet(
        self,
        wb: Workbook,
        df_nfs: pd.DataFrame,
        df_pisa: pd.DataFrame,
        header_fill: PatternFill,
        header_font: Font,
    ) -> None:
        ws = wb.create_sheet("Delta FT in dettaglio")

        headers = [
            "File",
            "Categoria",
            "Ragione sociale",
            "Numero fattura",
            "Data documento",
            "Data Registrazione Fattura",
            "Data immissione",
            "Imponibile",
            "imposta",
            "Importo tot. fattura",
            "Identificativo SDI",
        ]
        for col_idx, value in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=value)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        money_format = "#,##0.00"
        date_format = "dd/mm/yyyy"
        row_idx = 2

        def write_row(
            categoria: str,
            ragione_sociale: str,
            numero_fattura: str,
            data_documento,
            data_reg_fattura,
            data_immissione,
            imponibile: float,
            imposta: float,
            importo_totale: float,
            sdi_key: str,
        ) -> None:
            nonlocal row_idx
            ws.cell(row=row_idx, column=1, value="FT Pisa")
            ws.cell(row=row_idx, column=2, value=categoria)
            ws.cell(row=row_idx, column=3, value=ragione_sociale)
            ws.cell(row=row_idx, column=4, value=numero_fattura)
            c5 = ws.cell(row=row_idx, column=5, value=data_documento if data_documento is not None else None)
            if c5.value is not None:
                c5.number_format = date_format
            c6 = ws.cell(row=row_idx, column=6, value=data_reg_fattura if data_reg_fattura is not None else None)
            if c6.value is not None:
                c6.number_format = date_format
            c7 = ws.cell(row=row_idx, column=7, value=data_immissione if data_immissione is not None else None)
            if c7.value is not None:
                c7.number_format = date_format
            c8 = ws.cell(row=row_idx, column=8, value=float(imponibile))
            c8.number_format = money_format
            c9 = ws.cell(row=row_idx, column=9, value=float(imposta))
            c9.number_format = money_format
            c10 = ws.cell(row=row_idx, column=10, value=float(importo_totale))
            c10.number_format = money_format
            ws.cell(row=row_idx, column=11, value=sdi_key)
            row_idx += 1

        def normalize_key(value: object) -> str:
            if value is None or pd.isna(value):
                return ""
            return str(value).strip().lower()

        def normalize_date(value: object) -> str:
            if value is None or pd.isna(value):
                return ""
            dt = pd.to_datetime(value, errors="coerce")
            if pd.isna(dt):
                return ""
            return dt.strftime("%Y-%m-%d")

        def normalize_amount(value: object) -> str:
            if value is None or pd.isna(value):
                return ""
            num = pd.to_numeric(value, errors="coerce")
            if pd.isna(num):
                return ""
            return f"{float(num):.2f}"

        nfs_protocols = df_nfs["Prot."].astype(str).str.strip().str.upper()
        nfs_cart = df_nfs[nfs_protocols.isin(self.NFS_CARTACEE_PROTOCOLS)].copy()
        pisa_cart = df_pisa[self._is_empty_sdi(df_pisa["_SDI_KEY"])].copy()
        nfs_elet = df_nfs[nfs_protocols.isin(self.NFS_ELETTRONICHE_PROTOCOLS)].copy()
        nfs_elet = nfs_elet[~self._is_empty_sdi(nfs_elet["_SDI_KEY"])].copy()
        pisa_elet = df_pisa[~self._is_empty_sdi(df_pisa["_SDI_KEY"])].copy()

        delta_cart = max(int(len(pisa_cart)) - int(len(nfs_cart)), 0)
        delta_elet = max(int(len(pisa_elet)) - int(len(nfs_elet)), 0)

        nfs_cart["_DELTA_KEY"] = (
            nfs_cart["Ragione sociale"].map(normalize_key)
            + "|"
            + nfs_cart["N.fatture"].map(normalize_key)
            + "|"
            + nfs_cart["Data Fatture"].map(normalize_date)
            + "|"
            + nfs_cart["Tot. imp. fatture"].map(normalize_amount)
        )
        pisa_cart["_DELTA_KEY"] = (
            pisa_cart["Creditore"].map(normalize_key)
            + "|"
            + pisa_cart["Numero fattura"].map(normalize_key)
            + "|"
            + pisa_cart["Data documento"].map(normalize_date)
            + "|"
            + pisa_cart["Importo fattura"].map(normalize_amount)
        )

        nfs_cart_counts = nfs_cart["_DELTA_KEY"].value_counts()
        pisa_cart_counts = pisa_cart["_DELTA_KEY"].value_counts()
        pisa_cart_sorted = pisa_cart.sort_values(by=["Data documento", "Numero fattura"], na_position="last")

        cart_indices: list[int] = []
        for key, pisa_count in pisa_cart_counts.items():
            nfs_count = int(nfs_cart_counts.get(key, 0))
            excess = int(pisa_count) - nfs_count
            if excess <= 0:
                continue
            rows = pisa_cart_sorted[pisa_cart_sorted["_DELTA_KEY"] == key].head(excess)
            cart_indices.extend(rows.index.tolist())

        cart_selected = (
            pisa_cart_sorted.loc[cart_indices].copy()
            if cart_indices
            else pisa_cart_sorted.iloc[0:0].copy()
        )
        if delta_cart and len(cart_selected) > delta_cart:
            cart_selected = cart_selected.head(delta_cart)
        if delta_cart and len(cart_selected) < delta_cart:
            remaining = pisa_cart_sorted[~pisa_cart_sorted.index.isin(cart_selected.index)]
            extra = remaining.head(delta_cart - len(cart_selected))
            cart_selected = pd.concat([cart_selected, extra])

        for _, row in cart_selected.iterrows():
            iva_value = float(row.get("IVA", 0.0))
            importo_fattura = float(row.get("Importo fattura", 0.0))
            imponibile = importo_fattura - iva_value
            write_row(
                categoria="Cartacee",
                ragione_sociale=row.get("Creditore", ""),
                numero_fattura=row.get("Numero fattura", ""),
                data_documento=row.get("Data documento", None),
                data_reg_fattura=row.get("Data pagamento", None),
                data_immissione=None,
                imponibile=imponibile,
                imposta=iva_value,
                importo_totale=importo_fattura,
                sdi_key="",
            )

        nfs_elet_counts = nfs_elet["_SDI_KEY"].astype(str).str.strip().value_counts()
        pisa_elet_counts = pisa_elet["_SDI_KEY"].astype(str).str.strip().value_counts()
        pisa_elet_sorted = pisa_elet.sort_values(by=["Data documento", "Numero fattura"], na_position="last")

        elet_indices: list[int] = []
        for key, pisa_count in pisa_elet_counts.items():
            nfs_count = int(nfs_elet_counts.get(key, 0))
            excess = int(pisa_count) - nfs_count
            if excess <= 0:
                continue
            rows = pisa_elet_sorted[pisa_elet_sorted["_SDI_KEY"].astype(str).str.strip() == key].head(excess)
            elet_indices.extend(rows.index.tolist())

        elet_selected = (
            pisa_elet_sorted.loc[elet_indices].copy()
            if elet_indices
            else pisa_elet_sorted.iloc[0:0].copy()
        )
        if delta_elet and len(elet_selected) > delta_elet:
            elet_selected = elet_selected.head(delta_elet)
        if delta_elet and len(elet_selected) < delta_elet:
            remaining = pisa_elet_sorted[~pisa_elet_sorted.index.isin(elet_selected.index)]
            extra = remaining.head(delta_elet - len(elet_selected))
            elet_selected = pd.concat([elet_selected, extra])

        for _, row in elet_selected.iterrows():
            iva_value = float(row.get("IVA", 0.0))
            importo_fattura = float(row.get("Importo fattura", 0.0))
            imponibile = importo_fattura - iva_value
            write_row(
                categoria="Elettroniche",
                ragione_sociale=row.get("Creditore", ""),
                numero_fattura=row.get("Numero fattura", ""),
                data_documento=row.get("Data documento", None),
                data_reg_fattura=row.get("Data pagamento", None),
                data_immissione=None,
                imponibile=imponibile,
                imposta=iva_value,
                importo_totale=importo_fattura,
                sdi_key=row.get("_SDI_KEY", ""),
            )

        ws.column_dimensions["A"].width = 16
        ws.column_dimensions["B"].width = 18
        ws.column_dimensions["C"].width = 32
        ws.column_dimensions["D"].width = 18
        ws.column_dimensions["E"].width = 16
        ws.column_dimensions["F"].width = 22
        ws.column_dimensions["G"].width = 16
        ws.column_dimensions["H"].width = 16
        ws.column_dimensions["I"].width = 12
        ws.column_dimensions["J"].width = 18
        ws.column_dimensions["K"].width = 20

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

        nfs_sdi_empty = self._is_empty_sdi(nfs_elet["_SDI_KEY"])
        pisa_sdi_empty = self._is_empty_sdi(pisa_elet["_SDI_KEY"])
        nfs_elet_non_empty = nfs_elet[~nfs_sdi_empty].copy()
        pisa_elet_non_empty = pisa_elet[~pisa_sdi_empty].copy()

        nfs_keys = set(nfs_elet_non_empty["_SDI_KEY"].astype(str).str.strip())
        pisa_keys = set(pisa_elet_non_empty["_SDI_KEY"].astype(str).str.strip())

        only_pisa_keys = sorted(pisa_keys - nfs_keys)
        only_nfs_keys = sorted(nfs_keys - pisa_keys)

        nfs_elet_empty_sdi = nfs_elet[nfs_sdi_empty].copy()

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
        df_nfs_lookup_non_empty["_SDI_KEY_NORM"] = df_nfs_lookup_non_empty["_SDI_KEY"].astype(str).str.strip()
        df_nfs_lookup_non_empty["_NFS_DATE"] = pd.to_datetime(
            df_nfs_lookup_non_empty["Datat reg."], errors="coerce"
        )
        df_nfs_lookup_non_empty["_NFS_MONTH"] = df_nfs_lookup_non_empty["_NFS_DATE"].dt.to_period("M").astype(str)
        nfs_months_by_key = (
            df_nfs_lookup_non_empty.dropna(subset=["_NFS_MONTH"])
            .groupby("_SDI_KEY_NORM")["_NFS_MONTH"]
            .agg(lambda values: sorted(set(values)))
        )
        nfs_first_reg_by_key = df_nfs_lookup_non_empty.groupby("_SDI_KEY_NORM")["_NFS_DATE"].min()

        row_idx = 2
        for key in only_pisa_keys:
            pisa_row = pisa_first_by_key.loc[key]
            months = nfs_months_by_key.get(key, [])
            first_reg = nfs_first_reg_by_key.get(key, None)

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
