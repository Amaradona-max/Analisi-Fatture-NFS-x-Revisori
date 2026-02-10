from pathlib import Path

import pandas as pd
import pytest

from app.services.file_processor import NFSFTFileProcessor


@pytest.fixture
def sample_dataframe():
    return pd.DataFrame(
        {
            "C_NOME": ["ACME Inc", "Test Corp", "ACME Inc"],
            "FAT_DATDOC": ["2025-01-01", "2025-01-02", "2025-01-01"],
            "FAT_NDOC": ["F001", "F002", "F001"],
            "FAT_DATREG": ["2025-01-01", "2025-01-02", "2025-01-01"],
            "FAT_PROT": ["EP", "P", "EP"],
            "FAT_NUM": [1, 2, 1],
            "IMPONIBILE": [100.0, 200.0, 100.0],
            "FAT_TOTFAT": [122.0, 244.0, 122.0],
            "FAT_TOTIVA": [22.0, 44.0, 22.0],
            "DMA_NUM": ["M001", "M002", "M001"],
            "RA_CODTRIB": ["I9", "XX", "RO"],
            "RA_IMPOSTA": [5.0, 10.0, 5.0],
            "TMA_TOT": [122.0, 244.0, 122.0],
            "TMC_G8": ["ID1", "ID2", "ID1"],
        }
    )


def test_validate_file_success(sample_dataframe):
    processor = NFSFTFileProcessor()
    processor.validate_file(sample_dataframe)


def test_validate_file_missing_columns():
    processor = NFSFTFileProcessor()
    df = pd.DataFrame({"WRONG_COL": [1, 2]})
    with pytest.raises(ValueError, match="Colonne mancanti"):
        processor.validate_file(df)


def test_process_file_removes_duplicates(sample_dataframe, tmp_path: Path):
    processor = NFSFTFileProcessor()
    input_path = tmp_path / "input.xlsx"
    output_path = tmp_path / "output.xlsx"

    sample_dataframe.to_excel(input_path, index=False)
    stats = processor.process_file(input_path, output_path)

    assert output_path.exists()
    assert stats["total_records"] == 2
    assert stats["duplicates_removed"] == 1
    assert stats["fase2_records"] == 1
    assert stats["fase3_records"] == 1
