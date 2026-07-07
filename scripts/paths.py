from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_ROOT = DATA_DIR / "reports"
UNIVERSE_DIR = DATA_DIR / "universe"


def reports_dir(name: str) -> Path:
    return REPORTS_ROOT / name
