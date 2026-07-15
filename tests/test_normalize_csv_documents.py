from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


def load_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "normalize_csv_documents.py"
    spec = spec_from_file_location("normalize_csv_documents", script_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_default_targets_include_active_main_csv():
    module = load_module()
    assert module.PROJECT_DIR / "data" / "processed" / "Main_Song_Database.csv" in module.DEFAULT_TARGETS


def test_normalize_rows_reports_typography_changes():
    module = load_module()
    rows = [{"Title": "Beyoncé - \xa0Rebel Yell", "Artist": "La Femme D´Argent"}]
    normalized, incidents = module.normalize_rows(rows)
    assert normalized[0]["Title"] == "Beyoncé - Rebel Yell"
    assert normalized[0]["Artist"] == "La Femme D'Argent"
    assert len(incidents) == 2
