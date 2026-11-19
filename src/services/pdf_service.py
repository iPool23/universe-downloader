"""Servicio de compresión de PDFs"""
import io
import os
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple

import pikepdf
from PIL import Image

# Progreso de compresiones en curso (compress_id -> dict)
compress_progress: Dict[str, Dict] = {}

# Imágenes más pequeñas que esto (iconos, logos, firmas) no se recomprimen
MIN_IMAGE_PIXELS = 400 * 400


def _image_mode(xobj) -> Optional[str]:
    """Determina el modo PIL ('RGB'/'L') de una imagen si es segura de recomprimir.

    Se excluyen imágenes con canal alfa (SMask/Mask), profundidad distinta de
    8 bits, o espacios de color que no sean RGB/Gris (CMYK, Indexed, etc.)
    para evitar cualquier cambio de color inesperado.
    """
    if '/SMask' in xobj or '/Mask' in xobj:
        return None
    if int(xobj.get('/BitsPerComponent', 0)) != 8:
        return None

    colorspace = xobj.get('/ColorSpace')
    if colorspace is None:
        return None

    name = str(colorspace)
    if name == '/DeviceRGB':
        return 'RGB'
    if name == '/DeviceGray':
        return 'L'
    if isinstance(colorspace, pikepdf.Array) and len(colorspace) >= 2 and str(colorspace[0]) == '/ICCBased':
        try:
            components = int(colorspace[1].N)
        except Exception:
            return None
        return {1: 'L', 3: 'RGB'}.get(components)

    return None


class PdfService:
    """Comprime PDFs.

    Siempre optimiza la estructura del archivo sin pérdida (deduplica objetos,
    comprime streams). Si `quality` < 100, además recomprime las imágenes
    internas como JPEG a la calidad indicada (100 = no tocar las imágenes).
    """

    def compress(
        self,
        input_path: Path,
        output_path: Path,
        quality: int = 100,
        compress_id: Optional[str] = None,
    ) -> Tuple[int, int]:
        quality = max(30, min(100, quality))
        return self._compress_unclamped(input_path, output_path, quality, compress_id)

    def compress_to_target_size(
        self,
        input_path: Path,
        output_path: Path,
        max_size_bytes: int,
        compress_id: Optional[str] = None,
        max_attempts: int = 6,
    ) -> Tuple[int, int, int, bool]:
        """Busca automáticamente la calidad más alta (0-100) cuyo resultado quepa
        en `max_size_bytes`, mediante búsqueda binaria. Si ni siquiera la calidad
        mínima (0) alcanza el límite, entrega igualmente el resultado más pequeño
        posible (mejor esfuerzo) y lo indica en el último valor devuelto.

        Returns:
            (original_size, final_size, quality_used, reached_target)
        """
        original_size = input_path.stat().st_size

        self._report(compress_id, 3, 'Probando optimización sin pérdida...')
        lossless_size = self._trial_size(input_path, 100)
        if lossless_size <= max_size_bytes:
            self._compress_unclamped(input_path, output_path, 100, compress_id)
            return original_size, output_path.stat().st_size, 100, True

        low, high = 0, 99
        best_quality, best_size = None, None
        attempt = 0

        while low <= high and attempt < max_attempts:
            attempt += 1
            mid = (low + high) // 2
            self._report(compress_id, min(75, 5 + attempt * 11), f'Probando calidad {mid}%... (intento {attempt})')
            size = self._trial_size(input_path, mid)

            if size <= max_size_bytes:
                best_quality, best_size = mid, size
                low = mid + 1  # intentar una calidad mejor todavía
            else:
                high = mid - 1

        reached_target = best_quality is not None
        if best_quality is None:
            best_quality = 0  # ni siquiera la compresión máxima alcanzó el límite

        self._report(compress_id, 90, 'Generando archivo final...')
        self._compress_unclamped(input_path, output_path, best_quality, compress_id)

        final_size = output_path.stat().st_size
        return original_size, final_size, best_quality, reached_target

    def _trial_size(self, input_path: Path, quality: int) -> int:
        """Comprime a un archivo temporal solo para medir el tamaño resultante."""
        tmp_fd, tmp_name = tempfile.mkstemp(suffix='.pdf')
        os.close(tmp_fd)
        tmp_path = Path(tmp_name)
        try:
            self._compress_unclamped(input_path, tmp_path, quality, compress_id=None)
            return tmp_path.stat().st_size
        finally:
            try:
                tmp_path.unlink()
            except Exception:
                pass

    def _compress_unclamped(
        self,
        input_path: Path,
        output_path: Path,
        quality: int,
        compress_id: Optional[str],
    ) -> Tuple[int, int]:
        with pikepdf.open(str(input_path)) as pdf:
            if quality < 100:
                self._recompress_images(pdf, quality, compress_id)

            self._report(compress_id, 90, 'Optimizando estructura del PDF...')
            pdf.remove_unreferenced_resources()
            pdf.save(
                str(output_path),
                compress_streams=True,
                stream_decode_level=pikepdf.StreamDecodeLevel.generalized,
                object_stream_mode=pikepdf.ObjectStreamMode.generate,
            )

        original_size = input_path.stat().st_size
        final_size = output_path.stat().st_size
        return original_size, final_size

    def _report(self, compress_id: Optional[str], percent: int, message: str):
        if compress_id and compress_id in compress_progress:
            compress_progress[compress_id].update({'percent': percent, 'message': message})

    def _recompress_images(self, pdf: pikepdf.Pdf, quality: int, compress_id: Optional[str]):
        jpeg_quality = max(30, min(94, quality))
        # 100 -> escala 1.0 (no redimensiona) | 30 -> escala 0.65
        scale = 0.5 + (quality / 100) * 0.5

        images = [
            obj for obj in pdf.objects
            if isinstance(obj, pikepdf.Stream) and obj.get('/Subtype') == pikepdf.Name('/Image')
        ]

        total = len(images) or 1
        for i, xobj in enumerate(images):
            self._report(compress_id, 5 + int((i / total) * 80), f'Recomprimiendo imágenes... ({i + 1}/{total})')

            mode = _image_mode(xobj)
            if mode is None:
                continue

            try:
                raw_len = len(xobj.read_raw_bytes()) if '/Filter' in xobj else 0
                pil_image = pikepdf.PdfImage(xobj).as_pil_image()
            except Exception:
                continue

            if pil_image.mode != mode:
                pil_image = pil_image.convert(mode)

            width, height = pil_image.size
            if width * height < MIN_IMAGE_PIXELS:
                continue

            new_width, new_height = max(1, int(width * scale)), max(1, int(height * scale))
            resized = pil_image.resize((new_width, new_height), Image.LANCZOS) if scale < 0.999 else pil_image

            buffer = io.BytesIO()
            resized.save(buffer, 'JPEG', quality=jpeg_quality, optimize=True)
            new_bytes = buffer.getvalue()

            original_bytes = raw_len or (width * height * len(mode))
            if len(new_bytes) >= original_bytes:
                continue  # nunca dejar una imagen más pesada de lo que ya estaba

            xobj.write(new_bytes, filter=pikepdf.Name('/DCTDecode'))
            xobj.ColorSpace = pikepdf.Name('/DeviceRGB' if mode == 'RGB' else '/DeviceGray')
            xobj.Width = new_width
            xobj.Height = new_height
            xobj.BitsPerComponent = 8
            if '/DecodeParms' in xobj:
                del xobj['/DecodeParms']
            if '/Decode' in xobj:
                del xobj['/Decode']


pdf_service = PdfService()
