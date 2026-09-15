"""Abre un navegador temporal y aislado para iniciar sesión en YouTube.

Se ejecuta manualmente como el perfil `youtube-login` de Docker Compose. La persona ingresa
sus credenciales directamente en el navegador noVNC; este proceso nunca las lee ni las imprime.
El perfil persistente se comparte después con yt-dlp en modo de solo lectura.
"""
import os
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def main() -> None:
    options = Options()
    options.add_argument("--user-data-dir=/home/seluser/chrome-profile")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")

    driver = webdriver.Remote(
        command_executor=os.environ.get("SELENIUM_URL", "http://youtube-selenium:4444/wd/hub"),
        options=options,
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
