"""Modelos de datos (DTOs)"""
from typing import Optional
from pydantic import BaseModel, Field, validator


class VideoInfo(BaseModel):
    """Modelo para información del video"""
    title: str
    duration: float
    thumbnail: str
    webpage_url: str


class DownloadRequest(BaseModel):
    """Modelo para solicitud de descarga"""
    url: str = Field(..., description="URL del video de YouTube")
    format: str = Field(..., description="Formato de descarga (mp3 o mp4)")
    download_id: str = Field(..., description="ID único de la descarga")
    start_time: Optional[str] = Field(None, description="Tiempo de inicio (HH:MM:SS)")
    end_time: Optional[str] = Field(None, description="Tiempo de fin (HH:MM:SS)")
    
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
