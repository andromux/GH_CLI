#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitCommitTool - Una herramienta avanzada para gestionar commits y push de Git
Desarrollado para uso en Termux y entornos SSH
"""

import os
import sys
import subprocess
import argparse
import re
from datetime import datetime
import signal
import time

# Colores ANSI para terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class GitCommitTool:
    def __init__(self):
        self.parser = self._setup_argument_parser()
        self.args = None
        # Configurar el manejo de señales para limpieza adecuada
        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)

    def _setup_argument_parser(self):
        """Configura el parser de argumentos de línea de comandos"""
        parser = argparse.ArgumentParser(
            description=f"{Colors.CYAN}GitCommitTool{Colors.ENDC} - Herramienta para gestionar commits y push de Git",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        parser.add_argument('-m', '--message', type=str, help='Mensaje del commit (opcional)')
        parser.add_argument('-b', '--branch', type=str, default='main', 
                          help='Rama de destino (default: main)')
        parser.add_argument('-r', '--remote', type=str, default='origin', 
                          help='Remoto de destino (default: origin)')
        parser.add_argument('-n', '--no-push', action='store_true', 
                          help='Solo hace commit, sin push')
        parser.add_argument('-s', '--status', action='store_true', 
                          help='Muestra estado del repositorio antes de proceder')
        parser.add_argument('-v', '--verbose', action='store_true', 
                          help='Mostrar información detallada')
        
        return parser

    def _handle_interrupt(self, signum, frame):
        """Maneja interrupciones de manera elegante"""
        print(f"\n{Colors.YELLOW}[!] Proceso interrumpido por el usuario{Colors.ENDC}")
        sys.exit(1)

    def _print_banner(self):
        """Muestra un banner con información del programa"""
        banner = f"""
{Colors.CYAN}╭─────────────────────────────────────────────╮
│ {Colors.BOLD}GitCommitTool{Colors.ENDC}{Colors.CYAN}                             │
│ Facilita el manejo de commits en Git             │
│ Para uso en Termux y entornos SSH                │
╰─────────────────────────────────────────────╯{Colors.ENDC}
"""
        print(banner)

    def _exec_command(self, command, suppress_output=False):
        """Ejecuta un comando de shell y maneja errores adecuadamente"""
        try:
            if suppress_output:
                result = subprocess.run(
                    command, 
                    shell=True, 
                    text=True,
                    capture_output=True
                )
            else:
                result = subprocess.run(
                    command, 
                    shell=True, 
                    text=True,
                    stderr=subprocess.PIPE
                )
                
            if result.returncode != 0:
                print(f"{Colors.RED}[✗] Error al ejecutar: {command}{Colors.ENDC}")
                print(f"{Colors.RED}    → {result.stderr.strip()}{Colors.ENDC}")
                return False, result.stderr
            return True, result.stdout if suppress_output else True
        except Exception as e:
            print(f"{Colors.RED}[✗] Excepción al ejecutar: {command}{Colors.ENDC}")
            print(f"{Colors.RED}    → {str(e)}{Colors.ENDC}")
            return False, str(e)

    def _validate_git_repo(self):
        """Verifica que estamos en un repositorio Git válido"""
        success, output = self._exec_command("git rev-parse --is-inside-work-tree", suppress_output=True)
        if not success or output.strip() != "true":
            print(f"{Colors.RED}[✗] No estás dentro de un repositorio Git válido{Colors.ENDC}")
            return False
        return True

    def _get_current_branch(self):
        """Obtiene el nombre de la rama actual"""
        success, output = self._exec_command("git symbolic-ref --short HEAD 2>/dev/null || git rev-parse --short HEAD", suppress_output=True)
        if not success:
            print(f"{Colors.YELLOW}[!] No se pudo determinar la rama actual{Colors.ENDC}")
            return "desconocida"
        return output.strip()

    def _validate_branch_exists(self, branch, remote="origin"):
        """Verifica si la rama existe en el remoto"""
        success, output = self._exec_command(f"git ls-remote --heads {remote} {branch}", suppress_output=True)
        return success and branch in output

    def _sanitize_commit_message(self, message):
        """Sanitiza el mensaje de commit para evitar problemas con caracteres especiales"""
        # Eliminar caracteres que pueden causar problemas en la línea de comandos
        sanitized = re.sub(r'[`$"\'\\]', '', message)
        return sanitized

    def _get_commit_message(self):
        """Solicita un mensaje de commit al usuario o usa el proporcionado por argumento"""
        if self.args.message:
            return self.args.message
        
        print(f"{Colors.CYAN}[?] Introduce el mensaje para el commit:{Colors.ENDC}")
        message = input(f"{Colors.BOLD}> {Colors.ENDC}").strip()
        
        if not message:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"Actualización: {current_time}"
            print(f"{Colors.YELLOW}[!] Mensaje vacío, usando mensaje automático: {message}{Colors.ENDC}")
        
        return message

    def _show_status(self):
        """Muestra el estado actual del repositorio"""
        print(f"\n{Colors.CYAN}[*] Estado actual del repositorio:{Colors.ENDC}")
        self._exec_command("git status -s")
        
        # Mostrar último commit
        print(f"\n{Colors.CYAN}[*] Último commit:{Colors.ENDC}")
        self._exec_command("git log -1 --oneline")
        print()

    def _check_changes(self):
        """Verifica si hay cambios para commitear"""
        success, output = self._exec_command("git status --porcelain", suppress_output=True)
        if not output.strip():
            print(f"{Colors.YELLOW}[!] No hay cambios para commitear{Colors.ENDC}")
            return False
        return True

    def run(self):
        """Ejecuta el proceso principal"""
        self._print_banner()
        
        try:
            self.args = self.parser.parse_args()
            
            # Verificar que estamos en un repositorio Git
            if not self._validate_git_repo():
                return 1
            
            # Mostrar información inicial
            current_branch = self._get_current_branch()
            print(f"{Colors.BLUE}[i] Repositorio: {os.path.basename(os.getcwd())}{Colors.ENDC}")
            print(f"{Colors.BLUE}[i] Rama actual: {current_branch}{Colors.ENDC}")
            print(f"{Colors.BLUE}[i] Rama destino: {self.args.branch}{Colors.ENDC}")
            
            # Mostrar estado si se solicita
            if self.args.status:
                self._show_status()
            
            # Verificar cambios
            if not self._check_changes():
                return 0
            
            # Obtener mensaje de commit
            commit_message = self._get_commit_message()
            sanitized_message = self._sanitize_commit_message(commit_message)
            
            # Confirmar operación
            print(f"\n{Colors.CYAN}[*] Operaciones a realizar:{Colors.ENDC}")
            print(f"{Colors.GREEN}    → Añadir cambios (git add .){Colors.ENDC}")
            print(f"{Colors.GREEN}    → Commit con mensaje: \"{sanitized_message}\"{Colors.ENDC}")
            
            if not self.args.no_push:
                print(f"{Colors.GREEN}    → Push a {self.args.remote}/{self.args.branch}{Colors.ENDC}")
            
            print("\n¿Proceder? [S/n]: ", end="")
            confirm = input().strip().lower()
            if confirm and confirm != "s" and confirm != "y":
                print(f"{Colors.YELLOW}[!] Operación cancelada por el usuario{Colors.ENDC}")
                return 0
            
            # Añadir cambios
            print(f"\n{Colors.CYAN}[*] Añadiendo cambios...{Colors.ENDC}")
            if not self._exec_command("git add .")[0]:
                return 1
            
            # Hacer commit
            print(f"{Colors.CYAN}[*] Haciendo commit...{Colors.ENDC}")
            if not self._exec_command(f'git commit -m "{sanitized_message}"')[0]:
                return 1
            
            # Hacer push si se solicita
            if not self.args.no_push:
                print(f"{Colors.CYAN}[*] Haciendo push a {self.args.remote}/{self.args.branch}...{Colors.ENDC}")
                
                # Verificar si la rama remota existe
                if not self._validate_branch_exists(self.args.branch, self.args.remote):
                    print(f"{Colors.YELLOW}[!] La rama {self.args.branch} no existe en {self.args.remote}{Colors.ENDC}")
                    print(f"{Colors.YELLOW}[!] ¿Deseas crearla? [S/n]: {Colors.ENDC}", end="")
                    confirm = input().strip().lower()
                    if confirm and confirm != "s" and confirm != "y":
                        print(f"{Colors.YELLOW}[!] Push cancelado{Colors.ENDC}")
                        return 0
                
                # Hacer push
                push_cmd = f"git push {self.args.remote} {current_branch}:{self.args.branch}"
                if not self._exec_command(push_cmd)[0]:
                    return 1
            
            print(f"\n{Colors.GREEN}[✓] ¡Operación completada con éxito!{Colors.ENDC}")
            
            # Mostrar resumen final
            if self.args.verbose:
                self._show_status()
            
            return 0
            
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}[!] Operación cancelada por el usuario{Colors.ENDC}")
            return 1
        except Exception as e:
            print(f"{Colors.RED}[✗] Error inesperado: {str(e)}{Colors.ENDC}")
            if self.args and self.args.verbose:
                import traceback
                traceback.print_exc()
            return 1

if __name__ == "__main__":
    tool = GitCommitTool()
    sys.exit(tool.run())