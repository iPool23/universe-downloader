"""Servicio de Remoción de Fondo con rembg"""
import io
import weakref
from PIL import Image
from rembg import remove, new_session

class RembgService:
    def __init__(self):
        self.session = None

    def load_model(self):
        if self.session is None:
            print("[REMBG] Cargando modelo u2net...")
            self.session = new_session("u2net")
            print("[REMBG] Modelo cargado.")

    def unload_model(self):
        if self.session is not None:
            self.session = None
            print("[REMBG] Modelo descargado.")

    def remove_background(self, image: Image.Image) -> Image.Image:
        self.load_model()
        return remove(image, session=self.session)

rembg_service = RembgService()
