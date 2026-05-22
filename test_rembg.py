from PIL import Image
from src.services.rembg_service import rembg_service

# Crear imagen de prueba
img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))

print("1. Probando modelo estándar (u2net)...")
res1 = rembg_service.remove_background(img, model_name="u2net")
print("Éxito:", res1.size)

print("2. Probando con Alpha Matting...")
res2 = rembg_service.remove_background(img, model_name="u2net", alpha_matting=True, erode_size=10)
print("Éxito:", res2.size)

print("3. Probando con Post-procesado y Umbrales personalizados...")
res3 = rembg_service.remove_background(img, model_name="u2net", alpha_matting=True, erode_size=15, fg_threshold=230, bg_threshold=20, post_process=True)
print("Éxito:", res3.size)

print("4. Probando con Decontaminación de Bordes activa...")
res4 = rembg_service.remove_background(img, model_name="u2net", decontaminate=True)
print("Éxito:", res4.size)

print("¡Todas las pruebas del backend pasaron con éxito!")

