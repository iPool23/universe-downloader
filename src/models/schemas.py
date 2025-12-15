"""Modelos de datos (DTOs)"""
from typing import Optional
from pydantic import BaseModel, Field, validator


class VideoQuality(BaseModel):
    """Modelo para calidad de video"""
    value: int
    label: str


class VideoInfo(BaseModel):
    """Modelo para información del video"""
    title: str
    duration: Optional[float] = None
    thumbnail: Optional[str] = None
    webpage_url: str
    qualities: list[VideoQuality] = []


class DownloadRequest(BaseModel):
    """Modelo para solicitud de descarga"""
    url: str = Field(..., description="URL del video de YouTube")
    format: str = Field(..., description="Formato de descarga (mp3 o mp4)")
    download_id: str = Field(..., description="ID único de la descarga")
    start_time: Optional[str] = Field(None, description="Tiempo de inicio (HH:MM:SS)")
    end_time: Optional[str] = Field(None, description="Tiempo de fin (HH:MM:SS)")
    quality: Optional[int] = Field(None, description="Calidad del video en píxeles (ej: 720, 1080)")
    audio_quality: Optional[int] = Field(None, description="Calidad del audio en kbps (ej: 128, 192, 256, 320)")
    
    @validator('format')
    def validate_format(cls, v):
        if v not in ['mp3', 'mp4']:
            raise ValueError('Formato debe ser mp3 o mp4')
        return v
    
    @validator('url')
    def validate_url(cls, v):
        if not v or not v.strip():
            raise ValueError('URL no puede estar vacía')
        return v.strip()
