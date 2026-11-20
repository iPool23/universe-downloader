"""Versión e identidad de la app.

De aquí leen la versión el instalador (build.ps1), el actualizador y la interfaz:
para publicar una versión nueva solo se cambia APP_VERSION.
"""

APP_NAME = "Universe Downloader"
APP_VERSION = "3.1.1"

# AppUserModelID de Windows: el mismo que declaran los accesos directos del instalador,
# para que la barra de tareas agrupe la ventana con su ícono.
APP_ID = "iPool23.UniverseDownloader"

# GitHub Releases de este repositorio: instalador + SHA256SUMS.txt por versión.
UPDATES_REPO = "iPool23/universe-downloader"
