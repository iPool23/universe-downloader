# YouTube Downloader - Documentación para Desarrolladores

## 📋 Descripción

Aplicación web para descargar videos y audio de YouTube en máxima calidad, con interfaz moderna y fácil de usar.

## 🚀 Características

- ✅ Descarga videos en MP4 (hasta 4K/2160p)
- ✅ Descarga audio en M4A de alta calidad (AAC)
- ✅ Interfaz web moderna con modal de notificaciones
- ✅ Detección automática de FFmpeg
- ✅ Ejecutable standalone (no requiere Python instalado)
- ✅ Portable y listo para distribuir

## 🛠️ Tecnologías

- **Backend**: FastAPI + Uvicorn
- **Descarga**: yt-dlp
- **Frontend**: HTML5 + CSS3 + JavaScript vanilla
- **Build**: PyInstaller
- **Python**: 3.11+

## 📦 Estructura del Proyecto

```
youtubedlp/
├── src/
│   └── youtubedpl.py          # Aplicación principal
├── downloads/                  # Carpeta de descargas temporales
├── build.py                    # Script de compilación
├── create_release.py           # Script de empaquetado
├── BUILD_RELEASE.bat           # Build automático (Windows)
├── dist/                       # Ejecutable compilado
└── YouTubeDownloader_v1.0_Windows.zip  # Paquete de distribución
```

## 🔧 Desarrollo

### Requisitos

```bash
pip install fastapi uvicorn yt-dlp pydantic
```

### Ejecutar en modo desarrollo

```bash
python src/youtubedpl.py
```

La aplicación se abrirá automáticamente en `http://127.0.0.1:8000`

## 📦 Crear Ejecutable

### Opción 1: Script automático (Recomendado)

```bash
BUILD_RELEASE.bat
```

### Opción 2: Paso a paso

```bash
# 1. Compilar ejecutable
python build.py

# 2. Crear paquete de distribución
python create_release.py
```

### Resultado

Se generará:
- `dist/YouTubeDownloader.exe` - Ejecutable standalone (48 MB)
- `YouTubeDownloader_v1.0_Windows.zip` - Paquete completo para distribuir

## 🎯 Formatos Soportados

### MP4 (Video)
- Formato: `bestvideo[ext=mp4][height<=2160]+bestaudio[ext=m4a]`
- Calidad: Hasta 4K (2160p)
- Requiere: FFmpeg para merge (opcional, se busca automáticamente)

### M4A (Audio)
- Formato: `bestaudio[ext=m4a]`
- Codec: AAC de alta calidad
- Bitrate: Variable (mejor disponible)

## 🔍 Detección de FFmpeg

La aplicación busca FFmpeg automáticamente en:
- `C:\ffmpeg\bin`
- `C:\Program Files\ffmpeg\bin`
- `~\scoop\apps\ffmpeg\current\bin`
- `~\AppData\Local\Microsoft\WinGet\Links`
- `~\AppData\Local\CapCut\Apps` (recursivo)

## 📝 Notas Técnicas

### Warnings de YouTube
Los warnings sobre "JavaScript runtime" y "SABR streaming" son normales y no afectan la funcionalidad. YouTube limita ciertos formatos, pero yt-dlp encuentra alternativas automáticamente.

### Tamaño del Ejecutable
El ejecutable es grande (~48 MB) porque incluye:
- Python runtime completo
- Todas las librerías (FastAPI, yt-dlp, etc.)
- Dependencias de sistema

### Compatibilidad
- Windows 10/11 (64-bit)
- No requiere permisos de administrador
- Portable (no necesita instalación)

## 🐛 Solución de Problemas

### El ejecutable no inicia
- Verificar que no esté bloqueado por antivirus
- Ejecutar desde carpeta con permisos de escritura

### Error de descarga
- Verificar conexión a Internet
- Algunos videos pueden estar restringidos por región
- Videos privados o eliminados no se pueden descargar

### FFmpeg no encontrado
- Para MP4: Se descargará en formato pre-combinado (menor calidad)
- Para M4A: No se requiere FFmpeg

## 📄 Licencia

Proyecto de código abierto. Usa las librerías:
- FastAPI (MIT)
- yt-dlp (Unlicense)
- PyInstaller (GPL)

## 🤝 Contribuir

Para mejorar el proyecto:
1. Modifica `src/youtubedpl.py`
2. Prueba con `python src/youtubedpl.py`
3. Compila con `BUILD_RELEASE.bat`
4. Distribuye el ZIP generado

## 📞 Soporte

Para reportar bugs o sugerencias, documenta:
- Versión de Windows
- URL del video que falla
- Mensaje de error completo
- Logs de la consola
