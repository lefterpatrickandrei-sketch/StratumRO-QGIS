import os
from pathlib import Path
from config import ALLOWED_EXTENSIONS

def validate_file_structure(file_path: Path, layer_type: str) -> bool:
    """
    Verifica daca fisierul descarcat exista fizic pe disk, 
    daca contine date (nu este gol) si daca are o extensie valida.
    """
    if not os.path.exists(file_path):
        print(f"[Validator] Eroare: Fisierul nu exista la calea: {file_path}")
        return False

    if os.path.getsize(file_path) == 0:
        print(f"[Validator] Eroare: Fisierul descarcat este gol (0 bytes): {file_path}")
        return False

    ext = file_path.suffix.lower()
    if layer_type.lower() == "raster":
        if ext not in ALLOWED_EXTENSIONS["raster"]:
            print(f"[Validator] Extensie raster invalida: {ext}. Permise: {ALLOWED_EXTENSIONS['raster']}")
            return False
    elif layer_type.lower() == "point_cloud":
        if ext not in ALLOWED_EXTENSIONS["point_cloud"]:
            print(f"[Validator] Extensie nor de puncte invalida: {ext}. Permise: {ALLOWED_EXTENSIONS['point_cloud']}")
            return False
    else:
        print(f"[Validator] Tip de strat necunoscut pentru validare: {layer_type}")
        return False

    print(f"[Validator] Validare structurala initiala reusita pentru: {file_path.name}")
    return True