from PIL import Image
from src.services.rembg_service import rembg_service

img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
res = rembg_service.remove_background(img)
print("Success:", res.size)
