from pydantic import BaseModel, Field
from typing import Optional

class DownloadRequest(BaseModel):
    """Model de validare pentru cererile de descărcare primite de la LLM/Backend."""
    url: str = Field(..., description="URL-ul direct de unde se descarcă setul de date geospațiale")
    filename: str = Field(..., description="Numele sub care va fi salvat fișierul pe disk (ex: pod_therme_ortho.tif)")
    layer_type: str = Field(..., description="Tipul de strat: 'raster' sau 'point_cloud'")
    crs: Optional[str] = Field("EPSG:31700", description="Sistemul de coordonate estimat al setului de date")

class DatasetMetadata(BaseModel):
    """Model care stochează metadatele unui fișier descărcat cu succes."""
    file_path: str = Field(..., description="Calea absolută către fișierul salvat pe disk")
    file_size_mb: float = Field(..., description="Dimensiunea fișierului în Megabytes")
    crs_verified: str = Field(..., description="CRS-ul extras și verificat din interiorul fișierului")
    is_valid: bool = Field(True, description="Starea validității structurale a fișierului geospațial")