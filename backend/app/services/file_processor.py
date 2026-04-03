from pathlib import Path
from typing import Any, Dict, List, Optional
import logging
import re
import unicodedata

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows

logger = logging.getLogger(__name__)


class NFSPagatoProcessor:
    PROTOCOLLI_FASE2 = ["P", "2P", "LABI"]
    PROTOCOLLI_FASE3 = [
        "EP", "2EP", "EL", "2EL", "EZ", "2EZ", "EZP",
        "FCBI", "FCSI", "FCBE", "FCSE",
        "FPIC", "FSIC", "FPEC", "FSEC",
        "AFIC", "ASIC", "AFEC", "ASEC",
        "ACBI", "ACSI", "ACBE", "ACSE",
    ]

    REQUIRED_COLUMNS = [
        "C_NOME", "FAT_DATDOC", "FAT_NDOC", "FAT_DATREG",
        "FAT_PROT", "FAT_NUM", "IMPONIBILE",
        "FAT_TOTFAT", "FAT_TOTIVA",
        "RA_CODTRIB", "RA_IMPOSTA",
        "DMA_NUM", "TMA_TOT", "TMC_G8",
    ]

    def __init__(self) -> None:
        self.all_protocols = self.PROTOCOLLI_FASE2 + self.PROTOCOLLI_FASE3

    # ========================
    # 🔧 UTILS SDI (UNIFICATI)
    # ========================
    def _normalize_sdi(self, series: pd.Series) -> pd.Series:
        def normalize(value: Any) -> str:
            if pd.isna(value):
                return ""
            if isinstance(value, float) and value.is_integer():
                return str(int(value))
            return str(value).strip().lower()
        return series.map(normalize)

    def _is_empty_sdi(self, series: pd.Series) -> pd.Series:
        normalized = self._normalize_sdi(series)
        empty_text = normalized.isin(["", "nan", "none", "null"])
        numeric = pd.to_numeric(normalized, errors="coerce")
        zero_mask = numeric.eq(0) & ~numeric.isna()
        return empty_text | zero_mask

    # ========================
    # LETTURA FILE
    # ========================
    def _read_excel_flexible(self, path: Path) -> pd.DataFrame:
        df = pd.read_excel(path)
        df.columns = df.columns.astype(str).str.strip()
        return df

    def validate_file(self, df: pd.DataFrame) -> None:
        missing = [c for c in self.REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"Colonne mancanti: {', '.join(missing)}")

    # ========================
    # MAIN
    # ========================
    def process_file(self, input_path: Path, output_path: Path) -> Dict[str, Any]:
        df = self._read_excel_flexible(input_path)
        df = df.copy()

        self.validate_file(df)

        df["FAT_PROT"] = df["FAT_PROT"].astype(str).str.strip().str.upper()

        df = df[df["FAT_PROT"].isin(self.all_protocols)].copy()

        # ========================
        # SDI dedup elettroniche
        # ========================
        elettroniche = df[df["FAT_PROT"].isin(self.PROTOCOLLI_FASE3)].copy()
        cartacee = df[df["FAT_PROT"].isin(self.PROTOCOLLI_FASE2)].copy()

        elettroniche["_SDI"] = self._normalize_sdi(elettroniche["TMC_G8"])
        mask_empty = self._is_empty_sdi(elettroniche["_SDI"])

        elet_no_empty = elettroniche[~mask_empty].drop_duplicates("_SDI")
        elet_empty = elettroniche[mask_empty]

        df = pd.concat([cartacee, elet_no_empty, elet_empty])

        # ========================
        # RITENUTA
        # ========================
        df["RA_CODTRIB"] = df["RA_CODTRIB"].astype(str).str.strip()
        mask = df["RA_CODTRIB"].isin(["I9", "RO"])
        df.loc[~mask, "RA_CODTRIB"] = ""

        # ========================
        # CALCOLI
        # ========================
        df["PAGATO_LIB_PROF"] = None
        mask_lp = df["FAT_PROT"].isin(["LABI", "EL", "2EL"]) & df["RA_CODTRIB"].isin(["I9", "RO"])

        df.loc[mask_lp, "PAGATO_LIB_PROF"] = (
            pd.to_numeric(df.loc[mask_lp, "FAT_TOTFAT"], errors="coerce")
            - pd.to_numeric(df.loc[mask_lp, "RA_IMPOSTA"], errors="coerce")
        )

        df["PAGATO_ISTIT"] = None
        mask_ist = ~df["FAT_PROT"].isin(["LABI", "EL", "2EL"])

        df.loc[mask_ist, "PAGATO_ISTIT"] = pd.to_numeric(
            df.loc[mask_ist, "IMPONIBILE"], errors="coerce"
        )

        # ========================
        # OUTPUT
        # ========================
        df_out = pd.DataFrame({
            "Ragione Sociale": df["C_NOME"],
            "Data Fatture": pd.to_datetime(df["FAT_DATDOC"], errors="coerce"),
            "N. Fatture": df["FAT_NDOC"],
            "Data registrazione pagamento": pd.to_datetime(df["FAT_DATREG"], errors="coerce"),
            "Protocollo": df["FAT_PROT"],
            "N. Protocollo": df["FAT_NUM"],
            "Imponibile": df["IMPONIBILE"],
            "Pagato Lib. Prof.": df["PAGATO_LIB_PROF"],
            "Pagato Istit.": df["PAGATO_ISTIT"],
            "Imposta": df["FAT_TOTIVA"],
            "Ritenuta": df["RA_CODTRIB"],
            "Mandato": df["DMA_NUM"],
            "Importo Mandato": df["TMA_TOT"],
            "SDI": df["TMC_G8"],
        })

        df_out = df_out.sort_values("Data registrazione pagamento")

        self._create_excel_output(df_out, output_path)

        return {"records": len(df_out)}

    # ========================
    # EXCEL
    # ========================
    def _create_excel_output(self, df: pd.DataFrame, path: Path) -> None:
        wb = Workbook()
        ws = wb.active
        ws.title = "Dati"

        for r in dataframe_to_rows(df, index=False, header=True):
            ws.append(r)

        wb.save(path)


# ========================
# COMPARE (FIXATO)
# ========================
class CompareFTFileProcessor:
    NFS_CARTACEE_PROTOCOLS = NFSPagatoProcessor.PROTOCOLLI_FASE2
    NFS_ELETTRONICHE_PROTOCOLS = NFSPagatoProcessor.PROTOCOLLI_FASE3