#!/data/data/com.termux/files/usr/bin/bash

# ======================================================================
# Script para configurar el directorio .gh-bins como PATH en Termux
# Autor: Andromux.org
# Versión: 1.0.0
# ======================================================================

# === Definición de colores para mensajes informativos ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# === Variables de configuración ===
REPO_URL="https://github.com/andromux/GH_CLI.git"
GH_DIR="$HOME/.gh-bins"
TEMP_DIR="$HOME/.gh_temp"
SHELL_CONFIG=""

# === Funciones ===
print_message() {
    local type=$1
    local message=$2
    case $type in
        "info") echo -e "${BLUE}${BOLD}[INFO]${RESET} ${message}";;
        "success") echo -e "${GREEN}${BOLD}[ÉXITO]${RESET} ${message}";;
        "warning") echo -e "${YELLOW}${BOLD}[ADVERTENCIA]${RESET} ${message}";;
        "error") echo -e "${RED}${BOLD}[ERROR]${RESET} ${message}";;
        "step") echo -e "\n${CYAN}${BOLD}=== ${message} ===${RESET}";;
        "progress") echo -e "${MAGENTA}${BOLD}-->${RESET} ${message}";;
    esac
}

show_spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\'
    echo -ne "${YELLOW}"
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        echo -ne "\r"
        sleep $delay
    done
    echo -ne "${RESET}\r\033[K"
}

check_dependencies() {
    print_message "step" "Verificando dependencias necesarias"
    if ! command -v git &> /dev/null; then
        print_message "warning" "Git no está instalado. Instalando git..."
        yes | pkg install git > /dev/null 2>&1 &
        show_spinner $!
        if command -v git &> /dev/null; then
            print_message "success" "Git ha sido instalado correctamente"
        else
            print_message "error" "No se pudo instalar Git. Intente manualmente con 'pkg install git'"
            exit 1
        fi
    else
        print_message "success" "Git ya está instalado ✓"
    fi
}

detect_shell() {
    print_message "step" "Detectando shell en uso"
    local current_shell=$(basename "$SHELL")
    print_message "info" "Shell actual: $current_shell"
    if [[ "$current_shell" == "zsh" ]]; then
        SHELL_CONFIG="$HOME/.zshrc"
    else
        SHELL_CONFIG="$HOME/.bashrc"
    fi
    if [ ! -f "$SHELL_CONFIG" ]; then
        print_message "warning" "Archivo $SHELL_CONFIG no existe. Creándolo..."
        touch "$SHELL_CONFIG"
    fi
    print_message "success" "Archivo de configuración: $SHELL_CONFIG ✓"
}

clone_repository() {
    print_message "step" "Clonando repositorio GH_CLI"
    [ -d "$TEMP_DIR" ] && rm -rf "$TEMP_DIR"
    print_message "progress" "Clonando desde: $REPO_URL"
    git clone "$REPO_URL" "$TEMP_DIR" > /dev/null 2>&1 &
    show_spinner $!
    if [ $? -eq 0 ]; then
        print_message "success" "Repositorio clonado exitosamente ✓"
    else
        print_message "error" "Error al clonar el repositorio. Verifique la URL o su conexión."
        exit 1
    fi
}

install_binaries() {
    print_message "step" "Instalando binarios Github_Manager_CLI"
    if [ -d "$GH_DIR" ]; then
        print_message "warning" "Directorio $GH_DIR ya existe. Haciendo copia de seguridad..."
        local backup_dir="$HOME/.gh-bins_backup_$(date +%Y%m%d%H%M%S)"
        mv "$GH_DIR" "$backup_dir"
        print_message "info" "Backup creado: $backup_dir"
    fi
    mkdir -p "$GH_DIR"
    print_message "progress" "Copiando binarios desde .gh-bins"
    cp -r "$TEMP_DIR/.gh-bins/"* "$GH_DIR/" 2>/dev/null || cp -r "$TEMP_DIR/"* "$GH_DIR/" 2>/dev/null
    if [ "$(ls -A "$GH_DIR" 2>/dev/null)" ]; then
        print_message "success" "Archivos copiados exitosamente ✓"
    else
        print_message "error" "No se encontraron archivos en el repositorio para copiar."
        exit 1
    fi
    chmod +x "$GH_DIR"/* &
    show_spinner $!
    rm -rf "$TEMP_DIR"
    print_message "success" "Permisos de ejecución aplicados ✓"
}

configure_path() {
    print_message "step" "Configurando PATH en $SHELL_CONFIG"
    if grep -q "\$HOME/.gh-bins" "$SHELL_CONFIG"; then
        print_message "info" "PATH ya está configurado en $SHELL_CONFIG"
    else
        cat >> "$SHELL_CONFIG" << EOF

# === Configuración de binarios Github_Manager_CLI ===
if [ -d "\$HOME/.gh-bins" ]; then
    export PATH="\$HOME/.gh-bins:\$PATH"
fi
EOF
        print_message "success" "PATH añadido correctamente ✓"
    fi
}

apply_changes() {
    print_message "step" "Aplicando cambios"
    source "$SHELL_CONFIG" 2>/dev/null || . "$SHELL_CONFIG" 2>/dev/null
    if echo "$PATH" | grep -q "$HOME/.gh-bins"; then
        print_message "success" "Configuración aplicada correctamente ✓"
    else
        print_message "warning" "La configuración se guardó pero no se aplicó automáticamente."
        print_message "info" "Ejecute: source $SHELL_CONFIG"
    fi
}

show_summary() {
    print_message "step" "Resumen de instalación"
    echo -e "${BOLD}Directorio de binarios:${RESET} $GH_DIR"
    echo -e "${BOLD}Archivo de configuración:${RESET} $SHELL_CONFIG"
    echo -e "${BOLD}Binarios instalados:${RESET} $(ls -1 "$GH_DIR" | wc -l)"
    echo -e "\n${GREEN}${BOLD}¡Instalación completada exitosamente!${RESET}"
    echo -e "Puede ejecutar los binarios de Github_Manager_CLI desde cualquier parte."
    echo -e "Para que los cambios surtan efecto, abra una nueva sesión de Termux o ejecute: ${CYAN}source $SHELL_CONFIG${RESET}\n"
}

main() {
    echo -e "${CYAN}${BOLD}"
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║     INSTALADOR DE BINARIOS Github_Manager_CLI         ║"
    echo "║             para Termux v1.0.0                         ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo -e "${RESET}"
    check_dependencies
    detect_shell
    clone_repository
    install_binaries
    configure_path
    apply_changes
    show_summary
}

main
