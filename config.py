# In config.py
"""Configuración y constantes para la aplicación AudioTranscriptorPro."""

__version__ = "rev41__whisper_only_depuration"  # Updated version

# Tipos de archivo de audio soportados
AUDIO_FILE_TYPES = [("Archivos de audio", "*.mp3 *.wav *.ogg *.flac *.m4a"), # Añadidos más formatos comunes
                   ("Todos los archivos", "*.*")]
DEFAULT_EXTENSION = ".mp3"

# Configuración de Transcripción
TARGET_LANGUAGE = "es"
# GOOGLE_CHUNK_DURATION_MS = 30000 # Eliminado

# --- Configuración de Whisper ---
# Lista de modelos disponibles para selección
# Ordenados de más rápido/ligero a más lento/pesado
WHISPER_MODELS = ["tiny", "base", "small", "medium", "large"]
# Modelo por defecto si es necesario (aunque ahora se selecciona)
DEFAULT_WHISPER_MODEL = "tiny"
WHISPER_INITIAL_PROMPT = "Transcripción en español." # Prompt inicial para Whisper

# --- Mensajes específicos para la UI ---
MODEL_MEDIUM_WARNING = "¡Atención! El modelo 'medium' (y 'large') requiere muchos recursos y puede ser MUY lento en CPU. Úsalo solo para audios cortos."
MODEL_LARGE_WARNING = "¡Atención! El modelo 'large' es extremadamente lento en CPU y puede consumir mucha memoria. No recomendado sin GPU potente."

# --- NUEVO: Configuración Depuración ---
HIGHLIGHT_COLOR = "yellow" # Color para resaltar texto durante reproducción
PLAYBACK_UPDATE_INTERVAL_MS = 100 # Cada cuántos ms actualizar el resaltado

# Colores UI (Opcional, pero bueno tenerlos centralizados)
BG_COLOR = '#f0f0f0'
STATUS_COLOR_GRAY = "gray"
STATUS_COLOR_RED = "red"
STATUS_COLOR_GREEN = "green"
STATUS_COLOR_YELLOW = "yellow" # Para animación / estado "corriendo"
PROGRESS_BAR_COLOR = "#4CAF50" # Verde para la barra de progreso