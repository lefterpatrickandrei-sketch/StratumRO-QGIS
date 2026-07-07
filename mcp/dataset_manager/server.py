import sys
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# Ne asiguram ca directorul curent este inclus in caile Python
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from models import DownloadRequest
from downloader import download_dataset
from validator import validate_file_structure

# Initializam serverul FastMCP
mcp = FastMCP("Dataset Manager")

@mcp.tool()
def download_geospatial_data(url: str, filename: str, layer_type: str) -> str:
    """
    Descarca si valideaza structural un set de date geospatiale (Raster tip TIF sau Nor de puncte LiDAR tip LAS/LAZ).
    """
    try:
        # 1. Validare cerere
        request = DownloadRequest(url=url, filename=filename, layer_type=layer_type)
        
        # 2. Descarcare streaming
        file_path = download_dataset(request)
        
        # 3. Validare structurala
        is_valid = validate_file_structure(file_path, request.layer_type)
        
        if not is_valid:
            return f"Eroare: Fisierul salvat la {filename} nu a trecut validarea structurala."
            
        # 4. Calcul dimensiune pe disk
        file_size_mb = round(file_path.stat().st_size / (1024 * 1024), 2)
        
        return (
            f"=== DATASET DOWNLOAD SUCCESS ===\n"
            f"Fisier stocat: {file_path.name}\n"
            f"Cale absoluta: {file_path}\n"
            f"Dimensiune: {file_size_mb} MB\n"
            f"Tip strat validat: {layer_type.upper()}"
        )
               
    except Exception as e:
        return f"Eroare critica in Dataset Manager: {str(e)}"

if __name__ == "__main__":
    mcp.run()