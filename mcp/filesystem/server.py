from fastmcp import FastMCP
from pathlib import Path

mcp = FastMCP("Filesystem")

# Rădăcina permisă pentru operații — SIGURANȚĂ:
# nu lăsăm LLM-ul să umble prin tot sistemul de fișiere,
# doar în interiorul proiectului
BASE_DIR = Path(__file__).resolve().parent.parent.parent / "workspace"
BASE_DIR.mkdir(exist_ok=True)


def _safe_resolve(user_path: str) -> Path:
    """Rezolvă calea furnizată de LLM și validează că rămâne în interiorul BASE_DIR.

    Previne atacuri de tip Path Traversal (ex: '../../etc/passwd').
    Aruncă ValueError dacă calea rezolvată evadează din sandbox.
    """
    target = (BASE_DIR / user_path).resolve()
    if not target.is_relative_to(BASE_DIR):
        raise ValueError(
            f"Acces refuzat: calea '{user_path}' iese din sandbox-ul workspace."
        )
    return target


@mcp.tool()
def create_folder(name: str) -> str:
    """Creează un folder nou în workspace."""
    target = _safe_resolve(name)
    target.mkdir(parents=True, exist_ok=True)
    return f"Folder creat: {target}"


@mcp.tool()
def list_files(subpath: str = "") -> list[str]:
    """Listează fișierele dintr-un subfolder al workspace-ului."""
    target = _safe_resolve(subpath)
    if not target.exists():
        return [f"Eroare: {target} nu există"]
    return [str(p.relative_to(BASE_DIR)) for p in target.iterdir()]


if __name__ == "__main__":
    mcp.run()