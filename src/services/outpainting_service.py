"""Servicio de Outpainting con SDXL Inpainting"""
import os
import sys
import torch
from PIL import Image
from pathlib import Path
from typing import Optional, Literal

# Lazy import para no cargar diffusers al iniciar la app
_pipeline = None


class OutpaintingService:
    """Servicio de outpainting usando SDXL Inpainting.
    
    El modelo se carga lazy (solo cuando se usa por primera vez)
    para no consumir VRAM al iniciar la aplicación.
    """
    
    def __init__(self):
        self.pipe = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_id = "diffusers/stable-diffusion-xl-1.0-inpainting-0.1"
        self._loading = False
    
    def is_available(self) -> bool:
        """Verifica si CUDA está disponible para outpainting."""
        return torch.cuda.is_available()
    
    def is_loaded(self) -> bool:
        """Verifica si el modelo ya está cargado en memoria."""
        return self.pipe is not None
    
    def get_gpu_info(self) -> dict:
        """Retorna información de la GPU."""
        if not torch.cuda.is_available():
            return {"available": False, "name": "N/A", "vram_total": 0, "vram_free": 0}
        
        name = torch.cuda.get_device_name(0)
        vram_total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        vram_free = (torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated(0)) / (1024**3)
        
        return {
            "available": True,
            "name": name,
            "vram_total": round(vram_total, 1),
            "vram_free": round(vram_free, 1),
            "model_loaded": self.is_loaded()
        }
    
    def load_model(self):
        """Carga el modelo SDXL Inpainting en la GPU.
        
        La primera vez descargará ~7GB del modelo de HuggingFace.
        Después se cachea en ~/.cache/huggingface/
        """
        if self.pipe is not None:
            return
        
        if self._loading:
            return
        
        self._loading = True
        
        try:
            from diffusers import StableDiffusionXLInpaintPipeline
            
            print(f"[OUTPAINTING] Loading model: {self.model_id}")
            print(f"[OUTPAINTING] Device: {self.device}")
            print(f"[OUTPAINTING] This may take a few minutes on first run (downloading ~7GB)...")
            
            dtype = torch.float16 if self.device == "cuda" else torch.float32
            
            self.pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
                self.model_id,
                torch_dtype=dtype,
                variant="fp16" if self.device == "cuda" else None,
            )
            
            # Optimizaciones para VRAM (evita swapear 30-40 min)
            if self.device == "cuda":
                # En lugar de to(device), usamos offload para manejar GPUs de poca VRAM (4-8GB)
                self.pipe.enable_model_cpu_offload()
                self.pipe.enable_attention_slicing()
                try:
                    self.pipe.enable_xformers_memory_efficient_attention()
                    print("[OUTPAINTING] xformers enabled")
                except Exception:
                    print("[OUTPAINTING] xformers not available, using default attention")
            else:
                self.pipe.to(self.device)
            
            print("[OUTPAINTING] Model loaded successfully!")
        
        except Exception as e:
            print(f"[OUTPAINTING] Error loading model: {e}")
            self.pipe = None
            raise
        finally:
            self._loading = False
    
    def unload_model(self):
        """Descarga el modelo de la GPU para liberar VRAM."""
        if self.pipe is not None:
            del self.pipe
            self.pipe = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("[OUTPAINTING] Model unloaded, VRAM freed.")
    
    def expand(
        self,
        image: Image.Image,
        direction: Literal["up", "down", "left", "right", "all"] = "all",
        pixels: int = 128,
        prompt: str = "",
        negative_prompt: str = "blurry, bad quality, distorted, artifacts, text, watermark",
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
        strength: float = 0.99,
    ) -> Image.Image:
        """Expande una imagen en la dirección especificada usando outpainting.
        
        Args:
            image: Imagen PIL original
            direction: Dirección de expansión
            pixels: Cantidad de píxeles a expandir (32-512)
            prompt: Texto para guiar la generación (opcional)
            negative_prompt: Texto para evitar en la generación
            num_inference_steps: Pasos de inferencia (más = mejor calidad, más lento)
            guidance_scale: Qué tanto seguir el prompt (7-12 recomendado)
            strength: Fuerza del inpainting (0.99 = casi todo nuevo en área expandida)
            
        Returns:
            Imagen expandida
        """
        if self.pipe is None:
            self.load_model()
        
        # Clamp pixels
        pixels = max(32, min(512, pixels))
        
        # Get original dimensions
        orig_w, orig_h = image.size
        
        # Calculate new canvas dimensions based on direction
        if direction == "all":
            new_w = orig_w + pixels * 2
            new_h = orig_h + pixels * 2
        elif direction == "right":
            new_w = orig_w + pixels
            new_h = orig_h
        elif direction == "left":
            new_w = orig_w + pixels
            new_h = orig_h
        elif direction == "down":
            new_w = orig_w
            new_h = orig_h + pixels
        elif direction == "up":
            new_w = orig_w
            new_h = orig_h + pixels
        else:
            raise ValueError(f"Invalid direction: {direction}")
            
        # Cap dimensions for 8GB VRAM (max 1024x1024 equivalent area for SDXL)
        max_area = 1024 * 1024
        current_area = new_w * new_h
        
        # Guardar dimensiones y tamaños originales para restaurar alta calidad
        true_orig_image = image.copy()
        true_orig_w, true_orig_h = true_orig_image.size
        true_new_w, true_new_h = new_w, new_h
        true_pixels = pixels
        
        if direction == "all":
            true_paste_x, true_paste_y = true_pixels, true_pixels
        elif direction == "right":
            true_paste_x, true_paste_y = 0, 0
        elif direction == "left":
            true_paste_x, true_paste_y = true_pixels, 0
        elif direction == "down":
            true_paste_x, true_paste_y = 0, 0
        elif direction == "up":
            true_paste_x, true_paste_y = 0, true_pixels
        
        if current_area > max_area:
            import math
            scale = math.sqrt(max_area / current_area)
            
            # Scale down everything proportionally
            new_w = int(new_w * scale)
            new_h = int(new_h * scale)
            pixels = int(pixels * scale)
            
            image = image.resize((int(orig_w * scale), int(orig_h * scale)), Image.LANCZOS)
            orig_w, orig_h = image.size

        # SDXL works best with multiples of 8
        new_w = (new_w // 8) * 8
        new_h = (new_h // 8) * 8
        
        # Calculate paste coordinates
        if direction == "all":
            paste_x, paste_y = pixels, pixels
        elif direction == "right":
            paste_x, paste_y = 0, 0
        elif direction == "left":
            paste_x, paste_y = pixels, 0
        elif direction == "down":
            paste_x, paste_y = 0, 0
        elif direction == "up":
            paste_x, paste_y = 0, pixels
            
        # Recalculate original image size to strictly fit the 8-pixel aligned canvas
        if direction == "all":
            expected_orig_w = new_w - pixels * 2
            expected_orig_h = new_h - pixels * 2
        elif direction in ("left", "right"):
            expected_orig_w = new_w - pixels
            expected_orig_h = new_h
        elif direction in ("up", "down"):
            expected_orig_w = new_w
            expected_orig_h = new_h - pixels
            
        expected_orig_w = max(8, expected_orig_w)
        expected_orig_h = max(8, expected_orig_h)
        
        if orig_w != expected_orig_w or orig_h != expected_orig_h:
            image = image.resize((expected_orig_w, expected_orig_h), Image.LANCZOS)
            orig_w, orig_h = image.size
        
        # Create expanded canvas (fill with average edge color for better results)
        canvas = Image.new("RGB", (new_w, new_h), self._get_edge_color(image, direction))
        canvas.paste(image, (paste_x, paste_y))
        
        # Create mask (white = area to generate, black = keep original)
        mask = Image.new("L", (new_w, new_h), 255)  # Start all white
        # Mark original image area as black (keep it)
        mask_draw = Image.new("L", (orig_w, orig_h), 0)
        mask.paste(mask_draw, (paste_x, paste_y))
        
        # Add feathering at the edges for smooth blending (16px gradient)
        mask = self._feather_mask(mask, paste_x, paste_y, orig_w, orig_h, feather=16)
        
        # Default prompt if none provided
        if not prompt:
            prompt = "high quality, photorealistic, seamless continuation, natural extension of the scene, detailed, 8k"
        
        # Run inpainting
        with torch.inference_mode():
            result = self.pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                image=canvas,
                mask_image=mask,
                width=new_w,
                height=new_h,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                strength=strength,
            ).images[0]
        
        # FIX: Evitar que cambie la imagen original y REENSCALAR a alta calidad.
        # 1. Componemos en baja resolución para evitar defectos del VAE
        low_res_result = Image.composite(result, canvas, mask)
        
        # 2. Reescalamos al tamaño original (alta resolución)
        high_res_result = low_res_result.resize((true_new_w, true_new_h), Image.LANCZOS)
        
        # 3. Creamos una máscara en alta resolución para pegar la imagen original original intacta
        high_res_mask = Image.new("L", (true_new_w, true_new_h), 255)
        high_res_mask_draw = Image.new("L", (true_orig_w, true_orig_h), 0)
        high_res_mask.paste(high_res_mask_draw, (true_paste_x, true_paste_y))
        high_res_mask = self._feather_mask(high_res_mask, true_paste_x, true_paste_y, true_orig_w, true_orig_h, feather=32)
        
        # 4. Creamos un canvas con la alta resolución, y le pegamos el original para hacer la comp final
        high_res_canvas = high_res_result.copy()
        high_res_canvas.paste(true_orig_image, (true_paste_x, true_paste_y))
        final_result = Image.composite(high_res_result, high_res_canvas, high_res_mask)
        
        # Clean up VRAM
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        return final_result
    
    def _get_edge_color(self, image: Image.Image, direction: str) -> tuple:
        """Calcula el color promedio del borde de la imagen para rellenar el canvas."""
        import numpy as np
        arr = np.array(image)
        
        if direction in ("right", "all"):
            edge = arr[:, -4:, :]  # Last 4 columns
        elif direction == "left":
            edge = arr[:, :4, :]
        elif direction == "down":
            edge = arr[-4:, :, :]
        elif direction == "up":
            edge = arr[:4, :, :]
        else:
            edge = arr[:4, :, :]
        
        avg = edge.mean(axis=(0, 1)).astype(int)
        return tuple(avg[:3])
    
    def _feather_mask(self, mask: Image.Image, paste_x: int, paste_y: int, 
                       orig_w: int, orig_h: int, feather: int = 16) -> Image.Image:
        """Aplica un degradado suave en los bordes de la máscara para transiciones naturales."""
        import numpy as np
        
        mask_arr = np.array(mask, dtype=np.float32)
        
        # Create feathered transition at each edge of the original image
        for i in range(feather):
            alpha = int(255 * (i / feather))
            
            # Top edge
            if paste_y > 0 and paste_y + i < mask_arr.shape[0]:
                mask_arr[paste_y + i, paste_x:paste_x + orig_w] = min(
                    mask_arr[paste_y + i, paste_x:paste_x + orig_w].min(), alpha
                )
            
            # Bottom edge
            by = paste_y + orig_h - 1 - i
            if by >= 0 and by < mask_arr.shape[0]:
                mask_arr[by, paste_x:paste_x + orig_w] = min(
                    mask_arr[by, paste_x:paste_x + orig_w].min(), alpha
                )
            
            # Left edge
            if paste_x > 0 and paste_x + i < mask_arr.shape[1]:
                mask_arr[paste_y:paste_y + orig_h, paste_x + i] = np.minimum(
                    mask_arr[paste_y:paste_y + orig_h, paste_x + i], alpha
                )
            
            # Right edge
            rx = paste_x + orig_w - 1 - i
            if rx >= 0 and rx < mask_arr.shape[1]:
                mask_arr[paste_y:paste_y + orig_h, rx] = np.minimum(
                    mask_arr[paste_y:paste_y + orig_h, rx], alpha
                )
        
        return Image.fromarray(mask_arr.astype(np.uint8))


# Singleton instance
outpainting_service = OutpaintingService()
