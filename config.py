# config.py
"""Configuración y constantes para la aplicación AudioTranscriptorPro."""

__version__ = "rev38_refactored"  # Actualizar versión para reflejar refactorización

# Tipos de archivo de audio soportados
AUDIO_FILE_TYPES = [("Archivos de audio", "*.mp3 *.wav *.ogg"),
                   ("Todos los archivos", "*.*")]
DEFAULT_EXTENSION = ".mp3"

# Configuración de Transcripción
TARGET_LANGUAGE = "es"
GOOGLE_CHUNK_DURATION_MS = 30000  # Segmentos para Google (30 segundos)
WHISPER_MODEL_NAME = "tiny"      # Modelo Whisper a usar ("tiny", "base", "small", "medium", "large")
WHISPER_INITIAL_PROMPT = "Transcripción en español." # Prompt inicial para Whisper

# Colores UI (Opcional, pero bueno tenerlos centralizados)
BG_COLOR = '#f0f0f0'
STATUS_COLOR_GRAY = "gray"
STATUS_COLOR_RED = "red"
STATUS_COLOR_GREEN = "green"
STATUS_COLOR_YELLOW = "yellow" # Para animación