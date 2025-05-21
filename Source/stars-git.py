#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import requests
import getpass
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging
from datetime import datetime
import argparse
from tabulate import tabulate

# Constantes
CONFIG_DIR = os.path.join(str(Path.home()), '.github_manager')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
LOG_FILE = os.path.join(str(Path.home()), 'github_manager.log')
GITHUB_API_URL = 'https://api.github.com'
RATE_LIMIT_PAUSE = 1
API_TIMEOUT = 15
USER_AGENT = 'GitHub-Stars-Manager-Termux/1.0'

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=LOG_FILE,
    filemode='a'
)
logger = logging.getLogger('github_stars_manager')

# Colores
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def check_rate_limit(headers: Dict[str, str]) -> Tuple[int, int]:
    """Verifica límite de tasa de la API de GitHub y espera si es necesario."""
    try:
        r = requests.get(f"{GITHUB_API_URL}/rate_limit", headers=headers, timeout=API_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        remaining = data['resources']['core']['remaining']
        reset_time = data['resources']['core']['reset']
        current_time = int(time.time())
        
        if remaining < 5:  # Si quedan menos de 5 solicitudes
            wait_time = reset_time - current_time + 5  # Añadimos 5 segundos de margen
            if wait_time > 0:
                print(f"{Colors.YELLOW}Límite de API casi alcanzado. Esperando {wait_time} segundos...{Colors.END}")
                time.sleep(wait_time)
                return check_rate_limit(headers)  # Verificamos de nuevo después de esperar
        
        return remaining, reset_time
    except Exception as e:
        logger.warning(f"Error al verificar límite de tasa: {str(e)}")
        return 1000, 0  # Valor por defecto conservador

def load_credentials() -> Dict[str, str]:
    """Carga credenciales del archivo de configuración."""
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        
    if not os.path.exists(CONFIG_FILE):
        print(f"{Colors.RED}No se encontraron credenciales guardadas.{Colors.END}")
        setup_credentials()
        
    try:
        with open(CONFIG_FILE, 'r') as f:
            creds = json.load(f)
            if not creds.get('username') or not creds.get('token'):
                raise ValueError("Faltan credenciales")
            return creds
    except Exception as e:
        print(f"{Colors.RED}Error al leer el archivo de credenciales: {str(e)}{Colors.END}")
        setup_credentials()
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)

def setup_credentials() -> None:
    """Configura las credenciales para la API de GitHub."""
    print(f"\n{Colors.BOLD}Configuración de GitHub Stars Manager{Colors.END}")
    print("Necesitas un token de acceso personal de GitHub con permisos 'repo' y 'delete_repo'.")
    print("Puedes crear uno en: https://github.com/settings/tokens")
    
    username = input(f"\n{Colors.CYAN}Nombre de usuario de GitHub: {Colors.END}")
    token = getpass.getpass(f"{Colors.CYAN}Token de acceso personal: {Colors.END}")
    
    # Intentamos validar antes de guardar
    headers = {'Authorization': f'token {token}', 'User-Agent': USER_AGENT}
    try:
        r = requests.get(f"{GITHUB_API_URL}/user", headers=headers, timeout=API_TIMEOUT)
        r.raise_for_status()
        user_data = r.json()
        if user_data['login'].lower() != username.lower():
            raise Exception("El token no coincide con el usuario")
        
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump({'username': username, 'token': token}, f)
        os.chmod(CONFIG_FILE, 0o600)  # Solo lectura/escritura para el propietario
        print(f"{Colors.GREEN}Credenciales guardadas correctamente.{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}Error al validar credenciales: {str(e)}{Colors.END}")
        sys.exit(1)

def validate_token(username: str, token: str) -> Dict[str, str]:
    """Valida el token de GitHub."""
    headers = {'Authorization': f'token {token}', 'User-Agent': USER_AGENT}
    try:
        r = requests.get(f"{GITHUB_API_URL}/user", headers=headers, timeout=API_TIMEOUT)
        r.raise_for_status()
        user_data = r.json()
        if user_data['login'].lower() != username.lower():
            raise Exception("El token no coincide con el usuario")
        logger.info(f"Token validado correctamente para usuario: {username}")
        return headers
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print(f"{Colors.RED}Token inválido o expirado.{Colors.END}")
        else:
            print(f"{Colors.RED}Error HTTP: {e.response.status_code}{Colors.END}")
        logger.error(f"Error validando token: {str(e)}")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"{Colors.RED}Error de conexión. Verifica tu conexión a Internet.{Colors.END}")
        logger.error("Error de conexión validando token")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}Error desconocido: {str(e)}{Colors.END}")
        logger.error(f"Error desconocido validando token: {str(e)}")
        sys.exit(1)

def fetch_starred_repos(headers: Dict[str, str], username: str, language_filter: Optional[str] = None, topic_filter: Optional[str] = None) -> List[Dict]:
    """Obtiene todos los repositorios con estrella del usuario."""
    starred_repos = []
    page = 1
    total_count = 0
    
    print(f"{Colors.BOLD}Obteniendo repositorios con estrella...{Colors.END}")
    
    try:
        while True:
            # Verificar límite de tasa
            remaining, _ = check_rate_limit(headers)
            logger.debug(f"Solicitudes API restantes: {remaining}")
            
            params = {
                'page': page,
                'per_page': 100,
                'sort': 'created',
                'direction': 'desc'
            }
            
            url = f"{GITHUB_API_URL}/users/{username}/starred"
            r = requests.get(url, headers=headers, params=params, timeout=API_TIMEOUT)
            r.raise_for_status()
            
            repos = r.json()
            if not repos:
                break
                
            # Aplicar filtros si existen
            if language_filter or topic_filter:
                filtered_repos = []
                for repo in repos:
                    if language_filter and repo.get('language') and repo.get('language').lower() != language_filter.lower():
                        continue
                        
                    if topic_filter:
                        # Si necesitamos filtrar por tópico, debemos hacer una solicitud adicional
                        topics_url = f"{GITHUB_API_URL}/repos/{repo['full_name']}/topics"
                        topics_headers = headers.copy()
                        topics_headers['Accept'] = 'application/vnd.github.mercy-preview+json'
                        
                        try:
                            topics_r = requests.get(topics_url, headers=topics_headers, timeout=API_TIMEOUT)
                            topics_r.raise_for_status()
                            topics = topics_r.json().get('names', [])
                            
                            if topic_filter.lower() not in [t.lower() for t in topics]:
                                continue
                        except Exception as e:
                            logger.warning(f"Error al obtener tópicos para {repo['full_name']}: {str(e)}")
                            continue
                            
                    filtered_repos.append(repo)
                
                starred_repos.extend(filtered_repos)
            else:
                starred_repos.extend(repos)
                
            total_count = len(starred_repos)
            progress = min(total_count, page * 100)
            print(f"\r{Colors.CYAN}Procesando... {progress} repositorios encontrados{Colors.END}", end='')
            
            # Si recibimos menos de 100 repos, hemos llegado al final
            if len(repos) < 100:
                break
                
            page += 1
            time.sleep(RATE_LIMIT_PAUSE)
    except requests.exceptions.HTTPError as e:
        print(f"\n{Colors.RED}Error HTTP al obtener repositorios: {e.response.status_code}{Colors.END}")
        logger.error(f"Error HTTP obteniendo estrellas: {str(e)}")
    except requests.exceptions.ConnectionError:
        print(f"\n{Colors.RED}Error de conexión. Verifica tu conexión a Internet.{Colors.END}")
        logger.error("Error de conexión obteniendo estrellas")
    except Exception as e:
        print(f"\n{Colors.RED}Error al obtener repositorios: {str(e)}{Colors.END}")
        logger.error(f"Error obteniendo estrellas: {str(e)}")
    
    print(f"\n{Colors.GREEN}Total de repositorios con estrella: {len(starred_repos)}{Colors.END}")
    logger.info(f"Obtenidos {len(starred_repos)} repositorios con estrella")
    return starred_repos

def print_repos_table(repos: List[Dict], show_details: bool = False):
    """Imprime la tabla de repositorios con estrella."""
    if not repos:
        print(f"\n{Colors.YELLOW}No se encontraron repositorios con estrella.{Colors.END}")
        return
        
    # Preparar los datos de la tabla
    headers = ["#", "Repositorio", "⭐", "🍴", "Lenguaje", "Actualizado"]
    if show_details:
        headers.extend(["Descripción", "Tópicos"])
        
    table_data = []
    for i, repo in enumerate(repos, start=1):
        updated_at = datetime.strptime(repo['updated_at'], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")
        language = repo.get('language', 'N/A')
        
        row = [
            i,
            repo['full_name'],
            repo['stargazers_count'],
            repo['forks_count'],
            language,
            updated_at
        ]
        
        if show_details:
            description = repo.get('description', 'Sin descripción')
            if len(description) > 50:
                description = description[:47] + "..."
                
            # Obtener tópicos si están disponibles
            topics = "N/A"
            if repo.get('topics'):
                topics = ", ".join(repo['topics'][:3])
                if len(repo['topics']) > 3:
                    topics += f" +{len(repo['topics']) - 3} más"
            
            row.extend([description, topics])
            
        table_data.append(row)
    
    print()
    print(f"{Colors.BOLD}{tabulate(table_data, headers=headers, tablefmt='pretty')}{Colors.END}")
    print(f"\nTotal: {len(repos)} repositorios")

def parse_selection(selection: str, max_index: int) -> List[int]:
    """Parsea entradas como '1 3 5-7'."""
    result = []
    try:
        for part in selection.split():
            if '-' in part:
                start, end = map(int, part.split('-'))
                result.extend(range(start, end + 1))
            else:
                result.append(int(part))
        # Filtrar índices válidos y eliminar duplicados
        valid_indices = sorted(set([i for i in result if 1 <= i <= max_index]))
        return valid_indices
    except ValueError:
        print(f"{Colors.RED}Formato de selección inválido. Usa números y rangos (ej: 1 3 5-7).{Colors.END}")
        return []

def remove_stars(headers: Dict[str, str], repos: List[Dict]):
    """Elimina estrellas de repositorios seleccionados."""
    if not repos:
        print(f"{Colors.YELLOW}No hay repositorios seleccionados.{Colors.END}")
        return
        
    print(f"\n{Colors.BOLD}Quitando estrellas de {len(repos)} repositorios:{Colors.END}")
    successful = 0
    failed = 0
    
    for i, repo in enumerate(repos, start=1):
        full_name = repo['full_name']
        print(f"  [{i}/{len(repos)}] Quitando estrella de {full_name}... ", end='', flush=True)
        
        try:
            url = f"{GITHUB_API_URL}/user/starred/{full_name}"
            r = requests.delete(url, headers=headers, timeout=API_TIMEOUT)
            
            if r.status_code in [204, 200]:
                print(f"{Colors.GREEN}✓{Colors.END}")
                logger.info(f"Estrella eliminada: {full_name}")
                successful += 1
            else:
                print(f"{Colors.RED}✗ ({r.status_code}){Colors.END}")
                logger.error(f"Error al quitar estrella de {full_name}: {r.status_code}")
                failed += 1
        except Exception as e:
            print(f"{Colors.RED}✗ Error: {str(e)}{Colors.END}")
            logger.error(f"Excepción al quitar estrella de {full_name}: {str(e)}")
            failed += 1
            
        # Pausa para respetar límites de tasa
        time.sleep(RATE_LIMIT_PAUSE)
    
    print(f"\n{Colors.GREEN}Operación completada: {successful} exitosos, {failed} fallidos{Colors.END}")

def export_starred_repos(repos: List[Dict], format_type: str = 'json'):
    """Exporta la lista de repositorios con estrella a un archivo."""
    if not repos:
        print(f"{Colors.YELLOW}No hay repositorios para exportar.{Colors.END}")
        return
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if format_type == 'json':
        filename = f"github_stars_{timestamp}.json"
        # Simplificar la estructura para exportar solo los campos relevantes
        export_data = []
        for repo in repos:
            export_data.append({
                'full_name': repo['full_name'],
                'html_url': repo['html_url'],
                'description': repo.get('description', ''),
                'language': repo.get('language', ''),
                'stargazers_count': repo['stargazers_count'],
                'forks_count': repo['forks_count'],
                'updated_at': repo['updated_at'],
                'topics': repo.get('topics', [])
            })
            
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    elif format_type == 'csv':
        import csv
        filename = f"github_stars_{timestamp}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Encabezados
            writer.writerow(['Repositorio', 'URL', 'Descripción', 'Lenguaje', 'Estrellas', 'Forks', 'Actualizado'])
            
            # Datos
            for repo in repos:
                writer.writerow([
                    repo['full_name'],
                    repo['html_url'],
                    repo.get('description', ''),
                    repo.get('language', ''),
                    repo['stargazers_count'],
                    repo['forks_count'],
                    repo['updated_at']
                ])
    
    elif format_type == 'markdown':
        filename = f"github_stars_{timestamp}.md"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# Repositorios con Estrella en GitHub\n\n")
            f.write("Exportado el: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n")
            
            f.write("| # | Repositorio | Descripción | Lenguaje | ⭐ | 🍴 |\n")
            f.write("|---|------------|-------------|----------|-----|-----|\n")
            
            for i, repo in enumerate(repos, start=1):
                description = (repo.get('description', '') or 'Sin descripción').replace('|', '\\|')
                if len(description) > 60:
                    description = description[:57] + "..."
                    
                f.write(f"| {i} | [{repo['full_name']}]({repo['html_url']}) | {description} | {repo.get('language', 'N/A')} | {repo['stargazers_count']} | {repo['forks_count']} |\n")
    
    else:
        print(f"{Colors.RED}Formato de exportación no soportado: {format_type}{Colors.END}")
        return
        
    print(f"\n{Colors.GREEN}Repositorios exportados a: {filename}{Colors.END}")
    logger.info(f"Exportados {len(repos)} repositorios a {filename}")

def filter_starred_repos(repos: List[Dict]) -> List[Dict]:
    """Permite filtrar repositorios con estrella por diferentes criterios."""
    if not repos:
        return []
        
    print(f"\n{Colors.BOLD}Filtrar repositorios:{Colors.END}")
    print("1. Por lenguaje")
    print("2. Por cantidad de estrellas")
    print("3. Por fecha de actualización")
    print("4. Sin filtro (mostrar todos)")
    
    try:
        choice = int(input("\nElige una opción (1-4): "))
        
        if choice == 1:
            # Obtener lenguajes disponibles
            languages = {}
            for repo in repos:
                lang = repo.get('language') or 'Desconocido'
                languages[lang] = languages.get(lang, 0) + 1
                
            # Mostrar lenguajes disponibles
            print("\nLenguajes disponibles:")
            for i, (lang, count) in enumerate(sorted(languages.items(), key=lambda x: x[1], reverse=True), start=1):
                print(f"{i:2d}. {lang} ({count} repos)")
                
            language = input("\nEscribe el nombre del lenguaje: ")
            return [r for r in repos if r.get('language') and r.get('language').lower() == language.lower()]
            
        elif choice == 2:
            min_stars = int(input("\nNúmero mínimo de estrellas: "))
            return [r for r in repos if r['stargazers_count'] >= min_stars]
            
        elif choice == 3:
            print("\nFiltrar por fecha de actualización (formato: YYYY-MM-DD)")
            date_str = input("Fecha mínima: ")
            try:
                date_threshold = datetime.strptime(date_str, "%Y-%m-%d")
                return [r for r in repos if datetime.strptime(r['updated_at'].split('T')[0], "%Y-%m-%d") >= date_threshold]
            except ValueError:
                print(f"{Colors.RED}Formato de fecha inválido. Mostrando todos los repositorios.{Colors.END}")
                return repos
        else:
            return repos
            
    except ValueError:
        print(f"{Colors.RED}Opción inválida. Mostrando todos los repositorios.{Colors.END}")
        return repos

def interactive_menu(headers: Dict[str, str], username: str):
    """Menú interactivo para gestionar repositorios con estrella."""
    repos = []
    
    while True:
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print(f"\n{Colors.BOLD}{Colors.BLUE}🌟 GitHub Stars Manager (Termux Edition){Colors.END}")
        print(f"Usuario: {username}")
        print(f"Repositorios cargados: {len(repos)}")
        
        print("\n1. Cargar repositorios con estrella")
        print("2. Ver repositorios con estrella")
        print("3. Filtrar repositorios")
        print("4. Quitar estrella a repositorios")
        print("5. Exportar lista de repositorios")
        print("6. Salir")
        
        try:
            choice = int(input("\nElige una opción (1-6): "))
            
            if choice == 1:
                # Cargar repositorios
                language_filter = None
                topic_filter = None
                
                if input("\n¿Deseas aplicar filtros al cargar? (s/n): ").lower() == 's':
                    if input("¿Filtrar por lenguaje? (s/n): ").lower() == 's':
                        language_filter = input("Lenguaje: ")
                    if input("¿Filtrar por tópico? (s/n): ").lower() == 's':
                        topic_filter = input("Tópico: ")
                
                repos = fetch_starred_repos(headers, username, language_filter, topic_filter)
                input("\nPresiona Enter para continuar...")
                
            elif choice == 2:
                # Ver repositorios
                if not repos:
                    print(f"{Colors.YELLOW}No hay repositorios cargados. Selecciona la opción 1 primero.{Colors.END}")
                    input("\nPresiona Enter para continuar...")
                    continue
                    
                show_details = input("¿Mostrar detalles adicionales? (s/n): ").lower() == 's'
                print_repos_table(repos, show_details)
                input("\nPresiona Enter para continuar...")
                
            elif choice == 3:
                # Filtrar repositorios
                if not repos:
                    print(f"{Colors.YELLOW}No hay repositorios cargados. Selecciona la opción 1 primero.{Colors.END}")
                    input("\nPresiona Enter para continuar...")
                    continue
                    
                filtered_repos = filter_starred_repos(repos)
                print(f"\n{Colors.GREEN}Filtro aplicado: {len(filtered_repos)} repositorios coinciden{Colors.END}")
                
                if filtered_repos:
                    print_repos_table(filtered_repos)
                    
                    # Preguntar si queremos reemplazar la lista principal
                    if input("\n¿Reemplazar lista principal con estos resultados? (s/n): ").lower() == 's':
                        repos = filtered_repos
                        print(f"{Colors.GREEN}Lista principal actualizada.{Colors.END}")
                
                input("\nPresiona Enter para continuar...")
                
            elif choice == 4:
                # Quitar estrella
                if not repos:
                    print(f"{Colors.YELLOW}No hay repositorios cargados. Selecciona la opción 1 primero.{Colors.END}")
                    input("\nPresiona Enter para continuar...")
                    continue
                    
                print_repos_table(repos)
                print("\nOpciones:")
                print("1. Quitar estrella a todos los repositorios")
                print("2. Quitar estrella a repositorios seleccionados")
                print("3. Cancelar")
                
                subchoice = int(input("\nElige una opción (1-3): "))
                
                if subchoice == 1:
                    confirm = input(f"{Colors.RED}¿Estás seguro? Esto quitará TODAS las estrellas mostradas. (s/n): {Colors.END}")
                    if confirm.lower() == 's':
                        remove_stars(headers, repos)
                elif subchoice == 2:
                    selection = input("Selecciona números (ej: 1 3 5-7): ")
                    indices = parse_selection(selection, len(repos))
                    if indices:
                        selected = [repos[i-1] for i in indices]
                        remove_stars(headers, selected)
                        
                        # Actualizar la lista principal eliminando los repos sin estrella
                        if input(f"\n¿Quieres actualizar la lista principal? (s/n): ").lower() == 's':
                            selected_ids = {repo['id'] for repo in selected}
                            repos = [repo for repo in repos if repo['id'] not in selected_ids]
                            print(f"{Colors.GREEN}Lista principal actualizada.{Colors.END}")
                else:
                    print(f"{Colors.YELLOW}Operación cancelada.{Colors.END}")
                
                input("\nPresiona Enter para continuar...")
                
            elif choice == 5:
                # Exportar lista
                if not repos:
                    print(f"{Colors.YELLOW}No hay repositorios cargados. Selecciona la opción 1 primero.{Colors.END}")
                    input("\nPresiona Enter para continuar...")
                    continue
                    
                print("\nFormato de exportación:")
                print("1. JSON")
                print("2. CSV")
                print("3. Markdown")
                
                format_choice = int(input("\nElige un formato (1-3): "))
                format_map = {1: 'json', 2: 'csv', 3: 'markdown'}
                
                if format_choice in format_map:
                    export_starred_repos(repos, format_map[format_choice])
                else:
                    print(f"{Colors.RED}Opción inválida.{Colors.END}")
                
                input("\nPresiona Enter para continuar...")
                
            elif choice == 6:
                # Salir
                print(f"\n{Colors.GREEN}¡Gracias por usar GitHub Stars Manager!{Colors.END}")
                break
                
            else:
                print(f"{Colors.RED}Opción inválida. Por favor, elige una opción del 1 al 6.{Colors.END}")
                input("\nPresiona Enter para continuar...")
                
        except ValueError:
            print(f"{Colors.RED}Por favor, ingresa un número válido.{Colors.END}")
            input("\nPresiona Enter para continuar...")
        except Exception as e:
            print(f"{Colors.RED}Error inesperado: {str(e)}{Colors.END}")
            logger.error(f"Error en menú interactivo: {str(e)}")
            input("\nPresiona Enter para continuar...")

def parse_arguments():
    """Procesa los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description='GitHub Stars Manager para Termux')
    parser.add_argument('-l', '--language', help='Filtrar por lenguaje de programación')
    parser.add_argument('-t', '--topic', help='Filtrar por tópico')
    parser.add_argument('-e', '--export', choices=['json', 'csv', 'markdown'], help='Exportar repositorios (formato)')
    parser.add_argument('-i', '--interactive', action='store_true', help='Modo interactivo (por defecto)')
    
    return parser.parse_args()

def main():
    """Función principal."""
    try:
        args = parse_arguments()
        
        # Cargar y validar credenciales
        creds = load_credentials()
        username = creds.get('username')
        token = creds.get('token')
        
        if not (username and token):
            print(f"{Colors.RED}Faltan credenciales en el archivo de configuración.{Colors.END}")
            sys.exit(1)
            
        headers = validate_token(username, token)
        
        # Si no hay argumentos específicos o se solicitó modo interactivo
        if args.interactive or (not args.language and not args.topic and not args.export):
            interactive_menu(headers, username)
        else:
            # Procesar en modo no interactivo
            repos = fetch_starred_repos(headers, username, args.language, args.topic)
            
            if repos:
                print_repos_table(repos)
                
                if args.export:
                    export_starred_repos(repos, args.export)
    
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Operación cancelada por el usuario.{Colors.END}")
        logger.info("Programa terminado por interrupción del usuario")
    except Exception as e:
        print(f"\n{Colors.RED}Error inesperado: {str(e)}{Colors.END}")
        logger.error(f"Error general: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
