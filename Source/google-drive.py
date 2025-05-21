#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import re
import gdown
from rich.console import Console
from rich.panel import Panel
from rich.traceback import install

install()
console = Console()

def extract_drive_id(url: str) -> str:
    """
    Extrae el ID del archivo desde una URL de Google Drive.
    """
    patterns = [
        r"https?://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)",
        r"https?://drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)",
        r"https?://drive\.google\.com/uc\?id=([a-zA-Z0-9_-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def download_file(url: str, output: str = None, resume: bool = False,
                  quiet: bool = False, speed: str = None, proxy: str = None) -> None:
    """
    Descarga un archivo desde Google Drive, asegurando que se use el ID real del archivo.
    """
    try:
        file_id = extract_drive_id(url)
        if not file_id:
            console.print(Panel(f"[bold red]No se pudo extraer el ID del archivo desde la URL:[/bold red] {url}"))
            sys.exit(1)

        file_url = f"https://drive.google.com/uc?id={file_id}"
        console.print(Panel(f"[bold green]Iniciando descarga del archivo:[/bold green] {file_url}"))

        gdown.download(url=file_url, output=output, quiet=quiet,
                       resume=resume, proxy=proxy, speed=speed, fuzzy=False)

        console.print(Panel(f"[bold cyan]Descarga completada exitosamente.[/bold cyan]"))
    except Exception as e:
        console.print(Panel(f"[bold red]Error al descargar el archivo:[/bold red] {e}"), style="red")
        sys.exit(1)

def download_folder(url: str, output: str = None, quiet: bool = False,
                    remaining_ok: bool = False, proxy: str = None, speed: str = None) -> None:
    """
    Descarga una carpeta desde Google Drive.
    """
    try:
        console.print(Panel(f"[bold green]Iniciando descarga de la carpeta:[/bold green] {url}"))
        gdown.download_folder(url=url, output=output, quiet=quiet,
                              remaining_ok=remaining_ok, proxy=proxy, speed=speed)
        console.print(Panel(f"[bold cyan]Descarga de la carpeta completada exitosamente.[/bold cyan]"))
    except Exception as e:
        console.print(Panel(f"[bold red]Error al descargar la carpeta:[/bold red] {e}"), style="red")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="CLI robusta para descargar archivos/carpetas de Google Drive.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("url_or_id", help="URL o ID de Google Drive.")
    parser.add_argument("-O", "--output", help="Ruta de salida para el archivo/carpeta descargada.")
    parser.add_argument("-c", "--continue", dest="resume", action="store_true",
                        help="Reanuda la descarga si fue interrumpida.")
    parser.add_argument("-q", "--quiet", action="store_true", help="Modo silencioso.")
    parser.add_argument("--speed", help="Límite de velocidad (e.g., '10MB').")
    parser.add_argument("--proxy", help="Proxy para la descarga.")
    parser.add_argument("--folder", action="store_true", help="Descargar una carpeta.")
    parser.add_argument("--remaining-ok", action="store_true",
                        help="Permite carpetas con más de 50 archivos.")

    args = parser.parse_args()

    if args.folder:
        download_folder(url=args.url_or_id, output=args.output, quiet=args.quiet,
                        remaining_ok=args.remaining_ok, proxy=args.proxy, speed=args.speed)
    else:
        download_file(url=args.url_or_id, output=args.output, resume=args.resume,
                      quiet=args.quiet, speed=args.speed, proxy=args.proxy)

if __name__ == "__main__":
    main()
