#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import requests
import getpass
import sys
from pathlib import Path
from typing import List, Dict
import logging

# Constantes
CONFIG_DIR = os.path.join(str(Path.home()), '.github_manager')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
LOG_FILE = os.path.join(str(Path.home()), 'github_manager.log')
GITHUB_API_URL = 'https://api.github.com'
RATE_LIMIT_PAUSE = 2
API_TIMEOUT = 10

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=LOG_FILE,
    filemode='a'
)
logger = logging.getLogger('github_fork_manager')

# Colores
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BOLD = '\033[1m'
    END = '\033[0m'

def load_credentials() -> Dict[str, str]:
    """Carga credenciales del archivo de configuración."""
    if not os.path.exists(CONFIG_FILE):
        print(f"{Colors.RED}No se encontraron credenciales guardadas.{Colors.END}")
        sys.exit(1)
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"{Colors.RED}Error al leer el archivo de credenciales: {str(e)}{Colors.END}")
        sys.exit(1)

def validate_token(username: str, token: str) -> Dict[str, str]:
    """Valida el token de GitHub."""
    headers = {'Authorization': f'token {token}'}
    try:
        r = requests.get(f"{GITHUB_API_URL}/user", headers=headers, timeout=API_TIMEOUT)
        r.raise_for_status()
        user_data = r.json()
        if user_data['login'].lower() != username.lower():
            raise Exception("El token no coincide con el usuario")
        return headers
    except Exception as e:
        print(f"{Colors.RED}Token inválido: {str(e)}{Colors.END}")
        sys.exit(1)

def fetch_forks(headers: Dict[str, str]) -> List[Dict]:
    """Obtiene todos los forks del usuario."""
    forks = []
    page = 1
    while True:
        params = {
            'page': page,
            'per_page': 100,
            'sort': 'full_name',
            'affiliation': 'owner'
        }
        r = requests.get(f"{GITHUB_API_URL}/user/repos", headers=headers, params=params, timeout=API_TIMEOUT)
        r.raise_for_status()
        repos = r.json()
        if not repos:
            break
        forks.extend([r for r in repos if r.get('fork')])
        page += 1
        time.sleep(RATE_LIMIT_PAUSE)
    return forks

def print_forks(forks: List[Dict]):
    """Imprime la lista de forks."""
    if not forks:
        print(f"{Colors.YELLOW}No tienes forks.{Colors.END}")
        return
    print(f"\n{Colors.BOLD}Forks encontrados: {len(forks)}{Colors.END}")
    for i, repo in enumerate(forks, start=1):
        print(f"{i:2d}. {repo['full_name']}  ⭐ {repo['stargazers_count']}  🍴 {repo['forks_count']}")

def parse_selection(selection: str, max_index: int) -> List[int]:
    """Parsea entradas como '1 3 5-7'."""
    result = []
    for part in selection.split():
        if '-' in part:
            start, end = map(int, part.split('-'))
            result.extend(range(start, end + 1))
        else:
            result.append(int(part))
    return [i for i in result if 1 <= i <= max_index]

def delete_forks(headers: Dict[str, str], forks: List[Dict]):
    """Permite al usuario eliminar forks."""
    print_forks(forks)
    print("\nOpciones:")
    print("1. Eliminar todos los forks")
    print("2. Eliminar forks seleccionados")
    print("3. Cancelar")
    try:
        choice = int(input("\nElige una opción (1-3): "))
        if choice == 1:
            confirm = input(f"{Colors.RED}¿Estás seguro? Esto eliminará TODOS los forks. (s/n): {Colors.END}")
            if confirm.lower() == 's':
                _delete_repos(headers, forks)
        elif choice == 2:
            selection = input("Selecciona números (ej: 1 3 5-7): ")
            indices = parse_selection(selection, len(forks))
            selected = [forks[i-1] for i in indices]
            _delete_repos(headers, selected)
        else:
            print(f"{Colors.YELLOW}Cancelado.{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}Error en la selección: {str(e)}{Colors.END}")

def _delete_repos(headers: Dict[str, str], repos: List[Dict]):
    """Elimina repositorios vía API."""
    for repo in repos:
        name = repo['full_name']
        print(f"Eliminando {name}... ", end='')
        try:
            r = requests.delete(f"{GITHUB_API_URL}/repos/{name}", headers=headers, timeout=API_TIMEOUT)
            if r.status_code == 204:
                print(f"{Colors.GREEN}✓{Colors.END}")
                logger.info(f"Eliminado fork: {name}")
            else:
                print(f"{Colors.RED}✗ ({r.status_code}){Colors.END}")
                logger.error(f"No se pudo eliminar {name}: {r.text}")
        except Exception as e:
            print(f"{Colors.RED}✗ {str(e)}{Colors.END}")
        time.sleep(RATE_LIMIT_PAUSE)

def main():
    print(f"{Colors.BOLD}🔧 GitHub Forks Manager (Termux Edition){Colors.END}")
    creds = load_credentials()
    username = creds.get('username')
    token = creds.get('token')
    if not (username and token):
        print(f"{Colors.RED}Faltan credenciales en el archivo de configuración.{Colors.END}")
        sys.exit(1)

    headers = validate_token(username, token)
    forks = fetch_forks(headers)
    delete_forks(headers, forks)

if __name__ == "__main__":
    main()
