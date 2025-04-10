# playback.py
"""Funciones para controlar la reproducción de audio usando Pygame."""

import pygame
from pydub import AudioSegment
import io
import pathlib # Necesario para cargar desde ruta

_is_initialized = False
_mixer_initialized = False

def init_playback():
    """Inicializa pygame y pygame.mixer si no están ya inicializados."""
    global _is_initialized, _mixer_initialized
    if not _is_initialized:
        try:
            pygame.init() # Inicializa todos los módulos de pygame
            _is_initialized = True
            print("Pygame inicializado.")
        except pygame.error as e:
            print(f"Error al inicializar pygame: {e}. La reproducción no funcionará.")
            return False # Fallo crítico

    if not _mixer_initialized:
        try:
            pygame.mixer.init() # Inicializa solo el mixer
            _mixer_initialized = True
            print("Pygame mixer inicializado.")
        except pygame.error as e:
             print(f"Error al inicializar pygame mixer: {e}. La reproducción podría no funcionar.")
             return False # Fallo crítico
    return True


def load_audio_from_path(wav_path: pathlib.Path):
    """Carga un archivo WAV desde una ruta en pygame.mixer.music."""
    if not _mixer_initialized:
        if not init_playback():
            return False # No se pudo inicializar
    if not _mixer_initialized: return False

    try:
        pygame.mixer.music.load(str(wav_path))
        print(f"Audio cargado en pygame desde: {wav_path.name}")
        return True
    except pygame.error as e:
         print(f"Error al cargar audio desde path en pygame: {e}")
    return False


def load_audio_segment(audio_segment: AudioSegment):
    """Carga un AudioSegment en pygame.mixer.music desde un buffer en memoria."""
    if not _mixer_initialized:
        if not init_playback():
            return False # No se pudo inicializar
    if not _mixer_initialized: return False

    try:
        wav_buffer = io.BytesIO()
        audio_segment.export(wav_buffer, format="wav")
        wav_buffer.seek(0)
        pygame.mixer.music.load(wav_buffer)
        print("Audio segment cargado en pygame.")
        return True
    except pygame.error as e:
         print(f"Error al cargar audio segment en pygame: {e}")
    except Exception as e:
        print(f"Error al exportar audio segment para reproducción: {e}")
    return False

def play_audio(start_seconds: float = 0.0):
    """
    Inicia la reproducción del audio cargado.
    Args:
        start_seconds (float): Posición en segundos desde donde empezar a reproducir.
                               Requiere pygame >= 2.0.0.
    """
    if not _mixer_initialized or not pygame.mixer.get_init(): return False
    try:
        # Detener si ya está sonando para empezar desde el nuevo punto
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()

        # Verificar versión de pygame para el argumento 'start'
        if pygame.version.vernum >= (2, 0, 0):
             pygame.mixer.music.play(start=start_seconds)
             print(f"Reproducción iniciada desde {start_seconds:.2f}s.")
        else:
             if start_seconds > 0:
                 print("Advertencia: Tu versión de pygame no soporta iniciar desde una posición específica. Iniciando desde el principio.")
             pygame.mixer.music.play()
             print("Reproducción iniciada (desde el principio).")
        return True

    except pygame.error as e:
         print(f"Error al iniciar reproducción: {e}")
         return False


def stop_audio():
    """Detiene la reproducción de audio."""
    if not _mixer_initialized or not pygame.mixer.get_init(): return
    try:
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            print("Reproducción detenida.")
    except pygame.error as e:
         print(f"Error al detener reproducción: {e}")

def pause_audio():
    """Pausa la reproducción de audio."""
    if not _mixer_initialized or not pygame.mixer.get_init(): return
    try:
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            print("Reproducción pausada.")
    except pygame.error as e:
         print(f"Error al pausar reproducción: {e}")

def unpause_audio():
    """Reanuda la reproducción de audio pausada."""
    if not _mixer_initialized or not pygame.mixer.get_init(): return
    try:
        # Solo despausar si está pausado (get_busy() sigue siendo True si está pausado)
        # No hay una forma directa de saber si está pausado vs sonando, pero unpause() no hace daño si ya suena.
        pygame.mixer.music.unpause()
        print("Reproducción reanudada.")
    except pygame.error as e:
         print(f"Error al reanudar reproducción: {e}")


def unload_audio():
    """Descarga el audio cargado de la memoria."""
    if not _mixer_initialized or not pygame.mixer.get_init(): return
    try:
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        print("Audio descargado de pygame.")
    except pygame.error as e:
         print(f"Error al descargar audio: {e}")

def is_playing() -> bool:
    """
    Verifica si se está reproduciendo audio (no pausado).
    Devuelve True si está activamente sonando, False si está detenido o pausado.
    """
    if not _mixer_initialized or not pygame.mixer.get_init(): return False
    try:
        # get_busy() devuelve True tanto si está sonando como si está pausado.
        # Necesitamos una lógica adicional. get_pos() devuelve -1 si no está sonando.
        # Sin embargo, get_pos() también avanza si está pausado, lo que es confuso.
        # La forma más fiable es asumir que si llamamos a play/unpause, está sonando,
        # y si llamamos a pause/stop, no lo está. Mantenemos un estado externo si es necesario.
        # Por ahora, simplemente devolvemos get_busy(), aceptando la limitación.
        return pygame.mixer.music.get_busy()
    except pygame.error as e:
         print(f"Error al comprobar estado de reproducción: {e}")
         return False

def get_current_pos_ms() -> int:
    """
    Devuelve la posición de reproducción actual en milisegundos.
    Devuelve -1 si no se está reproduciendo.
    """
    if not _mixer_initialized or not pygame.mixer.get_init(): return -1
    try:
        return pygame.mixer.music.get_pos()
    except pygame.error as e:
         print(f"Error al obtener posición de reproducción: {e}")
         return -1


def quit_playback():
    """Cierra pygame.mixer y pygame."""
    global _is_initialized, _mixer_initialized
    if _mixer_initialized and pygame.mixer.get_init():
        try:
            pygame.mixer.quit()
            _mixer_initialized = False
            print("Pygame mixer cerrado.")
        except pygame.error as e:
             print(f"Error al cerrar pygame mixer: {e}")
    if _is_initialized:
         try:
             pygame.quit() # Cierra todos los módulos de pygame
             _is_initialized = False
             print("Pygame cerrado.")
         except pygame.error as e:
             print(f"Error al cerrar pygame: {e}")