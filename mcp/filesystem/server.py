from fastmcp import FastMCP
from pathlib import Path

mcp = FastMCP("Filesystem")

# Rădăcina permisă pentru operații — SIGURANȚĂ:
# nu lăsăm LLM-ul să umble prin tot sistemul de fișiere,
# doar în interiorul proiectului
BASE_DIR = Path(r"C:\Users\lefpa\Downloads\QGIS-AI\workspace")
BASE_DIR.mkdir(exist_ok=True)

@mcp.tool()
def create_folder(name: str) -> str:
    """Creează un folder nou în workspace."""
    target = BASE_DIR / name
    target.mkdir(parents=True, exist_ok=True)
    return f"Folder creat: {target}"

@mcp.tool()
def list_files(subpath: str = "") -> list[str]:
    """Listează fișierele dintr-un subfolder al workspace-ului."""
    target = BASE_DIR / subpath
    if not target.exists():
        return [f"Eroare: {target} nu există"]
    return [str(p.relative_to(BASE_DIR)) for p in target.iterdir()]

if __name__ == "__main__":
    mcp.run()