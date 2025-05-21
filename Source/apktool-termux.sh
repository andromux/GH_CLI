#!/bin/bash

# ApkTool Installer para Termux
# Creado: $(date +"%d-%m-%Y")

# Colores
RED="\033[1;31m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
BLUE="\033[1;34m"
MAGENTA="\033[1;35m"
CYAN="\033[1;36m"
WHITE="\033[1;37m"
RESET="\033[0m"

# Variables
APKTOOL_VERSION="2.11.1"
SUCCESS=true
LOG_FILE="apktool_install.log"

# Función para mostrar la animación de carga
show_spinner() {
    local message="$1"
    local pid=$!
    local delay=0.1
    local spinstr='|/-\'
    
    echo -ne "$message "
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        printf "${CYAN}[%c]${RESET}" "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b"
    done
    printf "   \b\b\b"
}

# Función para mostrar una barra de progreso
progress_bar() {
    local message="$1"
    local duration=$2
    local width=50
    
    echo -e "${BLUE}$message${RESET}"
    
    for ((i=0; i<=width; i++)); do
        sleep 0.05
        percent=$((i*100/width))
        
        # Calculamos cuántos caracteres mostrar
        chars=$((i*width/width))
        
        # Construimos la barra de progreso
        bar="["
        for ((j=0; j<chars; j++)); do
            bar="${bar}█"
        done
        
        # Añadimos espacios para completar la barra
        for ((j=chars; j<width; j++)); do
            bar="${bar} "
        done
        bar="${bar}]"
        
        # Mostramos la barra de progreso
        echo -ne "${GREEN}${bar}${RESET} ${YELLOW}${percent}%${RESET}\r"
    done
    echo
}

# Función para registrar en el log
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Función para mostrar mensajes
print_message() {
    local type="$1"
    local message="$2"
    
    case "$type" in
        "info") echo -e "${BLUE}[INFO]${RESET} $message" ;;
        "success") echo -e "${GREEN}[ÉXITO]${RESET} $message" ;;
        "warning") echo -e "${YELLOW}[AVISO]${RESET} $message" ;;
        "error") echo -e "${RED}[ERROR]${RESET} $message" ;;
    esac
    
    log "$type: $message"
}

# Función para verificar si un paquete está instalado
is_package_installed() {
    local package="$1"
    if dpkg -s "$package" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Función para verificar comandos
check_command() {
    local cmd="$1"
    if ! command -v "$cmd" &> /dev/null; then
        print_message "error" "El comando '$cmd' no está disponible."
        SUCCESS=false
        return 1
    fi
    return 0
}

# Función para instalar paquetes (evitando advertencias de apt)
install_package() {
    local package="$1"
    print_message "info" "Instalando $package..."
    
    # Usamos apt-get en lugar de apt o pkg para evitar advertencias
    (DEBIAN_FRONTEND=noninteractive apt-get -qq -y install "$package" >> "$LOG_FILE" 2>&1) &
    show_spinner "Instalando $package..."
    
    if ! dpkg -s "$package" >/dev/null 2>&1; then
        print_message "error" "No se pudo instalar $package."
        return 1
    else
        print_message "success" "$package instalado correctamente."
        return 0
    fi
}

# Función para actualizar repositorios sin advertencias
update_repos() {
    print_message "info" "Actualizando repositorios de paquetes..."
    
    # Usamos apt-get con opciones para suprimir advertencias
    (DEBIAN_FRONTEND=noninteractive apt-get -qq update && apt-get -qq -y upgrade) >> "$LOG_FILE" 2>&1 &
    show_spinner "Actualizando repositorios..."
    
    if [ $? -ne 0 ]; then
        print_message "error" "No se pudieron actualizar los repositorios."
        SUCCESS=false
        return 1
    else
        print_message "success" "Repositorios actualizados correctamente."
        return 0
    fi
}

# Función para mostrar el banner
show_banner() {
    clear
    echo -e "${CYAN}"
    echo "    _    ____  _  _______ ___   ___  _     "
    echo "   / \  |  _ \| |/ /_   _/ _ \ / _ \| |    "
    echo "  / _ \ | |_) | ' /  | || | | | | | | |    "
    echo " / ___ \|  __/| . \  | || |_| | |_| | |___ "
    echo "/_/   \_\_|   |_|\_\ |_| \___/ \___/|_____|"
    echo -e "${RESET}"
    echo -e "${GREEN}===== Instalador para Termux =====${RESET}"
    echo -e "${YELLOW}Versión: $APKTOOL_VERSION${RESET}"
    echo -e "${MAGENTA}------------------------------------${RESET}"
    echo
}

# Control de errores con trap
trap 'echo -e "${RED}[ERROR] La instalación fue interrumpida.${RESET}"; log "Instalación interrumpida por el usuario"; exit 1' INT TERM

# Inicio del script
show_banner
echo -e "${CYAN}Iniciando instalación de ApkTool...${RESET}"
echo -e "${YELLOW}El proceso puede tardar varios minutos dependiendo de tu conexión.${RESET}"
echo

# Comprobar si Termux es el entorno
if [ ! -d "/data/data/com.termux" ]; then
    print_message "error" "Este script está diseñado para ejecutarse en Termux."
    exit 1
fi

# Creamos archivo de log
echo "=== Log de instalación de ApkTool - $(date) ===" > "$LOG_FILE"

# Instalar bc (necesario para la barra de progreso)
if ! is_package_installed "bc"; then
    install_package "bc"
fi

# Actualizar repositorios
update_repos

# Instalar paquetes necesarios
echo
print_message "info" "Instalando paquetes necesarios..."
progress_bar "Preparando la instalación de dependencias..." 2

packages=("python" "python2" "openjdk-17" "wget" "curl")
for pkg in "${packages[@]}"; do
    if ! is_package_installed "$pkg"; then
        install_package "$pkg"
    else
        print_message "info" "$pkg ya está instalado."
    fi
done

# Verificar comandos esenciales
echo
print_message "info" "Verificando comandos esenciales..."
commands=("wget" "curl" "java")
all_commands_ok=true

for cmd in "${commands[@]}"; do
    if ! check_command "$cmd"; then
        all_commands_ok=false
    fi
done

if [ "$all_commands_ok" = true ]; then
    print_message "success" "Todos los comandos esenciales están disponibles."
else
    print_message "warning" "Algunos comandos no están disponibles, pero intentaremos continuar."
fi

# Descargar ApkTool
echo
print_message "info" "Descargando ApkTool versión $APKTOOL_VERSION..."
(wget "https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_${APKTOOL_VERSION}.jar" -O "$PREFIX/bin/apktool.jar") >> "$LOG_FILE" 2>&1 &
show_spinner "Descargando ApkTool..."
if [ ! -f "$PREFIX/bin/apktool.jar" ]; then
    print_message "error" "No se pudo descargar ApkTool."
    SUCCESS=false
else
    print_message "success" "ApkTool descargado correctamente."
    chmod +r "$PREFIX/bin/apktool.jar" >> "$LOG_FILE" 2>&1
fi

# Descargar script wrapper
print_message "info" "Descargando script wrapper..."
(wget "https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool" -O "$PREFIX/bin/apktool") >> "$LOG_FILE" 2>&1 &
show_spinner "Descargando script wrapper..."
if [ ! -f "$PREFIX/bin/apktool" ]; then
    print_message "error" "No se pudo descargar el script wrapper."
    SUCCESS=false
else
    print_message "success" "Script wrapper descargado correctamente."
    chmod +x "$PREFIX/bin/apktool" >> "$LOG_FILE" 2>&1
fi

# Verificar la instalación
echo
print_message "info" "Verificando la instalación..."
progress_bar "Comprobando archivos y permisos..." 3

if [ -f "$PREFIX/bin/apktool.jar" ] && [ -f "$PREFIX/bin/apktool" ] && [ -x "$PREFIX/bin/apktool" ]; then
    VERSION_OUTPUT=$(apktool --version 2>&1)
    if [[ "$VERSION_OUTPUT" == *"$APKTOOL_VERSION"* ]]; then
        print_message "success" "¡ApkTool se ha instalado correctamente!"
        print_message "info" "Versión instalada: $VERSION_OUTPUT"
    else
        print_message "warning" "ApkTool parece estar instalado, pero la versión no coincide."
        print_message "info" "Versión reportada: $VERSION_OUTPUT"
    fi
else
    print_message "error" "La verificación de la instalación falló."
    SUCCESS=false
fi

# Resumen final
echo
echo -e "${MAGENTA}----------------------------------------${RESET}"
if [ "$SUCCESS" = true ]; then
    echo -e "${GREEN}✓ La instalación de ApkTool ha finalizado con éxito.${RESET}"
    echo -e "${BLUE}Para usar ApkTool, ejecuta:${RESET} ${YELLOW}apktool [opciones]${RESET}"
    echo -e "${BLUE}Ejemplo:${RESET} ${YELLOW}apktool d mi_aplicacion.apk${RESET}"
else
    echo -e "${RED}✗ La instalación ha encontrado algunos problemas.${RESET}"
    echo -e "${YELLOW}Por favor, revisa el archivo de log:${RESET} ${WHITE}$LOG_FILE${RESET}"
    echo -e "${BLUE}Puedes intentar solucionar los errores y volver a ejecutar el script.${RESET}"
fi
echo -e "${MAGENTA}----------------------------------------${RESET}"

# Mostrar notas adicionales
echo
echo -e "${CYAN}[NOTAS]${RESET}"
echo -e "• ${WHITE}Este script ha creado un registro en ${YELLOW}$LOG_FILE${RESET}"
echo -e "• ${WHITE}Java es necesario para el funcionamiento de ApkTool${RESET}"
echo -e "• ${WHITE}Para más información, visita: ${BLUE}https://ibotpeaches.github.io/Apktool/${RESET}"

exit 0
