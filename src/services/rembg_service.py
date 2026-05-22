"""Servicio de Remoción de Fondo con rembg"""
import io
import weakref
from PIL import Image
from rembg import remove, new_session

class RembgService:
    def __init__(self):
        self.sessions = {}

    def get_session(self, model_name: str):
        if model_name not in self.sessions:
            print(f"[REMBG] Cargando modelo {model_name}...")
            self.sessions[model_name] = new_session(model_name)
            print(f"[REMBG] Modelo {model_name} cargado.")
        return self.sessions[model_name]

    def decontaminate_edges(self, image: Image.Image, radius: int = 5) -> Image.Image:
        """
        Elimina halos de contraluz en bordes del cabello y ropa.
        
        Fase 1: Calcula la distancia de cada píxel opaco al borde transparente.
        Fase 2: Propaga colores del interior profundo (lejos del borde) hacia afuera.
        Fase 3: Mezcla selectiva:
          - Semi-transparentes: mezcla ponderada por alfa (preserva degradados finos)
          - Opacos del borde: solo si son más brillantes que el interior profundo
            (detecta halos de contraluz sin oscurecer camisas blancas legítimas)
        """
        import numpy as np
        
        img_np = np.array(image.convert("RGBA"))
        rgb = img_np[:, :, :3].astype(np.float64)
        alpha = img_np[:, :, 3].astype(np.float64)
        
        opaque = (alpha == 255)
        semi_transparent = (alpha > 0) & (alpha < 255)
        not_opaque = ~opaque
        
        if not np.any(opaque):
            return image
        
        # === FASE 1: Distancia de cada píxel opaco al borde no-opaco ===
        edge_dist = np.full(alpha.shape, float(radius + 1), dtype=np.float64)
        edge_dist[not_opaque] = 0.0
        
        for _ in range(radius):
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                neighbor = np.roll(np.roll(edge_dist, dx, axis=1), dy, axis=0)
                edge_dist = np.minimum(edge_dist, neighbor + 1.0)
        
        # === FASE 2: Propagar colores del interior profundo hacia afuera ===
        # "Interior profundo" = píxeles opacos lejos del borde (distancia > radius)
        deep_interior = opaque & (edge_dist > radius)
        
        # Fallback: si no hay suficientes píxeles profundos, usar todos los opacos
        if np.sum(deep_interior) < 100:
            deep_interior = opaque
        
        prop_rgb = np.zeros_like(rgb)
        prop_rgb[deep_interior] = rgb[deep_interior]
        prop_w = deep_interior.astype(np.float64)
        
        # Propagar lo suficiente para que el color interior llegue al borde
        for _ in range(radius * 2):
            sum_rgb = prop_rgb.copy()
            sum_w = prop_w.copy()
            
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                shifted_rgb = np.roll(np.roll(prop_rgb, dx, axis=1), dy, axis=0)
                shifted_w = np.roll(np.roll(prop_w, dx, axis=1), dy, axis=0)
                sum_rgb += shifted_rgb
                sum_w += shifted_w
            
            has_neighbors = sum_w > 0
            to_update = has_neighbors & (prop_w == 0)
            
            if np.any(to_update):
                prop_rgb[to_update] = sum_rgb[to_update] / sum_w[to_update][:, np.newaxis]
                prop_w[to_update] = 1.0
            else:
                break
        
        # === FASE 3: Mezcla selectiva ===
        blend = np.zeros(alpha.shape, dtype=np.float64)
        
        # 3a. Semi-transparentes: mezcla por alfa (preserva degradados del cabello)
        if np.any(semi_transparent):
            blend[semi_transparent] = 1.0 - alpha[semi_transparent] / 255.0
        
        # 3b. Opacos del borde: solo si son MÁS BRILLANTES que el interior
        #     (esto detecta halos de contraluz sin afectar ropa blanca legítima)
        opaque_edge = opaque & (edge_dist <= radius) & (edge_dist > 0) & (prop_w > 0)
        if np.any(opaque_edge):
            # Luminancia del píxel vs luminancia del interior propagado
            pixel_lum = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
            interior_lum = 0.299 * prop_rgb[:, :, 0] + 0.587 * prop_rgb[:, :, 1] + 0.114 * prop_rgb[:, :, 2]
            
            # Solo corregir si es al menos 20 unidades más brillante que el interior
            brightness_diff = pixel_lum - interior_lum
            is_halo = opaque_edge & (brightness_diff > 20)
            
            if np.any(is_halo):
                # Factor por distancia: más cerca del borde = corrección más fuerte
                dist_factor = np.clip(1.0 - (edge_dist[is_halo] - 1) / max(radius - 1, 1), 0, 1)
                # Factor por brillo: más brillante que interior = corrección más fuerte
                bright_factor = np.clip(brightness_diff[is_halo] / 120.0, 0, 1)
                blend[is_halo] = dist_factor * bright_factor * 0.7
        
        # Aplicar mezcla final
        result_rgb = rgb.copy()
        has_blend = blend > 0
        if np.any(has_blend):
            for c in range(3):
                result_rgb[:, :, c] = rgb[:, :, c] * (1.0 - blend) + prop_rgb[:, :, c] * blend
        
        result_np = np.dstack([np.clip(result_rgb, 0, 255).astype(np.uint8), alpha.astype(np.uint8)])
        return Image.fromarray(result_np)

    def remove_background(
        self, 
        image: Image.Image, 
        model_name: str = "u2net", 
        alpha_matting: bool = False, 
        erode_size: int = 10,
        fg_threshold: int = 240,
        bg_threshold: int = 10,
        post_process: bool = False,
        decontaminate: bool = False
    ) -> Image.Image:
        session = self.get_session(model_name)
        
        # Opciones de rembg
        kwargs = {}
        if alpha_matting:
            kwargs["alpha_matting"] = True
            kwargs["alpha_matting_foreground_threshold"] = fg_threshold
            kwargs["alpha_matting_background_threshold"] = bg_threshold
            kwargs["alpha_matting_erode_size"] = erode_size
            
        if post_process:
            kwargs["post_process_mask"] = True

        result = remove(image, session=session, **kwargs)
        
        # Aplicar descontaminación de color de bordes si está activa
        if decontaminate:
            print("[REMBG] Aplicando decontaminación de bordes...")
            result = self.decontaminate_edges(result)
            
        return result

rembg_service = RembgService()


