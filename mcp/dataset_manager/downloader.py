import os
import urllib.request
from pathlib import Path
from config import ORTHOPHOTO_DIR, LIDAR_DIR
from models import DownloadRequest

def download_dataset(request: DownloadRequest) -> Path:
    """
    Descarca un fisier geospatial de la un URL dat si il salveaza in folderul corespunzator.
    Foloseste descarcarea in flux (chunks) pentru a gestiona fisiere mari (LiDAR/Ortofoto).
    """
    if request.layer_type.lower() == "raster":
        target_dir = ORTHOPHOTO_DIR
    elif request.layer_type.lower() == "point_cloud":
        target_dir = LIDAR_DIR
    else:
        raise ValueError(f"Tip de strat necunoscut: {request.layer_type}")

    # Extragerea exclusivă a numelui de fișier pentru prevenirea atacurilor de tip Path Injection
    safe_filename = Path(request.filename).name
    destination_path = target_dir / safe_filename

    # Am eliminat diacriticele din print-uri pentru a preveni crash-ul pe Windows stdout
    print(f"[Dataset Manager] Se initiaza descarcarea: {request.url}")
    
    with urllib.request.urlopen(request.url, timeout=30) as response, open(destination_path, "wb") as out_file:
        block_size = 1024 * 1024  # 1 MB
        while True:
            chunk = response.read(block_size)
            if not chunk:
                break
            out_file.write(chunk)

    print(f"[Dataset Manager] Descarcare completa. Fisier salvat la: {destination_path}")
    return destination_path