# playback.py
"""Funciones para controlar la reproducción de audio usando Pygame."""

import pygame
from pydub import AudioSegment
import io

_is_initialized = False

def init_playback():
    """Inicializa pygame.mixer si no está ya inicializado."""
    global _is_initialized
    if not _is_initialized:
        try:
            pygame.mixer.init()
            _is_initialized = True
            print("Pygame mixer inicializado.")
        except pygame.error as e:
             print(f"Error al inicializar pygame mixer: {e}. La reproducción podría no funcionar.")
             # Se podría mostrar un messagebox o deshabilitar funciones de reproducción

def load_audio_segment(audio_segment: AudioSegment):
    """Carga un AudioSegment en pygame.mixer.music desde un buffer en memoria."""
    if not _is_initialized: init_playback()
    if not _is_initialized: return False # Falló la inicialización

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

def play_audio():
    """Inicia la reproducción del audio cargado."""
    if not _is_initialized or not pygame.mixer.get_init(): return
    try:
        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.play()
            print("Reproducción iniciada.")
        else:
            print("Advertencia: Ya se estaba reproduciendo audio.")
    except pygame.error as e:
         print(f"Error al iniciar reproducción: {e}")

def stop_audio():
    """Detiene la reproducción de audio."""
    if not _is_initialized or not pygame.mixer.get_init(): return
    try:
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            print("Reproducción detenida.")
    except pygame.error as e:
         print(f"Error al detener reproducción: {e}")

def unload_audio():
    """Descarga el audio cargado de la memoria."""
    if not _is_initialized or not pygame.mixer.get_init(): return
    try:
        # Detener primero por si acaso
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        print("Audio descargado de pygame.")
    except pygame.error as e:
         print(f"Error al descargar audio: {e}")

def is_playing() -> bool:
    """Verifica si se está reproduciendo audio."""
    if not _is_initialized or not pygame.mixer.get_init(): return False
    try:
        return pygame.mixer.music.get_busy()
    except pygame.error as e:
         print(f"Error al comprobar estado de reproducción: {e}")
         return False

def quit_playback():
    """Cierra pygame.mixer."""
    global _is_initialized
    if _is_initialized and pygame.mixer.get_init():
        try:
            pygame.mixer.quit()
            _is_initialized = False
            print("Pygame mixer cerrado.")
        except pygame.error as e:
             print(f"Error al cerrar pygame mixer: {e}")