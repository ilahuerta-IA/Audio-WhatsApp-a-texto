# config.py
"""Configuración y constantes para la aplicación AudioTranscriptorPro."""

__version__ = "rev39__model_selection"  # Actualizar versión para reflejar refactorización

# Tipos de archivo de audio soportados
AUDIO_FILE_TYPES = [("Archivos de audio", "*.mp3 *.wav *.ogg"),
                   ("Todos los archivos", "*.*")]
DEFAULT_EXTENSION = ".mp3"

# Configuración de Transcripción
TARGET_LANGUAGE = "es"
GOOGLE_CHUNK_DURATION_MS = 30000  # Segmentos para Google (30 segundos)
# --- Configuración de Whisper (Enfoque CPU) ---
# Lista de modelos considerados viables para ejecución en CPU
# Ordenados de más rápido/ligero a más lento/pesado
# tiny: El más rápido, menor precisión.
# base: Buen equilibrio entre velocidad y precisión.
# small: Significativamente más preciso que base, pero notablemente más lento en CPU. Puede ser el límite superior práctico para CPU en muchos casos.
# medium y large: Generalmente no recomendados para ejecución exclusiva en CPU a menos que tengas muchísima paciencia y audios muy cortos.
WHISPER_MODEL_NAME = "tiny"      # Modelo Whisper a usar ("tiny", "base", "small") -- "medium" y "large" mejor solo para GPU
WHISPER_INITIAL_PROMPT = "Transcripción en español." # Prompt inicial para Whisper


# Colores UI (Opcional, pero bueno tenerlos centralizados)
BG_COLOR = '#f0f0f0'
STATUS_COLOR_GRAY = "gray"
STATUS_COLOR_RED = "red"
STATUS_COLOR_GREEN = "green"
STATUS_COLOR_YELLOW = "yellow" # Para animación
