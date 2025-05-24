#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import requests
import getpass
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
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
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def setup_config_directory():
    """Crea el directorio de configuración si no existe."""
    os.makedirs(CONFIG_DIR, exist_ok=True)

def load_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Carga credenciales del archivo de configuración."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                credentials = json.load(f)
            return credentials.get('username'), credentials.get('token')
        return None, None
    except Exception as e:
        logger.error(f"Error al cargar credenciales: {str(e)}")
        print(f"{Colors.RED}Error al cargar credenciales: {str(e)}{Colors.END}")
        return None, None

def save_credentials(username: str, token: str) -> bool:
    """Guarda las credenciales en el archivo de configuración."""
    credentials = {
        'username': username,
        'token': token,
        'last_used': time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(credentials, f, indent=2)
        os.chmod(CONFIG_FILE, 0o600)  # Solo lectura/escritura para el propietario
        logger.info(f"Credenciales guardadas para el usuario {username}")
        print(f"{Colors.GREEN}✓ Credenciales guardadas en {CONFIG_FILE}{Colors.END}")
        return True
    except Exception as e:
        logger.error(f"Error al guardar credenciales: {str(e)}")
        print(f"{Colors.RED}Error al guardar credenciales: {str(e)}{Colors.END}")
        return False

def get_user_credentials() -> Tuple[str, str]:
    """Solicita al usuario sus credenciales de GitHub."""
    print(f"\n{Colors.HEADER}Configuración de credenciales de GitHub{Colors.END}")
    print(f"{Colors.YELLOW}No se encontraron credenciales guardadas.{Colors.END}")
    print(f"{Colors.YELLOW}Para crear un token de acceso personal, visita:{Colors.END}")
    print(f"{Colors.YELLOW}https://github.com/settings/tokens{Colors.END}")
    print(f"{Colors.YELLOW}Asegúrate de que el token tenga permisos 'repo' para eliminar repositorios.{Colors.END}\n")
    
    username = input(f"{Colors.BOLD}Usuario de GitHub: {Colors.END}").strip()
    token = getpass.getpass(f"{Colors.BOLD}Token de GitHub: {Colors.END}").strip()
    
    if not username or not token:
        print(f"{Colors.RED}Error: Usuario y token son obligatorios.{Colors.END}")
        sys.exit(1)
    
    return username, token

def validate_token(username: str, token: str) -> Dict[str, str]:
    """Valida el token de GitHub."""
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    try:
        print(f"{Colors.YELLOW}Validando credenciales...{Colors.END}")
        r = requests.get(f"{GITHUB_API_URL}/user", headers=headers, timeout=API_TIMEOUT)
        r.raise_for_status()
        
        user_data = r.json()
        if user_data['login'].lower() != username.lower():
            raise Exception(f"El token no pertenece al usuario '{username}'. Pertenece a '{user_data['login']}'")
        
        print(f"{Colors.GREEN}✓ Credenciales validadas correctamente para {username}{Colors.END}")
        logger.info(f"Credenciales validadas correctamente para el usuario {username}")
        return headers
        
    except requests.exceptions.RequestException as e:
        error_message = f"Error de conexión: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            if e.response.status_code == 401:
                error_message = "Token inválido o caducado"
            elif e.response.status_code == 403:
                error_message = "Acceso denegado. Verifica los permisos del token"
        
        logger.error(f"Error de validación para el usuario {username}: {error_message}")
        print(f"{Colors.RED}Error de validación: {error_message}{Colors.END}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error inesperado en validación: {str(e)}")
        print(f"{Colors.RED}Error: {str(e)}{Colors.END}")
        sys.exit(1)

def fetch_forks(headers: Dict[str, str]) -> List[Dict]:
    """Obtiene todos los forks del usuario."""
    print(f"{Colors.YELLOW}Obteniendo lista de forks...{Colors.END}")
    forks = []
    page = 1
    
    while True:
        try:
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
                
            # Filtrar solo los forks
            page_forks = [repo for repo in repos if repo.get('fork')]
            forks.extend(page_forks)
            
            page += 1
            time.sleep(RATE_LIMIT_PAUSE)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al obtener repositorios (página {page}): {str(e)}")
            print(f"{Colors.RED}Error al obtener repositorios: {str(e)}{Colors.END}")
            sys.exit(1)
    
    logger.info(f"Se encontraron {len(forks)} forks")
    return forks

def print_forks(forks: List[Dict]):
    """Imprime la lista de forks."""
    if not forks:
        print(f"{Colors.YELLOW}No tienes forks para mostrar.{Colors.END}")
        return
    
    print(f"\n{Colors.BOLD}Forks encontrados: {len(forks)}{Colors.END}")
    print(f"{Colors.BOLD}{'#':<3} {'Nombre del repositorio':<50} {'⭐':<6} {'🍴':<6}{Colors.END}")
    print("-" * 70)
    
    for i, repo in enumerate(forks, start=1):
        print(f"{i:2d}. {repo['full_name']:<50} {repo['stargazers_count']:<6} {repo['forks_count']:<6}")

def parse_selection(selection: str, max_index: int) -> List[int]:
    """Parsea entradas como '1 3 5-7'."""
    if not selection.strip():
        return []
    
    result = []
    try:
        for part in selection.split():
            if '-' in part:
                start, end = map(int, part.split('-'))
                if start > end:
                    start, end = end, start
                result.extend(range(start, end + 1))
            else:
                result.append(int(part))
    except ValueError:
        raise ValueError("Formato de selección inválido. Use números separados por espacios o rangos como '1-5'")
    
    # Filtrar índices válidos
    valid_indices = [i for i in result if 1 <= i <= max_index]
    if len(valid_indices) != len(result):
        invalid_count = len(result) - len(valid_indices)
        print(f"{Colors.YELLOW}Advertencia: Se ignoraron {invalid_count} índices inválidos.{Colors.END}")
    
    return valid_indices

def delete_forks(headers: Dict[str, str], forks: List[Dict]):
    """Permite al usuario eliminar forks."""
    if not forks:
        print(f"{Colors.YELLOW}No hay forks para eliminar.{Colors.END}")
        return
    
    print_forks(forks)
    
    print(f"\n{Colors.BOLD}Opciones de eliminación:{Colors.END}")
    print("1. Eliminar todos los forks")
    print("2. Eliminar forks seleccionados")
    print("3. Cancelar y salir")
    
    try:
        choice = input(f"\n{Colors.BOLD}Elige una opción (1-3): {Colors.END}").strip()
        
        if choice == '1':
            print(f"\n{Colors.RED}¡ADVERTENCIA!{Colors.END}")
            print(f"{Colors.RED}Esto eliminará TODOS los {len(forks)} forks de forma permanente.{Colors.END}")
            confirm = input(f"{Colors.RED}¿Estás absolutamente seguro? Escribe 'ELIMINAR' para confirmar: {Colors.END}")
            
            if confirm == 'ELIMINAR':
                _delete_repos(headers, forks)
            else:
                print(f"{Colors.YELLOW}Operación cancelada.{Colors.END}")
                
        elif choice == '2':
            print(f"\n{Colors.BOLD}Selecciona los forks a eliminar{Colors.END}")
            print(f"{Colors.YELLOW}Ejemplos: '1 3 5' o '1-5 8 10-12'{Colors.END}")
            selection = input(f"{Colors.BOLD}Selección: {Colors.END}").strip()
            
            if selection:
                try:
                    indices = parse_selection(selection, len(forks))
                    if indices:
                        selected = [forks[i-1] for i in indices]
                        print(f"\n{Colors.YELLOW}Forks seleccionados para eliminar:{Colors.END}")
                        for repo in selected:
                            print(f"  - {repo['full_name']}")
                        
                        confirm = input(f"\n{Colors.RED}¿Confirmas la eliminación de {len(selected)} fork(s)? (s/n): {Colors.END}")
                        if confirm.lower() == 's':
                            _delete_repos(headers, selected)
                        else:
                            print(f"{Colors.YELLOW}Operación cancelada.{Colors.END}")
                    else:
                        print(f"{Colors.YELLOW}No se seleccionaron forks válidos.{Colors.END}")
                except ValueError as e:
                    print(f"{Colors.RED}Error en la selección: {str(e)}{Colors.END}")
            else:
                print(f"{Colors.YELLOW}No se ingresó ninguna selección.{Colors.END}")
                
        elif choice == '3':
            print(f"{Colors.YELLOW}Operación cancelada.{Colors.END}")
        else:
            print(f"{Colors.RED}Opción no válida.{Colors.END}")
            
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Operación cancelada por el usuario.{Colors.END}")
    except Exception as e:
        logger.error(f"Error en delete_forks: {str(e)}")
        print(f"{Colors.RED}Error inesperado: {str(e)}{Colors.END}")

def _delete_repos(headers: Dict[str, str], repos: List[Dict]):
    """Elimina repositorios vía API."""
    print(f"\n{Colors.BOLD}Iniciando eliminación de {len(repos)} repositorio(s)...{Colors.END}")
    
    success_count = 0
    error_count = 0
    
    for i, repo in enumerate(repos, 1):
        name = repo['full_name']
        print(f"[{i}/{len(repos)}] Eliminando {name}... ", end='', flush=True)
        
        try:
            r = requests.delete(f"{GITHUB_API_URL}/repos/{name}", headers=headers, timeout=API_TIMEOUT)
            
            if r.status_code == 204:
                print(f"{Colors.GREEN}✓{Colors.END}")
                logger.info(f"Eliminado fork: {name}")
                success_count += 1
            else:
                print(f"{Colors.RED}✗ (Código: {r.status_code}){Colors.END}")
                logger.error(f"No se pudo eliminar {name}: HTTP {r.status_code} - {r.text}")
                error_count += 1
                
        except requests.exceptions.RequestException as e:
            print(f"{Colors.RED}✗ Error de conexión{Colors.END}")
            logger.error(f"Error de conexión al eliminar {name}: {str(e)}")
            error_count += 1
        except Exception as e:
            print(f"{Colors.RED}✗ Error inesperado{Colors.END}")
            logger.error(f"Error inesperado al eliminar {name}: {str(e)}")
            error_count += 1
        
        # Pausa para evitar límites de API
        if i < len(repos):  # No pausar después del último
            time.sleep(RATE_LIMIT_PAUSE)
    
    # Resumen de resultados
    print(f"\n{Colors.BOLD}Resumen de eliminación:{Colors.END}")
    print(f"{Colors.GREEN}✓ Exitosos: {success_count}{Colors.END}")
    if error_count > 0:
        print(f"{Colors.RED}✗ Con errores: {error_count}{Colors.END}")
    
    if success_count > 0:
        print(f"\n{Colors.GREEN}Se eliminaron {success_count} fork(s) exitosamente.{Colors.END}")
    if error_count > 0:
        print(f"{Colors.RED}Hubo {error_count} error(es). Revisa el archivo de log para más detalles.{Colors.END}")

def main():
    """Función principal."""
    print(f"{Colors.BOLD}{Colors.BLUE}🔧 GitHub Forks Manager (Termux Edition){Colors.END}")
    print(f"{Colors.YELLOW}Versión 2.0 - Gestión automática de configuración{Colors.END}\n")
    
    try:
        # Configurar directorio de configuración
        setup_config_directory()
        
        # Cargar o solicitar credenciales
        username, token = load_credentials()
        
        if not username or not token:
            # No hay credenciales guardadas, solicitarlas
            username, token = get_user_credentials()
            
            # Validar las nuevas credenciales
            headers = validate_token(username, token)
            
            # Guardar credenciales si son válidas
            if save_credentials(username, token):
                print(f"{Colors.GREEN}Las credenciales se han guardado para futuros usos.{Colors.END}")
        else:
            # Validar credenciales existentes
            print(f"{Colors.GREEN}Credenciales encontradas para el usuario: {username}{Colors.END}")
            headers = validate_token(username, token)
        
        # Obtener y gestionar forks
        forks = fetch_forks(headers)
        delete_forks(headers, forks)
        
    except KeyboardInterrupt:
        print(f"\n\n{Colors.GREEN}¡Hasta pronto!{Colors.END}")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error crítico en main: {str(e)}")
        print(f"\n{Colors.RED}Error crítico: {str(e)}{Colors.END}")
        print(f"{Colors.YELLOW}Revisa el archivo de log en {LOG_FILE} para más detalles.{Colors.END}")
        sys.exit(1)

if __name__ == "__main__":
    main()
