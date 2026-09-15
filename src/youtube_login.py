"""Abre un navegador temporal y aislado para iniciar sesión en YouTube.

Se ejecuta manualmente como el perfil `youtube-login` de Docker Compose. La persona ingresa
sus credenciales directamente en el navegador noVNC; este proceso nunca las lee ni las imprime.
El perfil persistente se comparte después con yt-dlp en modo de solo lectura.
"""
import os
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from urllib3.exceptions import MaxRetryError


def _connect_with_retry(command_executor: str, options: Options, attempts: int = 30, delay: float = 2.0):
    """Reintenta la conexión al Grid de Selenium.

    `docker compose up` con `depends_on: condition: service_started` solo espera a que el
    contenedor arranque, no a que su servidor HTTP interno esté listo -- Selenium tarda unos
    segundos en levantarlo, así que el primer intento casi siempre choca con connection refused.
    """
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return webdriver.Remote(command_executor=command_executor, options=options)
        except MaxRetryError as exc:
            last_error = exc
            print(f"Selenium aún no responde (intento {attempt}/{attempts}), reintentando...", flush=True)
            time.sleep(delay)
    raise RuntimeError(f"No se pudo conectar al Grid de Selenium tras {attempts} intentos") from last_error


def main() -> None:
    options = Options()
    options.add_argument("--user-data-dir=/home/seluser/chrome-profile")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")

    driver = _connect_with_retry(
        os.environ.get("SELENIUM_URL", "http://youtube-selenium:4444/wd/hub"),
        options,
    )
    try:
        driver.get("https://www.youtube.com/")
        print("YouTube login browser ready; waiting for the user to finish sign-in", flush=True)
        while True:
            time.sleep(30)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
