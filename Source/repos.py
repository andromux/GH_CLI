#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import getpass
import requests
from pathlib import Path
import sys
import time
import logging
from typing import Dict, List, Tuple, Optional, Any, Union
from functools import lru_cache
from dataclasses import dataclass
from enum import Enum
import signal

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=os.path.join(str(Path.home()), 'github_manager.log'),
    filemode='a'
)
logger = logging.getLogger('/data/data/com.termux/files/home/github_manager')

# Definición de colores ANSI para terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

# Definición de constantes
GITHUB_API_URL = 'https://api.github.com'
CONFIG_DIR = os.path.join(str(Path.home()), '.github_manager')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
API_TIMEOUT = 10  # segundos
RATE_LIMIT_PAUSE = 2  # segundos entre peticiones para evitar límites de API

# Definición de tipos de repositorios
class RepoType(Enum):
    PUBLIC = "público"
    PRIVATE = "privado"
    FORK = "fork"

@dataclass
class Repository:
    """Clase para almacenar información de repositorios."""
    name: str
    full_name: str
    private: bool
    fork: bool
    stars: int
    forks: int
    visibility: str
    
    @classmethod
    def from_api(cls, repo_data: Dict[str, Any]) -> 'Repository':
        """Crea un objeto Repository desde los datos de la API de GitHub."""
        return cls(
            name=repo_data['name'],
            full_name=repo_data['full_name'],
            private=repo_data['private'],
            fork=repo_data['fork'],
            stars=repo_data['stargazers_count'],
            forks=repo_data['forks_count'],
            visibility="privado" if repo_data['private'] else "público"
        )

class GitHubManager:
    """Clase principal para gestionar los repositorios de GitHub."""
    
    def __init__(self):
        self.username = None
        self.token = None
        self.headers = None
        self.repositories = {
            RepoType.PUBLIC: [],
            RepoType.PRIVATE: [],
            RepoType.FORK: []
        }
        
        # Asegurar que existe el directorio de configuración
        os.makedirs(CONFIG_DIR, exist_ok=True)
        
        # Configurar manejador de señales para salida controlada
        signal.signal(signal.SIGINT, self._handle_exit)
    
    def _handle_exit(self, signum, frame):
        """Maneja la salida controlada del programa."""
        print(f"\n\n{Colors.GREEN}¡Hasta pronto!{Colors.END}")
        sys.exit(0)
        
    def clear_screen(self):
        """Limpia la pantalla de la terminal."""
        os.system('clear' if os.name == 'posix' else 'cls')
        
    def print_banner(self):
        """Muestra el banner de la aplicación."""
        self.clear_screen()
        print(f"{Colors.BOLD}{Colors.BLUE}╔══════════════════════════════════════════════════════╗{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}║                GITHUB PRIVACY MANAGER                ║{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}╚══════════════════════════════════════════════════════╝{Colors.END}")
        print(f"{Colors.YELLOW}Desarrollado para uso en Termux | Versión 2.0{Colors.END}\n")
        
    def load_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """Carga las credenciales guardadas."""
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
            
    def save_credentials(self, username: str, token: str) -> bool:
        """Guarda las credenciales en el archivo de configuración."""
        credentials = {
            'username': username,
            'token': token,
            'last_used': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(credentials, f)
            os.chmod(CONFIG_FILE, 0o600)  # Solo lectura/escritura para el propietario
            logger.info(f"Credenciales guardadas para el usuario {username}")
            print(f"{Colors.GREEN}✓ Credenciales guardadas en {CONFIG_FILE}{Colors.END}")
            return True
        except Exception as e:
            logger.error(f"Error al guardar credenciales: {str(e)}")
            print(f"{Colors.RED}Error al guardar credenciales: {str(e)}{Colors.END}")
            return False
            
    def validate_credentials(self, username: str, token: str) -> bool:
        """Valida las credenciales con la API de GitHub."""
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        try:
            response = requests.get(
                f'{GITHUB_API_URL}/user', 
                headers=headers, 
                timeout=API_TIMEOUT
            )
            response.raise_for_status()
            
            # Verificar que el usuario coincide
            user_data = response.json()
            if user_data['login'].lower() != username.lower():
                logger.warning(f"El token proporcionado no pertenece al usuario {username}")
                print(f"{Colors.RED}Error: El token proporcionado no pertenece al usuario {username}.{Colors.END}")
                return False
                
            # Guardar los headers para uso posterior
            self.headers = headers
            self.username = username
            self.token = token
            
            logger.info(f"Credenciales validadas correctamente para el usuario {username}")
            print(f"{Colors.GREEN}✓ Credenciales validadas correctamente.{Colors.END}")
            return True
        except requests.exceptions.RequestException as e:
            error_message = f"{Colors.RED}Error al validar credenciales: {str(e)}{Colors.END}"
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 401:
                    error_message = f"{Colors.RED}Error: Token inválido o caducado.{Colors.END}"
                    logger.error(f"Token inválido para el usuario {username}")
                elif e.response.status_code == 403:
                    error_message = f"{Colors.RED}Error: Acceso denegado. Verifica los permisos del token.{Colors.END}"
                    logger.error(f"Permisos insuficientes para el token del usuario {username}")
            print(error_message)
            return False
            
    def get_user_credentials(self) -> Tuple[str, str]:
        """Solicita al usuario sus credenciales de GitHub."""
        print(f"{Colors.HEADER}Configuración de credenciales de GitHub{Colors.END}")
        print(f"{Colors.YELLOW}Nota: Para crear un token de acceso personal, visita:{Colors.END}")
        print(f"{Colors.YELLOW}https://github.com/settings/tokens{Colors.END}")
        print(f"{Colors.YELLOW}Asegúrate de que el token tenga permisos 'repo' para modificar la visibilidad.{Colors.END}\n")
        
        username = input(f"{Colors.BOLD}Usuario de GitHub: {Colors.END}")
        token = getpass.getpass(f"{Colors.BOLD}Token de GitHub: {Colors.END}")
        
        return username, token
            
    def fetch_repositories(self) -> bool:
        """Obtiene todos los repositorios del usuario y los clasifica."""
        if not (self.username and self.headers):
            logger.error("Intento de obtener repositorios sin credenciales válidas")
            return False
            
        try:
            # Reiniciar las listas de repositorios
            self.repositories = {
                RepoType.PUBLIC: [],
                RepoType.PRIVATE: [],
                RepoType.FORK: []
            }
            
            print(f"{Colors.BOLD}Obteniendo lista de repositorios...{Colors.END}")
            
            # Obtener los repositorios paginados
            page = 1
            total_repos = []
            
            while True:
                try:
                    response = requests.get(
                        f'{GITHUB_API_URL}/user/repos', 
                        headers=self.headers, 
                        params={
                            'page': page,
                            'per_page': 100,
                            'sort': 'full_name',
                            'affiliation': 'owner,collaborator,organization_member'
                        },
                        timeout=API_TIMEOUT
                    )
                    response.raise_for_status()
                    repos = response.json()
                    
                    if not repos:  # No hay más repositorios
                        break
                        
                    total_repos.extend(repos)
                    page += 1
                    
                    # Pausar brevemente para evitar límites de API
                    time.sleep(RATE_LIMIT_PAUSE)
                    
                except requests.exceptions.RequestException as e:
                    logger.error(f"Error en la petición de repositorios (página {page}): {str(e)}")
                    if hasattr(e, 'response') and e.response:
                        logger.error(f"Respuesta de la API: {e.response.text}")
                    print(f"{Colors.RED}Error al obtener repositorios: {str(e)}{Colors.END}")
                    return False
            
            # Clasificar los repositorios
            for repo_data in total_repos:
                repo = Repository.from_api(repo_data)
                
                if repo.fork:
                    self.repositories[RepoType.FORK].append(repo)
                elif repo.private:
                    self.repositories[RepoType.PRIVATE].append(repo)
                else:
                    self.repositories[RepoType.PUBLIC].append(repo)
            
            logger.info(f"Obtenidos {len(total_repos)} repositorios para el usuario {self.username}")
            return True
            
        except Exception as e:
            logger.error(f"Error inesperado al obtener repositorios: {str(e)}")
            print(f"{Colors.RED}Error inesperado al obtener repositorios: {str(e)}{Colors.END}")
            return False
            
    def display_repositories(self) -> bool:
        """Muestra los repositorios clasificados."""
        # Calcular totales
        total_public = len(self.repositories[RepoType.PUBLIC])
        total_private = len(self.repositories[RepoType.PRIVATE])
        total_fork = len(self.repositories[RepoType.FORK])
        total_repos = total_public + total_private + total_fork
        
        # Si no hay repositorios, mostrar mensaje
        if total_repos == 0:
            print(f"{Colors.YELLOW}No se encontraron repositorios para el usuario {self.username}.{Colors.END}")
            return False
            
        # Mostrar estadísticas
        print(f"\n{Colors.BOLD}Total de repositorios: {total_repos}{Colors.END}")
        print(f"{Colors.BOLD}Públicos: {total_public} | Privados: {total_private} | Forks: {total_fork}{Colors.END}\n")
        
        # Función para mostrar una lista de repositorios
        def print_repo_list(repos: List[Repository], status_color: str, status_text: str):
            if not repos:
                return
                
            for i, repo in enumerate(repos):
                print(f"{Colors.BOLD}{i+1:3d}{Colors.END}. {repo.name:<40} "
                      f"[{status_color}{status_text}{Colors.END}] "
                      f"🌟 {repo.stars:<4} "
                      f"🍴 {repo.forks}")
            print()
        
        # Mostrar repositorios públicos
        if total_public > 0:
            print(f"{Colors.BOLD}{Colors.BLUE}=== REPOSITORIOS PÚBLICOS ==={Colors.END}")
            print_repo_list(
                self.repositories[RepoType.PUBLIC], 
                Colors.GREEN, 
                "PÚBLICO"
            )
        
        # Mostrar repositorios privados
        if total_private > 0:
            print(f"{Colors.BOLD}{Colors.BLUE}=== REPOSITORIOS PRIVADOS ==={Colors.END}")
            print_repo_list(
                self.repositories[RepoType.PRIVATE], 
                Colors.RED, 
                "PRIVADO"
            )
        
        # Mostrar repositorios fork
        if total_fork > 0:
            print(f"{Colors.BOLD}{Colors.BLUE}=== REPOSITORIOS FORK ==={Colors.END}")
            print_repo_list(
                self.repositories[RepoType.FORK], 
                Colors.YELLOW, 
                "FORK"
            )
            
        return True
    
    def change_repository_visibility(
        self, 
        repo_name: str, 
        make_private: bool
    ) -> Tuple[bool, str]:
        """Cambia la visibilidad de un repositorio."""
        new_visibility = 'private' if make_private else 'public'
        data = {'visibility': new_visibility}
        
        try:
            response = requests.patch(
                f'{GITHUB_API_URL}/repos/{self.username}/{repo_name}',
                json=data,
                headers=self.headers,
                timeout=API_TIMEOUT
            )
            response.raise_for_status()
            
            # Registrar la acción
            action = "privado" if make_private else "público"
            logger.info(f"Repositorio '{repo_name}' cambiado a {action}")
            
            return True, new_visibility
        except requests.exceptions.RequestException as e:
            error_msg = f"Error al cambiar la visibilidad de '{repo_name}': {str(e)}"
            if hasattr(e, 'response') and e.response:
                error_msg += f"\nRespuesta de la API: {e.response.text}"
            
            logger.error(error_msg)
            return False, error_msg
    
    def manage_visibility(self):
        """Gestiona los cambios de visibilidad de los repositorios."""
        # Verificar si hay repositorios disponibles
        if not self.fetch_repositories():
            input(f"\n{Colors.BOLD}Presiona Enter para continuar...{Colors.END}")
            return
            
        self.display_repositories()
        
        # Mostrar opciones de gestión
        print(f"\n{Colors.BOLD}Opciones de gestión de privacidad:{Colors.END}")
        print("1. Hacer repositorios públicos → privados")
        print("2. Hacer repositorios privados → públicos")
        print("3. Volver al menú principal")
        
        try:
            option = int(input(f"\n{Colors.BOLD}Selecciona una opción (1-3): {Colors.END}"))
            
            if option == 1:
                self._manage_public_to_private()
            elif option == 2:
                self._manage_private_to_public()
            elif option == 3:
                return
            else:
                print(f"{Colors.RED}Opción no válida.{Colors.END}")
                
        except ValueError:
            print(f"{Colors.RED}Por favor, ingresa un número válido.{Colors.END}")
            
        input(f"\n{Colors.BOLD}Presiona Enter para continuar...{Colors.END}")
    
    def _manage_public_to_private(self):
        """Gestiona el cambio de repositorios públicos a privados."""
        public_repos = self.repositories[RepoType.PUBLIC]
        
        if not public_repos:
            print(f"{Colors.YELLOW}No hay repositorios públicos para modificar.{Colors.END}")
            return
            
        print(f"\n{Colors.BOLD}Opciones:{Colors.END}")
        print("1. Hacer privados todos los repositorios públicos")
        print("2. Seleccionar repositorios específicos para hacer privados")
        print("3. Volver al menú anterior")
        
        try:
            option = int(input(f"\n{Colors.BOLD}Selecciona una opción (1-3): {Colors.END}"))
            
            if option == 1:
                # Hacer todos privados
                confirm = input(f"{Colors.RED}¿Estás seguro que deseas hacer TODOS los repositorios públicos privados? (s/n): {Colors.END}")
                if confirm.lower() == 's':
                    self._batch_change_visibility(public_repos, True)
            
            elif option == 2:
                # Selección específica
                print(f"\n{Colors.BOLD}Ingresa los números de los repositorios que deseas hacer privados{Colors.END}")
                print(f"{Colors.YELLOW}(separados por espacios, por ejemplo: 1 3 5){Colors.END}")
                
                selection = input(f"\n{Colors.BOLD}Selección: {Colors.END}")
                self._process_selection(selection, public_repos, True)
            
            elif option == 3:
                return
                
            else:
                print(f"{Colors.RED}Opción no válida.{Colors.END}")
                
        except ValueError:
            print(f"{Colors.RED}Por favor, ingresa un número válido.{Colors.END}")
    
    def _manage_private_to_public(self):
        """Gestiona el cambio de repositorios privados a públicos."""
        private_repos = self.repositories[RepoType.PRIVATE]
        
        if not private_repos:
            print(f"{Colors.YELLOW}No hay repositorios privados para modificar.{Colors.END}")
            return
            
        print(f"\n{Colors.BOLD}Opciones:{Colors.END}")
        print("1. Hacer públicos todos los repositorios privados")
        print("2. Seleccionar repositorios específicos para hacer públicos")
        print("3. Volver al menú anterior")
        
        try:
            option = int(input(f"\n{Colors.BOLD}Selecciona una opción (1-3): {Colors.END}"))
            
            if option == 1:
                # Hacer todos públicos
                confirm = input(f"{Colors.RED}¿Estás seguro que deseas hacer TODOS los repositorios privados públicos? (s/n): {Colors.END}")
                confirm2 = input(f"{Colors.RED}¡ADVERTENCIA! Esto hará que tu código sea visible para todos. Confirma nuevamente (s/n): {Colors.END}")
                if confirm.lower() == 's' and confirm2.lower() == 's':
                    self._batch_change_visibility(private_repos, False)
            
            elif option == 2:
                # Selección específica
                print(f"\n{Colors.BOLD}Ingresa los números de los repositorios que deseas hacer públicos{Colors.END}")
                print(f"{Colors.YELLOW}(separados por espacios, por ejemplo: 1 3 5){Colors.END}")
                print(f"{Colors.RED}¡ADVERTENCIA! Esto hará que tu código sea visible para todos.{Colors.END}")
                
                selection = input(f"\n{Colors.BOLD}Selección: {Colors.END}")
                self._process_selection(selection, private_repos, False)
            
            elif option == 3:
                return
                
            else:
                print(f"{Colors.RED}Opción no válida.{Colors.END}")
                
        except ValueError:
            print(f"{Colors.RED}Por favor, ingresa un número válido.{Colors.END}")
    
    def _batch_change_visibility(self, repos: List[Repository], make_private: bool):
        """Cambia la visibilidad de múltiples repositorios."""
        action_text = "privado" if make_private else "público"
        success_count = 0
        error_count = 0
        
        for repo in repos:
            print(f"Cambiando '{repo.name}' a {action_text}... ", end="", flush=True)
            success, result = self.change_repository_visibility(repo.name, make_private)
            
            if success:
                print(f"{Colors.GREEN}✓{Colors.END}")
                success_count += 1
            else:
                print(f"{Colors.RED}✗{Colors.END}")
                print(f"{Colors.RED}{result}{Colors.END}")
                error_count += 1
                
            # Pausar brevemente para evitar límites de API
            time.sleep(RATE_LIMIT_PAUSE)
        
        print(f"\n{Colors.GREEN}Completado: {success_count} repositorios cambiados a {action_text}s.{Colors.END}")
        if error_count > 0:
            print(f"{Colors.RED}{error_count} repositorios no pudieron ser modificados.{Colors.END}")
    
    def _process_selection(self, selection: str, repos: List[Repository], make_private: bool):
        """Procesa la selección de repositorios específicos."""
        selected_indices = []
        
        # Procesar la selección (admite rangos como "1-5")
        for part in selection.split():
            if '-' in part:
                try:
                    start, end = map(int, part.split('-'))
                    selected_indices.extend(range(start, end + 1))
                except ValueError:
                    # Ignorar partes no válidas
                    pass
            else:
                try:
                    selected_indices.append(int(part))
                except ValueError:
                    # Ignorar partes no válidas
                    pass
        
        if not selected_indices:
            print(f"{Colors.YELLOW}No se seleccionó ningún repositorio válido.{Colors.END}")
            return
            
        action_text = "privado" if make_private else "público"
        success_count = 0
        error_count = 0
        
        for idx in selected_indices:
            if 1 <= idx <= len(repos):
                repo = repos[idx-1]
                print(f"Cambiando '{repo.name}' a {action_text}... ", end="", flush=True)
                success, result = self.change_repository_visibility(repo.name, make_private)
                
                if success:
                    print(f"{Colors.GREEN}✓{Colors.END}")
                    success_count += 1
                else:
                    print(f"{Colors.RED}✗{Colors.END}")
                    print(f"{Colors.RED}{result}{Colors.END}")
                    error_count += 1
                    
                # Pausar brevemente para evitar límites de API
                time.sleep(RATE_LIMIT_PAUSE)
            else:
                print(f"{Colors.RED}Índice {idx} fuera de rango, ignorando.{Colors.END}")
        
        print(f"\n{Colors.GREEN}Completado: {success_count} repositorios cambiados a {action_text}s.{Colors.END}")
        if error_count > 0:
            print(f"{Colors.RED}{error_count} repositorios no pudieron ser modificados.{Colors.END}")
    
    def run(self):
        """Ejecuta el programa principal."""
        # Intenta cargar credenciales guardadas
        self.username, self.token = self.load_credentials()
        
        # Si no hay credenciales o son inválidas, solicitar nuevas
        if not (self.username and self.token and self.validate_credentials(self.username, self.token)):
            print(f"{Colors.YELLOW}Se requieren credenciales de GitHub válidas.{Colors.END}")
            self.username, self.token = self.get_user_credentials()
            
            if self.validate_credentials(self.username, self.token):
                self.save_credentials(self.username, self.token)
            else:
                print(f"{Colors.RED}No se pudieron validar las credenciales. Saliendo...{Colors.END}")
                sys.exit(1)
        
        # Menú principal
        while True:
            self.print_banner()
            
            # Obtener estadísticas para mostrar en el menú principal
            try:
                # Intentar obtener una versión rápida de las estadísticas
                response = requests.get(
                    f'{GITHUB_API_URL}/users/{self.username}',
                    headers=self.headers,
                    timeout=API_TIMEOUT
                )
                if response.status_code == 200:
                    user_data = response.json()
                    public_repos = user_data.get('public_repos', 0)
                    
                    # Para obtener repositorios privados necesitamos otra petición
                    private_repos = 0
                    try:
                        private_response = requests.get(
                            f'{GITHUB_API_URL}/user', 
                            headers=self.headers,
                            timeout=API_TIMEOUT
                        )
                        if private_response.status_code == 200:
                            private_data = private_response.json()
                            total_repos = private_data.get('total_private_repos', 0) + public_repos
                            private_repos = private_data.get('total_private_repos', 0)
                    except:
                        pass
                    
                    user_status = f"{Colors.BOLD}Usuario: {Colors.GREEN}{self.username}{Colors.END} | "
                    user_status += f"{Colors.BOLD}Repos: {Colors.GREEN}{total_repos}{Colors.END} "
                    user_status += f"({Colors.GREEN}Públicos: {public_repos} | Privados: {private_repos}{Colors.END})"
                    print(user_status)
                else:
                    print(f"{Colors.BOLD}Usuario: {Colors.GREEN}{self.username}{Colors.END}")
            except:
                print(f"{Colors.BOLD}Usuario: {Colors.GREEN}{self.username}{Colors.END}")
            
            print(f"\n{Colors.BOLD}Menú Principal:{Colors.END}")
            print(f"1. {Colors.BLUE}Listar repositorios{Colors.END}")
            print(f"2. {Colors.BLUE}Gestionar privacidad de repositorios{Colors.END}")
            print(f"3. {Colors.BLUE}Cambiar credenciales{Colors.END}")
            print(f"4. {Colors.RED}Salir{Colors.END}")
            
            try:
                option = int(input(f"\n{Colors.BOLD}Selecciona una opción (1-4): {Colors.END}"))
                
                if option == 1:
                    self.clear_screen()
                    if self.fetch_repositories():
                        self.display_repositories()
                    input(f"\n{Colors.BOLD}Presiona Enter para continuar...{Colors.END}")
                
                elif option == 2:
                    self.clear_screen()
                    self.manage_visibility()
                
                elif option == 3:
                    self.clear_screen()
                    self.username, self.token = self.get_user_credentials()
                    if self.validate_credentials(self.username, self.token):
                        self.save_credentials(self.username, self.token)
                    else:
                        input(f"\n{Colors.BOLD}Presiona Enter para continuar...{Colors.END}")
                
                elif option == 4:
                    print(f"\n{Colors.GREEN}¡Gracias por usar GitHub Privacy Manager!{Colors.END}")
                    sys.exit(0)
                
                else:
                    print(f"{Colors.RED}Opción no válida. Por favor, intenta de nuevo.{Colors.END}")
                    input(f"\n{Colors.BOLD}Presiona Enter para continuar...{Colors.END}")
            
            except ValueError:
                print(f"{Colors.RED}Por favor, ingresa un número válido.{Colors.END}")
                input(f"\n{Colors.BOLD}Presiona Enter para continuar...{Colors.END}")

def main():
    """Función principal."""
    try:
        github_manager = GitHubManager()
        github_manager.run()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.GREEN}¡Hasta pronto!{Colors.END}")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Error inesperado: {str(e)}")
        print(f"\n{Colors.RED}Error inesperado: {str(e)}{Colors.END}")
        print(f"{Colors.YELLOW}Este error ha sido registrado en el archivo de log.{Colors.END}")
        sys.exit(1)

if __name__ == "__main__":
    main()
